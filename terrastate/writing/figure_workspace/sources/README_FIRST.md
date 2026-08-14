# Figure 1 临时复制包

这是一个可整体复制、使用后可整体删除的临时目录。

## 最先打开

1. `FIGURE_1_VISUAL_ASSET_BLUEPRINT_ZH.md`
   - 最新 Figure 1 中文/双语布局与素材蓝图；
   - 已写明每个区域应该放什么，以及对应素材路径。

2. `ASSET_INDEX_ZH.md`
   - 所有真实素材的含义、用途和限制；
   - 明确哪些是 historical observation、observed future target 和天气控制。

3. `assets/qa/FIG1_REAL_ASSET_CONTACT_SHEET.png`
   - 三个候选样本的整体预览。

4. `assets/copy_ready_primary/`
   - 已按 Figure 1 位置整理的主选素材；
   - 通常直接复制这里的 PNG 即可开始排版。

## 完整内容

```text
TEMP_FIG1_COPY_BUNDLE_20260728/
├── README_FIRST.md
├── FIGURE_1_VISUAL_ASSET_BLUEPRINT_ZH.md
├── ASSET_INDEX_ZH.md
├── BUNDLE_SHA256SUMS.txt
├── reference/
│   └── current_fig1_framework.png
└── assets/
    ├── copy_ready_primary/
    ├── samples/
    ├── data/
    ├── qa/
    ├── source/
    ├── ASSET_INDEX_ZH.md
    └── SHA256SUMS.txt
```

## 重要限制

素材包内的 future EO/NDVI 是数据集中的真实未来 target，不是 TerraState forecast。
当前没有可追溯的模型 forecast、\(b_h\)、\(r_h\) 或真实内部状态张量，不能把 target
改名后冒充模型输出。

删除本临时目录不会影响原始素材包或正式蓝图。
