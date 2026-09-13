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

## 本包自身的构建与校验脚本（`code/`，11 个文件）

这些脚本**构建并独立复核**了本发布包本身；它们是随包交付的审计线索，
不是产生科学结果的代码（后者见上表）。全部为只读检查或幂等重生成。

| 路径 | 字节 | sha256(前16) | 作用 |
|---|---:|---|---|
| `code/build_release.sh` | 5810 | `037547e1f0007181…` | 从只读来源目录**复制**（绝不移动）材料，组装出本包 |
| `code/check_links2.py` | 3354 | `7d3b962e1473edf3…` | 全包 markdown 相对链接解析检查 |
| `code/fix_links.py` | 4129 | `2ec39cac5b5121c5…` | 把叙事稿中的绝对符号链接改写为 `../figures/` 相对路径 |
| `code/gen_release_docs.py` | 20247 | `5fc9408b171587cd…` | 生成 README / SOURCE_COMMIT / CODE_AND_CONFIG_INDEX / WEIGHTS |
| `code/p1_fallback.py` | 3575 | `61aa09df355e4bb7…` | 为图3 / 图8 的绘图脚本加入数组回退路径 |
| `code/p1b_readmes.py` | 4229 | `707e2f762b492b9c…` | 重写图3 / 图8 的 code/README.md，标注历史脚本 |
| `code/p1c_redraw.py` | 4471 | `83d1a7c54152c303…` | 在瘦身副本中重绘全部六张图并与 selected/ 逐像素比对 |
| `code/p2a_fix_master.py` | 4170 | `4976d33d64dcbb0e…` | 修正历史母稿中「官方基线不可用」的过时说法 |
| `code/p3_diag.py` | 3335 | `9def5ee18f97ebe2…` | 链接与过时表述的诊断扫描 |
| `code/p3a_fixes.py` | 4771 | `abfd07c2c969fc64…` | 补齐被引用的四份中文参考文档并解除死链 |
| `code/verify_release.py` | 30948 | `a589bd1ec7c7d6ea…` | 41 项独立验收 + 重绘证明，并写出 SHA256SUMS.txt 与 QA_REPORT.md |

## 运行环境

| 项 | 值 |
|---|---|
| 服务器 | dilab |
| Python | `/data/zs/WorldModel2026/.venv-worldmodel/bin/python` |
| GPU（正式评测） | 4× NVIDIA A100-SXM4-40GB |
| 数据集根 | `/data/zs/TrainData/EarthNet2021/earthnet2021x` |

