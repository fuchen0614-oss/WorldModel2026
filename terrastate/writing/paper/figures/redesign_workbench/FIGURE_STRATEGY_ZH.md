# TerraState 方法图重设计策略（Phase 2 正式接入版）

> 状态：双图信息层级已获作者批准，彩色矢量稿已完成并接入正式 PDF。  
> 边界：本轮只更新论文图、caption 与镜像稿；训练代码、权重、实验结果和冻结标题/摘要均未改动。  
> 当前事实优先级：84 号定义论文问题与方法型定位；87 号定义极端热旱的压力测试边界；88 号冻结唯一方法与训练合同。86 号中与 87/88 冲突的旧训练目标和旧研发阶段不进入新图。

正式源文件：

- Figure 1：`paper/figures/terrastate_method_overview.tex`
- Figure 2：`paper/figures/terrastate_operational_verification.tex`
- 共用样式：`paper/figures/terrastate_figure_style.tex`
- 可回退旧 Figure 1：`paper/figures/terrastate_overview_v3.tex`

## 1. 推荐布局

推荐采用“两张图、两个职责”的方案。

1. **Figure 1：TerraState Method Overview**
   - 双栏通栏 hero figure。
   - 第一视觉层只回答“TerraState 是什么、预测如何发生”。
   - 主链为：

     \[
     \mathcal H_t
     \rightarrow q_\theta
     \rightarrow P_\rho
     \rightarrow z_t
     \rightarrow T_\psi(u^{\rm full24},g,h)
     \rightarrow z_{t+h}
     \rightarrow O_\omega
     \rightarrow r_h,
     \qquad
     \widehat y_{t+h}=b_h+r_h.
     \]

   - 下方只保留一条明显分离的 training-only 监督带，准确显示
     \(\mathcal L_{\rm GT}+0.5\mathcal L_{\rm KD}
     +\lambda_s\mathcal L_{\rm future\text{-}state}\)。
   - Figure 1 不出现大面积 Q1–Q4 卡片。

2. **Figure 2：Operational State Verification**
   - 采用浅而宽的 claim-to-test evidence map。
   - Q1、Q2、Q3 是三个实边框核心面板；Q4 是窄小、灰色虚线的 optional 面板。
   - 所有面板从同一个 frozen checkpoint 出发，不形成排行榜或新 benchmark 的视觉语法。
   - Q3 中 hot-dry 只作为预注册压力分层，比较其效应与 matched-normal 的差异；它不是模型输入、训练目标，也不是第四种天气干预。

页面空间不足时使用紧凑备选：在 Figure 1 底部加入不超过总图高度 15% 的 verification strip。该备选只用于排版回退，不是首选叙事。

## 2. 当前 v3 的优点

- 已正确区分实线推理、虚线训练监督和点线训练后检验。
- 已准确画出 \(q_\theta\)、\(P_\rho\)、\(z_t\)、共享 \(T_\psi\)、\(z_{t+h}\)、\(O_\omega\)、\(b_h\) 与显式加法闭环。
- 已完整列出三项唯一训练监督，并把 future-state anchor 限定为 \(h=20\)。
- 是可编辑 TikZ 矢量图，论文尺度字体和线宽已经过检查。

## 3. 当前 v3 最大的三个问题

### 3.1 一张图承担了三个叙事层级

v3 同时承担方法主链、训练目标和 Q1–Q4 验证协议。虽然验证区已经压缩，但整张图仍像一个“方法 + 审计 dashboard”。审稿人第一眼需要在三条水平带之间切换，而不是沿一条世界模型闭环读取。

### 3.2 图内标题和分区标题过多，主链被文字包围

`TerraState forecast closure`、三个大分区标题、线型图例、training-only 公式标题和底部验证标题共同占据显著面积。它们多数属于 caption 层的信息，削弱了 \(z_t\rightarrow T_\psi\rightarrow z_{t+h}\) 的视觉中心，也违反本轮“图名只放 caption”的要求。

### 3.3 监督关系更像说明卡片，而不是可追踪的计算图

三项训练信号被写成三个大卡片，但真实的比较端点没有被逐一连接：读者不能立刻看出 GT/KD 监督预测输出，而 future-state 只在 \(h=20\) 对齐 \(z_{t+20}\)。同时，历史 EO、空间状态和预测输出主要由同形矩形表达，遥感/空间状态语义不够直观。

## 4. AAAI 图像锚点的可借鉴原则

### GLAM

