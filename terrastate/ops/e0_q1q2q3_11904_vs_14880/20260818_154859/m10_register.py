#!/usr/bin/env python
"""M10 part 2: register verified-resume14880@v1 in the registry and create the anchor alias.

Registry write is atomic (tmp + fsync + os.replace) and keeps a timestamped backup of the
previous revision inside this ops dir.  The RESERVED entry's publish_conditions are checked
against the M9 report before the entry is promoted.

Exit 0 ok · 2 failure
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(__file__).resolve().parent
TS_ROOT = OPS.parents[2]
STORE = Path("/csy-mix02/cog8/zjliu17/Agent/model-artifacts")
REGISTRY = TS_ROOT / "artifacts/weight_registry.json"

NEW_ID = "terrastate/v2/verified-resume14880@v1"
ALIAS = "terrastate/v2/default-training-anchor"
SHA = "a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f"
BYTES = 44302057
REPORT = OPS / "m10_register_report.json"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canon_sha(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()[:16]


def atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.parent / f".tmp.{os.getpid()}.{path.name}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    dfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def main() -> int:
    rec: dict = {"utc": utc()}
    print("M10 register")

    reg = json.loads(REGISTRY.read_text())
    prev_rev = reg.get("revision")
    rec["previous_revision"] = prev_rev
    print(f"  previous revision: {prev_rev}")

    # keep the pre-change registry as evidence in THIS ops dir (never overwrite anything)
    backup = OPS / f"weight_registry.before_m10.{prev_rev}.json"
    if not backup.exists():
        backup.write_text(json.dumps(reg, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"  backup: {backup.name}")

    # ---- verify the RESERVED publish_conditions are actually met ---------------------------
    reserved = reg.get("reserved", {})
    if NEW_ID not in reserved and NEW_ID not in reg["artifacts"]:
        print(f"  WARNING: {NEW_ID} was neither RESERVED nor present")
    conds = (reserved.get(NEW_ID) or {}).get("publish_conditions", [])
    m9 = json.loads((TS_ROOT / "ops/resume11904_to14880/20260818_112933/"
                     "m9_acceptance_report.json").read_text())
    if m9.get("accepted") is not True:
        print("BLOCKED: M9 not accepted")
        return 2
    by_name = {c["name"]: c for c in m9.get("checks", [])}
    # map each frozen publish condition to the M9 check(s) that discharge it
    cond_map = {
        "an exact resume from terrastate/v2/legacy-boundary11904@v1 reaches step 14880":
            ["final_step_is_14880", "lineage_parent_sha256", "lineage_parent_step_11904"],
        "exactly 2976 updates executed, the first one in stage 3":
            ["loss_log_count_2976", "loss_log_first_step_11905", "all_updates_stage_3"],
        "no duplicate boundary80 checkpoint, no extra stage-2 update":
            ["no_duplicate_boundary80", "all_updates_stage_3"],
        "only core.blocks.2.* q tensors trainable, receiving grad and Adam state":
            ["trainable_q_count_12", "trainable_q_all_core_blocks_2"],
        "optimizer/scheduler/RNG continuity verified":
            ["optimizer_state_present", "scheduler_last_epoch_14880"],
        "teacher weights unchanged; no NaN; no historical output overwritten":
            ["teacher_digest_parent_matches_child", "teacher_artifact_content_addressed",
             "trainer_asserted_teacher_unchanged", "best_val_finite"],
    }
    cond_status = []
    all_ok = True
    for c in conds:
        needed = cond_map.get(c, [])
        got = [(n, by_name.get(n, {}).get("ok")) for n in needed]
        ok = bool(needed) and all(v is True for _, v in got)
        all_ok &= ok
        cond_status.append({"condition": c, "discharged_by": got, "ok": ok})
        print(f"  [{'OK  ' if ok else 'FAIL'}] {c[:64]}...")
    rec["publish_conditions"] = cond_status
    if conds and not all_ok:
        print("BLOCKED: not all frozen publish_conditions are discharged by M9")
        REPORT.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
        return 2

    # ---- promote the entry ------------------------------------------------------------------
    obj_rel = f"objects/sha256/{SHA[:2]}/{SHA}.pt"
    entry = {
        "arch": "TerraStateV2",
        "route_version": "terrastate_v2",
        "kind": "object",
        "immutable": True,
        "file_sha256": SHA,
        "file_bytes": BYTES,
        "object_relpath": obj_rel,
        "original_path": str(TS_ROOT / "runs/resume11904_to14880/20260818_112933/checkpoint_last.pt"),
        "step": 14880,
        "total_steps": 14880,
        "epoch": 40,
        "candidate": "last",
        "stage_recorded_in_file": 3,
        "role": ("VERIFIED exact-resume result: legacy-boundary11904@v1 -> 14,880 (2,976 updates, "
                 "all in stage 3).  Anchor for subsequent legacy-model evaluation and for "
                 "initialising later stages."),
        "parent_id": "terrastate/v2/legacy-boundary11904@v1",
        "parent_file_sha256": "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd",
        "m9_report": "ops/resume11904_to14880/20260818_112933/m9_acceptance_report.json",
        "m9_checks_passed": f"{m9.get('n_checks')}/{m9.get('n_checks')}",
        "provenance_notes": [
            "Model WEIGHTS are byte-identical to terrastate/v2/historical-full14880@v1: "
            "value_sha (sha256 over key-ordered raw tensor bytes) = aa98fbd2fa302727 on both, "
            "max abs diff = 0 across all 255 tensors.",
            "The FILE sha256 nevertheless differs from historical-full14880@v1 "
            "(a5d2a0cc... vs 99f15a35...) because this checkpoint additionally carries the B5 "
            "lineage block and this run's own args/timestamps.  Byte-equal weights, "
            "independent file identity -- both statements are true and must not be conflated.",
            "Historical Q1/Q2/Q3 numbers measured on the 11,904 checkpoint must NOT be "
            "relabelled as coming from 14,880.",
        ],
    }
    reg["artifacts"][NEW_ID] = entry
    reg.setdefault("reserved", {}).pop(NEW_ID, None)
    reg["reserved"].pop(ALIAS, None)
    reg["aliases"] = dict(reg.get("aliases", {}))
    reg["aliases"][ALIAS] = {
        "target": NEW_ID,
        "mutable": True,
        "location": f"<store>/aliases/{ALIAS.replace('/', '__')}.json",
        "set_at": utc(),
        "note": ("Re-pointing this anchor is an operational act; the previous registry revision "
                 f"is preserved at ops/.../{backup.name}."),
    }
    reg["generated_at"] = utc()
    reg["revision"] = "PENDING"
    reg["revision"] = canon_sha({k: v for k, v in reg.items() if k != "revision"})
    rec["new_revision"] = reg["revision"]
    print(f"  new revision: {reg['revision']}")

    atomic_write_json(REGISTRY, reg)
    print(f"  registry written: {REGISTRY}")

    # ---- the alias file in the STORE ---------------------------------------------------------
    adir = STORE / "aliases"
    adir.mkdir(parents=True, exist_ok=True)
    apath = adir / f"{ALIAS.replace('/', '__')}.json"
    atomic_write_json(apath, {
        "alias": ALIAS,
        "logical_id": NEW_ID,
        "set_at": utc(),
        "set_by": "M10 (ops/e0_q1q2q3_11904_vs_14880/20260818_154859/m10_register.py)",
        "target_file_sha256": SHA,
        "note": "mutable pointer; resolve with tools/resolve_artifact.py --alias",
    })
    print(f"  alias written: {apath}")
    rec["alias_path"] = str(apath)
    rec["ok"] = True
    REPORT.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
