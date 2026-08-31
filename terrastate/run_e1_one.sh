#!/usr/bin/env bash
# E1 main table: export predictions for one (model, ckpt, split), then score them
# with the official GreenEarthNet scorer. One config per invocation so the outer
# loop can checkpoint progress and skip what is already done.
#
#   run_e1_one.sh <model> <ckpt-or-NONE> <split> [gpu]
#
# GPU: pass an index (default 4). GPUs 4-7 were idle; 0-3 belong to an unrelated
# training job. Pass "cpu" to fall back if the GPUs get taken.
set -uo pipefail
cd "$(dirname "$0")"

MODEL="$1"; CKPT="$2"; SPLIT="$3"; GPU="${4:-4}"
V=/mnt/data/users/luzheng/workspace/iclr/czj/.venv-worldmodel/bin/python
DATA=/mnt/data/users/luzheng/workspace/iclr/czj/TrainData/EarthNet2021/earthnet2021x
CFGROOT=/mnt/data/users/luzheng/workspace/iclr/czj/WorldModel2026-planb/third_party/greenearthnet/model_configs
EMPROOT=/mnt/data/users/luzheng/workspace/iclr/czj/_downloads/emp-v0.1.0
RUN=evaluations/e1_main_table
TAG="${MODEL}__${SPLIT}"
OUT="$RUN/$TAG"

# split name -> the scorer's --split label (it wants the protocol role, not the dir)
case "$SPLIT" in
  iid_chopped)    ROLE=iid    ;;
  ood-t_chopped)  ROLE=ood-t  ;;
  ood-s_chopped)  ROLE=ood-s  ;;
  ood-st_chopped) ROLE=ood-st ;;
  *) echo "unknown split $SPLIT"; exit 2 ;;
esac

if [ "$GPU" = "cpu" ]; then DEV=cuda_off; export CUDA_VISIBLE_DEVICES=""; DEVARG=cpu; BS=1
else export CUDA_VISIBLE_DEVICES="$GPU"; DEVARG=cuda; BS=16; fi

mkdir -p "$OUT"
[ -f "$OUT/scores/metrics_en21x.json" ] && { echo "[skip] $TAG already scored"; exit 0; }

echo "===== $TAG  gpu=$GPU  $(date -u +%H:%M:%SZ) ====="

# ---- 1. predictions -------------------------------------------------------
if [ ! -f "$OUT/.export_done" ]; then
  case "$MODEL" in
    contextformer*)
      "$V" eval/export_contextformer_predictions.py \
        --track-dir "$DATA/$SPLIT" --ckpt "$CKPT" \
        --output-dir "$OUT/pred" --device "$DEVARG" --batch-size "$BS" || exit 1 ;;
    convlstm*|predrnn*|simvp*)
      # official emp nn.Module built from its published YAML; see
      # eval/export_emp_baseline_predictions.py for why sys.path points upstream
      FAM="${MODEL%%[0-9]*}"; FAM="${FAM%_seed*}"
      VAR="${MODEL%%_seed*}"
      "$V" eval/export_emp_baseline_predictions.py \
        --track-dir "$DATA/$SPLIT" --ckpt "$CKPT" \
        --config "$CFGROOT/$FAM/$VAR/seed=42.yaml" --emp-root "$EMPROOT" \
        --output-dir "$OUT/pred" --device "$DEVARG" --batch-size "$BS" || exit 1 ;;
    *)
      echo "[skip] no exporter wired for $MODEL -- recorded as n.a."; exit 3 ;;
  esac
  touch "$OUT/.export_done"
fi

# ---- 2. official scorer ---------------------------------------------------
"$V" eval/eval_greenearthnet_official.py \
  --target-dir "$DATA/$SPLIT" --prediction-dir "$OUT/pred" \
  --output-dir "$OUT/scores" --split "$ROLE" --allow-discovery --workers 8 || exit 1

echo "[ok] $TAG  $(date -u +%H:%M:%SZ)"
