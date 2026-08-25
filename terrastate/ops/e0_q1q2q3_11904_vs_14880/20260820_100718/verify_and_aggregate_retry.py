#!/usr/bin/env python3
"""E0 retry attempt 严格验收和聚合脚本 - 完整版。"""
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
    """验收六项任务。"""
    manifest = json.loads(MANIFEST.read_text())
    jobs = {j["name"]: j for j in manifest["jobs"]}

    if not LAUNCH_REC.exists():
        ck.add("launch_record_exists", False, f"{LAUNCH_REC.name} 缺失")
        return {}, False

    rec = json.loads(LAUNCH_REC.read_text())
    launched = {r["name"]: r for r in rec.get("jobs", [])}

    all_ok = ck.add("launch_record_exists", True, f"{len(launched)} 任务")
    all_ok &= ck.add("all_six_jobs_launched", len(launched) == 6,
                     f"{len(launched)}/6")

    results = {}
    for name, job in jobs.items():
        lr = launched.get(name)
        if lr is None:
            all_ok &= ck.add(f"{name}:launched", False, "无 launch_record")
            continue

        rc = lr.get("exit_code")
        all_ok &= ck.add(f"{name}:exit_code_0", rc == 0, f"rc={rc}")

        outdir = Path(job["output_dir"])
        interrupted = (outdir / "INTERRUPTED.json").exists()
        all_ok &= ck.add(f"{name}:not_interrupted", not interrupted, "正常" if not interrupted else "INTERRUPTED")

        ckpt = Path(job["checkpoint_path"])
        now_sha = sha256_file(ckpt) if ckpt.exists() else "<missing>"
        all_ok &= ck.add(f"{name}:ckpt_unchanged", now_sha == job["checkpoint_sha256"],
                         f"{now_sha[:8]}...=={job['checkpoint_sha256'][:8]}...")

        for label, mp, want in job.get("manifest_shas", []):
            got = sha256_file(Path(mp)) if Path(mp).exists() else "<missing>"
            all_ok &= ck.add(f"{name}:{label}_manifest", got == want, f"{got[:8]}...")

        rp = Path(job["result_json"])
        if not rp.is_file():
            all_ok &= ck.add(f"{name}:result_json", False, "缺失")
            continue

        all_ok &= ck.add(f"{name}:result_json", True, f"{rp.stat().st_size}B")
        data = json.loads(rp.read_text())
        results[name] = {"job": job, "path": str(rp), "data": data, "launch": lr}

        if job["kind"] == "q1q2":
            status = data.get("status")
            all_ok &= ck.add(f"{name}:COMPLETE", status == "COMPLETE", str(status))
            n = dig(data, "provenance", "n_targets")
            all_ok &= ck.add(f"{name}:n_targets", n == job["expected_targets"], f"{n}")
            r2 = dig(data, "Q1_forecast", "full", "R2")
            rmse = dig(data, "Q1_forecast", "full", "rmse")
            all_ok &= ck.add(f"{name}:r2_finite", is_finite(r2), f"R2={r2}")
            all_ok &= ck.add(f"{name}:rmse_finite", is_finite(rmse), f"rmse={rmse}")
        else:
            role = data.get("evidence_role")
            all_ok &= ck.add(f"{name}:final", role == "final", str(role))
            n_pairs = data.get("n_pairs")
            all_ok &= ck.add(f"{name}:84pairs", n_pairs == 84, f"{n_pairs}")

    return results, all_ok


def check_historical(ck: Checks, results: dict) -> dict:
    """11,904 复现检查。"""
    if not HISTORICAL_REF.exists():
        ck.add("historical_ref", False, "缺失")
        return {"status": "no_reference"}

    ref = json.loads(HISTORICAL_REF.read_text())
    ck.add("historical_ref", True, f"{sum(1 for k in ref if not k.startswith('_'))} 指标")

    default_tol = ref.get("_tolerance", 1e-6)
    per_pattern = ref.get("_tolerances", {})

    def tol_for(path: str) -> float:
        best, best_len = default_tol, -1
        for pat, t in per_pattern.items():
            if pat in path and len(pat) > best_len:
                best, best_len = t, len(pat)
        return best

    deltas = []
    ok_all = True
    for key, want in ref.items():
        if key.startswith("_"):
            continue
        job_name, metric_path = key.split(":", 1)
        r = results.get(job_name)
        if not r:
            ok_all &= ck.add(f"repro:{key[:30]}", False, "任务缺失")
            continue

        got = dig(r["data"], *metric_path.split("."))
        if got is None:
            ok_all &= ck.add(f"repro:{key[:30]}", False, "路径缺失")
            continue

        tol = tol_for(metric_path)
        delta = abs(got - want) if isinstance(got, (int, float)) and isinstance(want, (int, float)) else None
        ok = delta is not None and delta <= tol
        delta_str = f"{delta:.2e}" if delta is not None else "N/A"
        ok_all &= ck.add(f"repro:{key[:30]}", ok, f"Δ={delta_str} tol={tol:.0e}")
        deltas.append({"key": key, "want": want, "got": got, "delta": delta, "tol": tol, "ok": ok})

    return {"status": "reproduced" if ok_all else "DRIFT_TO_DIAGNOSE", "deltas": deltas}


