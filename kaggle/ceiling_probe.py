"""ceiling_probe.py — is 0.60 reachable on this target at all, and by what?

Four models under identical group folds, everything inside the fold:

  A  boosted trees on PAIR-ONLY astrology  — every cross-chart angle and every composite longitude,
     which is what the doctrine constraint allows. Trees, so it can use interactions a linear model
     cannot.
  B  boosted trees on EVERYTHING astrological, single-side positions included — the doctrine
     constraint dropped, purely to see where the ceiling is.
  C  the birth years alone, boosted — the era confound with no astrology in it at all.
  D  a two-level stack: the era model and the astrology model each tuned, then combined out of fold.

If A cannot reach 0.60 but C can, the target is telling us the score lives in the calendar.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from v37_fit import groups

D = os.path.expanduser(os.environ.get("AQ_D", "~/.artamatch-dev/quality_good"))
SEEDS = (7, 23, 101)
BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "chiron", "mean_lilith"]
ALL = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
       "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(ALL)}


def blocks(tr, Z, split):
    A = np.asarray(Z[f"theta_a_{split}"], float)
    B = np.asarray(Z[f"theta_b_{split}"], float)
    cross, cn = [], []
    for x in BODIES:
        for y in BODIES:
            cross.append(((A[:, BI[x]] - B[:, BI[y]]) % 360.0).astype(np.float32))
            cn.append(f"cross_{x}_{y}")
    comp, mn = [], []
    for b in BODIES:
        raw = ((B[:, BI[b]] - A[:, BI[b]] + 180.0) % 360.0) - 180.0
        comp.append(((A[:, BI[b]] + raw / 2.0) % 360.0).astype(np.float32)); mn.append(f"comp_{b}")
    single, sn = [], []
    for b in BODIES:
        single.append(A[:, BI[b]].astype(np.float32)); sn.append(f"his_{b}")
        single.append(B[:, BI[b]].astype(np.float32)); sn.append(f"her_{b}")
    ya = pd.to_numeric(tr.dob_a.str[:4]).to_numpy(float)
    yb = pd.to_numeric(tr.dob_b.str[:4]).to_numpy(float)
    era = np.column_stack([ya, yb, ya - yb, (ya + yb) / 2]).astype(np.float32)
    return (np.nan_to_num(np.column_stack(cross + comp)), cn + mn,
            np.nan_to_num(np.column_stack(single)), sn, era)


def cv_gbm(X, y, gid, **kw):
    from sklearn.ensemble import HistGradientBoostingClassifier as H
    outs = []
    for seed in SEEDS:
        fold = np.random.default_rng(seed).integers(0, 5, gid.max() + 1)[gid]
        oof = np.zeros(len(y))
        for k in range(5):
            trm, tem = fold != k, fold == k
            m = H(random_state=seed, **kw).fit(X[trm], y[trm])
            oof[tem] = m.predict_proba(X[tem])[:, 1]
        outs.append(G.auc(y, oof))
    return float(np.mean(outs)), outs


def main():
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    y = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    gid = groups(ids)
    Xp, pn, Xs, sn, era = blocks(tr, Z, "train")
    print(f"  {len(tr):,} couples · pair-only block {Xp.shape[1]} · single-side {Xs.shape[1]}\n")
    kw = dict(max_iter=400, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0,
              min_samples_leaf=40, early_stopping=False)
    for lab, X in (("A  pair-only astrology (cross angles + composite), trees", Xp),
                   ("B  + single-side positions, doctrine constraint dropped",
                    np.column_stack([Xp, Xs])),
                   ("C  birth years only, no astrology at all", era),
                   ("D  birth years + all astrology", np.column_stack([Xp, Xs, era]))):
        a, outs = cv_gbm(X, y, gid, **kw)
        print(f"  {lab:<58} CV {a:.4f}  (seeds {', '.join(f'{o:.4f}' for o in outs)})")
        json.dump({"probe": lab, "cv": a}, open(f"/tmp/probe_{lab[0]}.json", "w"))


if __name__ == "__main__":
    main()
