"""
用于掩码自编码（Masked Autoencoding）的轻量级 Vision Transformer（ViT）风格编码器。

支持多光谱卫星影像（12 通道的 S2L2A）或 RGB（3 通道）。
"""

import torch
import torch.nn as nn
import math
from typing import Optional, Tuple


class PatchEmbed(nn.Module):
    """使用 2D 卷积将图像转换为 Patch Embedding。"""

    def __init__(self, img_size: int = 224, patch_size: int = 16, in_channels: int = 3, embed_dim: int = 256):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.num_patches = (img_size // patch_size) ** 2

        # Conv2d 投影
        self.proj = nn.Conv2d(in_channels, embed_dim, kernel_size=patch_size, stride=patch_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, C, H, W]
        Returns:
            [B, N_patches, embed_dim]
        """
        B, C, H, W = x.shape
        x = self.proj(x)  # [B, embed_dim, H', W']
        x = x.flatten(2)  # [B, embed_dim, N_patches]
        x = x.transpose(1, 2)  # [B, N_patches, embed_dim]
        return x


class MultiHeadAttention(nn.Module):
    """多头自注意力（Multi-head self-attention）。"""

    def __init__(self, embed_dim: int, num_heads: int, dropout: float = 0.0):
        super().__init__()
        assert embed_dim % num_heads == 0, "embed_dim must be divisible by num_heads"

        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.scale = self.head_dim ** -0.5

        self.qkv = nn.Linear(embed_dim, embed_dim * 3)
        self.attn_drop = nn.Dropout(dropout)
        self.proj = nn.Linear(embed_dim, embed_dim)
        self.proj_drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, N, embed_dim]
        Returns:
            [B, N, embed_dim]
        """
        B, N, C = x.shape

        # [B, N, 3 * embed_dim] -> [B, N, 3, num_heads, head_dim] -> [3, B, num_heads, N, head_dim]
        qkv = self.qkv(x).reshape(B, N, 3, self.num_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]  # 每个张量形状: [B, num_heads, N, head_dim]

        # 注意力: [B, num_heads, N, N]
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)

        # [B, num_heads, N, head_dim] -> [B, N, num_heads, head_dim] -> [B, N, embed_dim]
        x = (attn @ v).transpose(1, 2).reshape(B, N, C)
        x = self.proj(x)
        x = self.proj_drop(x)

        return x


class MLP(nn.Module):
    """前馈网络（Feed-forward network）。"""

    def __init__(self, in_features: int, hidden_features: Optional[int] = None, dropout: float = 0.0):
        super().__init__()
        hidden_features = hidden_features or in_features * 4

        self.fc1 = nn.Linear(in_features, hidden_features)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_features, in_features)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.drop(x)
        return x


