#!/usr/bin/env python
"""tools/hotdry_selector.py -- forcing-only extreme hot-dry selection for the OOD-t predictive-state audit.

FROZEN CONTRACT (doc-87 corrections; do not relax post-hoc):
  * Selection uses ONLY future-weather forcing + observed/pre-forcing context. NEVER future NDVI,
    model output, prediction error, or a checkpoint.
  * Weather is read per-variable with _FillValue / scale_factor / add_offset / units parsed from the
    NetCDF (correction 3). A future-window valid-fraction gate excludes cubes with insufficient
    forcing; excluded counts are reported, not silently dropped.
  * Train climatology uses a hierarchical cohort fallback with a frozen minimum cohort n
    (correction 4): season x loc-bin  ->  season x lat-band  ->  season overall. Per cube the finest
    level meeting min_cohort_n is used.
  * Q80/Q90 thresholds are frozen from the TRAIN anomaly distribution, then applied to OOD-t
    (correction 2). They are never tuned on OOD-t or on any model result.
  * Matched-normal controls are deterministic caliper nearest-neighbour on observed / pre-forcing
    features with a fixed seed and a frozen reuse cap (correction 5); balance / coverage / reuse are
    reported. Season is matched exactly.

Torch-free (numpy + h5py only) so it runs in any local env; the audit evaluator (torch) only consumes
the manifests this produces. Two subcommands:

  calibrate  --train-root ROOT/train  --out climatology_train.json
  select     --ood-root ROOT/ood-t_chopped --climatology climatology_train.json --out selection.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import numpy as np

try:
    import h5py
except Exception as exc:  # pragma: no cover - dependency guard
    raise SystemExit(f"hotdry_selector requires h5py (torch-free NetCDF read): {exc}")

# ----------------------------------------------------------------------------- geometry / vars
PENTAD_DAYS = 5
CONTEXT_PENTADS = 10
TARGET_PENTADS = 20
CONTEXT_DAYS = CONTEXT_PENTADS * PENTAD_DAYS            # 50
TOTAL_DAYS = (CONTEXT_PENTADS + TARGET_PENTADS) * PENTAD_DAYS  # 150
FUTURE_SLICE = slice(CONTEXT_DAYS, TOTAL_DAYS)          # forcing window: days 50:150
CONTEXT_SLICE = slice(0, CONTEXT_DAYS)                  # observed window: days 0:50

INT16_MIN_INVALID = -32768                              # int16 floor, treat as invalid alongside _FillValue
HOT_VAR = "eobs_tg"                                     # mean 2 m temperature (Celsius)
HOT_VAR_ROBUST = "eobs_tx"                              # daily-max temperature (robustness only)
DRY_VAR = "eobs_rr"                                     # rainfall (mm); dryness = negative anomaly
VEG_LC_CODES = (10, 20, 30, 40)                         # tree / shrub / grass / crop (model lc range)
DL_CLEAR = 0                                            # s2_dlmask: 0 clear, 1 thick, 2 thin, 3 shadow

# frozen protocol defaults (echoed verbatim into climatology_train.json / thresholds.json / protocol.json)
DEFAULTS: dict[str, Any] = dict(
    valid_fraction_min=0.80,     # min fraction of future-window days with BOTH tg and rr present
    min_cohort_n=30,             # a cohort must have >= this many train cubes to define a climatology
    lat_bin_deg=3.0,             # level-0 cohort = season x (lat-bin, lon-bin)
    lon_bin_deg=3.0,
    lat_band_deg=6.0,            # level-1 fallback = season x lat-band
    strict_q=0.90,               # Q90 joint  -> strict tier (high purity secondary)
    broad_q=0.80,                # Q80 joint  -> broad tier (primary)
    normal_band=0.75,            # |hot_anom| and |dry_anom| <= this  -> matched-normal candidate pool
    caliper=1.5,                 # max RMS standardized NN distance for a valid match (per-feature interpretable)
    reuse_cap=5,                 # a control may back at most this many extreme cubes
    seed=42,
)
MATCH_FEATURES = (
    "doy", "lat", "lon", "lc_veg_frac", "ctx_cloud_ratio",
    "ctx_valid_frac", "ctx_ndvi_mean", "future_valid_frac",
)

_LATLON_RE = re.compile(r"_(-?\d+\.\d+)_(-?\d+\.\d+)\.nc$")
_UNITS_RE = re.compile(r"days since (\d{4})-(\d{1,2})-(\d{1,2})")
_EPOCH_FALLBACK = _dt.date(1950, 1, 1)
_MET = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
        6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}


def _met_season(month: int) -> str:
    return _MET.get(int(month), "NA")


# ----------------------------------------------------------------------------- low-level NC read
def _read_var(f: "h5py.File", name: str, tslice: slice | None = None):
    """Return (physical_values, valid_mask) honouring _FillValue/scale_factor/add_offset; None if absent.

    ``tslice`` reads only that leading-axis slice from disk (h5py lazy read) -- used to load just the
    context window of the large S2 cubes instead of the full 150-frame array.
    """
    if name not in f:
        return None, None
    d = f[name]
    raw = np.asarray(d[tslice] if tslice is not None else d[()], dtype=np.float64)
    attrs = d.attrs
    fill = attrs.get("_FillValue", None)
    scale = float(np.asarray(attrs.get("scale_factor", 1.0)).ravel()[0])
    offset = float(np.asarray(attrs.get("add_offset", 0.0)).ravel()[0])
    valid = np.isfinite(raw)
    if fill is not None:
        valid &= raw != float(np.asarray(fill).ravel()[0])
    valid &= raw != INT16_MIN_INVALID
    phys = raw * scale + offset
    phys = np.where(valid, phys, np.nan)
    return phys, valid


def _units(f: "h5py.File", name: str) -> str:
    if name in f and "units" in f[name].attrs:
        u = f[name].attrs["units"]
        return u.decode() if isinstance(u, bytes) else str(u)
    return ""


def _parse_latlon(path: str):
    m = _LATLON_RE.search(os.path.basename(path))
    return (float(m.group(1)), float(m.group(2))) if m else (math.nan, math.nan)


def _ref_epoch(units: str) -> _dt.date:
    """Parse the per-cube 'days since YYYY-MM-DD' reference (train uses a cube-local epoch, ood-t uses 1950)."""
    m = _UNITS_RE.search(units or "")
    if not m:
        return _EPOCH_FALLBACK
    try:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return _EPOCH_FALLBACK


def _target_start(f: "h5py.File"):
    """(doy, month) of the first target-window day (index CONTEXT_DAYS), honouring the per-cube time units."""
    if "time" not in f:
        return math.nan, 0
    t = np.asarray(f["time"][()], dtype=np.float64)
    if t.size <= CONTEXT_DAYS or not np.isfinite(t[CONTEXT_DAYS]):
        return math.nan, 0
    u = f["time"].attrs.get("units", b"")
    u = u.decode() if isinstance(u, bytes) else str(u)
    d = _ref_epoch(u) + _dt.timedelta(days=float(t[CONTEXT_DAYS]))
    return float(d.timetuple().tm_yday), int(d.month)


def _cube_latlon(f: "h5py.File", path: str):
    """Cube-centre lat/lon from the NC coord arrays (consistent across train & chopped layouts)."""
    la = np.asarray(f["lat"][()], dtype=np.float64) if "lat" in f else None
    lo = np.asarray(f["lon"][()], dtype=np.float64) if "lon" in f else None
    if la is not None and lo is not None and np.isfinite(la).any() and np.isfinite(lo).any():
        return float(np.nanmean(la)), float(np.nanmean(lo))
    if "latitude_eobs" in f and "longitude_eobs" in f:
        return float(np.asarray(f["latitude_eobs"][()]).ravel()[0]), float(np.asarray(f["longitude_eobs"][()]).ravel()[0])
    return _parse_latlon(path)


# ----------------------------------------------------------------------------- per-cube reads
def read_forcing(path: str) -> dict[str, Any] | None:
    """Forcing-only summary of ONE cube (eobs read only -- cheap; used for train calibration + ood-t).

    Season (target-window month), lat/lon and DOY are all derived from NC CONTENT (time units + lat/lon
    coords), NOT from the filename/folder, so train and chopped layouts share one consistent key.
    Returns None only on an unreadable file. The valid-fraction gate is applied by the caller.
    """
    season_folder = os.path.basename(os.path.dirname(path))
    try:
        with h5py.File(path, "r") as f:
            tg, _ = _read_var(f, HOT_VAR)
            tx, _ = _read_var(f, HOT_VAR_ROBUST)
            rr, _ = _read_var(f, DRY_VAR)
            doy, month = _target_start(f)
            lat, lon = _cube_latlon(f, path)
            units = {"hot": _units(f, HOT_VAR), "dry": _units(f, DRY_VAR)}
    except Exception:
        return None
    if tg is None or rr is None:
        return None
    fut_tg, fut_rr = tg[FUTURE_SLICE], rr[FUTURE_SLICE]
    fok = np.isfinite(fut_tg) & np.isfinite(fut_rr)
    n_days = int(fut_tg.shape[0])
    vfrac = float(fok.sum()) / max(1, n_days)
    hot = float(np.nanmean(fut_tg[fok])) if fok.any() else math.nan
    dry = float(np.nanmean(fut_rr[fok])) if fok.any() else math.nan
    hot_tx = math.nan
    if tx is not None:
        ftx = tx[FUTURE_SLICE]
        ftx = ftx[np.isfinite(ftx)]
        hot_tx = float(np.mean(ftx)) if ftx.size else math.nan
    return dict(
        sample_id=f"{Path(path).parent.name}/{Path(path).stem}",   # parent (season/tile) + stem => unique
        path=path, season=(f"m{month:02d}" if month else "mNA"),
        met_season=_met_season(month), season_folder=season_folder, month=month,
        lat=lat, lon=lon, doy=doy,
        hot=hot, hot_tx=hot_tx, dry=dry, future_valid_frac=vfrac, n_future_days=n_days, units=units,
    )


def read_context_features(path: str) -> dict[str, Any]:
    """Observed / pre-forcing features for matched-normal balancing (context window ONLY; no future NDVI)."""
    out = dict(lc_veg_frac=math.nan, ctx_cloud_ratio=math.nan, ctx_valid_frac=math.nan,
               ctx_ndvi_mean=math.nan, ctx_n_valid_px=0.0)
    try:
        with h5py.File(path, "r") as f:
            lc, _ = _read_var(f, "esawc_lc")
            if lc is not None:
                fin = np.isfinite(lc)
                if fin.any():
                    out["lc_veg_frac"] = float(np.isin(lc[fin].astype(int), VEG_LC_CODES).mean())
            c8, _ = _read_var(f, "s2_B8A", CONTEXT_SLICE)   # only the context window (50 frames)
            c4, _ = _read_var(f, "s2_B04", CONTEXT_SLICE)
            cdl, _ = _read_var(f, "s2_dlmask", CONTEXT_SLICE)
            if c8 is not None and c4 is not None:
                den = c8 + c4
                ndvi = np.where(np.abs(den) > 1e-6, (c8 - c4) / den, np.nan)
                valid = np.isfinite(ndvi)
                if cdl is not None:
                    valid &= np.isfinite(cdl) & (cdl == DL_CLEAR)
                out["ctx_n_valid_px"] = float(valid.sum())
                if valid.any():
                    out["ctx_ndvi_mean"] = float(np.nanmean(np.where(valid, ndvi, np.nan)))
                out["ctx_valid_frac"] = float(valid.mean())
            if cdl is not None:
                fin = np.isfinite(cdl)
                if fin.any():
                    out["ctx_cloud_ratio"] = float((cdl[fin] != DL_CLEAR).mean())
    except Exception:
        pass
    return out


# ----------------------------------------------------------------------------- cohort climatology
def _loc_bin(lat: float, lon: float, lat_deg: float, lon_deg: float) -> str:
    return f"{round(lat / lat_deg) * lat_deg:.1f},{round(lon / lon_deg) * lon_deg:.1f}"


def _lat_band(lat: float, band: float) -> str:
    return f"{round(lat / band) * band:.1f}"


def _agg(vals: list[float]) -> dict[str, float]:
    a = np.asarray([v for v in vals if np.isfinite(v)], dtype=np.float64)
    if a.size == 0:
        return dict(n=0, mean=math.nan, std=math.nan)
    return dict(n=int(a.size), mean=float(a.mean()), std=float(a.std(ddof=0)))


def build_cohorts(records: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    """Three nested climatology levels over TRAIN records (each with season/lat/lon/hot/dry)."""
    lv0: dict[str, dict[str, list[float]]] = {}
    lv1: dict[str, dict[str, list[float]]] = {}
    lv2: dict[str, dict[str, list[float]]] = {}
    for r in records:
        if not (np.isfinite(r["hot"]) and np.isfinite(r["dry"])):
            continue
        s = r["season"]
        lat, lon = r["lat"], r["lon"]
        targets = [(lv2, s)]                                    # season level: always
        if np.isfinite(lat):
            targets.append((lv1, f"{s}|band{_lat_band(lat, cfg['lat_band_deg'])}"))
            if np.isfinite(lon):
                targets.append((lv0, f"{s}|{_loc_bin(lat, lon, cfg['lat_bin_deg'], cfg['lon_bin_deg'])}"))
        for tbl, key in targets:
            d = tbl.setdefault(key, {"hot": [], "dry": []})
            d["hot"].append(r["hot"]); d["dry"].append(r["dry"])

    def finalize(tbl):
        out = {}
        for key, d in tbl.items():
            h, dr = _agg(d["hot"]), _agg(d["dry"])
            out[key] = dict(n=h["n"], hot_mean=h["mean"], hot_std=h["std"],
                            dry_mean=dr["mean"], dry_std=dr["std"])
        return out

    return {"level0": finalize(lv0), "level1": finalize(lv1), "level2": finalize(lv2)}


def resolve_cohort(season: str, lat: float, lon: float, cohorts: dict[str, Any], cfg: dict[str, Any]):
    """Finest cohort meeting min_cohort_n (with positive std). Returns (stats_dict, level_tag)."""
    min_n = int(cfg["min_cohort_n"])
    candidates = []
    if np.isfinite(lat) and np.isfinite(lon):
        candidates.append(("level0", f"{season}|{_loc_bin(lat, lon, cfg['lat_bin_deg'], cfg['lon_bin_deg'])}"))
    if np.isfinite(lat):
        candidates.append(("level1", f"{season}|band{_lat_band(lat, cfg['lat_band_deg'])}"))
    candidates.append(("level2", season))
    for lvl, key in candidates:                                # finest first
        c = cohorts.get(lvl, {}).get(key)
        if c and c["n"] >= min_n and np.isfinite(c["hot_std"]) and c["hot_std"] > 0 \
                and np.isfinite(c["dry_std"]) and c["dry_std"] > 0:
            return c, lvl
    return None, None


def anomalies(rec: dict[str, Any], cohorts: dict[str, Any], cfg: dict[str, Any]):
    """(hot_anom, dry_anom, level). Positive hot_anom = hotter; positive dry_anom = drier (rainfall deficit)."""
    c, lvl = resolve_cohort(rec["season"], rec["lat"], rec["lon"], cohorts, cfg)
    if c is None:
        return math.nan, math.nan, None
    hot_anom = (rec["hot"] - c["hot_mean"]) / c["hot_std"]
    dry_anom = (c["dry_mean"] - rec["dry"]) / c["dry_std"]   # deficit sign
    return float(hot_anom), float(dry_anom), lvl


# ----------------------------------------------------------------------------- IO helpers
def _iter_nc(root: str) -> list[str]:
    return sorted(glob.glob(os.path.join(root, "**", "*.nc"), recursive=True))


def _subsample(files: list[str], max_cubes: int) -> list[str]:
    if max_cubes <= 0 or len(files) <= max_cubes:
        return files
    idx = np.linspace(0, len(files) - 1, max_cubes).round().astype(int)
    return [files[i] for i in sorted(set(idx.tolist()))]


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write_json(obj: dict[str, Any], path: str) -> str:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    p.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


# ----------------------------------------------------------------------------- calibrate
def cmd_calibrate(args) -> int:
    cfg = dict(DEFAULTS)
    for k in cfg:
        v = getattr(args, k, None)
        if v is not None:
            cfg[k] = type(cfg[k])(v)
    files = _subsample(_iter_nc(args.train_root), args.max_cubes)
    n_total = len(files)
    records, n_read, n_gate = [], 0, 0
    for fp in files:
        r = read_forcing(fp)
        if r is None:
            continue
        n_read += 1
        if r["future_valid_frac"] < cfg["valid_fraction_min"] or not np.isfinite(r["hot"]) or not np.isfinite(r["dry"]):
            n_gate += 1
            continue
        records.append(r)
    if not records:
        raise SystemExit("calibrate: no usable train cubes after the valid-fraction gate")
    cohorts = build_cohorts(records, cfg)

    # per-train-cube anomaly -> frozen Q80/Q90 thresholds + cohort-level usage histogram
    ha, da, level_usage = [], [], {"level0": 0, "level1": 0, "level2": 0, "unresolved": 0}
    for r in records:
        h, d, lvl = anomalies(r, cohorts, cfg)
        if lvl is None:
            level_usage["unresolved"] += 1
            continue
        level_usage[lvl] += 1
        ha.append(h); da.append(d)
    ha, da = np.asarray(ha), np.asarray(da)
    thr = {
        "strict": {"hot": float(np.quantile(ha, cfg["strict_q"])), "dry": float(np.quantile(da, cfg["strict_q"]))},
        "broad": {"hot": float(np.quantile(ha, cfg["broad_q"])), "dry": float(np.quantile(da, cfg["broad_q"]))},
        "q": {"strict": cfg["strict_q"], "broad": cfg["broad_q"]},
        "note": "frozen from the TRAIN anomaly distribution; applied unchanged to OOD-t (correction 2).",
    }
    payload = {
        "kind": "hotdry_climatology_train",
        "config": cfg,
        "geometry": {"context_days": CONTEXT_DAYS, "total_days": TOTAL_DAYS,
                     "future_slice": [CONTEXT_DAYS, TOTAL_DAYS]},
        "variables": {"hot": HOT_VAR, "hot_robust": HOT_VAR_ROBUST, "dry": DRY_VAR,
                      "units": records[0]["units"]},
        "n_train_files": n_total, "n_train_read": n_read,
        "n_excluded_valid_fraction": n_gate, "n_train_used": len(records),
        "cohort_level_usage": level_usage,
        "cohort_counts": {lvl: len(cohorts[lvl]) for lvl in cohorts},
        "thresholds": thr,
        "cohorts": cohorts,
    }
    sha = _write_json(payload, args.out)
    print(f"[calibrate] files={n_total} read={n_read} gated={n_gate} used={len(records)}")
    print(f"[calibrate] cohort level usage: {level_usage}")
    print(f"[calibrate] thresholds strict(hot>={thr['strict']['hot']:.3f}, dry>={thr['strict']['dry']:.3f}) "
          f"broad(hot>={thr['broad']['hot']:.3f}, dry>={thr['broad']['dry']:.3f})")
    print(f"[calibrate] wrote {args.out}  sha256={sha[:16]}...")
    return 0


# ----------------------------------------------------------------------------- select
def _standardize(rows: list[dict[str, Any]], feats: tuple[str, ...]):
    X = np.array([[r.get(f, math.nan) for f in feats] for r in rows], dtype=np.float64)
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0)
    sd = np.where((sd > 0) & np.isfinite(sd), sd, 1.0)
    Z = (X - mu) / sd
    Z = np.where(np.isfinite(Z), Z, 0.0)
    return Z, mu, sd


def _match_normal(extreme: list[dict[str, Any]], pool: list[dict[str, Any]], cfg: dict[str, Any]):
    """Deterministic caliper nearest-neighbour on standardized MATCH_FEATURES; exact meteorological-season
    hard constraint, seeded order, reuse-capped. Distance = RMS standardized difference over features
    (caliper is per-feature-interpretable and dimension-independent)."""
    feats = MATCH_FEATURES
    allrows = extreme + pool
    Z, mu, sd = _standardize(allrows, feats)
    zext, zpool = Z[:len(extreme)], Z[len(extreme):]
    caliper, reuse_cap = float(cfg["caliper"]), int(cfg["reuse_cap"])
    nfeat = len(feats)
    used: dict[str, int] = {}
    pairs, unmatched = {}, []
    order = sorted(range(len(extreme)), key=lambda i: extreme[i]["sample_id"])  # deterministic
    for i in order:
        e = extreme[i]
        best_j, best_d = -1, math.inf
        for j, p in enumerate(pool):
            if p.get("met_season") != e.get("met_season"):
                continue
            if used.get(p["sample_id"], 0) >= reuse_cap:
                continue
            d = float(np.sqrt(np.sum((zext[i] - zpool[j]) ** 2) / nfeat))   # RMS standardized diff
            if d < best_d:
                best_d, best_j = d, j
        if best_j < 0 or best_d > caliper:
            unmatched.append(e["sample_id"])
            continue
        c = pool[best_j]
        used[c["sample_id"]] = used.get(c["sample_id"], 0) + 1
        std_diffs = {f: float((e.get(f, math.nan) - c.get(f, math.nan)) / sd[k])
                     for k, f in enumerate(feats)}
        pairs[e["sample_id"]] = {"control": c["sample_id"], "distance": best_d, "std_diffs": std_diffs}
    return pairs, unmatched, used


def _balance(extreme_ids, pairs, byid, feats):
    ext = [byid[i] for i in extreme_ids if i in pairs]
    ctl = [byid[pairs[i]["control"]] for i in extreme_ids if i in pairs]
    rep = {}
    if not ext:
        return {f: {"extreme_mean": math.nan, "control_mean": math.nan, "std_diff": math.nan} for f in feats}
    for f in feats:
        e = np.array([r.get(f, math.nan) for r in ext], float)
        c = np.array([r.get(f, math.nan) for r in ctl], float)
        pooled = float(np.nanstd(np.concatenate([e, c]))) or 1.0
        rep[f] = {"extreme_mean": float(np.nanmean(e)), "control_mean": float(np.nanmean(c)),
                  "std_diff": float((np.nanmean(e) - np.nanmean(c)) / pooled)}
    return rep


def cmd_select(args) -> int:
    climo = json.loads(Path(args.climatology).read_text(encoding="utf-8"))
    cfg = dict(climo["config"])
    for key in ("caliper", "reuse_cap", "normal_band"):                 # matching overrides (frozen before eval)
        v = getattr(args, key, None)
        if v is not None:
            cfg[key] = type(DEFAULTS[key])(v)
    cohorts, thr = climo["cohorts"], climo["thresholds"]
    climo_sha = _sha256_bytes(Path(args.climatology).read_bytes())
    files = _subsample(_iter_nc(args.ood_root), args.max_cubes)
    n_total = len(files)

    valid, n_read, n_gate = [], 0, 0
    if args.features_json:                                   # fast re-match path (no NC re-read; tuning only)
        prev = json.loads(Path(args.features_json).read_text(encoding="utf-8"))["cube_features"]
        for sid, feat in prev.items():
            valid.append({"sample_id": sid, **feat})
        n_read = len(valid)
    else:
        for fp in files:
            r = read_forcing(fp)
            if r is None:
                continue
            n_read += 1
            if r["future_valid_frac"] < cfg["valid_fraction_min"] or not np.isfinite(r["hot"]) or not np.isfinite(r["dry"]):
                n_gate += 1
                continue
            h, d, lvl = anomalies(r, cohorts, cfg)
            if lvl is None:
                n_gate += 1
                continue
            r.update(hot_anom=h, dry_anom=d, cohort_level=lvl)
            r.update(read_context_features(fp))
            valid.append(r)

    byid = {r["sample_id"]: r for r in valid}
    strict = sorted(r["sample_id"] for r in valid
                    if r["hot_anom"] >= thr["strict"]["hot"] and r["dry_anom"] >= thr["strict"]["dry"])
    broad = sorted(r["sample_id"] for r in valid
                   if r["hot_anom"] >= thr["broad"]["hot"] and r["dry_anom"] >= thr["broad"]["dry"])
    broad_set = set(broad)
    primary = args.primary_tier
    primary_ids = strict if primary == "strict" else broad

    pool = [r for r in valid if r["sample_id"] not in broad_set
            and abs(r["hot_anom"]) <= cfg["normal_band"] and abs(r["dry_anom"]) <= cfg["normal_band"]]
    extreme_rows = [byid[i] for i in primary_ids]
    pairs, unmatched, used = _match_normal(extreme_rows, pool, cfg)
    control_ids = sorted({p["control"] for p in pairs.values()})
    match_report = {
        "primary_tier": primary,
        "n_extreme": len(primary_ids), "n_matched": len(pairs), "n_unmatched": unmatched,
        "n_control_unique": len(control_ids), "pool_size": len(pool),
        "reuse_histogram": {k: v for k, v in sorted(used.items())},
        "coverage": (len(pairs) / len(primary_ids)) if primary_ids else 0.0,
        "balance_std_diff": _balance(primary_ids, pairs, byid, MATCH_FEATURES),
        "caliper": cfg["caliper"], "reuse_cap": cfg["reuse_cap"], "seed": cfg["seed"],
    }

    def feat_of(r):
        return {k: r.get(k) for k in ("season", "met_season", "lat", "lon", "doy", "hot", "dry", "hot_tx",
                                      "hot_anom", "dry_anom", "cohort_level", "future_valid_frac",
                                      "lc_veg_frac", "ctx_cloud_ratio", "ctx_valid_frac",
                                      "ctx_ndvi_mean", "ctx_n_valid_px", "path")}

    payload = {
        "kind": "hotdry_selection_oodt",
        "config": cfg, "thresholds": thr, "climatology_sha256": climo_sha,
        "primary_tier": primary,
        "n_oodt_files": n_total, "n_read": n_read,
        "n_excluded_valid_fraction_or_cohort": n_gate, "n_valid": len(valid),
        "extreme": {"strict": strict, "broad": broad},
        "matched_pairs": pairs,
        "control_ids": control_ids,
        "match_report": match_report,
        "cube_features": {r["sample_id"]: feat_of(r) for r in valid},
    }
    sha = _write_json(payload, args.out)
    print(f"[select] files={n_total} read={n_read} gated={n_gate} valid={len(valid)}")
    print(f"[select] extreme strict={len(strict)} broad={len(broad)}  primary={primary}({len(primary_ids)})")
    print(f"[select] matched={len(pairs)}/{len(primary_ids)} coverage={match_report['coverage']:.2f} "
          f"unmatched={len(unmatched)} controls_unique={len(control_ids)} pool={len(pool)}")
    print(f"[select] wrote {args.out}  sha256={sha[:16]}...")
    return 0


# ----------------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("calibrate", help="compute frozen train climatology + Q80/Q90 thresholds")
    c.add_argument("--train-root", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--max-cubes", type=int, default=0, help="deterministic subsample (0 = all; smoke only)")
    for k, v in DEFAULTS.items():
        c.add_argument(f"--{k.replace('_', '-')}", type=type(v), default=None)
    c.set_defaults(func=cmd_calibrate)

    s = sub.add_parser("select", help="apply frozen thresholds to OOD-t + build matched-normal controls")
    s.add_argument("--ood-root", required=True)
    s.add_argument("--climatology", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--primary-tier", choices=("broad", "strict"), default="broad")
    s.add_argument("--caliper", type=float, default=None, help="max RMS standardized match distance (frozen)")
    s.add_argument("--reuse-cap", type=int, default=None, help="max times a control backs distinct extremes")
    s.add_argument("--normal-band", type=float, default=None, help="|anom| band for the matched-normal pool")
    s.add_argument("--max-cubes", type=int, default=0)
    s.add_argument("--features-json", default=None,
                   help="reuse cube_features from a prior selection.json (skip NC read; matching-tuning only)")
    s.set_defaults(func=cmd_select)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
