#!/usr/bin/env bash
# GPU 5 runner: v14880_val_q1q2
set -euo pipefail

RETRY_DIR="/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/ops/e0_q1q2q3_11904_vs_14880/20260820_100718"
PY="/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python"
GPU_IDX=5
CUDA_VISIBLE_DEVICES=$GPU_IDX
export CUDA_VISIBLE_DEVICES

LAUNCH_REC="$RETRY_DIR/e0_launch_record.gpu5.json"
echo '{"schema":"e0_launch_record_v1","gpu":5,"jobs":[]}' > "$LAUNCH_REC"

function log_event() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%6N+00:00)] $*" | tee -a "$RETRY_DIR/e0_runner_gpu5.log"
}

log_event "========== GPU 5 start =========="

job_name="gpu5_v14880_val_q1q2"
ckpt_sha="a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f"
ckpt_path="/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/a5/a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f.pt"
out_dir="$RETRY_DIR/runs/$job_name"
log_file="$RETRY_DIR/logs/$job_name.log"
pid_file="$RETRY_DIR/logs/$job_name.pid"

mkdir -p "$out_dir"
log_event "LAUNCHING $job_name on GPU $GPU_IDX"

"$PY" /csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/eval/eval_b4_exclusive_contract.py \
    --ckpt "$ckpt_path" \
    --val-dir /csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/val_chopped \
    --data-manifest /csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb/artifacts/protocols/b4_eval/val_chopped.manifest.json \
    --dataset-root /csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet \
    --split val \
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

entry=$(cat <<EOF
{"name":"$job_name","gpu":$GPU_IDX,"pid":$pid,"exit_code":$rc,"started_utc":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","checkpoint_sha256":"$ckpt_sha","output_dir":"$out_dir","log":"$log_file","expected_targets":952}
EOF
)
$PY -c "import json; r=json.load(open('$LAUNCH_REC')); r['jobs'].append($entry); json.dump(r,open('$LAUNCH_REC','w'),indent=1)"

log_event "========== GPU 5 done =========="
