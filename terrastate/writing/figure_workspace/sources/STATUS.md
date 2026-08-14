# TerraState Figure Session Status

## 1. 当前状态

**DONE — FIGURE 2 FRIEND-PPT ADAPTATION INTEGRATED**

作者批准以 `示例/fig2——2.pptx` 第 1 页作为 Figure 2 的视觉母版。经版面、
方法语义和素材 provenance 审核后，原页没有被直接复制；已用原创矢量元素重构为
可编辑的 Figure 2，并由正文会话接入正式 `main.pdf`。旧 SVG、PPTX、PDF 与预览
仍原样保留为历史草案。

### 1.1 本轮 Figure 2 落地

- 审核报告：`FIG2_FRIEND_PPT_AUDIT.md`
- 构建脚本：`source/build_fig2_friend_adaptation.py`
- 可编辑 PPTX：`source/fig2_friend_adapted.pptx`
- 可编辑 SVG：`source/fig2_friend_adapted.svg`
- 矢量 PDF：`export/fig2_friend_adapted.pdf`
- 300 dpi PNG：`export/fig2_friend_adapted.png`
- 灰度预览：`qa/fig2_friend_adapted_grayscale.png`
- 论文尺寸预览：`qa/fig2_friend_adapted_paperscale.png`
- 导出清单：`FIG2_FRIEND_ADAPTATION_MANIFEST.json`
- 正式论文资产：`paper/figures/terrastate_architecture_fig2.*`

新版 PPTX 为 7.0 × 3.18 英寸、单页、137 个原生对象，不含嵌入位图。图中
EO、天气、地理、状态和预测瓦片均为原创架构示意，不作为真实输入、输出或
定性实验结果。

## 2. 已完成内容

- 复核 EO-WM Figure 1/2、本地 AAAI 框架图锚点、`示例/` PPT与图片，以及当前
  TerraState方法契约和冻结Q1–Q3证据。
- 按作者反馈撤回“极简图标条”方向，在原三面板叙事基础上重新展开Figure 1：
  `(a)`借鉴EO-WM的上下领域映射，同时新增`output observable / state use ? / forcing use ?`
  验证带；`(b)`完整保留TerraState状态路径、`b_h+r_h`闭合及Q2/Q3接口；
  `(c)`用Q1前提→Q2定义性核心→Q3外部驱动落地的证据阶梯收束。
- 经独立方法真实性复核，Panel (a)的一般EO状态已改为`unobserved Earth-surface state`，
  `predictive state`只留给TerraState；Panel (b)增加极细`b_h`旁路，确保Q2表达为只移除
  `r_h`而不是删除整个预测器。
- 不直接复用EO-WM的`General World Model`宽泛表述、汽车图形、极端benchmark或具体构图；
  新增“endpoint accuracy仍不能检验state/forcing pathway”的TerraState桥接问题。
- Figure 1蓝图已为每个可放图位置补充素材提示词，并区分真实EO/模型输出与允许使用的
  抽象状态、驱动和干预图标。
- 纸面施工已锁定“必显/可选/caption”三级文字层级，保留完整故事结构，同时避免把蓝图
  中的全部长文案机械塞入7英寸图面。
- 完成 Figure 2 施工蓝图，并在本轮将其收敛为结果无关的架构图：
  历史上下文、`q/P/z_t`、共享天气条件转移 `T`、`O` 状态读出、
  `b_h+r_h` 闭合以及 Q2/Q3 接口。训练监督仍由 Figure 1 和正文说明，
  不塞入 Figure 2。
- 锁定两图全部中英文短文案、逐箭头端点、面板比例、真实图像尺寸、裁剪方式、
  英文caption、中文解释、AAAI双栏缩放检查及与EO-WM的差异。
- 为Figure 1/2补充纯中文ASCII逻辑版，并新增一页式中文速览，便于作者先按中文
  理解数据流和干预位置，再施工英文论文图。
- 完成真实素材清单、provenance字段、统一mask/crop/color scale规则、闭合恒等式
  验收和禁止伪造方案。
- 独立只读回归审核已通过：无Critical或Major方法/施工问题。

## 3. 新建或修改的文件

- `FIGURE_1_BLUEPRINT_ZH.md`
- `FIGURE_2_BLUEPRINT_ZH.md`
- `FIGURE_TEXT_COPY.md`
- `FIGURE_ASSET_CHECKLIST.md`
- `FIGURE_BLUEPRINT_QUICKLOOK_ZH.md`
- `FIG2_FRIEND_PPT_AUDIT.md`
- `FIG2_FRIEND_ADAPTATION_MANIFEST.json`
- `source/build_fig2_friend_adaptation.py`
- `source/fig2_friend_adapted.pptx`
- `source/fig2_friend_adapted.svg`
- `export/fig2_friend_adapted.pdf`
- `export/fig2_friend_adapted.png`
- `qa/fig2_friend_adapted_grayscale.png`
- `qa/fig2_friend_adapted_paperscale.pdf/png`
- `STATUS.md`

正文会话已同步修改 `paper/main.tex`、`MANUSCRIPT.md`、
`MANUSCRIPT_ZH.md`、`MANUSCRIPT_ZH_FULL.md` 和中文审阅 PDF，并新增
`paper/figures/terrastate_architecture_fig2.*`。未修改参考文献、训练/评测代码、
checkpoint 或实验结果原文件。

## 4. 尚未解决的问题

- 本地没有可追溯的 Figure 1 真实 EO 历史/future EO 和 TerraState 示例预测；新版蓝图
  允许在素材缺失时使用“无图槽位”，但禁止用伪造图填充。
- Figure 2 已明确采用架构示意，不再等待真实 `b_h/r_h/\widehat y` 个案；这些
  图块不作为定性证据。
- Figure 3 仍缺 provenance 完整的逐样本或固定定性图源；冻结聚合 CSV 可以支持
  Q2/Q3 方向和区间，但不能替代真实遥感案例。

## 5. 需要总控决定的事项

- 决定 Figure 1(a) 是否放真实 sparse EO/future EO；动作条件 WM 部分统一使用原创抽象图标。
- 决定 Figure 1(b) 是否放真实 TerraState forecast，或先采用无图预测框。
- Figure 1 Panel (c)已锁定为无详细数值的层级证据卡，不需要逐样本案例。
- Figure 2 已正式接入，不再等待总控决定。

## 6. 建议的下一步

1. 作者审核正式 PDF 第 5 页的 Figure 2 纸面效果。
2. 后续按 Figure 1 蓝图重画概念—贡献图，使 Figure 1 与 Figure 2 的职责完全
   分离；在此之前保留当前 Figure 1，不做无依据替换。
3. Figure 3 只在 provenance 完整的真实行为证据到位后制作。
