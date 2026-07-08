"""
编码器-解码器 集成测试

用随机张量验证 MAE 完整管线：编码（带掩码）-> 解码 -> 重建。
不依赖真实数据，可快速确认模型结构的形状是否自洽。
"""

import sys
from pathlib import Path

import torch

# 把项目根目录加入 import 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.encoders.tiny_vit_encoder import TinyViTEncoder, DEFAULT_CONFIG_S2L2A
from models.decoders.light_decoder import LightDecoder, DEFAULT_DECODER_CONFIG_S2L2A


def test_mae_pipeline():
    """测试完整 MAE 管线：带掩码编码 -> 解码重建。"""
    print("=" * 60)
    print("测试 MAE 管线 (编码器 + 解码器)")
    print("=" * 60)

    # 创建编码器和解码器
    encoder = TinyViTEncoder(**DEFAULT_CONFIG_S2L2A)
    decoder = LightDecoder(**DEFAULT_DECODER_CONFIG_S2L2A)

    # 输入：S2L2A 影像（随机张量，仅验证形状）
    B, C, H, W = 2, 12, 224, 224
    x_input = torch.randn(B, C, H, W)

    print(f"\n输入形状: {x_input.shape}")

    # 以 75% 掩码比例编码
    mask_ratio = 0.75
    tokens, mask, ids_restore = encoder(x_input, mask_ratio=mask_ratio)

    print(f"编码器输出 (可见 token): {tokens.shape}")
    print(f"掩码形状: {mask.shape}, 被掩 patch 数: {mask.sum(dim=1).tolist()}")
    print(f"ids_restore 形状: {ids_restore.shape}")

    # 解码重建
    x_recon = decoder(tokens, ids_restore, mask)

    print(f"解码器输出 (重建图像): {x_recon.shape}")
    print(f"重建形状与输入一致: {x_recon.shape == x_input.shape}")

    # 计算重建误差（MSE，未训练状态仅供参考）
    mse = torch.nn.functional.mse_loss(x_recon, x_input)
    print(f"\n重建 MSE (未训练): {mse.item():.4f}")

    assert x_recon.shape == x_input.shape, "重建形状与输入不一致！"

    print("\n" + "=" * 60)
    print("集成测试通过！")
    print("=" * 60)


if __name__ == '__main__':
    test_mae_pipeline()
