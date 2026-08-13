"""
trad_modern_western.py — Modern & psychological Western astrology.

WHAT THIS FAMILY CLAIMS, AND WHERE EACH RULE COMES FROM

  ELEMENT AND MODALITY BALANCE.  The modern textbook reads a chart first as a distribution over the
  four elements (fire, earth, air, water) and the three modalities/qualities (cardinal, fixed,
  mutable), with the bodies WEIGHTED rather than counted.  Two published weightings are implemented
  side by side because they disagree and the disagreement is itself informative:
    - March & McEvers, "The Only Way to Learn Astrology" vol. 1, chapter on the elements and
      qualities: Sun 3, Moon 3, Ascendant 3, Mercury 2, Venus 2, Mars 2, every remaining planet 1,
      Midheaven 1.
    - Arroyo, "Astrology, Psychology and the Four Elements" (1975): the Sun, Moon and Ascendant
      carry the personality; the trans-Saturnian planets are read collectively and weigh little.
  Element from sign index s (0 = Aries) is s mod 4 (fire, earth, air, water) and modality is
  s mod 3 (cardinal, fixed, mutable) — the standard cycle, exact, no table needed.
  ELEMENT COMPATIBILITY, the tradition's own tally: same element harmonious (+2); fire with air and
  earth with water compatible (+1); fire with earth and air with water uneasy (-1); fire with water
  and air with earth opposed (-2).  Same modality is friction (square/opposition by sign), different
  modality is easier — both are emitted as counted tallies, not as prose.
  SUN-SIGN COMPATIBILITY GRID.  The popular-modern grid ranks the sign-to-sign angle: trine best,
  sextile next, conjunction (same sign) good, opposition the "attraction of opposites", square and
  quincunx hardest (Linda Goodman, "Love Signs", 1978; March & McEvers vol. 1 on the aspects between
  signs).  Implemented exactly as the folded sign distance 0..6 mapped to 3,1,4,0,5,0,2.

  THE SYNASTRY POINT SCORE, the number this tradition actually computes.  Every cross-aspect between
  the two natal charts is scored value x weight(body A) x weight(body B) x orb taper, and summed.
  Body weights (Sun 4, Moon 4, Venus 3, Mars 3, Mercury 2, Jupiter 2, Saturn 2, Uranus/Neptune/Pluto
  1) and aspect values (conjunction +4, trine +3, sextile +2, opposition -2, square -3, quincunx -1,
  semisextile +1, semisquare -1, sesquiquadrate -1) are the modern textbook consensus as codified in
  computerised compatibility reports and in March & McEvers vol. 3 ("Horoscope Analysis") on
  synastry; the linear orb taper (1 at exact, 0 at the orb limit) is Hand's strength-by-orb rule
  ("Horoscope Symbols", ch. on aspects).  Orbs: 8 deg for conjunction/opposition/trine, 7 for square,
  6 for sextile, 3 for quincunx and semisextile, 2 for the octiles.  The total, its positive and
  negative halves, their ratio, the per-aspect subtotals and the per-body subtotals are all emitted,
  plus a variant with Juno weighted 3 as an eleventh body.

  ASPECT PATTERNS AS DETECTED CONFIGURATIONS (Bil Tierney, "Dynamics of Aspect Analysis", 1983;
  Robert Hand, "Horoscope Symbols").  Definitions implemented literally:
    grand trine        three bodies mutually trine
    T-square           an opposition whose two ends both square a third body (the apex)
    grand cross        two oppositions square each other — four bodies, four squares
    yod                a sextile whose two ends are both quincunx a third body (the apex)
    kite               a grand trine plus a fourth body opposing one member and sextiling the other two
    mystic rectangle   two oppositions joined by two sextiles and two trines
    stellium           three or more bodies within one sign, or piled inside a narrow arc
  Each is detected in BOTH natal charts, in the WEDDING chart, ACROSS the two natals (a configuration
  is only counted as cross-chart when it draws bodies from both people), and in the midpoint
  composite.  Two representations of every pattern: a hard count at the tradition's orb, and a soft
  product-of-orb-kernels strength, because the hard count is nearly always 0 or 1 and the soft one is
  continuous.

  ASTEROID SYNASTRY, which is where this tradition has the most to say about marriage specifically.
  JUNO (3 Juno) is the marriage asteroid — the wife of Jupiter, read for the committed partner and
  the terms of the commitment (Demetra George, "Asteroid Goddesses", 1986; Batya Stark; Zane Stein
  on the marriage asteroids).  Juno to the partner's Sun, Moon, Venus, Mars and Juno is the classic
  marriage indicator, and CERES (nurture, food, children, the mother-bond) is read the same way.
  PALLAS (strategy, the mind), VESTA (dedication, chastity/service) and CHIRON (the wound and the
  healing) follow George's readings; the LILITH point here is the mean lunar apogee, the Black Moon
  Lilith of modern practice (NOT asteroid 1181 Lilith — the two are routinely confused and only the
  Black Moon is in this ephemeris).  Because these rules are directional ("HER Juno on HIS Sun" is
  not the same statement as the reverse), every asteroid contact is emitted in both orderings.

  VENUS-MARS AND SUN-MOON CROSS-CONTACTS.  The two axes every modern synastry text opens with:
  Venus-Mars for attraction, Sun-Moon for the "inner marriage".  All sixteen ordered pairs among
  {Sun, Moon, Venus, Mars} across the two charts, by every classical (Ptolemaic) aspect plus the
  modern minors, at two orb widths, with the continuous orb tightness to the nearest aspect and the
  circular encoding of the signed difference.
  THE SUN/MOON MIDPOINT.  Ebertin's "Ehe-Achse" (marriage axis) and its modern-textbook descendant:
  a partner's planet standing ON your Sun/Moon midpoint is the marriage signature.  The near
  midpoint is used (the one inside the shorter arc), hard aspects only (conjunction, opposition,
  square) and tight orbs (1.5 and 3 deg), which is how the doctrine is stated.

  THE COMPOSITE AND THE DAVISON.  The midpoint composite takes the near midpoint of each pair of
  like bodies; the Davison relationship chart is a real chart cast for the midpoint in time between
  the two births.  Modern practice genuinely disputes which is correct (Hand, "Planets in
  Composite", argues the composite; Davison and his followers argue the real chart), so BOTH are
  built as separate blocks and their disagreement — the body-by-body separation between the two
  charts — is emitted as features of its own.

  PROGRESSED SYNASTRY.  Secondary progressions, a day for a year, progressed to the wedding date:
  each partner's progressed chart against the other's natal, and progressed against progressed.
  Progression orbs are tight in modern practice (1 to 3 deg), which is what is used.

  SOLAR RETURN.  The Sun's return nearest the wedding for each partner: the return position is by
  definition the natal Sun, so what is computable and informative is WHEN the return falls relative
  to the wedding — how far into the solar-return year the marriage happens, and how far apart the
  two partners' return dates are.

  SABIAN SYMBOLS.  Marc Edmund Jones and Elsie Wheeler, 1925 (Jones, "The Sabian Symbols in
  Astrology", 1953; Rudhyar, "An Astrological Mandala", 1973).  One symbol per whole degree of the
  zodiac, so the encoding is a 360-way one-hot of floor(longitude).  Jones's coarser groupings — the
  72 five-degree pentads and the 36 decanates — are emitted for points where 360 bins would be too
  sparse or too uncertain to mean anything.

  RETROGRADE VENUS AND MARS.  Modern practice reads a retrograde Venus or Mars at birth as a
  redirection of the relating and desiring functions inward, and treats marrying under a retrograde
  Venus as inauspicious (this is the one piece of electional lore modern astrology kept).  Speed sign
  is exact in this ephemeris, so these flags are among the most reliable features in the module.

THE HARD DATA LIMIT AND EXACTLY HOW IT LANDS HERE

  Only birth DATES are known; every chart is cast for 12:00 UT with no place.  Consequences, each
  handled explicitly rather than papered over:

    NO ASCENDANT, NO MIDHEAVEN, NO HOUSES.  The March & McEvers element weighting assigns 3 points to
    the Ascendant and 1 to the Midheaven; both are DROPPED here and the remaining planetary weights
    are used unchanged.  This is a documented proxy: it makes the balance vector purely planetary, so
    a chart whose Ascendant would have tipped it (say) fire-dominant may read otherwise.  Nothing
    house-based is attempted at all — no composite Ascendant, no solar-return Ascendant, no Vertex,
    no Part of Marriage, no progressed angles.
    THE MOON IS UNCERTAIN BY ROUGHLY +-6 DEGREES.  That is a fifth of a sign, so every lunar
    sign-level feature here is about half reliable and lunar Sabian DEGREE bins would be pure noise.
    The Moon therefore appears at 360-bin resolution nowhere: it gets decanates (10 deg) at most.
    Sun/Moon midpoints inherit half the lunar error (+-3 deg), which is why the tight-orb midpoint
    kernels are emitted at 1.5 AND 3 degrees rather than at 1 degree alone.
    THE DAVISON CHART IS TIME-MIDPOINT ONLY.  A true Davison chart uses the geographic midpoint as
    well, which needs birthplaces this dataset does not carry.  Slot 5 is the real midpoint in time,
    which fixes every planet exactly; only the angles and houses of the Davison chart are lost, and
    those are not used anywhere here.
    THE SOLAR RETURN CHART'S PLANETS ARE NOT EMITTED.  The return instant is not one of the six
    ephemeris slots and this module is not permitted extra ephemeris I/O, so only the return's TIMING
    (exact, from the Sun's own tropical motion) is used.  Extrapolating the return chart's Moon from
    the wedding Moon would carry a 10-degree-plus error and is deliberately not done.
"""

