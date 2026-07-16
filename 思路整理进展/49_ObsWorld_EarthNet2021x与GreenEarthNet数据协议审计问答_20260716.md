# 49. ObsWorld：EarthNet2021x 与 GreenEarthNet 数据协议审计问答

> 日期：2026-07-16  
> 状态：**当前数据协议仲裁文件。**它修正 43–48 中把“目录/发布名”和“论文评测协议”直接画等号的表述。模型的 DGH、世界模型叙事与 Stage1.5 投入不变；未通过本文件的审计闸门前，不启动长期 Stage2 正式训练，也不在论文中声称某一种官方协议。  
> 代码对应：`scripts/audit_greenearthnet_layout.py`（只读审计，不下载、不改数据、不占 GPU）。

---

## 一句话结论

**现在不需要重新下载，也不需要立刻二选一。**服务器上的
`EarthNet2021/earthnet2021x` 是当前唯一可靠的原始训练数据根；另一个
`GreenEarthNet` 目录含有若干 `*_chopped`（切分后的）轨道。两者很可能属于同一
EarthNet/GreenEarthNet 数据家族，但在字段、样本身份和官方验证轨道被机器审计前，
**不能混用后直接称为“官方 GreenEarthNet”，也不能把 `earthnet2021x` 这个名字自动
写成“原始 EarthNet2021 ENS 协议”。**

后续 Stage2-v2 的数据接口、24-D DGH 路径、Direct24、rollout（递推）和 partition
（时间分割一致性）可以继续开发；它们不依赖最终选择哪一个官方评估器。

## Q1：为什么会有 EarthNet2021、EarthNet2021x 和 GreenEarthNet 三个名字？

**答：它们有关联，但“名字相似”不等于“评测规则相同”。**

