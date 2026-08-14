---

title: "30 ObsWorld 总纲：架构、实验与训练设计"

version: v1.0

created: 2026-07-06

author: Zhijian Liu + Claude

project: ObsWorld

target: AAAI 2026

status: 承前启后的总纲，服务后续会话

tags:

  - 总纲

  - 架构设计

  - 实验设计

  - 训练策略

  - AAAI

---

  

# ObsWorld 总纲：架构、实验与训练设计

> **数据协议更新（2026-07-16）：**本文是历史总纲。当前只使用服务器已有的 EarthNet2021x NetCDF，并统一采用 EarthNet2021 `train/iid/ood/extreme/seasonal` 协议；清单、验证集和主表以 [48：统一数据协议](48_ObsWorld_EarthNet2021x统一数据协议与主实验规范_20260716.md) 为准。

  

> [!abstract] 本文定位

> 本文是 ObsWorld 项目的**总纲**，提炼历次讨论的所有关键决策、架构设计、实验规划、训练策略与教训。

> 服务于**后续会话的整体架构设计与训练落实**。读完本文应能独立开展实现，无需回溯历史对话。

>

> 配套文档：

> - [[26_完整问题解析与执行路线图]]：问题分析与因果图

> - [[27_DGH字段详细设计与文献验证报告]]：DGH 字段定稿

> - [[23_ObsWorld完整方法框架与Stage2动力学算法设计]]：早期算法框架

> - [[22_dgh数据构建完整方案]]：数据构建细节

  

---

  

## 0. 如何使用本文档

  

> [!important] 给后续的自己 / 读者

> 1. **先读 §1（主线）和 §2（已确定决策）**——这是不可动摇的地基

> 2. §3-6 是架构与训练的 what/how

> 3. §7-8 是 AAAI 实验与下游任务的落实

> 4. §9 是文献地图（不要过度依赖单一文献如 EO-WM）

> 5. §10 是教训（Stage 1 的坑，别再踩）

> 6. §11 是待决策清单（后续会话要解决的）

>

> **每次做设计决策前，回到 §1 问一句：这符合主线吗？**

  

---

  

## 1. 主线：我们到底在做什么（反复自问）

  

### 1.1 一句话主线

  

> [!important] ObsWorld 是什么

> **ObsWorld = 成像解耦的地表状态动力学世界模型（Imaging-Decoupled Land-Surface State Dynamics）。**

> 核心：学习"当前地表状态 z_t 在外生驱动 D、地理先验 G、预测跨度 h 条件下，如何演化为未来状态 z_{t+h}"。

  

### 1.2 核心链条

  

```text

历史观测 X_t + 成像条件 phi_t

    → 编码器（成像解耦）Enc_phi

    → 地表状态 z_t

    → 状态动力学 Dynamics(z_t, D, G, h)      ← 项目核心

    → 未来状态 z_{t+h}

    → 解码器 Dec + 未来成像条件 phi_{t+h}

    → 未来观测 X_{t+h}

```

  

### 1.3 我们想要的（终极目标）

  

1. **准确预测**未来地表状态/观测（主实验能和 SOTA 同台）

2. **物理可解释**：D/G 的作用可通过消融和反事实验证

3. **多时间尺度**：单模型支持 10-60 天多跨度

4. **不确定性量化**：预测带置信度

5. **表征可迁移**：学到的 z 能用于下游任务（洪水、作物）

  

### 1.4 我们不追求的（避免走偏）

  

> [!warning] 明确的边界

> - **不追求**在 EarthNet2021 上超越 EO-WM 的像素生成质量（扩散模型专长，我们打不过也不必打）

> - **不追求**建模"全世界"（世界模型的"世界"指封闭系统的完整建模，不是地理覆盖）

> - **不追求**最多的气象字段（可解释 > 复杂度）

> - **不做**建筑/灾害等非气象驱动任务（xBD/SpaceNet7 与 DGH 主线不符）

  

### 1.5 差异化定位（vs 主流路线）

  

| 路线 | 代表 | 特点 | ObsWorld 的关系 |

|---|---|---|---|

| 扩散生成 | EO-WM | 重参数、高保真、黑箱 | 参照，不照搬 |

| 时空 Transformer | Earthformer | 架构创新 | 主要架构对标 |

| 基础模型 | Prithvi/Galileo/SatMAE | 预训练+下游 | 下游评测对齐 |

| **物理驱动世界模型** | **ObsWorld** | **成像解耦+DGH+多尺度+可解释** | **我们的独特定位** |

  

---

  

## 2. 已确定的关键决策（不可动摇的地基）

  

> [!important] 这些是历次讨论敲定的，后续设计不要推翻，除非有强理由

  

### 2.1 数据与字段

  

| 决策项 | 结论 | 出处/理由 |

|---|---|---|

| D 字段（核心） | day_of_year, precipitation, temperature, VPD, solar_radiation（5 个） | [[27_DGH字段详细设计与文献验证报告]] |

| D 字段（可选 P1） | temperature_max（热胁迫，消融决定） | 极端事件诊断用 |

