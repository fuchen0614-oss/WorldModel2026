# D fixed40 ablation B: verified

| Split | C1 RMSE | Base RMSE | C1 R2 | Base R2 |
|---|---:|---:|---:|---:|
| iid_chopped | 0.149113789 | 0.149090499 | 0.530112884 | 0.528090929 |
| ood-t_chopped | 0.145668536 | 0.145482600 | 0.578612694 | 0.575506358 |
| ood-s_chopped | 0.156579286 | 0.156826645 | 0.496895836 | 0.494427677 |
| ood-st_chopped | 0.150780365 | 0.150481045 | 0.546020917 | 0.544087477 |

Seed42, epoch40/step29800; shared coverage verified. IID/OOD-T new worker exit0; OOD-S/ST reuse with exact coverage/aggregation verification. No baseline reevaluation.
