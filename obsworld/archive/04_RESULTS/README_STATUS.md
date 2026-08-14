# 结果文档状态

| 文件类型 | 状态 | 用途 |
|---|---|---|
| `STAGE1_DELIVERY_REPORT.md` | Stage 1 交付事实 | 理解最初训练框架与 FSDP checkpoint 形式 |
| `STAGE1.5_IMPLEMENTATION_AUDIT.md` / `STAGE1.5_AUDIT_SUMMARY.md` | 训练前实现审计 | 核对设计是否落到代码；不能当成训练结果 |
| `Stage1.5_30k_Phi_Leakage_Probe_结果分析.md` | 30k 结果 | 理解第一轮 nonlinear leakage 失败 |
| `28_Stage1.5_30k完整验证记录.md` | 30k 详细结果 | 复盘 probe 与指标 |
| `29_Stage1.5_30k_vs_60k_Phi泄漏对比.md` | 最终比较 | 当前 Stage 1.5 结果结论的首选来源 |
| `STAGE1_vs_STAGE1.5_STEP_EPOCH_VERIFICATION.md` | 训练口径核对 | 防止把 dual-mode `/2` 错误带入 Stage 1.5 |

不要把“实现审计通过”误写成“非线性解耦实验通过”。