import itertools
import numpy as np

TRADITION = "Modern & psychological Western (element balance, aspect patterns, asteroid synastry, composite)"

# ── small exact helpers ─────────────────────────────────────────────────────────────────────────
def _wrap(d):
    """Signed angular difference in (-180, 180]."""
    return (np.asarray(d, dtype=np.float64) + 180.0) % 360.0 - 180.0


def _sep(a, b):
    """Absolute separation in [0, 180]."""
    return np.abs(_wrap(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)))


def _kern(sep, angle, width):
    """Gaussian aspect kernel, 1 at exact — same definition as E.orbkern."""
    return np.exp(-0.5 * ((np.asarray(sep, dtype=np.float64) - angle) / width) ** 2)


def _mid(a, b):
    """The NEAR midpoint of two longitudes: the one inside the shorter arc."""
    a = np.asarray(a, dtype=np.float64)
    return np.mod(a + 0.5 * _wrap(np.asarray(b, dtype=np.float64) - a), 360.0)


def _sgn(lon):
    """Sign index 0..11, 0 = Aries."""
    return (np.floor(np.mod(np.asarray(lon, dtype=np.float64), 360.0) / 30.0).astype(np.int64)) % 12


def _onehot(idx, k):
    idx = np.asarray(idx, dtype=np.int64) % k
    M = np.zeros((idx.shape[0], k), dtype=np.float64)
    M[np.arange(idx.shape[0]), idx] = 1.0
    return M


def _pack(parts, n):
    out = []
    for p in parts:
        a = np.asarray(p, dtype=np.float64)
        if a.ndim == 1:
            a = a[:, None]
        assert a.ndim == 2 and a.shape[0] == n, f"bad part shape {a.shape}"
        out.append(a)
    return np.hstack(out)


