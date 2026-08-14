# 85 · 方案 A′ 静态审计报告 + 精度对齐修复方案（plan-a-vits）2026-07-23

> 本轮任务:方案 A′「accuracy-aligned predictive-state world model rescue」。**本文件为 §三静态审计的 durable 记录 + §四/五/六 实现计划。**
> 硬约束(本轮):只改 plan-a-vits 代码 + 本地 smoke;**禁止启动服务器训练、禁止 commit/push、禁止改 doc 84 标题摘要主线、禁止覆盖任何现有 checkpoint/evaluation/log/未提交文件**。方法身份(q→T→O、q=ViT-S、physical4、共享 T、预测必依赖 zh、无旁路)不可破坏。
> 审计经 3 只读子代理取证 + 我逐条复核 file/line。

---

## §三-A Optimizer 审计:**两个已验证缺陷 → ViT-S backbone 实际以 1e-4 训练(10× 预期)**

**builder** `train/train_stage2_earthnet.py:626-656` `build_optimizer`:参数分组**仅按 `_warmup_frozen_parameters` 的 id() 成员**划分(非模块身份、非名字子串)。空则全部进 `lr=1e-4` 组、不创建 `backbone_lr=1e-5` 组。

- **缺陷 1(config 语义)**:`plan_a_stage2v3_vits.yaml:15-18` `encoder.freeze=false` → `obsworld_factory.py:301` 的 `if freeze:` 跳过整块 → `_warmup_frozen_parameters=[]`(:323)。→ `build_optimizer` 全部可训练参数(含**整个 ViT-S**)进 `new_params@1e-4`,backbone 组不创建。**config 注释 `plan_a_stage2v3_vits.yaml:8`「backbone_lr stays 1e-5」是错的。**
- **缺陷 2(DDP bug,doc-84 未料到)**:`train:1568-1573` 先 `model=DDP(model)`,`:1574` 再 `build_optimizer(model)`;而 `:630` `getattr(model, "_warmup_frozen_parameters", [])` **读的是 DDP wrapper**(未 `.module` 解包)→ DDP 不代理任意属性 → **恒返回 `[]`**。对照:梯度抑制辅助 `:700-701` 正确 `model.module if isinstance(model,DDP)`,唯独 build_optimizer 没解包。→ **任何 DDP(正式 8 卡)run 里 warmup 分组永远失效**,连 `freeze=true` 的 direct24 也塌成单组 @1e-4。
- **净效果**:S1a(freeze=false + 8 卡 DDP)**整个预训练 ViT-S 以 1e-4 微调**(而非 1e-5),易破坏 Stage1.5 表征 → 直接相关精度损失。
- **修复(§四-4)**:改为**按模块身份显式分组**(q=core.encoder/phi/state_projector 一组低 lr;T/O/adapter/dynamics/decoder 一组高 lr),**在 DDP 前对 raw model 建 optimizer 或统一 `.module` 解包**;日志打印每组参数量/requires_grad/实时 LR。

## §三-B Loss / Metric / Horizon 审计

- **loss** = `EarthNetForecastLoss`(`models/losses/earthnet_forecasting.py:14`,建于 `train:1643`):**obs=RGBN Huber(w=1.0) + ndvi=masked L1(w=0.5)**,latent/delta/smooth=0(config `stage2_earthnet_v2_direct24.yaml:227-234`;obs=smooth_l1 `:113`;ndvi=masked L1 `:117-118`)。→ **主损失是反射率 Huber,不是 evaluator 计分的 NDVI R²/L2**。
- **NDVI 项只按 clear-sky `target_mask`、无 landcover**(`earthnet_forecasting.py:79,121-125`;`target_mask`←`clear_mask` `earthnet2021.py:752`)。
- **checkpoint primary metric = RGBN MAE(min)**(config `:224-225`;`train:1577-1582,2026-2044,2080-2084`;`MAE`=逐通道反射率 L1 `forecast_metrics.py:31,54`;`NDVI_MAE` 只是旁列)。→ **选的是反射率最优 checkpoint,不是 NDVI 最优**。
- **horizon**:`horizons_per_sample=6`(config`:208`;`train:1365`)。Direct24→`supervise_all=False`→`select_v2_horizon_indices`(`train:734-792`)每步随机取 **6/20**(short/mid/long 分层 + 始终含最后一个 h19);loss 只监督这 6(`train:807-821,1790-1832`)。**validation 评全 20**(无 selected_steps,`train:1063-1067`)。→ 每步 horizon 覆盖不足(B0 训全 20)。
- **修复(§四-1/2/3)**:主损失换 **clear×veg masked-L2-NDVI**(对齐 evaluator)、RGBN Huber 降为低权重辅助;checkpoint 按 **masked-NDVI-MSE/RMSE** 选;**监督全 20 horizon**(或分层但始终含最后)。

