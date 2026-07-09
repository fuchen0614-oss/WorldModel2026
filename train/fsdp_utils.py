"""
FSDP 分布式训练工具模块（FSDP2 / fully_shard）

本模块为 PyTorch 分布式训练提供完整工具函数，支持：
- FSDP2（torch.distributed.fsdp.fully_shard）—— PyTorch 2.0+ 官方推荐方案
- 单卡训练自动回退 —— 未启动分布式环境时直接透传，不做任何包装

设计要点（均在 torch 2.12 本机实测确认）：
- fully_shard 的混合精度参数名为 mp_policy，类型为 MixedPrecisionPolicy
  注意：这与 FSDP1 的 mixed_precision= + MixedPrecision 不同，写错会直接报错
- checkpoint 通过 torch.distributed.checkpoint.state_dict.get_model_state_dict
  配合 StateDictOptions(full_state_dict=True, cpu_offload=True) 在 rank 0 汇聚完整权重
  这样保存的 checkpoint 与训练 GPU 数量解耦，可在任意卡数或 CPU 上加载

典型用法：
    rank, local_rank, world_size, distributed = setup_distributed()
    model = MyModel().to(f"cuda:{local_rank}")
    if distributed:
        model = wrap_model_fsdp2(model)
    optimizer = torch.optim.AdamW(model.parameters(), ...)  # 必须在包装之后创建
    ... 训练 ...
    save_fsdp_checkpoint(model, optimizer, "ckpt.pt", global_step=step)
    cleanup_distributed()
"""

import os
from pathlib import Path
from typing import Optional

import torch
import torch.distributed as dist


# ============================================================
# 一、分布式环境初始化与查询
# ============================================================

def setup_distributed():
    """初始化分布式进程组（若由 torchrun 启动）。

    torchrun 会自动注入 RANK / LOCAL_RANK / WORLD_SIZE 等环境变量。
    本函数据此判断是否处于分布式模式：
    - 若 WORLD_SIZE > 1：GPU 使用 NCCL；无 GPU 的测试环境使用 Gloo
    - 否则：判定为单卡模式，不做任何初始化

    返回:
        (rank, local_rank, world_size, distributed)
        rank: 全局进程号；local_rank: 本机内 GPU 号；
        world_size: 总进程数；distributed: 是否为分布式模式
    """
    world_size = int(os.environ.get("WORLD_SIZE", "1"))

    if world_size > 1:
        rank = int(os.environ["RANK"])
        local_rank = int(os.environ["LOCAL_RANK"])

        # GPU runs use NCCL. Gloo keeps CPU distributed smoke tests available
        # without changing the production backend.
        from datetime import timedelta
        backend = "nccl" if torch.cuda.is_available() else "gloo"
        if torch.cuda.is_available():
            torch.cuda.set_device(local_rank)
        dist.init_process_group(
            backend=backend,
            init_method="env://",
            timeout=timedelta(minutes=30),
        )

        return rank, local_rank, world_size, True
    else:
        # 单卡模式：rank=0，使用 0 号 GPU（若有）
        return 0, 0, 1, False


def cleanup_distributed():
    """销毁分布式进程组并释放通信资源。"""
    if is_distributed():
        dist.destroy_process_group()


def is_distributed():
    """判断分布式进程组是否已初始化。"""
    return dist.is_available() and dist.is_initialized()


def get_rank():
    """获取当前进程的全局 rank；非分布式环境返回 0。"""
    if is_distributed():
        return dist.get_rank()
    return 0


def get_world_size():
    """获取总进程数；非分布式环境返回 1。"""
    if is_distributed():
        return dist.get_world_size()
    return 1


def is_main_process():
    """判断是否为主进程（rank 0）。日志、checkpoint 等只在主进程执行。"""
    return get_rank() == 0


def barrier():
    """同步屏障：等待所有进程到达此处（非分布式环境下为空操作）。"""
    if is_distributed():
        dist.barrier()


# ============================================================
# 二、FSDP2 模型包装
# ============================================================


