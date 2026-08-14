# 87 · TerraState 冻结主张、极端热旱状态审计、本地 Manifest 与方案 B 决策树

> 日期：2026-07-26（UTC）  
> 状态：**当前持续执行总纲；已完成第二轮结果—主张审计与 CCF-A/AAAI 多视角审查。**  
> 修改范围：本文为新增记录，不修改 84、86、代码、数据或论文正文。  
> 文档层级：84 号继续定义科学问题、方法型单模型定位和已提交标题；本文根据 2026-07-26 的真实结果，更新证据状态、极端热旱协议、方案 B 决策顺序和叙事边界。86 号中与本文冲突的旧 Stage-A/Stage-B 硬门和执行顺序，以本文为准。  
> 核心纪律：**目标主张、当前已证事实、待验证假设必须分开；最终精度和机制证据只能来自同一个冻结 checkpoint。**

---

## 0. 一页结论

### 0.1 路线是否继续

**继续。**

当前没有发现必须放弃“遥感 + 方法型世界模型 + 内部可检验状态”主线的逻辑性致命问题。但路线必须加入四项修正：

1. 极端热旱子集只检验“状态作用是否增强”，不能替代全局 Q2；
2. “极端组显著、正常组不显著”不能证明增强，必须直接检验两组效应差；
3. Phase-I B4 的强精度与 exclusive checkpoint 的转移证据不能跨 checkpoint 拼成一个成功模型；
4. 原定旧 Stage-B/Phase-II 不应直接启动；先冻结协议并评估已有权重，再决定是否进行一次有边界的 state-route takeover 训练。

### 0.2 当前完整主张是否已经成立

**没有。当前结果对完整标题级主张的 result-to-claim 判定为 `NO`，不是 headline-level `PARTIAL`。**

原因不是“所有实验都失败”，而是现有两个积极事实来自不同 checkpoint：

- Phase-I B4 有可用、具有竞争力量级的 OOD 预测精度；
- exclusive MAIN-last 的 `T_identity` 干预显示正且显著的 transition dependence；
- 但当前没有任何一个 checkpoint 同时满足“精度足够 + 全局状态真实承载预测”。

因此：

- 论文主线和目标性标题可以暂时保留；
- 摘要不能把目标结果写成已经发生；
- 后续所有训练与评估的唯一目标，是得到一个可以独立承担全部正文证据的最终 checkpoint。

### 0.3 当前最优执行顺序

```text
冻结主张与协议
  ↓
本地只用未来天气构造 hot-dry / matched-normal manifests
  ↓
上传 JSON、协议和映射脚本，不上传原始数据
  ↓
对两个已有 checkpoint 做预注册式分层审计
  ↓
判断是否已有一个 checkpoint 足以冻结
  ├─ 是：冻结并统一完成正式实验
  └─ 否：只允许一次从强 B4 热启动的 state-route takeover
          ↓
       同一 checkpoint 过 Q1 + 全局 Q2
          ↓
       极端热旱检验 effect amplification
          ↓
       Q3/Composition 仅按真实结果进入正文或附录
```

### 0.4 当前论文证据地位

| 位置 | 内容 | 作用 | 当前地位 |
|---|---|---|---|
| Table 1 | GreenEarthNet OOD-t 公共预测精度 | 证明模型可用、没有为机制牺牲到不可接受 | 核心 |
| Table 2 | 同 checkpoint 的 state / transition interventions | 证明状态或共享转移真实参与预测 | **最核心方法证据** |
| Table 3 | 预定义极端热旱与 matched-normal 的效应差 | 证明状态介导作用在需要天气动力学的压力场景中增强 | 核心压力测试 |
| Appendix / 可选图表 | Q3 完整天气 arms、composition、non-collapse、EO-WM 外部协议 | 扩展解释和完整性 | 非标题硬门 |

---

## 1. 冻结的科学问题与方法型定位

### 1.1 科学问题

> 一个天气条件化、预测准确的高分辨率 EO forecaster，是否同时形成了一个真实承载预测、可由未来天气推进、并能通过内部干预检验的预测状态？

标准像素误差只能评价最终输出，不能区分：

- 内部状态是真正承担预测的状态；
- 内部状态只是装饰性 auxiliary feature；
- 天气只进入接口但被模型忽略；
- 强底座绕过状态路径完成预测。

