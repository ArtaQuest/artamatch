"""cyclical_time — the long-cycle / generational layer of the doctrine.

WHY THIS MODULE EXISTS.  Every other block in the catalogue that says anything interesting leans on
the fast bodies (sun, moon, mercury, venus, mars), and those need a DAY to resolve.  A large share of
this set carries 'YYYY-00-00' — a year and nothing else — so those blocks are NaN for that share.
The slow bodies do not have that problem: Jupiter through Pluto, the lunar nodes, Chiron and Lilith
move so little in twelve months that a YEAR ALONE pins them to within a sign or better.  Astrology
has always read those bodies as GENERATIONAL signatures — "Pluto in Virgo", "the Uranus-Pluto
conjunction of the sixties" — and that reading is exactly the one that survives at year precision.
So this module is the block that is computable for essentially every row that has two birth years.

WHAT IT ENCODES, in four doctrines:

  1. PLACEMENT (generational signature).  Which SIGN each slow body occupied at each birth, and
     whether the two partners share it.  A shared Pluto sign is the astrological definition of
     "the same generation"; a shared triplicity (element) or quadruplicity (modality) is the
     weaker, wider version of the same claim.

  2. THE MUNDANE CYCLES.  Classical mundane astrology reads history not through single planets but
     through the SYNODIC CYCLES of pairs of slow planets — Jupiter-Saturn (the ~20y "great
     conjunction", the cycle of social order), Saturn-Uranus, Saturn-Neptune, Saturn-Pluto,
     Uranus-Neptune, Uranus-Pluto and Neptune-Pluto.  A cycle's PHASE at a birth is the angular
     distance from the faster body to the slower one: 0 deg = conjunction (the seed of the cycle),
     180 deg = opposition (its full flowering).  Every birth sits somewhere in each of these seven
     cycles, and where it sits is the mundane astrologer's statement about the world that person
     was born into.  This module evaluates all seven at BOTH births, and takes the PHASE DIFFERENCE
     between them.

  3. RETURNS.  A "return" is a body coming back to where it started.  The doctrine is that a Saturn
     return (29.5y) is a hard threshold of maturity, a nodal return (18.6y) a karmic one, a Jupiter
     return (11.9y) an expansive one.  Two people born N years apart are separated by N/29.5 Saturn
     returns — and the doctrine reads the FRACTIONAL part of that (are they in the same phase of the
     Saturn cycle, or in opposite phases?) as different from the integer count.

  4. GENERATIONAL DISTANCE.  The summed phase difference across all seven mundane cycles.  This is
     the astrological answer to "how far apart are these two people's generations", and it is
     deliberately NOT the age gap in years.  Two births 20 years apart sit at the SAME point of the
     Jupiter-Saturn cycle (one full turn) but a sixth of the way around Saturn-Pluto and almost
     nowhere at all in Neptune-Pluto; two births 250 years apart can land back near-conjunct in the
     slow cycles.  The sum of the seven circular separations is therefore a genuinely different
     quantity from |year_a - year_b| — the module also emits a coherence measure (the circular
     resultant across cycles) that says whether the seven cycles AGREE about the displacement.

ORDER-FREENESS.  There is no "first" partner here.  Every column is a symmetric function of the two
charts: circular separations use |.| (symmetric by construction), placements are reported as
min/max of the two sign indices, joint positions are reported as the vector (circular) mean of the
two angles, and the year gap is an absolute value.  Swapping dob_a with dob_b changes nothing.

MISSINGNESS.  Z supplies NaN for a body it could not resolve, and this module propagates that
honestly — np.minimum / np.mod / arithmetic all carry NaN through, and every masked write is guarded
by np.isfinite so a NaN never reaches an integer cast or a table index.  A row with '0000-MM-DD'
(the day is recorded but the YEAR is not) has no chart at all and is NaN throughout, which is the
correct answer rather than a zero.  Nothing is imputed.  The one column that reports a coarser
MEASUREMENT rather than a NaN is `gap_years` at year precision, and it is shipped with
`gap_precision` beside it so the two populations can always be separated.

df.start is ALWAYS the string '0000-00-00' in this dataset.  It is never read.

Pure function of (df, Z): no I/O, no randomness, no global state, no imports beyond numpy/pandas.
"""

