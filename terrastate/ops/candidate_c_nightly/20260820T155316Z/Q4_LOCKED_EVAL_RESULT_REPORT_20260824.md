# Candidate C · 一次性 Q4 锁定集结果报告

- 结果状态：**`Q4_LOCKED_COMPLETE_QUALIFIED_FAIL_NO_RERUN`**
- 完成时间（UTC）：`2026-08-24T11:46:01Z`
- 本报告范围：固定 4 卡 C1/C0R 内部配对的唯一一次 `val_locked` Q4；不是 8 卡副本结果，
  也不是 C2/C3/C0S/C4/C5 或 simulator 校准结果。

## 1. 不可回退的执行记录

| 项 | 值 |
|---|---|
| 输入选择收据 | `Q4_LOCKED_EVAL_AUDIT_AND_SELECTION_RECEIPT_20260824.md`（本报告不回改该收据） |
| 输出根目录 | `results/q4_eval_locked_4gpu_20260824T101119Z/` |
| 运行时间（UTC） | start `2026-08-24T10:11:20Z`；finished `2026-08-24T11:46:01Z` |
| 执行资源 | CPU-only：`CUDA_VISIBLE_DEVICES=""`、`nice -n 10`、OMP/MKL 各 2 线程；未占用 GPU/H200 |
| controller 结果 | C1 rc=0，C0R rc=1，compare rc=1，`missing_artifacts=0` |
| rc 解释 | score/compare 的 rc=0 或 1 均为有效科学 verdict；本次两个 rc=1 表示门 FAIL，不是基础设施故障 |
| split | `validation_subsplit.val_locked.ids`，`allow_locked=true`，476/476 cubes、40 tiles |

### 固定权重身份

| 臂 | 路径 | step / strict | checkpoint SHA-256 | loaded / checkpoint value SHA16 |
|---|---|---|---|---|
| C1 | recursive | 14,880 / true | `474f94340763e9ba5b7373316ff4d09b69fa398d3fac2df291b9bf9846a93819` | `a87f972b8a093b61` / `a87f972b8a093b61` |
| C0R | direct | 14,880 / true | `7051e04afc541100233b26af98cf63ae664a311e09076e4bcf0795fee98888a2` | `29c4baf88b6ebf5d` / `29c4baf88b6ebf5d` |

两臂均来自 `terrastate/v2/verified-resume14880@v1` 的 weights-only Phase-II fork，seed=42、
global batch=64、14,880 updates、`λ_z=λ_y=λ_pair=λ_nc=0`。两臂内部匹配，但实际启动是
4×8×accum2、checkpoint interval=1000、直接 `torchrun`；它不同于早期冻结的
8×8×accum1、interval=372 设想。因此本结果只能称为 **qualified locked evidence**。

## 2. 产物与完整性核验

检查通过：`execution_status.json`、两臂各自的 aggregate/provenance/per-cube JSON/NPZ、以及
compare JSON/provenance 均存在；aggregate 与 compare 的 provenance SHA 相符，per-cube JSON/NPZ
均与 aggregate 中记录的 SHA 相符；两臂的 7 项 evaluator/model/data source SHA 一致。

| 工件 | SHA-256 |
|---|---|
| `execution_status.json` | `8da0430613af01f10fbf374ce29d48e15ad48ab74c1e60ba0d29facfff4566db` |
| `c1_score/q4_aggregate.json` | `bd46e809238c2531e0817092dc982935e04e7f2045639ea1d7809d75fec597a7` |
| `c1_score/provenance.json` | `a7312d2512266cbd515d5692cffe576ac9f2896c8ff47a76857479fe5b6fbb5e` |
| `c0r_score/q4_aggregate.json` | `29a512c1503588859e303bfb44f24aa3b43544c707b185c91c94f776e218fccc` |
| `c0r_score/provenance.json` | `d28e310769039d2262d012d9cc33bfb14ee6fdad9a60632f94ccdccef98dc704` |
| `compare/q4_compare.json` | `ca132c1b73a376005e1b7c27bfe357b053baa0abf5d66aa5d655b336564ab129` |
| `compare/provenance.json` | `06dbc9bdcc575e2651a71329e4c11993c39a52329b7407e6255b41160ddc2987` |

