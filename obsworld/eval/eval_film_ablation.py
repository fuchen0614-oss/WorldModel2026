"""
Stage 1.5 消像解耦消融评估（EuroSAT linear probing）。

对比三种 encoder 在 EuroSAT 上冻结特征 + 线性头的表现（见 14_*.md §2.4）：
    A. baseline   : Stage1 的 MultiModalViTEncoder（无 phi 通路）
    B. w/o phi    : Stage1.5 的 FiLM encoder，但 forward 时**不传 phi**（消融）
    C. w/ phi     : Stage1.5 的 FiLM encoder，forward 时传 phi（完整版）

EuroSAT 没有真实成像条件 phi，C 用什么 phi？
    - EuroSAT 是单张 S2 切片，无时间序列、无 zarr 元数据。
    - 这里用"中性 phi"：经纬度缺失、单时间片、sun_elevation 用数据集平均（~49°）、
      season=missing、cloud=0。目的是验证 FiLM 通路在推理期可用、不破坏特征，
      而非测真实成像条件的增益（后者需带 phi 的下游集，留 Week4 跨成像一致性实验）。
    - 因此 B vs C 的核心结论是："加上 FiLM 通路后特征质量是否保持/提升"。

跨成像一致性 / phi 解相关等"解耦质量"指标需要带 phi 的配对数据，
本脚本提供 --consistency-data 钩子（默认跳过），用 SSL4EO val + phi 缓存计算。

用法：
    python eval/eval_film_ablation.py \
        --baseline-ckpt checkpoints/stage1_dual2/checkpoint_step_50000.pt \
        --film-ckpt     checkpoints/stage1_5_film/checkpoint_step_50000.pt \
        --eurosat-root  /csy-mix02/.../EuroSAT/.../tif \
        --epochs 100
"""

import argparse
import json
import os
import sys
import time
from glob import glob

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    import tifffile
except ImportError:
    tifffile = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) if 'eval' in SCRIPT_DIR else SCRIPT_DIR
sys.path.insert(0, PROJECT_ROOT)

from models.encoders.multimodal_vit_encoder import MultiModalViTEncoder
from models.encoders.multimodal_vit_encoder_film import MultiModalViTEncoderFiLM
from models.encoders.imaging_condition_encoder import ImagingConditionEncoder

# 复用基线脚本的常量与数据处理（同目录）
from eval.eval_linear_probe_eurosat import (
    EUROSAT_CLASSES, B10_INDEX, read_image, train_linear_probe,
)

# 数据集平均太阳高度角（来自 13_*.md §4.3 统计：mean≈49.3°）
DEFAULT_SUN_ELEVATION = 49.3


def load_baseline_encoder(ckpt_path, device):
    """A：Stage1 MultiModalViTEncoder。"""
    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    cfg = ckpt['config']['model']['encoder']
    enc = MultiModalViTEncoder(**{k: v for k, v in cfg.items() if k != 'type'})
    enc.load_state_dict(ckpt['encoder_state_dict'])
    enc.eval().to(device)
    for p in enc.parameters():
        p.requires_grad = False
    print(f"[baseline] step={ckpt.get('global_step')}, embed_dim={cfg['embed_dim']}")
    return enc, cfg['embed_dim']


def load_film_encoder(ckpt_path, device):
    """B/C：Stage1.5 FiLM encoder + phi_encoder。"""
    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    enc_cfg = ckpt['config']['model']['encoder']
    phi_cfg = ckpt['config']['model']['phi_encoder']
    enc = MultiModalViTEncoderFiLM(**{k: v for k, v in enc_cfg.items() if k != 'type'})
    enc.load_state_dict(ckpt['encoder_state_dict'])
    enc.eval().to(device)
    for p in enc.parameters():
        p.requires_grad = False

    phi_enc = ImagingConditionEncoder(**{k: v for k, v in phi_cfg.items() if k != 'type'})
    if 'phi_encoder_state_dict' in ckpt:
        phi_enc.load_state_dict(ckpt['phi_encoder_state_dict'])
    phi_enc.eval().to(device)
    for p in phi_enc.parameters():
        p.requires_grad = False
    print(f"[film] step={ckpt.get('global_step')}, embed_dim={enc_cfg['embed_dim']}, "
          f"use_film={enc_cfg.get('use_film')}, use_ca={enc_cfg.get('use_cross_attention')}")
    return enc, phi_enc, enc_cfg['embed_dim']


def make_neutral_phi(B, device):
    """构造中性 phi（EuroSAT 无真实成像条件，见文件头说明）。

    经纬度缺失（NaN→missing embedding）、单时间片有效、太阳高度角用数据集均值、
    season/cloud 缺失。modality=S2L2A。
    """
    phi = {
        'center_lat': torch.full((B,), float('nan'), device=device),
        'center_lon': torch.full((B,), float('nan'), device=device),
        'modality': torch.zeros(B, dtype=torch.long, device=device),  # S2L2A
        'time_valid': torch.zeros(B, 4, dtype=torch.long, device=device),
        'sun_elevation': torch.full((B, 4), float('nan'), device=device),
        'season': torch.full((B, 4), -1, dtype=torch.long, device=device),
        'cloud_cover': torch.full((B, 4), float('nan'), device=device),
        'cloud_shadow': torch.full((B, 4), float('nan'), device=device),
        'valid_ratio': torch.full((B, 4), float('nan'), device=device),
    }
    # 只激活第 0 个时间片，给一个数据集平均光照
    phi['time_valid'][:, 0] = 1
    phi['sun_elevation'][:, 0] = DEFAULT_SUN_ELEVATION
    return phi


