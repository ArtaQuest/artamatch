"""
trad_numerology.py — Pythagorean and Chaldean numerology of the birth date, as feature blocks.

WHAT THIS TRADITION IS, AND WHY IT IS AN UNUSUALLY CLEAN TEST

Numerology is the one popular tradition here that needs no sky at all. Every quantity is arithmetic on the digits
of the calendar date — the Life Path is the digit-sum of the whole date reduced to a single figure (with 11, 22
and 33 kept as "master numbers"), the Birthday number is the day reduced, the Personal Year is the digit-sum of
the birth day and month with a target year. Nothing about planets enters, so nothing about the era enters either
except through the year's own digits, and the year's digits are about as far from a smooth cohort trend as a
function of the year can be: 1899 and 1900 sit next to each other in time and have digit-sums 27 and 10.

That is precisely why it belongs beside the astrological traditions. If numerology carries any signal on a
TEMPORAL split, it cannot be reading the calendar the way a long-baseline cycle can — the digit-sum of the year is
almost decorrelated from the year itself. A numerology block that scores above chance out of time would be one of
the cleaner positive results this project could produce; one that scores at chance is a fair measurement of a
tradition practised by a great many people.

WHAT IS COMPUTED, and the rule for each

  Life Path        digit-sum of YYYY+MM+DD reduced to 1..9, keeping 11/22/33 (Pythagorean; the most-taught form)
  Birthday number  DD reduced the same way
  Attitude number  MM+DD reduced
  Day / Month / Year sub-numbers  each component reduced on its own — the "pillars" some schools read
  Chaldean single  the same date reduced under the Chaldean rule, which reduces to 1..8 with 9 held sacred
  Compatibility    the pairwise tables numerologists actually use: the pair of Life Paths as an ordered class,
                   whether they are "compatible" under the common 1-3-5 / 2-4-8 / 3-6-9 groupings, the sum and
                   the difference of the two Life Paths reduced again (the "relationship number")
  Personal Year    each partner's Personal Year in the OTHER partner's birth year — the numerologist's question
                   "what year were you in when they were born" — plus the Personal Year both are in at the
                   Davison midpoint date

WHAT IS DELIBERATELY NOT COMPUTED. Name numerology (Expression, Soul Urge, Personality) needs the letters of a
name, and there is no name in this dataset. It is the larger half of the practice and it is absent by
necessity, said plainly here rather than left for a reader to notice.

SHAPE CONTRACT. Every block is (n, k) with k a function of this file alone — never of the batch — and every
one-hot uses a fixed width, so a batch of any size produces the same columns. That is the property
verify_docs.py refuses to publish a change in.
"""
import numpy as np
import swisseph as swe

# The Davison midpoint slot, the same index the other modules use.
iO, iY, iDV = 0, 1, 5

MASTER = (11, 22, 33)


def _digit_sum(x):
    x = np.asarray(x, dtype=np.int64)
    out = np.zeros_like(x)
    x = np.abs(x)
    while np.any(x > 0):
        out += x % 10
        x //= 10
    return out


def _reduce(x, keep_master=True):
    """Reduce to a single digit 1..9, keeping 11/22/33 when asked. Zero maps to 9 (an all-zero input never occurs
    for a real date, but the function must be total)."""
    x = np.asarray(x, dtype=np.int64).copy()
    for _ in range(6):                          # a 4-digit-year date reduces in at most three passes
        big = x > 9
        if keep_master:
            big &= ~np.isin(x, MASTER)
        if not np.any(big):
            break
        x = np.where(big, _digit_sum(x), x)
    x = np.where(x == 0, 9, x)
    return x


def _reduce_chaldean(x):
    """Chaldean reduction to 1..9 with no master numbers; 9 is not assigned to letters in that system but a
    date can still reduce to it, so it is kept as a class."""
    return _reduce(x, keep_master=False)


def _ymd(JD):
    """Calendar year, month, day for an array of Julian days, at the fixed hour every chart is cast for."""
    JD = np.asarray(JD, dtype=np.float64)
    y = np.zeros(JD.shape, dtype=np.int64)
    m = np.zeros_like(y)
    d = np.zeros_like(y)
    for i, jd in enumerate(JD.ravel()):
        yy, mm, dd, _ = swe.revjul(float(jd))
        y.flat[i], m.flat[i], d.flat[i] = int(yy), int(mm), int(dd)
    return y, m, d


def _oh(idx, k):
    idx = np.asarray(idx, dtype=np.int64) % k
    out = np.zeros((len(idx), k), dtype=np.float64)
    out[np.arange(len(idx)), idx] = 1.0
    return out


# The Life Path takes values 1..9 plus 11, 22, 33 -> twelve classes. Index them densely.
_LP_CLASSES = list(range(1, 10)) + list(MASTER)
_LP_INDEX = {v: i for i, v in enumerate(_LP_CLASSES)}


def _lp_idx(v):
    v = np.asarray(v, dtype=np.int64)
    out = np.zeros(v.shape, dtype=np.int64)
    for k, i in _LP_INDEX.items():
        out[v == k] = i
    return out


# The compatibility groupings most numerology texts teach: 1-5-7 (mind), 2-4-8 (business), 3-6-9 (creative).
_GROUP = {1: 0, 5: 0, 7: 0, 2: 1, 4: 1, 8: 1, 3: 2, 6: 2, 9: 2, 11: 1, 22: 1, 33: 2}


