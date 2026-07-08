#!/usr/bin/env python3
"""
validate_orbit_direction.py —— 用 Planetary Computer STAC 精确 orbit_state
验证离线 LST 启发式推算升/降轨的一致率。

输入：audit JSON（含 center_lat/lon + 解析后的产品起始时间 + 我的离线 orbit_direction）
做法：对抽样的产品，按 datetime±窗口 + center 点 bbox 查 PC STAC，匹配 abs_orbit，
      取 sat:orbit_state 作真值，与离线 LST 预测对比。
输出：一致率、混淆计数、不一致样例。

只读、网络 metadata-only（不下影像）。
"""
import argparse
import json
import random
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"


def stac_orbit_state(abs_orbit, start_str, lat, lon, window_min=20):
    """按时间窗 + bbox 查 STAC，匹配 abs_orbit，返回 sat:orbit_state 或 None。"""
    try:
        dt = datetime.strptime(start_str, '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
    except Exception:
        return None
    t0 = (dt - timedelta(minutes=window_min)).strftime('%Y-%m-%dT%H:%M:%SZ')
    t1 = (dt + timedelta(minutes=window_min)).strftime('%Y-%m-%dT%H:%M:%SZ')
    bbox = [lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5]
    body = {"collections": ["sentinel-1-grd"], "datetime": f"{t0}/{t1}",
            "bbox": bbox, "limit": 10}
    try:
        req = urllib.request.Request(
            STAC, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        js = json.load(urllib.request.urlopen(req, timeout=25))
    except Exception as e:
        return None
    for ft in js.get("features", []):
        p = ft["properties"]
        if int(p.get("sat:absolute_orbit", -1)) == int(abs_orbit):
            return p.get("sat:orbit_state")
    # 退化：无精确 abs_orbit 命中时，取第一个命中的 orbit_state（同时间窗同地点通常同轨）
    feats = js.get("features", [])
    if feats:
        return feats[0]["properties"].get("sat:orbit_state")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--audit', default='/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/outputs/data_inspection/s1_metadata_audit.json')
    ap.add_argument('--n', type=int, default=40, help='验证多少个时间片')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--out', default='/csy-mix02/cog8/zjliu17/Agent/WorldModel2026/outputs/data_inspection/orbit_direction_validation.json')
    args = ap.parse_args()

    d = json.load(open(args.audit))
    # 收集所有 (abs_orbit, start, lat, lon, my_pred)
    items = []
    for sr in d['shards']:
        for rec in sr['records']:
            if not rec.get('ok'):
                continue
            lat = rec.get('center_lat'); lon = rec.get('center_lon')
            for t in rec.get('timesteps', []):
                p = t.get('parsed')
                if p and lat is not None and lon is not None:
                    items.append({'abs_orbit': p['abs_orbit'], 'start': p['start'],
                                  'lat': lat, 'lon': lon, 'pred': p.get('orbit_direction'),
                                  'mission': p['mission'], 'rel_orbit': p['rel_orbit']})
    rng = random.Random(args.seed)
    # 优先覆盖 pred 两类，各抽一半
    asc = [x for x in items if x['pred'] == 'ascending']
    desc = [x for x in items if x['pred'] == 'descending']
    half = args.n // 2
    sample = rng.sample(asc, min(half, len(asc))) + rng.sample(desc, min(args.n - half, len(desc)))
    print(f"[validate] 总 {len(items)} 时间片, 抽 {len(sample)} 个查 STAC (asc {len(asc)}/desc {len(desc)})")

    results = []
    agree = 0; checked = 0
    for i, x in enumerate(sample):
        truth = stac_orbit_state(x['abs_orbit'], x['start'], x['lat'], x['lon'])
        ok = (truth is not None and x['pred'] is not None and truth == x['pred'])
        if truth is not None:
            checked += 1
            agree += int(ok)
        results.append({**x, 'stac_truth': truth, 'agree': ok})
        print(f"  [{i+1}/{len(sample)}] abs={x['abs_orbit']} pred={x['pred']} truth={truth} {'OK' if ok else 'X'}", flush=True)

    summary = {
        'n_sampled': len(sample),
        'n_checked_with_stac': checked,
        'n_agree': agree,
        'agreement_rate': round(agree / max(checked, 1), 4),
    }
    out = {'summary': summary, 'results': results}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, 'w'), indent=2, ensure_ascii=False, default=str)
    print("\n=== 验证摘要 ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"写入: {args.out}")


if __name__ == '__main__':
    main()
