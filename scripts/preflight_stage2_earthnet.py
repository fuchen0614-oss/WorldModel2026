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
    _discover_npz_files,
    _load_external_drivers,
)
from data.earthnet_conditioning import (
    ConditioningStatsV2,
    EOBS_VARIABLES,
    FULL24_FEATURE_NAMES,
    is_stage2_v2_protocol,
)
from data.stage2_contract import validate_stage2_v2_batch
from train.train_stage2_earthnet import (
    create_stage2_model,
    load_stage2_model_state,
    require_stage15_initializer_if_formal,
)


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _min_driver_valid_fraction(config: dict) -> float:
    value = float(config.get("training", {}).get("min_driver_valid_fraction", 1.0))
    if not 0.0 <= value <= 1.0:
        raise ValueError("training.min_driver_valid_fraction must be in [0, 1]")
    return value


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
    if is_stage2_v2_protocol(data_cfg.stage2_protocol):
        return _scan_data_v2(config, data_cfg, all_files, max_files)
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
    dataset = EarthNet2021Dataset(data_cfg)

    for index, path in enumerate(files, start=1):
        try:
            sample = dataset[index - 1]
            context_shape = tuple(sample["x_context"].shape)
            high_shapes[str(context_shape)] = (
                high_shapes.get(str(context_shape), 0) + 1
            )
            driver_shape = tuple(sample["D"].shape)
            meso_shapes[str(driver_shape)] = (
                meso_shapes.get(str(driver_shape), 0) + 1
            )
            if sample.get("start_date") is None:
                date_failures += 1
            if data_cfg.external_driver_root:
                external, _ = _load_external_drivers(path, data_cfg)
            else:
                external = None
            if external is not None:
                sidecars_found += 1
            drivers = sample["D"].numpy()
            driver_mask = sample["D_mask"].numpy()
            if not np.isfinite(drivers).all():
                raise ValueError("constructed D contains non-finite values")
            valid_counts += (driver_mask > 0).sum(axis=0)

            geo_mask = sample["G_mask"].numpy()
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
    missing = [
        name
        for name, count in zip(names, valid_counts.tolist())
        if count == 0
    ]
    min_valid_fraction = _min_driver_valid_fraction(config)
    low_coverage = [
        name
        for name, fraction in zip(names, valid_fraction.tolist())
        if fraction < min_valid_fraction
    ]
    fatal_reasons = []
    if issue_count:
        fatal_reasons.append(f"{issue_count} cube/sidecar parsing failures")
    if date_failures:
        fatal_reasons.append(f"{date_failures} cube names have no parseable start date")
    if bool(config["training"].get("require_all_driver_features", True)):
        if missing:
            fatal_reasons.append(f"missing D features: {missing}")
        if low_coverage:
            fatal_reasons.append(
                "D feature valid_fraction below "
                f"{min_valid_fraction:.3f}: {low_coverage}"
            )
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
        "context_tensor_shapes": high_shapes,
        "driver_tensor_shapes": meso_shapes,
        "external_sidecars_found": sidecars_found,
        "date_parse_failures": date_failures,
        "zero_valid_elevation_files": zero_geo_files,
        "geo_valid_fraction": geo_valid_pixels / max(geo_total_pixels, 1),
        "driver_valid_count": dict(zip(names, valid_counts.tolist())),
        "driver_valid_fraction": dict(zip(names, valid_fraction.tolist())),
        "incomplete_driver_features": incomplete,
        "missing_driver_features": missing,
        "low_coverage_driver_features": low_coverage,
        "min_driver_valid_fraction": min_valid_fraction,
        "issue_count": issue_count,
        "sample_issues": issues,
        "fatal_reasons": fatal_reasons,
    }


