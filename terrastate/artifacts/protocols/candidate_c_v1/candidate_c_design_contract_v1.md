# Candidate C 设计合同 v1（冻结）

- 冻结时间(UTC): `2026-08-21T09:07:59.975870Z`　主机: `csy-zg01-gnode39`
- 架构: `TerraStateCandidateC`　route: `candidate_c_v1`
- 张量数: **255**　不新增参数: **True**

## 1. 父权重与 fork 语义

- alias: `terrastate/v2/default-training-anchor`
- logical id: `terrastate/v2/verified-resume14880@v1`
- object: `/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/a5/a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f.pt`
- file sha256: `a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f`
- value_sha16: `aa98fbd2fa302727`　张量数 255　父 step 14880

**Candidate C 必须是 weights-only Phase-II fork：新 optimizer、新 scheduler、新 RNG、phase step 从 0 开始；绝不加载父权重那次 14,880-update 训练留下的旧 optimizer/scheduler，也绝不称为 exact resume。（两个臂自身的预算同样是 14,880 update，与父权重同构，但那是一条从 0 重新开始的新 schedule。）**

| 项 | 值 |
|---|---|
| `kind` | `weights_only_phase_II_fork` |
| `is_exact_resume_of_parent` | `False` |
| `loads_parent_weights` | `True` |
| `loads_parent_optimizer` | `False` |
| `loads_parent_scheduler` | `False` |
| `loads_parent_rng` | `False` |
| `phase_step_starts_at` | `0` |

## 2. 数据与划分

- train: `/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/train`　**23816** cubes　ids sha256 `17c645d92e9dd4c38ce5bf14a412115c5f6622109cff3c19118b098e604b2554`
- val: `/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet/val_chopped`　**952** cubes　ids sha256 `555d44c0d59ab3902cf7d929ca86ce8bf4e3ce7cfda66c1c72b45a2ed3fd76c9`
- val_dev **476**（40 tiles）／val_locked **476**（40 tiles）
- 无 geo group 跨 split: **True**
- split manifest sha256 `160c3ccc5075d386ecdc235a61806610d8475cc46f17973b94a5a9a37ed3cd6b`
- q4 partition manifest sha256 `d0a4c6564516ea62f7eda9ebc4018433d1357391ad3a2a3bd8070de1a54e1e0e`

## 3. 预算（预注册）

- 23816 train cubes // global_batch 64 = 372 updates/epoch x 40 epochs = 14880 updates
- world 8 × per-GPU 8 × accum 1 = global 64
- ckpt/val interval 372　主 checkpoint 在第 **14880** 个 update
- lr warmup **300** step（linear warmup + cosine decay，总长 14880）
- 与父权重对齐: 预算与父权重 TerraState v2 的真实 schedule 严格对齐：40 epoch / 14880 update / warmup 300。原记录的 8 epoch / 2,976 update / warmup 100 已确认为事实错误并作废；11,904 仅是父 schedule 中 epoch-32 的中途 checkpoint，不是独立预算。
- OOM 回退: 若 per-GPU 8 触发 OOM：改用 per-GPU 4 + accum 2（global batch 仍为 64），并且必须对两个臂同时冻结同一设置，再重跑 resume/parity 测试后才能进入正式 run。

## 4. 损失

```
L = L_EO + lambda_z*L_cmp_z + lambda_y*L_cmp_y + lambda_pair*L_pair + lambda_nc*L_noncollapse
```

- 正式臂四个 λ 全为 0：`{'lambda_z': 0.0, 'lambda_y': 0.0, 'lambda_pair': 0.0, 'lambda_nc': 0.0}`
- smoke-only λ：`{'lambda_z': 0.1, 'lambda_y': 1.0, 'lambda_pair': 0.0, 'lambda_nc': 0.01}`（需 `--allow-nonzero-lambdas`）
- 本轮正式臂只检验 recursive vs direct 的 EO 拟合差异，四个辅助项全部关闭，避免把辅助项调参混进主结论；smoke 才开非零λ，仅用于验证这些项能算、能回传、不产生 NaN。

## 5. 两个臂

| arm | factual_path | seed | 角色 |
|---|---|---|---|
| `C0R` | `direct` | 42 | 同预算 direct Phase-II 对照臂 |
| `C1` | `recursive` | 42 | recursive-only 正式臂 |

- **C0R 不是 C0S。C0S 专指未来与 C4/C5 匹配 simulator 监督量的控制臂，本轮不得伪造。**

## 6. 选择合同（结果不可见时即已钉死）

- 主调参 split: `val_dev`（selector `validation_subsplit.val_dev.ids`）
- 锁定门: `val_locked`，FORMAL_READY 写入之后才打开
- 禁用: `['ood_t', 'test']` —— 禁止用于调参或 checkpoint 选择
- CI: 0.95 minicube 级 geo-clustered bootstrap，2000 次重采样
- 同一 tile 内的 minicube 高度相关，按 minicube 独立重采样会把置信区间做得虚假地窄；按 geo group 聚类重采样才诚实。

| 门 | 统计量 | 判据 |
|---|---|---|
| `LCB_delta_r2` | LCB(ΔR²) = LCB(R²_C1 - R²_C0R) | `>= -0.02` |
| `UCB_rmse_ratio` | UCB(RMSE_C1 / RMSE_C0R) | `<= 1.05` |

- 评估于 `val_locked`，两门都必须通过: **True**
- 两个臂的主 checkpoint 都预注册在第 14,880 个 update；不得在看到 loss/指标后改选别的 checkpoint；中途 checkpoint 仅用于故障恢复与诊断，不进入主结论。

## 7. Simulator 状态：本轮不跑 C4/C5

- 状态: `BLOCKED_SIMULATOR_LIBRARY_AND_FORMAL_SCENARIO_MANIFEST`
- 原因: 仓库和环境中没有正式 WOFOST/PCSE/SCOPE simulator 情景库、EO<->simulator mapping 或 scenario manifest。不得用 Q3 donor、随机合成数据或伪造轨迹冒充 paired simulator truth。
- 本轮最多允许: `['C1', 'C0R']`
- 队列中明确排除: `['C4', 'C5', 'C0S']`

## 8. CPU 验收测试（GPU 前置硬门）

| 套件 | verdict | checks | pass | fail |
|---|---|---|---|---|
| contract | `PASS` | 51 | 51 | 0 |
| resume | `PASS` | 59 | 59 | 0 |
| ddp | `PASS` | 9 | 9 | 0 |

- 合计 pass **119**，fail **0**，全绿 **True**

## 9. 禁止项

- 不得把 smoke/pilot 结果写成正式结果
- 不得基于 C1 结果决定是否运行预注册的 C0R
- 不得用 val_locked / OOD / test 做调参或 checkpoint 选择
- 不得把临时 Stage1.5 checkpoint 注册为 TerraState 权重
- 正式 run 不得使用 --allow-unverified-parent / --allow-nonzero-lambdas