import itertools

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Bodies.
#
# 'ascendant' and 'medium_coeli' are excluded: with no birth time they are always NaN.
# 'sun', 'moon', 'mercury', 'venus', 'mars' are excluded on purpose — this is the SLOW module, and
# admitting a day-precision body would make every column here inherit that body's NaN density,
# destroying the one property that makes the block worth having (near-total coverage).
# 'true_south_node' is excluded because it is exactly true_node + 180 by definition: its sign is the
# opposite sign, its cross-chart arc is identical, so every column it could add is a duplicate.
# ---------------------------------------------------------------------------
OUTERS = ['jupiter', 'saturn', 'uranus', 'neptune', 'pluto']      # the five slow PLANETS
POINTS = ['true_node', 'chiron', 'mean_lilith']                   # slow computed POINTS
SLOW = OUTERS + POINTS                                            # 8 bodies, all year-resolvable

# Bodies whose SIGN is read as a generational marker in its own right.  Jupiter and Saturn are left
# out of the sign block deliberately: they change sign every 1 and 2.5 years respectively, so at
# year precision their sign is close to arbitrary and, more importantly, it is already carried by
# the Jupiter-Saturn / Saturn-X cycle phases below.  Uranus (7y/sign), Neptune (14y/sign) and Pluto
# (12-30y/sign) are the classic "generation" markers; the node (1.5y/sign) and Chiron are read for
# their sign by tradition, so they are kept.
SIGN_BODIES = ['uranus', 'neptune', 'pluto', 'true_node', 'chiron']

# Bodies compared for triplicity/quadruplicity agreement.  Restricted to the five true planets:
# element/modality is a claim about temperament, and doctrine makes it about planets, not points.
ELEM_BODIES = OUTERS

# Bodies whose sign SEPARATION (in signs, cyclically) is reported.
SEP_SIGN_BODIES = OUTERS + ['true_node', 'chiron']

# Bodies entering the cross-chart arc grid.  All eight slow bodies for the same-body arcs; the
# cross-body grid drops Lilith (a computed point with no mundane-cycle doctrine attached).
ARC_BODIES = SLOW
CROSS_BODIES = OUTERS + ['true_node', 'chiron']

# ---------------------------------------------------------------------------
# The seven classical mundane cycles: (short tag, faster body, slower body, synodic period in
# years, what the tradition reads in it).  Phase is measured FAST minus SLOW so that 0 deg is the
# conjunction that opens the cycle and the phase advances monotonically to 360.
#
# The synodic periods are documentation of the doctrine's own timescales — they are why a phase
# difference means something different in each cycle.  They are not multiplied into any column: a
# rescale of a separation by a constant is a monotone transform and would add no information to a
# tree, only a duplicate column.
# ---------------------------------------------------------------------------
CYCLES = [
    ('jusa', 'jupiter', 'saturn',   19.865, 'the great conjunction — the cycle of social/political order'),
    ('saur', 'saturn',  'uranus',   45.363, 'structure against revolt — the reform cycle'),
    ('sane', 'saturn',  'neptune',  35.870, 'structure against dissolution — the ideology cycle'),
    ('sapl', 'saturn',  'pluto',    33.438, 'structure against power — the crisis cycle'),
    ('urne', 'uranus',  'neptune', 171.404, 'the long social-vision cycle'),
    ('urpl', 'uranus',  'pluto',   127.007, 'the upheaval cycle (its 1960s conjunction, its 2010s square)'),
    ('nepl', 'neptune', 'pluto',   492.329, 'the slowest cycle read in mundane work — the epoch itself'),
]