def _scan_data_v2(
    config: dict,
    data_cfg: EarthNet2021Config,
    all_files: List[Path],
    max_files: int,
) -> Dict[str, Any]:
    """Scan formal path tensors without forwarding them into a model.

    The result intentionally reports both any-valid and all-five-day weather
    coverage.  The loader permits partial five-day windows (with a feature
    mask), while the latter number remains useful evidence about data quality.
    """

    files = all_files if max_files <= 0 else all_files[:max_files]
    expected_windows = len(files) * 30
    feature_valid_counts = np.zeros(len(FULL24_FEATURE_NAMES), dtype=np.int64)
    daily_valid_counts = np.zeros(len(EOBS_VARIABLES), dtype=np.int64)
    daily_all_five_counts = np.zeros(len(EOBS_VARIABLES), dtype=np.int64)
    geo_valid_pixels = 0
    geo_total_pixels = 0
    date_failures = 0
    zero_geo_files = 0
    issues: List[dict] = []
    issue_count = 0
    tensor_shapes: Dict[str, int] = {}
    dataset = EarthNet2021Dataset(data_cfg)

    for index, path in enumerate(files, start=1):
        try:
            sample = dataset[index - 1]
            tensor_batch = {
                name: value.unsqueeze(0)
                for name, value in sample.items()
                if torch.is_tensor(value)
            }
            validate_stage2_v2_batch(tensor_batch, require_targets=True)
            for name, value in sample.items():
                if torch.is_tensor(value):
                    shape = str(tuple(value.shape))
                    tensor_shapes[f"{name}:{shape}"] = tensor_shapes.get(
                        f"{name}:{shape}", 0
                    ) + 1
            if sample.get("start_date") is None:
                date_failures += 1
            feature_valid_counts += (sample["D_mask"].numpy() > 0).sum(axis=0)
            valid_day_count = sample["D_valid_day_count"].numpy()
            daily_valid_counts += (valid_day_count > 0).sum(axis=0)
            daily_all_five_counts += (valid_day_count == 5).sum(axis=0)
            geo_mask = sample["G_mask"].numpy()
            valid_geo = int((geo_mask > 0).sum())
            geo_valid_pixels += valid_geo
            geo_total_pixels += int(geo_mask.size)
            if valid_geo == 0:
                zero_geo_files += 1
        except Exception as exc:
            issue_count += 1
            _record_issue(issues, path, f"{type(exc).__name__}: {exc}")
        if index % 1000 == 0:
            print(f"v2 preflight scanned {index}/{len(files)}", flush=True)

    min_valid_fraction = _min_driver_valid_fraction(config)
    feature_valid_fraction = feature_valid_counts / max(expected_windows, 1)
    missing = [
        name
        for name, count in zip(FULL24_FEATURE_NAMES, feature_valid_counts.tolist())
        if count == 0
    ]
    low_coverage = [
        name
        for name, fraction in zip(
            FULL24_FEATURE_NAMES, feature_valid_fraction.tolist()
        )
        if fraction < min_valid_fraction
    ]
    fatal_reasons = []
    if issue_count:
        fatal_reasons.append(f"{issue_count} v2 cube parsing/contract failures")
    if date_failures:
        fatal_reasons.append(f"{date_failures} cubes have no parseable start date")
    if bool(config["training"].get("require_all_driver_features", True)):
        if missing:
            fatal_reasons.append(f"missing v2 D_path features: {missing}")
        if low_coverage:
            fatal_reasons.append(
                "v2 D_path feature valid_fraction below "
                f"{min_valid_fraction:.3f}: {low_coverage}"
            )
    if bool(config["training"].get("require_geo", True)) and zero_geo_files:
        fatal_reasons.append(f"{zero_geo_files} cubes have no valid cop_dem pixels")
    if data_cfg.use_train_holdout:
        fatal_reasons.append(
            "v2 data config has use_train_holdout=true; formal statistics and "
            "training must use the complete frozen manifest population"
        )
    if data_cfg.conditioning_stats and data_cfg.conditioning_stats.is_identity_smoke_stats:
        fatal_reasons.append(
            "v2 loader is using identity smoke statistics instead of train-only "
            "conditioning_stats_v2"
        )

    return {
        "split": data_cfg.split,
        "stage2_protocol": data_cfg.stage2_protocol,
        "total_files_in_split": len(all_files),
        "scanned_files": len(files),
        "scan_is_full_split": len(files) == len(all_files),
        "tensor_shapes": tensor_shapes,
        "date_parse_failures": date_failures,
        "zero_valid_cop_dem_files": zero_geo_files,
        "cop_dem_valid_fraction": geo_valid_pixels / max(geo_total_pixels, 1),
        "D_path_valid_count": dict(
            zip(FULL24_FEATURE_NAMES, feature_valid_counts.tolist())
        ),
        "D_path_valid_fraction": dict(
            zip(FULL24_FEATURE_NAMES, feature_valid_fraction.tolist())
        ),
        "window_any_valid_fraction": dict(
            zip(
                EOBS_VARIABLES,
                (daily_valid_counts / max(expected_windows, 1)).tolist(),
            )
        ),
        "window_all_five_valid_fraction": dict(
            zip(
                EOBS_VARIABLES,
                (daily_all_five_counts / max(expected_windows, 1)).tolist(),
            )
        ),
        "missing_driver_features": missing,
        "low_coverage_driver_features": low_coverage,
        "min_driver_valid_fraction": min_valid_fraction,
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
    require_stage15_initializer_if_formal(config, resume_from=resume_from)
    model = create_stage2_model(config, torch.device("cpu"))
    if resume_from:
        checkpoint = torch.load(resume_from, map_location="cpu", weights_only=False)
        load_stage2_model_state(model, checkpoint["model_state_dict"], strict=True)
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
    if is_stage2_v2_protocol(str(config["data"].get("stage2_protocol", ""))):
        return _check_v2_stats(config)
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
    min_valid_fraction = _min_driver_valid_fraction(config)
    valid_fraction = stats.get("valid_fraction")
    if valid_fraction is None and valid_count:
        valid_fraction = [
            float(count) / max(expected_count, 1)
            for count in valid_count
        ]
    valid_fraction = list(valid_fraction or [])
    if bool(config["training"].get("require_all_driver_features", True)):
        if len(valid_count) != len(expected_names):
            errors.append("stats valid_count length differs from the configured D layout")
        else:
            missing = [
                name
                for name, count in zip(expected_names, valid_count)
                if int(count) == 0
            ]
            if missing:
                errors.append(f"stats prove missing D features: {missing}")
        if len(valid_fraction) != len(expected_names):
            errors.append("stats valid_fraction length differs from the configured D layout")
        else:
            low_coverage = [
                name
                for name, fraction in zip(expected_names, valid_fraction)
                if float(fraction) < min_valid_fraction
            ]
            if low_coverage:
                errors.append(
                    "stats D valid_fraction below "
                    f"{min_valid_fraction:.3f}: {low_coverage}"
                )
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "path": str(path),
        "fit_split": stats.get("fit_split"),
        "num_files": stats_files,
        "feature_names": stats.get("feature_names"),
        "min_driver_valid_fraction": min_valid_fraction,
        "driver_valid_fraction": dict(zip(expected_names, valid_fraction)),
        "driver_coverage_ok": True,
    }


