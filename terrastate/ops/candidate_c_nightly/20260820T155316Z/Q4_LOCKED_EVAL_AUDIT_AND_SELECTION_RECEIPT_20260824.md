# Candidate C · Q4 锁定集审计与一次性输入选择收据

- 写入时间（UTC）：2026-08-24T10:03:55Z
- 适用 attempt：`ops/candidate_c_nightly/20260820T155316Z/`
- 代码 HEAD：`e42b0722cc83f279cc99d5d05144d5a47491d79e`
- 决定状态：**`ACCEPTED_FOR_ONE_QUALIFIED_LOCKED_EVALUATION`**

## 1. 这份收据解决什么、不解决什么

用户已授权本轮继续完成后续审计与一次性锁定集评测。本收据把那一次评测的输入、
统计口径和输出纪律固定下来，防止在看到锁定结果后重跑、换 pair、换 checkpoint 或改资格线。

它**不是**对早期 8 卡冻结启动合同的追溯性重写，也不把当前 4 卡输出伪称为字节级的
严格预注册复现。它只允许对已经在 `val_dev` 上作为一个内部匹配对评估过的同一 4 卡
C1/C0R pair，做一次带明确限定语的锁定集确认。后续任何论文本体都必须同时披露本节的
偏离与 `val_dev` 的后验资格选择。

`val_locked` 的数据样本、标签、模型预测和指标在本收据写入前均未被评测器读取；为冻结
split 做完整性核验时读取过 manifest 的 ID/数量/互斥性元数据，这不构成对锁定样本的
model forward 或结果访问。

## 2. 审计结论

### 2.1 已通过的 CPU 证据

在冻结解释器
`/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python` 下，设
`CUDA_VISIBLE_DEVICES=""` 后顺序运行：

| 套件 | 通过 / 总数 | 核心覆盖 |
|---|---:|---|
| `test_candidate_c_contract.py` | 51 / 51 | 父权重严格装载、未来信息隔离、递归路径、坏对照、非坍缩、simulator fail-closed |
| `test_candidate_c_resume.py` | 59 / 59 | 原子写、phase 内 exact resume、严格 checkpoint、Q4 产物/provenance、冻结 split 互斥 |
| `test_candidate_c_ddp_cpu.py` | 9 / 9 | 2-rank 同步、rank0 唯一写盘、DDP resume、协作停止 |
| `test_q4_paths_and_floor.py` | 6 / 6 | `n_valid≥64`、敏感性口径、tile bootstrap |
| `test_q4_percube_eligibility.py` | 6 / 6 | 逐 cube mask、长度契约、pooled 同集计算 |
| **合计** | **131 / 131** | CPU 回归通过 |

冻结 design/selection/queue 合同和两份 EO/Q4 manifest 的 SHA-256 sidecar 现场复核均通过。
真实 4 卡 checkpoint 的文件 SHA-256 也已重新计算，和 `val_dev` provenance 一致。
同一冻结解释器还对两个真实 checkpoint 执行了 evaluator 的 `load_state_dict(strict=True)`：
C1 / C0R 均严格加载成功、均为 step 14,880，且 loaded value SHA16 分别为
`a87f972b8a093b61` / `29c4baf88b6ebf5d`。最新 `val_dev` provenance 所钉住的 7 个
evaluator/model/data source SHA 亦为 7/7 匹配当前工作树。

### 2.2 独立完整性审计

只读审计确认：Q4 target 来自真实 EO validation 数据；当前 `val_dev` 结果 JSON、逐 cube
数组和 provenance 相互一致；没有发现伪造真值、按模型输出归一化或凭空结果。审计同时给出
三个必须保留的 WARN：

1. 主资格 `n_valid≥64` 非预注册、改变了开发集结论，并排除约 44.7% 的 `(cube, combo)`；
2. 现有 `val_dev` 不是 `val_locked`，因此不能作为最终主张；
3. 4 卡 pair 与早期 8 卡启动合同存在偏离，不能和 8 卡副本混合，不能称为严格配置复现。

## 3. 选择的唯一输入 pair

锁定集只允许使用下列同一对 4 卡输出。理由不是它们的数值更有利，而是它们是此前完整
`val_dev` Q4 所使用的唯一内部配对；为了测试开发信号是否能外推，锁定评测必须固定在同一对，
而不是在结果之后换成未做同协议 `val_dev` Q4 的 8 卡副本。

