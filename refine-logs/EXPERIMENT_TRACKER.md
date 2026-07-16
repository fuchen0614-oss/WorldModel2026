# Experiment Tracker

> **固定协议（2026-07-16）：**本追踪器只使用服务器现有的 raw
> `EarthNet2021/earthnet2021x`。开发阶段为 `train_dev → val_dev`；锁定后主表为
> `iid/ood`，`extreme/seasonal` 仅作压力测试。GreenEarthNet 与 `*_chopped` 轨道
> 不在本轮训练、选择、导出或评分中出现。
>
> 状态含义：`CODE_READY` 表示实现和合成测试已通过、但尚未在真实冻结数据上完成；
> `TODO` 表示可开始但尚未运行；`PENDING_IMPLEMENTATION` 表示该实验依赖尚未写入代码；
> `DONE` 只能表示真实产物和结果已保存，不能仅表示脚本存在。

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics / Gate | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | freeze protocol | explicit `train_dev/val_dev/train_all/iid/ood/extreme/seasonal` manifests | all | unique path/tile counts; role and overlap checks; no fallback root scan | MUST | CODE_READY | `freeze_earthnet2021x_protocol.py`；真实 artifacts 尚未冻结 |
| R002 | M0 | score/export integrity | EarthNet NPZ export → EarthNetScore → provenance | tiny real subset, then iid/ood | checkpoint contract; SHA-256 manifest; score sidecar; scorer succeeds | MUST | CODE_READY | E-2 已用合成 NetCDF 实跑；不等于正式主表 |
| R003 | M0 | conditioning/preflight | 24-D E-OBS + `cop_dem` train-only stats | train_dev | full stats provenance; v2 contract; no missing/low-coverage driver | MUST | CODE_READY | 必须先在真实数据完成 full preflight |
| R004 | M0 | mask and target audit | input/view, loss mask, official scoring fields | train_dev/val_dev | target/eval fields cannot enter model; coverage/stats report | MUST | TODO | 现有静态测试通过；需要真实样本审计 |
| R005 | M0 | state unit tests | future observation availability/update contract | synthetic | q=0 identity; predict-before-update; partial-support recursion | MUST | PENDING_IMPLEMENTATION | 属于 observation-correction 分支，当前 A–D 尚未实现 |
| R006 | M0 | future-mask leakage | all online/update systems | synthetic | changing unrevealed supervision masks changes no model state/prediction | MUST | PENDING_IMPLEMENTATION | 先有 update model，后做此 test |
| R010 | M1 | tiny overfit | Direct24, Rollout24, Partition24 | 32 then 128 `train_dev` cubes | loss decreases; finite aligned RGBN/NDVI; checkpoint/resume works | MUST | TODO | Stage2-v2 core 已实现 |
| R011 | M1 | factual direct control | matched Direct24 | `val_dev` | ENS export/sanity + masked internal horizon curve | MUST | TODO | 这是当前最先应跑的正式模型对照 |
| R012 | M1 | world rollout pilot | Rollout24 no future observation | `val_dev` | open-loop curve; no factual collapse vs Direct24 | MUST | TODO | 使用相同 D/G/H、初始化、解码器预算 |
| R013 | M1 | compositional pilot | Partition24 | `val_dev` | partition state/pixel/NDVI gap plus factual score | MUST | TODO | 10 天 vs 5+5 天；不是额外 target 输入 |
| R014 | M1 | external baseline calibration | published direct/recurrent system only if exact protocol reproducible | `val_dev` | same raw manifest + EarthNetScore; no copied cross-protocol number | NICE | DEFERRED | Contextformer/PredRNN 不能用 Green `*_chopped` 数字替代 |
| R020 | M2 | generic filter pilot | capacity-matched VanillaFilter seed 42 | `val_dev` | paired post-reveal gain-AUC day25/day50 | MUST | PENDING_IMPLEMENTATION | 仅当 observation-correction 作为最终创新时启动 |
| R021 | M2 | proposed update pilot | aligned residual update seed 42 | `val_dev` | paired gain-AUC + absolute MAE/clear strata | MUST | PENDING_IMPLEMENTATION | 与 R020 同输入、同训练 schedule |
| R022 | M2 | pixel online control | PredRNN-online or matched recurrent assimilation | `val_dev` | post-reveal aggregate/strata | MUST | PENDING_IMPLEMENTATION | 先确认可在同一 raw protocol 复现 |
| R023 | M2 | no-reveal counterfactual | same trained online systems | `val_dev` | correction gain vs own no-reveal | MUST | PENDING_IMPLEMENTATION | inference only |
| R030 | M3 | component simplification | no staleness / binary-q / hard replacement | `val_dev` | delete a component if equivalent | MUST | PENDING_IMPLEMENTATION | 不在 OOD 上做结构选择 |
| R031 | M3 | initialization gate | Stage1 vs final Stage1.5 | `val_dev` | Stage2 prediction and semantic gate both non-worse | NICE | TODO | 等用户的最终 Stage1.5 checkpoint 冻结 |
| R032 | M3 | driver alignment | true/no/shuffled D | `val_dev` | correct-time driver utility; no causal wording | MUST | TODO | 可先在 Direct/Rollout 路径完成 |
| R040 | M4 | final factual systems | final Direct24/Rollout24/Partition24 seeds 42/27/97 | iid and ood | EarthNetScore + components; tile-cluster CI; config locked | MUST | TODO | 仅 M1/M3 gate 通过后启动 |
| R041 | M4 | final correction systems | Vanilla / innovation / online recurrent seeds | iid and ood | day25/day50 paired gain + absolute error | MUST | PENDING_IMPLEMENTATION | 仅 M2 gate 通过后启动 |
| R042 | M5 | stress tracks | locked final models | extreme/seasonal | compact ENS + horizon/failure panels | NICE | TODO | 不重新调参 |
| R043 | M5 | efficiency | final + matched controls | `val_dev` | Params/FLOPs/latency/memory | NICE | TODO | same hardware |

## Current execution order

1. Freeze real manifests and build matching full `train_dev` conditioning stats.
2. Run real-data preflight; fix data/contract errors before using GPUs.
3. Run R010–R013 in order, first on 32 then 128 cubes; do not start full seeds yet.
4. Use `val_dev` only to decide whether the observation-correction branch is worth implementing/running.
5. Run IID/OOD exactly once after the final configuration is locked; leave Extreme/Seasonal for compact stress evidence.
