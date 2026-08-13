"""
trad_harmonics.py — Harmonics, symmetry and alternative zodiacs.

WHAT THIS FAMILY CLAIMS, AND WHERE THE RULES COME FROM

  HARMONIC CHARTS (John Addey, "Harmonics in Astrology", 1976; David Hamblin, "Harmonic Charts",
  1983).  Multiply every longitude by N and reduce modulo 360.  An aspect of the Nth harmonic in
  the radix becomes a CONJUNCTION in the Nth harmonic chart, so the harmonic chart is read exactly
  like an ordinary chart and only conjunctions (and, for even N, oppositions) matter.  Addey's
  central claim is that each N carries its own meaning and that the numbers are not
  interchangeable: 5 for creative/formative power, 7 for inspiration and compulsion, 9 for
  fruition, completion and — explicitly in Addey — "the harmonic of the family".  Hamblin's
  chapter on the 5th, 7th and 9th is why those three get a block of their own here.
  The algebra used below is exact and worth stating: h_N(a) - h_N(b) == N*(a-b) (mod 360), so the
  Nth harmonic separation of a synastry pair is just N times its radix separation, wrapped.  That
  also means Addey's harmonic analysis IS Fourier analysis of the separation distribution, which is
  where the "wave amplitude" block comes from.

  NON-PTOLEMAIC ASPECT FAMILIES.  Kepler ("Harmonices Mundi", 1619) added the quintile family
  (72, 144) and the biquintile; the septile series (360/7 = 51.4286 and multiples) comes down
  through Addey and John Nelson; the novile series (40, 80, 160) is Vedic in origin (navamsa) and
  was brought into Western practice by Dane Rudhyar and Addey; the undecile (360/11) is Addey's;
  the octile pair (semisquare 45, sesquiquadrate 135) is Kepler's and is the backbone of German
  cosmobiology; semisextile 30 and quincunx 150 are the twelfth-harmonic pair.  Minor-aspect orbs
  are traditionally tight — Ebertin works to 1 degree on the 45-degree dial, Addey to about
  1.5 degrees on the septile — so the kernels below use per-angle orbs, listed in MINOR.

  DECLINATION: PARALLEL AND CONTRA-PARALLEL, and OUT-OF-BOUNDS.  A parallel is equal declination
  with the same sign, a contra-parallel equal declination with opposite signs; the classical orb is
  1 degree (Charles Jayne; Kt Boehrer).  A body is OUT OF BOUNDS when its declination exceeds the
  Sun's own maximum, i.e. the obliquity of the ecliptic at that epoch — the threshold is computed
  per couple from the IAU 1976 mean obliquity rather than hardcoded at 23.44, because the obliquity
  drifts about 2 arcminutes per century over this dataset's 1552-2022 span.

  ANTISCIA (Firmicus Maternus, "Mathesis" II; Ptolemy's "commanding/obeying" degrees).  The
  antiscion of a longitude is its mirror in the solstitial axis, 180 - lambda: two bodies in
  antiscion have the SAME declination, which is why this block sits beside the declination one.
  The contra-antiscion mirrors in the equinoctial axis, -lambda.

  MIDPOINTS ON THE DIAL (Alfred Witte, Hamburg School; Reinhold Ebertin, "The Combination of
  Stellar Influences", 1940).  Cosmobiology reads a planet as standing "on" the midpoint of two
  others when it falls within about 1.5 degrees of the midpoint, its opposition, or any 22.5-degree
  multiple of it — the 22.5 / 45 / 90 degree dials.  Ebertin's own marriage significator is a
  partner's planet on the Sun/Moon midpoint ("die Ehe-Achse"), so that axis gets dedicated columns.

  THE DRACONIC ZODIAC (Jayne; Rudhyar; in modern practice Pamela Crane, "Draconic Astrology").
  Longitudes measured from the Moon's north node instead of the vernal point.  Draconic-to-tropical
  cross contacts are the technique's own signature claim about relationships, and are emitted in
  BOTH directions because the rule is asymmetric.

  HELIOCENTRIC CHARTS (Sepharial; M. E. Jones; Michael Erlewine).  Sun-centred longitudes, plus
  helio-to-geo cross contacts.  The heliocentric Sun is identically 0 and is dropped; the Earth's
  heliocentric longitude is derived exactly as geocentric Sun + 180.

  SPEED, STATIONS, APPLYING vs SEPARATING.  Retrogradation and stationing are read as a weakening
  or an intensification of a body (Ptolemy, "Tetrabiblos" III; modern research astrology treats
  station and out-of-bounds together).  An applying aspect is stronger than a separating one in
  every tradition that distinguishes them, so each synastry contact carries a signed
  applying/separating kernel: +kernel when the residual is closing, -kernel when it is opening.

  FIXED STARS (Vivian Robson, "The Fixed Stars and Constellations in Astrology", 1923; Ebertin-
  Hoffmann, "Fixed Stars and Their Interpretation").  Positions are HARDCODED at J2000 from the
  Hipparcos/Bright Star values, given here in sexagesimal so they can be checked against a
  catalogue, then PRECESSED to each partner's own epoch with the rigorous IAU 1976 (Lieske) zeta/z/
  theta rotation and reduced to ecliptic longitude with the obliquity of date.  Linear proper motion
  is applied from J2000 as well, which matters over 450 years for Arcturus (2.0 arcsec/yr, about
  15 arcminutes) and Alpha Centauri.  Nothing is guessed.  The list is the 20 brightest stars plus
  four the tradition itself insists on (Regulus - the royal star excluded from the top 20 only by a
  magnitude technicality - Algol, Alcyone and Castor).  Star orbs are 1 degree, Robson's own.

THE HARD DATA LIMIT AND HOW IT LANDS HERE

  Only birth DATES are known; every chart is cast for 12:00 UT, so there is no Ascendant, no
  Midheaven and no house.  This family is unusually lucky in that respect: harmonics, declination,
  latitude, antiscia, midpoints, the draconic and heliocentric zodiacs and fixed-star contacts are
  all built from longitudes, declinations and speeds and need no house cusp at all.  Two
  compromises are still forced and are named where they occur:

    - THE MOON is uncertain by roughly +-6 degrees at noon.  In the high harmonics that error is
      multiplied by N: a 6-degree radix error becomes 96 degrees in the 16th harmonic.  Lunar
      columns in the N>=8 blocks are therefore close to noise BY CONSTRUCTION and are kept only
      because the tradition would include them and because a scorer that finds nothing in them is
      itself informative.  The Moon's declination and out-of-bounds flag carry the same +-6 degrees
      of longitude error, which is about +-2.5 degrees of declination near the nodes.
    - THE DRACONIC ZODIAC is measured from the TRUE node (Crane's choice); the mean node is
      available but the true node is what draconic practice uses.
    - "APPLYING" strictly needs the aspect to be tightening at the birth MOMENT.  Noon speeds are
      used, which is exact for slow bodies and good to a few percent for the Moon.

  No feature in this module reads E.Y, directly or indirectly.  Constant columns are pruned on X
  alone.
"""

