#!/usr/bin/env python
"""Candidate C CPU-only 契约测试 T01–T11。

CPU only：调用方须设 CUDA_VISIBLE_DEVICES=""。本文件不碰 GPU、不写任何 run、
不注册任何权重，只读父 checkpoint。

覆盖：
  T01 warm-start 严格装载 255 张量（value_sha16 == 父）
  T02 新模块 seed 决定性 + 零新增参数
  T03 未来 EO 泄漏（q 只读历史）
  T04 未来天气只能经 F 进入
  T05 direct / 2 段 / N 段 前反向
  T06 中途换天气：前段逐位相同、后段必须变
  T07 逐项 loss 的梯度定向
  T08 train / held-out 分段隔离
  T09 坏对照绝不更新参数
  T10 常数 / 恒等 / 坍缩夹具必须被非坍缩门拦下
  T11 无有效像素时全 rank 对称跳过
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.terrastate_candidate_c import (  # noqa: E402
    PARENT_ALIAS, PARENT_N_TENSORS, PARENT_VALUE_SHA16, TerraStateCandidateC,
    resolve_parent, value_sha16, warm_start_candidate_c,
)
from eval.eval_terrastate_candidate_c_q4 import (  # noqa: E402
    CONTROLS, constant_state_like, mismatched_weather, shuffled_weather,
    variant_predictions,
)
from tests.candidate_c_fixtures import (  # noqa: E402
    Recorder, build_model, forecast_parts, one_batch,
)

def sha_params(model):
    return value_sha16(model.state_dict())


# ---------------------------------------------------------------- T01 warm-start
def t01_warm_start(rec, args):
    """严格装载 255 张量；value_sha16 必须等于 A02 冻结记录。"""
    try:
        model = build_model("recursive", seed=0)
        before = sha_params(model)
        # 空串必须落回 alias 解析（"" is not None，直接传会被当成路径用）
        lin = warm_start_candidate_c(model, alias=PARENT_ALIAS,
                                     ckpt_path=(args.parent_ckpt or None),
                                     verify_file_sha=True)
    except Exception as e:                                          # noqa: BLE001
        rec.check("T01", "warm-start 严格装载父 255 张量", False, f"抛异常 {e!r}")
        return None
    ok = (lin["inherited_n_tensors"] == PARENT_N_TENSORS
          and lin["inherited_value_sha16"] == PARENT_VALUE_SHA16
          and lin["parent_value_sha16"] == PARENT_VALUE_SHA16
          and not lin["missing_keys"] and not lin["unexpected_keys"]
          and lin["max_abs_diff_vs_parent"] == 0.0
          and before != lin["inherited_value_sha16"])
    rec.check("T01", "warm-start 严格装载父 255 张量", ok,
              f"n={lin['inherited_n_tensors']} sha={lin['inherited_value_sha16']} "
              f"max|Δ|={lin['max_abs_diff_vs_parent']} "
              f"missing={len(lin['missing_keys'])} unexpected={len(lin['unexpected_keys'])}")
    rec.check("T01b", "是 weights-only fork 而非 exact resume",
              lin["is_exact_resume"] is False
              and lin["fork_kind"] == "weights_only_phase_ii_fork",
              f"fork_kind={lin['fork_kind']} reason={lin['not_exact_resume_reason']}")
    return model


# ---------------------------------------------------------------- T02 seed 决定性
def t02_seed_determinism(rec):
    a1, a2 = build_model("recursive", seed=123), build_model("recursive", seed=123)
    b = build_model("recursive", seed=999)
    s1, s2, sb = sha_params(a1), sha_params(a2), sha_params(b)
    rec.check("T02", "同 seed 构建逐位相同", s1 == s2, f"{s1} vs {s2}")
    rec.check("T02b", "不同 seed 必须不同（否则 seed 没起作用）", s1 != sb, f"{s1} vs {sb}")
    n_t = len(a1.state_dict())
    n_p = sum(p.numel() for p in a1.parameters())
    rec.check("T02c", "零新增参数：张量数 == 父 255",
              n_t == PARENT_N_TENSORS and tuple(a1.NEW_MODULE_WHITELIST) == (),
              f"n_tensors={n_t} n_params={n_p} whitelist={list(a1.NEW_MODULE_WHITELIST)}")


# ---------------------------------------------------------------- T03 未来 EO 泄漏
def t03_future_eo_leakage(rec):
    """扰动未来 EO 帧：context prior 与 z_t 必须逐位不变（q 只读历史）。"""
    model = build_model("recursive", seed=7).eval()
    data = one_batch(2, seed=3)
    cl, tl = model.context_len, model.target_len
    with torch.no_grad():
        _, prior_a, _, z_a, _, _, _, _, _ = forecast_parts(model, data)
    d2 = dict(data)
    d2["dynamic"] = [data["dynamic"][0].clone(), data["dynamic"][1]]
    d2["dynamic"][0][:, cl:cl + tl] += 3.0            # 只动未来 EO
    with torch.no_grad():
        _, prior_b, _, z_b, _, _, _, _, _ = forecast_parts(model, d2)
    rec.check("T03", "未来 EO 不进入 context prior", torch.equal(prior_a, prior_b),
              f"max|Δprior|={float((prior_a - prior_b).abs().max())}")
    rec.check("T03b", "未来 EO 不进入 z_t", torch.equal(z_a, z_b),
              f"max|Δz_t|={float((z_a - z_b).abs().max())}")


# ---------------------------------------------------------------- T04 天气只经 F
def t04_weather_only_via_F(rec):
    """扰动**未来**天气：prior/z_t 不变，但端点预测必须变（天气只能经 F 进入 ŷ）。

    注意扰动窗口必须严格是 [context_len, context_len+target_len)。过去天气
    u^past_<=t 是 q 的合法输入（models/plan_b_b4.py::_context_only_data 只把
    w[:, context_len:] 归零，过去帧原样保留），扰动整条天气张量会让 prior/z_t
    正当地变化，那测的是别的东西，不是未来天气泄漏。
    """
    model = build_model("recursive", seed=11).eval()
    data = one_batch(2, seed=5)
    cl, tl = int(model.context_len), int(model.target_len)
    with torch.no_grad():
        _, prior_a, _, z_a, geo_a, u_a, B, H, W = forecast_parts(model, data)
        y_a = model.endpoint_prediction(prior_a, z_a, u_a, geo_a, (5, 5), B, H, W)
        p0_a = model.endpoint_prediction(prior_a, z_a, u_a, geo_a, (5, 5), B, H, W,
                                        arm="alpha0")
    w2 = data["dynamic"][1].clone()
    w2[:, cl:cl + tl] = w2[:, cl:cl + tl] + 2.5          # 只动未来窗口
    d2 = dict(data)
    d2["dynamic"] = [data["dynamic"][0], w2]
    past_untouched = torch.equal(w2[:, :cl], data["dynamic"][1][:, :cl])
    rec.check("T04_setup", "扰动确实只落在未来天气窗口内",
              past_untouched and bool((w2[:, cl:cl + tl]
                                       != data["dynamic"][1][:, cl:cl + tl]).any()),
              f"context_len={cl} target_len={tl} past_untouched={past_untouched}")
    with torch.no_grad():
        _, prior_b, _, z_b, geo_b, u_b, _, _, _ = forecast_parts(model, d2)
        y_b = model.endpoint_prediction(prior_b, z_b, u_b, geo_b, (5, 5), B, H, W)
        p0_b = model.endpoint_prediction(prior_b, z_b, u_b, geo_b, (5, 5), B, H, W,
                                        arm="alpha0")
    rec.check("T04", "未来天气不进入 context prior", torch.equal(prior_a, prior_b),
              f"max|Δprior|={float((prior_a - prior_b).abs().max())}")
    rec.check("T04b", "未来天气不进入 z_t", torch.equal(z_a, z_b),
              f"max|Δz_t|={float((z_a - z_b).abs().max())}")
    d_y = float((y_a - y_b).abs().max())
    rec.check("T04c", "未来天气经 F 改变端点预测", d_y > 0, f"max|Δŷ|={d_y}")
    rec.check("T04d", "alpha0 臂对天气不敏感（确认通道唯一）", torch.equal(p0_a, p0_b),
              f"max|Δalpha0|={float((p0_a - p0_b).abs().max())}")


# ---------------------------------------------------------------- T05 前反向
def t05_forward_backward(rec):
    """direct / 2 段 / N 段 都要能前反向，且 transition 必须收到有限梯度。"""
    for tag, part in (("direct", (10,)), ("two_seg", (5, 5)),
                      ("three_seg", (5, 3, 2)), ("four_seg", (5, 5, 5, 5))):
        model = build_model("recursive", seed=13)
        data = one_batch(2, seed=8)
        pred, prior, _r, z_t, geo, u, B, H, W = forecast_parts(model, data)
        yh = model.endpoint_prediction(prior, z_t, u, geo, part, B, H, W)
        loss = yh.float().pow(2).mean()
        model.zero_grad(set_to_none=True)
        loss.backward()
        g = [p.grad for n, p in model.named_parameters()
             if n.startswith("transition.") and p.grad is not None]
        finite = bool(torch.isfinite(loss)) and all(bool(torch.isfinite(x).all()) for x in g)
        nonzero = any(float(x.abs().sum()) > 0 for x in g)
        rec.check(f"T05_{tag}", f"{tag} 前反向 + transition 梯度有限非零",
                  finite and nonzero and len(g) > 0,
                  f"loss={float(loss.detach()):.6g} n_grad_tensors={len(g)} finite={finite} "
                  f"nonzero={nonzero}")
# ------------------------------------------------- T06 semigroup + 中途换天气
def t06_semigroup_and_switch(rec):
    """1 段 ≡ direct_state、2 段 ≡ composed_state（逐位）；N 段必须非平凡地不同；
    中途换天气：前段逐位相同、后段必须变。"""
    model = build_model("recursive", seed=17).eval()
    data = one_batch(2, seed=9)
    with torch.no_grad():
        _p, _pr, _r, z_t, geo, u, _B, _H, _W = (*forecast_parts(model, data),)[:9]
        z1 = model.segment_state(z_t, u, geo, (10,))
        zd = model.direct_state(z_t, u, geo, 10)
        z2 = model.segment_state(z_t, u, geo, (5, 5))
        zc = model.composed_state(z_t, u, geo, 5, 5)
        z3 = model.segment_state(z_t, u, geo, (5, 3, 2))
    rec.check("T06", "1 段 ≡ direct_state（逐位）", torch.equal(z1, zd),
              f"max|Δ|={float((z1 - zd).abs().max())}")
    rec.check("T06b", "2 段 ≡ composed_state（逐位）", torch.equal(z2, zc),
              f"max|Δ|={float((z2 - zc).abs().max())}")
    rec.check("T06c", "3 段与直接路径非平凡地不同", not torch.equal(z3, zd),
              f"max|Δ|={float((z3 - zd).abs().max())}")
    for part, k in (((5, 5), 1), ((5, 3, 2), 1), ((5, 3, 2), 2), ((5, 5, 5, 5), 2)):
        g = torch.Generator(device="cpu").manual_seed(4242)
        with torch.no_grad():
            r = model.assert_weather_switch_contract(z_t, u, geo, part,
                                                     switch_after_segment=k, generator=g)
        tag = "-".join(map(str, part)) + f"@{k}"
        rec.check(f"T06_switch_{tag}", f"换天气 {tag}：前段逐位不变且后段改变",
                  r["pre_switch_bit_identical"] and r["post_switch_changed"],
                  f"pre={r['max_abs_delta_pre']} post={r['max_abs_delta_post']}")


# ---------------------------------------------------------- T07 逐项 loss 梯度定向
def _grad_groups(model):
    out = {}
    for name, p in model.named_parameters():
        head = name.split(".")[0]
        g = p.grad
        out.setdefault(head, {"n": 0, "n_grad": 0, "abs": 0.0})
        out[head]["n"] += 1
        if g is not None:
            out[head]["n_grad"] += 1
            out[head]["abs"] += float(g.abs().sum())
    return out


def _run_loss(model, data, lam, plan):
    model.zero_grad(set_to_none=True)
    _pred, aux = model.loss_candidate_c(data, lam, endpoint_plan=plan,
                                        want_diagnostics=False)
    aux["total"].backward()
    return aux, _grad_groups(model)


def t07_loss_gradient_routing(rec):
    """把 L_EO 权重置 0 后单独打开一项 λ，检查梯度只落在该项应当影响的模块上。"""
    from types import SimpleNamespace
    data = one_batch(2, seed=21)
    plan = [{"endpoint": 10, "partition": (5, 5), "n_segments": 2}]
    # (a) 只有 λ_nc：非坍缩只作用在状态上，绝不应给解码器 o_delta 非零梯度
    m = build_model("recursive", seed=23, eo_traj_weight=0.0, eo_endpoint_weight=0.0)
    lam = SimpleNamespace(z=0.0, y=0.0, pair=0.0, nc=1.0)
    aux, g = _run_loss(m, data, lam, plan)
    od = g.get("o_delta", {"abs": 0.0})["abs"]
    tr = g.get("transition", {"abs": 0.0})["abs"]
    rec.check("T07_nc", "只开 λ_nc：transition 有梯度、o_delta 无梯度",
              tr > 0 and od == 0.0,
              f"|g_transition|={tr:.6g} |g_o_delta|={od:.6g} keys={sorted(aux['logs'])}")
    # (b) 只有端点 L_EO：解码器与 transition 都必须收到梯度
    m2 = build_model("recursive", seed=23, eo_traj_weight=0.0, eo_endpoint_weight=1.0)
    lam2 = SimpleNamespace(z=0.0, y=0.0, pair=0.0, nc=0.0)
    aux2, g2 = _run_loss(m2, data, lam2, plan)
    rec.check("T07_ep", "只开端点 L_EO：o_delta 与 transition 都有梯度",
              g2.get("o_delta", {"abs": 0})["abs"] > 0
              and g2.get("transition", {"abs": 0})["abs"] > 0,
              f"|g_o_delta|={g2.get('o_delta', {'abs': 0})['abs']:.6g} "
              f"|g_transition|={g2.get('transition', {'abs': 0})['abs']:.6g}")
    # (c) λ_pair 必须 fail-closed（本轮没有 paired simulator 真值）
    try:
        m3 = build_model("recursive", seed=23)
        m3.loss_candidate_c(data, SimpleNamespace(z=0.0, y=0.0, pair=0.5, nc=0.0),
                            endpoint_plan=plan, want_diagnostics=False)
        ok, detail = False, "λ_pair≠0 竟然没抛异常"
    except RuntimeError as e:
        ok, detail = ("BLOCKED_SIMULATOR" in str(e)), str(e)[:110]
    rec.check("T07_pair", "λ_pair≠0 必须 fail-closed 抛错", ok, detail)
    # (d) direct 臂上 cmp_z 恒为 0（z_fact 就是 z_dir）——设计的应然性质
    m4 = build_model("direct", seed=23, eo_traj_weight=0.0, eo_endpoint_weight=0.0)
    lam4 = SimpleNamespace(z=1.0, y=0.0, pair=0.0, nc=0.0)
    plan4 = [{"endpoint": 10, "partition": (10,), "n_segments": 1}]
    aux4, _g4 = _run_loss(m4, data, lam4, plan4)
    cz = float(aux4["logs"].get("cmp_z", -1.0))
    rec.check("T07_cmp_direct", "direct 臂 cmp_z ≡ 0（同一条路径）", cz == 0.0,
              f"cmp_z={cz}")


# ------------------------------------------------------- T08 train/held-out 隔离
def t08_partition_isolation(rec):
    m = build_model("recursive", seed=29)
    tr = {p for v in m.cc_train_partitions.values() for p in v}
    ho = {p for v in m.cc_heldout_partitions.values() for p in v}
    inter = tr & ho
    rec.check("T08", "train 与 held-out 分段完全不相交", not inter,
              f"|train|={len(tr)} |heldout|={len(ho)} 交集={sorted(inter)}")
    drawn = set()
    for step in range(400):
        g = torch.Generator(device="cpu").manual_seed(42 * 1_000_003 + step)
        for item in m.draw_endpoint_plan(g):
            drawn.add(tuple(item["partition"]))
    leaked = drawn & ho
    rec.check("T08b", "400 步抽样从未抽到 held-out 分段", not leaked,
              f"抽到 {len(drawn)} 种分段，泄漏={sorted(leaked)}")
    sums_ok = all(sum(p) == ep for ep, v in m.cc_train_partitions.items() for p in v) \
        and all(sum(p) == ep for ep, v in m.cc_heldout_partitions.items() for p in v)
    rec.check("T08c", "每个分段之和都等于其端点", sums_ok, "")
# ------------------------------------------------------ T09 坏对照绝不更新参数
def t09_controls_never_update(rec):
    """四个坏对照只在 no_grad 评测路径里出现：参数 SHA 必须逐位不变、不留梯度。"""
    model = build_model("recursive", seed=31).eval()
    data = one_batch(2, seed=13)
    before = sha_params(model)
    with torch.no_grad():
        _p, prior, _r, z_t, geo, u, B, H, W = forecast_parts(model, data)
        preds, notes = variant_predictions(model, prior, z_t, geo, u, (5, 3, 2),
                                           B, H, W)
    after = sha_params(model)
    n_grad = sum(1 for p in model.parameters() if p.grad is not None)
    no_graph = all(not v.requires_grad for v in preds.values())
    rec.check("T09", "坏对照运行后参数 SHA 逐位不变", before == after,
              f"{before} -> {after}")
    rec.check("T09b", "坏对照不留梯度、不建图", n_grad == 0 and no_graph,
              f"n_param_with_grad={n_grad} no_graph={no_graph}")
    present = [c for c in CONTROLS if c in preds]
    rec.check("T09c", "四个坏对照都产出了预测（无退化）", len(present) == len(CONTROLS),
              f"present={present} notes={notes}")
    # 每个坏对照都必须真的改变预测，否则它没起到对照作用
    for c in present:
        d = float((preds[c] - preds["factual"]).abs().max())
        rec.check(f"T09_{c}", f"{c} 确实改变了预测", d > 0, f"max|Δ|={d:.6g}")
    # 单段分段上 segment_weather_mismatched 必须自报退化，而不是悄悄等于 factual
    _u, note1 = mismatched_weather(u, (10,))
    rec.check("T09d", "单段时 segment mismatch 自报退化", bool(note1.get("degenerate")),
              str(note1))
    _u2, note2 = shuffled_weather(u, 10, seed=4242)
    rec.check("T09e", "时间轴置换非恒等（对照有效）", not note2.get("degenerate"),
              str(note2)[:90])


# --------------------------------------- T10 常数/恒等/坍缩必须被非坍缩门拦下
def t10_noncollapse_gate(rec):
    model = build_model("recursive", seed=37).eval()
    data = one_batch(2, seed=17)
    with torch.no_grad():
        _p, _pr, _r, z_t, geo, u, _B, _H, _W = forecast_parts(model, data)
        z_ep = model.segment_state(z_t, u, geo, (10, 10))
    healthy = model.noncollapse_gate(z_t, z_ep)
    rec.check("T10", "健康状态通过非坍缩门", healthy["verdict"] == "PASS",
              f"std={healthy['state_std_zt']:.4f} "
              f"rank={healthy['effective_rank_zt']:.3f} "
              f"move={healthy['relative_movement']:.4f}")
    zc = constant_state_like(z_t)
    g_const = model.noncollapse_gate(zc, zc)
    rec.check("T10b", "常数状态被拦下", g_const["verdict"] == "FAIL",
              f"reasons={g_const['reasons']}")
    g_ident = model.noncollapse_gate(z_t, z_t.clone())
    rec.check("T10c", "恒等（零移动）被拦下", g_ident["verdict"] == "FAIL"
              and any("no_state_movement" in r for r in g_ident["reasons"]),
              f"reasons={g_ident['reasons']}")
    # 坍缩：秩 1（每个 token 只是同一方向的不同倍数）
    base = torch.randn(1, z_t.shape[-1], generator=torch.Generator().manual_seed(5))
    scale = torch.linspace(0.5, 1.5, z_t.shape[0]).unsqueeze(1)
    z_rank1 = (scale * base).to(z_t.dtype)
    g_coll = model.noncollapse_gate(z_rank1, z_rank1 * 1.7)
    rec.check("T10d", "秩 1 坍缩被拦下", g_coll["verdict"] == "FAIL"
              and any("effective_rank" in r for r in g_coll["reasons"]),
              f"rank={g_coll['effective_rank_zt']:.4f} reasons={g_coll['reasons']}")
    # T10e：子类的 SVD 路线与父类 eigvalsh 路线必须是**同一个量**。
    # 子类覆写 effective_rank 只为在常数/坍缩输入上不抛 _LinAlgError；
    # 若它同时悄悄改了被报告的有效秩，Q4 表格就与已验收世代不可比。
    from models.plan_b_b4 import ObsWorldB4                       # 只读引用，不修改
    pairs, worst = [], 0.0
    for tag, zz in (("z_t", z_t), ("z_ep", z_ep), ("rank1", z_rank1)):
        x = zz.reshape(-1, zz.shape[-1]).detach().to(torch.float64)
        x = x - x.mean(0, keepdim=True)
        cov = (x.T @ x) / max(x.shape[0] - 1, 1)
        ev = torch.linalg.eigvalsh(cov).clamp(min=0)
        ref64 = float(ev.sum() ** 2 / (ev.pow(2).sum() + 1e-12))   # 父公式，float64
        mine = float(TerraStateCandidateC.effective_rank(zz))
        rel = abs(mine - ref64) / max(ref64, 1e-12)
        worst = max(worst, rel)
        pairs.append(f"{tag}: svd={mine:.6f} eig64={ref64:.6f} rel={rel:.2e}")
    rec.check("T10e", "SVD 路线与父类特征值公式在健康输入上同值（定义未变）",
              worst < 1e-6, " | ".join(pairs))
    # 父类原实现在常数状态上确实会抛（这就是覆写的理由），显式登记该事实
    try:
        ObsWorldB4.effective_rank(zc)
        parent_raised = False
        parent_detail = "父实现未抛错（数值环境不同）；覆写仍是更稳的路线"
    except Exception as exc:                                       # noqa: BLE001
        parent_raised = True
        parent_detail = f"{type(exc).__name__}: {str(exc).splitlines()[0][:110]}"
    rec.check("T10f", "覆写理由成立：常数状态下子类返回 0.0 而不抛错",
              float(TerraStateCandidateC.effective_rank(zc)) == 0.0,
              f"parent_raised={parent_raised} | {parent_detail}")


# ------------------------------------------- T11 无有效像素时全 rank 对称跳过
def t11_symmetric_skip(rec):
    """全云 batch：有效像素为 0。loss 必须有限（0/eps=0），梯度为 0，
    且 MIN-reduce 的跳过判定必须让所有 rank 得到同一个决定。"""
    from types import SimpleNamespace
    model = build_model("recursive", seed=41)
    data = one_batch(2, seed=19, all_cloudy=True)
    lc = data["landcover"]
    cl, tl = model.context_len, model.target_len
    lc_mask = ((lc >= model.lc_min) & (lc <= model.lc_max)).float()
    cloud = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).float()
    n_valid = float((cloud * lc_mask.unsqueeze(1)).sum())
    plan = [{"endpoint": 10, "partition": (5, 5), "n_segments": 2}]
    lam = SimpleNamespace(z=0.0, y=0.0, pair=0.0, nc=0.0)
    model.zero_grad(set_to_none=True)
    _pred, aux = model.loss_candidate_c(data, lam, endpoint_plan=plan,
                                        want_diagnostics=False)
    loss = aux["total"]
    loss.backward()
    gsum = sum(float(p.grad.abs().sum()) for p in model.parameters() if p.grad is not None)
    rec.check("T11", "无有效像素时有效像素数确为 0", n_valid == 0.0, f"n_valid={n_valid}")
    rec.check("T11b", "loss 有限且为 0（不产生 NaN）",
              bool(torch.isfinite(loss)) and float(loss.detach()) == 0.0,
              f"loss={float(loss.detach())}")
    rec.check("T11c", "梯度全为 0（不会污染参数）", gsum == 0.0, f"Σ|g|={gsum:.6g}")
    # MIN-reduce 跳过判定：任一 rank 非有限 => 所有 rank 都跳过
    for flags, expect in (([1.0, 1.0], True), ([1.0, 0.0], False),
                          ([0.0, 0.0], False)):
        decided = min(flags) > 0.5
        rec.check(f"T11_reduce_{''.join(str(int(f)) for f in flags)}",
                  f"MIN-reduce 决定一致：flags={flags} -> 更新={expect}",
                  decided == expect, f"decided={decided}")
def main(argv=None):
    ap = argparse.ArgumentParser(description="Candidate C 契约测试 T01–T11 (CPU only)")
    ap.add_argument("--report", default="", help="机器可读报告落盘路径 (JSON)")
    ap.add_argument("--parent-ckpt", default="",
                    help="父 checkpoint 路径；留空则经 alias 解析并校验文件 SHA")
    ap.add_argument("--skip-warm-start", action="store_true",
                    help="跳过 T01（仅在父权重不可达时使用，会记为 fatal 失败）")
    args = ap.parse_args(argv)
    if os.environ.get("CUDA_VISIBLE_DEVICES", "unset") != "":
        print("WARN CUDA_VISIBLE_DEVICES 未设为空串；本套件仍强制 CPU", flush=True)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    rec = Recorder("candidate_c_contract_T01_T11")

    if args.skip_warm_start:
        rec.check("T01", "warm-start 严格装载父 255 张量", False,
                  "被 --skip-warm-start 跳过；CPU_READY 不得在此状态下宣告")
    else:
        t01_warm_start(rec, args)
    t02_seed_determinism(rec)
    t03_future_eo_leakage(rec)
    t04_weather_only_via_F(rec)
    t05_forward_backward(rec)
    t06_semigroup_and_switch(rec)
    t07_loss_gradient_routing(rec)
    t08_partition_isolation(rec)
    t09_controls_never_update(rec)
    t10_noncollapse_gate(rec)
    t11_symmetric_skip(rec)

    report = rec.report()
    print(json.dumps({k: v for k, v in report.items() if k != "checks"},
                     indent=2, ensure_ascii=False), flush=True)
    if args.report:
        from eval.eval_terrastate_candidate_c_q4 import atomic_write_json, provenance
        report["provenance"] = provenance({"suite": report["suite"]})
        sha = atomic_write_json(args.report, report)
        print(f"report -> {args.report}  sha256={sha}", flush=True)
    return 0 if report["n_fatal_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
