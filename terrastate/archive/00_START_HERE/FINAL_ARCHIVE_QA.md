# TerraState 精选归档最终质量门禁

日期：2026-07-31

## 总结

归档结构、论文资产、补充材料、发布代码、当前结果、历史 provenance、
可编辑图源、真实训练/评估实现和已公开历史权重均已建立明确边界。所有操作
仅发生在新建精选目录或临时目录，原工程保持只读。

## 已通过

- 论文从精选源码独立重编译：9 页、letter、无 LaTeX error、无未定义
  引用/交叉引用、无 overfull box，字体全部嵌入；重编译版与归档版提取文本一致。
- 补充材料独立重编译：3 页、letter、字体嵌入、提取文本一致。
- Reproducibility Checklist 独立重编译：2 页、letter、提取文本一致。
- Figure 1/2/3 的正文引用目标均存在；Figure 1/2 的作者 PPTX 与正式 PNG
  已并列保存，Figure 3 的 PDF/SVG/CSV/生成脚本齐全。
- 28 个正文 citation key 均可在 30 条 BibTeX 中解析。
- 三张最终结果表与 `main.tex` 中的字节内容一致；Q1/Q2/Q3 当前 JSON 与发布
  代码结果一致；30 个冻结正文数值全部核对存在。
- 面向发布的代码 smoke 通过，zip 完整性通过，未发现作者身份、旧项目名、
  `.pyc`、`.bak` 或 `.DS_Store`。
- commit-exact 真实实现共 83 个文件通过来源提交 SHA 核对，79 个 Python
  文件通过 AST 解析，核心训练/评估模块导入通过。
- TerraState-V2 独立 CPU 三阶段 smoke 15/15 通过。
- 历史 boundary80 checkpoint 已从公开 release 恢复，release SHA 与本地
  SHA 一致，并严格加载到历史 `TerraStateV2`。

## 科学证据边界

- 当前正文采用作者确认的完整 40 epochs / 14,880 updates 口径。
- 当前可恢复的机器权重是历史 boundary80 / 11,904-update checkpoint；
  它只能用于历史复验，不能被改名为最终权重。
- 最终 14,880-update checkpoint 二进制及其自包含 Q1–Q3 provenance 仍待
  外部恢复；这个缺口不会被归档文档掩盖。
- Q3 是冻结的 84 对 heat-drought weather-intervention 结果，不是完整
  OOD-t 精度；当前证据不支持 Q4/composition、SOTA 或因果反事实主张。

## 交付完整性

根目录的 `SOURCE_MAP.tsv` 提供逐文件来源与证据层，
`SOURCE_INVENTORY.tsv` 提供文件大小，`SHA256SUMS.txt` 提供最终完整性校验。
当前 235 个受检文件全量 SHA 校验通过；SOURCE_MAP 与实际文件集合一一对应、
无重复。任何后续修改都应重新生成后两项并执行
`sha256sum -c SHA256SUMS.txt`。
