"""declination_speed — three classical doctrines that need NO birth time and are absent from the
catalogue: DECLINATION (parallels / contraparallels / out-of-bounds), essential DIGNITY (the
five-fold table), and SPEED (apparent motion, retrogradation, combustion, synodic phase).

Everything here is a function of two ecliptic longitudes per body per partner, which is exactly what
Z gives.  Nothing needs an ascendant, a house or a birth hour, so nothing here is silently NaN for
the reason the angles are.  df.start is ALWAYS '0000-00-00' in this dataset and is NEVER read; the
only thing read out of df is the birth YEAR, and only to date the ayanamsa and the obliquity (see
below) — no feature is a function of the year alone.

WHY EACH DOCTRINE.

  1. DECLINATION.  Longitude says where two bodies stand around the zodiac; declination says how far
     north or south of the celestial equator they stand.  Two bodies at the SAME declination are in
     PARALLEL — read as a conjunction, a fusion, whether or not they are anywhere near each other in
     longitude.  Equal declinations of OPPOSITE sign are a CONTRAPARALLEL — read as an opposition.
     The doctrine matters here because a parallel is completely invisible to every longitude-based
     feature already in the catalogue: two bodies 100 degrees apart can be in exact parallel.
     The MOON OUT OF BOUNDS (declination beyond the obliquity, i.e. further north/south than the Sun
     ever reaches) is the classical signature of a nature that does not stay inside the rules — the
     single most cited declination indication in relationship work, and the reason it earns columns
     in a divorce-vs-death problem.

  2. DIGNITY.  A planet is strong or ruined by the SIGN and DEGREE it occupies: domicile, exaltation,
     triplicity, term (Egyptian bounds), face (Chaldean decan), against detriment, fall and being
     peregrine.  This is the classical measure of whether a body can act well.  Venus is the
     significator of marriage; a Venus in fall, or a Saturn dignified and a Venus peregrine, is the
     textbook reading for a marriage that holds together badly.  Sign and degree are all it needs.

  3. SPEED AND PHASE.  A body's APPARENT motion is not its mean motion: it is modulated by where the
     body stands in its synodic cycle relative to the Sun, and it turns RETROGRADE around opposition
     (outer bodies) or inferior conjunction (inner ones).  Retrogradation, combustion (being burnt by
     proximity to the Sun), cazimi, orientality and the Moon's swiftness are all accidental dignities
     in the classical scheme, and all of them are recoverable from two longitudes.

HOW THE ASTRONOMY IS DONE (and what would be wrong if it were done naively).

  * TROPICAL vs SIDEREAL.  Declination is an EQUATORIAL coordinate: it is a function of the TROPICAL
    longitude, measured from the vernal equinox.  Z holds SIDEREAL (Lahiri) longitudes.  Feeding a
    sidereal longitude into the declination formula is a silent ~24 degree error, which for a 1
    degree parallel orb is total nonsense.  So the module adds the Lahiri ayanamsa back, dated by the
    partner's own birth year (the ayanamsa drifts 50.29"/yr — 1.25 degrees across a 90-year sample,
    which is larger than the orb, so a single constant would not do either).  The obliquity is dated
    the same way.  Sign-based DIGNITY, by contrast, is left in the sidereal frame Z provides: that is
    the frame this project works in, the seven classical domiciles and exaltation SIGNS are identical
    in the Western and the Jyotisha tables, and terms/faces are sign-relative, so they are computed
    in the same frame.  A deliberate, stated choice, not an accident.

  * ECLIPTIC LATITUDE.  sin(decl) = sin(beta)cos(eps) + cos(beta)sin(eps)sin(lambda).  For the Sun
    and the two nodes beta is exactly 0.  For the MOON and MEAN LILITH (the lunar apogee) beta is
    recovered exactly to first order as 5.145*sin(lon - lon_node), because both lie in the lunar
    orbital plane and Z carries the true node — this is what makes an out-of-bounds Moon computable
    at all: with beta forced to 0 the formula can NEVER exceed the obliquity, so a naive
    implementation would report zero out-of-bounds Moons forever.  The remaining bodies are treated
    as on the ecliptic; the error in declination is about beta*cos(eps), which is under 2.5 degrees
    for Jupiter/Saturn/Uranus/Neptune, up to ~7 for Mercury/Mars/Chiron and up to ~17 for Pluto.
    Those bodies are therefore kept OUT of the "tight" declination aggregates, which are the honest
    ones; they still enter the full grid, where the error is a noise term and is named as such.

  * APPARENT SPEED AND RETROGRADATION are solved, not tabulated.  Given the body's geocentric
    longitude and the Sun's, the Earth's heliocentric direction is known (Sun + 180), so the ray from
    the Earth towards the body meets the body's (circular, coplanar) orbit at a solvable distance;
    from the two heliocentric positions and their mean motions the apparent d(lambda)/dt follows
    exactly.  The sign of that rate IS the retrograde flag — no hard-coded station elongations.  For
    an OUTER body the ray meets the orbit once, so the solution is unique.  For MERCURY and VENUS it
    meets it twice (near side / far side) and the longitudes genuinely cannot say which: their
    retrograde state is NOT emitted, only the necessary condition (inside the station elongation) and
    the combustion/orientality columns, which are exact.  Chiron is excluded from the speed block
    because e=0.38 makes a circular orbit meaningless for it.

ORDER-FREENESS.  Every cross-partner statistic is a max/min/sum/absolute-difference over the two
partners, or a sum over the FULL ordered body grid whose orb matrix is symmetric — swapping the
partners maps the grid onto its transpose and leaves every such statistic unchanged.  Named pairs are
symmetrised explicitly with np.fmax/np.fmin over the two observable directions.  No column is a raw
(a) or (b) quantity, so the model cannot learn column order in place of the doctrine.

MISSINGNESS.  NaN is propagated, never filled.  The Sun, Moon, Mercury, Venus and Mars resolve only
from a full date, so every column that needs one of them is NaN for a year-only birth date (~13-19%
of rows here) — including the whole speed/phase block, which needs the Sun.  Counts are built with a
NaN-aware indicator so an unknown body makes the count NaN rather than silently lowering it.  A
year-only block (Jupiter outwards plus the points) is emitted separately so the reading survives on
every row and cannot be confounded with how precisely a birth date was recorded.  Nothing is imputed.

Pure function of (df, Z): no I/O, no network, no randomness, no global state mutated.
"""

