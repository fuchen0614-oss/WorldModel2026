#!/usr/bin/env python
"""Candidate C Q4 评测器：composition / segment-transition 的 factual 技能与对照。

硬约束（与 A01 §8.3 / §8.5 一致）：
  * 严格加载：load_state_dict(strict=True)。绝不 strict=False，绝不容忍 missing/unexpected。
  * train-seen 与 held-out 分段完全分离，held-out 只在此处评测，训练侧从未见过。
  * 四个坏对照（shuffle 天气 / segment-mismatch / identity / constant）必须比 factual 更差，
    否则说明指标没有真正测到"状态承载 + 天气进入 F"这件事。
  * 逐 cube JSON + 原始数组 + provenance 全量落盘，聚合量可被独立重算。
  * 95% CI 用 minicube 级（可选 geo-cluster 级）bootstrap；不是显著性检验，是描述性区间。

本脚本只读 checkpoint 与数据，不写任何模型权重，不改任何 run。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset  # noqa: E402
from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.terrastate_candidate_c import (  # noqa: E402
    SIMULATOR_STATUS, TerraStateCandidateC, sha256_file, value_sha16,
)
from train.terrastate_v2_common import (  # noqa: E402
    canonical_json_sha256, collate_with_ids, relpath_of, to_device_with_ids,
)

# 四个坏对照的名字与 candidate_c_q4_partition_manifest_v1.json controls.generators 逐字一致。
CONTROLS = ("weather_order_shuffled", "segment_weather_mismatched",
            "identity_state", "constant_state")
CONTROL_SEED = 4242          # 冻结件 controls.seed，与训练 seed 42 刻意不同
BOOTSTRAP_B = 10000          # 冻结件 statistical_levels.ci_rule（Q4 四道门口径）
CI_ALPHA = 0.05
# 臂间比较（C1 vs C0R）走选择合同 candidate_c_selection_contract_v1.uncertainty：
#   method="minicube 级 geo-clustered bootstrap", n_resamples=2000,
#   cluster_unit="geo_group（tile）"
# 与 Q4 四道门的 minicube 配对口径**刻意不同**，两份冻结件各管一段：
#   * Q4 门是同一模型内 factual vs 坏对照的配对，同 tile 相关性在相减时抵消；
#   * 臂间比较是跨模型比较，tile 内相关性不抵消，按 minicube 独立重采样会把
#     区间做得虚假地窄（选择合同 rationale 原文）。
COMPARE_BOOTSTRAP_B = 2000
COMPARE_CLUSTER_UNIT = "geo_group(tile)"
# G_abs（A01 §8.5 / 选择合同）：事实端点非劣
EPS_R2 = 0.02                # LCB(ΔR²) >= -EPS_R2
EPS_RMSE = 0.05              # UCB(RMSE ratio) <= 1+EPS_RMSE
COMPOSED_VS_DIRECT_TOL = 0.05    # held-out composed MSE 不超过 direct 的 5%
RETENTION_MIN = 0.5             # std / effective-rank retention 下限

# ---------------------------------------------------------------- 逐 cube 资格
# 【口径变更记录 2026-08-24，必须连同理由一起读】
#
# 原实现只要求 `sst > 0`。这在云掩膜下不够：GreenEarthNet 的 NDVI 目标经过
# 云/阴影掩膜后，单个 (cube, combo) 可能只剩几十个甚至 2 个有效像素，而它在
# 476 个 cube 的等权平均里与剩 1600 个像素的 cube 权重完全相同。R²=1−SSE/SST
# 的分母是"待解释方差"，有效像素极少时 SST 由少数残留像素决定，R² 可取到
# −1e5 量级，单个 cube 即可支配全体均值。
#
# 判定轴的选择过程（不藏中间版本）：
#   v1 尝试 TARGET_STD_FLOOR = 1e-2（逐像素目标标准差下限）。它确实剔掉了
#      问题 cube，但被剔掉的两个 cube 分别只有 53 / 2 个有效像素，土地覆盖与
#      整体 NDVI 变异都正常（53 像素那个是 84% 农田、整段 NDVI std 0.235）。
#      也就是说 std 低是"云挡住后只剩少数相似像素"的**后果**，不是原因。
#      按后果设门限属于抓对现象、用错轴。
#   v2 改为 MIN_VALID_PIXELS = 64（有效像素数下限）= 当前口径。直接对因，
#      且门限稳健：见下方 sweep。
#
# 门限取值依据（先定轴再定值，不看结论）：
#   * 阈值 sweep（val_dev，C1 vs C0R compare 通过的 combo 数）：
#       n_valid≥0 → 2/19 ；≥32 → 2/19 ；≥64 → 7/19 ；≥128 → 7/19 ；
#       ≥512 → 7/19 ；≥1600 → 8/19
#     判定在 32→64 之间翻转，之后 64→1600 完全稳定。这条平台说明 64 落在
#     真实的"数据不够用"分界之后，而不是挑出来的幸运点。
#   * 量纲侧：单帧 128×128 = 16384 像素，全体有效像素中位数约 1600。64 是
#     中位数的 4%、单帧的 0.4%，是极宽松的下限，只切掉长尾。
#
# 该判据**不在任何冻结件中**（candidate_c_q4_partition_manifest_v1 /
# candidate_c_selection_contract_v1 / contract_freeze_receipt / A01 §8 均未
# 规定资格判据），原 `sst > 0` 是脚本实现选择而非预注册内容。因此这是填补
# 冻结件空白，不是改动已冻结判据。但它**改变了结论**（C1 在无门限下
# composed_vs_direct 不过、有门限下四门全过），所以：
#   1. 三个口径（无门限 / std≥1e-2 / n_valid≥64）全部并列落盘，任何一侧都不隐藏；
#   2. 代价明确记账：n_valid≥64 会排除约 44.7% 的 (cube, combo) 对，
#      这是云遮挡的普遍程度，不是少量异常；
#   3. 口径由人类决策者在看到三种结果后显式选定（2026-08-24），记录在
#      A05 §Q4 与 A04 Q4 结果条目中。
MIN_VALID_PIXELS = 64
TARGET_STD_FLOOR = 0.0          # v1 口径已停用；保留常量供敏感性分析显式传入
SENSITIVITY_STD_FLOOR = 1e-2    # 敏感性分析用的 v1 门限值

# 论文 Panel B 的逐 horizon 报告行。**只报告，不参与任何门**：预注册的
# state_retention 门用的是 ep20|10-10 的 cov_t/cov_ep，与此无关。
# 取值 = 冻结 manifest 里存在 direct（单段）组合的三个端点。模板草稿写的
# horizon 1/5/10/20 中的 1 和 5 在冻结件里没有对应组合，不能凭空补，
# 只能按实际预注册的 10/15/20 报告——差异在表注和 A05 中明说。
HORIZON_REPORT = (10, 15, 20)
class EvalError(RuntimeError):
    """评测器的致命错误。绝不降级为警告后继续。"""


# ------------------------------------------------------------------ 严格加载
def load_candidate_c_strict(ckpt_path, *, device="cpu"):
    """从 checkpoint 严格重建 Candidate C。

    硬约束：load_state_dict(strict=True)。任何 missing/unexpected key 一律抛错。
    绝不出现 strict=False，绝不 pop 掉对不上的 key 后继续——那会把"权重没装上"
    伪装成"评测跑通了"。
    """
    p = Path(ckpt_path)
    if not p.is_file():
        raise EvalError(f"checkpoint 不存在：{p}")
    ck = torch.load(str(p), map_location="cpu", weights_only=False)
    if "b4_state_dict" not in ck:
        raise EvalError(f"checkpoint 缺少 b4_state_dict，键为：{sorted(ck.keys())[:20]}")
    cfg = dict(ck.get("contract_cfg") or {})
    if not cfg:
        raise EvalError("checkpoint 缺少 contract_cfg，无法复现结构")
    arch = str(ck.get("arch", ""))
    if arch != TerraStateCandidateC.ARCH:
        raise EvalError(f"arch 不匹配：checkpoint={arch!r} 期望={TerraStateCandidateC.ARCH!r}")
    hp = contextformer6m_hparams(pvt_pretrained=False)
    model = TerraStateCandidateC(hp, contract_cfg=cfg)
    sd = ck["b4_state_dict"]
    missing, unexpected = model.load_state_dict(sd, strict=True)   # strict=True，返回空表
    if missing or unexpected:
        raise EvalError(f"strict 加载后仍有偏差 missing={list(missing)} unexpected={list(unexpected)}")
    model.to(device).eval()
    meta = {
        "ckpt_path": str(p.resolve()),
        "ckpt_file_sha256": sha256_file(p),
        "loaded_value_sha16": value_sha16(model.state_dict()),
        "ckpt_value_sha16": value_sha16(sd),
        "n_tensors_loaded": len(sd),
        "strict": True,
        "arch": arch,
        "route_version": str(ck.get("route_version", "")),
        "step": int(ck.get("step", -1)),
        "phase_step": int(ck.get("phase_step", -1)),
        "arm": str(ck.get("arm", "")),
        "factual_path": str(ck.get("factual_path", "")),
        "lambdas": dict(ck.get("lambdas") or {}),
        "completion_reason": str(ck.get("completion_reason", "")),
        "lineage": dict(ck.get("lineage") or {}),
        "sha": dict(ck.get("sha") or {}),
        "simulator_status": str(ck.get("simulator_status", SIMULATOR_STATUS)),
    }
    if meta["loaded_value_sha16"] != meta["ckpt_value_sha16"]:
        raise EvalError("装载后权重 value_sha16 与 checkpoint 不符，加载路径不可信")
    return model, ck, meta
# ------------------------------------------------------------------ split / 地理分组
def _dig(obj, dotted: str):
    """点选择器取值。取不到就抛 KeyError——绝不静默返回 None 后算出一个错数字。"""
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(f"选择器 {dotted!r} 在 {part!r} 处取不到")
        cur = cur[part]
    return cur


def geo_group_of(cube_id: str) -> str:
    """S2 tile ID。规则逐字来自冻结件 validation_subsplit.geo_group_definition：
    从 val cube 文件名 minicube_<i>_<TILE>_<lat>_<lon>.nc 提取；
    train 侧文件名形如 <TILE>/<TILE>_<dates>_<coords>.nc，取首段。"""
    base = os.path.basename(str(cube_id))
    stem = base[:-3] if base.endswith(".nc") else base
    parts = stem.split("_")
    if parts and parts[0] == "minicube" and len(parts) >= 3:
        return parts[2]
    head = str(cube_id).split("/")[0]
    if head and head != base:
        return head
    return parts[0] if parts else stem


def load_split_ids(manifest_path, selector: str, *, allow_locked: bool = False):
    """读冻结 split manifest 的 ID 列表。默认拒绝 val_locked / OOD / test。"""
    mp = Path(manifest_path)
    if not mp.is_file():
        raise EvalError(f"split manifest 不存在：{mp}")
    payload = json.loads(mp.read_text())
    low = selector.lower()
    if ("locked" in low or "ood" in low or "test" in low) and not allow_locked:
        raise EvalError(
            f"选择器 {selector!r} 指向锁定/OOD/test split。按 usage_contract："
            "val_locked 在 FORMAL_READY 写入前不打开，ood_t/test 禁止用于调参或 checkpoint 选择。"
            "确需开门须显式 --allow-locked 并在 STATUS 中登记。")
    ids = _dig(payload, selector)
    if not isinstance(ids, list) or not ids:
        raise EvalError(f"选择器 {selector!r} 未取到非空 ID 列表")
    dup = len(ids) - len(set(ids))
    if dup:
        raise EvalError(f"split ID 列表有 {dup} 个重复，配对重采样口径会被污染")
    return [str(x) for x in ids], payload


def subset_by_ids(ds, root, id_list, *, name="split"):
    """按冻结 ID 列表取子集。缺一个就抛错——评测集合必须与冻结件逐一对应。"""
    index = {relpath_of(fp, root): i for i, fp in enumerate(ds.filepaths)}
    missing, idxs = [], []
    for cid in id_list:
        j = index.get(cid)
        if j is None:
            missing.append(cid)
        else:
            idxs.append(j)
    if missing:
        raise EvalError(f"{name}: {len(missing)} 个冻结 ID 在 data-root 下找不到，"
                        f"前 3 个：{missing[:3]}")
    return Subset(ds, idxs), idxs
# ------------------------------------------------------------------ 四个坏对照
def shuffled_weather(u_future, horizon: int, *, seed: int = CONTROL_SEED):
    """weather_order_shuffled：在 target horizon 内对未来天气时间轴做固定种子置换。

    只打乱时间轴顺序，不换成别的 cube 的天气——破坏的是时序信息本身。
    """
    tl = int(u_future.shape[1])
    h = min(int(horizon), tl)
    g = torch.Generator(device="cpu").manual_seed(int(seed))
    perm = torch.randperm(h, generator=g).tolist()
    if perm == list(range(h)):                     # 恒等置换=对照退化
        return None, {"degenerate": True, "reason": "置换恰为恒等"}
    out = u_future.clone()
    out[:, :h] = u_future[:, perm]
    return out, {"degenerate": False, "perm": perm}


def mismatched_weather(u_future, partition):
    """segment_weather_mismatched：把第 k 段的天气子窗替换为另一段（k+1）的子窗，
    段边界完全不变。用环绕取索引保证子窗长度仍等于该段跨度。

    单段是结构性退化（真的没有『另一段』），整条 variant 不存在。
    但『错配后与原天气逐位相同』是**逐 cube** 的属性：某个 cube 在未来窗口内天气恒定
    时，换段等于没换，该 cube 对这条对照无信息量 —— 只能把**这些 cube** 标为不合格，
    不能因此丢掉整个 batch 乃至整条 arm 的数据（那会静默缩小 broken_control 的输入集）。
    """
    part = [int(s) for s in partition]
    if len(part) < 2:
        return None, {"degenerate": True, "reason": "单段没有『另一段』"}
    tl = int(u_future.shape[1])
    offs, cum = [], 0
    for s in part:
        offs.append(cum)
        cum += s
    out = u_future.clone()
    for k, span in enumerate(part):
        src = offs[(k + 1) % len(part)]
        idx = [(src + t) % tl for t in range(span)]
        out[:, offs[k]:offs[k] + span] = u_future[:, idx]
    h = min(cum, tl)
    feat_dims = tuple(range(1, out.dim()))
    changed = (out[:, :h] != u_future[:, :h]).any(dim=feat_dims)   # (B,) bool
    note = {"degenerate": False, "segment_offsets": offs,
            "cube_eligible": changed.detach().cpu().numpy().astype(bool),
            "n_cube_unchanged": int((~changed).sum().item())}
    if not bool(changed.any()):
        note["all_cubes_unchanged"] = True
    return out, note


def constant_state_like(z_t, *, seed: int = CONTROL_SEED):
    """constant_state：与输入无关的常数状态张量（同 dtype/device，逐行相同）。"""
    g = torch.Generator(device="cpu").manual_seed(int(seed) + 7)
    vec = torch.randn(1, int(z_t.shape[-1]), generator=g).to(
        dtype=z_t.dtype, device=z_t.device)
    return vec.expand_as(z_t).contiguous()
def masked_cube_stats(yhat, targ, valid):
    """逐 cube 充分统计量（只在 valid 像素上）：n, sse, sum_y, sum_y2。

    保留 batch 维度 —— 先算 per-cube，再按单位聚合。绝不先把像素池化再配对
    （冻结件 statistical_levels.aggregation 明文禁止）。
    """
    diff2 = ((targ - yhat) ** 2) * valid
    n = valid.sum(dim=(1, 2, 3))
    sse = diff2.sum(dim=(1, 2, 3))
    sy = (targ * valid).sum(dim=(1, 2, 3))
    sy2 = ((targ ** 2) * valid).sum(dim=(1, 2, 3))
    return n, sse, sy, sy2


def path_gaps(model, prior, z_t, geo, u_future, partition, B, H, W):
    """A01 §8.4「路径一致」：composed 与 direct 两条路径的差距，逐 cube。

    delta_z = ||z_composed − z_direct|| / ||z_direct||   （latent path distance）
    delta_y = RMSE(ŷ_composed, ŷ_direct)                  （output path gap）

    两条路径的**端点时刻相同**（sum(partition) == h），差别只在中间是否落地重启。
    单段 partition 与 direct 逐位相同，delta 恒为 0，是语义正确的（半群律的
    一段情形），因此照常返回 0 而不是标退化。
    """
    h = int(sum(int(s) for s in partition))
    direct = (h,)
    z_c = model.segment_state(z_t, u_future, geo, partition)
    z_d = model.segment_state(z_t, u_future, geo, direct)
    zc = z_c.detach().reshape(int(B), -1).to(torch.float64)
    zd = z_d.detach().reshape(int(B), -1).to(torch.float64)
    num = torch.linalg.vector_norm(zc - zd, dim=1)
    den = torch.linalg.vector_norm(zd, dim=1).clamp_min(1e-12)
    dz = (num / den).cpu().numpy()
    ep = model.endpoint_prediction
    y_c = ep(prior, z_t, u_future, geo, partition, B, H, W, arm="full")
    y_d = ep(prior, z_t, u_future, geo, direct, B, H, W, arm="full")
    d = (y_c[:, 0:1] - y_d[:, 0:1]).detach().to(torch.float64)
    dy = torch.sqrt((d ** 2).mean(dim=tuple(range(1, d.dim())))).cpu().numpy()
    return dz, dy


def broken_path_gap(model, prior, z_t, geo, u_future, partition, B, H, W,
                    *, seed: int = CONTROL_SEED):
    """delta_y^broken：坏路径（错配段天气）的 composed-vs-direct 输出差距。

    A_comp = delta_y^broken − delta_y（模板 Panel A 的最后一列）。
    返回 (dy_broken, cube_eligible)；单段无法错配时返回 (None, None)。
    """
    u_mm, note = mismatched_weather(u_future, partition)
    if u_mm is None:
        return None, None
    h = int(sum(int(s) for s in partition))
    ep = model.endpoint_prediction
    y_cb = ep(prior, z_t, u_mm, geo, partition, B, H, W, arm="full")
    y_db = ep(prior, z_t, u_mm, geo, (h,), B, H, W, arm="full")
    d = (y_cb[:, 0:1] - y_db[:, 0:1]).detach().to(torch.float64)
    dy = torch.sqrt((d ** 2).mean(dim=tuple(range(1, d.dim())))).cpu().numpy()
    return dy, note.get("cube_eligible")


def variant_predictions(model, prior, z_t, geo, u_future, partition, B, H, W,
                        *, seed: int = CONTROL_SEED):
    """一个 (endpoint, partition) 上的 factual + 4 坏对照 + alpha0 诊断臂。

    identity_state 用 arm='T_identity'（转移算子换恒等）；
    constant_state 把**状态**换成与输入无关的常数后仍走真实 F。
    两者分别对应冻结件里那两条不同的 rule，不可混为一谈。
    """
    out, notes = {}, {}
    h = int(sum(int(s) for s in partition))
    ep = model.endpoint_prediction
    out["factual"] = ep(prior, z_t, u_future, geo, partition, B, H, W, arm="full")
    out["alpha0"] = ep(prior, z_t, u_future, geo, partition, B, H, W, arm="alpha0")
    out["identity_state"] = ep(prior, z_t, u_future, geo, partition, B, H, W,
                               arm="T_identity")
    out["constant_state"] = ep(prior, constant_state_like(z_t, seed=seed), u_future,
                               geo, partition, B, H, W, arm="full")
    u_sh, notes["weather_order_shuffled"] = shuffled_weather(u_future, h, seed=seed)
    if u_sh is not None:
        out["weather_order_shuffled"] = ep(prior, z_t, u_sh, geo, partition, B, H, W,
                                           arm="full")
    u_mm, notes["segment_weather_mismatched"] = mismatched_weather(u_future, partition)
    if u_mm is not None:
        out["segment_weather_mismatched"] = ep(prior, z_t, u_mm, geo, partition,
                                               B, H, W, arm="full")
    return out, notes


def partition_plan(model):
    """每个端点的评测分段表：direct (h,) + train-seen 多段 + held-out 多段。

    held-out 分段只在此处出现；训练侧从未见过（模型构造时已断言两表不相交）。
    """
    plan = []
    for ep in model.FACTUAL_ENDPOINTS:
        seen = [tuple(int(s) for s in p) for p in model.cc_train_partitions[int(ep)]]
        held = [tuple(int(s) for s in p) for p in model.cc_heldout_partitions[int(ep)]]
        for p in seen:
            plan.append((int(ep), p, "direct" if len(p) == 1 else "train_seen"))
        for p in held:
            plan.append((int(ep), p, "heldout"))
    return plan
def combo_key(ep: int, partition) -> str:
    return f"ep{int(ep)}|" + "-".join(str(int(s)) for s in partition)


class StatGrid:
    """(endpoint, partition, variant) -> 逐 cube 充分统计量。

    每个 series 的 cube 顺序都等于 dataloader 顺序，因此可以按 cube 严格配对。
    """

    def __init__(self):
        self.series = {}          # key -> {"n":[],"sse":[],"sy":[],"sy2":[],"cube_elig":[]}
        self.cube_ids = []
        self.degenerate = {}      # (combo, variant) -> note（结构性缺失，整条不存在）
        self.partial = {}         # (combo, variant) -> 逐 cube 不合格记录
        self.paths = {}           # combo -> {"dz":[],"dy":[],"dy_broken":[],"bk_elig":[]}

    def add(self, ep, partition, variant, n, sse, sy, sy2, cube_elig=None):
        """追加一个 batch 的逐 cube 统计量。

        cube_elig 是该 variant 在这批 cube 上是否构成有效对照的掩码（None = 全部有效）。
        无论合格与否都要 append，series 长度恒等于 cube 数 —— 配对契约靠长度守住，
        合格性靠掩码表达，两件事不能混用同一个机制。
        """
        k = (combo_key(ep, partition), str(variant))
        d = self.series.setdefault(k, {"n": [], "sse": [], "sy": [], "sy2": [],
                                       "cube_elig": []})
        d["n"].extend(n.tolist())
        d["sse"].extend(sse.tolist())
        d["sy"].extend(sy.tolist())
        d["sy2"].extend(sy2.tolist())
        b = int(n.shape[0])
        if cube_elig is None:
            d["cube_elig"].extend([1.0] * b)
        else:
            m = np.asarray(cube_elig, dtype=bool).reshape(-1)
            if m.shape[0] != b:
                raise EvalError(f"{k}: cube_elig 长度 {m.shape[0]} != batch {b}")
            d["cube_elig"].extend(m.astype(np.float64).tolist())

    def add_paths(self, ep, partition, dz, dy, dy_broken=None, bk_elig=None):
        """逐 cube 路径量（A01 §8.4）。长度契约同 series。"""
        c = combo_key(ep, partition)
        d = self.paths.setdefault(c, {"dz": [], "dy": [], "dy_broken": [],
                                      "bk_elig": []})
        d["dz"].extend(np.asarray(dz, dtype=np.float64).tolist())
        d["dy"].extend(np.asarray(dy, dtype=np.float64).tolist())
        b = int(np.asarray(dz).shape[0])
        if dy_broken is None:
            d["dy_broken"].extend([np.nan] * b)
            d["bk_elig"].extend([0.0] * b)
        else:
            d["dy_broken"].extend(np.asarray(dy_broken, dtype=np.float64).tolist())
            m = (np.ones(b, dtype=bool) if bk_elig is None
                 else np.asarray(bk_elig, dtype=bool).reshape(-1))
            d["bk_elig"].extend(m.astype(np.float64).tolist())

    def mark_degenerate(self, ep, partition, variant, note):
        self.degenerate[(combo_key(ep, partition), str(variant))] = dict(note)

    def note_partial(self, ep, partition, variant, note, cube_ids):
        """记录哪些 cube 在这条 variant 上不构成有效对照（留证据，不丢数据）。"""
        k = (combo_key(ep, partition), str(variant))
        m = np.asarray(note.get("cube_eligible"), dtype=bool).reshape(-1)
        bad_ids = [cube_ids[i] for i in range(min(len(cube_ids), m.shape[0])) if not m[i]]
        rec = self.partial.setdefault(k, {"reason": "错配后与原天气逐位相同",
                                          "n_cube_ineligible": 0, "cube_ids": []})
        rec["n_cube_ineligible"] += len(bad_ids)
        rec["cube_ids"].extend(bad_ids)

    def finalize(self):
        n_cubes = len(self.cube_ids)
        bad = {f"{k[0]}::{k[1]}": len(v["n"]) for k, v in self.series.items()
               if len(v["n"]) != n_cubes}
        if bad:
            raise EvalError(f"series 长度与 cube 数 {n_cubes} 不一致，配对口径已坏：{bad}")
        return {f"{k[0]}::{k[1]}": {kk: np.asarray(vv, dtype=np.float64)
                                    for kk, vv in v.items()}
                for k, v in self.series.items()}


class CovAccum:
    """流式协方差累积，用于整个 split 的 effective rank（不需要留住全部 token）。"""

    def __init__(self, dim):
        self.dim = int(dim)
        self.n = 0
        self.s1 = np.zeros(self.dim, dtype=np.float64)
        self.s2 = np.zeros((self.dim, self.dim), dtype=np.float64)

    def update(self, z):
        x = z.reshape(-1, z.shape[-1]).detach().to(torch.float64).cpu().numpy()
        self.n += x.shape[0]
        self.s1 += x.sum(axis=0)
        self.s2 += x.T @ x

    def effective_rank(self):
        if self.n < 2:
            return float("nan")
        mu = self.s1 / self.n
        cov = (self.s2 - self.n * np.outer(mu, mu)) / (self.n - 1)
        ev = np.clip(np.linalg.eigvalsh(cov), 0.0, None)
        return float(ev.sum() ** 2 / (np.square(ev).sum() + 1e-12))

    def mean_std(self):
        if self.n < 2:
            return float("nan")
        mu = self.s1 / self.n
        var = np.clip(np.diag(self.s2) / self.n - mu ** 2, 0.0, None) * self.n / (self.n - 1)
        return float(np.sqrt(var).mean())
# ------------------------------------------------------------------ provenance
SOURCE_FILES = (
    "eval/eval_terrastate_candidate_c_q4.py",
    "models/terrastate_candidate_c.py",
    "models/terrastate_v2.py",
    "models/plan_b_b4_exclusive.py",
    "models/plan_b_b4.py",
    "train/terrastate_v2_common.py",
    "data/greenearthnet_contextformer_dataset.py",
)


def _git(*a):
    import subprocess
    try:
        return subprocess.run(["git", *a], cwd=str(ROOT), capture_output=True,
                              text=True, timeout=60).stdout.strip()
    except Exception as e:                                   # noqa: BLE001
        return f"<git unavailable: {e}>"


def provenance(extra=None) -> dict:
    import platform
    src = {}
    for rel in SOURCE_FILES:
        p = ROOT / rel
        src[rel] = sha256_file(p) if p.is_file() else "<missing>"
    prov = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hostname": platform.node(),
        "cwd": os.getcwd(),
        "repo_root": str(ROOT),
        "argv": list(sys.argv),
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "torch": torch.__version__,
        "numpy": np.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "<unset>"),
        "git_head": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "source_sha256": src,
        "control_seed": CONTROL_SEED,
        "bootstrap_B": BOOTSTRAP_B,
        "simulator_status": SIMULATOR_STATUS,
        "gate_constants": {"eps_r2": EPS_R2, "eps_rmse": EPS_RMSE,
                           "composed_vs_direct_tol": COMPOSED_VS_DIRECT_TOL,
                           "retention_min": RETENTION_MIN},
    }
    if extra:
        prov.update(extra)
    return prov
# ------------------------------------------------------------------ 结构性检查
@torch.no_grad()
def structural_checks(model, prior, z_t, geo, u_future, B, H, W) -> dict:
    """semigroup 一致性 + 中途换天气契约 + 非坍缩门。

    这些是"机制真的成立"的检查，与技能指标分开报。任一失败都要显式登记，
    绝不因为数字好看就放过。
    """
    out = {}
    # (1) 1 段 == direct_state；2 段 == composed_state（必须逐位相同）
    z1 = model.segment_state(z_t, u_future, geo, (10,))
    zd = model.direct_state(z_t, u_future, geo, 10)
    z2 = model.segment_state(z_t, u_future, geo, (5, 5))
    zc = model.composed_state(z_t, u_future, geo, 5, 5)
    out["semigroup"] = {
        "one_segment_equals_direct": bool(torch.equal(z1, zd)),
        "one_segment_max_abs_delta": float((z1 - zd).abs().max()),
        "two_segment_equals_composed": bool(torch.equal(z2, zc)),
        "two_segment_max_abs_delta": float((z2 - zc).abs().max()),
    }
    # (2) 多段 vs 直接：必须**非平凡地**不同，否则递归路径等于没接上
    z3 = model.segment_state(z_t, u_future, geo, (5, 3, 2))
    out["recursive_nontrivial"] = {
        "three_segment_differs_from_direct": bool(not torch.equal(z3, zd)),
        "max_abs_delta_vs_direct": float((z3 - zd).abs().max()),
    }
    # (3) 中途换天气：前段逐位不变，后段必须变
    out["weather_switch"] = model.assert_weather_switch_contract(
        z_t, u_future, geo, (5, 3, 2), switch_after_segment=1,
        generator=torch.Generator(device="cpu").manual_seed(CONTROL_SEED))
    # (4) 非坍缩门 + 状态保持率
    z_ep = model.segment_state(z_t, u_future, geo, (10, 10))
    out["noncollapse_gate"] = model.noncollapse_gate(z_t, z_ep)
    diag = model.state_diagnostics(z_t, z_ep)
    std_ret = diag["state_std_zep"] / max(diag["state_std_zt"], 1e-12)
    rank_ret = diag["effective_rank_zep"] / max(diag["effective_rank_zt"], 1e-12)
    out["state_diagnostics"] = diag
    out["retention"] = {
        "std_retention": float(std_ret),
        "effective_rank_retention": float(rank_ret),
        "retention_min": RETENTION_MIN,
        "passes": bool(std_ret >= RETENTION_MIN and rank_ret >= RETENTION_MIN),
    }
    # (5) 坏对照的状态确实被非坍缩门拦下（常数状态必须 FAIL）
    z_const = constant_state_like(z_t)
    out["constant_state_caught_by_gate"] = model.noncollapse_gate(z_const, z_const)
    return out
# ------------------------------------------------------------------ bootstrap
def bootstrap_weights(n: int, B: int = BOOTSTRAP_B, seed: int = CONTROL_SEED):
    """multinomial 计数矩阵 (B, n)：每行等价于"对 n 个 cube 有放回重采样 n 次"。

    所有配对比较共用同一个 W —— factual 与坏对照必须落在**同一次**重采样上，
    否则"配对"只是名义上的。加权均值与逐个 gather 重采样在数学上等价。
    """
    if n < 2:
        raise EvalError(f"可用 cube 数 {n} < 2，无法 bootstrap")
    rng = np.random.default_rng(int(seed))
    return rng.multinomial(n, np.full(n, 1.0 / n), size=int(B)).astype(np.float64)


def ci_from_draws(draws) -> tuple:
    """95% percentile bootstrap CI（冻结件 ci_rule）。"""
    d = np.asarray(draws, dtype=np.float64)
    d = d[np.isfinite(d)]
    if d.size == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(d, [100 * CI_ALPHA / 2, 100 * (1 - CI_ALPHA / 2)])
    return float(lo), float(hi)


def per_cube_metrics(s, *, min_valid: int = MIN_VALID_PIXELS,
                     std_floor: float = TARGET_STD_FLOOR):
    """逐 cube MSE / R² / SST / 可用标记。

    n_valid 与 SST 只依赖数据（掩膜、真值），与哪个 variant 无关，
    因此同一 combo 下所有 variant 的可用 cube 集合天然相同 —— 配对是严格的。

    min_valid 是有效像素数下限（当前口径，见 MIN_VALID_PIXELS 的变更记录）。
    std_floor 是已停用的 v1 口径，默认 0.0；显式传 1e-2 可复现 v1 用于敏感性分析。
    两者都传 0 / 1 即回到原始 `sst > 0` 口径。
    """
    n = s["n"]
    nz = np.maximum(n, 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        mse = np.where(n > 0, s["sse"] / nz, np.nan)
        sst = s["sy2"] - np.square(s["sy"]) / nz
        r2 = np.where(sst > 0, 1.0 - s["sse"] / np.where(sst > 0, sst, 1.0), np.nan)
        tstd = np.sqrt(np.maximum(sst, 0.0) / nz)      # 逐像素目标标准差
    eligible = (n >= float(min_valid)) & (sst > 0) & np.isfinite(mse)
    if float(std_floor) > 0.0:
        eligible = eligible & (tstd >= float(std_floor))
    return mse, r2, sst, eligible


def _variant_elig(s):
    """该 variant 自身的逐 cube 对照有效性掩码（缺字段 = 全部有效，向后兼容旧 npz）。"""
    ce = s.get("cube_elig")
    if ce is None:
        return np.ones(s["n"].shape[0], dtype=bool)
    return np.asarray(ce, dtype=np.float64) > 0.5


def _pooled_mse_on(s, mask):
    """在给定 cube 子集上的 pooled MSE（先按像素求和再作比）。"""
    m = mask.astype(np.float64)
    n = float((s["n"] * m).sum())
    sse = float((s["sse"] * m).sum())
    return sse / n if n > 0 else float("nan")


def wmean(W, vals, mask):
    """加权（bootstrap）均值，只在 mask 内。返回 (B,) 抽样分布。"""
    v = np.where(mask, np.nan_to_num(vals, nan=0.0), 0.0)
    m = mask.astype(np.float64)
    num = W @ v
    den = W @ m
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)


def wpooled(W, s, mask):
    """加权 pooled MSE / R²（先按像素求和再作比，作为次要口径）。"""
    m = mask.astype(np.float64)
    n = W @ (s["n"] * m)
    sse = W @ (s["sse"] * m)
    sy = W @ (s["sy"] * m)
    sy2 = W @ (s["sy2"] * m)
    with np.errstate(divide="ignore", invalid="ignore"):
        mse = np.where(n > 0, sse / np.maximum(n, 1e-12), np.nan)
        sst = sy2 - np.square(sy) / np.maximum(n, 1e-12)
        r2 = np.where(sst > 0, 1.0 - sse / np.where(sst > 0, sst, 1.0), np.nan)
    return mse, r2
# ------------------------------------------------------------------ 打分主循环
def per_cube_state_stats(z, B):
    """cube-major 布局 (B·reps, dim) -> 每个 cube 的 std（跨该 cube 的 patch token）。"""
    zz = z.detach().reshape(int(B), -1, z.shape[-1]).to(torch.float64)
    std = zz.std(dim=1).mean(dim=1)                     # (B,)
    return std.cpu().numpy()


@torch.no_grad()
def score_checkpoint(args, dataset_factory=None) -> dict:
    """dataset_factory 仅供 CPU 测试注入合成 cube；正式评测一律走真实数据集。"""
    dev = torch.device(args.device)
    model, ck, meta = load_candidate_c_strict(args.ckpt, device=dev)
    ids, split_payload = load_split_ids(args.split_manifest, args.split_selector,
                                        allow_locked=bool(args.allow_locked))
    root = args.data_root
    ds = (dataset_factory(root) if dataset_factory is not None
          else GreenEarthNetContextformerDataset(root, dl_cloudmask=True))
    sub, idxs = subset_by_ids(ds, root, ids, name=args.split_selector)
    if args.max_cubes and args.max_cubes > 0:
        sub = Subset(sub, list(range(min(int(args.max_cubes), len(sub)))))
    loader = DataLoader(sub, batch_size=args.batch_size, shuffle=False,
                        num_workers=args.num_workers, collate_fn=collate_with_ids)
    plan = partition_plan(model)
    grid, cov_t, cov_ep = StatGrid(), None, None
    cl, tl = model.context_len, model.target_len
    struct, state_rows = None, []
    for bi, batch in enumerate(loader):
        data = to_device_with_ids(batch, dev)
        pred, prior, residual, z_t, geo, u_future = model.forecast(data, want_parts=True)
        B, H, W = pred.shape[0], pred.shape[-2], pred.shape[-1]
        cube_ids = [relpath_of(fp, root) for fp in data["filepath"]]
        grid.cube_ids.extend(cube_ids)
        lc = data["landcover"]
        lc_mask = ((lc >= model.lc_min) & (lc <= model.lc_max)).type_as(pred)   # (B,1,H,W)
        if bi == 0:
            struct = structural_checks(model, prior, z_t, geo, u_future, B, H, W)
            cov_t = CovAccum(z_t.shape[-1])
            cov_ep = CovAccum(z_t.shape[-1])
            # 逐 horizon 的状态统计（**仅报告**，不参与任何门）。
            # 预注册的 state_retention 门只用 cov_t / cov_ep（ep20|10-10），这里
            # 另起累加器给论文 Panel B 的逐 horizon 行，绝不改动门的输入。
            hz_cov = {int(e): CovAccum(z_t.shape[-1]) for e in HORIZON_REPORT}
            hz_move = {int(e): [] for e in HORIZON_REPORT}
        cov_t.update(z_t)
        std_t = per_cube_state_stats(z_t, B)
        for ep, part, tag in plan:
            h = int(sum(part))
            targ = data["dynamic"][0][:, cl + h - 1, 0:1]                        # (B,1,H,W)
            cloud = (data["dynamic_mask"][0][:, cl + h - 1] < 1.0).type_as(pred)  # (B,1,H,W)
            valid = cloud * lc_mask
            preds, notes = variant_predictions(model, prior, z_t, geo, u_future,
                                               part, B, H, W, seed=CONTROL_SEED)
            for vname, note in notes.items():
                if note.get("degenerate"):
                    grid.mark_degenerate(ep, part, vname, note)
                elif int(note.get("n_cube_unchanged", 0)) > 0:
                    grid.note_partial(ep, part, vname, note, cube_ids)
            for vname, yh in preds.items():
                n, sse, sy, sy2 = masked_cube_stats(yh[:, 0:1], targ, valid)
                grid.add(ep, part, vname, n, sse, sy, sy2,
                         cube_elig=notes.get(vname, {}).get("cube_eligible"))
            dz, dy = path_gaps(model, prior, z_t, geo, u_future, part, B, H, W)
            dyb, bke = broken_path_gap(model, prior, z_t, geo, u_future, part,
                                       B, H, W, seed=CONTROL_SEED)
            grid.add_paths(ep, part, dz, dy, dyb, bke)
            if tag == "train_seen" and len(part) == 2 and ep == 20:
                z_ep = model.segment_state(z_t, u_future, geo, part)
                cov_ep.update(z_ep)
                for i, cid in enumerate(cube_ids):
                    state_rows.append({"cube_id": cid, "geo_group": geo_group_of(cid),
                                       "state_std_zt": float(std_t[i])})
            # Panel B 报告量：direct 查询（单段）在各 horizon 上的状态统计
            if tag == "direct" and int(ep) in hz_cov:
                z_h = model.segment_state(z_t, u_future, geo, part)
                hz_cov[int(ep)].update(z_h)
                hz_move[int(ep)].append(float(model.state_movement(z_t, z_h)))
        if args.max_batches and bi + 1 >= int(args.max_batches):
            break
    return _finish_scoring(args, model, ck, meta, ids, split_payload, grid, struct,
                           cov_t, cov_ep, state_rows, plan, root,
                           horizon_state=_horizon_state_block(cov_t, hz_cov, hz_move))
# ------------------------------------------------------------------ 聚合与 Q4 判据
def _key(combo, variant):
    return f"{combo}::{variant}"


def _combo_table(plan):
    combos, seen = [], set()
    for ep, part, tag in plan:
        c = combo_key(ep, part)
        if c not in seen:
            combos.append({"combo": c, "endpoint": int(ep),
                           "partition": [int(s) for s in part], "tag": tag,
                           "n_segments": len(part)})
            seen.add(c)
    return combos


def _variant_block(W, s, elig):
    """一个 variant 的点估计 + 95% CI（primary=per-cube 配对；pooled 为次要口径）。"""
    mse, r2, _sst, _e = per_cube_metrics(s)
    d_mse = wmean(W, mse, elig)
    d_r2 = wmean(W, r2, elig)
    p_mse, p_r2 = wpooled(W, s, elig)
    m = elig.astype(np.float64)
    n_tot = float((s["n"] * m).sum())
    sse_tot = float((s["sse"] * m).sum())
    sy_tot = float((s["sy"] * m).sum())
    sy2_tot = float((s["sy2"] * m).sum())
    pooled_mse = sse_tot / max(n_tot, 1e-12)
    sst_tot = sy2_tot - sy_tot ** 2 / max(n_tot, 1e-12)
    lo_m, hi_m = ci_from_draws(d_mse)
    lo_r, hi_r = ci_from_draws(d_r2)
    lo_pm, hi_pm = ci_from_draws(p_mse)
    lo_pr, hi_pr = ci_from_draws(p_r2)
    return {
        "per_cube_mse_mean": float(np.nanmean(np.where(elig, mse, np.nan))),
        "per_cube_mse_ci95": [lo_m, hi_m],
        "per_cube_r2_mean": float(np.nanmean(np.where(elig, r2, np.nan))),
        "per_cube_r2_ci95": [lo_r, hi_r],
        "pooled_mse": float(pooled_mse),
        "pooled_mse_ci95": [lo_pm, hi_pm],
        "pooled_rmse": float(np.sqrt(pooled_mse)),
        "pooled_r2": float(1.0 - sse_tot / sst_tot) if sst_tot > 0 else float("nan"),
        "pooled_r2_ci95": [lo_pr, hi_pr],
        "n_valid_pixels": n_tot,
        "sse": sse_tot, "sst": float(sst_tot),
    }
def _paths_block(W, p, elig):
    """路径量聚合（模板 Panel A 的 delta_z / delta_y / delta_y^broken / A_comp）。"""
    dz = np.asarray(p["dz"], dtype=np.float64)
    dy = np.asarray(p["dy"], dtype=np.float64)
    dyb = np.asarray(p["dy_broken"], dtype=np.float64)
    bke = np.asarray(p["bk_elig"], dtype=np.float64) > 0.5
    out = {}
    for nm, v in (("delta_z", dz), ("delta_y", dy)):
        m = elig & np.isfinite(v)
        lo, hi = ci_from_draws(wmean(W, v, m))
        out[nm] = {"mean": float(np.nanmean(np.where(m, v, np.nan))),
                   "ci95": [lo, hi], "n_cubes": int(m.sum())}
    mb = elig & bke & np.isfinite(dyb) & np.isfinite(dy)
    if int(mb.sum()) >= 2:
        lo, hi = ci_from_draws(wmean(W, dyb, mb))
        out["delta_y_broken"] = {"mean": float(np.nanmean(np.where(mb, dyb, np.nan))),
                                 "ci95": [lo, hi], "n_cubes": int(mb.sum())}
        a = dyb - dy                      # A_comp = gap_broken − gap_real
        lo, hi = ci_from_draws(wmean(W, a, mb))
        out["a_comp_path"] = {"mean": float(np.nanmean(np.where(mb, a, np.nan))),
                              "ci95": [lo, hi], "lcb_gt_0": bool(lo > 0),
                              "n_cubes": int(mb.sum())}
    else:
        out["delta_y_broken"] = {"degenerate": True,
                                 "reason": "单段无法错配，或无合格 cube"}
    return out


def aggregate(series, cube_ids, combos, degenerate, *, seed=CONTROL_SEED, paths=None):
    """按冻结件口径聚合：primary = per-minicube 配对 percentile bootstrap。"""
    n_cubes = len(cube_ids)
    W = bootstrap_weights(n_cubes, BOOTSTRAP_B, seed)
    per_combo, a_comp_cols, ratio_rows = {}, [], []
    for c in combos:
        combo = c["combo"]
        fk = _key(combo, "factual")
        if fk not in series:
            raise EvalError(f"缺少 factual series：{fk}")
        _m, _r, _s, elig = per_cube_metrics(series[fk])
        block = {"meta": c, "n_eligible_cubes": int(elig.sum()),
                 "variants": {}, "controls": {}, "degenerate": {}}
        for variant in ("factual", "alpha0", *CONTROLS):
            k = _key(combo, variant)
            if k not in series:
                note = degenerate.get((combo, variant))
                block["degenerate"][variant] = note or {"degenerate": True,
                                                        "reason": "未产出该 variant"}
                continue
            # 数据可用性（elig，与 variant 无关）∩ 该 variant 自身的对照有效性
            vm = elig & _variant_elig(series[k])
            block["variants"][variant] = _variant_block(W, series[k], vm)
            if int(vm.sum()) != int(elig.sum()):
                block["variants"][variant]["n_cubes_ineligible_for_variant"] = \
                    int(elig.sum()) - int(vm.sum())
        f_mse, _r2, _sst, _e = per_cube_metrics(series[fk])
        for variant in (*CONTROLS, "alpha0"):
            k = _key(combo, variant)
            if k not in series:
                continue
            c_mse, _cr2, _cs, _ce = per_cube_metrics(series[k])
            # 配对必须在两边都合格的 cube 上做；掩码是逐 cube 的，长度恒为 n_cubes
            pm = elig & _variant_elig(series[k])
            delta = c_mse - f_mse                       # >0 == factual 更好
            draws = wmean(W, delta, pm)
            lo, hi = ci_from_draws(draws)
            # 比值的分子分母必须落在同一批 cube 上，否则不是同一个总体的比
            pf = _pooled_mse_on(series[fk], pm)
            pc = _pooled_mse_on(series[k], pm)
            ratio = pf / pc if pc > 0 else float("nan")
            block["controls"][variant] = {
                "a_comp_per_cube_mean": float(np.nanmean(np.where(pm, delta, np.nan))),
                "a_comp_ci95": [lo, hi],
                "a_comp_lcb_gt_0": bool(lo > 0),
                "pooled_mse_ratio_factual_over_control": float(ratio),
                "ratio_lt_1": bool(np.isfinite(ratio) and ratio < 1.0),
                "n_paired_cubes": int(pm.sum()),
            }
            if variant in CONTROLS:
                a_comp_cols.append(np.where(pm, delta, np.nan))
                ratio_rows.append({"combo": combo, "control": variant,
                                   "ratio": float(ratio),
                                   "ratio_lt_1": bool(np.isfinite(ratio) and ratio < 1.0)})
        if paths and combo in paths:
            block["paths"] = _paths_block(W, paths[combo], elig)
        per_combo[combo] = block
    return W, per_combo, a_comp_cols, ratio_rows, n_cubes
def geo_cluster_weights(cube_ids, *, B=BOOTSTRAP_B, seed=CONTROL_SEED):
    """按 S2 tile 重采样的权重矩阵（敏感性分析口径，不替代 per-minicube primary）。"""
    groups = [geo_group_of(c) for c in cube_ids]
    tiles = sorted(set(groups))
    if len(tiles) < 2:
        return None, tiles
    idx_of = {t: i for i, t in enumerate(tiles)}
    memb = np.zeros((len(tiles), len(cube_ids)), dtype=np.float64)
    for j, g in enumerate(groups):
        memb[idx_of[g], j] = 1.0
    Wt = bootstrap_weights(len(tiles), B, seed + 1)          # (B, n_tiles)
    return Wt @ memb, tiles                                   # (B, n_cubes)


def q4_gates(per_combo, a_comp_cols, ratio_rows, W, Wg, cube_ids):
    """冻结件 q4_minimum_lines 的四条最低成立档，逐条给证据。"""
    gates = {}
    # (1) broken_control: pooled A_comp CI 下界 > 0，且至少一半 partition ratio < 1
    if a_comp_cols:
        Mx = np.vstack(a_comp_cols)
        with np.errstate(invalid="ignore"):
            pooled_delta = np.nanmean(Mx, axis=0)
        mask = np.isfinite(pooled_delta)
        draws = wmean(W, pooled_delta, mask)
        lo, hi = ci_from_draws(draws)
        n_lt1 = sum(1 for r in ratio_rows if r["ratio_lt_1"])
        frac = n_lt1 / max(len(ratio_rows), 1)
        g = {"pooled_a_comp_mean": float(np.nanmean(pooled_delta)),
             "pooled_a_comp_ci95": [lo, hi], "lcb_gt_0": bool(lo > 0),
             "n_partition_control_pairs": len(ratio_rows),
             "n_ratio_lt_1": n_lt1, "frac_ratio_lt_1": float(frac),
             "at_least_half_ratio_lt_1": bool(frac >= 0.5)}
        if Wg is not None:
            glo, ghi = ci_from_draws(wmean(Wg, pooled_delta, mask))
            g["geo_cluster_sensitivity_ci95"] = [glo, ghi]
            g["geo_cluster_lcb_gt_0"] = bool(glo > 0)
        g["passes"] = bool(g["lcb_gt_0"] and g["at_least_half_ratio_lt_1"])
        gates["broken_control"] = g
    else:
        gates["broken_control"] = {"passes": False, "reason": "没有可用坏对照列"}
    # (2) composed_vs_direct: held-out composed MSE 不超过 direct 的 5%
    rows, ok = [], True
    for combo, blk in per_combo.items():
        meta = blk["meta"]
        if meta["tag"] != "heldout":
            continue
        dkey = combo_key(meta["endpoint"], (meta["endpoint"],))
        if dkey not in per_combo:
            continue
        cm = blk["variants"]["factual"]["pooled_mse"]
        dm = per_combo[dkey]["variants"]["factual"]["pooled_mse"]
        ratio = cm / dm if dm > 0 else float("nan")
        good = bool(np.isfinite(ratio) and ratio <= 1.0 + COMPOSED_VS_DIRECT_TOL)
        ok = ok and good
        rows.append({"combo": combo, "direct_combo": dkey, "endpoint": meta["endpoint"],
                     "partition": meta["partition"], "composed_pooled_mse": float(cm),
                     "direct_pooled_mse": float(dm), "ratio": float(ratio),
                     "within_tol": good})
    gates["composed_vs_direct"] = {"tol": COMPOSED_VS_DIRECT_TOL, "rows": rows,
                                   "n_heldout_compared": len(rows),
                                   "passes": bool(ok and rows)}
    return gates
def _horizon_state_block(cov_t, hz_cov, hz_move) -> dict:
    """Panel B 的逐 horizon 状态量：M_h、S_h/S_t、r_eff,h/r_eff,t。

    分母 S_t / r_eff,t 是同一 split 上 z_t 的统计（cov_t），与 state_retention
    门共用分母定义，但**本函数不产生任何 pass/fail**——Panel B 是描述性证据，
    退化判定仍由预注册的 noncollapse_gate 负责。
    """
    if cov_t is None or cov_t.n < 2:
        return {"degenerate": True, "reason": "cov_t 样本不足"}
    s_t, r_t = cov_t.mean_std(), cov_t.effective_rank()
    rows = {}
    for ep in sorted(hz_cov):
        c, mv = hz_cov[ep], hz_move[ep]
        if c.n < 2 or not mv:
            rows[str(ep)] = {"degenerate": True, "reason": "该 horizon 无 direct 组合"}
            continue
        s_h, r_h = c.mean_std(), c.effective_rank()
        rows[str(ep)] = {
            "movement": float(np.mean(mv)),          # M_h：z_t → z_h 的平均 L2 位移
            "state_std": s_h,
            "std_retention": float(s_h / max(s_t, 1e-12)),
            "effective_rank": r_h,
            "effective_rank_retention": float(r_h / max(r_t, 1e-12)),
            "n_tokens": int(c.n), "n_batches": len(mv),
        }
    return {"reporting_only": True,
            "note": ("仅供论文 Panel B；不参与四道门。预注册 state_retention 门"
                     "用 ep20|10-10，见 gates.state_retention。"),
            "denominator": {"state_std_zt": s_t, "effective_rank_zt": r_t,
                            "n_tokens_zt": int(cov_t.n)},
            "horizons": rows}


def state_retention_gate(struct, per_combo, cov_t, cov_ep) -> dict:
    """冻结件 state_retention：std / effective-rank retention >= 0.5，且 Q2 成立。

    Q2（状态承载力）= 去掉状态贡献的移除臂必须更差。这里要求 alpha0 与
    identity_state 在**每个**端点组合上 a_comp 的 CI 下界 > 0。
    """
    batch = dict(struct.get("retention") or {})
    split = {}
    if cov_t is not None and cov_ep is not None and cov_ep.n >= 2:
        er_t, er_ep = cov_t.effective_rank(), cov_ep.effective_rank()
        sd_t, sd_ep = cov_t.mean_std(), cov_ep.mean_std()
        split = {
            "n_tokens_zt": int(cov_t.n), "n_tokens_zep": int(cov_ep.n),
            "state_std_zt": sd_t, "state_std_zep": sd_ep,
            "effective_rank_zt": er_t, "effective_rank_zep": er_ep,
            "std_retention": float(sd_ep / max(sd_t, 1e-12)),
            "effective_rank_retention": float(er_ep / max(er_t, 1e-12)),
        }
        split["passes"] = bool(split["std_retention"] >= RETENTION_MIN
                               and split["effective_rank_retention"] >= RETENTION_MIN)
    q2_rows, q2_ok = [], True
    for combo, blk in per_combo.items():
        for arm in ("alpha0", "identity_state"):
            ctl = blk["controls"].get(arm)
            if not ctl:
                continue
            good = bool(ctl["a_comp_lcb_gt_0"])
            q2_ok = q2_ok and good
            q2_rows.append({"combo": combo, "removal_arm": arm,
                            "a_comp_ci95": ctl["a_comp_ci95"], "lcb_gt_0": good})
    nc = dict(struct.get("noncollapse_gate") or {})
    const_gate = dict(struct.get("constant_state_caught_by_gate") or {})
    return {
        "retention_min": RETENTION_MIN,
        "batch_level": batch,
        "split_level": split,
        "noncollapse_gate": nc,
        "constant_state_caught_by_gate": const_gate,
        "constant_state_correctly_failed": bool(const_gate.get("verdict") == "FAIL"),
        "q2_removal_arms": q2_rows,
        "q2_holds": bool(q2_ok and q2_rows),
        "passes": bool((split.get("passes", batch.get("passes", False)))
                       and q2_ok and q2_rows
                       and nc.get("verdict") == "PASS"
                       and const_gate.get("verdict") == "FAIL"),
    }


def atomic_write_json(path, payload) -> str:
    """临时文件 + fsync + 原子 rename。返回落盘后的 SHA-256。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".tmp.{os.getpid()}")
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False,
                      default=_json_default)
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, p)
    dfd = os.open(str(p.parent), os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return sha256_file(p)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(f"不可序列化类型 {type(o)!r}")
def _safe(name: str) -> str:
    return name.replace("|", "__").replace(":", "-")


def _write_npz(path, series, cube_ids, state_rows, paths=None):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".tmp.{os.getpid()}")
    payload = {"cube_ids": np.asarray(cube_ids, dtype=object),
               "series_keys": np.asarray(sorted(series.keys()), dtype=object)}
    for k, v in series.items():
        for field, arr in v.items():
            payload[f"{_safe(k)}|{field}"] = arr
    if paths:
        payload["path_keys"] = np.asarray(sorted(paths.keys()), dtype=object)
        for k, v in paths.items():
            for field, arr in v.items():
                payload[f"path|{_safe(k)}|{field}"] = np.asarray(arr, dtype=np.float64)
    if state_rows:
        payload["state_std_zt_per_cube"] = np.asarray(
            [r["state_std_zt"] for r in state_rows], dtype=np.float64)
        payload["state_cube_ids"] = np.asarray(
            [r["cube_id"] for r in state_rows], dtype=object)
    with open(tmp, "wb") as fh:
        np.savez_compressed(fh, **payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, p)
    return sha256_file(p)


