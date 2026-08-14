"""Shared paired-statistics for the A' formal result package.

Implements the schema-required paired uncertainty used by Q1/Q2/Q3
(RESULT_INGESTION_SCHEMA.md sections 4.2, 5, 6): a FIXED (seeded, deterministic)
bootstrap CI over paired per-sample deltas, an optional tile-cluster bootstrap,
and a frozen tie-tolerance win/tie/loss count. Numpy-only, no torch, no I/O.

delta convention: ``delta = model - baseline`` for every metric; the caller
states ``higher_is_better`` so wins/losses are oriented correctly.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


def paired_bootstrap_ci(
    deltas: Sequence[float],
    *,
    n_boot: int = 10000,
    ci_level: float = 0.95,
    seed: int = 42,
    cluster_ids: Optional[Sequence] = None,
) -> dict:
    """Deterministic percentile bootstrap CI of the mean paired delta.

    ``cluster_ids`` (e.g. tile ids) switches to a cluster bootstrap that
    resamples clusters, not individual samples, so spatially-correlated
    minicubes do not inflate confidence.
    """

    d = np.asarray(deltas, dtype=np.float64)
    if d.ndim != 1 or d.size == 0:
        raise ValueError("deltas must be a non-empty 1-D sequence")
    if not np.isfinite(d).all():
        raise ValueError("deltas contain non-finite values")
    if not (0.0 < ci_level < 1.0):
        raise ValueError("ci_level must be in (0,1)")
    rng = np.random.default_rng(int(seed))
    n = d.size

    if cluster_ids is None:
        idx = rng.integers(0, n, size=(int(n_boot), n))
        boot_means = d[idx].mean(axis=1)
        n_clusters = None
        method = "iid_percentile_bootstrap"
    else:
        cluster_ids = list(cluster_ids)
        if len(cluster_ids) != n:
            raise ValueError("cluster_ids length must match deltas")
        groups: dict = {}
        for i, c in enumerate(cluster_ids):
            groups.setdefault(c, []).append(i)
        keys = list(groups)
        idx_by_key = [np.asarray(groups[k]) for k in keys]
        k = len(keys)
        boot_means = np.empty(int(n_boot), dtype=np.float64)
        for b in range(int(n_boot)):
            pick = rng.integers(0, k, size=k)
            sel = np.concatenate([idx_by_key[p] for p in pick])
            boot_means[b] = d[sel].mean()
        n_clusters = k
        method = "tile_cluster_percentile_bootstrap"

    alpha = 1.0 - ci_level
    lo = float(np.quantile(boot_means, alpha / 2.0))
    hi = float(np.quantile(boot_means, 1.0 - alpha / 2.0))
    return {
        "delta_mean": float(d.mean()),
        "ci_low": lo,
        "ci_high": hi,
        "ci_method": method,
        "ci_level": float(ci_level),
        "n_boot": int(n_boot),
        "bootstrap_seed": int(seed),
        "n_paired_samples": int(n),
        "n_clusters": n_clusters,
    }


def win_tie_loss(
    deltas: Sequence[float],
    *,
    tie_tolerance: float,
    higher_is_better: bool,
) -> dict:
    """Frozen tie-tolerance W/T/L over paired deltas (delta = model - baseline)."""

    d = np.asarray(deltas, dtype=np.float64)
    if d.ndim != 1 or d.size == 0:
        raise ValueError("deltas must be a non-empty 1-D sequence")
    if tie_tolerance < 0:
        raise ValueError("tie_tolerance must be non-negative")
    tie = int((np.abs(d) <= tie_tolerance).sum())
    if higher_is_better:
        win = int((d > tie_tolerance).sum())
        loss = int((d < -tie_tolerance).sum())
    else:
        win = int((d < -tie_tolerance).sum())
        loss = int((d > tie_tolerance).sum())
    assert win + tie + loss == d.size
    return {
        "win": win,
        "tie": tie,
        "loss": loss,
        "tie_tolerance": float(tie_tolerance),
        "higher_is_better": bool(higher_is_better),
        "n_paired_samples": int(d.size),
    }
