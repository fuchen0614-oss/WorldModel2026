# ObsWorld Stage2 EarthNet 服务器执行手册

## 1. 当前训练协议

- 监督数据只使用 EarthNet2021。
- 输入为 10 帧历史观测，预测未来 20 帧，对应 `h=5,10,...,100` 天。
- `D` 为年内日期、降水、温度、VPD、太阳辐射的区间统计。
- `G` 为 EarthNet `highresstatic` 中的高程。
- EarthNet 内置气象只有降水、气压、平均/最低/最高温度；VPD 和太阳辐射必须通过外部逐日 sidecar 提供。
- EarthNet 的内置气象取 `80×80` 窗口中与高分辨率影像重合的中心 `2×2` 区域，不对整个窗口求平均。
- 训练中的未来气象属于给定气象情景的 `oracle forcing`，用于检验条件动力学，不应表述成无需天气预报的部署预测。

## 2. 外部 D sidecar 格式

每个 EarthNet cube 对应一个同名 `.npz`：

```text
EarthNet2021_DGH/
  <earthnet_cube_name>.npz
```

支持两种内容：

```python
drivers      # [T, C]，逐日值
driver_names # [C]，名称可为 precipitation/temperature/vpd/solar_radiation
```

或直接使用同长度的一维数组：

```python
precipitation
temperature
vpd
solar_radiation
```

sidecar 第 0 天必须对应 cube 文件名中的首日。ERA5 单位须统一为降水
`mm/day`、温度 `degC`、VPD `kPa`、太阳辐射 `MJ/m2/day`。

## 3. 从 ERA5-Land 构建 sidecar

项目已提供 `scripts/build_earthnet_era5_sidecars.py`。它从温度和露点推导
VPD，并对太阳辐射做逐日聚合。默认保留 EarthNet 自带 E-OBS 降水和温度，
只从 ERA5-Land 补 VPD 与太阳辐射。

标准 `reanalysis-era5-land` 小时文件中的降水、辐射是从当日 00 UTC
开始累计的量，必须使用 `cumulative`，不能把 24 个累计值再次求和：

```bash
python scripts/build_earthnet_era5_sidecars.py \
  --config configs/train/stage2_earthnet_main.yaml \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --era5 '/path/to/era5_land/*.nc' \
  --output-root /path/to/EarthNet2021_DGH \
  --split train \
  --accumulation-mode cumulative \
  --report /path/to/EarthNet2021_DGH/build_report.json
```

如果使用 CDS 新版已去累计的 hourly time-series 产品，则改为：

```bash
--accumulation-mode incremental
```

如需让降水和温度也统一改用 ERA5，再显式增加
`--include-era5-precip-temp`。脚本会检查时间完整性、单位和每日覆盖，任一
cube 缺日值都会以非零状态退出。`train` 构建阶段覆盖原始 train 目录中的
全部 cube，包括之后划入验证集的部分。

## 4. 首次检查

```bash
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
pip install -r requirements.txt

python scripts/inspect_earthnet2021.py \
  --root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --external-driver-root /path/to/EarthNet2021_DGH \
  --try-loader
```

重点检查：

- `x_context=[10,4,256,256]`
- `x_target=[20,4,256,256]`
- `D=[20,9]`、`G=[1,256,256]`、`h=[20]`
- `driver_valid_rate` 中九个特征在正式主实验里均不应长期为 0。

## 5. 合成数据全链路测试

```bash
python scripts/make_synthetic_earthnet.py --output-root /tmp/obsworld_en21_smoke

pytest -q \
  tests/test_earthnet_loader.py \
  tests/test_stage2_components.py \
  tests/test_era5_sidecars.py

python scripts/build_earthnet_dgh_stats.py \
  --config configs/train/stage2_earthnet_smoke.yaml \
  --data-root /tmp/obsworld_en21_smoke \
  --external-driver-root /tmp/obsworld_en21_smoke/drivers \
  --output /tmp/obsworld_en21_smoke/dgh_stats.json \
  --max-files 1
```

再执行 2 个优化步。smoke 配置使用微型随机模型，只验证整条训练管线，不代表
正式模型结果：

```bash
EXTERNAL_DRIVER_ROOT=/tmp/obsworld_en21_smoke/drivers \
DGH_STATS_PATH=/tmp/obsworld_en21_smoke/dgh_stats.json \
DATA_ROOT=/tmp/obsworld_en21_smoke \
CONFIG=configs/train/stage2_earthnet_smoke.yaml \
MAX_STEPS=2 BATCH_SIZE=1 NUM_WORKERS=0 GPUS=1 \
bash run_stage2_earthnet.sh
```

## 6. 正式训练

