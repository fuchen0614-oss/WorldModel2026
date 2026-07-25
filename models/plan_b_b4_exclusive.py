"""plan-b-pvt · Phase-II EXCLUSIVE-weather-route world model (audit-approved).

Root cause fixed: in Phase-I  ŷ = B0(history, REAL future weather) + gate·O(T(...)),
the full-weather B0 lets future weather reach ŷ WITHOUT passing through T, so the
optimizer bypasses the state branch (Q2 non-load-bearing).

Exclusive route (this file) — future weather can reach ŷ ONLY through T:

    z_t      = projector(q_student(history, geo, FUTURE-WEATHER ZEROED))    # context_prior state
    prior    = q_student forecast on the SAME context-only input           # sees NO future weather
    z_{t+h}  = T(z_t, future_weather[t:t+h], geo, h)
    ŷ_{t+h}  = prior_{t+h} + alpha · O(z_{t+h})

Key properties (NOT claims about Q2 — Q2 must be confirmed empirically after training):
  * `prior` is provably future-weather-free: it is q's forecast on `_context_only_data`
    (future frames AND future weather zeroed). Changing future weather cannot change it.
  * NO free learnable gate. `alpha` is a NON-learnable buffer (a fixed schedule value);
    it can warm up 0→1 during training but the deployed structure has a fixed, non-zero
    state path (alpha=1).
  * NO teacher inside this (inference) model. The full-weather teacher is a SEPARATE
    frozen q copy held by the trainer; it never enters this model's state_dict / params.

Subclasses Phase-I ObsWorldB4 to reuse every helper (transition/O/decode/unpatchify/
masks/state stats) WITHOUT touching the Phase-I class or its checkpoints.
"""
from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from typing import Optional

import torch
import torch.nn as nn

from models.plan_b_b4 import ObsWorldB4


