"""systems_western.py — WESTERN & HELLENISTIC date-only systems as PSEUDO-BODIES (lens "western").

Every system is a PURE function fn(y, m, d, L) -> int state in [0, N-1], standard library only, so
the very same code runs in the browser under Pyodide. L is that person's SIDEREAL (Lahiri) longitudes
in degrees at 12:00 UT, {"sun":..., "moon":..., "mercury":..., "venus":..., "mars":..., "jupiter":...,
"saturn":..., "uranus":..., "neptune":..., "pluto":..., "node":..., "chiron":..., "lilith":...}.
Tropical = sidereal + ayanamsa(y); the ayanamsa is the linear Lahiri fit good to a few arcminutes,
which never moves a state except within arcminutes of a boundary (documented, accepted).

The fitter maps state s of N to the angle (s+1)*360/N on that system's own circle (build_systems.py
convention); this module only returns the state. Nothing here is a raw longitude — the bank already
carries every planet as a continuous angle — every system is a DISCRETISATION or a RE-LABELLING of
one, or a function of the Sun-Moon elongation, or of the calendar day.

SYSTEMS (all date-computable; the Part of Fortune, the sect of the chart, the planetary HOUR and the
triplicity lord "by sect" need a birth time and are deliberately absent):

  per body (13 bodies: sun moon mercury venus mars jupiter saturn uranus neptune pluto node chiron lilith)
    western_sign_<b>        12  tropical zodiac sign, Aries = 0
    western_decan_<b>       36  tropical decan (10-degree third of the sign), Aries I = 0
    western_face_<b>         7  Chaldean face (decan) RULER: Mars rules Aries I, then the Chaldean
                                sequence Saturn Jupiter Mars Sun Venus Mercury Moon repeats (Ptolemy)
    western_term_<b>        60  Egyptian term (bound) POSITION, 5 unequal terms per sign, in order
    western_term_ruler_<b>   5  Egyptian term RULER: Mercury Venus Mars Jupiter Saturn
    western_element_<b>      4  triplicity/element: fire earth air water
    western_modality_<b>     3  cardinal fixed mutable
    western_gender_<b>       2  sign gender: masculine (odd signs) / feminine (even)
    western_domicile_<b>     7  domicile RULER of the sign, traditional (Chaldean index)
    western_trip_day_<b>     7  Dorothean triplicity DAY lord of the sign's element
    western_trip_night_<b>   7  Dorothean triplicity NIGHT lord
    western_trip_part_<b>    7  Dorothean triplicity PARTICIPATING lord
  per classical planet (7: sun .. saturn)
    western_dignity_<p>      5  essential dignity by sign: domicile exaltation peregrine fall detriment
  lunar
    western_phase8           8  lunar phase from the Moon-Sun elongation, 45-degree phases centred
                                on the new moon (new crescent first-quarter gibbous full ...)
    western_phase30         30  fine lunar state, 12-degree steps of elongation from the new moon
    western_waxing           2  waxing (elongation < 180) / waning
    western_mansion         28  Arabic lunar mansion (manzil) of the TROPICAL Moon, 12 6/7 degrees each
                                from 0 Aries (Agrippa's table; the sidereal one is build_systems.py's)
  calendar
    western_weekday          7  day of the week, Sunday = 0 (Fliegel-Van Flandern JDN, +1 mod 7)
    western_day_ruler        7  the day's planetary ruler on the CHALDEAN circle (Saturn = 0 ...
                                Moon = 6): Sunday Sun, Monday Moon, Tuesday Mars, Wednesday Mercury,
                                Thursday Jupiter, Friday Venus, Saturday Saturn
    western_night_ruler      7  the ruler of the FIRST HOUR OF THE NIGHT (the 13th planetary hour,
                                12 Chaldean steps on from the day ruler = +5 mod 7): Sunday night
                                Jupiter, Monday Venus, Tuesday Saturn, Wednesday Sun, Thursday Moon,
                                Friday Mars, Saturday Mercury

Chaldean index used everywhere a planet is a state: Saturn 0, Jupiter 1, Mars 2, Sun 3, Venus 4,
Mercury 5, Moon 6 (descending speed, the order of the planetary hours).

Run as a script: smoke-tests every system on dates 1600-2000 with synthetic longitudes; with
AQ_BUILD=1 also writes AQ_DIR/systems_western.npz in the build_systems.py shape (theta_a_sys,
theta_b_sys in degrees, names, nstates) for AQ_SYSTEMS=1 AQ_SYSTEMS_FILE=systems_western.npz.
"""
import os

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
          "pluto", "node", "chiron", "lilith"]
