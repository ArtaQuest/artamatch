"""
ctx_cohort.py — birth cohort and EXPOSURE, the variable that censoring actually runs on.

NOT A TRADITION. Named ctx_ so nothing here is reported as an astrological result.

WHY THIS EXISTS. Parenthood as RECORDED collapses for recent cohorts: with the younger partner born in the
1800s the rate is 58.5%, by the 1970s 10.2%, by the 1990s 2.2%. That is not biology. A couple born in the
1980s may not have finished having children, and any child they have has not had time to become notable
enough for Wikidata to hold them.

There are two ways to deal with it. Restrict the sample to cohorts with a complete record — which throws
away most of the data — or keep every row and give the model the censoring variable directly. This module
does the second: EXPOSURE is the years elapsed since the younger partner's birth, i.e. how long this couple
has had for a child to arrive AND to become recorded. A model with exposure in hand can learn the censoring
curve instead of mistaking it for signal, and every cohort stays in the sample.

Also emitted: each partner's birth year and decade, the era in centuries, and interactions with whether the
dates are known at all — because a couple with one unknown birth date has a less certain exposure too.
"""

import numpy as np

TRADITION = "Context: birth cohort and exposure to the censoring window (NOT astrology)"

NOW = 2026.0                 # the year the data was collected; exposure is measured back from here
YR = 365.2425


def build(E):
    n = E.n
    jd = E.JD
    # birth years from the julian days already in the substrate
    yr_o = 1858.0 + (jd[0] - 2400000.5) / YR       # JD 2400000.5 is 1858-11-17
    yr_y = 1858.0 + (jd[1] - 2400000.5) / YR
    younger = np.maximum(yr_o, yr_y)
    older = np.minimum(yr_o, yr_y)
    exposure = np.clip(NOW - younger, 0.0, None)
    known_o = getattr(E, "PREC_O", np.full(n, 11.0)) >= 9
    known_y = getattr(E, "PREC_Y", np.full(n, 11.0)) >= 9
    both = (known_o & known_y).astype(float)

    out = {}
    out["coh: exposure + birth cohort"] = np.column_stack([
        exposure, np.log1p(exposure), exposure ** 2 / 1000.0,
        younger, older, younger - older,
        (younger // 10) * 10, (younger // 25) * 25,
        both, known_o.astype(float), known_y.astype(float),
        # exposure is less trustworthy when a date is missing, so say so explicitly
        exposure * both, exposure * (1.0 - both),
    ])
    # a decade one-hot, so the model can fit an arbitrary censoring curve rather than a smooth one
    dec = np.clip(((younger - 1800) // 10).astype(int), 0, 22)
    oh = np.zeros((n, 23))
    oh[np.arange(n), dec] = 1.0
    out["coh: birth decade one-hot"] = oh
    out["coh: EVERYTHING"] = np.concatenate([out["coh: exposure + birth cohort"], oh], axis=1)
    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick
    E = load()
    bl = build(E)
    bad = 0
    for k, v in bl.items():
        assert v.shape[0] == E.n and v.dtype == np.float64 and np.isfinite(v).all(), k
        if v.std(0).max() <= 0:
            print(f"  {k}: ALL CONSTANT"); bad += 1
        a, u = quick(E, v)
        print(f"  {k:<40} {v.shape[1]:>4} cols   acc {100*a:6.2f}%  AUC {u:.4f}")
    print("OK" if not bad else f"{bad} constant")
    sys.exit(1 if bad else 0)
