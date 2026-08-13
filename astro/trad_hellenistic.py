"""
trad_hellenistic.py — Hellenistic & classical Western doctrine, turned into feature blocks.

SOURCES IMPLEMENTED (each table is cited again at its definition below)

  Ptolemy, Tetrabiblos I.11-12 (qualities of the signs), I.13 (aspects/configurations),
    I.15-16 (commanding & obeying signs; signs of equal power = the antiscia pairs),
    I.17 (domiciles), I.19 (exaltations), I.21 (the bounds "according to the Egyptians"),
    III.4 (Mercury's sect by orientality), IV.5 (marriage).
  Vettius Valens, Anthology I.3 (bounds), II.37-38 (marriage, and the comparison of two
    nativities: luminary contacts, benefic/malefic testimony, reception), IV (the lots).
  Dorotheus of Sidon, Carmen Astrologicum II (triplicity lords by sect; Venus-Saturn contacts
    as hindrance to marriage).
  Paulus Alexandrinus, Introduction ch. 23 (the seven Hermetic lots), ch. 24 (Lot of Marriage
    for men from Saturn to Venus, for women from Venus to Saturn).
  Al-Biruni / Ibn Ezra / Lilly's "Table of Essential Dignities" for the five-fold dignity POINT
    weighting (domicile 5, exaltation 4, triplicity 3, bound 2, face 1) used for the almuten.
    That weighting is medieval, not Hellenistic — it is a scoring of the Hellenistic dignities and
    is labelled as such wherever it is used.

THE TWO PROXIES, STATED PLAINLY (both forced by the data, not chosen)

  1. NO ASCENDANT, SO NO REAL LOTS OR PLACES. Only birth dates are known and every instant is cast
     for 12:00 UT, so there is no Ascendant, Midheaven or house. Every lot below therefore uses a
     PROXY ascendant, and two of them, because the choice changes the answer:
        ASC1 "solar whole-sign": Asc := 0 deg of the Sun's sign (the proxy the project contract
             sanctions; the Sun's sign is treated as the first place, as in a solar-sign chart).
        ASC2 "noon chart": every instant IS noon UT, i.e. local noon on the Greenwich meridian, so
             under the ordinary noon-chart convention the Sun is culminating; MC := Sun and
             Asc := Sun + 90 deg (obliquity and latitude ignored — there is no latitude to use).
     Consequences worth knowing before reading any lot feature: under ASC1 the Lot of Fortune is
     the Moon minus the Sun's position within its sign, and under ASC2 it is simply Moon + 90 deg.
     The lots are still real functions of the chart, but the Ascendant's own contribution — which is
     most of what a lot is for — is absent. Nothing here is a substitute for a timed chart.
     Anything resting on the places themselves is NOT implemented at all (see NOT IMPLEMENTED).

  2. SECT IS UNDECIDABLE. Sect is whether the Sun is above the horizon, which needs a time and a
     place. Under the noon-chart convention of ASC2 every chart would be diurnal, which would make
     sect a constant and hide the doctrine rather than model it. So every sect-dependent quantity is
     computed TWICE — once by the day formula, once by the night formula — and both are emitted,
     together with their difference where that is meaningful. The one sect fact that IS computable
     without a birth time is Mercury's own sect (diurnal when it rises before the Sun, nocturnal
     when it sets after it — Ptolemy III.4, Paulus ch. 15); that is emitted directly.

  3. THE MOON IS UNCERTAIN BY ABOUT +-6 DEG (noon vs the true birth moment). Every lunar feature
     here — sign, bound, face, antiscion, the Moon-based lots, and every aspect involving the Moon —
     inherits that error. Sign-level lunar features are roughly half reliable; the bound (2-12 deg
     wide) and face (10 deg) of the Moon are worse than that. They are built anyway, because the
     doctrine is largely lunar, but they should not be read as precise.

REPRESENTATIONS BUILT OF THE SAME DOCTRINE, deliberately, because they score differently:
  orb kernels at four widths (2, 4, 6, 12 deg) · whole-sign (sign-to-sign) relations as one-hot,
  which is what Hellenistic aspect doctrine actually uses · circular cos/sin of lots and lot
  differences · dignity as one-hot states · dignity as the medieval point score and its almuten ·
  and the tradition's own tallies (Valens-style testimony counts, aversion counts, dignity counts).

NOT IMPLEMENTED, and why (all of them need a birth time or place, or an ephemeris search):
  the Ascendant and the twelve places; the lord of the seventh place (the classical marriage
  significator of Ptolemy IV.5 and Dorotheus II); angularity, and therefore any "in a good place"
  judgement; the almuten figuris in full (it needs the MC and the prenatal syzygy — the syzygy would
  need an ephemeris search this module is not allowed to run); Valens' decennials and
  circumambulations (they start from the Ascendant); planetary hours and the hour-lord; the trutine
  of Hermes; true heliacal phasis (needs the arcus visionis at a latitude — orientality by
  elongation is used instead); primary directions.
"""

