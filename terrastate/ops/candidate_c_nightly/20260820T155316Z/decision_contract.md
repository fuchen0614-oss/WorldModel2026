# Candidate C 决策合同（本轮 attempt）

- 生成时间(UTC): `2026-08-21T09:08:16.115531Z`
- attempt 目录: `/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate/ops/candidate_c_nightly/20260820T155316Z`

## 已冻结工件（路径 + sha256）

| 工件 | sha256 | bytes |
|---|---|---|
| `candidate_c_c0r_config_v1.yaml` | `4dfa913797ba1155b5ce295c9491daa3…` | 1843 |
| `candidate_c_c1_config_v1.yaml` | `593f790c4520136b53efcc0e1e33481e…` | 1843 |
| `candidate_c_design_contract_v1.json` | `d5e80cafe3998b4c220f1190e451881d…` | 12423 |
| `candidate_c_design_contract_v1.md` | `ffd2e963b574b7b0f423d30b13f22874…` | 5611 |
| `environment.txt` | `ac7a70e6cc17f7561563cbe30cd64e7a…` | 596 |
| `candidate_c_formal_queue_v1.json` | `511907a2ebeccaba7f1196c433793250…` | 1310 |
| `run_queue.json` | `47f90ce3029b120a21121dc043ca4623…` | 3057 |
| `candidate_c_selection_contract_v1.json` | `9ae8173adf26b03bbd969c64c54568d6…` | 3372 |
| `source_hashes.json` | `260d791c7ac48c9c5a3fec0e5c84be93…` | 2386 |

已冻结的两个 manifest（由 freeze_manifests.py 先前冻结，此处仅引用）：

- `candidate_c_eo_split_manifest_v1.json` sha256 `160c3ccc5075d386ecdc235a61806610d8475cc46f17973b94a5a9a37ed3cd6b`
- `candidate_c_q4_partition_manifest_v1.json` sha256 `d0a4c6564516ea62f7eda9ebc4018433d1357391ad3a2a3bd8070de1a54e1e0e`

## 硬门状态

- E0 v3: `ACCEPTED`，failures `None`
- CPU 验收测试: pass **119** / fail **0**（119 个用例三套件全绿）
- GPU idle gate 5 轮: PENDING
- 8-rank smoke（`--stop-after-step 32`）: PENDING
- pilot（100–300 updates）: PENDING
- pilot372: SUPERSEDED_BY_BUDGET_CORRECTION（已取消，目录保留为历史记录）
- FORMAL_READY: PENDING

## 预算修正（本次重新冻结的唯一原因）

- 预算与父权重 TerraState v2 的真实 schedule 严格对齐：40 epoch / 14880 update / warmup 300。原记录的 8 epoch / 2,976 update / warmup 100 已确认为事实错误并作废；11,904 仅是父 schedule 中 epoch-32 的中途 checkpoint，不是独立预算。
- 本次授权改动仅三项：max-epochs 8→40、expected_total_updates 2976→14880、lr-warmup-steps 100→300；两臂同时施加，其余全部不变。

## 不可回退的承诺

- 主 checkpoint 预注册在第 14880 个 update，两个臂相同；不得按结果重选。
- 锁定门 `val_locked` FORMAL_READY 写入之后才打开。
- C0R 的启动条件是 C1 的**机械**完成，与 C1 结果无关。
- 本轮不跑 `['C4', 'C5', 'C0S']`：BLOCKED_SIMULATOR_LIBRARY_AND_FORMAL_SCENARIO_MANIFEST。
- smoke/pilot 结果不得写成正式结果。
