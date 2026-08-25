#!/usr/bin/env python
"""M1 — publish the four core weights into the content-addressed artifact store.

Rules enforced here (per the task contract):
  * NEVER move / rename / delete an original file.  Copy only.
  * Content-addressed layout:
        <STORE>/objects/sha256/<first2>/<sha256>.pt
  * Copy -> fsync -> re-hash the COPY -> only then os.replace() into place (atomic
    publish).  A hash mismatch between source and published copy FAILS CLOSED and
    the temp file is removed.
  * If an object already exists with the right sha256 + size, it is reused (idempotent).
  * Expected sha256 values that the task supplied are asserted; unknown ones are
    computed and recorded (never guessed).
  * Logical-id -> object mapping is written by make_registry.py, not here.
  * The 12GB / 478MB future-state caches are NOT copied; they are registered
    by path/size/schema/SHA elsewhere.

Read-only w.r.t. every source path.  Writes only under <STORE>.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

STORE = Path("/csy-mix02/cog8/zjliu17/Agent/model-artifacts")
OBJECTS = STORE / "objects" / "sha256"
OPS_DIR = Path(__file__).resolve().parent

# logical_id -> (source path, expected file bytes or None, expected file sha256 or None)
ARTIFACTS = [
    {
        "logical_id": "terrastate/v2/legacy-boundary11904@v1",
        "source": "/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train/runs/terrastate_v2/run1/checkpoint_boundary80.pt",
        "expect_bytes": 37972401,
        "expect_sha256": "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd",
        "role": "parent checkpoint for the exact resume (step 11904, recorded stage 2)",
    },
    {
        "logical_id": "terrastate/v2/historical-full14880@v1",
        "source": "/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train/runs/terrastate_v2/run1/checkpoint_last.pt",
        "expect_bytes": 44300969,
        "expect_sha256": "99f15a35fb9a356901c995bb0f48280a4da236f6970d0dd06343a28857fe2b8b",
        "role": "historical original-run step-14880 result; READ-ONLY comparison target",
    },
    {
        "logical_id": "obsworld/b4-exclusive/student-main-last-step14880@v1",
        "source": "/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb/runs/planb_excl_tournament/stageA_rescue_20260726_173149/MAIN/checkpoint_last.pt",
        "expect_bytes": None,
        "expect_sha256": None,
        "role": "--student-init warm start (arch ObsWorldB4Exclusive)",
        "expect_state_sha256": "488052d97c7d1c8a2e805d9838f344daef7ad02e5f185d3025031a5f1c026338",
        "state_sha_note": "state_sha(b4_state_dict) recorded as sha.student_init_sha256 in the parent checkpoint",
    },
    {
        "logical_id": "obsworld/b4/teacher-best-step13000@v1",
        "source": "/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb/checkpoints/plan_b_b4a/checkpoint_best.pt",
        "expect_bytes": None,
        "expect_sha256": None,
        "role": "--teacher-b4 frozen KD teacher (only q.* is loaded)",
        "expect_teacher_sha256": "bbe2c3ee6de540ae6eabeb7798f331388112ad370dbcae9533187344f2f8a302",
        "state_sha_note": "state_sha(teacher.state_dict()) after loading q.* == sha.teacher_sha256; verified separately by verify_state_shas.py",
    },
]

CHUNK = 8 << 20


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def publish(entry: dict) -> dict:
    src = Path(entry["source"])
    if not src.is_file():
        raise SystemExit(f"FAIL-CLOSED: source missing: {src}")
    size = src.stat().st_size
    if entry["expect_bytes"] is not None and size != entry["expect_bytes"]:
        raise SystemExit(f"FAIL-CLOSED: {entry['logical_id']} size {size} != expected "
                         f"{entry['expect_bytes']}")
    src_sha = sha256_file(src)
    if entry["expect_sha256"] is not None and src_sha != entry["expect_sha256"]:
        raise SystemExit(f"FAIL-CLOSED: {entry['logical_id']} sha256 {src_sha} != expected "
                         f"{entry['expect_sha256']}")

    dest = OBJECTS / src_sha[:2] / f"{src_sha}.pt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    reused = False
    if dest.exists():
        if dest.stat().st_size == size and sha256_file(dest) == src_sha:
            reused = True
            print(f"[reuse] {entry['logical_id']} -> {dest}", flush=True)
        else:
            raise SystemExit(f"FAIL-CLOSED: existing object {dest} does not match its own "
                             f"content address; refusing to overwrite")
    if not reused:
        fd, tmp = tempfile.mkstemp(dir=str(dest.parent), prefix=".incoming-", suffix=".pt")
        os.close(fd)
        tmp = Path(tmp)
        try:
            with open(src, "rb") as fi, open(tmp, "wb") as fo:
                shutil.copyfileobj(fi, fo, CHUNK)
                fo.flush()
                os.fsync(fo.fileno())
            copy_sha = sha256_file(tmp)
            if copy_sha != src_sha:
                raise SystemExit(f"FAIL-CLOSED: copy sha {copy_sha} != source sha {src_sha}")
            if tmp.stat().st_size != size:
                raise SystemExit("FAIL-CLOSED: copy size mismatch")
            os.chmod(tmp, 0o444)                     # objects are immutable
            os.replace(tmp, dest)                    # atomic publish
            print(f"[publish] {entry['logical_id']} -> {dest}", flush=True)
        finally:
            if tmp.exists():
                tmp.unlink()
    # source must be untouched
    assert src.is_file() and src.stat().st_size == size, "source changed — ABORT"
    out = dict(entry)
    out.update({
        "file_bytes": size,
        "file_sha256": src_sha,
        "object_path": str(dest),
        "object_relpath": str(dest.relative_to(STORE)),
        "reused_existing_object": reused,
        "source_mtime": int(src.stat().st_mtime),
    })
    return out


def main():
    STORE.mkdir(parents=True, exist_ok=True)
    OBJECTS.mkdir(parents=True, exist_ok=True)
    (STORE / "registry" / "terrastate").mkdir(parents=True, exist_ok=True)
    (STORE / "aliases").mkdir(parents=True, exist_ok=True)
    rows = [publish(e) for e in ARTIFACTS]
    dest = OPS_DIR / "published_artifacts.json"
    dest.write_text(json.dumps({"store": str(STORE), "artifacts": rows}, indent=2, sort_keys=True))
    print(f"wrote {dest}", flush=True)
    for r in rows:
        print(f"  {r['logical_id']}  {r['file_bytes']} B  {r['file_sha256'][:16]}", flush=True)


if __name__ == "__main__":
    main()
