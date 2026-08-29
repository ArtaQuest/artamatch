"""v21_fit.py — the maximum-AUC explainable linear model, over every tradition we can name.

Two changes from the earlier fits, both of which the audit demanded:

  1. THE BANK grows by the traditions that were missing — numerology, Rudhyar's moon phases, the
     Chinese animal relations, the Navamsa D9, all eight kootas plus the Guna Milan total, the Mayan
     Tzolkin, and the 5th/7th/9th harmonic, draconic and antiscia charts (v21_traditions.py).

  2. THE SUPPORT FLOOR drops from 2% to 0.5% of the corpus. At 2% a twelve-by-twelve pair table is
     structurally excluded — its cells average n/144 rows — so numerology, the D9 and the yoni pairs
     could never be selected no matter what they predicted. That floor, not the doctrine, is why the
     per-tradition fit reported "numerology: 0 statements". A floor still exists (40 couples) to keep
     a rule from resting on a handful of marriages, and the alpha sweep does the rest.

Unchanged and non-negotiable: every statement is a named tradition, every statement uses BOTH dates,
only the weighting is fitted, folds are grouped by marriage-graph component, the alpha is declared by
cross-validation, and the test set is read ONCE.

Usage: v21_fit.py <corpus_dir> <out_model.json>
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

D = os.path.expanduser(sys.argv[1])
OUT = os.path.expanduser(sys.argv[2])
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))
ALPHAS = tuple(float(x) for x in os.environ.get("AQ_ALPHAS", "1e-4,2e-4,5e-4,1e-3,2e-3,4e-3,8e-3").split(","))


def main():
    from sklearn.linear_model import Lasso, LogisticRegression
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    ytr = yi.astype(float)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)

    parts, partst, names = [], [], []
    for tag, fn in (("v6", lambda d, s: V6.bank(d, Z, s)),
                    ("v7", lambda d, s: V7.additions(d, Z, s)),
                    ("v8", lambda d, s: V8.last_singles(d, Z, s))):
        a, nm = fn(tr, "train"); b, _ = fn(te, "test")
        parts.append(a); partst.append(b); names += nm
    ex = set(names)
    a, nm = V13.new_singles(tr, Z, "train", ex); b, _ = V13.new_singles(te, Z, "test", ex)
    parts.append(a); partst.append(b); names += nm
    ex |= set(nm)
    a, nm = V21.build(tr, Z, "train", ex, min_support=FLOOR)
    b, _ = V21.build(te, Z, "test", ex, min_support=1)
    # the test build must produce the SAME columns in the SAME order, so rebuild it by name
    b2, nm2 = V21.build(te, Z, "test", ex, min_support=1)
    idx = {k: i for i, k in enumerate(nm2)}
    b = np.column_stack([b2[:, idx[k]] if k in idx else np.zeros(len(te), np.float32) for k in nm])
    parts.append(a); partst.append(b); names += nm
    X = np.column_stack(parts).astype(np.float32)
    Xt = np.column_stack(partst).astype(np.float32)
    del parts, partst

    keep = np.array([clause_ok(n) for n in names]) & (X.sum(0) >= FLOOR) \
        & np.array([side(n) == "AB" for n in names])
    X, Xt = X[:, keep], Xt[:, keep]
    names = [n for n, k in zip(names, keep) if k]
    print(f"  {os.path.basename(D)}: train {len(tr):,} ({yi.mean():.1%} good) · test {len(te):,}")
    print(f"  bank {X.shape[1]:,} pair-only doctrine statements firing in >= {FLOOR} couples", flush=True)

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
    fold = np.random.default_rng(7).integers(0, 5, gid.max() + 1)[gid]

    best = None
    for alpha in ALPHAS:
        oof = np.full(len(yi), np.nan); nz = []
        for k in range(5):
            m = Lasso(alpha=alpha, positive=True, max_iter=8000).fit(X[fold != k], ytr[fold != k])
            surv = np.where(m.coef_ > 0)[0]; nz.append(len(surv))
            if len(surv) >= 2:
                w, b0 = G.fit_nonneg(X[fold != k][:, surv], yi[fold != k],
                                     np.ones(int((fold != k).sum())))
                oof[fold == k] = X[fold == k][:, surv] @ w + b0
            else:
                oof[fold == k] = 0.0
        a_cv = G.auc(yi, oof)
        print(f"    alpha={alpha:<7} CV {a_cv:.4f} · rules ~{int(np.mean(nz))}", flush=True)
        if best is None or a_cv > best[1]:
            best = (alpha, a_cv)
    alpha, cv = best
    print(f"\n  CV winner: alpha={alpha} (CV {cv:.4f})")

    m = Lasso(alpha=alpha, positive=True, max_iter=20000).fit(X, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(X[:, surv], yi, np.ones(len(yi)))
    zt = Xt[:, surv] @ w + b0
    auc = G.auc(yte, zt)
    weights = {names[i]: float(v) for i, v in zip(surv, w) if v > 0}

    dec = lambda d: np.column_stack([pd.to_numeric(d.dob_a.str[:4]) // 10,
                                     pd.to_numeric(d.dob_b.str[:4]) // 10]).astype(float)
    era = G.auc(yte, LogisticRegression(max_iter=2000).fit(dec(tr), yi).predict_proba(dec(te))[:, 1])
    bm = {}
    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    if os.path.exists(bp):
        bm = json.load(open(bp))
    se = bm.get("auc_se", float("nan"))
    print(f"\n  {len(weights)} surviving doctrine rules · TEST AUC (read once): {auc:.4f}")
    print(f"    chance 0.5000 · age gap {bm.get('age_gap_auc', float('nan')):.4f} · "
          f"birth-decade control {era:.4f} · SE {se:.4f}")
    print(f"    above chance     {auc - 0.5:+.4f} = {(auc - 0.5) / se:+.2f} SE")
    print(f"    over the era ctrl {auc - era:+.4f} = {(auc - era) / se:+.2f} SE")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:25]:
        print(f"    {k_[:76]:<78} +{v:.4f}")
    json.dump({"model": "ArtaMatch quality, all traditions, pair-only doctrine",
               "alpha": alpha, "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4),
               "era_control_auc": round(float(era), 4), "floor": FLOOR,
               "intercept": float(b0), "n_bank": int(X.shape[1]), "n_surviving": len(weights),
               "benchmark": bm, "weights": weights}, open(OUT, "w"), indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