def _per_cube_records(series, cube_ids, combos):
    """逐 cube 记录：每个 (combo, variant) 的 n_valid / mse / r2。"""
    cache = {k: per_cube_metrics(v) for k, v in series.items()}
    velig = {k: _variant_elig(v) for k, v in series.items()}
    recs = []
    for i, cid in enumerate(cube_ids):
        row = {"cube_id": cid, "geo_group": geo_group_of(cid), "combos": {}}
        for c in combos:
            combo = c["combo"]
            entry = {"endpoint": c["endpoint"], "partition": c["partition"],
                     "tag": c["tag"], "variants": {}}
            for variant in ("factual", "alpha0", *CONTROLS):
                k = _key(combo, variant)
                if k not in series:
                    continue
                mse, r2, sst, elig = cache[k]
                ve = velig[k]
                entry["variants"][variant] = {
                    "n_valid_pixels": float(series[k]["n"][i]),
                    "sse": float(series[k]["sse"][i]),
                    "mse": None if not np.isfinite(mse[i]) else float(mse[i]),
                    "r2": None if not np.isfinite(r2[i]) else float(r2[i]),
                    "sst": float(sst[i]),
                    "eligible": bool(elig[i] and ve[i]),
                    "data_eligible": bool(elig[i]),
                    "control_valid_for_cube": bool(ve[i]),
                }
            row["combos"][combo] = entry
        recs.append(row)
    return recs
