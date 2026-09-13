# CODE_AND_CONFIG_INDEX — 代码、协议与配置索引

路径均相对 Git 仓库根。哈希为 SHA256 前 16 位，完整值可用 `sha256sum <path>` 复核；不存在或未纳入仓库的条目已标明。

## 模型与训练（产生这些权重）

| 路径 | 存在 | 字节 | sha256(前16) |
|---|---|---:|---|
| `terrastate/models/terrastate_candidate_c.py` | 是 | 34017 | `6a53643245bde4da…` |
| `terrastate/models/terrastate_v2.py` | 是 | 10162 | `25251928a28320e8…` |
| `terrastate/models/plan_b_b4_exclusive.py` | 是 | 13778 | `20e3d9cdf5ceae88…` |
| `terrastate/train/train_terrastate_candidate_c.py` | 是 | 38622 | `47a31064a8a9a087…` |
| `terrastate/train/terrastate_v2_common.py` | 是 | 8323 | `53695c9e5f8c96d4…` |
| `terrastate/data/greenearthnet_contextformer_dataset.py` | 是 | 6979 | `8c0f9961353d31a3…` |

## 评测与协议（产生这些数字）

| 路径 | 存在 | 字节 | sha256(前16) |
|---|---|---:|---|
| `terrastate/eval/eval_b4_exclusive_contract.py` | 是 | 32556 | `d665e80dd3f85e60…` |
| `terrastate/eval/greenearthnet_protocol.py` | 是 | 17661 | `e0cc47ff794c80ad…` |
| `terrastate/eval/eval_greenearthnet_official.py` | 是 | 6358 | `0bf86eaf26f934cb…` |
| `terrastate/eval/extreme_state_audit.py` | 是 | 30690 | `58e02c1558c69b1a…` |
| `terrastate/eval/export_contextformer_predictions.py` | 是 | 5766 | `53cabf50e9e332cc…` |
| `terrastate/eval/export_emp_baseline_predictions.py` | 是 | 6486 | `ccbac80b9171d62b…` |
| `terrastate/collect_e1_table.py` | 是 | 7764 | `6228c2b7cc5eaaac…` |

## 运行时状态接口

| 路径 | 存在 | 字节 | sha256(前16) |
|---|---|---:|---|
| `terrastate/runtime/candidate_c_state.py` | 是 | 3882 | `ef866c7f27215228…` |

## 协议与配置

| 路径 | 存在 | 字节 | sha256(前16) |
|---|---|---:|---|
| `terrastate/artifacts/protocols/candidate_c_v1/candidate_c_design_contract_v1.json` | 是 | 12423 | `d5e80cafe3998b4c…` |
| `terrastate/artifacts/protocols/candidate_c_v1/candidate_c_selection_contract_v1.json` | 是 | 3372 | `9ae8173adf26b03b…` |
| `terrastate/artifacts/protocols/candidate_c_v1/candidate_c_formal_queue_v1.json` | 是 | 1310 | `511907a2ebeccaba…` |
| `terrastate/artifacts/protocols/extreme_audit_oodt_v1/hotdry_manifest.json` | 是 | 27890 | `f8db1ccbb39120c7…` |

## 图件绘制代码（本包内 23 个文件）

| 路径 |
|---|
| `figures/图1_科学问题框架/code/README.md` |
| `figures/图2_方法与监督框架/code/README.md` |
| `figures/图3_标准空间预测/code/README.md` |
| `figures/图3_标准空间预测/code/build_candidates.py` |
| `figures/图3_标准空间预测/code/export_arrays.py` |
| `figures/图3_标准空间预测/code/lib_showcase.py` |
| `figures/图3_标准空间预测/code/make_contact_sheets.py` |
| `figures/图3_标准空间预测/code/make_contact_sheets_5perpage.py` |
| `figures/图3_标准空间预测/code/render_final.py` |
| `figures/图3_标准空间预测/code/render_prediction.py` |
| `figures/图3_标准空间预测/code/run_official_greenearthnet_p42.py` |
| `figures/图3_标准空间预测/code/verify_showcase.py` |
| `figures/图4_第二数据集_延期/code/README.md` |
| `figures/图5_时距与分布偏移/code/README.md` |
| `figures/图5_时距与分布偏移/code/render_final.py` |
| `figures/图6_分段稳定性/code/README.md` |
| `figures/图6_分段稳定性/code/render_final.py` |
| `figures/图7_共同后缀与状态作用/code/README.md` |
| `figures/图7_共同后缀与状态作用/code/render_final.py` |
| `figures/图8_天气条件响应/code/README.md` |
| `figures/图8_天气条件响应/code/render_final.py` |
| `figures/图9_状态复用成本/code/README.md` |
| `figures/图9_状态复用成本/code/render_final.py` |

## 运行环境

| 项 | 值 |
|---|---|
| 服务器 | dilab |
| Python | `/data/zs/WorldModel2026/.venv-worldmodel/bin/python` |
| GPU（正式评测） | 4× NVIDIA A100-SXM4-40GB |
| 数据集根 | `/data/zs/TrainData/EarthNet2021/earthnet2021x` |

