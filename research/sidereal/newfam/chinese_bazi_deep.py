"""chinese_bazi_deep — the Four Pillars of Destiny (八字, BaZi), in depth, from two birth dates.

WHY THIS MODULE EXISTS.  The catalogue already carries a thin slice of East Asian doctrine: the DAY
pillar (the day master) and the twelve-animal year branch with a few of its simple relations.  That
is perhaps a tenth of what a BaZi reader actually looks at.  A real chart is FOUR pillars — year,
month, day and hour — each a HEAVENLY STEM (天干, 10) over an EARTHLY BRANCH (地支, 12), and the
reading is built from what those twenty-odd symbols do to each other: the qi hidden inside each
branch, the five-element census of the whole chart, the ten gods a day master sees in another chart,
the sound-element (納音) of each pillar, the combinations/clashes/harms/punishments between branches,
and whether the season the chart was born into feeds or starves its day master.  This module builds
all of that for BOTH partners and reads it ACROSS the two charts, which is exactly what a
compatibility reading (合婚) does.

The HOUR pillar is not built.  It needs a birth TIME, and there is none in this dataset.  A fabricated
hour pillar would be five columns of invention, so there are none.  Three pillars is the honest chart.

THE ENGINE, and how it was checked.
  * DAY pillar.  The sexagenary day count is an unbroken count of days: index = (JDN + 49) mod 60
    with 甲子 jiǎ-zǐ = 0.  Anchored on 2000-01-07 = 甲子 and re-derived below in the module test.
  * YEAR pillar.  The Chinese solar year turns at LÌ CHŪN (立春, ~4 February), NOT 1 January — a
    late-January birth carries the PREVIOUS animal.  Index = (solar_year - 4) mod 60, so 1984 = 甲子.
  * MONTH pillar.  The month is a SOLAR-TERM month: it turns when the Sun's TROPICAL longitude
    crosses a multiple of 30 deg starting at 315 deg (Lì Chūn).  Rather than a fixed "the 5th of the
    month" table — which drifts by a day or more over the centuries this set spans — the Sun's
    tropical longitude is computed analytically (the standard low-precision series, ~0.01 deg near
    2000 and well under 0.1 deg across the whole span; 0.1 deg is 2.4 hours of solar motion, far
    inside the +/-12h a date-without-a-time already costs us).  The month's BRANCH follows from that
    crossing (month 1 = 寅 yín = branch 2); its STEM follows from the year stem by the五虎遁
    five-tigers rule, here in its closed form stem = (2*year_stem + month_no + 1) mod 10.
  Verified end to end against four independently published charts, all four correct:
    2000-01-07 -> 己卯 / 丁丑 / 甲子      (the day-pillar anchor, and a Lì Chūn year rollback)
    1949-10-01 -> 己丑 / 癸酉 / 甲子      (the widely-printed 1949 chart)
    1984-02-05 -> 甲子 / 丙寅 / 己巳      (the famous 甲子 year, two days after Lì Chūn)
    2024-02-03 -> 癸卯 / 乙丑 / ...       (one day BEFORE Lì Chūn: still the previous year 癸卯)

WHAT IS COMPUTABLE FROM WHAT.  This is the whole design of the module, and it is why the columns are
grouped the way they are:
  * A YEAR alone gives the YEAR pillar and its 納音 — nothing else.  About a fifth of the dates here
    are 'YYYY-00-00', so the year-pillar block is the one that is answerable for nearly every row,
    and it is emitted SEPARATELY from everything day-dependent.  (Cost of honesty: with no month, a
    birth in the 1 Jan - 3 Feb window - about 9% of births - is assigned to the wrong solar year.
    That is a real, bounded, documented error, and it is preferable to inventing a month.)
  * A MONTH AND DAY, even with no year, still place the SOLAR MONTH BRANCH: the solar-term dates move
    less than two days across the whole span, so the branch is read at a mid-set reference year.  Its
    STEM is not: that needs the year stem.  So '0000-MM-DD' rows get the month branch and the season,
    and nothing else.
  * MONTH PRECISION ('YYYY-MM-00') does NOT place the solar month.  A solar month is a 30-degree arc
    of the Sun and a calendar month straddles two of them — the same reason Z leaves the Sun NaN at
    month precision.  Those rows are treated as year-only.  No majority-vote guess is taken.
  * The FULL three-pillar chart — and therefore the element census, the ten gods, the branch grid and
    the day-master strength — requires DAY precision on both sides.  Everything in those blocks is
    NaN otherwise.  Nothing is imputed anywhere, ever.

ORDER-FREENESS.  Every column is a symmetric function of the two charts, so a model cannot learn
column order in place of doctrine.  Categorical pairs are emitted as (min, max) of the unordered
pair; magnitudes as sums, absolute differences, min/max; every relation predicate (combination,
clash, harm, punishment, generation, control) is symmetric by construction; the 3x3 cross-pillar
grid is only ever reduced by statistics that are invariant under its transpose (its diagonal, and
its total).  The module test asserts BIT-IDENTICAL output under a full a<->b swap.

Z IS NOT READ.  BaZi is a solar-CALENDAR system: its inputs are the civil date and the Sun's
TROPICAL longitude.  Z carries SIDEREAL longitudes, which are the same body measured against a
different origin, and converting one to the other needs an ayanamsa this module has no business
choosing.  The Sun's tropical longitude is therefore computed here directly from the date.  Z is
accepted to satisfy the contract and deliberately ignored; `half` is likewise only a label.

df.start is ALWAYS the string '0000-00-00' in this dataset.  It is never read.

Pure function of (df, Z, half): no I/O, no network, no randomness, no global mutable state.  Imports
are numpy, pandas, math and itertools only.
"""

