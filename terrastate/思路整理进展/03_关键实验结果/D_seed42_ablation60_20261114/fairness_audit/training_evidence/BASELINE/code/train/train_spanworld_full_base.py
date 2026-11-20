#!/usr/bin/env python
"""Isolated full-base two-stage training; fixed effective-update budgets."""

import argparse
import json
import os
import sys
import time
from contextlib import nullcontext
from pathlib import Path

import multiprocessing.util as _mp_util
def _spanworld_ipc_dir():
    directory = Path("/dev/shm/spanworld_c1_ipc")
    directory.mkdir(mode=0o700, exist_ok=True)
    return str(directory)
_mp_util.get_temp_dir = _spanworld_ipc_dir

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler, Subset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.encoders.pvt_contextformer_q import contextformer6m_hparams  # noqa: E402
from models.terrastate_candidate_c import (  # noqa: E402
    PARENT_ALIAS, SIMULATOR_STATUS, TerraStateCandidateC, sha256_file,
    value_sha16, warm_start_candidate_c,
)
from train.terrastate_v2_common import (  # noqa: E402
    atomic_torch_save, canonical_json_sha256, capture_rng_state, collate_with_ids,
    data_manifest_sha256, log, relpath_of, restore_rng_state, seed_everything,
    seed_worker, state_sha, to_device_with_ids,
)
# 直接复用 V2 的 schedule 数学，保证两代之间 warmup+cosine 逐位同一实现。
from train.full_base_policy import lr_factor, configure_stage_args, verify_stage1_completion, validate_execution_request, wait_for_holder_handoff  # noqa: E402

STOP_FLAG_NAME = "STOP_AFTER_CHECKPOINT"
CKPT_GLOB = "*.pt"


def is_dist() -> bool:
    return dist.is_available() and dist.is_initialized()


def rank0() -> bool:
    return int(os.environ.get("LOCAL_RANK", 0)) == 0


def guard_output_dir(out: Path, allow_existing: bool) -> None:
    """绝不在已有 run 的 checkpoint 上再写一个 run。init_process_group 之前检查，
    所有 rank 同样地失败，不会有单 rank raise 导致其余 rank 卡在集合通信。"""
    if allow_existing or not out.exists():
        return
    existing = sorted(p.name for p in out.glob(CKPT_GLOB))
    if existing:
        raise FileExistsError(
            f"output-dir {out} 已含 {len(existing)} 个 checkpoint：{existing[:5]}"
            f"{'...' if len(existing) > 5 else ''}。拒绝写入（历史结果绝不可被覆盖）。"
            f"请换全新 --output-dir。")


def endpoint_rng(seed: int, step: int) -> torch.Generator:
    """端点计划的 RNG = (seed, step) 的纯函数。

    这样做的三个理由：
      1. C1 与 C0R 在同一 step 上抽到同一组端点（对照臂唯一差别只剩路径）；
      2. 不需要把这条 RNG 的状态写进 checkpoint 也能 exact resume；
      3. 所有 rank 抽到相同计划，不引入 rank 间不一致。
    """
    g = torch.Generator()
    g.manual_seed(int(seed) * 1_000_003 + int(step))
    return g


from train.train_terrastate_candidate_c import build_optimizer, validate_resume_candidate


def apply_phase_ii_freeze(raw, unfreeze_prefixes):
    """Phase-II 沿用父 checkpoint 结束时（stage 3）的冻结集合：q 仅解冻
    unfreeze_prefixes 命中的张量，freeze_b0=False 让梯度能过 context-only prior。
    两臂必须相同，否则容量/可训练集不同就不再是单变量对照。"""
    for p in raw.q.parameters():
        p.requires_grad_(False)
    matched = []
    for name, p in raw.q.named_parameters():
        if any(name.startswith(pre) for pre in unfreeze_prefixes):
            p.requires_grad_(True)
            matched.append(name)
    if not matched:
        raise RuntimeError(f"Phase-II: 没有 q 张量匹配 {unfreeze_prefixes}")
    raw.freeze_b0 = False
    return sorted(matched)


def poll_cooperative_stop(out: Path, dev) -> bool:
    """rank0 看文件，broadcast 给全体。绝不让各 rank 各自看盘：NFS 可见性不同步会
    导致一部分 rank 进入保存分支、另一部分继续训练，直接在集合通信上挂死。"""
    flag = 1.0 if (rank0() and (out / STOP_FLAG_NAME).exists()) else 0.0
    if not is_dist():
        return flag > 0.5
    t = torch.tensor([flag], device=dev, dtype=torch.float32)
    dist.broadcast(t, src=0)
    return t.item() > 0.5


def _dig(obj, dotted: str):
    """点号选择器；缺键直接 KeyError（fail-closed，绝不静默返回错的 ID 列表）。"""
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(f"选择器 {dotted!r} 在 {part!r} 处不存在")
        cur = cur[part]
    return cur


def subset_by_id_list(ds, root, id_list, name: str):
    """按冻结的 relpath ID 列表取子集。要求列表中每个 ID 都在数据集中命中，
    且命中数 == 列表长度；否则抛错而不是静默用一个更小的 split 评测。"""
    want = set(id_list)
    if len(want) != len(id_list):
        raise ValueError(f"{name}: ID 列表内部有重复")
    idx, seen = [], set()
    for i, fp in enumerate(ds.filepaths):
        rp = relpath_of(str(fp), root)
        if rp in want:
            idx.append(i)
            seen.add(rp)
    missing = sorted(want - seen)
    if missing:
        raise ValueError(
            f"{name}: 冻结 ID 列表有 {len(missing)} 个在数据集中找不到，"
            f"例如 {missing[:5]}。split 不完整则不得用于任何选择或门。")
    if len(idx) != len(id_list):
        raise ValueError(f"{name}: 命中 {len(idx)} != 列表长度 {len(id_list)}")
    return Subset(ds, idx)


def load_val_split(path: str, selector: str):
    blob = json.loads(Path(path).read_text())
    ids = _dig(blob, selector)
    if not isinstance(ids, list) or not ids:
        raise ValueError(f"{path}::{selector} 不是非空列表")
    return [str(x) for x in ids], blob


