#!/usr/bin/env python
"""Score prediction NetCDFs with the official GreenEarthNet protocol."""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import load_manifest_files  # noqa: E402
from eval.greenearthnet_protocol import (  # noqa: E402
    OFFICIAL_EVALUATOR_COMMIT,
    PREDICTION_GRID_FIVE_DAILY_20,
    VALID_PREDICTION_GRIDS,
    score_cube_paths,
    summarize_score_parquets,
)


def _score_pair(pair: tuple[str, str, str]) -> pd.DataFrame:
    return score_cube_paths(pair[0], pair[1], prediction_grid=pair[2])


def _target_files(args: argparse.Namespace) -> list[Path]:
    if args.manifest:
        if not args.dataset_root:
            raise ValueError("--dataset-root is required together with --manifest")
        return load_manifest_files(
            args.manifest,
            args.dataset_root,
            expected_split=args.split,
            verify_exists=True,
            verify_sizes=args.verify_manifest_sizes,
        )
    if not args.allow_discovery:
        raise ValueError(
            "Formal evaluation requires --manifest and --dataset-root. "
            "Use --allow-discovery only for local smoke tests."
        )
    return sorted(Path(args.target_dir).glob("**/*.nc"))


def _prediction_path(prediction_root: Path, target: Path) -> Path:
    return prediction_root / target.parent.name / target.name


def score_directory(
    targets: list[Path],
    prediction_dir: Path,
    score_dir: Path,
    *,
    workers: int,
    prediction_grid: str = PREDICTION_GRID_FIVE_DAILY_20,
) -> dict[str, object]:
    if not targets:
        raise ValueError("No target NetCDF files were selected")
    if prediction_grid not in VALID_PREDICTION_GRIDS:
        raise ValueError(
            f"Unsupported prediction grid {prediction_grid!r}; "
            f"expected one of {sorted(VALID_PREDICTION_GRIDS)}"
        )
    pairs = [(path, _prediction_path(prediction_dir, path)) for path in targets]
    missing = [str(prediction) for _, prediction in pairs if not prediction.is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing {len(missing)} prediction files; first entries: {missing[:10]}"
        )

    score_dir.mkdir(parents=True, exist_ok=True)
    pairs_by_region: dict[str, list[tuple[str, str, str]]] = {}
    for target, prediction in pairs:
        pairs_by_region.setdefault(target.parent.name, []).append(
            (str(target), str(prediction), prediction_grid)
        )
    eligible_pixels = 0
    output_paths = []
    pool = ProcessPoolExecutor(max_workers=workers) if workers != 1 else None
    try:
        for region in sorted(pairs_by_region):
            serialized = pairs_by_region[region]
            iterator = (
                map(_score_pair, serialized)
                if pool is None
                else pool.map(_score_pair, serialized)
            )
            frame = pd.concat(list(iterator), ignore_index=True)
            eligible_pixels += len(frame)
            output_path = score_dir / f"scores_en21x_{region}.parquet"
            frame.to_parquet(
                output_path,
                compression="snappy",
                index=False,
            )
            output_paths.append(str(output_path))
    finally:
        if pool is not None:
            pool.shutdown()
    return {
        "num_eligible_pixels": eligible_pixels,
        "score_parquets": output_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--prediction-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--dataset-root")
    parser.add_argument("--split", default="ood-t")
    parser.add_argument("--verify-manifest-sizes", action="store_true")
    parser.add_argument("--allow-discovery", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--prediction-grid",
        default=PREDICTION_GRID_FIVE_DAILY_20,
        choices=sorted(VALID_PREDICTION_GRIDS),
        help="Declared public target-time grid used by the prediction tree.",
    )
    parser.add_argument(
        "--comparison-score-dir",
        help="Parquet score directory for climatology/previous-year outperformance.",
    )
    args = parser.parse_args()

    if args.workers == 0 or args.workers < -1:
        raise ValueError("--workers must be -1 or a positive integer")
    workers = max(1, os.cpu_count() or 1) if args.workers == -1 else args.workers
    targets = _target_files(args)
    score_dir = Path(args.output_dir)
    score_summary = score_directory(
        targets,
        Path(args.prediction_dir),
        score_dir,
        workers=workers,
        prediction_grid=args.prediction_grid,
    )

    metrics = summarize_score_parquets(score_dir, args.comparison_score_dir)
    result = {
        "protocol": "GreenEarthNet CVPR 2024",
        "official_evaluator_commit": OFFICIAL_EVALUATOR_COMMIT,
        "prediction_grid": args.prediction_grid,
        "num_target_files": len(targets),
        "num_eligible_pixels": score_summary["num_eligible_pixels"],
        "metrics": metrics,
    }
    output = score_dir / "metrics_en21x.json"
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=True) + "\n",
        encoding="utf-8",
    )
    pd.DataFrame.from_dict(metrics, orient="index", columns=["value"]).to_csv(
        score_dir / "metrics_en21x.csv"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
