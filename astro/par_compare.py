"""
par_compare.py — the clean target, measured against the one baseline: a two-parameter logistic on the
difference of the two birth dates.

    logit P(became parents together) = b0 + b1 * (age gap in years)

The target is the first non-circular one in this project: 29,484 opposite-sex couples that Wikidata
DECLARES a relationship for, both partners independently notable, the younger born 1900-1950 so the
record is complete, and the label taken from a different set of statements than the membership.

Usage: cd astro && /tmp/aqpy/bin/python par_compare.py
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
import ctx_nationality as CN
import ctx_precision as CP

YR = 365.2425


def main():
    E = load()
    man, files = run._blocks()
    scr = json.load(open(run.SCREEN))
    astro = [r for r in scr if r.get("kind") != "context"]
    ctxb = [r for r in scr if r.get("kind") == "context"]
    bestA, bestC = astro[0]["key"], ctxb[0]["key"]
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
    A = run._get(files, bestA)
    C = run._get(files, bestC)
    print(f"\n  {E.n:,} couples · {int(E.Y.sum()):,} became parents together ({100*E.Y.mean():.1f}%)\n")
    print(f"  {'model':<52} {'cols':>6} {'AUC':>8} {'vs baseline':>12}")
    print(f"  {'-'*52} {'-'*6} {'-'*8} {'-'*12}")
    print(f"  {'BASELINE: logistic on the age gap':<52} {'2 par':>6} {base:>8.4f} {'—':>12}")
    rows = [
        (f"best astrology block ({bestA.split('::')[1][:26]})", A, "xgboost"),
        ("best context block (nationality, birthplace, sex)", C, "xgboost"),
        ("astrology + context", np.hstack([A, C]), "xgboost"),
        ("age gap + best astrology block", np.hstack([gap, A]), "xgboost"),
        ("age gap + context", np.hstack([gap, C]), "xgboost"),
        ("age gap + context + astrology", np.hstack([gap, C, A]), "xgboost"),
    ]
    out = {"baseline_agegap_2param": base, "target_rate": float(E.Y.mean()), "n": int(E.n)}
    for name, M, mdl in rows:
        a = score(M, mdl)
        out[name] = {"cols": int(M.shape[1]), "auc": a}
        print(f"  {name:<52} {M.shape[1]:>6} {a:>8.4f} {a-base:>+12.4f}")
    json.dump(out, open("par-out/compare.json", "w"), indent=1)

    m = LogisticRegression(max_iter=2000).fit(gap, E.Y)
    print(f"\n  the fitted baseline: logit p = {m.intercept_[0]:+.4f} {m.coef_[0][0]:+.5f} * gap_years")
    for g in (0, 2, 5, 10, 20, 30):
        z = m.intercept_[0] + m.coef_[0][0] * g
        print(f"    age gap {g:>2}y -> P(become parents together) {100/(1+np.exp(-z)):.2f}%")


if __name__ == "__main__":
    main()
