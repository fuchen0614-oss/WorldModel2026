#!/usr/bin/env python
"""E0 acceptance + aggregation for the 6 formal jobs.  CPU-only, read-only, fail closed.

Runs AFTER the six GPU jobs finish.  It (a) checks each job against the frozen manifest,
(b) re-verifies the checkpoints were not modified during evaluation, (c) confirms the
11,904 rerun reproduces the frozen historical numbers, and only then (d) emits the
11,904 vs 14,880 comparison with paired deltas.

Hard rules encoded here:
  * smoke/ and any dir containing INTERRUPTED.json are NEVER aggregated
  * a missing/failed job blocks the comparison; partial tables are not emitted as final
  * a 11,904 reproduction mismatch is reported as EVALUATOR/PROTOCOL DRIFT to be diagnosed,
    never silently explained as a model difference
  * no checkpoint is selected or switched on the basis of any metric read here

Exit 0 accepted · 2 acceptance failed · 3 jobs not finished yet
Usage: verify_and_aggregate.py [--selftest]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

OPS = Path(__file__).resolve().parent
TS_ROOT = OPS.parents[2]
MANIFEST = OPS / "launch_manifest.json"
LAUNCH_REC = OPS / "e0_launch_record.json"
REPORT = OPS / "e0_acceptance_report.json"
COMPARISON = OPS / "e0_comparison_11904_vs_14880.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, name: str, ok: bool, detail: str) -> bool:
        self.rows.append({"name": name, "ok": bool(ok), "detail": detail})
        print(f"  [{'OK  ' if ok else 'FAIL'}] {name}: {detail}")
        return bool(ok)

    @property
    def failures(self) -> list[dict]:
        return [r for r in self.rows if not r["ok"]]


def find_result_json(outdir: Path, kind: str) -> Path | None:
    """Locate the evaluator's result JSON, refusing smoke/interrupted dirs."""
    if not outdir.exists():
        return None
    if (outdir / "INTERRUPTED.json").exists():
        return None
    if "smoke" in outdir.parts:
        return None
    names = ({"q1q2": ["b4_exclusive_contract.json", "contract_report.json"],
              "q3": ["extreme_state_audit.json"]})[kind]
    for n in names:
        p = outdir / n
        if p.is_file():
            return p
    cands = sorted(outdir.glob("*.json"))
    cands = [c for c in cands if c.name != "INTERRUPTED.json"]
    return cands[0] if cands else None


def dig(obj, *path, default=None):
    """Tolerant nested lookup: dig(d, 'q1', 'r2')."""
    cur = obj
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def find_first(obj, keys: tuple[str, ...]):
    """Depth-first search for the first of `keys` present anywhere in a nested structure."""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and isinstance(obj[k], (int, float)):
                return obj[k]
        for v in obj.values():
            r = find_first(v, keys)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_first(v, keys)
            if r is not None:
                return r
    return None


