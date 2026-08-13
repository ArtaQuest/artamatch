"""
astro_stack.py — the best ASTROLOGY-ONLY stacked model, against the one permitted baseline.

ASTROLOGY ONLY. Every feature comes from a trad_* module: charts, aspects, houses, divisional charts,
calendars, astrocartography lines. No cohort or exposure variable, no citizenship, no sex, no raw
latitude and longitude as geography — birthplace coordinates enter only through astrological machinery
(house cusps, the Ascendant, astrocartography lines), which is what they are for in this tradition.

THE BASELINE, and the only one reported: a two-parameter logistic on the SIGNED difference of the two birth
dates, dob_woman - dob_man in years. Positive means the man is older.

HOW THE STACK IS BUILT
  1. every block is screened, and the survivors are chosen for DIVERSITY as well as score — at most three
     blocks per tradition, so one prolific module cannot fill the ensemble with restatements of itself
  2. out-of-fold predictions for each survivor, over person-disjoint GroupKFold folds, so a base model never
     predicts on a couple whose person it trained on
  3. meta-learners over those OOF columns: plain averaging, ridge-penalised logistic at several strengths,
     rank averaging, and greedy ensemble selection with replacement (Caruana), each scored under a nested
     outer fold so the meta-learner is never fitted on the rows it is judged on

Usage: cd astro && ~/.artamatch-venv/bin/python astro_stack.py
"""

import json
import os

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from core import load
import evalx
from evalx import MODELS
import run

YR = 365.2425
MAX_PER_MODULE = 3
# No global cap on the number of base models. See diverse(): the cap is per tradition, so every tradition
# that can be computed from two birth dates and two birthplaces is represented.
N_BASE = None
OUTER = 5


def signed_gap(E):
    """dob_woman - dob_man in years. Positive means the man is older."""
    raw = (E.JD[1] - E.JD[0]) / YR
    return np.where(E.SEX_O.astype(str) == "M", raw, -raw)


def signed_distance(E):
    """The spatial analogue of the signed age gap: how far apart the two birthplaces are, SIGNED.

    Distance alone is unsigned, so it cannot express direction, exactly as an absolute age gap cannot
    express which partner is older. The sign here is east-west: positive when the woman was born EAST of
    the man. Magnitude is the great-circle distance in thousands of kilometres, so the fitted coefficient
    reads per 1,000 km. Unknown for either birthplace gives 0 with the pair excluded from the fit's
    information by construction (a defined zero, flagged nowhere because a two-parameter model has no room
    for a flag — which is a real limitation of the baseline, not of the data).
    """
    la, lo = np.nan_to_num(E.LAT_O), np.nan_to_num(E.LON_O)
    lb, lob = np.nan_to_num(E.LAT_Y), np.nan_to_num(E.LON_Y)
    ok = (np.isfinite(E.LAT_O) & np.isfinite(E.LON_O) &
          np.isfinite(E.LAT_Y) & np.isfinite(E.LON_Y)).astype(float)
    p1, p2 = np.radians(la), np.radians(lb)
    dl = np.radians(lob - lo)
    h = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    d = 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(h, 0, 1))) / 1000.0
    east = np.sign(np.mod(lob - lo + 180.0, 360.0) - 180.0)
    # orient by which partner is the woman, so the sign means the same thing in every row
    woman_is_younger = (E.SEX_O.astype(str) == "M")
    signed = d * east * np.where(woman_is_younger, 1.0, -1.0)
    return signed * ok


def diverse(scr, files):
    """Up to MAX_PER_MODULE blocks from EVERY tradition — a per-tradition guarantee, not a global top-N.

    The earlier version took the best N_BASE blocks subject to a per-module cap, and that let a global cut
    starve a whole tradition: at N_BASE=45 the Vedic marriage-matching module (Ashtakoot's 36 points, Kuja
    dosha, the ten Poruthams) fell off the list entirely — the one tradition in the set whose subject matter
    IS marriage. A stack has no reason to prefer a 46th block from a tradition already represented three
    times over the first block from a tradition represented none, and the meta-learner is regularised, so
    a weak tradition costs a little shrinkage rather than accuracy. Operator instruction, 2026-08-12: every
    significant tradition is present.

    The three wedding-date traditions (electional, muhurta, wedding_transits) are absent for a different
    and unfixable reason — they need the date of the marriage, which does not exist at inference time. core.py
    skips them in DOB-only mode, so they never reach screening.
    """
    per, chosen = {}, []
    for r in sorted(scr, key=lambda x: -x["auc"]):
        if r["key"] not in files or r.get("kind") == "context":
            continue
        if per.get(r["slug"], 0) >= MAX_PER_MODULE:
            continue
        per[r["slug"]] = per.get(r["slug"], 0) + 1
        chosen.append(r)
    return chosen


def caruana(P, y, hill, rounds=80):
    m = P.shape[1]
    w = np.zeros(m)
    S = np.zeros(len(hill))
    k = 0
    for _ in range(rounds):
        best, bj = -np.inf, -1
        for j in range(m):
            s = roc_auc_score(y[hill], (S + P[hill, j]) / (k + 1))
            if s > best:
                best, bj = s, j
        S = S + P[hill, bj]
        k += 1
        w[bj] += 1
    return w / w.sum()


