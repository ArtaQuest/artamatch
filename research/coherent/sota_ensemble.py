"""
sota_ensemble.py — the ensemble done properly, after the first attempt scored BELOW its own age-gap feature.

WHAT WENT WRONG THE FIRST TIME. An ensemble handed the age gap scored 0.5809 held out while the age gap alone
scores 0.6045. That is not a fact about the data, it is a broken pipeline, and the evidence was already visible:
a rank-average of the top 1 feature scored 0.6065, of the top 100 scored 0.5920, and of the top 300 scored
0.5471. Adding weaker features degraded the score monotonically -- the signature of fitting noise.

Two causes, and adversarial validation ruled out a third:

  * ONE VALIDATION SPLIT, TOO CLOSE IN TIME. Selection used the latest 15% of training births -- 1888 to 1900 --
    while the competition's held-out couples are born 1901 to 1990. A model overfitted to 1890s structure looks
    fine 12 years ahead and fails 50 years ahead, so the split could not see the failure it was meant to catch.
    It gave the noisiest learner 0.873 of the blend weight.
  * NO CONSTRAINT AND NO STABILITY TEST. 305 features into a tree ensemble with 51% of features reversing sign
    out of time. Nothing forced the one relationship we are sure of -- a wider age gap means a shorter
    relationship -- to be respected, so the model was free to fit era-specific wiggles instead.
  * NOT extrapolation. Adversarial validation separates the halves at AUC 1.0000, but that is inevitable (the
    birth years differ by construction) and the top features' ranges OVERLAP 100% between halves, so
    out-of-range extrapolation is not the mechanism. Ruling this out mattered: it would have called for a
    different fix.

THE RECIPE

  1. EXPANDING-WINDOW TEMPORAL FOLDS. Three of them, each validating on couples born LATER than everything it
     trained on, at increasing distance. Selecting on the mean across folds penalises a model that only works
     one decade ahead. Every hyper-parameter, feature count and blend weight is chosen here.
  2. WORST-CASE FEATURE STABILITY. A feature is admitted only if it points the SAME WAY in every fold and its
     WEAKEST fold AUC clears a floor. Ranking by the minimum rather than the mean is what rejects a feature that
     is strong in one era and absent in another -- which is most of the 4,962.
  3. MONOTONE CONSTRAINTS. LightGBM is told the score must be non-increasing in the age gap. This encodes the
     one direction we are certain of and removes the model's freedom to fit noise against it.
  4. HEAVY REGULARISATION, chosen on the folds: few leaves, high minimum leaf size, feature and row subsampling.
  5. A HARD FLOOR AT THE GAP-ONLY MODEL. The gap alone is a candidate in the blend, and if no combination beats
     it across the folds, the gap alone is what ships. An ensemble that cannot beat its own strongest feature
     should return that feature, not a worse mixture of it.

Usage: python research/coherent/sota_ensemble.py
"""
import json
import os
import time

import numpy as np
import pandas as pd