def _fin(X):
    X = np.asarray(X, dtype=np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return np.ascontiguousarray(np.clip(X, -1e9, 1e9), dtype=np.float64)


def _circ(x):
    r = np.deg2rad(np.asarray(x, dtype=np.float64))
    return np.column_stack([np.cos(r), np.sin(r)])


# ── the tradition's constants ───────────────────────────────────────────────────────────────────
# March & McEvers vol.1: Sun 3, Moon 3, Asc 3, Mercury 2, Venus 2, Mars 2, other planets 1, MC 1.
# Asc and MC need a birth time -> dropped (see the module docstring).
W_MARCH = {"Sun": 3.0, "Moon": 3.0, "Mercury": 2.0, "Venus": 2.0, "Mars": 2.0, "Jupiter": 1.0,
           "Saturn": 1.0, "Uranus": 1.0, "Neptune": 1.0, "Pluto": 1.0}
# Arroyo: Sun/Moon/Asc dominant, personal planets next, outers barely.
W_ARROYO = {"Sun": 4.0, "Moon": 4.0, "Mercury": 1.0, "Venus": 2.0, "Mars": 2.0, "Jupiter": 1.0,
            "Saturn": 1.0, "Uranus": 0.5, "Neptune": 0.5, "Pluto": 0.5}

# element relation tally, the textbook grid (same +2, fire/air & earth/water +1, uneasy -1, opposed -2)
ELEM_TABLE = np.array([[2.0, -1.0, 1.0, -2.0],     # fire  vs fire earth air water
                       [-1.0, 2.0, -2.0, 1.0],     # earth
                       [1.0, -2.0, 2.0, -1.0],     # air
                       [-2.0, 1.0, -1.0, 2.0]])    # water
# sun-sign grid by folded sign distance 0..6: conj 3, semisextile 1, sextile 4, square 0,
# trine 5, quincunx 0, opposition 2  (Goodman "Love Signs"; March & McEvers vol.1)
SIGNGRID = np.array([3.0, 1.0, 4.0, 0.0, 5.0, 0.0, 2.0])

# the synastry point score
SYN_W = {"Sun": 4.0, "Moon": 4.0, "Venus": 3.0, "Mars": 3.0, "Mercury": 2.0, "Jupiter": 2.0,
         "Saturn": 2.0, "Uranus": 1.0, "Neptune": 1.0, "Pluto": 1.0}
SYN_ASP = [("conjunction", 0.0, 8.0, 4.0), ("opposition", 180.0, 8.0, -2.0),
           ("trine", 120.0, 8.0, 3.0), ("square", 90.0, 7.0, -3.0), ("sextile", 60.0, 6.0, 2.0),
           ("quincunx", 150.0, 3.0, -1.0), ("semisextile", 30.0, 3.0, 1.0),
           ("semisquare", 45.0, 2.0, -1.0), ("sesquiquadrate", 135.0, 2.0, -1.0)]

PTOL = [0.0, 60.0, 90.0, 120.0, 180.0]                                   # the classical five
MODERN_ANGLES = [0.0, 30.0, 45.0, 60.0, 72.0, 90.0, 120.0, 135.0, 150.0, 180.0]
SOLAR_DEG_PER_DAY = 360.0 / 365.2425                                     # mean tropical motion

# pattern aspects: name -> (angle, hard orb).  Modern textbook orbs, tighter for the minors.
PAT_ASP = {"cnj": (0.0, 8.0), "sxt": (60.0, 6.0), "sq": (90.0, 7.0),
           "tri": (120.0, 8.0), "qcx": (150.0, 3.0), "opp": (180.0, 8.0)}


# ── generic aspect grids ────────────────────────────────────────────────────────────────────────
def _cross_grid(A, B, angles, widths, tight=True, circ=False):
    """Kernels for every ordered pair between A (mA, n) and B (mB, n)."""
    ang = np.asarray(angles, dtype=np.float64)
    cols = []
    for i in range(A.shape[0]):
        for j in range(B.shape[0]):
            d = _wrap(A[i] - B[j])
            s = np.abs(d)
            for a in angles:
                for w in widths:
                    cols.append(_kern(s, a, w))
            if tight:
                cols.append(np.min(np.abs(s[None, :] - ang[:, None]), axis=0))
            if circ:
                cols.append(np.cos(np.deg2rad(d)))
                cols.append(np.sin(np.deg2rad(d)))
    return cols


def _self_grid(L, angles, widths, tight=True):
    """Kernels for every unordered pair inside one chart, L = (m, n)."""
    ang = np.asarray(angles, dtype=np.float64)
    cols = []
    m = L.shape[0]
    for i in range(m):
        for j in range(i + 1, m):
            s = _sep(L[i], L[j])
            for a in angles:
                for w in widths:
                    cols.append(_kern(s, a, w))
            if tight:
                cols.append(np.min(np.abs(s[None, :] - ang[:, None]), axis=0))
    return cols


def _nearest_onehot(a, b, angles):
    """Which aspect this pair is nearest to, as a one-hot — the discrete view of the same contact."""
    s = _sep(a, b)
    D = np.abs(s[None, :] - np.asarray(angles, dtype=np.float64)[:, None])
    return _onehot(np.argmin(D, axis=0), len(angles))


def _max_cluster(L, window):
    """Largest number of bodies inside any `window`-degree arc — the stellium test, circularly exact."""
    d = np.mod(L[None, :, :] - L[:, None, :], 360.0)     # forward distance from i to j
    return (d <= window).sum(axis=1).max(axis=0).astype(np.float64)


# ── aspect-pattern detection ────────────────────────────────────────────────────────────────────
def _patterns(L, orbscale=1.0, soft=6.0, split=None, participation=False):
    """Detected configurations in one chart (or across two, when `split` is given).

    L is (m, n) longitudes.  `split` = the number of leading rows belonging to the first chart; a
    configuration then only counts when it draws at least one body from each side, which is what
    makes it a cross-chart pattern rather than one person's own.
    Returns (columns, labels).
    """
    m, n = L.shape
    S = np.abs(_wrap(L[:, None, :] - L[None, :, :]))
    di = np.arange(m)
    S[di, di, :] = 999.0                                  # a body never aspects itself
    K, H = {}, {}
    for k, (ang, orb) in PAT_ASP.items():
        # the soft width follows the aspect's OWN orb (a quincunx is allowed 3 deg where a trine gets
        # 8), so the kernel product is not dominated by the aspect with the loosest kernel
        K[k] = _kern(S, ang, max(1.0, soft * orb / 8.0))
        H[k] = (np.abs(S - ang) <= orb * orbscale).astype(np.float64)
    el = _sgn(L) % 4
    md = _sgn(L) % 3

    z = lambda: np.zeros(n, dtype=np.float64)
    names = ["gtrine", "tsquare", "gcross", "yod", "kite", "mystic"]
    hard = {p: z() for p in names}
    softsum = {p: z() for p in names}
    softmax = {p: z() for p in names}
    part = {p: np.zeros((m, n)) for p in names}
    gt_elem = np.zeros((n, 4))
    tsq_mod = np.zeros((n, 3))
    gcr_mod = np.zeros((n, 3))

    def add(p, h, s, members):
        hard[p] += h
        softsum[p] += s
        np.maximum(softmax[p], s, out=softmax[p])
        for q in members:
            part[p][q] += h

    def spans(idxs):
        if split is None:
            return True
        return min(idxs) < split <= max(idxs)

    for i, j, k in itertools.combinations(range(m), 3):
        if not spans((i, j, k)):
            continue
        # grand trine: all three mutually trine
        h = H["tri"][i, j] * H["tri"][i, k] * H["tri"][j, k]
        s = K["tri"][i, j] * K["tri"][i, k] * K["tri"][j, k]
        add("gtrine", h, s, (i, j, k))
        for q in (i, j, k):
            for e in range(4):
                gt_elem[:, e] += (h / 3.0) * (el[q] == e)
        # T-square (apex squares both ends of an opposition) and yod (apex quincunx a sextile)
        for a, b, c in ((i, j, k), (i, k, j), (j, k, i)):
            h = H["opp"][a, b] * H["sq"][a, c] * H["sq"][b, c]
            s = K["opp"][a, b] * K["sq"][a, c] * K["sq"][b, c]
            add("tsquare", h, s, (a, b, c))
            for q in (a, b, c):
                for v in range(3):
                    tsq_mod[:, v] += (h / 3.0) * (md[q] == v)
            h = H["sxt"][a, b] * H["qcx"][a, c] * H["qcx"][b, c]
            s = K["sxt"][a, b] * K["qcx"][a, c] * K["qcx"][b, c]
            add("yod", h, s, (a, b, c))

    for quad in itertools.combinations(range(m), 4):
        if not spans(quad):
            continue
        a, b, c, d = quad
        # grand cross: two oppositions, mutually square
        for (p1, p2), (p3, p4) in (((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))):
            h = (H["opp"][p1, p2] * H["opp"][p3, p4] * H["sq"][p1, p3] * H["sq"][p1, p4]
                 * H["sq"][p2, p3] * H["sq"][p2, p4])
            s = (K["opp"][p1, p2] * K["opp"][p3, p4] * K["sq"][p1, p3] * K["sq"][p1, p4]
                 * K["sq"][p2, p3] * K["sq"][p2, p4])
            add("gcross", h, s, quad)
            for q in quad:
                for v in range(3):
                    gcr_mod[:, v] += (h / 4.0) * (md[q] == v)
            # mystic rectangle: the same two oppositions joined by two sextiles and two trines
            for (x1, x2), (y1, y2) in (((p1, p3), (p2, p4)), ((p1, p4), (p2, p3))):
                h = (H["opp"][p1, p2] * H["opp"][p3, p4] * H["sxt"][x1, x2] * H["sxt"][y1, y2]
                     * H["tri"][p1, p4 if (x1, x2) == (p1, p3) else p3]
                     * H["tri"][p2, p3 if (x1, x2) == (p1, p3) else p4])
                s = (K["opp"][p1, p2] * K["opp"][p3, p4] * K["sxt"][x1, x2] * K["sxt"][y1, y2]
                     * K["tri"][p1, p4 if (x1, x2) == (p1, p3) else p3]
                     * K["tri"][p2, p3 if (x1, x2) == (p1, p3) else p4])
                add("mystic", h, s, quad)
        # kite: grand trine among three, the fourth opposing one of them and sextiling the others
        for t in quad:
            o = [q for q in quad if q != t]
            g_h = H["tri"][o[0], o[1]] * H["tri"][o[0], o[2]] * H["tri"][o[1], o[2]]
            g_s = K["tri"][o[0], o[1]] * K["tri"][o[0], o[2]] * K["tri"][o[1], o[2]]
            for r in o:
                rest = [q for q in o if q != r]
                h = g_h * H["opp"][t, r] * H["sxt"][t, rest[0]] * H["sxt"][t, rest[1]]
                s = g_s * K["opp"][t, r] * K["sxt"][t, rest[0]] * K["sxt"][t, rest[1]]
                add("kite", h, s, quad)

    cols, labels = [], []
    for p in names:
        cols += [hard[p], softsum[p], softmax[p]]
        labels += [f"{p}.hard", f"{p}.softsum", f"{p}.softmax"]
    cols += [gt_elem, tsq_mod, gcr_mod]
    labels += ["gtrine.element x4", "tsquare.modality x3", "gcross.modality x3"]
    # stellium, two ways: a narrow arc, and three-plus bodies inside one sign
    for w in (8.0, 10.0, 15.0, 30.0):
        cols.append(_max_cluster(L, w))
        labels.append(f"stellium.maxcluster{int(w)}")
    signs = _sgn(L)
    cnt = np.zeros((n, 12))
    for i in range(m):
        for sg in range(12):
            cnt[:, sg] += (signs[i] == sg)
    cols += [cnt.max(axis=1), (cnt >= 3).sum(axis=1), (cnt >= 3).astype(np.float64)]
    labels += ["stellium.maxsign", "stellium.nsigns3plus", "stellium.sign3plus x12"]
    if participation:
        for p in ("gtrine", "tsquare", "gcross", "yod"):
            cols.append(part[p].T)
            labels.append(f"{p}.participation x{m}")
    return cols, labels


# ── block 1: element and modality balance ───────────────────────────────────────────────────────
def _balance_vec(E, slot, W, mod):
    """Weighted distribution over `mod` categories (4 = elements, 3 = modalities)."""
    out = np.zeros((E.n, mod), dtype=np.float64)
    tot = 0.0
    for b, w in W.items():
        c = _sgn(E.LON[slot, E.IDX[b]]) % mod
        tot += w
        for j in range(mod):
            out[:, j] += w * (c == j)
    return out / tot


def _sim(P, Q):
    dot = (P * Q).sum(1)
    nrm = np.sqrt((P * P).sum(1)) * np.sqrt((Q * Q).sum(1))
    cos = dot / np.maximum(nrm, 1e-12)
    l1 = np.abs(P - Q).sum(1)
    bh = np.sqrt(np.maximum(P, 0) * np.maximum(Q, 0)).sum(1)
    chi = (((P - Q) ** 2) / np.maximum(P + Q, 1e-12)).sum(1)
    return [cos, l1, bh, chi, dot]


def _b_balance(E):
    """Element/modality balance vectors per partner and their pairwise agreement.

    Weights are March & McEvers and Arroyo, both with the Ascendant/Midheaven terms DROPPED because
    no birth time is known — a documented proxy: the balance here is purely planetary.
    """
    n = E.n
    parts = []
    for W in (W_MARCH, W_ARROYO):
        v = {}
        for slot in (0, 1, 2):                                  # older, younger, wedding
            ev, mv = _balance_vec(E, slot, W, 4), _balance_vec(E, slot, W, 3)
            v[slot] = (ev, mv)
            parts += [ev, mv]
        eo, mo = v[0]
        ey, my = v[1]
        # agreement: the full outer product is the linear-model-friendly form of "which element of
        # hers meets which of his"; the abs-diff/min pair is the tally form.
        parts.append((eo[:, :, None] * ey[:, None, :]).reshape(n, 16))
        parts.append((mo[:, :, None] * my[:, None, :]).reshape(n, 9))
        parts += [np.abs(eo - ey), np.minimum(eo, ey), np.abs(mo - my), np.minimum(mo, my)]
        parts += _sim(eo, ey) + _sim(mo, my)
        parts += [0.5 * (eo + ey), 0.5 * (mo + my)]             # the couple read as one chart
        # dominant element / modality, and whether they share it
        do, dy = np.argmax(eo, axis=1), np.argmax(ey, axis=1)
        qo, qy = np.argmax(mo, axis=1), np.argmax(my, axis=1)
        parts += [_onehot(do, 4), _onehot(dy, 4), _onehot(qo, 3), _onehot(qy, 3),
                  (do == dy).astype(np.float64), (qo == qy).astype(np.float64),
                  ELEM_TABLE[do, dy]]
        # how lopsided each chart is (a "lack of water" is a modern reading in its own right)
        parts += [eo.max(1), ey.max(1), (eo <= 1e-9).sum(1).astype(np.float64),
                  (ey <= 1e-9).sum(1).astype(np.float64), mo.max(1), my.max(1)]
    return _fin(_pack(parts, n))


# ── block 2: sign and element pair one-hots ─────────────────────────────────────────────────────
def _b_signpairs(E):
    """Discrete sign/element/modality bins and their PAIRS — the interaction-heavy representation.

    The Moon's noon uncertainty is about +-6 degrees, a fifth of a sign, so the lunar rows here are
    roughly half reliable; they are emitted anyway because Sun/Moon sign pairing is what the
    tradition talks about.
    """
    n = E.n
    parts = []
    for b in ("Sun", "Moon", "Venus", "Mars", "Juno"):
        so, sy = _sgn(E.LON[0, E.IDX[b]]), _sgn(E.LON[1, E.IDX[b]])
        parts += [_onehot(so, 12), _onehot(sy, 12)]
        parts.append(ELEM_TABLE[so % 4, sy % 4])
        e = np.zeros((n, 16))
        e[np.arange(n), (so % 4) * 4 + (sy % 4)] = 1.0
        q = np.zeros((n, 9))
        q[np.arange(n), (so % 3) * 3 + (sy % 3)] = 1.0
        parts += [e, q]
        d = np.mod(sy - so, 12)
        parts += [_onehot(d, 12), _onehot(np.minimum(d, 12 - d), 7)]
    # the full Sun-sign pair grid, 144 cells: the popular-modern compatibility table's own domain
    so, sy = _sgn(E.LON[0, E.IDX["Sun"]]), _sgn(E.LON[1, E.IDX["Sun"]])
    g = np.zeros((n, 144))
    g[np.arange(n), so * 12 + sy] = 1.0
    parts.append(g)
    # cross pairs: her Venus sign against his Mars sign and the reverse
    for a, b in (("Venus", "Mars"), ("Mars", "Venus"), ("Sun", "Moon"), ("Moon", "Sun")):
        sa, sb = _sgn(E.LON[0, E.IDX[a]]), _sgn(E.LON[1, E.IDX[b]])
        e = np.zeros((n, 16))
        e[np.arange(n), (sa % 4) * 4 + (sb % 4)] = 1.0
        parts += [e, ELEM_TABLE[sa % 4, sb % 4], _onehot(np.mod(sb - sa, 12), 12)]
    return _fin(_pack(parts, n))


# ── block 3: the tradition's own computed numbers ───────────────────────────────────────────────
def _b_score(E):
    """The modern synastry POINT SCORE, computed exactly as the textbook scheme specifies.

    score = sum over cross-aspects of  value(aspect) x weight(body A) x weight(body B) x taper(orb),
    taper linear from 1 at exact to 0 at the aspect's orb limit (Hand's strength-by-orb).  Weights
    and aspect values are listed in SYN_W / SYN_ASP at the top of this file with their sources.
    Also here: the element-relation tally and the sun-sign compatibility grid score, the two other
    numbers this tradition computes rather than describes.
    """
    n = E.n
    bodies = list(SYN_W)
    A = np.stack([E.LON[0, E.IDX[b]] for b in bodies])
    B = np.stack([E.LON[1, E.IDX[b]] for b in bodies])
    per_asp = {a[0]: np.zeros(n) for a in SYN_ASP}
    per_a = np.zeros((n, len(bodies)))
    per_b = np.zeros((n, len(bodies)))
    total, pos, neg = np.zeros(n), np.zeros(n), np.zeros(n)
    nhit, nharm, nhard = np.zeros(n), np.zeros(n), np.zeros(n)
    vm, sm, sat = np.zeros(n), np.zeros(n), np.zeros(n)
    for i, ba in enumerate(bodies):
        for j, bb in enumerate(bodies):
            s = _sep(A[i], B[j])
            for name, ang, orb, val in SYN_ASP:
                t = np.maximum(0.0, 1.0 - np.abs(s - ang) / orb)
                c = val * SYN_W[ba] * SYN_W[bb] * t
                per_asp[name] += c
                per_a[:, i] += c
                per_b[:, j] += c
                total += c
                pos += np.maximum(c, 0.0)
                neg += np.minimum(c, 0.0)
                nhit += (t > 0)
                nharm += (t > 0) * (val > 0)
                nhard += (t > 0) * (val < 0)
                if {ba, bb} <= {"Venus", "Mars"}:
                    vm += c
                if {ba, bb} <= {"Sun", "Moon"}:
                    sm += c
                if "Saturn" in (ba, bb):
                    sat += c
    norm = sum(SYN_W.values()) ** 2
    parts = [total, total / norm, pos, neg, pos / np.maximum(pos - neg, 1e-9), nhit, nharm, nhard,
             nharm / np.maximum(nhit, 1.0), vm, sm, sat, per_a, per_b]
    parts += [per_asp[a[0]] for a in SYN_ASP]
    # the same score with Juno admitted as an eleventh body at weight 3 (asteroid-synastry variant)
    W2 = dict(SYN_W, Juno=3.0)
    b2 = list(W2)
    A2 = np.stack([E.LON[0, E.IDX[b]] for b in b2])
    B2 = np.stack([E.LON[1, E.IDX[b]] for b in b2])
    t2, jt = np.zeros(n), np.zeros(n)
    for i, ba in enumerate(b2):
        for j, bb in enumerate(b2):
            s = _sep(A2[i], B2[j])
            for name, ang, orb, val in SYN_ASP:
                c = val * W2[ba] * W2[bb] * np.maximum(0.0, 1.0 - np.abs(s - ang) / orb)
                t2 += c
                if "Juno" in (ba, bb):
                    jt += c
    parts += [t2, t2 / (sum(W2.values()) ** 2), jt]
    # element tally and sign-grid score, over the pairs the textbooks name
    tally, mtally = np.zeros(n), np.zeros(n)
    for a, b in (("Sun", "Sun"), ("Moon", "Moon"), ("Venus", "Venus"), ("Mars", "Mars"),
                 ("Sun", "Moon"), ("Moon", "Sun"), ("Venus", "Mars"), ("Mars", "Venus")):
        sa, sb = _sgn(E.LON[0, E.IDX[a]]), _sgn(E.LON[1, E.IDX[b]])
        tally += ELEM_TABLE[sa % 4, sb % 4]
        mtally += np.where(sa % 3 == sb % 3, -1.0, 1.0)
    so, sy = _sgn(E.LON[0, E.IDX["Sun"]]), _sgn(E.LON[1, E.IDX["Sun"]])
    d = np.mod(sy - so, 12)
    grid = SIGNGRID[np.minimum(d, 12 - d)]
    mo, my = _sgn(E.LON[0, E.IDX["Moon"]]), _sgn(E.LON[1, E.IDX["Moon"]])
    dm = np.mod(my - mo, 12)
    parts += [tally, mtally, grid, SIGNGRID[np.minimum(dm, 12 - dm)], grid + tally]
    return _fin(_pack(parts, n))


# ── blocks 4 and 5: aspect patterns ─────────────────────────────────────────────────────────────
def _modern10(E, slot):
    return np.stack([E.LON[slot, E.IDX[b]] for b in
                     ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                      "Uranus", "Neptune", "Pluto")])


