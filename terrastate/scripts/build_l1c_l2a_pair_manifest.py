#!/usr/bin/env python
"""plan-b-pvt · Stage1.8 prep: build an L1C/L2A PAIRED manifest from SSL4EO-S12.

CPU-only. Produces the paired sample list for phi factorization (Table 2 / Fig 3).
Pointer manifest (shard + member key + season), no pixels extracted — the training
loader re-reads bands[season][[1,2,3,8]] via the existing zarr path.

Pairing = tar `__key__` (member filename minus .zarr.zip), the same way S1GRD↔S2L2A
is paired (proven 512/512). Because S2L1C↔S2L2A index-alignment is NOT code-proven,
this script VERIFIES per-member key equality and the band order on the first shard
pair, and falls back to a key-join if positional zip mismatches.

Usage (server, CPU, parallel to other work):
  conda activate WorldModel
  python scripts/build_l1c_l2a_pair_manifest.py \
    --ssl4eo-root /csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1 \
    --split train --cap 6000 \
    --output artifacts/plan_b/ssl4eo_l1c_l2a_pairs.json
"""
from __future__ import annotations

import argparse
import io
import json
import tarfile
import tempfile
from pathlib import Path

COMMON_BAND_IDX = [1, 2, 3, 8]          # B02,B03,B04,B8A in both L1C(13) and L2A(12)
COMMON_BAND_NAMES = ["B02", "B03", "B04", "B8A"]


def member_key(name: str) -> str:
    return name.split("/")[-1].replace(".zarr.zip", "")


def read_band_names(tar_path: Path):
    """Extract the first .zarr.zip member and return its `band` string list + bands shape."""
    import zarr
    with tarfile.open(tar_path) as tf:
        for m in tf:
            if not m.name.endswith(".zarr.zip"):
                continue
            data = tf.extractfile(m).read()
            with tempfile.NamedTemporaryFile(suffix=".zarr.zip") as tmp:
                tmp.write(data); tmp.flush()
                store = zarr.storage.ZipStore(tmp.name, mode="r")
                root = zarr.open(store, mode="r")
                band = [str(b) for b in root["band"][:]] if "band" in root else None
                shape = tuple(root["bands"].shape)
                store.close()
            return band, shape
    return None, None


def sorted_members(tf: tarfile.TarFile):
    return sorted([m.name for m in tf.getmembers() if m.name.endswith(".zarr.zip")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ssl4eo-root", required=True)
    ap.add_argument("--split", default="train")
    ap.add_argument("--cap", type=int, default=6000, help="max (location,season) rows")
    ap.add_argument("--seasons", type=int, default=4)
    ap.add_argument("--output", default="artifacts/plan_b/ssl4eo_l1c_l2a_pairs.json")
    args = ap.parse_args()

    root = Path(args.ssl4eo_root) / args.split
    l1c_tars = sorted((root / "S2L1C").glob("*.tar"))
    l2a_tars = sorted((root / "S2L2A").glob("*.tar"))
    print(f"[enum] S2L1C tars={len(l1c_tars)}  S2L2A tars={len(l2a_tars)}")
    assert l1c_tars and l2a_tars, "missing S2L1C or S2L2A tars"
    assert len(l1c_tars) == len(l2a_tars), "L1C/L2A shard counts differ"
    for a, b in zip(l1c_tars, l2a_tars):
        assert a.name == b.name, f"shard basename mismatch: {a.name} vs {b.name}"

    # --- verify band order on the first shard pair ---
    l1c_bands, l1c_shape = read_band_names(l1c_tars[0])
    l2a_bands, l2a_shape = read_band_names(l2a_tars[0])
    print(f"[verify] L1C bands={l1c_bands} shape={l1c_shape}")
    print(f"[verify] L2A bands={l2a_bands} shape={l2a_shape}")
    for bands, tag in [(l1c_bands, "L1C"), (l2a_bands, "L2A")]:
        if bands is not None:
            got = [bands[i] for i in COMMON_BAND_IDX]
            assert got == COMMON_BAND_NAMES, (
                f"{tag} band order mismatch at {COMMON_BAND_IDX}: got {got}, "
                f"expected {COMMON_BAND_NAMES}. Fix COMMON_BAND_IDX before training.")
    print(f"[verify] common bands {COMMON_BAND_IDX} == {COMMON_BAND_NAMES} in both ✓")

    # --- stream shard pairs, match members by key ---
    rows, mismatches, scanned = [], 0, 0
    per_season = [0] * args.seasons
    for tl1c, tl2a in zip(l1c_tars, l2a_tars):
        with tarfile.open(tl1c) as f1, tarfile.open(tl2a) as f2:
            m1, m2 = sorted_members(f1), sorted_members(f2)
        # positional zip after sort; guard by key equality, fall back to key-join
        if [member_key(x) for x in m1] == [member_key(x) for x in m2]:
            pairs = list(zip(m1, m2))
        else:
            d2 = {member_key(x): x for x in m2}
            pairs = [(x, d2[member_key(x)]) for x in m1 if member_key(x) in d2]
            mismatches += len(m1) - len(pairs)
        for a, b in pairs:
            k = member_key(a)
            scanned += 1
            for s in range(args.seasons):
                rows.append({
                    "shard": tl1c.name, "member_key": k, "season": s,
                    "l1c_path": str(tl1c), "l2a_path": str(tl2a),
                    "l1c_member": a, "l2a_member": b,
                    "common_band_idx": COMMON_BAND_IDX,
                    "common_band_names": COMMON_BAND_NAMES,
                })
                per_season[s] += 1
                if len(rows) >= args.cap:
                    break
            if len(rows) >= args.cap:
                break
        if len(rows) >= args.cap:
            break

    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=0))
    stats = {
        "split": args.split, "n_rows": len(rows), "locations_scanned": scanned,
        "key_mismatches": mismatches, "per_season": per_season,
        "l1c_bands": l1c_bands, "l2a_bands": l2a_bands,
        "common_band_idx": COMMON_BAND_IDX, "cap": args.cap,
    }
    Path(str(out).replace(".json", "_stats.json")).write_text(json.dumps(stats, indent=2))
    print(f"[done] rows={len(rows)}  per_season={per_season}  key_mismatches={mismatches}")
    print(f"[done] manifest={out}")
    print(f"[done] stats={str(out).replace('.json', '_stats.json')}")


if __name__ == "__main__":
    main()