### 1.2 TerraState 的方法合同

\[
z_t=q(o_{\le t}),
\]

\[
z_{t+h}=T(z_t,u_{t:t+h},g,h),
\]

\[
\hat{o}_{t+h}=O(z_{t+h})
\quad\text{或}\quad
\hat{o}_{t+h}=b_h+O(z_{t+h}),
\]

其中：

- \(q\) 从受云遮挡的历史观测推断空间预测状态；
- \(T\) 是未来天气、地理背景和经过时间条件化的共享转移；
- \(O\) 从转移后的状态闭合为未来观测或 NDVI；
- 若使用 context-only prior \(b_h\)，它不得看到未来天气，也不得把状态路径饿死；
- 论文最终只出现一个 TerraState，不出现 Phase-I、exclusive、MAIN/SAFE 等研发名称。

### 1.3 与 EO-WM 的正确关系

EO-WM 已明确把 EO forecasting 表述为部分可观测、天气驱动的世界建模，并重点研究：

- 概率视频生成；
- 气候态、天气异常和累积物理压力；
- Extreme Summer 输出行为；
- Seasonal Matched-Pair 天气响应保真度。

TerraState 不能声称：

- 首个天气驱动 EO 世界模型；
- 首个使用极端天气评测的 EO 模型；
- 其他 EO 方法“不是真正世界模型”。

TerraState 的差异应稳定写为：

> EO-WM 重点验证预测输出是否对天气变化和极端压力作出合理响应；TerraState 进一步暴露并干预模型内部的空间预测状态，检验天气响应是否由一个真实参与预测的状态—转移路径介导。

### 1.4 极端热旱的正确地位

极端热旱不是新主线，也不是为了避开不利精度而制造的新榜单。它是一个预先定义的压力场景，用于检验：

> 当未来天气 forcing 更强、更偏离常态时，TerraState 的状态或共享转移对端点预测的作用是否相对正常天气显著增强。

因此标题中心继续是 `testable predictive-state world model`，而不是 `extreme forecasting` 或 `new benchmark`。

---

## 2. 当前真实证据与严格解释

### 2.1 Phase-I B4：精度强，但状态合同未成立

已知结果：

| Split | R² | RMSE | NSE | \|bias\| | RMSE25 |
|---|---:|---:|---:|---:|---:|
| val_chopped | 约 0.51197 | 约 0.15089 | — | — | — |
| ood-t_chopped | 0.58252 | 0.14342 | -0.00177 | 0.09390 | 0.07879 |

可支持：

- 当前项目已有一个可用、预测量级足以进入 Table 1 讨论的权重；
- TerraState 路线不是从一个完全失效的预测器开始。

不可支持：

- Phase-I B4 的状态真实承载预测；
- 天气条件带来正确的性能增益；
- composition 成立。

既有状态诊断：

- Q2：`NOT_LOAD_BEARING`；
- Q3：输出有可检测变化，但性能差异没有形成有力的 matched-weather 正确性证据；
- Q4：real/shuffled composition ratio 约为 1，只能说明非坍缩，不支持组合主张。

### 2.2 Exclusive MAIN-last：转移有作用，但精度与 closure 不足

已知结果：

| 项目 | 结果 |
|---|---:|
| Full R² | 0.49027 |
| Full RMSE | 0.16038 |
| alpha0 R² | 0.48611 |
| T-identity R² | 0.48158 |
| Full - alpha0 ΔR² | +0.00416 |
| Full - T-identity ΔR² | +0.00869 |
| closure paired mean | +0.00775 |
| closure 95% CI | [-0.00226, +0.01768] |
| transition paired mean | +0.01413 |
| transition 95% CI | [+0.00413, +0.02411] |

严格解释：

- `T_identity` 干预显著，说明共享转移对端点存在可检测影响；
- closure cut 方向为正，但 CI 跨 0，不能宣称完整 load-bearing；
- `T_identity` 会把 OOD state 送入 \(O\)，因此它是 transition-dependence 辅证，不能取代 closure；
- R² 0.49027 明显低于 Phase-I 精度锚点，当前不能作为最终论文模型。

允许的事实句：

> The exclusive route exhibits detectable transition dependence, while its global state-closure evidence remains inconclusive and its forecast accuracy is insufficient for the final model.

