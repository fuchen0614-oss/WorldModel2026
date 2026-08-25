#!/usr/bin/env python
"""M7: fail-closed preflight, then launch the FROZEN exact-resume run (11,904 -> 14,880).

This launcher adds nothing to the run: it executes `command` verbatim out of
launch_manifest.json. Its only job is to refuse to start unless every precondition holds.

Fail closed. Any check that fails, errors, or cannot be evaluated => launch NOTHING, exit
non-zero, write m7_preflight_failed.json. Uncertainty is never treated as permission.

GPU occupancy is re-verified HERE, independently of the watcher, with its own read-only
nvidia-smi call: the watcher's READY record proves the GPUs *were* idle for >=10 min, not
that they are idle at this instant. (It deliberately does NOT shell out to
`gpu_watcher.sh --once`, which would collide with the running watcher's flock.)

Never: kills/renices/migrates any PID · sudo · MIG/clock/power/persistence · a GPU subset ·
--allow-existing-out · pre-creating the output dir (the trainer creates it after its guard).

Usage:  launch_resume.py [--dry-run]
Exit :  0 launched (or dry-run OK) · 2 preflight failed · 3 another launcher holds the lock
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(__file__).resolve().parent
TS_ROOT = OPS.parents[2]
MANIFEST = OPS / "launch_manifest.json"
READY = OPS / "m6_gpu_ready.json"
LOCK = OPS / ".launch.lock"
REC = OPS / "m7_launch_record.json"
FAILED = OPS / "m7_preflight_failed.json"
EXPECT_MANIFEST_SHA = "1c7ea6c862a177d8abf8e6777f07275869fc179b83b0799b6234cbc558167d0a"

MEM_MAX_MIB, UTIL_MAX_PCT, EXPECT_GPUS = 1024, 5, 8


def sha256_file(p: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class Preflight:
    """Collects checks; a single failure blocks the launch."""

    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, name: str, ok: bool, detail: str) -> bool:
        self.checks.append({"name": name, "ok": bool(ok), "detail": detail})
        print(f"  [{'OK  ' if ok else 'FAIL'}] {name}: {detail}")
        return bool(ok)

    @property
    def failures(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"]]


def query_gpus() -> tuple[list[dict], str]:
    """Read-only nvidia-smi. Returns ([], reason) on ANY doubt."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,utilization.gpu,name",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30)
    except Exception as e:                                   # timeout, missing binary, ...
        return [], f"nvidia-smi unavailable: {type(e).__name__}: {e}"
    if r.returncode != 0:
        return [], f"nvidia-smi rc={r.returncode}: {r.stderr.strip()[:200]}"
    gpus = []
    for line in r.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            return [], f"unparseable nvidia-smi row: {line!r}"
        idx, mem, util, name = parts[0], parts[1], parts[2], ",".join(parts[3:])
        if not re.fullmatch(r"\d+", mem) or not re.fullmatch(r"\d+", util):
            return [], f"non-numeric row (gpu {idx}): mem={mem!r} util={util!r}"
        gpus.append({"i": int(idx), "mem_used_mib": int(mem), "util_pct": int(util), "name": name})
    return gpus, ""


