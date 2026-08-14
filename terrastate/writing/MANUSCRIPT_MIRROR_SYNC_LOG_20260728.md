# TerraState 全文文本镜像最小同步日志

日期：2026-07-28  
任务范围：只同步 `MANUSCRIPT.md` 与 `MANUSCRIPT_ZH.md` 的摘要和 Section 3。  
英文权威源：`paper/main.tex`  
完整中文权威源：`MANUSCRIPT_ZH_FULL.md`

## 1. 同步结果

本轮仅完成以下四项内容修改：

1. `MANUSCRIPT.md` Abstract 同步到当前 `paper/main.tex` Abstract；
2. `MANUSCRIPT.md` Section 3 同步到当前 Method，恢复 Equations (1)–(8)；
3. `MANUSCRIPT_ZH.md` 摘要同步到完整中文权威摘要；
4. `MANUSCRIPT_ZH.md` Section 3 同步到完整中文权威方法，恢复与英文
   Equations (1)–(8) 一一对应的公式。

没有修改两个镜像中的 Figure、caption、Table、Section 1、Section 2、
Section 4–Conclusion 或 References 区块。

## 2. 具体修复

### `MANUSCRIPT.md`

- 将旧的 `selected almost entirely`、`reusable world states` 和
  endpoint-prediction Abstract 替换为当前权威 Abstract；
- 将未来天气边界从旧的 \(u_{t:t+H}\)、\(u_{t:t+h}\) 恢复为
  \(u_{t+1:t+H}\)、\(u_{t+1:t+h}\)；
- 恢复当前 \(q/P/T/O\)、\(b_h+r_h\)、共享 residual transition、
  direct-per-horizon query 和 \(\alpha\) 切点；
- 恢复 GT、KD、future-state target 及总目标的 Equations (5)–(7)；
- 恢复 Equation (8) 的完整 20-step forecast-window fidelity；
- 删除旧的独立 Q4/composition/non-degeneracy 段；
- 保留 state removal 为 primary、\(T\to I\) 为 supporting；
- 保留 non-recursive、non-causal、non-counterfactual 和
  non-extreme-specific 边界。

### `MANUSCRIPT_ZH.md`

- 摘要与 `MANUSCRIPT_ZH_FULL.md` 的最终中文摘要逐字一致；
- Section 3 恢复完整 3.1–3.4 方法结构与 Equations (1)–(8)；
- Q3 从“观测终点”主判据恢复为完整 20 步预测窗口上的掩膜损失；
- 删除独立 Q4／组合一致性／non-collapse 叙事；
- 保留预测状态、共享天气条件转移、状态读出和干预证据的既定边界。

## 3. 修改前后文件 SHA-256

| 文件 | 修改前 | 修改后 |
|---|---|---|
| `MANUSCRIPT.md` | `8c8c47c00bc1ebc7337269f268539dfb9869fb73bc9a4feb2cc385a0ac3ebe21` | `82b7b2059f639a3cb257190ac6e0efb2462c54558be6e328f2741e78664b7229` |
| `MANUSCRIPT_ZH.md` | `d957d421af7efafb73d94ebd4775b3a1c150f01574d927c22197d27ac4c2f4ac` | `f4c3f7c1ce449816d48639deedd4382bf936581ce422e26772ccd9292433ef96` |

## 4. 修改区块 SHA-256

| 文件／区块 | 修改前 | 修改后 |
|---|---|---|
| `MANUSCRIPT.md` Abstract | `faee9746c622734d3572f16275f0052a0ab67bc29b9040680d21b2257c45382b` | `7c6a4023f77fa266aba00ae61ec5765a704a78df70c75c6e50e14b15ce26f34f` |
| `MANUSCRIPT.md` Section 3 | `c47b5c2d086c99a9f1eaeecedcbf590c3365eeca50997c57047c7db8154188b1` | `a92816307132415a8131146ff49739be8a3d4f13ade3a7610b4eae40acc7d523` |
| `MANUSCRIPT_ZH.md` 摘要 | `e9d1e594e4397f108fbcfa60e19a29c2e51bdcb353762f7f470c4f8795bf820e` | `f8911a491385f54854806b0f06e1506aff41767881dfa6e2e3b2b76dc368db74` |
| `MANUSCRIPT_ZH.md` Section 3 | `4471f8056ce16fb6bf1a4d9a9e9c7027d0a7a3692e2e1cd813616a39b193ec7c` | `6f84c7af58e774d916b0ccf34a312f583f24501c65ec0b876c5601be12182e6e` |

英文 Abstract 经 LaTeX→Markdown 表示转换并统一空白、破折号后，与
`paper/main.tex` Abstract 完全一致。中文摘要正文与
`MANUSCRIPT_ZH_FULL.md` 对应正文完全一致。

## 5. Equations (1)–(8) 回归