import numpy as np

TRADITION = ("Harmonics, symmetry and alternative zodiacs (Addey/Hamblin harmonics, Kepler-Addey "
             "minor aspects, declination, antiscia, Ebertin dial midpoints, draconic, heliocentric, "
             "fixed stars)")

# ── body sets ───────────────────────────────────────────────────────────────────────────────────
M10 = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
C7 = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
K6 = ("Sun", "Moon", "Venus", "Mars", "Jupiter", "Saturn")
K5 = ("Sun", "Moon", "Venus", "Mars", "Saturn")
LATB = ("Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
HELB = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
MOVERS = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
          "TrueNode", "Chiron", "Ceres", "Pallas", "Juno", "Vesta")

OLD, YNG, WED, DAV = 0, 1, 2, 5

# ── non-Ptolemaic aspect families: (label, angle, traditional orb) ──────────────────────────────
# Kepler (quintile family, octiles), Addey/Nelson (septiles, undeciles), Rudhyar/Addey (noviles),
# twelfth-harmonic pair (semisextile, quincunx).  Orbs are the tight ones these authors use.
MINOR = [
    ("decile36", 36.0, 1.5), ("quintile72", 72.0, 2.0),
    ("tredecile108", 108.0, 1.5), ("biquintile144", 144.0, 2.0),
    ("septile51", 360.0 / 7.0, 1.5), ("biseptile103", 720.0 / 7.0, 1.5),
    ("triseptile154", 1080.0 / 7.0, 1.5),
    ("novile40", 40.0, 1.5), ("binovile80", 80.0, 1.5), ("quadnovile160", 160.0, 1.5),
    ("undecile33", 360.0 / 11.0, 1.0), ("biundecile65", 720.0 / 11.0, 1.0),
    ("semisquare45", 45.0, 2.0), ("sesquiquadrate135", 135.0, 2.0),
    ("semisextile30", 30.0, 2.0), ("quincunx150", 150.0, 2.5),
]
PRIMARY = ("quintile72", "biquintile144", "septile51", "novile40",
           "semisquare45", "sesquiquadrate135", "semisextile30", "quincunx150")
FAMILIES = {"quintile": ("decile36", "quintile72", "tredecile108", "biquintile144"),
            "septile": ("septile51", "biseptile103", "triseptile154"),
            "novile": ("novile40", "binovile80", "quadnovile160"),
            "undecile": ("undecile33", "biundecile65"),
            "octile": ("semisquare45", "sesquiquadrate135"),
            "twelfth": ("semisextile30", "quincunx150")}
PTOL = (0.0, 60.0, 90.0, 120.0, 180.0)