## §三-C 训练 mask vs evaluator mask 审计:**严重错位(核心精度 bug)**

- **训练 clear_mask** = 只 `s2_dlmask<=0 & isfinite`(`earthnet2021.py:561-566`v2 / `633-638`physical4),**无 landcover、无 SCL 类**;`target_mask`=clear_mask 直接切片(`:751-752,855-856`)。
- **evaluator**:`official_clear_mask` = `s2_dlmask<1 & s2_SCL∈(1,2,4,5,6,7)`(`greenearthnet_protocol.py:128-135`,`VALID_SCL_CLASSES` `:28`);**打分只在植被 landcover**:`compute_pixel_metrics` `subset_hq`(默认开 `:153`)`frame.landcover<41 & min_ndvi>0 & n_obs≥10 & sigma>0.1`(`:207-214`),landcover←`esawc_lc`(`:193`),land-cover-balanced 聚合(`:377-378`)。
- **逐项**:(a)云定义 MISMATCH(训练二值 vs evaluator SCL 交集);(b)landcover MISMATCH(训练无 vs evaluator 仅植被 10-40);(c)有效预测 MISMATCH(evaluator 额外 NDVI 质量/观测数门)。
- **净效果**:训练像素是评测像素的**严格超集**——模型在大量"评测不计分像素"(非植被/SCL 排除类)上被监督,没有优先拟合评测真正计分的植被清晰像素。
- **band adapter** 无误(`earthnet_band_adapter.py:32-72`,EarthNet[B02,B03,B04,B8A]→canonical[1,2,3,8];NDVI 从 B8A(8)+B04(3),与 evaluator 一致)。
- **修复**:训练 mask 增加 `esawc_lc<41`(植被)+ SCL 有效类,复现 evaluator 的计分像素集。**⚠️ 前置验证**:训练 cube 是否含 `esawc_lc` 与 `s2_SCL`(见"未决点")。

## §三-D 现有结果审计

- 本地工作树**无** plan_a_s1a 评测目录(评测在服务器)。
- 已从 release 拉到本地 `_results_pulled/`:两个 `metrics_en21x.json` + `run_provenance.json` + `train_200epoch.log`。provenance 含:git `d8d2181`(dirty=True)、`resolved_config_sha256`、train/val manifest `files_sha256`(`c2cf69d7…`/`36d886c7…`)、stage15 path、**`horizons_per_sample=6`**。
- **正式写作前需从服务器取回**:完整 score bundle(per-cube metrics、`score_provenance.json`、checkpoint SHA256、manifest hash)。本轮**不因此改文档、不伪造产物**。

---

## 五处错位汇总(A′ Phase 1 逐一修复)
| # | 错位 | 证据 | A′ 修复 |
|---|---|---|---|
| 1 | ViT backbone @1e-4(应 1e-5) | build_optimizer 分组失效(freeze=false + DDP bug) | 按模块身份显式分组 + DDP 解包 |
| 2 | 主损失=RGBN Huber(非 NDVI) | earthnet_forecasting.py:72-104 | 主损失=clear×veg masked-L2-NDVI,RGBN 降辅助 |
| 3 | 训练 mask 无 landcover/SCL | earthnet2021.py:561-566 vs greenearthnet_protocol.py:207-214 | 训练 mask 加 esawc_lc<41 + SCL 有效类 |
| 4 | checkpoint 按 RGBN MAE | train:2026-2044 | 按 masked-NDVI-MSE 选 |
| 5 | 每步只监督 6/20 horizon | train:1790-1832 | 监督全 20(或分层含最后) |

---

