"""Protocol guards and provenance records for formal Stage2 evaluation.

Training provenance answers ``where did this checkpoint come from?``.  This
module answers the complementary question ``what exactly was evaluated or
exported from it?``.  In particular, a state-dict load being successful is not
enough evidence that a Direct24 checkpoint was evaluated as Direct24 under the
same temporal/data contract.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import math
import numbers
from pathlib import Path
from typing import Any, Mapping, Optional

from train.stage2_provenance import (
    canonical_json_sha256,
    conditioning_stats_identity,
    file_identity,
    git_identity,
    manifest_identity,
    runtime_identity,
    sha256_file,
    write_json_atomic,
)


_DATA_CONTRACT_KEYS = (
    "dataset",
    "data_format",
    "dataset_protocol",
    "evaluation_protocol",
    "stage2_protocol",
    "driver_protocol",
    "file_glob",
    "context_frames",
    "target_frames",
    "frame_interval_days",
    "netcdf_s2_offset_days",
    "model_img_size",
    "context_img_size",
    "target_img_size",
    "eval_img_size",
    "geo_img_size",
    "image_channels",
    "target_channels",
    "formal_dem_variable",
    "netcdf_dem_variables",
    "netcdf_solar_scale",
    "normalize",
    "band_spec",
    "driver_spec",
)

_ENCODER_RUNTIME_ONLY_KEYS = (
    "from_checkpoint",
    "freeze",
    "unfreeze_at_step",
    "unfreeze_last_blocks",
    "unfreeze_state_projector",
)

_MODEL_RUNTIME_ONLY_KEYS = (
    "compute_latent_targets",
    "require_stage15_checkpoint",
)


def stage2_evaluation_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    """Extract fields that must agree between checkpoint and evaluator config.

    Data roots, physical split names, manifests and Stage1.5 source paths are
    intentionally *not* part of this equality test.  An IID/OOD evaluation is
    supposed to change those.  Their identities are instead recorded in the
    evaluation sidecar.  Architecture, temporal alignment, masks/bands and
    loss definition must not silently drift.
    """

    data = config.get("data", {})
    model = copy.deepcopy(config.get("model", {}))
    protocol = config.get("protocol", {})
    if not isinstance(data, Mapping) or not isinstance(model, Mapping):
        raise TypeError("Stage2 configuration must contain mapping-valued data and model")
    for key in _MODEL_RUNTIME_ONLY_KEYS:
        model.pop(key, None)
    encoder = model.get("encoder")
    if isinstance(encoder, Mapping):
        cleaned_encoder = dict(encoder)
        for key in _ENCODER_RUNTIME_ONLY_KEYS:
            cleaned_encoder.pop(key, None)
        model["encoder"] = cleaned_encoder

    return {
        "schema_version": 1,
        "protocol": {
            "schema_version": protocol.get("schema_version")
            if isinstance(protocol, Mapping)
            else None,
            "dataset_protocol": data.get("dataset_protocol"),
            "stage2_protocol": data.get("stage2_protocol"),
            "evaluation_protocol": data.get("evaluation_protocol"),
            # Keep the physical DGH schema in the checkpoint/evaluator
            # contract.  The model's input dimension alone cannot detect a
            # permutation of four equally sized weather fields.
            "driver_protocol": protocol.get(
                "driver_protocol",
                model.get("driver_protocol", data.get("driver_protocol")),
            )
            if isinstance(protocol, Mapping)
            else model.get("driver_protocol", data.get("driver_protocol")),
            "physical_raw_variables": protocol.get("physical_raw_variables")
            if isinstance(protocol, Mapping)
            else None,
            "d_feature_names": protocol.get("d_feature_names")
            if isinstance(protocol, Mapping)
            else None,
            "eobs_variables": protocol.get("eobs_variables")
            if isinstance(protocol, Mapping)
            else None,
            "eobs_aggregations": protocol.get("eobs_aggregations")
            if isinstance(protocol, Mapping)
            else None,
            "dem_variable": protocol.get("dem_variable")
            if isinstance(protocol, Mapping)
            else None,
        },
        "data": {
            key: copy.deepcopy(data[key])
            for key in _DATA_CONTRACT_KEYS
            if key in data
        },
        "model": model,
        # Although loss weights do not change a prediction, allowing them to
        # drift changes reported internal validation numbers. Bind them too.
        "loss": copy.deepcopy(config.get("loss", {})),
    }


def _value_preview(value: Any, *, limit: int = 240) -> str:
    rendered = repr(value)
    return rendered if len(rendered) <= limit else f"{rendered[:limit]}..."


def _contract_mismatches(
    expected: Any,
    actual: Any,
    *,
    prefix: str = "",
) -> list[str]:
    """Return concise, recursively addressed differences between contracts."""

    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        differences: list[str] = []
        for key in sorted(set(expected) | set(actual), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in expected:
                differences.append(f"{path}: absent from checkpoint, runtime={_value_preview(actual[key])}")
            elif key not in actual:
                differences.append(f"{path}: checkpoint={_value_preview(expected[key])}, absent at runtime")
            else:
                differences.extend(
                    _contract_mismatches(expected[key], actual[key], prefix=path)
                )
        return differences
    if expected != actual:
        return [
            f"{prefix}: checkpoint={_value_preview(expected)}, "
            f"runtime={_value_preview(actual)}"
        ]
    return []


def verify_checkpoint_contract(
    checkpoint: Mapping[str, Any],
    runtime_config: Mapping[str, Any],
    *,
    allow_mismatch: bool = False,
) -> dict[str, Any]:
    """Reject a config/checkpoint protocol mismatch unless explicitly waived."""

    runtime_contract = stage2_evaluation_contract(runtime_config)
    saved_config = checkpoint.get("config")
    if not isinstance(saved_config, Mapping):
        message = (
            "Checkpoint has no saved resolved config, so its Stage2 protocol cannot "
            "be verified. Use --allow-checkpoint-contract-mismatch only for a "
            "clearly labeled legacy evaluation."
        )
        if not allow_mismatch:
            raise ValueError(message)
        return {
            "checked": False,
            "matches": False,
            "override_used": True,
            "reason": message,
            "runtime_contract_sha256": canonical_json_sha256(runtime_contract),
        }

    checkpoint_contract = stage2_evaluation_contract(saved_config)
    mismatches = _contract_mismatches(checkpoint_contract, runtime_contract)
    if mismatches and not allow_mismatch:
        preview = "\n  - ".join(mismatches[:12])
        extra = "" if len(mismatches) <= 12 else f"\n  ... and {len(mismatches) - 12} more"
        raise ValueError(
            "Refusing to evaluate a Stage2 checkpoint under a different protocol "
            "or architecture contract:\n  - "
            f"{preview}{extra}\n"
            "Pass --allow-checkpoint-contract-mismatch only for an explicitly "
            "labeled compatibility/legacy run."
        )
    return {
        "checked": True,
        "matches": not mismatches,
        "override_used": bool(mismatches and allow_mismatch),
        "mismatches": mismatches,
        "checkpoint_contract_sha256": canonical_json_sha256(checkpoint_contract),
        "runtime_contract_sha256": canonical_json_sha256(runtime_contract),
        "checkpoint_contract": checkpoint_contract,
        "runtime_contract": runtime_contract,
    }


def build_stage2_evaluation_provenance(
    runtime_config: Mapping[str, Any],
    *,
    checkpoint_path: str | Path,
    checkpoint: Mapping[str, Any],
    split: str,
    manifest_path: Optional[str | Path],
    conditioning_stats_path: Optional[str | Path],
    contract_verification: Mapping[str, Any],
    evaluator: str,
    invocation: Mapping[str, Any],
    device: Optional[str],
) -> dict[str, Any]:
    """Build a portable sidecar for direct evaluation or prediction export."""

    data = runtime_config.get("data", {})
    if not isinstance(data, Mapping):
        raise TypeError("runtime config data must be a mapping")
    checkpoint_training_provenance = checkpoint.get("provenance")
    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "kind": "stage2_evaluation",
        "evaluator": evaluator,
        "invocation": dict(invocation),
        "split": str(split),
        "checkpoint": file_identity(checkpoint_path, required=True),
        "checkpoint_training_provenance": (
            dict(checkpoint_training_provenance)
            if isinstance(checkpoint_training_provenance, Mapping)
            else None
        ),
        "contract_verification": dict(contract_verification),
        "runtime_config_sha256": canonical_json_sha256(runtime_config),
        "runtime_contract": stage2_evaluation_contract(runtime_config),
        "data": {
            "root": str(data.get("root", "")),
            "manifest": manifest_identity(manifest_path, required=False),
            "conditioning_stats": conditioning_stats_identity(
                conditioning_stats_path,
                required=False,
            ),
        },
        "git": git_identity(),
        "runtime": runtime_identity(device=device, world_size=1),
    }


def output_file_record(
    path: str | Path,
    *,
    root: str | Path,
    hash_mode: str,
) -> dict[str, Any]:
    """Describe a single exported prediction relative to its output root."""

    output = Path(path).resolve()
    output_root = Path(root).resolve()
    if hash_mode not in {"none", "sha256"}:
        raise ValueError(f"Unknown prediction hash_mode={hash_mode!r}")
    if not output.is_file():
        raise FileNotFoundError(f"Prediction output is missing: {output}")
    record: dict[str, Any] = {
        "path": output.relative_to(output_root).as_posix(),
        "size_bytes": int(output.stat().st_size),
    }
    if hash_mode == "sha256":
        record["sha256"] = sha256_file(output)
    return record


def prediction_records_digest(records: list[Mapping[str, Any]]) -> str:
    """Digest ordered prediction records without depending on JSON whitespace."""

    ordered = sorted((dict(record) for record in records), key=lambda item: item["path"])
    return canonical_json_sha256(ordered)


def write_evaluation_sidecar(path: str | Path, payload: Mapping[str, Any]) -> Path:
    """Atomically persist an evaluation/prediction provenance JSON object."""

    return write_json_atomic(path, payload)


def json_safe(value: Any) -> Any:
    """Convert non-finite scalar metrics into JSON ``null`` recursively."""

    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, numbers.Integral) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        scalar = float(value)
        return scalar if math.isfinite(scalar) else None
    return value