import math

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Bodies.  'ascendant'/'medium_coeli' are excluded: with no birth time they are
# always NaN and could only add empty columns.
# ---------------------------------------------------------------------------
BODIES = [
    'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus',
    'neptune', 'pluto', 'true_node', 'true_south_node', 'chiron', 'mean_lilith',
]
NB = len(BODIES)
IDX = {b: i for i, b in enumerate(BODIES)}

# Bodies that resolve from a YEAR alone; the rest need a full date.  Used for the
# coverage-stable declination block.
SLOW = ('jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
        'true_node', 'true_south_node', 'chiron', 'mean_lilith')

# Bodies whose declination is exact (beta known: 0, or recovered from the node).
# 'tight' adds the four whose ecliptic latitude never exceeds ~2.5 degrees, so
# the declination error stays well inside the parallel orb.
DECL_EXACT = ('sun', 'moon', 'true_node', 'true_south_node', 'mean_lilith')
DECL_TIGHT = DECL_EXACT + ('jupiter', 'saturn', 'uranus', 'neptune')

# Parallel orb hierarchy, mirroring the aspect-orb convention: the luminaries get
# the widest allowance, the planets a normal one, the computed points a tight one
# because a point is not a body.  Base orb 1.0 degree is the classical parallel orb.
PAR_ORB_BASE = 1.0
ORB_FACTOR = {
    'sun': 1.5, 'moon': 1.5,
    'mercury': 1.0, 'venus': 1.0, 'mars': 1.0, 'jupiter': 1.0, 'saturn': 1.0,
    'uranus': 1.0, 'neptune': 1.0, 'pluto': 1.0,
    'true_node': 0.75, 'true_south_node': 0.75, 'chiron': 0.75, 'mean_lilith': 0.75,
}
PAR_EXACT = 0.25          # "exact" parallel: a quarter degree of declination

# The declination pairs doctrine names.  A parallel between these is read exactly
# as a conjunction between them would be, and a contraparallel as an opposition.
DECL_PAIRS = [
    ('sun_moon', 'sun', 'moon'),        # the marriage contact of the two luminaries
    ('venus_mars', 'venus', 'mars'),    # attraction / desire
    ('sun_sun', 'sun', 'sun'),          # the two vitalities on the same latitude
    ('moon_moon', 'moon', 'moon'),      # shared emotional rhythm
    ('venus_saturn', 'venus', 'saturn'),# love met by duty/coldness — the hard-love pair
    ('moon_saturn', 'moon', 'saturn'),  # the pair most often blamed for coldness
]
# Bodies given their own individual declination columns.  Saturn is included even
# though it is not a luminary: it resolves from a YEAR alone, so its three columns
# are computable on every row, and it is the binding/limiting significator whose
# declination the doctrine reads alongside the Moon's.
DECL_SOLO = ('sun', 'moon', 'venus', 'mars', 'saturn')

# --- ayanamsa / obliquity ---------------------------------------------------
# Lahiri: 23.853 degrees at J2000.0, drifting 50.29 arcsec per year.
AYAN_J2000 = 23.853
AYAN_RATE = 50.29 / 3600.0
# IAU obliquity, linear term only (the quadratic terms are < 1e-5 deg over this sample).
EPS_J2000 = 23.4392911
EPS_RATE = -0.0130042 / 100.0        # degrees per year
LUNAR_INC = 5.145                    # inclination of the lunar orbit to the ecliptic

# --- orbits (coplanar circular model) --------------------------------------
# semi-major axis in AU, heliocentric mean motion in degrees/day.
ORBIT = {
    'mercury': (0.38710, 4.09234),
    'venus':   (0.72333, 1.60213),
    'earth':   (1.00000, 0.98561),
    'mars':    (1.52368, 0.52403),
    'jupiter': (5.20260, 0.08309),
    'saturn':  (9.55491, 0.03346),
    'uranus':  (19.21845, 0.01176),
    'neptune': (30.11039, 0.00602),
    'pluto':   (39.48168, 0.00397),
}
N_EARTH = math.radians(ORBIT['earth'][1])
OUTER_RETRO = ('mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto')
SPEED_BODIES = ('mars', 'jupiter', 'saturn')     # apparent speed worth its own columns
INNER = ('mercury', 'venus')

# Combustion thresholds (classical, in degrees of elongation from the Sun).
CAZIMI_DEG = 17.0 / 60.0     # "in the heart of the Sun" — 17 arcminutes
COMBUST_DEG = 8.5
BEAMS_DEG = 17.0
COMB_BODIES = ('mercury', 'venus', 'mars', 'jupiter', 'saturn')

# Earth's apsidal line and eccentricity, for the Sun's apparent speed.
SUN_PERIHELION_TROP = 283.0
EARTH_ECC = 0.01671
MOON_MEAN_SPEED = 13.17636
MOON_ECC = 0.0549

# ---------------------------------------------------------------------------
# The essential-dignity tables.
# ---------------------------------------------------------------------------
CLASSICAL = ('sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn')

# Traditional domicile rulers, sign 0 = Aries .. 11 = Pisces.  No modern rulers:
# the dignity scheme is only defined for the seven visible planets.
DOMICILE = ['mars', 'venus', 'mercury', 'moon', 'sun', 'mercury',
            'venus', 'mars', 'jupiter', 'saturn', 'saturn', 'jupiter']
# Exaltation SIGN of each classical planet (identical in the Western and the
# Jyotisha tables; only the exact degree differs between them, and no column here
# depends on the degree of exaltation).
EXALT_SIGN = {'sun': 0, 'moon': 1, 'mercury': 5, 'venus': 11,
              'mars': 9, 'jupiter': 3, 'saturn': 6}