- 原始 [EarthNet2021](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf) 使用 `train/iid/ood/extreme/seasonal` 这一组发布划分，常用 EarthNetScore（ENS）评估。
- [GreenEarthNet / Contextformer 官方仓库](https://github.com/vitusbenson/greenearthnet) 明确说明：论文名是 **GreenEarthNet**，开发时也会把同一新版数据/代码称作 `earthnet2021x` 或 `en21x`。它的 CVPR-2024 主协议使用 `train`、`val_chopped`、`ood-t_chopped`，并有 `ood-s_chopped`、`ood-st_chopped` 作为补充轨道。
- 所以 `earthnet2021x` 是一个很有价值的**发布/兼容名称**，但不是足以确定论文该用 ENS 还是 GreenEarthNet CVPR-2024 evaluator（评估器）的证据。

这不是推翻原有路线；恰恰相反，它解释了为什么现有 raw NetCDF 有 8 个 E-OBS 字段、`cop_dem` 等更适合 DGH 的字段，也解释了为什么项目中已经存在 GreenEarthNet 的 NetCDF 导出和评测代码。

## Q2：目前两套服务器目录已经知道什么？

用户已提供的事实如下。

| 位置 | 已观察到的内容 | 可以确认什么 | 还不能确认什么 |
|---|---|---|---|
| `/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021/earthnet2021x` | `train/iid/ood/extreme/seasonal`、`.manifests`，其中 `train` 清单的远端前缀为 `earthnet/earthnet2021x/train/...` | 有完整原始训练根；可立刻用于 Stage2-v2 的训练数据审计与统计量计算 | 这套 raw split 在论文中最终应叫原始 EarthNet2021 协议，还是 GreenEarthNet 的 raw release |
| `/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet` | `iid_chopped`、`ood-t_chopped`、`ood-s_chopped`、`ood-st_chopped`，以及 `iid/ood/extreme` 等目录；用户统计到 31,390 个 `.nc` | 已经有 Green 风格的若干评测轨道，不一定要重新下载 | 截至已给出的目录列表，**未见** `train` 与 `val_chopped`；因此尚不能自动组成完整官方 Green 主协议 |

特别注意：`*_chopped` 的文件数会因为一个原始 minicube（小立方体）被切成多个评测片段而大于原始样本数。它不能与 raw 文件数一一比较，更不能拿来证明“全部下载完成”。

## Q3：现在推荐用哪一套做主实验？

**短期推荐：先固定原始训练根，先不把论文主评测协议写死。**

1. **训练数据根不变**：继续使用
   `/TrainData/EarthNet2021/earthnet2021x/train`。它已有完整训练规模，且当前
   Stage2-v2 loader（加载器）正是为这类 150 天 NetCDF、8 个 E-OBS 字段和 `cop_dem`
   写的；不需要重下。
2. **主评测协议由审计决定**：
   - 若 `GreenEarthNet` 中确有 `val_chopped`，且 train/val/`ood-t_chopped` 的字段、时间和样本身份都能通过审计：主文优先采用 **GreenEarthNet CVPR-2024**，主测试是 `ood-t_chopped`，使用现有的 Green NetCDF evaluator；这是与 Contextformer 等前沿工作最直接可比的方案。
   - 若 `val_chopped` 确实缺失，或 raw/chopped 文件的 schema（字段结构）不兼容：不要硬拼。主文改用 **原始 EarthNet2021 ENS** 的 `iid/ood` 主表，`extreme/seasonal` 为补充；不得把 ENS 分数和 Green 分数放在同一张数字表里比较。
3. **开发阶段仍可推进**：即使 Green 官方验证轨道暂缺，也可以只在 raw `train` 内做确定性 tile holdout（地图格留出）来验证 Direct24/rollout/partition 代码、小样本过拟合和 one-seed（单随机种子）方向。它是开发验证，不能伪称官方 `val_chopped`。

因此并不是“换数据集”。更准确的说法是：**同一 EarthNet 家族的现有数据已足够支持开发；只需用一次小型、只读审计把最终评测协议定准。**

## Q4：服务器上现在应运行什么？

下面命令可与 Stage1.5 训练并行：只扫描目录和少量样本，不使用 GPU，不下载文件，不修改数据集。

```bash
cd /csy-mix02/cog8/zjliu17/Agent/WorldModel2026
git pull --ff-only origin main
source /csy-opt/cog8/zjliu17/miniconda3/bin/activate WorldModel

RAW_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/EarthNet2021/earthnet2021x
EVAL_ROOT=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet
REPORT=reports/greenearthnet_protocol/audit_layout_20260716.json

nice -n 10 python scripts/audit_greenearthnet_layout.py \
  --raw-root "$RAW_ROOT" \
  --eval-root "$EVAL_ROOT" \
  --sample-schema \
  --max-files-per-group 4 \
  --output "$REPORT"

python - <<'PY'
import json
from pathlib import Path
p = Path("reports/greenearthnet_protocol/audit_layout_20260716.json")
r = json.loads(p.read_text())
print(json.dumps(r["readiness"], indent=2, ensure_ascii=False))
PY
```

如果想把它作为“完整 Green 主协议”闸门再严格运行一次，只需追加
`--strict-main`：

```bash
nice -n 10 python scripts/audit_greenearthnet_layout.py \
  --raw-root "$RAW_ROOT" \
  --eval-root "$EVAL_ROOT" \
  --sample-schema \
  --max-files-per-group 4 \
  --strict-main \
  --output "$REPORT"
```

此时返回码 `0` 才表示目录和抽样字段满足 Green 主协议的**最低布局条件**；返回码
`2` 通常只是缺少 `val_chopped`，不是训练坏了，更不是要求立刻下载。报告会写明缺什么。

## Q5：为什么不能把 raw `train` 和 `ood-t_chopped` 直接拼起来？

**答：可以在审计通过后作为“两个数据根组成的同一协议”使用，但不能靠猜。**

需要同时确认四件事：

1. raw `train` 和 chopped track 都有 Stage2 所需的 150 天、RGBN、8 个 E-OBS、`cop_dem` 字段；
2. chopped track 具有 Green evaluator 所需的 `s2_dlmask`、`s2_SCL`、`esawc_lc`、`geom_cls`；
3. 两边的日期/坐标和样本命名没有错位，且不是把相同地点时间泄漏到 train 和 OOD；
4. 正式 manifest（文件清单）能明确记录每个文件来自哪一个根，不能用递归 glob（全目录模糊扫描）偷偷混入其它目录。

本次新增审计脚本先完成第 1–2 项的目录和抽样字段检查。第 3–4 项会在后续 Green manifest/导出评测提交中实现；在那之前，代码不会自动把两根数据合并。

## Q6：这对 DGH、phi 和“模拟真实世界”叙事有什么影响？

**几乎没有负面影响，反而让主张更准确。**

- `D`：仍是 8 个 E-OBS 气象字段的 24-D 五日路径；这是在 raw NetCDF 上构建的，与最终采用 ENS 或 Green evaluator 无冲突。
- `G`：仍固定 `cop_dem`；`C`（日历）和 `Δt`（真实五日步长）仍与 D 分离。
- `phi`：固定 Sentinel-2 主任务不虚构未来太阳角/几何；Stage1.5 仍作为更好状态初始化的候选，而不是被丢弃。
- 世界模型：真正需要证明的是**受驱动的开环状态递推、时间可组合性和可观测未来核验**。这三点由 Direct24、rollout 和 partition 对照来证明，不依赖把数据集改名。

## Q7：接下来代码工作按什么顺序？

1. 完成当前只读数据审计与报告；不等待全量字段扫描才能写模型。
2. 完成 Commit B：同一 24-D 路径条件下的 matched Direct24（公平直接预测对照）。
3. 完成 Commit C：共享五日转移的 20 步开环 rollout（递推）。
4. 完成 Commit D：10 天与 5+5 天的 partition consistency（时间分割一致性）约束。
5. 审计确定最终评测协议后，再把 manifest、导出器、official evaluator（官方评估器）和主表统一到一个不可混用的配置中。
6. 先跑 32–128 个 cube 的小样本过拟合和 one-seed Gate，方向成立才投入多随机种子正式训练。

## 相关来源与文件

- [GreenEarthNet 官方仓库](https://github.com/vitusbenson/greenearthnet)：说明 `GreenEarthNet`、`earthnet2021x`、`en21x` 的命名关系，并给出 `ood-t_chopped` 推理/评测入口。
- [GreenEarthNet CVPR 2024 论文](https://openaccess.thecvf.com/content/CVPR2024/papers/Benson_Multi-modal_Learning_for_Geospatial_Vegetation_Forecasting_CVPR_2024_paper.pdf)：官方数据与植被预测协议背景。
- [EarthNet2021 原论文](https://openaccess.thecvf.com/content/CVPR2021W/EarthVision/papers/Requena-Mesa_EarthNet2021_A_Large-Scale_Dataset_and_Challenge_for_Earth_Surface_Forecasting_CVPRW_2021_paper.pdf)：ENS 和原始 split 的背景。
- `scripts/audit_greenearthnet_layout.py`：这次新增的可执行审计。
- `47_ObsWorld_Stage2正式代码技术指导与实现规范_20260716.md`：后续 Direct24/rollout/partition 具体实现规范。

