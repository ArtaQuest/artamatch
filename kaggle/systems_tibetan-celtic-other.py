"""systems_tibetan-celtic-other.py — the OTHER TRADITIONS lens as PSEUDO-BODIES for the ArtaMatch
phasor fitter: Tibetan year cycles (animal, element, gender, rabjung 60, mewa, parkha), the Celtic
tree calendar (+ the fixed-date wheel of the year), the Burmese Mahabote, Sun Bear's medicine-wheel
birth totems, the popular Egyptian "twelve gods" date table, and the Hellenic civil lunar day.

Contract (pseudo-body round, 2026-09-03):
  SYSTEMS = [{"name": "tibetan-celtic-other_<system>", "n": N, "desc": ..., "fn": fn}, ...]
  fn(y, m, d, L) -> int state in [0, N-1].  y/m/d is the proleptic GREGORIAN civil birth date, L a
  dict of the person's SIDEREAL longitudes in degrees (Lahiri, 12:00 UT) plus L["_female"] (bool)
  for the gendered parkha.  Pure Python, standard library only, deterministic, no network — the
  same code runs in the browser under Pyodide.  A state s of N is placed at (s+1)*360/N degrees on
  the system's own circle by the BUILDER, not here.  A constant offset in a cycle is absorbed by the
  fitted phase; the cycle LENGTH and every BOUNDARY are what matter, and those are stated below.

Nothing here reads the label, the record depth or a name.  Only the Tibetan systems need the sky
(the Sun and the new moons of the Losar window) and they compute it from the DATE with a
low-precision solar theory and Meeus' true-new-moon series, so his and her states are produced by
the same rule whatever L holds; L is accepted for interface parity and read only for "_female".

TIBETAN  (Phugpa tradition; the year changes at LOSAR, not at 1 January and not at Li Chun)
  The Tibetan animals and elements are the Chinese sexagenary cycle (1984 = Wood-Rat, male), but the
  year begins at Losar, the first day of Hor month 1.  Rule used (documented approximation of the
  Phugpa calendar, which we do not reproduce table-for-table):
      Losar(y) = the civil day AFTER the first true new moon whose instant, shifted 6 hours
                 earlier, falls at or after the Sun reaches THRESHOLD(y) tropical, where
                 THRESHOLD(2000) = 315 deg (Li Chun) and THRESHOLD drifts by -0.0283 deg per year
                 into the past (the Phugpa mean year is 365.2706 d, longer than the tropical year
                 by 0.0283 d, so the Phugpa seasons slide later by one day per ~35 years).
      The 6-hour shift is the empirical daybreak convention that reproduces the published Losar
      dates 2000-2020 (checked in the smoke test: 2000-02-06, 2001-02-24, 2003-03-03, 2006-02-28,
      2008-02-07, 2009-02-25, 2010-02-14, 2011-03-05, 2019-02-05).  Expected error: +-1 day at the
      boundary; a birth on a Losar day may fall in the wrong year.  Only births in Jan-Mar are ever
      affected.
  tibetan_year_animal   12  (TY-4) mod 12: Rat 0, Ox 1, Tiger 2, Hare 3, Dragon 4, Snake 5, Horse 6,
                            Sheep 7, Monkey 8, Bird 9, Dog 10, Pig 11.
  tibetan_year_element   5  ((TY-4) mod 10)//2: wood 0, fire 1, earth 2, iron 3, water 4.
  tibetan_year_gender    2  (TY-4) mod 2: 0 male (pho), 1 female (mo).
  tibetan_year60        60  rabjung position (TY-1027) mod 60, Fire-Hare 1027 = 0 (the first rabjung).
  tibetan_mewa           9  the year's mewa (nine-square number): mewa = 11 - digitroot(TY), 10 -> 1
                            (1984 Wood-Rat = 7 red, 1985 = 6 white, 2000 = 9 maroon, 2020 = 7 red,
                            decreasing one per year, period 9).  State = mewa - 1.
  tibetan_parkha         8  natal parkha (skyes spar) from the year ANIMAL and the person's gender.
                            Ring (clockwise from south): Li 0, Khon 1, Dwa 2, Khen 3, Kham 4, Gin 5,
                            Zin 6, Zon 7.  Male: count clockwise from Li for the Rat year —
                            Rat Li, Ox Khon, Tiger Dwa, Hare Khen, Dragon Kham, Snake Gin, Horse Zin,
                            Sheep Zon, Monkey Li, Bird Khon, Dog Dwa, Pig Khen.  Female: count
                            counter-clockwise from Kham — Rat Kham, Ox Khen, Tiger Dwa, Hare Khon,
                            Dragon Li, Snake Zon, Horse Zin, Sheep Gin, Monkey Kham, Bird Khen,
                            Dog Dwa, Pig Khon.  State = ring position (so the angle IS the compass).
                            Gender from L["_female"] (missing -> male).
  tibetan_life_element   5  srog (life-force) element, fixed by the ANIMAL: Rat water, Ox earth,
                            Tiger wood, Hare wood, Dragon earth, Snake fire, Horse fire, Sheep earth,
                            Monkey iron, Bird iron, Dog earth, Pig water (the Chinese hidden branch
                            element under the Losar boundary).

CELTIC  (fixed Gregorian date tables; leap day Feb 29 falls in the range that holds Feb 28)
  celtic_tree           13  Robert Graves' Beth-Luis-Nion tree calendar, 13 "lunar months" of 28 days:
                            Birch Dec 24-Jan 20, Rowan Jan 21-Feb 17, Ash Feb 18-Mar 17,
                            Alder Mar 18-Apr 14, Willow Apr 15-May 12, Hawthorn May 13-Jun 9,
                            Oak Jun 10-Jul 7, Holly Jul 8-Aug 4, Hazel Aug 5-Sep 1, Vine Sep 2-29,
                            Ivy Sep 30-Oct 27, Reed Oct 28-Nov 24, Elder Nov 25-Dec 23 (Dec 23, the
                            "nameless day", is placed in Elder).
  celtic_animal          —  the Celtic animal zodiac (Stag, Cat, Adder, Fox, Bull, Seahorse, Wren,
                            Horse, Salmon, Swan, Butterfly, Wolf, Hawk) uses EXACTLY the tree
                            calendar's thirteen ranges: the table is kept in code and the smoke test
                            asserts the identity on every day of the year, and it is NOT added as a
                            pseudo-body (a duplicate with a constant offset of zero).
  celtic_wheel8          8  the eight-fold wheel of the year on its FIXED calendar dates: Yule Dec 21,
                            Imbolc Feb 1, Ostara Mar 21, Beltane May 1, Litha Jun 21, Lughnasadh
                            Aug 1, Mabon Sep 21, Samhain Nov 1 (each festival opens its eighth).
  celtic_fire_season     4  the four Gaelic fire-festival quarters: Samhain Nov 1-Jan 31,
                            Imbolc Feb 1-Apr 30, Beltane May 1-Jul 31, Lughnasadh Aug 1-Oct 31.
                            (Both wheels are coarse quantisations of the tropical Sun the bank
                            already carries, on calendar dates rather than solar degrees.)

BURMESE MAHABOTE  (weekday x Burmese-year remainder)
  Burmese Era year BE = CE - 638 from the Thingyan new year day (Atat + 1) of that year, else
  CE - 639.  The new year day is the day after the Sun's Burmese Mesha sankranti: with the Burmese
  Surya Siddhanta constants SY = 1577917828/4320000 = 365.2587565 d and epoch MO = 1954168.050623,
  new-year JDN = floor(SY*BE + MO) + 2 (calibrated: BE 1362 = 17 April 2000; it drifts ~1.6 days
  per century against the Gregorian calendar, ~10-11 April in 1600).
  Weekday numbers (Mahabote): Sunday 1, Monday 2, Tuesday 3, Wednesday 4, Thursday 5, Friday 6,
  Saturday 0 (Rahu = Wednesday afternoon, number 8, needs the birth hour and is folded into 4).
  mahabote_animal        7  the birth-day animal: Sunday Garuda 0, Monday Tiger 1, Tuesday Lion 2,
                            Wednesday Elephant 3, Thursday Rat 4, Friday Guinea-pig 5, Saturday
                            Naga 6.  (This is the plain weekday, listed because the lens names it.)
  mahabote_remainder     7  BE mod 7 (0..6) — which planet's year it is (0 Saturn, 1 Sun, 2 Moon,
                            3 Mars, 4 Mercury, 5 Jupiter, 6 Venus).
  mahabote_house         7  the house of the birth-day planet.  Planet sequence around the chart:
                            1 2 3 4 0 5 (8) 6 = Sun Moon Mars Mercury Saturn Jupiter (Rahu) Venus;
                            the remainder's planet sits in Binga (house 0) and the sequence runs on
                            through Atun 1, Yaza 2, Adipati 3, Marana 4, Thike 5, Puti 6.
                            house = (pos(weekday planet) - pos(remainder planet)) mod 7.

NATIVE AMERICAN MEDICINE WHEEL  (Sun Bear & Wabun, "The Medicine Wheel: Earth Astrology", 1980)
  medwheel_totem        12  Snow Goose Dec 22-Jan 19, Otter Jan 20-Feb 18, Wolf Feb 19-Mar 20,
                            Red Hawk Mar 21-Apr 19, Beaver Apr 20-May 20, Deer May 21-Jun 20,
                            Flicker Jun 21-Jul 22, Sturgeon Jul 23-Aug 22, Brown Bear Aug 23-Sep 22,
                            Raven Sep 23-Oct 23, Snake Oct 24-Nov 21, Elk Nov 22-Dec 21.
  medwheel_clan          4  elemental clan = totem mod 4: Turtle (earth: Snow Goose, Beaver, Brown
                            Bear) 0, Butterfly (air: Otter, Deer, Raven) 1, Frog (water: Wolf,
                            Flicker, Snake) 2, Thunderbird (fire: Red Hawk, Sturgeon, Elk) 3.
  medwheel_spirit_keeper 4  the season's Spirit Keeper = totem // 3: Waboose (north, winter) 0,
                            Wabun (east, spring) 1, Shawnodese (south, summer) 2, Mudjekeewis
                            (west, autumn) 3.

EGYPTIAN  (the popular "twelve gods" date table — multiple ranges per god, full-year coverage)
  egyptian_god          12  The Nile 0: Jan 1-7, Jun 19-28, Sep 1-7, Nov 18-26 · Amon-Ra 1: Jan 8-21,
                            Feb 1-11 · Mut 2: Jan 22-31, Sep 8-22 · Geb 3: Feb 12-29, Aug 20-31 ·
                            Osiris 4: Mar 1-10, Nov 27-Dec 18 · Isis 5: Mar 11-31, Oct 18-29,
                            Dec 19-31 · Thoth 6: Apr 1-19, Nov 8-17 · Horus 7: Apr 20-May 7,
                            Aug 12-19 · Anubis 8: May 8-27, Jun 29-Jul 13 · Seth 9: May 28-Jun 18,
                            Sep 28-Oct 2 · Bastet 10: Jul 14-28, Sep 23-27, Oct 3-17 · Sekhmet 11:
                            Jul 29-Aug 11, Oct 30-Nov 7.  The smoke test asserts every day of a
                            leap year is covered exactly once.  Not a cycle: the god index is an
                            arbitrary order, used as the lens asks.

HELLENIC
  hellenic_lunar_day    30  the civil lunar day of the Attic/Hesiodic month: the number of civil days
                            (UT dates) elapsed since the date of the last true new moon, 0 = the
                            new-moon day (noumenia), clipped to 29.  It is NOT the tithi (which is
                            12-degree steps of elongation, vedic_tithi): the two drift apart by up to
                            a day inside a month and re-align at each new moon.  Included because it
                            is not identical; expect it to be a near-duplicate.

SKIPPED, and why
  * Celtic animal zodiac: identical ranges to the tree calendar (asserted) — duplicate.
  * Aztec year bearer: in the mesoamerican lens.  Japanese eto: the Chinese cycle, east-asian lens.
  * Tibetan lunar day (tshes) and lunar mansion (gyukar): the tithi and the nakshatra, vedic lens.
  * Tibetan body/power/luck (lu, wang, lungta) elements: the published tables disagree between
    lineages and I could not fix one with confidence; only srog (life), which every source ties to
    the animal, is included.
  * Zulu / Yoruba systems: not computable from a date (initiatory/divinatory, no calendar rule).
  * Egyptian decans (36): a 10-degree quantisation of the tropical Sun — the bank carries the Sun.
"""
import math

