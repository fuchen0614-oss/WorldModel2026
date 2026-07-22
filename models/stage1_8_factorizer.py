"""plan-b-pvt · Stage1.8 observation-factorization model (world-model evidence).

Learns a shared, product-invariant land-surface state from paired Sentinel-2
L1C/L2A observations, plus a product-conditioned renderer O(z, phi) that can render
EITHER product from the SAME state. This is the Table-2 / Fig-3 evidence a pure
forecaster cannot produce (doc 71 §4.3, §7.2).

  q  : PVT-v2-b0 (in_chans=4, the 4 common bands B02/B03/B04/B8A) -> spatial state z
  phi: product token {L1C=0, L2A=1} -> FiLM (gamma,beta) on z
  O  : FiLM(z, phi) -> light conv decoder -> 4-band reflectance

Losses (forward returns a dict):
  recon   : O(q(X_a), phi_a) ~= X_a            self-reconstruction
  cross   : O(q(X_a), phi_b) ~= X_b            product controlled by phi, not z
  paired  : q(X_L1C) ~= q(X_L2A)               shared state across products
Standalone (own 4-band PVT); does NOT share weights with the 8-ch GreenEarthNet
Contextformer -- it is the factorization experiment, evaluated on its own.
"""
import timm
import torch
import torch.nn as nn
import torch.nn.functional as F

L1C, L2A = 0, 1


class Stage18Factorizer(nn.Module):
    def __init__(self, in_ch: int = 4, state_dim: int = 256, n_products: int = 2,
                 pvt_pretrained: bool = False):
        super().__init__()
        self.pvt = timm.create_model(
            "pvt_v2_b0.in1k", pretrained=pvt_pretrained, features_only=True, in_chans=in_ch,
        )
        # cat of the 4 PVT levels (interpolated to the finest) has 32+64+160+256 = 512 ch
        self.proj = nn.Conv2d(512, state_dim, kernel_size=1)
        self.phi = nn.Embedding(n_products, 2 * state_dim)   # -> (gamma, beta)
        nn.init.zeros_(self.phi.weight)                       # identity FiLM at init
        self.decoder = nn.Sequential(                        # 64->256 (x4), state_dim->in_ch
            nn.Conv2d(state_dim, 256, 3, padding=1), nn.GELU(),
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(256, 128, 3, padding=1), nn.GELU(),
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(128, 64, 3, padding=1), nn.GELU(),
            nn.Conv2d(64, in_ch, 3, padding=1), nn.Sigmoid(),   # reflectance in [0,1]
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, in_ch, H, W) -> z: (B, state_dim, H/4, W/4)"""
        feats = self.pvt(x)
        feats = [F.interpolate(f, size=feats[0].shape[-2:], mode="bilinear", align_corners=False)
                 for f in feats]
        return self.proj(torch.cat(feats, dim=1))

    def render(self, z: torch.Tensor, product_id: torch.Tensor) -> torch.Tensor:
        """z: (B, state_dim, h, w); product_id: (B,) long -> x_hat: (B, in_ch, H, W)"""
        gamma, beta = self.phi(product_id).chunk(2, dim=-1)   # each (B, state_dim)
        z = z * (1.0 + gamma[..., None, None]) + beta[..., None, None]   # FiLM
        return self.decoder(z)

    def forward(self, l1c, l2a, lambda_paired: float = 1.0) -> dict:
        B = l1c.shape[0]
        pid_l1c = torch.full((B,), L1C, device=l1c.device, dtype=torch.long)
        pid_l2a = torch.full((B,), L2A, device=l1c.device, dtype=torch.long)
        z1, z2 = self.encode(l1c), self.encode(l2a)

        recon = F.mse_loss(self.render(z1, pid_l1c), l1c) + F.mse_loss(self.render(z2, pid_l2a), l2a)
        cross = F.mse_loss(self.render(z1, pid_l2a), l2a) + F.mse_loss(self.render(z2, pid_l1c), l1c)
        paired = F.mse_loss(z1, z2)
        total = recon + cross + lambda_paired * paired
        return {"total": total, "recon": recon.detach(), "cross": cross.detach(),
                "paired": paired.detach()}