import numpy as np

TRADITION = "Hellenistic & classical Western (Ptolemy, Vettius Valens, Dorotheus, Paulus Alexandrinus)"

# ── planet codes for every table in this file ────────────────────────────────────────────────────
# 0 Sun  1 Moon  2 Mercury  3 Venus  4 Mars  5 Jupiter  6 Saturn — the same order as core's first
# seven bodies (E.CLASSICAL), so a table index is also a row index into E.LON[slot][:7].
SUN, MOON, MER, VEN, MAR, JUP, SAT = range(7)
NP = 7

# Domicile rulers by sign, Aries..Pisces — Ptolemy, Tetrabiblos I.17.
DOM = np.array([MAR, VEN, MER, MOON, SUN, MER, VEN, MAR, JUP, SAT, SAT, JUP])
# Exaltation sign and exact degree per planet — Ptolemy I.19.
EX_SIGN = np.array([0, 1, 5, 11, 9, 3, 6])          # Sun 19 Ari, Moon 3 Tau, Mer 15 Vir,
EX_DEG = np.array([19., 3., 15., 27., 28., 15., 21.])  # Ven 27 Pis, Mar 28 Cap, Jup 15 Can, Sat 21 Lib
# Triplicity lords by sect — Dorotheus, Carmen II (the "Dorothean" table Valens also uses):
#   fire  day Sun,   night Jupiter, participating Saturn
#   earth day Venus, night Moon,    participating Mars
#   air   day Saturn,night Mercury, participating Jupiter
#   water day Venus, night Mars,    participating Moon
# element of a sign is sign % 4 (0 fire, 1 earth, 2 air, 3 water), so the pattern repeats every 4.
TRIP_D = np.array([SUN, VEN, SAT, VEN] * 3)
TRIP_N = np.array([JUP, MOON, MER, MAR] * 3)
TRIP_P = np.array([SAT, MAR, JUP, MOON] * 3)

# The bounds/terms "according to the Egyptians" — Ptolemy I.21, Valens I.3. (planet, length) per
# sign in order from 0 deg; every sign sums to exactly 30.
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
    for _p, _l in _row:
        BOUND[_s, _d:_d + _l] = _p
        _d += _l

# Faces (decans) in the Chaldean order, Mars first at 0 Aries, descending — Lilly's face table,
# the same decan-face assignment used from Hellenistic sources onward.
CHALD = np.array([MAR, SUN, VEN, MER, MOON, SAT, JUP])
FACE = np.array([[CHALD[(3 * s + d) % 7] for d in range(3)] for s in range(12)])

# The five Ptolemaic configurations — Tetrabiblos I.13.
ASPECTS = (0.0, 60.0, 90.0, 120.0, 180.0)
# Orb kernel widths. Orb is itself a tradition parameter and the ancients did not fix it, so four
# widths are tried: 2 deg (near-partile, the strictest reading), 4 and 6 deg (moderate), 12 deg
# (the widest classical moiety, Lilly's for the Moon).
WIDTHS = (2.0, 4.0, 6.0, 12.0)

# Whole-sign relations by sign-distance 0..11 (Hellenistic aspect doctrine is sign-to-sign):
#   0 same sign · 2,10 sextile · 3,9 square · 4,8 trine · 6 opposition · 1,5,7,11 AVERSION.
WS_HARM = np.array([1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0], dtype=float)   # conj/sextile/trine
WS_HARD = np.array([0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0], dtype=float)   # square/opposition
WS_AVERSE = np.array([0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1], dtype=float)  # 1,5,7,11 signs apart

BENEFIC = (JUP, VEN)
MALEFIC = (MAR, SAT)
LIGHTS = (SUN, MOON)