SLUG = "tibetan-celtic-other"


# ---------------------------------------------------------------- helpers (stdlib only)
def jdn(y, m, d):
    """Fliegel & Van Flandern (1968) Julian Day Number of a proleptic Gregorian civil date."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def ayanamsa(y):
    """Lahiri ayanamsa in degrees, linear in the year (good to a few arcminutes)."""
    return 23.853 + 0.013971 * (y - 2000)


def _sind(x):
    return math.sin(math.radians(x))


def sun_lon_jd(jd):
    """Tropical longitude of the Sun (deg) at Julian Date jd; low-precision theory (~0.01 deg)."""
    n = jd - 2451545.0
    Lm = (280.460 + 0.9856474 * n) % 360.0
    g = (357.528 + 0.9856003 * n) % 360.0
    return (Lm + 1.915 * _sind(g) + 0.020 * _sind(2 * g)) % 360.0


def sun_reaches(lon, jd_guess):
    """The JD near jd_guess at which the tropical Sun reaches `lon` degrees (Newton on the mean rate)."""
    t = float(jd_guess)
    for _ in range(6):
        dl = ((lon - sun_lon_jd(t) + 180.0) % 360.0) - 180.0
        t += dl / 0.9856474
    return t


def new_moon_jd(k):
    """Meeus (Astronomical Algorithms ch. 49): JDE of the true new moon of lunation number k
    (k = 0 is the new moon of 2000-01-06).  Principal periodic terms; error ~ minutes."""
    T = k / 1236.85
    jde = (2451550.09766 + 29.530588861 * k + 0.00015437 * T * T
           - 0.000000150 * T ** 3 + 0.00000000073 * T ** 4)
    E = 1.0 - 0.002516 * T - 0.0000074 * T * T
    M = (2.5534 + 29.10535670 * k - 0.0000014 * T * T - 0.00000011 * T ** 3) % 360.0
    Mp = (201.5643 + 385.81693528 * k + 0.0107582 * T * T + 0.00001238 * T ** 3
          - 0.000000058 * T ** 4) % 360.0
    F = (160.7108 + 390.67050284 * k - 0.0016118 * T * T - 0.00000227 * T ** 3
         + 0.000000011 * T ** 4) % 360.0
    Om = (124.7746 - 1.56375588 * k + 0.0020672 * T * T + 0.00000215 * T ** 3) % 360.0
    s = _sind
    corr = (-0.40720 * s(Mp) + 0.17241 * E * s(M) + 0.01608 * s(2 * Mp) + 0.01039 * s(2 * F)
            + 0.00739 * E * s(Mp - M) - 0.00514 * E * s(Mp + M) + 0.00208 * E * E * s(2 * M)
            - 0.00111 * s(Mp - 2 * F) - 0.00057 * s(Mp + 2 * F) + 0.00056 * E * s(2 * Mp + M)
            - 0.00042 * s(3 * Mp) + 0.00042 * E * s(M + 2 * F) + 0.00038 * E * s(M - 2 * F)
            - 0.00024 * E * s(2 * Mp - M) - 0.00017 * s(Om) - 0.00007 * s(Mp + 2 * M)
            + 0.00004 * s(2 * Mp - 2 * F) + 0.00004 * s(3 * M) + 0.00003 * s(Mp + M - 2 * F)
            + 0.00003 * s(2 * Mp + 2 * F) - 0.00003 * s(Mp + M + 2 * F) + 0.00003 * s(Mp - M + 2 * F)
            - 0.00002 * s(Mp - M - 2 * F) - 0.00002 * s(3 * Mp + M) + 0.00002 * s(4 * Mp))
    return jde + corr


def first_new_moon_at_or_after(jd):
    """JDE of the first true new moon at or after Julian Date jd."""
    k0 = math.floor((jd - 2451550.09766) / 29.530588861) - 1
    for k in range(k0, k0 + 4):
        nm = new_moon_jd(k)
        if nm >= jd:
            return nm
    return new_moon_jd(k0 + 4)  # unreachable in practice


def last_new_moon_before(jd):
    """JDE of the last true new moon strictly before Julian Date jd."""
    k0 = math.floor((jd - 2451550.09766) / 29.530588861) + 1
    for k in range(k0, k0 - 4, -1):
        nm = new_moon_jd(k)
        if nm < jd:
            return nm
    return new_moon_jd(k0 - 4)  # unreachable in practice


def jd_to_jdn(jd):
    """Civil date (as a JDN at noon) holding the instant jd (UT)."""
    return int(math.floor(jd + 0.5))


def digit_root(t):
    t = abs(int(t))
    while t > 9:
        t = sum(int(c) for c in str(t))
    return t


def is_female(L):
    try:
        return bool(L.get("_female", False))
    except Exception:
        return False


# ---------------------------------------------------------------- Tibetan (Losar year)
LOSAR_THRESHOLD_2000 = 315.0        # Li Chun; the 2000-2020 Losar dates all follow the first new moon after it
LOSAR_DRIFT_PER_YEAR = 0.0283       # Phugpa year 365.2706 d - tropical 365.2422 d, in degrees of Sun per year
LOSAR_DAYBREAK_SHIFT = 6.0 / 24.0   # new-moon instant is dated after shifting 6 h earlier (empirical)
_LOSAR_CACHE = {}


def losar_jdn(y):
    """JDN of Losar (Tibetan new year's day) in Gregorian year y — documented approximation."""
    v = _LOSAR_CACHE.get(y)
    if v is not None:
        return v
    threshold = (LOSAR_THRESHOLD_2000 - LOSAR_DRIFT_PER_YEAR * (2000 - y)) % 360.0
    t_thr = sun_reaches(threshold, jdn(y, 2, 4))
    nm = first_new_moon_at_or_after(t_thr)
    v = jd_to_jdn(nm - LOSAR_DAYBREAK_SHIFT) + 1
    _LOSAR_CACHE[y] = v
    return v


def tibetan_year(y, m, d):
    """The Tibetan (Losar) year holding the civil date."""
    if m > 3:
        return y
    return y if jdn(y, m, d) >= losar_jdn(y) else y - 1


def tibetan_year_animal(y, m, d, L):
    return (tibetan_year(y, m, d) - 4) % 12


def tibetan_year_element(y, m, d, L):
    return ((tibetan_year(y, m, d) - 4) % 10) // 2


def tibetan_year_gender(y, m, d, L):
    return (tibetan_year(y, m, d) - 4) % 2


def tibetan_year60(y, m, d, L):
    return (tibetan_year(y, m, d) - 1027) % 60


def mewa_of_year(ty):
    """Mewa number 1..9 of a Tibetan year: 11 - digitroot(year), 10 -> 1."""
    v = 11 - digit_root(ty)
    return v - 9 if v > 9 else v


def tibetan_mewa(y, m, d, L):
    return mewa_of_year(tibetan_year(y, m, d)) - 1


# Ring positions: Li 0 (S), Khon 1 (SW), Dwa 2 (W), Khen 3 (NW), Kham 4 (N), Gin 5 (NE), Zin 6 (E), Zon 7 (SE)
PARKHA_NAMES = ["Li", "Khon", "Dwa", "Khen", "Kham", "Gin", "Zin", "Zon"]
#                  Rat Ox Tiger Hare Dragon Snake Horse Sheep Monkey Bird Dog Pig
PARKHA_MALE = [0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 2, 3]      # clockwise from Li
PARKHA_FEMALE = [4, 3, 2, 1, 0, 7, 6, 5, 4, 3, 2, 1]    # counter-clockwise from Kham
assert PARKHA_MALE == [a % 8 for a in range(12)]
assert PARKHA_FEMALE == [(4 - a) % 8 for a in range(12)]


def tibetan_parkha(y, m, d, L):
    a = tibetan_year_animal(y, m, d, L)
    return PARKHA_FEMALE[a] if is_female(L) else PARKHA_MALE[a]


# srog element by animal: wood 0, fire 1, earth 2, iron 3, water 4
#                 Rat Ox Tiger Hare Dragon Snake Horse Sheep Monkey Bird Dog Pig
LIFE_ELEMENT = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]


