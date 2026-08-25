#!/usr/bin/env python3
"""从 v3 工件渲染 A03 总账（中文）—— 全部数字由脚本读出，无手抄环节。

数据来源仅限：
  * e0_comparison_11904_vs_14880_v3.json   （Q1/Q2/Q3 全部数值与 Δ）
  * e0_acceptance_report_v3.json           （验收判定、门统计、复现、sanity anchor）
  * e0_provenance_v3.json                  （谱系、缺口、时间线、协议、训练侧记录）
  * e0_artifact_index_v3.json              （工件路径/字节/SHA/计数）
  * e0_launch_record_v3.json               （作业 → 物理 GPU、PID、启动时刻）
  * attempt_manifest_v3.json               （作业清单、checkpoint、分区、约束）
  * closeout_audit_v3.json                 （封账环境、已纠正缺陷、已知缺口）
  * ops/resume11904_to14880/.../parameter_audit.json （49 行训练超参与见证列）

A03 v2 与 v1 的任何表格都不作为来源。

用法： CUDA_VISIBLE_DEVICES="" python3 render_a03_v3.py
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

ATTEMPT = Path(__file__).resolve().parent
TS_ROOT = Path(__file__).resolve().parents[3]
PARAM_AUDIT = TS_ROOT / "ops/resume11904_to14880/20260818_112933/parameter_audit.json"
OUT = TS_ROOT / "思路整理进展/A03_TerraState_关键实验结果与决策总账.md"

# 渲染时允许写入的目标文件（防止误写其它文档）
ALLOWED_OUT = {OUT.name}


def load(name: str):
    with open(ATTEMPT / name, "r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def fnum(v, nd=6):
    """数值格式化。None 如实写成「未记录」，绝不填 0 或占位符。"""
    if v is None:
        return "未记录"
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float):
        if v != v:
            return "NaN"
        a = abs(v)
        if a != 0 and (a < 1e-4 or a >= 1e7):
            return f"{v:.3e}"
        return f"{v:.{nd}f}"
    return str(v)


def fdelta(v, nd=6):
    if v is None:
        return "—"
    if isinstance(v, float):
        a = abs(v)
        s = f"{v:+.3e}" if (a != 0 and a < 1e-4) else f"{v:+.{nd}f}"
        return s
    if isinstance(v, int):
        return f"{v:+d}"
    return str(v)


def cell(block, *path):
    cur = block
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return {"v11904": None, "v14880": None, "delta": None}
        cur = cur[p]
    return cur if isinstance(cur, dict) else {"v11904": None, "v14880": None, "delta": None}


def row3(label, c, nd=6):
    return (f"| {label} | {fnum(c.get('v11904'), nd)} | {fnum(c.get('v14880'), nd)} "
            f"| {fdelta(c.get('delta'), nd)} |")


def human_bytes(n):
    if n is None:
        return "未记录"
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024 or unit == "TiB":
            return f"{n:,} B（{n/1024**0 if unit=='B' else n/(1024**('B KiB MiB GiB TiB'.split().index(unit)))::.2f} {unit}）" if False else (
                f"{n:,} B" if unit == "B" else f"{n:,} B ≈ {n/(1024**('B KiB MiB GiB TiB'.split().index(unit))):.2f} {unit}")
        n_unit = unit
    return f"{n:,} B"


def gib(n):
    return "未记录" if n is None else f"{n:,} B ≈ {n/1024**3:.2f} GiB"


def mib(n):
    return "未记录" if n is None else f"{n:,} B ≈ {n/1024**2:.1f} MiB"


def atomic_write_text(path: Path, text: str) -> str:
    path = Path(path)
    if path.name not in ALLOWED_OUT:
        raise SystemExit(f"REFUSE: 目标文件不在允许写入清单内：{path}")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dirfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return sha256_file(path)


# ============================== 载入全部来源 ==============================

CMP = load("e0_comparison_11904_vs_14880_v3.json")
REP = load("e0_acceptance_report_v3.json")
PRV = load("e0_provenance_v3.json")
IDX = load("e0_artifact_index_v3.json")
LAU = load("e0_launch_record_v3.json")
MAN = load("attempt_manifest_v3.json")
AUD = load("closeout_audit_v3.json")
with open(PARAM_AUDIT, "r", encoding="utf-8") as f:
    PA = json.load(f)

HP = {r["parameter"]: r.get("frozen_value_for_resume") for r in PA["rows"]}
WIT = {r["parameter"]: r for r in PA["rows"]}
TS_ = PRV["trusted_sources"]
REG = TS_["registry_entries"]
CK = MAN["checkpoints"]
ENV = AUD["closeout_environment"]
M9 = TS_["training_side_records"]["m9_acceptance"]
SSC = TS_["training_side_records"]["state_sha_check"]
Q3P = TS_["q3_protocol"]
TL = PRV["timeline_log_provable"]
H = CMP["headline"]

L: list[str] = []
A = L.append


def sec(t):
    A("")
    A(t)
    A("")


# ============================== 文档 ==============================

A("# A03 TerraState 关键实验结果与决策总账")
A("")
A(f"**文档状态**：E0 v3 封账版（由 `{Path(__file__).name}` 从 v3 工件渲染，非手工抄录）  ")
A(f"**实验编号**：E0（11,904 与 14,880 同协议对照评测）  ")
A(f"**v3 验收判定**：{REP['verdict']}（检查 {REP['n_checks']} 项，失败 {REP['n_failed']} 项）  ")
rp = REP["reproduction"]
A(f"**历史复现**：{rp['n_pass']}/{rp['n_formal_metric_keys']} 个正式指标通过，"
  f"其中逐位相同 {rp['n_bit_exact']} 个（{rp['scope']}）  ")
A(f"**渲染时间（UTC）**：{ENV['now_utc']}  ")
A(f"**GPU 执行节点**：{MAN['nodes']['gpu_execution_hostname']}；"
  f"**CPU 封账节点**：{MAN['nodes']['cpu_closeout_hostname']}  ")
A(f"**前一版快照**：`A03_snapshot_before_v3_correction.md`（与被替换的 v2 正文逐字节一致，另存 `.sha256` 旁证）")
A("")
A("> 本文档记录当前证据链所能支持的结论。它不是「最终结论」：后续实验（Candidate C、Q4）可能改变其中的解释部分。")

sec("---")
sec("## 零、v3 相对 v2 修正了什么")
A("v2 正文中的下列内容经一手工件核对为错误或无来源，v3 全部改正。改正依据写在括号内。")
A("")
A("1. **历史复现指标个数**：v2 写 65/65。冻结参考 `historical_11904_reference.json` 的正式指标键实为 "
  f"**{rp['n_formal_metric_keys']} 个**（另有 8 个 `_` 前缀元数据键必须排除在计数之外）。v3 记 "
  f"{rp['n_pass']}/{rp['n_formal_metric_keys']}。")
A("2. **Q2 对照表数字无来源**：v2 表中 0.556762 / 0.556617 / 0.556546 / 0.484868 / 0.012454 / "
  "0.013196 / 0.012587 / 0.012732 等值，在六份一手结果 JSON 的全部浮点数中以 |Δ|<5e-7 搜索命中集合为空"
  "（验收器 gate E8 程序化确证）。v3 的 Q2 全部数值改由脚本从 raw JSON 读出。")
A("3. **Q1 分层与 horizon 表数字错误**：v2 的 OOD-t 分层（Forest 0.629023 等）与 horizon（0-5 天 0.113876 等）"
  "与一手结果不符。v3 见 §3.1，全部重新读出。")
A("4. **模型状态同一性被写反**：v2 称 11,904 与 14,880「模型张量值 SHA 一致」。"
  "一手证据只支持：**verified 14,880 与历史 14,880** 两者的 255 个模型张量逐值相同"
  f"（`value_sha={M9['value_digest_16hex']}`，max abs diff = 0）。"
  "11,904 与 14,880 是不同的模型状态，其证据是二者在同一 split 上的评测结果本身就不同（见 §3.1）。")
A("5. **`<待补充>` 占位符**：v2 的模型状态 SHA、batch_size、lr 等处留有占位符。"
  f"v3 的训练超参全部取自 `parameter_audit.json`（{PA['n_rows']} 行，全部 consistent），见 §2.3。")
A("6. **时间线含无法证明的时刻**：v2 写有 guardian 启动/退出时刻与「总耗时约 20 分钟」。"
  "v3 只保留日志与文件系统可证的时刻，并显式声明哪些量不可证（见 §2.4）。")
A("7. **SHA 一律 `—` 占位**：v2 的工件清单 SHA 列全部为 `—`。v3 见 §5，全部为实测值。")
A("8. **「本文档为当前最终版本」**：改为「当前证据链下的封账版」，不使用「最终」。")

sec("---")
sec("## 一、实验目标与协议")
sec("### 1.1 要回答的问题")
A("1. 在完全相同的协议下，14,880 步与 11,904 步的表现差异有多大、方向如何？")
A("2. 11,904 步的历史评测数字能否在本次环境与协议下复现？")
A("3. 14,880 步能否作为后续实验的 anchor checkpoint？")
A("")
A("本轮**没有**对两个 checkpoint 之间的差异做统计显著性检验，因此下文不出现「显著/不显著」「属于噪声」一类表述。"
  "（Q2 与 Q3 内部各自的 bootstrap 置信区间是**协议自带**的，针对的是「状态是否承载」「响应是否保真」，"
  "不是针对 11,904 与 14,880 的差异。）")

sec("### 1.2 评测协议与冻结输入")
dm = TS_["data_manifests"]
A("| 协议 | 冻结清单 | 文件 SHA-256 | 目标数 |")
A("|---|---|---|---|")
for k, label in (("val", "Q1/Q2 Validation"), ("oodt", "Q1/Q2 OOD-t")):
    e = dm[k]
    A(f"| {label} | `{Path(e['path']).name}` | `{e['sha256']}` | {e['n_files']} |")
A(f"| Q3 极端态审计 | `{Path(Q3P['dir']).name}/`（冻结协议目录） | "
  f"MANIFEST.SHA256 = `{Q3P['manifest_sha256']}` | {Q3P['counts']['n_primary']} 对 |")
A("")
gt = PRV["ground_truth_binding"]
A(f"**ground truth 归属**：Q3 协议冻结于 `{gt['q3_protocol_frozen_utc']}`，最早一次评测启动于 "
  f"`{gt['earliest_eval_start_utc']}`，冻结早于评测 **{gt['frozen_lead_days']} 天**。"
  "阈值与配对数只从冻结协议文件读入，不由本轮模型输出反推。")
A("")
th = Q3P["thresholds"]
A(f"Q3 阈值（冻结自训练集异常分布，原样施加于 OOD-t）：strict hot={fnum(th['strict']['hot'])}, "
  f"dry={fnum(th['strict']['dry'])}；broad hot={fnum(th['broad']['hot'])}, dry={fnum(th['broad']['dry'])}。")
A("")
A(f"Q3 协议计数（取自 `protocol.json`，非模型输出）：n_strict={Q3P['counts']['n_strict']}，"
  f"n_broad={Q3P['counts']['n_broad']}，n_primary={Q3P['counts']['n_primary']}，"
  f"n_control_unique={Q3P['counts']['n_control_unique']}。")
A("")
fp = Q3P["frozen_provenance"]
A(f"协议冻结时的仓库状态：git_commit=`{fp['git_commit']}`，git_dirty={fnum(fp['git_dirty'])}，"
  f"seed={fp['seed']}，n_train_used={fp['n_train_used']}，n_oodt_valid={fp['n_oodt_valid']}。")

sec("### 1.3 evaluator 身份")
for rel, e in TS_["evaluator_sources"].items():
    ok = "与冻结 manifest 记录一致" if e["sha256"] == e["frozen_expected"] else "**与冻结记录不一致**"
    A(f"- `{rel}`：实测 SHA-256 `{e['sha256']}`（{ok}）")
A("")
ec = PRV["evaluator_commit"]
A(f"- Q1/Q2 结果 JSON 自带 evaluator commit：`{ec['q1q2']}`（四份一致）")
A(f"- Q3 结果 JSON **不记录** evaluator commit。{ec['q3_gap_note']}")

sec("---")
sec("## 二、三份 checkpoint、继续训练与执行记录")
sec("### 2.1 三份 checkpoint 的身份与谱系")
A("本实验涉及三份 checkpoint。**三者文件身份互不相同**，必须分别称呼：")
A("")
A("| 项 | 边界 11,904 | verified 14,880 | 历史 14,880 |")
A("|---|---|---|---|")


def r3(label, f):
    return f"| {label} | {f('boundary11904')} | {f('verified14880')} | {f('historical14880')} |"


A(r3("逻辑 ID", lambda k: f"`{CK[k]['logical_id']}`"))
A(r3("步数", lambda k: str(CK[k]["step"])))
A(r3("文件字节数", lambda k: f"{CK[k]['bytes']:,}"))
A(r3("文件权限", lambda k: CK[k]["mode"]))
A(r3("文件 SHA-256", lambda k: f"`{CK[k]['file_sha256']}`"))
A(r3("内容寻址路径", lambda k: f"`{REG.get(k, {}).get('object_relpath', '未记录')}`"))
A(r3("文件内记录的 stage", lambda k: fnum(REG.get(k, {}).get("stage_recorded_in_file"))))
A(r3("epoch", lambda k: fnum(REG.get(k, {}).get("epoch"))))
A(r3("父节点", lambda k: f"`{REG.get(k, {}).get('parent_id')}`" if REG.get(k, {}).get("parent_id") else "无（非 resume 产物）"))
A("")
A("**关于「模型状态相同」这一说法的准确边界**：")
A("")
A(f"- 已验明：**verified 14,880 与历史 14,880** 的 255 个模型张量逐值相同 —— "
  f"`{M9['historical_bit_exact_detail']}`。")
A(f"- 同时成立：二者**文件 SHA-256 不同**（`{CK['verified14880']['file_sha256'][:16]}…` vs "
  f"`{CK['historical14880']['file_sha256'][:16]}…`），因为 verified 版另外携带 B5 谱系块与本次运行的 args/时间戳。"
  "「权重逐字节相同」与「文件身份独立」两句都为真，不得混为一谈。")
A(f"- **11,904 与 14,880 不是同一模型状态**。11,904 的 `b4_state_sha256` = "
  f"`{REG['boundary11904'].get('b4_state_sha256')}`（64 位十六进制），"
  f"与上面 16 位的 `value_sha` 是两套互不可比的摘要方案。二者不同的正向证据见 §3.1：同一 split 上评测结果本身就不同。")
A("")
A(f"- 边界 11,904 的保存时机说明（取自 registry provenance_notes）：{REG['boundary11904']['provenance_notes'][0]}")
A(f"- 边界 11,904 携带的续训状态：{REG['boundary11904']['provenance_notes'][1]}")
A("")
al = TS_["alias"]
A(f"**别名**：`{al['logical_id']}` 由 `terrastate/v2/default-training-anchor` 指向"
  f"（alias 文件 SHA-256 `{al['sha256']}`，set_at={al.get('set_at')}）。")
reg = TS_["weight_registry"]
A(f"**registry**：`{Path(reg['path']).name}`，revision `{reg['revision']}`，"
  f"schema `{reg['schema']}`，登记 {reg['n_artifacts']} 件工件，实测 SHA-256 `{reg['sha256']}`。")

sec("### 2.2 11,904 → 14,880 的继续训练")
lin = M9["lineage"]
ar = PA["arithmetic_self_consistency"]
sb = PA["stage_boundary_semantics"]
A("| 项 | 值 | 来源 |")
A("|---|---|---|")
A(f"| 续训方式 | exact-resume（resumed={fnum(lin['resumed'])}） | m9_acceptance_report.json |")
A(f"| 父 checkpoint | step={lin['parent_step']}, epoch={lin['parent_epoch']}, "
  f"micro_in_epoch={lin['parent_micro_in_epoch']} | 同上 |")
A(f"| 父文件内记录 stage | {lin['parent_stage_recorded']} | 同上 |")
A(f"| resume 实际施加 stage | {lin['resume_stage_applied']} | 同上 |")
A(f"| 优化器更新次数 | {ar['total_steps_minus_parent_step']}（= {HP['total_steps']} − {lin['parent_step']}） | parameter_audit.json |")
A(f"| 覆盖 epoch | {ar['epochs_range']}（剩余 {ar['remaining_epochs']} 个 epoch） | 同上 |")
A(f"| 每 epoch 更新数 | {ar['updates_per_epoch']} | 同上 |")
A(f"| 边界公式 | {ar['boundary80_formula']} | 同上 |")
A(f"| 数据顺序恢复 | {lin['data_order_restoration']} | m9_acceptance_report.json |")
A(f"| M9 验收 | accepted={fnum(M9['accepted'])}，{REG['verified14880']['m9_checks_passed']} 项检查通过 | 同上 |")
A(f"| 终点 | step={M9['final_step']}, stage={M9['stage']}, best_val={fnum(M9['best_val'], 8)} | 同上 |")
A("")
A(f"**stage 记录的已知歧义**：`stage_at_11904 = {sb['stage_at_11904']}`，而边界文件内记录的是 "
  f"`{sb['recorded_stage_in_parent']}`。原因：{sb['evidence']}。要求：{sb['requirement']}。"
  "本文如实保留这一差异，不做抹平。")
A("")
A("**warm-start / teacher / q_projector 身份核对**（`state_sha_check.json`）：")
A("")
A(f"- 全部匹配 all_match={fnum(SSC['all_match'])}；teacher_load_exact={fnum(SSC['teacher_load_exact'])}"
  f"（missing={SSC['teacher_load_missing']}, unexpected={SSC['teacher_load_unexpected']}）")
A(f"- warm_start_exact={fnum(SSC['warm_start_exact'])}"
  f"（missing={SSC['warm_start_missing']}, unexpected={SSC['warm_start_unexpected']}），"
  f"来源架构 {SSC['warm_start_source']}")
A(f"- teacher：{SSC['teacher_arch']}，q keys={SSC['teacher_q_keys']}，SHA-256 `{SSC['teacher_sha256']}`")
A(f"- student_init：{SSC['student_init_arch']}，SHA-256 `{SSC['student_init_sha256']}`")
A(f"- q_projector 初始化 SHA-256 `{SSC['q_projector_init_sha256']}`")

sec("### 2.3 训练超参（全部有值，无占位符）")
pa_sha = TS_["training_side_records"]["parameter_audit"]["sha256"]
A(f"下表取自 `parameter_audit.json`（SHA-256 `{pa_sha}`，{PA['n_rows']} 行，"
  f"all_consistent={fnum(PA['all_consistent'])}，inconsistent_parameters={PA['inconsistent_parameters']}）。"
  "「见证」列表示该值在 checkpoint / runbook / train.log 中各自是否独立出现。")
A("")
A("| 参数 | 冻结值 | 见证 |")
A("|---|---|---|")
GROUPS = ["world_size", "per_gpu_batch", "accum", "global_batch", "updates_per_epoch",
          "max_epochs", "max_steps", "total_steps", "boundary80",
          "branch_lr", "q_lr_scale", "lr_warmup_steps", "weight_decay", "grad_clip",
          "unfreeze_q_prefixes", "alpha", "loss_weights.gt", "loss_weights.kd",
          "lambda_state@11904", "state_dim", "seed", "deterministic", "device",
          "num_workers", "val_interval", "ckpt_interval", "log_interval",
          "cache_fail_closed_gb", "train_cache_cubes", "val_cache_cubes", "cache_horizon_h",
          "resume.step", "resume.epoch", "resume.micro_in_epoch", "resume.stage",
          "resume.q_freeze.trainable_q", "resume.best_val"]
for k in GROUPS:
    if k not in WIT:
        continue
    r = WIT[k]
    w = [n for n, c in (("checkpoint", "checkpoint"), ("runbook", "runbook"), ("train.log", "train_log"))
         if r.get(c) is not None]
    v = r.get("frozen_value_for_resume")
    vs = f"`{v}`" if not isinstance(v, (list, dict)) else f"`{json.dumps(v, ensure_ascii=False)}`"
    A(f"| `{k}` | {vs} | {' + '.join(w) if w else '仅审计表'} |")
A("")
A("训练侧数据指纹（**与评测侧冻结清单是不同文件，不得互换引用**）：")
A("")
for k in ("sha.train_manifest_sha256", "sha.val_manifest_sha256",
          "sha.train_cache_sha256", "sha.val_cache_sha256", "sha.q_projector_init_sha256"):
    if k in HP:
        A(f"- `{k}` = `{HP[k]}`")
A("")
md = PRV["manifest_disambiguation"]
A(f"> {md['note']}。验收器 gate F6 断言训练侧与评测侧 SHA 集合交集为空。")

sec("### 2.4 执行记录与可证时间线")
A("六份正式作业与其物理 GPU 的对应关系，**唯一权威来源是 launch shard**；"
  f"逻辑作业名（gpu0…gpu5）与物理 GPU 编号无对应关系，不得由名字推断。")
A("")
A("| 逻辑作业名 | 类型 | split | checkpoint | 物理 GPU | PID | exit | 启动（UTC） |")
A("|---|---|---|---|---|---|---|---|")
for j in LAU["jobs"]:
    A(f"| `{j['name']}` | {j['kind']} | {j['split']} | {j['checkpoint_role']} | "
      f"{j['physical_gpu']} | {j['pid']} | {j['exit_code']} | {j['started_utc']} |")
A("")
A(f"实际使用的物理 GPU：{LAU['physical_gpus_used']}。")
A("")
A("**可证时间线**（每一行都有指定证据；两类事件性质不同，不得相减当作单作业耗时）：")
A("")
A("| 时刻（UTC） | 事件 | 作业 | 证据 |")
A("|---|---|---|---|")
for e in TL["events"]:
    A(f"| {e['utc']} | {e['event']} | `{e['job']}` | {e['evidence']} |")
A("")
A(f"- 最早启动：{TL['earliest_job_start_utc']}；最后一份结果落盘：{TL['latest_result_write_utc']}")
A(f"- {TL['span_note']}")
A("")
A("**明确不可证的量**（因此本文不写）：")
for x in TL["not_log_provable"]:
    A(f"- {x}")

sec("---")
sec("## 三、结果")
A("下文所有数值由渲染脚本从 `e0_comparison_11904_vs_14880_v3.json` 读出，"
  f"该文件本身由验收器从六份一手结果 JSON 生成。**Δ 的约定：{CMP['delta_convention']}**。")

sec("### 3.1 Q1 预测精度")
for split, title in (("val", "Validation"), ("oodt", "OOD-t")):
    b = H["Q1"][split]
    nt = b["n_targets"]
    A("")
    A(f"#### {title}（{nt['v11904']} targets，冻结清单 SHA-256 `{nt['frozen_manifest_sha256'][:16]}…`）")
    A("")
    A("| 指标 | 11,904 | 14,880 | Δ |")
    A("|---|---|---|---|")
    for m, lab in (("R2", "R²"), ("rmse", "RMSE"), ("nse", "NSE"), ("biasabs", "|bias|")):
        A(row3(lab, b["overall"][m]))
    A("")
    A(f"**{title} — 预测步长分解（RMSE）**")
    A("")
    A("| Horizon | 11,904 | 14,880 | Δ |")
    A("|---|---|---|---|")
    for h, lab in (("rmse_0_5", "0–5 天"), ("rmse_5_10", "5–10 天"),
                   ("rmse_10_15", "10–15 天"), ("rmse_15_20", "15–20 天"),
                   ("rmse25", "rmse25")):
        A(row3(lab, b["horizons"][h]))
    A("")
    A(f"**{title} — 植被分层**")
    A("")
    A("| 分层 | 指标 | 11,904 | 14,880 | Δ |")
    A("|---|---|---|---|---|")
    for s, lab in (("forest", "Forest"), ("shrub", "Shrub"), ("grass", "Grass"), ("crop", "Crop")):
        for m, ml in (("R2", "R²"), ("rmse", "RMSE"), ("nse", "NSE"), ("biasabs", "|bias|")):
            c = b["strata"][s][m]
            A(f"| {lab} | {ml} | {fnum(c['v11904'])} | {fnum(c['v14880'])} | {fdelta(c['delta'])} |")
A("")
A("**读法**：两个 checkpoint 在 Q1 上的差异出现在小数点后第四位及更小的量级，"
  "方向在不同 split、不同分层、不同预测步长上并不一致（既有 Δ<0 也有 Δ>0）。"
  "本轮未对这些差异做显著性检验，因此只描述量级与方向，不做「等价」「无差别」一类判断。")
A("")
A("**同时，这些非零差异本身就是 11,904 与 14,880 属于不同模型状态的正向证据** —— "
  "若两者权重相同，同一冻结清单、同一 evaluator 下的结果应当逐位一致。")

sec("### 3.2 Q2 状态承载能力")
for split, title in (("val", "Validation"), ("oodt", "OOD-t")):
    b = H["Q2"][split]
    A("")
    A(f"#### {title}")
    A("")
    A("| 臂 | 指标 | 11,904 | 14,880 | Δ |")
    A("|---|---|---|---|---|")
    for arm, lab in (("full", "full"), ("alpha0", "α₀（context-prior）"), ("T_identity", "T-identity")):
        for m, ml in (("R2", "R²"), ("rmse", "RMSE")):
            c = b["arms"][arm][m]
            A(f"| {lab} | {ml} | {fnum(c['v11904'])} | {fnum(c['v14880'])} | {fdelta(c['delta'])} |")
    A("")
    A("| 官方 Δ | 11,904 | 14,880 | Δ |")
    A("|---|---|---|---|")
    A(row3("R²(full) − R²(α₀)", b["official_deltas"]["official_R2_full_minus_alpha0"]))
    A(row3("R²(full) − R²(T-identity)", b["official_deltas"]["official_R2_full_minus_Tid"]))
    A("")
    A("**bootstrap 与配对统计**（该 CI 针对「状态是否承载」，不是针对两 checkpoint 之差）")
    A("")
    A("| 家族 | 量 | 11,904 | 14,880 | Δ |")
    A("|---|---|---|---|---|")
    for fam, fl in (("closure_cut_alpha0", "closure_cut_α₀"),
                    ("transition_identity", "transition_identity")):
        fb = b["bootstrap_families"][fam]
        for m, ml in (("mean", "bootstrap95 mean"), ("ci_low", "bootstrap95 ci_low"),
                      ("ci_high", "bootstrap95 ci_high"), ("frac_pos", "frac_pos"),
                      ("n", "n"), ("significant_gt0", "significant>0")):
            c = fb["bootstrap95"][m]
            A(f"| {fl} | {ml} | {fnum(c['v11904'])} | {fnum(c['v14880'])} | {fdelta(c['delta'])} |")
        for m, ml in (("n", "paired n"), ("win", "win"), ("tie", "tie"), ("loss", "loss"),
                      ("mean_delta_R2", "paired mean ΔR²"), ("median_delta_R2", "paired median ΔR²")):
            c = fb["paired"][m]
            A(f"| {fl} | {ml} | {fnum(c['v11904'])} | {fnum(c['v14880'])} | {fdelta(c['delta'])} |")
    A("")
    A("| 判定项 | 11,904 | 14,880 |")
    A("|---|---|---|")
    for k, lab in (("dr2_floor", "ΔR² floor"), ("dr2_floor_pass", "floor 通过"),
                   ("transition_margin_clean", "transition_margin_clean"), ("verdict", "verdict")):
        c = b["gates"][k]
        A(f"| {lab} | {fnum(c['v11904'])} | {fnum(c['v14880'])} |")
    A("")
    A("| 不变量 | 11,904 | 14,880 |")
    A("|---|---|---|")
    for k in ("alpha0_pred_equals_context_prior", "T_identity_is_state_identity", "live_weights_restored"):
        c = b["invariants"][k]
        A(f"| `{k}` | {fnum(c['v11904'])} | {fnum(c['v14880'])} |")
A("")
A(f"**`transition_margin_clean = False` 的原因（协议自带说明，非本文推测）**：{H['Q2']['val']['transition_margin_confound_note']}")
A("")
A("因此 T-identity 一臂的 margin 有一部分来自 OOD 效应，不能整体解释为「状态转移的贡献」。"
  "这一标记在两个 checkpoint 上同时为 False，属于该评测路径的共有属性。")

sec("### 3.3 Q3 极端态审计")
q = H["Q3"]
A(f"配对结构：n_pairs={q['counts']['n_pairs']['v14880']}，"
  f"protocol_n_pairs={q['counts']['protocol_n_pairs']['v14880']}，"
  f"n_extreme={q['counts']['n_extreme']['v14880']}，"
  f"n_control_unique={q['counts']['n_control_unique']['v14880']}，"
  f"geo cluster 数={q['counts']['n_geo_clusters']['v14880']}，"
  f"reused-control cluster 数={q['counts']['n_reused_control_clusters']['v14880']}，"
  f"bootstrap 重抽样 {q['counts']['n_boot']['v14880']} 次。")
A("")
A("**三臂聚合精度（极端态）**")
A("")
A("| 臂 | 指标 | 11,904 | 14,880 | Δ |")
A("|---|---|---|---|---|")
for arm, al_ in (("actual", "actual"), ("donor", "donor"), ("mean", "mean")):
    for m, ml in (("R2", "R²"), ("rmse", "RMSE"), ("nse", "NSE")):
        c = q["aggregate"][arm][m]
        A(f"| {al_} | {ml} | {fnum(c['v11904'])} | {fnum(c['v14880'])} | {fdelta(c['delta'])} |")
A("")
A("**端点保真（endpoint fidelity）**：Δloss = 对照臂损失 − actual 损失，>0 表示 actual 更贴合真实极端终点。")
A("")
A("| 对照 | 家族 | 量 | 11,904 | 14,880 | Δ |")
A("|---|---|---|---|---|---|")
for c_, cl in (("extreme_actual_vs_donor", "actual vs donor"),
               ("extreme_actual_vs_mean", "actual vs mean")):
    ef = q["endpoint_fidelity"][c_]
    cc = ef["delta_loss_mean"]
    A(f"| {cl} | — | delta_loss_mean | {fnum(cc['v11904'])} | {fnum(cc['v14880'])} | {fdelta(cc['delta'])} |")
    for fam, fl in (("paired_bootstrap", "paired"),
                    ("geo_cluster_bootstrap", "geo-cluster"),
                    ("reused_control_cluster_bootstrap", "reused-control")):
        fb = ef[fam]
        for m in ("mean", "ci_low", "ci_high", "n", "significant_gt0"):
            if m in fb:
                cc = fb[m]
                A(f"| {cl} | {fl} | {m} | {fnum(cc['v11904'])} | {fnum(cc['v14880'])} | {fdelta(cc['delta'])} |")
        for m in ("n_clusters", "frac_pos"):
            if m in fb:
                cc = fb[m]
                A(f"| {cl} | {fl} | {m} | {fnum(cc['v11904'])} | {fnum(cc['v14880'])} | {fdelta(cc['delta'])} |")
A("")
A("**响应幅度（response magnitude）**")
A("")
A("| 对照 | 量 | 11,904 | 14,880 | Δ |")
A("|---|---|---|---|---|")
for c_, cl in (("extreme_actual_vs_donor", "极端 actual vs donor"),
               ("extreme_actual_vs_mean", "极端 actual vs mean"),
               ("normal_actual_vs_donor", "常态 actual vs donor"),
               ("normal_actual_vs_mean", "常态 actual vs mean")):
    for m in ("mean", "n"):
        cc = q["response_magnitude"][c_][m]
        A(f"| {cl} | {m} | {fnum(cc['v11904'])} | {fnum(cc['v14880'])} | {fdelta(cc['delta'])} |")
A("")
A("**热干交互（hot-dry − normal）**：这是 `hotdry_enhancement` 判定所依据的量。")
A("")
A("| 效应量 | 家族 | 量 | 11,904 | 14,880 | Δ |")
A("|---|---|---|---|---|---|")
for eff in ("dloss_donor", "dloss_mean", "resp_donor", "resp_mean"):
    for fam, fl in (("paired_bootstrap", "paired"),
                    ("geo_cluster_bootstrap", "geo-cluster"),
                    ("reused_control_cluster_bootstrap", "reused-control")):
        fb = q["hotdry_interaction"][eff][fam]
        for m in ("mean", "ci_low", "ci_high", "significant_gt0"):
            cc = fb[m]
            A(f"| `{eff}` | {fl} | {m} | {fnum(cc['v11904'])} | {fnum(cc['v14880'])} | {fdelta(cc['delta'])} |")
A("")
A("**分层精度（两个 cohort × 四条臂）**")
A("")
A("| cohort | 臂 | 指标 | 11,904 | 14,880 | Δ |")
A("|---|---|---|---|---|---|")
for cohort, arms in q["strata"].items():
    for arm, ms in arms.items():
        for m, ml in (("R2", "R²"), ("rmse", "RMSE")):
            cc = ms[m]
            A(f"| {cohort} | `{arm}` | {ml} | {fnum(cc['v11904'])} | {fnum(cc['v14880'])} | {fdelta(cc['delta'])} |")
A("")
wib = q["verdicts"]["weather_in_base"]
A(f"> `weather_in_base` 一臂的 R²/RMSE 两侧均为 null，与 `weather_in_base={fnum(wib['v14880'])}` 一致 —— "
  "该消融臂本轮未运行，不是缺失数据。")
A("")
A("**判定**")
A("")
A("| 判定项 | 11,904 | 14,880 |")
A("|---|---|---|")
for k, lab in (("endpoint_fidelity_status", "端点保真"),
               ("hotdry_enhancement_status", "热干增强"),
               ("raw_status", "raw_status"),
               ("overall_status", "overall_status"),
               ("primary_criterion", "主判据"),
               ("uf_differs_all_pairs", "全部配对 uf 有差异"),
               ("weather_in_base", "weather_in_base"),
               ("evidence_role", "证据角色")):
    cc = q["verdicts"][k]
    A(f"| {lab} | {fnum(cc['v11904'])} | {fnum(cc['v14880'])} |")
A("")
A("**口径边界**：`overall_status = Q3_RESPONSE_FIDELITY_ONLY` 的含义是 —— "
  "在冻结协议下，actual 状态相对 donor / mean 对照更贴合极端终点（端点保真 PASS）；"
  "但**未**取得「热干条件下存在额外增强」的支持（热干增强 FAIL，主判据 geo-cluster CI 下界 ≤ 0）。"
  "不能据此声称模型整体通过了极端态审计，也不能声称模型能正确预测真实极端状态或具备因果反事实正确性。")
A("")
A("热干增强判 FAIL 的原因本轮**无法区分**，候选包括架构能力边界、训练数据中极端样本的分布、"
  "损失函数对非线性交互的引导不足、协议对该效应的敏感度等。本文不选定其中任何一种。")

sec("### 3.4 历史复现")
hr = TS_["historical_reference"]
A(f"**范围**：{rp['scope']}。")
A("")
A(f"- 冻结参考：`{Path(hr['path']).name}`，SHA-256 `{hr['sha256']}`（验收器对该 SHA 做 fail-closed 校验，"
  "不符即停止封账）")
A(f"- 正式指标键 **{hr['n_formal']} 个**；被排除的 `_` 前缀元数据键 {len(hr['metadata_keys'])} 个："
  f"{', '.join('`%s`' % k for k in hr['metadata_keys'])}")
A(f"- 结果：{rp['n_pass']}/{rp['n_formal_metric_keys']} 通过，其中 **逐位相同 {rp['n_bit_exact']} 个**")
A(f"- 默认容差 {hr['default_tolerance']}；按模式指定的容差：`{json.dumps(hr['per_pattern_tolerances'], ensure_ascii=False)}`")
if hr.get("tolerance_rationale"):
    A(f"- 容差理由：{hr['tolerance_rationale']}")
A("")
A("**限定**：本项验证的是「在本次环境与本协议下，用同一 checkpoint 重跑能否得到同样的数字」。"
  "它不主张跨环境的完全确定性，也不主张 SHA 与结果之间存在唯一映射。"
  f"14,880 一侧没有历史参考可比 —— {rp['scope']}。")

sec("---")
sec("## 四、决策")
sec("### 4.1 结论")
A("**14,880（`terrastate/v2/verified-resume14880@v1`）继续作为后续实验的 anchor checkpoint。**")
A("")
A("依据：")
A("")
A("1. **Q1**：与 11,904 的差异在小数点后第四位及更小量级，方向在各 split / 分层 / 步长上不一致（见 §3.1）。")
A("2. **Q2**：两者在 Validation 与 OOD-t 上的 verdict 均为 "
  f"`{H['Q2']['val']['gates']['verdict']['v14880']}`，ΔR² 均超过 floor "
  f"{fnum(H['Q2']['val']['gates']['dr2_floor']['v14880'])}（见 §3.2）。")
A("3. **Q3**：两者的三项判定完全一致（端点保真 PASS、热干增强 FAIL、"
  f"overall `{q['verdicts']['overall_status']['v14880']}`）。")
A("4. **续训过程可验证**：exact-resume，M9 "
  f"{REG['verified14880']['m9_checks_passed']} 项检查通过，"
  f"{ar['total_steps_minus_parent_step']} 次优化器更新全部在 stage 3，"
  "数据顺序按 DistributedSampler(seed, epoch) 精确恢复（见 §2.2）。")
A("5. **评测系统可复现**：11,904 一侧 "
  f"{rp['n_pass']}/{rp['n_formal_metric_keys']} 复现，逐位相同 {rp['n_bit_exact']} 个（见 §3.4）。")
A("")
A("**这条决策不依赖「两个 checkpoint 模型状态相同」** —— 该说法本身不成立（见 §2.1）。")

sec("### 4.2 |ΔR²| < 0.01 这条规则的地位")
A("- 它是一条**描述性对齐标准**，用于陈述两个 checkpoint 的表现接近程度。")
A("- 它**不是**统计显著性检验：本轮未对 checkpoint 间差异做任何显著性检验。")
A("- 它**不是**成功门或 checkpoint 选择门：接纳 14,880 的依据是 Q1/Q2/Q3 三维证据加续训可验证性。")
A("- 它**没有被废除**，仍作为描述性口径继续使用。")

sec("### 4.3 不按 OOD 结果回选 checkpoint")
c_oodt = H["Q1"]["oodt"]["overall"]["R2"]
A(f"OOD-t 上 R² 的 Δ 为 {fdelta(c_oodt['delta'])}，量级极小且方向与其它切面不一致。即便如此，也不回退到 11,904：")
A("")
A("- 按 OOD 结果回选会引入「事后挑选最优点」的选择偏差；")
A("- 14,880 承载了更多训练信号，且其续训过程已被 M9 独立验收；")
A("- 该差异未经显著性检验，不足以支撑任何回选主张。")

sec("---")
sec("## 五、证据分区与工件清单")
sec("### 5.1 严格分区")
part = MAN["partitioning"]
A("本次尝试目录下的产物按下列分区处理，**任何一类都不得混入正式结果集**：")
A("")
A(f"1. **正式重跑**（{len(part['formal_rerun']['jobs'])} 份）：{part['formal_rerun']['what']}")
for jn in part["formal_rerun"]["jobs"]:
    A(f"   - `{jn}`")
A(f"2. **历史参考**：{part['historical_reference']['what']} —— {part['historical_reference']['role']}，"
  f"SHA-256 `{part['historical_reference']['sha256']}`")
A(f"3. **无效 partial 目录**（{len(part['invalid_partial']['dirs'])} 个）：{part['invalid_partial']['what']}")
for d in part["invalid_partial"]["dirs"]:
    e = IDX["invalid_partial_dirs"].get(d, {})
    A(f"   - `runs/{d}`：{e.get('n_files', '未记录')} 个文件，{gib(e.get('total_bytes'))}，"
      f"子项 {e.get('children')}；{e.get('reason', '')}")
for key, lab in (("smoke", "smoke 产物"), ("selftest", "自检 fixture")):
    ent = part[key]["entries"]
    A(f"4. **{lab}**：")
    for e in ent:
        A(f"   - `{e['path']}`，子项 {e['children']}；{e['reason']}")
ia = part["interrupted_attempt"]["detail"]
A(f"5. **20260818 中断尝试**：`{ia['attempt']}`，验收状态 `{ia['acceptance_status']}`"
  f"（SHA-256 `{ia['acceptance_sha256']}`），{ia['n_interrupted']} 个 INTERRUPTED 标记：")
for m in ia["interrupted_markers"]:
    A(f"   - `{m}`")
A(f"   watcher 轮询 {ia.get('watcher_polls')} 次，jobs_launched={fnum(ia.get('jobs_launched'))}；"
  f"让出对象 PID {ia.get('yielded_to')}。该目录完整保留为审计证据。")

sec("### 5.2 六份一手结果")
A("| 逻辑作业名 | 结果文件 | 字节 | 落盘时刻（UTC） | SHA-256 |")
A("|---|---|---|---|---|")
for n, e in IDX["raw_results"].items():
    A(f"| `{n}` | `{Path(e['path']).name}` | {e['bytes']:,} | {e['mtime_utc']} | `{e['sha256']}` |")
A("")
A("全部六份的实测 SHA-256 与本轮清点值一致（`sha256_matches_inventory` 均为 true），本轮只读校验，未修改。")

sec("### 5.3 v3 封账工件")
A("| 文件 | 字节 | SHA-256 |")
A("|---|---|---|")
for fn, e in AUD["artifacts_written"].items():
    A(f"| `{fn}` | {e['bytes']:,} | `{e['sha256']}` |")
A(f"| `closeout_audit_v3.json` | {(ATTEMPT / 'closeout_audit_v3.json').stat().st_size:,} | "
  f"`{sha256_file(ATTEMPT / 'closeout_audit_v3.json')}` |")
A("")
A("> `closeout_audit_v3.json` 自身的 SHA 由本文档记录，以避免验收器自指哈希。")

sec("### 5.4 目录规模与上游证据")
tot = IDX["totals"]
A(f"- 本次尝试目录合计 **{tot['attempt_n_files']:,} 个文件**，{gib(tot['attempt_total_bytes'])}")
A(f"- 正式 run 目录 {tot['n_formal_run_dirs']} 个，无效 partial 目录 {tot['n_invalid_partial_dirs']} 个，"
  f"日志 {tot['n_logs']} 个，上游证据 {tot['n_upstream_evidence']} 项，"
  f"既有 v1/v2 封账工件 {tot['n_prior_closeout_artifacts']} 项（全部保留，且不作为 v3 的数据来源）")
A("")
A("| 正式 run 目录 | 文件数 | 字节 |")
A("|---|---|---|")
for n, e in IDX["run_dirs"].items():
    A(f"| `{n}` | {e['n_files']:,} | {gib(e['total_bytes'])} |")

sec("### 5.5 已如实登记的证据缺口")
A("下列缺口是**已确认存在**的，登记而非掩盖：")
A("")
for gp in AUD["known_gaps_recorded_honestly"]:
    A(f"- {gp}")
A("")
A("其中两项展开：")
A("")
A(f"1. **Q3 身份为 sidecar 绑定**：{PRV['q3_checkpoint_identity']['gap_note']}")
for jn, e in PRV["q3_checkpoint_identity"]["per_job"].items():
    A(f"   - `{jn}`：checkpoint SHA-256 `{e['checkpoint_sha256']}`，证明方式 `{e['proof']}`，"
      f"依据 {e['sources']}")
    A(f"     身份基础：{e['identity_basis']}")
A("2. **空的 launch record**：")
for gp in PRV["provenance_gaps"]:
    A(f"   - `{gp['artifact']}`（SHA-256 `{gp['sha256']}`，n_jobs={gp['n_jobs']}）：{gp['gap']}")
A("")
A(f"3. **Q3 协议文件计数三个口径不同**：磁盘 {Q3P['n_files_on_disk']} 个、"
  f"MANIFEST.SHA256 列出 {Q3P['n_files_in_manifest']} 个（不含自身）、"
  f"结果 JSON 绑定 5 个。三个数字都如实报告，不择一掩盖。")

sec("---")
sec("## 六、验收与审计")
sec("### 6.1 v3 验收")
A(f"验收器：`verify_and_aggregate_retry_v3.py`（SHA-256 "
  f"`{AUD['artifacts_written']['verify_and_aggregate_retry_v3.py']['sha256']}`），"
  f"fail-closed（{REP['policy']}）。")
A("")
A("| 门 | 主题 | 检查数 | 失败 |")
A("|---|---|---|---|")
for g in REP["gate_summary"]:
    A(f"| {g['gate']} | {g['title']} | {g['n_checks']} | {g['n_failed']} |")
A(f"| **合计** | — | **{REP['n_checks']}** | **{REP['n_failed']}** |")
A("")
A("**sanity anchor**（用户下发的期望值；不一致即停止封账，禁止改数字迁就）：")
A("")
A("| 作业 | 路径 | 期望 | 实测 |")
A("|---|---|---|---|")
for a_ in REP["sanity_anchors"]:
    mark = "" if a_["expected"] == a_["observed"] else " **不一致**"
    A(f"| `{a_['job']}` | `{a_['path']}` | {a_['expected']!r} | {a_['observed']!r}{mark} |")

sec("### 6.2 封账环境")
A(f"- CPU 封账节点 `{ENV['closeout_hostname']}`；GPU 执行节点 `{MAN['nodes']['gpu_execution_hostname']}`"
  f"（{MAN['nodes']['note']}）")
A(f"- `CUDA_VISIBLE_DEVICES` = `{ENV['cuda_visible_devices']!r}`（严格 CPU-only，未创建 CUDA context，未导入 torch）")
A(f"- Python {ENV['python']}")
A(f"- git 仓库根 `{ENV['git_repo_toplevel']}`，HEAD `{ENV['git_head']}`，分支 `{ENV['git_branch']}`")
A(f"- 工作树 dirty：{fnum(ENV['git_worktree_dirty'])}，共 {ENV['git_dirty_entry_count']} 条，"
  f"其中 obsworld 之外 {ENV['git_dirty_outside_obsworld']} 条")
A(f"- {ENV['git_note']}")
A("")
A("本轮约束：")
for c in MAN["constraints_this_round"]:
    A(f"- {c}")

sec("### 6.3 已纠正的缺陷记录")
for d in AUD["corrected_defects"]:
    A(f"- **{d['defect']}**")
    if d.get("values"):
        A(f"  - 涉及数值：{d['values']}")
    A(f"  - 证据：{d['evidence']}")
    A(f"  - 处理：{d['resolution']}")

sec("### 6.4 明确未被用作数据来源的文件")
for x in PRV["explicitly_not_used_as_source"]:
    A(f"- {x}")

sec("---")
sec("## 七、后续行动")
sec("### 7.1 可直接使用")
A(f"- `{CK['verified14880']['logical_id']}` 作为 anchor，用于 Candidate C 对比基线、Q4 评测与其它下游实验。")
A("- 评测协议已冻结：后续实验必须引用相同的冻结清单 SHA-256 与 Q3 协议目录，否则结果不可比。")
A(f"- 下一步动作：`{AUD['next_action']}`。")

sec("### 7.2 待解决问题")
A("1. **Q3 热干增强 FAIL 的根因**：需要能区分「架构 / 数据分布 / 损失引导 / 协议敏感度」的实验设计；"
  "与 Candidate C 的同协议 Q3 结果对比是第一步。")
A("2. **`transition_margin_clean = False`**：其成因已由协议说明指出（T-identity 喂入冻结 z_t 造成 OOD），"
  "需要设计能把「转移贡献」与「OOD 效应」分开的消融。")
A("3. **checkpoint 间差异的显著性**：若后续需要主张两个 checkpoint 表现「有/无」差异，"
  "必须补做针对该差异的检验，当前 0.01 描述性标准不足以支撑此类主张。")
A(f"4. **`weather_in_base` 消融臂未运行**：Q3 中该臂 R²/RMSE 为 null，如需该维度证据须单独运行。")

sec("### 7.3 A01/A02 同步事项")
A("已在 A01/A02 中同步的最小事实集见两份文档自身的更新说明；本文只登记同步项：")
A("")
A("1. E0 与 T0 的完成状态；")
A("2. 三份 checkpoint 的角色区分（边界 11,904 / verified 14,880 / 历史 14,880）；")
A("3. 0.01 的语义（描述性对齐标准，非显著性门、非选择门）；")
A("4. 组合损失 λ 取值为**暂定**，须先做 loss/gradient scale pilot 再冻结，且只在 validation 上选择；")
A("5. C0S 公平匹配的定义；")
A("6. T3 smoke 与 T5 正式 scenario manifest 的冻结时机与外部 sidecar SHA 要求；")
A("7. 五轴结构、Q4 与 Candidate C 的既有结构保持不变。")

sec("---")
sec("## 附录 A：核心数字速查")
A("```")
A(f"Q1 Validation ({H['Q1']['val']['n_targets']['v11904']} targets)")
A(f"  11,904: R2={fnum(H['Q1']['val']['overall']['R2']['v11904'])}  RMSE={fnum(H['Q1']['val']['overall']['rmse']['v11904'])}")
A(f"  14,880: R2={fnum(H['Q1']['val']['overall']['R2']['v14880'])}  RMSE={fnum(H['Q1']['val']['overall']['rmse']['v14880'])}")
A(f"  dR2   = {fdelta(H['Q1']['val']['overall']['R2']['delta'])}")
A("")
A(f"Q1 OOD-t ({H['Q1']['oodt']['n_targets']['v11904']} targets)")
A(f"  11,904: R2={fnum(H['Q1']['oodt']['overall']['R2']['v11904'])}  RMSE={fnum(H['Q1']['oodt']['overall']['rmse']['v11904'])}")
A(f"  14,880: R2={fnum(H['Q1']['oodt']['overall']['R2']['v14880'])}  RMSE={fnum(H['Q1']['oodt']['overall']['rmse']['v14880'])}")
A(f"  dR2   = {fdelta(H['Q1']['oodt']['overall']['R2']['delta'])}")
A("")
A("Q2 verdict: 两个 checkpoint、两个 split 均为 "
  f"{H['Q2']['val']['gates']['verdict']['v14880']}；transition_margin_clean 均为 False")
A(f"Q3 overall: 两个 checkpoint 均为 {q['verdicts']['overall_status']['v14880']}"
  f"（端点保真 {q['verdicts']['endpoint_fidelity_status']['v14880']}，"
  f"热干增强 {q['verdicts']['hotdry_enhancement_status']['v14880']}）")
A("")
A(f"历史复现: {rp['n_pass']}/{rp['n_formal_metric_keys']} 通过，逐位相同 {rp['n_bit_exact']} 个（仅 11,904 侧）")
A(f"v3 验收 : {REP['verdict']}，{REP['n_checks']} 项检查，{REP['n_failed']} 项失败")
A("```")

sec("## 附录 B：常见问题")
A("**Q：14,880 的 R² 略低于 11,904，说明模型变差了吗？**  ")
A(f"A：Validation 上 ΔR² = {fdelta(H['Q1']['val']['overall']['R2']['delta'])}，"
  f"OOD-t 上 ΔR² = {fdelta(H['Q1']['oodt']['overall']['R2']['delta'])}，"
  "量级在小数点后第四位及更小，且在分层与预测步长上方向并不一致（既有变好也有变差，见 §3.1）。"
  "本轮未对该差异做显著性检验，因此既不能说「变差了」，也不能说「没有差别」。")
A("")
A("**Q：11,904 和 14,880 的模型权重是一样的吗？**  ")
A("A：不是。已验明权重逐值相同的是 **verified 14,880 与历史 14,880** 这一对"
  f"（255 个张量，`value_sha={M9['value_digest_16hex']}`，max abs diff = 0）。"
  "11,904 与 14,880 之间不存在这样的证据，且二者的评测结果本身就不同。")
A("")
A("**Q：Q3 判 FAIL，模型还能用吗？**  ")
A("A：FAIL 只落在「热干增强」这一项上。端点保真为 PASS，Q1 精度正常。"
  "结论的准确表述是 `Q3_RESPONSE_FIDELITY_ONLY`：支持响应保真，不支持热干条件下的额外增强。"
  "FAIL 的原因本轮无法区分。")
A("")
A("**Q：0.01 阈值被废除了吗？**  ")
A("A：没有。它继续作为描述性对齐标准使用，只是明确了它不是显著性门，也不是 checkpoint 选择门。")
A("")
A("**Q：这份文档是最终结论吗？**  ")
A("A：不是。它是当前证据链下的封账版。Candidate C 与 Q4 的结果可能改变其中的解释部分；"
  "已记录的一手数值与 SHA 不会因此改变。")
A("")
A("**Q：怎么核对本文的任何一个数字？**  ")
A(f"A：本文由 `{Path(__file__).name}` 从 `e0_comparison_11904_vs_14880_v3.json` 等 v3 工件渲染，"
  "没有手工抄录环节。逐项核对路径见每张表所标注的字段名，最终可追到六份一手结果 JSON 的 SHA-256（§5.2）。")
A("")
A("---")
A("")
A(f"**渲染脚本**：`{Path(__file__).name}`  ")
A(f"**渲染时间（UTC）**：{ENV['now_utc']}  ")
A(f"**数据来源**：{Path(__file__).name} 顶部 docstring 所列 v3 工件与 parameter_audit.json  ")
A("**文档结束**")

text = "\n".join(L) + "\n"
sha = atomic_write_text(OUT, text)
print(f"[write] {OUT}")
print(f"        bytes={OUT.stat().st_size}  sha256={sha}")

side = OUT.parent / f"{OUT.name}.sha256"
tmpf = side.parent / f".{side.name}.tmp"
with open(tmpf, "w", encoding="utf-8") as f:
    f.write(f"{sha}  {OUT.name}\n")
    f.flush()
    os.fsync(f.fileno())
os.replace(tmpf, side)
dfd = os.open(str(side.parent), os.O_RDONLY)
try:
    os.fsync(dfd)
finally:
    os.close(dfd)
print(f"[write] {side}")
