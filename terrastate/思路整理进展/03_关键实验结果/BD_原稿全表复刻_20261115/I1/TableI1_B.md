| Training scheme | Parameters | Devices × batch/device × accumulation | Global batch | Updates | Wall-hours | Allocated GPU-hours |
|---|---:|---|---:|---:|---:|---:|
| SpanWorld partitioned-path learning | 7181920 | 4 × 8 × 1 | 32 | 74,500 | 16.128 | 64.511 |
| Direct-endpoint supervision control | 7181920 | 多次切换；末段4 × 4 × 2 | 32 | 74,500 | 待核跨续训总量 | 待核跨续训总量 |

B-C0R已核实最终74500步完成；末次summary仅2.804小时，且此前有两卡/四卡迁移，不能直接乘4冒充全部训练成本。