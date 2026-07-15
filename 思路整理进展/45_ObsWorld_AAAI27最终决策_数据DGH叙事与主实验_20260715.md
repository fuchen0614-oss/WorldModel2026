# ObsWorld AAAI-27 最终决策：数据、DGH、中心叙事与主实验

> 日期：2026-07-15  
> 状态：**AAAI-27 截稿冲刺的当前规范性决策**  
> 范围：整理思路与实验，本轮**不修改训练代码、不中断正在运行的 Stage1.5**  
> 继承关系：保留 43 的代码/协议审计和 44 的 EarthNet+DGH+世界模型主线；本文更正 44 中“默认需要换/重下数据”和“L1C/L2A product Gate 必须进主文”的过强暗示。

---

## 0. 现在就可以拍板的七个结论

1. **数据集不是非换不可，现在默认不重新下载。**现有主配置已写 `dataset: earthnet2021x` 和 `data_format: netcdf`，只是根目录叫 `EarthNet2021`。历史文档记录已下载约 119GB，这与 GreenEarthNet/EarthNet2021x 的 `train+iid+ood` 规模高度一致。先审计，只增量补缺失或损坏文件。
2. **论文仍然是 EarthNet2021 主线。**准确写法是 `EarthNet2021 benchmark family` + `GreenEarthNet protocol over the EarthNet2021x release`，而不是改做一个无关数据集。
3. **DGH 保留，不改名，不推倒。**需要改的是 DGH 如何进入动力学：`D` 从终点累计摘要变为逐区间驱动路径，`G` 保持空间 DEM 背景，`H` 从 endpoint 编号升级为共享转移的 `Δt`。
4. **不否定 Stage1/1.5 已有 `phi` 工作。**已有字段构建、条件自重建、S1/S2 近时对齐、nuisance loss 和泄漏 probe；现在需要的是修复验收逻辑并检验它是否提升 Stage2，不是默认重练。
5. **L1C/L2A 不是 AAAI-27 必做项。**它是更干净的 product-conditioned observation 增强证据，但会引入新下载和新训练。当前主文使用现有 S1/S2 + Stage1/1.5 证据；L1C/L2A 放截稿后。
6. **AAAI-27 的主方法是“观测状态学习 × 受控时间组合”，不再强行写“跨产品解码”。**核心 2×2 直接比较 `Stage1 vs Stage1.5 state` 与 `no-partition vs partition-consistent dynamics`，最大限度利用已有投入。
7. **世界模型/模拟真实世界仍是母叙事。**可验证含义是：从有偏观测中维护预测状态，按区间 DGH 驱动连续推演，对时间划分保持一致，并回到真实卫星观测空间核验；不声称完整地球模拟器或唯一真实物理状态。

最终独立逆向审查为 **Conditional GO（有条件继续），8.7/10**：方案无需推翻；提交级 GO（可进入投稿主结果）取决于 all-8 E-OBS Gate（八字段天气数据门槛）、D_hist/D_fut（历史/未来天气路径）索引测试、one-seed（单随机种子）2×2 和实测训练墙钟。

### 0.1 英文术语速查

后文第一次看到这些词时，可以直接按括号中的中文理解；英文文件名、变量名不翻译。

| 英文 | 中文含义 | 大致读法 |
|---|---|---|
| phi / φ | 成像或获取条件，例如太阳角、轨道、卫星/产品身份及其缺失标记 | “费/斐” |
| fallback | 后备方案：首选方案做不成时使用的次选方案 | “福尔拜克” |
| schema | 字段结构：一个文件应有哪些变量、各是什么形状 | “斯基马” |
| manifest | 文件清单：明确哪些文件属于训练、验证或测试 | “曼尼费斯特” |
| audit | 审计/检查：检查目录、文件数、字段和损坏情况 | “奥迪特” |
| probe | 探针测试：冻结主模型后，用小模型检查状态里还含有什么信息 | “普柔布” |
| baseline | 基线方法：用来判断我们是否真正进步的参照方法 | “贝斯莱恩” |
| Direct | 直接式预测：从同一个初始状态分别预测各个未来时刻 | “德瑞克特” |
| rollout | 滚动预测：前一步预测状态继续作为后一步的输入 | “柔尔奥特” |
| partition | 时间分割：把十天拆成十天一步，或五天加五天 | “帕提申” |
| endpoint | 目标时刻：例如第十天这个真实监督点 | “恩德坡因特” |
| mask | 有效性标记：哪些像素/字段可用，哪些应忽略 | “马斯克” |
| evaluator | 评估器：按官方规则计算指标的程序 | “伊瓦流诶特” |
| smoke test | 冒烟测试：先用极少数据/步数验证代码能跑通 | “斯莫克测试” |
| one-seed | 单随机种子试验：先跑一遍判断方向是否值得继续 | “万·西德” |
| Gate | 门槛/闸门：达到条件才进入下一批昂贵实验 | “盖特” |
| Train-only | 只使用训练集计算，避免偷看验证/测试数据 | “吹瑞恩·欧恩利” |
| held-out | 留出数据：完全不参与训练的数据 | “赫尔德奥特” |
| prescribed/oracle forcing | 数据集直接提供的真实未来外生驱动；不是天气预报值 | “预先给定/理想驱动” |
| OOD | 分布外测试：时间、地点或二者不同于训练数据 | 逐字母读 O-O-D |
| bootstrap | 自助采样法：反复重采样估计置信区间 | “布特斯特拉普” |
| interaction | 交互效应：两个改动一起使用是否产生额外效果 | “因特拉克申” |
| compatible | 两个模块可以共同工作，但不保证互相增强 | “康帕特布尔” |
| synergistic | 协同增强：两者一起的收益超过各自收益简单相加 | “西呢吉斯提克” |
| curriculum | 渐进式训练安排：先简单短期，再逐步增加难度 | “科瑞丘勒姆” |

