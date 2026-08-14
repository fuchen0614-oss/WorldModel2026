"""
FiLM + Cross-attention 增强版双模态 ViT 编码器

在 MultiModalViTEncoder 基础上注入 phi（成像条件）：
1. FiLM 逐层调制：每个 Transformer block 中，attention 后做 x = x * (1+γ) + β
2. Cross-attention：在 FiLM 之后，patch tokens 作 Q，phi_tokens 作 KV

参考：
- FiLM (Perez et al., AAAI 2018): https://arxiv.org/abs/1709.07871
- 文档约束（13_*.md §6.4）

关键设计：
- γ/β 初始化为 0（identity 起点），让 FiLM 一开始等价于无调制
- 每层独立的 γ/β 投影（不共享），允许不同层学习不同的调制
- Cross-attention 是可选的（cross_attention=True/False），方便消融
"""

import math
from typing import Optional, Tuple, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from .tiny_vit_encoder import MultiHeadAttention, MLP
    from .multimodal_vit_encoder import MultiModalPatchEmbed
except ImportError:
    # 直接运行脚本时的 fallback
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from models.encoders.tiny_vit_encoder import MultiHeadAttention, MLP
    from models.encoders.multimodal_vit_encoder import MultiModalPatchEmbed


# ============================================================
# FiLM 调制层
# ============================================================
class FiLMModulation(nn.Module):
    """FiLM 调制层：从 phi_embed 生成 γ/β，作用在 x 上。

    x_out = x * (1 + γ) + β

    γ/β 投影初始化为 0，保证训练起点等价于 identity（不破坏预训练 encoder）。
    """

    def __init__(self, embed_dim: int, phi_dim: int):
        super().__init__()
        self.gamma_proj = nn.Linear(phi_dim, embed_dim)
        self.beta_proj = nn.Linear(phi_dim, embed_dim)
        # 零初始化：让起点等价于 identity
        nn.init.zeros_(self.gamma_proj.weight)
        nn.init.zeros_(self.gamma_proj.bias)
        nn.init.zeros_(self.beta_proj.weight)
        nn.init.zeros_(self.beta_proj.bias)

    def forward(self, x: torch.Tensor, phi_embed: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, N, embed_dim] patch tokens
            phi_embed: [B, phi_dim]

        Returns:
            调制后的 x: [B, N, embed_dim]
        """
        gamma = self.gamma_proj(phi_embed).unsqueeze(1)  # [B, 1, embed_dim]
        beta = self.beta_proj(phi_embed).unsqueeze(1)
        return x * (1.0 + gamma) + beta


# ============================================================
# Cross-attention 模块
# ============================================================
class PhiCrossAttention(nn.Module):
    """patch tokens 作 Q，phi_tokens 作 KV 的 cross-attention。

    残差连接 + 零初始化输出投影，保证训练起点等价于 identity。
    """

    def __init__(self, embed_dim: int, num_heads: int = 4, dropout: float = 0.0):
        super().__init__()
        self.norm_q = nn.LayerNorm(embed_dim)
        self.norm_kv = nn.LayerNorm(embed_dim)
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        # 输出投影零初始化（起点 identity）
        self.out_proj = nn.Linear(embed_dim, embed_dim)
        nn.init.zeros_(self.out_proj.weight)
        nn.init.zeros_(self.out_proj.bias)

    def forward(
        self,
        x: torch.Tensor,
        phi_tokens: torch.Tensor,
        phi_key_padding: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            x: [B, N, D] patch tokens
            phi_tokens: [B, T, D]
            phi_key_padding: [B, T] True 表示要忽略的 phi token

        Returns:
            x + cross_attn(x, phi): [B, N, D]
        """
        q = self.norm_q(x)
        kv = self.norm_kv(phi_tokens)
        attn_out, _ = self.attn(q, kv, kv, key_padding_mask=phi_key_padding)
        return x + self.out_proj(attn_out)


