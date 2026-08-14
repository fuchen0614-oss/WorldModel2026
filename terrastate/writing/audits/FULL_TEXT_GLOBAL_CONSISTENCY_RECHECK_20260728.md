# TerraState 全文一致性最小同步复核

复核日期：2026-07-28  
复核对象：`MANUSCRIPT.md`、`MANUSCRIPT_ZH.md`  
权威英文：`paper/main.tex`  
权威中文：`MANUSCRIPT_ZH_FULL.md`

# TEXT_MIRRORS_SYNCHRONIZED

## 1. 问题计数

| 等级 | 同步前 | 同步后 | 说明 |
|---|---:|---:|---|
| Critical | 0 | **0** | 未发现方法、结果或证据方向错误 |
| Major | 1 | **0** | M1 已关闭 |
| Minor | 5 | **5** | 原审计 m1–m5 均不在本轮授权范围内，未改动 |

原审计唯一 Major M1 已完全关闭。两个精简镜像不再包含旧 Abstract、旧
endpoint-only Method、独立 Q4 或旧天气区间。

## 2. 英文镜像一致性

**判定：PASS。**

- Abstract 与 `paper/main.tex` 最终 Abstract 在 Markdown 表示层面一致；
- Section 3 与当前 Method 的模块、术语、信息边界和证据边界一致；
- Equations (1)–(8) 的公式内容、符号和顺序逐式一致；
- \(u_{t+1:t+H}\) 与 \(u_{t+1:t+h}\) 边界已恢复；
- Q2 为 state removal primary、\(T\to I\) supporting；
- Q3 使用完整 20-step forecast-window masked loss；
- 未恢复 recursive rollout、causal/counterfactual、complete physical state
  或 composition claim。

Figure、caption 和 Figure 引用块按任务要求保持原样，不进入本轮文本镜像同步
判定。

## 3. 中文精简镜像一致性

**判定：PASS。**

- 中文摘要与 `MANUSCRIPT_ZH_FULL.md` 最终摘要正文完全一致；
- Section 3 与完整中文 3.1–3.4 的方法事实、术语和主张强度一致；
- 中文 Equations (1)–(8) 与英文公式一一对应，标准化 formula bundle SHA
  与英文镜像相同；
- Q3 明确为完整 20 步预测窗口；
- 不再把“观测终点”作为 Q3 主判据；
- 独立 Q4／组合一致性／non-collapse 段落已删除。

完整中文文件末尾的“中文审阅导航（非投稿正文）”属于原审计 Minor m4，且该文件
本轮被明确禁止修改；它不改变精简中文正文已完成同步的判定。

## 4. Q4 与 Q3 专项

| 检查 | `MANUSCRIPT.md` | `MANUSCRIPT_ZH.md` |
|---|---:|---:|
| 独立 Q4 段落 | 0 | 0 |
| Method 中 Q4 | 0 | 0 |
| endpoint-only Q3 | 0 | 0 |
| complete 20-step window | PASS | PASS |
| Equation (8) control-minus-actual 方向 | PASS | PASS |
| causal/counterfactual 正向主张 | 0 | 0 |

Q3 已恢复为：

\[
\Delta L_{\rm ctrl}
=\mathcal L_{\rm win}(\widehat{\mathbf y}(u^{\rm ctrl}),\mathbf y)
-\mathcal L_{\rm win}(\widehat{\mathbf y}(u^{\rm act}),\mathbf y),
\]

其中 \(\mathcal L_{\rm win}\) 是完整 20 步预测窗口上的掩膜损失；正值表示真实
天气误差更低。

## 5. Sections 1、2、4–Conclusion 回归

**判定：全部未变。**

### 英文精简镜像

