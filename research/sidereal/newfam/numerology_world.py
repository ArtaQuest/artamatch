"""
numerology_world - world numerology of the two birth dates, beyond the Pythagorean Life Path.

The whole module is arithmetic on the CALENDAR DATE ITSELF: the digits, their reductions, the
Julian day number and the cycles various traditions run off them.  Nothing here reads Z (the
sidereal longitudes) because no numerological doctrine consults a planet's longitude - it consults
the written date.  `Z` and `half` are therefore accepted and unused, which keeps build() a pure
function of `df` alone and guarantees identical width on both halves.

`df.start` is NEVER read: on this dataset it is always the string "0000-00-00", so every "wedding
date" cycle (personal year of the marriage, etc.) is unavailable.  The doctrines that need a
SECOND date are therefore re-pointed at the only other real date we have - the PARTNER'S BIRTH.
That is the classic synastry move in numerology (biorhythm compatibility is computed exactly this
way: the two birth dates, nothing else), so it is not a fudge, it is the doctrine's own pair form.

DELIBERATE OMISSIONS
  * Naam / name numerology - needs the name, which we do not have.
  * Kua / Ming Gua       - already built by another module (told to skip).
  * The raw age gap in days or years - the strongest known baseline on this task lives there, and
    smuggling it in under a numerology name would let a model credit the doctrine for it.  Every
    two-date quantity below is a RESIDUE or a COSINE, i.e. magnitude-destroying by construction.

ORDER-FREENESS
  Numerology's pair readings do not care who is "a".  Every pair feature is therefore built from
  min/max, |a-b|, a symmetrised lookup table, a count over the pair, or an even function of the
  signed difference (cos, |.| mod m).  Swapping the two columns cannot change a single output.

OUTPUT
  116 columns, identical on both halves.  See the names list: every column is prefixed `nm_` and
  named for the doctrine it encodes.

MISSING DATA
  Four date shapes exist: full, 'YYYY-00-00' (year only), '0000-MM-DD' (year unknown) and
  '0000-00-00' (absent).  A component that was never recorded is None, and every quantity that
  needs it is NaN - never a stand-in.  min/max over the pair use plain min/max so a NaN on ONE
  side propagates: "the older partner's Moolank" is not a pair statistic and must not masquerade
  as one.  No NaN is ever cast to int; every table lookup is guarded on an int in 1..9.
"""

import math
import numpy as np
import pandas as pd

NAN = float("nan")

MASTERS = (11, 22, 33)          # master numbers - stop the reduction here
KARMIC = (13, 14, 16, 19)       # karmic debt numbers - read from the UNREDUCED two-digit total

# The Lo Shu magic square (the Chinese birth grid).  Layout:
#       4 9 2
#       3 5 7
#       8 1 6
# Eight "arrows": 3 rows, 3 columns, 2 diagonals.  All three digits present -> arrow of strength;
# all three absent -> arrow of weakness.  Pair reading: does one partner's grid fill the other's
# empty arrows (complementary) or do both share the same hole (compounded weakness)?
LOSHU_LINES = (
    (4, 9, 2), (3, 5, 7), (8, 1, 6),    # rows: mind / soul / practical
    (4, 3, 8), (9, 5, 1), (2, 7, 6),    # columns: thought / will / action
    (4, 5, 6), (2, 5, 8),               # diagonals: determination / spirituality
)

# Biorhythm cycles in days.  The three classical ones plus the three "secondary" cycles of the
# extended theory.  Couple biorhythm compatibility is textbook-defined as the phase agreement of
# the two BIRTH dates, which is exactly what we can compute here.
BIO_CYCLES = (("phys", 23), ("emot", 28), ("intel", 33),
              ("intu", 38), ("aesth", 43), ("spir", 53))

# Moduli numerology actually uses on a day count: 7 (the week / the seven planets),
# 9 (the numerological wheel), 11 (master), 12 (the dozen / signs), 13 (lunar months, the first
# karmic debt), 22 (the Kabbalistic paths / Hebrew letters).
JD_MODULI = (7, 9, 11, 12, 13, 22)

# jdn % 7 -> weekday (0 = Monday, JDN 0 was a Monday) -> that day's ruling planet, as the
# number that planet carries in Indian numerology.
WEEKDAY_PLANET = (2, 9, 5, 3, 6, 8, 1)   # Moon Mars Mercury Jupiter Venus Saturn Sun

