#!/usr/bin/env bash
# Move C1's remaining Q1/Q2 splits from CPU onto the now-idle GPUs.
#
# The baselines finished and freed GPUs 4-7, but C1 was still grinding ood-st on
# CPU -- two hours in on 7,024 cubes, with ood-s (10,536) still queued behind it.
# At ~1.7 s/cube that would not have cleared the deadline. The evaluator writes
# its JSON only at the end, so nothing partial is lost by restarting.
#
# Kills the CPU run by PID (matching these patterns inline kept killing the caller)
# and relaunches both splits on GPU, one per card.
set -u
cd /mnt/data/users/luzheng/workspace/iclr/czj/WorldModel2026v2/terrastate

for pat in run_q1q2_rest.sh eval_b4_exclusive_contract; do
  for p in $(ps -eo pid,args --no-headers | grep -F "$pat" | grep -v grep | awk '{print $1}'); do
    [ "$p" = "$$" ] && continue
    kill "$p" 2>/dev/null
  done
done
sleep 5
for pat in run_q1q2_rest.sh eval_b4_exclusive_contract; do
  for p in $(ps -eo pid,args --no-headers | grep -F "$pat" | grep -v grep | awk '{print $1}'); do
    [ "$p" = "$$" ] && continue
    kill -9 "$p" 2>/dev/null
  done
done
echo "[stopped CPU run]"

V=/mnt/data/users/luzheng/workspace/iclr/czj/.venv-worldmodel/bin/python
D=/mnt/data/users/luzheng/workspace/iclr/czj/TrainData/EarthNet2021/earthnet2021x
RUN=evaluations/candidate_c_q1q2q3_20260830T072737Z
CKPT=ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt

launch () {                      # track  tag  gpu
  [ -f "$RUN/$2/state_contract_exclusive.json" ] && { echo "[skip] $1"; return; }
  CUDA_VISIBLE_DEVICES="$3" nohup "$V" eval/eval_b4_exclusive_contract.py \
    --ckpt "$CKPT" --val-dir "$D/$1" --dataset-root "$D" \
    --data-manifest "$RUN/manifests/$1_manifest.json" \
    --sections q1q2 --device cuda --batch-size 1 --num-data-workers 8 \
    --output-dir "$RUN/$2" > "$RUN/run_$2_gpu.log" 2>&1 &
  echo "[launch] $1 -> gpu $3  pid $!"
}

launch ood-st_chopped oodst 4
launch ood-s_chopped  oods  5
