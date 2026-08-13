"""
agegap.py — the one baseline: a two-parameter logistic regression on the difference of the two birth dates.

    logit P(prominent child) = b0 + b1 * (age gap in years)

Two parameters, one feature, no astrology, no context, no ephemeris. This is the reference point every
other model is measured against from here on. Fitted and scored under the same person-disjoint 5-fold
GroupKFold as everything else, so the numbers are directly comparable.

Usage: cd astro && /tmp/aqpy/bin/python agegap.py
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
from selfserve import form_context

YR = 365.2425
BEST_ASTRO = "uranian::ura: hypotheticals dial positions & cross contacts"


def main():
    E = load()
    man, files = run._blocks()
    gap = ((E.JD[1] - E.JD[0]) / YR)[:, None]
    era = ((E.JD[5] - E.JD[5].min()) / YR)[:, None]
    folds = list(GroupKFold(n_splits=5).split(np.zeros(E.n), E.Y, groups=E.gid))

    def score(M, model=None):
        p = np.zeros(E.n)
        for tr, te in folds:
            if model is None:
                mdl = LogisticRegression(max_iter=2000)      # exactly two parameters: b0 and b1
                mdl.fit(M[tr], E.Y[tr])
                p[te] = mdl.predict_proba(M[te])[:, 1]
            else:
                mdl = run.pipe("raw", M.shape[1], MODELS(M.shape[1])[model])
                mdl.fit(M[tr], E.Y[tr])
                p[te] = evalx._proba(mdl, M[te])
        return float(roc_auc_score(E.Y, p))

    base = score(gap)
    print(f"\n  {E.n:,} couples · {int(E.Y.sum()):,} with a prominent child ({100*E.Y.mean():.1f}%)\n")
    print(f"  {'model':<52} {'params/cols':>12} {'AUC':>8} {'vs baseline':>12}")
    print(f"  {'-'*52} {'-'*12} {'-'*8} {'-'*12}")
    print(f"  {'BASELINE: logistic on the age gap':<52} {'2 params':>12} {base:>8.4f} {'—':>12}")

    rows = []
    FC = form_context(E)
    A = run._get(files, BEST_ASTRO)
    rows.append(("best astrology block alone (Uranian dials)", A.shape[1], score(A, "xgboost")))
    rows.append(("every astrology block that scored best, pooled",
                 None, None))
    rows.append(("age gap + era", 2, score(np.hstack([gap, era]), "xgboost")))
    rows.append(("age gap + era + birth country, sex, precision", 2 + FC.shape[1],
                 score(np.hstack([gap, era, FC]), "xgboost")))
    rows.append(("…and the best astrology block on top", 2 + FC.shape[1] + A.shape[1],
                 score(np.hstack([gap, era, FC, A]), "xgboost")))
    out = {"baseline_agegap_2param": base}
    for name, cols, auc in rows:
        if auc is None:
            continue
        out[name] = {"cols": cols, "auc": auc}
        print(f"  {name:<52} {str(cols):>12} {auc:>8.4f} {auc-base:>+12.4f}")
    json.dump(out, open("max-out/agegap-baseline.json", "w"), indent=1)

    # what the two parameters actually say
    mdl = LogisticRegression(max_iter=2000).fit(gap, E.Y)
    print(f"\n  the fitted baseline: logit p = {mdl.intercept_[0]:+.4f} {mdl.coef_[0][0]:+.5f} * gap_years")
    for g in (0, 2, 5, 10, 20, 30):
        z = mdl.intercept_[0] + mdl.coef_[0][0] * g
        print(f"    age gap {g:>2}y -> P(prominent child) {100/(1+np.exp(-z)):.2f}%")


if __name__ == "__main__":
    main()
