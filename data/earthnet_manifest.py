"""Deterministic manifests for the EarthNet2021x NetCDF release.

The manifest is deliberately relocatable: file paths are relative to the
``earthnet2021x`` dataset root and the manifest digest does not include a
machine-specific absolute path.  Formal Stage2 runs can therefore prove which
files were used without falling back to an unconstrained recursive glob.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


MANIFEST_SCHEMA_VERSION = 2
DATASET_ID = "earthnet2021x"
PROTOCOL_ID = "earthnet2021_standard_v1"

# This repository uses the EarthNet2021 evaluation family over the available
# EarthNet2021x NetCDF release. The five directories below are therefore
# first-class physical/experimental splits. Do not infer a finer temporal or
# spatial OOD track from a directory name: such a track requires a separately
# supplied, verified file list rather than a fallback glob.
SPLIT_CANDIDATES: Mapping[str, Sequence[str]] = {
    "train": ("train",),
    "iid": ("iid",),
    "ood": ("ood",),
    "extreme": ("extreme",),
    "seasonal": ("seasonal",),
}

# ``split`` may be an implementation-level name such as ``train-dev``; role
# is the loader-facing semantic and must remain within this fixed protocol.
VALID_MANIFEST_ROLES = frozenset({"train", "val", *SPLIT_CANDIDATES})


def resolve_dataset_root(root: str | Path) -> Path:
    """Resolve either the parent directory or ``earthnet2021x`` itself."""

    path = Path(root).expanduser().resolve()
    if path.name.lower() == "earthnet2021x":
        return path
    nested = path / "earthnet2021x"
    return nested if nested.is_dir() else path


def discover_split_files(
    root: str | Path,
    split: str,
    *,
    pattern: str = "**/*.nc",
) -> list[Path]:
    """Discover one explicit split/track without scanning the dataset root."""

    dataset_root = resolve_dataset_root(root)
    if split not in SPLIT_CANDIDATES:
        raise ValueError(
            f"Unknown EarthNet split {split!r}; expected one of "
            f"{sorted(SPLIT_CANDIDATES)}"
        )
    candidates = [
        dataset_root / relative
        for relative in SPLIT_CANDIDATES[split]
        if (dataset_root / relative).is_dir()
    ]
    if not candidates:
        return []

    # Each supported split maps to exactly one physical directory.  There is
    # deliberately no root-level fallback and no guessed semantic sub-track.
    selected = candidates[0]
    return sorted(path.resolve() for path in selected.glob(pattern) if path.is_file())


def build_manifest(
    root: str | Path,
    split: str,
    *,
    hash_mode: str = "none",
    pattern: str = "**/*.nc",
) -> dict[str, Any]:
    """Build a deterministic JSON-serializable manifest."""

    dataset_root = resolve_dataset_root(root)
    files = discover_split_files(dataset_root, split, pattern=pattern)
    return build_manifest_from_paths(
        dataset_root,
        split,
        files,
        hash_mode=hash_mode,
        role=split,
        source_splits=(split,),
    )


def build_manifest_from_paths(
    root: str | Path,
    split: str,
    files: Iterable[Path],
    *,
    hash_mode: str = "none",
    role: str | None = None,
    source_splits: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze an explicit subset of EarthNet2021x files.

    ``split`` names the immutable experimental list (for example
    ``"train-dev"``), while ``role`` states the loader-facing purpose
    (``"train"`` or ``"val"``). ``source_splits`` preserves the physical
    origin. This makes a development holdout auditable without presenting it
    as an official test split.
    """

    if hash_mode not in {"none", "sha256"}:
        raise ValueError("hash_mode must be 'none' or 'sha256'")
    dataset_root = resolve_dataset_root(root)
    records = []
    seen_paths: set[str] = set()
    for path in files:
        path = Path(path).resolve()
        if path != dataset_root and dataset_root not in path.parents:
            raise ValueError(f"Manifest file escapes dataset root: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Manifest file does not exist: {path}")
        relative = path.relative_to(dataset_root).as_posix()
        if relative in seen_paths:
            raise ValueError(f"Duplicate manifest file path: {relative}")
        seen_paths.add(relative)
        record: dict[str, Any] = {
            "path": relative,
            "size_bytes": int(path.stat().st_size),
            "sample_id": path.stem,
        }
        if hash_mode == "sha256":
            record["sha256"] = sha256_file(path)
        records.append(record)
    records.sort(key=lambda item: item["path"])
    resolved_role = str(role or split)
    if resolved_role not in VALID_MANIFEST_ROLES:
        raise ValueError(
            f"Unsupported EarthNet2021 manifest role {resolved_role!r}; expected one of "
            f"{sorted(VALID_MANIFEST_ROLES)}"
        )
    resolved_sources = tuple(source_splits or (split,))
    unknown_sources = sorted(set(resolved_sources).difference(SPLIT_CANDIDATES))
    if unknown_sources:
        raise ValueError(
            "Unsupported EarthNet2021 source_splits: "
            f"{unknown_sources}; expected a subset of {sorted(SPLIT_CANDIDATES)}"
        )
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset": DATASET_ID,
        "protocol": PROTOCOL_ID,
        "split": split,
        "role": resolved_role,
        "source_splits": list(resolved_sources),
        "hash_mode": hash_mode,
        "num_files": len(records),
        "files": records,
        "files_sha256": records_digest(records),
    }
    if metadata:
        overlap = set(manifest).intersection(metadata)
        if overlap:
            raise ValueError(
                "Manifest metadata cannot overwrite reserved keys: "
                f"{sorted(overlap)}"
            )
        manifest.update(dict(metadata))
    return manifest


