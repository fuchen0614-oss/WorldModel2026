# SpanWorld — D方案复现包

状态：代码与结果归档版；权重下载及端到端复现验证尚未闭合。参见发布状态（未随本版归档：`PUBLICATION_STATUS.md`）。原工程保留。

- [代码结构](<docs/CODE_STRUCTURE.md>)
- [复现入口与验收边界](<docs/REPRODUCE.md>)
- [现有成绩总入口 A08](<../思路整理进展/A08_E1主表_同协议重跑结果.md>)
- [结果文件与SHA索引](<manifests/results_files.json>)
- [正式运行代码来源与SHA](<manifests/remote_sources.json>)
- [权重身份与待补文件](<manifests/weights.json>)

主表采用最终选定权重；固定40轮消融必须使用对应epoch40权重。不要用best替代固定轮次。
权重二进制不进入Git历史，后续通过GitHub Releases分发。已有历史Release仅在SHA完全相同后复用。
该包以D为主；A08及复刻证据可能包含历史/B对照，不代表那些模型已纳入D训练入口。
