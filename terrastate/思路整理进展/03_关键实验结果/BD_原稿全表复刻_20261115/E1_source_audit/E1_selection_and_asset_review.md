# E1筛选条件与原始资产追溯

已连通历史主机zhisheng，确认原始目录存在：/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z。此前仅查909而未定位旧主机，不能据此认定清单不存在。

## 已由冻结协议与v2重建代码共同核实的规则
1. receiver/candidate来自同一split、同一观测起始年/月YYYY-MM，排除自身。
2. 匹配仅使用最初10帧历史观测：NDVI帧均值、帧标准差、末个有效帧均值、有效帧比例四维统计，以及归一化256-bin ESA WorldCover地类直方图。不可用未来NDVI、未来天气、目标mask或模型误差选donor。
3. 四维统计按训练校准池的冻结median/IQR标准化；IQR为零或非有限时按校准规则置1。缺失/非有限历史特征不可匹配。
4. 距离 = 标准化历史特征欧氏距离 + 0.5×Hellinger地类距离；Hellinger = ||sqrt(p)-sqrt(q)||₂/sqrt(2)。代码未附加距离阈值筛选。
5. receiver按路径稳定排序；候选取距离最小者，同距离按donor路径打破平局。donor全局复用上限1，无可用候选则不匹配。无匹配样本在两种预测条件同时剔除。
6. 必须使用v2_corrected_mask：历史mask契约优先s2_dlmask。早期相邻donor生成函数和旧校准版本不能替代修正版清单。

## 干预与统计（原稿）
只替换同一模型单段推进到第50天的状态；receiver自己的prior、地理条件、后续天气、目标日期与评分mask不变。55–100天与第100天分别确定资格；报告sample-equal/group-equal/pixel-pooled三种加权，2000次配对地理组bootstrap，seed20260910。IID/OOD-T/OOD-S/OOD-ST完整后缀参考N为2066/1605/6965/5437，day100为1214/884/3549/2731，须由清单和实际mask复核，不能硬塞人数。

## 已找到
- 四split matched_donor_rebuild_v2_corrected_mask_*_20260909T153000Z/matched_donor_manifest.csv。
- calibration_train_v2_corrected_mask_20260909T134000Z/calibration.json。
- corrected_mask_recompute_20260910T071500Z/merged/*/manifests/matched_donor_manifest.csv。
- code/rebuild_frozen_matched_donor_manifest_v2.py及其特征提取器、推理与证据汇总代码。
- 本地工作区tip_review_20260910也有旧推理与汇总代码，但包含旧实现，不能当作修正版最终筛选来源。

当前是资产定位与取回，不是新BD E1评价完成。还需确认修正清单与merged清单哈希一致、配对唯一性/非自身/同season和当前数据路径映射；之后BD共享同一冻结匹配，不重新挑donor。


## 取回验收补充
已从zhisheng取回31份代码/校准/清单/报告，全部与远端SHA一致。四份v2修正清单与最终merged清单逐字节相同。匹配成功数IID2078、OOD-T1632、OOD-S7065、OOD-ST5577；这些不是最终评价资格数，不能混用。零自身匹配，donor最大复用1。
特征精确定义修正：先计算每个历史帧有效像素NDVI均值，再对10个帧均值计算nanmean和nanstd（不是空间像素标准差）；取最后有限帧均值，以及有限帧占比。优先s2_dlmask，缺失才s2_mask，并结合s2_avail。校准23816文件中22723有效、1093无效；冻结median/IQR已取回。
