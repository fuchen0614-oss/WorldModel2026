#!/usr/bin/env python
"""Candidate C CPU-only 测试 T12/T13、T15–T18。

T14（2-rank gloo DDP resume）在 tests/test_candidate_c_ddp_cpu.py，因为它必须
自起子进程，混在本文件里会让单进程用例也被 torchrun 语义污染。

CPU only：调用方须设 CUDA_VISIBLE_DEVICES=""。本文件只读父 checkpoint，
所有产物写入 --scratch 临时目录；不写任何正式 run，不注册任何权重，
不改 obsworld/**，不碰 ops/ 下已冻结的 manifest（只读校验其 SHA）。

覆盖：
  T12 原子 checkpoint + CPU roundtrip（无 .tmp 残留、由 contract_cfg 严格重建）
  T13 中断 vs 未中断的 exact resume（权重/优化器/调度器逐位一致）+ 四条 fail-closed
  T15 C1/C0R 的样本 ID、曝光、更新数、batch、seed 审计（唯一变量 = 递归段路径）
  T16 评测器严格装载（AST 层面不存在 strict=False，且坏 checkpoint 必抛）
  T17 评测器 per-cube JSON + 数组 + provenance 完整性
  T18 空白检查 + 已验收世代的定向回归

两个刻意的设计约束，写在这里以免以后被"优化"掉：
  1) T13 必须 --val-interval 0。validate_candidate_c 会消耗全局 RNG；若它只在
     run A 的 step 2 触发而 run C 恢复后不再触发，RNG 流就分叉，"exact resume"
     会因为一个与 resume 无关的原因判失败。
  2) 全程不得传 --verify-data-manifest。合成 cube 只存在于内存，
     data_manifest_sha256 会去 stat 不存在的文件。正式 run 必须开启该开关，
     那里的数据是真的。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]              # .../terrastate
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPO = ROOT.parent                                      # git toplevel: WorldModel2026v2

from models.terrastate_candidate_c import (  # noqa: E402
    PARENT_FILE_SHA256, PARENT_N_TENSORS, PARENT_VALUE_SHA16, TerraStateCandidateC,
    value_sha16,
)
from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from train.train_terrastate_candidate_c import (  # noqa: E402
    build_argparser, endpoint_rng, run_training,
)
# eval 包名与内建 eval 同形；整模块导入既避免与 trainer 的 build_argparser 撞名，
# 也让 T16 能对同一个 module 对象做 AST 扫描与功能测试。
import eval.eval_terrastate_candidate_c_q4 as ccq4  # noqa: E402
from tests.candidate_c_fixtures import (  # noqa: E402
    Recorder, SyntheticCubeDataset, write_val_split_manifest,
)

# 本轮新建的文件：git 尚未跟踪，`git diff --check` 看不见它们，T18 必须自己扫。
NEW_FILES = (
    "models/terrastate_candidate_c.py",
    "train/train_terrastate_candidate_c.py",
    "eval/eval_terrastate_candidate_c_q4.py",
    "tests/candidate_c_fixtures.py",
    "tests/test_candidate_c_contract.py",
    "tests/test_candidate_c_resume.py",
    "tests/test_candidate_c_ddp_cpu.py",
)
# 已验收 11,904→14,880 世代与五个 evaluator 共用；本轮必须逐字节等于 HEAD。
# 注意 train/train_terrastate_v2.py **不在**此列：它有其他会话的合法改动，
# 只能锁 lr_factor 这一个函数（T18g），不能锁整文件。
FROZEN_FILES = (
    "models/plan_b_b4.py",
    "models/plan_b_b4_exclusive.py",
    "models/terrastate_v2.py",
)
FROZEN_MANIFEST_DIR = ROOT / "ops/candidate_c_nightly/20260820T155316Z/manifests"
EXPECT_SPLIT_MANIFEST_SHA = (
    "160c3ccc5075d386ecdc235a61806610d8475cc46f17973b94a5a9a37ed3cd6b")
EXPECT_Q4_MANIFEST_SHA = (
    "d0a4c6564516ea62f7eda9ebc4018433d1357391ad3a2a3bd8070de1a54e1e0e")

from train.terrastate_v2_common import relpath_of  # noqa: E402


# ---------------------------------------------------------------------- 工具
def git_head_bytes(rel: str):
    """HEAD 版本的字节（rel 相对 git toplevel 的 terrastate/）；取不到返回 None。"""
    try:
        p = subprocess.run(["git", "show", f"HEAD:terrastate/{rel}"],
                           cwd=str(REPO), capture_output=True, timeout=120)
        return p.stdout if p.returncode == 0 else None
    except Exception:                                            # noqa: BLE001
        return None


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def opt_fingerprint(osd: dict) -> str:
    """优化器状态的确定性指纹：按 param-id 排序后哈希 step/exp_avg/exp_avg_sq。

    只比权重的 value_sha16 会漏掉"权重对了但动量错了"的 resume bug——那种 run
    继续训练几步就会偏离，却能通过一切只看权重的检查。
    """
    h = hashlib.sha256()
    for pid in sorted(osd.get("state", {}).keys(), key=lambda x: str(x)):
        h.update(str(pid).encode())
        st = osd["state"][pid]
        for k in sorted(st.keys()):
            v = st[k]
            h.update(k.encode())
            if torch.is_tensor(v):
                h.update(v.detach().cpu().contiguous().numpy().tobytes())
            else:
                h.update(repr(v).encode())
    for gi, g in enumerate(osd.get("param_groups", [])):
        h.update(f"g{gi}".encode())
        for k in sorted(kk for kk in g.keys() if kk != "params"):
            h.update(f"{k}={g[k]!r}".encode())
    return h.hexdigest()[:32]


class GeoCubeDataset(SyntheticCubeDataset):
    """把合成 cube 摆成 `<TILE>/<TILE>_<i>.nc`，让评测器的地理分组走真实规则。

    ccq4.geo_group_of 对没有 `minicube_` 前缀的 id 取首段目录，因此 relpath
    `29SND/29SND_0.nc` 的 geo_group 就是 `29SND`。geo-cluster bootstrap 需要
    至少 2 个组才有意义，所以 tiles 默认给 3 个。
    """

    def __init__(self, n, root, tiles=("29SND", "30TXM", "33UUB"), **kw):
        super().__init__(n, root, **kw)
        self.tiles = tuple(tiles)
        self.filepaths = [f"{root}/{tiles[i % len(tiles)]}/"
                          f"{tiles[i % len(tiles)]}_{i}.nc" for i in range(n)]

    def __getitem__(self, i):
        d = super().__getitem__(i)
        d["filepath"] = self.filepaths[i]
        d["cubename"] = Path(self.filepaths[i]).stem
        return d


class RecordingDataset(torch.utils.data.Dataset):
    """记录被消费的 cube id 顺序（num_workers=0 时 == __getitem__ 顺序）。

    T15 要证明两臂看到的 EO 样本完全一致，靠的是这个 sink 而不是"配置看起来一样"。
    """

    def __init__(self, base, root, sink):
        self.base, self.root, self.sink = base, root, sink
        self.filepaths = base.filepaths

    def __len__(self):
        return len(self.base)

    def __getitem__(self, i):
        d = self.base[i]
        self.sink.append(relpath_of(d["filepath"], self.root))
        return d


def mk_args(**over):
    """经真实 argparser 造 args，保证测试用的默认值与正式 CLI 逐字同源。

    绝不手写 Namespace：那样 CLI 改了默认值而测试不知道，"测过了"就成了假话。
    """
    argv = ["--arm", str(over.pop("arm", "C1")),
            "--factual-path", str(over.pop("factual_path", "recursive")),
            "--train-dir", str(over.pop("train_dir")),
            "--val-dir", str(over.pop("val_dir")),
            "--val-split-manifest", str(over.pop("val_split_manifest")),
            "--output-dir", str(over.pop("output_dir")),
            "--device", "cpu", "--num-workers", "0", "--deterministic"]
    for k, v in over.items():
        flag = "--" + k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                argv.append(flag)
        else:
            argv += [flag, str(v)]
    return build_argparser().parse_args(argv)


def scaffold(tmp, n_train=8, n_val=2, geo=False, seed=0):
    """合成 train/val 数据集 + split manifest（val_dev = 全部 val id）。"""
    tmp = Path(tmp)
    tr_dir, va_dir = tmp / "train", tmp / "val"
    tr_dir.mkdir(parents=True, exist_ok=True)
    va_dir.mkdir(parents=True, exist_ok=True)
    cls = GeoCubeDataset if geo else SyntheticCubeDataset
    train = cls(n_train, str(tr_dir), seed=seed)
    val = cls(n_val, str(va_dir), seed=seed + 7)
    val_ids = [relpath_of(p, str(va_dir)) for p in val.filepaths]
    man = write_val_split_manifest(tmp / "val_split.json", val_ids, [])
    return {"train_dir": str(tr_dir), "val_dir": str(va_dir), "manifest": str(man),
            "train": train, "val": val, "val_ids": val_ids,
            "factory": (lambda split, d: val if split == "val" else train)}


# ------------------------------------------------- T12 原子 checkpoint + roundtrip
def train_min(scratch, tag="t12", geo=False):
    """最小两更新 run：4 train / 2 val，per_gpu=global=2 -> accum=1，ckpt@2。

    T16/T17 复用它产出的 checkpoint，避免为了拿一个 checkpoint 重训四遍。
    """
    S = scaffold(scratch / tag, n_train=4, n_val=2, geo=geo)
    out = scratch / tag / "run"
    args = mk_args(train_dir=S["train_dir"], val_dir=S["val_dir"],
                   val_split_manifest=S["manifest"], output_dir=out,
                   per_gpu_batch=2, global_batch=2, max_steps=2,
                   ckpt_interval=2, val_interval=2, log_interval=1)
    return run_training(args, S["factory"]), out, S, args


def t12_atomic_ckpt_roundtrip(rec, scratch):
    summ, out, S, args = train_min(scratch, "t12")
    names = sorted(p.name for p in out.glob("checkpoint*.pt"))
    residue = sorted(p.name for p in out.iterdir() if ".tmp" in p.name)
    rec.check("T12a", "原子写：只留最终 checkpoint，无 .tmp 残留",
              names == ["checkpoint_main.pt", "checkpoint_step2.pt"] and not residue,
              f"files={names} tmp_residue={residue}")

    ck = torch.load(out / "checkpoint_main.pt", map_location="cpu", weights_only=False)
    sd = ck["b4_state_dict"]
    all_cpu = all(v.device.type == "cpu" for v in sd.values() if torch.is_tensor(v))
    rec.check("T12b", f"CPU map_location roundtrip：{PARENT_N_TENSORS} 张量全在 CPU",
              len(sd) == PARENT_N_TENSORS and all_cpu,
              f"n={len(sd)} all_cpu={all_cpu}")

    v16 = value_sha16(sd)
    rec.check("T12c", "checkpoint 权重 value_sha16 == summary 记录",
              v16 == summ["model_value_sha16"],
              f"ckpt={v16} summary={summ['model_value_sha16']}")

    hp = contextformer6m_hparams(pvt_pretrained=False)
    rebuilt = TerraStateCandidateC(hp, contract_cfg=dict(ck["contract_cfg"]))
    missing, unexpected = rebuilt.load_state_dict(sd, strict=True)
    rec.check("T12d", "仅凭 contract_cfg 就能严格重建（strict=True 无偏差）",
              not missing and not unexpected and value_sha16(rebuilt.state_dict()) == v16,
              f"missing={list(missing)} unexpected={list(unexpected)}")

    lin = dict(ck.get("lineage") or {})
    prov_ok = {
        "arch": ck.get("arch") == TerraStateCandidateC.ARCH,
        "route": ck.get("route_version") == TerraStateCandidateC.ROUTE_VERSION,
        "phase": ck.get("phase") == "candidate_c_phase_ii",
        "arm": ck.get("arm") == "C1",
        "path": ck.get("factual_path") == "recursive",
        "phase_step": int(ck.get("phase_step", -1)) == 2 == int(ck.get("step", -1)),
        "parent_file_sha": ck["sha"].get("parent_file_sha256") == PARENT_FILE_SHA256,
        "inherited_sha": lin.get("inherited_value_sha16") == PARENT_VALUE_SHA16,
        "fork_kind": lin.get("fork_kind") == "weights_only_phase_ii_fork",
        "not_exact_resume": lin.get("is_exact_resume") is False,
        "parent_opt_discarded":
            lin.get("parent_optimizer_scheduler_deliberately_discarded") is True,
        "disclaimer_present": bool(ck.get("not_exact_resume_of_parent")),
        "alpha_is_1": float(ck.get("alpha", 0.0)) == 1.0,
        "simulator_blocked": "BLOCKED_SIMULATOR" in str(ck.get("simulator_status", "")),
    }
    rec.check("T12e", "provenance 完整：父身份 / fork 性质 / phase_step=step",
              all(prov_ok.values()),
              " ".join(f"{k}={v}" for k, v in prov_ok.items()))

    summ_ok = (summ["status"] == "COMPLETE"
               and summ["completion_reason"] == "schedule_complete"
               and summ["step"] == summ["total_steps"] == 2
               and all(v == 0.0 for v in summ["lambdas"].values())
               and summ["n_state_dict_tensors"] == PARENT_N_TENSORS)
    rec.check("T12f", "summary.json：COMPLETE / 跑满 schedule / 四 λ 全 0",
              summ_ok, f"status={summ['status']} reason={summ['completion_reason']} "
                       f"step={summ['step']}/{summ['total_steps']} λ={summ['lambdas']}")

    recs = [json.loads(l) for l in
            (out / "loss_log.jsonl").read_text().strip().splitlines() if l.strip()]
    n_train = sum(1 for r in recs if "total" in r)
    n_val = sum(1 for r in recs if "val_dev" in r)
    rec.check("T12g", "loss_log.jsonl：2 条训练记录 + 1 条 val_dev",
              n_train == 2 and n_val == 1, f"train={n_train} val={n_val}")

    try:
        run_training(args, S["factory"])
        guarded, why = False, "第二次运行竟然成功了：会覆盖既有 checkpoint"
    except FileExistsError as exc:
        guarded, why = True, f"FileExistsError: {str(exc)[:100]}"
    except Exception as exc:                                     # noqa: BLE001
        guarded, why = False, f"抛了别的异常：{type(exc).__name__}: {exc}"
    rec.check("T12h", "guard_output_dir 拒绝复用已有 checkpoint 的目录", guarded, why)
    return out, S, args, summ


# ---------------------------------------------------- T13 中断 vs 未中断 exact resume
def t13_exact_resume(rec, scratch):
    """8 cube / per_gpu 2 / global 4 -> accum 2、4 batch/epoch、2 更新/epoch。
    max_epochs 2 => total_steps 4；ckpt@2。三个 run 共用同一份数据。

    val_interval=0 是必须的：validate_candidate_c 消耗全局 RNG，只在 A 触发会
    让 RNG 流分叉，从而用一个与 resume 无关的原因判失败。
    """
    S = scaffold(scratch / "t13", n_train=8, n_val=2)
    base = dict(train_dir=S["train_dir"], val_dir=S["val_dir"],
                val_split_manifest=S["manifest"], per_gpu_batch=2, global_batch=4,
                max_epochs=2, ckpt_interval=2, val_interval=0, log_interval=1)
    dA, dB, dC = (scratch / "t13" / x for x in ("runA", "runB", "runC"))

    sA = run_training(mk_args(output_dir=dA, **base), S["factory"])
    sB = run_training(mk_args(output_dir=dB, stop_after_step=2, **base), S["factory"])

    plan_ok = (sA["total_steps"] == sB["total_steps"] == 4 and sA["accum"] == 2
               and sA["step"] == 4 and sB["step"] == 2
               and sB["stop_after_step"] == 2
               and sB["completion_reason"] == "stop_after_step")
    rec.check("T13a", "--stop-after-step 2 不改变计划 total_steps=4",
              plan_ok, f"A: step={sA['step']}/{sA['total_steps']} accum={sA['accum']} | "
                       f"B: step={sB['step']}/{sB['total_steps']} "
                       f"stop_after={sB['stop_after_step']} reason={sB['completion_reason']}")

    a2 = torch.load(dA / "checkpoint_step2.pt", map_location="cpu", weights_only=False)
    b2 = torch.load(dB / "checkpoint_step2.pt", map_location="cpu", weights_only=False)
    same2 = (value_sha16(a2["b4_state_dict"]) == value_sha16(b2["b4_state_dict"])
             and opt_fingerprint(a2["optimizer_state_dict"])
             == opt_fingerprint(b2["optimizer_state_dict"]))
    rec.check("T13b", "中断点 step2：A 与 B 权重+优化器逐位一致",
              same2, f"A={value_sha16(a2['b4_state_dict'])}/"
                     f"{opt_fingerprint(a2['optimizer_state_dict'])[:12]} "
                     f"B={value_sha16(b2['b4_state_dict'])}/"
                     f"{opt_fingerprint(b2['optimizer_state_dict'])[:12]}")

    sC = run_training(mk_args(output_dir=dC, resume=str(dB / "checkpoint_step2.pt"),
                             **base), S["factory"])
    rec.check("T13c", "resume 后跑到预注册终点 step=4 且 schedule_complete",
              sC["step"] == 4 and sC["completion_reason"] == "schedule_complete"
              and sC["status"] == "COMPLETE",
              f"step={sC['step']}/{sC['total_steps']} reason={sC['completion_reason']}")

    mA = torch.load(dA / "checkpoint_main.pt", map_location="cpu", weights_only=False)
    mC = torch.load(dC / "checkpoint_main.pt", map_location="cpu", weights_only=False)
    wA, wC = value_sha16(mA["b4_state_dict"]), value_sha16(mC["b4_state_dict"])
    oA, oC = (opt_fingerprint(m["optimizer_state_dict"]) for m in (mA, mC))
    schedA = json.dumps(mA["scheduler_state_dict"], sort_keys=True, default=str)
    schedC = json.dumps(mC["scheduler_state_dict"], sort_keys=True, default=str)
    rec.check("T13d", "中断+resume 的终点权重与未中断逐位相同（exact resume）",
              wA == wC, f"uninterrupted={wA} resumed={wC}")
    rec.check("T13e", "优化器动量状态也逐位相同（不只是权重对上）",
              oA == oC, f"uninterrupted={oA[:16]} resumed={oC[:16]}")
    rec.check("T13f", "scheduler 状态一致且 last_epoch=4",
              schedA == schedC and int(mC["scheduler_state_dict"].get("last_epoch", -1)) == 4,
              f"last_epoch={mC['scheduler_state_dict'].get('last_epoch')} equal={schedA == schedC}")
    rec.check("T13g", "summary 的 value_sha16 与两条路线一致",
              sA["model_value_sha16"] == sC["model_value_sha16"] == wA,
              f"A={sA['model_value_sha16']} C={sC['model_value_sha16']}")

    linC = dict(mC.get("lineage") or {})
    rec.check("T13h", "resume 在 lineage 留痕，且仍标记为父的 weights-only fork",
              linC.get("resumed_within_phase") is True
              and linC.get("resume_parent_file_sha256")
              and linC.get("is_exact_resume") is False
              and linC.get("inherited_value_sha16") == PARENT_VALUE_SHA16,
              f"resumed_within_phase={linC.get('resumed_within_phase')} "
              f"resume_sha={str(linC.get('resume_parent_file_sha256'))[:16]} "
              f"is_exact_resume_of_parent={linC.get('is_exact_resume')}")

    # ---- fail-closed：任何 schedule/预算/臂/λ 漂移都必须拒绝 resume ----------
    ckB = str(dB / "checkpoint_step2.pt")
    cases = [
        ("total_steps", dict(max_steps=6), "total_steps"),
        ("global_batch", dict(max_steps=4, global_batch=8), "global_batch"),
        ("arm", dict(arm="C0R", factual_path="direct"), "arm"),
        ("lambda", dict(lambda_nc=0.01, allow_nonzero_lambdas=True), "λ"),
    ]
    for name, over, token in cases:
        cfg = dict(base); cfg.update(over)
        d = scratch / "t13" / f"reject_{name}"
        try:
            run_training(mk_args(output_dir=d, resume=ckB, **cfg), S["factory"])
            ok, why = False, "竟然允许 resume：预算/臂/λ 漂移没有被拦"
        except ValueError as exc:
            ok, why = token in str(exc), f"ValueError: {str(exc)[:120]}"
        except Exception as exc:                                 # noqa: BLE001
            ok, why = False, f"抛了别的异常：{type(exc).__name__}: {str(exc)[:100]}"
        rec.check(f"T13i_{name}", f"resume fail-closed：{name} 漂移被拒", ok, why)


# ------------------------------------------------------- T15 C1 / C0R 单变量审计
def t15_arm_parity(rec, scratch):
    """两臂共用同一份数据集对象，唯一差别是 factual_path 是否走递归段路径。

    "配置看起来一样"不算证据：这里用 RecordingDataset 记录真实被消费的 cube id
    顺序，用 loss_log 记录每步真实抽到的端点，逐项比对。
    """
    S = scaffold(scratch / "t15", n_train=8, n_val=2)
    base = dict(train_dir=S["train_dir"], val_dir=S["val_dir"],
                val_split_manifest=S["manifest"], per_gpu_batch=2, global_batch=4,
                max_epochs=1, ckpt_interval=0, val_interval=0, log_interval=1)
    seen = {"C1": [], "C0R": []}

    def fac_for(arm):
        def f(split, d):
            if split == "val":
                return S["val"]
            return RecordingDataset(S["train"], S["train_dir"], seen[arm])
        return f

    out = {}
    for arm, path in (("C1", "recursive"), ("C0R", "direct")):
        out[arm] = run_training(
            mk_args(arm=arm, factual_path=path, output_dir=scratch / "t15" / arm, **base),
            fac_for(arm))

    rec.check("T15a", "两臂消费的 EO cube id 与顺序完全一致（同一曝光）",
              seen["C1"] == seen["C0R"] and len(seen["C1"]) == 8,
              f"n={len(seen['C1'])} C1={seen['C1']} 相同={seen['C1'] == seen['C0R']}")

    def plans(summ):
        return [[(p["endpoint"], tuple(p["partition"])) for p in r["endpoint_plan"]]
                for r in summ["loss_log"] if "endpoint_plan" in r]

    pC1, pC0R = plans(out["C1"]), plans(out["C0R"])
    eps1 = [[e for e, _ in step] for step in pC1]
    eps0 = [[e for e, _ in step] for step in pC0R]
    rec.check("T15b", "每步抽到的端点集合逐位一致（RNG 流不因臂而分叉）",
              eps1 == eps0 and len(eps1) == 2 and all(e == [10, 15, 20] for e in eps1),
              f"C1={eps1} C0R={eps0}")

    multi = [pt for step in pC1 for _, pt in step if len(pt) > 1]
    all_single = all(len(pt) == 1 for step in pC0R for _, pt in step)
    rec.check("T15c", "唯一变量成立：C1 走多段递归、C0R 全是单段 direct",
              bool(multi) and all_single,
              f"C1 多段划分={multi[:4]} C0R 全单段={all_single} "
              f"C0R partitions={[pt for step in pC0R for _, pt in step]}")

    a, b = out["C1"], out["C0R"]
    top = ("total_steps", "accum", "world_size", "global_batch", "per_gpu_batch",
           "seed", "lambdas", "n_state_dict_tensors", "n_trainable_q", "step")
    shak = ("parent_file_sha256", "parent_value_sha16", "inherited_value_sha16",
            "warm_start_state_sha256", "val_split_manifest_sha256",
            "val_split_selector", "val_split_n_ids")
    diffs = [f"{k}: {a[k]!r} != {b[k]!r}" for k in top if a[k] != b[k]]
    diffs += [f"sha.{k}: {a['sha'].get(k)!r} != {b['sha'].get(k)!r}"
              for k in shak if a["sha"].get(k) != b["sha"].get(k)]
    rec.check("T15d", "预算/容量/seed/λ/父身份/split 逐项相同", not diffs,
              f"检查 {len(top) + len(shak)} 项，差异={diffs or '无'} | "
              f"updates={a['total_steps']} global_batch={a['global_batch']} "
              f"seed={a['seed']} n_tensors={a['n_state_dict_tensors']} "
              f"parent={a['sha']['parent_file_sha256'][:16]}")

    rec.check("T15e", "训练后两臂权重确实不同（那个唯一变量真的起作用了）",
              a["model_value_sha16"] != b["model_value_sha16"]
              and a["sha"]["warm_start_state_sha256"] == b["sha"]["warm_start_state_sha256"],
              f"C1={a['model_value_sha16']} C0R={b['model_value_sha16']} "
              f"（起点相同 warm_start={a['sha']['warm_start_state_sha256'][:16]}）")

    # 单元级 RNG 纯度：同 (seed, step) 下两臂抽到的划分索引必须逐位一致，
    # 差别只能是 direct 臂抽完就丢弃、改用 (endpoint,)。
    from tests.candidate_c_fixtures import build_model
    m1, m0 = build_model("recursive", seed=3), build_model("direct", seed=3)
    same_draw, collapsed = True, True
    detail = []
    for st in (0, 1, 7, 371, 2975):
        p1 = m1.draw_endpoint_plan(endpoint_rng(42, st))
        p0 = m0.draw_endpoint_plan(endpoint_rng(42, st))
        same_draw &= all(tuple(x["partition_drawn"]) == tuple(y["partition_drawn"])
                         and x["endpoint"] == y["endpoint"] for x, y in zip(p1, p0))
        collapsed &= all(tuple(y["partition"]) == (y["endpoint"],) for y in p0)
        if st in (0, 2975):
            detail.append(f"step{st}: drawn={[tuple(x['partition_drawn']) for x in p1]} "
                          f"C0R used={[tuple(y['partition']) for y in p0]}")
    rec.check("T15f", "draw_endpoint_plan 是 (seed,step) 的纯函数，两臂同流",
              same_draw and collapsed, " | ".join(detail))

    # 臂与路径的交叉校验 + C0S 双层拦截（argparse choices 与 run_training 各一道）
    d = scratch / "t15" / "reject"
    mism = dict(train_dir=S["train_dir"], val_dir=S["val_dir"],
                val_split_manifest=S["manifest"], output_dir=d / "mismatch")
    try:
        run_training(mk_args(arm="C1", factual_path="direct", **mism), S["factory"])
        m_ok, m_why = False, "arm=C1 竟然接受了 factual_path=direct"
    except ValueError as exc:
        m_ok, m_why = "factual-path" in str(exc), f"ValueError: {str(exc)[:110]}"
    except Exception as exc:                                     # noqa: BLE001
        m_ok, m_why = False, f"{type(exc).__name__}: {str(exc)[:100]}"
    rec.check("T15g", "arm 与 factual_path 不匹配被拒", m_ok, m_why)

    try:
        mk_args(arm="C0S", train_dir=S["train_dir"], val_dir=S["val_dir"],
                val_split_manifest=S["manifest"], output_dir=d / "c0s")
        cli_ok, cli_why = False, "argparse 竟然接受了 --arm C0S"
    except SystemExit:
        cli_ok, cli_why = True, "argparse choices 在 CLI 层就拒绝了 C0S"
    rec.check("T15h", "CLI 层拒绝 --arm C0S", cli_ok, cli_why)

    a2 = mk_args(arm="C1", factual_path="direct",
                 train_dir=S["train_dir"], val_dir=S["val_dir"],
                 val_split_manifest=S["manifest"], output_dir=d / "c0s2")
    a2.arm = "C0S"                                    # 绕过 argparse，测第二道防线
    try:
        run_training(a2, S["factory"])
        c_ok, c_why = False, "run_training 竟然接受了 arm=C0S"
    except ValueError as exc:
        c_ok, c_why = "C0S" in str(exc), f"ValueError: {str(exc)[:110]}"
    except Exception as exc:                                     # noqa: BLE001
        c_ok, c_why = False, f"{type(exc).__name__}: {str(exc)[:100]}"
    rec.check("T15i", "run_training 内层也拒绝 C0S（本轮不得伪造 simulator 对照臂）",
              c_ok, c_why)


# ------------------------------------------------------------ T16 评测器严格装载
# 这些接收者的 load_state_dict 没有 strict 形参（torch.optim / lr_scheduler /
# GradScaler）。它们不该被要求 strict=True，也不该被允许传 strict。
NON_MODULE_RECV = frozenset({"opt", "optimizer", "optim", "sched", "scheduler",
                             "lr_scheduler", "scaler", "grad_scaler"})


def _fn_ranges(tree):
    """[(name, lineno, end_lineno)]，用于把某行代码归属到最内层函数。"""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((n.name, n.lineno, getattr(n, "end_lineno", n.lineno)))
    return out


def _enclosing(ranges, lineno):
    best = None
    for name, a, b in ranges:
        if a <= lineno <= b and (best is None or a > best[1]):
            best = (name, a)
    return best[0] if best else "<module>"


def scan_strict(path):
    """AST 层面找出所有 load_state_dict 调用与所有 strict= 关键字。

    刻意不用 grep：evaluator 的 docstring 里就写着"绝不出现 strict=False"这句话，
    文本搜索会把这句注释当成违规，而真正的违规反而可能藏在别名调用里。
    """
    src = Path(path).read_text()
    tree = ast.parse(src)
    ranges = _fn_ranges(tree)
    loads, stricts = [], []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        fname = (n.func.attr if isinstance(n.func, ast.Attribute)
                 else getattr(n.func, "id", ""))
        kw = {k.arg: k.value for k in n.keywords if k.arg}
        if "strict" in kw:
            v = kw["strict"]
            lit = v.value if isinstance(v, ast.Constant) else f"<{ast.dump(v)[:40]}>"
            stricts.append({"line": n.lineno, "fn": _enclosing(ranges, n.lineno),
                            "call": fname, "value": lit})
        if fname == "load_state_dict":
            sv = kw.get("strict")
            recv = (ast.unparse(n.func.value).split(".")[-1]
                    if isinstance(n.func, ast.Attribute) else "<?>")
            loads.append({"line": n.lineno, "fn": _enclosing(ranges, n.lineno),
                          "recv": recv, "is_module": recv not in NON_MODULE_RECV,
                          "has_strict": sv is not None,
                          "explicit_true": isinstance(sv, ast.Constant) and sv.value is True,
                          "value": (sv.value if isinstance(sv, ast.Constant) else
                                    (None if sv is None else "<expr>"))})
    return loads, stricts


def strict_violations(loads):
    """双向判定，而不是"所有 load 都必须 strict=True"。

    Optimizer / scheduler / GradScaler 的 load_state_dict 根本没有 strict 形参，
    对它们传 strict= 会直接 TypeError。所以：module 接收者必须显式 strict=True；
    非 module 接收者必须一个 strict 都不传。这比单向断言更严，两个方向都能抓错。
    """
    bad = []
    for l in loads:
        if l["is_module"] and not l["explicit_true"]:
            bad.append(f"L{l['line']} {l['recv']}.load_state_dict "
                       f"strict={l['value']!r}（module 必须显式 strict=True）")
        elif not l["is_module"] and l["has_strict"]:
            bad.append(f"L{l['line']} {l['recv']}.load_state_dict 传了 strict="
                       f"{l['value']!r}（该 API 无此形参，会 TypeError）")
    return bad


def t16_strict_loader(rec, ckpt_dir, scratch):
    ev = ROOT / "eval/eval_terrastate_candidate_c_q4.py"
    loads, stricts = scan_strict(ev)
    bad = strict_violations(loads)
    n_mod = sum(1 for l in loads if l["is_module"])
    rec.check("T16a", "评测器所有 module load_state_dict 都显式 strict=True",
              n_mod >= 1 and not bad,
              f"共 {len(loads)} 处（module {n_mod} 处）：" + "; ".join(
                  f"L{l['line']} {l['fn']} {l['recv']} strict={l['value']!r}"
                  for l in loads)
              + (f" | 违规={bad}" if bad else ""))
    nt = [s for s in stricts if s["value"] is not True]
    rec.check("T16b", "评测器不存在任何非 True 的 strict= 实参", not nt, f"违规={nt or '无'}")

    tr = ROOT / "train/train_terrastate_candidate_c.py"
    md = ROOT / "models/terrastate_candidate_c.py"
    tl, _ = scan_strict(tr)
    ml, _ = scan_strict(md)
    tr_bad = strict_violations(tl)
    # 模型侧唯一合法的 strict=False 是 warm_start_candidate_c 里的预检：
    # 它后面紧跟白名单/unexpected 的 fail-closed 断言。除此之外一律违规。
    ml_bad = strict_violations([l for l in ml if l["fn"] != "warm_start_candidate_c"])
    ws = [l for l in ml if l["fn"] == "warm_start_candidate_c"]
    ws_ok = len(ws) == 1 and ws[0]["value"] is False
    # trainer 必须恰好有一处 module 严格装载（student），且 opt/sched 各一处不带 strict。
    tr_mod = [l for l in tl if l["is_module"]]
    tr_non = [l for l in tl if not l["is_module"]]
    rec.check("T16c", "trainer resume 严格装载；模型侧 strict=False 仅限 warm-start 预检",
              not tr_bad and not ml_bad and ws_ok
              and len(tr_mod) == 1 and len(tr_non) == 2,
              f"trainer={[(l['line'], l['recv'], l['value']) for l in tl]}"
              f"（module {len(tr_mod)} 处须 strict=True；opt/sched {len(tr_non)} 处"
              f"无 strict 形参，传了才是 bug） | "
              f"model warm_start={[(l['line'], l['recv'], l['value']) for l in ws]} "
              f"唯一且为 False={ws_ok} | 违规={(tr_bad + ml_bad) or '无'}")

    main_ck = Path(ckpt_dir) / "checkpoint_main.pt"
    model, ck, meta = ccq4.load_candidate_c_strict(str(main_ck), device="cpu")
    rec.check("T16d", "健康 checkpoint：strict 装载成功且 value_sha16 自洽",
              meta["strict"] is True and meta["n_tensors_loaded"] == PARENT_N_TENSORS
              and meta["loaded_value_sha16"] == meta["ckpt_value_sha16"],
              f"n={meta['n_tensors_loaded']} loaded={meta['loaded_value_sha16']} "
              f"ckpt={meta['ckpt_value_sha16']} step={meta['step']} arm={meta['arm']}")

    cdir = Path(scratch) / "t16_corrupt"
    cdir.mkdir(parents=True, exist_ok=True)

    def corrupt(name, fn):
        c = torch.load(main_ck, map_location="cpu", weights_only=False)
        fn(c)
        p = cdir / f"{name}.pt"
        torch.save(c, p)
        return p

    def drop_one(c):
        k = sorted(c["b4_state_dict"].keys())[0]
        c["b4_state_dict"].pop(k)

    def add_bogus(c):
        k = sorted(c["b4_state_dict"].keys())[0]
        c["b4_state_dict"]["bogus.injected.weight"] = c["b4_state_dict"][k].clone()

    cases = [
        ("missing_key", drop_one, (RuntimeError, ccq4.EvalError), "缺 1 个张量"),
        ("unexpected_key", add_bogus, (RuntimeError, ccq4.EvalError), "多 1 个张量"),
        ("wrong_arch", lambda c: c.__setitem__("arch", "TerraStateV2"),
         ccq4.EvalError, "arch 冒充父世代"),
        ("no_contract_cfg", lambda c: c.__setitem__("contract_cfg", {}),
         ccq4.EvalError, "没有 contract_cfg 无法复现结构"),
        ("no_state_dict", lambda c: c.pop("b4_state_dict"),
         ccq4.EvalError, "根本没有权重"),
    ]
    for name, fn, exc_types, desc in cases:
        p = corrupt(name, fn)
        try:
            ccq4.load_candidate_c_strict(str(p), device="cpu")
            ok, why = False, "坏 checkpoint 竟然装载成功了"
        except exc_types as exc:
            ok, why = True, f"{type(exc).__name__}: {str(exc).splitlines()[0][:100]}"
        except Exception as exc:                                 # noqa: BLE001
            ok, why = False, f"抛了预期外的异常：{type(exc).__name__}: {str(exc)[:90]}"
        rec.check(f"T16e_{name}", f"坏 checkpoint 必抛（{desc}）", ok, why)
    return model, meta


# --------------------------------------------------- T17 评测器产物完整性
def t17_evaluator_outputs(rec, ckpt_dir, scratch):
    """geo 排布的 6 个合成 cube（3 个 tile）跑一遍 score，检查四件产物齐备。

    合成数据上 Q4 判据的 verdict 没有物理意义，因此 verdict 只记录不作 fatal；
    fatal 的是"产物是否完整、字段是否自洽、SHA 是否对得上"。
    """
    import numpy as np
    S = scaffold(scratch / "t17", n_train=2, n_val=6, geo=True)
    outdir = scratch / "t17" / "score_val_dev"
    argv = ["score", "--ckpt", str(Path(ckpt_dir) / "checkpoint_main.pt"),
            "--data-root", S["val_dir"], "--split-manifest", S["manifest"],
            "--split-selector", "splits.val_dev.ids", "--output", str(outdir),
            "--batch-size", "6", "--num-workers", "0", "--device", "cpu",
            "--max-batches", "1"]
    args = ccq4.build_argparser().parse_args(argv)
    t0 = time.time()
    agg = ccq4.score_checkpoint(args, lambda root: S["val"])
    dt = time.time() - t0

    want = ["per_cube_arrays.npz", "per_cube_metrics.json", "provenance.json",
            "q4_aggregate.json"]
    got = sorted(p.name for p in outdir.iterdir())
    residue = [n for n in got if ".tmp" in n]
    rec.check("T17a", "四件产物齐备且原子写无残留",
              got == want and not residue, f"files={got} residue={residue} {dt:.1f}s")

    pc = json.loads((outdir / "per_cube_metrics.json").read_text())
    combos = [c["combo"] for c in agg["combos"]]
    tags = sorted({c["tag"] for c in agg["combos"]})
    eps = sorted({c["endpoint"] for c in agg["combos"]})
    cubes = pc["cubes"]
    missing_combo = [c["cube_id"] for c in cubes
                     if sorted(c["combos"].keys()) != sorted(combos)]
    geos = sorted({c["geo_group"] for c in cubes})
    rec.check("T17b", "per_cube JSON：逐 cube × 全部 combo，geo_group 由真实规则得出",
              pc["schema"] == "candidate_c_q4_per_cube_v1" and pc["n_cubes"] == 6
              and len(cubes) == 6 and not missing_combo
              and eps == [10, 15, 20] and set(tags) >= {"direct", "train_seen", "heldout"},
              f"n_cubes={pc['n_cubes']} n_combos={len(combos)} tags={tags} "
              f"endpoints={eps} geo_groups={geos} 缺 combo 的 cube={missing_combo or '无'}")

    # segment_weather_mismatched 在单段 combo 上**不可能存在**（mismatched_weather:
    # "单段没有『另一段』"）。所以不能要求每个 combo 都有 6 个 variant；正确的判据是
    # variants ∪ 评测器自己声明的 degenerate_controls == 全 6 个，且缺失只允许是
    # 单段上的 segment_weather_mismatched。这比固定计数更严：既抓漏算，也抓拿
    # "退化"当借口偷偷少算多段对照。
    ALL6 = set(("factual", "alpha0", *ccq4.CONTROLS))
    METRIC_KEYS = {"n_valid_pixels", "mse", "r2", "sse", "sst", "eligible"}
    nseg = {c["combo"]: int(c["n_segments"]) for c in agg["combos"]}
    degen = agg.get("degenerate_controls") or {}
    dg_by_combo = {}
    for k in degen:
        cb, _, vn = str(k).partition("::")
        dg_by_combo.setdefault(cb, set()).add(vn)
    bad_v, multi_has_mm = [], 0
    for c in cubes:
        for cb, blk in c["combos"].items():
            have = set(blk.get("variants") or {})
            allowed_missing = dg_by_combo.get(cb, set())
            if have | allowed_missing != ALL6:
                bad_v.append(f"{c['cube_id']}/{cb}: 有={sorted(have)} "
                             f"允许缺={sorted(allowed_missing)}")
            for vn, v in (blk.get("variants") or {}).items():
                if not METRIC_KEYS <= set(v.keys()):
                    bad_v.append(f"{c['cube_id']}/{cb}/{vn}: 缺 "
                                 f"{sorted(METRIC_KEYS - set(v.keys()))}")
            if nseg.get(cb, 1) > 1 and "segment_weather_mismatched" in have:
                multi_has_mm += 1
    bad_dg = [k for k in degen
              if not (k.endswith("::segment_weather_mismatched")
                      and nseg.get(k.split("::")[0], 9) == 1)]
    rec.check("T17c", "每个 combo 记满 6 个 variant，缺失仅限单段上不可能的段错配对照",
              not bad_v and not bad_dg and multi_has_mm > 0,
              f"违规={bad_v[:3] or '无'} | 评测器声明的退化项={sorted(degen)} "
              f"（合法性={not bad_dg}：只允许单段上的 segment_weather_mismatched） | "
              f"多段 combo 实际带段错配对照的次数={multi_has_mm}"
              f"（>0 才证明该对照不是死代码）")

    z = np.load(outdir / "per_cube_arrays.npz", allow_pickle=True)
    keys = set(z.files)
    skeys = [str(s) for s in z["series_keys"]]
    per_key_ok = all({f"{ccq4._safe(k)}|n", f"{ccq4._safe(k)}|sse"} <= keys
                     for k in skeys)
    len_ok = all(len(z[f"{ccq4._safe(k)}|n"]) == 6 for k in skeys)
    rec.check("T17d", "per_cube_arrays.npz：cube_ids + 每个 series 的 n/sse 逐 cube 数组",
              len(z["cube_ids"]) == 6 and bool(skeys) and per_key_ok and len_ok
              and "state_std_zt_per_cube" in keys and "state_cube_ids" in keys,
              f"n_cube_ids={len(z['cube_ids'])} n_series={len(skeys)} "
              f"per_key_ok={per_key_ok} len_ok={len_ok} "
              f"state_rows={len(z['state_std_zt_per_cube'])}")

    ag = json.loads((outdir / "q4_aggregate.json").read_text())
    art = ag.get("artifacts", {})
    sha_json = ccq4.sha256_file(outdir / "per_cube_metrics.json")
    sha_npz = ccq4.sha256_file(outdir / "per_cube_arrays.npz")
    gates = ag.get("gates", {})
    rec.check("T17e", "q4_aggregate.json：schema/verdict/gates/artifacts SHA 自洽",
              ag["schema"] == "candidate_c_q4_aggregate_v1"
              and ag["verdict"] in ("PASS", "FAIL")
              and art.get("per_cube_metrics.json") == sha_json
              and art.get("per_cube_arrays.npz") == sha_npz
              and ag["canonical_sha256_of_gates"] == ccq4.canonical_json_sha256(gates)
              and ag["n_cubes"] == 6 and ag["n_geo_clusters"] == 3,
              f"verdict={ag['verdict']}（合成数据上仅供参考）gates={sorted(gates.keys())} "
              f"n_geo_clusters={ag['n_geo_clusters']} geo={ag['geo_clusters']}")

    split = ag.get("split", {})
    rec.check("T17f", "split 溯源：selector / n_ids / allow_locked=False 都写进产物",
              split.get("selector") == "splits.val_dev.ids"
              and split.get("n_ids_in_manifest") == 6 and split.get("n_scored") == 6
              and split.get("allow_locked") is False,
              f"selector={split.get('selector')} n_ids={split.get('n_ids_in_manifest')} "
              f"n_scored={split.get('n_scored')} allow_locked={split.get('allow_locked')}")

    pv = json.loads((outdir / "provenance.json").read_text())
    src = pv.get("source_sha256", {})
    need = {"utc", "hostname", "python", "torch", "git_head", "source_sha256",
            "control_seed", "bootstrap_B", "simulator_status", "q4_aggregate_sha256"}
    live_ok = all(src.get(r) == ccq4.sha256_file(ROOT / r)
                  for r in ccq4.SOURCE_FILES if (ROOT / r).is_file())
    rec.check("T17g", "provenance.json：字段齐备且 source SHA 等于现场文件",
              need <= set(pv.keys()) and live_ok
              and pv["q4_aggregate_sha256"] == ccq4.sha256_file(outdir / "q4_aggregate.json")
              and len(src) == len(ccq4.SOURCE_FILES),
              f"缺字段={sorted(need - set(pv.keys())) or '无'} n_source={len(src)} "
              f"live_ok={live_ok} torch={pv.get('torch')} B={pv.get('bootstrap_B')}")

    # val_locked / ood / test 必须在选择器层就被拒（除非显式 --allow-locked）。
    for sel in ("splits.val_locked.ids", "splits.ood_t.ids", "splits.test.ids"):
        try:
            ccq4.load_split_ids(S["manifest"], sel, allow_locked=False)
            ok, why = False, f"{sel} 竟然被接受"
        except Exception as exc:                                 # noqa: BLE001
            ok, why = True, f"{type(exc).__name__}: {str(exc).splitlines()[0][:90]}"
        rec.check(f"T17h_{sel.split('.')[1]}", f"评测器拒绝 {sel}（未加 --allow-locked）",
                  ok, why)


# ------------------------------------------------- T18 空白检查 + 已验收世代回归
def t18_whitespace_and_regressions(rec):
    import numpy as np                                           # noqa: F401
    bad = []
    for rel in NEW_FILES:
        p = ROOT / rel
        if not p.is_file():
            bad.append(f"{rel}: 文件不存在")
            continue
        raw = p.read_bytes()
        if b"\r\n" in raw:
            bad.append(f"{rel}: 含 CRLF")
        if raw and not raw.endswith(b"\n"):
            bad.append(f"{rel}: 末尾缺换行")
        for i, line in enumerate(raw.decode("utf-8").splitlines(), 1):
            if line.rstrip() != line:
                bad.append(f"{rel}:{i}: 行尾空白")
            if "\t" in line:
                bad.append(f"{rel}:{i}: 制表符")
    rec.check("T18a", f"新建 {len(NEW_FILES)} 个文件无行尾空白/制表符/CRLF/缺末行",
              not bad, f"违规={bad[:8]}" + (f" 等共 {len(bad)} 条" if len(bad) > 8 else ""))

    # 新文件未被 git 跟踪，`git diff --check` 结构上看不见它们（T18a 才是那道门）。
    # 这里仍跑一次并断言输出没有点到我们的文件；terrastate/ 下其他会话的空白问题
    # 记录但不判失败——那不是本轮的改动。
    try:
        p = subprocess.run(["git", "diff", "--check", "--", "terrastate/"],
                           cwd=str(REPO), capture_output=True, text=True, timeout=120)
        raw = (p.stdout + p.stderr).strip()
    except Exception as exc:                                     # noqa: BLE001
        raw = f"<git 不可用: {exc}>"
    hits = [l for l in raw.splitlines() if any(n in l for n in NEW_FILES)]
    rec.check("T18b", "git diff --check 未点到本轮新建文件", not hits,
              f"本轮文件命中={hits or '无'} | 全部输出行数={len(raw.splitlines())}"
              + (f" 首行={raw.splitlines()[0][:90]}" if raw.splitlines() else ""),
              fatal=False)

    # 已验收世代共用的三个模型文件必须逐字节等于 HEAD。
    drift = []
    for rel in FROZEN_FILES:
        work = (ROOT / rel).read_bytes()
        head = git_head_bytes(rel)
        if head is None:
            drift.append(f"{rel}: 取不到 HEAD 版本")
        elif sha256_bytes(work) != sha256_bytes(head):
            drift.append(f"{rel}: work={sha256_bytes(work)[:16]} head={sha256_bytes(head)[:16]}")
    rec.check("T18c", "plan_b_b4 / plan_b_b4_exclusive / terrastate_v2 逐字节等于 HEAD",
              not drift,
              f"漂移={drift or '无'} | 已核 {len(FROZEN_FILES)} 个文件")

    import inspect
    import textwrap
    from models.plan_b_b4 import ObsWorldB4
    # getsource 返回的是类体内的缩进片段，必须先 dedent 才能 parse；
    # 走 AST 再 unparse 是为了剥掉注释——否则注释里出现 svdvals 就会误判。
    parent_src = ast.unparse(ast.parse(textwrap.dedent(
        inspect.getsource(ObsWorldB4.effective_rank))))
    rec.check("T18d", "父类 ObsWorldB4.effective_rank 仍走 eigvalsh（未被本轮改动）",
              "eigvalsh" in parent_src and "svdvals" not in parent_src,
              f"eigvalsh={'eigvalsh' in parent_src} svdvals={'svdvals' in parent_src}")

    # 覆写必须只落在 Candidate C 子类；已验收世代不得继承到新实现。
    cc_fn = TerraStateCandidateC.__dict__.get("effective_rank")
    inherit = {}
    for mod, cls in (("models.terrastate_v2", "TerraStateV2"),
                     ("models.plan_b_b4_exclusive", "ObsWorldB4Exclusive"),
                     ("models.plan_b_b4", "ObsWorldB4")):
        try:
            k = getattr(__import__(mod, fromlist=[cls]), cls)
            inherit[cls] = (getattr(k, "effective_rank", None)
                            is getattr(TerraStateCandidateC, "effective_rank"))
        except Exception as exc:                                 # noqa: BLE001
            inherit[cls] = f"<{type(exc).__name__}>"
    rec.check("T18e", "effective_rank 覆写只在 Candidate C 子类，未污染已验收世代",
              cc_fn is not None and all(v is False for v in inherit.values()),
              f"子类自有覆写={cc_fn is not None} 其他类是否继承到覆写={inherit}")

    # 常数输入上：子类返回 0.0（fail-closed 方向），父类实现会抛。
    zc = torch.ones(4, 6, 8)
    try:
        mine, mine_err = float(TerraStateCandidateC.effective_rank(zc)), ""
    except Exception as exc:                                     # noqa: BLE001
        mine, mine_err = None, f"{type(exc).__name__}"
    rec.check("T18f", "常数状态下子类 effective_rank 返回 0.0 而不抛（非坍缩门可判 FAIL）",
              mine == 0.0, f"value={mine} err={mine_err or '无'}")

    # train_terrastate_v2.py 整体有其他会话的合法改动，只能锁我们依赖的那个函数。
    def fn_src(src_bytes, name):
        tree = ast.parse(src_bytes.decode("utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name == name:
                return ast.unparse(n)
        return None

    rel = "train/train_terrastate_v2.py"
    head_b = git_head_bytes(rel)
    work_fn = fn_src((ROOT / rel).read_bytes(), "lr_factor")
    head_fn = fn_src(head_b, "lr_factor") if head_b else None
    from train.train_terrastate_v2 import lr_factor
    # 锚点跟随预算修正后的真实 schedule：warmup=300、total=14880（与父权重 40 epoch
    # 同构）。取样点是该 schedule 的四个几何地标：起点、warmup 中点、warmup 末端、
    # cosine 中点、终点；期望值 [0, .5, 1, .5, 0] 与旧预算逐字节相同，因为锁的是
    # lr_factor 的形状而不是某一组预算数字。
    pins = [round(lr_factor(s, 300, 14880), 12) for s in (0, 150, 300, 7590, 14880)]
    want_pins = [0.0, 0.5, 1.0, 0.5, 0.0]
    rec.check("T18g", "lr_factor 与 HEAD 同源，且 warmup+cosine 数值锚点未漂移",
              work_fn is not None and work_fn == head_fn and pins == want_pins,
              f"函数体等于 HEAD={work_fn == head_fn} "
              f"pins(step 0/150/300/7590/14880)={pins} 期望={want_pins} "
              f"（整文件另有其他会话改动，故只锁此函数）")

    # 用内建 compile 而不是 py_compile：py_compile 会先检查 cfile 是不是普通文件，
    # 传 /dev/null（字符设备）会被它判成 FileExistsError，与源码语法毫无关系。
    # 内建 compile 纯内存校验，不写 .pyc、不碰盘，也就不受 NFS/原子性约束影响。
    fails = []
    targets = list(dict.fromkeys(                       # 去重：q4 评测器同时在两张表里
        sorted((ROOT / "eval").glob("*.py"))
        + [ROOT / r for r in FROZEN_FILES] + [ROOT / r for r in NEW_FILES]))
    for p in targets:
        if not p.is_file():
            fails.append(f"{p.relative_to(ROOT)}: 文件不存在")
            continue
        try:
            compile(p.read_bytes(), str(p), "exec", dont_inherit=True)
        except Exception as exc:                                 # noqa: BLE001
            fails.append(f"{p.relative_to(ROOT)}: {type(exc).__name__}: {exc}")
    rec.check("T18h", f"{len(targets)} 个 evaluator/模型/新文件全部可编译", not fails,
              f"失败={fails or '无'} | evaluators={len(list((ROOT / 'eval').glob('*.py')))} "
              f"| 去重后目标={len(targets)}")

    # 冻结件只读校验：JSON 现场 SHA == sidecar == freeze receipt。
    md = FROZEN_MANIFEST_DIR
    probs, facts = [], []
    for base, want in (("candidate_c_eo_split_manifest_v1.json", EXPECT_SPLIT_MANIFEST_SHA),
                       ("candidate_c_q4_partition_manifest_v1.json", EXPECT_Q4_MANIFEST_SHA)):
        j, sc = md / base, md / (base + ".sha256")
        if not j.is_file():
            probs.append(f"{base}: 缺文件"); continue
        live = ccq4.sha256_file(j)
        m = re.search(r"\b([0-9a-f]{64})\b", sc.read_text()) if sc.is_file() else None
        side = m.group(1) if m else "<无 sidecar>"
        if live != want:
            probs.append(f"{base}: 现场 {live[:16]} != 冻结 {want[:16]}")
        if side != want:
            probs.append(f"{base}: sidecar {side[:16]} != 冻结 {want[:16]}")
        facts.append(f"{base.split('_v1')[0][12:]}={live[:16]}")
    rec.check("T18i", "两份冻结 manifest 的现场 SHA == sidecar == 本测试内嵌的冻结值",
              not probs, f"问题={probs or '无'} | {' '.join(facts)}")

    # split 契约的实质内容每轮重算，不靠"冻结过一次"背书。
    sp = md / "candidate_c_eo_split_manifest_v1.json"
    if sp.is_file():
        blob = json.loads(sp.read_text())
        vs = blob.get("validation_subsplit", {})
        dev = list(vs.get("val_dev", {}).get("ids", []))
        lock = list(vs.get("val_locked", {}).get("ids", []))
        gd = {ccq4.geo_group_of(i) for i in dev}
        gl = {ccq4.geo_group_of(i) for i in lock}
        cross = gd & gl
        checks = {
            "train_n": blob.get("train", {}).get("n_cubes") == 23816,
            "train_sha": blob.get("train", {}).get("data_manifest_sha256", "").startswith(
                "17c645d92e9dd4c3"),
            "val_n": blob.get("validation", {}).get("n_cubes") == 952,
            "val_sha": blob.get("validation", {}).get("data_manifest_sha256", "").startswith(
                "555d44c0d59ab390"),
            "dev_476": len(dev) == 476,
            "locked_476": len(lock) == 476,
            "id_disjoint": not (set(dev) & set(lock)),
            "union_952": len(set(dev) | set(lock)) == 952,
            "geo_no_cross": not cross,
            "flag_no_cross": vs.get("no_geo_group_crosses_splits") is True,
            "deterministic": vs.get("rule_is_deterministic") is True,
            "no_rng": vs.get("consumes_rng") is False,
        }
        rec.check("T18j", "冻结 split：476/476 互斥、并集 952、地理组不跨 split",
                  all(checks.values()),
                  " ".join(f"{k}={v}" for k, v in checks.items())
                  + f" | tiles dev={len(gd)} locked={len(gl)} 交集={sorted(cross) or '空'}")

        rcp = md / "manifest_freeze_receipt.json"
        if rcp.is_file():
            rtext = rcp.read_text()
            rec.check("T18k", "freeze receipt 同时记录两份 manifest 的 SHA",
                      EXPECT_SPLIT_MANIFEST_SHA in rtext and EXPECT_Q4_MANIFEST_SHA in rtext,
                      f"receipt={rcp.name} 含 split SHA="
                      f"{EXPECT_SPLIT_MANIFEST_SHA in rtext} 含 q4 SHA="
                      f"{EXPECT_Q4_MANIFEST_SHA in rtext}")
        else:
            rec.check("T18k", "freeze receipt 存在", False, f"缺 {rcp}")
    else:
        rec.check("T18j", "冻结 split manifest 可读", False, f"缺 {sp}")


# ------------------------------------------------------------------------- main
def dir_size_mb(p) -> float:
    tot = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                tot += (Path(root) / f).stat().st_size
            except OSError:
                pass
    return tot / 1048576.0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Candidate C CPU-only 测试 T12/T13、T15–T18")
    ap.add_argument("--report", default="", help="机器可读报告落盘路径 (JSON)")
    ap.add_argument("--scratch", default="",
                    help="临时产物根目录；默认在 /tmp 下新建带时间戳目录，且不自动删除")
    ap.add_argument("--only", default="", help="逗号分隔只跑指定用例，如 T12,T16")
    args = ap.parse_args(argv)
    if os.environ.get("CUDA_VISIBLE_DEVICES", "unset") != "":
        print("WARN CUDA_VISIBLE_DEVICES 未设为空串；本套件仍强制 CPU", flush=True)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    only = {s.strip().upper() for s in args.only.split(",") if s.strip()}

    def want(tid):
        return not only or tid in only

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    scratch = (Path(args.scratch) if args.scratch
               else Path(tempfile.mkdtemp(prefix=f"cc_cpu_{stamp}_")))
    scratch.mkdir(parents=True, exist_ok=True)
    print(f"scratch = {scratch}  (不自动删除：失败证据必须留存)", flush=True)
    rec = Recorder("candidate_c_resume_T12_T13_T15_T16_T17_T18")

    ck_dir = None
    if want("T12"):
        ck_dir, _S, _a, _s = t12_atomic_ckpt_roundtrip(rec, scratch)
    if want("T13"):
        t13_exact_resume(rec, scratch)
    if want("T15"):
        t15_arm_parity(rec, scratch)
    if (want("T16") or want("T17")) and ck_dir is None:
        _s, ck_dir, _S, _a = train_min(scratch, "t16_seed")
    if want("T16"):
        t16_strict_loader(rec, ck_dir, scratch)
    if want("T17"):
        t17_evaluator_outputs(rec, ck_dir, scratch)
    if want("T18"):
        t18_whitespace_and_regressions(rec)

    report = rec.report()
    report["scratch_dir"] = str(scratch)
    report["scratch_mb"] = round(dir_size_mb(scratch), 1)
    print(json.dumps({k: v for k, v in report.items() if k != "checks"},
                     indent=2, ensure_ascii=False), flush=True)
    if args.report:
        report["provenance"] = ccq4.provenance(
            {"suite": report["suite"], "scratch_dir": str(scratch)})
        sha = ccq4.atomic_write_json(args.report, report)
        print(f"report -> {args.report}  sha256={sha}", flush=True)
    return 0 if report["n_fatal_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