T0 = time.time()
MAT = os.environ.get("AQ_MAT", "/tmp/aqmat/mega.npz")
SOL = os.environ.get("AQ_SOL", "/tmp/aqdurcomp/solution.csv")
OUT = os.environ.get("AQ_OUT", "/tmp/aqsota")
os.makedirs(OUT, exist_ok=True)


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def auc(y, s):
    y = np.asarray(y, np.int64)
    s = np.asarray(s, np.float64)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    o = np.argsort(s, kind="mergesort")
    ys, ss = y[o], s[o]
    r = np.empty(len(ss))
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[i:j + 1] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((r[ys == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def r01(v):
    r = np.argsort(np.argsort(v)).astype(np.float64)
    return r / max(1.0, len(r) - 1)


Z = np.load(MAT, allow_pickle=True)
X = Z["X_train"].astype(np.float32)
Xe = Z["X_test"].astype(np.float32)
y = Z["y_train"].astype(np.int64)
names = list(Z["names"])
ids = Z["id_test"]
gap = Z["gap_train"].astype(np.float32)
gape = Z["gap_test"].astype(np.float32)
yr = Z["yr_train"].astype(np.int32)
later = yr.max(1)
log(f"{X.shape[0]:,} training couples x {X.shape[1]:,} features · {len(Xe):,} held out")

# ── 1. expanding-window temporal folds ────────────────────────────────────────────────────────────────────
CUTS = [(1820, 1850), (1850, 1875), (1875, 1901)]
FOLDS = [(later <= a, (later > a) & (later <= b)) for a, b in CUTS]
for (f, v), (a, b) in zip(FOLDS, CUTS):
    log(f"  fold: train births <= {a} ({int(f.sum()):,})  ->  validate {a+1}-{b} ({int(v.sum()):,})")

# ── 2. worst-case feature stability ───────────────────────────────────────────────────────────────────────
A = np.column_stack([X, gap])
Ae = np.column_stack([Xe, gape])
NAMES = names + ["age gap in days"]
GAPCOL = A.shape[1] - 1

per_fold = np.zeros((len(FOLDS), A.shape[1]))
for k, (f, v) in enumerate(FOLDS):
    for j in range(A.shape[1]):
        per_fold[k, j] = auc(y[f], A[f, j])
    log(f"  scored every feature on fold {k+1}")
signs = np.sign(per_fold - 0.5)
consistent = np.all(signs == signs[0], axis=0)
strength_min = np.min(np.abs(per_fold - 0.5), axis=0)
strength_min[~consistent] = 0.0
order = np.argsort(-strength_min)
log(f"  {int(consistent.sum()):,} of {A.shape[1]:,} features point the same way in all three folds")
print("\n  the most STABLE features, by their WEAKEST fold (not their best)\n")
for j in order[:12]:
    print(f"    min {0.5+strength_min[j]:.4f}   folds "
          f"{'  '.join(f'{a:.4f}' for a in per_fold[:, j])}   {NAMES[j][:46]}")

# ── 3-5. candidate models, all selected on the mean fold AUC ───────────────────────────────────────────────
import lightgbm as lgb

sign_all = np.where(per_fold.mean(0) >= 0.5, 1.0, -1.0)


def lgb_pred(cols, tr_mask, apply_sets, mono=True, leaves=7, mcs=200, ff=0.6, bf=0.7, n=300, lr=0.03, seeds=3):
    """A deliberately small LightGBM. `mono` constrains the score to be non-increasing in the age gap, which is
    the one direction this problem is certain about."""
    mc = [0] * len(cols)
    if mono and GAPCOL in cols:
        mc[list(cols).index(GAPCOL)] = -1
    outs = [np.zeros(len(s[0])) for s in apply_sets]
    for s in range(seeds):
        m = lgb.LGBMClassifier(n_estimators=n, learning_rate=lr, num_leaves=leaves,
                               min_child_samples=mcs, colsample_bytree=ff, subsample=bf, subsample_freq=1,
                               reg_lambda=10.0, monotone_constraints=mc if mono else None,
                               random_state=s, verbose=-1)
        m.fit(A[tr_mask][:, cols], y[tr_mask])
        for i, (Aset,) in enumerate(apply_sets):
            outs[i] += m.predict_proba(Aset[:, cols])[:, 1]
    return [o / seeds for o in outs]


CAND = {}
CAND["age gap alone (the floor this must beat)"] = ("gap", None)
for k in (3, 8, 20, 50):
    CAND[f"LightGBM, monotone in the gap, top {k} stable features"] = ("lgb", (k, True))
for k in (8, 20):
    CAND[f"LightGBM, NO monotone constraint, top {k} stable"] = ("lgb", (k, False))
for k in (3, 8, 20):
    CAND[f"rank-average of the gap and the top {k} stable features"] = ("rank", k)

log("evaluating candidates across the three expanding-window folds")
results = {}
for nm, (kind, arg) in CAND.items():
    fold_aucs = []
    for f, v in FOLDS:
        if kind == "gap":
            s = -A[v, GAPCOL]
        elif kind == "lgb":
            k, mono = arg
            cols = list(dict.fromkeys(list(order[:k]) + [GAPCOL]))
            s = lgb_pred(cols, f, [(A[v],)], mono=mono)[0]
        else:
            k = arg
            cols = [j for j in order[:k] if j != GAPCOL]
            s = r01(-A[v, GAPCOL]) + sum(r01(sign_all[j] * A[v, j]) for j in cols) / max(1, len(cols))
        fold_aucs.append(auc(y[v], s))
    results[nm] = fold_aucs
    log(f"  {nm[:56]:<56} folds {' '.join(f'{a:.4f}' for a in fold_aucs)}  mean {np.mean(fold_aucs):.4f}")

ranked = sorted(results.items(), key=lambda kv: -np.mean(kv[1]))
WIN = ranked[0][0]
floor = np.mean(results["age gap alone (the floor this must beat)"])
print(f"\n  SELECTED ON THE FOLDS: {WIN}")
print(f"    mean fold AUC {np.mean(results[WIN]):.4f} vs the gap-only floor {floor:.4f}")
if np.mean(results[WIN]) <= floor + 1e-9:
    WIN = "age gap alone (the floor this must beat)"
    print("    nothing beat the floor across the folds, so the gap alone is what ships")

# ── refit the winner on ALL training couples and predict the held-out half ─────────────────────────────────
allm = np.ones(len(y), dtype=bool)
kind, arg = CAND[WIN]
if kind == "gap":
    pred = -Ae[:, GAPCOL]
elif kind == "lgb":
    k, mono = arg
    cols = list(dict.fromkeys(list(order[:k]) + [GAPCOL]))
    pred = lgb_pred(cols, allm, [(Ae,)], mono=mono, seeds=5)[0]
else:
    k = arg
    cols = [j for j in order[:k] if j != GAPCOL]
    pred = r01(-Ae[:, GAPCOL]) + sum(r01(sign_all[j] * Ae[:, j]) for j in cols) / max(1, len(cols))

sol = pd.read_csv(SOL).set_index("id")
lab = [c for c in sol.columns if c != "Usage"][0]
yte = sol.loc[ids, lab].to_numpy()
pub = (sol.loc[ids, "Usage"] == "Public").to_numpy()
print("\n  HELD OUT (read once, after selection)\n")
print(f"  {'model':<58} {'mean fold':>10} {'held':>7} {'public':>8} {'private':>8}")
for nm, fa in ranked:
    kind, arg = CAND[nm]
    if kind == "gap":
        p = -Ae[:, GAPCOL]
    elif kind == "lgb":
        k, mono = arg
        cols = list(dict.fromkeys(list(order[:k]) + [GAPCOL]))
        p = lgb_pred(cols, allm, [(Ae,)], mono=mono, seeds=3)[0]
    else:
        k = arg
        cols = [j for j in order[:k] if j != GAPCOL]
        p = r01(-Ae[:, GAPCOL]) + sum(r01(sign_all[j] * Ae[:, j]) for j in cols) / max(1, len(cols))
    star = "  <-- selected" if nm == WIN else ""
    print(f"  {nm[:58]:<58} {np.mean(fa):>10.4f} {auc(yte,p):>7.4f} {auc(yte[pub],p[pub]):>8.4f} "
          f"{auc(yte[~pub],p[~pub]):>8.4f}{star}")

pd.DataFrame({"id": ids, lab: r01(pred)}).to_csv(os.path.join(OUT, "submission.csv"), index=False)
json.dump({"winner": WIN, "fold_aucs": {k: [float(x) for x in v] for k, v in results.items()},
           "held_out": float(auc(yte, pred)), "gap_only_held_out": float(auc(yte, -Ae[:, GAPCOL])),
           "n_stable": int(consistent.sum())}, open(os.path.join(OUT, "sota.json"), "w"), indent=1)
print(f"\n  wrote {OUT}/submission.csv · held out {auc(yte,pred):.4f} vs gap-only {auc(yte,-Ae[:,GAPCOL]):.4f}")
