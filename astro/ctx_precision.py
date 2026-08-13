"""
ctx_precision.py — what the model needs to stay honest when a birth date is only a year.

THE PROBLEM. 53,897 of the 176,251 couples have at least one birth date known only to the year, and 2,270
only to the month. Those charts are placed at the CENTRE of their uncertainty window rather than at
Wikidata's 1-January placeholder, which is unbiased — but unbiased is not precise, and a model given a
year-precision chart alongside a day-precision one has no way to know which is which. These blocks tell it.

THE KEY QUANTITY IS PER BODY, NOT PER COUPLE. A year of uncertainty does not degrade a chart uniformly: it
annihilates the Sun and Moon while leaving Pluto essentially exact. Averaging cos(theta) over a uniform
window of W days, where the body moves at omega degrees per day, attenuates it by

    sinc(x) = sin(x)/x,     x = omega * W / 2   in radians

which is exact for any circular feature. At year precision that gives, in round numbers:

    Sun      0.00     the Sun's place within a year is simply unknown
    Moon     0.00
    Mercury  0.00
    Venus    0.00
    Mars     0.02
    Jupiter  0.99     one degree of travel per twelve days: a year barely moves it
    Saturn   1.00
    Uranus   1.00
    Neptune  1.00
    Pluto    1.00

So a year-precision couple still carries almost all of its outer-planet information and none of its inner.
That matters here because the blocks that score best on this data are already the slow-cycle ones — Long
Count intervals, goal-year phase, saros. Emitting the attenuation per body per partner lets a tree learn
"trust this body for this couple", which is the honest version of using imprecise rows rather than either
discarding them or pretending they are exact.

Usage: cd /Users/arash/Studio/artamatch/astro && /tmp/aqpy/bin/python ctx_precision.py
"""

import numpy as np

TRADITION = "Context: date precision and per-body reliability (NOT astrology)"

# mean motion in degrees per day, the quantity that decides how fast uncertainty destroys a position
DEG_PER_DAY = {
    "Sun": 0.98561, "Moon": 13.17640, "Mercury": 4.09234, "Venus": 1.60213, "Mars": 0.52403,
    "Jupiter": 0.08309, "Saturn": 0.03346, "Uranus": 0.01176, "Neptune": 0.00602, "Pluto": 0.00397,
    "TrueNode": 0.05295, "MeanNode": 0.05295, "Lilith": 0.11140, "Chiron": 0.01955,
    "Ceres": 0.21400, "Pallas": 0.21300, "Juno": 0.22600, "Vesta": 0.27100,
}


def sinc_atten(omega_deg_per_day, window_days):
    """sin(x)/x with x = omega*W/2 in radians — the exact attenuation of a circular feature."""
    x = np.deg2rad(np.asarray(omega_deg_per_day) * np.asarray(window_days) / 2.0)
    return np.where(np.abs(x) < 1e-9, 1.0, np.sin(x) / np.where(np.abs(x) < 1e-9, 1.0, x))


def build(E):
    n = E.n
    out = {}
    pO, pY = E.PREC_O, E.PREC_Y
    wO, wY = E.WIN_O, E.WIN_Y

    # ── precision itself ──────────────────────────────────────────────────────────────────────────
    onehot = np.column_stack([
        (pO >= 11).astype(float), (pO == 10).astype(float), (pO <= 9).astype(float),
        (pY >= 11).astype(float), (pY == 10).astype(float), (pY <= 9).astype(float),
        ((pO >= 11) & (pY >= 11)).astype(float),          # both exact
        ((pO <= 9) | (pY <= 9)).astype(float),            # at least one is year-only
        np.minimum(pO, pY), np.maximum(pO, pY), np.abs(pO - pY),
        np.log1p(wO), np.log1p(wY), np.log1p(np.maximum(wO, wY)),
    ])
    out["prec: date precision + window width"] = onehot

    # ── per-body reliability, which is the whole point ────────────────────────────────────────────
    names = [b for b in E.NAME]
    AO = np.column_stack([sinc_atten(DEG_PER_DAY.get(b, 1.0), wO) for b in names])
    AY = np.column_stack([sinc_atten(DEG_PER_DAY.get(b, 1.0), wY) for b in names])
    out["prec: per-body attenuation, older"] = AO
    out["prec: per-body attenuation, younger"] = AY
    # a synastry contact between two bodies is only as good as the worse of the two, and the product is
    # what actually multiplies a cos(theta_a - theta_b) term
    out["prec: pairwise contact reliability"] = np.einsum("ij,ik->ijk", AO, AY).reshape(n, -1)
    out["prec: worst-case body reliability"] = np.minimum(AO, AY)

    out["prec: EVERYTHING"] = np.concatenate(
        [onehot, AO, AY, np.minimum(AO, AY)], axis=1)
    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick
    E = load()
    print("\nattenuation of a circular feature by date precision (1.0 = unaffected, 0 = destroyed):")
    print(f"  {'body':<10} {'day':>7} {'month':>7} {'year':>7}")
    for b in E.NAME:
        w = DEG_PER_DAY.get(b, 1.0)
        print(f"  {b:<10} {sinc_atten(w,1):>7.3f} {sinc_atten(w,31):>7.3f} {sinc_atten(w,366):>7.3f}")
    bl = build(E)
    bad = 0
    print()
    for k, v in bl.items():
        assert v.shape[0] == E.n and v.dtype == np.float64 and np.isfinite(v).all(), k
        if v.std(0).max() <= 0:
            print(f"  {k}: ALL CONSTANT"); bad += 1
        a, u = quick(E, v)
        print(f"  {k:<42} {v.shape[1]:>5} cols   acc {100*a:6.2f}%  AUC {u:.4f}")
    print("OK" if not bad else f"{bad} constant blocks")
    sys.exit(1 if bad else 0)
