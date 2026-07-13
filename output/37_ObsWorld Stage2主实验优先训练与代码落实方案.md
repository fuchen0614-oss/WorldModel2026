# 37 ObsWorld Stage2 主实验优先训练与代码落实方案

> 文件定位：本文专门用于落实 Stage2。它不再做版本摇摆，而是给出当前时间紧张条件下最应直接执行的高效率主线方案。  
> 核心原则：**先满足 EarthNet2021 标准预测主实验，再用同一套代码开关完成 D/G/h 消融、weather-response 和可视化。**

---

## 0. 先给结论

Stage2 的首要目标不是先做 D/G/h 消融，而是先把主实验跑通：

```text
EarthNet2021 标准预测
    -> 能输出完整未来序列
    -> 能计算 EarthNet / NDVI / long-horizon 指标
    -> 能与 baseline 和现有方法放入第一张主表
```

D/G/h 消融是之后的机制验证实验，但代码层面必须从一开始就支持：

```text
full model: z + D + G + h
no-D:       z + G + h
no-G:       z + D + h
no-h:       z + D + G
z-only:     z
```

也就是说，执行顺序是：

```text
先训练 full ObsWorld-S 主模型
再复用同一套 loader / trainer / evaluator 训练消融模型
再做 weather-response / uncertainty / G consistency
```

不要把机制实验放到主实验之前；但也不要等主实验做完才临时补消融代码。最佳效率是：**主实验路径优先，消融开关同步内置。**

---

## 1. Stage2 的最终任务定义

Stage2 要解决的是 EarthNet2021 标准预测任务，但叙事上不是普通像素预测。

标准任务表达：

```text
给定历史遥感观测、未来气象驱动和静态地理信息，
预测未来若干 lead time 的遥感观测。
```

ObsWorld 表达：

```text
先从历史观测估计当前陆表状态，
再学习该状态在 D/G/h 条件下如何演化，
最后把未来状态解码为可评估的未来观测。
```

核心公式：

```text
z_context = A_context({E_obs(x_{t_i}, phi_{t_i})}_{i=1..T_context})

z_hat_{t+h_j} = F_theta(z_context, D_{t:t+h_j}, G, h_j)

x_hat_{t+h_j} = O_earthnet(z_hat_{t+h_j}, phi_{t+h_j})
```

其中：

- `E_obs`：Stage1.5 得到的观测编码器。
- `A_context`：上下文状态聚合器，把多个历史观测状态融合成当前状态。
- `F_theta`：Stage2 状态动力学模块，是 Stage2 真正训练的核心。
- `D`：外生驱动。
- `G`：地理背景。
- `h`：预测跨度。
- `O_earthnet`：面向 EarthNet 输出波段的观测解码头。

注意：如果为了省事只用最后一帧 `z_t`，主实验精度可能吃亏。EarthNet 标准任务天然给了历史上下文，所以最高效率不是忽略历史，而是加一个轻量 `A_context`。

---

## 2. 主实验优先级

### 2.1 第一优先级是什么

第一优先级：

```text
完整输出 EarthNet 标准 target sequence
```

也就是不只预测一个 h，而是按 EarthNet 官方时间轴输出未来目标帧。通常可理解为：

```text
h = 5, 10, 15, ..., 100 days
```

实际实现时以数据 loader 解析出的 target dates / lead indices 为准。

### 2.2 训练时是否必须每次算所有 h

不必须。

为了节省显存和训练时间，建议采用：

```text
训练时：每个 batch 随机采样若干个 horizon，但覆盖短/中/长跨度
评估时：输出完整所有 horizon
```

推荐训练采样：

```text
每个样本采 4-6 个 h：
短期：5/10/15
中期：20/30/45/60
长期：75/90/100
```

这不是降低主实验要求，而是高效率的 multi-horizon training。最终评估仍然必须完整输出全部目标帧。

### 2.3 D/G/h 消融的位置

D/G/h 消融不在主实验之前做。

正确顺序：

```text
1. full model 跑通主实验
2. 固定同一训练协议，跑 no-D / no-G / no-h / z-only
3. 对比标准指标、NDVI 指标、long-horizon 指标、response 指标
```

写作中对应：

- Table 1：主实验，EarthNet 标准预测。
- Table 2：D/G/h 消融，解释为什么 full model 的设计有效。