def write_manifest(manifest: Mapping[str, Any], path: str | Path) -> Path:
    """Atomically persist a manifest so readers never see half JSON."""

    return write_json_atomic(dict(manifest), path)


def write_json_atomic(payload: Mapping[str, Any], path: str | Path) -> Path:
    """Persist a JSON sidecar through fsync plus atomic replacement.

    Dataset manifests are later treated as immutable experiment evidence.  A
    plain ``write_text`` can leave a truncated file if a NAS job is cancelled
    mid-write, so every standalone manifest/sidecar writer shares this small
    dependency-free primitive instead.
    """

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(dict(payload), handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
        _fsync_directory(output.parent)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output


def _fsync_directory(path: Path) -> None:
    """Best-effort directory fsync; network filesystems may not support it."""

    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def load_manifest_files(
    manifest_path: str | Path,
    dataset_root: str | Path,
    *,
    expected_split: str | None = None,
    expected_protocol: str = PROTOCOL_ID,
    verify_exists: bool = True,
    verify_sizes: bool = False,
    verify_hashes: bool = False,
) -> list[Path]:
    """Load and validate an immutable file list."""

    source = Path(manifest_path)
    with source.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if int(manifest.get("schema_version", -1)) != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported manifest schema in {source}: "
            f"{manifest.get('schema_version')!r}"
        )
    if manifest.get("dataset") != DATASET_ID:
        raise ValueError(
            f"Unexpected dataset in {source}: {manifest.get('dataset')!r}"
        )
    if manifest.get("protocol") != expected_protocol:
        raise ValueError(
            f"Unexpected manifest protocol in {source}: "
            f"expected={expected_protocol!r}, got={manifest.get('protocol')!r}"
        )
    declared_split = str(manifest.get("split", ""))
    declared_role = str(manifest.get("role", declared_split))
    if declared_role not in VALID_MANIFEST_ROLES:
        raise ValueError(
            f"Unsupported manifest role in {source}: {declared_role!r}; expected one of "
            f"{sorted(VALID_MANIFEST_ROLES)}"
        )
    if expected_split and declared_role != expected_split:
        raise ValueError(
            f"Manifest role={declared_role!r} (split={declared_split!r}) does not "
            f"match requested split={expected_split!r}"
        )

    records = manifest.get("files")
    if not isinstance(records, list):
        raise TypeError(f"Manifest {source} has no list-valued 'files' field")
    if int(manifest.get("num_files", -1)) != len(records):
        raise ValueError(f"Manifest {source} num_files does not match its records")
    if manifest.get("files_sha256") != records_digest(records):
        raise ValueError(f"Manifest {source} record digest is invalid")

    root = resolve_dataset_root(dataset_root)
    paths: list[Path] = []
    seen: set[str] = set()
    for record in records:
        relative_text = str(record.get("path", ""))
        relative = Path(relative_text)
        if not relative_text or relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe manifest path in {source}: {relative_text!r}")
        if relative_text in seen:
            raise ValueError(f"Duplicate manifest path in {source}: {relative_text}")
        seen.add(relative_text)
        path = (root / relative).resolve()
        if path != root and root not in path.parents:
            raise ValueError(f"Manifest path escapes dataset root: {relative_text}")
        if verify_exists and not path.is_file():
            raise FileNotFoundError(f"Manifest file is missing: {path}")
        if verify_sizes and path.is_file():
            expected_size = int(record.get("size_bytes", -1))
            if path.stat().st_size != expected_size:
                raise ValueError(
                    f"Manifest size mismatch for {path}: "
                    f"expected={expected_size}, actual={path.stat().st_size}"
                )
        if verify_hashes:
            expected_hash = record.get("sha256")
            if not expected_hash:
                raise ValueError(
                    f"Manifest {source} has no sha256 for {relative_text}"
                )
            if sha256_file(path) != expected_hash:
                raise ValueError(f"Manifest checksum mismatch for {path}")
        paths.append(path)

    if [record["path"] for record in records] != sorted(seen):
        raise ValueError(f"Manifest {source} records are not path-sorted")
    return paths


def records_digest(records: Iterable[Mapping[str, Any]]) -> str:
    canonical = json.dumps(
        list(records),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def sha256_file(path: str | Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