def tibetan_life_element(y, m, d, L):
    return LIFE_ELEMENT[tibetan_year_animal(y, m, d, L)]


# ---------------------------------------------------------------- fixed date-range tables
def _range_state(m, d, starts):
    """Index of the range holding (m, d).  `starts` is a list of (month, day) range openings in
    calendar order whose FIRST entry is the range that wraps the New Year (it opens in December)."""
    md = m * 100 + d
    if md >= starts[0][0] * 100 + starts[0][1]:      # the wrap-around range opens in December
        return 0
    for i in range(len(starts) - 1, 0, -1):
        sm, sd = starts[i]
        if md >= sm * 100 + sd:
            return i
    return 0


CELTIC_TREES = ["Birch", "Rowan", "Ash", "Alder", "Willow", "Hawthorn", "Oak", "Holly", "Hazel",
                "Vine", "Ivy", "Reed", "Elder"]
CELTIC_TREE_STARTS = [(12, 24), (1, 21), (2, 18), (3, 18), (4, 15), (5, 13), (6, 10), (7, 8), (8, 5),
                      (9, 2), (9, 30), (10, 28), (11, 25)]
CELTIC_ANIMALS = ["Stag", "Cat", "Adder", "Fox", "Bull", "Seahorse", "Wren", "Horse", "Salmon",
                  "Swan", "Butterfly", "Wolf", "Hawk"]
