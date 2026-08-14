# Provenance 与权重状态

## 当前作者口径

当前正文、代码发布包和补充材料采用：

- 40 epochs；
- 14,880 optimizer updates；
- Q1–Q3 使用完成完整训练协议的同一个最终 TerraState 模型；
- validation forecast performance 用于模型选择；
- OOD-t、Q2 和 Q3 不参与选择。

## 当前归档能否提供权重

能够提供一套历史可复验权重，但不能提供作者确认的 14,880-update 最终权重。

已经从公开 GitHub release 恢复：

`07_WEIGHTS_AND_PROVENANCE/historical_boundary80_release/checkpoint_boundary80.pt`

该文件的本地 SHA-256 已独立验证为：

`644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd`

它严格加载到 commit `52578ca` 的 `TerraStateV2`，无 missing 或 unexpected
keys。checkpoint 自身记录 `step=11904`、`stage=2` 和
`candidate=stage2_end_boundary80`。

历史候选台账还记录了 14,880-step `checkpoint_fsval_best.pt` 和
`checkpoint_last.pt` 的 weight SHA，但公开 release 没有提供这两个二进制，
当前原工作区中也没有找到可复制版本。因此不能把已恢复的 boundary80 权重
改名或解释为最终 14,880-update 权重。

## 需要明确保留的历史冲突

`04_RESULTS_EVIDENCE/historical_release_provenance/` 中的旧 release 记录把结果绑定到 `checkpoint_boundary80.pt` / update 11,904；当前作者确认和正式正文使用完成 14,880 updates 的最终模型。两者不能同时作为同一 checkpoint 身份的机器可验证证据。

本归档采用以下处理：

1. 当前论文口径以作者确认的 14,880 updates 为准，不恢复 boundary80 文案。
2. 历史 release 文件不删除，因为它们包含结果数组、运行记录和早期 provenance。
3. 历史目录被明确标记为 historical，不得直接覆盖当前事实。
4. 若未来取得最终 14,880-update checkpoint，应补充二进制、重新计算 SHA，并重新冻结 Q1–Q3 provenance。

## Q3 的额外 provenance 边界

Q3 原始 JSON 自身未内嵌 checkpoint SHA 或 evaluator commit。当前关联依赖 release bundle、运行日志和结果台账。这个缺口不改变已报告数值，但会影响独立机器审计的完整性。