# The seven Hermetic lots plus the marriage and children lots. "from A to B" projected from the
# Ascendant means Asc + B - A. Day formula first, night formula is the reverse arc.
#   Fortune   day Sun->Moon              Paulus ch. 23, Valens IV
#   Spirit    day Moon->Sun              Paulus ch. 23
#   Eros      day Spirit->Venus          Paulus ch. 23
#   Necessity day Mercury->Fortune       Paulus ch. 23
#   Courage   day Fortune->Mars          Paulus ch. 23
#   Victory   day Jupiter->Spirit        Paulus ch. 23
#   Nemesis   day Fortune->Saturn        Paulus ch. 23
#   Marriage (men)   Saturn->Venus       Paulus ch. 24, Valens II.38
#   Marriage (women) Venus->Saturn       Paulus ch. 24
#   Children  day Saturn->Jupiter        Paulus ch. 24
LOT_NAMES = ("Fortune", "Spirit", "Eros", "Necessity", "Courage", "Victory", "Nemesis",
             "MarriageM", "MarriageW", "Children")
LOT_CROSS = ("Fortune", "Spirit", "Eros", "MarriageM", "MarriageW", "Children")


# ── small helpers ────────────────────────────────────────────────────────────────────────────────
def _sign(lon):
    return np.floor(np.mod(np.asarray(lon, float), 360.0) / 30.0).astype(np.int64)


def _degin(lon):
    return np.mod(np.asarray(lon, float), 30.0)


def _fin(X):
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[:, None]
    return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


def _prune(X):
    """Finite-ise. Column count is fixed by the code, not the batch — see the note below."""
    X = _fin(X)
    # NO VARIANCE PRUNING HERE, DELIBERATELY. This used to drop columns whose standard deviation was
    # zero in the batch being built, and that made a block's WIDTH a function of the DATA rather than
    # of the code. Two consequences, both silent: a scoring batch (one couple, or ten thousand
    # candidates sharing a fixed partner) has many constant columns, so prediction handed the model a
    # narrower and differently-ordered matrix than training did; and a full run built in row chunks
    # produced chunks of different widths that could not be concatenated. Constant columns are now
    # pruned exactly once, globally, by run.collect, which records `kept_idx` in the manifest so
    # prediction can select the same columns. Width is a function of the code alone.
    return X


def _onehot(idx, k):
    """(m, n) integer codes -> (n, m*k) one-hot, blocks concatenated in m order."""
    flat = np.asarray(idx).reshape(-1, np.asarray(idx).shape[-1]).astype(np.int64)
    m, n = flat.shape
    out = np.zeros((n, m * k))
    rows = np.arange(n)
    for j in range(m):
        out[rows, j * k + np.clip(flat[j], 0, k - 1)] = 1.0
    return out


def _anti(lon):
    """Antiscion: reflection in the solstitial axis (0 Cancer / 0 Capricorn) = 180 - lon.
    Ptolemy I.16's 'signs of equal power'; Lilly's antiscia table (Taurus<->Leo, Aries<->Virgo...)."""
    return np.mod(180.0 - np.asarray(lon, float), 360.0)


def _canti(lon):
    """Contra-antiscion: reflection in the equinoctial axis (0 Aries / 0 Libra) = -lon.
    Ptolemy I.15's 'commanding and obeying' pairs (Aries<->Pisces, Taurus<->Aquarius...)."""
    return np.mod(-np.asarray(lon, float), 360.0)


def _lots(asc, P, day):
    """All ten lots for one chart. `asc` (n,), `P` (7, n) classical longitudes, `day` bool.

    Returns (10, n) in LOT_NAMES order. Sect enters exactly where the tradition puts it: the arc is
    taken in the reverse direction in a night chart. Marriage (men/women) is not sect-reversed —
    Paulus gives it by the native's sex, which we do not know, so BOTH orderings are emitted and the
    older/younger assignment is left to the model.
    """
    S, Mo, Me, V, Ma, J, Sa = (P[i] for i in range(7))
    f = lambda a, b: np.mod(asc + b - a, 360.0)          # "from a to b", projected from the Asc
    fort = f(S, Mo) if day else f(Mo, S)
    spir = f(Mo, S) if day else f(S, Mo)
    eros = f(spir, V) if day else f(V, spir)
    nece = f(Me, fort) if day else f(fort, Me)
    cour = f(fort, Ma) if day else f(Ma, fort)
    vict = f(J, spir) if day else f(spir, J)
    neme = f(fort, Sa) if day else f(Sa, fort)
    marm = f(Sa, V)
    marw = f(V, Sa)
    chil = f(Sa, J) if day else f(J, Sa)
    return np.stack([fort, spir, eros, nece, cour, vict, neme, marm, marw, chil])