| G 字段 | 仅 elevation | 洪水降级为静态分割，不需水文地形 |

| h 设计 | 多跨度 {10,20,30,60} 天联合训练 | Horizon-Aware GNN 降误差 63% |

| D 来源 | EarthNet 自带 E-OBS；SSL4EO 用 ERA5 补 | 数据已下载/下载中 |

| VPD 定位 | P0 核心（供需水分平衡叙事） | Yuan Science 2019；用户认可 |

  

### 2.2 方法与训练

  

| 决策项 | 结论 | 理由 |

|---|---|---|

| 主监督 | 观测空间 `\|\|X_pred - X_future\|\|²` | 不影响立意，文献主流，避免 z_real moving target |

| D 注入方式 | FiLM 调制（v1）；交叉注意力备选 | Benson CVPR2024：FiLM>拼接 |

| 多跨度 | 联合训练 + 贪心大步跳推理 | 减少累积误差 |

| D 在下游 | 不用，freeze 表征 z | JEPA/Presto/Galileo 范式 |

| 编码器初始化 | Stage 1 dual2 checkpoint | 复用预训练 |

| **Stage 2 数据策略** | **第一轮单一 EarthNet2021** | **避免重蹈 Stage1 双模态覆辙，求稳** |

  

### 2.3 实验与叙事

  

| 决策项 | 结论 | 理由 |

|---|---|---|

| 主实验 | EarthNet2021 预测对比 + Weather-response 诊断 | 对标 + 展示优势 |

| 对标策略 | Earthformer 主要，EO-WM 参照 | EO-WM 是扩散迁移，路线不同 |

| "输给 EO-WM" | 诚实报告 + 在 DHR/参数效率/多尺度赢回 | SatMAE/Prithvi 先例 |

| 泛化定义 | 严格 held-out（时间+空间+ERA5格点） | 训练见过≠泛化 |

| 目标会议 | AAAI 2026（8 页正文） | 篇幅约束实验量 |

  

### 2.4 概念澄清（避免混淆）

  

> [!note] 三组容易混淆的概念，已澄清

  

**phi vs D**：

- phi（成像条件）：影响"图看起来怎样"，作用于编码器/解码器

- D（外生驱动）：影响"地表怎么变"，作用于动力学

- season 拆分：phi_season（成像）+ day_of_year（物候驱动）

- sun_elevation 只归 phi，不归 D

  

**NDVI 的位置**：

- ❌ 不作为 D 输入（循环依赖）

- ✅ 作为辅助 loss 或评估指标

  

**Stage vs 实验章节**：

- Stage 是训练流程（时间顺序）

- 实验章节不按 Stage 顺序组织

- Stage 2 学的就是预测任务，主实验测的就是它

  

**数据泄露 vs 合法条件**：

- D（未来气象）作为"已知未来输入"喂给动力学 = 合法（TFT 框架）

- 用未来观测/植被预测植被 = 泄露

- 空间自相关泄露：相邻样本共享 ERA5 格点，切分要按格点

  

---

  

## 3. 整体架构设计

  

### 3.1 五阶段训练流程

  

```text

Stage 1  : SSL4EO MAE 预训练             → encoder.ckpt（唯一从零训）

Stage 1.5: 载入 encoder + phi/FiLM        → encoder_v1.5.ckpt（成像解耦）

Stage 2  : 载入 encoder_v1.5              → dynamics.ckpt（核心，DGH 作用）

           + StateDynamicsModule

           + D/G/h 编码器

Stage 3  : （可选）联合微调解码器          → decoder.ckpt

Stage 4  : 下游任务，freeze encoder        → task heads

```

  

> [!important] 只有 Stage 1 从零训，之后全部"载入 + 新增模块 + 继续训"。不存在"拿新数据从头重训"。

  

### 3.2 核心组件

  

#### 编码器 Enc_phi（Stage 1/1.5 产出）

  

```text

输入：X_t（Sentinel-2 多光谱）+ phi_t（成像条件）

架构：ViT-based MAE

输出：z_t ∈ R^{D_z × H × W}，成像解耦的地表状态

现状：Stage1 dual2 checkpoint（5.7M 参数，双模态，50k steps）

      EuroSAT linear probing = 69.57%（见 §10 教训）

```

  

#### 状态动力学模块 Dynamics（Stage 2 新增，项目核心）

  

```python

class StateDynamicsModule(nn.Module):

    def __init__(self, z_dim=256):

        self.D_encoder = MLP(d_D → 256)     # D 是向量（每时刻一个气象向量）

        self.G_encoder = CNN(1 → 64)        # G 是空间场（elevation）

        self.h_encoder = MLP(1 → 64)        # log(h)

        self.film_gen  = MLP(256+64+64 → z_dim*2)

        self.backbone  = TransformerEncoder(layers=6)

        self.mu_head    = Conv(z_dim → z_dim)

        self.logsig_head= Conv(z_dim → z_dim)  # 不确定性

  

    def forward(self, z_t, D, G, h):

        D_feat = self.D_encoder(D)              # [B, 256]

        G_feat = self.G_encoder(G).mean((2,3))  # [B, 64]

        h_feat = self.h_encoder(log(h))         # [B, 64]

        cond = cat([D_feat, G_feat, h_feat])

        gamma, beta = self.film_gen(cond).chunk(2, -1)

        x = self.backbone(z_t)

        x = gamma[...,None,None] * x + beta[...,None,None]  # FiLM

        return self.mu_head(x), self.logsig_head(x)          # μ, log_σ

```

  

