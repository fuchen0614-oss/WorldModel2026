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
  * NO free learnable gate. `alpha` is a NON-learnable buffer FIXED at 1.0 (both stages).
    (alpha must stay 1: L_distill wants residual≈teacher−prior while L_resid wants the same;
    any alpha<1 would demand residual≈(teacher−prior)/alpha and make the two targets conflict.)
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


# Exclusive-only composition splits (spec 五.3-4), FROZEN. TRAIN covers totals 10/15/20; HELDOUT is
# disjoint and covers unseen split ratios + total=10 + total=20. Unused when cmp/con=0 (Stage A), so
# Stage-A loss/forecast numerics are byte-unchanged.
EXCL_TRAIN_PARTITIONS = [(5, 5), (7, 8), (10, 10)]                     # totals 10, 15, 20
EXCL_HELDOUT_PARTITIONS = [(3, 7), (6, 4), (4, 11), (8, 12), (2, 18)]  # totals 10, 10, 15, 20, 20 (disjoint)


class ObsWorldB4Exclusive(ObsWorldB4):
    ARCH = "ObsWorldB4Exclusive"
    ROUTE_VERSION = "exclusive_v1"

    def __init__(self, hparams=None, contract_cfg: Optional[dict] = None):
        super().__init__(hparams, contract_cfg)
        # Drop the free gate entirely (audit: no scalar that can shrink to 0 and bypass T).
        if "gate" in self._parameters:
            del self._parameters["gate"]
        # alpha: NON-learnable schedule value (buffer, not a Parameter). Fixed at deploy.
        self.register_buffer("alpha", torch.tensor(1.0))
        self.route_version = self.ROUTE_VERSION
        # exclusive composition splits (overridable via contract_cfg; unused in Stage A)
        cfg = contract_cfg or {}
        if "partitions" not in cfg:
            self.partitions = [tuple(p) for p in EXCL_TRAIN_PARTITIONS]
        if "heldout_partitions" not in cfg:
            self.heldout_partitions = [tuple(p) for p in EXCL_HELDOUT_PARTITIONS]

    # ---- dual-signature forward so DDP works: -------------------------------
    #   model(data)                                     -> inference (NO teacher)
    #   model(data, teacher_pred, lambdas[, interv])    -> training loss
    def forward(self, data, teacher_pred=None, lambdas=None, intervention=None):
        if lambdas is None:
            return self.forecast(data)
        return self.loss(data, teacher_pred, lambdas, intervention)

    def intervention_residual_loss(self, arm_data, teacher_arm_pred):
        """OPTIONAL Stage-B intervention-distillation (spec 四), GATE-gated + default OFF. The student
        residual UNDER an intervened future-weather arm fits stopgrad(teacher_arm - context_prior);
        the weather-free prior cancels the base, so the target isolates the teacher's WEATHER response
        and trains T to MOVE with weather. Does NOT replace L_fore. Teacher runs the SAME arm (trainer)."""
        _, prior, residual, _, _, _ = self.forecast(arm_data, want_parts=True)
        cl, tl = self.context_len, self.target_len
        lc = arm_data["landcover"]
        lcm = ((lc >= self.lc_min) & (lc <= self.lc_max)).type_as(residual)
        cloud = (arm_data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).type_as(residual)
        valid = cloud * lcm.unsqueeze(1)
        target = (teacher_arm_pred.detach() - prior).detach()
        return (((residual - target) ** 2) * valid).sum() / (valid.sum() + 1e-8)

    # Parent gate-based methods MUST NOT be used on the exclusive route.
    def forecast_weather(self, *a, **k):
        raise NotImplementedError("exclusive route: use eval.eval_b4_exclusive_contract weather intervention (T-only, alpha).")

    def composed_predictions(self, *a, **k):
        raise NotImplementedError("exclusive route: use _composed_pred / the exclusive evaluator (no gate).")


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
    def loss(self, data, teacher_pred, lambdas: SimpleNamespace, intervention=None):
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
        logs, terms, total = {}, {}, pred.new_zeros(())
        # never-alone guard (spec 五.7): latent state-consistency must co-occur with real target loss
        # AND an endpoint composition/consistency loss (else identity/collapse trivially satisfies it).
        if float(getattr(lam, "state_con", 0.0)) > 0:
            assert float(getattr(lam, "fore", 0.0)) > 0 and (
                float(getattr(lam, "cmp", 0.0)) > 0 or float(getattr(lam, "con", 0.0)) > 0), \
                "state_con must never train alone: require fore>0 and (cmp>0 or con>0) (spec 五.7)."

        if float(getattr(lam, "fore", 0.0)) > 0:                                        # real label, beat teacher
            l_fore, _ = self.ndvi_loss(pred, data)
            logs["fore"] = l_fore.detach(); terms["fore"] = l_fore; total = total + lam.fore * l_fore
        if float(getattr(lam, "distill", 0.0)) > 0:                                     # protect accuracy
            l_d = (((pred - td) ** 2) * valid).sum() / (valid.sum() + 1e-8)
            logs["distill"] = l_d.detach(); terms["distill"] = l_d; total = total + lam.distill * l_d
        if float(getattr(lam, "resid", 0.0)) > 0:                                       # residual -> teacher-prior
            r_teacher = (td - prior).detach()
            l_r = (((residual - r_teacher) ** 2) * valid).sum() / (valid.sum() + 1e-8)
            logs["resid"] = l_r.detach(); terms["resid"] = l_r; total = total + lam.resid * l_r
        # Phase-B composition: cmp (composed endpoint accuracy) / con (output consistency) / state_con
        # (LayerNorm-normalized LATENT consistency, direct branch stop-grad). All default 0 => Stage-A unchanged.
        if any(float(getattr(lam, k, 0.0)) > 0 for k in ("cmp", "con", "state_con")):
            import torch.nn.functional as F
            k = len(self.partitions)
            l_cmp = pred.new_zeros(()); l_con = pred.new_zeros(()); l_state = pred.new_zeros(())
            for (h1, h2) in self.partitions:
                h = h1 + h2
                y_cmp = self._composed_pred(prior, z_t, u_future, geo, h1, h2, B, H, W)
                y_dir = pred[:, h - 1]
                th, ch = targ_win[:, h - 1], cloud_win[:, h - 1]
                l_cmp = l_cmp + self._masked_mse1(y_cmp, th, ch, lc_mask)
                l_con = l_con + self._masked_mse1(y_cmp, y_dir.detach(), ch, lc_mask)
                if float(getattr(lam, "state_con", 0.0)) > 0:                            # normalized latent consistency (五.5)
                    z_cmp = self.composed_state(z_t, u_future, geo, h1, h2)
                    z_dir = self.direct_state(z_t, u_future, geo, h).detach()            # direct branch stop-grad
                    zc = F.layer_norm(z_cmp, (z_cmp.shape[-1],)); zd = F.layer_norm(z_dir, (z_dir.shape[-1],))
                    l_state = l_state + ((zc - zd) ** 2).mean()
            l_cmp, l_con, l_state = l_cmp / k, l_con / k, l_state / k
            if float(getattr(lam, "cmp", 0.0)) > 0:
                logs["cmp"] = l_cmp.detach(); terms["cmp"] = l_cmp; total = total + lam.cmp * l_cmp
            if float(getattr(lam, "con", 0.0)) > 0:
                logs["con"] = l_con.detach(); terms["con"] = l_con; total = total + lam.con * l_con
            if float(getattr(lam, "state_con", 0.0)) > 0:
                logs["state_con"] = l_state.detach(); terms["state_con"] = l_state; total = total + lam.state_con * l_state
        if float(getattr(lam, "vic", 0.0)) > 0:
            var_t, cov_t = self.vicreg_loss(z_t)
            logs["vic_var"] = var_t.detach(); total = total + lam.vic * (25.0 * var_t + cov_t)
        if float(getattr(lam, "vic_future", 0.0)) > 0:                                   # anti-collapse on transitioned z_h (五.6)
            l_vf = pred.new_zeros(())
            for h in (10, self.target_len):
                z_h = self.direct_state(z_t, u_future, geo, h)
                var_h, cov_h = self.vicreg_loss(z_h)
                l_vf = l_vf + (25.0 * var_h + cov_h)
            l_vf = l_vf / 2
            logs["vic_future"] = l_vf.detach(); terms["vic_future"] = l_vf; total = total + lam.vic_future * l_vf
        # OPTIONAL intervention-distillation (spec 四): only fires when the trainer passes an arm batch
        # AND lam.intervention>0 (both gated OFF by default => Stage-A path untouched). Never replaces L_fore.
        if intervention is not None and float(getattr(lam, "intervention", 0.0)) > 0:
            l_int = self.intervention_residual_loss(intervention["arm_data"], intervention["teacher_arm_pred"])
            logs["intervention"] = l_int.detach(); terms["intervention"] = l_int
            total = total + lam.intervention * l_int
        logs["alpha"] = self.alpha.detach().clone()
        logs["total"] = total.detach()
        return pred, {"total": total, "logs": logs, "terms": terms}

    def config(self) -> dict:
        c = super().config(); c["arch"] = self.ARCH; c["route_version"] = self.ROUTE_VERSION; return c


def load_exclusive_from_b4(model: "ObsWorldB4Exclusive", b4_state_dict: dict):
    """Warm-start an exclusive model from a Phase-I b4_state_dict. Reuses q/projector/
    weather_enc/geo_enc/time_emb/fuse/transition/o_delta; DROPS the old scalar `gate`;
    `alpha` (new buffer) is left at its schedule init. Returns (missing, unexpected)."""
    sd = {k: v for k, v in b4_state_dict.items() if k != "gate"}          # explicitly drop gate
    missing, unexpected = model.load_state_dict(sd, strict=False)
    return list(missing), list(unexpected)
