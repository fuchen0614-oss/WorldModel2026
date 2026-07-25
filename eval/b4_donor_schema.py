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
    """Read tile/season/centroid + forecast-start DOY/year for one cube. Needs xarray + real data."""
    import datetime as _dt
    import xarray as xr  # lazy: never imported by the CPU unit tests
    from eval.greenearthnet_protocol import expected_prediction_times
    p = Path(path)
    with xr.open_dataset(p) as ds:
        times = expected_prediction_times(ds)
        t0 = str(times.values[0])[:10]                         # 'YYYY-MM-DD' of the forecast-window start
        y, mo, d = int(t0[:4]), int(t0[5:7]), int(t0[8:10])
        doy = _dt.date(y, mo, d).timetuple().tm_yday
        lat = float(ds["lat"].values.mean()); lon = float(ds["lon"].values.mean())
    parsed = parse_cube_key(p)
    return {"tile": parsed["tile"], "season": season_bucket(mo), "centroid": [lat, lon],
            "doy": int(doy), "year": int(y)}


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


# ======================================================================================
# DONOR v2 (Phase-II EXCLUSIVE Q3): weather-DIVERGENT donors, frozen rules, reuse cap.
# The v1 selector picks the geo-NEAREST same-season cube, which does not guarantee the
# injected future weather differs -> near-zero intervention. v2 requires a real weather
# regime change and PREFERS divergent donors, with all rules FROZEN before eval.
# ======================================================================================
SCHEMA_VERSION_V2 = "b4_donor_v2"
DOY_WINDOW_DAYS = 15          # frozen: narrow within-year window on forecast-start DOY (二.3)
REUSE_CAP = 3                 # frozen: max times one donor may be assigned (二.6)
MAX_GEO_KM_V2 = 150.0         # frozen: geo neighbourhood (二.2); no post-hoc CLI override
DIVERGENCE_FLOOR_QUANTILE = 0.5   # frozen RULE (二.9): absolute floor = this quantile of the eligible-pair
#                                   divergence distribution, DERIVED from data at build (no arbitrary constant)
WEATHER_DIV_METRIC = "rms_normalized_future_TxV"
REQUIRED_SCHEMA_KEYS_V2 = REQUIRED_SCHEMA_KEYS + (
    "doy_window_days", "reuse_cap", "divergence_floor_abs", "divergence_floor_quantile", "weather_div_metric")
REQUIRED_PAIR_KEYS_V2 = REQUIRED_PAIR_KEYS + ("doy_diff", "weather_divergence", "donor_reuse_count")


def doy_diff_circular(a: int, b: int) -> int:
    """Circular day-of-year distance (0..182), 365-day year."""
    d = abs(int(a) - int(b)) % 365
    return min(d, 365 - d)


def weather_divergence(uf_t, uf_d) -> float:
    """RMS over the (T,V) NORMALIZED future-weather trajectory — the SAME z-scored space the
    model ingests (二.4). Pure numpy so it is deterministic + testable."""
    import numpy as np
    a = np.asarray(uf_t, dtype=float); b = np.asarray(uf_d, dtype=float)
    return float(np.sqrt(np.mean((a - b) ** 2)))