def _finish_scoring(args, model, ck, meta, ids, split_payload, grid, struct,
                    cov_t, cov_ep, state_rows, plan, root,
                    *, horizon_state=None) -> dict:
    if struct is None:
        raise EvalError("一个 batch 都没跑到，拒绝产出任何聚合数字")
    series = grid.finalize()
    combos = _combo_table(plan)
    n_cube_ids = len(grid.cube_ids)
    for c, p in grid.paths.items():
        for f, v in p.items():
            if len(v) != n_cube_ids:
                raise EvalError(f"路径量 {c}.{f} 长度 {len(v)} != cube 数 {n_cube_ids}")
    W, per_combo, a_comp_cols, ratio_rows, n_cubes = aggregate(
        series, grid.cube_ids, combos, grid.degenerate, seed=CONTROL_SEED,
        paths=grid.paths)
    Wg, tiles = geo_cluster_weights(grid.cube_ids)
    gates = q4_gates(per_combo, a_comp_cols, ratio_rows, W, Wg, grid.cube_ids)
    gates["state_retention"] = state_retention_gate(struct, per_combo, cov_t, cov_ep)
    sg = struct["semigroup"]
    gates["semigroup_bit_exact"] = {
        "one_segment_equals_direct": sg["one_segment_equals_direct"],
        "two_segment_equals_composed": sg["two_segment_equals_composed"],
        "recursive_nontrivial":
            struct["recursive_nontrivial"]["three_segment_differs_from_direct"],
        "weather_switch_pre_identical":
            struct["weather_switch"]["pre_switch_bit_identical"],
        "weather_switch_post_changed": struct["weather_switch"]["post_switch_changed"],
        "passes": bool(sg["one_segment_equals_direct"]
                       and sg["two_segment_equals_composed"]
                       and struct["recursive_nontrivial"]["three_segment_differs_from_direct"]
                       and struct["weather_switch"]["pre_switch_bit_identical"]
                       and struct["weather_switch"]["post_switch_changed"]),
    }
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    recs = _per_cube_records(series, grid.cube_ids, combos)
    sha_cubes = atomic_write_json(out / "per_cube_metrics.json", {
        "schema": "candidate_c_q4_per_cube_v1",
        "n_cubes": n_cubes, "split_selector": args.split_selector,
        "aggregation_note": "先算 per-cube 指标，再按单位聚合；未先池化像素再配对",
        "cubes": recs})
    sha_npz = _write_npz(out / "per_cube_arrays.npz", series, grid.cube_ids,
                         state_rows, paths=grid.paths)
    all_pass = all(bool(g.get("passes")) for g in gates.values())
    agg = {
        "schema": "candidate_c_q4_aggregate_v1",
        "verdict": "PASS" if all_pass else "FAIL",
        "gates": gates,
        "n_cubes": n_cubes,
        "n_geo_clusters": len(tiles),
        "geo_clusters": tiles,
        "split": {"manifest": str(Path(args.split_manifest).resolve()),
                  "selector": args.split_selector,
                  "n_ids_in_manifest": len(ids),
                  "n_scored": n_cubes,
                  "allow_locked": bool(args.allow_locked),
                  "usage_contract": split_payload.get("usage_contract")},
        "combos": combos,
        "per_combo": per_combo,
        "structural_checks": struct,
        "horizon_state_report": horizon_state or {"degenerate": True,
                                                  "reason": "本次运行未采集"},
        "degenerate_controls": {f"{k[0]}::{k[1]}": v for k, v in grid.degenerate.items()},
        "eligibility_rule": {
            "axis": "n_valid（逐 cube 有效像素数）",
            "min_valid_pixels": MIN_VALID_PIXELS,
            "rationale": ("云/阴影掩膜后单个 (cube, combo) 可能只剩几十个有效像素，"
                          "却与剩 1600 个像素的 cube 等权。R²=1−SSE/SST 的分母是"
                          "待解释方差，有效像素极少时 R² 可达 −1e5 量级并支配 476 "
                          "cube 的均值。单帧 128×128=16384 像素，有效像素中位数约 "
                          "1600，64 是中位数的 4%，只切长尾。"),
            "threshold_sweep": {
                "axis_values": [0, 32, 64, 128, 512, 1600],
                "compare_combos_passing": ["2/19", "2/19", "7/19", "7/19",
                                           "7/19", "8/19"],
                "note": ("判定在 32→64 之间翻转，64→1600 完全稳定。这条平台说明 "
                         "64 落在真实的数据不足分界之后，不是挑出来的幸运点。"),
            },
            "superseded_v1": {
                "axis": "逐像素目标标准差 sqrt(SST/n)",
                "threshold": SENSITIVITY_STD_FLOOR,
                "why_dropped": ("被它剔掉的两个 cube 分别只有 53 / 2 个有效像素，"
                                "土地覆盖与整段 NDVI 变异都正常（53 像素那个是 "
                                "84% 农田、NDVI std 0.235）。std 低是云遮挡的后果"
                                "而非原因，按后果设门限是用错了轴。"),
            },
            "preregistered": False,
            "changes_conclusion": True,
            "cost": ("约 44.7% 的 (cube, combo) 对被排除，反映云遮挡的普遍程度，"
                     "不是少量异常。"),
            "freeze_note": ("四份冻结件与 A01 §8 均未规定资格判据；原实现的 sst>0 "
                            "是脚本实现选择而非预注册内容，故此为填补冻结件空白而非"
                            "改动已冻结判据。但它确实改变结论（无门限下 C1 "
                            "composed_vs_direct 不过），因此三个口径全部并列落盘，"
                            "且由人类决策者在看到三种结果后于 2026-08-24 显式选定，"
                            "记录在 A05 §Q4 与 A04 Q4 结果条目。"),
        },
        "partially_ineligible_controls": {
            f"{k[0]}::{k[1]}": {"reason": v["reason"],
                                "n_cube_ineligible": v["n_cube_ineligible"],
                                "cube_ids": sorted(set(v["cube_ids"]))}
            for k, v in grid.partial.items()},
        "checkpoint": meta,
        "model_config": model.config(),
        "artifacts": {"per_cube_metrics.json": sha_cubes,
                      "per_cube_arrays.npz": sha_npz},
    }
    prov = provenance({"eval_mode": "score", "device": args.device,
                       "batch_size": args.batch_size, "data_root": str(root)})
    agg["provenance"] = prov
    agg["canonical_sha256_of_gates"] = canonical_json_sha256(gates)
    sha_agg = atomic_write_json(out / "q4_aggregate.json", agg)
    atomic_write_json(out / "provenance.json", {**prov, "q4_aggregate_sha256": sha_agg})
    return agg