---

## 1. 九问九答

### Q1：为什么要更换数据集？现有 EarthNet2021 不好吗？非换不可吗？

**答：不是非换不可；更准确地说，很可能你已经下载了我们想用的版本。**

有三层事实：

1. 配置 [`configs/train/stage2_earthnet_main.yaml`](../configs/train/stage2_earthnet_main.yaml) 明确是 `dataset: earthnet2021x`、`data_format: netcdf`。
2. 代码 [`data/datasets/earthnet2021.py`](../data/datasets/earthnet2021.py) 在该路径下要求 `s2_B02/B03/B04/B8A`、E-OBS 和 DEM 的 NetCDF 字段，这是 GreenEarthNet/EarthNet2021x 格式。
3. 27 号文档记录“EarthNet2021 已下载 119GB”。官方对象存储中 `train+iid+ood` 约 108.75GB，考虑目录、缓存、差异和统计方式，119GB 与此高度相符。

所以当前决策不是“下载一个新数据集”，而是：

```text
先在训练机审计现有 EarthNet2021 目录
             │
             ├─ 是 train/iid/ood/*.nc，字段完整
             │      → 直接使用，零重下
             │
             ├─ 是 EarthNet2021x，但有少量缺失/损坏
             │      → sync 脚本只增量补文件
             │
             └─ 真的只有 legacy NPZ
                    → 7月16日前再决定是转旧协议还是后台增量下 train/iid/ood
```

你刚提供的物理目录结构是正确的：

    EarthNet2021/
      earthnet2021x/
        .manifests/
        train/
        iid/
        ood/
        extreme/
        seasonal/

现有路径解析器既可以接收外层 `.../EarthNet2021`，也可以直接接收内层 `.../EarthNet2021/earthnet2021x`；前者会自动进入内层目录。`.manifests` 多半是下载/同步文件清单缓存，不应自动等同于论文的训练/验证/测试划分清单，正式实验仍要核对官方 split（划分）定义。

还要区分“目录存在”和“全量下载完成”：五个 raw package（原始数据包）全部完整时约 218.9GB；历史记录约 119GB 更像是 AAAI 当前需要的 train+iid+ood 已基本齐全，而 extreme/seasonal 可能只是已有目录、部分文件或未完成。这个状态并不影响当前主线，因为前者才是优先检查对象。

不需要另写一套新脚本：项目已有 `scripts/audit_earthnet2021x.py`。但在正式运行前要给它补上四个字段 `fg/pp/tn/tx` 的检查，否则它只能证明四字段版本可读，不能证明 24-D 主协议可用。当前节点没有挂载 `/csy-mix02`，所以这里能确认路径逻辑，不能替训练机实际扫描文件。

当前不再补下载 `extreme/seasonal`：它们不是 AAAI-27 主表的必要条件；目录存在不代表文件完整，但其中已有文件保留即可，不需要删除。

但 119GB、目录名和 NetCDF 数量不是最终证明：当前 audit/loader 只强制 hu、qq、rr、tg 四个 E-OBS 字段，而 24-D 主协议需要 fg、hu、pp、qq、rr、tg、tn、tx 全八项。M0 必须补做 all-8 schema 审计。若只是少量文件缺字段则增量替换；若全库是四字段版本且重下赶不及，则明确采用 12-D 截稿 fallback，绝不能把实际 12-D 写成 24-D。

### Q2：“跨观测约束 + 时间分割一致性”到底是什么？

最简单地说，它要防止状态在两个方向上“作弊”。

**观测轴：不要把传感器/成像差异误当成地表变化。**

同一地点的 S1 和 S2 看到的像素完全不同，但它们都与同一地表场景有关。Stage1.5 用近时 S1/S2 对齐、`phi` 条件建模和 nuisance 约束，尝试让预测状态少一点“只记传感器外观”，多一点“记对未来有用的地表信息”。

**时间轴：不要把“怎样切时间步”误当成不同的世界。**

对同一段 10 天天气路径，模型可以：

```text
方式 A：从 day 0 直接推到 day 10
方式 B：先 day 0→5，再 day 5→10
```

两者读到的天气必须是同一条路径的正确分段，最后状态和观测应该接近，而且两条分支都必须匹配真实 day-10 卫星观测。这就是 **control-aware partition consistency（控制感知的时间分割一致性）**。

两条轴放在一起的意义是：

> 状态不应因为“怎样观测”就完全换一套语义；状态演化也不应因为“时间怎样分段”就给出矛盾未来。

44 曾把第一条严格写成 L1C/L2A “跨产品解码”。对 AAAI-27 冲刺，它收缩为现有 Stage1/1.5 的**观测状态轴**；新的 L1C/L2A 数据不再是必要条件。

### Q3：DGH 到底改了什么？

最简单的记法是：**D = Driver（外生驱动/天气），G = Geography（地理背景/地形），H = Horizon（这一步向未来走多久）**。另外把 **C = Calendar（日历/季节）** 单独列出，避免把季节和具体天气混为一谈。

| 组件 | 当前 Direct 原型 | 最终 ObsWorld | 直觉 |
|---|---|---|---|
| `D` | 从 context 末尾累计到每个 endpoint 的 9 维 sum/mean 摘要 | 每 5 日一个区间 E-OBS token；all-8 时为 24-D，四字段 fallback 为 12-D | 这 5 天实际发生了什么 |
| `G` | 一张 DEM，方向正确 | 保留空间 DEM token，使用固定数据源和 Train-only 标准化 | 这些驱动发生在什么地理背景 |
| `H` | 从 `s0` 独立查询 day 5/10/…/100 | 同一 `T` 的 `Δt=5/10/20 days`；主 rollout 是 20 次 5 日转移 | 每次要推进多久 |
| `C` | DOY sin/cos 混在 9 维 `D` 中 | 与天气分开的日历/季节 token | 什么季节，不等于天气是什么 |

