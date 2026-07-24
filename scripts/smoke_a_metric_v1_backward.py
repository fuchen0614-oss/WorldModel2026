#!/usr/bin/env python
"""Single-batch forward+backward self-test for the metric-aligned v1 variant.

Validates the NEW, default-off machinery end to end on ONE real batch:

  * builds the model via ``create_stage2_model`` with ``plan_a_metric_v1.yaml``
    (with ``require_stage15_checkpoint`` forced off + a random init so the test
    needs no Stage1.5 / A2 checkpoint),
  * pulls one batch from the configured dataset, forwards, computes the loss,
    backpropagates,
  * asserts:
      - the total loss is finite;
      - each of the three optimizer parameter groups (q / T / O) has >= 1 param
        with a non-None gradient AND the correct learning rate;
      - ``target_veg_mask.sum() > 0``;
      - ``target_landcover`` values are raw esawc_lc codes (subset of the valid
        ESA WorldCover set) and the SCORED veg subset ⊆ {10, 20, 30, 40};
      - each of the three new NDVI terms is finite, INCLUDING the degrade path
        (re-runs the loss with an all-zero land-cover map to exercise the
        empty-class / global-fallback guard);
  * prints every loss-term value.

Exits non-zero on any failure. Data/checkpoints live on the remote GPU host, so
run it there; it is intentionally NOT executed at authoring time.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.datasets.earthnet2021 import (  # noqa: E402
    EarthNet2021Config,
    EarthNet2021Dataset,
    collate_earthnet2021,
)
from models.losses.earthnet_forecasting import EarthNetForecastLoss  # noqa: E402
from train.train_stage2_earthnet import (  # noqa: E402
    build_optimizer,
    create_stage2_model,
    forward_stage2_model,
    load_config,
    move_batch_to_device,
    prepare_stage2_batch_for_model,
    stage2_supervision_for_output,
)

# target_landcover stores the RAW ESA WorldCover (esawc_lc) codes, so all valid
# codes may appear (plus 0 = "unknown" for missing/non-finite pixels).
_ALLOWED_LANDCOVER = {0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 95.0, 100.0}
# The evaluator only SCORES the vegetation classes; a scored (veg-masked) pixel
# must carry one of these codes.
_SCORED_LANDCOVER = {10.0, 20.0, 30.0, 40.0}
_NEW_TERMS = ("ndvi_lc_mse", "ndvi_time_bias", "ndvi_time_ccc")
# group-name prefix -> (bucket, optimizer config key holding its lr, default)
_GROUP_BUCKETS = (
    ("q_encoder_phi_projector", "q", "backbone_lr", 1e-5),
    ("transition_T", "T", "transition_lr", None),  # None -> falls back to lr
    ("heads_O_agg_dec", "O", "lr", 1e-4),
)


def _fail(message: str) -> None:
    print(f"[SMOKE FAIL] {message}")
    raise SystemExit(1)


def _check(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(REPO_ROOT / "configs" / "train" / "plan_a_metric_v1.yaml"),
        help="Training config to smoke-test.",
    )
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device to run the single batch on.",
    )
    parser.add_argument(
        "--conditioning-stats-path",
        default=str(
            REPO_ROOT
            / "artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048"
            / "conditioning_stats_physical4_v1_train_dev.json"
        ),
        help=(
            "Train-only physical4 conditioning stats JSON required by the "
            "physical4 data config. Defaults to the repo artifacts path."
        ),
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="Override data.root if the config's baked path is absent on this host.",
    )
    parser.add_argument(
        "--manifest-path",
        default=None,
        help=(
            "Frozen manifest for the smoke split (physical4 EarthNet2021x). "
            "Reuse the A1/A2 val_dev manifest. Required because the config's "
            "manifest paths are supplied by the training launcher at runtime."
        ),
    )
    parser.add_argument(
        "--split",
        default="val",
        help="Dataset split to pull the single smoke batch from (default: val).",
    )
    args = parser.parse_args()

    device = torch.device(args.device)
    config = load_config(args.config)

    # Make the model self-contained: no Stage1.5 / A2 checkpoint required.
    model_cfg = config.setdefault("model", {})
    model_cfg["require_stage15_checkpoint"] = False
    model_cfg.setdefault("encoder", {})["from_checkpoint"] = None
    config.setdefault("training", {})["init_from_checkpoint"] = None

    # physical4 requires a train-only conditioning-stats file; inject it (and an
    # optional data-root override) before building the dataset config.
    if args.conditioning_stats_path:
        config["data"]["conditioning_stats_path"] = args.conditioning_stats_path
    if args.data_root:
        config["data"]["root"] = args.data_root
    # The config leaves manifest paths null (the launcher injects them at
    # runtime); the smoke needs an explicit manifest for its split.
    config["data"]["split"] = args.split
    if args.manifest_path:
        config["data"]["manifest_path"] = args.manifest_path
        manifest_paths = config["data"].setdefault("manifest_paths", {})
        if isinstance(manifest_paths, dict):
            manifest_paths[args.split] = args.manifest_path
        config["data"]["require_manifest"] = True

    opt_cfg = config["optimizer"]
    expected_lr = {
        "q": float(opt_cfg.get("backbone_lr", 1e-5)),
        "O": float(opt_cfg.get("lr", 1e-4)),
    }
    transition_lr_cfg = opt_cfg.get("transition_lr", None)
    expected_lr["T"] = (
        float(transition_lr_cfg)
        if transition_lr_cfg is not None
        else float(opt_cfg.get("lr", 1e-4))
    )

    # --- data: one batch ---------------------------------------------------
    data_cfg = EarthNet2021Config.from_config(
        config["data"], split=config["data"].get("split", "train")
    )
    dataset = EarthNet2021Dataset(data_cfg)
    _check(len(dataset) > 0, "dataset is empty")
    batch = collate_earthnet2021([dataset[0]])
    _check("target_landcover" in batch, "batch is missing target_landcover")
    _check("target_veg_mask" in batch, "batch is missing target_veg_mask")

    # target_landcover value-domain check (before device move / index_select).
    # The stored map keeps raw esawc_lc codes, so any valid code (or 0) is fine.
    lc_map = batch["target_landcover"]
    lc_values = set(torch.unique(lc_map).tolist())
    _check(
        lc_values.issubset(_ALLOWED_LANDCOVER),
        f"target_landcover has out-of-domain values: {sorted(lc_values)}",
    )
    # The SCORED subset (veg-clear pixels) must be one of the vegetation classes.
    veg_bhw = batch["target_veg_mask"] > 0
    scored_codes = set(torch.unique(lc_map[veg_bhw]).tolist()) if bool(veg_bhw.any()) else set()
    _check(
        scored_codes.issubset(_SCORED_LANDCOVER),
        f"scored (veg-masked) land-cover codes must be in {sorted(_SCORED_LANDCOVER)}, "
        f"got {sorted(scored_codes)}",
    )

    batch = move_batch_to_device(batch, device)
    batch = prepare_stage2_batch_for_model(batch, data_cfg)

    # --- model / loss / optimizer -----------------------------------------
    model = create_stage2_model(config, device)
    model.train()
    loss_fn = EarthNetForecastLoss.from_config(
        config["loss"],
        red_index=data_cfg.band_spec.red_index,
        nir_index=data_cfg.band_spec.nir_index,
    ).to(device)
    optimizer = build_optimizer(model, config)

    # --- forward + loss + backward ----------------------------------------
    out = forward_stage2_model(model, batch)
    supervision = stage2_supervision_for_output(batch, out)

    veg_sum = float(supervision["target_veg_mask"].sum().detach().cpu())
    _check(veg_sum > 0.0, f"target_veg_mask.sum() must be > 0, got {veg_sum}")

    losses = loss_fn(
        out["pred"],
        supervision["target"],
        supervision["target_mask"],
        z_pred=out.get("z_pred"),
        z_target=out.get("z_target"),
        z_context=out.get("z_context"),
        z_target_mask=out.get("z_target_mask"),
        horizons=supervision["horizons"],
        ndvi_pred=out.get("ndvi_pred"),
        veg_mask=supervision.get("target_veg_mask"),
        landcover=supervision.get("target_landcover"),
    )

    print("=== loss terms (land-cover-aware path) ===")
    for name, value in losses.items():
        scalar = float(value.detach().float().cpu())
        print(f"  {name:20s} = {scalar:.6f}")

    _check(torch.isfinite(losses["total"]), "total loss is not finite")
    for term in _NEW_TERMS:
        _check(term in losses, f"loss dict is missing new term {term!r}")
        _check(
            torch.isfinite(losses[term]),
            f"new loss term {term!r} is not finite: {losses[term]}",
        )
    _check(
        out.get("ndvi_pred") is not None,
        "model produced no ndvi_pred; the metric terms need the direct NDVI head",
    )

    losses["total"].backward()

    # --- optimizer group assertions ---------------------------------------
    groups_by_bucket: dict[str, list[dict]] = {"q": [], "T": [], "O": []}
    for group in optimizer.param_groups:
        name = str(group.get("name", ""))
        for prefix, bucket, _key, _default in _GROUP_BUCKETS:
            if name.startswith(prefix):
                groups_by_bucket[bucket].append(group)
                break
    for bucket in ("q", "T", "O"):
        groups = groups_by_bucket[bucket]
        _check(len(groups) >= 1, f"no optimizer group found for bucket {bucket!r}")
        has_grad = False
        for group in groups:
            _check(
                math.isclose(float(group["lr"]), expected_lr[bucket], rel_tol=1e-9, abs_tol=1e-15),
                f"bucket {bucket!r} group '{group.get('name')}' lr={group['lr']} "
                f"!= expected {expected_lr[bucket]}",
            )
            has_grad = has_grad or any(
                p.grad is not None and torch.isfinite(p.grad).all()
                for p in group["params"]
            )
        _check(
            has_grad,
            f"bucket {bucket!r} has no parameter with a finite non-None gradient",
        )
        total_params = sum(len(g["params"]) for g in groups)
        print(
            f"  optimizer bucket {bucket!r}: groups={len(groups)} "
            f"tensors={total_params} lr={expected_lr[bucket]:.2e} grad=OK"
        )

    # --- degrade path: all-zero land cover (empty-class guard) -------------
    zero_lc = torch.zeros_like(supervision["target_landcover"])
    degrade = loss_fn(
        out["pred"].detach().requires_grad_(True),
        supervision["target"],
        supervision["target_mask"],
        ndvi_pred=out["ndvi_pred"].detach().requires_grad_(True),
        veg_mask=supervision.get("target_veg_mask"),
        landcover=zero_lc,
    )
    print("=== loss terms (degrade path: all-zero land cover) ===")
    for term in _NEW_TERMS:
        scalar = float(degrade[term].detach().float().cpu())
        print(f"  {term:20s} = {scalar:.6f}")
        _check(
            torch.isfinite(degrade[term]),
            f"degrade-path term {term!r} is not finite: {degrade[term]}",
        )

    print("[SMOKE PASS] metric-aligned v1 forward+backward self-test succeeded")


if __name__ == "__main__":
    main()
