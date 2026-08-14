# TerraState 证据会话状态

更新时间：2026-07-28 UTC

## 1. 当前状态

**DONE — FINAL EVIDENCE AUDIT COMPLETE**

Q1--Q3 数字、Table 1--3、Figure 3 活跃 CSV、24 条参考文献、公开 baseline、
caption 风险、匿名性和 reproducibility checklist 底稿均已完成只读审计。
证据本身不再阻塞；仍需正文整合会话插入 Figure 3、填写 checklist 并落实下列
措辞约束。

## 2. 已完成内容

- 冻结并记录 `main.tex`、三份 manuscript mirror、Table 1--3、BibTeX、
  checklist 与 Figure 3 CSV 的当前 SHA-256。
- 将 Q1--Q3 的所有正文/表格显示数字逆向核对到冻结 JSON 字段。
- 明确确认 Q2：
  - paired mean 只搭配 paired bootstrap CI；
  - official \(\Delta R^2\) 只作为 Table 2 的独立 dataset-level 统计量；
  - state removal 是主检验，\(T\to I\) 只是 supporting evidence。
- 明确确认 Q3 符号为 control loss − actual loss；正值表示 actual weather
  endpoint loss 更低。
- 逐行核对活跃 Figure 3 CSV 的 source path、SHA、estimand、CI、n 和方向，
  6/6 行通过。
- 识别并隔离旧 `paper/figures/data/terrastate_behavioral_evidence.csv`：
  它错误混配 Q2 estimand/CI 且写反 Q3 方向，禁止用作正文来源。
- 审计 Figure 1/2/3：Figure 1、2 PASS；Figure 3 图件 PASS，但正文整合 FAIL
  （尚未插入 `main.tex`）。
- 检查现有与计划 caption；权威 caption 未发现 SOTA、因果/counterfactual
  correctness、extreme enhancement、composition/Q4 或将 \(T\to I\) 当核心证据
  的过度暗示。
- 清点当前 24 条引用：missing/duplicate/unused = 0/0/0；完成元数据、版本、
  citation-to-claim、匿名性和公开 baseline 来源审计。
- 建立逐项 reproducibility checklist 回答底稿。

## 3. 新建或修改的文件

- `FINAL_EVIDENCE_AUDIT_20260728.md`（新建）
- `CITATION_AUDIT.md`（更新为当前 24 条引用）
- `STATUS.md`（本文件，更新）
- `audit/final_20260728/true-cite.json`（只读自动引用核验输出）
- `audit/final_20260728/bibcheck/`（只读工具运行记录；外部检查挂起后中止，
  不属于论文源）

未修改 `main.tex`、manuscript mirrors、BibTeX、Figure 1--3、CSV、原始 JSON、
实验结果或代码。

## 4. 尚未解决的问题

1. Figure 3 尚未插入 `main.tex`；当前正文只有注释接口。
2. `paper/ReproducibilityChecklist.tex` 仍为空，且未被正文引用。
3. `MANUSCRIPT_ZH_FULL.md` 仍称 Figure 3 在等待 provenance-complete evidence，
   与当前活跃 CSV 已闭合的状态不符。
4. TerraState 只有一个 selected training run，无法支持跨种子稳定性。
5. TerraState 与公开 GreenEarthNet 方法的 exact manifest/evaluator equivalence
   未建立，不能进行严格排行榜比较。
6. checklist 所需 seed、compute environment、完整配置/代码发布承诺尚不完整，
   其中发布承诺必须由作者决定。
7. LatentTSF 正式页码和 V-JEPA TMLR 页码/DOI unable to verify；不得编造。
8. 4 个 2026 arXiv 工作需在最终投稿前复查 venue 状态。
9. 本轮 Bib-Check 外部检查阶段未完成；这是工具级限制，人工/True Cite/引用清点
   已独立完成。

## 5. 需要总控决定的事项

1. 是否在最终提交版插入已通过核验的
   `figure_workspace/export/fig3_behavior.pdf`。
2. checklist 的 code/data release 项是否作出正式发布承诺。
3. 是否在 Table 1 caption 中补充：公开 learned baselines 为 3-seed means、
   Climatology deterministic、TerraState one-run。
4. 是否补充 seed 42、GPU/CPU/OS/framework 和完整配置说明；若不补，checklist
   必须诚实回答 No/Partial。
5. 是否在投稿前补 6 个可选 DOI；这不是正确性阻塞项。

## 6. 建议的下一步

1. 正文整合会话只使用活跃 Figure 3 CSV 对应的 export，插入 Figure 3 和权威
   caption；绝不使用旧 behavioral CSV/旧图。
2. 保持 official \(\Delta R^2\) 与 paired mean/CI 分列；保持 Q3
   control-minus-actual 正方向。
3. 更新中英文 mirror 的 Figure 3 状态文字，不改变已核实数字。
4. 按最终审计报告第 8 节填写 checklist，并由作者确认发布承诺。
5. 最后做一次编译后只读 gate：图号/表号、caption、引用、匿名性、PDF metadata
   和所有显示数字。
6. 禁止加入 SOTA/严格排名、因果或 counterfactual correctness、
   extreme-specific enhancement、composition/Q4 已验证、或 transition
   纯净必要性等表述。