import itertools
import math

import numpy as np
import pandas as pd

# =============================================================================================
# THE SYMBOL TABLES
# =============================================================================================

# 天干 the ten heavenly stems, in order: 甲乙丙丁戊己庚辛壬癸
STEM_NAMES = ['jia', 'yi', 'bing', 'ding', 'wu', 'ji', 'geng', 'xin', 'ren', 'gui']
# 地支 the twelve earthly branches, in order: 子丑寅卯辰巳午未申酉戌亥
BRANCH_NAMES = ['zi', 'chou', 'yin', 'mao', 'chen', 'si', 'wu', 'wei', 'shen', 'you', 'xu', 'hai']

# 五行 the five phases, in the GENERATING order: 0 wood -> 1 fire -> 2 earth -> 3 metal -> 4 water -> wood.
# Written in this order so that x generates (x+1)%5 and x controls (x+2)%5, which is the whole
# five-element algebra in two lines of arithmetic instead of two lookup tables.
ELEM_NAMES = ['wood', 'fire', 'earth', 'metal', 'water']

# Each stem's phase (a pair of stems per phase, yang then yin) and its polarity (0 yang, 1 yin).
STEM_ELEM = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
STEM_POL = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]

# Each branch's phase.  Note this is identical to the SEASON's ruling phase (spring = wood, summer =
# fire, autumn = metal, winter = water, the four 土 earth months at the season joints) — which is not
# a coincidence but the definition, and is why the seasonal-strength judgement below reads it directly.
BRANCH_ELEM = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]

# 藏干 THE HIDDEN STEMS.  Every branch conceals one to three stems: a principal qi (本气), sometimes a
# middle qi (中气) and a residual qi (余气).  They are what makes a branch more than a label — the
# element census, the ten-gods tally and the rooting of a day master all read the hidden stems, not
# the branch name.  Weights are the classical 60/30/10 apportionment of the branch's qi (70/30 where
# there are two), so EVERY branch contributes exactly 1.0 and every chart exactly 6.0 units of qi
# (3 visible stems + 3 branches).  That fixed total is what makes two charts' element vectors, and
# the two directions of the ten-gods tally, comparable to each other.
HIDDEN = {
    0:  [(9, 1.0)],                               # 子 zi   : 癸
    1:  [(5, 0.6), (9, 0.3), (7, 0.1)],           # 丑 chou : 己 癸 辛
    2:  [(0, 0.6), (2, 0.3), (4, 0.1)],           # 寅 yin  : 甲 丙 戊
    3:  [(1, 1.0)],                               # 卯 mao  : 乙
    4:  [(4, 0.6), (1, 0.3), (9, 0.1)],           # 辰 chen : 戊 乙 癸
    5:  [(2, 0.6), (4, 0.3), (6, 0.1)],           # 巳 si   : 丙 戊 庚
    6:  [(3, 0.7), (5, 0.3)],                     # 午 wu   : 丁 己
    7:  [(5, 0.6), (3, 0.3), (1, 0.1)],           # 未 wei  : 己 丁 乙
    8:  [(6, 0.6), (8, 0.3), (4, 0.1)],           # 申 shen : 庚 壬 戊
    9:  [(7, 1.0)],                               # 酉 you  : 辛
    10: [(4, 0.6), (7, 0.3), (3, 0.1)],           # 戌 xu   : 戊 辛 丁
    11: [(8, 0.7), (0, 0.3)],                     # 亥 hai  : 壬 甲
}

# 納音五行 THE SOUND ELEMENT of each of the 30 sexagenary PAIRS (pillars 2k and 2k+1 share one).
# Indexed by sexagenary_index // 2.  This is the core of Korean 궁합 gunghap and of the older Chinese
# 合婚 method, which compares the two BIRTH-YEAR pillars' sound elements before looking at anything
# else.  Transcribed from the canonical 60-pillar table and checked entry by entry
# (甲子乙丑 海中金 metal ... 壬戌癸亥 大海水 water).
NAYIN = [3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4,
         3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4]

# 十神 THE TEN GODS.  A day master (the day stem) looks at any other stem and names the relation from
# two facts only: the phase relation, and whether the polarities agree.  Five relations x two
# polarities = ten gods.  The five CATEGORIES are what most readings are actually about: peers,
# output, wealth, officer, resource.
GOD_NAMES = ['bijian', 'jiecai', 'shishen', 'shangguan', 'piancai',
             'zhengcai', 'qisha', 'zhengguan', 'pianyin', 'zhengyin']
GOD_CAT_NAMES = ['peer', 'output', 'wealth', 'officer', 'resource']
GOD_CAT = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]          # god index -> category index


def _god(dm, s):
    """The ten-god index that day master stem `dm` gives to stem `s`.

    d = (phase(s) - phase(dm)) mod 5 is the phase relation seen from the day master:
      0 the same phase          -> 比肩 bijian    / 劫財 jiecai      (a peer, or a rival)
      1 dm GENERATES s          -> 食神 shishen   / 傷官 shangguan   (what I put out)
      2 dm CONTROLS s           -> 偏財 piancai   / 正財 zhengcai    (what I command: wealth)
      3 s CONTROLS dm           -> 七殺 qisha     / 正官 zhengguan   (what commands me: office)
      4 s GENERATES dm          -> 偏印 pianyin   / 正印 zhengyin    (what feeds me: resource)
    Within each pair the FIRST is taken when the two polarities agree (an "indirect"/uneven meeting)
    and the second when they differ (a "direct"/complementary one) — except among peers, where the
    doctrine names the same-polarity case the friend and the mixed one the rival.  This is the
    standard assignment.
    """
    d = (STEM_ELEM[s] - STEM_ELEM[dm]) % 5
    return 2 * d + (0 if STEM_POL[dm] == STEM_POL[s] else 1)