def wrap_model_fsdp2(
    model: torch.nn.Module,
    mixed_precision: str = "bf16",
) -> torch.nn.Module:
    """用 FSDP2（fully_shard）包装模型，将参数/梯度/优化器状态分片到各 GPU。

    FSDP2 是 PyTorch 2.0+ 的官方推荐方案，相比 FSDP1：
    - 基于 DTensor，按参数（per-parameter）分片，内存管理更精细
    - API 更清晰，与张量并行等技术组合更干净

    Args:
        model: 待包装的模型（须已 .to(cuda) 到本进程的 GPU）
        mixed_precision: 混合精度模式，'bf16' / 'fp16' / 'fp32'

    Returns:
        被 FSDP2 包装后的模型（原地修改并返回同一对象）

    注意:
        - 必须先初始化分布式进程组，否则直接返回原模型
        - 优化器必须在本函数调用之后创建，因为包装后参数变为 DTensor
    """
    if not is_distributed():
        print("[FSDP] 警告：未初始化分布式环境，返回未包装模型（单卡模式）")
        return model

    from torch.distributed.fsdp import fully_shard, MixedPrecisionPolicy

    # 配置混合精度策略（torch 2.12 实测：参数名为 mp_policy）
    if mixed_precision == "bf16":
        mp_policy = MixedPrecisionPolicy(
            param_dtype=torch.bfloat16,
            reduce_dtype=torch.float32,  # 梯度归约用 fp32，数值更稳
        )
    elif mixed_precision == "fp16":
        mp_policy = MixedPrecisionPolicy(
            param_dtype=torch.float16,
            reduce_dtype=torch.float32,
        )
    else:  # fp32：不启用混合精度
        mp_policy = MixedPrecisionPolicy()

    fully_shard(model, mp_policy=mp_policy)
    return model


# ============================================================
# 三、分布式 checkpoint 保存与加载
# ============================================================


def get_full_state_dict(model: torch.nn.Module) -> dict:
    """汇聚一个模块的完整（非分片）state_dict。

    FSDP 模式下，参数以 DTensor 形式分片在各 GPU，需通过 get_model_state_dict
    + full_state_dict=True 汇聚成完整权重（在 rank 0 上，其余 rank 返回空 dict）。
    单卡模式直接返回普通 state_dict。

    用于 encoder / decoder 这类需要分别保存的多模块场景。
    """
    if is_distributed():
        from torch.distributed.checkpoint.state_dict import (
            get_model_state_dict,
            StateDictOptions,
        )
        options = StateDictOptions(full_state_dict=True, cpu_offload=True)
        return get_model_state_dict(model, options=options)
    return model.state_dict()


def get_full_optim_state_dict(model: torch.nn.Module, optimizer: torch.optim.Optimizer) -> dict:
    """汇聚优化器的完整（非分片）state_dict。

    FSDP 模式下，优化器的动量等状态（exp_avg / exp_avg_sq）也以 DTensor 形式
    分片在各 GPU。若直接 optimizer.state_dict() 保存，会残留 DTensor 与 DeviceMesh
    引用，导致 checkpoint 无法在不同卡数 / CPU 上干净加载。

    本函数通过 get_optimizer_state_dict + full_state_dict=True 汇聚成完整状态。
    单卡模式直接返回普通 optimizer.state_dict()。

    Args:
        model: 优化器所优化的模型（参数须在此 model 下，用于建立 FQN 映射）
        optimizer: 优化器

    Returns:
        完整优化器 state_dict（rank 0 含完整内容，其余 rank 视情况为空）
    """
    if is_distributed():
        from torch.distributed.checkpoint.state_dict import (
            get_optimizer_state_dict,
            StateDictOptions,
        )
        options = StateDictOptions(full_state_dict=True, cpu_offload=True)
        return get_optimizer_state_dict(model, optimizer, options=options)
    return optimizer.state_dict()