# ── the fixed stars: J2000 ICRS, sexagesimal so a reader can check them against a catalogue ─────
# (name, RA h m s, Dec sign d m s, proper motion mu_alpha* and mu_delta in mas/yr, V magnitude)
# The 20 brightest stars, then Regulus / Algol / Alcyone / Castor, which the tradition names.
STARS = [
    ("Sirius",    (6, 45, 8.917),   (-1, 16, 42, 58.02), (-546.01, -1223.07), -1.46),
    ("Canopus",   (6, 23, 57.11),   (-1, 52, 41, 44.4),  (19.93, 23.24),      -0.74),
    ("RigilKent", (14, 39, 36.49),  (-1, 60, 50, 2.3),   (-3608.0, 686.0),    -0.27),
    ("Arcturus",  (14, 15, 39.67),  (+1, 19, 10, 56.7),  (-1093.39, -1999.40), -0.05),
    ("Vega",      (18, 36, 56.34),  (+1, 38, 47, 1.3),   (200.94, 286.23),     0.03),
    ("Capella",   (5, 16, 41.36),   (+1, 45, 59, 52.8),  (75.52, -427.13),     0.08),
    ("Rigel",     (5, 14, 32.27),   (-1, 8, 12, 5.9),    (1.87, -0.56),        0.13),
    ("Procyon",   (7, 39, 18.12),   (+1, 5, 13, 29.9),   (-714.59, -1036.80),  0.34),
    ("Achernar",  (1, 37, 42.85),   (-1, 57, 14, 12.3),  (88.02, -40.08),      0.46),
    ("Betelgeuse", (5, 55, 10.31),  (+1, 7, 24, 25.4),   (27.33, 10.86),       0.50),
    ("Hadar",     (14, 3, 49.40),   (-1, 60, 22, 22.9),  (-33.27, -23.16),     0.61),
    ("Altair",    (19, 50, 46.999), (+1, 8, 52, 5.96),   (536.23, 385.29),     0.77),
    ("Acrux",     (12, 26, 35.90),  (-1, 63, 5, 56.7),   (-35.83, -14.86),     0.77),
    ("Aldebaran", (4, 35, 55.24),   (+1, 16, 30, 33.5),  (63.45, -188.94),     0.85),
    ("Spica",     (13, 25, 11.58),  (-1, 11, 9, 40.8),   (-42.50, -31.73),     1.04),
    ("Antares",   (16, 29, 24.46),  (-1, 26, 25, 55.2),  (-12.11, -23.30),     1.09),
    ("Pollux",    (7, 45, 18.95),   (+1, 28, 1, 34.3),   (-626.55, -45.80),    1.14),
    ("Fomalhaut", (22, 57, 39.05),  (-1, 29, 37, 20.1),  (329.22, -164.22),    1.16),
    ("Deneb",     (20, 41, 25.92),  (+1, 45, 16, 49.2),  (2.01, 1.85),         1.25),
    ("Mimosa",    (12, 47, 43.27),  (-1, 59, 41, 19.5),  (-48.24, -12.82),     1.25),
    ("Regulus",   (10, 8, 22.31),   (+1, 11, 58, 1.9),   (-249.40, 4.91),      1.40),
    ("Castor",    (7, 34, 35.87),   (+1, 31, 53, 17.8),  (-206.33, -148.18),   1.58),
    ("Algol",     (3, 8, 10.13),    (+1, 40, 57, 20.3),  (2.39, -1.44),        2.12),
    ("Alcyone",   (3, 47, 29.08),   (+1, 24, 6, 18.5),   (19.34, -43.67),      2.87),
]
J2000 = 2451545.0


# ── small utilities ─────────────────────────────────────────────────────────────────────────────
def _ix(E, names):
    return [E.IDX[b] for b in names]


def _fin(X):
    """Force (n, k) float64, finite, and drop columns that carry no variance at all."""
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[:, None]
    X = np.ascontiguousarray(X)
    X[~np.isfinite(X)] = 0.0
    # NO VARIANCE PRUNING HERE, DELIBERATELY. This used to drop columns whose standard deviation was
    # zero in the batch being built, and that made a block's WIDTH a function of the DATA rather than
    # of the code. Two consequences, both silent: a scoring batch (one couple, or ten thousand
    # candidates sharing a fixed partner) has many constant columns, so prediction handed the model a
    # narrower and differently-ordered matrix than training did; and a full run built in row chunks
    # produced chunks of different widths that could not be concatenated. Constant columns are now
    # pruned exactly once, globally, by run.collect, which records `kept_idx` in the manifest so
    # prediction can select the same columns. Width is a function of the code alone.
    return X


def _flat(a, n):
    """(..., n) -> (n, prod(...))."""
    return np.ascontiguousarray(np.asarray(a, dtype=np.float64).reshape(-1, n).T)


def _cross(E, A, B):
    """Signed radix difference of every A-body against every B-body: (na, nb, n)."""
    return E.wrap(A[:, None, :] - B[None, :, :])


def _pairs(k):
    return [(i, j) for i in range(k) for j in range(i + 1, k)]


def _obliquity(jd):
    """IAU 1976 mean obliquity of the ecliptic, degrees.  Also the Sun's maximum declination,
    which is the out-of-bounds threshold."""
    T = (np.asarray(jd, dtype=np.float64) - J2000) / 36525.0
    return 23.439291111 - 0.0130041667 * T - 1.6388889e-7 * T ** 2 + 5.0361111e-7 * T ** 3


