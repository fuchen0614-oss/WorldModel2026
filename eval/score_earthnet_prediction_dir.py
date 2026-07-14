#!/usr/bin/env python
"""Score an exported EarthNet2021 prediction directory with the official toolkit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.earthnet_standard_metrics import ensure_earthnet_ssim_compat


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prediction-dir", required=True)
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--workers", type=int, default=-1)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    try:
        import earthnet as en
        from earthnet.parallel_score import EarthNetScore
    except ImportError as exc:
        raise ImportError(
            "Install the official scorer first: pip install earthnet==0.3.9"
        ) from exc
    ensure_earthnet_ssim_compat(en)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    data_path = output / "individual_scores.json"
    ens_path = output / "earthnet_score.json"
    EarthNetScore.get_ENS(
        args.prediction_dir,
        args.target_dir,
        n_workers=args.workers,
        data_output_file=str(data_path),
        ens_output_file=str(ens_path),
    )
    with ens_path.open("r", encoding="utf-8") as handle:
        result = json.load(handle)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
