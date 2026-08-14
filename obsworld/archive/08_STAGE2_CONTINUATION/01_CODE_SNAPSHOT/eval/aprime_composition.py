"""Q4 composition-consistency & anti-collapse for a SINGLE frozen A' checkpoint.

Emits the fields required by TerraState_AAAI27/RESULT_INGESTION_SCHEMA.md
(sections 7.1 q4_composition and 7.2 q4_state_summary). The endpoint error uses
the SAME direct-NDVI closure as the rest of A' (core.decode_ndvi over the
evaluator-aligned vegetation mask) -- never the RGBN reflectance head -- so
selection, Q1, Q2, Q3 and Q4 all score one closure.

Per pre-declared depth (h1 + h2 = endpoint_h, in 5-day control tokens):
  * endpoint_direct_error  = masked-NDVI-MSE of O_ndvi(T(z0, h1+h2))
  * endpoint_composed_error= masked-NDVI-MSE of O_ndvi(T(T(z0,h1),h2))
  * state_path_gap_raw     = LayerNorm-space ||z_direct - z_composed||^2
  * state_shuffle_reference= same gap under a seeded cross-sample pairing
                             (same endpoint, same population) -- the floor
  * state_path_gap_normalized = gap_raw / shuffle_reference
  * output_path_gap        = masked-NDVI-MSE between the two decoded NDVIs
  * effective_rank         = participation ratio of the endpoint states
Plus a q4_state_summary per endpoint horizon (movement/std/rank, movement
normalized by the context-state std).

Guards are dual, validation-frozen thresholds on the direct AND composed
endpoint error, bound to the exact endpoint metric. A formal run fails closed if
either threshold is unset. The checkpoint SHA256 is captured before/after.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# name -> (h1, h2) in 5-day control tokens; endpoint_h = h1 + h2.
DEPTHS = {
    "10d_5+5": (1, 1),
    "20d_10+10": (2, 2),
    "20d_5+15": (1, 3),
}
ENDPOINT_METRIC_ID = "masked_ndvi_mse"
RANK_DEFINITION = "participation_ratio = (sum s)^2 / sum s^2 of singular values of centered per-sample endpoint-state means; eps=0"


def _ln(x):
    import torch

    return torch.nn.functional.layer_norm(x, (x.shape[-1],))


def _effective_rank(mat):
    import torch

    if mat is None or mat.shape[0] < 2:
        return float("nan")
    mat = mat - mat.mean(dim=0, keepdim=True)
    try:
        s = torch.linalg.svdvals(mat).clamp_min(0)
    except Exception:
        return float("nan")
    denom = float((s * s).sum())
    return float((s.sum() ** 2) / denom) if denom > 0 else 0.0


def _masked_ndvi_mse(pred_ndvi, target_ndvi, veg):
    import torch

    per = (pred_ndvi - target_ndvi).pow(2)
    if veg is None:
        return float(per.mean()), float(per.numel())
    m = veg.to(per.dtype)
    denom = float(m.sum())
    return (float((per * m).sum()), denom) if denom > 0 else (0.0, 0.0)


def evaluate_composition(model, batches, *, depths=None, shuffle_repeats: int = 8, seed: int = 42):
    """Core Q4 computation over prepared batches. ``model`` is the raw A' model."""

    import torch
    from data.stage2_contract import model_input_view
    from data.earthnet_fields import compute_ndvi

    core = getattr(model, "core", None)
    transition = getattr(model, "transition", None)
    if core is None or transition is None or getattr(core, "ndvi_head", None) is None:
        raise ValueError("Q4 requires an A' model with .core.ndvi_head and .transition")
    depths = depths or DEPTHS
    fsi = int(getattr(model, "future_start_index", 10))
    gen = torch.Generator().manual_seed(int(seed))

    acc = {name: {"direct_sse": 0.0, "comp_sse": 0.0, "endpoint_w": 0.0,
                  "gap_raw": 0.0, "gap_shuffle": 0.0, "out_gap_sse": 0.0, "out_gap_w": 0.0,
                  "w": 0.0} for name in depths}
    direct_states = {name: [] for name in depths}
    move = {name: {"raw": 0.0, "ctx_std": 0.0, "chan_std": 0.0} for name in depths}
    n = 0

    was_training = model.training
    model.eval()

    def seg(state, d, dmask, cal, dt, geo, lo, hi):
        return transition(state, d[:, lo:hi], dmask[:, lo:hi], cal[:, lo:hi], dt[:, lo:hi], geo,
                          return_diagnostics=True)["state"]

    with torch.no_grad():
        for batch in batches:
            mv = model_input_view(batch)
            init = core.initialize_state(mv)
            state0 = init["state"]
            last_rgbn = init["last_valid_rgbn"]
            red, nir = last_rgbn[:, 2], last_rgbn[:, 3]
            base = ((nir - red) / (nir + red + 1e-6)).clamp(-1.0, 1.0)  # [B,Hc,Wc]
            geo = core.encode_geo(mv["G"], mv.get("G_mask"), expected_tokens=state0.shape[1])
            d, dmask, cal, dt = mv["D_path"], mv["D_mask"], mv["C_path"], mv["delta_t_path"]

            target = batch.get("x_target")
            veg_all = batch.get("target_veg_mask", batch.get("target_mask"))
            tgt_ndvi_all = compute_ndvi(target, 2, 3).clamp(-1.0, 1.0) if target is not None else None

            bs = state0.shape[0]
            for name, (h1, h2) in depths.items():
                endpoint_h = h1 + h2
                z_direct = seg(state0, d, dmask, cal, dt, geo, fsi, fsi + endpoint_h)
                z_comp = seg(seg(state0, d, dmask, cal, dt, geo, fsi, fsi + h1),
                             d, dmask, cal, dt, geo, fsi + h1, fsi + endpoint_h)

                # LayerNorm-space paired gap + seeded cross-sample shuffle floor.
                gap_raw = float((_ln(z_direct) - _ln(z_comp)).pow(2).mean())
                shuf = 0.0
                for _ in range(shuffle_repeats):
                    perm = torch.randperm(bs, generator=gen)
                    shuf += float((_ln(z_direct) - _ln(z_comp[perm])).pow(2).mean())
                shuf /= max(shuffle_repeats, 1)
                acc[name]["gap_raw"] += gap_raw * bs
                acc[name]["gap_shuffle"] += shuf * bs

                # Endpoint error + output-space gap via the DIRECT NDVI closure.
                nd_direct = core.decode_ndvi(z_direct.unsqueeze(1), base).squeeze(1).squeeze(1)  # [B,H,W]
                nd_comp = core.decode_ndvi(z_comp.unsqueeze(1), base).squeeze(1).squeeze(1)
                if tgt_ndvi_all is not None and (endpoint_h - 1) < tgt_ndvi_all.shape[1]:
                    idx = endpoint_h - 1
                    tgt = tgt_ndvi_all[:, idx]
                    veg = None if veg_all is None else veg_all[:, idx]
                    sd, wd = _masked_ndvi_mse(nd_direct, tgt, veg)
                    sc, _ = _masked_ndvi_mse(nd_comp, tgt, veg)
                    acc[name]["direct_sse"] += sd
                    acc[name]["comp_sse"] += sc
                    acc[name]["endpoint_w"] += wd
                og, ogw = _masked_ndvi_mse(nd_direct, nd_comp, None if veg_all is None else veg_all[:, endpoint_h - 1])
                acc[name]["out_gap_sse"] += og
                acc[name]["out_gap_w"] += ogw

                direct_states[name].append(z_direct.mean(dim=1))  # [B,D]
                move[name]["raw"] += float((z_direct - state0).norm(dim=-1).mean()) * bs
                move[name]["ctx_std"] += float(state0.std()) * bs
                move[name]["chan_std"] += float(z_direct.std(dim=(0, 1)).mean()) * bs
                acc[name]["w"] += bs
            n += bs

    if was_training:
        model.train()
    if n == 0:
        raise RuntimeError("no samples were evaluated")

    per_depth, state_summary = {}, {}
    for name, (h1, h2) in depths.items():
        w = max(acc[name]["w"], 1.0)
        ew = max(acc[name]["endpoint_w"], 1.0)
        ow = max(acc[name]["out_gap_w"], 1.0)
        gap_raw = acc[name]["gap_raw"] / w
        gap_shuffle = acc[name]["gap_shuffle"] / w
        mats = torch.cat(direct_states[name], dim=0) if direct_states[name] else None
        eff_rank = _effective_rank(mats)
        endpoint_h = h1 + h2
        per_depth[name] = {
            "h1": h1, "h2": h2, "endpoint_h": endpoint_h,
            "endpoint_metric_id": ENDPOINT_METRIC_ID,
            "endpoint_direct_error": acc[name]["direct_sse"] / ew,
            "endpoint_composed_error": acc[name]["comp_sse"] / ew,
            "state_path_gap_raw": gap_raw,
            "state_shuffle_reference": gap_shuffle,
            "state_path_gap_normalized": (gap_raw / gap_shuffle) if gap_shuffle > 0 else float("nan"),
            "output_path_gap": acc[name]["out_gap_sse"] / ow,
            "effective_rank": eff_rank,
            "n_samples": n,
        }
        ctx_std = move[name]["ctx_std"] / w
        state_summary[str(endpoint_h)] = {
            "horizon": endpoint_h,
            "state_movement_raw": move[name]["raw"] / w,
            "context_state_std": ctx_std,
            "state_movement_normalized": (move[name]["raw"] / w) / ctx_std if ctx_std > 0 else float("nan"),
            "future_state_channel_std": move[name]["chan_std"] / w,
            "effective_rank": eff_rank,
            "rank_definition": RANK_DEFINITION,
            "n_samples": n,
            "n_tokens": int(mats.shape[0]) if mats is not None else 0,
        }
    return {
        "num_samples": n,
        "endpoint_metric_id": ENDPOINT_METRIC_ID,
        "shuffle_repeats": int(shuffle_repeats),
        "shuffle_seed": int(seed),
        "per_depth": per_depth,
        "state_summary": state_summary,
        "rank_definition": RANK_DEFINITION,
    }