# ------------------------------------------------------------------ 配对比较 (G_abs)
def load_score_dir(path):
    """读回一次 score 的产物。series key 用记录下来的原始键 + _safe() 反查，
    不做字符串解析——避免 '::' 与 '-' 混淆导致悄悄配错。"""
    d = Path(path)
    agg_p, npz_p = d / "q4_aggregate.json", d / "per_cube_arrays.npz"
    for p in (agg_p, npz_p):
        if not p.is_file():
            raise EvalError(f"score 产物缺失：{p}")
    agg = json.loads(agg_p.read_text())
    z = np.load(str(npz_p), allow_pickle=True)
    cube_ids = [str(x) for x in z["cube_ids"].tolist()]
    series = {}
    for k in [str(x) for x in z["series_keys"].tolist()]:
        s = _safe(k)
        series[k] = {f: np.asarray(z[f"{s}|{f}"], dtype=np.float64)
                     for f in ("n", "sse", "sy", "sy2")}
        ck = f"{s}|cube_elig"
        if ck in z.files:                       # 旧产物没有这个字段，向后兼容
            series[k]["cube_elig"] = np.asarray(z[ck], dtype=np.float64)
    return agg, series, cube_ids


def _align(series_a, ids_a, series_b, ids_b, key):
    """按 cube_id 严格配对，返回对齐后的两份充分统计量与共同可用掩膜。"""
    if key not in series_a or key not in series_b:
        return None
    pos_b = {c: i for i, c in enumerate(ids_b)}
    common = [(i, pos_b[c]) for i, c in enumerate(ids_a) if c in pos_b]
    if len(common) < 2:
        return None
    ia = np.asarray([i for i, _ in common])
    ib = np.asarray([j for _, j in common])
    sa = {f: series_a[key][f][ia] for f in ("n", "sse", "sy", "sy2")}
    sb = {f: series_b[key][f][ib] for f in ("n", "sse", "sy", "sy2")}
    _ma, _ra, _sa, ea = per_cube_metrics(sa)
    _mb, _rb, _sb, eb = per_cube_metrics(sb)
    ids = [ids_a[i] for i in ia]
    return sa, sb, (ea & eb), ids


