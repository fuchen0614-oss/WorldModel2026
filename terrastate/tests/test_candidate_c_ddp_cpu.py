#!/usr/bin/env python
"""Candidate C CPU-only 测试 T14：2-rank gloo DDP 的 exact resume 与全 rank 对称性。

CPU only：调用方须设 CUDA_VISIBLE_DEVICES=""。本文件自己 spawn 两个 worker 子进程
（--ddp-worker），因为 DDP 语义只能在真进程组里验证：混进单进程套件里，
"某个 rank 少走一次集合通信"或"只有 rank0 恢复了 RNG"这类 bug 根本测不出来。

覆盖：
  T14a  两 rank 都正常起落、rc=0、gloo 进程组干净销毁
  T14b  两 rank 的最终权重一致（DDP 梯度同步真的生效）
  T14c  rank0 独占写盘：checkpoint 不重复、无 .tmp 残留
  T14d  checkpoint 内含 per-rank RNG（rng_states_by_rank 长度 == world_size）
  T14e  --stop-after-step 中断后 resume，终点权重与未中断逐位一致
  T14f  优化器动量在 2-rank resume 后同样逐位一致
  T14g  合作式停止：rank0 读到 STOP_AFTER_CHECKPOINT 并广播，全 rank 完整保存
  T14h  合作式停止产出的 checkpoint 可 exact resume，终点与未中断一致
  T14i  非有限窗口的 MIN all_reduce 决定全 rank 一致（对称跳过，绝不半更新）

T14g/T14h 是 §12 的前置条件：正式 C1 启动前必须证明 cooperative stop 不只是
"能写出一个文件"，而是能从那个文件精确续训到预注册终点。

进程管理约定：只对本文件自己 Popen 出来的 PID 做 terminate；超时也不升级到
SIGKILL；不使用任何 pkill/killall 语义；不碰任何其他会话的进程。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import torch
import torch.distributed as dist

ROOT = Path(__file__).resolve().parents[1]              # .../terrastate
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WORLD = 2
N_TRAIN, N_VAL = 8, 2
TOTAL_STEPS = 4        # 8 cube / (per_gpu 1 x world 2) = 4 batch/rank, accum 1

from train.train_terrastate_candidate_c import run_training, STOP_FLAG_NAME  # noqa: E402
from train.terrastate_v2_common import relpath_of  # noqa: E402
from models.terrastate_candidate_c import value_sha16  # noqa: E402
from tests.candidate_c_fixtures import (  # noqa: E402
    Recorder, SyntheticCubeDataset, write_val_split_manifest,
)
# 复用单进程套件的 args 构造与优化器指纹，保证两套测试对"同一个东西"下同一个定义。
from tests.test_candidate_c_resume import (  # noqa: E402
    RecordingDataset, dir_size_mb, mk_args, opt_fingerprint,
)


def build_sets(train_dir, val_dir, n_train=N_TRAIN, n_val=N_VAL):
    """父进程与 worker 必须用同一处种子定义，否则两边的数据集悄悄不同。"""
    return (SyntheticCubeDataset(n_train, str(train_dir), seed=0),
            SyntheticCubeDataset(n_val, str(val_dir), seed=7))


def scaffold_ddp(tmp):
    tr, va = Path(tmp) / "train", Path(tmp) / "val"
    tr.mkdir(parents=True, exist_ok=True)
    va.mkdir(parents=True, exist_ok=True)
    _train, val = build_sets(tr, va)
    val_ids = [relpath_of(p, str(va)) for p in val.filepaths]
    man = write_val_split_manifest(Path(tmp) / "val_split.json", val_ids, [])
    return str(tr), str(va), str(man)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


# ------------------------------------------------------------------ worker 侧
def worker_train(a) -> dict:
    train, val = build_sets(a.train_dir, a.val_dir)
    consumed = []

    def factory(split, d):
        if split == "val":
            return val
        return RecordingDataset(train, a.train_dir, consumed)

    over = {}
    if a.resume:
        over["resume"] = a.resume
    if a.stop_after_step:
        over["stop_after_step"] = a.stop_after_step
    args = mk_args(arm="C1", factual_path="recursive", train_dir=a.train_dir,
                   val_dir=a.val_dir, val_split_manifest=a.manifest,
                   output_dir=a.output_dir, per_gpu_batch=1, global_batch=2,
                   max_epochs=1, ckpt_interval=2, val_interval=0, log_interval=1,
                   **over)
    s = run_training(args, factory)
    keep = ("status", "completion_reason", "step", "total_steps", "accum",
            "world_size", "global_batch", "per_gpu_batch", "seed", "lambdas",
            "model_value_sha16", "n_state_dict_tensors", "phase_step")
    return {"mode": "train", "rank": a.rank, "consumed": consumed,
            **{k: s.get(k) for k in keep},
            "endpoint_plans": [r.get("endpoint_plan") for r in s.get("loss_log", [])
                               if "endpoint_plan" in r]}


def worker_reduce(a) -> dict:
    """复现 trainer 的非有限窗口判定：MIN all_reduce 后全 rank 必须同一个决定。

    只要有任一 rank 的窗口非有限，所有 rank 都必须跳过这次更新——半更新会让
    两个 rank 的参数从此永久分叉，而 DDP 不会再告诉你。
    """
    dist.init_process_group("gloo")
    flags = [float(x) for x in a.flags.split(",")]
    mine = flags[a.rank]
    t = torch.tensor([mine])
    dist.all_reduce(t, op=dist.ReduceOp.MIN)
    decided_update = bool(t.item() > 0.5)
    dist.barrier()
    dist.destroy_process_group()
    return {"mode": "reduce", "rank": a.rank, "my_flag": mine,
            "reduced": float(t.item()), "decided_update": decided_update,
            "expect_update": bool(min(flags) > 0.5)}


def worker_main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ddp-worker", action="store_true")
    ap.add_argument("--mode", default="train", choices=["train", "reduce"])
    ap.add_argument("--result", required=True)
    ap.add_argument("--train-dir", default="")
    ap.add_argument("--val-dir", default="")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--output-dir", default="")
    ap.add_argument("--resume", default="")
    ap.add_argument("--stop-after-step", type=int, default=0)
    ap.add_argument("--flags", default="1.0,1.0")
    a = ap.parse_args(argv)
    a.rank = int(os.environ.get("RANK", "0"))
    torch.set_num_threads(2)
    out = {"rank": a.rank, "ok": False}
    try:
        out = worker_reduce(a) if a.mode == "reduce" else worker_train(a)
        out["ok"] = True
    except BaseException as exc:                                 # noqa: BLE001
        import traceback
        out.update({"ok": False, "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc()[-2000:]})
    finally:
        # 即使失败也要留下机器可读证据：父进程靠这个文件区分"崩了"和"跑完但结论不对"。
        p = Path(a.result)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with open(tmp, "w") as f:
            json.dump(out, f, ensure_ascii=False, sort_keys=True, indent=1, default=str)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, p)
    return 0 if out.get("ok") else 1


# ------------------------------------------------------------------ 父进程侧
def spawn_ddp(tag, scratch, *, mode="train", timeout=1800, **kw):
    """起 WORLD 个 worker，回收每个 rank 的 (rc, result JSON, log 路径)。

    进程管理：只对本函数自己 Popen 出来的 PID 调 terminate；超时也不升级到
    SIGKILL；不使用任何 pkill/killall 语义；不触碰其他会话的进程。
    """
    port = free_port()
    logs = Path(scratch) / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    procs = []
    for rank in range(WORLD):
        env = dict(os.environ)
        env.update({"MASTER_ADDR": "127.0.0.1", "MASTER_PORT": str(port),
                    "WORLD_SIZE": str(WORLD), "RANK": str(rank),
                    "LOCAL_RANK": str(rank), "CUDA_VISIBLE_DEVICES": "",
                    "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"})
        res = Path(scratch) / f"result_{tag}_r{rank}.json"
        argv = [sys.executable, str(Path(__file__).resolve()), "--ddp-worker",
                "--mode", mode, "--result", str(res)]
        for k, v in kw.items():
            argv += ["--" + k.replace("_", "-"), str(v)]
        lf = open(logs / f"{tag}_r{rank}.log", "w")
        procs.append((rank, subprocess.Popen(argv, env=env, stdout=lf,
                                             stderr=subprocess.STDOUT), lf, res))
    out, deadline = [], time.time() + timeout
    for rank, p, lf, res in procs:
        try:
            rc = p.wait(timeout=max(5.0, deadline - time.time()))
        except subprocess.TimeoutExpired:
            p.terminate()
            try:
                rc = p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                rc = None                       # 记为失败，不升级 SIGKILL
        lf.close()
        blob = {}
        if res.is_file():
            try:
                blob = json.loads(res.read_text())
            except Exception:                                    # noqa: BLE001
                blob = {"error": "result JSON 不可解析"}
        out.append({"rank": rank, "rc": rc, "result": blob,
                    "log": str(logs / f"{tag}_r{rank}.log")})
    return out


def all_ok(runs) -> bool:
    return all(r["rc"] == 0 and r["result"].get("ok") is True for r in runs)


def why(runs) -> str:
    return " | ".join(
        f"r{r['rank']}: rc={r['rc']} ok={r['result'].get('ok')}"
        + (f" err={str(r['result'].get('error'))[:80]}" if r["result"].get("error") else "")
        for r in runs)


def res(runs, rank=0) -> dict:
    return next(r["result"] for r in runs if r["rank"] == rank)


def ckpt_names(d) -> list:
    return sorted(p.name for p in Path(d).glob("checkpoint*.pt"))


def tmp_residue(d) -> list:
    return sorted(p.name for p in Path(d).iterdir() if ".tmp" in p.name)


def load_ck(path) -> dict:
    return torch.load(str(path), map_location="cpu", weights_only=False)


def w_sha(ck) -> str:
    return value_sha16(ck["b4_state_dict"])


def canon_rng(st):
    """把 RNG 状态压成可比较的纯量结构（tensor / ndarray 都要落到 bytes）。"""
    import numpy as np
    if isinstance(st, torch.Tensor):
        return ("t", bytes(st.cpu().numpy().tobytes()))
    if isinstance(st, np.ndarray):
        return ("a", st.tobytes())
    if isinstance(st, dict):
        return tuple(sorted((k, canon_rng(v)) for k, v in st.items()))
    if isinstance(st, (list, tuple)):
        return tuple(canon_rng(v) for v in st)
    return st


TITLES = {
    "T14a": "两 rank 正常起落、rc=0、gloo 进程组干净销毁",
    "T14b": "两 rank 最终权重一致（DDP 梯度同步生效）",
    "T14c": "rank0 独占写盘：checkpoint 不重复、无 .tmp 残留",
    "T14d": "checkpoint 内含 per-rank RNG（rng_states_by_rank 长度==world_size）",
    "T14e": "stop-after-step 中断后 resume，终点权重逐位一致",
    "T14f": "优化器动量在 2-rank resume 后逐位一致",
    "T14g": "合作式停止：rank0 读旗广播，全 rank 完整保存",
    "T14h": "合作式停止的 checkpoint 可 exact resume 到预注册终点",
    "T14i": "非有限窗口 MIN all_reduce 决定全 rank 一致（对称跳过）",
}


def bail(rec, ids, reason):
    """前置 run 失败时，把后续用例显式记为 FAIL 而不是静默跳过：
    报告必须始终覆盖完整 T14 矩阵，否则"没跑"会被误读成"通过"。"""
    for tid in ids:
        rec.check(tid, TITLES[tid], False, f"前置失败，无法评估：{reason}")


# ---------------------------------------------------------------- T14a–T14h
def t14_train_group(rec, scratch):
    tr, va, man = scaffold_ddp(scratch)
    common = dict(train_dir=tr, val_dir=va, manifest=man)
    dA = Path(scratch) / "runA"
    runs_a = spawn_ddp("A", scratch, output_dir=str(dA), **common)

    ok_a = rec.check("T14a", TITLES["T14a"], all_ok(runs_a), why(runs_a))
    if not ok_a:
        bail(rec, ["T14b", "T14c", "T14d", "T14e", "T14f", "T14g", "T14h"],
             "runA 未能两 rank 正常完成")
        return
    r0, r1 = res(runs_a, 0), res(runs_a, 1)
    shape_ok = (r0["model_value_sha16"] == r1["model_value_sha16"]
                and r0["step"] == r1["step"] == TOTAL_STEPS
                and r0["status"] == r1["status"] == "COMPLETE"
                and r0["completion_reason"] == "schedule_complete"
                and r0["world_size"] == 2 and r0["accum"] == 1
                and r0["global_batch"] == 2 and r0["per_gpu_batch"] == 1
                and r0["n_state_dict_tensors"] == r1["n_state_dict_tensors"] == 255)
    rec.check("T14b", TITLES["T14b"], shape_ok,
              f"sha r0={r0['model_value_sha16']} r1={r1['model_value_sha16']} | "
              f"step={r0['step']}/{r0['total_steps']} reason={r0['completion_reason']} "
              f"world={r0['world_size']} accum={r0['accum']} gb={r0['global_batch']} "
              f"tensors={r0['n_state_dict_tensors']}")

    names, residue = ckpt_names(dA), tmp_residue(dA)
    want = ["checkpoint_main.pt", "checkpoint_step2.pt", "checkpoint_step4.pt"]
    rec.check("T14c", TITLES["T14c"],
              names == want and not residue
              and (dA / "summary.json").is_file() and (dA / "loss_log.jsonl").is_file(),
              f"ckpt={names} 期望={want} | .tmp残留={residue or '无'} | "
              f"summary/loss_log={(dA / 'summary.json').is_file()}/"
              f"{(dA / 'loss_log.jsonl').is_file()}（每个 rank 都调 save，仅 rank0 落盘）")

    ckA = load_ck(dA / "checkpoint_main.pt")
    by_rank = ckA.get("rng_states_by_rank")
    n_rank = len(by_rank) if isinstance(by_rank, list) else -1
    keys_ok = (isinstance(by_rank, list)
               and all(isinstance(x, dict) for x in by_rank)
               and len({tuple(sorted(x)) for x in by_rank}) == 1)
    distinct = keys_ok and canon_rng(by_rank[0]) != canon_rng(by_rank[1])
    rec.check("T14d", TITLES["T14d"], n_rank == WORLD and keys_ok and distinct,
              f"len={n_rank} 期望={WORLD} | 结构一致={keys_ok} | "
              f"两 rank 状态不同={distinct}（seed_everything(seed+local_rank) "
              f"决定各 rank 必须不同；若相同说明只存了 rank0 的状态）")
    # ---- B：跑到 step2 中断；C：从 B 的 step2 在全新目录续到终点 ----------------
    dB, dC = Path(scratch) / "runB", Path(scratch) / "runC"
    runs_b = spawn_ddp("B", scratch, output_dir=str(dB), stop_after_step=2, **common)
    if not all_ok(runs_b):
        bail(rec, ["T14e", "T14f"], f"runB(stop-after-step) 失败：{why(runs_b)}")
        return dA, ckA, common
    b0 = res(runs_b, 0)
    runs_c = spawn_ddp("C", scratch, output_dir=str(dC), **common,
                       resume=str(dB / "checkpoint_step2.pt"))
    if not all_ok(runs_c):
        bail(rec, ["T14e", "T14f"], f"runC(resume) 失败：{why(runs_c)}")
        return dA, ckA, common
    c0 = res(runs_c, 0)
    ckC = load_ck(dC / "checkpoint_main.pt")
    same_w = w_sha(ckA) == w_sha(ckC)
    rec.check("T14e", TITLES["T14e"],
              same_w and b0["step"] == 2 and b0["total_steps"] == TOTAL_STEPS
              and c0["step"] == TOTAL_STEPS
              and c0["completion_reason"] == "schedule_complete"
              and res(runs_c, 1)["model_value_sha16"] == c0["model_value_sha16"],
              f"A={w_sha(ckA)} C={w_sha(ckC)} | B step={b0['step']} "
              f"total_steps={b0['total_steps']}(中断不得改预注册终点) | "
              f"C step={c0['step']} reason={c0['completion_reason']} | "
              f"C 两 rank 权重一致={res(runs_c, 1)['model_value_sha16'] == c0['model_value_sha16']}")

    fA, fC = opt_fingerprint(ckA["optimizer_state_dict"]), opt_fingerprint(ckC["optimizer_state_dict"])
    sA = ckA["scheduler_state_dict"].get("last_epoch")
    sC = ckC["scheduler_state_dict"].get("last_epoch")
    lin = ckC.get("lineage") or {}
    rec.check("T14f", TITLES["T14f"],
              fA == fC and sA == sC == TOTAL_STEPS
              and lin.get("resumed_within_phase") is True
              and lin.get("is_exact_resume") is False,
              f"opt指纹 A={fA[:16]} C={fC[:16]} 同={fA == fC} | "
              f"sched last_epoch A={sA} C={sC} | "
              f"lineage resumed_within_phase={lin.get('resumed_within_phase')} "
              f"is_exact_resume={lin.get('is_exact_resume')}（phase 内续训≠父 exact resume）")
    return dA, ckA, common


# ---------------------------------------------------------------- T14g / T14h
def t14_coop_group(rec, scratch, dA, ckA, common):
    """父进程在 spawn 前就放好停止旗：rank0 在 step1 的 poll 处读到并广播。

    STOP_AFTER_CHECKPOINT 不匹配 CKPT_GLOB，因此 guard_output_dir 不会把它误判成
    "目录里已有 run"。这正是 §12 要求的形状：先放旗，再让 run 自己走到检查点。
    """
    dD, dE = Path(scratch) / "runD", Path(scratch) / "runE"
    dD.mkdir(parents=True, exist_ok=True)
    (dD / STOP_FLAG_NAME).write_text("stop after next full optimizer step\n")
    runs_d = spawn_ddp("D", scratch, output_dir=str(dD), **common)
    if not all_ok(runs_d):
        bail(rec, ["T14g", "T14h"], f"runD(cooperative stop) 失败：{why(runs_d)}")
        return
    d0, d1 = res(runs_d, 0), res(runs_d, 1)
    coop = "checkpoint_step1_cooperative_stop.pt"
    names, residue = ckpt_names(dD), tmp_residue(dD)
    ckD = load_ck(dD / coop) if (dD / coop).is_file() else {}
    n_rank_d = len(ckD.get("rng_states_by_rank") or [])
    rec.check("T14g", TITLES["T14g"],
              names == [coop] and not residue and n_rank_d == WORLD
              and d0["completion_reason"] == d1["completion_reason"] == "cooperative_stop"
              and d0["status"] == "COMPLETE" and d0["step"] == d1["step"] == 1
              and d0["total_steps"] == TOTAL_STEPS,
              f"ckpt={names} 期望=[{coop}] | .tmp={residue or '无'} | "
              f"rng_states_by_rank={n_rank_d}（all_gather_object 是集合通信："
              f"若只有 rank0 调 save，两 rank 都会挂死而非 rc=0） | "
              f"reason={d0['completion_reason']}/{d1['completion_reason']} "
              f"step={d0['step']}/{d0['total_steps']} | 未写 checkpoint_last="
              f"{'checkpoint_last.pt' not in names}")

    runs_e = spawn_ddp("E", scratch, output_dir=str(dE), **common,
                       resume=str(dD / coop))
    if not all_ok(runs_e):
        bail(rec, ["T14h"], f"runE(从合作停止点 resume) 失败：{why(runs_e)}")
        return
    e0 = res(runs_e, 0)
    ckE = load_ck(dE / "checkpoint_main.pt")
    fA, fE = opt_fingerprint(ckA["optimizer_state_dict"]), opt_fingerprint(ckE["optimizer_state_dict"])
    rec.check("T14h", TITLES["T14h"],
              w_sha(ckA) == w_sha(ckE) and fA == fE
              and e0["step"] == TOTAL_STEPS
              and e0["completion_reason"] == "schedule_complete"
              and e0["model_value_sha16"] == res(runs_e, 1)["model_value_sha16"],
              f"权重 A={w_sha(ckA)} E={w_sha(ckE)} 同={w_sha(ckA) == w_sha(ckE)} | "
              f"opt指纹同={fA == fE} | E step={e0['step']} "
              f"reason={e0['completion_reason']} | E 两 rank 一致="
              f"{e0['model_value_sha16'] == res(runs_e, 1)['model_value_sha16']}")


# ---------------------------------------------------------------- T14i
def t14_reduce_group(rec, scratch):
    """两种旗组合：只要任一 rank 的窗口非有限，全体必须对称跳过这次更新。"""
    bad, seen = [], []
    for flags, expect in (("1.0,0.0", False), ("1.0,1.0", True)):
        tag = "reduce_" + flags.replace(".", "").replace(",", "_")
        runs = spawn_ddp(tag, scratch, mode="reduce", timeout=600, flags=flags)
        if not all_ok(runs):
            bad.append(f"flags={flags} 未能完成：{why(runs)}")
            continue
        dec = [res(runs, r)["decided_update"] for r in range(WORLD)]
        seen.append(f"flags={flags}→决定={dec}(期望全体={expect})")
        if len(set(dec)) != 1 or dec[0] is not expect:
            bad.append(f"flags={flags} 决定={dec} 期望全体={expect}")
    rec.check("T14i", TITLES["T14i"], not bad,
              (" | ".join(seen) or "无结果")
              + (f" || 违规={bad}" if bad
                 else " | 全 rank 同一决定：绝不出现半更新导致的参数永久分叉"))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--ddp-worker" in argv:            # 子进程入口：先分流，别碰父进程的参数表
        return worker_main(argv)
    ap = argparse.ArgumentParser(
        description="Candidate C CPU-only 测试 T14（自 spawn 2-rank gloo DDP）")
    ap.add_argument("--report", default="", help="机器可读报告落盘路径 (JSON)")
    ap.add_argument("--scratch", default="",
                    help="临时产物根目录；默认在 /tmp 下新建带时间戳目录，且不自动删除")
    ap.add_argument("--only", default="", help="逗号分隔：train / reduce（默认全跑）")
    a = ap.parse_args(argv)
    if os.environ.get("CUDA_VISIBLE_DEVICES", "unset") != "":
        print("WARN CUDA_VISIBLE_DEVICES 未设为空串；本套件仍强制 CPU", flush=True)
    torch.set_num_threads(2)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    scratch = (Path(a.scratch) if a.scratch
               else Path(tempfile.mkdtemp(prefix=f"cc_ddp_{stamp}_")))
    scratch.mkdir(parents=True, exist_ok=True)
    print(f"scratch = {scratch}  (不自动删除：失败证据必须留存)", flush=True)
    only = {s.strip().lower() for s in a.only.split(",") if s.strip()}
    rec = Recorder("candidate_c_ddp_cpu_T14")
    if not only or "train" in only:
        got = t14_train_group(rec, scratch)
        if got:                    # None 时 bail 已把 T14b–T14h 全部记为 FAIL
            t14_coop_group(rec, scratch, *got)
    if not only or "reduce" in only:
        t14_reduce_group(rec, scratch)

    report = rec.report()
    report["world_size"], report["total_steps"] = WORLD, TOTAL_STEPS
    report["scratch_dir"] = str(scratch)
    report["scratch_mb"] = round(dir_size_mb(scratch), 1)
    print(json.dumps({k: v for k, v in report.items() if k != "checks"},
                     indent=2, ensure_ascii=False), flush=True)
    if a.report:
        import eval.eval_terrastate_candidate_c_q4 as ccq4
        report["provenance"] = ccq4.provenance(
            {"suite": report["suite"], "scratch_dir": str(scratch)})
        sha = ccq4.atomic_write_json(a.report, report)
        print(f"report -> {a.report}  sha256={sha}", flush=True)
    return 0 if report["n_fatal_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
