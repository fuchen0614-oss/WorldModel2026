# 一键重绘

在本图目录执行：

```bash
/data/zs/WorldModel2026/.venv-worldmodel/bin/python code/render_final.py
```

脚本只读取本图 `data/` 中已保存的 P42 数组和官方基线预测，不训练模型。若需重新执行官方基线预测，再运行 `run_official_greenearthnet_p42.py`；该步骤需要原始数据、官方配置和 checkpoint，详见 `data/baseline_predictions/P42_provenance.json`。
