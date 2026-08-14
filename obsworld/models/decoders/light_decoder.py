"""
用于掩码自编码（Masked Autoencoding）的轻量级像素重建解码器。

从 patch token 重建图像，支持以下两种方式：
1. Transformer 解码器块（轻量级 self-attention）
2. 转置卷积层（高效上采样）

支持可选的"仅掩码"解码以提升效率。
"""

import torch
import torch.nn as nn
import math
from typing import Optional, Tuple


class DecoderFiLM(nn.Module):
    """方案 A 的核心：把成像条件 phi 通过 FiLM 注入 decoder。

    x_out = x * (1 + γ(phi)) + β(phi)

    γ/β 投影零初始化 → 训练起点等价 identity，可无损加载 Stage1 decoder 权重。
    这里 phi 只进 decoder，encoder 保持纯净（不见 phi）→ latent 被迫学成像无关的地表状态。
    对标 SPADE / conditional-VAE 的 decoder-only conditioning。
    """

    def __init__(self, embed_dim: int, phi_dim: int):
        super().__init__()
        self.gamma_proj = nn.Linear(phi_dim, embed_dim)
        self.beta_proj = nn.Linear(phi_dim, embed_dim)
        nn.init.zeros_(self.gamma_proj.weight)
        nn.init.zeros_(self.gamma_proj.bias)
        nn.init.zeros_(self.beta_proj.weight)
        nn.init.zeros_(self.beta_proj.bias)

    def forward(self, x: torch.Tensor, phi_embed: torch.Tensor) -> torch.Tensor:
        # x: [B, N, D]; phi_embed: [B, phi_dim]
        gamma = self.gamma_proj(phi_embed).unsqueeze(1)  # [B,1,D]
        beta = self.beta_proj(phi_embed).unsqueeze(1)
        return x * (1.0 + gamma) + beta


