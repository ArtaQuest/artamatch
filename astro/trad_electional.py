"""
trad_electional.py — Western & medieval ELECTIONAL astrology for a marriage.

Every other module in this family reads the two nativities. This one reads THE WEDDING DAY: the chart
of the election itself, its own internal condition, and its agreement with the two nativities and with
the two secondary-progressed charts and the Davison chart. Electional doctrine is a checklist of
conditions on one moment, and almost all of it is about the Moon.

SLOTS USED
  2  the wedding                      — the election. Everything below is centred on it.
  0  older's birth, 1 younger's birth — only as the charts the election must not contradict.
  3  older's secondary progression to the wedding, 4 younger's  — the progressed lights at the date.
  5  the Davison chart                — the relationship's own chart (Davison, "Synastry", 1977).

SOURCES IMPLEMENTED (each rule is cited again at the line that computes it)
  Ptolemy, Tetrabiblos I.13 (the five configurations), I.17/I.19/I.21 (domiciles, exaltations, the
    bounds "according to the Egyptians"), IV.5 (Of Marriage — Venus for a man, Mars for a woman, and
    the seventh place).
  Dorotheus of Sidon, Carmen Astrologicum, the katarchic material (what the Moon must be doing when a
    thing is begun, and that the benefics must be well placed).
  Sahl ibn Bishr, Introductorium and The Fifty Judgements (the Moon increasing in light, swift in
    course, free of the malefics, applying to a benefic; reception, and that reception without an
    aspect is not reception).
  Guido Bonatti, Liber Astronomiae Tr. 5 (the 146 Considerations — the Moon void of course, the Moon
    in the via combusta, the Moon in the last degrees of a sign, joining a retrograde planet, the
    malefics on the significators) and his treatise on Elections (marriage, and that an election may
    not contradict the nativity).
  William Lilly, Christian Astrology, Book I: the Table of Essential Dignities, and the
    "Considerations before Judgement" (combustion 8.5 deg, under the Sun's beams 17 deg, cazimi 17
    arcmin, the via combusta from 15 Libra to 15 Scorpio, the Moon void of course); and, on
    elections: fortify the seventh and its lord, the Moon increasing and unafflicted, and the lords
    of the first and the seventh in a soft aspect with reception.
  Modern electional practice, for the additions the classical authors could not have: Mercury's
    retrograde SHADOW periods either side of the two stations (Erin Sullivan, Retrograde Planets),
    the outer planets and Chiron on the wedding luminaries, aspect-pattern density, Rudhyar's
    progressed lunation cycle (The Lunation Cycle, 1967), and the Davison relationship chart.

THE PROXIES, STATED PLAINLY — all three are forced by the data, none is a choice
  1. NO TIME OF DAY ANYWHERE, so NO ASCENDANT and NO HOUSES. Only dates are known and every instant
     is cast for 12:00 UT. An election is normally chosen BY its Ascendant, so the single most
     important electional quantity is simply absent. Two documented zodiacal proxies stand in for
     the first and seventh places, and both are emitted because they disagree:
       "solar-sign"  Asc := 0 deg of the Sun's sign, 7th := the opposite sign. This is the proxy the
                     project contract sanctions (the Sun's sign treated as the first place).
       "noon-MC"     every instant IS 12:00 UT, i.e. local noon on the Greenwich meridian, so under
                     the ordinary noon-chart convention the Sun culminates: MC := Sun, Asc := Sun+90,
                     and the seventh cusp := Sun+270. Obliquity and latitude are ignored because
                     there is no latitude to use.
     Everything in the seventh-place block is therefore a PROXY, labelled as one in its block name.
     The planetary hour and the hour-lord (a real electional requirement) are NOT implemented at all:
     they need the true clock time and the sunrise of the place, and no proxy for them is honest.
  2. THE MOON IS UNCERTAIN BY ABOUT +-6 DEG at a birth (noon versus the true moment), and by the same
     amount at the wedding. The Moon is the heart of every election, so this limit bites hardest
     exactly here: the wedding Moon's SIGN is roughly half reliable, its void-of-course state and its
     next application are computed exactly under linear motion but from a longitude that may be six
     degrees wrong, and the tightness of any lunar orb inherits that error. Built anyway — the
     doctrine is unusable without the Moon — but no lunar orb below should be read as precise.
  3. SECT IS UNDECIDABLE (it needs the Sun above or below the horizon). Every dignity that depends on
     sect is computed TWICE, by the day table and by the night table, and both are emitted. The
     noon-chart convention of proxy 2 would make every chart diurnal, which would hide the doctrine
     rather than model it.

APPLYING VERSUS SEPARATING, which is the whole of electional judgement
  A classical aspect is not a state but a direction: an APPLYING square from Mars is the affliction,
  a SEPARATING one is spent. E.SPD carries the longitude speed of every body at every instant, so
  the direction is computable exactly. For bodies A and B and an aspect angle a, with
  d = wrap(lonA - lonB), r = |d| and o = r - a, the orb closes at do/dt = sign(d) * (spdA - spdB);
  the contact is applying when o and do/dt have opposite signs. Every aspect kernel in this module is
  emitted BOTH as a plain magnitude and as that magnitude SIGNED +applying / -separating, because a
  linear model cannot recover one from the other (signed alone cannot say "an aspect is present"; the
  magnitude alone cannot say which way it points). For a transit to a natal chart only the transiting
  body moves, so spd_natal := 0 — the standard convention.

VOID OF COURSE, COMPUTED THE WAY LILLY DEFINES IT
  "The Moon is void of course when she is not applying to any planet" — and, as every author means
  it, before she leaves the sign she is in. That is a prediction, not a state, so it is computed as
  one: the relative longitude of the Moon against each planet is advanced under linear motion until
  each of the five configurations next perfects, and the Moon is void when none of them perfects
  inside her remaining arc. Checked against a fine Swiss-Ephemeris scan on a random sample of 80
  weddings: the predicted degrees of the Moon's own travel to her next perfection are correct to a
  mean of 0.003 deg and a maximum of 0.10 deg, and the void verdict agrees on 79 of 80 (the one
  disagreement sits a tenth of a degree from a sign boundary). The rate this yields on the dataset,
  21.6 per cent of weddings, is simply what the definition gives for six planets and five aspects —
  it is not a tuned threshold. Two looser readings are emitted beside it, and the version that
  ignores the Sun, because authors differ on whether the Sun ends a void course.

TWO SWISS-EPHEMERIS SEARCHES, both over the wedding span only, both cached in-process
  * the eclipse catalogue, from swe.sol_eclipse_when_glob / swe.lun_eclipse_when, so that "how far is
    this wedding from an eclipse" is the real answer and not an ecliptic-limit estimate;
  * Mercury's station catalogue, from a four-day scan for a sign change in its longitude speed
    refined by linear interpolation, because the shadow periods are defined by the LONGITUDES of the
    two stations and cannot be had from the wedding-day ephemeris alone.
  Nothing is written to disk and no network is touched.

NOT IMPLEMENTED, and why
  * the Ascendant, the twelve houses, angularity, the hour-lord and the planetary hour, the Moon in
    the sixth/eighth/twelfth (Bonatti's commonest prohibition), the lord of the seventh as a real
    house lord — all need a time and a place (proxy 1).
  * eclipse MAGNITUDE and local visibility: swisseph gives those per geographic location, and there
    is no wedding place. Only the eclipse TYPE flags (total / annular / partial / hybrid / central,
    and total / partial / penumbral) and the distance in days are used.
  * the fixed stars: the sibling harmonics module already precesses a rigorous star catalogue, so
    repeating a coarser one here would only add noise.
  * primary directions, profections, and firdaria — they start from the Ascendant or from a timed
    nativity.
"""

import os
import numpy as np
import swisseph as swe

# core sets this on import, but this module may be imported first; setting a path does no I/O.
swe.set_ephe_path(os.path.expanduser("~/.sweph/ephe"))
FLG = swe.FLG_SWIEPH | swe.FLG_SPEED

TRADITION = ("Western & medieval electional astrology for marriage "
             "(Dorotheus, Sahl, Bonatti, Lilly, and modern electional practice)")

# ── body indices, identical to core's ordering, so these index E.LON[slot] directly ──────────────
SUN, MOON, MER, VEN, MAR, JUP, SAT, URA, NEP, PLU, TNODE, MNODE, LIL, CHI, CER, PAL, JUN, VES = range(18)
CLASSIC = [SUN, MOON, MER, VEN, MAR, JUP, SAT]          # the seven of every pre-telescopic election
MODERN10 = [SUN, MOON, MER, VEN, MAR, JUP, SAT, URA, NEP, PLU]
BENEFIC = (VEN, JUP)
MALEFIC = (MAR, SAT)
LIGHTS = (SUN, MOON)

# ── the essential dignities: Lilly's Table of Essential Dignities (Ptolemy I.17, I.19, I.21) ─────
# Planet codes below are 0..6 = Sun Moon Mercury Venus Mars Jupiter Saturn, i.e. the same integers
# as the body indices above, so a table lookup is also a row index into E.LON[slot].
DOM = np.array([MAR, VEN, MER, MOON, SUN, MER, VEN, MAR, JUP, SAT, SAT, JUP])   # Aries..Pisces
DETRI = DOM[(np.arange(12) + 6) % 12]                                            # ruler of the opposite sign
EX_SIGN = np.array([0, 1, 5, 11, 9, 3, 6])        # Sun 19 Ari, Moon 3 Tau, Mercury 15 Vir,
EX_DEG = np.array([19., 3., 15., 27., 28., 15., 21.])   # Venus 27 Pis, Mars 28 Cap, Jup 15 Can, Sat 21 Lib
EXALT_OF = np.full(12, -1, dtype=np.int64)
FALL_OF = np.full(12, -1, dtype=np.int64)
for _p, _s in enumerate(EX_SIGN):
    EXALT_OF[_s] = _p
    FALL_OF[(_s + 6) % 12] = _p