# The three cycles built only from the outermost planets.  These are the ones that genuinely cannot
# separate two people of the same generation, and so are the purest "cohort" statement of the seven.
SLOW3 = ('urne', 'urpl', 'nepl')

# ---------------------------------------------------------------------------
# Return periods, in years — the sidereal periods the doctrine counts returns by.
# ---------------------------------------------------------------------------
RETURNS = [
    ('jupiter', 11.8618, 'the Jupiter return — the ~12y cycle of expansion'),
    ('node',    18.6129, 'the nodal return — the karmic cycle; the node regresses one full turn'),
    ('saturn',  29.4571, 'the Saturn return — the doctrine\'s hardest threshold of maturity'),
    ('chiron',  50.4200, 'the Chiron return — the wound come round'),
    ('uranus',  84.0205, 'the Uranus return; its half is the midlife opposition'),
]

_DIM = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


# --------------------------------------------------------------------------- date helpers

def _leap(y):
    return (y % 4 == 0) and (y % 100 != 0 or y % 400 == 0)


def _dim(y, m):
    if m == 2 and _leap(y):
        return 29
    return _DIM[m - 1]


def _jdn(y, m, d):
    """Proleptic Gregorian Julian Day Number.  Proleptic throughout: what is needed is one
    consistent day count across a set that reaches back centuries, not a calendar-reform ruling."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _parse(s):
    """'YYYY-MM-DD' -> (y, m, d), each None where that component was never recorded.

    Handles all four shapes this dataset contains:
      'YYYY-MM-DD' -> (y, m, d)      a full date
      'YYYY-00-00' -> (y, None, None) a year only — the slow bodies still resolve
      '0000-MM-DD' -> (None, m, d)    the YEAR is unknown, so NO chart exists at all
      '0000-00-00' -> (None, None, None) absent
    An out-of-range or impossible component (month 13, 31 February) is treated as not recorded
    rather than clamped, because clamping would invent a date nobody wrote down.
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


def _gap_years(df, n):
    """Absolute separation between the two births, in years, plus its precision.

    Returns (gap, prec) as float arrays of length n:
      prec == 2  both dates are full 'YYYY-MM-DD'  -> gap is the exact day difference / 365.25
      prec == 1  both YEARS are known but at least one lacks day precision -> gap is the year
                 difference, a real measurement at YEAR resolution (+/- 1y), not an invention
      prec is NaN and gap is NaN when either birth year is unrecorded — there is nothing to measure

    The value is ABSOLUTE so that swapping the two partners cannot change it.  The precision column
    ships alongside precisely so that the coarse and exact populations stay separable downstream;
    a single column whose resolution silently varies would be the dishonest version of this.
    """
    sa = df['dob_a'].astype(str).tolist() if 'dob_a' in getattr(df, 'columns', []) else [''] * n
    sb = df['dob_b'].astype(str).tolist() if 'dob_b' in getattr(df, 'columns', []) else [''] * n
    gap = np.full(n, np.nan, dtype=np.float64)
    prec = np.full(n, np.nan, dtype=np.float64)
    for i in range(min(n, len(sa), len(sb))):
        ya, ma, da = _parse(sa[i])
        yb, mb, db = _parse(sb[i])
        if ya is None or yb is None:
            continue                                # no year on one side: no measurable separation
        if ma is not None and da is not None and mb is not None and db is not None:
            gap[i] = abs(_jdn(ya, ma, da) - _jdn(yb, mb, db)) / 365.25
            prec[i] = 2.0
        else:
            gap[i] = abs(ya - yb)
            prec[i] = 1.0
    return gap, prec


# --------------------------------------------------------------------------- Z helpers

def _body_names(Z):
    try:
        raw = list(np.asarray(Z['bodies']).ravel())
    except Exception:
        return []
    out = []
    for b in raw:
        if isinstance(b, bytes):
            b = b.decode('utf-8', 'ignore')
        out.append(str(b).strip().lower())
    return out