def _star_j2000():
    """Decode the hardcoded catalogue into arrays: RA/Dec in degrees, proper motion in deg/yr."""
    ra, dec, pmr, pmd, mag, names = [], [], [], [], [], []
    for nm, (h, m, s), (sg, dd, dm, ds), (pa, pd), v in STARS:
        ra.append(15.0 * (h + m / 60.0 + s / 3600.0))
        dec.append(sg * (dd + dm / 60.0 + ds / 3600.0))
        pmr.append(pa / 3.6e6)      # mu_alpha* (already includes cos dec)
        pmd.append(pd / 3.6e6)
        mag.append(v)
        names.append(nm)
    return (np.array(ra), np.array(dec), np.array(pmr), np.array(pmd), np.array(mag), names)


def _stars_at(jd):
    """Precess the hardcoded J2000 stars to the epochs `jd` (shape (n,)).

    Rigorous IAU 1976 / Lieske accumulated precession angles zeta, z, theta, applied as the standard
    equatorial rotation, after linear proper motion from J2000.  Then equatorial-of-date to
    ecliptic-of-date with the mean obliquity of date.  Returns (lon, dec) each (n_stars, n).
    """
    jd = np.asarray(jd, dtype=np.float64)
    ra0, dec0, pmr, pmd, _, _ = _star_j2000()
    dt = (jd - J2000) / 365.25                                   # years from J2000
    d0 = np.deg2rad(dec0)[:, None] + np.deg2rad(pmd)[:, None] * dt[None, :]
    a0 = np.deg2rad(ra0)[:, None] + np.deg2rad(pmr)[:, None] * dt[None, :] / np.cos(np.deg2rad(dec0))[:, None]

    T = (jd - J2000) / 36525.0
    asec = np.pi / 180.0 / 3600.0
    zeta = (2306.2181 * T + 0.30188 * T ** 2 + 0.017998 * T ** 3) * asec
    z = (2306.2181 * T + 1.09468 * T ** 2 + 0.018203 * T ** 3) * asec
    th = (2004.3109 * T - 0.42665 * T ** 2 - 0.041833 * T ** 3) * asec

    ap = a0 + zeta[None, :]
    A = np.cos(d0) * np.sin(ap)
    B = np.cos(th)[None, :] * np.cos(d0) * np.cos(ap) - np.sin(th)[None, :] * np.sin(d0)
    C = np.sin(th)[None, :] * np.cos(d0) * np.cos(ap) + np.cos(th)[None, :] * np.sin(d0)
    ra = np.arctan2(A, B) + z[None, :]
    dec = np.arcsin(np.clip(C, -1.0, 1.0))

    eps = np.deg2rad(_obliquity(jd))[None, :]
    y = np.sin(dec) * np.sin(eps) + np.cos(dec) * np.cos(eps) * np.sin(ra)
    x = np.cos(dec) * np.cos(ra)
    lon = np.mod(np.rad2deg(np.arctan2(y, x)), 360.0)
    return lon, np.rad2deg(dec)


# ── blocks ──────────────────────────────────────────────────────────────────────────────────────
def _harmonic_kernels(E, Ns, bi, width):
    """Nth-harmonic synastry conjunctions.  h_N(a)-h_N(b) == N*(a-b) (mod 360), so the harmonic
    separation is N times the radix separation, wrapped — Addey's own algebra, no chart recast."""
    d = _cross(E, E.LON[OLD][bi], E.LON[YNG][bi])
    out = [E.orbkern(np.abs(E.wrap(N * d)), 0.0, width) for N in Ns]
    return np.concatenate([_flat(o, E.n) for o in out], axis=1)


def _wave(E, d, nmax=16):
    """Addey's harmonic analysis of a distribution of separations: the Nth Fourier component.

    d is (m, n) signed separations.  For each N the mean of exp(i*N*d) over the m contacts gives
    the wave's cosine and sine parts and its amplitude — the amplitude is exactly Addey's "strength
    of the Nth harmonic" for that set of contacts.
    """
    out = []
    for N in range(1, nmax + 1):
        r = np.deg2rad(N * d)
        c, s = np.cos(r).mean(axis=0), np.sin(r).mean(axis=0)
        out += [c, s, np.sqrt(c * c + s * s)]
    return np.stack(out, axis=1)


def _own_pairs(E, slot, bi):
    """Signed separations of every distinct pair inside one chart: (45, n) for 10 bodies."""
    L = E.LON[slot][bi]
    return np.stack([E.wrap(L[i] - L[j]) for i, j in _pairs(len(bi))], axis=0)


def _minor_detail(E):
    d = np.abs(_cross(E, E.LON[OLD][_ix(E, K6)], E.LON[YNG][_ix(E, K6)]))
    cols = []
    for lab, ang, orb in MINOR:
        if lab in PRIMARY:
            cols.append(_flat(E.orbkern(d, ang, orb), E.n))
    return np.concatenate(cols, axis=1)


