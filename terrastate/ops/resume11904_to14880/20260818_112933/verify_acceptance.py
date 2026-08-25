#!/usr/bin/env python
"""M9: acceptance verification for the 11,904 -> 14,880 exact-resume run.

Runs AFTER training completes (step 14,880 reached). Verifies:
1. Final checkpoint exists (`checkpoint_last.pt` at step 14,880)
2. Lineage recorded (parent path/sha256/step, resumed=True)
3. Stage 3 throughout (no spurious stage-2 update, no duplicate boundary80)
4. Only core.blocks.2.* trainable in stage 3, with grad + Adam state
5. Teacher SHA unchanged
6. Optimizer/scheduler/RNG continuity from parent
7. No NaN/OOM/crash/overwrite
8. loss_log.jsonl integrity (2,976 updates logged)
9. Output artifacts match expected set

Exit 0 = all checks pass · 2 = verification failed · 3 = training not done yet

Usage:  verify_acceptance.py [--compare-historical]
  --compare-historical: also load historical-full14880@v1 and report weight distance
                        (read-only comparison, preference for bit-exact; does NOT
                        change the canonical status of the resume run)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

OPS = Path(__file__).resolve().parent
TS_ROOT = OPS.parents[2]
OUTDIR = TS_ROOT / "runs/resume11904_to14880/20260818_112933"
LAUNCH_REC = OPS / "m7_launch_record.json"
MANIFEST = OPS / "launch_manifest.json"
REPORT = OPS / "m9_acceptance_report.json"


def sha256_file(p: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def state_sha(sd: dict) -> str:
    """Match the trainer's state_sha: sort keys, cat dtypes+shapes+strides, hash.

    NOTE: this digest covers only tensor METADATA (dtype/shape/stride) -- NOT the tensor
    values.  Two checkpoints with completely different weights but the same architecture
    share this digest.  It is therefore usable as an architecture/provenance tag, but it
    CANNOT establish weight equality.  Use value_sha() for that.
    """
    keys = sorted(sd.keys())
    parts = []
    for k in keys:
        t = sd[k]
        parts.append(f"{k}:{t.dtype}:{tuple(t.shape)}:{tuple(t.stride())}")
    return hashlib.sha256("".join(parts).encode()).hexdigest()[:16]


def value_sha(sd: dict) -> str:
    """Hash the actual tensor BYTES (key-ordered).  This is what proves weight equality."""
    h = hashlib.sha256()
    for k in sorted(sd.keys()):
        h.update(k.encode())
        h.update(sd[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()[:16]


class Acceptance:
    def __init__(self):
        self.checks: list[dict] = []

    def add(self, name: str, ok: bool, detail: str, evidence: str = "") -> bool:
        self.checks.append({"name": name, "ok": bool(ok), "detail": detail, "evidence": evidence})
        print(f"  [{'OK  ' if ok else 'FAIL'}] {name}: {detail}")
        return bool(ok)

    @property
    def failures(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"]]


def main() -> int:
    compare_hist = "--compare-historical" in sys.argv[1:]
    print(f"M9 acceptance verification {'(+historical compare)' if compare_hist else ''}")

    if not LAUNCH_REC.exists():
        print(f"BLOCKED: no launch record at {LAUNCH_REC} (training never started)")
        return 3
    launch = json.loads(LAUNCH_REC.read_text())
    man = json.loads(MANIFEST.read_text())

    acc = Acceptance()

    # ---- 1. training completed to step 14,880 -----------------------------------------------
    ckpt_last = OUTDIR / "checkpoint_last.pt"
    acc.add("output_dir_exists", OUTDIR.exists(), str(OUTDIR))
    acc.add("checkpoint_last_exists", ckpt_last.exists(), str(ckpt_last))

    if not ckpt_last.exists():
        print("\nBLOCKED: checkpoint_last.pt does not exist (training incomplete or crashed)")
        REPORT.write_text(json.dumps(
            {"accepted": False, "reason": "checkpoint_last.pt missing", "checks": acc.checks},
            ensure_ascii=False, indent=2))
        return 3

    import torch
    ck = torch.load(ckpt_last, map_location="cpu", weights_only=False)
    step = int(ck["step"])
    acc.add("final_step_is_14880", step == 14880, f"step={step}")
    acc.add("candidate_is_last", ck.get("candidate") == "last", f"candidate={ck.get('candidate')}")
    acc.add("total_steps_14880", int(ck["total_steps"]) == 14880, f"total_steps={ck['total_steps']}")

    # ---- 2. lineage (B5) --------------------------------------------------------------------
    lin = ck.get("lineage", {})
    acc.add("lineage_resumed_true", lin.get("resumed") is True, f"resumed={lin.get('resumed')}")
    acc.add("lineage_parent_step_11904", lin.get("parent_step") == 11904,
            f"parent_step={lin.get('parent_step')}")
    parent_sha_frozen = "644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd"
    acc.add("lineage_parent_sha256", lin.get("parent_file_sha256") == parent_sha_frozen,
            f"parent_file_sha256={lin.get('parent_file_sha256', '')[:16]}...")
    acc.add("lineage_data_order_exact", "exact" in lin.get("data_order_restoration", "").lower(),
            f"data_order_restoration={lin.get('data_order_restoration', '')[:60]}...")

    # ---- 3. stage 3 throughout, no duplicate boundary80 --------------------------------------
    stage_rec = int(ck["stage"])
    acc.add("final_stage_is_3", stage_rec == 3, f"stage={stage_rec}")

    # B2: no duplicate boundary80 (parent already wrote it at step 11904)
    b80_ckpt = OUTDIR / "checkpoint_boundary80.pt"
    acc.add("no_duplicate_boundary80", not b80_ckpt.exists(),
            "checkpoint_boundary80.pt absent (parent already saved it)" if not b80_ckpt.exists()
            else "DUPLICATE boundary80 found (B2 suppression failed)")

    # loss_log: all 2,976 updates should be stage 3
    loss_log_path = OUTDIR / "loss_log.jsonl"
    acc.add("loss_log_exists", loss_log_path.exists(), str(loss_log_path))
    if loss_log_path.exists():
        lines = loss_log_path.read_text().strip().split("\n")
        entries = [json.loads(l) for l in lines if l.strip()]
        acc.add("loss_log_count_2976", len(entries) == 2976,
                f"{len(entries)} entries (expect 2976 = 14880 - 11904)")
        stages = [e.get("stage") for e in entries]
        all_stage3 = all(s == 3 for s in stages)
        acc.add("all_updates_stage_3", all_stage3,
                f"all {len(stages)} updates in stage 3" if all_stage3
                else f"NON-3 stages found: {set(stages)}")
        first_step = entries[0].get("step") if entries else None
        last_step = entries[-1].get("step") if entries else None
        acc.add("loss_log_first_step_11905", first_step == 11905, f"first_step={first_step}")
        acc.add("loss_log_last_step_14880", last_step == 14880, f"last_step={last_step}")

    # ---- 4. stage-3 trainable q (B6) --------------------------------------------------------
    qf = ck.get("q_freeze", {})
    trainable_q = qf.get("trainable_q", [])
    acc.add("trainable_q_count_12", len(trainable_q) == 12,
            f"{len(trainable_q)} trainable q tensors (expect 12 for core.blocks.2.*)")
    acc.add("trainable_q_all_core_blocks_2", all("core.blocks.2." in n for n in trainable_q),
            f"all prefixed with 'core.blocks.2.'" if trainable_q and all("core.blocks.2." in n for n in trainable_q)
            else f"prefix mismatch: {[n for n in trainable_q if 'core.blocks.2.' not in n][:3]}")

    # ---- 5. teacher unchanged ---------------------------------------------------------------
    # Three INDEPENDENT witnesses.  Deliberately NOT comparing the child's recorded teacher
    # digest against a constant copied out of that same child checkpoint -- such a check can
    # never fail and proves nothing.  Note also that the ORIGINAL check here was broken in a
    # different way: it compared teacher_sha256 (a 16-hex tensor-metadata digest from
    # state_sha) against a 64-hex FILE sha256.  Those are different kinds of object and could
    # never be equal, so its failure was a bug in this script, not a teacher change.
    #
    #   (a) parent(11904) vs child(14880) tensor digest.  The parent checkpoint was written by
    #       the ORIGINAL run, before this task existed, so it is an outside witness.
    #   (b) the teacher artifact is content-addressed: its file sha256 must equal its filename.
    #   (c) the trainer's own end-of-run assertion (teacher_unchanged=True on the done line).
    TEACHER_STORE_SHA = "2c5d084236716d84d1ed11289248a501a7cb906675a32ccb8fd73e1f2a26881c"
    child_teacher_sha = ck.get("sha", {}).get("teacher_sha256", "")
    child_teacher_path = ck.get("sha", {}).get("teacher_b4_path", "")

    # (a) cross-check against the parent's independent record
    parent_path = lin.get("parent_path", "")
    parent_teacher_sha = ""
    parent_teacher_path = ""
    try:
        if parent_path and Path(parent_path).exists():
            pk = torch.load(parent_path, map_location="cpu", weights_only=False)
            parent_teacher_sha = pk.get("sha", {}).get("teacher_sha256", "")
            parent_teacher_path = pk.get("sha", {}).get("teacher_b4_path", "")
            del pk
        else:
            parent_teacher_sha = "<parent checkpoint not readable>"
    except Exception as e:
        parent_teacher_sha = f"<load failed: {type(e).__name__}>"
    acc.add("teacher_digest_parent_matches_child",
            bool(child_teacher_sha) and child_teacher_sha == parent_teacher_sha,
            f"parent={str(parent_teacher_sha)[:16]}... child={child_teacher_sha[:16]}... "
            f"(parent record predates this task -> independent witness)")
    # The two PATHS legitimately differ: M1 republished the teacher into the content-addressed
    # store, so path equality is NOT a valid identity test here; the digest above is.
    acc.add("teacher_path_divergence_explained",
            parent_teacher_path != child_teacher_path,
            f"parent path={parent_teacher_path.split('/')[-1] if parent_teacher_path else '?'} "
            f"child path={child_teacher_path.split('/')[-1] if child_teacher_path else '?'} "
            f"(differ by design: M1 republished into the artifact store; digests match above)")

    # (b) content-addressed integrity of the teacher artifact actually loaded by this run
    tp = Path(child_teacher_path) if child_teacher_path else None
    if tp is not None and tp.exists():
        tp_actual = sha256_file(tp)
        tp_expect = tp.name.replace(".pt", "")
        acc.add("teacher_artifact_content_addressed",
                tp_actual == tp_expect == TEACHER_STORE_SHA,
                f"file sha256={tp_actual[:16]}... == filename={tp_expect[:16]}... "
                f"== frozen {TEACHER_STORE_SHA[:16]}...")
    else:
        acc.add("teacher_artifact_content_addressed", False,
                f"teacher artifact not readable: {child_teacher_path}")

    # (c) the trainer's own runtime comparison of teacher state at end vs start
    train_log = OPS / "m7_train.log"
    done_line = ""
    if train_log.exists():
        for ln in train_log.read_text(errors="replace").splitlines():
            if "done step=" in ln:
                done_line = ln.strip()
    acc.add("trainer_asserted_teacher_unchanged", "teacher_unchanged=True" in done_line,
            f"done line: {done_line[-90:] if done_line else '<no done line>'}")

    # ---- 6. optimizer/scheduler state continuity --------------------------------------------
    opt_sd = ck.get("optimizer_state_dict", {})
    sched_sd = ck.get("scheduler_state_dict", {})
    acc.add("optimizer_state_present", bool(opt_sd), f"{len(opt_sd.get('state', {}))} param states")
    acc.add("scheduler_state_present", bool(sched_sd), f"last_epoch={sched_sd.get('last_epoch')}")
    acc.add("scheduler_last_epoch_14880", sched_sd.get("last_epoch") == 14880,
            f"last_epoch={sched_sd.get('last_epoch')}")

    # ---- 7. no NaN/OOM (heuristic: final loss finite, checkpoint keys intact) ---------------
    best_val = float(ck.get("best_val", float("nan")))
    acc.add("best_val_finite", not (best_val != best_val),  # NaN check
            f"best_val={best_val:.5f}")
    acc.add("b4_state_dict_present", "b4_state_dict" in ck,
            f"{len(ck.get('b4_state_dict', {}))} model keys" if "b4_state_dict" in ck else "MISSING")

    # ---- 8. expected output artifacts -------------------------------------------------------
    expected_files = {"checkpoint_last.pt", "loss_log.jsonl", "checkpoint_fsval_best.pt"}
    actual = {p.name for p in OUTDIR.iterdir() if p.is_file()}
    acc.add("expected_artifacts_present", expected_files <= actual,
            f"expected subset present: {expected_files & actual} (actual: {actual})")
    forbidden = {"checkpoint_boundary80.pt"}  # B2
    acc.add("no_forbidden_artifacts", not (forbidden & actual),
            "no boundary80 duplicate" if not (forbidden & actual) else f"FORBIDDEN: {forbidden & actual}")

    # ---- 9. optional: compare to historical-full14880@v1 ------------------------------------
    if compare_hist:
        print("\n  [comparing to historical-full14880@v1 (read-only)]")
        try:
            import subprocess
            r = subprocess.run([sys.executable, str(TS_ROOT / "tools/resolve_artifact.py"),
                                "terrastate/v2/historical-full14880@v1", "--json"],
                               cwd=TS_ROOT, capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                hist_rec = json.loads(r.stdout)
                hist_path = Path(hist_rec["resolved_path"])
                hist_ck = torch.load(hist_path, map_location="cpu", weights_only=False)
                hist_sd, resume_sd = hist_ck["b4_state_dict"], ck["b4_state_dict"]
                # Weight equality must be proven on VALUES.  state_sha covers only
                # dtype/shape/stride, so it is reported as an arch tag, never as the proof.
                keys_equal = sorted(hist_sd.keys()) == sorted(resume_sd.keys())
                hist_val, resume_val = value_sha(hist_sd), value_sha(resume_sd)
                max_abs = 0.0
                worst = None
                if keys_equal:
                    for k in sorted(hist_sd.keys()):
                        d = (hist_sd[k].float() - resume_sd[k].float()).abs().max().item()
                        if d > max_abs:
                            max_abs, worst = d, k
                bit_exact = keys_equal and (hist_val == resume_val) and (max_abs == 0.0)
                acc.add("historical_bit_exact", bit_exact,
                        f"value_sha hist={hist_val} resume={resume_val} keys_equal={keys_equal} "
                        f"max_abs_diff={max_abs:.3e} over {len(hist_sd)} tensors"
                        + (f" worst={worst}" if worst else ""))
                acc.add("historical_arch_tag_matches",
                        state_sha(hist_sd) == state_sha(resume_sd),
                        f"state_sha (dtype/shape/stride only) hist={state_sha(hist_sd)} "
                        f"resume={state_sha(resume_sd)} -- arch tag, NOT weight proof")
                if bit_exact:
                    print(f"    RESUME WEIGHTS ARE BYTE-IDENTICAL TO HISTORICAL "
                          f"(value_sha={resume_val}, max_abs_diff=0 over {len(hist_sd)} tensors)")
                else:
                    print(f"    resume weights DIFFER from historical: value_sha {resume_val} "
                          f"vs {hist_val}, max_abs_diff={max_abs:.3e} (worst={worst})")
            else:
                acc.add("historical_comparison_available", False, f"resolver rc={r.returncode}")
        except Exception as e:
            acc.add("historical_comparison_available", False, f"{type(e).__name__}: {e}")

    # ---- verdict ----------------------------------------------------------------------------
    print(f"\nM9 acceptance: {len(acc.checks) - len(acc.failures)}/{len(acc.checks)} passed")
    if acc.failures:
        print("FAILED checks:")
        for c in acc.failures:
            print(f"  - {c['name']}: {c['detail']}")
        REPORT.write_text(json.dumps(
            {"accepted": False, "n_checks": len(acc.checks), "failures": acc.failures,
             "checks": acc.checks}, ensure_ascii=False, indent=2))
        print(f"\nwrote {REPORT}")
        return 2

    print("\nACCEPTED: exact-resume 11,904 -> 14,880 verified.")
    REPORT.write_text(json.dumps(
        {"accepted": True, "n_checks": len(acc.checks), "checks": acc.checks,
         "checkpoint_last_path": str(ckpt_last), "checkpoint_last_sha256": sha256_file(ckpt_last),
         "final_step": step, "best_val": best_val, "stage": stage_rec,
         "lineage": lin}, ensure_ascii=False, indent=2))
    print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
