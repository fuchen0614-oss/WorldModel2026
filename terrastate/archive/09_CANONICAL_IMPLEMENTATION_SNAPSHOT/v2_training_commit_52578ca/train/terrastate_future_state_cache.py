"""Future-state target cache (doc 88 deliverable B) — build + load, kept separate from
the inference path (doc 88: "cache 不得被正式 inference path 读取").

The frozen target (doc 88 §3.1):
    z*_{t+H} = sg( P_frozen( q_frozen( o_{<=t+H} ) ) )
computed by a COPY of the student's q/projector taken at training start (permanently
eval + no_grad). The target ENCODER input keeps the REAL future EO frames but EXPLICITLY
ZEROES the future weather (so the target cannot trivially copy the weather). Only the
terminal horizon h = target_len (=20) state is cached, in FP16, keyed by relative cube
path, with the frozen q/projector SHA, data-manifest SHA, field order, h and config SHA.

This module is import-light (torch + std-lib + the v2 common helpers); the dataset (xarray)
is passed IN by the CLI, never imported here.
"""
from __future__ import annotations

import copy
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from train.terrastate_v2_common import (
    FULL24_FIELD_ORDER, canonical_json_sha256, collate_with_ids, data_manifest_sha256,
    module_pair_sha256, relpath_of, state_sha, to_device_with_ids,
)

CACHE_SCHEMA = "terrastate_future_state_cache_v1"


class FrozenFutureStateEncoder(nn.Module):
    """Frozen (q, projector) copy — the doc-88 future-observation target encoder.

    Permanently eval + no_grad. Reuses the SAME encode entrypoint the model uses for its
    privileged all-frames pass (q.encode(data, pred_start=T, preds_length=0)), so the
    terminal-frame state is produced from the REAL future observation.
    """

    def __init__(self, q, projector, context_len: int, target_len: int, patch_size: int,
                 lc_min: int = 10, lc_max: int = 40, deepcopy: bool = True):
        super().__init__()
        self.q = copy.deepcopy(q) if deepcopy else q
        self.projector = copy.deepcopy(projector) if deepcopy else projector
        self.context_len = int(context_len)
        self.target_len = int(target_len)
        self.patch_size = int(patch_size)
        self.lc_min = int(lc_min)
        self.lc_max = int(lc_max)
        self.eval()
        for p in self.parameters():
            p.requires_grad_(False)

    def sha256(self) -> str:
        return module_pair_sha256(self.q, self.projector)

    def _target_input(self, data) -> dict:
        """Real EO frames kept; FUTURE WEATHER explicitly zeroed (doc 88 §3.1)."""
        cl, tl = self.context_len, self.target_len
        w = data["dynamic"][1].clone()
        w[:, cl:cl + tl] = 0.0
        return {"dynamic": [data["dynamic"][0], w], "dynamic_mask": data["dynamic_mask"],
                "static": data["static"], "landcover": data["landcover"]}

    @torch.no_grad()
    def encode_target(self, data) -> torch.Tensor:
        """z*_{t+H} = projector(frozen-q terminal-frame state), (B_patch, state_dim)."""
        cl, tl = self.context_len, self.target_len
        T = cl + tl
        tin = self._target_input(data)
        was = self.q.core.training
        self.q.core.eval()
        _, z_full = self.q.encode(tin, pred_start=T, preds_length=0)   # ALL frames visible
        if was:
            self.q.core.train()
        z_tok = z_full[:, cl + tl - 1]                                 # terminal frame == t+H
        return self.projector(z_tok)                                   # (B_patch, D)

    @torch.no_grad()
    def context_state(self, data) -> torch.Tensor:
        """z_t (context-only) — for the movement sanity metric only."""
        cl, tl = self.context_len, self.target_len
        x = data["dynamic"][0].clone(); x[:, cl:] = 0.0
        w = data["dynamic"][1].clone(); w[:, cl:] = 0.0
        m = data["dynamic_mask"][0].clone(); m[:, cl:] = 0.0
        cdata = {"dynamic": [x, w], "dynamic_mask": [m], "static": data["static"]}
        _, z_ctx = self.q.encode(cdata, pred_start=cl, preds_length=tl)
        return self.projector(z_ctx[:, cl - 1])

    @torch.no_grad()
    def patch_mask(self, data) -> torch.Tensor:
        """Valid target patches STRICTLY consistent with ContextFormer token visibility.

        The vendored ContextFormer (models/encoders/contextformer_official.py:471-478) masks
        a 4x4 image token to `mask_token` iff `mask_patches.max(-1) > 0`, i.e. if ANY pixel in
        the patch has dynamic_mask > 0. So the terminal-frame token carries a REAL future
        observation ONLY when the whole 4x4 patch is cloud-free. A patch is therefore a valid
        future-state supervision target iff:
          (a) NO pixel in the 4x4 patch is cloud-masked (max over patch of mask == 0), AND
          (b) it contains >= 1 vegetation pixel (land-cover in [lc_min, lc_max]).
        (The old 'any clear vegetation pixel' rule was inconsistent with this visibility.)"""
        cl, tl, ps = self.context_len, self.target_len, self.patch_size
        term = cl + tl - 1
        mask_raw = data["dynamic_mask"][0][:, term]                    # (B,1,H,W) raw cloud mask
        patch_has_cloud = F.max_pool2d((mask_raw > 0).float(), ps) > 0  # mirrors CF max(-1)>0
        fully_clear = ~patch_has_cloud                                 # (B,1,H',W') bool
        lc = data["landcover"]
        has_veg = F.max_pool2d(((lc >= self.lc_min) & (lc <= self.lc_max)).float(), ps) > 0
        valid = fully_clear & has_veg                                  # (B,1,H',W')
        B, _, hp, wp = valid.shape
        return valid.reshape(B, hp * wp).reshape(-1)                   # (B*P,) cube-major bool