### 2.3 禁止跨 checkpoint 拼接

严禁出现以下逻辑：

```text
Phase-I B4 精度强
  +
exclusive 的 T_identity 显著
  =
TerraState 同时精度强且状态承载预测
```

这是无效拼接。最终正文中的：

- Table 1；
- state / transition intervention；
- extreme / matched-normal；
- 所有摘要结果句；

必须来自同一个最终 checkpoint。

---

## 3. 目标主张、条件主张与保底主张

### 3.1 理想目标主张

中文：

> TerraState 在保持具有竞争力的 OOD 预测能力的同时，形成真实承载预测的内部状态：干预状态或共享转移会损害端点预测，而且这种状态介导作用在独立定义的极端热旱 forcing 下显著增强。

英文：

> TerraState maintains competitive OOD forecasting skill while exposing a forecast-bearing predictive state: perturbing the state or its shared transition degrades endpoint forecasts, and this state-mediated effect strengthens under independently defined extreme hot-dry forcing.

只有同一个 checkpoint 同时满足 Q1、全局 Q2 和 hot-dry interaction 后，才能使用事实语气。

### 3.2 条件性结果主张

若全局 closure 不充分，但预定义热旱组相对 matched-normal 存在显著 interaction：

> TerraState preserves useful OOD forecasting skill and exhibits a conditionally forecast-bearing state under extreme hot-dry forcing, where state and transition interventions have a measurably larger endpoint effect than under matched normal conditions.

此时必须：

- 明确是 `under extreme hot-dry forcing`；
- 同时报告全样本 Q2；
- 不把条件效应写成一般性的 load-bearing state；
- 重新检查标题和摘要是否需要收窄。

### 3.3 最低诚实主张

若最终 checkpoint 仍只能保持精度，而内部状态证据为 partial：

> TerraState provides an explicit predictive-state interface and a matched intervention audit, revealing a measurable transition dependence but also the difficulty of making internal state use coexist with strong EO forecast accuracy.

这可以形成无占位、逻辑完整的正文，但不再支持强方法成功句，标题与摘要需要相应降级。

---

## 4. 极端热旱协议：不能用子集替代全局 Q2

### 4.1 核心研究问题

极端热旱实验不是问：

> 能否在某个更有利的子集上把失败的全局 Q2 变成 PASS？

而是问：

> 在预先定义、只由未来天气 forcing 决定的极端热旱样本中，状态或共享转移的端点效应是否显著大于可比的正常天气样本？

### 4.2 必须直接检验 interaction

令某个冻结干预的端点效应为：

\[
E_i = \mathrm{loss}_{i,\mathrm{intervention}}
      - \mathrm{loss}_{i,\mathrm{full}}.
\]

分别计算：

\[
\bar E_{\mathrm{hotdry}},
\qquad
\bar E_{\mathrm{normal}},
\]

核心检验是：

\[
\Delta_{\mathrm{interaction}}
=
\bar E_{\mathrm{hotdry}}
-
\bar E_{\mathrm{normal}}.
\]

必须对 \(\Delta_{\mathrm{interaction}}\) 做 paired / cluster bootstrap，并报告：

- 均值；
- 95% CI；
- 样本数；
- cube、地点、季节或配对层级；
- 效应方向；
- extreme 与 normal 的覆盖关系。

只有当 interaction 的 CI 下界大于 0，才能写“作用增强”。

以下说法无效：

```text
极端组 p < 0.05
正常组 p > 0.05
所以两组显著不同
```

### 4.3 样本定义纪律

hot-dry 样本：

- 只用 future-weather forcing；
- 优先由 train / calibration split 的季节气候态与阈值定义；
- 禁止使用未来 NDVI、预测误差、checkpoint 输出或任何模型排名选样本；
- strict 与 broad 阈值、样本数回退规则必须在看分层模型结果前冻结；
- manifest 必须记录协议版本、阈值、生成脚本 commit、数据源指纹和 SHA。

matched-normal 至少匹配：

- 季节 / DOY；
- 地理位置或生态区；
- 预测时域；
- 云量 / 有效像素比例；
- 可用的 pre-forcing context；
- 植被有效覆盖；
- 样本复用次数。

否则 extreme 与 normal 的差异可能只是样本难度、观测质量或初始状态不同。

