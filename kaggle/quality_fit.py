"""quality_fit.py — the doctrine-only fit, regularised for the size of corpus we actually have.

The first pass reused the alpha grid from the 44,000-row divorce corpora and kept 1,430 rules on 2,496
training rows: cross-validation happily picked a model that had memorised its folds, and the held-out
AUC came back at 0.46 — below chance, the signature of over-parameterisation rather than of an inverse
effect. This fit is built for small n:

  · a support floor: a statement must fire in at least 2% of couples to be a candidate at all
  · an alpha grid two orders of magnitude stronger, swept until the surviving rule count is sane
  · the survivor count printed beside every CV score, so over-parameterisation is visible not implied
  · the pair-only and doctrine-only constraints unchanged
  · ONE test read, for the CV winner only

Usage: quality_fit.py <corpus_dir> <out_model.json>
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser(sys.argv[1])
OUT = os.path.expanduser(sys.argv[2])
ALPHAS = (2e-4, 5e-4, 1e-3, 2e-3, 4e-3, 8e-3)


def main():
    from sklearn.linear_model import Lasso
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(float)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    yi = ytr.astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)

    X6, n6 = V6.bank(tr, Z, "train"); X6t, _ = V6.bank(te, Z, "test")
    XA, nA = V7.additions(tr, Z, "train"); XAt, _ = V7.additions(te, Z, "test")
    XL, nL = V8.last_singles(tr, Z, "train"); XLt, _ = V8.last_singles(te, Z, "test")
    ex1 = set(n6 + nA + nL)
    XN, nN = V13.new_singles(tr, Z, "train", ex1); XNt, _ = V13.new_singles(te, Z, "test", ex1)
    X = np.column_stack([X6, XA, XL, XN]); Xt = np.column_stack([X6t, XAt, XLt, XNt])
    names = n6 + nA + nL + nN
    del X6, XA, XL, XN, X6t, XAt, XLt, XNt

    floor = max(40, int(0.02 * len(tr)))
    keep = np.array([clause_ok(n) for n in names]) & (X.sum(0) >= floor) & (side_ok(names))
    X, Xt = X[:, keep], Xt[:, keep]
    names = [n for n, k in zip(names, keep) if k]
    print(f"  {D.split('/')[-1]}: train {len(tr):,} ({yi.mean():.1%} pos) · test {len(te):,} "
          f"({yte.mean():.1%} pos)")
    print(f"  bank {X.shape[1]:,} both-date doctrine statements firing in >= {floor} couples", flush=True)

    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    gid = pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]
    fold = np.random.default_rng(7).integers(0, 5, gid.max() + 1)[gid]

    best = None
    for alpha in ALPHAS:
        oof = np.full(len(ytr), np.nan)
        nz = []
        for k in range(5):
            m = Lasso(alpha=alpha, positive=True, max_iter=8000)
            m.fit(X[fold != k], ytr[fold != k])
            surv = np.where(m.coef_ > 0)[0]
            nz.append(len(surv))
            if len(surv) >= 2:
                w, b = G.fit_nonneg(X[fold != k][:, surv], yi[fold != k],
                                    np.ones(int((fold != k).sum())))
                oof[fold == k] = X[fold == k][:, surv] @ w + b
            else:
                oof[fold == k] = 0.0
        a_cv = G.auc(yi, oof)
        print(f"    alpha={alpha:<7} CV {a_cv:.4f} · rules ~{int(np.mean(nz))}"
              f"{'  <- fewer rules than rows/10' if np.mean(nz) <= len(tr) / 10 else ''}", flush=True)
        if best is None or a_cv > best[1]:
            best = (alpha, a_cv, int(np.mean(nz)))
    alpha, cv, nrules = best
    print(f"\n  CV winner: alpha={alpha} (CV {cv:.4f}, ~{nrules} rules)")

    m = Lasso(alpha=alpha, positive=True, max_iter=12000)
    m.fit(X, ytr)
    surv = np.where(m.coef_ > 0)[0]
    if len(surv) < 2:
        print("  the sweep kept fewer than two rules — nothing to declare")
        return
    w, b0 = G.fit_nonneg(X[:, surv], yi, np.ones(len(yi)))
    zt = Xt[:, surv] @ w + b0
    weights = {names[i]: float(v) for i, v in zip(surv, w) if v > 0}
    auc = G.auc(yte, zt)
    bm = {}
    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    if os.path.exists(bp):
        bm = json.load(open(bp))
    print(f"\n  {len(weights)} surviving doctrine rules · TEST AUC (read once): {auc:.4f}")
    if bm:
        print(f"    chance 0.5000 · age-gap baseline {bm['age_gap_auc']:.4f} · AUC SE {bm['auc_se']:.4f}")
        d = auc - 0.5
        print(f"    above chance by {d:+.4f} = {d / bm['auc_se']:.2f} standard errors")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:12]:
        print(f"    {k_[:78]:<80} +{v:.4f}")
    json.dump({"model": f"ArtaMatch quality ({os.path.basename(D)}, doctrine-only, small-n regularised)",
               "alpha": alpha, "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4),
               "intercept": float(b0), "n_bank": int(X.shape[1]), "n_surviving": len(weights),
               "benchmark": bm, "weights": weights}, open(OUT, "w"), indent=1)
    np.save(OUT.replace(".json", "_z.npy"), zt)
    print(f"  saved {OUT}")


def side_ok(names):
    """pair-only: a statement about one partner alone may not stand as a rule"""
    return np.array([side(n) == "AB" for n in names])


if __name__ == "__main__":
    main()
