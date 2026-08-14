"""
MAE 重建可视化工具

每隔若干步从 batch 中取出几个样本，把"原图 | 遮掩输入 | 重建"三联图存成 PNG
并写入 TensorBoard，用来直观判断模型是否真的在学。

设计要点：
- S2L2A 是 12 波段，可视化时取 RGB 等价的 3 个波段（B4=红, B3=绿, B2=蓝）
- 多卡 FSDP：所有 rank 都要调用以对齐 forward 的 all-gather 集合通信，
  但只有主进程 render=True 真正绘图/写盘（详见 save_reconstruction_grid 的 render 参数）
- 不参与训练计算图（torch.no_grad + detach）
"""

import os
from pathlib import Path

import numpy as np
import torch


# ---------------------------------------------------------------------------
# 中文字体配置
# ---------------------------------------------------------------------------
# matplotlib 默认字体（DejaVu Sans）不含中文字形，直接画中文会显示成方框「□」。
# 这里把随项目附带的思源黑体（Noto Sans CJK SC）注册给 matplotlib，保证标题、
# 列名等中文正常显示。字体文件放在 Agent 共享目录下，不随某一项目走。
# 可用环境变量 CJK_FONT_PATH 覆盖字体路径。
_CJK_FONT_CANDIDATES = [
    os.environ.get("CJK_FONT_PATH", ""),
    "/csy-mix02/cog8/zjliu17/Agent/assets/fonts/NotoSansCJKsc-Regular.otf",
]
_CJK_FONT_READY = False  # 进程内只配置一次


def setup_cjk_font() -> bool:
    """把中文字体注册给 matplotlib 并设为默认。返回是否成功找到中文字体。

    找不到中文字体时返回 False（调用方会退回英文标签，避免方框乱码）。
    """
    global _CJK_FONT_READY
    if _CJK_FONT_READY:
        return True

    import matplotlib
    matplotlib.use("Agg")  # 非交互后端
    from matplotlib import font_manager

    for path in _CJK_FONT_CANDIDATES:
        if path and os.path.isfile(path):
            try:
                font_manager.fontManager.addfont(path)
                font_name = font_manager.FontProperties(fname=path).get_name()
                matplotlib.rcParams["font.family"] = "sans-serif"
                matplotlib.rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
                matplotlib.rcParams["axes.unicode_minus"] = False  # 负号正常显示
                _CJK_FONT_READY = True
                return True
            except Exception:
                continue
    return False


# Sentinel-2 L2A 波段索引 → RGB
# SSL4EO 的 12 波段顺序: B01 B02 B03 B04 B05 B06 B07 B08 B8A B09 B11 B12
# RGB ≈ B04(红, idx=3) + B03(绿, idx=2) + B02(蓝, idx=1)
_S2L2A_RGB_IDX = [3, 2, 1]


def _to_rgb(image: torch.Tensor, modality: str) -> np.ndarray:
    """把单张多波段图转成可显示的 RGB numpy 数组 [H, W, 3]，范围 [0, 1]。"""
    image = image.detach().float().cpu()  # [C, H, W]

    if modality == "S2L2A":
        rgb = image[_S2L2A_RGB_IDX]  # [3, H, W]
    elif modality == "S2RGB":
        rgb = image[:3]
    else:
        # 其他模态：取前 3 通道（不一定好看，仅占位）
        rgb = image[:3] if image.shape[0] >= 3 else image[0:1].repeat(3, 1, 1)

    rgb = rgb.permute(1, 2, 0).numpy()  # [H, W, 3]
    # 已经在 [0,1] 范围（dataloader normalize=true），轻度增强对比度
    rgb = np.clip(rgb * 2.5, 0, 1)  # S2 反射率偏暗，乘 2.5 后看着自然
    return rgb


def _build_masked_input(image: torch.Tensor, mask: torch.Tensor, patch_size: int) -> torch.Tensor:
    """根据 patch-level mask 把被遮掉的 patch 涂成灰色，得到"模型实际看到"的图。

    Args:
        image: [C, H, W]
        mask: [N_patches] 1=被遮（不可见），0=保留（可见）
        patch_size: patch 边长
    Returns:
        [C, H, W] 被遮位置变灰
    """
    C, H, W = image.shape
    nh = H // patch_size
    nw = W // patch_size
    # mask: [N] -> [nh, nw] -> [H, W]
    m = mask.reshape(nh, nw)
    m = m.repeat_interleave(patch_size, dim=0).repeat_interleave(patch_size, dim=1)  # [H, W]
    m = m.unsqueeze(0).to(image.device).to(image.dtype)  # [1, H, W]

    # 灰色填充值（在 [0,1] 归一化空间里）
    gray_value = 0.5
    return image * (1 - m) + gray_value * m