def g_abs_block(W, sa, sb, elig):
    """G_abs：LCB(ΔR²) >= -eps_R2 且 UCB(RMSE_a/RMSE_b) <= 1+eps_RMSE。

    【R² 腿口径更正 2026-08-31，见 A04 §19】
    原实现对**逐 cube** R² 取平均。逐 cube R²=1−SSE/SST 的分母是该 cube 的待解释方差，
    在 SST→0 时无下界；对它取算术平均在 SST 高度异质的数据上不是有效聚合。在
    `val_locked` 上它产出了 ΔR²=−35.489、CI 下界 −116.744 这类非物理取值，而同一道门的
    RMSE 腿（本来就 pooled）同期 19/19 通过——一道门两条腿用两种聚合，本身就是规格缺陷。

    现改为 pooled R²（`wpooled` 的第二个返回值，此前被算出后丢弃），与 RMSE 腿口径一致。
    逐 cube 版仍以 `legacy_percube_*` 全量记录，供复现历史结果与敏感性对照；它不再参与判定。
    """
    _ma, ra, _s1, _e1 = per_cube_metrics(sa)
    _mb, rb, _s2, _e2 = per_cube_metrics(sb)
    _msea, r2a = wpooled(W, sa, elig)
    _mseb, r2b = wpooled(W, sb, elig)
    d_r2 = r2a - r2b                                  # pooled，与 RMSE 腿同口径
    lo_r2, hi_r2 = ci_from_draws(d_r2)
    d_r2_legacy = wmean(W, ra - rb, elig)             # 逐 cube，仅记录
    lo_r2_legacy, hi_r2_legacy = ci_from_draws(d_r2_legacy)
    pa, _ = wpooled(W, sa, elig)
    pb, _ = wpooled(W, sb, elig)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.sqrt(pa) / np.sqrt(np.maximum(pb, 1e-300))
    lo_rt, hi_rt = ci_from_draws(ratio)
    m = elig.astype(np.float64)
    pmse_a = float((sa["sse"] * m).sum() / max((sa["n"] * m).sum(), 1e-12))
    pmse_b = float((sb["sse"] * m).sum() / max((sb["n"] * m).sum(), 1e-12))
    point_ratio = float(np.sqrt(pmse_a) / max(np.sqrt(pmse_b), 1e-300))
    d_point = float(np.nanmedian(d_r2))
    return {
        "n_paired_cubes": int(elig.sum()),
        "r2_aggregation": "pooled",
        "delta_r2_mean": d_point, "delta_r2_ci95": [lo_r2, hi_r2],
        "delta_r2_lcb": lo_r2, "eps_r2": EPS_R2,
        "lcb_ge_neg_eps": bool(lo_r2 >= -EPS_R2),
        "legacy_percube_delta_r2_mean": float(np.nanmean(np.where(elig, ra - rb, np.nan))),
        "legacy_percube_delta_r2_ci95": [lo_r2_legacy, hi_r2_legacy],
        "legacy_percube_lcb_ge_neg_eps": bool(lo_r2_legacy >= -EPS_R2),
        "legacy_percube_note": "mis-specified aggregation, recorded only; see A04 §19",
        "rmse_ratio_point": point_ratio, "rmse_ratio_ci95": [lo_rt, hi_rt],
        "rmse_ratio_ucb": hi_rt, "eps_rmse": EPS_RMSE,
        "ucb_le_1_plus_eps": bool(hi_rt <= 1.0 + EPS_RMSE),
        "pooled_rmse_a": float(np.sqrt(pmse_a)), "pooled_rmse_b": float(np.sqrt(pmse_b)),
        "passes": bool(lo_r2 >= -EPS_R2 and hi_rt <= 1.0 + EPS_RMSE),
    }
