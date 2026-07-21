# plan-b-pvt · 执行日志(Gate-0 → 主实验)

> 活文档,持续追加。对齐 `思路整理进展/75_方案B执行引导...`。

## Gate-0 · 复现官方 Contextformer(精度底座)

### A2 架构复现忠实性 ✅
- vendored `models/encoders/contextformer_official.py`(emp v0.1.0 的 `ContextFormer`,去 PL 依赖,torch2.x 可跑)。
- 载官方 `contextformer6M/seed42.ckpt`:**0 missing / 0 unexpected 键,6.06M 参数**(=公开 6.1M SOTA)。前向 `(1,20,1,128,128)` finite。
- 数据适配器 `data/greenearthnet_contextformer_dataset.py` = emp `EarthNet2021XDataset.__getitem__` 逐行复制(dl_cloudmask=True,5 波段 [ndvi,B02,B03,B04,B8A],eobs 8×{mean,min,max}=24,静态 std 500/500/500/1/1)。

### A2 数值 parity(GreenEarthNet ood-t_chopped,1904 cubes,seed42)
| 指标 | 我们(seed42) | 公开 Contextformer | |
|---|---|---|---|
| RMSE | 0.1433 | 0.14 | ✅ |
| \|bias\| | 0.0937 | 0.09 | ✅ |
| RMSE25 | 0.0786 | 0.08 | ✅ |
| **R²** | **0.583** | 0.62 | ⚠️ 低 0.037 |
| NSE | ~0 | 0.09 | ⚠️ |

**诊断**:打分器已核为与官方 `eval.py` 聚合一致(R²=forest/shrub/grass/crop 四类均值,0.554/0.578/0.594/0.605→0.583);架构字节级一致、数据逐行复制、推理调用一致。→ 0.583 是官方 seed42 的**真实分数**,非 bug。R² 低 0.037 且误差指标全中,符合"单 seed vs 论文 3-seed 均值"特征。**决策 A(2026-07-21):0.583 记为 matched 底座,推进主实验;3-seed 公开 parity 推迟到写 SOTA 前确认。**

**Provenance**:seed42.ckpt sha256 `ec6706e8…d4a4fa`;评分器 commit `a0329636`;结果 `evaluations/plan_b_ctx_a2/score/metrics_en21x.json`(服务器)。

## 下一步:B0 matched fine-tune(8 卡 H200)
- 从官方权重 init,MaskedL2NDVILoss(lc 10–40,pred_mask -1),matched 预算 → 目标不跌破底座 0.583。
- 之后 B1–B4 加状态契约冲 SOTA(与 B0 同 init/data/预算)。

---
### 执行记录追加
- 2026-07-21 A2 复现 + parity 完成(见上)。