def _classical7(E, slot):
    return np.stack([E.LON[slot, E.IDX[b]] for b in
                     ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")])


def _b_patterns_natal(E):
    """Grand trine, T-square, grand cross, yod, kite, mystic rectangle and stellium, detected in
    each partner's natal chart and in the wedding chart, over the ten modern bodies.

    Two representations of every configuration: the hard count at the tradition's own orbs, and the
    product of orb kernels (continuous), because the hard count is almost always 0 or 1.
    """
    parts = []
    per = {}
    for slot in (0, 1, 2):
        cols, _ = _patterns(_modern10(E, slot), participation=True)
        per[slot] = cols
        parts += cols
    # do both people carry the same kind of configuration? (min = "both have it")
    for a, b in zip(per[0][:18], per[1][:18]):
        parts.append(np.minimum(np.asarray(a).ravel(), np.asarray(b).ravel()))
    return _fin(_pack(parts, E.n))


def _b_patterns_cross(E):
    """The same configurations formed ACROSS the two charts (at least one body from each partner),
    and inside the two relationship charts — the midpoint composite and the Davison.

    Cross-chart detection uses the seven classical bodies from each side (fourteen points); with all
    twenty the combinatorics say nothing that the tighter set does not.  Two orb settings are given
    because a cross-chart pattern is conventionally allowed a wider orb than a natal one.  A grand
    trine or T-square that appears only when both charts are overlaid is the modern tradition's
    strongest structural claim about a pair, which is why it is detected separately here rather than
    folded into the natal block.
    """
    parts = []
    U = np.concatenate([_classical7(E, 0), _classical7(E, 1)], axis=0)
    for orbscale, soft in ((1.0, 6.0), (0.6, 3.0)):
        cols, _ = _patterns(U, orbscale=orbscale, soft=soft, split=7)
        parts += cols
    C = np.stack([_mid(E.LON[0, E.IDX[b]], E.LON[1, E.IDX[b]]) for b in
                  ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                   "Uranus", "Neptune", "Pluto")])
    cols, _ = _patterns(C)
    parts += cols
    cols, _ = _patterns(_modern10(E, 5))                    # the Davison chart's own patterns
    parts += cols
    return _fin(_pack(parts, E.n))


# ── blocks 6 and 7: asteroid synastry ───────────────────────────────────────────────────────────
def _asteroid_block(E, roids, targets, widths):
    n = E.n
    parts = []
    seen = set()
    for r in roids:
        for t in targets + [r]:
            for da, db in ((0, 1), (1, 0)):
                key = tuple(sorted([(da, r), (db, t)]))
                if key in seen:
                    continue
                seen.add(key)
                a, b = E.LON[da, E.IDX[r]], E.LON[db, E.IDX[t]]
                d = _wrap(a - b)
                s = np.abs(d)
                for ang in PTOL:
                    for w in widths:
                        parts.append(_kern(s, ang, w))
                parts.append(np.min(np.abs(s[None, :] - np.asarray(PTOL)[:, None]), axis=0))
                parts.append(np.cos(np.deg2rad(d)))
                parts.append(np.sin(np.deg2rad(d)))
    return parts


def _b_juno_ceres(E):
    """JUNO and CERES synastry — the modern tradition's own marriage indicators.

    Juno (the wife of Jupiter) is read for the committed partner; Ceres for nurture, food and
    children (Demetra George, "Asteroid Goddesses", 1986).  Each is tested against the partner's
    Sun, Moon, Venus, Mars and same asteroid, in BOTH directions because the rule is directional,
    by all five classical aspects at two orbs, plus the continuous orb tightness and the circular
    form of the signed difference.  Also the tradition's own count: how many Juno contacts fall
    inside 3 and inside 6 degrees.
    """
    n = E.n
    parts = _asteroid_block(E, ["Juno", "Ceres"], ["Sun", "Moon", "Venus", "Mars"], (2.0, 5.0))
    # counted contacts, the way an asteroid-synastry report tallies them
    for r in ("Juno", "Ceres"):
        for lim in (3.0, 6.0):
            c = np.zeros(n)
            for t in ("Sun", "Moon", "Venus", "Mars", r):
                for da, db in ((0, 1), (1, 0)):
                    s = _sep(E.LON[da, E.IDX[r]], E.LON[db, E.IDX[t]])
                    for ang in PTOL:
                        c += (np.abs(s - ang) <= lim)
            parts.append(c)
    # Juno in the partner's Sun sign, and the Juno-Juno sign relationship
    jo, jy = _sgn(E.LON[0, E.IDX["Juno"]]), _sgn(E.LON[1, E.IDX["Juno"]])
    so, sy = _sgn(E.LON[0, E.IDX["Sun"]]), _sgn(E.LON[1, E.IDX["Sun"]])
    parts += [_onehot(jo, 12), _onehot(jy, 12), (jo == sy).astype(np.float64),
              (jy == so).astype(np.float64), ELEM_TABLE[jo % 4, jy % 4],
              _onehot(np.mod(jy - jo, 12), 12)]
    e = np.zeros((n, 16))
    e[np.arange(n), (jo % 4) * 4 + (jy % 4)] = 1.0
    parts.append(e)
    # each partner's Juno against the composite and the wedding Sun/Venus
    for slot in (2, 5):
        for t in ("Sun", "Venus", "Juno"):
            for d in (0, 1):
                s = _sep(E.LON[d, E.IDX["Juno"]], E.LON[slot, E.IDX[t]])
                parts += [_kern(s, 0.0, 4.0), _kern(s, 180.0, 4.0), _kern(s, 120.0, 4.0)]
    return _fin(_pack(parts, n))


def _b_other_asteroids(E):
    """PALLAS, VESTA, CHIRON and the LILITH point in synastry.

    Pallas (strategy and the pattern-making mind), Vesta (dedication and what is kept sacred),
    Chiron (the wound and the healing that binds two people) after Demetra George and Melanie
    Reinhart; Lilith here is the MEAN LUNAR APOGEE — the Black Moon Lilith of modern practice, not
    asteroid 1181 Lilith, which is a different body and is not in this ephemeris.  The Black Moon is
    a computed point rather than a body, so its position is exact at noon and carries none of the
    Moon's own uncertainty.
    """
    parts = _asteroid_block(E, ["Pallas", "Vesta", "Chiron", "Lilith"],
                            ["Sun", "Moon", "Venus", "Mars"], (5.0,))
    for r in ("Pallas", "Vesta", "Chiron", "Lilith"):
        so, sy = _sgn(E.LON[0, E.IDX[r]]), _sgn(E.LON[1, E.IDX[r]])
        e = np.zeros((E.n, 16))
        e[np.arange(E.n), (so % 4) * 4 + (sy % 4)] = 1.0
        parts += [e, ELEM_TABLE[so % 4, sy % 4], _onehot(np.mod(sy - so, 12), 12)]
    return _fin(_pack(parts, E.n))


# ── block 8: Venus-Mars and Sun-Moon cross-contacts ─────────────────────────────────────────────
def _b_venus_mars(E):
    """Venus-Mars and Sun-Moon cross-contacts: the two axes every modern synastry text opens with.

    All sixteen ordered pairs among {Sun, Moon, Venus, Mars} across the two natals, by every
    classical aspect plus the modern minors (30, 45, 72, 135, 150), at a tight and a wide orb, with
    the continuous orb tightness to the nearest aspect, the nearest-aspect one-hot for the four
    marquee pairs, and cos/sin of the signed difference.  Cross-contacts involving the Moon inherit
    its +-6 degree noon uncertainty, so the wide-orb kernels matter more than the tight ones there.
    """
    n = E.n
    keys = ("Sun", "Moon", "Venus", "Mars")
    A = np.stack([E.LON[0, E.IDX[b]] for b in keys])
    B = np.stack([E.LON[1, E.IDX[b]] for b in keys])
    parts = _cross_grid(A, B, MODERN_ANGLES, (3.0, 7.0), tight=True, circ=True)
    for a, b in (("Venus", "Mars"), ("Mars", "Venus"), ("Sun", "Moon"), ("Moon", "Sun")):
        parts.append(_nearest_onehot(E.LON[0, E.IDX[a]], E.LON[1, E.IDX[b]], MODERN_ANGLES))
    # double-Venus and double-Mars, and the same-body contacts, counted the report's way
    c3, c6 = np.zeros(n), np.zeros(n)
    for i in range(4):
        for j in range(4):
            s = _sep(A[i], B[j])
            for ang in PTOL:
                c3 += (np.abs(s - ang) <= 3.0)
                c6 += (np.abs(s - ang) <= 6.0)
    parts += [c3, c6]
    return _fin(_pack(parts, n))


# ── block 9: the Sun/Moon midpoint doctrine ─────────────────────────────────────────────────────
def _b_sunmoon_mid(E):
    """The Sun/Moon midpoint — Ebertin's marriage axis, as modern textbooks inherited it.

    A partner's planet standing ON your Sun/Moon midpoint is the marriage signature; the doctrine is
    stated with hard aspects only (conjunction, opposition, square) and tight orbs, so kernels are
    given at 1.5 and 3 degrees.  The NEAR midpoint is used.  Half the Moon's +-6 degree noon
    uncertainty passes into this point (+-3 degrees), which is exactly why the 3-degree kernel is
    emitted beside the 1.5-degree one rather than a 1-degree one alone.
    """
    n = E.n
    smo = _mid(E.LON[0, E.IDX["Sun"]], E.LON[0, E.IDX["Moon"]])
    smy = _mid(E.LON[1, E.IDX["Sun"]], E.LON[1, E.IDX["Moon"]])
    smc = _mid(_mid(E.LON[0, E.IDX["Sun"]], E.LON[1, E.IDX["Sun"]]),
               _mid(E.LON[0, E.IDX["Moon"]], E.LON[1, E.IDX["Moon"]]))
    smw = _mid(E.LON[2, E.IDX["Sun"]], E.LON[2, E.IDX["Moon"]])
    smd = _mid(E.LON[5, E.IDX["Sun"]], E.LON[5, E.IDX["Moon"]])
    parts = []
    ten = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
    for axis, src in ((smo, 1), (smy, 0), (smc, 2), (smc, 5)):
        tight = np.full(n, 90.0)
        for b in ten:
            s = _sep(axis, E.LON[src, E.IDX[b]])
            for ang in (0.0, 180.0, 90.0):
                for w in (1.5, 3.0):
                    parts.append(_kern(s, ang, w))
            o = np.minimum(np.minimum(np.abs(s), np.abs(s - 180.0)), np.abs(s - 90.0))
            parts.append(o)
            tight = np.minimum(tight, o)
        parts.append(tight)
    # the two marriage axes against each other, and against the wedding and Davison axes
    for a, b in ((smo, smy), (smo, smw), (smy, smw), (smc, smw), (smc, smd), (smo, smd), (smy, smd)):
        s = _sep(a, b)
        parts += [_kern(s, 0.0, 1.5), _kern(s, 0.0, 3.0), _kern(s, 180.0, 3.0),
                  _kern(s, 90.0, 3.0), s]
    parts += [_circ(smo), _circ(smy), _circ(smc), _onehot(_sgn(smo), 12), _onehot(_sgn(smy), 12),
              _onehot(_sgn(smc), 12)]
    return _fin(_pack(parts, n))


# ── blocks 10 and 11: composite and Davison ─────────────────────────────────────────────────────
def _chart_block(E, L, W=W_MARCH):
    n = L.shape[1]
    parts = _self_grid(L, PTOL, (3.0, 6.0), tight=True)
    el = np.zeros((n, 4))
    md = np.zeros((n, 3))
    names = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
    tot = 0.0
    for i, b in enumerate(names):
        w = W[b]
        tot += w
        s = _sgn(L[i])
        for j in range(4):
            el[:, j] += w * (s % 4 == j)
        for j in range(3):
            md[:, j] += w * (s % 3 == j)
    parts += [el / tot, md / tot, _onehot(_sgn(L[0]), 12), _onehot(_sgn(L[1]), 12),
              _circ(L[0]), _circ(L[1]), _circ(L[3]), _circ(L[4])]
    smsep = _sep(L[0], L[1])
    parts += [smsep, np.cos(np.deg2rad(_wrap(L[1] - L[0]))), _sep(L[3], L[4]),
              _sep(L[0], L[3]), _sep(L[0], L[6]), _sep(L[3], L[6]),
              _max_cluster(L, 10.0), _max_cluster(L, 15.0)]
    return parts


def _b_composite(E):
    """The MIDPOINT COMPOSITE chart and its own aspects.

    Each composite body is the near midpoint of the two natal positions of that body; the chart is
    then read as an ordinary chart (Robert Hand, "Planets in Composite", 1975).  No composite
    Ascendant or Midheaven is attempted — those need birth times.  The composite Moon carries the
    combined lunar uncertainty, so it is used at sign resolution and in aspect kernels, never as a
    degree bin.
    """
    L = np.stack([_mid(E.LON[0, E.IDX[b]], E.LON[1, E.IDX[b]]) for b in
                  ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                   "Uranus", "Neptune", "Pluto")])
    return _fin(_pack(_chart_block(E, L), E.n))


