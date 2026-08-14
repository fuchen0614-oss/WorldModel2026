# WorldModel 环境复现说明

当前环境按原机器 `conda list` 重建：Conda 基座版本由
`environment.worldmodel.yml` 固定，PyPI 用户态依赖由
`requirements.worldmodel.lock.txt` 逐项锁定。

环境前缀：

```text
.conda/envs/WorldModel
```

激活方式（在项目根目录执行）：

```bash
source scripts/activate_worldmodel.sh
```

从零重建：

```bash
CONDA=/root/nas/users/luzheng/workspace/enter/bin/conda
ENV="$PWD/.conda/envs/WorldModel"
"$CONDA" env create --prefix "$ENV" --file environment.worldmodel.yml
"$CONDA" run --prefix "$ENV" python -m pip install -r requirements.worldmodel.lock.txt
```

GitHub CLI 也安装在此环境中：

```bash
source scripts/activate_worldmodel.sh
gh --version
gh auth status
```

`GH_CONFIG_DIR` 会自动指向 `.conda/envs/WorldModel/.gh`，因此 GitHub CLI
的登录配置与令牌保存在项目虚拟环境内部，并由仓库根目录的 `.gitignore`
排除，不会提交到 Git。环境首次创建后如未登录，执行 `gh auth login` 即可。

说明：原环境前缀 `/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel`
在当前节点不可见，所以无法执行二进制前缀克隆。当前方案精确固定 Python 与
Python/CUDA 用户态包；glibc、驱动和少量 Conda 系统库由当前节点按平台解析。

已知的平台级解析差异（不属于 Python/CUDA 用户态依赖）：当前节点得到
`ca-certificates 2026.5.14`、`openssl 3.5.7`、`tzdata 2026c`，源列表分别为
`2026.6.17`、`3.6.3`、`2026b`。源 Conda 前缀不可见时，强行复制这些证书/时区/
动态库 build 的收益很低且可能降低当前节点兼容性；Python、PyTorch、CUDA 与全部
项目依赖仍按源列表精确锁定，并已通过运行验证。

## 2026-07-15 验证结果

```text
Python       3.11.15
PyTorch      2.12.0+cu130
torchvision  0.27.0+cu130
Triton       3.7.0
NumPy        2.4.6
Xarray       2026.4.0
EarthNet     0.3.9
GitHub CLI   2.96.0
GPU          8 x NVIDIA H200
```

- `pip check`：无 broken requirements；
- CUDA smoke：在 GPU 0 完成 `2048 x 2048` FP16 matmul，结果 finite；
- 正式测试：`pytest -q tests`，`26 passed`；
- 激活脚本验证：`CONDA_PREFIX`、PyTorch 和 CUDA 均正确。

全仓直接运行 `pytest -q` 会额外收集 `scripts/test_dual_dataloader.py`，其中仍硬编码
旧机器 `/csy-mix02/cog8/zjliu17/Agent/TrainData/...`，因此在当前节点会于测试收集阶段
报数据不存在。这是数据路径可移植性问题，不是环境安装失败，当前未按本任务修改训练代码。

正式测试有一条来自 `netCDF4==1.7.4` / `numpy==2.4.6` 的二进制 ABI
`RuntimeWarning`；该版本组合与源环境完全一致，实际 NetCDF 读写测试通过。