GOD_TABLE = [[_god(a, b) for b in range(10)] for a in range(10)]

# 旺相休囚死 SEASONAL STRENGTH.  The classical judgement of a day master against the month branch —
# the single most important call in a BaZi reading, because the month is the season and the season
# decides whether the day master's phase is in power or in exile.  Indexed by
# d = (phase(day_master) - phase(month_branch)) mod 5:
#   d=0 旺 wàng  the day master IS the season                     -> 4  prosperous
#   d=1 相 xiàng the season generates it                          -> 3  supported
#   d=4 休 xiū   it generates the season (spends itself)          -> 2  resting
#   d=3 囚 qiú   it controls the season (fights it, and tires)    -> 1  trapped
#   d=2 死 sǐ    the season controls it                           -> 0  dead
SEASON_STRENGTH = [4, 3, 0, 1, 2]

# ---------------------------------------------------------------------------------------------
# BRANCH RELATIONS.  Six canonical relations between two earthly branches.  All six are SYMMETRIC in
# the unordered pair, which is exactly what this module needs.  Each is built as a 12x12 boolean
# table so the row loop is a lookup and never a set search.
# ---------------------------------------------------------------------------------------------

# 六合 liù hé, the six combinations — the classic harmony pair, and the one a marriage reading wants.
HE_PAIRS = [(0, 1), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)]
# 六害 liù hài, the six harms — a quiet corrosive relation, the counterpart of the combinations.
HAI_PAIRS = [(0, 7), (1, 6), (2, 5), (3, 4), (8, 11), (9, 10)]
# 相破 xiāng pò, the six destructions.
PO_PAIRS = [(0, 9), (3, 6), (5, 8), (2, 11), (1, 4), (7, 10)]
# 三刑 the punishments: two mutually-punishing triads, one uncivil pair, and the four self-punishments.
XING_TRIADS = [(2, 5, 8), (1, 7, 10)]
XING_PAIR = (0, 3)
XING_SELF = (4, 6, 9, 11)


def _blank12():
    return [[False] * 12 for _ in range(12)]


def _sym(table, pairs):
    for a, b in pairs:
        table[a][b] = True
        table[b][a] = True
    return table


HE = _sym(_blank12(), HE_PAIRS)
HAI = _sym(_blank12(), HAI_PAIRS)
PO = _sym(_blank12(), PO_PAIRS)

# 三合 sān hé, the trines.  申子辰 water, 亥卯未 wood, 寅午戌 fire, 巳酉丑 metal.  Each triad is a set of
# branches four apart, so membership of a common trine is exactly (b1 - b2) % 4 == 0 with b1 != b2 —
# no table needed, but one is built anyway to keep every relation the same shape.
SANHE = _blank12()
for _a in range(12):
    for _b in range(12):
        SANHE[_a][_b] = (_a != _b) and ((_a - _b) % 4 == 0)

# 六冲 liù chōng, the clashes: the branch directly opposite, six places away.  The strongest
# antagonism in the system, and the one traditional 合婚 refuses a match on.
CHONG = _blank12()
for _a in range(12):
    CHONG[_a][(_a + 6) % 12] = True

XING = _blank12()
for _t in XING_TRIADS:
    for _a, _b in itertools.permutations(_t, 2):
        XING[_a][_b] = True
XING[XING_PAIR[0]][XING_PAIR[1]] = True
XING[XING_PAIR[1]][XING_PAIR[0]] = True
for _a in XING_SELF:
    XING[_a][_a] = True                            # 自刑 a branch that punishes itself

BRANCH_RELATIONS = [('he', HE), ('sanhe', SANHE), ('chong', CHONG),
                    ('hai', HAI), ('xing', XING), ('po', PO)]

_DIM = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

# The reference year used ONLY to place the solar-term month of a '0000-MM-DD' row, whose year was
# never recorded.  Solar-term dates move by under two days across the centuries this set covers, so
# the branch is right except for a birth within a day or so of a term boundary.  It is used for
# NOTHING else: no year pillar, no month stem, no day pillar is ever derived from it.
_REF_YEAR = 1950


# =============================================================================================
# CALENDAR
# =============================================================================================

def _leap(y):
    return (y % 4 == 0) and (y % 100 != 0 or y % 400 == 0)


def _dim(y, m):
    if m == 2 and _leap(y):
        return 29
    return _DIM[m - 1]


