#!/usr/bin/env bash
set -euo pipefail

cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

CONFIG="configs/train/stage1_5_dual_conditioned_vits_state_bridge_60k.yaml"
RESUME="checkpoints/stage1_5_dual_conditioned_vits_state_bridge_60k/checkpoint_step_30000.pt"
mkdir -p logs
TS=$(date +%Y%m%d_%H%M%S)
LOG="logs/stage1_5_state_bridge_resume_${TS}.log"

if [[ ! -f "${RESUME}" ]]; then
  echo "Missing resume checkpoint: ${RESUME}" >&2
  exit 1
fi

echo "Resuming Stage1.5 from ${RESUME}; log=${LOG}"
torchrun --nproc_per_node=8 --nnodes=1 \
  --rdzv_backend=c10d --rdzv_endpoint=localhost:0 \
  train/train_stage1_5_dual_conditioned.py \
  --config "${CONFIG}" \
  --resume-stage15 "${RESUME}" \
  2>&1 | tee "${LOG}"
