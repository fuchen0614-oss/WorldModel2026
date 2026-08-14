# 当前论文结果入口

本目录只保留正式正文实际采用的结果表达：

- `tables/`：从 `01_MANUSCRIPT/paper/main.tex` 同步出的最终 Table 1–3；
- `release_metrics/`：Q1–Q3 的结构化数值副本；
- `CLAIM_EVIDENCE_MAP.md`：主张、证据与禁止外推的边界。

旧 release 台账、旧表格措辞和 boundary80 训练身份已经完整迁至：

`../../historical_release_provenance/archived_pre_final_current/`

迁移是证据分层，不是删除。当前论文采用作者确认的 40 epochs / 14,880
updates 口径；但本地仍缺少与该身份匹配的最终 checkpoint 二进制和逐项
机器 provenance。因此：

- 正文数值和最终表格：以本目录为准；
- 历史可执行复验：使用 `historical_release_provenance/` 与已恢复的
  boundary80 权重；
- 不得把 boundary80 的 11,904-step 机器证据改写成 14,880-step 机器证据；
- 取得 14,880-step 最终权重后，应重新冻结 checkpoint SHA 和 Q1–Q3
  provenance。
