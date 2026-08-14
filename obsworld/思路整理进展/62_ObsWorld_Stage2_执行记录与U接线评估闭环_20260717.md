# 62 ObsWorld Stage2：执行记录、评估闭环与 U 接线

日期：2026-07-17
性质：本轮代码实现与本地静态/契约检查记录。训练仍在另一台服务器上，本轮没有启动、停止或修改远程训练进程。

## 0. 本轮执行目标

当前主线保持为：

```text
Direct-P4
  → 官方评分闭环 + 完整 val_dev checkpoint 选择
  → Rollout-P4 训练并冻结
  → U（Observation Correction）接线与测试
  → val_dev 单 seed：U vs No-update / Restart / VanillaFilter
  → 通过后才做正式 U 表格
```

本轮只实现能够从现有代码合同安全推出的部分；真实数据 target 目录、正式 baseline checkpoint 和论文统计门仍然保留为未决项，不把代码存在写成实验结果。

## 1. 已完成的代码变更

### 1.1 Direct-P4 / Rollout-P4

- 新增 `configs/train/stage2_earthnet_v2_rollout_physical4_h200_200ep.yaml`。
  - 继承 Direct-P4 的 data/model/loss/checkpoint contract；
  - 明确 `open_loop=true`、`teacher_forcing_future_state=false`；
  - 8×H200、每卡 B64 的 8,800 optimizer steps 对应 200 epochs；
  - 暂定 curriculum：2→4→8→12→20，切换点为 0/1760/3520/5280/7040；
  - 该 schedule 是可复现的起始配方，不是已经证明最优的超参数。

- 修正 `train/train_stage2_earthnet.py` 的模型分发：`direct_path_physical4` 现在和 `direct_path_24d` 一样进入 Direct 分支。此前分发器只按字符串判断 `direct_path_24d`，physical4 Direct 存在进入首个 v2 batch 后走错分支的风险。

### 1.2 完整 val_dev checkpoint 选择

- 新增 `eval/checkpoint_selection.py`：默认发现 `checkpoint_best.pt` 与命名 epoch checkpoint；普通 `checkpoint_step_*.pt` 必须显式 `--include-step-checkpoints`，避免误启动大量完整验证；只接受有限、预先列出的候选并要求选择指标为有限数。
- 新增 `eval/select_stage2_checkpoint.py`：逐候选调用现有严格 `eval/eval_stage2_earthnet.py`，评估完整指定 split 而不是训练期间固定 512 样本 monitor，保存每候选 sidecar 并写出 `selected_checkpoint.json`。

### 1.3 官方 EarthNetScore 编排

- 新增 `scripts/run_stage2_official_score.sh`，串联：

```text
selected checkpoint
  → eval/predict_stage2_earthnet.py（20 帧 NPZ + manifest/hash）
  → eval/score_earthnet_prediction_dir.py（官方 EarthNetScore）
```

- 脚本强制要求 `TARGET_DIR`。没有真实官方 target 目录时会直接拒绝运行，不会猜测 `.nc` 到 target 的映射。
- 因此 E0 的“代码入口”已具备，但 raw NetCDF 与官方 scorer target 的真实 parity 仍未在本仓库完成实证；这一项仍是正式主表门槛。

### 1.4 Observation Correction / U

- 新增 `models/dynamics/obsworld_correction.py`，注册到 `models/dynamics/obsworld_factory.py`，支持 `rollout_t5_24d_correction` 与 `rollout_t5_physical4_correction`。
- 因果顺序固定为：`prior transition → decode current prediction → optional reveal update → next transition`。当前 reveal step 的预测仍使用 prior；posterior 只供后续 step 使用，避免“先看真值再评价当前帧”。
- 支持四个显式策略：
  - `u`：visibility-weighted residual + gate + staleness；
  - `no_update`：保持 prior；
  - `restart`：对可见 token 用观测编码状态做无额外学习容量的替换/混合；
  - `vanilla_filter`：新增容量可控的无 gate additive filter cell。
