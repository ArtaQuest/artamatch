"""
trad_persian_arabic.py — Persian and medieval Arabic doctrine, turned into feature blocks.

THE AUTHORITIES IMPLEMENTED HERE (each rule is cited again at the line that computes it)

  Abu Ma'shar al-Balkhi, *Kitab al-madkhal al-kabir* (the Great Introduction), Books V-VIII — the
    dignities, the triplicity lords and their division of the life, the lots.
  Abu Ma'shar, *On the Revolutions of the Years of the Nativities* — the firdaria, the profection of
    the year and of the lots, the tasyir.
  al-Biruni, *Kitab al-tafhim* / *The Book of Instruction in the Elements of the Art of Astrology*
    (tr. R. Ramsay Wright, 1934) — §§ 439-461 the dignities, the aspects, the orbs ("moieties of
    light"), application and separation; §§ 475-478 the lots, including the lots of marriage and of
    children; § 526 the firdaria.
  Ibn Ezra, *Reshith Hokhmah* (The Beginning of Wisdom) — the point-scoring almuten.
  Guido Bonatti, *Liber Astronomiae* tr. IV — transmits the Persian firdaria with the nodes, and the
    rule that the two nodal periods take no sub-periods.

THE TWO PROXIES THIS DATASET FORCES, STATED PLAINLY

  1. NO ASCENDANT.  Only birth dates are known; every chart is cast for 12:00 UT with no birthplace,
     so there is no Ascendant, no Midheaven and no houses.  Two techniques here need one:
       * PROFECTIONS.  We profect from the SUN'S SIGN instead of the Ascendant's, one sign per
         completed year of life, and say so in the block name ("solar profection").  This is a
         PROXY, not the doctrine: Abu Ma'shar profects the Ascendant.  Solar profection is the
         standard fallback for a date-only chart and it preserves the one thing the technique
         actually claims — that the year's lord rotates through the twelve signs in order.
       * THE LOTS.  Every lot in Abu Ma'shar and al-Biruni is "cast from the Ascendant".  We
         substitute the SUN'S DEGREE for the Ascendant (the "solar chart", the Arabic practice when
         the hour is unknown).  Consequence worth knowing: with ASC := Sun, the day Lot of Fortune
         collapses to the Moon's own degree and the day Lot of Spirit to 2*Sun - Moon.  The lots are
         still real functions of the chart and the sect reversal still swaps them; they are simply
         one term poorer than the doctrine intends.
  2. NO SECT.  Sect (day chart / night chart) needs the Sun above or below the horizon, which needs
     the hour and the place.  SECT PROXY USED: every chart is cast at 12:00 UT, and at noon on the
     Greenwich meridian the Sun is above the horizon, so the DAY sect is taken as primary.  Because
     that proxy is constant across the dataset (and therefore carries no signal on its own) the
     NIGHT-sect ordering is computed in full and emitted alongside it, block for block: the firdaria
     has a day block and a night block, and the lots emit both the day formula and its correct night
     reversal.  Nothing here pretends to know the sect; the ensemble is handed both readings.

  The Moon's noon longitude carries about +-6 degrees of error against the true birth moment, so
  every lunar sign, every lot built on the Moon (Fortune, Spirit, Eros, the lots of children) and the
  lunar dignity points are about half reliable at sign level.  They are built anyway — the doctrine
  is built on them — but they should not be read as precise.

WHAT IS COMPUTED

  firdaria         the Persian 75-year chronocrator sequence, day and night orderings, with the
                   seven sub-periods of each planetary period in descending Chaldean order, giving
                   the lord and sub-lord in force at each partner's wedding age.
  tasyir           symbolic direction at one degree per year of life, and the aspects the directed
                   bodies of one partner make to the natal bodies of the other at the wedding; plus
                   the "divisor of the years", the lord of the bound the direction arrives in.
  profections      one sign per year from the Sun's sign (proxy, above), the profected sign, the lord
                   of the year, the monthly lord, and the profection of the lots of marriage.
  the lots         thirteen lots of Abu Ma'shar / al-Biruni including both marriage lots and the
                   lots of children, with the sect reversal.
  triplicity       the Dorothean triplicity lords used by the Persians, for the sign of the year, for
                   the light of the sect, and dividing the life into three.
  aspects          al-Biruni's five aspects with his own orbs ("moieties"), and the application /
                   separation distinction taken from the natal longitude SPEEDS (E.SPD), plus the
                   dexter / sinister distinction.
  reception        reception and mutual reception between the two charts by domicile and exaltation.
  almuten          the Ibn Ezra / al-Biruni point score (5-4-3-2-1) over the places available.

Interface: build(E) -> {name: (E.n, k) float64}.  Nothing else.  E.Y is never touched.
"""

import numpy as np

TRADITION = "Persian & medieval Arabic (Abu Ma'shar, al-Biruni, Ibn Ezra, Bonatti's firdaria)"

YR = 365.2425

# ── the seven visible bodies, in the order used for every 7-vector in this file ──────────────────
P7 = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
SUN, MOON, MERC, VEN, MARS, JUP, SAT = range(7)

# ── domicile lords of the twelve signs (al-Biruni § 439) ─────────────────────────────────────────
RULER = np.array([MARS, VEN, MERC, MOON, SUN, MERC, VEN, MARS, JUP, SAT, SAT, JUP])