# ---------------------------------------------------------------- per-job acceptance
def check_jobs(ck: Checks) -> tuple[dict, bool]:
    man = json.loads(MANIFEST.read_text())
    jobs = {j["name"]: j for j in man["jobs"]}

    if not LAUNCH_REC.exists():
        ck.add("launch_record_exists", False,
               f"{LAUNCH_REC} absent -- the six formal jobs have not been launched")
        return {}, False
    rec = json.loads(LAUNCH_REC.read_text())
    launched = {r["name"]: r for r in rec.get("jobs", [])}
    ck.add("launch_record_exists", True, f"{len(launched)} job records")
    ck.add("all_six_jobs_launched", len(launched) == 6,
           f"{len(launched)}/6 present: {sorted(launched)}")

    results: dict = {}
    all_ok = True
    for name, job in jobs.items():
        lr = launched.get(name)
        if lr is None:
            all_ok &= ck.add(f"{name}:launched", False, "no launch record")
            continue
        rc = lr.get("exit_code")
        all_ok &= ck.add(f"{name}:exit_code_0", rc == 0, f"exit_code={rc}")
        outdir = Path(job["output_dir"])
        interrupted = (outdir / "INTERRUPTED.json").exists()
        all_ok &= ck.add(f"{name}:not_interrupted", not interrupted,
                         "clean" if not interrupted else "INTERRUPTED -- excluded from aggregation")
        # checkpoint unchanged across the evaluation
        ckpt = Path(job["checkpoint_path"])
        now = sha256_file(ckpt) if ckpt.exists() else "<missing>"
        all_ok &= ck.add(f"{name}:ckpt_sha_unchanged", now == job["checkpoint_sha256"],
                         f"{now[:16]}... vs frozen {job['checkpoint_sha256'][:16]}...")
        # frozen manifests unchanged
        for label, mp, want in job.get("manifest_shas", []):
            p = Path(mp)
            g = sha256_file(p) if p.exists() else "<missing>"
            all_ok &= ck.add(f"{name}:{label}_manifest_sha", g == want, f"{g[:16]}...")
        rp = find_result_json(outdir, job["kind"])
        if rp is None:
            all_ok &= ck.add(f"{name}:result_json", False,
                             f"no aggregatable result JSON in {outdir}")
            continue
        all_ok &= ck.add(f"{name}:result_json", True, str(rp.relative_to(TS_ROOT)))
        data = json.loads(rp.read_text())
        results[name] = {"job": job, "path": str(rp), "data": data,
                         "exit_code": rc, "launch": lr}
        # counts + role
        if job["kind"] == "q1q2":
            n = find_first(data, ("n_targets", "n_samples", "num_files", "n_cubes", "n"))
            all_ok &= ck.add(f"{name}:expected_targets", n == job["expected_targets"],
                             f"n={n} expect {job['expected_targets']}")
            role = json.dumps(data)
            all_ok &= ck.add(f"{name}:not_smoke", '"limit": 0' in role or "limit" not in role
                             or find_first(data, ("limit",)) in (0, None),
                             f"limit={find_first(data, ('limit',))} (0/absent = full run)")
        else:
            npairs = data.get("n_pairs")
            all_ok &= ck.add(f"{name}:expected_pairs_84", npairs == job["expected_pairs"],
                             f"n_pairs={npairs} expect {job['expected_pairs']}")
            all_ok &= ck.add(f"{name}:evidence_role_final",
                             data.get("evidence_role") == "final",
                             f"evidence_role={data.get('evidence_role')}")
            all_ok &= ck.add(f"{name}:protocol_sha_pinned",
                             bool(data.get("protocol_sha")),
                             f"protocol_sha={str(data.get('protocol_sha'))[:16]}...")
    return results, all_ok


# ---------------------------------------------------------------- historical reproduction
HISTORICAL_REF = OPS / "historical_11904_reference.json"


def check_reproduction(ck: Checks, results: dict) -> dict:
    """The 11,904 rerun must reproduce the frozen historical 11,904 numbers.

    Same checkpoint (legacy-boundary11904@v1, SHA 644deaac...) + same frozen protocol =>
    the same numbers.  A mismatch therefore means the HARNESS moved (evaluator, manifest,
    scorer, dataloader), not the model.  Report it as drift to diagnose; never explain it
    as a model difference and never let it silently pass into the comparison.
    """
    out: dict = {"status": "not_evaluated", "deltas": {}}
    if not HISTORICAL_REF.exists():
        ck.add("historical_reference_present", False,
               f"{HISTORICAL_REF.name} absent -- record the frozen historical 11,904 numbers "
               f"there to enable the reproduction gate")
        out["status"] = "no_reference"
        return out
    ref = json.loads(HISTORICAL_REF.read_text())
    n_metrics = len([k for k in ref if not k.startswith("_")])
    ck.add("historical_reference_present", True, f"{n_metrics} reference metrics")
    default_tol = ref.get("_tolerance", 1e-6)
    per_pattern = ref.get("_tolerances", {})

    def tol_for(metric_path: str) -> float:
        """Longest matching pattern wins; counts (tol 0) must therefore match exactly."""
        best, best_len = default_tol, -1
        for pat, t in per_pattern.items():
            if pat in metric_path and len(pat) > best_len:
                best, best_len = t, len(pat)
        return best

    out["tolerance_policy"] = {"default": default_tol, "per_pattern": per_pattern}
    ok_all = True
    for key, want in ref.items():
        if key.startswith("_"):
            continue
        job_name, metric_path = key.split(":", 1)
        r = results.get(job_name)
        if r is None:
            ok_all &= ck.add(f"repro:{key}", False, "job result missing")
            continue
        got = dig(r["data"], *metric_path.split("."))
        if got is None:
            got = find_first(r["data"], (metric_path.split(".")[-1],))
        if not isinstance(got, (int, float)):
            ok_all &= ck.add(f"repro:{key}", False, f"metric not found (got {got!r})")
            continue
        d = abs(got - want)
        tol = tol_for(metric_path)
        same = d <= tol
        ok_all &= ck.add(f"repro:{key}", same,
                         f"rerun={got:.6f} frozen={want:.6f} |delta|={d:.2e} tol={tol:g}")
        out["deltas"][key] = {"rerun": got, "frozen_historical": want, "abs_delta": d,
                              "tolerance": tol, "within_tolerance": same}
    out["status"] = "reproduced" if ok_all else "DRIFT_TO_DIAGNOSE"
    if not ok_all:
        print("\n  !! The 11,904 RERUN does not reproduce 11,904's own frozen historical numbers.")
        print("     Both sides of THIS gate are the same checkpoint (644deaac..., step 11,904),")
        print("     so the difference cannot come from the model.  Diagnose evaluator /")
        print("     manifest / scorer / dataloader drift FIRST.")
        print("     (Unrelated to the 11,904-vs-14,880 comparison, where the weights DO differ.)")
    return out


