# TerraState 最终训练与权重链

本文档把散落在 runbook、checkpoint、selection record 和正文中的信息整理为
一条可复盘的实现链。它描述真实训练实现，不把早期 ObsWorld/Plan A 叙事混入
最终 TerraState 方法。

## 1. 权重链

```text
Phase-I B4 checkpoint_best.pt
  └─ 提供冻结的 full-weather q.*，作为唯一 KD teacher

exclusive MAIN checkpoint_last.pt
  └─ 初始化 TerraState-V2 student
     ├─ 初始化时复制 q + state projector
     └─ 冻结复制体生成 future-state target cache

TerraState-V2 单次三阶段训练
  ├─ Stage 1: 0–20%，q 冻结，future-state 权重线性升至 0.02
  ├─ Stage 2: 20–80%，q 冻结，future-state 权重保持 0.02
  └─ Stage 3: 80–100%，仅解冻 q 的最后一个 transformer block，
               future-state 权重降至 0.01
```

统一目标为：

`L = L_GT + 0.5 L_KD + lambda_s L_future_state`

其中 KD 只使用一次；future-state target 来自初始化时冻结的 q/projector，
而不是随 student 同步漂移的目标网络。

## 2. 推理链

```text
cloud-masked history
  -> history encoder q
  -> context-only predictive state z_t

z_t + future weather + geography + elapsed horizon
  -> shared transition T
  -> evolved state z_(t+h)
  -> state readout O
  -> state contribution r_h

context-only forecast b_h + r_h
  -> final land-surface forecast
```

未来天气不能进入 context-only prior；它只能通过共享转移进入状态贡献。这一
结构隔离使 Q2 状态移除和 Q3 天气替换具有可解释的干预接口。

## 3. 训练输入与 cache

future-state cache 不是数据集副本，也不是权重迁移。它按训练/验证 minicube
保存冻结 target encoder 产生的未来状态目标及 provenance，以避免训练时重复
运行 target encoder。sidecar 应记录：

- 数据 manifest SHA；
- q/projector 初始化 SHA；
- horizon；
- mask/coverage；
- NaN、零方差维度、effective rank 等 sanity 统计。

## 4. 历史可复验 checkpoint

当前归档已恢复：

- `checkpoint_boundary80.pt`
- step 11,904，stage 2；
- file SHA-256
  `644deaac0b1578cd153eaffb65bddd6c5ac55d30e0bc09b595111588471e1acd`；
- weight SHA-256
  `aba100c138119bc0fc4412082412596dcf31090410643aa0736b5705b04feaa7`；
- teacher SHA-256
  `bbe2c3ee6de540ae6eabeb7798f331388112ad370dbcae9533187344f2f8a302`；
- student-init SHA-256
  `488052d97c7d1c8a2e805d9838f344daef7ad02e5f185d3025031a5f1c026338`；
- q/projector-init SHA-256
  `da978b0243c8dae070d8a9a3db8e09b889ba9e4c91b36724370c5d747593243d`。

本地验证结果：使用 commit `52578ca` 的 `TerraStateV2` 构造模型，加载
`b4_state_dict` 后 missing=[]、unexpected=[]。

## 5. 当前论文口径与机器证据边界

正式正文采用作者确认的 40 epochs / 14,880 updates，并把 Q1–Q3 描述为来自
完成完整训练协议的同一个最终模型。历史候选记录也确实包含 step 14,880 的
`fsval_best`/`last`，二者具有相同 weight SHA：

`aa98fbd2fa302727bc3375dff17e1c414c652c19d0919c4fbcdcd05a0a5d28aa`

但当前归档没有这两个 14,880-step 二进制，也没有与它们重新绑定的完整 Q1–Q3
原始输出。现有公开 release 的 Q1–Q3 机器证据绑定 boundary80。因此必须同时
保留两层事实：

1. **当前论文/作者口径**：40 epochs / 14,880 updates；
2. **当前可独立机器复验层**：boundary80 / 11,904 updates。

不得将第二层的权重或 provenance 静默改写成第一层。未来若恢复 14,880-step
权重，首要工作是核验 weight SHA、重跑冻结 Q1–Q3，并生成新的结果台账。
