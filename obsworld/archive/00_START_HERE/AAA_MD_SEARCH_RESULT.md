# “AAA 文档”追溯与确认结果

2026-07-31 重新按用户提供的内容线索做了文件名、正文、全部 Git 历史、
悬空 Git 对象和本地历史搜索。检索范围包括：

- `WorldModel2026/`
- `WorldModel2026-planb/`
- `WorldModel2026-planb-v2train/`
- `TerraState_AAAI27/`
- `WorldModel2026` 全部 git 提交的文件名

## 最终确认

用户补充“是在纠结方案 A/B 时写的”“短期做不到，完整目标需要数月”后，
时间线与内容可以唯一对齐到：

`WorldModel2026/思路整理进展/72_ObsWorld叙事母稿与AAAI27正文蓝图_锁定版_20260722.md`

确认依据不是只看文件名，而是它同时满足用户记忆中的四个内容锚点：

1. 原文件确实位于 `WorldModel2026/思路整理进展/`；
2. 文件名包含 `AAAI27`，正文第一行更明确写为
   `# AAA00 · ObsWorld 叙事母稿 + AAAI-27 正文蓝图（锁定版）`；
3. 日期为 2026-07-22，与方案 A/B 的 74、75 号执行文档属于同一阶段；
4. 第 6 节把当前短期稿称为 `AAA00`，把完整目标明确延期为 `AAA01`，包括
   S1 云鲁棒预测和多任务广度，并链接 73 号旗舰计划。

72 号链接的完整展开文档是：

`WorldModel2026/思路整理进展/73_ObsWorld统一世界模型设计_S1云鲁棒_后续venue_20260722.md`

其正文第一行是 `AAA01`，状态明确写为“旗舰前向计划（3–6 个月，后续
venue）”，并将 S1 时空对齐、重训、消融、可控性和多任务拆成 3–6 个月的
里程碑。这正是用户记得的“目标不是不可行，而是短期来不及”的来源。

这两个文件在原目录中并未物理丢失，只是文件名不是以 `AAA00/AAA01` 开头。
现已作为逐字节精确副本补入：

- `09_LONG_TERM_VISION/72_ObsWorld叙事母稿与AAAI27正文蓝图_锁定版_20260722.md`
- `09_LONG_TERM_VISION/73_ObsWorld统一世界模型设计_S1云鲁棒_后续venue_20260722.md`

源文件与归档副本 SHA-256 分别为：

- 72：`15d2ff51818b8bf0b947510b017d8038e142b655f21ad60e07240cf8fd25abd9`
- 73：`af4b239871a50f042fc61474f1a697dde36ec744d8700d5e06ed4f2b4c007187`

## 关联但不是同一文件的早期文档

- `67_ObsWorld_核心叙事_相关工作差异_Table1数值与下一步_20260719.md`
  有整节“模拟真实世界发生了什么”，解释预测状态边界。
- `39_ObsWorld_AAAI叙事前沿文献公开数据与代码独立审查_完整汇总.md`
  是更早的独立总审查，明确写“后续工作的首要入口”，并包含“模拟真实世界
  发生什么”、下游任务边界和完整 RQ 证据链。它不是 A/B 同期的 `AAA00`，
  但同样是长期复盘所需的上游材料，故也作为精确副本保留在
  `05_DESIGN_AND_NARRATIVE/`。

最符合“之前为了复盘学习而创建的 Markdown”这一描述的是：

- `WorldModel2026/.learning/大纲.md`
- `WorldModel2026/.learning/README.md`
- `WorldModel2026/.learning/进度追踪.md`
- `WorldModel2026/.learning/疑问记录.md`
- `WorldModel2026/.learning/笔记/Stage1-VAE编码解码器.md`

它们已完整复制到 `06_LEARNING_SYSTEM/`。其中旧大纲有少量概念表述与最终代码不完全一致，例如把 Stage 1 简称为 VAE；学习时应以本归档的 `STAGE1_TO_1_5_MAP.md` 和实际代码为准。

上述 `.learning/` 文件仍已完整复制到 `06_LEARNING_SYSTEM/`，但不再把它们
误认为用户所说的“AAA 文档”。

此外，为支持后续继续研究，Stage2 与 AAAI 证据链最强相关的 9 份
Markdown 已精选加入 `08_STAGE2_CONTINUATION/02_RELATED_DOCUMENTS/`，索引见
`08_STAGE2_CONTINUATION/RELATED_DOCUMENT_INDEX.md`。39 号承担早期独立总
审查，72/73 承担 `AAA00 → AAA01` 长期愿景，08 承担已实现 Stage2 延续代码；
三者角色不同。
