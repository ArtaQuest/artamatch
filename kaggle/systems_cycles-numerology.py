"""systems_cycles-numerology.py — the NUMEROLOGY & PURE CYCLES lens as pseudo-bodies.

Every system here is a PURE function of the birth date (the sidereal longitudes L are accepted for
interface parity and never read: nothing in this lens depends on a planet). State s of N becomes the
angle (s+1)*360/N on that system's own circle downstream; a constant offset (which day is "state 0")
is absorbed by the fitted phase, so only the cycle LENGTH matters — exactly as in build_systems.py.

Pure Python, standard library only, deterministic; runs unchanged under Pyodide in the browser.

NUMEROLOGY (Pythagorean, date-only — Chaldean vs Pythagorean concerns letters, not digits)
  num_lifepath            9   digit sum of YYYYMMDD reduced to 1..9. (Reducing the three
                              components first gives the same 1..9: a digit sum is congruent
                              mod 9 to its number.) IDENTICAL to build_systems.py num_lifepath.
  num_lifepath_master    12   the "keep the masters" variant: month, day and year are each
                              reduced keeping 11/22/33, summed, and the sum reduced keeping
                              11/22/33. States 0..8 = 1..9, 9 = 11, 10 = 22, 11 = 33.
  num_birthday           31   the calendar day itself, 1..31.
  num_birthday_reduced    9   the day reduced to 1..9 (this IS "the day reduced separately").
  num_attitude            9   month + day, reduced (a.k.a. the Sun number).
  num_maturity_birth      9   y + m + d as INTEGERS, the total reduced (the date-only "maturity"
                              of the lens; the name-based maturity number is disqualified).
  num_month_reduced       9   the month reduced (10->1, 11->2, 12->3).
  num_year_reduced        9   the year's digit sum reduced.
  num_pinnacle2           9   day + year (each reduced), reduced.        [beyond the lens: the
  num_pinnacle3           9   pinnacle1 + pinnacle2, reduced.              classical pinnacles
  num_pinnacle4           9   month + year (each reduced), reduced.        and challenges are
  num_challenge1          9   |month - day| on reduced components, 0..8.  the only OTHER
  num_challenge2          9   |day - year|                                 date-only numbers
  num_challenge3          9   |challenge1 - challenge2|                    in the Pythagorean
  num_challenge4          9   |month - year|                               canon; pinnacle1 =
                                                                           attitude, so skipped]

BIORHYTHMS (state = JDN mod period; his minus hers is the phase difference between their two
cycles — exactly the traditional biorhythm "compatibility" percentage)
  bio_physical 23 · bio_emotional 28 · bio_intellectual 33 · bio_intuitive 38 ·
  bio_aesthetic 43 · bio_spiritual 53

KABBALAH / DIVINATION DAY CYCLES (JDN mod N)
  kab_day_letter 22 (the 22 Hebrew letters) · kab_72_names 72 (Shem HaMephorash) ·
  iching_day_hexagram 64 (King Wen sequence)

DELIBERATELY SKIPPED (documented, not forgotten)
  * tarot major arcana of the day (22, JDN mod 22): the same cycle as the day letter up to a
    constant offset, which the fitted phase absorbs — a duplicate pseudo-body, so skipped.
  * the 9-year personal cycle: needs a reference year (the year of the match), not date-only.
  * zodiac-numerology cross (sun sign x life path): a product of two states, not a state.
  * num_day_reduced: identical to num_birthday_reduced.
  * JDN mod 7 / 9 / 13 / 60: covered by other lenses (weekday, Lord of the Night, Tzolkin tone,
    sexagenary day) — not duplicated here.
"""

SLUG = "cycles-numerology"