# Triplicity lords by sect, the Dorothean table Lilly prints with a participating lord:
#   fire day Sun / night Jupiter / part. Saturn ; earth day Venus / night Moon / part. Mars
#   air  day Saturn / night Mercury / part. Jupiter ; water day Venus / night Mars / part. Moon
# A sign's element is sign % 4 (0 fire, 1 earth, 2 air, 3 water), so the row repeats every four signs.
TRIP_D = np.array([SUN, VEN, SAT, VEN] * 3)
TRIP_N = np.array([JUP, MOON, MER, MAR] * 3)
TRIP_P = np.array([SAT, MAR, JUP, MOON] * 3)
# The bounds / terms "according to the Egyptians" — Ptolemy I.21, and Lilly's table of terms.
EGYPT = [
    [(JUP, 6), (VEN, 6), (MER, 8), (MAR, 5), (SAT, 5)],    # Aries
    [(VEN, 8), (MER, 6), (JUP, 8), (SAT, 5), (MAR, 3)],    # Taurus
    [(MER, 6), (JUP, 6), (VEN, 5), (MAR, 7), (SAT, 6)],    # Gemini
    [(MAR, 7), (VEN, 6), (MER, 6), (JUP, 7), (SAT, 4)],    # Cancer
    [(JUP, 6), (VEN, 5), (SAT, 7), (MER, 6), (MAR, 6)],    # Leo
    [(MER, 7), (VEN, 10), (JUP, 4), (MAR, 7), (SAT, 2)],   # Virgo
    [(SAT, 6), (MER, 8), (JUP, 7), (VEN, 7), (MAR, 2)],    # Libra
    [(MAR, 7), (VEN, 4), (MER, 8), (JUP, 5), (SAT, 6)],    # Scorpio
    [(JUP, 12), (VEN, 5), (MER, 4), (SAT, 5), (MAR, 4)],   # Sagittarius
    [(MER, 7), (JUP, 7), (VEN, 8), (SAT, 4), (MAR, 4)],    # Capricorn
    [(MER, 7), (VEN, 6), (JUP, 7), (MAR, 5), (SAT, 5)],    # Aquarius
    [(VEN, 12), (JUP, 4), (MER, 3), (MAR, 9), (SAT, 2)],   # Pisces
]
BOUND = np.zeros((12, 30), dtype=np.int64)
for _s, _row in enumerate(EGYPT):
    assert sum(l for _, l in _row) == 30, "an Egyptian bound row must fill its sign"
    _d = 0
    for _pl, _len in _row:
        BOUND[_s, _d:_d + _len] = _pl
        _d += _len
# Faces (decans) in the Chaldean order, Mars first at 0 Aries — Lilly's face table.
CHALD = np.array([MAR, SUN, VEN, MER, MOON, SAT, JUP])
FACE = np.array([[CHALD[(3 * s + d) % 7] for d in range(3)] for s in range(12)])

# ── the five Ptolemaic configurations (Tetrabiblos I.13) and the hard subset ─────────────────────
ASPECTS = (0.0, 60.0, 90.0, 120.0, 180.0)
HARD = (0.0, 90.0, 180.0)                 # conjunction, square, opposition — the afflicting contacts
HARD8 = (45.0, 135.0)                     # the octile pair, a later (Kepler/modern) addition
SOFT = (60.0, 120.0)

# Mean daily motions, for "swift or slow in course" (Bonatti Tr. 5: the Moon swift in course).
MEAN_SPD = {SUN: 0.9856, MOON: 13.1764, MER: 1.3833, VEN: 1.6021, MAR: 0.5240,
            JUP: 0.0831, SAT: 0.0335, URA: 0.0117, NEP: 0.0060, PLU: 0.0040, CHI: 0.0198,
            LIL: 0.1114, JUN: 0.2262}          # 360 deg over E.PERIOD, in degrees per day

# The via combusta, Lilly (Considerations before Judgement): from 15 Libra to 15 Scorpio.
VIA_LO, VIA_HI = 195.0, 225.0
# A second reading found in the tradition, the burnt way measured from the stars themselves,
# roughly 13 Libra to 9 Scorpio. Emitted alongside so the choice of band is itself a feature.
VIA2_LO, VIA2_HI = 193.0, 219.0

MOON_MEAN = 13.1764
SYN_MER = 115.8775                        # Mercury's synodic period, days


# ════════════════════════════════════════════════════════════════════════════════════════════════
# small numeric helpers
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _wrap(d):
    return (np.asarray(d, dtype=np.float64) + 180.0) % 360.0 - 180.0


def _sep(a, b):
    return np.abs(_wrap(np.asarray(a, float) - np.asarray(b, float)))


def _sign(lon):
    return np.mod(np.floor(np.asarray(lon, float) / 30.0), 12).astype(np.int64)


def _deg(lon):
    return np.mod(np.asarray(lon, float), 30.0)


def _fin(X):
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[:, None]
    return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


def _prune(X):
    """Drop columns that never vary. Uses the design matrix only — never the target."""
    X = _fin(X)
    keep = X.std(axis=0) > 1e-12
    return np.ascontiguousarray(X[:, keep] if keep.any() else X[:, :1], dtype=np.float64)


def _c(*parts):
    """Column-stack (n,) or (n,k) pieces into one finite block, constants dropped."""
    return _prune(np.hstack([_fin(a) for a in parts]))


def _onehot(idx, k):
    """(m, n) integer codes -> (n, m*k) one-hot, the m groups concatenated in order."""
    flat = np.asarray(idx).reshape(-1, np.asarray(idx).shape[-1]).astype(np.int64)
    m, n = flat.shape
    out = np.zeros((n, m * k))
    rows = np.arange(n)
    for j in range(m):
        out[rows, j * k + np.clip(flat[j], 0, k - 1)] = 1.0
    return out


def _circ(lon):
    r = np.deg2rad(np.asarray(lon, float))
    return np.stack([np.cos(r), np.sin(r)], axis=-1)


def _in_band(lon, lo, hi):
    """Membership of a zodiacal band [lo, hi) that does not wrap past 360."""
    x = np.mod(np.asarray(lon, float), 360.0)
    return ((x >= lo) & (x < hi)).astype(np.float64)


def _band_dist(lon, lo, hi):
    """Angular distance to the nearest edge of a band, 0 inside it."""
    x = np.mod(np.asarray(lon, float), 360.0)
    d = np.minimum(np.abs(_wrap(x - lo)), np.abs(_wrap(x - hi)))
    return np.where(_in_band(x, lo, hi) > 0, 0.0, d)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# applying / separating — the mechanism the whole module turns on
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _contact(lonA, spdA, lonB, spdB, angle, width):
    """One aspect contact. Returns (magnitude, signed, orb_offset, closing_rate).

    magnitude    Gaussian orb kernel, 1 at exact perfection.
    signed       the same value, positive when APPLYING and negative when SEPARATING.
    orb_offset   o = |wrap(lonA-lonB)| - angle, i.e. signed degrees from perfection.
    closing_rate do/dt in degrees per day; negative means the bodies are closing on the aspect from
                 outside it. For a transit to a natal chart pass spdB = 0.

    Sahl and Bonatti judge by application, not by presence: a separating square from Mars is spent
    while an applying one is the affliction. E.SPD makes the distinction exact.
    """
    d = _wrap(np.asarray(lonA, float) - np.asarray(lonB, float))
    r = np.abs(d)
    sgn = np.where(d >= 0, 1.0, -1.0)
    drdt = sgn * (np.asarray(spdA, float) - np.asarray(spdB, float))
    o = r - angle
    app = np.where(o * drdt <= 0.0, 1.0, -1.0)          # exact (o == 0) counts as applying
    k = np.exp(-0.5 * (o / width) ** 2)
    return k, k * app, o, drdt


def _days_to_perfect(o, drdt, cap=45.0):
    """Days until an applying contact perfects; `cap` when separating or effectively stationary."""
    safe = np.where(np.abs(drdt) < 1e-8, 1e-8, drdt)
    t = -o / safe
    return np.clip(np.where((t > 0) & (t < cap), t, cap), 0.0, cap)


def _grid(LA, VA, LB, VB, rowsA, rowsB, angles, widths, natal=False):
    """Every rowsA x rowsB x angle x width contact as two (n, K) blocks: magnitudes and signed.

    `natal=True` freezes the B side (a transit: only the transiting body moves).
    """
    mag, sgn = [], []
    for a in rowsA:
        for b in rowsB:
            vb = np.zeros_like(LB[b]) if natal else VB[b]
            for ang in angles:
                for w in widths:
                    k, s, _, _ = _contact(LA[a], VA[a], LB[b], vb, ang, w)
                    mag.append(k)
                    sgn.append(s)
    return np.stack(mag, axis=1), np.stack(sgn, axis=1)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# essential dignity
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _lords(lon):
    """The dignity lords at a longitude: domicile, exaltation, both triplicities, bound, face."""
    s = _sign(lon)
    d = _deg(lon)
    di = np.clip(np.floor(d).astype(np.int64), 0, 29)
    return {"dom": DOM[s], "exa": EXALT_OF[s], "trd": TRIP_D[s], "trn": TRIP_N[s],
            "trp": TRIP_P[s], "bnd": BOUND[s, di],
            "fac": FACE[s, np.clip((d / 10.0).astype(np.int64), 0, 2)], "sign": s, "deg": d}


def _points(lon, night):
    """Five-fold dignity POINTS of every classical planet at longitude `lon` -> (7, n).

    domicile 5, exaltation 4, triplicity 3, bound 2, face 1 — the medieval weighting of the
    Hellenistic dignities that Lilly's dignity table prints, and from which the almuten is its argmax.
    """
    L = _lords(lon)
    tri = L["trn"] if night else L["trd"]
    pts = np.zeros((7, np.asarray(lon).shape[-1]))
    for p in range(7):
        pts[p] = (5.0 * (L["dom"] == p) + 4.0 * (L["sign"] == EX_SIGN[p]) + 3.0 * (tri == p)
                  + 2.0 * (L["bnd"] == p) + 1.0 * (L["fac"] == p))
    return pts


def _self_points(L7, night):
    """(7, n) dignity points of each classical planet at its OWN position in one chart."""
    out = np.zeros((7, L7.shape[-1]))
    for p in range(7):
        out[p] = _points(L7[p], night)[p]
    return out


def _dig_flags(lon, p):
    """The dignity/debility STATE of planet `p` standing at `lon`, as eight flags."""
    L = _lords(lon)
    s = L["sign"]
    dom = (L["dom"] == p).astype(float)
    exa = (s == EX_SIGN[p]).astype(float)
    det = (DETRI[s] == p).astype(float)
    fal = (FALL_OF[s] == p).astype(float)
    trd = (L["trd"] == p).astype(float)
    trn = (L["trn"] == p).astype(float)
    bnd = (L["bnd"] == p).astype(float)
    fac = (L["fac"] == p).astype(float)
    per = ((dom + exa + trd + trn + bnd + fac) == 0).astype(float)     # peregrine: no dignity at all
    return np.stack([dom, exa, det, fal, trd, trn, bnd, fac, per], axis=1)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# the Moon's next application, and void of course
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _travel_to_aspect(lonM, spdM, lonP, spdP, angles):
    """Degrees of the MOON's own travel until each aspect with P next perfects -> (len(angles), n).

    Linear motion in both bodies. The relative longitude u = lonM - lonP moves at spdM - spdP, which
    for the Moon against any planet is always positive and never smaller than about 9 deg/day, so a
    perfection inside the Moon's remaining two-and-a-half degrees-per-hour sign is well inside the
    range where linear motion is a fair approximation. This is the computation Lilly's void-of-course
    rule actually asks for: will she complete an aspect BEFORE she leaves her sign.
    """
    u = np.mod(np.asarray(lonM, float) - np.asarray(lonP, float), 360.0)
    vrel = np.asarray(spdM, float) - np.asarray(spdP, float)
    out = []
    for a in angles:
        targets = (a,) if a in (0.0, 180.0) else (a, 360.0 - a)
        fwd = np.min(np.stack([np.mod(t - u, 360.0) for t in targets]), axis=0)
        bwd = np.min(np.stack([np.mod(u - t, 360.0) for t in targets]), axis=0)
        du = np.where(vrel >= 0, fwd, bwd)
        days = du / np.maximum(np.abs(vrel), 1e-6)
        out.append(days * np.abs(np.asarray(spdM, float)))
    return np.stack(out)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# the two Swiss-Ephemeris searches, both memoised for the life of the process
