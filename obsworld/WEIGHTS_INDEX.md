# ObsWorld 权重索引

本仓库**不存放模型权重**。所有 `.pt` / `.ckpt` 走 GitHub Release。

- Release tag：`weights-obsworld-v1`
- 下载后放回下表的「仓库内路径」即可。

## 清单

| 仓库内路径 | 大小 | SHA-256 | 用途 |
|---|---|---|---|
| `archive/07_WEIGHT_PROVENANCE/weights/stage1_final/checkpoint_epoch200_step_95000.pt` | 312.4 MB | `79b20ee6ddc499c60019ed8590108e08789dcc0d8877d1892eb490b2cc5500df` | Stage 1 最终权重（epoch200 / 95k step） |
| `archive/07_WEIGHT_PROVENANCE/weights/stage1_5_final_state_bridge/checkpoint_step_60000.pt` | 346.9 MB | `24646b89eda5fb97ff03a76da5c136969bd1e2af9d76d60bd9537b6e304ff97d` | Stage 1.5 最终权重（60k step，state bridge） |
| `archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/plan_a_s1a_full24/checkpoint_best.pt` | 319.8 MB | `2a0a465fe4d4a148a493954a8acc63b0e6e55896b12631cf3bd9efa08440fad5` | Plan A S1a full24 best |
| `archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/rollout_physical4/checkpoint_best.pt` | 170.0 MB | `8908c62e40b6f71d7ca45aa74047ba2e0c719ea4bc2db7d9cef41587510ead31` | Stage2 rollout physical4 best |
| `archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/direct_physical4/checkpoint_best.pt` | 170.0 MB | `1158ffe6644e6a05345cba3fa56ee73af8d1390a2eb078b4b0bc3a94746f91d2` | Stage2 direct physical4 best |

合计 1.29 GB。

## 重要边界

Stage 1.5 的 60k 结果**没有**证明完整成像不变性：线性 cross-covariance 约束保持较低，
但非线性 MLP probe 仍能恢复部分 orbit/satellite 信息。该负结果被保留，不得在后续设计中被略过。
详见 `archive/00_START_HERE/RESULT_TRUTH_AND_LIMITATIONS.md`。

## 下载

```bash
gh release download weights-obsworld-v1 --repo <owner>/WorldModel2026 --dir /tmp/w
sha256sum -c WEIGHTS_SHA256.txt
```

## 从归档续训

见 `archive/00_START_HERE/RUN_FROM_ARCHIVE.md`（数据、配置与命令）。
