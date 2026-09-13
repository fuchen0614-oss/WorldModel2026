# Table 3. 训练机制比较（C0R vs C1，四卡正式配对）

本轮**不新增训练臂**。仅整理已有 C0R/C1 正式权重与其同协议结果。

## 3.1 配对身份（必须一致才是有效配对）

| 项 | C1 | C0R |
|---|---|---|
| arm / factual_path | C1 | C0R |
| 父权重 value_sha16 | aa98fbd2fa302727 | aa98fbd2fa302727 |
| 父权重文件 sha256 | a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f | a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f |
| 继承张量 / max_abs_diff | 255 / 0.0 | 255 / 0.0 |
| seed | 42 | 42 |
| world / accum / global batch | 4 / 2 / 64 | 4 / 2 / 64 |
| 训练步数 / 完成原因 | 14880 / schedule_complete | 14880 / schedule_complete |
| checkpoint sha256 | 474f94340763e9ba5b7373316ff4d09b69fa398d3fac2df291b9bf9846a93819 | 7051e04afc541100233b26af98cf63ae664a311e09076e4bcf0795fee98888a2 |
| 训练墙钟（4 卡，同机） | 21245 s | 20395 s |

> 两臂同 parent、同 seed(42)、同 world/accum/batch、同 14880 步、同为四卡正式运行 → 满足既有配对合同。
> **同更新次数不等于同计算量**；两者墙钟差异只作成本记录，不作效率结论。

## 3.2 标准预测（同协议 q1_full，同 manifest/掩码/评分器）

| split | 指标 | C1 seed42 | C0R seed42 | C0R−C1 | 来源 |
|---|---|---:|---:|---:|---|
| iid_chopped | R²_LC | 0.522020 | 0.525101 | +0.003082 | 本轮补测 C0R / E1 交付 C1 |
| iid_chopped | RMSE_LC | 0.155529 | 0.154695 | -0.000834 | 本轮补测 C0R / E1 交付 C1 |
| ood-t_chopped | R²_LC | 0.572600 | 0.576484 | +0.003883 | 本轮补测 C0R / E1 交付 C1 |
| ood-t_chopped | RMSE_LC | 0.150940 | 0.150667 | -0.000273 | 本轮补测 C0R / E1 交付 C1 |
| ood-st_chopped | R²_LC | 0.540760 | 0.545616 | +0.004856 | 本轮补测 C0R / E1 交付 C1 |
| ood-st_chopped | RMSE_LC | 0.154161 | 0.153792 | -0.000369 | 本轮补测 C0R / E1 交付 C1 |
| ood-s_chopped | R²_LC | 0.494875 | 0.497474 | +0.002599 | 本轮补测 C0R / E1 交付 C1 |
| ood-s_chopped | RMSE_LC | 0.162130 | 0.161620 | -0.000510 | 本轮补测 C0R / E1 交付 C1 |

> 已完成 4/4 个 split 的 C0R 标准预测（本轮补测）。缺失项留空，不用部分样本冒充全量。

### 3.2b 配对空间组 bootstrap（B=2000，seed=20260910）

统计量：**pooled RMSE 之差（C0R − C1）**；同一重采样同时作用于两臂（配对）。
点估计与 CI 针对**同一个估计对象**。仅使用**评测已写完**的 split。

**空间分组定义（已按代码核实）**：优先用记录 id 中的 Sentinel-2 tile 码；无 tile 时回退到
经纬度网格单元。主结果使用 **0.1° 回退网格**（即 v1 实际实现 `.round(1)`，与已报告数值一一对应）。
> v1 代码注释写的是「0.5°」，与实现的 `.round(1)` 不一致；**冻结合同（A14B）只要求 tile/预定地理组，
> 并未规定 0.5°**，故主结果保持原分组不变，另附 0.5° 分组作为敏感性对照（见下表之后）。