class TransformerBlock(nn.Module):
    """带有自注意力和 MLP 的 Transformer 块。"""

    def __init__(self, embed_dim: int, num_heads: int, mlp_ratio: float = 4.0, dropout: float = 0.0):
        super().__init__()
        self.norm1 = nn.LayerNorm(embed_dim)
        self.attn = MultiHeadAttention(embed_dim, num_heads, dropout)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.mlp = MLP(embed_dim, int(embed_dim * mlp_ratio), dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, N, embed_dim]
        Returns:
            [B, N, embed_dim]
        """
        x = x + self.attn(self.norm1(x))
        x = x + self.mlp(self.norm2(x))
        return x


class TinyViTEncoder(nn.Module):
    """
    用于掩码自编码（Masked Autoencoding）的轻量级 Vision Transformer 编码器。

    Args:
        img_size: 输入图像尺寸（假设为正方形图像）
        in_channels: 输入通道数（RGB 为 3，S2L2A 为 12）
        patch_size: 每个 patch 的尺寸
        embed_dim: 嵌入维度
        depth: Transformer 块的数量
        num_heads: 注意力头的数量
        mlp_ratio: MLP 隐藏层维度比例
        dropout: Dropout 比率
    """

    def __init__(
        self,
        img_size: int = 224,
        in_channels: int = 12,
        patch_size: int = 16,
        embed_dim: int = 256,
        depth: int = 6,
        num_heads: int = 4,
        mlp_ratio: float = 4.0,
        dropout: float = 0.0,
    ):
        super().__init__()

        self.img_size = img_size
        self.in_channels = in_channels
        self.patch_size = patch_size
        self.embed_dim = embed_dim
        self.depth = depth
        self.num_heads = num_heads

        # Patch embedding
        self.patch_embed = PatchEmbed(img_size, patch_size, in_channels, embed_dim)
        num_patches = self.patch_embed.num_patches

        # 位置嵌入（可学习）
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches, embed_dim))
        self.pos_drop = nn.Dropout(dropout)

        # Transformer 块
        self.blocks = nn.ModuleList([
            TransformerBlock(embed_dim, num_heads, mlp_ratio, dropout)
            for _ in range(depth)
        ])

        self.norm = nn.LayerNorm(embed_dim)

        # 初始化权重
        self._init_weights()

    def _init_weights(self):
        """初始化位置嵌入和权重。"""
        # 使用截断正态分布初始化位置嵌入
        nn.init.trunc_normal_(self.pos_embed, std=0.02)

        # 初始化其他权重
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
        通过打乱 patch 顺序执行随机掩码。

        Args:
            x: [B, N, D] patch tokens
            mask_ratio: 需要掩码的 patch 比例

        Returns:
            x_masked: [B, N*(1-mask_ratio), D] 可见的 patch
            mask: [B, N] 二值掩码（1=保留，0=掩码）
            ids_restore: [B, N] 用于恢复原始顺序的索引
        """
        B, N, D = x.shape
        len_keep = int(N * (1 - mask_ratio))

        # 随机打乱
        noise = torch.rand(B, N, device=x.device)
        ids_shuffle = torch.argsort(noise, dim=1)
        ids_restore = torch.argsort(ids_shuffle, dim=1)

        # 保留前一部分子集
        ids_keep = ids_shuffle[:, :len_keep]
        x_masked = torch.gather(x, dim=1, index=ids_keep.unsqueeze(-1).expand(-1, -1, D))

        # 生成二值掩码: 1=保留，0=掩码
        mask = torch.ones([B, N], device=x.device)
        mask[:, :len_keep] = 0
        mask = torch.gather(mask, dim=1, index=ids_restore)

        return x_masked, mask, ids_restore

    def forward(
        self,
        x: torch.Tensor,
        mask_ratio: Optional[float] = None
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        前向传播，支持为 MAE 进行可选的掩码操作。

        Args:
            x: [B, C, H, W] 输入图像
            mask_ratio: 若提供，则应用随机掩码（用于 MAE 训练）

        Returns:
            tokens: [B, N_visible, embed_dim] patch tokens（若掩码则仅含可见部分）
            mask: [B, N] 二值掩码（若提供 mask_ratio），否则为 None
            ids_restore: [B, N] 恢复索引（若提供 mask_ratio），否则为 None
        """
        # Patch embedding
        x = self.patch_embed(x)  # [B, N, embed_dim]

        # 加上位置嵌入
        x = x + self.pos_embed

        # 若指定则应用掩码
        mask = None
        ids_restore = None
        if mask_ratio is not None and mask_ratio > 0:
            x, mask, ids_restore = self.random_masking(x, mask_ratio)

        x = self.pos_drop(x)

        # Transformer 块
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
            'in_channels': self.in_channels,
            'patch_size': self.patch_size,
            'embed_dim': self.embed_dim,
            'depth': self.depth,
            'num_heads': self.num_heads,
        }


def create_tiny_vit_encoder(**kwargs) -> TinyViTEncoder:
    """工厂函数，用于以自定义配置创建 TinyViTEncoder。"""
    return TinyViTEncoder(**kwargs)


# 默认配置
DEFAULT_CONFIG_S2L2A = {
    'img_size': 224,
    'in_channels': 12,  # S2L2A 多光谱
    'patch_size': 16,
    'embed_dim': 256,
    'depth': 6,
    'num_heads': 4,
    'mlp_ratio': 4.0,
    'dropout': 0.1,
}

DEFAULT_CONFIG_S2RGB = {
    'img_size': 224,
    'in_channels': 3,  # 仅 RGB
    'patch_size': 16,
    'embed_dim': 256,
    'depth': 4,
    'num_heads': 4,
    'mlp_ratio': 4.0,
    'dropout': 0.1,
}


if __name__ == '__main__':
    # 测试 S2L2A 编码器
    print("Testing S2L2A encoder...")
    encoder_s2l2a = TinyViTEncoder(**DEFAULT_CONFIG_S2L2A)
    x_s2l2a = torch.randn(2, 12, 224, 224)

    # 不使用掩码
    tokens, mask, ids_restore = encoder_s2l2a(x_s2l2a)
    print(f"S2L2A output shape (no mask): {tokens.shape}")
    print(f"Expected: [2, 196, 256], Got: {list(tokens.shape)}")

    # 使用掩码（75% 掩码比例）
    tokens_masked, mask, ids_restore = encoder_s2l2a(x_s2l2a, mask_ratio=0.75)
    print(f"S2L2A output shape (75% masked): {tokens_masked.shape}")
    print(f"Mask shape: {mask.shape}, Masked patches: {mask.sum(dim=1)}")
    print(f"ids_restore shape: {ids_restore.shape}")

    # 测试 RGB 编码器
    print("\nTesting S2RGB encoder...")
    encoder_rgb = TinyViTEncoder(**DEFAULT_CONFIG_S2RGB)
    x_rgb = torch.randn(2, 3, 224, 224)
    tokens_rgb, _, _ = encoder_rgb(x_rgb, mask_ratio=0.75)
    print(f"S2RGB output shape (75% masked): {tokens_rgb.shape}")

    # 模型参数量
    print(f"\nS2L2A encoder parameters: {sum(p.numel() for p in encoder_s2l2a.parameters()) / 1e6:.2f}M")
    print(f"S2RGB encoder parameters: {sum(p.numel() for p in encoder_rgb.parameters()) / 1e6:.2f}M")
