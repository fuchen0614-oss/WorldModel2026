#!/usr/bin/env python
"""Freeze the available EarthNet2021x release into a formal experiment protocol.

The server data is used under the EarthNet2021 split family:
``train``, ``iid``, ``ood``, ``extreme``, and ``seasonal``.  This utility is
metadata-only: it reads paths, file sizes, and dates encoded in file names; it
does not open NetCDF arrays and never downloads data.  It creates immutable
JSON manifests plus a deterministic train-only development holdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (  # noqa: E402
    DATASET_ID,
    PROTOCOL_ID,
    SPLIT_CANDIDATES,
    build_manifest,
    build_manifest_from_paths,
    discover_split_files,
    resolve_dataset_root,
    write_manifest,
    write_json_atomic,
)


PHYSICAL_SPLITS = ("train", "iid", "ood", "extreme", "seasonal")
SAMPLE_ID_RE = re.compile(
    r"^(?P<tile>[^_]+)_(?P<start>\d{4}-\d{2}-\d{2})_"
    r"(?P<end>\d{4}-\d{2}-\d{2})_"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Freeze EarthNet2021x train/IID/OOD/Extreme/Seasonal manifests "
            "and a deterministic train-only development validation holdout."
        )
    )
    parser.add_argument(
        "--root",
        required=True,
        help="EarthNet2021 parent directory or the earthnet2021x directory itself.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--val-tile-count",
        type=int,
        default=8,
        help="Number of train Sentinel-2 tiles reserved for development validation.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260716,
        help="Stable seed used only for deterministic tile selection.",
    )
    parser.add_argument(
        "--hash-mode",
        choices=("none", "sha256"),
        default="none",
        help="sha256 is strongest but slow on network storage; none records file sizes.",
    )
    return parser.parse_args()


def _sample_metadata(sample_id: str) -> tuple[str, str, str]:
    match = SAMPLE_ID_RE.match(sample_id)
    if match is None:
        raise ValueError(
            "EarthNet2021x sample id does not encode tile/start/end dates: "
            f"{sample_id!r}"
        )
    return match.group("tile"), match.group("start"), match.group("end")


def summarize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return inventory evidence without reading NetCDF contents."""

    tiles: set[str] = set()
    starts: list[str] = []
    ends: list[str] = []
    for record in manifest["files"]:
        tile, start, end = _sample_metadata(str(record["sample_id"]))
        tiles.add(tile)
        starts.append(start)
        ends.append(end)
    if not starts:
        raise ValueError(f"Manifest {manifest['split']!r} contains zero files")
    return {
        "num_files": int(manifest["num_files"]),
        "num_tiles": len(tiles),
        "tiles": sorted(tiles),
        "start_date_min": min(starts),
        "start_date_max": max(starts),
        "end_date_min": min(ends),
        "end_date_max": max(ends),
        "files_sha256": manifest["files_sha256"],
    }


def select_validation_tiles(tiles: Iterable[str], *, count: int, seed: int) -> list[str]:
    """Select a stable tile-level holdout without Python hash randomization."""

    candidates = sorted(set(tiles))
    if count <= 0:
        raise ValueError("--val-tile-count must be positive")
    if len(candidates) <= count:
        raise ValueError(
            f"Need more train tiles than validation tiles, got {len(candidates)} and {count}"
        )

    def key(tile: str) -> str:
        return hashlib.sha256(f"{seed}:{tile}".encode("utf-8")).hexdigest()

    return sorted(sorted(candidates, key=key)[:count])


