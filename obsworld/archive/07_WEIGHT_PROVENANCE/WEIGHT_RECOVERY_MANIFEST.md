# Stage 1 / Stage 1.5 权重恢复清单

## 当前状态

2026-07-31 已从私有 GitHub releases 恢复最终 Stage1 与 Stage1.5 二进制。此目录仍
不得用 Stage2、Plan A、smoke 或 TerraState 权重替代它们。

| 角色 | 预期文件 | 状态 |
|---|---|---|
| Stage 1 初始化 | `weights/stage1_final/checkpoint_epoch200_step_95000.pt` | `RECOVERED_AND_STRICTLY_VALIDATED`；327,546,060 B；SHA-256 `79b20ee6ddc499c60019ed8590108e08789dcc0d8877d1892eb490b2cc5500df` |
| Stage 1.5 中点 | 私有 release `stage1.5/checkpoint_step_30000.pt` | `AVAILABLE_BUT_EXCLUDED_INTERMEDIATE`；最终归档不复制中间权重 |
| Stage 1.5 最终 state-bridge | `weights/stage1_5_final_state_bridge/checkpoint_step_60000.pt` | `RECOVERED_AND_STRICTLY_VALIDATED`；363,727,067 B；SHA-256 `24646b89eda5fb97ff03a76da5c136969bd1e2af9d76d60bd9537b6e304ff97d` |

历史文档指向的训练服务器根目录为：

`/csy-mix02/cog8/zjliu17/Agent/WorldModel2026`

## 原训练服务器只读查找（历史恢复路径）

```bash
ROOT=/csy-mix02/cog8/zjliu17/Agent/WorldModel2026
find "$ROOT/checkpoints" -type f \
  \( -name 'checkpoint_step_95000.pt' \
  -o -name 'checkpoint_step_30000.pt' \
  -o -name 'checkpoint_step_60000.pt' \) \
  -printf '%s\t%p\n' | sort -nr
```

找到后先生成清单，不要立即重命名：

```bash
sha256sum /absolute/path/to/checkpoint*.pt
```

并用 Python 读取以下字段：

- global step；
- serialized config；
- encoder / decoder key；
- Stage 1.5 的 phi encoder、state projector、state bridge；
- optimizer / scheduler；
- checkpoint 所属架构。

## 接收门槛与完成情况

以下条件已经全部满足：

1. 文件路径和训练阶段一致；
2. step 与预期一致；
3. state-dict 结构与归档代码一致；
4. SHA-256、大小和原始路径已记录；
5. Stage 1.5 结果能与冻结 probe 文档对应。

Stage1/1.5 现在可以从冻结参数直接加载或续训；严格加载记录见同目录
`STRICT_LOAD_VALIDATION.txt`。