# The four "planes of expression" of Western numerology.
PLANE = {1: 0, 8: 0,          # mental
         4: 1, 5: 1,          # physical
         2: 2, 3: 2, 6: 2,    # emotional
         7: 3, 9: 3}          # intuitive

# --- Indian numerology: each number is a planet, and the planets have natural friendships. -----
# 1 Sun  2 Moon  3 Jupiter  4 Rahu  5 Mercury  6 Venus  7 Ketu  8 Saturn  9 Mars
# Naisargika maitri, with Rahu read as Saturn-like and Ketu as Mars-like.  Symmetrised below.
_V_FRIEND = {1: {1, 2, 3, 9}, 2: {1, 2, 5}, 3: {1, 2, 3, 9}, 4: {4, 5, 6, 8},
             5: {1, 5, 6}, 6: {4, 5, 6, 7, 8}, 7: {3, 6, 7, 8, 9}, 8: {4, 5, 6, 7, 8},
             9: {1, 2, 3, 7, 9}}
_V_ENEMY = {1: {4, 6, 8}, 2: {4, 6, 8}, 3: {5, 6}, 4: {1, 2, 9},
            5: {2, 7}, 6: {1, 2, 3}, 7: {2, 5}, 8: {1, 2, 9}, 9: {4, 5, 8}}

# --- Western "life path compatibility" chart, the one reproduced in practice. ------------------
_LP_GOOD = {1: {1, 2, 3, 5, 9}, 2: {1, 2, 4, 6, 8}, 3: {1, 3, 5, 6, 9}, 4: {2, 4, 6, 7, 8},
            5: {1, 3, 5, 7, 9}, 6: {2, 3, 4, 6, 9}, 7: {4, 5, 7}, 8: {2, 4, 6, 8},
            9: {1, 3, 5, 6, 9}}
_LP_HARD = {1: {4, 6, 8}, 2: {5, 7}, 3: {4, 7, 8}, 4: {3, 5, 9}, 5: {2, 4, 6},
            6: {1, 5, 7}, 7: {2, 3, 6, 8}, 8: {3, 5, 7}, 9: {4, 7}}


def _sym_table(good, hard):
    """+1 friendly, -1 hostile, 0 neutral; averaged over both directions so the table is
    symmetric and the model cannot learn column order from it.  Row/col 0 left NaN as a tripwire:
    a 0 index would mean an unguarded lookup and would show up as NaN, not as a wrong number."""
    m = np.full((10, 10), NAN, dtype=np.float64)
    for a in range(1, 10):
        for b in range(1, 10):
            sa = 1.0 if b in good[a] else (-1.0 if b in hard[a] else 0.0)
            sb = 1.0 if a in good[b] else (-1.0 if a in hard[b] else 0.0)
            m[a, b] = 0.5 * (sa + sb)
    return m


_VEDIC = _sym_table(_V_FRIEND, _V_ENEMY)
_LPTAB = _sym_table(_LP_GOOD, _LP_HARD)


# ---------------------------------------------------------------- arithmetic primitives -------

def _dsum(n):
    """One pass of digit summing - the Chaldean 'compound' step."""
    n = abs(int(n))
    s = 0
    while n:
        s += n % 10
        n //= 10
    return s


def _chain(n):
    """The whole reduction chain, e.g. 48 -> [48, 12, 3].  Karmic debt is read from the
    intermediates, which is why the chain and not just the root is kept."""
    out = [int(n)]
    while out[-1] > 9:
        out.append(_dsum(out[-1]))
    return out


def _droot(n):
    """Full Pythagorean digital root, 1..9.  None for anything non-positive (0 has no root)."""
    if n is None:
        return None
    n = int(n)
    if n <= 0:
        return None
    return 1 + (n - 1) % 9


def _droot_m(n):
    """Digital root that STOPS at a master number: 29 -> 11, 33 -> 33, 26 -> 8."""
    if n is None:
        return None
    n = int(n)
    if n <= 0:
        return None
    while n > 9:
        if n in MASTERS:
            return n
        n = _dsum(n)
    return n


