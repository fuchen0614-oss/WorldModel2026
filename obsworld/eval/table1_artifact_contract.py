"""Small dependency-free identities for immutable Table 1 artifacts.

Prediction/scoring modules may need NumPy, xarray, pandas, or torch.  The
assembly and parity stages should remain runnable in a minimal Python
environment, so their JSON/file identity contract lives here instead of in a
model/data helper.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


TABLE1_SCHEMA_VERSION = 1

# These identifiers are intentionally dependency-free because table assembly and
# parity verification should be runnable without NumPy/xarray/PyTorch.
PREDICTION_GRID_FIVE_DAILY_20 = "official_5day_20"
PREDICTION_GRID_CLIMATOLOGY_DAILY = "official_climatology_day50_daily"
VALID_PREDICTION_GRIDS = frozenset(
    (PREDICTION_GRID_FIVE_DAILY_20, PREDICTION_GRID_CLIMATOLOGY_DAILY)
)


def sha256_file(path: str | Path, *, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def load_json_object(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON object: {source}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a JSON object in {source}")
    return payload


def file_identity(path: str | Path, *, required: bool = True) -> dict[str, Any] | None:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        if required:
            raise FileNotFoundError(source)
        return None
    return {
        "path": str(source),
        "size_bytes": int(source.stat().st_size),
        "sha256": sha256_file(source),
    }


def source_manifest_identity(path: str | Path) -> dict[str, Any]:
    """Return the same stable target-manifest identity used by Table 1 artifacts."""

    source = Path(path).expanduser().resolve()
    payload = load_json_object(source)
    files_sha256 = payload.get("files_sha256")
    if not isinstance(files_sha256, str) or not files_sha256:
        raise ValueError(f"Manifest has no files_sha256: {source}")
    return {
        "path": str(source),
        "sha256": sha256_file(source),
        "dataset": payload.get("dataset"),
        "protocol": payload.get("protocol"),
        "split": payload.get("split"),
        "role": payload.get("role"),
        "num_files": payload.get("num_files"),
        "files_sha256": files_sha256,
    }