def _jdn(y, m, d):
    """Proleptic Gregorian Julian Day Number.  Proleptic throughout, deliberately: the sexagenary day
    count is an unbroken count of DAYS, so what matters is one consistent day numbering across a set
    that reaches back centuries, not which calendar a given country had adopted by then."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _sun_tropical(jd):
    """The Sun's apparent TROPICAL ecliptic longitude in degrees, low-precision series, at the noon
    of Julian Day Number `jd`.  ~0.01 deg near 2000 and well inside 0.1 deg over this set's span;
    0.1 deg is 2.4 hours of solar motion, which is far smaller than the +/-12h uncertainty a date
    with no time already carries.  This is what places the solar terms, and therefore both the Lì
    Chūn year boundary and every month-branch boundary."""
    n = float(jd) - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360.0
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    return (L + 1.915 * math.sin(g) + 0.020 * math.sin(2.0 * g)) % 360.0


def _solar_month_index(jd):
    """Which solar-term month a Julian day falls in: 0 = the 寅 yín month opening at Lì Chūn
    (Sun at 315 deg), 1 = 卯 mao, ... 11 = 丑 chou (the month that closes the solar year)."""
    return int(((_sun_tropical(jd) - 315.0) % 360.0) // 30.0)


def _parse(s):
    """'YYYY-MM-DD' -> (y, m, d), each None where that component was never recorded.

    Handles all five shapes present in this dataset:
      'YYYY-MM-DD' -> (y, m, d)          a full date
      'YYYY-MM-00' -> (y, m, None)       month precision
      'YYYY-00-00' -> (y, None, None)    a year only
      '0000-MM-DD' -> (None, m, d)       the YEAR was never recorded
      '0000-00-00' -> (None, None, None) absent
    Only the first ten characters are read, so a date carrying a time suffix parses the same way.  An
    impossible component (month 13, 31 February) is treated as NOT RECORDED rather than clamped:
    clamping would invent a date nobody wrote down.
    """
    if not isinstance(s, str):
        return (None, None, None)
    s = s.strip()
    if len(s) < 10:
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
        d = None                                   # a day with no month cannot be placed in a year
    elif d is not None:
        ref = y if y is not None else 2001         # a non-leap reference when the year is unknown
        if d > _dim(ref, m):
            d = None
    return (y, m, d)


def _pillars(s):
    """The three pillars a date can support: (year_sexagenary, month_branch, month_stem, day_sexagenary).

    Each is an int or None; None means "this date does not determine it", and every downstream column
    that needs it becomes NaN.  See the module docstring for why each precision gives what it gives.
    """
    y, m, d = _parse(s)

    if y is not None and m is not None and d is not None:
        jd = _jdn(y, m, d)
        k = _solar_month_index(jd)
        # The solar YEAR turns at Lì Chūn.  A January or February date still sitting in the last two
        # solar months (k >= 10: 子 zi and 丑 chou) belongs to the PREVIOUS solar year.  The month
        # test is what keeps a December date — also in the 子 month — from being rolled back.
        cy = y - 1 if (m <= 2 and k >= 10) else y
        ysex = (cy - 4) % 60                       # 1984 = 甲子 = 0
        mno = k + 1                                # solar month number, 1 = 寅 yín
        mbr = (2 + k) % 12
        ystem = ysex % 10
        mstem = (2 * ystem + mno + 1) % 10         # 五虎遁 five-tigers rule, closed form
        dsex = (jd + 49) % 60                      # 2000-01-07 = 甲子 = 0
        return (ysex, mbr, mstem, dsex)

    if y is not None:
        # A year, with or without a month.  MONTH PRECISION IS TREATED AS YEAR PRECISION: a calendar
        # month straddles two solar months, so it does not place the month pillar, and no majority
        # guess is taken.  Nor is the Lì Chūn rollback applied from a month alone — that would fix
        # January's year while leaving February's wrong, buying a smaller error for an inconsistent
        # one.  The year pillar is therefore the calendar year throughout this branch, with the
        # ~9% Jan-1-to-Feb-3 misassignment documented in the module docstring.
        return ((y - 4) % 60, None, None, None)

    if m is not None and d is not None:
        # No year: no year pillar, no month stem, no day pillar.  The solar month BRANCH survives,
        # because it moves under two days over the whole span (see _REF_YEAR).
        k = _solar_month_index(_jdn(_REF_YEAR, m, d))
        return (None, (2 + k) % 12, None, None)

    return (None, None, None, None)


# =============================================================================================
# THE CHART
# =============================================================================================

def _entropy(vec, total):
    """Shannon entropy of a five-element census, in nats.  0 = the whole chart is one element (a
    "one-phase" chart, which the doctrine reads as extreme), log 5 = perfectly even.  This is the
    numeric form of what a reader means by a BALANCED chart."""
    h = 0.0
    for v in vec:
        if v > 0.0:
            p = v / total
            h -= p * math.log(p)
    return h


def _chart(s):
    """Everything this module reads out of ONE birth date.  A dict; missing pieces are None.

    'full' is True only when all three pillars resolve (i.e. day precision), which is the precondition
    for the element census, the ten gods, the branch grid and the day-master strength.
    """
    ysex, mbr, mstem, dsex = _pillars(s)
    c = {
        'ysex': ysex, 'mbr': mbr, 'mstem': mstem, 'dsex': dsex,
        'n_pillars': (1 if ysex is not None else 0)
                     + (1 if (mbr is not None and mstem is not None) else 0)
                     + (1 if dsex is not None else 0),
        'full': False,
    }
    if ysex is not None:
        c['ystem'] = ysex % 10
        c['ybr'] = ysex % 12
        c['ynayin'] = NAYIN[ysex // 2]
    if mbr is not None:
        c['season'] = BRANCH_ELEM[mbr]             # the month branch's phase IS the season's phase
    if ysex is None or mbr is None or mstem is None or dsex is None:
        return c

    # ---- the full three-pillar chart -------------------------------------------------------
    msex = (6 * mstem - 5 * mbr) % 60              # the sexagenary index of a (stem, branch) pillar
    dstem, dbr = dsex % 10, dsex % 12
    stems = [ysex % 10, mstem, dstem]
    branches = [ysex % 12, mbr, dbr]

    # Every unit of qi in the chart: the three visible stems at full weight, then each branch's
    # hidden stems at their share of that branch's single unit.  Total is exactly 6.0 for every
    # chart, which is what makes two charts comparable.  Index 2 is the DAY MASTER itself.
    qi = [(stems[0], 1.0), (stems[1], 1.0), (stems[2], 1.0)]
    for b in branches:
        for st, w in HIDDEN[b]:
            qi.append((st, w))

    elem = [0.0] * 5
    for st, w in qi:
        elem[STEM_ELEM[st]] += w

    dm = dstem
    e_dm = STEM_ELEM[dm]
    e_feed = (e_dm - 1) % 5                        # the phase that GENERATES the day master

    # 通根 ROOTING / support: how much of the chart's own qi is the day master's own phase or the
    # phase that feeds it.  The day master itself (qi[2]) is excluded — a stem is not its own root.
    root = 0.0
    for i, (st, w) in enumerate(qi):
        if i == 2:
            continue
        if STEM_ELEM[st] == e_dm or STEM_ELEM[st] == e_feed:
            root += w

    dom = 0
    for e in range(1, 5):
        if elem[e] > elem[dom]:
            dom = e

    c.update({
        'full': True,
        'msex': msex, 'dstem': dstem, 'dbr': dbr,
        'stems': stems, 'branches': branches, 'qi': qi,
        'sexes': [ysex, msex, dsex],
        'nayin': [NAYIN[ysex // 2], NAYIN[msex // 2], NAYIN[dsex // 2]],
        'elem': elem,
        'dom': dom,
        'missing': sum(1 for v in elem if v <= 1e-9),
        'entropy': _entropy(elem, 6.0),
        'dms': SEASON_STRENGTH[(e_dm - BRANCH_ELEM[mbr]) % 5],
        'root': root,
    })
    return c


# =============================================================================================
# SMALL SYMMETRIC PREDICATES
#
# Every one of these takes an UNORDERED pair and is exactly invariant under swapping its arguments.
# `gen` and `ctl` are mutually exclusive and, for x != y, exactly one of them holds: the five-phase
# cycle puts any two distinct phases either one step apart (generation) or two (control).
# =============================================================================================

def _gen_link(x, y):
    """Does one phase GENERATE the other (生)?  Symmetric: the doctrine's harmonious relation."""
    return 1.0 if (y == (x + 1) % 5 or x == (y + 1) % 5) else 0.0


