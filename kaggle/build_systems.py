"""build_systems.py — every date-only system in the history of astrology and numerology as a
PSEUDO-BODY: its state, as an angle on its own circle (state s of N -> s*360/N; a life path of 1 is
40 degrees). The same three angle families then produce every aspect, across systems too.

CORRECTNESS (operator 2026-09-02, "ensure the pseudo-bodies are modelled correctly"):
  * The Chinese year — animal, stem, Nine-Star year and month, Kua — begins at LI CHUN, when the
    tropical Sun reaches 315 degrees (about 4 February), NOT on 1 January. The lab used the plain
    calendar year, which mislabels everyone born from 1 January to Li Chun (~9% of people). The
    tropical Sun is the sidereal Sun the corpus already holds plus the Lahiri ayanamsa (Swiss
    Ephemeris), and the browser computes it the same way from the shim.
  * A constant offset in a cycle (which Lord of the Night is "first") is absorbed by the fitted
    phase and does not matter; the cycle LENGTH and its BOUNDARY do, and those are exact here.
  * Kua is gendered by rule: the man's formula for the man, the woman's for the woman.
  * Name-based numerology is deliberately absent: the page's contract is two birth dates only.

Twenty systems: numerology (life path 9, birthday 31, birthday reduced 9, attitude 9), Chinese
(year animal 12, year stem 10, day stem 10, day branch 12, day nayin 30, Kua 9), Nine-Star Ki
(year 9, month 9), Maya (Tzolkin sign 20, tone 13, Haab month 19, Lord of the Night 9), Vedic
(yoga 27, Vimshottari dasha lord 9), Arabic lunar mansion (28), weekday (7 — Burmese Mahabote and
every planetary-day system). Systems that quantise a planet the bank already carries (Western
tropical sign, nakshatra, tithi, decan, Celtic tree, totems) are not duplicated.

Writes AQ_DIR/systems.npz: theta_a_sys, theta_b_sys (degrees), names, nstates.
"""
import os, numpy as np, pandas as pd
import swisseph as swe
D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt"))
swe.set_sid_mode(swe.SIDM_LAHIRI)

SYS = [("num_lifepath", 9), ("num_birthday", 31), ("num_birthday_reduced", 9), ("num_attitude", 9),
       ("cn_year_animal", 12), ("cn_year_stem", 10), ("cn_day_stem", 10), ("cn_day_branch", 12),
       ("cn_day_nayin", 30), ("cn_kua", 9), ("nine_star", 9), ("nine_star_month", 9),
       ("tz_sign", 20), ("tz_tone", 13), ("haab_month", 19), ("lord_night", 9),
       ("vedic_yoga", 27), ("vedic_dasha_lord", 9), ("manzil", 28), ("weekday", 7)]
# NAME NUMEROLOGY (operator 2026-09-02, "also include numerology of names"): the name the world
# knows the person by (the Wikidata English label), romanised so every script gets a value.
# Pythagorean letter values A=1..I=9, J=1..; Chaldean 1-8 by the classical table. Master numbers
# reduce (nine states each). The corpus and the browser share this code to the letter.
NAME_SYS = [("name_expression", 9), ("name_soul_urge", 9), ("name_personality", 9),
            ("name_chaldean", 9), ("name_cornerstone", 9), ("name_maturity", 9)]
SYS = SYS + NAME_SYS
NST = dict(SYS)
PYTH = {c: (i % 9) + 1 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
CHAL = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [1,2,3,4,5,8,3,5,1,1,2,3,4,5,7,8,1,2,3,4,6,6,6,5,1,7]))
VOWELS = set("AEIOUY")
def romanize(label):
    from unidecode import unidecode
    return "".join(c for c in unidecode(label or "").upper() if "A" <= c <= "Z")
def name_states(label, lifepath_1to9):
    L = romanize(label)
    if not L:                       # no Latin letters at all: state 0 everywhere, counted
        return {n: 0 for n, _ in NAME_SYS}
    expr = red9(sum(PYTH[c] for c in L)); soul = red9(sum(PYTH[c] for c in L if c in VOWELS) or 9)
    pers = red9(sum(PYTH[c] for c in L if c not in VOWELS) or 9); chal = red9(sum(CHAL[c] for c in L))
    return {"name_expression": expr - 1, "name_soul_urge": soul - 1, "name_personality": pers - 1,
            "name_chaldean": chal - 1, "name_cornerstone": red9(PYTH[L[0]]) - 1,
            "name_maturity": red9(lifepath_1to9 + expr) - 1}

