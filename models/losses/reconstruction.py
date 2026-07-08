"""
用于掩码图像建模（masked image modeling）的重建损失。

实现了多种重建损失，用于计算预测 patch 与目标 patch 之间的差异，
并支持仅在掩码（masked）区域上计算损失。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class MaskedL1Loss(nn.Module):
    """
    仅在掩码 patch 上计算的 L1 损失。

    Args:
        reduction: 指定对输出应用的归约方式：
                  'none' | 'mean' | 'sum'。默认值：'mean'
    """

    def __init__(self, reduction='mean'):
        super().__init__()
        self.reduction = reduction

    def forward(self, pred, target, mask):
        """
        在掩码区域上计算 L1 损失。

        Args:
            pred: 预测值，形状为 (B, C, H, W)
            target: 目标值，与 pred 形状相同
            mask: 二值掩码，形状为 (B, N)，1 表示被掩码的 patch

        Returns:
            损失值
        """
        loss = F.l1_loss(pred, target, reduction='none')

        # 如果 mask 处于 patch 空间 (B, N)，则将其扩展到像素空间 (B, 1, H, W)
        if mask.dim() == 2:
            B, N = mask.shape
            H, W = pred.shape[2], pred.shape[3]
            patch_size = int((H * W / N) ** 0.5)

            # 将 mask 重塑为空间网格
            num_patches_side = int(N ** 0.5)
            mask_spatial = mask.reshape(B, num_patches_side, num_patches_side)

            # 上采样到像素分辨率
            mask_spatial = mask_spatial.unsqueeze(1)  # (B, 1, h, w)
            mask_pixel = mask_spatial.repeat_interleave(patch_size, dim=2).repeat_interleave(patch_size, dim=3)
        else:
            # mask 已处于像素空间
            mask_pixel = mask
            if mask_pixel.dim() < loss.dim():
                mask_pixel = mask_pixel.unsqueeze(1)

        # 应用掩码
        loss = loss * mask_pixel

        if self.reduction == 'mean':
            return loss.sum() / (mask_pixel.sum() + 1e-8)
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss


class MaskedMSELoss(nn.Module):
    """
    仅在掩码 patch 上计算的 MSE 损失。

    Args:
        reduction: 指定对输出应用的归约方式：
                  'none' | 'mean' | 'sum'。默认值：'mean'
    """

    def __init__(self, reduction='mean'):
        super().__init__()
        self.reduction = reduction

    def forward(self, pred, target, mask):
        """
        在掩码区域上计算 MSE 损失。

        Args:
            pred: 预测值，形状为 (B, C, H, W)
            target: 目标值，与 pred 形状相同
            mask: 二值掩码，形状为 (B, N)，其中 N 为 patch 数量，1 表示被掩码的 patch

        Returns:
            损失值
        """
        loss = F.mse_loss(pred, target, reduction='none')

        # 如果 mask 处于 patch 空间 (B, N)，则将其扩展到像素空间 (B, 1, H, W)
        if mask.dim() == 2:
            B, N = mask.shape
            H, W = pred.shape[2], pred.shape[3]
            patch_size = int((H * W / N) ** 0.5)

            # 将 mask 重塑为空间网格：(B, N) -> (B, sqrt(N), sqrt(N))
            num_patches_side = int(N ** 0.5)
            mask_spatial = mask.reshape(B, num_patches_side, num_patches_side)

            # 使用 repeat_interleave 将 mask 上采样到像素分辨率
            mask_spatial = mask_spatial.unsqueeze(1)  # (B, 1, h, w)
            mask_pixel = mask_spatial.repeat_interleave(patch_size, dim=2).repeat_interleave(patch_size, dim=3)
        else:
            # mask 已处于像素空间
            mask_pixel = mask
            if mask_pixel.dim() < loss.dim():
                mask_pixel = mask_pixel.unsqueeze(1)

        # 应用掩码
        loss = loss * mask_pixel

        if self.reduction == 'mean':
            return loss.sum() / (mask_pixel.sum() + 1e-8)
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss


class CharbonnierLoss(nn.Module):
    """
    Charbonnier 损失（L1 损失的一种平滑变体），在掩码 patch 上计算。

    Charbonnier 损失定义为：
        L = sqrt((pred - target)^2 + eps^2)

    它在零点处可微，并提供了对 L1 损失的平滑近似。

    Args:
        eps: 平滑参数。默认值：1e-3
        reduction: 指定对输出应用的归约方式：
                  'none' | 'mean' | 'sum'。默认值：'mean'
    """

    def __init__(self, eps=1e-3, reduction='mean'):
        super().__init__()
        self.eps = eps
        self.reduction = reduction

    def forward(self, pred, target, mask):
        """
        在掩码区域上计算 Charbonnier 损失。

        Args:
            pred: 预测值，形状为 (B, N, C) 或 (B, C, H, W)
            target: 目标值，与 pred 形状相同
            mask: 二值掩码，形状为 (B, N) 或 (B, 1, H, W)，1 表示被掩码的 patch

        Returns:
            损失值
        """
        diff = pred - target
        loss = torch.sqrt(diff * diff + self.eps * self.eps)

        # 将 mask 扩展以匹配 loss 的维度
        if mask.dim() < loss.dim():
            mask = mask.unsqueeze(-1)

        # 应用掩码
        loss = loss * mask

        if self.reduction == 'mean':
            return loss.sum() / (mask.sum() + 1e-8)
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss


def get_reconstruction_loss(loss_type, **kwargs):
    """
    用于创建重建损失实例的工厂函数。

    Args:
        loss_type: 要创建的损失类型。取值之一：
                  'masked_l1', 'masked_mse', 'charbonnier'
        **kwargs: 传递给损失构造函数的额外参数

    Returns:
        损失模块（module）实例

    Raises:
        ValueError: 如果 loss_type 无法识别

    Examples:
        >>> loss_fn = get_reconstruction_loss('masked_l1')
        >>> loss_fn = get_reconstruction_loss('charbonnier', eps=1e-3)
        >>> loss_fn = get_reconstruction_loss('masked_mse', reduction='sum')
    """
    loss_type = loss_type.lower()

    if loss_type == 'masked_l1':
        return MaskedL1Loss(**kwargs)
    elif loss_type == 'masked_mse':
        return MaskedMSELoss(**kwargs)
    elif loss_type == 'charbonnier':
        return CharbonnierLoss(**kwargs)
    else:
        available = ['masked_l1', 'masked_mse', 'charbonnier']
        raise ValueError(
            f"Unknown loss type: {loss_type}. "
            f"Available types: {available}"
        )


# 可用的损失类型列表
AVAILABLE_LOSSES = ['masked_l1', 'masked_mse', 'charbonnier']