---

## 3. 数据样本应如何构建

Stage2 loader 推荐输出：

```python
batch = {
    "x_context": ...,       # [B,Tc,C,H,W] 历史观测
    "phi_context": ...,     # [B,Tc,P] 或 dict，历史成像条件
    "context_mask": ...,    # [B,Tc,H,W] 历史有效像素/云 mask

    "x_target": ...,        # [B,Tf,C,H,W] 未来真值
    "phi_target": ...,      # [B,Tf,P]，若不可完整获得则用 neutral / date-derived phi
    "target_mask": ...,     # [B,Tf,H,W] EarthNet 评估有效 mask

    "D": ...,               # [B,Td,D_dim] 或 [B,Tf,D_feat] 外生驱动
    "G": ...,               # [B,1,H,W] 或 token-aligned elevation
    "h": ...,               # [B,Tf] lead time，单位 day 或归一化 day

    "meta": ...             # tile id, dates, split, region
}
```

### 3.1 x_context

不要只默认使用最后一帧。

推荐：

```text
把 context period 内可用观测都送入 E_obs，
得到一组 state tokens，
再由 A_context 聚合为 z_context。
```

好处：

- 历史状态更稳。
- 云、缺失、异常观测的影响更小。
- 能利用过去趋势。
- 更符合 EarthNet 标准输入协议。

### 3.2 x_target

`x_target` 是主实验直接监督来源。

Stage2 不应只用 latent loss，因为最终第一张主表看的是预测观测。必须有：

```text
future observation loss
NDVI / vegetation dynamics loss
EarthNet evaluation metrics
```

### 3.3 D

最终 D 字段：

```text
D = day_of_year, precipitation, temperature, VPD, solar_radiation
```

高效率实现方式：

```text
对每个 target horizon h_j，构造 t:t+h_j 的驱动特征。
```

推荐特征：

| 字段 | 特征 |
| --- | --- |
| day_of_year | sin/cos |
| precipitation | cumulative sum, mean |
| temperature | mean, min/max 可选 |
| VPD | mean, max |
| solar_radiation | cumulative sum, mean |

为了效率，建议提前预计算 cumulative statistics：

```text
cumsum_precip
cumsum_srad
cummean_temp
cummean_vpd
max_vpd over interval
```

这样任意 `t:t+h` 的 D 特征都可以快速切片得到。

### 3.4 G

首选：

```text
G = elevation
```

如果 `z` 是 patch tokens，`G` 不要只做全局平均，建议 patch pooling 到同样 token 网格：

```text
elevation map [H,W]
    -> patch pooling
    -> geo tokens [N, geo_dim]
```

这样每个空间 token 都能拿到对应地形背景。

### 3.5 h

`h` 必须进入模型。

推荐编码：

```text
h_norm = h / 100
h_embed = MLP([h_norm, log1p(h_norm)])
```

如果使用全部 EarthNet target lead times，则 h 是：

```text
5, 10, 15, ..., 100
```

如果训练时做 horizon sampling，仍然从这套完整集合里采样，不另造一套最终 h。

### 3.6 工程硬约束清单

下面这些不是可选优化，而是 Stage2 代码落地时必须遵守的约束。

| 约束 | 必须怎么做 | 为什么 |
| --- | --- | --- |
| 主实验优先 | full model 先满足 EarthNet 标准预测输出和指标 | 没有主实验，机制实验站不住 |
| Dynamics 不读 phi | `F_theta` 只接收 `z_context,D,G,h` | 避免把观测条件混入状态转移 |
| Decoder 可读 target phi | `O_earthnet` 可接收 `phi_target` 或 neutral phi | phi 是生成观测外观的条件，不是动力学驱动 |
| D/G/h 必须可消融 | 从 config 控制 no-D/no-G/no-h/z-only | Table 2 需要同代码路径、公平比较 |
| 通道必须显式声明 | 建 `BandSpec`，记录 band name、index、scale、nodata、red/nir index | 避免 12 通道预训练与 EarthNet 波段不一致导致静默错误 |
| NDVI 必须在物理反射率空间算 | 对输出和 GT 先反归一化，再计算 NDVI | 归一化空间里的 NDVI 没有物理意义 |
| normalization 只用 train split | D/G/band 的 mean/std 只从训练集估计 | 避免验证/测试统计泄漏 |
| mask 贯穿全流程 | context mask、target mask、driver missing mask、geo mask 分开保存 | 云、无效值、缺失驱动的处理不能混在一起 |
| h 用真实日期差 | 由 target date - reference date 计算，不只靠帧号 | 避免缺帧、非均匀时间间隔导致 h 错误 |
| 未来天气协议写清楚 | 主实验是 scenario/oracle forcing；部署预测另用 forecast/climatology | 避免被误解为数据泄漏 |
| target 图像只能做监督 | target image 不得进入 context encoder 或 D/G/h 构造 | 避免真实未来信息泄漏 |
| 缓存 state 要带版本号 | 缓存必须记录 checkpoint、band adapter、phi 策略、normalization | 避免换 adapter 后继续用旧 latent |

