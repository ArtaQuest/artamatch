"""
trad_babylonian_egyptian.py — the Babylonian and Egyptian doctrines, as feature blocks.

WHAT THIS TRADITION FAMILY ACTUALLY DOES, AND WHAT IS ENCODED HERE

Babylonian celestial divination is not natal astrology in the Hellenistic sense. It is (a) a
schematic arithmetic of time — the ideal 360-day year and the lunar month begun by the first
visibility of the crescent, (b) the *Goal-Year* method: to predict what a planet will do in a
target year, look up what it did one characteristic period earlier (Venus 8 years, Mercury 46,
Saturn 59, Jupiter 71 and 83, Mars 79 and 47, the Moon 18 = the saros) — see the Goal-Year Texts,
e.g. BM 36599, and Neugebauer, *HAMA* II 554ff., (c) the named *heliacal phenomena* of each planet
(first visibility, station, acronychal rising/opposition, last visibility — Neugebauer's letters
Gamma, Phi, Theta, Psi, Omega), and (d) omen protases of the *Enuma Anu Enlil* type: eclipse
possibility, the Moon standing beside a planet, and a body's position in the three "paths" of
Enlil, Anu and Ea (MUL.APIN I) or inside the band called the path of the Moon (the eighteen gods
"in the path of the Moon", MUL.APIN I iv 31-39).

Egyptian material: the 36 decans with their planetary rulers in descending Chaldean order starting
from Mars at Aries 0 (Hephaistion; Firmicus, *Mathesis* IV; the Liber Hermetis decan lists); the
*Egyptian* bounds/terms, which are a different table from Ptolemy's own — the one Ptolemy reports
as "the Egyptians'" in *Tetrabiblos* I.21 and which Valens (*Anthology* III) and Paulus
Alexandrinus (ch. 3) also transmit; the dodekatemoria or twelfth-parts, 2;30 degrees each, which
are a shared Babylonian-Egyptian technique (Neugebauer & Sachs; Brack-Bernsen & Steele,
"Babylonian Mathemagics", on the related Kalendertext x13 scheme); and the civil calendar of 12
months of 30 days plus 5 epagomenal days, its 36 ten-day weeks (decades, which are the decans),
its three Nile seasons Akhet / Peret / Shemu, and the 1461-year Sothic drift of that wandering
year against the Sun.

PROXIES AND LIMITS — stated plainly, because several of these rules want data we do not have

  * NO BIRTH TIME, NO BIRTH PLACE. Everything is computed at 12:00 UT.
  * Heliacal visibility is properly an *arcus visionis* measured in altitude at the moment of
    sunrise or sunset, and therefore depends on the observer's latitude and on the day's exact
    time. We do not have either. The documented proxy used here is elongation in ecliptic
    longitude compared against the conventional arcus-visionis values used in reconstructions of
    the Babylonian phenomena (Mercury 11.5, Venus 5.7, Mars 14.5, Jupiter 9.5, Saturn 13.0
    degrees; Neugebauer HAMA II, Schaefer 1987). A planet is called "morning" when it is west of
    the Sun in longitude and "evening" when east. This gets the *phase of the synodic cycle*
    right and the exact visibility day wrong.
  * Stations are detected by |longitude speed| falling below a per-planet threshold rather than by
    bracketing the turning point, because we have one instant per chart, not a time series.
  * The Babylonian month day is derived from the Sun-Moon elongation: day 1 begins on the evening
    the crescent is first seen, taken here at 11 degrees of elongation (about 17-18 hours after
    conjunction). The Moon's noon longitude is uncertain by roughly +-6 degrees, so a month-day
    feature is uncertain by about half a day and the day-of-month one-hots are correspondingly
    soft. Said once here and not repeated per block.
  * The Egyptian civil date and the schematic 360-day date are counted from Thoth 1 of year 1 of
    the Era of Nabonassar, 26 February 747 BC (Julian) = JD 1448638, the standard chronological
    anchor (Ptolemy's era, *Almagest*). A wrong epoch would only rotate every calendar phase by a
    constant, which the circular encodings absorb; the day-of-year one-hots would shift wholesale.
  * NO HOUSES, NO ASCENDANT. Nothing here needs them: Babylonian omen protases and the Egyptian
    decan/bound/twelfth-part apparatus are all zodiacal or calendrical. This family is the rare
    one that loses almost nothing to the missing birth time — except visibility, as above.
  * WHAT THE CALENDRICAL AND GOAL-YEAR BLOCKS ARE MADE OF, stated so nobody has to guess: the
    Goal-Year phase block and the two-calendar block are functions of the absolute julian day and
    of nothing else. That is the doctrine — a Goal-Year phase is by definition a position within a
    period counted from a fixed epoch — but it means eight mutually incommensurate periods of
    cos/sin jointly identify the date, and the Sothic phase is monotone in the date across this
    dataset's ~469-year span rather than cyclic. Read those two blocks as calendar encodings,
    because that is exactly what the Babylonian scribes' arithmetic was.

REPRESENTATIONS. Each doctrine is emitted more than once on purpose: circular (cos/sin), orb
kernels at the tradition's own thresholds, discrete one-hots, partner cross-contact matrices, and
— where the tradition computes its own number — that number exactly (the Goal-Year recurrence
phase, the EAE day-of-opposition, the count of shared decans and twelfth-parts).
"""

