#!/usr/bin/env python
"""Candidate C Phase-II trainer — weights-only fork of the verified 14,880 anchor.

这不是 exact resume。父权重只贡献 255 个张量的**数值**；optimizer / scheduler /
RNG 全新，phase_step 从 0 开始。父 checkpoint 里的 optimizer_state_dict 与
scheduler_state_dict 被**故意丢弃**并在 lineage 中显式记录。

两个预注册臂共用这一个脚本，唯一差别是 --factual-path：
  C1  : --factual-path recursive   端点监督经通用 N 段递归路径
  C0R : --factual-path direct      端点监督走变跨度直接路径（同预算对照）
其余一切（父权重、EO 样本 ID、曝光、updates、seed、global batch、
optimizer/scheduler 预算、ckpt interval、λ 全为 0）逐项相同。C0R 不是 C0S：
C0S 专指未来与 C4/C5 匹配 simulator 监督量的对照臂，本轮不得伪造。

L = L_EO + λ_z·L_cmp_z + λ_y·L_cmp_y + λ_pair·L_pair + λ_nc·L_noncollapse
正式臂四个 λ 全部为 0；λ_pair 在任何情况下都被硬阻塞（无冻结 simulator 情景库）。

合作式停止：rank0 每个完整 optimizer step 检查 attempt 目录下的
STOP_AFTER_CHECKPOINT 文件，broadcast 给所有 rank，原子保存整份 checkpoint，
completion_reason=cooperative_stop，barrier 后干净关闭 process group。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from contextlib import nullcontext
from pathlib import Path

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
from train.train_terrastate_v2 import lr_factor  # noqa: E402

STOP_FLAG_NAME = "STOP_AFTER_CHECKPOINT"
CKPT_GLOB = "checkpoint*.pt"


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


def build_optimizer(raw, branch_lr: float, q_lr_scale: float, weight_decay: float):
    """AdamW，按模块身份分组；与 V2 完全同一分组规则（branch / q），
    使 q 与 branch 的 LR 比例在整个 cosine 上保持不变。全新 optimizer。"""
    branch_params = [p for n, p in raw.named_parameters() if not n.startswith("q.")]
    q_params = [p for n, p in raw.named_parameters() if n.startswith("q.")]
    groups = [{"params": branch_params, "lr": branch_lr, "name": "branch"}]
    if q_params:
        groups.append({"params": q_params, "lr": branch_lr * q_lr_scale, "name": "q"})
    return torch.optim.AdamW(groups, betas=(0.9, 0.999), weight_decay=weight_decay)


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


@torch.no_grad()
def validate_candidate_c(model, loader, dev, arm: str = "full"):
    """val_dev 上的 factual EO 技能。累加未归约的 masked 平方和与计数再 all_reduce，
    因此结果与 world size / batching 无关，等于精确的全局 masked 均值。

    只算 L_EO 轨迹项与端点项；不在训练中触碰 val_locked、OOD 或 test。
    """
    raw = model.module if hasattr(model, "module") else model
    cl, tl = raw.context_len, raw.target_len
    raw.eval()
    tj_num = tj_den = 0.0
    ep_num = {int(e): 0.0 for e in raw.FACTUAL_ENDPOINTS}
    ep_den = {int(e): 0.0 for e in raw.FACTUAL_ENDPOINTS}
    for batch in loader:
        data = to_device_with_ids(batch, dev)
        pred, prior, residual, z_t, geo, u_future = raw.forecast(data, want_parts=True)
        B, H, W = pred.shape[0], pred.shape[-2], pred.shape[-1]
        lc = data["landcover"]
        lc_mask = ((lc >= raw.lc_min) & (lc <= raw.lc_max)).type_as(pred)
        cloud = (data["dynamic_mask"][0][:, cl:cl + tl] < 1.0).type_as(pred)
        valid = cloud * lc_mask.unsqueeze(1)
        targ = data["dynamic"][0][:, cl:cl + tl, 0:1]
        tj_num += float((((pred - targ) ** 2) * valid).sum())
        tj_den += float(valid.sum())
        # 端点：每臂用自己的 factual 路径（recursive 用训练侧多段划分的第一个）
        for e in raw.FACTUAL_ENDPOINTS:
            e = int(e)
            part = raw.recursive_candidates(e)[0] if raw.factual_path == "recursive" else (e,)
            y = raw.endpoint_prediction(prior, z_t, u_future, geo, part, B, H, W, arm=arm)
            v1 = valid[:, e - 1]
            ep_num[e] += float((((y - targ[:, e - 1]) ** 2) * v1).sum())
            ep_den[e] += float(v1.sum())
    raw.train()
    if is_dist():
        flat = [tj_num, tj_den] + [ep_num[int(e)] for e in raw.FACTUAL_ENDPOINTS] \
                                + [ep_den[int(e)] for e in raw.FACTUAL_ENDPOINTS]
        t = torch.tensor(flat, device=dev, dtype=torch.float64)
        dist.all_reduce(t, op=dist.ReduceOp.SUM)
        vals = t.tolist()
        tj_num, tj_den = vals[0], vals[1]
        n = len(raw.FACTUAL_ENDPOINTS)
        for i, e in enumerate(raw.FACTUAL_ENDPOINTS):
            ep_num[int(e)] = vals[2 + i]
            ep_den[int(e)] = vals[2 + n + i]
    per_ep = {str(int(e)): ep_num[int(e)] / max(ep_den[int(e)], 1e-8)
              for e in raw.FACTUAL_ENDPOINTS}
    mean_ep = sum(per_ep.values()) / max(len(per_ep), 1)
    return {"eo_traj_mse": tj_num / max(tj_den, 1e-8),
            "eo_endpoint_mse_per_endpoint": per_ep,
            "eo_endpoint_mse_mean": mean_ep,
            "arm": arm, "n_valid_pixels_traj": tj_den}


def make_checkpoint(raw, opt, sched, *, epoch, step, micro_in_epoch, total_steps, accum,
                    world, global_batch, shas, args, gathered_rng, lineage,
                    trainable_q, unfreeze_prefixes, best_val, completion_reason,
                    lambdas, endpoint_plan_note):
    """完整 exact-resume schema。phase_step 就是 step（本 phase 从 0 开始计）。"""
    return {
        "arch": raw.ARCH, "route_version": raw.ROUTE_VERSION,
        "b4_state_dict": raw.state_dict(), "contract_cfg": raw.config(),
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
        "global_batch": global_batch, "alpha": float(raw.alpha),
        "lambdas": dict(lambdas),
        "endpoint_plan_note": endpoint_plan_note,
        "completion_reason": completion_reason,
        "sha": shas, "args": vars(args), "lineage": dict(lineage or {}),
        "simulator_status": SIMULATOR_STATUS,
        "selection_note": (
            "主 checkpoint 已预注册在固定端点 step=total_steps；不得按结果重新挑选。"
            "调参与观察只允许用 val_dev；val_locked 仅作最终门，OOD/test 本轮不开。"),
        "not_exact_resume_of_parent": (
            "本 run 是 verified-14880 的 weights-only Phase-II fork：新 optimizer / "
            "新 scheduler / 新 RNG / phase_step 从 0 开始。父 optimizer 与 scheduler "
            "状态被故意丢弃，绝不可称为 exact resume。"),
    }


def run_training(args, dataset_factory=None) -> dict:
    """`dataset_factory(split, dir) -> Dataset` 是测试缝（DDP smoke 注入合成数据集），
    不改变 model / loss / schedule / 契约。"""
    if dataset_factory is None:
        from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
        dataset_factory = lambda split, d: GreenEarthNetContextformerDataset(d, dl_cloudmask=True)

    if args.arm not in ("C1", "C0R"):
        raise ValueError(f"--arm 只允许 C1 或 C0R，收到 {args.arm!r}。C0S 本轮不得伪造。")
    expect_path = {"C1": "recursive", "C0R": "direct"}[args.arm]
    if args.factual_path != expect_path:
        raise ValueError(
            f"--arm {args.arm} 要求 --factual-path {expect_path}，收到 {args.factual_path!r}。")
    if float(args.lambda_pair) != 0.0:
        raise ValueError(f"λ_pair 必须为 0：{SIMULATOR_STATUS}")
    if args.stop_after_step < 0:
        raise ValueError("--stop-after-step 必须 >= 0")
    guard_output_dir(Path(args.output_dir), args.allow_existing_out)

    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    world = int(os.environ.get("WORLD_SIZE", 1))
    seed_everything(args.seed + local_rank)
    use_cuda = torch.cuda.is_available() and args.device != "cpu"
    if world > 1:
        dist.init_process_group("nccl" if use_cuda else "gloo",
                                device_id=(torch.device("cuda", local_rank) if use_cuda else None))
        if use_cuda:
            torch.cuda.set_device(local_rank)
    dev = torch.device("cuda", local_rank) if use_cuda else torch.device("cpu")
    out = Path(args.output_dir)
    if rank0():
        out.mkdir(parents=True, exist_ok=True)

    # ---- 模型 + weights-only warm start ------------------------------------------
    hp = contextformer6m_hparams(pvt_pretrained=False)
    ccfg = {"state_dim": args.state_dim, "freeze_b0": False,
            "factual_path": args.factual_path,
            "days_per_transition_step": args.days_per_transition_step,
            "use_future_state_anchor": False,
            "eo_traj_weight": args.eo_traj_weight,
            "eo_endpoint_weight": args.eo_endpoint_weight}
    model_cpu = TerraStateCandidateC(hp, contract_cfg=ccfg)
    lineage = warm_start_candidate_c(
        model_cpu, alias=args.parent_alias,
        ckpt_path=(args.parent_ckpt or None),
        verify_file_sha=(not args.allow_unverified_parent))
    student = model_cpu.to(dev)
    log(f"warm-start OK: 继承 {lineage['inherited_n_tensors']} 张量，"
        f"value_sha={lineage['inherited_value_sha16']}，"
        f"max_abs_diff={lineage['max_abs_diff_vs_parent']}，"
        f"missing={len(lineage['missing_keys'])} unexpected={len(lineage['unexpected_keys'])}")
    log(f"  fork_kind={lineage['fork_kind']} is_exact_resume={lineage['is_exact_resume']} "
        f"phase_step=0 父 optimizer/scheduler 已丢弃="
        f"{lineage['parent_optimizer_scheduler_deliberately_discarded']}")

    unfreeze_prefixes = [s for s in args.unfreeze_q_prefixes.split(",") if s]
    trainable_q = apply_phase_ii_freeze(student, unfreeze_prefixes)
    log(f"Phase-II 冻结集：q 可训练张量 {len(trainable_q)}（prefixes {unfreeze_prefixes}）")
    # ---- 数据 --------------------------------------------------------------------
    train_ds = dataset_factory("train", args.train_dir)
    val_full = dataset_factory("val", args.val_dir)
    val_ids, split_blob = load_val_split(args.val_split_manifest, args.val_split_selector)
    val_ds = subset_by_id_list(val_full, args.val_dir, val_ids, args.val_split_selector)
    log(f"val split {args.val_split_selector}: {len(val_ds)} cubes（全 val {len(val_full)}）")
    if args.val_split_selector.endswith("val_locked.ids"):
        raise ValueError("训练期禁止把 val_locked 作为观察 split；它只作最终门。")

    shuffle = not args.deterministic
    sampler = DistributedSampler(train_ds, shuffle=shuffle, seed=args.seed) if world > 1 else None
    gen = torch.Generator(); gen.manual_seed(args.seed)
    loader = DataLoader(train_ds, batch_size=args.per_gpu_batch, sampler=sampler,
                        shuffle=(sampler is None and shuffle), num_workers=args.num_workers,
                        collate_fn=collate_with_ids, pin_memory=use_cuda, drop_last=True,
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
    updates_per_epoch = max(len(loader) // accum, 1)
    total_steps = args.max_steps if args.max_steps > 0 else args.max_epochs * updates_per_epoch
    stop_after_step = args.stop_after_step if args.stop_after_step > 0 else total_steps
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
    if args.arm in ("C1", "C0R") and any(v != 0.0 for v in lambdas.values()) and not args.allow_nonzero_lambdas:
        raise ValueError(
            f"正式臂 {args.arm} 要求四个 λ 全为 0，收到 {lambdas}。"
            f"smoke/pilot 若确需非零请显式加 --allow-nonzero-lambdas，并且结果不得写成正式结果。")
    log(f"λ = {lambdas}（正式臂应全 0；λ_pair 恒被阻塞：{SIMULATOR_STATUS}）")

    # ---- optimizer / scheduler：全新 ---------------------------------------------
    opt = build_optimizer(student, args.branch_lr, args.q_lr_scale, args.weight_decay)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lr_lambda=lambda s: lr_factor(s, args.lr_warmup_steps, total_steps))
    for g in opt.param_groups:
        log(f"  opt '{g['name']}': tensors={len(g['params'])} base_lr={g['lr']:.2e}")
    # ---- provenance：每份 checkpoint 都带 ----------------------------------------
    shas = {
        "parent_alias": args.parent_alias,
        "parent_logical_id": lineage["parent_logical_id"],
        "parent_file_sha256": lineage["parent_file_sha256"],
        "parent_value_sha16": lineage["parent_value_sha16"],
        "inherited_value_sha16": lineage["inherited_value_sha16"],
        "warm_start_state_sha256": state_sha(student.state_dict()),
        "val_split_manifest_path": args.val_split_manifest,
        "val_split_manifest_sha256": sha256_file(args.val_split_manifest),
        "val_split_selector": args.val_split_selector,
        "val_split_n_ids": len(val_ids),
        "q4_partition_manifest_path": args.q4_partition_manifest or "",
        "q4_partition_manifest_sha256": (sha256_file(args.q4_partition_manifest)
                                        if args.q4_partition_manifest else ""),
        "config_sha256": canonical_json_sha256({k: getattr(args, k) for k in sorted(vars(args))}),
        "source_sha256": {
            rel: sha256_file(ROOT / rel) for rel in (
                "models/terrastate_candidate_c.py",
                "train/train_terrastate_candidate_c.py",
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
    best_val = float("inf")
    if args.resume:
        rk = torch.load(args.resume, map_location="cpu", weights_only=False)
        if rk.get("arch") != student.ARCH:
            raise ValueError(f"resume arch 不符：{rk.get('arch')} != {student.ARCH}")
        if rk.get("arm") != args.arm:
            raise ValueError(f"resume arm 不符：{rk.get('arm')} != {args.arm}")
        if rk.get("factual_path") != args.factual_path:
            raise ValueError(f"resume factual_path 不符：{rk.get('factual_path')} != {args.factual_path}")
        if int(rk["total_steps"]) != total_steps:
            raise ValueError("resume total_steps 不符（schedule 变了）")
        if int(rk["global_batch"]) != args.global_batch or int(rk["accum"]) != accum:
            raise ValueError("resume global_batch/accum 不符")
        for key in ("parent_file_sha256", "inherited_value_sha16", "val_split_manifest_sha256"):
            if rk["sha"].get(key) != shas.get(key):
                raise ValueError(f"resume {key} 不符：{rk['sha'].get(key)} != {shas.get(key)}")
        if dict(rk.get("lambdas") or {}) != lambdas:
            raise ValueError(f"resume λ 不符：{rk.get('lambdas')} != {lambdas}")
        student.load_state_dict(rk["b4_state_dict"], strict=True)
        opt.load_state_dict(rk["optimizer_state_dict"])
        sched.load_state_dict(rk["scheduler_state_dict"])
        step = int(rk["step"]); start_epoch = int(rk["epoch"])
        resume_micro = int(rk["micro_in_epoch"]); best_val = float(rk["best_val"])
        rng_by_rank = rk.get("rng_states_by_rank") or [rk["rng_state"]]
        restore_rng_state(rng_by_rank[min(local_rank, len(rng_by_rank) - 1)])
        lineage = dict(rk.get("lineage") or lineage)
        lineage["resumed_within_phase"] = True
        lineage["resume_parent_path"] = str(Path(args.resume).resolve())
        lineage["resume_parent_file_sha256"] = sha256_file(args.resume)
        log(f"RESUME(phase 内) step={step} epoch={start_epoch} micro={resume_micro} "
            f"best_val={best_val:.6f}")
    resume_completed = bool(args.resume) and step >= stop_after_step
    if resume_completed:
        log(f"RESUME-COMPLETE step={step} >= stop_after_step={stop_after_step}"
            f"（total_steps={total_steps}）；无事可训，不写任何 checkpoint")

    student.train()
    ddp_device_ids = [local_rank] if use_cuda else None
    model = DDP(student, device_ids=ddp_device_ids,
                find_unused_parameters=True) if world > 1 else student

    loss_log = []
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
        if rank0():
            atomic_torch_save(ck, path)
            log(f"  checkpoint saved: {path} (step={step} reason={reason})")
        if is_dist():
            dist.barrier()

    # Define milestone steps for checkpoint tagging
    milestone_steps = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 14880]

    done = resume_completed
    t0 = time.time(); t_prev, step_prev = t0, step
    micro_in_epoch = resume_micro
    epoch = start_epoch
    for epoch in range(start_epoch, 10_000_000):
        if done:
            break
        if sampler is not None:
            sampler.set_epoch(epoch)
        skip = resume_micro if epoch == start_epoch else 0
        micro_idx = 0
        window_finite = True
        for batch in loader:
            if micro_idx < skip:
                micro_idx += 1
                continue
            data = to_device_with_ids(batch, dev)
            raw_m = model.module if hasattr(model, "module") else model
            # 端点计划：(seed, step) 的纯函数 => 两臂同步、全 rank 一致、resume 精确
            plan = raw_m.draw_endpoint_plan(endpoint_rng(args.seed, step))
            in_window = (micro_idx - skip) % accum
            is_boundary = (in_window == accum - 1)
            sync_ctx = model.no_sync() if (world > 1 and not is_boundary) else nullcontext()
            with sync_ctx:
                _, aux = model(data, lam_ns, plan, None)
                loss = aux["total"] / accum
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
                # 非有限窗：全 rank 对称跳过这次更新，绝不让一部分 rank 更新
                log(f"WARN 非有限 loss 窗口 @ step {step}；全 rank 跳过更新")
                opt.zero_grad(set_to_none=True); window_finite = True
                sched.step(); step += 1
                if stop_after_step < total_steps and step >= stop_after_step:
                    done = True; completion_reason = "stop_after_step"
                    break
                continue

            raw_m = model.module if hasattr(model, "module") else model
            if args.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(raw_m.parameters(), args.grad_clip)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            step += 1; window_finite = True

            if rank0():
                lg = {k: float(v) for k, v in aux["logs"].items()}
                rec = {"step": step, "arm": args.arm, "factual_path": args.factual_path,
                       "lr": float(sched.get_last_lr()[0]), "total": lg.get("total"),
                       "eo_traj": lg.get("eo_traj"), "eo_endpoint": lg.get("eo_endpoint"),
                       "endpoint_plan": [{"endpoint": p["endpoint"],
                                          "partition": list(p["partition"])} for p in plan]}
                for k in ("cmp_z", "cmp_y", "noncollapse"):
                    if k in lg:
                        rec[k] = lg[k]
                if "diagnostics" in aux:
                    rec["diag"] = aux["diagnostics"]
                loss_log.append(rec)
            if step % args.log_interval == 0 and rank0():
                now = time.time()
                ips = (step - step_prev) / max(now - t_prev, 1e-6)
                t_prev, step_prev = now, step
                l = aux["logs"]
                eta_h = (total_steps - step) / max(ips, 1e-9) / 3600.0
                log(f"step {step}/{total_steps} {ips:.3f}it/s eta={eta_h:.2f}h "
                    f"lr={sched.get_last_lr()[0]:.2e} total={float(l['total']):.6f} "
                    f"eo_traj={float(l['eo_traj']):.6f} eo_ep={float(l['eo_endpoint']):.6f}")

            # ---- 合作式停止：每个完整 optimizer step 检查一次 --------------------
            if poll_cooperative_stop(out, dev):
                stop_requested = True
                completion_reason = "cooperative_stop"
                save(out / f"checkpoint_step{step}_cooperative_stop.pt", epoch,
                     micro_in_epoch, "cooperative_stop", candidate="cooperative_stop")
                log(f"  [cooperative stop] 已在 step {step} 完整保存，准备干净退出")
                done = True
                break

            if args.val_interval > 0 and (step % args.val_interval == 0 or step == total_steps):
                vm = validate_candidate_c(model, val_loader, dev)
                per_ep = {k: round(v, 6) for k, v in
                          vm["eo_endpoint_mse_per_endpoint"].items()}
                log(f"  [val_dev] step {step} eo_traj={vm['eo_traj_mse']:.6f} "
                    f"eo_ep_mean={vm['eo_endpoint_mse_mean']:.6f} per_ep={per_ep}")
                if rank0():
                    loss_log.append({"step": step, "val_dev": vm})
                best_val = min(best_val, float(vm["eo_endpoint_mse_mean"]))

            if args.ckpt_interval > 0 and step % args.ckpt_interval == 0:
                save(out / f"checkpoint_step{step}.pt", epoch, micro_in_epoch,
                     "interval", candidate="interval")

            # Tag milestone checkpoints：只在 rank0 复制，源不存在只告警不打断训练
            if rank0() and step in milestone_steps:
                src_path = out / f"checkpoint_step{step}.pt"
                dst_path = out / f"checkpoint_milestone{step}_step{step}.pt"
                if src_path.exists():
                    shutil.copy2(src_path, dst_path)
                    log(f"  [milestone-tag] 已复制: {dst_path.name}")
                else:
                    log(f"  [警告] milestone tag 想复制的 ckpt 不存在: {src_path.name}")

            if stop_after_step < total_steps and step >= stop_after_step:
                done = True; completion_reason = "stop_after_step"
                break
            if step >= total_steps:
                done = True; completion_reason = "schedule_complete"
                break
        resume_micro = 0
        if done:
            break
    # ---- 收尾 --------------------------------------------------------------------
    if completion_reason == "not_completed" and step >= total_steps:
        completion_reason = "schedule_complete"
    if not resume_completed and not stop_requested:
        # 主 checkpoint 预注册在固定端点；到点即 main，不按结果重挑。
        is_main = (step >= total_steps)
        save(out / ("checkpoint_main.pt" if is_main else "checkpoint_last.pt"),
             epoch, micro_in_epoch, completion_reason,
             candidate=("main_pre_registered_endpoint" if is_main else "last"))
    if rank0():
        (out / "loss_log.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in loss_log) + "\n")

    raw_m = model.module if hasattr(model, "module") else model
    summary = {
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
        "best_val_dev_endpoint_mse": (None if best_val == float("inf") else best_val),
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
    ap.add_argument("--arm", required=True, choices=["C1", "C0R"],
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
    ap.add_argument("--parent-ckpt", default="", help="显式路径（默认走 alias 解析）")
    ap.add_argument("--allow-unverified-parent", action="store_true",
                    help="仅测试用；正式 run 绝不使用")
    ap.add_argument("--state-dim", type=int, default=256)
    ap.add_argument("--per-gpu-batch", type=int, default=8)
    ap.add_argument("--global-batch", type=int, default=64)
    ap.add_argument("--num-workers", type=int, default=8)
    ap.add_argument("--max-epochs", type=int, default=8)
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
    ap.add_argument("--lr-warmup-steps", type=int, default=100)
    ap.add_argument("--unfreeze-q-prefixes", default="core.blocks.2.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--log-interval", type=int, default=10)
    ap.add_argument("--val-interval", type=int, default=372)
    ap.add_argument("--ckpt-interval", type=int, default=372)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--deterministic", action="store_true")
    ap.add_argument("--allow-existing-out", action="store_true")
    ap.add_argument("--verify-data-manifest", action="store_true",
                    help="正式 run 必须开启：校验 EO 样本集指纹")
    ap.add_argument("--expect-train-manifest-sha", default="")
    ap.add_argument("--expect-val-manifest-sha", default="")
    return ap


def main():
    run_training(build_argparser().parse_args())


if __name__ == "__main__":
    main()