def compare_runs(args) -> dict:
    """C1(candidate) vs C0R(control) 的配对比较。

    只做 validation-口径的事实非劣比较；不打开 OOD/test，不做第二个 seed，
    不因结果好坏改动任何预注册决定。
    """
    agg_a, sa_all, ids_a = load_score_dir(args.candidate)
    agg_b, sb_all, ids_b = load_score_dir(args.control)
    for name, agg in (("candidate", agg_a), ("control", agg_b)):
        sel = (agg.get("split") or {}).get("selector", "")
        if ("locked" in sel.lower() or "ood" in sel.lower() or "test" in sel.lower()) \
                and not args.allow_locked:
            raise EvalError(f"{name} 的 split 选择器 {sel!r} 指向锁定/OOD/test，拒绝比较")
    sel_a = (agg_a.get("split") or {}).get("selector")
    sel_b = (agg_b.get("split") or {}).get("selector")
    if sel_a != sel_b:
        raise EvalError(f"两臂 split 不同（{sel_a!r} vs {sel_b!r}），比较无效")
    arm_a = (agg_a.get("checkpoint") or {}).get("arm")
    arm_b = (agg_b.get("checkpoint") or {}).get("arm")
    if arm_b == "C0S" or arm_a == "C0S":
        raise EvalError("出现 C0S。本轮没有 simulator 监督量，C0S 不得伪造")
    combos_a = {c["combo"]: c for c in agg_a.get("combos", [])}
    per_combo, direct_ok, composed_ok, n_direct, n_composed = {}, True, True, 0, 0
    Wcache = {}
    for combo, meta in combos_a.items():
        key = _key(combo, "factual")
        al = _align(sa_all, ids_a, sb_all, ids_b, key)
        if al is None:
            continue
        sa, sb, elig, ids = al
        # 臂间比较按 geo_group(tile) 聚类重采样（选择合同 uncertainty）。
        # 缓存键必须含 ids 本身：不同 combo 的可用 cube 集合不同，只按 n 缓存
        # 会把 A 的权重矩阵用到 B 的 cube 顺序上。
        ck = (len(ids), hash(tuple(ids)))
        if ck not in Wcache:
            Wc, tiles_c = geo_cluster_weights(ids, B=COMPARE_BOOTSTRAP_B,
                                              seed=CONTROL_SEED)
            if Wc is None:
                raise EvalError(f"{combo}: 只有 {len(tiles_c)} 个 tile，"
                                f"无法按 geo_group 聚类重采样")
            Wcache[ck] = (Wc, tiles_c)
        Wc, tiles_c = Wcache[ck]
        blk = g_abs_block(Wc, sa, sb, elig)
        blk["ci_method"] = {"method": "geo-clustered bootstrap",
                            "cluster_unit": COMPARE_CLUSTER_UNIT,
                            "n_resamples": COMPARE_BOOTSTRAP_B,
                            "n_clusters": len(tiles_c),
                            "source": "candidate_c_selection_contract_v1.uncertainty"}
        # 敏感性分析：三个口径全部并列落盘，任何一侧都不隐藏。
        #   none    = 原始 sst>0（无任何下限）
        #   std_v1  = 已停用的 v1 口径 std>=1e-2
        #   primary = 当前口径 n_valid>=64（即上面的 elig）
        _e_none = (per_cube_metrics(sa, min_valid=1, std_floor=0.0)[3]
                   & per_cube_metrics(sb, min_valid=1, std_floor=0.0)[3])
        _e_std = (per_cube_metrics(sa, min_valid=1,
                                   std_floor=SENSITIVITY_STD_FLOOR)[3]
                  & per_cube_metrics(sb, min_valid=1,
                                     std_floor=SENSITIVITY_STD_FLOOR)[3])
        blk["sensitivity"] = {
            "none": g_abs_block(Wc, sa, sb, _e_none),
            "std_floor_v1": g_abs_block(Wc, sa, sb, _e_std),
        }
        blk["eligibility"] = {"primary_axis": "n_valid",
                              "min_valid_pixels": MIN_VALID_PIXELS,
                              "n_eligible": int(elig.sum()),
                              "n_eligible_none": int(_e_none.sum()),
                              "n_eligible_std_floor_v1": int(_e_std.sum()),
                              "n_cubes_total": int(elig.shape[0])}
        blk["meta"] = meta
        per_combo[combo] = blk
        if meta["n_segments"] == 1:
            n_direct += 1
            direct_ok = direct_ok and blk["passes"]
        else:
            n_composed += 1
            composed_ok = composed_ok and blk["passes"]
    if not per_combo:
        raise EvalError("没有任何可配对的 combo，比较无法成立")
    gate = {"direct_all_pass": bool(direct_ok and n_direct > 0),
            "composed_all_pass": bool(composed_ok and n_composed > 0),
            "n_direct_combos": n_direct, "n_composed_combos": n_composed,
            "rule": "direct 与 composed 均须通过 G_abs（冻结件 factual_endpoint_gate）",
            "passes": bool(direct_ok and composed_ok and n_direct > 0 and n_composed > 0)}
    out = {
        "schema": "candidate_c_q4_compare_v1",
        "verdict": "PASS" if gate["passes"] else "FAIL",
        "factual_endpoint_gate": gate,
        "per_combo": per_combo,
        "candidate": {"dir": str(Path(args.candidate).resolve()),
                      "arm": arm_a, "checkpoint": agg_a.get("checkpoint"),
                      "own_verdict": agg_a.get("verdict")},
        "control": {"dir": str(Path(args.control).resolve()),
                    "arm": arm_b, "checkpoint": agg_b.get("checkpoint"),
                    "own_verdict": agg_b.get("verdict")},
        "split_selector": sel_a,
        "uncertainty": {"method": "minicube 级 geo-clustered bootstrap",
                        "cluster_unit": COMPARE_CLUSTER_UNIT,
                        "n_resamples": COMPARE_BOOTSTRAP_B,
                        "ci_level": 1.0 - CI_ALPHA,
                        "source": "candidate_c_selection_contract_v1.uncertainty",
                        "rationale": ("同一 tile 内 minicube 高度相关，按 minicube "
                                      "独立重采样会把区间做得虚假地窄")},
        "note": ("ΔR² = candidate − control，RMSE ratio = candidate / control。"
                 "非劣判据只用于事实端点，不构成因果或 simulator 结论。"),
    }
    prov = provenance({"eval_mode": "compare"})
    out["provenance"] = prov
    out["canonical_sha256_of_gate"] = canonical_json_sha256(gate)
    outdir = Path(args.output)
    sha = atomic_write_json(outdir / "q4_compare.json", out)
    atomic_write_json(outdir / "provenance.json", {**prov, "q4_compare_sha256": sha})
    return out
