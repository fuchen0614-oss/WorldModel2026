"""Run complete val_dev evaluation for named checkpoints and select one.

This command intentionally delegates each candidate to the existing strict
Stage2 evaluator.  It does not use the trainer's fixed 512-sample monitor and
does not silently score a checkpoint under a different contract.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.checkpoint_selection import discover_checkpoint_candidates, select_best_candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint-dir")
    parser.add_argument("--checkpoint", action="append", default=[])
    parser.add_argument("--split", default="val")
    parser.add_argument("--data-root")
    parser.add_argument("--external-driver-root")
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--conditioning-stats-path")
    parser.add_argument("--manifest-path")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--metric", default=None, help="Metric key, default config validation.primary_metric or MAE")
    parser.add_argument("--mode", choices=("min", "max"), default=None)
    parser.add_argument("--include-step-checkpoints", action="store_true")
    parser.add_argument("--allow-checkpoint-contract-mismatch", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    # Keep --help and the pure candidate-discovery path usable in lightweight
    # analysis environments; the training module is imported only for a real
    # evaluation run where PyTorch is required anyway.
    from train.train_stage2_earthnet import load_config

    config = load_config(args.config)
    validation_cfg = config.get("validation", {})
    metric = args.metric or str(validation_cfg.get("primary_metric", "MAE"))
    mode = args.mode or str(validation_cfg.get("mode", "min"))
    if args.checkpoint:
        candidates = discover_checkpoint_candidates(
            Path(args.checkpoint[0]).parent,
            include_step_checkpoints=args.include_step_checkpoints,
            explicit=args.checkpoint,
        )
    else:
        if not args.checkpoint_dir:
            parser.error("one of --checkpoint-dir or --checkpoint is required")
        candidates = discover_checkpoint_candidates(
            args.checkpoint_dir,
            include_step_checkpoints=args.include_step_checkpoints,
        )

    root = ROOT
    eval_dir = Path(args.output).expanduser().resolve().parent
    eval_dir.mkdir(parents=True, exist_ok=True)
    evaluations: list[dict[str, object]] = []
    for checkpoint in candidates:
        sidecar = eval_dir / f"{checkpoint.stem}_{args.split}_full_eval.json"
        command = [
            sys.executable,
            str(root / "eval/eval_stage2_earthnet.py"),
            "--config", str(Path(args.config).expanduser().resolve()),
            "--checkpoint", str(checkpoint),
            "--split", args.split,
            "--batch-size", str(args.batch_size),
            "--num-workers", str(args.num_workers),
            "--output", str(sidecar),
        ]
        for flag, value in (
            ("--data-root", args.data_root),
            ("--external-driver-root", args.external_driver_root),
            ("--dgh-stats-path", args.dgh_stats_path),
            ("--conditioning-stats-path", args.conditioning_stats_path),
            ("--manifest-path", args.manifest_path),
        ):
            if value:
                command.extend([flag, value])
        if args.allow_checkpoint_contract_mismatch:
            command.append("--allow-checkpoint-contract-mismatch")
        print("[stage2-select] evaluating", checkpoint, flush=True)
        subprocess.run(command, cwd=root, check=True)
        with sidecar.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        evaluations.append(
            {
                "checkpoint": str(checkpoint),
                "sidecar": str(sidecar),
                "metrics": payload.get("metrics", {}),
                "provenance": payload.get("provenance", {}),
            }
        )

    selection = select_best_candidate(evaluations, metric=metric, mode=mode)
    selection.update(
        {
            "config": str(Path(args.config).expanduser().resolve()),
            "split": args.split,
            "manifest_path": args.manifest_path,
            "complete_val": True,
            "official_ens_scored": False,
            "note": (
                "This selector uses the complete requested split. Official ENS "
                "remains a separate prediction-directory closure."
            ),
        }
    )
    output = Path(args.output).expanduser().resolve()
    temp = output.with_suffix(output.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(selection, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    temp.replace(output)
    print(json.dumps(selection, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
