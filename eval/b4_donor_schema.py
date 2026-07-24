#!/usr/bin/env python
"""plan-b-pvt · Q3 season+geo DONOR schema, validator (pure) and builder helpers.

A donor manifest supplies, for every target cube, a DIFFERENT cube whose FUTURE
weather is injected into the TerraState transition while B0 stays fixed. For the
"season+geo matched" arm to be meaningful the donor must genuinely share the
target's meteorological season AND geographic neighbourhood — not merely carry a
field that says so.

This module is deliberately split:
  * ``validate_donor_manifest`` is PURE (dict in, error-list out): it refuses a
    manifest that lacks the schema header or per-pair EVIDENCE, and it re-checks
    that evidence's internal consistency (haversine recomputed from the recorded
    centroids must match the recorded distance; the tile parsed from the filename
    must match the recorded tile; seasons must be equal and valid; the geo
    distance must be within the schema bound). It NEVER declares "matched" from a
    bare field name — every claim is cross-checked or the pair fails closed.
  * ``extract_cube_record`` reads season (from the NetCDF time coordinate) and the
    lat/lon centroid (from coordinates). It needs xarray + real data, so it is
    imported lazily by the builder and never runs in the CPU unit tests.

Season truth is the meteorological bucket (DJF/MAM/JJA/SON) of the FORECAST-window
start; geo truth is the cube centroid. Both are recorded by the builder from the
NetCDF and re-checked here for consistency.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "b4_donor_v1"
REQUIRED_SCHEMA_KEYS = ("version", "season_rule", "geo_rule", "max_geo_km", "season_source", "geo_source")
REQUIRED_PAIR_KEYS = (
    "donor", "target_tile", "donor_tile", "target_season", "donor_season",
    "target_centroid", "donor_centroid", "geo_distance_km",
)
VALID_SEASONS = ("DJF", "MAM", "JJA", "SON")
_MGRS_RE = re.compile(r"(?<![0-9A-Za-z])([0-9]{2}[A-Z]{3})(?![0-9A-Za-z])")
_DATE_RE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")
_TOL_KM = 1.0  # recomputed-vs-recorded haversine tolerance


def season_bucket(month: int) -> str:
    if month in (12, 1, 2):
        return "DJF"
    if month in (3, 4, 5):
        return "MAM"
    if month in (6, 7, 8):
        return "JJA"
    if month in (9, 10, 11):
        return "SON"
    raise ValueError(f"month out of range: {month!r}")


def parse_cube_key(relpath: str | Path) -> dict[str, Any]:
    """Best-effort deterministic parse of tile + earliest date from a cube path.

    Returns {"tile": str|None, "start_date": (y,m,d)|None}. The MGRS tile is taken
    from the filename token, falling back to the parent-directory name (the
    official scorer's "season"/region field). Dates are only present in some
    naming conventions; when absent the season cannot be filename-verified and the
    validator relies on the builder's NetCDF-recorded season instead.
    """
    p = Path(relpath)
    stem, region = p.stem, p.parent.name
    tile = None
    m = _MGRS_RE.search(stem) or _MGRS_RE.search(region)
    if m:
        tile = m.group(1)
    dates = [(int(y), int(mo), int(d)) for y, mo, d in _DATE_RE.findall(stem)]
    start = min(dates) if dates else None
    return {"tile": tile, "start_date": start}


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between (lat, lon) points in km."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(h)))


def _finite_pair(v) -> bool:
    return (isinstance(v, (list, tuple)) and len(v) == 2
            and all(isinstance(x, (int, float)) and not isinstance(x, bool) and x == x
                    and math.isfinite(x) for x in v))


def validate_donor_manifest(manifest: dict, targets, root: Path) -> list[str]:
    """Return a list of errors (empty == usable). Fail closed on anything unproven."""
    errs: list[str] = []
    if not isinstance(manifest, dict):
        return ["donor manifest is not an object"]
    schema = manifest.get("donor_schema")
    if not isinstance(schema, dict):
        return ["missing 'donor_schema' header — refusing to trust bare donor fields"]
    miss = [k for k in REQUIRED_SCHEMA_KEYS if k not in schema]
    if miss:
        errs.append(f"donor_schema missing keys: {miss}")
    max_km = schema.get("max_geo_km")
    if not isinstance(max_km, (int, float)) or isinstance(max_km, bool) or not math.isfinite(max_km):
        errs.append("donor_schema.max_geo_km is not a finite number")
        max_km = None
    pairs = manifest.get("pairs")
    if not isinstance(pairs, dict):
        return errs + ["missing 'pairs' mapping"]

    root = Path(root)
    for t in targets:
        rel = str(Path(t).relative_to(root))
        entry = pairs.get(rel)
        if entry is None:
            errs.append(f"uncovered target: {rel}"); continue
        if not isinstance(entry, dict):
            errs.append(f"pair for {rel} is not an object with evidence"); continue
        miss = [k for k in REQUIRED_PAIR_KEYS if k not in entry]
        if miss:
            errs.append(f"{rel}: pair missing evidence {miss}"); continue

        donor_rel = entry["donor"]
        if donor_rel == rel:
            errs.append(f"donor==target: {rel}")
        if not (root / donor_rel).is_file():
            errs.append(f"donor file missing: {donor_rel}")

        # tile evidence cross-checked against the filename-derived tile
        t_parsed, d_parsed = parse_cube_key(rel), parse_cube_key(donor_rel)
        if t_parsed["tile"] and entry["target_tile"] != t_parsed["tile"]:
            errs.append(f"{rel}: recorded target_tile {entry['target_tile']} != filename {t_parsed['tile']}")
        if d_parsed["tile"] and entry["donor_tile"] != d_parsed["tile"]:
            errs.append(f"{rel}: recorded donor_tile {entry['donor_tile']} != filename {d_parsed['tile']}")

        # season evidence: valid, equal, and (when the filename carries a date) verified
        ts, dsn = entry["target_season"], entry["donor_season"]
        if ts not in VALID_SEASONS or dsn not in VALID_SEASONS:
            errs.append(f"{rel}: season not in {VALID_SEASONS} (got {ts}/{dsn})")
        elif ts != dsn:
            errs.append(f"{rel}: season mismatch target={ts} donor={dsn}")
        if t_parsed["start_date"]:
            fn_season = season_bucket(t_parsed["start_date"][1])
            if fn_season != ts:
                errs.append(f"{rel}: recorded target_season {ts} != filename-derived {fn_season}")

        # geo evidence: centroids present & finite, recorded distance consistent & within bound
        tc, dc = entry["target_centroid"], entry["donor_centroid"]
        if not (_finite_pair(tc) and _finite_pair(dc)):
            errs.append(f"{rel}: centroid evidence missing/non-finite"); continue
        rec = entry["geo_distance_km"]
        if not isinstance(rec, (int, float)) or isinstance(rec, bool) or not math.isfinite(rec):
            errs.append(f"{rel}: geo_distance_km not finite"); continue
        recomputed = haversine_km(tuple(tc), tuple(dc))
        if abs(recomputed - rec) > _TOL_KM:
            errs.append(f"{rel}: geo_distance_km {rec:.1f} inconsistent with centroids ({recomputed:.1f})")
        if max_km is not None and recomputed > max_km:
            errs.append(f"{rel}: donor {recomputed:.1f}km exceeds max_geo_km {max_km}")
    return errs


def donor_rel(entry) -> str:
    """Extract the donor relative path from a pair entry (dict or bare string)."""
    return entry["donor"] if isinstance(entry, dict) else entry


# ---- builder helpers (NetCDF read is lazy; pair assignment is pure) -----------
def extract_cube_record(path: str | Path) -> dict[str, Any]:
    """Read tile/season/centroid for one cube. Needs xarray + real data."""
    import xarray as xr  # lazy: never imported by the CPU unit tests
    from eval.greenearthnet_protocol import expected_prediction_times
    p = Path(path)
    with xr.open_dataset(p) as ds:
        times = expected_prediction_times(ds)
        start_month = int(str(times.values[0])[5:7])
        lat = float(ds["lat"].values.mean()); lon = float(ds["lon"].values.mean())
    parsed = parse_cube_key(p)
    return {"tile": parsed["tile"], "season": season_bucket(start_month),
            "centroid": [lat, lon]}


def build_pairs(records: dict[str, dict], *, max_geo_km: float) -> dict[str, dict]:
    """Assign each target a donor from the SAME season and (tile-family OR ≤max_geo_km),
    never itself. ``records`` maps rel-path -> {tile, season, centroid}. Deterministic:
    among eligible donors, the geographically nearest (then lexicographically first)
    is chosen. Targets with no eligible donor are omitted (caller fails closed on the
    resulting coverage gap)."""
    pairs: dict[str, dict] = {}
    rels = sorted(records)
    for rel in rels:
        r = records[rel]
        cands = []
        for other in rels:
            if other == rel:
                continue
            o = records[other]
            if o["season"] != r["season"]:
                continue
            dist = haversine_km(tuple(r["centroid"]), tuple(o["centroid"]))
            same_family = (r["tile"] and o["tile"] and r["tile"][:3] == o["tile"][:3])
            if same_family or dist <= max_geo_km:
                cands.append((dist, other))
        if not cands:
            continue
        cands.sort(key=lambda x: (x[0], x[1]))
        dist, donor = cands[0]
        o = records[donor]
        pairs[rel] = {"donor": donor, "target_tile": r["tile"], "donor_tile": o["tile"],
                      "target_season": r["season"], "donor_season": o["season"],
                      "target_centroid": r["centroid"], "donor_centroid": o["centroid"],
                      "geo_distance_km": round(dist, 4)}
    return pairs
