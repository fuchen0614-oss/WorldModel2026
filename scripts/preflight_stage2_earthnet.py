#!/usr/bin/env python
"""Validate real EarthNet data and checkpoints before a Stage2 server run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    EarthNet2021Dataset,
    _build_driver_features,
    _discover_npz_files,
    _extract_elevation,
    _extract_meso_features,
    _load_external_drivers,
    _parse_start_date,
    _select_required_array,
    _to_tchw,
)
from train.train_stage2_earthnet import create_stage2_model


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _record_issue(issues: List[dict], path: Path, message: str) -> None:
    if len(issues) < 50:
        issues.append({"file": str(path), "error": message})


def _scan_data(
    config: dict,
    max_files: int,
) -> Dict[str, Any]:
    data_cfg = EarthNet2021Config.from_config(
        config["data"],
        split=config["data"].get("split", "train"),
    )
    all_files = _discover_npz_files(data_cfg)
    if not all_files:
        raise FileNotFoundError(
            f"No EarthNet files found under {data_cfg.root} for split={data_cfg.split}"
        )
    files = all_files if max_files <= 0 else all_files[:max_files]
    dim = data_cfg.driver_spec.dim
    valid_counts = np.zeros(dim, dtype=np.int64)
    expected_per_feature = len(files) * data_cfg.target_frames
    geo_valid_pixels = 0
    geo_total_pixels = 0
    sidecars_found = 0
    date_failures = 0
    zero_geo_files = 0
    issues: List[dict] = []
    issue_count = 0
    high_shapes: Dict[str, int] = {}
    meso_shapes: Dict[str, int] = {}

    for index, path in enumerate(files, start=1):
        try:
            with np.load(path, allow_pickle=True) as cube:
                arrays = {key: cube[key] for key in cube.files}
            high = _select_required_array(arrays, ("highresdynamic",), ndim=4)
            high_tchw = _to_tchw(high)
            high_shapes[str(tuple(high.shape))] = (
                high_shapes.get(str(tuple(high.shape)), 0) + 1
            )
            required_frames = data_cfg.context_frames + data_cfg.target_frames
            if high_tchw.shape[0] < required_frames and data_cfg.strict:
                raise ValueError(
                    f"highresdynamic has {high_tchw.shape[0]} frames; "
                    f"{required_frames} required"
                )
            if high_tchw.shape[1] < max(data_cfg.image_channels, 5):
                raise ValueError(
                    f"highresdynamic has only {high_tchw.shape[1]} channels"
                )

            start_date = _parse_start_date(path.name)
            if start_date is None:
                date_failures += 1
            meso = _extract_meso_features(
                arrays,
                crop_size=data_cfg.meso_crop_size,
            )
            if meso is not None:
                meso_shapes[str(tuple(meso.shape))] = (
                    meso_shapes.get(str(tuple(meso.shape)), 0) + 1
                )
            external, channel_map = _load_external_drivers(path, data_cfg)
            if external is not None:
                sidecars_found += 1
            drivers, driver_mask = _build_driver_features(
                meso=meso,
                num_targets=data_cfg.target_frames,
                context_frames=data_cfg.context_frames,
                frame_interval_days=data_cfg.frame_interval_days,
                meso_steps_per_image=data_cfg.meso_steps_per_image,
                driver_spec=data_cfg.driver_spec,
                start_date=start_date,
                external_drivers=external,
                external_channel_map=channel_map,
            )
            if not np.isfinite(drivers).all():
                raise ValueError("constructed D contains non-finite values")
            valid_counts += (driver_mask > 0).sum(axis=0)

            _, geo_mask = _extract_elevation(
                arrays,
                image_hw=high_tchw.shape[-2:],
                channel=data_cfg.elevation_channel,
                scale=data_cfg.elevation_scale,
            )
            valid_geo = int((geo_mask > 0).sum())
            geo_valid_pixels += valid_geo
            geo_total_pixels += int(geo_mask.size)
            if valid_geo == 0:
                zero_geo_files += 1
        except Exception as exc:
            issue_count += 1
            _record_issue(issues, path, f"{type(exc).__name__}: {exc}")
        if index % 1000 == 0:
            print(f"preflight scanned {index}/{len(files)}", flush=True)

    names = data_cfg.driver_spec.feature_names
    valid_fraction = valid_counts / max(expected_per_feature, 1)
    incomplete = [
        name
        for name, count in zip(names, valid_counts.tolist())
        if count < expected_per_feature
    ]
    fatal_reasons = []
    if issue_count:
        fatal_reasons.append(f"{issue_count} cube/sidecar parsing failures")
    if date_failures:
        fatal_reasons.append(f"{date_failures} cube names have no parseable start date")
    if bool(config["training"].get("require_all_driver_features", True)) and incomplete:
        fatal_reasons.append(f"incomplete D features: {incomplete}")
    if bool(config["training"].get("require_geo", True)) and zero_geo_files:
        fatal_reasons.append(f"{zero_geo_files} cubes have no valid elevation")
    if data_cfg.external_driver_required and sidecars_found != len(files):
        fatal_reasons.append(
            f"external sidecars found for {sidecars_found}/{len(files)} cubes"
        )

    return {
        "split": data_cfg.split,
        "total_files_in_split": len(all_files),
        "scanned_files": len(files),
        "scan_is_full_split": len(files) == len(all_files),
        "highresdynamic_shapes": high_shapes,
        "mesodynamic_time_channel_shapes": meso_shapes,
        "external_sidecars_found": sidecars_found,
        "date_parse_failures": date_failures,
        "zero_valid_elevation_files": zero_geo_files,
        "geo_valid_fraction": geo_valid_pixels / max(geo_total_pixels, 1),
        "driver_valid_count": dict(zip(names, valid_counts.tolist())),
        "driver_valid_fraction": dict(zip(names, valid_fraction.tolist())),
        "incomplete_driver_features": incomplete,
        "issue_count": issue_count,
        "sample_issues": issues,
        "fatal_reasons": fatal_reasons,
    }


def _check_model(config: dict, resume_from: Optional[str]) -> Dict[str, Any]:
    checkpoint_kind = "stage1.5"
    if resume_from:
        checkpoint_path = Path(resume_from)
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Stage2 resume checkpoint not found: {checkpoint_path}")
        config["model"]["encoder"]["from_checkpoint"] = None
        checkpoint_kind = "stage2_resume"
    model = create_stage2_model(config, torch.device("cpu"))
    if resume_from:
        checkpoint = torch.load(resume_from, map_location="cpu", weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    total = sum(parameter.numel() for parameter in model.parameters())
    trainable = sum(
        parameter.numel() for parameter in model.parameters()
        if parameter.requires_grad
    )
    return {
        "checkpoint_kind": checkpoint_kind,
        "checkpoint_compatible": True,
        "total_parameters": total,
        "trainable_parameters": trainable,
    }


def _check_stats(config: dict) -> Dict[str, Any]:
    path = Path(config["data"]["dgh_stats_path"])
    with path.open("r", encoding="utf-8") as handle:
        stats = json.load(handle)
    train_cfg = EarthNet2021Config.from_config(
        config["data"],
        split="train",
    )
    expected_names = train_cfg.driver_spec.feature_names
    errors = []
    if stats.get("fit_split") != "train":
        errors.append(f"fit_split={stats.get('fit_split')!r}, expected 'train'")
    if list(stats.get("feature_names", [])) != list(expected_names):
        errors.append("feature_names/order differs from the configured D layout")
    stats_files = int(stats.get("num_files", -1))
    expected_files = len(_discover_npz_files(train_cfg))
    if stats_files != expected_files:
        errors.append(
            f"stats num_files={stats_files}, train split contains {expected_files}"
        )
    expected_count = expected_files * int(config["data"].get("target_frames", 20))
    valid_count = list(stats.get("valid_count", []))
    if bool(config["training"].get("require_all_driver_features", True)):
        if len(valid_count) != len(expected_names) or any(
            int(count) != expected_count for count in valid_count
        ):
            errors.append(
                "stats valid_count does not prove complete D coverage over all "
                "train cubes and horizons"
            )
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "path": str(path),
        "fit_split": stats.get("fit_split"),
        "num_files": stats_files,
        "feature_names": stats.get("feature_names"),
        "complete_driver_coverage": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-root")
    parser.add_argument("--external-driver-root")
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--stage15-checkpoint")
    parser.add_argument("--resume-from")
    parser.add_argument("--split", default="train")
    parser.add_argument(
        "--max-files",
        type=int,
        default=64,
        help="Number of cubes to scan; 0 scans the complete selected split.",
    )
    parser.add_argument("--check-model", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    config = _load_yaml(args.config)
    config["data"]["split"] = args.split
    if args.data_root:
        config["data"]["root"] = args.data_root
    if args.external_driver_root:
        config["data"]["external_driver_root"] = args.external_driver_root
    if args.dgh_stats_path:
        config["data"]["dgh_stats_path"] = args.dgh_stats_path
    if args.stage15_checkpoint:
        config["model"]["encoder"]["from_checkpoint"] = args.stage15_checkpoint

    report: Dict[str, Any] = {
        "config": str(Path(args.config).resolve()),
        "data_root": config["data"]["root"],
        "external_driver_root": config["data"].get("external_driver_root"),
        "dgh_stats_path": config["data"].get("dgh_stats_path"),
    }
    fatal = []
    try:
        if bool(config["training"].get("require_dgh_stats", True)):
            if not config["data"].get("dgh_stats_path"):
                raise ValueError("formal training requires --dgh-stats-path")
        report["data"] = _scan_data(config, args.max_files)
        fatal.extend(report["data"]["fatal_reasons"])
        if config["data"].get("dgh_stats_path"):
            report["stats"] = _check_stats(config)
        # Exercise the final resize/collate-facing path once as well.
        dataset = EarthNet2021Dataset(
            EarthNet2021Config.from_config(config["data"], split=args.split)
        )
        sample = dataset[0]
        report["sample_shapes"] = {
            key: list(value.shape)
            for key, value in sample.items()
            if torch.is_tensor(value)
        }
    except Exception as exc:
        fatal.append(f"data preflight failed: {type(exc).__name__}: {exc}")

    if args.check_model:
        try:
            report["model"] = _check_model(config, args.resume_from)
        except Exception as exc:
            fatal.append(f"model preflight failed: {type(exc).__name__}: {exc}")

    report["ok"] = not fatal
    report["fatal_reasons"] = fatal
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    if fatal:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
