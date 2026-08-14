"""CPU-only synthetic tests for the A' post-training eval tools.

No GPU, no real data, no checkpoints. Exercises the selection closure's
stale-artifact guard and run-spec parsing, and the load-bearing core on the tiny
synthetic A' model reused from scripts/smoke_plan_a_prime.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]


def _load_smoke_helpers():
    spec = importlib.util.spec_from_file_location(
        "smoke_plan_a_prime", ROOT / "scripts" / "smoke_plan_a_prime.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- Task 1 selection

def test_parse_runs_valid_and_invalid():
    from eval.aprime_select_checkpoint import _parse_runs

    runs = _parse_runs(["rescue=/a/b", "fresh=/c/d"])
    assert list(runs) == ["rescue", "fresh"]
    assert runs["rescue"].name == "b"
    with pytest.raises(ValueError):
        _parse_runs(["noequalsign"])
    with pytest.raises(ValueError):
        _parse_runs(["dup=/x", "dup=/y"])
    with pytest.raises(ValueError):
        _parse_runs([])


def test_sidecar_stale_guard():
    from eval.aprime_select_checkpoint import _sidecar_is_fresh

    fresh = {
        "provenance": {
            "checkpoint": {"sha256": "AAA"},
            "runtime_config_sha256": "CFG",
            "data": {"manifest": {"files_sha256": "MAN"}},
        }
    }
    assert _sidecar_is_fresh(fresh, checkpoint_sha256="AAA", config_sha256="CFG", manifest_files_sha256="MAN")
    # A different checkpoint -> stale (must re-evaluate, never reuse).
    assert not _sidecar_is_fresh(fresh, checkpoint_sha256="BBB", config_sha256="CFG", manifest_files_sha256="MAN")
    # A different config -> stale.
    assert not _sidecar_is_fresh(fresh, checkpoint_sha256="AAA", config_sha256="OTHER", manifest_files_sha256="MAN")
    # A different manifest -> stale.
    assert not _sidecar_is_fresh(fresh, checkpoint_sha256="AAA", config_sha256="CFG", manifest_files_sha256="OTHER")


def test_cross_run_selection_uses_same_metric_min():
    # The cross-run layer is just select_best_candidate over run winners; verify
    # it picks the lower masked-NDVI-MSE and is OOD-t agnostic.
    from eval.checkpoint_selection import select_best_candidate

    winners = [
        {"run": "rescue", "checkpoint": "r.pt", "metrics": {"ndvi_main": 0.031}},
        {"run": "fresh", "checkpoint": "f.pt", "metrics": {"ndvi_main": 0.028}},
    ]
    sel = select_best_candidate(winners, metric="ndvi_main", mode="min")
    assert sel["selected_checkpoint"] == "f.pt"


# ---------------------------------------------------------------- Task 2 Q2 load-bearing

def _tiny_model_and_batches():
    smk = _load_smoke_helpers()
    from models.dynamics.obsworld_factory import create_obsworld_v2_model

    torch.manual_seed(0)
    model = create_obsworld_v2_model(smk.tiny_config(ndvi_head=True))
    # Give the transition + head a non-identity init so ablations actually move
    # the prediction (an untrained model is identity in T and near-persistence).
    with torch.no_grad():
        model.transition.state_dynamics.output_proj.weight.normal_(0.0, 0.3)
        model.core.ndvi_residual_scale.fill_(0.5)
    batch = smk.make_batch(0)
    return model, [batch]


def test_load_bearing_reports_all_modes_and_restores_scale():
    from eval.aprime_load_bearing import evaluate_load_bearing

    model, batches = _tiny_model_and_batches()
    scale_before = float(model.core.ndvi_residual_scale.detach())
    report = evaluate_load_bearing(model, batches, red_index=2, nir_index=3, n_boot=200, bootstrap_seed=1)

    # residual scale intervention must restore the scale exactly (recoverable).
    assert float(model.core.ndvi_residual_scale.detach()) == scale_before
    # schema 5.1 fixed arms
    assert set(report["arms"]) == {"full", "closure_cut", "T_identity"}
    for a in ("closure_cut", "T_identity"):
        for f in ("delta_mse_vs_full", "delta_ci_low", "delta_ci_high", "output_change_normalized"):
            assert f in report["arms"][a], f
    # closure cut does not move the state; T_identity does.
    assert report["arms"]["closure_cut"]["state_change_normalized"] is None
    assert report["arms"]["T_identity"]["state_change_normalized"] is not None
    # real per-cube output keyed 1:1 with samples
    assert len(report["per_cube_ids"]) == report["n_samples"]
    assert len(report["per_cube_mse"]["full"]) == report["n_samples"]


def test_load_bearing_requires_ndvi_head():
    from eval.aprime_load_bearing import evaluate_load_bearing

    smk = _load_smoke_helpers()
    from models.dynamics.obsworld_factory import create_obsworld_v2_model

    model = create_obsworld_v2_model(smk.tiny_config(ndvi_head=False))
    with pytest.raises(ValueError, match="A' model with core.ndvi_head"):
        evaluate_load_bearing(model, [smk.make_batch(0)], red_index=2, nir_index=3)


def test_apply_guards_fail_closed_semantics():
    from eval.aprime_load_bearing import apply_guards

    report = {"arms": {"closure_cut": {"delta_ci_low": 0.02}, "T_identity": {"delta_ci_low": 0.05}}}
    assert apply_guards(report, min_degradation=0.01)["all_pass"] is True
    # closure_cut delta CI low 0.02 < 0.03 -> not load-bearing at that margin
    assert apply_guards(report, min_degradation=0.03)["all_pass"] is False


# ---------------------------------------------------------------- Task 2 Q3 driver

def test_driver_sensitivity_donor_moves_state_and_output_and_fail_closed():
    from eval.aprime_driver_sensitivity import (
        evaluate_driver_sensitivity, build_matched_donor_future, assert_donor_rates_complete,
    )

    smk = _load_smoke_helpers()
    from models.dynamics.obsworld_factory import create_obsworld_v2_model

    torch.manual_seed(0)
    model = create_obsworld_v2_model(smk.tiny_config(ndvi_head=True))
    with torch.no_grad():
        model.transition.state_dynamics.output_proj.weight.normal_(0.0, 0.4)
        model.core.ndvi_residual_scale.fill_(0.5)

    b = smk.make_batch(0)  # B=2
    # Put the two samples in the SAME season+geo bucket (identical C and G) but
    # keep different future weather (different D) so a matched donor exists AND
    # perturbing with it actually changes the prediction.
    with torch.no_grad():
        b["G"][1] = b["G"][0]
        b["C_path"][1] = b["C_path"][0]
    donor, verified, rates = build_matched_donor_future(
        b["D_path"], b["C_path"], b["G"], future_start_index=10, target_steps=20)
    assert bool(verified.all())
    assert rates["season"] == 1.0 and rates["geography"] == 1.0
    assert rates["not_self"] == 1.0 and rates["coverage"] == 1.0
    b["donor_D_future"] = donor
    b["donor_verified"] = True
    b["donor_rates"] = rates

    rep = evaluate_driver_sensitivity(model, [b], n_boot=100, bootstrap_seed=1)
    assert set(rep["arms"]) == {"matched", "normalized_mean", "season_geo_donor"}
    for a in ("normalized_mean", "season_geo_donor"):
        for f in ("masked_ndvi_mse", "delta_mse_vs_matched", "delta_ci_low", "delta_ci_high",
                  "mean_state_change_normalized", "mean_ndvi_output_change", "mean_rgbn_output_change"):
            assert f in rep["arms"][a], f
    assert rep["donor_rates"]["donor_coverage_rate"] == 1.0
    assert_donor_rates_complete(rep["donor_rates"])  # complete -> no raise

    # fail-closed: any donor rate < 1.0 must raise.
    with pytest.raises(ValueError):
        assert_donor_rates_complete({
            "donor_season_match_rate": 1.0, "donor_geography_match_rate": 0.5,
            "donor_not_self_rate": 1.0, "donor_coverage_rate": 1.0,
        })
    with pytest.raises(ValueError):
        assert_donor_rates_complete(None)


def test_matched_donor_future_requires_season_and_geography():
    from eval.aprime_driver_sensitivity import build_matched_donor_future

    smk = _load_smoke_helpers()
    b = smk.make_batch(0)  # B=2 random -> generally different geo buckets
    with torch.no_grad():
        # same season, DIFFERENT geography -> must NOT match (geography required).
        b["C_path"][1] = b["C_path"][0]
        b["G"][0].fill_(-5.0)
        b["G"][1].fill_(5.0)
    _, verified, rates = build_matched_donor_future(
        b["D_path"], b["C_path"], b["G"], future_start_index=10, target_steps=20)
    assert not bool(verified.any())
    assert rates["coverage"] == 0.0


# ---------------------------------------------------------------- Task 2 Q4 composition

def test_composition_reports_gap_rank_and_guards():
    from eval.aprime_composition import evaluate_composition, apply_guards

    model, batches = _tiny_model_and_batches()
    rep = evaluate_composition(model, batches, shuffle_repeats=4, seed=7)
    assert set(rep["per_depth"]) == {"10d_5+5", "20d_10+10", "20d_5+15"}
    assert rep["endpoint_metric_id"] == "masked_ndvi_mse"
    for name, block in rep["per_depth"].items():
        # schema 7.1 fields present
        for field in ("h1", "h2", "endpoint_h", "endpoint_direct_error",
                      "endpoint_composed_error", "state_path_gap_raw",
                      "state_shuffle_reference", "state_path_gap_normalized",
                      "output_path_gap", "effective_rank"):
            assert field in block, field
        assert block["h1"] + block["h2"] == block["endpoint_h"]
    # schema 7.2 state summary keyed by endpoint horizon
    for hz, srow in rep["state_summary"].items():
        for field in ("state_movement_raw", "context_state_std",
                      "state_movement_normalized", "future_state_channel_std",
                      "effective_rank", "rank_definition", "n_tokens"):
            assert field in srow, field
    # dual validation-frozen guard
    lenient = apply_guards(rep, guard_direct_threshold=1e9, guard_composed_threshold=1e9)
    assert lenient["all_pass"] is True and lenient["n_guard_pass"] == lenient["n_total"]
    strict = apply_guards(rep, guard_direct_threshold=-1.0, guard_composed_threshold=-1.0)
    assert strict["all_pass"] is False and strict["n_guard_pass"] == 0
    # guard-fail rows are not interpretation-eligible (schema 7.1)
    assert all(not r["interpretation_eligible"] for r in strict["per_depth"].values())


def test_composition_finite_only_sanitizer():
    from eval.aprime_composition import _finite_only

    cleaned = _finite_only({"a": float("nan"), "b": [1.0, float("inf")], "c": {"d": 2.0}})
    assert cleaned["a"] is None and cleaned["b"] == [1.0, None] and cleaned["c"]["d"] == 2.0


# ---------------------------------------------------------------- paired stats + provenance

def test_paired_bootstrap_ci_deterministic_and_ordered():
    from eval.aprime_paired_stats import paired_bootstrap_ci

    deltas = [(-0.01) for _ in range(50)] + [0.03, -0.02, -0.015, -0.005, 0.0]
    a = paired_bootstrap_ci(deltas, n_boot=500, ci_level=0.95, seed=42)
    b = paired_bootstrap_ci(deltas, n_boot=500, ci_level=0.95, seed=42)
    assert a == b  # deterministic under fixed seed
    assert a["ci_low"] <= a["delta_mean"] <= a["ci_high"]
    assert a["n_paired_samples"] == len(deltas)
    import pytest as _p
    with _p.raises(ValueError):
        paired_bootstrap_ci([], n_boot=10)
    with _p.raises(ValueError):
        paired_bootstrap_ci([float("nan"), 0.1], n_boot=10)


def test_paired_bootstrap_cluster_matches_length():
    from eval.aprime_paired_stats import paired_bootstrap_ci

    deltas = [-0.01, -0.02, 0.0, 0.01, -0.03, -0.02]
    tiles = ["A", "A", "B", "B", "C", "C"]
    out = paired_bootstrap_ci(deltas, n_boot=200, seed=1, cluster_ids=tiles)
    assert out["ci_method"] == "tile_cluster_percentile_bootstrap"
    assert out["n_clusters"] == 3


def test_win_tie_loss_orientation_and_tolerance():
    from eval.aprime_paired_stats import win_tie_loss

    # delta = model - baseline; RMSE lower-is-better -> negative delta is a win.
    deltas = [-0.05, -0.001, 0.0, 0.002, 0.05]
    wtl = win_tie_loss(deltas, tie_tolerance=0.003, higher_is_better=False)
    assert wtl["win"] == 1 and wtl["loss"] == 1 and wtl["tie"] == 3
    # R2 higher-is-better flips wins/losses.
    wtl2 = win_tie_loss(deltas, tie_tolerance=0.003, higher_is_better=True)
    assert wtl2["win"] == 1 and wtl2["loss"] == 1 and wtl2["tie"] == 3
    assert wtl["win"] + wtl["tie"] + wtl["loss"] == len(deltas)


def test_provenance_finite_and_shell():
    from eval.aprime_provenance import finite_only, has_non_finite, assert_all_finite, common_provenance_shell
    import pytest as _p

    assert finite_only({"a": float("inf"), "b": [float("nan"), 1.0]}) == {"a": None, "b": [None, 1.0]}
    assert has_non_finite({"x": [1.0, float("nan")]}) is True
    assert has_non_finite({"x": [1.0, 2.0]}) is False
    with _p.raises(ValueError):
        assert_all_finite({"x": float("nan")})
    shell = common_provenance_shell(
        closure_id="A_state_primary", checkpoint_sha256="CK", config_sha256="CF",
        data_manifest_sha256=None, evaluator_sha256="EV", mask_protocol_sha256="MK",
        aggregation_protocol_sha256="AG", artifact_id="q2_load_bearing",
    )
    assert shell["paper_model_id"] == "TerraState" and shell["closure_id"] == "A_state_primary"
    assert shell["data_manifest_sha256"] is None  # missing recorded as null, not fabricated
    with _p.raises(ValueError):
        common_provenance_shell(
            closure_id="C_bad", checkpoint_sha256="CK", config_sha256="CF",
            data_manifest_sha256=None, evaluator_sha256=None, mask_protocol_sha256=None,
            aggregation_protocol_sha256=None, artifact_id="x",
        )


# ---------------------------------------------------------------- direct-head export

def test_direct_ndvi_dataset_builds_valid_cube():
    import numpy as np
    xr = pytest.importorskip("xarray")
    from eval.export_greenearthnet_predictions import _direct_ndvi_dataset
    from eval.greenearthnet_protocol import PREDICTION_VARIABLE

    # A synthetic GreenEarthNet-shaped target: >=154 daily steps, small grid.
    target = xr.Dataset(coords={"time": np.arange(160), "lat": np.arange(8), "lon": np.arange(8)})
    ndvi = (np.random.rand(20, 8, 8).astype(np.float32) * 4.0) - 2.0  # out of [-1,1] on purpose
    cube = _direct_ndvi_dataset(target, ndvi)
    assert PREDICTION_VARIABLE in cube
    da = cube[PREDICTION_VARIABLE]
    assert da.dims == ("time", "lat", "lon")
    assert da.sizes["time"] == 20 and da.sizes["lat"] == 8 and da.sizes["lon"] == 8
    vals = da.values
    assert float(vals.min()) >= -1.0 and float(vals.max()) <= 1.0  # clipped
    # wrong horizon count must fail closed
    with pytest.raises(ValueError):
        _direct_ndvi_dataset(target, np.zeros((19, 8, 8), dtype=np.float32))


# ---------------------------------------------------------------- dual-NDVI accuracy gate

def test_dual_ndvi_head_and_rgbn_same_mask():
    from eval.eval_stage2_earthnet import _accumulate_dual_ndvi, _finalize_dual_ndvi
    from data.earthnet_fields import compute_ndvi

    torch.manual_seed(0)
    B, K, H, W = 2, 3, 4, 4
    target = torch.rand(B, K, 4, H, W)
    pred = (target + 0.05 * torch.randn(B, K, 4, H, W)).clamp(0, 1)
    head = (compute_ndvi(target, 2, 3).clamp(-1, 1) + 0.01).unsqueeze(2)
    veg = (torch.rand(B, K, H, W) > 0.3).float()
    sup = {"target": target, "target_veg_mask": veg}

    def _fresh():
        return {"mask": 0.0, "t": 0.0, "tt": 0.0, "head_sae": 0.0, "head_sse": 0.0,
                "rgbn_sae": 0.0, "rgbn_sse": 0.0, "head_seen": False}

    dual = _fresh()
    _accumulate_dual_ndvi(dual, {"pred": pred, "ndvi_pred": head}, sup, 2, 3)
    m = _finalize_dual_ndvi(dual, veg_masked=True)
    assert m["ndvi_metric_mask"] == "veg_clear"
    for src in ("head", "rgbn"):
        for k in ("mae", "rmse", "r2"):
            assert f"ndvi_{src}_{k}" in m, f"{src}_{k}"
    assert m["ndvi_head_rmse"] >= 0.0 and m["ndvi_rgbn_rmse"] >= 0.0
    # head is closer to target than rgbn here -> its rmse should be <= rgbn's.
    assert m["ndvi_head_rmse"] <= m["ndvi_rgbn_rmse"] + 1e-6
    # same mask pixel count used for both sources
    assert m["ndvi_metric_pixels"] == int(veg.sum())

    # head absent (non-A' checkpoint) -> head metrics are explicit None, rgbn still scored
    d2 = _fresh()
    _accumulate_dual_ndvi(d2, {"pred": pred}, sup, 2, 3)
    m2 = _finalize_dual_ndvi(d2, veg_masked=True)
    assert m2["ndvi_head_rmse"] is None and m2["ndvi_rgbn_rmse"] >= 0.0
