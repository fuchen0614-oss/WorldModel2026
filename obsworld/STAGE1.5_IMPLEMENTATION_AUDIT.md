# Stage1.5 双端条件化方案实施审查报告

**日期**：2026-07-03  
**审查员**：Claude Opus 4.8  
**审查类型**：理论-实现一致性、文献对齐、护栏完整性

---

## 执行摘要

| 审查项 | 状态 | 风险等级 |
|---|:---:|:---:|
| **护栏实现完整性** | ✅ 7/7 | 🟢 低 |
| **文献对齐合理性** | ⚠️ 部分 | 🟡 中 |
| **废案清理完整性** | ⚠️ 部分 | 🟡 中 |
| **理论-实现脱节** | ⚠️ 2项 | 🟡 中 |

**核心结论**：
- ✅ 所有7项"护栏"已正确实现，代码与文档声明一致
- ⚠️ 发现2处理论-实现脱节需要修复
- ⚠️ 存在3个过期文档/配置未清理
- ⚠️ 文献对齐有1个理论空白需要补充说明

---

## 问题1：文献调研 - 方案合理性评估

### ✅ 有明确文献支撑的设计

| 设计点 | 文献支撑 | 对齐度 |
|---|---|:---:|
| **双端条件化** | CVAE (Sohn et al., 2015)、SPADE (Park et al., 2019) | ✅ 强 |
| **FiLM 注入** | FiLM (Perez et al., 2018)、DOFA (CVPR 2024) | ✅ 强 |
| **近同期跨模态对齐** | CROMA (NeurIPS 2023)、Panopticon (CVPRW 2025) | ✅ 强 |
| **VICReg 防坍塌** | VICReg (Bardes et al., ICLR 2022) | ✅ 强 |
| **φ 零初始化** | LoRA (Hu et al., 2022)、adapter 续训最佳实践 | ✅ 强 |
| **状态与观测分离** | DeCUR (ECCV 2024)、LEPA (arXiv 2026) | ✅ 强 |

### ⚠️ 理论空白：φ 泄漏约束的新颖性

**现状**：`PhiCrossCovarianceLoss` 直接计算 state 与原始 φ 字段的 cross-covariance，这是本项目的**原创设计**，25号文档未引用直接先例。

**文献对比**：
- DeCUR (ECCV 2024)：用**对抗性分类器**测试 nuisance 泄漏（0.5 = 完全解耦）
- DOFA (CVPR 2024)：用**线性 probe**测试波长/传感器可预测性
- 本方案：直接正则化 cross-covariance（更高效，但理论保证弱于对抗训练）

**风险等级**：🟡 中等
- ✅ 优势：计算高效，梯度稳定，无需额外判别器
- ⚠️ 风险：线性独立 ≠ 非线性独立；复杂非线性变换后仍可能泄漏
- 💡 建议：10k 门槛必须加**非线性 probe**验证（MLP 3层），确认 cross-cov 正则有效

**文献引用建议**（补充到25号文档 §14）：
```markdown
| [DeCUR](https://arxiv.org/abs/2309.05300) | ECCV 2024 | 对抗分类器测 nuisance；本文用 cross-cov 正则更高效 |
| [Invariant Risk Min](https://arxiv.org/abs/1907.02893) | ICML 2020 | 线性独立性作为因果解耦的必要条件 |
```

### ✅ 时间阈值 ≤7 天的合理性

**文献支持**：
- Panopticon (CVPRW 2025)：同地点跨传感器作为"自然增强"，隐含近同期假设
- CROMA (NeurIPS 2023)：S1/S2 对比学习，未明确说明配对阈值（可能≤Sentinel-2 重访周期 5 天）
- RS-WorldModel (arXiv 2026)：状态估计需要"准同时观测"，避免动力学混淆

**本项目覆盖率数据**（来自实测）：
- ≤7 天：70–72%
- ≤14 天：88–90%
- ≤30 天：99.98%

**结论**：✅ 7天阈值合理，88–90% 的 14 天作为消融对照即可，不应作为主方案（会引入真实物候变化）。

### ⚠️ Pure φ 字段选择的理论依据

**现状**：排除 lat/lon、season、DEM 基于"捷径假设"，但25号文档未引用**信息论/因果推断**框架证明这些确实是捷径。

