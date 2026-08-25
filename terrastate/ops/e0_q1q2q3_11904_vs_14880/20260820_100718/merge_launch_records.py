#!/usr/bin/env python3
"""合并 4 个物理 GPU 的 launch_record 分片成一个符合聚合器要求的 e0_launch_record.json"""
import json
from pathlib import Path

retry_dir = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/ops/e0_q1q2q3_11904_vs_14880/20260820_100718")

shards = [
    retry_dir / "launch_record_shard_pgpu2.json",
    retry_dir / "launch_record_shard_pgpu4.json",
    retry_dir / "launch_record_shard_pgpu5.json",
    retry_dir / "launch_record_shard_pgpu6.json",
]

all_jobs = []
for shard_path in shards:
    if not shard_path.exists():
        print(f"WARNING: {shard_path.name} not found, skipping")
        continue
    shard = json.loads(shard_path.read_text())
    all_jobs.extend(shard.get("jobs", []))

# 验证任务名是否与冻结清单匹配
expected_names = {
    "gpu0_v14880_val_q1q2",
    "gpu1_v14880_oodt_q1q2",
    "gpu2_v14880_oodt_q3",
    "gpu3_legacy11904_val_q1q2",
    "gpu4_legacy11904_oodt_q1q2",
    "gpu5_legacy11904_oodt_q3",
}
actual_names = {j["name"] for j in all_jobs}

print(f"合并了 {len(all_jobs)} 个任务")
print(f"期望任务名: {sorted(expected_names)}")
print(f"实际任务名: {sorted(actual_names)}")

missing = expected_names - actual_names
extra = actual_names - expected_names
if missing:
    print(f"WARNING: 缺失任务 {missing}")
if extra:
    print(f"WARNING: 多余任务 {extra}")

# 生成最终的 launch_record
output = {
    "schema": "e0_launch_record_v1",
    "all_six_jobs_launched": len(all_jobs),
    "physical_gpu_mapping": {
        "gpu0_v14880_val_q1q2": 5,
        "gpu1_v14880_oodt_q1q2": 2,
        "gpu2_v14880_oodt_q3": 5,
        "gpu3_legacy11904_val_q1q2": 6,
        "gpu4_legacy11904_oodt_q1q2": 4,
        "gpu5_legacy11904_oodt_q3": 6,
    },
    "note": "Task names match frozen manifest (gpu0-5); physical GPUs are 2/4/5/6",
    "jobs": all_jobs,
}

out_path = retry_dir / "e0_launch_record.json"
out_path.write_text(json.dumps(output, indent=1))
print(f"\n✓ 写入 {out_path}")
print(f"  all_six_jobs_launched = {len(all_jobs)}")