| 项 | C1（candidate） | C0R（control） |
|---|---|---|
| run | `run_c1_20260822T131006Z` | `run_c0r_20260823T063516Z` |
| 路径 | recursive | direct |
| checkpoint | `checkpoint_main.pt` | `checkpoint_main.pt` |
| checkpoint SHA-256 | `474f94340763e9ba5b7373316ff4d09b69fa398d3fac2df291b9bf9846a93819` | `7051e04afc541100233b26af98cf63ae664a311e09076e4bcf0795fee98888a2` |
| step / phase_step | 14,880 / 14,880 | 14,880 / 14,880 |
| loaded value SHA16 | `a87f972b8a093b61` | `29c4baf88b6ebf5d` |
| parent | `terrastate/v2/verified-resume14880@v1` / `a5d2…e94f` | 同左 |
| seed / global batch / λ | 42 / 64 / z=y=pair=nc=0 | 同左 |
| 实际 world × per-GPU × accum | 4 × 8 × 2 | 4 × 8 × 2 |

8 卡 C1/C0R 是独立副本，**不进入本次锁定 gate**；本收据不解释它们的效果，也不允许与上表
混合比较。

## 4. 已登记的合同偏离与结论边界

| 维度 | 早期冻结启动合同 | 本次 locked 输入 pair | 处置 |
|---|---|---|---|
| 并行 | 8 × 8 × accum1 | 4 × 8 × accum2 | global batch 仍为 64；仅作内部匹配证据 |
| checkpoint/validation interval | 372 | 1000 | 已登记，不能称严格复现 |
| 启动与看护 | launcher、空闲门、launch record | 直接 `torchrun`，缺上述收据 | 启动 provenance 弱，结果不包装为强流程证据 |
| trainer source receipt | 冻结时绑定 | 后续 milestone tagging 使旧测试源码哈希失效 | 本收据以当前 131/131 CPU 回归补充，不倒签历史收据 |

所以，无论锁定结果是什么：

- 可以报告“这个 4 卡、内部匹配的 C1/C0R pair 在 `val_locked` 的结果”；
- 不可以写“8 卡副本已确认”“严格预注册配置完全复现”；
- 不可以因 C1 单臂门通过就写“Q4 overall PASS”或“事实预测不劣于 C0R”；
- 不能把 C1/C0R 当作 C2/C3、C0S、C4/C5 或 simulator 校准的证据。

## 5. 固定的 split、统计与执行纪律

| 项 | 固定值 |
|---|---|
| split selector | `validation_subsplit.val_locked.ids` |
| split | 476 cubes / 40 tiles；与 `val_dev` 互斥 |
| EO split manifest SHA-256 | `160c3ccc5075d386ecdc235a61806610d8475cc46f17973b94a5a9a37ed3cd6b` |
| Q4 partition manifest SHA-256 | `d0a4c6564516ea62f7eda9ebc4018433d1357391ad3a2a3bd8070de1a54e1e0e` |
| 单臂 Q4 门 | paired-minicube bootstrap，B=10,000 |
| 臂间 G_abs | tile geo-clustered bootstrap，B=2,000；LCB ΔR² ≥ -0.02 且 UCB RMSE ratio ≤ 1.05 |
| 主资格 | `n_valid≥64`；必须一并保留 none / std-v1 敏感性 |
| 执行设备 | CPU，`CUDA_VISIBLE_DEVICES=""`；不占任何 H200 |

每个 score 与 compare 步骤的退出码 `0` 或 `1` 都可能是正常科学 verdict；只要四类结果产物完整且
SHA 自洽，`1` 必须记录为 FAIL 而不是当作运行错误。`rc>1`、缺产物、strict load 失败或 provenance
不一致时立即停止，**不得自动重跑 locked**。

输出必须写入此前不存在的唯一目录 `results/q4_eval_locked_4gpu_<UTC>/`；不得使用
`scripts/run_q4_eval.sh`（它硬编码 `val_dev` 且 `set -e` 会把正常 FAIL 当作中止）。

## 6. 不可回退规则

1. 这次锁定评测开始后，不能再执行第二次 `val_locked` score/compare；
2. 不得据此改 `MIN_VALID_PIXELS`、bootstrap、checkpoint、arm、pair 或 source code；
3. 结果出现 FAIL 时，保留全部输出和日志，更新 A04/A05 后停止对锁定集的访问；
4. 后续 C2/C3 是否开展，只能依据本次结果和明确的新计划决定；C0S/C4/C5 仍因 simulator 数据缺失而阻塞。