# Dorothean triplicity rulers by element: (day ruler, night ruler).  Sect is NOT
# knowable without a birth time, so both hypotheses are carried: the score uses
# their mean and the day-minus-night SPREAD is emitted as its own column.
# element = sign % 4  ->  0 fire, 1 earth, 2 air, 3 water.
TRIPLICITY = {0: ('sun', 'jupiter'), 1: ('venus', 'moon'),
              2: ('saturn', 'mercury'), 3: ('venus', 'mars')}
# Egyptian bounds: (ending degree, ruler) per sign, boundaries at whole degrees.
EGYPT_TERMS = {
    0:  [(6, 'jupiter'), (12, 'venus'), (20, 'mercury'), (25, 'mars'), (30, 'saturn')],
    1:  [(8, 'venus'), (14, 'mercury'), (22, 'jupiter'), (27, 'saturn'), (30, 'mars')],
    2:  [(6, 'mercury'), (12, 'jupiter'), (17, 'venus'), (24, 'mars'), (30, 'saturn')],
    3:  [(7, 'mars'), (13, 'venus'), (19, 'mercury'), (26, 'jupiter'), (30, 'saturn')],
    4:  [(6, 'jupiter'), (11, 'venus'), (18, 'saturn'), (24, 'mercury'), (30, 'mars')],
    5:  [(7, 'mercury'), (17, 'venus'), (21, 'jupiter'), (28, 'mars'), (30, 'saturn')],
    6:  [(6, 'saturn'), (14, 'mercury'), (21, 'jupiter'), (28, 'venus'), (30, 'mars')],
    7:  [(7, 'mars'), (11, 'venus'), (19, 'mercury'), (24, 'jupiter'), (30, 'saturn')],
    8:  [(12, 'jupiter'), (17, 'venus'), (21, 'mercury'), (26, 'saturn'), (30, 'mars')],
    9:  [(7, 'mercury'), (14, 'jupiter'), (22, 'venus'), (26, 'saturn'), (30, 'mars')],
    10: [(7, 'mercury'), (13, 'venus'), (20, 'jupiter'), (25, 'mars'), (30, 'saturn')],
    11: [(12, 'venus'), (16, 'jupiter'), (19, 'mercury'), (28, 'mars'), (30, 'saturn')],
}
# Faces / decans run in Chaldean order from Aries 0 = Mars, one ruler per 10 degrees.
CHALDEAN = ('mars', 'sun', 'venus', 'mercury', 'moon', 'saturn', 'jupiter')

# Lilly's scores.
S_DOMICILE, S_EXALT, S_TRIP, S_TERM, S_FACE = 5.0, 4.0, 3.0, 2.0, 1.0
S_DETRIMENT, S_FALL, S_PEREGRINE = -5.0, -4.0, -5.0

BENEFICS = ('venus', 'jupiter')
MALEFICS = ('mars', 'saturn')


def _term_ruler(sign, deg_floor):
    for end, ruler in EGYPT_TERMS[sign]:
        if deg_floor < end:
            return ruler
    return EGYPT_TERMS[sign][-1][1]


