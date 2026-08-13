"""
p4_final.py — the deployable model under the four-input contract, against the age-gap baseline.

THE CONTRACT. The model sees exactly four things, any of which may be missing:

    partner A: date of birth, place of birth (latitude, longitude)
    partner B: date of birth, place of birth (latitude, longitude)

Everything derived from those is permitted — the astrology, the date-precision reliability weights, the
cohort/exposure variable, the geometry between the two birthplaces. Citizenship and sex are NOT inputs a
page can collect and are excluded by configuration, not by choice at scoring time.

Reported against the one baseline: a two-parameter logistic on the difference of the two birth dates.

Usage: cd astro && /tmp/aqpy/bin/python p4_final.py
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


def main():
    E = load()
    man, files = run._blocks()
    # The astrology ranking is taken from the earlier full screen on this SAME dataset (par-out). Excluding
    # the nationality module cannot change how the astrology blocks rank against each other, so re-screening
    # 180 blocks with xgboost on 135,000 rows would cost hours to reproduce a list we already have.
    import os as _os
    _prev = "par-out/screen.json"
    scr = json.load(open(_prev if _os.path.exists(_prev) else run.SCREEN))
    astro = [r for r in scr if r.get("kind") != "context"]
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
    GEO = run._get(files, "geo4::geo: EVERYTHING")
    COH = run._get(files, "cohort::coh: EVERYTHING")
    PRC = run._get(files, "precision::prec: EVERYTHING")
    DATES = np.hstack([gap, COH, PRC])            # everything derivable from the two dates alone
    ALL4 = np.hstack([DATES, GEO])                # the full four-input feature set, no astrology
    astro = [r for r in astro if r["key"] in files]
    A = run._get(files, astro[0]["key"])

    print(f"\n  {E.n:,} couples · {int(E.Y.sum()):,} became parents together ({100*E.Y.mean():.1f}%)")
    okA = np.isfinite(E.LAT_O); okB = np.isfinite(E.LAT_Y)
    print(f"  birthplace known: A {100*okA.mean():.1f}% · B {100*okB.mean():.1f}% · both {100*(okA&okB).mean():.1f}%")
    print(f"  birth date known: both {100*np.mean((E.PREC_O>=9)&(E.PREC_Y>=9)):.1f}%\n")
    print(f"  {'model (four inputs only)':<52} {'cols':>6} {'AUC':>8} {'vs baseline':>12}")
    print(f"  {'-'*52} {'-'*6} {'-'*8} {'-'*12}")
    print(f"  {'BASELINE: logistic on the age gap':<52} {'2 par':>6} {base:>8.4f} {'—':>12}")
    out = {"baseline": base, "n": int(E.n), "rate": float(E.Y.mean())}
    for name, M in (("dates only: gap + cohort + precision", DATES),
                    ("places only: two coordinate pairs", GEO),
                    ("ALL FOUR INPUTS, no astrology", ALL4),
                    (f"best astrology block alone ({astro[0]['name'][:20]})", A),
                    ("ALL FOUR INPUTS + best astrology block", np.hstack([ALL4, A]))):
        a = score(M, "xgboost")
        out[name] = {"cols": int(M.shape[1]), "auc": a}
        print(f"  {name:<52} {M.shape[1]:>6} {a:>8.4f} {a-base:>+12.4f}")

    print(f"\n  {'does astrology add to the four inputs?':<52}")
    b4 = out["ALL FOUR INPUTS, no astrology"]["auc"]
    gains = {}
    for r in astro[:6]:
        if r["key"] not in files:
            continue
        X = run._get(files, r["key"])
        a = score(np.hstack([ALL4, X]), "xgboost")
        gains[r["name"]] = a - b4
        print(f"  {'+ ' + r['name'][:50]:<52} {ALL4.shape[1]+X.shape[1]:>6} {a:>8.4f} {a-b4:>+12.4f}")
    out["gains_over_four_inputs"] = gains
    json.dump(out, open("p4-out/final.json", "w"), indent=1)
    g = list(gains.values())
    print(f"\n  astrology gain over the four inputs: mean {sum(g)/len(g):+.4f}, best {max(g):+.4f}, "
          f"helping {sum(1 for x in g if x > 0.005)}/{len(g)}")


if __name__ == "__main__":
    main()
