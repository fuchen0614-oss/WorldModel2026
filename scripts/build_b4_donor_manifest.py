#!/usr/bin/env python
"""plan-b-pvt · build + audit a Q3 season+geo DONOR manifest for the B4 contract.

Reads the FROZEN val_chopped data manifest (no discovery), extracts each cube's
tile / meteorological season / lat-lon centroid FROM THE NetCDF, then assigns each
target a same-season, geo-near donor (never itself) via the pure
``eval.b4_donor_schema.build_pairs``. Writes:
  * <out>.json      — {donor_schema, pairs} consumed by eval_b4_state_contract.py
  * <out>.audit.json — coverage, season/geo distributions, uncovered targets

Fail closed: if ANY target has no eligible donor, the manifest is still written but
the audit marks it INCOMPLETE and the script exits non-zero, so the formal contract
run refuses it (a partial donor set must not be silently scored).

Server only (needs xarray + real data):
  python scripts/build_b4_donor_manifest.py \
    --data-manifest <frozen val.json> --dataset-root $DATA --split val \
    --out evaluations/plan_b_b4a_post/donors.json --max-geo-km 150
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import load_manifest_files, write_json_atomic  # noqa: E402
from eval.b4_donor_schema import (  # noqa: E402
    SCHEMA_VERSION_V2, DOY_WINDOW_DAYS, REUSE_CAP, MAX_GEO_KM_V2, DIVERGENCE_FLOOR_QUANTILE,
    WEATHER_DIV_METRIC, build_pairs_divergent, extract_cube_record, validate_donor_manifest_exclusive,
)


def main() -> int:
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-manifest", required=True, help="FROZEN val_chopped manifest (no discovery)")
    ap.add_argument("--dataset-root", required=True)
    ap.add_argument("--split", default="val")
    ap.add_argument("--out", required=True)
    # frozen RULE knobs (defaults ARE the pre-registered constants; overriding is discouraged and recorded)
    ap.add_argument("--max-geo-km", type=float, default=MAX_GEO_KM_V2)
    ap.add_argument("--doy-window-days", type=int, default=DOY_WINDOW_DAYS)
    ap.add_argument("--reuse-cap", type=int, default=REUSE_CAP)
    ap.add_argument("--divergence-floor-quantile", type=float, default=DIVERGENCE_FLOOR_QUANTILE)
    args = ap.parse_args()

    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    from models.encoders.pvt_contextformer_q import contextformer6m_hparams
    hp = contextformer6m_hparams(pvt_pretrained=False)
    cl, tl = hp.context_length, hp.target_length

    root = Path(args.dataset_root)
    man = json.loads(Path(args.data_manifest).read_text())
    proto = man.get("protocol", "earthnet2021_standard_v1")
    role = man.get("role") or man.get("split") or args.split
    targets = load_manifest_files(args.data_manifest, str(root),
                                  expected_split=role, expected_protocol=proto, verify_exists=True)
    ds = GreenEarthNetContextformerDataset(str(root), dl_cloudmask=True)
    idx_of = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}

    records, uf_by_rel = {}, {}
    for t in targets:
        rel = str(Path(t).relative_to(root))
        records[rel] = extract_cube_record(t)                              # tile/season/centroid/doy/year
        s = ds[idx_of[str(Path(t))]]
        uf_by_rel[rel] = s["dynamic"][1][cl:cl + tl].detach().cpu().numpy()  # (tl,V) NORMALIZED future weather

    pairs, floor_abs, unpaired = build_pairs_divergent(
        records, uf_by_rel, max_geo_km=args.max_geo_km, doy_window=args.doy_window_days,
        reuse_cap=args.reuse_cap, floor_quantile=args.divergence_floor_quantile)

    manifest = {
        "donor_schema": {
            "version": SCHEMA_VERSION_V2,
            "season_rule": "same meteorological season bucket (DJF/MAM/JJA/SON) of the forecast-window start",
            "geo_rule": "same MGRS tile family (tile[:3]) OR cube-centroid haversine <= max_geo_km",
            "max_geo_km": args.max_geo_km, "season_source": "netcdf_time (expected_prediction_times)",
            "geo_source": "netcdf_latlon_centroid",
            "doy_window_days": args.doy_window_days, "reuse_cap": args.reuse_cap,
            "divergence_floor_quantile": args.divergence_floor_quantile, "divergence_floor_abs": floor_abs,
            "weather_div_metric": WEATHER_DIV_METRIC,
            "selection_rule": "PREFER max weather-divergence among season+geo+DOY-window eligible donors "
                              "with divergence>=floor, reuse-capped; FROZEN before eval; NOT chosen from model results.",
            "data_manifest": str(Path(args.data_manifest).resolve()),
        },
        "pairs": pairs,
    }
    covered = set(pairs)
    uncovered = sorted(str(Path(t).relative_to(root)) for t in targets
                       if str(Path(t).relative_to(root)) not in covered)
    errs = validate_donor_manifest_exclusive(manifest, targets, root)

    from collections import Counter
    reuse_ctr = Counter(e["donor"] for e in pairs.values())
    seasons = Counter(e["target_season"] for e in pairs.values())
    divs = [e["weather_divergence"] for e in pairs.values()]
    doys = [e["doy_diff"] for e in pairs.values()]
    reuse_hist = Counter(reuse_ctr.values())     # how many donors used k times -> {k: n_donors}

    def _q(x, qs):
        return {f"p{int(q*100)}": (float(np.quantile(x, q)) if x else None) for q in qs}
    audit = {
        "n_targets": len(targets), "n_paired": len(pairs), "n_uncovered": len(uncovered),
        "uncovered": uncovered[:50], "season_hist": dict(seasons),
        "n_unique_donors": len(reuse_ctr), "reuse_histogram": {str(k): v for k, v in sorted(reuse_hist.items())},
        "divergence_floor_abs": floor_abs, "divergence_quantiles": _q(divs, (0.0, 0.1, 0.5, 0.9)),
        "doy_diff_quantiles": _q(doys, (0.0, 0.5, 0.9, 1.0)),
        "max_geo_km": args.max_geo_km, "doy_window_days": args.doy_window_days, "reuse_cap": args.reuse_cap,
        "validator_errors": errs[:50],
        "status": "COMPLETE" if (not uncovered and not errs) else "INCOMPLETE_FAIL_CLOSED",
    }
    write_json_atomic(manifest, args.out)
    write_json_atomic(audit, str(Path(args.out).with_suffix(".audit.json")))
    print(json.dumps(audit, indent=2))
    if audit["status"] != "COMPLETE":
        print("[donor v2] INCOMPLETE — uncovered targets or validator errors; contract will fail closed.")
        return 2
    print(f"[donor v2] wrote {args.out}  pairs={len(pairs)} floor_abs={floor_abs:.5f} unique_donors={len(reuse_ctr)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
