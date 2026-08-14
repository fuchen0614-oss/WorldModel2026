"""Shared provenance + finite-value helpers for the A' formal result package.

Centralises the RESULT_INGESTION_SCHEMA.md common-shell fields (section 3.3) and
the schema's hard "no NaN/Infinity in JSON" rule (section 1.9). Pure-python, no
torch, no model imports, so it is cheap to unit-test on CPU.
"""

from __future__ import annotations

import math
from typing import Any, Optional

PAPER_MODEL_ID = "TerraState"
VALID_CLOSURE_IDS = ("A_state_primary", "B_matched_residual")


def finite_only(obj: Any) -> Any:
    """Recursively replace non-finite floats with None (explicit missing)."""

    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: finite_only(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [finite_only(v) for v in obj]
    return obj


def has_non_finite(obj: Any) -> bool:
    """True if any float anywhere in the structure is NaN/Inf."""

    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(has_non_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(has_non_finite(v) for v in obj)
    return False


def assert_all_finite(obj: Any, *, where: str = "result") -> None:
    """Fail-closed: raise if a formal payload contains any non-finite float."""

    if has_non_finite(obj):
        raise ValueError(f"{where} contains non-finite (NaN/Inf) values; formal package is fail-closed")


def common_provenance_shell(
    *,
    closure_id: str,
    checkpoint_sha256: str,
    config_sha256: str,
    data_manifest_sha256: Optional[str],
    evaluator_sha256: Optional[str],
    mask_protocol_sha256: Optional[str],
    aggregation_protocol_sha256: Optional[str],
    artifact_id: str,
    output_sha256: Optional[str] = None,
) -> dict:
    """The per-row common provenance shell required by schema section 3.3.

    ``closure_id`` must be one of the two allowed values; for A' it is
    ``A_state_primary``. Missing upstream hashes are recorded as None (explicit),
    never fabricated -- the ingestion side keeps the corresponding cell ``TBD``.
    """

    if closure_id not in VALID_CLOSURE_IDS:
        raise ValueError(f"closure_id must be one of {VALID_CLOSURE_IDS}, got {closure_id!r}")
    if not checkpoint_sha256 or not config_sha256:
        raise ValueError("checkpoint_sha256 and config_sha256 are required")
    if not artifact_id:
        raise ValueError("artifact_id is required")
    return {
        "paper_model_id": PAPER_MODEL_ID,
        "closure_id": closure_id,
        "checkpoint_sha256": checkpoint_sha256,
        "config_sha256": config_sha256,
        "data_manifest_sha256": data_manifest_sha256,
        "evaluator_sha256": evaluator_sha256,
        "mask_protocol_sha256": mask_protocol_sha256,
        "aggregation_protocol_sha256": aggregation_protocol_sha256,
        "artifact_id": artifact_id,
        "output_sha256": output_sha256,
    }