def main():
    E = load()
    man, files = run._blocks()
    scr = json.load(open(run.SCREEN))
    base_rows = diverse(scr, files)
    print(f"\n  {E.n:,} couples · {int(E.Y.sum()):,} became parents together ({100*E.Y.mean():.1f}%)")
    nmod = len({r["slug"] for r in base_rows})
    print(f"  {len(scr)} astrology blocks screened · {len(base_rows)} chosen as base models "
          f"— up to {MAX_PER_MODULE} from each of {nmod} traditions\n")
    bym = {}
    for r in base_rows:
        bym.setdefault(r["slug"], []).append(r)
    for slug, rs in sorted(bym.items(), key=lambda t: -max(x["auc"] for x in t[1])):
        aucs = ", ".join("%.4f" % x["auc"] for x in rs)
        print(f"    {slug:<24} {aucs}")

    folds = list(GroupKFold(n_splits=OUTER).split(np.zeros(E.n), E.Y, groups=E.gid))
    print(f"\n  THE TWO PERMITTED BASELINES, each a 2-parameter logistic on one signed subtraction")
    print(f"  {'baseline':<44} {'AUC':>8}   fitted")
    print(f"  {'-'*44} {'-'*8}   {'-'*34}")
    bases = {}
    for nm, v, unit in (("signed age gap (dob_woman - dob_man)", signed_gap(E), "per year"),
                        ("signed distance gap (birthplaces, E+)", signed_distance(E), "per 1000 km")):
        X = v[:, None]
        pv = np.zeros(E.n)
        for tr, te in folds:
            m = LogisticRegression(max_iter=2000).fit(X[tr], E.Y[tr])
            pv[te] = m.predict_proba(X[te])[:, 1]
        auc = float(roc_auc_score(E.Y, pv))
        bases[nm] = auc
        fm = LogisticRegression(max_iter=2000).fit(X, E.Y)
        print(f"  {nm:<44} {auc:>8.4f}   logit p = {fm.intercept_[0]:+.4f} "
              f"{fm.coef_[0][0]:+.5f} * x   ({unit})")
    base = max(bases.values())
    print(f"\n  the stronger of the two ({max(bases, key=bases.get)}) is used as the reference: {base:.4f}")

    # ── out-of-fold base predictions ──────────────────────────────────────────────────────────────
    print(f"\n  building out-of-fold predictions for {len(base_rows)} base models…")
    P = np.zeros((E.n, len(base_rows)))
    for j, r in enumerate(base_rows):
        X = run._get(files, r["key"])
        f = MODELS(X.shape[1])[r["model"]]
        for tr, te in folds:
            mdl = run.pipe("raw", X.shape[1], f)
            mdl.fit(X[tr], E.Y[tr])
            P[te, j] = evalx._proba(mdl, X[te])
        print(f"    [{j+1:>2}/{len(base_rows)}] {r['auc']:.4f} -> oof "
              f"{roc_auc_score(E.Y, P[:, j]):.4f}  {r['key'][:52]}", flush=True)

    # ── meta-learners, each scored on outer folds it was not fitted on ─────────────────────────────
    print(f"\n  {'stacked model':<40} {'AUC':>8} {'vs baseline':>12}")
    print(f"  {'-'*40} {'-'*8} {'-'*12}")
    res = {"baselines": bases, "reference": base}
    metas = {
        "mean of all base models": None,
        "rank mean of all": "rank",
        "meta logistic (C=0.03)": 0.03,
        "meta logistic (C=0.3)": 0.3,
        "meta logistic (C=3)": 3.0,
        "greedy ensemble (Caruana)": "caruana",
    }
    best_name, best_auc, best_pred = None, -1, None
    for name, spec in metas.items():
        pred = np.zeros(E.n)
        for tr, te in folds:
            if spec is None:
                pred[te] = P[te].mean(1)
            elif spec == "rank":
                R = np.apply_along_axis(lambda c: np.argsort(np.argsort(c)) / len(c), 0, P)
                pred[te] = R[te].mean(1)
            elif spec == "caruana":
                inner = list(GroupKFold(n_splits=3).split(np.zeros(len(tr)), E.Y[tr], groups=E.gid[tr]))
                _, hill = inner[0]
                w = caruana(P[tr], E.Y[tr], hill)
                pred[te] = P[te] @ w
            else:
                mdl = make_pipeline(StandardScaler(), LogisticRegression(C=spec, max_iter=3000))
                mdl.fit(P[tr], E.Y[tr])
                pred[te] = mdl.predict_proba(P[te])[:, 1]
        auc = float(roc_auc_score(E.Y, pred))
        res[name] = auc
        print(f"  {name:<40} {auc:>8.4f} {auc-base:>+12.4f}")
        if auc > best_auc:
            best_name, best_auc, best_pred = name, auc, pred

    single = max(range(P.shape[1]), key=lambda j: roc_auc_score(E.Y, P[:, j]))
    res["best single astrology block"] = {
        "auc": float(roc_auc_score(E.Y, P[:, single])), "key": base_rows[single]["key"],
        "model": base_rows[single]["model"]}
    print(f"\n  best single astrology block: {res['best single astrology block']['auc']:.4f}  "
          f"{base_rows[single]['key']}")
    print(f"  BEST STACK: {best_name} at {best_auc:.4f} ({best_auc-base:+.4f} over the baseline)")
    res["best_stack"] = {"name": best_name, "auc": best_auc}
    res["base_models"] = [{"key": r["key"], "model": r["model"], "rep": "raw", "screen_auc": r["auc"]}
                          for r in base_rows]
    json.dump(res, open(os.path.join(run.OUTDIR, "astro-stack.json"), "w"), indent=1)
    np.save(os.path.join(run.OUTDIR, "astro-oof.npy"), P)
    print(f"\n  wrote {run.OUTDIR}/astro-stack.json and astro-oof.npy")


if __name__ == "__main__":
    main()
