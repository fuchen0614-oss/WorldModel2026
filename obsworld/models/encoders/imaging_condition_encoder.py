"""
ImagingConditionEncoder：将 phi（成像条件）编码为可注入的特征向量

输入：phi_dict（来自 phi_loader.PhiCache，含 lat/lon/sun_elevation/season/cloud 等）
输出：phi_embed [B, D] 与对应的 FiLM γ/β 参数

设计约束（来自 任务描述相关/13_*.md §6）：
1. season **不能单独**使用，必须和 lat + sun_elevation 联合输入（南北半球区分）
2. 用 dict 输入接口，未来加字段只需加 key（约束 8）
3. field_mask gating：缺失字段走 learnable missing embedding
4. 编码方式：
   - sun_elevation: sin(elev) 物理归一化
   - season: 4 类 embedding（非有序）
   - lat/lon: 多频 sin/cos（球谐函数轻量版）
   - cloud_cover: log 变换 + 二值标志

⭐ 单时间片严格对齐版（D3）：
   - 每个样本只输入**一个时间片**的 phi（sun_elevation/season/cloud 为标量 [B]，
     而非 4 季 [B,4]），与该样本实际选中的那一季图像严格对应。
   - 去掉时序聚合（mean/attention）分支。dataloader 负责按选中的季节 t 取对应字段。
"""

import math
from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


