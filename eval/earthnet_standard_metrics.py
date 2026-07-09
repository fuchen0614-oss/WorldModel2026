"""Official EarthNet2021 metric adapter.

This follows the public EarthNet metric implementation: MAD, OLS, EMD and
SSIM are computed per cube, then aggregated and combined using a harmonic mean.
The optional dependency is provided by the ``earthnet`` Python package.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np
import torch
import torch.nn.functional as F


class EarthNetScoreAccumulator:
    def __init__(self, eval_size: int = 128):
        try:
            import earthnet as en
        except ImportError as exc:
            raise ImportError(
                "Official EarthNet scoring requires the 'earthnet' package. "
                "Install it with: pip install earthnet==0.3.9"
            ) from exc
        self.calculator = en.parallel_score.CubeCalculator
        self.eval_size = int(eval_size)
        self.rows: List[Dict[str, float]] = []

    def update(
        self,
        preds: torch.Tensor,
        targets: torch.Tensor,
        clear_mask: torch.Tensor,
        names: Sequence[str],
    ) -> None:
        preds = _resize_video(preds.detach().float().clamp(0, 1), self.eval_size, "bilinear")
        targets = _resize_video(targets.detach().float().clamp(0, 1), self.eval_size, "bilinear")
        masks = _resize_mask(clear_mask.detach().float(), self.eval_size)

        pred_np = preds.cpu().numpy()
        target_np = targets.cpu().numpy()
        mask_np = masks.cpu().numpy()
        for i, name in enumerate(names):
            pred = np.transpose(pred_np[i], (2, 3, 1, 0))  # [H,W,C,T]
            target = np.transpose(target_np[i], (2, 3, 1, 0))
            mask_single = np.transpose(mask_np[i], (1, 2, 0))[:, :, None, :]
            mask = np.repeat(mask_single, pred.shape[2], axis=2)

            ndvi_pred = _ndvi_hwct(pred)
            ndvi_target = _ndvi_hwct(target)
            mad, _ = self.calculator.MAD(pred, target, mask)
            ols, _ = self.calculator.OLS(ndvi_pred, ndvi_target, mask_single)
            emd, _ = self.calculator.EMD(ndvi_pred, ndvi_target, mask_single)
            ssim, _ = self.calculator.SSIM(pred, target, mask)
            self.rows.append({
                "name": str(name),
                "MAD": mad,
                "OLS": ols,
                "EMD": emd,
                "SSIM": ssim,
            })

    def compute(self) -> Dict[str, float]:
        if not self.rows:
            return {}
        scores = np.asarray(
            [[row["MAD"], row["OLS"], row["EMD"], row["SSIM"]] for row in self.rows],
            dtype=np.float64,
        )
        mean_scores = np.nanmean(scores, axis=0)
        return {
            "ENS": _harmonic_mean(mean_scores.tolist()),
            "MAD": float(mean_scores[0]),
            "OLS": float(mean_scores[1]),
            "EMD": float(mean_scores[2]),
            "SSIM": float(mean_scores[3]),
            "num_scored_cubes": len(self.rows),
        }


def _resize_video(x: torch.Tensor, size: int, mode: str) -> torch.Tensor:
    b, t, c, h, w = x.shape
    if (h, w) == (size, size):
        return x
    y = F.interpolate(
        x.reshape(b * t, c, h, w),
        size=(size, size),
        mode=mode,
        align_corners=False,
    )
    return y.reshape(b, t, c, size, size)


def _resize_mask(x: torch.Tensor, size: int) -> torch.Tensor:
    b, t, h, w = x.shape
    if (h, w) == (size, size):
        return x
    y = F.interpolate(
        x.reshape(b * t, 1, h, w),
        size=(size, size),
        mode="nearest",
    )
    return y.reshape(b, t, size, size)


def _ndvi_hwct(x: np.ndarray) -> np.ndarray:
    ndvi = (x[:, :, 3, :] - x[:, :, 2, :]) / (
        x[:, :, 3, :] + x[:, :, 2, :] + 1e-6
    )
    return ndvi[:, :, None, :]


def _harmonic_mean(values: Sequence[float]) -> float:
    valid = [float(v) for v in values if np.isfinite(v) and v > 0]
    if not valid:
        return float("nan")
    return min(1.0, len(valid) / sum(1.0 / (v + 1e-8) for v in valid))

