"""
EuroSAT Linear Probing 评估脚本。

冻结 Stage 1 预训练的 MultiModalViTEncoder，在 EuroSAT 上训练一个线性分类头，
用 Overall Accuracy (OA) 衡量 encoder 学到的特征质量。

对标基准（SSL4EO-S12 v1.0 论文 Table III, linear probing）：
    MAE ViT-S/16        = 94.1%   <- 你的直接对标（同为 MAE + 小 ViT）
    data2vec ViT-S/16   = 96.9%
    DINO/MoCo ViT-S/16  = 97.7%
    Random Init         = 81.3%   <- 下界

关键对齐点（必须与 Stage 1 训练一致，否则精度虚低）：
    - 波段：EuroSAT 13 波段 -> 丢弃 B10 (index 10) -> 12 波段，匹配 SSL4EO S2L2A
    - 归一化：clip(0, 10000) / 10000
    - 输入尺寸：resize 64 -> 256
    - 模态：S2 通路

流程：
    1. 加载 encoder checkpoint，冻结
    2. 提取所有图像特征（patch tokens 均值池化 -> [N, 256]），缓存到内存
    3. 80/20 划分 train/test（固定 seed）
    4. 训练线性头，报告 test OA + per-class accuracy
    5. 结果写入 JSON

用法：
    python eval/eval_linear_probe_eurosat.py \
        --checkpoint checkpoints/stage1_dual2/checkpoint_step_50000.pt \
        --eurosat-root /csy-mix02/cog8/zjliu17/Agent/TrainData/EuroSAT/ds/images/remote_sensing/otherDatasets/sentinel_2/tif \
        --epochs 100
"""

import argparse
import json
import os
import sys
import time
from glob import glob

import numpy as np
import tifffile
import torch
import torch.nn as nn
import torch.nn.functional as F

# 让脚本能 import 项目模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) if 'eval' in SCRIPT_DIR else SCRIPT_DIR
sys.path.insert(0, PROJECT_ROOT)
from models.encoders.multimodal_vit_encoder import MultiModalViTEncoder

# EuroSAT 10 类（按字母序，与目录一致）
EUROSAT_CLASSES = [
    "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
    "Pasture", "PermanentCrop", "Residential", "River", "SeaLake",
]

# EuroSAT AllBands 13 波段顺序：B01,B02,B03,B04,B05,B06,B07,B08,B08A,B09,B10,B11,B12
# SSL4EO S2L2A 是 L2A 产品，无 B10，需丢弃 index 10 得到 12 波段
B10_INDEX = 10


def load_encoder(checkpoint_path, device):
    """加载并冻结 encoder。"""
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    enc_cfg = ckpt["config"]["model"]["encoder"]
    encoder = MultiModalViTEncoder(**enc_cfg)
    encoder.load_state_dict(ckpt["encoder_state_dict"])
    encoder.eval().to(device)
    for p in encoder.parameters():
        p.requires_grad = False
    print(f"[encoder] 已加载 step={ckpt.get('global_step')}, "
          f"embed_dim={enc_cfg['embed_dim']}, 参数已冻结")
    return encoder, enc_cfg["embed_dim"]


def read_image(path):
    """读取一张 EuroSAT tif -> [12, H, W] float32，已对齐 SSL4EO 预处理。"""
    arr = tifffile.imread(path)              # [H, W, 13] uint16
    arr = np.transpose(arr, (2, 0, 1))       # [13, H, W]
    arr = np.delete(arr, B10_INDEX, axis=0)  # 丢弃 B10 -> [12, H, W]
    arr = arr.astype(np.float32)
    arr = np.clip(arr, 0, 10000) / 10000.0   # 与训练一致的归一化
    return arr


@torch.no_grad()
def extract_features(encoder, image_paths, labels, device, img_size=256, batch_size=128):
    """批量提取特征：patch tokens 均值池化 -> [N, embed_dim]。"""
    feats, labs = [], []
    buf_imgs, buf_labs = [], []

    def flush():
        if not buf_imgs:
            return
        x = torch.from_numpy(np.stack(buf_imgs)).to(device)          # [B,12,256,256]
        tokens, _, _ = encoder(x, modality="S2", mask_ratio=None)    # [B, N_patch, D]
        pooled = tokens.mean(dim=1)                                  # [B, D]
        feats.append(pooled.cpu())
        labs.extend(buf_labs)
        buf_imgs.clear()
        buf_labs.clear()

    t0 = time.time()
    for i, (path, lab) in enumerate(zip(image_paths, labels)):
        img = read_image(path)                                       # [12,64,64]
        t = torch.from_numpy(img).unsqueeze(0)                       # [1,12,64,64]
        t = F.interpolate(t, size=(img_size, img_size),
                          mode="bilinear", align_corners=False)      # [1,12,256,256]
        buf_imgs.append(t.squeeze(0).numpy())
        buf_labs.append(lab)
        if len(buf_imgs) >= batch_size:
            flush()
        if (i + 1) % 2000 == 0:
            print(f"  提取特征 {i+1}/{len(image_paths)} "
                  f"({(i+1)/(time.time()-t0):.0f} img/s)")
    flush()

    X = torch.cat(feats, dim=0)              # [N, D]
    y = torch.tensor(labs, dtype=torch.long) # [N]
    print(f"[features] 共 {X.shape[0]} 个样本，维度 {X.shape[1]}，"
          f"耗时 {time.time()-t0:.0f}s")
    return X, y