# ============================================================
# 子模块：字段编码器
# ============================================================
class SunElevationEncoder(nn.Module):
    """太阳高度角编码：sin(elev) → MLP → embed。

    sin(elev) ∈ [-1, 1]，物理意义直接（与光照强度相关）。
    """

    def __init__(self, embed_dim: int = 64):
        super().__init__()
        self.proj = nn.Sequential(
            nn.Linear(1, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, embed_dim),
        )
        # missing embedding（可学习）
        self.missing_embed = nn.Parameter(torch.zeros(embed_dim))
        nn.init.trunc_normal_(self.missing_embed, std=0.02)

    def forward(self, sun_elev_deg: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
        """
        Args:
            sun_elev_deg: [B, T] 太阳高度角（度），NaN 表示缺失
            valid_mask: [B, T] 1=有效，0=缺失

        Returns:
            [B, T, embed_dim] 编码特征
        """
        # NaN 替换为 0（避免传播）
        sun_clean = torch.where(valid_mask.bool(), sun_elev_deg, torch.zeros_like(sun_elev_deg))
        # sin(elev) 归一化
        sin_elev = torch.sin(torch.deg2rad(sun_clean)).unsqueeze(-1)  # [B, T, 1]
        feat = self.proj(sin_elev)  # [B, T, embed_dim]

        # 缺失位置替换为 missing embedding
        valid_b = valid_mask.unsqueeze(-1).bool()
        feat = torch.where(valid_b, feat, self.missing_embed.expand_as(feat))
        return feat


class SeasonEncoder(nn.Module):
    """季节编码：4 类 embedding（非有序）+ missing 类别。"""

    def __init__(self, embed_dim: int = 32):
        super().__init__()
        # 4 类（春夏秋冬）+ 1 类（missing） = 5
        self.embedding = nn.Embedding(5, embed_dim)
        self.missing_idx = 4
        nn.init.trunc_normal_(self.embedding.weight, std=0.02)

    def forward(self, season: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
        """
        Args:
            season: [B, T] 季节编码（0-3），-1 或缺失会被替换为 missing_idx
            valid_mask: [B, T] 1=有效

        Returns:
            [B, T, embed_dim]
        """
        # 无效位置（season=-1 或 valid_mask=0）映射到 missing_idx
        season_clean = torch.where(
            valid_mask.bool() & (season >= 0) & (season <= 3),
            season,
            torch.full_like(season, self.missing_idx),
        )
        return self.embedding(season_clean)


class LatLonEncoder(nn.Module):
    """经纬度多频 sin/cos 编码（球谐函数轻量版）。

    参考：SatCLIP、GeoCLIP、NeRF positional encoding。
    频率倍增 2^0..2^(num_freq-1)，捕获从全局到局部的空间模式。
    """

    def __init__(self, num_frequencies: int = 4, embed_dim: int = 64):
        super().__init__()
        self.num_frequencies = num_frequencies
        # 输入维度: num_freq * 4 (lat_sin, lat_cos, lon_sin, lon_cos)
        input_dim = num_frequencies * 4
        self.proj = nn.Sequential(
            nn.Linear(input_dim, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, embed_dim),
        )
        self.missing_embed = nn.Parameter(torch.zeros(embed_dim))
        nn.init.trunc_normal_(self.missing_embed, std=0.02)

        # 注册频率为 buffer（不参与梯度）
        freqs = torch.tensor([2.0 ** i for i in range(num_frequencies)], dtype=torch.float32)
        self.register_buffer('freqs', freqs)

    def forward(self, lat: torch.Tensor, lon: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
        """
        Args:
            lat, lon: [B] 度，NaN 表示缺失
            valid_mask: [B] 1=有效

        Returns:
            [B, embed_dim]
        """
        lat_clean = torch.where(valid_mask.bool(), lat, torch.zeros_like(lat))
        lon_clean = torch.where(valid_mask.bool(), lon, torch.zeros_like(lon))

        lat_rad = torch.deg2rad(lat_clean).unsqueeze(-1)  # [B, 1]
        lon_rad = torch.deg2rad(lon_clean).unsqueeze(-1)  # [B, 1]

        freqs = self.freqs.unsqueeze(0)  # [1, num_freq]
        encs = []
        for arr in (lat_rad, lon_rad):
            scaled = arr * freqs  # [B, num_freq]
            encs.extend([torch.sin(scaled), torch.cos(scaled)])
        feat_in = torch.cat(encs, dim=-1)  # [B, num_freq*4]

        feat = self.proj(feat_in)
        feat = torch.where(valid_mask.unsqueeze(-1).bool(), feat, self.missing_embed.expand_as(feat))
        return feat


class CloudEncoder(nn.Module):
    """云量编码：log 变换 + 二值标志，处理长尾稀疏。

    数据特性（§4.3）：中位数 0%，仅 18.6% 时间片有云。
    """

    def __init__(self, embed_dim: int = 32):
        super().__init__()
        # 输入: [log(1+cover), log(1+shadow), valid_ratio, has_cloud_flag] = 4 dim
        self.proj = nn.Sequential(
            nn.Linear(4, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, embed_dim),
        )
        self.missing_embed = nn.Parameter(torch.zeros(embed_dim))
        nn.init.trunc_normal_(self.missing_embed, std=0.02)

    def forward(self, cover: torch.Tensor, shadow: torch.Tensor,
                valid_ratio: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
        """
        Args:
            cover, shadow, valid_ratio: [B, T] 各时间片云量/云影/有效像素占比。
                可能为 NaN（如 S1GRD 没有云字段，整列缺失）。
            valid_mask: [B, T] 时间片有效性（来自 time_valid）

        Returns:
            [B, T, embed_dim]

        云有效性 = 时间片有效 AND 云量非 NaN。S1GRD 等无云模态会落到 missing embedding
        （遵守 §6.3：缺失字段走可学习的 missing embedding，且不让 NaN 污染前向）。
        """
        # 云字段独立有效性：时间片有效 且 cover 非 NaN（S1 无云 → False → missing embedding）
        cloud_valid = valid_mask.bool() & torch.isfinite(cover)

        # 先把 NaN 清零，避免 torch.where "未选中分支仍含 NaN" 导致的 NaN 梯度
        cover = torch.nan_to_num(cover, nan=0.0)
        shadow = torch.nan_to_num(shadow, nan=0.0)
        valid_ratio = torch.nan_to_num(valid_ratio, nan=1.0)

        c = torch.where(cloud_valid, cover, torch.zeros_like(cover))
        s = torch.where(cloud_valid, shadow, torch.zeros_like(shadow))
        v = torch.where(cloud_valid, valid_ratio, torch.ones_like(valid_ratio))
        # 二值标志：是否有云（>1% 阈值）
        has_cloud = (c > 0.01).float()

        feat_in = torch.stack([
            torch.log1p(c),      # log(1+x) 抑制长尾
            torch.log1p(s),
            v,
            has_cloud,
        ], dim=-1)  # [B, T, 4]
        feat = self.proj(feat_in)

        feat = torch.where(cloud_valid.unsqueeze(-1), feat, self.missing_embed.expand_as(feat))
        return feat


class ModalityEncoder(nn.Module):
    """模态编码：S2L2A/S1GRD/... 类别 embedding。"""

    def __init__(self, num_modalities: int = 6, embed_dim: int = 32):
        super().__init__()
        # +1 for missing
        self.embedding = nn.Embedding(num_modalities + 1, embed_dim)
        self.missing_idx = num_modalities
        nn.init.trunc_normal_(self.embedding.weight, std=0.02)

    def forward(self, modality: torch.Tensor) -> torch.Tensor:
        """
        Args:
            modality: [B] long，-1 表示缺失

        Returns:
            [B, embed_dim]
        """
        mod_clean = torch.where(modality >= 0, modality, torch.full_like(modality, self.missing_idx))
        return self.embedding(mod_clean)


class SARGeometryEncoder(nn.Module):
    """S1 SAR 几何成像条件编码（phi v3，见 outputs/20_S1几何字段审查报告.md）。

    字段（均来自 S1 产品 ID file_id，单时间片标量 [B]）：
    - orbit_direction: 升/降轨 —— 0=desc,1=asc,-1=missing → 3 类 embedding
    - relative_orbit:  相对轨道 1..175，-1=missing → 176 类 embedding（0 槽=missing）
    - satellite:       0=S1A,1=S1B,-1=missing → 3 类 embedding
    - incidence_angle: 入射角（当前占位，缺失走 missing embedding；STAC 不暴露，详见报告 §3.3）

    缺失全部走可学习 missing，不产生 NaN。S2 样本无这些字段时整体走 missing → 退化为零贡献。
    """

    def __init__(self, embed_dim: int = 64,
                 orbit_dim: int = 16, relorbit_dim: int = 24,
                 sat_dim: int = 8, incidence_dim: int = 16):
        super().__init__()
        # 0=desc,1=asc,2=missing
        self.orbit_embed = nn.Embedding(3, orbit_dim)
        # 0=missing, 1..175=relative orbit
        self.relorbit_embed = nn.Embedding(176, relorbit_dim)
        # 0=S1A,1=S1B,2=missing
        self.sat_embed = nn.Embedding(3, sat_dim)
        for emb in (self.orbit_embed, self.relorbit_embed, self.sat_embed):
            nn.init.trunc_normal_(emb.weight, std=0.02)

        # incidence：sin/cos(角度) → MLP；缺失走 missing embedding
        self.incidence_proj = nn.Sequential(
            nn.Linear(2, incidence_dim), nn.GELU(), nn.Linear(incidence_dim, incidence_dim))
        self.incidence_missing = nn.Parameter(torch.zeros(incidence_dim))
        nn.init.trunc_normal_(self.incidence_missing, std=0.02)

        fused = orbit_dim + relorbit_dim + sat_dim + incidence_dim
        self.fuse = nn.Sequential(nn.Linear(fused, embed_dim), nn.GELU())
        self.embed_dim = embed_dim

    def forward(self, phi: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        Args（均为 [B]，缺失：类别=-1，incidence=NaN，valid=0）:
            s1_orbit_direction, s1_relative_orbit, s1_satellite,
            s1_incidence_angle, s1_incidence_valid
        Returns: [B, embed_dim]

        当整个 SAR 几何字段缺失时（如 S2 样本，phi 里根本没有 s1_* 键），
        全部走 missing 分支 → 输出稳定的 all-missing 嵌入，不产生 NaN、不崩。
        """
        # 推断 batch 大小与设备（SAR 字段可能全缺，需从其它 phi 字段兜底）
        ref = phi.get('s1_orbit_direction')
        if not isinstance(ref, torch.Tensor):
            # S2 样本：无任何 SAR 字段。用其它标量字段推断 [B] 与 device。
            for k in ('modality', 'season', 'sun_elevation', 'center_lat'):
                cand = phi.get(k)
                if isinstance(cand, torch.Tensor):
                    ref = cand
                    break
            device = ref.device if isinstance(ref, torch.Tensor) else 'cpu'
            B = ref.shape[0] if isinstance(ref, torch.Tensor) else 1
            miss = torch.full((B,), -1, dtype=torch.long, device=device)
            orbit = rel = sat = miss
            inc = None
            inc_valid = None
        else:
            device = ref.device
            orbit = phi.get('s1_orbit_direction')
            rel = phi.get('s1_relative_orbit')
            sat = phi.get('s1_satellite')
            inc = phi.get('s1_incidence_angle')
            inc_valid = phi.get('s1_incidence_valid')

        orbit_idx = torch.where(orbit >= 0, orbit, torch.full_like(orbit, 2))  # -1→2(missing)
        orbit_feat = self.orbit_embed(orbit_idx)

        rel_idx = torch.where((rel >= 1) & (rel <= 175), rel, torch.zeros_like(rel))  # 非法/缺失→0
        rel_feat = self.relorbit_embed(rel_idx)

        sat_idx = torch.where(sat >= 0, sat, torch.full_like(sat, 2))  # -1→2(missing)
        sat_feat = self.sat_embed(sat_idx)

        # incidence（占位；当前数据恒缺失 → 走 missing）
        if inc is None:
            inc_feat = self.incidence_missing.expand(orbit_feat.shape[0], -1)
        else:
            inc_clean = torch.nan_to_num(inc, nan=0.0)
            rad = torch.deg2rad(inc_clean).unsqueeze(-1)
            inc_in = torch.cat([torch.sin(rad), torch.cos(rad)], dim=-1)
            inc_proj = self.incidence_proj(inc_in)
            valid_b = (inc_valid > 0).unsqueeze(-1) if inc_valid is not None else torch.zeros_like(inc_proj[..., :1]).bool()
            inc_feat = torch.where(valid_b, inc_proj, self.incidence_missing.expand_as(inc_proj))

        fused = torch.cat([orbit_feat, rel_feat, sat_feat, inc_feat], dim=-1)
        return self.fuse(fused)


# ============================================================
# 主模块：ImagingConditionEncoder
# ============================================================
class ImagingConditionEncoder(nn.Module):
    """成像条件编码器（单时间片严格对齐版）。

    输入：phi_dict（单时间片，时序字段为标量 [B]），输出：
    - phi_embed: [B, embed_dim] 成像条件向量（用于 FiLM γ/β）
    - phi_tokens: [B, 1, embed_dim] token（用于 cross-attention，单时间片只有 1 个）

    架构（无时序聚合）：
        sun_elev [B] ──┐
        season   [B] ──┤
        cloud    [B] ──┼── concat → proj → phi_embed [B, D]
        lat/lon  [B] ──┤
        modality [B] ──┘

    Args:
        embed_dim: 输出维度（与 ViT encoder embed_dim 一致）
        sun_dim, season_dim, latlon_dim, cloud_dim, modality_dim: 各子编码器维度
        num_frequencies: lat/lon 多频编码层数
        dropout: dropout 率
        time_steps / time_aggregation: 已废弃（保留入参以兼容旧 config，忽略其值）
    """

    def __init__(
        self,
        embed_dim: int = 256,
        sun_dim: int = 64,
        season_dim: int = 32,
        latlon_dim: int = 64,
        cloud_dim: int = 32,
        modality_dim: int = 32,
        num_frequencies: int = 4,
        dropout: float = 0.0,
        time_steps: int = 4,            # 废弃，忽略（向后兼容旧 config）
        time_aggregation: str = 'mean', # 废弃，忽略
        use_sar_geometry: bool = False, # phi v3：是否启用 S1 SAR 几何编码（默认关闭，不破坏旧 config）
        sar_geom_dim: int = 64,
    ):
        super().__init__()
        self.embed_dim = embed_dim
        self.use_sar_geometry = use_sar_geometry

        # 子编码器（均为 last-dim 投影，天然支持 [B] 单时间片输入 → [B, D]）
        self.sun_encoder = SunElevationEncoder(sun_dim)
        self.season_encoder = SeasonEncoder(season_dim)
        self.latlon_encoder = LatLonEncoder(num_frequencies, latlon_dim)
        self.cloud_encoder = CloudEncoder(cloud_dim)
        self.modality_encoder = ModalityEncoder(num_modalities=6, embed_dim=modality_dim)

        # phi v3：可选 SAR 几何编码器
        if use_sar_geometry:
            self.sar_geom_encoder = SARGeometryEncoder(embed_dim=sar_geom_dim)

        # 全部字段拼接维度
        fused_dim = sun_dim + season_dim + cloud_dim + latlon_dim + modality_dim
        if use_sar_geometry:
            fused_dim += sar_geom_dim

        # 融合投影 → embed_dim
        self.fuse_proj = nn.Sequential(
            nn.Linear(fused_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim, embed_dim),
            nn.LayerNorm(embed_dim),
        )

    def _prepare_valid_masks(self, phi: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """从单时间片 phi dict 构造各字段的 valid mask（均为 [B]）。

        约定（单时间片）：缺失值已填充为 float→NaN / int→-1。
        """
        masks = {}
        # 时间片有效性：优先用 time_valid [B]，否则用 sun_elevation 是否 NaN
        if 'time_valid' in phi:
            masks['time'] = (phi['time_valid'] > 0).float()
        else:
            masks['time'] = (~torch.isnan(phi.get('sun_elevation', torch.zeros(1)))).float()

        masks['lat'] = (~torch.isnan(phi.get('center_lat', torch.zeros(1)))).float()
        masks['lon'] = (~torch.isnan(phi.get('center_lon', torch.zeros(1)))).float()
        masks['latlon'] = (masks['lat'] * masks['lon']).float()
        return masks

    def forward(self, phi: Dict[str, torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            phi: dict（单时间片），包含以下 tensors:
                - center_lat, center_lon: [B] float (NaN if missing)
                - modality: [B] long (-1 if missing)
                - time_valid: [B] long (1/0)
                - sun_elevation: [B] float (NaN if missing)
                - season: [B] long (-1 if missing)
                - cloud_cover, cloud_shadow, valid_ratio: [B] float

        Returns:
            phi_embed: [B, embed_dim] 成像条件向量
            phi_tokens: [B, 1, embed_dim] 单时间片 token（供 cross-attention）
        """
        masks = self._prepare_valid_masks(phi)
        time_valid = masks['time']  # [B]

        # 各字段编码（均返回 [B, dim]）
        sun_feat = self.sun_encoder(phi['sun_elevation'], time_valid)          # [B, sun_dim]
        season_feat = self.season_encoder(phi['season'], time_valid)           # [B, season_dim]
        cloud_feat = self.cloud_encoder(
            phi['cloud_cover'], phi['cloud_shadow'], phi['valid_ratio'], time_valid
        )                                                                       # [B, cloud_dim]
        latlon_feat = self.latlon_encoder(
            phi['center_lat'], phi['center_lon'], masks['latlon']
        )                                                                       # [B, latlon_dim]
        modality_feat = self.modality_encoder(phi['modality'])                  # [B, modality_dim]

        fused = torch.cat([sun_feat, season_feat, cloud_feat, latlon_feat, modality_feat], dim=-1)
        if self.use_sar_geometry:
            sar_feat = self.sar_geom_encoder(phi)                               # [B, sar_geom_dim]
            fused = torch.cat([fused, sar_feat], dim=-1)
        phi_embed = self.fuse_proj(fused)                                       # [B, embed_dim]

        # 单时间片 → 1 个 token（cross-attention 接口保持 [B, T, D] 形状）
        phi_tokens = phi_embed.unsqueeze(1)                                     # [B, 1, embed_dim]
        return phi_embed, phi_tokens

    def get_config(self) -> dict:
        return {
            'embed_dim': self.embed_dim,
            'single_timestep': True,
        }
        season_feat = self.season_encoder(phi['season'], time_valid)          # [B, T, season_dim]
        cloud_feat = self.cloud_encoder(
            phi['cloud_cover'], phi['cloud_shadow'], phi['valid_ratio'], time_valid
        )                                                                       # [B, T, cloud_dim]
        time_token_in = torch.cat([sun_feat, season_feat, cloud_feat], dim=-1)  # [B, T, time_token_dim]

if __name__ == '__main__':
    # 自测：单时间片 phi（每字段为标量 [B]）
    print("=== ImagingConditionEncoder 自测（单时间片）===")
    encoder = ImagingConditionEncoder(embed_dim=256)

    B = 4
    phi = {
        'center_lat': torch.tensor([33.67, -33.67, 0.0, float('nan')]),
        'center_lon': torch.tensor([47.22, 47.22, 0.0, 100.0]),
        'modality': torch.tensor([0, 0, 1, -1], dtype=torch.long),  # S2L2A, S2L2A, S1GRD, missing
        'time_valid': torch.tensor([1, 1, 1, 0], dtype=torch.long),
        'sun_elevation': torch.tensor([40.0, 30.0, 50.0, float('nan')]),
        'season': torch.tensor([3, 1, 0, -1], dtype=torch.long),
        'cloud_cover': torch.tensor([0.0, 0.2, float('nan'), 0.0]),   # 第3个模拟 S1 无云
        'cloud_shadow': torch.tensor([0.0, 0.05, float('nan'), 0.0]),
        'valid_ratio': torch.tensor([1.0, 1.0, float('nan'), 1.0]),
    }

    phi_embed, phi_tokens = encoder(phi)
    print(f"phi_embed shape: {phi_embed.shape} (预期 [{B}, 256])")
    print(f"phi_tokens shape: {phi_tokens.shape} (预期 [{B}, 1, 256])")
    print(f"phi_embed 数值范围: [{phi_embed.min().item():.3f}, {phi_embed.max().item():.3f}]")
    print(f"参数量: {sum(p.numel() for p in encoder.parameters()) / 1e3:.1f}K")

    assert phi_tokens.shape == (B, 1, 256), "phi_tokens 应为 [B,1,D]"
    assert not torch.isnan(phi_embed).any(), "phi_embed 含 NaN！"
    # 梯度可传 + 无 NaN
    loss = phi_embed.pow(2).mean(); loss.backward()
    gnan = any(p.grad is not None and torch.isnan(p.grad).any() for p in encoder.parameters())
    assert not gnan, "梯度含 NaN！"
    print("\n✓ 单时间片 + 缺失值（含 S1 无云）处理正确，无 NaN 传播")
    print("✓ ImagingConditionEncoder 自测通过")