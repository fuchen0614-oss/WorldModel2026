#!/usr/bin/env python3
"""E0 v3 最终封账验收器 —— 严格 fail-closed，全部事实从一手来源重新推导。

与 v1/v2 的关键区别（v1/v2 一律保留作为审计证据，本脚本不读取它们的结论）：

  * 只信任以下一手来源：六份正式 raw 结果 JSON、原始 launch shard、
    20260818 冻结 launch manifest、historical_11904_reference.json、
    checkpoint 二进制、Q3 协议文件、weight registry、parameter audit、
    M9 验收报告。A03 与 v1/v2 的任何比较表都不作为数据来源。
  * 六组门：A 作业与启动记录 / B 四份 Q1Q2 / C 两份 Q3 /
    D 历史复现（57 个正式指标，排除 `_` 前缀元数据） / E 完整性 /
    F sanity anchor 复核。
  * 任何一项失败 => 整体 BLOCKED，不写 ACCEPTED。
  * 严格 CPU-only：不 import torch，不创建 CUDA context，不动任何进程。
  * 所有输出都用 tempfile + json 往返校验 + fsync + rename 原子写入。

用法： CUDA_VISIBLE_DEVICES="" python3 verify_and_aggregate_retry_v3.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ATTEMPT = Path(__file__).resolve().parent               # .../20260820_100718
TS_ROOT = Path(__file__).resolve().parents[3]           # .../WorldModel2026v2/terrastate
AGENT_ROOT = TS_ROOT.parents[1]                         # .../Agent
PARENT = ATTEMPT.parent / "20260818_154859"
RUNS = ATTEMPT / "runs"
RESUME_OPS = TS_ROOT / "ops/resume11904_to14880/20260818_112933"

LAUNCH_MANIFEST = PARENT / "launch_manifest.json"
LAUNCH_MANIFEST_SHA = "500e5031335c366ed06819dd9af8679dcf0318301d559aa7bfd573688c6cdd08"
HIST_REF = PARENT / "historical_11904_reference.json"
HIST_REF_SHA = "0b97406c3bd44cd68bb3f098b6ee2fb5da914f1198bd4684a1a55c813bd493f4"
REGISTRY = TS_ROOT / "artifacts/weight_registry.json"
REGISTRY_REVISION = "a7fd2763935a26d1"
PARAM_AUDIT = RESUME_OPS / "parameter_audit.json"
M9_REPORT = RESUME_OPS / "m9_acceptance_report.json"
STATE_SHA_CHECK = RESUME_OPS / "state_sha_check.json"
OBJECTS = AGENT_ROOT / "model-artifacts/objects/sha256"
ALIAS_FILE = (AGENT_ROOT
              / "model-artifacts/aliases/terrastate__v2__default-training-anchor.json")

# ---- 三份 checkpoint 身份（逻辑 ID -> 文件 SHA-256；文件按内容寻址存放） ----
CKPT = {
    "boundary11904": {
        "logical_id": "terrastate/v2/legacy-boundary11904@v1",
        "file_sha256": "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd",
        "step": 11904, "expect_bytes": 37972401,
    },
    "verified14880": {
        "logical_id": "terrastate/v2/verified-resume14880@v1",
        "file_sha256": "a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f",
        "step": 14880, "expect_bytes": 44302057,
    },
    "historical14880": {
        "logical_id": "terrastate/v2/historical-full14880@v1",
        "file_sha256": "99f15a35fb9a356901c995bb0f48280a4da236f6970d0dd06343a28857fe2b8b",
        "step": 14880, "expect_bytes": 44300969,
    },
}

# ---- 冻结数据 manifest ----
# 路径由两个独立见证确定并已实测核验：
#   (1) 20260818 launch_manifest.json 的 frozen_inputs.{validation,oodt}_manifest.path
#   (2) 六份 raw 结果 JSON 里 evaluator 自身的 --data-manifest argv
# 两处一致，且磁盘实测 sha256 与 provenance.data_manifest_sha256 相同。
PLANB_ROOT = AGENT_ROOT / "WorldModel2026-planb"
MANIFESTS = {
    "val": (PLANB_ROOT / "artifacts/protocols/b4_eval/val_chopped.manifest.json",
            "d9bd91d6e2aafbf66b38afca7576516823fc710b6cc3ca44ea25d2e31152bf8e", 952),
    "oodt": (PLANB_ROOT / "evaluations/greenearthnet_oodt_20260719_214234"
                          / "greenearthnet_oodt_chopped_manifest.json",
             "58c8d64897193e9cffff5bc6c8524909707ebae5376b5d4dee68597ef08e1e49", 1904),
}
# JOBS/MANIFESTS 用的内部键 -> evaluator 在 provenance.split 里实际写入的字符串。
# 内部键是本脚本的索引，不是被断言的事实；断言必须用 evaluator 的真实取值。
SPLIT_LABEL = {"val": "val", "oodt": "ood-t_chopped"}

# checkpoint 逻辑角色在 run 目录名里的标记（Q3 身份为 sidecar-bound，见 gate C4c）
Q3_DIRTAG = {"boundary11904": "legacy11904", "verified14880": "v14880",
             "historical14880": "historical14880"}
EVALUATORS = {
    "eval/eval_b4_exclusive_contract.py":
        "c6759dec60ede433f99a97b1ba3191d9427210cd907a08d6d8776dfb8efec9b4",
    "eval/extreme_state_audit.py":
        "10ef9e40f1f668a3b12c34e70accefae98ca4c419c7f122829f5531c5cd9f838",
}
Q3_PROTO = TS_ROOT / "artifacts/protocols/extreme_audit_oodt_v1"

Q1Q2_FILE = "state_contract_exclusive.json"
Q3_FILE = "extreme_state_audit.json"

# ---- 六份正式作业（allowlist）。physical_gpu 只能来自 launch shard，不得由名字推断 ----
JOBS = {
    "gpu0_v14880_val_q1q2":       dict(kind="q1q2", ckpt="verified14880",
                                       split="val",  n_targets=952,  stage=3, pgpu=5),
    "gpu1_v14880_oodt_q1q2":      dict(kind="q1q2", ckpt="verified14880",
                                       split="oodt", n_targets=1904, stage=3, pgpu=2),
    "gpu3_legacy11904_val_q1q2":  dict(kind="q1q2", ckpt="boundary11904",
                                       split="val",  n_targets=952,  stage=2, pgpu=6),
    "gpu4_legacy11904_oodt_q1q2": dict(kind="q1q2", ckpt="boundary11904",
                                       split="oodt", n_targets=1904, stage=2, pgpu=4),
    "gpu2_v14880_oodt_q3":        dict(kind="q3",   ckpt="verified14880",
                                       split="oodt", n_targets=None, stage=3, pgpu=5),
    "gpu5_legacy11904_oodt_q3":   dict(kind="q3",   ckpt="boundary11904",
                                       split="oodt", n_targets=None, stage=2, pgpu=6),
}
Q1Q2_JOBS = [j for j, c in JOBS.items() if c["kind"] == "q1q2"]
Q3_JOBS = [j for j, c in JOBS.items() if c["kind"] == "q3"]

# 六份 raw 结果 JSON 的 SHA-256（本轮只读复核；不一致即 fail-closed）
RAW_SHA = {
    "gpu0_v14880_val_q1q2":
        "229918a49a42887614d1cfce99dae70c2f0ccdc3590490bce73d5a2e8434314f",
    "gpu1_v14880_oodt_q1q2":
        "965a46d249f816c0b17df903185a74bc3c6c371ca10b5ef7472d4459e31c9670",
    "gpu3_legacy11904_val_q1q2":
        "10a903185fd14c16d0fec49b2e730a2bd451d3ff25b2fcaef40cf242f4960354",
    "gpu4_legacy11904_oodt_q1q2":
        "d0ebbbbea74de549bba481ae5e3ee40fd478a8b5552cbfff09c84ec0e115f7c0",
    "gpu2_v14880_oodt_q3":
        "4a51ce5d2877305df1f10fe4c3e278945c4decca657ffcfc6d0f242ebf7bcc43",
    "gpu5_legacy11904_oodt_q3":
        "ccd1a9a107237bc409c96b92032497a84e5d8153d76270f04665153bab6a00fa",
}

# ---- 三个已知无效的 partial 目录 + 20260818 中断尝试（必须登记、必须排除） ----
INVALID_PARTIAL = ["gpu2_v14880_oodt_q1q2", "gpu5_v14880_val_q1q2",
                   "gpu6_legacy11904_val_q1q2"]

# ---- 用户下发的 sanity anchor：脚本读数必须与之一致，否则停止封账 ----
ANCHORS = [
    ("gpu3_legacy11904_val_q1q2",  "Q1_forecast.full.R2", 0.49732196418835595),
    ("gpu0_v14880_val_q1q2",       "Q1_forecast.full.R2", 0.49709355615470024),
    ("gpu4_legacy11904_oodt_q1q2", "Q1_forecast.full.R2", 0.56934936116640855),
    ("gpu1_v14880_oodt_q1q2",      "Q1_forecast.full.R2", 0.5692781483135535),
]
ANCHOR_TOL = 1e-12

# ---- M9 交叉验证锚点（来自 m9_acceptance_report.json / state_sha_check.json） ----
M9_EXPECT = {
    "accepted": True, "n_checks": 31, "final_step": 14880, "stage": 3,
    "checkpoint_last_sha256": CKPT["verified14880"]["file_sha256"],
    "parent_file_sha256": CKPT["boundary11904"]["file_sha256"],
    "parent_step": 11904, "parent_stage_recorded": 2, "resume_stage_applied": 3,
    "parent_b4_state_sha256":
        "aba100c138119bc0fc4412082412596dcf31090410643aa0736b5705b04feaa7",
    "value_digest_16hex": "aa98fbd2fa302727",   # verified vs 历史 14,880，255 张量
    "n_model_tensors": 255, "n_updates": 2976,
}

# ============================ 基础工具 ============================

# 同一进程内按 (真实路径, 大小, mtime_ns) 记忆化：三份 ~44MB checkpoint 会在
# gate A 与 artifact index 两处被要求摘要，重复读盘在网络文件系统上代价很高。
# 键里带 size+mtime_ns，文件一旦变动缓存自动失效，不会掩盖内容改变。
_SHA_CACHE: dict[tuple[str, int, int], str] = {}


def sha256_file(p: Path) -> str | None:
    p = Path(p)
    if not p.is_file():
        return None
    st = p.stat()
    key = (str(p.resolve()), st.st_size, st.st_mtime_ns)
    hit = _SHA_CACHE.get(key)
    if hit is not None:
        return hit
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    _SHA_CACHE[key] = h.hexdigest()
    return _SHA_CACHE[key]


def load_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def get_path(obj, dotted: str, default=None):
    """按点号路径取值；不存在返回 default。列表下标用数字段。"""
    cur = obj
    for seg in dotted.split("."):
        if isinstance(cur, dict):
            if seg not in cur:
                return default
            cur = cur[seg]
        elif isinstance(cur, list):
            try:
                cur = cur[int(seg)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return cur


def flatten(obj, prefix="", out=None, skip=()):
    """把嵌套结构压平成 dotted -> 标量。skip 中的键名整枝跳过。"""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in skip:
                continue
            flatten(v, f"{prefix}.{k}" if prefix else str(k), out, skip)
    elif isinstance(obj, list):
        out[prefix] = f"<list n={len(obj)}>"
    else:
        out[prefix] = obj
    return out


def find_key(obj, key):
    """在任意深度查找第一个同名键的值。用于 schema 未完全固定的外部协议文件，
    避免把猜测的嵌套路径写死。找不到返回 None。"""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def walk_nonfinite(obj, prefix="", out=None):
    """递归找出所有 NaN / Inf 的路径。不做任何整枝，覆盖整份文档。"""
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk_nonfinite(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_nonfinite(v, f"{prefix}[{i}]", out)
    elif isinstance(obj, float) and not math.isfinite(obj):
        out.append(prefix)
    return out


def atomic_write_json(path: Path, payload) -> str:
    """临时文件 + json 往返校验 + fsync + rename。返回落盘后的 SHA-256。"""
    path = Path(path)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False)
    json.loads(text)                      # 往返校验，拒绝写出不可解析内容
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dirfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return sha256_file(path)


class Gate:
    """一组检查。任何 ok=False 即该组失败。"""

    def __init__(self, gid: str, title: str):
        self.gid, self.title, self.checks = gid, title, []

    def add(self, name: str, ok: bool, detail: str = "", evidence: str = ""):
        self.checks.append({"name": name, "ok": bool(ok),
                            "detail": str(detail), "evidence": str(evidence)})
        return bool(ok)

    def eq(self, name, got, want, detail=""):
        return self.add(name, got == want,
                        detail or f"got={got!r} want={want!r}")

    def close(self, name, got, want, tol, detail=""):
        ok = (isinstance(got, (int, float)) and not isinstance(got, bool)
              and math.isfinite(got) and abs(float(got) - float(want)) <= tol)
        d = detail or f"got={got!r} want={want!r} tol={tol:g}"
        if isinstance(got, (int, float)) and not isinstance(got, bool):
            d += f" |Δ|={abs(float(got) - float(want)):.3e}"
        return self.add(name, ok, d)

    @property
    def failed(self):
        return [c for c in self.checks if not c["ok"]]

    @property
    def ok(self):
        return len(self.failed) == 0 and len(self.checks) > 0

    def as_dict(self):
        return {"gate": self.gid, "title": self.title, "n_checks": len(self.checks),
                "n_failed": len(self.failed), "ok": self.ok, "checks": self.checks}


# ============================ Gate A：作业与启动记录 ============================

def gate_a(ctx) -> Gate:
    g = Gate("A", "作业清单、启动记录与 checkpoint 身份")

    # A1 allowlist 精确性：runs/ 下的最终结果目录必须恰好是六个正式作业
    present = sorted(d.name for d in RUNS.iterdir() if d.is_dir())
    finals = sorted(d.name for d in RUNS.iterdir()
                    if d.is_dir() and ((d / Q1Q2_FILE).exists() or (d / Q3_FILE).exists()))
    g.eq("allowlist_exact_six", finals, sorted(JOBS),
         f"带最终结果 JSON 的目录={finals}")
    g.eq("runs_dirs_are_six_plus_three_partial", present,
         sorted(list(JOBS) + INVALID_PARTIAL), f"runs/ 全部子目录={present}")
    g.add("no_unexpected_run_dir", set(present) <= set(JOBS) | set(INVALID_PARTIAL),
          f"意外目录={sorted(set(present) - set(JOBS) - set(INVALID_PARTIAL))}")

    # A2 三个无效 partial 目录必须存在（作为审计证据）且不含最终结果 JSON
    for name in INVALID_PARTIAL:
        d = RUNS / name
        g.add(f"partial_dir_preserved:{name}", d.is_dir(), str(d))
        g.add(f"partial_dir_has_no_final_json:{name}",
              d.is_dir() and not (d / Q1Q2_FILE).exists() and not (d / Q3_FILE).exists(),
              "无效 partial 目录不得含最终结果 JSON")

    # A3 六份 raw JSON 的 SHA-256 必须与本轮清点值一致（只读复核）
    for name, want in RAW_SHA.items():
        fn = Q1Q2_FILE if JOBS[name]["kind"] == "q1q2" else Q3_FILE
        got = sha256_file(RUNS / name / fn)
        g.eq(f"raw_json_sha256:{name}", got, want, f"got={got} want={want}")

    # A4 三份 checkpoint：内容寻址自洽（文件 SHA == 文件名）、字节数、只读权限
    for role, meta in CKPT.items():
        sha = meta["file_sha256"]
        p = OBJECTS / sha[:2] / f"{sha}.pt"
        exists = p.is_file()
        g.add(f"ckpt_exists:{role}", exists, str(p))
        if exists:
            got = sha256_file(p)
            g.eq(f"ckpt_sha_matches_filename:{role}", got, sha)
            g.eq(f"ckpt_bytes:{role}", p.stat().st_size, meta["expect_bytes"])
            mode = oct(p.stat().st_mode & 0o777)
            g.eq(f"ckpt_mode_readonly:{role}", mode, "0o444")
            ctx["ckpt_stat"][role] = {"path": str(p), "bytes": p.stat().st_size,
                                      "mode": mode, "file_sha256": got,
                                      "logical_id": meta["logical_id"],
                                      "step": meta["step"]}

    # A5 registry：revision 与三份 checkpoint 登记
    reg_sha = sha256_file(REGISTRY)
    g.add("registry_exists", REGISTRY.is_file(), str(REGISTRY))
    if REGISTRY.is_file():
        reg = load_json(REGISTRY)
        ctx["registry"] = {"path": str(REGISTRY), "sha256": reg_sha,
                           "revision": reg.get("revision"),
                           "schema": reg.get("schema"),
                           "n_artifacts": len(reg.get("artifacts", {}))}
        g.eq("registry_revision", reg.get("revision"), REGISTRY_REVISION)
        arts_raw = reg.get("artifacts", {})
        if isinstance(arts_raw, list):     # 兼容 list / dict 两种容器形态
            arts = {}
            for e in arts_raw:
                if isinstance(e, dict):
                    lid = e.get("logical_id") or e.get("id") or e.get("name")
                    if lid:
                        arts[lid] = e
        else:
            arts = dict(arts_raw)

        def _f(e, *keys):
            for k in keys:
                if isinstance(e, dict) and k in e:
                    return e[k]
            return None

        for role, meta in CKPT.items():
            ent = arts.get(meta["logical_id"])
            g.add(f"registry_has:{role}", isinstance(ent, dict), meta["logical_id"])
            if isinstance(ent, dict):
                g.eq(f"registry_sha:{role}",
                     _f(ent, "file_sha256", "sha256", "target_file_sha256"),
                     meta["file_sha256"])
                g.eq(f"registry_step:{role}", _f(ent, "step", "global_step"),
                     meta["step"])
        g.add("registry_reserved_empty", not reg.get("reserved"),
              f"reserved={reg.get('reserved')!r}（空 dict 与空 list 均视为空）")
        # 捕获三份 checkpoint 的完整登记字段，供 A03 谱系表直接引用
        for role, meta in CKPT.items():
            ent = arts.get(meta["logical_id"])
            if isinstance(ent, dict):
                ctx["registry_entries"][role] = {
                    k: ent.get(k) for k in (
                        "role", "arch", "candidate", "step", "total_steps", "epoch",
                        "micro_in_epoch", "stage_recorded_in_file",
                        "stage_of_next_update", "route_version", "file_bytes",
                        "file_sha256", "object_relpath", "original_path", "parent_id",
                        "parent_file_sha256", "b4_state_sha256", "best_val",
                        "immutable", "m9_checks_passed", "m9_report", "evidence_doc",
                        "provenance_notes") if k in ent}
        # 11,904 的 b4_state_sha256 必须与 M9 记录的 parent_b4_state_sha256 一致
        b4s = ctx["registry_entries"].get("boundary11904", {}).get("b4_state_sha256")
        g.eq("registry_11904_b4_state_sha_matches_m9", b4s,
             M9_EXPECT["parent_b4_state_sha256"])
        # verified 14,880 的父指针必须指回 11,904
        g.eq("registry_verified_parent_id",
             ctx["registry_entries"].get("verified14880", {}).get("parent_id"),
             CKPT["boundary11904"]["logical_id"])
        g.eq("registry_verified_parent_sha",
             ctx["registry_entries"].get("verified14880", {}).get("parent_file_sha256"),
             CKPT["boundary11904"]["file_sha256"])
        # 历史 14,880 不得带 parent_id（它来自同一次未中断的原始训练）
        g.add("registry_historical_has_no_parent_pointer",
              "parent_id" not in ctx["registry_entries"].get("historical14880", {}),
              "历史 14,880 由同一次未中断原始训练产出，不是 resume 产物")
        ctx["registry"]["aliases"] = reg.get("aliases")
        ctx["registry"]["policy"] = reg.get("policy")
        ctx["registry"]["store"] = reg.get("store")

    # A6 alias：default-training-anchor 必须指向 verified 14,880
    if ALIAS_FILE.is_file():
        al = load_json(ALIAS_FILE)
        ctx["alias"] = {"path": str(ALIAS_FILE), "sha256": sha256_file(ALIAS_FILE),
                        "logical_id": al.get("logical_id"),
                        "target_file_sha256": al.get("target_file_sha256"),
                        "set_at": al.get("set_at"), "set_by": al.get("set_by")}
        g.eq("alias_logical_id", al.get("logical_id"),
             CKPT["verified14880"]["logical_id"])
        g.eq("alias_target_sha", al.get("target_file_sha256"),
             CKPT["verified14880"]["file_sha256"])
    else:
        g.add("alias_exists", False, str(ALIAS_FILE))

    # A7 launch shard 是 job -> 物理 GPU 的唯一权威来源（不得由逻辑名推断）
    seen = {}
    for pg in (2, 4, 5, 6):
        sp = ATTEMPT / f"launch_record_shard_pgpu{pg}.json"
        if not g.add(f"shard_exists:pgpu{pg}", sp.is_file(), str(sp)):
            continue
        sh = load_json(sp)
        g.eq(f"shard_physical_gpu:pgpu{pg}", sh.get("physical_gpu"), pg)
        for job in sh.get("jobs", []):
            nm = job.get("name")
            g.add(f"shard_job_in_allowlist:{nm}", nm in JOBS, f"pgpu{pg} -> {nm}")
            g.add(f"shard_job_unique:{nm}", nm not in seen,
                  f"首次出现={seen.get(nm)} 重复出现={pg}")
            if nm not in JOBS:
                continue
            seen[nm] = pg
            g.eq(f"shard_job_pgpu:{nm}", job.get("physical_gpu"), JOBS[nm]["pgpu"])
            g.eq(f"shard_exit_code:{nm}", job.get("exit_code"), 0)
            g.eq(f"shard_ckpt_sha:{nm}", job.get("checkpoint_sha256"),
                 CKPT[JOBS[nm]["ckpt"]]["file_sha256"])
            g.add(f"shard_output_dir:{nm}",
                  Path(job.get("output_dir", "/nonexistent")).resolve()
                  == (RUNS / nm).resolve(), job.get("output_dir"))
            if JOBS[nm]["kind"] == "q1q2":
                g.eq(f"shard_expected_targets:{nm}", job.get("expected_targets"),
                     JOBS[nm]["n_targets"])
            else:
                g.eq(f"shard_kind_q3:{nm}", job.get("kind"), "q3")
                g.eq(f"shard_expected_pairs:{nm}", job.get("expected_pairs"), 84)
            ctx["launch"][nm] = {
                "physical_gpu": job.get("physical_gpu"), "pid": job.get("pid"),
                "exit_code": job.get("exit_code"), "started_utc": job.get("started_utc"),
                "checkpoint_sha256": job.get("checkpoint_sha256"), "log": job.get("log"),
                "expected_targets": job.get("expected_targets"),
                "expected_pairs": job.get("expected_pairs"), "shard": sp.name}
    g.eq("shard_covers_all_six", sorted(seen), sorted(JOBS))

    # A8 provenance 缺口：e0_launch_record.gpu{2,4,5,6}.json 的 jobs 全为空 —— 诚实登记
    for pg in (2, 4, 5, 6):
        p = ATTEMPT / f"e0_launch_record.gpu{pg}.json"
        if p.is_file():
            rec = load_json(p)
            empty = rec.get("jobs") == []
            ctx["provenance_gaps"].append({
                "artifact": p.name, "schema": rec.get("schema"), "gpu": rec.get("gpu"),
                "n_jobs": len(rec.get("jobs", [])), "sha256": sha256_file(p),
                "empty_as_expected": empty,
                "gap": "jobs 列表为空；真实启动记录只存在于 "
                       "launch_record_shard_pgpu*.json，本文件不可作为启动证据"})
            g.add(f"provenance_gap_registered:gpu{pg}", empty,
                  f"jobs={rec.get('jobs')!r}（空是已知缺口，必须登记而非掩盖）")
    mainrec = ATTEMPT / "e0_launch_record.json"
    if mainrec.is_file():
        mr = load_json(mainrec)
        jb = mr.get("jobs")
        ctx["provenance_gaps"].append({
            "artifact": mainrec.name, "sha256": sha256_file(mainrec),
            "n_jobs": len(jb) if isinstance(jb, list) else -1,
            "gap": "合并产物；job 名称字段曾缺失，v2 阶段以 "
                   "e0_launch_record_reconstructed.json 补齐，v3 直接改用 shard 为准"})

    # A9 冻结 launch manifest（20260818）：SHA + 关键冻结值成员检查
    ms = sha256_file(LAUNCH_MANIFEST)
    g.add("launch_manifest_exists", LAUNCH_MANIFEST.is_file(), str(LAUNCH_MANIFEST))
    g.eq("launch_manifest_sha256", ms, LAUNCH_MANIFEST_SHA)
    if LAUNCH_MANIFEST.is_file():
        lm = load_json(LAUNCH_MANIFEST)

        def strs(o, acc=None):
            acc = set() if acc is None else acc
            if isinstance(o, dict):
                [strs(v, acc) for v in o.values()]
            elif isinstance(o, list):
                [strs(v, acc) for v in o]
            elif isinstance(o, str):
                acc.add(o)
            return acc

        S = strs(lm)
        ctx["launch_manifest"] = {"path": str(LAUNCH_MANIFEST), "sha256": ms,
                                  "top_keys": sorted(lm) if isinstance(lm, dict) else None}
        g.add("manifest_carries_registry_revision", REGISTRY_REVISION in S,
              f"revision {REGISTRY_REVISION} 出现在冻结 manifest 中")
        for role, meta in CKPT.items():
            if role == "historical14880":
                continue          # 历史 14,880 不参与本轮评测，manifest 不必引用
            g.add(f"manifest_carries_ckpt_sha:{role}", meta["file_sha256"] in S,
                  meta["logical_id"])
        for key, (_p, sha, _n) in MANIFESTS.items():
            g.add(f"manifest_carries_data_manifest_sha:{key}", sha in S, key)
        for rel, sha in EVALUATORS.items():
            g.add(f"manifest_carries_evaluator_sha:{rel}", sha in S, rel)
    return g


# ============================ Gate B：四份 Q1/Q2 正式结果 ============================

def gate_b(ctx) -> Gate:
    g = Gate("B", "四份 Q1/Q2 结果：状态、契约、绑定、数值有限性与 Q2 schema 完整性")
    commits = {}
    for name in sorted(Q1Q2_JOBS):
        cfg = JOBS[name]
        p = RUNS / name / Q1Q2_FILE
        if not g.add(f"exists:{name}", p.is_file(), str(p)):
            continue
        d = load_json(p)
        ctx["raw"][name] = d
        pv = d.get("provenance", {})

        # B1 完成状态（v2 曾弱化过的 formal/split/sections 检查在此全部恢复）
        g.eq(f"status:{name}", d.get("status"), "COMPLETE")
        g.eq(f"incomplete_reasons_empty:{name}", d.get("incomplete_reasons"), [])
        g.eq(f"formal:{name}", pv.get("formal"), True)
        g.eq(f"split:{name}", pv.get("split"), SPLIT_LABEL[cfg["split"]])
        g.eq(f"sections:{name}", pv.get("sections"), ["q1", "q2"])
        g.eq(f"n_targets:{name}", pv.get("n_targets"), cfg["n_targets"])
        g.eq(f"checkpoint_unchanged:{name}", d.get("checkpoint_unchanged"), True)
        g.eq(f"route_version:{name}", pv.get("route_version"), "exclusive_v1")
        g.eq(f"checkpoint_stage:{name}", pv.get("checkpoint_stage"), cfg["stage"])

        # B2 checkpoint 绑定：JSON 里的 checkpoint 是路径字符串，需与内容寻址对象一致
        want_sha = CKPT[cfg["ckpt"]]["file_sha256"]
        g.eq(f"prov_checkpoint_sha256:{name}", pv.get("checkpoint_sha256"), want_sha)
        ck = d.get("checkpoint")
        g.add(f"checkpoint_is_path_string:{name}", isinstance(ck, str), f"type={type(ck).__name__}")
        g.add(f"checkpoint_path_contains_sha:{name}",
              isinstance(ck, str) and want_sha in ck, str(ck))
        # 并与 launch shard 记录的 checkpoint 交叉核对
        g.eq(f"shard_vs_json_ckpt:{name}",
             ctx["launch"].get(name, {}).get("checkpoint_sha256"), want_sha)

        # B3 数据 manifest 绑定到官方冻结清单
        _mp, msha, mn = MANIFESTS[cfg["split"]]
        g.eq(f"data_manifest_sha256:{name}", pv.get("data_manifest_sha256"), msha)
        g.eq(f"manifest_count_matches_n_targets:{name}", mn, cfg["n_targets"])

        # B4 evaluator commit 必须存在且四份一致
        commits[name] = pv.get("evaluator_commit")
        g.add(f"evaluator_commit_present:{name}", bool(pv.get("evaluator_commit")),
              str(pv.get("evaluator_commit")))

        # B5 Q1 schema 完整性：主指标 + 五个 horizon + 四个植被层
        q1_req = [f"Q1_forecast.full.{m}" for m in
                  ("R2", "rmse", "nse", "biasabs", "rmse25",
                   "rmse_0_5", "rmse_5_10", "rmse_10_15", "rmse_15_20")]
        q1_req += [f"Q1_forecast.full.{m}_{s}"
                   for m in ("R2", "rmse", "nse", "biasabs")
                   for s in ("forest", "shrub", "grass", "crop")]
        miss = [k for k in q1_req if not isinstance(get_path(d, k), (int, float))]
        g.add(f"q1_schema_complete:{name}", not miss, f"缺失或非数值={miss}")

        # B6 Q2 schema 完整性：三条臂 + 官方 Δ + 两个 bootstrap 家族 + 不变量
        q2_req = []
        for arm in ("full", "alpha0", "T_identity"):
            q2_req += [f"Q2_load_bearing.{arm}.{m}" for m in
                       ("R2", "rmse", "nse", "biasabs", "rmse25",
                        "rmse_0_5", "rmse_5_10", "rmse_10_15", "rmse_15_20")]
        q2_req += ["Q2_load_bearing.official_R2_full_minus_alpha0",
                   "Q2_load_bearing.official_R2_full_minus_Tid",
                   "Q2_load_bearing.dr2_floor"]
        for fam in ("closure_cut_alpha0", "transition_identity"):
            q2_req += [f"Q2_load_bearing.{fam}.bootstrap95.{m}"
                       for m in ("mean", "ci_low", "ci_high", "frac_pos", "n")]
            q2_req += [f"Q2_load_bearing.{fam}.paired.{m}"
                       for m in ("n", "win", "tie", "loss",
                                 "mean_delta_R2", "median_delta_R2")]
        miss2 = [k for k in q2_req if not isinstance(get_path(d, k), (int, float))]
        g.add(f"q2_schema_complete:{name}", not miss2, f"缺失或非数值={miss2}")
        for k in ("Q2_load_bearing.invariants.alpha0_pred_equals_context_prior",
                  "Q2_load_bearing.invariants.T_identity_is_state_identity",
                  "Q2_load_bearing.invariants.live_weights_restored",
                  "Q2_load_bearing.dr2_floor_pass"):
            g.eq(f"{k.split('.')[-1]}:{name}", get_path(d, k), True)
        g.eq(f"verdict:{name}", get_path(d, "Q2_load_bearing.verdict"), "LOAD_BEARING")
        g.eq(f"dr2_floor:{name}", get_path(d, "Q2_load_bearing.dr2_floor"), 0.005)

        # B7 内部自洽：官方 Δ 必须等于两臂 R² 之差；Q2.full 必须镜像 Q1.full
        fR2 = get_path(d, "Q2_load_bearing.full.R2")
        a0R2 = get_path(d, "Q2_load_bearing.alpha0.R2")
        tiR2 = get_path(d, "Q2_load_bearing.T_identity.R2")
        g.close(f"official_delta_a0_consistent:{name}",
                get_path(d, "Q2_load_bearing.official_R2_full_minus_alpha0"),
                fR2 - a0R2, 1e-12)
        g.close(f"official_delta_tid_consistent:{name}",
                get_path(d, "Q2_load_bearing.official_R2_full_minus_Tid"),
                fR2 - tiR2, 1e-12)
        for m in ("R2", "rmse", "nse", "biasabs"):
            g.close(f"q2_full_mirrors_q1:{name}.{m}",
                    get_path(d, f"Q2_load_bearing.full.{m}"),
                    get_path(d, f"Q1_forecast.full.{m}"), 0.0)

        # B8 两个 bootstrap 家族的内部一致性
        for fam in ("closure_cut_alpha0", "transition_identity"):
            b = get_path(d, f"Q2_load_bearing.{fam}.bootstrap95", {})
            pr = get_path(d, f"Q2_load_bearing.{fam}.paired", {})
            g.eq(f"{fam}_paired_counts_sum:{name}",
                 pr.get("win", 0) + pr.get("tie", 0) + pr.get("loss", 0), pr.get("n"))
            g.eq(f"{fam}_bootstrap_n_matches_paired:{name}", b.get("n"), pr.get("n"))
            g.close(f"{fam}_mean_matches_paired:{name}",
                    b.get("mean"), pr.get("mean_delta_R2"), 1e-9)
            lo, hi, mu = b.get("ci_low"), b.get("ci_high"), b.get("mean")
            g.add(f"{fam}_ci_ordered:{name}",
                  all(isinstance(x, float) for x in (lo, hi, mu)) and lo <= mu <= hi,
                  f"ci_low={lo} mean={mu} ci_high={hi}")
            g.eq(f"{fam}_significance_consistent:{name}",
                 b.get("significant_gt0"), bool(lo is not None and lo > 0))
            g.add(f"{fam}_frac_pos_in_unit:{name}",
                  isinstance(b.get("frac_pos"), float) and 0.0 <= b["frac_pos"] <= 1.0,
                  f"frac_pos={b.get('frac_pos')}")

        # B9 transition_margin_clean 必须为 False 且带 confound 说明（不得被写成干净）
        g.eq(f"transition_margin_clean_is_false:{name}",
             get_path(d, "Q2_load_bearing.transition_margin_clean"), False)
        g.add(f"transition_margin_confound_note_present:{name}",
              bool(get_path(d, "Q2_load_bearing.transition_margin_confound_note")),
              "必须保留 T-identity 冻结 z_t 的 confound 说明")

        # B10 全文递归有限性（不整枝，覆盖每一个浮点数）
        nf = walk_nonfinite(d)
        g.add(f"all_values_finite:{name}", not nf, f"非有限值路径={nf[:10]}")

    # B11 四份 evaluator commit 必须一致且非空
    uniq = sorted(set(commits.values()))
    g.eq("evaluator_commit_unique_across_q1q2", len(uniq), 1, f"取值={uniq}")
    ctx["evaluator_commit_q1q2"] = uniq[0] if len(uniq) == 1 else None
    return g


# ============================ Gate C：两份 Q3 极端态审计 ============================

# 协议目录内 8 个文件的 SHA-256（本轮只读复核）。其中 Q3 JSON 只绑定 5 个，
# MANIFEST.SHA256 列出 7 个（不含自身），磁盘上共 8 个 —— 三个数字都要如实报告。
Q3_PROTO_SHA = {
    "climatology_train.json":
        "0123a016",   # 前缀占位，脚本以实测值为准并记录全量
    "hotdry_manifest.json":
        "f8db1ccbb39120c78723d203655e506f5ac13790e11e59e4c6fbb96e5f2d09c7",
    "matched_normal_manifest.json":
        "84a09421ff5b43c5b5529a3e7e9a0b40e3e999c170f1cd365d0509c73e9c2ccf",
    "protocol.json":
        "570a0c36c3d1ceb83d0b2294fc7998b55443ae8a3ccc73f05f92c4e45a792ae5",
    "provenance.json":
        "d658211a2fe1832bd30e238eaa592541b33d935dd06cb7ee804510976fc3d0ea",
    "thresholds.json":
        "1c20cd71e6b30207aa6b1816607a6ba402e600b92abceb06a52bf8a1577fa790",
}
Q3_JSON_BOUND_FILES = ["hotdry_manifest.json", "matched_normal_manifest.json",
                       "protocol.json", "provenance.json", "thresholds.json"]
Q3_PROTO_COUNTS = {"on_disk": 8, "in_manifest": 7, "bound_by_result_json": 5}


def gate_c(ctx) -> Gate:
    g = Gate("C", "两份 Q3 结果：证据角色、配对数、协议绑定、CI 完整性与 sidecar 身份")

    # C1 协议目录：逐文件实测 SHA，与 MANIFEST.SHA256 对照，报告三个计数
    g.add("q3_protocol_dir_exists", Q3_PROTO.is_dir(), str(Q3_PROTO))
    disk = {}
    if Q3_PROTO.is_dir():
        for f in sorted(Q3_PROTO.iterdir()):
            if f.is_file():
                disk[f.name] = sha256_file(f)
        ctx["q3_protocol"] = {"dir": str(Q3_PROTO), "n_files_on_disk": len(disk),
                              "file_sha256": dict(disk)}
        g.eq("q3_protocol_n_files_on_disk", len(disk), Q3_PROTO_COUNTS["on_disk"])
        # 与本轮清点值逐一比对（climatology_train 只核前缀，其余核全量）
        for fn, want in Q3_PROTO_SHA.items():
            got = disk.get(fn)
            if want and len(want) == 64:
                g.eq(f"q3_protocol_sha:{fn}", got, want)
            else:
                g.add(f"q3_protocol_sha_prefix:{fn}",
                      isinstance(got, str) and got.startswith(want),
                      f"got={got} 期望前缀={want}")

        # C2 MANIFEST.SHA256：逐行解析并与磁盘实测值对照
        mf = Q3_PROTO / "MANIFEST.SHA256"
        if g.add("q3_manifest_exists", mf.is_file(), str(mf)):
            listed = {}
            bad = []
            for line in mf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 1)
                if len(parts) != 2 or len(parts[0]) != 64:
                    bad.append(line)
                    continue
                listed[parts[1].lstrip("*").strip()] = parts[0]
            g.add("q3_manifest_all_lines_parsed", not bad, f"无法解析的行={bad}")
            g.eq("q3_protocol_n_files_in_manifest", len(listed),
                 Q3_PROTO_COUNTS["in_manifest"])
            g.add("q3_manifest_excludes_itself", "MANIFEST.SHA256" not in listed,
                  "清单自身不应列入自身")
            mism = {k: (v, disk.get(k)) for k, v in listed.items() if disk.get(k) != v}
            g.add("q3_manifest_matches_disk", not mism, f"不一致={mism}")
            extra = sorted(set(disk) - set(listed) - {"MANIFEST.SHA256"})
            g.add("q3_manifest_covers_disk", not extra, f"磁盘多出未列入清单的文件={extra}")
            ctx["q3_protocol"]["n_files_in_manifest"] = len(listed)
            ctx["q3_protocol"]["manifest_sha256"] = disk.get("MANIFEST.SHA256")

        # C3 官方协议即 ground truth：protocol.json 的计数不得由模型输出反推
        pj = Q3_PROTO / "protocol.json"
        if g.add("q3_protocol_json_exists", pj.is_file(), str(pj)):
            proto = load_json(pj)
            counts = {k: find_key(proto, k) for k in
                      ("n_strict", "n_broad", "n_primary", "n_control_unique")}
            ctx["q3_protocol"]["counts"] = counts
            g.eq("protocol_n_primary_84", counts["n_primary"], 84)
            g.eq("protocol_n_broad_84", counts["n_broad"], 84)
            g.eq("protocol_n_strict_36", counts["n_strict"], 36)
            g.eq("protocol_n_control_unique_45", counts["n_control_unique"], 45)
            ctx["q3_protocol"]["config"] = find_key(proto, "config")
            ctx["q3_protocol"]["geometry"] = find_key(proto, "geometry")
        prov = Q3_PROTO / "provenance.json"
        if prov.is_file():
            pd = load_json(prov)
            ctx["q3_protocol"]["frozen_provenance"] = {
                k: find_key(pd, k) for k in
                ("git_commit", "git_dirty", "frozen_utc", "seed",
                 "n_train_used", "n_oodt_valid")}
            g.eq("q3_protocol_frozen_not_dirty", find_key(pd, "git_dirty"), False)
        th = Q3_PROTO / "thresholds.json"
        if th.is_file():
            ctx["q3_protocol"]["thresholds"] = load_json(th)

    # C4 逐份 Q3 结果
    for name in sorted(Q3_JOBS):
        cfg = JOBS[name]
        p = RUNS / name / Q3_FILE
        if not g.add(f"exists:{name}", p.is_file(), str(p)):
            continue
        d = load_json(p)
        ctx["raw"][name] = d

        # C4a 顶层契约
        g.eq(f"evidence_role:{name}", d.get("evidence_role"), "final")
        g.eq(f"n_pairs:{name}", d.get("n_pairs"), 84)
        g.eq(f"protocol_n_pairs:{name}", d.get("protocol_n_pairs"), 84)
        g.eq(f"n_extreme:{name}", d.get("n_extreme"), 84)
        g.eq(f"n_control_unique:{name}", d.get("n_control_unique"), 45)
        g.eq(f"n_boot:{name}", d.get("n_boot"), 10000)
        g.eq(f"limit_is_none:{name}", d.get("limit"), None)
        g.add(f"note_present:{name}", bool(d.get("note")), str(d.get("note"))[:80])
        g.add(f"protocol_dir_is_official:{name}",
              Path(str(d.get("protocol_dir"))).resolve() == Q3_PROTO.resolve(),
              f"记录={d.get('protocol_dir')} 官方={Q3_PROTO}")

        # C4b protocol_sha 精确绑定 5 个文件，且每个都与磁盘实测一致
        psha = d.get("protocol_sha", {})
        g.eq(f"protocol_sha_binds_five:{name}", sorted(psha), sorted(Q3_JSON_BOUND_FILES))
        bad = {k: (v, disk.get(k)) for k, v in psha.items() if disk.get(k) != v}
        g.add(f"protocol_sha_matches_disk:{name}", not bad, f"不一致={bad}")

        # C4c schema gap：Q3 JSON 既无顶层 checkpoint 也无 evaluator_commit
        #     身份只能由 run 目录 + launch shard + 运行日志共同确定（sidecar-bound）
        want_sha = CKPT[cfg["ckpt"]]["file_sha256"]
        g.add(f"q3_json_has_no_native_checkpoint:{name}",
              "checkpoint" not in d and find_key(d, "checkpoint_sha256") is None,
              "已确认的 schema 缺口：Q3 结果 JSON 不记录 checkpoint SHA")
        g.add(f"q3_json_has_no_evaluator_commit:{name}",
              find_key(d, "evaluator_commit") is None,
              "已确认的 schema 缺口：Q3 结果 JSON 不记录 evaluator commit")
        g.eq(f"q3_checkpoint_via_shard:{name}",
             ctx["launch"].get(name, {}).get("checkpoint_sha256"), want_sha)
        logp = ctx["launch"].get(name, {}).get("log")
        if logp and Path(logp).is_file():
            txt = Path(logp).read_text(encoding="utf-8", errors="replace")
            # 实测：两份 Q3 运行日志都不含任何 64 位十六进制串，即日志同样不记录
            # checkpoint SHA。这里把该缺口正面断言下来，而不是假装日志能自证身份。
            g.eq(f"q3_log_lacks_checkpoint_sha:{name}",
                 sorted(set(re.findall(r"[0-9a-f]{64}", txt))), [],
                 f"已确认缺口：运行日志不含 checkpoint SHA（{logp}）")
            # 日志唯一能提供的绑定是它写出的结果路径，含 run 目录名与结果文件名
            g.add(f"q3_log_binds_result_path:{name}",
                  f"runs/{name}/{Q3_FILE}" in txt.replace("\\", "/"),
                  "日志 [audit] wrote 行指向本 job 的结果文件")
            g.add(f"q3_run_dir_encodes_ckpt_role:{name}",
                  Q3_DIRTAG[cfg["ckpt"]] in name,
                  f"run 目录名含 checkpoint 角色标记 {Q3_DIRTAG[cfg['ckpt']]}")
            # 日志能核对的六项事实 + 三个判定，逐项与 JSON 交叉比对
            tok: dict[str, str] = {}
            for k, v in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s|]+)", txt):
                tok.setdefault(k, v)
            DFP = "models.exclusive.q3_donor_fidelity"
            for lk, jv in (
                    ("weather_in_base", get_path(d, "models.exclusive.weather_in_base")),
                    ("n_extreme", d.get("n_extreme")),
                    ("n_control_unique", d.get("n_control_unique")),
                    ("n_pairs", d.get("n_pairs")),
                    ("role", d.get("evidence_role")),
                    ("uf_differs_all", get_path(d, f"{DFP}.uf_differs_all_pairs")),
                    ("endpoint", get_path(d, f"{DFP}.endpoint_fidelity_status")),
                    ("enhancement", get_path(d, f"{DFP}.hotdry_enhancement_status")),
                    ("raw", get_path(d, f"{DFP}.raw_status")),
                    ("overall", get_path(d, f"{DFP}.overall_status"))):
                g.eq(f"q3_log_json_agree:{name}:{lk}", tok.get(lk), str(jv))
            ctx["q3_sidecar_identity"][name] = {
                "checkpoint_sha256": want_sha,
                "proof": "sidecar",
                "sources": ["launch_record_shard", "run_dir_name",
                            "runner_log(result_path+metrics only)"],
                "log": logp,
                "known_gaps": [
                    "Q3 结果 JSON 不含顶层 checkpoint 字段与 checkpoint SHA",
                    "Q3 结果 JSON 不含 evaluator_commit",
                    "Q3 运行日志不含 checkpoint SHA（实测 0 个 64-hex 串）"],
                "identity_basis": "launch shard 记录的 checkpoint_sha256 + run 目录名角色标记；"
                                  "日志只能证明结果路径与指标一致，不能独立证明权重身份"}
        else:
            g.add(f"q3_log_available:{name}", False, str(logp))

        # C4d 指标完整性：聚合三臂 + 端点保真两组对照 + 三个 bootstrap 家族
        EX = "models.exclusive"
        req = [f"{EX}.q3_aggregate_extreme.{arm}.{m}"
               for arm in ("actual", "donor", "mean") for m in ("R2", "rmse", "nse")]
        fams = ("paired_bootstrap", "geo_cluster_bootstrap",
                "reused_control_cluster_bootstrap")
        contrasts = ("extreme_actual_vs_donor", "extreme_actual_vs_mean")
        for c in contrasts:
            req.append(f"{EX}.q3_donor_fidelity.endpoint_fidelity.{c}.delta_loss_mean")
            for fam in fams:
                req += [f"{EX}.q3_donor_fidelity.endpoint_fidelity.{c}.{fam}.{m}"
                        for m in ("mean", "ci_low", "ci_high", "n")]
        for c in ("extreme_actual_vs_donor", "extreme_actual_vs_mean",
                  "normal_actual_vs_donor", "normal_actual_vs_mean"):
            req += [f"{EX}.q3_donor_fidelity.response_magnitude.{c}.{m}"
                    for m in ("mean", "n")]
        for eff in ("dloss_donor", "dloss_mean", "resp_donor", "resp_mean"):
            for fam in fams:
                req += [f"{EX}.q3_donor_fidelity.interaction_hotdry_minus_normal."
                        f"{eff}.{fam}.{m}" for m in ("mean", "ci_low", "ci_high")]
        missq3 = [k for k in req if not isinstance(get_path(d, k), (int, float))]
        g.add(f"q3_metric_completeness:{name}", not missq3, f"缺失或非数值={missq3}")

        # C4e 每个 bootstrap 家族的 n / n_clusters / CI 次序 / 显著性判定
        for c in contrasts:
            base = f"{EX}.q3_donor_fidelity.endpoint_fidelity.{c}"
            for fam, ncl in (("paired_bootstrap", None),
                             ("geo_cluster_bootstrap", 31),
                             ("reused_control_cluster_bootstrap", 45)):
                b = get_path(d, f"{base}.{fam}", {})
                g.eq(f"{c}.{fam}.n:{name}", b.get("n"), 84)
                if ncl is not None:
                    g.eq(f"{c}.{fam}.n_clusters:{name}", b.get("n_clusters"), ncl)
                lo, hi, mu = b.get("ci_low"), b.get("ci_high"), b.get("mean")
                g.add(f"{c}.{fam}.ci_ordered:{name}",
                      all(isinstance(x, float) for x in (lo, hi, mu)) and lo <= mu <= hi,
                      f"ci=[{lo}, {hi}] mean={mu}")
                g.eq(f"{c}.{fam}.significance_consistent:{name}",
                     b.get("significant_gt0"), bool(lo is not None and lo > 0))
                g.close(f"{c}.{fam}.mean_matches_point:{name}", mu,
                        get_path(d, f"{base}.delta_loss_mean"), 1e-12)
            g.add(f"{c}.paired_frac_pos_in_unit:{name}",
                  0.0 <= get_path(d, f"{base}.paired_bootstrap.frac_pos", -1) <= 1.0,
                  f"frac_pos={get_path(d, f'{base}.paired_bootstrap.frac_pos')}")

        # C4f 判定字段：不得被弱化，也不得被夸大
        DF = f"{EX}.q3_donor_fidelity"
        g.eq(f"endpoint_fidelity_status:{name}",
             get_path(d, f"{DF}.endpoint_fidelity_status"), "PASS")
        g.eq(f"hotdry_enhancement_status:{name}",
             get_path(d, f"{DF}.hotdry_enhancement_status"), "FAIL")
        g.eq(f"primary_criterion:{name}", get_path(d, f"{DF}.primary_criterion"),
             "geo_cluster_bootstrap_ci_low_gt0")
        g.eq(f"raw_status:{name}", get_path(d, f"{DF}.raw_status"),
             "Q3_RESPONSE_FIDELITY_ONLY")
        g.eq(f"overall_status:{name}", get_path(d, f"{DF}.overall_status"),
             "Q3_RESPONSE_FIDELITY_ONLY")
        g.eq(f"df_evidence_role:{name}", get_path(d, f"{DF}.evidence_role"), "final")
        g.eq(f"df_n_pairs:{name}", get_path(d, f"{DF}.n_pairs"), 84)
        g.eq(f"uf_differs_all_pairs:{name}", get_path(d, f"{DF}.uf_differs_all_pairs"), True)
        g.eq(f"df_weather_in_base:{name}", get_path(d, f"{DF}.weather_in_base"), False)
        g.eq(f"diagnostic_only:{name}", get_path(d, f"{EX}.diagnostic_only"), False)
        g.eq(f"models_n_extreme:{name}", get_path(d, f"{EX}.n_extreme"), 84)
        g.eq(f"models_n_control:{name}", get_path(d, f"{EX}.n_control"), 45)

        # C4g 判定与数值自洽：PASS 必须真的满足 actual 优于 donor 与 mean
        aR2 = get_path(d, f"{EX}.q3_aggregate_extreme.actual.R2")
        dR2 = get_path(d, f"{EX}.q3_aggregate_extreme.donor.R2")
        mR2 = get_path(d, f"{EX}.q3_aggregate_extreme.mean.R2")
        g.add(f"endpoint_pass_is_earned:{name}",
              all(isinstance(x, float) for x in (aR2, dR2, mR2))
              and aR2 > dR2 and aR2 > mR2,
              f"R2 actual={aR2} donor={dR2} mean={mR2}（PASS 要求 actual 同时优于两者）")
        ilo = get_path(d, f"{DF}.interaction_hotdry_minus_normal."
                          f"dloss_donor.geo_cluster_bootstrap.ci_low")
        g.add(f"hotdry_fail_is_earned:{name}",
              isinstance(ilo, float) and ilo <= 0.0,
              f"主判据 geo_cluster ci_low={ilo} ≤ 0，故 hotdry 增强判 FAIL 与数值一致")

        # C4h 结构计数：per_cube_effects = n_extreme + n_control_unique；donor_rows = n_pairs
        pce = get_path(d, f"{EX}.per_cube_effects")
        rows = get_path(d, f"{EX}.q3_donor_rows")
        g.eq(f"per_cube_effects_count:{name}",
             len(pce) if isinstance(pce, dict) else None, 84 + 45)
        g.eq(f"q3_donor_rows_count:{name}",
             len(rows) if isinstance(rows, list) else None, 84)

        # C4i stratum_accuracy 结构：两个 cohort，臂集合彼此一致
        sa = get_path(d, f"{EX}.stratum_accuracy")
        if g.add(f"stratum_accuracy_is_dict:{name}", isinstance(sa, dict), type(sa).__name__):
            g.eq(f"stratum_accuracy_cohorts:{name}", sorted(sa),
                 ["hotdry", "matched_normal"])
            arms = {c: sorted(v) if isinstance(v, dict) else None for c, v in sa.items()}
            vals = list(arms.values())
            g.add(f"stratum_accuracy_arms_consistent:{name}",
                  len(vals) == 2 and vals[0] == vals[1] and vals[0] is not None,
                  f"两 cohort 的臂集合={arms}")
            # 实测臂集合为 4 个（不是 3 个）：full 之外还有三条消融臂。
            # 断言精确名单而不是只断言个数，个数对了但名字变了同样必须失败。
            g.eq(f"stratum_accuracy_arms:{name}",
                 vals[0] if vals and vals[0] else None,
                 ["closure_zero_scale", "full", "t_identity", "weather_in_base"])
            ctx["q3_stratum_arms"][name] = arms

        # C4j 全文递归有限性（含 per_cube_effects 与 q3_donor_rows，不整枝）
        nf = walk_nonfinite(d)
        g.add(f"all_values_finite:{name}", not nf, f"非有限值路径={nf[:10]}")
    return g


# ==================== Gate D：历史复现（57 个正式指标，排除元数据） ====================

def gate_d(ctx) -> Gate:
    g = Gate("D", "11,904 复现历史参考：57 个正式指标逐项比对")

    got_sha = sha256_file(HIST_REF)
    g.add("hist_ref_exists", HIST_REF.is_file(), str(HIST_REF))
    # 源变更即 fail-closed：历史参考是冻结证据，SHA 不符时不得继续封账
    g.eq("hist_ref_sha256_unchanged", got_sha, HIST_REF_SHA,
         f"got={got_sha} want={HIST_REF_SHA}（不一致说明冻结参考被改动，必须停止）")
    if not HIST_REF.is_file() or got_sha != HIST_REF_SHA:
        return g

    ref = load_json(HIST_REF)
    formal = {k: v for k, v in ref.items() if not k.startswith("_")}
    meta_keys = sorted(k for k in ref if k.startswith("_"))
    g.eq("formal_metric_count_is_57", len(formal), 57,
         f"正式指标键={len(formal)}，元数据键={len(meta_keys)}：{meta_keys}")
    g.add("metadata_keys_excluded", all(k.startswith("_") for k in meta_keys),
          f"排除的元数据键={meta_keys}")

    default_tol = ref.get("_tolerance", 1e-6)
    per_pattern = ref.get("_tolerances", {})

    def tol_for(path: str) -> float:
        """最长匹配优先：`_tolerances` 的模式若为 path 的子串则命中，取最长者。"""
        best, best_len = default_tol, -1
        for pat, t in per_pattern.items():
            if pat in path and len(pat) > best_len:
                best, best_len = t, len(pat)
        return best

    ctx["hist_ref"] = {
        "path": str(HIST_REF), "sha256": got_sha, "n_formal": len(formal),
        "metadata_keys": meta_keys, "default_tolerance": default_tol,
        "per_pattern_tolerances": per_pattern,
        "tolerance_rationale": ref.get("_tolerance_rationale"),
        "note": ref.get("_note"), "sources": ref.get("_sources"),
        "generated_at": ref.get("_generated_at"), "generated_by": ref.get("_generated_by"),
    }

    rows, n_exact, n_pass = [], 0, 0
    for key in sorted(formal):
        want = formal[key]
        job, _, dotted = key.partition(":")
        g.add(f"ref_key_job_known:{key}", job in JOBS and JOBS[job]["ckpt"] == "boundary11904",
              f"历史参考键必须指向 11,904 作业，实际 job={job}")
        d = ctx["raw"].get(job)
        got = get_path(d, dotted) if d is not None else None
        tol = tol_for(dotted)
        ok = (isinstance(got, (int, float)) and not isinstance(got, bool)
              and math.isfinite(got) and abs(float(got) - float(want)) <= tol)
        delta = (float(got) - float(want)) if isinstance(got, (int, float)) else None
        exact = delta == 0.0
        n_exact += 1 if exact else 0
        n_pass += 1 if ok else 0
        rows.append({"key": key, "job": job, "path": dotted, "reference": want,
                     "reproduced": got, "delta": delta, "tolerance": tol,
                     "exact": exact, "ok": ok})
        g.add(f"reproduce:{key}", ok,
              f"ref={want!r} got={got!r} Δ={'n/a' if delta is None else format(delta, '.3e')} tol={tol:g}")
    g.eq("reproduction_pass_count", n_pass, 57, f"通过 {n_pass}/57，逐位相同 {n_exact}/57")
    ctx["reproduction"] = {"n_formal": len(formal), "n_pass": n_pass,
                          "n_bit_exact": n_exact, "rows": rows}
    return g


# ============================ Gate E：完整性与口径边界 ============================

def gate_e(ctx) -> Gate:
    g = Gate("E", "完整性：无 smoke/partial/中断混入、无幽灵结果、ground truth 归属、口径边界")

    # E1 六个正式作业目录内不得出现中断或 partial 标记
    for name in sorted(JOBS):
        d = RUNS / name
        marks = sorted(f.name for f in d.iterdir()
                       if f.is_file() and ("INTERRUPTED" in f.name
                                           or "PARTIAL" in f.name.upper()
                                           or f.name.endswith(".partial")))
        g.add(f"no_interrupt_marker:{name}", not marks, f"发现标记文件={marks}")
        g.add(f"no_smoke_marker:{name}", "smoke" not in name.lower(),
              "正式作业名不得含 smoke")

    # E2 smoke / selftest 目录如存在，必须登记且不得进入 allowlist
    for base in (ATTEMPT, PARENT):
        for sub in ("smoke", "selftest"):
            p = base / sub
            if p.is_dir():
                kids = sorted(x.name for x in p.iterdir())
                ctx["excluded"].append({
                    "path": str(p), "children": kids,
                    "reason": f"{sub} 产物：永久保留为审计证据，绝不进入正式结果集"})
                g.add(f"excluded_not_in_allowlist:{p.name}@{base.name}",
                      not (set(kids) & set(JOBS)),
                      f"{p} 的子项与正式作业名无交集")

    # E3 20260818 中断尝试必须登记（三份 INTERRUPTED.json + NOT_READY 验收 + watcher）
    if PARENT.is_dir():
        pruns = PARENT / "runs"
        inter = sorted(str(f.relative_to(PARENT)) for f in pruns.rglob("INTERRUPTED.json")
                       ) if pruns.is_dir() else []
        rep = PARENT / "e0_acceptance_report.json"
        wat = PARENT / "e0_watcher_state.json"
        rec = PARENT / "e0_launch_record.json"
        entry = {"attempt": PARENT.name, "interrupted_markers": inter,
                 "n_interrupted": len(inter)}
        if rep.is_file():
            rd = load_json(rep)
            entry["acceptance_status"] = rd.get("status")
            entry["acceptance_sha256"] = sha256_file(rep)
            g.eq("interrupted_attempt_status_not_ready", rd.get("status"), "NOT_READY")
        if wat.is_file():
            wd = load_json(wat)
            entry["watcher_state"] = wd.get("state") or find_key(wd, "state")
            entry["watcher_polls"] = find_key(wd, "polls")
            entry["jobs_launched"] = find_key(wd, "jobs_launched")
        if rec.is_file():
            rj = load_json(rec)
            entry["launch_record_n_jobs"] = len(rj.get("jobs", []))
            entry["yielded_to"] = rj.get("yielded_to")
        ctx["interrupted_attempt"] = entry
        g.eq("interrupted_attempt_has_three_markers", len(inter), 3, f"标记={inter}")
        g.add("interrupted_attempt_preserved", PARENT.is_dir(),
              f"{PARENT} 作为审计证据保留，未被删除或覆盖")

    # E4 无幽灵结果：结果 ↔ 启动记录必须双向一一对应
    launched = set(ctx["launch"])
    with_result = {n for n in JOBS
                   if (RUNS / n / (Q1Q2_FILE if JOBS[n]["kind"] == "q1q2" else Q3_FILE)).is_file()}
    g.eq("every_result_has_launch_record", sorted(with_result - launched), [])
    g.eq("every_launch_record_has_result", sorted(launched - with_result), [])
    g.eq("result_set_equals_allowlist", sorted(with_result), sorted(JOBS))

    # E5 ground truth 归属：Q1/Q2 绑冻结数据清单，Q3 绑冻结协议，且协议先于评测冻结
    for key, (mp, msha, mn) in MANIFESTS.items():
        got = sha256_file(mp)
        g.eq(f"frozen_manifest_sha:{key}", got, msha, f"{mp}")
        if mp.is_file():
            mj = load_json(mp)
            files = mj if isinstance(mj, list) else (find_key(mj, "files") or [])
            g.eq(f"frozen_manifest_count:{key}", len(files), mn)
    fz = (ctx.get("q3_protocol", {}).get("frozen_provenance") or {}).get("frozen_utc")
    starts = [j.get("started_utc") for j in ctx["launch"].values() if j.get("started_utc")]
    if fz and starts:
        try:
            fzt = datetime.fromisoformat(str(fz).replace("Z", "+00:00"))
            e0 = min(datetime.fromisoformat(s.replace("Z", "+00:00")) for s in starts)
            days = (e0 - fzt).total_seconds() / 86400.0
            g.add("q3_protocol_frozen_before_eval", days > 0,
                  f"协议冻结 {fz}，最早评测启动 {min(starts)}，早于评测 {days:.1f} 天")
            ctx["ground_truth"] = {"q3_protocol_frozen_utc": fz,
                                   "earliest_eval_start_utc": min(starts),
                                   "frozen_lead_days": round(days, 2)}
        except ValueError as e:
            g.add("q3_protocol_frozen_before_eval", False, f"时间解析失败：{e}")

    # E6 不得以模型输出反向归一化：阈值与配对数只能来自冻结协议文件
    th = ctx.get("q3_protocol", {}).get("thresholds")
    g.add("q3_thresholds_come_from_frozen_file", isinstance(th, dict) and bool(th),
          "hot/dry 阈值取自 thresholds.json（冻结），不由本轮结果反推")
    pc = ctx.get("q3_protocol", {}).get("counts", {})
    for name in Q3_JOBS:
        d = ctx["raw"].get(name) or {}
        g.eq(f"result_counts_follow_protocol:{name}",
             [d.get("n_extreme"), d.get("n_control_unique"), d.get("n_pairs")],
             [pc.get("n_primary"), pc.get("n_control_unique"), pc.get("n_primary")],
             f"结果计数必须等于协议计数 n_primary={pc.get('n_primary')} "
             f"n_control_unique={pc.get('n_control_unique')}")
    for name in Q1Q2_JOBS:
        d = ctx["raw"].get(name) or {}
        split = JOBS[name]["split"]
        g.eq(f"n_targets_follows_frozen_manifest:{name}",
             get_path(d, "provenance.n_targets"), MANIFESTS[split][2])

    # E7 口径边界：三份 checkpoint 文件身份互不相同
    shas = {r: m["file_sha256"] for r, m in CKPT.items()}
    g.eq("three_checkpoint_file_shas_distinct", len(set(shas.values())), 3, f"{shas}")

    # E7a 「张量值一致」只适用于 verified 14,880 与历史 14,880，绝不适用于 11,904
    notes = " ".join(ctx["registry_entries"].get("verified14880", {})
                     .get("provenance_notes", []) or [])
    g.add("value_identity_scoped_to_14880_pair",
          M9_EXPECT["value_digest_16hex"] in notes and "historical-full14880" in notes,
          "registry provenance_notes 明确：值一致性只在 verified 与历史 14,880 之间成立")
    g.add("file_identity_explicitly_not_conflated",
          ("must not be conflated" in notes) or ("独立" in notes) or ("differs" in notes),
          "同一条 note 同时声明文件身份不同，二者不得混为一谈")
    g.add("registry_warns_against_relabelling",
          "must NOT be relabelled" in notes or "must not be relabelled" in notes,
          "registry 明确禁止把 11,904 的历史数字改标为 14,880")
    g.add("hist_ref_note_warns_against_relabelling",
          "11,904" in str(ctx.get("hist_ref", {}).get("note", "")),
          f"历史参考 _note={str(ctx.get('hist_ref', {}).get('note'))[:90]}")

    # E7b 正向证据：11,904 与 14,880 在同一 split 上结果不同 => 不是同一模型状态
    for split, (a, b) in {"val": ("gpu3_legacy11904_val_q1q2", "gpu0_v14880_val_q1q2"),
                          "oodt": ("gpu4_legacy11904_oodt_q1q2",
                                   "gpu1_v14880_oodt_q1q2")}.items():
        ra = get_path(ctx["raw"].get(a), "Q1_forecast.full.R2")
        rb = get_path(ctx["raw"].get(b), "Q1_forecast.full.R2")
        g.add(f"11904_and_14880_differ_on:{split}",
              isinstance(ra, float) and isinstance(rb, float) and ra != rb,
              f"11904 R2={ra} vs 14880 R2={rb}（数值不同，二者模型状态不可等同）")

    # E7c Q3 口径：只支持「响应保真」，不得表述为极端态整体通过
    for name in Q3_JOBS:
        st = get_path(ctx["raw"].get(name),
                      "models.exclusive.q3_donor_fidelity.overall_status")
        g.eq(f"q3_claim_scope:{name}", st, "Q3_RESPONSE_FIDELITY_ONLY")

    # E8 A03 曾出现的 Q2 数字在任何一手结果中都不存在（程序化确证该批数字系臆造）
    fabricated = [0.556762, 0.556617, 0.556546, 0.484868,
                  0.012454, 0.013196, 0.012587, 0.012732]
    allvals = []
    for d in ctx["raw"].values():
        allvals += [v for v in flatten(d, skip=("per_cube_effects", "q3_donor_rows")).values()
                    if isinstance(v, float)]
    hits = {f: [v for v in allvals if abs(v - f) < 5e-7] for f in fabricated}
    hit_any = {k: v for k, v in hits.items() if v}
    g.add("a03_stray_q2_values_absent_from_all_raw", not hit_any,
          f"在六份一手结果中命中的臆造值={hit_any}（应为空，证明这批数字无任何工件来源）")
    ctx["corrected_defects"].append({
        "defect": "A03 v2 的 Q2 对照表数字无来源",
        "values": fabricated,
        "evidence": "对六份一手结果全部浮点值做 |Δ|<5e-7 搜索，命中集合为空",
        "resolution": "v3 一律从 raw JSON 重新推导 Q2 三臂与官方 Δ"})
    return g


# ==================== Gate F：sanity anchor 与训练侧记录交叉核对 ====================

def gate_f(ctx) -> Gate:
    g = Gate("F", "sanity anchor、M9 验收、参数审计与 evaluator 源码指纹交叉核对")

    # F1 用户下发的 sanity anchor：不一致即停止封账，禁止改数字迁就
    for job, path, want in ANCHORS:
        got = get_path(ctx["raw"].get(job), path)
        g.close(f"anchor:{job}:{path}", got, want, ANCHOR_TOL)
    ctx["anchors"] = [{"job": j, "path": p, "expected": w,
                       "observed": get_path(ctx["raw"].get(j), p)}
                      for j, p, w in ANCHORS]

    # F2 M9 验收报告
    g.add("m9_report_exists", M9_REPORT.is_file(), str(M9_REPORT))
    if M9_REPORT.is_file():
        m9 = load_json(M9_REPORT)
        lin = m9.get("lineage", {})
        g.eq("m9_accepted", m9.get("accepted"), M9_EXPECT["accepted"])
        g.eq("m9_n_checks_31", m9.get("n_checks"), M9_EXPECT["n_checks"])
        g.eq("m9_all_checks_ok",
             sum(1 for c in m9.get("checks", []) if c.get("ok")), M9_EXPECT["n_checks"])
        g.eq("m9_final_step", m9.get("final_step"), M9_EXPECT["final_step"])
        g.eq("m9_stage", m9.get("stage"), M9_EXPECT["stage"])
        g.eq("m9_checkpoint_last_sha256", m9.get("checkpoint_last_sha256"),
             M9_EXPECT["checkpoint_last_sha256"])
        g.eq("m9_parent_file_sha256", lin.get("parent_file_sha256"),
             M9_EXPECT["parent_file_sha256"])
        g.eq("m9_parent_step", lin.get("parent_step"), M9_EXPECT["parent_step"])
        g.eq("m9_parent_stage_recorded", lin.get("parent_stage_recorded"),
             M9_EXPECT["parent_stage_recorded"])
        g.eq("m9_resume_stage_applied", lin.get("resume_stage_applied"),
             M9_EXPECT["resume_stage_applied"])
        g.eq("m9_parent_b4_state_sha256", lin.get("parent_b4_state_sha256"),
             M9_EXPECT["parent_b4_state_sha256"])
        g.eq("m9_resumed", lin.get("resumed"), True)
        cks = {c["name"]: c for c in m9.get("checks", [])}
        be = cks.get("historical_bit_exact", {})
        g.add("m9_historical_bit_exact_ok", be.get("ok") is True, be.get("detail", ""))
        det = str(be.get("detail", ""))
        g.add("m9_value_digest_matches_both_sides",
              det.count(M9_EXPECT["value_digest_16hex"]) >= 2
              and "keys_equal=True" in det and "max_abs_diff=0.000e+00" in det,
              f"255 张量值摘要两侧一致：{det}")
        g.add("m9_tensor_count_255", f"{M9_EXPECT['n_model_tensors']} tensors" in det,
              det)
        g.add("m9_loss_log_2976",
              f"{M9_EXPECT['n_updates']} entries" in
              str(cks.get("loss_log_count_2976", {}).get("detail", "")),
              cks.get("loss_log_count_2976", {}).get("detail", ""))
        for nm in ("all_updates_stage_3", "trainer_asserted_teacher_unchanged",
                   "trainable_q_count_12", "optimizer_state_present",
                   "scheduler_last_epoch_14880", "b4_state_dict_present",
                   "no_duplicate_boundary80", "loss_log_first_step_11905",
                   "loss_log_last_step_14880"):
            g.add(f"m9_check:{nm}", cks.get(nm, {}).get("ok") is True,
                  cks.get(nm, {}).get("detail", "缺失"))
        ctx["m9"] = {"path": str(M9_REPORT), "sha256": sha256_file(M9_REPORT),
                     "accepted": m9.get("accepted"), "n_checks": m9.get("n_checks"),
                     "final_step": m9.get("final_step"), "stage": m9.get("stage"),
                     "best_val": m9.get("best_val"), "lineage": lin,
                     "historical_bit_exact_detail": det,
                     "value_digest_16hex": M9_EXPECT["value_digest_16hex"]}

    # F3 参数审计：49 行、全部 consistent、算术自洽、stage 语义如实记录
    g.add("param_audit_exists", PARAM_AUDIT.is_file(), str(PARAM_AUDIT))
    if PARAM_AUDIT.is_file():
        pa = load_json(PARAM_AUDIT)
        g.eq("param_audit_n_rows_49", pa.get("n_rows"), 49)
        g.eq("param_audit_rows_len_49", len(pa.get("rows", [])), 49)
        g.eq("param_audit_all_consistent", pa.get("all_consistent"), True)
        g.eq("param_audit_no_inconsistent", pa.get("inconsistent_parameters"), [])
        g.eq("param_audit_no_missing_runbook_literal",
             pa.get("runbook_literals_missing"), [])
        bad = [r["parameter"] for r in pa.get("rows", []) if r.get("consistent") is not True]
        g.add("param_audit_every_row_consistent", not bad, f"不一致行={bad}")
        frozen = {r["parameter"]: r.get("frozen_value_for_resume")
                  for r in pa.get("rows", [])}
        ctx["hyperparams"] = frozen
        ctx["param_audit"] = {
            "path": str(PARAM_AUDIT), "sha256": sha256_file(PARAM_AUDIT),
            "n_rows": pa.get("n_rows"), "all_consistent": pa.get("all_consistent"),
            "arithmetic_self_consistency": pa.get("arithmetic_self_consistency"),
            "stage_boundary_semantics": pa.get("stage_boundary_semantics"),
            "sources": pa.get("sources"),
            "witness_columns": ["checkpoint", "runbook", "train_log"]}
        EXPECT_HP = {
            "per_gpu_batch": 8, "global_batch": 64, "world_size": 8, "accum": 1,
            "max_epochs": 40, "total_steps": 14880, "updates_per_epoch": 372,
            "boundary80": 11904, "branch_lr": 3e-05, "q_lr_scale": 0.033,
            "weight_decay": 0.0, "grad_clip": 1.0, "lr_warmup_steps": 300,
            "unfreeze_q_prefixes": "core.blocks.2.", "seed": 42, "state_dim": 256,
            "val_interval": 1000, "ckpt_interval": 2000, "deterministic": False,
            "alpha": 1.0, "loss_weights.gt": 1.0, "loss_weights.kd": 0.5,
            "lambda_state@11904": 0.01, "resume.step": 11904, "resume.epoch": 31,
            "resume.micro_in_epoch": 372, "resume.stage": 2,
            "resume.best_val": 0.31334985432787643,
        }
        for k, want in EXPECT_HP.items():
            g.eq(f"hyperparam:{k}", frozen.get(k), want)
        g.add("hyperparams_no_placeholder_left",
              all(frozen.get(k) is not None for k in EXPECT_HP),
              "A03 的训练超参必须全部有值，不得残留 <待补充>")
        ar = pa.get("arithmetic_self_consistency", {})
        g.eq("arith_2976_updates", ar.get("total_steps_minus_parent_step"), 2976)
        g.eq("arith_remaining_updates", ar.get("remaining_updates"), 2976)
        g.eq("arith_ok", ar.get("ok"), True)
        g.eq("boundary80_formula_holds", int(0.80 * 14880), 11904)
        sb = pa.get("stage_boundary_semantics", {})
        g.eq("stage_at_11904_is_3", sb.get("stage_at_11904"), 3)
        g.eq("recorded_stage_in_parent_is_2", sb.get("recorded_stage_in_parent"), 2)
        g.add("stage_discrepancy_documented",
              sb.get("stage_at_11904") != sb.get("recorded_stage_in_parent")
              and bool(sb.get("evidence")),
              "边界 checkpoint 记录 stage=2 而下一次更新属 stage=3，须如实说明而非抹平")

    # F4 state_sha_check：warm-start / teacher / q_projector 身份
    if g.add("state_sha_check_exists", STATE_SHA_CHECK.is_file(), str(STATE_SHA_CHECK)):
        sc = load_json(STATE_SHA_CHECK)
        for k in ("all_match", "q_projector_match", "student_init_match",
                  "teacher_match", "teacher_load_exact", "warm_start_exact"):
            g.eq(f"state_sha_check:{k}", sc.get(k), True)
        for k in ("teacher_load_missing", "teacher_load_unexpected",
                  "warm_start_missing", "warm_start_unexpected"):
            g.eq(f"state_sha_check:{k}", sc.get(k), 0)
        g.eq("state_sha_check_parent_b4_state", sc.get("parent_b4_state_sha256"),
             M9_EXPECT["parent_b4_state_sha256"])
        g.eq("state_sha_check_parent_step", sc.get("parent_step"), 11904)
        g.eq("state_sha_check_parent_stage", sc.get("parent_stage"), 2)
        for k in ("q_projector_init_sha256", "student_init_sha256", "teacher_sha256"):
            g.eq(f"state_sha_check_matches_expected:{k}",
                 sc.get(k), sc.get(f"{k}_expected"))
        ctx["state_sha_check"] = {"path": str(STATE_SHA_CHECK),
                                  "sha256": sha256_file(STATE_SHA_CHECK), **sc}

    # F5 evaluator 源码指纹：实测必须等于冻结 manifest 记录值
    for rel, want in EVALUATORS.items():
        got = sha256_file(TS_ROOT / rel)
        g.eq(f"evaluator_source_sha:{rel}", got, want, f"{TS_ROOT / rel}")
        ctx["evaluator_sources"][rel] = {"path": str(TS_ROOT / rel), "sha256": got,
                                         "frozen_expected": want}

    # F6 训练 manifest 与评测冻结 manifest 必须区分，禁止在 A03 里混用
    hp = ctx.get("hyperparams", {})
    train_shas = {k: hp.get(k) for k in
                  ("sha.train_manifest_sha256", "sha.val_manifest_sha256")}
    eval_shas = {k: v[1] for k, v in MANIFESTS.items()}
    overlap = set(x for x in train_shas.values() if x) & set(eval_shas.values())
    g.add("train_manifests_distinct_from_eval_manifests", not overlap,
          f"训练侧 {train_shas} vs 评测侧 {eval_shas}；交集={overlap}（必须为空）")
    ctx["manifest_disambiguation"] = {
        "training_side": train_shas, "evaluation_side": eval_shas,
        "note": "训练用 train/val manifest 与评测用 val_952 / oodt_1904 冻结清单是不同文件，"
                "A03 中不得互相替代"}

    # F7 本轮 CPU 封账节点与 GPU 执行节点必须分别记录，不得互相覆盖
    g.add("cpu_and_gpu_nodes_recorded",
          bool(ctx["env"]["closeout_hostname"]) and bool(ctx["env"]["gpu_exec_hostname"]),
          f"CPU 封账节点={ctx['env']['closeout_hostname']}，"
          f"GPU 执行节点（取自 attempt_manifest 记录）={ctx['env']['gpu_exec_hostname']}")
    g.eq("cpu_only_env_enforced", os.environ.get("CUDA_VISIBLE_DEVICES"), "",
         f"CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES')!r}（必须为空串）")
    return g


# ==================== 对照表：脚本生成，Δ = 14,880 − 11,904 ====================

PAIRS = {
    "Q1Q2_val":  ("gpu3_legacy11904_val_q1q2", "gpu0_v14880_val_q1q2"),
    "Q1Q2_oodt": ("gpu4_legacy11904_oodt_q1q2", "gpu1_v14880_oodt_q1q2"),
    "Q3_oodt":   ("gpu5_legacy11904_oodt_q3", "gpu2_v14880_oodt_q3"),
}
FLATTEN_SKIP = ("per_cube_effects", "q3_donor_rows", "command")


def diff_rows(a, b, skip=FLATTEN_SKIP):
    """逐键对照两份 JSON。Δ 只对数值给出；非数值只记录两侧取值与是否相同。"""
    fa, fb = flatten(a, skip=skip), flatten(b, skip=skip)
    rows = []
    for k in sorted(set(fa) | set(fb)):
        va, vb = fa.get(k, "<MISSING>"), fb.get(k, "<MISSING>")
        num = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                  for v in (va, vb))
        row = {"path": k, "v11904": va, "v14880": vb,
               "delta": (vb - va) if num else None,
               "numeric": num, "same": va == vb}
        if num and va != 0:
            row["rel_delta"] = (vb - va) / abs(va)
        rows.append(row)
    return rows


def build_comparison(ctx):
    """完整对照表。所有数字均由脚本从 raw JSON 读出，无手抄环节。"""
    cmp_out = {
        "schema": "e0_comparison_11904_vs_14880_v3",
        "generated_at_utc": ctx["env"]["now_utc"],
        "generated_by": Path(__file__).name,
        "delta_convention": "delta = 14880 - 11904",
        "data_sources": {
            "note": "全部取自六份一手结果 JSON；A03 与 v1/v2 对照表均未被引用",
            "raw_json_sha256": dict(RAW_SHA),
        },
        "checkpoints": {
            "11904": {"logical_id": CKPT["boundary11904"]["logical_id"],
                      "file_sha256": CKPT["boundary11904"]["file_sha256"],
                      "step": 11904, "stage_recorded_in_file": 2},
            "14880": {"logical_id": CKPT["verified14880"]["logical_id"],
                      "file_sha256": CKPT["verified14880"]["file_sha256"],
                      "step": 14880, "stage_recorded_in_file": 3},
        },
        "pairs": {}, "headline": {}, "excluded_branches": list(FLATTEN_SKIP),
    }
    for pname, (jold, jnew) in PAIRS.items():
        a, b = ctx["raw"].get(jold), ctx["raw"].get(jnew)
        if a is None or b is None:
            cmp_out["pairs"][pname] = {"error": "缺少一手结果，无法生成对照"}
            continue
        rows = diff_rows(a, b)
        nums = [r for r in rows if r["numeric"]]
        cmp_out["pairs"][pname] = {
            "job_11904": jold, "job_14880": jnew,
            "n_paths": len(rows), "n_numeric": len(nums),
            "n_identical": sum(1 for r in rows if r["same"]),
            "max_abs_delta": max((abs(r["delta"]) for r in nums), default=None),
            "rows": rows,
        }
    return cmp_out


Q1_MAIN = ("R2", "rmse", "nse", "biasabs")
Q1_HORIZ = ("rmse25", "rmse_0_5", "rmse_5_10", "rmse_10_15", "rmse_15_20")
STRATA = ("forest", "shrub", "grass", "crop")
Q2_ARMS = ("full", "alpha0", "T_identity")
Q2_FAMS = ("closure_cut_alpha0", "transition_identity")
Q3_FAMS = ("paired_bootstrap", "geo_cluster_bootstrap", "reused_control_cluster_bootstrap")


def _cell(ctx, jold, jnew, path):
    """取一对数值并给出 Δ。缺失如实记为 None，不做填补。"""
    va = get_path(ctx["raw"].get(jold), path)
    vb = get_path(ctx["raw"].get(jnew), path)
    num = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (va, vb))
    return {"path": path, "v11904": va, "v14880": vb,
            "delta": (vb - va) if num else None}


def _headline_q1(ctx, cmp_out):
    for split, pname in (("val", "Q1Q2_val"), ("oodt", "Q1Q2_oodt")):
        jold, jnew = PAIRS[pname]
        blk = {"split": split, "job_11904": jold, "job_14880": jnew,
               "n_targets": {
                   "v11904": get_path(ctx["raw"].get(jold), "provenance.n_targets"),
                   "v14880": get_path(ctx["raw"].get(jnew), "provenance.n_targets"),
                   "frozen_manifest_sha256": MANIFESTS[split][1]},
               "overall": {}, "horizons": {}, "strata": {}}
        for m in Q1_MAIN:
            blk["overall"][m] = _cell(ctx, jold, jnew, f"Q1_forecast.full.{m}")
        for h in Q1_HORIZ:
            blk["horizons"][h] = _cell(ctx, jold, jnew, f"Q1_forecast.full.{h}")
        for s in STRATA:
            blk["strata"][s] = {m: _cell(ctx, jold, jnew, f"Q1_forecast.full.{m}_{s}")
                                for m in Q1_MAIN}
        cmp_out["headline"].setdefault("Q1", {})[split] = blk


def _headline_q2(ctx, cmp_out):
    for split, pname in (("val", "Q1Q2_val"), ("oodt", "Q1Q2_oodt")):
        jold, jnew = PAIRS[pname]
        blk = {"split": split, "arms": {}, "official_deltas": {},
               "bootstrap_families": {}, "invariants": {}, "gates": {}}
        for arm in Q2_ARMS:
            blk["arms"][arm] = {m: _cell(ctx, jold, jnew, f"Q2_load_bearing.{arm}.{m}")
                                for m in ("R2", "rmse")}
        for k in ("official_R2_full_minus_alpha0", "official_R2_full_minus_Tid"):
            blk["official_deltas"][k] = _cell(ctx, jold, jnew, f"Q2_load_bearing.{k}")
        for fam in Q2_FAMS:
            blk["bootstrap_families"][fam] = {
                "bootstrap95": {m: _cell(ctx, jold, jnew,
                                         f"Q2_load_bearing.{fam}.bootstrap95.{m}")
                                for m in ("mean", "ci_low", "ci_high",
                                          "frac_pos", "n", "significant_gt0")},
                "paired": {m: _cell(ctx, jold, jnew, f"Q2_load_bearing.{fam}.paired.{m}")
                           for m in ("n", "win", "tie", "loss",
                                     "mean_delta_R2", "median_delta_R2")}}
        for inv in ("alpha0_pred_equals_context_prior", "T_identity_is_state_identity",
                    "live_weights_restored"):
            blk["invariants"][inv] = _cell(
                ctx, jold, jnew, f"Q2_load_bearing.invariants.{inv}")
        for k in ("dr2_floor", "dr2_floor_pass", "transition_margin_clean", "verdict"):
            blk["gates"][k] = _cell(ctx, jold, jnew, f"Q2_load_bearing.{k}")
        blk["transition_margin_confound_note"] = get_path(
            ctx["raw"].get(jnew), "Q2_load_bearing.transition_margin_confound_note")
        cmp_out["headline"].setdefault("Q2", {})[split] = blk


def _headline_q3(ctx, cmp_out):
    jold, jnew = PAIRS["Q3_oodt"]
    EX = "models.exclusive"
    DF = f"{EX}.q3_donor_fidelity"
    blk = {"split": "oodt", "job_11904": jold, "job_14880": jnew,
           "aggregate": {}, "endpoint_fidelity": {}, "response_magnitude": {},
           "hotdry_interaction": {}, "strata": {}, "counts": {}, "verdicts": {}}

    # 三臂聚合精度
    for arm in ("actual", "donor", "mean"):
        blk["aggregate"][arm] = {
            m: _cell(ctx, jold, jnew, f"{EX}.q3_aggregate_extreme.{arm}.{m}")
            for m in ("R2", "rmse", "nse")}

    # 端点保真：donor−actual 与 mean−actual 的损失差 + 三个 bootstrap 家族
    for c in ("extreme_actual_vs_donor", "extreme_actual_vs_mean"):
        base = f"{DF}.endpoint_fidelity.{c}"
        ent = {"delta_loss_mean": _cell(ctx, jold, jnew, f"{base}.delta_loss_mean")}
        for fam in Q3_FAMS:
            keys = ["mean", "ci_low", "ci_high", "n", "significant_gt0"]
            if fam == "paired_bootstrap":
                keys.append("frac_pos")
            else:
                keys.append("n_clusters")
            ent[fam] = {m: _cell(ctx, jold, jnew, f"{base}.{fam}.{m}") for m in keys}
        blk["endpoint_fidelity"][c] = ent

    # 响应幅度（极端 / 常态 各两组对照）
    for c in ("extreme_actual_vs_donor", "extreme_actual_vs_mean",
              "normal_actual_vs_donor", "normal_actual_vs_mean"):
        blk["response_magnitude"][c] = {
            m: _cell(ctx, jold, jnew, f"{DF}.response_magnitude.{c}.{m}")
            for m in ("mean", "n")}

    # 热干交互（hotdry − normal），四个效应量 × 三个 bootstrap 家族
    for eff in ("dloss_donor", "dloss_mean", "resp_donor", "resp_mean"):
        blk["hotdry_interaction"][eff] = {
            fam: {m: _cell(ctx, jold, jnew,
                           f"{DF}.interaction_hotdry_minus_normal.{eff}.{fam}.{m}")
                  for m in ("mean", "ci_low", "ci_high", "significant_gt0")}
            for fam in Q3_FAMS}

    # 分层精度：两个 cohort × 各臂 × R²/RMSE
    sa_new = get_path(ctx["raw"].get(jnew), f"{EX}.stratum_accuracy", {}) or {}
    for cohort, arms in sa_new.items():
        if not isinstance(arms, dict):
            continue
        blk["strata"][cohort] = {
            arm: {m: _cell(ctx, jold, jnew,
                           f"{EX}.stratum_accuracy.{cohort}.{arm}.{m}")
                  for m in ("R2", "rmse")} for arm in sorted(arms)}

    # 计数与判定
    for k in ("n_pairs", "protocol_n_pairs", "n_extreme", "n_control_unique", "n_boot"):
        blk["counts"][k] = _cell(ctx, jold, jnew, k)
    blk["counts"]["n_geo_clusters"] = _cell(
        ctx, jold, jnew,
        f"{DF}.endpoint_fidelity.extreme_actual_vs_donor."
        f"geo_cluster_bootstrap.n_clusters")
    blk["counts"]["n_reused_control_clusters"] = _cell(
        ctx, jold, jnew,
        f"{DF}.endpoint_fidelity.extreme_actual_vs_donor."
        f"reused_control_cluster_bootstrap.n_clusters")
    for k in ("endpoint_fidelity_status", "hotdry_enhancement_status",
              "raw_status", "overall_status", "primary_criterion",
              "uf_differs_all_pairs", "weather_in_base", "evidence_role"):
        blk["verdicts"][k] = _cell(ctx, jold, jnew, f"{DF}.{k}")
    cmp_out["headline"]["Q3"] = blk


# ==================== 指标清单：每个 job 的全部可用指标键 ====================

def build_metric_inventory(ctx):
    inv = {
        "schema": "e0_metric_inventory_v3",
        "generated_at_utc": ctx["env"]["now_utc"],
        "generated_by": Path(__file__).name,
        "convention": "每个 job 列出压平后的全部指标路径；per_cube_effects 与 "
                      "q3_donor_rows 两棵大子树只记录规模，不逐项展开",
        "jobs": {},
        "historical_reference": {
            "path": str(HIST_REF), "sha256": ctx.get("hist_ref", {}).get("sha256"),
            "n_formal_metric_keys": ctx.get("hist_ref", {}).get("n_formal"),
            "metadata_keys_excluded": ctx.get("hist_ref", {}).get("metadata_keys"),
            "key_format": "<job_name>:<dotted.path>",
            "per_job_key_counts": {},
            "note": "正式指标键共 57 个（19 × 3 个 11,904 作业）；"
                    "`_` 前缀的 8 个键是元数据，必须排除在复现计数之外",
        },
    }
    for name in sorted(JOBS):
        d = ctx["raw"].get(name)
        if d is None:
            inv["jobs"][name] = {"error": "缺少一手结果"}
            continue
        flat = flatten(d, skip=("per_cube_effects", "q3_donor_rows", "command"))
        numeric = {k: v for k, v in flat.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)}
        cfg = JOBS[name]
        entry = {
            "kind": cfg["kind"], "split": cfg["split"],
            "checkpoint_role": cfg["ckpt"],
            "checkpoint_file_sha256": CKPT[cfg["ckpt"]]["file_sha256"],
            "checkpoint_logical_id": CKPT[cfg["ckpt"]]["logical_id"],
            "raw_json_sha256": RAW_SHA[name],
            "n_paths_total": len(flat), "n_numeric_paths": len(numeric),
            "numeric_paths": sorted(numeric),
            "non_numeric_paths": sorted(set(flat) - set(numeric)),
        }
        if cfg["kind"] == "q3":
            pce = get_path(d, "models.exclusive.per_cube_effects")
            rows = get_path(d, "models.exclusive.q3_donor_rows")
            entry["large_subtrees"] = {
                "per_cube_effects": {"type": "dict",
                                     "size": len(pce) if isinstance(pce, dict) else None},
                "q3_donor_rows": {"type": "list",
                                  "size": len(rows) if isinstance(rows, list) else None}}
        inv["jobs"][name] = entry
    ref_rows = ctx.get("reproduction", {}).get("rows", [])
    per_job = {}
    for r in ref_rows:
        per_job[r["job"]] = per_job.get(r["job"], 0) + 1
    inv["historical_reference"]["per_job_key_counts"] = per_job
    return inv


# ==================== 工件索引：路径 / 字节 / SHA / mtime ====================

SELF_GENERATED_V3 = (
    "attempt_manifest_v3.json", "e0_launch_record_v3.json",
    "e0_acceptance_report_v3.json", "e0_metric_inventory_v3.json",
    "e0_comparison_11904_vs_14880_v3.json", "e0_provenance_v3.json",
    "e0_artifact_index_v3.json", "closeout_audit_v3.json",
)


def _finfo(p: Path, with_sha=True):
    st = p.stat()
    out = {"path": str(p), "bytes": st.st_size,
           "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc)
           .isoformat().replace("+00:00", "Z"),
           "mode": oct(st.st_mode & 0o777)}
    if with_sha:
        out["sha256"] = sha256_file(p)
    return out


def build_artifact_index(ctx):
    idx = {
        "schema": "e0_artifact_index_v3",
        "generated_at_utc": ctx["env"]["now_utc"],
        "generated_by": Path(__file__).name,
        "note": "本索引不含本脚本尚未写出的 _v3 产物自身 SHA（写出后由 closeout "
                "审计单独记录），以避免自指哈希",
        "attempt_root": str(ATTEMPT),
        "raw_results": {}, "run_dirs": {}, "invalid_partial_dirs": {},
        "logs": {}, "runners": {}, "verifiers": {}, "prior_closeout_artifacts": {},
        "upstream_evidence": {}, "totals": {},
    }
    # 六份一手结果
    for name in sorted(JOBS):
        fn = Q1Q2_FILE if JOBS[name]["kind"] == "q1q2" else Q3_FILE
        p = RUNS / name / fn
        if p.is_file():
            e = _finfo(p)
            e["sha256_matches_inventory"] = e["sha256"] == RAW_SHA[name]
            idx["raw_results"][name] = e
    # 每个 run 目录的文件计数与总字节
    for d in sorted(RUNS.iterdir()):
        if not d.is_dir():
            continue
        files = [f for f in d.rglob("*") if f.is_file()]
        ent = {"path": str(d), "n_files": len(files),
               "total_bytes": sum(f.stat().st_size for f in files),
               "children": sorted(x.name for x in d.iterdir())}
        if d.name in INVALID_PARTIAL:
            ent["status"] = "INVALID_PARTIAL"
            ent["reason"] = "无最终结果 JSON，永久保留为审计证据，不进入正式结果集"
            idx["invalid_partial_dirs"][d.name] = ent
        else:
            ent["status"] = "FORMAL"
            idx["run_dirs"][d.name] = ent
    return idx


def extend_artifact_index(ctx, idx):
    """继续补齐日志、runner、验收器、既有 v1/v2 工件与上游证据。"""
    logs = ATTEMPT / "logs"
    if logs.is_dir():
        for f in sorted(logs.iterdir()):
            if f.is_file():
                e = _finfo(f)
                stem = f.name.replace(".log", "")
                e["belongs_to"] = ("FORMAL" if stem in JOBS else
                                   "INVALID_PARTIAL" if stem in INVALID_PARTIAL
                                   else "OTHER")
                idx["logs"][f.name] = e
    for pat, bucket in (("runner_physical_gpu*.sh", "runners"),
                        ("e0_runner_gpu*.sh", "runners"),
                        ("launch_record_shard_pgpu*.json", "runners"),
                        ("verify_and_aggregate_retry*.py", "verifiers"),
                        ("build_attempt_manifest.py", "verifiers"),
                        ("merge_launch_records*.py", "verifiers")):
        for f in sorted(ATTEMPT.glob(pat)):
            if f.is_file():
                idx[bucket][f.name] = _finfo(f)
    # 既有 v1/v2 封账工件：登记但明确不作为 v3 的数据来源
    for f in sorted(ATTEMPT.iterdir()):
        if not f.is_file():
            continue
        nm = f.name
        if nm in SELF_GENERATED_V3 or nm in idx["verifiers"] or nm in idx["runners"]:
            continue
        if (nm.startswith(("e0_acceptance_report", "e0_comparison", "e0_provenance",
                           "e0_artifact_index", "closeout_audit", "attempt_manifest",
                           "e0_launch_record", "A03_snapshot", "STATUS", "state"))
                or nm.endswith((".sha256", ".txt"))):
            e = _finfo(f)
            e["role"] = "prior_closeout_evidence"
            e["used_as_v3_data_source"] = False
            idx["prior_closeout_artifacts"][nm] = e
    # 上游证据：checkpoint / registry / alias / 冻结清单 / 协议 / 训练侧记录
    up = idx["upstream_evidence"]
    for role, meta in CKPT.items():
        sha = meta["file_sha256"]
        p = OBJECTS / sha[:2] / f"{sha}.pt"
        if p.is_file():
            up[f"checkpoint:{role}"] = {**_finfo(p, with_sha=False),
                                        "sha256": sha,
                                        "logical_id": meta["logical_id"],
                                        "sha_verified_this_run": True}
    for p in (REGISTRY, ALIAS_FILE, HIST_REF, LAUNCH_MANIFEST,
              PARAM_AUDIT, M9_REPORT, STATE_SHA_CHECK,
              MANIFESTS["val"][0], MANIFESTS["oodt"][0],
              TS_ROOT / "eval/eval_b4_exclusive_contract.py",
              TS_ROOT / "eval/extreme_state_audit.py"):
        if Path(p).is_file():
            up[str(Path(p).relative_to(AGENT_ROOT))] = _finfo(Path(p))
    if Q3_PROTO.is_dir():
        for f in sorted(Q3_PROTO.iterdir()):
            if f.is_file():
                up[f"q3_protocol/{f.name}"] = _finfo(f)
    allf = [f for f in ATTEMPT.rglob("*") if f.is_file()]
    idx["totals"] = {
        "attempt_n_files": len(allf),
        "attempt_total_bytes": sum(f.stat().st_size for f in allf),
        "n_raw_results": len(idx["raw_results"]),
        "n_formal_run_dirs": len(idx["run_dirs"]),
        "n_invalid_partial_dirs": len(idx["invalid_partial_dirs"]),
        "n_logs": len(idx["logs"]), "n_upstream_evidence": len(up),
        "n_prior_closeout_artifacts": len(idx["prior_closeout_artifacts"]),
    }
    return idx


# ==================== provenance：来源、缺口与时间线 ====================

def build_provenance(ctx):
    pv = {
        "schema": "e0_provenance_v3",
        "generated_at_utc": ctx["env"]["now_utc"],
        "generated_by": Path(__file__).name,
        "closeout_environment": ctx["env"],
        "trusted_sources": {
            "raw_results": {n: {"path": str(RUNS / n / (Q1Q2_FILE if JOBS[n]["kind"] == "q1q2"
                                                        else Q3_FILE)),
                                "sha256": RAW_SHA[n]} for n in sorted(JOBS)},
            "launch_shards": [f"launch_record_shard_pgpu{g}.json" for g in (2, 4, 5, 6)],
            "frozen_launch_manifest": ctx.get("launch_manifest"),
            "historical_reference": ctx.get("hist_ref"),
            "weight_registry": ctx.get("registry"),
            "alias": ctx.get("alias"),
            "checkpoints": ctx.get("ckpt_stat"),
            "registry_entries": ctx.get("registry_entries"),
            "data_manifests": {k: {"path": str(v[0]), "sha256": v[1], "n_files": v[2]}
                               for k, v in MANIFESTS.items()},
            "evaluator_sources": ctx.get("evaluator_sources"),
            "q3_protocol": ctx.get("q3_protocol"),
            "training_side_records": {
                "m9_acceptance": ctx.get("m9"),
                "parameter_audit": ctx.get("param_audit"),
                "state_sha_check": ctx.get("state_sha_check"),
            },
        },
        "explicitly_not_used_as_source": [
            "思路整理进展/A03_TerraState_关键实验结果与决策总账.md（待本轮重写的文档本身）",
            "e0_comparison_11904_vs_14880.json / _v2.json / _v2_comprehensive.json",
            "e0_acceptance_report.json / _v2.json",
            "closeout_audit_v2.json",
        ],
        "evaluator_commit": {
            "q1q2": ctx.get("evaluator_commit_q1q2"),
            "q3": None,
            "q3_gap_note": "Q3 结果 JSON 的 schema 不记录 evaluator commit；"
                           "Q3 评测脚本身份改由 eval/extreme_state_audit.py 的实测 "
                           "SHA-256 与冻结 manifest 记录值比对来确定",
        },
        "q3_checkpoint_identity": {
            "binding": "sidecar",
            "per_job": ctx.get("q3_sidecar_identity"),
            "gap_note": "extreme_state_audit.json 记录 protocol_sha，但不记录 checkpoint "
                        "SHA；身份由 run 目录名、launch shard 的 checkpoint_sha256 与 "
                        "runner 日志首行的加载记录三方共同确定，并直接校验磁盘上的 "
                        "checkpoint 文件 SHA",
        },
        "provenance_gaps": ctx.get("provenance_gaps"),
        "manifest_disambiguation": ctx.get("manifest_disambiguation"),
        "ground_truth_binding": ctx.get("ground_truth"),
        "excluded_evidence": ctx.get("excluded"),
        "interrupted_attempt": ctx.get("interrupted_attempt"),
        "corrected_defects": ctx.get("corrected_defects"),
        "timeline_log_provable": ctx.get("timeline"),
    }
    return pv


# ==================== 时间线：只写日志/文件系统可证的时刻 ====================

def build_timeline(ctx):
    """每一行都必须有可指认的证据来源。不推算总耗时，不编造运行时长。"""
    ev = []
    for name in sorted(JOBS):
        j = ctx["launch"].get(name, {})
        if j.get("started_utc"):
            ev.append({"event": "job_started", "job": name,
                       "utc": j["started_utc"], "pid": j.get("pid"),
                       "physical_gpu": j.get("physical_gpu"),
                       "evidence": f"launch_record_shard_pgpu{j.get('physical_gpu')}.json"
                                   " 的 started_utc 字段"})
        fn = Q1Q2_FILE if JOBS[name]["kind"] == "q1q2" else Q3_FILE
        p = RUNS / name / fn
        if p.is_file():
            ev.append({"event": "result_json_written", "job": name,
                       "utc": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                       .isoformat().replace("+00:00", "Z"),
                       "evidence": f"{p.relative_to(ATTEMPT)} 的文件 mtime"})
    ev.sort(key=lambda e: e["utc"])
    starts = [e["utc"] for e in ev if e["event"] == "job_started"]
    writes = [e["utc"] for e in ev if e["event"] == "result_json_written"]
    tl = {
        "convention": "全部为 UTC。job_started 取自 launch shard；result_json_written "
                      "取自结果文件 mtime。二者是不同性质的证据，不得相减当作单作业耗时。",
        "events": ev,
        "earliest_job_start_utc": min(starts) if starts else None,
        "latest_result_write_utc": max(writes) if writes else None,
        "not_log_provable": [
            "单个作业的精确 wall-clock 时长（runner 日志未记录逐作业结束时刻）",
            "六作业总耗时的精确值（存在 GPU 共享与排队，不能由首启到末写直接相减）",
        ],
        "span_note": None,
    }
    if starts and writes:
        tl["span_note"] = (f"最早启动 {min(starts)} 至最后一份结果落盘 {max(writes)} "
                           f"之间的跨度可由文件系统证明，但该跨度包含 GPU 共享等待，"
                           f"不等于计算耗时")
    ctx["timeline"] = tl
    return tl


def build_launch_record_v3(ctx):
    jobs = []
    for name in sorted(JOBS):
        cfg, j = JOBS[name], ctx["launch"].get(name, {})
        jobs.append({
            "name": name, "kind": cfg["kind"], "split": cfg["split"],
            "physical_gpu": j.get("physical_gpu"), "pid": j.get("pid"),
            "exit_code": j.get("exit_code"), "started_utc": j.get("started_utc"),
            "checkpoint_role": cfg["ckpt"],
            "checkpoint_logical_id": CKPT[cfg["ckpt"]]["logical_id"],
            "checkpoint_sha256": j.get("checkpoint_sha256"),
            "checkpoint_stage_recorded": cfg["stage"],
            "expected_targets": j.get("expected_targets"),
            "expected_pairs": j.get("expected_pairs"),
            "output_dir": str(RUNS / name), "log": j.get("log"),
            "source_shard": j.get("shard"),
            "result_json": (Q1Q2_FILE if cfg["kind"] == "q1q2" else Q3_FILE),
            "result_json_sha256": RAW_SHA[name],
        })
    return {
        "schema": "e0_launch_record_v3", "generated_at_utc": ctx["env"]["now_utc"],
        "generated_by": Path(__file__).name,
        "authority": "job → 物理 GPU 的映射唯一来源是 launch_record_shard_pgpu*.json；"
                     "逻辑作业名（gpu0..gpu5）与物理 GPU 编号无对应关系，禁止由名字推断",
        "logical_name_vs_physical_gpu": {n: JOBS[n]["pgpu"] for n in sorted(JOBS)},
        "physical_gpus_used": sorted({JOBS[n]["pgpu"] for n in JOBS}),
        "n_jobs": len(jobs), "jobs": jobs,
        "provenance_gaps": ctx.get("provenance_gaps"),
        "invalid_partial_dirs": INVALID_PARTIAL,
    }


# ==================== attempt manifest / 验收报告 / closeout 审计 ====================

def build_attempt_manifest_v3(ctx):
    return {
        "schema": "attempt_manifest_v3",
        "generated_at_utc": ctx["env"]["now_utc"],
        "generated_by": Path(__file__).name,
        "attempt_id": ATTEMPT.name,
        "attempt_root": str(ATTEMPT),
        "parent_attempt": {"id": PARENT.name, "path": str(PARENT),
                           "status": "INTERRUPTED",
                           "detail": ctx.get("interrupted_attempt")},
        "experiment": "E0：11,904 与 14,880 在同一 Q1/Q2/Q3 协议下的对照评测",
        "nodes": {
            "gpu_execution_hostname": ctx["env"]["gpu_exec_hostname"],
            "gpu_execution_hostname_source": ctx["env"]["gpu_exec_hostname_source"],
            "cpu_closeout_hostname": ctx["env"]["closeout_hostname"],
            "note": "GPU 执行节点与本轮 CPU 封账节点是两台不同机器，"
                    "两者都必须如实记录，任何一方都不得覆盖另一方",
        },
        "physical_gpus_used": sorted({JOBS[n]["pgpu"] for n in JOBS}),
        "jobs": {n: {"kind": JOBS[n]["kind"], "split": JOBS[n]["split"],
                     "checkpoint_role": JOBS[n]["ckpt"],
                     "physical_gpu": JOBS[n]["pgpu"],
                     "n_targets": JOBS[n]["n_targets"],
                     "checkpoint_stage_recorded": JOBS[n]["stage"]}
                 for n in sorted(JOBS)},
        "checkpoints": ctx.get("ckpt_stat"),
        "registry": ctx.get("registry"),
        "partitioning": {
            "historical_reference": {
                "what": "11,904 的历史 Q1/Q2/Q3 数字（57 个正式指标）",
                "path": str(HIST_REF), "sha256": ctx.get("hist_ref", {}).get("sha256"),
                "role": "复现基准，不是本轮新测结果"},
            "formal_rerun": {"what": "本轮六份正式结果", "jobs": sorted(JOBS)},
            "smoke": {"what": "smoke 产物", "entries": [
                e for e in ctx.get("excluded", []) if "smoke" in e["path"]]},
            "selftest": {"what": "自检 fixture", "entries": [
                e for e in ctx.get("excluded", []) if "selftest" in e["path"]]},
            "invalid_partial": {"what": "无最终结果 JSON 的中途目录",
                                "dirs": INVALID_PARTIAL},
            "interrupted_attempt": {"what": "20260818 因共享 GPU 让让出而中断的尝试",
                                    "detail": ctx.get("interrupted_attempt")},
        },
        "constraints_this_round": [
            "严格 CPU-only：CUDA_VISIBLE_DEVICES=\"\"，不创建 CUDA context",
            "不重跑任何 GPU 作业，不启动训练 / Q4 / Candidate C / simulator",
            "不删除、移动、覆盖任何 raw JSON、checkpoint、旧 manifest、v1/v2 工件",
            "不进行任何进程操作，不执行 git 写操作",
        ],
    }


def build_acceptance_report_v3(ctx, gates):
    all_failed = [{"gate": g.gid, **c} for g in gates for c in g.failed]
    n_checks = sum(len(g.checks) for g in gates)
    accepted = not all_failed and all(g.ok for g in gates)
    return {
        "schema": "e0_acceptance_report_v3",
        "generated_at_utc": ctx["env"]["now_utc"],
        "generated_by": Path(__file__).name,
        "verdict": "ACCEPTED" if accepted else "BLOCKED",
        "fail_closed": True,
        "n_gates": len(gates), "n_checks": n_checks,
        "n_failed": len(all_failed),
        "gate_summary": [{"gate": g.gid, "title": g.title, "ok": g.ok,
                          "n_checks": len(g.checks), "n_failed": len(g.failed)}
                         for g in gates],
        "failed_checks": all_failed,
        "gates": [g.as_dict() for g in gates],
        "reproduction": {
            "n_formal_metric_keys": ctx.get("reproduction", {}).get("n_formal"),
            "n_pass": ctx.get("reproduction", {}).get("n_pass"),
            "n_bit_exact": ctx.get("reproduction", {}).get("n_bit_exact"),
            "scope": "仅 11,904 侧复现历史参考；14,880 侧无历史参考可比",
        },
        "sanity_anchors": ctx.get("anchors"),
        "policy": "任一检查失败即整体 BLOCKED；不得在存在失败项时写「正式封账」",
    }


def build_closeout_audit_v3(ctx, gates, report, written):
    all_failed = report["failed_checks"]
    accepted = report["verdict"] == "ACCEPTED"
    return {
        "schema": "closeout_audit_v3",
        "generated_at_utc": ctx["env"]["now_utc"],
        "generated_by": Path(__file__).name,
        "verdict": report["verdict"],
        "n_checks": report["n_checks"],
        "failed_checks": all_failed,
        "n_failed": len(all_failed),
        "gate_groups": {
            "A": "作业清单、启动记录与 checkpoint 身份",
            "B": "四份 Q1/Q2 结果契约与 schema 完整性",
            "C": "两份 Q3 极端态审计与协议绑定",
            "D": "11,904 复现历史参考 57 个正式指标",
            "E": "完整性、ground truth 归属与口径边界",
            "F": "sanity anchor 与训练侧记录交叉核对",
        },
        "closeout_environment": ctx["env"],
        "artifacts_written": written,
        "evidence_preserved": {
            "v1_v2_artifacts": "全部保留，未删除未覆盖；本轮仅新增 _v3 文件",
            "invalid_partial_dirs": INVALID_PARTIAL,
            "interrupted_attempt": PARENT.name,
            "raw_results": "六份一手结果只读校验，SHA-256 与清点值一致",
        },
        "corrected_defects": ctx.get("corrected_defects"),
        "known_gaps_recorded_honestly": [
            "e0_launch_record.gpu{2,4,5,6}.json 的 jobs 列表为空",
            "Q3 结果 JSON 不记录 checkpoint SHA 与 evaluator commit（sidecar 绑定）",
            "Q3 协议文件计数三个口径不同：磁盘 8 / MANIFEST 7 / 结果 JSON 绑定 5",
            "单作业 wall-clock 时长不可由现有日志证明",
            "边界 checkpoint 记录 stage=2，而其后第一次更新属 stage=3",
        ],
        "next_action": ("CANDIDATE_C_T3_CPU_CONTRACT" if accepted else "FIX_FAILED_CHECKS"),
        "e0_closeout_v3": "ACCEPTED" if accepted else "BLOCKED",
        "t0_status": "COMPLETE" if accepted else "PROVISIONAL",
    }


# ============================ 环境与主流程 ============================

def _git(*args):
    # 仓库根是 WorldModel2026v2，不是 AGENT_ROOT；AGENT_ROOT 下没有 .git，
    # 且向上发现会在 mount 边界停止，故必须以 TS_ROOT 为 -C 并允许跨文件系统发现。
    try:
        env = dict(os.environ, GIT_DISCOVERY_ACROSS_FILESYSTEM="1")
        r = subprocess.run(["git", "-C", str(TS_ROOT), *args],
                           capture_output=True, text=True, timeout=90, env=env)
        return r.stdout.strip() if r.returncode == 0 else f"<git error: {r.stderr.strip()[:120]}>"
    except (OSError, subprocess.SubprocessError) as e:
        return f"<git unavailable: {e}>"


def build_env():
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    gpu_host, gpu_host_src = None, None
    am = ATTEMPT / "attempt_manifest.json"
    if am.is_file():
        h = find_key(load_json(am), "hostname")
        if h:
            gpu_host, gpu_host_src = h, f"{am.name} 的 hostname 字段（GPU 执行时写入）"
    porcelain = _git("status", "--porcelain")
    git_ok = not porcelain.startswith("<git")
    lines = porcelain.splitlines() if git_ok else []
    outside = [ln for ln in lines if " obsworld/" not in ln]
    return {
        "now_utc": now,
        "closeout_hostname": os.uname().nodename,
        "closeout_role": "CPU-only 封账与审计（不执行任何 GPU 计算）",
        "gpu_exec_hostname": gpu_host,
        "gpu_exec_hostname_source": gpu_host_src,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "python": os.sys.version.split()[0],
        "cwd": os.getcwd(),
        "torch_imported": False,
        "git_repo_toplevel": _git("rev-parse", "--show-toplevel"),
        "git_head": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_query_ok": git_ok,
        "git_worktree_dirty": git_ok and bool(lines),
        "git_dirty_entry_count": len(lines) if git_ok else None,
        "git_dirty_outside_obsworld": len(outside) if git_ok else None,
        "git_dirty_outside_obsworld_entries": outside if git_ok else None,
        "git_note": "工作树确实是 dirty 的：obsworld/** 由另一会话并发修改，本轮不触碰；"
                    "obsworld 之外的条目多为本封账自身新增的 untracked 目录/文档。"
                    "本脚本只读 git，不执行 add/commit/push/reset/checkout/stash/clean。",
    }


def new_ctx():
    return {"env": build_env(), "raw": {}, "launch": {}, "ckpt_stat": {},
            "registry": {}, "registry_entries": {}, "alias": {},
            "provenance_gaps": [], "launch_manifest": {}, "q3_protocol": {},
            "q3_sidecar_identity": {}, "q3_stratum_arms": {}, "hist_ref": {},
            "reproduction": {}, "excluded": [], "interrupted_attempt": {},
            "ground_truth": {}, "corrected_defects": [], "anchors": [],
            "m9": {}, "param_audit": {}, "state_sha_check": {},
            "evaluator_sources": {}, "manifest_disambiguation": {},
            "hyperparams": {}, "timeline": {}, "evaluator_commit_q1q2": None}


def main() -> int:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        print("REFUSE: 必须以 CUDA_VISIBLE_DEVICES=\"\" 运行（严格 CPU-only）")
        return 2
    ctx = new_ctx()
    print(f"[v3] attempt={ATTEMPT.name} 封账节点={ctx['env']['closeout_hostname']} "
          f"GPU 执行节点={ctx['env']['gpu_exec_hostname']}")

    # 分段计时：网络文件系统上元数据 RPC 是主要开销，必须可归因而不是靠猜
    _mark = [time.monotonic()]

    def lap(label: str) -> None:
        now = time.monotonic()
        print(f"    [t] {label}: {now - _mark[0]:.1f}s", flush=True)
        _mark[0] = now

    gates = []
    for fn in (gate_a, gate_b, gate_c, gate_d, gate_e, gate_f):
        g = fn(ctx)
        gates.append(g)
        print(f"[gate {g.gid}] {g.title}: {len(g.checks) - len(g.failed)}/{len(g.checks)} 通过"
              + ("" if g.ok else f"  ✗ 失败 {len(g.failed)} 项"))
        for c in g.failed[:12]:
            print(f"    ✗ {c['name']}: {c['detail'][:150]}")
        lap(f"gate {g.gid}")

    build_timeline(ctx)
    lap("build_timeline")
    comparison = build_comparison(ctx)
    _headline_q1(ctx, comparison)
    _headline_q2(ctx, comparison)
    _headline_q3(ctx, comparison)
    lap("comparison+headline")
    inventory = build_metric_inventory(ctx)
    lap("metric_inventory")
    index = extend_artifact_index(ctx, build_artifact_index(ctx))
    lap("artifact_index")
    provenance = build_provenance(ctx)
    lap("provenance")
    launch_v3 = build_launch_record_v3(ctx)
    manifest_v3 = build_attempt_manifest_v3(ctx)
    lap("launch_record+attempt_manifest")
    report = build_acceptance_report_v3(ctx, gates)
    lap("acceptance_report")

    written = {}
    for fname, payload in (
            ("e0_comparison_11904_vs_14880_v3.json", comparison),
            ("e0_metric_inventory_v3.json", inventory),
            ("e0_artifact_index_v3.json", index),
            ("e0_provenance_v3.json", provenance),
            ("e0_launch_record_v3.json", launch_v3),
            ("attempt_manifest_v3.json", manifest_v3),
            ("e0_acceptance_report_v3.json", report)):
        sha = atomic_write_json(ATTEMPT / fname, payload)
        written[fname] = {"sha256": sha, "bytes": (ATTEMPT / fname).stat().st_size}
        print(f"[write] {fname}  {written[fname]['bytes']} B  sha256={sha[:16]}…")

    self_name = Path(__file__).name
    written[self_name] = {"sha256": sha256_file(Path(__file__)),
                          "bytes": Path(__file__).stat().st_size}
    audit = build_closeout_audit_v3(ctx, gates, report, written)
    sha = atomic_write_json(ATTEMPT / "closeout_audit_v3.json", audit)
    print(f"[write] closeout_audit_v3.json  sha256={sha[:16]}…")

    print(f"\n[verdict] {report['verdict']}  检查 {report['n_checks']} 项，"
          f"失败 {report['n_failed']} 项；历史复现 "
          f"{ctx['reproduction'].get('n_pass')}/{ctx['reproduction'].get('n_formal')}"
          f"（逐位相同 {ctx['reproduction'].get('n_bit_exact')}）")
    return 0 if report["verdict"] == "ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