| split | 空间组数 | C1 pooled RMSE | C0R pooled RMSE | Δ(C0R−C1) | 95% CI | P(Δ<0) |
|---|---:|---:|---:|---:|---|---:|
| iid_chopped | 80 | 0.175621 | 0.174575 | -0.001046 | [-0.001441, -0.000684] | 1.0000 |
| ood-t_chopped | 77 | 0.171082 | 0.170671 | -0.000411 | [-0.001320, +0.000665] | 0.8005 |
| ood-st_chopped | 641 | 0.173006 | 0.172894 | -0.000111 | [-0.000459, +0.000266] | 0.7250 |
| ood-s_chopped | 748 | 0.187027 | 0.186513 | -0.000513 | [-0.000817, -0.000186] | 1.0000 |

**逐条点估计与 CI（不写“不劣于”，也不做未检验的非劣性判定）**：
- `iid_chopped`：Δ = -0.001046，95% CI [-0.001441, -0.000684]，P(Δ<0) = 1.0000 → CI 不含 0，方向上 C0R 的 pooled RMSE 更低。
- `ood-t_chopped`：Δ = -0.000411，95% CI [-0.001320, +0.000665]，P(Δ<0) = 0.8005 → **CI 跨 0：该 split 上不可判定方向**。
- `ood-st_chopped`：Δ = -0.000111，95% CI [-0.000459, +0.000266]，P(Δ<0) = 0.7250 → **CI 跨 0：该 split 上不可判定方向**。
- `ood-s_chopped`：Δ = -0.000513，95% CI [-0.000817, -0.000186]，P(Δ<0) = 1.0000 → CI 不含 0，方向上 C0R 的 pooled RMSE 更低。

> **术语纪律**：本表**不**声称 “C0R 不劣于 C1”。CI 跨 0 只表示该 split 上不可判定，
> **不等于**等价、也**不等于**已通过非劣性检验——本对照从未定义过非劣性边界，因此不做该判定。
> 统计量是 pooled RMSE 差（非官方 LC-balanced R²_LC），两者不可互换。

**敏感性：0.5° 回退网格（同一批已算好的评分，仅分组变粗）**

| split | 空间组数（0.5°） | 空间组数（主，0.1°） | Δ(C0R−C1) | 95% CI | 与主口径结论是否一致 |
|---|---:|---:|---:|---|---|
| iid_chopped | 80 | 80 | -0.001046 | [-0.001441, -0.000684] | 是 |
| ood-t_chopped | 77 | 77 | -0.000411 | [-0.001320, +0.000665] | 是 |
| ood-st_chopped | 399 | 641 | -0.000111 | [-0.000479, +0.000257] | 是 |
| ood-s_chopped | 454 | 748 | -0.000513 | [-0.000846, -0.000168] | 是 |

> 合同依据：`A14B only requires spatial tiles / predefined geographic groups; it does not mandate a 0.5-degree grid. The v1 comment saying 0.5 degrees was inconsistent with the implemented round(1). The primary result keeps the v1 grouping so that no previously reported number changes; the 0.5-degree run is reported alongside as a sensitivity check.`

## 3.3 分段稳定性（Q4 locked，val_dev 476 receivers / 40 空间组）

| 臂 | 九个 held-out 分段 composed/direct 比值范围 | 整体 verdict |
|---|---|---|
| C1 | 1.0005 – 1.0275 | PASS |
| C0R | 1.0709 – 1.3246 | FAIL |

> 1.05 是 **MSE 比值门**（不是 5% RMSE）。C1 全部在门内、C0R 全部超门，这是本对照的核心信号。
> C0R 的 FAIL 是真实评测结果，不是“未运行”。

## 3.4 本轮范围说明

- **FSR 不进入本表**：按最新决策，FSR 仅作为历史证据登记（见 `EVIDENCE_INVENTORY.csv`），本轮不新增分析、推理或图表。
- **不补新训练臂**：一致性正则、compute-matched、第二编码器、新 seed 均不在本轮范围。
- **不把状态移除推理实验当成重新训练消融**。