### 4.4 干预地位

建议主次顺序：

1. closure / state contribution cut：主要 state-to-output 证据；
2. state shuffle 或 matched donor state：主要破坏状态内容的证据；
3. `T_identity`：共享转移的辅证，明确 OOD-state 混淆；
4. mean / climatology / shuffled / donor weather：weather-conditioned dependence；
5. state rank、std、movement：排除常数或低秩坍缩；
6. composition：扩展项，不得补偿失败的 Q2。

### 4.5 允许与禁止的语言

允许：

- `weather-conditioned state dependence`；
- `state-mediated response`；
- `effect amplification under hot-dry forcing`；
- `stress-regime diagnostic`。

禁止：

- `causal counterfactual correctness`；
- `general drought forecasting system`；
- `proof of physical dynamics`；
- 只因输出变化就写 `weather-response fidelity`；
- 用 extreme 子集隐藏或替代全样本结果。

---

## 5. 本地 Manifest 优先的数据工程协议

### 5.1 已核验本地资产

根目录：

```text
/mnt/data/users/luzheng/workspace/iclr/czj/TrainData/EarthNet2021/earthnet2021x
```

| Split | 文件数 | 总大小 | 本地状态 |
|---|---:|---:|---|
| `ood-t_chopped` | 1,904 | 6,295,915,546 bytes（约 6.30 GB） | manifest 中全部文件存在且大小匹配 |
| `extreme` | 3,972 | 25,529,793,394 bytes（约 25.53 GB） | manifest 中全部文件存在且大小匹配 |

重要：

- `.smoke_reports/extreme_sync.json` 是旧的 `PARTIAL` 报告，记录了旧路径和未完成状态；
- 以 2026-07-26 的实际逐文件核对为准：当前 `extreme` 已经完整；
- 后续若保留该旧报告，必须防止脚本误读它为当前事实。

### 5.2 不上传原始数据

训练服务器已经下载了相同数据，因此：

- 不上传整个 `extreme`；
- 不上传整个 `ood-t_chopped`；
- 不上传筛选后的 NC 副本；
- 不在 Git 仓库重新分发 EarthNet 原始数据。

本地只生成并上传：

```text
protocol/
├── hotdry_manifest.json
├── matched_normal_manifest.json
├── thresholds.json
├── calibration_statistics.json
├── protocol.json
├── provenance.json
└── MANIFEST.SHA256

tools/
├── validate_hotdry_manifest.py
└── materialize_manifest_view.py
```

### 5.3 Manifest 必须使用相对路径

示例：

```json
{
  "dataset": "earthnet2021x",
  "source_split": "ood-t_chopped",
  "protocol": "terrastate_hotdry_v1",
  "files": [
    "MAM22/minicube_184_33VUG_59.63_12.31.nc"
  ]
}
```

禁止写入：

```text
/mnt/data/users/.../ood-t_chopped/...
/csy-mix02/.../ood-t_chopped/...
```

训练端通过：

```text
dataset_root + relative_path
```

解析文件。

### 5.4 训练端两种使用模式

首选：evaluator 直接读取 manifest，不创建新目录。

```text
manifest
  → 验证相对路径
  → dataset_root / relative_path
  → 只加载指定 cube
```

兼容旧 evaluator：创建软链接视图。

```text
hotdry_view/MAM22/minicube_xxx.nc
  -> 训练端已有的原始 NC
```

只建立软链接，不复制数据。

### 5.5 训练端必须验证

- manifest schema 和 protocol version；
- 不存在 `..`、绝对路径或越界路径；
- 所有文件存在；
- 文件大小与源数据 manifest 匹配；
- 入选文件的 SHA 或至少冻结的数据指纹匹配；
- hot-dry / normal 不重叠；
- 配对关系与复用次数合法；
- 阈值、样本数和分组标签不在训练端重新计算；
- 输出记录训练端 dataset root、manifest SHA、checkpoint SHA 和代码 commit。

### 5.6 EarthNet2021X extreme 与 EO-WM exact protocol

本地 `earthnet2021x/extreme` 是 NetCDF 格式。EO-WM exact comparison 使用原始 EarthNet2021 NPZ 与官方 benchmark CSV。

因此：

