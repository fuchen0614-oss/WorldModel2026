"""ObsWorld 状态动力学模块。

输入当前地表状态 ``z_t``、外生驱动 ``D``、地理背景 ``G`` 和预测跨度
``h`` 的编码，直接预测对应跨度的未来状态 ``z_{t+h}``。EarthNet 主实验会
同时请求多个 h，因此同一个上下文状态可并行得到多跨度结果。
"""

from typing import Optional

import torch
import torch.nn as nn


class StateDynamicsModule(nn.Module):
    """状态动力学：给定当前状态 z_t + 驱动 D + 地理 G，预测未来状态 z_{t+h}。

    Args:
        latent_dim: Stage1.5 状态投影后的 token 维度。
        dynamics_type: 'gru' | 'transformer' | 'mlp'
        driver_dim: 外生驱动编码维度；0 表示不使用。
        geo_dim: 地理编码维度；0 表示不使用。
        time_dim: 预测跨度编码维度。
        hidden_dim: 内部隐藏维度
        num_layers: GRU/Transformer 层数
    """

    def __init__(
        self,
        latent_dim: int = 256,
        dynamics_type: str = 'gru',
        driver_dim: int = 0,
        geo_dim: int = 0,
        time_dim: int = 1,
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
        self.time_dim = time_dim

        # 条件投影：把 [z_t ; D ; G ; time_delta] 投到 hidden_dim
        cond_in = latent_dim + driver_dim + geo_dim + time_dim
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

        # 常规缺失掩膜由条件编码器处理。这里的常量仅覆盖直接传入 None
        # 的兼容路径，不应成为正式训练中的闲置参数。
        if driver_dim > 0:
            self.register_buffer(
                "driver_missing",
                torch.zeros(driver_dim),
                persistent=True,
            )
        if geo_dim > 0:
            self.register_buffer(
                "geo_missing",
                torch.zeros(geo_dim),
                persistent=True,
            )

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
            geo: [B, geo_dim] 或 [B, N, geo_dim] 地理先验 G
            time_delta: [B,time_dim] 预测跨度 h 的编码。

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
            time_delta = torch.ones(B, self.time_dim, device=device)
        elif time_delta.dim() == 1:
            time_delta = time_delta[:, None]
        if time_delta.shape != (B, self.time_dim):
            raise ValueError(
                f"time_delta must be [B,{self.time_dim}], got {tuple(time_delta.shape)}"
            )
        td = time_delta[:, None, :].expand(B, N, self.time_dim).float()

        feats = [z_t, td]
        if self.driver_dim > 0:
            if driver is None:
                driver = self.driver_missing.expand(B, self.driver_dim)
            feats.insert(1, driver.unsqueeze(1).expand(B, N, self.driver_dim))
        if self.geo_dim > 0:
            if geo is None:
                geo = self.geo_missing.expand(B, self.geo_dim)
            if geo.dim() == 2:
                geo_feat = geo.unsqueeze(1).expand(B, N, self.geo_dim)
            elif geo.dim() == 3:
                if geo.shape[1] != N or geo.shape[2] != self.geo_dim:
                    raise ValueError(
                        f"geo token shape must be [B,{N},{self.geo_dim}], got {tuple(geo.shape)}"
                    )
                geo_feat = geo
            else:
                raise ValueError(f"geo must be [B,G] or [B,N,G], got {tuple(geo.shape)}")
            feats.insert(-1, geo_feat)

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

        if squeeze_back:
            z_pred = z_pred.squeeze(1)
        return z_pred

    def get_config(self) -> dict:
        return {
            'latent_dim': self.latent_dim,
            'dynamics_type': self.dynamics_type,
            'driver_dim': self.driver_dim,
            'geo_dim': self.geo_dim,
            'time_dim': self.time_dim,
        }


if __name__ == '__main__':
    print("=== StateDynamicsModule self-test ===")
    for dt in ('gru', 'transformer', 'mlp'):
        m = StateDynamicsModule(latent_dim=256, dynamics_type=dt, driver_dim=4, geo_dim=3)
        z = torch.randn(2, 16, 256)
        zp = m(z, driver=torch.randn(2, 4), geo=torch.randn(2, 3), time_delta=torch.tensor([1., 2.]))
        assert zp.shape == z.shape
        diff = (zp - z).abs().max().item()
        zp2 = m(torch.randn(2, 256))
        assert zp2.shape == (2, 256)
        print(
            f"  [{dt:11s}] token={tuple(zp.shape)} residual={diff:.2e}, "
            f"pooled={tuple(zp2.shape)}, "
            f"params={sum(p.numel() for p in m.parameters()) / 1e6:.2f}M"
        )
    print("StateDynamicsModule self-test passed.")
