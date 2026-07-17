# ObsWorld Stage2：本地缓存、manifest 暂存与安全清理指南

日期：2026-07-17  
适用配置：`configs/train/stage2_earthnet_v2_direct_physical4.yaml`  
目标：在 8 × H200 上运行 physical4 Stage2，同时把共享盘 NetCDF 读取改为本机 `/tmp` 读取，并避免因一次 OOM/外部抢卡而重复拷贝数据。

## 1. 两个明确开关

`scripts/run_stage2_earthnet_local_staged.sh` 支持下面两个环境变量。

| 变量 | 取值 | 行为 |
| --- | --- | --- |
| `LOCAL_STAGE_CLEANUP` | `auto`（默认） | 正常成功、失败、`INT`/`TERM`/`HUP` 后都自动删除本地暂存。 |
|  | `manual` | 正常结束、训练报错或可捕获中断后保留经过校验的本地缓存；需要显式执行清理命令。适合首次正式启动与 OOM 后快速重试。 |
| `LOCAL_STAGE_DATA_SCOPE` | `all`（默认） | 暂存 `earthnet2021x` 下所有 NetCDF；适用于后续全 split 评测。 |
|  | `train_val` | 只暂存冻结 `train_dev.json` 与 `val_dev.json` 的去重并集。当前 Stage2 训练和 validation monitor 足够，启动复制量显著更小。 |
| `REQUIRE_EMPTY_GPUS` | `0`（默认） | 不额外限制 GPU 进程。 |
|  | `1` | 在暂存开始前和真正训练开始前都检查 `nvidia-smi`；只要已有 compute 进程就拒绝启动，避免因为外部显存占用而 OOM。 |

默认值保持旧行为：`auto + all`。

## 2. 缓存复用的安全规则

每次启动都重新生成本次所需文件清单，并校验：源数据根目录、scope、训练/验证 manifest 的 SHA-256、文件清单 SHA-256、计划文件数，以及每个本地 NetCDF 文件的存在性。

只有全部匹配时才会输出：

```text
reusing verified local staging copy: ...
```

这时不会再次运行 `rsync`。不匹配或不完整的标记缓存会被安全清理后重新暂存；未带 ObsWorld marker 的目录绝不会被覆盖或删除。

一个常用流程是：首次以 `manual + train_val` 启动；若外部进程导致 OOM，缓存保留；确认 GPU 空闲后以相同 `LOCAL_STAGE_ROOT` 重启。即使第二次改为 `auto`，也会复用这份已校验缓存，并在最终运行结束时自动删除。

## 3. 推荐的本次正式训练策略

当前训练只使用 train manifest 和 validation monitor，因此推荐：

```bash
LOCAL_STAGE_CLEANUP=manual
LOCAL_STAGE_DATA_SCOPE=train_val
REQUIRE_EMPTY_GPUS=1
```

这样第一次拷贝后，任何可捕获失败都不必重复复制。模型训练成功、关键 checkpoint 和结果已确认后，再手动清理。这是比“失败即删除、重新拷贝数小时”更稳的选择。

`train_val` 不包含日后可能需要的 OOD/extreme/seasonal 测试样本。做这些评测前，应单独以对应 manifest 暂存，或使用 `LOCAL_STAGE_DATA_SCOPE=all`。

## 4. 启动与监控

完整命令见本文件对应的运行交接消息。启动后先观察：

```bash
tail -F "$LOG_DIR/launcher.log" | tr '\r' '\n'
```

阶段一会显示 `local staging starts` 和 rsync 进度；出现 `training starts` 后，使用：

```bash
tail --retry -F "$LOG_DIR/train_200epoch.log"
```

并用：

```bash
watch -n 2 nvidia-smi
```

确认外部进程没有抢占显存。若日志出现 `CUDA out of memory`，先确认 `nvidia-smi` 的进程列表；本项目此前的 B64 OOM 是另一进程已经占掉约 108 GiB 显存，不能据此判断 B64 本身不适合 H200。

推荐启动命令启用 `REQUIRE_EMPTY_GPUS=1`：它会在复制前和训练前自动做上述检查。若集群调度器有合法的常驻 compute 进程，才应在理解影响后显式设置为 `0`。

## 5. 手动清理与空间核验

以下命令只接受 `/tmp` 下、含正确 marker 的暂存目录；不会删除共享盘数据、checkpoint 或日志：

```bash
bash scripts/cleanup_stage2_earthnet_local_staged.sh \
  --stage-root "$LOCAL_STAGE_ROOT" --force
```

清理前可核验：

```bash
du -sh "$LOCAL_STAGE_ROOT"
test -f "$LOCAL_STAGE_ROOT/.obsworld_stage2_local_stage_metadata.env" && \
  sed -n '1,120p' "$LOCAL_STAGE_ROOT/.obsworld_stage2_local_stage_metadata.env"
```

若使用 `LOCAL_STAGE_CLEANUP=auto`，以上清理动作会在正常成功、失败和可捕获的中断中自动执行。`kill -9` 和节点重启无法运行 shell trap；恢复后执行上述安全清理命令即可。

## 6. 本地磁盘下限

启动器默认要求本地盘剩余至少 `250 GiB`，避免暂存过程中填满根盘。该阈值是安全下限，不代表数据必然占满 250 GiB；实际占用由 `all` 或 `train_val` 的本次清单决定。可在确认空间条件后通过 `MIN_LOCAL_FREE_GB` 覆盖，但不建议低于实际暂存量加上至少数十 GiB 余量。
