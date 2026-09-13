# QA_REPORT — first_dataset_20260913

对本发布包做的机械验收。所有检查都重新读盘，不依赖任何先前结论；
重绘类检查（`--with-redraw`）会在临时副本中删掉图内数组后实际重画并逐像素比对。

| # | 检查 | 结果 | 细节 |
|---|---|---|---|
| 1 | QA/build tooling shipped inside the package | PASS | ['build_release.sh', 'gen_release_docs.py', 'verify_release.py', 'fix_links.py', 'check_links2.py', 'p1_fallback.py', 'p1b_readmes.py', 'p2a_fix_master.py', 'p1c_redraw.py', 'p3a_fixes.py', 'p3_diag.py'] |
| 2 | provenance/RELEASE_EDITS.csv written | PASS | 9 intentional edits recorded |
| 3 | every recorded edit actually exists in the package | PASS | [] |
| 4 | all top-level documents present | PASS | [] |
| 5 | narrative carries both main documents | PASS | 01 十二章继承更新版 + 02 中文论文叙事稿 |
| 6 | nine figure directories present | PASS | ['图1_科学问题框架', '图2_方法与监督框架', '图3_标准空间预测', '图4_第二数据集_延期', '图5_时距与分布偏移', '图6_分段稳定性', '图7_共同后缀与状态作用', '图8_天气条件响应', '图9_状态复用成本'] |
| 7 | exactly 18 selected figure files (9 PNG + 9 PDF) | PASS | 18 files = 9 PNG + 9 PDF |
| 8 | tables count is 16 (8 tables x md+csv) | PASS | 16 files |
| 9 | metrics present | PASS | ['T1_per_seed_values.csv', 'T3_c0r_vs_c1_paired_bootstrap.json', 'T5_q3_extreme_state_audit.json', 'T7_c1_runtime.json'] |
| 10 | package file count in the expected range (250-300) | PASS | 277 files |
| 11 | three key NPZ present and loadable | PASS | ['reproduction/P42_arrays/arrays.npz', 'reproduction/P42_official_baselines.npz', 'reproduction/W02_arrays/arrays.npz'] |
| 12 | payload contains no weight-like / LFS-triggering files | PASS | [] |
| 13 | source trees still hold at least every original file (copy, not move) | PASS | ['first_dataset_figures_final_20260913T052645Z: 730 files (baseline 728)', 'first_dataset_narrative_dual_20260913T082412Z: 11 files (baseline 11)', 'first_dataset_closure_fix_20260911T081702Z: 130 files (baseline 130)'] |
| 14 | every shipped file is byte-identical to a source, or recorded in RELEASE_EDITS.csv | PASS | 0 unverified: [] |
| 15 | the two main documents differ from their source ONLY by the documented link rewrite | PASS | [] |
| 16 | master-draft fix preserves the original text (banner + 2 sentences + 9 unlinked images) | PASS | 619/630 source lines still present verbatim; changed=11 |
| 17 | narrative hash file: only the two intentionally rewritten docs differ | PASS | 3 entries; differing=['01_TerraState_第一数据集成果总览_十二章继承更新版.md', '02_TerraState_中文论文叙事稿.md']; unexpected=[] |
| 18 | every table is byte-identical to the frozen package | PASS | [] |
| 19 | every key aggregate JSON is byte-identical to the frozen package | PASS | [] |
| 20 | release contains no symlinks at all | PASS | [] |
| 21 | every relative reference in every markdown file resolves | PASS | 88 checked, 0 broken: [] |
| 22 | all figure links inside the two narrative documents resolve | PASS | 43 figure links of 53 references |
| 23 | 图3 caption names all four official baselines | PASS | all four present |
| 24 | 图3 analysis names all four official baselines | PASS | all four present |
| 25 | 图3 README names all four official baselines | PASS | all four present |
| 26 | the official-baseline NPZ holds all four arrays | PASS | ['contextformer', 'convlstm', 'predrnn', 'simvp'] |
| 27 | official-baseline provenance record present and non-trivial | PASS | 4870 B |
| 28 | no file still asserts that the official baselines are unavailable | PASS | scanned 112 markdown files |
| 29 | 图3_标准空间预测 render_final.py resolves its inputs from the slim package | PASS | fallback present and targets exist |
| 30 | 图3_标准空间预测 does not duplicate the arrays (the fallback is exercised) | PASS | figure-local _arrays absent by design |
| 31 | 图8_天气条件响应 render_final.py resolves its inputs from the slim package | PASS | fallback present and targets exist |
| 32 | 图8_天气条件响应 does not duplicate the arrays (the fallback is exercised) | PASS | figure-local _arrays absent by design |
| 33 | six redraw scripts present | PASS | 图3/5/6/7/8/9 |
| 34 | all six figures redraw in the slim package (figure-local arrays removed) | PASS | 6/6 rc=0 |
| 35 | redrawn PNGs are pixel-identical to selected/ | PASS | 9/9 identical; [] |
| 36 | redrawn PDFs are identical to selected/ apart from the embedded creation date | PASS | 9/9 identical after blanking /CreationDate |
| 37 | SHA256SUMS.txt written | PASS | 274 entries |
| 38 | sha256sum -c SHA256SUMS.txt passes with no failures and no warnings | PASS | 274 entries OK |
| 39 | no mode 120000 (symlink) entries in the git index for the release dir | PASS | 277 index entries, all regular |
| 40 | nothing outside the release directory is staged | PASS | 3 staged, all inside the release dir |
| 41 | no weight-like file is staged | PASS | 0 |
| 42 | WEIGHTS.md registers the live GitHub Release that carries the four formal weights | PASS | tag + asset count stated in WEIGHTS.md |
| 43 | WEIGHTS.md carries the full SHA256 of all four published weights (matches the frozen files) | PASS | 4/4 hashes present, byte-for-byte identical to the on-disk checkpoints |
| 44 | terrastate/WEIGHTS_INDEX.md links the new Release and keeps the older one | PASS | 8007 B index, both releases listed |
| 45 | the legacy 133-byte LFS pointers are documented as unusable, not rewritten | PASS | WEIGHTS.md + WEIGHTS_INDEX.md both flag them |
| 46 | FSR weight is explicitly excluded from the Release (out of scope this round) | PASS | exclusion stated in WEIGHTS.md and WEIGHTS_INDEX.md |

