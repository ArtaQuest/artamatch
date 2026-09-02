"""tilldeath.py — the Till Death Do Us Part reading, scored in the browser under Pyodide.

    score = bias + SUM_t w_t * trig_t(angle_t)          p = 1 / (1 + exp(-score))

Every angle is built from two SIDEREAL birth charts (Lahiri, noon UT) and nothing else: the same
positions the model was fitted on, computed here through the page's own Swiss Ephemeris shim, so
the page and the fit are the same physics rather than two implementations that agree by luck.

The angle kinds, all at the fundamental harmonic:

    diff  man[i] - woman[i]      the synastry aspect, his body against hers
    natM  man[i]                 his placement
    natW  woman[i]               her placement
    sum   man[i] + woman[i]      the couple's midpoint axis for that body
    aspM  man[i] - man[j]        his own natal aspect
    aspW  woman[i] - woman[j]    her own natal aspect
    midM  man[i] + man[j]        his own midpoint axis
    midW  woman[i] + woman[j]    her own midpoint axis
    xdiff man[i] - woman[j]      the cross-body synastry aspect
    xsum  man[i] + woman[j]      the cross-body couple midpoint
    camp  (man[i]+woman[i]) - (man[j]+woman[j])   an aspect inside the composite chart
    ddm   d_i - d_j    ddp  d_i + d_j    ssp  s_i + s_j    dsm  d_i - s_j    dsp  d_i + s_j
          where d_i = man[i] - woman[i] and s_i = man[i] + woman[i]

Every term also carries a HARMONIC k (absent means 1): the feature is cos(k*angle) or sin(k*angle).
k=12 is the 30-degree sign structure, k=27 the nakshatra, k=36 the decan — so the whole tradition is
expressed sinusoidally and no indicator column is ever needed.

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


def chart(iso, bodies, female=False):
    """-> {body: radians} for a YYYY-MM-DD birth date at noon UT, sidereal Lahiri.

    The shim has no FLG_SIDEREAL: sidereal is tropical minus the ayanamsa, which is how
    docs/worked.py does it and how the fit's own charts were built. `female` matters only to the
    gendered pseudo-body (Kua), whose rule differs for men and women."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    y, m, d = int(iso[0:4]), int(iso[5:7]), int(iso[8:10])
    jd = swe.julday(y, m, d, 12.0)
    aya = swe.get_ayanamsa_ut(jd)
    out = {}
    sid = lambda b: (swe.calc_ut(jd, BODY_CODE[b], FLAGS)[0][0] - aya) % 360.0
    st = None
    for b in bodies:
        if b in SYSTEM_STATES:
            if st is None:
                st = system_states(y, m, d, sid("sun"), sid("moon"), aya, female)
            out[b] = (st[b] + 1) * 360.0 / SYSTEM_STATES[b] * DEG
            continue
        out[b] = sid(b) * DEG
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
    # PAIR-ONLY kinds (2026-09-01): each needs BOTH charts, so none can be evaluated for a single
    # person — which is exactly what makes them the only admissible features for a pair claim.
    if k == "xdiff": return A[i] - B[j]
    if k == "xsum":  return A[i] + B[j]
    if k == "camp":  return (A[i] + B[i]) - (A[j] + B[j])
    # The rest of the two-body pair space, in terms of d = man - woman and s = man + woman.
    if k == "ddm":   return (A[i] - B[i]) - (A[j] - B[j])
    if k == "ddp":   return (A[i] - B[i]) + (A[j] - B[j])
    if k == "ssp":   return (A[i] + B[i]) + (A[j] + B[j])
    if k == "dsm":   return (A[i] - B[i]) - (A[j] + B[j])
    if k == "dsp":   return (A[i] - B[i]) + (A[j] + B[j])
    raise ValueError(k)


