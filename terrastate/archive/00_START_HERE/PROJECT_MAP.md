# 项目地图

| 目录 | 内容 | 使用场景 |
|---|---|---|
| `01_MANUSCRIPT/` | 可独立编译的最小论文树、英文 PDF、三份 Markdown 镜像 | 阅读、修改、重新编译 |
| `02_EDITABLE_FIGURES/` | Figure 1/2 的作者 PPTX、Figure 3 的 SVG/CSV/生成脚本 | 手工改图与数据核对 |
| `03_CODE_RELEASE/` | AAAI 发布代码、配置、manifest、Q1–Q3 评估入口 | 代码阅读与后续发布 |
| `04_RESULTS_EVIDENCE/current/` | 当前结果台账、表格和报告指标 | 数值与 claim–evidence 核对 |
| `04_RESULTS_EVIDENCE/historical_release_provenance/` | 原始 release 记录和运行日志 | 追溯历史，不直接作为当前训练身份 |
| `05_SUPPLEMENT/` | 补充材料 PDF/TeX、中文镜像与事实冻结表 | 补充材料复盘 |
| `06_FINAL_AUDITS/` | 各节最终审计、格式/引用/一致性审计 | 投稿前质量门禁 |
| `07_NARRATIVE_HISTORY/` | 从母稿、已提交摘要到单模型闭环的叙事演化 | 回看主线如何收敛 |
| `07_WEIGHTS_AND_PROVENANCE/` | 已验真的历史 boundary80 权重及最终权重缺口 | 权重加载、SHA 和身份核对 |
| `08_SUBMISSION/` | 投稿指南和就绪审计 | 上传前人工检查 |
| `09_CANONICAL_IMPLEMENTATION_SNAPSHOT/` | commit-exact 的 V2 训练、Q1–Q3 评估器和冻结协议 | 真实实现复盘与历史权重复验 |

## 推荐复盘顺序

1. 读 `KEY_FACTS_AND_CLAIMS.md`，先建立当前有效结论。
2. 读 `KEY_WEIGHTS_AND_RESULTS_INDEX.md`，确认权重身份与最终数值。
3. 对照 `main.pdf` 与中文全文。
4. 读 `METHOD_CANONICAL_SPEC_AND_AAAI_WRITING_GUIDE_ZH.md` 理解真实信息流。
5. 用 Q1/Q2/Q3 三个 JSON 和 `current/tables/` 核对正文表格。
6. 查看 Figure 可编辑源，逐项核对图文一致性。
7. 最后阅读 `07_NARRATIVE_HISTORY/`，理解哪些早期想法被保留、弱化或放弃。

## 不应从本归档推断的内容

- 归档中的 boundary80 权重可复验历史评估，但不等于作者确认的
  14,880-update 最终权重。
- Q3 的 84 对结果不是完整 OOD-t 精度。
- 状态干预不证明完整物理状态、因果效应或反事实正确性。
- 不支持 Q4/composition、non-collapse、SOTA 或极端天气特异增强。
