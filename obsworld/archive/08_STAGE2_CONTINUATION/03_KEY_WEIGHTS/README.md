# Stage2 关键权重

本目录只保留三条历史 Stage2 正式训练线各自的 `checkpoint_best.pt`。它们是
validation 选出的正式 best checkpoint，不是 smoke、周期快照或中间 step。

| 路线 | 文件 | step | validation MAE | 文件大小 | SHA-256 |
|---|---|---:|---:|---:|---|
| Direct physical4 | `direct_physical4/checkpoint_best.pt` | 8000 | 0.03256629 | 178,271,409 B | `1158ffe6644e6a05345cba3fa56ee73af8d1390a2eb078b4b0bc3a94746f91d2` |
| Rollout physical4 | `rollout_physical4/checkpoint_best.pt` | 8000 | 0.03346540 | 178,271,665 B | `8908c62e40b6f71d7ca45aa74047ba2e0c719ea4bc2db7d9cef41587510ead31` |
| Plan-A S1a full24 | `plan_a_s1a_full24/checkpoint_best.pt` | 8000 | 0.03358213 | 335,371,774 B | `2a0a465fe4d4a148a493954a8acc63b0e6e55896b12631cf3bd9efa08440fad5` |

三份 checkpoint 均包含完整 `model_state_dict`（360 个 tensor 项）、optimizer、
scheduler、serialized config、训练 provenance、data position 和 RNG 状态。CPU
审计已确认：在评估模式关闭外部 Stage1.5 初始化依赖后，两者分别严格加载为
`ObsWorldDirectPathModel`、`ObsWorldRolloutModel` 与 full24
`ObsWorldDirectPathModel`，均为 `missing=[]`、`unexpected=[]`。

## 与 Stage1.5 的关系

三份权重都记录了相同的 Stage1.5 初始化器：

- 原始路径：`checkpoints/stage1_5_dual_conditioned_vits_state_bridge_60k/checkpoint_step_60000.pt`
- 原始大小：363,727,067 B
- 原始 SHA-256：`24646b89eda5fb97ff03a76da5c136969bd1e2af9d76d60bd9537b6e304ff97d`

Stage1.5 原始二进制现已恢复到 `07_WEIGHT_PROVENANCE/weights/`，并通过严格
加载。Stage2 权重仍不能倒置冒充 Stage1.5 权重，因为其参数已经接受 Stage2
训练且 checkpoint 结构不同。

## 明确排除

- `checkpoint_epoch100/150/200_*`：周期快照，不纳入精选归档；
- smoke 权重：不纳入；
- 第三方 Contextformer 权重：不纳入；
- 后期 TerraState 权重：保存在另一份 TerraState 归档，不在这里重复。
