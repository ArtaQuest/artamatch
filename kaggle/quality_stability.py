"""quality_stability.py — is the one target that beat chance actually stable, and what is it reading?

quality_happy came in at 0.5462, 2.5 standard errors above chance, on three doctrine rules. Two things
have to be checked before that can be called a result:

  1. STABILITY — the alpha was chosen by a cross-validation that depends on one random fold assignment.
     Re-run the whole selection under several different fold seeds. If the CV score and the surviving
     rules move around, the model is an artefact of one split. No extra test reads are spent: the test
     set is touched once, by the declared model, and never again.

  2. WHAT IT READS — the three rules are outer-planet phases and a Pluto-Pluto conjunction. Pluto takes
     248 years to circle the zodiac, so "his Pluto conjunct her Pluto" is satisfied by almost any couple
     born within a few decades of each other: it is a statement about ERA, not about the pair. This
     measures exactly that, by asking how well the couple's birth DECADE alone predicts the same target.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev/quality_happy")
ALPHAS = (1e-3, 2e-3, 4e-3, 8e-3, 1.2e-2)


def main():
    from sklearn.linear_model import Lasso, LogisticRegression
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)

    X6, n6 = V6.bank(tr, Z, "train")
    XA, nA = V7.additions(tr, Z, "train")
    XL, nL = V8.last_singles(tr, Z, "train")
    XN, nN = V13.new_singles(tr, Z, "train", set(n6 + nA + nL))
    X = np.column_stack([X6, XA, XL, XN])
    names = n6 + nA + nL + nN
    floor = max(40, int(0.02 * len(tr)))
    keep = (np.array([clause_ok(n) for n in names]) & (X.sum(0) >= floor)
            & np.array([side(n) == "AB" for n in names]))
    X = X[:, keep]
    names = [n for n, k in zip(names, keep) if k]

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

    print(f"  {os.path.basename(D)} · {len(tr):,} train couples · bank {X.shape[1]:,} statements\n")
    print("  1. STABILITY — the same selection under five different fold assignments")
    picks = []
    for seed in (7, 11, 23, 42, 101):
        fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
        best = None
        for alpha in ALPHAS:
            oof = np.full(len(ytr), np.nan)
            for k in range(5):
                m = Lasso(alpha=alpha, positive=True, max_iter=8000)
                m.fit(X[fold != k], ytr[fold != k])
                surv = np.where(m.coef_ > 0)[0]
                if len(surv) >= 2:
                    w, b = G.fit_nonneg(X[fold != k][:, surv], ytr[fold != k],
                                        np.ones(int((fold != k).sum())))
                    oof[fold == k] = X[fold == k][:, surv] @ w + b
                else:
                    oof[fold == k] = 0.0
            a_cv = G.auc(ytr, oof)
            if best is None or a_cv > best[1]:
                best = (alpha, a_cv)
        m = Lasso(alpha=best[0], positive=True, max_iter=12000).fit(X, ytr)
        surv = [names[i] for i in np.where(m.coef_ > 0)[0]]
        picks.append((seed, best[0], best[1], surv))
        print(f"    seed {seed:>3}: alpha={best[0]:<7} CV {best[1]:.4f} · {len(surv)} rules · "
              f"{', '.join(surv[:3])}")
    cvs = [p[2] for p in picks]
    print(f"    CV across seeds: {np.mean(cvs):.4f} +/- {np.std(cvs):.4f}"
          f" (spread {max(cvs) - min(cvs):.4f})")
    common = set(picks[0][3])
    for p in picks[1:]:
        common &= set(p[3])
    print(f"    rules chosen by EVERY seed: {sorted(common) if common else 'none'}")

    print("\n  2. WHAT IT READS — the birth decade alone, on the same split")
    dec_tr = np.column_stack([
        pd.to_numeric(tr.dob_a.str[:4]).to_numpy() // 10,
        pd.to_numeric(tr.dob_b.str[:4]).to_numpy() // 10]).astype(float)
    dec_te = np.column_stack([
        pd.to_numeric(te.dob_a.str[:4]).to_numpy() // 10,
        pd.to_numeric(te.dob_b.str[:4]).to_numpy() // 10]).astype(float)
    lo = LogisticRegression(max_iter=2000).fit(dec_tr, ytr)
    era = G.auc(yte, lo.predict_proba(dec_te)[:, 1])
    print(f"    two birth decades, two parameters: TEST AUC {era:.4f}")
    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    if os.path.exists(bp):
        bm = json.load(open(bp))
        print(f"    for comparison — doctrine model 0.5462 · age gap {bm['age_gap_auc']:.4f} · "
              f"chance 0.5000 · SE {bm['auc_se']:.4f}")


if __name__ == "__main__":
    main()
