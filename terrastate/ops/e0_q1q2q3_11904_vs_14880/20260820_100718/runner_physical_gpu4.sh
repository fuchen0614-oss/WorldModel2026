#!/usr/bin/env bash
# 物理 GPU 4: 运行 gpu4_legacy11904_oodt_q1q2
set -euo pipefail

RETRY_DIR="/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/ops/e0_q1q2q3_11904_vs_14880/20260820_100718"
PY="/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python"
PHYSICAL_GPU=4
CUDA_VISIBLE_DEVICES=$PHYSICAL_GPU
export CUDA_VISIBLE_DEVICES

LAUNCH_REC="$RETRY_DIR/launch_record_shard_pgpu4.json"
echo '{"physical_gpu":4,"jobs":[]}' > "$LAUNCH_REC"

function log_event() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%6N+00:00)] $*" | tee -a "$RETRY_DIR/runner_pgpu4.log"
}

log_event "========== 物理GPU 4 开始 =========="

job_name="gpu4_legacy11904_oodt_q1q2"
ckpt_sha="644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd"
ckpt_path="/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/64/644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd.pt"
out_dir="$RETRY_DIR/runs/$job_name"
log_file="$RETRY_DIR/logs/$job_name.log"
pid_file="$RETRY_DIR/logs/$job_name.pid"

mkdir -p "$out_dir"
log_event "LAUNCHING $job_name on physical GPU $PHYSICAL_GPU"

"$PY" /csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/eval/eval_b4_exclusive_contract.py \
    --ckpt "$ckpt_path" \
    --val-dir /csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/ood-t_chopped \
    --data-manifest /csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb/evaluations/greenearthnet_oodt_20260719_214234/greenearthnet_oodt_chopped_manifest.json \
    --dataset-root /csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet \
    --split ood-t_chopped \
    --sections q1q2 \
    --batch-size 1 \
    --num-data-workers 2 \
    --workers 4 \
    --device cuda \
    --output-dir "$out_dir" \
    > "$log_file" 2>&1 &

pid=$!
echo $pid > "$pid_file"
log_event "$job_name started pid=$pid"
wait $pid
rc=$?
log_event "$job_name finished pid=$pid exit_code=$rc"

started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
entry=$(cat <<EOF
{"name":"$job_name","physical_gpu":$PHYSICAL_GPU,"pid":$pid,"exit_code":$rc,"started_utc":"$started_utc","checkpoint_sha256":"$ckpt_sha","output_dir":"$out_dir","log":"$log_file","expected_targets":1904}
EOF
)
$PY -c "import json; r=json.load(open('$LAUNCH_REC')); r['jobs'].append($entry); json.dump(r,open('$LAUNCH_REC','w'),indent=1)"

log_event "========== 物理GPU 4 完成 =========="
