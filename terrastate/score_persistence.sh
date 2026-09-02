#!/usr/bin/env bash
# Score the persistence baseline's existing predictions with OUR official scorer.
#
# The upstream pixelwise script already wrote every prediction cube for all five
# splits, but it scored them with its own routine and emitted metrics_en21x.csv.
# A08 reads metrics_en21x.json produced by eval_greenearthnet_official.py, so the
# persistence row is currently blank despite the work being done. This closes that
# gap without re-running the model -- scoring only, CPU, a few minutes per split.
#
# Output lands under evaluations/e1_main_table/ so collect_e1_table.py finds it the
# same way it finds the learned baselines.
set -u
cd "$(dirname "$0")"

V=/mnt/data/users/luzheng/workspace/iclr/czj/.venv-worldmodel/bin/python
DATA=/mnt/data/users/luzheng/workspace/iclr/czj/TrainData/EarthNet2021/earthnet2021x
PRED=evaluations/e1_nonml/persistence/preds

for pair in "iid_chopped:iid" "ood-t_chopped:ood-t" \
            "ood-s_chopped:ood-s" "ood-st_chopped:ood-st"; do
  split="${pair%%:*}"; role="${pair##*:}"
  out="evaluations/e1_main_table/persistence__${split}/scores"
  [ -f "$out/metrics_en21x.json" ] && { echo "[skip] $split"; continue; }
  echo "===== persistence $split  $(date -u +%H:%M:%SZ) ====="
  mkdir -p "$out"
  CUDA_VISIBLE_DEVICES="" nice -n 10 "$V" eval/eval_greenearthnet_official.py \
    --target-dir "$DATA/$split" --prediction-dir "$PRED/$split" \
    --output-dir "$out" --split "$role" --allow-discovery --workers 16
  echo "rc=$? $split"
done
echo "PERSISTENCE SCORING DONE $(date -u +%H:%M:%SZ)"