def _dig_points(lon, trip):
    """Medieval five-fold dignity POINTS of every planet at position `lon` (n,) -> (7, n).

    domicile 5 · exaltation 4 · triplicity 3 · bound 2 · face 1 (al-Biruni / Ibn Ezra / Lilly's
    Table of Essential Dignities). The dignities themselves are Hellenistic; the weighting is the
    medieval scoring of them, and the almuten is its argmax. `trip` selects the sect column.
    """
    s = _sign(lon)
    d = _degin(lon)
    di = np.clip(np.floor(d).astype(np.int64), 0, 29)
    dom = DOM[s]
    bnd = BOUND[s, di]
    fac = FACE[s, np.clip((d / 10.0).astype(np.int64), 0, 2)]
    tri = trip[s]
    pts = np.zeros((NP, s.shape[0]))
    for p in range(NP):
        pts[p] = (5.0 * (dom == p) + 4.0 * (s == EX_SIGN[p]) + 3.0 * (tri == p)
                  + 2.0 * (bnd == p) + 1.0 * (fac == p))
    return pts


def _pairsep(A, B):
    """All cross separations between two (7, n) longitude tables -> (49, n), row = A-body * 7 + B."""
    return np.abs(_wrap(A[:, None, :] - B[None, :, :])).reshape(-1, A.shape[-1])


def _wrap(d):
    return (np.asarray(d, float) + 180.0) % 360.0 - 180.0


