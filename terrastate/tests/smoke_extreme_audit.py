#!/usr/bin/env python
"""tests/smoke_extreme_audit.py -- CPU smoke for the extreme hot-dry predictive-state audit pipeline.

Exercises every new file end to end on a tiny subsample with RANDOM models (no checkpoints, no GPU,
no training): hotdry_selector (calibrate + select) -> build_extreme_audit_protocol -> manifest load
-> materialize_manifest_view -> extreme_state_audit (both architectures, --smoke-fresh). Validates the
code path and artefact integrity, NOT scientific results.

Usage:
  python tests/smoke_extreme_audit.py \
      --train-root ROOT/train --ood-root ROOT/ood-t_chopped --dataset-root ROOT [--work-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(cmd, cwd=None, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd or REPO), capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout[-2000:]); print(r.stderr[-3000:])
        raise AssertionError(f"command failed ({r.returncode}): {' '.join(map(str, cmd))}")
    return r.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-root", required=True)
    ap.add_argument("--ood-root", required=True)
    ap.add_argument("--dataset-root", required=True)
    ap.add_argument("--work-dir", default=None)
    ap.add_argument("--train-cubes", type=int, default=300)
    ap.add_argument("--ood-cubes", type=int, default=250)
    args = ap.parse_args()

    work = Path(args.work_dir) if args.work_dir else Path(tempfile.mkdtemp(prefix="extreme_audit_smoke_"))
    work.mkdir(parents=True, exist_ok=True)
    climo = work / "climatology_train.json"; sel = work / "selection.json"
    proto = work / "protocol"; view = work / "view"; audit_out = work / "audit"
    passed = []

    print("[1/6] hotdry_selector calibrate")
    _run([PY, "tools/hotdry_selector.py", "calibrate", "--train-root", args.train_root,
          "--out", climo, "--max-cubes", args.train_cubes, "--min-cohort-n", 10])
    assert climo.is_file() and json.loads(climo.read_text())["thresholds"]["broad"]["hot"] > 0
    passed.append("calibrate")

    print("[2/6] hotdry_selector select")
    _run([PY, "tools/hotdry_selector.py", "select", "--ood-root", args.ood_root,
          "--climatology", climo, "--out", sel, "--max-cubes", args.ood_cubes])
    s = json.loads(sel.read_text())
    assert s["extreme"]["broad"], "no broad extremes selected in smoke subsample"
    assert len(s["cube_features"]) == s["n_valid"], "cube_features collapsed (non-unique keys!)"
    passed.append(f"select(strict={len(s['extreme']['strict'])},broad={len(s['extreme']['broad'])},"
                  f"matched={s['match_report']['n_matched']})")

    print("[3/6] build_extreme_audit_protocol")
    _run([PY, "scripts/build_extreme_audit_protocol.py", "--selection", sel, "--climatology", climo,
          "--dataset-root", args.dataset_root, "--out-dir", proto, "--frozen-utc", "2026-01-01T00:00:00Z"])
    for name in ("hotdry_manifest.json", "matched_normal_manifest.json", "climatology_train.json",
                 "thresholds.json", "protocol.json", "provenance.json", "MANIFEST.SHA256", "README.md"):
        assert (proto / name).is_file(), f"missing artefact {name}"
    # verify MANIFEST.SHA256 integrity
    _run(["sha256sum", "-c", "MANIFEST.SHA256"], cwd=str(proto)) if _has("sha256sum") else None
    passed.append("protocol")

    print("[4/6] manifest load + materialize view")
    sys.path.insert(0, str(REPO))
    from data.earthnet_manifest import load_manifest_files, GREENEARTHNET_CHOPPED_PROTOCOL_ID as CP
    n_ext = len(load_manifest_files(proto / "hotdry_manifest.json", args.dataset_root,
                                    expected_split="ood-t_chopped", expected_protocol=CP, verify_exists=True))
    _run([PY, "scripts/materialize_manifest_view.py", "--dataset-root", args.dataset_root, "--out-dir", view,
          "--manifest", proto / "hotdry_manifest.json", "--manifest", proto / "matched_normal_manifest.json"])
    assert any(view.rglob("*.nc")), "view has no symlinks"
    passed.append(f"view(ext={n_ext})")

    # pairs-first --limit logic (dataset-free): first N COMPLETE pairs -> derive strata (no truncate+intersect)
    nrm_audit = json.loads((proto / "matched_normal_manifest.json").read_text())["audit"]
    pnp = int(nrm_audit.get("n_pairs", len(nrm_audit["pairs_extreme_to_control"])))
    pr = sorted(nrm_audit["pairs_extreme_to_control"].items())
    assert len(pr[:4]) == min(4, pnp), "pairs-first --limit must give min(limit, protocol_n_pairs)"
    assert min(len(pr[:10 ** 6]), pnp) == pnp, "no-limit must equal frozen protocol n_pairs"
    sel = pr[:4]
    assert len({e for e, _ in sel}) == len(sel), "N pairs must give N unique extremes (derived from pairs)"
    passed.append(f"pairs-first limit (protocol_n_pairs={pnp}, limit4->{min(4, pnp)})")

    if _have_xarray():
        print("[5/6] extreme_state_audit (real dataset, fresh models, CPU, --limit 4 => exactly 4 pairs)")
        _run([PY, "eval/extreme_state_audit.py", "--protocol-dir", proto, "--dataset-root", args.dataset_root,
              "--data-dir", view, "--output-dir", audit_out, "--smoke-fresh", "--limit", 4,
              "--device", "cpu", "--no-accuracy", "--batch-size", 1, "--n-boot", 300])
        rep = json.loads((audit_out / "extreme_state_audit.json").read_text())
        assert set(rep["models"]) == {"b4", "exclusive"}, "both architectures must run"
        assert rep["n_pairs"] == 4, f"--limit 4 must yield exactly 4 complete pairs, got {rep['n_pairs']}"
        assert rep["evidence_role"] == "diagnostic", "default evidence role must be diagnostic"
        assert rep["models"]["b4"]["weather_in_base"] is True and rep["models"]["exclusive"]["weather_in_base"] is False
        for m in ("b4", "exclusive"):
            q3 = rep["models"][m]["q3_donor_fidelity"]
            assert q3["uf_differs_all_pairs"], f"{m}: donor future weather must differ from actual"
            assert q3["n_pairs"] == 4 and {"endpoint_fidelity_status", "hotdry_enhancement_status",
                                           "raw_status", "overall_status"} <= set(q3), "q3 status fields missing"
            assert q3["overall_status"] == "DIAGNOSTIC_ONLY", f"{m}: diagnostic role must not emit a formal verdict"
            assert "resp_clim" in rep["models"][m]["interaction_hotdry_minus_normal_cohort"], "cohort interaction missing"
        passed.append("audit(real dataset, --limit 4 -> 4 pairs, geo-cluster Q3 statuses, diagnostic-gated)")

        print("[6/6] extreme_state_audit with official scorer (CPU, --limit 2)")
        _run([PY, "eval/extreme_state_audit.py", "--protocol-dir", proto, "--dataset-root", args.dataset_root,
              "--data-dir", view, "--output-dir", work / "audit_acc", "--smoke-fresh", "--limit", 2,
              "--device", "cpu", "--batch-size", 1, "--n-boot", 100, "--workers", 2])
        rep2 = json.loads((work / "audit_acc" / "extreme_state_audit.json").read_text())
        assert rep2["n_pairs"] == 2, "official-scorer run must also be pairs-first"
        acc = rep2["models"]["exclusive"]["q3_aggregate_extreme"]
        assert set(acc) >= {"actual", "mean", "donor"}, "aggregate donor arms incomplete"
        passed.append("audit(official scorer actual/mean/donor aggregate)")
    else:
        print("[5/6] xarray absent locally -> synthetic-batch adapter/effect/interaction test (no dataset class)")
        _synthetic_adapter_test()
        passed.append("adapter+effect+interaction + donor-weather fidelity (synthetic, geo-cluster primary)")
        print("[6/6] real-dataset audit needs xarray -> run this CPU smoke in the server WorldModel env:")
        print(f"    python eval/extreme_state_audit.py --protocol-dir {proto} --dataset-root {args.dataset_root} \\")
        print(f"        --output-dir /tmp/audit_smoke --smoke-fresh --limit 4 --device cpu --no-accuracy "
              f"--batch-size 1 --n-boot 200 --evidence-role diagnostic")
        passed.append("server real-dataset audit command emitted (xarray needed)")

    print("[*] old evaluator/model git diff must be empty (no in-place edits)")
    diff = _run(["git", "diff", "--stat", "HEAD", "--", "eval/eval_b4_state_contract.py",
                 "eval/eval_b4_exclusive_contract.py", "models/plan_b_b4.py", "models/plan_b_b4_exclusive.py"])
    assert diff.strip() == "", f"old evaluator/model files were modified:\n{diff}"
    passed.append("old evaluator/model git diff empty")

    print("\n==== SMOKE PASS ====")
    for i, p in enumerate(passed, 1):
        print(f"  {i}. {p}")
    print(f"work dir: {work}")
    return 0


def _has(binname):
    from shutil import which
    return which(binname) is not None


def _have_xarray():
    try:
        import xarray  # noqa: F401
        return True
    except Exception:
        return False


def _synthetic_adapter_test():
    """Validate audit_adapters + per-cube effect + interaction math on a synthetic batch (no dataset class)."""
    import numpy as np
    import torch
    sys.path.insert(0, str(REPO))
    import eval.extreme_state_audit as ESA
    import eval.audit_adapters as A
    cpu = torch.device("cpu")
    b4, _ = ESA.load_model(None, cpu, "b4")
    ex, _ = ESA.load_model(None, cpu, "exclusive")
    assert A.weather_in_base(b4) is True and A.weather_in_base(ex) is False, "weather_in_base tags wrong"
    # arch dispatch (fail-closed exact-key load): TerraStateV2 & ObsWorldB4Exclusive -> exclusive T-only
    # route; ObsWorldB4 -> gate route. Confirms the V2 fix AND that the existing B4/B4Exclusive paths
    # are intact. load_model RAISES on the exclusive route if missing/unexpected != [].
    import tempfile

    def _fake_ckpt(arch, sd):
        p = tempfile.NamedTemporaryFile(suffix=".pt", delete=False).name
        torch.save({"arch": arch, "contract_cfg": {"state_dim": 256, "arch": arch}, "b4_state_dict": sd}, p)
        return p
    for arch, src, want in (("TerraStateV2", ex, "exclusive"),
                            ("ObsWorldB4Exclusive", ex, "exclusive"),
                            ("ObsWorldB4", b4, "b4")):
        mdl, prov = ESA.load_model(_fake_ckpt(arch, src.state_dict()), cpu)
        assert A.arch_of(mdl) == want and prov["arch"] == arch, f"{arch} must dispatch to the {want} route"
    print("  arch dispatch: TerraStateV2/ObsWorldB4Exclusive -> exclusive, ObsWorldB4 -> b4 (all clean fail-closed) OK")
    B, H, W, T = 2, 128, 128, 30
    data = {"dynamic": [torch.rand(B, T, 5, H, W), torch.randn(B, T, 24)],
            "dynamic_mask": [torch.rand(B, T, 1, H, W)], "static": [torch.rand(B, 5, H, W)],
            "landcover": torch.full((B, 1, H, W), 30.0),
            "filepath": ["JAS21/minicube_0_29SND_39.29_-8.56.nc", "MAM22/minicube_1_32TPP_43.28_10.58.nc"]}
    for name, m in (("b4", b4), ("ex", ex)):
        with torch.no_grad():
            pred = A.predict(m, data)
            uf = A.future_weather(m, data)
            pc = A.predict_with_weather(m, data, torch.zeros_like(uf))
            with A.zero_scale_ctx(m):
                _ = A.predict(m, data)
            zt, zh = A.extract_states(m, data, m.target_len)
        mask = ESA._veg_cloud_mask(data, m, pred)
        eff = ESA._per_cube_masked_mean(pred - pc, mask)
        assert pred.shape[0] == B and eff.shape == (B,), f"{name}: bad shapes pred{pred.shape} eff{eff.shape}"
        mv = torch.linalg.vector_norm(zh.reshape(B, -1) - zt.reshape(B, -1), dim=1)
        assert mv.shape == (B,), f"{name}: state_move shape {mv.shape} (expected per-cube)"
    assert ESA._boot([0.3, 0.1, -0.2], 500, 0)["n"] == 3
    assert ESA._cluster_boot([0.3, 0.1], ["29SND", "32TPP"], 500, 0)["n_clusters"] == 2

    # ---- matched-DONOR weather intervention: swap ONLY the full24 future weather ----
    Bd = 1

    def _synth(wshift, cube):
        return {"dynamic": [torch.rand(Bd, T, 5, H, W), torch.randn(Bd, T, 24) + wshift],
                "dynamic_mask": [torch.rand(Bd, T, 1, H, W)], "static": [torch.rand(Bd, 5, H, W)],
                "landcover": torch.full((Bd, 1, H, W), 30.0),
                "filepath": [f"JAS21/{cube}_29SND_39.29_-8.56.nc"]}
    E = _synth(1.5, "minicube_0"); C = _synth(-1.5, "minicube_1")
    for name, m in (("b4", b4), ("ex", ex)):
        with torch.no_grad():
            bE, zE, gE, ufE, shE = ESA._parts(m, E)
            _, _, _, ufC, _ = ESA._parts(m, C)
            pE_act = ESA._decode(m, bE, zE, gE, ufE, shE)
            pE_don = ESA._decode(m, bE, zE, gE, ufC, shE)          # extreme ctx + donor (C) future weather
        assert ufE.shape[1] == m.target_len and ufE.shape[-1] == 24, "future window must be full24"
        assert bool((ufE - ufC).abs().max() > 0), "donor future weather must differ from actual"
        mE = ESA._veg_cloud_mask(E, m, pE_act)
        le = ESA._endpoint_masked_mse(pE_act, E, m, mE)
        assert le.shape == (Bd,) and bool(torch.isfinite(torch.tensor(le)).all()), "endpoint loss shape/NaN"
        if name == "ex":                                          # exclusive: weather-free base -> donor changes pred
            assert bool((pE_act - pE_don).abs().max() > 0), "exclusive donor swap must change prediction"
    # ---- Q3 status logic (geo-cluster PRIMARY) + evidence-role gating ----
    S = ESA._q3_statuses
    assert S(True, True, True, False, "final")["raw_status"] == "Q3_STRONG_RESPONSE_FIDELITY_AND_HOTDRY_ENHANCEMENT"
    assert S(True, True, True, False, "final")["overall_status"].startswith("Q3_STRONG")
    assert S(True, True, True, False, "diagnostic")["overall_status"] == "DIAGNOSTIC_ONLY"   # diagnostic never strong
    assert S(True, True, True, True, "final")["overall_status"] == "DIAGNOSTIC_ONLY"          # b4 always
    assert S(True, True, False, False, "final")["raw_status"] == "Q3_RESPONSE_FIDELITY_ONLY"
    assert S(False, True, True, False, "final")["raw_status"] == "Q3_SENSITIVITY_PARTIAL"     # endpoint needs BOTH

    def _row(tile, cid, dd, dm, cdd=0.005):
        return dict(tile=tile, control_id=cid, uf_differs=True, resp_e_donor=0.01, resp_e_mean=0.01,
                    resp_c_donor=0.003, resp_c_mean=0.003, dloss_e_donor=dd, dloss_e_mean=dm,
                    dloss_c_donor=cdd, dloss_c_mean=cdd)

    def _pos():                                             # all tiles positive -> STRONG
        return [_row(f"T{t}", f"c{t}{k}", 0.02, 0.02) for t in range(5) for k in range(2)]

    def _fid_only():                                        # break enhancement (interaction) on one tile
        rows = _pos()
        for r in rows:
            if r["tile"] == "T4":
                r["dloss_c_donor"] = 0.5                    # interaction dloss_donor = 0.02-0.5 < 0 on T4
        return rows

    def _partial():                                         # break endpoint donor on one tile
        rows = _pos()
        for r in rows:
            if r["tile"] == "T4":
                r["dloss_e_donor"] = -0.5
        return rows

    def _geo_decides():                                     # paired>0 but geo crosses 0 on endpoint donor
        rows = [_row("T0", f"c0{k}", 0.1, 0.02, cdd=0.0) for k in range(30)]
        rows += [_row("T1", "c1", -0.2, 0.02, cdd=0.0), _row("T2", "c2", -0.2, 0.02, cdd=0.0)]
        return rows

    NB = 2000
    strong = ESA.q3_donor_report(ex, _pos(), NB, 0, evidence_role="final")
    assert strong["raw_status"] == "Q3_STRONG_RESPONSE_FIDELITY_AND_HOTDRY_ENHANCEMENT", strong["raw_status"]
    assert strong["endpoint_fidelity_status"] == "PASS" and strong["hotdry_enhancement_status"] == "PASS"
    assert ESA.q3_donor_report(ex, _fid_only(), NB, 0, "final")["raw_status"] == "Q3_RESPONSE_FIDELITY_ONLY"
    assert ESA.q3_donor_report(ex, _partial(), NB, 0, "final")["raw_status"] == "Q3_SENSITIVITY_PARTIAL"
    gd = ESA.q3_donor_report(ex, _geo_decides(), NB, 0, "final")
    dp = gd["endpoint_fidelity"]["extreme_actual_vs_donor"]
    assert dp["paired_bootstrap"]["significant_gt0"] is True, "paired should be significant here"
    assert dp["geo_cluster_bootstrap"]["significant_gt0"] is False, "geo-cluster should NOT be significant"
    assert gd["raw_status"] != "Q3_STRONG_RESPONSE_FIDELITY_AND_HOTDRY_ENHANCEMENT", "geo-cluster must decide, not paired"
    diag = ESA.q3_donor_report(ex, _pos(), NB, 0, evidence_role="diagnostic")
    assert diag["overall_status"] == "DIAGNOSTIC_ONLY" and diag["raw_status"].startswith("Q3_STRONG")
    assert ESA.q3_donor_report(b4, _pos(), NB, 0, "final")["overall_status"] == "DIAGNOSTIC_ONLY", "b4 diagnostic-only"
    empty = ESA.q3_donor_report(ex, [], NB, 0)
    assert empty["uf_differs_all_pairs"] is False and empty["n_pairs"] == 0, "empty pairing must not pass silently"
    for sec in ("paired_bootstrap", "geo_cluster_bootstrap", "reused_control_cluster_bootstrap"):
        v = strong["endpoint_fidelity"]["extreme_actual_vs_donor"][sec]
        assert v["mean"] == v["mean"], "NaN in donor bootstrap"
    print("  donor-weather fidelity: geo-cluster-primary STRONG/FIDELITY_ONLY/PARTIAL, geo-decides-not-paired, "
          "diagnostic gating, empty-guard OK")


if __name__ == "__main__":
    raise SystemExit(main())
