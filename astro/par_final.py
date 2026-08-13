"""
par_final.py — the clean target at maximum scale, measured against the age-gap baseline, plus the one
comparison the numbers force: does any astrology block add anything over EXPOSURE?

WHAT THE SCREEN SHOWED. Four unrelated traditions all top out within 0.0014 of each other:

    lun: saros / inex / metonic / callippic     0.6981
    har: declination parallels + out-of-bounds  0.6980
    meso: Long Count distance numbers           0.6978
    bab+egy: schematic 360-day + Egyptian civil 0.6967
    coh: exposure (the censoring variable)      0.6976   <- not astrology at all

while the traditions that can only express a CYCLIC position, and therefore cannot encode which year it is,
sit far below: Hellenistic sign qualities 0.6068, Chinese sexagenary cycles 0.5832. Four independent
implementations of "what year was this" converging on the same number is not four traditions agreeing; it
is one variable measured four ways.

So this file asks two things:
  1. how everything compares with the two-parameter age-gap logistic, the only baseline being reported;
  2. whether any astrology block adds to exposure, which is what separates a tradition carrying its own
     information from a tradition re-deriving the calendar.

Usage: cd astro && /tmp/aqpy/bin/python par_final.py
"""

import json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from core import load
import evalx
from evalx import MODELS
import run

YR = 365.2425
COH = "cohort::coh: EVERYTHING"


def main():
    E = load()
    man, files = run._blocks()
    scr = json.load(open(run.SCREEN))
    astro = [r for r in scr if r.get("kind") != "context"]
    ctxb = [r for r in scr if r.get("kind") == "context" and not r["key"].startswith("cohort::")]
    gap = ((E.JD[1] - E.JD[0]) / YR)[:, None]
    folds = list(GroupKFold(n_splits=5).split(np.zeros(E.n), E.Y, groups=E.gid))

    def score(M, model=None):
        p = np.zeros(E.n)
        for tr, te in folds:
            if model is None:
                m = LogisticRegression(max_iter=2000).fit(M[tr], E.Y[tr])
                p[te] = m.predict_proba(M[te])[:, 1]
            else:
                m = run.pipe("raw", M.shape[1], MODELS(M.shape[1])[model])
                m.fit(M[tr], E.Y[tr])
                p[te] = evalx._proba(m, M[te])
        return float(roc_auc_score(E.Y, p))

    base = score(gap)
    EXP = run._get(files, COH)
    CTX = run._get(files, ctxb[0]["key"]) if ctxb else np.zeros((E.n, 0))
    out = {"baseline_agegap_2param": base, "n": int(E.n), "rate": float(E.Y.mean())}
    print(f"\n  {E.n:,} couples · {int(E.Y.sum()):,} became parents together ({100*E.Y.mean():.1f}%)\n")
    print(f"  {'model':<54} {'cols':>6} {'AUC':>8} {'vs baseline':>12}")
    print(f"  {'-'*54} {'-'*6} {'-'*8} {'-'*12}")
    print(f"  {'BASELINE: logistic on the age gap':<54} {'2 par':>6} {base:>8.4f} {'—':>12}")

    rows = [("exposure / cohort alone (NOT astrology)", EXP)]
    for r in astro[:6]:
        rows.append((f"astrology: {r['name'][:40]}", run._get(files, r["key"])))
    rows.append((f"context: {ctxb[0]['name'][:40]}" if ctxb else "context", CTX))
    for name, M in rows:
        if M.shape[1] == 0:
            continue
        a = score(M, "xgboost")
        out[name] = {"cols": int(M.shape[1]), "auc": a}
        print(f"  {name:<54} {M.shape[1]:>6} {a:>8.4f} {a-base:>+12.4f}")

    print(f"\n  {'ON TOP OF EXPOSURE — does the astrology add anything?':<54}")
    e = score(EXP, "xgboost")
    print(f"  {'exposure alone':<54} {EXP.shape[1]:>6} {e:>8.4f} {'—':>12}")
    gains = {}
    for r in astro[:6]:
        X = run._get(files, r["key"])
        a = score(np.hstack([EXP, X]), "xgboost")
        gains[r["name"]] = a - e
        print(f"  {'+ ' + r['name'][:52]:<54} {EXP.shape[1]+X.shape[1]:>6} {a:>8.4f} {a-e:>+12.4f}")
    a = score(np.hstack([EXP, CTX]), "xgboost") if CTX.shape[1] else e
    print(f"  {'+ context (nationality, birthplace, sex)':<54} {EXP.shape[1]+CTX.shape[1]:>6} {a:>8.4f} {a-e:>+12.4f}")
    out["exposure_alone"] = e
    out["gains_over_exposure"] = gains
    json.dump(out, open("par-out/final.json", "w"), indent=1)
    g = list(gains.values())
    if g:
        print(f"\n  astrology gain over exposure: mean {sum(g)/len(g):+.4f}, best {max(g):+.4f}, "
              f"helping {sum(1 for x in g if x > 0.005)}/{len(g)}")

    m = LogisticRegression(max_iter=2000).fit(gap, E.Y)
    print(f"\n  the fitted baseline: logit p = {m.intercept_[0]:+.4f} {m.coef_[0][0]:+.5f} * gap_years")
    for gg in (0, 5, 10, 20, 30):
        z = m.intercept_[0] + m.coef_[0][0] * gg
        print(f"    age gap {gg:>2}y -> P(become parents together) {100/(1+np.exp(-z)):.2f}%")


if __name__ == "__main__":
    main()
