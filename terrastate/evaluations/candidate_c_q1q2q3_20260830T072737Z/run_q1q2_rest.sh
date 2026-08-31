#!/usr/bin/env bash
# C1's Q1/Q2 on the three splits the earlier run did not cover, so the E1 main
# table has a complete TerraState row. CPU-only on purpose: GPUs 4-7 are saturated
# by the baseline export queue, and the box has ~240 idle cores.
set -u
cd "$(dirname "$0")/../.."
V=/mnt/data/users/luzheng/workspace/iclr/czj/.venv-worldmodel/bin/python
D=/mnt/data/users/luzheng/workspace/iclr/czj/TrainData/EarthNet2021/earthnet2021x
RUN=evaluations/candidate_c_q1q2q3_20260830T072737Z
CKPT=ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt
for pair in "iid_chopped:iid" "ood-st_chopped:oodst" "ood-s_chopped:oods"; do
  track="${pair%%:*}"; tag="${pair##*:}"
  [ -f "$RUN/$tag/state_contract_exclusive.json" ] && { echo "[skip] $track"; continue; }
  echo "===== $track $(date -u +%H:%M:%SZ) ====="
  CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=16 MKL_NUM_THREADS=16 nice -n 10 \
  "$V" eval/eval_b4_exclusive_contract.py --ckpt "$CKPT" \
    --val-dir "$D/$track" --dataset-root "$D" \
    --data-manifest "$RUN/manifests/${track}_manifest.json" \
    --sections q1q2 --device cpu --batch-size 1 --num-data-workers 8 \
    --output-dir "$RUN/$tag"
  echo "rc=$? $track $(date -u +%H:%M:%SZ)"
done
echo "C1 REST DONE $(date -u +%H:%M:%SZ)"
