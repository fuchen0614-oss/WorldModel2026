"""eval/audit_adapters.py -- unify ObsWorldB4 (gate route) and ObsWorldB4Exclusive (T-only route)
for the extreme predictive-state audit, WITHOUT modifying either model or evaluator.

Only THREE things differ per architecture -- the base+state accessor, the second-branch scale, and
the zero-scale context manager. Everything below reuses the models' shared, gate/alpha-free machinery
(`_geo_weather`, `_direct_residual`, `direct_state`, `_decode_state`).

Correction 8 (weather_in_base): for B4 the base B0 still reads REAL future weather, so its T-identity /
zero-scale arms do NOT remove all weather -- they only isolate the ADDITIONAL state-branch contribution.
For the exclusive route the base (context prior) is weather-free, so those arms remove all weather. The
audit tags every arm with `weather_in_base` and never merges B4 and exclusive numbers into one claim.

Correction 9: the shared PRIMARY arms are the semantically-consistent ones (full, T-identity, zero-scale
closure, state-shuffle, weather intervention). The architecture-specific broken control stays secondary.
"""
from __future__ import annotations

import torch

from eval.eval_b4_state_contract import _gate_zero, _t_identity           # noqa: E402
from eval.eval_b4_exclusive_contract import _alpha_zero, _uf              # noqa: E402


def arch_of(model) -> str:
    """Exclusive registers an `alpha` buffer and deletes `gate`; B4 keeps the learnable `gate`."""
    return "exclusive" if hasattr(model, "alpha") and "gate" not in model._parameters else "b4"


def weather_in_base(model) -> bool:
    """True iff the base prediction already contains real future weather (B4 B0). Tag every arm with this."""
    return arch_of(model) == "b4"


def base_and_state(model, data):
    """(base_pred, z_t). B4 base = B0 with REAL future weather; exclusive base = weather-free context prior."""
    if arch_of(model) == "exclusive":
        return model._prior_state(data)
    return model._b0_and_state(data)


def scale(model):
    return model.alpha if arch_of(model) == "exclusive" else model.gate


def zero_scale_ctx(model):
    """Context manager that zeroes the second-branch scale (closure). NOT interchangeable across arch."""
    return _alpha_zero(model) if arch_of(model) == "exclusive" else _gate_zero(model)


def t_identity_ctx(model):
    """Shared T->identity ablation (works verbatim on both; `transition` is the parent module)."""
    return _t_identity(model)


def _bhw(data):
    hr = data["dynamic"][0]
    return hr.shape[0], hr.shape[-2], hr.shape[-1]


def predict(model, data):
    """[full] forecast -- bare positional call is identical on both routes."""
    return model.forecast(data)


def future_weather(model, data):
    """The real future-weather forcing window fed to T (B, target_len, n_weather)."""
    return _uf(model, data)


def predict_with_weather(model, data, uf):
    """base + scale * O(T(z_t, uf, geo)). Drives BOTH routes by an explicit forcing tensor `uf`
    (never `model.forecast_weather`, which the exclusive route refuses)."""
    base, z_t = base_and_state(model, data)
    geo, _ = model._geo_weather(data)
    B, H, W = _bhw(data)
    resid = model._direct_residual(z_t, uf, geo, B, H, W)
    return base + scale(model) * resid


def predict_state_shuffle(model, data, perm):
    """[shared state-shuffle control] decode the state branch from a PERMUTED z_t (across the batch),
    keeping the real base + real weather geometry. `perm` is a LongTensor permutation of range(B)."""
    base, z_t = base_and_state(model, data)
    geo, uf = model._geo_weather(data)
    B, H, W = _bhw(data)
    resid = model._direct_residual(z_t[perm], uf, geo, B, H, W)
    return base + scale(model) * resid


def extract_states(model, data, h: int):
    """(z_t, z_{t+h}) via the shared transition (state movement / rank diagnostics)."""
    base, z_t = base_and_state(model, data)
    geo, uf = model._geo_weather(data)
    z_h = model.direct_state(z_t, uf, geo, int(h))
    return z_t, z_h


ARMS_SHARED_PRIMARY = ("full", "closure_zero_scale", "t_identity", "state_shuffle")