## 未决点(实现前需确认/验证)
1. **训练 cube 是否含 `esawc_lc` + `s2_SCL`**?(修复 #3 依赖)。chopped 已确认有 s2_SCL;需查 GreenEarthNet **train** cube 是否有 esawc_lc + s2_SCL。→ 我实现前本地 `ncdump`/xarray 验一个 train cube。
2. **masked-L2-NDVI 的确切定义**:是否完全照 evaluator(landcover<41 + SCL + min_ndvi>0 + n_obs 门),还是训练用简化版(landcover<41 + clear)?evaluator 的 n_obs/sigma 门是 cube 级统计、训练逐 batch 难复现 → 建议训练用「clear ∩ (SCL 有效) ∩ (esawc_lc<41)」,不含 n_obs/sigma 门(那是 eval 端样本筛选)。
3. **NDVI residual head 与现有 RGBN decoder 的关系**:新增 O_ndvi(zh) 直出 NDVI residual(零初始化,初始≈last_valid_ndvi);RGBN decoder 保留为 O 的辅助输出(不作第二条预测旁路)。Table 1 用冻结的 NDVI 输出定义。
4. **physical4 conditioning stats**:A′ 沿用现成 `conditioning_stats_physical4_v1_train_dev.json`(不重开 full24)。

## §五 两条 config(仅初始化来源不同,不覆盖 S1a)
- `plan_a_prime_from_s15.yaml`:加载冻结的原始 Stage1.5 ckpt,q/state_projector 从 S1.5 初始化,Stage2 其余按兼容初始化,新 optimizer。输出 `checkpoints/plan_a_prime_from_s15/`。
- `plan_a_prime_from_s1a_stage2.yaml`:加载完整 S1a Stage2 ckpt(形状兼容 q/context/T/O 全保留),新增 NDVI head 仅初始化新参数,**严禁恢复 S1a optimizer/scheduler**,重建参数组。输出 `checkpoints/plan_a_prime_from_s1a_stage2/`。
- 两者同 manifest/batch/steps/evaluator/physical4/loss/optimizer policy/checkpoint rule。

## §六 Phase 2(本轮只实现接口 + smoke,不远程跑)
composition(direct vs composed,同一 O 解码,各自 endpoint accuracy,预注册 partition,consistency 从 0 ramp) / driver sensitivity(matched/shuffled-donor/mean/显式 mask,干预须改最终 output) / anti-collapse(state std·delta·effective rank) / endpoint guard(退化 ≤ 预注册 ~1%,Table1 与合同同一 checkpoint)。

## 停止门(§八-8,内部决策线,非官方统计等价)
- val NDVI 不明显优于当前 S1a → 停该初始化;
- OOD-t 工程目标 R²≳0.58 / RMSE≲0.155–0.160;更稳 R²≈0.59–0.60 / RMSE≈0.15。

---

## §九 · 正式评测结果与 A/B 决策(2026-07-25 追加)

> 运行:服务器 csy-zg01/65。评估器 commit `a0329636631371a4aaa9a95c75ed0a37d27b8c4f`,协议 `greenearthnet_cvpr2024_chopped_v1`,`--ndvi-source head`。A 两条路线各 4 个 checkpoint(`best` / `epoch100_step_4400` / `epoch150_step_6600` / `epoch200_step_8800`);A′ 两次训练均 8800/8800 完成。A1=rescue(warm-start 自 S1a Stage2),A2=fresh(自 Stage1.5)。

### 9.1 官方 val_chopped(**选模轨**,952 cube,head)
R² 主、RMSE tie-break。

| 路线·ckpt | R² | RMSE | NSE | \|bias\| | RMSE25 |
|---|---|---|---|---|---|
| **A2·epoch100**(A2 winner) | **0.50211** | 0.16953 | −0.2835 | 0.11045 | 0.09482 |
| A2·epoch150 | 0.49868 | 0.16340 | −0.2169 | 0.10361 | 0.09544 |
| A2·best | 0.49860 | 0.16328 | −0.2137 | 0.10348 | 0.09568 |
| A2·epoch200 | 0.49558 | 0.16338 | −0.2169 | 0.10359 | 0.09556 |
| **A1·best**(A1 winner) | 0.49292 | 0.16359 | −0.2231 | 0.10483 | 0.09516 |
| A1·epoch100 | 0.48964 | 0.16477 | −0.2431 | 0.10580 | 0.09504 |
| A1·epoch150 | 0.48894 | 0.16383 | −0.2265 | 0.10472 | 0.09553 |
| A1·epoch200 | 0.48742 | 0.16430 | −0.2304 | 0.10531 | 0.09583 |

**B(同评估器,val):B4 R²=0.51197 / RMSE=0.15089 / \|bias\|=0.09463;B0 R²=0.50848。** → val 同口径 **B4 > B0 > A2-best(0.5021) > A1-best**。注:A2·epoch100 R² 最高但 RMSE 最差(0.1695),R²/RMSE 打架,校准偏差是 A 的主要短板。

### 9.2 官方 ood-t_chopped(**测试轨,只跑一次**,1904 cube,head)

| 路线·ckpt | R² | RMSE | NSE | \|bias\| | RMSE25 | ckpt sha(前12) |
|---|---|---|---|---|---|---|
| **B0** | **0.58421** | 0.14536 | −0.0209 | 0.09645 | 0.08147 | 6def717ec11e |
| **B4** | 0.58252 | **0.14342** | **−0.0018** | **0.09390** | **0.07879** | 2c5d08423671 |
| A2·epoch100(A winner) | 0.55452 | 0.16877 | −0.3407 | 0.11630 | 0.09062 | 57165386ab4a |
| A2·epoch150 | 0.54772 | 0.16493 | −0.2884 | 0.11223 | 0.09299 | fbd2e3d8dd99 |
| A1·best | 0.54388 | 0.16485 | −0.3027 | 0.11135 | 0.08987 | b0c4c61cba81 |
| A2·best | 0.54319 | 0.16686 | −0.3089 | 0.11451 | 0.09542 | 4b16ee4e05d7 |
| A1·epoch100 | 0.54239 | 0.16660 | −0.3323 | 0.11296 | 0.08941 | d98975f4b582 |
| A2·epoch200 | 0.53974 | 0.16589 | −0.2977 | 0.11275 | 0.09459 | f9ce074288f6 |
| A1·epoch150 | 0.53439 | 0.16685 | −0.3268 | 0.11280 | 0.09062 | cfa3d8a8fb56 |
| A1·epoch200 | 0.53284 | 0.16678 | −0.3259 | 0.11260 | 0.09011 | 6ecf3243ea77 |

### 9.3 结论与决策
- **同一 test 轨(ood-t)B 全面领先 A**:A 最好(A2·epoch100)R²=0.5545 / RMSE=0.169 vs **B4 R²=0.5825 / RMSE=0.143**(ΔR²≈+0.028、ΔRMSE≈−0.025;NSE −0.34→−0.002、\|bias\| 0.116→0.094、RMSE25 0.091→0.079 亦全胜)。
- **当前单模型胜出者 = B(取 B4)**:B4 与 B0 的 R² 基本持平(B0 微高 0.0017),但 B4 的 RMSE/NSE/\|bias\|/RMSE25 全更好,均衡最优。
- **差距真实**:A 走的是 "best-of-8 on ood-t"(**在测试集上选模、已构成泄漏、数值被抬高**),即便如此仍全面输给 B → A 当前实力确实落后约 0.03 R² / 0.025 RMSE。
- **停止门对照(§八)**:A 未达 OOD-t 工程目标(R²≳0.58 / RMSE≲0.155–0.160)——R² 差 ~0.03、RMSE 超标 ~0.014。
- **红线**:ood-t 现已 A/B 皆看过 → **不得再用于调 A2+ 的 loss/权重/checkpoint**;A2+ 的选择与目标**只在 val_chopped**,锚点用 **B4 的 val 口径**(R²=0.512 / RMSE=0.151 / \|bias\|=0.09463)。最终唯一冻结模型再跑一次 ood-t 进 Table 1。A 的 best-of-8-on-ood-t 有泄漏,但 A 未进表 → 不污染上报数字。

### 9.4 下一步
A2+ accuracy sprint(逐像素时间对齐的可微代理 + 分层候选 + ≤8 run one-seed 搜索 + 唯一主/回退),目标:**val 同口径逼近/进入 B4 的 Pareto 前沿**。设计文档见后续追加(parts A–E,待发令交付)。

### 9.5 Provenance
- **ood-t manifest**:`num_files=1904`,`files_sha256=5c05025bef233100e147fc0645842ee2b2851a8950f41a900707409e629ab687`,路径 `evaluations/greenearthnet_oodt_20260719_214234/greenearthnet_oodt_chopped_manifest.json`。
- **A ood-t 产物**:`WorldModel2026/evaluations/aprime_oodt_chopped_head_run1/{key}/{predictions,score}`(8 个 key,均 1904/1904)。
- **A val 产物**:`WorldModel2026/evaluations/aprime_greenval/{A1,A2}/{ckpt}/score`。
- **B ckpt**:`WorldModel2026-planb/checkpoints/plan_b_b4a/checkpoint_best.pt`(2c5d08423671)、`.../plan_b_b0/checkpoint_best.pt`(6def717ec11e);B ood-t 产物 `WorldModel2026-planb/evaluations/plan_b_b4a_post/oodt/{b4,b0}/score`。
- **A ckpt 目录**:`WorldModel2026/checkpoints/{plan_a_prime_from_s1a_stage2(=A1),plan_a_prime_from_s15(=A2)}`。