class _Sanity:
    """Bounded running collection of z*/z_t patches for the doc-88 target sanity report."""

    def __init__(self, cap: int = 20000):
        self.cap = cap
        self.zs, self.zt = [], []
        self.n_nan = 0
        self.n_patches = 0

    def add(self, z_star_fp32: torch.Tensor, z_t_fp32: torch.Tensor):
        self.n_nan += int(torch.isnan(z_star_fp32).sum().item())
        self.n_patches += z_star_fp32.shape[0]
        room = self.cap - sum(t.shape[0] for t in self.zs)
        if room > 0:
            k = min(room, z_star_fp32.shape[0])
            self.zs.append(z_star_fp32[:k].cpu())
            self.zt.append(z_t_fp32[:k].cpu())

    def report(self) -> dict:
        if not self.zs:
            return {"n_patches": self.n_patches, "n_nan": self.n_nan}
        zs = torch.cat(self.zs, 0).float()
        zt = torch.cat(self.zt, 0).float()
        var = zs.var(dim=0, unbiased=False)                            # per-dim variance
        # effective rank = participation ratio of covariance eigenvalues
        x = zs - zs.mean(0, keepdim=True)
        cov = (x.T @ x) / max(x.shape[0] - 1, 1)
        ev = torch.linalg.eigvalsh(cov).clamp(min=0)
        eff_rank = float((ev.sum() ** 2 / (ev.pow(2).sum() + 1e-12)).item())
        # movement = how far the future state moved from the context state (normalized cos)
        zsn = F.layer_norm(zs, (zs.shape[-1],))
        ztn = F.layer_norm(zt, (zt.shape[-1],))
        movement_cos = float((1.0 - F.cosine_similarity(zsn, ztn, dim=-1)).mean().item())
        movement_l2 = float((zs - zt).norm(dim=-1).mean().item())
        return {
            "n_patches": int(self.n_patches),
            "n_nan": int(self.n_nan),
            "sanity_sample_patches": int(zs.shape[0]),
            "mean_dim_variance": float(var.mean().item()),
            "min_dim_variance": float(var.min().item()),
            "n_zero_var_dims": int((var < 1e-8).sum().item()),
            "effective_rank": eff_rank,
            "state_dim": int(zs.shape[-1]),
            "movement_cos_from_context": movement_cos,
            "movement_l2_from_context": movement_l2,
        }


