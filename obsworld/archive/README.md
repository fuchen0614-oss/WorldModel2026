# ObsWorld Stage 1 → Stage 1.5 精选归档

这是对 WorldModel2026 最初训练路线至 Stage 1.5 的独立本地精选快照。它用于代码学习、实验复盘和以后继续完善“从观测表征到显式状态”的初始研究叙事。

用户先前要求“结束当前工作后回看”的长期母叙事文档，已确认为
`09_LONG_TERM_VISION/` 中正文标题为 `AAA00` 和 `AAA01` 的 72、73 号文档。
其中 73 明确记录 3–6 个月旗舰计划。更早的 39 号独立总审查也保留在
`05_DESIGN_AND_NARRATIVE/`；这些文件用于长期复盘，不代表其中每项扩展都已
实现。

## 快速入口

1. `00_START_HERE/STAGE1_TO_1_5_MAP.md`：端到端流程与代码入口。
2. `00_START_HERE/RESULT_TRUTH_AND_LIMITATIONS.md`：哪些结论成立、哪些不成立。
3. `00_START_HERE/CONTINUATION_NARRATIVE.md`：值得延续的研究主线与下一步。
4. `07_WEIGHT_PROVENANCE/WEIGHT_STATUS.md`：已恢复的 Stage1 95k、Stage1.5 60k 最终权重及严格加载记录。
5. `06_LEARNING_SYSTEM/大纲.md`：此前创建的项目学习体系。
6. `00_START_HERE/RUN_FROM_ARCHIVE.md`：从归档续训时的数据、配置和命令。
7. `00_START_HERE/FINAL_ARCHIVE_QA.md`：最终验证门禁和仍待恢复项。
8. `08_STAGE2_CONTINUATION/README.md`：隔离保存的 Stage2 延续代码、两份关键 best 权重及正式结果。
9. `SOURCE_MAP.tsv`：逐文件来源、SHA、证据层和保留原因。

## 代码快照

- Git commit：`bbdd4dc29b0bacfd7af4a143ee7987d97c0b330d`
- 日期：2026-07-17 10:40:01 +08:00
- 主题：`Add Stage1.5 60k run metadata`
- 所有纳入的 Stage 1/1.5 代码文件均与该提交字节一致。
- Stage 1/1.5 训练入口已真实导入，Stage 1.5 两组 CPU 测试共 12 项通过。

## 重要提醒

Stage 1.5 的 60k 结果没有证明完整成像不变性。线性 cross-covariance 约束保持较低，但非线性 MLP probe 仍能恢复部分 orbit/satellite 信息。这个结果是后续设计必须面对的事实，因此被保留，而不是作为“失败垃圾”删除。

## 原冻结区不包含

`00`–`07` 冻结区不包含 Stage 2 代码、后期 TerraState 主模型、重复 plan-b
仓库、旧 Plan A、`.bak`、环境目录、数据集本体、缓存、普通训练日志和无结论
的过程产物。

补充说明：原始 Stage1–1.5 冻结区仍不混入 Stage2；2026-07-31 新增的
`08_STAGE2_CONTINUATION/` 是独立的后续研究入口，保存 commit-exact 最新
Plan-A Stage2 代码、强相关文档及诚实的历史结果边界。