def _b_davison(E):
    """The DAVISON relationship chart (slot 5) and its own aspects, plus its disagreement with the
    composite.

    The Davison chart is a real chart cast for the instant midway in time between the two births,
    so its planets are exact rather than averaged.  The full technique also uses the geographic
    midpoint, which needs birthplaces this dataset does not have; that costs only the angles and
    houses, which are not used here.  Modern practice disputes composite versus Davison, so the
    body-by-body separation between the two charts is emitted as features: where the two techniques
    agree, either answer will do; where they diverge by 90 degrees or more, the dispute is live for
    that couple.
    """
    names = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
    D = np.stack([E.LON[5, E.IDX[b]] for b in names])
    C = np.stack([_mid(E.LON[0, E.IDX[b]], E.LON[1, E.IDX[b]]) for b in names])
    parts = _chart_block(E, D)
    diff = np.stack([_sep(D[i], C[i]) for i in range(len(names))])
    parts += [diff.T, diff.mean(axis=0), diff.max(axis=0), (diff > 90.0).sum(axis=0).astype(np.float64),
              np.cos(np.deg2rad(diff)).T]
    return _fin(_pack(parts, E.n))


# ── block 12: progressed synastry ───────────────────────────────────────────────────────────────
def _b_progressed(E):
    """SECONDARY PROGRESSED synastry, a day for a year, progressed to the wedding date.

    Three techniques, all of them standard: each partner's progressed chart against the other's
    natal (both directions, because they are different statements), and progressed against
    progressed.  Progression orbs are tight in modern practice, so kernels are at 1.5 and 3 degrees.
    The progressed chart is cast at noon like everything else; the progressed Moon therefore keeps
    the same +-6 degree uncertainty as the natal one, and the progressed Sun's arc from its natal
    place is, exactly as the technique intends, the solar arc.
    """
    n = E.n
    prog = ("Sun", "Moon", "Venus", "Mars")
    nat = ("Sun", "Moon", "Venus", "Mars", "Juno", "Saturn")
    parts = []
    for pslot, nslot in ((3, 1), (4, 0)):
        P = np.stack([E.LON[pslot, E.IDX[b]] for b in prog])
        N = np.stack([E.LON[nslot, E.IDX[b]] for b in nat])
        parts += _cross_grid(P, N, PTOL, (3.0,), tight=True)
    P3 = np.stack([E.LON[3, E.IDX[b]] for b in prog])
    P4 = np.stack([E.LON[4, E.IDX[b]] for b in prog])
    parts += _cross_grid(P3, P4, PTOL, (1.5, 3.0), tight=True, circ=True)
    # the progressed chart in its own right: sign, whether the progressed Sun changed sign, solar arc
    for pslot, bslot in ((3, 0), (4, 1)):
        ps, ns = _sgn(E.LON[pslot, E.IDX["Sun"]]), _sgn(E.LON[bslot, E.IDX["Sun"]])
        arc = np.mod(E.LON[pslot, E.IDX["Sun"]] - E.LON[bslot, E.IDX["Sun"]], 360.0)
        parts += [_onehot(ps, 12), (ps != ns).astype(np.float64), arc, _circ(arc),
                  _onehot(np.mod(ps - ns, 12), 12),
                  _sep(E.LON[pslot, E.IDX["Moon"]], E.LON[bslot, E.IDX["Moon"]]),
                  np.cos(np.deg2rad(_wrap(E.LON[pslot, E.IDX["Moon"]] - E.LON[pslot, E.IDX["Sun"]])))]
    return _fin(_pack(parts, n))