# ── the build ────────────────────────────────────────────────────────────────────────────────────
def build(E):
    n = E.n
    iO, iY, iW = E.SLOT["older"], E.SLOT["younger"], E.SLOT["wedding"]
    LO = E.LON[iO][:NP]                     # (7, n) older's classical bodies
    LY = E.LON[iY][:NP]
    LW = E.LON[iW][:NP]
    CHARTS = (("o", LO), ("y", LY), ("w", LW))
    out = {}

    # ── 1-3. Ptolemaic orb kernels on the two natal charts, cross-aspects (synastry) ─────────────
    # Every one of the 49 ordered body pairs (older's body x younger's body) at all five Ptolemaic
    # configurations. Three orb widths get their own block because the orb IS the parameter under
    # test; the fourth width (12 deg) rides with the wedding chart below.
    sep_xy = _pairsep(LO, LY)                                    # (49, n)
    for w in (2.0, 4.0, 6.0):
        cols = [E.orbkern(sep_xy, a, w).T for a in ASPECTS]      # 5 x (n, 49)
        out[f"hel: synastry ptolemaic orbs {w:g}deg"] = _prune(np.hstack(cols))

    # ── 4. the wedding chart's OWN aspects, all four widths ──────────────────────────────────────
    iu, ju = np.triu_indices(NP, k=1)
    sep_w = np.abs(_wrap(LW[iu] - LW[ju]))                       # (21, n)
    cols = [E.orbkern(sep_w, a, w).T for w in WIDTHS for a in ASPECTS]
    out["hel: wedding chart ptolemaic orbs 2/4/6/12deg"] = _prune(np.hstack(cols))

    # ── 5. whole-sign relations, dexter and sinister kept apart ──────────────────────────────────
    # Hellenistic aspect doctrine is sign-to-sign, and the direction matters (a right-hand/dexter
    # trine is not a left-hand/sinister one — Valens I.). Signed sign-distance, 12 classes, for all
    # 49 cross pairs. This is the same doctrine as blocks 1-3 in a purely discrete representation.
    sgO, sgY, sgW = _sign(LO), _sign(LY), _sign(LW)
    dist_xy = np.mod(sgY[None, :, :] - sgO[:, None, :], 12).reshape(-1, n)   # (49, n)
    out["hel: whole-sign relations dexter/sinister"] = _prune(_onehot(dist_xy, 12))

    # ── 6. aversion and configuration tallies (the tradition's own counting) ─────────────────────
    # A pair is AVERSE when the signs are 1, 5, 7 or 11 apart: they do not behold one another at
    # all. Counts over the whole cross-grid, over the marriage significators only, and inside the
    # wedding chart, plus the per-pair flags for the pairs Valens actually names.
    tal = []
    cnt12 = np.stack([(dist_xy == d).sum(axis=0) for d in range(12)]).T.astype(float)
    tal.append(cnt12)                                            # 12: how many pairs at each dist
    tal.append(WS_HARM[dist_xy].sum(axis=0)[:, None])
    tal.append(WS_HARD[dist_xy].sum(axis=0)[:, None])
    tal.append(WS_AVERSE[dist_xy].sum(axis=0)[:, None])
    key = (SUN, MOON, VEN, MAR)                                  # the marriage significators
    sub = np.mod(sgY[np.array(key)][None, :, :] - sgO[np.array(key)][:, None, :], 12).reshape(-1, n)
    tal.append(np.stack([(sub == d).sum(axis=0) for d in range(12)]).T.astype(float))
    tal.append(WS_AVERSE[sub].sum(axis=0)[:, None])
    tal.append(WS_HARM[sub].sum(axis=0)[:, None])
    dist_w = np.mod(sgW[ju] - sgW[iu], 12)
    tal.append(np.stack([(dist_w == d).sum(axis=0) for d in range(12)]).T.astype(float))
    tal.append(WS_AVERSE[dist_w].sum(axis=0)[:, None])
    named = ((SUN, MOON), (MOON, SUN), (SUN, SUN), (MOON, MOON), (VEN, MAR), (MAR, VEN),
             (VEN, VEN), (VEN, SAT), (SAT, VEN), (MOON, SAT), (MOON, VEN), (VEN, MOON))
    for a, b in named:
        d = np.mod(sgY[b] - sgO[a], 12)
        tal.append(np.stack([WS_HARM[d], WS_HARD[d], WS_AVERSE[d], (d == 0).astype(float)], 1))
    out["hel: aversion & whole-sign tallies"] = _prune(np.hstack([_fin(t) for t in tal]))

    # ── 7. essential dignity STATES, one-hot, per chart per body ──────────────────────────────────
    # domicile · exaltation (by sign, and partile within 3 deg of the exact degree) · detriment ·
    # fall · its own bound lord · its own face lord · day / night / participating triplicity lord.
    dig = []
    for tag, L in CHARTS:
        s, d = _sign(L), _degin(L)
        di = np.clip(np.floor(d).astype(np.int64), 0, 29)
        for p in range(NP):
            sp, dp, dip = s[p], d[p], di[p]
            fl = [
                (DOM[sp] == p).astype(float),                            # in its own domicile
                (sp == EX_SIGN[p]).astype(float),                        # in its exaltation sign
                ((sp == EX_SIGN[p]) & (np.abs(dp - EX_DEG[p]) <= 3.0)).astype(float),
                (DOM[np.mod(sp + 6, 12)] == p).astype(float),            # detriment (opposite sign)
                (sp == np.mod(EX_SIGN[p] + 6, 12)).astype(float),        # fall
                (BOUND[sp, dip] == p).astype(float),                     # its own Egyptian bound
                (FACE[sp, np.clip((dp / 10).astype(np.int64), 0, 2)] == p).astype(float),
                (TRIP_D[sp] == p).astype(float),
                (TRIP_N[sp] == p).astype(float),
                (TRIP_P[sp] == p).astype(float),
            ]
            dig.append(np.stack(fl, axis=1))
        # per-chart counts: how many bodies dignified, how many debilitated
        dgn = sum((DOM[s[p]] == p).astype(float) + (s[p] == EX_SIGN[p]).astype(float)
                  for p in range(NP))
        dbl = sum((DOM[np.mod(s[p] + 6, 12)] == p).astype(float)
                  + (s[p] == np.mod(EX_SIGN[p] + 6, 12)).astype(float) for p in range(NP))
        dig.append(np.stack([dgn, dbl, dgn - dbl], axis=1))
    out["hel: essential dignity states"] = _prune(np.hstack([_fin(x) for x in dig]))

    # ── 8. dignity POINTS and the almuten of each body's degree ──────────────────────────────────
    alm = []
    for tag, L in CHARTS:
        for trip, lab in ((TRIP_D, "day"), (TRIP_N, "night")):
            own = np.zeros((n, NP))
            for p in range(NP):
                pts = _dig_points(L[p], trip)                    # (7, n) points of every planet
                own[:, p] = pts[p]                               # the body's own dignity score
                # the almuten OF EVERY BODY's degree: which planet holds most dignity there
                alm.append(_onehot(np.argmax(pts, axis=0)[None, :], NP))
                if p in (SUN, MOON, VEN):                        # full point vector for the lights
                    alm.append(pts.T)
            alm.append(own)
            alm.append(own.sum(axis=1, keepdims=True))
    # almuten over the significators we actually have (Sun, Moon, proxy Asc, Lot of Fortune).
    # NOT the full almuten figuris: the MC and the prenatal syzygy are unavailable (see docstring).
    for tag, L in CHARTS:
        asc1 = 30.0 * np.floor(L[SUN] / 30.0)
        fort = _lots(asc1, L, True)[0]
        tot = sum(_dig_points(x, TRIP_D) for x in (L[SUN], L[MOON], asc1, fort))
        alm.append(tot.T)
        alm.append(_onehot(np.argmax(tot, axis=0)[None, :], NP))
    out["hel: dignity points & almuten"] = _prune(np.hstack([_fin(x) for x in alm]))

    # ── 9. sect (proxied), triplicity lords by sect, planetary sect ───────────────────────────────
    sect = []
    for tag, L in CHARTS:
        # Mercury's sect — the only computable one: oriental (rises before the Sun) = diurnal.
        el = _wrap(L[MER] - L[SUN])
        sect.append(np.stack([(el < 0).astype(float), np.cos(np.deg2rad(el)),
                              np.sin(np.deg2rad(el))], axis=1))
        # a planet in a sign of its own sect: diurnal planets (Sun, Jup, Sat) in masculine signs,
        # nocturnal (Moon, Ven, Mar) in feminine — the computable half of hayz (Ptolemy I.12, III.4).
        # Mercury is "common" and takes the sect of its orientality, which is the flag just above;
        # in this gender test it is grouped with the nocturnal planets.
        s = _sign(L)
        masc = (np.mod(s, 2) == 0).astype(float)
        diur = np.array([1., 0., 0., 0., 0., 1., 1.])
        sect.append(np.stack([np.abs(diur[p] - (1.0 - masc[p])) for p in range(NP)], axis=1))
        # triplicity lords of the Sun's and the Moon's sign, both sects, as identities and as
        # whether that lord beholds its own light by whole sign
        for b in (SUN, MOON):
            sect.append(_onehot(np.mod(s[b], 4)[None, :], 4))              # element of the sign
            for trip in (TRIP_D, TRIP_N, TRIP_P):
                lord = trip[s[b]]
                sect.append(_onehot(lord[None, :], NP))
                dd = np.mod(s[lord, np.arange(n)] - s[b], 12)
                sect.append(np.stack([WS_HARM[dd], WS_HARD[dd], WS_AVERSE[dd]], axis=1))
    # cross-chart: does the older's day/night triplicity lord of the Sun behold the younger's Sun
    for trip in (TRIP_D, TRIP_N):
        for A, B, sa, sb in ((LO, LY, sgO, sgY), (LY, LO, sgY, sgO)):
            lord = trip[sa[SUN]]
            dd = np.mod(sb[SUN] - sa[lord, np.arange(n)], 12)
            sect.append(np.stack([WS_HARM[dd], WS_HARD[dd], WS_AVERSE[dd]], axis=1))
    out["hel: sect proxy, triplicity lords & planetary sect"] = _prune(
        np.hstack([_fin(x) for x in sect]))

    # ── 10. antiscia and contra-antiscia contacts ────────────────────────────────────────────────
    # An antiscion contact is a conjunction with the reflected degree (and the opposition to it is
    # the contra-antiscion contact). Traditionally tight, so 1.5 and 3 deg kernels only.
    ant = []
    for refl in (_anti, _canti):
        sep = _pairsep(refl(LO), LY)                              # older's reflection vs younger
        for w in (1.5, 3.0):
            ant.append(E.orbkern(sep, 0.0, w).T)
        ant.append((sep <= 2.0).sum(axis=0)[:, None].astype(float))
        sep2 = _pairsep(refl(LY), LO)                             # the other direction
        ant.append(E.orbkern(sep2, 0.0, 3.0).T)
        ant.append((sep2 <= 2.0).sum(axis=0)[:, None].astype(float))
        sepw = np.abs(_wrap(refl(LW)[iu] - LW[ju]))               # inside the wedding chart
        ant.append(E.orbkern(sepw, 0.0, 3.0).T)
        # sign-level: Ptolemy I.15-16 'commanding/obeying' and 'equal power' pairs of the lights
        ds = np.mod(_sign(refl(LO))[None, :, :] - sgY[:, None, :], 12).reshape(-1, n)
        ant.append((ds == 0).sum(axis=0)[:, None].astype(float))
    out["hel: antiscia & contra-antiscia contacts"] = _prune(np.hstack([_fin(x) for x in ant]))

    # ── 11. the Hermetic lots, circular ──────────────────────────────────────────────────────────
    # Both proxy ascendants, both sect formulae, all three charts. cos/sin so a linear model can
    # use them; the same lots are used discretely in block 12.
    ASC = {}
    for tag, L in CHARTS:
        ASC[tag] = (30.0 * np.floor(L[SUN] / 30.0), np.mod(L[SUN] + 90.0, 360.0))
    LOTS = {}
    for tag, L in CHARTS:
        for ai, asc in enumerate(ASC[tag]):
            for day in (True, False):
                LOTS[(tag, ai, day)] = _lots(asc, L, day)         # (10, n)
    lot = []
    for k in sorted(LOTS, key=lambda t: (t[0], t[1], not t[2])):
        r = np.deg2rad(LOTS[k])
        lot.append(np.cos(r).T)
        lot.append(np.sin(r).T)
    # the two partners' same-named lots against each other (sin keeps the older/younger direction)
    for ai in (0, 1):
        for day in (True, False):
            d = np.deg2rad(_wrap(LOTS[("o", ai, day)] - LOTS[("y", ai, day)]))
            lot.append(np.cos(d).T)
            lot.append(np.sin(d).T)
    out["hel: hermetic lots (circular)"] = _prune(np.hstack([_fin(x) for x in lot]))

    # ── 12. lot cross-contacts: each partner's lots against the other's planets ───────────────────
    li = [LOT_NAMES.index(x) for x in LOT_CROSS]
    xc = []
    for src, dst, Ld in (("o", "y", LY), ("y", "o", LO)):
        for day in (True, False):
            P = LOTS[(src, 0, day)][li]                           # (6, n) ASC1 lots
            sep = np.abs(_wrap(P[:, None, :] - Ld[None, :, :])).reshape(-1, n)   # (42, n)
            xc.append(E.orbkern(sep, 0.0, 6.0).T)
            xc.append(E.orbkern(sep, 180.0, 6.0).T)
            xc.append(E.orbkern(sep, 120.0, 6.0).T)
            ds = np.mod(_sign(Ld)[None, :, :] - _sign(P)[:, None, :], 12).reshape(-1, n)
            xc.append((ds == 0).astype(float).T)                  # same sign = whole-sign contact
            xc.append(WS_HARM[ds].sum(axis=0)[:, None])
            xc.append(WS_HARD[ds].sum(axis=0)[:, None])
    out["hel: lot cross-contacts"] = _prune(np.hstack([_fin(x) for x in xc]))

    # ── 13. Valens-style testimony count — the tradition's OWN synastry number ────────────────────
    # Valens Anthology II.37-38 compares two nativities by counting testimonies rather than
    # measuring anything: the lights beholding one another, benefics or malefics beholding the
    # other's lights, Venus with Mars, Venus hindered by Saturn (Dorotheus II), reception between
    # the charts, and the marriage lot beheld by benefic or malefic. Whole-sign throughout, because
    # that is how the testimony is taken. Emitted per component AND as the tallies and the net.
    tes = []
    def ws(a, b, sa, sb):
        return np.mod(sb[b] - sa[a], 12)

    ben_t = np.zeros(n)
    mal_t = np.zeros(n)
    for sa, sb, A, B in ((sgO, sgY, LO, LY), (sgY, sgO, LY, LO)):
        # lights of one with the lights of the other
        for a in LIGHTS:
            for b in LIGHTS:
                d = ws(a, b, sa, sb)
                tes.append(np.stack([WS_HARM[d], WS_HARD[d], WS_AVERSE[d]], axis=1))
                ben_t += WS_HARM[d]
                mal_t += WS_HARD[d]
        # benefics of one to the lights of the other; malefics likewise
        bl = sum(WS_HARM[ws(p, b, sa, sb)] for p in BENEFIC for b in LIGHTS)
        ml = sum(WS_HARD[ws(p, b, sa, sb)] for p in MALEFIC for b in LIGHTS)
        mc = sum(WS_HARM[ws(p, b, sa, sb)] for p in MALEFIC for b in LIGHTS)
        tes.append(np.stack([bl, ml, mc], axis=1))
        ben_t += bl
        mal_t += ml
        # Venus with Mars (desire), Venus with Saturn (hindrance, Dorotheus II)
        for p, q, sgn in ((VEN, MAR, +1), (VEN, SAT, -1), (VEN, JUP, +1), (MOON, VEN, +1)):
            d = ws(p, q, sa, sb)
            tes.append(np.stack([WS_HARM[d], WS_HARD[d], WS_AVERSE[d]], axis=1))
            if sgn > 0:
                ben_t += WS_HARM[d]
                mal_t += WS_HARD[d]
            else:
                mal_t += WS_HARM[d] + WS_HARD[d]
        # reception: A's planet stands in a sign B's planet rules, and the reverse (oikodektor)
        rec = np.zeros(n)
        for p in range(NP):
            for q in range(NP):
                rec += ((DOM[sa[p]] == q) & (DOM[sb[q]] == p)).astype(float)
        tes.append(rec[:, None])
        ben_t += rec
        # the marriage lot of one, beheld by the other's benefics / malefics. Both Paulus orderings
        # (men's and women's) and both sect formulae, since neither sex nor sect is known.
        for lname in ("MarriageM", "MarriageW"):
            j = LOT_NAMES.index(lname)
            tag = "o" if sa is sgO else "y"
            for day in (True, False):
                lot_s = _sign(LOTS[(tag, 0, day)][j])
                b_ = sum(WS_HARM[np.mod(sb[p] - lot_s, 12)] for p in BENEFIC)
                m_ = sum(WS_HARD[np.mod(sb[p] - lot_s, 12)] for p in MALEFIC)
                tes.append(np.stack([b_, m_, WS_AVERSE[np.mod(sb[SUN] - lot_s, 12)]], axis=1))
                if day:
                    ben_t += b_
                    mal_t += m_
        # antiscia contact between the significators (Ptolemy I.16 'seeing' by equal power)
        sep = np.abs(_wrap(_anti(A[np.array((SUN, MOON, VEN, MAR))])[:, None, :]
                           - B[np.array((SUN, MOON, VEN, MAR))][None, :, :])).reshape(-1, n)
        na = (sep <= 2.0).sum(axis=0).astype(float)
        tes.append(na[:, None])
        ben_t += na
    tes.append(np.stack([ben_t, mal_t, ben_t - mal_t,
                         (ben_t - mal_t) / np.maximum(ben_t + mal_t, 1.0)], axis=1))
    out["hel: Valens synastry testimony count"] = _prune(np.hstack([_fin(x) for x in tes]))

    # ── 14. qualities of the signs, and the planets' solar phase ──────────────────────────────────
    # Ptolemy I.11-12: masculine/feminine, tropical, solid (fixed), bicorporeal — the last is his
    # own marriage indication (bicorporeal signs give more than one marriage, Tetrabiblos IV.5).
    # Then the classical conditions of a planet with respect to the Sun: combust, under the beams,
    # cazimi, retrograde, oriental/occidental. Heliacal phasis proper needs a latitude (see
    # docstring) so orientality is by elongation only.
    qual = []
    trop = np.isin(np.arange(12), [0, 3, 6, 9]).astype(float)
    solid = np.isin(np.arange(12), [1, 4, 7, 10]).astype(float)
    bicorp = np.isin(np.arange(12), [2, 5, 8, 11]).astype(float)
    for (tag, L), slot in zip(CHARTS, (iO, iY, iW)):
        s = _sign(L)
        for p in (SUN, MOON, VEN, MAR, SAT):
            sp = s[p]
            qual.append(np.stack([(np.mod(sp, 2) == 0).astype(float), trop[sp], solid[sp],
                                  bicorp[sp]], axis=1))
            qual.append(_onehot(np.mod(sp, 4)[None, :], 4))
        for p in (SUN, MOON):
            qual.append(_onehot(s[p][None, :], 12))
        for p in (MOON, MER, VEN, MAR, JUP, SAT):
            el = _wrap(L[p] - L[SUN])
            ael = np.abs(el)
            spd = E.SPD[slot, p]
            qual.append(np.stack([
                (ael < 8.5).astype(float),           # combust
                (ael < 17.0).astype(float),          # under the Sun's beams
                (ael < 0.2833).astype(float),        # cazimi (17 arcminutes)
                (spd < 0).astype(float),             # retrograde
                (np.abs(spd) < 0.05).astype(float),  # near a station
                (el < 0).astype(float),              # oriental / matutine
                np.cos(np.deg2rad(el)), np.sin(np.deg2rad(el)),
            ], axis=1))
    out["hel: sign qualities & solar phase"] = _prune(np.hstack([_fin(x) for x in qual]))

    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick

    E = load()
    B = build(E)
    total = 0
    bad = []
    for name, X in B.items():
        try:
            assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
            assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
            assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
            assert np.isfinite(X).all(), f"{name}: non-finite values"
            assert X.std(axis=0).max() > 1e-12, f"{name}: all-constant block"
            assert name.startswith("hel: "), f"{name}: missing tradition tag"
        except AssertionError as e:
            bad.append(str(e))
            continue
        total += X.shape[1]
    assert len(set(B)) == len(B), "duplicate block names"
    if bad:
        for b in bad:
            print("FAIL", b)
        sys.exit(1)
    print(f"{TRADITION}\n{len(B)} blocks, {total} columns, n={E.n}\n")
    for name, X in B.items():
        acc, auc = quick(E, X)
        print(f"  {name:<52} {X.shape[1]:>5} cols   acc {100*acc:5.2f}%   AUC {auc:.4f}")
    print("\nOK")
