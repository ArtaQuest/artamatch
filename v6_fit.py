"""
v6_fit.py — NON-NEGATIVE SPARSE regression over every doctrine indicator (operator 2026-08-25).

The model class is exactly what was asked: sklearn Lasso with positive=True — non-negative regression with L1
sparsity — over thousands of 0/1 doctrine statements. A weight can only ADD risk, so the fitted model reads as
a list of RISK RULES: statements history charges a premium for, everything else neutral. Alpha is tuned by
marriage-component group-CV on AUC; the test half is read once for the winner.
"""
import json, os, sys
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, explain_gam as EG
D = os.path.expanduser("~/.artamatch-dev/remar_sh")
SIGNS = EG.SIGNS; BRANCH = EG.BRANCH; STEMS = EG.STEMS


def extra_pairs(df, Z, half):
    """The pair matrices that take the bank into the thousands — every cell a tradition-table statement."""
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    im = bodies.index("moon")
    blocks, names = [], []
    NAK = 360.0 / 27.0
    na = np.floor((A[:, im] % 360) / NAK); nb = np.floor((B[:, im] % 360) / NAK)
    pair = np.where(np.isfinite(na) & np.isfinite(nb), na * 27 + nb, np.nan)
    M, nm = EG.onehot(pair, 729, "nakpair", [f"{i}x{j}" for i in range(27) for j in range(27)])
    blocks.append(M); names += nm
    import importlib.util
    _dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
    dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    for nm_, j1, j2, k in (("branchpair", ja, jb, 12), ("stempair", ja, jb, 10)):
        sa = np.where(np.isfinite(j1), (np.nan_to_num(j1) + 49) % 60, np.nan)
        sb = np.where(np.isfinite(j2), (np.nan_to_num(j2) + 49) % 60, np.nan)
        va, vb = sa % k, sb % k
        pr = np.where(np.isfinite(va) & np.isfinite(vb), va * k + vb, np.nan)
        lab = BRANCH if k == 12 else STEMS
        M, nmx = EG.onehot(pr, k * k, nm_, [f"{lab[i]}x{lab[j]}" for i in range(k) for j in range(k)])
        blocks.append(M); names += nmx
    return np.column_stack(blocks).astype(np.float32), names


def bank(df, Z, half):
    X1, n1 = EG.build(df, Z, half)                       # v1+v2: placements, davison, cycles, contacts, ...
    keep = [i for i, n in enumerate(n1) if not n.startswith("verdict:")]   # indicators only, ranks out
    X2, n2 = extra_pairs(df, Z, half)
    return np.column_stack([X1[:, keep], X2]), [n1[i] for i in keep] + n2


def main():
    from sklearn.linear_model import Lasso
    tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv"); ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(float)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    Xtr, names = bank(tr, Z, "train"); Xte, _ = bank(te, Z, "test")
    print(f"  bank: {Xtr.shape[1]:,} doctrine indicators · train {len(tr):,} · test {len(te):,}", flush=True)

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
    for alpha in (3e-5, 1e-4, 3e-4, 1e-3, 3e-3):
        oof = np.full(len(ytr), np.nan)
        nz = []
        for k in range(5):
            m = Lasso(alpha=alpha, positive=True, max_iter=6000)
            m.fit(Xtr[fold != k], ytr[fold != k])
            oof[fold == k] = Xtr[fold == k] @ m.coef_ + m.intercept_
            nz.append(int((m.coef_ > 0).sum()))
        a = G.auc(ytr.astype(int), oof)
        print(f"    alpha={alpha:<8} group-CV AUC {a:.4f} · surviving weights/fold ~{int(np.mean(nz))}", flush=True)
        if best is None or a > best[1]:
            best = (alpha, a)
    alpha = best[0]
    m = Lasso(alpha=alpha, positive=True, max_iter=10000)
    m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    zt = Xte @ m.coef_ + m.intercept_
    auc = G.auc(yte, zt)
    print(f"\n  NON-NEGATIVE SPARSE MODEL · alpha={alpha} · {len(surv)} surviving rules of {Xtr.shape[1]:,}")
    print(f"  TEST AUC (read once): {auc:.4f}   (signed dense GAM was 0.7707)")
    o = surv[np.argsort(-m.coef_[surv])]
    print("\n  the heaviest surviving risk rules:")
    for i in o[:18]:
        print(f"    {names[i]:<44} +{m.coef_[i]:.4f}")
    # calibration for the product: score deciles -> historical divorce share (train only)
    ztr = Xtr @ m.coef_ + m.intercept_
    qs = np.quantile(ztr, np.linspace(0, 1, 11))
    qs[0], qs[-1] = -1e9, 1e9
    calib = []
    for k in range(10):
        s = (ztr >= qs[k]) & (ztr < qs[k + 1])
        calib.append({"lo": float(qs[k]), "hi": float(qs[k + 1]), "share": float(ytr[s].mean()), "n": int(s.sum())})
    json.dump({"model": "ArtaMatch v6 — non-negative sparse risk rules", "alpha": alpha,
               "cv_auc": round(best[1], 4), "test_auc": round(float(auc), 4),
               "intercept": float(m.intercept_), "n_bank": int(Xtr.shape[1]), "n_surviving": int(len(surv)),
               "weights": {names[i]: round(float(m.coef_[i]), 6) for i in o},
               "calibration_deciles": calib, "train_score_range": [float(ztr.min()), float(ztr.max())]},
              open(os.path.expanduser("~/.artamatch-dev/v6_model.json"), "w"), indent=1)
    print(f"\n  saved v6_model.json · {len(surv)} rules deploy")


if __name__ == "__main__":
    main()