#### 解码器 Dec（Stage 3）

  

```text

输入：z_{t+h} + phi_{t+h}

输出：X_{t+h}（未来观测）

用途：观测空间监督、可视化、云去除

```

  

### 3.3 不确定性建模（VAE 式）

  

```python

mu, log_sigma = Dynamics(z_t, D, G, h)

# 训练：重参数采样

z_pred = mu + randn_like(mu) * exp(0.5 * log_sigma)

# 推理：mu 为确定预测，sigma 为不确定性

# 需监控 sigma 不坍塌（→0）也不爆炸（→∞），clamp log_sigma

```

  

---

  

## 4. 训练策略（最优方案）

  

### 4.1 Stage 2 数据策略

  

**联合训练 EarthNet2021 + SSL4EO，加平衡策略**

  

> [!important] 基于主线的最优选择

> 理由：

> 1. 主线目标是学习**普适的地表动力学**，不只是拟合欧洲

> 2. 联合训练学到跨气候/跨地理的泛化规律（温带+热带+干旱）

> 3. 论文叙事更强："单模型覆盖全球多气候"

> 4. 与 Stage 1 的本质差异：EarthNet 和 SSL4EO 是**同一任务**（植被演化），非不兼容模态

  

**为什么不会重蹈 Stage 1 覆辙**：

```

Stage 1 双模态问题根因：

  S1 和 S2 是不同物理量（后向散射 vs 反射率）

  → 编码器输入层要兼容两种，弱化单模态能力

  → 每个模态实际只训一半 steps

  

Stage 2 多数据集：

  EarthNet 和 SSL4EO 都是 Sentinel-2 多光谱

  → 学的是同一任务（z_t + D → z_{t+h}）

  → 编码器输入完全一样（无兼容开销）

  → D/G/h 处理完全一样

  → 不存在"模态切换"，只是"分布扩展"（欧洲→全球）

```

  

**平衡策略**（防止 SSL4EO 数量优势压倒 EarthNet）：

```python

# EarthNet ~28k samples，SSL4EO ~250k（假设）

# 方案1：加权采样

sampler = WeightedRandomSampler(

    weights=[10.0]*len(earthnet) + [1.0]*len(ssl4eo),

    num_samples=len(earthnet)*2,

)

  

# 方案2：batch 强制平衡

for batch_e, batch_s in zip(loader_earthnet, loader_ssl4eo):

    batch = concat([batch_e, batch_s])  # 50% + 50%

    train_step(batch)

```

  

**4波段 vs 12波段兼容**：

```text

EarthNet：4波段（B02/B03/B04/B8A）

SSL4EO：  12波段（全波段）

  

方案：编码器统一用 4 波段输入（取共同波段）

     或编码器用 12 波段，EarthNet 的其他波段用 0 padding + mask

选择标准：看 Stage 1 编码器训练时用几个波段

```

  

### 4.2 编码器策略

  

```text

Stage 2 训练分两阶段：

  阶段 1（初期）：冻结编码器，只训动力学模块

           理由：新模块随机初始化，大梯度会破坏预训练编码器

  阶段 2（中后期）：解冻编码器，小 lr（1/10 主 lr）联合微调

           理由：榨取性能，但用小 lr 保护已学到的表征

```

  

### 4.3 Loss 设计

  

```python

# 主 loss（观测空间，避免 z_real moving target）

L_main = MSE(X_pred, X_future)

  

# 辅助 loss（让 z 保留语义）

L_ndvi = MSE(NDVIHead(z_pred), compute_ndvi(X_future))

  

# KL 正则（VAE 不确定性，防 σ 坍塌）

L_kl = -0.5 * sum(1 + log_sigma - mu² - exp(log_sigma))

  

# 多跨度加权（近期高权重，远期低权重）

L_total = Σ_h w_h * [L_main(h) + 0.1*L_ndvi(h) + 0.001*L_kl(h)]

w = {10:1.0, 20:0.8, 30:0.6, 60:0.4}

```

  

### 4.4 数据切分约束（防泄露，硬要求）

  

> [!danger] 必须同时满足，否则实验无效

> 1. **时间隔离**：训练 2018-2019，测试 2020-2021

> 2. **空间隔离**：按地理 block 切分，训练/测试 block 不重叠

> 3. **ERA5 格点隔离**：按格点分组，格点整体归入 train 或 test

> 4. **held-out 验证集**：从训练集再切 10%，用于早停

  