def _matrix(Z, key):
    try:
        T = np.asarray(Z[key], dtype=np.float64)
    except Exception:
        return None
    return T if T.ndim == 2 else None


def _body_col(T, j, n):
    """One body's longitudes as a length-n float column, NaN wherever it is unavailable.
    Missing body, missing matrix and short matrix all degrade to NaN rather than to an exception,
    so the module returns the SAME width for both halves whatever Z happens to contain."""
    out = np.full(n, np.nan, dtype=np.float64)
    if T is None or j is None or j < 0 or j >= T.shape[1]:
        return out
    m = min(n, T.shape[0])
    if m:
        out[:m] = T[:m, j]
    out[~np.isfinite(out)] = np.nan
    return out


# --------------------------------------------------------------------------- circular helpers

def _sep180(a, b):
    """Circular separation of two ecliptic longitudes, 0..180 degrees.
    Symmetric in (a, b) by construction, so every column built on it is order-free.
    NaN in either argument propagates."""
    d = np.mod(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64), 360.0)
    return np.minimum(d, 360.0 - d)


def _mid_sincos(a, b):
    """sin and cos of the VECTOR (circular) mean of two angles given in degrees.

    The circular mean of two angles is the bisector of their SHORTER arc, obtained as the direction
    of the sum of the two unit vectors.  It is symmetric in (a, b), which is why it is used here in
    place of "partner A's phase" — it says where the PAIR sits in the cycle without naming an order.
    Exactly antipodal angles have a zero resultant and therefore no defined mean; that case returns
    NaN rather than an arbitrary bisector.
    """
    ar = np.radians(np.asarray(a, dtype=np.float64))
    br = np.radians(np.asarray(b, dtype=np.float64))
    s = np.sin(ar) + np.sin(br)
    c = np.cos(ar) + np.cos(br)
    r = np.hypot(s, c)
    bad = ~np.isfinite(r) | (r < 1e-9)
    ang = np.arctan2(s, c)
    return (np.where(bad, np.nan, np.sin(ang)), np.where(bad, np.nan, np.cos(ang)))


def _sign(lon):
    """Zodiac sign index 0..11 (0 = Aries), NaN where the longitude is unknown.
    Guarded by an isfinite mask so a NaN can never reach the floor/cast."""
    lon = np.asarray(lon, dtype=np.float64)
    out = np.full(lon.shape, np.nan, dtype=np.float64)
    ok = np.isfinite(lon)
    if ok.any():
        out[ok] = np.floor(np.mod(lon[ok], 360.0) / 30.0)
    return out


def _same_mod(sa, sb, k):
    """1.0 when the two sign indices agree modulo k, else 0.0; NaN where either is unknown.
    k = 4 is the TRIPLICITY (element: fire/earth/air/water, since sign % 4 cycles the elements);
    k = 3 is the QUADRUPLICITY (modality: cardinal/fixed/mutable, since sign % 3 cycles them)."""
    sa = np.asarray(sa, dtype=np.float64)
    sb = np.asarray(sb, dtype=np.float64)
    out = np.full(sa.shape, np.nan, dtype=np.float64)
    ok = np.isfinite(sa) & np.isfinite(sb)
    if ok.any():
        out[ok] = (np.mod(sa[ok], k) == np.mod(sb[ok], k)).astype(np.float64)
    return out


def _sign_sep(sa, sb):
    """Cyclic distance between two sign indices, 0..6 signs.  Symmetric; NaN-propagating."""
    d = np.mod(np.abs(np.asarray(sa, dtype=np.float64) - np.asarray(sb, dtype=np.float64)), 12.0)
    return np.minimum(d, 12.0 - d)


# --------------------------------------------------------------------------- build

