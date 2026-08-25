#!/usr/bin/env python3
"""E0 retry attempt 严格验收和聚合脚本 (Part 1/2)。

只读验证六项正式任务，生成：
- e0_acceptance_report.json
- e0_comparison_11904_vs_14880.json
- e0_provenance.json
- e0_artifact_index.json
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

RETRY = Path(__file__).parent
TS_ROOT = RETRY.parents[3]
MANIFEST = RETRY / "attempt_manifest.json"
LAUNCH_REC = RETRY / "e0_launch_record.json"
HISTORICAL_REF = RETRY.parent / "20260818_154859" / "historical_11904_reference.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dig(obj, *path, default=None):
    cur = obj
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def is_finite(v) -> bool:
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return math.isfinite(v)
    return False


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, name: str, ok: bool, detail: str) -> bool:
        self.rows.append({"name": name, "ok": bool(ok), "detail": detail})
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")
        return bool(ok)

    @property
    def failures(self) -> list[dict]:
        return [r for r in self.rows if not r["ok"]]


def check_six_jobs(ck: Checks) -> tuple[dict, bool]:
    """验收六项任务：exit_code、目录、结果 JSON、目标数、SHA。"""
    manifest = json.loads(MANIFEST.read_text())
    jobs = {j["name"]: j for j in manifest["jobs"]}

    if not LAUNCH_REC.exists():
        ck.add("launch_record_exists", False, f"{LAUNCH_REC.name} 缺失")
        return {}, False

    rec = json.loads(LAUNCH_REC.read_text())
    launched = {r["name"]: r for r in rec.get("jobs", [])}

    all_ok = ck.add("launch_record_exists", True, f"{len(launched)} 任务")
    all_ok &= ck.add("all_six_jobs_launched", len(launched) == 6,
                     f"{len(launched)}/6 任务名: {sorted(launched)}")

    results = {}
    for name, job in jobs.items():
        lr = launched.get(name)
        if lr is None:
            all_ok &= ck.add(f"{name}:launched", False, "launch_record 无此任务")
            continue

        rc = lr.get("exit_code")
        all_ok &= ck.add(f"{name}:exit_code_0", rc == 0, f"exit_code={rc}")

        outdir = Path(job["output_dir"])
        interrupted = (outdir / "INTERRUPTED.json").exists()
        all_ok &= ck.add(f"{name}:not_interrupted", not interrupted,
                         "正常" if not interrupted else "INTERRUPTED - 不得聚合")

        # checkpoint 文件 SHA 不变
        ckpt = Path(job["checkpoint_path"])
        now_sha = sha256_file(ckpt) if ckpt.exists() else "<missing>"
        all_ok &= ck.add(f"{name}:ckpt_sha_unchanged", now_sha == job["checkpoint_sha256"],
                         f"{now_sha[:16]}... vs {job['checkpoint_sha256'][:16]}...")

        # manifest SHA
        for label, mp, want in job.get("manifest_shas", []):
            got = sha256_file(Path(mp)) if Path(mp).exists() else "<missing>"
            all_ok &= ck.add(f"{name}:{label}_manifest_sha", got == want, f"{got[:16]}...")

        # 结果 JSON
        rp = Path(job["result_json"])
        if not rp.is_file():
            all_ok &= ck.add(f"{name}:result_json", False, f"{rp.name} 不存在")
            continue

        all_ok &= ck.add(f"{name}:result_json", True, f"{rp.name} ({rp.stat().st_size} bytes)")
        data = json.loads(rp.read_text())
        results[name] = {"job": job, "path": str(rp), "data": data, "launch": lr}

        # Q1/Q2 验证
        if job["kind"] == "q1q2":
            status = data.get("status")
            all_ok &= ck.add(f"{name}:status_COMPLETE", status == "COMPLETE", f"status={status}")

            incomplete = data.get("incomplete_reasons", [])
            all_ok &= ck.add(f"{name}:incomplete_reasons_empty", len(incomplete) == 0,
                             f"incomplete={incomplete}")

            formal = data.get("formal")
            all_ok &= ck.add(f"{name}:formal_true", formal is True, f"formal={formal}")

            ckpt_unchanged = data.get("checkpoint_unchanged")
            all_ok &= ck.add(f"{name}:checkpoint_unchanged_true", ckpt_unchanged is True,
                             f"checkpoint_unchanged={ckpt_unchanged}")

            n = dig(data, "q1", "full", "n_targets") or dig(data, "n_targets")
            expected = job["expected_targets"]
            all_ok &= ck.add(f"{name}:n_targets", n == expected, f"n={n} 期望={expected}")

            # 检查关键数值是否有限
            r2 = dig(data, "q1", "full", "r2")
            rmse = dig(data, "q1", "full", "rmse")
            all_ok &= ck.add(f"{name}:r2_finite", is_finite(r2), f"R²={r2}")
            all_ok &= ck.add(f"{name}:rmse_finite", is_finite(rmse), f"RMSE={rmse}")

        # Q3 验证
        else:
            role = data.get("evidence_role")
            all_ok &= ck.add(f"{name}:evidence_role_final", role == "final", f"role={role}")

            n_pairs = data.get("n_pairs")
            expected_pairs = job["expected_pairs"]
            all_ok &= ck.add(f"{name}:n_pairs_84", n_pairs == expected_pairs,
                             f"n_pairs={n_pairs} 期望={expected_pairs}")

            protocol_n = data.get("protocol_n_pairs")
            all_ok &= ck.add(f"{name}:protocol_n_pairs_84", protocol_n == 84,
                             f"protocol_n_pairs={protocol_n}")

            # 检查 R² 是否有限
            r2_actual = dig(data, "actual", "r2")
            all_ok &= ck.add(f"{name}:actual_r2_finite", is_finite(r2_actual), f"actual_R²={r2_actual}")

    return results, all_ok


def check_historical_reproduction(ck: Checks, results: dict) -> dict:
    """11,904 历史复现检查。"""
    if not HISTORICAL_REF.exists():
        ck.add("historical_ref_present", False, f"{HISTORICAL_REF.name} 缺失")
        return {"status": "no_reference"}

    ref = json.loads(HISTORICAL_REF.read_text())
    n_metrics = sum(1 for k in ref if not k.startswith("_"))
    ck.add("historical_ref_present", True, f"{n_metrics} 参考指标")

    default_tol = ref.get("_tolerance", 1e-6)
    per_pattern = ref.get("_tolerances", {})

    def tol_for(metric_path: str) -> float:
        best, best_len = default_tol, -1
        for pat, t in per_pattern.items():
            if pat in metric_path and len(pat) > best_len:
                best, best_len = t, len(pat)
        return best

    deltas = []
    ok_all = True
    for key, want in ref.items():
        if key.startswith("_"):
            continue
        job_name, metric_path = key.split(":", 1)
        r = results.get(job_name)
        if r is None:
            ok_all &= ck.add(f"repro:{key}", False, "任务结果缺失")
            continue

        got = dig(r["data"], *metric_path.split("."))
        if got is None:
            ok_all &= ck.add(f"repro:{key}", False, "指标路径缺失")
            continue

        tol = tol_for(metric_path)
        delta = abs(got - want) if isinstance(got, (int, float)) and isinstance(want, (int, float)) else None
        ok = delta is not None and delta <= tol

        ok_all &= ck.add(f"repro:{key}", ok,
                         f"want={want:.10g} got={got:.10g} Δ={delta:.2e} tol={tol:.0e}")
        deltas.append({"key": key, "want": want, "got": got, "delta": delta, "tol": tol, "ok": ok})

    status = "reproduced" if ok_all else "DRIFT_TO_DIAGNOSE"
    return {"status": status, "deltas": deltas, "tolerance_policy": {"default": default_tol, "per_pattern": per_pattern}}


def build_comparison(results: dict) -> dict:
    """构建 11,904 vs 14,880 比较表。"""
    comp = {"schema": "e0_comparison_v1", "pairs": {}}

    # Q1 Val
    v11_name = "gpu3_legacy11904_val_q1q2"
    v14_name = "gpu0_v14880_val_q1q2"
    if v11_name in results and v14_name in results:
        d11 = results[v11_name]["data"]
        d14 = results[v14_name]["data"]
        comp["pairs"]["validation_q1"] = {
            "11904": {
                "r2": dig(d11, "q1", "full", "r2"),
                "rmse": dig(d11, "q1", "full", "rmse"),
                "nse": dig(d11, "q1", "full", "nse"),
            },
            "14880": {
                "r2": dig(d14, "q1", "full", "r2"),
                "rmse": dig(d14, "q1", "full", "rmse"),
                "nse": dig(d14, "q1", "full", "nse"),
            },
        }

    # Q1 OOD-t
    o11_name = "gpu4_legacy11904_oodt_q1q2"
    o14_name = "gpu1_v14880_oodt_q1q2"
    if o11_name in results and o14_name in results:
        d11 = results[o11_name]["data"]
        d14 = results[o14_name]["data"]
        comp["pairs"]["oodt_q1"] = {
            "11904": {
                "r2": dig(d11, "q1", "full", "r2"),
                "rmse": dig(d11, "q1", "full", "rmse"),
            },
            "14880": {
                "r2": dig(d14, "q1", "full", "r2"),
                "rmse": dig(d14, "q1", "full", "rmse"),
            },
        }

    # Q3
    q3_11_name = "gpu5_legacy11904_oodt_q3"
    q3_14_name = "gpu2_v14880_oodt_q3"
    if q3_11_name in results and q3_14_name in results:
        d11 = results[q3_11_name]["data"]
        d14 = results[q3_14_name]["data"]
        comp["pairs"]["oodt_q3"] = {
            "11904": {
                "actual_r2": dig(d11, "actual", "r2"),
                "overall": d11.get("overall"),
            },
            "14880": {
                "actual_r2": dig(d14, "actual", "r2"),
                "overall": d14.get("overall"),
            },
        }

    comp["interpretation_rules"] = [
        "0.01 OOD-t 对齐阈值仅用于描述 checkpoint 近似程度，非成功门或选择阈值",
        "14,880 已在 E0 前固定为后续默认 anchor，不根据 OOD 结果回选",
        "Q1 Val/OOD-t 的极小 R² 差异（<0.001）属正常训练噪声，不视为显著改善或退化",
        "Q3 hot-dry FAIL 是科学结果，不是运行失败",
        "只主张 response fidelity，不主张极端热旱特异增强或反事实因果",
    ]

    return comp


# 继续 Part 2...
