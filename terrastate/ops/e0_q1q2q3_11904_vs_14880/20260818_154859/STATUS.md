# E0 — 11,904 vs verified 14,880 同协议 Q1/Q2/Q3 正式评测

Ops 目录：`ops/e0_q1q2q3_11904_vs_14880/20260818_154859/`
最后更新：2026-08-18（CST，下同）

## 总状态：`WAITING_FOR_SHARED_GPU`

**T0 未完成。** 六项正式 GPU 评测全部 `NOT_STARTED`。
GPU 已被其他用户重新占用，按安全约束**已停止所有 CUDA 动作**，改为
"watcher 常驻 + 只做 CPU 工作"。

| 项目 | 状态 | 说明 |
|---|---|---|
| M10 发布 + 注册 + alias | **DONE** | 已只读复核，见 §1 |
| Q1/Q2 GPU smoke（limit=2） | **DONE（仅管路）** | GPU 空闲窗口内完成，见 §3 |
| Q3 CPU smoke（limit=2, cpu） | **DONE（仅管路）** | 零 GPU 占用，见 §3 |
| 正式 launch manifest 冻结 | **DONE** | 6 job，mode 0444，见 §4 |
| 冻结输入复验 | **DONE** | 两份 manifest + 协议门，见 §5 |
| 验收/汇总脚本 | **DONE（19/19 自测）** | 见 §6 |
| 历史复现基准 | **DONE（57 指标）** | 见 §7 |
| **六项正式 GPU 评测** | **NOT_STARTED** | GPU 被占，watcher 待机，见 §2 |

> **没有任何 smoke 数字可以进论文。** Q1/Q2 smoke 的
> `NOT_LOAD_BEARING`、Q3 CPU smoke 的两样本数字都只证明"能跑通"，
> 不是研究结论。见 §3 的显式说明。

---

## 1. M10（已完成，本轮只做只读复核）

对象已发布到内容寻址库，**copy-only，源文件保留，mode 0444**：

```
/csy-mix02/cog8/zjliu17/Agent/model-artifacts/objects/sha256/a5/
  a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f.pt
```

三个 ID + alias 全部 rc=0 解析成功（本轮复核）：

| 逻辑 ID | 解析到的 file sha256 |
|---|---|
| `terrastate/v2/verified-resume14880@v1` | `a5d2a0cc…` |
| `terrastate/v2/legacy-boundary11904@v1` | `644deaac…` |
| `terrastate/v2/historical-full14880@v1` | `99f15a35…` |
| alias `terrastate/v2/default-training-anchor` | → `a5d2a0cc…` ✅ 符合要求 |

- registry revision：`ebc374b34b2e818a` → `a7fd2763935a26d1`
- 旧 revision 完整备份：`weight_registry.before_m10.ebc374b34b2e818a.json`
- 6 条冻结 `publish_conditions` 全部由 M9 具名检查项逐条兑现（6/6），
  记录在 `m10_register_report.json`
- 本轮**没有**重新发布、没有改写 alias、没有动 registry —— 只读复核未发现不一致

### 双来源标注（必须保持）

| 角色 | checkpoint | 用途 |
|---|---|---|
| legacy 证据 checkpoint / 精确续训父节点 | 11,904 `644deaac…` | 冻结 Q1/Q2/Q3 历史证据的来源 |
| anchor | verified 14,880 `a5d2a0cc…` | 后续旧模型评测与新阶段初始化 |

- 11,904 的历史 Q1/Q2/Q3 数字**永远不得改标成 14,880 的**。
- verified 14,880 与 historical 14,880 **权重逐字节相同**
  （`value_sha=aa98fbd2fa302727`，255 个张量最大差 0），
  但 **file sha256 不同**（多了 B5 lineage 块与本次 args/时间戳）——两句都成立，不可混为一谈。
- 11,904 与 14,880 **权重不同**（`aba100c138119bc0` vs `aa98fbd2fa302727`，
  最大绝对差 `1.9256e-03`），所以两者的指标差是真实的状态差异。

---

## 2. GPU 现状与 watcher

**当前占用者：`xddu2`**，8 张 H200 全部被占（16 个 compute process，
约 74 GB/卡）。已确认：本轮**未启动任何 GPU 程序**，
**未 kill / 暂停 / 修改 / 查看**其他用户任务的私有内容，未抢占部分卡。

### watcher（常驻，已脱离会话）

| 项 | 值 |
|---|---|
| PID | **2834736**（PPID=1，独立 session） |
| 命令 | `e0_watcher.py --interval 60 --required-streak 5 --deadline-hours 72` |
| 日志 | `e0_watcher.log`、`e0_watcher.nohup.log` |
| 状态文件 | `e0_watcher_state.json`（`status=WAITING_FOR_SHARED_GPU`） |
| 快照 | `gpu_snapshots.jsonl`（逐次追加，不覆盖） |
| 单实例锁 | `.e0_watcher.lock`（flock） |