变化的核心不是换掉 DGH，而是从：

```text
s0 + cumulative_D_to_h + G + h  → 各个终点独立预测
```

变成：

```text
s_k + D[k:k+1] + C[k:k+1] + G + Δt  → s_(k+1)
```

因而 DGH 第一次成为“模拟地表演化”的转移接口，而不只是三个条件字段。

### Q4：Stage1 不是已经验证了 `phi`（成像/获取条件）吗？为什么还要更严格的证据？

**答：已经做了很多，但“已做的证据”和“论文想写的强结论”不完全是一件事。**

先回答你最关心的误解：**probe（探针测试）不是“先把 phi 单独训练一遍，再接到 Stage1.5”。你之前问到的 AI 所说“把 phi 直接加入 Stage1.5 训练”是正确的，而且当前代码就是这样做的。**

实际顺序是：

    Stage1 checkpoint（作为初始化）
            ↓
    Stage1.5 直接读入图像和 phi
            ↓
    phi_encoder、FiLM、state projector 等与 Stage1.5 目标一起训练
            ↓
    Stage1.5 训练完成后冻结主模型
            ↓
    另外训练一个很小的 probe，尝试只从 state 预测太阳角/轨道/卫星

probe 只是一把“体检仪器”：

- 如果小 probe 很容易从 state 猜出轨道或卫星，说明 state 里还保留较多成像条件信息；
- 如果很难猜出，同时未来预测没有下降，说明角色分工更好；
- probe 不参与 Stage1.5 主训练，也不会修改已训练好的 state；
- 因为太阳、季节和地理本身有关联，probe 不一定必须降到随机水平，所以要同时看 Stage1 对比和 Stage2 未来预测。

代码上，`phi_s1/phi_s2` 会先进入 `phi_encoder`，再作为 `phi_embed` 直接送进 S1/S2 encoder 和 decoder；`phi_encoder` 从 Stage1.5 初期就参与优化，后续再逐步解冻更多主干层。因此不是额外插入一个“Stage1.25”。

| 已有工作 | 是否已有 | 能证明什么 | 还不能证明什么 |
|---|---|---|---|
| `phi` parquet/cache/join/缺失值 | 是 | 字段能可靠进入网络 | 状态真正按地表/观测角色分工 |
| `phi` 条件的 S1/S2 self-reconstruction | 是 | 模型能利用条件重建本模态 | 固定 state 只改条件能得到正确目标观测 |
| 近时 S1/S2 VICReg alignment | 是 | 多模态表示开始对齐 | 它必然提升 EarthNet 未来预测 |
| cross-covariance nuisance loss | 是 | 抑制一部分线性相关 | 完全非线性解耦 |
| 旧 phi leakage MLP probe | 是 | 提供了方向性诊断 | 目前不适合直接作论文数字 |

旧 probe 代码的具体问题：

- Stage1 对照的 `state_projector` 是新随机初始化，不是文字所说的“恒等映射”；
- probe 训练和评估没有建立明确的地理隔离 split；
- 提取 Stage1.5 state 时没有传入训练时使用的 `phi_embed`；
- 历史结果本身也显示非线性泄漏未消除：orbit/satellite 约 67%–71%。

因此不需要给我额外样例才能得出当前结论。后续落地时，一个 EarthNet `.nc` 的 `ncdump/xarray` 字段清单和一个 SSL4EO batch 的 key/shape 样例会有助于做 preflight，但不是现在的阻塞。

最节省的处理是：

1. 让当前 Stage1.5 正常跑完；
2. 修复 probe，只重跑验收，不重练 Stage1.5；
3. 做 `Stage1 vs Stage1.5` 在完全相同 Stage2 下的 transfer 对比；
4. 如果 Stage1.5 不改善未来/OOD 预测，把强“成像解耦”降级为辅助诊断，不造假。

### Q5：目标就是 AAAI-27，应该怎么处理？

AAAI-27 官方日程是：

- 2026-07-21 23:59 UTC-12：摘要截止；
- 2026-07-28 23:59 UTC-12：全文截止；
- 2026-07-31 23:59 UTC-12：补充材料与代码截止；
- 7 页正文，最多 9 页，第 8–9 页只能是参考文献。

因此本轮不再纳入：新下全量 L1C、一个新下游数据集、大模型+ours 大表、`U` 新观测校正、原 EarthNet Extreme/Seasonal 全量下载。

正文只留：

1. official GreenEarthNet/EarthNet2021x OOD-t 主表；
2. Stage1/Stage1.5 × partition 2×2；
3. Direct/shared rollout/variable-step 动力学归因；
4. D/G intervention；
5. horizon error + partition gap 一张图。

当前配置的 50k steps 不能直接乘以四格、三种子和全部消融。完成 500–1000-step smoke 后必须实测 sec/step，再按“单种子 2×2 → 四格三种子 → Direct 三种子 → D intervention”的顺序冻结队列；tile bootstrap 不能替代随机种子。

### Q6：DGH 具体要怎么优化？

#### D 的必改项

八个 E-OBS 天气字段可以先这样记：

| 字段 | 中文 |
|---|---|
| fg | 风速 |
| hu | 相对湿度 |
| pp | 海平面气压 |
| qq | 全球/太阳辐射 |
| rr | 降水 |
| tg | 平均气温 |
| tn | 最低气温 |
| tx | 最高气温 |