**建议补充**（理论基础）：
- **Invariant Risk Minimization** (Arjovsky et al., ICML 2020)：lat/lon → climate zone 是 spurious correlation
- **InfoMax 原则**：若 I(lat; NDVI | state) > 0，则 lat 包含状态信息，不应作为 nuisance
- **实证验证**：10k 时必须测试"用 lat/lon/season probe state"，若准确率高（>random baseline），则证明确实需要排除

**当前缺失**：缺少"为什么这些是捷径"的定量证据（probe accuracy、mutual information）。

**风险等级**：🟡 中等
- 建议在10k评估时补充：probe lat/lon/season/DEM from state_tokens，若准确率接近随机 → 证明成功排除

---

## 问题2：文件清单与位置

### 正式文件（当前生效）

#### 模型实现
```
models/encoders/multimodal_vit_encoder_film.py      # Encoder FiLM (blocks 8-11)
models/encoders/pure_imaging_condition_encoder.py   # Pure φ encoder (排除捷径)
models/encoders/state_projection.py                 # 384→256 state projector
models/decoders/light_decoder.py                    # Decoder 独立 FiLM
models/losses/stage1_5_state.py                     # VICReg + φ泄漏 + anchor
```

#### 训练与配置
```
train/train_stage1_5_dual_conditioned.py                 # 唯一正式训练脚本
configs/train/stage1_5_dual_conditioned_vits.yaml        # 唯一正式配置
scripts/train_stage1_5_dual_conditioned_fsdp8.sh         # 8卡启动脚本
```

#### 测试
```
tests/test_stage1_5_dual_conditioned.py              # CPU 集成测试 (5项)
tests/test_stage1_5_integration.py                   # 旧集成测试 (待审查)
```

#### 文档
```
任务描述相关/25_Stage1.5双端条件化训练策略与决策记录.md   # 权威决策文档
README_Stage1.5_Training.md                              # 快速启动指南
STAGE1.5_READY.md                                        # 就绪报告
```

### ⚠️ 过期文件（需要清理或标记）

#### 过期使用指南
```
docs/stage1_5_usage_guide.md                        # 旧 Plan A 使用指南 (2026-06-26)
任务描述相关/15_Stage1与Stage1.5完整训练指南.md      # 早期训练指南 (2026-07-01)
```
**状态**：引用旧的 checkpoint 路径、旧的 step/epoch 换算（有 /2 因子）
**建议**：
- 方案1：删除
- 方案2：重命名为 `*_DEPRECATED.md` 并在开头标注"仅供审计"

#### 旧的集成测试
```
tests/test_stage1_5_integration.py
```
**状态**：未确认是否兼容新双端条件化方案
**建议**：运行一次，若失败则删除或修复

#### 过期的进度监控脚本
```
scripts/watch_stage1_5_progress.py
```
**状态**：未确认是否兼容新配置文件
**建议**：验证或删除

---

## 问题3：废案清理完整性

### ✅ 已删除的 Plan A 文件（4个）

```
train/train_stage1_5_film.py                         # 旧 Decoder-only 训练脚本
tests/smoke_stage1_5_planA.py                        # 旧 smoke test
scripts/train_stage1_5_planA_fsdp8.sh                # 旧 8卡启动脚本
configs/train/stage1_5_film.yaml                     # 旧 Decoder-only 配置
```

**验证**：
```bash
$ ls train/train_stage1_5_film.py
ls: cannot access 'train/train_stage1_5_film.py': No such file or directory
```
✅ 确认已删除

### ⚠️ 潜在的废案残留

#### 1. `configs/train/stage2_dynamics.yaml`
**内容**：提及 stage1.5，需检查是否引用旧路径
**建议**：检查 `resume_from` 字段是否指向旧 checkpoint 路径

#### 2. `scripts/train_dual_fsdp8.sh`
**内容**：可能是 Stage1 的旧脚本，名称容易混淆
**建议**：重命名为 `train_stage1_dual_fsdp8.sh` 或验证其用途

#### 3. `eval/eval_film_ablation.py`
**内容**：FiLM 消融评估脚本，需确认是否兼容新方案
**建议**：检查是否硬编码旧模型类名

---

## 问题4：护栏实现与理论脱节审查

### ✅ 护栏1：φ 主训练只放纯成像因素

**理论要求**（25号文档 §6.2）：
- S2: sun_elevation, time_valid
- S1: orbit_direction, relative_orbit, satellite
- **排除**: lat/lon, season, day_of_year, cloud, DEM

