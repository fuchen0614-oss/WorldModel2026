# 图3｜标准空间预测

用途：以 P42 展示 Ground truth、Persistence、TerraState C1 与四个官方基线的空间预测和逐像素绝对误差。

怎么读：A 的共享色带是 NDVI 0–1；B 的共享色带是绝对误差 0–0.4，暗低亮高；灰色仅为无效像素。正式图只在 `selected/`，60 个案例浏览库在 `candidates/`。

数据来源：P42 保存数组、官方 checkpoint 推理结果与来源记录均在 `data/`。

重绘：见 `code/README.md`。