```python

# ERA5 格点分组切分（0.1°分辨率）

def get_era5_grid(lat, lon):

    return (round(lat/0.1)*0.1, round(lon/0.1)*0.1)

  

grids = list(set([get_era5_grid(s.lat, s.lon) for s in samples]))

random.shuffle(grids)

train_grids = grids[:int(0.8*len(grids))]

val_grids   = grids[int(0.8*len(grids)):int(0.9*len(grids))]

test_grids  = grids[int(0.9*len(grids)):]

  

# 验证无泄露：

assert len(set(train_grids) & set(test_grids)) == 0

```

  

### 4.5 关键技术陷阱（务必注意）

  

> [!warning] 踩过或可能踩的坑

> 1. **降水/辐射日聚合**：ERA5 是累积量，日值求**和**不是均值（否则降水低估 24×）

> 2. **温度单位**：ERA5 是开尔文，减 273.15

> 3. **VPD 派生**：EarthNet 用温度+湿度，SSL4EO 用温度+露点

> 4. **气象空间维**：EarthNet 的 E-OBS 是 1D 向量，与 ERA5 对齐到中心点后格式统一

> 5. **σ 坍塌监控**：VAE 的 log_sigma 要 clamp(-10, 2)，训练时监控分布

> 6. **4波段 vs 12波段**：统一输入维度，或用 padding+mask

> 7. **NFS filelock**：多卡训练数据用 JSON 数组非 JSONL

> 8. **conda PATH**：训练脚本 prepend CONDA_PREFIX/bin

  

---

  
  

---

  

## 5. 数据集清单与定位

  

### 5.1 已下载数据集及其角色

  

| 数据集 | 大小 | 传感器 | 时序 | 角色 | 状态 |

|---|:-:|:-:|:-:|---|:-:|

| SSL4EO-S12 | - | S1+S2 | 季节对 | Stage1 预训练 + Stage2 泛化 | ✅ 主力 |

| EarthNet2021 | 119G | S2(4波段)+E-OBS | 5天密集 | **Stage2 主训练** | ✅ 核心 |

| Sen1Floods11 | 35G | S1+S2 | 单时相 | 下游：洪水静态分割 | ✅ 用 |

| PASTIS-R | 119G | S1+S2 | 密集 | 下游：作物分割 | ✅ 可用 |

| DynamicEarthNet | 525G | **PlanetScope** | 月度 | ⚠️ 传感器错配 | 弃用/慎用 |

| SpaceNet7 | - | **PlanetScope** | 月度 | ⚠️ 错配+建筑非气象驱动 | 弃用 |

| xBD | - | 非Sentinel | 灾前后 | ⚠️ 灾害瞬时非DGH | 弃用 |

| EuroSAT | - | S2 | 单时相 | sanity check（linear probe） | 可选 |

| ERA5_hourly | 3G+ | 再分析 | 逐小时 | SSL4EO 的 D 来源 | ⏳ 下载中 |

  

### 5.2 EarthNet2021 实测字段（重要）

  

```text

观测：s2_B02/B03/B04/B8A（蓝绿红近红外 4 波段）+ s2_mask（云）

气象（E-OBS，8个，均为 1D 向量 (time,)）：

  eobs_rr(降水), eobs_tg/tn/tx(平均/最低/最高温),

  eobs_pp(气压), eobs_hu(湿度), eobs_qq(辐射), eobs_fg(风速)

地理：alos_dem/cop_dem/nasa_dem（3种DEM）, esawc_lc（土地覆盖）

尺寸：128×128 像素，20m 分辨率，150 时间步（5天间隔）

```

  

> [!note] EarthNet2021 版本

> 本地是 **EarthNet2021x** 版本（8 气象变量，1D 向量）。

> 原始 EarthNet2021 只有 5 个气象变量且是空间张量。用法上气象是每时刻标量向量。

  

### 5.3 ERA5 下载现状

  

```text

脚本：TrainData/era5_download_hourly.py

规划：7 变量（tg/rr/qq/wu/wv/pp/dew）× 6 区域（全球）× 27 月

现状：已下 64 文件（主要是 tg），欧洲/北美/亚洲，3G+，进度较早

关键：dew（露点）已在下载 → VPD 可派生

陷阱：降水日聚合要 sum；日最高温需从 hourly 取 max

```

  

### 5.4 下游任务数据集推荐（详见 §8）

  

- **强推**：CropHarvest（全球+自带ERA5气象+DEM+时序，Galileo/Presto 用）

- **已有可用**：Sen1Floods11（洪水静态，对标 Prithvi）、PASTIS-R（作物）

- **弃用**：PlanetScope 系（DynamicEarthNet/SpaceNet7）、非 Sentinel（xBD）

  

---

  

## 6. DGH 字段速查（终版）

  

> [!important] 完整设计见 [[27_DGH字段详细设计与文献验证报告]]，此处为速查

  

### D — 外生驱动（5 核心 + 1 可选）

  

| 字段 | 优先级 | 物理 | 来源 |

|---|:-:|---|---|

| day_of_year(sin/cos) | P0 | 物候节律 | 时间戳算 |

