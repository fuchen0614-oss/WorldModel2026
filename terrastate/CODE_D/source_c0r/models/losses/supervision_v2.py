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


def trajectory_weights(clear_mask, landcover_mask=None):
    """One count per pixel with at least one valid target date."""
    weights = (clear_mask.sum(1) > 0).to(dtype=torch.float32)
    return weights if landcover_mask is None else weights * landcover_mask


def endpoint_weights(clear_mask, landcover_mask):
    return clear_mask * landcover_mask


def supervision_counts(data, context_len, target_len, lcmin, lcmax, endpoint_plan):
    """LOCAL denominators in [trajectory, endpoint-plan order]; caller sums/reduces windows.
    Restricted to current NDVI loss (no prediction-derived masks).
    """
    clear = (data["dynamic_mask"][0][:, context_len:context_len + target_len] < 1).float()
    lc = data["landcover"]
    land = ((lc >= lcmin) & (lc <= lcmax)).float()
    counts = [trajectory_weights(clear, land).sum()]
    for item in endpoint_plan:
        ep = int(item["endpoint"])
        if not 1 <= ep <= target_len:
            raise ValueError("supervision endpoint outside target window")
        counts.append(endpoint_weights(clear[:, ep - 1], land).sum())
    return torch.stack(counts).detach()


def window_scaled_mean(loss, micro_count, window_count):
    """global_mean already compensates DDP mean. Do not divide again by accum."""
    if not bool(torch.isfinite(window_count)) or bool(window_count < 0) or bool(micro_count > window_count):
        raise ValueError("invalid global window supervision denominator")
    return loss * micro_count / window_count.clamp_min(1)
