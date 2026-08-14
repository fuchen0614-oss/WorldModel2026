#!/usr/bin/env python3
"""Build a safe, deduplicated NUL-delimited Stage2 local-staging file list.

``LOCAL_STAGE_DATA_SCOPE=train_val`` stages exactly the union of the frozen
train and validation manifests rather than inferring files through a directory
glob.  The resulting paths are relative to the ``earthnet2021x`` dataset root
and are ready for ``rsync --from0 --files-from``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.earthnet_manifest import load_manifest_files, resolve_dataset_root


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--train-manifest", required=True)
    parser.add_argument("--validation-manifest", required=True)
    parser.add_argument("--output", required=True, help="NUL-delimited relative file list")
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    dataset_root = resolve_dataset_root(args.dataset_root)
    train_manifest = Path(args.train_manifest)
    validation_manifest = Path(args.validation_manifest)
    train_paths = load_manifest_files(
        train_manifest,
        dataset_root,
        expected_split="train",
        verify_exists=False,
    )
    validation_paths = load_manifest_files(
        validation_manifest,
        dataset_root,
        expected_split="val",
        verify_exists=False,
    )

    relative_paths: set[str] = set()
    for path in [*train_paths, *validation_paths]:
        relative = Path(path).relative_to(dataset_root).as_posix()
        if not relative.endswith(".nc"):
            raise ValueError(f"Stage2 manifest record is not a NetCDF cube: {relative}")
        relative_paths.add(relative)

    ordered_paths = sorted(relative_paths)
    if not ordered_paths:
        raise ValueError("train+validation manifests contain no NetCDF files")
    payload = "".join(f"{relative}\0" for relative in ordered_paths).encode("utf-8")
    output = Path(args.output)
    _write_atomic(output, payload)

    summary = {
        "schema": "obsworld-stage2-local-stage-file-list-v1",
        "dataset_root": str(dataset_root),
        "train_manifest": str(train_manifest),
        "validation_manifest": str(validation_manifest),
        "train_manifest_sha256": _sha256_file(train_manifest),
        "validation_manifest_sha256": _sha256_file(validation_manifest),
        "num_files": len(ordered_paths),
        "file_list_sha256": hashlib.sha256(payload).hexdigest(),
    }
    summary_payload = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _write_atomic(Path(args.summary), summary_payload)
    print(json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
