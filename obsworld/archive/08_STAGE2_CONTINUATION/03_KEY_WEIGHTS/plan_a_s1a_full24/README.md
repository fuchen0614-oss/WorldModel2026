# Plan-A S1a full24 最优权重

- 文件：`checkpoint_best.pt`
- 来源：私有 release `plan-a-s1a-full24`
- 大小：335,371,774 B
- SHA-256：`2a0a465fe4d4a148a493954a8acc63b0e6e55896b12631cf3bd9efa08440fad5`
- `global_step=8000`
- best validation MAE：`0.033582128665915534`
- 模式：`direct_path_24d`，driver protocol `full24`
- Stage1.5 initializer SHA：`24646b89eda5fb97ff03a76da5c136969bd1e2af9d76d60bd9537b6e304ff97d`
- 代码来源：branch `plan-a-vits`，checkpoint provenance commit
  `d8d2181d1a4d61056c470f85881fdfa907fc210f`

已使用归档 Stage1.5 权重重建 `ObsWorldDirectPathModel` 并执行
`load_state_dict(strict=True)`，missing/unexpected 均为空。
