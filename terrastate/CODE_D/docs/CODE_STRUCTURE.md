# 代码结构与来源

`source_c1/`：从D-C1 seed42正式运行目录逐文件取回的源代码。
`source_c0r/`：从D-C0R seed42正式运行目录逐文件取回的源代码。
两份保留原貌，差异见 `manifests/c1_c0r_source_diff.json`；不能只按文件名判断相同。

各源码根目录内部：
- `models/`：模型结构；`spanworld_full_base.py`及CandidateC实现和编码器。
- `train/`：训练循环、阶段策略、参数冻结、checkpoint和验证。
- `data/`：数据集、天气契约、日历特征。
- `eval/`：标准精度等评价实现。
- `configs/`：历史配置原件。父权重字段可能为空，因为正式运行由命令行传入；不是父权重不存在。
- `tools/`：配套工具。

`configs/`：另行整理的可迁移D配置，不覆盖历史配置。
`evaluation_recipes/`：既有六表/固定40轮/消融的实现副本，部分仍依赖原执行器plan及路径，尚不能宣称独立运行。
`manifests/data/`：实际运行使用的数据划分和Q4清单。
`parent_metadata/`：父训练完成及选模记录。训练器要求父权重名为best_val.pt且同目录有summary.json。
`environment/`：历史环境说明与当前远端环境清单；当前环境不能自动等同历史训练环境。
`checkpoints/`：下载核验后的二进制（Git忽略）；父权重、三种子C1/C0R、固定40轮例外权重。

`manifests/results_files.json`引用原有成绩记录，没有生成与A08脱节的新表。
原始预测张量和重复备份不在发布范围。小型逐样本指标可作为统计复算输入。
