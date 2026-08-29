"""v22_nnls.py — orient every statement toward HAPPY first, then fit all of them with NNLS.

THE PROBLEM THIS FIXES. The whole pipeline is non-negative: the Lasso selects with positive=True and
`fit_nonneg` bounds every weight at zero and below, deliberately, so that "no member can be used
backwards". The cost of that was never measured. It is large: of 5,771 pair-only statements, 2,819 (49%)
point AWAY from happy, and 199 of those sit more than two standard errors from the base rate. A
non-negative fit cannot give them a weight, so half the doctrine — including the strongest single
signals in the bank, like Neptune-Pluto in Taurus at z = -8.4 — was silently unusable.

THE FIX. A statement and its negation are the same doctrine. "Nadi dosha is present" and "nadi dosha is
absent" are one fact stated two ways, and only one of them can carry a non-negative weight. So every
statement is oriented toward happy before fitting: where firing predicts unhappy, the complement is used
instead and the name becomes NOT(...). Nothing is discarded and nothing is used backwards.

THE LEAK THIS AVOIDS. Orientation reads the label, so doing it once on the whole training set would leak
into cross-validation. Direction is therefore computed INSIDE each fold, on that fold's training rows
only, and the held-out rows are oriented with those flips. The final model orients on all training rows
and applies the same flips to the test set.

Then NNLS over every oriented statement at once — no Lasso pre-selection. Non-negativity is the only
constraint, and it produces a sparse solution on its own.

Usage: v22_nnls.py <corpus_dir> <out_model.json>
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
import v21_traditions as V21
import v23_traditions as V23
import v26_traditions as V26
import v27_traditions as V27
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.artamatch-dev/quality_good")
OUT = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/.artamatch-dev/quality_v22.json")
FLOOR = int(os.environ.get("AQ_FLOOR_N", "40"))
WITH_V23 = os.environ.get("AQ_V23", "1") == "1"   # the marriage-specific traditions
WITH_V26 = os.environ.get("AQ_V26", "1") == "1"   # the lagna and compatibility systems
WITH_V27 = os.environ.get("AQ_V27", "1") == "1"   # the deepening of the strongest families


def build(df, Z, split):
    parts, names = [], []
    for fn in (lambda d, s: V6.bank(d, Z, s), lambda d, s: V7.additions(d, Z, s),
               lambda d, s: V8.last_singles(d, Z, s)):
        a, nm = fn(df, split); parts.append(a); names += nm
    ex = set(names)
    a, nm = V13.new_singles(df, Z, split, ex); parts.append(a); names += nm; ex |= set(nm)
    a, nm = V21.build(df, Z, split, ex, min_support=1)
    parts.append(a); names += nm; ex |= set(nm)
    if WITH_V23:
        a, nm = V23.build(df, Z, split, ex, min_support=1)
        parts.append(a); names += nm; ex |= set(nm)
    if WITH_V26:
        a, nm = V26.build(df, Z, split, ex, min_support=1)
        parts.append(a); names += nm; ex |= set(nm)
    if WITH_V27:
        a, nm = V27.build(df, Z, split, ex, min_support=1)
        parts.append(a); names += nm
    return np.column_stack(parts).astype(np.float32), names


def orient(Xtr, ytr):
    """direction of each statement on THESE rows only; returns a +1/-1 flip vector"""
    f = Xtr > 0
    base = ytr.mean()
    n1 = f.sum(0)
    s1 = (f * ytr[:, None]).sum(0)
    p1 = np.where(n1 > 0, s1 / np.maximum(n1, 1), base)
    n0 = len(ytr) - n1
    p0 = np.where(n0 > 0, (ytr.sum() - s1) / np.maximum(n0, 1), base)
    return np.where(p1 >= p0, 1.0, -1.0).astype(np.float32), p1 - p0


def apply_flip(X, flip):
    """a flipped statement becomes its complement: 1 - x"""
    out = X.copy()
    neg = flip < 0
    out[:, neg] = 1.0 - out[:, neg]
    return out


def nnls_fit(X, y):
    from scipy.optimize import nnls
    A = np.column_stack([X, np.ones(len(X), np.float32)]).astype(np.float64)
    w, _ = nnls(A, y.astype(np.float64), maxiter=max(3 * A.shape[1], 3000))
    return w[:-1].astype(np.float32), float(w[-1])


def main():
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
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
    print(f"  {os.path.basename(D)}: train {len(tr):,} ({yi.mean():.1%} good) · test {len(te):,}")
    print(f"  bank {X.shape[1]:,} pair-only doctrine statements"
          f"{'  (incl. the marriage-specific traditions)' if WITH_V23 else ''}\n", flush=True)

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

    cvs = []
    for seed in (7, 23, 101):
        fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
        oof = np.zeros(len(yi))
        for k in range(5):
            trm, tem = fold != k, fold == k
            fl, _ = orient(X[trm], yi[trm])            # direction from THIS fold's train rows only
            Xa = apply_flip(X[trm], fl); Xb = apply_flip(X[tem], fl)
            w, b = nnls_fit(Xa, yi[trm])
            oof[tem] = Xb @ w + b
        cvs.append(G.auc(yi, oof))
        print(f"    fold seed {seed:>3}: CV {cvs[-1]:.4f}", flush=True)
    cv = float(np.mean(cvs))
    print(f"  CV (mean of 3 seeds): {cv:.4f}  (spread {max(cvs)-min(cvs):.4f})\n")

    fl, delta = orient(X, yi)
    Xa, Xta = apply_flip(X, fl), apply_flip(Xt, fl)
    w, b = nnls_fit(Xa, yi)
    nz = np.where(w > 0)[0]
    z = Xta @ w + b
    auc = G.auc(yte, z)
    bm = {}
    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    if os.path.exists(bp):
        bm = json.load(open(bp))
    se = bm.get("auc_se", float("nan"))
    flipped = int((fl < 0).sum())
    print(f"  oriented toward happy: {flipped:,} of {len(names):,} statements used as their NEGATION")
    print(f"  NNLS keeps {len(nz):,} of {len(names):,} statements with a positive weight")
    print(f"\n  TEST AUC (read once): {auc:.4f}")
    base = bm.get('age_gap_auc', float('nan'))
    print(f"    chance 0.5000 · age-gap baseline {base:.4f} · SE {se:.4f}")
    print(f"    above chance        {auc - 0.5:+.4f} = {(auc - 0.5) / se:+.2f} SE")
    print(f"    over the age gap    {auc - base:+.4f} = {(auc - base) / se:+.2f} SE")
    wt = {}
    for i in nz:
        nm = names[i] if fl[i] > 0 else f"NOT({names[i]})"
        wt[nm] = float(w[i])
    for k_, v in sorted(wt.items(), key=lambda kv: -kv[1])[:22]:
        print(f"    {k_[:76]:<78} +{v:.4f}")
    json.dump({"model": "ArtaMatch quality — all statements oriented toward happy, NNLS",
               "cv_auc": round(cv, 4), "cv_seeds": [round(c, 4) for c in cvs],
               "test_auc": round(float(auc), 4),
               "intercept": float(b), "n_bank": int(len(names)),
               "n_flipped": flipped, "n_surviving": len(nz),
               "benchmark": bm, "weights": wt}, open(OUT, "w"), indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