def _karmic(n):
    """1 if a karmic debt number appears anywhere in the reduction chain of n."""
    if n is None:
        return None
    for v in _chain(n):
        if v in KARMIC:
            return 1
    return 0


def _dim(y, m):
    """Days in month; Feb defaults to 29 when the year is unknown so a real 29-Feb birth on a
    '0000-02-29' record is kept rather than silently discarded."""
    if m in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if m in (4, 6, 9, 11):
        return 30
    if y is None:
        return 29
    return 29 if ((y % 4 == 0 and y % 100 != 0) or y % 400 == 0) else 28


def _jdn(y, m, d):
    """Proleptic Gregorian Julian Day Number.  Proleptic throughout (the set reaches back to the
    1400s): what the cycles need is a single consistent day count, not a calendar-reform ruling."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _parse(s):
    """'YYYY-MM-DD' -> (y, m, d), each None when that component was never recorded.
    Handles all four shapes: full, 'YYYY-00-00', '0000-MM-DD', '0000-00-00'."""
    if not isinstance(s, str) or len(s) < 10:
        return (None, None, None)
    try:
        y = int(s[0:4])
        m = int(s[5:7])
        d = int(s[8:10])
    except (ValueError, TypeError):
        return (None, None, None)
    y = y if y > 0 else None
    m = m if 1 <= m <= 12 else None
    d = d if 1 <= d <= 31 else None
    if m is None:
        d = None if d is None else d          # a day without a month is still a Moolank
    if m is not None and d is not None and d > _dim(y, m):
        d = None                              # an impossible day is not a day
    return (y, m, d)


# ---------------------------------------------------------------- one partner -----------------

def _person(s):
    """Every single-person numerology number this module needs.  None where unknowable."""
    y, m, d = _parse(s)
    p = {"y": y, "m": m, "d": d}
    full = (y is not None and m is not None and d is not None)
    p["full"] = full
    p["jd"] = _jdn(y, m, d) if full else None

    # Vedic Psychic number (Moolank) - the birth DAY reduced; rules the personality one shows a
    # partner.  Available whenever the day is known, even with no year.
    p["moolank"] = _droot(d)
    # The same day kept master-preserving: an 11th or 22nd is a master birthday, not a 2 or a 4.
    p["day_master"] = _droot_m(d)
    p["birthday"] = float(d) if d is not None else None

    p["month_root"] = _droot(m)
    p["year_root"] = _droot(y)
    p["year_compound"] = _dsum(y) if y is not None else None
    # Attitude / Sun number: month + day reduced - how the person meets the world on first contact.
    p["attitude"] = _droot(m + d) if (m is not None and d is not None) else None

    # Chaldean compound of the whole date: every digit summed ONCE, unreduced.  Chaldean reads the
    # two-digit compound itself, not only its root - so it is kept as a feature in its own right.
    total = (_dsum(y) + _dsum(m) + _dsum(d)) if full else None
    p["compound"] = total
    # Vedic Destiny (Bhagyank) == Pythagorean Life Path, master-preserving.
    p["bhagyank"] = _droot_m(total)
    # The same reduced all the way to 1..9 - the form the compatibility grids are indexed by.
    p["bhagyank_plain"] = _droot(total)
    # Kabbalistic path: the compound folded onto the 22 paths / Hebrew letters of the Tree.
    p["kab_path"] = (1 + (total - 1) % 22) if total else None

    # Karmic debt, counted over the three places doctrine looks: the raw birth day, the compound
    # chain, and the classic life-path sum (reduced year + raw month + raw day).
    if full:
        s2 = _droot(y) + m + d
        p["karmic"] = (1 if d in KARMIC else 0) + _karmic(total) + _karmic(s2)
    elif d is not None:
        p["karmic"] = None      # partial evidence is not a count - do not invent one
    else:
        p["karmic"] = None
    # A master flag must be able to see BOTH places a master can appear (the day and the life
    # path).  With only one of them readable, "no master" would be an assertion about a number
    # nobody recorded, so it stays NaN.
    if p["bhagyank"] is None or p["day_master"] is None:
        p["master"] = None
    else:
        p["master"] = 1 if (p["bhagyank"] in MASTERS or p["day_master"] in MASTERS) else 0

    p["wd_planet"] = WEEKDAY_PLANET[p["jd"] % 7] if full else None

    # Lo Shu grid: how many times each digit 1..9 appears in DDMMYYYY.  Zeros have no cell, so
    # they are dropped.  The grid is only a grid when the whole date is there.
    if full:
        cnt = [0] * 10
        for ch in ("%02d%02d%04d" % (d, m, y)):
            k = ord(ch) - 48
            if k:
                cnt[k] += 1
        p["grid"] = cnt
    else:
        p["grid"] = None
    return p


# ---------------------------------------------------------------- accumulator ------------------

class _Acc:
    """Collects (name, value) in one pass so the names list can never drift out of step with the
    value order - the names are derived by running the very same code once on an empty pair."""
    __slots__ = ("names", "vals", "collect")

    def __init__(self, collect):
        self.names = []
        self.vals = []
        self.collect = collect

    def add(self, name, val):
        if self.collect:
            self.names.append(name)
        if val is None:
            self.vals.append(NAN)
        else:
            self.vals.append(float(val))


def _mm(a, b):
    """Order-free (min, max).  NaN-propagating on purpose: with one side missing there IS no pair
    minimum, and reporting the known side as 'the min' would be a fabricated pair statistic."""
    if a is None or b is None:
        return (None, None)
    if a != a or b != b:
        return (None, None)
    return (min(a, b), max(a, b))


def _absdiff(a, b):
    if a is None or b is None:
        return None
    return abs(a - b)


def _same(a, b):
    if a is None or b is None:
        return None
    return 1.0 if a == b else 0.0


def _lookup(tab, a, b):
    """Guarded symmetric table read.  A None (or anything outside 1..9) yields NaN and NEVER an
    int cast - a NaN silently becoming index 0 is exactly the bug the contract forbids."""
    if a is None or b is None:
        return None
    if not (isinstance(a, int) and isinstance(b, int)):
        return None
    if not (1 <= a <= 9 and 1 <= b <= 9):
        return None
    return float(tab[a, b])


def _circ(a, b, mod):
    """Shortest distance between two positions on a wheel of `mod`, normalised to 0..1."""
    if a is None or b is None:
        return None
    r = abs(a - b) % mod
    return min(r, mod - r) / (mod / 2.0)


# ---------------------------------------------------------------- the pair ---------------------

def _features(pa, pb, acc):
    """Every add() below is unconditional: the SHAPE of the output never depends on the data,
    only the values do.  That is what guarantees equal width on train and test."""
    add = acc.add

    # --- A. the per-person numbers, made order-free as (min, max) over the couple --------------
    for key, label, why in (
        ("moolank",       "moolank",   "Vedic Psychic number: birth day reduced 1-9"),
        ("day_master",    "daymaster", "birth day reduced but stopping at master 11/22"),
        ("bhagyank",      "bhagyank",  "Vedic Destiny = Pythagorean Life Path, master-preserving"),
        ("compound",      "compound",  "Chaldean compound: every digit of the date, unreduced"),
        ("year_root",     "yearroot",  "digit root of the birth year"),
        ("month_root",    "monthroot", "digit root of the birth month"),
        ("attitude",      "attitude",  "Attitude/Sun number: month+day reduced"),
        ("birthday",      "birthday",  "Birthday number: the raw day 1-31"),
        ("kab_path",      "kabpath",   "Kabbalistic path 1-22 of the compound"),
        ("karmic",        "karmic",    "how many places karmic debt 13/14/16/19 shows"),
        ("wd_planet",     "wdplanet",  "planet ruling the weekday of birth, as its number"),
    ):
        lo, hi = _mm(pa[key], pb[key])
        add("nm_%s_min" % label, lo)
        add("nm_%s_max" % label, hi)

    # --- B. plain pair agreements and differences ----------------------------------------------
    add("nm_same_moolank", _same(pa["moolank"], pb["moolank"]))
    add("nm_same_bhagyank", _same(pa["bhagyank"], pb["bhagyank"]))
    add("nm_same_yearroot", _same(pa["year_root"], pb["year_root"]))
    add("nm_same_wdplanet", _same(pa["wd_planet"], pb["wd_planet"]))
    add("nm_absdiff_moolank", _absdiff(pa["moolank"], pb["moolank"]))
    add("nm_absdiff_bhagyank", _absdiff(pa["bhagyank_plain"], pb["bhagyank_plain"]))
    # "digit-sum difference": the two Chaldean compounds set against each other
    add("nm_absdiff_compound", _absdiff(pa["compound"], pb["compound"]))
    add("nm_absdiff_yearcompound", _absdiff(pa["year_compound"], pb["year_compound"]))
    add("nm_absdiff_birthday", _absdiff(pa["birthday"], pb["birthday"]))
    # distance on the 22-path wheel: the paths are a cycle, so 1 and 22 are neighbours
    add("nm_kab_circdist", _circ(pa["kab_path"], pb["kab_path"], 22))

    # --- C. the compatibility grids doctrine actually uses -------------------------------------
    # Indian numerology: number = planet, planets are friends/neutrals/enemies by nature.
    add("nm_vedic_moolank", _lookup(_VEDIC, pa["moolank"], pb["moolank"]))
    add("nm_vedic_bhagyank", _lookup(_VEDIC, pa["bhagyank_plain"], pb["bhagyank_plain"]))
    add("nm_vedic_wdplanet", _lookup(_VEDIC, pa["wd_planet"], pb["wd_planet"]))
    # Western life-path compatibility chart, symmetrised.
    add("nm_lptab_moolank", _lookup(_LPTAB, pa["moolank"], pb["moolank"]))
    add("nm_lptab_bhagyank", _lookup(_LPTAB, pa["bhagyank_plain"], pb["bhagyank_plain"]))
    # Sum of the two numbers, reduced: the number the RELATIONSHIP is said to carry.  9 is
    # "completion" and is called out separately because that is the reading, not the magnitude.
    for key, label in (("moolank", "moolank"), ("bhagyank_plain", "bhagyank")):
        a, b = pa[key], pb[key]
        sr = _droot(a + b) if (a is not None and b is not None) else None
        add("nm_sumroot_%s" % label, sr)
        add("nm_sumroot_is9_%s" % label, None if sr is None else (1.0 if sr == 9 else 0.0))
        # polarity: odd numbers are read as yang/active, even as yin/receptive.  Count of odds.
        par = None if (a is None or b is None) else float((a % 2) + (b % 2))
        add("nm_parity_%s" % label, par)
        # planes of expression: mental / physical / emotional / intuitive
        sp = None
        if a is not None and b is not None:
            sp = 1.0 if PLANE.get(a) == PLANE.get(b) else 0.0
        add("nm_sameplane_%s" % label, sp)
        # the three triads of the wheel (1-4-7, 2-5-8, 3-6-9)
        st = None if (a is None or b is None) else (1.0 if a % 3 == b % 3 else 0.0)
        add("nm_sametriad_%s" % label, st)

    # --- D. master numbers and karmic debt across the couple -----------------------------------
    ma, mb = pa["master"], pb["master"]
    add("nm_master_count", None if (ma is None or mb is None) else float(ma + mb))
    ka, kb = pa["karmic"], pb["karmic"]
    add("nm_karmic_count_pair", None if (ka is None or kb is None) else float(ka + kb))
    add("nm_karmic_any", None if (ka is None or kb is None)
        else (1.0 if (ka > 0 or kb > 0) else 0.0))

    # --- E. the couple number: both compounds added, then read as one date would be -------------
    ca, cb = pa["compound"], pb["compound"]
    cc = (ca + cb) if (ca is not None and cb is not None) else None
    add("nm_couple_compound", cc)
    add("nm_couple_root", _droot(cc))
    cm = _droot_m(cc)
    add("nm_couple_master", cm)
    add("nm_couple_is_master", None if cm is None else (1.0 if cm in MASTERS else 0.0))
    add("nm_couple_karmic", _karmic(cc))
    add("nm_couple_kabpath", None if cc is None else float(1 + (cc - 1) % 22))

    # --- F. the Lo Shu grid, singly and as a pair ----------------------------------------------
    ga, gb = pa["grid"], pb["grid"]
    both = ga is not None and gb is not None
    if both:
        pra = [ga[k] > 0 for k in range(10)]
        prb = [gb[k] > 0 for k in range(10)]
        miss_a = sum(1 for k in range(1, 10) if not pra[k])
        miss_b = sum(1 for k in range(1, 10) if not prb[k])
        lo, hi = _mm(float(miss_a), float(miss_b))
        add("nm_loshu_missing_min", lo)
        add("nm_loshu_missing_max", hi)
        # a hole BOTH partners carry is the compounded weakness of the pair reading
        add("nm_loshu_missing_shared",
            float(sum(1 for k in range(1, 10) if not pra[k] and not prb[k])))
        add("nm_loshu_missing_either",
            float(sum(1 for k in range(1, 10) if not pra[k] or not prb[k])))
        add("nm_loshu_present_shared",
            float(sum(1 for k in range(1, 10) if pra[k] and prb[k])))
        inter = sum(1 for k in range(1, 10) if pra[k] and prb[k])
        union = sum(1 for k in range(1, 10) if pra[k] or prb[k])
        add("nm_loshu_jaccard", (inter / union) if union else None)

        ca_ = cb_ = bothc = bothe = comp = uni = 0
        for ln in LOSHU_LINES:
            fa = all(pra[k] for k in ln)
            fb = all(prb[k] for k in ln)
            ea = all(not pra[k] for k in ln)
            eb = all(not prb[k] for k in ln)
            fu = all(pra[k] or prb[k] for k in ln)
            ca_ += fa
            cb_ += fb
            bothc += (fa and fb)
            bothe += (ea and eb)
            comp += (fa != fb)          # exactly one has it: one grid fills the other's gap
            uni += fu
        lo, hi = _mm(float(ca_), float(cb_))
        add("nm_loshu_arrows_complete_min", lo)
        add("nm_loshu_arrows_complete_max", hi)
        ea_ = sum(1 for ln in LOSHU_LINES if all(not pra[k] for k in ln))
        eb_ = sum(1 for ln in LOSHU_LINES if all(not prb[k] for k in ln))
        lo, hi = _mm(float(ea_), float(eb_))
        add("nm_loshu_arrows_empty_min", lo)
        add("nm_loshu_arrows_empty_max", hi)
        add("nm_loshu_arrows_both_complete", float(bothc))
        add("nm_loshu_arrows_both_empty", float(bothe))
        add("nm_loshu_arrows_complement", float(comp))
        add("nm_loshu_arrows_union", float(uni))
        for k in range(1, 10):
            # 0, 1 or 2 of the couple carry this number at all - shared strength vs shared gap.
            # A cell can come out constant on a narrow era (every year 1000-1999 contains a 1, so
            # nm_loshu_d1_pair is 2 for every row of this set).  That is the era, not a bug: the
            # cell is not structurally constant (2023-05-07 has no 1), and dropping a grid cell
            # because of one dataset's date range would make the grid dataset-dependent.
            add("nm_loshu_d%d_pair" % k, float((1 if pra[k] else 0) + (1 if prb[k] else 0)))
        add("nm_loshu_repeat_max",
            float(max(max(ga[1:10]), max(gb[1:10]))))       # an over-represented number = excess
    else:
        for nm in ("missing_min", "missing_max", "missing_shared", "missing_either",
                   "present_shared", "jaccard", "arrows_complete_min", "arrows_complete_max",
                   "arrows_empty_min", "arrows_empty_max", "arrows_both_complete",
                   "arrows_both_empty", "arrows_complement", "arrows_union"):
            add("nm_loshu_%s" % nm, None)
        for k in range(1, 10):
            add("nm_loshu_d%d_pair" % k, None)
        add("nm_loshu_repeat_max", None)

    # --- G. biorhythm: each partner's cycle phase at the other's birth ---------------------------
    # The phase of A at B's birth is the negative of the phase of B at A's birth, so the raw sine
    # is order-DEPENDENT and is not emitted.  cos of the signed day difference and |diff| mod P are
    # both even in that difference, and cos is exactly the textbook couple-compatibility read.
    jda, jdb = pa["jd"], pb["jd"]
    delta = (jda - jdb) if (jda is not None and jdb is not None) else None
    for label, period in BIO_CYCLES:
        if delta is None:
            add("nm_bio_%s_cos" % label, None)
            add("nm_bio_%s_frac" % label, None)
        else:
            add("nm_bio_%s_cos" % label, math.cos(2.0 * math.pi * delta / period))
            add("nm_bio_%s_frac" % label, (abs(delta) % period) / float(period))

    # --- H. modular relations between the two Julian day numbers --------------------------------
    # Residues only: |delta| mod m destroys the magnitude of the age gap, so nothing here can be
    # the age gap wearing a numerology hat.
    for m in JD_MODULI:
        add("nm_jdmod%d_res" % m, None if delta is None else (abs(delta) % m) / float(m))
    add("nm_jdmod7_same", None if delta is None else (1.0 if abs(delta) % 7 == 0 else 0.0))
    add("nm_jdmod9_same", None if delta is None else (1.0 if abs(delta) % 9 == 0 else 0.0))
    wlo, whi = _mm(None if jda is None else float(jda % 7),
                   None if jdb is None else float(jdb % 7))
    add("nm_weekday_min", wlo)      # the pair of weekdays, sorted so column order cannot be learnt
    add("nm_weekday_max", whi)

    # --- I. personal year / month / day cycles -------------------------------------------------
    # No wedding date exists, so the cycle is evaluated at the ONLY other real date: the partner's
    # birth.  "What personal year was A living through when B was born", and the mirror.
    def _cycle(px, py_):
        if px["m"] is None or px["d"] is None or py_["y"] is None:
            return (None, None, None)
        yr = _droot(_droot(px["m"]) + _droot(px["d"]) + _droot(py_["y"]))
        mo = _droot(yr + _droot(py_["m"])) if py_["m"] is not None else None
        dy = _droot(mo + _droot(py_["d"])) if (mo is not None and py_["d"] is not None) else None
        return (yr, mo, dy)

    ya, ma_, da_ = _cycle(pa, pb)
    yb, mb_, db_ = _cycle(pb, pa)
    for (va, vb, label) in ((ya, yb, "py"), (ma_, mb_, "pm"), (da_, db_, "pd")):
        lo, hi = _mm(va, vb)
        add("nm_%s_min" % label, lo)
        add("nm_%s_max" % label, hi)
        add("nm_%s_same" % label, _same(va, vb))
    add("nm_py_circdist", _circ(ya, yb, 9))

    # --- J. the nine-year epicycle on the birth YEARS (survives a year-only record) -------------
    yA, yB = pa["y"], pb["y"]
    if yA is None or yB is None:
        add("nm_year9_cos", None)
        add("nm_year9_frac", None)
        add("nm_year_sumroot", None)
    else:
        dy = yA - yB
        add("nm_year9_cos", math.cos(2.0 * math.pi * dy / 9.0))
        add("nm_year9_frac", (abs(dy) % 9) / 9.0)
        add("nm_year_sumroot", _droot(_dsum(yA) + _dsum(yB)))

    # --- K. one metadata column, so a model can tell "not applicable" from "computed" -----------
    add("nm_meta_n_full_dates", float((1 if pa["full"] else 0) + (1 if pb["full"] else 0)))


_NAMES = None


def _names():
    global _NAMES
    if _NAMES is None:
        acc = _Acc(True)
        _features(_person("0000-00-00"), _person("0000-00-00"), acc)
        _NAMES = acc.names
    return _NAMES


# ---------------------------------------------------------------- the contract ------------------

def build(df, Z, half):
    """See the module docstring.  Z and half are part of the contract but unused: numerology reads
    the written date, never a longitude, so this stays a pure function of df."""
    names = _names()
    k = len(names)
    n = len(df)
    X = np.full((n, k), NAN, dtype=np.float32)
    if n == 0:
        return X, list(names)

    a_col = df["dob_a"].tolist() if "dob_a" in df.columns else [None] * n
    b_col = df["dob_b"].tolist() if "dob_b" in df.columns else [None] * n

    cache = {}          # local, so build() stays pure; dates repeat a lot in this set

    def person(s):
        key = s if isinstance(s, str) else None
        if key in cache:
            return cache[key]
        p = _person(s)
        cache[key] = p
        return p

    acc = _Acc(False)
    for i in range(n):
        acc.vals = []
        _features(person(a_col[i]), person(b_col[i]), acc)
        if len(acc.vals) != k:
            raise RuntimeError("numerology_world: row %d produced %d values, expected %d"
                               % (i, len(acc.vals), k))
        X[i, :] = acc.vals
    return X, list(names)
