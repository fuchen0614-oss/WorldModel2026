# TerraState AAAI-27 精选归档

这是从 `TerraState_AAAI27/` 与 `WorldModel2026/` 中整理出的本地只读式精选快照，创建于 2026-07-30。目标是支持论文复盘、继续修改和提交前核对，而不是保存每一次过程性尝试。

## 从哪里开始

1. `00_START_HERE/PROJECT_MAP.md`：目录用途与推荐阅读顺序。
2. `00_START_HERE/KEY_FACTS_AND_CLAIMS.md`：论文方法、结果和主张边界。
3. `00_START_HERE/KEY_WEIGHTS_AND_RESULTS_INDEX.md`：关键权重、最终 Q1–Q3 数值与中间结果排除规则。
4. `00_START_HERE/PROVENANCE_AND_WEIGHT_STATUS.md`：权重是否在本地、训练身份和历史证据冲突。
5. `00_START_HERE/FINAL_TRAINING_AND_WEIGHT_LINEAGE.md`：从 Phase-I B4 到 TerraState-V2 的真实权重链。
6. `00_START_HERE/FINAL_ARCHIVE_QA.md`：最终通过项与仍待外部恢复项。
7. `01_MANUSCRIPT/paper/main.pdf`：当前英文 PDF。
8. `01_MANUSCRIPT/mirrors/MANUSCRIPT_ZH_FULL.md`：完整中文镜像。
9. `03_CODE_RELEASE/README.md`：面向发布的简化代码。
10. `09_CANONICAL_IMPLEMENTATION_SNAPSHOT/README.md`：真实训练和 Q1–Q3 评估实现快照。

## 归档原则

- 原项目文件没有被删除、移动或覆盖。
- 只复制当前正文、最终图像链路、可编辑图源、发布代码、冻结数值、关键证据、补充材料和最终审计。
- 不纳入编译日志、辅助文件、旧 wireframe、失败版 Figure、重复审计、下载工具链、环境目录和无结论的过程稿。
- 具有科学意义的负结果不被删除；它们会被放入明确的限制或历史证据区域。
- `04_RESULTS_EVIDENCE/historical_release_provenance/` 仅用于保存历史可追溯性，不代表其中每个训练身份字段仍是当前作者口径。

## 快照边界

- 论文标题：*TerraState: A Testable Predictive-State World Model for Weather-Driven Land-Surface Forecasting*。
- 当前 PDF：9 页、letter paper；正文与参考文献边界以该 PDF 为准。
- 当前正文采用作者确认的 40 epochs / 14,880 updates 口径。
- Q1–Q3 的报告数值保存在 `04_RESULTS_EVIDENCE/current/release_metrics/`。
- 已恢复并验真历史 boundary80 checkpoint；它不能冒充作者确认的
  14,880-update 最终权重，后者的二进制仍缺失。
- 真实训练与评估实现已按对应 git commit 建立最小依赖闭包，并完成
  83/83 字节级来源核对、导入检查和 15/15 三阶段训练 smoke。

## 完整性

`SHA256SUMS.txt` 记录本归档全部文件的 SHA-256。`SOURCE_INVENTORY.tsv`
记录文件大小和归档相对路径，`SOURCE_MAP.tsv` 记录逐文件来源和角色。
