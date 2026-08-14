#!/usr/bin/env python
"""Read-only preflight for the formal GreenEarthNet OOD-t Table 1 path.

The preflight deliberately checks the *frozen chopped manifest* rather than a
recursive data root.  It validates a few evenly selected target minicubes
against both the Stage2 150-day input contract and the public evaluator's
explicit output grids: the learned/Persistence 20-step five-daily grid and
Climatology's daily day-50-plus grid.  It never trains, exports predictions,
or removes cached data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (  # noqa: E402
    GREENEARTHNET_CHOPPED_PROTOCOL_ID,
    load_manifest_files,
    manifest_protocol_spec,
    resolve_manifest_root,
    write_json_atomic,
)
from eval.earthnet_table1 import raw_cube_from_netcdf, source_manifest_identity  # noqa: E402
from eval.generate_baseline_predictions import _full_cube_path  # noqa: E402
from eval.greenearthnet_protocol import (  # noqa: E402
    PREDICTION_GRID_CLIMATOLOGY_DAILY,
    PREDICTION_GRID_FIVE_DAILY_20,
    PREDICTION_VARIABLE,
    expected_climatology_prediction_times,
    expected_prediction_times,
    validate_prediction_dataset,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only formal GreenEarthNet chopped-track Table 1 preflight."
    )
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--manifest-protocol",
        default=GREENEARTHNET_CHOPPED_PROTOCOL_ID,
        help="Formal Table 1 requires greenearthnet_cvpr2024_chopped_v1.",
    )
    parser.add_argument("--split", default="ood-t_chopped")
    parser.add_argument("--sample-count", type=int, default=3)
    parser.add_argument("--full-cube-root")
    parser.add_argument("--verify-manifest-sizes", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 if the selected files fail the Stage2/evaluator contract.",
    )
    return parser.parse_args()


def _choose_evenly(paths: list[Path], count: int) -> list[Path]:
    if count <= 0:
        raise ValueError("--sample-count must be positive")
    if len(paths) <= count:
        return paths
    if count == 1:
        return [paths[0]]
    indices = {
        round(index * (len(paths) - 1) / (count - 1))
        for index in range(count)
    }
    return [paths[index] for index in sorted(indices)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(8 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _inspect_target(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "ok": False,
    }
    try:
        # Validate the same raw input slice used by Stage2 (indices 4..149).
        raw = raw_cube_from_netcdf(path)
        with xr.open_dataset(path, decode_times=True, cache=False) as target:
            five_daily_times = expected_prediction_times(target)
            climatology_times = expected_climatology_prediction_times(target)

            def synthetic_prediction(times: xr.DataArray) -> xr.Dataset:
                return xr.Dataset(
                    {
                        PREDICTION_VARIABLE: xr.DataArray(
                            np.zeros(
                                (
                                    int(times.size),
                                    int(target.sizes["lat"]),
                                    int(target.sizes["lon"]),
                                ),
                                dtype=np.float32,
                            ),
                            coords={"time": times, "lat": target.lat, "lon": target.lon},
                            dims=("time", "lat", "lon"),
                        )
                    }
                )

            validate_prediction_dataset(
                target,
                synthetic_prediction(five_daily_times),
                prediction_grid=PREDICTION_GRID_FIVE_DAILY_20,
            )
            validate_prediction_dataset(
                target,
                synthetic_prediction(climatology_times),
                prediction_grid=PREDICTION_GRID_CLIMATOLOGY_DAILY,
            )
            result.update(
                {
                    "ok": True,
                    "sizes": {key: int(value) for key, value in target.sizes.items()},
                    "stage2_sampled_rgbn_shape": list(raw.rgbn.shape),
                    "stage2_context_steps": int(raw.context_rgbn.shape[0]),
                    "stage2_target_steps": int(raw.future_rgbn.shape[0]),
                    "official_five_daily_prediction_steps": int(five_daily_times.size),
                    "official_five_daily_first_prediction_time": str(five_daily_times.values[0]),
                    "official_five_daily_last_prediction_time": str(five_daily_times.values[-1]),
                    "official_climatology_prediction_steps": int(climatology_times.size),
                    "official_climatology_first_prediction_time": str(climatology_times.values[0]),
                    "official_climatology_last_prediction_time": str(climatology_times.values[-1]),
                }
            )
    except Exception as exc:  # Keep the report actionable on a mismatched release.
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _inspect_full_cube(full_root: Path, target_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"target": str(target_path), "ok": False}
    try:
        full_path = _full_cube_path(full_root, target_path)
        with xr.open_dataset(full_path, decode_times=True, cache=False) as cube:
            if int(cube.sizes.get("time", 0)) <= 0:
                raise ValueError("full minicube has no positive time dimension")
            result.update(
                {
                    "ok": True,
                    "path": str(full_path),
                    "size_bytes": int(full_path.stat().st_size),
                    "sha256": _sha256(full_path),
                    "sizes": {key: int(value) for key, value in cube.sizes.items()},
                }
            )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _all_ok(records: Iterable[dict[str, Any]]) -> bool:
    materialized = list(records)
    return bool(materialized) and all(record.get("ok") is True for record in materialized)


def main() -> int:
    args = parse_args()
    manifest_protocol_spec(args.manifest_protocol)
    if args.manifest_protocol != GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        raise ValueError("Formal OOD-t Table 1 preflight only accepts the chopped protocol")
    if args.split != "ood-t_chopped":
        raise ValueError("Formal Table 1 main-track preflight requires --split ood-t_chopped")

    dataset_root = resolve_manifest_root(args.dataset_root, protocol=args.manifest_protocol)
    sources = load_manifest_files(
        args.manifest,
        dataset_root,
        expected_protocol=args.manifest_protocol,
        expected_split=args.split,
        verify_exists=True,
        verify_sizes=args.verify_manifest_sizes,
    )
    selected = _choose_evenly(sources, args.sample_count)
    target_checks = [_inspect_target(path) for path in selected]

    full_root = Path(args.full_cube_root).expanduser().resolve() if args.full_cube_root else None
    full_checks = (
        [_inspect_full_cube(full_root, path) for path in selected] if full_root is not None else []
    )
    report = {
        "kind": "greenearthnet_oodt_table1_preflight",
        "source_manifest": source_manifest_identity(args.manifest),
        "source_manifest_protocol": args.manifest_protocol,
        "evaluation_track": args.split,
        "dataset_root": str(dataset_root),
        "num_manifest_files": len(sources),
        "sample_count": len(selected),
        "target_checks": target_checks,
        "full_cube_root": str(full_root) if full_root is not None else None,
        "full_cube_checks": full_checks,
        "stage2_direct_export_ready": _all_ok(target_checks),
        "official_persistence_ready": _all_ok(target_checks),
        "official_climatology_ready": (
            _all_ok(target_checks) and _all_ok(full_checks) if full_root is not None else None
        ),
        "notes": [
            "This preflight is read-only and does not validate learned checkpoint weights.",
            "It checks both public timing contracts: 20 five-daily points for learned/Persistence and daily target times from positional index 50 for Climatology.",
            "A formal model row still requires a hash-verified export, strict score provenance, evaluator parity, and deterministic-baseline reference parity confirmation.",
        ],
    }
    output = write_json_atomic(report, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"preflight={output}")

    ready = bool(report["stage2_direct_export_ready"])
    if full_root is not None:
        ready = ready and bool(report["official_climatology_ready"])
    return 0 if (ready or not args.strict) else 2


if __name__ == "__main__":
    raise SystemExit(main())
