#!/usr/bin/env python3
"""Render the two-level candidate gallery figures from the exported arrays.

Level A (`P##_browse.png`)  : browse sheet -- id/split/category, context overview, GT and every
                              available model at three fixed target steps, plus a validity hint.
Level B (`P##_detail.png`)  : comparison sheet -- same steps for every model, absolute-error maps,
                              the spatial-mean NDVI trajectory and the per-horizon RMSE curve.

Consistency rules enforced here (they are also asserted by verify_showcase.py):
  * identical sample, identical target steps and identical validity mask across panels;
  * one NDVI colour scale (0..1) and one error colour scale (0..0.4, clipped) for all panels;
  * invalid pixels are drawn flat grey, never as a zero value;
  * nothing is cropped or rescaled per model;
  * canvas text is English; interpretation lives in the index and the overview.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_showcase as L  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
plt = L.setup_matplotlib()
from matplotlib.gridspec import GridSpec  # noqa: E402

EARLY, MID, LATE = 4, 9, 19
STEP_LABEL = {EARLY: f"t+{EARLY + 1}", MID: f"t+{MID + 1}", LATE: f"t+{LATE + 1} (endpoint)"}


def load(cid_dir: Path):
    z = np.load(cid_dir / "arrays.npz")
    meta = json.loads((cid_dir / "metadata.json").read_text(encoding="utf-8"))
    return ({k: z[k] for k in z.files}, meta)


def traj_of(arr, valid):
    out = []
    for h in range(arr.shape[0]):
        m = valid[h] > 0
        out.append(float(arr[h][m].mean()) if m.any() else np.nan)
    return np.array(out)


def panel(ax, arr, valid, title=None, cmap=None, vmin=None, vmax=None, bad="0.78"):
    a = np.where(valid > 0, arr, np.nan) if valid is not None else arr
    cm = L.plt_get_cmap(cmap or L.NDVI_CMAP).copy()
    cm.set_bad(bad)
    im = ax.imshow(a, cmap=cm, vmin=vmin if vmin is not None else L.NDVI_VMIN,
                   vmax=vmax if vmax is not None else L.NDVI_VMAX)
    ax.set_xticks([]); ax.set_yticks([])
    if title:
        ax.set_title(title, fontsize=8.5, pad=3)
    return im


def render_browse(out: Path, cid: str, arr, meta, mrow):
    gt, c1, pers = arr["gt"], arr["c1"], arr["persistence"]
    valid, ctx, cvalid = arr["valid"], arr["context"], arr["context_valid"]
    fig = plt.figure(figsize=(13.2, 8.4))
    gs = GridSpec(3, 4, figure=fig, hspace=0.20, wspace=0.06,
                  left=0.035, right=0.925, top=0.885, bottom=0.075)
    # DISPLAY-STEP RULE: the three columns are the three steps with the largest valid fraction
    # (pre-registered; identical for every model of this sample). Each column states its own step,
    # so a substituted step is never mistaken for the fixed t+5 / t+10 / t+20 of the detail page.
    cols = [i - 1 for i in meta.get("display_steps_top3_1based", [EARLY + 1, MID + 1, LATE + 1])]
    while len(cols) < 3:
        cols.append(cols[-1] if cols else LATE)
    lab = {h: f"t+{h + 1}" for h in set(cols)}
    for j, h in enumerate(cols):
        ax = fig.add_subplot(gs[0, j]); ax.set_xticks([]); ax.set_yticks([])
        ax.imshow(np.where(valid[h] > 0, gt[h], np.nan),
                  cmap=_bad(L.NDVI_CMAP), vmin=L.NDVI_VMIN, vmax=L.NDVI_VMAX)
        ax.set_title(f"Ground truth  {lab[h]}", fontsize=9)
    ax = fig.add_subplot(gs[0, 3])
    ax.imshow(np.where(cvalid[-1] > 0, ctx[-1], np.nan), cmap=_bad(L.NDVI_CMAP),
              vmin=L.NDVI_VMIN, vmax=L.NDVI_VMAX)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"Last observed context step  (t-{(L.CONTEXT_STEPS - 1) * L.STRIDE_DAYS}d)",
                 fontsize=9)

    for j, h in enumerate(cols):
        ax = fig.add_subplot(gs[1, j])
        panel(ax, pers[h], valid[h], f"Persistence  {lab[h]}")
    axm = fig.add_subplot(gs[1, 3]); axm.set_xticks([]); axm.set_yticks([])
    cov = (valid.sum(axis=(1, 2)) / valid[0].size)
    axm.bar(np.arange(1, len(cov) + 1), cov, color="0.35")
    axm.set_ylim(0, 1); axm.set_xlim(0.2, len(cov) + 0.8)
    axm.axhline(meta["valid_fraction"], color="crimson", lw=1.0, ls="--")
    for h in cols:
        axm.axvline(h + 1, color="tab:blue", lw=0.8, alpha=0.7)
    axm.set_title("Valid-pixel fraction per step", fontsize=9)
    axm.tick_params(labelsize=7)
    axm.set_xlabel("target step", fontsize=8)

    for j, h in enumerate(cols):
        ax = fig.add_subplot(gs[2, j])
        panel(ax, c1[h], valid[h], f"TerraState-C1  {lab[h]}")
    axt = fig.add_subplot(gs[2, 3])
    tg, tp, tc = traj_of(gt, valid), traj_of(pers, valid), traj_of(c1, valid)
    x = np.arange(1, len(tg) + 1)
    axt.plot(x, tg, color="black", lw=1.8, label="Ground truth")
    axt.plot(x, tp, color="tab:orange", lw=1.3, label="Persistence")
    axt.plot(x, tc, color="tab:blue", lw=1.3, label="TerraState-C1")
    axt.set_xlim(1, len(tg)); axt.set_ylim(0, 1)
    axt.set_title("Spatial-mean NDVI over valid pixels", fontsize=9)
    axt.tick_params(labelsize=7); axt.grid(alpha=0.25, lw=0.5)
    axt.legend(fontsize=7, frameon=False, loc="best")

    cax = fig.add_axes([0.945, 0.075, 0.014, 0.81])
    fig.colorbar(plt.cm.ScalarMappable(norm=plt.matplotlib.colors.Normalize(0, 1),
                                       cmap=L.plt_get_cmap(L.NDVI_CMAP)), cax=cax,
                 label="NDVI (shared scale)")
    cax.tick_params(labelsize=8)

    fig.suptitle(f"{cid}   |   {meta['split']}   |   category: {meta['category']}   |   "
                 f"{meta['cube']}  ({meta['season']})", fontsize=11, y=0.955)
    rm_c1 = mrow.get("rmse_c1", "")
    rm_p = mrow.get("rmse_persistence", "")
    fig.text(0.035, 0.018,
             f"Browse columns are the three steps with the LARGEST valid fraction "
             f"(t+{cols[0] + 1}, t+{cols[1] + 1}, t+{cols[2] + 1}); the detail page keeps the fixed "
             f"t+5 / t+10 / t+20 steps. Masked RMSE over the 20-step target window (same mask as "
             f"the official scorer): TerraState-C1 {rm_c1}   Persistence {rm_p}   |   "
             f"valid fraction {meta['valid_fraction']:.3f}, "
             f"{meta.get('n_empty_steps', 0)} of 20 steps fully clouded   |   grey = invalid "
             f"(cloud / non-vegetated / missing), never a zero value.   "
             f"Baselines Contextformer/PredRNN/ConvLSTM/SimVP: no official checkpoint or exported "
             f"prediction available on this server.",
             fontsize=7.4, color="0.25")
    d = out / "gallery/prediction"
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / f"{cid}_browse.png")
    fig.savefig(d / f"{cid}_browse.pdf")
    plt.close(fig)


def render_detail(out: Path, cid: str, arr, meta, mrow):
    gt, c1, pers = arr["gt"], arr["c1"], arr["persistence"]
    valid = arr["valid"]
    cols = [EARLY, MID, LATE]
    fig = plt.figure(figsize=(13.2, 13.6))
    gs = GridSpec(5, 4, figure=fig, hspace=0.22, wspace=0.06,
                  left=0.04, right=0.90, top=0.905, bottom=0.055,
                  height_ratios=[1, 1, 1, 1, 1.45])
    rows = [("Ground truth", gt, None), ("Persistence", pers, "persistence"),
            ("TerraState-C1", c1, "c1")]
    for i, (name, arr3, _k) in enumerate(rows):
        for j, h in enumerate(cols):
            ax = fig.add_subplot(gs[i, j])
            panel(ax, arr3[h], valid[h], f"{name}  {STEP_LABEL[h]}" if j == 0 or i == 0 else None)

    # fourth column of rows 1-3: context overview, coverage profile, and the case facts
    ctx, cvalid = arr["context"], arr["context_valid"]
    axc = fig.add_subplot(gs[0, 3])
    panel(axc, ctx[-1], cvalid[-1],
          f"Last observed context step (t-{(L.CONTEXT_STEPS - 1) * L.STRIDE_DAYS}d)")
    axb = fig.add_subplot(gs[1, 3])
    cov = valid.sum(axis=(1, 2)) / valid[0].size
    axb.bar(np.arange(1, len(cov) + 1), cov, color="0.35")
    axb.axhline(meta["valid_fraction"], color="crimson", lw=1.0, ls="--")
    axb.set_ylim(0, 1); axb.set_xlim(0.2, len(cov) + 0.8)
    axb.set_title("Valid-pixel fraction per step", fontsize=9)
    axb.set_xlabel("target step", fontsize=8); axb.tick_params(labelsize=7)
    axt2 = fig.add_subplot(gs[2, 3]); axt2.axis("off")
    axt2.text(0.0, 1.0,
              f"sample   {meta['cube']}\n"
              f"season   {meta['season']}\n"
              f"split    {meta['split']}\n"
              f"category {meta['category']}\n\n"
              f"valid fraction  {meta['valid_fraction']:.3f}\n"
              f"valid pixels    {meta['n_valid_target']:,}\n\n"
              f"masked RMSE (20 steps)\n"
              f"  TerraState-C1  {mrow.get('rmse_c1', '—')}\n"
              f"  Persistence    {mrow.get('rmse_persistence', '—')}\n\n"
              f"first target date  {meta['target_dates'][0]}\n"
              f"last  target date  {meta['target_dates'][-1]}",
              fontsize=8, va="top", ha="left", family="monospace")

    for j, h in enumerate(cols):
        ax = fig.add_subplot(gs[3, j])
        panel(ax, np.abs(c1[h] - gt[h]), valid[h], f"|TerraState-C1 - truth|  {STEP_LABEL[h]}",
              cmap=L.ERR_CMAP, vmin=L.ERR_VMIN, vmax=L.ERR_VMAX)
    ax = fig.add_subplot(gs[3, 3])
    panel(ax, np.abs(pers[LATE] - gt[LATE]), valid[LATE],
          f"|Persistence - truth|  {STEP_LABEL[LATE]}", cmap=L.ERR_CMAP,
          vmin=L.ERR_VMIN, vmax=L.ERR_VMAX)

    ax1 = fig.add_subplot(gs[4, 0:2])
    tg, tp, tc = traj_of(gt, valid), traj_of(pers, valid), traj_of(c1, valid)
    x = np.arange(1, len(tg) + 1)
    ax1.plot(x, tg, color="black", lw=2.0, label="Ground truth")
    ax1.plot(x, tp, color="tab:orange", lw=1.4, label="Persistence")
    ax1.plot(x, tc, color="tab:blue", lw=1.4, label="TerraState-C1")
    ax1.set_xlim(1, len(tg)); ax1.set_ylim(0, 1)
    ax1.set_title("Spatial-mean NDVI over valid pixels (target window)", fontsize=10)
    ax1.set_xlabel("target step (5-daily)", fontsize=9)
    ax1.grid(alpha=0.25, lw=0.5); ax1.legend(fontsize=8, frameon=False)

    ax2 = fig.add_subplot(gs[4, 2:4])
    hc = mrow.get("rmse_c1_h") or []
    hp = mrow.get("rmse_persistence_h") or []
    if hc and hp:
        xs = np.arange(1, len(hc) + 1)
        ax2.plot(xs, hp, color="tab:orange", lw=1.6, marker="o", ms=2.5, label="Persistence")
        ax2.plot(xs, hc, color="tab:blue", lw=1.6, marker="o", ms=2.5, label="TerraState-C1")
        ax2.set_xlabel("target step (5-daily)", fontsize=9)
        ax2.set_ylabel("masked RMSE", fontsize=9)
        ax2.set_title("Per-horizon masked RMSE", fontsize=10)
        ax2.grid(alpha=0.25, lw=0.5); ax2.legend(fontsize=8, frameon=False)
        ax2.tick_params(labelsize=8)

    cax1 = fig.add_axes([0.915, 0.335, 0.013, 0.555])
    fig.colorbar(plt.cm.ScalarMappable(norm=plt.matplotlib.colors.Normalize(L.NDVI_VMIN, L.NDVI_VMAX),
                                       cmap=L.plt_get_cmap(L.NDVI_CMAP)), cax=cax1,
                 label="NDVI (shared scale)")
    cax1.tick_params(labelsize=8)
    cax2 = fig.add_axes([0.915, 0.115, 0.013, 0.175])
    fig.colorbar(plt.cm.ScalarMappable(norm=plt.matplotlib.colors.Normalize(L.ERR_VMIN, L.ERR_VMAX),
                                       cmap=L.plt_get_cmap(L.ERR_CMAP)), cax=cax2,
                 label="|error| (clipped at 0.4)")
    cax2.tick_params(labelsize=8)

    fig.suptitle(f"{cid} -- detailed comparison   |   {meta['split']}   |   "
                 f"category: {meta['category']}   |   {meta['cube']} ({meta['season']})",
                 fontsize=11.5, y=0.962)
    fig.text(0.04, 0.012,
             f"All panels: identical sample, identical 20 five-daily target steps, identical "
             f"validity mask ({meta['valid_fraction']:.3f} valid fraction). "
             f"Error maps are clipped at 0.4 and invalid pixels are grey (not zero). "
             f"TerraState-C1 prediction read from the frozen E1 evaluation output "
             f"(seed 42, official 5-daily grid); no re-inference was performed for this figure.",
             fontsize=7.4, color="0.25")
    d = out / "gallery/prediction"
    fig.savefig(d / f"{cid}_detail.png")
    fig.savefig(d / f"{cid}_detail.pdf")
    plt.close(fig)


def _bad(cmap):
    cm = L.plt_get_cmap(cmap).copy()
    cm.set_bad("0.78")
    return cm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    out = args.out
    mrows = {}
    mp = out / "metrics/PREDICTION_CANDIDATE_METRICS.csv"
    if mp.exists():
        for r in csv.DictReader(open(mp, newline="", encoding="utf-8")):
            if r.get("status") == "ok":
                def _arr(key):
                    try:
                        v = json.loads(r.get(key) or "[]")
                    except Exception:  # noqa: BLE001
                        return []
                    return [np.nan if x is None else float(x) for x in v]
                r["rmse_c1_h"] = _arr("rmse_c1_h20") or [
                    float(r[f"rmse_c1_{k}"]) for k in ("early", "mid", "late")]
                r["rmse_persistence_h"] = _arr("rmse_persistence_h20") or [
                    float(r[f"rmse_persistence_{k}"]) for k in ("early", "mid", "late")]
            mrows[r["candidate_id"]] = r
    dirs = sorted((out / "gallery/_arrays").glob("P*"))
    if args.only:
        dirs = [d for d in dirs if d.name in args.only.split(",")]
    for d in dirs:
        arr, meta = load(d)
        mrow = mrows.get(d.name, {})
        render_browse(out, d.name, arr, meta, mrow)
        render_detail(out, d.name, arr, meta, mrow)
        print(f"  rendered {d.name}  ({meta['split']}, {meta['category']})")
    print(f"\nrendered {len(dirs)} candidates -> gallery/prediction/")


if __name__ == "__main__":
    main()
