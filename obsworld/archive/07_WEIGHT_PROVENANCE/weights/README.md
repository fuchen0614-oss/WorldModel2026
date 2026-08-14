# Stage1–Stage1.5 最终权重

本目录只保留最终关键权重：

- `stage1_final/checkpoint_epoch200_step_95000.pt`：Stage1 最终 95k；
- `stage1_5_final_state_bridge/checkpoint_step_60000.pt`：Stage1.5 最终 60k state-bridge。

来源为私有仓库 `fuchen0614-oss/WorldModel2026-weights` 的 `stage1` 与 `stage1.5`
releases。未复制 5k–55k 中间 checkpoint。Stage1 release 同时提供
`checkpoint_step_95000.pt`，但其 SHA 与 epoch200 文件完全相同，因此不重复归档。

身份与严格加载结论见上一级 `WEIGHT_STATUS.md`、`WEIGHT_RECOVERY_MANIFEST.md` 和
`STRICT_LOAD_VALIDATION.txt`。