CELTIC_ANIMAL_STARTS = [(12, 24), (1, 21), (2, 18), (3, 18), (4, 15), (5, 13), (6, 10), (7, 8), (8, 5),
                        (9, 2), (9, 30), (10, 28), (11, 25)]   # identical to the trees — NOT a body


def celtic_tree(y, m, d, L):
    return _range_state(m, d, CELTIC_TREE_STARTS)


def celtic_animal(y, m, d, L):
    """Kept for the identity check only; not in SYSTEMS."""
    return _range_state(m, d, CELTIC_ANIMAL_STARTS)


WHEEL8 = ["Yule", "Imbolc", "Ostara", "Beltane", "Litha", "Lughnasadh", "Mabon", "Samhain"]
WHEEL8_STARTS = [(12, 21), (2, 1), (3, 21), (5, 1), (6, 21), (8, 1), (9, 21), (11, 1)]


def celtic_wheel8(y, m, d, L):
    return _range_state(m, d, WHEEL8_STARTS)


FIRE_SEASONS = ["Samhain", "Imbolc", "Beltane", "Lughnasadh"]
FIRE_SEASON_STARTS = [(11, 1), (2, 1), (5, 1), (8, 1)]


def celtic_fire_season(y, m, d, L):
    return _range_state(m, d, FIRE_SEASON_STARTS)


