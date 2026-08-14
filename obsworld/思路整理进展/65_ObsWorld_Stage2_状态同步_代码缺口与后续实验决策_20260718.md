# 65 ObsWorld Stage2：状态同步、代码缺口与后续实验决策

日期：2026-07-18
性质：以当前 Git 提交和已提交的 Direct-P4 完整开发集结果为准的状态快照。它不宣称远程 Rollout 作业的实时状态；该状态只能由对应训练服务器上的进程与日志确认。

## 0. 一页结论

当前不是“马上训练 U”。正确主线是：

Direct-P4（已训练并完成完整 val_dev 选择）
+ Rollout-P4（当前独立训练候选；需完成并选择 checkpoint）
→ 同协议官方评分与同协议基线闭环
→ Direct vs Rollout 的主结果、时距曲线与统计
→ Rollout 通过结构门后，才做 U 的冻结主干机制实验

因此，下一项主实验不是 U，而是把 Rollout-P4 与 Direct-P4 的 no-U 主线评估闭环。U 是条件性的“新观测到达后的状态更新”主张；它不能替代或掩盖共享 rollout 本身是否有效。

## 1. 文档关系

- 52 与 58 是中心叙事/论文冻结设计，保持“结果未填”的约束。
- 59、60、62 是此前的审计和实现记录，应按当时日期理解。
- 63 是 U 与评估的详细指南；其中 exporter 未修复的旧描述已由本文件和顶部同步说明覆盖。
- 本文件是当前“已修复什么、还缺什么、下一步先跑什么”的唯一状态摘要。

## 2. 已完成并可复用的工程事实

| 项目 | 当前状态 | 证据与边界 |
|---|---|---|
| Direct physical4 分发与训练合同 | 已修复 | ccebe98 使 direct_path_physical4 进入 Direct 分支。 |
| Rollout-P4 200 epoch 配方 | 已实现 | rollout physical4 H200 配置固定 8,800 step、2→4→8→12→20 curriculum；它只是待检验的起始配方。 |
| 完整 val_dev checkpoint selector | 已实现且真实跑通 | selector 仅比较预先定义的有限候选，不把训练 512-sample monitor 当论文选择。 |
| Stage2 evaluator/legacy NPZ exporter 输入一致性 | 已修复 | 评估入口复用 prepare_stage2_batch_for_model，deferred 128→256 context resize 与训练对齐。 |
| GreenEarthNet NetCDF exporter 工程合同 | 已修复 | d2fd5af 加入 physical4 conditioning-stats、checkpoint contract 校验、显式 split、原子写入、输出目录保护与 prediction manifest/hash。 |
| legacy EarthNetScore 编排 | 已实现 | run_stage2_official_score.sh 强制真实 TARGET_DIR，不猜测原始 NetCDF 到官方 target 的映射。 |
| U 基础模型、训练和评估接线 | 已实现 | correction factory/wrapper、predict→reveal-update→next transition、u/no_update/restart/vanilla_filter、基础 schedule/evaluator 均存在。 |

这些是工程能力已具备，不是论文结果已经成立。已记录的静态检查包括 syntax/compile、YAML 合并/contract 检查与 git diff --check；完整 PyTorch/真实官方 scorer 的远程回归仍应保留为待记录的运行证据。

## 3. Direct-P4 已得到的开发集结果

结果目录：

evaluations/eval_direct_p4_valdev_b16_20260718_213729/

选择协议：完整冻结 val_dev（969 samples），预先列出的 checkpoint_best、epoch100、epoch150、epoch200，以 MAE 最小选择。

| 候选 | MAE ↓ | NDVI-MAE ↓ | long-horizon MAE ↓ | skill vs Persistence ↑ |
|---|---:|---:|---:|---:|
| checkpoint_best.pt | **0.0331381** | 0.1087442 | **0.0367183** | **0.1922196** |
| epoch100 / step4400 | 0.0344239 | 0.1169737 | 0.0377538 | 0.1608763 |
| epoch150 / step6600 | 0.0334920 | 0.1097534 | 0.0370541 | 0.1835926 |
| epoch200 / step8800 | 0.0331626 | **0.1085097** | 0.0368423 | 0.1916223 |

冻结选择：checkpoint_best.pt，SHA256 为 1158ffe6644e6a05345cba3fa56ee73af8d1390a2eb078b4b0bc3a94746f91d2。

边界必须明确：

- 这是内部 val_dev 的 MAE 选择结果，不是 58 中 Table 1 的 IID/OOD R²、RMSE、Outperformance 或 ENS。
- official_ens_scored=false，故不能填官方 ENS。
- skill_vs_persistence=0.1922 是内部 RGBN-MAE 相对 persistence 的 19.22% 改善，不是论文 Table 1 的 Outperf。
- epoch200 的 NDVI-MAE 略好，不改变预先冻结的 MAE 选择规则。

## 4. 尚未闭环的缺口

| 编号 | 缺口 | 类型 | 是否需要重训 | 阻塞内容 |
|---|---|---|---:|---|
| E0 | 真实 NetCDF/manifest 与 GreenEarthNet 官方 target、mask、时间轴、官方 evaluator 的数值 parity | 数据/协议实证 | 否 | Table 1 的可直接比较 R²/RMSE/NSE/bias/ENS |
| E1 | Persistence、Climatology 的同协议预测/评分与 Outperformance 所需 per-pixel 对照 | 评估基线代码与运行 | 否 | Table 1 基线与 Outperformance |
| E2 | 逐 5 日 R²/RMSE、逐样本结果、tile-cluster paired bootstrap 95% CI、结果 bundle | 评分/汇总代码 | 否 | Figure 2 与 Direct–Rollout 显著性 |
| R0 | Rollout-P4 完成、训练曲线检查、完整 val_dev selection | 训练与评估 | 正在/需完成 | 共享转移核心主张 |
| R1 | Direct 与 Rollout 在相同官方 split/mask/scorer 下导出与评分 | 评估运行 | 否 | Table 1 的关键成对行 |
| U-P0 | 从 selected Rollout 安全初始化 correction；冻结 I/F/O，只训练 U | 训练代码 | 后续需要 U-only 训练 | U 的归因有效性 |
| U-P1 | 固定 day25/day50 reveal、每样本配对 gain/Gain-AUC、no-reveal 严格等价、observation/evaluation mask 分离、完整 provenance | evaluator/协议 | 后续需要 U 推理 | U 表格可信性 |
| U-P2 | 容量匹配且独立训练的 VanillaFilter | 新训练 | 是 | U 是否优于普通在线滤波器 |