def _minor_totals(E):
    """The tradition's own tallies: how many minor-aspect contacts of each family a couple has,
    plus the summed kernel strength at three orb widths (orb choice is itself doctrinal)."""
    m10 = _ix(E, M10)
    d = np.abs(_cross(E, E.LON[OLD][m10], E.LON[YNG][m10])).reshape(-1, E.n)
    ownA = np.abs(_own_pairs(E, OLD, m10))
    ownB = np.abs(_own_pairs(E, YNG, m10))
    ownW = np.abs(_own_pairs(E, WED, m10))
    cols, fam = [], {}
    for lab, ang, orb in MINOR:
        for w in (1.0, 2.0, 4.0):
            cols.append(E.orbkern(d, ang, w).sum(axis=0))
        hit = (np.abs(d - ang) <= orb).sum(axis=0).astype(np.float64)
        cols.append(hit)
        fam[lab] = hit
        cols.append((np.abs(ownA - ang) <= orb).sum(axis=0).astype(np.float64))
        cols.append((np.abs(ownB - ang) <= orb).sum(axis=0).astype(np.float64))
        cols.append((np.abs(ownW - ang) <= orb).sum(axis=0).astype(np.float64))
    for _, labs in FAMILIES.items():
        cols.append(np.sum([fam[l] for l in labs], axis=0).astype(np.float64))
    return np.stack(cols, axis=1)


def _declination(E):
    """Parallels, contra-parallels (1 degree, Jayne) and out-of-bounds (declination beyond the
    Sun's own maximum = the obliquity of date, Kt Boehrer)."""
    m10 = _ix(E, M10)
    A, B = E.DEC[OLD][m10], E.DEC[YNG][m10]
    par = np.abs(A[:, None, :] - B[None, :, :])
    con = np.abs(A[:, None, :] + B[None, :, :])
    cols = [_flat(E.orbkern(par, 0.0, 1.0), E.n), _flat(E.orbkern(con, 0.0, 1.0), E.n),
            _flat(E.orbkern(par, 0.0, 2.5), E.n), _flat(E.orbkern(con, 0.0, 2.5), E.n)]
    cols.append(np.stack([(par <= 1.0).sum(axis=(0, 1)), (con <= 1.0).sum(axis=(0, 1)),
                          (par <= 2.0).sum(axis=(0, 1)), (con <= 2.0).sum(axis=(0, 1))],
                         axis=1).astype(np.float64))
    oob = []
    for s in (OLD, YNG):
        lim = _obliquity(E.JD[s])
        dec = E.DEC[s]
        flag = (np.abs(dec) > lim[None, :]).astype(np.float64)
        exc = np.maximum(np.abs(dec) - lim[None, :], 0.0)
        oob += [_flat(flag, E.n), _flat(exc, E.n),
                flag.sum(axis=0)[:, None], exc.sum(axis=0)[:, None],
                np.abs(dec).max(axis=0)[:, None]]
    cols += oob
    cols.append(_flat(E.DEC[OLD][m10], E.n))
    cols.append(_flat(E.DEC[YNG][m10], E.n))
    return np.concatenate(cols, axis=1)


def _latitude(E):
    """Ecliptic-latitude parallels and contra-parallels, plus each body's latitude.  The Moon's
    latitude is its distance from the nodal plane, so small |lat| is the eclipse-prone condition
    the tradition reads as fated."""
    lb = _ix(E, LATB)
    A, B = E.LAT[OLD][lb], E.LAT[YNG][lb]
    par = np.abs(A[:, None, :] - B[None, :, :])
    con = np.abs(A[:, None, :] + B[None, :, :])
    cols = [_flat(E.orbkern(par, 0.0, 1.0), E.n), _flat(E.orbkern(con, 0.0, 1.0), E.n),
            _flat(A, E.n), _flat(B, E.n), _flat(np.abs(A), E.n), _flat(np.abs(B), E.n)]
    mo = E.IDX["Moon"]
    cols.append(np.stack([np.abs(E.LAT[OLD][mo]), np.abs(E.LAT[YNG][mo]),
                          np.abs(E.LAT[WED][mo]), np.abs(E.LAT[DAV][mo]),
                          (par <= 1.0).sum(axis=(0, 1)).astype(np.float64),
                          (con <= 1.0).sum(axis=(0, 1)).astype(np.float64)], axis=1))
    return np.concatenate(cols, axis=1)