# ── exaltation lords, -1 where the sign exalts no planet (al-Biruni § 442: Sun 19 Ari, Moon 3 Tau,
#    Mercury 15 Vir, Venus 27 Pis, Mars 28 Cap, Jupiter 15 Can, Saturn 21 Lib) ────────────────────
EXALT = np.array([SUN, MOON, -1, JUP, -1, MERC, SAT, -1, -1, MARS, -1, VEN])
EXALT_DEG = {SUN: (0, 19.0), MOON: (1, 3.0), MERC: (5, 15.0), VEN: (11, 27.0),
             MARS: (9, 28.0), JUP: (3, 15.0), SAT: (6, 21.0)}

# ── triplicity lords: the DOROTHEAN set that Abu Ma'shar and al-Biruni transmit (day, night,
#    participating).  Fire Sun/Jupiter/Saturn · Earth Venus/Moon/Mars · Air Saturn/Mercury/Jupiter ·
#    Water Venus/Mars/Moon.  (Ptolemy differs on water; the Persian tradition uses this one.) ─────
_TRIP4 = {0: (SUN, JUP, SAT), 1: (VEN, MOON, MARS), 2: (SAT, MERC, JUP), 3: (VEN, MARS, MOON)}
TRIP = np.array([_TRIP4[s % 4] for s in range(12)])          # (12, 3)

# ── the Egyptian bounds / terms (hadd), the set al-Biruni § 443 gives first and the Persians use ──
_BOUNDS = [
    [(JUP, 6), (VEN, 12), (MERC, 20), (MARS, 25), (SAT, 30)],        # Aries
    [(VEN, 8), (MERC, 14), (JUP, 22), (SAT, 27), (MARS, 30)],        # Taurus
    [(MERC, 6), (JUP, 12), (VEN, 17), (MARS, 24), (SAT, 30)],        # Gemini
    [(MARS, 7), (VEN, 13), (MERC, 19), (JUP, 26), (SAT, 30)],        # Cancer
    [(JUP, 6), (VEN, 11), (SAT, 18), (MERC, 24), (MARS, 30)],        # Leo
    [(MERC, 7), (VEN, 17), (JUP, 21), (MARS, 28), (SAT, 30)],        # Virgo
    [(SAT, 6), (MERC, 14), (JUP, 21), (VEN, 28), (MARS, 30)],        # Libra
    [(MARS, 7), (VEN, 11), (MERC, 19), (JUP, 24), (SAT, 30)],        # Scorpio
    [(JUP, 12), (VEN, 17), (MERC, 21), (SAT, 26), (MARS, 30)],       # Sagittarius
    [(MERC, 7), (JUP, 14), (VEN, 22), (SAT, 26), (MARS, 30)],        # Capricorn
    [(MERC, 7), (VEN, 13), (JUP, 20), (MARS, 25), (SAT, 30)],        # Aquarius
    [(VEN, 12), (JUP, 16), (MERC, 19), (MARS, 28), (SAT, 30)],       # Pisces
]
BOUND = np.zeros((12, 30), int)
for _s, _rows in enumerate(_BOUNDS):
    _lo = 0
    for _p, _hi in _rows:
        BOUND[_s, _lo:_hi] = _p
        _lo = _hi

# ── the faces (decans): the descending Chaldean sequence, Mars taking the first face of Aries ────
CHALD = np.array([SAT, JUP, MARS, SUN, VEN, MERC, MOON])      # descending order of the spheres
FACE = np.array([[CHALD[(2 + 3 * s + d) % 7] for d in range(3)] for s in range(12)])

# ── al-Biruni § 458, the orbs ("moieties of light"), degrees ─────────────────────────────────────
ORB7 = np.array([15.0, 12.0, 7.0, 7.0, 8.0, 9.0, 9.0])
MOIETY = 0.5 * (ORB7[:, None] + ORB7[None, :])               # (7, 7) the half-sum rule

# ── al-Biruni's five aspects (§§ 447-451): conjunction, sextile, square, trine, opposition ───────
ASPECTS = [0.0, 60.0, 90.0, 120.0, 180.0]
MINOR_DEX = [60.0, 90.0, 120.0]                              # only these can be dexter or sinister

# ── the firdaria (Abu Ma'shar via Bonatti, *Liber Astronomiae* tr. IV; al-Biruni § 526) ──────────
#    codes 0-6 the planets, 7 = Caput Draconis (north node), 8 = Cauda Draconis (south node).
#    Day: Sun 10, Venus 8, Mercury 13, Moon 9, Saturn 11, Jupiter 12, Mars 7, then the nodes 3 + 2.
#    Night: begins with the Moon and runs Moon 9, Saturn 11, Jupiter 12, Mars 7, Sun 10, Venus 8,
#    Mercury 13, then the same nodes.  Either way 70 + 5 = 75 years, and then it repeats.
FIRD_DAY = [(SUN, 10), (VEN, 8), (MERC, 13), (MOON, 9), (SAT, 11), (JUP, 12), (MARS, 7), (7, 3), (8, 2)]
FIRD_NIGHT = [(MOON, 9), (SAT, 11), (JUP, 12), (MARS, 7), (SUN, 10), (VEN, 8), (MERC, 13), (7, 3), (8, 2)]
FIRD_SPAN = 75.0