import numpy as np

TRADITION = ("Babylonian & Egyptian (Enuma Anu Enlil omens, Goal-Year periods, MUL.APIN paths, "
             "36 decans, Egyptian bounds, dodekatemoria)")

# ── epoch and calendrical constants ─────────────────────────────────────────────────────────────
# Thoth 1, year 1 of the Era of Nabonassar = 26 Feb 747 BC (Julian) = JD 1448638. Ptolemy's era.
NAB = 1448638.0
EGY_YEAR = 365.0            # the Egyptian civil "wandering" year: 12 x 30 + 5 epagomenal days
SCHEM_YEAR = 360.0          # the Babylonian ideal / schematic year
SOTHIC_YEARS = 1461         # 1461 civil years = 1460 Julian years
CRESCENT = 11.0             # elongation, in degrees, at which the new crescent is first seen
SYN_MONTH = 29.530589
SAROS = 223 * SYN_MONTH     # 6585.32 days: the 18-year lunar Goal-Year period

CL7 = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
PL5 = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")

# conventional synodic periods, days
SYN = {"Mercury": 115.8775, "Venus": 583.9214, "Mars": 779.9361, "Jupiter": 398.8840,
       "Saturn": 378.0919}

# The Goal-Year periods, as whole numbers of synodic cycles — which is what makes them work and
# why the scribes kept two for Jupiter and two for Mars (Goal-Year Texts; HAMA II 554ff.).
GOAL = {
    "Venus 8y (5 syn)":      5 * SYN["Venus"],
    "Mercury 46y (145 syn)": 145 * SYN["Mercury"],
    "Saturn 59y (57 syn)":   57 * SYN["Saturn"],
    "Jupiter 71y (65 syn)":  65 * SYN["Jupiter"],
    "Jupiter 83y (76 syn)":  76 * SYN["Jupiter"],
    "Mars 79y (37 syn)":     37 * SYN["Mars"],
    "Mars 47y (22 syn)":     22 * SYN["Mars"],
    "Moon 18y (saros)":      SAROS,
}

# arcus visionis proxies (see docstring) and station thresholds in deg/day
AV = {"Mercury": 11.5, "Venus": 5.7, "Mars": 14.5, "Jupiter": 9.5, "Saturn": 13.0}
STAT = {"Mercury": 0.12, "Venus": 0.06, "Mars": 0.035, "Jupiter": 0.020, "Saturn": 0.014}
# greatest elongation for the inner planets; quadrature stands in for the outer ones
MAXEL = {"Mercury": 27.8, "Venus": 46.3, "Mars": 90.0, "Jupiter": 90.0, "Saturn": 90.0}

# ── the 36 decans and their rulers ──────────────────────────────────────────────────────────────
# Descending Chaldean order, the first decan of Aries given to Mars, then round and round: the
# decan-ruler scheme reported as Egyptian by Hephaistion and Firmicus (Mathesis IV).
CHALD = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")
DECAN_RULER = np.array([(2 + d) % 7 for d in range(36)])     # index into CHALD