先用完整训练集生成只基于 train split 的归一化统计：

```bash
python scripts/build_earthnet_dgh_stats.py \
  --config configs/train/stage2_earthnet_main.yaml \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --external-driver-root /path/to/EarthNet2021_DGH \
  --output /path/to/EarthNet2021_DGH/stats_train.json \
  --require-complete
```

正式开跑前对训练 split 做一次全量预检。`--max-files 0` 表示检查完整 split，
并严格验证每个 cube 的 D、G、日期、sidecar、统计文件和 Stage1.5 权重：

```bash
python scripts/preflight_stage2_earthnet.py \
  --config configs/train/stage2_earthnet_main.yaml \
  --data-root /csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
  --external-driver-root /path/to/EarthNet2021_DGH \
  --dgh-stats-path /path/to/EarthNet2021_DGH/stats_train.json \
  --stage15-checkpoint /path/to/checkpoint_step_60000.pt \
  --max-files 0 \
  --check-model \
  --output /path/to/EarthNet2021_DGH/preflight_train.json
```

预检 `ok=true` 后训练：

```bash
EXTERNAL_DRIVER_ROOT=/path/to/EarthNet2021_DGH \
DGH_STATS_PATH=/path/to/EarthNet2021_DGH/stats_train.json \
STAGE15_CHECKPOINT=/path/to/checkpoint_step_60000.pt \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
GPUS=1 BATCH_SIZE=2 NUM_WORKERS=4 PREFLIGHT=1 \
bash run_stage2_earthnet.sh
```

启动脚本默认再快速抽查 64 个 cube。全量预检已经单独完成时，可设置
`PREFLIGHT=0` 跳过重复检查。

训练每 1000 个优化步在固定验证子集上报告总 loss、MAE、NDVI-MAE 和相对
persistence（保持最后清晰观测）的 skill，并以验证 MAE 自动更新
`checkpoint_best.pt`。这个子集只用于稳定监控和选权重；最终表格仍需用
`eval/eval_stage2_earthnet.py` 对完整验证集重新计算。

断点续训不再依赖原 Stage1.5 文件，Stage2 checkpoint 已包含完整模型：

```bash
RESUME_FROM=/path/to/checkpoint_step_10000.pt \
EXTERNAL_DRIVER_ROOT=/path/to/EarthNet2021_DGH \
DGH_STATS_PATH=/path/to/EarthNet2021_DGH/stats_train.json \
DATA_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021 \
GPUS=1 BATCH_SIZE=2 NUM_WORKERS=4 \
bash run_stage2_earthnet.sh
```

首次服务器反馈至少保留：数据检查 JSON、九个 D 特征有效率、模型加载日志、前 20 个 step 的各项 loss、GPU 显存和单步耗时。

## 7. 官方测试轨道导出与评分

导出格式严格为 `pred_dir/<tile>/<cubename>.npz`，其中
`highresdynamic=[128,128,4,20]`：

```bash
python eval/predict_stage2_earthnet.py \
  --config configs/train/stage2_earthnet_main.yaml \
  --checkpoint /path/to/stage2_checkpoint.pt \
  --data-root /path/to/EarthNet2021 \
  --split iid \
  --external-driver-root /path/to/EarthNet2021_DGH \
  --dgh-stats-path /path/to/EarthNet2021_DGH/stats_train.json \
  --output-dir /path/to/predictions/iid
```

有本地 target 时使用官方 EarthNet 工具评分：

```bash
python eval/score_earthnet_prediction_dir.py \
  --prediction-dir /path/to/predictions/iid \
  --target-dir /path/to/iid_test_split \
  --output-dir /path/to/scores/iid
```

当前正式协议和导出器面向固定的 10 帧输入、20 帧输出，即 train/val 与
IID/OOD 标准轨道。Extreme/seasonal 的序列长度不同，不应直接复用本配置。

## 8. Weather-response 诊断

固定历史状态、G 和 h，仅改变 D 的物理量，再比较预测 NDVI 与像素变化：

```bash
python eval/weather_response_stage2.py \
  --config configs/train/stage2_earthnet_main.yaml \
  --checkpoint /path/to/stage2_checkpoint.pt \
  --data-root /path/to/EarthNet2021 \
  --split val \
  --external-driver-root /path/to/EarthNet2021_DGH \
  --dgh-stats-path /path/to/EarthNet2021_DGH/stats_train.json \
  --output /path/to/results/weather_response.json
```

脚本默认扫描降水 `x0.5/x2`、温度 `-5/+5 degC`、VPD
`x0.5/x1.5` 和太阳辐射 `x0.5/x1.5`，并按全部及各 lead time
报告 NDVI 响应和像素响应强度。
