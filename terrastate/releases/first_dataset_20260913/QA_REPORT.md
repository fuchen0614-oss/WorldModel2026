# QA_REPORT — first_dataset_20260913

对本发布包做的机械验收。所有检查都重新读盘，不依赖任何先前结论。

| 检查 | 结果 | 细节 |
|---|---|---|
| all top-level documents present | PASS | [] |
| narrative carries both main documents | PASS | 01 十二章继承更新版 + 02 中文论文叙事稿 |
| nine figure directories present | PASS | ['图1_科学问题框架', '图2_方法与监督框架', '图3_标准空间预测', '图4_第二数据集_延期', '图5_时距与分布偏移', '图6_分段稳定性', '图7_共同后缀与状态作用', '图8_天气条件响应', '图9_状态复用成本'] |
| selected figures present | PASS | 18 files |
| tables count is 16 (8 tables x md+csv) | PASS | 16 files |
| metrics present | PASS | ['T1_per_seed_values.csv', 'T3_c0r_vs_c1_paired_bootstrap.json', 'T5_q3_extreme_state_audit.json', 'T7_c1_runtime.json'] |
| reproduction arrays present | PASS | P42 arrays + P42 official baselines + W02 arrays |
| payload contains no LFS-triggering weights | PASS | [] |
| source trees still hold every original file | PASS | [] |
| every shipped file is a byte-identical copy of a source file | PASS | 0 unverified: [] |
| narrative copies match the narrative package's own hash file | PASS | 3 entries checked, mismatches=[] |
| every table is byte-identical to the frozen package | PASS | [] |
| SHA256SUMS.txt written | PASS | 222 entries |

**合计 13 项，FAIL 0 项。**

## 包概况

- 文件数：**225**
- 总大小：**66.3 MiB**
- 最大文件：figures/图7_共同后缀与状态作用/data/ood_s_per_cube_horizon.csv

## 已知限制（如实记录）

1. **权重不在包内**：仓库配置 Git LFS 而服务器未装 git-lfs，提交权重只会产生 133 字节指针。四个正式权重的路径、字节数与实测 SHA256 见 `WEIGHTS.md`。
2. **图7 的四个 per-cube CSV 占 46 MiB**（`ood_s` 20.1 + `ood_st` 15.4 + `iid` 6.1 + `ood_t` 4.6 MiB）。它们是逐 receiver × 逐时距的原始证据，是 Table 6B 可直接复核的底座，因此保留而未压缩；若仓库体积敏感，可改为 `.csv.gz`（读取方 `pandas.read_csv` 可直接识别）。
3. **候选图库未收录**：60 个预测候选与 12 个天气候选只保留终稿实际使用的 P42 / W02；完整候选图库仍在运行目录 `first_dataset_showcase_20260912T062326Z`。
4. **基线的空间预测文件在本服务器不可用**（官方权重与导出的预测都不在盘上），因此图件中的对比模型只有 Ground truth / Persistence / TerraState-C1；基线数值仍在 Table 1。
5. `narrative/figure references` 与 `figures/` 之间存在少量同名图片的重复（约 5 MiB），为保持两份主文可独立阅读而刻意保留。

