"""Q3 driver (weather) sensitivity for a SINGLE frozen A' checkpoint.

Three fixed arms (RESULT_INGESTION_SCHEMA.md section 6.1):
  matched            -- the sample's own future weather (reference).
  normalized_mean    -- future weather set to the normalized mean (0 in
                        normalized driver space): weather variation removed.
  season_geo_donor   -- future weather replaced by a deterministic season AND
                        geography matched, non-self donor. Fail-closed: the
                        donor season/geography/non-self/coverage match rates must
                        all be 1.0 for a formal run.

For every arm the tool reports the masked-NDVI error (direct head), the paired
delta vs matched with a bootstrap CI, and the transitioned-state change plus the
endpoint-output change (both the NDVI head and the reflectance head). Per-cube
values are keyed by sample_id. All perturbations are in-memory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _future_slice(model):
    fsi = int(getattr(model, "future_start_index", 10))
    steps = int(getattr(model, "target_steps", 20))
    return fsi, fsi + steps


def _cube_masked_mse(pred_khw, tgt_khw, mask_khw):
    per = (pred_khw - tgt_khw).pow(2)
    if mask_khw is None:
        return float(per.mean())
    d = mask_khw.sum().clamp_min(1.0)
    return float((per * mask_khw).sum() / d)


def evaluate_driver_sensitivity(model, batches, *, red_index: int = 2, nir_index: int = 3,
                                n_boot: int = 2000, bootstrap_seed: int = 42):
    """Core Q3 computation over prepared batches (matched + mean + optional donor)."""

    import numpy as np
    import torch
    from data.stage2_contract import model_input_view
    from data.earthnet_fields import compute_ndvi
    from eval.aprime_paired_stats import paired_bootstrap_ci

    core = getattr(model, "core", None)
    if core is None or getattr(core, "ndvi_head", None) is None:
        raise ValueError("Q3 requires an A' model with core.ndvi_head")
    fsi, end = _future_slice(model)

    arms = ("matched", "normalized_mean", "season_geo_donor")
    err = {a: {} for a in arms}          # sample_id -> masked-NDVI error
    state_change = {a: {} for a in arms}  # sample_id -> normalized state change vs matched
    ndvi_change = {a: {} for a in arms}
    rgbn_change = {a: {} for a in arms}
    donor_rate_acc = {"season": 0.0, "geography": 0.0, "not_self": 0.0, "coverage": 0.0, "n": 0}
    ids = []

    def forward_all(mv):
        out = model(mv, selected_steps=None)
        return out["z_pred"], out["pred"], out["ndvi_pred"].squeeze(2), out["step_indices"]

    was_training = model.training
    model.eval()
    with torch.no_grad():
        for batch in batches:
            mv = model_input_view(batch)
            z_m, pred_m, ndvi_m, steps = forward_all(mv)
            target = batch["x_target"].index_select(1, steps.to(pred_m.device))
            tgt_ndvi = compute_ndvi(target, red_index, nir_index).clamp(-1.0, 1.0)
            veg = batch.get("target_veg_mask", batch.get("target_mask"))
            if veg is not None:
                veg = veg.index_select(1, steps.to(pred_m.device))
            meta = batch.get("meta")
            ctx_std = float(z_m.mean(dim=1).std()) + 1e-6
            bs = target.shape[0]
            batch_ids = [meta[b].get("sample_id") if meta else f"cube_{len(ids)+b}" for b in range(bs)]

            def run_arm(name, d_future_or_zero, active_mask):
                perturbed = dict(batch)
                d = batch["D_path"].clone()
                if d_future_or_zero is None:
                    d[:, fsi:end] = 0.0
                else:
                    d[:, fsi:end] = d_future_or_zero.to(d.dtype)
                perturbed["D_path"] = d
                z_p, pred_p, ndvi_p, _ = forward_all(model_input_view(perturbed))
                for b in range(bs):
                    if active_mask is not None and not bool(active_mask[b]):
                        continue
                    sid = batch_ids[b]
                    m = None if veg is None else veg[b]
                    err[name][sid] = _cube_masked_mse(ndvi_p[b], tgt_ndvi[b], m)
                    state_change[name][sid] = float((z_p[b] - z_m[b]).norm(dim=-1).mean()) / ctx_std
                    ndvi_change[name][sid] = float((ndvi_p[b] - ndvi_m[b]).abs().mean())
                    rgbn_change[name][sid] = float((pred_p[b] - pred_m[b]).abs().mean())

            # matched arm: error only (it is its own reference, zero change).
            for b in range(bs):
                sid = batch_ids[b]
                m = None if veg is None else veg[b]
                err["matched"][sid] = _cube_masked_mse(ndvi_m[b], tgt_ndvi[b], m)
                state_change["matched"][sid] = 0.0
                ndvi_change["matched"][sid] = 0.0
                rgbn_change["matched"][sid] = 0.0
            run_arm("normalized_mean", None, None)

            donor_future = batch.get("donor_D_future")
            if donor_future is not None and bool(batch.get("donor_verified", False)):
                run_arm("season_geo_donor", donor_future, None)
                rates = batch.get("donor_rates", {})
                donor_rate_acc["season"] += float(rates.get("season", 1.0)) * bs
                donor_rate_acc["geography"] += float(rates.get("geography", 1.0)) * bs
                donor_rate_acc["not_self"] += float(rates.get("not_self", 1.0)) * bs
                donor_rate_acc["coverage"] += float(rates.get("coverage", 1.0)) * bs
                donor_rate_acc["n"] += bs
            ids.extend(batch_ids)

    if was_training:
        model.train()
    if not ids:
        raise RuntimeError("no samples were evaluated")

    def _agg(name):
        e = np.asarray(list(err[name].values()), dtype=np.float64) if err[name] else np.asarray([])
        block = {
            "arm_id": name,
            "n_samples": int(e.size),
            "masked_ndvi_mse": float(e.mean()) if e.size else None,
            "rmse": float(e.mean()) ** 0.5 if e.size else None,
            "mean_state_change_normalized": float(np.mean(list(state_change[name].values()))) if state_change[name] else None,
            "mean_ndvi_output_change": float(np.mean(list(ndvi_change[name].values()))) if ndvi_change[name] else None,
            "mean_rgbn_output_change": float(np.mean(list(rgbn_change[name].values()))) if rgbn_change[name] else None,
        }
        return block

    rows = {a: _agg(a) for a in arms}
    # paired delta vs matched (shared sample_ids only).
    matched_ids = set(err["matched"])
    for a in ("normalized_mean", "season_geo_donor"):
        shared = [sid for sid in err[a] if sid in matched_ids]
        if shared:
            delta = [err[a][sid] - err["matched"][sid] for sid in shared]
            ci = paired_bootstrap_ci(delta, n_boot=n_boot, seed=bootstrap_seed)
            rows[a]["delta_mse_vs_matched"] = ci["delta_mean"]
            rows[a]["delta_ci_low"] = ci["ci_low"]
            rows[a]["delta_ci_high"] = ci["ci_high"]
            rows[a]["n_paired_samples"] = ci["n_paired_samples"]

    donor_rates = None
    if donor_rate_acc["n"] > 0:
        d_n = donor_rate_acc["n"]
        donor_rates = {
            "donor_season_match_rate": donor_rate_acc["season"] / d_n,
            "donor_geography_match_rate": donor_rate_acc["geography"] / d_n,
            "donor_not_self_rate": donor_rate_acc["not_self"] / d_n,
            "donor_coverage_rate": donor_rate_acc["coverage"] / len(ids),
            "n_donor_samples": d_n,
        }

    return {
        "endpoint_metric_id": "masked_ndvi_mse",
        "n_samples": len(ids),
        "state_change_definition": "mean over horizons/tokens of ||z_perturbed - z_matched|| / context_state_std",
        "output_change_definition": "mean over masked pixels/horizons of |output_perturbed - output_matched|",
        "arms": rows,
        "donor_rates": donor_rates,
        "bootstrap": {"n_boot": int(n_boot), "seed": int(bootstrap_seed)},
    }


def assert_donor_rates_complete(donor_rates: dict) -> None:
    """Fail-closed: every donor match rate must be exactly 1.0 (schema 6.1)."""

    if donor_rates is None:
        raise ValueError("donor arm has no rates -- fail-closed")
    for key in ("donor_season_match_rate", "donor_geography_match_rate",
                "donor_not_self_rate", "donor_coverage_rate"):
        if float(donor_rates.get(key, 0.0)) != 1.0:
            raise ValueError(f"donor rate {key}={donor_rates.get(key)} != 1.0 -- fail-closed")


def apply_guards(report: dict, *, min_state_change: float, min_output_change: float) -> dict:
    """Weather-sensitivity guard on the donor arm (state AND output must move)."""

    donor = report["arms"].get("season_geo_donor", {})
    checks = {
        "state_moves": (donor.get("mean_state_change_normalized") or 0.0) >= min_state_change,
        "ndvi_output_moves": (donor.get("mean_ndvi_output_change") or 0.0) >= min_output_change,
        "rgbn_output_moves": (donor.get("mean_rgbn_output_change") or 0.0) >= min_output_change,
    }
    return {
        "min_state_change": min_state_change,
        "min_output_change": min_output_change,
        "checks": checks,
        "all_pass": all(checks.values()),
    }


def build_matched_donor_future(d_path, calendar_path, geo, *, future_start_index, target_steps,
                               season_bins: int = 4, geo_bins: int = 4):
    """Deterministic season+geography matched, non-self donor future weather.

    Returns ``(donor_future, verified_mask, rates)``. A sample is matched to
    another sample in the SAME (season, geography) bucket; season and geography
    are BOTH required. Samples with no same-bucket non-self partner are
    unverified. ``rates`` reports the season/geography/non-self/coverage match
    rates (over matched samples) for the schema's fail-closed check.
    """

    import torch

    b = d_path.shape[0]
    fsi, end = future_start_index, future_start_index + target_steps
    cal = calendar_path[:, fsi:end].mean(dim=1)
    season = torch.atan2(cal[:, 0], cal[:, 1])
    season_bucket = ((season + torch.pi) / (2 * torch.pi) * season_bins).long().clamp(0, season_bins - 1)
    geo_mean = geo.reshape(b, -1).mean(dim=1)
    gmin, gmax = geo_mean.min(), geo_mean.max()
    geo_bucket = ((geo_mean - gmin) / (gmax - gmin + 1e-6) * geo_bins).long().clamp(0, geo_bins - 1)

    donor_future = torch.zeros_like(d_path[:, fsi:end])
    verified = torch.zeros(b, dtype=torch.bool)
    season_ok = geo_ok = not_self_ok = 0
    matched = 0
    for i in range(b):
        partners = [j for j in range(b)
                    if j != i and int(season_bucket[j]) == int(season_bucket[i])
                    and int(geo_bucket[j]) == int(geo_bucket[i])]
        if partners:
            j = partners[0]
            donor_future[i] = d_path[j, fsi:end]
            verified[i] = True
            matched += 1
            season_ok += int(int(season_bucket[j]) == int(season_bucket[i]))
            geo_ok += int(int(geo_bucket[j]) == int(geo_bucket[i]))
            not_self_ok += int(j != i)
    rates = {
        "season": (season_ok / matched) if matched else 0.0,
        "geography": (geo_ok / matched) if matched else 0.0,
        "not_self": (not_self_ok / matched) if matched else 0.0,
        "coverage": matched / b if b else 0.0,
    }
    return donor_future, verified, rates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--split", default="val")
    parser.add_argument("--data-root")
    parser.add_argument("--manifest-path")
    parser.add_argument("--conditioning-stats-path")
    parser.add_argument("--external-driver-root")
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--bootstrap-seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=0, help="Max batches (NON-FORMAL smoke).")
    parser.add_argument("--min-state-change", type=float, default=None)
    parser.add_argument("--min-output-change", type=float, default=None)
    parser.add_argument("--allow-checkpoint-contract-mismatch", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    import torch
    from torch.utils.data import DataLoader
    from data.datasets.earthnet2021 import EarthNet2021Config, EarthNet2021Dataset, collate_earthnet2021
    from train.stage2_provenance import sha256_file
    from train.train_stage2_earthnet import (
        load_config, create_stage2_model, load_stage2_model_state,
        move_batch_to_device, prepare_stage2_batch_for_model,
    )
    from eval.stage2_evaluation_provenance import verify_checkpoint_contract
    from eval.aprime_provenance import finite_only

    is_smoke = bool(args.limit and args.limit > 0)
    if not is_smoke and (args.min_state_change is None or args.min_output_change is None):
        raise SystemExit("formal run requires --min-state-change and --min-output-change (fail-closed)")

    config = load_config(args.config)
    for key, value in (
        ("root", args.data_root), ("manifest_path", args.manifest_path),
        ("conditioning_stats_path", args.conditioning_stats_path),
        ("external_driver_root", args.external_driver_root), ("dgh_stats_path", args.dgh_stats_path),
    ):
        if value is not None:
            config["data"][key] = value
    if args.manifest_path is not None:
        manifest_paths = config["data"].get("manifest_paths")
        if isinstance(manifest_paths, dict):
            manifest_paths[args.split] = args.manifest_path
        config["data"]["require_manifest"] = True
    config["data"]["split"] = args.split
    config["model"]["encoder"]["from_checkpoint"] = None
    config["model"]["compute_latent_targets"] = False

    sha_before = sha256_file(args.checkpoint)
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    verify_checkpoint_contract(checkpoint, config, allow_mismatch=args.allow_checkpoint_contract_mismatch)
    device = torch.device("cpu")
    model = create_stage2_model(config, device)
    load_stage2_model_state(model, checkpoint.get("model_state_dict", checkpoint), strict=True)
    raw = model.module if hasattr(model, "module") else model
    fsi, end = _future_slice(raw)

    data_cfg = EarthNet2021Config.from_config(config["data"], split=args.split)
    dataset = EarthNet2021Dataset(data_cfg)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False,
                        num_workers=args.num_workers, drop_last=False, collate_fn=collate_earthnet2021)

    def prepared():
        for i, batch in enumerate(loader):
            if args.limit and i >= args.limit:
                break
            batch = move_batch_to_device(batch, device)
            batch = prepare_stage2_batch_for_model(batch, data_cfg)
            donor_future, verified, rates = build_matched_donor_future(
                batch["D_path"], batch["C_path"], batch["G"],
                future_start_index=fsi, target_steps=end - fsi,
            )
            if bool(verified.all()):
                batch["donor_D_future"] = donor_future
                batch["donor_verified"] = True
                batch["donor_rates"] = rates
            else:
                # A formal run requires 100% donor coverage; a partial batch is
                # dropped from the donor arm (fail-closed later on rates).
                batch["donor_verified"] = False
                batch["donor_rates"] = rates
            yield batch

    report = evaluate_driver_sensitivity(raw, prepared(), n_boot=args.n_boot, bootstrap_seed=args.bootstrap_seed)
    if not is_smoke:
        assert_donor_rates_complete(report.get("donor_rates"))

    sha_after = sha256_file(args.checkpoint)
    report.update({
        "checkpoint": str(Path(args.checkpoint).resolve()),
        "checkpoint_sha256_before": sha_before,
        "checkpoint_sha256_after": sha_after,
        "checkpoint_unchanged": sha_before == sha_after,
        "is_smoke": is_smoke,
        "formal": not is_smoke,
    })
    if args.min_state_change is not None and args.min_output_change is not None:
        report["guard"] = apply_guards(report, min_state_change=args.min_state_change, min_output_change=args.min_output_change)
    if not report["checkpoint_unchanged"]:
        raise SystemExit("checkpoint file changed during evaluation -- aborting")

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(finite_only(report), handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    tmp.replace(out)
    print(json.dumps(finite_only(report), indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
