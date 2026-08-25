#!/usr/bin/env python
"""Freeze the launch manifest for the 6 formal E0 jobs.  Refuses to overwrite an existing one.

Writes launch_manifest.json (mode 0444) pinning, for every job: the resolved checkpoint path
+ file SHA, evaluator path + SHA, manifest/protocol SHAs, the exact argv, the GPU, and a
unique output dir.  GPU 6-7 are deliberately absent.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(__file__).resolve().parent
TS_ROOT = OPS.parents[2]
OUT = OPS / "launch_manifest.json"
PY = "/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python"

DATA_ROOT = Path("/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet")
VAL_DIR = DATA_ROOT / "val_chopped"
OODT_DIR = DATA_ROOT / "ood-t_chopped"
VAL_MAN = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb/artifacts/protocols/"
               "b4_eval/val_chopped.manifest.json")
OODT_MAN = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb/evaluations/"
                "greenearthnet_oodt_20260719_214234/greenearthnet_oodt_chopped_manifest.json")
VAL_MAN_SHA = "d9bd91d6e2aafbf66b38afca7576516823fc710b6cc3ca44ea25d2e31152bf8e"
OODT_MAN_SHA = "58c8d64897193e9cffff5bc6c8524909707ebae5376b5d4dee68597ef08e1e49"
Q3_PROTO = TS_ROOT / "artifacts/protocols/extreme_audit_oodt_v1"

Q1Q2_EVAL = TS_ROOT / "eval/eval_b4_exclusive_contract.py"
Q3_EVAL = TS_ROOT / "eval/extreme_state_audit.py"

ANCHOR_ALIAS = "terrastate/v2/default-training-anchor"
LEGACY_ID = "terrastate/v2/legacy-boundary11904@v1"
ANCHOR_SHA = "a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f"
LEGACY_SHA = "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve(logical: str, alias: bool = False) -> str:
    cmd = [PY, str(TS_ROOT / "tools/resolve_artifact.py"), logical]
    if alias:
        cmd.append("--alias")
    r = subprocess.run(cmd, cwd=TS_ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"resolver rc={r.returncode} for {logical}: {r.stderr[:300]}")
    return r.stdout.strip()


def main() -> int:
    if OUT.exists():
        print(f"REFUSING: {OUT} already exists (a frozen manifest is never silently rewritten).")
        print("  To change it, move the old one to launch_manifest.rejected_<why>.json first")
        print("  and record why in STATUS.md.")
        return 2

    anchor_ck = Path(resolve(ANCHOR_ALIAS, alias=True))
    legacy_ck = Path(resolve(LEGACY_ID))
    got_a, got_l = sha256_file(anchor_ck), sha256_file(legacy_ck)
    if got_a != ANCHOR_SHA:
        raise SystemExit(f"anchor SHA drift: {got_a}")
    if got_l != LEGACY_SHA:
        raise SystemExit(f"legacy SHA drift: {got_l}")
    for p, want, label in ((VAL_MAN, VAL_MAN_SHA, "validation"),
                           (OODT_MAN, OODT_MAN_SHA, "ood-t")):
        g = sha256_file(p)
        if g != want:
            raise SystemExit(f"{label} manifest SHA drift: {g}")

    # Q3 protocol gate: verify the frozen MANIFEST.SHA256 inside the protocol dir
    r = subprocess.run(["sha256sum", "-c", "MANIFEST.SHA256"], cwd=Q3_PROTO,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"Q3 protocol gate FAILED:\n{r.stdout}\n{r.stderr}")
    q3_gate = [l for l in r.stdout.strip().splitlines()]

    runs = OPS / "runs"
    jobs = []

    def q1q2(name: str, gpu: int, ck: Path, ck_sha: str, split: str,
             data_dir: Path, man: Path, man_sha: str, man_label: str) -> dict:
        od = runs / name
        return {
            "name": name, "gpu": gpu, "kind": "q1q2",
            "checkpoint_path": str(ck), "checkpoint_sha256": ck_sha,
            "evaluator": str(Q1Q2_EVAL.relative_to(TS_ROOT)),
            "evaluator_sha256": sha256_file(Q1Q2_EVAL),
            "manifest_shas": [[man_label, str(man), man_sha]],
            "output_dir": str(od), "log": str(od.parent / f"{name}.log"),
            "pid_file": str(od.parent / f"{name}.pid"),
            "expected_targets": 952 if split == "val" else 1904,
            "command": [
                PY, str(Q1Q2_EVAL),
                "--ckpt", str(ck),
                "--val-dir", str(data_dir),
                "--data-manifest", str(man),
                "--dataset-root", str(DATA_ROOT),
                "--split", split,
                "--sections", "q1q2",
                "--batch-size", "1",
                "--num-data-workers", "2",
                "--workers", "4",
                "--device", "cuda",
                "--output-dir", str(od),
            ],
        }

    def q3(name: str, gpu: int, ck: Path, ck_sha: str) -> dict:
        od = runs / name
        return {
            "name": name, "gpu": gpu, "kind": "q3",
            "checkpoint_path": str(ck), "checkpoint_sha256": ck_sha,
            "evaluator": str(Q3_EVAL.relative_to(TS_ROOT)),
            "evaluator_sha256": sha256_file(Q3_EVAL),
            "manifest_shas": [["ood-t", str(OODT_MAN), OODT_MAN_SHA]],
            "protocol_dir": str(Q3_PROTO.relative_to(TS_ROOT)),
            "output_dir": str(od), "log": str(od.parent / f"{name}.log"),
            "pid_file": str(od.parent / f"{name}.pid"),
            "expected_pairs": 84,
            "command": [
                PY, str(Q3_EVAL),
                "--protocol-dir", str(Q3_PROTO),
                "--dataset-root", str(DATA_ROOT),
                "--ckpt-exclusive", str(ck),
                "--batch-size", "1",
                "--num-data-workers", "2",
                "--workers", "4",
                "--n-boot", "10000",
                "--evidence-role", "final",
                "--device", "cuda",
                "--dump-per-cube",
                "--output-dir", str(od),
            ],
        }

    jobs.append(q1q2("gpu0_v14880_val_q1q2", 0, anchor_ck, ANCHOR_SHA, "val",
                     VAL_DIR, VAL_MAN, VAL_MAN_SHA, "validation"))
    jobs.append(q1q2("gpu1_v14880_oodt_q1q2", 1, anchor_ck, ANCHOR_SHA, "ood-t_chopped",
                     OODT_DIR, OODT_MAN, OODT_MAN_SHA, "ood-t"))
    jobs.append(q3("gpu2_v14880_oodt_q3", 2, anchor_ck, ANCHOR_SHA))
    jobs.append(q1q2("gpu3_legacy11904_val_q1q2", 3, legacy_ck, LEGACY_SHA, "val",
                     VAL_DIR, VAL_MAN, VAL_MAN_SHA, "validation"))
    jobs.append(q1q2("gpu4_legacy11904_oodt_q1q2", 4, legacy_ck, LEGACY_SHA, "ood-t_chopped",
                     OODT_DIR, OODT_MAN, OODT_MAN_SHA, "ood-t"))
    jobs.append(q3("gpu5_legacy11904_oodt_q3", 5, legacy_ck, LEGACY_SHA))

    man = {
        "schema": "e0_launch_manifest_v1",
        "frozen_at": utc(),
        "ops_dir": str(OPS.relative_to(TS_ROOT)),
        "registry_revision": json.loads(
            (TS_ROOT / "artifacts/weight_registry.json").read_text())["revision"],
        "artifacts": {
            "verified_14880": {"logical_id_via_alias": ANCHOR_ALIAS,
                               "resolved_path": str(anchor_ck), "file_sha256": ANCHOR_SHA},
            "legacy_11904": {"logical_id": LEGACY_ID,
                             "resolved_path": str(legacy_ck), "file_sha256": LEGACY_SHA},
        },
        "frozen_inputs": {
            "validation_manifest": {"path": str(VAL_MAN), "sha256": VAL_MAN_SHA,
                                    "num_files": 952},
            "oodt_manifest": {"path": str(OODT_MAN), "sha256": OODT_MAN_SHA,
                              "num_files": 1904},
            "q3_protocol_dir": str(Q3_PROTO.relative_to(TS_ROOT)),
            "q3_protocol_gate": q3_gate,
            "q3_expected_pairs": 84,
        },
        "gpu_policy": {
            "gpus_used": [0, 1, 2, 3, 4, 5],
            "gpus_left_free": [6, 7],
            "note": ("one job per GPU via CUDA_VISIBLE_DEVICES; batch A = 0/1/2 (verified "
                     "14,880) starts first and must be verified alive before batch B = 3/4/5 "
                     "(legacy 11,904)"),
        },
        "forbidden": [
            "--sections all", "Q4", "modifying scorer/mask/manifest/bootstrap/metric defs",
            "aggregating smoke or INTERRUPTED outputs",
            "re-selecting a checkpoint based on OOD results",
        ],
        "jobs": jobs,
    }
    OUT.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n")
    os.chmod(OUT, 0o444)
    print(f"froze {OUT} (mode 0444)")
    print(f"  manifest sha256 = {sha256_file(OUT)}")
    for j in jobs:
        print(f"  {j['name']}: gpu={j['gpu']} kind={j['kind']} -> {Path(j['output_dir']).name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
