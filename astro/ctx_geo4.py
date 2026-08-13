"""
ctx_geo4.py — the ONLY non-date context the deployed model is allowed: two birthplaces as real coordinates.

THE INPUT CONTRACT is exactly four things, each of which may be missing:

    partner A: date of birth, place of birth
    partner B: date of birth, place of birth

Nothing else. No citizenship, no country one-hot, no sex, no marriage date. That rules out the block that
had been carrying most of the context gain — citizenship one-hots over 90 states — and it is the right
call for a page a stranger fills in: nobody is asked for their citizenship history, and the multi-valued
historical-state version the model trained on is not something a form could collect anyway.

PLACE IS EMBEDDED AS TWO REAL NUMBERS, latitude and longitude, not as a category. A country one-hot cannot
say that Lyon is near Geneva, and it forces a fixed vocabulary that breaks on any place the training set
never saw. Two floats generalise to anywhere on Earth and let the model use actual geography: the
great-circle distance between the two birthplaces, the latitude difference, which hemisphere each is in.

MISSINGNESS is explicit, never imputed. A coordinate that is unknown ships as 0 WITH a flag saying so, so
a tree can split on "unknown" instead of treating the equator and the prime meridian as a real birthplace.

Usage: cd astro && /tmp/aqpy/bin/python ctx_geo4.py
"""

import numpy as np

TRADITION = "Context: two birthplaces as real coordinates (the only non-date input)"
R_EARTH = 6371.0


def build(E):
    n = E.n
    la, lo = E.LAT_O, E.LON_O
    lb, lob = E.LAT_Y, E.LON_Y
    okA = np.isfinite(la) & np.isfinite(lo)
    okB = np.isfinite(lb) & np.isfinite(lob)
    both = okA & okB
    LA, LO = np.nan_to_num(la), np.nan_to_num(lo)
    LB, LOB = np.nan_to_num(lb), np.nan_to_num(lob)

    # great-circle distance between the two birthplaces, defined only when both are known
    p1, p2 = np.radians(LA), np.radians(LB)
    dl = np.radians(LOB - LO)
    hav = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    dist = 2 * R_EARTH * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))
    dist = np.where(both, dist, 0.0)

    raw = np.column_stack([
        LA, LO, okA.astype(float),                       # partner A's place, and whether it is known
        LB, LOB, okB.astype(float),                      # partner B's place
        both.astype(float),
        dist, np.log1p(dist),
        np.where(both, np.abs(LA - LB), 0.0),            # latitude difference — climate, day length
        np.where(both, np.abs(((LOB - LO + 180) % 360) - 180), 0.0),   # longitude difference, wrapped
        (LA >= 0).astype(float) * okA, (LB >= 0).astype(float) * okB,  # northern hemisphere flags
        np.where(both, ((LA >= 0) == (LB >= 0)).astype(float), 0.0),   # same hemisphere
        # a smooth encoding of position on the sphere, so the model is not forced to learn a step function
        np.cos(np.radians(LA)) * okA, np.sin(np.radians(LA)) * okA,
        np.cos(np.radians(LO)) * okA, np.sin(np.radians(LO)) * okA,
        np.cos(np.radians(LB)) * okB, np.sin(np.radians(LB)) * okB,
        np.cos(np.radians(LOB)) * okB, np.sin(np.radians(LOB)) * okB,
    ])
    out = {"geo: two birthplaces as coordinates": raw}
    out["geo: EVERYTHING"] = raw
    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick
    E = load()
    bl = build(E)
    okA = np.isfinite(E.LAT_O)
    okB = np.isfinite(E.LAT_Y)
    print(f"  birthplace known: partner A {100*okA.mean():.1f}% · B {100*okB.mean():.1f}% · "
          f"both {100*(okA & okB).mean():.1f}%")
    bad = 0
    for k, v in bl.items():
        assert v.shape[0] == E.n and v.dtype == np.float64 and np.isfinite(v).all(), k
        if v.std(0).max() <= 0:
            print(f"  {k}: ALL CONSTANT"); bad += 1
        a, u = quick(E, v)
        print(f"  {k:<40} {v.shape[1]:>4} cols   acc {100*a:6.2f}%  AUC {u:.4f}")
    print("OK" if not bad else f"{bad} constant")
    sys.exit(1 if bad else 0)
