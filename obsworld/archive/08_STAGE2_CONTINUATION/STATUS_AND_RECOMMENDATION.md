# Stage2 状态、可行性与续研建议

## 一句话判断

这套 Stage2 **工程上可运行、概念上可延续、实验上尚未成功闭环**。最合理的
用途是作为 Stage1.5 表征进入天气驱动预测状态模型的可修改起点，而不是直接
复用其历史论文结论。

## 代码身份

- 仓库：`WorldModel2026`
- 分支：`plan-a-vits`
- commit：`541dd76`
- 代码主题：A′/metric-aligned Stage2，包含 `q → T → O`、
  physical4 驱动、直接 NDVI head、Q2 load-bearing、Q3 driver sensitivity
  和 Q4 composition evaluator。
- 快照规模：70 个 commit-exact 文件，其中 60 个 Python 文件。

## 为什么说“可行”

- 与 Stage2 核心模型、训练合同和 evaluator 相关的测试 32/32 通过。
- `smoke_plan_a_prime.py` 的 13/13 项通过，包括：
  - NDVI 输出和有限损失；
  - q/T/O 均能获得梯度；
  - DDP 下无未使用的可训练参数；
  - 未来卫星观测不会泄漏进初始状态；
  - 天气变化能传递到状态和输出；
  - 预测确实依赖推进后的状态；
  - checkpoint round-trip；
  - optimizer 中 q 与 T/O 使用预期学习率；
  - vegetation/SCL/clear mask 合同。
- 配置继承链和主要依赖已经闭合，可从本目录独立导入和测试。

## 为什么不能叫“已经成功”

历史 A′ 全量结果已在 85 号审计中冻结：

| 路线 | OOD-t R² | RMSE |
|---|---:|---:|
| A2 epoch100（A′ 历史最好 R²） | 0.55452 | 0.16877 |
| B4（后续路线参照） | 0.58252 | 0.14342 |

因此，A′ 当时没有达到内部工程门槛。`plan_a_metric_v1.yaml` 是在上述结果后新增
的 metric-aligned 修复代码；当前只有静态、单元测试和 smoke 证据，没有完整
训练结果。后续工作必须重新验证精度，不能把“代码通过”写成“方法有效”。

## 三个初始化入口

1. `plan_a_prime_from_s15.yaml`
   - 从 Stage1.5 checkpoint 新建 Stage2；
   - 概念链最干净；
   - 当前归档缺少 Stage1.5 权重。
2. `plan_a_prime_from_s1a_stage2.yaml`
   - 从历史 S1a Stage2 checkpoint 做 weights-only warm start；
   - 不恢复旧 optimizer/scheduler；
   - 当前归档没有该远程权重。
3. `plan_a_metric_v1.yaml`（未来实验优先）
   - 默认继承 fresh Stage1.5 路径的结构，但实际设计为用
     `INIT_FROM_CHECKPOINT` 注入 A2-best 完整模型；
   - 对齐 land-cover macro NDVI、时间 bias/CCC、EMA、全 horizon 监督和
     validation selection；
   - 若恢复不到 A2-best，不能假装从该路径继续。

## 已归档的两个可加载历史起点

`03_KEY_WEIGHTS/` 现已加入两条更早正式训练线的 validation-best checkpoint：

| 起点 | step | OOD-t R² | RMSE | 用途 |
|---|---:|---:|---:|---|
| Direct physical4 | 8000 | 0.52430 | 0.17776 | 直接多时域预测的历史基线与 warm start 候选 |
| Rollout physical4 | 8000 | 0.50388 | 0.18390 | 递推/共享动力学的历史基线与 warm start 候选 |

两者都已严格 CPU 加载通过，并内含 serialized config 和完整训练状态。它们不能
替代 Stage1.5 或 A2-best，也不代表 `plan_a_metric_v1` 已完成训练；但在远程
Stage1.5/A2-best 尚未恢复时，它们避免了 Stage2 续研只能从随机初始化开始。

## 建议的续研顺序

1. 最优选择仍是恢复 Stage1.5 或 A2-best 权重并记录 SHA；若短期无法恢复，
   只可明确标注地使用 `03_KEY_WEIGHTS/` 的 Direct/rollout best 做历史 warm start。
2. 在本快照上运行 13/13 synthetic smoke。
3. 使用冻结 train/validation manifest 和仅由训练集计算的 physical4 stats。
4. 先在 validation 上跑 `plan_a_metric_v1`，只比较预先冻结的指标。
5. 只有 validation 过门后才冻结唯一 checkpoint，再做一次 OOD-t。
6. Q2/Q3 可作为世界模型证据；Q4 仍是扩展诊断，不应先写成既定贡献。

## 禁止事项

- 不根据 OOD-t 反复调 loss、权重或 checkpoint。
- 不把 32/32 测试或 13/13 smoke 当成精度结果。
- 不把旧 Stage2 权重、B4/TerraState 权重冒充 Stage1.5/A2 初始化。
- 不重新宣称历史 A′ 已达到 B4 精度。
- 不让任何精度旁路绕过 `z_h`，否则 `q → T → O` 的世界模型合同失效。