逐一移除 Markdown `\tag{}` 并标准化空白后，两个精简镜像的八条公式均与
`paper/main.tex` 对应公式完全一致：

| 检查 | `MANUSCRIPT.md` | `MANUSCRIPT_ZH.md` |
|---|---:|---:|
| Equation (1) | PASS | PASS |
| Equation (2) | PASS | PASS |
| Equation (3) | PASS | PASS |
| Equation (4) | PASS | PASS |
| Equation (5) | PASS | PASS |
| Equation (6) | PASS | PASS |
| Equation (7) | PASS | PASS |
| Equation (8) | PASS | PASS |

两文件标准化公式 bundle 的共同 SHA-256 为：

`0d0a1668707480425e46d3b03e8ae3cca6a058300ebb5cea1b152fa20300b2e8`

## 6. 未修改区块回归

### `MANUSCRIPT.md`

| 区块 | 修改前后共同 SHA-256 |
|---|---|
| Section 1 | `b3bb69be4770db6b682848a26bde13c1b4e3706afe96ba334eb36d71f7102f2d` |
| Section 2 | `948e3249fa5c85d1f10447d68a6d66c03a8f32a3e1fb5a84a768e175f0462009` |
| Section 4 | `4b2861326cf5f1061c8198de015eb97b848ff9c68661fd59755213f6131c171a` |
| Section 5 | `2761bf2bd15ae7704acda7d74cd593daecb1e1ff95eac59b06aa4ed66422b43f` |
| Section 6 | `1cb596d1f3c6e30eb61afc318b6805c7706151585b535e6b509fff7a4b02ba0c` |
| References | `4e6b45ffdf35b6acced4a2036c4dacba44b1ff2cce66c92a70eafdf280dd1003` |

### `MANUSCRIPT_ZH.md`

| 区块 | 修改前后共同 SHA-256 |
|---|---|
| Section 1 | `7ed6a7c39658043fc663034fc948984f760e070fa5c5af61677853e33e53f117` |
| Section 2 | `141a3d704ed1dcbc28c1d4b8a9348ed38440e1ad965ed365507f4d9d3cc1b212` |
| Section 4 | `5cb9ab2c5f47c3091f610218d1fa1315001a0d998e236c52d7f3647f0c4a1bca` |
| Section 5 | `b166d8728f2124f445ccf1307ee94fbb11dcb4531c97814e3dd9e5dbe248feba` |
| Section 6 | `632d6bb513fc7b5a23d0b5e339dbf0bc142f8269ccfe574d200c2e50e97eb524` |
| References | `795e08303e9ce9bfa557a3c9626cdc8fc73b1929173ae12347c2dd9d4e72c8a0` |

因此，Q1–Q3 结果数字、40 epochs、14,880 updates、Table 1–3、Figure
说明以及 Limitations/Conclusion 均保持原样。

## 7. 禁止叙事与历史工程词扫描

两个精简镜像分别满足：

| 项目 | 英文镜像 | 中文镜像 |
|---|---:|---:|
| 独立 Q4 段落 | 0 | 0 |
| endpoint-only Q3 | 0 | 0 |
| `11,904` | 0 | 0 |
| `boundary80` | 0 | 0 |
| `B0` / `B4` | 0 | 0 |
| `Stage A` / `Stage B` | 0 | 0 |
| `pilot` | 0 | 0 |
| `smoke` | 0 | 0 |
| Published/Local 标签 | 0 | 0 |
| single-seed / single-run | 0 | 0 |
| `±` | 0 | 0 |

`14,880` 在每个镜像中保留 2 次：同步前后均位于 Section 4 的实验协议与实现
说明中。Sections 4 的区块哈希完全不变。

## 8. 权威文件只读证明

| 文件 | 当前 SHA-256 | 与同步前审计 |
|---|---|---|
| `paper/main.tex` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` | 未变 |
| `paper/main.pdf` | `5f3931e373643d7aa3674fa3517e2e4f1e58f1632bd279b513d11f28bc021691` | 未变 |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` | 未变 |
| `MANUSCRIPT_ZH_FULL.md` | `0577238cd6d9561fb9ca7ea9fa4d8275da74a5b5f447e1d0407c4390d66099c6` | 未变 |

未编译 LaTeX；未处理 Figure、引用、AAAI 格式、附录或
Reproducibility Checklist。

## 9. 最终自检

- 摘要主张均可由 Q1–Q3 和 Limitations 支持：PASS。
- 公式、术语、信息边界和主辅证据层级一致：PASS。
- Q3 为完整 20 步窗口，不是 \(h=20\) endpoint：PASS。
- 未恢复 recursive rollout、因果、反事实、完整物理状态或 composition：PASS。
- 仅目标镜像的 Abstract 与 Section 3 发生变化：PASS。

