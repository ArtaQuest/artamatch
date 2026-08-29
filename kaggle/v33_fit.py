"""v33_fit.py — the sparse doctrine bank AND the shrunk compatibility tables, fitted together.

Two kinds of statement, both doctrine:
  · the binary bank — "both born in the Disseminating phase of Neptune-Pluto" — a condition that either
    holds or does not;
  · the shrunk tables — "the Chinese animal table puts this pairing above average" — a whole almanac
    table read as one number, its cells borrowing strength from their own rows and columns.

The second exists because a 12x12 table encoded as 144 binary columns is mostly noise, and that is what
forced a support floor high enough to exclude numerology entirely. A shrunk table uses every couple in
the corpus and costs ONE parameter.

Both the orientation of the binary bank and the table encoders read the label, so both are fitted inside
each fold, on that fold's training rows alone. The test set is read once.

Usage: v33_fit.py <corpus_dir> <out_model.json>
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
from v32_tables import categories, TableEncoder

D = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev/quality_good")
OUT = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/.artamatch-dev/quality_v33.json")
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))
ALPHAS = tuple(float(x) for x in os.environ.get("AQ_ALPHAS", "0.004,0.006,0.008,0.010").split(","))
KS = tuple(float(x) for x in os.environ.get("AQ_K", "10,25,60").split(","))
SEEDS = (7, 23, 101)


def groups(ids):
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]


def main():
    from sklearn.linear_model import Lasso
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    ytr = yi.astype(float)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X, names = build(tr, Z, "train")
    Xt, nt = build(te, Z, "test")
    pos = {k: i for i, k in enumerate(nt)}
    Xt = np.column_stack([Xt[:, pos[k]] if k in pos else np.zeros(len(te), np.float32) for k in names])
    keep = np.array([clause_ok(n) for n in names]) & (X.sum(0) >= FLOOR) \
        & np.array([side(n) == "AB" for n in names])
    X, Xt = X[:, keep], Xt[:, keep]
    names = [n for n, k in zip(names, keep) if k]
    cat_tr = categories(tr, Z, "train"); cat_te = categories(te, Z, "test")
    gid = groups(ids)
    print(f"  bank {X.shape[1]:,} binary statements + {len(cat_tr)} compatibility tables")
    print(f"  tables: {', '.join(cat_tr)}\n", flush=True)

    best = None
    print(f"  {'k':>5}{'alpha':>8}{'CV(mean3)':>11}{'spread':>9}{'rules':>7}{'tables kept':>13}")
    print("  " + "-" * 55)
    for k in KS:
        for a in ALPHAS:
            cvs, nr, ntb = [], [], []
            for seed in SEEDS:
                fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
                oof = np.zeros(len(yi))
                for f in range(5):
                    trm, tem = fold != f, fold == f
                    fl, _ = orient(X[trm], yi[trm])
                    enc = TableEncoder(k).fit({n_: (v[0][trm], v[1][trm], v[2])
                                               for n_, v in cat_tr.items()}, yi[trm])
                    Ta = enc.transform({n_: (v[0][trm], v[1][trm], v[2]) for n_, v in cat_tr.items()})
                    Tb = enc.transform({n_: (v[0][tem], v[1][tem], v[2]) for n_, v in cat_tr.items()})
                    Xa = np.column_stack([apply_flip(X[trm], fl), Ta])
                    Xb = np.column_stack([apply_flip(X[tem], fl), Tb])
                    m = Lasso(alpha=a, positive=True, max_iter=9000).fit(Xa, ytr[trm])
                    s = np.where(m.coef_ > 0)[0]
                    nr.append(int((s < X.shape[1]).sum())); ntb.append(int((s >= X.shape[1]).sum()))
                    if len(s) >= 2:
                        w, b = G.fit_nonneg(Xa[:, s], yi[trm], np.ones(int(trm.sum())))
                        oof[tem] = Xb[:, s] @ w + b
                cvs.append(G.auc(yi, oof))
            print(f"  {k:>5.0f}{a:>8.4f}{np.mean(cvs):>11.4f}{max(cvs)-min(cvs):>9.4f}"
                  f"{int(np.mean(nr)):>7}{int(np.mean(ntb)):>13}", flush=True)
            if best is None or np.mean(cvs) > best[2]:
                best = (k, a, float(np.mean(cvs)))
    k, a, cv = best
    print(f"\n  CV winner: k={k:.0f}, alpha={a} — CV {cv:.4f}")

    fl, _ = orient(X, yi)
    enc = TableEncoder(k).fit(cat_tr, yi)
    Xa = np.column_stack([apply_flip(X, fl), enc.transform(cat_tr)])
    Xb = np.column_stack([apply_flip(Xt, fl), enc.transform(cat_te)])
    allnames = names + enc.names
    m = Lasso(alpha=a, positive=True, max_iter=20000).fit(Xa, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(Xa[:, surv], yi, np.ones(len(yi)))
    auc = G.auc(yte, Xb[:, surv] @ w + b0)
    bm = json.load(open(f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"))
    se, base = bm["auc_se"], bm["age_gap_auc"]
    wt = {}
    for i, v in zip(surv, w):
        nm = allnames[i]
        if i < len(names) and fl[i] < 0:
            nm = f"NOT({nm})"
        wt[nm] = float(v)
    print(f"\n  {len(wt)} statements ({sum(1 for x in wt if x.startswith('table['))} of them whole tables)")
    print(f"  TEST AUC (read once): {auc:.4f}")
    print(f"    chance 0.5000 · age-gap baseline {base:.4f} · SE {se:.4f}")
    print(f"    above chance      {auc-0.5:+.4f} = {(auc-0.5)/se:+.2f} SE")
    print(f"    over the age gap  {auc-base:+.4f} = {(auc-base)/se:+.2f} SE")
    for kk, vv in sorted(wt.items(), key=lambda t: -t[1])[:20]:
        print(f"    {kk[:74]:<76} +{vv:.4f}")
    json.dump({"model": "ArtaMatch quality — binary doctrine + shrunk compatibility tables",
               "alpha": a, "table_k": k, "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4),
               "intercept": float(b0), "n_bank": int(len(allnames)), "n_surviving": len(wt),
               "benchmark": bm, "weights": wt,
               "tables": {n_: enc.tab[n_].tolist() for n_ in enc.tab}},
              open(OUT, "w"), indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