### 3.7 12 通道预训练与 EarthNet 波段不对称

这是 Stage2 最容易踩坑的地方。

当前 Stage1.5 的 S2 encoder 是按 SSL4EO 的 12 通道 Sentinel-2 输入训练的；EarthNet 标准预测通常围绕少数目标波段，常见为 RGB/NIR 相关通道。两者不是天然同构。

因此代码中必须先建立：

```text
BandSpec
```

至少包含：

```python
band_spec = {
    "dataset": "earthnet2021",
    "input_bands": [...],
    "target_bands": [...],
    "canonical_s2_bands": [...],   # Stage1.5 期望的 12 通道顺序
    "red_index": ...,
    "nir_index": ...,
    "scale_factor": ...,
    "nodata_value": ...,
    "normalization": {
        "mean": ...,
        "std": ...,
        "fit_split": "train"
    }
}
```

禁止：

```text
把 EarthNet tensor 直接送进 12-channel encoder。
```

不推荐作为主训练：

```text
简单把缺失通道填 0，然后假装是完整 12 通道。
```

推荐做法：

```text
EarthNetInputAdapter:
    EarthNet bands
        -> canonical S2 band space
        -> learnable missing-band tokens / 1x1 projection
        -> Stage1.5 encoder-compatible tensor
```

更具体地说：

1. 如果 EarthNet 某个波段能对应 Stage1.5 的 canonical S2 波段，就 scatter 到对应通道。
2. 如果 canonical S2 的某些波段在 EarthNet 中没有，就使用 learnable missing-band parameter 或 small projection 生成占位特征。
3. 再用一个轻量 `1x1 conv / linear projection` 做波段适配。
4. 适配器参数参与 Stage2 训练，但主干 encoder 先冻结或低学习率。
5. 所有 band mapping 必须写进 config 和输出日志。

输出端也要分开：

```text
Stage1.5 decoder: 服务 SSL4EO 12 通道重建
EarthNet decoder: 服务 EarthNet target bands
```

Stage2 主实验不应强行复用 Stage1.5 的 12 通道 decoder。应新建 `EarthNetObservationDecoder`，输出 EarthNet 需要评估的目标波段。

### 3.8 phi 缺失或不一致时的处理

Stage1.5 的 `E_obs(x, phi)` 依赖 phi，但 EarthNet 不一定提供与 SSL4EO 完全一致的 phi 字段。因此 Stage2 需要明确 phi 策略。

优先顺序：

1. 若 EarthNet 可构造与 Stage1.5 一致的纯成像 phi，则正常使用。
2. 若只能构造部分 phi，则使用 partial phi + missing mask。
3. 若无法可靠构造，则使用 learned neutral phi，并降低 latent target loss 权重。

关键约束：

```text
phi_context / phi_target 只能进入 E_obs 或 O_earthnet，
不能进入 F_theta。
```

如果 `phi_target` 不可靠：

- `z_target = E_obs(x_target, phi_target)` 只能作为弱监督。
- 主监督应更依赖 `L_obs` 和 `L_ndvi`。
- 文档和代码中要记录 `latent_target_confidence`。

---

## 4. 模型结构落地

### 4.1 总结构

```text
x_context, phi_context
    -> E_obs
    -> state sequence Z_context
    -> A_context
    -> z_context

z_context, D, G, h
    -> F_theta
    -> z_pred_future

z_pred_future, phi_target
    -> O_earthnet
    -> x_pred_future
```