# ---------------------------------------------------------------- comparison
def paired_stats(a: list[float], b: list[float]) -> dict:
    """Paired delta (b - a) with a normal-approx CI; per-sample pairing preserved."""
    pairs = [(x, y) for x, y in zip(a, b)
             if isinstance(x, (int, float)) and isinstance(y, (int, float))]
    n = len(pairs)
    if n < 2:
        return {"n": n, "note": "insufficient paired samples"}
    d = [y - x for x, y in pairs]
    m = sum(d) / n
    var = sum((v - m) ** 2 for v in d) / (n - 1)
    se = math.sqrt(var / n)
    return {"n": n, "mean_paired_delta": m, "se": se,
            "ci95": [m - 1.96 * se, m + 1.96 * se],
            "excludes_zero": (m - 1.96 * se) * (m + 1.96 * se) > 0}


PAIRS = [
    ("validation_q1q2", "gpu3_legacy11904_val_q1q2", "gpu0_v14880_val_q1q2"),
    ("oodt_q1q2", "gpu4_legacy11904_oodt_q1q2", "gpu1_v14880_oodt_q1q2"),
    ("oodt_q3", "gpu5_legacy11904_oodt_q3", "gpu2_v14880_oodt_q3"),
]


def build_comparison(results: dict, repro: dict) -> dict:
    comp: dict = {
        "schema": "e0_comparison_v1",
        "legacy_id": "terrastate/v2/legacy-boundary11904@v1",
        "verified_id": "terrastate/v2/verified-resume14880@v1",
        "reproduction_gate": repro["status"],
        "sections": {},
        "interpretation_rules": [
            "11,904 and 14,880 are DIFFERENT weights (value_sha aba100c138119bc0 vs "
            "aa98fbd2fa302727; max abs diff 1.93e-03 over 255 tensors), so a metric difference "
            "between them is a genuine 11,904-vs-14,880 state difference.",
            "Separately: verified 14,880 is byte-identical to HISTORICAL 14,880 "
            "(both value_sha aa98fbd2fa302727, max abs diff 0). That identity is what licenses "
            "the reproduction gate below; it says nothing about the 11,904 comparison. Do not "
            "conflate the two statements.",
            "Prefer same-sample PAIRED deltas with CIs over raw aggregate differences.",
            "A ~0.01 OOD-t point difference is DESCRIPTIVE alignment context only and must not "
            "be used to select or switch a checkpoint.",
            "11,904 remains the legacy evidence checkpoint; verified 14,880 remains the anchor, "
            "regardless of which scores higher.",
            "Historical Q1/Q2/Q3 numbers measured on 11,904 must never be relabelled as 14,880.",
        ],
    }
    for label, legacy_job, new_job in PAIRS:
        lr, nr = results.get(legacy_job), results.get(new_job)
        if lr is None or nr is None:
            comp["sections"][label] = {"status": "incomplete",
                                       "missing": [j for j, r in
                                                   ((legacy_job, lr), (new_job, nr)) if r is None]}
            continue
        ld, nd = lr["data"], nr["data"]
        sec: dict = {"status": "ok",
                     "legacy_result": lr["path"], "verified_result": nr["path"],
                     "raw": {}, "paired": {}}
        if label.endswith("q1q2"):
            for metric in ("r2", "R2", "rmse", "RMSE", "nse", "mae"):
                a, b = find_first(ld, (metric,)), find_first(nd, (metric,))
                if a is not None and b is not None:
                    sec["raw"][metric] = {"legacy_11904": a, "verified_14880": b,
                                          "raw_delta": b - a}
            for arm in ("full", "state_removed", "identity_transition"):
                a, b = dig(ld, "q2", arm), dig(nd, "q2", arm)
                if a is not None or b is not None:
                    sec["raw"][f"q2_{arm}"] = {"legacy_11904": a, "verified_14880": b}
            for key in ("per_cube", "per_sample", "per_target", "per_cube_r2"):
                pa, pb = find_first_list(ld, key), find_first_list(nd, key)
                if pa and pb and len(pa) == len(pb):
                    sec["paired"][key] = paired_stats(pa, pb)
                    break
            else:
                sec["paired"]["note"] = ("no aligned per-sample vectors found in both result "
                                         "JSONs; paired CI requires --dump-per-cube style output")
        else:
            for arm in ("actual", "donor", "mean"):
                a, b = find_first(ld, (arm,)), find_first(nd, (arm,))
                sec["raw"][arm] = {"legacy_11904": a, "verified_14880": b}
            for key in ("per_pair", "per_cube", "pairs"):
                pa, pb = find_first_list(ld, key), find_first_list(nd, key)
                if pa and pb and len(pa) == len(pb):
                    sec["paired"][key] = paired_stats(pa, pb)
                    break
            else:
                sec["paired"]["note"] = ("no aligned per-pair vectors found; rerun with "
                                         "--dump-per-cube (the frozen manifest already sets it)")
            for k in ("cluster_ci", "geo_cluster_ci", "paired_ci", "ci95"):
                a, b = dig(ld, k), dig(nd, k)
                if a or b:
                    sec["raw"][k] = {"legacy_11904": a, "verified_14880": b}
        comp["sections"][label] = sec
    return comp


