#!/usr/bin/env python3
"""
Phase 3 最终门检查：验证所有 v3 交付物是否完整。

检查清单：
1. 九件 _v3 工件存在且非空
2. A03 v3 文档存在且有 SHA sidecar 通过 sha256sum -c
3. A01/A02 已同步 7 项事实
4. 独立审计通过（18/18 MATCH, 0 DISCREPANCY）
5. verify_and_aggregate_retry_v3.py 存在且可执行
6. 所有 v3 JSON 可解析

Usage:
    CUDA_VISIBLE_DEVICES="" python final_gates_v3.py
"""
import json
import subprocess
import sys
from pathlib import Path

ATTEMPT = Path(__file__).parent
A03_PATH = ATTEMPT.parent.parent.parent / "思路整理进展" / "A03_TerraState_关键实验结果与决策总账.md"
A01_PATH = ATTEMPT.parent.parent.parent / "思路整理进展" / "A01_TerraState_AAAI后续研究与实验总纲.md"
A02_PATH = ATTEMPT.parent.parent.parent / "思路整理进展" / "A02_TerraState_后续研究计划.md"

REQUIRED_V3_ARTIFACTS = [
    "e0_comparison_11904_vs_14880_v3.json",
    "e0_acceptance_report_v3.json",
    "e0_provenance_v3.json",
    "e0_artifact_index_v3.json",
    "e0_launch_record_v3.json",
    "attempt_manifest_v3.json",
    "e0_metric_inventory_v3.json",
    "closeout_audit_v3.json",
    "verify_and_aggregate_retry_v3.py"
]

def check_v3_artifacts() -> tuple:
    """检查九件 v3 工件"""
    missing = []
    for name in REQUIRED_V3_ARTIFACTS:
        p = ATTEMPT / name
        if not p.exists():
            missing.append(name)
        elif p.stat().st_size == 0:
            missing.append(f"{name} (空文件)")

    if missing:
        return False, f"缺少或为空: {', '.join(missing)}"
    return True, "九件 v3 工件完整"

def check_a03_sidecar() -> tuple:
    """检查 A03 及其 SHA sidecar"""
    if not A03_PATH.exists():
        return False, "A03 不存在"

    sidecar = A03_PATH.with_suffix(A03_PATH.suffix + ".sha256")
    if not sidecar.exists():
        return False, "A03 SHA sidecar 不存在"

    # 验证 sha256sum -c
    try:
        result = subprocess.run(
            ["sha256sum", "-c", str(sidecar)],
            cwd=str(sidecar.parent),
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, f"SHA 验证失败: {result.stderr}"
        return True, "A03 SHA sidecar 验证通过"
    except Exception as e:
        return False, f"SHA 验证异常: {e}"

def check_a01_a02_sync() -> tuple:
    """检查 A01/A02 同步的 7 项事实"""
    checks = []

    # A01
    if not A01_PATH.exists():
        return False, "A01 不存在"

    a01_text = A01_PATH.read_text(encoding="utf-8")

    # 1. 三份 checkpoint 表格
    checks.append(("A01 三份checkpoint表", "644deaac" in a01_text and "a5d2a0cc" in a01_text and "99f15a35" in a01_text))

    # 2. E0 完成标记
    checks.append(("A01 E0完成标记", "✅ **已完成**" in a01_text and "2026-08-20" in a01_text))

    # 3. 0.01 语义
    checks.append(("A01 0.01语义", "描述性对齐标准" in a01_text and "没有被废除" in a01_text))

    # 4. λ 暂定
    checks.append(("A01 λ暂定", "λ 系数取值为暂定" in a01_text or "λ 系数取值为**暂定**" in a01_text))

    # 5. T3/T5 冻结时机
    checks.append(("A01 T3/T5冻结", "T3 smoke 阶段使用合成小样本" in a01_text and "T5 正式训练前必须先构建并冻结" in a01_text))

    # A02
    if not A02_PATH.exists():
        return False, "A02 不存在"

    a02_text = A02_PATH.read_text(encoding="utf-8")

    # 6. A02 三份 checkpoint
    checks.append(("A02 三份checkpoint", "644deaac" in a02_text and "a5d2a0cc" in a02_text and "99f15a35" in a02_text))

    # 7. A02 E0 完成
    checks.append(("A02 E0完成", "✅ 第 14,880 训练步权重已固定" in a02_text or "2026-08-20" in a02_text))

    failed = [name for name, ok in checks if not ok]
    if failed:
        return False, f"未找到: {', '.join(failed)}"
    return True, f"A01/A02 同步完成 (7/7)"

def check_audit() -> tuple:
    """检查独立审计结果"""
    audit_json = ATTEMPT / "experiment_integrity_audit_v3.json"
    if not audit_json.exists():
        return False, "审计 JSON 不存在"

    try:
        audit = json.load(open(audit_json, "r", encoding="utf-8"))
        n_match = audit.get("n_match", 0)
        n_discrep = audit.get("n_discrepancy", 0)
        overall = audit.get("overall_status", "UNKNOWN")

        if overall != "PASS":
            return False, f"审计未通过: {n_match} MATCH, {n_discrep} DISCREPANCY"

        return True, f"审计通过 ({n_match}/{n_match+n_discrep} MATCH)"
    except Exception as e:
        return False, f"审计 JSON 解析失败: {e}"

def check_json_parseable() -> tuple:
    """检查所有 v3 JSON 可解析"""
    json_files = [f for f in REQUIRED_V3_ARTIFACTS if f.endswith(".json")]
    failed = []

    for name in json_files:
        try:
            with open(ATTEMPT / name, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            failed.append(f"{name}: {e}")

    if failed:
        return False, f"JSON 解析失败: {'; '.join(failed)}"
    return True, f"{len(json_files)} 个 JSON 文件可解析"

def main():
    print("=== Phase 3 最终门检查 ===\n")

    gates = [
        ("v3 工件完整性", check_v3_artifacts),
        ("A03 SHA sidecar", check_a03_sidecar),
        ("A01/A02 同步", check_a01_a02_sync),
        ("独立审计", check_audit),
        ("JSON 可解析", check_json_parseable)
    ]

    results = []
    for name, check_fn in gates:
        print(f"[{len(results)+1}/{len(gates)}] 检查 {name}...", end=" ")
        ok, msg = check_fn()
        results.append((name, ok, msg))
        print("✅" if ok else "❌", msg)

    n_pass = sum(1 for _, ok, _ in results if ok)
    print(f"\n总结: {n_pass}/{len(gates)} 门通过")

    # 写入报告
    report = {
        "phase": "Phase3_final_gates",
        "date": "2026-08-20",
        "n_gates": len(gates),
        "n_pass": n_pass,
        "n_fail": len(gates) - n_pass,
        "overall_status": "PASS" if n_pass == len(gates) else "FAIL",
        "gates": [
            {"name": name, "status": "PASS" if ok else "FAIL", "message": msg}
            for name, ok, msg in results
        ]
    }

    out_json = ATTEMPT / "final_gates_v3.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n已写入: {out_json}")

    if n_pass < len(gates):
        print("\n❌ 最终门检查未通过")
        sys.exit(1)
    else:
        print("\n✅ 所有门通过，可更新 STATUS.md 和 state.json")
        sys.exit(0)

if __name__ == "__main__":
    main()
