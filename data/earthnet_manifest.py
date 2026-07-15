"""Deterministic manifests for GreenEarthNet / EarthNet2021x files.

The manifest is deliberately relocatable: file paths are relative to the
``earthnet2021x`` dataset root and the manifest digest does not include a
machine-specific absolute path.  Formal Stage2 runs can therefore prove which
files were used without falling back to an unconstrained recursive glob.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


MANIFEST_SCHEMA_VERSION = 1
DATASET_ID = "greenearthnet/earthnet2021x"

# The EarthNet downloader exposes five physical packages.  GreenEarthNet's
# official evaluation tracks are commonly nested inside ``iid`` and ``ood``.
SPLIT_CANDIDATES: Mapping[str, Sequence[str]] = {
    "train": ("train",),
    "iid": ("iid/iid_chopped", "iid_chopped", "iid"),
    "ood": ("ood",),
    "ood-t": ("ood/ood-t_chopped", "ood-t_chopped"),
    "ood-s": ("ood/ood-s_chopped", "ood-s_chopped"),
    "ood-st": ("ood/ood-st_chopped", "ood-st_chopped"),
    "extreme": ("extreme",),
    "seasonal": ("seasonal",),
}


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

    # Prefer the first (most specific) existing directory.  Including both a
    # nested track and its parent would silently mix OOD-t/OOD-s/OOD-st.
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

    if hash_mode not in {"none", "sha256"}:
        raise ValueError("hash_mode must be 'none' or 'sha256'")
    dataset_root = resolve_dataset_root(root)
    files = discover_split_files(dataset_root, split, pattern=pattern)
    records = []
    for path in files:
        relative = path.relative_to(dataset_root).as_posix()
        record: dict[str, Any] = {
            "path": relative,
            "size_bytes": int(path.stat().st_size),
            "sample_id": path.stem,
        }
        if hash_mode == "sha256":
            record["sha256"] = sha256_file(path)
        records.append(record)
    records.sort(key=lambda item: item["path"])
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset": DATASET_ID,
        "split": split,
        "hash_mode": hash_mode,
        "num_files": len(records),
        "files": records,
        "files_sha256": records_digest(records),
    }


def write_manifest(manifest: Mapping[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(dict(manifest), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output


def load_manifest_files(
    manifest_path: str | Path,
    dataset_root: str | Path,
    *,
    expected_split: str | None = None,
    verify_exists: bool = True,
    verify_sizes: bool = False,
    verify_hashes: bool = False,
) -> list[Path]:
    """Load and validate an immutable file list.

    A validation dataset may intentionally reuse a ``train`` manifest before
    the deterministic geographic holdout is applied, hence ``val`` accepts a
    manifest whose declared split is ``train``.
    """

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
    declared_split = str(manifest.get("split", ""))
    allowed_splits = {expected_split} if expected_split else set()
    if expected_split == "val":
        allowed_splits.add("train")
    if expected_split and declared_split not in allowed_splits:
        raise ValueError(
            f"Manifest split={declared_split!r} does not match "
            f"requested split={expected_split!r}"
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