# ════════════════════════════════════════════════════════════════════════════════════════════════
_ECL = {}


def _eclipses(jd_lo, jd_hi):
    """Every global solar and lunar eclipse in the window, with its type flags and its DEGREE.

    swe.sol_eclipse_when_glob / swe.lun_eclipse_when answer for the whole Earth, which is the right
    question here: there is no wedding place, so a locally visible eclipse cannot be distinguished
    from one that is not. The degree stored is the Sun's longitude at a solar eclipse and the Moon's
    at a lunar one — that is the "eclipse degree" the tradition watches for on a significator.
    """
    key = (round(jd_lo), round(jd_hi))
    if key in _ECL:
        return _ECL[key]
    sj, sf, sl, lj, lf, ll = [], [], [], [], [], []
    t = jd_lo
    while t < jd_hi:
        r, tret = swe.sol_eclipse_when_glob(t, swe.FLG_SWIEPH, 0, False)
        if tret[0] <= t:
            break
        sj.append(tret[0]); sf.append(r)
        sl.append(swe.calc_ut(tret[0], swe.SUN, swe.FLG_SWIEPH)[0][0])
        t = tret[0] + 2.0
    t = jd_lo
    while t < jd_hi:
        r, tret = swe.lun_eclipse_when(t, swe.FLG_SWIEPH, 0, False)
        if tret[0] <= t:
            break
        lj.append(tret[0]); lf.append(r)
        ll.append(swe.calc_ut(tret[0], swe.MOON, swe.FLG_SWIEPH)[0][0])
        t = tret[0] + 2.0
    out = (np.array(sj), np.array(sf, dtype=np.int64), np.array(sl),
           np.array(lj), np.array(lf, dtype=np.int64), np.array(ll))
    _ECL[key] = out
    return out


_STA = {}


