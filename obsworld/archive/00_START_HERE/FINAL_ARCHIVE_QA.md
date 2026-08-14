# ObsWorld Stage 1 → Stage 1.5 精选归档最终质量门禁

日期：2026-07-31

## 已通过

- 所纳入的训练、配置和评估实现均按 commit
  `bbdd4dc29b0bacfd7af4a143ee7987d97c0b330d` 建立来源记录。
- 原缺失的三个运行依赖已经补齐并与该 commit 字节一致。
- Stage 1 与 Stage 1.5 核心训练入口真实导入通过。
- Stage 1.5 CPU 单元/集成测试 12/12 通过。
- 25 个 Python 文件通过 AST 解析。
- `00`–`07` 原冻结区未发现 Stage 2、Plan B、B4 或 TerraState 污染；
  后续 Stage2 只存在于明确隔离的 `08_STAGE2_CONTINUATION/`。
- 未发现 `.pyc`、`.bak` 或 `.DS_Store`。
- 结果文档同时保留有效结论和非线性 probe 暴露的限制，没有把历史负结果
  改写为成功结论。

## 仍需外部恢复

- Stage 1 95k checkpoint；
- Stage 1.5 30k checkpoint；
- Stage 1.5 60k checkpoint。

归档没有用名称相近或后期模型权重替代上述文件。恢复目标、验证方法和禁止
误配规则见 `07_WEIGHT_PROVENANCE/WEIGHT_RECOVERY_MANIFEST.md`。

两份独立正式 Stage2 checkpoint 已交叉恢复 Stage1.5 60k state-bridge 的
身份信息：大小 363,727,067 B、SHA-256
`24646b89eda5fb97ff03a76da5c136969bd1e2af9d76d60bd9537b6e304ff97d`。
该信息只用于验证将来找回的二进制，不等于二进制已经恢复。

## 后续 Stage2 快照

- commit `541dd76` 的 70 个文件已建立独立 continuation 快照；
- 32/32 相关测试与 13/13 synthetic smoke 通过；
- 历史 A′ 精度未过门、metric-v1 尚未完整训练的边界已明确记录；
- Direct physical4 与 rollout physical4 两条正式训练线各自的 best checkpoint
  已纳入，均在 CPU 上严格加载通过；周期 checkpoint 和 smoke 权重没有纳入；
- 与两份 best 权重对应的 OOD-t 聚合指标、共同 manifest 和 scorer provenance
  已纳入，逐季 parquet、预测文件和过程日志没有纳入；
- 该快照不会被解释为 Stage1–1.5 既有结果或 TerraState 正文最终模型。

## 交付完整性

根目录 `SOURCE_MAP.tsv`、`SOURCE_INVENTORY.tsv` 和 `SHA256SUMS.txt`
分别提供逐文件来源、大小和完整性校验。当前 196 个受检文件全量 SHA 校验
通过；SOURCE_MAP 与实际文件集合一一对应、无重复。后续优先恢复 Stage1/1.5
原权重；短期无法恢复时，只能明确标注地从隔离区的历史 Direct/rollout best
继续，不能把它们改写成 Stage1.5 或 A2-best。