**合计 46 项：PASS 46，FAIL 0，SKIP 0。**

## 包概况

- 文件数：**277**
- 总大小：**67.0 MiB**
- 最大文件：`figures/图7_共同后缀与状态作用/data/ood_s_per_cube_horizon.csv`
- 逐文件哈希：`SHA256SUMS.txt`（274 条，`sha256sum -c` 已通过）
- 有意修改清单：`provenance/RELEASE_EDITS.csv`（9 条，逐条给出源路径与理由）

## 本轮定向修正（相对上一版发布包）

1. **一键重绘可在精简包内运行**：`图3` 与 `图8` 的 `render_final.py` 增加「优先图内、回退发布根」的输入解析，因此 `reproduction/` 只需保留一份数组，不再重复约 13 MiB。
2. **修正过时描述**：本报告的旧第 4 条曾称官方基线预测不可用——**该说法已作废**。终稿图3 含四个官方基线；同时修正了参考母稿 `figures/references/OVERVIEW_母稿_*.md` 中两处同类过时表述（加历史母稿横幅，未改任何数值与结论）。
3. **提交关系写清**：`SOURCE_COMMIT.md` / `README.md` 区分科学基线提交与发布包提交序列，且不再写入自指 HEAD。

## 已知限制（如实记录）

1. **权重不在包内**：仓库配置 Git LFS 而服务器未装 git-lfs，提交权重只会产生 133 字节指针。四个正式权重已通过 GitHub Release [`weights-first-dataset-20260913`](https://github.com/fuchen0614-oss/WorldModel2026/releases/tag/weights-first-dataset-20260913) 发布（4 个资产 / 176,955,684 字节），并已**逐一回下载复核**过字节数与 SHA256；路径、字节数与实测 SHA256 见 `WEIGHTS.md` 与 `terrastate/WEIGHTS_INDEX.md`。历史 LFS 指针保持原样，仅标明不可用。
2. **图7 的四个 per-cube CSV 占 46 MiB**（`ood_s` 20.1 + `ood_st` 15.4 + `iid` 6.1 + `ood_t` 4.6 MiB）。它们是逐 receiver × 逐时距的原始证据，是 Table 6B 可直接复核的底座，因此保留而未压缩；若仓库体积敏感，可改为 `.csv.gz`（读取方 `pandas.read_csv` 可直接识别）。
3. **候选图库未收录**：60 个预测候选与 12 个天气候选只保留终稿实际使用的 P42 / W02；完整候选图库仍在运行目录 `first_dataset_showcase_20260912T062326Z`。
4. **图3 的四个官方基线已包含在正式图中**（ConvLSTM 1M / PredRNN 1M / SimVP 6M / Contextformer 6M，来自匹配的 GreenEarthNet 官方 seed-42 checkpoint），复现数组见 `reproduction/P42_official_baselines.npz`，来源见 `reproduction/P42_provenance.json`。**本包不含四个官方 checkpoint 本体**（体积原因），获取方式见该 provenance 的 `official_release` 字段。
5. `narrative/figure references` 与 `figures/` 之间存在少量同名图片的重复（约 5 MiB），为保持两份主文可独立阅读而刻意保留。
6. **历史 LFS 指针**：提交 `ecb632c` 中 `terrastate/sync_package_20260912_v1/checkpoints/` 的5 个权重是 133 字节 LFS 指针，**不是可用权重**。本包不改写该历史，正式获取入口是新的 GitHub Release（见 `WEIGHTS.md`）。

## 文字勘误轮（2026-09-13 晚，追加记录）

上表 46 项是**发布包构建时**的验收结果，保持原样不改。此后进行了一轮**纯文字勘误**：不改图片本体、
不改任何表格数值、不重跑任何统计，只修正事实、范围与转写错误。

| 项 | 修正前 | 修正后 |
|---|---|---|
| 历史窗口 | `history 130` | `history 10`（五日步） |
| 九分段比值 | 合并为 `0.9923–1.0275` | IID2856 `0.9923–1.0234` / dev476 `1.0005–1.0275` 分列 |
| 三种子标准差 | `6.5e-5 – 2.2e-4` | `2.9e-5 – 1.9e-4` |
| 分段对照强度 | “显著改善” | “大幅改善”，并声明未做比值层面配对检验 |
| 图 3 行序 / 图 7A 布局 / 图 9A 阶段 / 图 8A 区间单位 | 与成图不符 | 与成图一致 |
| 图 7 验收记录 | 2318×2094 / 449098 B | 2192×1810 / 476051 B |

影响文件 23 个内容文件（含三处 `Table7_*.csv` 副本的 `conditions` 描述列，见
`provenance/RELEASE_EDITS.csv` 末 20 行 + 本轮补记，`edit_kind = wording_correction_20260913`），
`SHA256SUMS.txt` 已刷新（补入 `QA_REPORT.md`、`figures/reports/SHA256SUMS.txt`，共 276 条，逐条对照索引内容复核通过）。
构建期验收的其余结论（重绘逐像素一致、包内无 LFS 文件、无符号链接、链接全部可解析等）不受本轮影响。

另外删除了此前位于包根、**未被 git 跟踪**的 `02_TerraState_中文论文叙事稿.pdf`（约 4.1 MB）：
它是修正前文字的排版产物，保留会与 `narrative/02_TerraState_中文论文叙事稿.md` 不一致。

`figures/references/OVERVIEW_母稿_20260912T112243Z.md` 是**带“历史母稿，已被取代”横幅的归档副本**，
按归档原则保持原样（其中的 `history 130` 等表述属历史记录，不代表当前口径）。