def apply_guards(report: dict, *, guard_direct_threshold: float, guard_composed_threshold: float) -> dict:
    """Dual validation-frozen endpoint guards bound to the endpoint metric."""

    rows = {}
    all_pass = True
    for name, blk in report["per_depth"].items():
        d_ok = blk["endpoint_direct_error"] <= guard_direct_threshold
        c_ok = blk["endpoint_composed_error"] <= guard_composed_threshold
        rows[name] = {"guard_direct_pass": bool(d_ok), "guard_composed_pass": bool(c_ok),
                      "guard_pass": bool(d_ok and c_ok),
                      # per schema 7.1: gap numbers stay diagnostic when guard fails.
                      "interpretation_eligible": bool(d_ok and c_ok)}
        all_pass = all_pass and d_ok and c_ok
    return {
        "endpoint_metric_id": report["endpoint_metric_id"],
        "guard_direct_threshold": guard_direct_threshold,
        "guard_composed_threshold": guard_composed_threshold,
        "per_depth": rows,
        "n_guard_pass": sum(1 for r in rows.values() if r["guard_pass"]),
        "n_total": len(rows),
        "all_pass": all_pass,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--partition-name", required=True)
    parser.add_argument("--partition-role", required=True, choices=["train", "heldout"])
    parser.add_argument("--split", required=True)
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--data-root")
    parser.add_argument("--conditioning-stats-path")
    parser.add_argument("--external-driver-root")
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--shuffle-repeats", type=int, default=8)
    parser.add_argument("--shuffle-seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=0, help="Max batches (NON-FORMAL smoke).")
    parser.add_argument("--guard-direct-threshold", type=float, default=None)
    parser.add_argument("--guard-composed-threshold", type=float, default=None)
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

    is_smoke = bool(args.limit and args.limit > 0)
    if not is_smoke and (args.guard_direct_threshold is None or args.guard_composed_threshold is None):
        raise SystemExit("formal run requires --guard-direct-threshold and --guard-composed-threshold (fail-closed)")

    config = load_config(args.config)
    for key, value in (
        ("root", args.data_root), ("manifest_path", args.manifest_path),
        ("conditioning_stats_path", args.conditioning_stats_path),
        ("external_driver_root", args.external_driver_root), ("dgh_stats_path", args.dgh_stats_path),
    ):
        if value is not None:
            config["data"][key] = value
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

    data_cfg = EarthNet2021Config.from_config(config["data"], split=args.split)
    dataset = EarthNet2021Dataset(data_cfg)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False,
                        num_workers=args.num_workers, drop_last=False, collate_fn=collate_earthnet2021)

    def prepared():
        for i, batch in enumerate(loader):
            if args.limit and i >= args.limit:
                break
            batch = move_batch_to_device(batch, device)
            yield prepare_stage2_batch_for_model(batch, data_cfg)

    report = evaluate_composition(raw, prepared(), shuffle_repeats=args.shuffle_repeats, seed=args.shuffle_seed)
    sha_after = sha256_file(args.checkpoint)
    report.update({
        "partition_name": args.partition_name,
        "partition_role": args.partition_role,
        "split": args.split,
        "checkpoint": str(Path(args.checkpoint).resolve()),
        "checkpoint_sha256_before": sha_before,
        "checkpoint_sha256_after": sha_after,
        "checkpoint_unchanged": sha_before == sha_after,
        "is_smoke": is_smoke,
        "formal": not is_smoke,
    })
    if args.guard_direct_threshold is not None and args.guard_composed_threshold is not None:
        report["guard"] = apply_guards(
            report, guard_direct_threshold=args.guard_direct_threshold,
            guard_composed_threshold=args.guard_composed_threshold,
        )
    if not report["checkpoint_unchanged"]:
        raise SystemExit("checkpoint file changed during evaluation -- aborting")

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(_finite_only(report), handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    tmp.replace(out)
    print(json.dumps(_finite_only(report), indent=2, ensure_ascii=False, allow_nan=False))


def _finite_only(obj):
    """Recursively replace non-finite floats with None (schema forbids NaN/Inf)."""

    import math

    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _finite_only(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_finite_only(v) for v in obj]
    return obj


if __name__ == "__main__":
    main()
