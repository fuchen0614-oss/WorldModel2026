"""plan-b-pvt · B4 = ObsWorld unified shared-z world model (design A).

ONE model, forecasting-primary + strong-baseline-recoverable (doc 71 §4.2):

    q (PVT ContextFormer)  --> z  (predictive state, per patch-token, T steps)
      |                         |
      |-- forecast head ------- + ---> NDVI preds        == B0 EXACTLY when contract off
      |
      +-- projector ----------> s  (state space)
              |
              +-- ControlledTransition T(s_t, weather_t) --> ŝ_{t+1}   (REAL dynamics)
              |        \\__ latent-future = predict future s from context s (non-trivial gap)
              |
              +-- PhiRenderer O(s, φ) --> observation      (factorization / Fig3 capability)

Design A (recommended): the forecast path is UNCHANGED from B0 (Contextformer
head). T / renderer / latent-future are accuracy-relevant AUX + capability heads
on the SHARED z. Accuracy is expected to improve via (i) SSL4EO pretraining of
the shared encoder and (ii) these aux regularizers — NOT by rerouting the
forecast through a lossy bottleneck (that is design B, kept for ablation).

Recoverability contract: with `lambdas` all zero (or None) `forward` returns
predictions byte-identical to B0 and an all-zero loss. Every new sub-module that
could touch the forecast is either (a) not on the forecast path, or (b) a
zero-initialised residual — so the world model "can only help, not break".
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from models.encoders.pvt_contextformer_q import (
    PVTContextformerQ,
    contextformer6m_hparams,
)
from models.encoders.state_projection import SpatialStateProjector


class ControlledTransition(nn.Module):
    """ŝ_{t+1} = s_t + Δ(s_t, driver_t), with Δ zero-initialised (identity at start).

    Makes latent-future a REAL one-step prediction: the transition must model how
    the state evolves under the exogenous driver (weather). Because the last layer
    is zero-init, at initialisation ŝ_{t+1}=s_t (a harmless identity), so nothing
    is perturbed until the transition learns useful dynamics.
    """

    def __init__(self, state_dim: int, driver_dim: int, hidden: int = 512):
        super().__init__()
        self.state_dim = state_dim
        self.driver_dim = driver_dim
        self.net = nn.Sequential(
            nn.Linear(state_dim + driver_dim, hidden),
            nn.GELU(),
            nn.Linear(hidden, hidden),
            nn.GELU(),
            nn.Linear(hidden, state_dim),
        )
        # zero-init the residual head -> Δ==0 at start -> ŝ_{t+1}=s_t (recoverable)
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def step(self, s_t: torch.Tensor, driver_t: torch.Tensor) -> torch.Tensor:
        return s_t + self.net(torch.cat([s_t, driver_t], dim=-1))

    def forward(self, s_seq: torch.Tensor, driver_seq: torch.Tensor) -> torch.Tensor:
        """s_seq (B,T,state_dim), driver_seq (B,T,driver_dim) ->
        predicted next-states ŝ (B,T-1,state_dim) where ŝ[:,t] predicts s[:,t+1]."""
        return self.step(s_seq[:, :-1], driver_seq[:, :-1])


class PhiRenderer(nn.Module):
    """O(s, φ): render observation-product-conditioned reflectance from the state.

    φ (product id, e.g. L1C vs L2A) FiLM-modulates the decoded observation. Used
    for the factorization / controllable-rendering capability (Table 2 / Fig 3).
    Token-level here (per patch-token); full spatial rendering reuses the Stage1.8
    factorizer decoder. FiLM is zero-init -> φ has no effect at start.
    """

    def __init__(self, state_dim: int, n_products: int, out_bands: int = 4, hidden: int = 256):
        super().__init__()
        self.hidden = hidden
        self.pre = nn.Sequential(nn.LayerNorm(state_dim), nn.Linear(state_dim, hidden), nn.GELU())
        self.film = nn.Embedding(n_products, 2 * hidden)
        nn.init.zeros_(self.film.weight)  # γ=0,β=0 -> identity at start (φ has no effect)
        self.act = nn.GELU()
        self.head = nn.Linear(hidden, out_bands)

    def forward(self, s: torch.Tensor, phi: torch.Tensor) -> torch.Tensor:
        """s (..., state_dim), phi (long, broadcastable to s[...,0]) -> (..., out_bands)."""
        h = self.pre(s)
        gamma_beta = self.film(phi)
        gamma, beta = gamma_beta[..., : self.hidden], gamma_beta[..., self.hidden :]
        h = (1.0 + gamma) * h + beta
        return self.head(self.act(h))


class ObsWorldB4(nn.Module):
    def __init__(self, hparams: Optional[SimpleNamespace] = None, contract_cfg: Optional[dict] = None):
        super().__init__()
        self.hparams = hparams if hparams is not None else contextformer6m_hparams()
        cfg = contract_cfg or {}
        self.state_dim = int(cfg.get("state_dim", 256))
        self.n_products = int(cfg.get("n_products", 2))
        self.context_len = self.hparams.context_length
        self.target_len = self.hparams.target_length
        self.driver_dim = self.hparams.n_weather

        # shared encoder + forecast backbone (B0-recoverable; captures z via hook)
        self.q = PVTContextformerQ(self.hparams)
        # world-model heads on the shared z
        self.projector = SpatialStateProjector(in_dim=self.hparams.n_hidden, state_dim=self.state_dim)
        self.transition = ControlledTransition(self.state_dim, self.driver_dim)
        self.renderer = PhiRenderer(self.state_dim, self.n_products)

    # ---- forecast (== B0 when contract off) ---------------------------------
    def forecast(self, data, pred_start=None, preds_length=None):
        pred_start = self.context_len if pred_start is None else pred_start
        preds_length = self.target_len if preds_length is None else preds_length
        preds, z = self.q.encode(data, pred_start=pred_start, preds_length=preds_length)
        return preds, z

    # ---- weather -> per-patch-token driver ----------------------------------
    def _driver_per_token(self, weather: torch.Tensor, b_patch: int, T: int) -> torch.Tensor:
        """weather (B,T,driver) -> (b_patch,T,driver) by repeating over patch tokens."""
        B = weather.shape[0]
        reps = b_patch // B
        return weather.unsqueeze(1).expand(B, reps, T, weather.shape[-1]).reshape(b_patch, T, weather.shape[-1])

    def latent_future_loss(self, s: torch.Tensor, driver: torch.Tensor) -> torch.Tensor:
        """Non-trivial: roll the transition over the whole sequence and match the
        predicted FUTURE state to the encoder's true future state (stop-grad)."""
        s_hat = self.transition(s, driver)              # (b_patch, T-1, state_dim) predicts s[:,1:]
        target = s[:, 1:].detach()
        fut = slice(self.context_len, self.context_len + self.target_len)
        # align: s_hat[:,t] predicts s[:,t+1]; future targets are indices [c_l .. c_l+tl-1]
        pred_fut = s_hat[:, self.context_len - 1 : self.context_len - 1 + self.target_len]
        true_fut = s[:, fut].detach()
        return F.mse_loss(pred_fut, true_fut)

    @staticmethod
    def vicreg_loss(s: torch.Tensor, gamma: float = 1.0, eps: float = 1e-4):
        """VICReg anti-collapse on the state: variance hinge + covariance decorrelation.

        This is the fix for the contract≈0 pathology: the earlier teacher-student
        latent-future was ~0 because the state COLLAPSED (cos≈0.9996). Forcing each
        state dim to keep variance (≥gamma) and decorrelating dims keeps z from
        degenerating, so the transition must model REAL dynamics and the JEPA
        latent-future becomes a genuine learning signal.
        """
        x = s.reshape(-1, s.shape[-1])
        n, d = x.shape
        std = torch.sqrt(x.var(dim=0) + eps)
        var_term = F.relu(gamma - std).mean()
        xc = x - x.mean(dim=0, keepdim=True)
        cov = (xc.T @ xc) / max(n - 1, 1)
        off = cov - torch.diag(torch.diagonal(cov))
        cov_term = off.pow(2).sum() / d
        return var_term, cov_term

    def forward(self, data, pred_start=None, preds_length=None, lambdas: Optional[SimpleNamespace] = None):
        preds, z = self.forecast(data, pred_start, preds_length)   # z: (b_patch, T, n_hidden)
        if lambdas is None:
            return preds
        logs, total = {}, preds.new_zeros(())
        b_patch, T, _ = z.shape
        s = self.projector(z)                                       # (b_patch, T, state_dim)
        lam_dyn = float(getattr(lambdas, "dyn", 0.0))
        if lam_dyn > 0:
            driver = self._driver_per_token(data["dynamic"][1], b_patch, T)
            l_dyn = self.latent_future_loss(s, driver)
            logs["latent_future"] = l_dyn.detach()
            total = total + lam_dyn * l_dyn
        lam_vic = float(getattr(lambdas, "vic", 0.0))
        if lam_vic > 0:
            var_t, cov_t = self.vicreg_loss(s)
            logs["vic_var"], logs["vic_cov"] = var_t.detach(), cov_t.detach()
            total = total + lam_vic * (var_t + cov_t)
        logs["contract_total"] = total.detach()
        return preds, {"total": total, "logs": logs}

    @classmethod
    def from_b0(cls, ckpt_path: str, contract_cfg: Optional[dict] = None, strict: bool = True) -> "ObsWorldB4":
        """Init the shared encoder/backbone from a B0 or official ContextFormer ckpt;
        the world-model heads start fresh (recoverable: their aux losses are opt-in)."""
        hp = contextformer6m_hparams(pvt_pretrained=False)
        obj = cls(hp, contract_cfg=contract_cfg)
        rep = PVTContextformerQ.from_checkpoint(ckpt_path, hparams=hp, strict=strict)
        obj.q.load_state_dict(rep.state_dict())
        return obj

    def num_params(self) -> int:
        return sum(p.numel() for p in self.parameters())
