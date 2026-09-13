# Table 4A. 状态承载（Q2，历史 full vs 移除臂）

来源：`evaluations/candidate_c_q1q2q3_20260830T072737Z/{split}/state_contract_exclusive.json` 的 `Q2_load_bearing`。
移除臂：`alpha0`（去 T 贡献）、`T_identity`（转移换恒等）。指标为官方 LC-balanced。

| split | 臂 | R²_LC | RMSE_LC | biasabs |
|---|---|---:|---:|---:|
| iid | full | 0.5220 | 0.1555 | 0.0996 |
| iid | alpha0 | 0.4883 | 0.1708 | 0.1094 |
| iid | T_identity | 0.4877 | 0.2150 | 0.1639 |
| iid | **官方 ΔR²(full−alpha0)** | 0.0337 | | 门槛 0.005 → pass=True |
| iid | 配对 ΔR² (n=1487) | 0.0314 | 95% CI [0.0253, 0.0372] | win/loss=933/554 |
| ood_t | full | 0.5726 | 0.1509 | 0.1013 |
| ood_t | alpha0 | 0.5555 | 0.1627 | 0.1078 |
| ood_t | T_identity | 0.5549 | 0.2150 | 0.1704 |
| ood_t | **官方 ΔR²(full−alpha0)** | 0.0171 | | 门槛 0.005 → pass=True |
| ood_t | 配对 ΔR² (n=1019) | 0.0189 | 95% CI [0.0109, 0.0269] | win/loss=576/443 |
| ood_s | full | 0.4949 | 0.1621 | 0.1018 |
| ood_s | alpha0 | 0.4614 | 0.1755 | 0.1100 |
| ood_s | T_identity | 0.4605 | 0.2196 | 0.1653 |
| ood_s | **官方 ΔR²(full−alpha0)** | 0.0334 | | 门槛 0.005 → pass=True |
| ood_s | 配对 ΔR² (n=3496) | 0.0287 | 95% CI [0.0246, 0.0329] | win/loss=2077/1419 |
| ood_st | full | 0.5408 | 0.1542 | 0.1016 |
| ood_st | alpha0 | 0.5237 | 0.1650 | 0.1078 |
| ood_st | T_identity | 0.5232 | 0.2164 | 0.1699 |
| ood_st | **官方 ΔR²(full−alpha0)** | 0.0170 | | 门槛 0.005 → pass=True |
| ood_st | 配对 ΔR² (n=2188) | 0.0210 | 95% CI [0.0150, 0.0272] | win/loss=1242/946 |

> 点估计与 CI 均针对 **同一配对样本集合**（`closure_cut_alpha0.paired` / `bootstrap95`）。
> 移除臂退化表示该状态支路被实际使用，**不是**完整物理状态或因果反事实的证明。
