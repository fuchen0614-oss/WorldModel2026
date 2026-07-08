"""
双模态（S1 GRD + S2 L2A）Stage 1 MAE 预训练。

训练策略：
- 交替训练：每个 batch 随机选择 S1 或 S2 其中一个模态
- 模态内 MAE：S1 → S1 重建，S2 → S2 重建
- 共享编码器 + 双头解码器

支持 FSDP 分布式训练。
"""

import argparse
import os
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.cuda.amp import autocast  # 删除这行，下面直接用 torch.cuda.amp.autocast
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm
import yaml

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.datasets.ssl4eo_simple import create_simple_dual_dataloader
from models.encoders.multimodal_vit_encoder import MultiModalViTEncoder
from models.decoders.dual_head_decoder import DualHeadDecoder
from models.losses.reconstruction import MaskedL1Loss, MaskedMSELoss
from train.fsdp_utils import (
    setup_distributed, wrap_model_fsdp2, is_main_process, is_distributed,
    barrier, cleanup_distributed, get_full_state_dict, get_full_optim_state_dict,
    set_full_optim_state_dict
)


def log_main(msg: str):
    """仅主进程打印日志。"""
    if is_main_process():
        print(msg)


def load_config(config_path: str) -> dict:
    """加载 YAML 配置文件。"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def create_model(config: dict) -> tuple:
    """创建多模态编码器和双头解码器。"""
    encoder_cfg = config['model']['encoder']
    decoder_cfg = config['model']['decoder']

    encoder = MultiModalViTEncoder(**encoder_cfg)
    decoder = DualHeadDecoder(**decoder_cfg)

    return encoder, decoder


def save_checkpoint(
    checkpoint_dir, global_step,
    model, encoder, decoder, optimizer, config
):
    """保存 checkpoint（encoder + decoder + optimizer）。"""
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
    model, encoder, decoder, dataloader, loss_fn_dict, optimizer, scheduler,
    device, writer, global_step, max_steps, log_interval,
    checkpoint_dir, checkpoint_interval, config,
    mask_ratio=0.75, use_amp=True,
    s1_weight=1.0, s2_weight=1.0,
) -> int:
    """训练一个 epoch（交替模态训练）。"""
    encoder.train()
    decoder.train()

    iterator = dataloader
    if is_main_process():
        iterator = tqdm(dataloader, desc=f"训练中 (step {global_step})")

    # 追踪每个模态最近一次的 loss（避免固定间隔采样只抓到一个模态）
    last_loss = {'S1': None, 'S2': None}

    for batch in iterator:
        if global_step >= max_steps:
            break

        # 选择训练模态。
        # 关键：必须所有 rank 同步选择同一模态，否则 FSDP 各卡 forward
        # 走不同分支（S1/S2 的 patch_embed 和 decoder 不同），
        # all-gather 的参数集合不一致 → 集合通信死锁。
        # 用 global_step 奇偶确定性交替，保证全卡一致。
        # 根据配置决定训练模态（支持单模态/双模态灵活切换）
        training_mode = config.get('training_mode', 'dual')  # 'dual', 's1_only', 's2_only'

        if training_mode == 's1_only':
            modality = 'S1'
        elif training_mode == 's2_only':
            modality = 'S2'
        else:  # dual
            modality = 'S1' if (global_step % 2 == 0) else 'S2'

        if modality == 'S1':
            images = batch['s1_image'].to(device)  # [B, 2, H, W]
            loss_weight = s1_weight
        else:  # S2
            images = batch['s2_image'].to(device)  # [B, 12, H, W]
            loss_weight = s2_weight

        optimizer.zero_grad()

        # bf16 混合精度
        if use_amp:
            with torch.cuda.amp.autocast(dtype=torch.bfloat16):
                # Encoder forward
                latent, mask, ids_restore = encoder(images, modality=modality, mask_ratio=mask_ratio)
                # Decoder forward
                pred = decoder(latent, modality=modality, ids_restore=ids_restore, mask=mask)
                # Loss（仅在掩码 patch 上计算）
                loss_fn = loss_fn_dict[modality]
                loss = loss_fn(pred, images, mask) * loss_weight
        else:
            latent, mask, ids_restore = encoder(images, modality=modality, mask_ratio=mask_ratio)
            pred = decoder(latent, modality=modality, ids_restore=ids_restore, mask=mask)
            loss_fn = loss_fn_dict[modality]
            loss = loss_fn(pred, images, mask) * loss_weight

        loss.backward()
        optimizer.step()
        scheduler.step()

        global_step += 1

        # 记录当前模态最近一次 loss
        last_loss[modality] = loss.item()

        # 每步都把当前模态的 loss 写入 TensorBoard（各自标签，互不覆盖）
        if writer is not None:
            writer.add_scalar(f"train/loss_{modality}", loss.item(), global_step)

        # 按间隔打印：同时展示 S1 和 S2 的最新 loss
        if global_step % log_interval == 0:
            current_lr = scheduler.get_last_lr()[0]
            if writer is not None:
                writer.add_scalar("train/lr", current_lr, global_step)
            if is_main_process():
                s1_str = f"{last_loss['S1']:.4f}" if last_loss['S1'] is not None else "N/A"
                s2_str = f"{last_loss['S2']:.4f}" if last_loss['S2'] is not None else "N/A"
                if hasattr(iterator, "set_postfix"):
                    iterator.set_postfix({
                        "S1": s1_str,
                        "S2": s2_str,
                        "lr": f"{current_lr:.6f}"
                    })
                log_main(f"Step {global_step}/{max_steps} | "
                         f"Loss_S1: {s1_str} | Loss_S2: {s2_str} | LR: {current_lr:.6f}")

        # 保存 checkpoint
        if global_step % checkpoint_interval == 0:
            save_checkpoint(checkpoint_dir, global_step, model, encoder, decoder, optimizer, config)

        if global_step >= max_steps:
            break

    return global_step


def main():
    parser = argparse.ArgumentParser(description="Stage 1 双模态 MAE 预训练")
    parser.add_argument("--config", type=str, required=True, help="训练配置 YAML 路径")
    parser.add_argument("--max-steps", type=int, default=None, help="最大训练步数（覆盖配置）")
    parser.add_argument("--checkpoint-interval", type=int, default=None, help="checkpoint 间隔")
    parser.add_argument("--mask-ratio", type=float, default=0.75, help="掩码比例")
    args = parser.parse_args()

    # 1. 初始化分布式
    rank, local_rank, world_size, distributed = setup_distributed()

    # 2. 加载配置
    config = load_config(args.config)
    if args.max_steps is not None:
        config["max_steps"] = args.max_steps
    max_steps = config.get("max_steps", 10000)
    checkpoint_interval = args.checkpoint_interval or max_steps

    # 3. 设备
    if torch.cuda.is_available():
        device = torch.device(f"cuda:{local_rank}")
    else:
        device = torch.device("cpu")

    log_main("=" * 60)
    log_main(f"双模态 Stage 1 MAE 预训练")
    log_main(f"  配置文件: {args.config}")
    log_main(f"  分布式: {distributed}, Rank: {rank}/{world_size}")
    log_main(f"  设备: {device}")
    log_main(f"  最大步数: {max_steps}")
    log_main("=" * 60)

    # 4. 创建模型
    encoder, decoder = create_model(config)
    encoder.to(device)
    decoder.to(device)

    log_main(f"编码器参数量: {sum(p.numel() for p in encoder.parameters()) / 1e6:.2f}M")
    log_main(f"解码器参数量: {sum(p.numel() for p in decoder.parameters()) / 1e6:.2f}M")

    # 5. FSDP 包装
    if distributed:
        encoder = wrap_model_fsdp2(encoder, mixed_precision="bf16")
        decoder = wrap_model_fsdp2(decoder, mixed_precision="bf16")

    # ModuleDict 用于优化器状态汇聚
    model = nn.ModuleDict({"encoder": encoder, "decoder": decoder})

    # 6. 数据加载器（使用简化版 DataLoader）
    data_cfg = config['data']
    dataloader = create_simple_dual_dataloader(
        data_root=data_cfg.get("data_root"),
        split=data_cfg.get("split", "train"),
        batch_size=data_cfg.get("batch_size", 64),
        num_workers=data_cfg.get("num_workers", 8),
        random_season=data_cfg.get("random_season", True),
        normalize=data_cfg.get("normalize", True),
        infinite=distributed,
        prefetch_factor=data_cfg.get("prefetch_factor", 4),
        seed=local_rank,   # 各 rank 使用不同 seed，保证样本多样性
    )

    # 7. 优化器和调度器
    opt_cfg = config['optimizer']
    optimizer = optim.AdamW(
        model.parameters(),
        lr=opt_cfg.get("lr", 0.0001),
        weight_decay=opt_cfg.get("weight_decay", 0.05),
        betas=tuple(opt_cfg.get("betas", [0.9, 0.95])),
    )

    sched_cfg = config['scheduler']
    warmup_steps = sched_cfg.get("warmup_steps", 500)
    min_lr = sched_cfg.get("min_lr", 0.00001)

    def lr_lambda(step):
        if step < warmup_steps:
            return step / warmup_steps
        else:
            progress = (step - warmup_steps) / (max_steps - warmup_steps)
            return min_lr / opt_cfg['lr'] + (1 - min_lr / opt_cfg['lr']) * 0.5 * (1 + torch.cos(torch.tensor(progress * 3.14159)))

    scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # 8. Loss 函数
    loss_cfg = config.get('loss', {})
    loss_type = loss_cfg.get('loss_type', 'l1')
    if loss_type == 'l1':
        loss_fn_s1 = MaskedL1Loss()
        loss_fn_s2 = MaskedL1Loss()
    elif loss_type == 'mse':
        loss_fn_s1 = MaskedMSELoss()
        loss_fn_s2 = MaskedMSELoss()
    else:
        raise ValueError(f"Unknown loss_type: {loss_type}")

    loss_fn_dict = {'S1': loss_fn_s1, 'S2': loss_fn_s2}
    s1_weight = loss_cfg.get('s1_weight', 1.0)
    s2_weight = loss_cfg.get('s2_weight', 1.0)

    # 9. TensorBoard
    log_dir = config.get("log_dir", "logs/stage1_dual")
    writer = None
    if is_main_process():
        os.makedirs(log_dir, exist_ok=True)
        writer = SummaryWriter(log_dir)

    # 10. 训练循环
    checkpoint_dir = config.get("checkpoint_dir", "checkpoints/stage1_dual")
    log_interval = config.get("log_interval", 50)
    mask_ratio = args.mask_ratio

    global_step = 0
    log_main("开始训练...")
    global_step = train_one_epoch(
        model, encoder, decoder, dataloader,
        loss_fn_dict, optimizer, scheduler,
        device, writer, global_step, max_steps, log_interval,
        checkpoint_dir, checkpoint_interval, config,
        mask_ratio=mask_ratio, use_amp=True,
        s1_weight=s1_weight, s2_weight=s2_weight,
    )

    # 11. 最终 checkpoint
    if global_step >= max_steps:
        save_checkpoint(checkpoint_dir, global_step, model, encoder, decoder, optimizer, config)

    log_main("训练完成！")

    if writer is not None:
        writer.close()

    cleanup_distributed()


if __name__ == "__main__":
    main()