- 本地 NC 可以用于开发适配器和私有评估；
- 未验证 CSV 窗口与 NC cube 的一一映射前，不能称 exact EO-WM reproduction；
- exact protocol 若后续执行，也采用“本地冻结 CSV/manifest、训练端读取已有数据”的原则；
- EO-WM external protocol 是补充证据，不能抢占当前 Q1 + 内部状态证据的优先级。

---

## 6. 方案 B 的唯一正确决策树

### 6.1 当前禁止直接启动旧 Stage-B

86 号原定 Stage-B 的进入条件是 Stage-A 至少达到 Q1 qualifier，并形成可辩护 Q2。当前：

- exclusive 精度没有达到原 Q1 qualifier；
- closure 仍不显著；
- 只有 `T_identity` transition dependence 为正。

因此旧 Stage-B 的 composition / VICReg / partial-unfreeze 配方没有可靠底座，直接启动属于偏离诊断结果。

### 6.2 P0：先完成新协议与已有权重审计

对两个现有 checkpoint 使用同一冻结 hot-dry / matched-normal manifest：

1. Phase-I B4：
   - 判断强精度模型是否在预定义压力场景中暴露更强的 state / transition dependence；
   - 不能因全局 Q2 已失败而只报告极端结果。

2. Exclusive MAIN-last：
   - 判断已出现的 transition dependence 是否在 hot-dry 中增强；
   - 判断 closure 是否仍然不稳定；
   - 结果只用于诊断训练方向，不用于与 B4 跨 checkpoint 拼接。

本轮已有权重审计的主要价值是：

- 验证 selector、matched control、interaction 和 evaluator；
- 判断 state signal 究竟存在于何种天气区间；
- 为唯一一次新训练确定明确靶点。

不应预设它一定能直接找到最终 winner。

### 6.3 分支 A：Phase-I B4 已经满足同 checkpoint 证据

必要条件：

- Q1 保持当前强档；
- 全局 closure / state intervention 至少达到可辩护效应；
- hot-dry interaction 若写入核心结果则 CI 支持增强；
- 所有结果来自同一个 B4 checkpoint。

动作：

- 直接冻结 B4；
- 不进行新训练；
- 用该 checkpoint 统一重跑 Table 1–3；
- composition 只在额外结果真实强时进入正文。

### 6.4 分支 B：B4 保精度，exclusive 有机制，但没有单一成功 checkpoint

这是当前最可能出现的分支。

动作：

- 启动一次**精度保持型 state-route takeover**；
- 从强 Phase-I B4 / Contextformer 权重热启动，不从头训练；
- frozen teacher 只在训练期提供强预测目标；
- 状态路径逐步接管未来天气相关的预测贡献；
- 最终推理不得依赖训练期 teacher；
- context-only prior 不能看到未来天气；
- takeover 过程中同时监控 Q1 与全局 closure，不只优化 hot-dry。

建议只允许：

- 一个主配方；
- 一个预先声明的安全回退；
- 一个固定训练预算；
- 一次结果后停止，不继续扩展筛选空间。

### 6.5 分支 C：两个已有 checkpoint 均没有可复用的状态信号

若：

- 全局 Q2 仍失败；
- hot-dry interaction 也不成立；
- state shuffle / closure / transition 均没有稳定方向；

则：

- 不再启动旧 composition Stage-B；
- 不再增加更多子集寻找显著性；
- 判断最后一次 takeover 是否仍有足够时间和机制依据；
- 若没有，立刻转为诚实的 transition-dependence / diagnostic 论文闭环，并修改摘要强度。

### 6.6 一次 takeover 的停止条件

成功门：

- 同一个 checkpoint 保持可接受 Q1；
- 全局 closure / state intervention 有正、稳定、可解释的效应；
- `T_identity` 作为辅证方向一致；
- hot-dry 若作为核心结果，interaction CI 支持增强；
- normal / global 精度没有因只优化极端样本而崩盘。

停止门：

- 精度持续低于保底且没有恢复趋势；
- closure 仍近零或方向不稳定；
- 只有 T-identity 有效而 state cut 无效；
- 只能通过修改 extreme 阈值或更换子集找到显著结果；
- 同一 claim 连续两轮仍为 partial / no；
- 需要第二轮大规模结构搜索才能继续。

---

## 7. 多视角 AAAI 审查

