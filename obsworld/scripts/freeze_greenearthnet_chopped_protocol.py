#!/usr/bin/env python
"""Freeze one explicit GreenEarthNet chopped evaluation track.

This script is deliberately evaluation-only. It never scans a raw
EarthNet2021x root and it never turns a chopped track into raw "ood". The
resulting manifest can be supplied to the Stage2 loader only with
"manifest_protocol=greenearthnet_cvpr2024_chopped_v1".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.earthnet_manifest import (
    GREENEARTHNET_CHOPPED_PROTOCOL_ID,
    GREENEARTHNET_CHOPPED_TRACKS,
    build_greenearthnet_chopped_manifest,
    manifest_protocol_spec,
    write_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze one explicit GreenEarthNet chopped track for formal evaluation."
    )
    parser.add_argument(
        "--eval-root",
        required=True,
        help="Directory containing explicit val_chopped/ood-t_chopped tracks.",
    )
    parser.add_argument(
        "--track",
        required=True,
        choices=GREENEARTHNET_CHOPPED_TRACKS,
        help="One public chopped track; no raw IID/OOD aliases are accepted.",
    )
    parser.add_argument("--output", required=True, help="Output JSON manifest path.")
    parser.add_argument(
        "--hash-mode",
        choices=("none", "sha256"),
        default="sha256",
        help="Per-file hash mode; sha256 is required for a formal paper run.",
    )
    parser.add_argument(
        "--audit-report",
        help=(
            "Optional report from scripts/audit_greenearthnet_layout.py. When "
            "provided, this command checks its recorded evaluation root and "
            "track count before freezing the manifest."
        ),
    )
    return parser.parse_args()


def _validate_audit(path: str | Path, *, eval_root: Path, track: str) -> None:
    report_path = Path(path).expanduser().resolve()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if payload.get("candidate_protocol") != "greenearthnet_cvpr2024_v1":
        raise ValueError(f"Unexpected GreenEarthNet audit report: {report_path}")
    if Path(str(payload.get("evaluation_root", ""))).expanduser().resolve() != eval_root:
        raise ValueError("Audit report belongs to a different --eval-root")
    groups = payload.get("greenearthnet_track_groups")
    if not isinstance(groups, dict):
        raise ValueError("Audit report has no track-group inventory")
    group = groups.get(track)
    if not isinstance(group, dict) or int(group.get("num_netcdf_files", 0)) <= 0:
        raise ValueError(f"Audit report does not confirm a nonempty {track} track")


def main() -> int:
    args = parse_args()
    eval_root = Path(args.eval_root).expanduser().resolve()
    if args.audit_report:
        _validate_audit(args.audit_report, eval_root=eval_root, track=args.track)
    manifest = build_greenearthnet_chopped_manifest(
        eval_root,
        args.track,
        hash_mode=args.hash_mode,
        metadata={
            "evaluation_track": args.track,
            "protocol_note": (
                "Explicit GreenEarthNet chopped evaluation track; it must not be "
                "mixed with raw EarthNet2021x IID/OOD or legacy EarthNetScore."
            ),
        },
    )
    output = write_manifest(manifest, args.output)
    spec = manifest_protocol_spec(GREENEARTHNET_CHOPPED_PROTOCOL_ID)
    result = {
        "manifest": str(output),
        "dataset": spec["dataset"],
        "protocol": GREENEARTHNET_CHOPPED_PROTOCOL_ID,
        "track": args.track,
        "num_files": manifest["num_files"],
        "files_sha256": manifest["files_sha256"],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
