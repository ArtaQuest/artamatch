"""tilldeath.py — the Till Death Do Us Part reading, scored in the browser under Pyodide.

    score = bias + SUM_t w_t * trig_t(angle_t)          p = 1 / (1 + exp(-score))

Every angle is built from two SIDEREAL birth charts (Lahiri, noon UT) and nothing else: the same
positions the model was fitted on, computed here through the page's own Swiss Ephemeris shim, so
the page and the fit are the same physics rather than two implementations that agree by luck.

The eight angle kinds, all at the fundamental harmonic:

    diff  man[i] - woman[i]      the synastry aspect, his body against hers
    natM  man[i]                 his placement
    natW  woman[i]               her placement
    sum   man[i] + woman[i]      the couple's midpoint axis for that body
    aspM  man[i] - man[j]        his own natal aspect
    aspW  woman[i] - woman[j]    her own natal aspect
    midM  man[i] + man[j]        his own midpoint axis
    midW  woman[i] + woman[j]    her own midpoint axis

`verify()` replays the couples shipped inside tilldeath.json and is what CI runs: a scorer that
drifts from the fit would otherwise show numbers the corpus never produced.
"""
import json
import math

import sweshim as swe

BODY_CODE = {
    "sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY, "venus": swe.VENUS,
    "mars": swe.MARS, "jupiter": swe.JUPITER, "saturn": swe.SATURN, "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE, "pluto": swe.PLUTO, "node": swe.TRUE_NODE,
    "chiron": swe.CHIRON, "lilith": swe.MEAN_APOG,
}
DEG = math.pi / 180.0


FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


def chart(iso, bodies):
    """-> {body: radians} for a YYYY-MM-DD birth date at noon UT, sidereal Lahiri.

    The shim has no FLG_SIDEREAL: sidereal is tropical minus the ayanamsa, which is how
    docs/worked.py does it and how the fit's own charts were built."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    y, m, d = int(iso[0:4]), int(iso[5:7]), int(iso[8:10])
    jd = swe.julday(y, m, d, 12.0)
    aya = swe.get_ayanamsa_ut(jd)
    out = {}
    for b in bodies:
        trop = swe.calc_ut(jd, BODY_CODE[b], FLAGS)[0][0]
        out[b] = ((trop - aya) % 360.0) * DEG
    return out


def _angle(t, bodies, A, B):
    i = bodies[t["i"]]
    j = bodies[t["j"]] if t["j"] is not None else None
    k = t["kind"]
    if k == "diff": return A[i] - B[i]
    if k == "natM": return A[i]
    if k == "natW": return B[i]
    if k == "sum":  return A[i] + B[i]
    if k == "aspM": return A[i] - A[j]
    if k == "aspW": return B[i] - B[j]
    if k == "midM": return A[i] + A[j]
    if k == "midW": return B[i] + B[j]
    raise ValueError(k)


def score(model, man_iso, woman_iso):
    """-> dict(score, p, percentile, drivers). Man first, as the corpus was built."""
    bodies = model["bodies"]
    A = chart(man_iso, bodies)
    B = chart(woman_iso, bodies)
    s = model["bias"]
    parts = []
    for t in model["terms"]:
        a = _angle(t, bodies, A, B)
        c = t["w"] * (math.cos(a) if t["trig"] == "cos" else math.sin(a))
        s += c
        parts.append((abs(c), t["label"], c))
    q = model["quantiles"]
    lo, hi = 0, len(q) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if q[mid] < s:
            lo = mid + 1
        else:
            hi = mid
    parts.sort(reverse=True)
    return {"score": s, "p": 1.0 / (1.0 + math.exp(-s)),
            "percentile": lo / float(len(q) - 1),
            "drivers": [{"label": lb, "contribution": c} for _, lb, c in parts[:8]]}


def verify(model, tol=1e-6):
    """replay the shipped couples; -> (worst_absolute_difference, n)"""
    worst = 0.0
    for v in model["verify"]:
        got = score(model, v["dob_a"], v["dob_b"])["score"]
        worst = max(worst, abs(got - v["score"]))
    return worst, len(model["verify"])


def load(path="/tilldeath.json"):
    with open(path) as f:
        return json.load(f)