MEDWHEEL_TOTEMS = ["Snow Goose", "Otter", "Wolf", "Red Hawk", "Beaver", "Deer", "Flicker",
                   "Sturgeon", "Brown Bear", "Raven", "Snake", "Elk"]
MEDWHEEL_STARTS = [(12, 22), (1, 20), (2, 19), (3, 21), (4, 20), (5, 21), (6, 21), (7, 23), (8, 23),
                   (9, 23), (10, 24), (11, 22)]
MEDWHEEL_CLANS = ["Turtle", "Butterfly", "Frog", "Thunderbird"]
SPIRIT_KEEPERS = ["Waboose", "Wabun", "Shawnodese", "Mudjekeewis"]


def medwheel_totem(y, m, d, L):
    return _range_state(m, d, MEDWHEEL_STARTS)


def medwheel_clan(y, m, d, L):
    return medwheel_totem(y, m, d, L) % 4


def medwheel_spirit_keeper(y, m, d, L):
    return medwheel_totem(y, m, d, L) // 3


EGYPTIAN_GODS = ["The Nile", "Amon-Ra", "Mut", "Geb", "Osiris", "Isis", "Thoth", "Horus", "Anubis",
                 "Seth", "Bastet", "Sekhmet"]
# (start month, start day, end month, end day, god index) — inclusive ranges
EGYPTIAN_RANGES = [
    (1, 1, 1, 7, 0), (6, 19, 6, 28, 0), (9, 1, 9, 7, 0), (11, 18, 11, 26, 0),
    (1, 8, 1, 21, 1), (2, 1, 2, 11, 1),
    (1, 22, 1, 31, 2), (9, 8, 9, 22, 2),
    (2, 12, 2, 29, 3), (8, 20, 8, 31, 3),
    (3, 1, 3, 10, 4), (11, 27, 12, 18, 4),
    (3, 11, 3, 31, 5), (10, 18, 10, 29, 5), (12, 19, 12, 31, 5),
    (4, 1, 4, 19, 6), (11, 8, 11, 17, 6),
    (4, 20, 5, 7, 7), (8, 12, 8, 19, 7),
    (5, 8, 5, 27, 8), (6, 29, 7, 13, 8),
    (5, 28, 6, 18, 9), (9, 28, 10, 2, 9),
    (7, 14, 7, 28, 10), (9, 23, 9, 27, 10), (10, 3, 10, 17, 10),
    (7, 29, 8, 11, 11), (10, 30, 11, 7, 11),
]


