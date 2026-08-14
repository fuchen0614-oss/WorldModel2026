#!/usr/bin/env python
"""Create a deterministic, explicitly non-formal Stage2-v2 sanity bundle.

Long EarthNet runs should use the complete frozen ``train_dev`` manifest.  A
32/128-cube overfit run serves a different purpose: it checks real NetCDF
fields, gradients, checkpointing and export before GPU-hours are spent.  This
utility creates new manifests for that purpose instead of silently truncating
a full manifest with ``max_files``.

The output directory is immutable and is published only after both manifests
and their bundle metadata are complete.  It is intentionally a *new* artifact
whose provenance points back to the frozen development manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping, Sequence
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (  # noqa: E402
    build_manifest_from_paths,
    load_manifest_files,
    resolve_dataset_root,
    sha256_file,
    write_json_atomic,
    write_manifest,
)


SELECTOR_VERSION = "tile_round_robin_sha256_v1"


def _read_manifest(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Manifest must be a JSON object: {source}")
    return payload


def _tile_key(path: Path) -> str:
    sample_id = path.stem
    tile, separator, _ = sample_id.partition("_")
    if not separator or not tile:
        raise ValueError(
            "EarthNet sanity selection requires a '<tile>_<start>_...' sample id, "
            f"got {sample_id!r}"
        )
    return tile


def _stable_digest(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def select_tile_round_robin(
    paths: Sequence[Path],
    *,
    count: int,
    seed: int,
) -> list[Path]:
    """Select a deterministic spatially spread subset without RNG state.

    First rank tiles and each tile's files by SHA-256 of ``seed`` plus its
    identifier, then take one cube per tile in rounds.  This is not a new
    validation split and makes no generalization claim; it simply avoids an
    arbitrary sorted-file prefix being dominated by one Sentinel tile.
    """

    if count <= 0:
        raise ValueError(f"Sanity subset count must be positive, got {count}")
    if len(paths) < count:
        raise ValueError(
            f"Requested {count} sanity cubes but parent manifest has only {len(paths)}"
        )
    grouped: dict[str, list[Path]] = {}
    for path in paths:
        grouped.setdefault(_tile_key(path), []).append(path)
    tiles = sorted(grouped, key=lambda tile: _stable_digest(seed, f"tile:{tile}"))
    for tile in tiles:
        grouped[tile].sort(
            key=lambda path: _stable_digest(seed, f"cube:{path.stem}")
        )

    selected: list[Path] = []
    position = {tile: 0 for tile in tiles}
    while len(selected) < count:
        progressed = False
        for tile in tiles:
            index = position[tile]
            candidates = grouped[tile]
            if index >= len(candidates):
                continue
            selected.append(candidates[index])
            position[tile] = index + 1
            progressed = True
            if len(selected) == count:
                break
        if not progressed:
            raise AssertionError("Tile round-robin selection exhausted unexpectedly")
    return selected


def _new_staging_directory(output: Path) -> Path:
    if output.exists():
        raise FileExistsError(
            "Refusing to overwrite an existing sanity-bundle directory: "
            f"{output}. Choose a new output directory so the previous debug "
            "evidence remains inspectable."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(
        f".{output.name}.staging-{os.getpid()}-{uuid.uuid4().hex}"
    )
    staging.mkdir()
    return staging


def _publish_staging_directory(staging: Path, output: Path) -> None:
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


def _parent_metadata(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": str(path),
        "manifest_sha256": sha256_file(path),
        "files_sha256": payload.get("files_sha256"),
        "split": payload.get("split"),
        "role": payload.get("role"),
        "num_files": payload.get("num_files"),
    }


def _subset_manifest(
    *,
    dataset_root: Path,
    parent_path: Path,
    parent_payload: Mapping[str, Any],
    paths: Sequence[Path],
    role: str,
    count: int,
    seed: int,
    hash_mode: str,
) -> dict[str, Any]:
    selected = select_tile_round_robin(paths, count=count, seed=seed)
    source_splits = parent_payload.get("source_splits")
    if not isinstance(source_splits, list) or not source_splits:
        raise ValueError(f"Parent manifest has no valid source_splits: {parent_path}")
    return build_manifest_from_paths(
        dataset_root,
        f"{role}-sanity-{count}",
        selected,
        hash_mode=hash_mode,
        role=role,
        source_splits=tuple(str(value) for value in source_splits),
        metadata={
            "selection": {
                "kind": "sanity_subset_not_formal",
                "algorithm": SELECTOR_VERSION,
                "seed": int(seed),
                "requested_count": int(count),
                "parent_manifest": _parent_metadata(parent_path, parent_payload),
            }
        },
    )


def build_sanity_bundle(
    *,
    data_root: str | Path,
    train_manifest_path: str | Path,
    validation_manifest_path: str | Path,
    output_dir: str | Path,
    train_count: int = 32,
    validation_count: int = 32,
    seed: int = 20260716,
    hash_mode: str = "none",
) -> dict[str, Any]:
    """Build and atomically publish train/validation sanity manifests."""

    dataset_root = resolve_dataset_root(data_root)
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"EarthNet2021x data root does not exist: {dataset_root}")
    train_parent = Path(train_manifest_path).expanduser().resolve()
    validation_parent = Path(validation_manifest_path).expanduser().resolve()
    train_payload = _read_manifest(train_parent)
    validation_payload = _read_manifest(validation_parent)
    train_paths = load_manifest_files(train_parent, dataset_root, expected_split="train")
    validation_paths = load_manifest_files(
        validation_parent,
        dataset_root,
        expected_split="val",
    )
    output = Path(output_dir).expanduser().resolve()
    staging = _new_staging_directory(output)
    try:
        train_manifest = _subset_manifest(
            dataset_root=dataset_root,
            parent_path=train_parent,
            parent_payload=train_payload,
            paths=train_paths,
            role="train",
            count=train_count,
            seed=seed,
            hash_mode=hash_mode,
        )
        validation_manifest = _subset_manifest(
            dataset_root=dataset_root,
            parent_path=validation_parent,
            parent_payload=validation_payload,
            paths=validation_paths,
            role="val",
            count=validation_count,
            seed=seed,
            hash_mode=hash_mode,
        )
        train_output = write_manifest(train_manifest, staging / "train_sanity.json")
        validation_output = write_manifest(
            validation_manifest,
            staging / "val_sanity.json",
        )
        bundle = {
            "schema_version": 1,
            "kind": "stage2_earthnet2021x_sanity_bundle",
            "formal_result_eligible": False,
            "selector": SELECTOR_VERSION,
            "dataset_root_name": dataset_root.name,
            "seed": int(seed),
            "hash_mode": hash_mode,
            "rules": [
                "This bundle is for real-data overfit/sanity checks only.",
                "Do not report its metrics as a main, validation, IID or OOD result.",
                "Build conditioning statistics from train_sanity.json if training with it.",
                "Use the original frozen train_dev/val_dev manifests for model selection.",
            ],
            "parents": {
                "train": _parent_metadata(train_parent, train_payload),
                "val": _parent_metadata(validation_parent, validation_payload),
            },
            "manifests": {
                "train": {
                    "filename": train_output.name,
                    "num_files": train_manifest["num_files"],
                    "files_sha256": train_manifest["files_sha256"],
                },
                "val": {
                    "filename": validation_output.name,
                    "num_files": validation_manifest["num_files"],
                    "files_sha256": validation_manifest["files_sha256"],
                },
            },
        }
        write_json_atomic(bundle, staging / "bundle.json")
        _publish_staging_directory(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "output_dir": str(output),
        "bundle_path": str(output / "bundle.json"),
        "train_manifest_path": str(output / "train_sanity.json"),
        "validation_manifest_path": str(output / "val_sanity.json"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an explicitly non-formal real-data Stage2 sanity bundle."
    )
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--train-manifest", required=True)
    parser.add_argument("--validation-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--train-count", type=int, default=32)
    parser.add_argument("--validation-count", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20260716)
    parser.add_argument("--hash-mode", choices=("none", "sha256"), default="none")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_sanity_bundle(
        data_root=args.data_root,
        train_manifest_path=args.train_manifest,
        validation_manifest_path=args.validation_manifest,
        output_dir=args.output_dir,
        train_count=args.train_count,
        validation_count=args.validation_count,
        seed=args.seed,
        hash_mode=args.hash_mode,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