## 3. Q4 结果

### 3.1 单臂四门

| 臂 | broken-control | composed-vs-direct | state-retention | semigroup bit-exact | verdict |
|---|---:|---:|---:|---:|---:|
| C1 recursive | PASS | PASS | PASS | PASS | **PASS** |
| C0R direct | PASS | FAIL | FAIL | PASS | **FAIL** |

C1 的 broken-control `A_comp=0.01287`，95% CI `[0.01195, 0.01380]`，73 个 control pairs 中
66 个 ratio<1。其 Panel-B（仅报告、不是门）的 h=10/15/20 状态标准差保留为
`1.0109 / 1.0130 / 1.0148`，有效秩保留为 `0.9777 / 0.9806 / 0.9828`，预注册的
`ep20|10-10` noncollapse 检查 PASS。

### 3.2 臂间事实端点门 G_abs

G_abs 使用 tile geo-clustered bootstrap（B=2,000）；每个组合须同时满足
`LCB(ΔR²) ≥ -0.02` 与 `UCB(RMSE_C1/RMSE_C0R) ≤ 1.05`。合同要求全部 direct 与全部
composed 组合通过。本次：

- direct：**1/3** 通过；
- composed：**3/16** 通过；
- 总计：**4/19**，`direct_all_pass=false`，`composed_all_pass=false`，**verdict=FAIL**。

| endpoint | C1 direct RMSE / R² | C1 最差分段退化 | C0R direct RMSE / R² | C0R 最差分段退化 | G_abs 通过数 |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.1377 / 0.630 | 0.8% | 0.1369 / 0.634 | 9.2% | 2/6 |
| 15 | 0.1596 / 0.493 | 1.0% | 0.1600 / 0.491 | 9.1% | 0/5 |
| 20 | 0.1617 / 0.531 | 1.2% | 0.1628 / 0.525 | 14.7% | 2/8 |

### 3.3 必须同时报告的资格敏感性

主口径是 `n_valid≥64`（逐 cube 有效像素数）。它非预注册、会改变结论，且约排除 44.7%
`(cube, combo)` 对。不得只报告有利口径：

| 资格口径 | 臂间通过数 |
|---|---:|
| none（仅 `sst>0`） | 1/19 |
| std-v1（`std≥1e-2`） | 5/19 |
| 主口径 `n_valid≥64` | 4/19 |

三种口径均不满足 G_abs 总门，因此没有选择某个口径来制造成功结论。

## 4. 可支持与不可支持的结论

**可支持（带上述 qualified 限定）**：在固定 4 卡内部配对和锁定 split 上，recursive C1 单臂通过
四道 Q4 门，而 direct C0R 的 composition / retention 门失败；C1 的最差分段退化为 0.8%–1.2%，
小于 C0R 的 9.1%–14.7%，显示出更强的分段稳定性信号。

**不可支持**：

- “Q4 整体 PASS”或“C1 在事实端点不劣于 C0R”；
- “可组合预测状态已经被完整证明”；
- 严格 8 卡冻结合同复现、8 卡副本结论、multi-seed 稳健性；
- C2/C3 损失有效、C0S/C4/C5/simulator 校准、因果反事实或 SOTA。

## 5. 封存与后续边界

本次锁定集已经完成，之后**不得**再对 `val_locked` 执行 score/compare、换 checkpoint/pair、改
`n_valid`/bootstrap，或因本结果启动重跑。若下一阶段考虑 C2/C3，必须先写出新的开发集驱动、
可复现的诊断与 λ 选择协议；该协议不得以此处任何 locked 指标作为调参依据。C0S/C4/C5 仍在正式
simulator 数据、EO↔simulator mapping 与 scenario manifest 可用前保持阻塞。
