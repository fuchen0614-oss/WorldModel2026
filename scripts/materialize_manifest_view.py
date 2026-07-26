#!/usr/bin/env python
"""scripts/materialize_manifest_view.py -- training-side SYMLINK view of manifest-selected cubes (no copy).

Some tools (e.g. the dataset class that globs a directory) want a folder that contains exactly the
selected cubes. This creates that folder out of SYMLINKS into the existing dataset -- it never copies
NetCDF (correction 1). Root-relative manifest paths are preserved under the view root, so a globbing
loader sees the same ``ood-t_chopped/<season>/<cube>.nc`` layout.

Usage:
  python scripts/materialize_manifest_view.py --dataset-root ROOT --out-dir VIEW \
      --manifest hotdry_manifest.json --manifest matched_normal_manifest.json
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (  # noqa: E402
    GREENEARTHNET_CHOPPED_PROTOCOL_ID, load_manifest_files, resolve_manifest_root,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-root", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--manifest", action="append", required=True, help="repeatable; chopped manifest JSON")
    ap.add_argument("--expected-split", default="ood-t_chopped")
    ap.add_argument("--relative-to-track", action="store_true",
                    help="drop the leading track dir in the view (view/<season>/<cube> instead of "
                         "view/ood-t_chopped/<season>/<cube>)")
    args = ap.parse_args()

    root = resolve_manifest_root(args.dataset_root, protocol=GREENEARTHNET_CHOPPED_PROTOCOL_ID)
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    linked, skipped, total = 0, 0, 0
    seen: set[str] = set()
    for man in args.manifest:
        files = load_manifest_files(man, args.dataset_root, expected_split=args.expected_split,
                                    expected_protocol=GREENEARTHNET_CHOPPED_PROTOCOL_ID, verify_exists=True)
        for src in files:
            total += 1
            rel = src.resolve().relative_to(root)
            if args.relative_to_track and rel.parts and rel.parts[0] == args.expected_split:
                rel = Path(*rel.parts[1:])
            dst = out / rel
            key = str(dst)
            if key in seen:                                   # same cube in >1 manifest -> one link
                skipped += 1
                continue
            seen.add(key)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.is_symlink() or dst.exists():
                try:
                    dst.unlink()
                except OSError:
                    pass
            os.symlink(src.resolve(), dst)
            linked += 1
    print(f"[view] manifests={len(args.manifest)} entries={total} symlinked={linked} deduped={skipped} -> {out}")
    print(f"[view] NOTE: symlinks only; no NetCDF copied. Point the loader/evaluator at {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
