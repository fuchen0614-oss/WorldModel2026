#!/usr/bin/env python
"""Build historical_11904_reference.json for the reproduction gate.  CPU only, read-only inputs.

The numbers are EXTRACTED from the frozen raw result JSONs, never transcribed from
TERRASTATE_V2_EVIDENCE.md -- a doc-transcribed number would make the gate test my own typing
instead of the evaluator.  Both known copies of each raw JSON are hashed and required to agree.

Every source JSON is additionally required to record checkpoint 644deaac... (11,904) so the gate
cannot accidentally be seeded with 14,880 numbers.

Exit 0 written · 2 refused
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(__file__).resolve().parent
TS_ROOT = OPS.parents[2]
OUT = OPS / "historical_11904_reference.json"

LEGACY_SHA = "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd"

# How each source proves it is an 11,904 measurement.
#   "in_json"  -- the JSON body itself records the checkpoint sha (Q1/Q2 contract schema does)
#   "sidecar"  -- the extreme_state_audit schema records NO checkpoint identity at all; the
#                 producing run dir carries checkpoint_sha256.txt + checkpoint_path.txt beside a
#                 BYTE-IDENTICAL copy of the same JSON, and every per-stratum
#                 exclusive/*/pred/provenance.json embeds ckpt_sha.  We tie the release copy to
#                 that run dir by sha256 equality, then read the identity from the sidecar.
#                 This is weaker than in-JSON pinning, so it is recorded explicitly rather than
#                 waved through -- and it is why the Q3 job's own SHA check must also look at the
#                 sidecar instead of the result JSON.
Q3_RUN_DIR = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026-planb-v2train/runs/terrastate_v2/"
                  "selection/q3_final_boundary80_20260727_230029")

PROOF = {"val_q1q2": "in_json", "oodt_q1q2": "in_json", "oodt_q3": "sidecar"}

# (label, primary copy, independent second copy)
SOURCES = {
    "val_q1q2": ("writing/evidence_workspace/raw/release/val_q2_state_contract_exclusive.json",
                 "archive/04_RESULTS_EVIDENCE/historical_release_provenance/"
                 "val_q2_state_contract_exclusive.json"),
    "oodt_q1q2": ("writing/evidence_workspace/raw/release/oodt_q1q2_state_contract_exclusive.json",
                  "archive/04_RESULTS_EVIDENCE/historical_release_provenance/"
                  "oodt_q1q2_state_contract_exclusive.json"),
    "oodt_q3": ("writing/evidence_workspace/raw/release/q3_extreme_state_audit.json",
                "archive/04_RESULTS_EVIDENCE/historical_release_provenance/"
                "q3_extreme_state_audit.json"),
}

# job name in launch_manifest.json  <-  which frozen source it must reproduce
JOB_SOURCE = {
    "gpu3_legacy11904_val_q1q2": "val_q1q2",
    "gpu4_legacy11904_oodt_q1q2": "oodt_q1q2",
    "gpu5_legacy11904_oodt_q3": "oodt_q3",
}

Q1Q2_PATHS = [
    "Q1_forecast.full.R2",
    "Q1_forecast.full.rmse",
    "Q1_forecast.full.nse",
    "Q1_forecast.full.biasabs",
    "Q2_load_bearing.full.R2",
    "Q2_load_bearing.full.rmse",
    "Q2_load_bearing.alpha0.R2",
    "Q2_load_bearing.alpha0.rmse",
    "Q2_load_bearing.T_identity.R2",
    "Q2_load_bearing.T_identity.rmse",
    "Q2_load_bearing.official_R2_full_minus_alpha0",
    "Q2_load_bearing.official_R2_full_minus_Tid",
    "Q2_load_bearing.closure_cut_alpha0.paired.n",
    "Q2_load_bearing.closure_cut_alpha0.bootstrap95.mean",
    "Q2_load_bearing.closure_cut_alpha0.bootstrap95.ci_low",
    "Q2_load_bearing.closure_cut_alpha0.bootstrap95.ci_high",
    "Q2_load_bearing.transition_identity.bootstrap95.mean",
    "Q2_load_bearing.transition_identity.bootstrap95.ci_low",
    "Q2_load_bearing.transition_identity.bootstrap95.ci_high",
]

Q3_PATHS = [
    "models.exclusive.n_extreme",
    "models.exclusive.n_control",
    "models.exclusive.q3_aggregate_extreme.actual.R2",
    "models.exclusive.q3_aggregate_extreme.actual.rmse",
    "models.exclusive.q3_aggregate_extreme.donor.R2",
    "models.exclusive.q3_aggregate_extreme.donor.rmse",
    "models.exclusive.q3_aggregate_extreme.mean.R2",
    "models.exclusive.q3_aggregate_extreme.mean.rmse",
    "models.exclusive.q3_donor_fidelity.n_pairs",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_donor.delta_loss_mean",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_donor.paired_bootstrap.ci_low",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_donor.paired_bootstrap.ci_high",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_donor.geo_cluster_bootstrap.ci_low",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_donor.geo_cluster_bootstrap.ci_high",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_mean.delta_loss_mean",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_mean.paired_bootstrap.ci_low",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_mean.paired_bootstrap.ci_high",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_mean.geo_cluster_bootstrap.ci_low",
    "models.exclusive.q3_donor_fidelity.endpoint_fidelity."
    "extreme_actual_vs_mean.geo_cluster_bootstrap.ci_high",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dig(obj, *path):
    cur = obj
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def main() -> int:
    if OUT.exists():
        print(f"REFUSING: {OUT.name} already exists; move it aside first if it must change.")
        return 2

    loaded: dict[str, dict] = {}
    provenance: dict[str, dict] = {}
    for label, (a, b) in SOURCES.items():
        pa, pb = TS_ROOT / a, TS_ROOT / b
        for p in (pa, pb):
            if not p.exists():
                print(f"REFUSING: missing frozen source {p}")
                return 2
        ha, hb = sha256_file(pa), sha256_file(pb)
        if ha != hb:
            print(f"REFUSING: the two copies of {label} differ ({ha[:12]} vs {hb[:12]}); "
                  f"resolve which one is the frozen evidence before seeding the gate.")
            return 2
        d = json.loads(pa.read_text())
        prov: dict = {"path": a, "second_copy": b, "sha256": ha, "copies_agree": True,
                      "checkpoint_proof": PROOF[label]}

        # the source must be an 11,904 measurement -- proven per-schema, never assumed
        if PROOF[label] == "in_json":
            if LEGACY_SHA not in json.dumps(d):
                print(f"REFUSING: {label} does not record checkpoint {LEGACY_SHA[:12]}...; "
                      f"it is not an 11,904 result")
                return 2
            prov["ckpt_sha256_in_json"] = LEGACY_SHA
        else:
            # 1) the release copy must be byte-identical to the producing run's JSON
            run_json = Q3_RUN_DIR / "extreme_state_audit.json"
            side_sha = Q3_RUN_DIR / "checkpoint_sha256.txt"
            side_path = Q3_RUN_DIR / "checkpoint_path.txt"
            for p in (run_json, side_sha, side_path):
                if not p.exists():
                    print(f"REFUSING: {label} sidecar proof incomplete, missing {p}")
                    return 2
            hr = sha256_file(run_json)
            if hr != ha:
                print(f"REFUSING: {label} release copy ({ha[:12]}) is not byte-identical to the "
                      f"producing run's JSON ({hr[:12]}); the sidecar cannot be trusted to "
                      f"describe it")
                return 2
            # 2) the sidecar must name the 11,904 checkpoint
            got = side_sha.read_text().strip()
            if got != LEGACY_SHA:
                print(f"REFUSING: {label} sidecar checkpoint_sha256.txt = {got[:12]}..., "
                      f"expected {LEGACY_SHA[:12]}...")
                return 2
            # 3) independent third witness: per-stratum prediction provenance embeds ckpt_sha
            provs = sorted(Q3_RUN_DIR.glob("exclusive/*/*/pred/provenance.json"))
            wit = [p for p in provs
                   if LEGACY_SHA in json.dumps(json.loads(p.read_text()))]
            if not wit:
                print(f"REFUSING: {label} has no per-stratum provenance.json carrying "
                      f"ckpt_sha {LEGACY_SHA[:12]}...")
                return 2
            prov.update({
                "run_dir": str(Q3_RUN_DIR),
                "run_json_sha256_equals_release_copy": True,
                "sidecar_checkpoint_sha256": got,
                "sidecar_checkpoint_path": side_path.read_text().strip(),
                "per_stratum_provenance_witnesses": len(wit),
                "schema_gap_note": ("extreme_state_audit.json records protocol_sha but NOT the "
                                    "checkpoint sha; identity comes from the run dir.  The Q3 "
                                    "acceptance check must therefore verify the checkpoint file "
                                    "SHA directly, not expect it inside the result JSON."),
            })
            print(f"  {label}: identity via sidecar + {len(wit)} per-stratum witnesses")

        loaded[label] = d
        provenance[label] = prov
        print(f"  {label}: sha {ha[:16]}... (2 copies agree)")

    ref: dict = {}
    missing = []
    for job, label in JOB_SOURCE.items():
        paths = Q3_PATHS if label == "oodt_q3" else Q1Q2_PATHS
        for mp in paths:
            v = dig(loaded[label], *mp.split("."))
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                missing.append(f"{label}:{mp} -> {v!r}")
                continue
            ref[f"{job}:{mp}"] = v

    if missing:
        print("REFUSING: some pinned metric paths were not numeric in the frozen JSON:")
        for m in missing:
            print(f"    {m}")
        return 2

    ref["_generated_at"] = datetime.now(timezone.utc).isoformat()
    ref["_generated_by"] = "ops/e0_q1q2q3_11904_vs_14880/20260818_154859/make_historical_reference.py"
    ref["_checkpoint"] = {"logical_id": "terrastate/v2/legacy-boundary11904@v1",
                          "file_sha256": LEGACY_SHA, "step": 11904}
    ref["_sources"] = provenance
    ref["_tolerance"] = 1e-6
    ref["_tolerances"] = {
        ".paired.n": 0.0,
        "n_extreme": 0.0,
        "n_control": 0.0,
        "n_pairs": 0.0,
        ".R2": 1e-5,
        ".rmse": 1e-5,
        ".nse": 1e-5,
        ".biasabs": 1e-5,
        "official_R2_": 1e-5,
        "delta_loss_mean": 1e-5,
        "bootstrap95.": 1e-4,
        "_bootstrap.ci_": 1e-4,
    }
    ref["_tolerance_rationale"] = [
        "Counts (n, n_pairs, n_extreme, n_control) must match EXACTLY -- a changed count means a "
        "changed manifest or dataloader, which is harness drift by definition.",
        "Point metrics carry 1e-5: the frozen numbers were measured on GPU, and cuDNN/TF32 "
        "reduction order is not bit-stable across driver/library versions.  Real harness drift "
        "(different scorer, mask, manifest or split) moves these by orders of magnitude more.",
        "Bootstrap CI bounds carry 1e-4: both evaluators seed np.random.default_rng(--seed, "
        "default 0), so resampling is deterministic given identical inputs, but tiny per-sample "
        "perturbations propagate into the quantiles.",
        "These tolerances bound FLOAT NOISE only.  They are not a licence to wave through a "
        "mismatch: anything outside them is reported as DRIFT_TO_DIAGNOSE and must be traced to "
        "evaluator / manifest / scorer / dataloader before any comparison is read.",
    ]
    ref["_note"] = (
        "Reproduction target for the 11,904 RERUN only (jobs gpu3/gpu4/gpu5).  Same checkpoint + "
        "same frozen protocol => same numbers, so a mismatch means the harness moved, not the "
        "model.  These are 11,904's numbers and must never be relabelled as 14,880's."
    )

    OUT.write_text(json.dumps(ref, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    n = len([k for k in ref if not k.startswith("_")])
    print(f"wrote {OUT.name}: {n} pinned metrics across {len(JOB_SOURCE)} jobs")
    print(f"  sha256 = {sha256_file(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