def _mercury_stations(jd_lo, jd_hi):
    """Mercury's stations in the window: (jd, longitude, +1 direct / -1 retrograde).

    Found by scanning the longitude speed on a four-day grid for a sign change and refining that
    bracket by linear interpolation of the speed, then one call for the longitude at the station.
    Four days is safe: a Mercury retrogradation lasts about three weeks, so no interval is missed.
    The refinement is good to a few hours, far finer than the one-day granularity of the dataset.
    The STATION LONGITUDES are what the shadow periods are defined by, and they cannot be recovered
    from the wedding day's ephemeris alone — hence the search.
    """
    key = (round(jd_lo), round(jd_hi))
    if key in _STA:
        return _STA[key]
    g = np.arange(np.floor(jd_lo), np.ceil(jd_hi) + 4.0, 4.0)
    spd = np.array([swe.calc_ut(float(t), swe.MERCURY, FLG)[0][3] for t in g])
    i = np.where(np.sign(spd[:-1]) != np.sign(spd[1:]))[0]
    frac = spd[i] / (spd[i] - spd[i + 1])
    tst = g[i] + frac * 4.0
    lon = np.array([swe.calc_ut(float(t), swe.MERCURY, swe.FLG_SWIEPH)[0][0] for t in tst])
    direc = np.where(spd[i] < 0.0, 1.0, -1.0)      # negative then positive = a station DIRECT
    out = (tst, lon, direc)
    _STA[key] = out
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
# the build
# ════════════════════════════════════════════════════════════════════════════════════════════════
def build(E):
    n = E.n
    iW, iO, iY, iPO, iPY, iDA = 2, 0, 1, 3, 4, 5
    LW, VW, BW, DW = E.LON[iW], E.SPD[iW], E.LAT[iW], E.DEC[iW]
    LO, LY = E.LON[iO], E.LON[iY]
    LPO, VPO, LPY, VPY = E.LON[iPO], E.SPD[iPO], E.LON[iPY], E.SPD[iPY]
    LDA, VDA = E.LON[iDA], E.SPD[iDA]
    ar = np.arange(n)
    out = {}

    # everything the Moon block and half the flag block need
    elong = np.mod(LW[MOON] - LW[SUN], 360.0)          # the Moon's elongation, 0 at the new Moon
    waxing = (elong < 180.0).astype(float)
    mspd = VW[MOON]
    mlat = BW[MOON]
    F = _wrap(LW[MOON] - LW[TNODE])                    # argument of latitude from the true node
    via = _in_band(LW[MOON], VIA_LO, VIA_HI)
    msign = _sign(LW[MOON])
    mdeg = _deg(LW[MOON])
    sign_left = 30.0 - mdeg                            # degrees of the Moon's own travel left in sign

    # the Moon's travel to every next perfection, once, reused by three blocks
    OTHERS = [SUN, MER, VEN, MAR, JUP, SAT]
    TRAV = np.stack([_travel_to_aspect(LW[MOON], mspd, LW[p], VW[p], ASPECTS) for p in OTHERS])
    flat = TRAV.reshape(-1, n)                         # (6*5, n)
    jbest = np.argmin(flat, axis=0)
    trav_best = flat[jbest, ar]
    next_pl = jbest // len(ASPECTS)                    # index into OTHERS
    next_as = jbest % len(ASPECTS)
    next_body = np.array(OTHERS)[next_pl]
    # the same excluding the Sun, because authors differ on whether the Sun ends a void course
    flat_ns = TRAV[1:].reshape(-1, n)
    trav_ns = flat_ns.min(axis=0)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 1. the Moon's condition at the wedding — the heart of every election
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # Sahl, Introductorium: the Moon increasing in light, swift in course, in northern and increasing
    # latitude, free of the malefics, not void, not burnt, applying to a benefic. Bonatti Tr. 5
    # repeats every one of these as a separate Consideration, and Lilly's Considerations before
    # Judgement give the numbers.
    C = []
    C.append(elong / 360.0)
    C.append(_circ(elong))
    C.append(_circ(2.0 * elong))
    C.append((1.0 - np.cos(np.deg2rad(elong))) / 2.0)          # illuminated fraction
    C.append(waxing)
    C.append(_onehot(np.floor(elong / 45.0).astype(np.int64)[None, :], 8))    # the eight phases
    C.append(_onehot(np.floor(elong / 90.0).astype(np.int64)[None, :], 4))    # the four quarters
    # burnt, under the beams, and the opposite extreme (Lilly; the Moon combust is the
    # single commonest electional prohibition)
    el2 = np.minimum(elong, 360.0 - elong)
    C.append(np.stack([(el2 < 8.5).astype(float), (el2 < 17.0).astype(float),
                       (el2 < 12.0).astype(float), (el2 < 30.0).astype(float),
                       (np.abs(elong - 180.0) < 12.0).astype(float),
                       (elong > 168.0).astype(float)], axis=1))
    C.append(el2 / 180.0)
    C.append(np.exp(-el2 / 6.0))
    # swift or slow in course (Bonatti Tr. 5): against the Moon's mean motion of 13.176 deg/day
    C.append(np.stack([mspd / MOON_MEAN, (mspd - MOON_MEAN) / MOON_MEAN,
                       (mspd > MOON_MEAN).astype(float), (mspd > 14.0).astype(float),
                       (mspd < 12.5).astype(float), (mspd - 13.1764)], axis=1))
    # latitude: north or south, and increasing or decreasing. There is no latitude SPEED in the
    # table, but lat ~ 5.145 deg * sin(F) with F the argument of latitude, so the latitude is
    # increasing exactly when cos(F) > 0 — an exact consequence, not an approximation of doctrine.
    C.append(np.stack([mlat / 5.2, np.abs(mlat) / 5.2, (mlat > 0).astype(float),
                       (np.cos(np.deg2rad(F)) > 0).astype(float),
                       ((mlat > 0) & (np.cos(np.deg2rad(F)) > 0)).astype(float)], axis=1))
    C.append(_circ(F))
    C.append(np.abs(_wrap(F)) / 180.0)
    # the via combusta, both readings, plus the soft distance to the band
    C.append(np.stack([via, _in_band(LW[MOON], VIA2_LO, VIA2_HI),
                       _band_dist(LW[MOON], VIA_LO, VIA_HI) / 90.0,
                       np.exp(-_band_dist(LW[MOON], VIA_LO, VIA_HI) / 10.0)], axis=1))
    # sign, modality, element, and the degrees at either end of the sign (Bonatti: the Moon in the
    # last degrees of a sign brings nothing to completion)
    C.append(_onehot(msign[None, :], 12))
    C.append(_onehot(np.mod(msign, 3)[None, :], 3))
    C.append(_onehot(np.mod(msign, 4)[None, :], 4))
    C.append(np.stack([mdeg / 30.0, sign_left / 30.0, (sign_left < 3.0).astype(float),
                       (mdeg >= 29.0).astype(float), (mdeg < 1.0).astype(float)], axis=1))
    # the Moon's own dignity, and her fall in Scorpio / detriment in Capricorn
    C.append(_dig_flags(LW[MOON], MOON))
    C.append(_points(LW[MOON], False)[MOON])
    C.append(_points(LW[MOON], True)[MOON])
    C.append(np.exp(-0.5 * (_sep(LW[MOON], 30.0 + EX_DEG[MOON]) / 3.0) ** 2))   # partile exaltation
    # the nodes: the Moon with the Dragon's head or tail (Bonatti Tr. 5)
    C.append(np.stack([np.exp(-0.5 * (_sep(LW[MOON], LW[TNODE]) / w) ** 2) for w in (3.0, 8.0)]
                      + [np.exp(-0.5 * (_sep(LW[MOON], LW[TNODE] + 180.0) / w) ** 2) for w in (3.0, 8.0)],
                      axis=1))
    # void of course, three readings of the same rule
    voc = (trav_best > sign_left).astype(float)
    voc_ns = (trav_ns > sign_left).astype(float)
    C.append(np.stack([voc, voc_ns,
                       (trav_best > 6.0).astype(float),        # the loose modern reading: no
                       (trav_best > 3.0).astype(float),        # applying aspect within orb at all
                       trav_best / 30.0, trav_ns / 30.0,
                       np.exp(-trav_best / 3.0), np.exp(-trav_best / 8.0),
                       trav_best / np.maximum(sign_left, 0.25)], axis=1))
    # the next application: to whom, by what, and how tight
    C.append(_onehot(next_body[None, :], 7))
    C.append(_onehot(next_as[None, :], 5))
    ben_next = np.isin(next_body, BENEFIC).astype(float)
    mal_next = np.isin(next_body, MALEFIC).astype(float)
    C.append(np.stack([ben_next, mal_next, ben_next - mal_next,
                       ben_next * np.exp(-trav_best / 6.0), mal_next * np.exp(-trav_best / 6.0),
                       np.isin(next_as, (1, 3)).astype(float),     # a soft next aspect
                       np.isin(next_as, (0, 2, 4)).astype(float)], axis=1))
    # travel to each planet and each aspect separately: the tightness of every application
    C.append(np.exp(-TRAV.reshape(-1, n).T / 6.0))
    C.append(np.minimum(TRAV.reshape(-1, n).T, 30.0) / 30.0)
    # besieged between the two malefics, and the same with a benefic allowed to intervene
    dM, dS = _wrap(LW[MAR] - LW[MOON]), _wrap(LW[SAT] - LW[MOON])
    bes = ((np.sign(dM) != np.sign(dS)) & (np.abs(dM) < 30.0) & (np.abs(dS) < 30.0)).astype(float)
    # ... and the same with a benefic allowed to break the siege by standing inside the enclosing arc
    saved = np.zeros(n)
    for b in BENEFIC:
        db = _wrap(LW[b] - LW[MOON])
        for side in (dM, dS):
            saved = np.maximum(saved, ((np.sign(db) == np.sign(side))
                                      & (np.abs(db) < np.abs(side))).astype(float))
    C.append(np.stack([bes, bes * (1.0 - saved), saved], axis=1))
    out["elec: moon condition at the election"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 2. the Moon's aspects, APPLYING and SEPARATING kept apart
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # The same doctrine as block 1's "next application", but as continuous orb kernels at three orbs,
    # each emitted twice: once as a magnitude and once signed by direction. Three orbs because the orb
    # is itself a tradition parameter — Lilly gives the Moon a moiety of 6 deg, Bonatti judges by
    # partile contact, and the modern literature allows more.
    partners = [SUN, MER, VEN, MAR, JUP, SAT, URA, NEP, PLU, CHI]
    mag, sgn = _grid(LW, VW, LW, VW, [MOON], partners, ASPECTS, (2.0, 5.0, 9.0))
    C = [mag, sgn]
    dtp = []
    for p in partners:
        for ang in ASPECTS:
            _, _, o, dr = _contact(LW[MOON], mspd, LW[p], VW[p], ang, 6.0)
            dtp.append(_days_to_perfect(o, dr) / 45.0)
            dtp.append(np.sign(o))
    C.append(np.stack(dtp, axis=1))
    # the tradition's own tallies: how much benefic and how much malefic light the Moon receives, and
    # whether the strongest contact she has is applying or separating
    for w in (3.0, 6.0):
        pos = np.zeros(n); neg = np.zeros(n); posa = np.zeros(n); nega = np.zeros(n)
        for p, sign_of in ((VEN, 1), (JUP, 1), (MAR, -1), (SAT, -1)):
            for ang in ASPECTS:
                k, s, _, _ = _contact(LW[MOON], mspd, LW[p], VW[p], ang, w)
                soft = ang in SOFT      # a malefic's trine or sextile hurts half as much as its
                if sign_of > 0:         # conjunction, square or opposition (Lilly, Bonatti)
                    pos += k; posa += np.maximum(s, 0.0)
                else:
                    neg += k * (1.0 if not soft else 0.5)
                    nega += np.maximum(s, 0.0) * (1.0 if not soft else 0.5)
        C.append(np.stack([pos, neg, pos - neg, posa, nega, posa - nega,
                           pos / np.maximum(pos + neg, 1e-6)], axis=1))
    out["elec: moon applying vs separating orbs"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 3. the benefics: Venus and Jupiter must be strong and unafflicted
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # Dorotheus V and Sahl both make a strong, direct, unburnt Venus the first requirement of a
    # marriage election, with Jupiter as the general benefic of contracts. Every debility Lilly lists
    # is emitted as its own flag as well as folded into the five-fold point score.
    C = []
    for p in (VEN, JUP):
        C.append(_dig_flags(LW[p], p))
        C.append(_points(LW[p], False)[p])
        C.append(_points(LW[p], True)[p])
        C.append(_onehot(_sign(LW[p])[None, :], 12))
        el = _wrap(LW[p] - LW[SUN])
        ael = np.abs(el)
        sp = VW[p]
        C.append(np.stack([
            (sp < 0).astype(float),                                  # retrograde
            np.abs(sp) / MEAN_SPD[p], sp / MEAN_SPD[p],
            (np.abs(sp) < 0.2 * MEAN_SPD[p]).astype(float),          # stationary
            (np.abs(sp) > MEAN_SPD[p]).astype(float),                # swift in course
            (ael < 8.5).astype(float),                               # combust, Lilly's 8 deg 30'
            (ael < 17.0).astype(float),                              # under the Sun's beams
            (ael < 0.2833).astype(float),                            # cazimi, 17 arcminutes
            (el < 0).astype(float),                                  # oriental / matutine
            ael / 180.0,
            BW[p] / 4.0, np.abs(BW[p]) / 4.0, DW[p] / 30.0,
            _in_band(LW[p], VIA_LO, VIA_HI),
            _deg(LW[p]) / 30.0,
            np.exp(-0.5 * (_sep(LW[p], EX_SIGN[p] * 30.0 + EX_DEG[p]) / 3.0) ** 2),
        ], axis=1))
        C.append(_circ(el))
        # what the benefic receives, from everything, in both directions of motion
        others = [b for b in MODERN10 if b != p]
        m2, s2 = _grid(LW, VW, LW, VW, [p], others, ASPECTS, (3.0, 7.0))
        C.append(m2); C.append(s2)
        # besieged between the malefics, and afflicted-versus-fortified tallies
        dm, ds = _wrap(LW[MAR] - LW[p]), _wrap(LW[SAT] - LW[p])
        C.append(((np.sign(dm) != np.sign(ds)) & (np.abs(dm) < 30.0) & (np.abs(ds) < 30.0)).astype(float))
        aff = np.zeros(n); fort = np.zeros(n)
        for ang in HARD:
            for q in MALEFIC:
                k, s, _, _ = _contact(LW[p], sp, LW[q], VW[q], ang, 6.0)
                aff += k; fort -= np.maximum(s, 0.0)
        for ang in SOFT + (0.0,):
            for q in (VEN, JUP):
                if q == p:
                    continue
                k, _, _, _ = _contact(LW[p], sp, LW[q], VW[q], ang, 6.0)
                fort += k
        strong = ((_points(LW[p], False)[p] >= 3.0) & (sp > 0) & (ael > 8.5)).astype(float)
        C.append(np.stack([aff, fort, fort - aff, strong,
                           strong * (1.0 - np.minimum(aff, 1.0))], axis=1))
    # the two benefics in aspect with each other, and the pair's combined strength
    C.append(np.stack([np.exp(-0.5 * (_sep(LW[VEN], LW[JUP]) - a) ** 2 / 36.0) for a in ASPECTS], axis=1))
    C.append((_points(LW[VEN], False)[VEN] + _points(LW[JUP], False)[JUP])[:, None])
    out["elec: benefics venus & jupiter at the election"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 4. the malefics on the luminaries and on Venus, by APPLYING hard aspect
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # Bonatti Tr. 5 and Lilly Book II: an applying conjunction, square or opposition from Mars or
    # Saturn to a luminary, to Venus, or to the lord of the seventh, spoils the election; a separating
    # one does not. The orb TIGHTNESS is the whole judgement, so three orbs are emitted, and the
    # single tightest offending orb in the chart is emitted as its own column.
    C = []
    targets = [SUN, MOON, VEN, JUP]
    mag, sgn = _grid(LW, VW, LW, VW, MALEFIC, targets, HARD, (2.0, 4.0, 8.0))
    C += [mag, sgn]
    m8, s8 = _grid(LW, VW, LW, VW, MALEFIC, targets, HARD8, (3.0,))
    C += [m8, s8]
    tight = np.full(n, 30.0)
    napp = np.zeros(n); wsum = np.zeros(n); wsum_app = np.zeros(n)
    for q in MALEFIC:
        for t in targets:
            for ang in HARD:
                k, s, o, dr = _contact(LW[q], VW[q], LW[t], VW[t], ang, 6.0)
                app = (s > 0).astype(float)
                tight = np.minimum(tight, np.where(app > 0, np.abs(o), 30.0))
                napp += app * (np.abs(o) < 10.0)
                wsum += k
                wsum_app += np.maximum(s, 0.0)
    C.append(np.stack([tight / 30.0, np.exp(-tight / 3.0), (tight < 1.0).astype(float),
                       (tight < 3.0).astype(float), (tight < 6.0).astype(float),
                       napp, wsum, wsum_app, wsum_app / np.maximum(wsum, 1e-6)], axis=1))
    # the malefics' own condition: a malefic in its own dignity does less harm (Lilly), a retrograde
    # or stationary malefic is worse, and a malefic in the via combusta is worse still
    for q in MALEFIC:
        C.append(_dig_flags(LW[q], q))
        C.append(_points(LW[q], False)[q])
        C.append(np.stack([(VW[q] < 0).astype(float), np.abs(VW[q]) / MEAN_SPD[q],
                           (np.abs(VW[q]) < 0.15 * MEAN_SPD[q]).astype(float),
                           _in_band(LW[q], VIA_LO, VIA_HI),
                           np.abs(_wrap(LW[q] - LW[SUN])) / 180.0,
                           (np.abs(_wrap(LW[q] - LW[SUN])) < 8.5).astype(float)], axis=1))
        C.append(_onehot(_sign(LW[q])[None, :], 12))
    # reception mitigates an affliction (Sahl): does the malefic have dignity where its victim sits?
    rec = []
    for q in MALEFIC:
        for t in (SUN, MOON, VEN):
            L = _lords(LW[t])
            has = ((L["dom"] == q) | (L["exa"] == q) | (L["trd"] == q) | (L["bnd"] == q)).astype(float)
            inasp = np.max(np.stack([np.exp(-0.5 * ((_sep(LW[q], LW[t]) - a) / 6.0) ** 2)
                                     for a in ASPECTS]), axis=0)
            rec += [has, has * inasp, inasp]
    C.append(np.stack(rec, axis=1))
    # the malefics enclosing a light or Venus
    for t in (SUN, MOON, VEN):
        dm, ds = _wrap(LW[MAR] - LW[t]), _wrap(LW[SAT] - LW[t])
        C.append(((np.sign(dm) != np.sign(ds)) & (np.abs(dm) < 30.0) & (np.abs(ds) < 30.0)).astype(float))
    out["elec: malefics afflicting the lights & venus"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 5. Mercury retrograde, and the shadow periods either side of the stations
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # "Let Mercury not be retrograde" is classical (Bonatti Tr. 5; Mercury signifies the contract).
    # The SHADOW periods are modern (Erin Sullivan, Retrograde Planets): the pre-shadow runs from the
    # day Mercury first reaches the degree at which it will later station direct, to the retrograde
    # station; the post-shadow runs from the direct station until it regains the degree of the
    # retrograde station. Both are defined by the station LONGITUDES, hence the station search.
    JW = E.JD[iW]
    tst, slon, sdir = _mercury_stations(float(JW.min()) - 400.0, float(JW.max()) + 400.0)
    j = np.clip(np.searchsorted(tst, JW) - 1, 1, len(tst) - 3)      # index of the previous station
    prev_t, next_t = tst[j], tst[j + 1]
    prev_l, next_l = slon[j], slon[j + 1]
    prev_d = sdir[j]
    mer_retro = (VW[MER] < 0).astype(float)
    d_prev = JW - prev_t
    d_next = next_t - JW
    # inside a retrogradation: the bracketing stations are retrograde then direct
    inretro = ((prev_d < 0) & (VW[MER] < 0)).astype(float)
    cyc = np.maximum(next_t - prev_t, 1e-6)
    # pre-shadow: direct, the next station is retrograde, and Mercury already stands at or beyond the
    # longitude of the direct station that will END that retrogradation (two stations ahead).
    pre_ref = slon[j + 2]
    a_pre = np.mod(LW[MER] - pre_ref, 360.0)
    b_pre = np.mod(next_l - pre_ref, 360.0)                         # the retrograde arc, ~10-15 deg
    pre = ((prev_d > 0) & (VW[MER] > 0) & (a_pre <= b_pre) & (b_pre < 40.0)).astype(float)
    # post-shadow: direct after a direct station, and not yet back to the retrograde station's degree
    post_ref = prev_l
    a_post = np.mod(LW[MER] - post_ref, 360.0)
    b_post = np.mod(slon[j - 1] - post_ref, 360.0)
    post = ((prev_d > 0) & (VW[MER] > 0) & (a_post <= b_post) & (b_post < 40.0)).astype(float)
    C = [np.stack([
        mer_retro, VW[MER] / MEAN_SPD[MER], np.abs(VW[MER]) / MEAN_SPD[MER],
        (np.abs(VW[MER]) < 0.1).astype(float), (np.abs(VW[MER]) < 0.3).astype(float),
        np.minimum(d_prev, 60.0) / 60.0, np.minimum(d_next, 60.0) / 60.0,
        np.exp(-d_prev / 7.0), np.exp(-d_next / 7.0),
        np.exp(-np.minimum(d_prev, d_next) / 3.0),
        (np.minimum(d_prev, d_next) < 3.0).astype(float),
        (np.minimum(d_prev, d_next) < 7.0).astype(float),
        (np.minimum(d_prev, d_next) < 14.0).astype(float),
        prev_d, inretro, np.clip((JW - prev_t) / cyc, 0.0, 1.0) * inretro,
        pre, post, np.clip(a_pre / np.maximum(b_pre, 1e-6), 0.0, 1.0) * pre,
        np.clip(a_post / np.maximum(b_post, 1e-6), 0.0, 1.0) * post,
        pre + post + inretro,                                        # "in the whole Mercury season"
        b_pre / 20.0, np.minimum(cyc, 130.0) / 130.0,
        _sep(LW[MER], prev_l) / 180.0, _sep(LW[MER], next_l) / 180.0,
        (_sign(LW[MER]) == _sign(prev_l)).astype(float),
    ], axis=1)]
    # Mercury's own condition and its synodic angle from the Earth, which is what actually drives the
    # retrogradation: phi = heliocentric Mercury minus heliocentric Earth (= geocentric Sun + 180).
    phi = _wrap(E.HELIO[iW, MER] - (LW[SUN] + 180.0))
    C.append(_circ(phi))
    C.append(np.stack([np.abs(phi) / 180.0, (np.abs(phi) < 33.0).astype(float),
                       np.abs(_wrap(LW[MER] - LW[SUN])) / 180.0,
                       (np.abs(_wrap(LW[MER] - LW[SUN])) < 8.5).astype(float),
                       (_wrap(LW[MER] - LW[SUN]) < 0).astype(float)], axis=1))
    C.append(_dig_flags(LW[MER], MER))
    C.append(_points(LW[MER], False)[MER])
    # the other planets' retrogradation, which the same doctrine forbids more weakly
    retro = np.stack([(VW[b] < 0).astype(float) for b in (VEN, MAR, JUP, SAT, URA, NEP, PLU)], axis=1)
    C.append(retro)
    C.append(retro.sum(axis=1))
    C.append(retro[:, :4].sum(axis=1))
    # Venus's own synodic angle, for the "never marry under a retrograde Venus" rule
    phv = _wrap(E.HELIO[iW, VEN] - (LW[SUN] + 180.0))
    C.append(_circ(phv))
    C.append(np.stack([np.abs(phv) / 180.0, (np.abs(phv) < 22.0).astype(float),
                       np.abs(VW[VEN]) / MEAN_SPD[VEN]], axis=1))
    out["elec: mercury retrograde & station shadows"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 6. eclipse proximity, and the eclipse degree on a significator
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # Bonatti Tr. 5 warns against beginning anything while the Moon is eclipsed or standing in an
    # eclipse degree; the modern electional rule extends the prohibition to a window either side, and
    # authors give anything from a few days to a fortnight, so every width is emitted as a flag and
    # the model may choose. The eclipse DEGREE falling on a natal light is the older and sharper form
    # of the rule, and it needs the eclipse longitudes, which is why the catalogue is searched.
    sj, sf, sl, lj, lf, ll = _eclipses(float(JW.min()) - 420.0, float(JW.max()) + 420.0)
    C = []
    for ev_t, ev_f, ev_l, kinds in ((sj, sf, sl, ((4, "total"), (8, "annular"), (16, "partial"),
                                                  (32, "hybrid"), (1, "central"))),
                                    (lj, lf, ll, ((4, "total"), (16, "partial"), (64, "penumbral")))):
        k = np.clip(np.searchsorted(ev_t, JW), 1, len(ev_t) - 1)
        dp = JW - ev_t[k - 1]                      # days since the previous eclipse of this kind
        dn = ev_t[k] - JW                          # days to the next
        near = np.where(dp <= dn, -dp, dn)         # signed: negative = the eclipse is past
        pick = np.where(dp <= dn, k - 1, k)
        C.append(np.stack([near / 200.0, np.abs(near) / 200.0, np.sign(near),
                           dp / 200.0, dn / 200.0], axis=1))
        C.append(np.stack([np.exp(-np.abs(near) / t) for t in (2.0, 5.0, 12.0, 30.0)], axis=1))
        C.append(np.stack([(np.abs(near) <= w).astype(float)
                           for w in (1.0, 3.0, 7.0, 15.0, 30.0, 45.0)], axis=1))
        C.append(np.stack([((ev_f[pick] & bit) > 0).astype(float) for bit, _ in kinds], axis=1))
        # the eclipse degree against the election's own lights and Venus, and against both nativities
        edeg = ev_l[pick]
        for chart in (LW, LO, LY):                 # the election's own lights, then both nativities'
            for b in (SUN, MOON, VEN):
                s = _sep(edeg, chart[b])
                C.append(np.stack([np.exp(-0.5 * (s / 3.0) ** 2),
                                   np.exp(-0.5 * ((s - 180.0) / 3.0) ** 2),
                                   np.exp(-0.5 * ((s - 90.0) / 3.0) ** 2),
                                   np.exp(-0.5 * (s / 8.0) ** 2)], axis=1))
        C.append(_onehot(_sign(edeg)[None, :], 12))
        cnt = (np.searchsorted(ev_t, JW + 183.0) - np.searchsorted(ev_t, JW - 183.0)).astype(float)
        C.append(cnt)
    # the nearest eclipse of either kind, and the classical ecliptic-limit view of the same fact
    ks = np.clip(np.searchsorted(sj, JW), 1, len(sj) - 1)
    kl = np.clip(np.searchsorted(lj, JW), 1, len(lj) - 1)
    both = np.minimum(np.minimum(JW - sj[ks - 1], sj[ks] - JW),
                      np.minimum(JW - lj[kl - 1], lj[kl] - JW))
    nd = np.abs(_wrap(2.0 * (LW[SUN] - LW[TNODE]))) / 2.0            # Sun's distance to the nodal axis
    C.append(np.stack([both / 200.0, np.exp(-both / 7.0), np.exp(-both / 20.0),
                       (both <= 15.0).astype(float), (both <= 7.0).astype(float),
                       nd / 90.0, (nd < 15.35).astype(float), (nd < 18.0).astype(float),
                       np.exp(-0.5 * (nd / 8.0) ** 2)], axis=1))
    out["elec: eclipse proximity & the eclipse degree"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 7. the seventh place — PROXY, twice over (see proxy 1 in the module docstring)
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # Ptolemy IV.5 and every electional author after him judge a marriage from the seventh place, its
    # lord, and the lord of the first. There is no Ascendant here, so the first place is proxied
    # twice: by the Sun's own sign ("solar-sign") and by the noon-chart Ascendant Sun+90 ("noon-MC").
    # NOTHING in this block is a real house. Both proxies are emitted because they disagree.
    C = []
    for asc in (np.mod(np.floor(LW[SUN] / 30.0) * 30.0, 360.0), np.mod(LW[SUN] + 90.0, 360.0)):
        s1 = _sign(asc)
        s7 = np.mod(s1 + 6, 12)
        l1, l7 = DOM[s1], DOM[s7]
        lon1, lon7 = LW[l1, ar], LW[l7, ar]
        spd1, spd7 = VW[l1, ar], VW[l7, ar]
        C.append(_onehot(np.stack([s1, s7]), 12))
        C.append(_onehot(np.stack([l1, l7]), 7))
        pts_d = _self_points(LW[:7], False)
        pts_n = _self_points(LW[:7], True)
        for l, lon, spd in ((l1, lon1, spd1), (l7, lon7, spd7)):
            ael = np.abs(_wrap(lon - LW[SUN]))
            notsun = (l != SUN).astype(float)
            C.append(np.stack([
                pts_d[l, ar], pts_n[l, ar],
                (spd < 0).astype(float),                             # a retrograde lord: Lilly's
                (ael < 8.5).astype(float) * notsun,                  # refusal, and a combust one
                (ael < 17.0).astype(float) * notsun,
                ael / 180.0,
                (_sign(lon) == s7).astype(float),                    # the lord in the seventh
                (_sign(lon) == s1).astype(float),                    # or in the first
                _in_band(lon, VIA_LO, VIA_HI),
                _deg(lon) / 30.0,
                np.isin(l, MALEFIC).astype(float),
                np.isin(l, BENEFIC).astype(float),
            ], axis=1))
        # the two lords in aspect, and in reception — Lilly's central marriage-election requirement
        sep17 = _sep(lon1, lon7)
        for w in (3.0, 6.0):
            C.append(np.stack([np.exp(-0.5 * ((sep17 - a) / w) ** 2) for a in ASPECTS], axis=1))
        _, sg, _, _ = _contact(lon1, spd1, lon7, spd7, 0.0, 6.0)
        C.append(sg)
        L1, L7 = _lords(lon1), _lords(lon7)
        r_7of1 = np.stack([(L1[k] == l7).astype(float) for k in ("dom", "exa", "trd", "bnd", "fac")], axis=1)
        r_1of7 = np.stack([(L7[k] == l1).astype(float) for k in ("dom", "exa", "trd", "bnd", "fac")], axis=1)
        inasp = np.max(np.stack([np.exp(-0.5 * ((sep17 - a) / 6.0) ** 2) for a in ASPECTS]), axis=0)
        C += [r_7of1, r_1of7, r_7of1 * r_1of7, (r_7of1.max(1) * r_1of7.max(1))[:, None],
              (r_7of1.max(1) * inasp)[:, None], (r_1of7.max(1) * inasp)[:, None], inasp[:, None],
              np.isin(np.stack([s1, s7]).T % 12, [0, 3, 6, 9]).astype(float)]
        # who stands in the seventh sign, and in the first
        occ7 = np.stack([(_sign(LW[b]) == s7).astype(float) for b in MODERN10], axis=1)
        occ1 = np.stack([(_sign(LW[b]) == s1).astype(float) for b in MODERN10], axis=1)
        C += [occ7, occ1]
        C.append(np.stack([
            occ7[:, [3, 5]].max(1), occ7[:, [4, 6]].max(1), occ7[:, 1], occ7[:, 0],
            occ7.sum(1), occ1.sum(1),
            occ7[:, [4, 6]].max(1) - occ7[:, [3, 5]].max(1),
        ], axis=1))
    out["elec: seventh-place proxy (solar-sign & noon-MC)"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 8. reception and mutual reception between the election's benefics and each natal ruler
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # Sahl: A receives B when B stands in a place where A has dignity, and reception without an aspect
    # is no reception at all. Across charts the same test is well defined — the election's Venus
    # standing in a sign the partner's own ruler governs — and it is the closest this data can come to
    # asking whether the day belongs to these two people. The natal "rulers" are proxies: the lord of
    # the natal Sun's sign (the solar-sign lord of the first), the lord of the opposite sign (the
    # proxy seventh lord), and the lord of the natal Moon's sign.
    LEVELS = ("dom", "exa", "trd", "bnd")
    C = []
    tal = []
    for chart in (LO, LY):
        s_sun, s_moon = _sign(chart[SUN]), _sign(chart[MOON])
        rulers = [DOM[s_sun], DOM[np.mod(s_sun + 6, 12)], DOM[s_moon]]
        got = []
        for b in (VEN, JUP, MOON):
            Lb = _lords(LW[b])
            for R in rulers:
                lonR = chart[R, ar]
                LR = _lords(lonR)
                # the natal ruler receives the election's benefic, and the reverse
                fwd = np.stack([(Lb[k] == R).astype(float) for k in LEVELS], axis=1)
                bwd = np.stack([(LR[k] == b).astype(float) for k in LEVELS], axis=1)
                sepx = _sep(LW[b], lonR)
                kern = lambda angs: np.max(np.stack(
                    [np.exp(-0.5 * ((sepx - a) / 6.0) ** 2) for a in angs]), axis=0)
                inasp, soft = kern(ASPECTS), kern(SOFT + (0.0,))
                C += [fwd, bwd, fwd * bwd]
                C.append(np.stack([fwd.max(1), bwd.max(1), fwd.max(1) * bwd.max(1),
                                   inasp, soft, fwd.max(1) * inasp, bwd.max(1) * inasp,
                                   fwd.max(1) * bwd.max(1) * inasp, sepx / 180.0], axis=1))
                got.append(np.stack([fwd.max(1), bwd.max(1), fwd.max(1) * bwd.max(1), inasp], axis=1))
        g = np.concatenate(got, axis=1)
        tal.append(np.stack([g[:, 0::4].sum(1), g[:, 1::4].sum(1), g[:, 2::4].sum(1),
                             g[:, 3::4].sum(1), g[:, 3::4].max(1)], axis=1))
    C += tal
    C.append(tal[0] - tal[1])                       # the older/younger asymmetry, both orderings kept
    out["elec: reception with the natal rulers"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 9. Bonatti's and Lilly's marriage-election considerations, each as its own flag
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # One column per named consideration, then the tradition's own TALLY of how many are satisfied —
    # which is what an electional astrologer actually produces. Considerations that need a house or a
    # clock time (the Moon in the sixth, eighth or twelfth; the hour-lord; a fortified seventh house
    # proper) are absent by necessity and are listed in the docstring, not silently proxied here.
    mal_app_moon = np.zeros(n)
    for q in MALEFIC:
        for ang in HARD:
            _, s, _, _ = _contact(LW[MOON], mspd, LW[q], VW[q], ang, 6.0)
            mal_app_moon = np.maximum(mal_app_moon, np.maximum(s, 0.0))
    ben_app_moon = np.zeros(n)
    for q in BENEFIC:
        for ang in SOFT + (0.0,):
            _, s, _, _ = _contact(LW[MOON], mspd, LW[q], VW[q], ang, 6.0)
            ben_app_moon = np.maximum(ben_app_moon, np.maximum(s, 0.0))
    # the Moon joined to a retrograde planet — Bonatti Tr. 5
    join_retro = np.zeros(n)
    for q in (MER, VEN, MAR, JUP, SAT):
        k, s, _, _ = _contact(LW[MOON], mspd, LW[q], VW[q], 0.0, 6.0)
        join_retro = np.maximum(join_retro, np.maximum(s, 0.0) * (VW[q] < 0))
    ven_pts = _points(LW[VEN], False)[VEN]
    jup_pts = _points(LW[JUP], False)[JUP]
    ven_el = np.abs(_wrap(LW[VEN] - LW[SUN]))
    jup_el = np.abs(_wrap(LW[JUP] - LW[SUN]))
    s1 = _sign(LW[SUN]); s7 = np.mod(s1 + 6, 12)
    l7 = DOM[s7]
    lon7, spd7 = LW[l7, ar], VW[l7, ar]
    mars_in_7 = (_sign(LW[MAR]) == s7).astype(float)
    sat_in_7 = (_sign(LW[SAT]) == s7).astype(float)
    ven_in_7 = (_sign(LW[VEN]) == s7).astype(float)
    jup_in_7 = (_sign(LW[JUP]) == s7).astype(float)
    lights_soft = np.max(np.stack([np.exp(-0.5 * ((_sep(LW[SUN], LW[MOON]) - a) / 6.0) ** 2)
                                   for a in SOFT]), axis=0)
    FLAGS = [
        ("moon increasing in light", waxing),                                    # Sahl; Bonatti Tr.5
        ("moon not combust", (el2 >= 12.0).astype(float)),                       # Lilly
        ("moon not void of course", 1.0 - voc),                                  # Lilly
        ("moon out of the via combusta", 1.0 - via),                             # Lilly
        ("moon free of applying malefic", 1.0 - np.minimum(mal_app_moon * 2.0, 1.0)),
        ("moon applying to a benefic", np.minimum(ben_app_moon * 2.0, 1.0)),     # Sahl
        ("moon not besieged", 1.0 - bes),
        ("moon not on the nodes", (np.minimum(_sep(LW[MOON], LW[TNODE]),
                                              _sep(LW[MOON], LW[TNODE] + 180.0)) > 6.0).astype(float)),
        ("moon not in fall or detriment", 1.0 - ((msign == 7) | (msign == 9)).astype(float)),
        ("moon swift in course", (mspd > MOON_MEAN).astype(float)),              # Bonatti Tr.5
        ("moon northern in latitude", (mlat > 0).astype(float)),
        ("moon increasing in latitude", (np.cos(np.deg2rad(F)) > 0).astype(float)),
        ("moon not in the last degrees", (sign_left >= 3.0).astype(float)),      # Bonatti Tr.5
        ("moon not joined a retrograde", 1.0 - np.minimum(join_retro * 2.0, 1.0)),
        ("moon in a fixed sign", np.isin(msign, [1, 4, 7, 10]).astype(float)),   # for an enduring
        ("moon in a common sign", np.isin(msign, [2, 5, 8, 11]).astype(float)),  # marriage: Lilly II
        ("venus dignified", (ven_pts >= 3.0).astype(float)),                     # Dorotheus V
        ("venus direct", (VW[VEN] > 0).astype(float)),
        ("venus not combust", (ven_el >= 8.5).astype(float)),
        ("venus free of malefic", 1.0 - np.minimum(2.0 * np.max(np.stack(
            [np.maximum(_contact(LW[VEN], VW[VEN], LW[q], VW[q], a, 6.0)[1], 0.0)
             for q in MALEFIC for a in HARD]), axis=0), 1.0)),
        ("venus swift", (np.abs(VW[VEN]) > MEAN_SPD[VEN]).astype(float)),
        ("jupiter dignified", (jup_pts >= 3.0).astype(float)),
        ("jupiter direct", (VW[JUP] > 0).astype(float)),
        ("jupiter not combust", (jup_el >= 8.5).astype(float)),
        ("mercury direct", (VW[MER] > 0).astype(float)),                         # Bonatti Tr.5
        ("mercury out of shadow", 1.0 - np.minimum(pre + post + inretro, 1.0)),
        ("no malefic in the 7th (proxy)", 1.0 - np.maximum(mars_in_7, sat_in_7)),
        ("a benefic in the 7th (proxy)", np.maximum(ven_in_7, jup_in_7)),
        ("7th lord direct", (spd7 > 0).astype(float)),                           # Lilly Book II
        ("7th lord not combust", ((np.abs(_wrap(lon7 - LW[SUN])) >= 8.5) | (l7 == SUN)).astype(float)),
        ("7th lord dignified", (_self_points(LW[:7], False)[l7, ar] >= 3.0).astype(float)),
        ("lights in a soft aspect", (lights_soft > 0.5).astype(float)),
        ("far from an eclipse", (both > 15.0).astype(float)),                    # Bonatti Tr.5
        ("no planet stationary", (np.min(np.stack([np.abs(VW[b]) / MEAN_SPD[b] for b in
                                                   (MER, VEN, MAR, JUP, SAT)]), axis=0) > 0.15
                                  ).astype(float)),
        ("saturn not in aspect to the moon", 1.0 - np.minimum(2.0 * np.max(np.stack(
            [np.maximum(_contact(LW[MOON], mspd, LW[SAT], VW[SAT], a, 6.0)[1], 0.0)
             for a in HARD]), axis=0), 1.0)),
        ("mars not in aspect to venus", 1.0 - np.minimum(2.0 * np.max(np.stack(
            [np.maximum(_contact(LW[VEN], VW[VEN], LW[MAR], VW[MAR], a, 6.0)[1], 0.0)
             for a in HARD]), axis=0), 1.0)),
    ]
    Fl = np.stack([f for _, f in FLAGS], axis=1)
    lunar = Fl[:, :14]      # the fourteen lunar musts; 14 and 15 are sign PREFERENCES and exclusive
    bonatti = Fl[:, [0, 2, 3, 4, 6, 7, 9, 12, 13, 24, 32, 33]]
    lilly = Fl[:, [0, 1, 2, 3, 5, 14, 16, 17, 18, 26, 27, 28, 29, 30, 31]]
    C = [Fl, Fl.sum(1), lunar.sum(1), bonatti.sum(1), lilly.sum(1),
         Fl.mean(1), (Fl.sum(1) >= 30.0).astype(float), (Fl.sum(1) <= 20.0).astype(float),
         lunar.prod(1), bonatti.prod(1)]
    # the pairwise products of the six considerations every author leads with — an election is judged
    # by conjunctions of conditions, not by their sum, and a linear model cannot form them itself
    key = Fl[:, [0, 2, 3, 4, 5, 16]]
    C.append(np.stack([key[:, a] * key[:, b] for a in range(6) for b in range(a + 1, 6)], axis=1))
    out["elec: bonatti & lilly considerations"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 10. the marriage of the lights
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # The Sun and Moon are the archetypal husband and wife of the whole tradition (Ptolemy I.4;
    # Valens II), so their own relationship at the election is read as the marriage itself. Aspect,
    # direction, mutual reception between them, the triplicity they share, their antiscia, and their
    # declinational parallel — five different encodings of one relationship.
    C = []
    ssep = _sep(LW[SUN], LW[MOON])
    for w in (2.0, 5.0, 10.0):
        C.append(np.stack([np.exp(-0.5 * ((ssep - a) / w) ** 2) for a in ASPECTS], axis=1))
    sg = []
    for a in ASPECTS:
        _, s, o, dr = _contact(LW[MOON], mspd, LW[SUN], VW[SUN], a, 6.0)
        sg += [s, _days_to_perfect(o, dr) / 45.0]
    C.append(np.stack(sg, axis=1))
    C.append(_circ(LW[SUN] - LW[MOON]))
    C.append(ssep[:, None] / 180.0)
    ssign, msg = _sign(LW[SUN]), msign
    dist = np.mod(msg - ssign, 12)
    C.append(_onehot(dist[None, :], 12))
    C.append(_onehot((np.mod(ssign, 4) * 4 + np.mod(msg, 4))[None, :], 16))       # element pair
    C.append(_onehot((np.mod(ssign, 3) * 3 + np.mod(msg, 3))[None, :], 9))        # modality pair
    C.append(np.stack([(np.mod(ssign, 4) == np.mod(msg, 4)).astype(float),        # same triplicity
                       (np.mod(ssign, 2) == np.mod(msg, 2)).astype(float),        # same gender
                       (np.mod(ssign, 3) == np.mod(msg, 3)).astype(float)], axis=1))
    # mutual reception of the lights: the Moon in Leo or Aries, the Sun in Cancer or Taurus
    m_in_s = ((msg == 4) | (msg == 0)).astype(float)
    s_in_m = ((ssign == 3) | (ssign == 1)).astype(float)
    C.append(np.stack([m_in_s, s_in_m, m_in_s * s_in_m, m_in_s + s_in_m], axis=1))
    # the antiscia of the lights (Lilly uses them in elections), and their declinations
    C.append(np.stack([np.exp(-0.5 * (_sep(np.mod(180.0 - LW[SUN], 360.0), LW[MOON]) / w) ** 2)
                       for w in (2.0, 6.0)]
                      + [np.exp(-0.5 * (_sep(np.mod(-LW[SUN], 360.0), LW[MOON]) / w) ** 2)
                         for w in (2.0, 6.0)], axis=1))
    C.append(np.stack([np.exp(-0.5 * ((DW[SUN] - DW[MOON]) / 1.0) ** 2),
                       np.exp(-0.5 * ((DW[SUN] + DW[MOON]) / 1.0) ** 2),
                       (DW[SUN] - DW[MOON]) / 60.0, DW[MOON] / 30.0, DW[SUN] / 24.0], axis=1))
    # the syzygy midpoint of the lights, and who stands on it
    mid = np.mod(LW[SUN] + _wrap(LW[MOON] - LW[SUN]) / 2.0, 360.0)
    C.append(_circ(mid))
    C.append(_onehot(_sign(mid)[None, :], 12))
    C.append(np.stack([np.exp(-0.5 * (np.minimum(_sep(mid, LW[b]), _sep(mid, LW[b] + 180.0)) / 4.0) ** 2)
                       for b in (VEN, JUP, MAR, SAT, MER)], axis=1))
    # signs of long ascension (Cancer..Sagittarius in the northern hemisphere) — used in elections for
    # a slow, enduring unfolding. There is no latitude here, so this is the northern convention only.
    C.append(np.stack([np.isin(ssign, [3, 4, 5, 6, 7, 8]).astype(float),
                       np.isin(msg, [3, 4, 5, 6, 7, 8]).astype(float)], axis=1))
    # both lights' dignity: a fortified pair of lights fortifies the election itself
    C.append(np.stack([_points(LW[SUN], False)[SUN], _points(LW[MOON], False)[MOON],
                       _points(LW[SUN], True)[SUN], _points(LW[MOON], True)[MOON]], axis=1))
    out["elec: the marriage of the lights"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 11. modern addition: the outer planets and Chiron on the wedding luminaries
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # No classical authority exists for these; they are the modern electional supplement. Their SIGNS
    # are deliberately NOT one-hotted: Uranus stays in a sign for seven years and Neptune for
    # fourteen, so a sign one-hot of an outer planet is a coarse index of the calendar era rather
    # than a statement about the election, and it would read as astrology while behaving as a date.
    C = []
    slow = [URA, NEP, PLU, CHI, LIL, JUN]
    mag, sgn = _grid(LW, VW, LW, VW, slow, [SUN, MOON, VEN], ASPECTS, (2.0, 6.0))
    C += [mag, sgn]
    C.append(np.stack([(VW[b] < 0).astype(float) for b in slow], axis=1))
    C.append(np.stack([np.abs(VW[b]) / max(MEAN_SPD.get(b, 0.05), 1e-6) for b in slow], axis=1))
    C.append(np.stack([BW[b] / 5.0 for b in slow], axis=1))
    # Juno is the asteroid the tradition of the last century reads for marriage, so she also gets her
    # own contacts to the benefics and to the lights' midpoint
    C.append(np.stack([np.exp(-0.5 * ((_sep(LW[JUN], LW[b]) - a) / 4.0) ** 2)
                       for b in (VEN, JUP, MAR, SAT, MOON, SUN) for a in ASPECTS], axis=1))
    C.append(np.stack([np.exp(-0.5 * (np.minimum(_sep(mid, LW[b]), _sep(mid, LW[b] + 180.0)) / 4.0) ** 2)
                       for b in slow], axis=1))
    C.append(_onehot(_sign(LW[CHI])[None, :], 12))
    C.append(_onehot(_sign(LW[JUN])[None, :], 12))
    # a hard-aspect tally from the outers to the lights, the modern analogue of block 4
    tal = np.zeros(n)
    for b in (URA, NEP, PLU, CHI):
        for t in LIGHTS:
            for a in HARD:
                k, _, _, _ = _contact(LW[b], VW[b], LW[t], VW[t], a, 4.0)
                tal += k
    C.append(tal)
    out["elec: outer planets & chiron on the lights"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 12. modern addition: the election chart's own aspect-pattern density
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # A count of how tightly woven the day is. Classical doctrine judges named contacts one at a time;
    # the modern reading of a chart as a whole gives it a density and a shape, so both the counts at
    # three orbs and the circular dispersion of the bodies are emitted.
    C = []
    for rows, tag in ((CLASSIC, "7"), (MODERN10, "10")):
        iu, ju = np.triu_indices(len(rows), k=1)
        A = np.array(rows)
        sepm = _sep(LW[A[iu]], LW[A[ju]])
        for orb in (3.0, 6.0, 8.0):
            C.append(np.stack([((np.abs(sepm - a) <= orb).sum(axis=0)).astype(float)
                               for a in ASPECTS], axis=1))
            hardc = np.stack([(np.abs(sepm - a) <= orb).sum(axis=0) for a in HARD]).sum(0).astype(float)
            softc = np.stack([(np.abs(sepm - a) <= orb).sum(axis=0) for a in SOFT]).sum(0).astype(float)
            C.append(np.stack([hardc, softc, hardc + softc, softc - hardc,
                               softc / np.maximum(hardc + softc, 1.0)], axis=1))
        for w in (3.0, 6.0, 10.0):
            K = np.stack([np.exp(-0.5 * ((sepm - a) / w) ** 2) for a in ASPECTS])
            C.append(np.stack([K.sum(axis=(0, 1)), K.max(axis=0).max(axis=0),
                               K.sum(axis=0).mean(axis=0)], axis=1))
        # circular dispersion, the largest empty arc, and how many signs are occupied
        z = np.exp(1j * np.deg2rad(LW[A]))
        R = np.abs(z.mean(axis=0))
        srt = np.sort(np.mod(LW[A], 360.0), axis=0)
        gaps = np.diff(np.vstack([srt, srt[:1] + 360.0]), axis=0)
        sg12 = _sign(LW[A])
        occ = np.stack([(sg12 == s).sum(axis=0) for s in range(12)]).astype(float)
        pr = occ / occ.sum(axis=0, keepdims=True)
        ent = -(np.where(pr > 0, pr * np.log(np.maximum(pr, 1e-12)), 0.0)).sum(axis=0)
        C.append(np.stack([R, gaps.max(axis=0) / 360.0, gaps.min(axis=0) / 360.0,
                           (occ > 0).sum(axis=0).astype(float), ent, occ.max(axis=0)], axis=1))
        C.append(occ.T)
        C.append(np.stack([(np.mod(sg12, 4) == e).sum(axis=0).astype(float) for e in range(4)], axis=1))
        C.append(np.stack([(np.mod(sg12, 3) == m).sum(axis=0).astype(float) for m in range(3)], axis=1))
        C.append(np.stack([(VW[A[i]] < 0).astype(float) for i in range(len(rows))], axis=1).sum(1))
        # the largest stellium: the most bodies inside a 10 and a 15 degree window
        for wd in (10.0, 15.0):
            cnt = np.zeros((len(rows), n))
            for i in range(len(rows)):
                cnt[i] = (_sep(LW[A[i]][None, :], LW[A]) <= wd).sum(axis=0)
            C.append(cnt.max(axis=0))
    # the named patterns, as soft minima over every triple of the ten bodies
    A = np.array(MODERN10)
    K120 = {}
    K90 = {}
    K180 = {}
    K60 = {}
    K150 = {}
    for i in range(10):
        for jx in range(i + 1, 10):
            s = _sep(LW[A[i]], LW[A[jx]])
            K120[(i, jx)] = np.exp(-0.5 * ((s - 120.0) / 6.0) ** 2)
            K90[(i, jx)] = np.exp(-0.5 * ((s - 90.0) / 6.0) ** 2)
            K180[(i, jx)] = np.exp(-0.5 * ((s - 180.0) / 6.0) ** 2)
            K60[(i, jx)] = np.exp(-0.5 * ((s - 60.0) / 6.0) ** 2)
            K150[(i, jx)] = np.exp(-0.5 * ((s - 150.0) / 6.0) ** 2)
    gt = np.zeros(n); ts = np.zeros(n); yod = np.zeros(n)
    for i in range(10):
        for jx in range(i + 1, 10):
            for k in range(jx + 1, 10):
                gt = np.maximum(gt, np.minimum(np.minimum(K120[(i, jx)], K120[(jx, k)]), K120[(i, k)]))
                ts = np.maximum(ts, np.minimum(np.minimum(K90[(i, jx)], K90[(jx, k)]), K180[(i, k)]))
                yod = np.maximum(yod, np.minimum(np.minimum(K150[(i, jx)], K150[(i, k)]), K60[(jx, k)]))
    C.append(np.stack([gt, ts, yod], axis=1))
    # the chart's total essential dignity, and how many of its planets are peregrine
    P = _self_points(LW[:7], False)
    Pn = _self_points(LW[:7], True)
    C.append(np.stack([P.sum(0), Pn.sum(0), (P == 0).sum(0).astype(float), P.max(0),
                       np.abs(BW[:7]).sum(0), np.abs(DW[:7]).sum(0)], axis=1))
    out["elec: election chart aspect-pattern density"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 13. the election against each nativity — Bonatti: an election may not contradict the nativity
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # Every one of the seven classical bodies of the election against every one of the seven of each
    # nativity, at the five Ptolemaic configurations and two orbs, SIGNED by application (only the
    # transiting body moves, so the natal speed is zero — the standard transit convention). Both
    # orderings of the couple are present because the pair older/younger is all we have in place of a
    # bride and a groom.
    C = []
    for chart in (LO, LY):
        mag, sgn = _grid(LW, VW, chart, None, CLASSIC, CLASSIC, ASPECTS, (3.0, 6.0), natal=True)
        C.append(sgn)
        m2, _ = _grid(LW, VW, chart, None, [MOON, VEN, JUP, MAR, SAT], [SUN, MOON, VEN],
                      ASPECTS, (4.0,), natal=True)
        C.append(m2)
        # the tallies the doctrine actually states: benefic light on the natal lights versus malefic
        ben = np.zeros(n); mal = np.zeros(n); bena = np.zeros(n); mala = np.zeros(n)
        for t in (SUN, MOON, VEN):
            for a in ASPECTS:
                for q in BENEFIC:
                    k, s, _, _ = _contact(LW[q], VW[q], chart[t], np.zeros(n), a, 6.0)
                    ben += k; bena += np.maximum(s, 0.0)
                for q in MALEFIC:
                    k, s, _, _ = _contact(LW[q], VW[q], chart[t], np.zeros(n), a, 6.0)
                    if a in HARD:
                        mal += k; mala += np.maximum(s, 0.0)
        C.append(np.stack([ben, mal, ben - mal, bena, mala, bena - mala,
                           ben / np.maximum(ben + mal, 1e-6)], axis=1))
        # the election's Moon on the natal Moon and Venus, the contact electional authors want, and
        # the natal Sun's own sign against the election's Sun sign
        C.append(np.stack([np.exp(-0.5 * (_sep(LW[MOON], chart[b]) / w) ** 2)
                           for b in (MOON, VEN, SUN, JUP) for w in (3.0, 8.0)], axis=1))
        C.append(_onehot(np.mod(_sign(LW[SUN]) - _sign(chart[SUN]), 12)[None, :], 12))
        C.append(_onehot(np.mod(msign - _sign(chart[MOON]), 12)[None, :], 12))
    out["elec: the election against each nativity"] = _c(*C)

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 14. the progressed charts and the Davison chart at the wedding date
    # ════════════════════════════════════════════════════════════════════════════════════════════
    # Slots 3 and 4 are each partner's secondary progression (a day for a year) to the wedding, and
    # slot 5 is the Davison chart, the real midpoint in time between the two births (Davison,
    # Synastry, 1977). Neither is classical; both are the modern way of asking whether the DATE is
    # ripe for these two people rather than merely well elected in itself. The progressed lunation
    # phase is Rudhyar's (The Lunation Cycle, 1967).
    C = []
    for LP, VP, nat in ((LPO, VPO, LO), (LPY, VPY, LY)):
        pel = np.mod(LP[MOON] - LP[SUN], 360.0)
        C.append(_circ(pel))
        C.append(np.stack([pel / 360.0, (pel < 180.0).astype(float),
                           (1.0 - np.cos(np.deg2rad(pel))) / 2.0], axis=1))
        C.append(_onehot(np.floor(pel / 45.0).astype(np.int64)[None, :], 8))
        C.append(_onehot(_sign(LP[MOON])[None, :], 12))
        C.append(_onehot(_sign(LP[SUN])[None, :], 12))
        # the progressed lights and Venus against the same person's own natal chart
        mag, sgn = _grid(LP, VP, nat, None, [SUN, MOON, VEN], [SUN, MOON, VEN, MAR, JUP, SAT],
                         ASPECTS, (1.5,), natal=True)
        C += [mag, sgn]
        # and against the election itself
        mag, sgn = _grid(LP, VP, LW, VW, [SUN, MOON, VEN], [SUN, MOON, VEN], ASPECTS, (3.0,))
        C += [mag, sgn]
        C.append(np.stack([np.abs(VP[MOON]) / MOON_MEAN, (VP[MER] < 0).astype(float),
                           (VP[VEN] < 0).astype(float), np.abs(VP[SUN])], axis=1))
    # the two progressed charts against each other: the couple's own moving synastry on the day
    mag, sgn = _grid(LPO, VPO, LPY, VPY, [SUN, MOON, VEN], [SUN, MOON, VEN], ASPECTS, (2.0, 5.0))
    C += [mag, sgn]
    C.append(np.stack([np.mod(np.mod(LPO[MOON] - LPO[SUN], 360.0)
                              - np.mod(LPY[MOON] - LPY[SUN], 360.0), 360.0) / 360.0], axis=1))
    # the Davison chart: its own lunar condition, and its contacts with the election
    del2 = np.mod(LDA[MOON] - LDA[SUN], 360.0)
    C.append(_circ(del2))
    C.append(np.stack([del2 / 360.0, (del2 < 180.0).astype(float),
                       (1.0 - np.cos(np.deg2rad(del2))) / 2.0,
                       np.abs(VDA[MOON]) / MOON_MEAN,
                       _in_band(LDA[MOON], VIA_LO, VIA_HI),
                       E.LAT[iDA, MOON] / 5.2], axis=1))
    C.append(_onehot(np.stack([_sign(LDA[SUN]), _sign(LDA[MOON]), _sign(LDA[VEN])]), 12))
    C.append(_dig_flags(LDA[VEN], VEN))
    C.append(np.stack([_points(LDA[VEN], False)[VEN], _points(LDA[JUP], False)[JUP],
                       _points(LDA[MOON], False)[MOON]], axis=1))
    davtrav = np.stack([_travel_to_aspect(LDA[MOON], VDA[MOON], LDA[p], VDA[p], ASPECTS)
                        for p in OTHERS]).reshape(-1, n).min(axis=0)
    C.append(np.stack([(davtrav > (30.0 - _deg(LDA[MOON]))).astype(float), davtrav / 30.0], axis=1))
    mag, sgn = _grid(LDA, VDA, LW, VW, [SUN, MOON, VEN, MAR, SAT], [SUN, MOON, VEN, MAR, SAT],
                     ASPECTS, (4.0,))
    C += [mag, sgn]
    out["elec: progressed & davison charts at the date"] = _c(*C)

    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in out.items()}


# ════════════════════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import time
    from core import load
    from evalx import quick

    t0 = time.time()
    E = load()

    # ── spot checks that would catch a wrong table or a wrong slot before anything is scored ─────
    LW, VW = E.LON[2], E.SPD[2]
    #                     0 Aries    95 Cancer  190 Libra  300 Aquarius
    assert (DOM[_sign(np.array([0.0, 95.0, 190.0, 300.0]))] == np.array([MAR, MOON, VEN, SAT])).all(), \
        "the domicile table is mis-transcribed"
    assert DETRI[0] == VEN and FALL_OF[6] == SUN, "detriment/fall are not the opposite places"
    assert abs(_in_band(LW[MOON], VIA_LO, VIA_HI).mean() - 30.0 / 360.0) < 0.02, \
        "the via combusta should catch about a twelfth of all Moons"
    assert 0.13 < (VW[MER] < 0).mean() < 0.25, "Mercury should be retrograde about a fifth of the time"
    _tst, _sl, _sd = _mercury_stations(float(E.JD[2].min()) - 400.0, float(E.JD[2].max()) + 400.0)
    assert (np.diff(_sd) != 0).all(), "Mercury's stations must alternate direct/retrograde"
    assert 15.0 < np.diff(_tst).min() and np.diff(_tst).max() < 120.0, \
        "a Mercury retrogradation is about three weeks and the direct run about three months"
    # the Moon applies to the Sun while waning and to the opposition while waxing — the sign
    # convention of _contact, checked against the phase it must reproduce
    _, _s0, _, _ = _contact(LW[MOON], VW[MOON], LW[SUN], VW[SUN], 0.0, 6.0)
    _el = np.mod(LW[MOON] - LW[SUN], 360.0)
    _far = (np.abs(_el - 180.0) > 0.5) & (np.minimum(_el, 360.0 - _el) > 0.5)   # away from the syzygies
    assert ((_s0 > 0)[_far] == (_el > 180.0)[_far]).all(), \
        "applying to the Sun must mean approaching the new Moon"

    B = build(E)
    secs = time.time() - t0
    bad, total = [], 0
    for name, X in B.items():
        try:
            assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
            assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
            assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
            assert np.isfinite(X).all(), f"{name}: non-finite values"
            assert X.std(axis=0).max() > 1e-12, f"{name}: all-constant block"
            assert name.startswith("elec: "), f"{name}: missing tradition tag"
        except AssertionError as e:
            bad.append(str(e))
            continue
        total += X.shape[1]
    assert len(set(B)) == len(B), "duplicate block names"
    if bad:
        for b in bad:
            print("FAIL", b)
        sys.exit(1)
    print(f"{TRADITION}\n{len(B)} blocks, {total} columns, n={E.n}, built in {secs:.1f}s\n")
    for name, X in B.items():
        acc, auc = quick(E, X)
        print(f"  {name:<52} {X.shape[1]:>5} cols   acc {100*acc:5.2f}%   AUC {auc:.4f}")
    print("\nOK")
