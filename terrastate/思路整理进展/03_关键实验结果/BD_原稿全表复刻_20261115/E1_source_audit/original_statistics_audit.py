"""Read-only audit of saved scalar statistics; no inference or remote writes.

Run on the existing server Python through SSH stdin with -B.
All intervals below condition on the saved donor assignment and use the
existing receiver geographic groups. They are diagnostic percentile intervals,
not a retrospective preregistration or a replacement of the original package.
"""
import csv
import json
import math
from pathlib import Path
from collections import defaultdict
import numpy as np

ROOT = Path('/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/corrected_mask_recompute_20260910T071500Z/merged')


def group(cube):
    fields = Path(cube).name.split('_')
    return fields[2] if len(fields) >= 5 else 'lat=' + fields[2] + '_lon=' + fields[3]


def ci(values):
    return [float(x) for x in np.quantile(values, [.025, .975])]


for split in ['iid', 'ood_t', 'ood_s', 'ood_st']:
    sets = {'suffix': {}, 'endpoint': {}}
    bad = 0
    seen = set()
    duplicates = 0
    path = ROOT / split / 'plot_data/formal_common_suffix_per_cube_horizon.csv'
    with path.open() as handle:
        for row in csv.DictReader(handle):
            key = row['dataset_index']
            horizon = int(row['suffix_horizon'])
            row_key = (key, horizon)
            if row_key in seen:
                duplicates += 1
            seen.add(row_key)
            n = int(float(row['n_valid']))
            sse = [float(row[c + '_sse']) for c in ['D20', 'A', 'B', 'donor']]
            if n <= 0:
                continue
            if not all(math.isfinite(x) for x in sse):
                bad += 1
                continue
            for scope in (['suffix', 'endpoint'] if horizon == 10 else ['suffix']):
                if key not in sets[scope]:
                    sets[scope][key] = [group(row['cube']), np.zeros(7)]
                values = sets[scope][key][1]
                values[:5] += np.array([n] + sse)
                values[5] += float(row['A_B_output_mae']) * n
                values[6] += float(row['donor_A_output_mae']) * n
    for scope, items in sets.items():
        grouped = defaultdict(lambda: np.zeros(7))
        deltas = []
        total = np.zeros(7)
        for geo, values in items.values():
            delta = (values[4] - values[2]) / values[0]
            deltas.append(delta)
            total += values
            grouped[geo][:5] += values[:5]
            grouped[geo][5] += delta
            grouped[geo][6] += 1
        matrix = np.array(list(grouped.values()))
        group_means = matrix[:, 5] / matrix[:, 6]
        rng = np.random.default_rng(20260910)
        boot_cube, boot_geo, boot_pool, boot_a, boot_b = [], [], [], [], []
        for _ in range(10):
            indices = rng.integers(0, len(matrix), size=(200, len(matrix)))
            draw = matrix[indices].sum(axis=1)
            boot_cube.extend(draw[:, 5] / draw[:, 6])
            boot_geo.extend(group_means[indices].mean(axis=1))
            boot_pool.extend((draw[:, 4] - draw[:, 2]) / draw[:, 0])
            boot_a.extend(np.sqrt(draw[:, 2] / draw[:, 1]))
            boot_b.extend(np.sqrt(draw[:, 3] / draw[:, 1]))
        rmse = np.sqrt(total[1:5] / total[0])
        result = {
            'split': split, 'scope': scope, 'cubes': len(items),
            'groups': len(grouped), 'bad_positive_n_rows': bad,
            'duplicates': duplicates,
            'rmse': dict(zip(['direct', 'A', 'B', 'donor'], rmse.tolist())),
            'A_over_direct': float(rmse[1] / rmse[0]),
            'A_over_direct_ci95': ci(boot_a),
            'B_over_direct': float(rmse[2] / rmse[0]),
            'B_over_direct_ci95': ci(boot_b),
            'donor_cube_delta_mse': float(np.mean(deltas)),
            'donor_cube_delta_ci95': ci(boot_cube),
            'donor_geo_equal_delta_mse': float(group_means.mean()),
            'donor_geo_equal_ci95': ci(boot_geo),
            'donor_pooled_delta_mse': float((total[4] - total[2]) / total[0]),
            'donor_pooled_delta_ci95': ci(boot_pool),
            'AB_pooled_mae': float(total[5] / total[0]),
            'donorA_pooled_mae': float(total[6] / total[0]),
        }
        print(json.dumps(result), flush=True)
