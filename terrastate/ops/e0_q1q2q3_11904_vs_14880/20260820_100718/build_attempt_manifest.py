#!/usr/bin/env python3
"""生成 attempt-specific manifest，记录父 manifest SHA 和本次 retry 的输出路径。"""
import hashlib
import json
import sys
from pathlib import Path

RETRY = Path(__file__).parent
TS_ROOT = RETRY.parents[3]
PARENT_MANIFEST = RETRY.parent / "20260818_154859" / "launch_manifest.json"

CKPT_14880 = "/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/a5/a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f.pt"
CKPT_11904 = "/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/64/644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd.pt"
SHA_14880 = "a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f"
SHA_11904 = "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    if not PARENT_MANIFEST.exists():
        print(f"ERROR: 父 manifest 不存在: {PARENT_MANIFEST}", file=sys.stderr)
        return 2

    parent_sha = sha256_file(PARENT_MANIFEST)
    parent = json.loads(PARENT_MANIFEST.read_text())

    # 验证父 manifest SHA
    expected_parent = "500e5031335c366ed06819dd9af8679dcf0318301d559aa7bfd573688c6cdd08"
    if parent_sha != expected_parent:
        print(f"ERROR: 父 manifest SHA 不匹配", file=sys.stderr)
        print(f"  期望: {expected_parent}", file=sys.stderr)
        print(f"  实际: {parent_sha}", file=sys.stderr)
        return 2

    # 读取 launch record 获取实际执行信息
    launch_rec = json.loads((RETRY / "e0_launch_record.json").read_text())
    jobs_by_name = {j["name"]: j for j in launch_rec["jobs"]}

    # 映射：逻辑任务名 -> 物理 GPU
    gpu_map = {j["name"]: j["physical_gpu"] for j in launch_rec["jobs"]}

    # 从父 manifest 继承科学参数，只改变输出路径和执行元数据
    retry_jobs = []
    for parent_job in parent["jobs"]:
        name = parent_job["name"]
        if name not in jobs_by_name:
            print(f"ERROR: 父任务 {name} 在 launch_record 中缺失", file=sys.stderr)
            return 2

        launch_info = jobs_by_name[name]

        # 构造 retry 任务记录
        retry_job = {
            "name": name,
            "kind": parent_job["kind"],
            "checkpoint_path": parent_job["checkpoint_path"],
            "checkpoint_sha256": parent_job["checkpoint_sha256"],
            "checkpoint_logical_id": (
                "terrastate/v2/verified-resume14880@v1" if "14880" in name
                else "terrastate/v2/legacy-boundary11904@v1"
            ),
            "evaluator": parent_job["evaluator"],
            "evaluator_sha256": parent_job["evaluator_sha256"],
            "manifest_shas": parent_job.get("manifest_shas", []),
            "protocol_dir": parent_job.get("protocol_dir"),
            "output_dir": str(RETRY / "runs" / name),
            "log": str(RETRY / "logs" / f"{name}.log"),
            "result_json": str(RETRY / "runs" / name / (
                "state_contract_exclusive.json" if parent_job["kind"] == "q1q2"
                else "extreme_state_audit.json"
            )),
            "expected_targets": parent_job.get("expected_targets"),
            "expected_pairs": parent_job.get("expected_pairs"),
            "physical_gpu": gpu_map[name],
            "gpu_uuid": "not_persisted",
            "hostname": "csy-zg01-gnode39",
            "exit_code": launch_info["exit_code"],
        }
        retry_jobs.append(retry_job)

    # 构造 attempt manifest
    manifest = {
        "schema": "e0_attempt_manifest_v1",
        "retry_dir": str(RETRY),
        "parent_manifest": {
            "path": str(PARENT_MANIFEST),
            "sha256": parent_sha,
        },
        "note": "本 retry 继承父 manifest 的科学参数；仅改变输出目录、物理 GPU 和执行元数据",
        "artifacts": parent["artifacts"],
        "frozen_inputs": parent["frozen_inputs"],
        "gpu_policy": {
            "original": parent["gpu_policy"],
            "retry_physical_gpus": [2, 4, 5, 6],
            "logical_to_physical_mapping": gpu_map,
        },
        "forbidden": parent["forbidden"],
        "excluded_invalid_attempts": [
            {"dir": "runs/gpu2_v14880_oodt_q1q2", "reason": "INVALID_PARTIAL_ORCHESTRATION - 早期编排错误"},
            {"dir": "runs/gpu5_v14880_val_q1q2", "reason": "INVALID_PARTIAL_ORCHESTRATION - 早期编排错误"},
            {"dir": "runs/gpu6_legacy11904_val_q1q2", "reason": "INVALID_PARTIAL_ORCHESTRATION - 早期编排错误"},
        ],
        "jobs": retry_jobs,
    }

    # 写入
    out_path = RETRY / "attempt_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False))

    # SHA sidecar
    manifest_sha = sha256_file(out_path)
    (RETRY / "attempt_manifest.sha256").write_text(f"{manifest_sha}  attempt_manifest.json\n")

    print(f"✓ 生成 {out_path.name}")
    print(f"  SHA-256: {manifest_sha}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