def build(df, Z, half):
    n = int(len(df))
    idx = {nm: i for i, nm in enumerate(_body_names(Z))}
    TA = _matrix(Z, 'theta_a_%s' % half)
    TB = _matrix(Z, 'theta_b_%s' % half)

    LA = {b: _body_col(TA, idx.get(b), n) for b in SLOW}
    LB = {b: _body_col(TB, idx.get(b), n) for b in SLOW}
    SA = {b: _sign(LA[b]) for b in SLOW}
    SB = {b: _sign(LB[b]) for b in SLOW}

    cols, names = [], []

    def add(name, arr):
        a = np.asarray(arr, dtype=np.float64).reshape(-1)
        if a.shape[0] != n:
            raise ValueError('feature %s has length %d, expected %d' % (name, a.shape[0], n))
        cols.append(np.where(np.isfinite(a), a, np.nan))
        names.append(name)

    # ================================================================= A. placement / generation
    # A1. The generational sign itself, order-free as (min, max) of the two partners' sign indices.
    # An unordered pair of signs is what the doctrine actually reads ("one in Virgo, one in Libra");
    # min/max is the canonical order-free encoding of an unordered pair of labels.
    for b in SIGN_BODIES:
        ss = np.stack([SA[b], SB[b]])
        add('sign_lo_%s' % b, np.min(ss, axis=0))     # NaN-propagating (np.min, not fmin)
        add('sign_hi_%s' % b, np.max(ss, axis=0))

    # A2. How many signs apart the two placements are (0 = same sign = same cohort for that body).
    # 0..6, cyclic — this is the coarse, robust version of the cross-chart arc in A/B below, and it
    # is the quantity that survives at year precision even for the faster of the slow bodies.
    for b in SEP_SIGN_BODIES:
        add('sign_sep_%s' % b, _sign_sep(SA[b], SB[b]))

    # A3. Triplicity and quadruplicity agreement — the wide form of "same generation": two people
    # can miss the same sign and still share its element (a fire-sign Pluto) or its modality.
    for b in ELEM_BODIES:
        add('elem_same_%s' % b, _same_mod(SA[b], SB[b], 4))   # fire/earth/air/water
        add('mode_same_%s' % b, _same_mod(SA[b], SB[b], 3))   # cardinal/fixed/mutable

    # ================================================================= B. cross-chart arcs, same body
    # The angular distance between partner A's body X and partner B's SAME body X.  For a slow body
    # this is the birth separation read MODULO that body's orbital period — Pluto's arc is a near
    # monotone read of the gap for gaps under ~120y, while the node's arc wraps every 18.6y.  Taken
    # together the eight arcs are a modular fingerprint of the separation, not a restatement of it.
    for b in ARC_BODIES:
        add('arc_same_%s' % b, _sep180(LA[b], LB[b]))

    # ================================================================= C. cross-chart arcs, cross body
    # Partner A's body X against partner B's body Y, for every unordered pair {X, Y}.  Swapping the
    # partners exchanges the two observable directions (A.X-B.Y) and (A.Y-B.X), so the MINIMUM over
    # those two is order-free.  np.minimum (not fmin) is used deliberately: if either direction is
    # unmeasurable the pair is NaN, rather than quietly reporting the single direction that happened
    # to resolve — a half-measured pair is not the same quantity as a fully measured one.
    for x, y in itertools.combinations(CROSS_BODIES, 2):
        d1 = _sep180(LA[x], LB[y])
        d2 = _sep180(LA[y], LB[x])
        add('arc_cross_%s_%s' % (x, y), np.minimum(d1, d2))

    # ================================================================= D. the mundane cycles
    # For each classical cycle: its phase at each birth (fast minus slow, 0 = conjunction), reported
    # as a fraction of the full cycle, plus the circular phase DIFFERENCE between the two births and
    # the sin/cos of where the PAIR jointly sits.
    #   *_frac_lo / *_frac_hi : the two birth phases as fractions 0..1, order-free as min/max.
    #   *_sep_deg             : |phase_a - phase_b| circularly, 0..180. THE phase difference asked
    #                           for by the doctrine — how far apart in this cycle the two births are.
    #   *_mid_sin / *_mid_cos : sin/cos of the circular mean phase. A cycle phase is an ANGLE, so a
    #                           raw fraction has a false discontinuity at the 0/1 wrap; sin/cos give
    #                           the model a continuous encoding of the same position.
    ph_a, ph_b, sep = {}, {}, {}
    for tag, fast, slow, _per, _doc in CYCLES:
        pa = np.mod(LA[fast] - LA[slow], 360.0)
        pb = np.mod(LB[fast] - LB[slow], 360.0)
        ph_a[tag], ph_b[tag] = pa, pb
        pp = np.stack([pa, pb]) / 360.0
        add('cyc_%s_frac_lo' % tag, np.min(pp, axis=0))
        add('cyc_%s_frac_hi' % tag, np.max(pp, axis=0))
        s = _sep180(pa, pb)
        sep[tag] = s
        add('cyc_%s_sep_deg' % tag, s)
        msin, mcos = _mid_sincos(pa, pb)
        add('cyc_%s_mid_sin' % tag, msin)
        add('cyc_%s_mid_cos' % tag, mcos)

    # ================================================================= E. returns between the births
    # A return count is the calendar separation divided by a body's period.  The INTEGER part says
    # how many complete cycles of that body separate the two lives; the FRACTIONAL part says whether
    # they sit at the same point of the cycle (near 0 or 1) or in opposition (near 0.5).  The
    # doctrine reads those as different things, so they are shipped as different columns — and the
    # fraction is emphatically not a monotone function of the gap, which is the whole point.
    gap, prec = _gap_years(df, n)
    add('gap_years', gap)          # |years between the two births|; see _gap_years for precision
    add('gap_precision', prec)     # 2 = both dates full, 1 = year resolution, NaN = not measurable
    # Only the FRACTIONAL part is emitted.  The raw count gap/period is a constant multiple of
    # gap_years, and the integer part floor(gap/period) is a step function of it — both are MONOTONE
    # transforms of a column already present, so they offer a model no split it could not already
    # make, while adding surface to overfit.  The fraction is the one piece of the return that is
    # genuinely new: it wraps, so it is not monotone in the gap, and it is what the doctrine
    # actually reads (same phase of the cycle vs opposite phase).
    for nm, per, _doc in RETURNS:
        add('ret_%s_frac' % nm, np.mod(gap / per, 1.0))   # position within the return cycle, 0..1

    # NOTE — the SKY-read version of these returns is already in block B and is not repeated here.
    # arc_same_saturn IS the Saturn return read from the actual positions (a full return is an arc
    # of 0), and arc_same_true_node is the nodal return; dividing either by 180 to call it a
    # "fraction" would emit the identical column under a second name.  The sky version is the more
    # faithful measurement of the two — it uses the body's true longitude rather than a mean rate,
    # and it sharpens to day precision when the dates allow — while the calendar version above is
    # the one that survives when a body is missing from Z.  Both are wanted; neither is wanted twice.

    # ================================================================= F. generational-cohort distance
    # The doctrine's own measure of "how far apart are these two generations": the phase difference
    # summed across ALL the mundane cycles.  This is NOT the age gap.  A 20-year gap returns
    # Jupiter-Saturn to the same phase (separation ~0) while displacing Saturn-Pluto by ~215 deg of
    # its cycle; a 250-year gap can leave Neptune-Pluto near-conjunct again.  The sum therefore
    # measures displacement in CYCLE space, where the axes wrap at different rates.
    S = np.stack([sep[t] for t, _f, _s, _p, _d in CYCLES])        # (7, n)
    ok = np.isfinite(S)
    k = ok.sum(axis=0).astype(np.float64)
    tot = np.where(ok, S, 0.0).sum(axis=0)
    # The MEAN, not the sum.  All seven cycles are built from the same five outer planets, so Z
    # resolves them together: k is 7 or 0, never in between.  That makes the sum exactly 7x the mean
    # (a monotone duplicate) and makes a count-of-resolved-cycles column a constant — both were
    # measured to be dead and are deliberately not emitted.  meta_n_charts below already carries the
    # coverage fact honestly.
    add('cohort_mean_sep_deg', np.where(k > 0, tot / np.maximum(k, 1.0), np.nan))
    add('cohort_max_sep_deg', np.where(k > 0, np.nanmax(np.where(ok, S, -np.inf), axis=0), np.nan))
    add('cohort_min_sep_deg', np.where(k > 0, np.nanmin(np.where(ok, S, np.inf), axis=0), np.nan))

    # Restricted to the three outermost cycles — the ones that genuinely cannot tell apart two
    # people of the same cohort.  This is the strictest reading of "same generation".
    S3 = np.stack([sep[t] for t in SLOW3])
    ok3 = np.isfinite(S3)
    k3 = ok3.sum(axis=0).astype(np.float64)
    add('cohort_slow3_mean_sep', np.where(k3 > 0,
                                          np.where(ok3, S3, 0.0).sum(axis=0) / np.maximum(k3, 1.0),
                                          np.nan))

    # COHERENCE.  Each cycle contributes a signed phase displacement; the circular resultant of
    # those seven displacements is 1 when every cycle agrees the two births are offset by the same
    # phase, and falls toward 0 when they scatter.  A coherent displacement is the signature of a
    # clean generational step; an incoherent one means the cycles have wrapped differently, which is
    # exactly the case the age gap alone cannot express.  |.| is taken of the signed displacement so
    # the measure is unchanged by swapping the partners.
    D = np.stack([np.abs(np.mod(ph_a[t] - ph_b[t] + 180.0, 360.0) - 180.0)
                  for t, _f, _s, _p, _d in CYCLES])
    dr = np.radians(D)
    okd = np.isfinite(dr)
    kd = okd.sum(axis=0).astype(np.float64)
    cs = np.where(okd, np.cos(dr), 0.0).sum(axis=0)
    sn = np.where(okd, np.sin(dr), 0.0).sum(axis=0)
    add('cohort_resultant', np.where(kd > 0, np.hypot(cs, sn) / np.maximum(kd, 1.0), np.nan))

    # The same idea in BODY space rather than cycle space: the mean and the max of the eight
    # same-body cross-chart arcs.  Where the cycle version asks "how far apart are the two worlds",
    # this asks "how far apart are the two skies".
    B = np.stack([_sep180(LA[b], LB[b]) for b in ARC_BODIES])
    okb = np.isfinite(B)
    kb = okb.sum(axis=0).astype(np.float64)
    add('cohort_body_mean_arc', np.where(kb > 0,
                                         np.where(okb, B, 0.0).sum(axis=0) / np.maximum(kb, 1.0),
                                         np.nan))
    add('cohort_body_max_arc', np.where(kb > 0, np.nanmax(np.where(okb, B, -np.inf), axis=0), np.nan))

    # How many of the two partners have a chart at all (a usable birth YEAR).  This is row metadata,
    # not doctrine: it is what explains the NaN density of everything above, and it is derived from
    # Z's own resolution of a slow body rather than re-parsing the dates.
    add('meta_n_charts', np.isfinite(LA['pluto']).astype(np.float64)
                         + np.isfinite(LB['pluto']).astype(np.float64))

    if len(set(names)) != len(names):
        raise ValueError('duplicate feature names in cyclical_time')
    X = (np.column_stack(cols).astype(np.float32) if cols
         else np.zeros((n, 0), dtype=np.float32))
    if X.shape != (n, len(names)):
        raise ValueError('cyclical_time shape %s != (%d, %d)' % (X.shape, n, len(names)))
    return X, names