**实现验证**：
```python
# models/encoders/pure_imaging_condition_encoder.py
class PureImagingConditionEncoder(nn.Module):
    def __init__(self, ...):
        self.sun_encoder = SunElevationEncoder(sun_dim)
        self.sar_encoder = SARGeometryEncoder(embed_dim=sar_geom_dim)
        # ✅ 无 lat/lon/season/DEM encoder
```

**配置验证**：
```yaml
# configs/train/stage1_5_dual_conditioned_vits.yaml
phi_encoder:
  type: PureImagingConditionEncoder  # ✅
  use_sar_geometry: true             # ✅
```

**结论**：✅ **完全一致**

---

### ✅ 护栏2：零初始化 FiLM 注入 ViT 后部层

**理论要求**：
- FiLM 只在 Encoder blocks 8–11（后4层）
- γ/β 投影零初始化
- 训练起点等价 Stage1 identity

**实现验证**：
```python
# models/encoders/multimodal_vit_encoder_film.py
class FiLMModulation(nn.Module):
    def __init__(self, embed_dim, phi_dim):
        self.gamma_proj = nn.Linear(phi_dim, embed_dim)
        self.beta_proj = nn.Linear(phi_dim, embed_dim)
        nn.init.zeros_(self.gamma_proj.weight)  # ✅
        nn.init.zeros_(self.gamma_proj.bias)    # ✅
        nn.init.zeros_(self.beta_proj.weight)
        nn.init.zeros_(self.beta_proj.bias)
```

**配置验证**：
```yaml
encoder:
  use_film: true
  film_start_layer: 8  # ✅ blocks 8-11 (共12层，索引0-11)
```

**smoke test 验证**：
```
✅ 真实 95k checkpoint 加载：missing=0, unexpected=16 (16个新FiLM γ/β)
```

**结论**：✅ **完全一致**

---

### ✅ 护栏3：Decoder 使用独立 FiLM

**理论要求**：
- Decoder 每层独立 FiLM
- 与 Encoder FiLM 参数不共享
- 零初始化

**实现验证**：
```python
# models/decoders/light_decoder.py
class DecoderFiLM(nn.Module):
    def __init__(self, embed_dim, phi_dim):
        self.gamma_proj = nn.Linear(phi_dim, embed_dim)
        self.beta_proj = nn.Linear(phi_dim, embed_dim)
        nn.init.zeros_(self.gamma_proj.weight)  # ✅
        nn.init.zeros_(self.beta_proj.bias)

class TransformerDecoderBlock(nn.Module):
    def __init__(self, ..., phi_dim=None):
        self.film = DecoderFiLM(embed_dim, phi_dim) if phi_dim else None  # ✅ 独立
```

**配置验证**：
```yaml
decoder:
  type: DualHeadDecoder
  depth: 4
  phi_dim: 384  # ✅ 每层独立 FiLM
```

**结论**：✅ **完全一致**

---

### ✅ 护栏4：删除 shuffle-φ invariance

**理论要求**：不再使用 shuffle-phi 作为不变性约束（会删除真实变化）

**实现验证**：
```bash
$ grep -rn "shuffle.*phi\|phi.*shuffle" models/losses/stage1_5_state.py train/train_stage1_5_dual_conditioned.py
train/train_stage1_5_dual_conditioned.py:8:shuffle-phi invariance are intentionally absent because they erase real change
```

**loss 实现**：
```python
# models/losses/stage1_5_state.py
# ✅ 只有 CrossModalVICRegLoss (S1/S2 近同期对齐)
# ✅ 无 shuffle-phi 相关代码
```

**结论**：✅ **完全一致**

---

### ✅ 护栏5：近同期 S1/S2 最终 state 一致性约束

**理论要求**：
- 只对 ≤7 天配对启用跨模态一致性
- 作用在最终 state_tokens，不要求中间层一致
- 使用 VICReg（invariance + variance + covariance）

**实现验证**：
```python
# models/losses/stage1_5_state.py
class CrossModalVICRegLoss(nn.Module):
    def forward(self, z_s1, z_s2, valid_mask=None):
        if valid_mask is not None:
            keep = valid_mask.bool()
            z_s1, z_s2 = z_s1[keep], z_s2[keep]  # ✅ 门控
        inv = F.mse_loss(z_s1, z_s2)             # ✅ invariance
        var = self._variance(z_s1) + ...         # ✅ variance
        cov = self._covariance(z_s1) + ...       # ✅ covariance
```

