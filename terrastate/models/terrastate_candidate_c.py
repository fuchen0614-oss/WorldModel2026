#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TerraState Candidate C：可变跨度共享分段转移（A01 §4.2）。

与 AAAI 版 TerraStateV2 的唯一结构差别是**接口**，不是参数：

    z_t = q(H_t, u^past_<=t, g)                     # weather-free context prior
    z_b = F(z_a, u_{a+1:b}, g, dt=b-a)              # 可变跨度，参数共享
    y_b = O(z_b) + b_b(H_t, u^past_<=t, g)

因此 Candidate C 继承父 checkpoint 的**全部 255 个张量**且不新增任何参数
（whitelist 为空）。这不是巧合，而是本轮的控制性质：C1 与 C0R 参数量完全
相同，任何差异都不能归因于容量。

本轮硬边界：
  * L_pair 需要正式 simulator 情景库；仓库中不存在，故只提供 schema/adapter/
    合成 fixture，状态记为 BLOCKED_SIMULATOR_LIBRARY_AND_FORMAL_SCENARIO_MANIFEST；
  * 旧 future-state anchor 默认 OFF（不接 z_star，不读 cache）；
  * 不使用 teacher/KD：L_EO 是纯真实 EO 监督。
"""
from __future__ import annotations

import hashlib
from types import SimpleNamespace
from typing import Dict, List, Optional, Sequence

import torch
import torch.nn.functional as F

from .terrastate_v2 import TerraStateV2

# 与 ops/candidate_c_nightly/<ts>/manifests/candidate_c_q4_partition_manifest_v1.json 一致。
# 模型侧只作默认值；正式运行由 config 显式传入并与 manifest SHA 交叉校验。
CC_TRAIN_PARTITIONS = {
    10: [(10,), (5, 5), (5, 3, 2)],
    15: [(15,), (7, 8), (7, 4, 4)],
    20: [(20,), (10, 10), (10, 5, 5), (5, 5, 5, 5)],
}
CC_HELDOUT_PARTITIONS = {
    10: [(3, 7), (6, 4), (2, 3, 5)],
    15: [(4, 11), (3, 5, 7)],
    20: [(8, 12), (2, 18), (2, 6, 12), (1, 4, 6, 9)],
}

SIMULATOR_STATUS = "BLOCKED_SIMULATOR_LIBRARY_AND_FORMAL_SCENARIO_MANIFEST"
def value_sha16(sd: Dict[str, torch.Tensor]) -> str:
    """与 ops/resume11904_to14880 的 value_sha 完全同一约定：
    按 key 排序，喂入 key 与原始张量字节，取 sha256 前 16 hex。
    A02 记录 verified-14880 的 value_sha = aa98fbd2fa302727。"""
    h = hashlib.sha256()
    for k in sorted(sd.keys()):
        h.update(k.encode())
        h.update(sd[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()[:16]


def sha256_file(path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def _as_partition_table(obj, default: dict) -> dict:
    """把 config 里的 {endpoint: [[...], ...]} 规整为 {int: [tuple, ...]}，并校验和。"""
    if obj is None:
        return {int(k): [tuple(p) for p in v] for k, v in default.items()}
    out = {}
    for k, v in obj.items():
        ep = int(k)
        parts = [tuple(int(s) for s in p) for p in v]
        for p in parts:
            if sum(p) != ep:
                raise ValueError(f"分段 {p} 之和 {sum(p)} != 端点 {ep}")
            if any(s < 1 for s in p):
                raise ValueError(f"分段 {p} 含非正跨度")
        out[ep] = parts
    return out


class TerraStateCandidateC(TerraStateV2):
    """Candidate C：通用 N 段递归 rollout + 可变跨度 direct transition。

    继承 TerraStateV2 的全部模块，不新增参数。direct 与 composed 共享同一个
    F（self.transition + self.fuse + self.weather_enc + self.time_emb），但走
    不同计算图，因此 semigroup 一致性是可检验的非平凡性质。
    """

    ARCH = "TerraStateCandidateC"
    ROUTE_VERSION = "candidate_c_v1"
    # 允许缺失的新模块前缀白名单。Candidate C 不新增参数，故为空元组。
    NEW_MODULE_WHITELIST: tuple = ()

    def __init__(self, hparams=None, contract_cfg: Optional[dict] = None):
        super().__init__(hparams, contract_cfg)
        cfg = contract_cfg or {}
        self.cc_train_partitions = _as_partition_table(
            cfg.get("cc_train_partitions"), CC_TRAIN_PARTITIONS)
        self.cc_heldout_partitions = _as_partition_table(
            cfg.get("cc_heldout_partitions"), CC_HELDOUT_PARTITIONS)
        tr = {p for v in self.cc_train_partitions.values() for p in v}
        ho = {p for v in self.cc_heldout_partitions.values() for p in v}
        if tr & ho:
            raise ValueError(f"train/held-out 分段相交，held-out 失效：{sorted(tr & ho)}")
        self.days_per_step = int(cfg.get("days_per_transition_step", 5))
        # factual 端点监督走哪条路径：C1='recursive'，C0R='direct'。
        # 这是两臂**唯一**的结构性差别。
        self.factual_path = str(cfg.get("factual_path", "recursive"))
        if self.factual_path not in ("recursive", "direct"):
            raise ValueError(f"factual_path 只能是 recursive/direct，收到 {self.factual_path!r}")
        # 旧 future-state anchor 默认 OFF
        self.use_future_state_anchor = bool(cfg.get("use_future_state_anchor", False))
        # L_EO 的两个分量权重。两臂必须相同，否则不再是单变量对照。
        self.eo_traj_weight = float(cfg.get("eo_traj_weight", 1.0))
        self.eo_endpoint_weight = float(cfg.get("eo_endpoint_weight", 1.0))
        # 非坍缩门阈值（诊断门，不是显著性检验）
        self.nc_min_std = float(cfg.get("nc_min_std", 1e-3))
        self.nc_min_rank = float(cfg.get("nc_min_effective_rank", 2.0))
        self.nc_min_movement = float(cfg.get("nc_min_movement", 1e-4))

    # ---------------- 通用 N 段递归 rollout ----------------
    def segment_states(self, z_t, u_future, geo, partition: Sequence[int],
                       u_switch=None, switch_after_segment: Optional[int] = None):
        """沿 partition 逐段推进，返回每段结束后的状态列表。

        语义与父类 composed_state 严格一致：第 k 段用**该段跨度**做 time
        embedding（不是累计 horizon），天气子窗为 u[cum : cum+span]。
        因此 partition=(h1,h2) 与 composed_state(h1,h2) 逐位相同，
        partition=(h,) 与 direct_state(h) 逐位相同。

        u_switch/switch_after_segment 实现中途换天气：前 switch_after_segment
        段用 u_future，其后各段改用 u_switch（时间轴绝对对齐，仍按 cum 切窗）。
        """
        if not partition:
            raise ValueError("partition 不能为空")
        b_patch = z_t.shape[0]
        z = z_t
        cum = 0
        states = []
        for k, span in enumerate(partition):
            span = int(span)
            src = u_future
            if u_switch is not None and switch_after_segment is not None \
                    and k >= int(switch_after_segment):
                src = u_switch
            sub = src[:, cum:cum + span]
            d = self._to_patch(self.weather_enc.window(sub), b_patch)
            he = self.time_emb(torch.full((b_patch,), span, device=z.device,
                                          dtype=torch.long))
            z = self.transition(z, self._cond(d, geo, he))
            states.append(z)
            cum += span
        return states

    def segment_state(self, z_t, u_future, geo, partition: Sequence[int], **kw):
        """只要终点状态。"""
        return self.segment_states(z_t, u_future, geo, partition, **kw)[-1]
    # ---------------- 端点计划（C1/C0R 的 RNG 流必须逐位一致） ----------------
    FACTUAL_ENDPOINTS = (10, 15, 20)

    def recursive_candidates(self, endpoint: int) -> List[tuple]:
        """该端点下的多段候选（>=2 段）。单段 (h,) 已由直接轨迹覆盖，不入此表。"""
        cands = [p for p in self.cc_train_partitions[int(endpoint)] if len(p) >= 2]
        if not cands:
            raise ValueError(f"端点 {endpoint} 没有多段候选，递归臂无法成立")
        return cands

    def draw_endpoint_plan(self, rng, endpoints=None) -> List[dict]:
        """为一个 optimizer step 生成 (endpoint, partition) 计划。

        关键：RNG 消耗与 factual_path **无关**。两臂对每个端点都抽一次索引；
        direct 臂抽完后丢弃抽到的多段划分、改用 (endpoint,)。于是 C1 与 C0R 的
        随机数流逐位一致，端点集合也完全相同，唯一差别是端点监督是否经过
        递归分段路径。这正是本轮要单变量隔离的那个变量。
        """
        eps = self.FACTUAL_ENDPOINTS if endpoints is None else tuple(int(e) for e in endpoints)
        plan = []
        for ep in eps:
            cands = self.recursive_candidates(ep)
            idx = int(torch.randint(len(cands), (1,), generator=rng).item())
            drawn = cands[idx]
            used = drawn if self.factual_path == "recursive" else (int(ep),)
            plan.append({"endpoint": int(ep), "partition": tuple(used),
                         "partition_drawn": tuple(drawn), "n_segments": len(used)})
        return plan

    # ---------------- 端点预测（含 Q2 状态移除臂） ----------------
    def endpoint_prediction(self, prior, z_t, u_future, geo, partition, B, H, W,
                            arm: str = "full", u_switch=None,
                            switch_after_segment: Optional[int] = None):
        """ŷ_ep = prior[:, h-1] + alpha · O_δ(z_ep)，与父类 _composed_pred 同构。

        arm='full'       : 完整路径
        arm='alpha0'     : 去掉 T 的贡献（只剩 context-only prior）
        arm='T_identity' : 把整条 transition 换成恒等（z_ep := z_t）
        后两个是 Q2 状态承载力的移除臂，评测用，绝不参与训练梯度。
        """
        h = int(sum(partition))
        if arm == "alpha0":
            return prior[:, h - 1]
        if arm == "T_identity":
            z_ep = z_t
        elif arm == "full":
            z_ep = self.segment_state(z_t, u_future, geo, partition, u_switch=u_switch,
                                      switch_after_segment=switch_after_segment)
        else:
            raise ValueError(f"未知 arm {arm!r}，只允许 full/alpha0/T_identity")
        return prior[:, h - 1] + self.alpha * self._decode_state(z_ep, B, H, W)
    # ---------------- 中途换天气 ----------------
    def _alt_weather(self, u_future, generator=None):
        if generator is None:
            return torch.randn_like(u_future)
        return torch.randn(u_future.shape, dtype=u_future.dtype,
                           device=u_future.device, generator=generator)

    def weather_switch_states(self, z_t, u_future, geo, partition,
                              switch_after_segment: int, u_alt=None, generator=None):
        """前 k 段用原天气，第 k+1 段起改用 u_alt。返回 (base_states, switched_states)。"""
        k = int(switch_after_segment)
        if not (0 <= k < len(partition)):
            raise ValueError(f"switch_after_segment={k} 超出分段数 {len(partition)}")
        if u_alt is None:
            u_alt = self._alt_weather(u_future, generator=generator)
        base = self.segment_states(z_t, u_future, geo, partition)
        sw = self.segment_states(z_t, u_future, geo, partition,
                                 u_switch=u_alt, switch_after_segment=k)
        return base, sw

    @torch.no_grad()
    def assert_weather_switch_contract(self, z_t, u_future, geo, partition,
                                       switch_after_segment: int, u_alt=None,
                                       generator=None) -> dict:
        """契约：换天气不能回溯改写已发生的过去（前 k 段逐位相同），
        但必须改变其后（否则未来天气没真正进入 F，路由是坏的）。"""
        k = int(switch_after_segment)
        base, sw = self.weather_switch_states(z_t, u_future, geo, partition, k,
                                             u_alt=u_alt, generator=generator)
        n = len(partition)
        pre_ok = all(torch.equal(base[i], sw[i]) for i in range(k))
        post_changed = any(not torch.equal(base[i], sw[i]) for i in range(k, n))
        max_pre = max([(base[i] - sw[i]).abs().max().item() for i in range(k)] or [0.0])
        max_post = max((base[i] - sw[i]).abs().max().item() for i in range(k, n))
        return {"pre_switch_bit_identical": bool(pre_ok),
                "post_switch_changed": bool(post_changed),
                "max_abs_delta_pre": float(max_pre),
                "max_abs_delta_post": float(max_post),
                "n_segments": n, "switch_after_segment": k,
                "partition": [int(s) for s in partition]}
    # ---------------- 数值稳健的有效秩（子类覆写，父文件一行不动） ----------------
    #   父类 plan_b_b4.ObsWorldB4.effective_rank 走 eigvalsh(cov)。常数/坍缩状态的
    #   cov 是（近）零矩阵、特征值高度重复，torch 的 eigvalsh 在 CPU 上会抛
    #   _LinAlgError("failed to converge ... ill-conditioned or has too many repeated
    #   eigenvalues")。而这恰恰是非坍缩门存在的目标输入：门在自己要拦的用例上崩溃。
    #   plan_b_b4.py 被已验收的 11,904→14,880 世代和五个 evaluator 共用，故不修改它；
    #   只在 Candidate C 子类内换成 SVD 路径。
    #   定义不变：s 为中心化矩阵的奇异值时 ev_i = s_i^2/(n-1) 就是同一个协方差谱，
    #   participation ratio 公式与父类逐字一致（含 +1e-12）；零方差时父公式的极限
    #   恰为 0.0，与早退返回值一致。test_candidate_c_contract T10e 断言两条路线在
    #   健康输入上一致，因此"更稳健"没有偷偷改变被报告的量。
    EFF_RANK_VAR_FLOOR = 1e-24

    @staticmethod
    def effective_rank(z) -> float:
        x = z.reshape(-1, z.shape[-1]).detach().to(torch.float64)
        n = int(x.shape[0])
        x = x - x.mean(0, keepdim=True)
        if n < 2 or not (float(x.pow(2).sum()) > TerraStateCandidateC.EFF_RANK_VAR_FLOOR):
            # 常数 / 单行 / 全零：协方差为零矩阵，父公式极限 = 0.0。
            # 返回 0.0（而非抛错）非坍缩门才能把它判成 FAIL。
            return 0.0
        denom = max(n - 1, 1)
        try:
            ev = (torch.linalg.svdvals(x).pow(2) / denom).clamp(min=0.0)
        except Exception:                                    # noqa: BLE001
            try:                                             # 退回父类同式的谱路径
                cov = (x.T @ x) / denom
                ev = torch.linalg.eigvalsh(cov).clamp(min=0.0)
            except Exception:                                # noqa: BLE001
                # 两条路线都算不出来：对门而言返回 0.0 是 fail-closed 方向
                # （判为坍缩、拦下），不能因为数值失败就放行。
                return 0.0
        return float(ev.sum() ** 2 / (ev.pow(2).sum() + 1e-12))

    # ---------------- 非坍缩诊断与门 ----------------
    @staticmethod
    def state_movement(z_a, z_b) -> float:
        """两状态间的平均 L2 位移。T 退化为恒等时恒为 0。"""
        return (z_b - z_a).reshape(-1, z_a.shape[-1]).norm(dim=-1).mean().item()

    @torch.no_grad()
    def state_diagnostics(self, z_t, z_ep=None) -> dict:
        """可导出的状态运动/离散度/有效秩。三者都是 Q4 报告要求的量。"""
        d = {"state_dim": int(z_t.shape[-1]),
             "state_std_zt": float(self.state_std(z_t)),
             "effective_rank_zt": float(self.effective_rank(z_t))}
        if z_ep is not None:
            base = z_t.reshape(-1, z_t.shape[-1]).norm(dim=-1).mean().item()
            d["state_std_zep"] = float(self.state_std(z_ep))
            d["effective_rank_zep"] = float(self.effective_rank(z_ep))
            d["movement_zt_to_zep"] = float(self.state_movement(z_t, z_ep))
            d["relative_movement"] = float(d["movement_zt_to_zep"] / (base + 1e-12))
        return d

    def noncollapse_loss(self, z_states: Sequence[torch.Tensor]):
        """VICReg 形式，沿用父类 vicreg_loss，不另发明数学：方差撑开 + 去相关。"""
        if not z_states:
            raise ValueError("noncollapse_loss 需要至少一个状态")
        var_t = cov_t = None
        for z in z_states:
            v, c = self.vicreg_loss(z)
            var_t = v if var_t is None else var_t + v
            cov_t = c if cov_t is None else cov_t + c
        k = len(z_states)
        return 25.0 * (var_t / k) + (cov_t / k)

    @torch.no_grad()
    def noncollapse_gate(self, z_t, z_ep) -> dict:
        """把 constant / identity / collapsed 三类坏状态挡在门外；任一命中即 FAIL。"""
        d = self.state_diagnostics(z_t, z_ep)
        r = []
        if d["state_std_zt"] < self.nc_min_std:
            r.append("zt_std_below_min(constant_like)")
        if d["state_std_zep"] < self.nc_min_std:
            r.append("zep_std_below_min(constant_like)")
        if d["effective_rank_zt"] < self.nc_min_rank:
            r.append("zt_effective_rank_below_min(collapsed)")
        if d["effective_rank_zep"] < self.nc_min_rank:
            r.append("zep_effective_rank_below_min(collapsed)")
        if d["movement_zt_to_zep"] < self.nc_min_movement:
            r.append("no_state_movement(identity_like)")
        d["reasons"] = r
        d["verdict"] = "PASS" if not r else "FAIL"
        d["thresholds"] = {"min_std": self.nc_min_std, "min_effective_rank": self.nc_min_rank,
                           "min_movement": self.nc_min_movement}
        return d
    # ---------------- 损失契约 ----------------
    #   L = L_EO + λ_z·L_cmp_z + λ_y·L_cmp_y + λ_pair·L_pair + λ_nc·L_noncollapse
    #   C1 正式臂：λ_z=λ_y=λ_pair=λ_nc=0，factual_path='recursive'
    #   C0R 对照臂：同上四个 λ=0，factual_path='direct'
    #   两臂唯一差别 = 端点监督是否经过递归分段路径。
    LAMBDA_FIELDS = ("z", "y", "pair", "nc")

    @staticmethod
    def smoke_lambdas() -> SimpleNamespace:
        """仅 smoke 用的起始值（A02 标注为暂定，待 pilot 定标）。正式臂不得使用。"""
        return SimpleNamespace(z=0.1, y=1.0, pair=0.5, nc=0.01)

    @staticmethod
    def formal_lambdas() -> SimpleNamespace:
        """C1 与 C0R 正式臂：四个 λ 全部为 0。"""
        return SimpleNamespace(z=0.0, y=0.0, pair=0.0, nc=0.0)

    def loss_candidate_c(self, data, lambdas: SimpleNamespace,
                         endpoint_plan: Optional[List[dict]] = None,
                         rng=None, want_diagnostics: bool = True):
        """Candidate C 训练损失。teacher/KD 与 future-state anchor 均已移除，
        因此 L_EO 是纯真实 EO 监督。"""
        lam = lambdas
        if float(getattr(lam, "pair", 0.0)) != 0.0:
            raise RuntimeError(
                "L_pair 需要冻结的 paired simulator 情景库；本轮状态 = "
                f"{SIMULATOR_STATUS}。禁止用 Q3 donor/随机合成数据冒充 paired truth。")
        pred, prior, residual, z_t, geo, u_future = self.forecast(data, want_parts=True)
        cl, tl = self.context_len, self.target_len
        B, H, W = pred.shape[0], pred.shape[-2], pred.shape[-1]
        lc = data["landcover"]
        lc_mask = ((lc >= self.lc_min) & (lc <= self.lc_max)).type_as(pred)
        targ_win = data["dynamic"][0][:, cl:cl + tl, 0:1]
        cloud_win = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).type_as(pred)

        logs, total = {}, pred.new_zeros(())
        # (a) L_EO 轨迹项：全 20 步真实 NDVI，沿用 B0 的像素协议
        l_traj, _ = self.ndvi_loss(pred, data)
        total = total + self.eo_traj_weight * l_traj
        logs["eo_traj"] = l_traj.detach()

        if endpoint_plan is None:
            if rng is None:
                raise ValueError("endpoint_plan 与 rng 不能同时为 None")
            endpoint_plan = self.draw_endpoint_plan(rng)
        # (b) L_EO 端点项：真实标签经 factual 路径。
        # 同一行代码服务两臂：part=(ep,) 时 segment_state ≡ direct_state，
        # 因此 C1/C0R 不存在两套代码分支，差别只在 partition 元组本身。
        l_ep = pred.new_zeros(())
        l_cmp_z = pred.new_zeros(())
        l_cmp_y = pred.new_zeros(())
        nc_states, ep_logs = [], []
        want_cmp = float(getattr(lam, "z", 0.0)) > 0 or float(getattr(lam, "y", 0.0)) > 0
        for item in endpoint_plan:
            ep = int(item["endpoint"])
            part = tuple(int(s) for s in item["partition"])
            if sum(part) != ep:
                raise ValueError(f"端点计划不自洽：{part} 之和 {sum(part)} != {ep}")
            z_fact = self.segment_state(z_t, u_future, geo, part)
            y_fact = prior[:, ep - 1] + self.alpha * self._decode_state(z_fact, B, H, W)
            targ_h, cloud_h = targ_win[:, ep - 1], cloud_win[:, ep - 1]
            l_one = self._masked_mse1(y_fact, targ_h, cloud_h, lc_mask)
            l_ep = l_ep + l_one
            nc_states.append(z_fact)
            ep_logs.append({"endpoint": ep, "partition": list(part),
                            "n_segments": len(part), "eo_endpoint": l_one.detach()})
            if want_cmp:
                # 语义一致性：递归复合 vs 变跨度直接，应当逼近同一个 z_ep。
                # factual_path='direct' 时 z_fact 就是 z_dir，两项恒为 0（应然）。
                z_dir = self.direct_state(z_t, u_future, geo, ep)
                y_dir = prior[:, ep - 1] + self.alpha * self._decode_state(z_dir, B, H, W)
                l_cmp_z = l_cmp_z + F.mse_loss(z_fact, z_dir.detach())
                l_cmp_y = l_cmp_y + self._masked_mse1(y_fact, y_dir.detach(), cloud_h, lc_mask)
        k = max(len(endpoint_plan), 1)
        l_ep = l_ep / k
        total = total + self.eo_endpoint_weight * l_ep
        logs["eo_endpoint"] = l_ep.detach()
        logs["eo_total"] = (self.eo_traj_weight * l_traj + self.eo_endpoint_weight * l_ep).detach()

        # (c) λ_z / λ_y 复合一致性
        if float(getattr(lam, "z", 0.0)) > 0:
            l_cmp_z = l_cmp_z / k
            total = total + lam.z * l_cmp_z
            logs["cmp_z"] = l_cmp_z.detach()
        if float(getattr(lam, "y", 0.0)) > 0:
            l_cmp_y = l_cmp_y / k
            total = total + lam.y * l_cmp_y
            logs["cmp_y"] = l_cmp_y.detach()
        # (d) λ_nc 非坍缩
        if float(getattr(lam, "nc", 0.0)) > 0:
            l_nc = self.noncollapse_loss([z_t] + nc_states)
            total = total + lam.nc * l_nc
            logs["noncollapse"] = l_nc.detach()
        logs["total"] = total.detach()
        out = {"total": total, "logs": logs, "endpoint_plan": endpoint_plan,
               "endpoint_logs": ep_logs, "factual_path": self.factual_path,
               "blocked": {"L_pair": SIMULATOR_STATUS},
               "lambdas": {f: float(getattr(lam, f, 0.0)) for f in self.LAMBDA_FIELDS}}
        if want_diagnostics:
            with torch.no_grad():
                out["diagnostics"] = self.state_diagnostics(
                    z_t, nc_states[-1] if nc_states else None)
        return pred, out

    # ---- 三签名 forward：DDP 下推理/训练共用一个 module ----
    def forward(self, data, lambdas: Optional[SimpleNamespace] = None,
                endpoint_plan: Optional[List[dict]] = None, rng=None):
        if lambdas is None:
            return self.forecast(data)
        return self.loss_candidate_c(data, lambdas, endpoint_plan=endpoint_plan, rng=rng)

    # ---------------- simulator 接口：本轮硬阻塞 ----------------
    SIMULATOR_SCHEMA = {
        "schema_version": "candidate_c_simulator_v1",
        "required_scenario_fields": ["scenario_id", "site_id", "lat", "lon",
                                     "sim_engine", "sim_version", "t0", "horizon_days",
                                     "weather_forcing_sha256", "state_vars", "eo_mapping_sha256"],
        "required_manifest_fields": ["manifest_version", "n_scenarios", "scenario_ids",
                                     "engine_versions", "canonical_json_sha256"],
        "status": SIMULATOR_STATUS,
    }

    def simulator_pairs(self, *_a, **_k):
        """C4/C5 的 paired simulator 接口。仓库中没有正式 WOFOST/PCSE/SCOPE 情景库、
        EO↔simulator mapping 或 scenario manifest，故此处硬失败而不是静默返回假数据。"""
        raise RuntimeError(
            f"{SIMULATOR_STATUS}: 无冻结 scenario manifest 与 EO↔simulator mapping。"
            "不得用 Q3 donor、随机合成数据或伪造轨迹冒充 paired simulator truth。"
            "仅允许 synthetic fixture 走 schema/adapter 的形状 smoke。")

    @staticmethod
    def simulator_synthetic_fixture(n: int = 2, horizon: int = 20, seed: int = 0) -> dict:
        """形状/字段 smoke 专用的合成 fixture。显式自标记为非真实、不可用于任何结果。"""
        g = torch.Generator().manual_seed(int(seed))
        return {"is_synthetic_fixture": True, "usable_for_results": False,
                "status": SIMULATOR_STATUS,
                "scenario_id": [f"SYNTH-{i:04d}" for i in range(n)],
                "state_traj": torch.randn(n, horizon, 4, generator=g),
                "eo_proxy": torch.randn(n, horizon, 1, generator=g)}

    def config(self) -> dict:
        c = super().config()
        c.update({"arch": self.ARCH, "route_version": self.ROUTE_VERSION,
                  "factual_path": self.factual_path,
                  "days_per_transition_step": self.days_per_step,
                  "use_future_state_anchor": self.use_future_state_anchor,
                  "eo_traj_weight": self.eo_traj_weight,
                  "eo_endpoint_weight": self.eo_endpoint_weight,
                  "factual_endpoints": list(self.FACTUAL_ENDPOINTS),
                  "nc_min_std": self.nc_min_std,
                  "nc_min_effective_rank": self.nc_min_rank,
                  "nc_min_movement": self.nc_min_movement,
                  "cc_train_partitions": {str(k): [list(p) for p in v]
                                          for k, v in self.cc_train_partitions.items()},
                  "cc_heldout_partitions": {str(k): [list(p) for p in v]
                                            for k, v in self.cc_heldout_partitions.items()},
                  "simulator_status": SIMULATOR_STATUS})
        return c


# ---------------------------------------------------------------------------
# weights-only Phase-II fork（不是 exact resume）
# ---------------------------------------------------------------------------
PARENT_ALIAS = "terrastate/v2/default-training-anchor"
PARENT_LOGICAL_ID = "terrastate/v2/verified-resume14880@v1"
PARENT_FILE_SHA256 = "a5d2a0cc28ad7c01c7e314fd1e02ceb5022e1a9c5733870ebe89c490a594e94f"
PARENT_VALUE_SHA16 = "aa98fbd2fa302727"
PARENT_ARCH = "TerraStateV2"
PARENT_ROUTE = "terrastate_v2"
PARENT_STEP = 14880
PARENT_N_TENSORS = 255
CONTRACT_KEYS_MUST_MATCH = ("state_dim", "cond_dim", "dw", "dg", "dh", "lc_min", "lc_max")


class WarmStartError(RuntimeError):
    """warm-start 任何一项不符即抛出。绝不降级为部分加载后继续。"""


def resolve_parent(alias: str = PARENT_ALIAS, *, verify: bool = True):
    """经 tools/resolve_artifact.py 解析并重算哈希，返回 (path, logical_id)。"""
    from tools.resolve_artifact import load_registry, resolve, resolve_alias
    reg = load_registry()
    lid = resolve_alias(alias, reg)
    if lid != PARENT_LOGICAL_ID:
        raise WarmStartError(
            f"锚点 alias {alias!r} 现指向 {lid!r}，与本轮冻结的父权重 "
            f"{PARENT_LOGICAL_ID!r} 不一致。锚点被重指是运维事件，必须先核对再继续。")
    path = resolve(lid, verify=verify, reg=reg)
    return path, lid


def warm_start_candidate_c(model: TerraStateCandidateC, *, alias: str = PARENT_ALIAS,
                           ckpt_path=None, verify_file_sha: bool = True,
                           map_location: str = "cpu") -> dict:
    """把 verified-14880 的 255 个张量按 weights-only 方式装进 Candidate C。

    FAIL-CLOSED 检查清单（任一不符即抛 WarmStartError）：
      1. alias 仍指向冻结的 logical id；对象文件重算 SHA-256 与登记一致
      2. arch == TerraStateV2 且 route_version == terrastate_v2
      3. step == 14,880，张量数 == 255
      4. contract_cfg 的结构维度与本模型逐项相同
      5. 父权重每个 key 在本模型中存在且 shape 相同
      6. missing 只允许落在 NEW_MODULE_WHITELIST（本轮为空 => 必须为空）
      7. unexpected 必须为空（不得有继承不下来的父张量被丢弃）
      8. 首次 optimizer 更新之前算 inherited value_sha16，与父记录交叉核对
      9. 明确**不**加载 optimizer/scheduler/RNG/step —— 这是 fork，不是 resume
    """
    if ckpt_path is None:
        ckpt_path, logical_id = resolve_parent(alias, verify=verify_file_sha)
    else:
        logical_id = f"explicit-path:{ckpt_path}"
    file_sha = sha256_file(ckpt_path)
    if verify_file_sha and file_sha != PARENT_FILE_SHA256:
        raise WarmStartError(
            f"父权重文件 SHA-256 {file_sha} != 冻结值 {PARENT_FILE_SHA256}。FAIL CLOSED。")

    ck = torch.load(ckpt_path, map_location=map_location, weights_only=False)
    arch = (ck.get("contract_cfg", {}) or {}).get("arch") or ck.get("arch")
    route = (ck.get("contract_cfg", {}) or {}).get("route_version") or ck.get("route_version")
    if arch != PARENT_ARCH:
        raise WarmStartError(f"父权重 arch={arch!r}，本轮只接受 {PARENT_ARCH!r}。")
    if route != PARENT_ROUTE:
        raise WarmStartError(f"父权重 route_version={route!r}，只接受 {PARENT_ROUTE!r}。")
    step = int(ck.get("step", ck.get("global_step", -1)))
    if step != PARENT_STEP:
        raise WarmStartError(f"父权重 step={step} != {PARENT_STEP}。不是已验收的 14,880 锚点。")
    if "b4_state_dict" not in ck:
        raise WarmStartError("父权重缺少 b4_state_dict，schema 不符。")
    sd = ck["b4_state_dict"]
    if len(sd) != PARENT_N_TENSORS:
        raise WarmStartError(f"父权重张量数 {len(sd)} != {PARENT_N_TENSORS}。")

    pcfg = ck.get("contract_cfg", {}) or {}
    mine = model.config()
    for k in CONTRACT_KEYS_MUST_MATCH:
        if k in pcfg and pcfg[k] != mine.get(k):
            raise WarmStartError(
                f"结构维度不一致：contract_cfg[{k!r}] 父={pcfg[k]!r} 本模型={mine.get(k)!r}。")
    # 5) 逐 key/逐 shape 核对（在 load 之前，先把不匹配暴露成可读清单）
    own = model.state_dict()
    shape_mismatch, absent_in_child = [], []
    for k, v in sd.items():
        if k not in own:
            absent_in_child.append(k)
        elif tuple(own[k].shape) != tuple(v.shape):
            shape_mismatch.append({"key": k, "parent": list(v.shape), "child": list(own[k].shape)})
    if absent_in_child or shape_mismatch:
        raise WarmStartError(
            f"父权重与本模型结构不兼容：child 缺 key {absent_in_child[:8]}，"
            f"shape 不符 {shape_mismatch[:8]}。禁止部分加载。")

    missing, unexpected = model.load_state_dict(sd, strict=False)
    missing, unexpected = list(missing), list(unexpected)
    wl = tuple(model.NEW_MODULE_WHITELIST)
    not_whitelisted = [k for k in missing if not any(k.startswith(p) for p in wl)]
    if not_whitelisted:
        raise WarmStartError(
            f"missing 中有非白名单张量 {not_whitelisted[:8]}（白名单={list(wl)}）。"
            "Candidate C 不新增参数，missing 必须为空。")
    if unexpected:
        raise WarmStartError(
            f"unexpected={unexpected[:8]}：父权重有张量没被继承，血统不完整。FAIL CLOSED。")

    # 8) 首次 optimizer 更新之前，算继承子集的 value_sha 并与父记录交叉核对
    after = model.state_dict()
    inherited = {k: after[k] for k in sd.keys()}
    inh_sha = value_sha16(inherited)
    parent_sha = value_sha16(sd)
    if inh_sha != parent_sha:
        raise WarmStartError(
            f"继承张量 value_sha {inh_sha} != 父权重 {parent_sha}：加载过程改变了数值。")
    if inh_sha != PARENT_VALUE_SHA16:
        raise WarmStartError(
            f"继承张量 value_sha {inh_sha} != A02 冻结记录 {PARENT_VALUE_SHA16}。")
    max_abs = 0.0
    for k, v in sd.items():
        d = (after[k].detach().cpu().float() - v.detach().cpu().float()).abs().max().item()
        max_abs = max(max_abs, d)

    lineage = {
        "fork_kind": "weights_only_phase_ii_fork",
        "is_exact_resume": False,
        "not_exact_resume_reason": "新 optimizer / 新 scheduler / 新 RNG / phase_step 从 0 开始",
        "parent_alias": alias,
        "parent_logical_id": logical_id,
        "parent_path": str(ckpt_path),
        "parent_file_sha256": file_sha,
        "parent_arch": arch,
        "parent_route_version": route,
        "parent_step": step,
        "parent_n_tensors": len(sd),
        "inherited_n_tensors": len(inherited),
        "inherited_value_sha16": inh_sha,
        "parent_value_sha16": parent_sha,
        "expected_value_sha16": PARENT_VALUE_SHA16,
        "max_abs_diff_vs_parent": float(max_abs),
        "missing_keys": missing,
        "unexpected_keys": unexpected,
        "new_module_whitelist": list(wl),
        "child_arch": model.ARCH,
        "child_route_version": model.ROUTE_VERSION,
        "child_n_state_dict_tensors": len(after),
        "child_n_parameters": sum(1 for _ in model.parameters()),
        "child_numel": int(sum(p.numel() for p in model.parameters())),
        "phase_step": 0,
        "loaded_optimizer_state": False,
        "loaded_scheduler_state": False,
        "loaded_rng_state": False,
        "parent_had_optimizer_state": "optimizer_state_dict" in ck,
        "parent_had_scheduler_state": "scheduler_state_dict" in ck,
        "parent_optimizer_scheduler_deliberately_discarded": True,
    }
    return lineage
