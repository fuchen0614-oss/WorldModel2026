"""plan-b-pvt · Stage1.8 paired L1C/L2A dataset (reads the local npz cache).

Cache produced by scripts/cache_l1c_l2a_pairs.py: <cache>/<key>_s<season>.npz with
`l1c` and `l2a` int16 arrays (4, 256, 256) = the 4 common bands B02/B03/B04/B8A.
Normalized to reflectance [0,1] by /10000 (SSL4EO S2 int16 scale).
"""
from glob import glob
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset


class SSL4EOL1CL2APairedDataset(Dataset):
    def __init__(self, cache_dir: str, norm: float = 10000.0):
        self.files = sorted(p for p in glob(str(Path(cache_dir) / "*.npz")))
        self.norm = float(norm)
        if not self.files:
            raise FileNotFoundError(f"no .npz pairs in {cache_dir}")

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, i: int) -> dict:
        d = np.load(self.files[i])
        l1c = torch.from_numpy(d["l1c"].astype("float32")).clamp(0, self.norm) / self.norm
        l2a = torch.from_numpy(d["l2a"].astype("float32")).clamp(0, self.norm) / self.norm
        return {"l1c": l1c, "l2a": l2a}
