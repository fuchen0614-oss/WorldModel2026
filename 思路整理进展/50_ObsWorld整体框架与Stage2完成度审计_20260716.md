---
title: ObsWorld 整体框架与 Stage2 完成度审计
aliases:
  - ObsWorld 当前框架总览
  - 47 号文档完成度审计
tags:
  - ObsWorld
  - Stage2
  - WorldModel
  - AAAI27
  - 进度审计
created: 2026-07-16
status: 代码骨架已成形｜真实数据训练与论文证据未完成
related:
  - "[[47_ObsWorld_Stage2正式代码技术指导与实现规范_20260716]]"
  - "[[48_ObsWorld_EarthNet2021x统一数据协议与主实验规范_20260716]]"
  - "[[51_ObsWorld_DGH字段构造与使用规范_20260716]]"
  - "[[52_ObsWorld_AAAI27中心叙事训练实验与写作总纲_20260716]]"
---

# 50. ObsWorld 整体框架与 Stage2 完成度审计

> [!abstract] 直接结论
> **47 号文档没有“全部完成”。**它是一份从数据契约、模型、训练、评估到论文实验的完整技术规范，当前已经完成其中大部分**代码骨架、协议保护与合成测试**，但尚未完成真实数据的完整统计量与 preflight（训练前检查）、32/128 cube 过拟合、正式 Stage2 训练、IID/OOD 主表、强基线、多随机种子统计，以及 observation correction（再观测校正）与正式训练器的端到端接入。

> [!important] 当前最准确的状态
> ObsWorld 已经从“旧 9-D Direct-DGH 原型”发展为一套可创建、可训练、可续训、可导出和可核验的 Stage2-v2 框架；但它目前仍是 **code-ready（代码就绪）**，还不是 **result-ready（结果就绪）**，更不是 **paper-ready（论文就绪）**。

---

## 1. 我们现在到底有一个什么框架

ObsWorld 当前被定义为一个 **observation-correctable Earth observation world model（可由新观测校正的地球观测世界模型）**。

它模拟的不是完整地球，也不是不可观测的绝对真实物理状态，而是：

> 在给定气象、季节和地理条件下，维持一个由观测历史形成的 predictive belief（预测信念状态），把该状态向未来连续推进，解码为可核验的未来卫星观测，并在新的局部有效观测到来时修正内部状态。

整体状态机可以写成：

```text
历史遥感观测 x_context
        │
        ▼
状态初始化 I：形成当前 predictive belief b0
        │
        ├── D：逐五日天气驱动路径
        ├── C：季节/日历位置
        ├── G：Copernicus DEM 地理背景
        └── Δt：本次推进的时间长度
        │
        ▼
共享转移 F：b_t → b_(t+1)
        │
        ▼
观测模型 H：b_t → 未来 RGBN 卫星像素
        │
        ├── 没有新观测：继续 open-loop rollout（开放循环推演）
        └── 有新观测：U 根据可见区域残差修正 b_t，再继续推演
```

这里的世界模型身份由四项能力共同支撑：

1. 状态由历史观测形成，而不是只靠一个未来时距编号；
2. 同一个短步转移反复调用，完成 100 天开放循环推演；
3. 状态可以被解码回真实卫星观测空间接受检验；
4. 新的部分观测能够更新状态，并改善更新后的未来预测。

当前第 1–3 项已有正式代码骨架；第 4 项只完成了独立状态契约与单元测试，尚未形成端到端训练系统。

---

## 2. 各阶段在整体框架中的作用

| 阶段 | 目标 | 当前作用 | 当前状态 |
|---|---|---|---|
| Stage1 | 学习遥感图像表征 | 提供 S1/S2 视觉编码器初始化 | 已有代码与历史 checkpoint；本文不重新判定其精度 |
| Stage1.5 | 在 `phi` 条件下学习更稳定的观测状态 | 作为 Stage2 状态初始化器候选 | 训练代码已存在；最终 checkpoint 与 Stage2 价值仍需确认 |
| Stage2-D | Direct24（直接多时距预测） | 与世界模型共享 D/C/G、初始化器和解码器的公平对照 | 代码与合成测试完成；真实训练未完成 |
| Stage2-R | Rollout24（20 步开放循环推演） | 证明共享短步动力学能连续模拟可观测地表演化 | 代码与合成测试完成；真实训练未完成 |
| Stage2-P | Partition24（时间分割一致性） | 检查 10 天一步与 5+5 天组合是否给出一致未来 | 代码与合成测试完成；真实训练未完成 |
| Stage2-U | Observation correction（再观测校正） | 新观测到达后安全更新 belief | 独立 cell/rollout 契约完成；未接入数据、模型工厂和 trainer |
| Stage3/论文评估 | IID/OOD 主表、压力测试、强基线与统计 | 把模型能力转化为 AAAI 证据 | 尚未开始正式结果生产 |

为了避免名称继续混乱，当前最实用的称呼是：

- **Direct24**：公平直接预测对照；
- **Rollout24**：无未来观测的开放循环世界模型；
- **Partition24**：带时间可组合性约束的开放循环模型；
- **ObsWorld-Correct**：未来完成再观测校正后的最终系统。