@torch.no_grad()
def build_cache(dataset, encoder: FrozenFutureStateEncoder, device, *, root, split: str,
                student_init_path: str, student_init_sha256: str,
                per_gpu_batch: int = 2, num_workers: int = 0, limit: int = 0,
                sanity_cap: int = 20000, min_coverage: float = 0.0) -> dict:
    """Build a future-state cache over `dataset`. Returns the full blob (targets/masks/
    provenance/sanity). NO shuffling: cube order is deterministic and irrelevant (keyed
    by relative path). Fail-closed: if valid-patch coverage < `min_coverage`, RAISE (do NOT
    silently proceed / relax the mask rule)."""
    import hashlib
    loader = DataLoader(dataset, batch_size=per_gpu_batch, shuffle=False,
                        num_workers=num_workers, collate_fn=collate_with_ids, drop_last=False)
    targets, masks = {}, {}
    dup = []
    sanity = _Sanity(cap=sanity_cap)
    valid_patches = total_patches = 0
    for batch in loader:
        data = to_device_with_ids(batch, device)
        z_star = encoder.encode_target(data)          # (B*P, D)
        pmask = encoder.patch_mask(data)              # (B*P,)
        z_t = encoder.context_state(data)             # (B*P, D)
        B = data["dynamic"][0].shape[0]
        P = z_star.shape[0] // B
        for b in range(B):
            relp = relpath_of(batch["filepath"][b], root)
            zs_b = z_star[b * P:(b + 1) * P].float()
            zt_b = z_t[b * P:(b + 1) * P].float()
            mk_b = pmask[b * P:(b + 1) * P]
            if relp in targets:                       # duplicate filepath check (doc 88)
                dup.append(relp)
                continue
            targets[relp] = zs_b.to(torch.float16).cpu()
            masks[relp] = mk_b.to(torch.bool).cpu()
            valid_patches += int(mk_b.sum().item()); total_patches += int(mk_b.numel())
            sanity.add(zs_b, zt_b)
        if limit and len(targets) >= limit:
            break

    coverage = valid_patches / max(total_patches, 1)
    # mask SHA over relpath-sorted bool masks (identity of the supervision footprint)
    mh = hashlib.sha256()
    for relp in sorted(masks):
        mh.update(relp.encode()); mh.update(masks[relp].numpy().tobytes())
    mask_sha256 = mh.hexdigest()

    filepaths = [str(p) for p in dataset.filepaths]
    provenance = {
        "schema": CACHE_SCHEMA,
        "split": split,
        "driver_protocol": "full24",
        "field_order": FULL24_FIELD_ORDER,            # aggregation-major [8 mean|8 min|8 max]
        "horizon_h": int(encoder.target_len),         # 20 (terminal, only cached horizon)
        "context_len": int(encoder.context_len),
        "target_len": int(encoder.target_len),
        "patch_size": int(encoder.patch_size),
        "state_dim": int(next(iter(targets.values())).shape[-1]) if targets else None,
        "patches_per_cube": int(next(iter(targets.values())).shape[0]) if targets else None,
        "patch_mask_rule": "fully_clear(no dynamic_mask>0 in 4x4) AND >=1 vegetation pixel (CF-consistent)",
        "valid_patches": int(valid_patches),
        "total_patches": int(total_patches),
        "coverage": float(coverage),
        "mask_sha256": mask_sha256,
        "future_weather_zeroed": True,
        "target_uses_real_future_eo": True,
        "q_projector_sha256": encoder.sha256(),
        "student_init_path": str(student_init_path),
        "student_init_sha256": student_init_sha256,
        "data_root": str(root),
        "n_cubes": len(targets),
        "n_cubes_in_dataset": len(dataset),
        "data_manifest_sha256": data_manifest_sha256(filepaths, root),
        "lc_min": int(encoder.lc_min), "lc_max": int(encoder.lc_max),
        "built_by": "scripts/build_future_state_cache.py",
    }
    provenance["config_sha256"] = canonical_json_sha256({
        k: provenance[k] for k in ("schema", "driver_protocol", "field_order", "horizon_h",
                                   "context_len", "target_len", "patch_size", "state_dim",
                                   "patch_mask_rule", "future_weather_zeroed", "q_projector_sha256")
    })
    if min_coverage > 0.0 and coverage < min_coverage:
        raise RuntimeError(
            f"[{split}] future-state valid-patch coverage {coverage:.4f} < min_coverage {min_coverage} "
            f"({valid_patches}/{total_patches}). STOP — do NOT relax the CF-consistent mask rule. "
            f"Investigate cloud density at the terminal horizon / horizon choice.")
    return {"provenance": provenance, "targets": targets, "masks": masks,
            "sanity": sanity.report(), "dup": dup}