### 4.2 E_obs

来自 Stage1.5。

建议训练策略：

```text
同一次训练内使用 progressive unfreeze：
前若干 step 冻结 E_obs，只训练 adapter / A_context / F_theta / decoder；
随后只解冻 state_projector 和 ViT 最后若干 block；
主干学习率远小于新模块学习率。
```

这不是分版本升级，而是一个训练 run 内的稳定训练日程。它能减少灾难性遗忘，又允许模型适配 EarthNet。

### 4.3 EarthNet band adapter

这是代码落地的高风险点。

当前 Stage1.5 的 S2 输入是 12 通道，而 EarthNet 常用目标是少数关键波段。不能直接假设输入通道一致。

推荐建立：

```text
EarthNetBandAdapter
```

职责：

- 把 EarthNet 输入波段映射到 Stage1.5 encoder 可接受格式。
- 如果只用 RGB/NIR，可用 learnable 1x1 projection 或 band-specific patch embedding。
- 保留明确 band mapping，避免训练和评估时通道顺序错乱。

建议不要直接复制填零 12 通道作为唯一方案。填零可用于 sanity check，但主训练最好用 learnable adapter。

建议接口：

```python
class EarthNetInputAdapter(nn.Module):
    def forward(self, x, band_spec, band_mask=None):
        """
        x: [B,T,C_earthnet,H,W]
        return: [B,T,C_stage1_5,H,W]
        """
```

实现规则：

- 输入和输出都保持 `[B,T,C,H,W]`，不要在 adapter 内偷偷改变时间维。
- `band_mask` 用来标记真实存在波段和 learnable missing 波段。
- adapter 输出的数值分布要接近 Stage1.5 encoder 训练时的归一化分布。
- adapter 的配置、band order、mean/std 必须随 checkpoint 一起保存。
- sanity check 阶段要打印每个 band 的 min/max/mean/std，确认没有通道顺序错乱。

### 4.4 A_context

推荐轻量实现：

```text
ContextStateAggregator
```

输入：

```text
Z_context: [B,Tc,N,256]
context_valid_mask: [B,Tc]
```

输出：

```text
z_context: [B,N,256]
```

可选结构：

1. masked temporal attention，推荐。
2. GRU over time，简单稳定。
3. last-valid state + small residual temporal adapter，最低成本。

最推荐：

```text
masked temporal attention + residual last-valid connection
```

形式：

```text
z_context = z_last_valid + TemporalAdapter(Z_context, mask)
```

这样起点接近 persistence，但能利用历史趋势。

### 4.5 F_theta

当前已有 `StateDynamicsModule`，但需要扩展成适合 multi-horizon：

当前：

```text
z_t [B,N,256] + D [B,D] + G [B,G] + h [B]
    -> z_pred [B,N,256]
```

建议目标：

```text
z_context [B,N,256]
D_h       [B,H,D_feat]
G_tokens  [B,N,G_dim]
h         [B,H]
    -> z_pred [B,H,N,256]
```

高效率实现方式：

```text
把 H 维展开到 batch 维：

[B,H,N,256] -> [B*H,N,256]
[B,H,D]     -> [B*H,D]
[B,H]       -> [B*H]
```

这样可以最大程度复用当前 `StateDynamicsModule`。

#### 4.5.1 D/G/h 的实际接入方式

推荐使用三个独立编码器：

```text
DriverEncoder(D_{t:t+h}) -> d_emb
GeoTokenizer(G)          -> g_tokens
HorizonEncoder(h)        -> h_emb
```

张量形态：

```text
z_context: [B,N,256]
D_feat:    [B,Hf,D_feat]
G_tokens:  [B,N,G_dim]
h:         [B,Hf]

d_emb:     [B,Hf,C_cond]
h_emb:     [B,Hf,C_cond]
g_emb:     [B,N,C_cond]
```

融合方式：

```text
cond[B,Hf,N,C] =
    d_emb[:, :, None, :]
  + h_emb[:, :, None, :]
  + g_emb[:, None, :, :]
```

然后把 horizon 维展开：

```text
z_context_expand: [B,Hf,N,256] -> [B*Hf,N,256]
cond:             [B,Hf,N,C]   -> [B*Hf,N,C]
```

再送入 dynamics block：

