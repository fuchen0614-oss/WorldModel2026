"""
Stage 1.5 轻量集成测试（smoke test，无需 GPU / 无需真实数据）。

只测"实际可用"的功能（见 14_*.md §2.5），不测空骨架：
  1. ImagingConditionEncoder 实例化 + forward 不报错 + 无 NaN（含 S1 无云、缺失值）
  2. MultiModalViTEncoderFiLM forward 正常；phi=0 与 no_phi 等价（零初始化 identity）
  3. MultiModalViTEncoderFiLM 能加载 stage1 ckpt（用临时假 state_dict 验证键匹配逻辑）
  4. ImagingDecouplingLoss 梯度可传，masked 正确
  5. dataloader collate：mock 的 phi_dict 列表 → tensor dict（batch_phi_dicts_to_tensors）
  6. train_step 风格的端到端前向（小模型 + 假 batch），验证 mae/decouple 无 NaN

运行：
    python -m pytest tests/test_stage1_5_integration.py -v
或直接：
    python -m tests.test_stage1_5_integration
"""

import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.encoders.imaging_condition_encoder import ImagingConditionEncoder
from models.encoders.multimodal_vit_encoder_film import MultiModalViTEncoderFiLM
from models.losses.imaging_decoupling import ImagingDecouplingLoss
from data.phi_loader import batch_phi_dicts_to_tensors


def _make_phi_batch(B=4, with_missing=True, s1_no_cloud=False):
    """构造单时间片 phi tensor dict（每字段标量 [B]）。"""
    phi = {
        'center_lat': torch.tensor([33.67, -20.0, 0.0, 11.0])[:B],
        'center_lon': torch.tensor([47.2, 140.0, -5.9, -70.0])[:B],
        'modality': torch.tensor([0, 0, 1, 1], dtype=torch.long)[:B],
        'time_valid': torch.ones(B, dtype=torch.long),
        'sun_elevation': torch.tensor([40., 30., -0.6, 10.])[:B],
        'season': torch.tensor([3, 1, 0, 2], dtype=torch.long)[:B],
    }
    if s1_no_cloud:
        # S1GRD：云字段缺失（NaN），但 time_valid=1
        phi['cloud_cover'] = torch.full((B,), float('nan'))
        phi['cloud_shadow'] = torch.full((B,), float('nan'))
        phi['valid_ratio'] = torch.full((B,), float('nan'))
    else:
        phi['cloud_cover'] = torch.tensor([0., 0.2, 0.05, 0.])[:B]
        phi['cloud_shadow'] = torch.tensor([0., 0.05, 0.02, 0.])[:B]
        phi['valid_ratio'] = torch.ones(B)
    if with_missing and B >= 1:
        # 第 0 个样本标为缺失时间片
        phi['time_valid'][0] = 0
        phi['sun_elevation'][0] = float('nan')
        phi['season'][0] = -1
    return phi


def test_imaging_condition_encoder():
    """1. ImagingConditionEncoder forward 无 NaN（单时间片，含 S1 无云 + 缺失值）。"""
    enc = ImagingConditionEncoder(embed_dim=128)
    for s1_no_cloud in (False, True):
        phi = _make_phi_batch(s1_no_cloud=s1_no_cloud)
        emb, tok = enc(phi)
        assert emb.shape == (4, 128), f"phi_embed shape {emb.shape}"
        assert tok.shape == (4, 1, 128), f"phi_tokens shape {tok.shape}"
        assert not torch.isnan(emb).any(), f"NaN in phi_embed (s1={s1_no_cloud})"
        assert not torch.isnan(tok).any(), f"NaN in phi_tokens (s1={s1_no_cloud})"
    print("✓ [1] ImagingConditionEncoder（单时间片）：S2/S1无云 均无 NaN，token=[B,1,D]")


def test_film_encoder_identity():
    """2. FiLM encoder：phi=0 与 no_phi 输出等价（零初始化 identity）。"""
    enc = MultiModalViTEncoderFiLM(img_size=64, embed_dim=64, depth=2, num_heads=4,
                                   phi_dim=64, use_film=True, use_cross_attention=True)
    enc.eval()
    x = torch.randn(2, 12, 64, 64)
    with torch.no_grad():
        out_zero, _, _ = enc(x, modality='S2', mask_ratio=0.0,
                             phi_embed=torch.zeros(2, 64), phi_tokens=torch.zeros(2, 4, 64))
        out_none, _, _ = enc(x, modality='S2', mask_ratio=0.0)
    diff = (out_zero - out_none).abs().max().item()
    assert diff < 1e-4, f"phi=0 vs no_phi 差异过大: {diff}"
    print(f"✓ [2] FiLM encoder identity：phi=0 vs no_phi 最大差异 {diff:.2e}")