def _build_dignity_tables():
    """Precompute, once at import, the dignity of every (planet, sign, whole degree).

    Pure constants — no I/O, nothing read from df or Z.  Indexing a table by an
    integer sign/degree keeps the per-row work to a gather and makes it impossible
    for a NaN to reach a lookup (the caller masks instead of indexing with NaN).

    Returned tables, all indexed [planet, sign, degree] unless noted:
      score      mean-sect essential dignity (Lilly's numbers)
      spread     day-score minus night-score (the triplicity ambiguity, [planet, sign])
      dom/exa/det/fal   0/1 flags at [planet, sign]
      pereg      0/1 peregrine (no dignity of any of the five kinds)
    """
    np_ = len(CLASSICAL)
    score = np.zeros((np_, 12, 30), dtype=np.float64)
    spread = np.zeros((np_, 12), dtype=np.float64)
    dom = np.zeros((np_, 12), dtype=np.float64)
    exa = np.zeros((np_, 12), dtype=np.float64)
    det = np.zeros((np_, 12), dtype=np.float64)
    fal = np.zeros((np_, 12), dtype=np.float64)
    pereg = np.zeros((np_, 12, 30), dtype=np.float64)

    for pi, p in enumerate(CLASSICAL):
        dom_signs = {s for s in range(12) if DOMICILE[s] == p}
        det_signs = {(s + 6) % 12 for s in dom_signs}
        ex_sign = EXALT_SIGN[p]
        fall_sign = (ex_sign + 6) % 12
        for s in range(12):
            day_r, night_r = TRIPLICITY[s % 4]
            is_day = (day_r == p)
            is_night = (night_r == p)
            # Sect is unknowable here, so the score carries the MEAN of the two
            # hypotheses and the difference is reported separately rather than
            # one of them being asserted.
            trip_mean = S_TRIP * 0.5 * (float(is_day) + float(is_night))
            spread[pi, s] = S_TRIP * (float(is_day) - float(is_night))
            base = 0.0
            if s in dom_signs:
                base += S_DOMICILE
                dom[pi, s] = 1.0
            elif s == ex_sign:
                base += S_EXALT
                exa[pi, s] = 1.0
            if s in det_signs:
                base += S_DETRIMENT
                det[pi, s] = 1.0
            if s == fall_sign:
                base += S_FALL
                fal[pi, s] = 1.0
            base += trip_mean
            for d in range(30):
                v = base
                has_term = (_term_ruler(s, d) == p)
                has_face = (CHALDEAN[(s * 3 + d // 10) % 7] == p)
                if has_term:
                    v += S_TERM
                if has_face:
                    v += S_FACE
                # Peregrine: not dignified by ANY of the five.  Detriment and fall
                # are separate debilities and stack with it, as in Lilly.
                if not (s in dom_signs or s == ex_sign or is_day or is_night
                        or has_term or has_face):
                    v += S_PEREGRINE
                    pereg[pi, s, d] = 1.0
                score[pi, s, d] = v
    return score, spread, dom, exa, det, fal, pereg


DIG_SCORE, DIG_SPREAD, DIG_DOM, DIG_EXA, DIG_DET, DIG_FAL, DIG_PEREG = _build_dignity_tables()
# Domicile ruler of each sign, as an index into CLASSICAL — for mutual reception.
DOM_RULER_IDX = np.array([CLASSICAL.index(DOMICILE[s]) for s in range(12)], dtype=np.int64)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _theta(Z, slot, half, n):
    """(n, 14) sidereal longitudes for one partner, columns in BODIES order.

    Resolved by NAME out of Z['bodies'] so a reordered npz cannot silently shuffle
    the bodies.  A body missing from the npz yields an all-NaN column, which keeps
    the returned width constant instead of dropping features."""
    T = np.asarray(Z['theta_%s_%s' % (slot, half)], dtype=np.float64)
    if T.ndim != 2 or T.shape[0] != n:
        raise ValueError('theta_%s_%s has shape %r, expected (%d, k)'
                         % (slot, half, T.shape, n))
    names = [str(x) for x in np.asarray(Z['bodies']).ravel().tolist()]
    where = {nm: i for i, nm in enumerate(names)}
    out = np.full((n, NB), np.nan, dtype=np.float64)
    for k, b in enumerate(BODIES):
        j = where.get(b)
        if j is not None and j < T.shape[1]:
            out[:, k] = T[:, j]
    # A longitude of exactly 360.0 occurs in this npz; fold it to 0 so that
    # floor(lon/30) can never produce sign index 12 and walk off a lookup table.
    return np.mod(out, 360.0)


def _frac_year(s):
    """Fractional year of a 'YYYY-MM-DD' string, NaN when no year was recorded.

    Handles all four shapes: full, 'YYYY-00-00' (year only), '0000-MM-DD' (year
    unknown!) and '0000-00-00' (absent).  Used ONLY to date the ayanamsa and the
    obliquity, both of which drift smoothly; when the month/day are missing the
    year midpoint is used, an error of at most half a year = 0.007 degrees of
    ayanamsa, which is two orders of magnitude below the 1 degree parallel orb.
    A missing YEAR is not guessed — it returns NaN and every declination for that
    partner follows it to NaN."""
    if not isinstance(s, str):
        return np.nan
    p = s.strip().split('-')
    if len(p) != 3:
        return np.nan
    ys, ms, ds = p[0], p[1], p[2]
    if not (ys.isdigit() and int(ys) > 0):
        return np.nan
    y = int(ys)
    if ms.isdigit() and ds.isdigit() and 0 < int(ms) <= 12 and 0 < int(ds) <= 31:
        doy = (int(ms) - 1) * 30.44 + int(ds)
        return y + (doy - 0.5) / 365.25
    return y + 0.5


def _has_daymonth(s):
    """True when the string carries a real month AND day (not '00')."""
    if not isinstance(s, str):
        return False
    p = s.strip().split('-')
    if len(p) != 3:
        return False
    return p[1].isdigit() and p[2].isdigit() and int(p[1]) > 0 and int(p[2]) > 0


def _col(df, name, n):
    if name in df.columns:
        return df[name].tolist()
    return [None] * n


def _declination(lon, fy):
    """(n, 14) declination in degrees from (n, 14) SIDEREAL longitudes.

    Two corrections a naive implementation would miss, both material:
      * the ayanamsa is added back, dated by the partner's own birth year, because
        declination is a function of TROPICAL longitude;
      * the Moon and mean Lilith are given their real ecliptic latitude from the
        true node (both lie in the lunar orbital plane), which is the only reason
        an out-of-bounds Moon can be detected at all.
    Every other body is treated as on the ecliptic — an approximation, named as
    such, and excluded from the 'tight' aggregates."""
    ayan = AYAN_J2000 + (fy - 2000.0) * AYAN_RATE          # (n,), NaN if no year
    eps = EPS_J2000 + (fy - 2000.0) * EPS_RATE             # (n,)
    lam = np.radians(np.mod(lon + ayan[:, None], 360.0))   # tropical longitude
    beta = np.zeros_like(lon)
    node = lon[:, IDX['true_node']]
    for b in ('moon', 'mean_lilith'):
        k = IDX[b]
        # beta = i * sin(lon - node): frame-invariant, so the sidereal difference
        # is the right argument and no ayanamsa is needed here.
        beta[:, k] = LUNAR_INC * np.sin(np.radians(lon[:, k] - node))
    br = np.radians(beta)
    er = np.radians(eps)[:, None]
    sd = np.sin(br) * np.cos(er) + np.cos(br) * np.sin(er) * np.sin(lam)
    return np.degrees(np.arcsin(np.clip(sd, -1.0, 1.0))), eps


def _tri(dist, orb):
    """Triangular orb membership: 1 at exactitude, falling linearly to 0 at the orb
    edge.  np.maximum (not a clipped comparison) so NaN stays NaN instead of
    collapsing to 'no contact'."""
    return np.maximum(0.0, 1.0 - dist / orb)


def _safe_div(num, den):
    """num/den with den <= 0 -> NaN, never a fabricated zero."""
    num = np.asarray(num, dtype=np.float64)
    den = np.asarray(den, dtype=np.float64)
    out = np.full(num.shape, np.nan, dtype=np.float64)
    ok = den > 0
    np.divide(num, np.where(ok, den, 1.0), out=out, where=ok)
    return out


def _flag(src, cond):
    """0/1 indicator that stays NaN wherever `src` is unknown.

    A bare comparison against NaN is False, which would silently turn 'we do not
    know' into 'no' and quietly lower every count built on it.  Everything
    countable in this module goes through here."""
    return np.where(np.isfinite(src), np.asarray(cond, dtype=np.float64), np.nan)


def _elong(lon_body, lon_sun):
    """Signed elongation from the Sun in (-180, 180]: negative = oriental (rises
    before the Sun, a morning star), positive = occidental.  Frame-invariant, so
    the sidereal longitudes can be used directly."""
    return np.mod(lon_body - lon_sun + 180.0, 360.0) - 180.0


def _apparent_speed(lon_p, lon_sun, body):
    """Apparent geocentric d(longitude)/dt in degrees/day for an OUTER body.

    Coplanar circular orbits.  The Earth's heliocentric direction is the Sun's
    geocentric longitude + 180.  The body lies along the unit vector u at
    geocentric distance delta, with |E + delta*u| = r_p; for r_p > 1 the quadratic
    has exactly one positive root, so the geometry is unambiguous.  The rate then
    follows from the two heliocentric velocities as cross(G, dG)/|G|^2.  The SIGN
    of the returned rate is the retrograde flag — derived, not tabulated.
    (Sanity: Mars at exact opposition returns about -0.36 deg/day, against a real
    peak retrograde rate near -0.4.)"""
    r_p, n_p_deg = ORBIT[body]
    n_p = math.radians(n_p_deg)
    LE = np.radians(np.mod(lon_sun + 180.0, 360.0))
    lp = np.radians(lon_p)
    ux, uy = np.cos(lp), np.sin(lp)
    ex, ey = np.cos(LE), np.sin(LE)
    b = ex * ux + ey * uy
    disc = b * b - 1.0 + r_p * r_p                 # > 0 for every outer body
    delta = -b + np.sqrt(np.maximum(disc, 0.0))    # NaN propagates through maximum
    px, py = ex + delta * ux, ey + delta * uy
    vex, vey = -N_EARTH * ey, N_EARTH * ex
    vpx, vpy = -n_p * py, n_p * px                 # |v| = n * r_p
    gx, gy = px - ex, py - ey
    dgx, dgy = vpx - vex, vpy - vey
    g2 = gx * gx + gy * gy
    return np.degrees(_safe_div(gx * dgy - gy * dgx, g2))


def _sign_degree(lon_body):
    """(sign 0-11, whole degree 0-29, finite mask) for one body's longitudes.

    NaN NEVER reaches an index: the indices are computed on a zero-filled copy and
    the caller masks the RESULT back to NaN.  Longitudes are already folded to
    [0, 360) by _theta, so the sign index cannot reach 12; the clips are belt and
    braces against a float landing exactly on a boundary."""
    fin = np.isfinite(lon_body)
    safe = np.where(fin, lon_body, 0.0)
    sidx = np.clip(np.floor(safe / 30.0), 0, 11).astype(np.int64)
    didx = np.clip(np.floor(safe - 30.0 * sidx), 0, 29).astype(np.int64)
    return sidx, didx, fin


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build(df, Z, half):
    n = len(df)
    cols = []
    names = []

    def add(name, v):
        cols.append(np.asarray(v, dtype=np.float64).reshape(n))
        names.append(name)

    A = _theta(Z, 'a', half, n)
    B = _theta(Z, 'b', half, n)

    dob_a = _col(df, 'dob_a', n)
    dob_b = _col(df, 'dob_b', n)
    fy_a = np.array([_frac_year(s) for s in dob_a], dtype=np.float64)
    fy_b = np.array([_frac_year(s) for s in dob_b], dtype=np.float64)
    md_a = np.array([1.0 if _has_daymonth(s) else 0.0 for s in dob_a])
    md_b = np.array([1.0 if _has_daymonth(s) else 0.0 for s in dob_b])

    dA, eps_a = _declination(A, fy_a)
    dB, eps_b = _declination(B, fy_b)

    fac = np.array([ORB_FACTOR[b] for b in BODIES], dtype=np.float64)
    # A pair's orb is the WIDER of the two allowances: symmetric in (i, j), which
    # is what keeps every grid aggregate order-free.
    orb_pair = (PAR_ORB_BASE * np.maximum(fac[:, None], fac[None, :])).reshape(-1)
    tight_mask = np.array([b in DECL_TIGHT for b in BODIES])
    slow_mask = np.array([b in SLOW for b in BODIES])
    tight_pair = np.outer(tight_mask, tight_mask).reshape(-1)
    slow_pair = np.outer(slow_mask, slow_mask).reshape(-1)

    # Declination grids.  par = |d_a - d_b| (same declination, same side = parallel,
    # read as a conjunction);  cpar = |d_a + d_b| (equal and opposite = contraparallel,
    # read as an opposition).
    g_par3 = np.abs(dA[:, :, None] - dB[:, None, :])
    g_cpar3 = np.abs(dA[:, :, None] + dB[:, None, :])
    g_par = g_par3.reshape(n, NB * NB)
    g_cpar = g_cpar3.reshape(n, NB * NB)
    valid = np.isfinite(g_par)
    nv = valid.sum(axis=1).astype(np.float64)
    nv_tight = valid[:, tight_pair].sum(axis=1).astype(np.float64)
    nv_slow = valid[:, slow_pair].sum(axis=1).astype(np.float64)
    have = nv > 0

    w_par = _tri(g_par, orb_pair[None, :])
    w_cpar = _tri(g_cpar, orb_pair[None, :])

    # ---------------- A. coverage / date precision (4) ----------------
    # Missingness made legible instead of hidden inside the aggregates: a reading
    # with 81 computable declination pairs is not the same reading as one with 196.
    add('ds_cov_decl_pairs', nv)
    ka = np.isfinite(dA).sum(axis=1).astype(np.float64)
    kb = np.isfinite(dB).sum(axis=1).astype(np.float64)
    add('ds_cov_bodies_max', np.maximum(ka, kb))     # order-free: max/min, never (a,b)
    add('ds_cov_bodies_min', np.minimum(ka, kb))
    add('ds_prec_n_daymonth', md_a + md_b)           # 0/1/2 dobs carrying month+day

    # ---------------- B. declination grid (12) ----------------
    # Sums over the FULL ordered 14x14 grid with a symmetric orb matrix: swapping
    # the partners transposes the grid, so every statistic below is order-free.
    add('ds_decl_par_wn', _safe_div(np.nansum(w_par, axis=1), nv))
    add('ds_decl_cpar_wn', _safe_div(np.nansum(w_cpar, axis=1), nv))
    ex_par = _flag(g_par, g_par < PAR_EXACT)
    ex_cpar = _flag(g_cpar, g_cpar < PAR_EXACT)
    add('ds_decl_par_n_exact', np.where(have, np.nansum(ex_par, axis=1), np.nan))
    add('ds_decl_cpar_n_exact', np.where(have, np.nansum(ex_cpar, axis=1), np.nan))
    par_inf = np.where(valid, g_par, np.inf)
    cpar_inf = np.where(valid, g_cpar, np.inf)
    add('ds_decl_par_min', np.where(have, par_inf.min(axis=1), np.nan))
    add('ds_decl_cpar_min', np.where(have, cpar_inf.min(axis=1), np.nan))
    # The honest sub-grid: only the bodies whose declination is exact or whose
    # ecliptic latitude is under ~2.5 degrees, so the approximation error stays
    # far inside the orb.
    add('ds_decl_tight_par_wn',
        _safe_div(np.nansum(w_par[:, tight_pair], axis=1), nv_tight))
    add('ds_decl_tight_cpar_wn',
        _safe_div(np.nansum(w_cpar[:, tight_pair], axis=1), nv_tight))
    add('ds_decl_tight_par_min',
        np.where(nv_tight > 0, par_inf[:, tight_pair].min(axis=1), np.nan))
    # The coverage-stable sub-grid: the nine bodies that resolve from a YEAR alone,
    # so these three are computable on every row and cannot be confounded with how
    # precisely the birth dates were recorded.
    add('ds_decl_slow_par_wn',
        _safe_div(np.nansum(w_par[:, slow_pair], axis=1), nv_slow))
    add('ds_decl_slow_cpar_wn',
        _safe_div(np.nansum(w_cpar[:, slow_pair], axis=1), nv_slow))
    add('ds_decl_slow_par_min',
        np.where(nv_slow > 0, par_inf[:, slow_pair].min(axis=1), np.nan))

    # ---------------- C. named declination pairs (12) ----------------
    # For an unordered body pair {X, Y} the synastry offers two contacts, (A.X, B.Y)
    # and (A.Y, B.X); swapping the partners merely exchanges them, so np.fmax over
    # the two is order-free — and it is also the doctrine, which asks whether the
    # contact is there at all, i.e. in its stronger direction.  fmax ignores a NaN
    # direction and returns NaN only when BOTH are unknown.
    for pname, bx, by in DECL_PAIRS:
        i, j = IDX[bx], IDX[by]
        orb = PAR_ORB_BASE * max(fac[i], fac[j])
        p_ab = _tri(np.abs(dA[:, i] - dB[:, j]), orb)
        p_ba = _tri(np.abs(dA[:, j] - dB[:, i]), orb)
        c_ab = _tri(np.abs(dA[:, i] + dB[:, j]), orb)
        c_ba = _tri(np.abs(dA[:, j] + dB[:, i]), orb)
        add('ds_decl_%s_parallel' % pname, np.fmax(p_ab, p_ba))
        add('ds_decl_%s_contra' % pname, np.fmax(c_ab, c_ba))

    # ---------------- D. individual declinations (16) ----------------
    # How far north/south each partner's body stands, and whether the two partners
    # share a hemisphere.  |declination| is the "extremity" the doctrine reads;
    # max/min over the partners keeps it order-free, and same-hemisphere is
    # symmetric by construction.
    for b in DECL_SOLO:
        k = IDX[b]
        aa, bb = np.abs(dA[:, k]), np.abs(dB[:, k])
        add('ds_decl_%s_abs_max' % b, np.fmax(aa, bb))
        add('ds_decl_%s_abs_min' % b, np.fmin(aa, bb))
        same = _flag(dA[:, k] + dB[:, k], np.sign(dA[:, k]) == np.sign(dB[:, k]))
        add('ds_decl_%s_same_hemi' % b, same)
    slow_same = np.zeros(n)
    for b in SLOW:
        k = IDX[b]
        slow_same = slow_same + _flag(dA[:, k] + dB[:, k],
                                      np.sign(dA[:, k]) == np.sign(dB[:, k]))
    add('ds_decl_slow_same_hemi_n', slow_same)       # 0..9, NaN if any is unknown

    # ---------------- E. out-of-bounds Moon (1) ----------------
    # Beyond the obliquity the Moon stands further north/south than the Sun ever
    # reaches: the classical "outside the rules" signature.  Only computable because
    # the Moon's latitude was recovered from the node above.
    exc_a = np.abs(dA[:, IDX['moon']]) - eps_a
    exc_b = np.abs(dB[:, IDX['moon']]) - eps_b
    add('ds_oob_moon_n', _flag(exc_a, exc_a > 0) + _flag(exc_b, exc_b > 0))
    # No continuous "excess" twin: the obliquity is all but constant across this
    # sample, so |decl| - eps is ds_decl_moon_abs_* shifted by a constant — it
    # measured at r = 1.000 against those columns.  The threshold count above is
    # the part of the doctrine they do NOT already carry.

    # ---------------- F. essential dignity, per planet (14) ----------------
    dig_a = {}
    dig_b = {}
    cnt = {k: np.zeros(n) for k in ('dom', 'exa', 'det', 'fal', 'pereg')}
    tot_a = np.zeros(n)
    tot_b = np.zeros(n)
    spread_tot = np.zeros(n)
    sign_a = np.zeros((n, len(CLASSICAL)), dtype=np.int64)
    sign_b = np.zeros((n, len(CLASSICAL)), dtype=np.int64)
    fin_a = np.zeros((n, len(CLASSICAL)), dtype=bool)
    fin_b = np.zeros((n, len(CLASSICAL)), dtype=bool)
    for pi, p in enumerate(CLASSICAL):
        k = IDX[p]
        for lon, store, sg, fn in ((A[:, k], dig_a, sign_a, fin_a),
                                   (B[:, k], dig_b, sign_b, fin_b)):
            sidx, didx, fin = _sign_degree(lon)
            sg[:, pi] = sidx
            fn[:, pi] = fin
            store[p] = np.where(fin, DIG_SCORE[pi, sidx, didx], np.nan)
            store[p + '_spread'] = np.where(fin, DIG_SPREAD[pi, sidx], np.nan)
            for key, tbl in (('dom', DIG_DOM), ('exa', DIG_EXA),
                             ('det', DIG_DET), ('fal', DIG_FAL)):
                store[p + '_' + key] = np.where(fin, tbl[pi, sidx], np.nan)
            store[p + '_pereg'] = np.where(fin, DIG_PEREG[pi, sidx, didx], np.nan)
        # order-free per-planet dignity: the better-placed and the worse-placed of
        # the two partners, never (a, b)
        add('ds_dig_%s_max' % p, np.fmax(dig_a[p], dig_b[p]))
        add('ds_dig_%s_min' % p, np.fmin(dig_a[p], dig_b[p]))
        tot_a = tot_a + dig_a[p]                     # plain +, so NaN survives
        tot_b = tot_b + dig_b[p]
        spread_tot = spread_tot + dig_a[p + '_spread'] + dig_b[p + '_spread']
        for key in ('dom', 'exa', 'det', 'fal', 'pereg'):
            cnt[key] = cnt[key] + dig_a[p + '_' + key] + dig_b[p + '_' + key]

    # ---------------- G. dignity totals, counts, receptions (17) ----------------
    add('ds_dig_total_max', np.fmax(tot_a, tot_b))
    add('ds_dig_total_min', np.fmin(tot_a, tot_b))
    add('ds_dig_total_sum', tot_a + tot_b)
    add('ds_dig_total_absdiff', np.abs(tot_a - tot_b))
    # How much the unknown sect could move the totals.  Sect needs an ascendant and
    # there is no birth time, so the score above carries the MEAN of the diurnal and
    # nocturnal readings and this column carries what is at stake in that guess.
    add('ds_dig_sect_spread_sum', spread_tot)
    add('ds_dig_n_domicile', cnt['dom'])
    add('ds_dig_n_exalt', cnt['exa'])
    add('ds_dig_n_detriment', cnt['det'])
    add('ds_dig_n_fall', cnt['fal'])
    add('ds_dig_n_peregrine', cnt['pereg'])
    # The benefics carrying the marriage vs the malefics carrying it: the classical
    # reading of a union that holds badly is dignified malefics over ruined benefics.
    ben_a = sum(dig_a[p] for p in BENEFICS)
    ben_b = sum(dig_b[p] for p in BENEFICS)
    mal_a = sum(dig_a[p] for p in MALEFICS)
    mal_b = sum(dig_b[p] for p in MALEFICS)
    add('ds_dig_benefic_sum', ben_a + ben_b)
    add('ds_dig_malefic_sum', mal_a + mal_b)
    add('ds_dig_malefic_minus_benefic', (mal_a + mal_b) - (ben_a + ben_b))
    # Venus is the significator of marriage; her debility is the single most cited
    # essential-dignity indication in this doctrine.
    add('ds_dig_venus_debil_n',
        dig_a['venus_det'] + dig_a['venus_fal'] + dig_b['venus_det'] + dig_b['venus_fal'])
    # Mutual reception by domicile: two planets each in the other's own sign — the
    # classical rescue, two bodies that co-operate however badly placed they are.
    rec_a = np.zeros(n)
    rec_b = np.zeros(n)
    for i in range(len(CLASSICAL)):
        for j in range(i + 1, len(CLASSICAL)):
            for sg, fn, out in ((sign_a, fin_a, 'a'), (sign_b, fin_b, 'b')):
                ok = fn[:, i] & fn[:, j]
                hit = (DOM_RULER_IDX[sg[:, i]] == j) & (DOM_RULER_IDX[sg[:, j]] == i)
                v = np.where(ok, hit.astype(np.float64), np.nan)
                if out == 'a':
                    rec_a = rec_a + v
                else:
                    rec_b = rec_b + v
    add('ds_recep_max', np.fmax(rec_a, rec_b))
    add('ds_recep_min', np.fmin(rec_a, rec_b))
    add('ds_recep_sum', rec_a + rec_b)

    # ---------------- H. combustion and orientality (10) ----------------
    # Exact from two longitudes: how far a planet stands from the Sun.  Inside 8.5
    # degrees it is COMBUST (burnt, its significations spoiled); inside 17 arcminutes
    # it is CAZIMI (in the heart of the Sun, the one place proximity strengthens it);
    # inside 17 degrees it is under the beams.  The sign of the elongation is
    # orientality (morning vs evening star).
    sun_a, sun_b = A[:, IDX['sun']], B[:, IDX['sun']]
    el_a = {b: _elong(A[:, IDX[b]], sun_a) for b in COMB_BODIES}
    el_b = {b: _elong(B[:, IDX[b]], sun_b) for b in COMB_BODIES}
    n_caz = np.zeros(n); n_com = np.zeros(n); n_beam = np.zeros(n); n_ori = np.zeros(n)
    for b in COMB_BODIES:
        for e in (el_a[b], el_b[b]):
            ae = np.abs(e)
            n_caz = n_caz + _flag(e, ae < CAZIMI_DEG)
            n_com = n_com + _flag(e, ae < COMBUST_DEG)
            n_beam = n_beam + _flag(e, ae < BEAMS_DEG)
            n_ori = n_ori + _flag(e, e < 0.0)
    add('ds_comb_n_cazimi', n_caz)
    add('ds_comb_n_combust', n_com)
    add('ds_comb_n_beams', n_beam)
    add('ds_comb_n_oriental', n_ori)
    for b in ('mercury', 'venus', 'mars'):
        add('ds_elong_%s_absmax' % b, np.fmax(np.abs(el_a[b]), np.abs(el_b[b])))
        add('ds_elong_%s_absmin' % b, np.fmin(np.abs(el_a[b]), np.abs(el_b[b])))

    # ---------------- I. apparent speed (11) ----------------
    # The Sun's apparent speed is the equation of centre — swift near perihelion in
    # January, slow near aphelion in July; a function of the tropical longitude alone.
    def _sun_speed(sun, fy):
        ayan = AYAN_J2000 + (fy - 2000.0) * AYAN_RATE
        trop = np.radians(np.mod(sun + ayan, 360.0) - SUN_PERIHELION_TROP)
        return ORBIT['earth'][1] * (1.0 + 2.0 * EARTH_ECC * np.cos(trop))

    vs_a, vs_b = _sun_speed(sun_a, fy_a), _sun_speed(sun_b, fy_b)
    add('ds_spd_sun_max', np.fmax(vs_a, vs_b))
    add('ds_spd_sun_min', np.fmin(vs_a, vs_b))

    # The Moon's speed is set by its distance from PERIGEE, and mean Lilith IS the
    # mean apogee, so perigee = Lilith + 180.  Swift vs slow Moon is a classical
    # accidental dignity, and this is the only route to it without an ephemeris.
    def _moon_speed(T):
        anom = np.radians(T[:, IDX['moon']] - (T[:, IDX['mean_lilith']] + 180.0))
        return MOON_MEAN_SPEED * (1.0 + 2.0 * MOON_ECC * np.cos(anom))

    vm_a, vm_b = _moon_speed(A), _moon_speed(B)
    add('ds_spd_moon_max', np.fmax(vm_a, vm_b))
    add('ds_spd_moon_min', np.fmin(vm_a, vm_b))
    add('ds_spd_moon_n_swift',
        _flag(vm_a, vm_a > MOON_MEAN_SPEED) + _flag(vm_b, vm_b > MOON_MEAN_SPEED))

    spd_a = {b: _apparent_speed(A[:, IDX[b]], sun_a, b) for b in OUTER_RETRO}
    spd_b = {b: _apparent_speed(B[:, IDX[b]], sun_b, b) for b in OUTER_RETRO}
    for b in SPEED_BODIES:
        add('ds_spd_%s_max' % b, np.fmax(spd_a[b], spd_b[b]))
        add('ds_spd_%s_min' % b, np.fmin(spd_a[b], spd_b[b]))

    # ---------------- J. retrogradation (9) ----------------
    # The flag IS the sign of the solved apparent rate — no station elongations are
    # hard-coded, and the ambiguous inner planets are deliberately absent.
    r_a = {b: _flag(spd_a[b], spd_a[b] < 0.0) for b in OUTER_RETRO}
    r_b = {b: _flag(spd_b[b], spd_b[b] < 0.0) for b in OUTER_RETRO}
    for b in OUTER_RETRO:                            # all six, 0/1/2, order-free
        add('ds_retro_n_%s' % b, r_a[b] + r_b[b])
    tot_r = np.zeros(n); both_r = np.zeros(n); one_r = np.zeros(n)
    for b in OUTER_RETRO:
        tot_r = tot_r + r_a[b] + r_b[b]
        both_r = both_r + r_a[b] * r_b[b]
        one_r = one_r + np.abs(r_a[b] - r_b[b])
    add('ds_retro_n_total', tot_r)                   # 0..12
    # (no normalised twin: it would be tot_r/12 exactly, a collinear duplicate)
    add('ds_retro_n_both', both_r)                   # bodies retrograde for BOTH
    add('ds_retro_n_one', one_r)                     # retrograde for exactly one
    # Mercury and Venus: the geometry admits two solutions and the longitudes cannot
    # choose between them, so only the NECESSARY condition is emitted — inside the
    # greatest elongation, where a retrograde is possible at all.
    n_inner_poss = np.zeros(n)
    for b in INNER:
        max_el = math.degrees(math.asin(ORBIT[b][0]))
        for e in (el_a[b], el_b[b]):
            n_inner_poss = n_inner_poss + _flag(e, np.abs(e) < max_el)
    add('ds_retro_inner_possible_n', n_inner_poss)

    # ---------------- K. matching synodic phases (6) ----------------
    # Two partners born at the same point of a body's synodic cycle stand in the same
    # relation to the Sun — the same retrograde loop, the same visibility.  cos of the
    # difference is order-free (an even function) and is 1 at a shared phase, -1 at
    # opposite phases.
    n_close = np.zeros(n)
    for b in OUTER_RETRO:
        ea, eb = _elong(A[:, IDX[b]], sun_a), _elong(B[:, IDX[b]], sun_b)
        d = np.mod(ea - eb, 360.0)
        d = np.minimum(d, 360.0 - d)
        if b in ('mars', 'jupiter', 'saturn', 'uranus', 'neptune'):
            add('ds_phase_cos_%s' % b, np.cos(np.radians(ea - eb)))
        n_close = n_close + _flag(d, d < 30.0)
    add('ds_phase_n_close', n_close)

    # ---------------- L. lunation (6) ----------------
    # The Moon's elongation from the Sun IS the lunar phase: 0 new, 180 full.  The
    # phase at birth is read as the temperament of the life (balsamic = an ending,
    # full = a culmination), and two partners on the same phase share it.
    ph_a = np.mod(A[:, IDX['moon']] - sun_a, 360.0)
    ph_b = np.mod(B[:, IDX['moon']] - sun_b, 360.0)
    il_a = 0.5 * (1.0 - np.cos(np.radians(ph_a)))    # illuminated fraction, 0..1
    il_b = 0.5 * (1.0 - np.cos(np.radians(ph_b)))
    add('ds_lun_illum_max', np.fmax(il_a, il_b))
    add('ds_lun_illum_min', np.fmin(il_a, il_b))
    dph = np.mod(ph_a - ph_b, 360.0)
    add('ds_lun_phase_absdiff', np.minimum(dph, 360.0 - dph))
    add('ds_lun_phase_cos', np.cos(np.radians(ph_a - ph_b)))
    add('ds_lun_n_balsamic', _flag(ph_a, ph_a >= 315.0) + _flag(ph_b, ph_b >= 315.0))
    add('ds_lun_n_full',
        _flag(ph_a, np.abs(ph_a - 180.0) < 22.5) + _flag(ph_b, np.abs(ph_b - 180.0) < 22.5))

    X = np.stack(cols, axis=1).astype(np.float32)
    assert X.shape == (n, len(names)), (X.shape, len(names))
    assert len(set(names)) == len(names), 'duplicate feature name'
    return X, names
