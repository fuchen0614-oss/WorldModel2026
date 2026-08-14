"""Local smoke for Plan A' (accuracy-aligned) — NO training, NO GPU required.

Verifies the A' wiring end to end on a tiny synthetic model/batch:
  1  model builds with the NDVI head; forward emits ndvi_pred
  2  initial residual == persistence (zero-init scale)
  3  loss computes masked-L2 ndvi_main + ndvi_consistency, finite
  4  q / T / O(reflectance) / ndvi_residual_scale receive gradients
  5  ndvi_head is wired (grad flows once the residual scale is non-zero)
  6  future-satellite invariance: z0 does not depend on x_target
  7  weather sensitivity: perturbing the future driver path moves zh + outputs
  8  endpoint-guard: decoding z0 != decoding zh (prediction depends on zh)
  9  save/load round-trip is bit-identical
 10  warm-start: a head-less Stage2 state_dict loads non-strict, missing == head
 11  optimizer grouping: q at backbone_lr, head/T/O (incl. NDVI head) at lr
 12  data veg mask: clear x SCL-valid x vegetation, and veg subset of clear
"""

from __future__ import annotations

import copy

import numpy as np
import torch

from data.stage2_contract import model_input_view
from data.earthnet_physical_conditioning import PHYSICAL4_FEATURE_NAMES
from data.earthnet_fields import compute_ndvi
from models.dynamics.obsworld_factory import create_obsworld_v2_model
from models.losses.earthnet_forecasting import EarthNetForecastLoss

PASS, FAIL = "PASS", "FAIL"
_results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, bool(ok), detail))
    print(f"[{PASS if ok else FAIL}] {name}  {detail}")


def tiny_config(ndvi_head: bool) -> dict:
    return {
        "data": {"stage2_protocol": "earthnet2021x_path_v2", "driver_protocol": "physical4_v1"},
        "model": {
            "family": "obsworld_stage2_v2",
            "forecast_mode": "direct_path_physical4",
            "driver_protocol": "physical4_v1",
            "future_start_index": 10,
            "target_steps": 20,
            "require_stage15_checkpoint": False,
            "use_phi_encoder": True,
            "ndvi_head": ndvi_head,
            "residual_scale_init": 1.0,
            "conditions": {"use_D": True, "use_G": True, "use_h": True},
            "encoder": {
                "type": "MultiModalViTEncoderFiLM", "from_checkpoint": None, "freeze": False,
                "img_size": 32, "s1_channels": 2, "s2_channels": 12, "patch_size": 16,
                "embed_dim": 32, "depth": 1, "num_heads": 4, "mlp_ratio": 2.0, "dropout": 0.0,
                "phi_dim": 32, "use_film": True, "use_cross_attention": False, "film_start_layer": 0,
            },
            "phi_encoder": {
                "type": "PureImagingConditionEncoder", "embed_dim": 32, "sun_dim": 8,
                "sar_geom_dim": 8, "dropout": 0.0, "condition_dropout": 0.0, "use_sar_geometry": True,
            },
            "state_projector": {"type": "SpatialStateProjector", "in_dim": 32, "state_dim": 16, "hidden_dim": 32},
            "band_adapter": {
                "type": "EarthNetInputAdapter", "in_channels": 4, "out_channels": 12,
                "hidden_channels": 16, "mode": "linear", "source_to_canonical": [1, 2, 3, 8],
            },
            "context_aggregator": {
                "type": "ContextStateAggregator", "state_dim": 16, "hidden_dim": 32, "dropout": 0.0,
                "max_context_frames": 10, "min_token_clear_fraction": 0.25, "zero_unobserved_tokens": True,
            },
            "interval_driver_encoder": {
                "type": "IntervalDriverEncoder", "input_dim": 4,
                "feature_names": list(PHYSICAL4_FEATURE_NAMES), "calendar_dim": 2, "token_dim": 16,
                "hidden_dim": 32, "out_dim": 8, "num_layers": 1, "num_heads": 4, "dropout": 0.0,
                "max_segment_length": 20,
            },
            "horizon_encoder": {"type": "HorizonEncoder", "out_dim": 8, "hidden_dim": 16, "max_h_days": 100.0},
            "geo_tokenizer": {"type": "GeoTokenizer", "in_channels": 1, "geo_dim": 4, "img_size": 16, "patch_size": 8},
            "dynamics": {
                "type": "StateDynamicsModule", "latent_dim": 16, "dynamics_type": "mlp", "driver_dim": 8,
                "geo_dim": 4, "time_dim": 8, "hidden_dim": 32, "num_layers": 1, "num_heads": 4, "dropout": 0.0,
            },
            "decoder": {
                "type": "EarthNetObservationDecoder", "in_dim": 16, "out_channels": 4, "img_size": 16,
                "patch_size": 8, "depth": 1, "num_heads": 4, "decoder_embed_dim": 32, "mlp_ratio": 2.0,
                "dropout": 0.0, "decoder_mode": "transformer", "predict_logvar": False, "output_activation": "sigmoid",
            },
        },
    }


