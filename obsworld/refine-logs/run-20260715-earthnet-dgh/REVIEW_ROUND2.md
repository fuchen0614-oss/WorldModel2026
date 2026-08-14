# Independent Reverse Review — Round 2

日期：2026-07-15  
原判定：REVISE，7.3/10

## 复审确认的优点

- 原始“状态推断—状态演化—观测生成”三柱已保留；
- D/G/calendar/elapsed time 与 `phi` 的角色已区分；
- predictive state 不再冒充唯一真实物理状态；
- GreenEarthNet 不能独立验证强 renderer 已写入 Gate；
- Stage1.5、G、phi、composition 都有失败降级路线；
- `U` 已回到扩展，不再绑架首篇中心叙事。

## 复审指出的主要缺口

1. 只有接口路由，仍可能被视为普通 conditional state-space model；
2. 旧稿使用未定义的 `T_10`，composition gap 缺少同一模型内定义；
3. S1/S2 同日不是纯 observation-operator pair；
4. full E-OBS 与 Direct/rollout 的 matched-input 规则不够严格；
5. 七页正文实验过载；
6. Green official split 与 original Extreme/Seasonal 混写；
7. context initializer 未冻结成一种方法。

## 本轮落实的修改

- 方法名收敛为 role-separated predictive-state EO world model；
- 增加 target-condition cross-observation training constraint；
- 定义共享参数的 5/10/20-day variable-step transition；
- 在同一模型内定义 direct/composed partition consistency；
- 固定轻量 history initializer；
- L1C/L2A 作为唯一强 product-conditioned Gate，S1/S2 只作 cross-modal state evidence；
- Direct/rollout 使用完全相同 raw daily E-OBS、history weather 和 driver encoder；
- G 使用完整跨 location 置换，不随机打乱像素；
- 正文压缩为 Table 1、Table 2、Figure 1、可删除的 phi mini-result；
- 原始 EarthNet Extreme/Seasonal 移至 secondary diagnostics。

