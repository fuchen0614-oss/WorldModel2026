# SELECTION_GUIDE — 选图指南

面向“从候选图库挑图放进正文”的场景。编号与 `gallery/prediction/`、`gallery/weather/` 中的文件名一一对应，也与缩略图页对应。

## 1. 正文应覆盖哪些科学现象

| 现象 | 建议类别 | 候选编号 |
|---|---|---|
| 常规条件下的预测水平（第三部分基础） | `typical` | P07, P08, P15, P16, P23, P24, P31, P32 |
| 变化幅度大、空间结构清楚 | `high_change` | P01, P02, P09, P10, P17, P18, P25, P26 |
| 目标窗口内单调趋势（生长/衰落过程） | `seasonal_trend` | P04, P05, P12, P13, P20, P21, P28, P29 |
| 窗口内出现转折（不同变化过程） | `turn_point` | P06, P14, P22, P30 |
| 云与有效像素受限的困难案例 | `low_validity` | P03, P11, P19, P27 |

## 2. 信息重复、不建议同时使用的候选

同一 `cube` 的不同 `season` 是**不同样本**（不同 dataset_index），但空间格局相同，同时放进正文会显得重复。下表按 cube 分组，每组建议最多取一个：

| cube | 候选编号 |
|---|---|
| minicube_223_34TEL_40.70_21.54 | P05, P13 |
| minicube_153_33TXJ_43.46_16.80 | P07, P09 |

## 3. 受云、有效像素或缺失基线限制的候选

**展示步规则（预先登记）**：浏览页与缩略图统一取**该样本有效像素比例最高的那一步**（并列取较晚者）并在每格标注真实步号；详细对比页固定 t+5 / t+10 / t+20 并给出逐步覆盖条。规则对所有模型与所有候选一致。下表按平均有效比例列出覆盖最差的候选：

| 候选编号 | split | 类别 | valid_fraction | 无有效像素的步数 |
|---|---|---|---:|---:|
| P19 | ood-s_chopped | low_validity | 0.150 | 14 |
| P03 | iid_chopped | low_validity | 0.150 | 16 |
| P27 | ood-st_chopped | low_validity | 0.150 | 14 |
| P11 | ood-t_chopped | low_validity | 0.150 | 14 |
| P26 | ood-st_chopped | high_change | 0.294 | 11 |
| P25 | ood-st_chopped | high_change | 0.295 | 10 |

**所有候选共同的限制：** 基线（Contextformer / PredRNN / ConvLSTM / SimVP）的空间预测在本服务器上不可用，图库只能展示 Ground truth / Persistence / TerraState-C1。这不是选样问题，缺的是预测文件与权重本身。

## 4. 代表案例与困难案例

- **代表案例**：`typical` 与 `high_change` 类的候选——覆盖良好、现象清楚，适合放正文。

- **困难案例**：`low_validity` 类候选——有效像素少，预测更难，适合用来说明方法的适用范围与限制，而不是当作失败案例渲染。

- **过程案例**：`seasonal_trend` 与 `turn_point` 类——展示不同变化过程，用于说明模型跟随真实演化而非复制历史。


## 5. 推荐暂选及理由

| 用途 | 暂选编号 | split | 类别 | 理由 |
|---|---|---|---|---|
| basis_typical | P07 | iid_chopped | typical | 空间结构清楚、覆盖良好，作为常规代表 |
| basis_changed | P01 | iid_chopped | high_change | 变化幅度最大，能看出模型跟随真实变化 |
| suffix_turn | P14 | ood-t_chopped | turn_point | 窗口内出现转折，展示不同变化过程 |
| suffix_trend | P20 | ood-s_chopped | seasonal_trend | 趋势最明显，覆盖不同分布的划分 |
| hard_case | P27 | ood-st_chopped | low_validity | 有效像素最少的合规样本，用于交代适用范围 |

暂选依据是**可解释的展示属性**（覆盖、变化过程、空间结构、分布覆盖），**不是**“哪个模型赢得最多”。候选集合在读取任何模型逐样本结果之前就已冻结（见 `manifests/PREDICTION_CANDIDATES.csv` 及其选样规则说明）。


## 6. 天气候选

| 编号 | q3 序号 | tile | receiver | control |
|---|---:|---|---|---|
| W01 | 0 | 32TPR | minicube_103_32TPR_45.49_10.47 | minicube_97_32TNR_45.45_9.59 |
| W02 | 8 | 30STJ | minicube_23_30STJ_39.19_-5.73 | minicube_64_31TCG_41.73_1.24 |
| W03 | 15 | 29SQB | minicube_6_29SQB_37.12_-5.86 | minicube_29_30TWK_40.05_-2.43 |
| W04 | 23 | 34TET | minicube_224_34TET_47.72_21.24 | minicube_238_34TFT_47.29_22.46 |
| W05 | 30 | 32TPR | minicube_103_32TPR_45.49_10.47 | minicube_112_32TQM_42.36_12.39 |
| W06 | 38 | 33TYM | minicube_160_33TYM_46.19_17.62 | minicube_154_33TXJ_43.62_16.81 |
| W07 | 45 | 34TDQ | minicube_219_34TDQ_45.04_20.93 | minicube_208_34TCQ_44.74_18.50 |
| W08 | 53 | 30TTK | minicube_24_30TTK_39.99_-6.07 | minicube_9_29TNE_40.49_-7.88 |
| W09 | 60 | 30TWM | minicube_32_30TWM_42.08_-2.23 | minicube_62_31TBF_41.07_0.71 |
| W10 | 68 | 30TYR | minicube_46_30TYR_45.49_0.70 | minicube_66_31TCN_47.02_1.44 |
| W11 | 75 | 31TEJ | minicube_78_31TEJ_43.47_3.31 | minicube_74_31TDJ_43.31_2.71 |
| W12 | 83 | 31TBF | minicube_60_31TBF_41.35_-0.04 | minicube_63_31TCG_41.48_0.66 |

天气候选全部来自**冻结的 Q3 配对列表**，按等距规则取 12 个，不按结果挑选。`donor` / `mean` 是反事实情景，**没有观测真值**；不使用“热旱下收益更大”这类未获支持的表述。

