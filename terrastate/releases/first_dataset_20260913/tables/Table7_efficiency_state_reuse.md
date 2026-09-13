# Table 7. 效率与状态复用成本

仅使用**可核实的历史记录**与**本轮新增的 C1 运行时测量**；受资源争抢影响的数值一律标注条件。

## 7.1 参数量与训练成本（历史记录，4 卡正式运行）

| 项 | C1 | C0R |
|---|---|---|
| 参数量 | 7.1809 M | 7.1809 M |
| 训练步数 | 14880 / 14880 | 14880 / 14880 |
| 训练墙钟（同机 csy-zg01-gnode39，4 卡） | 21245 s = 5.90 h | 20395 s = 5.67 h |
| 训练转移调用（端点分支/step，按代码解析） | 期望 8.005（6–10 波动） | 恒 3 |

> 两臂在同一台机器、同为 4 卡。墙钟差异只作成本记录；**同更新次数不等于同 FLOPs**。

## 7.2 推理时延与显存（同机同条件，历史测量，来源见来源列）

| 臂 | 参数 M | 完整预测中位 ms | 峰值显存 MiB | 每查询 transition 调用 |
|---|---:|---:|---:|---:|
| C0R | 7.1809 | 48.38 | 1107.7 | 4.0 |
| C1 | 7.1809 | 48.19 | 1119.0 | 4.0 |

> 来源：`fixedstep_r_20260910T110000Z/eval/efficiency.json`（同一会话中另测了一个第三臂，本轮不报告）。
> 该测量在 dilab 上、检测到外部占卡时进行；仅作**受限测量**，不据此声称谁更快。

## 7.3 运行时状态测量（本轮重做，C1 seed42）

- 设备：`NVIDIA A100-SXM4-40GB`（`cuda:0`）；协议：`eval()` + **`inference_mode`**（推理专用，无梯度），batch 1，fp32。
- 计时：每段前后 `torch.cuda.synchronize()`；预热 10 (cheap phases) / 3-5 (end-to-end phases), discarded（丢弃），正式 10-30 depending on cost; median reported，取**中位数**。
- 查询：**4 条完全相同的查询**——all four queries use the SAME fixed real future-weather segment, so the only difference between the two paths is whether the history and the shared prefix are recomputed。
- 测量时的其他计算进程：`3` 个（共享节点，受限测量）。
- 检查点：`/data/zs/WorldModel2026/terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt`（seed 42）

| 项 | 实测 |
|---|---:|
| 完整预测（20 步，1 样本）中位 | 31.91 ms |
| 状态张量字节（z+prior+geo） | 2,621,440 B = 2.50 MiB |
| 状态序列化文件 | 2,623,985 B = 2.50 MiB |
| 保存状态中位 | 22.99 ms |
| 恢复状态中位 | 34.10 ms |

### 7.3a 分支计算成本（**纯计算**，不含适配器的哈希校验）

| 分支数 B | 计算耗时中位 ms | B=1 起的每分支增量 ms |
|---|---:|---:|
| 1 | 0.41 | nan |
| 2 | 0.74 | 0.32 |
| 4 | 1.38 | 0.32 |
| 8 | 2.64 | 0.32 |

> 本节是**分支与解码的纯计算成本**（直接调用模型内部函数，不经运行时适配器），**不能**与 v1 表的分支成本直接比较：
> v1 的分支成本是经适配器测得的，而适配器的每一次 `advance()` / `decode()` 都附带一次**全量 state-dict 哈希校验**（见 7.3b 的 `model_hash` 一行）。
> 因此 v1 的 69 / 139 / 278 / 556 ms 主要是**校验开销**，不是分支本身的计算成本；本表按纯计算重新测量。


### 7.3b 分阶段成本（**逐阶段单独测量，不合并成一个倍率**）

阶段定义（与运行时适配器的函数一一对应）：
`history_encoding` = `initialize()`（把 10 个五日步历史编码成状态）；
`shared_prefix` = `advance(..., 10)`（推进到中间时刻，**四个查询共用**）；
`suffix_per_branch` = `branch()` + `advance(..., 20)` + `decode()`（**每个分支各算一次**）；
`model_hash` = `model_state_hash()`（身份校验）；`save` / `restore` = `save_state()` / `load_state()`。

| 阶段 | 中位 ms | 说明 |
|---|---:|---|
| history_encoding | 29.47 | 每次 initialize 一次 |
| shared_prefix | 0.39 | 共享，只算一次 |
| suffix_per_branch | 0.41 | 每分支一次 |
| model_hash | 33.35 | 身份校验 |
| save | 22.99 | 序列化到磁盘 |
| restore (GPU) | 34.66 | 同设备 |
| restore (CPU→CPU) | 34.10 | CPU map_location |
| load→GPU 传输 | 0.93 | 若状态存在 CPU 需先搬上卡 |

**正确的命名**：所谓“复用”是 **历史及共享前缀只计算一次**（`history_encoding + shared_prefix`，
在 B 个查询间摊销）；所谓“重编码”是 **每个分支都重新计算历史及前缀**
（`B × (history_encoding + shared_prefix)`）。两者在 `suffix_per_branch` 上**完全相同**。

成本模型（B = 查询数）：

```
reuse(B)    = history_encoding + shared_prefix + B * suffix_per_branch
reencode(B) = B * (history_encoding + shared_prefix + suffix_per_branch)
ratio(B)    = reencode(B) / reuse(B)
```

| B | 模型：reuse ms | 模型：reencode ms | 模型比值 |
|---|---:|---:|---:|
| 1 | 30.27 | 30.27 | 1.00× |
| 2 | 30.68 | 60.55 | 1.97× |
| 4 | 31.51 | 121.09 | 3.84× |
| 8 | 33.15 | 242.18 | 7.30× |

> **倍率随 B 变化，因此本轮不把任何单一倍率当作结论**；v1 报告的 1.80× 是B=4 时的取值，且其“复用”路径内**仍含一次 `initialize()`**，属于**该实现的实测点**，不构成通用加速比。本表以阶段成本与公式为准。

### 7.3c 四条查询输出的逐条一致性核对

| 查询 | 最大绝对差 | 一致 |
|---|---:|---|
| q0 | 0.0 | 是 |
| q1 | 0.0 | 是 |
| q2 | 0.0 | 是 |
| q3 | 0.0 | 是 |

> 全部查询一致：**True**；整体最大绝对差 = **0.0**。

### 7.3d 适配器端到端 与 一次性身份校验的纯计算副本

| 路径 | 中位 ms | 用途 |
|---|---:|---|
| 适配器端到端（runtime adapter） | 371.15 | 对外可用路径，本轮主结果 |
| 纯计算副本（一次性身份校验，不改共享仓库） | 34.40 | 仅核对二者给出相同输出 |

- 两条路径输出最大绝对差 = **0.0**（一致=True）。
- 纯计算副本**不写入共享仓库**，只在本轮 `code/` 内以一次性校验脚本形式存在。

**两条路径为何差这么多（必须一起读）**：适配器路径对 `initialize` / `advance` / `decode` 的**每一次调用**都执行一次全量 state-dict 哈希校验，共 `10` 次；纯计算副本 `0` 次。单次哈希中位 `33.35` ms，即校验本身约 333 ms，已接近两条路径的全部差额。
**结论**：这不是算子效率差异，而是**身份校验策略的代价**；报告时不得把它写成“适配器比纯计算慢 N 倍”的性能结论。