```text
z_pred = F_theta(z_context_expand, cond)
```

如果沿用当前 `StateDynamicsModule` 的 concat 接口，也可以先把 `cond` 拼到 token：

```text
[z_context ; cond] -> input_proj -> dynamics core -> delta_z
```

要求：

- `D` 必须按 horizon 构造，不能只给一个全局天气均值。
- `G` 推荐 token-aligned，不能只用一个全局 elevation 均值替代所有空间位置。
- `h` 必须参与每个 horizon 的预测，不能只用于 loss 分组。
- `no-D/no-G/no-h` 消融必须通过 config 控制同一个 forward path。

#### 4.5.2 D/G/h 消融开关

建议 config：

```yaml
conditions:
  use_D: true
  use_G: true
  use_h: true
  null_condition: learned   # learned | zero
```

实现规则：

- 训练 full model 时 `use_D/use_G/use_h=true`。
- 训练 no-D/no-G/no-h 消融时从头训练对应 config，不建议只在 eval 时遮挡。
- 为了公平，消融模型应保持尽量接近的参数规模；缺失条件使用 learnable null embedding 或同维 zero embedding。
- weather-response 只对 full model 做，不要拿 no-D 模型做 response。

#### 4.5.3 D 特征构造硬规则

对每个 target horizon `h_j`，D 特征必须来自：

```text
[reference_time, target_time]
```

不能使用：

```text
target_time 之后的天气
target image 反推出来的 NDVI/状态
验证/测试集统计归一化
```

推荐 D 特征：

| 字段 | horizon-level 特征 |
| --- | --- |
| day_of_year | target doy sin/cos, optionally start doy sin/cos |
| precipitation | interval sum, interval mean |
| temperature | interval mean, optionally min/max |
| VPD | interval mean, interval max |
| solar_radiation | interval sum, interval mean |

所有特征都要带 missing mask：

```text
D_feat: [B,Hf,D_feat]
D_mask: [B,Hf,D_feat] or [B,Hf]
```

缺失处理：

- 少量缺失：插值 + mask。
- 大量缺失：样本跳过或使用 learned missing embedding。
- 不能把缺失值直接填 0 而不提供 mask。

#### 4.5.4 G 特征构造硬规则

`G=elevation` 的处理要对齐两个空间尺度：

```text
image grid:  [H,W]
state grid:  [N]，通常 N = patch_h * patch_w
```

推荐：

```text
elevation [B,1,H,W]
    -> normalize with train stats
    -> patch pooling / interpolation
    -> g_tokens [B,N,G_dim]
```

重采样规则：

- elevation 是连续值，可用 bilinear。
- mask 是离散有效性，只能用 nearest。
- 任何 resize 都要保证和影像同一坐标系。

#### 4.5.5 h 特征构造硬规则

`h` 应由日期差得到：

```text
h_days = (target_date - reference_date).days
```

编码：

```text
h_norm = h_days / max_h_days
h_log = log1p(h_days) / log1p(max_h_days)
h_emb = HorizonEncoder([h_norm, h_log])
```

注意：

- 训练时可以 horizon sampling。
- 评估时必须输出完整 target horizon。
- `h` 不能只作为 loss 权重，它必须进入模型。

### 4.6 O_earthnet

不要强依赖 Stage1.5 的 12 通道重建 decoder。

建议新建 EarthNet 专用输出头：

```text
EarthNetObservationDecoder
```

输出：

```text
RGB/NIR or EarthNet target bands
optional NDVI head
optional uncertainty head
```

这样更直接服务主实验，也绕开 Stage1.5 decoder 与 EarthNet 波段不一致的问题。

---

## 5. Loss 设计

主实验优先时，loss 不能只在 latent 空间。

推荐主 loss：

```text
L_total =
    lambda_obs   * L_obs
  + lambda_ndvi  * L_ndvi
  + lambda_latent * L_latent
  + lambda_delta * L_delta
  + lambda_smooth * L_smooth
```

### 5.1 L_obs

未来观测重建损失：

```text
masked L1 / Huber over valid target pixels
```

必须使用 `target_mask`，否则云、无效像素会污染训练。

### 5.2 L_ndvi

NDVI 动态损失：

```text
NDVI = (NIR - Red) / (NIR + Red + eps)
```

用途：

