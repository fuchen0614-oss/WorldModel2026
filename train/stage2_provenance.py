"""Immutable provenance and atomic checkpoint helpers for formal Stage2 runs.

The aim is not to make a checkpoint larger for its own sake.  A future result
is only interpretable if it says exactly which resolved configuration, frozen
manifest, conditioning statistics, Stage1.5 initializer and code revision
produced it.  This module keeps that bookkeeping independent of the training
loop so it can be unit-tested without a GPU or EarthNet cube.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping, Optional, Sequence

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: str | Path, *, chunk_size: int = 8 * 1024 * 1024) -> str:
    """Return a streaming SHA-256 digest without loading a large file at once."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(payload: Any) -> str:
    """Digest JSON-like data in a stable, formatting-independent way."""

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_identity(
    path: Optional[str | Path],
    *,
    required: bool = False,
) -> Optional[dict[str, Any]]:
    """Describe a file by absolute location, size and content digest."""

    if path is None or str(path).strip() == "":
        if required:
            raise ValueError("A required provenance file path is missing")
        return None
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        if required:
            raise FileNotFoundError(f"Required provenance file does not exist: {source}")
        return {"path": str(source), "exists": False}
    return {
        "path": str(source),
        "exists": True,
        "size_bytes": int(source.stat().st_size),
        "sha256": sha256_file(source),
    }


def manifest_identity(
    path: Optional[str | Path],
    *,
    required: bool = False,
) -> Optional[dict[str, Any]]:
    """Record both the JSON file checksum and its frozen record digest."""

    identity = file_identity(path, required=required)
    if identity is None or not identity.get("exists", False):
        return identity
    source = Path(identity["path"])
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise TypeError(f"Manifest {source} must contain a JSON object")
    records_digest = payload.get("files_sha256")
    if not isinstance(records_digest, str) or not records_digest:
        raise ValueError(f"Manifest {source} is missing files_sha256")
    identity.update(
        {
            "dataset": payload.get("dataset"),
            "protocol": payload.get("protocol"),
            "split": payload.get("split"),
            "role": payload.get("role"),
            "source_splits": payload.get("source_splits"),
            "selection": payload.get("selection"),
            "num_files": payload.get("num_files"),
            "files_sha256": records_digest,
        }
    )
    return identity


def conditioning_stats_identity(
    path: Optional[str | Path],
    *,
    required: bool = False,
) -> Optional[dict[str, Any]]:
    """Describe train-only conditioning statistics and their source manifest."""

    identity = file_identity(path, required=required)
    if identity is None or not identity.get("exists", False):
        return identity
    source = Path(identity["path"])
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise TypeError(f"Conditioning stats {source} must contain a JSON object")
    identity.update(
        {
            "schema_version": payload.get("schema_version"),
            "manifest_sha256": payload.get("manifest_sha256"),
            "num_files": payload.get("num_files"),
            "is_full_train": payload.get("is_full_train"),
            "g_variable": payload.get("g_variable"),
        }
    )
    return identity


def git_identity(repo_root: str | Path = REPO_ROOT) -> dict[str, Any]:
    """Best-effort repository identity; never makes a run silently untracked."""

    root = Path(repo_root).expanduser().resolve()

    def run(*args: str) -> Optional[str]:
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), *args],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError:
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.strip()

    status = run("status", "--porcelain")
    return {
        "repository": str(root),
        "commit": run("rev-parse", "HEAD"),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": None if status is None else bool(status),
        "status_porcelain": status,
    }


def runtime_identity(
    *,
    device: Optional[torch.device | str],
    world_size: int,
) -> dict[str, Any]:
    """Collect versions/hardware facts relevant to deterministic recovery."""

    resolved_device = str(device) if device is not None else None
    cuda_available = torch.cuda.is_available()
    gpu_names: list[str] = []
    if cuda_available:
        for index in range(torch.cuda.device_count()):
            try:
                gpu_names.append(torch.cuda.get_device_name(index))
            except RuntimeError:
                gpu_names.append(f"cuda:{index}")
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version() if cuda_available else None,
        "cuda_available": cuda_available,
        "gpu_names": gpu_names,
        "requested_device": resolved_device,
        "world_size": int(world_size),
    }


