#!/usr/bin/env python
"""E0 watcher/launcher: wait for ALL 8 H200s to be stably idle, then launch the 6 frozen jobs.

Read-only GPU inspection via nvidia-smi only.  This process NEVER creates a CUDA context
(it does not import torch), never signals/renices/inspects another user's processes, and
never launches on a subset of GPUs.

Idle bar -- ALL of these, on ALL 8 GPUs, for 5 CONSECUTIVE polls (~5 min):
    * zero compute processes anywhere on the node
    * memory.used <= 100 MiB per GPU
    * utilization.gpu <= 5 % per GPU
Any doubt (nvidia-smi timeout/error, GPU count != 8, unparseable row) => streak reset to 0.
A partial release (some GPUs free) does NOT lower the bar and does NOT launch anything.

Launch order: batch A = GPU 0,1,2 (verified 14,880).  Then a fresh re-check plus a liveness
probe of batch A.  Only if still safe: batch B = GPU 3,4,5 (legacy 11,904).  GPU 6-7 stay free.

After launching, the watcher supervises: if a FOREIGN compute process appears on GPUs 0-5
while our jobs run, it stops ONLY our own overlapping evaluators, marks their output dirs
INTERRUPTED, and returns to waiting for a clean window (a retry runs in a NEW directory).

Exit 0 all six launched and supervised to completion · 3 another instance holds the lock
· 4 deadline reached without a clean window (nothing launched)

Usage:
  e0_watcher.py [--interval S] [--required-streak N] [--deadline-hours H]
                [--once] [--dry-run] [--smi-cmd CMD] [--state-suffix S]
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(__file__).resolve().parent
TS_ROOT = OPS.parents[2]

MEM_MAX_MIB = 100
UTIL_MAX_PCT = 5
EXPECT_GPUS = 8
OUR_GPUS = [0, 1, 2, 3, 4, 5]          # 6 and 7 are deliberately left free


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ctx:
    """Paths + knobs, so the self-test can redirect every write into a sandbox."""

    def __init__(self, a: argparse.Namespace):
        sfx = a.state_suffix
        self.manifest = OPS / "launch_manifest.json"
        self.lock = OPS / f".e0_watcher{sfx}.lock"
        self.log = OPS / f"e0_watcher{sfx}.log"
        self.snaps = OPS / f"gpu_snapshots{sfx}.jsonl"
        self.state = OPS / f"e0_watcher_state{sfx}.json"
        self.launched = OPS / f"e0_launch_record{sfx}.json"
        self.interval = a.interval
        self.need = a.required_streak
        self.deadline_h = a.deadline_hours
        self.dry = a.dry_run
        self.smi = a.smi_cmd

    def say(self, msg: str) -> None:
        line = f"[{utc()}] {msg}"
        print(line, flush=True)
        with open(self.log, "a") as f:
            f.write(line + "\n")


def run_smi(ctx: Ctx, query: str, extra: str = "") -> tuple[int, str, str]:
    """Read-only nvidia-smi. ctx.smi is overridable so tests can inject fake output."""
    cmd = f"{ctx.smi} --query-{query} --format=csv,noheader,nounits {extra}".strip()
    try:
        p = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=30)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:                                     # timeout / missing binary
        return 99, "", f"{type(e).__name__}: {e}"


def sample(ctx: Ctx) -> dict:
    """One read-only snapshot.  Returns idle=False on ANY uncertainty (fail closed)."""
    snap: dict = {"utc": utc(), "idle": False, "reason": "", "gpus": [], "foreign": []}

    rc, out, err = run_smi(ctx, "gpu=index,memory.used,utilization.gpu")
    if rc != 0:
        snap["reason"] = f"nvidia-smi rc={rc}: {err.strip()[:160]}"
        return snap
    for line in out.strip().splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) < 3 or not all(x.isdigit() for x in parts[:3]):
            snap["reason"] = f"unparseable row: {line!r}"
            return snap
        snap["gpus"].append({"i": int(parts[0]), "mem": int(parts[1]), "util": int(parts[2])})
    if len(snap["gpus"]) != EXPECT_GPUS:
        snap["reason"] = f"expected {EXPECT_GPUS} GPUs, saw {len(snap['gpus'])}"
        return snap

    rc, out, err = run_smi(ctx, "compute-apps=pid,used_memory")
    if rc != 0:
        snap["reason"] = f"query-compute-apps rc={rc}"
        return snap
    for line in out.strip().splitlines():
        if not line.strip():
            continue
        parts = [x.strip() for x in line.split(",")]
        pid = parts[0]
        owner = "unknown"
        try:                                    # owner only, for the record; never inspected
            ps = subprocess.run(["ps", "-o", "user=", "-p", pid],
                                capture_output=True, text=True, timeout=10)
            if ps.returncode == 0 and ps.stdout.strip():
                owner = ps.stdout.strip()
            else:
                owner = "gone"
        except Exception:
            pass
        snap["foreign"].append({"pid": pid, "mem": parts[1] if len(parts) > 1 else "?",
                                "user": owner})
    if snap["foreign"]:
        snap["reason"] = (f"{len(snap['foreign'])} compute process(es) present "
                          f"(users={sorted({f['user'] for f in snap['foreign']})}) "
                          f"-- RECORDED ONLY, never signalled")
        return snap

    busy = [g for g in snap["gpus"] if g["mem"] > MEM_MAX_MIB or g["util"] > UTIL_MAX_PCT]
    if busy:
        snap["reason"] = ("above bar: "
                          + ", ".join(f"g{g['i']}={g['mem']}MiB/{g['util']}%" for g in busy))
        return snap

    snap["idle"] = True
    snap["reason"] = "all 8 GPUs idle"
    return snap


def foreign_on_our_gpus(ctx: Ctx) -> list[dict]:
    """Foreign compute processes only. Our own launched PIDs are excluded by caller."""
    rc, out, _ = run_smi(ctx, "compute-apps=pid,used_memory")
    if rc != 0:
        return [{"pid": "?", "mem": "?", "note": f"smi rc={rc} -- treated as occupied"}]
    apps = []
    for line in out.strip().splitlines():
        if line.strip():
            parts = [x.strip() for x in line.split(",")]
            apps.append({"pid": parts[0], "mem": parts[1] if len(parts) > 1 else "?"})
    return apps


# ------------------------------------------------------------------ job launching
def load_jobs(ctx: Ctx) -> list[dict]:
    if not ctx.manifest.exists():
        raise SystemExit(f"BLOCKED: frozen manifest missing: {ctx.manifest}")
    man = json.loads(ctx.manifest.read_text())
    return man["jobs"]


def preflight_job(job: dict) -> tuple[bool, str]:
    """Re-verify the frozen inputs of ONE job immediately before it starts."""
    import hashlib

    def sha(p: Path) -> str:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()

    ck = Path(job["checkpoint_path"])
    if not ck.exists():
        return False, f"checkpoint missing: {ck}"
    got = sha(ck)
    if got != job["checkpoint_sha256"]:
        return False, f"checkpoint SHA drift: {got[:16]} != {job['checkpoint_sha256'][:16]}"
    for label, mp, want in job.get("manifest_shas", []):
        p = Path(mp)
        if not p.exists():
            return False, f"{label} manifest missing: {mp}"
        g = sha(p)
        if g != want:
            return False, f"{label} manifest SHA drift: {g[:16]} != {want[:16]}"
    outdir = Path(job["output_dir"])
    if outdir.exists() and any(outdir.iterdir()):
        return False, f"output dir already non-empty (never overwrite): {outdir}"
    return True, "ok"


def launch_job(ctx: Ctx, job: dict) -> dict:
    outdir = Path(job["output_dir"])
    outdir.mkdir(parents=True, exist_ok=True)
    logp = Path(job["log"])
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = str(job["gpu"])
    env.pop("OMP_NUM_THREADS", None)
    rec = {"name": job["name"], "gpu": job["gpu"], "cmd": job["command"],
           "output_dir": str(outdir), "log": str(logp),
           "cuda_visible_devices": str(job["gpu"]), "started_utc": utc()}
    if ctx.dry:
        rec.update({"pid": None, "dry_run": True})
        ctx.say(f"DRY RUN would launch {job['name']} on GPU {job['gpu']}")
        return rec
    with open(logp, "wb") as lf:
        p = subprocess.Popen(job["command"], cwd=str(TS_ROOT), env=env,
                             stdout=lf, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    rec["pid"] = p.pid
    rec["pgid"] = os.getpgid(p.pid)
    Path(job["pid_file"]).write_text(f"{p.pid}\n")
    ctx.say(f"LAUNCHED {job['name']} gpu={job['gpu']} pid={p.pid}")
    return rec


def alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except Exception:
        return False


def stop_ours(ctx: Ctx, recs: list[dict], why: str) -> None:
    """Stop ONLY processes this watcher started; mark their outputs INTERRUPTED."""
    for r in recs:
        pid = r.get("pid")
        if pid and alive(pid):
            ctx.say(f"stopping OUR OWN job {r['name']} pid={pid} -- {why}")
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except Exception as e:
                ctx.say(f"  SIGTERM failed ({type(e).__name__}); leaving it alone")
            r["stopped_utc"] = utc()
            r["stopped_reason"] = why
        od = Path(r["output_dir"])
        if od.exists():
            (od / "INTERRUPTED.json").write_text(json.dumps(
                {"interrupted_utc": utc(), "reason": why, "job": r["name"], "pid": pid,
                 "status": "INTERRUPTED -- NOT a formal result; do not aggregate",
                 "retry_policy": "rerun from a NEW timestamped output dir"},
                ensure_ascii=False, indent=2))


def supervise(ctx: Ctx, recs: list[dict]) -> None:
    """Poll our jobs to completion; yield the node back if a foreign job shows up."""
    ours = {r["pid"] for r in recs if r.get("pid")}
    while True:
        running = [r for r in recs if alive(r.get("pid"))]
        for r in recs:
            if r.get("pid") and not alive(r["pid"]) and "exit_code" not in r:
                try:
                    _, st = os.waitpid(r["pid"], os.WNOHANG)
                    r["exit_code"] = os.waitstatus_to_exitcode(st)
                except Exception:
                    r["exit_code"] = "unknown (not our direct child or already reaped)"
                r["finished_utc"] = utc()
                ctx.say(f"job {r['name']} finished exit={r['exit_code']}")
        ctx.launched.write_text(json.dumps(
            {"utc": utc(), "jobs": recs}, ensure_ascii=False, indent=2))
        if not running:
            ctx.say("all our jobs have finished")
            return
        apps = foreign_on_our_gpus(ctx)
        foreign = [a for a in apps if a.get("pid", "?").isdigit() and int(a["pid"]) not in ours]
        # a foreign PID may be a child of our own torch process; only react to PIDs whose
        # owner differs from us
        truly_foreign = []
        for a in foreign:
            try:
                ps = subprocess.run(["ps", "-o", "user=", "-p", a["pid"]],
                                    capture_output=True, text=True, timeout=10)
                who = ps.stdout.strip()
                if who and who != os.environ.get("USER", ""):
                    truly_foreign.append({**a, "user": who})
            except Exception:
                pass
        if truly_foreign:
            stop_ours(ctx, recs, f"foreign compute process(es) appeared: {truly_foreign[:3]}")
            ctx.launched.write_text(json.dumps(
                {"utc": utc(), "jobs": recs, "yielded_to": truly_foreign[:5]},
                ensure_ascii=False, indent=2))
            ctx.say("yielded the node; our overlapping jobs stopped, foreign jobs untouched")
            return
        time.sleep(ctx.interval)


def launch_all(ctx: Ctx, jobs: list[dict]) -> int:
    """Batch A (GPU 0-2, verified 14,880) -> verify -> batch B (GPU 3-5, legacy 11,904)."""
    batch_a = [j for j in jobs if j["gpu"] in (0, 1, 2)]
    batch_b = [j for j in jobs if j["gpu"] in (3, 4, 5)]
    recs: list[dict] = []

    for label, batch in (("A", batch_a), ("B", batch_b)):
        if label == "B":
            ctx.say("verifying batch A before starting batch B")
            time.sleep(0 if ctx.dry else 150)
            for r in recs:
                ok = alive(r.get("pid")) or ctx.dry
                logtail = ""
                lp = Path(r["log"])
                if lp.exists():
                    txt = lp.read_text(errors="replace")
                    logtail = txt[-400:]
                    for bad in ("Traceback", "CUDA out of memory", "nan", "NaN"):
                        if bad in txt:
                            ctx.say(f"  batch A job {r['name']} log contains {bad!r}")
                r["batch_a_alive_check"] = ok
                ctx.say(f"  {r['name']} alive={ok} log_tail={logtail[-120:]!r}")
            if not ctx.dry and not all(r.get("batch_a_alive_check") for r in recs):
                ctx.say("BLOCKED: a batch-A job is not alive; NOT starting batch B")
                ctx.launched.write_text(json.dumps({"utc": utc(), "jobs": recs,
                                                    "batch_b": "not started"},
                                                   ensure_ascii=False, indent=2))
                supervise(ctx, recs)
                return 2
            snap = sample(ctx)
            our_pids = {str(r.get("pid")) for r in recs}
            others = [f for f in snap["foreign"] if f["pid"] not in our_pids]
            if others:
                ctx.say(f"BLOCKED: foreign process appeared before batch B: {others[:3]}; "
                        f"not starting batch B, supervising batch A")
                supervise(ctx, recs)
                return 2

        for job in batch:
            ok, why = preflight_job(job)
            if not ok:
                ctx.say(f"BLOCKED launching {job['name']}: {why}")
                stop_ours(ctx, recs, f"aborting batch after preflight failure on {job['name']}")
                return 2
            recs.append(launch_job(ctx, job))
            ctx.launched.write_text(json.dumps({"utc": utc(), "jobs": recs},
                                               ensure_ascii=False, indent=2))
        ctx.say(f"batch {label} launched ({len(batch)} jobs)")

    if ctx.dry:
        ctx.say("DRY RUN complete -- no process was started")
        return 0
    supervise(ctx, recs)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--required-streak", type=int, default=5)
    ap.add_argument("--deadline-hours", type=float, default=72.0)
    ap.add_argument("--once", action="store_true", help="one poll, report, exit (no launch)")
    ap.add_argument("--dry-run", action="store_true", help="never start a process")
    ap.add_argument("--smi-cmd", default="nvidia-smi", help="override for self-tests")
    ap.add_argument("--state-suffix", default="", help="sandbox state files for self-tests")
    a = ap.parse_args()
    ctx = Ctx(a)

    lock_fd = os.open(ctx.lock, os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(f"another watcher/launcher holds {ctx.lock} -- exiting (single instance)")
        return 3
    os.write(lock_fd, f"{os.getpid()}\n".encode())

    ctx.say(f"watcher start pid={os.getpid()} interval={ctx.interval}s "
            f"need_streak={ctx.need} bar=mem<={MEM_MAX_MIB}MiB util<={UTIL_MAX_PCT}% "
            f"gpus={EXPECT_GPUS} our_gpus={OUR_GPUS} (6,7 stay free) dry={ctx.dry}")

    if a.once:
        snap = sample(ctx)
        with open(ctx.snaps, "a") as f:
            f.write(json.dumps(snap, ensure_ascii=False) + "\n")
        ctx.say(f"once: idle={snap['idle']} reason={snap['reason']}")
        print(json.dumps(snap, ensure_ascii=False))
        return 0 if snap["idle"] else 1

    jobs = load_jobs(ctx)
    ctx.say(f"frozen manifest loaded: {len(jobs)} jobs")

    streak = 0
    t0 = time.time()
    deadline = t0 + ctx.deadline_h * 3600
    polls = 0
    while True:
        if time.time() > deadline:
            ctx.say(f"DEADLINE {ctx.deadline_h}h reached with streak={streak}; "
                    f"launching NOTHING, bar never lowered")
            ctx.state.write_text(json.dumps(
                {"utc": utc(), "status": "TIMEOUT_NOTHING_LAUNCHED", "polls": polls,
                 "final_streak": streak}, ensure_ascii=False, indent=2))
            return 4
        snap = sample(ctx)
        polls += 1
        streak = streak + 1 if snap["idle"] else 0
        snap["streak"] = streak
        with open(ctx.snaps, "a") as f:
            f.write(json.dumps(snap, ensure_ascii=False) + "\n")
        ctx.state.write_text(json.dumps(
            {"utc": utc(), "pid": os.getpid(), "status": "WAITING_FOR_SHARED_GPU",
             "polls": polls, "consecutive_idle": streak, "required_streak": ctx.need,
             "bar": {"mem_used_mib_max": MEM_MAX_MIB, "util_pct_max": UTIL_MAX_PCT,
                     "n_gpu": EXPECT_GPUS},
             "last_reason": snap["reason"],
             "foreign_users": sorted({f.get("user", "?") for f in snap["foreign"]}),
             "jobs_launched": False}, ensure_ascii=False, indent=2))
        ctx.say(f"poll {polls}: idle={snap['idle']} streak={streak}/{ctx.need} -- {snap['reason'][:150]}")

        if streak >= ctx.need:
            ctx.say("streak satisfied; doing an immediate final re-check before launching")
            final = sample(ctx)
            with open(ctx.snaps, "a") as f:
                f.write(json.dumps({**final, "final_recheck": True}, ensure_ascii=False) + "\n")
            if not final["idle"]:
                ctx.say(f"final re-check FAILED ({final['reason'][:120]}); streak reset, "
                        f"launching nothing")
                streak = 0
                time.sleep(ctx.interval)
                continue
            return launch_all(ctx, jobs)
        time.sleep(ctx.interval)


if __name__ == "__main__":
    sys.exit(main())
