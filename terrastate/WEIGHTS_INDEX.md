# TerraState 权重索引

本仓库**不存放模型权重**。所有 `.pt` / `.ckpt` 走 GitHub Release。

- Release tag：`weights-terrastate-v1`
- 下载后放回下表的「仓库内路径」即可。

## 清单

| 仓库内路径 | 大小 | SHA-256 | 用途 |
|---|---|---|---|
| `checkpoints/contextformer_official/contextformer6M/seed42.ckpt` | 69.6 MB | `ec6706e8a904bba8a195d542921f54c6ce058f8d0d7a9aaeb91f117237d4a4fa` | Contextformer 官方权重，TerraState history operator $q_\theta$ 的初始化来源 |
| `archive/07_WEIGHTS_AND_PROVENANCE/historical_boundary80_release/checkpoint_boundary80.pt` | 36.2 MB | `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd` | 已恢复并验真的历史 boundary80 checkpoint |
| `archive/07_WEIGHTS_AND_PROVENANCE/phase1_b4_teacher/checkpoint_best.pt` | 27.5 MB | `2c5d084236716d84d1ed11289248a501a7cb906675a32ccb8fd73e1f2a26881c` | Phase-I B4 teacher（KD 教师） |

合计 133.3 MB。

## 重要边界（沿用归档口径，不要弱化）

已恢复的 boundary80 checkpoint **不能**冒充作者确认口径的
40 epochs / 14,880 updates 最终权重——后者的二进制目前仍缺失。
论文 Q1–Q3 报告值以 `archive/04_RESULTS_EVIDENCE/current/release_metrics/`
与 `submission/` 内的冻结数值为准，不由本地权重重算。

## 下载

```bash
gh release download weights-terrastate-v1 --repo <owner>/WorldModel2026 --dir /tmp/w
# 校验后放回对应路径
sha256sum -c WEIGHTS_SHA256.txt
```

## 校验文件

```
ec6706e8a904bba8a195d542921f54c6ce058f8d0d7a9aaeb91f117237d4a4fa  seed42.ckpt
644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd  checkpoint_boundary80.pt
2c5d084236716d84d1ed11289248a501a7cb906675a32ccb8fd73e1f2a26881c  checkpoint_best.pt
```
