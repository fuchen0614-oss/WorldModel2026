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
    SCHEMA_VERSION, build_pairs, extract_cube_record, validate_donor_manifest,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-manifest", required=True, help="FROZEN val_chopped manifest (no discovery)")
    ap.add_argument("--dataset-root", required=True)
    ap.add_argument("--split", default="val")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-geo-km", type=float, default=150.0)
    args = ap.parse_args()

    root = Path(args.dataset_root)
    man = json.loads(Path(args.data_manifest).read_text())      # honour the manifest's OWN protocol + role
    proto = man.get("protocol", "earthnet2021_standard_v1")
    role = man.get("role") or man.get("split") or args.split
    targets = load_manifest_files(args.data_manifest, str(root),
                                  expected_split=role, expected_protocol=proto, verify_exists=True)
    records = {}
    for t in targets:
        rel = str(Path(t).relative_to(root))
        records[rel] = extract_cube_record(t)

    pairs = build_pairs(records, max_geo_km=args.max_geo_km)
    manifest = {
        "donor_schema": {
            "version": SCHEMA_VERSION,
            "season_rule": "same meteorological season bucket (DJF/MAM/JJA/SON) of the "
                           "official forecast-window start month",
            "geo_rule": "same MGRS tile family (tile[:3]) OR cube-centroid haversine <= max_geo_km",
            "max_geo_km": args.max_geo_km,
            "season_source": "netcdf_time (expected_prediction_times)",
            "geo_source": "netcdf_latlon_centroid",
            "data_manifest": str(Path(args.data_manifest).resolve()),
        },
        "pairs": pairs,
    }
    covered = set(pairs)
    uncovered = sorted(str(Path(t).relative_to(root)) for t in targets
                       if str(Path(t).relative_to(root)) not in covered)
    # Self-validate the emitted manifest against the same pure validator the contract uses.
    errs = validate_donor_manifest(manifest, targets, root)
    seasons = {}
    for rel, e in pairs.items():
        seasons[e["target_season"]] = seasons.get(e["target_season"], 0) + 1
    audit = {
        "n_targets": len(targets), "n_paired": len(pairs), "n_uncovered": len(uncovered),
        "uncovered": uncovered[:50], "season_hist": seasons,
        "max_geo_km": args.max_geo_km, "validator_errors": errs[:50],
        "status": "COMPLETE" if (not uncovered and not errs) else "INCOMPLETE_FAIL_CLOSED",
    }
    write_json_atomic(manifest, args.out)
    write_json_atomic(audit, str(Path(args.out).with_suffix(".audit.json")))
    print(json.dumps(audit, indent=2))
    if audit["status"] != "COMPLETE":
        print("[donor] INCOMPLETE — uncovered targets or validator errors; contract will fail closed.")
        return 2
    print(f"[donor] wrote {args.out}  pairs={len(pairs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