def _sub_table(order):
    """Each planetary period splits into SEVEN equal sub-periods, the first belonging to the period
    lord itself and the rest following in descending Chaldean order (Bonatti; the standard firdaria
    tables).  The two nodal periods are NOT subdivided — their sub-lord is the node itself."""
    T = np.zeros((len(order), 7), int)
    for i, (code, _) in enumerate(order):
        if code >= 7:
            T[i, :] = code
        else:
            p = int(np.where(CHALD == code)[0][0])
            T[i, :] = CHALD[(p + np.arange(7)) % 7]
    return T


SUB_DAY, SUB_NIGHT = _sub_table(FIRD_DAY), _sub_table(FIRD_NIGHT)


# ── small numeric helpers (kept local so the module stands alone) ────────────────────────────────
def _wrap(x):
    return (np.asarray(x, float) + 180.0) % 360.0 - 180.0


def _sep(a, b):
    return np.abs(_wrap(np.asarray(a, float) - np.asarray(b, float)))


def _kern(s, ang, w):
    return np.exp(-0.5 * ((np.asarray(s, float) - ang) / w) ** 2)


def _signof(lon):
    return np.floor(np.mod(np.asarray(lon, float), 360.0) / 30.0).astype(int)


def _onehot(idx, k):
    idx = np.asarray(idx).astype(int).ravel()
    out = np.zeros((idx.size, k))
    m = (idx >= 0) & (idx < k)
    out[np.where(m)[0], idx[m]] = 1.0
    return out


def _circ(lon):
    r = np.deg2rad(np.asarray(lon, float))
    return np.stack([np.cos(r), np.sin(r)], axis=-1)


def _offset(d, ang):
    """Signed distance from exactitude of aspect `ang`, for a signed separation d in (-180, 180].
    Positive means the aspect is past exact in the direction of increasing d."""
    if ang == 0.0:
        return d
    if ang == 180.0:
        return _wrap(d - 180.0)
    s = np.where(d >= 0.0, 1.0, -1.0)
    return d - s * ang


def _prune(X):
    """Drop columns with zero variance.  Target-free (variance only) and deterministic."""
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[:, None]
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    # NO VARIANCE PRUNING HERE, DELIBERATELY. This used to drop columns whose standard deviation was
    # zero in the batch being built, and that made a block's WIDTH a function of the DATA rather than
    # of the code. Two consequences, both silent: a scoring batch (one couple, or ten thousand
    # candidates sharing a fixed partner) has many constant columns, so prediction handed the model a
    # narrower and differently-ordered matrix than training did; and a full run built in row chunks
    # produced chunks of different widths that could not be concatenated. Constant columns are now
    # pruned exactly once, globally, by run.collect, which records `kept_idx` in the manifest so
    # prediction can select the same columns. Width is a function of the code alone.
    return np.ascontiguousarray(X)


def _points(lon, day=True):
    """The medieval point score of a degree, per planet — (n, 7).

    al-Biruni § 439-446 and Ibn Ezra, *Reshith Hokhmah*: domicile 5, exaltation 4, triplicity 3,
    bound (term) 2, face (decan) 1.  Only the sect-appropriate triplicity lord takes the 3 points.
    """
    lon = np.mod(np.asarray(lon, float), 360.0)
    s = np.floor(lon / 30.0).astype(int)
    d = lon - 30.0 * s
    di = np.clip(np.floor(d).astype(int), 0, 29)
    fi = np.clip(np.floor(d / 10.0).astype(int), 0, 2)
    n = lon.shape[0]
    r = np.arange(n)
    P = np.zeros((n, 7))
    P[r, RULER[s]] += 5.0
    ex = EXALT[s]
    m = ex >= 0
    if m.any():
        P[r[m], ex[m]] += 4.0
    P[r, TRIP[s, 0 if day else 1]] += 3.0
    P[r, BOUND[s, di]] += 2.0
    P[r, FACE[s, fi]] += 1.0
    return P


def _firdaria(age, order, subtab):
    """The firdaria lord and sub-lord in force at `age`.

    Returns (lord, sublord, fraction elapsed through the period, years to the next handover,
    second-cycle flag).  The 75-year sequence repeats, so age >= 75 wraps (Bonatti).
    """
    codes = np.array([c for c, _ in order])
    yrs = np.array([float(y) for _, y in order])
    cum = np.cumsum(yrs)
    start = np.concatenate([[0.0], cum[:-1]])
    a = np.mod(np.asarray(age, float), FIRD_SPAN)
    i = np.clip(np.searchsorted(cum, a, side="right"), 0, len(order) - 1)
    t = a - start[i]
    L = yrs[i]
    j = np.clip(np.floor(t / (L / 7.0)).astype(int), 0, 6)
    return codes[i], subtab[i, j], t / L, L - t, (np.asarray(age, float) >= FIRD_SPAN).astype(float)


