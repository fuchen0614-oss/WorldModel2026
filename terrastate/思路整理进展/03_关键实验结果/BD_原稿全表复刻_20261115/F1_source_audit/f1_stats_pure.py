import numpy as np
def _boot(vals, n_boot, seed, alpha=0.05):
    a = np.asarray(vals, float); a = a[np.isfinite(a)]
    if a.size == 0:
        return dict(n=0, mean=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
                    frac_pos=float("nan"), significant_gt0=False)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, a.size, size=(n_boot, a.size))
    boots = a[idx].mean(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return dict(n=int(a.size), mean=float(a.mean()), ci_low=float(lo), ci_high=float(hi),
                frac_pos=float((a > 0).mean()), significant_gt0=bool(lo > 0))

def _cluster_boot(vals, clusters, n_boot, seed, alpha=0.05):
    a = np.asarray(vals, float); c = np.asarray(clusters)
    ok = np.isfinite(a); a, c = a[ok], c[ok]
    if a.size == 0:
        return dict(n=0, n_clusters=0, mean=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
                    significant_gt0=False)
    uniq = np.unique(c); rng = np.random.default_rng(seed)
    groups = {t: a[c == t] for t in uniq}
    boots = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.choice(uniq, size=uniq.size, replace=True)
        boots[b] = np.concatenate([groups[t] for t in pick]).mean()
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return dict(n=int(a.size), n_clusters=int(uniq.size), mean=float(a.mean()),
                ci_low=float(lo), ci_high=float(hi), significant_gt0=bool(lo > 0))