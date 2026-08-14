"""
Stage 1 观测编码器（Observation Encoder）MAE 预训练脚本 —— SSL4EO-S12 数据集

完整流程：读取遥感影像 -> 随机掩码 -> 编码器编码可见 patch -> 解码器重建整图
        -> 仅在被掩码区域计算重建损失 -> 反向传播 -> 优化器更新 -> 保存 checkpoint

支持两种运行模式（由是否经 torchrun 启动自动判定）：
- 单卡模式：直接 python 运行，模型不分片
- 多卡 FSDP 模式：torchrun 启动，用 FSDP2(fully_shard) 把参数/梯度/优化器状态
  分片到各 GPU，数据并行（每卡读不同 shard）

关键特性：
- Masked Autoencoder（编码器 + 轻量解码器）
- 仅对被掩码 patch 计算重建损失
- AdamW 优化器 + 余弦学习率调度
- bf16 混合精度（bf16 无需 GradScaler，直接 autocast）
- TensorBoard 日志（仅主进程 rank 0）
- 分布式 checkpoint 保存（汇聚完整权重，与卡数解耦）
"""

import argparse
import os
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torch.amp import autocast
import yaml
from tqdm import tqdm

try:
    from torch.utils.tensorboard import SummaryWriter
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False

# 把项目根目录加入 import 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.encoders.tiny_vit_encoder import TinyViTEncoder
from models.decoders.light_decoder import LightDecoder
from models.losses.reconstruction import get_reconstruction_loss
from data.datamodules.ssl4eo_dm import SSL4EODataModule
from train.fsdp_utils import (
    setup_distributed,
    cleanup_distributed,
    is_distributed,
    is_main_process,
    get_rank,
    get_world_size,
    wrap_model_fsdp2,
    get_full_state_dict,
    get_full_optim_state_dict,
    set_full_optim_state_dict,
    barrier,
)
from train.visualization import save_reconstruction_grid

def log_main(msg: str):
    """仅在主进程（rank 0）打印日志，避免多卡重复刷屏。"""
    if is_main_process():
        print(msg)


def load_config(config_path: str) -> dict:
    """加载并合并 YAML 配置文件。

    支持两种写法：
    1. 单文件内联：直接在文件里写 model / data 两个嵌套字段（本项目采用）
    2. 引用式：通过 model_config / data_config 字段引用 configs/ 下的独立文件
    """
    config_path = Path(config_path).resolve()

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    config_dir = config_path.parent.parent

    # 若引用了独立的 model 配置文件，则加载进来
    if "model_config" in config and "model" not in config:
        model_config_path = config_dir / "configs" / "model" / f"{config['model_config']}.yaml"
        if model_config_path.exists():
            with open(model_config_path, "r") as f:
                config["model"] = yaml.safe_load(f)

    # 若引用了独立的 data 配置文件，则加载进来
    if "data_config" in config and "data" not in config:
        data_config_path = config_dir / "configs" / "data" / f"{config['data_config']}.yaml"
        if data_config_path.exists():
            with open(data_config_path, "r") as f:
                config["data"] = yaml.safe_load(f)

    return config


def create_model(model_config: dict):
    """根据配置创建编码器（TinyViTEncoder）和解码器（LightDecoder）。"""
    enc = model_config["encoder"]
    dec = model_config["decoder"]

    encoder = TinyViTEncoder(
        img_size=enc.get("img_size", 256),
        in_channels=enc["in_channels"],
        patch_size=enc["patch_size"],
        embed_dim=enc["embed_dim"],
        depth=enc["depth"],
        num_heads=enc["num_heads"],
        mlp_ratio=enc.get("mlp_ratio", 4.0),
        dropout=enc.get("dropout", 0.0),
    )

    decoder = LightDecoder(
        in_dim=dec["in_dim"],
        out_channels=dec["out_channels"],
        patch_size=enc["patch_size"],
        img_size=enc.get("img_size", 256),
        depth=dec["depth"],
        num_heads=dec.get("num_heads", 4),
        decoder_embed_dim=dec.get("decoder_embed_dim", 128),
        mlp_ratio=dec.get("mlp_ratio", 4.0),
        dropout=dec.get("dropout", 0.0),
        decoder_mode=dec.get("decoder_mode", "transformer"),
    )

    return encoder, decoder