def _gather_rng():
    st = capture_rng_state()
    if not is_dist():
        return [st]
    out = [None for _ in range(dist.get_world_size())]
    dist.all_gather_object(out, st)
    return out


from train.c1_validation import aggregate, improved, score_file
from train.topology_migration import commit, reconcile


@torch.no_grad()
def validate_candidate_c(model, loader, dev, expected):
    raw = model.module if hasattr(model, "module") else model
    raw.eval()
    local = []
    nonfinite = False
    try:
        for batch in loader:
            data = to_device_with_ids(batch, dev)
            prediction = raw.forecast(data)
            nonfinite |= not bool(torch.isfinite(prediction).all())
            if nonfinite:
                continue
            for path, cube in zip(batch["filepath"], prediction[:, :, 0].cpu().numpy()):
                local.append((path, score_file(path, cube, raw.context_len)))
    finally:
        raw.train()
    partitions = [(local, nonfinite)]
    if is_dist():
        partitions = [None] * dist.get_world_size()
        dist.all_gather_object(partitions, (local, nonfinite))
    if any(invalid for _, invalid in partitions):
        return None, "nonfinite_prediction"
    return aggregate(expected, [rows for rows, _ in partitions])


def make_checkpoint(raw, opt, sched, *, epoch, step, micro_in_epoch, total_steps, accum,
                    world, global_batch, shas, args, gathered_rng, lineage,
                    trainable_q, unfreeze_prefixes, best_val, completion_reason,
                    lambdas, endpoint_plan_note):
    """完整 exact-resume schema。phase_step 就是 step（本 phase 从 0 开始计）。"""
    return {
        "arch": raw.ARCH, "route_version": raw.ROUTE_VERSION,
        "training_stage": args.stage, "variant": args.variant,
        "b4_state_dict": raw.state_dict(), "contract_cfg": raw.config(),
        "experiment": "baseline_only_retrain", "planned_stop_step": args.stop_after_step,
        "optimizer_state_dict": opt.state_dict(),
        "scheduler_state_dict": sched.state_dict(),
        "scaler": {"enabled": False, "state": None, "note": "FP32 训练；GradScaler 关闭"},
        "epoch": epoch, "step": step, "phase_step": step, "micro_in_epoch": micro_in_epoch,
        "phase": "candidate_c_phase_ii",
        "arm": args.arm, "factual_path": raw.factual_path,
        "q_freeze": {"trainable_q": trainable_q, "unfreeze_prefixes": unfreeze_prefixes},
        "rng_state": capture_rng_state(), "rng_states_by_rank": gathered_rng,
        "best_val": best_val,
        "total_steps": total_steps, "accum": accum, "world_size": world,
        "global_batch": global_batch, "runtime_topology": {"world_size":world,"per_gpu_batch":args.per_gpu_batch,"accum":accum,"global_batch":global_batch}, "alpha": None,
        "lambdas": dict(lambdas),
        "endpoint_plan_note": endpoint_plan_note,
        "completion_reason": completion_reason,
        "sha": shas, "args": vars(args), "lineage": dict(lineage or {}),
        "simulator_status": SIMULATOR_STATUS,
        "selection_note": (
            "Select by val_dev official RMSE_LC; ties preserve the first epoch."
            "调参与观察只允许用 val_dev；val_locked 仅作最终门，OOD/test 本轮不开。"),
        "not_exact_resume_of_parent": (
            "本 run 是共同 stage1 的 q-only weights-only fork：新 optimizer / "
            "新 scheduler / 新 RNG / phase_step 从 0 开始。父 optimizer 与 scheduler "
            "状态被故意丢弃，绝不可称为 exact resume。"),
    }


def accumulation_batches(loader, accum, raw, dev, plan_factory, window_supervision):
    """Prefetch CPU batches only; never retain multiple forward graphs."""
    if not window_supervision:
        for batch in loader:
            yield batch, None, None
        return
    from itertools import islice
    from models.losses.supervision_v2 import supervision_counts
    iterator = iter(loader)
    while True:
        window = list(islice(iterator, accum))
        if not window:
            return
        plan = plan_factory()
        counts = sum((supervision_counts(batch, raw.context_len, raw.target_len,
                                        raw.lc_min, raw.lc_max, plan) for batch in window)).to(dev)
        if is_dist():
            dist.all_reduce(counts, op=dist.ReduceOp.SUM)
        for batch in window:
            yield batch, counts, plan


_RUN_PROGRESS_WRITER = None

def run_training(args, dataset_factory=None) -> dict:
    global _RUN_PROGRESS_WRITER
    _RUN_PROGRESS_WRITER = None
    try:
        return _run_training(args, dataset_factory)
    finally:
        if _RUN_PROGRESS_WRITER is not None:
            _RUN_PROGRESS_WRITER.flush()