class ObsWorldB4Exclusive(ObsWorldB4):
    ARCH = "ObsWorldB4Exclusive"

    def __init__(self, hparams=None, contract_cfg: Optional[dict] = None):
        super().__init__(hparams, contract_cfg)
        # Drop the free gate entirely (audit: no scalar that can shrink to 0 and bypass T).
        if "gate" in self._parameters:
            del self._parameters["gate"]
        # alpha: NON-learnable schedule value (buffer, not a Parameter). Fixed at deploy.
        self.register_buffer("alpha", torch.tensor(1.0))

    # ---- context prior + state (student q, NO future weather, NO teacher) ------
    def _prior_state(self, data):
        """Return (prior, z_t):
          prior = q_student forecast on CONTEXT-ONLY data (future frames+weather zeroed);
          z_t   = projector(context-only state at t).
        Grad flows through q_student only when it is unfrozen (Phase B); frozen in Phase A."""
        core = self.q.core
        was = core.training
        core.eval()
        ctx = torch.no_grad() if self.freeze_b0 else nullcontext()
        with ctx:
            prior, z_ctx = self.q.encode(self._context_only_data(data),
                                         pred_start=self.context_len, preds_length=self.target_len)
        if was:
            core.train()
        if self.freeze_b0:
            prior, z_ctx = prior.detach(), z_ctx.detach()
        z_t = self.projector(z_ctx[:, self.context_len - 1])
        return prior, z_t

    # ---- exclusive forecast: prior + alpha · O(T(...)) -------------------------
    def forecast(self, data, want_parts: bool = False):
        prior, z_t = self._prior_state(data)
        hr = data["dynamic"][0]
        B, H, W = hr.shape[0], hr.shape[-2], hr.shape[-1]
        geo, u_future = self._geo_weather(data)
        residual = self._direct_residual(z_t, u_future, geo, B, H, W)      # (B, tl, n_out, H, W)
        pred = prior + self.alpha * residual
        if want_parts:
            return pred, prior, residual, z_t, geo, u_future
        return pred

    def _composed_pred(self, prior, z_t, u_future, geo, h1, h2, B, H, W):
        """Composed prediction on the exclusive route (prior base + alpha·decoded composed state)."""
        z_cmp = self.composed_state(z_t, u_future, geo, h1, h2)
        r = self._decode_state(z_cmp, B, H, W)
        return prior[:, h1 + h2 - 1] + self.alpha * r

    # ---- training loss (teacher_pred is passed IN by the trainer, NOT owned here) ----
    def loss(self, data, teacher_pred, lambdas: SimpleNamespace):
        """Losses for the exclusive route. `teacher_pred` = stop-grad full-weather forecast
        computed by the trainer from a SEPARATE frozen q copy (never `self` during Phase B).

          L_fore  : real-label masked NDVI on the FINAL pred (chase, aims to beat teacher)
          L_dist  : masked (pred -> teacher.detach())        (protect Table-1 accuracy)
          L_resid : residual -> stopgrad(teacher - prior)    (NOT the old y - full_B0)
          L_vic   : VICReg on z_t
          + Phase-B: cmp/con on the exclusive composed path
        """
        pred, prior, residual, z_t, geo, u_future = self.forecast(data, want_parts=True)
        cl, tl = self.context_len, self.target_len
        B, H, W = pred.shape[0], pred.shape[-2], pred.shape[-1]
        lam = lambdas
        lc = data["landcover"]
        lc_mask = ((lc >= self.lc_min) & (lc <= self.lc_max)).type_as(pred)             # (B,1,H,W)
        targ_win = data["dynamic"][0][:, cl:cl + tl, 0:1]
        cloud_win = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).type_as(pred)        # (B,tl,1,H,W)
        valid = cloud_win * lc_mask.unsqueeze(1)
        td = teacher_pred.detach()
        logs, total = {}, pred.new_zeros(())

        if float(getattr(lam, "fore", 0.0)) > 0:                                        # real label, beat teacher
            l_fore, _ = self.ndvi_loss(pred, data)
            logs["fore"] = l_fore.detach(); total = total + lam.fore * l_fore
        if float(getattr(lam, "distill", 0.0)) > 0:                                     # protect accuracy
            l_d = (((pred - td) ** 2) * valid).sum() / (valid.sum() + 1e-8)
            logs["distill"] = l_d.detach(); total = total + lam.distill * l_d
        if float(getattr(lam, "resid", 0.0)) > 0:                                       # residual -> teacher-prior
            r_teacher = (td - prior).detach()
            l_r = (((residual - r_teacher) ** 2) * valid).sum() / (valid.sum() + 1e-8)
            logs["resid"] = l_r.detach(); total = total + lam.resid * l_r
        if float(getattr(lam, "cmp", 0.0)) > 0 or float(getattr(lam, "con", 0.0)) > 0:  # Phase-B composition
            k = len(self.partitions); l_cmp = pred.new_zeros(()); l_con = pred.new_zeros(())
            for (h1, h2) in self.partitions:
                h = h1 + h2
                y_cmp = self._composed_pred(prior, z_t, u_future, geo, h1, h2, B, H, W)
                y_dir = pred[:, h - 1]
                th, ch = targ_win[:, h - 1], cloud_win[:, h - 1]
                l_cmp = l_cmp + self._masked_mse1(y_cmp, th, ch, lc_mask)
                l_con = l_con + self._masked_mse1(y_cmp, y_dir.detach(), ch, lc_mask)
            l_cmp, l_con = l_cmp / k, l_con / k
            if float(getattr(lam, "cmp", 0.0)) > 0:
                logs["cmp"] = l_cmp.detach(); total = total + lam.cmp * l_cmp
            if float(getattr(lam, "con", 0.0)) > 0:
                logs["con"] = l_con.detach(); total = total + lam.con * l_con
        if float(getattr(lam, "vic", 0.0)) > 0:
            var_t, cov_t = self.vicreg_loss(z_t)
            logs["vic_var"] = var_t.detach(); total = total + lam.vic * (25.0 * var_t + cov_t)
        logs["alpha"] = self.alpha.detach().clone()
        logs["total"] = total.detach()
        return pred, {"total": total, "logs": logs}

    def config(self) -> dict:
        c = super().config(); c["arch"] = self.ARCH; return c


def load_exclusive_from_b4(model: "ObsWorldB4Exclusive", b4_state_dict: dict):
    """Warm-start an exclusive model from a Phase-I b4_state_dict. Reuses q/projector/
    weather_enc/geo_enc/time_emb/fuse/transition/o_delta; DROPS the old scalar `gate`;
    `alpha` (new buffer) is left at its schedule init. Returns (missing, unexpected)."""
    sd = {k: v for k, v in b4_state_dict.items() if k != "gate"}          # explicitly drop gate
    missing, unexpected = model.load_state_dict(sd, strict=False)
    return list(missing), list(unexpected)
