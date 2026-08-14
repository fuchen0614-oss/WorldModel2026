# Stage2 后续研究入口

本目录为 Stage1 → Stage1.5 精选归档新增的、**明确隔离的后续研究区**。它保存
Plan-A/ViT-S 路线截至 2026-07-23 的最新可修改 Stage2 实现，不改变原归档中
Stage1–1.5 已冻结的事实和结果。

## 快速入口

1. `STATUS_AND_RECOMMENDATION.md`：这套 Stage2 到底能做什么、历史结果如何、
   下一步推荐从哪里改。
2. `01_CODE_SNAPSHOT/`：commit `541dd76` 的最小可运行代码闭包。
3. `RELATED_DOCUMENT_INDEX.md`：9 份强相关 Markdown 的阅读优先级和时效边界。
4. `VALIDATION.txt`：commit 核对、测试和 smoke 结果。
5. `03_KEY_WEIGHTS/`：Direct/rollout 两条正式训练线各自的 best 权重与严格加载审计。
6. `04_KEY_RESULTS/`：上述权重对应的 OOD-t 聚合指标、manifest 与 scorer provenance。

## 当前推荐入口

优先阅读和修改：

- `01_CODE_SNAPSHOT/configs/train/plan_a_metric_v1.yaml`
- `01_CODE_SNAPSHOT/train/train_stage2_earthnet.py`
- `01_CODE_SNAPSHOT/models/dynamics/obsworld_factory.py`
- `01_CODE_SNAPSHOT/models/losses/earthnet_forecasting.py`
- `01_CODE_SNAPSHOT/scripts/smoke_plan_a_prime.py`
- `01_CODE_SNAPSHOT/eval/aprime_load_bearing.py`
- `01_CODE_SNAPSHOT/eval/aprime_driver_sensitivity.py`

`plan_a_metric_v1.yaml` 是最新的 metric-aligned 延续方案，但它没有完整训练结果，
不能被描述为已经优于历史 A′。它的价值在于把训练损失、land-cover mask、
checkpoint selection、20 个 horizon 和 optimizer 分组进一步对齐到正式评估。

## 边界

- 本目录是“可继续修改的研究快照”，不是 AAAI 正文采用的 TerraState 最终实现。
- 历史 A′ 最佳 OOD-t 结果仍低于后续 B 路线；详见
  `STATUS_AND_RECOMMENDATION.md` 与 85 号审计。
- Stage1.5 与 A2-best 原始 checkpoint 仍未找回，不能凭文件名猜测替代；
  `03_KEY_WEIGHTS/` 新增的是两条更早的 Direct/rollout Stage2 best 权重，并已与
  Stage1.5 身份严格区分。
- 原始 `WorldModel2026` 没有被修改。