# ── block 13: solar return timing and retrogrades ───────────────────────────────────────────────
def _b_return_retro(E):
    """The SOLAR RETURN nearest the wedding, and retrograde Venus/Mars.

    A solar return's Sun is by definition the natal Sun, so the computable content is the return's
    TIMING: how far the transiting Sun has moved past the natal Sun by the wedding day gives the
    phase of the solar-return year (exact, from the Sun's own tropical motion of 360/365.2425 degrees
    per day), and therefore how many days the wedding sits after the last return and before the next.
    The return chart's other planets are NOT emitted: that instant is not one of the six ephemeris
    slots and extrapolating a Moon over up to half a year would carry a double-figure error.
    Retrograde flags come from the sign of the longitude speed and are exact.
    """
    n = E.n
    parts = []
    ph = []
    for bslot in (0, 1):
        d = np.mod(E.LON[2, E.IDX["Sun"]] - E.LON[bslot, E.IDX["Sun"]], 360.0)
        phase = d / 360.0
        ph.append(d)
        since = d / SOLAR_DEG_PER_DAY
        nxt = (360.0 - d) / SOLAR_DEG_PER_DAY
        parts += [phase, since, nxt, np.minimum(since, nxt), (nxt < since).astype(np.float64),
                  _circ(d), _onehot(np.floor(d / 30.0).astype(np.int64), 12)]
    dd = _wrap(ph[0] - ph[1])
    parts += [np.abs(dd), dd, _circ(dd), _onehot(np.floor(np.mod(dd, 360.0) / 30.0).astype(np.int64), 12)]
    # retrogrades: Venus and Mars are the tradition's concern, Mercury is its folklore
    for b in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Chiron"):
        for slot in (0, 1, 2):
            sp = E.SPD[slot, E.IDX[b]]
            parts += [(sp < 0).astype(np.float64)]
        parts.append(np.abs(E.SPD[2, E.IDX[b]]))
    for b in ("Venus", "Mars"):
        ro = (E.SPD[0, E.IDX[b]] < 0).astype(np.int64)
        ry = (E.SPD[1, E.IDX[b]] < 0).astype(np.int64)
        rw = (E.SPD[2, E.IDX[b]] < 0).astype(np.int64)
        parts += [_onehot(ro * 2 + ry, 4), _onehot(ro * 4 + ry * 2 + rw, 8),
                  (ro + ry + rw).astype(np.float64),
                  np.abs(E.SPD[0, E.IDX[b]]), np.abs(E.SPD[1, E.IDX[b]]),
                  (E.SPD[3, E.IDX[b]] < 0).astype(np.float64),
                  (E.SPD[4, E.IDX[b]] < 0).astype(np.float64)]
    nretro = np.zeros(n)
    for slot in (0, 1, 2):
        for b in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"):
            nretro += (E.SPD[slot, E.IDX[b]] < 0)
    parts.append(nretro)
    return _fin(_pack(parts, n))