---

## 3. 47 号文档到底完成了多少

47 号文档同时包含“已经实现的功能”和“最终论文必须达到的标准”。因此不能只看文件是否存在，而应按四个层次判断。

### 3.1 L1：数据和协议层

| 要求 | 代码状态 | 真实产物状态 | 判断 |
|---|---|---|---|
| 24-D E-OBS 固定顺序 | 已实现 | 审计样本通过 | 代码完成 |
| 30 个五日 D token 与 index 10 未来起点 | 已实现并有单测 | 尚未用正式训练产物验证 | 代码完成 |
| C_path 与 delta_t_path | 已实现并有单测 | 正式训练未运行 | 代码完成 |
| 固定 `cop_dem` | 已实现并强制检查 | 抽样字段检查通过 | 代码完成 |
| train/val/IID/OOD manifest | 冻结脚本已实现 | 正式 frozen artifacts 尚未确认落盘 | 部分完成 |
| train-only conditioning stats | 脚本已实现，支持并行读取 | 完整 `train_dev` 统计文件尚未确认 | 部分完成 |
| 三类 mask 隔离 | 代码与静态测试完成 | 仍需真实 batch 审计 | 部分完成 |
| official track/evaluator 对齐 | 导出与评分链路已实现 | IID/OOD 正式结果尚无 | 部分完成 |

因此，L1 不是“完全完成”，而是：**协议代码基本完成，真实冻结产物仍缺最后闭环。**

### 3.2 L2：公平预测模型层

已经完成：

- `ObsWorldV2Core`：共享观测编码、状态初始化、G 编码和 RGBN 解码；
- `IntervalDriverEncoder`：统一读取 1 个或多个 D/C 时间段；
- `ControlledTransition`：同一状态转移接收 D、C、G 和时间长度；
- `ObsWorldDirectPathModel`：每个终点从同一历史状态直接预测；
- `ObsWorldRolloutModel`：前一步预测状态继续作为下一步输入；
- `ObsWorldPartitionModel`：比较 10 天直接路径与 5+5 天组合路径；
- Direct/Rollout/Partition 配置继承，减少输入和预算不公平；
- 128×128 RGBN 解码、NDVI 损失、课程学习和时距抽样。

尚未完成：

- 真实 EarthNet 数据上的 32/128 cube 过拟合；
- GPU 显存、吞吐与数值稳定性验证；
- Direct24、Rollout24、Partition24 的 `val_dev` 可比较结果；
- 判断 rollout 是否相对 Direct 出现长期崩溃。

因此 L2 是：**模型结构已完成，真实训练验收未完成。**

### 3.3 L3：完整世界模型动力学层

已有：

- 共享五日状态转移；
- 最长 20 步、100 天开放循环；
- variable-step（可变时间段）路径；
- 10 天 vs 5+5 天 partition consistency（时间分割一致性）；
- endpoint（终点）真实 RGBN/NDVI 监督；
- no-D/no-G 结构开关；
- checkpoint 精确续训、配置锁定和来源追踪；
- q=0 恒等、先预测后更新、部分支持更新和未 reveal mask 不泄漏的 correction 契约。

仍缺：

- D 的 true/no/shuffled 实际实验；
- partition gap 的真实数值；
- observation correction 与 EarthNet reveal 数据、共享编码器/解码器和训练循环的连接；
- VanillaFilter、PredRNN-online 等公平更新基线；
- 再观测是否真正改善 reveal 之后的未来预测。

因此 L3 是：**开放循环动力学代码基本成形；“可校正世界模型”仍只完成底层契约。**

### 3.4 L4：论文级完成

当前尚未完成任何一项正式论文结果：

- 没有锁定后的 IID/OOD 主表；
- 没有三随机种子与 tile-cluster bootstrap（地图格聚类自助统计）；
- 没有强基线同协议复现；
- 没有 horizon curve（时距误差曲线）；
- 没有 correction gain（再观测收益）主表；
- 没有 failure/clear-fraction 分层分析；
- 没有最终结果支持或否定中心 claim。

因此不能说“47 已经全部实现”，也不能说“Stage2 已经达到 AAAI 论文标准”。

---

## 4. 已经完成的工程保护

当前工程基础比旧原型完整得多，主要保护包括：

1. **数据不会静默混用**：formal 模式要求显式 manifest；
2. **旧 9-D 与新 24-D 不会伪装成同一协议**：两条路径独立命名；
3. **目标和官方评估 mask 不会进入模型输入**；
4. **Direct/Rollout/Partition 共享模型组件与输入协议**；
5. **checkpoint 保存完整配置、数据位置、随机状态和来源摘要**；
6. **断点恢复会检查 batch size、world size 和 loader 位置**；
7. **预测文件原子写入并带 SHA-256 清单**；
8. **评分会拒绝缺失、篡改或混入旧预测的目录**；
9. **sanity bundle 明确标记为非正式结果，不能误入主表**；
10. **全套本地回归测试最近一次为 116 passed，另有 11 个已知第三方警告。**