CLASSICAL = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]

# ---- helpers ---------------------------------------------------------------------------------------
def jdn(y, m, d):
    """Julian Day Number of a proleptic-Gregorian civil date (Fliegel & Van Flandern 1968)."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045

def ayanamsa(y):
    """Lahiri ayanamsa in degrees, linear fit (good to a few arcminutes 1600-2100)."""
    return 23.853 + 0.013971 * (y - 2000)

def tropical(y, L, body):
    """Tropical longitude of a body in [0, 360)."""
    return (float(L[body]) + ayanamsa(y)) % 360.0

# ---- tables ----------------------------------------------------------------------------------------
CHALDEAN = ["saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon"]
CH = {p: i for i, p in enumerate(CHALDEAN)}
# Domicile rulers, Aries .. Pisces (traditional, no modern rulers)
DOMICILE = ["mars", "venus", "mercury", "moon", "sun", "mercury",
            "venus", "mars", "jupiter", "saturn", "saturn", "jupiter"]
# Exaltations by sign (Ptolemy): Sun Aries, Moon Taurus, Mercury Virgo, Venus Pisces, Mars Capricorn,
# Jupiter Cancer, Saturn Libra
EXALT = {"sun": 0, "moon": 1, "mercury": 5, "venus": 11, "mars": 9, "jupiter": 3, "saturn": 6}
# Element of each sign (Aries fire, Taurus earth, Gemini air, Cancer water, repeating)
ELEMENT = ["fire", "earth", "air", "water"]
# Dorothean triplicity lords: element -> (day, night, participating)
TRIPLICITY = {"fire": ("sun", "jupiter", "saturn"),
              "earth": ("venus", "moon", "mars"),
              "air": ("saturn", "mercury", "jupiter"),
              "water": ("venus", "mars", "moon")}
# Egyptian terms (bounds), Ptolemy Tetrabiblos I.21 "the Egyptian system": per sign, five
# (ruler, upper bound in degrees within the sign) in order. Upper bounds are exclusive.
TERMS = [
    [("jupiter", 6), ("venus", 12), ("mercury", 20), ("mars", 25), ("saturn", 30)],    # Aries
    [("venus", 8), ("mercury", 14), ("jupiter", 22), ("saturn", 27), ("mars", 30)],    # Taurus
    [("mercury", 6), ("jupiter", 12), ("venus", 17), ("mars", 24), ("saturn", 30)],    # Gemini
    [("mars", 7), ("venus", 13), ("mercury", 19), ("jupiter", 26), ("saturn", 30)],    # Cancer
    [("jupiter", 6), ("venus", 11), ("saturn", 18), ("mercury", 24), ("mars", 30)],    # Leo
    [("mercury", 7), ("venus", 17), ("jupiter", 21), ("mars", 28), ("saturn", 30)],    # Virgo
    [("saturn", 6), ("mercury", 14), ("jupiter", 21), ("venus", 28), ("mars", 30)],    # Libra
    [("mars", 7), ("venus", 11), ("mercury", 19), ("jupiter", 24), ("saturn", 30)],    # Scorpio
    [("jupiter", 12), ("venus", 17), ("mercury", 21), ("saturn", 26), ("mars", 30)],   # Sagittarius
    [("mercury", 7), ("jupiter", 14), ("venus", 22), ("saturn", 26), ("mars", 30)],    # Capricorn
    [("mercury", 7), ("venus", 13), ("jupiter", 20), ("mars", 25), ("saturn", 30)],    # Aquarius
    [("venus", 12), ("jupiter", 16), ("mercury", 19), ("mars", 28), ("saturn", 30)],   # Pisces
]
TERM_RULER_IDX = {"mercury": 0, "venus": 1, "mars": 2, "jupiter": 3, "saturn": 4}
for _sg in TERMS:                              # table self-check: 5 terms, last bound 30, ascending
    assert len(_sg) == 5 and _sg[-1][1] == 30 and all(_sg[i][1] < _sg[i + 1][1] for i in range(4))
    assert sorted(r for r, _ in _sg) == sorted(TERM_RULER_IDX)
# Weekday (Sunday = 0) -> ruling planet
WEEKDAY_RULER = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]

# ---- per-body state functions ----------------------------------------------------------------------
def _sign(y, L, b):      return int(tropical(y, L, b) // 30.0)
def _decan(y, L, b):     return int(tropical(y, L, b) // 10.0)
def _face(y, L, b):      return (2 + _decan(y, L, b)) % 7          # Mars (Chaldean 2) rules Aries I
def _term_pos(y, L, b):
    t = tropical(y, L, b); s = int(t // 30.0); dg = t - 30.0 * s
    for i, (_, hi) in enumerate(TERMS[s]):
        if dg < hi:
            return i
    return 4                                                          # dg == 30 - epsilon rounding
def _term(y, L, b):      return 5 * _sign(y, L, b) + _term_pos(y, L, b)
def _term_ruler(y, L, b):
    s = _sign(y, L, b)
    return TERM_RULER_IDX[TERMS[s][_term_pos(y, L, b)][0]]
def _element(y, L, b):   return _sign(y, L, b) % 4
def _modality(y, L, b):  return _sign(y, L, b) % 3
def _gender(y, L, b):    return _sign(y, L, b) % 2
def _domicile(y, L, b):  return CH[DOMICILE[_sign(y, L, b)]]
def _trip(y, L, b, k):   return CH[TRIPLICITY[ELEMENT[_element(y, L, b)]][k]]
def _dignity(y, L, p):
    s = _sign(y, L, p)
    if DOMICILE[s] == p:                 return 0     # domicile
    if EXALT[p] == s:                    return 1     # exaltation
    if DOMICILE[(s + 6) % 12] == p:      return 4     # detriment (opposite domicile)
    if (EXALT[p] + 6) % 12 == s:         return 3     # fall (opposite exaltation)
    return 2                                          # peregrine

# ---- lunar and calendar ----------------------------------------------------------------------------
def _elong(L):
    """Moon - Sun elongation in [0, 360); the ayanamsa cancels, sidereal == tropical."""
    return (float(L["moon"]) - float(L["sun"])) % 360.0
def phase8(y, m, d, L):   return int(((_elong(L) + 22.5) % 360.0) // 45.0)
def phase30(y, m, d, L):  return int(_elong(L) // 12.0)
def waxing(y, m, d, L):   return 0 if _elong(L) < 180.0 else 1
def mansion(y, m, d, L):  return int(tropical(y, L, "moon") // (360.0 / 28.0))
def weekday(y, m, d, L):  return (jdn(y, m, d) + 1) % 7
def day_ruler(y, m, d, L):   return CH[WEEKDAY_RULER[weekday(y, m, d, L)]]
def night_ruler(y, m, d, L): return (day_ruler(y, m, d, L) + 12) % 7

# ---- the registry ----------------------------------------------------------------------------------
def _mk(f, b, *extra):
    def fn(y, m, d, L, _f=f, _b=b, _x=extra):
        return int(_f(y, L, _b, *_x))
    return fn

SYSTEMS = []
for _b in BODIES:
    SYSTEMS += [
        {"name": f"western_sign_{_b}", "n": 12, "desc": f"tropical sign of {_b} (Aries=0)", "fn": _mk(_sign, _b)},
        {"name": f"western_decan_{_b}", "n": 36, "desc": f"tropical decan of {_b} (Aries I=0)", "fn": _mk(_decan, _b)},
        {"name": f"western_face_{_b}", "n": 7, "desc": f"Chaldean face ruler of {_b} (Chaldean index)", "fn": _mk(_face, _b)},
        {"name": f"western_term_{_b}", "n": 60, "desc": f"Egyptian term position of {_b} (5 per sign)", "fn": _mk(_term, _b)},
        {"name": f"western_term_ruler_{_b}", "n": 5, "desc": f"Egyptian term ruler of {_b} (Me Ve Ma Ju Sa)", "fn": _mk(_term_ruler, _b)},
        {"name": f"western_element_{_b}", "n": 4, "desc": f"triplicity/element of {_b} (fire earth air water)", "fn": _mk(_element, _b)},
        {"name": f"western_modality_{_b}", "n": 3, "desc": f"modality of {_b} (cardinal fixed mutable)", "fn": _mk(_modality, _b)},
        {"name": f"western_gender_{_b}", "n": 2, "desc": f"sign gender of {_b} (masculine feminine)", "fn": _mk(_gender, _b)},
        {"name": f"western_domicile_{_b}", "n": 7, "desc": f"traditional domicile ruler of {_b}'s sign (Chaldean index)", "fn": _mk(_domicile, _b)},
        {"name": f"western_trip_day_{_b}", "n": 7, "desc": f"Dorothean triplicity day lord of {_b}'s sign", "fn": _mk(_trip, _b, 0)},
        {"name": f"western_trip_night_{_b}", "n": 7, "desc": f"Dorothean triplicity night lord of {_b}'s sign", "fn": _mk(_trip, _b, 1)},
        {"name": f"western_trip_part_{_b}", "n": 7, "desc": f"Dorothean triplicity participating lord of {_b}'s sign", "fn": _mk(_trip, _b, 2)},
    ]
for _p in CLASSICAL:
    SYSTEMS.append({"name": f"western_dignity_{_p}", "n": 5,
                    "desc": f"essential dignity of {_p} by sign (domicile exaltation peregrine fall detriment)",
                    "fn": _mk(_dignity, _p)})
SYSTEMS += [
    {"name": "western_phase8", "n": 8, "desc": "lunar phase, 45-degree phases centred on the new moon", "fn": phase8},
    {"name": "western_phase30", "n": 30, "desc": "fine lunar state, 12-degree steps of Moon-Sun elongation", "fn": phase30},
    {"name": "western_waxing", "n": 2, "desc": "waxing / waning Moon", "fn": waxing},
    {"name": "western_mansion", "n": 28, "desc": "Arabic lunar mansion of the tropical Moon (Agrippa, from 0 Aries)", "fn": mansion},
    {"name": "western_weekday", "n": 7, "desc": "day of the week, Sunday=0", "fn": weekday},
    {"name": "western_day_ruler", "n": 7, "desc": "planetary day ruler on the Chaldean circle (Saturn=0 .. Moon=6)", "fn": day_ruler},
    {"name": "western_night_ruler", "n": 7, "desc": "ruler of the first hour of the night (13th planetary hour), Chaldean circle", "fn": night_ruler},
]
NAMES = [s["name"] for s in SYSTEMS]
assert len(NAMES) == len(set(NAMES))

def states(y, m, d, L):
    """All states for one person, in SYSTEMS order."""
    return [s["fn"](y, m, d, L) for s in SYSTEMS]

def angles(y, m, d, L):
    """The pseudo-body angles, build_systems.py convention: state s of N -> (s+1)*360/N."""
    return [(st + 1) * 360.0 / s["n"] for st, s in zip(states(y, m, d, L), SYSTEMS)]

# ---- smoke test + optional corpus build ------------------------------------------------------------
def smoke():
    """Deterministic synthetic longitudes on 20+ dates 1600-2000; every state must be in range.
    Also pins a few hand-checked facts (weekday of known dates, a term boundary, a face ruler)."""
    dates = [(1600, 1, 1), (1610, 2, 28), (1620, 3, 31), (1650, 6, 15), (1666, 9, 2), (1700, 1, 1),
             (1700, 2, 28), (1700, 3, 1), (1725, 12, 25), (1750, 7, 4), (1776, 7, 4), (1800, 2, 28),
             (1800, 3, 1), (1815, 6, 18), (1850, 10, 31), (1870, 4, 1), (1900, 2, 28), (1900, 3, 1),
             (1912, 4, 15), (1930, 11, 11), (1945, 8, 15), (1969, 7, 20), (1999, 12, 31), (2000, 2, 29),
             (2000, 12, 31)]
    n_dates = 0; n_evals = 0
    for k, (y, m, d) in enumerate(dates):
        for trial in range(8):
            # synthetic sidereal longitudes: an LCG seeded by the date and trial, plus edge cases
            L = {}
            seed = (jdn(y, m, d) * 7919 + trial * 104729) % 2147483647
            for i, b in enumerate(BODIES):
                seed = (seed * 1103515245 + 12345) % 2147483648
                L[b] = (seed / 2147483648.0) * 360.0
            if trial == 0:  L = {b: 0.0 for b in BODIES}
            if trial == 1:  L = {b: 359.999999 for b in BODIES}
            if trial == 2:  L = {b: (360.0 - ayanamsa(y)) % 360.0 for b in BODIES}      # tropical 0
            if trial == 3:  L = {b: (30.0 * i + 29.9999 - ayanamsa(y)) % 360.0 for i, b in enumerate(BODIES)}
            for s in SYSTEMS:
                st = s["fn"](y, m, d, L)
                assert isinstance(st, int) and 0 <= st < s["n"], (s["name"], y, m, d, st)
                n_evals += 1
        n_dates += 1
    # pinned facts
    assert weekday(2000, 1, 1, {}) == 6, "2000-01-01 was a Saturday"
    assert weekday(1969, 7, 20, {}) == 0, "1969-07-20 was a Sunday"
    assert weekday(1600, 1, 1, {}) == 6, "1600-01-01 (Gregorian) was a Saturday"
    assert day_ruler(2000, 1, 2, {}) == CH["sun"] and night_ruler(2000, 1, 2, {}) == CH["jupiter"]
    assert night_ruler(2000, 1, 3, {}) == CH["venus"]                    # Monday night: Venus
    aya = ayanamsa(2000)
    Lt = lambda t: {b: (t - aya) % 360.0 for b in BODIES}                # all bodies at tropical t
    assert _sign(2000, Lt(29.9), "sun") == 0 and _sign(2000, Lt(30.0), "sun") == 1
    assert _term_pos(2000, Lt(5.99), "sun") == 0 and _term_pos(2000, Lt(6.0), "sun") == 1
    assert _term_ruler(2000, Lt(6.0), "sun") == TERM_RULER_IDX["venus"]  # Aries 6-12 Venus
    assert _term_ruler(2000, Lt(330.0), "sun") == TERM_RULER_IDX["venus"]  # Pisces 0-12 Venus
    assert _face(2000, Lt(0.0), "sun") == CH["mars"] and _face(2000, Lt(30.0), "sun") == CH["mercury"]
    assert _dignity(2000, Lt(0.0), "sun") == 1 and _dignity(2000, Lt(120.0), "sun") == 0
    assert _dignity(2000, Lt(180.0), "sun") == 3 and _dignity(2000, Lt(300.0), "sun") == 4
    assert _dignity(2000, Lt(150.0), "mercury") == 0                     # Virgo: domicile beats exaltation
    assert _dignity(2000, Lt(60.0), "sun") == 2                          # Gemini: peregrine
    assert _domicile(2000, Lt(90.0), "sun") == CH["moon"] and _domicile(2000, Lt(300.0), "sun") == CH["saturn"]
    assert phase8(0, 0, 0, {"sun": 0.0, "moon": 0.0}) == 0 and phase8(0, 0, 0, {"sun": 0.0, "moon": 180.0}) == 4
    assert phase8(0, 0, 0, {"sun": 10.0, "moon": 350.0}) == 0            # 340 elongation: new
    assert waxing(0, 0, 0, {"sun": 0.0, "moon": 90.0}) == 0 and waxing(0, 0, 0, {"sun": 0.0, "moon": 270.0}) == 1
    assert mansion(2000, 1, 1, Lt(0.0)) == 0 and mansion(2000, 1, 1, Lt(359.9)) == 27
    assert _trip(2000, Lt(0.0), "sun", 0) == CH["sun"] and _trip(2000, Lt(0.0), "sun", 1) == CH["jupiter"]
    return n_dates, n_evals

def build():
    """Write AQ_DIR/systems_western.npz from full.csv + phases.npz (numpy/pandas only here)."""
    import numpy as np, pandas as pd
    D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
    full = pd.read_csv(f"{D_}/full.csv", dtype=str)
    Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
    bodies = [str(b) for b in Z["bodies"]]
    col = {b: bodies.index({"node": "true_node", "lilith": "mean_lilith"}.get(b, b)) for b in BODIES}
    def side(dcol, theta):
        out = []
        for iso, row in zip(full[dcol], theta):
            y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
            L = {b: float(row[col[b]]) for b in BODIES}
            out.append(angles(y, m, d, L))
        return np.array(out, np.float64)
    A = side("true_dob_a", Z["theta_a_train"]); B = side("true_dob_b", Z["theta_b_train"])
    assert np.isfinite(A).all() and np.isfinite(B).all()
    path = f"{D_}/systems_western.npz"
    np.savez_compressed(path, theta_a_sys=A, theta_b_sys=B, names=np.array(NAMES),
                        nstates=np.array([s["n"] for s in SYSTEMS]))
    print(f"wrote {path} · {len(SYSTEMS)} systems x {len(full):,} couples")

if __name__ == "__main__":
    nd, ne = smoke()
    print(f"smoke OK: {len(SYSTEMS)} systems · {nd} dates 1600-2000 · {ne:,} evaluations all in range")
    if os.environ.get("AQ_BUILD") == "1":
        build()
