# Independent Reverse Review — Round 4

日期：2026-07-15  
判定：**CAUTION，8.7/10**  
原路线保留度：约 **89%**

## 最终判断

EarthNet-first 承担现实任务与官方 OOD 评估，D/G/H 承担受控地表动力学，Q/T/O 承担状态推断、演化和卫星观测形成。当前叙事已自洽，世界模型被落实为可组合转移、长期 rollout 和真实产品核验，不再只是标题。

当前文本没有继续被 EO-WM 带偏：“稀疏/部分观测”已回到背景，`phi`、DGH 与状态—转移—观测三柱恢复为主线。

Stage2 已达到可实施规格：共享 `T_theta`、`delta_t={5,10,20}`、按区间对齐的 24-D E-OBS forcing、direct-vs-composed 分支、两侧真实观测监督，以及无可学习 affine 参数的 LayerNorm 状态比较。

路线可以进入 `M0 + 单种子 Val pilot`，但尚不能宣布 AAAI 主张已成立。最终决定因素是两条约束能否共同改善 EarthNet 长期和 OOD 未来预测。

## 仍需通过的五个 Gate

1. 完整运行 product-axis × temporal-axis 四格 2×2；交互项不显著时只写 `jointly constrained`，不写 `synergistic`。
2. 完成 `M0-phi`：本地 L1C、key/time/file_id、common bands、cloud support 和 geographic holdout；数据 Gate 失败则固定为 S2-L2A decoder。
3. 四格保持相同 product-pair 数据量、更新次数、初始化起点、Stage2 schedule、D/C/G、参数量与 evaluator，只切换 `L_crossobs` 和 `L_part`。
4. 在主实验前冻结 5/10/20 日抽样比例、partition 组合、driver 拼接、mask、loss weights 和 rollout anchor。
5. AAAI 正文仅保留 Table 1、Table 2、horizon/composition Figure 和通过 Gate 后的 `phi` mini-table；附录不承担核心证据。

## 新颖性边界

Q/T/O、跨观测解码、L1C/L2A translation、variable-step 或 partition consistency 都不是组件首创。方案层面新颖性约 4.5/10；若两轴 2×2、official OOD 竞争力、partition gain 无 forecast harm 以及 product-axis future utility 均成立，可提升到约 6–6.5/10 的可投区间。

安全的总贡献是：

> **在同一个非自治 DGH predictive state 上，联合施加跨产品观测约束和跨时间分割的控制感知组合约束，并验证它们的未来预测效用。**

## 最终建议

路线本身已可冻结，下一步不再大改叙事。先让 M0 和核心 2×2 决定它能否从可行方案升级为 AAAI 主张。