def _ctl_link(x, y):
    """Does one phase CONTROL the other (剋)?  Symmetric: the doctrine's antagonistic relation."""
    return 1.0 if (y == (x + 2) % 5 or x == (y + 2) % 5) else 0.0


def _cyc(a, b, n):
    """Cyclic distance on a ring of n positions, 0 .. n//2.  Symmetric by construction."""
    d = abs(a - b) % n
    return float(min(d, n - d))


# =============================================================================================
# THE COLUMNS
# =============================================================================================

def _names():
    nm = []

    # -- 0. the one permitted coverage column -------------------------------------------------
    # This is the ONLY census column in the module and it is a NUISANCE control, not doctrine: date
    # precision proxies era and notability and is the strongest single thing in this dataset.  It is
    # named so that it can never be mistaken for a doctrinal reading, and it is emitted exactly once
    # so a model that wants to condition on precision has one honest handle instead of inferring it
    # from the NaN pattern of every other block.
    nm.append('nuisance_pillars_resolved')

    # -- 1. THE YEAR PILLAR: answerable from two birth YEARS alone ----------------------------
    nm += [
        'yr_stem_same',            # the two birth-year heavenly stems are the same
        'yr_branch_same',          # the same animal — the best-known compatibility claim there is
        'yr_stem_elem_same',       # the year stems share a phase
        'yr_stem_elem_gen',        # one year stem's phase generates the other's (生, harmony)
        'yr_stem_elem_ctl',        # one controls the other (剋, friction)
        'yr_stem_pol_same',        # both year stems yang, or both yin (an "uneven" meeting)
        'yr_branch_min',           # the unordered pair of animals, low member
        'yr_branch_max',           # ... and high member
        'yr_branch_cyc',           # how far apart on the twelve-ring, 0..6 (6 is the clash)
        'yr_branch_he',            # 六合 the six combinations, on the year branches
        'yr_branch_sanhe',         # 三合 a shared trine
        'yr_branch_chong',         # 六冲 the clash — traditional 合婚 refuses the match on this
        'yr_branch_hai',           # 六害 harm
        'yr_branch_xing',          # 三刑 punishment
        'yr_branch_po',            # 相破 destruction
        'yr_sex_cyc',              # distance on the 60-ring, 0..30 (0 = a 60-year echo)
        'yr_nayin_min',            # 納音 the year pillars' sound elements, unordered pair
        'yr_nayin_max',
        'yr_nayin_same',           # the Korean 궁합 gunghap headline: one sound element between them
        'yr_nayin_gen',            # one sound element generates the other
        'yr_nayin_ctl',            # one controls the other
    ]

    # -- 2. THE MONTH PILLAR ------------------------------------------------------------------
    # The branch three need only month+day (so they survive a missing year); the stem and 納音 need
    # the year stem and are NaN without it.
    nm += [
        'mo_branch_min',           # the unordered pair of solar-term month branches
        'mo_branch_max',
        'mo_branch_cyc',           # distance on the twelve-ring between the two birth months
        'mo_stem_same',
        'mo_stem_elem_same',
        'mo_stem_elem_gen',
        'mo_stem_elem_ctl',
        'mo_nayin_same',
        'mo_nayin_gen',
        'mo_nayin_ctl',
    ]

    # -- 3. THE SEASON (the month branch's own phase) -----------------------------------------
    nm += [
        'season_same',             # both born into the same seasonal phase
        'season_min',              # the unordered pair of seasonal phases
        'season_max',
    ]

    # -- 4. THE DAY PILLAR and the two DAY MASTERS --------------------------------------------
    nm += [
        'dy_stem_min',             # the two day masters as an unordered pair — the core of the chart
        'dy_stem_max',
        'dy_branch_min',           # 日支 the day branch is read as the "spouse palace"
        'dy_branch_max',
        'dy_branch_cyc',
        'dy_sex_cyc',              # distance on the 60-ring between the two day pillars
        'dy_nayin_same',
        'dy_nayin_gen',
        'dy_nayin_ctl',
        'dm_elem_same',            # the day masters share a phase
        'dm_elem_gen',             # one day master's phase generates the other's
        'dm_elem_ctl',             # one controls the other
        'dm_pol_same',             # both yang or both yin
        'dm_god_min',              # the two directional ten-gods between the day masters, unordered
        'dm_god_max',
    ]

    # -- 5. THE TEN GODS: each day master against every stem of the OTHER chart ---------------
    # The tally is weighted by the same qi weights, so each direction totals exactly 6.0 and the two
    # directions are comparable.  Sums are symmetric; the category ABSOLUTE DIFFERENCE is the
    # asymmetry of the relationship (one partner seeing wealth where the other sees office), which is
    # a distinct doctrinal statement from the total and cannot be recovered from it.
    nm += ['god_sum_' + g for g in GOD_NAMES]
    nm += ['godcat_sum_' + g for g in GOD_CAT_NAMES]
    nm += ['godcat_absdiff_' + g for g in GOD_CAT_NAMES]

    # -- 6. THE FIVE-ELEMENT CENSUS -----------------------------------------------------------
    nm += ['elem_sum_' + e for e in ELEM_NAMES]        # the couple's combined phase census
    nm += ['elem_absdiff_' + e for e in ELEM_NAMES]    # how differently the two charts are stocked
    nm += [
        'elem_dom_min',            # the unordered pair of dominant (most-stocked) phases
        'elem_dom_max',
        'elem_dom_same',           # both charts led by the same phase — reinforcement, or excess
        'elem_dom_gen',            # one chart's dominant phase generates the other's
        'elem_dom_ctl',            # one controls the other
        'elem_missing_max',        # the more deficient chart's count of absent phases (0..4)
        'elem_complement',         # COMPLEMENTARITY: how much of what one chart LACKS the other HAS
        'elem_complement_full',    # every phase missing from either chart is supplied by the other
        'elem_entropy_min',        # the less balanced chart's phase entropy
        'elem_entropy_max',        # the more balanced chart's
        'elem_joint_entropy',      # the balance of the two charts TAKEN TOGETHER, as one census
        'elem_cosine',             # how alike the two phase profiles are, scale-free
    ]

    # -- 7. BRANCH RELATIONS ACROSS THE 3x3 CROSS-PILLAR GRID ---------------------------------
    # Each partner's three branches against each of the other's three: nine comparisons.  Only
    # transpose-invariant reductions are emitted, because swapping the partners transposes the grid:
    # the TOTAL over all nine, and the DIAGONAL (year-to-year, month-to-month, day-to-day — the
    # like-against-like comparisons a reader actually makes).
    for r, _ in BRANCH_RELATIONS:
        nm.append('br_' + r + '_total9')
        nm.append('br_' + r + '_diag3')

    # -- 8. WITHIN-CHART BRANCH RELATIONS (the integrity of each chart on its own) ------------
    nm += [
        'own_he_sum', 'own_he_max',          # a chart whose own branches combine is self-consistent
        'own_chong_sum', 'own_chong_max',    # a chart clashing with itself is the unstable one
        'own_xing_sum', 'own_xing_max',
    ]

    # -- 9. DAY-MASTER STRENGTH ---------------------------------------------------------------
    nm += [
        'dms_min', 'dms_max', 'dms_absdiff',        # the 旺相休囚死 seasonal ordinal, 0..4
        'dmroot_min', 'dmroot_max', 'dmroot_absdiff',  # 通根 support from the chart's own qi, 0..5
        'dms_both_strong',                          # both day masters in season (>= 相)
        'dms_both_weak',                            # both out of season (<= 囚)
        'dms_complement',                           # one strong, one weak — the classical good match
    ]
    return nm


