"""Parity check: inline EarthNetScoreAccumulator vs official EarthNetScore.get_ENS.

Feeds the SAME (pred, target, mask) cubes through both scoring paths and compares
ENS + the four subscores. This isolates the inline adapter (resize / mask handling /
NDVI / aggregation) against the official directory scorer. If they agree, the
officialENS_run1 numbers (ours 0.15, persistence 0.209) are faithful ENS values.

Synthetic cubes are fine here: parity is a scorer-vs-scorer property on identical
inputs, not a statement about realistic ENS magnitude. We span the component range
(perfect / persistence-like / blurred+noisy) so no subscore is degenerate.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.earthnet_standard_metrics import EarthNetScoreAccumulator  # noqa: E402

H = W = 128
T = 20
N = 8
EVAL_SIZE = 128


def _smooth_field(rng, shape):
    """Spatially smooth random field in [0,1] so SSIM/NDVI are non-degenerate."""
    x = rng.random(shape).astype(np.float64)
    # cheap separable blur over H,W
    k = np.array([1, 4, 6, 4, 1], dtype=np.float64)
    k = k / k.sum()
    for ax in (-2, -1):
        x = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), ax, x)
    return np.clip(x, 0.0, 1.0)


def _blur(x):
    k = np.array([1, 2, 1], dtype=np.float64)
    k = k / k.sum()
    y = x.copy()
    for ax in (0, 1):
        y = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), ax, y)
    return np.clip(y, 0.0, 1.0)


def build_cubes():
    rng = np.random.default_rng(0)
    cubes = []
    for i in range(N):
        # target RGBN: [H,W,4,T]
        targ = _smooth_field(rng, (H, W, 4, T))
        # cloud/invalid mask as LAST channel (1 = invalid), mostly valid (~10% invalid)
        cloud = (rng.random((H, W, 1, T)) < 0.1).astype(np.float64)
        # prediction variants spanning the quality range
        if i % 3 == 0:
            pred = targ.copy()                       # perfect
        elif i % 3 == 1:
            pred = np.repeat(targ[:, :, :, :1], T, axis=3)  # persistence (frame 0)
        else:
            pred = np.clip(_blur(targ) + rng.normal(0, 0.03, targ.shape), 0, 1)  # blur+noise
        cubes.append({"name": f"29SND_cube{i}", "targ": targ, "cloud": cloud, "pred": pred})
    return cubes


def score_inline(cubes):
    """[H,W,4,T] cubes -> inline accumulator ([B,T,C,H,W], mask 1=valid)."""
    acc = EarthNetScoreAccumulator(EVAL_SIZE)
    preds = np.stack([np.transpose(c["pred"], (3, 2, 0, 1)) for c in cubes])   # [B,T,C,H,W]
    targs = np.stack([np.transpose(c["targ"], (3, 2, 0, 1)) for c in cubes])
    # inline clear_mask is [B,T,H,W], 1 = valid = 1 - cloud
    valid = np.stack([np.transpose(1.0 - c["cloud"][:, :, 0, :], (2, 0, 1)) for c in cubes])
    acc.update(
        torch.from_numpy(preds).float(),
        torch.from_numpy(targs).float(),
        torch.from_numpy(valid).float(),
        [c["name"] for c in cubes],
    )
    return acc.compute()


def score_official(cubes):
    """Write highresdynamic NPZs and call EarthNetScore.get_ENS (n_workers=0)."""
    import earthnet as en
    from eval.earthnet_standard_metrics import ensure_earthnet_ssim_compat

    ensure_earthnet_ssim_compat(en)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        pred_dir = td / "pred"
        targ_dir = td / "targ"
        for c in cubes:
            pt = pred_dir / "29SND"
            tt = targ_dir / "29SND"
            pt.mkdir(parents=True, exist_ok=True)
            tt.mkdir(parents=True, exist_ok=True)
            # pred: [H,W,4,T]
            np.savez(pt / f"{c['name']}.npz", highresdynamic=c["pred"].astype(np.float32))
            # targ: RGBN (4) + cloud mask as LAST channel -> [H,W,5,T]
            targ_hr = np.concatenate([c["targ"], c["cloud"]], axis=2).astype(np.float32)
            np.savez(tt / f"{c['name']}.npz", highresdynamic=targ_hr)
        ens_out = td / "ens.json"
        en.parallel_score.EarthNetScore.get_ENS(
            str(pred_dir), str(targ_dir), n_workers=0, ens_output_file=str(ens_out)
        )
        import json
        d = json.load(open(ens_out))
        return {
            "ENS": d["EarthNetScore"],
            "MAD": d["Value (MAD)"],
            "OLS": d["Trend (OLS)"],
            "EMD": d["Distribution (EMD)"],
            "SSIM": d["Perceptual (SSIM)"],
        }


def run_parity(tol: float = 1e-3):
    cubes = build_cubes()
    inline = score_inline(cubes)
    official = score_official(cubes)
    keys = ["ENS", "MAD", "OLS", "EMD", "SSIM"]
    print(f"\n{'metric':6} {'inline':>12} {'official':>12} {'abs_diff':>12}")
    print("-" * 46)
    maxdiff = 0.0
    for k in keys:
        a, b = float(inline[k]), float(official[k])
        d = abs(a - b)
        maxdiff = max(maxdiff, d)
        print(f"{k:6} {a:12.6f} {b:12.6f} {d:12.2e}")
    print("-" * 46)
    print(f"max abs diff = {maxdiff:.2e}  (tol {tol:.0e})")
    ok = maxdiff < tol
    print("VERDICT:", "PARITY OK (adapter faithful)" if ok
          else "DIVERGENCE (adapter differs from official)")
    return ok, maxdiff


def test_parity_inline_matches_official():
    """Regression gate: inline EarthNetScoreAccumulator must track official get_ENS."""
    ok, maxdiff = run_parity()
    assert ok, f"inline vs official ENS diverged: max abs diff {maxdiff:.2e} >= 1e-3"


def main():
    ok, _ = run_parity()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