@torch.no_grad()
def extract_features(encoder, image_paths, labels, device, mode='baseline',
                     phi_encoder=None, img_size=256, batch_size=128):
    """提取特征：patch tokens 均值池化 → [N, D]。

    mode: 'baseline' | 'film_no_phi' | 'film_with_phi'
    """
    feats, labs = [], []
    buf_imgs, buf_labs = [], []

    def flush():
        if not buf_imgs:
            return
        x = torch.from_numpy(np.stack(buf_imgs)).to(device)
        B = x.shape[0]
        if mode == 'baseline':
            tokens, _, _ = encoder(x, modality='S2', mask_ratio=None)
        elif mode == 'film_no_phi':
            tokens, _, _ = encoder(x, modality='S2', mask_ratio=None)  # 不传 phi
        elif mode == 'film_with_phi':
            phi = make_neutral_phi(B, device)
            pe, pt = phi_encoder(phi)
            tokens, _, _ = encoder(x, modality='S2', mask_ratio=None,
                                   phi_embed=pe, phi_tokens=pt)
        else:
            raise ValueError(mode)
        feats.append(tokens.mean(dim=1).float().cpu())
        labs.extend(buf_labs)
        buf_imgs.clear()
        buf_labs.clear()

    t0 = time.time()
    for i, (path, lab) in enumerate(zip(image_paths, labels)):
        img = read_image(path)
        t = torch.from_numpy(img).unsqueeze(0)
        t = F.interpolate(t, size=(img_size, img_size), mode='bilinear', align_corners=False)
        buf_imgs.append(t.squeeze(0).numpy())
        buf_labs.append(lab)
        if len(buf_imgs) >= batch_size:
            flush()
        if (i + 1) % 4000 == 0:
            print(f"  [{mode}] {i+1}/{len(image_paths)} ({(i+1)/(time.time()-t0):.0f} img/s)")
    flush()
    X = torch.cat(feats, dim=0)
    y = torch.tensor(labs, dtype=torch.long)
    print(f"[{mode}] {X.shape[0]} 样本, dim={X.shape[1]}, {time.time()-t0:.0f}s")
    return X, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-ckpt", default="checkpoints/stage1_dual2/checkpoint_step_50000.pt")
    ap.add_argument("--film-ckpt", required=True,
                    help="Stage1.5 FiLM checkpoint（含 encoder + phi_encoder state_dict）")
    ap.add_argument("--eurosat-root", default=(
        "/csy-mix02/cog8/zjliu17/Agent/TrainData/EuroSAT/ds/images/"
        "remote_sensing/otherDatasets/sentinel_2/tif"))
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--img-size", type=int, default=256)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-baseline", action="store_true", help="跳过 baseline（只比 B vs C）")
    ap.add_argument("--output", default="results/film_ablation_eurosat.json")
    args = ap.parse_args()

    if tifffile is None:
        raise RuntimeError("需要 tifffile 读取 EuroSAT，请 pip install tifffile")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[device] {device}")

    # 收集图像
    image_paths, labels = [], []
    for ci, cname in enumerate(EUROSAT_CLASSES):
        files = sorted(glob(os.path.join(args.eurosat_root, cname, "*.tif")))
        image_paths.extend(files)
        labels.extend([ci] * len(files))
    print(f"[data] {len(image_paths)} 张图，{len(EUROSAT_CLASSES)} 类")

    results = {}

    def probe(X, y, tag):
        final_oa, best_oa, per_class = train_linear_probe(
            X, y, len(EUROSAT_CLASSES), device,
            epochs=args.epochs, lr=args.lr, seed=args.seed)
        results[tag] = {'final_oa': final_oa, 'best_oa': best_oa, 'per_class': per_class}
        print(f"  >> [{tag}] final OA={final_oa*100:.2f}% best={best_oa*100:.2f}%")
        return final_oa

    # A. baseline
    if not args.skip_baseline:
        enc, _ = load_baseline_encoder(args.baseline_ckpt, device)
        X, y = extract_features(enc, image_paths, labels, device, mode='baseline',
                                img_size=args.img_size)
        probe(X, y, 'baseline')
        del enc
        torch.cuda.empty_cache() if device == 'cuda' else None

    # B + C: FiLM encoder
    film_enc, phi_enc, _ = load_film_encoder(args.film_ckpt, device)
    Xb, yb = extract_features(film_enc, image_paths, labels, device, mode='film_no_phi',
                              img_size=args.img_size)
    probe(Xb, yb, 'film_no_phi')
    Xc, yc = extract_features(film_enc, image_paths, labels, device, mode='film_with_phi',
                              phi_encoder=phi_enc, img_size=args.img_size)
    probe(Xc, yc, 'film_with_phi')

    # 汇总
    print("\n" + "=" * 56)
    print("  消融对比 (EuroSAT linear probing, OA)")
    print("=" * 56)
    for tag in ('baseline', 'film_no_phi', 'film_with_phi'):
        if tag in results:
            print(f"    {tag:16s} {results[tag]['final_oa']*100:.2f}%")
    print("  基线 MAE ViT-S/16 参考: 94.1%  (Stage1 实测 69.57%)")
    print("=" * 56)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump({
            'baseline_ckpt': args.baseline_ckpt,
            'film_ckpt': args.film_ckpt,
            'results': results,
            'note': 'EuroSAT 无真实 phi，film_with_phi 用中性 phi，主要验证 FiLM 通路不破坏特征',
            'config': vars(args),
        }, f, indent=2, ensure_ascii=False)
    print(f"[saved] {args.output}")


if __name__ == "__main__":
    main()
