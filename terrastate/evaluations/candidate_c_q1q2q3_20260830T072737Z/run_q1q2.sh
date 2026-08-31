#!/usr/bin/env bash
# Formal Q1/Q2 for Candidate C1 on the two frozen chopped splits. CPU-only by
# design: the 8 local GPUs are fully occupied by an unrelated FastWAM training,
# and the Q4 locked eval set the precedent of scoring on CPU.
set -u
cd "$(dirname "$0")/../.."
V=/mnt/data/users/luzheng/workspace/iclr/czj/.venv-worldmodel/bin/python
D=/mnt/data/users/luzheng/workspace/iclr/czj/TrainData/EarthNet2021/earthnet2021x
RUN=evaluations/candidate_c_q1q2q3_20260830T072737Z
CKPT=ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt

for pair in "val_chopped:val" "ood-t_chopped:oodt"; do
  track="${pair%%:*}"; tag="${pair##*:}"
  echo "===== $track ($(date -u +%H:%M:%SZ)) ====="
  CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 nice -n 10 \
  "$V" eval/eval_b4_exclusive_contract.py \
    --ckpt "$CKPT" \
    --val-dir "$D/$track" \
    --dataset-root "$D" \
    --data-manifest "$RUN/manifests/${track}_manifest.json" \
    --sections q1q2 --device cpu --batch-size 1 --num-data-workers 4 \
    --output-dir "$RUN/$tag"
  echo "rc=$? track=$track"
done
echo "ALL DONE $(date -u +%H:%M:%SZ)"
