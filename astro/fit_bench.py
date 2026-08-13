"""
fit_bench.py — train the stack on a 90% split and score it across the PRECISION GRID.

THE BENCHMARK (operator specification, 2026-08-12). A single AUC on clean input is not what this model has to
survive: real birth data arrives to the day, to the month, to the year, or not at all. So the headline number
is the AVERAGE OF EIGHT AUCs, measured on the held-out 10%, over the same couples each time:

    the woman's date  full  ·  1st of the month  ·  1 January  ·  absent      -> 4 AUCs
    the man's date    full  ·  1st of the month  ·  1 January  ·  absent      -> 4 AUCs
    benchmark = the mean of those eight

The two "full" entries are the same quantity measured twice; both are reported because the specification asks
for four per partner, and averaging over eight rather than seven weights the clean case as the specification
intends.

WHY THE SAME COUPLES IN EVERY CONDITION. Stratifying real rows by the precision they happen to have (which is
what the earlier version did) confounds precision with cohort: year-only dates are concentrated in the 19th
century, where the parenthood rate is 46% rather than 24%. Degrading a FIXED set of day-precision couples
isolates the effect of losing precision from the effect of being a different population.

WHAT "ABSENT" MEANS, PLAINLY. The input contract is two dates. There is no way to express "no date" except by
the convention the dataset itself uses: the missing partner is placed on the known partner's day. So in that
condition the model has literally nothing about that person, the age gap is zero, and every chart reduces to a
function of the other date. It is a floor, not a handicap, and it should be read as one.

THE SPLIT IS PERSON-DISJOINT. A person appears in more than one partnership, so a random 90/10 by row would
put one of somebody's relationships in training and another in test. The split is by person group, which makes
the test share of ROWS approximate rather than exactly 10%.

NOTHING ABOUT THE TEST SET INFLUENCES ANY CHOICE. The meta-learner's regularisation is selected by
cross-validation inside the 90%, on ordinary AUC. The eight conditions are computed once, at the end, on data
no fitting step has seen.

Usage:
    cd astro && ~/.artamatch-venv/bin/python fit_bench.py
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(HERE, "astro-out")
BLOCKS = os.path.join(HERE, "blocks")
COUPLES = os.path.join(ROOT, "research/data-dob/couples-parents.json")
CAND = "/tmp/aq-bench-candidates.json"
YR = 365.2425
INNER = 5
TEST_FRAC = 0.10
WORKERS = int(os.environ.get("AQ_WORKERS") or 3)
SEED = 20260812


def hgb():
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=15,
                                          l2_regularization=1.0, random_state=0)


def logit():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000))


def _fit_block(arg):
    """One block: both model kinds, out-of-fold INSIDE the training 90%, then refit on all of it."""
    path, ypath, gidpath, trpath, key = arg
    tr = np.load(trpath)
    X = np.asarray(np.load(path, mmap_mode="r"), dtype=np.float32)[tr]
    y = np.load(ypath)[tr]
    gid = np.load(gidpath)[tr]
    folds = list(GroupKFold(n_splits=INNER).split(np.zeros(len(y)), y, groups=gid))
    best = None
    for kind, mk in (("hgb", hgb), ("logit", logit)):
        pv = np.zeros(len(y))
        try:
            for a, b in folds:
                pv[b] = mk().fit(X[a], y[a]).predict_proba(X[b])[:, 1]
            auc = float(roc_auc_score(y, pv))
        except Exception as e:
            print(f"    {key} / {kind} failed: {str(e)[:90]}", flush=True)
            continue
        if best is None or auc > best[1]:
            best = (kind, auc, pv)
    if best is None:
        return None
    kind, auc, pv = best
    return {"key": key, "kind": kind, "auc": auc, "oof": pv,
            "estimator": (hgb() if kind == "hgb" else logit()).fit(X, y), "cols": int(X.shape[1])}


# ── the eight conditions ──────────────────────────────────────────────────────────────────────────
def month_only(d):
    return d[:8] + "01"


def year_only(d):
    return d[:4] + "-01-01"


# THE FULL 4x4 GRID, not a list of marginal cases. The specification arrived as "4 AUCs for the woman, the
# same 4 for the man, average them" — eight numbers — and then as "9 scores". Those are different slices of
# the same object, and rather than guess which, this computes every combination of the two partners'
# precision and reports each slice from it:
#
#     LEVELS x LEVELS = 16 cells        every combination, the complete picture
#     the 3x3 day/month/year sub-grid   = 9 numbers
#     the 8 marginal conditions         = degrade one partner, the other full: the original specification,
#                                         with "both full" counted once per partner as asked
#     the diagonal                      both partners degraded together
#
# Reporting the grid costs one extra feature build per cell and removes the ambiguity for good.
LEVELS = [("full", None), ("month", month_only), ("year", year_only), ("none", "absent")]


def degrade_pair(row, wlev, mlev):
    """(aDob, bDob) with the woman's date at `wlev` and the man's at `mlev`, whichever partner is which."""
    a, b = row["aDob"], row["bDob"]
    wa = row.get("aSex") == "F"
    wdob, mdob = (a, b) if wa else (b, a)
    for dob_name, lev in (("w", wlev), ("m", mlev)):
        how = dict(LEVELS)[lev]
        if how is None:
            continue
        if how == "absent":
            # No way to say "no date" under a two-date contract except the dataset's own convention: place
            # the missing partner on the known partner's day. The model then knows nothing about them.
            if dob_name == "w":
                wdob = mdob
            else:
                mdob = wdob
        elif dob_name == "w":
            wdob = how(wdob)
        else:
            mdob = how(mdob)
    return (wdob, mdob) if wa else (mdob, wdob)


def main():
    sys.path.insert(0, HERE)
    sys.path.insert(0, WEB)
    os.environ.setdefault("AQ_COUPLES", COUPLES)
    os.environ["AQ_NO_PLACE"] = "1"
    os.environ["AQ_KEEP_ALL_COLS"] = "1"
    os.environ.setdefault("AQ_EPHEM_CACHE", os.path.join(HERE, "ephem-full.npz"))
    from core import load
    E = load()
    y = E.Y.astype(int)
    gid = E.gid
    man = json.load(open(os.path.join(HERE, "manifest.json")))
    blocks = [b for b in man["blocks"] if b["kind"] != "context"]
    print(f"\n  {E.n:,} couples · {int(y.sum()):,} became parents ({100*y.mean():.1f}%)")
    print(f"  {len(blocks)} blocks · {sum(b['cols'] for b in blocks):,} columns · "
          f"{len({b['slug'] for b in blocks})} traditions · inputs: two dates at 08:00 UT")

    # ── the 90/10 split, by person group ──────────────────────────────────────────────────────────
    rng = np.random.default_rng(SEED)
    groups = np.unique(gid)
    perm = rng.permutation(len(groups))
    ntest = int(round(TEST_FRAC * len(groups)))
    test_groups = set(groups[perm[:ntest]].tolist())
    is_test = np.array([g in test_groups for g in gid])
    tr_idx = np.flatnonzero(~is_test)
    te_idx = np.flatnonzero(is_test)
    print(f"\n  split by person group: {len(groups) - ntest:,} groups train / {ntest:,} test")
    print(f"  rows: {len(tr_idx):,} train ({100*len(tr_idx)/E.n:.1f}%) · "
          f"{len(te_idx):,} test ({100*len(te_idx)/E.n:.1f}%)")
    np.save(os.path.join(OUT, "y.npy"), y)
    np.save(os.path.join(OUT, "gid.npy"), gid)
    np.save(os.path.join(OUT, "train_idx.npy"), tr_idx)
    np.save(os.path.join(OUT, "test_idx.npy"), te_idx)

    # ── base models, fitted only on the training 90% ──────────────────────────────────────────────
    args = [(os.path.join(BLOCKS, b["file"]), os.path.join(OUT, "y.npy"),
             os.path.join(OUT, "gid.npy"), os.path.join(OUT, "train_idx.npy"), b["key"])
            for b in blocks]
    print(f"\n  fitting {len(args)} blocks x 2 kinds on the training rows, {WORKERS} workers…")
    t0 = time.time()
    res = []
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for i, r in enumerate(ex.map(_fit_block, args), 1):
            if r is None:
                continue
            res.append(r)
            print(f"    [{i:>2}/{len(args)}] {r['auc']:.4f}  {r['kind']:<5} {r['key'][:60]}", flush=True)
    print(f"  done in {time.time()-t0:.0f}s")
    res.sort(key=lambda r: -r["auc"])

    P = np.column_stack([r["oof"] for r in res])
    mu, sd = P.mean(0), P.std(0) + 1e-9
    ytr, gtr = y[tr_idx], gid[tr_idx]
    folds = list(GroupKFold(n_splits=INNER).split(np.zeros(len(ytr)), ytr, groups=gtr))
    best = None
    print(f"\n  meta logistic over {P.shape[1]} columns, C chosen INSIDE the training 90%")
    for C in (0.01, 0.03, 0.1, 0.3, 1.0):
        pv = np.zeros(len(ytr))
        for a, b in folds:
            pv[b] = LogisticRegression(C=C, max_iter=4000) \
                .fit((P[a] - mu) / sd, ytr[a]).predict_proba((P[b] - mu) / sd)[:, 1]
        a_ = float(roc_auc_score(ytr, pv))
        print(f"    C={C:<5} AUC {a_:.4f}")
        if best is None or a_ > best[1]:
            best = (C, a_)
    C, inner_auc = best
    meta = LogisticRegression(C=C, max_iter=4000).fit((P - mu) / sd, ytr)
    print(f"  chose C={C} (inner AUC {inner_auc:.4f})")

    # ── export first, so the benchmark is measured through the SHIPPED arrays ──────────────────────
    import export_model
    bmap = {b["key"]: b for b in blocks}
    specs = [{"key": r["key"], "slug": bmap[r["key"]]["slug"], "name": bmap[r["key"]]["name"],
              "kind": r["kind"], "kept_idx": bmap[r["key"]]["kept_idx"],
              "full_cols": bmap[r["key"]]["full_cols"], "auc": r["auc"], "estimator": r["estimator"]}
             for r in res]
    metad = {"mu": mu, "sd": sd, "coef": meta.coef_.ravel(), "intercept": meta.intercept_[0],
             "n": int(len(tr_idx)), "rate": float(ytr.mean()), "hour": "08:00 UT",
             "contract": "two birth dates; no birthplace, no houses, no Ascendant"}
    size, raw = export_model.pack(specs, metad, os.path.join(WEB, "model.json"),
                                  os.path.join(WEB, "model.npz"))
    print(f"\n  exported web/model.json + model.npz ({size/1e6:.2f} MB)")

    # ── the eight conditions, on the held-out 10% ─────────────────────────────────────────────────
    bench = benchmark(te_idx, y)

    # fold the results into the shipped header
    h = json.load(open(os.path.join(WEB, "model.json")))
    h.update({"auc": bench["benchmark"], "benchmark": bench,
              "baseline": {"signed age gap (dob_woman - dob_man)": bench["baseline_benchmark"]},
              "n": int(len(tr_idx)), "rate": float(ytr.mean()),
              "tradition_auc": {k: v for k, v in bench["tradition_auc"].items()},
              "inner_auc": inner_auc, "meta_C": C})
    json.dump(h, open(os.path.join(WEB, "model.json"), "w"), indent=1)
    json.dump({"benchmark": bench, "inner_auc": inner_auc, "meta_C": C,
               "n_train": int(len(tr_idx)), "n_test": int(len(te_idx)),
               "base": [{"key": r["key"], "kind": r["kind"], "auc": r["auc"]} for r in res]},
              open(os.path.join(OUT, "fit-bench.json"), "w"), indent=1)
    print(f"\n  wrote astro-out/fit-bench.json and folded the benchmark into web/model.json")


def benchmark(te_idx, y_all):
    """The eight conditions, scored through the exported arrays on the held-out couples."""
    import predictor
    import sweshim
    raw = json.load(open(COUPLES))

    # core.py's own filters decide which rows exist, so map test indices back to source rows by rebuilding
    # the same record order the probe wrote.
    order = json.load(open(os.path.join(OUT, "rows.json")))["keys"]
    src = {}
    for r in raw:
        src[(r["a"], r["b"])] = r
        src[(r["b"], r["a"])] = r
    rows = []
    for i in te_idx:
        k = tuple(order[i])
        r = src.get(k)
        if r is None:
            continue
        # only couples with BOTH dates to the day: the "full" condition has to be genuinely full, and a
        # row that is already year-precision cannot be degraded to year-precision
        if int(r.get("aPrec", 11)) < 11 or int(r.get("bPrec", 11)) < 11:
            continue
        if not (r.get("aSex") in ("M", "F") and r.get("bSex") in ("M", "F")
                and r["aSex"] != r["bSex"]):
            continue
        rows.append(r)
    print(f"\n  BENCHMARK on the held-out 10%: {len(rows):,} couples with both dates to the day "
          f"and both sexes known")

    sweshim.load(os.path.join(WEB, "ephem4.bin"), os.path.join(WEB, "tables.json"))
    sys.modules["swisseph"] = sweshim
    stack = predictor.load(open(os.path.join(WEB, "model.json")).read(),
                           open(os.path.join(WEB, "model.npz"), "rb").read())
    os.environ["AQ_COUPLES"] = CAND
    os.environ["AQ_NO_EPHEM_CACHE"] = "1"
    os.environ["AQ_EPHEM_CACHE"] = "/nonexistent.npz"
    import importlib
    import core
    importlib.reload(core)
    mods = {s: __import__(f"trad_{s}") for s in stack.modules}

    print(f"\n  {'woman':>6} x {'man':<6}  {'rows':>7} {'stack':>8} {'baseline':>9} {'lift':>8}")
    print(f"  {'-'*15}  {'-'*7} {'-'*8} {'-'*9} {'-'*8}")
    out, per_trad_full = {}, {}
    names = [n for n, _ in LEVELS]
    for wlev in names:
        for mlev in names:
            nm = f"{wlev}|{mlev}"
            recs = []
            for i, r in enumerate(rows):
                a, b = degrade_pair(r, wlev, mlev)
                recs.append({"a": f"a{i}", "b": f"b{i}", "aDob": a, "bDob": b,
                             "aSex": r["aSex"], "bSex": r["bSex"],
                             "aPrec": 11, "bPrec": 11, "aWin": 1, "bWin": 1,
                             "label": int(r.get("label", r.get("hasKids", 0)))})
            json.dump(recs, open(CAND, "w"))
            E = core.load()
            blocks = {}
            for slug, mod in mods.items():
                for k, v in (mod.build(E) or {}).items():
                    blocks[f"{slug}::{k}"] = v
            p, Pm = stack.proba(blocks)
            yy = E.Y.astype(int)
            auc = float(roc_auc_score(yy, p))
            gap = np.where(E.SEX_O.astype(str) == "M", (E.JD[1] - E.JD[0]) / YR,
                           -(E.JD[1] - E.JD[0]) / YR)
            # the baseline is refitted per cell on the SAME degraded input, which is the only fair
            # comparison: a two-parameter model on a blurred gap is what astrology has to beat
            bp = np.zeros(len(yy))
            for a_, b_ in GroupKFold(n_splits=5).split(np.zeros(len(yy)), yy, groups=E.gid):
                bp[b_] = LogisticRegression(max_iter=2000).fit(gap[a_, None], yy[a_]) \
                    .predict_proba(gap[b_, None])[:, 1]
            bauc = float(roc_auc_score(yy, bp))
            out[nm] = {"woman": wlev, "man": mlev, "rows": int(len(yy)),
                       "stack": auc, "baseline": bauc, "lift": auc - bauc}
            if wlev == "full" and mlev == "full":
                for k, v in stack.by_tradition(Pm).items():
                    per_trad_full[k] = float(roc_auc_score(yy, v))
            print(f"  {wlev:>6} x {mlev:<6}  {len(yy):>7,} {auc:>8.4f} {bauc:>9.4f} "
                  f"{auc-bauc:>+8.4f}", flush=True)

    def mean_of(cells):
        return (float(np.mean([out[c]["stack"] for c in cells])),
                float(np.mean([out[c]["baseline"] for c in cells])))

    # THE SLICES. One grid, several ways of summarising it, each stated so nobody has to guess which
    # average a number came from.
    marginal8 = ["full|full", "month|full", "year|full", "none|full",
                 "full|full", "full|month", "full|year", "full|none"]
    grid9 = [f"{w}|{m}" for w in ("full", "month", "year") for m in ("full", "month", "year")]
    all16 = list(out.keys())
    diag = ["full|full", "month|month", "year|year", "none|none"]
    slices = {}
    print(f"\n  {'slice':<52} {'stack':>8} {'baseline':>9} {'lift':>8}")
    print(f"  {'-'*52} {'-'*8} {'-'*9} {'-'*8}")
    for label, cells in (
            ("8 marginal conditions (4 per partner, the spec)", marginal8),
            ("9 cells: the day/month/year sub-grid", grid9),
            ("all 16 cells", all16),
            ("4 diagonal cells (both degraded together)", diag)):
        a, b = mean_of(cells)
        slices[label] = {"stack": a, "baseline": b, "cells": cells}
        print(f"  {label:<52} {a:>8.4f} {b:>9.4f} {a-b:>+8.4f}")
    b8, bb8 = mean_of(marginal8)
    print(f"\n  HEADLINE BENCHMARK = the mean of the 8 marginal conditions: {b8:.4f} "
          f"(baseline {bb8:.4f}, lift {b8-bb8:+.4f})")
    return {"cells": out, "slices": slices, "benchmark": b8, "baseline_benchmark": bb8,
            "tradition_auc": per_trad_full, "n_rows": int(len(rows))}


if __name__ == "__main__":
    main()