def query_compute_apps() -> tuple[list[dict], str]:
    """Foreign compute processes are RECORDED, never signalled."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory,gpu_uuid",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30)
    except Exception as e:
        return [], f"query-compute-apps unavailable: {type(e).__name__}: {e}"
    if r.returncode != 0:
        return [], f"query-compute-apps rc={r.returncode}"
    apps = []
    for line in r.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        pid = parts[0]
        owner = comm = "unknown"
        try:
            ps = subprocess.run(["ps", "-o", "user=,comm=", "-p", pid],
                                capture_output=True, text=True, timeout=10)
            if ps.returncode == 0 and ps.stdout.split():
                f = ps.stdout.split()
                owner, comm = f[0], (f[1] if len(f) > 1 else "unknown")
        except Exception:
            pass
        apps.append({"pid": pid, "used_mib": parts[1] if len(parts) > 1 else "?",
                     "user": owner, "comm": comm})
    return apps, ""


def my_training_procs() -> list[str]:
    """Any already-running trainer of MINE (a second launch would double-write the out dir)."""
    try:
        r = subprocess.run(["ps", "-u", str(os.getuid()), "-o", "pid=,cmd="],
                           capture_output=True, text=True, timeout=15)
    except Exception:
        return []
    hits = []
    for line in r.stdout.splitlines():
        if "train_terrastate_v2" in line and "launch_resume" not in line:
            hits.append(line.strip())
    return hits


def resolve(logical_id: str) -> dict:
    """Re-resolve through the M1 resolver, which verifies sha256 and exits non-zero on drift."""
    r = subprocess.run([sys.executable, str(TS_ROOT / "tools/resolve_artifact.py"),
                        logical_id, "--json"], cwd=TS_ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"resolver rc={r.returncode} for {logical_id}: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout)


def git_status_modified() -> list[str]:
    r = subprocess.run(["git", "status", "--short"], cwd=TS_ROOT,
                       capture_output=True, text=True)
    out = []
    for l in r.stdout.splitlines():          # NOT .strip()ed: 'XY ' is a fixed 3-char prefix
        if any(c in l[:2] for c in "MTAD R".strip()):
            out.append(l[3:])
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv[1:]
    print(f"M7 preflight {'(DRY RUN)' if dry else ''} @ {utc()}")

    lock_fd = os.open(LOCK, os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(f"another launcher holds {LOCK} -- exiting (single-instance rule)")
        return 3

    if REC.exists() and not dry:
        print(f"REFUSING: a launch record already exists at {REC}.")
        print("  A second launch would write into the same output dir as the first.")
        print("  Inspect it (and the run it points at) before doing anything else.")
        return 2

    pf = Preflight()

    # ---- 1. manifest integrity (the frozen contract itself) --------------------------------
    ok_man = MANIFEST.exists()
    pf.add("manifest_exists", ok_man, str(MANIFEST))
    if not ok_man:
        FAILED.write_text(json.dumps({"utc": utc(), "checks": pf.checks}, indent=2))
        return 2
    man_sha = sha256_file(MANIFEST)
    pf.add("manifest_sha256_unchanged", man_sha == EXPECT_MANIFEST_SHA,
           f"{man_sha[:16]}... (expected {EXPECT_MANIFEST_SHA[:16]}...)")
    man = json.loads(MANIFEST.read_text())
    pf.add("manifest_immutable_mode", (MANIFEST.stat().st_mode & 0o222) == 0,
           f"mode={oct(MANIFEST.stat().st_mode & 0o777)} (expect no write bits)")

    # ---- 2. code identity: the run must be the code that passed the CPU gate ---------------
    for rel, want in man["key_file_sha256"].items():
        p = TS_ROOT / rel
        got = sha256_file(p) if p.exists() else "<missing>"
        pf.add(f"key_file:{rel}", got == want, f"{got[:16]}... vs frozen {want[:16]}...")

    mods = git_status_modified()
    pf.add("only_trainer_modified", mods == ["train/train_terrastate_v2.py"],
           f"tracked modifications = {mods}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=TS_ROOT,
                          capture_output=True, text=True).stdout.strip()
    pf.add("git_head_unchanged", head == man["repo"]["head"],
           f"{head[:12]} vs frozen {man['repo']['head'][:12]}")

    # ---- 3. output dir must not exist (never overwrite; trainer creates it itself) ----------
    outdir = TS_ROOT / man["output_dir_relative"]
    pf.add("output_dir_absent", not outdir.exists(),
           f"{outdir} {'does not exist' if not outdir.exists() else 'ALREADY EXISTS'}")
    pf.add("no_allow_existing_out", "--allow-existing-out" not in man["command"],
           "overwrite protection active")
    fss = man["command"][man["command"].index("--future-state-scale") + 1] \
        if "--future-state-scale" in man["command"] else "<absent>"
    pf.add("future_state_scale_is_1.0", fss == "1.0", f"--future-state-scale {fss}")
    pf.add("nproc_per_node_is_8", "--nproc_per_node=8" in man["command"],
           "all 8 GPUs, never a subset")

    # ---- 4. artifacts still resolve to the same bytes --------------------------------------
    for key, rec in man["artifacts_resolved"].items():
        try:
            now = resolve(rec["logical_id"])
            same = (now["resolved_path"] == rec["resolved_path"]
                    and now["file_sha256"] == rec["file_sha256"]
                    and now.get("sha256_verified") is True)
            pf.add(f"artifact:{key}", same,
                   f"{rec['logical_id']} sha={now['file_sha256'][:16]}... verified={now.get('sha256_verified')}")
        except Exception as e:
            pf.add(f"artifact:{key}", False, f"{type(e).__name__}: {e}")

    # ---- 5. no trainer of mine already running --------------------------------------------
    running = my_training_procs()
    pf.add("no_existing_trainer_of_mine", not running, f"{len(running)} found: {running[:2]}")

    # ---- 6. watcher READY record ------------------------------------------------------------
    pf.add("gpu_ready_record_exists", READY.exists(),
           str(READY) if READY.exists() else "watcher has not confirmed stable idle yet")
    if READY.exists():
        rd = json.loads(READY.read_text())
        pf.add("gpu_ready_record_valid",
               rd.get("ready") is True and rd.get("consecutive_idle", 0) >= 10
               and rd.get("n_gpu") == EXPECT_GPUS
               and rd.get("bar", {}).get("mem_used_mib_lt") == MEM_MAX_MIB
               and rd.get("bar", {}).get("util_pct_lt") == UTIL_MAX_PCT,
               f"consecutive_idle={rd.get('consecutive_idle')} n_gpu={rd.get('n_gpu')} "
               f"bar={rd.get('bar')} (bar must be unmodified)")

    # ---- 7. FRESH occupancy re-check, independent of the watcher ----------------------------
    gpus, err = query_gpus()
    pf.add("nvidia_smi_readable", not err and len(gpus) == EXPECT_GPUS,
           err or f"{len(gpus)} GPUs: " + ", ".join(f"g{g['i']}={g['mem_used_mib']}MiB/{g['util_pct']}%"
                                                    for g in gpus))
    if gpus and not err:
        busy = [g for g in gpus if g["mem_used_mib"] >= MEM_MAX_MIB or g["util_pct"] >= UTIL_MAX_PCT]
        pf.add("all_8_gpus_idle_right_now", not busy,
               "all idle" if not busy else f"BUSY: {[(g['i'], g['mem_used_mib'], g['util_pct']) for g in busy]}")
    apps, aerr = query_compute_apps()
    pf.add("no_compute_apps", not apps and not aerr,
           aerr or ("none" if not apps else f"{len(apps)} foreign/other process(es): {apps[:3]} "
                                            "-- RECORDED ONLY, never signalled; launch blocked"))

    # ---- verdict ---------------------------------------------------------------------------
    print(f"\npreflight: {len(pf.checks) - len(pf.failures)}/{len(pf.checks)} passed")
    if pf.failures:
        print("BLOCKED. Failing checks:")
        for c in pf.failures:
            print(f"  - {c['name']}: {c['detail']}")
        FAILED.write_text(json.dumps(
            {"utc": utc(), "launched": False, "n_checks": len(pf.checks),
             "failures": pf.failures, "checks": pf.checks,
             "note": "fail-closed: nothing was launched; no process was signalled; "
                     "the idle bar was NOT lowered"}, ensure_ascii=False, indent=2))
        print(f"wrote {FAILED}")
        return 2

    if dry:
        print("\nDRY RUN: all checks passed, launching nothing.")
        return 0

    # ---- launch the frozen command verbatim ------------------------------------------------
    env = dict(os.environ)
    for k, v in man["env"].items():
        if k != "note":
            env[k] = str(v)
    # Match the original run exactly: torchrun sets OMP_NUM_THREADS=1 itself when unset, which
    # is what run1 did (its log carries torchrun's default-OMP warning). So do not set it here.
    env.pop("CUDA_VISIBLE_DEVICES", None)          # all 8 GPUs, never a subset
    env.pop("OMP_NUM_THREADS", None)

    log_path = OPS / "m7_train.log"
    print(f"\nlaunching:\n  cwd={TS_ROOT}\n  log={log_path}\n  {man['command_str'][:200]}...")
    with open(log_path, "wb") as lf:
        proc = subprocess.Popen(man["command"], cwd=str(TS_ROOT), env=env,
                                stdout=lf, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
    pgid = os.getpgid(proc.pid)
    rec = {
        "launched": True, "utc": utc(), "pid": proc.pid, "pgid": pgid,
        "cwd": str(TS_ROOT), "log": str(log_path),
        "command": man["command"], "command_str": man["command_str"],
        "manifest_sha256": man_sha, "output_dir": str(outdir),
        "preflight_checks_passed": len(pf.checks), "preflight": pf.checks,
        "gpus_at_launch": gpus,
        "expected": {"from_step": 11904, "to_step": 14880, "updates": 2976,
                     "first_update": 11905, "first_stage": 3,
                     "eta_minutes_compute_only": man["expected_behaviour"]["compute_estimate_minutes"]},
        "process_ownership": ("started by THIS task in its own session (start_new_session=True); "
                             "PID/PGID recorded above are the only processes this task may manage"),
    }
    REC.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    print(f"LAUNCHED pid={proc.pid} pgid={pgid}")
    print(f"wrote {REC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
