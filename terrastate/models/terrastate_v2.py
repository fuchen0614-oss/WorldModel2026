"""TerraState-V2 — the doc-88 UNIQUE inference/training model (frozen contract).

Inference chain (doc 88 §0.1 / §3, verbatim):
    z_t      = projector(q(context-only history))          # context-only predictive state
    b_h      = q's context-only forecast (the prior)       # reads NO future weather
    z_{t+h}  = T(z_t, full24[t:t+h], static_geo, h)         # ONE shared transition
    y_{t+h}  = b_h + alpha * O(z_{t+h}),   alpha == 1 (fixed, non-learnable buffer)

This REUSES the audit-approved exclusive route (models/plan_b_b4_exclusive.
ObsWorldB4Exclusive) VERBATIM for inference — that class already implements exactly this
contract with `alpha` a NON-learnable buffer fixed at 1.0 and a provably
future-weather-free prior (`_prior_state`). We do NOT re-derive the backbone (doc 88
constraint 六 "reuse existing verified backbone").

TerraState-V2 ONLY ADDS:
  * loss_v2 — the doc-88 THREE-term loss  L = 1.0*L_GT + 0.5*L_KD + lambda_s*L_future_state
    (exactly ONE KD; NO resid / cmp / con / state_con / vic / intervention — those live on
    the inherited multi-term `loss()` which we DO NOT call).
  * future_state / forecast_parts / context_state — the evaluator-facing state API
    (doc 88 constraint 七: expose forecast, forecast parts, direct_state, context state).
  * inference-leakage assertions — future EO frames and the future-state target/cache are
    provably NOT in the inference graph.

The future-state target z*_{t+h} and the KD teacher prediction are ALWAYS passed IN by
the trainer as plain tensors; the model never reads a cache or a teacher of its own, so
inference (`model(data)`) touches neither (doc 88 constraint 五 / 六).
"""
from __future__ import annotations

from typing import Optional

import torch
import torch.nn.functional as F

from models.plan_b_b4_exclusive import ObsWorldB4Exclusive