def _draconic(E):
    """Draconic synastry: longitudes measured from the TRUE node (draconic practice's own choice)."""
    m10, c7 = _ix(E, M10), _ix(E, C7)
    nd = E.IDX["TrueNode"]
    DA = np.mod(E.LON[OLD] - E.LON[OLD][nd][None, :], 360.0)
    DB = np.mod(E.LON[YNG] - E.LON[YNG][nd][None, :], 360.0)
    d = np.abs(_cross(E, DA[m10], DB[m10]))
    dc = np.abs(_cross(E, DA[c7], DB[c7]))
    hard = np.maximum.reduce([E.orbkern(dc, a, 3.0) for a in (0.0, 90.0, 180.0)])
    soft = np.maximum.reduce([E.orbkern(dc, a, 3.0) for a in (60.0, 120.0)])
    cols = [_flat(E.orbkern(d, 0.0, 3.0), E.n), _flat(E.orbkern(d, 0.0, 6.0), E.n),
            _flat(hard, E.n), _flat(soft, E.n)]
    # draconic sign of the two luminaries, one-hot both partners (the Moon's sign is ~half reliable)
    for D in (DA, DB):
        for b in (E.IDX["Sun"], E.IDX["Moon"]):
            sg = np.floor(D[b] / 30.0).astype(int) % 12
            oh = np.zeros((E.n, 12))
            oh[np.arange(E.n), sg] = 1.0
            cols.append(oh)
    return np.concatenate(cols, axis=1)


def _draconic_cross(E):
    """Draconic-to-tropical cross contacts, both orderings (the rule is asymmetric)."""
    m10 = _ix(E, M10)
    nd = E.IDX["TrueNode"]
    DA = np.mod(E.LON[OLD] - E.LON[OLD][nd][None, :], 360.0)[m10]
    DB = np.mod(E.LON[YNG] - E.LON[YNG][nd][None, :], 360.0)[m10]
    TA, TB = E.LON[OLD][m10], E.LON[YNG][m10]
    ab = np.abs(_cross(E, DA, TB))
    ba = np.abs(_cross(E, DB, TA))
    return np.concatenate([_flat(E.orbkern(ab, 0.0, 3.0), E.n),
                           _flat(E.orbkern(ba, 0.0, 3.0), E.n),
                           _flat(np.maximum(E.orbkern(ab, 0.0, 3.0), E.orbkern(ab, 180.0, 3.0)), E.n),
                           _flat(np.maximum(E.orbkern(ba, 0.0, 3.0), E.orbkern(ba, 180.0, 3.0)), E.n)],
                          axis=1)


def _heliocentric(E):
    """Heliocentric synastry and helio-to-geo cross contacts.  The heliocentric Sun is identically
    zero, so it is replaced by the Earth, whose heliocentric longitude is geocentric Sun + 180."""
    hb, c7 = _ix(E, HELB), _ix(E, C7)
    HA = np.concatenate([E.HELIO[OLD][hb], np.mod(E.LON[OLD][E.IDX["Sun"]] + 180.0, 360.0)[None, :]])
    HB = np.concatenate([E.HELIO[YNG][hb], np.mod(E.LON[YNG][E.IDX["Sun"]] + 180.0, 360.0)[None, :]])
    d = np.abs(_cross(E, HA, HB))
    ab = np.abs(_cross(E, HA, E.LON[YNG][c7]))
    ba = np.abs(_cross(E, HB, E.LON[OLD][c7]))
    return np.concatenate([_flat(E.orbkern(d, 0.0, 4.0), E.n),
                           _flat(E.orbkern(d, 180.0, 4.0), E.n),
                           _flat(E.orbkern(ab, 0.0, 4.0), E.n),
                           _flat(E.orbkern(ba, 0.0, 4.0), E.n)], axis=1)


# TYPICAL SPEED PER BODY — a FROZEN PHYSICAL CONSTANT, and it used to be a cohort statistic.
#
# This was `np.median(np.abs(E.SPD[:3]), axis=(0, 2))`, and axis 2 is the ROW axis: the divisor below was
# the median speed of whoever happened to be in the batch. Three feature families are scaled by it, so the
# same couple got different features depending on its company — measured, on 400 real couples built whole
# versus in two halves: 184 of 557 columns differed, by up to 0.385, AT IDENTICAL WIDTH, so no shape check
# could ever have caught it. It also meant a browser scoring one pair divided by that pair's own speed.
#
# A body's typical speed is a property of the body, not of a dataset. These are the median |longitude speed|
# over every third day from 1800 to 2030, in degrees per day, in core.py's body order. Reproduce with:
#     for each body: median(|swe.calc_ut(jd, body, FLG_SPEED)[0][3]|) over arange(jd0+1, jd1-1, 3.0)
TYPICAL_SPEED = np.array([
    0.98491065,    # Sun
    13.05743005,   # Moon
    1.35642026,    # Mercury
    1.19605313,    # Venus
    0.63568558,    # Mars
    0.12906101,    # Jupiter
    0.07062950,    # Saturn
    0.03524307,    # Uranus
    0.02269534,    # Neptune
    0.01706841,    # Pluto
    0.03012490,    # TrueNode
    0.05293769,    # MeanNode
    0.11131916,    # Lilith
    0.04518209,    # Chiron
    0.30230568,    # Ceres
    0.30278249,    # Pallas
    0.29597738,    # Juno
    0.37480638,    # Vesta
])


