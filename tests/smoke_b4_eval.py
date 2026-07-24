"""plan-b-pvt · CPU synthetic verification of the B4 post-training eval infra (v2).

No GPU / no real checkpoint / no real data / no scoring (xarray-free). Verifies the
hardening fixes: real N-target subset mirror (Fix 1), NaN/±Inf rejection (Fix 2),
season+geo donor schema validator (Fix 3), Q4 diagnostic renaming + frozen guard
(Fix 4/6), intervention recoverability, donor-only-affects-T (B0 fixed), --limit
subset, and checkpoint byte-invariance. Actual scoring / stale-artifact wipe /
limit export==score on real cubes need the server (xarray + official scorer).

Run: CUDA_VISIBLE_DEVICES="" <WorldModel python> tests/smoke_b4_eval.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.plan_b_b4 import ObsWorldB4  # noqa: E402
from eval.select_b4_checkpoint import (  # noqa: E402
    discover_checkpoints, rank_and_select, mirror_prediction_targets, _finite,
)
from eval.eval_b4_state_contract import (  # noqa: E402
    _gate_zero, _t_identity, _paired_diff, _sha, _predict_donor, _load_guard_config,
    _targets, _q4, _driver_deltas, validate_donor_manifest,
)
from eval.b4_donor_schema import (  # noqa: E402
    SCHEMA_VERSION, season_bucket, parse_cube_key, haversine_km, build_pairs,
)
from eval.export_b4_predictions import load_b4  # noqa: E402


class FakeDS:
    def __init__(self, n=3, H=128, W=128, T=30):
        self.filepaths = [f"/fake/JAS21/cube{i}.nc" for i in range(n)]
        self.H, self.W, self.T = H, W, T

    def __len__(self):
        return len(self.filepaths)

    def __getitem__(self, i):
        g = torch.Generator().manual_seed(i)
        dyn = torch.randn(self.T, 5, self.H, self.W, generator=g); dyn[:, 0] = torch.tanh(dyn[:, 0])
        return {"dynamic": [dyn, torch.randn(self.T, 24, generator=g)],
                "dynamic_mask": [(torch.rand(self.T, 1, self.H, self.W, generator=g) < 0.05).float()],
                "static": [torch.randn(5, self.H, self.W, generator=g)],
                "landcover": torch.randint(10, 41, (1, self.H, self.W), generator=g).float(),
                "filepath": self.filepaths[i]}


def fake_data(B=2, T=30, H=128, W=128, seed=0):
    g = torch.Generator().manual_seed(seed)
    dyn = torch.randn(B, T, 5, H, W, generator=g); dyn[:, :, 0] = torch.tanh(dyn[:, :, 0])
    return {"dynamic": [dyn, torch.randn(B, T, 24, generator=g)],
            "dynamic_mask": [(torch.rand(B, T, 1, H, W, generator=g) < 0.05).float()],
            "static": [torch.randn(B, 5, H, W, generator=g)],
            "landcover": torch.randint(10, 41, (B, 1, H, W), generator=g).float(), "filepath": "/fake/JAS21/x.nc"}


def _touch(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"x")


def _good_donor_manifest(root: Path):
    """Two same-season (JJA) geo-near cubes on real temp files -> a valid manifest."""
    t_rel = "29SND/29SND_2018-07-01_2018-12-01_a.nc"
    d_rel = "29SNE/29SNE_2018-07-15_2018-12-15_b.nc"
    _touch(root / t_rel); _touch(root / d_rel)
    records = {t_rel: {"tile": "29SND", "season": "JJA", "centroid": [40.0, -4.0]},
               d_rel: {"tile": "29SNE", "season": "JJA", "centroid": [40.2, -4.1]}}
    pairs = build_pairs(records, max_geo_km=150.0)
    manifest = {"donor_schema": {"version": SCHEMA_VERSION, "season_rule": "s", "geo_rule": "g",
                                 "max_geo_km": 150.0, "season_source": "netcdf_time",
                                 "geo_source": "netcdf_latlon_centroid"},
                "pairs": pairs}
    return manifest, [root / t_rel]


def main():
    C = []
    dev = torch.device("cpu")

    # -- discovery + ranking (Fix 2: NaN AND ±Inf rejected) --------------------
    with tempfile.TemporaryDirectory() as td:
        for n in ("checkpoint_best.pt", "checkpoint_last.pt", "checkpoint_step2000.pt", "checkpoint_step1000.pt"):
            (Path(td) / n).write_bytes(b"x")
        order = [p.name for p in discover_checkpoints(Path(td))]
    C.append(("discover order best,last,step1000,step2000",
              order == ["checkpoint_best.pt", "checkpoint_last.pt", "checkpoint_step1000.pt", "checkpoint_step2000.pt"]))
    ranked, winner = rank_and_select(
        [{"name": "a", "metrics": {"R2": 0.60, "rmse": 0.15}},
         {"name": "b", "metrics": {"R2": 0.62, "rmse": 0.14}},
         {"name": "nan", "metrics": {"R2": float("nan"), "rmse": 0.1}},
         {"name": "pinf", "metrics": {"R2": float("inf"), "rmse": 0.1}},
         {"name": "ninf", "metrics": {"R2": float("-inf"), "rmse": 0.1}},
         {"name": "none", "metrics": None}], "R2", True)
    C.append(("rank winner=b, NaN/±Inf/None all rejected (never selected)",
              winner["name"] == "b" and not _finite(float("inf")) and not _finite(float("nan"))
              and {r["name"] for r in ranked[:2]} == {"a", "b"}))

    # -- formal mode REFUSES discovery ----------------------------------------
    r = subprocess.run([sys.executable, str(ROOT / "eval/select_b4_checkpoint.py"),
                        "--ckpt-dir", "/tmp/x", "--val-dir", "/tmp/val", "--output-dir", "/tmp/o"],
                       capture_output=True, text=True)
    C.append(("formal selection rejects discovery", r.returncode != 0 and "REFUSED" in (r.stdout + r.stderr)))

    # -- Fix 1: N-target subset mirror = exactly the predicted set -------------
    with tempfile.TemporaryDirectory() as td:
        td = Path(td); pred, val, mir = td / "pred", td / "val", td / "mir"
        for rel in ("29SND/a.nc", "29SND/b.nc", "33TUL/c.nc"):
            _touch(pred / rel); _touch(val / rel)
        _touch(val / "33TUL/extra.nc")                       # val has MORE than predicted
        created, missing = mirror_prediction_targets(pred, val, mir)
        got = sorted(str(p.relative_to(mir)) for p in mir.glob("*/*.nc"))
        pred_set = sorted(str(p.relative_to(pred)) for p in pred.glob("*/*.nc"))
        C.append(("mirror set == prediction set (subset, no full discovery)",
                  got == pred_set and not missing and len(got) == 3))
        # a predicted cube with no source target -> reported missing (smoke refuses)
        _touch(pred / "44XXX/orphan.nc")
        _, missing2 = mirror_prediction_targets(pred, val, mir)
        C.append(("mirror flags predicted cube with no source target", missing2 == ["44XXX/orphan.nc"]))

    hp = contextformer6m_hparams(pvt_pretrained=False)
    model = ObsWorldB4(hp, contract_cfg={"state_dim": 256, "freeze_b0": True}).eval()
    data = fake_data()

    # -- interventions recoverable + distinct ---------------------------------
    model.gate.data.fill_(0.5)
    with torch.no_grad():
        full = model.forecast(data)
        g0, w0 = model.gate.data.clone(), model.transition.net[-1].weight.data.clone()
        with _gate_zero(model):
            p_g0 = model.forecast(data)
        with _t_identity(model):
            p_ti = model.forecast(data)
        restored = torch.equal(model.gate.data, g0) and torch.equal(model.transition.net[-1].weight.data, w0)
    C.append(("interventions restore weights", restored))
    C.append(("gate0 & T-identity change forecast",
              (full - p_g0).abs().max().item() > 1e-6 and (full - p_ti).abs().max().item() > 1e-6))

    # -- donor ONLY affects T (B0 fixed) --------------------------------------
    dA, dB = torch.randn(2, 20, 24), torch.randn(2, 20, 24)
    with torch.no_grad():
        model.gate.data.fill_(0.0)
        b0 = model.forecast_weather(data, "matched")[0]
        pA0, pB0 = _predict_donor(model, data, dA), _predict_donor(model, data, dB)
        model.gate.data.fill_(0.5)
        pA1, pB1 = _predict_donor(model, data, dA), _predict_donor(model, data, dB)
        model.gate.data.fill_(0.0)
    C.append(("donor B0-fixed: gate0 donor==B0 & donors identical",
              (pA0 - b0).abs().max().item() == 0 and (pA0 - pB0).abs().max().item() == 0))
    C.append(("donor changes T output at gate>0", (pA1 - pB1).abs().max().item() > 1e-6))

    # -- Fix 3: season+geo donor schema validator -----------------------------
    C.append(("season_bucket + parse_cube_key + haversine",
              season_bucket(7) == "JJA" and parse_cube_key("29SND/29SND_2018-07-01_x.nc")["tile"] == "29SND"
              and parse_cube_key("29SND/29SND_2018-07-01_x.nc")["start_date"] == (2018, 7, 1)
              and haversine_km((40.0, -4.0), (40.0, -4.0)) == 0.0))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        man, targets = _good_donor_manifest(root)
        C.append(("valid donor manifest -> no errors", validate_donor_manifest(man, targets, root) == [])
                 )
        trel = str(targets[0].relative_to(root))
        # missing schema header
        C.append(("no donor_schema header -> fail closed",
                  any("donor_schema" in e for e in validate_donor_manifest({"pairs": man["pairs"]}, targets, root))))
        # donor==target
        bad = json.loads(json.dumps(man)); bad["pairs"][trel]["donor"] = trel
        C.append(("donor==target flagged", any("donor==target" in e for e in validate_donor_manifest(bad, targets, root))))
        # tile evidence disagrees with filename
        bad = json.loads(json.dumps(man)); bad["pairs"][trel]["target_tile"] = "99ZZZ"
        C.append(("recorded tile != filename flagged",
                  any("target_tile" in e for e in validate_donor_manifest(bad, targets, root))))
        # season mismatch
        bad = json.loads(json.dumps(man)); bad["pairs"][trel]["donor_season"] = "DJF"
        C.append(("season mismatch flagged", any("season mismatch" in e for e in validate_donor_manifest(bad, targets, root))))
        # geo distance inconsistent with centroids
        bad = json.loads(json.dumps(man)); bad["pairs"][trel]["geo_distance_km"] = 0.0
        C.append(("geo distance inconsistent flagged",
                  any("inconsistent" in e for e in validate_donor_manifest(bad, targets, root))))
        # geo over max
        bad = json.loads(json.dumps(man)); bad["donor_schema"]["max_geo_km"] = 1.0
        C.append(("geo over max_geo_km flagged", any("exceeds max_geo_km" in e for e in validate_donor_manifest(bad, targets, root))))
        # uncovered target
        extra = root / "29SND/29SND_2018-07-02_z.nc"; _touch(extra)
        C.append(("uncovered target flagged",
                  any("uncovered" in e for e in validate_donor_manifest(man, targets + [extra], root))))
        # missing evidence keys
        bad = json.loads(json.dumps(man)); bad["pairs"][trel].pop("target_centroid")
        C.append(("missing pair evidence flagged", any("missing evidence" in e for e in validate_donor_manifest(bad, targets, root))))

    # -- Fix 6: frozen guard-config -------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        gp = Path(td) / "guard.json"
        gp.write_text(json.dumps({"threshold": 0.05, "caliber": "diag", "rationale": "x", "frozen_utc": "z"}))
        thr, sha, cfg = _load_guard_config(str(gp))
        ok_valid = thr == 0.05 and len(sha) == 64
        # null threshold -> refuse
        gp.write_text(json.dumps({"threshold": None, "caliber": "d", "rationale": "x", "frozen_utc": "z"}))
        try:
            _load_guard_config(str(gp)); refused_null = False
        except SystemExit:
            refused_null = True
        # missing keys -> refuse
        gp.write_text(json.dumps({"threshold": 0.05}))
        try:
            _load_guard_config(str(gp)); refused_missing = False
        except SystemExit:
            refused_missing = True
    C.append(("guard-config: valid loads, null+missing-keys fail closed", ok_valid and refused_null and refused_missing))

    # -- Fix 4/6: Q4 guard UNSET vs SET_FROZEN + diagnostic field names --------
    ds = FakeDS(2); idx_of = {str(Path(p)): i for i, p in enumerate(ds.filepaths)}
    tg = [Path(p) for p in ds.filepaths]
    q4 = _q4(model, ds, idx_of, tg, dev, None, None, official_overall_R2=0.5)
    part0 = next(iter(q4["train"].values()))
    C.append(("Q4 UNSET => FAIL_CLOSED + diagnostic caliber + gap withheld",
              q4["guard_status"] == "UNSET_FAIL_CLOSED" and "DIAGNOSTIC" in q4["caliber"]
              and part0["guard_verdict"] == "UNSET_FAIL_CLOSED"
              and "diagnostic_endpoint_dir_mse_modelspace" in part0
              and isinstance(part0["diagnostic_path_gap_mse_modelspace"], str)))
    q4s = _q4(model, ds, idx_of, tg, dev, 0.5, "deadbeef", official_overall_R2=0.5)
    C.append(("Q4 SET_FROZEN => PASS/FAIL + records guard sha",
              q4s["guard_status"] == "SET_FROZEN" and q4s["guard_config_sha256"] == "deadbeef"
              and next(iter(q4s["train"].values()))["guard_verdict"] in ("PASS", "FAIL")))

    # -- driver deltas + limit subset + ckpt invariance -----------------------
    dd = _driver_deltas(model, ds, idx_of, tg, dev, "mean")
    C.append(("driver deltas finite", dd["mean_transitioned_state_delta"] >= 0 and dd["mean_endpoint_output_delta"] >= 0))
    C.append(("_targets(limit=2) = first 2",
              [str(p) for p in _targets(SimpleNamespace(limit=2), ds, Path("/fake"))] == ds.filepaths[:2]))

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "b4.pt"
        torch.save({"b4_state_dict": model.state_dict(), "contract_cfg": model.config()}, p)
        sha0 = _sha(p); m2 = load_b4(str(p), "cpu")
        with torch.no_grad(), _gate_zero(m2):
            _ = m2.forecast(data)
        C.append(("checkpoint file byte-unchanged after eval", _sha(p) == sha0))

    C.append(("paired_diff win/tie/loss", (lambda d: d["n"] == 2 and d["win"] == 1 and d["loss"] == 1)(
        _paired_diff({"x": 0.6, "y": 0.5}, {"x": 0.55, "y": 0.52}))))
    C.append(("CPU-only", not torch.cuda.is_available()))

    print("=" * 74)
    allok = True
    for name, ok in C:
        allok &= bool(ok); print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print("-" * 74)
    print(f"RESULT: {'ALL PASS' if allok else 'FAIL'}  ({sum(bool(c[1]) for c in C)}/{len(C)})")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
