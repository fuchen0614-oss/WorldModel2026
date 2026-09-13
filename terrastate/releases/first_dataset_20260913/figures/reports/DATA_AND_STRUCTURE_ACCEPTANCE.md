# 数据与结构验收记录

结果：通过。

| 检查 | 实际 | 期望 | 状态 |
|---|---:|---:|---|
| Fig3 browse PNG | 60 | 60 | PASS |
| Fig3 contact pages | 12 | 12 | PASS |
| Fig3 selection rows | 12 | 12 | PASS |
| Fig7 candidate browse PNG | 16 | 16 | PASS |
| Fig7 contact pages | 4 | 4 | PASS |
| Fig7 selection rows | 16 | 16 | PASS |
| Fig8 candidate browse PNG | 12 | 12 | PASS |
| Fig8 contact pages | 2 | 2 | PASS |
| Fig8 selection rows | 4 | 4 | PASS |
| 图1_科学问题框架 README | 1 | 1 | PASS |
| 图1_科学问题框架 source manifest | 1 | 1 | PASS |
| 图1_科学问题框架 selection record | 1 | 1 | PASS |
| 图2_方法与监督框架 README | 1 | 1 | PASS |
| 图2_方法与监督框架 source manifest | 1 | 1 | PASS |
| 图2_方法与监督框架 selection record | 1 | 1 | PASS |
| 图3_标准空间预测 README | 1 | 1 | PASS |
| 图3_标准空间预测 source manifest | 1 | 1 | PASS |
| 图3_标准空间预测 selection record | 1 | 1 | PASS |
| 图4_第二数据集_延期 README | 1 | 1 | PASS |
| 图4_第二数据集_延期 source manifest | 1 | 1 | PASS |
| 图4_第二数据集_延期 selection record | 1 | 1 | PASS |
| 图5_时距与分布偏移 README | 1 | 1 | PASS |
| 图5_时距与分布偏移 source manifest | 1 | 1 | PASS |
| 图5_时距与分布偏移 selection record | 1 | 1 | PASS |
| 图6_分段稳定性 README | 1 | 1 | PASS |
| 图6_分段稳定性 source manifest | 1 | 1 | PASS |
| 图6_分段稳定性 selection record | 1 | 1 | PASS |
| 图7_共同后缀与状态作用 README | 1 | 1 | PASS |
| 图7_共同后缀与状态作用 source manifest | 1 | 1 | PASS |
| 图7_共同后缀与状态作用 selection record | 1 | 1 | PASS |
| 图8_天气条件响应 README | 1 | 1 | PASS |
| 图8_天气条件响应 source manifest | 1 | 1 | PASS |
| 图8_天气条件响应 selection record | 1 | 1 | PASS |
| 图9_状态复用成本 README | 1 | 1 | PASS |
| 图9_状态复用成本 source manifest | 1 | 1 | PASS |
| 图9_状态复用成本 selection record | 1 | 1 | PASS |
| OVERVIEW relative links | 12 | 12 | PASS |
| direct overview relative links | 12 | 12 | PASS |

## 科学边界核对

- 图3候选池在模型误差读取前冻结；P01–P32旧映射保留，P33–P60无冲突。
- 图3主选P42使用官方seed-42配置与checkpoint完成四个基线推理；严格加载结果和哈希已记录，未以近似模型替代。
- 图5沿用完整冻结范围与三种子样本标准差，不把标准差写成置信区间。
- 图6 A仅使用合法配对的标准预测记录；B单独展示九个C1分段集合；1.05明确为MSE比值门限。
- 图7轨迹、区间、receiver分布和分箱关联均由冻结逐receiver、逐后缀记录计算；分箱中位数不代替主口径均值，只称关联。
- 图8总体字段只用于总体面板；个案来自真实actual/donor/mean路径；donor/mean无反事实GT。
- 图9实测阶段成本与解析成本模型分面板；不画缺失的同协议精度—速度散点。
- 本轮没有训练或基线复现；仅执行官方checkpoint推理；未恢复FSR/SFR、未开展第二数据集。

## 链接