# ── the EGYPTIAN bounds (terms/horia) — NOT the Ptolemaic set ────────────────────────────────────
# Ptolemy, Tetrabiblos I.21 ("the Egyptians'" table); also Valens Anthology III and Paulus
# Alexandrinus ch. 3. Only the five planets receive bounds. Widths sum to 30 in every sign.
EB_PL = ("Saturn", "Jupiter", "Mars", "Venus", "Mercury")
EGY_BOUNDS = [
    [("Jupiter", 6), ("Venus", 6), ("Mercury", 8), ("Mars", 5), ("Saturn", 5)],      # Aries
    [("Venus", 8), ("Mercury", 6), ("Jupiter", 8), ("Saturn", 5), ("Mars", 3)],      # Taurus
    [("Mercury", 6), ("Jupiter", 6), ("Venus", 5), ("Mars", 7), ("Saturn", 6)],      # Gemini
    [("Mars", 7), ("Venus", 6), ("Mercury", 6), ("Jupiter", 7), ("Saturn", 4)],      # Cancer
    [("Jupiter", 6), ("Venus", 5), ("Saturn", 7), ("Mercury", 6), ("Mars", 6)],      # Leo
    [("Mercury", 7), ("Venus", 10), ("Jupiter", 4), ("Mars", 7), ("Saturn", 2)],     # Virgo
    [("Saturn", 6), ("Mercury", 8), ("Jupiter", 7), ("Venus", 7), ("Mars", 2)],      # Libra
    [("Mars", 7), ("Venus", 4), ("Mercury", 8), ("Jupiter", 5), ("Saturn", 6)],      # Scorpio
    [("Jupiter", 12), ("Venus", 5), ("Mercury", 4), ("Saturn", 5), ("Mars", 4)],     # Sagittarius
    [("Mercury", 7), ("Jupiter", 7), ("Venus", 8), ("Saturn", 4), ("Mars", 4)],      # Capricorn
    [("Mercury", 7), ("Venus", 6), ("Jupiter", 7), ("Mars", 5), ("Saturn", 5)],      # Aquarius
    [("Venus", 12), ("Jupiter", 4), ("Mercury", 3), ("Mars", 9), ("Saturn", 2)],     # Pisces
]


def _bound_tables():
    """Per-degree lookups: bound lord index, bound start, bound width. 360 entries."""
    lord = np.empty(360, dtype=int)
    start = np.empty(360)
    width = np.empty(360)
    for s, row in enumerate(EGY_BOUNDS):
        assert sum(w for _, w in row) == 30, f"Egyptian bounds for sign {s} do not sum to 30"
        off = 0.0
        for pl, w in row:
            for d in range(int(off), int(off) + w):
                lord[30 * s + d] = EB_PL.index(pl)
                start[30 * s + d] = 30 * s + off
                width[30 * s + d] = w
            off += w
    return lord, start, width


EB_LORD, EB_START, EB_WIDTH = _bound_tables()


# ── small helpers ───────────────────────────────────────────────────────────────────────────────
def _c(*arrs):
    """Horizontally stack (n,) or (n,k) pieces into one float64 (n, K) block."""
    out = []
    for a in arrs:
        a = np.asarray(a, dtype=np.float64)
        out.append(a[:, None] if a.ndim == 1 else a)
    return np.ascontiguousarray(np.hstack(out), dtype=np.float64)


def _oh(idx, k):
    """One-hot of an integer array, (n,) -> (n, k). Indices are clipped, never wrapped silently."""
    idx = np.clip(np.asarray(idx, dtype=int), 0, k - 1)
    out = np.zeros((idx.shape[0], k))
    out[np.arange(idx.shape[0]), idx] = 1.0
    return out


def _circ(deg):
    r = np.deg2rad(np.asarray(deg, dtype=np.float64))
    return np.stack([np.cos(r), np.sin(r)], axis=-1)


def _phase(days, period):
    """Phase within a period, in degrees 0..360 — the Goal-Year 'where in the cycle are we'."""
    return 360.0 * np.mod(np.asarray(days, dtype=np.float64) / float(period), 1.0)


