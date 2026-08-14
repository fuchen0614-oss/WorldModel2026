# ObsWorld 权重索引

本仓库**不存放模型权重**（`.gitignore` 已排除 `*.pt` / `*.ckpt`）。全部权重存放在 GitHub Release。

- **Release**：[`weights-obsworld-v1`](https://github.com/fuchen0614-oss/WorldModel2026/releases/tag/weights-obsworld-v1)
- 上传日期：2026-08-14 · 5 个资产 / 1.29 GB

## 清单

Release 资产名是扁平化的（用 `__` 连接来源目录），下载后请按「仓库内路径」放回。

| Release 资产名 | 仓库内路径 | 字节数 | SHA-256 |
|---|---|---:|---|
| `stage1_final__checkpoint_epoch200_step_95000.pt` | `archive/07_WEIGHT_PROVENANCE/weights/stage1_final/checkpoint_epoch200_step_95000.pt` | 327546060 | `79b20ee6ddc499c60019ed8590108e08789dcc0d8877d1892eb490b2cc5500df` |
| `stage1_5_final_state_bridge__checkpoint_step_60000.pt` | `archive/07_WEIGHT_PROVENANCE/weights/stage1_5_final_state_bridge/checkpoint_step_60000.pt` | 363727067 | `24646b89eda5fb97ff03a76da5c136969bd1e2af9d76d60bd9537b6e304ff97d` |
| `plan_a_s1a_full24__checkpoint_best.pt` | `archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/plan_a_s1a_full24/checkpoint_best.pt` | 335371774 | `2a0a465fe4d4a148a493954a8acc63b0e6e55896b12631cf3bd9efa08440fad5` |
| `rollout_physical4__checkpoint_best.pt` | `archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/rollout_physical4/checkpoint_best.pt` | 178271665 | `8908c62e40b6f71d7ca45aa74047ba2e0c719ea4bc2db7d9cef41587510ead31` |
| `direct_physical4__checkpoint_best.pt` | `archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/direct_physical4/checkpoint_best.pt` | 178271409 | `1158ffe6644e6a05345cba3fa56ee73af8d1390a2eb078b4b0bc3a94746f91d2` |

用途：

- **stage1_final** — Stage 1 最终权重（epoch 200 / 95k step）。
- **stage1_5_final_state_bridge** — Stage 1.5 最终权重（60k step，state bridge）。
- **plan_a_s1a_full24 / rollout_physical4 / direct_physical4** — Stage 2 延续（Plan A）的关键 best 权重。

## 重要边界（不要弱化）

Stage 1.5 的 60k 结果**没有**证明完整成像不变性：线性 cross-covariance 约束保持较低，
但非线性 MLP probe 仍能恢复部分 orbit/satellite 信息。该负结果被保留，后续设计必须正视它。

详见 `archive/00_START_HERE/RESULT_TRUTH_AND_LIMITATIONS.md`。

## 下载

有 `gh` CLI：

```bash
gh release download weights-obsworld-v1 --repo fuchen0614-oss/WorldModel2026 --dir /tmp/w
```

没有 `gh`（只需一个 `repo` scope 的 token）：

```bash
export GITHUB_TOKEN=<your-token>
REPO=fuchen0614-oss/WorldModel2026
mkdir -p /tmp/w
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/$REPO/releases/tags/weights-obsworld-v1" \
| python3 -c "import sys,json;[print(a['id'],a['name']) for a in json.load(sys.stdin)['assets']]" \
| while read id name; do
    echo ">>> $name"
    curl -sSL -C - --retry 5 --retry-delay 5 \
      -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/octet-stream" \
      "https://api.github.com/repos/$REPO/releases/assets/$id" -o "/tmp/w/$name"
  done
```

> 这几个文件 170–360 MB，网络不稳时务必带 `-C -`（断点续传）与 `--retry`；
> 本仓库的上传过程就遇到过代理中断导致资产停留在 `starter` 状态。

## 校验

```bash
cd /tmp/w && sha256sum -c <<'EOF'
79b20ee6ddc499c60019ed8590108e08789dcc0d8877d1892eb490b2cc5500df  stage1_final__checkpoint_epoch200_step_95000.pt
24646b89eda5fb97ff03a76da5c136969bd1e2af9d76d60bd9537b6e304ff97d  stage1_5_final_state_bridge__checkpoint_step_60000.pt
2a0a465fe4d4a148a493954a8acc63b0e6e55896b12631cf3bd9efa08440fad5  plan_a_s1a_full24__checkpoint_best.pt
8908c62e40b6f71d7ca45aa74047ba2e0c719ea4bc2db7d9cef41587510ead31  rollout_physical4__checkpoint_best.pt
1158ffe6644e6a05345cba3fa56ee73af8d1390a2eb078b4b0bc3a94746f91d2  direct_physical4__checkpoint_best.pt
EOF
```

## 放回

```bash
mkdir -p archive/07_WEIGHT_PROVENANCE/weights/{stage1_final,stage1_5_final_state_bridge} \
         archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/{plan_a_s1a_full24,rollout_physical4,direct_physical4}
mv /tmp/w/stage1_final__checkpoint_epoch200_step_95000.pt       archive/07_WEIGHT_PROVENANCE/weights/stage1_final/checkpoint_epoch200_step_95000.pt
mv /tmp/w/stage1_5_final_state_bridge__checkpoint_step_60000.pt archive/07_WEIGHT_PROVENANCE/weights/stage1_5_final_state_bridge/checkpoint_step_60000.pt
mv /tmp/w/plan_a_s1a_full24__checkpoint_best.pt                 archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/plan_a_s1a_full24/checkpoint_best.pt
mv /tmp/w/rollout_physical4__checkpoint_best.pt                 archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/rollout_physical4/checkpoint_best.pt
mv /tmp/w/direct_physical4__checkpoint_best.pt                  archive/08_STAGE2_CONTINUATION/03_KEY_WEIGHTS/direct_physical4/checkpoint_best.pt
```

## 从归档续训

见 `archive/00_START_HERE/RUN_FROM_ARCHIVE.md`（数据、配置与命令）。