def _lots(asc, L7, day=True):
    """The lots of Abu Ma'shar (Great Introduction VIII) and al-Biruni (§§ 475-478).

    `asc` is the Ascendant PROXY (the Sun's degree — see the module docstring).  A lot is
    asc + (B - C); the sect reversal exchanges B and C at night, which is done here for the seven
    Hermetic lots al-Biruni transmits and for the lots of male / female children.

    The two marriage lots and the two orderings of the Jupiter/Saturn lot are emitted in BOTH
    directions unconditionally instead of being reversed, for two reasons: al-Biruni gives the
    marriage lot as "from Saturn to Venus for men, from Venus to Saturn for women" and reports that
    only *some* reverse it at night; and the sources disagree about which way the Jupiter/Saturn arc
    runs for children (al-Biruni § 478 puts a Jupiter/Saturn lot in the fifth place; Paulus ch. 23
    gives the same arc to the third place, brothers).  Emitting both orderings covers the
    disagreement without pretending to settle it.
    """
    Su, Mo, Me, Ve, Ma, Ju, Sa = [L7[i] for i in range(7)]
    m = lambda x: np.mod(x, 360.0)
    out = {}
    if day:
        out["fortune"] = m(asc + Mo - Su)                    # al-Biruni § 476, the lot of Fortune
        out["spirit"] = m(asc + Su - Mo)                     # the lot of the Spirit (daemon)
        out["eros"] = m(asc + Ve - out["spirit"])            # Eros: Spirit -> Venus
        out["necessity"] = m(asc + out["fortune"] - Me)      # Necessity: Mercury -> Fortune
        out["courage"] = m(asc + Ma - out["fortune"])        # Courage: Fortune -> Mars
        out["victory"] = m(asc + Ju - out["spirit"])         # Victory: Spirit -> Jupiter
        out["nemesis"] = m(asc + out["fortune"] - Sa)        # Nemesis: Saturn -> Fortune
        out["male children"] = m(asc + Ju - Mo)              # al-Biruni § 478 (5th place, variant)
        out["female children"] = m(asc + Ve - Mo)            # al-Biruni § 478 (5th place, variant)
    else:
        out["fortune"] = m(asc + Su - Mo)
        out["spirit"] = m(asc + Mo - Su)
        out["eros"] = m(asc + out["spirit"] - Ve)
        out["necessity"] = m(asc + Me - out["fortune"])
        out["courage"] = m(asc + out["fortune"] - Ma)
        out["victory"] = m(asc + out["spirit"] - Ju)
        out["nemesis"] = m(asc + Sa - out["fortune"])
        out["male children"] = m(asc + Mo - Ju)
        out["female children"] = m(asc + Mo - Ve)
    out["marriage of men"] = m(asc + Ve - Sa)                # al-Biruni § 478: Saturn -> Venus
    out["marriage of women"] = m(asc + Sa - Ve)              # al-Biruni § 478: Venus -> Saturn
    out["children Ju-Sa"] = m(asc + Ju - Sa)
    out["children Sa-Ju"] = m(asc + Sa - Ju)
    return out


REVERSING = ["fortune", "spirit", "eros", "necessity", "courage", "victory", "nemesis",
             "male children", "female children"]
LOTS_ALL = REVERSING + ["marriage of men", "marriage of women", "children Ju-Sa", "children Sa-Ju"]
LOTS_KEY = ["fortune", "spirit", "eros", "marriage of men", "marriage of women",
            "children Ju-Sa", "children Sa-Ju", "male children"]


def _syzygy(sun, moon):
    """The prenatal syzygy — one of Ibn Ezra's almuten places.

    APPROXIMATION, not an ephemeris search: the elongation is run backwards at the MEAN synodic rate
    (12.1907 deg/day) to the last new or full Moon, whichever is nearer, and the Sun is run back at
    its mean motion.  The true elongation rate varies 11.8-14.9 deg/day, so the returned degree can
    be a couple of degrees out and the sign occasionally wrong.  At a new moon the syzygy degree is
    the common degree of the luminaries; at a full moon the doctrine wants the luminary above the
    earth, which needs a birth hour, so the Moon's degree is used and that choice is arbitrary.
    """
    e = np.mod(np.asarray(moon, float) - np.asarray(sun, float), 360.0)
    rate = 12.1907491
    d_new = e / rate
    d_full = np.mod(e - 180.0, 360.0) / rate
    use_new = d_new <= d_full
    days = np.where(use_new, d_new, d_full)
    sun_then = np.mod(np.asarray(sun, float) - 0.98564736 * days, 360.0)
    return np.where(use_new, sun_then, np.mod(sun_then + 180.0, 360.0))