1. all-8（八个天气字段齐全）审计通过时，主协议从 9 维累计摘要切到 Contextformer 对齐的 `8 E-OBS × mean/min/max = 24-D per 5 days`；若本地只有四字段且无法及时替换，则使用明确标记的 12-D fallback（12 维后备方案）。
2. 保留原来 `rr/tg/hu/qq + VPD` 为 `D-core`（紧凑驱动版本）消融，不丢弃原设计。
3. 输入是 `[B, intervals, K_D]`（批次×时间区间×天气字段，K_D 为 24 或后备的 12）路径，不再是 `[B, endpoints, 9]`（批次×目标时刻×字段）累计结果。
4. 同一 `E_D`（天气路径编码器）读 1/2/4 个 token（区间特征单元）来支持 5/10/20 日，不为每个步长设独立 head（输出分支）。
5. DOY（年内第几天）从 `D` 拆出为 `C`，以便 no-D（去掉天气）真正只去天气，不同时删掉季节。
6. Direct（直接式预测）和 ObsWorld 必须使用同一原始 D path（天气路径）、mask（有效标记）、标准化和 `E_D`，不允许输入不对称。

#### G 的优化项

1. P0（最高优先级）只用一个固定 DEM 源，不再每个 cube（小数据块）“找到哪个就用哪个”；推荐 `cop_dem`，同时保留数据缺失 mask（有效标记）。
2. 用 Train-only mean/std（只由训练集计算的均值/标准差），替代固定除以 2000 的粗略归一化。
3. 保持 spatial raster/token（保留空间位置的栅格/特征单元），不降为单个全局标量。
4. 做 no-G（去掉地理信息）和合理的 whole-location G shuffle（整地点交换 DEM），不随机打乱 DEM 像素制造假地形。

#### H 的必改项

1. matched Direct（输入匹配的直接式方法）仍可以使用 absolute horizon query（绝对预测时距查询），它是强基线。
2. 主模型将 `H` 定义为当前转移的 elapsed time `Δt`（这一步经过了多少天）。
3. 同一 `T_theta` 支持 5/10/20 日；正式 100 日预测是 20 次 5 日 open-loop rollout（不喂入真实未来状态的开环滚动预测）。
4. 10 日直接与 5+5 日组合读取严格一致的 D/C 路径，用真实 day-10 监督防止一致地错。

#### 为什么这样改，以及怎样检查它是否真的有用？

| 你可能卡住的地方 | 通俗解释 | 用什么实验检查 | 理想结果 |
|---|---|---|---|
| 为什么不能继续用终点累计 D？ | 两段天气总量相同，不代表发生顺序相同。前 50 天干旱、后 50 天降雨，与反过来会产生不同植被轨迹；累计到终点会把顺序压扁。 | 当前 9-D 累计版 vs 逐五日 D path | 逐区间版本在中长期/OOD 更好，至少不差 |
| 为什么是 24-D？ | 不是因为 24 这个数字神奇，而是八个 E-OBS 字段各取平均、最小、最大，既看通常水平，也看极端；同时与 Contextformer 的天气信息量更公平。 | D-full-24 vs D-core；若只有四字段则明确比较 12-D | 24-D 更好；若 D-core 持平，则说明原紧凑设计已经足够 |
| 为什么把 C 从 D 拆出来？ | “现在是夏天”与“未来五天具体下多少雨”不是同一件事。混在一起后，去掉 D 会把季节也删掉，实验无法判断模型是否真的用了天气。 | full、no-D、calendar-only（只有日历） | full 优于 no-D，且 no-D 仍有合理季节基线 |
| 为什么 G 固定一个 DEM？ | 若每个样本随机使用 NASA/ALOS/COP 中不同产品，模型看到的差异可能来自 DEM 产品，而不是地形本身。 | full vs no-G；必要时整地点交换 G | full 优于 no-G；若不优，则删除“G 提升精度”的主张 |
| 为什么 H 要改成 Δt？ | 世界模型应学习“从当前状态再走五天/十天”，而不只是问“从起点看第几天”。这样同一个转移才能反复使用。 | Direct vs shared-T5 rollout | rollout 的长期误差不爆炸，并接近或超过 Direct |
| 为什么比较 10 与 5+5？ | 同一真实十天不能因为切法不同就变成两个未来。这是在检查模型是否学到可组合演化。 | no-partition vs partition；同时看真实预测误差 | partition gap 明显下降，真实 RMSE 不变差 |
| 为什么要 true-D/no-D/shuffled-D？ | 仅把天气作为输入，不等于模型真的使用了它；模型可能只靠季节和历史图像。 | 正确天气、无天气、整条错配天气 | 正确天气最好；若三者相同，就不能声称学到了外生驱动响应 |

### Q7：最终落实后要做什么？主实验怎样证明叙事？

最终方法链是：

```text
历史 S2 观测 + context phi/mask
                │
                ▼
      Stage1/1.5 Q + history initializer I
                │
                ▼
       predictive state s0
                │  D path + C + G + Δt
                ▼
    shared variable-step transition T
                │
                ▼
        future state s1...s20
                │  fixed S2-L2A observation model
                ▼
    future RGBN → deterministic NDVI → official evaluator
```

主实验列表见本文第 7 节；每个实验都对应一个可被证伪的叙事环节：

- official forecast 证明不是只有概念没有 skill；
- Stage1/1.5 对比证明观测状态学习对未来有用；
- Direct/shared rollout/variable-step 证明改善来自动力学设计；
- partition gap 证明不同时间切分不会导向矛盾未来；
- true-D/no-D/shuffled-D 证明模型真的用了外生路径，而不只是季节性；
- no-G/shuffled-G 证明或否定地理背景的实际价值。

为了阅读时能直接知道“为什么跑”，主实验可按下面理解：

