"""
成像解耦损失（Imaging Decoupling Losses）

实现两个核心解耦目标（对应 任务描述相关/13_*.md §6.5）：

1. 跨成像一致性损失（cross-imaging consistency）
   同一地表在不同成像条件（季节/光照/模态）下，latent 应更接近。
   实现：同一 batch 内同 sample 不同时间片的 latent 距离，作为正例 InfoNCE 拉近。

2. 反事实解耦损失（counterfactual decoupling）
   替换 phi（保持 image 不变），latent 应反映"地表状态相似"的事实。
   实现：phi shuffle 后 latent 不应随之剧烈变化（用 L2 + 阈值惩罚）。

3. （可选）phi 解相关损失
   latent 应与 phi_embed 解相关（成像条件信息不留在地表状态中）。
   实现：cosine 相似度约束 + 解相关惩罚。

所有 loss 都支持 field_mask gating（缺失字段时降级或跳过）。

参考：
- InfoNCE: van den Oord et al., 2018
- Counterfactual representation learning (Lopez-Paz et al.)
- 文档约束（10_*.md §阶段1.5 损失部分）
"""

from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


# ============================================================
# 跨成像一致性损失（InfoNCE-style）
# ============================================================
class CrossImagingConsistencyLoss(nn.Module):
    """同一样本不同 phi 条件下的 latent 应更接近（正例），
    与不同样本的 latent 远离（负例）。

    实现：把 batch 内"同 sample_id 不同时间片"作为正例对，
    其他样本作为负例。

    使用方式：训练时一个 batch 内对同一组 sample 用两个不同 phi 视图前向，
    得到 z_view1 / z_view2，本损失拉近它们的全局 token 平均。
    """

    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature

    def forward(
        self,
        z_view1: torch.Tensor,
        z_view2: torch.Tensor,
        valid_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            z_view1, z_view2: [B, D] 同 batch 两次不同 phi 视图的全局表示
                              （由 latent.mean(dim=1) 或 [CLS] token 提取）
            valid_mask: [B] 1=有效对，0=跳过

        Returns:
            loss 标量
        """
        z1 = F.normalize(z_view1, dim=-1)
        z2 = F.normalize(z_view2, dim=-1)

        B = z1.shape[0]
        # [B, B] similarity matrix
        sim_matrix = z1 @ z2.T / self.temperature

        # 对角线是正例
        labels = torch.arange(B, device=z1.device)
        ce_loss = F.cross_entropy(sim_matrix, labels, reduction='none')

        if valid_mask is not None:
            valid_mask = valid_mask.float()
            ce_loss = (ce_loss * valid_mask).sum() / valid_mask.sum().clamp_min(1e-6)
        else:
            ce_loss = ce_loss.mean()
        return ce_loss


# ============================================================
# 反事实解耦损失
# ============================================================
class CounterfactualDecouplingLoss(nn.Module):
    """phi 替换后 latent 不应剧烈变化。

    实现：对同一图像分别用真实 phi 和 shuffle 后的 phi 前向，
    比较两个 latent 的距离。距离应被约束在阈值内（说明 phi 不主导 latent）。
    """

    def __init__(self, margin: float = 0.5, reduction: str = 'mean'):
        super().__init__()
        self.margin = margin
        self.reduction = reduction

    def forward(
        self,
        z_real_phi: torch.Tensor,
        z_shuffled_phi: torch.Tensor,
        valid_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            z_real_phi, z_shuffled_phi: [B, D]
            valid_mask: [B] 1=参与

        Returns:
            loss 标量；理想情况是 ||z1-z2|| 接近 0（不超过 margin 也行）
        """
        # 用 1 - cosine 相似度（更稳定）
        z1 = F.normalize(z_real_phi, dim=-1)
        z2 = F.normalize(z_shuffled_phi, dim=-1)
        dist = 1.0 - (z1 * z2).sum(dim=-1)  # [B]

        # 超过 margin 才惩罚
        loss = F.relu(dist - self.margin)

        if valid_mask is not None:
            valid_mask = valid_mask.float()
            loss = (loss * valid_mask).sum() / valid_mask.sum().clamp_min(1e-6)
        elif self.reduction == 'mean':
            loss = loss.mean()
        else:
            loss = loss.sum()
        return loss


# ============================================================
# phi 解相关损失
# ============================================================
class PhiDecorrelationLoss(nn.Module):
    """latent 应与 phi_embed 解相关。

    实现：cosine 相似度的绝对值作为惩罚（鼓励正交）。
    """

    def __init__(self, target: float = 0.0):
        super().__init__()
        self.target = target

    def forward(
        self,
        z: torch.Tensor,
        phi_embed: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            z: [B, D] latent（全局表示）
            phi_embed: [B, D] 成像条件 embedding

        Returns:
            loss = (|cosine(z, phi)| - target)^2.mean()
        """
        z_n = F.normalize(z, dim=-1)
        p_n = F.normalize(phi_embed, dim=-1)
        cos = (z_n * p_n).sum(dim=-1)  # [B]
        loss = (cos.abs() - self.target) ** 2
        return loss.mean()


# ============================================================
# 综合解耦损失（带权重和 mask）
# ============================================================
class ImagingDecouplingLoss(nn.Module):
    """综合三种解耦损失，统一接口。

    Loss 组合：
        L = w_consistency * L_consistency
          + w_counterfactual * L_counterfactual
          + w_decorr * L_decorrelation
    """

    def __init__(
        self,
        w_consistency: float = 1.0,
        w_counterfactual: float = 0.5,
        w_decorr: float = 0.1,
        temperature: float = 0.07,
        cf_margin: float = 0.5,
    ):
        super().__init__()
        self.w_consistency = w_consistency
        self.w_counterfactual = w_counterfactual
        self.w_decorr = w_decorr

        self.consistency = CrossImagingConsistencyLoss(temperature=temperature)
        self.counterfactual = CounterfactualDecouplingLoss(margin=cf_margin)
        self.decorr = PhiDecorrelationLoss()

    def forward(
        self,
        z_view1: torch.Tensor,
        z_view2: torch.Tensor,
        z_shuffled: Optional[torch.Tensor] = None,
        phi_embed: Optional[torch.Tensor] = None,
        valid_mask: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Args:
            z_view1, z_view2: [B, D] 同样本不同 phi 视图（必填，consistency）
            z_shuffled: [B, D] 同图像 + shuffle phi 视图（可选，counterfactual）
            phi_embed: [B, D] phi 编码（可选，decorrelation）
            valid_mask: [B] 字段有效性 mask

        Returns:
            dict: {'total', 'consistency', 'counterfactual', 'decorr'}
                  缺失项为 0
        """
        out = {}
        out['consistency'] = self.consistency(z_view1, z_view2, valid_mask)
        total = self.w_consistency * out['consistency']

        if z_shuffled is not None:
            out['counterfactual'] = self.counterfactual(z_view1, z_shuffled, valid_mask)
            total = total + self.w_counterfactual * out['counterfactual']
        else:
            out['counterfactual'] = torch.zeros((), device=z_view1.device)

        if phi_embed is not None:
            out['decorr'] = self.decorr(z_view1, phi_embed)
            total = total + self.w_decorr * out['decorr']
        else:
            out['decorr'] = torch.zeros((), device=z_view1.device)

        out['total'] = total
        return out

    def get_config(self) -> dict:
        return {
            'w_consistency': self.w_consistency,
            'w_counterfactual': self.w_counterfactual,
            'w_decorr': self.w_decorr,
        }


if __name__ == '__main__':
    print("=== ImagingDecouplingLoss 自测 ===")

    loss_fn = ImagingDecouplingLoss(w_consistency=1.0, w_counterfactual=0.5, w_decorr=0.1)

    B, D = 8, 256
    z1 = torch.randn(B, D, requires_grad=True)
    z2 = z1.detach().clone() + 0.1 * torch.randn(B, D)  # 同样本不同视图
    z_shuffled = torch.randn(B, D)  # phi shuffle 后
    phi = torch.randn(B, D)

    out = loss_fn(z1, z2, z_shuffled=z_shuffled, phi_embed=phi)
    print(f"total: {out['total'].item():.4f}")
    print(f"  consistency: {out['consistency'].item():.4f}")
    print(f"  counterfactual: {out['counterfactual'].item():.4f}")
    print(f"  decorr: {out['decorr'].item():.4f}")

    # 验证梯度可传
    out['total'].backward()
    print(f"\nz1.grad norm: {z1.grad.norm().item():.4f} ✓ (梯度可传)")

    # mask 测试
    valid = torch.tensor([1, 1, 0, 1, 0, 1, 1, 1], dtype=torch.float)
    z1_new = z1.detach().clone().requires_grad_(True)
    out_masked = loss_fn(z1_new, z2, z_shuffled=z_shuffled, phi_embed=phi, valid_mask=valid)
    print(f"\nmasked total: {out_masked['total'].item():.4f} ✓")

    print("\n✓ ImagingDecouplingLoss 自测通过")