NAMES = _names()
K = len(NAMES)
assert len(set(NAMES)) == K, 'duplicate feature name'


def _row(ca, cb):
    """All K features for one couple, as a name -> value dict.  Every value starts NaN and is only
    written where the two charts actually support it, so nothing is ever fabricated and no NaN can
    reach an integer cast: every table lookup below sits inside a guard on the pieces it needs."""
    f = dict.fromkeys(NAMES, np.nan)

    f['nuisance_pillars_resolved'] = float(ca['n_pillars'] + cb['n_pillars'])

    # ---- 1. the year pillar: two birth years are enough -------------------------------------
    if ca['ysex'] is not None and cb['ysex'] is not None:
        sa, sb = ca['ystem'], cb['ystem']
        ba, bb = ca['ybr'], cb['ybr']
        ea, eb = STEM_ELEM[sa], STEM_ELEM[sb]
        f['yr_stem_same'] = 1.0 if sa == sb else 0.0
        f['yr_branch_same'] = 1.0 if ba == bb else 0.0
        f['yr_stem_elem_same'] = 1.0 if ea == eb else 0.0
        f['yr_stem_elem_gen'] = _gen_link(ea, eb)
        f['yr_stem_elem_ctl'] = _ctl_link(ea, eb)
        f['yr_stem_pol_same'] = 1.0 if STEM_POL[sa] == STEM_POL[sb] else 0.0
        f['yr_branch_min'] = float(min(ba, bb))
        f['yr_branch_max'] = float(max(ba, bb))
        f['yr_branch_cyc'] = _cyc(ba, bb, 12)
        f['yr_branch_he'] = 1.0 if HE[ba][bb] else 0.0
        f['yr_branch_sanhe'] = 1.0 if SANHE[ba][bb] else 0.0
        f['yr_branch_chong'] = 1.0 if CHONG[ba][bb] else 0.0
        f['yr_branch_hai'] = 1.0 if HAI[ba][bb] else 0.0
        f['yr_branch_xing'] = 1.0 if XING[ba][bb] else 0.0
        f['yr_branch_po'] = 1.0 if PO[ba][bb] else 0.0
        f['yr_sex_cyc'] = _cyc(ca['ysex'], cb['ysex'], 60)
        na, nb = ca['ynayin'], cb['ynayin']
        f['yr_nayin_min'] = float(min(na, nb))
        f['yr_nayin_max'] = float(max(na, nb))
        f['yr_nayin_same'] = 1.0 if na == nb else 0.0
        f['yr_nayin_gen'] = _gen_link(na, nb)
        f['yr_nayin_ctl'] = _ctl_link(na, nb)

    # ---- 2/3. the month branch and the season: month+day is enough, no year needed ----------
    if ca['mbr'] is not None and cb['mbr'] is not None:
        ba, bb = ca['mbr'], cb['mbr']
        f['mo_branch_min'] = float(min(ba, bb))
        f['mo_branch_max'] = float(max(ba, bb))
        f['mo_branch_cyc'] = _cyc(ba, bb, 12)
        qa, qb = ca['season'], cb['season']
        f['season_same'] = 1.0 if qa == qb else 0.0
        f['season_min'] = float(min(qa, qb))
        f['season_max'] = float(max(qa, qb))

    # ---- 2b. the month STEM and its 納音: needs the year stem on both sides ------------------
    if ca['full'] and cb['full']:
        sa, sb = ca['mstem'], cb['mstem']
        ea, eb = STEM_ELEM[sa], STEM_ELEM[sb]
        f['mo_stem_same'] = 1.0 if sa == sb else 0.0
        f['mo_stem_elem_same'] = 1.0 if ea == eb else 0.0
        f['mo_stem_elem_gen'] = _gen_link(ea, eb)
        f['mo_stem_elem_ctl'] = _ctl_link(ea, eb)
        na, nb = ca['nayin'][1], cb['nayin'][1]
        f['mo_nayin_same'] = 1.0 if na == nb else 0.0
        f['mo_nayin_gen'] = _gen_link(na, nb)
        f['mo_nayin_ctl'] = _ctl_link(na, nb)

    if not (ca['full'] and cb['full']):
        return f

    # ---- 4. the day pillar and the two day masters ------------------------------------------
    da, db = ca['dstem'], cb['dstem']
    dba, dbb = ca['dbr'], cb['dbr']
    f['dy_stem_min'] = float(min(da, db))
    f['dy_stem_max'] = float(max(da, db))
    f['dy_branch_min'] = float(min(dba, dbb))
    f['dy_branch_max'] = float(max(dba, dbb))
    f['dy_branch_cyc'] = _cyc(dba, dbb, 12)
    f['dy_sex_cyc'] = _cyc(ca['dsex'], cb['dsex'], 60)
    na, nb = ca['nayin'][2], cb['nayin'][2]
    f['dy_nayin_same'] = 1.0 if na == nb else 0.0
    f['dy_nayin_gen'] = _gen_link(na, nb)
    f['dy_nayin_ctl'] = _ctl_link(na, nb)
    ea, eb = STEM_ELEM[da], STEM_ELEM[db]
    f['dm_elem_same'] = 1.0 if ea == eb else 0.0
    f['dm_elem_gen'] = _gen_link(ea, eb)
    f['dm_elem_ctl'] = _ctl_link(ea, eb)
    f['dm_pol_same'] = 1.0 if STEM_POL[da] == STEM_POL[db] else 0.0
    g_ab, g_ba = GOD_TABLE[da][db], GOD_TABLE[db][da]
    f['dm_god_min'] = float(min(g_ab, g_ba))
    f['dm_god_max'] = float(max(g_ab, g_ba))

    # ---- 5. the ten gods, each day master against the whole of the other chart --------------
    ga = [0.0] * 10
    for st, w in cb['qi']:
        ga[GOD_TABLE[da][st]] += w
    gb = [0.0] * 10
    for st, w in ca['qi']:
        gb[GOD_TABLE[db][st]] += w
    for i, nmg in enumerate(GOD_NAMES):
        f['god_sum_' + nmg] = ga[i] + gb[i]
    ca_cat = [0.0] * 5
    cb_cat = [0.0] * 5
    for i in range(10):
        ca_cat[GOD_CAT[i]] += ga[i]
        cb_cat[GOD_CAT[i]] += gb[i]
    for i, nmc in enumerate(GOD_CAT_NAMES):
        f['godcat_sum_' + nmc] = ca_cat[i] + cb_cat[i]
        f['godcat_absdiff_' + nmc] = abs(ca_cat[i] - cb_cat[i])

    # ---- 6. the five-element census ---------------------------------------------------------
    va, vb = ca['elem'], cb['elem']
    for i, nme in enumerate(ELEM_NAMES):
        f['elem_sum_' + nme] = va[i] + vb[i]
        f['elem_absdiff_' + nme] = abs(va[i] - vb[i])
    doma, domb = ca['dom'], cb['dom']
    f['elem_dom_min'] = float(min(doma, domb))
    f['elem_dom_max'] = float(max(doma, domb))
    f['elem_dom_same'] = 1.0 if doma == domb else 0.0
    f['elem_dom_gen'] = _gen_link(doma, domb)
    f['elem_dom_ctl'] = _ctl_link(doma, domb)
    f['elem_missing_max'] = float(max(ca['missing'], cb['missing']))
    comp = 0.0
    full_comp = True
    for i in range(5):
        a_zero = va[i] <= 1e-9
        b_zero = vb[i] <= 1e-9
        comp += (vb[i] if a_zero else 0.0) + (va[i] if b_zero else 0.0)
        if a_zero and b_zero:
            full_comp = False
    f['elem_complement'] = comp
    f['elem_complement_full'] = 1.0 if full_comp else 0.0
    f['elem_entropy_min'] = min(ca['entropy'], cb['entropy'])
    f['elem_entropy_max'] = max(ca['entropy'], cb['entropy'])
    joint = [va[i] + vb[i] for i in range(5)]
    f['elem_joint_entropy'] = _entropy(joint, 12.0)
    dot = 0.0
    na2 = 0.0
    nb2 = 0.0
    for i in range(5):
        dot += va[i] * vb[i]
        na2 += va[i] * va[i]
        nb2 += vb[i] * vb[i]
    f['elem_cosine'] = dot / math.sqrt(na2 * nb2) if na2 > 0.0 and nb2 > 0.0 else np.nan

    # ---- 7. the 3x3 cross-pillar branch grid ------------------------------------------------
    bra, brb = ca['branches'], cb['branches']
    for r, tab in BRANCH_RELATIONS:
        tot = 0
        diag = 0
        for i in range(3):
            for j in range(3):
                if tab[bra[i]][brb[j]]:
                    tot += 1
                    if i == j:
                        diag += 1
        f['br_' + r + '_total9'] = float(tot)
        f['br_' + r + '_diag3'] = float(diag)

    # ---- 8. each chart's own three branches against themselves ------------------------------
    for r, tab, key in (('he', HE, 'own_he'), ('chong', CHONG, 'own_chong'), ('xing', XING, 'own_xing')):
        ka = sum(1 for i, j in ((0, 1), (0, 2), (1, 2)) if tab[bra[i]][bra[j]])
        kb = sum(1 for i, j in ((0, 1), (0, 2), (1, 2)) if tab[brb[i]][brb[j]])
        f[key + '_sum'] = float(ka + kb)
        f[key + '_max'] = float(max(ka, kb))

    # ---- 9. day-master strength -------------------------------------------------------------
    sa, sb = ca['dms'], cb['dms']
    f['dms_min'] = float(min(sa, sb))
    f['dms_max'] = float(max(sa, sb))
    f['dms_absdiff'] = float(abs(sa - sb))
    ra, rb = ca['root'], cb['root']
    f['dmroot_min'] = min(ra, rb)
    f['dmroot_max'] = max(ra, rb)
    f['dmroot_absdiff'] = abs(ra - rb)
    f['dms_both_strong'] = 1.0 if (sa >= 3 and sb >= 3) else 0.0
    f['dms_both_weak'] = 1.0 if (sa <= 1 and sb <= 1) else 0.0
    f['dms_complement'] = 1.0 if ((sa >= 3 and sb <= 1) or (sb >= 3 and sa <= 1)) else 0.0
    return f