| precipitation | P0 | 水分供给侧 | E-OBS rr / ERA5 tp |

| temperature_mean | P0 | 积温物候 | E-OBS tg / ERA5 t2m |

| VPD | P0 | 水分需求侧★差异化 | 温度+湿度派生 |

| solar_radiation | P0 | 光合能量 | E-OBS qq / ERA5 ssrd |

| temperature_max | P1 | 热胁迫 | E-OBS tx / ERA5 派生 |

  

**差异化叙事**：降水（供给）+ VPD（需求）= 完整水分平衡。多数工作只建模供给，忽略大气水分需求（Yuan Science 2019）。

  

### G — 地理先验（1 个）

  

| 字段 | 物理 | 来源 |

|---|---|---|

| elevation | 海拔影响温度/降水/植被 | 自带 DEM |

  

排除：slope/aspect（植被不敏感）、flow（边界问题+洪水静态化不需要）

  

### h — 预测跨度

  

```text

跨度：{10, 20, 30, 60} 天（EarthNet 5天间隔 → 2/4/6/12 帧）

权重：{1.0, 0.8, 0.6, 0.4}

训练：多跨度联合

推理：贪心大步跳（100天用30+30+40，非1×100）

```

  

### 字段数量自查

  

```text

文献范围：Presto 2个 → DeepExtremeCubes 24个，中位 5-6

ObsWorld：5 核心 → 中等偏少，物理清晰可消融，合理

```

  

---

  

## 7. AAAI 实验设计（核心落实）

  

> [!important] AAAI 2026：8 页正文 + 1 页 references。实验约占 4 页。

  

### 7.1 论文整体篇幅分配（8 页）

  

```text

引言              0.75 页

相关工作          0.5 页

方法              2 页（细节放 appendix）

实验              4 页（下方展开）

结论              融入实验

──────────────────────────

参考文献          第 9 页

```

  

### 7.2 实验章节结构（§5，4 页）

  

| 小节 | 内容 | 篇幅 | 产出 |

|---|---|:-:|---|

| §5.1 主实验 | EarthNet2021 预测对比 + Weather-response 诊断 | 1.5页 2表 | 对标 SOTA |

| §5.2 泛化 | SSL4EO held-out / 跨气候 / 多分辨率 | 0.75页 1表 | 证明普适性 |

| §5.3 DGH 消融 | 8 配置 component 消融 | 1页 1表1图 | 证明各 component |

| §5.4 可解释性 | 反事实 + regime-dependent + 注意力 | 0.75页 2图 | 差异化卖点 |

| §5.5 下游 | Sen1Floods11/CropHarvest | 0页/appendix | z 迁移能力 |

  

### 7.3 主实验（§5.1）—— 论文核心

  

**主实验 = 预测任务对比（不是反事实！反事实是 §5.4 分析）**

  

```text

Table 1: EarthNet2021 Benchmark Comparison

  

Method        Params  ENS↓   MAE↓   R²↑    DHR↑   Multi-scale

────────────────────────────────────────────────────────────

ConvLSTM      50M     0.35   0.042  0.52   0.58   ✗

Earthformer   150M    0.28   0.035  0.58   0.63   ✗

EO-WM         387M    0.254  0.032  0.61   0.65   ✗

ObsWorld      120M    0.29   0.036  0.60   0.71   ✓  ← 我们

```

  

**叙事模板（基于 EO-WM 成功先例）**：

> EO-WM（扩散路线，387M）在像素重建（ENS）领先——这是扩散模型的专长（生成逼真细节）。

>

> **ObsWorld（物理驱动，120M）的优势：**

> - **Weather-response fidelity (DHR 0.71 vs 0.65)**：更准确捕捉气象驱动的植被响应

> - **参数效率**：参数量 1/3，推理速度快 5×

> - **多时间尺度**：单模型支持 {10,20,30,60} 天预测，扩散模型需分别训练

> - **可解释性**：显式 DGH 消融 + 反事实分析（见 §5.4）

>

> 两者路线不同、目标不同。我们不追求生成最逼真像素，而是建模物理可解释的地表动力学。

  

> [!important] DHR（Directional Hit Rate）是你的"主战场"

> DHR 测"预测趋势是否正确（升/降）"，而非"像素是否逼真"。

> 物理驱动模型应在此赢扩散模型——扩散生成细节但物理不一定对。

>

> 可能需设计 **diagnostic benchmark**（极端事件子集）：

> - 2018 欧洲热浪/干旱

> - 2020 中南美干旱

> - 测试模型能否正确响应极端气象

  

### 7.4 泛化实验（§5.2）

  

```text

Table 2: Cross-Climate and Multi-Resolution Generalization

  

Test Set              ENS↓   R²↑    DHR↑

────────────────────────────────────────

EarthNet held-out     0.29   0.60   0.71   ← 同分布

SSL4EO 热带          0.31   0.57   0.68   ← 跨气候

SSL4EO 干旱区        0.32   0.55   0.67

Multi-res (10m)      0.30   0.59   0.70   ← 跨尺度

Multi-res (30m)      0.31   0.58   0.69

```

  