- 支撑 vegetation dynamics。
- 对 weather-response 更敏感。
- 让模型不只是做 RGB 外观相似。

### 5.3 L_latent

latent target：

```text
z_target = stopgrad(E_obs(x_target, phi_target))
```

然后：

```text
cosine / MSE(z_pred, z_target)
```

注意：

- `z_target` 应 stopgrad。
- 不要一开始让 target encoder 随训练漂移。
- 如果 `phi_target` 缺失，用 neutral phi 或 EarthNet 可构造的日期/传感器条件，但不要让 Stage2 dynamics 直接读取 phi。

### 5.4 L_delta

方向一致性：

```text
delta_pred = z_pred - z_context
delta_true = z_target - z_context
L_delta = 1 - cosine(delta_pred, delta_true)
```

用途：

- 防止模型退化成 persistence。
- 强化状态变化方向。

### 5.5 L_smooth

时间平滑正则：

```text
z_pred[h_{j+1}] - z_pred[h_j]
```

权重要小。它是稳定器，不是主要监督。

---

## 6. 主实验训练配置建议

推荐建立主配置：

```text
configs/train/stage2_earthnet_main.yaml
```

核心字段：

```yaml
model:
  encoder:
    from_checkpoint: checkpoints/stage1_5_dual_conditioned_vits_60k/...
    freeze_schedule:
      warmup_new_modules_steps: 2000
      unfreeze_state_projector: true
      unfreeze_last_blocks: 2

  band_adapter:
    type: learnable_projection
    in_channels: earthnet_channels
    out_channels: stage1_5_s2_channels

  context_aggregator:
    type: masked_temporal_attention
    residual_last_valid: true

  dynamics:
    type: StateDynamicsModule
    latent_dim: 256
    driver_dim: computed_D_feat_dim
    geo_dim: computed_G_feat_dim
    horizon_conditioned: true

  decoder:
    type: EarthNetObservationDecoder
    out_channels: earthnet_target_channels
    predict_ndvi: true
    predict_uncertainty: false

data:
  dataset: earthnet2021
  target_horizons: official
  train_horizon_sampling:
    enabled: true
    horizons_per_sample: 6
    stratified_short_mid_long: true

loss:
  obs: 1.0
  ndvi: 0.5
  latent: 0.2
  delta: 0.1
  smooth: 0.02
```

具体权重可调，但原则是：

```text
主实验以 observation / NDVI 为主，
latent / delta 用于稳定状态动力学。
```

---

## 7. 代码目录建议

建议新增或改造以下文件。

### 7.1 数据

```text
WorldModel2026/data/datasets/earthnet2021.py
WorldModel2026/data/datamodules/earthnet_dm.py
WorldModel2026/data/earthnet_fields.py
WorldModel2026/data/earthnet_transforms.py
```

职责：

- 读取 context / target。
- 对齐 D/G/h。
- 生成 valid masks。
- 输出标准 batch dict。
- 明确 split，不允许训练集统计泄漏到验证/测试。

### 7.2 适配器

```text
WorldModel2026/models/adapters/earthnet_band_adapter.py
WorldModel2026/models/adapters/geo_tokenizer.py
```

职责：

- 处理 EarthNet 波段与 Stage1.5 encoder 通道不一致。
- 把 elevation 对齐到 state token。

### 7.3 上下文状态聚合

```text
WorldModel2026/models/dynamics/context_state_aggregator.py
```

职责：

- 多历史帧状态融合。
- 支持 mask。
- 输出 `z_context`。

### 7.4 动力学

已有：

```text
WorldModel2026/models/dynamics/state_dynamics_module.py
```

建议扩展：

- 支持 horizon batch 展开。
- 支持 token-aligned geo。
- 支持 D/G/h ablation mask。
- 输出可选 uncertainty。

### 7.5 解码器

```text
WorldModel2026/models/decoders/earthnet_observation_decoder.py
```

职责：

- 从 `z_pred` 输出 EarthNet target bands。
- 可选输出 NDVI。
- 可选输出 logvar。

### 7.6 Loss

```text
WorldModel2026/models/losses/earthnet_forecasting.py
```

职责：

- masked observation loss。
- NDVI loss。
- latent dynamics loss。
- direction loss。
- horizon weighting。

### 7.7 训练与评估