def _phenom(elong, spd, av, stat):
    """Nine named stations of a planet's synodic cycle, from elongation, side and speed.

    0 invisible near the Sun · 1 morning visibility band (Gamma / Sigma) · 2 morning direct
    3 morning station · 4 morning retrograde · 5 evening retrograde · 6 evening station
    7 evening direct · 8 evening visibility band (Epsilon / Omega)
    """
    e = np.abs(elong)
    eve = elong > 0
    inv = e < av
    st = (~inv) & (np.abs(spd) < stat)
    band = (~inv) & (~st) & (e < av + 8.0)
    rest = (~inv) & (~st) & (~band)
    direct = spd >= 0
    cat = np.zeros(e.shape, dtype=int)
    cat[st & ~eve] = 3
    cat[st & eve] = 6
    cat[band & ~eve] = 1
    cat[band & eve] = 8
    cat[rest & ~eve & direct] = 2
    cat[rest & ~eve & ~direct] = 4
    cat[rest & eve & ~direct] = 5
    cat[rest & eve & direct] = 7
    return cat


def _dodeka_a(lon):
    """Classical twelfth-part: 2;30 degrees each, counted in zodiacal order from the sign's start.

    lon_d = 30*s + 12*(lon - 30*s), reduced mod 360. Equivalent to (12*lon + 30*s) mod 360.
    Neugebauer & Sachs; the technique is shared Babylonian-Egyptian.
    """
    lon = np.mod(np.asarray(lon, dtype=np.float64), 360.0)
    s = np.floor(lon / 30.0)
    return np.mod(12.0 * lon + 30.0 * s, 360.0)


def _dodeka_b(lon):
    """The Kalendertext x13 scheme: lon' = 13*lon (mod 360).

    Brack-Bernsen & Steele, "Babylonian Mathemagics" (2004) — a second, genuinely Babylonian
    twelfth-part-family transformation, kept separate because it scores differently.
    """
    return np.mod(13.0 * np.mod(np.asarray(lon, dtype=np.float64), 360.0), 360.0)


