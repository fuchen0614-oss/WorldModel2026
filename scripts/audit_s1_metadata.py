#!/usr/bin/env python3
"""
audit_s1_metadata.py —— SSL4EO-S12-v1.1 S1GRD 几何字段可行性审查

目的（见 任务描述相关/19 + 18 §7.5）：核实能否为 S1 补充
  - orbit_direction (asc/desc)
  - incidence_angle
作为 phi v3 的 SAR 几何成像条件。

关键发现前置：S1GRD 的 zarr 内含 `file_id: [4] str`，存的是完整原始
Sentinel-1 产品 ID，例如：
  S1A_IW_GRDH_1SDV_20200307T145157_20200307T145222_031571_03A32A_72A2
  └┬┘ └┬┘ └─┬┘ └┬┘ └──────┬──────┘ └──────┬──────┘ └─┬──┘ └─┬──┘ └┬┘
  卫星  模式  产品  极化     起始时间          结束时间      绝对轨道 datatake 唯一码

本脚本：
  1. 抽样 train 前 5 / train 随机 5 / val 全部 shard；
  2. 每 shard 抽若干 zarr，读 file_id（4 时间片）；
  3. 解析产品 ID 各字段；
  4. 由绝对轨道号 + 成像时刻 + 经度，离线推算升/降轨（太阳同步轨道局地时法）；
  5. 统计完整性、缺失率、卫星/极化/模式分布；
  6. 输出 JSON 审查结果（不写入 phi，不碰旧 phi_processed）。

只读、CPU/IO-only、不占 GPU。建议 nice -n 19 ionice -c3 运行。
"""

import argparse
import io
import json
import random
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections.abc import MutableMapping

import numpy as np
import zarr

# Sentinel-1 产品 ID 正则
# S1A_IW_GRDH_1SDV_20200307T145157_20200307T145222_031571_03A32A_72A2
S1_PATTERN = re.compile(
    r'^(?P<mission>S1[AB])_'
    r'(?P<mode>[A-Z]{2})_'
    r'(?P<ptype>[A-Z]{3}[A-Z_])_'
    r'(?P<plevel>\d)(?P<class>[SA])(?P<pol>[SD][VH])_'
    r'(?P<start>\d{8}T\d{6})_'
    r'(?P<stop>\d{8}T\d{6})_'
    r'(?P<abs_orbit>\d{6})_'
    r'(?P<datatake>[0-9A-F]{6})_'
    r'(?P<uid>[0-9A-F]{4})$'
)

# 相对轨道公式（ESA 官方）：S1A 偏移 73，S1B 偏移 27，周期 175
REL_ORBIT_OFFSET = {'S1A': 73, 'S1B': 27}


def parse_s1_product_id(pid: str) -> Optional[Dict[str, Any]]:
    """解析单个 S1 产品 ID 为结构化字段。失败返回 None。"""
    if not pid or not isinstance(pid, str):
        return None
    m = S1_PATTERN.match(pid.strip())
    if not m:
        return None
    d = m.groupdict()
    abs_orbit = int(d['abs_orbit'])
    mission = d['mission']
    rel_orbit = ((abs_orbit - REL_ORBIT_OFFSET[mission]) % 175) + 1
    return {
        'mission': mission,
        'mode': d['mode'],
        'product_type': d['ptype'],
        'polarization': d['pol'],          # DV=dual VV+VH, DH=dual HH+HV, SV/SH=single
        'start': d['start'],
        'abs_orbit': abs_orbit,
        'rel_orbit': rel_orbit,
        'datatake': d['datatake'],
        'uid': d['uid'],
    }


