#!/usr/bin/env bash
# 物理 GPU 5: 第一波 gpu0_v14880_val_q1q2, 第二波 gpu2_v14880_oodt_q3
set -euo pipefail

RETRY_DIR="/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/ops/e0_q1q2q3_11904_vs_14880/20260820_100718"
PY="/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python"
PHYSICAL_GPU=5
CUDA_VISIBLE_DEVICES=$PHYSICAL_GPU
export CUDA_VISIBLE_DEVICES

LAUNCH_REC="$RETRY_DIR/launch_record_shard_pgpu5.json"
echo '{"physical_gpu":5,"jobs":[]}' > "$LAUNCH_REC"

function log_event() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%6N+00:00)] $*" | tee -a "$RETRY_DIR/runner_pgpu5.log"
}

function run_q1q2() {
    local job_name=$1
    local ckpt_sha=$2
    local ckpt_path=$3
    local split=$4
    local val_dir=$5
    local manifest=$6
    local expected=$7

    local out_dir="$RETRY_DIR/runs/$job_name"
    local log_file="$RETRY_DIR/logs/$job_name.log"
    local pid_file="$RETRY_DIR/logs/$job_name.pid"

    mkdir -p "$out_dir"
    log_event "LAUNCHING $job_name on physical GPU $PHYSICAL_GPU"

    "$PY" /csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/eval/eval_b4_exclusive_contract.py \
        --ckpt "$ckpt_path" \
        --val-dir "$val_dir" \
        --data-manifest "$manifest" \
        --dataset-root /csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet \
        --split "$split" \
        --sections q1q2 \
        --batch-size 1 \
        --num-data-workers 2 \
        --workers 4 \
        --device cuda \
        --output-dir "$out_dir" \
        > "$log_file" 2>&1 &

    local pid=$!
    echo $pid > "$pid_file"
    log_event "$job_name started pid=$pid"
    wait $pid
    local rc=$?
    log_event "$job_name finished pid=$pid exit_code=$rc"

    local started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local entry=$(cat <<EOF
{"name":"$job_name","physical_gpu":$PHYSICAL_GPU,"pid":$pid,"exit_code":$rc,"started_utc":"$started_utc","checkpoint_sha256":"$ckpt_sha","output_dir":"$out_dir","log":"$log_file","expected_targets":$expected}
EOF
)
    $PY -c "import json; r=json.load(open('$LAUNCH_REC')); r['jobs'].append($entry); json.dump(r,open('$LAUNCH_REC','w'),indent=1)"
}

function run_q3() {
    local job_name=$1
    local ckpt_sha=$2
    local ckpt_path=$3

    local out_dir="$RETRY_DIR/runs/$job_name"
    local log_file="$RETRY_DIR/logs/$job_name.log"
    local pid_file="$RETRY_DIR/logs/$job_name.pid"

    mkdir -p "$out_dir"
    log_event "LAUNCHING $job_name on physical GPU $PHYSICAL_GPU"

    "$PY" /csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/eval/extreme_state_audit.py \
        --protocol-dir /csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/artifacts/protocols/extreme_audit_oodt_v1 \
        --dataset-root /csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet \
        --ckpt-exclusive "$ckpt_path" \
        --batch-size 1 \
        --num-data-workers 2 \
        --workers 4 \
        --n-boot 10000 \
        --evidence-role final \
        --device cuda \
        --dump-per-cube \
        --output-dir "$out_dir" \
        > "$log_file" 2>&1 &

    local pid=$!
    echo $pid > "$pid_file"
    log_event "$job_name started pid=$pid"
    wait $pid
    local rc=$?
    log_event "$job_name finished pid=$pid exit_code=$rc"

    local started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local entry=$(cat <<EOF
{"name":"$job_name","physical_gpu":$PHYSICAL_GPU,"pid":$pid,"exit_code":$rc,"started_utc":"$started_utc","checkpoint_sha256":"$ckpt_sha","output_dir":"$out_dir","log":"$log_file","kind":"q3","expected_pairs":84}
EOF
)
    $PY -c "import json; r=json.load(open('$LAUNCH_REC')); r['jobs'].append($entry); json.dump(r,open('$LAUNCH_REC','w'),indent=1)"
}

log_event "========== 物理GPU 5 开始 =========="

# 第一波: gpu0_v14880_val_q1q2
run_q1q2 "gpu0_v14880_val_q1q2" \
    "a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f" \
    "/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/a5/a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f.pt" \
    "val" \
    "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/val_chopped" \
    "/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb/artifacts/protocols/b4_eval/val_chopped.manifest.json" \
    952

# 第二波: gpu2_v14880_oodt_q3
run_q3 "gpu2_v14880_oodt_q3" \
    "a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f" \
    "/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/a5/a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f.pt"

log_event "========== 物理GPU 5 完成 =========="
