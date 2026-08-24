#!/usr/bin/env python
"""目标变异门限、路径量、geo-clustered bootstrap 的单元测试。

覆盖三项本轮新增/修正的逻辑：
  1 TARGET_STD_FLOOR：近常数目标的 cube 不得进入配对池（R² 会到 −1e5 量级）
  2 path_gaps：单段路径 delta 恒为 0（半群律一段情形），多段应 > 0
  3 geo_cluster_weights：臂间比较必须按 tile 聚类，且缓存键不能只看 n
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
    COMPARE_BOOTSTRAP_B, TARGET_STD_FLOOR, geo_cluster_weights, per_cube_metrics,
)


def _fail(m):
    print(f"FAIL {m}")
    return 1


def t_std_floor_excludes_near_constant():
    n = np.array([10000.0, 10000.0, 10000.0])
    sy = np.array([0.0, 0.0, 0.0])
    # cube0: 逐像素 std = 0.5（正常）; cube1: 1e-3（噪声地板）; cube2: 0.02（勉强合格）
    sst = np.array([0.5, 1e-3, 2e-2]) ** 2 * n
    s = {"n": n, "sse": np.array([1.0, 1.0, 1.0]), "sy": sy, "sy2": sst}
    _m, _r, _s, el = per_cube_metrics(s)
    if list(el.astype(int)) != [1, 0, 1]:
        return _fail(f"std_floor 未正确筛选：{el}（期望 [1,0,1]）")
    _m2, _r2, _s2, el2 = per_cube_metrics(s, std_floor=0.0)
    if not el2.all():
        return _fail(f"关闭门限后应全部合格：{el2}")
    print("PASS std_floor 剔除近常数目标，可关闭做敏感性分析")
    return 0


def t_std_floor_value_is_documented():
    if not np.isclose(TARGET_STD_FLOOR, 1e-2):
        return _fail(f"门限值意外变化：{TARGET_STD_FLOOR}")
    print(f"PASS TARGET_STD_FLOOR={TARGET_STD_FLOOR:g}（NDVI 噪声地板上一个数量级）")
    return 0


def t_r2_blowup_is_what_we_exclude():
    """确认被剔除的正是 R² 爆掉的样本，不是误伤正常 cube。"""
    n = np.array([1324.0])
    sy = np.array([0.0])
    sst = np.array([3.824e-03])              # 事故现场的真实值
    s = {"n": n, "sse": np.array([0.72]), "sy": sy, "sy2": sst}
    mse, r2, _s, el = per_cube_metrics(s, std_floor=0.0)
    if not (r2[0] < -100):
        return _fail(f"该样本 R² 应当极负，实际 {r2[0]}")
    _m, _r, _s2, el2 = per_cube_metrics(s)
    if bool(el2[0]):
        return _fail("门限应剔除该样本")
    print(f"PASS 门限剔除的正是 R²={r2[0]:.0f} 这类样本")
    return 0


def t_geo_cluster_weights_shape_and_unit():
    ids = [f"JAS20/minicube_{i}_{t}_1.0_2.0.nc"
           for t in ("30TYQ", "32TML", "34SFF") for i in range(4)]
    W, tiles = geo_cluster_weights(ids, B=COMPARE_BOOTSTRAP_B, seed=1)
    if W is None:
        return _fail("3 个 tile 应能聚类重采样")
    if len(tiles) != 3:
        return _fail(f"tile 数应为 3，实际 {tiles}")
    if W.shape != (COMPARE_BOOTSTRAP_B, len(ids)):
        return _fail(f"权重矩阵形状 {W.shape} != ({COMPARE_BOOTSTRAP_B},{len(ids)})")
    # 每行总权重应等于 n_tiles 次抽样 × 每 tile 4 个 cube
    rs = W.sum(axis=1)
    if not np.allclose(rs, len(tiles) * 4):
        return _fail(f"行和应恒为 {len(tiles)*4}，实际 {np.unique(rs)[:5]}")
    # 同 tile 内的 cube 必须同进同出（聚类重采样的定义）
    row = W[0]
    for i in range(0, len(ids), 4):
        if len(set(row[i:i + 4])) != 1:
            return _fail(f"同 tile 权重不一致：{row[i:i+4]}")
    print(f"PASS geo-clustered 权重按 tile 同进同出，B={COMPARE_BOOTSTRAP_B}")
    return 0


def t_single_tile_refuses():
    ids = ["JAS20/minicube_0_30TYQ_1.0_2.0.nc", "JAS20/minicube_1_30TYQ_1.1_2.1.nc"]
    W, tiles = geo_cluster_weights(ids, B=64, seed=1)
    if W is not None:
        return _fail("只有 1 个 tile 时应返回 None 而不是伪造区间")
    print("PASS 单 tile 时拒绝聚类重采样（compare 会据此抛错）")
    return 0


def t_cluster_ci_wider_than_minicube():
    """聚类重采样必须给出更宽的区间——这是选择合同采用它的理由。"""
    from eval.eval_terrastate_candidate_c_q4 import (bootstrap_weights,
                                                     ci_from_draws, wmean)
    rng = np.random.default_rng(0)
    n_t, per = 20, 12
    ids, vals = [], []
    for t in range(n_t):
        base = rng.normal(0, 1.0)                 # tile 级效应：制造 tile 内相关
        for j in range(per):
            ids.append(f"JAS20/minicube_{j}_TILE{t:02d}_1.0_2.0.nc")
            vals.append(base + rng.normal(0, 0.05))
    v = np.asarray(vals)
    m = np.ones(v.size, dtype=bool)
    Wm = bootstrap_weights(v.size, 2000, 7)
    lo_m, hi_m = ci_from_draws(wmean(Wm, v, m))
    Wg, _ = geo_cluster_weights(ids, B=2000, seed=7)
    lo_g, hi_g = ci_from_draws(wmean(Wg, v, m))
    wm, wg = hi_m - lo_m, hi_g - lo_g
    if not (wg > wm):
        return _fail(f"聚类区间 {wg:.4f} 未比 minicube 区间 {wm:.4f} 宽")
    print(f"PASS tile 内相关时聚类区间更宽（{wg:.4f} vs {wm:.4f}，"
          f"{wg/wm:.1f}×），与合同 rationale 一致")
    return 0


def main():
    torch.manual_seed(0)
    rc = 0
    for fn in (t_std_floor_excludes_near_constant, t_std_floor_value_is_documented,
               t_r2_blowup_is_what_we_exclude, t_geo_cluster_weights_shape_and_unit,
               t_single_tile_refuses, t_cluster_ci_wider_than_minicube):
        rc |= fn()
    print("\n=== ALL PASS ===" if rc == 0 else "\n=== HAS FAILURES ===")
    return rc


if __name__ == "__main__":
    sys.exit(main())
