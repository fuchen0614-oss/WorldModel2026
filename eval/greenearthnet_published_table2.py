"""Frozen published-reference rows from Benson et al., CVPR 2024 Table 2.

These rows are citation-backed comparison values, not locally reproduced
artifacts.  Keeping them in a small typed module prevents paper-table scripts
from silently mixing them with hash-bound local evaluation rows.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PUBLICATION = {
    "key": "benson2024multimodal",
    "title": "Multi-modal Learning for Geospatial Vegetation Forecasting",
    "venue": "CVPR 2024",
    "table": "Table 2",
    "url": "https://openaccess.thecvf.com/content/CVPR2024/html/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.html",
    "protocol": "GreenEarthNet OOD-t chopped",
}


def _row(
    method_id: str,
    label: str,
    kind: str,
    params_millions: float,
    *,
    r2: float,
    rmse: float,
    nse: float,
    biasabs: float,
    outperformance: float | None,
    rmse25: float,
    prediction_grid: str = "official_5day_20",
    seeds: int | None = None,
    single_seed: bool = False,
    std: dict[str, float] | None = None,
) -> dict[str, Any]:
    return {
        "method_id": method_id,
        "method": label,
        "type": kind,
        "seed": "single" if single_seed else (f"{seeds} seeds" if seeds else ""),
        "params_millions": float(params_millions),
        "R2": float(r2),
        "rmse": float(rmse),
        "nse": float(nse),
        "biasabs": float(biasabs),
        "outperformance": None if outperformance is None else float(outperformance),
        "rmse25": float(rmse25),
        "metric_std": dict(std or {}),
        "prediction_grid": prediction_grid,
        "result_source": "published_reference",
        "citation": deepcopy(PUBLICATION),
        "evaluator_parity": "reported_by_source",
        "baseline_reference_parity": "reported_by_source",
    }


# Selected rows used by the ObsWorld paper-facing comparison.  Values are the
# means (and, where reported, standard deviations) printed in CVPR 2024 Table 2.
PUBLISHED_TABLE2_ROWS = (
    _row(
        "persistence", "Persistence", "published non-learning", 0.0,
        r2=0.00, rmse=0.23, nse=-1.28, biasabs=0.17,
        outperformance=0.218, rmse25=0.09,
    ),
    _row(
        "previous-year", "Previous year", "published non-learning", 0.0,
        r2=0.56, rmse=0.20, nse=-0.40, biasabs=0.14,
        outperformance=0.193, rmse25=0.18,
    ),
    _row(
        "climatology", "Climatology", "published non-learning", 0.0,
        r2=0.58, rmse=0.18, nse=-0.34, biasabs=0.13,
        outperformance=None, rmse25=0.16,
        prediction_grid="official_climatology_day50_daily",
    ),
    _row(
        "earthformer", "Earthformer†", "published learned baseline", 60.6,
        r2=0.52, rmse=0.16, nse=-0.13, biasabs=0.10,
        outperformance=0.565, rmse25=0.09, single_seed=True,
    ),
    _row(
        "predrnn", "PredRNN", "published learned baseline", 1.4,
        r2=0.62, rmse=0.15, nse=0.03, biasabs=0.10,
        outperformance=0.647, rmse25=0.10, seeds=3,
        std={"R2": 0.00, "rmse": 0.00, "nse": 0.00, "biasabs": 0.00,
             "outperformance": 0.012, "rmse25": 0.00},
    ),
    _row(
        "simvp", "SimVP", "published learned baseline", 6.6,
        r2=0.60, rmse=0.15, nse=0.03, biasabs=0.09,
        outperformance=0.641, rmse25=0.10, seeds=3,
        std={"R2": 0.00, "rmse": 0.00, "nse": 0.01, "biasabs": 0.00,
             "outperformance": 0.010, "rmse25": 0.00},
    ),
    _row(
        "contextformer", "Contextformer", "published learned baseline", 6.1,
        r2=0.62, rmse=0.14, nse=0.09, biasabs=0.09,
        outperformance=0.668, rmse25=0.08, seeds=3,
        std={"R2": 0.00, "rmse": 0.00, "nse": 0.01, "biasabs": 0.00,
             "outperformance": 0.003, "rmse25": 0.00},
    ),
)


def published_table2_rows() -> list[dict[str, Any]]:
    """Return mutable copies for rendering/serialization."""

    return deepcopy(list(PUBLISHED_TABLE2_ROWS))
