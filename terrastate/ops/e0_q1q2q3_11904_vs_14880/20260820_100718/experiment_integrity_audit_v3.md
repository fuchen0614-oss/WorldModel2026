# E0 v3 实验完整性审计报告

**审计日期**：2026-08-20
**审计工具**：independent_audit_v3.py
**审计范围**：A03 v3 文档声明与原始 JSON 的一致性

## 审计结果

- **总检查项**：18
- **通过**：18
- **不符**：0
- **总体状态**：✅ PASS

## 审计发现

所有检查项均通过，A03 文档与原始 JSON 一致。
## 审计方法

1. 独立加载所有 `_v3.json` 工件；
2. 从 JSON 中提取关键数值和元数据；
3. 在 A03 文档中搜索对应字符串（格式化为6位小数）；
4. 记录所有匹配与不匹配项；
5. 交叉验证 provenance、launch_record 和 manifest 的一致性。

## 审计覆盖

- §2.1 三份 checkpoint（SHA/字节/步数/角色/value_sha）
- §3.1 Q1 主表（Val/OOD-t overall + strata）
- §3.2 Q2 load-bearing（full/alpha0/T_identity, delta, CI, verdict）
- §3.3 Q3 extreme state（n_pairs, n_unique_controls, verdicts）
- §4 历史复现（57 formal keys, bit-identical）
- §5.2 artifact inventory（total_files, total_bytes）
- provenance vs launch_record 一致性
- manifest n_tasks 验证

**审计工件**：`experiment_integrity_audit_v3.json` + `experiment_integrity_audit_v3.md`
