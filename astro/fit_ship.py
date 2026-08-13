"""
fit_ship.py — fit the stack on ALL the couples and export exactly that model to the browser.

WHAT THIS IS. The end of the training pipeline: it takes the blocks that `collect_chunked.py` built for every
couple, fits one base model per block, fits a meta logistic over their out-of-fold predictions, measures the
result against the single permitted baseline, and writes the two files `web/` evaluates. The model the page
runs is the model measured here — `export_model.py --selftest` proves the browser's numpy predictor
reproduces scikit-learn to 1e-16, so there is no gap between the reported number and the shipped one.

THE INPUT CONTRACT: TWO DATES. Birthplaces were dropped by operator instruction on 2026-08-12, at the single
point where they enter core.py. So there is no Ascendant, no house cusp and no astrocartography line, every
chart is cast at 08:00 UT, and the two place-only traditions are gone. That also leaves ONE permitted
baseline — a two-parameter logistic on the signed subtraction of the two birth dates — because the signed
distance gap between birthplaces no longer has anything to measure.

HOW THE STACK IS BUILT, AND WHY EACH STEP IS SHAPED THIS WAY

  1. Every base model is fitted BOTH ways, as histogram gradient boosting and as a standardised logistic, and
     the better out-of-fold score wins. Not for accuracy — the difference is usually small — but because
     both kinds are exportable to plain arrays. Letting the screening stage pick from its full zoo would
     sooner or later select a random forest or an MLP that cannot be shipped, and the shipped model would
     then quietly differ from the measured one.
  2. Folds are person-disjoint GroupKFold. A person appears in more than one couple, so splitting by row
     would let a base model train on one of someone's relationships and predict on another.
  3. The meta logistic is fitted on the out-of-fold columns, then the base models are REFITTED on every row.
     That is the standard arrangement: the meta learns weights from predictions no base model had seen, and
     the shipped bases still use all the data.
  4. Robustness is reported as part of the headline, not as an appendix — AUC within each date-precision
     stratum, which is what "robust to missing data" has to mean when a quarter of the rows have only a year
     and a fifth have only one date at all.

Usage:
    cd astro && ~/.artamatch-venv/bin/python fit_ship.py
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
WEB = os.path.join(os.path.dirname(HERE), "web")
OUT = os.path.join(HERE, "astro-out")
BLOCKS = os.path.join(HERE, "blocks")
YR = 365.2425
FOLDS = 5
# Three, not four. The widest block is 1,442 columns, which at 134,957 rows is 779 MB of float32 per
# worker before histogram gradient boosting allocates its own binned copy — and the machine has 17 GB that
# also has to hold the ephemeris table.
WORKERS = int(os.environ.get("AQ_WORKERS") or 3)


def hgb():
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=15,
                                          l2_regularization=1.0, random_state=0)


def logit():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000))


def _fit_block(arg):
    """One block, both model kinds, out-of-fold. Runs in a worker; loads its own arrays from disk.

    The folds are RECOMPUTED here rather than passed in. GroupKFold is deterministic given (y, groups), so
    the worker gets the identical split — and shipping five index pairs over 134,957 rows to each of 51
    tasks would have serialised half a gigabyte to say something both sides can derive.
    """
    path, ypath, gidpath, key = arg
    X = np.asarray(np.load(path, mmap_mode="r"), dtype=np.float32)
    y = np.load(ypath)
    gid = np.load(gidpath)
    folds = list(GroupKFold(n_splits=FOLDS).split(np.zeros(len(y)), y, groups=gid))
    best = None
    for kind, mk in (("hgb", hgb), ("logit", logit)):
        pv = np.zeros(len(y))
        try:
            for tr, te in folds:
                m = mk().fit(X[tr], y[tr])
                pv[te] = m.predict_proba(X[te])[:, 1]
            auc = float(roc_auc_score(y, pv))
        except Exception as e:
            print(f"    {key} / {kind} failed: {str(e)[:90]}", flush=True)
            continue
        if best is None or auc > best[1]:
            best = (kind, auc, pv)
    if best is None:
        return None
    kind, auc, pv = best
    full = (hgb() if kind == "hgb" else logit()).fit(X, y)
    return {"key": key, "kind": kind, "auc": auc, "oof": pv, "estimator": full,
            "cols": int(X.shape[1])}


def main():
    sys.path.insert(0, HERE)
    os.environ.setdefault("AQ_COUPLES", os.path.join(os.path.dirname(HERE),
                                                     "research/data-dob/couples-parents.json"))
    os.environ["AQ_NO_PLACE"] = "1"
    os.environ.setdefault("AQ_EPHEM_CACHE", os.path.join(HERE, "ephem-full.npz"))
    from core import load
    E = load()
    y = E.Y.astype(int)
    np.save(os.path.join(OUT, "y.npy"), y)
    man = json.load(open(os.path.join(HERE, "manifest.json")))
    blocks = [b for b in man["blocks"] if b["kind"] != "context"]
    print(f"\n  {E.n:,} couples · {int(y.sum()):,} became parents together ({100*y.mean():.1f}%)")
    print(f"  {len(blocks)} blocks · {sum(b['cols'] for b in blocks):,} columns · "
          f"{len({b['slug'] for b in blocks})} traditions")
    print(f"  inputs: the two birth dates, 08:00 UT — no birthplace, no houses, no Ascendant")

    folds = list(GroupKFold(n_splits=FOLDS).split(np.zeros(E.n), y, groups=E.gid))
    print(f"  {FOLDS} person-disjoint folds over {len(set(E.gid.tolist())):,} person groups")

    # ── the one permitted baseline ────────────────────────────────────────────────────────────────
    gap = np.where(E.SEX_O.astype(str) == "M", (E.JD[1] - E.JD[0]) / YR, -(E.JD[1] - E.JD[0]) / YR)
    pv = np.zeros(E.n)
    for tr, te in folds:
        m = LogisticRegression(max_iter=2000).fit(gap[tr, None], y[tr])
        pv[te] = m.predict_proba(gap[te, None])[:, 1]
    base_auc = float(roc_auc_score(y, pv))
    fm = LogisticRegression(max_iter=2000).fit(gap[:, None], y)
    print(f"\n  BASELINE  signed age gap (dob_woman - dob_man, years)   AUC {base_auc:.4f}")
    print(f"            logit p = {fm.intercept_[0]:+.4f} {fm.coef_[0][0]:+.5f} * gap")

    # ── base models ───────────────────────────────────────────────────────────────────────────────
    yp = os.path.join(OUT, "y.npy")
    gp = os.path.join(OUT, "gid.npy")
    np.save(gp, E.gid)
    args = [(os.path.join(BLOCKS, b["file"]), yp, gp, b["key"]) for b in blocks]
    print(f"\n  fitting {len(args)} blocks x 2 model kinds, out-of-fold, on {WORKERS} workers…")
    t0 = time.time()
    res = []
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for i, r in enumerate(ex.map(_fit_block, args), 1):
            if r is None:
                continue
            res.append(r)
            print(f"    [{i:>2}/{len(args)}] {r['auc']:.4f}  {r['kind']:<5} {r['key'][:62]}", flush=True)
    print(f"  base models done in {time.time()-t0:.0f}s")
    res.sort(key=lambda r: -r["auc"])
    bym = {}
    for r in res:
        bym.setdefault(r["key"].split("::")[0], []).append(r)

    P = np.column_stack([r["oof"] for r in res])
    mu, sd = P.mean(0), P.std(0) + 1e-9

    # ── meta ──────────────────────────────────────────────────────────────────────────────────────
    print(f"\n  meta logistic over {P.shape[1]} out-of-fold columns")
    best = None
    for C in (0.01, 0.03, 0.1, 0.3, 1.0):
        pred = np.zeros(E.n)
        for tr, te in folds:
            m = LogisticRegression(C=C, max_iter=4000).fit((P[tr] - mu) / sd, y[tr])
            pred[te] = m.predict_proba((P[te] - mu) / sd)[:, 1]
        a = float(roc_auc_score(y, pred))
        print(f"    C={C:<5} AUC {a:.4f}")
        if best is None or a > best[1]:
            best = (C, a, pred)
    C, stack_auc, stack_pred = best
    meta = LogisticRegression(C=C, max_iter=4000).fit((P - mu) / sd, y)
    print(f"\n  STACK  AUC {stack_auc:.4f}   baseline {base_auc:.4f}   "
          f"lift {stack_auc - base_auc:+.4f}   (meta C={C})")

    per_trad = {}
    for slug, rs in bym.items():
        pv = np.mean([r["oof"] for r in rs], axis=0)
        per_trad[slug] = float(roc_auc_score(y, pv))
    print(f"\n  {'tradition':<24} {'AUC':>7}  blocks")
    for slug, a in sorted(per_trad.items(), key=lambda t: -t[1]):
        print(f"  {slug:<24} {a:>7.4f}  {len(bym[slug])}")

    # ── robustness: what the model does on incomplete inputs, measured on real rows ───────────────
    rob = robustness(E, y, stack_pred, gap)

    # ── export ────────────────────────────────────────────────────────────────────────────────────
    import export_model
    bmap = {b["key"]: b for b in blocks}
    specs = []
    for r in res:
        b = bmap[r["key"]]
        specs.append({"key": r["key"], "slug": b["slug"], "name": b["name"], "kind": r["kind"],
                      "kept_idx": b["kept_idx"], "full_cols": b["full_cols"],
                      "auc": r["auc"], "estimator": r["estimator"]})
    metad = {"mu": mu, "sd": sd, "coef": meta.coef_.ravel(), "intercept": meta.intercept_[0],
             "auc": stack_auc, "baseline": {"signed age gap (dob_woman - dob_man)": base_auc},
             "n": int(E.n), "rate": float(y.mean()), "hour": "08:00 UT",
             "contract": "two birth dates; no birthplace, no houses, no Ascendant",
             "tradition_auc": per_trad, "robustness": rob}
    size, raw = export_model.pack(specs, metad, os.path.join(WEB, "model.json"),
                                  os.path.join(WEB, "model.npz"))
    print(f"\n  wrote web/model.json and web/model.npz  ({size/1e6:.2f} MB compressed, "
          f"{raw/1e6:.1f} MB raw)")
    json.dump({"auc": stack_auc, "baseline": base_auc, "meta_C": C, "n": int(E.n),
               "rate": float(y.mean()), "tradition_auc": per_trad, "robustness": rob,
               "base": [{"key": r["key"], "kind": r["kind"], "auc": r["auc"]} for r in res]},
              open(os.path.join(OUT, "fit-ship.json"), "w"), indent=1)
    print(f"  wrote astro-out/fit-ship.json")


def robustness(E, y, pred, gap):
    """AUC within each stratum of input completeness — measured on real rows, not simulated.

    "Robust to missing data" is a claim about the rows that HAVE missing data, so the honest measurement is
    a stratified one: take the same out-of-fold predictions and score them inside each precision class. The
    baseline is scored in the same strata, because a stratum can be harder for everything (a year-only date
    destroys the Sun and the Moon for the astrology AND blurs the age gap for the baseline) and a number that
    only falls tells you nothing about which of the two fell further.
    """
    pO, pY = E.PREC_O.astype(int), E.PREC_Y.astype(int)
    lo = np.minimum(pO, pY)
    strata = [
        ("both dates to the day", (pO >= 11) & (pY >= 11)),
        ("one date to the month", (lo == 10)),
        ("one date to the year only", (lo == 9)),
        ("one date unknown entirely", (lo == 0)),
    ]
    out = {}
    pv = np.zeros(len(y))
    folds = list(GroupKFold(n_splits=FOLDS).split(np.zeros(len(y)), y, groups=E.gid))
    for tr, te in folds:
        m = LogisticRegression(max_iter=2000).fit(gap[tr, None], y[tr])
        pv[te] = m.predict_proba(gap[te, None])[:, 1]
    print(f"\n  ROBUSTNESS TO MISSING DATES — AUC within each precision stratum, on real rows")
    print(f"  {'stratum':<28} {'rows':>8} {'rate':>7} {'stack':>8} {'baseline':>9} {'lift':>8}")
    for nm, m in strata:
        if m.sum() < 200 or len(np.unique(y[m])) < 2:
            print(f"  {nm:<28} {int(m.sum()):>8,}  too few rows to score")
            continue
        a = float(roc_auc_score(y[m], pred[m]))
        b = float(roc_auc_score(y[m], pv[m]))
        out[nm] = {"rows": int(m.sum()), "rate": float(y[m].mean()), "stack": a, "baseline": b}
        print(f"  {nm:<28} {int(m.sum()):>8,} {100*y[m].mean():>6.1f}% {a:>8.4f} {b:>9.4f} "
              f"{a-b:>+8.4f}")
    return out


if __name__ == "__main__":
    main()
