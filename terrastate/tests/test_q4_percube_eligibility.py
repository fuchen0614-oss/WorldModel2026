#!/usr/bin/env python
"""per-cube 资格掩码的单元测试。

回归的是一个真实事故：3 个 batch 里有 12 个 cube 在天气错配后与原天气逐位相同，
原实现整批跳过 -> series 长度 464 != 476 -> 配对校验报错；曾经的"修复"是整条
variant 删掉，代价是 broken_control 的对照从 76 组缩到 57 组（静默缩小输入集）。
正确语义：series 长度恒等于 cube 数，合格性用逐 cube 掩码表达。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.eval_terrastate_candidate_c_q4 import (  # noqa: E402
    StatGrid, _pooled_mse_on, _variant_elig, mismatched_weather,
)


def _fail(msg):
    print(f"FAIL {msg}")
    return 1


def t_single_segment_still_degenerate():
    u = torch.randn(3, 10, 4)
    out, note = mismatched_weather(u, (10,))
    if out is not None or not note.get("degenerate"):
        return _fail("单段必须整条退化（真的没有『另一段』）")
    print("PASS 单段仍自报结构性退化")
    return 0


def t_mixed_batch_percube_mask():
    """一个 batch 里混入常天气 cube：掩码只标它，不牵连其他 cube。"""
    B, T, D = 4, 10, 3
    u = torch.randn(B, T, D)
    u[1] = 7.0                      # cube 1 未来窗口天气恒定 -> 换段等于没换
    u[3] = -2.5                     # cube 3 同理
    out, note = mismatched_weather(u, (5, 5))
    if out is None or note.get("degenerate"):
        return _fail("多段不该整条退化")
    m = note["cube_eligible"]
    if list(m.astype(int)) != [1, 0, 1, 0]:
        return _fail(f"逐 cube 掩码错：{m}")
    if note["n_cube_unchanged"] != 2:
        return _fail(f"n_cube_unchanged 错：{note['n_cube_unchanged']}")
    # 被标为合格的 cube 必须真的变了；不合格的必须真的没变
    for i in range(B):
        changed = bool((out[i] != u[i]).any())
        if changed != bool(m[i]):
            return _fail(f"cube {i} 掩码与实际变化不符 changed={changed} mask={m[i]}")
    print("PASS 混合 batch 的逐 cube 掩码精确对齐实际变化")
    return 0


def t_statgrid_length_and_mask():
    """核心契约：无论是否合格，series 长度恒等于 cube 数。"""
    g = StatGrid()
    g.cube_ids = ["a", "b", "c", "d"]
    n = torch.tensor([10.0, 10.0, 10.0, 10.0])
    sse = torch.tensor([1.0, 2.0, 3.0, 4.0])
    sy = torch.tensor([5.0, 5.0, 5.0, 5.0])
    sy2 = torch.tensor([30.0, 30.0, 30.0, 30.0])
    g.add(10, (5, 5), "factual", n, sse, sy, sy2)
    g.add(10, (5, 5), "segment_weather_mismatched", n, sse * 2, sy, sy2,
          cube_elig=np.array([True, False, True, False]))
    series = g.finalize()          # 不该抛异常
    for k, v in series.items():
        if v["n"].shape[0] != 4:
            return _fail(f"{k} 长度 {v['n'].shape[0]} != 4")
    fe = _variant_elig(series["ep10|5-5::factual"])
    me = _variant_elig(series["ep10|5-5::segment_weather_mismatched"])
    if not fe.all():
        return _fail("factual 掩码应为全真")
    if list(me.astype(int)) != [1, 0, 1, 0]:
        return _fail(f"mismatched 掩码未落库：{me}")
    print("PASS StatGrid 保住 476 式长度契约，掩码独立落库")
    return 0


def t_pooled_ratio_same_cube_set():
    """比值的分子分母必须落在同一批 cube 上。"""
    s_f = {"n": np.array([10.0, 10.0, 10.0]), "sse": np.array([1.0, 100.0, 2.0])}
    s_c = {"n": np.array([10.0, 10.0, 10.0]), "sse": np.array([4.0, 100.0, 8.0])}
    mask = np.array([True, False, True])
    pf = _pooled_mse_on(s_f, mask)
    pc = _pooled_mse_on(s_c, mask)
    if not np.isclose(pf, 3.0 / 20.0) or not np.isclose(pc, 12.0 / 20.0):
        return _fail(f"pooled 未按掩码计算 pf={pf} pc={pc}")
    if not np.isclose(pf / pc, 0.25):
        return _fail(f"ratio 错 {pf / pc}")
    print("PASS pooled 比值在同一 cube 子集上计算")
    return 0


def t_degenerate_batch_does_not_shrink_series():
    """整批都没变的极端情况：仍然 append，只是全部不合格。"""
    B, T, D = 3, 10, 2
    u = torch.full((B, T, D), 4.0)          # 所有 cube 天气全常数
    out, note = mismatched_weather(u, (5, 5))
    if out is None:
        return _fail("整批未变也必须返回张量，否则 series 会短一截")
    if note.get("degenerate"):
        return _fail("这不是结构性退化，不该整条标退化")
    if bool(note["cube_eligible"].any()):
        return _fail("整批都没变时掩码应全假")
    if not note.get("all_cubes_unchanged"):
        return _fail("应标记 all_cubes_unchanged 供 provenance 留证")
    g = StatGrid()
    g.cube_ids = ["a", "b", "c"]
    z = torch.zeros(B)
    g.add(10, (5, 5), "segment_weather_mismatched", z + 10, z + 1, z + 5, z + 30,
          cube_elig=note["cube_eligible"])
    series = g.finalize()
    if series["ep10|5-5::segment_weather_mismatched"]["n"].shape[0] != 3:
        return _fail("长度契约被破坏")
    print("PASS 整批不合格也不缩短 series（长度契约与合格性解耦）")
    return 0


def t_mask_length_guard():
    g = StatGrid()
    g.cube_ids = ["a", "b"]
    z = torch.zeros(2)
    try:
        g.add(10, (5, 5), "x", z, z, z, z, cube_elig=np.array([True]))
    except Exception:
        print("PASS 掩码长度与 batch 不符时明确报错")
        return 0
    return _fail("掩码长度不符应报错而不是静默截断")


def main():
    torch.manual_seed(0)
    rc = 0
    for fn in (t_single_segment_still_degenerate, t_mixed_batch_percube_mask,
               t_statgrid_length_and_mask, t_pooled_ratio_same_cube_set,
               t_degenerate_batch_does_not_shrink_series, t_mask_length_guard):
        rc |= fn()
    print("\n=== ALL PASS ===" if rc == 0 else "\n=== HAS FAILURES ===")
    return rc


if __name__ == "__main__":
    sys.exit(main())
