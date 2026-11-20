| Training scheme | Parameters | Devices × batch/device × accumulation | Global batch | Updates | Wall-hours | Allocated GPU-hours |
|---|---:|---|---:|---:|---:|---:|
| SpanWorld partitioned-path learning | 7313504 | 4 × 4 × 2 → 4 × 8 × 1 | 32 | 74,500 | 待核跨续训总量 | 待核跨续训总量 |
| Direct-endpoint supervision control | 7313504 | 4 × 8 × 1 | 32 | 74,500 | 15.186 | 60.744 |

D-C1目前确认step27,565→74,500续训段7.347小时、29.389 GPU-hours；前27,565步耗时尚未闭环，不能将这一段当全部100轮成本。