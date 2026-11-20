"""Independent full-weather baseline + context-only state route.
Constructors never reset inherited readout; stage initialization is explicit.
"""
from contextlib import nullcontext
import hashlib
from pathlib import Path
import torch
from models.terrastate_candidate_c import TerraStateCandidateC


class SpanWorldFullBase(TerraStateCandidateC):
    ARCH = "SpanWorldFullBase"
    ROUTE_VERSION = "spanworld_full_base_v1"

    def __init__(self, hparams=None, contract_cfg=None):
        cfg = contract_cfg or {}
        self.training_stage = cfg.get("training_stage", "stage2")
        self.variant = cfg.get("variant", "A")
        if self.training_stage not in ("stage1", "stage2"):
            raise ValueError("unknown training stage")
        super().__init__(hparams, contract_cfg)
        self.history_state_only = False  # Runtime optimization; absent from config/state_dict.

    def config(self):
        cfg = super().config()
        cfg.update(training_stage=self.training_stage, variant=self.variant)
        return cfg

    def loss_candidate_c(self, data, lambdas, endpoint_plan=None, rng=None, want_diagnostics=False):
        if self.training_stage == "stage1":
            if self.eo_endpoint_weight != 0 or any(float(getattr(lambdas, k, 0)) != 0 for k in self.LAMBDA_FIELDS):
                raise ValueError("stage1 is trajectory-only: endpoint weight and auxiliary lambdas must be zero")
            if endpoint_plan:
                raise ValueError("stage1 endpoint_plan must be empty")
            endpoint_plan = []
        return super().loss_candidate_c(data, lambdas, endpoint_plan=endpoint_plan,
                                        rng=rng, want_diagnostics=want_diagnostics)

    def _prior_state(self, data):
        core = self.q.core
        was = core.training
        core.eval()
        try:
            with torch.no_grad() if self.freeze_b0 else nullcontext():
                # Capture each result immediately: q hook storage is overwritten per call.
                prior, _ = self.q.encode(data, pred_start=self.context_len,
                                         preds_length=self.target_len)
                if self.history_state_only:
                    z_ctx = self.q.encode_state(self._context_only_data(data),
                                                pred_start=self.context_len,
                                                preds_length=self.target_len)
                else:
                    _, z_ctx = self.q.encode(self._context_only_data(data),
                                             pred_start=self.context_len,
                                             preds_length=self.target_len)
        finally:
            core.train(was)
        if self.freeze_b0:
            prior, z_ctx = prior.detach(), z_ctx.detach()
        return prior, self.projector(z_ctx[:, self.context_len - 1])


def initialize_stage1(model):
    """Call once AFTER official q loading, never during stage2 or resume."""
    if model.use_adaln:
        raise ValueError("stage1 must disable AdaLN")
    model.freeze_b0 = True
    for p in model.q.parameters():
        p.requires_grad_(False)
    torch.nn.init.zeros_(model.o_delta.weight)
    torch.nn.init.zeros_(model.o_delta.bias)


def _verified_checkpoint(path, expected_sha256):
    if not expected_sha256 or len(expected_sha256) != 64:
        raise ValueError("explicit expected SHA256 required")
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha256.lower():
        raise ValueError("checkpoint SHA256 mismatch")
    return torch.load(path, map_location='cpu', weights_only=False)


def _inherit(module, sd, allowed_missing):
    own = module.state_dict()
    missing, extra = set(own) - set(sd), set(sd) - set(own)
    if missing != set(allowed_missing) or extra:
        raise ValueError(f"checkpoint keys mismatch missing={sorted(missing)} extra={sorted(extra)}")
    for k, v in sd.items():
        if own[k].shape != v.shape:
            raise ValueError(f"checkpoint shape mismatch: {k}")
    module.load_state_dict(sd, strict=not allowed_missing)
    after = module.state_dict()
    if any(not torch.equal(after[k].cpu(), v.cpu()) for k, v in sd.items()):
        raise ValueError("inherited tensor values differ")
    return {'inherited_tensors': len(sd), 'missing': sorted(missing)}


def load_official_baseline(model, path, *, expected_sha256, schema='lightning_model'):
    """Explicit schema: lightning_model(state_dict/model.*), core_state_dict, bare_core."""
    ck = _verified_checkpoint(path, expected_sha256)
    if schema == 'lightning_model':
        raw = ck['state_dict']
        if not raw or not all(k.startswith('model.') for k in raw):
            raise ValueError('expected exclusively model.* state_dict keys')
        sd = {k[len('model.'):]: v for k, v in raw.items()}
    elif schema == 'core_state_dict':
        sd = ck['core_state_dict']
    elif schema == 'bare_core':
        sd = ck
    else:
        raise ValueError(f'unsupported explicit schema: {schema}')
    result = _inherit(model.q.core, sd, {'season_proj.weight'})
    torch.nn.init.zeros_(model.q.core.season_proj.weight)
    return result


def load_stage1_parent(model, path, *, expected_sha256):
    """Stage2 weights-only inheritance; never reset o_delta or any inherited tensor."""
    ck = _verified_checkpoint(path, expected_sha256)
    cfg = ck.get('contract_cfg') or {}
    if cfg.get('arch') != model.ARCH or cfg.get('route_version') != model.ROUTE_VERSION:
        raise ValueError('parent is not the full-baseline route')
    if cfg.get('training_stage') != 'stage1':
        raise ValueError('parent is not a stage1 checkpoint')
    if cfg.get('use_adaln', False):
        raise ValueError('stage1 parent must not contain AdaLN')
    for k in ('state_dim', 'cond_dim', 'dw', 'dg', 'dh', 'lc_min', 'lc_max'):
        if cfg.get(k) != model.config().get(k):
            raise ValueError(f'parent contract mismatch: {k}')
    if cfg.get('freeze_b0') is not True:
        raise ValueError('stage1 parent must freeze the baseline')
    sd = ck['b4_state_dict']
    if 'q.core.season_proj.weight' not in sd or torch.count_nonzero(sd['q.core.season_proj.weight']).item() != 0:
        raise ValueError('stage1 parent token season must remain zero')
    missing = {'transition.adaln.weight', 'transition.adaln.bias'} if model.use_adaln else set()
    report = _inherit(model, ck['b4_state_dict'], missing)
    if model.use_adaln:
        # Explicitly initialize ONLY new tensors; constructor/resume retain originals.
        torch.nn.init.zeros_(model.transition.adaln.weight)
        torch.nn.init.zeros_(model.transition.adaln.bias)
    return report