def test_film_encoder_load_stage1():
    """3. FiLM encoder 能加载 stage1 风格 state_dict（共享键匹配，新增键在 missing）。"""
    enc = MultiModalViTEncoderFiLM(img_size=64, embed_dim=64, depth=2, num_heads=4, phi_dim=64)
    # 用自身参数里"非 FiLM/CA"的部分模拟 stage1 ckpt（patch_embed/pos/blocks.*.attn/mlp/norm）
    full_sd = enc.state_dict()
    stage1_sd = {k: v for k, v in full_sd.items()
                 if ('film' not in k and 'cross_attn' not in k)}
    info = enc.load_stage1_encoder_weights(stage1_sd, strict=False)
    assert info['loaded_from_stage1'] == len(stage1_sd), \
        f"加载数 {info['loaded_from_stage1']} != stage1 键数 {len(stage1_sd)}"
    # 新增参数（film/cross_attn）应出现在 missing_keys
    assert any('film' in k or 'cross_attn' in k for k in info['new_params']), \
        "FiLM/CA 应在 missing_keys"
    assert not info['unexpected'], f"不应有 unexpected: {info['unexpected'][:3]}"
    print(f"✓ [3] FiLM encoder 加载 stage1：共享 {info['loaded_from_stage1']} 键，"
          f"新增 {len(info['new_params'])} 键从零训")


def test_decoupling_loss_grad():
    """4. ImagingDecouplingLoss 梯度可传 + masked 正确。"""
    loss_fn = ImagingDecouplingLoss(w_consistency=1.0, w_counterfactual=0.5, w_decorr=0.1)
    B, D = 6, 64
    z1 = torch.randn(B, D, requires_grad=True)
    z2 = z1.detach() + 0.1 * torch.randn(B, D)
    z_shuf = torch.randn(B, D)
    phi = torch.randn(B, D)
    out = loss_fn(z1, z2, z_shuffled=z_shuf, phi_embed=phi)
    out['total'].backward()
    assert z1.grad is not None and not torch.isnan(z1.grad).any(), "梯度异常"
    for key in ('total', 'consistency', 'counterfactual', 'decorr'):
        assert key in out, f"缺少 loss 分量 {key}"
    # masked 不报错
    valid = torch.tensor([1, 1, 0, 1, 0, 1], dtype=torch.float)
    z1b = z1.detach().requires_grad_(True)
    out_m = loss_fn(z1b, z2, z_shuffled=z_shuf, phi_embed=phi, valid_mask=valid)
    assert not torch.isnan(out_m['total']), "masked total NaN"
    print(f"✓ [4] ImagingDecouplingLoss：梯度可传，masked OK "
          f"(total={out['total'].item():.3f})")


def test_collate_phi_to_tensors():
    """5. batch_phi_single_timestep_to_tensors：按选中季节 t 取单片 → [B] 标量。"""
    from data.phi_loader import batch_phi_single_timestep_to_tensors
    phi_dicts = [
        {'sample_key': 'k0', 'modality': 'S2L2A', 'center_lat': 33.6, 'center_lon': 47.2,
         'time_valid_0': 1, 'time_valid_1': 1, 'time_valid_2': 1, 'time_valid_3': 1,
         'sun_elevation_0': 40.0, 'sun_elevation_1': 65.0, 'sun_elevation_2': 55.0, 'sun_elevation_3': 35.0,
         'season_0': 3, 'season_1': 1, 'season_2': 2, 'season_3': 3,
         'cloud_cover_0': 0.0, 'cloud_cover_1': 0.1, 'cloud_cover_2': 0.5, 'cloud_cover_3': 0.0,
         'cloud_shadow_0': 0.0, 'cloud_shadow_1': 0.0, 'cloud_shadow_2': 0.1, 'cloud_shadow_3': 0.0,
         'valid_ratio_0': 1.0, 'valid_ratio_1': 1.0, 'valid_ratio_2': 1.0, 'valid_ratio_3': 1.0},
        # S1GRD，云字段缺失（None）
        {'sample_key': 'k1', 'modality': 'S1GRD', 'center_lat': None, 'center_lon': 140.0,
         'time_valid_0': 1, 'time_valid_1': 1, 'time_valid_2': 1, 'time_valid_3': 1,
         'sun_elevation_0': 30.0, 'sun_elevation_1': 22.0, 'sun_elevation_2': 45.0, 'sun_elevation_3': 50.0,
         'season_0': 1, 'season_1': 2, 'season_2': 0, 'season_3': 0,
         'cloud_cover_0': None, 'cloud_cover_1': None, 'cloud_cover_2': None, 'cloud_cover_3': None,
         'cloud_shadow_0': None, 'cloud_shadow_1': None, 'cloud_shadow_2': None, 'cloud_shadow_3': None,
         'valid_ratio_0': None, 'valid_ratio_1': None, 'valid_ratio_2': None, 'valid_ratio_3': None},
    ]
    # 样本0 选季节 2，样本1 选季节 3
    out = batch_phi_single_timestep_to_tensors(phi_dicts, season_indices=[2, 3])
    assert out['modality'].tolist() == [0, 1], f"modality codes {out['modality'].tolist()}"
    assert out['sun_elevation'].shape == (2,), f"应为标量 [B], got {out['sun_elevation'].shape}"
    assert abs(out['sun_elevation'][0].item() - 55.0) < 1e-4, "样本0 应取 sun_elevation_2=55"
    assert out['season'][0].item() == 2 and out['season'][1].item() == 0, "season 取片错误"
    assert torch.isnan(out['center_lat'][1]), "缺失 lat 应为 NaN"
    assert torch.isnan(out['cloud_cover'][1]), "S1 云字段应 NaN"
    # 喂给单时间片 encoder 不报错、不 NaN
    enc = ImagingConditionEncoder(embed_dim=64)
    emb, tok = enc(out)
    assert tok.shape == (2, 1, 64)
    assert not torch.isnan(emb).any(), "单片 collate 产物喂 encoder 后 NaN"
    print("✓ [5] batch_phi_single_timestep_to_tensors：按 t 取单片→[B]，缺失→NaN，喂 encoder 无 NaN")


