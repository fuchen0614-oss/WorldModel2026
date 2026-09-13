# first_dataset_20260913 — 第一数据集成果发布包

本目录是 **TerraState 第一数据集** 的一次性发布快照：代码索引、两份主文、终稿图、关键表格与
统计、必要的复现数组，以及来源与哈希。**只收录关键结果，不收中间产物。**

- 生成时间（UTC）：2026-09-13T09:10:26Z
- 基线提交：`dc743eb75616`（分支 `q4-eval-percube-eligibility`，远端 `git@github.com:fuchen0614-oss/WorldModel2026.git`）
- 规模：**219 个文件，66.2 MiB**
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

## 目录

```
README.md                 本文件
SOURCE_COMMIT.md          基线提交与每一项材料的来源路径
CODE_AND_CONFIG_INDEX.md  代码 / 协议 / 配置索引（含哈希）
WEIGHTS.md                正式权重清单：路径、字节数、SHA256、获取方式
QA_REPORT.md              本轮验收记录
SHA256SUMS.txt            逐文件哈希
narrative/                两份主文 + 参考文献 + 叙事 QA
figures/                  OVERVIEW + 9 个图目录（selected/ 终稿、code/、data/ 文本）
tables/                   8 张表（md + csv）
metrics/                  关键聚合指标（配对 bootstrap、运行时、天气审计、逐 seed 值）
reports/                  验收 / 主张矩阵 / 证据清单 / 缺口 / 展示方案 / 候选清单
reproduction/             选定样本的数组与候选清单
```

## 范围与排除（重要）

**收录**：两份主文；9 张终稿图及其绘图代码与文本数据；8 张表的 md+csv；
关键聚合 JSON；验收与缺口记录；**选定样本**（P42 / W02）的复现数组；正式权重清单。

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

## 这份包不是什么

- 不是论文正文，也不是完整审计日志；它是**成果快照 + 来源索引**。
- 不包含第二数据集结论；只覆盖第一数据集。
- 不重跑实验：包内所有数字都来自已验收的冻结结果，本包只做整理与校验。