def _speed(E):
    """Retrograde flags, near-stationary kernels, and an applying/separating sign on every contact.

    Applying is computed from noon speeds: with d = wrap(lonA - lonB) and residual r = |d| - angle,
    the residual closes at rate -sign(r) * sign(d) * (spdA - spdB).  The emitted column is the
    aspect kernel signed by that rate: positive applying, negative separating.
    """
    mv, m10 = _ix(E, MOVERS), _ix(E, M10)
    med = TYPICAL_SPEED
    med = np.where(med > 1e-9, med, 1e-9)
    cols = []
    for s in (OLD, YNG, WED):
        cols.append(_flat((E.SPD[s][mv] < 0).astype(np.float64), E.n))
        cols.append(_flat(np.abs(E.SPD[s][mv]) / med[mv, None], E.n))
        cols.append(_flat(np.exp(-0.5 * (E.SPD[s][mv] / (0.06 * med[mv, None])) ** 2), E.n))
        cols.append((E.SPD[s][mv] < 0).sum(axis=0)[:, None].astype(np.float64))
    ra = (E.SPD[OLD][mv] < 0).astype(np.float64)
    rb = (E.SPD[YNG][mv] < 0).astype(np.float64)
    cols += [_flat(ra * rb, E.n), _flat(np.abs(ra - rb), E.n)]
    d = _cross(E, E.LON[OLD][m10], E.LON[YNG][m10])
    rel = (E.SPD[OLD][m10][:, None, :] - E.SPD[YNG][m10][None, :, :])
    scale = (med[m10][:, None] + med[m10][None, :])[:, :, None]
    cols.append(_flat(rel / scale, E.n))
    sep = np.abs(d)
    sgn = np.sign(d)
    sgn[sgn == 0] = 1.0
    for ang in (0.0, 90.0, 180.0):
        k = E.orbkern(sep, ang, 6.0)
        r = sep - ang
        rs = np.sign(r)
        rs[rs == 0] = 1.0
        closing = -rs * sgn * rel
        cols.append(_flat(k * np.sign(closing), E.n))
    return np.concatenate(cols, axis=1)


def _fixed_stars(E):
    """Conjunctions by longitude and parallels by declination with the precessed bright stars."""
    c7 = _ix(E, C7)
    cols, hits = [], []
    for s in (OLD, YNG):
        slon, sdec = _stars_at(E.JD[s])
        L, D = E.LON[s][c7], E.DEC[s][c7]
        sep = np.abs(E.wrap(slon[:, None, :] - L[None, :, :]))       # (nstar, nbody, n)
        par = np.abs(sdec[:, None, :] - D[None, :, :])
        cols.append(_flat(E.orbkern(sep, 0.0, 1.0), E.n))
        cols.append(_flat(E.orbkern(par, 0.0, 1.0), E.n))
        h = (sep <= 1.0).astype(np.float64)
        hits.append(h)
        cols.append(h.sum(axis=(0, 1))[:, None])
        cols.append((par <= 1.0).sum(axis=(0, 1))[:, None].astype(np.float64))
    # both partners carrying the same star: the shared-star contact
    cols.append(_flat((hits[0].sum(axis=1) > 0) * (hits[1].sum(axis=1) > 0), E.n))
    return np.concatenate(cols, axis=1)


def _symmetry(E):
    """Antiscia / contra-antiscia (Firmicus) and Ebertin's dial midpoints, including the Sun/Moon
    marriage axis."""
    m10, c7, k5 = _ix(E, M10), _ix(E, C7), _ix(E, K5)
    A, B = E.LON[OLD][m10], E.LON[YNG][m10]
    anti_A = np.mod(180.0 - A, 360.0)
    cont_A = np.mod(-A, 360.0)
    sa = np.abs(_cross(E, anti_A, B))
    sc = np.abs(_cross(E, cont_A, B))
    cols = [_flat(E.orbkern(sa, 0.0, 1.5), E.n), _flat(E.orbkern(sc, 0.0, 1.5), E.n),
            np.stack([(sa <= 1.0).sum(axis=(0, 1)), (sc <= 1.0).sum(axis=(0, 1)),
                      (sa <= 2.0).sum(axis=(0, 1)), (sc <= 2.0).sum(axis=(0, 1))],
                     axis=1).astype(np.float64)]

    def dial(p, m, step):
        r = np.mod(p - m, step)
        return np.minimum(r, step - r)

    for src, dst in ((OLD, YNG), (YNG, OLD)):
        L = E.LON[src][c7]
        mid = np.stack([np.mod(L[i] + E.wrap(L[j] - L[i]) / 2.0, 360.0) for i, j in _pairs(len(c7))])
        P = E.LON[dst][k5]
        d225 = dial(P[None, :, :], mid[:, None, :], 22.5)
        cols.append(_flat(E.orbkern(d225, 0.0, 1.5), E.n))
        cols.append((d225 <= 1.5).sum(axis=(0, 1))[:, None].astype(np.float64))
        # Ebertin's Ehe-Achse: the partner's bodies on this chart's Sun/Moon midpoint
        sm = np.mod(E.LON[src][E.IDX["Sun"]]
                    + E.wrap(E.LON[src][E.IDX["Moon"]] - E.LON[src][E.IDX["Sun"]]) / 2.0, 360.0)
        Q = E.LON[dst][m10]
        for step in (22.5, 45.0, 90.0):
            cols.append(_flat(E.orbkern(dial(Q, sm[None, :], step), 0.0, 1.5), E.n))
    return np.concatenate(cols, axis=1)


