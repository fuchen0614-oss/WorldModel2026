# 复现状态与执行顺序

## 已落实
- 从实际远端运行目录取回C1/C0R代码及两份数据划分清单；逐文件核验SHA。
- 父权重身份：438e8d93505827ce2a1b7ffaef78b64e46e5d65920cf79af25305af5b72e10fb。
- 配置：D，global batch32，4卡×每卡8，100epoch/74500更新，seed27/42/97；具体参数以历史配置及checkpoint为准。
- 已有结果保持在A08/A51/A52及其原始CSV/JSON；发布索引记录文件SHA。

## 尚需闭合的发布验收
1. 权重下载完成后逐个核验SHA、epoch、step、初始化谱系；核实seed97最终完成记录。
2. 父权重连同summary.json整理为checkpoints/parent/best_val.pt。追溯父模型再上一层初始化及生成命令。
3. 核实多种子实际训练代码与seed42代码差异，不把同模型名称视为源码完全一致。
4. 补齐四split数据来源/预处理、扩展样本ID及接收方-供体配对清单的最终选择。
5. 将评价脚本中的执行器路径改为显式参数，完成标准评价、共同后缀、两类消融、天气/机制实验和表图统计入口映射。
6. 在干净环境运行导入、严格加载和小样本训练/评价；对照历史验收。语法检查不代表数值复现通过。
7. 审核A08及证据相对链接、发布文件隐私和第三方许可；仅提交明确清单，不使用git add全目录。
8. 发布Releases、写入下载URL、从全新checkout校验，再合入main。保留历史作者，不新增助手署名。

不重跑已验收的100epoch训练或全量评价；必要小样本验证单独留回执。

## 固定训练命令入口

已增加 `scripts/train_d.py`，C1/C0R×三个seed的生成配置均通过原训练器的配置策略校验。
默认只打印命令；传入 `--execute` 才实际启动。以下为Linux运行模板：

```bash
python CODE_D/scripts/train_d.py --arm C1 --seed 42 \
  --train-dir /data/greenearthnet/train \
  --val-dir /data/greenearthnet/val_chopped \
  --parent-dir CODE_D/checkpoints/parent \
  --output-dir /outputs/D_C1_seed42 --execute
```

C0R改为 `--arm C0R`；seed可以选27、42、97。该入口仅用于全新训练，不接管在训进程或恢复任务。
入口绑定4卡×8×1、历史数据SHA和父权重SHA；训练器仍会核验数据，不静默放宽验收。
尚待干净环境运行验证；不能把配置校验当作训练复现已通过。
