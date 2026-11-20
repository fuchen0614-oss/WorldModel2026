"""Parameter-free supervision helpers; collectives require identical calls on all ranks."""
import torch
import torch.distributed as dist

def global_mean(local_sum, local_count):
    count = local_count.detach().to(device=local_sum.device, dtype=torch.float32).clone()
    world = 1
    if dist.is_available() and dist.is_initialized():
        world = dist.get_world_size()
        dist.all_reduce(count)
    # DDP averages gradients: compensate so the result is the global valid mean.
    loss = local_sum * world / count.clamp_min(1)
    return loss, count

def optimizer_step_if_supervised(optimizer, scheduler, global_count):
    """Call after synchronized backward; all ranks must pass the same count.
    Current contract: accumulation=1. Empty batches do not advance updates.
    Gradient clipping, if used, belongs before this function.
    """
    active = bool(global_count.item() > 0)
    if active:
        optimizer.step()
        if scheduler is not None:
            scheduler.step()
    optimizer.zero_grad(set_to_none=True)
    return active
