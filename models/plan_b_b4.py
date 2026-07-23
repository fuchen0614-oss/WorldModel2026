"""plan-b-pvt · B4 = TerraState — horizon-conditioned, load-bearing predictive-state
world model on the frozen Contextformer/B0 backbone (doc 84 §1.2 / §3.2 closure ②).

Contract (doc 84 §1.2):
    z_t     = P(E_ctx(o_≤t))                                   # context-only spatial state
    d_h     = WeatherEncoder24(U[t:t+h])                       # full-24 future weather window, any h
    z_{t+h} = z_t + Δ(LN z_t, Fuse(d_h, Geo(G), ψ(h)))         # ONE shared horizon transition
    ŷ_{t+h} = ŷ^{B0}_{t+h} + α · O_δ(z_{t+h})                  # state dynamics correct B0's error

Stage-1 design (B0 frozen — this file):
- ONE B0 core serves BOTH the B0 forecast and the context-only state pass (no second
  backbone). When B0 is frozen the TRAINED params are: projector, WeatherEncoder24,
  GeoEncoder, TimeEmbedding, transition Δ, O_δ, gate α. (See `trainable_parameters`.)
- Load-bearing: the DIRECT horizon transition is ON the forecast path
  (ŷ = B0 + α·O_δ(direct T)); cutting/ablating T changes the forecast.
- Anti-starvation (doc 84 correction 2): the residual branch is supervised by an
  UNGATED residual target r*=y−sg(ŷ_B0), so WeatherEncoder/T/O_δ receive gradient from
  step 1 regardless of the zero-init gate (which alone would starve them).
- direct vs composed are two genuinely different call paths (NOT iterated one-step).
- Strong-baseline-recoverable: gate α is zero-init → ŷ == B0 at init (bit-exact).
- Driver sensitivity (doc 84 correction 3): B0 preds are computed once and DETACHED;
  matched/shuffled/null weather is applied ONLY to the T branch, so any output change
  is attributable to T, not to B0 re-reading weather.

Kept from the earlier one-step draft (doc 84 review I): the unpatchify + residual-head
+ zero-init-gate recoverability idea. Removed: the trivial iterated one-step rollout /
one-step "composition".
"""
from __future__ import annotations

import math
from contextlib import nullcontext
from types import SimpleNamespace
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams
from models.encoders.state_projection import SpatialStateProjector
from models.losses.masked_l2_ndvi import MaskedL2NDVILoss


class TimeEmbedding(nn.Module):
    """Sinusoidal embedding of the (integer) elapsed horizon h."""

    def __init__(self, dim: int, max_h: int = 64):
        super().__init__()
        self.dim = dim
        pos = torch.arange(max_h + 1).float().unsqueeze(1)
        div = torch.exp(torch.arange(0, dim, 2).float() * (-math.log(10000.0) / dim))
        tab = torch.zeros(max_h + 1, dim)
        tab[:, 0::2] = torch.sin(pos * div)
        tab[:, 1::2] = torch.cos(pos * div)
        self.register_buffer("table", tab)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        return self.table[h]


class WeatherEncoder24(nn.Module):
    """Encode an arbitrary-length FUTURE weather window (full-24) with a shared GRU.

    A single forward over U[t:t+H] yields the encodings of EVERY prefix U[t:t+h]
    (h=1..H) as the per-step hidden states — so all horizons come from one pass.
    """

    def __init__(self, in_dim: int = 24, hidden: int = 128):
        super().__init__()
        self.gru = nn.GRU(in_dim, hidden, batch_first=True)
        self.out_dim = hidden

    def all_prefixes(self, u_future: torch.Tensor) -> torch.Tensor:
        out, _ = self.gru(u_future)          # (B, H, hidden); out[:,h-1] == enc(U[:h])
        return out

    def window(self, u_sub: torch.Tensor) -> torch.Tensor:
        out, _ = self.gru(u_sub)             # encode a specific sub-window
        return out[:, -1]                    # (B, hidden)


