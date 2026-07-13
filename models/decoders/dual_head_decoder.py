"""
双头解码器：分别重建 S1 和 S2。

从 decoder-space latent tokens 重建双模态图像。Stage 1.5 中这些 token
由显式 state bottleneck 经过 StateReconstructionBridge 投影得到。
支持模态内 MAE 重建（S1→S1, S2→S2）。
"""

import torch
import torch.nn as nn
from typing import Optional, Tuple

from .light_decoder import LightDecoder


class DualHeadDecoder(nn.Module):
    """
    双头解码器：S1 重建头 + S2 重建头。

    Args:
        in_dim: decoder 输入 token 维度
        s1_channels: S1 输出通道数（2: VV/VH）
        s2_channels: S2 输出通道数（12: S2L2A bands）
        patch_size: patch 尺寸
        img_size: 输出图像尺寸
        decoder_embed_dim: 解码器内部维度
        depth: 解码器块数量
        num_heads: attention 头数
        decoder_mode: 'transformer' 或 'conv'
    """

    def __init__(
        self,
        in_dim: int = 256,
        s1_channels: int = 2,
        s2_channels: int = 12,
        patch_size: int = 16,
        img_size: int = 256,
        decoder_embed_dim: int = 128,
        depth: int = 2,
        num_heads: int = 4,
        mlp_ratio: float = 4.0,
        dropout: float = 0.0,
        decoder_mode: str = 'transformer',
        phi_dim: Optional[int] = None,
    ):
        super().__init__()

        self.in_dim = in_dim
        self.s1_channels = s1_channels
        self.s2_channels = s2_channels
        self.phi_dim = phi_dim

        # S1 解码器
        self.s1_decoder = LightDecoder(
            in_dim=in_dim,
            out_channels=s1_channels,
            patch_size=patch_size,
            img_size=img_size,
            depth=depth,
            num_heads=num_heads,
            decoder_embed_dim=decoder_embed_dim,
            mlp_ratio=mlp_ratio,
            dropout=dropout,
            decoder_mode=decoder_mode,
            phi_dim=phi_dim,
        )

        # S2 解码器
        self.s2_decoder = LightDecoder(
            in_dim=in_dim,
            out_channels=s2_channels,
            patch_size=patch_size,
            img_size=img_size,
            depth=depth,
            num_heads=num_heads,
            decoder_embed_dim=decoder_embed_dim,
            mlp_ratio=mlp_ratio,
            dropout=dropout,
            decoder_mode=decoder_mode,
            phi_dim=phi_dim,
        )

    def forward(
        self,
        x: torch.Tensor,
        modality: str,
        ids_restore: Optional[torch.Tensor] = None,
        mask: Optional[torch.Tensor] = None,
        phi_embed: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        从 latent tokens 重建图像。

        Args:
            x: [B, N_visible, in_dim] decoder-space tokens
            modality: 'S1' 或 'S2'（决定用哪个解码头）
            ids_restore: [B, N_total] 恢复索引
            mask: [B, N_total] 二值掩码
            phi_embed: [B, phi_dim] 成像条件（方案 A：注入 decoder）

        Returns:
            [B, C, H, W] 重建后的图像
        """
        if modality == 'S1':
            return self.s1_decoder(x, ids_restore, mask, phi_embed=phi_embed)
        elif modality == 'S2':
            return self.s2_decoder(x, ids_restore, mask, phi_embed=phi_embed)
        else:
            raise ValueError(f"Unknown modality: {modality}")

    def get_config(self) -> dict:
        """返回配置字典。"""
        return {
            'in_dim': self.in_dim,
            's1_channels': self.s1_channels,
            's2_channels': self.s2_channels,
            's1_decoder_config': self.s1_decoder.get_config(),
            's2_decoder_config': self.s2_decoder.get_config(),
        }


def create_dual_head_decoder(**kwargs) -> DualHeadDecoder:
    """工厂函数。"""
    return DualHeadDecoder(**kwargs)


# 默认配置
DEFAULT_DECODER_CONFIG_DUAL = {
    'in_dim': 256,
    's1_channels': 2,
    's2_channels': 12,
    'patch_size': 16,
    'img_size': 256,
    'decoder_embed_dim': 128,
    'depth': 2,
    'num_heads': 4,
    'mlp_ratio': 4.0,
    'dropout': 0.0,
    'decoder_mode': 'transformer',
}


if __name__ == '__main__':
    # 测试双头解码器
    print("测试双头解码器...")
    decoder = DualHeadDecoder(**DEFAULT_DECODER_CONFIG_DUAL)

    B, N_total, N_visible = 2, 256, 64
    in_dim = 256

    x_visible = torch.randn(B, N_visible, in_dim)
    ids_restore = torch.randperm(N_total).unsqueeze(0).expand(B, -1)
    mask = torch.ones(B, N_total)
    mask[:, :N_visible] = 0

    # 重建 S1
    img_s1_recon = decoder(x_visible, modality='S1', ids_restore=ids_restore, mask=mask)
    print(f"S1 重建 shape: {img_s1_recon.shape}")
    print(f"  预期: [2, 2, 256, 256], 实际: {list(img_s1_recon.shape)}")

    # 重建 S2
    img_s2_recon = decoder(x_visible, modality='S2', ids_restore=ids_restore, mask=mask)
    print(f"S2 重建 shape: {img_s2_recon.shape}")
    print(f"  预期: [2, 12, 256, 256], 实际: {list(img_s2_recon.shape)}")

    # 参数量
    total_params = sum(p.numel() for p in decoder.parameters()) / 1e6
    print(f"\n双头解码器参数量: {total_params:.2f}M")