| 实验 | 为什么做 | 实际比较什么 | 理想现象 | 不理想时说明什么 |
|---|---|---|---|---|
| Persistence/Climatology（持续性/气候平均基线） | 排除任务太简单，确认模型不是只复制最后一帧或季节平均 | ObsWorld 与最简单规则 | ObsWorld 明显更好 | 模型没有学到足够未来变化 |
| Contextformer（公开强基线） | 与前沿 EarthNet 方法建立同协议可比性 | 官方 OOD 指标和参数量 | 进入竞争带，长期项有优势 | 若全面落后，世界模型行为证据也难支撑主稿 |
| Official OOD-t（官方时间分布外测试） | 检查模型能否预测训练时期之外的未来 | Val 用于选模型，OOD-t 只作最终测试 | OOD-t 仍稳定，不只在训练/Val 好 | 可能过拟合训练年份或季节 |
| Stage1/Stage1.5 × no-part/part 2×2 | 分开看观测状态预训练包和时间一致性约束是否有用 | 四个模型只改变 initializer（初始化器）和 partition loss（时间分割损失） | Stage1.5 与 part 至少各有稳定收益；二者一起最好 | 哪条轴无效，就把哪条降为辅助证据 |
| Direct/shared-T5/ObsWorld | 判断收益来自直接预测、递归结构，还是 partition 约束 | 同一 D/C/G 和容量下比较三种动力学 | ObsWorld 不低于 Direct，且长期更稳 | rollout 太差说明当前转移还不足以支撑世界模型主张 |
| Partition gap（时间切分差距） | 直接测量“十天一步”和“五天加五天”是否矛盾 | direct 与 composed（组合）结果的状态/像素差 | gap 至少明显下降，同时真实 RMSE 不恶化 | 只降 gap 却伤精度，说明模型只是“一致地错” |
| true-D/no-D/shuffled-D | 证明模型真的响应时间对齐的天气路径 | 正确天气、去掉天气、交换整条天气 | true-D 最好 | 若相同，不能声称外生驱动模拟成立 |
| full/no-G/D-core | 判断地形是否有用，以及原紧凑 D 是否已足够 | 去掉 DEM；24-D/12-D 与 D-core | full 优于 no-G；D-core 若持平也是有价值结论 | G 无效就删去性能贡献，不强行保留 |
| phi probe + Stage2 transfer（探针+迁移） | probe 看状态残留什么；transfer 看这种状态是否真的帮助未来 | Stage1 与 Stage1.5 的条件可预测性及相同 Stage2 结果 | 泄漏不更严重，且 Stage1.5 长期/OOD 更好 | probe 好看但预测无提升，只能算表示诊断 |
| Horizon curve（分时距误差曲线） | 防止平均指标掩盖 60–100 日崩溃 | 每 5 日报告一次误差 | 误差平稳增长，后半段相对优势扩大 | 只在前 25 日好，不足以证明长期模拟 |

### Q8：代码改造和训练的先后顺序是什么？

详细路线在 [46 号文档](46_ObsWorld_AAAI27代码改造与并行执行路线_20260715.md)中，总原则是：

```text
GPU 线：当前 Stage1.5 继续跑 → 结束后验收 → Stage2 smoke → one-seed Gate → 三种子

CPU/I/O 线：all-8 schema 审计 → official evaluator → 24-D 主协议或 12-D fallback stats → manifests/configs
                                                     │
                                                     └─ 全部可与 Stage1.5 并行
```

不等 Stage1.5 结束也可以开始：all-8 数据审计、评估器、D/C/G 字段、Direct/transition 代码 smoke，用旧 checkpoint 只验证通路。真正论文数字要等新 Stage1.5 final checkpoint 固定后重跑。

### Q9：本轮形成哪两个文档？

1. **45（本文）**：九问九答、最终叙事、数据决策、DGH 定义、主实验和合格线。
2. **46**：精确到文件/模块/配置的代码改造方案，以及 GPU 与 CPU/I/O 并行日程。

---

## 2. 最终中心叙事

### 2.1 中文正式版

> **ObsWorld 是一个按观测过程与地表动力学进行角色分工的对地观测世界模型。它从多源、受传感器与成像条件 `phi` 影响的遥感观测中，推断对未来足够的 EO 可观测地表预测状态；在区间外生驱动 `D`、静态地理背景 `G`、日历 `C` 和时间跨度 `H/Δt` 的约束下推演该状态；再通过固定或给定产品条件的观测模型，将未来状态生成为可由真实卫星数据核验的未来观测。**

### 2.2 英文版与中文速读

> **ObsWorld is a role-separated Earth-observation world model.**  
> ObsWorld 是一个按功能角色分工的对地观测世界模型。

> **It infers a predictive state of EO-observable land-surface dynamics from heterogeneous, acquisition-affected observations.**  
> 它从多源、受成像过程影响的观测中推断 EO 可观测的地表预测状态。

> **It advances that state with a shared transition under interval-specific drivers, static geography, calendar, and elapsed time.**  
> 它用同一个转移模型，在区间天气、静态地理、日历和经过时间的约束下推进状态。

> **Its forecasts are trained to remain consistent across valid temporal partitions and are mapped back to satellite observations for verification.**  
> 它要求同一驱动路径的不同时间分段得到一致未来，并把未来状态回到真实卫星观测空间核验。

### 2.3 最短直觉版

> **先从有偏卫星观测中估计对未来有用的地表状态，再模拟它在 DGH 作用下如何变化，最后生成卫星将看到的未来。**

### 2.4 安全的中心方法句

> **ObsWorld couples acquisition-aware multimodal state learning with DGH-controlled, partition-consistent temporal evolution for verifiable long-horizon Earth observation forecasting.**

中文：

> **ObsWorld 将成像条件感知的多模态状态学习，与受 DGH 控制、对时间分割保持一致的状态演化相结合，用于可核验的长时程对地观测预测。**

这句不声称任一组件首创；论文价值要靠第 7 节的联合证据成立。

---

## 3. 数据集的最终口径

### 3.1 论文写法

> **We study the EarthNet2021 benchmark family and use the GreenEarthNet protocol over the EarthNet2021x release for primary evaluation.**

中文：

> **我们研究 EarthNet2021 基准系谱，并在 EarthNet2021x 数据发布上采用 GreenEarthNet 协议进行主评估。**