### 7.1 Field expert

积极点：

- EO world modeling、天气驱动预测和极端气候响应具有明确现实意义；
- “精度是否对应可复用内部状态”是超越局部刷分的 AI 问题；
- 问题与 GreenEarthNet、EarthNet2021 的实际输入输出一致。

主要风险：

- 若只展示遥感数据上的自定义干预指标，容易被认为影响面窄；
- 必须把问题写成一般的 predictive-state / world-model verification 问题，再以 EO 为重要落点。

最有价值的升级：

- 强调“准确 forecaster 可以绕过声称的状态”这一普遍方法风险；
- 用 matched-backbone、同 checkpoint 干预说明这不是遥感特有小技巧。

### 7.2 Method expert

积极点：

- \(q\rightarrow T\rightarrow O\) 简洁；
- shared transition、closure cut 和 state intervention 能把架构命名变成可证伪机制；
- state-route takeover 有明确的技术目标。

主要风险：

- context-only prior 过强会饿死 residual；
- 为强迫 load-bearing 而破坏精度；
- `T_identity` 受到 OOD state 混淆；
- 训练 loss 多但缺少一个清晰的主机制。

最有价值的升级：

- 把“预测贡献逐步由 state route 接管”写成唯一训练机制；
- closure 作为主证据，T-identity 作为辅证；
- composition 不再与主方法竞争叙事空间。

### 7.3 Experiment expert

积极点：

- 现有精度权重、已有 evaluator、本地完整数据和 8×H200 资源使实验可执行；
- paired interventions 和 cluster bootstrap 能形成比纯可视化更有力的证据；
- 失败结果仍能解释精度—机制张力。

主要风险：

- hot-dry 是在看到全局 Q2 失败后提出，存在明显 post-hoc 风险；
- 两个 checkpoint 的积极结果不能拼接；
- matched-normal 若不匹配云量、上下文和地理，interaction 会混杂；
- OOD-t 反复选模会污染最终测试。

最有价值的升级：

- 在看分层模型结果前冻结阈值、manifest、interaction 和所有 primary metrics；
- checkpoint 只用验证协议选择；
- OOD-t 作为一次性冻结验证；
- 直接报告连续效应与 CI，不依赖自定 PASS 标签。

### 7.4 AC / venue expert

积极点：

- 文章属于方法型、经验型和分析型贡献的结合，符合 AAAI 对 substantive AI contribution 的包容范围；
- “testable predictive-state world model”标题有明确问题意识；
- 不要求 Table 1 SOTA，只要求预测能力足以让机制结论有意义。

主要风险：

- 标题级主张当前没有被一个 checkpoint 支撑；
- 如果正文以 extreme benchmark 为中心，会像追随 EO-WM；
- 如果 internal audit 多于实际方法，容易被判为 benchmark / analysis paper；
- 结果表存在大量 TBD 会直接损害完整性。

最有价值的升级：

- Table 2 提升为内部 state / transition 核心证据；
- extreme 放在 Table 3 做压力测试；
- 方法部分围绕 state-route takeover，而不是 evaluator 细节；
- 正文并行完成，实验只决定结果句强度，不决定论文是否可编译。

### 7.5 Skeptical prior-art expert

积极点：

- TerraState 不声称天气条件化、latent dynamics 或 EO world model 本身新；
- 与 EO-WM、VegSim、Observability Forecasting 的区别可以被清楚表述。

主要风险：

- predictive-state、latent intervention、composition consistency 均有通用先例；
- 若没有 EO 场景中特有的 weather-driven state mediation 与实际结果，方法可能被看作已知模块组合；
- 最新 EO world-model 文献很密集，novelty 仍需持续核对。

最有价值的升级：

- 新颖性锚定在“让高分辨率 weather-conditioned forecaster 的内部状态承担预测，并用同 checkpoint 的 matched interventions 检验”；
- 不把任何单个模块包装成首次；
- Related Work 明确区分 output response、latent simulation 与 forecast-bearing internal state。

### 7.6 Reproducibility / data expert

积极点：

- 本地数据完整；
- manifest-only 跨服务器协议减少数据漂移；
- 相对路径、SHA 和只读映射能完整追踪样本。

主要风险：

