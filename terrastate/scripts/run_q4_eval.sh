#!/bin/bash
# Q4 评测脚本：Candidate C composition / segment-transition 评测
# 使用 CPU，按 A05 主线，在 C1 和 C0R 完成后运行

set -e

# 使用正式训练冻结环境（A05 §14.2 env_identity.json）
PYTHON=/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python

ROOT=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate
cd "$ROOT"

# 数据与 manifest
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/val_chopped
SPLIT_MANIFEST="$ROOT/ops/candidate_c_nightly/20260820T155316Z/manifests/candidate_c_eo_split_manifest_v1.json"
SPLIT_SELECTOR="validation_subsplit.val_dev.ids"

# checkpoint
NIGHTLY="$ROOT/ops/candidate_c_nightly/20260820T155316Z/formal"
CKPT_C1="$NIGHTLY/run_c1_20260822T131006Z/checkpoint_main.pt"
CKPT_C0R="$NIGHTLY/run_c0r_20260823T063516Z/checkpoint_main.pt"

# 输出
TIMESTAMP=$(date +%Y%m%dT%H%M%SZ)
OUT_ROOT="$ROOT/results/q4_eval_$TIMESTAMP"
OUT_C1="$OUT_ROOT/c1_score"
OUT_C0R="$OUT_ROOT/c0r_score"
OUT_COMPARE="$OUT_ROOT/compare"

mkdir -p "$OUT_C1" "$OUT_C0R" "$OUT_COMPARE"

echo "[$(date)] Q4 评测开始"
echo "  C1  checkpoint: $CKPT_C1"
echo "  C0R checkpoint: $CKPT_C0R"
echo "  Data root: $DATA_ROOT"
echo "  Split manifest: $SPLIT_MANIFEST"
echo "  Output: $OUT_ROOT"
echo

# 第一步：C1 打分
echo "[$(date)] Step 1/3: C1 score"
$PYTHON eval/eval_terrastate_candidate_c_q4.py score \
  --ckpt "$CKPT_C1" \
  --data-root "$DATA_ROOT" \
  --split-manifest "$SPLIT_MANIFEST" \
  --split-selector "$SPLIT_SELECTOR" \
  --output "$OUT_C1" \
  --device cpu \
  --batch-size 4 \
  --num-workers 2

echo "[$(date)] C1 score 完成"
echo

# 第二步：C0R 打分
echo "[$(date)] Step 2/3: C0R score"
$PYTHON eval/eval_terrastate_candidate_c_q4.py score \
  --ckpt "$CKPT_C0R" \
  --data-root "$DATA_ROOT" \
  --split-manifest "$SPLIT_MANIFEST" \
  --split-selector "$SPLIT_SELECTOR" \
  --output "$OUT_C0R" \
  --device cpu \
  --batch-size 4 \
  --num-workers 2

echo "[$(date)] C0R score 完成"
echo

# 第三步：配对比较（G_abs 判据）
echo "[$(date)] Step 3/3: C1 vs C0R compare (G_abs gate)"
$PYTHON eval/eval_terrastate_candidate_c_q4.py compare \
  --candidate "$OUT_C1" \
  --control "$OUT_C0R" \
  --output "$OUT_COMPARE"

echo "[$(date)] 比较完成"
echo

# 输出结果摘要
if [ -f "$OUT_COMPARE/q4_compare.json" ]; then
  echo "=== Q4 评测结果 ==="
  $PYTHON -c "
import json
with open('$OUT_COMPARE/q4_compare.json') as f:
    r = json.load(f)
print(f\"Verdict: {r['verdict']}\")
gate = r['factual_endpoint_gate']
print(f\"Direct combos pass: {gate['direct_all_pass']} ({gate['n_direct_combos']} combos)\")
print(f\"Composed combos pass: {gate['composed_all_pass']} ({gate['n_composed_combos']} combos)\")
print(f\"Overall gate: {gate['passes']}\")
"
  echo
  echo "完整结果: $OUT_COMPARE/q4_compare.json"
else
  echo "错误：未找到 q4_compare.json"
  exit 1
fi

echo "[$(date)] Q4 评测全部完成"
echo "输出目录: $OUT_ROOT"
