"""非线性 φ 泄漏 probe 验证（适配 Stage1.5 数据格式）

目的：验证 cross-covariance 正则是否真的阻止了非线性 φ 泄漏
方法：训练 3 层 MLP probe: state_tokens → [sun_elevation, orbit_direction, satellite]
判定：若准确率显著低于 Stage1 → 说明 φ 泄漏约束有效

用法：
    python eval/eval_phi_leakage_probe_fixed.py \
        --stage1_ckpt checkpoints/stage1_vits_dual_staged/checkpoint_step_95000.pt \
        --stage1_5_ckpt checkpoints/stage1_5_dual_conditioned_vits/checkpoint_step_30000.pt \
        --batch_size 64 \
        --probe_epochs 5
"""

import argparse
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.encoders.multimodal_vit_encoder_film import MultiModalViTEncoderFiLM
from models.encoders.state_projection import SpatialStateProjector
from data.datasets.ssl4eo_dual import SSL4EODualConfig, create_ssl4eo_dual_dataset


class PhiLeakageProbe(nn.Module):
    """3 层 MLP probe 测试 phi 泄漏"""
    def __init__(self, state_dim=256, hidden_dim=512):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
        )
        # 预测头
        self.sun_head = nn.Linear(hidden_dim // 2, 1)  # 回归 sun_elevation
        self.orbit_head = nn.Linear(hidden_dim // 2, 2)  # 分类 orbit_direction (ASC/DESC)
        self.satellite_head = nn.Linear(hidden_dim // 2, 2)  # 分类 satellite (S1A/S1B)

    def forward(self, state_tokens):
        """
        Args:
            state_tokens: [B, state_dim]
        Returns:
            dict with 'sun', 'orbit', 'satellite' predictions
        """
        pooled = self.mlp(state_tokens)
        return {
            'sun': self.sun_head(pooled),
            'orbit': self.orbit_head(pooled),
            'satellite': self.satellite_head(pooled),
        }


def extract_state_tokens_stage15(encoder, state_projector, batch, device, modality='S2'):
    """提取 Stage1.5 的 state tokens（冻结模式）

    Args:
        modality: 'S1' or 'S2'，决定使用哪个模态的图像
    """
    img_key = 's1_image' if modality == 'S1' else 's2_image'
    img = batch[img_key].to(device)

    with torch.no_grad():
        # Stage1.5 的 encoder 可能需要 phi，但我们不传（测试纯 visual）
        tokens = encoder(img, modality=modality)
        if isinstance(tokens, tuple):
            tokens = tokens[0]  # [B, num_patches+1, embed_dim]

        # 去掉 CLS token，取平均池化
        tokens = tokens[:, 1:, :]  # [B, num_patches, embed_dim]
        pooled = tokens.mean(dim=1)  # [B, embed_dim]

        # 投影到 state 空间
        state_tokens = state_projector(pooled)  # [B, state_dim]

    return state_tokens


def train_probe(probe, encoder, state_projector, dataloader, device, epochs=5, modality='S2'):
    """训练 probe（encoder 冻结）"""
    probe.train()
    encoder.eval()
    state_projector.eval()

    optimizer = torch.optim.Adam(probe.parameters(), lr=1e-3, weight_decay=1e-4)

    for epoch in range(epochs):
        total_loss = 0
        pbar = tqdm(dataloader, desc=f'Probe Epoch {epoch+1}/{epochs} ({modality})')

        for batch in pbar:
            # 提取 state_tokens（冻结）
            state_tokens = extract_state_tokens_stage15(encoder, state_projector, batch, device, modality=modality)

            # Probe 预测
            pred = probe(state_tokens)

            # 计算损失
            loss = 0.0
            n_loss = 0

            phi_key = 's2_phi' if modality == 'S2' else 's1_phi'
            phi = batch.get(phi_key, {})

            # S2: sun_elevation 回归
            if modality == 'S2' and 'sun_elevation' in phi:
                sun_target = phi['sun_elevation'].to(device)
                sun_valid = torch.isfinite(sun_target)
                if sun_valid.any():
                    sun_loss = F.mse_loss(pred['sun'][sun_valid], sun_target[sun_valid].unsqueeze(-1))
                    loss = loss + sun_loss
                    n_loss += 1

            # S1: orbit_direction 分类
            if modality == 'S1' and 's1_orbit_direction' in phi:
                orbit_target = phi['s1_orbit_direction'].to(device)
                orbit_valid = orbit_target.ge(0)
                if orbit_valid.any():
                    orbit_loss = F.cross_entropy(pred['orbit'][orbit_valid], orbit_target[orbit_valid])
                    loss = loss + orbit_loss
                    n_loss += 1

            # S1: satellite 分类
            if modality == 'S1' and 's1_satellite' in phi:
                sat_target = phi['s1_satellite'].to(device)
                sat_valid = sat_target.ge(0)
                if sat_valid.any():
                    sat_loss = F.cross_entropy(pred['satellite'][sat_valid], sat_target[sat_valid])
                    loss = loss + sat_loss
                    n_loss += 1

            if n_loss > 0:
                loss = loss / n_loss
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            pbar.set_postfix({'loss': f'{loss.item():.4f}'})


def evaluate_probe(probe, encoder, state_projector, dataloader, device, modality='S2'):
    """评估 probe 性能"""
    probe.eval()
    encoder.eval()
    state_projector.eval()

    sun_errors = []
    orbit_correct = 0
    orbit_total = 0
    sat_correct = 0
    sat_total = 0

    with torch.no_grad():
        for batch in tqdm(dataloader, desc=f'Evaluating ({modality})'):
            state_tokens = extract_state_tokens_stage15(encoder, state_projector, batch, device, modality=modality)
            pred = probe(state_tokens)

            phi_key = 's2_phi' if modality == 'S2' else 's1_phi'
            phi = batch.get(phi_key, {})

            # S2: sun_elevation MAE
            if modality == 'S2' and 'sun_elevation' in phi:
                sun_target = phi['sun_elevation'].to(device)
                sun_valid = torch.isfinite(sun_target)
                if sun_valid.any():
                    sun_pred = pred['sun'][sun_valid].squeeze(-1)
                    sun_errors.extend((sun_pred - sun_target[sun_valid]).abs().cpu().tolist())

            # S1: orbit accuracy
            if modality == 'S1' and 's1_orbit_direction' in phi:
                orbit_target = phi['s1_orbit_direction'].to(device)
                orbit_valid = orbit_target.ge(0)
                if orbit_valid.any():
                    orbit_pred = pred['orbit'][orbit_valid].argmax(dim=-1)
                    orbit_correct += (orbit_pred == orbit_target[orbit_valid]).sum().item()
                    orbit_total += orbit_valid.sum().item()

            # S1: satellite accuracy
            if modality == 'S1' and 's1_satellite' in phi:
                sat_target = phi['s1_satellite'].to(device)
                sat_valid = sat_target.ge(0)
                if sat_valid.any():
                    sat_pred = pred['satellite'][sat_valid].argmax(dim=-1)
                    sat_correct += (sat_pred == sat_target[sat_valid]).sum().item()
                    sat_total += sat_valid.sum().item()

    results = {
        'sun_elevation_mae': sum(sun_errors) / len(sun_errors) if sun_errors else float('nan'),
        'orbit_accuracy': orbit_correct / orbit_total if orbit_total > 0 else float('nan'),
        'satellite_accuracy': sat_correct / sat_total if sat_total > 0 else float('nan'),
    }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage1_ckpt', type=str, required=True)
    parser.add_argument('--stage1_5_ckpt', type=str, required=True)
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--probe_epochs', type=int, default=5)
    parser.add_argument('--num_workers', type=int, default=4)
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # 加载数据集
    print("\n=== 加载数据集 ===")
    data_cfg = SSL4EODualConfig(
        base_path='/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1',
        phi_cache_root='/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed',
        v3_geom_root='/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed_v3_s1geom',
        shard_pattern='ssl4eos12_shard_{000001..000477}.tar',
        split='val',
        random_season=True,
        normalize=True,
        use_phi_cache=True,
        conditioned_pair=True,
    )

    dataloader = create_ssl4eo_dual_dataset(
        data_cfg,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        shuffle=False,
    )

    # 加载 Stage 1 模型
    print("\n=== Stage 1 (Baseline) ===")
    ckpt1 = torch.load(args.stage1_ckpt, map_location='cpu', weights_only=False)
    encoder1_cfg = ckpt1['config']['model']['encoder'].copy()
    # 移除配置中的 'type' 字段（不是构造函数参数）
    encoder1_cfg.pop('type', None)
    encoder1 = MultiModalViTEncoderFiLM(**encoder1_cfg).to(device)
    encoder1.load_state_dict(ckpt1['encoder_state_dict'], strict=False)

    state_projector1 = SpatialStateProjector(in_dim=encoder1_cfg['embed_dim'], state_dim=256).to(device)
    # Stage 1 没有 state_projector，用恒等映射

    print(f"Loaded Stage1 from {args.stage1_ckpt}")

    # 加载 Stage 1.5 模型
    print("\n=== Stage 1.5 (Ours) ===")
    ckpt15 = torch.load(args.stage1_5_ckpt, map_location='cpu', weights_only=False)
    encoder15_cfg = ckpt15['config']['model']['encoder'].copy()
    # 移除配置中的 'type' 字段（不是构造函数参数）
    encoder15_cfg.pop('type', None)
    encoder15 = MultiModalViTEncoderFiLM(**encoder15_cfg).to(device)
    encoder15.load_state_dict(ckpt15['encoder_state_dict'], strict=False)

    state_projector15 = SpatialStateProjector(in_dim=encoder15_cfg['embed_dim'], state_dim=256).to(device)
    if 'state_projector_state_dict' in ckpt15:
        state_projector15.load_state_dict(ckpt15['state_projector_state_dict'])

    print(f"Loaded Stage1.5 from {args.stage1_5_ckpt}")

    # 训练并评估 S2 probe
    print("\n=== S2: Sun Elevation Probe ===")

    print("\n--- Training Stage1 Probe (S2) ---")
    probe1_s2 = PhiLeakageProbe(state_dim=256).to(device)
    train_probe(probe1_s2, encoder1, state_projector1, dataloader, device, epochs=args.probe_epochs, modality='S2')
    results1_s2 = evaluate_probe(probe1_s2, encoder1, state_projector1, dataloader, device, modality='S2')

    print("\n--- Training Stage1.5 Probe (S2) ---")
    probe15_s2 = PhiLeakageProbe(state_dim=256).to(device)
    train_probe(probe15_s2, encoder15, state_projector15, dataloader, device, epochs=args.probe_epochs, modality='S2')
    results15_s2 = evaluate_probe(probe15_s2, encoder15, state_projector15, dataloader, device, modality='S2')

    # 训练并评估 S1 probe
    print("\n=== S1: Orbit/Satellite Probe ===")

    print("\n--- Training Stage1 Probe (S1) ---")
    probe1_s1 = PhiLeakageProbe(state_dim=256).to(device)
    train_probe(probe1_s1, encoder1, state_projector1, dataloader, device, epochs=args.probe_epochs, modality='S1')
    results1_s1 = evaluate_probe(probe1_s1, encoder1, state_projector1, dataloader, device, modality='S1')

    print("\n--- Training Stage1.5 Probe (S1) ---")
    probe15_s1 = PhiLeakageProbe(state_dim=256).to(device)
    train_probe(probe15_s1, encoder15, state_projector15, dataloader, device, epochs=args.probe_epochs, modality='S1')
    results15_s1 = evaluate_probe(probe15_s1, encoder15, state_projector15, dataloader, device, modality='S1')

    # 输出结果
    print("\n" + "=" * 70)
    print("最终结果对比")
    print("=" * 70)

    print("\n【S2: Sun Elevation】")
    print(f"  Stage1   MAE: {results1_s2['sun_elevation_mae']:.2f}°")
    print(f"  Stage1.5 MAE: {results15_s2['sun_elevation_mae']:.2f}°")
    delta_sun = results15_s2['sun_elevation_mae'] - results1_s2['sun_elevation_mae']
    print(f"  Δ (Stage1.5 - Stage1): {delta_sun:+.2f}° ({delta_sun/results1_s2['sun_elevation_mae']*100:+.1f}%)")

    print("\n【S1: Orbit Direction】")
    print(f"  Stage1   Acc: {results1_s1['orbit_accuracy']*100:.1f}%")
    print(f"  Stage1.5 Acc: {results15_s1['orbit_accuracy']*100:.1f}%")
    print(f"  Random baseline: 50.0%")
    delta_orbit = results15_s1['orbit_accuracy'] - results1_s1['orbit_accuracy']
    print(f"  Δ (Stage1.5 - Stage1): {delta_orbit*100:+.1f}%")

    print("\n【S1: Satellite】")
    print(f"  Stage1   Acc: {results1_s1['satellite_accuracy']*100:.1f}%")
    print(f"  Stage1.5 Acc: {results15_s1['satellite_accuracy']*100:.1f}%")
    print(f"  Random baseline: 50.0%")
    delta_sat = results15_s1['satellite_accuracy'] - results1_s1['satellite_accuracy']
    print(f"  Δ (Stage1.5 - Stage1): {delta_sat*100:+.1f}%")

    print("\n【判定】")
    # 判定标准：Stage1.5 相比 Stage1 下降 >20%，且接近随机（50%）
    orbit_drop = (results1_s1['orbit_accuracy'] - results15_s1['orbit_accuracy']) / results1_s1['orbit_accuracy']
    sat_drop = (results1_s1['satellite_accuracy'] - results15_s1['satellite_accuracy']) / results1_s1['satellite_accuracy']

    if orbit_drop > 0.2 and results15_s1['orbit_accuracy'] < 0.6:
        print("  ✅ Orbit Direction: 泄漏显著降低，接近随机（解耦成功）")
    elif orbit_drop > 0.1:
        print("  ⚠️ Orbit Direction: 泄漏有所降低，但未达理想（部分成功）")
    else:
        print("  ❌ Orbit Direction: 泄漏未显著降低（解耦失败）")

    if sat_drop > 0.2 and results15_s1['satellite_accuracy'] < 0.6:
        print("  ✅ Satellite: 泄漏显著降低，接近随机（解耦成功）")
    elif sat_drop > 0.1:
        print("  ⚠️ Satellite: 泄漏有所降低，但未达理想（部分成功）")
    else:
        print("  ❌ Satellite: 泄漏未显著降低（解耦失败）")

    print("=" * 70)


if __name__ == '__main__':
    main()
