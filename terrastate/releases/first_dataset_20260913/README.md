# first_dataset_20260913 — 第一数据集成果发布包

本目录是 **TerraState 第一数据集** 的一次性发布快照：代码索引、两份主文、终稿图、关键表格与
统计、必要的复现数组，以及来源与哈希。**只收录关键结果，不收中间产物。**

- 生成时间（UTC）：2026-09-13T10:24:37Z
- **科学基线提交**：`dc743eb75616`（产生本包全部数值与图件的代码/结果所处提交）
- 发布分支：`q4-eval-percube-eligibility`，远端 `git@github.com:fuchen0614-oss/WorldModel2026.git`
- **发布包提交序列**：`421f2cb` → `7a1223a` → `b19a1a1` → 后续修正；
  现查命令 `git log --oneline -- terrastate/releases/first_dataset_20260913`
- 规模：**277 个文件，66.9 MiB**
- 完整性：`SHA256SUMS.txt`（逐文件）；`QA_REPORT.md`（本轮验收）

## 怎么读

| 想做什么 | 从这里开始 |
|---|---|
| 快速理解主线与结论 | `narrative/01_TerraState_第一数据集成果总览_十二章继承更新版.md` |
| 直接用于论文写作 | `narrative/02_TerraState_中文论文叙事稿.md` |
| 看图选图 | `figures/OVERVIEW.md` → `figures/图*/selected/`（终稿）+ `figures/reports/FIGURE_CAPTIONS_ZH.md` |
| 核对某个数字 | `tables/`（8 张表 md+csv）→ `metrics/`（聚合 JSON） |
| 复现图与数字 | `reproduction/`（选定样本的数组与元数据）+ `figures/图*/code/` |
| 查来源与权重 | `SOURCE_COMMIT.md`、`CODE_AND_CONFIG_INDEX.md`、`WEIGHTS.md` |
| 核对"哪些文件被有意改过、为什么" | `provenance/RELEASE_EDITS.csv`（逐文件：原路径 / 原 sha256 / 本包 sha256 / 原因） |
| 重新独立验收本包 | `python code/verify_release.py --with-redraw`（含重绘逐像素比对） |

## 目录

```
README.md                 本文件
SOURCE_COMMIT.md          基线提交与每一项材料的来源路径
CODE_AND_CONFIG_INDEX.md  代码 / 协议 / 配置索引（含哈希）
WEIGHTS.md                正式权重清单：路径、字节数、SHA256、获取方式
QA_REPORT.md              本轮验收记录
SHA256SUMS.txt            逐文件哈希
narrative/                两份主文 + 参考文献 + 叙事 QA
figures/                  OVERVIEW + 9 个图目录（selected/ 终稿、code/、data/ 文本）+ references/
tables/                   8 张表（md + csv）
metrics/                  关键聚合指标（配对 bootstrap、运行时、天气审计、逐 seed 值）
reports/                  验收 / 主张矩阵 / 证据清单 / 缺口 / 展示方案 / 候选清单
reproduction/             选定样本的数组与候选清单
code/                     本包的构建 / 校验 / 修复脚本（11 个，可重跑）
provenance/               逐项来源与**有意修改**记录（RELEASE_EDITS.csv）
```

## 范围与排除（重要）

**收录**：两份主文；9 张终稿图及其绘图代码与文本数据；8 张表的 md+csv；
关键聚合 JSON；验收与缺口记录；**选定样本**（P42 / W02）的复现数组；正式权重清单；
被引用的参考文档；本包的构建/校验脚本与逐项来源记录。

**刻意排除**（都有理由，不是遗漏）：

| 排除内容 | 原因 |
|---|---|
| `figures/图*/candidates/`、`alternatives/`、`contact_sheets/` | 候选图库与备选图，属选图过程产物，已另行保存在运行目录 |
| `figures/图*/data/_arrays/`（P01…P60 全量数组，约 273 MiB） | 60 个候选的逐样本数组；仅保留终稿实际使用的 P42 / W02 |
| 训练日志、`runs/`、`__pycache__`、中断运行 | 过程产物 |
| milestone / 冒烟 / 已停止路线的中间权重 | 非正式权重 |
| 旧 closure / showcase 包的重复副本 | 上游包仍在原处，本目录只放精选 |
| 第二数据集空产物 | 本轮范围外（已延期） |
| `*.pt / *.pth / *.ckpt / *.safetensors` | 仓库配置了 Git LFS 过滤器而服务器未安装 git-lfs，权重走 `WEIGHTS.md` 记录的路径，见下文 |

## 关于权重（请注意）

