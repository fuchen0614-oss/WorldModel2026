# WEIGHTS — 正式权重清单

本包**不包含**权重文件：仓库根 `.gitattributes` 将 `*.pt / *.pth / *.ckpt / *.safetensors` 交由 Git LFS 管理，而本服务器**未安装 git-lfs**。若直接提交，写进仓库的只会是 133 字节的 LFS 指针（历史提交 `ecb632c` 中的 `sync_package_20260912_v1/checkpoints/` 正是如此），克隆方拿到的是指针而非模型。因此这里给出**实测**的路径、字节数与 SHA256。

## 支撑当前结论的正式权重

| 权重 | 仓库内路径 | 字节 | SHA256（实测） |
|---|---|---:|---|
| C1 seed 42 (recursive endpoint training, main arm) | `terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt` | 44,239,001 | `474f94340763e9ba5b7373316ff4d09b69fa398d3fac2df291b9bf9846a93819` |
| C0R seed 42 (direct endpoint training, mechanism control) | `terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c0r_20260823T063516Z/checkpoint_main.pt` | 44,239,001 | `7051e04afc541100233b26af98cf63ae664a311e09076e4bcf0795fee98888a2` |
| C1 seed 27 (multi-seed stability) | `terrastate/sync_package_20260912_v1/checkpoints/c1_seed27_checkpoint_main.pt` | 44,238,937 | `bdb6486a6d4b0b708683909b8a1b3b4814167964f4e8770e5f3e4106b7ebdfba` |
| C1 seed 97 (multi-seed stability) | `terrastate/sync_package_20260912_v1/checkpoints/c1_seed97_checkpoint_main.pt` | 44,238,745 | `8e193b1e104a9a5aed56fcc62275775c57a7c8ddf11c585716797e3099d684f9` |
| FSR seed 42 (fixed-index-step endpoint variant -- historical registration only) | `terrastate/sync_package_20260912_v1/checkpoints/fsr_seed42_checkpoint_main.pt` | 44,238,937 | `71fa03d313259ba29d8106de5248f5118b94a9bac796a0dacd3015b120e4c97b` |

## 与 E1 交付记录的交叉核对

E1 交付 CSV 中记录的 `checkpoint_sha256`（截断形式）：

| seed | 记录的哈希 |
|---|---|
| 27 | `bdb6486a6d4b0b708683909b8a1b3b4814167964f4e8770e5f3e4106b7ebdfba` |
| 42 | `474f94340763e9ba5b7373316ff4d09b69fa398d3fac2df291b9bf9846a93819` |
| 97 | `8e193b1e104a9a5aed56fcc62275775c57a7c8ddf11c585716797e3099d684f9` |

> 说明：上表为本包**重新计算**的完整 SHA256；E1 CSV 中记录的是截断值，两者前缀一致即为同一文件。

## 三个 C1 权重的关系

C1 seed 27 / 42 / 97 是同一次多 seed 标准评测的三个训练种子；Table 1 的 `均值 ± 样本标准差(ddof=1, n=3)` 就来自这三个权重，它是**种子离散度**，不是置信区间（见 `tables/Table1_standard_prediction.md`）。

## 获取方式

**首选：GitHub Release [`weights-first-dataset-20260913`](https://github.com/fuchen0614-oss/WorldModel2026/releases/tag/weights-first-dataset-20260913)**（TerraState First-Dataset Formal Weights，4 个资产，约 168.6 MiB）。资产名与仓库内路径的对应见上表；该 Release 的每个资产都已**回下载复核过字节数与 SHA256**。

无需 `gh`（本服务器未安装），只要有 `repo` scope 的 token：

```bash
export GITHUB_TOKEN=<your-token>
REPO=fuchen0614-oss/WorldModel2026
curl -sSL --retry 5 -C - -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/octet-stream" \
  "https://api.github.com/repos/$REPO/releases/tags/weights-first-dataset-20260913" \
| python3 -c "import sys,json;[print(a['id'],a['name']) for a in json.load(sys.stdin)['assets']]" \
| while read id name; do
    curl -sSL --retry 5 -C - -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "Accept: application/octet-stream" \
      "https://api.github.com/repos/$REPO/releases/assets/$id" -o "/tmp/w/$name"
  done
```

其他方式：

1. **直接从服务器复制**：上表路径在 dilab 上可直接 `scp`（无需 LFS、无需 token）。
2. **修复 LFS 后重推**：安装 `git-lfs` 并 `git lfs push --all origin`，可把历史指针补成真实对象；但这会改动已推送历史，需谨慎。

### 历史 LFS 指针不可用

历史提交 `ecb632c` 中 `terrastate/sync_package_20260912_v1/checkpoints/` 下的同名文件是 **133 字节的 LFS 指针**，克隆后拿到的是文本而非模型。它们**不会被改写**；请一律以本 Release 的资产为准。

### 未随本 Release 发布的权重

`fsr_seed42_checkpoint_main.pt`（fixed-index-step 变体）是历史登记项，本轮分析范围外（已延期）；其文件仍在服务器上原处，未移动、未删除。

## 复核命令

```bash
# 服务器上直接核对（与本文件表格逐项比对）
sha256sum terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt
sha256sum terrastate/sync_package_20260912_v1/checkpoints/c1_seed27_checkpoint_main.pt
sha256sum terrastate/sync_package_20260912_v1/checkpoints/c1_seed97_checkpoint_main.pt
sha256sum terrastate/ops/candidate_c_nightly/20260820T155316Z/formal/run_c0r_20260823T063516Z/checkpoint_main.pt
```