def build(E):
    n = E.n
    B7 = np.array([E.IDX[p] for p in P7])
    lo7, ly7 = E.LON[0][B7], E.LON[1][B7]                    # (7, n) natal longitudes
    so7, sy7 = E.SPD[0][B7], E.SPD[1][B7]                    # (7, n) natal longitude speeds
    node_o, node_y = E.LON[0][E.IDX["TrueNode"]], E.LON[1][E.IDX["TrueNode"]]
    age_o = (E.JD[2] - E.JD[0]) / YR
    age_y = (E.JD[2] - E.JD[1]) / YR
    r = np.arange(n)
    out = {}

    # extended body table indexed by firdaria code 0..8 (7 = north node, 8 = south node)
    ext_o = np.vstack([lo7, node_o[None, :], np.mod(node_o + 180.0, 360.0)[None, :]])
    ext_y = np.vstack([ly7, node_y[None, :], np.mod(node_y + 180.0, 360.0)[None, :]])

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 1-2.  FIRDARIA — the Persian chronocrators, day ordering and night ordering
    #       (Abu Ma'shar via Bonatti tr. IV; al-Biruni § 526).  The sect is unknowable here, so both
    #       orderings are emitted as separate blocks; see the module docstring for the proxy.
    # ════════════════════════════════════════════════════════════════════════════════════════════
    fd = {t: {} for t in ("day", "night")}
    for tag, order, subtab in (("day", FIRD_DAY, SUB_DAY), ("night", FIRD_NIGHT, SUB_NIGHT)):
        cols = []
        for who, age in (("o", age_o), ("y", age_y)):
            lord, sub, frac, rem, cyc = _firdaria(age, order, subtab)
            fd[tag][who] = (lord, sub, frac, rem)
            cols += [_onehot(lord, 9), _onehot(sub, 9), _circ(360.0 * frac),
                     frac[:, None], (rem / 13.0)[:, None], cyc[:, None]]
        out[f"pa: firdaria {tag}-sect lord+sublord"] = _prune(np.hstack(cols))

    # ── 3. the firdaria of the two partners against each other ──────────────────────────────────
    cols = []
    for tag in ("day", "night"):
        lo_c, so_c = fd[tag]["o"][0], fd[tag]["o"][1]
        ly_c, sy_c = fd[tag]["y"][0], fd[tag]["y"][1]
        cols.append(_onehot(lo_c * 9 + ly_c, 81))                      # the pair of period lords
        cols.append((lo_c == ly_c).astype(float)[:, None])             # same lord ruling both
        cols.append((so_c == sy_c).astype(float)[:, None])             # same sub-lord
        cols.append((lo_c == sy_c).astype(float)[:, None])             # his lord = her sub-lord
        cols.append((so_c == ly_c).astype(float)[:, None])
        # the natal degrees of the two ruling planets, and the aspect between them
        a = ext_o[lo_c, r]
        b = ext_y[ly_c, r]
        s = _sep(a, b)
        cols.append(np.stack([_kern(s, ang, 6.0) for ang in ASPECTS], axis=1))
        a2, b2 = ext_o[so_c, r], ext_y[sy_c, r]
        s2 = _sep(a2, b2)
        cols.append(np.stack([_kern(s2, ang, 6.0) for ang in ASPECTS], axis=1))
        cols.append(_circ(_wrap(a - b)))
    out["pa: firdaria lords paired"] = _prune(np.hstack(cols))

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 4-5.  TASYIR — symbolic direction at ONE DEGREE PER YEAR of life (Abu Ma'shar, *On the
    #       Revolutions of the Years of the Nativities*; al-Biruni § 522, the tasyir of the
    #       significators).  Each natal body is advanced by the partner's age in degrees, and the
    #       aspects the directed positions make to the OTHER chart's natal bodies are read.
    # ════════════════════════════════════════════════════════════════════════════════════════════
    dir_o = np.mod(lo7 + age_o[None, :], 360.0)
    dir_y = np.mod(ly7 + age_y[None, :], 360.0)
    cols = []
    for src, tgt in ((dir_o, ly7), (dir_y, lo7)):
        for a in range(7):
            for b in range(7):
                s = _sep(src[a], tgt[b])
                for ang in ASPECTS:
                    cols.append(_kern(s, ang, 3.0)[:, None])
    out["pa: tasyir 1deg/yr directed-to-natal orbs"] = _prune(np.hstack(cols))

    cols = []
    for src, tgt in ((dir_o, ly7), (dir_y, lo7)):
        S = _sep(src[:, None, :], tgt[None, :, :])                     # (7, 7, n)
        for ang in ASPECTS:
            off = np.abs(S - ang)
            cols.append(off.reshape(49, n).min(axis=0)[:, None] / 30.0)  # closest hit in the chart
            cols.append((off <= 1.0).reshape(49, n).sum(axis=0)[:, None])  # exact to the year
            cols.append((off <= 3.0).reshape(49, n).sum(axis=0)[:, None])
        # the marriage significators of the tradition: the luminaries, Venus and Saturn
        for a in (SUN, MOON, VEN, SAT):
            for b in (SUN, MOON, VEN, SAT):
                off = np.min(np.abs(S[a, b][:, None] - np.array(ASPECTS)[None, :]), axis=1)
                cols.append(_kern(off, 0.0, 2.0)[:, None])
    # directed marriage lots (the lot itself is directed one degree per year)
    lots_o_day = _lots(lo7[SUN], lo7, day=True)
    lots_y_day = _lots(ly7[SUN], ly7, day=True)
    lots_o_night = _lots(lo7[SUN], lo7, day=False)
    lots_y_night = _lots(ly7[SUN], ly7, day=False)
    for ln in ("marriage of men", "marriage of women"):
        d1 = np.mod(lots_o_day[ln] + age_o, 360.0)
        d2 = np.mod(lots_y_day[ln] + age_y, 360.0)
        for b in (SUN, MOON, VEN):
            cols.append(_kern(_sep(d1, ly7[b]), 0.0, 3.0)[:, None])
            cols.append(_kern(_sep(d2, lo7[b]), 0.0, 3.0)[:, None])
        cols.append(_kern(_sep(d1, d2), 0.0, 3.0)[:, None])
    # ── the DIVISOR of the years (al-Biruni § 522; Abu Ma'shar's *qisma*, Latin *divisor*): the
    #    tasyir arrives in one of the BOUNDS, and the lord of that bound governs the year — a planet
    #    aspecting the directed degree is its "partner" (participator).  The doctrine directs the
    #    ASCENDANT; with no birth time we direct the Sun's and the Moon's degrees instead and say so.
    #    The partner test uses the ASPECTING planet's own orb (ORB7), because a directed degree is
    #    not a planet and has no moiety of its own — a stated choice, not a rule of al-Biruni's.
    div = {}
    for who, D, other7 in (("o", dir_o, ly7), ("y", dir_y, lo7)):
        for nm in ("Sun", "Moon"):
            deg = D[SUN if nm == "Sun" else MOON]
            s = _signof(deg)
            di = np.clip(np.floor(deg - 30.0 * s).astype(int), 0, 29)
            lord = BOUND[s, di]
            div[(who, nm)] = lord
            cols += [_onehot(lord, 7), _onehot(s, 12),
                     (lord == RULER[s]).astype(float)[:, None]]
            hit = np.zeros((n, 7))
            for b in range(7):
                dd = _wrap(deg - other7[b])
                h = np.zeros(n, bool)
                for ang in ASPECTS:
                    h |= np.abs(_offset(dd, ang)) <= ORB7[b]
                hit[:, b] = h
            cols.append(hit)
        lm = np.mod((lots_o_day if who == "o" else lots_y_day)["marriage of men"]
                    + (age_o if who == "o" else age_y), 360.0)
        s = _signof(lm)
        di = np.clip(np.floor(lm - 30.0 * s).astype(int), 0, 29)
        cols.append(_onehot(BOUND[s, di], 7))
    cols.append(_onehot(div[("o", "Sun")] * 7 + div[("y", "Sun")], 49))
    cols.append((div[("o", "Sun")] == div[("y", "Sun")]).astype(float)[:, None])
    cols.append((div[("o", "Moon")] == div[("y", "Moon")]).astype(float)[:, None])
    out["pa: tasyir hits + divisor of the years"] = _prune(np.hstack(cols))

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 6.  ANNUAL PROFECTIONS and the LORD OF THE YEAR (Abu Ma'shar, *Revolutions of the Years of the
    #     Nativities*).  One sign per completed year of life.  PROFECTED FROM THE SUN'S SIGN, not
    #     the Ascendant's — a documented proxy forced by having no birth time (module docstring).
    #     The monthly profection (one sign per twelfth of the year) is likewise solar.
    # ════════════════════════════════════════════════════════════════════════════════════════════
    prof = {}
    cols = []
    for who, age, L in (("o", age_o, lo7), ("y", age_y, ly7)):
        place = np.floor(age).astype(int) % 12                        # 0 = the natal sign itself
        psign = (_signof(L[SUN]) + place) % 12
        lord = RULER[psign]
        mplace = np.clip(np.floor((age - np.floor(age)) * 12.0).astype(int), 0, 11)
        msign = (psign + mplace) % 12
        mlord = RULER[msign]
        prof[who] = (place, psign, lord, mlord)
        cols += [_onehot(psign, 12), _onehot(lord, 7), _onehot(place, 12), _onehot(mlord, 7),
                 (place == 6).astype(float)[:, None]]                 # the year of the 7th place
    plo, ply = prof["o"][2], prof["y"][2]
    cols.append(_onehot(plo * 7 + ply, 49))                           # the pair of year-lords
    cols.append((plo == ply).astype(float)[:, None])
    cols.append(((prof["o"][0] == 6) & (prof["y"][0] == 6)).astype(float)[:, None])
    a, b = lo7[plo, r], ly7[ply, r]
    cols.append(np.stack([_kern(_sep(a, b), ang, 6.0) for ang in ASPECTS], axis=1))
    cols.append(np.stack([(so7[plo, r] < 0).astype(float), (sy7[ply, r] < 0).astype(float)], axis=1))
    cols.append(_circ(_wrap(a - b)))
    # Abu Ma'shar profects the LOTS as well as the Ascendant: the lot of marriage of the year
    for who, lots, pl in (("o", lots_o_day, prof["o"][0]), ("y", lots_y_day, prof["y"][0])):
        for ln in ("marriage of men", "marriage of women"):
            ps = (_signof(lots[ln]) + pl) % 12
            cols.append(_onehot(RULER[ps], 7))
    out["pa: solar profection + lord of the year"] = _prune(np.hstack(cols))

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 7.  THE LOTS, circular encoding — the day formulae AND their correct night reversal.
    # ════════════════════════════════════════════════════════════════════════════════════════════
    cols = []
    for ln in LOTS_ALL:
        cols += [_circ(lots_o_day[ln]), _circ(lots_y_day[ln]),
                 _circ(_wrap(lots_o_day[ln] - lots_y_day[ln]))]
    for ln in REVERSING:
        cols += [_circ(lots_o_night[ln]), _circ(lots_y_night[ln]),
                 _circ(_wrap(lots_o_night[ln] - lots_y_night[ln]))]
    out["pa: lots day+night reversal (circular)"] = _prune(np.hstack(cols))

    # ── 8. the lots by sign, and the lord of each lot ────────────────────────────────────────────
    cols = []
    for ln in LOTS_KEY:
        for lots in (lots_o_day, lots_y_day):
            s = _signof(lots[ln])
            cols += [_onehot(s, 12), _onehot(RULER[s], 7)]
    for ln in LOTS_ALL:
        so_, sy_ = _signof(lots_o_day[ln]), _signof(lots_y_day[ln])
        cols.append((so_ == sy_).astype(float)[:, None])              # the two lots in one sign
        cols.append((RULER[so_] == RULER[sy_]).astype(float)[:, None])
    out["pa: lot signs + lot lords (one-hot)"] = _prune(np.hstack(cols))

    # ── 9. the marriage and children lots of one chart against the other chart's planets ─────────
    cols = []
    targets = (SUN, MOON, VEN, MARS, JUP, SAT)
    for ln in ("marriage of men", "marriage of women", "children Ju-Sa", "male children"):
        for lot, tgt in ((lots_o_day[ln], ly7), (lots_y_day[ln], lo7)):
            for b in targets:
                s = _sep(lot, tgt[b])
                cols.append(np.stack([_kern(s, ang, 6.0) for ang in ASPECTS], axis=1))
    for ln in LOTS_ALL:
        s = _sep(lots_o_day[ln], lots_y_day[ln])
        cols.append(np.stack([_kern(s, ang, 6.0) for ang in ASPECTS], axis=1))
    out["pa: marriage+children lots cross-chart"] = _prune(np.hstack(cols))

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 10.  THE TRIPLICITY LORDS OF THE YEAR (Abu Ma'shar, Great Introduction V; al-Biruni § 441).
    #      Three readings: the triplicity lords of the sign profected to for the year; the lords of
    #      the light of the sect (the Sun, under the day proxy); and Abu Ma'shar's division of the
    #      LIFE into three, each third governed by one of the sect light's triplicity lords — here
    #      against the firdaria's nominal 75-year span (25 years a third), which is a stated choice,
    #      since the true division needs a predicted length of life.
    # ════════════════════════════════════════════════════════════════════════════════════════════
    cols = []
    trip = {}
    for who, L, pr in (("o", lo7, prof["o"]), ("y", ly7, prof["y"])):
        ps = pr[1]
        for j in range(3):
            cols.append(_onehot(TRIP[ps, j], 7))                      # lords of the year's sign
        sl = _signof(L[SUN])                                          # the light of the sect (day)
        for j in range(3):
            cols.append(_onehot(TRIP[sl, j], 7))
        fs = _signof(lots_o_day["fortune"] if who == "o" else lots_y_day["fortune"])
        for j in range(3):
            cols.append(_onehot(TRIP[fs, j], 7))
        age = age_o if who == "o" else age_y
        third = np.clip(np.floor(np.mod(age, FIRD_SPAN) / 25.0).astype(int), 0, 2)
        life_lord = TRIP[sl, third]
        cols += [_onehot(third, 3), _onehot(life_lord, 7)]
        trip[who] = (TRIP[ps, 0], TRIP[sl, 0], life_lord)
    cols.append((trip["o"][0] == trip["y"][0]).astype(float)[:, None])
    cols.append((trip["o"][1] == trip["y"][1]).astype(float)[:, None])
    cols.append((trip["o"][2] == trip["y"][2]).astype(float)[:, None])
    cols.append(_onehot(trip["o"][2] * 7 + trip["y"][2], 49))
    out["pa: triplicity lords of the year"] = _prune(np.hstack(cols))

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 11.  AL-BIRUNI'S ASPECT DOCTRINE with APPLICATION and SEPARATION (§§ 447-461).
    #      An aspect holds when the distance from exactitude is within the half-sum of the two
    #      planets' orbs (his "moieties of light", § 458).  It is APPLYING while that distance is
    #      shrinking and SEPARATING once it grows — determined here from the natal longitude SPEEDS
    #      (E.SPD, negative = retrograde), which is what makes the distinction computable at all:
    #      the offset from exact changes at (speed_a - speed_b), so the configuration applies when
    #      offset and relative motion have opposite signs.  Retrogradation is therefore built in.
    # ════════════════════════════════════════════════════════════════════════════════════════════
    d = _wrap(lo7[:, None, :] - ly7[None, :, :])                      # (7, 7, n) signed separation
    rate = so7[:, None, :] - sy7[None, :, :]
    app_cols, sep_cols, counts = [], [], []
    for ang in ASPECTS:
        off = _offset(d, ang)
        moi = MOIETY[:, :, None]
        inorb = np.abs(off) <= moi
        applying = (off * rate) < 0.0
        w = _kern(np.abs(off), 0.0, np.maximum(moi / 2.0, 1.0))
        A = (w * inorb * applying).reshape(49, n).T
        S = (w * inorb * (~applying)).reshape(49, n).T
        app_cols.append(A)
        sep_cols.append(S)
        counts.append(inorb.reshape(49, n).sum(axis=0)[:, None])
        counts.append((inorb & applying).reshape(49, n).sum(axis=0)[:, None])
    cols = app_cols + sep_cols + counts
    out["pa: al-Biruni aspects applying vs separating"] = _prune(np.hstack(cols))

    # ── 12. dexter / sinister, and the same aspects read at three orb widths ─────────────────────
    #     al-Biruni § 452: an aspect cast in the order of the signs is SINISTER (left), against it
    #     DEXTER (right); only sextile, square and trine have the distinction.
    cols = []
    for ang in MINOR_DEX:
        off = _offset(d, ang)
        w = _kern(np.abs(off), 0.0, np.maximum(MOIETY[:, :, None] / 2.0, 1.0))
        sinister = d < 0.0                                            # the younger's body is ahead
        cols.append((w * sinister).reshape(49, n).T)
        cols.append((w * (~sinister)).reshape(49, n).T)
    S = np.abs(d)
    for width in (3.0, 6.0, 9.0):
        for ang in ASPECTS:
            k = _kern(S, ang, width)
            cols.append(k.reshape(49, n).sum(axis=0)[:, None])
            cols.append(k.max(axis=(0, 1))[:, None])
    for ang in ASPECTS:
        k = _kern(S, ang, 6.0)
        cols.append(k.sum(axis=1).T)                                  # per older-planet totals
        cols.append(k.sum(axis=0).T)                                  # per younger-planet totals
    out["pa: al-Biruni dexter/sinister + orb widths"] = _prune(np.hstack(cols))

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 13.  RECEPTION and MUTUAL RECEPTION between the two charts (al-Biruni § 461; Abu Ma'shar).
    #      A planet is RECEIVED by the lord of the sign it stands in — by domicile or by exaltation.
    #      Across two charts: the older's planet a is received by the younger's planet b when b is
    #      the domicile lord (or exaltation lord) of the sign a occupies.  The reception is PERFECT
    #      only if the two are also in aspect and applying, so the gated forms are emitted too.
    # ════════════════════════════════════════════════════════════════════════════════════════════
    sgn_o, sgn_y = _signof(lo7), _signof(ly7)
    dom_o, dom_y = RULER[sgn_o], RULER[sgn_y]                         # (7, n) dispositor codes
    exl_o, exl_y = EXALT[sgn_o], EXALT[sgn_y]
    pb = np.arange(7)[None, :, None]
    dom_oy = (dom_o[:, None, :] == pb).astype(float)                  # (7, 7, n)
    dom_yo = (dom_y[:, None, :] == pb).astype(float)
    exl_oy = (exl_o[:, None, :] == pb).astype(float)
    exl_yo = (exl_y[:, None, :] == pb).astype(float)
    rec_oy = np.clip(dom_oy + exl_oy, 0, 1)
    rec_yo = np.clip(dom_yo + exl_yo, 0, 1)
    mutual = rec_oy * np.transpose(rec_yo, (1, 0, 2))
    inasp = np.zeros((7, 7, n), bool)
    appl = np.zeros((7, 7, n), bool)
    for ang in ASPECTS:
        off = _offset(d, ang)
        io = np.abs(off) <= MOIETY[:, :, None]
        inasp |= io
        appl |= io & ((off * rate) < 0.0)
    cols = [dom_oy.reshape(49, n).T, dom_yo.reshape(49, n).T,
            exl_oy.reshape(49, n).T, exl_yo.reshape(49, n).T,
            mutual.reshape(49, n).T, (mutual * inasp).reshape(49, n).T]
    for M in (rec_oy, rec_yo, mutual):
        cols.append(M.reshape(49, n).sum(axis=0)[:, None])
        cols.append((M * inasp).reshape(49, n).sum(axis=0)[:, None])
        cols.append((M * appl).reshape(49, n).sum(axis=0)[:, None])
    cols.append(np.stack([(exl_o >= 0).sum(axis=0), (exl_y >= 0).sum(axis=0)], axis=1).astype(float))
    out["pa: reception + mutual reception"] = _prune(np.hstack(cols))

    # ════════════════════════════════════════════════════════════════════════════════════════════
    # 14.  THE ALMUTEN by the Ibn Ezra / al-Biruni point score (5 domicile, 4 exaltation,
    #      3 triplicity, 2 bound, 1 face), summed over the places available to us: the Sun, the
    #      Moon, the Lot of Fortune and the prenatal syzygy.  Ibn Ezra's almuten figuris also uses
    #      the ASCENDANT, which this dataset cannot give (module docstring), so this is a four-place
    #      almuten and the syzygy itself is approximated (see _syzygy).  Ties break to the earlier
    #      planet in the order Sun..Saturn.
    # ════════════════════════════════════════════════════════════════════════════════════════════
    cols = []
    alm = {}
    for who, L, lots in (("o", lo7, lots_o_day), ("y", ly7, lots_y_day)):
        places = [L[SUN], L[MOON], lots["fortune"], _syzygy(L[SUN], L[MOON])]
        tot = np.zeros((n, 7))
        for p in places:
            P = _points(p, day=True)
            cols.append(P)
            tot += P
        winner = np.argmax(tot, axis=1)
        alm[who] = winner
        own = np.stack([_points(L[b], day=True)[r, b] for b in range(7)], axis=1)
        cols += [tot, tot / np.maximum(tot.sum(axis=1, keepdims=True), 1e-9),
                 _onehot(winner, 7), own]
    cols.append(_onehot(alm["o"] * 7 + alm["y"], 49))
    cols.append((alm["o"] == alm["y"]).astype(float)[:, None])
    a, b = lo7[alm["o"], r], ly7[alm["y"], r]
    cols.append(np.stack([_kern(_sep(a, b), ang, 6.0) for ang in ASPECTS], axis=1))
    cols.append(_circ(_wrap(a - b)))
    out["pa: almuten point score (Ibn Ezra)"] = _prune(np.hstack(cols))

    return {k: np.ascontiguousarray(np.asarray(v, dtype=np.float64)) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick

    E = load()
    blocks = build(E)
    print(f"TRADITION  {TRADITION}")
    print(f"couples    {E.n}   blocks {len(blocks)}   "
          f"total columns {sum(v.shape[1] for v in blocks.values())}\n")
    bad = 0
    for name, X in blocks.items():
        try:
            assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
            assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
            assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape}"
            assert np.isfinite(X).all(), f"{name}: non-finite values"
            assert X.std(axis=0).max() > 1e-12, f"{name}: all-constant block"
            acc, auc = quick(E, X)
            print(f"  {name:<48} {X.shape[1]:>5} cols   acc {100*acc:5.2f}%   AUC {auc:.4f}")
        except AssertionError as e:
            bad += 1
            print(f"  FAIL {e}")
    names = list(blocks)
    assert len(names) == len(set(names)), "duplicate block names"
    if bad:
        print(f"\n{bad} block(s) failed")
        sys.exit(1)
    print("\nOK")
