# TerraState — AAAI-27

> A Testable Predictive-State World Model for Weather-Driven Land-Surface Forecasting

本目录是**独立项目**，不依赖同仓库的 `../obsworld/`。请勿跨目录 import。

---

## 目录

| 路径 | 内容 |
|---|---|
| `models/` | TerraState 模型：`terrastate_v2.py`、`plan_b_b4.py`、`plan_b_b4_exclusive.py`、`encoders/pvt_contextformer_q.py`（history operator）、`stage1_8_factorizer.py`、`losses/masked_l2_ndvi.py` |
| `data/` | `greenearthnet_contextformer_dataset.py`、`ssl4eo_l1c_l2a_paired.py`、`earthnet_manifest.py` |
| `train/` | `train_terrastate_v2.py`、`train_plan_b_contextformer.py`、`train_plan_b_b4_exclusive.py`、`terrastate_v2_common.py`、`terrastate_future_state_cache.py` |
| `eval/` | Q1–Q3 评测：`export_b4_predictions.py`、`eval_b4_state_contract.py`、`b4_donor_schema.py`、`select_b4_checkpoint.py`、`eval_greenearthnet_official.py`、`greenearthnet_protocol.py` |
| `evaluations/` | 评测产物与汇总 CSV |
| `artifacts/protocols/extreme_audit_oodt_v1/` | **Q3 热旱 84 对冻结清单**：`hotdry_manifest.json`、`matched_normal_manifest.json`、`thresholds.json`、`climatology_train.json` |
| `artifacts/protocols/b4_eval/` | B4 评测 guard 模板 |
| `scripts/` `tools/` `tests/` | 启动脚本、运维工具、smoke 测试 |
| `思路整理进展/` | 24 篇 AAAI 线设计与写作文档 |
| `submission/` | 已提交材料：正文、补充材料、代码包、Reproducibility Checklist |
| `archive/` | `TerraState_AAAI27_CURATED_20260730` 精选归档（去权重） |

## 从哪里开始

1. `archive/00_START_HERE/PROJECT_MAP.md` — 归档导航
2. `archive/00_START_HERE/KEY_FACTS_AND_CLAIMS.md` — 方法、结果与主张边界
3. `archive/00_START_HERE/FINAL_TRAINING_AND_WEIGHT_LINEAGE.md` — Phase-I B4 → TerraState-V2 权重链
4. `submission/main.pdf` — 已提交正文（9 页）
5. `submission/aaai27_supplement/supplementary.pdf` — 补充材料（3 页）
6. `TERRASTATE_V2_EVIDENCE.md` / `TERRASTATE_V2_RUNBOOK.md` — 证据表与运行手册

## 三个可检验问题

| | 问题 | 主表 |
|---|---|---|
| Q1 | OOD-t 下是否保留有用预报能力 | 正文 Table 1 |
| Q2 | 移除状态中介贡献是否降低预测质量 | 正文 Table 2 |
| Q3 | 真实未来天气是否比控制更忠实 | 正文 Table 3 |

Q1–Q3 的冻结报告值在 `archive/04_RESULTS_EVIDENCE/current/release_metrics/`
与 `submission/aaai27_code_package/` 内的 `results/*.json`。

## 权重

不在仓库内，见 [`WEIGHTS_INDEX.md`](WEIGHTS_INDEX.md)（Release tag `weights-terrastate-v1`）。

⚠️ 作者确认口径的 40 epochs / 14,880 updates 最终权重**二进制仍缺失**；
已恢复的 boundary80 checkpoint 不能替代它。

## 环境

```bash
python -m pip install -r requirements.txt
# 或
conda env create -f environment.worldmodel.yml
```