class TerraStateV2(ObsWorldB4Exclusive):
    ARCH = "TerraStateV2"
    ROUTE_VERSION = "terrastate_v2"
    DRIVER_PROTOCOL = "full24"

    # doc-88 §4.2 FIXED loss weights (not configurable): exactly one KD.
    W_GT = 1.0
    W_KD = 0.5

    def __init__(self, hparams=None, contract_cfg: Optional[dict] = None):
        super().__init__(hparams, contract_cfg)
        self.route_version = self.ROUTE_VERSION
        # alpha is inherited as a fixed buffer == 1.0. Re-assert the doc-88 hard constraint.
        assert "alpha" in self._buffers, "alpha must be a buffer (non-learnable)"
        assert not self.alpha.requires_grad, "alpha must NOT be learnable"
        assert float(self.alpha) == 1.0, "alpha must be fixed at 1.0"

    # ---- evaluator-facing state API (doc 88 constraint 七) --------------------------
    def context_state(self, data) -> torch.Tensor:
        """z_t = context-only predictive state (no future EO, no future weather)."""
        _, z_t = self._prior_state(data)
        return z_t

    def future_state(self, z_t, u_future, geo, h: Optional[int] = None) -> torch.Tensor:
        """z_{t+h} = T(z_t, full24[t:t+h], geo, h). Default h = target_len (terminal)."""
        h = self.target_len if h is None else int(h)
        return self.direct_state(z_t, u_future, geo, h)

    def forecast_parts(self, data) -> dict:
        """One forward -> every part an evaluator/loss needs. `z_future` == z_{t+H}."""
        pred, prior, residual, z_t, geo, u_future = self.forecast(data, want_parts=True)
        z_future = self.direct_state(z_t, u_future, geo, self.target_len)
        return {
            "pred": pred, "prior": prior, "residual": residual,
            "z_t": z_t, "z_future": z_future, "geo": geo, "u_future": u_future,
        }

    # ---- doc-88 UNIQUE training loss -----------------------------------------------
    def loss_v2(self, data, teacher_pred, z_star, patch_mask, lambda_state):
        """L = 1.0*L_GT + 0.5*L_KD + lambda_s*L_future_state  (doc 88 §0.2 / §4.2).

          L_GT           : masked NDVI on the FINAL forecast (exact B0 pixel protocol).
          L_KD           : masked (pred -> teacher.detach()); teacher = frozen full-weather
                           B4, computed & passed IN by the trainer. Exactly ONE KD.
          L_future_state : 1 - cos(LN z_{t+H}, LN z*_{t+H}), masked over valid patches.
                           z*_{t+H} = frozen future-observation target (cache), passed IN.
        """
        parts = self.forecast_parts(data)
        pred, z_future = parts["pred"], parts["z_future"]
        cl, tl = self.context_len, self.target_len

        # valid pixels = clear cloud (<1) AND vegetation land-cover — SAME selection as GT.
        lc = data["landcover"]
        lc_mask = ((lc >= self.lc_min) & (lc <= self.lc_max)).type_as(pred)          # (B,1,H,W)
        cloud_win = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).type_as(pred)     # (B,tl,1,H,W)
        valid = cloud_win * lc_mask.unsqueeze(1)

        l_gt, _ = self.ndvi_loss(pred, data)                                         # L_GT
        td = teacher_pred.detach()
        l_kd = (((pred - td) ** 2) * valid).sum() / (valid.sum() + 1e-8)             # L_KD (single)
        l_fs = self.future_state_loss(z_future, z_star, patch_mask)                  # L_future_state

        lam = float(lambda_state)
        total = self.W_GT * l_gt + self.W_KD * l_kd + lam * l_fs
        logs = {
            "gt": l_gt.detach(), "kd": l_kd.detach(), "future_state": l_fs.detach(),
            "lambda_state": pred.new_tensor(lam), "alpha": self.alpha.detach().clone(),
            "total": total.detach(),
        }
        terms = {"gt": l_gt, "kd": l_kd, "future_state": l_fs}
        return pred, {"total": total, "logs": logs, "terms": terms}

    @staticmethod
    def future_state_loss(z_future, z_star, patch_mask=None, eps: float = 1e-6):
        """1 - cos(LN(z_{t+H}), LN(z*_{t+H})), averaged over valid patches.
        z_star is a stop-grad target (frozen encoder / cache); LN is applied to BOTH."""
        zf = F.layer_norm(z_future, (z_future.shape[-1],))
        zs = F.layer_norm(z_star.detach().to(z_future.dtype), (z_star.shape[-1],))
        per = 1.0 - F.cosine_similarity(zf, zs, dim=-1)                              # (B_patch,)
        if patch_mask is None:
            return per.mean()
        m = patch_mask.to(per.dtype)
        return (per * m).sum() / (m.sum() + eps)

    # ---- dual-signature forward (DDP-safe): inference vs doc-88 loss ---------------
    def forward(self, data, teacher_pred=None, z_star=None, patch_mask=None, lambda_state=None):
        # INFERENCE: teacher_pred None -> pure forecast. Never touches z_star / any cache.
        if teacher_pred is None:
            return self.forecast(data)
        return self.loss_v2(data, teacher_pred, z_star, patch_mask, lambda_state)

    # ---- inference-leakage guards (used by the smoke; cheap, no_grad) --------------
    @torch.no_grad()
    def assert_prior_ignores_future_weather(self, data) -> bool:
        """The context-only prior b_h must be invariant to future weather (doc 88 §3 ①)."""
        d2 = self._shallow_with_weather(data, randomize_future=True)
        p0, _ = self._prior_state(data)
        p1, _ = self._prior_state(d2)
        return torch.equal(p0, p1)

    @torch.no_grad()
    def assert_forecast_ignores_future_eo(self, data) -> bool:
        """The inference forecast must NOT read future EO frames (only future WEATHER,
        via T). Perturbing future EO must leave the forecast byte-identical."""
        d2 = self._shallow_with_frames(data, randomize_future=True)
        y0 = self.forecast(data)
        y1 = self.forecast(d2)
        return torch.equal(y0, y1)

    # helpers that clone ONLY the perturbed tensor (leave others shared)
    def _shallow_with_weather(self, data, randomize_future: bool):
        w = data["dynamic"][1].clone()
        if randomize_future:
            w[:, self.context_len:] = torch.randn_like(w[:, self.context_len:])
        return {"dynamic": [data["dynamic"][0], w], "dynamic_mask": data["dynamic_mask"],
                "static": data["static"], "landcover": data["landcover"]}

    def _shallow_with_frames(self, data, randomize_future: bool):
        x = data["dynamic"][0].clone()
        if randomize_future:
            x[:, self.context_len:] = torch.randn_like(x[:, self.context_len:])
        return {"dynamic": [x, data["dynamic"][1]], "dynamic_mask": data["dynamic_mask"],
                "static": data["static"], "landcover": data["landcover"]}

    def config(self) -> dict:
        c = super().config()
        c["arch"] = self.ARCH
        c["route_version"] = self.ROUTE_VERSION
        c["driver_protocol"] = self.DRIVER_PROTOCOL
        return c


def warm_start_terrastate_v2(model: "TerraStateV2", init_ck: dict, *, require_exact: bool = True):
    """FAIL-CLOSED warm-start of the OFFICIAL student.

    doc-88 frozen weight chain: the student is initialised from the exclusive MAIN-last
    checkpoint ONLY (arch ObsWorldB4Exclusive), or a TerraStateV2 resume. A raw Phase-I B4
    (arch ObsWorldB4) is REJECTED as a student init — the choice is not free. With
    `require_exact` (default), the load MUST be exact: missing == [] and unexpected == [];
    otherwise we RAISE instead of printing and continuing. Returns (missing, unexpected, arch).
    """
    sd = init_ck["b4_state_dict"]
    arch = (init_ck.get("contract_cfg", {}) or {}).get("arch") or init_ck.get("arch")
    if arch not in ("ObsWorldB4Exclusive", "TerraStateV2"):
        raise RuntimeError(
            f"student init arch={arch!r} is NOT allowed. TerraState-V2's student MUST be the "
            f"exclusive MAIN-last checkpoint (arch ObsWorldB4Exclusive) or a TerraStateV2 resume; "
            f"a raw Phase-I B4 (ObsWorldB4) is not a valid student init (doc 88 frozen weight chain).")
    miss, unexp = model.load_state_dict(sd, strict=False)
    miss, unexp = list(miss), list(unexp)
    if require_exact and (miss or unexp):
        raise RuntimeError(
            f"FAIL-CLOSED student load rejected: missing={miss[:8]} unexpected={unexp[:8]} "
            f"(require missing==[] and unexpected==[]). Do NOT proceed on a partial load.")
    return miss, unexp, arch