def _run_training(args, dataset_factory=None) -> dict:
    global _RUN_PROGRESS_WRITER
    validate_execution_request(args, torch.cuda.is_available(), production=dataset_factory is None)
    args = configure_stage_args(args)
    """`dataset_factory(split, dir) -> Dataset` 是测试缝（DDP smoke 注入合成数据集），
    不改变 model / loss / schedule / 契约。"""
    if dataset_factory is None:
        from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
        dataset_factory = lambda split, d: GreenEarthNetContextformerDataset(d, dl_cloudmask=True)

    if args.arm not in ("BASELINE",):
        raise ValueError(f"--arm 只允许 C1 或 C0R，收到 {args.arm!r}。C0S 本轮不得伪造。")
    expect_path = {"BASELINE": "direct"}[args.arm]
    if args.factual_path != expect_path:
        raise ValueError(
            f"--arm {args.arm} 要求 --factual-path {expect_path}，收到 {args.factual_path!r}。")
    if float(args.lambda_pair) != 0.0:
        raise ValueError(f"λ_pair 必须为 0：{SIMULATOR_STATUS}")
    if args.continuation_manifest and (not args.resume or args.migration_checkpoint):
        raise ValueError("continuation requires resume and forbids topology migration")
    if args.stop_after_step < 0:
        raise ValueError("--stop-after-step 必须 >= 0")
    if args.migration_checkpoint and args.resume:
        raise ValueError("migration and exact resume are mutually exclusive")
    if args.migration_checkpoint and args.allow_existing_out:
        raise ValueError("migration requires a new output directory")
    guard_output_dir(Path(args.output_dir), args.allow_existing_out)

    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    world = int(os.environ.get("WORLD_SIZE", 1))
    # All ranks must construct the same temporary warm-start weights before provenance checks.
    # Rank0 initialization is unchanged; migration reseeds ranks only after state restoration.
    seed_everything(args.seed)
    use_cuda = torch.cuda.is_available() and args.device != "cpu"
    if world > 1:
        if use_cuda:
            torch.cuda.set_device(local_rank)
        dist.init_process_group("nccl" if use_cuda else "gloo")
    dev = torch.device("cuda", local_rank) if use_cuda else torch.device("cpu")
    out = Path(args.output_dir)
    from train.progress_io import ProgressWriter
    progress_writer = ProgressWriter(out, every_steps=10, max_seconds=10.0)
    _RUN_PROGRESS_WRITER = progress_writer
    if rank0():
        out.mkdir(parents=True, exist_ok=True)

    # ---- 模型 + weights-only warm start ------------------------------------------
    hp = contextformer6m_hparams(pvt_pretrained=False)
    ccfg = {"use_adaln": args.use_adaln, "supervision_v2": True, "state_dim": args.state_dim, "freeze_b0": False,
            "factual_path": args.factual_path,
            "days_per_transition_step": args.days_per_transition_step,
            "use_future_state_anchor": False,
            "eo_traj_weight": args.eo_traj_weight,
            "eo_endpoint_weight": args.eo_endpoint_weight}
    from models.spanworld_full_base import SpanWorldFullBase, load_official_baseline, load_stage1_parent, initialize_stage1
    ccfg.update(training_stage=args.stage, variant=args.variant)
    from models.spanworld_baseline_only import SpanWorldBaselineOnly, load_stage1_base_only
    assert args.stage == "stage2" and args.variant == "D" and args.stop_after_step == 44700
    model_cpu = SpanWorldBaselineOnly(hp, contract_cfg=ccfg)
    model_cpu.history_state_only = args.history_state_only
    # The verified parent contains NumPy 2 RNG pickle names. Its RNG is discarded.
    import numpy as np
    if not hasattr(np, "_core"):
        sys.modules.setdefault("numpy._core", np.core)
        sys.modules.setdefault("numpy._core.multiarray", np.core.multiarray)
    if args.stage == "stage1":
        report = load_official_baseline(model_cpu, args.parent_ckpt,
                                       expected_sha256=args.expected_parent_sha256)
        initialize_stage1(model_cpu)
        inherited = {k: v for k, v in model_cpu.q.core.state_dict().items() if k not in report["missing"]}
    else:
        parent_best = verify_stage1_completion(args.parent_ckpt)
        if sha256_file(args.parent_ckpt) != args.expected_parent_sha256:
            raise ValueError("stage1 parent SHA mismatch")
        parent_metadata = torch.load(args.parent_ckpt, map_location="cpu", weights_only=False)
        if parent_metadata.get("rmse_best") != parent_best or parent_metadata.get("step") != parent_best["step"]:
            raise ValueError("stage1 best checkpoint and completed summary disagree")
        del parent_metadata
        report = load_stage1_base_only(model_cpu, args.parent_ckpt,
                                   expected_sha256=args.expected_parent_sha256)
        inherited = {k: v for k, v in model_cpu.state_dict().items() if k not in report["missing"]}
    inherited_sha = value_sha16(inherited)
    lineage = dict(parent_alias="explicit_full_baseline" if args.stage == "stage1" else "selected_stage1",
                   parent_file_sha256=sha256_file(args.parent_ckpt), parent_value_sha16=inherited_sha,
                   inherited_value_sha16=inherited_sha, inherited_n_tensors=report["inherited_tensors"],
                   max_abs_diff_vs_parent=0.0, missing_keys=report["missing"], unexpected_keys=[],
                   parent_logical_id=str(Path(args.parent_ckpt).resolve()), parent_path=args.parent_ckpt,
                   fork_kind="weights_only_base_subset_" + args.stage, is_exact_resume=False,
                   parent_optimizer_scheduler_deliberately_discarded=True)
    student = model_cpu.to(dev)
    log(f"warm-start OK: 继承 {lineage['inherited_n_tensors']} 张量，"
        f"value_sha={lineage['inherited_value_sha16']}，"
        f"max_abs_diff={lineage['max_abs_diff_vs_parent']}，"
        f"missing={len(lineage['missing_keys'])} unexpected={len(lineage['unexpected_keys'])}")
    log(f"  fork_kind={lineage['fork_kind']} is_exact_resume={lineage['is_exact_resume']} "
        f"phase_step=0 父 optimizer/scheduler 已丢弃="
        f"{lineage['parent_optimizer_scheduler_deliberately_discarded']}")

    unfreeze_prefixes = [s for s in args.unfreeze_q_prefixes.split(",") if s]
    if args.stage == "stage1":
        for param in student.q.parameters():
            param.requires_grad_(False)
        student.freeze_b0 = True
        trainable_q = []
    else:
        unfreeze_prefixes.append("core.season_proj.")
        trainable_q = apply_phase_ii_freeze(student, unfreeze_prefixes)
    # ---- 数据 --------------------------------------------------------------------
    train_ds = dataset_factory("train", args.train_dir)
    val_full = dataset_factory("val", args.val_dir)
    val_ids, split_blob = load_val_split(args.val_split_manifest, args.val_split_selector)
    val_ds = subset_by_id_list(val_full, args.val_dir, val_ids, args.val_split_selector)
    log(f"val split {args.val_split_selector}: {len(val_ds)} cubes（全 val {len(val_full)}）")
    if args.val_split_selector.endswith("val_locked.ids"):
        raise ValueError("训练期禁止把 val_locked 作为观察 split；它只作最终门。")

    expected = [str(val_full.filepaths[i]) for i in val_ds.indices]
    if len(train_ds) != 23816 or len(expected) != 476:
        raise ValueError("frozen train/val_dev counts changed")
    if sha256_file(args.val_split_manifest) != "160c3ccc5075d386ecdc235a61806610d8475cc46f17973b94a5a9a37ed3cd6b":
        raise ValueError("val split manifest changed")
    shuffle = not args.deterministic
    sampler = DistributedSampler(train_ds, shuffle=shuffle, seed=args.seed) if world > 1 else None
    gen = torch.Generator(); gen.manual_seed(args.seed)
    loader = DataLoader(train_ds, batch_size=args.per_gpu_batch, sampler=sampler,
                        shuffle=(sampler is None and shuffle), num_workers=args.num_workers,
                        collate_fn=collate_with_ids, pin_memory=use_cuda, drop_last=False,
                        generator=gen, worker_init_fn=seed_worker)
    val_sampler = DistributedSampler(val_ds, shuffle=False, drop_last=False) if world > 1 else None
    val_loader = DataLoader(val_ds, batch_size=args.per_gpu_batch, sampler=val_sampler,
                            shuffle=False, num_workers=args.num_workers,
                            collate_fn=collate_with_ids, pin_memory=use_cuda)

    # ---- global batch / accumulation ---------------------------------------------
    denom = args.per_gpu_batch * world
    if args.global_batch % denom != 0:
        raise ValueError(f"--global-batch {args.global_batch} 不能被 per_gpu"
                         f"({args.per_gpu_batch}) x world({world}) 整除")
    accum = args.global_batch // denom
    updates_per_epoch = max((len(loader) + accum - 1) // accum, 1)
    total_steps = args.max_steps if args.max_steps > 0 else args.max_epochs * updates_per_epoch
    stop_after_step = args.stop_after_step if args.stop_after_step > 0 else total_steps
    if world != args.runtime_world_size or world not in (2, 4):
        raise ValueError("world differs from explicit runtime topology")
    if args.stage == "stage2" and (world, args.per_gpu_batch, accum) not in ((4,8,1),(4,4,2)):
        raise ValueError("stage2 runtime must be 4x8x1 or approved 4x4x2")
    if (args.arm in ("BASELINE",), args.seed in (27, 42, 97), world, args.per_gpu_batch,
        accum, updates_per_epoch, total_steps, args.max_epochs) != (
        True, True, args.runtime_world_size, args.per_gpu_batch, 32 // (args.runtime_world_size * args.per_gpu_batch), 745, args.stage_total_steps, args.stage_epochs
    ):
        raise ValueError("unexpected C1 budget")
    if stop_after_step > total_steps:
        raise ValueError(f"--stop-after-step {stop_after_step} 超过计划 total_steps {total_steps}")
    log(f"arm={args.arm} factual_path={args.factual_path} world={world} "
        f"per_gpu={args.per_gpu_batch} accum={accum} global_batch={args.global_batch} "
        f"updates/epoch={updates_per_epoch} total_steps={total_steps} "
        f"stop_after_step={stop_after_step}")

    lambdas = {"z": float(args.lambda_z), "y": float(args.lambda_y),
               "pair": float(args.lambda_pair), "nc": float(args.lambda_nc)}
    from types import SimpleNamespace
    lam_ns = SimpleNamespace(**lambdas)
    if args.arm in ("BASELINE",) and any(v != 0.0 for v in lambdas.values()) and not args.allow_nonzero_lambdas:
        raise ValueError(
            f"正式臂 {args.arm} 要求四个 λ 全为 0，收到 {lambdas}。"
            f"smoke/pilot 若确需非零请显式加 --allow-nonzero-lambdas，并且结果不得写成正式结果。")
    log(f"λ = {lambdas}（正式臂应全 0；λ_pair 恒被阻塞：{SIMULATOR_STATUS}）")

    # ---- optimizer / scheduler：全新 ---------------------------------------------
    opt = build_optimizer(student, args.branch_lr, args.q_lr_scale, args.weight_decay)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lr_lambda=lambda s: lr_factor(s, args.lr_warmup_steps, total_steps, args.stage))
    for g in opt.param_groups:
        log(f"  opt '{g['name']}': tensors={len(g['params'])} base_lr={g['lr']:.2e}")
    # ---- provenance：每份 checkpoint 都带 ----------------------------------------
    shas = {
        "parent_alias": lineage["parent_alias"],
        "parent_logical_id": lineage["parent_logical_id"],
        "parent_file_sha256": lineage["parent_file_sha256"],
        "parent_value_sha16": lineage["parent_value_sha16"],
        "inherited_value_sha16": lineage["inherited_value_sha16"],
        "warm_start_state_sha256": state_sha(student.state_dict()),
        "val_split_manifest_path": args.val_split_manifest,
        "val_split_manifest_sha256": sha256_file(args.val_split_manifest),
        "val_split_selector": args.val_split_selector,
        "val_split_n_ids": len(val_ids),
        "selection_metric": "GreenEarthNet RMSE_LC HQ",
        "scorer_reference_sha256": "cfbc6722174981daeabd880e27afaa90dce0de11269ecbba8365fe54de29bd2f",
        "q4_partition_manifest_path": args.q4_partition_manifest or "",
        "q4_partition_manifest_sha256": (sha256_file(args.q4_partition_manifest)
                                        if args.q4_partition_manifest else ""),
        "selected_config_sha256": sha256_file(args.config) if args.config else None,
        "selected_config_content": json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else None,
        "config_sha256": canonical_json_sha256({k: v for k, v in vars(args).items() if k not in {"resume", "allow_existing_out", "handoff_dir", "handoff_token", "handoff_timeout", "continuation_manifest"} and not k.startswith("migration_")}),
        "source_sha256": {
            rel: sha256_file(ROOT / rel) for rel in (
                "models/spanworld_baseline_only.py",
                "train/baseline_startup_check.py",
                "models/terrastate_candidate_c.py",
                "train/train_spanworld_full_base.py",
                "train/full_base_policy.py",
                "train/efficiency_continuation.py",
                "train/progress_io.py",
                "models/encoders/pvt_contextformer_q.py",
                "train/topology_migration.py",
                "models/spanworld_full_base.py",
                "train/train_terrastate_candidate_c.py",
                "models/losses/supervision_v2.py",
                "models/encoders/contextformer_official.py",
                "data/calendar_features.py",
                "data/weather_contract.py",
                "data/greenearthnet_contextformer_dataset.py",
                "train/c1_validation.py",
                "train/c1_checkpoint.py",
                "models/terrastate_v2.py",
                "models/plan_b_b4_exclusive.py",
                "models/plan_b_b4.py",
                "train/train_terrastate_v2.py",
                "train/terrastate_v2_common.py",
            ) if (ROOT / rel).is_file()
        },
    }
    if args.verify_data_manifest:
        tr_sha = data_manifest_sha256([str(p) for p in train_ds.filepaths], args.train_dir)
        va_sha = data_manifest_sha256([str(p) for p in val_full.filepaths], args.val_dir)
        shas["train_manifest_sha256"] = tr_sha
        shas["val_manifest_sha256"] = va_sha
        if args.expect_train_manifest_sha and tr_sha != args.expect_train_manifest_sha:
            raise ValueError(f"train data manifest SHA {tr_sha} != 冻结值 "
                             f"{args.expect_train_manifest_sha}。EO 样本集变了，FAIL CLOSED。")
        if args.expect_val_manifest_sha and va_sha != args.expect_val_manifest_sha:
            raise ValueError(f"val data manifest SHA {va_sha} != 冻结值 "
                             f"{args.expect_val_manifest_sha}。FAIL CLOSED。")
        log(f"data manifest 校验通过：train={tr_sha[:16]} val={va_sha[:16]}")
    else:
        shas["train_manifest_sha256"] = ""
        shas["val_manifest_sha256"] = ""
        shas["data_manifest_note"] = "未校验（--verify-data-manifest 关闭）；正式 run 必须开启"

    endpoint_plan_note = (
        "端点计划 RNG = (seed, step) 的纯函数（endpoint_rng），因此 C1 与 C0R 在同一 step "
        "抽到同一组端点，且无需把该 RNG 状态写进 checkpoint 即可 exact resume。"
        "direct 臂照样抽一次索引后丢弃多段划分、改用 (endpoint,)，保证两臂 RNG 流逐位一致。")

    # ---- resume（本 phase 内的 exact resume；与父 fork 是两回事）------------------
    start_epoch, step, resume_micro = 0, 0, 0
    best_val = None
    validation_history = []
    if args.resume:
        rk = torch.load(args.resume, map_location="cpu", weights_only=False)
        continuation = None
        if args.continuation_manifest:
            from train.efficiency_continuation import validate_continuation
            continuation = validate_continuation(rk, args, shas, world, accum)

        if rk.get("training_stage") != args.stage or rk.get("variant") != args.variant:
            raise ValueError("resume stage/variant mismatch")
        if rk.get("arch") != student.ARCH:
            raise ValueError(f"resume arch 不符：{rk.get('arch')} != {student.ARCH}")
        if rk.get("experiment") != "baseline_only_retrain" or rk.get("planned_stop_step") != args.stop_after_step:
            raise ValueError("resume experiment/stop mismatch")
        if rk.get("arm") != args.arm:
            raise ValueError(f"resume arm 不符：{rk.get('arm')} != {args.arm}")
        if rk.get("factual_path") != args.factual_path:
            raise ValueError(f"resume factual_path 不符：{rk.get('factual_path')} != {args.factual_path}")
        if int(rk["total_steps"]) != total_steps:
            raise ValueError("resume total_steps 不符（schedule 变了）")
        if int(rk["global_batch"]) != args.global_batch or (int(rk["accum"]) != accum and continuation is None):
            raise ValueError("resume global_batch/accum 不符")
        for key in ("parent_file_sha256", "inherited_value_sha16", "val_split_manifest_sha256"):
            if rk["sha"].get(key) != shas.get(key):
                raise ValueError(f"resume {key} 不符：{rk['sha'].get(key)} != {shas.get(key)}")
        if dict(rk.get("lambdas") or {}) != lambdas:
            raise ValueError(f"resume λ 不符：{rk.get('lambdas')} != {lambdas}")
        validate_resume_candidate(rk, opt.param_groups, sched.base_lrs, unfreeze_prefixes, student.use_adaln)
        student.load_state_dict(rk["b4_state_dict"], strict=True)
        opt.load_state_dict(rk["optimizer_state_dict"])
        sched.load_state_dict(rk["scheduler_state_dict"])
        step = int(rk["step"]); start_epoch = int(rk["epoch"])
        resume_micro = int(rk["micro_in_epoch"])
        best_val = rk["rmse_best"]
        validation_history = rk["validation_history"]
        if (rk["sha"] != shas and continuation is None) or len(rk["rng_states_by_rank"]) != world:
            raise ValueError("resume provenance/world differs")
        if resume_micro != 0:
            raise ValueError("resume only from committed epoch boundaries")
        if continuation is None and Path(args.resume).resolve() != (out / "last.pt").resolve():
            raise ValueError("resume requires this run's last.pt")
        if continuation is not None and is_dist():
            dist.barrier()  # All ranks finish pristine-output validation before rank0 copies best.
        if rank0():
            if continuation is None:
                reconcile(out, out / "last.pt", rk)
            else:
                from train.c1_checkpoint import copy_atomic
                copy_atomic(continuation["inherited_best"]["source_path"], out / "best_val.pt")
        if is_dist():
            dist.barrier()
        rng_by_rank = rk.get("rng_states_by_rank") or [rk["rng_state"]]
        restore_rng_state(rng_by_rank[min(local_rank, len(rng_by_rank) - 1)])
        lineage = dict(rk.get("lineage") or lineage)
        if continuation is not None:
            lineage["efficiency_continuation"] = continuation
        lineage["resumed_within_phase"] = True
        lineage["resume_parent_path"] = str(Path(args.resume).resolve())
        lineage["resume_parent_file_sha256"] = sha256_file(args.resume)
        log(f"RESUME(phase 内) step={step} epoch={start_epoch} micro={resume_micro} "
            f"best_val={best_val}")
    if args.migration_checkpoint:
        from train.topology_migration import verified_load, validate_migration, validate_best
        from train.c1_checkpoint import copy_atomic
        rk = verified_load(args.migration_checkpoint, args.migration_checkpoint_sha256)
        bk = verified_load(args.migration_best, args.migration_best_sha256)
        if Path(args.output_dir).resolve() in (Path(args.migration_checkpoint).resolve().parent, Path(args.migration_best).resolve().parent):
            raise ValueError("migration must use an independent output directory")
        validate_migration(rk, vars(args), shas, world, accum)
        validate_best(rk, bk)
        if rk["arch"] != student.ARCH or rk["contract_cfg"] != student.config():
            raise ValueError("migration model contract differs")
        validate_resume_candidate(rk, opt.param_groups, sched.base_lrs, unfreeze_prefixes, student.use_adaln)
        student.load_state_dict(rk["b4_state_dict"], strict=True)
        opt.load_state_dict(rk["optimizer_state_dict"])
        sched.load_state_dict(rk["scheduler_state_dict"])
        step, start_epoch = int(rk["step"]), int(rk["epoch"])
        resume_micro = 0
        best_val, validation_history = rk["rmse_best"], rk["validation_history"]
        seed_everything(args.seed + start_epoch * 1_000_003 + local_rank)
        migration = dict(kind="topology_continuation_not_bitwise_exact", source_world=2, target_world=4,
                         source_accum=2, target_accum=1, source_step=step, source_epoch=start_epoch,
                         checkpoint_source_path=str(Path(args.migration_checkpoint).resolve()),
                         checkpoint_source_sha256=args.migration_checkpoint_sha256,
                         best_source_path=str(Path(args.migration_best).resolve()),
                         best_source_sha256=args.migration_best_sha256, inherited_best=best_val,
                         rng_policy="all ranks seed + completed_epoch*1000003 + local_rank",
                         sample_policy="same deterministic epoch permutation; changed rank grouping/reduction",
                         original_source_manifest=rk["sha"]["source_sha256"])
        lineage = dict(rk.get("lineage") or {})
        lineage["topology_migration"] = migration
        lineage["is_exact_resume"] = False
        # Create a durable bridge checkpoint without altering inherited best bytes.
        bridge = dict(rk)
        bridge.update(world_size=world,accum=accum,args=vars(args),sha=shas,lineage=lineage,
                      rng_states_by_rank=_gather_rng(),rng_state=capture_rng_state(),
                      completion_reason="topology_migration")
        if rank0():
            copy_atomic(Path(args.migration_best), out/"best_val.pt")
            atomic_torch_save(bridge,out/"last.pt")
            reconcile(out,out/"last.pt",bridge)
            (out/"topology_migration.json").write_text(json.dumps(migration,indent=2),encoding="utf-8")
        if is_dist():
            dist.barrier()
        log(f"TOPOLOGY-MIGRATION step={step}/{total_steps}; optimizer/scheduler inherited; not bitwise exact")
    resume_completed = bool(args.resume) and step >= stop_after_step
    if resume_completed:
        log(f"RESUME-COMPLETE step={step} >= stop_after_step={stop_after_step}"
            f"（total_steps={total_steps}）；无事可训，不写任何 checkpoint")

    student.train()
    from train.baseline_startup_check import StartupCheck
    startup_check = StartupCheck(student)
    ddp_device_ids = [local_rank] if use_cuda else None
    model = DDP(student, device_ids=ddp_device_ids,
                find_unused_parameters=True) if world > 1 else student

    loss_log = []
    handoff_done = False
    completion_reason = "not_completed"
    stop_requested = False

    def save(path, epoch, micro_in_epoch, reason, candidate=None):
        """必须**所有 rank**都调用：_gather_rng 是集合通信，只有写文件是 rank0。
        放在 `if rank0():` 后面会让 DDP 死锁。"""
        raw = model.module if hasattr(model, "module") else model
        tq = sorted(n for n, p in raw.q.named_parameters() if p.requires_grad)
        gathered_rng = _gather_rng()
        ck = make_checkpoint(raw, opt, sched, epoch=epoch, step=step,
                             micro_in_epoch=micro_in_epoch, total_steps=total_steps,
                             accum=accum, world=world, global_batch=args.global_batch,
                             shas=shas, args=args, gathered_rng=gathered_rng,
                             lineage=lineage, trainable_q=tq,
                             unfreeze_prefixes=unfreeze_prefixes, best_val=best_val,
                             completion_reason=reason, lambdas=lambdas,
                             endpoint_plan_note=endpoint_plan_note)
        ck["candidate"] = candidate
        ck["rmse_best"] = best_val
        ck["validation_history"] = validation_history
        if rank0():
            if path.name == "last.pt":
                progress_writer.flush()
                commit(out, ck)
            else:
                atomic_torch_save(ck, path)
            log(f"  checkpoint saved: {path} (step={step} reason={reason})")
        if is_dist():
            dist.barrier()

    done = resume_completed
    t0 = time.time(); t_prev, step_prev = t0, step
    micro_in_epoch = resume_micro
    epoch = start_epoch
    for epoch in range(start_epoch, 10_000_000):
        if done:
            break
        if sampler is not None:
            sampler.set_epoch(epoch)
        gen.manual_seed(args.seed + epoch)
        skip = 0
        epoch_start_step = step
        epoch_started = time.monotonic()
        if use_cuda:
            torch.cuda.reset_peak_memory_stats(dev)
        micro_idx = 0
        window_finite = True
        window_count = torch.zeros((), device=dev)
        window_numerator = torch.zeros((), device=dev)
        raw_window = model.module if hasattr(model, "module") else model
        window_supervision = args.stage == "stage2" and accum > 1
        batches = accumulation_batches(loader, accum, raw_window, dev,
                    lambda: raw_window.draw_endpoint_plan(endpoint_rng(args.seed, step)), window_supervision)
        for batch, window_denominators, window_plan in batches:
            if micro_idx == updates_per_epoch * accum:
                break
            if micro_idx < skip:
                micro_idx += 1
                continue
            data = to_device_with_ids(batch, dev)
            raw_m = model.module if hasattr(model, "module") else model
            # 端点计划：(seed, step) 的纯函数 => 两臂同步、全 rank 一致、resume 精确
            plan = [] if args.stage == "stage1" else (window_plan if window_plan is not None else raw_m.draw_endpoint_plan(endpoint_rng(args.seed, step)))
            if window_denominators is not None:
                data["_supervision_window_counts"] = window_denominators
            in_window = (micro_idx - skip) % accum
            is_boundary = (in_window == accum - 1 or micro_idx + 1 == len(loader))
            sync_ctx = model.no_sync() if (world > 1 and not is_boundary) else nullcontext()
            with sync_ctx:
                _, aux = model(data, lam_ns, plan, None)
                if args.stage == "stage1" and accum > 1:
                    # DDP mean already compensates world size in global_mean.
                    # Accumulate numerator gradients, then normalize ONCE per window.
                    micro_count = aux["global_supervised_count"].detach()
                    window_count += micro_count
                    loss = aux["total"] * micro_count
                elif window_supervision:
                    window_count += aux["global_supervised_count"].detach()
                    loss = aux["total"]
                else:
                    window_count = aux["global_supervised_count"].detach()
                    loss = aux["total"]
                window_numerator += aux["total"].detach() if window_supervision else aux["total"].detach() * aux["global_supervised_count"].detach()
                window_finite = window_finite and bool(torch.isfinite(loss))
                loss.backward()
            micro_idx += 1
            micro_in_epoch = micro_idx
            if not is_boundary:
                continue
            finite = window_finite
            if is_dist():
                f = torch.tensor([1.0 if finite else 0.0], device=dev)
                dist.all_reduce(f, op=dist.ReduceOp.MIN)
                finite = f.item() > 0.5
            if not finite:
                raise FloatingPointError(f"nonfinite loss at step {step}")

            if is_dist():
                dist.all_reduce(window_numerator, op=dist.ReduceOp.SUM)
                window_numerator /= world
            window_loss = float((window_numerator if window_supervision else window_numerator / window_count.clamp_min(1)).item())
            window_numerator = torch.zeros((), device=dev)
            raw_m = model.module if hasattr(model, "module") else model
            if args.stage == "stage1" and accum > 1:
                for parameter in raw_m.parameters():
                    if parameter.grad is not None:
                        parameter.grad.div_(window_count.clamp_min(1))
            if args.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(raw_m.parameters(), args.grad_clip, error_if_nonfinite=True)
            from models.losses.supervision_v2 import optimizer_step_if_supervised
            if step < 2:
                startup_check.observe_gradients(raw_m)
            if not optimizer_step_if_supervised(opt, sched, window_count):
                log(f"empty supervision: epoch={epoch + 1} micro={micro_idx} step={step}; no update")
                window_finite = True
                window_count = torch.zeros((), device=dev)
                continue
            step += 1; window_finite = True
            if step == 2:
                startup_check.finish(raw_m, opt, sched, out, local_rank, step)
            if not handoff_done and step >= 2:
                wait_for_holder_handoff(args.handoff_dir, args.handoff_token, local_rank, step, args.handoff_timeout)
                handoff_done = True
            window_count = torch.zeros((), device=dev)

            if rank0():
                lg = {k: float(v) for k, v in aux["logs"].items()}
                rec = {"step": step, "arm": args.arm, "factual_path": args.factual_path,
                       "lr": float(sched.get_last_lr()[0]), "total": window_loss,
                       "loss_scope": "global_effective_window",
                       "eo_traj": lg.get("eo_traj"), "eo_endpoint": lg.get("eo_endpoint"),
                       "endpoint_plan": [{"endpoint": p["endpoint"],
                                          "partition": list(p["partition"])} for p in plan]}
                for k in ("cmp_z", "cmp_y", "noncollapse"):
                    if k in lg:
                        rec[k] = lg[k]
                if "diagnostics" in aux:
                    rec["diag"] = aux["diagnostics"]
                loss_log.append(rec)
                progress = dict(step=step,total_steps=total_steps,time=time.time(),
                                lr=sched.get_last_lr(),loss=window_loss,epoch=epoch+1,
                                stage=args.stage,variant=args.variant,experiment="baseline_only_retrain",planned_stop_step=stop_after_step)
                progress_writer.update(progress)
            if (step == 1 or step % args.log_interval == 0) and rank0():
                now = time.time()
                ips = (step - step_prev) / max(now - t_prev, 1e-6)
                t_prev, step_prev = now, step
                l = aux["logs"]
                eta_h = (stop_after_step - step) / max(ips, 1e-9) / 3600.0
                log(f"step {step}/{total_steps} {ips:.3f}it/s eta={eta_h:.2f}h "
                    f"lr={sched.get_last_lr()[0]:.2e} total={window_loss:.6f} "
                    f"eo_traj={float(l['eo_traj']):.6f} eo_ep={float(l['eo_endpoint']):.6f}")

            if step >= stop_after_step:
                done = True
                completion_reason = "schedule_complete" if step >= total_steps else "stop_after_step"
                break
        if not resume_completed and step == epoch_start_step:
            raise RuntimeError("complete data epoch had no valid supervision updates; refusing empty-epoch loop")
        if not resume_completed:
            score, reason = validate_candidate_c(model, val_loader, dev, expected)
            updated = improved(best_val, score, epoch + 1, step)
            record = {"epoch": epoch + 1, "step": step, "RMSE_LC": score,
                      "status": reason, "best_updated": updated != best_val,
                      "lr": sched.get_last_lr(), "seconds": time.monotonic() - epoch_started,
                      "peak_cuda_bytes_rank0": torch.cuda.max_memory_allocated(dev) if use_cuda else 0}
            validation_history.append(record)
            best_val = updated
            log(json.dumps(record, allow_nan=False))
            save(out / "last.pt", epoch + 1, 0, "epoch_complete")
            if poll_cooperative_stop(out, dev):
                stop_requested = True
                completion_reason = "cooperative_stop"
                break
        if done:
            break
    # ---- 收尾 --------------------------------------------------------------------
    if completion_reason == "not_completed" and step >= total_steps:
        completion_reason = "schedule_complete"
    if rank0():
        (out / "loss_log.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in loss_log) + "\n")

    raw_m = model.module if hasattr(model, "module") else model
    summary = {
        "runtime_topology": {"world_size":world,"per_gpu_batch":args.per_gpu_batch,"accum":accum,"global_batch":args.global_batch},
        "training_stage": args.stage, "variant": args.variant,
        "schema": "candidate_c_run_summary_v1",
        "status": "COMPLETE" if completion_reason in (
            "schedule_complete", "stop_after_step", "cooperative_stop") else "INCOMPLETE",
        "completion_reason": completion_reason,
        "arm": args.arm, "factual_path": args.factual_path,
        "step": step, "phase_step": step, "total_steps": total_steps,
        "stop_after_step": stop_after_step,
        "accum": accum, "world_size": world, "global_batch": args.global_batch,
        "per_gpu_batch": args.per_gpu_batch,
        "seed": args.seed, "lambdas": lambdas,
        "best_val_dev_RMSE_LC": best_val,
        "validation_history": validation_history,
        "model_state_sha256": state_sha(raw_m.state_dict()),
        "model_value_sha16": value_sha16(raw_m.state_dict()),
        "n_state_dict_tensors": len(raw_m.state_dict()),
        "n_trainable_q": len(sorted(n for n, p in raw_m.q.named_parameters() if p.requires_grad)),
        "lineage": lineage, "sha": shas,
        "endpoint_plan_note": endpoint_plan_note,
        "simulator_status": SIMULATOR_STATUS,
        "not_a_formal_result_unless": (
            "smoke/pilot 只能写工程结论；正式结果仅来自 arm=C1/C0R、四 λ=0、"
            "跑满预注册 total_steps 且 completion_reason=schedule_complete 的 run。"),
        "elapsed_sec": time.time() - t0,
    }
    if rank0():
        tmp = out / "summary.json.tmp"
        with open(tmp, "w") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, out / "summary.json")
    log(f"done arm={args.arm} step={step}/{total_steps} reason={completion_reason} out={out}")
    if is_dist():
        dist.barrier()
        dist.destroy_process_group()
    summary["loss_log"] = loss_log
    return summary


