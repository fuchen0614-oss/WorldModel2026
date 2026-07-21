"""plan-b-pvt · `q: image -> z` wrapper around the official Contextformer.

This is the plan-B encoder/backbone entry point (doc 75 §9). It:
  1. defines the exact `contextformer6M` (PVT, published 6.1M SOTA) hparams;
  2. builds the vendored `ContextFormer` (see contextformer_official.py);
  3. loads the OFFICIAL Zenodo weights by stripping the Lightning `model.`
     prefix (Gate-0 A2: reproduce Contextformer in our torch-2.x stack);
  4. exposes both the full forecasting forward AND the spatio-temporal state
     `z` (the transformer output *before* the NDVI head) that the ObsWorld
     state contract will later hang off.

Strong-baseline-recoverable principle (doc 71 §4.2): with the state contract
disabled, `PVTContextformerQ.forward` is EXACTLY the official Contextformer.

Official config (model_configs/contextformer/contextformer6M/seed=42.yaml) and
checkpoint keys were verified locally: 223 tensors, 6.06M params, all under a
`model.` prefix.
"""

from types import SimpleNamespace
from typing import Optional, Tuple

import torch
import torch.nn as nn

from .contextformer_official import ContextFormer


# --- exact contextformer6M (PVT, published SOTA) hyper-parameters -------------
# Values from the official yaml; the rest are add_model_specific_args defaults.
CONTEXTFORMER6M = dict(
    setting="en21x",
    context_length=10,
    target_length=20,
    patch_size=4,
    n_image=8,
    n_weather=24,
    n_hidden=256,
    n_out=1,
    n_heads=8,
    depth=3,
    mlp_ratio=4.0,
    mtm=True,
    leave_n_first=3,
    p_mtm=0.7,
    p_use_mtm=0.5,
    mask_clouds=True,
    use_weather=True,          # default (not overridden in the 6M yaml)
    predict_delta=False,
    predict_delta0=False,
    predict_delta_avg=False,
    predict_delta_max=False,
    pvt=True,
    pvt_frozen=False,
    add_last_ndvi=True,
    add_mean_ndvi=False,
    spatial_shuffle=False,
    # our extra knob (not in upstream): skip the timm ImageNet download when we
    # are going to overwrite PVT weights with the official checkpoint anyway.
    pvt_pretrained=True,
)


def contextformer6m_hparams(**overrides) -> SimpleNamespace:
    cfg = dict(CONTEXTFORMER6M)
    cfg.update(overrides)
    return SimpleNamespace(**cfg)


def load_official_ckpt(
    model: nn.Module, ckpt_path: str, strict: bool = True
) -> Tuple[list, list]:
    """Load an official GreenEarthNet Lightning checkpoint into a bare
    `ContextFormer`. Official keys are `model.<...>`; strip that prefix."""
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    sd = ckpt.get("state_dict", ckpt)
    prefix = "model."
    remapped = {
        k[len(prefix):]: v for k, v in sd.items() if k.startswith(prefix)
    }
    if not remapped:  # already a bare state_dict
        remapped = sd
    missing, unexpected = model.load_state_dict(remapped, strict=strict)
    return list(missing), list(unexpected)


class PVTContextformerQ(nn.Module):
    """Wraps the official Contextformer as `q: image -> z` + forecasting head.

    * `forward(data, pred_start, preds_length)` -> NDVI predictions (identical
      to the official model; this is the recoverable strong baseline).
    * `encode(...)` -> (predictions, z) where z is the transformer output before
      the NDVI head, shape (B*H'*W', T, n_hidden) — the ObsWorld predictive
      state the contract will operate on.
    """

    def __init__(self, hparams: Optional[SimpleNamespace] = None):
        super().__init__()
        self.hparams = hparams if hparams is not None else contextformer6m_hparams()
        self.core = ContextFormer(self.hparams)
        self._z: Optional[torch.Tensor] = None
        # tap the last transformer block's output (== `x` fed to `head`)
        self.core.blocks[-1].register_forward_hook(self._capture_z)

    def _capture_z(self, module, inputs, output):
        self._z = output

    @classmethod
    def from_official(
        cls,
        ckpt_path: str,
        hparams: Optional[SimpleNamespace] = None,
        strict: bool = True,
    ) -> "PVTContextformerQ":
        # PVT weights come from the official ckpt -> no need for the timm download
        hp = hparams or contextformer6m_hparams(pvt_pretrained=False)
        obj = cls(hp)
        missing, unexpected = load_official_ckpt(obj.core, ckpt_path, strict=strict)
        obj._load_report = {"missing": missing, "unexpected": unexpected}
        return obj

    @classmethod
    def from_checkpoint(
        cls,
        ckpt_path: str,
        hparams: Optional[SimpleNamespace] = None,
        strict: bool = True,
    ) -> "PVTContextformerQ":
        """Auto-detect and load either an OFFICIAL Lightning ckpt (`model.`-prefixed
        state_dict) or one of OUR B0/B1-B4 checkpoints (`core_state_dict`)."""
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        if isinstance(ckpt, dict) and "core_state_dict" in ckpt:
            hp = hparams or contextformer6m_hparams(pvt_pretrained=False)
            obj = cls(hp)
            miss, unexp = obj.core.load_state_dict(ckpt["core_state_dict"], strict=strict)
            obj._load_report = {"missing": list(miss), "unexpected": list(unexp)}
            return obj
        return cls.from_official(ckpt_path, hparams=hparams, strict=strict)

    def forward(self, data, pred_start: int = 0, preds_length: Optional[int] = None):
        preds, aux = self.core(data, pred_start=pred_start, preds_length=preds_length)
        return preds

    def encode(self, data, pred_start: int = 0, preds_length: Optional[int] = None):
        self._z = None
        preds = self.forward(data, pred_start=pred_start, preds_length=preds_length)
        return preds, self._z

    def num_params(self) -> int:
        return sum(p.numel() for p in self.core.parameters())