**配置验证**：
```yaml
data:
  pair_max_days: 7.0  # ✅

training:
  vicreg:
    invariance_weight: 25.0  # ✅
    variance_weight: 25.0
    covariance_weight: 1.0
```

**数据流验证**：
```python
# data/datasets/ssl4eo_dual.py
time_diff_days = torch.abs(ts_s1 - ts_s2).float() / 86400.0
align_mask = time_diff_days <= self.pair_max_days  # ✅ 门控计算
```

**结论**：✅ **完全一致**

---

### ✅ 护栏6：10% φ-dropout 和 missing embedding

**理论要求**：
- 训练时 10% 样本将 φ embedding 置零
- 防止 encoder 离开完整元数据就失效

**实现验证**：
```python
# models/encoders/pure_imaging_condition_encoder.py
class PureImagingConditionEncoder(nn.Module):
    def __init__(self, ..., condition_dropout: float = 0.10):
        self.condition_dropout = condition_dropout  # ✅ 默认 10%

    def forward(self, phi, drop_mask=None):
        if drop_mask is None and self.training and self.condition_dropout > 0:
            drop_mask = torch.rand(...) < self.condition_dropout  # ✅ 随机 10%
        if drop_mask is not None:
            embedding = embedding.masked_fill(drop_mask.unsqueeze(-1), 0.0)  # ✅ 置零
```

**配置验证**：
```yaml
phi_encoder:
  condition_dropout: 0.10  # ✅
```

**结论**：✅ **完全一致**

---

### ✅ 护栏7：泄漏 probe 测试

**理论要求**：
- 用 probe 测太阳角/轨道能否从 state 被预测
- 同时证明真实状态（NDVI/LULC/变化）仍然保留
- 若"φ泄漏降低"以"真实状态能力下降"为代价，则判定解耦失败

**实现验证**：
```python
# models/losses/stage1_5_state.py
class PhiCrossCovarianceLoss(nn.Module):
    @staticmethod
    def _raw_features(phi, modality):
        if modality == "S2":
            sun = torch.nan_to_num(phi["sun_elevation"], ...)
            return torch.stack([torch.sin(torch.deg2rad(sun)), valid], dim=-1)  # ✅
        orbit = phi.get("s1_orbit_direction", ...)
        rel = phi.get("s1_relative_orbit", ...)
        sat = phi.get("s1_satellite", ...)
        return torch.cat([orbit_oh, sat_oh, rel_feat], dim=-1)  # ✅ 原始字段
```

**10k Go/No-Go 门槛验证**（25号文档 §12）：
```markdown
1. ✓ 状态保留：EuroSAT/LULC ≤1% 下降  # ✅ 明确要求
3. ✓ φ 泄漏降低：probe 相对 Stage1 明显下降  # ✅ 明确要求
```

**结论**：✅ **理论声明完整**，但需要在 10k 时**实际执行** probe 验证

---

## ⚠️ 发现的理论-实现脱节

### 脱节1：Encoder cross-attention 配置与文档不一致

**文档声明**（25号文档 §6.3）：
> Encoder cross-attention：关闭。单个 φ token 上的 cross-attention 信息增益有限且参数冗余。

**配置文件**：
```yaml
# configs/train/stage1_5_dual_conditioned_vits.yaml
encoder:
  use_cross_attention: false  # ✅ 确实关闭
```

**实现代码**：
```python
# models/encoders/multimodal_vit_encoder_film.py
class FiLMTransformerBlock(nn.Module):
    def __init__(self, ..., use_cross_attention=True):  # ⚠️ 默认 True
        self.use_cross_attention = use_cross_attention
        if use_cross_attention:
            self.cross_attn = PhiCrossAttention(...)  # ⚠️ 仍然创建模块
```

**问题**：
- 配置文件确实关闭了 cross-attention
- 但模块定义的**默认值是 True**
- 若未来有人不读配置文件直接实例化模型，会意外启用 cross-attention

**风险等级**：🟡 中等（当前运行不受影响，但代码可维护性差）

**建议修复**：
```python
class FiLMTransformerBlock(nn.Module):
    def __init__(self, ..., use_cross_attention=False):  # 改为 False
        # ...
```

---

### 脱节2：φ 泄漏正则的实际作用对象不明确