本目录**不含权重文件**，原因是仓库根 `.gitattributes` 把 `*.pt` 等列入 Git LFS，而服务器没有安装
`git-lfs`；直接提交权重只会写入 133 字节的 LFS 指针，克隆方拿到的是指针而不是模型。
因此这里改为在 `WEIGHTS.md` 中给出**每个权重的路径、字节数与实测 SHA256**，
并说明获取方式。仓库历史提交 `ecb632c` 中的 `terrastate/sync_package_20260912_v1/checkpoints/`
就是这种情况（指针），请以 `WEIGHTS.md` 为准。

## 关于图3 的四个官方基线

终稿 **图3 包含四个官方基线**：ConvLSTM 1M、PredRNN 1M、SimVP 6M、Contextformer 6M，
全部来自**匹配的 GreenEarthNet 官方 seed-42 checkpoint**（协议、上游 commit 与权重校验见
`figures/图3_标准空间预测/data/OFFICIAL_BASELINE_WEIGHT_AUDIT.md` 与
`reproduction/P42_provenance.json`）。图中已无空行。

复现数组随包提供：`reproduction/P42_official_baselines.npz`（四个基线在 P42 上的预测）。
**四个官方 checkpoint 本体不在本包内**（体积原因）；其获取方式见
`reproduction/P42_provenance.json` 的 `official_release` 字段。

## 这份包不是什么

- 不是论文正文，也不是完整审计日志；它是**成果快照 + 来源索引**。
- 不包含第二数据集结论；只覆盖第一数据集。
- 不重跑实验：包内所有数字都来自已验收的冻结结果，本包只做整理与校验。

## 核对哈希（含 Windows 行尾说明）

Linux / macOS：

```bash
cd terrastate/releases/first_dataset_20260913
sha256sum -c SHA256SUMS.txt          # 应逐条 OK
```

**Windows 请注意**：本目录中有 **101 个文本文件在仓库里本身就是 CRLF 行尾**
（源包如此，本包逐字节复制、未做改动）。若本地 `core.autocrlf=true`（Windows 默认），
检出时会再次转换行尾，于是**这些文件的原始哈希会与 `SHA256SUMS.txt` 不一致**——
这是行尾转换，不是内容损坏。两种可靠的核对方式：

```powershell
# 方式一（权威，推荐）：让 git 自己判定
git -C <repo> status --porcelain -- terrastate/releases/first_dataset_20260913
# 输出为空 = 本地内容与已提交内容完全一致

# 方式二：关闭行尾转换后再检出并逐条核对
git -C <repo> -c core.autocrlf=false rm --cached -r --quiet terrastate/releases/first_dataset_20260913
git -C <repo> -c core.autocrlf=false checkout -- terrastate/releases/first_dataset_20260913
```

> `core.autocrlf` 影响整个仓库的检出行为；如只需核对本包，用方式一即可。
> 另外 19 个文本文件带 UTF-8 BOM，同样来自源包、原样保留。

## 文字勘误轮（2026-09-13 晚）

在不动任何图片、数值与统计口径的前提下，本轮只修正已证实的**事实 / 范围 / 转写**错误：

- `history 130 → forecast 20` 更正为 **`history 10 → forecast 20（均为五日步）`**：GreenEarthNet 官方配置为 `context_length=10`，终稿图 3 的实际张量为 `context (10,128,128)` 与 `gt (20,128,128)`。`tables/`、`narrative/tables/` 与两份主文同步更正。
- 九个留出分段的 `composed/direct` 比值**按集合分列**：IID2856 `0.9923–1.0234`、dev476 `1.0005–1.0275`，不再合并成单一范围（dev476 为开发诊断集，报告方式必须与独立确认集分开）。
- C1 三种子 R²_LC 样本标准差范围更正为 **`2.9e-5 至 1.9e-4`**（原写 `6.5e-5 到 2.2e-4`，与冻结的 `Table1_standard_prediction.csv` 不符）。
- 图 3 行序、图 7A 布局描述、图 9A 阶段清单与图 8A 区间口径**按实际成图**改写；图 7 的验收记录与尺寸按 18:45 的重绘结果更新（2192×1810 / 476051 B）。
- 分段对照不再写“显著改善”，并明示本轮未做比值层面的配对显著性检验。

同时**删除**了此前位于本目录根部、未被 git 跟踪的 `02_TerraState_中文论文叙事稿.pdf`（约 4.1 MB）：
它是修正前文字的排版产物，保留会与 `narrative/02_TerraState_中文论文叙事稿.md` 不一致。

改动逐条登记在 `provenance/RELEASE_EDITS.csv`（`edit_kind = wording_correction_20260913`），
`SHA256SUMS.txt` 已按同一约定刷新（更新 20 条，并补入此前遗漏的 `QA_REPORT.md` 与
`figures/reports/SHA256SUMS.txt`，共 276 条）。