# ── block 14: Sabian symbol degree bins ─────────────────────────────────────────────────────────
CRITICAL = {0: (0.0, 13.0, 26.0), 1: (8.5, 21.5), 2: (4.0, 17.0)}   # cardinal, fixed, mutable


def _b_sabian(E):
    """SABIAN SYMBOL degree bins — one symbol per whole degree of the zodiac, 360 of them.

    Jones and Wheeler, 1925; Jones, "The Sabian Symbols in Astrology", 1953; Rudhyar, "An
    Astrological Mandala", 1973.  The symbol for a longitude is indexed by floor(longitude), so the
    faithful encoding is a 360-way one-hot.  It is given for the two natal SUNS, whose noon position
    is accurate to about a hundredth of a degree.  It is deliberately NOT given for the Moon: the
    noon Moon is uncertain by roughly +-6 degrees, so a lunar degree bin would be six bins wide and
    meaningless — the Moon appears here only at decanate (10 degree) resolution.  Jones's coarser
    groupings, the 72 five-degree pentads and the 36 decanates, carry the intermediate points.
    Critical degrees (cardinal 0/13/26, fixed 8-9/21-22, mutable 4/17) are the classical modern
    addition to the same degree doctrine.
    """
    n = E.n
    parts = []
    for slot in (0, 1):
        lon = np.mod(E.LON[slot, E.IDX["Sun"]], 360.0)
        parts.append(_onehot(np.floor(lon).astype(np.int64), 360))
    for slot, b in ((0, "Venus"), (1, "Venus"), (0, "Juno"), (1, "Juno")):
        lon = np.mod(E.LON[slot, E.IDX[b]], 360.0)
        parts.append(_onehot(np.floor(lon / 5.0).astype(np.int64), 72))
    comp = _mid(E.LON[0, E.IDX["Sun"]], E.LON[1, E.IDX["Sun"]])
    parts.append(_onehot(np.floor(comp / 5.0).astype(np.int64), 72))
    for slot, b in ((0, "Moon"), (1, "Moon"), (5, "Moon")):
        lon = np.mod(E.LON[slot, E.IDX[b]], 360.0)
        parts.append(_onehot(np.floor(lon / 10.0).astype(np.int64), 36))
    for slot in (0, 1):
        for b in ("Sun", "Moon"):
            lon = np.mod(E.LON[slot, E.IDX[b]], 360.0)
            dg = np.mod(lon, 30.0)
            if b == "Sun":
                parts.append(_onehot(np.floor(dg).astype(np.int64), 30))
            s = _sgn(lon)
            crit = np.zeros(n)
            for md, degs in CRITICAL.items():
                for d in degs:
                    crit = np.maximum(crit, (s % 3 == md) * (np.abs(dg - d) <= 1.0))
            parts.append(crit.astype(np.float64))
    return _fin(_pack(parts, n))


