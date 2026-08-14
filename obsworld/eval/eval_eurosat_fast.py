#!/usr/bin/env python
"""EuroSAT Linear Probing - 优化版（真正的 batch inference）"""
import argparse, glob, json, os, sys, time
import numpy as np, tifffile, torch, torch.nn as nn, torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.encoders.multimodal_vit_encoder import MultiModalViTEncoder

CLASSES = ["AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
           "Pasture", "PermanentCrop", "Residential", "River", "SeaLake"]

class EuroSATDataset(Dataset):
    def __init__(self, root, img_size=256):
        self.img_size = img_size
        self.paths, self.labels = [], []
        for ci, cn in enumerate(CLASSES):
            fs = sorted(glob.glob(os.path.join(root, cn, "*.tif")))
            self.paths.extend(fs)
            self.labels.extend([ci] * len(fs))

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        arr = tifffile.imread(self.paths[idx])           # [64,64,13]
        arr = np.transpose(arr, (2,0,1))                 # [13,64,64]
        arr = np.delete(arr, 10, axis=0).astype(np.float32)  # [12,64,64]
        arr = np.clip(arr, 0, 10000) / 10000.0
        t = torch.from_numpy(arr)
        t = F.interpolate(t.unsqueeze(0), size=(self.img_size, self.img_size),
                          mode="bilinear", align_corners=False).squeeze(0)
        return t, self.labels[idx]

@torch.no_grad()
def extract_features(encoder, loader, device):
    feats, labs = [], []
    t0 = time.time()
    for i, (x, y) in enumerate(loader):
        x = x.to(device)
        tokens, _, _ = encoder(x, "S2", mask_ratio=None)  # [B,N,D]
        pooled = tokens.mean(1).cpu()  # [B,D]
        feats.append(pooled)
        labs.append(y)
        if (i+1) % 20 == 0:
            done = (i+1) * loader.batch_size
            print(f"  {done}/{len(loader.dataset)} ({done/(time.time()-t0):.0f} img/s)")
    X = torch.cat(feats)
    y = torch.cat(labs)
    print(f"[features] {X.shape}, 耗时 {time.time()-t0:.0f}s")
    return X, y

def train_probe(X, y, device, epochs=100, lr=1e-3, test_ratio=0.2, seed=42):
    torch.manual_seed(seed)
    N = len(X)
    perm = torch.randperm(N, generator=torch.Generator().manual_seed(seed))
    n_test = int(N * test_ratio)
    test_idx, train_idx = perm[:n_test], perm[n_test:]

    Xtr, ytr = X[train_idx], y[train_idx]
    Xte, yte = X[test_idx], y[test_idx]
    mean, std = Xtr.mean(0, keepdim=True), Xtr.std(0, keepdim=True) + 1e-6
    Xtr = ((Xtr - mean) / std).to(device)
    Xte = ((Xte - mean) / std).to(device)
    ytr, yte = ytr.to(device), yte.to(device)

    clf = nn.Linear(X.shape[1], len(CLASSES)).to(device)
    opt = torch.optim.AdamW(clf.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)

    print(f"[probe] train={len(train_idx)}, test={len(test_idx)}, epochs={epochs}")
    best_oa = 0.0
    for ep in range(epochs):
        clf.train()
        opt.zero_grad()
        F.cross_entropy(clf(Xtr), ytr).backward()
        opt.step()
        sched.step()

        if (ep+1) % 10 == 0 or ep == epochs - 1:
            clf.eval()
            pred = clf(Xte).argmax(1)
            oa = (pred == yte).float().mean().item()
            best_oa = max(best_oa, oa)
            print(f"  epoch {ep+1:3d} | test OA {oa*100:.2f}%")

    clf.eval()
    pred = clf(Xte).argmax(1)
    final_oa = (pred == yte).float().mean().item()
    per_class = {}
    for c in range(len(CLASSES)):
        mask = (yte == c)
        if mask.sum() > 0:
            per_class[CLASSES[c]] = (pred[mask] == c).float().mean().item()
    return final_oa, best_oa, per_class

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--eurosat-root", default=(
        "/csy-mix02/cog8/zjliu17/Agent/TrainData/EuroSAT/ds/images/"
        "remote_sensing/otherDatasets/sentinel_2/tif"))
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--output", default="results/linear_probe_eurosat.json")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[device] {device}")

    dataset = EuroSATDataset(args.eurosat_root)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False,
                        num_workers=4, pin_memory=True)
    print(f"[data] {len(dataset)} 张图，{len(CLASSES)} 类")

    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    enc_cfg = ckpt["config"]["model"]["encoder"]
    encoder = MultiModalViTEncoder(**enc_cfg)
    encoder.load_state_dict(ckpt["encoder_state_dict"])
    encoder.eval().to(device)
    for p in encoder.parameters():
        p.requires_grad = False
    print(f"[encoder] step={ckpt['global_step']}, embed_dim={enc_cfg['embed_dim']}")

    X, y = extract_features(encoder, loader, device)
    final_oa, best_oa, per_class = train_probe(X, y, device, args.epochs)

    verdict = ("✅ 达标" if final_oa >= 0.94
               else "⚠️ 可用" if final_oa >= 0.90 else "❌ 偏低")

    print("\n" + "="*50)
    print(f"  最终 Test OA: {final_oa*100:.2f}%")
    print(f"  对标 MAE ViT-S/16: 94.1%")
    print(f"  判定: {verdict}")
    print("="*50)
    for cn, acc in per_class.items():
        print(f"    {cn:22s} {acc*100:.2f}%")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({
            "checkpoint": args.checkpoint,
            "final_oa": final_oa,
            "best_oa": best_oa,
            "per_class": per_class,
            "baseline": 0.941,
            "verdict": verdict,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n[saved] {args.output}")

if __name__ == "__main__":
    main()