GreenEarthNet 不是 EarthNet2021 的一个小子集，而是保持训练位置与时空规格兼容的 complete remake/enhanced release。这个口径同时保留 EarthNet 主线和当前最可比的 Contextformer 协议。

### 3.2 当前所需数据

| 数据 | AAAI-27 身份 | 是否重下 |
|---|---|---|
| EarthNet2021x `train` | Stage2 训练 | 否，先审计现有目录 |
| `iid` | Val/official split 构建与调试 | 否，先审计 |
| `ood` | OOD-t/s/st 主评估原始包 | 否，先审计 |
| `extreme/seasonal` | 截稿后过程诊断 | 不下 |
| SSL4EO S1GRD/S2L2A | Stage1/1.5 | 已有，继续用 |
| SSL4EO S2L1C | 可选 product Gate | AAAI-27 不下 |
| 下游数据 | 可选附录 | AAAI-27 不新增 |

### 3.3 为什么 GreenEarthNet protocol 更适合 DGH

- 8 个 daily E-OBS 可构建真正的逐区间 `D path`；
- DEM 是直接可用的空间 `G`；
- 10 context + 20 future、五日规则间隔直接支持 `H/Δt`；
- OOD-t/s/st 分开检验时间、空间与时空外推；
- 官方云 mask 和 NDVI evaluator 比旧 ENS 更直接对准植被动力学。

---

## 4. Stage1/1.5 在 AAAI-27 中的最终身份

### 4.1 不停当前训练

当前更新后的 Stage1.5 已跑一半，它包含显式 `state_projector` 和 `state_decoder_bridge`，对 Stage2 比旧 60k checkpoint 更合适。现在修改运行中代码不会影响已启动进程，却会混乱可复现性，因此等它正常结束。

### 4.2 不把训练 loss 当成论文结论

Stage1.5 必须用三类外部证据验收：

1. **表示证据**：修复后的 geographic-held-out phi/nuisance probe；
2. **配对证据**：近时 S1/S2 state agreement 按 `0–1/1–3/3–7 day` 分层，避免把真实时间变化当成成像差异；
3. **未来效用证据**：Stage1 和 Stage1.5 只替换 checkpoint，其余 Stage2 完全一致，比较 Val/OOD 未来预测。

### 4.3 AAAI-27 的 2×2 直接复用现有 checkpoint

| 观测状态学习 | temporal partition loss | 模型 |
|---|---|---|
| Stage1 | 无 | base state + variable-step no-part |
| Stage1.5 | 无 | acquisition-aware/aligned state + no-part |
| Stage1 | 有 | base state + `L_part` |
| Stage1.5 | 有 | full ObsWorld |

这个设计不需要下载 L1C，也不需要先做新的 cross-decoding repair。如果 Stage1.5 主效应和交互效应都不成立，观测轴降为辅助实验，论文不再写“双轴协同”。

需要诚实限定：Stage1 与 Stage1.5 不只相差一个 phi loss，因此这个 2×2 检验的是**基础状态预训练 vs 完整 acquisition-aware/aligned state-learning package**，不是对 phi 单一因素的严格因果归因。即便交互项成立，也优先写“二者联合有效/compatible”，只有 matched ablation 足够充分时才写“synergistic”。

---

## 5. Stage2 最终方法

### 5.1 观测编码与历史初始化

```text
e_i = Q(x_i, phi_i, validity_i)
s_0 = I(e_1:10, D_history, C_history, G)
```

EarthNet context 可安全使用数据中确实存在、且推理时可得的 S2 产品身份、日期/时间索引和 missing mask，不应永久使用全 neutral phi；但若没有精确采集时刻、太阳角或观测角，就保持相应字段 missing/neutral，不能只凭日期和经纬度伪造精确太阳几何。不输入 future cloud truth、future SCL/dlmask 或事后可得元数据。

### 5.2 DGH 受控可变步长转移

```text
D_hist = D_path[0:10]; D_fut = D_path[10:30]
d_k = aggregate_5day(EOBS[k])                # 24-D main or 12-D fallback
u_a:b = E_D(d_a, ..., d_(b-1), C_a:b)       # shared interval encoder
s_b = T_theta(s_a, u_a:b, G, delta_t=b-a)
x_hat_b = O_psi(s_b, phi_fixed_S2_L2A)
```

同一 `T_theta` 训练 `Δt in {5,10,20 days}`，而正式推理用 20 个 5 日步。所有未来转移只索引 future-relative 的 `D_fut/C_fut`；第一步使用 `D_fut[0:1]`，不能误用完整 `D_path[0:1]`。

GreenEarthNet 官方任务提供真实未来 E-OBS，因此这里属于 prescribed/oracle forcing：论文评估的是“给定未来外生驱动时的条件地表动力学”，不等同于包含未来天气预报误差的实时业务系统。

### 5.3 受控时间分割一致性

```text
s10_direct = T(s0, E_D(D_fut[0:2], C_fut[0:2]), G, 10d)
s10_comp   = T(T(s0, E_D(D_fut[0:1], C_fut[0:1]), G, 5d),
                 E_D(D_fut[1:2], C_fut[1:2]), G, 5d)

P(s)       = LayerNorm(s, elementwise_affine=False)
sym(a,b)   = 0.5*d(a, stopgrad(b)) + 0.5*d(b, stopgrad(a))
L_part     = sym(P(s10_direct), P(s10_comp))
           + sym(O(s10_direct), O(s10_comp))
```

两条分支同时对真实 day-10 RGBN/NDVI 监督。这是对非自治 D/C 控制路径的 composition/evolution consistency，不写成“首个 semigroup loss”。

正式训练不能只见 5/10/20 日局部片段：主 rollout 分支从 s0 开始递归 20 次，并在分层抽取的真实未来端点上监督；partition 分支则在 rollout 轨迹的随机合法位置比较 10 日与 5+5 日。前 10% 步数先训练短 rollout、令 lambda_part=0，随后逐步增加 rollout 长度并 ramp partition 权重，避免一开始就被长链误差和一致性项共同拖垮。

