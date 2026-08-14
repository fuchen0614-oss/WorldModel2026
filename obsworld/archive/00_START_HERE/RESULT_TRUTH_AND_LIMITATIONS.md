# Stage 1/1.5 结果真值与限制

## 已支持

- Stage 1 训练、FSDP full-state checkpoint 保存和单卡加载链路已打通。
- Stage 1.5 双端条件化、显式 state projector、state reconstruction bridge、VICReg alignment、phi cross-covariance 和 feature anchor 均有对应代码。
- 30k → 60k：
  - alignment loss：15.19 → 12.63，跨模态一致性继续改善；
  - S2 reconstruction MAE：0.0498 → 0.0421；
  - nuisance loss 约 0.013，线性约束保持低位。

## 未支持

60k 没有改善非线性 \(\phi\) 解耦：

| Probe | Stage 1 | Stage 1.5 30k | Stage 1.5 60k | 结论 |
|---|---:|---:|---:|---|
| S2 sun elevation MAE | 7.12° | 10.14° | 10.25° | 有变化，但远未接近随机水平 |
| S1 orbit direction accuracy | 65.4% | 70.7% | 71.2% | 泄漏未消除 |
| S1 satellite accuracy | 65.6% | 66.3% | 67.5% | 泄漏未消除 |

因此不能写：

- “state 已实现完整成像不变性”；
- “非线性成像信息已经被去除”；
- “Stage 1.5 学到了完整物理地表状态”。

## 正确解释

cross-covariance 只直接约束线性相关，MLP probe 能发现非线性依赖。alignment 改善和 nuisance disentanglement 是两个不同目标；60k 的价值主要是更强跨模态一致性，而不是更彻底的成像解耦。

## 为什么保留这个负结果

它决定后续算法应改进约束机制，而不是盲目延长训练。如果删除这条信息，未来很容易重复“多训一倍就会自然解耦”的错误假设。