@torch.no_grad()
def save_reconstruction_grid(
    encoder,
    decoder,
    batch: dict,
    output_path: str,
    step: int,
    modality: str = "S2L2A",
    patch_size: int = 16,
    n_samples: int = 4,
    mask_ratio: float = 0.75,
    writer=None,
    render: bool = True,
) -> None:
    """从一个 batch 中取 n_samples 张图，跑 encoder+decoder，存"原图|遮掩|重建"三联图。

    Args:
        encoder/decoder: 训练中的模型（FSDP 包装也兼容）
        batch: dataloader 出来的 batch（含 'image' 键）
        output_path: PNG 输出路径（render=False 时可为 None）
        step: 当前训练步数（写入文件名和 TensorBoard tag）
        modality: 'S2L2A' / 'S2RGB'，决定如何取 RGB 三通道
        patch_size: 与编码器一致
        n_samples: 可视化几张图
        mask_ratio: 与训练一致
        writer: TensorBoard writer（可为 None）
        render: 是否渲染绘图并写盘。FSDP 多卡下，所有 rank 都必须调用本函数
            以保证下面的 forward 集合通信（all-gather）在各 rank 间对齐，但只有
            主进程 render=True 真正画图/写盘，其余 rank render=False 仅跑 forward。
    """
    encoder_was_training = encoder.training
    decoder_was_training = decoder.training
    encoder.eval()
    decoder.eval()

    images = batch["image"]
    if images.dim() == 5:  # [B, T, C, H, W] —— 时序场景，取第 0 个时相
        images = images[:, 0]
    images = images[:n_samples]
    n = images.shape[0]
    device = next(encoder.parameters()).device
    images = images.to(device)

    # forward（与训练一致）
    # 关键：这一步在 FSDP 下会触发 all-gather 集合通信，必须【所有 rank 都执行】，
    # 否则各 rank 的集合操作序列错位，会让后续 checkpoint 的 all-gather 永久挂起
    # （NCCL watchdog 30 分钟超时崩溃）。绘图/写盘是纯本地操作，只在主进程做。
    latent, mask, ids_restore = encoder(images, mask_ratio=mask_ratio)
    pred = decoder(latent, ids_restore, mask)
    pred = pred.float()  # bf16 -> fp32 便于绘图

    if render and output_path is not None:
        import matplotlib
        matplotlib.use("Agg")  # 非交互后端
        import matplotlib.pyplot as plt

        # 配置中文字体；找不到则退回英文标签，避免方框乱码
        has_cjk = setup_cjk_font()
        if has_cjk:
            col_titles = ["原图", "遮掩输入", "重建"]
        else:
            col_titles = ["Original", "Masked", "Reconstructed"]

        # 画 n × 3 网格：每行一个样本，列依次是 原图 / 遮掩输入 / 重建
        fig, axes = plt.subplots(n, 3, figsize=(9, 3 * n))
        if n == 1:
            axes = axes[None, :]

        for i in range(n):
            original = _to_rgb(images[i], modality)
            masked_input = _to_rgb(_build_masked_input(images[i], mask[i], patch_size), modality)
            reconstructed = _to_rgb(pred[i], modality)

            for j, img in enumerate([original, masked_input, reconstructed]):
                axes[i, j].imshow(img)
                axes[i, j].axis("off")
                if i == 0:
                    axes[i, j].set_title(col_titles[j], fontsize=12)

        fig.suptitle(f"Step {step} | mask_ratio={mask_ratio} | modality={modality}", fontsize=11)
        fig.tight_layout()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=80, bbox_inches="tight")

        # 写入 TensorBoard
        if writer is not None:
            fig.canvas.draw()
            # matplotlib 3.x: 用 buffer_rgba() 取像素
            buf = np.asarray(fig.canvas.buffer_rgba())[..., :3]  # [H, W, 3]
            # tensorboard 需要 [3, H, W]
            writer.add_image("recon/grid", buf.transpose(2, 0, 1), step)

        plt.close(fig)

    # 恢复训练模式（所有 rank）
    if encoder_was_training:
        encoder.train()
    if decoder_was_training:
        decoder.train()
