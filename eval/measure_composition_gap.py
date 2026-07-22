"""Post-hoc composition-gap measurement for the Plan A S1a Direct checkpoint.

Read-only. Loads a TRAINED ObsWorldDirectPathModel and measures whether its
shared ControlledTransition COMPOSES: does one K-token direct transition reach
the same latent state as the same control path split into consecutive hops?

    z(s0 --K*5d-->)  vs  z(s0 --5d--> --5d--> ...)     over identical D/C/dt.

This is a POST-HOC probe (no rollout, no retraining): the Direct model already
owns .core + .transition; we just call the trained transition in a composed
way. It supplies the falsifiable Table-3(i) evidence, WITH the guards the
adversarial review demanded so a small gap cannot be a trivial artefact:

  (a) state-movement:  ||z_direct - s0|| and state std  -> proves T actually
      moves the state (guards against near-identity / residual_scale~0 collapse
      that would make any two paths agree trivially).
  (b) endpoint accuracy (best-effort, only if targets are in the batch): decode
      z_direct AND z_composed and score both vs the true endpoint frame -> shows
      "both accurate AND agree", not "two mediocre predictions agree".
  (c) shuffle-pair floor + normalization: the gap between mismatched (i,j) pairs
      is the chance level; a real result needs gap << shuffle-floor.
  (d) multi-depth curve: 10=5+5, 15=5+5+5, and an unequal 15=10+5 split -> a
      composable transition should stay consistent with depth, not just at 2
      steps. Reporting only 10=5+5 is the weakest possible semigroup evidence.

NOTE: cannot be smoked on the local box (no /csy-mix02 data/checkpoint). Smoke
on the server first with --num-batches 2 before trusting the numbers.

Example (server):
  conda activate WorldModel
  python eval/measure_composition_gap.py \
    --config configs/train/plan_a_stage2v3_vits_train.yaml \
    --checkpoint checkpoints/plan_a_s1a/checkpoint_best.pt \
    --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet \
    --split ood-t_chopped \
    --manifest evaluations/table1_oodt_plan_a_s1a_best/greenearthnet_oodt_chopped_manifest.json \
    --manifest-protocol greenearthnet_cvpr2024_chopped_v1 \
    --conditioning-stats-path artifacts/protocols/earthnet2021x_physical4_v1_20260717_092048/conditioning_stats_physical4_v1_train_dev.json \
    --num-batches 12 --batch-size 8 --output evaluations/composition_gap_plan_a_s1a.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    EarthNet2021Dataset,
    collate_earthnet2021,
)
from train.train_stage2_earthnet import (
    create_stage2_model,
    load_config,
    load_stage2_model_state,
    model_input_view,
    move_batch_to_device,
    prepare_stage2_batch_for_model,
)


def _ln(z: torch.Tensor) -> torch.Tensor:
    """Fixed (non-learnable) LayerNorm, exactly as PartitionConsistencyLoss."""
    return F.layer_norm(z, (z.shape[-1],))


def _gap(z_a: torch.Tensor, z_b: torch.Tensor) -> torch.Tensor:
    """Per-sample layer-normed MSE gap between two [B,N,D] states -> [B]."""
    return (_ln(z_a) - _ln(z_b)).pow(2).mean(dim=-1).mean(dim=-1)


def _run_segment(model, state, geo, batch, lo, hi):
    """Apply the shared transition over control tokens [lo:hi] from `state`."""
    out = model.transition(
        state,
        batch["D_path"][:, lo:hi],
        batch["D_mask"][:, lo:hi],
        batch["C_path"][:, lo:hi],
        batch["delta_t_path"][:, lo:hi],
        geo,
        return_diagnostics=True,
    )
    return out["state"]


def _direct_to(model, state0, geo, batch, fsi, k):
    return _run_segment(model, state0, geo, batch, fsi, fsi + k)


def _composed_to(model, state0, geo, batch, fsi, hops):
    state = state0
    offset = fsi
    for hop in hops:
        state = _run_segment(model, state, geo, batch, offset, offset + hop)
        offset += hop
    return state


# (label, direct_token_count K, hop token-lengths summing to K)
DEPTHS = [
    ("10d: 5+5", 2, [1, 1]),
    ("15d: 5+5+5", 3, [1, 1, 1]),
    ("15d: 10+5 (unequal)", 3, [2, 1]),
    ("20d: 5x4", 4, [1, 1, 1, 1]),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--manifest-protocol", required=True)
    ap.add_argument("--conditioning-stats-path", default=None)
    ap.add_argument("--num-batches", type=int, default=12)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    torch.manual_seed(args.seed)

    config = load_config(args.config)
    config["data"].update(
        {
            "root": args.data_root,
            "split": args.split,
            "manifest_path": args.manifest,
            "manifest_protocol": args.manifest_protocol,
            "require_manifest": True,
            "strict": True,
        }
    )
    if args.conditioning_stats_path:
        config["data"]["conditioning_stats_path"] = args.conditioning_stats_path
    config["model"]["encoder"]["from_checkpoint"] = None
    config["model"]["compute_latent_targets"] = False

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = create_stage2_model(config, device)
    load_stage2_model_state(model, checkpoint.get("model_state_dict", checkpoint), strict=True)
    model.eval()
    raw = model.module if hasattr(model, "module") else model
    if not hasattr(raw, "transition") or not hasattr(raw, "core"):
        raise SystemExit(
            f"This probe needs a Direct path model with .core/.transition; got {type(raw).__name__}"
        )
    fsi = int(getattr(raw, "future_start_index", 10))
    residual_scale = float(raw.transition.residual_scale.detach().cpu())

    data_cfg = EarthNet2021Config.from_config(config["data"], split=args.split)
    loader = DataLoader(
        EarthNet2021Dataset(data_cfg),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
        drop_last=False,
        collate_fn=collate_earthnet2021,
    )

    # Accumulators
    n_samples = 0
    depth_gap = {label: 0.0 for label, _, _ in DEPTHS}
    depth_shuffle = {label: 0.0 for label, _, _ in DEPTHS}
    depth_raw_gap = {label: 0.0 for label, _, _ in DEPTHS}  # non-layernorm
    delta_direct = 0.0  # ||z_direct(10d) - s0||
    delta_composed = 0.0  # ||z_composed(5+5) - s0||
    state_std_sum = 0.0
    endpoint = {"direct_mae": 0.0, "composed_mae": 0.0, "n": 0}

    with torch.no_grad():
        for bi, batch in enumerate(loader):
            if bi >= args.num_batches:
                break
            batch = move_batch_to_device(batch, device)
            batch = prepare_stage2_batch_for_model(batch, data_cfg)
            inputs = model_input_view(batch, include_training_targets=False)

            initialized = raw.core.initialize_state(inputs)
            state0 = initialized["state"]
            baseline = initialized.get("last_valid_rgbn")
            geo = raw.core.encode_geo(
                inputs["G"], inputs.get("G_mask"), expected_tokens=state0.shape[1]
            )
            bsz = state0.shape[0]
            perm = torch.randperm(bsz, device=state0.device)

            for label, k, hops in DEPTHS:
                z_d = _direct_to(raw, state0, geo, inputs, fsi, k)
                z_c = _composed_to(raw, state0, geo, inputs, fsi, hops)
                depth_gap[label] += float(_gap(z_d, z_c).sum())
                depth_raw_gap[label] += float((z_d - z_c).pow(2).mean(dim=-1).mean(dim=-1).sum())
                # shuffle floor: direct vs a MISMATCHED composed (chance level)
                depth_shuffle[label] += float(_gap(z_d, z_c[perm]).sum())
                if label.startswith("10d"):
                    delta_direct += float((z_d - state0).norm(dim=-1).mean(dim=-1).sum())
                    delta_composed += float((z_c - state0).norm(dim=-1).mean(dim=-1).sum())
                    # (b) endpoint accuracy vs true 10d frame (future index 1),
                    #     best-effort: only if the loader carried the target.
                    tgt = batch.get("x_target")
                    tmask = batch.get("target_mask")
                    if tgt is not None and tgt.shape[1] > 1:
                        pd = raw.core.decode_states(z_d, baseline=baseline)["mean"]
                        pc = raw.core.decode_states(z_c, baseline=baseline)["mean"]
                        y = tgt[:, 1]
                        if tmask is not None:
                            m = tmask[:, 1].unsqueeze(1).to(pd.dtype)
                            denom = m.sum().clamp_min(1.0)
                            endpoint["direct_mae"] += float(((pd - y).abs() * m).sum() / denom)
                            endpoint["composed_mae"] += float(((pc - y).abs() * m).sum() / denom)
                        else:
                            endpoint["direct_mae"] += float((pd - y).abs().mean())
                            endpoint["composed_mae"] += float((pc - y).abs().mean())
                        endpoint["n"] += 1

            state_std_sum += float(state0.float().std(dim=(1, 2), unbiased=False).sum())
            n_samples += bsz

    if n_samples == 0:
        raise SystemExit("No samples processed; check split/manifest.")

    def _avg(x):
        return x / n_samples

    report = {
        "checkpoint": args.checkpoint,
        "split": args.split,
        "num_samples": n_samples,
        "residual_scale": residual_scale,
        "future_start_index": fsi,
        # (a) state movement — gap is only meaningful if T actually moves state
        "state_movement": {
            "delta_direct_10d_norm": _avg(delta_direct),
            "delta_composed_10d_norm": _avg(delta_composed),
            "state_std": _avg(state_std_sum),
            "note": "if delta_*_norm << state_std, transition is near-identity -> a small gap is trivial",
        },
        # (c)+(d) gaps per depth, with shuffle floor + normalized ratio
        "composition_gap": {
            label: {
                "gap_layernorm": _avg(depth_gap[label]),
                "gap_raw": _avg(depth_raw_gap[label]),
                "shuffle_floor": _avg(depth_shuffle[label]),
                "normalized_gap_vs_floor": (
                    _avg(depth_gap[label]) / _avg(depth_shuffle[label])
                    if depth_shuffle[label] > 0 else None
                ),
            }
            for label, _, _ in DEPTHS
        },
    }
    # (b) endpoint accuracy (only if targets were present)
    if endpoint["n"] > 0:
        report["endpoint_accuracy_10d"] = {
            "direct_mae": endpoint["direct_mae"] / endpoint["n"],
            "composed_mae": endpoint["composed_mae"] / endpoint["n"],
            "note": "both should be low AND close -> 'accurate and agree', not 'mediocre and agree'",
        }
    else:
        report["endpoint_accuracy_10d"] = {
            "skipped": "no x_target in batch (run on a split that loads targets to get this guard)",
        }

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"\nwrote {args.output}")

    # Headline interpretation
    g = report["composition_gap"]["10d: 5+5"]
    print(
        "\n=== 一句话解读 ===\n"
        f"residual_scale={residual_scale:.3f}；state 位移 direct={report['state_movement']['delta_direct_10d_norm']:.3f} "
        f"vs state_std={report['state_movement']['state_std']:.3f}（位移应 > 0 才说明 T 推动了状态）\n"
        f"10d 组合 gap={g['gap_layernorm']:.4f}，shuffle 下限={g['shuffle_floor']:.4f}，"
        f"归一比={g['normalized_gap_vs_floor']}\n"
        "→ 归一比 << 1 且 state 有位移 = 干净的可组合证据；归一比接近 1 或 state 几乎不动 = 结果不成立。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
