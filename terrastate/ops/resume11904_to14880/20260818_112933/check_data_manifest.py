#!/usr/bin/env python
"""M0 data-identity proof (read-only).

The original run's args recorded train_dir=/tmp/zjliu17_mix_stage_v2/train and
val_dir=/tmp/zjliu17_mix_stage_v2/val_chopped -- a staging directory that no longer
exists.  Before the persistent roots under TrainData/GreenEarthNet may be used for an
EXACT resume we must prove they carry the same cube identity as the frozen caches:

    data_manifest_sha256 = SHA256 over sorted (relpath, size_bytes) pairs
                           (train/terrastate_v2_common.data_manifest_sha256)

Expected (from the checkpoint `sha` block AND the cache sidecars):
    train : 17c645d92e9dd4c38ce5bf14a412115c5f6622109cff3c19118b098e604b2554
    val   : 555d44c0d59ab3902cf7d929ca86ce8bf4e3ce7cfda66c1c72b45a2ed3fd76c9

A match proves the relative-path set AND every file size are identical, hence the
future-state cache keys (relpaths) resolve under the new root.  Mismatch => FAIL CLOSED
(do NOT regenerate a "similar" dataset).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

EXPECT = {
    "train": "17c645d92e9dd4c38ce5bf14a412115c5f6622109cff3c19118b098e604b2554",
    "val": "555d44c0d59ab3902cf7d929ca86ce8bf4e3ce7cfda66c1c72b45a2ed3fd76c9",
}
ROOTS = {
    "train": "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/train",
    "val": "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/val_chopped",
}
N_EXPECT = {"train": 23816, "val": 952}


def relpath_of(filepath: str, root) -> str:
    """Verbatim copy of train.terrastate_v2_common.relpath_of (no torch import)."""
    if root is None:
        return os.path.basename(str(filepath))
    try:
        rp = os.path.relpath(str(filepath), str(root))
    except ValueError:
        return os.path.basename(str(filepath))
    if rp.startswith(".."):
        return os.path.basename(str(filepath))
    return rp


def data_manifest_sha256(filepaths, root) -> str:
    """Verbatim copy of train.terrastate_v2_common.data_manifest_sha256."""
    h = hashlib.sha256()
    rows = []
    for fp in filepaths:
        relp = relpath_of(fp, root)
        try:
            sz = os.path.getsize(fp)
        except OSError:
            sz = -1
        rows.append((relp, sz))
    for relp, sz in sorted(rows):
        h.update(relp.encode())
        h.update(str(sz).encode())
    return h.hexdigest()


def main():
    out = {}
    ok = True
    for split, root in ROOTS.items():
        folder = Path(root)
        # dataset identity is built by GreenEarthNetContextformerDataset as
        # sorted(folder.glob("**/*.nc")) -- mirror it exactly.
        fps = sorted(folder.glob("**/*.nc"))
        sha = data_manifest_sha256([str(p) for p in fps], root)
        match = sha == EXPECT[split]
        count_match = len(fps) == N_EXPECT[split]
        ok = ok and match and count_match
        out[split] = {
            "root": root,
            "n_cubes": len(fps),
            "n_cubes_expected": N_EXPECT[split],
            "n_cubes_match": count_match,
            "data_manifest_sha256": sha,
            "data_manifest_sha256_expected": EXPECT[split],
            "match": match,
            "first_relpath": relpath_of(str(fps[0]), root) if fps else None,
            "last_relpath": relpath_of(str(fps[-1]), root) if fps else None,
        }
        print(f"[{split}] n={len(fps)} (expect {N_EXPECT[split]}) sha={sha} "
              f"match={match}", flush=True)
    out["all_match"] = ok
    dest = Path(__file__).resolve().parent / "data_manifest_check.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"wrote {dest}; all_match={ok}", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
