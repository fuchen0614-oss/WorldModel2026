#!/usr/bin/env python
"""plan-b-pvt · Stage1.8 cache: extract paired L1C/L2A 4-band arrays to local npz.

The pointer manifest (build_l1c_l2a_pair_manifest.py) records shard/member/season.
Reading them on-the-fly per __getitem__ would re-scan tars every time (too slow), so
this shard-grouped pass extracts each pair's 4 common bands ([1,2,3,8]=B02/B03/B04/B8A,
center-cropped 264->256) ONCE and writes <cache>/<key>_s<season>.npz {l1c,l2a} int16.

CPU-only. Run after the manifest, before Stage1.8 training.
  python scripts/cache_l1c_l2a_pairs.py \
    --manifest artifacts/plan_b/ssl4eo_l1c_l2a_pairs.json \
    --cache-dir /tmp/zjliu17_l1c_l2a_cache
"""
from __future__ import annotations

import argparse
import json
import tarfile
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np

CROP_START, CROP_SIZE = 4, 256   # 264 -> 256 center crop (matches ssl4eo readers)


def member_key(name: str) -> str:
    return name.split("/")[-1].replace(".zarr.zip", "")


def read_bands(tf: tarfile.TarFile, member_name: str) -> np.ndarray:
    """Return bands array [4_seasons, C, 264, 264] from a .zarr.zip tar member."""
    import zarr
    data = tf.extractfile(member_name).read()
    with tempfile.NamedTemporaryFile(suffix=".zarr.zip") as tmp:
        tmp.write(data); tmp.flush()
        store = zarr.storage.ZipStore(tmp.name, mode="r")
        bands = np.array(zarr.open(store, mode="r")["bands"])
        store.close()
    return bands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--band-idx", type=int, nargs="+", default=[1, 2, 3, 8])
    args = ap.parse_args()

    rows = json.loads(Path(args.manifest).read_text())
    cache = Path(args.cache_dir); cache.mkdir(parents=True, exist_ok=True)
    idx = list(args.band_idx)

    # group manifest rows by shard-pair, and per member collect the needed seasons
    groups: dict = defaultdict(lambda: defaultdict(lambda: {"seasons": set(), "l1c": None, "l2a": None}))
    for r in rows:
        g = groups[(r["l1c_path"], r["l2a_path"])][r["member_key"]]
        g["seasons"].add(int(r["season"])); g["l1c"] = r["l1c_member"]; g["l2a"] = r["l2a_member"]

    written = 0
    for (l1c_path, l2a_path), members in groups.items():
        with tarfile.open(l1c_path) as f1, tarfile.open(l2a_path) as f2:
            n1 = {member_key(m.name): m.name for m in f1.getmembers() if m.name.endswith(".zarr.zip")}
            n2 = {member_key(m.name): m.name for m in f2.getmembers() if m.name.endswith(".zarr.zip")}
            for key, info in members.items():
                b1 = read_bands(f1, n1[key])   # (4, 13, 264, 264)
                b2 = read_bands(f2, n2[key])   # (4, 12, 264, 264)
                sl = (slice(CROP_START, CROP_START + CROP_SIZE),) * 2
                for s in sorted(info["seasons"]):
                    l1c = b1[s][idx][:, sl[0], sl[1]].astype("int16")   # (4,256,256)
                    l2a = b2[s][idx][:, sl[0], sl[1]].astype("int16")
                    np.savez(cache / f"{key}_s{s}.npz", l1c=l1c, l2a=l2a)
                    written += 1
        print(f"[cache] shard {Path(l1c_path).name}: cumulative {written}", flush=True)

    Path(cache / "_cache_stats.json").write_text(json.dumps(
        {"n_written": written, "band_idx": idx, "crop": CROP_SIZE, "manifest": args.manifest}, indent=2))
    print(f"[done] cached {written} paired samples -> {cache}")


if __name__ == "__main__":
    main()
