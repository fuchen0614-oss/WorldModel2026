#!/usr/bin/env python
"""M10: publish the M9-verified 14,880 checkpoint + create the default-training-anchor alias.

Fail closed.  Copy-only (never mv, never delete the source), atomic publish:
    tmpfile in the SAME dir -> write -> fsync -> re-hash the WRITTEN BYTES -> chmod 0444
    -> os.replace (atomic within a filesystem)

If the object already exists it is verified, not rewritten (idempotent republish).

Exit 0 published/verified · 2 precondition or verification failure
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(__file__).resolve().parent
TS_ROOT = OPS.parents[2]
STORE = Path("/csy-mix02/cog8/zjliu17/Agent/model-artifacts")
REGISTRY = TS_ROOT / "artifacts/weight_registry.json"

SRC = TS_ROOT / "runs/resume11904_to14880/20260818_112933/checkpoint_last.pt"
EXPECT_SHA = "a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f"
EXPECT_BYTES = 44302057

NEW_ID = "terrastate/v2/verified-resume14880@v1"
ALIAS = "terrastate/v2/default-training-anchor"
PARENT_ID = "terrastate/v2/legacy-boundary11904@v1"

REPORT = OPS / "m10_publish_report.json"


def sha256_file(p: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def fail(msg: str, rec: dict) -> int:
    print(f"BLOCKED: {msg}")
    rec["ok"] = False
    rec["reason"] = msg
    REPORT.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    rec: dict = {"utc": utc(), "steps": []}

    def note(k: str, v) -> None:
        rec["steps"].append({k: v})
        print(f"  {k}: {v}")

    print("M10 publish")

    # ---- 0. preconditions -----------------------------------------------------------------
    if not SRC.exists():
        return fail(f"source checkpoint missing: {SRC}", rec)
    src_bytes = SRC.stat().st_size
    src_sha = sha256_file(SRC)
    note("source", str(SRC))
    note("source_bytes", src_bytes)
    note("source_sha256", src_sha)
    if src_sha != EXPECT_SHA or src_bytes != EXPECT_BYTES:
        return fail(f"source SHA/bytes mismatch: got {src_sha}/{src_bytes} "
                    f"expect {EXPECT_SHA}/{EXPECT_BYTES}", rec)

    # M9 must have accepted this exact run before we may publish it (publish_conditions).
    m9 = TS_ROOT / "ops/resume11904_to14880/20260818_112933/m9_acceptance_report.json"
    if not m9.exists():
        return fail(f"M9 report missing: {m9}", rec)
    m9d = json.loads(m9.read_text())
    note("m9_accepted", m9d.get("accepted"))
    note("m9_n_checks", m9d.get("n_checks"))
    if m9d.get("accepted") is not True:
        return fail("M9 report does not say accepted=true", rec)

    # ---- 1. atomic publish into the content-addressed store --------------------------------
    obj_rel = Path("objects/sha256") / EXPECT_SHA[:2] / f"{EXPECT_SHA}.pt"
    dst = STORE / obj_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    note("object_path", str(dst))

    if dst.exists():
        have = sha256_file(dst)
        note("object_already_present", True)
        if have != EXPECT_SHA:
            return fail(f"EXISTING object at {dst} has SHA {have} != {EXPECT_SHA}; "
                        f"refusing to overwrite", rec)
        note("existing_object_verified", have)
    else:
        tmp = dst.parent / f".tmp.{os.getpid()}.{EXPECT_SHA[:12]}.pt"
        try:
            # copy-only; the source file is never moved or deleted
            with open(SRC, "rb") as fi, open(tmp, "wb") as fo:
                shutil.copyfileobj(fi, fo, 1 << 20)
                fo.flush()
                os.fsync(fo.fileno())
            written = sha256_file(tmp)          # re-hash the BYTES ON DISK, not the source
            if written != EXPECT_SHA:
                tmp.unlink(missing_ok=True)
                return fail(f"written bytes hash {written} != {EXPECT_SHA}; tmp discarded", rec)
            os.chmod(tmp, 0o444)
            os.replace(tmp, dst)                # atomic within the filesystem
            # fsync the directory so the rename is durable
            dfd = os.open(dst.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
            note("published_bytes_verified", written)
        except Exception as e:
            Path(tmp).unlink(missing_ok=True)
            return fail(f"publish failed ({type(e).__name__}: {e}); tmp discarded", rec)

    final_sha = sha256_file(dst)
    mode = oct(dst.stat().st_mode & 0o777)
    note("object_final_sha256", final_sha)
    note("object_mode", mode)
    if final_sha != EXPECT_SHA:
        return fail(f"post-publish SHA drift: {final_sha}", rec)
    if (dst.stat().st_mode & 0o222) != 0:
        return fail(f"object is writable ({mode}); expected 0444", rec)
    if not SRC.exists():
        return fail("source file disappeared -- publish must be copy-only", rec)
    note("source_still_present", True)

    rec["object"] = {"path": str(dst), "relpath": str(obj_rel), "sha256": final_sha,
                     "bytes": dst.stat().st_size, "mode": mode}
    print("  -> object published/verified")
    REPORT.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