def set_full_optim_state_dict(model, optimizer, optim_state_dict):
    """把完整（非分片）优化器 state_dict 加载回优化器（与 get_full_optim_state_dict 配对）。

    FSDP 模式下，optimizer 的参数已是 DTensor，而 checkpoint 里的动量是普通 Tensor。
    若直接 optimizer.load_state_dict(...)，动量会以普通 Tensor 进入优化器，导致 step()
    时 Adam 更新遇到 Tensor 与 DTensor 混合而崩溃。必须用 set_optimizer_state_dict
    把完整状态正确分片成 DTensor。单卡模式直接 load_state_dict。

    Args:
        model: 优化器所优化的模型（建立 FQN 映射）
        optimizer: 目标优化器
        optim_state_dict: 来自 checkpoint 的完整优化器状态
    """
    if is_distributed():
        from torch.distributed.checkpoint.state_dict import (
            set_optimizer_state_dict,
            StateDictOptions,
        )
        options = StateDictOptions(full_state_dict=True, broadcast_from_rank0=True)
        set_optimizer_state_dict(model, optimizer, optim_state_dict, options=options)
    else:
        optimizer.load_state_dict(optim_state_dict)


def save_fsdp_checkpoint(
    model: torch.nn.Module,
    optimizer: Optional[torch.optim.Optimizer],
    path: str,
    **extra_state,
) -> None:
    """保存 FSDP / 单卡模型 checkpoint（仅 rank 0 实际写盘）。

    通过 get_model_state_dict + StateDictOptions(full_state_dict=True) 把分片
    在各 GPU 上的参数汇聚成完整 state_dict，因此保存的 checkpoint 与训练卡数
    解耦，可在任意 GPU 数量或 CPU 上加载。

    Args:
        model: 模型（FSDP 包装或普通模型均可）
        optimizer: 优化器（可为 None）
        path: checkpoint 保存路径
        **extra_state: 额外状态（如 global_step、config 等）
    """
    if is_distributed():
        from torch.distributed.checkpoint.state_dict import (
            get_model_state_dict,
            StateDictOptions,
        )
        # full_state_dict=True 汇聚完整权重，cpu_offload=True 卸载到 CPU 避免显存峰值
        options = StateDictOptions(full_state_dict=True, cpu_offload=True)
        model_state = get_model_state_dict(model, options=options)
    else:
        model_state = model.state_dict()

    # 仅主进程写盘
    if not is_main_process():
        barrier()
        return

    checkpoint = dict(extra_state)
    checkpoint["model"] = model_state
    if optimizer is not None:
        checkpoint["optimizer"] = optimizer.state_dict()

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, path)
    print(f"[FSDP] checkpoint 已保存: {path}")

    barrier()


def load_fsdp_checkpoint(
    path: str,
    model: torch.nn.Module,
    optimizer: Optional[torch.optim.Optimizer] = None,
    strict: bool = True,
) -> dict:
    """加载 checkpoint 到模型/优化器，返回其余额外状态（如 global_step）。

    Args:
        path: checkpoint 路径
        model: 目标模型
        optimizer: 目标优化器（可选）
        strict: 是否严格校验 state_dict 键匹配

    Returns:
        除 model / optimizer 外的额外状态字典
    """
    map_location = (
        f"cuda:{torch.cuda.current_device()}" if torch.cuda.is_available() else "cpu"
    )
    checkpoint = torch.load(path, map_location=map_location, weights_only=False)

    if "model" in checkpoint:
        if is_distributed():
            from torch.distributed.checkpoint.state_dict import (
                set_model_state_dict,
                StateDictOptions,
            )
            options = StateDictOptions(full_state_dict=True, broadcast_from_rank0=True)
            set_model_state_dict(model, checkpoint["model"], options=options)
        else:
            model.load_state_dict(checkpoint["model"], strict=strict)

    if optimizer is not None and "optimizer" in checkpoint:
        optimizer.load_state_dict(checkpoint["optimizer"])

    if is_main_process():
        print(f"[FSDP] checkpoint 已加载: {path}")

    return {k: v for k, v in checkpoint.items() if k not in ("model", "optimizer")}

