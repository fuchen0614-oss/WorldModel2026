# Review Summary

**Problem**: 稀疏、云遮 EO 中的长期 predictive state、开放循环推进与再观测校正。  
**Initial approach**: Stage1.5 state/observation 分解 + shared five-day latent rollout + weather response + 多套主/下游实验。  
**Date**: 2026-07-15  
**Rounds**: 5 / 5  
**Final score**: 9.2 / 10  
**Final verdict**: READY

## Problem Anchor

- **Bottom-line problem**: 在稀疏、受云和 acquisition 条件影响的 Earth observations 中，学习一个能支持可靠长期预测的状态表示及其动力学，而不是只把未来卫星图像当作一个独立视频 cuboid 回归目标。
- **Must-solve bottleneck**: 当前框架和主流方法没有证明 latent 中哪些变化属于地表过程、哪些属于观测形成，也没有证明同一个短步状态转移能够组合到长期、解释中间观测并在新观测到来时被修正。
- **Non-goals**: 不恢复不可识别的绝对真实物理状态；不声称首个 EO world model、因果反事实、完整地球模拟、业务天气预报或通用 EO foundation model；当前不实现大规模概率生成。
- **Constraints**: 现有 Stage1/1.5 ViT 与 EarthNet/GreenEarthNet 代码可复用；当前本地只有 Stage1 EuroSAT probe，无 Stage1.5/Stage2 结果；主目标是 AAAI 级、7 页内可闭环的工作；本轮不改代码。
- **Success condition**: 在 GreenEarthNet 官方 OOD 协议上，shared-step latent model 与强 direct control 至少统计持平，并在中间状态组合、观测条件稳健或再观测校正中给出 direct/pixel-autoregressive 模型不具备的稳定收益；天气控制证明收益不是纯 calendar shortcut。

## Round-by-Round Resolution Log

| Round | Main Reviewer Concerns | Simplification / Method Fix | Solved? | Remaining Risk |
|---|---|---|---|---|
| 1 | belief 被错误对齐到单帧 encoder latent；U 是 stretch；贡献过多 | prior/posterior 分离；U 升为核心；删除 semigroup/FM/downstream并列线 | yes | generic filtering novelty |
| 2 | 缺 Vanilla/PredRNN-online；随机 decoder 被写成冻结；mask contract不具体 | 强 online controls；共同训练 H；连续 q 与 all-cube protocol | yes | innovation 仍是自由 Q |
| 3 | Q 不具 observation semantics；q² attenuation；截断官方指标；多 reveal | shared masked re-encoding residual；删 Q/mask token；single reveal；自定义 paired metrics | yes | future mask leakage/statistics |
| 4 | availability 与 supervision mask 混用风险；primary estimand未锁 | 显式 a/m_obs/m_sup；mask invariance；gain-AUC/Holm/tile bootstrap；NI gate | yes | actual effect size |
| 5 | final audit | 不再改方法；确认设计闭环 | READY | engineering/results only |

## Overall Evolution

- 从“state factorization + recurrence + weather + downstream”的多线系统，收缩成一个 observation-aligned residual correction。
- 从 whole-belief latent target 改为 history belief 与 single-observation evidence分离。
- 从自由 `Q` subtraction 改为同 mask、同 encoder 下 real-vs-predicted observation residual。
- 从弱 no-update/hard-replace 对照改为 information/compute-matched VanillaFilter 与 PredRNN-online。
- 从多指标选择空间改为一个预注册 paired gain-AUC、Holm 与 geographic-tile bootstrap。
- 大模型、无关下游、第二 benchmark、概率生成均被明确推迟。

## Final Status

- Anchor status: preserved
- Focus status: tight; one dominant claim
- Modernity status: appropriately frontier-aware without forced LLM/diffusion/FM
- Strongest part: residual semantics、exact no-evidence identity、future-only correction supervision与强 falsifier chain
- Remaining weakness: contribution is deliberately narrow；AAAI viability depends on actual advantages over Vanilla/PredRNN-online and official open-loop non-inferiority

## Post-READY World-Model Framing Revision

The correction-only presentation was subsequently audited because it had suppressed the intended “world model + remote sensing” identity too aggressively. After two framing rounds, the proposal is frozen at **9.3/10, READY** with the following hierarchy:

- **system identity**: observation-correctable EO world model；
- **method novelty**: visibility-safe observation-aligned residual correction；
- **world-model evidence**: open-loop Earth-observation rollout, partial-observation belief correction, and forcing/mask/identity contract checks；
- **simulation boundary**: EO-observable Earth-surface evolution under supplied forcing, not complete physical or causal Earth simulation。

This revision does not add a new method or a parallel contribution; it corrects the problem framing and experimental organization.