def create_datamodule(data_config: dict) -> SSL4EODataModule:
    """根据配置创建 SSL4EO 数据模块。

    多卡模式下，底层 WebDataset 通过 split_by_node 把 tar shard 自动按 rank
    切分，因此每张卡读取不同的数据子集，实现数据并行。
    """
    return SSL4EODataModule(
        modality=data_config.get("modality", "S2L2A"),
        batch_size=data_config.get("batch_size", 8),
        num_workers=data_config.get("num_workers", 4),
        random_season=data_config.get("random_season", True),
        base_path=data_config.get("data_root", "/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1"),
        normalize=data_config.get("normalize", True),
        cache_size=data_config.get("cache_size", 100),
        shard_pattern=data_config.get("shard_pattern", "*.tar"),
    )


def save_checkpoint(checkpoint_dir, global_step, model, encoder, decoder, optimizer, config):
    """保存 encoder + decoder + optimizer + step + config 到单个 checkpoint 文件。

    FSDP 模式下，encoder/decoder 的参数、以及优化器的动量状态都分片在各 GPU，
    需先分别汇聚成完整权重 / 完整优化器状态（在 rank 0），再仅由 rank 0 写盘。
    这样保存的 checkpoint 不含任何 DTensor / DeviceMesh 引用，与训练卡数解耦，
    可在任意卡数或纯 CPU 上加载。

    Args:
        model: 包裹 encoder/decoder 的 ModuleDict（供优化器状态汇聚建立 FQN 映射）
        encoder/decoder: 两个子模型（分别汇聚权重）
        optimizer: 优化器
    """
    # 集合通信：所有 rank 都必须调用，不能只在 rank 0 调用
    encoder_state = get_full_state_dict(encoder)
    decoder_state = get_full_state_dict(decoder)
    optim_state = get_full_optim_state_dict(model, optimizer)

    if not is_main_process():
        barrier()
        return

    os.makedirs(checkpoint_dir, exist_ok=True)
    ckpt_path = os.path.join(checkpoint_dir, f"checkpoint_step_{global_step}.pt")
    torch.save({
        "global_step": global_step,
        "encoder_state_dict": encoder_state,
        "decoder_state_dict": decoder_state,
        "optimizer_state_dict": optim_state,
        "config": config,
    }, ckpt_path)
    log_main(f"checkpoint 已保存: {ckpt_path}")
    barrier()


def train_one_epoch(
    model, encoder, decoder, dataloader, loss_fn, optimizer, scheduler,
    device, writer, global_step, max_steps, log_interval,
    checkpoint_dir, checkpoint_interval, config,
    mask_ratio=0.75, use_amp=True,
    viz_interval=0, viz_dir=None, viz_modality="S2L2A", viz_patch_size=16,
) -> int:
    """训练一个 epoch（达到 max_steps 即提前退出）。"""
    encoder.train()
    decoder.train()

    # 仅主进程显示进度条
    iterator = dataloader
    if is_main_process():
        iterator = tqdm(dataloader, desc=f"训练中 (step {global_step})")

    for batch in iterator:
        if global_step >= max_steps:
            break

        images = batch["image"].to(device)  # [B, C, H, W]

        optimizer.zero_grad()

        # bf16 混合精度：bf16 动态范围足够，无需 GradScaler，直接 autocast
        if use_amp:
            with autocast(device_type="cuda", dtype=torch.bfloat16):
                latent, mask, ids_restore = encoder(images, mask_ratio=mask_ratio)
                pred = decoder(latent, ids_restore, mask)
                loss = loss_fn(pred, images, mask)
        else:
            latent, mask, ids_restore = encoder(images, mask_ratio=mask_ratio)
            pred = decoder(latent, ids_restore, mask)
            loss = loss_fn(pred, images, mask)

        loss.backward()
        optimizer.step()
        scheduler.step()

        global_step += 1

        # 日志（仅主进程）
        if global_step % log_interval == 0:
            current_lr = scheduler.get_last_lr()[0]
            if writer is not None:
                writer.add_scalar("train/loss", loss.item(), global_step)
                writer.add_scalar("train/lr", current_lr, global_step)
            if is_main_process():
                if hasattr(iterator, "set_postfix"):
                    iterator.set_postfix({"loss": f"{loss.item():.4f}", "lr": f"{current_lr:.6f}"})
                log_main(f"Step {global_step}/{max_steps} | Loss: {loss.item():.4f} | LR: {current_lr:.6f}")

        # 保存 checkpoint（save_checkpoint 内部仅 rank 0 写盘）
        if global_step % checkpoint_interval == 0:
            save_checkpoint(checkpoint_dir, global_step, model, encoder, decoder, optimizer, config)

        # 可视化重建（forward 必须所有 rank 都跑以对齐 FSDP all-gather；仅主进程写盘）
        if viz_interval > 0 and global_step % viz_interval == 0:
            is_main = is_main_process()
            viz_path = os.path.join(viz_dir, f"recon_step_{global_step}.png") if is_main else None
            try:
                save_reconstruction_grid(
                    encoder, decoder, batch, viz_path, global_step,
                    modality=viz_modality, patch_size=viz_patch_size,
                    n_samples=4, mask_ratio=mask_ratio, writer=writer,
                    render=is_main,
                )
                if is_main:
                    log_main(f"已保存重建可视化: {viz_path}")
            except Exception as e:
                log_main(f"[警告] 可视化失败 (不影响训练): {e}")

        if global_step >= max_steps:
            break

    return global_step


