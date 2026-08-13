"""
increment.py — the question that decides whether there is an astrology product here at all.

WHY THIS FILE EXISTS. The best model the whole sweep produced was xgboost on a four-column block named
"meso: distance numbers (LC intervals)" plus a context block. Inspecting those four columns:

    col 0  older's age at the "wedding"    |r| with the age gap = 1.0000
    col 1  younger's age at the "wedding"  |r| with the age gap = 1.0000
    col 2  the gap between the births      |r| with the age gap = 1.0000
    col 3  katun position in the era       |r| with the era     = 1.0000

Columns 0, 1 and 2 correlate with EACH OTHER at r = 1.000000 — they are one quantity written three times,
because in DOB-only mode the "wedding" slot holds the Davison midpoint, which sits exactly halfway between
the two births. The 360-day tun divisor is a linear rescaling and changes nothing. Replacing the block with
two plain numbers, (age gap, era), scored 0.6860 against the block's 0.6852 — very slightly BETTER.

So the sweep's winner is age gap + era + birth country + sex, and the module's own comment says as much:
"Quarantined in their own tiny block because these are ages, not divination."

THE TEST. Take (age gap, era, form context) as the thing to beat and ask whether ANY astrology block adds
to it. Every block here is also a function of the two birth dates, so each can re-encode the gap and the
era; the increment is the only way to see whether it carries anything else. If the increments are ~0, a page
branded as astrology would be a page whose engine is an age gap, and that is not shippable.

Usage: cd astro && /tmp/aqpy/bin/python increment.py
"""

import json
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from core import load
import evalx
from evalx import MODELS
import run
from selfserve import form_context

TOP = [
    "uranian::ura: hypotheticals dial positions & cross contacts",
    "lunar_calendrical::lun: saros/inex/metonic/callippic + computus",
    "babylonian_egyptian::bab+egy: schematic 360-day & Egyptian civil calendars",
    "harmonics::har: ecliptic latitude contacts",
    "harmonics::har: declination parallels + out-of-bounds",
    "lunar_calendrical::lun: 45 pair synodic phases, births + diff",
    "modern_western::mod: Davison chart + composite dispute",
    "babylonian_egyptian::bab: goal-year phase, circular",
]
YR = 365.2425


def main():
    E = load()
    man, files = run._blocks()
    gap = (E.JD[1] - E.JD[0]) / YR
    era = (E.JD[5] - E.JD[5].min()) / YR
    FC = form_context(E)
    BASE = np.column_stack([gap, era, FC])
    folds = list(GroupKFold(n_splits=5).split(np.zeros(E.n), E.Y, groups=E.gid))

    def auc(M, model="xgboost"):
        p = np.zeros(E.n)
        f = MODELS(M.shape[1])[model]
        for tr, te in folds:
            m = run.pipe("raw", M.shape[1], f)
            m.fit(M[tr], E.Y[tr])
            p[te] = evalx._proba(m, M[te])
        return float(roc_auc_score(E.Y, p))

    out = {}
    out["age gap + era ONLY (2 cols)"] = auc(np.column_stack([gap, era]))
    out["form context ONLY"] = auc(FC)
    b = auc(BASE)
    out["BASELINE: age gap + era + form context"] = b
    print(f"  {'reference point':<50} {'cols':>5} {'AUC':>8}")
    print(f"  {'-'*50} {'-'*5} {'-'*8}")
    print(f"  {'age gap + era only':<50} {2:>5} {out['age gap + era ONLY (2 cols)']:>8.4f}")
    print(f"  {'form context only (country, sex, precision)':<50} {FC.shape[1]:>5} {out['form context ONLY']:>8.4f}")
    print(f"  {'BASELINE: age gap + era + form context':<50} {BASE.shape[1]:>5} {b:>8.4f}")
    print()
    print(f"  {'+ astrology block on top of the baseline':<50} {'cols':>5} {'AUC':>8} {'gain':>8}")
    print(f"  {'-'*50} {'-'*5} {'-'*8} {'-'*8}")
    gains = {}
    for k in TOP:
        if k not in files:
            continue
        X = run._get(files, k)
        a = auc(np.concatenate([BASE, X], axis=1))
        gains[k] = a - b
        print(f"  {k.split('::')[1][:50]:<50} {X.shape[1]:>5} {a:>8.4f} {a-b:>+8.4f}", flush=True)
    out["gains"] = gains
    json.dump(out, open("max-out/astro-increment.json", "w"), indent=1)
    g = list(gains.values())
    if g:
        print(f"\n  mean gain {sum(g)/len(g):+.4f} · best {max(g):+.4f} · "
              f"blocks that help at all: {sum(1 for x in g if x > 0)}/{len(g)}")
        print(f"  split-to-split noise on this design is roughly +-0.005 AUC, so a gain under about")
        print(f"  0.01 is not a gain.")


if __name__ == "__main__":
    main()