最近稳定代码点：

| Commit | 内容 |
|---|---|
| `66be516` | Direct24 |
| `80f59f8` | Rollout24 |
| `a3b0f6d` | Partition24 |
| `567b006` | 可复现 checkpoint |
| `46785ba` | 评估来源与预测完整性 |
| `9f09b38` | 原子冻结数据协议 |
| `fe8f004` | 正式 Stage2 launcher（启动器） |
| `d406bd2` | 并行统计与 sanity bundle |
| `b83b8a3` | 可见性安全的再观测校正契约 |

这些提交证明的是“软件逻辑可运行、错误可被拒绝”，不证明模型已经有论文级精度。

---

## 5. 当前数据证据能证明什么

仓库中的 `reports/earthnet_protocol/audit_metadata.json` 记录：

| split | 文件数 | 当前证据 |
|---|---:|---|
| train | 23,816 | 统计目录；抽查 64 文件 schema（字段结构）通过 |
| iid | 4,205 | 统计目录；抽查 64 文件 schema 通过 |
| ood | 4,202 | 统计目录；抽查 64 文件 schema 通过 |
| extreme | 3,972 | 已统计目录，当前报告未打开 NetCDF 内容 |
| seasonal | 3,880 | 已统计目录，当前报告未打开 NetCDF 内容 |

抽样检查已覆盖 8 个 E-OBS 字段、4 个 S2 波段、`cop_dem` 和评分相关字段，因此足以支持 24-D 代码开发。但它不能代替：

- 全量数值完整性；
- 正式 manifest 冻结；
- 完整 train-only 统计量；
- 真实 DataLoader preflight；
- 正式 IID/OOD 评分。

---

## 6. 当前框架最需要警惕的三个问题

### 6.1 47 的勾选表已部分过时

47 第 21 节中的部分数据/模型项仍显示 `[ ]`，但对应代码已经实现；与此同时，一些看似“代码完成”的项目还没有真实实验。因此后续不应机械地按旧勾选框判断，而应以本文的“代码状态 + 真实产物状态 + 论文证据状态”三列为准。

### 6.2 开放循环动力学与最终新意不是一回事

Direct24、Rollout24 和 Partition24 是世界模型身份的基础，但仅靠 recurrence（递归）和 partition（时间一致性）未必足以形成强方法新意。当前更有潜力的中心增量是 observation-aligned residual correction（观测对齐残差校正），但它还没有接入正式训练。

### 6.3 Stage1.5 不能预先写成必然贡献

Stage1.5 是有价值的已有投资，但论文中只能在同一 Stage2 下与 Stage1 公平比较。若它不改善 `val_dev` 或 OOD，应该作为辅助/附录或删除行，而不能为了保留旧工作而扭曲主结论。

---

## 7. 下一步最合理的执行顺序

### 第一阶段：把真实数据链闭合

1. 冻结 `train_dev/val_dev/train_all/iid/ood/extreme/seasonal` manifest；
2. 用 `train_dev` 完整计算 `conditioning_stats_v2_train_dev.json`；
3. 运行真实数据 preflight，确认 24-D、C、G、H、mask 与 DataLoader；
4. 记录最终 Stage1.5 checkpoint 路径与 SHA-256。

### 第二阶段：先得到主线模型的最小真实结果

1. 创建 32-cube sanity bundle；
2. 依次运行 Direct24、Rollout24、Partition24 的过拟合；
3. 扩展到 128 cube；
4. 检查 loss、RGBN/NDVI、长期误差、partition gap、checkpoint/resume；
5. 只在全部正常后进行 `train_dev → val_dev` one-seed pilot（单随机种子试验）。

### 第三阶段：决定最终 AAAI 新意是否成立

1. 把 correction 契约接入共享 `F/E/P/H`；
2. 实现 matched VanillaFilter；
3. 实现或同协议复现 PredRNN-online；
4. 在 `val_dev` 做 day25/day50 reveal；
5. 只有 correction 同时优于强更新基线且 open-loop 不崩，才进入三随机种子主实验。

### 第四阶段：形成论文证据

1. 锁定配置；
2. 最终 IID/OOD 各评一次；
3. 生成主表、时距曲线与再观测收益曲线；
4. 做 D 对齐、q/age、Stage1/1.5 等必要消融；
5. Extreme/Seasonal 只作为补充压力证据。

---

## 8. 最终判断

> [!summary] 是否可以开始训练 Stage2
> **可以开始真实数据 preflight 和 32-cube sanity；不应该直接开始完整三随机种子主实验。**

> [!summary] 47 是否已经全部完成
> **没有。**代码层大约已覆盖 47 的数据协议、Direct/Rollout/Partition、训练恢复和评测保护；真实训练、正式对比、在线校正集成和论文结果仍未完成。

> [!summary] 当前最重要的里程碑
> 不是继续堆新模块，而是先让 Direct24、Rollout24、Partition24 在同一真实数据清单上跑通 32/128 cube，并用 `val_dev` 判断开放循环地基是否成立。
