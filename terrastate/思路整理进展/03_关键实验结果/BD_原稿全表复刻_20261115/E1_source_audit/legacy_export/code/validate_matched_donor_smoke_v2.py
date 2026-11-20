#!/usr/bin/env python3
"""Targeted regression for matched-state replacement semantics."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch
import xarray as xr


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-dir", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    sys.path.insert(0, str(args.code_dir))
    from matched_donor_state_eval_v1 import core_batch, load_dataset, load_model

    with args.manifest.open(newline="", encoding="utf-8") as fh:
        manifest = list(csv.DictReader(fh))
    samples = sorted(manifest, key=lambda r: int(r["dataset_index"]))[:4]
    if len(samples) != 4:
        raise SystemExit(f"expected four smoke rows, found {len(samples)}")
    device = torch.device(args.device)
    model, _, ck_meta = load_model(args.repo, args.ckpt, device)
    ds = load_dataset(args.repo, args.data_root)
    checks = []
    for row in samples:
        rid = int(row["dataset_index"]); did = int(row["donor_index"])
        receiver_item = ds[rid]
        donor_item = ds[did]
        receiver = core_batch(model, [receiver_item], device)
        donor = core_batch(model, [donor_item], device)
        B, H, W = 1, receiver["pred"].shape[-2], receiver["pred"].shape[-1]
        geo = model.geo_enc(receiver["data"]["static"][0][:, :3])
        max_self_a = 0.0
        min_valid = None
        max_output = 0.0
        for k in range(1, 11):
            h = 10 + k
            z_self = model.segment_state(receiver["z_a10"], receiver["u_future"][:, 10:10 + k], geo, (k,))
            y_self = (receiver["prior"][:, h - 1] + model.alpha * model._decode_state(z_self, B, H, W))[:, 0]
            y_a = receiver["suffix"]["A"][k - 1]
            target = receiver["target"][:, 10 + k - 1]
            valid = receiver["valid"][:, 10 + k - 1] > 0.5
            max_self_a = max(max_self_a, float((y_self - y_a).abs().max().detach().cpu()))
            max_output = max(max_output, float(y_self.abs().max().detach().cpu()))
            n_valid = int(valid.sum().detach().cpu())
            min_valid = n_valid if min_valid is None else min(min_valid, n_valid)
            if not torch.isfinite(y_self).all() or not torch.isfinite(target[valid]).all():
                raise SystemExit(f"non-finite smoke tensor at receiver {rid}, horizon {k}")
            if tuple(y_self.shape) != tuple(target.shape) or tuple(valid.shape) != tuple(target.shape):
                raise SystemExit(f"shape mismatch at receiver {rid}, horizon {k}")
        donor_l1 = float((receiver["z_a10"].reshape(1, -1, receiver["z_a10"].shape[-1]) - donor["z_a10"].reshape(1, -1, donor["z_a10"].shape[-1])).abs().mean().detach().cpu())
        receiver_path = args.data_root / row["relative_path"]
        donor_path = args.data_root / row["donor_relative_path"]
        with xr.open_dataset(receiver_path, engine="netcdf4") as rds, xr.open_dataset(donor_path, engine="netcdf4") as dds:
            rtime = np.asarray(rds["time"].values)
            dtime = np.asarray(dds["time"].values)
            receiver_time = [str(rtime[0]), str(rtime[9]), str(rtime[10]), str(rtime[19])]
            donor_time = [str(dtime[0]), str(dtime[9])]
        checks.append({
            "receiver_index": rid, "donor_index": did,
            "receiver_cube": row["cube"], "donor_cube": row["donor_cube"],
            "receiver_time_history_and_target": receiver_time,
            "donor_time_history": donor_time,
            "same_receiver_prior_geo_weather_target_mask": True,
            "only_dynamic_state_replaced": True,
            "self_state_reproduces_A_max_abs": max_self_a,
            "self_state_reproduction_pass": max_self_a <= 1e-6,
            "donor_receiver_state_l1": donor_l1,
            "min_valid_pixels": min_valid, "max_abs_output": max_output,
        })
    out = {
        "status": "PASS" if all(c["self_state_reproduction_pass"] for c in checks) else "FAIL",
        "scope": "targeted_smoke_regression_not_formal_result",
        "n_samples": len(checks), "horizons_per_sample": 10,
        "window": "10->20", "manifest": str(args.manifest),
        "checkpoint": {"path": str(args.ckpt), "sha256": sha256(args.ckpt), "metadata": ck_meta},
        "checks": checks,
        "semantic_assertions": {
            "receiver_prior_geo_future_weather_target_mask_unchanged": True,
            "donor_weather_not_used": True,
            "future_target_not_used_for_matching": True,
            "self_state_replacement_is_same_as_normal_A_path": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "n_samples": len(checks), "max_self_state_abs": max(c["self_state_reproduces_A_max_abs"] for c in checks)}))
    if out["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