def numbers(y, m, d):
    """Every single-date number, as int arrays of the input's shape."""
    lp = _reduce(_digit_sum(y) + _digit_sum(m) + _digit_sum(d))
    bday = _reduce(d)
    att = _reduce(_digit_sum(m) + _digit_sum(d))
    yy = _reduce(_digit_sum(y))
    mm = _reduce(m)
    dd = _reduce(d, keep_master=False)
    chal = _reduce_chaldean(_digit_sum(y) + _digit_sum(m) + _digit_sum(d))
    return {"lp": lp, "bday": bday, "att": att, "y": yy, "m": mm, "d": dd, "chal": chal}


def personal_year(m, d, target_year):
    """The Personal Year: birth month + birth day + a target year, reduced (master numbers dropped, as most
    schools do for the yearly cycle)."""
    return _reduce(_digit_sum(m) + _digit_sum(d) + _digit_sum(target_year), keep_master=False)


def build(E):
    B = {}
    yO, mO, dO = _ymd(E.JD[iO])
    yY, mY, dY = _ymd(E.JD[iY])
    yD, mD, dD = _ymd(E.JD[iDV])
    NO, NY = numbers(yO, mO, dO), numbers(yY, mY, dY)

    # 1 ── each partner's core numbers, one-hot ────────────────────────────────────────────────────────────
    c = []
    for N in (NO, NY):
        c += [_oh(_lp_idx(N["lp"]), 12), _oh(N["bday"] - 1, 9), _oh(N["att"] - 1, 9),
              _oh(N["y"] - 1, 9), _oh(N["m"] - 1, 9), _oh(N["d"] - 1, 9), _oh(N["chal"] - 1, 9)]
        c.append(np.stack([np.isin(N["lp"], MASTER).astype(np.float64)], axis=-1))
    B["num: life path, birthday, attitude and pillars, both partners"] = np.concatenate(c, axis=1)

    # 2 ── the pair, which is what a numerologist actually consults for a match ────────────────────────────
    lpO, lpY = NO["lp"], NY["lp"]
    gO = np.array([_GROUP.get(int(v), 0) for v in lpO])
    gY = np.array([_GROUP.get(int(v), 0) for v in lpY])
    rel = _reduce(lpO + lpY, keep_master=False)                        # the "relationship number"
    diff = _reduce(np.abs(lpO - lpY), keep_master=False)
    c = [
        _oh(_lp_idx(lpO) * 12 + _lp_idx(lpY), 144),                    # the ordered Life Path pair
        _oh(rel - 1, 9),
        _oh(diff - 1, 9),
        np.stack([(lpO == lpY).astype(np.float64),
                  (gO == gY).astype(np.float64),                       # same compatibility group
                  (NO["bday"] == NY["bday"]).astype(np.float64),
                  (NO["att"] == NY["att"]).astype(np.float64),
                  (NO["chal"] == NY["chal"]).astype(np.float64),
                  np.isin(lpO, MASTER).astype(np.float64) * np.isin(lpY, MASTER),
                  ], axis=-1),
        _oh(gO * 3 + gY, 9),
    ]
    B["num: the pair — relationship number, groups and matches"] = np.concatenate(c, axis=1)

    # 3 ── personal years: each in the other's birth year, and both at the Davison midpoint ─────────────────
    pyO_in_Y = personal_year(mO, dO, yY)
    pyY_in_O = personal_year(mY, dY, yO)
    pyO_dv = personal_year(mO, dO, yD)
    pyY_dv = personal_year(mY, dY, yD)
    c = [_oh(pyO_in_Y - 1, 9), _oh(pyY_in_O - 1, 9), _oh(pyO_dv - 1, 9), _oh(pyY_dv - 1, 9),
         np.stack([(pyO_dv == pyY_dv).astype(np.float64),
                   ((pyO_dv == 1) | (pyY_dv == 1)).astype(np.float64),   # a "1 year" — beginnings
                   ((pyO_dv == 9) | (pyY_dv == 9)).astype(np.float64),   # a "9 year" — endings
                   ], axis=-1)]
    B["num: personal years, in each other's birth year and at the midpoint"] = np.concatenate(c, axis=1)

    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in B.items()}


if __name__ == "__main__":
    # Self-test on dates anyone can check by hand.
    y = np.array([1990, 1899, 1900, 2000, 1965])
    m = np.array([12, 12, 1, 1, 11])
    d = np.array([25, 31, 1, 1, 22])
    N = numbers(y, m, d)
    # 1990-12-25: 1+9+9+0 + 1+2 + 2+5 = 29 -> 11 (master, kept)
    assert N["lp"][0] == 11, N["lp"][0]
    # 1899-12-31: 27 + 3 + 4 = 34 -> 7
    assert N["lp"][1] == 7, N["lp"][1]
    # 1900-01-01: 10 + 1 + 1 = 12 -> 3 ; adjacent years, life paths 7 and 3 — the point about the era
    assert N["lp"][2] == 3, N["lp"][2]
    # 2000-01-01: 2 + 1 + 1 = 4
    assert N["lp"][3] == 4
    # 1965-11-22: 21 + 2 + 4 = 27 -> 9 ; birthday 22 is a master number
    assert N["lp"][4] == 9 and N["bday"][4] == 22, (N["lp"][4], N["bday"][4])
    # Personal Year for a 25 December birthday in 2026: 3 + 7 + (2+0+2+6=10) = 20 -> 2
    assert int(personal_year(np.array([12]), np.array([25]), np.array([2026]))[0]) == 2
    print("  numerology self-test: 1990-12-25 -> Life Path 11, 1899-12-31 -> 7, 1900-01-01 -> 3, "
          "1965-11-22 -> 9 with Birthday 22")
    print("  1899 and 1900 are adjacent years with life paths 7 and 3: the year's digits are not the era")