def _new_staging_directory(output: Path) -> Path:
    """Create an unpublished sibling directory for an immutable protocol run.

    A formal manifest set is a single evidence object, not seven unrelated
    JSON files.  Building it below a private sibling directory and renaming
    that directory only after every file is durable prevents a cancelled job
    from exposing a half-frozen protocol at the requested output path.
    """

    if output.exists():
        raise FileExistsError(
            "Refusing to overwrite an existing frozen-protocol directory: "
            f"{output}. Manifests are immutable evidence; choose a new output "
            "directory for a new freeze attempt."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(
        f".{output.name}.staging-{os.getpid()}-{uuid.uuid4().hex}"
    )
    staging.mkdir()
    return staging


def _publish_staging_directory(staging: Path, output: Path) -> None:
    """Atomically make a complete frozen protocol visible at ``output``."""

    if output.exists():
        raise FileExistsError(f"Refusing to replace existing output directory: {output}")
    os.replace(staging, output)
    try:
        descriptor = os.open(output.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def freeze_protocol(
    root: str | Path,
    output_dir: str | Path,
    *,
    val_tile_count: int = 8,
    seed: int = 20260716,
    hash_mode: str = "none",
) -> dict[str, Any]:
    """Create all EarthNet2021x-standard manifests and provenance metadata."""

    dataset_root = resolve_dataset_root(root)
    output = Path(output_dir).expanduser().resolve()
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"EarthNet2021x root does not exist: {dataset_root}")

    staging = _new_staging_directory(output)
    try:
        return _freeze_protocol_into_staging(
            dataset_root,
            staging,
            output,
            val_tile_count=val_tile_count,
            seed=seed,
            hash_mode=hash_mode,
        )
    except Exception:
        # Only the private, unpublished staging directory is removed.  The
        # requested output either does not exist or is a pre-existing immutable
        # run which we refused to touch above.
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _freeze_protocol_into_staging(
    dataset_root: Path,
    staging: Path,
    output: Path,
    *,
    val_tile_count: int,
    seed: int,
    hash_mode: str,
) -> dict[str, Any]:
    """Build every artifact privately, then publish it as one directory."""

    physical = {
        split: build_manifest(dataset_root, split, hash_mode=hash_mode)
        for split in PHYSICAL_SPLITS
    }
    inventory = {split: summarize_manifest(manifest) for split, manifest in physical.items()}

    train_files = discover_split_files(dataset_root, "train")
    train_tiles = inventory["train"]["tiles"]
    val_tiles = select_validation_tiles(train_tiles, count=val_tile_count, seed=seed)
    val_tile_set = set(val_tiles)
    dev_train_files = [
        path for path in train_files if _sample_metadata(path.stem)[0] not in val_tile_set
    ]
    dev_val_files = [
        path for path in train_files if _sample_metadata(path.stem)[0] in val_tile_set
    ]
    if not dev_train_files or not dev_val_files:
        raise AssertionError("Deterministic train/validation tile split produced an empty list")

    manifests: dict[str, dict[str, Any]] = {
        "train_all": build_manifest_from_paths(
            dataset_root,
            "train-all",
            train_files,
            hash_mode=hash_mode,
            role="train",
            source_splits=("train",),
            metadata={"selection": {"kind": "all_train_tiles"}},
        ),
        "train_dev": build_manifest_from_paths(
            dataset_root,
            "train-dev",
            dev_train_files,
            hash_mode=hash_mode,
            role="train",
            source_splits=("train",),
            metadata={
                "selection": {
                    "kind": "tile_holdout_complement",
                    "seed": seed,
                    "held_out_tiles": val_tiles,
                }
            },
        ),
        "val_dev": build_manifest_from_paths(
            dataset_root,
            "val-dev",
            dev_val_files,
            hash_mode=hash_mode,
            role="val",
            source_splits=("train",),
            metadata={
                "selection": {
                    "kind": "tile_holdout",
                    "seed": seed,
                    "held_out_tiles": val_tiles,
                }
            },
        ),
        "iid": physical["iid"],
        "ood": physical["ood"],
        "extreme": physical["extreme"],
        "seasonal": physical["seasonal"],
    }

    manifest_paths: dict[str, str] = {}
    for name, manifest in manifests.items():
        path = write_manifest(manifest, staging / f"{name}.json")
        # Returned paths describe the published directory, never the private
        # staging location which disappears after the final rename.
        manifest_paths[name] = str(output / path.name)

    protocol = {
        "schema_version": 1,
        "dataset": DATASET_ID,
        "protocol": PROTOCOL_ID,
        "dataset_root_name": dataset_root.name,
        "hash_mode": hash_mode,
        "physical_splits": list(PHYSICAL_SPLITS),
        "development": {
            "train_manifest": "train_dev.json",
            "validation_manifest": "val_dev.json",
            "validation_selection": "deterministic train-tile holdout",
            "validation_tile_count": len(val_tiles),
            "validation_tiles": val_tiles,
            "seed": seed,
        },
        "final_training": {"train_manifest": "train_all.json"},
        "primary_test_tracks": ["iid", "ood"],
        "supplementary_test_tracks": ["extreme", "seasonal"],
        "rules": [
            "Use val_dev only for checkpoint selection and hyperparameter decisions.",
            "Do not use iid, ood, extreme, or seasonal for model selection.",
            "After decisions are frozen, train_all may be used for a fixed-budget final retrain.",
            "Statistics must be fitted from the same role=train manifest used by the run.",
        ],
        "inventory": inventory,
        "manifest_files": {
            name: {
                "filename": Path(path).name,
                "split": manifest["split"],
                "role": manifest["role"],
                "num_files": manifest["num_files"],
                "files_sha256": manifest["files_sha256"],
            }
            for name, (path, manifest) in {
                name: (manifest_paths[name], manifest)
                for name, manifest in manifests.items()
            }.items()
        },
    }
    write_json_atomic(inventory, staging / "inventory.json")
    # ``protocol.json`` is deliberately written last: it is the human and
    # machine-readable declaration that the complete manifest set is ready.
    write_json_atomic(protocol, staging / "protocol.json")
    _publish_staging_directory(staging, output)
    return {
        "output_dir": str(output),
        "protocol_path": str(output / "protocol.json"),
        "inventory_path": str(output / "inventory.json"),
        "manifest_paths": manifest_paths,
        "validation_tiles": val_tiles,
    }


def main() -> int:
    args = parse_args()
    result = freeze_protocol(
        args.root,
        args.output_dir,
        val_tile_count=args.val_tile_count,
        seed=args.seed,
        hash_mode=args.hash_mode,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
