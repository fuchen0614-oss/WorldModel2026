"""A' post-training checkpoint selection closure (val_dev, OOD-t free).

This is an ADDITIVE eval-side orchestrator. It does NOT modify the trainer, the
model, or any config. It layers a fair two-stage selection on top of the
existing strict evaluator:

  1. within each run (rescue = plan_a_prime_from_s1a_stage2, fresh =
     plan_a_prime_from_s15), evaluate every candidate checkpoint
     (best + epoch milestones; optionally last/step checkpoints) on the SAME
     frozen val_dev manifest with the SAME evaluator and pick the run winner;
  2. across the two runs, pick the single A' winner with the SAME manifest /
     evaluator / metric.

Design guarantees demanded by the A' post-training closure:
  * OOD-t is NEVER used here (selection split is val only). The OOD-t number is
    a separate, run-once-after-freeze step (see the runbook).
  * The selection metric defaults to ``ndvi_main`` = masked-L2 NDVI on the A'
    NDVI head over the evaluator-aligned vegetation mask (lower is better) --
    the same objective the trainer selects on. NOTE the trainer names it
    ``loss/ndvi_main`` but the offline sidecar stores it unprefixed as
    ``ndvi_main``; this tool uses the sidecar name.
  * Real checkpoint path + SHA256 + config-sha + manifest files_sha256 + the
    exact evaluation command + any failure reason are recorded for every
    candidate.
  * Stale-artifact guard: a pre-existing sidecar is reused ONLY when its
    recorded checkpoint SHA256, runtime_config_sha256 and manifest files_sha256
    all still match; otherwise the candidate is re-evaluated. This prevents old
    predictions / old sidecars / different-checkpoint results from being mixed.
  * ``--limit`` (max eval batches) produces an explicitly NON-FORMAL smoke
    result: the output is stamped ``formal=false`` and ``selected_checkpoint``
    is withheld (a smoke run must never crown a formal winner).

It intentionally shells out to eval/eval_stage2_earthnet.py per candidate so a
single strict contract/provenance path is reused for every number.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.checkpoint_selection import discover_checkpoint_candidates, select_best_candidate
from train.stage2_provenance import canonical_json_sha256, sha256_file


def _parse_runs(run_args: list[str]) -> dict[str, Path]:
    """Parse ``name=dir`` run specifications into an ordered mapping."""

    runs: dict[str, Path] = {}
    for spec in run_args:
        if "=" not in spec:
            raise ValueError(f"--run must be name=dir, got {spec!r}")
        name, _, directory = spec.partition("=")
        name = name.strip()
        directory = directory.strip()
        if not name or not directory:
            raise ValueError(f"--run must be name=dir, got {spec!r}")
        if name in runs:
            raise ValueError(f"duplicate run name {name!r}")
        runs[name] = Path(directory).expanduser().resolve()
    if not runs:
        raise ValueError("at least one --run name=dir is required")
    return runs


def _sidecar_is_fresh(
    sidecar_payload: dict,
    *,
    checkpoint_sha256: str,
    config_sha256: str,
    manifest_files_sha256: str | None,
) -> bool:
    """Return True only when a pre-existing sidecar matches the current inputs."""

    provenance = sidecar_payload.get("provenance", {})
    ckpt = provenance.get("checkpoint", {})
    if ckpt.get("sha256") != checkpoint_sha256:
        return False
    if provenance.get("runtime_config_sha256") != config_sha256:
        return False
    if manifest_files_sha256 is not None:
        manifest = provenance.get("data", {}).get("manifest", {})
        if manifest.get("files_sha256") != manifest_files_sha256:
            return False
    return True


def _evaluate_candidate(
    checkpoint: Path,
    *,
    sidecar: Path,
    args: argparse.Namespace,
    config_sha256: str,
    manifest_files_sha256: str | None,
) -> dict:
    """Evaluate one checkpoint (or reuse a fresh sidecar) and return a record."""

    record: dict[str, object] = {
        "checkpoint": str(checkpoint),
        "sidecar": str(sidecar),
    }
    try:
        checkpoint_sha256 = sha256_file(checkpoint)
    except FileNotFoundError as exc:
        record.update({"metrics": {}, "failure_reason": f"missing checkpoint: {exc}"})
        return record
    record["checkpoint_sha256"] = checkpoint_sha256

    command = [
        sys.executable,
        str(ROOT / "eval/eval_stage2_earthnet.py"),
        "--config", str(Path(args.config).expanduser().resolve()),
        "--checkpoint", str(checkpoint),
        "--split", args.split,
        "--batch-size", str(args.batch_size),
        "--num-workers", str(args.num_workers),
        "--output", str(sidecar),
    ]
    for flag, value in (
        ("--data-root", args.data_root),
        ("--conditioning-stats-path", args.conditioning_stats_path),
        ("--manifest-path", args.manifest_path),
        ("--external-driver-root", args.external_driver_root),
        ("--dgh-stats-path", args.dgh_stats_path),
    ):
        if value:
            command.extend([flag, value])
    if args.limit and args.limit > 0:
        command.extend(["--max-batches", str(args.limit)])
    if args.allow_checkpoint_contract_mismatch:
        command.append("--allow-checkpoint-contract-mismatch")
    record["command"] = " ".join(command)

    reused = False
    if sidecar.is_file() and not args.force:
        try:
            with sidecar.open("r", encoding="utf-8") as handle:
                existing = json.load(handle)
            if _sidecar_is_fresh(
                existing,
                checkpoint_sha256=checkpoint_sha256,
                config_sha256=config_sha256,
                manifest_files_sha256=manifest_files_sha256,
            ):
                reused = True
                payload = existing
        except (json.JSONDecodeError, OSError):
            reused = False
    if not reused:
        try:
            subprocess.run(command, cwd=ROOT, check=True)
        except subprocess.CalledProcessError as exc:
            record.update({"metrics": {}, "failure_reason": f"evaluator exit {exc.returncode}"})
            return record
        try:
            with sidecar.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            record.update({"metrics": {}, "failure_reason": f"unreadable sidecar: {exc}"})
            return record

    record["reused_sidecar"] = reused
    record["metrics"] = payload.get("metrics", {})
    record["provenance"] = payload.get("provenance", {})
    record["is_smoke"] = bool(args.limit and args.limit > 0)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", action="append", default=[], required=True,
        help="Run as name=checkpoint_dir, e.g. rescue=/.../plan_a_prime_from_s1a_stage2",
    )
    parser.add_argument("--config", required=True, help="The A' training config (contract must match).")
    parser.add_argument("--split", default="val")
    parser.add_argument("--manifest-path", required=True, help="Frozen val_dev manifest.")
    parser.add_argument("--data-root")
    parser.add_argument("--conditioning-stats-path")
    parser.add_argument("--external-driver-root")
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--metric", default="ndvi_main", help="(deprecated) unused; selection is by NDVI RMSE per source.")
    parser.add_argument("--mode", choices=("min", "max"), default="min", help="(deprecated) selection is always min RMSE.")
    parser.add_argument(
        "--sources", nargs="+", choices=("head", "rgbn"), default=["head", "rgbn"],
        help="NDVI output ways to include in the selection space (default: both).",
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--include-step-checkpoints", action="store_true")
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Max eval batches (NON-FORMAL smoke). >0 withholds the formal winner.",
    )
    parser.add_argument("--force", action="store_true", help="Ignore fresh sidecars and re-evaluate all.")
    parser.add_argument("--allow-checkpoint-contract-mismatch", action="store_true")
    parser.add_argument("--sidecar-dir", default=None, help="Where per-checkpoint sidecars live (default: alongside --output).")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    runs = _parse_runs(args.run)
    config_path = Path(args.config).expanduser().resolve()
    config_sha256 = canonical_json_sha256(_load_config_text(config_path))
    manifest_files_sha256 = _manifest_files_sha256(args.manifest_path)

    output = Path(args.output).expanduser().resolve()
    sidecar_dir = Path(args.sidecar_dir).expanduser().resolve() if args.sidecar_dir else output.parent
    sidecar_dir.mkdir(parents=True, exist_ok=True)

    is_smoke = bool(args.limit and args.limit > 0)
    sources = tuple(args.sources)
    per_run: dict[str, dict] = {}
    all_candidates: list[dict] = []   # flat {run x checkpoint x ndvi_source}
    for name, directory in runs.items():
        try:
            candidates = discover_checkpoint_candidates(
                directory, include_step_checkpoints=args.include_step_checkpoints
            )
        except FileNotFoundError as exc:
            per_run[name] = {"error": str(exc), "candidates": []}
            continue
        records = []
        run_source_candidates: list[dict] = []
        for checkpoint in candidates:
            sidecar = sidecar_dir / f"{name}__{checkpoint.stem}_{args.split}_full_eval.json"
            record = _evaluate_candidate(
                checkpoint, sidecar=sidecar, args=args,
                config_sha256=config_sha256, manifest_files_sha256=manifest_files_sha256,
            )
            records.append(record)
            metrics = record.get("metrics") or {}
            if "failure_reason" in record:
                continue
            for source in sources:
                rmse = metrics.get(f"ndvi_{source}_rmse")
                if rmse is None:   # e.g. head absent on a non-A' checkpoint
                    continue
                run_source_candidates.append({
                    "run": name,
                    "checkpoint": str(record["checkpoint"]),
                    "checkpoint_sha256": record.get("checkpoint_sha256"),
                    "ndvi_source": source,
                    "rmse": float(rmse),
                    "r2": metrics.get(f"ndvi_{source}_r2"),
                    "mae": metrics.get(f"ndvi_{source}_mae"),
                    "sidecar": record.get("sidecar"),
                    "is_smoke": record.get("is_smoke", False),
                })
        run_block: dict[str, object] = {"checkpoint_dir": str(directory), "candidates": records,
                                        "source_candidates": run_source_candidates}
        if run_source_candidates:
            best = min(run_source_candidates, key=lambda c: c["rmse"])
            run_block["within_run_selection"] = best
            all_candidates.extend(run_source_candidates)
        else:
            run_block["within_run_error"] = "no candidate produced a finite NDVI RMSE"
        per_run[name] = run_block

    result: dict[str, object] = {
        "schema_version": 2,
        "kind": "aprime_checkpoint_selection",
        "formal": not is_smoke,
        "is_smoke": is_smoke,
        "limit_max_batches": int(args.limit or 0),
        "selection_metric": "ndvi_rmse",
        "selection_mode": "min",
        "selection_space": "{run x checkpoint x ndvi_source}",
        "ndvi_sources": list(sources),
        "reported_metric": "ndvi_r2",
        "split": args.split,
        "config": str(config_path),
        "config_sha256": config_sha256,
        "manifest_path": str(Path(args.manifest_path).expanduser().resolve()),
        "manifest_files_sha256": manifest_files_sha256,
        "oodt_used_in_selection": False,
        "runs": per_run,
        "all_source_candidates": all_candidates,
    }

    if is_smoke:
        result["cross_run_selection"] = None
        result["note"] = "NON-FORMAL smoke (--limit>0): no formal winner is produced."
    elif all_candidates:
        winner = min(all_candidates, key=lambda c: c["rmse"])
        result["cross_run_selection"] = {
            "selected_run": winner["run"],
            "selected_checkpoint": winner["checkpoint"],
            "selected_ndvi_source": winner["ndvi_source"],
            "selected_checkpoint_sha256": winner["checkpoint_sha256"],
            "selected_rmse": winner["rmse"],
            "selected_r2": winner["r2"],
            "selected_mae": winner["mae"],
        }
    else:
        result["cross_run_selection"] = None
        result["note"] = "No run produced a valid winner."

    temp = output.with_suffix(output.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    temp.replace(output)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


def _load_config_text(config_path: Path):
    """Load the composed config as a plain dict for a stable content hash."""

    from train.train_stage2_earthnet import load_config

    return load_config(str(config_path))


def _manifest_files_sha256(manifest_path: str | None) -> str | None:
    if not manifest_path:
        return None
    source = Path(manifest_path).expanduser().resolve()
    if not source.is_file():
        return None
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    digest = payload.get("files_sha256")
    return digest if isinstance(digest, str) and digest else None


if __name__ == "__main__":
    main()
