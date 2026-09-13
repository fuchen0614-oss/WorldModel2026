# 图3官方基线权重与推理审计

- 官方发布页：https://zenodo.org/records/10793870（DOI 10.5281/zenodo.10793870）。
- 完整 `model_weights.zip`：2,452,814,122 bytes；MD5 `d9f531a7e6e3e1d497af30760ca6fcf9`，与发布页一致；压缩包完整性测试通过。
- 官方配置仓库：GreenEarthNet commit `a0329636631371a4aaa9a95c75ed0a37d27b8c4f`。
- 官方模型实现：earthnet-models-pytorch v0.1.0 commit `268943b10f78f69a79084ddda3291c35763c3612`。
- 模型：ConvLSTM 1M、PredRNN 1M、SimVP 6M、Contextformer 6M；均使用seed 42官方YAML和checkpoint。
- 四个checkpoint严格加载，`missing=[]`、`unexpected=[]`；输入为P42的10步上下文，输出20步预测。
- Contextformer构造时关闭了无法联网下载的通用PVT初始化；随后完整、严格载入官方Contextformer checkpoint，因此未缺失任何官方训练参数。
- 这是单个主选案例的推理填充，不是重新训练，也不把单例RMSE作为表1总体结论。

逐模型配置/checkpoint SHA256、epoch、global step、预测范围、显存与耗时见 `图3_标准空间预测/data/baseline_predictions/P42_provenance.json`；原始预测见同目录 `P42.npz`。
