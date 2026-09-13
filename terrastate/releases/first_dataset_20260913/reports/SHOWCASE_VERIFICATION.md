# SHOWCASE_VERIFICATION

机械核对，只覆盖本轮新增或改动的内容；**不重算任何统计量**。
运行入口：`code/verify_showcase.py`。

| 检查 | 结果 | 细节 |
|---|---|---|
| 32 prediction candidates frozen | PASS | n=32 |
| candidate ids unique and contiguous | PASS | ids=['P01', 'P02', 'P03']…['P31', 'P32'] |
| 8 candidates per split | PASS | {'iid_chopped': 8, 'ood-t_chopped': 8, 'ood-s_chopped': 8, 'ood-st_chopped': 8} |
| all five categories present | PASS | ['high_change', 'low_validity', 'seasonal_trend', 'turn_point', 'typical'] |
| each candidate names a season and a cube | PASS | no empty season/cube |
| all 32 candidates exported | PASS | ok=32 |
| target timestamps agree with the dataset axis for every candidate | PASS | 32/32 |
| every candidate has an exported array bundle | PASS | [] |
| GT / C1 / Persistence share one shape per candidate | PASS | 4 (key,shape) pairs over 8 sampled candidates |
| validity mask is strictly binary | PASS | values ∈ {0,1} |
| every prediction candidate has browse/detail (png+pdf) and a thumbnail | PASS | [] |
| prediction contact sheets cover all 32 candidates (8 per page) | PASS | 4 page(s) |
| 12 weather candidates frozen | PASS | n=12 |
| weather contact sheets present | PASS | 2 page(s) |
| every weather case has browse/detail figures | PASS | [] |
| weather cases state that donor/mean have no counterfactual truth | PASS | interpretation_limit present on all 12 |
| OVERVIEW quotes Table 1 C1 iid R²_LC exactly | PASS | 0.5221 |
| OVERVIEW quotes T4B iid/full_suffix_1_to_10/receiver_equal = 0.003192 | PASS | 0.003192 |
| OVERVIEW quotes T4B iid/full_suffix_1_to_10/geo_equal = 0.003168 | PASS | 0.003168 |
| OVERVIEW quotes T4B ood_st/endpoint_h10/receiver_equal = 0.001004 | PASS | 0.001004 |
| OVERVIEW quotes T4B ood_st/endpoint_h10/geo_equal = 0.000533 | PASS | 0.000533 |
| OVERVIEW quotes the ood-t bootstrap CI exactly | PASS | [-0.001320, +0.000665] |
| OVERVIEW quotes the model_hash phase cost exactly | PASS | 33.35 |
| every embedded image resolves on disk | PASS | [] |
| every backticked file reference resolves either here or in the frozen package | PASS | [] |
| overview and guide keep the wording discipline | PASS | [] |
| frozen copies are byte-identical to their recorded hashes | PASS | [] |
| every frozen source still exists (nothing was moved or altered) | PASS | [] |

**合计 28 项，FAIL 0 项。**

