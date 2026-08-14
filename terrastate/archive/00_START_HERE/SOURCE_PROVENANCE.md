# 来源映射

归档根源均位于 `/mnt/data/users/luzheng/workspace/iclr/czj/`：

| 归档内容 | 原始来源 |
|---|---|
| `01_MANUSCRIPT/paper/` | `TerraState_AAAI27/paper/` |
| `01_MANUSCRIPT/mirrors/` | `TerraState_AAAI27/MANUSCRIPT*.md` 与摘要修订记录 |
| `02_EDITABLE_FIGURES/figure1/` | `TerraState_AAAI27/示例/fig1.pptx` 与正式 Figure 1 PNG |
| `02_EDITABLE_FIGURES/figure2/` | `TerraState_AAAI27/示例/fig2.pptx` 与正式 Figure 2 PNG |
| `02_EDITABLE_FIGURES/figure3/` | `figure_workspace/source/`、`figure_workspace/export/`、`paper/figures/data/` |
| `03_CODE_RELEASE/` | `aaai27_code_package/staging/TerraState_CodeData/` 与发布 zip/QA |
| `04_RESULTS_EVIDENCE/current/` | `evidence_workspace/` 与代码发布包的 reported metrics |
| `04_RESULTS_EVIDENCE/historical_release_provenance/` | `evidence_workspace/raw/release/` |
| `05_SUPPLEMENT/` | `aaai27_supplement/` 中的正式文档，不含工具链与构建中间物 |
| `06_FINAL_AUDITS/` | `TerraState_AAAI27/` 根目录下各节 final audit |
| `07_NARRATIVE_HISTORY/` | `WorldModel2026/思路整理进展/` 的四份主线文档 |
| `08_SUBMISSION/` | AAAI 投稿指南和 submission readiness audit |
| `09_CANONICAL_IMPLEMENTATION_SNAPSHOT/` | `WorldModel2026-planb-v2train` 与 `WorldModel2026-planb` 指定 git commit 的真实训练/评估最小闭包 |
| `07_WEIGHTS_AND_PROVENANCE/` | GitHub release `terrastate-v2-boundary80-evidence-v1` 中已验真的历史权重与身份记录 |

Figure 1 和 Figure 2 的正式 PNG 与 `示例/fig1.png`、`示例/fig2.png` 分别具有相同 SHA-256；对应 PPTX 是作者可编辑源。

逐文件来源、对应 commit/版本、SHA、证据层和保留理由见归档根目录
`SOURCE_MAP.tsv`。其中由归档过程新生成的导航、审计和索引会明确标为
`GENERATED`，不会伪装成原工程文件。