def build_argparser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--continuation-manifest", default="")
    ap.add_argument("--history-state-only", action="store_true", default=False)
    ap.add_argument("--migration-checkpoint", default="")
    ap.add_argument("--migration-checkpoint-sha256", default="")
    ap.add_argument("--migration-best", default="")
    ap.add_argument("--migration-best-sha256", default="")
    ap.add_argument("--handoff-dir", default="")
    ap.add_argument("--handoff-token", default="")
    ap.add_argument("--handoff-timeout", type=float, default=120.0)
    ap.add_argument("--runtime-per-gpu-batch", type=int, choices=[4], default=None)
    ap.add_argument("--runtime-world-size", type=int, choices=[2, 4], default=4)
    ap.add_argument("--config", default=None, help="Reviewed JSON; all strategy fields must match locked policy")
    ap.add_argument("--stage", required=True, choices=["stage1", "stage2"])
    ap.add_argument("--variant", choices=["A", "B", "C", "D"], default="A")
    ap.add_argument("--expected-parent-sha256", required=True)
    ap.add_argument("--arm", required=True, choices=["BASELINE"],
                    help="C1=recursive-only；C0R=同预算 direct 对照（不是 C0S）")
    ap.add_argument("--factual-path", required=True, choices=["recursive", "direct"])
    ap.add_argument("--train-dir", required=True)
    ap.add_argument("--val-dir", required=True)
    ap.add_argument("--val-split-manifest", required=True,
                    help="冻结的 EO split manifest（含 val_dev/val_locked 的实际 ID 列表）")
    ap.add_argument("--val-split-selector", default="splits.val_dev.ids",
                    help="点号选择器；训练期只允许 val_dev")
    ap.add_argument("--q4-partition-manifest", default="")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--resume", default="")
    ap.add_argument("--parent-alias", default=PARENT_ALIAS)
    ap.add_argument("--parent-ckpt", required=True)
    ap.add_argument("--allow-unverified-parent", action="store_true",
                    help="仅测试用；正式 run 绝不使用")
    ap.add_argument("--state-dim", type=int, default=256)
    ap.add_argument("--per-gpu-batch", type=int, default=8)
    ap.add_argument("--global-batch", type=int, default=32)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--max-epochs", type=int, default=100)
    ap.add_argument("--max-steps", type=int, default=0, help=">0 覆盖 epochs")
    ap.add_argument("--stop-after-step", type=int, default=0,
                    help=">0 在该 update 停止执行，但**不改变**计划 total_steps")
    ap.add_argument("--lambda-z", type=float, default=0.0)
    ap.add_argument("--lambda-y", type=float, default=0.0)
    ap.add_argument("--lambda-pair", type=float, default=0.0, help="恒被阻塞，必须为 0")
    ap.add_argument("--lambda-nc", type=float, default=0.0)
    ap.add_argument("--allow-nonzero-lambdas", action="store_true",
                    help="仅 smoke/pilot；正式臂四 λ 必须为 0")
    ap.add_argument("--eo-traj-weight", type=float, default=1.0)
    ap.add_argument("--eo-endpoint-weight", type=float, default=1.0)
    ap.add_argument("--days-per-transition-step", type=int, default=5)
    ap.add_argument("--branch-lr", type=float, default=3e-5)
    ap.add_argument("--q-lr-scale", type=float, default=0.033)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--lr-warmup-steps", type=int, default=600)
    ap.add_argument("--use-adaln", action="store_true")
    ap.add_argument("--unfreeze-q-prefixes", default="core.blocks.2.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--log-interval", type=int, default=10)
    ap.add_argument("--val-interval", type=int, default=745)
    ap.add_argument("--ckpt-interval", type=int, default=372)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--deterministic", action="store_true")
    ap.add_argument("--allow-existing-out", action="store_true")
    ap.add_argument("--verify-data-manifest", action="store_true",
                    help="正式 run 必须开启：校验 EO 样本集指纹")
    ap.add_argument("--expect-train-manifest-sha", default="")
    ap.add_argument("--expect-val-manifest-sha", default="")
    ap.set_defaults(max_epochs=None, branch_lr=None, q_lr_scale=None, use_adaln=None, unfreeze_q_prefixes=None, eo_endpoint_weight=None)
    return ap


def main():
    run_training(build_argparser().parse_args())


if __name__ == "__main__":
    main()