def egyptian_god(y, m, d, L):
    md = m * 100 + d
    for (m1, d1, m2, d2, g) in EGYPTIAN_RANGES:
        if m1 * 100 + d1 <= md <= m2 * 100 + d2:
            return g
    return 0  # unreachable: the table covers every day (asserted in the smoke test)


# ---------------------------------------------------------------- Burmese Mahabote
BURMESE_SY = 1577917828.0 / 4320000.0     # 365.2587565 days
BURMESE_MO = 1954168.050623                # Burmese epoch (JD)
_BNY_CACHE = {}


def burmese_new_year_jdn(be):
    """JDN of the Burmese new year's day of Burmese-Era year `be` (day after Thingyan Atat)."""
    v = _BNY_CACHE.get(be)
    if v is None:
        v = int(math.floor(BURMESE_SY * be + BURMESE_MO)) + 2
        _BNY_CACHE[be] = v
    return v


def burmese_year(y, m, d):
    be = y - 638
    return be if jdn(y, m, d) >= burmese_new_year_jdn(be) else be - 1


def mahabote_weekday(y, m, d):
    """Sunday 1 .. Friday 6, Saturday 0."""
    return ((jdn(y, m, d) + 1) % 7 + 1) % 7


MAHABOTE_ANIMALS = ["Garuda", "Tiger", "Lion", "Elephant", "Rat", "Guinea-pig", "Naga"]  # Sun..Sat
MAHABOTE_HOUSES = ["Binga", "Atun", "Yaza", "Adipati", "Marana", "Thike", "Puti"]
MAHABOTE_SEQUENCE = [1, 2, 3, 4, 0, 5, 6]   # Sun Moon Mars Mercury Saturn Jupiter (Rahu folded) Venus
_SEQ_POS = {p: i for i, p in enumerate(MAHABOTE_SEQUENCE)}


def mahabote_animal(y, m, d, L):
    return (jdn(y, m, d) + 1) % 7            # 0 Sunday .. 6 Saturday


def mahabote_remainder(y, m, d, L):
    return burmese_year(y, m, d) % 7


def mahabote_house(y, m, d, L):
    wd = mahabote_weekday(y, m, d)
    r = burmese_year(y, m, d) % 7
    return (_SEQ_POS[wd] - _SEQ_POS[r]) % 7


# ---------------------------------------------------------------- Hellenic civil lunar day
def hellenic_lunar_day(y, m, d, L):
    j = jdn(y, m, d)
    nm = last_new_moon_before(j + 0.5)          # before the end of the civil day
    days = j - jd_to_jdn(nm)
    if days < 0:
        days = 0
    return min(days, 29)


# ---------------------------------------------------------------- the bank
def _s(name, n, desc, fn):
    return {"name": f"{SLUG}_{name}", "n": n, "desc": desc, "fn": fn}


