"""v37_fit.py — honest cross-validation over continuous doctrine features.

EVERYTHING that touches the label happens INSIDE the fold: standardisation, feature selection, and the
fit. The number this prints is therefore comparable with the 0.5612 the binary pipeline reports, and
NOT with the 0.6283 the audit prints for a logistic on statements that were chosen using all the
training rows — that one has its selection outside the folds and is optimistic by construction.

Folds are over connected components of the marriage graph, so two couples sharing a person are never
split across the boundary.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
import v37_harmonics as V37
import v38_symharm as V38
import v39_composite_harm as V39

D = os.path.expanduser(os.environ.get("AQ_D", "~/.artamatch-dev/quality_good"))
BLOCKS = os.environ.get("AQ_BLOCKS", "harm")           # harm | bank | both
CS = tuple(float(x) for x in os.environ.get("AQ_CS", "0.0003,0.001,0.003,0.01,0.03,0.1").split(","))
SEEDS = (7, 23, 101)
MIN_INTER = float(os.environ.get("AQ_MIN_INTERACTION", "0"))
OUT = os.path.expanduser(os.environ.get("AQ_OUT_JSON", "~/.artamatch-dev/v37.json"))


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


def design(tr, Z, split):
    parts, names = [], []
    if BLOCKS in ("harm", "both"):
        X, nm = V37.build(tr, Z, split)
        parts.append(X); names += nm
    if BLOCKS in ("comp", "harmcomp"):
        X, nm = V39.build(tr, Z, split)
        parts.append(X); names += nm
    if BLOCKS == "harmcomp":
        X, nm = V37.build(tr, Z, split)
        parts.append(X); names += nm
    if BLOCKS in ("sym", "symbank"):
        X, nm = V38.build(tr, Z, split)
        parts.append(X); names += nm
    if BLOCKS == "symbank":
        BLOCKS_BANK = True
    if BLOCKS in ("bank", "both", "symbank"):
        from v22_nnls import build as bank_build
        from v12_fit import side
        from denylist import clause_ok
        Xb, nb = bank_build(tr, Z, split)
        keep = np.array([clause_ok(n) and side(n) == "AB" for n in nb]) & (Xb.sum(0) >= 40)
        if MIN_INTER > 0:
            sc = json.load(open(os.path.expanduser("~/.artamatch-dev/interaction_scores.json")))
            keep &= np.array([min((sc.get(p, 0.0) for p in n.split(" AND ")), default=0.0) >= MIN_INTER
                              for n in nb])
        parts.append(Xb[:, keep]); names += [n for n, k in zip(nb, keep) if k]
    return np.column_stack(parts).astype(np.float32), names


def main():
    from sklearn.linear_model import LogisticRegression
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    y = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X, names = design(tr, Z, "train")
    gid = groups(ids)
    print(f"  {os.path.basename(D)}: {len(tr):,} couples · {X.shape[1]:,} features "
          f"({BLOCKS}) · {y.mean():.1%} good\n")

    best = None
    print(f"     {'C':>9}  {'CV(mean3)':>10}  {'spread':>8}")
    print("  " + "-" * 34)
    for C in CS:
        accs = []
        for seed in SEEDS:
            fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
            oof = np.zeros(len(y))
            for k in range(5):
                trm, tem = fold != k, fold == k
                mu = X[trm].mean(0); sd = X[trm].std(0) + 1e-9      # fitted on the fold only
                lo = LogisticRegression(C=C, max_iter=3000)
                lo.fit((X[trm] - mu) / sd, y[trm])
                oof[tem] = lo.predict_proba((X[tem] - mu) / sd)[:, 1]
            accs.append(G.auc(y, oof))
        a = float(np.mean(accs))
        print(f"     {C:>9.4g}  {a:>10.4f}  {max(accs)-min(accs):>8.4f}")
        if best is None or a > best[1]:
            best = (C, a)
    print(f"\n  BEST: C={best[0]:g}  CV {best[1]:.4f}")
    json.dump({"blocks": BLOCKS, "n_features": int(X.shape[1]), "C": best[0], "cv_auc": best[1],
               "min_interaction": MIN_INTER}, open(OUT, "w"), indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
