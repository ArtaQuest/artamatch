"""quality_by_tradition.py — score EVERY named tradition separately, on one table.

The pooled fit answers "does the doctrine as a whole predict marriage quality". The standing question
for this project is narrower and more useful: WHICH traditions carry the signal. A tradition that works
should show it on its own bank, measured against the one baseline this project uses: a two-parameter
logistic on the signed difference of the two birth dates.

Each family is fitted alone, with the same small-n regularisation, the same group folds, and the same
pair-only and doctrine-only constraints. Three numbers per family:

  CV        out-of-fold AUC on the training couples, its own bank only
  TEST      one held-out read
  vsBASE    test minus the age-gap baseline — a two-parameter logistic on the signed difference of the
            two birth dates, which is the ONE comparator this project measures against, because it uses
            nothing but the same two dates the astrology uses

Usage: quality_by_tradition.py <corpus_dir>
"""
import json, os, re, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser(sys.argv[1])
ALPHAS = (2e-4, 5e-4, 1e-3, 2e-3, 4e-3, 8e-3)

FAMILIES = [
    ("Synastry aspects (his body to hers)", r"^(his|her)_\w+_(conj|opp|trine|square|sext|semisext|quinc)_"),
    ("Synastry houses (his body in her house)", r"_house=\d+$"),
    ("Composite chart (midpoint of the two)", r"^comp_"),
    ("Davison chart (chart of the midpoint in time)", r"^dav_"),
    ("Outer-planet cycles (Neptune-Pluto etc)", r"^cycle"),
    ("Vedic: nakshatra, tithi, yoga", r"(nakshatra|tithi|yoga|rajju|vashya|gana|graha_maitri|bhakoot|nadi)"),
    ("Chinese: nayin element, kua number", r"(nayin|kua)"),
    ("Element / mode / polarity pairings", r"(elempair|modepair|polpair|_pair=|pair=)"),
    ("Decans and sign placements", r"(_decan|_sign)="),
    ("Numerology (life path, name, cycles)", r"(lifepath|numer|destiny|expression|birthnum)"),
]


def main():
    from sklearn.linear_model import Lasso, LogisticRegression
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
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
    keep = np.array([clause_ok(n) for n in names]) & (X.sum(0) >= floor) \
        & np.array([side(n) == "AB" for n in names])
    X, Xt = X[:, keep], Xt[:, keep]
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
    fold = np.random.default_rng(7).integers(0, 5, gid.max() + 1)[gid]

    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    bmj = json.load(open(bp)) if os.path.exists(bp) else {}
    se = bmj.get("auc_se", float("nan"))
    a_base = bmj.get("age_gap_auc", float("nan"))

    print(f"  {os.path.basename(D)} · train {len(tr):,} · test {len(te):,} · "
          f"bank {X.shape[1]:,} · AUC SE {se:.4f}")
    print(f"  reference: chance 0.5000 · age-gap baseline {a_base:.4f}\n")
    print(f"  {'tradition':<44}{'rules':>7}{'CV':>9}{'TEST':>9}{'vsBASE':>9}{'':>4}")
    print("  " + "-" * 80)
    out = []
    for label, pat in FAMILIES:
        rx = re.compile(pat)
        cols = [i for i, n in enumerate(names) if rx.search(n)]
        if len(cols) < 8:
            print(f"  {label:<44}{len(cols):>7}   (too few statements to fit)")
            continue
        Xf, Xft = X[:, cols], Xt[:, cols]
        best = None
        for alpha in ALPHAS:
            oof = np.full(len(yi), np.nan)
            for k in range(5):
                m = Lasso(alpha=alpha, positive=True, max_iter=6000).fit(Xf[fold != k], yi[fold != k])
                s = np.where(m.coef_ > 0)[0]
                if len(s) >= 2:
                    w, b = G.fit_nonneg(Xf[fold != k][:, s], yi[fold != k],
                                        np.ones(int((fold != k).sum())))
                    oof[fold == k] = Xf[fold == k][:, s] @ w + b
                else:
                    oof[fold == k] = 0.0
            a = G.auc(yi, oof)
            if best is None or a > best[1]:
                best = (alpha, a)
        alpha, cv = best
        m = Lasso(alpha=alpha, positive=True, max_iter=9000).fit(Xf, yi)
        s = np.where(m.coef_ > 0)[0]
        if len(s) < 2:
            print(f"  {label:<44}{len(cols):>7}   (nothing survives selection)")
            continue
        w, b0 = G.fit_nonneg(Xf[:, s], yi, np.ones(len(yi)))
        z = Xft[:, s] @ w + b0
        a_test = G.auc(yte, z)
        d = a_test - a_base
        mark = "  <-- beats the baseline" if d / se > 2 else ""
        print(f"  {label:<44}{len(s):>7}{cv:>9.4f}{a_test:>9.4f}{d:>+9.4f}{mark}")
        out.append({"tradition": label, "n_rules": int(len(s)), "cv": round(cv, 4),
                    "test": round(float(a_test), 4), "over_baseline": round(float(d), 4),
                    "over_baseline_se": round(float(d / se), 2)})
    print(f"\n  vsBASE is the tradition's held-out AUC minus the age-gap baseline ({a_base:.4f}).")
    print(f"  Anything under {2*se:.4f} (2 SE) is inside what this test set can resolve.")
    json.dump({"corpus": os.path.basename(D), "age_gap_auc": float(a_base), "auc_se": float(se),
               "families": out}, open(f"{os.path.dirname(D)}/{os.path.basename(D)}_traditions.json", "w"),
              indent=1)


if __name__ == "__main__":
    main()