def main():
    parser = argparse.ArgumentParser(description="Stage 1 观测编码器 MAE 预训练")
    parser.add_argument("--config", type=str, required=True, help="训练配置 YAML 路径")
    parser.add_argument("--max-steps", type=int, default=None, help="最大训练步数（覆盖配置）")
    parser.add_argument("--checkpoint-interval", type=int, default=None, help="每多少步存一次 checkpoint")
    parser.add_argument("--mask-ratio", type=float, default=0.75, help="MAE 掩码比例")
    parser.add_argument("--viz-interval", type=int, default=0,
                        help="每多少步存一张重建可视化图（0=关闭，建议 200-500）")
    parser.add_argument("--resume", type=str, default=None,
                        help="从已有 checkpoint 继续训练的路径（如 checkpoints/long_run/checkpoint_step_10000.pt）")
    args = parser.parse_args()

    # ---------- 1. 初始化分布式环境（torchrun 启动时生效，否则单卡） ----------
    rank, local_rank, world_size, distributed = setup_distributed()

    # ---------- 2. 加载配置 ----------
    config = load_config(args.config)
    if args.max_steps is not None:
        config["max_steps"] = args.max_steps
    max_steps = config.get("max_steps", 10)
    checkpoint_interval = args.checkpoint_interval or max_steps

    # ---------- 3. 设备 ----------
    if torch.cuda.is_available():
        device = torch.device(f"cuda:{local_rank}")
    else:
        device = torch.device("cpu")

    log_main("=" * 60)
    log_main(f"运行模式: {'多卡 FSDP (world_size=%d)' % world_size if distributed else '单卡'}")
    log_main(f"当前进程: rank={rank}, local_rank={local_rank}, device={device}")
    log_main("=" * 60)

    # ---------- 4. 创建模型并搬到对应 GPU ----------
    encoder, decoder = create_model(config["model"])
    encoder = encoder.to(device)
    decoder = decoder.to(device)

    raw_param_count = sum(p.numel() for p in encoder.parameters()) + \
                      sum(p.numel() for p in decoder.parameters())
    log_main(f"模型总参数量: {raw_param_count / 1e6:.2f}M")

    # ---------- 4.5. Resume 模型权重（必须在 FSDP 包装前加载，避免 Tensor/DTensor 混合） ----------
    resume_ckpt = None
    global_step_start = 0
    if args.resume:
        if not os.path.exists(args.resume):
            log_main(f"[错误] resume checkpoint 不存在: {args.resume}")
            cleanup_distributed()
            return
        log_main(f"\n从 checkpoint 恢复权重: {args.resume}")
        resume_ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        encoder.load_state_dict(resume_ckpt["encoder_state_dict"])
        decoder.load_state_dict(resume_ckpt["decoder_state_dict"])
        global_step_start = resume_ckpt.get("global_step", 0)
        log_main(f"已加载模型权重，global_step={global_step_start}（优化器状态将在创建优化器后加载）")

    # ---------- 5. FSDP2 包装（仅多卡模式） ----------
    if distributed:
        precision = config.get("precision", "bf16")
        encoder = wrap_model_fsdp2(encoder, mixed_precision=precision)
        decoder = wrap_model_fsdp2(decoder, mixed_precision=precision)

        # 诊断：证明参数已被分片成 DTensor，每卡只持有一部分
        from torch.distributed.tensor import DTensor
        sample_param = next(encoder.parameters())
        is_sharded = isinstance(sample_param, DTensor)
        local_numel = sum(
            p.to_local().numel() if isinstance(p, DTensor) else p.numel()
            for p in list(encoder.parameters()) + list(decoder.parameters())
        )
        log_main(f"[FSDP 诊断] 参数已分片为 DTensor: {is_sharded}")
        log_main(f"[FSDP 诊断] 全量参数 {raw_param_count/1e6:.2f}M | "
                 f"本卡(rank {rank})本地持有 {local_numel/1e6:.2f}M "
                 f"(约 1/{world_size})")

    # 用 ModuleDict 统一管理 encoder/decoder，便于优化器状态汇聚建立 FQN 映射
    model = nn.ModuleDict({"encoder": encoder, "decoder": decoder})

    # ---------- 6. 数据 ----------
    log_main("初始化数据模块...")
    datamodule = create_datamodule(config["data"])
    datamodule.setup("fit")
    train_loader = datamodule.train_dataloader()

    # ---------- 7. 损失 / 优化器 / 调度器（优化器必须在 FSDP 包装之后创建） ----------
    loss_type = config.get("loss_type", "masked_mse")
    loss_fn = get_reconstruction_loss(loss_type)
    log_main(f"重建损失: {loss_type}")

    learning_rate = float(config.get("learning_rate", 1e-4))
    weight_decay = float(config.get("weight_decay", 0.05))
    params = list(encoder.parameters()) + list(decoder.parameters())
    optimizer = torch.optim.AdamW(params, lr=learning_rate, weight_decay=weight_decay)
    log_main(f"优化器: AdamW (lr={learning_rate}, weight_decay={weight_decay})")

    warmup_steps = config.get("warmup_steps", 0)

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, max_steps - warmup_steps)
        return 0.5 * (1 + torch.cos(torch.tensor(progress * 3.14159265359)).item())

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    log_main(f"学习率调度: warmup={warmup_steps} + 余弦退火, max_steps={max_steps}")

    # ---------- 7.5. Resume 优化器状态（如果有 resume） ----------
    global_step = 0
    if resume_ckpt is not None:
        # FSDP 模式下优化器参数是 DTensor，必须用 set_full_optim_state_dict 把完整状态
        # 正确分片成 DTensor，否则 step() 时 Adam 会遇到 Tensor/DTensor 混合而崩溃
        set_full_optim_state_dict(model, optimizer, resume_ckpt["optimizer_state_dict"])
        global_step = global_step_start
        # scheduler 需要同步到相应步数（LambdaLR 没有 load_state_dict，手动 step）
        for _ in range(global_step):
            scheduler.step()
        log_main(f"已加载优化器状态，将从 step {global_step+1} 继续训练")

    # ---------- 8. 日志 / checkpoint 目录（仅主进程建 TensorBoard） ----------
    log_dir = config.get("log_dir", "./logs")
    checkpoint_dir = config.get("checkpoint_dir", "./checkpoints")
    viz_dir = os.path.join(log_dir, "reconstructions")
    writer = None
    if is_main_process():
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(checkpoint_dir, exist_ok=True)
        if args.viz_interval > 0:
            os.makedirs(viz_dir, exist_ok=True)
            log_main(f"重建可视化目录: {viz_dir} (每 {args.viz_interval} 步)")
        if TENSORBOARD_AVAILABLE:
            writer = SummaryWriter(log_dir)
            log_main(f"TensorBoard 日志目录: {log_dir}")

    use_amp = config.get("precision", "bf16") == "bf16"
    log_main(f"混合精度: {'bf16' if use_amp else 'fp32'}")
    log_main(f"\n开始训练，共 {max_steps} 步，掩码比例 {args.mask_ratio}")
    log_main("=" * 60)

    # ---------- 10. 训练循环 ----------
    global_step = 0
    log_interval = config.get("log_interval", 2)
    while global_step < max_steps:
        global_step = train_one_epoch(
            model, encoder, decoder, train_loader, loss_fn, optimizer, scheduler,
            device, writer, global_step, max_steps, log_interval,
            checkpoint_dir, checkpoint_interval, config,
            mask_ratio=args.mask_ratio, use_amp=use_amp,
            viz_interval=args.viz_interval, viz_dir=viz_dir,
            viz_modality=config["data"].get("modality", "S2L2A"),
            viz_patch_size=config["model"]["encoder"].get("patch_size", 16),
        )

    # ---------- 10. 收尾：保存最终 checkpoint + 清理分布式 ----------
    log_main("\n训练完成！")
    save_checkpoint(checkpoint_dir, global_step, model, encoder, decoder, optimizer, config)
    if writer is not None:
        writer.close()
    log_main(f"最终 checkpoint 已保存于 step {global_step}")

    cleanup_distributed()


if __name__ == "__main__":
    main()

