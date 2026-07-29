#!/usr/bin/env python
"""Summarize completed no-FS Q1/Q2 evaluator JSONs without rerunning evaluation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


REFERENCES = {
    "val_chopped": {
        "full_R2": 0.49732,
        "RMSE": 0.15729,
        "state_removal_official_delta_R2": 0.01121,
        "paired_mean_delta_R2": 0.01616,
        "paired_ci95": [0.00643, 0.02590],
    },
    "ood-t_chopped": {
        "full_R2": 0.56935,
        "RMSE": 0.15059,
        "state_removal_official_delta_R2": 0.01997,
        "paired_mean_delta_R2": 0.02200,
        "paired_ci95": [0.01422, 0.03018],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-json", required=True)
    parser.add_argument("--ood-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    return parser.parse_args()


def extract(path: Path) -> dict:
    result = json.loads(path.read_text())
    assert result["status"] == "COMPLETE"
    assert result["checkpoint_unchanged"] is True
    assert result["provenance"]["sections"] == ["q1", "q2"]
    q1 = result["Q1_forecast"]["full"]
    q2 = result["Q2_load_bearing"]
    closure = q2["closure_cut_alpha0"]["bootstrap95"]
    transition = q2["transition_identity"]["bootstrap95"]
    extracted = {
        "full_R2": q1["R2"],
        "RMSE": q1["rmse"],
        "state_removal_R2": q2["alpha0"]["R2"],
        "state_removal_official_delta_R2": q2["official_R2_full_minus_alpha0"],
        "paired_mean_delta_R2": closure["mean"],
        "paired_ci95": [closure["ci_low"], closure["ci_high"]],
        "T_identity_R2": q2["T_identity"]["R2"],
        "T_identity_official_delta_R2": q2["official_R2_full_minus_Tid"],
        "T_identity_paired_mean_delta_R2": transition["mean"],
        "T_identity_paired_ci95": [transition["ci_low"], transition["ci_high"]],
        "q2_verdict": q2["verdict"],
        "invariants": q2["invariants"],
        "checkpoint_unchanged": result["checkpoint_unchanged"],
    }
    headline = [
        extracted["full_R2"],
        extracted["RMSE"],
        extracted["state_removal_R2"],
        extracted["state_removal_official_delta_R2"],
        extracted["paired_mean_delta_R2"],
        *extracted["paired_ci95"],
        extracted["T_identity_R2"],
        extracted["T_identity_official_delta_R2"],
        extracted["T_identity_paired_mean_delta_R2"],
        *extracted["T_identity_paired_ci95"],
    ]
    assert all(math.isfinite(float(value)) for value in headline)
    return extracted


def main() -> int:
    args = parse_args()
    ablations = {
        "val_chopped": extract(Path(args.val_json)),
        "ood-t_chopped": extract(Path(args.ood_json)),
    }
    payload = {
        "status": "Q1_Q2_COMPLETE",
        "q3_status": "NOT_RUN",
        "full_terrastate_reference": REFERENCES,
        "without_future_state_anchor": ablations,
    }
    Path(args.output_json).write_text(json.dumps(payload, indent=2, allow_nan=False))

    lines = [
        "# TerraState: Full vs w/o Future-State Anchor",
        "",
        "| split | model | Full R2 | RMSE | state-removal R2 | official delta R2 | paired mean | paired 95% CI | T=Id R2 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("val_chopped", "ood-t_chopped"):
        ref, abl = REFERENCES[split], ablations[split]
        lines.append(
            f"| {split} | Full TerraState | {ref['full_R2']:.5f} | "
            f"{ref['RMSE']:.5f} | — | "
            f"{ref['state_removal_official_delta_R2']:.5f} | "
            f"{ref['paired_mean_delta_R2']:.5f} | "
            f"[{ref['paired_ci95'][0]:.5f}, {ref['paired_ci95'][1]:.5f}] | — |"
        )
        lines.append(
            f"| {split} | w/o FS | {abl['full_R2']:.5f} | {abl['RMSE']:.5f} | "
            f"{abl['state_removal_R2']:.5f} | "
            f"{abl['state_removal_official_delta_R2']:.5f} | "
            f"{abl['paired_mean_delta_R2']:.5f} | "
            f"[{abl['paired_ci95'][0]:.5f}, {abl['paired_ci95'][1]:.5f}] | "
            f"{abl['T_identity_R2']:.5f} |"
        )
    Path(args.output_md).write_text("\n".join(lines) + "\n")
    print(json.dumps(payload, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