def build_stage2_run_provenance(
    config: Mapping[str, Any],
    *,
    train_manifest_path: Optional[str | Path],
    validation_manifest_path: Optional[str | Path],
    conditioning_stats_path: Optional[str | Path],
    stage15_checkpoint_path: Optional[str | Path],
    resume_checkpoint_path: Optional[str | Path],
    parent_provenance: Optional[Mapping[str, Any]],
    device: Optional[torch.device | str],
    world_size: int,
    repo_root: str | Path = REPO_ROOT,
) -> dict[str, Any]:
    """Build the static provenance block saved in every Stage2 checkpoint."""

    data = config.get("data", {})
    model = config.get("model", {})
    training = config.get("training", {})
    v2_protocol = str(data.get("stage2_protocol", "")).lower() in {
        "earthnet2021x_path_v2",
        "earthnet_path_v2",
        "path_v2",
    }
    formal_v2 = v2_protocol and (
        bool(data.get("require_manifest", False))
        or bool(model.get("require_stage15_checkpoint", False))
        or bool(training.get("require_full_conditioning_stats", False))
    )
    git = git_identity(repo_root)
    return {
        "schema_version": 1,
        "run_started_at_utc": datetime.now(timezone.utc).isoformat(),
        "resolved_config_sha256": canonical_json_sha256(config),
        "protocol": {
            "schema_version": config.get("protocol", {}).get("schema_version"),
            "dataset_protocol": data.get("dataset_protocol"),
            "stage2_protocol": data.get("stage2_protocol"),
            "evaluation_protocol": data.get("evaluation_protocol"),
            "driver_protocol": model.get("driver_protocol"),
            "forecast_mode": model.get("forecast_mode"),
        },
        "training": {
            "seed": training.get("seed"),
            "batch_size": data.get("batch_size"),
            "gradient_accumulation_steps": training.get("gradient_accumulation_steps"),
            "max_steps": training.get("max_steps"),
            "horizons_per_sample": training.get("horizons_per_sample"),
            "rollout_curriculum": training.get("rollout_curriculum"),
            "partition": training.get("partition"),
        },
        "data_root": str(data.get("root", "")),
        "train_manifest": manifest_identity(train_manifest_path, required=formal_v2),
        "validation_manifest": manifest_identity(
            validation_manifest_path,
            required=False,
        ),
        "conditioning_stats": conditioning_stats_identity(
            conditioning_stats_path,
            required=formal_v2 and bool(training.get("require_conditioning_stats", True)),
        ),
        "stage15_initializer": file_identity(
            stage15_checkpoint_path,
            required=formal_v2
            and not bool(resume_checkpoint_path)
            and bool(model.get("require_stage15_checkpoint", False)),
        ),
        "resume_checkpoint": file_identity(resume_checkpoint_path, required=False),
        "parent_provenance": dict(parent_provenance) if parent_provenance else None,
        "git": git,
        "official_evaluator": {
            "implementation": "eval.earthnet_standard_metrics",
            "repository_commit": git.get("commit"),
        },
        "runtime": runtime_identity(device=device, world_size=world_size),
    }


def write_json_atomic(path: str | Path, payload: Mapping[str, Any]) -> Path:
    """Write JSON through a temporary file and fsync before replacement."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output)
    _fsync_directory(output.parent)
    return output


def atomic_torch_save(payload: Mapping[str, Any], path: str | Path) -> Path:
    """Atomically serialize a checkpoint and persist its containing directory."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        torch.save(dict(payload), handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output)
    _fsync_directory(output.parent)
    return output


def _fsync_directory(path: Path) -> None:
    """Best effort directory fsync (unsupported filesystems may reject it)."""

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


def write_run_provenance(
    provenance: Mapping[str, Any],
    destinations: Sequence[str | Path],
) -> list[Path]:
    """Persist identical static provenance sidecars at requested locations."""

    written: list[Path] = []
    seen: set[Path] = set()
    for destination in destinations:
        resolved = Path(destination).expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        written.append(write_json_atomic(resolved, provenance))
    return written
