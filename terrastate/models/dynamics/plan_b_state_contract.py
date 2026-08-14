"""plan-b-pvt · config-driven state contract on the reproduced Contextformer.

Auxiliary (does NOT replace the NDVI prediction path — doc 71 §4.2); with all
components off / lambda=0 the forward+loss are EXACTLY B0 (strong-baseline
recoverable). Operates on the transformer features z (B_patch, T=30, n_hidden).

Latent-future = TEACHER-STUDENT (privileged distillation), NOT self-distillation:
  * student z_s : normal forecasting forward (future frames masked)
  * teacher z_t : forward with ALL frames visible (sees the real future), stop-grad
  * loss = 1 - cos( proj(z_s)[future], stopgrad(proj(z_t))[future] )
The teacher's future tokens are informed by the real future observation, so the
student's masked-future state is trained to predict that future-informed state.
Unlike self-distillation (student's own future tokens, trivially ~0), this is a
non-trivial signal and the dynamics evidence for Table 3.

Rows:
  B0: contract not built. B1: use_state, lambda=0 -> projector only, preds==B0.
  B2: + lambda_dyn>0 -> teacher-student latent-future. B3/B4: + phi (Stage1.8).
"""
from types import SimpleNamespace
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from models.encoders.state_projection import SpatialStateProjector


class PlanBStateContract(nn.Module):
    def __init__(self, feat_dim: int = 256, state_dim: int = 256,
                 context_len: int = 10, target_len: int = 20,
                 use_state: bool = True, use_latent_future: bool = True, **kw):
        super().__init__()
        self.context_len = context_len
        self.target_len = target_len
        self.use_state = use_state
        self.use_latent_future = use_latent_future
        if use_state:
            self.projector = SpatialStateProjector(in_dim=feat_dim, state_dim=state_dim)

    def project(self, z: torch.Tensor) -> torch.Tensor:
        return self.projector(z) if self.use_state else z

    def teacher_student_loss(self, z_student: torch.Tensor, z_teacher: torch.Tensor) -> torch.Tensor:
        s_s = self.project(z_student)
        s_t = self.project(z_teacher).detach()
        fut = slice(self.context_len, self.context_len + self.target_len)
        return (1.0 - F.cosine_similarity(s_s[:, fut], s_t[:, fut], dim=-1)).mean()

    def loss(self, z_student, z_teacher, batch, lambdas: SimpleNamespace) -> dict:
        logs = {}
        total = z_student.new_zeros(())
        if (self.use_latent_future and z_teacher is not None
                and getattr(lambdas, "dyn", 0.0) > 0):
            l = self.teacher_student_loss(z_student, z_teacher)
            logs["latent_future"] = l.detach()
            total = total + lambdas.dyn * l
        logs["contract_total"] = total.detach()
        return {"total": total, "logs": logs}