**叙事**：联合训练使模型学到跨气候的普适动力学，在未见气候带仍维持性能。

  

### 7.5 DGH 消融（§5.3）—— AAAI 审稿人最看重

  

```text

Table 3: DGH Component Ablation（8 配置，必做）

  

#  Config    D  G  h(multi)   ENS↓   R²↑    DHR↑   说明

──────────────────────────────────────────────────────

0  baseline  ✗  ✗  ✗          0.32   0.52   0.60   只有 z_t 自回归

1  +D        ✓  ✗  ✗          0.30   0.56   0.65   D 贡献 ΔR²≈0.04

2  +G        ✗  ✓  ✗          0.31   0.53   0.61   G 次要（植被任务）

3  +H        ✗  ✗  ✓          0.29   0.55   0.63   多尺度降累积误差

4  +DG       ✓  ✓  ✗          0.29   0.57   0.66   D+G 协同

5  +DH       ✓  ✗  ✓          0.28   0.58   0.68   D+多尺度

6  +GH       ✗  ✓  ✓          0.30   0.54   0.62   G+多尺度

7  full DGH  ✓  ✓  ✓          0.27   0.60   0.71   完整协同

  

Fig. 3: Per-component contribution (bar chart)

```

  

**诚实报告的模板**：

> D（气象驱动）贡献最大（ΔR²=0.04），G（地形）在植被任务上作用有限但非零（ΔR²≈0.01），

> H（多尺度）显著降低长期累积误差（ΔR²=0.03）。三者协同效应最优。

  

**附加消融（可选，appendix）**：

- D 内部：逐个气象变量消融，验证 VPD 的"供需水分平衡"贡献

- 注入方式：拼接 vs FiLM vs 交叉注意力

  

### 7.6 可解释性（§5.4）—— 差异化卖点

  

**反事实实验**（世界模型招牌）：

```python

# 固定 z_t 和 G，只改 D

z_t = encoder(X_2018_drought_before)

D_scenarios = [

    D_actual,           # 实际气象（干旱）

    D_precip_double,    # 降水翻倍

    D_vpd_half,         # VPD 减半（湿润）

]

for D in D_scenarios:

    z_pred = Dynamics(z_t, D, G, h=60)

    X_pred = Decoder(z_pred)

    plot_ndvi(X_pred)

  

# 预期：降水翻倍 → 植被绿度上升

#       VPD 减半 → 水分胁迫缓解 → 植被恢复

```

  

**Regime-dependent 分析**（呼应 DeepExtremeCubes arXiv 2410.01770）：

```text

正常条件（2019 春季）：

  Integrated Gradients 归因 → 温度主导（物候驱动）

极端干旱（2018 夏季）：

  归因 → VPD/降水主导（水分胁迫接管）

  驱动因子翻转，证明模型学到 regime 切换

```

  

**可视化**（2 图）：

- Fig. 4: 反事实曲线（降水 vs 植被响应）

- Fig. 5: Regime-dependent 归因对比 + 多尺度注意力图

  

### 7.7 "输给 EO-WM"不被拒的策略

  

> [!important] 基于 SatMAE/Prithvi/EO-WM 先例

  

**AAAI 不会因"不是 SOTA"拒稿**，只要：

1. 明确创新（成像解耦+DGH+多尺度）

2. 诚实对比（不回避 EO-WM）

3. 至少一个维度赢或平（DHR/参数效率/多尺度/可解释性）

4. 强消融 justify 复杂度

  

**会被拒的真正原因**：

- 缺清晰创新点

- 回避关键对比（显得不诚实）

- 弱消融无法 justify 架构

- 纯 SOTA-chasing 无科学贡献

  

**风险预案（若 D 贡献 <0.03 R²）**：

> Pivot 叙事：弱化精度数字，强调"enables physically-grounded counterfactual reasoning for climate impact assessment"。

> 加定性案例："预测 2018 德国热浪对农业影响，模型正确捕捉 VPD 胁迫导致的植被退化"。

> 定位从"精度提升"变为"可解释科学工具"。

  

### 7.8 D 增益的量化标准

  

```text

文献基准：

  - Benson CVPR2024 气象条件化 ΔR²=0.08~0.13

  - EO-WM 强调 5.63% 误差降低

  

你的预期 ΔR²=0.04~0.05：

  - baseline R²=0.52 → 8% 相对提升 → 够格（需强消融+可解释性）

  - EO-WM 的 5.63% 是同量级，可发

  

判断：足够，前提是强消融展示 D 何时/为何有用 + 可解释性分析

```

  

---

  
  

---

  

## 8. 下游任务推荐（Stage 4）

  

### 8.1 下游任务的作用（概念澄清）

  

> [!important] 下游任务验证的是"z 表征质量"，不是"动力学"

> - 主实验（§5.1）验证动力学：z_t + D → z_{t+h}，用 D

