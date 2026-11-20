"""Matched D base predictor ablation: instantiate no dynamic state modules."""
import torch
from torch import nn
from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams
from models.losses.masked_l2_ndvi import MaskedL2NDVILoss
from models.losses.supervision_v2 import global_mean, endpoint_weights
from models.terrastate_candidate_c import TerraStateCandidateC, CC_TRAIN_PARTITIONS


class SpanWorldBaselineOnly(nn.Module):
    ARCH = "SpanWorldBaselineOnly"
    ROUTE_VERSION = "spanworld_baseline_only_v1"
    FACTUAL_ENDPOINTS = TerraStateCandidateC.FACTUAL_ENDPOINTS
    LAMBDA_FIELDS = TerraStateCandidateC.LAMBDA_FIELDS
    recursive_candidates = TerraStateCandidateC.recursive_candidates
    draw_endpoint_plan = TerraStateCandidateC.draw_endpoint_plan

    def __init__(self, hparams=None, contract_cfg=None):
        super().__init__()
        cfg = contract_cfg or {}
        if cfg.get("use_adaln", False) or cfg.get("factual_path", "direct") != "direct":
            raise ValueError("baseline-only has no state/AdaLN or recursive path")
        self.hparams = hparams or contextformer6m_hparams(pvt_pretrained=False)
        self.hparams.zero_empty_history_reference = True
        self.q = PVTContextformerQ(self.hparams)
        self.context_len = self.hparams.context_length
        self.target_len = self.hparams.target_length
        self.freeze_b0 = False
        self.use_adaln = False
        self.supervision_v2 = True
        self.factual_path = "direct"
        self.cc_train_partitions = CC_TRAIN_PARTITIONS
        self.lc_min, self.lc_max = 10, 40
        self.eo_traj_weight = float(cfg.get("eo_traj_weight", 1.))
        self.eo_endpoint_weight = float(cfg.get("eo_endpoint_weight", 1.))
        self.ndvi_loss = MaskedL2NDVILoss(lc_min=10, lc_max=40,
            context_length=self.context_len, target_length=self.target_len,
            ndvi_pred_idx=0, ndvi_targ_idx=0, pred_mask_value=-1,
            scale_by_std=False, exclude_unsupervised_pixels=True)

    def config(self):
        return dict(arch=self.ARCH, route_version=self.ROUTE_VERSION,
                    experiment="baseline_only_retrain", training_stage="stage2",
                    variant="D", factual_path="direct", use_adaln=False,
                    freeze_b0=self.freeze_b0, supervision_v2=True,
                    season_encoding="annual_sincos_v1", season_route="tokens_only",
                    context_length=self.context_len, target_length=self.target_len,
                    eo_traj_weight=self.eo_traj_weight, eo_endpoint_weight=self.eo_endpoint_weight,
                    factual_endpoints=list(self.FACTUAL_ENDPOINTS), continuation="not_applicable")

    def forecast(self, data):
        # Match full-base prior exactly, including disabled MTM/dropout during forecast.
        was = self.q.core.training
        self.q.core.eval()
        try:
            pred, _ = self.q.encode(data, pred_start=self.context_len, preds_length=self.target_len)
            return pred
        finally:
            self.q.core.train(was)

    def forward(self, data, lambdas=None, endpoint_plan=None, rng=None):
        pred = self.forecast(data)
        if lambdas is None:
            return pred
        if any(float(getattr(lambdas, k, 0)) != 0 for k in self.LAMBDA_FIELDS):
            raise ValueError("baseline-only cannot carry state-specific objectives")
        if data.get("_supervision_window_counts") is not None:
            raise ValueError("locked baseline topology is 4x8x1; no accumulation window")
        if endpoint_plan is None:
            if rng is None:
                raise ValueError("endpoint plan required")
            endpoint_plan = self.draw_endpoint_plan(rng)
        traj, info = self.ndvi_loss(pred, data)
        supervised = info["global_valid_pixels"] if self.eo_traj_weight > 0 else pred.new_zeros(())
        cl, tl = self.context_len, self.target_len
        target = data["dynamic"][0][:, cl:cl+tl, 0:1]
        cloud = (data["dynamic_mask"][0][:, cl:cl+tl] < 1.).type_as(pred)
        lc = data["landcover"]
        lc_mask = ((lc >= self.lc_min) & (lc <= self.lc_max)).type_as(pred)
        endpoint = pred.new_zeros(())
        ep_logs = []
        for item in endpoint_plan:
            ep = int(item["endpoint"])
            if not 1 <= ep <= tl or tuple(item["partition"]) != (ep,):
                raise ValueError("baseline endpoint must be direct")
            valid = endpoint_weights(cloud[:, ep-1], lc_mask)
            one, count = global_mean((((target[:, ep-1]-pred[:, ep-1])**2)*valid).sum(), valid.sum())
            endpoint = endpoint + one
            if self.eo_endpoint_weight > 0:
                supervised = supervised + count
            ep_logs.append(dict(endpoint=ep, partition=[ep], n_segments=1, eo_endpoint=one.detach()))
        endpoint = endpoint / max(len(endpoint_plan), 1)
        total = self.eo_traj_weight * traj + self.eo_endpoint_weight * endpoint
        return pred, dict(total=total, global_supervised_count=supervised,
                         logs=dict(eo_traj=traj.detach(), eo_endpoint=endpoint.detach(),
                                   eo_total=total.detach(), total=total.detach()),
                         endpoint_plan=endpoint_plan, endpoint_logs=ep_logs, factual_path="direct")


def load_stage1_base_only(model, path, expected_sha256):
    from models.spanworld_full_base import _verified_checkpoint
    ck = _verified_checkpoint(path, expected_sha256)
    if ck.get("arch") != "SpanWorldFullBase" or ck.get("training_stage") != "stage1":
        raise ValueError("requires completed shared full-base stage1 parent")
    inherited = {k: v for k, v in ck["b4_state_dict"].items() if k.startswith("q.")}
    if set(inherited) != set(model.state_dict()):
        raise ValueError("base predictor key set mismatch")
    model.load_state_dict(inherited, strict=True)
    assert all(torch.equal(v, inherited[k]) for k, v in model.state_dict().items())
    assert all(k.startswith("q.") for k in model.state_dict())
    return dict(missing=[], inherited_tensors=len(inherited), max_abs_diff=0.)
