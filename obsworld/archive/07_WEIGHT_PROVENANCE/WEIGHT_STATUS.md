# 权重状态

## 应有的关键权重

| 阶段 | 文档记录的权重 | 本地是否存在 | SHA-256 |
|---|---|---|---|
| Stage 1 | `weights/stage1_final/checkpoint_epoch200_step_95000.pt` | 是 | `79b20ee6ddc499c60019ed8590108e08789dcc0d8877d1892eb490b2cc5500df` |
| Stage 1.5 30k | 私有 release `stage1.5/checkpoint_step_30000.pt` | 未归档（中间权重） | `964411a8e7f7b9e8ca39dfaf7431b681873f2652fb0eff775b795469e232c116` |
| Stage 1.5 60k state-bridge | `weights/stage1_5_final_state_bridge/checkpoint_step_60000.pt` | 是 | `24646b89eda5fb97ff03a76da5c136969bd1e2af9d76d60bd9537b6e304ff97d` |

权重于 2026-07-31 从私有仓库 `fuchen0614-oss/WorldModel2026-weights` 的 `stage1`
与 `stage1.5` releases 恢复。GitHub asset digest、本地重新计算 SHA、checkpoint
元数据与严格 CPU load 四层核验均通过。Stage1 release 的两种 95k 文件名内容完全
相同，因此只保留语义更完整的 `checkpoint_epoch200_step_95000.pt`；Stage1.5 只保留
最终 60k state-bridge，不复制中间 step。

## 处理原则

- 本归档没有把 `checkpoints_pulled/direct-p4`、`rollout-p4` 或后期 TerraState
  权重误标为 Stage 1/1.5。Direct/rollout best 只在隔离的
  `08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/` 中作为 Stage2 续研起点保存。
- 新找回权重均复制到本目录的 `weights/`，并记录：
  - 原始绝对路径；
  - 文件大小；
  - SHA-256；
  - 对应 git commit；
  - serialized config；
  - 训练 step；
  - 能否由 CPU/单卡加载。

## 已完成的最小核验

1. Stage 1 95k 已严格初始化共享 encoder/decoder，`global_step=95000`。
2. Stage 1.5 60k 的 encoder、phi encoder、decoder、state projector、state bridge
   均严格加载，且包含 optimizer、scheduler，`global_step=60000`。
3. 历史 alignment 与 nonlinear phi leakage probe 仍保存在 `04_RESULTS/`；没有为归档
   人为重跑或改写科学结果。