特别说明：d2fd5af 修好了 NetCDF 导出工程合同，但没有凭空产生官方 target 目录，也没有证明真实 cube 与官方 eval.py 数值一致。因此 E0 是实验门，不是尚未修的代码 bug。

## 5. 论文主张和实验归属

| 主张 | 最小证据 | 论文位置 | 当前状态 |
|---|---|---|---|
| C1：共享五日状态转移有长期预测价值 | 同预算 Direct-P4 vs Rollout-P4、同协议 IID/OOD、长时距曲线与 paired CI | Table 1 + Figure 2 | Direct 就绪；Rollout/正式评分未完成 |
| C2：模型真实使用 physical4 外驱动 | true D、no D、shuffled D、time-shifted D 的固定 checkpoint 诊断 | no-U Table 2 | C1 后进行 |
| C3：Stage1.5 初始化有预测价值 | 同预算 Stage1 vs Stage1.5 Rollout 对照 | Table 3 | 尚未训练 Stage1-init Rollout |
| C4：新观测可校正后续预测状态 | U vs No-update/Restart/VanillaFilter，day25/day50、Gain-AUC、no-reveal parity | U 表与 U 图 | 基础代码有；正式合同与训练未完成 |

C1 是当前文章的主张；C4/U 只在 C1 已站住且自身机制门通过后，才升级为正文贡献。若 Rollout 劣于 Direct，应先诊断 transition、curriculum 或 loss，而不是直接训练 U。

## 6. 正确的后续顺序

### M1：完成并冻结 Rollout-P4

1. 在训练服务器确认实际作业状态、step、GPU 与 train_200epoch.log。
2. 完成后检查 2→4→8→12→20 curriculum 切换后的 loss、NDVI loss、长时距 monitor。
3. 在完整 val_dev 上用与 Direct 相同的 selector 固定 Rollout checkpoint。

决策门：若它明显崩溃或长时距劣于 Direct，暂停 U，优先修 rollout；若至少稳定且长期行为合理，进入 M2。

### M2：不增加模型训练的正式评分闭环

1. 用真实 cube 做 GreenEarthNet target/scorer parity smoke。
2. 为 Direct(best) 与冻结 Rollout 各导出一次带 hash 的完整预测。
3. 生成/评分 Persistence 与 Climatology。
4. 汇总 IID/OOD R²、RMSE、NSE、bias、Outperformance；ENS parity 不成立则从 Table 1 删除 ENS 列。
5. 保存逐样本误差，补 Figure 2 与 tile-cluster paired CI。

M2 是推理与评分，不是重新训练；它首次让 58 的 Table 1 和 Figure 2 有资格填真实数字。

### M3：no-U 驱动诊断与结构消融

在 C1 的 checkpoint 和评分协议冻结后，再做 true D、no D、shuffled D、time-shifted D 的 checkpoint inference 诊断；随后才决定 Stage1-init Rollout（Table 3 B）和 3-seed 重复。

### M4：U 的单 seed 机制门

只在 M1/M2 通过后实施：

1. 补 U-P0/P1 代码和端到端测试。
2. 从 frozen selected Rollout 初始化，冻结 I/F/O，仅训练 U。
3. 同条件独立训练容量匹配 VanillaFilter。
4. 在 val_dev 固定 day25/day50 比较 No-update、Restart、VanillaFilter 与 U。
5. 只有 U 在配对 Gain-AUC/后续 RMSE 上可靠胜出且 no-reveal 不退化，才做 U 的三 seed 或 IID/OOD 扩展。

## 7. 现在不建议启动的训练

- 不要在 Rollout 结果未知时启动 U 大训练。
- 不要为了“有更多实验”先跑 full24 或 Partition；它们是条件性附录，不阻塞 C1。
- 不要在官方 scorer/target 未验证时启动三 seed 扩张。
- 不要把当前 Direct val_dev MAE 当作论文主表、ENS 或外部方法严格比较数值。

## 8. 最短、可发表的路线

现在：Rollout-P4 完成
→ 完整 val_dev 选择 Rollout checkpoint
→ Direct(best) + Rollout(selected) + Persistence + Climatology 在同一真实 scorer 上完成 IID/OOD
→ Table 1 + Figure 2 + paired CI
→ 若 Rollout 通过：U-P0/P1 → 单 seed U 机制门
→ 最后才决定：U 扩展、Stage1 vs Stage1.5、3 seed、full24/Partition

这一路线先回答文章最重要的问题——共享递推状态是否有长期预测价值；U 随后回答更强但更难证明的问题——中途新观测能否安全改善之后的预测。

## 9. 同步边界

本文件只同步文档事实，不改变模型、checkpoint、正在运行的训练或远程缓存。当前工作树另有用户自己的未提交同步脚本、权重传输脚本与文档；本文件不把它们混入 Stage2 代码修复提交。要同步到训练服务器时，应单独提交本文件和对 63 的状态注记，再由服务器执行 git pull --ff-only origin main。
