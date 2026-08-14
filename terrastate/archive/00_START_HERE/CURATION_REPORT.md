# 精选归档执行报告

- 新建目录：`TerraState_AAAI27_CURATED_20260730/`
- 原项目修改：无
- 文件数：以根目录 `SOURCE_INVENTORY.tsv` 为准
- 权重二进制：已从公开 release 恢复并验真历史 boundary80 checkpoint；
  作者确认的 14,880-update 最终 checkpoint 二进制仍未找到
- 论文 PDF：已复制，9 页，SHA-256 `5578ad0ceaa28bf6398f55443f7b67fd633a193622ac6e5631206f1445ce4242`
- Figure 1/2：正式 PNG 与作者可编辑 PPTX 均已纳入
- Figure 3：正式 PDF、可编辑 SVG、CSV 和生成脚本均已纳入
- 发布代码：已纳入可读目录与原 zip
- 结果：最终正文表格与 Q1/Q2/Q3 当前数值、历史 release provenance 已分层保存
- 真实实现：V2 训练、Q1/Q2/Q3 evaluator 与极端天气协议的 commit-exact
  最小依赖闭包已纳入，83/83 个文件通过 git 字节级核对
- 真实训练闭环 smoke：15/15 通过；包含缓存、信息隔离、阶段冻结、
  三阶段微型训练、断点续训和全局 batch 因子化
- Python 导入与语法检查：通过
- 论文独立重新编译：通过；9 页，0 个 LaTeX error、undefined
  reference/citation、overfull hbox/vbox，字体全部嵌入，提取文本与归档 PDF 一致
- 补充材料独立重新编译：通过；3 页，字体全部嵌入，提取文本一致
- Reproducibility Checklist 独立重新编译：通过；2 页，提取文本一致
- 发布代码 smoke、zip 完整性和匿名化扫描：通过
- SHA-256 全量校验：235 个受检文件全部通过；SOURCE_MAP 覆盖完整且无重复

本归档最大的未闭合项不是文件整理或代码可运行性，而是作者确认的最终
14,880-update checkpoint 二进制，以及能够把它与 Q1–Q3 冻结结果直接绑定的
自包含机器 provenance。历史 boundary80 权重已恢复，但不会被改写成最终权重。