### 5.4 三个必要动力学对照

| 模型 | 定义 | 作用 |
|---|---|---|
| matched Direct-DGH | 每个 horizon 从同一 `s0` 独立查询 | 强精度基线，当前代码的正确身份 |
| shared `T5` rollout | 同一 5 日转移递归 20 步，无 partition loss | 分离“递归结构”的效果 |
| ObsWorld | shared variable-step `T` + `L_part` | 检验可组合世界模型主张 |

---

## 6. AAAI-27 的主实验表和图

### Table 1：Official OOD-t 主结果

行：

1. Persistence；
2. Previous Year / Climatology；
3. Contextformer 6M；
4. 一个强 video/recurrent baseline（优先 PredRNN 或 SimVP）；
5. matched Direct-DGH；
6. shared `T5` rollout；
7. ObsWorld。

列：`R²↑ / RMSE↓ / NSE↑ / |bias|↓ / Outperformance↑ / first-25-day RMSE↓ / Params`。

主表使用未参与训练的 official OOD-t，不在训练集上比精度，也不需要换一个无关数据集才算主实验。

### Table 2A：观测状态 × 时间组合 2×2

使用第 4.3 节四行，所有模型共享 Stage2 数据、D/C/G、预算、训练步数和 evaluator。报告：

- official Val/OOD forecast；
- long-horizon NDVI RMSE；
- 10/20-day observation-space partition gap；
- 两个主效应与交互效应。

预注册四个 simple contrasts、两个平均主效应和 interaction。interaction 的置信区间跨零时，只能写 Stage1.5 package 与 partition jointly effective/compatible，不能写 synergistic。

### Table 2B：DGH 真实使用证据

| 实验 | 要回答的问题 |
|---|---|
| full DGH | 完整模型 |
| no-D | 没有未来天气时模型剩下多少季节/持续性 skill |
| plausible-shuffled D | 模型是否用了时间对齐的天气，而非只使用分布信息 |
| no-G | DEM 是否带来可检验增益 |
| `D-core` | 原设计的 rr/tg/hu/qq+VPD 是否已足够 |

wrong-year/lagged-D、shuffled-G、calendar-only 放附录或只在 Val 报告。

plausible-shuffled D 必须交换不同 location/tile 样本的整条 `D_fut + D_mask`，按起始 DOY 的 30 日 bin 匹配，并优先限制在同一气候区；没有可靠气候标签时用同一纬度带和同一 split。不能逐 token 打乱，因为那会破坏时间自相关并制造明显不真实的天气。C、G 和目标观测保持原样。

### Figure 1：世界模型行为图

- 左：5–100 日 horizon-wise NDVI RMSE，比较 Direct/shared-T5/ObsWorld；
- 右：10/20 日 direct-vs-composed observation gap，同时画真实 forecast error；
- 可选 inset：partition gap 与长时程 OOD error 在 checkpoint/model/region 上的预注册相关性。

### Mini Figure 2：Stage1/1.5 证据

只放最紧凑的两项：

- corrected geographic-held-out nuisance/phi probe；
- Stage1 vs Stage1.5 在相同 Stage2 的长时程/OOD 差值。

不在本轮加 L1C/L2A 四向解码大表。

---

## 7. 怎样的结果才算“合格”？

下列是**项目 GO/NO-GO 工程线**，不是对会议录用的保证。

### G0：协议合格（否则所有精度无效）

- official manifest，不 fallback 扫描根目录；
- official `ndvi_pred` NetCDF 格式与 evaluator；
- 复现官方 Persistence 和 Climatology/Previous-Year 中至少两个；
- context input mask、training target mask、official evaluation eligibility 分开；
- 所有 normalization/imputation 只用 Train。
- all-8 主协议逐文件/抽样检查 `fg/hu/pp/qq/rr/tg/tn/tx`，并固定 `D_hist=0:10`、`D_fut=10:30`；
- 明确主表使用 benchmark-prescribed/oracle future E-OBS，不把它描述成包含天气预报误差的端到端业务系统。

### G1：精度合格

[GreenEarthNet/Contextformer](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf) 公布的 Contextformer 6M 参考是：

| 指标 | 公布参考 | 本项目最低竞争带 | 强 GO |
|---|---:|---:|---:|
| R² ↑ | 0.62 | ≥0.60 | ≥0.62 |
| RMSE ↓ | 0.14 | ≤0.15 | ≤0.14 |
| NSE ↑ | 0.09 | ≥0.07 | ≥0.09 |
| `|bias|` ↓ | 0.09 | ≤0.10 | ≤0.09 |
| Outperformance ↑ | 66.8% | ≥60% | ≥66.8% |
| first-25-day RMSE ↓ | 0.08 | ≤0.09 | ≤0.08 |

“最低竞争带”只用于冲刺时的项目决策，不替代统计检验。ObsWorld 还必须满足：

- 对 matched Direct 的主指标非劣或显著更好；
- 长时程/OOD 不能只靠前 25 天精度遮掩后期崩溃；
- 自有方法最终三种子，同时报 tile/location-cluster paired 95% CI。

### G2：时间动力学合格

必须同时成立：

```text
upper95CI(gap_full - gap_noPart) < 0
upper95CI(forecast_full - forecast_noPart) <= delta_part
upper95CI(longRMSE_full - longRMSE_Direct) <= delta_NI
```

`delta_part` 和 `delta_NI` 在 locked OOD 前冻结为对应 reference NDVI RMSE 的 1% relative。工程期望：相对 no-part，partition gap 至少降低约 20%，且 60–100 日 RMSE 不恶化；如能改善 2%以上则是强信号。百分比是 pilot 调度线，最终结论用成对 CI。

### G3：DGH 使用合格