def build(df, Z, half):
    """Four Pillars (八字) features for every couple in `df`.

    df   : string columns dob_a, dob_b, start.  `start` is always '0000-00-00' here and is not read.
    Z    : accepted for the common contract and deliberately unused — see the module docstring.
    half : 'train' or 'test'; a label only, since Z is not indexed.

    Returns (X, names): X float32 of shape (len(df), K), names a list of K strings.  K is a module
    constant, so both halves are always the same width.
    """
    n = len(df)
    cols = getattr(df, 'columns', [])
    sa = df['dob_a'].astype(str).tolist() if 'dob_a' in cols else [''] * n
    sb = df['dob_b'].astype(str).tolist() if 'dob_b' in cols else [''] * n

    X = np.full((n, K), np.nan, dtype=np.float64)
    # Dates repeat heavily in this set, so charts are memoised per date string.  The cache is local
    # to the call: the function stays pure and two calls cannot influence each other.
    cache = {}
    for i in range(n):
        ka = sa[i] if i < len(sa) else ''
        kb = sb[i] if i < len(sb) else ''
        ca = cache.get(ka)
        if ca is None:
            ca = cache[ka] = _chart(ka)
        cb = cache.get(kb)
        if cb is None:
            cb = cache[kb] = _chart(kb)
        f = _row(ca, cb)
        X[i] = [f[nm] for nm in NAMES]

    X[~np.isfinite(X)] = np.nan                   # an inf can only come from a bug; never ship one
    return X.astype(np.float32), list(NAMES)