# ── the contract ────────────────────────────────────────────────────────────────────────────────
def build(E):
    out = {}
    out["mod: element+modality balance (March/Arroyo)"] = _b_balance(E)
    out["mod: sign & element pair one-hot"] = _b_signpairs(E)
    out["mod: textbook synastry point score"] = _b_score(E)
    out["mod: aspect patterns natal + wedding"] = _b_patterns_natal(E)
    out["mod: aspect patterns cross-chart + relationship charts"] = _b_patterns_cross(E)
    out["mod: Juno + Ceres marriage synastry"] = _b_juno_ceres(E)
    out["mod: Pallas Vesta Chiron Lilith synastry"] = _b_other_asteroids(E)
    out["mod: Venus-Mars + Sun-Moon cross contacts"] = _b_venus_mars(E)
    out["mod: Sun/Moon midpoint marriage axis"] = _b_sunmoon_mid(E)
    out["mod: midpoint composite chart"] = _b_composite(E)
    out["mod: Davison chart + composite dispute"] = _b_davison(E)
    out["mod: progressed synastry"] = _b_progressed(E)
    out["mod: solar return phase + retrogrades"] = _b_return_retro(E)
    out["mod: Sabian 360-degree + pentad bins"] = _b_sabian(E)
    return out


if __name__ == "__main__":
    import sys
    import time
    from core import load
    from evalx import quick

    E = load()
    t0 = time.time()
    B = build(E)
    print(f"{TRADITION}\n{len(B)} blocks built in {time.time()-t0:.1f}s over {E.n} couples\n")

    # visible arithmetic checks on the two things most easily got wrong here
    s = _sgn(np.array([0.0, 29.9, 30.0, 359.9]))
    assert list(s) == [0, 0, 1, 11], f"sign indexing wrong: {s}"
    assert (s % 4).tolist() == [0, 0, 1, 3] and (s % 3).tolist() == [0, 0, 1, 2]
    m = _mid(np.array([350.0, 10.0]), np.array([10.0, 350.0]))
    assert np.allclose(m, [0.0, 0.0]), f"near midpoint wrong: {m}"    # not 180
    d = np.mod(E.LON[2, E.IDX["Sun"]] - E.LON[0, E.IDX["Sun"]], 360.0)
    print(f"solar-return check: wedding falls {np.median(d/SOLAR_DEG_PER_DAY):.0f} days (median) "
          f"after the older partner's return; range "
          f"{(d/SOLAR_DEG_PER_DAY).min():.0f}-{(d/SOLAR_DEG_PER_DAY).max():.0f}")
    gt, lab = _patterns(_modern10(E, 0))
    print(f"pattern check: grand trine present in {100*np.mean(gt[0] > 0):.1f}% of older charts, "
          f"T-square {100*np.mean(gt[3] > 0):.1f}%, grand cross {100*np.mean(gt[6] > 0):.1f}%, "
          f"yod {100*np.mean(gt[9] > 0):.1f}%")

    tot = 0
    for name, X in B.items():
        assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
        assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
        assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
        assert X.shape[1] >= 1, f"{name}: no columns"
        assert np.isfinite(X).all(), f"{name}: non-finite values"
        assert X.std(axis=0).max() > 1e-12, f"{name}: entirely constant"
        tot += X.shape[1]
    assert len(set(B)) == len(B)
    print()
    for name, X in B.items():
        a, u = quick(E, X)
        print(f"  {name:<48} {X.shape[1]:>5} cols   acc {100*a:5.2f}%   AUC {u:.4f}")
    print(f"\n{tot} columns across {len(B)} blocks")
    print("OK")
