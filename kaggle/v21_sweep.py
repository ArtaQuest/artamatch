"""v21_sweep.py — refine the regularisation by CROSS-VALIDATION ONLY, spending no test reads.

The coarse grid jumped from 179 surviving rules at alpha=2e-3 to 22 at 4e-3, and the CV rose by 0.02
across that gap, so the optimum sits inside it. Searching it costs nothing in test-set integrity as long
as nothing here touches the test set — and nothing here does. The winner is then handed to v21_fit for
a single declared read.

Also reports, per alpha, how much of the model's weight sits on era-dominated statements, because a
higher CV bought entirely with more Pluto is not the thing we are looking for.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
import v21_traditions as V21
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev/quality_good")
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))
GRID = [float(x) for x in os.environ.get(
    "AQ_GRID", "0.0020,0.0025,0.0030,0.0035,0.0040,0.0045,0.0050,0.0060,0.0070").split(",")]
ERA_RX = ("pluto", "neptune", "uranus", "cycle")


def main():
    from sklearn.linear_model import Lasso
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    ytr = yi.astype(float)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    parts, names = [], []
    for fn in (lambda d, s: V6.bank(d, Z, s), lambda d, s: V7.additions(d, Z, s),
               lambda d, s: V8.last_singles(d, Z, s)):
        a, nm = fn(tr, "train"); parts.append(a); names += nm
    ex = set(names)
    a, nm = V13.new_singles(tr, Z, "train", ex); parts.append(a); names += nm; ex |= set(nm)
    a, nm = V21.build(tr, Z, "train", ex, min_support=FLOOR); parts.append(a); names += nm
    X = np.column_stack(parts).astype(np.float32); del parts
    keep = np.array([clause_ok(n) for n in names]) & (X.sum(0) >= FLOOR) \
        & np.array([side(n) == "AB" for n in names])
    X = X[:, keep]; names = [n for n, k in zip(names, keep) if k]
    is_era = np.array([any(t in n for t in ERA_RX) for n in names])
    print(f"  bank {X.shape[1]:,} · era-flavoured statements {int(is_era.sum()):,} "
          f"({is_era.mean():.0%})\n")

    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a_, b_ in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a_), find(b_)
        if ra != rb:
            parent[ra] = rb
    gid = pd.factorize(pd.Series([find(a_) for a_ in ids.pid_a]))[0]

    print(f"  {'alpha':>8}{'CV(seed7)':>11}{'CV(mean3)':>11}{'rules':>7}{'non-era':>9}{'wt non-era':>12}")
    print("  " + "-" * 60)
    best = None
    for alpha in GRID:
        cvs = []
        for seed in (7, 23, 101):
            fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
            oof = np.full(len(yi), np.nan)
            for k in range(5):
                m = Lasso(alpha=alpha, positive=True, max_iter=8000).fit(X[fold != k], ytr[fold != k])
                s = np.where(m.coef_ > 0)[0]
                if len(s) >= 2:
                    w, b0 = G.fit_nonneg(X[fold != k][:, s], yi[fold != k],
                                         np.ones(int((fold != k).sum())))
                    oof[fold == k] = X[fold == k][:, s] @ w + b0
                else:
                    oof[fold == k] = 0.0
            cvs.append(G.auc(yi, oof))
        m = Lasso(alpha=alpha, positive=True, max_iter=20000).fit(X, ytr)
        s = np.where(m.coef_ > 0)[0]
        w, _ = G.fit_nonneg(X[:, s], yi, np.ones(len(yi))) if len(s) >= 2 else (np.array([]), 0)
        ne = int((~is_era[s]).sum())
        wne = float(w[~is_era[s]].sum() / max(w.sum(), 1e-9)) if len(s) >= 2 else 0.0
        print(f"  {alpha:>8.4f}{cvs[0]:>11.4f}{np.mean(cvs):>11.4f}{len(s):>7}{ne:>9}{wne:>11.0%}")
        if best is None or np.mean(cvs) > best[1]:
            best = (alpha, float(np.mean(cvs)), len(s))
    print(f"\n  CV winner (mean of 3 fold seeds): alpha={best[0]} · CV {best[1]:.4f} · {best[2]} rules")
    json.dump({"alpha": best[0], "cv_mean3": best[1], "n_rules": best[2]},
              open(os.path.expanduser("~/.artamatch-dev/v21_alpha.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
