#!/usr/bin/env bash
# Formal Q3 (weather-response fidelity) for Candidate C1, on the frozen
# extreme_audit_oodt_v1 protocol -- the same 84 pairs V2 was audited on.
# All four protocol SHAs verified against the frozen evidence before launch.
# CPU-only: the 8 local GPUs are busy with an unrelated FastWAM training.
# --dump-per-cube is ON: V2's audit regretted having only aggregate JSONs and no
# per-cube rasters to plot from.
set -u
cd "$(dirname "$0")/../.."
V=/mnt/data/users/luzheng/workspace/iclr/czj/.venv-worldmodel/bin/python
D=/mnt/data/users/luzheng/workspace/iclr/czj/TrainData/EarthNet2021/earthnet2021x
RUN=evaluations/candidate_c_q1q2q3_20260830T072737Z

echo "===== Q3 start $(date -u +%H:%M:%SZ) ====="
CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 nice -n 10 \
"$V" eval/extreme_state_audit.py \
  --protocol-dir artifacts/protocols/extreme_audit_oodt_v1 \
  --dataset-root "$D" --data-dir "$D/ood-t_chopped" \
  --ckpt-exclusive ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt \
  --device cpu --batch-size 1 --num-data-workers 4 \
  --evidence-role final --dump-per-cube \
  --output-dir "$RUN/q3"
echo "rc=$?  done $(date -u +%H:%M:%SZ)"