- 旧 smoke report 与当前真实数据状态冲突；
- 本地/训练端绝对路径不同；
- EarthNet2021X NC 与 EO-WM NPZ exact protocol 可能被误写为相同；
- 公共仓库重新分发原始数据可能引入许可与体积问题。

最有价值的升级：

- 只上传协议、manifest 和脚本；
- 训练端读取已有数据或创建软链接视图；
- 明确 external protocol 是否 exact；
- 将数据 manifest SHA 与 checkpoint SHA 一起写入结果。

---

## 8. CCF-A/AAAI idea-stage 评分

> 此评分评价问题与方法的开发价值，不是接收概率，也不代表当前实验已经成功。

| 维度 | 权重 | 评分（1–5） | 解释 |
|---|---:|---:|---|
| 问题重要性 | 12 | 4.3 | 精度与内部状态真实性的差距具有一般 world-model 意义 |
| 相对现有工作的创新性 | 14 | 3.7 | internal forecast-bearing audit 有差异，但最新近邻密集 |
| 概念创新 | 12 | 4.0 | 将世界状态从架构标签改为可证伪主张较清晰 |
| 方法可靠性 | 14 | 3.3 | 机制明确，但精度—承载冲突尚未解决 |
| 优雅与简洁 | 8 | 3.6 | \(q,T,O\) 简洁，旧 Q1–Q4 体系曾过重 |
| 资源与时间可行性 | 8 | 3.5 | 代码数据基本齐全，但截止时间紧 |
| 实验说服力潜力 | 10 | 3.3 | paired intervention 强，但当前同 checkpoint 缺口明显 |
| AAAI 受众匹配 | 8 | 3.8 | 方法/经验/分析结合合理，需避免遥感小众化 |
| 时效性 | 6 | 4.5 | EO world model 与天气驱动预测高度活跃 |
| 风险调整后的潜力 | 8 | 3.2 | 最大风险是最终单 checkpoint 无法闭环 |

加权得分约为：

\[
3.70/5.
\]

推荐：**`revise / continue`**。

解释：

- 思想值得继续；
- 当前不应 pivot 到纯 benchmark 或纯精度刷榜；
- 必须解决“同 checkpoint 精度 + state closure”这一唯一高优先级阻塞；
- 若一次 takeover 仍失败，应降级主张而不是无限搜索。

置信度：

- 对当前完整主张尚未成立：高；
- 对修正后路线逻辑自洽：高；
- 对最终强主张必然成功：中低；
- 对能够完成一篇无占位、诚实、逻辑完整正文：高，前提是立即并行写作和结果回填。

---

## 9. 致命风险、可修复问题与应对

| 问题 | 严重度 | 是否可修 | 必须动作 |
|---|---|---|---|
| 极端子集替代失败的全局 Q2 | 致命 | 可避免 | 全局 Q2 仍报告；extreme 只做 interaction |
| 跨 checkpoint 拼接精度与机制 | 致命 | 可避免 | 最终只保留一个 checkpoint |
| 根据模型结果修改 extreme 阈值 | 致命 | 可避免 | 看分层结果前冻结 protocol 与 SHA |
| state closure 与强精度无法共存 | 高 | 部分可修 | 只允许一次 B4 热启动 takeover |
| 只比较组内显著性，不比较组间差异 | 高 | 可修 | 直接 bootstrap interaction |
| matched-normal 混杂 | 高 | 可修 | 匹配季节、地理、云量、context、时域 |
| 把 T-identity 当完整 load-bearing | 高 | 可修 | closure 主证据，T-identity 辅证 |
| extreme 叙事与 EO-WM 过近 | 中高 | 可修 | internal state mediation 为核心差异 |
| composition 绑架主线 | 中 | 已修正 | 降为扩展 |
| Table 1 不 SOTA | 中 | 可辩护 | 保持 competitive / sufficient，不写 SOTA |
| 自定义尺子被质疑 | 中高 | 可修 | claim-aligned、预注册、连续效应、公开协议 |
| 正文等待实验才写 | 高 | 可修 | 写作和实验双线并行 |

---

## 10. 正文同步要求

当前 `TerraState_AAAI27/paper/main.tex` 已有完整结构，但仍基于旧 Q1–Q4 中 composition 较高的地位，并保留大量 TBD。

后续正文修改应遵循：

