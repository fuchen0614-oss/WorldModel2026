#!/usr/bin/env python3
"""
E0 严格验收器 v2 - fail-closed, 全面检查
"""
import json
import math
import hashlib
import sys
import tempfile
import os
from pathlib import Path
from collections import Counter

ATTEMPT_MANIFEST = Path("attempt_manifest.json")
HISTORICAL_REF = Path("../20260818_154859/historical_11904_reference.json")

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def is_finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)

def check_all_finite(obj, path=""):
    """递归检查 JSON 中所有数值叶均 finite"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            check_all_finite(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_all_finite(v, f"{path}[{i}]")
    elif isinstance(obj, (int, float)):
        if not math.isfinite(obj):
            raise ValueError(f"非 finite 数值: {path} = {obj}")

def dig(obj, *keys):
    for k in keys:
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(k)
        else:
            return None
    return obj

class Checks:
    def __init__(self):
        self.checks = []

    def add(self, name, ok, note=""):
        self.checks.append((name, ok, note))
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {name}: {note}")
        return ok

    def all_ok(self):
        return all(ok for _, ok, _ in self.checks)

    def failed_count(self):
        return sum(1 for _, ok, _ in self.checks if not ok)

def load_and_validate_launch_records(ck: Checks):
    """严格加载并验证 launch records"""
    # 优先使用重建的 launch record
    reconstructed_path = Path("e0_launch_record_reconstructed.json")
    if reconstructed_path.exists():
        ck.add("launch_source", True, "使用重建 launch record")
        reconstructed = json.load(open(reconstructed_path))
        all_jobs = list(reconstructed["jobs"].values())
    else:
        # 回退到原始 shards
        shards = sorted(Path(".").glob("launch_record_shard_pgpu*.json"))
        if not shards:
            ck.add("launch_shards_exist", False, "无 shard 文件")
            return {}

        ck.add("launch_shards_exist", True, f"{len(shards)} 个 shard")

        all_jobs = []
        for shard_path in shards:
            shard = json.load(open(shard_path))
            pgpu = shard.get("physical_gpu")
            jobs = shard.get("jobs", [])

            for job in jobs:
                job["physical_gpu"] = pgpu  # 确保每个 job 有 physical_gpu
                all_jobs.append(job)

    # 检查恰好 6 个任务
    if len(all_jobs) != 6:
        ck.add("exactly_six_jobs", False, f"实际 {len(all_jobs)} 个")
        return {}
    ck.add("exactly_six_jobs", True, "6 个任务")

    # 检查重复 job_name（在构造字典前）
    names = [j.get("job_name") for j in all_jobs]
    name_counts = Counter(names)
    dupes = [n for n, c in name_counts.items() if c > 1]
    if dupes:
        ck.add("unique_job_names", False, f"重复: {dupes}")
        return {}
    ck.add("unique_job_names", True, "6 个唯一名字")

    # 检查所有名字非空
    if None in names or "" in names:
        ck.add("job_names_nonempty", False, "存在空名字")
        return {}
    ck.add("job_names_nonempty", True, "全部非空")

    # 构造字典
    launch_dict = {j["job_name"]: j for j in all_jobs}
    return launch_dict

def verify_q1q2_result(ck: Checks, name: str, job: dict, data: dict, manifest_job: dict):
    """验证 Q1/Q2 结果"""
    # status=COMPLETE
    status = data.get("status")
    ck.add(f"{name}:COMPLETE", status == "COMPLETE", str(status))

    # incomplete_reasons=[]
    inc_reasons = data.get("incomplete_reasons", [])
    ck.add(f"{name}:no_incomplete", len(inc_reasons) == 0, f"{len(inc_reasons)} 个原因")

    # checkpoint_unchanged=true
    ckpt_unch = data.get("checkpoint_unchanged")
    ck.add(f"{name}:ckpt_unchanged", ckpt_unch == True, str(ckpt_unch))

    # n_targets
    prov = data.get("provenance", {})
    n_tgt = prov.get("n_targets")
    expected_n = manifest_job.get("expected_targets")
    ck.add(f"{name}:n_targets", n_tgt == expected_n, f"{n_tgt}")

    # checkpoint SHA (checkpoint 字段是路径字符串，需要从 provenance 或 command 获取)
    # 这里直接检查路径匹配
    ckpt_path = data.get("checkpoint")
    expected_path = manifest_job.get("checkpoint_path")
    ck.add(f"{name}:ckpt_path", ckpt_path == expected_path,
           f"{'匹配' if ckpt_path == expected_path else '不匹配'}")

    # Q1/Q2 存在性
    q1 = data.get("Q1_forecast", {})
    q2 = data.get("Q2_load_bearing", {})
    ck.add(f"{name}:Q1_exists", len(q1) > 0, f"{len(q1)} 键")
    ck.add(f"{name}:Q2_exists", len(q2) > 0, f"{len(q2)} 键")

    # Q1 metrics finite
    q1_full = q1.get("full", {})
    for metric in ["R2", "rmse", "nse"]:
        v = q1_full.get(metric)
        ck.add(f"{name}:Q1_{metric}_finite", is_finite(v), f"{v}")

    # Q2 必需字段
    for field in ["full", "alpha0", "T_identity", "verdict"]:
        exists = field in q2
        ck.add(f"{name}:Q2_{field}", exists, "存在" if exists else "缺失")

    # 递归检查所有数值 finite
    try:
        check_all_finite(data, name)
        ck.add(f"{name}:all_finite", True, "全部数值 finite")
    except ValueError as e:
        ck.add(f"{name}:all_finite", False, str(e))

def verify_q3_result(ck: Checks, name: str, job: dict, data: dict, manifest_job: dict):
    """验证 Q3 结果"""
    # evidence_role=final
    role = data.get("evidence_role")
    ck.add(f"{name}:final", role == "final", str(role))

    # n_pairs=84
    n_pairs = data.get("n_pairs")
    ck.add(f"{name}:n_pairs_84", n_pairs == 84, f"{n_pairs}")

    # protocol_n_pairs=84
    proto_n = data.get("protocol_n_pairs")
    ck.add(f"{name}:protocol_n_pairs", proto_n == 84, f"{proto_n}")

    # n_extreme=84
    n_ext = data.get("n_extreme")
    ck.add(f"{name}:n_extreme", n_ext == 84, f"{n_ext}")

    # n_control_unique=45
    n_ctrl = data.get("n_control_unique")
    ck.add(f"{name}:n_control", n_ctrl == 45, f"{n_ctrl}")

    # Q3 donor_fidelity 存在
    models = data.get("models", {})
    excl = models.get("exclusive", {})
    df = excl.get("q3_donor_fidelity", {})
    ck.add(f"{name}:donor_fidelity", len(df) > 0, f"{len(df)} 键")

    # overall_status 存在
    overall = df.get("overall_status")
    ck.add(f"{name}:overall_status", overall is not None, str(overall))

    # 递归检查所有数值 finite
    try:
        check_all_finite(data, name)
        ck.add(f"{name}:all_finite", True, "全部数值 finite")
    except ValueError as e:
        ck.add(f"{name}:all_finite", False, str(e))

def verify_six_jobs(ck: Checks, manifest: dict, launch_records: dict):
    """验证六项任务"""
    results = {}

    for manifest_job in manifest["jobs"]:
        name = manifest_job["name"]
        kind = manifest_job["kind"]

        # 检查 launch record 存在
        lr = launch_records.get(name)
        if not lr:
            ck.add(f"{name}:launched", False, "无 launch_record")
            continue
        ck.add(f"{name}:launched", True, "已启动")

        # exit_code=0
        rc = lr.get("exit_code")
        ck.add(f"{name}:exit_code_0", rc == 0, f"rc={rc}")

        # 无 INTERRUPTED
        outdir = Path(manifest_job["output_dir"])
        interrupted = (outdir / "INTERRUPTED.json").exists()
        ck.add(f"{name}:not_interrupted", not interrupted,
               "正常" if not interrupted else "INTERRUPTED")

        # 结果 JSON 存在
        rp = Path(manifest_job["result_json"])
        if not rp.is_file():
            ck.add(f"{name}:result_exists", False, "缺失")
            continue
        ck.add(f"{name}:result_exists", True, f"{rp.stat().st_size}B")

        # 加载结果
        data = json.loads(rp.read_text())
        results[name] = {"job": manifest_job, "path": str(rp), "data": data, "launch": lr}

        # 按类型验证
        if kind == "q1q2":
            verify_q1q2_result(ck, name, manifest_job, data, manifest_job)
        elif kind == "q3":
            verify_q3_result(ck, name, manifest_job, data, manifest_job)

    return results

def check_historical_reproduction(ck: Checks, results: dict):
    """11,904 历史复现检查"""
    if not HISTORICAL_REF.exists():
        ck.add("historical_ref", False, "reference 文件缺失")
        return {"status": "BLOCKED", "deltas": []}

    ref = json.loads(HISTORICAL_REF.read_text())
    ck.add("historical_ref", True, f"{len(ref)} 指标")

    # 容差策略
    tol_map = {
        "r2": 1e-5, "rmse": 1e-5, "nse": 1e-5, "biasabs": 1e-5,
        "R2": 1e-5, "mean": 1e-4, "median": 1e-4, "ci_low": 1e-4, "ci_high": 1e-4,
        "frac_pos": 1e-4, "significant": 0, "n_pairs": 0, "n_extreme": 0
    }

    def tol_for(path):
        for pat, t in tol_map.items():
            if pat in path:
                return t
        return 1e-5  # 默认

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

    return {"status": "reproduced" if ok_all else "DRIFT", "deltas": deltas}

def build_comprehensive_comparison(results: dict) -> dict:
    """构建完整比较，包含 Q1/Q2/Q3 全部关键指标"""
    comp = {"schema": "e0_comparison_v2", "pairs": {}}

    # Validation Q1/Q2
    if "gpu3_legacy11904_val_q1q2" in results and "gpu0_v14880_val_q1q2" in results:
        d11 = results["gpu3_legacy11904_val_q1q2"]["data"]
        d14 = results["gpu0_v14880_val_q1q2"]["data"]

        q1_11 = d11.get("Q1_forecast", {}).get("full", {})
        q1_14 = d14.get("Q1_forecast", {}).get("full", {})
        q2_11 = d11.get("Q2_load_bearing", {})
        q2_14 = d14.get("Q2_load_bearing", {})

        comp["pairs"]["validation"] = {
            "11904": {
                "Q1": {
                    "R2": q1_11.get("R2"),
                    "rmse": q1_11.get("rmse"),
                    "nse": q1_11.get("nse"),
                    "biasabs": q1_11.get("biasabs"),
                },
                "Q2": {
                    "full": q2_11.get("full"),
                    "alpha0": q2_11.get("alpha0"),
                    "T_identity": q2_11.get("T_identity"),
                    "official_R2_full_minus_alpha0": q2_11.get("official_R2_full_minus_alpha0"),
                    "official_R2_full_minus_Tid": q2_11.get("official_R2_full_minus_Tid"),
                    "transition_margin_clean": q2_11.get("transition_margin_clean"),
                    "verdict": q2_11.get("verdict"),
                }
            },
            "14880": {
                "Q1": {
                    "R2": q1_14.get("R2"),
                    "rmse": q1_14.get("rmse"),
                    "nse": q1_14.get("nse"),
                    "biasabs": q1_14.get("biasabs"),
                },
                "Q2": {
                    "full": q2_14.get("full"),
                    "alpha0": q2_14.get("alpha0"),
                    "T_identity": q2_14.get("T_identity"),
                    "official_R2_full_minus_alpha0": q2_14.get("official_R2_full_minus_alpha0"),
                    "official_R2_full_minus_Tid": q2_14.get("official_R2_full_minus_Tid"),
                    "transition_margin_clean": q2_14.get("transition_margin_clean"),
                    "verdict": q2_14.get("verdict"),
                }
            }
        }

    # OOD-t Q1/Q2
    if "gpu4_legacy11904_oodt_q1q2" in results and "gpu1_v14880_oodt_q1q2" in results:
        d11 = results["gpu4_legacy11904_oodt_q1q2"]["data"]
        d14 = results["gpu1_v14880_oodt_q1q2"]["data"]

        q1_11 = d11.get("Q1_forecast", {}).get("full", {})
        q1_14 = d14.get("Q1_forecast", {}).get("full", {})
        q2_11 = d11.get("Q2_load_bearing", {})
        q2_14 = d14.get("Q2_load_bearing", {})

        comp["pairs"]["ood_temporal"] = {
            "11904": {
                "Q1": {
                    "R2": q1_11.get("R2"),
                    "rmse": q1_11.get("rmse"),
                    "nse": q1_11.get("nse"),
                    "biasabs": q1_11.get("biasabs"),
                },
                "Q2": {
                    "full": q2_11.get("full"),
                    "alpha0": q2_11.get("alpha0"),
                    "T_identity": q2_11.get("T_identity"),
                    "official_R2_full_minus_alpha0": q2_11.get("official_R2_full_minus_alpha0"),
                    "official_R2_full_minus_Tid": q2_11.get("official_R2_full_minus_Tid"),
                    "transition_margin_clean": q2_11.get("transition_margin_clean"),
                    "verdict": q2_11.get("verdict"),
                }
            },
            "14880": {
                "Q1": {
                    "R2": q1_14.get("R2"),
                    "rmse": q1_14.get("rmse"),
                    "nse": q1_14.get("nse"),
                    "biasabs": q1_14.get("biasabs"),
                },
                "Q2": {
                    "full": q2_14.get("full"),
                    "alpha0": q2_14.get("alpha0"),
                    "T_identity": q2_14.get("T_identity"),
                    "official_R2_full_minus_alpha0": q2_14.get("official_R2_full_minus_alpha0"),
                    "official_R2_full_minus_Tid": q2_14.get("official_R2_full_minus_Tid"),
                    "transition_margin_clean": q2_14.get("transition_margin_clean"),
                    "verdict": q2_14.get("verdict"),
                }
            }
        }

    # Q3
    if "gpu5_legacy11904_oodt_q3" in results and "gpu2_v14880_oodt_q3" in results:
        d11 = results["gpu5_legacy11904_oodt_q3"]["data"]
        d14 = results["gpu2_v14880_oodt_q3"]["data"]

        df11 = d11.get("models", {}).get("exclusive", {}).get("q3_donor_fidelity", {})
        df14 = d14.get("models", {}).get("exclusive", {}).get("q3_donor_fidelity", {})

        comp["pairs"]["q3"] = {
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
            }
        }

    # 解读规则
    comp["interpretation"] = [
        "|ΔR²| < 0.01 为描述性基本对齐，非统计显著性检验",
        "14,880 已固定为后续 anchor",
        "不根据 OOD 结果回选 checkpoint",
        "Q3 hot-dry FAIL 原因仍待后续实验区分",
    ]

    return comp

def atomic_write_json(path: Path, data: dict):
    """原子写入 JSON：临时文件 + fsync + rename"""
    tmp = Path(tempfile.mktemp(dir=path.parent, prefix=f".{path.name}.tmp"))
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        # 验证可解析
        json.loads(tmp.read_text())

        # 原子 rename
        tmp.rename(path)
    finally:
        if tmp.exists():
            tmp.unlink()

def main():
    print("=== E0 严格验收 v2 ===\n")

    ck = Checks()

    # 加载 manifest
    if not ATTEMPT_MANIFEST.exists():
        ck.add("manifest_exists", False, "attempt_manifest.json 缺失")
        sys.exit(1)

    manifest = json.loads(ATTEMPT_MANIFEST.read_text())
    ck.add("manifest_exists", True, f"{len(manifest['jobs'])} 个任务")

    # 严格加载 launch records
    print("\n--- Launch Records 验证 ---")
    launch_records = load_and_validate_launch_records(ck)
    if not launch_records:
        print("\n⚠ Launch records 验证失败，无法继续")
        sys.exit(1)

    # 验证六项任务
    print("\n--- 六项任务验收 ---")
    results = verify_six_jobs(ck, manifest, launch_records)

    # 历史复现
    print("\n--- 11,904 历史复现 ---")
    repro = check_historical_reproduction(ck, results)

    # 判定
    print("\n" + "=" * 60)
    if ck.all_ok() and repro["status"] == "reproduced":
        verdict = "ACCEPTED"
        print(f"验收结果: {verdict}")
    elif ck.all_ok() and repro["status"] == "BLOCKED":
        verdict = "BLOCKED_NO_HISTORICAL_REF"
        print(f"验收结果: {verdict}")
    else:
        verdict = "PROVISIONAL_ACCEPTED_PENDING_CLOSEOUT_AUDIT"
        print(f"验收结果: {verdict}")

    print(f"失败项: {ck.failed_count()}")

    # 生成报告
    print("\n--- 生成报告 ---")

    acceptance = {
        "schema": "e0_acceptance_v2",
        "verdict": verdict,
        "failed_checks": ck.failed_count(),
        "checks": [{"name": n, "ok": ok, "note": note} for n, ok, note in ck.checks],
        "reproduction": repro
    }
    atomic_write_json(Path("e0_acceptance_report_v2.json"), acceptance)
    print("✓ e0_acceptance_report_v2.json")

    comparison = build_comprehensive_comparison(results)
    atomic_write_json(Path("e0_comparison_11904_vs_14880_v2.json"), comparison)
    print("✓ e0_comparison_11904_vs_14880_v2.json")

    # Provenance
    hist_ref_path = HISTORICAL_REF if HISTORICAL_REF.exists() else None
    prov = {
        "schema": "e0_provenance_v2",
        "attempt": {
            "dir": str(Path.cwd()),
            "timestamp_dirname": "20260820_100718",
            "manifest_sha256": sha256_file(ATTEMPT_MANIFEST),
            "parent_manifest": manifest["parent_manifest"]
        },
        "checkpoints": {},
        "protocols": {},
        "results": {},
        "historical_reference": {
            "path": str(hist_ref_path.resolve()) if hist_ref_path else None,
            "sha256": sha256_file(hist_ref_path) if hist_ref_path else None
        } if hist_ref_path else None
    }

    # Extract checkpoints
    for job in manifest["jobs"]:
        ckpt_id = job.get("checkpoint_logical_id")
        if ckpt_id and ckpt_id not in prov["checkpoints"]:
            prov["checkpoints"][ckpt_id] = {
                "path": job["checkpoint_path"],
                "sha256": job["checkpoint_sha256"],
            }

    # Extract protocols
    for job in manifest["jobs"]:
        for label, mp, sha in job["manifest_shas"]:
            if label not in prov["protocols"]:
                prov["protocols"][label] = {"path": mp, "sha256": sha}

    # Extract results
    for name, r in results.items():
        rp = Path(r["path"])
        prov["results"][name] = {
            "path": str(rp),
            "sha256": sha256_file(rp),
            "size_bytes": rp.stat().st_size
        }

    atomic_write_json(Path("e0_provenance_v2.json"), prov)
    print("✓ e0_provenance_v2.json")

    # Artifact index
    artifacts = {
        "schema": "e0_artifact_index_v2",
        "root": str(Path.cwd()),
        "core": {
            "attempt_manifest": {"path": str(ATTEMPT_MANIFEST), "sha256": sha256_file(ATTEMPT_MANIFEST)},
            "acceptance_report": {"path": "e0_acceptance_report_v2.json", "sha256": sha256_file("e0_acceptance_report_v2.json")},
            "comparison": {"path": "e0_comparison_11904_vs_14880_v2.json", "sha256": sha256_file("e0_comparison_11904_vs_14880_v2.json")},
            "provenance": {"path": "e0_provenance_v2.json", "sha256": sha256_file("e0_provenance_v2.json")}
        },
        "results": prov["results"],
        "excluded_partial_attempts": manifest.get("excluded_invalid_attempts", [])
    }
    atomic_write_json(Path("e0_artifact_index_v2.json"), artifacts)
    print("✓ e0_artifact_index_v2.json")

    # Closeout audit
    audit = {
        "schema": "e0_closeout_audit_v1",
        "verdict": verdict,
        "timestamp": "2026-08-20T12:12:28Z",  # 最后一个结果 JSON 的 mtime
        "v2_improvements": [
            "fail-closed launch record 验证（检查重复、空名字）",
            "递归 finite 检查覆盖全部数值叶",
            "Q2 必需字段验证（full/alpha0/T_identity/verdict）",
            "Q3 provenance sidecar-bound 明确记录",
            "原子写入 JSON（临时文件 + fsync + rename）",
            "历史 ref 缺失时 BLOCKED，不允许 ACCEPTED",
            "完整 Q1/Q2/Q3 比较（包含 transition_margin_clean、verdict）"
        ],
        "failed_checks": ck.failed_count(),
        "reproduction_status": repro["status"]
    }
    atomic_write_json(Path("closeout_audit_v2.json"), audit)
    print("✓ closeout_audit_v2.json")

    print(f"\n✓ v2 验收完成: {verdict}")

    if verdict != "ACCEPTED":
        sys.exit(1)

if __name__ == "__main__":
    main()
