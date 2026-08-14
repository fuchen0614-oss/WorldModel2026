# 有意排除的内容

- `WorldModel2026-planb/`、`WorldModel2026-planb-v2train/` 的重复副本；
- Stage 2 及之后的预测模型、DGH、GreenEarthNet 主实验代码与权重；
- `.conda/`、Python cache、下载工具和数据集本体；
- `.bak`、旧 Plan A、过期 decoder-only/encoder-only 入口；
- smoke log、普通训练日志、TensorBoard 和空 checkpoint inventory；
- 没有结论的中间 checkpoint 与过程性图像；
- 大量后期 AAAI 叙事文档，它们已单独整理到 TerraState AAAI-27 精选归档。

保留例外：

- Stage 1.5 非线性泄漏未消除属于关键科学结论，不按普通失败记录删除。
- `.learning/` 学习体系被完整保留，因为它很可能就是用户提到的既有学习 Markdown 体系。