- Figure 1 先建立单步推理直觉，Figure 2 再给完整架构。
- 完整架构保持一条端到端阅读方向，局部机制放在第二层。
- TerraState 借鉴“主链优先、必要机制次级”，不复制其圆形符号、双 Mamba 分支或具体构图。

### SparseWorld

- 以表示形态变化和核心状态模块为视觉中心，输入、状态、预测输出之间有清晰的空间语义。
- 大功能区有边界，但主箭头始终连续。
- TerraState 借鉴“空间状态用网格/token glyph 表达”，不复制点云、3D 方块、自动驾驶图标或 decoder 细节。

### WorldAgen

- 架构、训练流程和结果被分成不同面板，说明多层信息必须显式降级。
- 它也展示了把性能图塞进 Figure 1 会导致页面拥挤。
- TerraState 借鉴训练/推理路径的边界，不把性能面板和 checkpoint 工程画进 hero figure。

### Drive-OccWorld

- 先用任务直觉图说明输入、世界状态、未来预测和下游闭环，再用独立方法图展开架构。
- 输入与输出缩略图服务于语义，而不是装饰。
- TerraState 借鉴“历史观测—状态—未来观测”的闭环组织；在真实、固定样本和统一色标尚未冻结前，只预留可替换图像槽，不放伪造遥感图。

## 5. Figure 1 与 Figure 2 分别服务的主张

| 图 | 第一问题 | 服务的主张 | 明确不服务 |
|---|---|---|---|
| Figure 1 | 模型如何从历史形成预测状态并受未来天气推进？ | 一个 history-only predictive state 位于最终预测闭环中；未来天气只经共享 \(T_\psi\) 影响 state contribution；训练期由 GT、KD 与未来状态锚定共同监督 | Q1–Q4 已经通过、hot-dry 已经增强、composition 已成立 |
| Figure 2 | 同一 checkpoint 如何被证伪？ | Q1 预测能力、Q2 load-bearing、Q3 driver response 的匹配检验；Q4 为可选扩展 | 新 benchmark、排行榜、因果/物理正确性、训练时优化这些检验 |

## 6. 明确排除

- 方案 A/B、B4、V2、Stage A/B、Phase-I/II；
- cache 构建、checkpoint 迁移、选模流程、服务器与 DDP；
- physical4、显式 anomaly/stress 输入、hot-dry 标签输入；
- residual carrier、composition loss、output consistency、VICReg、driver distillation 或其他不存在的非零目标；
- 把 observed future EO、teacher 或 target cache 画入推理实线；
- 把 Q4 画成已成立的核心能力；
- 图内大标题、长句、排行榜、装饰性 3D 网络块和未经验证的真实结果图。

## 7. 图像槽位策略

Figure 1 预留三个可替换的语义槽位：

1. cloud-masked EO history：三帧小缩略图叠放并叠加云掩膜纹理；
2. final forecast：一个小型 NDVI/地表预测网格；
3. observed future EO（training only）：一个尺寸更小的目标缩略槽。

第一阶段线框只使用矢量占位，不冒充真实数据。若后续使用真实图片，必须先冻结样本、色标、掩膜、时间点与 provenance；否则保留抽象矢量缩略图。

## 8. Phase 2 输出与接入状态

Phase 1 线框与紧凑备选仍完整保留在本工作区。作者确认双图层级后，
Phase 2 已生成并正式接入：

- `paper/figures/terrastate_method_overview.tex/pdf/png`
- `paper/figures/terrastate_method_overview_grayscale.png`
- `paper/figures/terrastate_operational_verification.tex/pdf/png`
- `paper/figures/terrastate_operational_verification_grayscale.png`
- 最新逐页检查目录：
  `build_review_20260727_phase2_final/`

Figure 1 位于正式 PDF 第 2 页；Figure 2 位于第 6 页。两图均使用 v3
延续下来的克制蓝/绿/紫/橙配色，但颜色不是唯一区分：推理、训练与评测同时由
实线、橙色虚线和点线编码。

## 9. Figure 3 的预留职责

Figure 3 只在真实 Q2/Q3 数组、配对置信区间或按验证集规则冻结的定性 tile
到位后生成，用于呈现 empirical evidence，而不是重复方法或协议。当前正式
PDF 不放任何可见 TBD 图框。若最终页面紧张，保留优先级为 Figure 1、真实
Figure 3、Figure 2；Figure 2 可在结果到位后压缩回文字/表格。
