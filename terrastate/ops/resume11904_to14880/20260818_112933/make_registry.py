#!/usr/bin/env python
"""M1 — write terrastate/artifacts/weight_registry.json.

Two artifact kinds:

  kind="object"           the file was COPIED into the content-addressed store and is
                          resolved as <store>/objects/sha256/<2>/<sha>.pt
  kind="path-registered"  the file stays exactly where it is (the 12GB / 478MB
                          future-state caches).  Only path + size + schema + provenance
                          SHAs are registered; nothing is copied.

Every record carries the provenance the trainer itself asserts, so a launcher can prove
it is using the intended file WITHOUT looking at basenames.

Idempotent: re-running rewrites the same content (revision bumps only if the artifact set
or any digest actually changed).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

OPS = Path(__file__).resolve().parent
REPO = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate")
STORE = Path("/csy-mix02/cog8/zjliu17/Agent/model-artifacts")
REGISTRY = REPO / "artifacts" / "weight_registry.json"

PUB = json.loads((OPS / "published_artifacts.json").read_text())
BY_ID = {a["logical_id"]: a for a in PUB["artifacts"]}
SSC = json.loads((OPS / "state_sha_check.json").read_text())
DMC = json.loads((OPS / "data_manifest_check.json").read_text())

CACHE_SHA_FILE = OPS / "cache_sha256.txt"
CACHE_DIR = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train/runs/terrastate_v2/cache")

PARENT_SHA = "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd"
HIST_SHA = "99f15a35fb9a356901c995bb0f48280a4da236f6970d0dd06343a28857fe2b8b"


def cache_file_shas() -> dict:
    """Parse `sha256sum` output (may be absent if the 12GB hash has not finished)."""
    out = {}
    if CACHE_SHA_FILE.is_file():
        for line in CACHE_SHA_FILE.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and len(parts[0]) == 64:
                out[Path(parts[1]).name] = parts[0]
    return out


def sidecar(name: str) -> dict:
    p = CACHE_DIR / f"{name}.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def main():
    cshas = cache_file_shas()
    arts: dict[str, dict] = {}

    # ---------------- object-store artifacts -------------------------------------------
    p = BY_ID["terrastate/v2/legacy-boundary11904@v1"]
    arts["terrastate/v2/legacy-boundary11904@v1"] = {
        "kind": "object",
        "object_relpath": p["object_relpath"],
        "file_bytes": p["file_bytes"],
        "file_sha256": p["file_sha256"],
        "original_path": p["source"],
        "arch": "TerraStateV2",
        "route_version": "terrastate_v2",
        "step": 11904,
        "epoch": 31,
        "micro_in_epoch": 372,
        "stage_recorded_in_file": 2,
        "stage_of_next_update": 3,
        "total_steps": 14880,
        "candidate": "stage2_end_boundary80",
        "best_val": 0.31334985432787643,
        "b4_state_sha256": SSC["parent_b4_state_sha256"],
        "role": ("EXACT-RESUME PARENT for the 11,904 -> 14,880 continuation. Also the "
                 "checkpoint that produced the FROZEN Q1/Q2/Q3 evidence in "
                 "TERRASTATE_V2_EVIDENCE.md."),
        "provenance_notes": [
            "Written by the original run at step 11904 BEFORE the stage 2->3 switch, so the "
            "recorded stage is 2 while the next scheduled update belongs to stage 3.",
            "Complete resume state: optimizer_state_dict (2 groups / 30 Adam entries), "
            "scheduler_state_dict (last_epoch=11904), scaler record (FP32, disabled), "
            "rng_state + rng_states_by_rank (8 ranks), q_freeze.",
        ],
        "evidence_doc": "TERRASTATE_V2_EVIDENCE.md",
        "immutable": True,
    }

    p = BY_ID["terrastate/v2/historical-full14880@v1"]
    arts["terrastate/v2/historical-full14880@v1"] = {
        "kind": "object",
        "object_relpath": p["object_relpath"],
        "file_bytes": p["file_bytes"],
        "file_sha256": p["file_sha256"],
        "original_path": p["source"],
        "arch": "TerraStateV2",
        "route_version": "terrastate_v2",
        "step": 14880,
        "epoch": 40,
        "stage_recorded_in_file": 3,
        "total_steps": 14880,
        "candidate": "last",
        "role": ("HISTORICAL original-run 40-epoch / 14,880-update result. READ-ONLY "
                 "comparison target for the resume run. Its binary EXISTS (this record "
                 "supersedes the earlier 'binary missing' claim in WEIGHTS_INDEX.md)."),
        "provenance_notes": [
            "Produced by the SAME uninterrupted original run as the boundary80 parent "
            "(train.log: 'done step=14880 best_val=0.31288 teacher_unchanged=True "
            "stage3_qgrad_seen=True').",
            "This artifact must never be overwritten, and the resume run must write to a "
            "DIFFERENT output directory.",
            "Its provenance is NOT interchangeable with a resumed 14,880 checkpoint even if "
            "metrics coincide.",
        ],
        "immutable": True,
    }

    p = BY_ID["obsworld/b4-exclusive/student-main-last-step14880@v1"]
    arts["obsworld/b4-exclusive/student-main-last-step14880@v1"] = {
        "kind": "object",
        "object_relpath": p["object_relpath"],
        "file_bytes": p["file_bytes"],
        "file_sha256": p["file_sha256"],
        "original_path": p["source"],
        "arch": SSC["student_init_arch"],
        "role": "--student-init warm start for the TerraState-V2 training line",
        "b4_state_sha256": SSC["student_init_sha256"],
        "asserted_as": "sha.student_init_sha256 in every TerraState-V2 checkpoint",
        "warm_start_exact": SSC["warm_start_exact"],
        "provenance_notes": [
            "warm_start_terrastate_v2 loads it with missing==0 and unexpected==0 "
            "(verified on the published object, source=ObsWorldB4Exclusive).",
            "A raw Phase-I B4 is NOT a substitute (it lacks the alpha buffer).",
        ],
        "immutable": True,
    }

    p = BY_ID["obsworld/b4/teacher-best-step13000@v1"]
    arts["obsworld/b4/teacher-best-step13000@v1"] = {
        "kind": "object",
        "object_relpath": p["object_relpath"],
        "file_bytes": p["file_bytes"],
        "file_sha256": p["file_sha256"],
        "original_path": p["source"],
        "arch": SSC["teacher_arch"],
        "role": "--teacher-b4 frozen KD teacher (only its q.* is loaded)",
        "teacher_state_sha256_after_q_load": SSC["teacher_sha256"],
        "asserted_as": "sha.teacher_sha256 in every TerraState-V2 checkpoint",
        "teacher_q_keys": SSC["teacher_q_keys"],
        "teacher_load_exact": SSC["teacher_load_exact"],
        "provenance_notes": [
            "223 q.* tensors load into a fresh PVTContextformerQ with missing==0 and "
            "unexpected==0; the resulting state_sha equals the value the parent checkpoint "
            "recorded, so the resume teacher assertion passes.",
            "The trainer re-asserts this SHA is unchanged at the end of the run.",
        ],
        "immutable": True,
    }

    # ---------------- path-registered data artifacts (NOT copied) ----------------------
    for split, fname, expect_cubes, manifest_key in (
        ("train", "train_future_state_cache.pt", 23816, "train"),
        ("val", "val_future_state_cache.pt", 952, "val"),
    ):
        fp = CACHE_DIR / fname
        sc = sidecar(fname).get("provenance", {})
        rec = {
            "kind": "path-registered",
            "path": str(fp),
            "file_bytes": fp.stat().st_size,
            "file_sha256": cshas.get(fname),
            "schema": sc.get("schema"),
            "split": sc.get("split"),
            "n_cubes": sc.get("n_cubes"),
            "n_cubes_expected": expect_cubes,
            "horizon_h": sc.get("horizon_h"),
            "patch_size": sc.get("patch_size"),
            "patches_per_cube": sc.get("patches_per_cube"),
            "state_dim": sc.get("state_dim"),
            "coverage": sc.get("coverage"),
            "q_projector_sha256": sc.get("q_projector_sha256"),
            "data_manifest_sha256": sc.get("data_manifest_sha256"),
            "mask_sha256": sc.get("mask_sha256"),
            "config_sha256": sc.get("config_sha256"),
            "recorded_data_root": sc.get("data_root"),
            "resolved_data_root": DMC[manifest_key]["root"],
            "resolved_data_root_manifest_match": DMC[manifest_key]["match"],
            "role": f"frozen future-state target cache ({split} split)",
            "provenance_notes": [
                "NOT copied into the object store (12.5GB / 0.5GB); registered in place.",
                "config_sha256 is a PROTOCOL fingerprint (schema/field order/horizon/patch "
                "rule/q-projector SHA) and is therefore IDENTICAL for train and val by "
                "construction; content identity is data_manifest_sha256 + mask_sha256.",
                f"recorded data_root {sc.get('data_root')} was a /tmp staging dir that no "
                f"longer exists; {DMC[manifest_key]['root']} reproduces the SAME "
                f"data_manifest_sha256, so the relpath keys still resolve.",
            ],
            "immutable": True,
        }
        arts[f"terrastate/v2/future-state-cache-{split}@v1"] = rec

    # ---------------- reserved (not yet published) -------------------------------------
    reserved = {
        "terrastate/v2/verified-resume14880@v1": {
            "status": "RESERVED — not published",
            "publish_conditions": [
                "an exact resume from terrastate/v2/legacy-boundary11904@v1 reaches step 14880",
                "exactly 2976 updates executed, the first one in stage 3",
                "no duplicate boundary80 checkpoint, no extra stage-2 update",
                "only core.blocks.2.* q tensors trainable, receiving grad and Adam state",
                "optimizer/scheduler/RNG continuity verified",
                "teacher weights unchanged; no NaN; no historical output overwritten",
            ],
        },
        "terrastate/v2/default-training-anchor": {
            "status": "RESERVED alias — not created",
            "note": ("mutable alias, lives at <store>/aliases/; will point at the verified "
                     "resume artifact only after M9 acceptance passes"),
        },
    }

    payload = {
        "schema": "terrastate_weight_registry_v1",
        "store": str(STORE),
        "generated_by": str(Path(__file__).resolve()),
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "policy": {
            "selection": ("Launchers, tests and eval scripts must name a LOGICAL ID and "
                          "resolve it with tools/resolve_artifact.py. Selecting a weight by "
                          "basename (checkpoint_last.pt / _best.pt / _boundary80.pt) is "
                          "forbidden: three of those share a byte count in the same dir."),
            "verification": "resolve_artifact re-hashes the object and fails closed on mismatch.",
            "immutability": ("objects/ entries are content-addressed and mode 0444; originals "
                             "are never moved or deleted; historical results are never "
                             "overwritten."),
            "aliases": ("only <store>/aliases/*.json are mutable; re-pointing an anchor is an "
                        "operational act with its own record."),
        },
        "artifacts": arts,
        "reserved": reserved,
    }
    body = json.dumps({k: v for k, v in payload.items() if k != "generated_at"},
                      sort_keys=True, separators=(",", ":"))
    payload["revision"] = hashlib.sha256(body.encode()).hexdigest()[:16]

    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {REGISTRY}")
    print(f"revision={payload['revision']} artifacts={len(arts)} reserved={len(reserved)}")
    for k, v in arts.items():
        sha = v.get("file_sha256")
        print(f"  {k:56s} {v['kind']:16s} {(sha[:16] if sha else 'sha=PENDING')}")


if __name__ == "__main__":
    main()
