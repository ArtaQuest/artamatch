"""v31_regularisers.py — the model side, not the feature side: what selection rule maximises CV?

Every fit so far has used one rule — non-negative Lasso, with a relaxed refit. That is one point in a
space of standard choices, and the others have never been measured on this bank. Six are compared here
on identical folds, identical features, and the same relaxed non-negative refit, so the only thing
varying is HOW statements are chosen:

  lasso          L1. The incumbent. Picks one statement from a correlated group and drops the rest,
                 which is exactly wrong for a doctrine bank where Vedic and Chinese say related things.
  enet           L1 + L2. Keeps correlated groups together instead of picking an arbitrary member —
                 the textbook fix for the failure above.
  adaptive       Lasso whose penalty on each statement is 1/|first-pass coefficient|: statements that
                 looked strong get penalised less. Has oracle properties Lasso lacks.
  stability      Fit on many bootstrap resamples and keep only statements selected in at least PI of
                 them. Meinshausen-Buhlmann. The strongest known defence against selecting noise in
                 p >> n, and it costs nothing but time.
  stability_enet stability selection with elastic net as the base learner.
  ridge_thresh   L2 over everything, then keep the largest coefficients — no sparsity during fitting.

Everything is nested inside the folds: orientation, selection, and the refit all happen on the fold's
training rows alone. The test set is untouched here; this file only reports cross-validation.

Usage: v31_regularisers.py [corpus_dir]
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v22_nnls import build, orient, apply_flip
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev/quality_good")
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))
SEEDS = (7, 23, 101)
B_BOOT = int(os.environ.get("AQ_BOOT", "24"))
PI = float(os.environ.get("AQ_PI", "0.6"))


def relaxed(Xa, y, idx):
    if len(idx) < 2:
        return None, None
    w, b = G.fit_nonneg(Xa[:, idx], y, np.ones(len(y)))
    return w, b


def sel_lasso(Xa, y, a):
    from sklearn.linear_model import Lasso
    m = Lasso(alpha=a, positive=True, max_iter=8000).fit(Xa, y)
    return np.where(m.coef_ > 0)[0]


def sel_enet(Xa, y, a, l1=0.7):
    from sklearn.linear_model import ElasticNet
    m = ElasticNet(alpha=a, l1_ratio=l1, positive=True, max_iter=8000).fit(Xa, y)
    return np.where(m.coef_ > 0)[0]


def sel_adaptive(Xa, y, a):
    from sklearn.linear_model import Lasso
    m0 = Lasso(alpha=a * 0.4, positive=True, max_iter=6000).fit(Xa, y)
    wgt = np.abs(m0.coef_)
    keep = np.where(wgt > 0)[0]
    if len(keep) < 2:
        return keep
    # Penalise each survivor by the inverse of how strong it first looked. Scaling the COLUMNS by the
    # first-pass weights is equivalent and cheaper than a per-feature penalty — but it shrinks the
    # design by roughly the mean weight, so alpha has to be rescaled by the same factor or the fit
    # returns nothing at all. It did: zero rules, CV 0.5000, which is a bug and not a verdict on the
    # method.
    ws = wgt[keep]
    Xs = Xa[:, keep] * ws
    a_eff = a * float(ws.mean())
    m = Lasso(alpha=a_eff, positive=True, max_iter=8000).fit(Xs, y)
    return keep[m.coef_ > 0]


def sel_stability(Xa, y, a, base="lasso", rng=None, B=B_BOOT, pi=PI):
    n, p = Xa.shape
    cnt = np.zeros(p)
    f = sel_lasso if base == "lasso" else sel_enet
    for b in range(B):
        ix = rng.choice(n, size=n // 2, replace=False)
        s = f(Xa[ix], y[ix], a)
        cnt[s] += 1
    return np.where(cnt / B >= pi)[0]


def sel_ridge(Xa, y, a, k=12):
    from sklearn.linear_model import Ridge
    m = Ridge(alpha=a * 3000, positive=True).fit(Xa, y)
    return np.argsort(-m.coef_)[:k]


def main():
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    ytr = yi.astype(float)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X, names = build(tr, Z, "train")
    keep = np.array([clause_ok(n) for n in names]) & (X.sum(0) >= FLOOR) \
        & np.array([side(n) == "AB" for n in names])
    X = X[:, keep]; names = [n for n, k in zip(names, keep) if k]
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
    print(f"  bank {X.shape[1]:,} statements · train {len(tr):,}\n", flush=True)

    METHODS = {
        "lasso":          (lambda Xa, y, a, r: sel_lasso(Xa, y, a),            (0.005, 0.007, 0.009)),
        "enet .7":        (lambda Xa, y, a, r: sel_enet(Xa, y, a, 0.7),        (0.005, 0.007, 0.010)),
        "enet .4":        (lambda Xa, y, a, r: sel_enet(Xa, y, a, 0.4),        (0.007, 0.010, 0.014)),
        "adaptive":       (lambda Xa, y, a, r: sel_adaptive(Xa, y, a),         (0.004, 0.007, 0.010)),
        "stability":      (lambda Xa, y, a, r: sel_stability(Xa, y, a, "lasso", r), (0.007, 0.010)),
        "stability enet": (lambda Xa, y, a, r: sel_stability(Xa, y, a, "enet", r),  (0.007, 0.010)),
        "ridge+top12":    (lambda Xa, y, a, r: sel_ridge(Xa, y, a),            (0.004, 0.008)),
    }
    print(f"  {'method':<16}{'alpha':>8}{'CV(mean3)':>11}{'spread':>9}{'rules':>7}")
    print("  " + "-" * 52)
    best = None
    for nm, (fn, alphas) in METHODS.items():
        for a in alphas:
            cvs, nr = [], []
            for seed in SEEDS:
                rng = np.random.default_rng(seed)
                fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
                oof = np.zeros(len(yi))
                for k in range(5):
                    trm, tem = fold != k, fold == k
                    fl, _ = orient(X[trm], yi[trm])
                    Xa, Xb = apply_flip(X[trm], fl), apply_flip(X[tem], fl)
                    idx = fn(Xa, ytr[trm], a, rng)
                    nr.append(len(idx))
                    w, b = relaxed(Xa, yi[trm], idx)
                    oof[tem] = (Xb[:, idx] @ w + b) if w is not None else 0.0
                cvs.append(G.auc(yi, oof))
            print(f"  {nm:<16}{a:>8.4f}{np.mean(cvs):>11.4f}{max(cvs)-min(cvs):>9.4f}"
                  f"{int(np.mean(nr)):>7}", flush=True)
            if best is None or np.mean(cvs) > best[2]:
                best = (nm, a, float(np.mean(cvs)), int(np.mean(nr)))
    print(f"\n  CV winner: {best[0]} at alpha={best[1]} — CV {best[2]:.4f} with ~{best[3]} statements")
    json.dump({"method": best[0], "alpha": best[1], "cv": best[2], "n_rules": best[3]},
              open(os.path.expanduser("~/.artamatch-dev/v31_best.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