1. 标题暂时保留：

   > TerraState: A Testable Predictive-State World Model for Weather-Driven Land-Surface Forecasting

2. 摘要当前仍使用 registration-safe 问题式版本，不提前添加结果成功句；
3. Introduction 的三条贡献顺序改为：
   - 精度不能确认内部预测状态；
   - TerraState 让 state route 承担预测并可被干预；
   - 公共预测、内部 state intervention 和 hot-dry interaction 三层证据；
4. Table 2 提升为 state / transition intervention；
5. hot-dry 与 matched-normal 放 Table 3；
6. composition 移到扩展结果或附录，除非最终非常强；
7. 方法图重点画：

```text
历史观测 → q → state
                ↓
未来天气 → shared T → future state → O → endpoint forecast
```

并标出：

- training-only frozen teacher；
- state/closure cut；
- T-identity；
- hot-dry vs matched-normal forcing；
- 最终只有一个 inference model。

8. 任何最终摘要结果句都必须根据本文 §3 的主张档位选择；
9. 不得在正文中出现研发名 Phase-I、B4、exclusive、MAIN/SAFE；
10. 即使强主张失败，也必须完成真实结果、限制与结论，不保留 TBD。

---

## 11. 当前执行优先级

### P0：今天立即推进

- [ ] 冻结 hot-dry / matched-normal 协议；
- [ ] 本地生成相对路径 manifests、thresholds、provenance 与 SHA；
- [ ] 实现 manifest validator 和训练端相对路径映射；
- [ ] 本地小样本 smoke；
- [ ] 训练端只读取已有数据，不重新筛选；
- [ ] 继续完善正文方法、实验设置、流程图和表格框架；
- [ ] 不启动旧 Stage-B。

### P1：协议通过后

- [ ] 对 Phase-I B4 做全局 + hot-dry + matched-normal 审计；
- [ ] 对 exclusive MAIN-last 做同协议诊断；
- [ ] 计算 closure、state shuffle、T-identity 的 interaction；
- [ ] 报告所有冻结 primary metrics，不删除不利项；
- [ ] 按 §6 决策树选择冻结或 takeover。

### P2：若必须 takeover

- [ ] 锁定一个主配方和一个安全回退；
- [ ] 从强 B4 热启动；
- [ ] 训练期 teacher 离线，推理期删除；
- [ ] 同时监控 Q1 与全局 closure；
- [ ] 不仅优化 extreme；
- [ ] 固定预算后停止；
- [ ] 在验证协议冻结唯一 checkpoint。

### P3：最终统一评估

- [ ] 同一个 checkpoint 完成 Table 1；
- [ ] 同一个 checkpoint 完成 Table 2；
- [ ] 同一个 checkpoint 完成 Table 3；
- [ ] OOD-t 只做冻结验证，不继续挑 winner；
- [ ] 回填中英文摘要、正文、图表和限制；
- [ ] 论文 PDF 无 TBD、无口径冲突、可复现。

---

## 12. 每次监督 B 时必须先问的七个问题

1. 当前工作是否直接服务“同 checkpoint 的精度 + state closure”？
2. 是否又把 composition、EO-WM benchmark 或附属 evaluator 放在了主线之前？
3. extreme 阈值和 manifest 是否已经在看模型分层结果前冻结？
4. 是否直接检验了 hot-dry 与 matched-normal 的 interaction？
5. 是否正在把两个 checkpoint 的优点拼接成一个结论？
6. 当前结果允许的语言到底是 load-bearing、transition-dependent、weather-sensitive，还是仅 non-collapse？
7. 正文是否同步推进，是否还存在可提前完成的 TBD、图表和公式？

若任何一项回答不清楚，应暂停扩展实验并回到本文。

---

## 13. 最终北极星

> TerraState 不是因为公共精度不够而寻找一把更有利的尺子，也不是通过定义谁“算世界模型”来制造贡献。它提出一个让预测状态承担输出的单模型方法，并用同 checkpoint 的公共精度、内部状态干预和预定义极端热旱 interaction，检验准确的天气驱动 EO forecaster 何时真正形成可被推进和检验的预测状态。

当前持续执行口令：

> **先冻结协议并评估已有权重；再决定是否进行一次精度保持型 state-route takeover；最终只用一个 checkpoint 完成精度、状态和极端热旱三层证据。**

