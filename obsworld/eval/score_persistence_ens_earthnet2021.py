#!/usr/bin/env python
"""Compute official EarthNetScore for the persistence baseline on an EarthNet2021 split.

Persistence = per-pixel mean of cloud-free context frames, held constant across the
20 target frames (official earthnet-toolkit definition). Scored with the SAME
EarthNetScoreAccumulator used for our models, so it is a same-pipeline anchor.
"""
import sys, json, argparse
sys.path.insert(0, '.')
import torch
from torch.utils.data import DataLoader
from data.datasets.earthnet2021 import EarthNet2021Config, EarthNet2021Dataset, collate_earthnet2021
from train.train_stage2_earthnet import load_config
from eval.earthnet_standard_metrics import EarthNetScoreAccumulator
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **k): return x

ap = argparse.ArgumentParser()
ap.add_argument('--config', required=True)
ap.add_argument('--split', required=True)
ap.add_argument('--data-root', required=True)
ap.add_argument('--conditioning-stats-path', required=True)
ap.add_argument('--manifest-path', required=True)
ap.add_argument('--batch-size', type=int, default=8)
ap.add_argument('--num-workers', type=int, default=8)
ap.add_argument('--output', required=True)
a = ap.parse_args()

cfg = load_config(a.config)
cfg['data']['root'] = a.data_root
cfg['data']['conditioning_stats_path'] = a.conditioning_stats_path
cfg['data']['manifest_path'] = a.manifest_path
cfg['data']['split'] = a.split
dc = EarthNet2021Config.from_config(cfg['data'], split=a.split)
ds = EarthNet2021Dataset(dc)
ld = DataLoader(ds, batch_size=a.batch_size, shuffle=False, num_workers=a.num_workers,
                collate_fn=collate_earthnet2021)
acc = EarthNetScoreAccumulator(dc.eval_img_size)
T = 20
with torch.no_grad():
    for b in tqdm(ld, desc=f'persistence {a.split}'):
        xc = b['x_context']                       # B,10,4,H,W
        cm = b['context_mask'].unsqueeze(2)       # B,10,1,H,W  (1=valid)
        num = (xc * cm).sum(1)                     # B,4,H,W
        den = cm.sum(1)                            # B,1,H,W
        per = num / den.clamp(min=1e-6)            # B,4,H,W
        novalid = den < 0.5                        # pixels with no cloud-free context
        per = torch.where(novalid, xc.mean(1), per)
        pred = per.unsqueeze(1).expand(-1, T, -1, -1, -1).contiguous()  # B,20,4,H,W
        acc.update(pred, b['x_target'], b['target_mask'], [m['sample_id'] for m in b['meta']])
res = acc.compute()
json.dump({'metrics': res, 'split': a.split, 'baseline': 'persistence_context_mean',
           'num_samples': res.get('num_scored_cubes')}, open(a.output, 'w'), indent=2)
print(json.dumps(res, indent=2))