class GeoEncoder(nn.Module):
    """Static geography (reuse B0's 3 DEM channels) -> per-patch geo code. No new data."""

    def __init__(self, in_ch: int = 3, patch_size: int = 4, out_dim: int = 64):
        super().__init__()
        self.patch_size = patch_size
        self.mlp = nn.Sequential(nn.Linear(in_ch, out_dim), nn.GELU(), nn.Linear(out_dim, out_dim))

    def forward(self, static3: torch.Tensor) -> torch.Tensor:
        b, c, h, w = static3.shape
        g = F.avg_pool2d(static3, self.patch_size)          # (B,3,H',W')
        hp, wp = g.shape[-2:]
        g = g.permute(0, 2, 3, 1).reshape(b * hp * wp, c)   # (B·H'·W', 3) patch-major (matches PVT)
        return self.mlp(g)


class HorizonTransition(nn.Module):
    """ONE shared controlled residual transition z_{t+h}=z_t+Δ(LN z_t, cond_h).

    Δ is normally initialised (NOT zero) so T is genuinely weather/horizon-sensitive
    from the start; forecast recoverability comes from the zero-init GATE, not from T.
    The SAME module is called for direct and for each leg of composed.
    """

    def __init__(self, state_dim: int, cond_dim: int, hidden: int = 512):
        super().__init__()
        self.ln = nn.LayerNorm(state_dim)
        self.net = nn.Sequential(
            nn.Linear(state_dim + cond_dim, hidden), nn.GELU(),
            nn.Linear(hidden, hidden), nn.GELU(),
            nn.Linear(hidden, state_dim),
        )

    def forward(self, z: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        return z + self.net(torch.cat([self.ln(z), cond], dim=-1))


# PRE-REGISTERED composition partitions (doc84 P4), frozen before any training:
#   TRAIN_PARTITIONS  — used INSIDE the cmp/con loss (balanced splits reaching h=10).
#   HELDOUT_PARTITIONS — eval-ONLY composition-consistency test, NEVER trained on.
TRAIN_PARTITIONS = [(5, 5), (4, 6), (6, 4)]
HELDOUT_PARTITIONS = [(3, 7), (7, 3), (2, 8), (8, 2), (10, 10)]


class ObsWorldB4(nn.Module):
    def __init__(self, hparams: Optional[SimpleNamespace] = None, contract_cfg: Optional[dict] = None):
        super().__init__()
        self.hparams = hparams if hparams is not None else contextformer6m_hparams()
        cfg = contract_cfg or {}
        self.state_dim = int(cfg.get("state_dim", 256))
        self.context_len = self.hparams.context_length
        self.target_len = self.hparams.target_length
        self.driver_dim = self.hparams.n_weather              # 24 (full24)
        self.patch_size = self.hparams.patch_size
        self.n_out = self.hparams.n_out
        self.freeze_b0 = bool(cfg.get("freeze_b0", True))
        self.dw = int(cfg.get("dw", 128)); self.dg = int(cfg.get("dg", 64)); self.dh = int(cfg.get("dh", 64))
        self.cond_dim = int(cfg.get("cond_dim", 256))

        # shared B0 backbone (context-only state pass + B0 forecast both use THIS core)
        self.q = PVTContextformerQ(self.hparams)
        # TerraState branch (trained even when B0 is frozen)
        self.projector = SpatialStateProjector(in_dim=self.hparams.n_hidden, state_dim=self.state_dim)
        self.weather_enc = WeatherEncoder24(self.driver_dim, self.dw)
        self.geo_enc = GeoEncoder(3, self.patch_size, self.dg)
        self.time_emb = TimeEmbedding(self.dh, max_h=max(64, self.target_len))
        self.fuse = nn.Sequential(nn.Linear(self.dw + self.dg + self.dh, self.cond_dim),
                                  nn.GELU(), nn.Linear(self.cond_dim, self.cond_dim))
        self.transition = HorizonTransition(self.state_dim, self.cond_dim)
        self.o_delta = nn.Linear(self.state_dim, self.n_out * self.patch_size ** 2)
        self.gate = nn.Parameter(torch.zeros(1))              # zero-init -> ŷ==B0 at init
        # PRE-REGISTERED composition split (doc84 P4): TRAIN partitions enter the cmp/con LOSS;
        # HELD-OUT partitions are eval-ONLY composition tests (never trained on).
        self.partitions = [tuple(p) for p in cfg.get("partitions", TRAIN_PARTITIONS)]
        self.heldout_partitions = [tuple(p) for p in cfg.get("heldout_partitions", HELDOUT_PARTITIONS)]
        # Stage-1.8 factorizer is APPENDIX-ONLY (doc84 §1.3): it is NOT part of B4's main
        # method and is not connected here. models/stage1_8_factorizer.py is kept (not deleted)
        # but B4 does not use it; a frozen-teacher on/off ablation is deferred, not assumed.
        # masked NDVI loss — SAME protocol as B0 (clear cloud <1 × vegetation lc∈[lc_min,lc_max])
        self.lc_min, self.lc_max = int(cfg.get("lc_min", 10)), int(cfg.get("lc_max", 40))
        self.ndvi_loss = MaskedL2NDVILoss(
            lc_min=self.lc_min, lc_max=self.lc_max, context_length=self.context_len,
            target_length=self.target_len, ndvi_pred_idx=0, ndvi_targ_idx=0,
            pred_mask_value=-1, scale_by_std=False,
        )

        if self.freeze_b0:
            for p in self.q.parameters():
                p.requires_grad_(False)

    # ---- context-only B0 pass (no future satellite / no future weather leakage) ----
    def _context_only_data(self, data):
        """Keep full length 30 but ZERO the future frames AND future weather. The
        transformer masks future image tokens to mask_token; future weather -> 0 ->
        embed_weather(0) is a constant, so the state cannot see any future info.
        (Slicing to C frames is unsafe: the core's T==c_l branch pads images to 30 but
        NOT weather, causing a 30-vs-10 mismatch.)"""
        c = self.context_len
        x = data["dynamic"][0].clone(); x[:, c:] = 0.0
        w = data["dynamic"][1].clone(); w[:, c:] = 0.0
        m = data["dynamic_mask"][0].clone(); m[:, c:] = 0.0
        return {"dynamic": [x, w], "dynamic_mask": [m], "static": data["static"]}

    def _b0_and_state(self, data):
        """Two eval-mask passes of the SHARED core:
          (1) full history + FUTURE WEATHER  -> the real B0 forecast (legit driver);
          (2) context frames only            -> context-only state z_t (no leakage).
        When B0 is frozen both are detached; the state branch still trains via projector."""
        core = self.q.core
        was_training = core.training
        core.eval()
        ctx = torch.no_grad() if self.freeze_b0 else nullcontext()
        with ctx:
            preds_b0, _ = self.q.encode(data, pred_start=self.context_len, preds_length=self.target_len)
            _, z_ctx = self.q.encode(self._context_only_data(data),
                                     pred_start=self.context_len, preds_length=self.target_len)
        if was_training:
            core.train()
        if self.freeze_b0:
            preds_b0, z_ctx = preds_b0.detach(), z_ctx.detach()
        z_t = self.projector(z_ctx[:, self.context_len - 1])       # (B_patch, state_dim) context-only
        return preds_b0, z_t

    # ---- weather -> per-patch broadcast --------------------------------------
    @staticmethod
    def _to_patch(x, b_patch):
        """(B, ...) -> (B_patch, ...) repeating over the H'·W' patch tokens."""
        b = x.shape[0]
        reps = b_patch // b
        return x.unsqueeze(1).expand(b, reps, *x.shape[1:]).reshape(b_patch, *x.shape[1:])

    def _cond(self, d, geo, h_emb):
        return self.fuse(torch.cat([d, geo, h_emb], dim=-1))

    # ---- direct / composed (two genuinely different call paths) --------------
    def direct_state(self, z_t, u_future, geo, h: int):
        """z_dir = T(z_t, U[t:t+h], G, h) — ONE horizon-conditioned call."""
        b_patch = z_t.shape[0]
        d = self._to_patch(self.weather_enc.window(u_future[:, :h]), b_patch)   # (B_patch, dw)
        he = self.time_emb(torch.full((b_patch,), h, device=z_t.device, dtype=torch.long))
        return self.transition(z_t, self._cond(d, geo, he))

    def composed_state(self, z_t, u_future, geo, h1: int, h2: int):
        """z_cmp = T(T(z_t, U[t:t+h1], G, h1), U[t+h1:t+h1+h2], G, h2) — TWO calls,
        different sub-windows/horizons. NOT an iterated fixed one-step operator."""
        b_patch = z_t.shape[0]
        d1 = self._to_patch(self.weather_enc.window(u_future[:, :h1]), b_patch)
        he1 = self.time_emb(torch.full((b_patch,), h1, device=z_t.device, dtype=torch.long))
        z_mid = self.transition(z_t, self._cond(d1, geo, he1))
        d2 = self._to_patch(self.weather_enc.window(u_future[:, h1:h1 + h2]), b_patch)
        he2 = self.time_emb(torch.full((b_patch,), h2, device=z_t.device, dtype=torch.long))
        return self.transition(z_mid, self._cond(d2, geo, he2))

    def _direct_residual(self, z_t, u_future, geo, B, H, W):
        """Batched DIRECT residual over horizons h=1..target_len -> (B, target_len, n_out, H, W)."""
        b_patch = z_t.shape[0]
        Hh = self.target_len
        d_all = self._to_patch(self.weather_enc.all_prefixes(u_future), b_patch)     # (B_patch, Hh, dw)
        he = self.time_emb(torch.arange(1, Hh + 1, device=z_t.device))              # (Hh, dh)
        he = he.unsqueeze(0).expand(b_patch, Hh, -1)
        geo_e = geo.unsqueeze(1).expand(b_patch, Hh, geo.shape[-1])
        cond = self._cond(d_all, geo_e, he)                                          # (B_patch, Hh, cond)
        z_th = self.transition(z_t.unsqueeze(1).expand(b_patch, Hh, self.state_dim), cond)
        patches = self.o_delta(z_th)                                                 # (B_patch, Hh, n_out·ps²)
        return self._unpatchify(patches, B, H, W)

    def _unpatchify(self, patches, B, H, W):
        ps, no = self.patch_size, self.n_out
        hp, wp, tf = H // ps, W // ps, patches.shape[1]
        x = patches.reshape(B, hp, wp, tf, no, ps, ps)
        return x.permute(0, 3, 4, 1, 5, 2, 6).reshape(B, tf, no, H, W)

    def _geo_weather(self, data):
        geo = self.geo_enc(data["static"][0][:, :3])                                 # (B_patch, dg)
        u_future = data["dynamic"][1][:, self.context_len:self.context_len + self.target_len]  # (B, Hh, 24)
        return geo, u_future

    # ---- forecast = B0 + gate·direct-residual (LOAD-BEARING) -----------------
    def forecast(self, data, want_state: bool = False):
        preds_b0, z_t = self._b0_and_state(data)
        hr = data["dynamic"][0]
        B, H, W = hr.shape[0], hr.shape[-2], hr.shape[-1]
        geo, u_future = self._geo_weather(data)
        residual = self._direct_residual(z_t, u_future, geo, B, H, W)                 # (B, Hh, n_out, H, W)
        preds = preds_b0 + self.gate * residual
        if want_state:
            return preds, preds_b0, residual, z_t, geo, u_future
        return preds

    # ---- composed prediction + weather intervention + masked losses ----------
    def _decode_state(self, z_state, B, H, W):
        """Decode a single-horizon state (B_patch, state_dim) -> NDVI (B, n_out, H, W)."""
        patches = self.o_delta(z_state).unsqueeze(1)          # (B_patch, 1, n_out·ps²)
        return self._unpatchify(patches, B, H, W)[:, 0]       # (B, n_out, H, W)

    def composed_prediction(self, preds_b0, z_t, u_future, geo, h1: int, h2: int, B, H, W):
        """ŷ_cmp at horizon h=h1+h2 = B0[h] + gate·O_δ(composed state). A real DECODED
        prediction (doc84 stage-1.5 ①), not just a latent."""
        z_cmp = self.composed_state(z_t, u_future, geo, h1, h2)
        r = self._decode_state(z_cmp, B, H, W)                # (B, n_out, H, W)
        return preds_b0[:, h1 + h2 - 1] + self.gate * r       # (B, n_out, H, W)

    @staticmethod
    def _intervene(u, mode: str):
        # weather is NORMALIZED (mean-subtracted), so a zero tensor == the CLIMATOLOGICAL MEAN
        # forcing, NOT "no weather". "shuffled" (batch roll) is SMOKE-ONLY; formal driver-sensitivity
        # experiments must use a season/region-matched DONOR manifest, not a batch roll.
        if mode == "matched":
            return u
        if mode == "mean":                                    # climatological (normalized-zero) forcing
            return torch.zeros_like(u)
        if mode == "shuffled":                                # SMOKE-ONLY deterministic non-identity donor
            return torch.roll(u, shifts=1, dims=0)
        raise ValueError(mode)

    def forecast_weather(self, data, mode: str = "matched"):
        """T-only weather intervention (doc84 stage-1.5 ③): B0 prediction is FIXED
        (recomputed from real data, unchanged across modes); matched/shuffled/null
        weather is applied ONLY to the transition branch, so any output change is
        attributable to T, not to B0 re-reading weather."""
        preds_b0, z_t = self._b0_and_state(data)
        hr = data["dynamic"][0]
        B, H, W = hr.shape[0], hr.shape[-2], hr.shape[-1]
        geo, u_future = self._geo_weather(data)
        residual = self._direct_residual(z_t, self._intervene(u_future, mode), geo, B, H, W)
        return preds_b0, preds_b0 + self.gate * residual

    def composed_predictions(self, data, partitions=None):
        """Eval interface (doc84 P4): per partition (h1,h2) return (ŷ_direct[h], ŷ_composed[h])
        at horizon h=h1+h2. Parameterizable — pass partitions=[(3,7),(4,6),(5,5),…]."""
        partitions = partitions or self.partitions
        preds, preds_b0, _, z_t, geo, u_future = self.forecast(data, want_state=True)
        B, H, W = preds.shape[0], preds.shape[-2], preds.shape[-1]
        out = {}
        for (h1, h2) in partitions:
            h = h1 + h2
            out[(h1, h2)] = (preds[:, h - 1],
                             self.composed_prediction(preds_b0, z_t, u_future, geo, h1, h2, B, H, W))
        return out

    def _masked_mse1(self, pred, targ, cloud, lc_mask):
        """Masked MSE over ONE horizon on valid pixels = clear (cloud<1) × vegetation.
        Same pixel selection as B0's MaskedL2NDVILoss; all args (B, n_out, H, W)."""
        valid = cloud * lc_mask
        return (((targ - pred) ** 2) * valid).sum() / (valid.sum() + 1e-8)

    def forward(self, data, lambdas: Optional[SimpleNamespace] = None):
        preds, preds_b0, residual, z_t, geo, u_future = self.forecast(data, want_state=True)
        if lambdas is None:
            return preds
        lam = lambdas
        cl, tl = self.context_len, self.target_len
        B, H, W = preds.shape[0], preds.shape[-2], preds.shape[-1]
        lc = data["landcover"]
        lc_mask = ((lc >= self.lc_min) & (lc <= self.lc_max)).type_as(preds)          # (B,1,H,W)
        targ_win = data["dynamic"][0][:, cl:cl + tl, 0:1]                             # (B,20,1,H,W)
        cloud_win = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).type_as(preds)     # (B,20,1,H,W)
        logs, total = {}, preds.new_zeros(())
        # (a) DIRECT endpoint = masked forecast, EXACT B0 protocol (no raw mse)
        if float(getattr(lam, "fore", 0.0)) > 0:
            l_fore, _ = self.ndvi_loss(preds, data)
            logs["fore"] = l_fore.detach(); total = total + lam.fore * l_fore
        # (b) UNGATED residual supervision r*=y−sg(ŷ_B0), masked to valid pixels (anti-starvation)
        if float(getattr(lam, "resid", 0.0)) > 0:
            valid = cloud_win * lc_mask.unsqueeze(1)
            r_star = targ_win - preds_b0.detach()
            l_res = (((residual - r_star) ** 2) * valid).sum() / (valid.sum() + 1e-8)
            logs["resid"] = l_res.detach(); total = total + lam.resid * l_res
        # (c) COMPOSED endpoint (real target) + direct/composed consistency, over ALL partitions
        if float(getattr(lam, "cmp", 0.0)) > 0 or float(getattr(lam, "con", 0.0)) > 0:
            k = len(self.partitions)
            l_cmp = preds.new_zeros(()); l_dir = preds.new_zeros(()); l_con = preds.new_zeros(())
            for (h1, h2) in self.partitions:
                h = h1 + h2
                yhat_cmp = self.composed_prediction(preds_b0, z_t, u_future, geo, h1, h2, B, H, W)
                yhat_dir = preds[:, h - 1]
                targ_h, cloud_h = targ_win[:, h - 1], cloud_win[:, h - 1]
                l_cmp = l_cmp + self._masked_mse1(yhat_cmp, targ_h, cloud_h, lc_mask)
                l_dir = l_dir + self._masked_mse1(yhat_dir, targ_h, cloud_h, lc_mask)
                l_con = l_con + self._masked_mse1(yhat_cmp, yhat_dir.detach(), cloud_h, lc_mask)
            l_cmp, l_dir, l_con = l_cmp / k, l_dir / k, l_con / k
            if float(getattr(lam, "cmp", 0.0)) > 0:
                logs["cmp_ep"], logs["dir_ep"] = l_cmp.detach(), l_dir.detach()
                total = total + lam.cmp * (l_cmp + l_dir)
            if float(getattr(lam, "con", 0.0)) > 0:
                logs["con"] = l_con.detach(); total = total + lam.con * l_con
        # (d) anti-collapse on the state
        if float(getattr(lam, "vic", 0.0)) > 0:
            var_t, cov_t = self.vicreg_loss(z_t)
            logs["vic_var"], logs["vic_cov"] = var_t.detach(), cov_t.detach()
            total = total + lam.vic * (25.0 * var_t + cov_t)
        logs["gate"] = self.gate.detach().abs().mean()
        logs["total"] = total.detach()
        return preds, {"total": total, "logs": logs}

    @staticmethod
    def vicreg_loss(z, gamma: float = 1.0, eps: float = 1e-4):
        x = z.reshape(-1, z.shape[-1])
        n, d = x.shape
        std = torch.sqrt(x.var(dim=0) + eps)
        var_term = F.relu(gamma - std).mean()
        xc = x - x.mean(dim=0, keepdim=True)
        cov = (xc.T @ xc) / max(n - 1, 1)
        cov_term = (cov - torch.diag(torch.diagonal(cov))).pow(2).sum() / d
        return var_term, cov_term

    # ---- utilities -----------------------------------------------------------
    def trainable_parameters(self):
        return [p for p in self.parameters() if p.requires_grad]

    def unfreeze_b0(self):
        self.freeze_b0 = False
        for p in self.q.parameters():
            p.requires_grad_(True)

    @classmethod
    def from_b0(cls, ckpt_path: str, contract_cfg: Optional[dict] = None, strict: bool = True) -> "ObsWorldB4":
        hp = contextformer6m_hparams(pvt_pretrained=False)
        obj = cls(hp, contract_cfg=contract_cfg)
        rep = PVTContextformerQ.from_checkpoint(ckpt_path, hparams=hp, strict=strict)
        obj.q.load_state_dict(rep.state_dict())
        return obj

    def num_params(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def config(self) -> dict:
        """Full contract_cfg for EXACT checkpoint reconstruction (doc84 §五): dims, mask
        bounds and BOTH partition sets are saved so export rebuilds the identical model."""
        return {"state_dim": self.state_dim, "freeze_b0": self.freeze_b0,
                "dw": self.dw, "dg": self.dg, "dh": self.dh, "cond_dim": self.cond_dim,
                "lc_min": self.lc_min, "lc_max": self.lc_max,
                "partitions": [list(p) for p in self.partitions],
                "heldout_partitions": [list(p) for p in self.heldout_partitions]}

    @staticmethod
    def state_std(z):
        return z.reshape(-1, z.shape[-1]).std(dim=0).mean().item()

    @staticmethod
    def effective_rank(z):
        """Participation ratio of the state covariance eigenvalues (effective dimensionality)."""
        x = z.reshape(-1, z.shape[-1]); x = x - x.mean(0, keepdim=True)
        cov = (x.T @ x) / max(x.shape[0] - 1, 1)
        ev = torch.linalg.eigvalsh(cov).clamp(min=0)
        return (ev.sum() ** 2 / (ev.pow(2).sum() + 1e-12)).item()