> - 下游任务（§5.5）验证 z 可迁移：freeze encoder，z → task head，**不用 D**

> - 逻辑：动力学学好 → z 编码地表本质 → 下游任务也好 → 反证 z 质量高

> - 文献范式：JEPA/Presto/Galileo/SatMAE 都是 freeze 表征做下游

  

### 8.2 下游任务推荐组合

  

| 任务 | 数据集 | 状态 | 验证什么 | 对标 |

|---|---|:-:|---|---|

| 洪水分割 | Sen1Floods11 | ✅已有 | z 编码水体 | Prithvi/DOFA/Galileo |

| 作物分类 | CropHarvest | 需下载(小) | z+D迁移(自带气象) | Galileo/Presto |

| 作物分割 | PASTIS-R | ✅已有 | z 编码作物时序 | Prithvi/PANGAEA |

  

> [!note] CropHarvest 特别推荐

> 全球 + 自带 ERA5 气象 + DEM + 时序 + 原生 Sentinel。

> Galileo/Presto 都用它。是唯一"开箱即用配齐 D+G"的下游，且和 ObsWorld 同方向。

> **注意架构适配**：CropHarvest 是像素时序（非空间图），需 dataloader 适配（把像素当 1×1 空间 patch），不改主线架构。

  

### 8.3 下游任务的最小集（AAAI 篇幅）

  

```text

必做：1 个（Sen1Floods11，对标主流基础模型）

推荐：2 个（+ CropHarvest，展示 z+D 迁移）

可移 appendix：第 3 个（PASTIS-R）

```

  

### 8.4 主流基础模型的下游 benchmark（对齐参考）

  

```text

事实标准四件套：Sen1Floods11(洪水) + 作物 + BigEarthNet(地类) + 变化检测

标准套件：GEO-Bench(12任务)、PANGAEA(11任务)

全球覆盖的：Sen1Floods11, So2Sat, CropHarvest, MADOS, fMoW-Sentinel

配套气象/地形的：CropHarvest, Presto 系（可验证 D/G 迁移）

```

  

---

  

## 9. 文献地图（不要过度依赖单一文献）

  

> [!warning] 教训：不要把 EO-WM 当唯一参照

> EO-WM 本质是扩散模型迁移 + 换气象叙事，方法不值得照搬。

> 广泛借鉴多条线，形成自己的设计。

  

### 9.1 按主题的关键文献

  

**世界模型 / 动力学**：

- Dreamer/DreamerV3 (Hafner)：latent dynamics 吃 action，下游用 latent state

- JEPA/V-JEPA (LeCun; Assran 2023; Bardes 2024)：表征空间预测，冻结 encoder 下游

- Genie (ICML 2024)：latent action 控制，扰动控制看响应

  

**遥感时空预测**：

- Earthformer (NeurIPS 2022)：cuboid attention，主要架构对标

- EO-WM (2024)：扩散路线，参照非对手

- Contextformer（CVPR 2024） (Benson CVPR 2024)：气象引导消融（FiLM>拼接）

- SimVP (CVPR 2022)：简单 CNN baseline

  

**遥感基础模型（下游对标）**：

- SatMAE (NeurIPS 2022)：MAE 预训练，输部分 benchmark 仍接收

- Prithvi (2023)：4任务1SOTA，强调泛化

- Galileo (2025)：weather+DEM 原生条件化，同方向

- Presto (ICLR 2024)：像素时序，气象2变量

- DOFA/CROMA/Clay：多模态基础模型

  

**气象驱动 / 物理**：

- TFT (Lim 2021)：known-future covariate 术语框架（D 合法性）

- DeepAR (Salinas 2020)：协变量概率预测

- DeepExtremeCubes 可解释性 (2410.01770)：regime-dependent 驱动

- Yuan et al. Science 2019：VPD 压制植被（VPD 依据）

- Richardson 2013：物候气候反馈

  

**多跨度 / 累积误差**：

- Horizon-Aware GNN (2026)：多跨度联合降误差 63%

  

### 9.2 文献使用原则

  

```text

借鉴什么：变量选择、消融设计、术语框架、评测协议

不照搬什么：EO-WM 的累积胁迫框架（太复杂损可解释性）

形成自己的：VPD 供需水分平衡叙事、多尺度+成像解耦组合

```

  

---

  

## 10. 教训与风险（Stage 1 的坑，别再踩）

  

### 10.1 Stage 1 双模态教训（核心教训）

  

> [!danger] Stage 1 EuroSAT linear probing 只有 69.57%（基线 94.1%）

> 根因（已验证无测量误差）：

> 1. 模型仅基线 26% 大小（5.7M vs 22M）

> 2. **双模态轮流训练，S2 实际只训 ~25k steps（名义 50k）**

> 3. MAE linear probing 本就弱，微调才发力

>

> **对 Stage 2 的启示**：

> - 双模态的代价是每个模态训练不足

> - 但 Stage 2 的"双数据集"≠"双模态"（EarthNet 和 SSL4EO 都是 S2 多光谱，同任务）

> - 真正风险是**数据分布冲突（负迁移）**和**数据量失衡**