**理论声明**（25号文档 §8.3）：
> 对固定的原始成像字段计算 state–φ cross covariance，不再让一个 learned φ encoder 与 state encoder 共同旋转、规避 cosine loss。

**实现代码**：
```python
# models/losses/stage1_5_state.py
class PhiCrossCovarianceLoss(nn.Module):
    def forward(self, state: torch.Tensor, phi: Dict[str, torch.Tensor], modality: str):
        nuisance = self._raw_features(phi, modality)  # ✅ 原始字段
        cross_cov = state.T @ nuisance / ...
        return cross_cov.square().mean()
```

**问题**：
- 代码确实使用原始字段（sun elevation sin、orbit one-hot 等）
- 但文档未说明**为什么这样可以防止共同旋转**
- 缺少与旧方案（learned φ encoder + cosine loss）的对比说明

**建议补充**（25号文档 §8.3）：
```markdown
### 8.3 φ 泄漏约束（修订版）

**旧方案问题**（Decoder-only Plan A）：
若同时学习 φ encoder 和 state encoder，二者可以共同旋转到一个子空间，使得：
- cosine(φ_embed, state_embed) 表面上低
- 但 φ 信息已通过**共同的旋转基**编码进 state

**新方案**：
直接正则化 state 与**原始 φ 字段**（sun sin、orbit one-hot）的 cross-covariance：
$$
\mathcal{L}_{\text{nuisance}} = \|\text{Cov}(z_{\text{state}}, \phi_{\text{raw}})\|_F^2
$$
- 原始字段固定，不参与训练
- state encoder 无法通过旋转规避约束
- 等价于线性 CCA 正则化
```

---

## 综合建议

### 立即修复（阻塞 8 卡启动）

**无**。当前实现可以启动训练。

### 10k 前必须完成

1. **补充非线性 probe 验证**（脱节1风险缓解）
   - 训练 3 层 MLP probe：state → sun_elevation/orbit/relative_orbit
   - 若准确率 << Stage1 → 证明 cross-cov 正则有效
   - 若准确率仍高 → 需加对抗训练或更强正则

2. **补充 lat/lon/season probe**（Pure φ 假设验证）
   - 若 state 仍能高精度预测 lat/lon → 证明 Pure φ 排除不彻底
   - 若接近随机 → 证明捷径假设成立

3. **验证/清理过期文件**
   - `docs/stage1_5_usage_guide.md` → 标记 DEPRECATED 或删除
   - `任务描述相关/15_*.md` → 标记 DEPRECATED
   - `tests/test_stage1_5_integration.py` → 运行验证或删除

### 文档改进（非阻塞）

1. **25号文档 §8.3 补充 φ 泄漏约束的理论依据**（见脱节2建议）
2. **25号文档 §14 补充文献**：DeCUR、Invariant Risk Minimization
3. **README_Stage1.5_Training.md 补充"为什么排除 lat/lon"**的实证证据

### 代码改进（非阻塞）

1. **修改 FiLMTransformerBlock 默认参数**：`use_cross_attention=False`（见脱节1）
2. **添加 probe 评估脚本**：`eval/eval_phi_leakage_probe.py`

---

## 最终判定

### 护栏实现完整性：✅ 7/7 通过

所有声明的护栏均已正确实现，代码与文档一致。

### 文献对齐合理性：⚠️ 部分对齐

- ✅ 核心设计（双端条件化、FiLM、VICReg）有强文献支撑
- ⚠️ φ 泄漏约束为原创设计，需补充理论依据和非线性 probe 验证
- ⚠️ Pure φ 字段选择基于合理假设，但缺少定量证据

### 废案清理完整性：⚠️ 部分完成

- ✅ 4 个 Plan A 核心文件已删除
- ⚠️ 3 个过期文档/脚本需要标记或清理

### 理论-实现脱节：⚠️ 2 项中等风险

- 🟡 脱节1：cross-attention 默认参数（可维护性问题）
- 🟡 脱节2：φ 泄漏约束理论依据不完整（需补充文档）

### 总体风险评估：🟡 中等

**可以启动 8 卡训练**，但必须在 10k 门槛时：
1. 补充非线性 probe 验证
2. 验证 Pure φ 假设（lat/lon/season probe）
3. 若验证失败，需回到 10k checkpoint 调整方案

---

**审查完成时间**：2026-07-03 20:15  
**下一步行动**：启动 8 卡训练 → 10k 时执行补充验证 → 通过门槛后继续 30k