# ---------------------------------------------------------------- helpers
def jdn(y, m, d):
    """Julian Day Number at noon, proleptic Gregorian (Fliegel & Van Flandern 1968)."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def ayanamsa(y):
    """Lahiri ayanamsa in degrees for a birth year (good to a few arcminutes). Unused by this
    lens — kept so every systems_<tradition>.py module carries the same two helpers."""
    return 23.853 + 0.013971 * (y - 2000)


def digit_sum(n):
    return sum(int(c) for c in str(abs(int(n))))


def red9(t):
    """Reduce to a single digit 1..9 (0 stays 0; never produced from a date)."""
    t = int(t)
    while t > 9:
        t = digit_sum(t)
    return t


MASTERS = (11, 22, 33)


def red_master(t):
    """Reduce to 1..9 but stop on a master number 11, 22, 33."""
    t = int(t)
    while t > 9 and t not in MASTERS:
        t = digit_sum(t)
    return t


# ---------------------------------------------------------------- numerology
def num_lifepath(y, m, d, L=None):
    return red9(digit_sum(y) + digit_sum(m) + digit_sum(d)) - 1


MASTER_STATE = {11: 9, 22: 10, 33: 11}


def num_lifepath_master(y, m, d, L=None):
    v = red_master(red_master(m) + red_master(d) + red_master(digit_sum(y)))
    return MASTER_STATE.get(v, v - 1)


def num_birthday(y, m, d, L=None):
    return d - 1


def num_birthday_reduced(y, m, d, L=None):
    return red9(d) - 1


def num_attitude(y, m, d, L=None):
    return red9(m + d) - 1


def num_maturity_birth(y, m, d, L=None):
    return red9(y + m + d) - 1


def num_month_reduced(y, m, d, L=None):
    return red9(m) - 1


def num_year_reduced(y, m, d, L=None):
    return red9(digit_sum(y)) - 1


def num_pinnacle2(y, m, d, L=None):
    return red9(red9(d) + red9(digit_sum(y))) - 1


def num_pinnacle3(y, m, d, L=None):
    p1 = red9(red9(m) + red9(d))
    p2 = red9(red9(d) + red9(digit_sum(y)))
    return red9(p1 + p2) - 1


def num_pinnacle4(y, m, d, L=None):
    return red9(red9(m) + red9(digit_sum(y))) - 1


def _challenges(y, m, d):
    rm, rd, ry = red9(m), red9(d), red9(digit_sum(y))
    c1 = abs(rm - rd)
    c2 = abs(rd - ry)
    c3 = abs(c1 - c2)
    c4 = abs(rm - ry)
    return c1, c2, c3, c4                       # each in 0..8


def num_challenge1(y, m, d, L=None): return _challenges(y, m, d)[0]
def num_challenge2(y, m, d, L=None): return _challenges(y, m, d)[1]
def num_challenge3(y, m, d, L=None): return _challenges(y, m, d)[2]
def num_challenge4(y, m, d, L=None): return _challenges(y, m, d)[3]


# ---------------------------------------------------------------- pure cycles
def _mod(period):
    def fn(y, m, d, L=None):
        return jdn(y, m, d) % period
    fn.__name__ = f"jdn_mod_{period}"
    return fn


bio_physical = _mod(23)
bio_emotional = _mod(28)
bio_intellectual = _mod(33)
bio_intuitive = _mod(38)
bio_aesthetic = _mod(43)
bio_spiritual = _mod(53)
kab_day_letter = _mod(22)
kab_72_names = _mod(72)
iching_day_hexagram = _mod(64)

# Reference tables (documentation; the state index is what the model sees).
HEBREW_LETTERS = ["alef", "bet", "gimel", "dalet", "he", "vav", "zayin", "chet", "tet", "yod",
                  "kaf", "lamed", "mem", "nun", "samekh", "ayin", "pe", "tsadi", "qof", "resh",
                  "shin", "tav"]
KING_WEN = ["Qian", "Kun", "Zhun", "Meng", "Xu", "Song", "Shi", "Bi", "Xiao Chu", "Lu", "Tai",
            "Pi", "Tong Ren", "Da You", "Qian(15)", "Yu", "Sui", "Gu", "Lin", "Guan", "Shi He",
            "Bi(22)", "Bo", "Fu", "Wu Wang", "Da Chu", "Yi", "Da Guo", "Kan", "Li", "Xian",
            "Heng", "Dun", "Da Zhuang", "Jin", "Ming Yi", "Jia Ren", "Kui", "Jian", "Xie", "Sun",
            "Yi(42)", "Guai", "Gou", "Cui", "Sheng", "Kun(47)", "Jing", "Ge", "Ding", "Zhen",
            "Gen", "Jian(53)", "Gui Mei", "Feng", "Lu(56)", "Xun", "Dui", "Huan", "Jie",
            "Zhong Fu", "Xiao Guo", "Ji Ji", "Wei Ji"]
assert len(HEBREW_LETTERS) == 22 and len(KING_WEN) == 64


def _S(name, n, desc, fn):
    return {"name": f"{SLUG}_{name}", "n": n, "desc": desc, "fn": fn}


SYSTEMS = [
    _S("num_lifepath", 9, "life path: digit sum of YYYYMMDD reduced to 1..9", num_lifepath),
    _S("num_lifepath_master", 12, "life path keeping masters: 1..9, 11, 22, 33 (component method)", num_lifepath_master),
    _S("num_birthday", 31, "birthday number: the calendar day 1..31", num_birthday),
    _S("num_birthday_reduced", 9, "birthday number reduced to 1..9 (= day reduced)", num_birthday_reduced),
    _S("num_attitude", 9, "attitude / Sun number: month + day reduced", num_attitude),
    _S("num_maturity_birth", 9, "maturity-of-birth: y + m + d (integers) reduced", num_maturity_birth),
    _S("num_month_reduced", 9, "birth month reduced to 1..9", num_month_reduced),
    _S("num_year_reduced", 9, "birth year digit sum reduced to 1..9", num_year_reduced),
    _S("num_pinnacle2", 9, "second pinnacle: day + year reduced", num_pinnacle2),
    _S("num_pinnacle3", 9, "third pinnacle: pinnacle1 + pinnacle2 reduced", num_pinnacle3),
    _S("num_pinnacle4", 9, "fourth pinnacle: month + year reduced", num_pinnacle4),
    _S("num_challenge1", 9, "first challenge |month - day| (reduced components), 0..8", num_challenge1),
    _S("num_challenge2", 9, "second challenge |day - year|, 0..8", num_challenge2),
    _S("num_challenge3", 9, "third challenge |challenge1 - challenge2|, 0..8", num_challenge3),
    _S("num_challenge4", 9, "fourth challenge |month - year|, 0..8", num_challenge4),
    _S("bio_physical", 23, "biorhythm physical cycle phase: JDN mod 23", bio_physical),
    _S("bio_emotional", 28, "biorhythm emotional cycle phase: JDN mod 28", bio_emotional),
    _S("bio_intellectual", 33, "biorhythm intellectual cycle phase: JDN mod 33", bio_intellectual),
    _S("bio_intuitive", 38, "biorhythm intuitive cycle phase: JDN mod 38", bio_intuitive),
    _S("bio_aesthetic", 43, "biorhythm aesthetic cycle phase: JDN mod 43", bio_aesthetic),
    _S("bio_spiritual", 53, "biorhythm spiritual cycle phase: JDN mod 53", bio_spiritual),
    _S("kab_day_letter", 22, "Kabbalistic day letter (22 Hebrew letters): JDN mod 22", kab_day_letter),
    _S("kab_72_names", 72, "the 72 names of God cycle: JDN mod 72", kab_72_names),
    _S("iching_day_hexagram", 64, "I Ching hexagram of the day (King Wen order): JDN mod 64", iching_day_hexagram),
]


# ---------------------------------------------------------------- smoke test
SMOKE_DATES = [
    (1600, 1, 1), (1600, 2, 29), (1617, 11, 22), (1650, 7, 4), (1666, 6, 6), (1700, 3, 1),
    (1721, 12, 31), (1750, 5, 15), (1776, 7, 4), (1789, 7, 14), (1800, 2, 28), (1815, 6, 18),
    (1833, 3, 22), (1850, 10, 10), (1869, 11, 11), (1879, 3, 14), (1888, 8, 8), (1900, 2, 28),
    (1911, 11, 11), (1922, 2, 22), (1933, 3, 3), (1945, 8, 15), (1955, 2, 24), (1966, 6, 29),
    (1979, 3, 22), (1984, 12, 31), (1999, 9, 9), (2000, 1, 1), (2000, 12, 31),
]
BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
          "pluto", "node", "chiron", "lilith"]


def smoke():
    checked = 0
    for (y, m, d) in SMOKE_DATES:
        L = {b: (i * 27.3 + y % 360 + m * 11.1 + d) % 360.0 for i, b in enumerate(BODIES)}
        for s in SYSTEMS:
            v = s["fn"](y, m, d, L)
            assert isinstance(v, int), (s["name"], y, m, d, v)
            assert 0 <= v < s["n"], (s["name"], y, m, d, v, s["n"])
            assert s["fn"](y, m, d, L) == v          # deterministic
            checked += 1
    # anchors
    assert jdn(2000, 1, 1) == 2451545 and jdn(1600, 1, 1) == 2305448
    assert num_lifepath(1979, 3, 22) == red9(1 + 9 + 7 + 9 + 3 + 2 + 2) - 1
    assert num_lifepath_master(1979, 3, 22) == 11        # 3 + 22 + 8 = 33
    assert num_lifepath_master(1966, 11, 22) == 0        # 11 + 22 + 22 = 55 -> 10 -> 1
    assert num_lifepath_master(1911, 11, 11) == 6        # 11 + 11 + (1+9+1+1=12->3) = 25 -> 7
    assert num_lifepath_master(1922, 2, 22) == 9         # 2 + 22 + (14->5) = 29 -> 11 (master)
    return checked


if __name__ == "__main__":
    n = smoke()
    print(f"smoke ok: {len(SYSTEMS)} systems x {len(SMOKE_DATES)} dates = {n} states in range")