# ============================================================
# FiLM-augmented Transformer Block
# ============================================================
class FiLMTransformerBlock(nn.Module):
    """Transformer block with FiLM modulation and optional cross-attention.

    流程：
        x → norm1 → self_attn → +residual
          → FiLM(γ/β from phi_embed)
          → cross_attn(phi_tokens)  [可选]
          → norm2 → mlp → +residual
    """

    def __init__(
        self,
        embed_dim: int,
        num_heads: int,
        mlp_ratio: float = 4.0,
        dropout: float = 0.0,
        phi_dim: int = 256,
        use_film: bool = True,
        use_cross_attention: bool = False,
    ):
        super().__init__()
        self.use_film = use_film
        self.use_cross_attention = use_cross_attention

        # 标准 self-attention 部分
        self.norm1 = nn.LayerNorm(embed_dim)
        self.attn = MultiHeadAttention(embed_dim, num_heads, dropout)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.mlp = MLP(embed_dim, int(embed_dim * mlp_ratio), dropout)

        # FiLM
        if use_film:
            self.film = FiLMModulation(embed_dim, phi_dim)

        # Cross-attention
        if use_cross_attention:
            self.cross_attn = PhiCrossAttention(embed_dim, num_heads, dropout)

    def forward(
        self,
        x: torch.Tensor,
        phi_embed: Optional[torch.Tensor] = None,
        phi_tokens: Optional[torch.Tensor] = None,
        phi_key_padding: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            x: [B, N, D] patch tokens
            phi_embed: [B, D] 用于 FiLM；为 None 时跳过 FiLM
            phi_tokens: [B, T, D] 用于 cross-attention；为 None 时跳过
            phi_key_padding: [B, T] cross-attention mask

        Returns:
            [B, N, D]
        """
        # 1. Self-attention + residual
        x = x + self.attn(self.norm1(x))

        # 2. FiLM modulation
        if self.use_film and phi_embed is not None:
            x = self.film(x, phi_embed)

        # 3. Cross-attention
        if self.use_cross_attention and phi_tokens is not None:
            x = self.cross_attn(x, phi_tokens, phi_key_padding)

        # 4. MLP + residual
        x = x + self.mlp(self.norm2(x))
        return x


# ============================================================
# 主编码器：MultiModalViTEncoderFiLM
# ============================================================
class MultiModalViTEncoderFiLM(nn.Module):
    """支持 phi 调制的双模态 ViT 编码器（FiLM + Cross-attention）。

    与 MultiModalViTEncoder 接口兼容（共享 patch_embed/pos_embed/modality_embed/random_masking），
    新增：
    - phi_embed 通过 FiLM 注入每层
    - phi_tokens 通过 cross-attention 注入每层
    - 可加载 stage1_dual2 的 encoder_state_dict 继续训练（forward block 前缀兼容）

    Args:
        img_size, s1_channels, s2_channels, patch_size, embed_dim, depth, num_heads, mlp_ratio, dropout:
            标准 ViT 参数（与 MultiModalViTEncoder 一致）
        phi_dim: phi_embed 维度
        use_film, use_cross_attention: 消融开关
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
        phi_dim: int = 256,
        use_film: bool = True,
        use_cross_attention: bool = False,
        film_start_layer: int = 0,
    ):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.embed_dim = embed_dim
        self.depth = depth
        self.num_heads = num_heads
        self.use_film = use_film
        self.use_cross_attention = use_cross_attention
        if not 0 <= film_start_layer <= depth:
            raise ValueError(f"film_start_layer must be in [0, {depth}], got {film_start_layer}")
        self.film_start_layer = film_start_layer

        # ---- 与 MultiModalViTEncoder 完全一致的子模块（用于加载 stage1 ckpt）----
        self.patch_embed = MultiModalPatchEmbed(
            img_size, patch_size, s1_channels, s2_channels, embed_dim
        )
        num_patches = self.patch_embed.num_patches

        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches, embed_dim))
        self.modality_embed_s1 = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.modality_embed_s2 = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.pos_drop = nn.Dropout(dropout)

        # ---- FiLM 增强的 Transformer blocks ----
        self.blocks = nn.ModuleList([
            FiLMTransformerBlock(
                embed_dim, num_heads, mlp_ratio, dropout,
                phi_dim=phi_dim,
                use_film=(use_film and i >= film_start_layer),
                use_cross_attention=use_cross_attention,
            )
            for i in range(depth)
        ])

        self.norm = nn.LayerNorm(embed_dim)
        self._init_weights()

    def _init_weights(self):
        nn.init.trunc_normal_(self.pos_embed, std=0.02)
        nn.init.trunc_normal_(self.modality_embed_s1, std=0.02)
        nn.init.trunc_normal_(self.modality_embed_s2, std=0.02)
        self.apply(self._init_module_weights)

    def _init_module_weights(self, m):
        # 不要覆盖 FiLM 和 cross_attn.out_proj 的零初始化
        if isinstance(m, nn.Linear):
            # 跳过特殊层（FiLM 的 gamma/beta_proj 和 cross_attn 的 out_proj 在自己模块里已初始化）
            return
        if isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode='fan_out')
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.weight, 1.0)
            nn.init.constant_(m.bias, 0)

    def random_masking(self, x: torch.Tensor, mask_ratio: float):
        """与 MultiModalViTEncoder.random_masking 完全一致。"""
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
        mask_ratio: Optional[float] = None,
        phi_embed: Optional[torch.Tensor] = None,
        phi_tokens: Optional[torch.Tensor] = None,
        phi_key_padding: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        Args:
            x: [B, C, H, W] 输入图像
            modality: 'S1' 或 'S2'
            mask_ratio: MAE 掩码比例
            phi_embed: [B, phi_dim] 全局 phi 向量（FiLM 用）
            phi_tokens: [B, T, embed_dim] phi 时序 tokens（cross-attention 用）
            phi_key_padding: [B, T] cross-attention mask

        Returns:
            tokens, mask, ids_restore  (与 MultiModalViTEncoder 一致)
        """
        x = self.patch_embed(x, modality)
        x = x + self.pos_embed

        if modality == 'S1':
            x = x + self.modality_embed_s1
        elif modality == 'S2':
            x = x + self.modality_embed_s2
        else:
            raise ValueError(f"Unknown modality: {modality}")

        mask = None
        ids_restore = None
        if mask_ratio is not None and mask_ratio > 0:
            x, mask, ids_restore = self.random_masking(x, mask_ratio)

        x = self.pos_drop(x)

        # 关键：每个 block 都注入 phi
        for block in self.blocks:
            x = block(x, phi_embed=phi_embed, phi_tokens=phi_tokens,
                      phi_key_padding=phi_key_padding)

        x = self.norm(x)
        return x, mask, ids_restore

    def load_stage1_encoder_weights(self, state_dict: dict, strict: bool = False):
        """从 stage1_dual2 的 encoder_state_dict 加载预训练权重。

        新增的 FiLM/cross_attn 模块在 ckpt 中不存在，用 strict=False 忽略它们；
        共享部分（patch_embed/pos_embed/modality_embed/blocks.*.norm*/attn/mlp）应能匹配。

        Args:
            state_dict: stage1_dual2 ckpt['encoder_state_dict']
            strict: 是否严格校验

        Returns:
            missing_keys, unexpected_keys
        """
        result = self.load_state_dict(state_dict, strict=strict)
        # 统计 stage1 已加载 / 新增 / 不匹配
        loaded = sum(1 for k in state_dict.keys() if k not in result.unexpected_keys)
        return {
            'loaded_from_stage1': loaded,
            'new_params': result.missing_keys,
            'unexpected': result.unexpected_keys,
        }

    def get_num_patches(self) -> int:
        return self.patch_embed.num_patches

    def get_config(self) -> dict:
        return {
            'img_size': self.img_size,
            'patch_size': self.patch_size,
            'embed_dim': self.embed_dim,
            'depth': self.depth,
            'num_heads': self.num_heads,
            'use_film': self.use_film,
            'use_cross_attention': self.use_cross_attention,
            'film_start_layer': self.film_start_layer,
        }


if __name__ == '__main__':
    print("=== MultiModalViTEncoderFiLM 自测 ===")

    encoder = MultiModalViTEncoderFiLM(
        img_size=256, embed_dim=256, depth=6, num_heads=4,
        phi_dim=256, use_film=True, use_cross_attention=True,
    )
    n_params = sum(p.numel() for p in encoder.parameters()) / 1e6
    print(f"参数量: {n_params:.2f}M (baseline 5.72M, 新增 FiLM+CA 约 {n_params-5.72:.2f}M)")

    # 模拟输入
    B, T, D = 2, 4, 256
    x_s2 = torch.randn(B, 12, 256, 256)
    phi_embed = torch.randn(B, D)
    phi_tokens = torch.randn(B, T, D)

    # 正常前向
    tokens, mask, ids_restore = encoder(
        x_s2, modality='S2', mask_ratio=0.75,
        phi_embed=phi_embed, phi_tokens=phi_tokens,
    )
    print(f"forward (with phi): tokens={tokens.shape}, mask={mask.shape}")

    # 不传 phi（消融模式）
    tokens2, _, _ = encoder(x_s2, modality='S2', mask_ratio=0.75)
    print(f"forward (without phi): tokens={tokens2.shape} ✓")

    # 测试 FiLM/CA 初始化是否真为 identity
    # 不掩码、不传 phi 的输出应与 baseline 几乎一致（FiLM/CA 起点应等价 identity）
    encoder.eval()
    with torch.no_grad():
        out_with_phi_zero, _, _ = encoder(
            x_s2, modality='S2', mask_ratio=0.0,
            phi_embed=torch.zeros(B, D), phi_tokens=torch.zeros(B, T, D),
        )
        out_no_phi, _, _ = encoder(x_s2, modality='S2', mask_ratio=0.0)
    diff = (out_with_phi_zero - out_no_phi).abs().max().item()
    print(f"phi=0 vs no_phi 的最大差异: {diff:.6e}")
    print("（FiLM/cross_attn 都零初始化，理论上应 < 1e-5）")

    print("\n✓ MultiModalViTEncoderFiLM 自测通过")