def build_comparison(results: dict) -> dict:
    """11,904 vs 14,880 比较。"""
    comp = {"schema": "e0_comparison_v1", "pairs": {}}

    # Val Q1
    if "gpu3_legacy11904_val_q1q2" in results and "gpu0_v14880_val_q1q2" in results:
        d11 = results["gpu3_legacy11904_val_q1q2"]["data"]
        d14 = results["gpu0_v14880_val_q1q2"]["data"]
        comp["pairs"]["validation_q1"] = {
            "11904": {"r2": dig(d11, "Q1_forecast", "full", "R2"), "rmse": dig(d11, "Q1_forecast", "full", "rmse")},
            "14880": {"r2": dig(d14, "Q1_forecast", "full", "R2"), "rmse": dig(d14, "Q1_forecast", "full", "rmse")},
        }

    # OOD-t Q1
    if "gpu4_legacy11904_oodt_q1q2" in results and "gpu1_v14880_oodt_q1q2" in results:
        d11 = results["gpu4_legacy11904_oodt_q1q2"]["data"]
        d14 = results["gpu1_v14880_oodt_q1q2"]["data"]
        comp["pairs"]["oodt_q1"] = {
            "11904": {"r2": dig(d11, "Q1_forecast", "full", "R2"), "rmse": dig(d11, "Q1_forecast", "full", "rmse")},
            "14880": {"r2": dig(d14, "Q1_forecast", "full", "R2"), "rmse": dig(d14, "Q1_forecast", "full", "rmse")},
        }

    # Q3
    if "gpu5_legacy11904_oodt_q3" in results and "gpu2_v14880_oodt_q3" in results:
        d11 = results["gpu5_legacy11904_oodt_q3"]["data"]
        d14 = results["gpu2_v14880_oodt_q3"]["data"]
        df11 = dig(d11, "models", "exclusive", "q3_donor_fidelity") or {}
        df14 = dig(d14, "models", "exclusive", "q3_donor_fidelity") or {}
        comp["pairs"]["oodt_q3"] = {
            "11904": {
                "n_pairs": d11.get("n_pairs"),
                "endpoint_fidelity_status": df11.get("endpoint_fidelity_status"),
                "hotdry_enhancement_status": df11.get("hotdry_enhancement_status"),
                "overall_status": df11.get("overall_status"),
                "evidence_role": df11.get("evidence_role"),
            },
            "14880": {
                "n_pairs": d14.get("n_pairs"),
                "endpoint_fidelity_status": df14.get("endpoint_fidelity_status"),
                "hotdry_enhancement_status": df14.get("hotdry_enhancement_status"),
                "overall_status": df14.get("overall_status"),
                "evidence_role": df14.get("evidence_role"),
            },
        }

    comp["interpretation"] = [
        "0.01 仅为描述性阈值，非选择门",
        "14,880 已固定为后续 anchor",
        "不根据 OOD 结果回选",
        "Q3 hot-dry FAIL 是科学结果",
    ]

    comp["interpretation"] = [
        "0.01 仅为描述性阈值，非选择门",
        "14,880 已固定为后续 anchor",
        "不根据 OOD 结果回选",
        "Q3 hot-dry FAIL 是科学结果",
    ]

    return comp


def main() -> int:
    print("=== E0 Retry Attempt 验收 ===")
    ck = Checks()

    print("\n--- 六项任务验收 ---")
    results, jobs_ok = check_six_jobs(ck)

    print("\n--- 11,904 历史复现 ---")
    repro = check_historical(ck, results)

    print("\n--- 比较 ---")
    comp = build_comparison(results)

    accepted = jobs_ok and (repro["status"] == "reproduced" or repro["status"] == "no_reference")

    report = {
        "schema": "e0_acceptance_report_v1",
        "accepted": accepted,
        "checks": ck.rows,
        "failures": ck.failures,
        "reproduction": repro,
    }

    print(f"\n{'='*60}")
    print(f"验收结果: {'ACCEPTED' if accepted else 'BLOCKED'}")
    print(f"失败项: {len(ck.failures)}")

    # 写入
    (RETRY / "e0_acceptance_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    (RETRY / "e0_comparison_11904_vs_14880.json").write_text(json.dumps(comp, indent=1, ensure_ascii=False))

    print(f"\n生成:")
    print(f"  - e0_acceptance_report.json")
    print(f"  - e0_comparison_11904_vs_14880.json")

    return 0 if accepted else 2


if __name__ == "__main__":
    sys.exit(main())