| 区块 | 修改前后共同 SHA-256 |
|---|---|
| Section 1 | `b3bb69be4770db6b682848a26bde13c1b4e3706afe96ba334eb36d71f7102f2d` |
| Section 2 | `948e3249fa5c85d1f10447d68a6d66c03a8f32a3e1fb5a84a768e175f0462009` |
| Section 4 | `4b2861326cf5f1061c8198de015eb97b848ff9c68661fd59755213f6131c171a` |
| Section 5 | `2761bf2bd15ae7704acda7d74cd593daecb1e1ff95eac59b06aa4ed66422b43f` |
| Section 6 | `1cb596d1f3c6e30eb61afc318b6805c7706151585b535e6b509fff7a4b02ba0c` |

### 中文精简镜像

| 区块 | 修改前后共同 SHA-256 |
|---|---|
| Section 1 | `7ed6a7c39658043fc663034fc948984f760e070fa5c5af61677853e33e53f117` |
| Section 2 | `141a3d704ed1dcbc28c1d4b8a9348ed38440e1ad965ed365507f4d9d3cc1b212` |
| Section 4 | `5cb9ab2c5f47c3091f610218d1fa1315001a0d998e236c52d7f3647f0c4a1bca` |
| Section 5 | `b166d8728f2124f445ccf1307ee94fbb11dcb4531c97814e3dd9e5dbe248feba` |
| Section 6 | `632d6bb513fc7b5a23d0b5e339dbf0bc142f8269ccfe574d200c2e50e97eb524` |

由于两个 Section 4 区块哈希逐字节不变，以下内容也得到直接保护：

- Q1–Q3 的全部结果数字；
- 40 epochs / 14,880 updates；
- Table 1–3；
- Figure 说明及引用；
- Limitations 与 Conclusion 的主张边界。

## 6. 历史工程词与禁止标签

两个精简镜像分别通过以下零命中检查：

- `11,904`：0；
- `boundary80`：0；
- `B0` / `B4`：0；
- `Stage A` / `Stage B`：0；
- `pilot`：0；
- `smoke`：0；
- Published/Local 标签：0；
- single-seed / single-run：0；
- `±`：0；
- 独立 Q4：0；
- endpoint-only Q3：0。

没有加入 SOTA 或严格排名语言，也没有说明公开数值来源或本地复现身份。

## 7. 权威文件保护

以下文件 SHA-256 与同步前全文审计记录完全一致：

| 文件 | SHA-256 |
|---|---|
| `paper/main.tex` | `1fe12204bad54b2b18a8debd5792cab9dff85a1e342cc35ca8df0e9a2d6eaab9` |
| `paper/main.pdf` | `5f3931e373643d7aa3674fa3517e2e4f1e58f1632bd279b513d11f28bc021691` |
| `paper/references.bib` | `e67c885bccb4aa6228424c06ec86c9255a462891029a7f3655521fff4e107659` |
| `MANUSCRIPT_ZH_FULL.md` | `0577238cd6d9561fb9ca7ea9fa4d8275da74a5b5f447e1d0407c4390d66099c6` |

Figure 1–3、Table 1–3、实验、JSON、代码、权重、证据文件和既有审计报告均未
修改。未重新编译 LaTeX。

## 8. Claim–evidence 最终检查

| 镜像主张 | 对应证据／边界 | 判定 |
|---|---|---|
| 保留 temporal-shift forecasting skill | Q1，Section 4 数字未变 | 支持 |
| state contribution is load-bearing | Q2 state removal primary | 支持 |
| learned transition involvement | \(T\to I\) supporting only | 支持且范围正确 |
| weather-response fidelity | Q3 complete 20-step window | 支持 |
| causal/counterfactual correctness | 明确不主张 | 边界正确 |
| Q4/composition | 已从两个精简 Method 清除 | 不主张 |

## 9. 最终判定

两个精简镜像的唯一 Major 已修复；Abstract、Section 3、Equations (1)–(8)、
Q3 窗口定义和 Q4 边界均已与各自权威源同步。未授权区块和权威文件保持不变。

# TEXT_MIRRORS_SYNCHRONIZED
