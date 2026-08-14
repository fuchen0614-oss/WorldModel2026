# Stage 1 → Stage 1.5 代码与概念地图

## Stage 1：双模态 MAE 观测表征

目标是从 SSL4EO-S12 的 S1/S2 观测学习可重建的空间 token，为后续状态建模提供初始化。

主要入口：

- 配置：`02_CONFIGS/configs/train/stage1_vits_dual_staged.yaml`
- 训练：`01_CODE_SNAPSHOT/train/train_stage1_vits.py`
- 编码器：`01_CODE_SNAPSHOT/models/encoders/multimodal_vit_encoder.py`
- 解码器：`01_CODE_SNAPSHOT/models/decoders/light_decoder.py`
- 重建损失：`01_CODE_SNAPSHOT/models/losses/reconstruction.py`
- 数据：`01_CODE_SNAPSHOT/data/datasets/ssl4eo.py`

冻结配置记录的是 ViT-S/16、S1/S2 轮流训练、75% mask、L1 reconstruction、95,000 steps。

## Stage 1.5：带成像条件的显式空间状态

目标不是简单提升重建，而是尝试把地表相关内容与成像条件 \(\phi\) 分开，并形成显式的 256 维 patch-wise state。

前向过程：

1. `PureImagingConditionEncoder` 编码 sun elevation、S1 orbit/satellite 等纯成像条件。
2. `MultiModalViTEncoderFiLM` 在最后四个 Transformer blocks 通过零初始化 FiLM 使用 \(\phi\)；正式配置关闭 cross-attention。
3. `SpatialStateProjector` 将 384 维 observation tokens 映射为 256 维 spatial state。
4. `StateReconstructionBridge` 把 state 映回 decoder token width。
5. `DualHeadDecoder` 在给定 \(\phi\) 下重建 S1/S2。

主要入口：

- 配置：`02_CONFIGS/configs/train/stage1_5_dual_conditioned_vits_60k.yaml`
- 同义明确配置：`02_CONFIGS/configs/train/stage1_5_dual_conditioned_vits_state_bridge_60k.yaml`
- 训练：`01_CODE_SNAPSHOT/train/train_stage1_5_dual_conditioned.py`
- 状态损失：`01_CODE_SNAPSHOT/models/losses/stage1_5_state.py`
- 评估：`03_TRAINING_AND_EVAL/eval/eval_phi_leakage_probe_fixed.py`

## Stage 1.5 损失角色

- masked reconstruction：保持观测信息和重建能力；
- cross-modal VICReg：对齐近同期 S1/S2 状态并抑制坍缩；
- phi cross-covariance：抑制 state 与原始成像字段的线性相关；
- feature anchor：约束 conditioned encoder 不偏离 Stage 1 初始化语义。

## 数据与训练约束

- S1/S2 配对最大间隔：7 天；
- 8 GPUs × 64 per GPU × accumulation 2 = effective batch 1,024；
- 60,000 steps；
- 新模块先训练，随后逐步部分解冻；
- 10% condition dropout；
- reconstruction 必须经过显式 state projector 和 bridge。

