"""Candidate C CPU-only 测试夹具：无 GPU、无真实数据、无 xarray、无网络盘遍历。

所有夹具都是确定性的（固定 generator 种子），因此"两次运行逐位相同"这类断言
本身是可检验的，而不是靠运气。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import torch
from torch.utils.data import Dataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.terrastate_candidate_c import TerraStateCandidateC  # noqa: E402

SYNTH_H = 32          # 可被 patch_size 整除
CONTRACT_CFG = {
    "state_dim": 256, "cond_dim": 256, "dw": 128, "dg": 64, "dh": 64,
    "lc_min": 10, "lc_max": 40, "freeze_b0": False,
    "partitions": [[5, 5], [7, 8], [10, 10]],
    "heldout_partitions": [[3, 7], [6, 4], [4, 11], [8, 12], [2, 18]],
}


class SyntheticCubeDataset(Dataset):
    """与 GreenEarthNet dict schema 完全一致的确定性内存 cube（含 filepath/cubename）。"""

    def __init__(self, n, root, H=SYNTH_H, W=SYNTH_H, T=30, seed=0, all_cloudy=False):
        self.filepaths = [f"{root}/synth_{i}.nc" for i in range(n)]
        self.root, self.H, self.W, self.T = root, H, W, T
        self.seed, self.all_cloudy = seed, all_cloudy

    def __len__(self):
        return len(self.filepaths)

    def __getitem__(self, i):
        g = torch.Generator().manual_seed(self.seed * 100003 + i)
        dyn = torch.rand(self.T, 5, self.H, self.W, generator=g)
        wx = torch.randn(self.T, 24, generator=g)
        if self.all_cloudy:
            mask = torch.ones(self.T, 1, self.H, self.W) * 4.0       # 全云 -> 零有效像素
        else:
            mask = (torch.rand(self.T, 1, self.H, self.W, generator=g) < 0.03).float() * 4.0
        static = torch.randn(5, self.H, self.W, generator=g)
        lc = torch.randint(0, 50, (1, self.H, self.W), generator=g).float()
        return {"dynamic": [dyn, wx], "dynamic_mask": [mask], "static": [static],
                "static_mask": [], "landcover": lc,
                "filepath": self.filepaths[i], "cubename": f"synth_{i}"}


def build_model(factual_path="recursive", seed=0, **cfg_over):
    """确定性构建（未 warm-start 的随机权重）。测试 warm-start 的用例自己去装父权重。"""
    torch.manual_seed(seed)
    hp = contextformer6m_hparams(pvt_pretrained=False)
    cfg = dict(CONTRACT_CFG)
    cfg["factual_path"] = factual_path
    cfg.update(cfg_over)
    return TerraStateCandidateC(hp, contract_cfg=cfg)


def one_batch(n=2, seed=0, all_cloudy=False, dev=None):
    from train.terrastate_v2_common import collate_with_ids, to_device_with_ids
    ds = SyntheticCubeDataset(n, "/tmp/synth", seed=seed, all_cloudy=all_cloudy)
    batch = collate_with_ids([ds[i] for i in range(len(ds))])
    return to_device_with_ids(batch, dev or torch.device("cpu"))


def forecast_parts(model, data):
    """(pred, prior, residual, z_t, geo, u_future, B, H, W) 一把取齐。"""
    pred, prior, residual, z_t, geo, u_future = model.forecast(data, want_parts=True)
    B, H, W = pred.shape[0], pred.shape[-2], pred.shape[-1]
    return pred, prior, residual, z_t, geo, u_future, B, H, W


def write_val_split_manifest(path, ids_dev, ids_locked):
    """最小可用的 split manifest（结构与冻结件同形），供 trainer 的选择器测试使用。"""
    blob = {"schema": "candidate_c_eo_split_manifest_v1_testfixture",
            "is_test_fixture": True,
            "splits": {"val_dev": {"n": len(ids_dev), "ids": list(ids_dev)},
                       "val_locked": {"n": len(ids_locked), "ids": list(ids_locked)}}}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(blob, f, ensure_ascii=False, sort_keys=True, indent=1)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, p)
    return p


class Recorder:
    """测试结果记录器：机器可读报告 + 人可读逐行输出。"""

    def __init__(self, name):
        self.name, self.rows = name, []

    def check(self, test_id, title, ok, detail="", fatal=True):
        self.rows.append({"id": test_id, "title": title, "passed": bool(ok),
                          "fatal": bool(fatal), "detail": str(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {test_id} {title}"
              + (f" :: {detail}" if detail else ""), flush=True)
        return bool(ok)

    @property
    def n_failed(self):
        return sum(1 for r in self.rows if not r["passed"])

    @property
    def n_fatal_failed(self):
        return sum(1 for r in self.rows if not r["passed"] and r["fatal"])

    def report(self):
        return {"suite": self.name, "n_checks": len(self.rows),
                "n_passed": sum(1 for r in self.rows if r["passed"]),
                "n_failed": self.n_failed, "n_fatal_failed": self.n_fatal_failed,
                "verdict": "PASS" if self.n_fatal_failed == 0 else "FAIL",
                "checks": self.rows}
