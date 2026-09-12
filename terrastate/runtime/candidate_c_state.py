"""Thin runtime state adapter for Candidate C inference."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

import torch

SCHEMA = "candidate_c_runtime_state_v1"

def model_state_hash(model) -> str:
    h = hashlib.sha256()
    for key, value in sorted(model.state_dict().items()):
        h.update(key.encode("utf-8"))
        h.update(value.detach().cpu().to(torch.float32).numpy().tobytes())
    return h.hexdigest()

@dataclass
class CandidateCState:
    z: torch.Tensor
    prior: torch.Tensor
    geo: torch.Tensor
    offset: int
    valid_horizon: int
    model_hash: str
    schema: str = SCHEMA

    def clone(self) -> "CandidateCState":
        return CandidateCState(self.z.clone(), self.prior.clone(), self.geo.clone(), int(self.offset), int(self.valid_horizon), self.model_hash, self.schema)

def initialize(model, history_batch: dict[str, Any]) -> CandidateCState:
    prior, z = model._prior_state(history_batch)
    geo, _ = model._geo_weather(history_batch)
    # offset is relative to the future window: z starts before weather[0].
    return CandidateCState(z.detach().clone(), prior.detach().clone(), geo.detach().clone(), 0, int(model.target_len), model_state_hash(model))

def branch(state: CandidateCState) -> CandidateCState:
    return state.clone()

def advance(model, state: CandidateCState, weather_segment: torch.Tensor, end_offset: int) -> CandidateCState:
    if state.schema != SCHEMA:
        raise ValueError(f"unsupported runtime state schema: {state.schema!r}")
    if model_state_hash(model) != state.model_hash:
        raise ValueError("runtime state model hash does not match the model")
    end_offset = int(end_offset)
    span = end_offset - int(state.offset)
    if span <= 0 or end_offset > state.offset + state.valid_horizon:
        raise ValueError("end_offset is outside the valid runtime horizon")
    if weather_segment.ndim != 3 or weather_segment.shape[1] != span:
        raise ValueError(f"weather segment must have length {span}")
    with torch.no_grad():
        z_next = model.segment_state(state.z, weather_segment, state.geo, (span,))
    return CandidateCState(z_next.detach().clone(), state.prior, state.geo, end_offset, state.valid_horizon, state.model_hash, state.schema)

def decode(model, state: CandidateCState) -> torch.Tensor:
    if state.offset <= 0 or state.offset > state.prior.shape[1]:
        raise ValueError("state offset is outside the stored prior horizon")
    if model_state_hash(model) != state.model_hash:
        raise ValueError("runtime state model hash does not match the model")
    b = state.prior.shape[0]
    h, w = state.prior.shape[-2:]
    with torch.no_grad():
        return state.prior[:, state.offset - 1] + model.alpha * model._decode_state(state.z, b, h, w)

def save_state(state: CandidateCState, destination: str | Path) -> None:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"schema": state.schema, "z": state.z.cpu(), "prior": state.prior.cpu(), "geo": state.geo.cpu(), "offset": state.offset, "valid_horizon": state.valid_horizon, "model_hash": state.model_hash}, path)

def load_state(destination: str | Path, *, model=None, expected_model_hash: str | None = None) -> CandidateCState:
    raw = torch.load(destination, map_location="cpu", weights_only=False)
    if raw.get("schema") != SCHEMA:
        raise ValueError("runtime state schema mismatch")
    expected = model_state_hash(model) if model is not None else expected_model_hash
    if expected is not None and raw["model_hash"] != expected:
        raise ValueError("runtime state model hash does not match the expected model")
    return CandidateCState(raw["z"], raw["prior"], raw["geo"], int(raw["offset"]), int(raw["valid_horizon"]), str(raw["model_hash"]), raw["schema"])