class TransformerDecoderBlock(nn.Module):
    """轻量级 transformer 解码器块（可选 FiLM 条件化）。"""

    def __init__(self, embed_dim: int, num_heads: int, mlp_ratio: float = 4.0, dropout: float = 0.0,
                 phi_dim: Optional[int] = None):
        super().__init__()
        self.norm1 = nn.LayerNorm(embed_dim)
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(embed_dim)

        hidden_dim = int(embed_dim * mlp_ratio)
        self.mlp = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embed_dim),
            nn.Dropout(dropout),
        )
        # 方案 A：每个 decoder block 一个 FiLM（phi_dim 为 None 时不启用，向后兼容）
        self.film = DecoderFiLM(embed_dim, phi_dim) if phi_dim is not None else None

    def forward(self, x: torch.Tensor, phi_embed: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: [B, N, embed_dim]
            phi_embed: [B, phi_dim] 成像条件（方案 A：在此注入 decoder）
        Returns:
            [B, N, embed_dim]
        """
        # 带残差连接的 self-attention
        attn_out, _ = self.attn(self.norm1(x), self.norm1(x), self.norm1(x))
        x = x + attn_out

        # FiLM 条件化（attention 之后、MLP 之前）
        if self.film is not None and phi_embed is not None:
            x = self.film(x, phi_embed)

        # 带残差连接的 MLP
        x = x + self.mlp(self.norm2(x))

        return x


class ConvTransposeDecoder(nn.Module):
    """用于高效上采样的转置卷积解码器。"""

    def __init__(
        self,
        in_dim: int,
        out_channels: int,
        patch_size: int = 16,
        hidden_dim: int = 128,
    ):
        super().__init__()
        self.patch_size = patch_size

        # 渐进式上采样
        # in_dim -> hidden_dim*4 -> hidden_dim -> out_channels
        layers = []

        # 第一层：投影到空间特征图
        layers.append(nn.Linear(in_dim, hidden_dim * 4))
        layers.append(nn.GELU())

        # 计算上采样阶段数
        self.initial_size = 4  # 每个 patch 从 4x4 特征图开始
        num_upsample = int(math.log2(patch_size // self.initial_size))

        # 初始 reshape 和卷积
        self.proj = nn.Sequential(*layers)

        # 上采样块
        conv_layers = []
        current_dim = hidden_dim * 4

        for i in range(num_upsample):
            next_dim = hidden_dim if i < num_upsample - 1 else hidden_dim // 2
            conv_layers.extend([
                nn.ConvTranspose2d(
                    current_dim, next_dim,
                    kernel_size=4, stride=2, padding=1
                ),
                nn.BatchNorm2d(next_dim),
                nn.GELU(),
            ])
            current_dim = next_dim

        # 最终投影到输出通道
        conv_layers.append(
            nn.Conv2d(current_dim, out_channels, kernel_size=3, padding=1)
        )

        self.conv_decoder = nn.Sequential(*conv_layers)

    def forward(self, x: torch.Tensor, num_patches_side: int) -> torch.Tensor:
        """
        Args:
            x: [B, N, in_dim] patch token
            num_patches_side: sqrt(N)，patch 网格的边长
        Returns:
            [B, out_channels, H, W] 重建后的图像
        """
        B, N, D = x.shape

        # 投影 token
        x = self.proj(x)  # [B, N, hidden_dim*4]

        # reshape 成空间网格
        x = x.reshape(B, num_patches_side, num_patches_side, -1)
        x = x.permute(0, 3, 1, 2)  # [B, hidden_dim*4, H_patch, W_patch]

        # 使用转置卷积进行上采样
        x = x.repeat_interleave(self.initial_size, dim=2).repeat_interleave(self.initial_size, dim=3)
        x = self.conv_decoder(x)

        return x


class LightDecoder(nn.Module):
    """
    用于掩码自编码（Masked Autoencoding）的轻量级像素重建解码器。

    Args:
        in_dim: 输入 token 维度（编码器输出维度）
        out_channels: 输出图像通道数（RGB 为 3，S2L2A 为 12）
        patch_size: 每个 patch 的大小（应与编码器一致）
        img_size: 输出图像尺寸（假设为正方形图像）
        depth: 解码器块的数量（推荐 2-4）
        num_heads: attention 头数（用于 transformer 模式）
        decoder_embed_dim: 解码器内部维度（若为 None，则使用 in_dim）
        mlp_ratio: MLP 隐藏层维度比例
        dropout: dropout 比率
        decoder_mode: 'transformer' 或 'conv' —— 架构类型
    """

    def __init__(
        self,
        in_dim: int = 256,
        out_channels: int = 12,
        patch_size: int = 16,
        img_size: int = 224,
        depth: int = 2,
        num_heads: int = 4,
        decoder_embed_dim: Optional[int] = None,
        mlp_ratio: float = 4.0,
        dropout: float = 0.0,
        decoder_mode: str = 'transformer',
        phi_dim: Optional[int] = None,
    ):
        super().__init__()

        self.in_dim = in_dim
        self.out_channels = out_channels
        self.patch_size = patch_size
        self.img_size = img_size
        self.num_patches = (img_size // patch_size) ** 2
        self.num_patches_side = img_size // patch_size
        self.decoder_mode = decoder_mode
        self.phi_dim = phi_dim

        # 解码器 embedding 维度
        self.decoder_embed_dim = decoder_embed_dim or in_dim

        # 将编码器输出投影到解码器维度
        self.decoder_embed = nn.Linear(in_dim, self.decoder_embed_dim)

        # mask token（可学习）
        self.mask_token = nn.Parameter(torch.zeros(1, 1, self.decoder_embed_dim))

        # 解码器的位置 embedding
        self.decoder_pos_embed = nn.Parameter(
            torch.zeros(1, self.num_patches, self.decoder_embed_dim)
        )

        if decoder_mode == 'transformer':
            # Transformer 解码器块
            self.decoder_blocks = nn.ModuleList([
                TransformerDecoderBlock(
                    self.decoder_embed_dim, num_heads, mlp_ratio, dropout,
                    phi_dim=phi_dim,
                )
                for _ in range(depth)
            ])

            self.decoder_norm = nn.LayerNorm(self.decoder_embed_dim)

            # 投影到像素值
            self.decoder_pred = nn.Linear(
                self.decoder_embed_dim,
                patch_size * patch_size * out_channels
            )

        elif decoder_mode == 'conv':
            # 卷积解码器
            self.conv_decoder = ConvTransposeDecoder(
                self.decoder_embed_dim,
                out_channels,
                patch_size,
                hidden_dim=128,
            )
        else:
            raise ValueError(f"Unknown decoder_mode: {decoder_mode}. Use 'transformer' or 'conv'.")

        # 初始化权重
        self._init_weights()

    def _init_weights(self):
        """初始化权重。"""
        nn.init.trunc_normal_(self.mask_token, std=0.02)
        nn.init.trunc_normal_(self.decoder_pos_embed, std=0.02)

        self.apply(self._init_module_weights)

        # apply() 会把所有 Linear 用 trunc_normal 覆盖，需重新把 FiLM 的 γ/β 归零，
        # 保证 identity 起点（可无损加载 Stage1 decoder 权重）。
        for m in self.modules():
            if isinstance(m, DecoderFiLM):
                nn.init.zeros_(m.gamma_proj.weight); nn.init.zeros_(m.gamma_proj.bias)
                nn.init.zeros_(m.beta_proj.weight); nn.init.zeros_(m.beta_proj.bias)

    def _init_module_weights(self, m):
        """初始化线性层和卷积层的权重。"""
        if isinstance(m, nn.Linear):
            nn.init.trunc_normal_(m.weight, std=0.02)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, (nn.Conv2d, nn.ConvTranspose2d)):
            nn.init.kaiming_normal_(m.weight, mode='fan_out')
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, (nn.LayerNorm, nn.BatchNorm2d)):
            nn.init.constant_(m.weight, 1.0)
            nn.init.constant_(m.bias, 0)

    def forward(
        self,
        x: torch.Tensor,
        ids_restore: Optional[torch.Tensor] = None,
        mask: Optional[torch.Tensor] = None,
        phi_embed: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        从 patch token 重建图像的前向传播。

        Args:
            x: [B, N_visible, in_dim] 来自编码器的可见 patch token
            ids_restore: [B, N_total] 用于恢复原始 patch 顺序的索引（可选）
            mask: [B, N_total] 二值掩码（1=被掩码，0=可见）（可选）
            phi_embed: [B, phi_dim] 成像条件（方案 A：注入 decoder 每个 block 的 FiLM）

        Returns:
            [B, C, H, W] 重建后的图像
        """
        B = x.shape[0]

        # 投影到解码器维度
        x = self.decoder_embed(x)  # [B, N_visible, decoder_embed_dim]

        # 如果应用了掩码，则用 mask token 恢复完整序列
        if ids_restore is not None:
            N_visible = x.shape[1]
            N_total = self.num_patches

            # 扩展 mask token
            mask_tokens = self.mask_token.repeat(B, N_total - N_visible, 1)

            # 拼接可见 token 和 mask token
            x_full = torch.cat([x, mask_tokens], dim=1)  # [B, N_total, decoder_embed_dim]

            # 反向打乱以恢复原始顺序
            x_full = torch.gather(
                x_full, dim=1,
                index=ids_restore.unsqueeze(-1).expand(-1, -1, self.decoder_embed_dim)
            )
            x = x_full

        # 添加位置 embedding
        x = x + self.decoder_pos_embed

        if self.decoder_mode == 'transformer':
            # Transformer 解码器
            for block in self.decoder_blocks:
                x = block(x, phi_embed=phi_embed)

            x = self.decoder_norm(x)

            # 投影到像素值
            x = self.decoder_pred(x)  # [B, N, patch_size^2 * out_channels]

            # reshape 成图像
            x = self.unpatchify(x)  # [B, out_channels, H, W]

        elif self.decoder_mode == 'conv':
            # 卷积解码器
            x = self.conv_decoder(x, self.num_patches_side)  # [B, out_channels, H, W]

        return x

    def unpatchify(self, x: torch.Tensor) -> torch.Tensor:
        """
        将 patch token 转换为图像。

        Args:
            x: [B, N, patch_size^2 * out_channels]
        Returns:
            [B, out_channels, H, W]
        """
        B, N, _ = x.shape
        h = w = self.num_patches_side
        p = self.patch_size

        # reshape：[B, N, p*p*C] -> [B, h, w, p, p, C]
        x = x.reshape(B, h, w, p, p, self.out_channels)

        # permute：[B, h, w, p, p, C] -> [B, C, h, p, w, p]
        x = x.permute(0, 5, 1, 3, 2, 4)

        # reshape：[B, C, h, p, w, p] -> [B, C, h*p, w*p]
        x = x.reshape(B, self.out_channels, h * p, w * p)

        return x

    def forward_masked_only(
        self,
        x: torch.Tensor,
        ids_restore: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        高效的前向传播，只重建被掩码的 patch。
        第二阶段（Stage 2）的效率特性 —— 可后续实现。

        Args:
            x: [B, N_visible, in_dim] 可见 patch token
            ids_restore: [B, N_total] 恢复索引
            mask: [B, N_total] 二值掩码（1=被掩码，0=可见）

        Returns:
            [B, N_masked, patch_size^2 * out_channels] 仅重建被掩码的 patch
        """
        # 目前回退到完整重建
        # TODO: 实现仅掩码解码以提升效率
        return self.forward(x, ids_restore, mask)

    def get_config(self) -> dict:
        """返回配置字典。"""
        return {
            'in_dim': self.in_dim,
            'out_channels': self.out_channels,
            'patch_size': self.patch_size,
            'img_size': self.img_size,
            'decoder_embed_dim': self.decoder_embed_dim,
            'decoder_mode': self.decoder_mode,
        }


def create_light_decoder(**kwargs) -> LightDecoder:
    """用于创建带自定义配置的 LightDecoder 的工厂函数。"""
    return LightDecoder(**kwargs)


# 默认配置
DEFAULT_DECODER_CONFIG_S2L2A = {
    'in_dim': 256,
    'out_channels': 12,
    'patch_size': 16,
    'img_size': 224,
    'depth': 4,
    'num_heads': 4,
    'decoder_embed_dim': 128,
    'mlp_ratio': 4.0,
    'dropout': 0.0,
    'decoder_mode': 'transformer',
}

DEFAULT_DECODER_CONFIG_S2RGB = {
    'in_dim': 256,
    'out_channels': 3,
    'patch_size': 16,
    'img_size': 224,
    'depth': 2,
    'num_heads': 4,
    'decoder_embed_dim': 128,
    'mlp_ratio': 4.0,
    'dropout': 0.0,
    'decoder_mode': 'transformer',
}

DEFAULT_DECODER_CONFIG_CONV = {
    'in_dim': 256,
    'out_channels': 12,
    'patch_size': 16,
    'img_size': 224,
    'decoder_embed_dim': 128,
    'decoder_mode': 'conv',
}


if __name__ == '__main__':
    # 测试 transformer 解码器（S2L2A）
    print("Testing Transformer Decoder (S2L2A)...")
    decoder_transformer = LightDecoder(**DEFAULT_DECODER_CONFIG_S2L2A)

    # 模拟编码器输出（75% 掩码率：196 个 patch -> 49 个可见）
    B, N_total, N_visible = 2, 196, 49
    in_dim = 256

    x_visible = torch.randn(B, N_visible, in_dim)
    ids_restore = torch.randperm(N_total).unsqueeze(0).expand(B, -1)
    mask = torch.ones(B, N_total)
    mask[:, :N_visible] = 0

    # 重建完整图像
    img_recon = decoder_transformer(x_visible, ids_restore, mask)
    print(f"Transformer decoder output shape: {img_recon.shape}")
    print(f"Expected: [2, 12, 224, 224], Got: {list(img_recon.shape)}")

    # 测试无掩码情形（所有 patch 均可见）
    print("\nTesting without masking...")
    x_full = torch.randn(B, N_total, in_dim)
    img_recon_full = decoder_transformer(x_full)
    print(f"Full reconstruction shape: {img_recon_full.shape}")

    # 测试卷积解码器
    print("\nTesting Convolutional Decoder...")
    decoder_conv = LightDecoder(**DEFAULT_DECODER_CONFIG_CONV)
    img_recon_conv = decoder_conv(x_visible, ids_restore, mask)
    print(f"Conv decoder output shape: {img_recon_conv.shape}")
    print(f"Expected: [2, 12, 224, 224], Got: {list(img_recon_conv.shape)}")

    # 测试 RGB 解码器
    print("\nTesting RGB Decoder...")
    decoder_rgb = LightDecoder(**DEFAULT_DECODER_CONFIG_S2RGB)
    img_recon_rgb = decoder_rgb(x_visible, ids_restore, mask)
    print(f"RGB decoder output shape: {img_recon_rgb.shape}")
    print(f"Expected: [2, 3, 224, 224], Got: {list(img_recon_rgb.shape)}")

    # 模型参数量
    print(f"\nTransformer decoder parameters: {sum(p.numel() for p in decoder_transformer.parameters()) / 1e6:.2f}M")
    print(f"Convolutional decoder parameters: {sum(p.numel() for p in decoder_conv.parameters()) / 1e6:.2f}M")
    print(f"RGB decoder parameters: {sum(p.numel() for p in decoder_rgb.parameters()) / 1e6:.2f}M")
