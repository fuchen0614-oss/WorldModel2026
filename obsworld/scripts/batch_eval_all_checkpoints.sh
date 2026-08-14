#!/bin/bash
# 批量验证所有 Stage1.5 checkpoint

STAGE1_CKPT="checkpoints/stage1_vits_dual_staged/checkpoint_step_95000.pt"
STAGE1_5_DIR="checkpoints/stage1_5_dual_conditioned_vits"

echo "===== Batch Evaluation: All Stage1.5 Checkpoints ====="

for ckpt in ${STAGE1_5_DIR}/checkpoint_step_*.pt; do
    step=$(basename $ckpt | sed 's/checkpoint_step_//;s/.pt//')
    echo ""
    echo ">>> Evaluating Step ${step} <<<"

    # φ 泄漏 probe
    echo "[1/2] φ Leakage Probe..."
    python eval/eval_phi_leakage_probe.py \
        --stage1_ckpt ${STAGE1_CKPT} \
        --stage1_5_ckpt ${ckpt} \
        --batch_size 128 \
        --probe_epochs 5 \
        > logs/eval_phi_leakage_step_${step}.log 2>&1

    # Pure φ 假设验证
    echo "[2/2] Pure φ Assumption..."
    python eval/eval_pure_phi_assumption.py \
        --stage1_ckpt ${STAGE1_CKPT} \
        --stage1_5_ckpt ${ckpt} \
        --batch_size 128 \
        --probe_epochs 10 \
        > logs/eval_pure_phi_step_${step}.log 2>&1

    echo "✓ Step ${step} evaluation complete"
done

echo ""
echo "===== All Evaluations Complete ====="
echo "Results saved in logs/eval_*_step_*.log"
