"""
StateDynamicsModule —— 状态动力学模块（Stage 2 骨架）

ObsWorld 主线（见 13_*.md §1.1）：
    z_t (当前地表状态) + D (外生驱动) + G (地理先验)
        → StateDynamicsModule → z_{t+h} (未来地表状态)

本文件提供**可运行的最小实现**（GRU / Transformer 二选一），但训练 loop、
真实的 D/G 注入、DynamicEarthNet/EarthNet loader 留到 Stage 2（已用 TODO[Stage2] 标注）。

设计要点：
- 输入 z_t [B, N, latent_dim]（来自 Stage1.5 encoder 的 patch tokens）或 [B, latent_dim]（池化后）
- driver D / geo G 为可选条件，通过 FiLM-style 或拼接注入（当前用拼接 + 投影）
- time_delta h 编码为标量条件（未来多步预测用）
- 输出与 z_t 同形状的 z_{t+h}

约束（与 Stage1.5 一致）：
- D/G 缺失时走 learnable missing embedding（接口预留，Stage2 实现 join）
- dynamics_type 可切换，方便消融
"""

from typing import Optional

import torch
import torch.nn as nn


class StateDynamicsModule(nn.Module):
    """状态动力学：给定当前状态 z_t + 驱动 D + 地理 G，预测未来状态 z_{t+h}。

    Args:
        latent_dim: 地表状态维度（= Stage1.5 encoder 的 embed_dim，默认 256）
        dynamics_type: 'gru' | 'transformer' | 'mlp'
        driver_dim: 外生驱动 D 的维度（ERA5 气象等，Stage2 join）；0 表示暂不使用
        geo_dim: 地理先验 G 的维度（DEM/坡度等）；0 表示暂不使用
        hidden_dim: 内部隐藏维度
        num_layers: GRU/Transformer 层数
    """

    def __init__(
        self,
        latent_dim: int = 256,
        dynamics_type: str = 'gru',
        driver_dim: int = 0,
        geo_dim: int = 0,
        hidden_dim: int = 256,
        num_layers: int = 2,
        num_heads: int = 4,
        dropout: float = 0.0,
    ):
        super().__init__()
        self.latent_dim = latent_dim
        self.dynamics_type = dynamics_type
        self.driver_dim = driver_dim
        self.geo_dim = geo_dim

        # 条件投影：把 [z_t ; D ; G ; time_delta] 投到 hidden_dim
        cond_in = latent_dim + driver_dim + geo_dim + 1  # +1 for time_delta scalar
        self.input_proj = nn.Linear(cond_in, hidden_dim)

        if dynamics_type == 'gru':
            self.core = nn.GRU(hidden_dim, hidden_dim, num_layers=num_layers,
                               batch_first=True, dropout=dropout if num_layers > 1 else 0.0)
        elif dynamics_type == 'transformer':
            layer = nn.TransformerEncoderLayer(
                d_model=hidden_dim, nhead=num_heads,
                dim_feedforward=hidden_dim * 4, dropout=dropout, batch_first=True)
            self.core = nn.TransformerEncoder(layer, num_layers=num_layers)
        elif dynamics_type == 'mlp':
            self.core = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim * 2), nn.GELU(),
                nn.Linear(hidden_dim * 2, hidden_dim))
        else:
            raise ValueError(f"Unknown dynamics_type: {dynamics_type}")

        # 输出投影回 latent_dim；零初始化使起点为"恒等动力学"（z_{t+h}≈z_t），训练更稳
        self.output_proj = nn.Linear(hidden_dim, latent_dim)
        nn.init.zeros_(self.output_proj.weight)
        nn.init.zeros_(self.output_proj.bias)

        # D/G 缺失时的 learnable missing embedding（接口预留）
        if driver_dim > 0:
            self.driver_missing = nn.Parameter(torch.zeros(driver_dim))
        if geo_dim > 0:
            self.geo_missing = nn.Parameter(torch.zeros(geo_dim))

    def forward(
        self,
        z_t: torch.Tensor,
        driver: Optional[torch.Tensor] = None,
        geo: Optional[torch.Tensor] = None,
        time_delta: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            z_t: [B, N, latent_dim] 或 [B, latent_dim] 当前地表状态
            driver: [B, driver_dim] 外生驱动 D（None → missing embedding / 跳过）
            geo: [B, geo_dim] 地理先验 G
            time_delta: [B] 预测步长 h（默认 1）

        Returns:
            z_pred: 与 z_t 同形状的 z_{t+h}（残差形式：z_t + Δ）
        """
        squeeze_back = False
        if z_t.dim() == 2:
            z_t = z_t.unsqueeze(1)  # [B,1,D]
            squeeze_back = True
        B, N, D = z_t.shape
        device = z_t.device

        if time_delta is None:
            time_delta = torch.ones(B, device=device)
        td = time_delta.view(B, 1, 1).expand(B, N, 1).float()

        feats = [z_t, td]
        if self.driver_dim > 0:
            if driver is None:
                driver = self.driver_missing.expand(B, self.driver_dim)
            feats.insert(1, driver.unsqueeze(1).expand(B, N, self.driver_dim))
        if self.geo_dim > 0:
            if geo is None:
                geo = self.geo_missing.expand(B, self.geo_dim)
            feats.insert(-1, geo.unsqueeze(1).expand(B, N, self.geo_dim))

        x = torch.cat(feats, dim=-1)
        h = self.input_proj(x)

        if self.dynamics_type == 'gru':
            h, _ = self.core(h)
        elif self.dynamics_type == 'transformer':
            h = self.core(h)
        else:  # mlp
            h = self.core(h)

        delta = self.output_proj(h)
        z_pred = z_t + delta  # 残差动力学：起点等价恒等

        # TODO[Stage2]: 多步 rollout（z_t → z_{t+1} → ... → z_{t+h}）、
        #               teacher forcing、以及 D/G 的真实 join（ERA5/DEM）。

        if squeeze_back:
            z_pred = z_pred.squeeze(1)
        return z_pred

    def get_config(self) -> dict:
        return {
            'latent_dim': self.latent_dim,
            'dynamics_type': self.dynamics_type,
            'driver_dim': self.driver_dim,
            'geo_dim': self.geo_dim,
        }


if __name__ == '__main__':
    print("=== StateDynamicsModule 骨架自测 ===")
    for dt in ('gru', 'transformer', 'mlp'):
        m = StateDynamicsModule(latent_dim=256, dynamics_type=dt, driver_dim=4, geo_dim=3)
        # token 形式
        z = torch.randn(2, 16, 256)
        zp = m(z, driver=torch.randn(2, 4), geo=torch.randn(2, 3), time_delta=torch.tensor([1., 2.]))
        assert zp.shape == z.shape
        # 起点应≈恒等（output_proj 零初始化）
        diff = (zp - z).abs().max().item()
        # 池化形式 + 缺失 D/G
        zp2 = m(torch.randn(2, 256))
        assert zp2.shape == (2, 256)
        print(f"  [{dt:11s}] token {tuple(zp.shape)} 残差≈{diff:.2e}, 池化 {tuple(zp2.shape)}, "
              f"params={sum(p.numel() for p in m.parameters())/1e6:.2f}M ✓")
    print("✓ StateDynamicsModule 骨架自测通过")
