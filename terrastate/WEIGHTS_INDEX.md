# TerraState 权重索引

本仓库**不存放模型权重**（`.gitignore` 已排除 `*.pt` / `*.ckpt`）。全部权重存放在 GitHub Release。

| Release | 日期 | 资产 | 内容 |
|---|---|---:|---|
| [`weights-first-dataset-20260913`](https://github.com/fuchen0614-oss/WorldModel2026/releases/tag/weights-first-dataset-20260913) | 2026-09-13 | 4 | 第一数据集正式权重（C1 seed 42/27/97、C0R seed 42） |
| [`weights-terrastate-v1`](https://github.com/fuchen0614-oss/WorldModel2026/releases/tag/weights-terrastate-v1) | 2026-08-14 | 3 | Contextformer 官方权重、boundary80 历史权重、Phase-I B4 teacher |

## `weights-first-dataset-20260913` — 第一数据集正式权重（2026-09-13）

- **Release**：[`weights-first-dataset-20260913`](https://github.com/fuchen0614-oss/WorldModel2026/releases/tag/weights-first-dataset-20260913)
- 名称：TerraState First-Dataset Formal Weights · 4 个资产 / 176,955,684 字节（约 168.8 MiB）
- 目标提交：`c8dac4b352de2f3048c42db9d1a155bac7946216`
- 模型：`TerraStateCandidateC`，7,180,896 参数，255 个状态张量

| Release 资产名 | 仓库内路径 | 字节数 | SHA-256 |
|---|---|---:|---|
| `c1_seed42_checkpoint_main.pt` | `terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt` | 44239001 | `474f94340763e9ba5b7373316ff4d09b69fa398d3fac2df291b9bf9846a93819` |
| `c0r_seed42_checkpoint_main.pt` | `terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c0r_20260823T063516Z/checkpoint_main.pt` | 44239001 | `7051e04afc541100233b26af98cf63ae664a311e09076e4bcf0795fee98888a2` |
| `c1_seed27_checkpoint_main.pt` | `terrastate/sync_package_20260912_v1/checkpoints/c1_seed27_checkpoint_main.pt` | 44238937 | `bdb6486a6d4b0b708683909b8a1b3b4814167964f4e8770e5f3e4106b7ebdfba` |
| `c1_seed97_checkpoint_main.pt` | `terrastate/sync_package_20260912_v1/checkpoints/c1_seed97_checkpoint_main.pt` | 44238745 | `8e193b1e104a9a5aed56fcc62275775c57a7c8ddf11c585716797e3099d684f9` |

用途：

- **c1_seed42_checkpoint_main.pt** — C1 seed 42 — 主臂（recursive endpoint training）
- **c0r_seed42_checkpoint_main.pt** — C0R seed 42 — 机制对照（direct endpoint training）
- **c1_seed27_checkpoint_main.pt** — C1 seed 27 — 多种子稳定性
- **c1_seed97_checkpoint_main.pt** — C1 seed 97 — 多种子稳定性

下载（无需 `gh`，只需 `repo` scope 的 token）：

```bash
export GITHUB_TOKEN=<your-token>
REPO=fuchen0614-oss/WorldModel2026
mkdir -p /tmp/w && cd /tmp/w
curl -sSL --retry 5 -C - -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/$REPO/releases/tags/weights-first-dataset-20260913" \
| python3 -c "import sys,json;[print(a['id'],a['name']) for a in json.load(sys.stdin)['assets']]" \
| while read id name; do
    echo ">>> $name"
    curl -sSL --retry 5 -C - -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "Accept: application/octet-stream" \
      "https://api.github.com/repos/$REPO/releases/assets/$id" -o "$name"
  done
```

校验：

```bash
cd /tmp/w && sha256sum -c <<'EOF'
474f94340763e9ba5b7373316ff4d09b69fa398d3fac2df291b9bf9846a93819  c1_seed42_checkpoint_main.pt
7051e04afc541100233b26af98cf63ae664a311e09076e4bcf0795fee98888a2  c0r_seed42_checkpoint_main.pt
bdb6486a6d4b0b708683909b8a1b3b4814167964f4e8770e5f3e4106b7ebdfba  c1_seed27_checkpoint_main.pt
8e193b1e104a9a5aed56fcc62275775c57a7c8ddf11c585716797e3099d684f9  c1_seed97_checkpoint_main.pt
EOF
```

放回：

```bash
cd /path/to/WorldModel2026
cp /tmp/w/c1_seed42_checkpoint_main.pt  terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt
cp /tmp/w/c0r_seed42_checkpoint_main.pt terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c0r_20260823T063516Z/checkpoint_main.pt
cp /tmp/w/c1_seed27_checkpoint_main.pt  terrastate/sync_package_20260912_v1/checkpoints/c1_seed27_checkpoint_main.pt
cp /tmp/w/c1_seed97_checkpoint_main.pt  terrastate/sync_package_20260912_v1/checkpoints/c1_seed97_checkpoint_main.pt
```

> **历史 LFS 指针不可用**：提交 `ecb632c` 中 `terrastate/sync_package_20260912_v1/checkpoints/`
> 下的同名文件是 **133 字节的 LFS 指针**（克隆后拿到的是文本而非模型）。它们**不会被改写**；
> 请一律以本 Release 的资产为准。
>
> `fsr_seed42_checkpoint_main.pt`（fixed-index-step 变体）**不在**本 Release 内：它是历史登记项，
> 本轮分析范围外（已延期）；文件仍在服务器原处，未移动、未删除。

## `weights-terrastate-v1` — 清单

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