def find_first_list(obj, key: str) -> list | None:
    """Find a list of numbers stored under `key` anywhere in the structure."""
    if isinstance(obj, dict):
        v = obj.get(key)
        if isinstance(v, list) and v and all(isinstance(x, (int, float)) for x in v):
            return v
        if isinstance(v, list) and v and isinstance(v[0], dict):
            for cand in ("value", "r2", "delta", "score", "actual"):
                col = [d.get(cand) for d in v if isinstance(d, dict)]
                if col and all(isinstance(x, (int, float)) for x in col):
                    return col
        for vv in obj.values():
            r = find_first_list(vv, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for vv in obj:
            r = find_first_list(vv, key)
            if r is not None:
                return r
    return None


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    """Exercise the gates on synthetic fixtures.  No GPU, no full-data evaluation."""
    print("verify_and_aggregate self-test")
    n = p = 0

    def t(name: str, cond: bool) -> None:
        nonlocal n, p
        n += 1
        p += 1 if cond else 0
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    # smoke dirs must never be aggregated
    t("smoke dir refused", find_result_json(OPS / "smoke" / "q3_cpu", "q3") is None)

    # interrupted dirs must never be aggregated
    sb = OPS / "selftest" / "fixture_interrupted"
    sb.mkdir(parents=True, exist_ok=True)
    (sb / "extreme_state_audit.json").write_text('{"n_pairs": 84}')
    (sb / "INTERRUPTED.json").write_text('{"reason": "test"}')
    t("interrupted dir refused", find_result_json(sb, "q3") is None)

    # a clean fixture IS found
    cb = OPS / "selftest" / "fixture_clean"
    cb.mkdir(parents=True, exist_ok=True)
    (cb / "extreme_state_audit.json").write_text('{"n_pairs": 84}')
    t("clean dir accepted", find_result_json(cb, "q3") is not None)

    # paired stats: a constant +0.01 shift over 84 pairs must exclude zero
    a = [0.30 + 0.001 * i for i in range(84)]
    b = [x + 0.01 for x in a]
    ps = paired_stats(a, b)
    t("paired delta = +0.01", abs(ps["mean_paired_delta"] - 0.01) < 1e-12)
    t("zero-variance shift excludes zero", ps["excludes_zero"] is True)
    t("insufficient pairs handled", paired_stats([1.0], [2.0])["n"] == 1)

    # nested lookup helpers
    t("find_first nested", find_first({"a": {"b": {"r2": 0.42}}}, ("r2",)) == 0.42)
    t("find_first_list of dicts",
      find_first_list({"x": {"per_pair": [{"value": 1.0}, {"value": 2.0}]}}, "per_pair") == [1.0, 2.0])

    # comparison with a missing job must be marked incomplete, never emitted as final
    comp = build_comparison({}, {"status": "no_reference"})
    t("missing jobs -> incomplete sections",
      all(s.get("status") == "incomplete" for s in comp["sections"].values()))
    t("interpretation rules present", len(comp["interpretation_rules"]) >= 5)

    # ---- reproduction gate, driven by the REAL reference file ----------------------------
    # Fixtures are synthesised from the reference itself, so no real result is ever read to
    # make a selection; what is under test is the gate's arithmetic and its verdicts.
    if HISTORICAL_REF.exists():
        ref = json.loads(HISTORICAL_REF.read_text())
        keys = [k for k in ref if not k.startswith("_")]
        t("reference has 3 legacy jobs",
          len({k.split(":", 1)[0] for k in keys}) == 3)
        t("reference targets only legacy jobs",
          all("legacy11904" in k.split(":", 1)[0] for k in keys))
        t("reference records 11,904 checkpoint",
          ref.get("_checkpoint", {}).get("file_sha256", "").startswith("644deaac"))
        t("count tolerances are exactly zero",
          all(ref["_tolerances"][k] == 0.0
              for k in ("n_pairs", "n_extreme", "n_control", ".paired.n")))

        def synth(mutate=None) -> dict:
            """Rebuild per-job nested dicts holding exactly the reference values."""
            jobs: dict = {}
            for k in keys:
                job, mp = k.split(":", 1)
                cur = jobs.setdefault(job, {"data": {}})["data"]
                parts = mp.split(".")
                for seg in parts[:-1]:
                    cur = cur.setdefault(seg, {})
                v = ref[k]
                cur[parts[-1]] = mutate(k, v) if mutate else v
            return jobs

        c1 = Checks()
        r1 = check_reproduction(c1, synth())
        t("exact replay -> reproduced", r1["status"] == "reproduced")

        # a 1e-7 wobble on point metrics is float noise and must pass
        c2 = Checks()
        r2 = check_reproduction(c2, synth(
            lambda k, v: v + 1e-7 if isinstance(v, float) and ".R2" in k else v))
        t("1e-7 float noise tolerated", r2["status"] == "reproduced")

        # a 0.01 shift is NOT noise -- that is drift and must be caught
        c3 = Checks()
        r3 = check_reproduction(c3, synth(
            lambda k, v: v + 0.01 if ".R2" in k else v))
        t("0.01 shift -> DRIFT_TO_DIAGNOSE", r3["status"] == "DRIFT_TO_DIAGNOSE")

        # a changed sample count is drift by definition, however small
        c4 = Checks()
        r4 = check_reproduction(c4, synth(
            lambda k, v: v - 1 if k.endswith("n_pairs") else v))
        t("n_pairs 84->83 -> DRIFT_TO_DIAGNOSE", r4["status"] == "DRIFT_TO_DIAGNOSE")

        # a missing job must fail loudly rather than silently reproduce
        c5 = Checks()
        part = synth()
        part.pop("gpu5_legacy11904_oodt_q3", None)
        r5 = check_reproduction(c5, part)
        t("missing job -> DRIFT_TO_DIAGNOSE", r5["status"] == "DRIFT_TO_DIAGNOSE")
    else:
        t("historical reference present", False)

    print(f"\nself-test: {p}/{n} passed")
    return 0 if p == n else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    print("E0 acceptance + aggregation")
    ck = Checks()
    results, jobs_ok = check_jobs(ck)

    if not results:
        print("\nNOT READY: the six formal jobs have not produced aggregatable results yet.")
        REPORT.write_text(json.dumps(
            {"status": "NOT_READY", "checks": ck.rows}, ensure_ascii=False, indent=2))
        return 3

    repro = check_reproduction(ck, results)
    comp = build_comparison(results, repro)

    n_ok = len(ck.rows) - len(ck.failures)
    print(f"\nacceptance: {n_ok}/{len(ck.rows)} checks passed")
    accepted = not ck.failures and jobs_ok and repro["status"] in ("reproduced", "no_reference")

    REPORT.write_text(json.dumps(
        {"accepted": accepted, "n_checks": len(ck.rows), "failures": ck.failures,
         "checks": ck.rows, "reproduction": repro}, ensure_ascii=False, indent=2))
    COMPARISON.write_text(json.dumps(comp, ensure_ascii=False, indent=2))
    print(f"wrote {REPORT.name} and {COMPARISON.name}")

    if not accepted:
        print("\nNOT ACCEPTED -- see failures above. No comparison is to be treated as final.")
        return 2
    print("\nACCEPTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