- 新增 `data.stage2_contract.observation_correction_view` 和三个 correction-only 字段：`observations`、`observation_mask`、`reveal_mask`。这些字段不会进入普通 `model_input_view`，所以 no-U Direct/Rollout 仍然不能看到未来 target 或评估 mask。
- 新增 `train/observation_correction_schedule.py`：50% no-reveal，50% exactly-one reveal；20-step horizon 的 reveal index 为 zero-based 2–15；支持短 rollout 自动退化为 no-reveal；trainer 在 correction mode 下可显式生成 correction-only inputs，并默认监督所有可用 future endpoint。
- 新增 `configs/train/stage2_earthnet_v2_correction_physical4.yaml`：full-20、无 teacher forcing、全部 20 个 future endpoint 监督，策略为 `u`。
- 新增 `configs/train/stage2_earthnet_v2_vanilla_filter_physical4.yaml`：与 U 使用同一 hidden width/数据合同的独立 filter 消融训练配置；No-update 与 Restart 不需要额外训练。
- 新增 `eval/eval_observation_correction.py`：同一 seed、同一 reveal schedule 下比较 U / No-update / Restart。若没有独立训练的 VanillaFilter checkpoint，只输出 `not_evaluated`，不会拿随机初始化模型冒充 baseline。
- 评估脚本现在接受可选 `--vanilla-filter-checkpoint`；只有提供独立训练、容量匹配的 checkpoint 才会真正计算 VanillaFilter，否则仍明确标记 `not_evaluated`。
- 训练期间的 `validate_stage2()` 也已接入同一确定性 reveal schedule：U 模型的 `checkpoint_best.pt` 不再用无 reveal 路径偷偷选出，而是在 `seed + reveal_probability` 固定的 U 验证协议上选择；Direct/普通 Rollout 的验证逻辑保持不变。完整 val 与正式 U 对比仍以 `eval/eval_observation_correction.py` 为准。

## 2. 本地检查结果与限制

已执行并通过：

- `python -m compileall -q models data train eval tests`；
- `bash -n scripts/run_stage2_official_score.sh`；
- `git diff --check`；
- 用 PyYAML 递归检查 Direct-P4、H200 Rollout-P4、U config 的 `_base_` 合并、protocol、driver protocol、8,800 steps 和 rollout mode。
- 额外用无 PyTorch 的纯函数 smoke 检查三份配置的 `curriculum_checkpoint_state`：Direct=20、Rollout 从 2 开始、U 的 `null` curriculum 稳定归一为 full-20 且保存 correction provenance。

当前工作区 Python 没有 PyTorch，也没有 `pytest`，因此本机无法执行依赖 torch 的完整单元测试。已新增/更新的测试文件为：

```text
tests/test_stage2_checkpoint_selection.py
tests/test_observation_correction_schedule.py
tests/test_observation_correction.py
tests/test_obsworld_v2_factory.py
tests/test_stage2_config_inheritance.py
tests/test_stage2_curriculum.py
tests/test_stage2_v2_contract.py
```

WorldModel 环境服务器上应先运行：

```bash
pytest -q \
  tests/test_stage2_checkpoint_selection.py \
  tests/test_observation_correction_schedule.py \
  tests/test_observation_correction.py \
  tests/test_obsworld_v2_factory.py \
  tests/test_stage2_config_inheritance.py \
  tests/test_stage2_curriculum.py \
  tests/test_stage2_v2_contract.py
```

## 3. 仍未完成、不能由本轮代码自动决定的事项

### 3.1 官方 ENS target 目录

现有预测导出和 scorer 都存在，但仓库没有确认：官方 target directory 的真实位置、target 文件命名是否与 manifest 的 `sample_id` 一一对应、NetCDF mask/字段是否与官方 scorer 读取路径一致，以及内存 accumulator 与官方 `EarthNetScore.get_ENS` 的 parity。因此官方分数只有在真实 target 目录确认后才可写入 Table 1/2；不能用内存分数替代闭环。

### 3.2 Rollout schedule 不是已证明最优

H200 配置解决了原 24D schedule 与 8,800 steps 不匹配的问题，但 2/4/8/12/20 仍是工程起始方案。远程训练完成后要检查 full-20 是否获得足够优化步数、切换点是否导致 loss/NDVI 异常、long-horizon MAE 是否优于 Direct-P4，以及 manifest/stats/seed/contract 是否完全相同。

### 3.3 VanillaFilter 与 Restart 的论文语义

当前代码定义了 filter 结构和评估接口，但没有把随机 filter 结果计入论文。正式比较前必须锁定 VanillaFilter 的独立训练、hidden width、参数/FLOPs ±5% 预算，以及 Restart 是 token replacement 还是 entire-state reinitialization。必要时再加入 PredRNN-online 等强在线基线。

### 3.4 Observation mask 的最终语义

本轮严格把 correction-only `observation_mask` 与 target/evaluation mask 分开，但真实 EarthNet 任务是否用 `target_mask` 模拟 clear observation，还是必须使用官方 clear×SCL×veg/dynamic mask，仍需结合官方评分实现确认。不能把当前训练 target mask 直接写成官方 observation protocol。

## 4. 与 52/58/59/60 的关系

