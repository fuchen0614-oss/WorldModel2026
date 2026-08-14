"""
StateDynamicsLoss —— 状态动力学损失（Stage 2 骨架）

预测未来地表状态 z_{t+h} 的训练目标（见 13_*.md §1.1、总纲阶段 2）：

1. 预测损失（prediction）：z_pred 与 z_target 的距离
   - 在 latent 空间用 cosine / MSE（地表状态空间，非像素空间）
2. 平滑性损失（smoothness / temporal consistency）：
   - 相邻时刻状态变化不应剧烈跳变（一阶差分正则）
3. （可选）方向一致性：预测的状态变化方向与真实方向一致（cosine）

所有 loss 支持 valid_mask gating（缺失目标时跳过），与 Stage1.5 风格一致。

注意：真实训练需要 DynamicEarthNet / EarthNet 这类**时间序列**数据集
（同地点多时刻），SSL4EO 的 4 个时间片间隔不规则、不适合做精确动力学监督。
loader 与训练 loop 留 Stage 2，已用 TODO[Stage2] 标注。
"""

from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class StateDynamicsLoss(nn.Module):
    """状态动力学综合损失。

    L = w_pred * L_prediction + w_smooth * L_smoothness + w_dir * L_direction
    """

    def __init__(
        self,
        w_pred: float = 1.0,
        w_smooth: float = 0.1,
        w_dir: float = 0.0,
        pred_metric: str = 'cosine',  # 'cosine' | 'mse'
    ):
        super().__init__()
        self.w_pred = w_pred
        self.w_smooth = w_smooth
        self.w_dir = w_dir
        self.pred_metric = pred_metric

    def prediction_loss(self, z_pred, z_target, valid_mask=None):
        """预测损失：latent 空间距离。z_*: [B, ..., D]。"""
        if self.pred_metric == 'cosine':
            zp = F.normalize(z_pred, dim=-1)
            zt = F.normalize(z_target, dim=-1)
            per = 1.0 - (zp * zt).sum(dim=-1)  # [B, ...]
        else:  # mse
            per = (z_pred - z_target).pow(2).mean(dim=-1)
        return _masked_mean(per, valid_mask)

    def smoothness_loss(self, z_seq):
        """平滑性：相邻时刻一阶差分的 L2。z_seq: [B, T, D]（T>=2）。"""
        if z_seq.dim() != 3 or z_seq.shape[1] < 2:
            return torch.zeros((), device=z_seq.device)
        diff = z_seq[:, 1:] - z_seq[:, :-1]  # [B, T-1, D]
        return diff.pow(2).mean()

    def direction_loss(self, z_pred, z_t, z_target, valid_mask=None):
        """方向一致性：预测变化方向 (z_pred - z_t) 与真实 (z_target - z_t) 的 cosine。"""
        pred_dir = F.normalize(z_pred - z_t, dim=-1)
        true_dir = F.normalize(z_target - z_t, dim=-1)
        per = 1.0 - (pred_dir * true_dir).sum(dim=-1)
        return _masked_mean(per, valid_mask)

    def forward(
        self,
        z_pred: torch.Tensor,
        z_target: torch.Tensor,
        z_t: Optional[torch.Tensor] = None,
        z_seq: Optional[torch.Tensor] = None,
        valid_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Args:
            z_pred: [B, ..., D] 预测的 z_{t+h}
            z_target: [B, ..., D] 真实 z_{t+h}
            z_t: [B, ..., D] 当前状态（方向损失用，可选）
            z_seq: [B, T, D] 状态序列（平滑损失用，可选）
            valid_mask: [B, ...] 有效性

        Returns:
            dict: {'total', 'prediction', 'smoothness', 'direction'}
        """
        out = {}
        out['prediction'] = self.prediction_loss(z_pred, z_target, valid_mask)
        total = self.w_pred * out['prediction']

        if self.w_smooth > 0 and z_seq is not None:
            out['smoothness'] = self.smoothness_loss(z_seq)
            total = total + self.w_smooth * out['smoothness']
        else:
            out['smoothness'] = torch.zeros((), device=z_pred.device)

        if self.w_dir > 0 and z_t is not None:
            out['direction'] = self.direction_loss(z_pred, z_t, z_target, valid_mask)
            total = total + self.w_dir * out['direction']
        else:
            out['direction'] = torch.zeros((), device=z_pred.device)

        out['total'] = total
        # TODO[Stage2]: 加入 decoder 重建的端到端 loss（z_{t+h} → X_hat_{t+h} 与真实未来观测）
        return out

    def get_config(self) -> dict:
        return {'w_pred': self.w_pred, 'w_smooth': self.w_smooth,
                'w_dir': self.w_dir, 'pred_metric': self.pred_metric}


def _masked_mean(per_sample: torch.Tensor, valid_mask: Optional[torch.Tensor]) -> torch.Tensor:
    """对 per-sample loss 做（可选 mask 的）均值。"""
    if valid_mask is not None:
        vm = valid_mask.float()
        return (per_sample * vm).sum() / vm.sum().clamp_min(1e-6)
    return per_sample.mean()


if __name__ == '__main__':
    print("=== StateDynamicsLoss 骨架自测 ===")
    loss_fn = StateDynamicsLoss(w_pred=1.0, w_smooth=0.1, w_dir=0.5, pred_metric='cosine')
    B, T, D = 4, 5, 256
    z_t = torch.randn(B, D, requires_grad=True)
    z_pred = z_t.detach() + 0.1 * torch.randn(B, D)
    z_pred.requires_grad_(True)
    z_target = z_t.detach() + 0.12 * torch.randn(B, D)
    z_seq = torch.randn(B, T, D)
    out = loss_fn(z_pred, z_target, z_t=z_t, z_seq=z_seq)
    for k, v in out.items():
        print(f"  {k}: {v.item():.4f}")
    out['total'].backward()
    assert z_pred.grad is not None and not torch.isnan(z_pred.grad).any()
    # masked
    vm = torch.tensor([1, 1, 0, 1], dtype=torch.float)
    out_m = loss_fn(z_pred.detach().requires_grad_(True), z_target, z_t=z_t.detach(), valid_mask=vm)
    assert not torch.isnan(out_m['total'])
    print("✓ StateDynamicsLoss 骨架自测通过（梯度可传 + masked OK）")
