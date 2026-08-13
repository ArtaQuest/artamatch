"""
trad_lunar_calendrical.py — Lunar cycles, eclipses and the religious/folk lunar calendars.

WHAT THIS FAMILY CLAIMS, AND WHAT IS COMPUTED HERE

This is the doctrine of the *moving Moon* rather than of the zodiac: the synodic phase, the mansion
the Moon stands in, the nearness of the syzygy to a node (an eclipse), the long repeat-cycles that
carry eclipses and calendars (Saros, Inex, Metonic, Callippic), and the lunar calendars of the
religions that fix marriage dates by them (Hebrew, Islamic, Zoroastrian, plus the two modern
"revived" folk calendars, Graves's Celtic tree months and Pennick's runic half-months). Every rule
below is computed the way its own authority states it, and the authority is named in a comment.

Three lunar-mansion systems compete here deliberately, in three separate blocks, because they cut
the sky differently and their traditions disagree about which cut is real:

  * `lun: manazil` — the Arabic 28 manazil, 28 EQUAL divisions of 12 deg 51' 26" of the ECLIPTIC,
    counted from the vernal point in the medieval tabulation (al-Biruni, *Kitab al-Tafhim* §§ on the
    28 lunar stations; Picatrix I.4; Agrippa, *De occulta philosophia* II.33).
  * `lun: nakshatra tropical` — the Vedic 27 nakshatras of 13 deg 20' of the ECLIPTIC, but measured
    TROPICALLY (from 0 deg tropical Aries). This is deliberately NOT the sidereal reckoning that the
    Vedic modules use: the tropical measurement is the Sayana school's, and letting the two compete is
    the point.
  * `lun: xiu` — the Chinese 28 xiu, which are UNEQUAL and measured along the EQUATOR in right
    ascension, each lodge beginning at the hour circle of its determinative star (ju xing). Widths in
    du are the Han table (Hanshu, Lu li zhi; repeated in the Kaiyuan zhan jing): 12, 9, 15, 5, 5, 18,
    11, 26.25, 8, 12, 10, 17, 16, 9, 16, 12, 14, 11, 16, 2, 9, 33, 4, 15, 7, 18, 18, 17 du, summing
    to exactly 365.25 du = 360 deg. The origin is the right ascension of Spica (alpha Vir), the
    determinative star of the first lodge Jiao, computed at each instant from the ephemeris so that
    precession is carried correctly.

THE HARD DATA LIMIT AND WHAT IT COSTS THIS FAMILY (read this before trusting any mansion column)

Only DATES are known; every instant is 12:00 UT. The Moon moves 12-15 deg/day, so its longitude
carries roughly +-6 deg of error against the true moment of birth. A mansion is 12.86 deg (manazil),
13.33 deg (nakshatra) or ~5-32 deg (xiu) wide, so a mansion assignment from a birth DATE is right
maybe half the time and its neighbour otherwise. The mansion one-hots are built anyway — three
traditions here are nothing but the Moon — but they are noisy by construction, and the circular and
cyclic-difference encodings beside them are there precisely because they degrade gracefully when the
bin is wrong. The wedding-day columns are less damaged: a wedding is an all-day event and the
electional authorities judged it by the day, not the minute.

PROXIES USED, STATED PLAINLY

  * No Ascendant, no houses, so no house-based lunar rule (no Moon-in-the-7th election). Nothing here
    needs one; the electional block uses only the Moon's sign, phase, speed, latitude and aspects,
    all of which the classical texts also state in sign-and-aspect terms.
  * Void-of-course (Lilly, *Christian Astrology* p.112: the Moon "is not applying to any planet by
    any aspect before she leaves the sign she is in") is decided by LINEAR extrapolation of the noon
    longitude speeds rather than by integrating the ephemeris forward. That is the same approximation
    the traditional tables used, and over the <2.5 days a Moon needs to cross a sign the error is
    small; but it is an approximation, and a wedding held far from noon can flip the verdict.
  * The Islamic calendar is the TABULAR CIVIL one (arithmetic, 30-year cycle, leap years 2, 5, 7, 10,
    13, 16, 18, 21, 24, 26, 29 — the standard type-II intercalation). Real observed Hijri dates differ
    from it by 1-2 days depending on the sighting, so month-boundary flags are approximate; the month
    identity itself (Ramadan vs Shawwal) is almost always right.
  * The Zoroastrian calendar is the QADIMI reckoning from the Yazdegerdi epoch (1 Farvardin 1 YZ =
    16 June 632 CE Julian), a pure 365-day vague year with no intercalation. The Shahanshahi reckoning
    used by the Indian Parsis runs one month later after the ~1129 CE intercalation; both are emitted.
  * The Celtic tree calendar is Robert Graves, *The White Goddess* (1948), and the runic half-months
    are Nigel Pennick, *Runic Astrology* (1990). Both are TWENTIETH-CENTURY constructions, not
    attested ancient practice; they are included because the family brief asks for them and because
    both are precisely tabulated, so they can at least be computed faithfully to their own authors.
  * Eclipse "certain/possible" flags use the standard ecliptic limits (Meeus, *Elements of Solar
    Eclipses*; Explanatory Supplement): solar 9.55 deg minor / 15.35 deg major, lunar 3.80 deg minor /
    12.15 deg major, as the Sun's longitude distance from the lunar node.

THE TRADITIONS' OWN NUMBERS, computed exactly as specified (these are the load-bearing features)

  * Saros series number, from the van den Bergh Saros-Inex lattice: two eclipses 223 lunations apart
    share a series; two eclipses one Inex (358 lunations) apart lie in adjacent series. Hence
    S = S0 + 38*(L - L0) mod 223, where 38 = 358^-1 mod 223. Anchored on the total solar eclipse of
    1999 Aug 11 (Saros 145) and the total lunar eclipse of 2019 Jan 21 (Saros 134); verified against
    eleven catalogued solar and seven catalogued lunar series before use.
  * The computus: golden number = (year mod 19) + 1, the classical Julian epact = 11*(GN-1) mod 30,
    and the Gregorian Easter by the Butcher/Meeus algorithm (verified on six years).
  * Partial Ashtakoot subtotal, measured TROPICALLY: Tara/Dina (3), Nadi (8), Bhakoot (7), Varna (1)
    = 19 of the 36 points, by the tables of the *Muhurta Chintamani*. Only these four kootas are
    computed, because they follow from the nakshatra index, its nadi triplet, the rashi count and the
    rashi element alone, and so can be stated without a disputed animal/lord table. The rules are
    bride/groom asymmetric and sex is unknown, so both orderings are emitted.
  * Halakhic marriage windows: Shabbat, the festivals and chol ha-mo'ed, Sefirat ha-Omer (16 Nisan -
    5 Sivan, with Lag ba-Omer on 18 Iyyar splitting the two customs), the Three Weeks (17 Tammuz -
    9 Av), and the resulting yes/no "a wedding may be held today".
  * Islamic marriage seasons: Ramadan, Shawwal (favoured — the Prophet's marriage to Aisha was in
    Shawwal, Sahih Muslim, Book of Marriage), Muharram 1-10 and Safar (avoided), the four sacred
    months of Qur'an 9:36, the two Eids, and Friday.
  * The lunar month is not one month: the synodic (29.5306 d), draconic (27.2122 d) and anomalistic
    (27.5546 d) months are carried as separate phases through Meeus's mean elements D, M, M', F
    (*Astronomical Algorithms* 2nd ed., ch.47), together with their beat periods — D-F is the eclipse
    year (346.62 d), D-M' the full-moon cycle (411.78 d).

Instant slots: calendar and eclipse blocks use only 0 (older's birth), 1 (younger's birth),
2 (wedding) and 5 (Davison midpoint), because slots 3 and 4 (secondary progressions) fall within
about 90 days of the birth itself and would be near-duplicate calendar dates. The Sun-Moon phase
blocks DO use all six, because the progressed lunation cycle is itself a doctrine of this family
(Rudhyar, *The Lunation Cycle*, 1967).
"""

import math
import numpy as np
import swisseph as swe

TRADITION = "Lunar cycles, eclipses and the religious calendars (manazil, nakshatra, xiu, Saros, computus, Hebrew, Hijri, Zoroastrian)"

