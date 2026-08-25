#!/usr/bin/env bash
# GPU 4 runner: legacy11904 三项队列（oodt_q1q2 → val_q1q2 → oodt_q3）
set -euo pipefail

RETRY_DIR="/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/ops/e0_q1q2q3_11904_vs_14880/20260820_100718"
PY="/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python"
GPU_IDX=4
CUDA_VISIBLE_DEVICES=$GPU_IDX
export CUDA_VISIBLE_DEVICES

mkdir -p "$RETRY_DIR/runs"
mkdir -p "$RETRY_DIR/logs"

LAUNCH_REC="$RETRY_DIR/e0_launch_record.gpu4.json"
echo '{"schema":"e0_launch_record_v1","gpu":4,"jobs":[]}' > "$LAUNCH_REC"

function log_event() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%6N+00:00)] $*" | tee -a "$RETRY_DIR/e0_runner_gpu4.log"
}

function check_gpu_free() {
    local idx=$1
    local uuid=$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader | awk -v i="$idx" -F', ' '$1==i {print $2}')
    local mem=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -v i="$idx" -F', ' '$1==i {print $2}')
    local util=$(nvidia-smi --query-gpu=index,utilization.gpu --format=csv,noheader,nounits | awk -v i="$idx" -F', ' '$1==i {print $2}')
    local procs=$(nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader | grep -c "^$uuid," || true)

    log_event "pre-check: GPU $idx uuid=$uuid mem=${mem}MiB util=${util}% procs=$procs"

    if [ "$procs" -gt 0 ] || [ "$mem" -gt 512 ] || [ "$util" -gt 5 ]; then
        log_event "GPU $idx OCCUPIED (procs=$procs mem=$mem util=$util) -- ABORT"
        return 1
    fi
    return 0
}

function run_job() {
    local job_name=$1
    local ckpt_sha=$2
    local ckpt_path=$3
    local sections=$4
    local split_name=$5
    local val_dir=$6
    local data_manifest=$7
    local expected=$8

    local out_dir="$RETRY_DIR/runs/$job_name"
    local log_file="$RETRY_DIR/logs/$job_name.log"
    local pid_file="$RETRY_DIR/logs/$job_name.pid"

    mkdir -p "$out_dir"

    check_gpu_free $GPU_IDX || return 1

    log_event "LAUNCHING $job_name on GPU $GPU_IDX"

    "$PY" /csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/eval/eval_b4_exclusive_contract.py \
        --ckpt "$ckpt_path" \
        --val-dir "$val_dir" \
        --data-manifest "$data_manifest" \
        --dataset-root /csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet \
        --split "$split_name" \
        --sections "$sections" \
        --batch-size 1 \
        --num-data-workers 2 \
        --workers 4 \
        --device cuda \
        --output-dir "$out_dir" \
        > "$log_file" 2>&1 &

    local pid=$!
    echo $pid > "$pid_file"
    log_event "$job_name started pid=$pid log=$log_file"

    wait $pid
    local rc=$?

    log_event "$job_name finished pid=$pid exit_code=$rc"

    local entry=$(cat <<EOF
{"name":"$job_name","gpu":$GPU_IDX,"pid":$pid,"exit_code":$rc,"started_utc":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","checkpoint_sha256":"$ckpt_sha","output_dir":"$out_dir","log":"$log_file","expected_targets":$expected}
EOF
)
    $PY -c "import json; r=json.load(open('$LAUNCH_REC')); r['jobs'].append($entry); json.dump(r,open('$LAUNCH_REC','w'),indent=1)"

    return $rc
}

function run_q3_job() {
    local job_name=$1
    local ckpt_sha=$2
    local ckpt_path=$3

    local out_dir="$RETRY_DIR/runs/$job_name"
    local log_file="$RETRY_DIR/logs/$job_name.log"
    local pid_file="$RETRY_DIR/logs/$job_name.pid"

    mkdir -p "$out_dir"

    check_gpu_free $GPU_IDX || return 1

    log_event "LAUNCHING $job_name on GPU $GPU_IDX"

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
    log_event "$job_name started pid=$pid log=$log_file"

    wait $pid
    local rc=$?

    log_event "$job_name finished pid=$pid exit_code=$rc"

    local entry=$(cat <<EOF
{"name":"$job_name","gpu":$GPU_IDX,"pid":$pid,"exit_code":$rc,"started_utc":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","checkpoint_sha256":"$ckpt_sha","output_dir":"$out_dir","log":"$log_file","kind":"q3","expected_pairs":84}
EOF
)
    $PY -c "import json; r=json.load(open('$LAUNCH_REC')); r['jobs'].append($entry); json.dump(r,open('$LAUNCH_REC','w'),indent=1)"

    return $rc
}

log_event "========== GPU 4 queue start =========="

# job 1: gpu4_legacy11904_oodt_q1q2 (原 gpu4)
run_job "gpu4_legacy11904_oodt_q1q2" \
    "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd" \
    "/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/64/644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd.pt" \
    "q1q2" \
    "ood-t_chopped" \
    "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/ood-t_chopped" \
    "/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb/evaluations/greenearthnet_oodt_20260719_214234/greenearthnet_oodt_chopped_manifest.json" \
    1904

# job 2: gpu3_legacy11904_val_q1q2 (原 gpu3，现在改成 gpu4)
run_job "gpu4_legacy11904_val_q1q2" \
    "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd" \
    "/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/64/644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd.pt" \
    "q1q2" \
    "val" \
    "/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/val_chopped" \
    "/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb/artifacts/protocols/b4_eval/val_chopped.manifest.json" \
    952

# job 3: gpu5_legacy11904_oodt_q3 (原 gpu5，现在改成 gpu4)
run_q3_job "gpu4_legacy11904_oodt_q3" \
    "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd" \
    "/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/64/644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd.pt"

log_event "========== GPU 4 queue done =========="
