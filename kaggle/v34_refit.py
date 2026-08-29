"""v34_refit.py — the SECOND stage nobody varied: how the selected statements are re-weighted.

Every fit in this project selects with a non-negative Lasso and then re-weights the survivors with
`fit_nonneg`, a non-negative logistic carrying a fixed L2 of 1e-3. That second stage has never been
varied, and it is doing real work: the audit's own logistic on the selected statements scored above the
pipeline that produced them, which is a hint that the refit is leaving something behind.

Five refits are compared on identical folds, with selection held fixed at the CV-winning Lasso:

  nonneg          the incumbent: non-negative logistic, L2 = 1e-3
  nonneg L2 tuned same, with the ridge term swept — it was never chosen, only inherited
  logistic        plain logistic, unconstrained sign. Every statement is already oriented toward happy,
                  so a negative weight here means the statement is being used to CANCEL another, which
                  is worth knowing about rather than forbidding by construction.
  logistic + L2   the same, regularised
  equal weights   no fitting at all: every selected statement counts one. If this matches the others,
                  the weights were never carrying information and only the SELECTION was.

That last one is the honest control, and the one most likely to be uncomfortable.
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
FLOOR = 40
ALPHA = float(os.environ.get("AQ_ALPHA", "0.007"))
SEEDS = (7, 23, 101)


def main():
    from sklearn.linear_model import Lasso, LogisticRegression
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
    print(f"  bank {X.shape[1]:,} · selection fixed at Lasso alpha={ALPHA}\n", flush=True)

    def refit_nonneg(Xa, y, lam):
        return ("nn", G.fit_nonneg(Xa, y, np.ones(len(y)), lam=lam))

    REFITS = {
        "nonneg L2=1e-3 (incumbent)": lambda Xa, y: refit_nonneg(Xa, y, 1e-3),
        "nonneg L2=1e-4":             lambda Xa, y: refit_nonneg(Xa, y, 1e-4),
        "nonneg L2=1e-2":             lambda Xa, y: refit_nonneg(Xa, y, 1e-2),
        "nonneg L2=1e-1":             lambda Xa, y: refit_nonneg(Xa, y, 1e-1),
        "logistic (signed)":          lambda Xa, y: ("lr", LogisticRegression(max_iter=3000, C=1e6).fit(Xa, y)),
        "logistic C=1":               lambda Xa, y: ("lr", LogisticRegression(max_iter=3000, C=1.0).fit(Xa, y)),
        "logistic C=0.1":             lambda Xa, y: ("lr", LogisticRegression(max_iter=3000, C=0.1).fit(Xa, y)),
        "equal weights (control)":    lambda Xa, y: ("eq", None),
    }
    print(f"  {'refit':<28}{'CV(mean3)':>11}{'spread':>9}")
    print("  " + "-" * 48)
    out = {}
    for nm, fn in REFITS.items():
        cvs = []
        for seed in SEEDS:
            fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
            oof = np.zeros(len(yi))
            for f in range(5):
                trm, tem = fold != f, fold == f
                fl, _ = orient(X[trm], yi[trm])
                Xa, Xb = apply_flip(X[trm], fl), apply_flip(X[tem], fl)
                s = np.where(Lasso(alpha=ALPHA, positive=True, max_iter=9000)
                             .fit(Xa, ytr[trm]).coef_ > 0)[0]
                if len(s) < 2:
                    continue
                kind, mdl = fn(Xa[:, s], yi[trm])
                if kind == "nn":
                    w, b = mdl; oof[tem] = Xb[:, s] @ w + b
                elif kind == "lr":
                    oof[tem] = mdl.decision_function(Xb[:, s])
                else:
                    oof[tem] = Xb[:, s].sum(1)
            cvs.append(G.auc(yi, oof))
        out[nm] = float(np.mean(cvs))
        print(f"  {nm:<28}{np.mean(cvs):>11.4f}{max(cvs)-min(cvs):>9.4f}", flush=True)
    b = max(out, key=out.get)
    print(f"\n  best refit: {b} — CV {out[b]:.4f}")
    inc = out["nonneg L2=1e-3 (incumbent)"]
    print(f"  against the incumbent: {out[b]-inc:+.4f}")
    eq = out["equal weights (control)"]
    print(f"  fitting the weights buys {inc-eq:+.4f} over counting the statements equally")
    json.dump(out, open(os.path.expanduser("~/.artamatch-dev/v34_refits.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
