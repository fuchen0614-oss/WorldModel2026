#!/usr/bin/env python
"""scripts/build_extreme_audit_protocol.py -- freeze the OOD-t hot-dry predictive-state audit PROTOCOL.

Emits ONLY small JSON artefacts (committable to Git). It NEVER copies NetCDF data (correction 1):
the training server already has the full dataset; the evaluator resolves root-relative manifest paths
via ``--dataset-root``. Outputs (all under ``--out-dir``):

  hotdry_manifest.json          selected extreme cubes (primary tier), chopped-subset schema
  matched_normal_manifest.json  unique matched-normal control cubes, chopped-subset schema
  climatology_train.json        train cohort climatology (copied from calibrate)
  thresholds.json               frozen train-derived Q80/Q90 hot/dry thresholds
  protocol.json                 frozen protocol parameters (geometry, variables, matching, gates)
  provenance.json               git commit, selector/builder version, input SHAs, seed, frozen_utc
  MANIFEST.SHA256               sha256 of every emitted artefact (bundle integrity)
  README.md                     what this is + how the training end consumes it

Manifests use the GreenEarthNet chopped subset schema (loadable by data.earthnet_manifest.load_manifest_files
with expected_protocol=greenearthnet chopped, expected_split=ood-t_chopped). Extra selection detail lives in a
top-level ``audit`` block; per-file records stay canonical {path,size_bytes,sample_id,sha256}.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (  # noqa: E402  (pure, torch-free)
    GREENEARTHNET_CHOPPED_DATASET_ID, GREENEARTHNET_CHOPPED_PROTOCOL_ID, GREENEARTHNET_CHOPPED_TRACKS,
    MANIFEST_SCHEMA_VERSION, records_digest, resolve_manifest_root, sha256_file,
)

BUILDER_VERSION = "extreme_audit_protocol_v1"
TRACK = "ood-t_chopped"


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "UNKNOWN"


def _git_dirty() -> bool:
    try:
        out = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"],
                                      text=True, stderr=subprocess.DEVNULL)
        return bool(out.strip())
    except Exception:
        return True


def _write_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _rel_of(abs_path: str, root: Path) -> str:
    return Path(abs_path).resolve().relative_to(root).as_posix()


def _chopped_subset_manifest(root: Path, abs_paths: list[str], audit_block: dict, hash_mode: str) -> dict:
    """Build a GreenEarthNet chopped SUBSET manifest (schema v2) from an explicit list of absolute paths."""
    if hash_mode not in ("none", "sha256"):
        raise ValueError("hash_mode must be 'none' or 'sha256'")
    records, seen = [], set()
    for p in sorted({str(Path(x).resolve()) for x in abs_paths}):
        pp = Path(p)
        rel = pp.relative_to(root).as_posix()
        if not rel.startswith(f"{TRACK}/"):
            raise ValueError(f"selected cube is not under {TRACK}/: {rel}")
        if rel in seen:
            continue
        seen.add(rel)
        rec = {"path": rel, "size_bytes": int(pp.stat().st_size), "sample_id": pp.stem}
        if hash_mode == "sha256":
            rec["sha256"] = sha256_file(pp)
        records.append(rec)
    records.sort(key=lambda r: r["path"])
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset": GREENEARTHNET_CHOPPED_DATASET_ID,
        "protocol": GREENEARTHNET_CHOPPED_PROTOCOL_ID,
        "split": TRACK, "role": TRACK, "source_splits": [TRACK],
        "hash_mode": hash_mode, "num_files": len(records), "files": records,
        "files_sha256": records_digest(records),
        "audit": audit_block,
    }
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selection", required=True, help="selection.json from hotdry_selector select")
    ap.add_argument("--climatology", required=True, help="climatology_train.json from hotdry_selector calibrate")
    ap.add_argument("--dataset-root", required=True, help="earthnet2021x root (or its parent)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--primary-tier", choices=("broad", "strict"), default=None,
                    help="override selection's primary tier for the hotdry manifest")
    ap.add_argument("--hash-mode", choices=("none", "sha256"), default="sha256")
    ap.add_argument("--frozen-utc", default=None, help="ISO timestamp to freeze into provenance (default: now)")
    args = ap.parse_args()

    if TRACK not in GREENEARTHNET_CHOPPED_TRACKS:
        raise SystemExit(f"internal: {TRACK} is not a valid chopped track")
    sel = json.loads(Path(args.selection).read_text(encoding="utf-8"))
    climo = json.loads(Path(args.climatology).read_text(encoding="utf-8"))
    root = resolve_manifest_root(args.dataset_root, protocol=GREENEARTHNET_CHOPPED_PROTOCOL_ID)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    primary = args.primary_tier or sel.get("primary_tier", "broad")
    feats = sel["cube_features"]
    strict_ids, broad_ids = sel["extreme"]["strict"], sel["extreme"]["broad"]
    primary_ids = strict_ids if primary == "strict" else broad_ids
    pairs = sel["matched_pairs"]                        # extreme_sample_id -> {control, distance, std_diffs}
    control_ids = sel["control_ids"]

    def absp(sid: str) -> str:
        return feats[sid]["path"]

    # ---- hotdry manifest (primary-tier extreme cubes) ----
    tier_by_path = {}
    for sid in primary_ids:
        rel = _rel_of(absp(sid), root)
        tier_by_path[rel] = "strict" if sid in set(strict_ids) else "broad"
    hotdry_audit = {
        "kind": "hotdry_extreme", "primary_tier": primary,
        "n_strict": len(strict_ids), "n_broad": len(broad_ids), "n_primary": len(primary_ids),
        "tier_by_path": tier_by_path,
        "thresholds": climo["thresholds"], "climatology_sha256": sel.get("climatology_sha256"),
        "selection_note": "forcing-only; NO future NDVI / model / prediction-error / checkpoint used.",
    }
    hotdry_manifest = _chopped_subset_manifest(root, [absp(s) for s in primary_ids], hotdry_audit, args.hash_mode)

    # ---- matched-normal manifest (unique control cubes) + pairing ----
    pairs_by_path = {}
    for e_sid, info in pairs.items():
        if e_sid not in set(primary_ids):
            continue
        pairs_by_path[_rel_of(absp(e_sid), root)] = {
            "control_path": _rel_of(absp(info["control"]), root),
            "distance": info["distance"], "std_diffs": info["std_diffs"],
        }
    used_control_ids = sorted({pairs[e]["control"] for e in primary_ids if e in pairs})
    normal_audit = {
        "kind": "matched_normal_control", "primary_tier": primary,
        "n_control_unique": len(used_control_ids), "n_pairs": len(pairs_by_path),
        "pairs_extreme_to_control": pairs_by_path,
        "match_report": sel["match_report"],
    }
    normal_manifest = _chopped_subset_manifest(root, [absp(s) for s in used_control_ids], normal_audit, args.hash_mode)

    # ---- protocol + thresholds + provenance ----
    protocol = {
        "kind": "extreme_hotdry_state_audit_protocol", "builder_version": BUILDER_VERSION,
        "track": TRACK, "primary_tier": primary,
        "geometry": climo.get("geometry"), "variables": climo.get("variables"),
        "config": climo.get("config"), "matching_features": [
            "doy", "lat", "lon", "lc_veg_frac", "ctx_cloud_ratio", "ctx_valid_frac",
            "ctx_ndvi_mean", "future_valid_frac"],
        "matching_hard_constraint": "meteorological_season (DJF/MAM/JJA/SON)",
        "internal_vs_external": {
            "this_protocol": "forcing-only OOD-t hot-dry subset -- INTERNAL state stress test",
            "not_this": "EarthNet2021 extreme-2018 EO-WM external protocol (raw NPZ+CSV); "
                        "no strict same-table reproduction is claimed here.",
        },
        "counts": {"n_strict": len(strict_ids), "n_broad": len(broad_ids),
                   "n_primary": len(primary_ids), "n_control_unique": len(used_control_ids)},
    }
    thresholds = {"kind": "frozen_thresholds", **climo["thresholds"],
                  "climatology_sha256": sel.get("climatology_sha256")}
    provenance = {
        "kind": "provenance", "builder_version": BUILDER_VERSION, "selector_kind": sel.get("kind"),
        "git_commit": _git_commit(), "git_dirty": _git_dirty(),
        "frozen_utc": args.frozen_utc or _dt.datetime.utcnow().isoformat() + "Z",
        "dataset_root_basename": root.name,
        "inputs": {
            "selection_json_sha256": hashlib.sha256(Path(args.selection).read_bytes()).hexdigest(),
            "climatology_json_sha256": hashlib.sha256(Path(args.climatology).read_bytes()).hexdigest(),
        },
        "seed": climo.get("config", {}).get("seed"),
        "n_train_used": climo.get("n_train_used"), "n_train_excluded": climo.get("n_excluded_valid_fraction"),
        "n_oodt_valid": sel.get("n_valid"), "n_oodt_excluded": sel.get("n_excluded_valid_fraction_or_cohort"),
    }

    # ---- write artefacts + integrity ----
    _write_json(hotdry_manifest, out / "hotdry_manifest.json")
    _write_json(normal_manifest, out / "matched_normal_manifest.json")
    _write_json(climo, out / "climatology_train.json")
    _write_json(thresholds, out / "thresholds.json")
    _write_json(protocol, out / "protocol.json")
    _write_json(provenance, out / "provenance.json")
    (out / "README.md").write_text(_readme(protocol, provenance), encoding="utf-8")

    artefacts = ["hotdry_manifest.json", "matched_normal_manifest.json", "climatology_train.json",
                 "thresholds.json", "protocol.json", "provenance.json", "README.md"]
    lines = []
    for name in sorted(artefacts):
        digest = hashlib.sha256((out / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (out / "MANIFEST.SHA256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[protocol] primary={primary} n_primary={len(primary_ids)} (strict={len(strict_ids)} broad={len(broad_ids)}) "
          f"n_control_unique={len(used_control_ids)} pairs={len(pairs_by_path)}")
    print(f"[protocol] hotdry_manifest files_sha256={hotdry_manifest['files_sha256'][:16]}...")
    print(f"[protocol] normal_manifest files_sha256={normal_manifest['files_sha256'][:16]}...")
    print(f"[protocol] wrote {len(artefacts)} artefacts + MANIFEST.SHA256 -> {out}")
    return 0


def _readme(protocol: dict, provenance: dict) -> str:
    c = protocol["counts"]
    return (
        "# OOD-t hot-dry predictive-state audit protocol (FROZEN)\n\n"
        f"- git_commit: `{provenance['git_commit']}` (dirty={provenance['git_dirty']})\n"
        f"- frozen_utc: {provenance['frozen_utc']}\n"
        f"- primary tier: **{protocol['primary_tier']}**  "
        f"(strict={c['n_strict']}, broad={c['n_broad']}, primary={c['n_primary']}, "
        f"control_unique={c['n_control_unique']})\n\n"
        "## What this is\n"
        "Forcing-only extreme hot-dry subset of `ood-t_chopped` (INTERNAL state stress test) plus a\n"
        "season/location/quality matched-normal control. Selection used ONLY future-weather forcing and\n"
        "observed pre-forcing context -- never future NDVI, model output, prediction error, or a checkpoint.\n"
        "Thresholds were frozen from the TRAIN climatology before any OOD-t scoring.\n\n"
        "## Training-end usage (no re-selection; existing data only)\n"
        "1. Verify: `sha256sum -c MANIFEST.SHA256` and check `num_files` / `files_sha256` in each manifest.\n"
        "2. The evaluator reads the manifests directly and resolves root-relative paths via `--dataset-root`\n"
        "   (or materialize a symlink view with `scripts/materialize_manifest_view.py`). No NetCDF is copied.\n\n"
        "## NOT this\n"
        "The EarthNet2021 extreme-2018 EO-WM external protocol (raw NPZ+CSV) is a SEPARATE track; no strict\n"
        "same-table reproduction is claimed until its window mapping is verified.\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