def sidecar(blob: dict) -> dict:
    """Tensor-free JSON view (provenance + sanity + dup) for quick inspection / SHA."""
    return {"provenance": blob["provenance"], "sanity": blob["sanity"],
            "n_dup": len(blob["dup"]), "dup_examples": blob["dup"][:5]}


class FutureStateCache:
    """Read-only loader. `gather` returns per-batch (z*, patch_mask) by relative path.

    Uses torch.load(mmap=True) so that under N-process DDP the OS shares ONE page-cached
    copy of the (potentially ~12GB) cache file instead of N private RAM copies. If mmap is
    unavailable AND the file exceeds `fail_closed_gb`, we REFUSE to load (fail-closed) rather
    than silently let every rank materialise a full copy (doc-88 §B memory risk)."""

    def __init__(self, path: str, root, *, mmap: bool = True, fail_closed_gb: float = None,
                 verbose: bool = True):
        import os
        from train.terrastate_v2_common import rss_bytes
        size = os.path.getsize(path)
        rss0 = rss_bytes()
        mmap_ok = False
        blob = None
        if mmap:
            try:
                blob = torch.load(path, map_location="cpu", weights_only=False, mmap=True)
                mmap_ok = True
            except (TypeError, RuntimeError, ValueError) as e:
                if verbose:
                    print(f"[FutureStateCache] mmap load failed ({type(e).__name__}: {str(e)[:80]}); "
                          f"falling back to full load", flush=True)
        if blob is None:
            blob = torch.load(path, map_location="cpu", weights_only=False)
        rss1 = rss_bytes()
        if verbose:
            print(f"[FutureStateCache] {path} size={size/1e9:.3f}GB mmap={'OK' if mmap_ok else 'FALLBACK'} "
                  f"rss {rss0/1e9:.2f}->{rss1/1e9:.2f}GB (Δ{(rss1-rss0)/1e9:+.2f}GB, CPU RAM not GPU)", flush=True)
        if (not mmap_ok) and fail_closed_gb is not None and size > fail_closed_gb * 1e9:
            raise RuntimeError(
                f"future-state cache {size/1e9:.1f}GB exceeds fail-closed threshold {fail_closed_gb}GB "
                f"and mmap is unavailable: refusing to load a full per-rank copy (would OOM under DDP). "
                f"Use a torch build with mmap support, lower --cache-fail-closed-gb only if you understand "
                f"the per-rank RAM cost, or shard the cache.")
        assert blob["provenance"]["schema"] == CACHE_SCHEMA, "unknown cache schema"
        self.path = str(path)
        self.root = root
        self.mmap_ok = mmap_ok
        self.size_bytes = size
        self.provenance = blob["provenance"]
        self.targets = blob["targets"]
        self.masks = blob["masks"]
        self.sanity = blob.get("sanity", {})

    def __len__(self) -> int:
        return len(self.targets)

    def verify(self, *, q_projector_sha256: str, field_order, horizon_h: int) -> None:
        """Fail-closed identity checks against the trainer's INITIAL frozen q/projector."""
        p = self.provenance
        assert p["q_projector_sha256"] == q_projector_sha256, (
            f"cache q/projector SHA mismatch: cache={p['q_projector_sha256'][:12]} "
            f"trainer={q_projector_sha256[:12]} (frozen target encoder differs)")
        assert list(p["field_order"]) == list(field_order), "cache full24 field order mismatch"
        assert int(p["horizon_h"]) == int(horizon_h), "cache horizon_h mismatch"
        for relp, t in self.targets.items():
            if torch.isnan(t.float()).any():
                raise AssertionError(f"cache target has NaN: {relp}")
            break

    def has(self, filepath: str) -> bool:
        return relpath_of(filepath, self.root) in self.targets

    def gather(self, filepaths, device):
        """(B*P, D) fp32 targets and (B*P,) bool masks, in the SAME cube order as
        `filepaths` (so it aligns with the model's cube-major B_patch ordering)."""
        zs, mk, missing = [], [], []
        for fp in filepaths:
            relp = relpath_of(fp, self.root)
            t = self.targets.get(relp)
            if t is None:
                missing.append(relp)
                continue
            zs.append(t)
            mk.append(self.masks[relp])
        assert not missing, f"future-state cache missing {len(missing)} cubes e.g. {missing[:3]}"
        z = torch.cat([t.to(device=device, dtype=torch.float32) for t in zs], dim=0)
        m = torch.cat([t.to(device=device) for t in mk], dim=0)
        return z, m
