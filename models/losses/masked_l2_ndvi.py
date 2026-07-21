"""Vendored MaskedL2NDVILoss from earthnet-models-pytorch @ v0.1.0
(earthnet_models_pytorch/task/loss.py). Pure torch — used to train the
reproduced Contextformer (B0) and later B1-B4 in our torch-2.x stack.

Faithful copy of __init__/forward. The loss = masked L2 on predicted vs target
NDVI over the target window, restricted to clear (cloud mask <1), vegetation
(lc in [lc_min, lc_max]) and valid-prediction (pred != pred_mask_value) pixels.
Consumes the same batch dict our data adapter yields:
  batch["dynamic"][0]      sen2arr (B,30,5,H,W) — NDVI truth at channel ndvi_targ_idx=0
  batch["dynamic_mask"][0] cloud mask (B,30,1,H,W)
  batch["landcover"]       esawc_lc (B,1,H,W)
`preds` = model output (B, N, 1, H, W); the target window is the last target_length frames.
"""

import torch
import torch.nn as nn


class MaskedL2NDVILoss(nn.Module):
    def __init__(
        self,
        lc_min=None,
        lc_max=None,
        context_length=None,
        target_length=None,
        ndvi_pred_idx=0,
        ndvi_targ_idx=0,
        pred_mask_value=None,
        scale_by_std=False,
        weight_by_std=False,
        extra_aux_loss_term=None,
        extra_aux_loss_weight=1,
        mask_hq_only=False,
        **kwargs,
    ):
        super().__init__()
        self.lc_min = lc_min if lc_min else None
        self.lc_max = lc_max if lc_max else None
        self.use_lc = bool(self.lc_min) and bool(self.lc_max)
        self.context_length = context_length
        self.target_length = target_length
        self.ndvi_pred_idx = ndvi_pred_idx
        self.ndvi_targ_idx = ndvi_targ_idx
        self.pred_mask_value = pred_mask_value
        self.scale_by_std = scale_by_std
        self.weight_by_std = weight_by_std
        self.extra_aux_loss_term = extra_aux_loss_term
        self.extra_aux_loss_weight = extra_aux_loss_weight
        self.mask_hq_only = mask_hq_only

    def forward(self, preds, batch, aux=None, current_step=None):
        aux = aux or {}
        cl, tl = self.context_length, self.target_length

        # Cloud mask over the target window (clear == mask < 1)
        s2_mask = (
            (batch["dynamic_mask"][0][:, cl:cl + tl, ...] < 1.0).bool().type_as(preds)
        )  # b t c h w

        # Landcover (vegetation) mask
        lc = batch["landcover"]
        lc_mask = ((lc >= self.lc_min).bool() & (lc <= self.lc_max).bool()).type_as(
            preds
        )  # b c h w

        ndvi_targ = batch["dynamic"][0][:, cl:cl + tl, self.ndvi_targ_idx, ...].unsqueeze(2)
        ndvi_pred = preds[:, -ndvi_targ.shape[1]:, self.ndvi_pred_idx, ...].unsqueeze(2)

        sum_squared_error = (((ndvi_targ - ndvi_pred) * s2_mask) ** 2).sum(1)  # b c h w
        mse = sum_squared_error / (s2_mask.sum(1) + 1e-8)  # b c h w

        if self.scale_by_std:
            mean_ndvi_targ = (ndvi_targ * s2_mask).sum(1).unsqueeze(1) / (
                s2_mask.sum(1).unsqueeze(1) + 1e-8
            )
            sum_squared_deviation = (((ndvi_targ - mean_ndvi_targ) * s2_mask) ** 2).sum(1)
            mse = sum_squared_error / sum_squared_deviation.clip(min=0.01)
        elif self.weight_by_std:
            mean_ndvi_targ = (ndvi_targ * s2_mask).sum(1).unsqueeze(1) / (
                s2_mask.sum(1).unsqueeze(1) + 1e-8
            )
            sum_squared_deviation = (((ndvi_targ - mean_ndvi_targ) * s2_mask) ** 2).sum(1)
            mse = sum_squared_error * (
                ((sum_squared_deviation / (s2_mask.sum(1) + 1e-8)) ** 0.5) / 0.1
            ).clip(min=0.01, max=100.0)

        if self.pred_mask_value is not None:
            pred_mask = (
                (ndvi_pred != self.pred_mask_value).bool().type_as(preds).max(1)[0]
            )
            mse_lc = (mse * lc_mask * pred_mask).sum() / ((lc_mask * pred_mask).sum() + 1e-8)
        elif self.use_lc:
            mse_lc = (mse * lc_mask).sum() / (lc_mask.sum() + 1e-8)
        else:
            mse_lc = mse.mean()

        logs = {"loss": mse_lc.detach()}
        if self.extra_aux_loss_term:
            extra_loss = aux[self.extra_aux_loss_term]
            logs["mse_lc"] = mse_lc.detach()
            logs[self.extra_aux_loss_term] = extra_loss.detach()
            mse_lc = mse_lc + self.extra_aux_loss_weight * extra_loss
            logs["loss"] = mse_lc.detach()
        return mse_lc, logs
