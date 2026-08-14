# WorldModel2026

本仓库同时承载**两个互不依赖的研究项目**，各自拥有独立根目录、独立文档与独立演化路线。
两者共享同一个 git 历史，但**代码上没有交叉依赖**——请不要在其中一个项目里 import 另一个。

```
terrastate/     项目一 · AAAI-27 投稿：TerraState 可检验预测状态世界模型
obsworld/       项目二 · ObsWorld：Stage 1 → 1.5 → Stage 2 观测表征与显式状态
```

## terrastate/ — TerraState（AAAI-27）

天气驱动的地表预报世界模型。围绕三个可检验问题构建：

- **Q1** 时间分布外（OOD-t）预报是否仍然有用
- **Q2** 移除状态中介的预报贡献是否会降低预测质量（load-bearing）
- **Q3** 真实未来天气是否比匹配供体/归一化均值控制更忠实

论文正文、补充材料与代码包见 [`terrastate/submission/`](terrastate/submission/)，
精选归档见 [`terrastate/archive/`](terrastate/archive/)。

## obsworld/ — ObsWorld

把遥感图像视为「地表状态在某成像条件下的有偏观测」，逐阶段构建：

```
历史遥感观测 + 成像条件 → 成像无关的地表状态
地表状态 + 外生驱动 + 地理先验 → 未来地表状态
未来地表状态 + 未来成像条件 → 未来遥感观测
```

Stage 1（SSL4EO MAE 预训练）→ Stage 1.5（成像条件解耦）→ Stage 2（EarthNet 动力学）。
入口见 [`obsworld/README.md`](obsworld/README.md)，精选归档见 [`obsworld/archive/`](obsworld/archive/)。

## 两个项目的关系

TerraState 在历史上从 ObsWorld 的研究线中分化出来（分叉点约在 2026-07-22，
对应 `思路整理进展/74`（Plan A）与 `75`（Plan B）两份执行引导）。分化之后：

- 两条线的**新增代码文件交集为 0**；
- TerraState 对 ObsWorld 底座的实际依赖只有 5 个文件，已各自复制一份，此后独立演化；
- 分化前的共同历史文档按「最终归属」硬分；少数确实跨越两条线的文档在两边各保留一份。

## 权重

仓库内**不存放任何模型权重**。全部走 GitHub Release：

| Release | 内容 | 索引 |
|---|---|---|
| [`weights-terrastate-v1`](https://github.com/fuchen0614-oss/WorldModel2026/releases/tag/weights-terrastate-v1) | 3 个 / 133.4 MB | [`terrastate/WEIGHTS_INDEX.md`](terrastate/WEIGHTS_INDEX.md) |
| [`weights-obsworld-v1`](https://github.com/fuchen0614-oss/WorldModel2026/releases/tag/weights-obsworld-v1) | 5 个 / 1.29 GB | [`obsworld/WEIGHTS_INDEX.md`](obsworld/WEIGHTS_INDEX.md) |

资产名是扁平化的（`来源目录__文件名`），下载后按索引里的对照表放回仓库内路径。
每个索引都给了 `gh` 与 `curl + token` 两种下载方式，并附 SHA-256 校验块。

## 服务器端使用

```bash
git clone <repo> && cd WorldModel2026
git checkout main
cd terrastate   # 或 cd obsworld
```

两个项目各自带 `requirements.txt` 与 `environment.worldmodel.yml`，可分别建环境。

## 历史分支

分化前后的完整开发历史保留在只读分支，不再合并、不再更新：

| 分支 | 内容 |
|---|---|
| `archive/plan-a-vits` | ObsWorld Plan A / A′（Stage2 延续、S1a、Table B） |
| `archive/plan-b-pvt` | TerraState 论文证据链（boundary80 evidence、OOD-t metrics、主表） |
| `archive/plan-b-v2-train` | TerraState-V2 训练与运维基建（no-FS pipeline、node-local launcher） |
