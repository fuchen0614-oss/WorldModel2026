"""Q2 load-bearing evidence for a SINGLE frozen A' checkpoint.

TerraState's claim is that one checkpoint carries a *forecast-bearing* predictive
state: the transition T and the NDVI closure O_ndvi(zh) must actually change the
prediction, not decorate a persistence baseline. This tool measures that with
in-memory, fully recoverable interventions on the model's REAL modules -- it does
NOT copy Plan B's gate and it does NOT mutate anything on disk.

Interventions (all vs. the same frozen weights, restored afterwards):
  * full            -- ndvi = clamp(baseline + tanh(scale * O_ndvi(zh)))
  * T_identity      -- replace zh by z0 (transition does nothing); decode from z0.
                       Isolates whether the horizon-conditioned transition T is
                       load-bearing.
  * residual_ref    -- set ndvi_residual_scale -> 0 (reference = persistence), so
                       ndvi == last-valid baseline. Isolates whether the NDVI head
                       O_ndvi contributes beyond persistence. Snapshotted+restored.
  * rgbn_closure_cut-- decode the reflectance head O from z0 vs zh. Isolates the
                       reflectance closure.

A load-bearing module must make ``full`` strictly better (lower masked-NDVI-MSE
over the evaluator-aligned vegetation mask) than its ablation by a pre-declared
margin. Guards are pre-declared (``--min-degradation``); a formal run FAILS
CLOSED if the guard is not set. The checkpoint file SHA256 is captured before and
after and asserted identical.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ndvi_from_rgbn(rgbn, red_index: int, nir_index: int):
    red = rgbn[:, red_index]
    nir = rgbn[:, nir_index]
    return ((nir - red) / (nir + red + 1e-6)).clamp(-1.0, 1.0)


def evaluate_load_bearing(model, batches, *, red_index: int = 2, nir_index: int = 3):
    """Core Q2 computation over an iterable of prepared batches.

    ``model`` is the raw (unwrapped) A' Direct-path model with a ``core`` that has
    ``ndvi_head`` and ``ndvi_residual_scale``. Each batch must contain the model
    input fields plus ``x_target`` and (ideally) ``target_veg_mask``. Returns a
    plain dict; raises if the model has no NDVI head (not an A' checkpoint).
    """

def evaluate_load_bearing(model, batches, *, red_index: int = 2, nir_index: int = 3,
                          n_boot: int = 2000, bootstrap_seed: int = 42):
    """Core Q2 computation with per-cube masked-NDVI-MSE and paired bootstrap.

    Fixed three arms (RESULT_INGESTION_SCHEMA.md section 5.1):
      full         -- ndvi = clamp(baseline + tanh(scale*O_ndvi(zh)))
      closure_cut  -- residual scale -> 0: the closure's recoverable state
                      contribution is zeroed, restoring the deterministic
                      persistence reference (backbone/reference NOT recomputed).
      T_identity   -- the shared transition is replaced by identity (zh -> z0)
                      while the closure/decoder are unchanged.
    Emits per-cube masked-NDVI-MSE keyed by sample_id, per-arm r2/rmse, the
    paired delta (arm - full) bootstrap CI, and normalized output/state change.
    All interventions are in-memory and exactly restored.
    """

    import numpy as np
    import torch
    from data.stage2_contract import model_input_view
    from data.earthnet_fields import compute_ndvi
    from eval.aprime_paired_stats import paired_bootstrap_ci

    core = getattr(model, "core", None)
    if core is None or getattr(core, "ndvi_head", None) is None:
        raise ValueError("load-bearing tool requires an A' model with core.ndvi_head")

    arms = ("full", "closure_cut", "T_identity")
    percube = {a: [] for a in arms}          # per-cube masked-NDVI-MSE
    tvar = []                                 # per-cube masked target variance (for R2)
    out_change = {"closure_cut": [], "T_identity": []}
    state_change_tident = []
    ids = []

    def _cube_mse(pred_bhw, tgt_bhw, mask_bhw):
        per = (pred_bhw - tgt_bhw).pow(2)
        if mask_bhw is None:
            return float(per.mean())
        d = mask_bhw.sum().clamp_min(1.0)
        return float((per * mask_bhw).sum() / d)

    was_training = model.training
    model.eval()
    with torch.no_grad():
        for batch in batches:
            mv = model_input_view(batch)
            out = model(mv, selected_steps=None)
            if "ndvi_pred" not in out:
                raise ValueError("model forward did not emit ndvi_pred (A' head off?)")
            z0 = out["z_context"]
            zh = out["z_pred"]
            z0_rep = z0.unsqueeze(1).expand_as(zh)
            ndvi_full = out["ndvi_pred"].squeeze(2)  # [B,K,H,W]

            init = core.initialize_state(mv)
            base = _ndvi_from_rgbn(init["last_valid_rgbn"], red_index, nir_index)

            ndvi_tident = core.decode_ndvi(z0_rep, base).squeeze(2)  # closure intact, T=identity
            saved = core.ndvi_residual_scale.detach().clone()
            core.ndvi_residual_scale.zero_()
            ndvi_cut = core.decode_ndvi(zh, base).squeeze(2)          # scale->0 = persistence ref
            core.ndvi_residual_scale.copy_(saved)                     # exact recovery
            arm_ndvi = {"full": ndvi_full, "closure_cut": ndvi_cut, "T_identity": ndvi_tident}

            target = batch["x_target"].index_select(1, out["step_indices"].to(z0.device))
            tgt_ndvi = compute_ndvi(target, red_index, nir_index).clamp(-1.0, 1.0)
            veg = batch.get("target_veg_mask", batch.get("target_mask"))
            if veg is not None:
                veg = veg.index_select(1, out["step_indices"].to(z0.device))
            meta = batch.get("meta")
            ctx_std = float(z0.std())
            bs = target.shape[0]

            for b in range(bs):
                m = None if veg is None else veg[b]
                for a in arms:
                    percube[a].append(_cube_mse(arm_ndvi[a][b], tgt_ndvi[b], m))
                if m is None:
                    tvar.append(float(tgt_ndvi[b].var()))
                    tstd = float(tgt_ndvi[b].std()) + 1e-6
                else:
                    d = m.sum().clamp_min(1.0)
                    mu = (tgt_ndvi[b] * m).sum() / d
                    tvar.append(float(((tgt_ndvi[b] - mu).pow(2) * m).sum() / d))
                    tstd = float((((tgt_ndvi[b] - mu).pow(2) * m).sum() / d) ** 0.5) + 1e-6
                for a in ("closure_cut", "T_identity"):
                    diff = (arm_ndvi[a][b] - ndvi_full[b]).abs()
                    oc = float(diff.mean()) if m is None else float((diff * m).sum() / m.sum().clamp_min(1.0))
                    out_change[a].append(oc / tstd)
                state_change_tident.append(float((zh[b] - z0_rep[b]).norm(dim=-1).mean()) / (ctx_std + 1e-6))
                ids.append(meta[b].get("sample_id") if meta else f"cube_{len(ids)}")

    if was_training:
        model.train()
    if not ids:
        raise RuntimeError("no samples were evaluated")

    tvar_mean = float(np.mean(tvar)) if tvar else 0.0
    full = np.asarray(percube["full"], dtype=np.float64)
    rows = {}
    for a in arms:
        arr = np.asarray(percube[a], dtype=np.float64)
        mse_mean = float(arr.mean())
        rows[a] = {
            "arm_id": a,
            "masked_ndvi_mse": mse_mean,
            "rmse": mse_mean ** 0.5,
            "r2": (1.0 - mse_mean / tvar_mean) if tvar_mean > 0 else None,
            "n_samples": int(arr.size),
        }
    for a in ("closure_cut", "T_identity"):
        delta = (np.asarray(percube[a]) - full).tolist()
        ci = paired_bootstrap_ci(delta, n_boot=n_boot, seed=bootstrap_seed)
        rows[a]["delta_mse_vs_full"] = ci["delta_mean"]
        rows[a]["delta_ci_low"] = ci["ci_low"]
        rows[a]["delta_ci_high"] = ci["ci_high"]
        rows[a]["output_change_normalized"] = float(np.mean(out_change[a]))
    rows["full"]["output_change_normalized"] = 0.0
    rows["full"]["state_change_normalized"] = 0.0
    # Per schema 5.1: closure cut zeroes the closure's use of state, it does NOT
    # move the state itself -> state_change is not_applicable.
    rows["closure_cut"]["state_change_normalized"] = None
    rows["T_identity"]["state_change_normalized"] = float(np.mean(state_change_tident))

    return {
        "endpoint_metric_id": "masked_ndvi_mse",
        "n_samples": len(ids),
        "per_cube_ids": ids,
        "per_cube_mse": {a: percube[a] for a in arms},
        "arms": rows,
        "bootstrap": {"n_boot": int(n_boot), "seed": int(bootstrap_seed)},
    }


def apply_guards(report: dict, *, min_degradation: float = 0.0) -> dict:
    """Load-bearing guard: each ablation's paired delta CI must exceed the margin.

    An arm is load-bearing iff cutting it strictly increases error, i.e. the LOWER
    bound of the paired (arm - full) delta CI is above ``min_degradation``.
    """

    rows = report["arms"]
    checks = {}
    for a in ("closure_cut", "T_identity"):
        checks[f"{a}_load_bearing"] = bool(rows[a].get("delta_ci_low", float("-inf")) > min_degradation)
    return {
        "min_degradation": min_degradation,
        "checks": checks,
        "all_pass": all(checks.values()),
    }


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
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="Max batches (NON-FORMAL smoke).")
    parser.add_argument(
        "--min-degradation", type=float, default=None,
        help="Pre-declared load-bearing margin. REQUIRED for a formal run (fail-closed).",
    )
    parser.add_argument("--allow-checkpoint-contract-mismatch", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    import torch
    from torch.utils.data import DataLoader
    from data.datasets.earthnet2021 import (
        EarthNet2021Config, EarthNet2021Dataset, collate_earthnet2021,
    )
    from train.stage2_provenance import sha256_file
    from train.train_stage2_earthnet import (
        load_config, create_stage2_model, load_stage2_model_state,
        move_batch_to_device, prepare_stage2_batch_for_model,
    )
    from eval.stage2_evaluation_provenance import verify_checkpoint_contract
    from eval.aprime_provenance import finite_only

    is_smoke = bool(args.limit and args.limit > 0)
    if not is_smoke and args.min_degradation is None:
        raise SystemExit("formal run requires --min-degradation (guard fail-closed)")

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
    verify_checkpoint_contract(
        checkpoint, config, allow_mismatch=args.allow_checkpoint_contract_mismatch
    )
    device = torch.device("cpu")
    model = create_stage2_model(config, device)
    load_stage2_model_state(model, checkpoint.get("model_state_dict", checkpoint), strict=True)
    raw = model.module if hasattr(model, "module") else model

    data_cfg = EarthNet2021Config.from_config(config["data"], split=args.split)
    dataset = EarthNet2021Dataset(data_cfg)
    loader = DataLoader(
        dataset, batch_size=args.batch_size, shuffle=False,
        num_workers=args.num_workers, drop_last=False, collate_fn=collate_earthnet2021,
    )

    def prepared():
        for i, batch in enumerate(loader):
            if args.limit and i >= args.limit:
                break
            batch = move_batch_to_device(batch, device)
            yield prepare_stage2_batch_for_model(batch, data_cfg)

    report = evaluate_load_bearing(
        raw, prepared(),
        red_index=data_cfg.band_spec.red_index, nir_index=data_cfg.band_spec.nir_index,
    )
    sha_after = sha256_file(args.checkpoint)
    report["checkpoint"] = str(Path(args.checkpoint).resolve())
    report["checkpoint_sha256_before"] = sha_before
    report["checkpoint_sha256_after"] = sha_after
    report["checkpoint_unchanged"] = (sha_before == sha_after)
    report["is_smoke"] = is_smoke
    report["formal"] = not is_smoke
    if args.min_degradation is not None:
        report["guard"] = apply_guards(report, min_degradation=args.min_degradation)
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

