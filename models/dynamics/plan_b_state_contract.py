"""plan-b-pvt · config-driven state contract on top of the reproduced Contextformer.

Auxiliary (does NOT replace the Contextformer NDVI prediction path — doc 71 §4.2):
it hangs a predictive-state contract on the transformer features `z`
(shape (B_patch=B·H'·W', T=30, n_hidden=256), axis-1 = time), so that with all
components off / all λ=0 the forward and loss are EXACTLY B0 (strong-baseline
recoverable).

Reuses pure-torch pieces already in the repo:
  - SpatialStateProjector  (models/encoders/state_projection.py)
  - StateDynamicsModule    (models/dynamics/state_dynamics_module.py, zero-init → identity)

Rows:
  B0: contract disabled entirely (this module not built / not called).
  B1: use_state=True, λ_dyn=0 → projector added but no loss uses it → preds ≡ B0.
  B2: + λ_dyn>0 → latent-future consistency (self-distillation of future tokens),
      regularizes the shared z. (No explicit D-driven transition on the prediction
      path → no double-counting of Contextformer's internal weather.)
  B3/B4: + φ / O_product on SSL4EO (Stage1.8), handled elsewhere.
"""
from types import SimpleNamespace
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from models.encoders.state_projection import SpatialStateProjector
from models.dynamics.state_dynamics_module import StateDynamicsModule


class PlanBStateContract(nn.Module):
    def __init__(
        self,
        feat_dim: int = 256,
        state_dim: int = 256,
        driver_dim: int = 24,
        context_len: int = 10,
        target_len: int = 20,
        use_state: bool = True,
        use_latent_future: bool = True,
        dynamics_type: str = "mlp",
    ):
        super().__init__()
        self.feat_dim = feat_dim
        self.state_dim = state_dim
        self.driver_dim = driver_dim
        self.context_len = context_len
        self.target_len = target_len
        self.use_state = use_state
        self.use_latent_future = use_latent_future

        if use_state:
            self.projector = SpatialStateProjector(in_dim=feat_dim, state_dim=state_dim)
        if use_latent_future:
            # zero-init residual dynamics -> identity at start (B0-recoverable)
            self.transition = StateDynamicsModule(
                latent_dim=state_dim, dynamics_type=dynamics_type,
                driver_dim=driver_dim, geo_dim=0, time_dim=1,
            )

    def project(self, z: torch.Tensor) -> torch.Tensor:
        return self.projector(z) if self.use_state else z

    def latent_future_loss(
        self, z: torch.Tensor, driver: torch.Tensor,
        spatial_factor: Optional[int] = None,
    ) -> torch.Tensor:
        """z: (B_patch, T, feat); driver: (B, T, driver_dim).
        s_context = mean over context tokens; predict each future token via the
        transition; align (cosine) to the model's own future token (stop-grad)."""
        Bp, T, _ = z.shape
        s = self.project(z)                              # (B_patch, T, state)
        if spatial_factor is None:
            spatial_factor = Bp // driver.shape[0]
        D = driver.repeat_interleave(spatial_factor, dim=0)  # (B_patch, T, driver_dim)
        s_ctx = s[:, : self.context_len].mean(1)         # (B_patch, state)

        total = z.new_zeros(())
        for h in range(self.target_len):
            t = self.context_len + h
            td = torch.full((Bp, 1), float(h + 1), device=z.device, dtype=s.dtype)
            s_pred = self.transition(s_ctx, driver=D[:, t], geo=None, time_delta=td)
            target = s[:, t].detach()
            total = total + (1.0 - F.cosine_similarity(s_pred, target, dim=-1)).mean()
        return total / self.target_len

    def loss(self, z, batch, lambdas: SimpleNamespace) -> dict:
        """Weighted contract loss. λ all 0 -> returns 0 (B0)."""
        logs = {}
        total = z.new_zeros(())
        if self.use_latent_future and getattr(lambdas, "dyn", 0.0) > 0:
            l = self.latent_future_loss(z, batch["dynamic"][1])
            logs["latent_future"] = l.detach()
            total = total + lambdas.dyn * l
        logs["contract_total"] = total.detach()
        return {"total": total, "logs": logs}