放行条件（**fail-closed，任一不满足就不放行**）：
8 张卡全部可见 · 无任何 compute process · 显存 ≤ 100 MiB · 利用率 ≤ 5%，
**连续 5 次（约 5 分钟）**满足，且**启动前再复检一次**。
瞬时 0% 不算空闲；只有部分卡空闲时**继续等待**，绝不降级成 1–5 卡版本。

watcher 上线前通过 8 项测试：`py_compile`、真实节点占用检测、
伪造空闲检测、外部程序负例、GPU 数量负例、部分释放负例、flock 单实例、
完整 dry-run（dry-run 产生的空目录已清理）。

放行后行为：先起 batch A（GPU 0/1/2 = verified 14,880），
等待并确认存活、扫描日志无 Traceback/OOM/NaN 后再起 batch B（GPU 3/4/5 = legacy 11,904）；
**GPU 6/7 全程不碰**。若我们的 job 跑起来后有其他用户进入目标卡，
只停我们自己的进程组，写 `INTERRUPTED.json`（标明"非正式结果、不得汇总"），
等重新满足稳定空闲门后在**新的 retry 目录**重跑。

> **后台启动 ≠ 任务完成。** watcher 在跑，只代表放行门在监控；
> 六项正式评测在放行并跑完验收之前一律记为 `NOT_STARTED`。

---

## 3. Smoke（仅证明管路，全部不可作为结果）

### Q1/Q2 GPU smoke（GPU 空闲窗口内完成）
`smoke/q1q2/`，`--sections q1q2 --limit 2`，GPU 0。
`status=COMPLETE`、`checkpoint_unchanged=True`、arch=TerraStateV2 干净加载、
无 missing/unexpected key、JSON 正常生成、无 CUDA/OOM/NaN/scorer/schema 报错。

> 该 smoke 输出的 `Q2 verdict = NOT_LOAD_BEARING (significant=False)`
> **不是研究结果**：只有 2 个样本，统计量无意义。它只证明
> 加载 → 数据 → 前向 → 干预 → JSON 这条链路能跑通。

### Q3 CPU smoke（零 GPU 占用）
`smoke/q3_cpu/`，`CUDA_VISIBLE_DEVICES="" --device cpu --limit 2 --n-boot 200
--evidence-role diagnostic`。8/8 管路检查通过：
TerraStateV2 干净加载 · 冻结 pair + 协议解析 · actual/donor/mean 三臂可执行 ·
`uf_differs_all_pairs=True` · JSON schema 正常 · 无 NaN / Traceback / 缺文件。

> 记录为 `device=cpu, limit=2, n_boot=200, n_pairs=2, evidence_role=diagnostic`——
> 双样本指标**不做任何解释**。

---

## 4. 冻结的正式 launch manifest（未执行）

`launch_manifest.json`，mode **0444**，
sha256 `500e5031335c366ed06819dd9af8679dcf0318301d559aa7bfd573688c6cdd08`

| job | GPU | checkpoint | 内容 | 期望规模 |
|---|---|---|---|---|
| `gpu0_v14880_val_q1q2` | 0 | a5d2a0cc（14,880） | validation Q1/Q2 | 952 |
| `gpu1_v14880_oodt_q1q2` | 1 | a5d2a0cc | OOD-t Q1/Q2 | 1,904 |
| `gpu2_v14880_oodt_q3` | 2 | a5d2a0cc | Q3 `--evidence-role final` | 84 pairs |
| `gpu3_legacy11904_val_q1q2` | 3 | 644deaac（11,904） | validation Q1/Q2 | 952 |
| `gpu4_legacy11904_oodt_q1q2` | 4 | 644deaac | OOD-t Q1/Q2 | 1,904 |
| `gpu5_legacy11904_oodt_q3` | 5 | 644deaac | Q3 `--evidence-role final` | 84 pairs |

`gpu_policy.gpus_left_free = [6, 7]`。
`forbidden` 已写入 manifest：`--sections all`、Q4、改 scorer/mask/manifest/bootstrap/metric、
汇总 smoke 或 INTERRUPTED 输出、按 OOD 结果回选 checkpoint。

> 冻结 manifest 不得被静默修改。若必须改，先把旧版另存为
> `launch_manifest.rejected_<原因>.json` 并在本文件记录原因；
> `make_launch_manifest.py` 已内置"已存在即拒绝覆盖"的保护。

---

## 5. 冻结输入复验（本轮再次通过）

| 输入 | 期望 sha256 | 结果 |
|---|---|---|
| validation manifest（952） | `d9bd91d6…` | ✅ 一致 |
| OOD-t manifest（1,904） | `58c8d648…` | ✅ 一致 |
| Q3 协议目录 `artifacts/protocols/extreme_audit_oodt_v1` | `sha256sum -c MANIFEST.SHA256` | ✅ 7/7 OK |

未重新生成、未重新抽样、未改动任何协议文件。

---

## 6. 验收 / 汇总脚本（CPU-only，已自测）