SYSTEMS = [
    _s("tibetan_year_animal", 12, "Tibetan year animal, Losar boundary (first new moon after Li Chun, Phugpa drift); Rat=0, 1984=Rat", tibetan_year_animal),
    _s("tibetan_year_element", 5, "Tibetan year element (wood fire earth iron water), Losar boundary; 1984=wood", tibetan_year_element),
    _s("tibetan_year_gender", 2, "Tibetan year gender (0 male/pho, 1 female/mo), Losar boundary", tibetan_year_gender),
    _s("tibetan_year60", 60, "Tibetan rabjung position (year-1027) mod 60, Fire-Hare 1027=0, Losar boundary", tibetan_year60),
    _s("tibetan_mewa", 9, "Tibetan year mewa (nine-square number) 11-digitroot(year), 1984=7 red; state=mewa-1; Losar boundary", tibetan_mewa),
    _s("tibetan_parkha", 8, "Tibetan natal parkha from year animal and gender (male clockwise from Li, female counter-clockwise from Kham); state = ring position Li0..Zon7", tibetan_parkha),
    _s("tibetan_life_element", 5, "Tibetan srog (life-force) element fixed by the year animal, Losar boundary", tibetan_life_element),
    _s("celtic_tree", 13, "Celtic tree calendar (Graves), 13 fixed 28-day ranges from Birch Dec 24; Dec 23 in Elder", celtic_tree),
    _s("celtic_wheel8", 8, "Eight-fold wheel of the year on fixed dates (Yule Dec 21 ... Samhain Nov 1)", celtic_wheel8),
    _s("celtic_fire_season", 4, "Gaelic fire-festival quarter: Samhain Nov 1, Imbolc Feb 1, Beltane May 1, Lughnasadh Aug 1", celtic_fire_season),
    _s("mahabote_animal", 7, "Burmese Mahabote birth-day animal = weekday (Sunday Garuda 0 .. Saturday Naga 6)", mahabote_animal),
    _s("mahabote_remainder", 7, "Burmese-Era year mod 7 (Thingyan new year, Surya Siddhanta constants)", mahabote_remainder),
    _s("mahabote_house", 7, "Mahabote house of the birth-day planet (Binga 0 .. Puti 6) from weekday and year remainder", mahabote_house),
    _s("medwheel_totem", 12, "Sun Bear medicine-wheel birth totem, 12 fixed date ranges from Snow Goose Dec 22", medwheel_totem),
    _s("medwheel_clan", 4, "Medicine-wheel elemental clan = totem mod 4 (Turtle Butterfly Frog Thunderbird)", medwheel_clan),
    _s("medwheel_spirit_keeper", 4, "Medicine-wheel Spirit Keeper = totem // 3 (Waboose Wabun Shawnodese Mudjekeewis)", medwheel_spirit_keeper),
    _s("egyptian_god", 12, "Popular Egyptian zodiac, 12 gods by fixed multi-range date table (The Nile 0 .. Sekhmet 11)", egyptian_god),
    _s("hellenic_lunar_day", 30, "Hellenic civil lunar day: civil days since the last true new moon's UT date (0 = noumenia), clipped to 29", hellenic_lunar_day),
]


