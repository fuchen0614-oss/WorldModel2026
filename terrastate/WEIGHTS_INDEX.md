# TerraState 权重索引

本仓库**不存放模型权重**（`.gitignore` 已排除 `*.pt` / `*.ckpt`）。全部权重存放在 GitHub Release。

- **Release**：[`weights-terrastate-v1`](https://github.com/fuchen0614-oss/WorldModel2026/releases/tag/weights-terrastate-v1)
- 上传日期：2026-08-14 · 3 个资产 / 133.4 MB

## 清单

Release 资产名是扁平化的（用 `__` 连接来源目录），下载后请按「仓库内路径」放回。

| Release 资产名 | 仓库内路径 | 字节数 | SHA-256 |
|---|---|---:|---|
| `contextformer_official__seed42.ckpt` | `checkpoints/contextformer_official/contextformer6M/seed42.ckpt` | 73009735 | `ec6706e8a904bba8a195d542921f54c6ce058f8d0d7a9aaeb91f117237d4a4fa` |
| `historical_boundary80__checkpoint_boundary80.pt` | `archive/07_WEIGHTS_AND_PROVENANCE/historical_boundary80_release/checkpoint_boundary80.pt` | 37972401 | `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd` |
| `phase1_b4_teacher__checkpoint_best.pt` | `archive/07_WEIGHTS_AND_PROVENANCE/phase1_b4_teacher/checkpoint_best.pt` | 28846423 | `2c5d084236716d84d1ed11289248a501a7cb906675a32ccb8fd73e1f2a26881c` |

用途：

- **contextformer_official/seed42.ckpt** — Contextformer 官方权重，TerraState history operator $q_\theta$ 的初始化来源。
- **checkpoint_boundary80.pt** — 已恢复并验真的历史 boundary80 checkpoint。
- **phase1_b4_teacher/checkpoint_best.pt** — Phase-I B4 teacher（KD 教师）。

## 重要边界（不要弱化）

已恢复的 boundary80 checkpoint **不能**冒充作者确认口径的
40 epochs / 14,880 updates 最终权重——**后者的二进制目前仍缺失**，可能只存在于训练服务器上。

论文 Q1–Q3 的报告值以 `archive/04_RESULTS_EVIDENCE/current/release_metrics/`
与 `submission/` 内的冻结数值为准，不由本地权重重算。

## 下载

有 `gh` CLI：

```bash
gh release download weights-terrastate-v1 --repo fuchen0614-oss/WorldModel2026 --dir /tmp/w
```

没有 `gh`（只需一个 `repo` scope 的 token）：

```bash
export GITHUB_TOKEN=<your-token>
REPO=fuchen0614-oss/WorldModel2026
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/$REPO/releases/tags/weights-terrastate-v1" \
| python3 -c "import sys,json;[print(a['id'],a['name']) for a in json.load(sys.stdin)['assets']]" \
| while read id name; do
    echo ">>> $name"
    curl -sSL -C - --retry 5 --retry-delay 5 \
      -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/octet-stream" \
      "https://api.github.com/repos/$REPO/releases/assets/$id" -o "/tmp/w/$name"
  done
```

> 网络不稳时务必带 `-C -`（断点续传）与 `--retry`；本仓库的上传过程就遇到过代理中断。

## 校验

```bash
cd /tmp/w && sha256sum -c <<'EOF'
ec6706e8a904bba8a195d542921f54c6ce058f8d0d7a9aaeb91f117237d4a4fa  contextformer_official__seed42.ckpt
644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd  historical_boundary80__checkpoint_boundary80.pt
2c5d084236716d84d1ed11289248a501a7cb906675a32ccb8fd73e1f2a26881c  phase1_b4_teacher__checkpoint_best.pt
EOF
```

## 放回

```bash
mkdir -p checkpoints/contextformer_official/contextformer6M \
         archive/07_WEIGHTS_AND_PROVENANCE/historical_boundary80_release \
         archive/07_WEIGHTS_AND_PROVENANCE/phase1_b4_teacher
mv /tmp/w/contextformer_official__seed42.ckpt              checkpoints/contextformer_official/contextformer6M/seed42.ckpt
mv /tmp/w/historical_boundary80__checkpoint_boundary80.pt  archive/07_WEIGHTS_AND_PROVENANCE/historical_boundary80_release/checkpoint_boundary80.pt
mv /tmp/w/phase1_b4_teacher__checkpoint_best.pt            archive/07_WEIGHTS_AND_PROVENANCE/phase1_b4_teacher/checkpoint_best.pt
```