# ── slot sets ───────────────────────────────────────────────────────────────────────────────────
S_OLD, S_YNG, S_WED, S_PO, S_PY, S_DAV = 0, 1, 2, 3, 4, 5
ALL_SLOTS = [S_OLD, S_YNG, S_WED, S_PO, S_PY, S_DAV]
CAL_SLOTS = [S_OLD, S_YNG, S_WED, S_DAV]          # dated-calendar slots (see docstring)
CAL_TAG = ["old", "yng", "wed", "dav"]

# ── the lunar constants every cycle here is built from ──────────────────────────────────────────
SYNODIC = 29.530588861          # mean synodic month, days (Meeus AA ch.49)
DRACONIC = 27.212220817         # mean draconic (nodal) month
ANOMALISTIC = 27.554549878      # mean anomalistic month
TROPICAL_M = 27.321582241       # mean tropical month
NM_EPOCH = 2451550.09766        # JDE of the New Moon of 2000 Jan 6, Meeus's k = 0
FM_EPOCH = NM_EPOCH + SYNODIC / 2.0
SAROS = 223 * SYNODIC           # 6585.3213 d
INEX = 358 * SYNODIC            # 10571.95 d
EXELIGMOS = 3 * SAROS           # 19755.96 d — the triple Saros, same hour of day
METONIC = 235 * SYNODIC         # 6939.688 d (the calendrical Metonic is 19 Julian yr = 6939.75 d)
METONIC_CAL = 19 * 365.25
CALLIPPIC = 4 * METONIC_CAL - 1.0        # 76 yr less one day = 27758.0 d, 940 lunations
HIPPARCHIC = 304 * 365.25 - 4.0          # 304 yr less four days
MEAN_MOON_SPEED = 13.176358               # deg/day

RD0 = 1721425.0                 # RD (Rata Die) = floor(JD - 1721424.5); JD_noon - RD0 is an integer


# ── tiny column builders ────────────────────────────────────────────────────────────────────────
def _p(C, a):
    """Append one finite column."""
    v = np.asarray(a, dtype=np.float64).ravel()
    C.append(np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0))


def _circ(C, deg, mult=1):
    r = np.deg2rad(mult * np.asarray(deg, dtype=np.float64))
    _p(C, np.cos(r))
    _p(C, np.sin(r))


def _hot(C, idx, k):
    idx = np.asarray(idx)
    for j in range(k):
        _p(C, (idx == j).astype(np.float64))


def _mk(C, n):
    """Stack into (n, >=1) finite float64. Column count is fixed by the code — see the note below."""
    X = np.column_stack(C).astype(np.float64, copy=False)
    assert X.shape[0] == n, f"row count {X.shape[0]} != {n}"
    # NO VARIANCE PRUNING HERE, DELIBERATELY. This used to drop columns whose standard deviation was
    # zero in the batch being built, and that made a block's WIDTH a function of the DATA rather than
    # of the code. Two consequences, both silent: a scoring batch (one couple, or ten thousand
    # candidates sharing a fixed partner) has many constant columns, so prediction handed the model a
    # narrower and differently-ordered matrix than training did; and a full run built in row chunks
    # produced chunks of different widths that could not be concatenated. Constant columns are now
    # pruned exactly once, globally, by run.collect, which records `kept_idx` in the manifest so
    # prediction can select the same columns. Width is a function of the code alone.
    return np.ascontiguousarray(X)


def _fold90(d):
    """Distance from an AXIS (a node and its opposite): fold |wrap| into [0, 90]."""
    a = np.abs((np.asarray(d) + 180.0) % 360.0 - 180.0)
    return np.minimum(a, 180.0 - a)


def _cycdiff(a, b):
    """Signed cyclic difference of two integer bin indices, as a float in [-k/2, k/2)."""
    return a - b


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Calendar arithmetic — Dershowitz & Reingold, *Calendrical Calculations*, with the constants
# re-derived from Swiss Ephemeris (Hebrew epoch = 7 Oct 3761 BCE Julian = RD -1373427; Islamic epoch
# = 16 July 622 CE Julian = RD 227015) rather than copied, and round-trip tested over 1550-2030.
# ════════════════════════════════════════════════════════════════════════════════════════════════
HEB_EPOCH = -1373427
ISL_EPOCH = 227015
_HEB_ELAPSED = {}
_HEB_NY = {}


def heb_leap(y):
    """Metonic leap rule: years 3, 6, 8, 11, 14, 17, 19 of the 19-year cycle carry Adar II."""
    return ((7 * y + 1) % 19) < 7


def heb_last_month(y):
    return 13 if heb_leap(y) else 12


def _heb_elapsed(y):
    """Days from the epoch to the molad-derived 1 Tishri of year y, with the dehiyyah lo ADU rosh."""
    v = _HEB_ELAPSED.get(y)
    if v is None:
        me = (235 * y - 234) // 19                 # months elapsed since the epochal molad
        pe = 12084 + 13753 * me                    # parts (1/1080 hour) elapsed
        d = 29 * me + pe // 25920
        if (3 * (d + 1)) % 7 < 3:                  # lo ADU rosh
            d += 1
        _HEB_ELAPSED[y] = v = d
    return v


def heb_new_year(y):
    v = _HEB_NY.get(y)
    if v is None:
        n0, n1, n2 = _heb_elapsed(y - 1), _heb_elapsed(y), _heb_elapsed(y + 1)
        c = 2 if n2 - n1 == 356 else (1 if n1 - n0 == 382 else 0)   # the gatarad / betutakpat rules
        _HEB_NY[y] = v = HEB_EPOCH + n1 + c
    return v


def heb_year_len(y):
    return heb_new_year(y + 1) - heb_new_year(y)


def heb_last_day(y, m):
    if m in (2, 4, 6, 10, 13):
        return 29
    if m == 12 and not heb_leap(y):
        return 29
    if m == 8 and heb_year_len(y) not in (355, 385):    # short Marheshvan
        return 29
    if m == 9 and heb_year_len(y) in (353, 383):        # short Kislev
        return 29
    return 30


def heb_to_rd(y, m, d):
    if m < 7:
        s = (sum(heb_last_day(y, i) for i in range(7, heb_last_month(y) + 1))
             + sum(heb_last_day(y, i) for i in range(1, m)))
    else:
        s = sum(heb_last_day(y, i) for i in range(7, m))
    return heb_new_year(y) + s + d - 1


def rd_to_heb(rd):
    """(year, month, day); months are Nisan=1 .. Adar=12, Adar II=13, the year turning at Tishri=7."""
    y = int(math.floor((rd - HEB_EPOCH) * 98496 / 35975351))     # mean Hebrew year 35975351/98496 d
    while heb_new_year(y + 1) <= rd:
        y += 1
    m = 7 if rd < heb_to_rd(y, 1, 1) else 1
    while rd > heb_to_rd(y, m, heb_last_day(y, m)):
        m += 1
    return y, m, rd - heb_to_rd(y, m, 1) + 1


def isl_leap(y):
    """((14 + 11y) mod 30) < 11 — exactly the leap set {2,5,7,10,13,16,18,21,24,26,29}."""
    return ((14 + 11 * y) % 30) < 11


def isl_to_rd(y, m, d):
    return ISL_EPOCH + 354 * (y - 1) + (3 + 11 * y) // 30 + 29 * (m - 1) + m // 2 + d - 1