def test_end_to_end_forward():
    """6. 端到端季节对比前向（小模型 + 假 batch），mae/InfoNCE 无 NaN。"""
    enc = MultiModalViTEncoderFiLM(img_size=64, embed_dim=64, depth=2, num_heads=4, phi_dim=64)
    phi_enc = ImagingConditionEncoder(embed_dim=64)
    loss_fn = ImagingDecouplingLoss(w_consistency=1.0, w_counterfactual=0.0, w_decorr=0.1)
    enc.train(); phi_enc.train()

    B = 4
    # 两个季节视图（同地点不同季节）
    s2_v1 = torch.randn(B, 12, 64, 64)
    s2_v2 = torch.randn(B, 12, 64, 64)
    phi_v1 = _make_phi_batch(B=B, s1_no_cloud=False, with_missing=False)
    phi_v2 = _make_phi_batch(B=B, s1_no_cloud=False, with_missing=False)
    phi_v2['season'] = (phi_v1['season'] + 1) % 4  # 不同季节

    pe_v1, pt_v1 = phi_enc(phi_v1)
    pe_v2, pt_v2 = phi_enc(phi_v2)

    # MAE（mask）
    tok1, m1, _ = enc(s2_v1, modality='S2', mask_ratio=0.75, phi_embed=pe_v1, phi_tokens=pt_v1)
    tok2, m2, _ = enc(s2_v2, modality='S2', mask_ratio=0.75, phi_embed=pe_v2, phi_tokens=pt_v2)
    assert not torch.isnan(tok1).any() and not torch.isnan(tok2).any(), "encoder forward NaN"

    # 对比（mask=0，各自真实 phi）
    z1 = enc(s2_v1, modality='S2', mask_ratio=0.0, phi_embed=pe_v1, phi_tokens=pt_v1)[0].mean(1)
    z2 = enc(s2_v2, modality='S2', mask_ratio=0.0, phi_embed=pe_v2, phi_tokens=pt_v2)[0].mean(1)
    dec = loss_fn(z_view1=z1, z_view2=z2, phi_embed=pe_v1)
    assert not torch.isnan(dec['total']), "InfoNCE total NaN"
    dec['total'].backward()
    print(f"✓ [6] 季节对比端到端：S2 MAE + InfoNCE 无 NaN "
          f"(consist={dec['consistency'].item():.3f} decorr={dec['decorr'].item():.3f})")


ALL_TESTS = [
    test_imaging_condition_encoder,
    test_film_encoder_identity,
    test_film_encoder_load_stage1,
    test_decoupling_loss_grad,
    test_collate_phi_to_tensors,
    test_end_to_end_forward,
]


def run_all():
    print("=" * 60)
    print("Stage 1.5 集成测试")
    print("=" * 60)
    torch.manual_seed(0)
    failed = 0
    for t in ALL_TESTS:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"✗ {t.__name__} 失败: {e}")
        except Exception as e:
            failed += 1
            print(f"✗ {t.__name__} 异常: {type(e).__name__}: {e}")
    print("=" * 60)
    if failed == 0:
        print(f"✓ 全部 {len(ALL_TESTS)} 个测试通过")
    else:
        print(f"✗ {failed}/{len(ALL_TESTS)} 个测试失败")
    return failed


if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)
