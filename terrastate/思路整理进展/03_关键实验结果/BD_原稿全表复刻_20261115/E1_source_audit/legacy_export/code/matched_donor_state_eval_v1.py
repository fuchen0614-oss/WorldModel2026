#!/usr/bin/env python3
"""C1 seed42 matched-donor 10->20 state intervention, isolated from repo code."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import xarray as xr


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def rel(path, root):
    return str(Path(path).relative_to(Path(root))).replace("\\", "/")


def load_model(repo, ckpt, device):
    import sys
    sys.path.insert(0, str(repo))
    from eval.eval_terrastate_candidate_c_q4 import load_candidate_c_strict
    return load_candidate_c_strict(str(ckpt), device=device)


def load_dataset(repo, root):
    import sys
    sys.path.insert(0, str(repo))
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    return GreenEarthNetContextformerDataset(root, dl_cloudmask=True)


def collate(items):
    from train.terrastate_v2_common import collate_with_ids
    return collate_with_ids(items)


def move(batch, device):
    from train.terrastate_v2_common import to_device_with_ids
    return to_device_with_ids(batch, device)


def make_donor_manifest(ds, root, model, out):
    """Freeze same-season adjacent pairing without looking at model outcomes."""
    rows = []
    for i, path in enumerate(ds.filepaths):
        relative = rel(path, root)
        rows.append({"dataset_index": i, "cube": Path(path).stem,
                     "relative_path": relative, "season": str(Path(relative).parts[0]),
                     "history_mean": "", "history_std": "", "history_last_mean": "",
                     "history_feature_valid": "not_used"})
    groups = {}
    for r in rows: groups.setdefault(r["season"], []).append(r)
    for season, group in groups.items():
        group.sort(key=lambda r: r["relative_path"])
        for j, r in enumerate(group):
            donor = group[(j + 1) % len(group)]
            r["donor_index"] = donor["dataset_index"]
            r["donor_cube"] = donor["cube"]
    rows.sort(key=lambda r: int(r["dataset_index"]))
    write_csv(out, rows, ["dataset_index", "cube", "relative_path", "season",
                          "history_mean", "history_std", "history_last_mean",
                          "history_feature_valid", "donor_index", "donor_cube"])
    return {int(r["dataset_index"]): r for r in rows}


@torch.no_grad()
def core_batch(model, items, device):
    data = move(collate(items), device)
    pred, prior, _res, z_t, geo, u_future = model.forecast(data, want_parts=True)
    cl, tl = int(model.context_len), int(model.target_len)
    target = data["dynamic"][0][:, cl:cl + tl, 0]
    cloud = data["dynamic_mask"][0][:, cl:cl + tl] < 1.0
    lc = data["landcover"]
    valid = (cloud & ((lc >= model.lc_min) & (lc <= model.lc_max)).unsqueeze(1))[:, :, 0].float()
    z_a10 = model.segment_state(z_t, u_future, geo, (10,))
    z_b10 = model.segment_state(z_t, u_future, geo, (5, 5))
    B, H, W = pred.shape[0], pred.shape[-2], pred.shape[-1]
    suffix = {"D20": [pred[:, 10 + k, 0] for k in range(10)], "A": [], "B": [], "donor": []}
    for k in range(1, 11):
        h = 10 + k
        z_a = model.segment_state(z_a10, u_future[:, 10:10 + k], geo, (k,))
        z_b = model.segment_state(z_b10, u_future[:, 10:10 + k], geo, (k,))
        suffix["A"].append((prior[:, h - 1] + model.alpha * model._decode_state(z_a, B, H, W))[:, 0])
        suffix["B"].append((prior[:, h - 1] + model.alpha * model._decode_state(z_b, B, H, W))[:, 0])
    return {"data": data, "prior": prior, "z_a10": z_a10, "z_b10": z_b10,
            "u_future": u_future, "target": target, "valid": valid,
            "pred": pred[:, :, 0], "suffix": suffix, "cl": cl, "tl": tl}


@torch.no_grad()
def donor_suffix(model, receiver, donor, device):
    d = core(model, donor, device)
    r = receiver
    prior, u, donor_state = r["prior"], r["u_future"], d["z_a10"]
    out = []
    for k in range(1, 11):
        h = 10 + k
        z = model.segment_state(donor_state, u[:, 10:10 + k],
                                r["data"]["static"][0][:, :3].new_zeros((1, donor_state.shape[0] // r["data"]["static"][0].shape[0], 2)), (k,)) if False else None
        # Use the receiver's geographic conditioning. Geo is recovered from a
        # one-call receiver field stored below; this branch is replaced in main.
        out.append(z)
    return out


def state_l1(a, b, B):
    aa = a.reshape(B, -1, a.shape[-1]).float()
    bb = b.reshape(B, -1, b.shape[-1]).float()
    return (aa - bb).abs().mean(dim=(1, 2)).detach().cpu().numpy()


def row_stats(pred, target, valid):
    m = valid > 0.5; vals = (pred - target)[m].detach(); n = int(vals.numel())
    return {"n_valid": n, "sse": float((vals ** 2).sum()) if n else float("nan"),
            "target_sum": float(target[m].detach().sum()) if n else float("nan"),
            "target_sum_sq": float((target[m].detach() ** 2).sum()) if n else float("nan"),
            "sum_abs": float(vals.abs().sum()) if n else float("nan")}


def geo_group(cube):
    name = Path(cube).name
    fields = name.split("_")
    if len(fields) >= 5 and fields[0] == "minicube":
        return fields[2]
    return Path(cube).parts[0] if Path(cube).parts else "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True); ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--ckpt", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--device", default="cuda:0"); ap.add_argument("--max-cubes", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=4)
    args = ap.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    for d in ("tables", "plot_data", "manifests", "logs"): (args.out / d).mkdir(exist_ok=True)
    device = torch.device(args.device); model, _ck, ck_meta = load_model(args.repo, args.ckpt, device)
    ds = load_dataset(args.repo, args.data_root)
    source_manifest = args.manifest
    donor_path = args.out / "manifests" / "matched_donor_manifest.csv"
    source_rows = list(csv.DictReader(source_manifest.open(newline="", encoding="utf-8")))
    donor_map = {int(r["dataset_index"]): r for r in source_rows}
    if len(donor_map) != len(source_rows):
        raise SystemExit("duplicate receiver dataset_index in matched manifest")
    if not source_rows:
        raise SystemExit("matched manifest is empty")
    # Verify that the frozen indices refer to the current dataset ordering.
    for r in source_rows:
        idx = int(r["dataset_index"])
        expected = str(Path(args.data_root / r["relative_path"]).resolve())
        actual = str(Path(ds.filepaths[idx]).resolve())
        if expected != actual:
            raise SystemExit(f"dataset index/path mismatch at {idx}: {actual} != {expected}")
    write_csv(donor_path, source_rows, list(source_rows[0]))
    all_indices = sorted(donor_map)
    indices = all_indices if not args.max_cubes else all_indices[: args.max_cubes]
    rows = []; state_rows = []; start = time.time()
    for start_i in range(0, len(indices), args.batch_size):
        batch_indices = indices[start_i:start_i + args.batch_size]
        receiver_items = [ds[i] for i in batch_indices]
        donor_indices = [int(donor_map[i]["donor_index"]) for i in batch_indices]
        donor_items = [ds[i] for i in donor_indices]
        receiver = core_batch(model, receiver_items, device)
        donor = core_batch(model, donor_items, device)
        B, H, W = len(batch_indices), receiver["pred"].shape[-2], receiver["pred"].shape[-1]
        geo_encoded = model.geo_enc(receiver["data"]["static"][0][:, :3])
        donor_suffix = []
        for k in range(1, 11):
            h = 10 + k
            z = model.segment_state(donor["z_a10"], receiver["u_future"][:, 10:10 + k], geo_encoded, (k,))
            donor_suffix.append((receiver["prior"][:, h - 1] + model.alpha * model._decode_state(z, B, H, W))[:, 0])
        receiver["suffix"]["donor"] = donor_suffix
        ab_l1 = state_l1(receiver["z_a10"], receiver["z_b10"], B)
        ad_l1 = state_l1(receiver["z_a10"], donor["z_a10"], B)
        for b, idx in enumerate(batch_indices):
            for k in range(10):
                target = receiver["target"][b, 10 + k]; valid = receiver["valid"][b, 10 + k] > 0.5
                stats = {name: row_stats(receiver["suffix"][name][k][b], target, valid)
                         for name in ("D20", "A", "B", "donor")}
                base = {"dataset_index": idx, "cube": receiver_items[b]["cubename"], "geo_group": geo_group(receiver_items[b]["cubename"]), "season": donor_map[idx]["season"],
                        "donor_index": donor_indices[b], "donor_cube": donor_map[idx]["donor_cube"],
                        "suffix_horizon": k + 1, "state_A_B_l1": float(ab_l1[b]), "state_A_donor_l1": float(ad_l1[b]),
                        "n_valid": stats["D20"]["n_valid"], "target_sum": stats["D20"]["target_sum"],
                        "target_sum_sq": stats["D20"]["target_sum_sq"]}
                for name in ("D20", "A", "B", "donor"):
                    base[f"{name}_sse"] = stats[name]["sse"]; base[f"{name}_sum_abs"] = stats[name]["sum_abs"]
                for name_a, name_b, label in (("A", "B", "A_B"), ("A", "D20", "A_D20"), ("B", "D20", "B_D20"), ("donor", "A", "donor_A")):
                    diff = (receiver["suffix"][name_a][k][b] - receiver["suffix"][name_b][k][b])[valid]
                    base[f"{label}_output_mae"] = float(diff.abs().mean().detach().cpu()) if diff.numel() else float("nan")
                rows.append(base)
            state_rows.append({"dataset_index": idx, "cube": receiver_items[b]["cubename"], "geo_group": geo_group(receiver_items[b]["cubename"]), "donor_index": donor_indices[b],
                               "state_A_B_l1": float(ab_l1[b]), "state_A_donor_l1": float(ad_l1[b])})
        n_done = start_i + len(batch_indices)
        if n_done == len(batch_indices) or n_done % 25 == 0: print(f"processed {n_done}/{len(indices)} elapsed={time.time()-start:.1f}s", flush=True)
    fields = list(rows[0]) if rows else []
    write_csv(args.out / "plot_data/formal_common_suffix_per_cube_horizon.csv", rows, fields)
    write_csv(args.out / "plot_data/formal_state_intervention_per_cube.csv", state_rows, list(state_rows[0]) if state_rows else [])
    write_json(args.out / "manifests/formal_run_summary.json", {"status": "COMPLETE" if len(indices) == len(all_indices) else "SMOKE",
              "n_cubes": len(indices), "dataset_total": len(ds), "eligible_manifest_total": len(all_indices), "window": "10->20", "split": args.data_root.name,
              "checkpoint": ck_meta, "donor_rule": "A14B frozen same-year-month matched donor; standardized first-10 observed NDVI summaries plus 0.5*Hellinger land-cover distance; no future target or model outcome used; reuse cap 1",
              "source_manifest": str(source_manifest),
              "elapsed_seconds": time.time() - start, "source_data_root": str(args.data_root)})


if __name__ == "__main__": main()