# ------------------------------------------------------------------ CLI
def build_argparser():
    ap = argparse.ArgumentParser(
        description="Candidate C Q4 评测器（composition / segment-transition）")
    sub = ap.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("score", help="在一个 split 上给一个 checkpoint 打分")
    s.add_argument("--ckpt", required=True)
    s.add_argument("--data-root", required=True)
    s.add_argument("--split-manifest", required=True)
    s.add_argument("--split-selector", default="validation_subsplit.val_dev.ids",
                   help="默认 val_dev；val_locked/OOD/test 需显式 --allow-locked")
    s.add_argument("--output", required=True)
    s.add_argument("--batch-size", type=int, default=4)
    s.add_argument("--num-workers", type=int, default=2)
    s.add_argument("--device", default="cpu")
    s.add_argument("--max-cubes", type=int, default=0, help="0=全部")
    s.add_argument("--max-batches", type=int, default=0, help="0=不限（仅调试用）")
    s.add_argument("--allow-locked", action="store_true")

    c = sub.add_parser("compare", help="C1 与 C0R 的配对 G_abs 比较")
    c.add_argument("--candidate", required=True, help="C1 的 score 输出目录")
    c.add_argument("--control", required=True, help="C0R 的 score 输出目录")
    c.add_argument("--output", required=True)
    c.add_argument("--allow-locked", action="store_true")
    return ap


def main(argv=None):
    args = build_argparser().parse_args(argv)
    if args.mode == "score":
        res = score_checkpoint(args)
        gates = {k: bool(v.get("passes")) for k, v in res["gates"].items()}
        print(json.dumps({"verdict": res["verdict"], "n_cubes": res["n_cubes"],
                          "gates": gates, "output": str(Path(args.output).resolve())},
                         indent=2, ensure_ascii=False))
        return 0 if res["verdict"] == "PASS" else 1
    res = compare_runs(args)
    print(json.dumps({"verdict": res["verdict"],
                      "factual_endpoint_gate": res["factual_endpoint_gate"],
                      "output": str(Path(args.output).resolve())},
                     indent=2, ensure_ascii=False))
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
