"""
多模态 Vision Transformer 编码器（支持 S1 SAR + S2 光学融合）。

架构 B 实现：
- 各模态独立的 patch embedding 层
- 可学习的 modality embedding
- 共享 Transformer 编码器
- 支持 MAE 随机掩码

适用于遥感双模态预训练（S1GRD + S2L2A）。
"""

import torch
import torch.nn as nn
import math
from typing import Optional, Tuple, Dict

from .tiny_vit_encoder import TransformerBlock


class MultiModalPatchEmbed(nn.Module):
    """多模态 patch embedding：S1 和 S2 各自投影到统一维度。"""

    def __init__(
        self,
        img_size: int = 256,
        patch_size: int = 16,
        s1_channels: int = 2,
        s2_channels: int = 12,
        embed_dim: int = 256,
    ):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.num_patches = (img_size // patch_size) ** 2

        # S1 GRD 投影（2 通道 SAR）
        self.s1_proj = nn.Conv2d(
            s1_channels, embed_dim,
            kernel_size=patch_size, stride=patch_size
        )

        # S2 L2A 投影（12 通道光学）
        self.s2_proj = nn.Conv2d(
            s2_channels, embed_dim,
            kernel_size=patch_size, stride=patch_size
        )

    def forward(self, x: torch.Tensor, modality: str) -> torch.Tensor:
        """
        Args:
            x: [B, C, H, W] 输入图像
            modality: 'S1' 或 'S2'

        Returns:
            [B, N_patches, embed_dim] patch tokens
        """
        if modality == 'S1':
            x = self.s1_proj(x)  # [B, embed_dim, H', W']
        elif modality == 'S2':
            x = self.s2_proj(x)
        else:
            raise ValueError(f"Unknown modality: {modality}")

        B, D, H, W = x.shape
        x = x.flatten(2).transpose(1, 2)  # [B, N_patches, embed_dim]
        return x


class MultiModalViTEncoder(nn.Module):
    """
    双模态 ViT 编码器：S1 + S2 → 共享 Transformer。

    Args:
        img_size: 输入图像尺寸（正方形）
        s1_channels: S1 通道数（默认 2: VV/VH）
        s2_channels: S2 通道数（默认 12: S2L2A bands）
        patch_size: 每个 patch 的尺寸
        embed_dim: 嵌入维度
        depth: Transformer 块数量
        num_heads: 注意力头数
        mlp_ratio: MLP 隐藏层维度比例
        dropout: Dropout 比率
    """

    def __init__(
        self,
        img_size: int = 256,
        s1_channels: int = 2,
        s2_channels: int = 12,
        patch_size: int = 16,
        embed_dim: int = 256,
        depth: int = 6,
        num_heads: int = 4,
        mlp_ratio: float = 4.0,
        dropout: float = 0.0,
    ):
        super().__init__()

        self.img_size = img_size
        self.patch_size = patch_size
        self.embed_dim = embed_dim
        self.depth = depth
        self.num_heads = num_heads

        # 多模态 patch embedding
        self.patch_embed = MultiModalPatchEmbed(
            img_size, patch_size,
            s1_channels, s2_channels,
            embed_dim
        )
        num_patches = self.patch_embed.num_patches

        # 位置嵌入（共享，spatial structure）
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches, embed_dim))

        # 模态嵌入（可学习，区分 S1/S2）
        self.modality_embed_s1 = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.modality_embed_s2 = nn.Parameter(torch.zeros(1, 1, embed_dim))

        self.pos_drop = nn.Dropout(dropout)

        # 共享 Transformer 块
        self.blocks = nn.ModuleList([
            TransformerBlock(embed_dim, num_heads, mlp_ratio, dropout)
            for _ in range(depth)
        ])

        self.norm = nn.LayerNorm(embed_dim)

        # 初始化权重
        self._init_weights()

    def _init_weights(self):
        """初始化位置嵌入和模态嵌入。"""
        nn.init.trunc_normal_(self.pos_embed, std=0.02)
        nn.init.trunc_normal_(self.modality_embed_s1, std=0.02)
        nn.init.trunc_normal_(self.modality_embed_s2, std=0.02)

        self.apply(self._init_module_weights)

    def _init_module_weights(self, m):
        """初始化线性层和卷积层的权重。"""
        if isinstance(m, nn.Linear):
            nn.init.trunc_normal_(m.weight, std=0.02)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode='fan_out')
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.weight, 1.0)
            nn.init.constant_(m.bias, 0)

    def random_masking(
        self,
        x: torch.Tensor,
        mask_ratio: float = 0.75
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        对 patch tokens 执行随机掩码。

        Args:
            x: [B, N, D] patch tokens
            mask_ratio: 需要掩码的 patch 比例

        Returns:
            x_masked: [B, N*(1-mask_ratio), D] 可见 patch
            mask: [B, N] 二值掩码（1=保留，0=掩码）
            ids_restore: [B, N] 用于恢复原始顺序的索引
        """
        B, N, D = x.shape
        len_keep = int(N * (1 - mask_ratio))

        noise = torch.rand(B, N, device=x.device)
        ids_shuffle = torch.argsort(noise, dim=1)
        ids_restore = torch.argsort(ids_shuffle, dim=1)

        ids_keep = ids_shuffle[:, :len_keep]
        x_masked = torch.gather(x, dim=1, index=ids_keep.unsqueeze(-1).expand(-1, -1, D))

        mask = torch.ones([B, N], device=x.device)
        mask[:, :len_keep] = 0
        mask = torch.gather(mask, dim=1, index=ids_restore)

        return x_masked, mask, ids_restore

    def forward(
        self,
        x: torch.Tensor,
        modality: str,
        mask_ratio: Optional[float] = None
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        前向传播，支持单模态输入。

        Args:
            x: [B, C, H, W] 输入图像
            modality: 'S1' 或 'S2'
            mask_ratio: 若提供，则应用随机掩码

        Returns:
            tokens: [B, N_visible, embed_dim] patch tokens
            mask: [B, N] 二值掩码（若提供 mask_ratio）
            ids_restore: [B, N] 恢复索引（若提供 mask_ratio）
        """
        # Patch embedding
        x = self.patch_embed(x, modality)  # [B, N, embed_dim]

        # 加位置嵌入
        x = x + self.pos_embed

        # 加模态嵌入
        if modality == 'S1':
            x = x + self.modality_embed_s1
        elif modality == 'S2':
            x = x + self.modality_embed_s2
        else:
            raise ValueError(f"Unknown modality: {modality}")

        # 若指定则应用掩码
        mask = None
        ids_restore = None
        if mask_ratio is not None and mask_ratio > 0:
            x, mask, ids_restore = self.random_masking(x, mask_ratio)

        x = self.pos_drop(x)

        # 共享 Transformer 块
        for block in self.blocks:
            x = block(x)

        x = self.norm(x)

        return x, mask, ids_restore

    def get_num_patches(self) -> int:
        """返回 patch 的总数量。"""
        return self.patch_embed.num_patches

    def get_config(self) -> dict:
        """返回配置字典。"""
        return {
            'img_size': self.img_size,
            'patch_size': self.patch_size,
            'embed_dim': self.embed_dim,
            'depth': self.depth,
            'num_heads': self.num_heads,
        }


def create_multimodal_vit_encoder(**kwargs) -> MultiModalViTEncoder:
    """工厂函数，用于创建多模态 ViT 编码器。"""
    return MultiModalViTEncoder(**kwargs)


# 默认配置
DEFAULT_CONFIG_DUAL = {
    'img_size': 256,
    's1_channels': 2,   # S1 GRD: VV/VH
    's2_channels': 12,  # S2 L2A: 12 bands
    'patch_size': 16,
    'embed_dim': 256,
    'depth': 6,
    'num_heads': 4,
    'mlp_ratio': 4.0,
    'dropout': 0.1,
}


if __name__ == '__main__':
    # 测试双模态编码器
    print("测试双模态 ViT 编码器...")
    encoder = MultiModalViTEncoder(**DEFAULT_CONFIG_DUAL)

    # 测试 S1 输入
    x_s1 = torch.randn(2, 2, 256, 256)
    tokens_s1, mask_s1, ids_restore_s1 = encoder(x_s1, modality='S1', mask_ratio=0.75)
    print(f"S1 输出 shape (75% 掩码): {tokens_s1.shape}")
    print(f"  Mask shape: {mask_s1.shape}, 掩码 patches: {mask_s1.sum(dim=1)}")

    # 测试 S2 输入
    x_s2 = torch.randn(2, 12, 256, 256)
    tokens_s2, mask_s2, ids_restore_s2 = encoder(x_s2, modality='S2', mask_ratio=0.75)
    print(f"S2 输出 shape (75% 掩码): {tokens_s2.shape}")

    # 参数量
    total_params = sum(p.numel() for p in encoder.parameters()) / 1e6
    print(f"\n多模态编码器参数量: {total_params:.2f}M")
