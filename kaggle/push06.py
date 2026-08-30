"""push06.py — the last stretch to 0.60, using variance reduction rather than penalty-hunting.

The alpha curve peaks at 0.5984 but its seed-to-seed spread is 0.005, which is wider than the gap to
0.60. Reading a maximum off a curve that noisy and calling the maximum the score is fitting the
cross-validation itself, so this does not go looking for a better alpha. It reduces the variance of
the estimate instead, three ways that are each legitimate:

  1  FIVE SEEDS on a coarse grid, so the number being compared is stabler than a three-seed one.
  2  ALPHA ENSEMBLE — inside each fold, fit at several penalties and average the rank-normalised
     predictions. A Lasso's choice among correlated statements is unstable by construction; averaging
     over neighbouring penalties keeps what all of them agree on.
  3  BAGGING — inside each fold, refit on bootstrap resamples of the training rows and average. Same
     idea against a different source of instability.

Both 2 and 3 average PREDICTIONS made without seeing the held-out rows, so neither leaks. The bank is
built once and reused across all three, because building it is the expensive part.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v37_fit import groups
from scipy.stats import rankdata

D = os.path.expanduser(os.environ.get("AQ_D", "~/.artamatch-dev/quality_good"))
OUT = os.path.expanduser("~/.artamatch-dev/push06.json")


def bank(tr, Z):
    from v22_nnls import build as bb
    from v12_fit import side
    from denylist import clause_ok
    X, n = bb(tr, Z, "train")
    keep = np.array([clause_ok(k) and side(k) == "AB" for k in n]) & (X.sum(0) >= 40)
    return X[:, keep], [k for k, kk in zip(n, keep) if kk]


def one(A, ytr, B, alpha, rng=None):
    """one Lasso + relaxed non-negative refit; rng resamples the rows for bagging"""
    from sklearn.linear_model import Lasso
    if rng is not None:
        idx = rng.integers(0, len(A), len(A))
        A_, y_ = A[idx], ytr[idx]
    else:
        A_, y_ = A, ytr
    m = Lasso(alpha=alpha, positive=True, max_iter=8000).fit(A_, y_)
    s = np.where(m.coef_ > 0)[0]
    if len(s) < 2:
        return np.zeros(len(B))
    w, b = G.fit_nonneg(A_[:, s], y_, np.ones(len(A_)))
    return B[:, s] @ w + b


def run(Xb, y, gid, seeds, mode, alphas, nbag=0):
    from v22_nnls import orient, apply_flip
    accs = []
    for seed in seeds:
        fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
        oof = np.zeros(len(y))
        for k in range(5):
            trm, tem = fold != k, fold == k
            flip, _ = orient(Xb[trm], y[trm].astype(float))
            A, B = apply_flip(Xb[trm], flip), apply_flip(Xb[tem], flip)
            yt = y[trm].astype(float)
            preds = []
            if mode == "bag":
                rng = np.random.default_rng(1000 + seed)
                preds = [one(A, yt, B, alphas[0], rng) for _ in range(nbag)]
            else:
                preds = [one(A, yt, B, a) for a in alphas]
            R = np.column_stack([rankdata(p) / len(p) for p in preds])
            oof[tem] = R.mean(1)
        accs.append(G.auc(y, oof))
    return float(np.mean(accs)), accs


def main():
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    y = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    gid = groups(ids)
    Xb, nb = bank(tr, Z)
    print(f"  {len(tr):,} couples · bank {Xb.shape[1]:,} statements (no interaction gate)\n")
    res = {}

    print("  1. five seeds, one penalty at a time")
    for a in (0.007, 0.0075, 0.008):
        m, accs = run(Xb, y, gid, (7, 23, 101, 5, 61), "single", [a])
        res[f"single_{a}"] = m
        print(f"     alpha {a:<8g} CV {m:.4f}   {', '.join(f'{v:.4f}' for v in accs)}")

    print("\n  2. alpha ensemble, five seeds")
    for tag, al in (("0.006-0.009", [0.006, 0.007, 0.0075, 0.008, 0.009]),
                    ("0.007-0.008", [0.007, 0.0075, 0.008])):
        m, accs = run(Xb, y, gid, (7, 23, 101, 5, 61), "ens", al)
        res[f"ens_{tag}"] = m
        print(f"     {tag:<12} CV {m:.4f}   {', '.join(f'{v:.4f}' for v in accs)}")

    print("\n  3. bagged Lasso at 0.0075, five seeds")
    for nbag in (8, 16):
        m, accs = run(Xb, y, gid, (7, 23, 101, 5, 61), "bag", [0.0075], nbag)
        res[f"bag{nbag}"] = m
        print(f"     {nbag} resamples  CV {m:.4f}   {', '.join(f'{v:.4f}' for v in accs)}")

    best = max(res, key=res.get)
    print(f"\n  BEST: {best}  CV {res[best]:.4f}")
    json.dump(res, open(OUT, "w"), indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
