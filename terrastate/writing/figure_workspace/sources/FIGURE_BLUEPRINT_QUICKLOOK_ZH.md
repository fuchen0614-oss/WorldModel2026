# TerraState Figure 1–2 中文逻辑速览

这份文件只用于作者快速理解图的故事和数据流。最终英文论文图仍使用
`FIGURE_TEXT_COPY.md`中的英文标签。

## Figure 1：EO世界模型逻辑、TerraState能力与证据

```text
(a) 世界模型逻辑进入EO后，还留下什么验证缺口？

典型动作条件世界模型：
场景历史 → latent state → dynamics → future rollout
                            ↑
                          action

外生驱动下的EO世界建模：
稀疏EO历史 → 未观测地表状态 → EO dynamics → future EO
                                  ↑
                             future weather

二者共享观测—状态—转移—未来逻辑；EO的驱动是外生天气。
终点评分看到：output directly scored
终点评分看不到：state use ? / forcing use ?


(b) TerraState怎样把内部路径变得可操作、可检验？

历史上下文 → z_t → 共享天气条件T → z_{t+h} → O → r_h ─┐
                      ↑                                  ×│
             actual / matched donor / normalized mean   ▼
历史上下文 ───────────────→ 仅上下文预测 b_h ───────────⊕→ 预测

Q2：只切断状态贡献r_h；b_h仍产生预测。
Q3：只替换进入T的未来天气。


(c) 最小证据阶梯

Q1 预测效用
Useful OOD-t forecast
前提，不是充分证明
            ↓
Q2 承载预测的状态
Removing state contribution degrades skill
定义性核心证据
            ↓
Q3 天气响应忠实性
Actual weather outperforms controls
外部天气驱动落地
```

一句话总结：

> EO世界模型的驱动从action变为weather；TerraState让这条状态路径可干预，并用Q1–Q3分层检验。

## Figure 2：模型内部怎样运行

```text
真实历史EO、云掩膜、时间、历史天气、静态地理
                         │
                         ▼
                   q：上下文编码器
                    ├──────────────→ 上下文预测 b_h ──────────┐
                    ▼                                        │
                   P：状态投影器                              │
                    ▼                                        │
               显式预测状态 z_t                               │
                    │                                        │
未来天气 ───────────┼──→ 共享天气条件转移 T                    │
静态地理、时距 ─────┘             │                          │
                                  ▼                          │
                            未来状态 z_{t+h}                  │
                                  │                          │
                                  ▼                          │
                            O：状态读出                       │
                                  │                          │
                                  ▼                          ▼
                       状态贡献 r_h ───────────────→ b_h + r_h
                                                         │
                                                         ▼
                                                未来NDVI预测
```

干预接口：

- Q2主检验：在`r_h`进入加法节点前设置`s=0`。
- Q2支持检验：令`T→I`，让状态不经学习到的转移。
- Q3：只将进入`T`的未来天气替换为`actual / matched donor / normalized mean`。

训练区：

```text
预测 + 真实未来目标      → 预测监督
预测 + 冻结teacher预测   → 蒸馏监督
z_{t+20} + z*_{t+20}    → 未来状态对齐

观测EO直到t+20（未来天气置零）→ 冻结q/P → z*_{t+20}
```

推理时不使用teacher、未来EO或目标编码器。

## 施工时最重要的三条

1. Figure 1的Q2/Q3预测图以及Figure 2的`b_h/r_h/最终预测`必须是真实模型输出。
2. 未来天气只进入`T`，不能连到`q`、`b_h`、`O`或加法节点。
3. 抽象状态张量可以示意，但必须明确写成`predictive state`，不能伪装成物理地图。