```text
WorldModel2026/train/train_stage2_earthnet.py
WorldModel2026/eval/eval_earthnet.py
WorldModel2026/eval/eval_stage2_ablation.py
WorldModel2026/eval/eval_weather_response.py
WorldModel2026/scripts/generate_stage2_ablation_configs.py
```

---

## 8. 实验执行顺序

不要再写版本递进式路线，直接按任务优先级执行。

### Step 1：主实验 pipeline 打通

目标：

```text
一条命令训练 full ObsWorld-S
一条命令输出 EarthNet 标准预测结果
一条命令计算 Table 1 指标
```

验收：

- loader 能输出完整 batch。
- 模型能输出完整 target sequence。
- loss 正常下降。
- eval 能保存 prediction arrays。
- 指标脚本能跑通。

### Step 2：主模型训练

训练：

```text
full ObsWorld-S: z_context + D + G + h
```

优先看：

- validation observation loss。
- NDVI-MAE。
- long-horizon error。
- persistence / climatology 是否被超过。

如果 full 模型连 persistence / climatology 都打不过，先不要跑一堆消融，优先修主训练。

### Step 3：消融训练

复用同一 trainer，只改 config：

```text
no-D
no-G
no-h
z-only
no-Stage1.5 / Stage1-only
last-frame-only context ablation
```

注意：

- 消融训练预算可以低于 full，但不能低到不公平。
- 至少保证相同数据、相同 horizon、相同 evaluator。

### Step 4：weather-response

固定：

```text
z_context, G, h
```

改变：

```text
precipitation / VPD / temperature / solar_radiation
```

输出：

```text
NDVI curve
response direction
response magnitude
prediction maps
```

这是 Table 3 或核心 figure 的来源。

### Step 5：可视化

必须和主实验一起准备，不要最后补。

建议输出：

```text
context frames
GT future
ObsWorld prediction
baseline prediction
error map
NDVI curve
response sweep
```

---

## 9. 主实验表格如何安排

Table 1 应以标准预测为中心：

| Method | Params | Pretrain | ENS↑ | MAE/MAD↓ | SSIM↑ | NDVI-MAE↓ | Long-horizon↓ | Cost |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Persistence | - | no |  |  |  |  |  |  |
| Climatology | - | no |  |  |  |  |  |  |
| ConvLSTM / SGConvLSTM |  | no/task |  |  |  |  |  |  |
| SimVP / PredRNN |  | task |  |  |  |  |  |  |
| Earthformer |  | task |  |  |  |  |  |  |
| Contextformer |  | task |  |  |  |  |  |  |
| EO-WM | large | yes |  |  |  |  |  |  |
| ObsWorld-S | small | SSL4EO |  |  |  |  |  |  |

注意：

- Table 1 不负责证明所有机制。
- Table 1 只证明你在标准预测任务上站得住。
- 如果 ObsWorld-S 的 ENS 不是第一，但 NDVI / long-horizon / cost 有优势，也可以解释。
- 但如果输给 persistence / climatology，必须先修模型。

---

## 10. Table 2 消融如何服务主实验

Table 2 不要写成“另一个实验”，而要写成：

```text
为什么 Table 1 里的 ObsWorld-S 设计是合理的？
```

表格：

| Config | Context | D | G | h | Stage1.5 | ENS↑ | NDVI-MAE↓ | Long-horizon↓ | Response↑ |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| full | yes | yes | yes | yes | yes |  |  |  |  |
| no-D | yes | no | yes | yes | yes |  |  |  |  |
| no-G | yes | yes | no | yes | yes |  |  |  |  |
| no-h | yes | yes | yes | no | yes |  |  |  |  |
| z-only | yes | no | no | no | yes |  |  |  |  |
| last-frame-only | no | yes | yes | yes | yes |  |  |  |  |
| no-Stage1.5 | yes | yes | yes | yes | no |  |  |  |  |

这个表的意义：

- `no-D`：检验未来天气驱动是否真的有用。
- `no-G`：检验 elevation 是否提供地理背景。
- `no-h`：检验多跨度条件是否必要。
- `z-only`：检验是不是只是状态 persistence。
- `last-frame-only`：检验历史上下文是否必要。
- `no-Stage1.5`：检验成像条件处理后的状态是否更适合动力学。

---