def orbit_direction_from_lst(start: str, center_lon: float) -> Optional[str]:
    """太阳同步轨道局地时法推算升/降轨。

    Sentinel-1 升交点平局地时 (MLTAN) = 18:00。
    => 升轨整条 pass 局地太阳时 ≈ 18:00（午后/傍晚区间 [12,24)）
       降轨 ≈ 06:00（凌晨/上午区间 [0,12)）
    LST = UTC 小时 + 经度/15。

    这是离线代理，不是精确真值；高纬度边界有歧义。返回 'ascending'/'descending'/None。
    """
    if center_lon is None or not np.isfinite(center_lon):
        return None
    try:
        dt = datetime.strptime(start, '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
    except Exception:
        return None
    utc_hours = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    lst = (utc_hours + center_lon / 15.0) % 24.0
    return 'ascending' if 12.0 <= lst < 24.0 else 'descending'


class ZipFileStore(MutableMapping):
    """Zarr store wrapper for ZipFile（与 build_phi_cache.py 一致）。

    继承 MutableMapping 以满足 zarr KVStore 对完整 mapping 接口的要求。
    只读：__setitem__/__delitem__ 抛 NotImplementedError。
    """
    def __init__(self, zf):
        self.zf = zf

    def __getitem__(self, key):
        try:
            return self.zf.read(key)
        except KeyError:
            raise KeyError(key)

    def __contains__(self, key):
        try:
            self.zf.getinfo(key)
            return True
        except KeyError:
            return False

    def keys(self):
        return iter(self.zf.namelist())

    def __iter__(self):
        return self.keys()

    def __len__(self):
        return len(self.zf.namelist())

    def __setitem__(self, key, value):
        raise NotImplementedError("read-only store")

    def __delitem__(self, key):
        raise NotImplementedError("read-only store")


def read_zarr_buf(buf: io.BytesIO, member_name: str) -> Dict[str, Any]:
    """从内存中的 zarr.zip 字节流读取必要字段（不加载 bands 大数组）。

    注意：Zarr 2.11+ 要求 store 是 BaseStore 子类，需用 KVStore 包裹 MutableMapping
    （与 build_phi_cache.py 的 ZipFileStore 用法一致）。
    """
    try:
        from zarr.storage import KVStore
        zf = zipfile.ZipFile(buf)
        store = KVStore(ZipFileStore(zf))
        g = zarr.open(store, mode='r')
        out = {'member': member_name}
        for key in ['file_id', 'center_lon', 'center_lat', 'sample']:
            try:
                v = g[key][...]
                v = v.item() if v.ndim == 0 else v.tolist()
                out[key] = v
            except Exception:
                out[key] = None
        return out
    except Exception as e:
        return {'member': member_name, 'error': str(e)}


def audit_shard(tar_path: Path, samples_per_shard: int, seed: int = 0) -> Dict[str, Any]:
    """审查单个 shard：打开 tar 一次，抽样若干 zarr，解析 file_id。"""
    import tarfile
    rng = random.Random(seed)
    records = []
    total_members = 0
    sampled = 0
    with tarfile.open(tar_path, 'r') as tf:
        members = [m for m in tf.getmembers() if m.name.endswith('.zarr.zip')]
        total_members = len(members)
        picked = rng.sample(members, min(samples_per_shard, len(members))) if members else []
        sampled = len(picked)
        for m in picked:
            f = tf.extractfile(m)
            if f is None:
                records.append({'member': m.name, 'ok': False, 'err': 'extractfile None'})
                continue
            s = read_zarr_buf(io.BytesIO(f.read()), m.name)
            if 'error' in s:
                records.append({'member': m.name, 'ok': False, 'err': s['error']})
                continue
            file_ids = s.get('file_id')
            lon = s.get('center_lon')
            parsed_ts = []
            if isinstance(file_ids, list):
                for pid in file_ids:
                    p = parse_s1_product_id(pid)
                    if p:
                        p['orbit_direction'] = orbit_direction_from_lst(p['start'], lon)
                    parsed_ts.append({'raw': pid, 'parsed': p})
            records.append({
                'member': m.name, 'ok': True,
                'sample': s.get('sample'),
                'center_lon': lon, 'center_lat': s.get('center_lat'),
                'n_timesteps': len(file_ids) if isinstance(file_ids, list) else 0,
                'timesteps': parsed_ts,
            })
    return {
        'shard': tar_path.name,
        'total_members': total_members,
        'sampled': sampled,
        'records': records,
    }


def pick_shards(root: Path, split: str, mode: str, n: int, seed: int = 0) -> List[Path]:
    """选择 shard：mode='first' 取前 n；mode='random' 随机 n；mode='all' 全部。"""
    d = root / split / 'S1GRD'
    shards = sorted(d.glob('ssl4eos12_shard_*.tar'))
    if mode == 'first':
        return shards[:n]
    if mode == 'all':
        return shards
    rng = random.Random(seed)
    pool = shards[n:] if len(shards) > 2 * n else shards
    return rng.sample(pool, min(n, len(pool)))


def summarize(shard_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    n_samples = 0
    n_with_fileid = 0
    n_ts_total = 0
    n_ts_parsed = 0
    missions, pols, modes, ptypes, orbit_dirs = {}, {}, {}, {}, {}
    for sr in shard_results:
        for rec in sr['records']:
            if not rec.get('ok'):
                continue
            n_samples += 1
            ts = rec.get('timesteps', [])
            if ts and any(t['raw'] for t in ts):
                n_with_fileid += 1
            for t in ts:
                n_ts_total += 1
                p = t['parsed']
                if p:
                    n_ts_parsed += 1
                    missions[p['mission']] = missions.get(p['mission'], 0) + 1
                    pols[p['polarization']] = pols.get(p['polarization'], 0) + 1
                    modes[p['mode']] = modes.get(p['mode'], 0) + 1
                    ptypes[p['product_type']] = ptypes.get(p['product_type'], 0) + 1
                    od = p.get('orbit_direction')
                    orbit_dirs[od] = orbit_dirs.get(od, 0) + 1
    return {
        'n_samples_audited': n_samples,
        'n_samples_with_fileid': n_with_fileid,
        'fileid_presence_rate': round(n_with_fileid / max(n_samples, 1), 4),
        'n_timesteps_total': n_ts_total,
        'n_timesteps_parsed': n_ts_parsed,
        'product_id_parse_rate': round(n_ts_parsed / max(n_ts_total, 1), 4),
        'mission_dist': missions,
        'polarization_dist': pols,
        'mode_dist': modes,
        'product_type_dist': ptypes,
        'orbit_direction_dist': orbit_dirs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1')
    ap.add_argument('--samples-per-shard', type=int, default=10)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--out', default='/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/outputs/data_inspection/s1_metadata_audit.json')
    args = ap.parse_args()

    root = Path(args.root)
    plan = (
        [('train', s, 'first5') for s in pick_shards(root, 'train', 'first', 5)] +
        [('train', s, 'random5') for s in pick_shards(root, 'train', 'random', 5, args.seed)] +
        [('val', s, 'all') for s in pick_shards(root, 'val', 'all', 0)]
    )
    print(f"[audit] 计划审查 {len(plan)} 个 shard，每 shard 抽 {args.samples_per_shard} 样本")

    shard_results = []
    for split, tar_path, group in plan:
        print(f"  [{split}/{group}] {tar_path.name} ...", flush=True)
        sr = audit_shard(tar_path, args.samples_per_shard, seed=args.seed)
        sr['split'] = split
        sr['group'] = group
        shard_results.append(sr)

    summary = summarize(shard_results)
    out = {'summary': summary, 'shards': shard_results}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)

    print("\n" + "=" * 60)
    print("审查摘要：")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\n详细结果写入: {out_path}")


if __name__ == '__main__':
    main()