def make_batch(seed: int = 0) -> dict:
    g = torch.Generator().manual_seed(seed)
    b = 2
    return {
        "x_context": torch.rand(b, 10, 4, 32, 32, generator=g),
        "context_mask": torch.ones(b, 10, 32, 32),
        "D_path": torch.randn(b, 30, 4, generator=g),
        "D_mask": torch.ones(b, 30, 4),
        "C_path": torch.randn(b, 30, 2, generator=g),
        "delta_t_path": torch.full((b, 30), 5.0),
        "G": torch.rand(b, 1, 16, 16, generator=g),
        "G_mask": torch.ones(b, 1, 16, 16),
        "h": torch.arange(5, 101, 5).repeat(b, 1).float(),
        "x_target": torch.rand(b, 20, 4, 16, 16, generator=g),
        "target_mask": torch.ones(b, 20, 16, 16),
        "target_veg_mask": (torch.rand(b, 20, 16, 16, generator=g) > 0.3).float(),
    }


def main() -> None:
    torch.manual_seed(0)
    model = create_obsworld_v2_model(tiny_config(ndvi_head=True)).train()
    batch = make_batch(0)
    mv = model_input_view(batch)

    # 1 forward emits ndvi_pred
    out = model(mv, selected_steps=[0, 9, 19])
    ndvi_pred = out.get("ndvi_pred")
    check("1 forward emits ndvi_pred [B,K,1,16,16]",
          ndvi_pred is not None and tuple(ndvi_pred.shape) == (2, 3, 1, 16, 16) and torch.isfinite(ndvi_pred).all(),
          f"shape={None if ndvi_pred is None else tuple(ndvi_pred.shape)}")

    # 2 initial prediction is NEAR persistence (small nonzero scale). The scale
    # is intentionally small-but-nonzero (~0.1) so the head trains from step 1
    # and DDP does not see it as an unused parameter; the deviation from
    # persistence is bounded by |tanh(scale*residual)| and stays small.
    raw = model
    last_rgbn = raw.core.initialize_state(mv)["last_valid_rgbn"]
    red, nir = last_rgbn[:, 2], last_rgbn[:, 3]
    base = ((nir - red) / (nir + red + 1e-6)).clamp(-1.0, 1.0).unsqueeze(1)
    base_resized = torch.nn.functional.interpolate(base, size=(16, 16), mode="bilinear", align_corners=False)
    persistence = base_resized.unsqueeze(1).expand(2, 3, 1, 16, 16)
    scale0 = float(raw.core.ndvi_residual_scale.detach())
    dev = float((ndvi_pred - persistence).abs().max())
    check("2 initial pred near persistence (scale small nonzero)",
          0.0 < abs(scale0) <= 0.2 and dev <= float(torch.tanh(torch.tensor(abs(scale0))) + 1e-4),
          f"scale={scale0:.3f} max|diff|={dev:.3e} (bound=tanh(scale)={float(torch.tanh(torch.tensor(abs(scale0)))):.3f})")

    # 3 loss computes ndvi_main + ndvi_consistency
    loss_fn = EarthNetForecastLoss(red_index=2, nir_index=3, w_obs=0.1, w_ndvi=0.0,
                                   w_latent=0.0, w_delta=0.0, w_smooth=0.0,
                                   w_ndvi_main=1.0, w_ndvi_consistency=0.1)
    tgt = batch["x_target"].index_select(1, out["step_indices"])
    tmask = batch["target_mask"].index_select(1, out["step_indices"])
    veg = batch["target_veg_mask"].index_select(1, out["step_indices"])
    losses = loss_fn(out["pred"], tgt, tmask, ndvi_pred=out["ndvi_pred"], veg_mask=veg)
    check("3 loss ndvi_main+ndvi_consistency finite",
          torch.isfinite(losses["total"]) and losses["ndvi_main"].item() >= 0 and torch.isfinite(losses["ndvi_consistency"]),
          f"total={losses['total'].item():.4f} ndvi_main={losses['ndvi_main'].item():.4f} "
          f"ndvi_consistency={losses['ndvi_consistency'].item():.4f} obs={losses['obs'].item():.4f}")

    # 4 q / T / O gradients
    model.zero_grad(set_to_none=True)
    losses["total"].backward()

    def gnorm(module) -> float:
        s = 0.0
        for p in module.parameters():
            if p.grad is not None:
                s += float(p.grad.detach().pow(2).sum())
        return s ** 0.5

    q_g = gnorm(raw.core.encoder) + gnorm(raw.core.state_projector)
    t_g = gnorm(raw.transition.state_dynamics)
    o_g = gnorm(raw.core.decoder)
    scale_g = None if raw.core.ndvi_residual_scale.grad is None else float(raw.core.ndvi_residual_scale.grad)
    check("4 q/T/O(reflectance)/scale receive gradients",
          q_g > 0 and t_g > 0 and o_g > 0 and scale_g is not None and abs(scale_g) > 0,
          f"|g q|={q_g:.3e} |g T|={t_g:.3e} |g O|={o_g:.3e} g_scale={scale_g}")

    # 5 DDP-safety: at the DEFAULT init scale, the NDVI head receives gradient
    # AND no trainable parameter is left without a grad after one backward. This
    # reproduces DDP's find_unused_parameters=False contract (a zero-init scale
    # would leave the whole head unused and crash 8-GPU training at step 1).
    head_g_init = gnorm(raw.core.ndvi_head)
    unused = [name for name, p in raw.named_parameters()
              if p.requires_grad and p.grad is None]
    check("5 DDP-safe: head has grad at init & no trainable param unused",
          head_g_init > 0.0 and len(unused) == 0,
          f"|g head|@init(scale={float(raw.core.ndvi_residual_scale.detach()):.2f})={head_g_init:.3e} "
          f"unused_trainable_params={unused[:5]}{'...' if len(unused) > 5 else ''} (count={len(unused)})")

    # 6 future-satellite invariance: z0 independent of x_target
    model.eval()
    b_a = make_batch(0)
    b_b = copy.deepcopy(b_a)
    b_b["x_target"] = torch.rand_like(b_b["x_target"])  # only future truth changes
    with torch.no_grad():
        za = model(model_input_view(b_a), selected_steps=[0, 19])["z_context"]
        zb = model(model_input_view(b_b), selected_steps=[0, 19])["z_context"]
    check("6 future-satellite invariance (z0 unchanged)",
          torch.allclose(za, zb, atol=1e-6), f"max|dz0|={float((za - zb).abs().max()):.2e}")

    # The transition is identity-initialised (zero-init output projection) so an
    # UNTRAINED model leaves zh==z0 and drivers look inert. Perturb the output
    # projection to emulate a trained T and verify the driver -> zh -> output
    # WIRING (not the zero-init, which check 2 already covers).
    with torch.no_grad():
        raw.transition.state_dynamics.output_proj.weight.normal_(0.0, 0.3)
        if raw.transition.state_dynamics.output_proj.bias is not None:
            raw.transition.state_dynamics.output_proj.bias.normal_(0.0, 0.1)
        # Push the NDVI head scale up a bit so weather sensitivity is clearly
        # visible through it (check 2 covers the small-scale near-persistence).
        raw.core.ndvi_residual_scale.fill_(0.5)

    # 7 weather sensitivity: perturb future driver path -> zh + outputs move
    b_c = copy.deepcopy(b_a)
    b_c["D_path"][:, 10:] = b_c["D_path"][:, 10:] + 3.0
    with torch.no_grad():
        oa = model(model_input_view(b_a), selected_steps=[19])
        oc = model(model_input_view(b_c), selected_steps=[19])
    dz = float((oa["z_pred"] - oc["z_pred"]).abs().max())
    dp = float((oa["pred"] - oc["pred"]).abs().max())
    dn = float((oa["ndvi_pred"] - oc["ndvi_pred"]).abs().max())
    check("7 weather sensitivity (zh, pred, ndvi move)",
          dz > 1e-5 and dp > 1e-6 and dn > 1e-6, f"max|dzh|={dz:.2e} max|dpred|={dp:.2e} max|dndvi|={dn:.2e}")

    # 8 endpoint-guard: decoding z0 differs from decoding zh
    with torch.no_grad():
        init = model.core.initialize_state(model_input_view(b_a))
        z0 = init["state"]
        zh = model(model_input_view(b_a), selected_steps=[19])["z_pred"][:, 0]
        dec0 = model.core.decode_states(z0, baseline=init["last_valid_rgbn"])["mean"]
        dech = model.core.decode_states(zh, baseline=init["last_valid_rgbn"])["mean"]
    check("8 endpoint-guard: O(z0) != O(zh)",
          float((dec0 - dech).abs().max()) > 1e-6 and float((z0 - zh).abs().max()) > 1e-6,
          f"max|z0-zh|={float((z0 - zh).abs().max()):.2e} max|O(z0)-O(zh)|={float((dec0 - dech).abs().max()):.2e}")

    # 9 save/load round-trip
    sd = copy.deepcopy(model.state_dict())
    model2 = create_obsworld_v2_model(tiny_config(ndvi_head=True)).eval()
    model2.load_state_dict(sd, strict=True)
    with torch.no_grad():
        r1 = model(model_input_view(b_a), selected_steps=[0, 9, 19])
        r2 = model2(model_input_view(b_a), selected_steps=[0, 9, 19])
    check("9 save/load round-trip identical",
          torch.allclose(r1["pred"], r2["pred"], atol=1e-6) and torch.allclose(r1["ndvi_pred"], r2["ndvi_pred"], atol=1e-6),
          f"max|dpred|={float((r1['pred'] - r2['pred']).abs().max()):.2e}")

    # 10 warm-start: head-less state_dict loads non-strict
    headless = create_obsworld_v2_model(tiny_config(ndvi_head=False))
    fresh = create_obsworld_v2_model(tiny_config(ndvi_head=True))
    report = fresh.load_state_dict(headless.state_dict(), strict=False)
    missing = set(report.missing_keys)
    head_keys = {k for k in fresh.state_dict() if k.startswith("core.ndvi_head") or k == "core.ndvi_residual_scale"}
    check("10 warm-start non-strict: missing==head only, unexpected==0",
          missing == head_keys and len(report.unexpected_keys) == 0,
          f"missing={len(missing)} (head={len(head_keys)}) unexpected={len(report.unexpected_keys)}")

    # 10b warm-start HARD GATE rejects a mismatched source (extra key AND a
    # dropped non-head key). Replicates the trainer's gate predicate.
    def gate_violation(src_sd, target_model) -> bool:
        rep = target_model.load_state_dict(src_sd, strict=False)
        allowed = {k for k in target_model.state_dict()
                   if k.startswith("core.ndvi_head") or k == "core.ndvi_residual_scale"}
        illegal_missing = set(rep.missing_keys) - allowed
        return bool(list(rep.unexpected_keys) or illegal_missing)

    good_src = create_obsworld_v2_model(tiny_config(ndvi_head=False)).state_dict()
    target = create_obsworld_v2_model(tiny_config(ndvi_head=True))
    bad_src = dict(good_src)
    bad_src["core.__bogus_extra_key__"] = torch.zeros(1)          # unexpected key
    a_real_key = next(k for k in good_src if k.startswith("core.decoder"))
    del bad_src[a_real_key]                                        # missing non-head key
    ok = (not gate_violation(good_src, create_obsworld_v2_model(tiny_config(ndvi_head=True)))
          and gate_violation(bad_src, target))
    check("10b warm-start hard gate: accepts good src, rejects mismatched src", ok,
          f"good_passes={not gate_violation(good_src, create_obsworld_v2_model(tiny_config(ndvi_head=True)))} "
          f"bad_rejected={gate_violation(bad_src, create_obsworld_v2_model(tiny_config(ndvi_head=True)))}")

    # 11 optimizer grouping
    try:
        from train.train_stage2_earthnet import build_optimizer
        cfg = {"optimizer": {"lr": 1e-4, "backbone_lr": 1e-5, "weight_decay": 0.05, "betas": [0.9, 0.95]}}
        opt = build_optimizer(fresh, cfg)
        by_lr = {g["lr"]: set(id(p) for p in g["params"]) for g in opt.param_groups}
        # Compare only trainable encoder params: the core intentionally freezes
        # s1_proj / modality_embed_s1, which are correctly excluded from the
        # optimizer, so the full encoder param set is not a subset by design.
        enc_ids = {id(p) for p in fresh.core.encoder.parameters() if p.requires_grad}
        # Only trainable head params: mask_token is frozen (unused in decode) and
        # correctly excluded from the optimizer, so don't require it to be present.
        head_ids = {id(p) for p in fresh.core.ndvi_head.parameters() if p.requires_grad} | {id(fresh.core.ndvi_residual_scale)}
        ok = (1e-5 in by_lr and enc_ids <= by_lr[1e-5]
              and 1e-4 in by_lr and head_ids <= by_lr[1e-4])
        check("11 optimizer: q@backbone_lr, NDVI head@lr", ok,
              f"groups={[(g['lr'], len(g['params'])) for g in opt.param_groups]}")
    except Exception as exc:  # pragma: no cover
        check("11 optimizer grouping", False, f"import/build failed: {exc!r}")

    # 12 data veg mask helper
    try:
        import xarray as xr
        from data.datasets.earthnet2021 import _evaluator_aligned_veg_clear_mask
        T, H, W = 20, 16, 16
        rng = np.random.default_rng(0)
        clear = (rng.random((T, H, W)) > 0.4).astype(np.float32)
        scl = rng.choice([1, 2, 3, 4, 8, 9], size=(T, H, W)).astype(np.float32)  # 3/8/9 invalid
        esawc = rng.choice([10, 30, 40, 50, 80], size=(H, W)).astype(np.float32)  # 50/80 non-veg
        cube = xr.Dataset(
            {
                "s2_SCL": (("time", "lat", "lon"), scl),
                "esawc_lc": (("lat", "lon"), esawc),
            }
        )
        veg = _evaluator_aligned_veg_clear_mask(cube, clear, indices=list(range(T)))
        valid_scl = np.isin(scl, (1, 2, 4, 5, 6, 7))
        veg_lc = (esawc < 41)[None].repeat(T, 0)
        expected = clear.astype(bool) & valid_scl & veg_lc
        ok = (veg.shape == (T, H, W) and np.array_equal(veg.astype(bool), expected)
              and bool((veg.astype(bool) <= clear.astype(bool)).all()))
        check("12 veg mask = clear & SCL-valid & veg-lc, subset of clear", ok,
              f"veg_frac={veg.mean():.3f} clear_frac={clear.mean():.3f}")
    except Exception as exc:  # pragma: no cover
        check("12 data veg mask helper", False, f"{exc!r}")

    n_pass = sum(1 for _, ok, _ in _results if ok)
    print(f"\n==== SMOKE SUMMARY: {n_pass}/{len(_results)} PASS ====")
    if n_pass != len(_results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