def build_pairs_divergent(records, uf_by_rel, *, max_geo_km=MAX_GEO_KM_V2, doy_window=DOY_WINDOW_DAYS,
                          reuse_cap=REUSE_CAP, floor_quantile=DIVERGENCE_FLOOR_QUANTILE):
    """v2 assignment (二.1-6). Eligible donor = target!=donor, same season, geo (tile-family OR
    <=max_geo_km), DOY within window, weather-divergence >= data-derived floor. PREFER the MOST
    weather-divergent (then geo-nearest, then name), subject to a per-donor reuse cap; fail closed
    when none qualifies. Returns (pairs, floor_abs, unpaired_rels)."""
    import numpy as np
    rels = sorted(records)
    elig, all_div = {}, []
    for rel in rels:
        r = records[rel]; lst = []
        for other in rels:
            if other == rel:
                continue
            o = records[other]
            if o["season"] != r["season"]:
                continue
            dd = doy_diff_circular(r["doy"], o["doy"])
            if dd > doy_window:
                continue
            dist = haversine_km(tuple(r["centroid"]), tuple(o["centroid"]))
            same_family = bool(r["tile"] and o["tile"] and r["tile"][:3] == o["tile"][:3])
            if not (same_family or dist <= max_geo_km):
                continue
            div = weather_divergence(uf_by_rel[rel], uf_by_rel[other])
            lst.append({"donor": other, "geo": dist, "doy": dd, "div": div}); all_div.append(div)
        elig[rel] = lst
    floor_abs = float(np.quantile(all_div, floor_quantile)) if all_div else 0.0
    pairs, reuse, unpaired = {}, {}, []
    for rel in rels:
        r = records[rel]
        cands = [c for c in elig[rel] if c["div"] >= floor_abs and reuse.get(c["donor"], 0) < reuse_cap]
        if not cands:
            unpaired.append(rel); continue
        cands.sort(key=lambda c: (-c["div"], c["geo"], c["donor"]))   # PREFER divergent (二.5)
        c = cands[0]; o = records[c["donor"]]
        reuse[c["donor"]] = reuse.get(c["donor"], 0) + 1
        pairs[rel] = {"donor": c["donor"], "target_tile": r["tile"], "donor_tile": o["tile"],
                      "target_season": r["season"], "donor_season": o["season"],
                      "target_centroid": r["centroid"], "donor_centroid": o["centroid"],
                      "geo_distance_km": round(c["geo"], 4), "doy_diff": int(c["doy"]),
                      "weather_divergence": round(c["div"], 6)}
    for rel, e in pairs.items():
        e["donor_reuse_count"] = int(reuse.get(e["donor"], 0))
    return pairs, floor_abs, unpaired


def validate_donor_manifest_exclusive(manifest: dict, targets, root: Path) -> list[str]:
    """v2 pure validator (二.7): v1 geo/season/tile/self checks PLUS recorded-vs-FROZEN-threshold
    re-checks (doy_diff<=window, weather_divergence>=floor, donor_reuse_count<=cap and consistent).
    Weather divergence is recomputed against DATA by the builder, not here (no data in a pure check)."""
    from collections import Counter
    errs = list(validate_donor_manifest(manifest, targets, root))
    if not isinstance(manifest, dict):
        return errs
    schema = manifest.get("donor_schema", {})
    miss = [k for k in REQUIRED_SCHEMA_KEYS_V2 if k not in schema]
    if miss:
        errs.append(f"v2 donor_schema missing keys: {miss}")
    window = schema.get("doy_window_days"); cap = schema.get("reuse_cap"); floor = schema.get("divergence_floor_abs")
    pairs = manifest.get("pairs", {})
    if not isinstance(pairs, dict):
        return errs
    ctr = Counter(donor_rel(e) for e in pairs.values() if isinstance(e, dict))
    root = Path(root)
    for t in targets:
        rel = str(Path(t).relative_to(root)); e = pairs.get(rel)
        if not isinstance(e, dict):
            continue
        for k in REQUIRED_PAIR_KEYS_V2:
            if k not in e:
                errs.append(f"{rel}: v2 pair missing {k}")
        if isinstance(window, (int, float)) and isinstance(e.get("doy_diff"), (int, float)) and e["doy_diff"] > window:
            errs.append(f"{rel}: doy_diff {e['doy_diff']} > window {window}")
        if isinstance(floor, (int, float)) and isinstance(e.get("weather_divergence"), (int, float)) and e["weather_divergence"] < floor:
            errs.append(f"{rel}: weather_divergence {e['weather_divergence']} < floor {floor}")
        rc = int(ctr.get(donor_rel(e), 0))
        if isinstance(cap, (int, float)) and rc > cap:
            errs.append(f"{rel}: donor reused {rc}x > cap {cap}")
        if e.get("donor_reuse_count") != rc:
            errs.append(f"{rel}: recorded donor_reuse_count {e.get('donor_reuse_count')} != recomputed {rc}")
    return errs