`verify_and_aggregate.py`，`--selftest` **19/19 通过**；对当前真实状态运行
正确报 `NOT_READY`（`e0_launch_record.json` 不存在 ⇒ 六项正式任务未启动）。

已实现的硬门：
- 每个 job：exit code 0 · 非 INTERRUPTED · checkpoint SHA 前后不变 ·
  manifest SHA 匹配 · 目标数 952/1,904 · Q3 84 pairs ·
  `evidence_role == "final"` · 非 smoke limit · protocol_sha 已固定
- **拒绝**从 smoke 目录或含 `INTERRUPTED.json` 的目录汇总
- 配对统计：同样本 paired delta + 正态近似 95% CI + `excludes_zero`
- Q3 checkpoint 身份**直接对文件做 sha256**，不依赖结果 JSON
  （`extreme_state_audit.json` 的 schema 根本不记录 checkpoint sha，见 §7）

---

## 7. 历史复现基准（新增）

`historical_11904_reference.json`（57 个指标，sha256 `0b97406c…`），
由 `make_historical_reference.py` 从**冻结的原始 JSON 中提取**，
**不是**从 `TERRASTATE_V2_EVIDENCE.md` 抄数字——抄来的数字只会测试我的手抄准确度。

来源（每个都要求两份独立副本逐字节一致）：

| 标签 | 来源 | checkpoint 身份证明 |
|---|---|---|
| `val_q1q2` | `writing/evidence_workspace/raw/release/val_q2_state_contract_exclusive.json`（sha `33b40d3e…`） | JSON 内直接记录 `644deaac…` |
| `oodt_q1q2` | 同目录 `oodt_q1q2_state_contract_exclusive.json`（sha `7ebc0569…`） | JSON 内直接记录 `644deaac…` |
| `oodt_q3` | 同目录 `q3_extreme_state_audit.json`（sha `9dae43b9…`） | **sidecar**（见下） |

**Q3 的 schema 缺口（已显式记录，不掩盖）**：
`extreme_state_audit.json` 记录 `protocol_sha` 但**完全不记录 checkpoint sha**。
因此 Q3 的 11,904 身份用三个证据链接起来：
1. release 副本与产出目录 `…/selection/q3_final_boundary80_20260727_230029/extreme_state_audit.json`
   **逐字节相同**（都是 `9dae43b9…`）；
2. 该目录的 `checkpoint_sha256.txt` = `644deaac…`，`checkpoint_path.txt` = `run1/checkpoint_boundary80.pt`；
3. `exclusive/*/*/pred/provenance.json` 中有 **9 份**内嵌 `ckpt_sha=644deaac…`。

这比"JSON 内直接记录"弱，所以在基准文件里标为 `checkpoint_proof: "sidecar"`，
并同时约束：Q3 正式 job 的 SHA 校验必须直接哈希 checkpoint 文件。

### 容差策略（只兜浮点噪声，不放水）

| 类别 | 容差 | 理由 |
|---|---|---|
| 计数（`n`、`n_pairs`、`n_extreme`、`n_control`） | **0（必须精确相等）** | 计数变了就是 manifest / dataloader 变了，定义上就是漂移 |
| 点指标（R2 / rmse / nse / biasabs / Δ） | `1e-5` | 冻结数字在 GPU 上测得，cuDNN/TF32 归约顺序跨驱动不逐位稳定 |
| bootstrap CI 端点 | `1e-4` | 两个 evaluator 都用 `default_rng(--seed, 默认 0)`，重采样确定；但逐样本微扰会传到分位点 |

超出容差 ⇒ 报 `DRIFT_TO_DIAGNOSE`，**必须先排查 evaluator / manifest / scorer / dataloader**，
**不得直接解释为模型差异**——这道门的两侧是同一个 checkpoint（`644deaac…`, step 11,904），
模型不可能是原因。（与 11,904-vs-14,880 的比较无关，那里权重确实不同。）

自测覆盖：精确重放→`reproduced`；`1e-7` 噪声→容忍；`0.01` 偏移→`DRIFT_TO_DIAGNOSE`；
`n_pairs` 84→83→`DRIFT_TO_DIAGNOSE`；缺 job→`DRIFT_TO_DIAGNOSE`。

---

## 8. 结果解读的预设约束（跑完之前就固定）

- OOD-t 的 0.01 点差**只能**作为描述性 alignment 提示，
  **不得**用于选择或切换 checkpoint。
- **无论 14,880 结果高低，都不切回 11,904。**
  11,904 永久保持"历史证据来源"，14,880 永久保持 anchor。
- 不改任何论文声明；不开 Candidate C；不做 Q4；不给旧模型加训练步数。
- 未 commit、未 push。

---

## 9. 下一步（自动）

GPU 满足稳定空闲门后 watcher 自动执行 batch A → 存活确认 → batch B，
六项跑完后运行 `verify_and_aggregate.py` 做验收 + 复现门 + 配对比较。
在那之前，本任务状态保持 `WAITING_FOR_SHARED_GPU`。