- `52`：继续作为中心叙事与 no-U 主线冻结文件；本轮没有把 U 写成已通过的主方法。
- `58`：继续作为中文论文冻结版；本轮代码实现不改变正文“U 通过机制门后才升级”的表述。
- `59`：其中明确的 P0/P1 缺口已转成可执行代码入口，但 E0 target parity、正式 baseline 和论文统计仍保持未决。
- `60`：原本是“本轮先不改附录代码”的需求梳理；用户随后明确要求执行，因此只实现可安全确定的 U 接线、Rollout 配置和评估选择器，未决科研选择仍保留在本文件。

## 5. 远程服务器上的建议执行顺序

本机不启动训练；远程服务器按下列门顺序执行：

```text
1. Direct-P4 200 epoch 结束，检查 epoch200/checkpoint_step_8800 和 provenance
2. 用 eval/select_stage2_checkpoint.py 对 best/epoch100/150/200 跑完整 val_dev
3. 确认官方 target 目录后，用 run_stage2_official_score.sh 做 NPZ + 官方 ENS
4. 用 stage2_earthnet_v2_rollout_physical4_h200_200ep.yaml 训练并冻结 Rollout-P4
5. 完整 val 选择 Rollout checkpoint，确认 long-horizon 指标和 Direct 配对
6. U config 先跑短 smoke，再跑单 seed val_dev U/No-update/Restart
7. VanillaFilter 独立训练且预算锁定后，才填 U 对比表
```

### 5.1 远程执行命令骨架（只在对应训练服务器运行）

完整 val 选择 Direct/Rollout 候选：

```bash
python eval/select_stage2_checkpoint.py \
  --config configs/train/stage2_earthnet_v2_direct_physical4.yaml \
  --checkpoint-dir "$CHECKPOINT_DIR" --split val \
  --data-root "$DATA_ROOT" \
  --conditioning-stats-path "$CONDITIONING_STATS_PATH" \
  --manifest-path "$VAL_MANIFEST" \
  --batch-size 8 --num-workers 4 --metric MAE \
  --output "$LOG_DIR/direct_full_val_selection.json"
```

确认官方 target directory 后闭环评分（`TARGET_DIR` 不可省略）：

```bash
export CONFIG=.../configs/train/stage2_earthnet_v2_direct_physical4.yaml
export CHECKPOINT=.../checkpoints/<selected_checkpoint>.pt
export DATA_ROOT=.../TrainData/EarthNet2021
export SPLIT=iid                         # 按官方 target split 改写
export MANIFEST_PATH=.../artifacts/protocols/<split>.json
export CONDITIONING_STATS_PATH=.../artifacts/protocols/<stats>.json
export PREDICTION_DIR=.../eval/<run>/predictions
export TARGET_DIR=.../<official_earthnet_targets>/<split>
export SCORE_DIR=.../eval/<run>/official_score
bash scripts/run_stage2_official_score.sh
```

U 单 seed 机制门（有独立 VanillaFilter 时再加最后一个参数）：

```bash
python eval/eval_observation_correction.py \
  --config configs/train/stage2_earthnet_v2_correction_physical4.yaml \
  --checkpoint "$U_CHECKPOINT" --data-root "$DATA_ROOT" \
  --manifest-path "$VAL_MANIFEST" \
  --conditioning-stats-path "$CONDITIONING_STATS_PATH" \
  --batch-size 8 --num-workers 4 --seed 42 \
  --output "$LOG_DIR/u_val_seed42.json" \
  [--vanilla-filter-checkpoint "$VANILLA_CHECKPOINT"]
```

方括号参数仅表示可选项，不能原样复制到 shell；没有 VanillaFilter checkpoint 时脚本会明确写出 `not_evaluated`。

## 6. Git 记录边界

最终本地 commit 应包含：本文件 62、用户指定的 52/58/60 文档，以及本轮新增/修改的模型、contract、trainer、eval、config、script、tests。59/57 已有本地 commit，不需重复改写。只做本地 commit，不自动 push；远程训练服务器按 commit 拉取。由于本地缺少 torch/pytest，commit 前保留“compileall/shell/YAML 通过、torch pytest 待远程执行”的事实。

## 7. 当前结论

本轮已经把“有概念但未注册”的 U 推进为可被 factory/trainer/evaluator 调用的安全代码路径，并补齐 Direct physical4 dispatch、H200 Rollout 配置、完整 val checkpoint selector 和可选的独立 VanillaFilter 训练/评估入口。它仍然不是论文结果：真正决定主线是否成立的下一步仍是 Direct/Rollout 的完整 val 选择与官方 ENS target parity；U 必须在 no-U 主线冻结后，经过单 seed 机制门和容量匹配 baseline 才能进入正式表格。
