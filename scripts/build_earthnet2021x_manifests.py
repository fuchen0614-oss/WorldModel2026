#!/usr/bin/env python
"""Build deterministic split manifests for formal GreenEarthNet runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (  # noqa: E402
    SPLIT_CANDIDATES,
    build_manifest,
    write_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze exact EarthNet2021x files per physical split/official track."
    )
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "iid", "ood-t"],
        choices=sorted(SPLIT_CANDIDATES),
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--hash-mode",
        choices=("none", "sha256"),
        default="none",
        help="sha256 verifies file contents but is slow on network storage.",
    )
    parser.add_argument("--pattern", default="**/*.nc")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    failed = False
    summary = {}
    for split in args.splits:
        manifest = build_manifest(
            args.root,
            split,
            hash_mode=args.hash_mode,
            pattern=args.pattern,
        )
        output = write_manifest(manifest, output_dir / f"{split}.json")
        summary[split] = {
            "path": str(output),
            "num_files": manifest["num_files"],
            "files_sha256": manifest["files_sha256"],
        }
        if manifest["num_files"] == 0:
            failed = True

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
