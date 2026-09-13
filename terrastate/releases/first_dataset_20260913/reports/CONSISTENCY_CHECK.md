# CONSISTENCY_CHECK — 表 / CSV / 图 / 结论 / 来源 的最终一致性

全部为机械核对，**不重新计算任何统计量**。运行入口：`code/verify_consistency.py`。

| 检查 | 结果 | 细节 |
|---|---|---|
| inventory has the editorial columns | PASS | missing=[] |
| every inventory item states a question and a conclusion | PASS | items=19 |
| every inventory item declares an evidence role | PASS | roles=['core', 'core_cost', 'core_foundation', 'core_headline', 'deferred', 'pending', 'registered_only', 'supporting'] |
| every inventory deliverable_path exists on disk | PASS | [] |
| every table .md has a .csv sibling | PASS | md-only=[] csv-only=[] |
| claim matrix declares an evidence_role and a where for every claim | PASS | claims=12 |
| claim matrix uses the agreed role vocabulary | PASS | roles=['core', 'core_foundation', 'core_headline', 'counter_evidence', 'discipline', 'not_tested', 'out_of_scope', 'supporting'] |
| every claim 'where' pointer resolves to a table or figure | PASS | [] |
| T4B primary (receiver-equal) point estimates reproduce the v8 table | PASS | iid/ood_t/ood_s/ood_st full-suffix receiver-equal values present in the table |
| T4B CSV marks receiver-equal as main and the other two as sensitivity | PASS | roles=['geo_equal:sensitivity', 'pixel_pooled:sensitivity', 'receiver_equal:main'] |
| T4B OOD-st endpoint: receiver-equal CI above 0 while geo-equal CI crosses 0 | PASS | receiver_equal=True geo_equal=False |
| T4B states the mandated exception in words | PASS | the table itself names the forbidden over-claim |
| Table 3.3 range is quoted consistently in the table and in the claim matrix | PASS | both the table and the claim carry the same nine-partition ratio range |
| Table 7 reports the phase decomposition and a B-dependent cost model | PASS | each runtime phase is reported separately |
| Table 7 reports no single reuse speedup as the result | PASS | the cost model is presented instead of one ratio |
| Table 5 contains no JSON dump and no truncated content | PASS | every cell is a parsed number |
| Table 5 separates response magnitude from real loss benefit | PASS | 5.2/5.4b are loss-benefit sections; 5.3/5.4a are response-magnitude sections |
| wording discipline: forbidden claims appear only inside their explicit retraction | PASS | [] |
| every figure file is registered somewhere (png/pdf twins matched by stem) | PASS | [] |
| provenance/SHA256SUMS.txt exists and is non-trivial | PASS | entries=80 |
| local sync list documents its exclusions | PASS | 81 files to mirror |
| every local sync entry exists | PASS | [] |
| every deliverable is either hash-listed or explicitly excluded | PASS | hash coverage is asserted by finalize_package.py (step 12) |
| run ledger rows all have the header's field count | PASS | header=9 rows=[9] |
| run ledger survives a naive comma split | PASS | comma counts=[8] |
| every ledger log_or_output path resolves (globs allowed) | PASS | [] |
| run ledger carries no stale status | PASS | statuses=['done'] |
| review entry point names the final directory, the local mirror and the preserved old version | PASS | final dir + local mirror + old version all named |
| review entry point links the presentation plan and the inventory | PASS | both editorial documents are reachable from the single entry point |
| presentation plan exists and carries the main line | PASS | main line stated verbatim in the plan |
| retention record present and all deleted prediction dirs absent | PASS | 4 dirs recorded |

**合计 31 项，FAIL 0 项。**

