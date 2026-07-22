# 83 · Table B 实现方案：EO-WM benchmark 完全可复现 + 我们的模型怎么插进去（2026-07-22）

> 依据：EO-WM(arXiv 2606.27277) 附录 A.2 全文抽取 + 官方 README。**结论：EO-WM 把 benchmark CSV + eval 脚本 + 指标公式 + 构造算法全开源了 → 我们能在同一把尺子上评自己的模型、和它同表比。这是 Table B 的可执行路径。**

## 0. 为什么这是"对我们有利的尺子"（再确认）
Table 2(Extreme Summer) 已抽到真数：**PredRNN(R²榜0.62) 的极端 NDVI-MAE=0.38、SimVP=0.18，而 Earthformer(R²最弱0.52)=0.11**——**R² 榜赢家因过度平滑在极端事件上崩**。我们残差头锚 last-valid、学变化量、不过度平滑 → **假设**我们在这把尺子上比在 R² 尺子上好看得多。**这是待验证假设，不是既定胜利——必须实测。**

## 1. EO-WM 开源了什么（可直接用）
- **benchmark 定义 CSV**：`benchmark_csv/extreme_summer_benchmark.csv`(1440 窗口) + `benchmark_csv/seasonal_pairs_benchmark.csv`(422 对)——**精确到样本/窗口/对/severity bin/track/trough 帧 t\***。
- **eval 脚本**（Earthformer 示例，可改成我们的模型）：`script/earthformer_eval_extreme_summer_bench.py`、`script/earthformer_eval_seasonal_bench.py`。
- **输入布局**：EarthNet2021 root → `extreme_test_split/{context,target}/<tile>/*.npz`、`seasonal_test_split/{context,target}/...`。CSV 路径相对该 root。
- **输出**：`metrics.json` + `per_sample_metrics.csv`（Extreme）/ `per_pair_metrics.csv`+`per_window_metrics.csv`（Seasonal）。
- **GT 参考行**（附录）：`0.3809 0.1879 1.0000 0.3332 1.0000 0.0000 0.0000`。

## 2. 指标公式（精确，附录 A.2）
- **Pixel-MAE**：全有效像素+波段的 MAE。**N-MAE(NDVI-MAE)**：NDVI 的 MAE。
- **TN-MAE**：在 **GT 谷值帧 t\***（benchmark metadata 记录）处的 NDVI 误差。
- **DAE(Drop Amplitude Error)**：`Δpred = ȳbase − min_t ŷ(t)`；`DAE = |Δpred − Δgt|`。
- **DRA(辅助,可视化用)**：∈[0,1]，1=完全匹配下降幅度，误差超 Δgt 记 0。
- **severity 分箱**：按 **复合极端分 sextreme 的 33.3/66.7 百分位** 分 low/mid/high；箱内对 per-window 值求平均。
  - `sextreme = Δ·(0.55+0.45·rpersist)·(0.70+0.30·rconsec)·(0.40+0.60·q)`（Δ=NDVI下降幅度, rpersist=低于阈值的有效目标帧占比, rconsec=min(nconsec/6,1), q=全窗有效像素比）。
- **DRR(Divergence Reproduction Ratio)**：配对窗口间"发散幅度"的复现比，绝对发散、噪声阈 τ=0.02、最优≈1。
- **DHR(Directional Hit Rate)**：配对 NDVI 差的**符号命中率**；`DHRagg = Σ ni_hits / Σ |Tiτ|`（按每对有效帧数加权）。
- **PDC(Paired Divergence Correlation)**：跨对的**总绝对发散**的 **Spearman 秩相关**（排序保真）。
- 三者正交：DRR=幅度校准/DHR=方向/PDC=排序。

## 3. 构造算法（可复现，附录 A.2 Algorithm 1/2）
- **Extreme Summer**：extreme_test → 逐序列提取 peak/trough NDVI、下降幅度、局部极小(prominence≥0.04)、有效比 → 硬条件(目标有效比≥0.30, 序列级目标下降≥0.35, trough≥0) → 1,447 候选 → 窗口定位+验证(global-trough 62%/multi-trough 27.2%/exhaustive 10.7%) → **1,440 窗口**（窗口质检：context 无效帧>6、target 无效>12、半云帧>15 则弃）。
- **Seasonal Matched-Pair**：seasonal_test → 每地点 3 季节偏移×3 年 30 帧窗口 → 同地同相位跨年配对 36,000 候选 → 三 track 发散评分(气象 Dmeteo/植被轨迹 Dveg(±3帧移容 L2)/像素 Dpixel(≥30%共享有效像素)) → 初始态匹配(Dinit≤40 百分位)→ 3,379 匹配对 → 每 track top-50(每 cube 上限3) → **422 对(844 推理窗口)**。

## 4. 把【我们的模型】跑上去的落地步骤
1. **服务器 clone**：`git clone https://github.com/Luo-Z13/EO-WM` → 拿 `benchmark_csv/*.csv` + `script/*.py`。
2. **数据**：EO-WM 用**原版 EarthNet2021 的 extreme/seasonal(NPZ)**（`pip install earthnet; earthnet.Downloader.get(root,['extreme','seasonal'])`）。
   - ⚠️ **格式差异**：我们本地是 **earthnet2021x(netcdf)**，EO-WM CSV 指向**原版 EarthNet2021(NPZ)**。两条路：(a) 下原版 NPZ（extreme 3972+seasonal 3880，不大）跑它的 eval；(b) 把 CSV 的窗口/对定义映射到我们的 netcdf cube（若 tile/日期 ID 对得上）。**先走 (a) 最省心、也最可比。**
3. **适配器**：EO-WM 的 eval 脚本是 Earthformer 版；写个薄 wrapper 把**我们的 S1a/full24 模型**塞进它的"给 context→出 20 帧预测"接口（我们的 `export_greenearthnet_predictions.py` 已有推理逻辑，改数据读取即可）。
4. **跑**：S1a(physical4) + full24 + 我们的 Direct，过 Extreme Summer + Seasonal Matched-Pair → 拿 TN-MAE/DAE/DHR/DRR/PDC。
5. **成表**：Table B = 我们的行 + EO-WM + Earthformer + SimVP/PredRNN，同表比。

## 5. 诚实边界（写死）
- **这是假设，未实测**：我们在 TN-MAE/DAE/DHR 上到底多少，**跑了才知道**。若也不好看，Table B 救不了，得回头想。**所以第一优先是尽快把 S1a 跑上 Extreme Summer 出个数。**
- EO-WM 是**预印本**（模板/同期强，"已接收先例"待证）。
- 我们的 S1a 训练数据(earthnet2021x train)与 EO-WM 训练数据(原版 EarthNet2021 train) **可能有版本差**——评测在其 test 上、需确认 test cube 可比（走步骤 2a 下原版 test 即可干净）。

## 6. 下一步（GPU 空时第一枪）
- clone EO-WM + 下原版 extreme/seasonal test → 写 wrapper → **S1a 跑 Extreme Summer 出 TN-MAE/DAE**（先只做 Extreme，最小验证假设）。
- 若 TN-MAE 进 Earthformer 档（~0.11）或更好 → Table B 成立、主线锁定。