# ── the contract ────────────────────────────────────────────────────────────────────────────────
def build(E):
    """name -> (E.n, k) float64, every value finite.  Nothing here reads E.Y."""
    m10, c7 = _ix(E, M10), _ix(E, C7)
    out = {}

    # 1-3: harmonic charts.  Grouped by what the doctrine claims for the number, not by size.
    out["har: harmonic 5/7/9 conj (Addey creative)"] = _fin(_harmonic_kernels(E, (5, 7, 9), m10, 4.0))
    out["har: harmonic 2/3/4/6/8/12 conj"] = _fin(_harmonic_kernels(E, (2, 3, 4, 6, 8, 12), m10, 4.0))
    out["har: harmonic 10/11/13/16 conj"] = _fin(_harmonic_kernels(E, (10, 11, 13, 16), m10, 4.0))

    # 4: the same doctrine, circular instead of kernelled — cos/sin of N*(a-b).
    d7 = _cross(E, E.LON[OLD][c7], E.LON[YNG][c7])
    circ = []
    for N in (5, 7, 9):
        r = np.deg2rad(N * d7)
        circ += [_flat(np.cos(r), E.n), _flat(np.sin(r), E.n)]
    out["har: harmonic 5/7/9 circular cos/sin"] = _fin(np.concatenate(circ, axis=1))

    # 5: Addey's own number — the amplitude of the Nth harmonic wave in a set of contacts.
    sets = [_cross(E, E.LON[OLD][m10], E.LON[YNG][m10]).reshape(-1, E.n),
            d7.reshape(-1, E.n),
            _own_pairs(E, OLD, m10), _own_pairs(E, YNG, m10),
            _own_pairs(E, WED, m10), _own_pairs(E, DAV, m10)]
    out["har: Addey wave amplitudes N=1..16"] = _fin(np.concatenate([_wave(E, s) for s in sets], axis=1))

    # 6-7: non-Ptolemaic aspect families.
    out["har: minor-aspect kernels (Kepler/Addey)"] = _fin(_minor_detail(E))
    out["har: minor-aspect family tallies"] = _fin(_minor_totals(E))

    # 8-9: out of the plane of the ecliptic.
    out["har: declination parallels + out-of-bounds"] = _fin(_declination(E))
    out["har: ecliptic latitude contacts"] = _fin(_latitude(E))

    # 10-12: alternative zodiacs and frames.
    out["har: draconic zodiac synastry"] = _fin(_draconic(E))
    out["har: draconic-tropical cross contacts"] = _fin(_draconic_cross(E))
    out["har: heliocentric + helio-geo contacts"] = _fin(_heliocentric(E))

    # 13: motion.
    out["har: speed, stations, applying/separating"] = _fin(_speed(E))

    # 14: the sphere of fixed stars, precessed.
    out["har: fixed stars conj + parallels"] = _fin(_fixed_stars(E))

    # 15: symmetry — antiscia and the cosmobiological dial.
    out["har: antiscia + Ebertin dial midpoints"] = _fin(_symmetry(E))
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

    # a visible check that the hardcoded stars really are precessed, not guessed:
    # astrological longitudes for J2000 should match the standard tables to a few arcminutes.
    lon, dec = _stars_at(np.full(1, J2000))
    ref = {"Regulus": 149.83, "Aldebaran": 69.79, "Antares": 249.77, "Spica": 203.84,
           "Sirius": 104.08, "Algol": 56.17, "Alcyone": 59.95, "Vega": 285.32, "Fomalhaut": 333.87}
    names = [s[0] for s in STARS]
    worst = 0.0
    for k, v in ref.items():
        got = float(lon[names.index(k), 0])
        worst = max(worst, abs(((got - v + 180) % 360) - 180))
    print(f"star check: worst |J2000 longitude - published table| = {worst*60:.1f} arcmin "
          f"over {len(ref)} named stars")
    assert worst < 0.25, "precession or catalogue transcription is wrong"

    bad = 0
    tot = 0
    for name, X in B.items():
        assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
        assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
        assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
        assert X.shape[1] >= 1, f"{name}: no columns"
        assert np.isfinite(X).all(), f"{name}: non-finite values"
        assert X.std(axis=0).max() > 1e-12, f"{name}: entirely constant"
        assert len(set(B)) == len(B)
        tot += X.shape[1]
    for name, X in B.items():
        a, u = quick(E, X)
        print(f"  {name:<46} {X.shape[1]:>5} cols   acc {100*a:5.2f}%   AUC {u:.4f}")
    print(f"\n{tot} columns across {len(B)} blocks")
    if bad:
        sys.exit(1)
    print("OK")
