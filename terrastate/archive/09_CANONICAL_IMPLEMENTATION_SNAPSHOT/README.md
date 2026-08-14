# TerraState commit-exact 实现快照

这里保存论文真实训练与评估链路的最小依赖闭包。它与
`03_CODE_RELEASE/` 的简化、面向阅读的发布接口不同：本目录优先保证历史实现
可追溯和历史 checkpoint 可加载。

## 子目录

| 子目录 | 来源提交 | 角色 |
|---|---|---|
| `v2_training_commit_52578ca/` | `WorldModel2026-planb-v2train` `52578ca4...` | TerraState-V2 模型、future-state cache、三阶段训练与 smoke |
| `q2_validation_evaluator_commit_221052f/` | `WorldModel2026-planb` `221052f...` | validation Q1/Q2 冻结评估 |
| `q1_q2_ood_evaluator_commit_78073db/` | `WorldModel2026-planb` `78073db...` | OOD-t Q1/Q2 冻结评估 |
| `q3_evaluator_commit_4dce19a/` | `WorldModel2026-planb` `4dce19a...` | Q3 extreme-state/weather-response 评估 |
| `q3_protocol_builder_commit_83e62e9/` | `WorldModel2026-planb` `83e62e9...` | 极端天气协议和 donor manifest 构建 |
| `frozen_protocols/extreme_audit_oodt_v1/` | 原 PlanB 工程冻结 artifact | Q3 的 climatology、hot-dry、matched-normal 和阈值 |

每个 Python 文件均从对应 Git commit 直接提取；没有把当前分支的新实现伪装成
历史实现。为保持最小依赖闭包，未复制会通过 eager import 拉入无关旧模块的
部分 package `__init__.py`；Python namespace package 可正常导入具体模块。

## 已验证事项

- V2 模型、训练、cache 与 Q1/Q2 evaluator 导入通过；
- validation Q1/Q2 evaluator 导入通过；
- OOD-t Q1/Q2 evaluator 导入通过；
- Q3 evaluator 导入通过；
- 所有 83 个 commit-exact 文件通过来源提交的字节级 SHA 核对；
- 独立 CPU 三阶段训练 smoke 15/15 通过，包括缓存约束、未来信息隔离、
  阶段冻结、断点续训与等价全局 batch；
- 已恢复 boundary80 权重能严格加载到 V2 模型，missing=[]、
  unexpected=[]。

验证记录见 `COMMIT_EXACT_VALIDATION.txt`、`IMPORT_VALIDATION.txt`、
`V2_SMOKE_VALIDATION.txt` 和
`../07_WEIGHTS_AND_PROVENANCE/historical_boundary80_release/LOAD_VALIDATION.txt`。

## 运行前仍需外部输入

- GreenEarthNet train / val_chopped / ood-t_chopped 数据；
- future-state train/val cache（若重新训练）；
- Phase-I B4 teacher 和 exclusive MAIN student-init（若从头训练）；
- 对 14,880-step 最终模型做复验时，还需恢复对应 checkpoint 二进制。
