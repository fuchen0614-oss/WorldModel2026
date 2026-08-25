#!/usr/bin/env python3
"""E0 六项任务守护进程 —— 持续监控到六项全部产出结果 JSON。

策略（按用户 2026-08-20 指示）：
  * 不礼让：启动后不因外来进程停自己的任务；别人 kill 我们，我们等卡空闲后重跑。
  * 只补缺口：某任务既没有结果 JSON、也没有存活进程 => 才重启它。
  * 绝不碰别人的进程：外来 PID 只记录，从不发信号。
  * 绝不与存活的 runner 抢任务：先按 --output-dir 匹配存活进程。
  * 不删除已有输出；重跑前把残留目录改名成 .killed_<ts> 归档，不用 rm。

只读 nvidia-smi，不建 CUDA context。CPU 占用极低（30s 一轮）。
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RETRY_DIR = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/ops/e0_q1q2q3_11904_vs_14880/20260820_100718")
TS_ROOT = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate")
PY = "/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python"
DATA_ROOT = "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet"
PLANB = "/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb"
OBJ = "/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256"

CKPT_14880 = f"{OBJ}/a5/a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f.pt"
CKPT_11904 = f"{OBJ}/64/644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd.pt"
SHA_14880 = "a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f"
SHA_11904 = "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd"

VAL_MANIFEST = f"{PLANB}/artifacts/protocols/b4_eval/val_chopped.manifest.json"
OODT_MANIFEST = f"{PLANB}/evaluations/greenearthnet_oodt_20260719_214234/greenearthnet_oodt_chopped_manifest.json"
Q3_PROTOCOL = f"{TS_ROOT}/artifacts/protocols/extreme_audit_oodt_v1"

LOG = RETRY_DIR / "e0_guardian.log"
STATE = RETRY_DIR / "e0_guardian_state.json"
LOCK = RETRY_DIR / ".e0_guardian.lock"
SNAP = RETRY_DIR / "guardian_gpu_snapshots.jsonl"

POLL_SECONDS = 30
# 一张卡上我们自己的任务加载后约 1.4-40 GB；判"别人在用"看外来 PID，不看总显存。
FOREIGN_FREE_MEM_MIB = 2048   # 无外来 PID 且显存低于此值 => 可用

# 六项任务：名字必须与冻结清单一致；物理卡是本节点的 2/4/5/6。
JOBS = [
    {"name": "gpu1_v14880_oodt_q1q2",      "pgpu": 2, "kind": "q1q2",
     "ckpt": CKPT_14880, "sha": SHA_14880, "split": "ood-t_chopped",
     "val_dir": f"{DATA_ROOT}/ood-t_chopped", "manifest": OODT_MANIFEST, "targets": 1904},
    {"name": "gpu4_legacy11904_oodt_q1q2", "pgpu": 4, "kind": "q1q2",
     "ckpt": CKPT_11904, "sha": SHA_11904, "split": "ood-t_chopped",
     "val_dir": f"{DATA_ROOT}/ood-t_chopped", "manifest": OODT_MANIFEST, "targets": 1904},
    {"name": "gpu0_v14880_val_q1q2",       "pgpu": 5, "kind": "q1q2",
     "ckpt": CKPT_14880, "sha": SHA_14880, "split": "val",
     "val_dir": f"{DATA_ROOT}/val_chopped", "manifest": VAL_MANIFEST, "targets": 952},
    {"name": "gpu3_legacy11904_val_q1q2",  "pgpu": 6, "kind": "q1q2",
     "ckpt": CKPT_11904, "sha": SHA_11904, "split": "val",
     "val_dir": f"{DATA_ROOT}/val_chopped", "manifest": VAL_MANIFEST, "targets": 952},
    {"name": "gpu2_v14880_oodt_q3",        "pgpu": 5, "kind": "q3",
     "ckpt": CKPT_14880, "sha": SHA_14880, "pairs": 84},
    {"name": "gpu5_legacy11904_oodt_q3",   "pgpu": 6, "kind": "q3",
     "ckpt": CKPT_11904, "sha": SHA_11904, "pairs": 84},
]
# 实测本 evaluator 的产物名（2026-08-20 gpu0 跑完后确认）：
#   q1q2 -> state_contract_exclusive.json      q3 -> extreme_state_audit.json
# 与聚合器 find_result_json() 的 fallback 一致：目录里任一非 INTERRUPTED 的 *.json 即算产出。
RESULT_NAME = {"q1q2": ["state_contract_exclusive.json", "b4_exclusive_contract.json",
                        "contract_report.json"],
               "q3": ["extreme_state_audit.json"]}
# 同一张卡上的先后次序：Q1/Q2 先，Q3 后（与现有 runner 一致，避免同卡并发）
ORDER = {j["name"]: i for i, j in enumerate(JOBS)}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def smi(query: str, extra: str = "") -> list[str]:
    cmd = ["nvidia-smi", f"--query-{query}", "--format=csv,noheader,nounits"]
    if extra:
        cmd.insert(1, extra)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return [l.strip() for l in out.stdout.splitlines() if l.strip()]
    except Exception as e:  # nvidia-smi 卡住/不可用时不崩，视作未知
        log(f"nvidia-smi failed: {e!r}")
        return []


def gpu_uuid_map() -> dict[int, str]:
    m = {}
    for line in smi("gpu=index,uuid"):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            try:
                m[int(parts[0])] = parts[1]
            except ValueError:
                pass
    return m


def owner(pid: str) -> str:
    try:
        r = subprocess.run(["ps", "-o", "user=", "-p", str(pid)],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "?"
    except Exception:
        return "?"


def gpu_state() -> dict[int, dict]:
    """每张卡：显存、利用率、计算进程（区分我们 vs 外来）。只读。"""
    me = os.environ.get("USER") or "zjliu17"
    uuids = gpu_uuid_map()
    rev = {v: k for k, v in uuids.items()}
    st = {i: {"mem": None, "util": None, "mine": [], "foreign": []} for i in uuids}
    for line in smi("gpu=index,memory.used,utilization.gpu"):
        p = [x.strip() for x in line.split(",")]
        if len(p) >= 3:
            try:
                i = int(p[0])
                st.setdefault(i, {"mine": [], "foreign": []})
                st[i]["mem"] = int(p[1])
                st[i]["util"] = int(p[2])
            except ValueError:
                pass
    for line in smi("compute-apps=gpu_uuid,pid,used_memory"):
        p = [x.strip() for x in line.split(",")]
        if len(p) >= 3 and p[0] in rev:
            i = rev[p[0]]
            rec = {"pid": p[1], "mem": p[2], "user": owner(p[1])}
            (st[i]["mine"] if rec["user"] == me else st[i]["foreign"]).append(rec)
    return st


def live_jobs() -> dict[str, int]:
    """按 --output-dir 把存活的 eval 进程映射到任务名（含现有 runner 起的）。"""
    out = {}
    try:
        r = subprocess.run(["pgrep", "-u", os.environ.get("USER", "zjliu17"), "-af",
                            "eval_b4_exclusive_contract|extreme_state_audit"],
                           capture_output=True, text=True, timeout=15)
        for line in r.stdout.splitlines():
            if "pgrep" in line:
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            pid, cmd = parts
            if "--output-dir" not in cmd:
                continue
            od = cmd.split("--output-dir", 1)[1].split()[0]
            name = Path(od).name
            try:
                out[name] = int(pid)
            except ValueError:
                pass
    except Exception as e:
        log(f"pgrep failed: {e!r}")
    return out


def runner_alive(pgpu: int) -> bool:
    """对应物理卡的 runner_physical_gpuN.sh 是否还在（它会自己跑第二波）。"""
    try:
        r = subprocess.run(["pgrep", "-u", os.environ.get("USER", "zjliu17"), "-f",
                            f"runner_physical_gpu{pgpu}.sh"],
                           capture_output=True, text=True, timeout=15)
        return bool(r.stdout.strip())
    except Exception:
        return False


def shard_exit_ok(name: str) -> bool:
    """runner 分片里已记 exit_code==0 => 该任务确已正常收尾。"""
    for f in RETRY_DIR.glob("launch_record_shard_pgpu*.json"):
        try:
            for j in json.loads(f.read_text()).get("jobs", []):
                if j.get("name") == name and j.get("exit_code") == 0:
                    return True
        except Exception:
            continue
    return False


def done(job: dict) -> bool:
    """产出判定：任一已知结果 JSON 存在，或 runner 已记录 exit_code==0。

    产物名以实测为准；再退一步接受目录内任意非 INTERRUPTED 的 *.json（与聚合器
    find_result_json 的 fallback 同语义），避免把已完成的任务误判成缺口而重跑。
    """
    d = RETRY_DIR / "runs" / job["name"]
    if (d / "INTERRUPTED.json").exists():
        return False
    if not d.exists():
        return False
    for n in RESULT_NAME[job["kind"]]:
        if (d / n).is_file():
            return True
    if any(p.name != "INTERRUPTED.json" for p in d.glob("*.json")):
        return True
    return shard_exit_ok(job["name"])

def build_cmd(job: dict) -> list[str]:
    out_dir = str(RETRY_DIR / "runs" / job["name"])
    if job["kind"] == "q1q2":
        return [PY, f"{TS_ROOT}/eval/eval_b4_exclusive_contract.py",
                "--ckpt", job["ckpt"], "--val-dir", job["val_dir"],
                "--data-manifest", job["manifest"], "--dataset-root", DATA_ROOT,
                "--split", job["split"], "--sections", "q1q2",
                "--batch-size", "1", "--num-data-workers", "2", "--workers", "4",
                "--device", "cuda", "--output-dir", out_dir]
    return [PY, f"{TS_ROOT}/eval/extreme_state_audit.py",
            "--protocol-dir", Q3_PROTOCOL, "--dataset-root", DATA_ROOT,
            "--ckpt-exclusive", job["ckpt"], "--batch-size", "1",
            "--num-data-workers", "2", "--workers", "4", "--n-boot", "10000",
            "--evidence-role", "final", "--device", "cuda", "--dump-per-cube",
            "--output-dir", out_dir]


def archive_partial(job: dict) -> str | None:
    """被 kill 后的残留输出改名归档，不删除（用户要求不再 rm）。"""
    d = RETRY_DIR / "runs" / job["name"]
    if not d.exists() or not any(d.iterdir()):
        return None
    dst = d.with_name(d.name + ".killed_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    shutil.move(str(d), str(dst))
    return dst.name


def relaunch(job: dict, st: dict) -> dict | None:
    pgpu = job["pgpu"]
    uuids = gpu_uuid_map()
    g = st.get(pgpu, {})
    foreign = g.get("foreign", [])
    mem = g.get("mem")
    if foreign:
        log(f"DEFER {job['name']}: GPU {pgpu} 有外来进程 "
            f"{[(f['pid'], f['user']) for f in foreign]}（只记录，不干预）")
        return None
    if mem is not None and mem > FOREIGN_FREE_MEM_MIB:
        log(f"DEFER {job['name']}: GPU {pgpu} 显存 {mem}MiB 偏高但无外来 PID；等下一轮确认")
        return None

    arch = archive_partial(job)
    if arch:
        log(f"归档残留输出 -> runs/{arch}")
    out_dir = RETRY_DIR / "runs" / job["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = RETRY_DIR / "logs" / f"{job['name']}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = str(pgpu)
    cmd = build_cmd(job)
    started = now()
    with open(log_file, "ab") as lf:
        lf.write(f"\n===== guardian relaunch {started} on physical GPU {pgpu} =====\n".encode())
        lf.flush()
        p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                             env=env, cwd=str(TS_ROOT), start_new_session=True)
    (RETRY_DIR / "logs" / f"{job['name']}.pid").write_text(str(p.pid))
    rec = {"name": job["name"], "physical_gpu": pgpu, "gpu_uuid": uuids.get(pgpu),
           "pid": p.pid, "started_utc": started, "hostname": os.uname().nodename,
           "cmd": cmd, "launched_by": "guardian",
           "cuda_visible_devices": str(pgpu)}
    (RETRY_DIR / f"guardian_launch_{job['name']}.json").write_text(json.dumps(rec, indent=1))
    log(f"RELAUNCHED {job['name']} pid={p.pid} physical_gpu={pgpu} uuid={uuids.get(pgpu)}")
    return rec


def write_state(st: dict, live: dict, waiting: list[str], relaunched: list[dict]) -> None:
    payload = {
        "updated_utc": now(),
        "hostname": os.uname().nodename,
        "guardian_pid": os.getpid(),
        "policy": {
            "yield_to_foreign_after_launch": False,
            "may_be_killed_by_others": True,
            "on_killed": "wait for the card to free up, then relaunch",
            "never_signals_foreign_processes": True,
            "never_deletes_output": "partial output is renamed to .killed_<ts>",
        },
        "jobs": {j["name"]: {
            "physical_gpu": j["pgpu"],
            "kind": j["kind"],
            "done": done(j),
            "live_pid": live.get(j["name"]),
            "runner_alive": runner_alive(j["pgpu"]),
        } for j in JOBS},
        "gpu": {str(i): {"mem": v.get("mem"), "util": v.get("util"),
                         "mine": v.get("mine", []), "foreign": v.get("foreign", [])}
                for i, v in st.items() if i in {2, 4, 5, 6}},
        "waiting_for_gpu": waiting,
        "relaunched_this_round": [r["name"] for r in relaunched],
        "remaining": [j["name"] for j in JOBS if not done(j)],
    }
    STATE.write_text(json.dumps(payload, indent=1))


def main() -> int:
    # 单实例锁
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        try:
            old = int(LOCK.read_text().strip())
            os.kill(old, 0)
            log(f"另一个 guardian 已在运行 pid={old}；退出")
            return 0
        except (ValueError, ProcessLookupError, PermissionError):
            LOCK.write_text(str(os.getpid()))

    stop = {"flag": False}
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.update(flag=True))

    log(f"guardian 启动 pid={os.getpid()} host={os.uname().nodename} "
        f"poll={POLL_SECONDS}s policy=no-yield/allow-external-kill/auto-relaunch")
    rnd = 0
    try:
        while not stop["flag"]:
            rnd += 1
            st = gpu_state()
            live = live_jobs()
            with open(SNAP, "a") as f:
                f.write(json.dumps({"utc": now(), "round": rnd,
                                    "gpu": {str(i): {"mem": v.get("mem"), "util": v.get("util"),
                                                     "foreign": v.get("foreign", [])}
                                            for i, v in st.items() if i in {2, 4, 5, 6}}}) + "\n")

            remaining = [j for j in JOBS if not done(j)]
            if not remaining:
                log("六项任务全部产出结果 JSON；guardian 退出（验收由 CPU 聚合脚本执行）")
                write_state(st, live, [], [])
                return 0

            waiting, relaunched = [], []
            busy_pgpu = {JOBS[ORDER[n]]["pgpu"] for n in live if n in ORDER}
            for job in remaining:
                name = job["name"]
                if name in live:
                    continue  # 正在跑
                if runner_alive(job["pgpu"]):
                    # 原 runner 还活着，它会自己按顺序起后续任务，不抢
                    waiting.append(f"{name} (原 runner 仍在管 GPU {job['pgpu']})")
                    continue
                if job["pgpu"] in busy_pgpu:
                    waiting.append(f"{name} (同卡 GPU {job['pgpu']} 上另一任务在跑)")
                    continue
                rec = relaunch(job, st)
                if rec:
                    relaunched.append(rec)
                    busy_pgpu.add(job["pgpu"])
                else:
                    waiting.append(f"{name} (GPU {job['pgpu']} 暫不可用)")

            if rnd % 10 == 1 or relaunched:
                log(f"round {rnd}: 剩余 {[j['name'] for j in remaining]} | "
                    f"在跑 {sorted(live)} | 等待 {waiting}")
            write_state(st, live, waiting, relaunched)
            for _ in range(POLL_SECONDS):
                if stop["flag"]:
                    break
                time.sleep(1)
        log("收到停止信号；guardian 退出（不影响已启动的评测任务）")
        return 0
    finally:
        try:
            if LOCK.exists() and LOCK.read_text().strip() == str(os.getpid()):
                LOCK.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