def train_linear_probe(X, y, num_classes, device, epochs=100, lr=1e-3,
                       wd=0.0, test_ratio=0.2, seed=42):
    """在缓存特征上训练线性头，返回 test OA 与 per-class acc。"""
    torch.manual_seed(seed)
    N = X.shape[0]
    perm = torch.randperm(N, generator=torch.Generator().manual_seed(seed))
    n_test = int(N * test_ratio)
    test_idx, train_idx = perm[:n_test], perm[n_test:]

    # 标准化特征（用 train 统计量）
    Xtr, Xte = X[train_idx], X[test_idx]
    ytr, yte = y[train_idx], y[test_idx]
    mean, std = Xtr.mean(0, keepdim=True), Xtr.std(0, keepdim=True) + 1e-6
    Xtr, Xte = ((Xtr - mean) / std).to(device), ((Xte - mean) / std).to(device)
    ytr, yte = ytr.to(device), yte.to(device)

    clf = nn.Linear(X.shape[1], num_classes).to(device)
    opt = torch.optim.AdamW(clf.parameters(), lr=lr, weight_decay=wd)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)

    print(f"[probe] train={len(train_idx)}, test={len(test_idx)}, "
          f"epochs={epochs}, lr={lr}")
    best_oa = 0.0
    for ep in range(epochs):
        clf.train()
        opt.zero_grad()
        loss = F.cross_entropy(clf(Xtr), ytr)
        loss.backward()
        opt.step()
        sched.step()

        if (ep + 1) % 10 == 0 or ep == epochs - 1:
            clf.eval()
            with torch.no_grad():
                pred = clf(Xte).argmax(1)
                oa = (pred == yte).float().mean().item()
            best_oa = max(best_oa, oa)
            print(f"  epoch {ep+1:3d} | loss {loss.item():.4f} | test OA {oa*100:.2f}%")

    # 最终 per-class accuracy
    clf.eval()
    with torch.no_grad():
        pred = clf(Xte).argmax(1)
    per_class = {}
    for c in range(num_classes):
        mask = (yte == c)
        if mask.sum() > 0:
            per_class[EUROSAT_CLASSES[c]] = (pred[mask] == c).float().mean().item()
    final_oa = (pred == yte).float().mean().item()
    return final_oa, best_oa, per_class


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--eurosat-root", default=(
        "/csy-mix02/cog8/zjliu17/Agent/TrainData/EuroSAT/ds/images/"
        "remote_sensing/otherDatasets/sentinel_2/tif"))
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--img-size", type=int, default=256)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", default="results/linear_probe_eurosat.json")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[device] {device}")

    # 收集所有图像路径与标签
    image_paths, labels = [], []
    for ci, cname in enumerate(EUROSAT_CLASSES):
        files = sorted(glob(os.path.join(args.eurosat_root, cname, "*.tif")))
        image_paths.extend(files)
        labels.extend([ci] * len(files))
    print(f"[data] {len(image_paths)} 张图，{len(EUROSAT_CLASSES)} 类")

    encoder, embed_dim = load_encoder(args.checkpoint, device)
    X, y = extract_features(encoder, image_paths, labels, device, args.img_size)
    final_oa, best_oa, per_class = train_linear_probe(
        X, y, len(EUROSAT_CLASSES), device,
        epochs=args.epochs, lr=args.lr, seed=args.seed)

    # 汇总输出
    print("\n" + "=" * 50)
    print(f"  最终 Test OA: {final_oa*100:.2f}%   (best: {best_oa*100:.2f}%)")
    print(f"  对标 MAE ViT-S/16 基线: 94.1%")
    verdict = ("✅ 达标" if final_oa >= 0.94
               else "⚠️ 基本可用" if final_oa >= 0.90
               else "❌ 偏低")
    print(f"  判定: {verdict}")
    print("=" * 50)
    print("  Per-class accuracy:")
    for cname, acc in per_class.items():
        print(f"    {cname:22s} {acc*100:.2f}%")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({
            "checkpoint": args.checkpoint,
            "final_oa": final_oa,
            "best_oa": best_oa,
            "per_class_accuracy": per_class,
            "baseline_mae_vits16": 0.941,
            "verdict": verdict,
            "config": vars(args),
        }, f, indent=2, ensure_ascii=False)
    print(f"\n[saved] {args.output}")


if __name__ == "__main__":
    main()
