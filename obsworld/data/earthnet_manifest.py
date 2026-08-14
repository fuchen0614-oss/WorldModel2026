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

# GreenEarthNet keeps the public chopped tracks in a separate tree from the
# raw EarthNet2021x release. It is tempting to encode ``ood-t_chopped`` as
# the raw ``ood`` role, but doing so would make a result look comparable while
# actually changing its target population. Keep an explicit schema/role
# family instead. The Stage2 loader can consume it only when a caller passes
# ``data.manifest_protocol`` deliberately; ordinary train/IID/OOD runs retain
# the raw defaults below.
GREENEARTHNET_CHOPPED_DATASET_ID = "greenearthnet_chopped"
GREENEARTHNET_CHOPPED_PROTOCOL_ID = "greenearthnet_cvpr2024_chopped_v1"
GREENEARTHNET_CHOPPED_TRACKS: tuple[str, ...] = (
    "val_chopped",
    "iid_chopped",
    "ood-t_chopped",
    "ood-s_chopped",
    "ood-st_chopped",
)

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


def manifest_protocol_spec(protocol: str) -> dict[str, object]:
    """Return the immutable dataset/role contract for a supported manifest.

    This is intentionally closed rather than accepting arbitrary strings: a
    typo such as ``ood_t`` must fail before a prediction export reads data.
    """

    if protocol == PROTOCOL_ID:
        return {
            "dataset": DATASET_ID,
            "roles": VALID_MANIFEST_ROLES,
            "source_splits": frozenset(SPLIT_CANDIDATES),
            "resolve_nested_earthnet_root": True,
        }
    if protocol == GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        tracks = frozenset(GREENEARTHNET_CHOPPED_TRACKS)
        return {
            "dataset": GREENEARTHNET_CHOPPED_DATASET_ID,
            "roles": tracks,
            "source_splits": tracks,
            "resolve_nested_earthnet_root": False,
        }
    raise ValueError(
        f"Unsupported manifest protocol {protocol!r}; expected one of "
        f"{[PROTOCOL_ID, GREENEARTHNET_CHOPPED_PROTOCOL_ID]}"
    )


def resolve_manifest_root(root: str | Path, *, protocol: str = PROTOCOL_ID) -> Path:
    """Resolve a dataset root without conflating raw and chopped layouts."""

    spec = manifest_protocol_spec(protocol)
    if bool(spec["resolve_nested_earthnet_root"]):
        return resolve_dataset_root(root)
    return Path(root).expanduser().resolve()


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


def build_greenearthnet_chopped_manifest(
    root: str | Path,
    track: str,
    *,
    hash_mode: str = "sha256",
    pattern: str = "**/*.nc",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze exactly one explicit GreenEarthNet chopped track.

    Unlike the raw EarthNet builder, this never interprets a chopped track as
    a raw IID/OOD split and never discovers files from the evaluation root.
    """

    if track not in GREENEARTHNET_CHOPPED_TRACKS:
        raise ValueError(
            f"Unknown GreenEarthNet chopped track {track!r}; expected one of "
            f"{list(GREENEARTHNET_CHOPPED_TRACKS)}"
        )
    if hash_mode not in {"none", "sha256"}:
        raise ValueError("hash_mode must be 'none' or 'sha256'")
    evaluation_root = resolve_manifest_root(
        root,
        protocol=GREENEARTHNET_CHOPPED_PROTOCOL_ID,
    )
    track_root = evaluation_root / track
    if not track_root.is_dir():
        raise FileNotFoundError(f"GreenEarthNet chopped track is missing: {track_root}")
    files = sorted(path.resolve() for path in track_root.glob(pattern) if path.is_file())
    if not files:
        raise FileNotFoundError(f"GreenEarthNet chopped track is empty: {track_root}")

    records: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for path in files:
        if path != evaluation_root and evaluation_root not in path.parents:
            raise ValueError(f"Manifest file escapes evaluation root: {path}")
        if path != track_root and track_root not in path.parents:
            raise ValueError(f"Manifest file escapes requested chopped track: {path}")
        relative = path.relative_to(evaluation_root).as_posix()
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
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset": GREENEARTHNET_CHOPPED_DATASET_ID,
        "protocol": GREENEARTHNET_CHOPPED_PROTOCOL_ID,
        "split": track,
        "role": track,
        "source_splits": [track],
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
    spec = manifest_protocol_spec(expected_protocol)
    expected_dataset = str(spec["dataset"])
    valid_roles = frozenset(spec["roles"])
    if int(manifest.get("schema_version", -1)) != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported manifest schema in {source}: "
            f"{manifest.get('schema_version')!r}"
        )
    if manifest.get("dataset") != expected_dataset:
        raise ValueError(
            f"Unexpected dataset in {source}: expected={expected_dataset!r}, "
            f"got={manifest.get('dataset')!r}"
        )
    if manifest.get("protocol") != expected_protocol:
        raise ValueError(
            f"Unexpected manifest protocol in {source}: "
            f"expected={expected_protocol!r}, got={manifest.get('protocol')!r}"
        )
    declared_split = str(manifest.get("split", ""))
    declared_role = str(manifest.get("role", declared_split))
    if declared_role not in valid_roles:
        raise ValueError(
            f"Unsupported manifest role in {source}: {declared_role!r}; expected one of "
            f"{sorted(valid_roles)}"
        )
    if expected_split and declared_role != expected_split:
        raise ValueError(
            f"Manifest role={declared_role!r} (split={declared_split!r}) does not "
            f"match requested split={expected_split!r}"
        )
    declared_sources = manifest.get("source_splits")
    if not isinstance(declared_sources, list) or not declared_sources:
        raise ValueError(f"Manifest {source} has no nonempty source_splits list")
    allowed_sources = frozenset(spec["source_splits"])
    invalid_sources = sorted(
        str(item) for item in declared_sources if str(item) not in allowed_sources
    )
    if invalid_sources:
        raise ValueError(
            f"Unsupported manifest source_splits in {source}: {invalid_sources}; "
            f"expected a subset of {sorted(allowed_sources)}"
        )

    if expected_protocol == GREENEARTHNET_CHOPPED_PROTOCOL_ID:
        if declared_split != declared_role or declared_sources != [declared_role]:
            raise ValueError(
                "GreenEarthNet chopped manifest split/role/source_splits must all "
                "refer to the same exact track; got "
                f"split={declared_split!r}, role={declared_role!r}, "
                f"source_splits={declared_sources!r}"
            )

    records = manifest.get("files")
    if not isinstance(records, list):
        raise TypeError(f"Manifest {source} has no list-valued 'files' field")
    if int(manifest.get("num_files", -1)) != len(records):
        raise ValueError(f"Manifest {source} num_files does not match its records")
    if manifest.get("files_sha256") != records_digest(records):
        raise ValueError(f"Manifest {source} record digest is invalid")

    root = resolve_manifest_root(dataset_root, protocol=expected_protocol)
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
        # ``Path.resolve`` performs a filesystem lookup for every record on
        # some shared NAS mounts.  Preflight deliberately sets
        # ``verify_exists=False`` and only needs a safe, relocatable path; in
        # that mode the manifest's already-validated relative path can be
        # joined directly.  Resolve only when an existence/size/hash check
        # actually needs filesystem evidence.
        path = (root / relative).resolve() if (
            verify_exists or verify_sizes or verify_hashes
        ) else (root / relative)
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