def jdn(y, m, d):
    a = (14 - m) // 12; yy = y + 4800 - a; mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
def red9(t):
    while t > 9: t = sum(int(c) for c in str(t))
    return t
def lifepath(y, m, d): return red9(sum(int(c) for c in f"{y:04d}{m:02d}{d:02d}"))
def ninestar_year(cy): return 1 + (11 - (1 + (sum(int(c) for c in str(cy)) - 1) % 9) - 1) % 9

def states(y, m, d, sid_sun, sid_moon, aya, female, label=""):
    """0-based state index per system. sid_* sidereal degrees at noon UT; aya the Lahiri ayanamsa."""
    j = jdn(y, m, d); sx = (j + 49) % 60; k = (j - 584283) % 260
    trop_sun = (sid_sun + aya) % 360.0
    cy = y - 1 if (m <= 2 and trop_sun < 315.0) else y                 # LI CHUN year
    ys = ninestar_year(cy)
    month_idx = int(((trop_sun - 315.0) % 360.0) // 30.0)               # solar month from Li Chun
    feb = {1: 8, 4: 8, 7: 8, 2: 5, 5: 5, 8: 5, 3: 2, 6: 2, 9: 2}[ys]
    mstar = ((feb - month_idx - 1) % 9) + 1
    s = red9(sum(int(c) for c in str(cy)))
    if cy < 2000: kua = red9(5 + s) if female else red9(10 - s)
    else:         kua = red9(6 + s) if female else red9(9 - s)
    if kua == 5: kua = 8 if female else 2
    nak = int(sid_moon // (360.0 / 27.0))
    return {"num_lifepath": lifepath(y, m, d) - 1, "num_birthday": d - 1,
            "num_birthday_reduced": red9(d) - 1, "num_attitude": red9(m + d) - 1,
            "cn_year_animal": (cy - 4) % 12, "cn_year_stem": (cy - 4) % 10,
            "cn_day_stem": sx % 10, "cn_day_branch": sx % 12, "cn_day_nayin": (sx // 2) % 30,
            "cn_kua": kua - 1, "nine_star": ys - 1, "nine_star_month": mstar - 1,
            "tz_sign": k % 20, "tz_tone": k % 13, "haab_month": ((j - 584283 + 348) % 365) // 20,
            "lord_night": (j - 584283) % 9,
            "vedic_yoga": int(((sid_sun + sid_moon) % 360.0) // (360.0 / 27.0)),
            "vedic_dasha_lord": nak % 9, "manzil": int(sid_moon // (360.0 / 28.0)),
            "weekday": (j + 1) % 7, **name_states(label, lifepath(y, m, d))}

def angles(y, m, d, sid_sun, sid_moon, aya, female, label=""):
    st = states(y, m, d, sid_sun, sid_moon, aya, female, label)
    return [(st[n] + 1) * 360.0 / N for n, N in SYS]

if __name__ == "__main__":
    full = pd.read_csv(f"{D_}/full.csv", dtype=str)
    Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
    bodies = [str(b) for b in Z["bodies"]]; isun, imoon = bodies.index("sun"), bodies.index("moon")
    LAB = os.path.expanduser("~/.artamatch-dev/labels.csv")
    labels = dict(pd.read_csv(LAB, dtype=str).fillna("").itertuples(index=False, name=None)) if os.path.exists(LAB) else {}
    missing = 0
    def side(col, pcol, theta, female):
        nonlocal missing
        out = []
        for iso, pid, row in zip(full[col], full[pcol], theta):
            y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
            aya = swe.get_ayanamsa_ut(swe.julday(y, m, d, 12.0))
            lab = labels.get(pid, "")
            if not romanize(lab): missing += 1
            out.append(angles(y, m, d, float(row[isun]), float(row[imoon]), aya, female, lab))
        return np.array(out, np.float64)
    A = side("true_dob_a", "pid_a", Z["theta_a_train"], False)
    B = side("true_dob_b", "pid_b", Z["theta_b_train"], True)
    print(f"  names: {len(labels):,} labels · {missing:,} of {2*len(full):,} persons without Latin letters (state 0)")
    np.savez_compressed(f"{D_}/systems.npz", theta_a_sys=A, theta_b_sys=B,
                        names=np.array([n for n, _ in SYS]), nstates=np.array([n for _, n in SYS]))
    print(f"wrote {D_}/systems.npz · {len(SYS)} systems x {len(full):,} couples")
