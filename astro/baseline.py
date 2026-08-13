"""
baseline.py — the ONE permitted non-astrology baseline for ArtaMatch.

    logit P(became parents together) = b0 + b1 * (dob_woman - dob_man)      in years, SIGNED

Two parameters, one feature, and the feature is the literal subtraction of the two birth dates. The sign
carries real information and an absolute value throws it away: in this data the man is older in 75% of
couples, and man-older and woman-older behave differently. Positive means the man is older.

Nothing else is a baseline here. Exposure, cohort, nationality, birthplace country and sex are model
FEATURES when the input contract allows them; they are never the reference point.

Usage: cd astro && /tmp/aqpy/bin/python baseline.py
"""

import json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from core import load

YR = 365.2425


def signed_gap(E):
    """dob_woman - dob_man, in years. Slots 0/1 are older/younger, so the sex decides the sign."""
    raw = (E.JD[1] - E.JD[0]) / YR                 # always >= 0: younger minus older
    older_is_man = (E.SEX_O.astype(str) == "M")
    return np.where(older_is_man, raw, -raw)


def main():
    E = load()
    g = signed_gap(E)
    folds = list(GroupKFold(n_splits=5).split(np.zeros(E.n), E.Y, groups=E.gid))
    print(f"\n  {E.n:,} couples · {int(E.Y.sum()):,} became parents together ({100*E.Y.mean():.1f}%)")
    print(f"  signed gap: min {g.min():+.1f}y  median {np.median(g):+.1f}y  max {g.max():+.1f}y")
    print(f"  the man is older in {100*(g > 0).mean():.1f}% of couples\n")

    out = {}
    for name, X in (("SIGNED gap (dob_woman - dob_man)", g[:, None]),
                    ("unsigned |gap|, for contrast only", np.abs(g)[:, None])):
        p = np.zeros(E.n)
        for tr, te in folds:
            m = LogisticRegression(max_iter=2000).fit(X[tr], E.Y[tr])
            p[te] = m.predict_proba(X[te])[:, 1]
        auc = float(roc_auc_score(E.Y, p))
        out[name] = auc
        m = LogisticRegression(max_iter=2000).fit(X, E.Y)
        print(f"  {name:<40} AUC {auc:.4f}   "
              f"logit p = {m.intercept_[0]:+.4f} {m.coef_[0][0]:+.5f} * x")
    json.dump(out, open("baseline.json", "w"), indent=1)

    m = LogisticRegression(max_iter=2000).fit(g[:, None], E.Y)
    print(f"\n  the baseline curve (positive = the man is older):")
    for v in (-20, -10, -5, 0, 5, 10, 20, 30):
        z = m.intercept_[0] + m.coef_[0][0] * v
        who = "woman older" if v < 0 else ("same age" if v == 0 else "man older")
        print(f"    {v:>+4d}y  {who:<12} P(become parents together) {100/(1+np.exp(-z)):.2f}%")

    print("\n  observed rate by signed gap, as a check on the fitted line:")
    for lo, hi in ((-60, -10), (-10, -5), (-5, -2), (-2, 2), (2, 5), (5, 10), (10, 20), (20, 60)):
        s = (g >= lo) & (g < hi)
        if s.sum() >= 300:
            print(f"    [{lo:>+4d},{hi:>+4d})  {int(s.sum()):>7,} couples   {100*E.Y[s].mean():>5.1f}%")


if __name__ == "__main__":
    main()
