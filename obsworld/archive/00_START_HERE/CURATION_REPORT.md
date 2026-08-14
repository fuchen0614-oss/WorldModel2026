# 精选归档执行报告

- 新建目录：`ObsWorld_STAGE1_TO_STAGE1_5_CURATED_20260730/`
- 原项目修改：无
- 代码快照：commit `bbdd4dc29b0bacfd7af4a143ee7987d97c0b330d`
- 代码/配置/训练评估文件逐项 git 对照：0 个失败
- 原始缺失依赖：已补入 `tiny_vit_encoder.py`、`ssl4eo_simple.py` 和仅用于
  package import 闭包的 `state_dynamics.py`；三者均与 commit 字节一致
- 核心训练入口真实导入：通过
- Stage 1.5 CPU 单元/集成测试：12/12 通过
- Python 语法检查：通过
- `00`–`07` 原冻结区 Stage 2 文件名扫描：0 个命中；新增 Stage2 仅位于
  `08_STAGE2_CONTINUATION/`
- `.bak`、编译辅助文件、Python cache：0 个
- Stage1/1.5 权重二进制：0；Stage 1 95k、Stage 1.5 30k/60k 仍不在当前工作区
- 精选保留：Stage 1 训练、Stage 1.5 state bridge、配置、评估 probe、30k/60k 关键结果、初始叙事和学习体系
- 有意排除：重复 plan-b 仓库、环境、数据、普通日志、旧 Plan A、Stage 2 及后期 AAAI 主模型
- 长期母叙事入口：已补入用户所指的 39 号 `AAAI` 独立总审查原文；它保留
  “模拟真实世界发生什么”、下游任务边界、完整 RQ 证据链和后续继续规则，
  与源文件逐字节一致

2026-07-31 增补：

- 原冻结区保持不变；新增独立 `08_STAGE2_CONTINUATION/`，不与 Stage1–1.5
  已验证证据混写；
- 纳入 commit `541dd76` 的最新 Plan-A/metric-aligned Stage2 最小闭包：
  70 个文件、60 个 Python 文件；
- 归档内独立测试 32/32 通过，synthetic smoke 13/13 通过；
- 纳入 9 份 Stage2 强相关文档，并明确记录 A′ 历史精度未过门、
  metric-v1 尚无完整训练结果。
- 新增独立 `09_LONG_TERM_VISION/`：恢复方案 A/B 同期的 `AAA00` 72 号母稿
  及 `AAA01` 73 号 3–6 个月旗舰计划，二者均与原文件逐字节一致。
- 新增两份可加载的 Stage2 正式 best 权重：Direct physical4（step 8000）与
  rollout physical4（step 8000）；二者均通过严格 CPU state-dict 加载。
- 新增两者对应的 GreenEarthNet OOD-t chopped 聚合结果、共同 manifest 和
  scorer provenance；有意排除周期 checkpoint、逐季 parquet、预测文件和日志。
- 两份 Stage2 provenance 交叉给出 Stage1.5 60k state-bridge 原权重的预期
  SHA-256，可用于未来找回验真，但不将 Stage2 权重冒充 Stage1.5。

精确逐文件结果见 `CODE_SNAPSHOT_VERIFICATION.tsv`、`IMPORT_VALIDATION.txt`、
`TEST_VALIDATION.txt`、根目录 `SOURCE_MAP.tsv`、`SOURCE_INVENTORY.tsv` 和
`SHA256SUMS.txt`。