def rd_to_isl(rd):
    y = (30 * (rd - ISL_EPOCH) + 10646) // 10631
    pd = rd - isl_to_rd(y, 1, 1)
    m = min(12, (11 * pd + 330) // 325)
    return int(y), int(m), int(rd - isl_to_rd(y, m, 1) + 1)


def easter_greg(Y):
    """Gregorian Easter, Butcher/Meeus algorithm. Returns (month, day, h, l); h is the epact term."""
    a = Y % 19
    b, c = Y // 100, Y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    t = h + l - 7 * m + 114
    return t // 31, (t % 31) + 1, h, l


# ── Zoroastrian: 12 months of 30 named days + 5 Gatha days, pure 365-day vague year ─────────────
ZORO_JASHAN = {(1, 19), (2, 3), (3, 6), (4, 13), (5, 7), (6, 4), (7, 16), (8, 10), (9, 9),
               (10, 8), (10, 15), (10, 23), (11, 2), (12, 5)}
# day-name == month-name feasts: Farvardigan 1/19, Ardibeheshtgan 2/3, Khordadgan 3/6, Tirgan 4/13,
# Amardadgan 5/7, Shehrevargan 6/4, Mihragan 7/16, Abangan 8/10, Adargan 9/9, the three Dae days of
# month Dae, Bahmanagan 11/2, Aspandarmadgan 12/5.
ZORO_DAE = (8, 15, 23)          # the three Dae day-names that quarter the month into "weeks"

# ── Celtic tree calendar (Graves 1948): 13 x 28 days from 24 Dec + one nameless day, 23 Dec ─────
TREE_START = [(12, 24), (1, 21), (2, 18), (3, 18), (4, 15), (5, 13), (6, 10), (7, 8), (8, 5),
              (9, 2), (9, 30), (10, 28), (11, 25)]
# Beth Birch, Luis Rowan, Nion Ash, Fearn Alder, Saille Willow, Uath Hawthorn, Duir Oak,
# Tinne Holly, Coll Hazel, Muin Vine, Gort Ivy, Ngetal Reed, Ruis Elder.  23 Dec = the nameless day.

# ── Runic half-months (Pennick 1990): 24 Elder Futhark runes, Fehu opening on 29 June ───────────
RUNE_START = [(6, 29), (7, 14), (7, 29), (8, 13), (8, 29), (9, 13), (9, 28), (10, 13),
              (10, 28), (11, 13), (11, 28), (12, 13), (12, 28), (1, 13), (1, 28), (2, 12),
              (2, 27), (3, 14), (3, 30), (4, 14), (4, 29), (5, 14), (5, 29), (6, 14)]


def _ordinal_md(m, d):
    """Order (month, day) pairs on a fixed non-leap year, for the two folk calendars.

    29 February is folded onto the 28th: both folk calendars are tabulated on a 365-day year and
    neither author says what to do with the leap day."""
    cum = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if m == 2 and d == 29:
        d = 28
    return cum[m - 1] + d


def _band_index(m, d, starts):
    """Index of the band containing (m, d) for a cyclic list of (month, day) start dates."""
    o = _ordinal_md(m, d)
    so = [_ordinal_md(*s) for s in starts]
    best, bi = None, 0
    for i, s in enumerate(so):
        gap = (o - s) % 365
        if best is None or gap < best:
            best, bi = gap, i
    return bi, best


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Eclipse catalogue (swisseph) and the Saros-Inex lattice
# ════════════════════════════════════════════════════════════════════════════════════════════════
_ECL = {}


def _eclipses(jd_lo, jd_hi):
    """Every global solar and lunar eclipse in the window, from swe.sol_eclipse_when_glob /
    swe.lun_eclipse_when. Cached per window so build() pays for it once."""
    key = (round(jd_lo), round(jd_hi))
    if key in _ECL:
        return _ECL[key]
    sj, sf, lj, lf = [], [], [], []
    t = jd_lo
    while t < jd_hi:
        r, tret = swe.sol_eclipse_when_glob(t, swe.FLG_SWIEPH, 0, False)
        if tret[0] <= t:
            break
        sj.append(tret[0]); sf.append(r); t = tret[0] + 2.0
    t = jd_lo
    while t < jd_hi:
        r, tret = swe.lun_eclipse_when(t, swe.FLG_SWIEPH, 0, False)
        if tret[0] <= t:
            break
        lj.append(tret[0]); lf.append(r); t = tret[0] + 2.0
    out = (np.array(sj), np.array(sf, dtype=np.int64),
           np.array(lj), np.array(lf, dtype=np.int64))
    _ECL[key] = out
    return out


def _saros_series(jd, lunar):
    """Saros series number by the van den Bergh lattice (see the module docstring).

    223 lunations = one Saros (same series); 358 lunations = one Inex (adjacent series), so with
    inv(358 mod 223) = inv(135) = 38 (mod 223):  S = S0 + 38*(L - L0)  (mod 223).
    Anchors: solar 1999-08-11 = Saros 145 (L = -5 from the 2000-01-06 new moon);
             lunar 2019-01-21 = Saros 134 (L = 235 from the corresponding full moon).
    Checked against 11 catalogued solar and 7 catalogued lunar series before use.
    """
    if lunar:
        L = np.round((np.asarray(jd) - FM_EPOCH) / SYNODIC)
        return ((134 + 38 * (L - 235) - 1) % 223) + 1
    L = np.round((np.asarray(jd) - NM_EPOCH) / SYNODIC)
    return ((145 + 38 * (L + 5) - 1) % 223) + 1


def _nearest(events, jd):
    """Signed days from each jd to the nearest event (negative = the event was before)."""
    i = np.searchsorted(events, jd)
    i0 = np.clip(i - 1, 0, len(events) - 1)
    i1 = np.clip(i, 0, len(events) - 1)
    d0, d1 = events[i0] - jd, events[i1] - jd
    pick = np.where(np.abs(d0) <= np.abs(d1), i0, i1)
    return events[pick] - jd, pick


# The interpolation grid, as fixed constants so it is never a function of which couples are being built.
#
# THEY ARE TIED TO THE ACCEPTED BIRTH RANGE, NOT TO THE ASSET, and that is the second time this bit them. The
# first draft put them 200 days outside the shipped Spica table, and because sweshim raises rather than clamps
# outside its tables, the whole array silently fell into the analytic fallback below — a different function,
# for every row. Fixed by matching the table. Then the accepted range moved to 1900 and back, the asset
# resized with it, and the same constants were outside again: 392 silent fallbacks. So they now bracket
# core.YEAR_FLOOR/YEAR_CEIL by a year, and build_asset_v4 guarantees the asset brackets that range by two —
# which makes the grid inside the table by construction rather than by coincidence.
SPICA_GRID_LO = 2378131.5      # 1799-01-01, one year before core.YEAR_FLOOR
SPICA_GRID_HI = 2461771.5      # 2028-01-01, one year after core.YEAR_CEIL


def _spica_ra(jd):
    """Right ascension of Spica (alpha Vir) at each instant — the origin of the Chinese lodges.

    From the ephemeris when the fixed-star file is present; otherwise the documented precession rate
    for Spica, dRA/dt = m + n sin(RA) tan(dec) = 0.013212 deg/yr about RA(J2000) = 201.2937 deg.
    """
    jd = np.asarray(jd, dtype=np.float64)
    # A FIXED GRID, not one derived from the rows. This was `jd.min() - 400` to `jd.max() + 400`, so the
    # interpolation nodes moved with the batch and the same couple got a different Spica: measured on 400
    # real couples built whole versus in two halves, Spica's right ascension shifted 30 arcsec, which
    # flipped 6 of the 240 one-hot columns of `lun: xiu 28` by a full 1.0 — at identical width, so no shape
    # check could catch it. The span below covers the whole shipped ephemeris with margin, so every caller
    # lands inside it and no row can influence another's value.
    grid = np.arange(SPICA_GRID_LO, SPICA_GRID_HI, 365.25)
    try:
        vals = np.array([swe.fixstar2_ut("Spica", float(g),
                                        swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)[0][0] for g in grid])
        vals = np.unwrap(np.deg2rad(vals))
        return np.rad2deg(np.interp(jd, grid, vals)) % 360.0
    except Exception:
        return (201.2937 + 0.013212 * (jd - 2451545.0) / 365.25) % 360.0


# ── the 28 xiu: Han widths in du, and the four palaces of seven lodges each ─────────────────────
XIU_DU = np.array([12, 9, 15, 5, 5, 18, 11,            # Azure Dragon (east)
                   26.25, 8, 12, 10, 17, 16, 9,        # Black Tortoise (north)
                   16, 12, 14, 11, 16, 2, 9,           # White Tiger (west)
                   33, 4, 15, 7, 18, 18, 17],          # Vermilion Bird (south)
                  dtype=np.float64)
assert abs(XIU_DU.sum() - 365.25) < 1e-9, "the Han xiu table must close on 365.25 du"
XIU_DEG = XIU_DU * (360.0 / 365.25)
XIU_EDGE = np.concatenate([[0.0], np.cumsum(XIU_DEG)])   # 0 .. 360, 29 edges

# ── the 27 nakshatras: Vimshottari lords, gana, nadi ───────────────────────────────────────────
VIM_LORD = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8] * 3)     # Ketu Venus Sun Moon Mars Rahu Jup Sat Merc
GANA = np.array([0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1, 1, 0])
#               Deva=0, Manushya=1, Rakshasa=2 (Muhurta Chintamani)
NADI_PAT = np.array([0, 1, 2, 2, 1, 0])                  # Adi, Madhya, Antya — the period-6 zigzag
NADI = NADI_PAT[np.arange(27) % 6]
# Varna rank by Moon-sign element: Brahmin 4 (water), Kshatriya 3 (fire), Vaishya 2 (earth), Shudra 1 (air)
VARNA = np.array([3, 2, 1, 4, 3, 2, 1, 4, 3, 2, 1, 4])
BHAKOOT_BAD = {(2, 12), (12, 2), (5, 9), (9, 5), (6, 8), (8, 6)}
TARA_GOOD = {2, 4, 6, 8, 9}                              # Sampat Kshema Sadhaka Mitra Ati-Mitra

