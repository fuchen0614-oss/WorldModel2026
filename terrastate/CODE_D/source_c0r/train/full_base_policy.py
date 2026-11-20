"""Fixed full-base policies; no dependencies beyond the standard library."""
import math

def lr_factor(step, warmup, total, stage):
    if stage not in ("stage1", "stage2") or warmup != 600:
        raise ValueError("unrecognized stage/schedule")
    if total != (29800 if stage == "stage1" else 74500):
        raise ValueError("stage update budget mismatch")
    step = max(0, min(step, total))
    if step < warmup:
        return step / warmup
    decay_start = 22350 if stage == "stage1" else warmup
    if step <= decay_start:
        return 1.0
    progress = (step - decay_start) / (total - decay_start)
    return 0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2

def configure_stage_args(args):
    first = args.stage == "stage1"
    if first and args.variant != "A":
        raise ValueError("stage1 is one shared parent, use variant A")
    if not args.parent_ckpt or len(args.expected_parent_sha256) != 64 or any(c not in "0123456789abcdef" for c in args.expected_parent_sha256):
        raise ValueError("explicit parent path and SHA256 required")
    if args.allow_unverified_parent:
        raise ValueError("unverified parent is forbidden")
    epochs = 40 if first else 100
    q_lr = 0.0 if first else (1e-5 if args.variant in ("B", "D") else 3e-6)
    branch_lr = 1e-4 if first else 3e-5
    prefixes = "" if first else ("core.blocks.1.,core.blocks.2." if args.variant in ("B", "D") else "core.blocks.2.")
    locked = dict(max_epochs=epochs, branch_lr=branch_lr, q_lr_scale=q_lr / branch_lr,
                  use_adaln=not first and args.variant in ("C", "D"),
                  unfreeze_q_prefixes=prefixes, eo_endpoint_weight=0.0 if first else 1.0,
                  eo_traj_weight=1.0, lr_warmup_steps=600, weight_decay=0.0, grad_clip=1.0,
                  global_batch=32, per_gpu_batch=8)
    for name, value in locked.items():
        old = getattr(args, name)
        if old is not None and old != value:
            raise ValueError(f"{name} conflicts with locked stage policy: {old} != {value}")
        setattr(args, name, value)
    args.stage_epochs = epochs
    args.stage_total_steps = epochs * 745
    if args.max_steps not in (0, args.stage_total_steps):
        raise ValueError("max_steps cannot change stage budget")
    if getattr(args, "config", None):
        validate_config(args)
    runtime_batch = getattr(args, "runtime_per_gpu_batch", None)
    if runtime_batch is not None:
        if args.stage != "stage2" or getattr(args, "runtime_world_size", 4) != 4 or runtime_batch != 4:
            raise ValueError("only stage2 four-rank runtime batch4 override is authorized")
        args.per_gpu_batch = runtime_batch
    return args


def validate_config(args):
    import json
    from pathlib import Path
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    expected = dict(stage=args.stage, variant=args.variant, trainer="train/train_spanworld_full_base.py",
                    global_batch=args.global_batch, world_size=4, per_gpu_batch=args.per_gpu_batch,
                    effective_updates=args.stage_total_steps, epochs_equivalent=args.stage_epochs,
                    branch_peak_lr=args.branch_lr, token_season_lr=0 if args.stage == "stage1" else 3e-5,
                    q_peak_lr=args.branch_lr * args.q_lr_scale,
                    branch_final_lr=args.branch_lr * .1, q_final_lr=args.branch_lr * args.q_lr_scale * .1,
                    token_season_final_lr=0 if args.stage == "stage1" else 3e-6,
                    transition_season_peak_lr=args.branch_lr, transition_season_final_lr=args.branch_lr * .1,
                    adaln_peak_lr=args.branch_lr if args.use_adaln else None,
                    adaln_final_lr=args.branch_lr * .1 if args.use_adaln else None,
                    q_blocks=[] if args.stage == "stage1" else ([1,2] if args.variant in ("B","D") else [2]),
                    adaln=args.use_adaln, traj_weight=args.eo_traj_weight, endpoint_weight=args.eo_endpoint_weight,
                    warmup=600, decay_start=22350 if args.stage == "stage1" else 600, final_factor=.1,
                    selection="val_dev476 official RMSE_LC minimum; first tie",
                    arm=args.arm, factual_path=args.factual_path, seed=args.seed)
    for name, value in expected.items():
        actual = cfg.get(name)
        equal = math.isclose(actual, value, rel_tol=1e-12, abs_tol=0) if type(value) is float and type(actual) in (float,int) else actual == value
        if not equal:
            raise ValueError(f"config {name} mismatch: {actual} != {value}")
    for name, value in (("parent_ckpt", args.parent_ckpt), ("expected_parent_sha256", args.expected_parent_sha256)):
        if cfg.get(name) is not None and cfg[name] != value:
            raise ValueError(f"config {name} mismatch; only null permits CLI binding")


def verify_stage1_completion(parent_path):
    import json
    from pathlib import Path
    path = Path(parent_path)
    if path.name != "best_val.pt":
        raise ValueError("stage2 requires selected stage1 best_val.pt")
    summary = json.loads((path.parent / "summary.json").read_text(encoding="utf-8"))
    if (summary.get("training_stage"), summary.get("completion_reason"), summary.get("step")) != ("stage1", "schedule_complete", 29800):
        raise ValueError("stage1 schedule has not completed")
    best = summary.get("best_val_dev_RMSE_LC")
    if not isinstance(best, dict) or not math.isfinite(best.get("score", float("nan"))) or not 0 < best.get("step", 0) <= 29800:
        raise ValueError("stage1 selected best metadata invalid")
    return best


def validate_execution_request(args, cuda_available, production=True):
    """No silent CUDA-to-CPU fallback; diagnostic injection bypasses only formal gates."""
    if str(args.device).startswith("cuda") and not cuda_available:
        raise RuntimeError("CUDA requested but unavailable; refusing CPU fallback")
    if production and (not args.config or not args.verify_data_manifest):
        raise ValueError("formal CLI requires --config and --verify-data-manifest")


def wait_for_holder_handoff(directory, token, rank, step, timeout=120.0):
    """Optional one-time handshake only; never signals or stops another process."""
    if not directory:
        return
    if not token or timeout <= 0:
        raise ValueError("handoff requires token and positive timeout")
    import os, json, time
    from pathlib import Path
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    ready = root / f"ready_rank_{rank}.json"
    staged = root / f"ready_rank_{rank}.{os.getpid()}.tmp"
    staged.write_text(json.dumps(dict(rank=rank,pid=os.getpid(),step=step,token=token)),encoding="utf-8")
    staged.replace(ready)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        release = root / "RELEASE"
        if release.exists():
            document = json.loads(release.read_text(encoding="utf-8"))
            if document.get("token") != token:
                raise ValueError("handoff RELEASE token mismatch")
            return
        time.sleep(min(.1, max(0, deadline-time.monotonic())))
    raise TimeoutError("holder handoff RELEASE timeout")