def _egy_civil(jd):
    """Egyptian civil date from JD: day-of-year 0..364, month 0..12 (12 = epagomenal), day 1..30,
    decade-of-year 0..35, day-in-decade 0..9, season 0..3 (3 = epagomenal)."""
    d = np.mod(np.floor(np.asarray(jd, dtype=np.float64) - NAB + 0.5), EGY_YEAR).astype(int)
    month = np.minimum(d // 30, 12)
    day = np.where(d >= 360, d - 360 + 1, d % 30 + 1)
    dec_year = np.minimum(d // 10, 35)
    dec_day = d % 10
    season = np.minimum(d // 120, 3)
    return d, month, day, dec_year, dec_day, season


# ════════════════════════════════════════════════════════════════════════════════════════════════
def build(E):
    n = E.n
    I, S = E.IDX, E.SLOT
    L, LAT, SPD, DEC, HELIO, JD = E.LON, E.LAT, E.SPD, E.DEC, E.HELIO, E.JD
    NS = 6
    OLD, YNG, WED, DAV = S["older"], S["younger"], S["wedding"], S["davison"]
    B = {}

    sun = L[:, I["Sun"], :]                     # (6, n)
    moon = L[:, I["Moon"], :]
    # Earth's heliocentric longitude is the geocentric Sun + 180 (HELIO[Sun] is 0 in core.py)
    earth_h = np.mod(sun + 180.0, 360.0)

    # ── 1. Goal-Year phase of every planet, at every instant ────────────────────────────────────
    # The Babylonian predictive engine: a phenomenon recurs after one Goal-Year period, so a
    # chart's place *within* each period is the whole of what the method knows about it.
    parts = []
    for _, P in GOAL.items():
        for s in range(NS):
            parts.append(_circ(_phase(JD[s] - NAB, P)))
    B["bab: goal-year phase, circular"] = _c(*parts)

    # ── 2. Goal-Year RECURRENCE between the charts — the tradition's own computed test ──────────
    # "To know year Y, read year Y minus one period." Two instants separated by a whole number of
    # Goal-Year periods repeat each other's phenomena; the phase of the interval IS that number.
    parts = []
    for a, b in ((OLD, YNG), (OLD, WED), (YNG, WED), (DAV, WED)):
        dt = JD[b] - JD[a]
        for _, P in GOAL.items():
            ph = E.wrap(_phase(dt, P))
            parts.append(_circ(ph))
            for w in (8.0, 20.0, 40.0):
                parts.append(E.orbkern(ph, 0.0, w))
    B["bab: goal-year recurrence between charts"] = _c(*parts)

    # ── 3. Synodic phase and elongation from the Sun ────────────────────────────────────────────
    # Synodic phase is taken heliocentrically (planet minus Earth), so it sweeps 0..360 once per
    # synodic cycle and is 0 at inferior conjunction (inner) or opposition (outer).
    parts = []
    for pl in PL5:
        b = I[pl]
        for s in range(NS):
            syn = np.mod(HELIO[s, b, :] - earth_h[s], 360.0)
            el = E.wrap(L[s, b, :] - sun[s])
            parts.append(_circ(syn))
            parts.append(_circ(el))
            parts.append(np.abs(el) / 180.0)
            parts.append(SPD[s, b, :])                                # deg/day, signed
            parts.append(SPD[s, b, :] * (SYN[pl] / 360.0))            # in synodic-cycle units
            parts.append((SPD[s, b, :] < 0).astype(float))            # retrograde flag
    B["bab: synodic phase & elongation"] = _c(*parts)

    # ── 4. The named heliacal phenomena, as discrete stations (one-hot) ─────────────────────────
    parts = []
    for pl in PL5:
        b = I[pl]
        for s in range(NS):
            el = E.wrap(L[s, b, :] - sun[s])
            cat = _phenom(el, SPD[s, b, :], AV[pl], STAT[pl])
            parts.append(_oh(cat, 9))
            parts.append((np.abs(el) > 150.0).astype(float))          # acronychal / Theta
            parts.append((np.abs(el) < AV[pl]).astype(float))         # invisible
    B["bab: heliacal phenomena, one-hot"] = _c(*parts)

    # ── 5. The same phenomena as orb kernels at the tradition's own thresholds ──────────────────
    parts = []
    for pl in PL5:
        b = I[pl]
        for s in range(NS):
            el = E.wrap(L[s, b, :] - sun[s])
            ae = np.abs(el)
            sp = SPD[s, b, :]
            syn = np.mod(HELIO[s, b, :] - earth_h[s], 360.0)
            parts.append(E.orbkern(ae, 0.0, 4.0))                     # conjunction with the Sun
            parts.append(E.orbkern(ae, AV[pl], 2.0))                  # first / last visibility
            parts.append(E.orbkern(ae, AV[pl], 6.0))
            parts.append(E.orbkern(ae, 180.0, 10.0))                  # opposition / acronychal
            parts.append(np.exp(-0.5 * (sp / STAT[pl]) ** 2))         # station, tight
            parts.append(np.exp(-0.5 * (sp / (3.0 * STAT[pl])) ** 2)) # station, loose
            parts.append(E.orbkern(ae, MAXEL[pl], 5.0))               # greatest elongation
            for a in (0.0, 90.0, 180.0, 270.0):
                parts.append(E.orbkern(E.wrap(syn - a), 0.0, 20.0))
    B["bab: heliacal phenomena, orb kernels"] = _c(*parts)

    # ── 6. The lunar month by first visibility, and the EAE day of opposition ───────────────────
    # EAE tablets 1-6: the Moon and Sun seen together on the 14th is favourable; the 13th, 15th
    # and 16th are ominous. The day on which opposition falls is therefore a computed omen number.
    parts = []
    for s in range(NS):
        el = np.mod(moon[s] - sun[s], 360.0)
        rel = SPD[s, I["Moon"], :] - SPD[s, I["Sun"], :]
        dom = 1.0 + np.floor(np.mod(el - CRESCENT, 360.0) / (360.0 / SYN_MONTH))
        dopp = np.clip(1.0 + np.floor((180.0 - CRESCENT) / rel), 11, 17)
        parts.append(_circ(el))
        parts.append(_circ(dom * 12.0))
        parts.append(rel / 12.19)
        parts.append((rel > 12.19).astype(float))                     # hollow (29-day) month
        parts.append(dopp / 17.0)
        parts.append(E.orbkern(dopp, 14.0, 1.0))                      # the favourable 14th
        if s in (OLD, YNG, WED):
            parts.append(_oh(dom.astype(int) - 1, 30))
            parts.append(_oh(dopp.astype(int) - 11, 7))
    eo = np.mod(moon[OLD] - sun[OLD], 360.0)
    ey = np.mod(moon[YNG] - sun[YNG], 360.0)
    do = 1.0 + np.floor(np.mod(eo - CRESCENT, 360.0) / (360.0 / SYN_MONTH))
    dy = 1.0 + np.floor(np.mod(ey - CRESCENT, 360.0) / (360.0 / SYN_MONTH))
    parts.append((do == dy).astype(float))
    parts.append(_circ((do - dy) * 12.0))
    B["bab: lunar-visibility month & EAE opposition day"] = _c(*parts)

    # ── 7. Enuma Anu Enlil omen conditions: eclipse, saros, the Moon beside a planet, the paths ─
    parts = []
    for s in range(NS):
        el = np.mod(moon[s] - sun[s], 360.0)
        blat = LAT[s, I["Moon"], :]
        dfull, dnew = E.wrap(el - 180.0), E.wrap(el)
        for w in (6.0, 12.0):
            parts.append(E.orbkern(dfull, 0.0, w) * E.orbkern(blat, 0.0, 1.0))   # lunar eclipse
            parts.append(E.orbkern(dnew, 0.0, w) * E.orbkern(blat, 0.0, 1.2))    # solar eclipse
        parts.append(blat)
        parts.append(np.abs(blat))
        parts.append(_circ(E.wrap(moon[s] - L[s, I["TrueNode"], :])))
        parts.append(_circ(E.wrap(sun[s] - L[s, I["TrueNode"], :])))
        parts.append(_circ(_phase(JD[s] - NAB, SAROS)))
        parts.append(SPD[s, I["Moon"], :] / 13.176)
        # the Moon standing beside / occulting a planet
        for pl in PL5:
            b = I[pl]
            sep = E.sep(moon[s], L[s, b, :])
            for w in (3.0, 6.0, 12.0):
                parts.append(E.orbkern(sep, 0.0, w))
            parts.append(E.orbkern(sep, 0.0, 1.5) *
                         E.orbkern(blat - LAT[s, b, :], 0.0, 0.6))
            parts.append(np.sign(E.wrap(moon[s] - L[s, b, :])))
        # MUL.APIN I: the three paths. Reconstructed as declination bands, middle = path of Anu.
        if s in (OLD, YNG, WED):
            for nm in CL7:
                d = DEC[s, I[nm], :]
                parts.append(_oh((d > 17.0).astype(int) * 2 + (np.abs(d) <= 17.0).astype(int), 3))
            # "in the path of the Moon": inside the Moon's own latitude limit of 5 deg 9 min
            for pl in PL5:
                bl = np.abs(LAT[s, I[pl], :])
                band = np.where(bl <= 1.5, 0, np.where(bl <= 5.15, 1, 2))
                parts.append(_oh(band, 3))
                parts.append(np.sign(LAT[s, I[pl], :]))
    B["bab: EAE eclipse, saros, moon-omens & MUL.APIN paths"] = _c(*parts)

    # ── 8. The two calendars: the schematic 360-day year and the Egyptian wandering 365-day year ─
    parts = []
    for s in range(NS):
        sch = np.mod(JD[s] - NAB, SCHEM_YEAR)
        parts.append(_circ(sch))                                    # 1 day = 1 degree, as in the
        parts.append(_circ((sch % 30.0) * 12.0))                    # System A/B schemes
        if s in (OLD, YNG, WED):
            parts.append(_oh((sch // 30.0).astype(int), 12))
    for s in range(NS):
        d, month, day, dy10, dd10, seas = _egy_civil(JD[s])
        parts.append(_circ(d * (360.0 / EGY_YEAR)))
        parts.append((d >= 360).astype(float))                       # the 5 epagomenal days
        parts.append(_circ(_phase(np.floor((JD[s] - NAB) / EGY_YEAR), SOTHIC_YEARS))) # Sothic
        parts.append(_circ(E.wrap(d * (360.0 / EGY_YEAR) - sun[s]))) # the Nile/seasonal drift
        if s in (OLD, YNG, WED):
            parts.append(_oh(month, 13))
            parts.append(_oh(seas, 4))                               # Akhet / Peret / Shemu / epag
            parts.append(_oh(np.minimum((day - 1) // 10, 2), 3))     # decade within the month
        if s in (OLD, YNG):
            parts.append(_oh(dy10, 36))                              # the 36 ten-day weeks
            parts.append(_oh(dd10, 10))
    do_, mo_, dyo_, d10o_, ddo_, so_ = _egy_civil(JD[OLD])
    dy_, my_, dyy_, d10y_, ddy_, sy_ = _egy_civil(JD[YNG])
    parts.append((mo_ == my_).astype(float))
    parts.append((d10o_ == d10y_).astype(float))
    parts.append((ddo_ == ddy_).astype(float))
    parts.append((so_ == sy_).astype(float))
    parts.append(_circ((do_ - dy_) * (360.0 / EGY_YEAR)))
    parts.append(_circ((d10o_ - d10y_) * 10.0))
    B["bab+egy: schematic 360-day & Egyptian civil calendars"] = _c(*parts)

    # ── 9. The 36 decans, as discrete places ────────────────────────────────────────────────────
    dec = {}      # (slot, body) -> decan index 0..35
    for s in range(NS):
        for nm in CL7:
            dec[(s, nm)] = (np.floor(np.mod(L[s, I[nm], :], 360.0) / 10.0).astype(int)) % 36
    parts = []
    for s in (OLD, YNG):
        for nm in CL7:
            parts.append(_oh(dec[(s, nm)], 36))
    B["egy: 36 decans, one-hot"] = _c(*parts)

    # ── 10. The decan rulers in descending Chaldean order from Mars ─────────────────────────────
    rul = {k: DECAN_RULER[v] for k, v in dec.items()}
    parts = []
    for s in range(NS):
        tally = np.zeros((n, 7))
        for nm in CL7:
            r = rul[(s, nm)]
            parts.append(_oh(r, 7))
            tally += _oh(r, 7)
        parts.append(tally)
        # position inside the decan, circular — the decan is 10 degrees wide
        for nm in CL7:
            parts.append(_circ((np.mod(L[s, I[nm], :], 10.0)) * 36.0))
    B["egy: decan rulers, Chaldean order"] = _c(*parts)

    # ── 11. Decan pair contacts between the partners ────────────────────────────────────────────
    parts = []
    same_d = np.zeros(n)
    same_r = np.zeros(n)
    for a in CL7:
        for b in CL7:
            da, db = dec[(OLD, a)], dec[(YNG, b)]
            eq = (da == db).astype(float)
            eqr = (rul[(OLD, a)] == rul[(YNG, b)]).astype(float)
            parts.append(eq)
            parts.append(eqr)
            parts.append(_circ(E.wrap((da - db) * 10.0)))
            same_d += eq
            same_r += eqr
    parts.append(same_d)
    parts.append(same_r)
    # low-rank encoding of the decan pair for the four bodies a marriage doctrine cares about
    for a in ("Sun", "Moon", "Venus", "Mars"):
        for b in ("Sun", "Moon", "Venus", "Mars"):
            sa, sb = dec[(OLD, a)] * 10.0, dec[(YNG, b)] * 10.0
            for h in (1, 2, 3):
                parts.append(_circ(h * (sa + sb)))
                parts.append(_circ(h * (sa - sb)))
    B["egy: decan-pair contacts"] = _c(*parts)

    # ── 12. The Egyptian bounds (terms) — Ptolemy's "Egyptians'" table, not his own ──────────────
    parts = []
    bl = {}
    for s in range(NS):
        for nm in CL7:
            deg = np.clip(np.floor(np.mod(L[s, I[nm], :], 360.0)).astype(int), 0, 359)
            lord = EB_LORD[deg]
            bl[(s, nm)] = lord
            st, wd = EB_START[deg], EB_WIDTH[deg]
            pos = (np.mod(L[s, I[nm], :], 360.0) - st) / wd
            parts.append(_oh(lord, 5))
            parts.append(pos)
            parts.append(np.minimum(pos, 1.0 - pos))                 # nearness to a bound edge
            parts.append(_circ(pos * 360.0))
    same_b = np.zeros(n)
    for a in CL7:
        for b in CL7:
            eq = (bl[(OLD, a)] == bl[(YNG, b)]).astype(float)
            parts.append(eq)
            same_b += eq
    parts.append(same_b)
    B["egy: Egyptian bounds (terms)"] = _c(*parts)

    # ── 13. The dodekatemoria: both schemes, circular and as signs ──────────────────────────────
    dA, dB = {}, {}
    for s in range(NS):
        for nm in CL7:
            dA[(s, nm)] = _dodeka_a(L[s, I[nm], :])
            dB[(s, nm)] = _dodeka_b(L[s, I[nm], :])
    parts = []
    for s in range(NS):
        for nm in CL7:
            parts.append(_circ(dA[(s, nm)]))
            parts.append(_circ(dB[(s, nm)]))
    for s in (OLD, YNG):
        for nm in CL7:
            parts.append(_oh((dA[(s, nm)] // 30.0).astype(int), 12))
            parts.append(_oh((dB[(s, nm)] // 30.0).astype(int), 12))
    B["bab+egy: dodekatemoria, circular & signs"] = _c(*parts)

    # ── 14. Twelfth-part cross-contacts between the partners ────────────────────────────────────
    # The attested use of a twelfth-part is comparative: a body's dodekatemorion is set beside
    # another body's actual place, or beside another dodekatemorion.
    parts = []
    hits3 = np.zeros(n)
    hits8 = np.zeros(n)
    sameS = np.zeros(n)
    cross = np.zeros(n)
    for a in CL7:
        for b in CL7:
            sep = E.sep(dA[(OLD, a)], dA[(YNG, b)])
            k3, k8 = E.orbkern(sep, 0.0, 3.0), E.orbkern(sep, 0.0, 8.0)
            eq = ((dA[(OLD, a)] // 30.0) == (dA[(YNG, b)] // 30.0)).astype(float)
            s1 = E.orbkern(E.sep(dA[(OLD, a)], L[YNG, I[b], :]), 0.0, 4.0)
            s2 = E.orbkern(E.sep(dA[(YNG, b)], L[OLD, I[a], :]), 0.0, 4.0)
            parts += [k3, k8, eq, s1, s2]
            hits3 += (sep < 3.0).astype(float)
            hits8 += (sep < 8.0).astype(float)
            sameS += eq
            cross += ((s1 > 0.5) | (s2 > 0.5)).astype(float)
    parts += [hits3, hits8, sameS, cross]
    B["bab+egy: twelfth-part cross-contacts"] = _c(*parts)

    for k, v in B.items():
        assert v.shape[0] == n and v.dtype == np.float64, (k, v.shape, v.dtype)
        assert np.isfinite(v).all(), f"{k} is not finite"
    return B


# ════════════════════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import time
    from core import load
    from evalx import quick

    t0 = time.time()
    E = load()
    X = build(E)
    print(f"{TRADITION}\n{len(X)} blocks, built in {time.time()-t0:.1f}s\n")
    total, bad = 0, 0
    for name, M in X.items():
        try:
            assert isinstance(M, np.ndarray), "not an ndarray"
            assert M.ndim == 2 and M.shape[0] == E.n, f"shape {M.shape} != ({E.n}, k)"
            assert M.dtype == np.float64, f"dtype {M.dtype}"
            assert np.isfinite(M).all(), "non-finite values"
            assert M.std(axis=0).max() > 0, "block is all-constant"
        except AssertionError as e:
            print(f"FAIL  {name}: {e}")
            bad += 1
            continue
        total += M.shape[1]
        acc, auc = quick(E, M)
        print(f"  {name:<52} {M.shape[1]:>5} cols   acc {100*acc:5.2f}%   AUC {auc:.4f}")
    print(f"\ntotal columns {total}")
    if bad:
        sys.exit(1)
    print("OK")
