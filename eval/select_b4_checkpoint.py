#!/usr/bin/env python
"""plan-b-pvt · B4 full-val checkpoint SELECTOR (priority 1, provenance-hardened).

FORMAL selection requires a FROZEN DATA MANIFEST (+dataset-root+split); discovery is
REFUSED in formal mode. --limit is a NON-FORMAL smoke only: it does NOT write a formal
selection.json and does NOT freeze a winner. Selection provenance stores each
candidate's REAL absolute path + SHA256 + data-manifest hash + metrics + commands, and
resume-skip re-verifies that provenance so a stale result from a different checkpoint or
data manifest is never reused.

Reuses eval/export_b4_predictions.py + eval/eval_greenearthnet_official.py (official scorer).
NEVER touches OOD-t.

Formal:  python eval/select_b4_checkpoint.py --ckpt-dir checkpoints/plan_b_b4a \
           --val-dir $DATA_GEN/val_chopped --data-manifest <frozen val manifest> \
           --dataset-root $DATA_GEN --split val --output-dir evaluations/plan_b_b4a_select
Smoke :  ... --limit 8   (NON-formal; no selection.json, no freeze)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _evaluator_commit() -> str:
    """Frozen provenance: repo git short-SHA (best effort) + official scorer commit."""
    try:
        from eval.greenearthnet_protocol import OFFICIAL_EVALUATOR_COMMIT
    except Exception:
        OFFICIAL_EVALUATOR_COMMIT = "unknown"
    git = "nogit"
    try:
        git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip() or "nogit"
    except Exception:
        pass
    return f"repo:{git}+official:{OFFICIAL_EVALUATOR_COMMIT}"


# ---- pure discovery / ranking (unit-testable) --------------------------------
def discover_checkpoints(ckpt_dir: Path) -> list[Path]:
    d = Path(ckpt_dir)
    named = [d / n for n in ("checkpoint_best.pt", "checkpoint_last.pt") if (d / n).is_file()]
    steps = sorted(d.glob("checkpoint_step*.pt"),
                   key=lambda p: int("".join(ch for ch in p.stem if ch.isdigit()) or -1))
    seen, out = set(), []
    for p in named + steps:
        if p.resolve() not in seen:
            seen.add(p.resolve()); out.append(p)
    return out


def _finite(m) -> bool:
    """A selectable metric must be a real, finite number (reject None/NaN/±Inf/bool)."""
    return isinstance(m, (int, float)) and not isinstance(m, bool) and math.isfinite(m)


def rank_and_select(results: list[dict], primary: str = "R2", higher_better: bool = True):
    def key(r):
        m = (r.get("metrics") or {}).get(primary)
        ok = _finite(m)
        rmse = (r.get("metrics") or {}).get("rmse", float("inf"))
        rmse = rmse if _finite(rmse) else float("inf")
        return (0 if ok else 1, -(m if higher_better else -m) if ok else 0.0, rmse)
    ranked = sorted(results, key=key)
    winner = ranked[0] if ranked and _finite((ranked[0].get("metrics") or {}).get(primary)) else None
    return ranked, winner


# ---- N-target subset mirror (unit-testable) ----------------------------------
def mirror_prediction_targets(pred_dir: Path, val_dir: Path, mirror_dir: Path) -> tuple[list[Path], list[str]]:
    """Build a target dir that contains EXACTLY the cubes that were predicted.

    The official scorer maps target ``<region>/<name>.nc`` to prediction
    ``pred_dir/<region>/<name>.nc``. In a NON-formal smoke we export only N cubes,
    so discovery over the full val_dir would list targets with no prediction and
    fail. Instead we mirror (symlink) each PREDICTED cube's source target into
    ``mirror_dir``; discovery over that dir then yields the identical N-set, so
    target-set == prediction-set == N. Returns (created_targets, missing_sources).
    """
    pred_dir, val_dir, mirror_dir = Path(pred_dir), Path(val_dir), Path(mirror_dir)
    if mirror_dir.exists():
        shutil.rmtree(mirror_dir)
    mirror_dir.mkdir(parents=True, exist_ok=True)
    created, missing = [], []
    for pred in sorted(pred_dir.glob("*/*.nc")):
        region, name = pred.parent.name, pred.name
        src = val_dir / region / name
        if not src.is_file():
            missing.append(f"{region}/{name}")
            continue
        link = mirror_dir / region / name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(src.resolve())
        created.append(link)
    return created, missing


EXPORTERS = {"b4": "eval/export_b4_predictions.py",
             "contextformer": "eval/export_contextformer_predictions.py"}


# ---- one candidate: export + official score, with provenance -----------------
def _score_one(py, ckpt: Path, args, data_hash: str, out_dir: Path) -> dict:
    ckpt = ckpt.resolve()
    formal = not args.limit
    prov = {"checkpoint_abs": str(ckpt), "checkpoint_sha256": _sha256(ckpt),
            "data_manifest_sha256": data_hash, "formal": formal, "limit": args.limit,
            "split": args.split, "exporter": args.exporter, "evaluator_commit": _evaluator_commit()}
    cdir = out_dir / ckpt.stem
    pred_dir, score_dir = cdir / "pred", cdir / "score"
    mirror_dir = cdir / "smoke_targets"
    prov_path, metrics_json = cdir / "provenance.json", score_dir / "metrics_en21x.json"
    prov_keys = ("checkpoint_sha256", "data_manifest_sha256", "formal", "limit", "split",
                 "exporter", "evaluator_commit")

    if metrics_json.is_file() and prov_path.is_file():           # resume-skip: FULL provenance must match
        old = json.loads(prov_path.read_text())
        if all(old.get(k) == prov[k] for k in prov_keys):
            return {"name": ckpt.stem, "provenance": old, "skipped": True,
                    "metrics": json.loads(metrics_json.read_text()).get("metrics")}
    if cdir.exists():                                            # stale (any provenance diff) -> wipe whole dir
        shutil.rmtree(cdir)
    pred_dir.mkdir(parents=True, exist_ok=True); score_dir.mkdir(parents=True, exist_ok=True)

    export = [py, EXPORTERS[args.exporter], "--track-dir", args.val_dir,
              "--ckpt", str(ckpt), "--output-dir", str(pred_dir)]
    if args.limit:
        export += ["--limit", str(args.limit)]
    subprocess.run(export, cwd=ROOT, check=True)

    if formal:                                                  # FORMAL -> frozen data manifest, NO discovery
        target_dir = args.val_dir
        man = json.loads(Path(args.data_manifest).read_text())   # forward the manifest's OWN protocol + role
        m_proto = man.get("protocol", "earthnet2021_standard_v1")
        m_role = man.get("role") or man.get("split") or args.split
        score = [py, "eval/eval_greenearthnet_official.py", "--target-dir", target_dir,
                 "--prediction-dir", str(pred_dir), "--output-dir", str(score_dir), "--workers", str(args.workers),
                 "--manifest", args.data_manifest, "--dataset-root", args.dataset_root,
                 "--split", m_role, "--manifest-protocol", m_proto]
    else:                                                       # NON-formal smoke -> score EXACTLY the N exported cubes
        created, missing = mirror_prediction_targets(pred_dir, Path(args.val_dir), mirror_dir)
        if missing or not created:
            raise SystemExit(f"REFUSED smoke: {len(missing)} predicted cubes have no source target "
                             f"(first: {missing[:5]}) — cannot form an identical N-subset.")
        target_dir = str(mirror_dir)
        score = [py, "eval/eval_greenearthnet_official.py", "--target-dir", target_dir,
                 "--prediction-dir", str(pred_dir), "--output-dir", str(score_dir), "--workers", str(args.workers),
                 "--allow-discovery"]
    prov["export_cmd"], prov["score_cmd"] = " ".join(export), " ".join(score)
    subprocess.run(score, cwd=ROOT, check=True)
    prov_path.write_text(json.dumps(prov, indent=2))
    return {"name": ckpt.stem, "provenance": prov, "skipped": False,
            "metrics": json.loads(metrics_json.read_text()).get("metrics")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt-dir", required=True)
    ap.add_argument("--ckpt-manifest", default="", help="explicit CHECKPOINT list (distinct from data manifest)")
    ap.add_argument("--val-dir", required=True, help="val_chopped export track-dir (NEVER ood-t)")
    ap.add_argument("--data-manifest", default="", help="FROZEN data manifest (required for FORMAL selection)")
    ap.add_argument("--dataset-root", default="")
    ap.add_argument("--split", default="val")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--primary-metric", default="R2")
    ap.add_argument("--exporter", choices=sorted(EXPORTERS), default="b4",
                    help="b4 = TerraState (export_b4_predictions); contextformer = B0-FT (export_contextformer_predictions). "
                         "Same official scorer + same prediction tree, so B4 and B0-FT selection are apples-to-apples.")
    ap.add_argument("--lower-better", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="NON-formal smoke on first N cubes (no freeze)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()

    if "ood-t" in args.val_dir or "ood_t" in args.val_dir:
        raise SystemExit("REFUSED: --val-dir looks like OOD-t; selection uses val_chopped only.")
    formal = not args.limit
    if formal and not (args.data_manifest and args.dataset_root):
        raise SystemExit("REFUSED: FORMAL selection needs --data-manifest + --dataset-root (no discovery). "
                         "Use --limit N only for a NON-formal smoke.")
    data_hash = _sha256(Path(args.data_manifest)) if args.data_manifest else "SMOKE_NO_MANIFEST"

    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    if args.ckpt_manifest:
        ckpts = [Path(l.strip()) for l in Path(args.ckpt_manifest).read_text().splitlines() if l.strip()]
    else:
        ckpts = discover_checkpoints(Path(args.ckpt_dir))
    print(f"[select] formal={formal}  {len(ckpts)} candidates: {[c.stem for c in ckpts]}")

    if args.dry_run:
        plan = {"formal": formal, "data_manifest": args.data_manifest or None, "limit": args.limit,
                "primary_metric": args.primary_metric, "candidates": [str(c.resolve()) for c in ckpts]}
        (out / "dry_run_plan.json").write_text(json.dumps(plan, indent=2))
        print(json.dumps(plan, indent=2)); print("[select] DRY RUN"); return 0

    results = []
    for c in ckpts:
        try:
            results.append(_score_one(args.python, c, args, data_hash, out))
        except subprocess.CalledProcessError as e:
            print(f"[select] ERROR scoring {c.stem}: {e}")
            results.append({"name": c.stem, "metrics": None, "error": str(e)})
    n_ok = sum(1 for r in results if (r.get("metrics") is not None))
    if formal and n_ok == 0:                                    # systematic failure must not look like "no winner, ok"
        (out / "ranking.json").write_text(json.dumps(
            {"formal": formal, "primary_metric": args.primary_metric, "data_manifest_sha256": data_hash,
             "ranked": results, "winner": None, "error": "ALL candidates failed to score"}, indent=2))
        raise SystemExit(f"REFUSED: all {len(results)} candidates failed to score (see errors above). "
                         "No selection.json written.")
    ranked, winner = rank_and_select(results, args.primary_metric, not args.lower_better)

    (out / "ranking.json").write_text(json.dumps(
        {"formal": formal, "primary_metric": args.primary_metric, "data_manifest_sha256": data_hash,
         "ranked": ranked, "winner": winner["name"] if winner else None}, indent=2))
    with (out / "ranking.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["rank", "checkpoint", "abs_path", args.primary_metric, "rmse"])
        for i, r in enumerate(ranked):
            m = r.get("metrics") or {}; pv = r.get("provenance") or {}
            w.writerow([i, r["name"], pv.get("checkpoint_abs"), m.get(args.primary_metric), m.get("rmse")])

    if not formal:
        print("[select] SMOKE (--limit): no selection.json, no winner frozen (non-formal).")
        return 0
    if winner:
        (out / "selection.json").write_text(json.dumps(
            {"selected_checkpoint": winner["provenance"]["checkpoint_abs"],
             "selected_sha256": winner["provenance"]["checkpoint_sha256"],
             "data_manifest_sha256": data_hash, "selection_metric": args.primary_metric,
             "exporter": args.exporter,
             "value": (winner["metrics"] or {}).get(args.primary_metric),
             "note": "FORMAL selection on frozen val manifest; OOD-t NOT used"}, indent=2))
        print(f"[select] WINNER {winner['name']} -> {winner['provenance']['checkpoint_abs']}")
    else:
        print("[select] no valid candidate; nothing frozen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