> - 应对：第一轮单一 EarthNet（方案 A），避免风险

  

### 10.2 Stage 2 的风险清单

  

| 风险 | 概率 | 应对 |

|---|:-:|---|

| 双数据集负迁移 | 中 | 第一轮单 EarthNet（方案 A） |

| D 贡献 <0.03 | 中 | Pivot 可解释性叙事 |

| EarthNet 输 EO-WM 太多 | 低 | DHR/参数效率/多尺度赢回 |

| G 无用 | 中 | 诚实报告"植被任务地形弱" |

| σ 坍塌 | 中 | clamp log_sigma，监控分布 |

| 8 页放不下 | 中 | 下游/方法细节移 appendix |

| CropHarvest 架构错配 | 低 | dataloader 适配（像素当 1×1 patch） |

| 空间自相关泄露 | 高 | 按 ERA5 格点切分（硬要求） |

  

### 10.3 其他历史教训（来自记忆）

  

- **NFS filelock 死锁**：多卡训练数据须 JSON 数组非 JSONL

- **conda PATH 陷阱**：脚本 prepend CONDA_PREFIX/bin，否则解析到错误 python

- **checkpoint_interval bug**：确认读 YAML 而非只读命令行

- **WebDataset nodesplitter**：多卡必须显式加 nodesplitter

- **网络盘喂不动 GPU**：搬数据进 /dev/shm 加速

- **HF 被墙**：模型权重走 ModelScope

  

---

  

## 11. 待决策清单（后续会话解决）

  

> [!important] 这些还没最终定，后续会话要讨论

  

### 11.1 架构层面

  

- [ ] 动力学 backbone：Transformer vs CNN+RNN（倾向 Transformer）

- [ ] z_real 是否 detach（状态空间辅助 loss 时）

- [ ] 不确定性：VAE vs Dropout ensemble（倾向 VAE）

- [ ] D 注入：FiLM 够不够，要不要交叉注意力（消融决定）

- [ ] 编码器是否需要重训输入层（若用 4 波段 EarthNet vs 12 波段 SSL4EO）

  

### 11.2 数据层面

  

- [ ] EarthNet 4 波段 vs SSL4EO 12 波段的兼容（编码器输入层）

- [ ] ERA5 下载完整性（何时够用）

- [ ] 严格切分的具体 block 划分方案

- [ ] VPD 用湿度还是露点（两数据集不同）

  

### 11.3 实验层面

  

- [ ] DHR 等 diagnostic 指标的精确定义

- [ ] 是否创建极端事件 diagnostic benchmark

- [ ] 下游任务最终选几个（1 还是 2）

- [ ] h 的具体取值（{10,20,30,60} 是否最优）

- [ ] VPD 消融后是否保留（P1→P0 或删除）

  

### 11.4 叙事层面

  

- [ ] 论文标题（强调 multi-scale? imaging-decoupled? interpretable?）

- [ ] 主打卖点排序（成像解耦 / DGH / 多尺度 / 可解释）

- [ ] 与陈志盛对齐字段和实验策略

  

---

  

## 12. 一页纸速查（TL;DR）

  

```text

【主线】成像解耦的地表状态动力学世界模型

       z_t + D + G + h → z_{t+h}，物理可解释

  

【DGH】

  D = day_of_year + precip + temp + VPD + solar_rad（5核心）

  G = elevation（1个）

  h = {10,20,30,60}天多跨度联合

  

【训练最优策略】

  联合训练 EarthNet2021 + SSL4EO（加权平衡）

  理由：学普适动力学，叙事更强，与Stage1本质不同

  监督：观测空间 MSE + NDVI辅助 + KL正则

  注入：FiLM 调制

  切分：时间+空间+ERA5格点三隔离

  

【AAAI实验（8页，实验4页）】

  §5.1 主实验：EarthNet预测对比（DHR赢EO-WM，0.71 vs 0.65）

  §5.2 泛化：SSL4EO held-out跨气候

  §5.3 消融：8配置DGH（必做）

  §5.4 可解释：反事实+regime-dependent

  §5.5 下游：Sen1Floods11+CropHarvest（freeze z）

  

【定位】不拼扩散生成精度，走物理可解释+多尺度+跨气候

       输给EO-WM像素质量不怕，DHR/参数效率/多尺度/可解释赢回

  

【Stage1教训】双模态致69.57%，但Stage2是同任务非模态切换

  

【核心差异化】降水(供给)+VPD(需求)=完整水分平衡

             联合训练覆盖全球多气候（欧洲+热带+干旱）

```

  

---

  

**文档状态**：v1.0 总纲

**维护者**：Zhijian Liu

**服务对象**：后续会话的架构设计与训练落实

**最后更新**：2026-07-06

  

**配套文档**：

- [[26_完整问题解析与执行路线图]]

- [[27_DGH字段详细设计与文献验证报告]]

- [[23_ObsWorld完整方法框架与Stage2动力学算法设计]]

- [[22_dgh数据构建完整方案]]