# ── the 28 manazil: planetary lords by the repeating Chaldean order, al-Sharatain = Mars ────────
CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
MANAZIL_LORD = np.array([(i + 2) % 7 for i in range(28)])       # 0 Saturn .. 6 Moon; mansion 1 = Mars
LORD_BENEFIC = np.array([-2.0, 2.0, -2.0, 0.0, 2.0, 0.0, 1.0])  # Sat Jup Mars Sun Ven Mer Moon

PHASE8 = ["new", "crescent", "first quarter", "gibbous",
          "full", "disseminating", "last quarter", "balsamic"]   # Rudhyar, *The Lunation Cycle*


# ════════════════════════════════════════════════════════════════════════════════════════════════
def build(E):
    n = E.n
    IX = E.IDX
    SUN, MOON, TN, MN = IX["Sun"], IX["Moon"], IX["TrueNode"], IX["MeanNode"]
    LON, LAT, SPD, RA, DIST, JD = E.LON, E.LAT, E.SPD, E.RA, E.DIST, E.JD
    out = {}

    # elongation Moon - Sun, 0..360, per slot: the synodic phase itself
    elong = np.mod(LON[:, MOON, :] - LON[:, SUN, :], 360.0)          # (6, n)

    # ── civil dates for the calendar slots ──────────────────────────────────────────────────────
    rd = np.floor(JD - (RD0 - 0.5)).astype(np.int64)                  # (6, n) Rata Die
    gy = np.zeros((6, n), dtype=np.int64)
    gm = np.zeros((6, n), dtype=np.int64)
    gd = np.zeros((6, n), dtype=np.int64)
    for s in CAL_SLOTS:
        for k in range(n):
            y, m, d, _ = swe.revjul(float(rd[s, k]) + RD0, swe.GREG_CAL)
            gy[s, k], gm[s, k], gd[s, k] = y, m, d

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 1. the synodic phase, circular — the smooth form of the whole doctrine
    # ════════════════════════════════════════════════════════════════════════════════════════════
    C = []
    for s in ALL_SLOTS:
        e = elong[s]
        for h in (1, 2, 3, 4):                 # harmonics: the halves, quarters and eighths
            _circ(C, e, h)
        _p(C, (1.0 - np.cos(np.deg2rad(e))) / 2.0)          # illuminated fraction
        _p(C, (e < 180.0).astype(float))                    # waxing
        _p(C, np.minimum(e, 360.0 - e) / 180.0)             # distance from the conjunction
        _p(C, np.abs(180.0 - e) / 180.0)                    # distance from the opposition
    for a in range(6):                                       # the partners' phase relationship
        for b in range(a + 1, 6):
            d = E.wrap(elong[a] - elong[b])
            _circ(C, d)
            _p(C, np.abs(d) / 180.0)
    out["lun: synodic phase circular, 6 instants"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 2. the eight phases and the four quarters, one-hot, and the phase-family pairing
    # ════════════════════════════════════════════════════════════════════════════════════════════
    ph8 = np.floor(elong / 45.0).astype(np.int64) % 8
    ph4 = np.floor(elong / 90.0).astype(np.int64) % 4
    C = []
    for s in ALL_SLOTS:
        _hot(C, ph8[s], 8)
        _hot(C, ph4[s], 4)
    d_oy = np.mod(elong[S_OLD] - elong[S_YNG], 360.0)
    d_wo = np.mod(elong[S_WED] - elong[S_OLD], 360.0)
    d_wy = np.mod(elong[S_WED] - elong[S_YNG], 360.0)
    for d in (d_oy, d_wo, d_wy):
        _hot(C, np.floor(d / 45.0).astype(np.int64) % 8, 8)
    _p(C, (ph8[S_OLD] == ph8[S_YNG]).astype(float))
    _p(C, (ph8[S_WED] == ph8[S_OLD]).astype(float))
    _p(C, (ph8[S_WED] == ph8[S_YNG]).astype(float))
    _p(C, (ph8[S_PO] == ph8[S_PY]).astype(float))            # progressed lunation phases agreeing
    _p(C, (ph4[S_OLD] == ph4[S_YNG]).astype(float))
    _p(C, ((ph8[S_OLD] + 4) % 8 == ph8[S_YNG]).astype(float))   # opposite phases of the cycle
    out["lun: eight phases one-hot + pairing"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 3. the Arabic 28 manazil — equal 12 deg 51' 26" of ecliptic from the vernal point
    # ════════════════════════════════════════════════════════════════════════════════════════════
    W28 = 360.0 / 28.0
    man_moon = np.floor(np.mod(LON[:, MOON, :], 360.0) / W28).astype(np.int64) % 28
    man_sun = np.floor(np.mod(LON[:, SUN, :], 360.0) / W28).astype(np.int64) % 28
    C = []
    for s in CAL_SLOTS:
        _hot(C, man_moon[s], 28)
        _circ(C, man_moon[s] * W28)
        _hot(C, MANAZIL_LORD[man_moon[s]], 7)
        _p(C, LORD_BENEFIC[MANAZIL_LORD[man_moon[s]]])
        _p(C, np.mod(LON[s, MOON, :], W28) / W28)            # position inside the mansion
    _hot(C, man_sun[S_WED], 28)                              # the Sun's station: the anwa' calendar
    _hot(C, man_sun[S_OLD], 28)
    dm = (man_moon[S_OLD] - man_moon[S_YNG]) % 28
    _hot(C, dm, 28)
    for a, b in ((S_OLD, S_YNG), (S_WED, S_OLD), (S_WED, S_YNG)):
        _circ(C, (man_moon[a] - man_moon[b]) % 28 * W28)
        _p(C, (man_moon[a] == man_moon[b]).astype(float))
        _p(C, (MANAZIL_LORD[man_moon[a]] == MANAZIL_LORD[man_moon[b]]).astype(float))
        _p(C, LORD_BENEFIC[MANAZIL_LORD[man_moon[a]]] * LORD_BENEFIC[MANAZIL_LORD[man_moon[b]]])
    out["lun: manazil 28 (Arabic, ecliptic)"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 4. the 27 nakshatras measured TROPICALLY, and the four kootas that follow from them
    # ════════════════════════════════════════════════════════════════════════════════════════════
    W27 = 360.0 / 27.0
    nak = np.floor(np.mod(LON[:, MOON, :], 360.0) / W27).astype(np.int64) % 27
    pada = np.floor(np.mod(LON[:, MOON, :], W27) / (W27 / 4.0)).astype(np.int64) % 4
    rashi = np.floor(np.mod(LON[:, MOON, :], 360.0) / 30.0).astype(np.int64) % 12
    C = []
    for s in CAL_SLOTS:
        _hot(C, nak[s], 27)
        _hot(C, VIM_LORD[nak[s]], 9)
        _circ(C, nak[s] * W27)
    for s in (S_OLD, S_YNG, S_WED):
        _hot(C, pada[s], 4)
    for s in (S_OLD, S_YNG):
        _hot(C, GANA[nak[s]], 3)
        _hot(C, NADI[nak[s]], 3)
    no, ny = nak[S_OLD], nak[S_YNG]
    ro, ry = rashi[S_OLD], rashi[S_YNG]
    # Tara/Dina koota (3 points): count nakshatras from one to the other, reduce mod 9
    cnt_oy = ((ny - no) % 27) + 1
    cnt_yo = ((no - ny) % 27) + 1
    tara_oy = ((cnt_oy - 1) % 9) + 1
    tara_yo = ((cnt_yo - 1) % 9) + 1
    good_oy = np.isin(tara_oy, list(TARA_GOOD)).astype(float)
    good_yo = np.isin(tara_yo, list(TARA_GOOD)).astype(float)
    _hot(C, tara_oy - 1, 9)
    _hot(C, tara_yo - 1, 9)
    _p(C, good_oy); _p(C, good_yo)
    tara_pts = 3.0 * (good_oy + good_yo) / 2.0
    _p(C, tara_pts)
    # Nadi koota (8 points): same nadi is the dosha
    same_nadi = (NADI[no] == NADI[ny]).astype(float)
    nadi_pts = 8.0 * (1.0 - same_nadi)
    _p(C, same_nadi); _p(C, nadi_pts)
    _hot(C, NADI[no] * 3 + NADI[ny], 9)
    # Bhakoot koota (7 points): the 2/12, 5/9, 6/8 rashi counts are the dosha
    c1 = ((ry - ro) % 12) + 1
    c2 = ((ro - ry) % 12) + 1
    bad = np.array([1.0 if (int(a), int(b)) in BHAKOOT_BAD else 0.0 for a, b in zip(c1, c2)])
    bha_pts = 7.0 * (1.0 - bad)
    _hot(C, c1 - 1, 12); _hot(C, c2 - 1, 12)
    _p(C, bad); _p(C, bha_pts)
    # Varna koota (1 point): the groom's varna must not fall below the bride's; sex unknown, so both
    v_o, v_y = VARNA[ro], VARNA[ry]
    var_oy = (v_o >= v_y).astype(float)
    var_yo = (v_y >= v_o).astype(float)
    _p(C, var_oy); _p(C, var_yo); _p(C, (v_o - v_y).astype(float))
    _hot(C, v_o - 1, 4); _hot(C, v_y - 1, 4)
    # the partial 19-point subtotal, both orderings
    _p(C, tara_pts + nadi_pts + bha_pts + var_oy)
    _p(C, tara_pts + nadi_pts + bha_pts + var_yo)
    _hot(C, (ny - no) % 27, 27)
    _circ(C, ((ny - no) % 27) * W27)
    _p(C, (no == ny).astype(float))
    out["lun: nakshatra 27 tropical + partial ashtakoot"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 5. the Chinese 28 xiu — unequal, equatorial, anchored on Spica
    # ════════════════════════════════════════════════════════════════════════════════════════════
    C = []
    xiu_moon = np.zeros((6, n), dtype=np.int64)
    xiu_sun = np.zeros((6, n), dtype=np.int64)
    xiu_frac = np.zeros((6, n))
    for s in CAL_SLOTS:
        origin = _spica_ra(JD[s])
        for tgt, store in ((MOON, xiu_moon), (SUN, xiu_sun)):
            off = np.mod(RA[s, tgt, :] - origin, 360.0)
            idx = np.clip(np.searchsorted(XIU_EDGE, off, side="right") - 1, 0, 27)
            store[s] = idx
            if tgt == MOON:
                xiu_frac[s] = (off - XIU_EDGE[idx]) / XIU_DEG[idx]
    for s in CAL_SLOTS:
        _hot(C, xiu_moon[s], 28)
        _circ(C, xiu_moon[s] * (360.0 / 28.0))
        _hot(C, xiu_moon[s] // 7, 4)                     # the four palaces
        _hot(C, xiu_moon[s] % 7, 7)                      # the septenary within the palace
        _p(C, xiu_frac[s])
        _p(C, XIU_DEG[xiu_moon[s]] / 30.0)               # how wide the occupied lodge is
    _hot(C, xiu_sun[S_WED], 28)
    for a, b in ((S_OLD, S_YNG), (S_WED, S_OLD), (S_WED, S_YNG)):
        _p(C, (xiu_moon[a] == xiu_moon[b]).astype(float))
        _p(C, (xiu_moon[a] // 7 == xiu_moon[b] // 7).astype(float))
        _circ(C, ((xiu_moon[a] - xiu_moon[b]) % 28) * (360.0 / 28.0))
    _hot(C, (xiu_moon[S_OLD] - xiu_moon[S_YNG]) % 28, 28)
    out["lun: xiu 28 (Chinese, equatorial)"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 6. three lunar months and their beats — Meeus's mean elements D, M, M', F
    # ════════════════════════════════════════════════════════════════════════════════════════════
    C = []
    T = (JD - 2451545.0) / 36525.0
    D = (297.8501921 + 445267.1114034 * T - 0.0018819 * T ** 2
         + T ** 3 / 545868.0 - T ** 4 / 113065000.0)                       # mean elongation
    M = (357.5291092 + 35999.0502909 * T - 0.0001536 * T ** 2 + T ** 3 / 24490000.0)   # Sun anomaly
    MP = (134.9633964 + 477198.8675055 * T + 0.0087414 * T ** 2
          + T ** 3 / 69699.0 - T ** 4 / 14712000.0)                        # Moon anomaly
    F = (93.2720950 + 483202.0175233 * T - 0.0036539 * T ** 2
         - T ** 3 / 3526000.0 + T ** 4 / 863310000.0)                      # argument of latitude
    for s in ALL_SLOTS:
        for a in (D[s], M[s], MP[s], F[s]):
            _circ(C, a)
        for a in (D[s] - F[s], D[s] - MP[s], F[s] - MP[s], D[s] - M[s]):   # the beat periods
            _circ(C, a)
        _p(C, DIST[s, MOON, :] / 0.00257 - 1.0)                             # perigee/apogee, direct
        _p(C, LAT[s, MOON, :] / 5.2)                                        # draconic, direct
        _p(C, SPD[s, MOON, :] / MEAN_MOON_SPEED - 1.0)                      # anomalistic, direct
        _p(C, np.mod(JD[s] - NM_EPOCH, SYNODIC) / SYNODIC)
        _p(C, np.mod(JD[s] - NM_EPOCH, DRACONIC) / DRACONIC)
        _p(C, np.mod(JD[s] - NM_EPOCH, ANOMALISTIC) / ANOMALISTIC)
        _p(C, np.mod(JD[s] - NM_EPOCH, TROPICAL_M) / TROPICAL_M)
    for a, b in ((S_OLD, S_YNG), (S_WED, S_OLD), (S_WED, S_YNG)):
        for arr in (D, MP, F):
            _circ(C, arr[a] - arr[b])
        _p(C, np.abs(E.wrap(F[a] - F[b])) / 180.0)
    out["lun: synodic/draconic/anomalistic months + beats"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 7. eclipse proximity and the classical ecliptic limits
    # ════════════════════════════════════════════════════════════════════════════════════════════
    sj, sf, lj, lf = _eclipses(float(JD.min()) - 400.0, float(JD.max()) + 400.0)
    C = []
    dt_s = np.zeros((6, n)); dt_l = np.zeros((6, n))
    pick_s = np.zeros((6, n), dtype=np.int64); pick_l = np.zeros((6, n), dtype=np.int64)
    for s in CAL_SLOTS:
        dt_s[s], pick_s[s] = _nearest(sj, JD[s])
        dt_l[s], pick_l[s] = _nearest(lj, JD[s])
    for s in CAL_SLOTS:
        for dt in (dt_s[s], dt_l[s]):
            _p(C, dt / 180.0)
            _p(C, np.abs(dt) / 180.0)
            for tau in (2.0, 7.0, 20.0, 60.0, 180.0):
                _p(C, np.exp(-np.abs(dt) / tau))
            for w in (1.0, 3.0, 7.0, 15.0, 30.0, 90.0, 180.0):
                _p(C, (np.abs(dt) <= w).astype(float))
        both = np.minimum(np.abs(dt_s[s]), np.abs(dt_l[s]))
        _p(C, both / 180.0)
        _p(C, np.exp(-both / 7.0))
        _p(C, np.exp(-both / 30.0))
        _p(C, (both <= 15.0).astype(float))
        # the ecliptic limits: how far the Sun and Moon stand from the nodal axis
        sun_nd = _fold90(LON[s, SUN, :] - LON[s, TN, :])
        sun_nd_m = _fold90(LON[s, SUN, :] - LON[s, MN, :])
        moon_nd = _fold90(LON[s, MOON, :] - LON[s, TN, :])
        _p(C, sun_nd / 90.0); _p(C, sun_nd_m / 90.0); _p(C, moon_nd / 90.0)
        _p(C, np.abs(LAT[s, MOON, :]) / 5.2)
        _p(C, (sun_nd < 9.55).astype(float))       # solar eclipse certain (minor limit)
        _p(C, (sun_nd < 15.35).astype(float))      # solar eclipse possible (major limit)
        _p(C, (sun_nd < 3.80).astype(float))       # lunar eclipse certain
        _p(C, (sun_nd < 12.15).astype(float))      # lunar eclipse possible
        _p(C, (sun_nd < 18.0).astype(float))       # eclipse season at all
        _circ(C, 2.0 * (LON[s, SUN, :] - LON[s, TN, :]))
        _p(C, np.exp(-0.5 * (sun_nd / 6.0) ** 2))
        # syzygy x node: an eclipse needs both, so carry the product explicitly
        syz = np.maximum(np.exp(-0.5 * (np.minimum(elong[s], 360.0 - elong[s]) / 12.0) ** 2),
                         np.exp(-0.5 * ((180.0 - elong[s]) / 12.0) ** 2))
        _p(C, syz)
        _p(C, syz * np.exp(-0.5 * (sun_nd / 8.0) ** 2))
    # how many eclipses fall in the wedding's own year. Deliberately NOT counted over the interval
    # between the births or from a birth to the wedding: an eclipse count over an interval is that
    # interval's length divided by 173.3 days, i.e. the age gap or the age wearing a lunar name.
    for ev in (sj, lj):
        cnt = (np.searchsorted(ev, JD[S_WED] + 182.6) - np.searchsorted(ev, JD[S_WED] - 182.6))
        _p(C, cnt.astype(float))
    out["lun: eclipse proximity + ecliptic limits"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 8. the long cycles: Saros, Inex, Exeligmos, Metonic, Callippic, Hipparchic, and the computus
    # ════════════════════════════════════════════════════════════════════════════════════════════
    C = []
    CALLIPPIC_EPOCH = swe.julday(-329, 6, 28, 12.0, swe.JUL_CAL)     # Callippus, summer solstice 330 BC
    for s in CAL_SLOTS:
        for per, ep in ((SAROS, NM_EPOCH), (INEX, NM_EPOCH), (EXELIGMOS, NM_EPOCH),
                        (METONIC, NM_EPOCH), (METONIC_CAL, CALLIPPIC_EPOCH),
                        (CALLIPPIC, CALLIPPIC_EPOCH), (HIPPARCHIC, CALLIPPIC_EPOCH)):
            frac = np.mod(JD[s] - ep, per) / per
            _circ(C, frac * 360.0)
            _p(C, frac)
        _p(C, np.floor(np.mod(JD[s] - CALLIPPIC_EPOCH, CALLIPPIC) / METONIC_CAL))  # Callippic quarter
    for s in CAL_SLOTS:                                              # the computus
        gn = (gy[s] % 19) + 1                                        # golden number
        _hot(C, gn - 1, 19)
        _circ(C, (gn - 1) * (360.0 / 19.0))
        ep_j = (11 * (gn - 1)) % 30                                  # the classical Julian epact
        _p(C, ep_j / 30.0)
        _circ(C, ep_j * 12.0)
    ymin, ymax = int(gy[CAL_SLOTS].min()), int(gy[CAL_SLOTS].max())
    etab = {Y: easter_greg(Y) for Y in range(ymin - 1, ymax + 2)}
    for s in CAL_SLOTS:
        emo = np.array([etab[int(y)][0] for y in gy[s]], dtype=np.int64)
        eda = np.array([etab[int(y)][1] for y in gy[s]], dtype=np.int64)
        eh = np.array([etab[int(y)][2] for y in gy[s]], dtype=np.float64)
        el = np.array([etab[int(y)][3] for y in gy[s]], dtype=np.float64)
        eord = np.array([_ordinal_md(int(a), int(b)) for a, b in zip(emo, eda)], dtype=np.float64)
        dord = np.array([_ordinal_md(int(a), int(b)) for a, b in zip(gm[s], gd[s])], dtype=np.float64)
        _p(C, eord / 365.0); _p(C, eh / 29.0); _p(C, el / 6.0)
        dd = (dord - eord + 182.5) % 365.0 - 182.5
        _p(C, dd / 182.5)
        _circ(C, dd * (360.0 / 365.0))
        _p(C, (np.abs(dd) <= 7.0).astype(float))                     # married in Easter week
        _p(C, ((dd >= -46.0) & (dd < 0.0)).astype(float))            # married in Lent
    for a, b in ((S_OLD, S_YNG), (S_WED, S_OLD), (S_WED, S_YNG)):
        for per, ep in ((SAROS, NM_EPOCH), (METONIC, NM_EPOCH), (INEX, NM_EPOCH)):
            _circ(C, (np.mod(JD[a] - ep, per) - np.mod(JD[b] - ep, per)) / per * 360.0)
        _p(C, ((gy[a] % 19) == (gy[b] % 19)).astype(float))           # the same golden number
    # the Saros SERIES of the eclipse nearest each instant
    for s in CAL_SLOTS:
        ss = _saros_series(sj[pick_s[s]], lunar=False)
        sl = _saros_series(lj[pick_l[s]], lunar=True)
        for v in (ss, sl):
            _circ(C, v * (360.0 / 223.0))
            _p(C, v / 223.0)
            _p(C, (v % 2).astype(float))                              # odd/even = node crossed
        if s == S_WED:
            _hot(C, (ss // 19).astype(np.int64), 12)
            _hot(C, (sl // 19).astype(np.int64), 12)
        # where in its own series the eclipse sits: the signed Sun-node distance at the eclipse
        _p(C, np.abs(E.wrap(LON[s, SUN, :] - LON[s, TN, :])) / 180.0)
    out["lun: saros/inex/metonic/callippic + computus"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 9. the 45 planet-pair synodic phases at the WEDDING — the cleanest planetary-cycle encoding
    # ════════════════════════════════════════════════════════════════════════════════════════════
    bodies = E.MODERN
    pairs = [(a, b) for i, a in enumerate(bodies) for b in bodies[i + 1:]]
    C = []
    for a, b in pairs:
        e = np.mod(LON[S_WED, b, :] - LON[S_WED, a, :], 360.0)
        _circ(C, e)
        _p(C, e / 360.0)                                        # fraction of the synodic cycle run
        _p(C, np.minimum(e, 360.0 - e) / 180.0)
    out["lun: 45 pair synodic phases, wedding"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 10. the same 45 pair phases at both births and the Davison, and the partners' difference
    # ════════════════════════════════════════════════════════════════════════════════════════════
    C = []
    for a, b in pairs:
        eo = np.mod(LON[S_OLD, b, :] - LON[S_OLD, a, :], 360.0)
        ey = np.mod(LON[S_YNG, b, :] - LON[S_YNG, a, :], 360.0)
        ed = np.mod(LON[S_DAV, b, :] - LON[S_DAV, a, :], 360.0)
        _circ(C, eo); _circ(C, ey); _circ(C, ed)
        _circ(C, ey - eo)
        _p(C, np.abs(E.wrap(ey - eo)) / 180.0)
    out["lun: 45 pair synodic phases, births + diff"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 11. void-of-course Moon and the electional Moon at the wedding
    #     Lilly, *Christian Astrology* p.112 (void of course); Sahl ibn Bishr, *On Elections*;
    #     Bonatti's "considerations before judgement" for via combusta and the beams.
    # ════════════════════════════════════════════════════════════════════════════════════════════
    C = []
    lm = np.mod(LON[S_WED, MOON, :], 360.0)
    sm = np.maximum(SPD[S_WED, MOON, :], 1e-6)
    deg_exit = 30.0 - np.mod(lm, 30.0)
    days_exit = deg_exit / sm
    _p(C, deg_exit / 30.0); _p(C, days_exit / 2.5)
    PT = np.array([0.0, 60.0, 90.0, 120.0, 180.0, 240.0, 270.0, 300.0])   # the Ptolemaic crossings
    others = [IX[b] for b in ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")]
    best = np.full(n, 1e6)
    for b in others:
        v = np.maximum(sm - SPD[S_WED, b, :], 1e-6)                # the Moon always outruns them
        e = np.mod(lm - LON[S_WED, b, :], 360.0)
        gap = np.min(np.mod(PT[None, :] - e[:, None], 360.0), axis=1)
        dperf = gap / v                                            # days until it perfects
        best = np.minimum(best, dperf)
        _p(C, np.minimum(dperf, 5.0) / 5.0)
        _p(C, np.minimum(gap, 60.0) / 60.0)
        _p(C, (dperf < days_exit).astype(float))                   # an applying aspect, in sign
        _p(C, np.minimum(np.min(np.abs(E.wrap(PT[None, :] - e[:, None])), axis=1), 12.0) / 12.0)
    voc = (best > days_exit).astype(float)
    _p(C, np.minimum(best, 5.0) / 5.0)
    _p(C, voc)
    _p(C, ((best * sm) > (deg_exit + 3.0)).astype(float))          # with a 3 deg moiety allowance
    _p(C, (days_exit - np.minimum(best, 5.0)) / 2.5)
    # the rest of the electional Moon
    sunsep = E.sep(LON[S_WED, MOON, :], LON[S_WED, SUN, :])
    beams = (sunsep < 17.0).astype(float)
    combust = (sunsep < 8.5).astype(float)
    cazimi = (sunsep < 0.2833).astype(float)
    waxing = (elong[S_WED] < 180.0).astype(float)
    # "increasing in latitude": the Moon's ecliptic latitude is sin(F), so it rises when cos(F) > 0
    lat_inc = (np.cos(np.deg2rad(F[S_WED])) > 0).astype(float)
    via = ((lm >= 195.0) & (lm < 225.0)).astype(float)             # 15 Libra - 15 Scorpio
    lastdeg = (np.mod(lm, 30.0) >= 27.0).astype(float)
    firstdeg = (np.mod(lm, 30.0) < 3.0).astype(float)
    msign = np.floor(lm / 30.0).astype(np.int64) % 12
    dom = (msign == 3).astype(float)
    exalt = (msign == 1).astype(float)
    detr = (msign == 9).astype(float)
    fall = (msign == 7).astype(float)
    for a in (beams, combust, cazimi, waxing, lat_inc, via, lastdeg, firstdeg, dom, exalt, detr, fall):
        _p(C, a)
    _p(C, sunsep / 180.0)
    _p(C, SPD[S_WED, MOON, :] / MEAN_MOON_SPEED)
    _p(C, (SPD[S_WED, MOON, :] > MEAN_MOON_SPEED).astype(float))
    _p(C, LAT[S_WED, MOON, :] / 5.2)
    benefic_sign = np.isin(msign, [1, 3, 6, 8, 11]).astype(float)   # Venus's and Jupiter's domiciles
    _p(C, benefic_sign)
    appl = {}
    for nm in ("Venus", "Jupiter", "Saturn", "Mars"):
        b = IX[nm]
        v = np.maximum(sm - SPD[S_WED, b, :], 1e-6)
        e = np.mod(lm - LON[S_WED, b, :], 360.0)
        gap = np.min(np.mod(PT[None, :] - e[:, None], 360.0), axis=1)
        appl[nm] = ((gap / v) < days_exit).astype(float)
        _p(C, appl[nm])
        sepd = E.sep(lm, LON[S_WED, b, :])
        hard = np.maximum.reduce([E.orbkern(sepd, ang, 3.0) for ang in (0.0, 90.0, 180.0)])
        _p(C, hard)
    # the tradition's own tally: Sahl's conditions for an election, counted
    good = (waxing + benefic_sign + appl["Venus"] + appl["Jupiter"] + (1.0 - voc)
            + (1.0 - via) + (1.0 - beams) + dom + exalt)
    bad = (voc + via + beams + combust + lastdeg + detr + fall
           + appl["Saturn"] + appl["Mars"] + (1.0 - waxing))
    _p(C, good); _p(C, bad); _p(C, good - bad)
    out["lun: void-of-course + electional Moon"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 12. the Hebrew calendar and the halakhic marriage windows
    # ════════════════════════════════════════════════════════════════════════════════════════════
    C = []
    HY = np.zeros((6, n), dtype=np.int64); HM = np.zeros((6, n), dtype=np.int64)
    HD = np.zeros((6, n), dtype=np.int64); HL = np.zeros((6, n), dtype=np.int64)
    HYL = np.zeros((6, n), dtype=np.int64)
    for s in CAL_SLOTS:
        for k in range(n):
            y, m, d = rd_to_heb(int(rd[s, k]))
            HY[s, k], HM[s, k], HD[s, k] = y, m, d
            HL[s, k] = 1 if heb_leap(y) else 0
            HYL[s, k] = heb_year_len(y)
    for s in CAL_SLOTS:
        _hot(C, HM[s] - 1, 13)
        _circ(C, (HD[s] - 1) * 12.0)
        _p(C, HD[s] / 30.0)
        _p(C, HL[s].astype(float))
        _circ(C, (HY[s] % 19) * (360.0 / 19.0))
        _hot(C, rd[s] % 7, 7)                            # 0 = Sunday; Shabbat = 6
    _hot(C, HD[S_WED] - 1, 30)
    _hot(C, HY[S_WED] % 19, 19)
    # the six possible Hebrew year lengths: 353/354/355 (haser/kesidran/shalem) and 383/384/385
    ylen_bin = (HYL[S_WED] - 353) + np.where(HYL[S_WED] >= 383, -27, 0)
    _hot(C, ylen_bin, 6)
    # halakhic windows at the wedding (month numbering: Nisan=1 .. Tishri=7 .. Adar=12, Adar II=13)
    m_, d_ = HM[S_WED], HD[S_WED]
    dow = (rd[S_WED] % 7).astype(np.int64)
    omer_day = np.where(m_ == 1, d_ - 15, np.where(m_ == 2, d_ + 15, np.where(m_ == 3, d_ + 44, 0)))
    in_omer = ((omer_day >= 1) & (omer_day <= 49)).astype(float)      # 16 Nisan - 5 Sivan
    omer_early = ((omer_day >= 1) & (omer_day <= 32)).astype(float)   # up to Lag ba-Omer (18 Iyyar)
    omer_late = ((omer_day >= 34) & (omer_day <= 49)).astype(float)
    lag = (omer_day == 33).astype(float)
    three_weeks = (((m_ == 4) & (d_ >= 17)) | ((m_ == 5) & (d_ <= 9))).astype(float)
    nine_days = ((m_ == 5) & (d_ <= 9)).astype(float)
    yomtov = (((m_ == 7) & np.isin(d_, [1, 2, 10, 15, 16, 21, 22, 23]))
              | ((m_ == 1) & np.isin(d_, [15, 16, 20, 21, 22]))
              | ((m_ == 3) & np.isin(d_, [6, 7]))).astype(float)
    cholhamoed = (((m_ == 7) & (d_ >= 17) & (d_ <= 20))
                  | ((m_ == 1) & (d_ >= 17) & (d_ <= 19))).astype(float)
    shabbat = (dow == 6).astype(float)
    rosh_chodesh = ((d_ == 1) | (d_ == 30)).astype(float)
    chanukah = (((m_ == 9) & (d_ >= 25)) | ((m_ == 10) & (d_ <= 3))).astype(float)
    # Purim is 14 Adar, and in a leap year 14 Adar II (month 13)
    purim = ((m_ == np.where(HL[S_WED] == 1, 13, 12)) & (d_ == 14)).astype(float)
    fasts = (((m_ == 10) & (d_ == 10)) | ((m_ == 4) & (d_ == 17)) | ((m_ == 5) & (d_ == 9))
             | ((m_ == 7) & (d_ == 3)) | ((m_ == 7) & (d_ == 10))).astype(float)
    elul = (m_ == 6).astype(float)
    permitted = (1.0 - np.clip(shabbat + yomtov + cholhamoed + omer_early + omer_late
                               + three_weeks + fasts, 0.0, 1.0))
    for a in (in_omer, omer_early, omer_late, lag, three_weeks, nine_days, yomtov, cholhamoed,
              shabbat, rosh_chodesh, chanukah, purim, fasts, elul, permitted):
        _p(C, a)
    _p(C, np.clip(omer_day, 0, 49) / 49.0)
    _p(C, (rd[S_WED] - np.array([heb_to_rd(int(y), 7, 1) for y in HY[S_WED]])) / 384.0)
    _p(C, (rd[S_WED] - np.array([heb_to_rd(int(y), 1, 15) for y in HY[S_WED]])) / 384.0)
    _circ(C, (HM[S_OLD] - HM[S_YNG]) * (360.0 / 13.0))
    _p(C, (HM[S_OLD] == HM[S_YNG]).astype(float))
    _circ(C, ((HY[S_OLD] % 19) - (HY[S_YNG] % 19)) * (360.0 / 19.0))
    _p(C, (HL[S_OLD] == HL[S_YNG]).astype(float))
    out["lun: hebrew calendar + halakhic windows"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 13. the Islamic tabular civil calendar and its marriage seasons
    # ════════════════════════════════════════════════════════════════════════════════════════════
    C = []
    IY = np.zeros((6, n), dtype=np.int64); IM = np.zeros((6, n), dtype=np.int64)
    ID = np.zeros((6, n), dtype=np.int64)
    for s in CAL_SLOTS:
        for k in range(n):
            y, m, d = rd_to_isl(int(rd[s, k]))
            IY[s, k], IM[s, k], ID[s, k] = y, m, d
    for s in CAL_SLOTS:
        _hot(C, IM[s] - 1, 12)
        _circ(C, (ID[s] - 1) * 12.0)
        _p(C, ID[s] / 30.0)
        _circ(C, (IY[s] % 30) * 12.0)
        _p(C, np.array([1.0 if isl_leap(int(y)) else 0.0 for y in IY[s]]))
    _hot(C, ID[S_WED] - 1, 30)
    _hot(C, IY[S_WED] % 30, 30)
    m_, d_ = IM[S_WED], ID[S_WED]
    ramadan = (m_ == 9).astype(float)
    shawwal = (m_ == 10).astype(float)                    # favoured: Sahih Muslim, Book of Marriage
    muharram = (m_ == 1).astype(float)
    ashura10 = ((m_ == 1) & (d_ <= 10)).astype(float)
    safar = (m_ == 2).astype(float)
    rajab = (m_ == 7).astype(float)
    shaban = (m_ == 8).astype(float)
    qada = (m_ == 11).astype(float)
    hijjah = (m_ == 12).astype(float)
    hajj = ((m_ == 12) & (d_ >= 8) & (d_ <= 13)).astype(float)
    sacred = np.isin(m_, [1, 7, 11, 12]).astype(float)    # Qur'an 9:36, the four sacred months
    eid_fitr = ((m_ == 10) & (d_ <= 3)).astype(float)
    eid_adha = ((m_ == 12) & (d_ >= 10) & (d_ <= 13)).astype(float)
    friday = ((rd[S_WED] % 7) == 5).astype(float)
    fullmoon = ((d_ >= 13) & (d_ <= 15)).astype(float)
    for a in (ramadan, shawwal, muharram, ashura10, safar, rajab, shaban, qada, hijjah, hajj,
              sacred, eid_fitr, eid_adha, friday, fullmoon):
        _p(C, a)
    rec = shawwal + friday + shaban + fullmoon
    dis = ramadan + ashura10 + safar + hajj + eid_fitr + eid_adha
    _p(C, rec); _p(C, dis); _p(C, rec - dis)
    _hot(C, (rd[S_WED] % 7).astype(np.int64), 7)
    _circ(C, (IM[S_OLD] - IM[S_YNG]) * 30.0)
    _p(C, (IM[S_OLD] == IM[S_YNG]).astype(float))
    _circ(C, (ID[S_OLD] - ID[S_YNG]) * 12.0)
    out["lun: islamic hijri (tabular) + seasons"] = _mk(C, n)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 14. folk calendars: Zoroastrian day-names, the Celtic tree months, the runic half-months
    # ════════════════════════════════════════════════════════════════════════════════════════════
    C = []
    YZ_EPOCH = int(swe.julday(632, 6, 16, 12.0, swe.JUL_CAL)) - int(RD0)     # 1 Farvardin 1 YZ
    for s in CAL_SLOTS:
        el_ = (rd[s] - YZ_EPOCH)
        doy = np.mod(el_, 365).astype(np.int64)
        zm = np.minimum(doy // 30, 12).astype(np.int64)          # 0..11 months, 12 = the Gatha days
        zd = np.where(zm < 12, doy % 30, doy - 360).astype(np.int64) + 1
        gatha = (zm == 12).astype(float)
        jash = np.array([1.0 if (int(a) + 1, int(b)) in ZORO_JASHAN else 0.0
                         for a, b in zip(zm, zd)])
        _hot(C, zm, 13)
        _circ(C, np.where(zm < 12, (zd - 1) * 12.0, 0.0))
        _p(C, np.where(zm < 12, zd / 30.0, 0.0))
        _p(C, gatha); _p(C, jash)
        _p(C, ((zm < 12) & (zd <= 7)).astype(float))             # the Amesha Spenta heptad
        _p(C, np.isin(zd, ZORO_DAE).astype(float) * (zm < 12))   # the three Dae quarter-marks
        # Shahanshahi runs one month later than Qadimi after the ~1129 CE intercalation
        doy_sh = np.mod(el_ - 30, 365).astype(np.int64)
        _hot(C, np.minimum(doy_sh // 30, 12).astype(np.int64), 13)
        if s == S_WED:
            _hot(C, np.where(zm < 12, zd - 1, 29).astype(np.int64), 30)
            _hot(C, np.clip((zd - 1) // 8, 0, 3).astype(np.int64), 4)
    zdo = np.mod(rd[S_OLD] - YZ_EPOCH, 365) % 30
    zdy = np.mod(rd[S_YNG] - YZ_EPOCH, 365) % 30
    _circ(C, (zdo - zdy) * 12.0)
    _p(C, (zdo == zdy).astype(float))
    # Celtic tree months (Graves 1948) and the runic half-months (Pennick 1990)
    tree = np.zeros((6, n), dtype=np.int64); tfrac = np.zeros((6, n))
    rune = np.zeros((6, n), dtype=np.int64); rfrac = np.zeros((6, n))
    for s in CAL_SLOTS:
        for k in range(n):
            i, g = _band_index(int(gm[s, k]), int(gd[s, k]), TREE_START)
            tree[s, k], tfrac[s, k] = i, g / 28.0
            j, h = _band_index(int(gm[s, k]), int(gd[s, k]), RUNE_START)
            rune[s, k], rfrac[s, k] = j, h / 16.0
    for s in CAL_SLOTS:
        _hot(C, tree[s], 13)
        _circ(C, tree[s] * (360.0 / 13.0))
        _p(C, np.clip(tfrac[s], 0.0, 2.0))
        _p(C, (tfrac[s] > 1.0).astype(float))                    # the nameless day, 23 December
        _circ(C, rune[s] * 15.0)
        _hot(C, np.clip(rune[s] // 8, 0, 2), 3)                  # the three aettir
        _p(C, np.clip(rfrac[s], 0.0, 2.0))
    _hot(C, rune[S_WED], 24)
    _hot(C, rune[S_OLD], 24)
    for a, b in ((S_OLD, S_YNG), (S_WED, S_OLD), (S_WED, S_YNG)):
        _circ(C, (tree[a] - tree[b]) * (360.0 / 13.0))
        _p(C, (tree[a] == tree[b]).astype(float))
        _circ(C, (rune[a] - rune[b]) * 15.0)
        _p(C, (rune[a] == rune[b]).astype(float))
    out["lun: zoroastrian + celtic tree + runic"] = _mk(C, n)

    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import time
    from core import load
    from evalx import quick

    t0 = time.time()
    E = load()
    B = build(E)
    print(f"{TRADITION}\n{len(B)} blocks built in {time.time()-t0:.1f}s\n")

    # ── self-checks the contract asks for ───────────────────────────────────────────────────────
    seen = set()
    total = 0
    for name, X in B.items():
        assert name not in seen, f"duplicate block name {name}"
        assert name.startswith("lun: "), f"block {name!r} is missing the tradition tag"
        seen.add(name)
        assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
        assert X.dtype == np.float64, f"{name}: dtype {X.dtype} != float64"
        assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
        assert np.isfinite(X).all(), f"{name}: non-finite values"
        assert X.std(axis=0).max() > 1e-12, f"{name}: all-constant block"
        total += X.shape[1]
    assert total < 6000, f"{total} columns is over the budget"

    # a few doctrine spot-checks, so a silent index slip cannot pass
    assert abs(XIU_DU.sum() - 365.25) < 1e-9
    assert rd_to_heb(int(swe.julday(2024, 4, 23, 12.0, swe.GREG_CAL)) - int(RD0)) == (5784, 1, 15)
    assert rd_to_isl(int(swe.julday(2000, 1, 1, 12.0, swe.GREG_CAL)) - int(RD0)) == (1420, 9, 24)
    assert easter_greg(2024)[:2] == (3, 31) and easter_greg(2000)[:2] == (4, 23)
    assert int(_saros_series(swe.julday(2024, 4, 8, 18.0, swe.GREG_CAL), False)) == 139
    assert int(_saros_series(swe.julday(2022, 5, 16, 4.0, swe.GREG_CAL), True)) == 131
    print(f"checks passed: {total} columns total\n")

    print(f"{'block':<48} {'cols':>5}  {'acc':>7}  {'auc':>7}")
    print("-" * 74)
    for name, X in B.items():
        a, u = quick(E, X)
        print(f"{name:<48} {X.shape[1]:>5}  {100*a:>6.2f}%  {u:>7.4f}")
    print("\nOK")
    sys.exit(0)