def _check_v2_stats(config: dict) -> Dict[str, Any]:
    """Prove that v2 normalization belongs to the frozen full train manifest."""

    path_text = config["data"].get("conditioning_stats_path")
    if not path_text:
        raise ValueError("formal Stage2-v2 requires data.conditioning_stats_path")
    path = Path(path_text)
    stats = ConditioningStatsV2.from_file(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    train_cfg = EarthNet2021Config.from_config(config["data"], split="train")
    expected_files = len(_discover_npz_files(train_cfg))
    errors = []
    if train_cfg.use_train_holdout:
        errors.append("v2 train config must set use_train_holdout=false")
    if not train_cfg.manifest_path:
        errors.append("v2 formal stats require an explicit train manifest")
    else:
        manifest = json.loads(Path(train_cfg.manifest_path).read_text(encoding="utf-8"))
        expected_digest = manifest.get("files_sha256")
        if stats.manifest_sha256 != expected_digest:
            errors.append(
                "stats manifest_sha256 does not match the configured train manifest"
            )
    if stats.num_files != expected_files:
        errors.append(
            f"stats num_files={stats.num_files}, train manifest resolves to {expected_files}"
        )
    require_full = bool(
        config.get("training", {}).get("require_full_conditioning_stats", True)
    )
    if require_full and payload.get("is_full_train") is not True:
        errors.append("conditioning stats are a smoke subset, not the full train manifest")
    if payload.get("g_variable") != "cop_dem":
        errors.append(f"g_variable={payload.get('g_variable')!r}, expected 'cop_dem'")
    if int(payload.get("g_valid_count", 0)) <= 0:
        errors.append("conditioning stats contain no valid cop_dem pixels")

    min_valid_fraction = _min_driver_valid_fraction(config)
    daily_counts = payload.get("daily_valid_count") or {}
    any_valid_fraction = payload.get("window_any_valid_fraction") or {}
    all_five_fraction = payload.get("window_all_five_valid_fraction") or {}
    if not isinstance(daily_counts, dict):
        errors.append("daily_valid_count must be an object keyed by E-OBS variable")
        daily_counts = {}
    if not isinstance(any_valid_fraction, dict):
        errors.append("window_any_valid_fraction must be an object keyed by E-OBS variable")
        any_valid_fraction = {}
    if not isinstance(all_five_fraction, dict):
        errors.append("window_all_five_valid_fraction must be an object keyed by E-OBS variable")
        all_five_fraction = {}
    missing_daily = [
        name for name in EOBS_VARIABLES if int(daily_counts.get(name, 0)) <= 0
    ]
    low_daily_coverage = [
        name
        for name in EOBS_VARIABLES
        if float(any_valid_fraction.get(name, 0.0)) < min_valid_fraction
    ]
    if bool(config.get("training", {}).get("require_all_driver_features", True)):
        if missing_daily:
            errors.append(f"stats prove missing daily E-OBS variables: {missing_daily}")
        if low_daily_coverage:
            errors.append(
                "stats window_any_valid_fraction below "
                f"{min_valid_fraction:.3f}: {low_daily_coverage}"
            )
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "path": str(path),
        "fit_split": "train",
        "num_files": stats.num_files,
        "manifest_sha256": stats.manifest_sha256,
        "feature_names": list(FULL24_FEATURE_NAMES),
        "g_variable": "cop_dem",
        "is_full_train": bool(payload.get("is_full_train")),
        "min_driver_valid_fraction": min_valid_fraction,
        "window_any_valid_fraction": {
            name: float(any_valid_fraction[name]) for name in EOBS_VARIABLES
        },
        "window_all_five_valid_fraction": {
            name: float(all_five_fraction.get(name, 0.0))
            for name in EOBS_VARIABLES
        },
        "driver_coverage_ok": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-root")
    parser.add_argument("--external-driver-root")
    parser.add_argument("--dgh-stats-path")
    parser.add_argument("--conditioning-stats-path")
    parser.add_argument("--manifest-path")
    parser.add_argument("--validation-manifest-path")
    parser.add_argument("--require-manifest", action="store_true")
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
    config.setdefault("training", {})
    config["data"]["split"] = args.split
    if args.data_root:
        config["data"]["root"] = args.data_root
    if args.external_driver_root:
        config["data"]["external_driver_root"] = args.external_driver_root
    if args.dgh_stats_path:
        config["data"]["dgh_stats_path"] = args.dgh_stats_path
    if args.conditioning_stats_path:
        config["data"]["conditioning_stats_path"] = args.conditioning_stats_path
    if args.manifest_path:
        config["data"]["manifest_path"] = args.manifest_path
        manifest_paths = config["data"].get("manifest_paths")
        if isinstance(manifest_paths, dict):
            manifest_paths[str(config["data"].get("split", "train"))] = args.manifest_path
    if args.validation_manifest_path:
        config["data"].setdefault("manifest_paths", {})["val"] = args.validation_manifest_path
    if args.require_manifest:
        config["data"]["require_manifest"] = True
    if args.stage15_checkpoint:
        config["model"]["encoder"]["from_checkpoint"] = args.stage15_checkpoint

    report: Dict[str, Any] = {
        "config": str(Path(args.config).resolve()),
        "data_root": config["data"]["root"],
        "stage2_protocol": config["data"].get("stage2_protocol", "legacy_direct9"),
        "external_driver_root": config["data"].get("external_driver_root"),
        "dgh_stats_path": config["data"].get("dgh_stats_path"),
        "conditioning_stats_path": config["data"].get("conditioning_stats_path"),
    }
    fatal = []
    try:
        is_v2 = is_stage2_v2_protocol(
            str(config["data"].get("stage2_protocol", "legacy_direct9"))
        )
        if is_v2:
            require_v2_stats = bool(
                config["training"].get(
                    "require_conditioning_stats",
                    config["data"].get("require_conditioning_stats", True),
                )
            )
            if require_v2_stats and not config["data"].get("conditioning_stats_path"):
                raise ValueError(
                    "formal Stage2-v2 requires --conditioning-stats-path"
                )
        elif bool(config["training"].get("require_dgh_stats", True)):
            if not config["data"].get("dgh_stats_path"):
                raise ValueError("formal training requires --dgh-stats-path")
        report["data"] = _scan_data(config, args.max_files)
        fatal.extend(report["data"]["fatal_reasons"])
        if is_v2 and config["data"].get("conditioning_stats_path"):
            report["stats"] = _check_stats(config)
        elif config["data"].get("dgh_stats_path"):
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