# ---------------------------------------------------------------- smoke test
if __name__ == "__main__":
    import random
    rng = random.Random(4242)
    dates = [(1600, 1, 1), (1600, 2, 14), (1600, 4, 10), (1612, 3, 3), (1625, 7, 14), (1650, 12, 31),
             (1675, 2, 28), (1700, 2, 28), (1710, 4, 13), (1725, 10, 5), (1750, 6, 21), (1775, 1, 20),
             (1800, 2, 29 - 1), (1825, 9, 2), (1850, 11, 25), (1875, 4, 17), (1900, 1, 21),
             (1900, 2, 4), (1925, 8, 18), (1950, 3, 21), (1960, 6, 30), (1975, 12, 23),
             (1984, 2, 1), (1984, 2, 3), (1999, 12, 31), (2000, 1, 1), (2000, 2, 5), (2000, 2, 6),
             (2000, 2, 29), (2000, 4, 16), (2000, 4, 17), (2000, 12, 31)]
    bodies = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
              "pluto", "node", "chiron", "lilith"]
    checks = 0
    for (y, m, d) in dates:
        for female in (False, True):
            for kind in ("synthetic", "empty"):
                L = {b: rng.uniform(0, 360) for b in bodies} if kind == "synthetic" else {}
                L["_female"] = female
                for S in SYSTEMS:
                    v = S["fn"](y, m, d, L)
                    assert isinstance(v, int) and not isinstance(v, bool), (S["name"], y, m, d, v)
                    assert 0 <= v < S["n"], (S["name"], y, m, d, v)
                    checks += 1

    # ---- anchors: Losar dates published 2000-2020 (Phugpa)
    def ymd(j):
        # JDN -> (y, m, d), proleptic Gregorian (Fliegel & Van Flandern inverse)
        l = j + 68569
        n = 4 * l // 146097
        l = l - (146097 * n + 3) // 4
        i = 4000 * (l + 1) // 1461001
        l = l - 1461 * i // 4 + 31
        jj = 80 * l // 2447
        dd = l - 2447 * jj // 80
        l = jj // 11
        mm = jj + 2 - 12 * l
        yy = 100 * (n - 49) + i + l
        return (yy, mm, dd)
    LOSAR = {2000: (2, 6), 2001: (2, 24), 2002: (2, 13), 2003: (3, 3), 2004: (2, 21), 2005: (2, 9),
             2006: (2, 28), 2007: (2, 18), 2008: (2, 7), 2009: (2, 25), 2010: (2, 14), 2011: (3, 5),
             2012: (2, 22), 2013: (2, 11), 2014: (3, 2), 2015: (2, 19), 2016: (2, 9), 2017: (2, 27),
             2018: (2, 16), 2019: (2, 5), 2020: (2, 24)}
    bad = []
    for yr, (mm, dd) in LOSAR.items():
        got = ymd(losar_jdn(yr))
        if got != (yr, mm, dd):
            bad.append((yr, (mm, dd), got))
    print("Losar mismatches:", bad)
    assert len(bad) <= 2, bad
    for yr in range(1600, 2001, 7):
        yy, mm, dd = ymd(losar_jdn(yr))
        assert yy == yr and (mm, dd) >= (1, 20) and (mm, dd) <= (3, 8), (yr, mm, dd)
    # year cycles
    assert tibetan_year_animal(1984, 6, 1, {}) == 0 and tibetan_year_element(1984, 6, 1, {}) == 0
    assert tibetan_year_animal(2000, 2, 5, {}) == 3 and tibetan_year_animal(2000, 2, 6, {}) == 4
    assert mewa_of_year(1984) == 7 and mewa_of_year(1985) == 6 and mewa_of_year(2000) == 9 and mewa_of_year(2020) == 7
    assert tibetan_year60(1027, 6, 1, {}) == 0 and tibetan_year60(1987, 6, 1, {}) == 0
    assert tibetan_parkha(1984, 6, 1, {"_female": False}) == 0      # Rat, male -> Li
    assert tibetan_parkha(1984, 6, 1, {"_female": True}) == 4       # Rat, female -> Kham
    assert tibetan_parkha(1985, 6, 1, {"_female": True}) == 3       # Ox, female -> Khen
    # ---- Celtic: every day of a leap year covered, 28-day months, animal identity
    counts = [0] * 13
    for j in range(jdn(2000, 1, 1), jdn(2000, 12, 31) + 1):
        yy, mm, dd = ymd(j)
        t = celtic_tree(yy, mm, dd, {})
        assert t == celtic_animal(yy, mm, dd, {})
        counts[t] += 1
    assert counts == [28, 28, 29, 28, 28, 28, 28, 28, 28, 28, 28, 28, 29], counts   # leap Ash, Elder + Dec 23
    assert celtic_tree(2000, 12, 23, {}) == 12 and celtic_tree(2000, 12, 24, {}) == 0
    assert celtic_wheel8(2000, 12, 21, {}) == 0 and celtic_wheel8(2000, 12, 20, {}) == 7
    assert celtic_fire_season(2000, 1, 31, {}) == 0 and celtic_fire_season(2000, 2, 1, {}) == 1
    # ---- medicine wheel coverage
    mc = [0] * 12
    for j in range(jdn(1999, 1, 1), jdn(1999, 12, 31) + 1):
        yy, mm, dd = ymd(j)
        mc[medwheel_totem(yy, mm, dd, {})] += 1
    assert sum(mc) == 365 and min(mc) >= 28 and max(mc) <= 32, mc
    assert medwheel_totem(2000, 12, 22, {}) == 0 and medwheel_clan(2000, 4, 25, {}) == 0 and medwheel_spirit_keeper(2000, 10, 1, {}) == 3
    # ---- Egyptian: every day of a leap year exactly once
    seen = {}
    for j in range(jdn(2000, 1, 1), jdn(2000, 12, 31) + 1):
        yy, mm, dd = ymd(j)
        md = mm * 100 + dd
        hits = [g for (m1, d1, m2, d2, g) in EGYPTIAN_RANGES if m1 * 100 + d1 <= md <= m2 * 100 + d2]
        assert len(hits) == 1, (mm, dd, hits)
        seen[hits[0]] = seen.get(hits[0], 0) + 1
    assert len(seen) == 12 and sum(seen.values()) == 366
    # ---- Burmese
    assert ymd(burmese_new_year_jdn(1362)) == (2000, 4, 17), ymd(burmese_new_year_jdn(1362))
    assert burmese_year(2000, 4, 16) == 1361 and burmese_year(2000, 4, 17) == 1362
    assert mahabote_remainder(2000, 4, 17, {}) == 1362 % 7 == 4
    assert mahabote_weekday(2000, 1, 1) == 0                      # Saturday -> 0
    assert mahabote_animal(1969, 7, 20, {}) == 0                  # Sunday
    assert mahabote_house(2000, 4, 17, {}) == (_SEQ_POS[2] - _SEQ_POS[4]) % 7   # Monday 17 Apr 2000, remainder 4
    for yr in (1600, 1700, 1800, 1900, 2000):
        yy, mm, dd = ymd(burmese_new_year_jdn(yr - 638))
        assert yy == yr and mm == 4 and 8 <= dd <= 18, (yr, mm, dd)
    # ---- Hellenic lunar day: 0 on a new-moon day, monotone inside the month
    assert hellenic_lunar_day(2000, 2, 5, {}) == 0 and hellenic_lunar_day(2000, 2, 6, {}) == 1
    assert hellenic_lunar_day(2000, 1, 6, {}) == 0                # new moon 2000-01-06 18:14 UT
    print(f"SMOKE OK: {len(SYSTEMS)} systems x {len(dates)} dates x 2 genders x 2 L-kinds = {checks} state checks in range; anchors OK")
    for S in SYSTEMS:
        print(f"  {S['name']:44s} n={S['n']:3d}  {S['desc']}")