## 11. 代码落地注意事项

### 11.1 不要让 Stage2 读 phi

Stage2 dynamics 只允许读取：

```text
z_context, D, G, h
```

不能读取：

```text
phi_target embedding
```

`phi_target` 只能给 decoder 使用。

### 11.2 不要把 D 和 phi 混在一起

不要把 `sun_elevation` 放入 D。

不要把 `season` 和 `day_of_year` 混乱重复使用。

建议：

```text
D: day_of_year, precipitation, temperature, VPD, solar_radiation
phi: acquisition / observation condition
G: elevation
```

### 11.3 normalization 只用训练集统计

所有 D/G/band normalization：

```text
fit on train
apply to val/test
```

不要在全数据上算均值方差。

### 11.4 cloud / valid mask 要贯穿训练和评估

必须明确：

- 哪些像素参与 loss。
- 哪些像素参与 EarthNet 指标。
- NDVI loss 是否排除云、雪、无效值。

### 11.5 horizon 维度要统一

所有输出都建议统一成：

```text
[B, H, C, H_img, W_img]
```

或者为了避免变量名冲突：

```text
[B, T_future, C, height, width]
```

不要有的地方用 `[B,C,T,H,W]`，有的地方用 `[B,T,C,H,W]`。

### 11.6 先对齐 baseline

主训练开始前必须能跑：

```text
persistence
climatology
last observation
```

这不是附属工作，而是主实验安全线。

### 11.7 每次实验保存统一输出

建议保存：

```text
predictions.npz
metrics.json
config.yaml
visual_samples/
response_curves/
```

否则写表和画图会很痛苦。

### 11.8 训练前必须通过的 sanity checks

开始正式训练前，必须先跑这些检查：

```text
1. batch shape check:
   x_context [B,Tc,C,H,W]
   x_target  [B,Tf,C,H,W]
   D         [B,Tf,D_feat]
   G         [B,1,H,W] or [B,N,G_dim]
   h         [B,Tf]

2. band check:
   打印 band names、red/nir index、每通道 min/max/mean/std

3. adapter check:
   EarthNetInputAdapter 输出通道数等于 Stage1.5 encoder 期望通道数

4. mask check:
   target_mask 有效比例合理，不能全 0 或全 1

5. temporal check:
   h_days 与 target dates 一致

6. driver check:
   D_{t:t+h} 不包含 target 之后天气

7. leakage check:
   target image 不出现在 context 或条件变量中

8. overfit check:
   用极小 batch 过拟合 10-50 个样本，确认 loss 可下降

9. baseline check:
   persistence / climatology 指标可复现

10. output check:
    保存 prediction 后能被 eval_earthnet.py 独立读取和评分
```

这些检查没有通过时，不应启动长训。

---

## 12. 最终执行口径

不要说：

```text
我们先做一个简化模型，后面再补完整。
```

应该说：

```text
我们直接实现主实验所需的标准预测闭环，
并在同一套代码中保留机制消融开关。
```

不要说：

```text
D/G/h 消融是主实验。
```

应该说：

```text
EarthNet 标准预测是主实验；D/G/h 消融解释主实验中 ObsWorld 设计为何成立。
```

不要说：

```text
Stage2 只训练 latent dynamics 就够了。
```

应该说：

```text
Stage2 以状态动力学为核心，但主实验必须通过未来观测和 NDVI 指标验证。
```

最终路线：

```text
1. 建 EarthNet loader
2. 建 band adapter
3. 建 context state aggregator
4. 扩展 StateDynamicsModule 支持 D/G/h + multi-horizon
5. 建 EarthNet decoder
6. 建 masked obs + NDVI + latent/delta loss
7. 建 train_stage2_earthnet.py
8. 建 eval_earthnet.py
9. 训练 full ObsWorld-S
10. 跑 Table 1
11. 跑 Table 2 消融
12. 跑 weather-response 和可视化
```

---

## 13. 一句话定稿

Stage2 的最高效率方案是：

> **直接围绕 EarthNet2021 标准预测建立完整 end-to-end 训练与评估闭环；模型内部采用 Stage1.5 状态编码、历史状态聚合、D/G/h 条件状态动力学和 EarthNet 解码头；主模型优先训练，D/G/h 消融作为同一代码路径下的配置复用实验。**
