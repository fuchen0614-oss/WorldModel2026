#!/usr/bin/env python3
"""严格合并 launch_record 分片，fail-closed 验证。"""
import hashlib
import json
import sys
from pathlib import Path

RETRY = Path(__file__).parent
EXPECTED_JOBS = {
    "gpu0_v14880_val_q1q2", "gpu1_v14880_oodt_q1q2", "gpu2_v14880_oodt_q3",
    "gpu3_legacy11904_val_q1q2", "gpu4_legacy11904_oodt_q1q2", "gpu5_legacy11904_oodt_q3",
}

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    shards = sorted(RETRY.glob("launch_record_shard_pgpu*.json"))
    if not shards:
        print("ERROR: 无 shard 文件", file=sys.stderr)
        return 2

    all_jobs = []
    shard_meta = []
    for sp in shards:
        sha = sha256_file(sp)
        shard = json.loads(sp.read_text())
        shard_meta.append({"path": str(sp.relative_to(RETRY)), "sha256": sha,
                           "physical_gpu": shard.get("physical_gpu"),
                           "job_count": len(shard.get("jobs", []))})
        all_jobs.extend(shard.get("jobs", []))

    # 验证
    names = {j["name"] for j in all_jobs}
    if names != EXPECTED_JOBS:
        print(f"ERROR: 任务名不匹配", file=sys.stderr)
        print(f"  期望: {sorted(EXPECTED_JOBS)}", file=sys.stderr)
        print(f"  实际: {sorted(names)}", file=sys.stderr)
        return 2

    if len(all_jobs) != 6:
        print(f"ERROR: 任务数={len(all_jobs)}，期望 6", file=sys.stderr)
        return 2

    for j in all_jobs:
        if j.get("exit_code") != 0:
            print(f"ERROR: {j['name']} exit_code={j.get('exit_code')}", file=sys.stderr)
            return 2

    # raw_merged
    raw = {
        "schema": "e0_launch_record_raw_merged_v1",
        "source_shards": shard_meta,
        "jobs": all_jobs,
    }
    raw_path = RETRY / "e0_launch_record.raw_merged.json"
    raw_path.write_text(json.dumps(raw, indent=1, ensure_ascii=False))
    print(f"✓ 写入 {raw_path.name}, {len(all_jobs)} 任务")

    # 正式记录：补齐字段
    formal_jobs = []
    for j in all_jobs:
        out_dir = Path(j["output_dir"])
        log_path = Path(j["log"])

        # 尝试从 log mtime 获取更准确的 started
        started = j.get("started_utc")
        ended = None
        if log_path.exists():
            # log 第一行时间戳更准确（但这需要解析，暂用 shard 记录的）
            pass

        rec = {
            "name": j["name"],
            "checkpoint_sha256": j["checkpoint_sha256"],
            "physical_gpu": j["physical_gpu"],
            "pid": j["pid"],
            "exit_code": j["exit_code"],
            "started_utc": started,
            "started_source": "runner_shard_on_completion",
            "ended_utc": ended,
            "ended_source": "not_persisted",
            "hostname": "csy-zg01-gnode39",
            "hostname_source": "recovered_from_context",
            "output_dir": j["output_dir"],
            "log": j["log"],
            "expected_targets": j.get("expected_targets"),
            "expected_pairs": j.get("expected_pairs"),
            "kind": j.get("kind", "q1q2" if "expected_targets" in j else "q3"),
        }
        formal_jobs.append(rec)

    formal = {
        "schema": "e0_launch_record_v1",
        "all_six_jobs_launched": 6,
        "provenance_note": "时间字段从 runner 完成后写入的 shard 获取，非原子记录；hostname 从执行上下文恢复",
        "jobs": formal_jobs,
    }
    formal_path = RETRY / "e0_launch_record.json"
    formal_path.write_text(json.dumps(formal, indent=1, ensure_ascii=False))
    print(f"✓ 写入 {formal_path.name}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