```text
upper95CI(L_trueD - L_plausibleShuffleD) < 0
upper95CI(L_trueD - L_noD) < 0
upper95CI(L_trueG - L_noG) < 0     # 若不成立，删除 G 增益主张
```

如果 `D-core` 与 full 24-D 持平，这不是失败：可以得出“紧凑物理驱动已足够”的有价值结果。若 all-8 Gate 未通过，则所有主表明确标记 12-D fallback，并披露相对 Contextformer 的输入差异。

### G4：Stage1.5 合格

不要求 phi probe 必须完全随机，而要求：

- corrected probe 相对 Stage1 不显示更严重的条件泄漏；
- Stage1.5 在相同 Stage2 下改善长时程或 OOD，或在不伤精度时显著改善 partition/D-response；
- 2×2 中 Stage1.5 主效应或与 `L_part` 的交互效应成立。

如果全不成立，Stage1.5 只作预训练过程/附录，主模型退回 Stage1 checkpoint。

### G5：AAAI 级证据完整性

- 主表不只有训练集或自建 split；
- 不只有 full vs one ablation；
- 不只报 pixel RMSE，同时报长时程、OOD、D intervention 和 partition behavior；
- 不把降低 consistency gap 本身当成成功，必须不伤真实 forecast；
- 不把 DGH、Q/T/O、variable-step 或 world model 这些名词本身写成首创。

---

## 8. 实验失败时如何诚实收缩

| 失败 | 立即处理 | 还能保留什么 |
|---|---|---|
| 现有数据是 legacy NPZ | 先跑旧协议 smoke；后台只增量下 train/iid/ood | EarthNet 主线，但 AAAI 主表风险上升 |
| Stage1.5 不优于 Stage1 | 主模型退回 Stage1，Stage1.5 进附录 | DGH 受控动力学 |
| rollout 显著弱于 Direct | 停止强 compositional world-model claim | Direct-DGH 可作负结果，但不足以支撑当前 AAAI 方法稿 |
| `L_part` 降 gap 却升真实 error | 删除 `L_part` | shared rollout；需重新查新/评估新颖性 |
| true D 不优于 shuffle/no-D | 删 driver-aligned 强主张 | 季节条件预测，但“外生驱动模拟”不成立 |
| G 无效 | 不宣称 G 带来增益，可作固定背景接口 | D/H 主线；不为缩写强留贡献 |
| 没时间做 L1C/L2A/下游/FM/`U` | 全部不进正文 | 不影响已成立的 EarthNet+DGH+Stage2 闭环 |

---

## 9. 七页正文安排

| 内容 | 页数 |
|---|---:|
| Introduction + contributions | 0.75 |
| Related work | 0.45 |
| Method：state inference + DGH transition + partition loss | 2.20 |
| Protocol | 0.65 |
| Table 1 + Table 2 | 1.30 |
| Figure 1 + Stage1/1.5 mini evidence + limitations | 1.35 |
| Conclusion | 0.30 |

不单独安排通用下游页面。“大模型 + ours”若已有现成数字，可作一行 initializer 补充；否则不占冲刺资源。

---

## 10. 全部思路档案的继承关系

| 档案 | 当前作用 | 是否仍有效 |
|---|---|---|
| 01–10 | 从初版叙事到完整阶段设计的演化路线 | 作历史依据，不直接规范当前实验 |
| 11–21 | SSL4EO、phi、FiLM、Stage1/1.5 实现与 S1 几何/DEM | 重要；用于理解已有投入和字段来源 |
| 22–27 | DGH 字段和多数据集设计 | DGH 物理直觉保留；多数据集联训不进 AAAI-27 P0 |
| 28–29 | 30k/60k phi 泄漏结果 | 数字作历史诊断；因 probe 实现问题不直接进论文 |
| 30–38 | EarthNet 主线、AAAI 实验闭环与代码落实的多轮收敛 | 保留 EarthNet+DGH+世界模型母线；去掉过多下游扩张 |
| 39 | 前沿文献、数据和代码独立审计 | 继续作最重要的外部依据库 |
| 40–42 | 阶段改造、代码行动与 DGH 细化 | 作实现底稿；以 46 的截稿优先级重排 |
| 43 | 代码、协议、overclaim 审计 | 仍然有效；其“稀疏/局部 + U”中心被 44/45 取代 |
| 44 | 恢复 EarthNet、DGH、三柱世界模型 | 叙事有效；数据重下与 L1C/L2A 必做暗示由 45 收缩 |
| **45** | AAAI-27 最终决策和合格线 | **当前规范性方法/实验文档** |
| **46** | 代码改造与执行日程 | **当前规范性工程文档** |

---

## 11. 对初版立意的保留度

| 初版内容 | 保留判断 |
|---|---:|
| 世界模型/模拟真实世界母叙事 | 90% |
| 从有偏观测估计地表状态 | 85%，改为可验证 predictive state |
| DGH | 95%，接口升级而非删除 |
| 状态—动力学—观测三柱 | 90% |
| Stage1/1.5 已有投入 | 90%，直接进 2×2 |
| 任意成像条件可控渲染 | 降到 30%，当前只守 fixed S2/product-limited 边界 |

总体上，立意保留约 **85%–90%**。实质大改发生在 Stage2 的动力学与评估协议，而不是把 ObsWorld 重做成另一个 EO-WM 或普通像素预测器。

---

## 12. 外部依据

- [EarthNet2021](https://arxiv.org/abs/2104.10066)
- [GreenEarthNet / Contextformer, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf)
- [GreenEarthNet official repository and evaluator](https://github.com/vitusbenson/greenearthnet)
- [EO-WM](https://arxiv.org/abs/2606.27277)
- [Earth-o1](https://arxiv.org/abs/2605.06337)
- [Intrinsic Differential Consistency](https://arxiv.org/abs/2605.08454)
- [AAAI-27 Main Technical Track Call](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/)