def score(model, man_iso, woman_iso):
    """-> dict(score, p, percentile, drivers). Man first, as the corpus was built."""
    bodies = model["bodies"]
    A = chart(man_iso, bodies)
    B = chart(woman_iso, bodies, female=True)
    s = model["bias"]
    parts = []
    for t in model["terms"]:
        # THE HARMONIC. k=1 is the aspect itself; k=12 is the 30-degree sign structure, k=27 the
        # nakshatra, k=36 the decan. Absent means 1, so a model written before harmonics existed
        # still scores identically through this path.
        a = _angle(t, bodies, A, B) * t.get("k", 1)
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
    # the same score placed among couples whose husband was born in the same decade — the
    # calendar-fair percentile. Absent when the model file predates it or the decade is thin.
    era = None
    qd = (model.get("quantiles_by_decade") or {}).get(str(int(man_iso[:4]) // 10 * 10))
    if qd:
        elo, ehi = 0, len(qd) - 1
        while elo < ehi:
            mid = (elo + ehi) // 2
            if qd[mid] < s: elo = mid + 1
            else: ehi = mid
        era = elo / float(len(qd) - 1)
    return {"score": s, "p": 1.0 / (1.0 + math.exp(-s)),
            "percentile": lo / float(len(q) - 1), "percentile_era": era,
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


# ── EVERY DATE-ONLY SYSTEM AS A PSEUDO-BODY (operator 2026-09-02). A system's state is an angle on
# its own circle: state s of N -> s * 360/N (a life path of 1 is 40 degrees). This is the SAME code
# as kaggle/build_systems.py, to the digit — the corpus and this page must agree, or the shipped
# replay of 200 couples refuses the model file. The Chinese year begins at Li Chun (tropical Sun
# 315 degrees), never on 1 January; Kua is gendered by rule; offsets in a cycle are absorbed by
# the fitted phase, lengths and boundaries are exact.
SYSTEM_STATES = {"num_lifepath": 9, "num_birthday": 31, "num_birthday_reduced": 9, "num_attitude": 9,
                 "cn_year_animal": 12, "cn_year_stem": 10, "cn_day_stem": 10, "cn_day_branch": 12,
                 "cn_day_nayin": 30, "cn_kua": 9, "nine_star": 9, "nine_star_month": 9,
                 "tz_sign": 20, "tz_tone": 13, "haab_month": 19, "lord_night": 9,
                 "vedic_yoga": 27, "vedic_dasha_lord": 9, "manzil": 28, "weekday": 7}

def _jdn(y, m, d):
    a = (14 - m) // 12; yy = y + 4800 - a; mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045

def _red9(t):
    while t > 9:
        t = sum(int(c) for c in str(t))
    return t

def _ninestar_year(cy):
    return 1 + (11 - (1 + (sum(int(c) for c in str(cy)) - 1) % 9) - 1) % 9

def system_states(y, m, d, sid_sun, sid_moon, aya, female):
    j = _jdn(y, m, d); sx = (j + 49) % 60; k = (j - 584283) % 260
    trop_sun = (sid_sun + aya) % 360.0
    cy = y - 1 if (m <= 2 and trop_sun < 315.0) else y
    ys = _ninestar_year(cy)
    month_idx = int(((trop_sun - 315.0) % 360.0) // 30.0)
    feb = {1: 8, 4: 8, 7: 8, 2: 5, 5: 5, 8: 5, 3: 2, 6: 2, 9: 2}[ys]
    mstar = ((feb - month_idx - 1) % 9) + 1
    s = _red9(sum(int(c) for c in str(cy)))
    if cy < 2000:
        kua = _red9(5 + s) if female else _red9(10 - s)
    else:
        kua = _red9(6 + s) if female else _red9(9 - s)
    if kua == 5:
        kua = 8 if female else 2
    nak = int(sid_moon // (360.0 / 27.0))
    return {"num_lifepath": _red9(sum(int(c) for c in "%04d%02d%02d" % (y, m, d))) - 1,
            "num_birthday": d - 1, "num_birthday_reduced": _red9(d) - 1, "num_attitude": _red9(m + d) - 1,
            "cn_year_animal": (cy - 4) % 12, "cn_year_stem": (cy - 4) % 10,
            "cn_day_stem": sx % 10, "cn_day_branch": sx % 12, "cn_day_nayin": (sx // 2) % 30,
            "cn_kua": kua - 1, "nine_star": ys - 1, "nine_star_month": mstar - 1,
            "tz_sign": k % 20, "tz_tone": k % 13, "haab_month": ((j - 584283 + 348) % 365) // 20,
            "lord_night": (j - 584283) % 9,
            "vedic_yoga": int(((sid_sun + sid_moon) % 360.0) // (360.0 / 27.0)),
            "vedic_dasha_lord": nak % 9, "manzil": int(sid_moon // (360.0 / 28.0)),
            "weekday": (j + 1) % 7}
