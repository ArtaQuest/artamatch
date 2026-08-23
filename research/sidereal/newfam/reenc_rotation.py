"""reenc_rotation — rotation-invariant and difference encodings of the synastry overlay.

WHY THIS MODULE EXISTS
----------------------
A gradient-boosted tree splits on axis-aligned thresholds of the raw columns it is given.  It can
therefore never represent

    (1) a DIFFERENCE of two columns          — "how far apart are the two Saturns?"
    (2) a ROTATION-invariant of a chart      — "where does Saturn sit once the Sun is put at 0?"
    (3) a CIRCULAR wrap                      — 359 deg and 1 deg are two degrees apart, not 358

and every one of those is what astrological doctrine is actually made of.  A doctrine about the ARC
between two bodies is invisible to a tree unless the arc is handed over already computed.  (This is
the same failure the project has already measured elsewhere: a boosted tree handed two birth years
scored 0.5311 while the plain DIFFERENCE of those years scored 0.6045.)  This module computes no new
astronomy — it re-encodes what Z already contains into the coordinates the doctrine is written in.

WHAT IS BUILT
-------------
  A. CROSS-PARTNER ARCS, same body.   d_i = theta_a[i] - theta_b[i], wrapped to [-180, 180).
     Handed over as the absolute arc, as a canonically SIGNED arc, and as a Fourier ladder
     cos(k*d), |sin(k*d)| over the HIGHER harmonics k = 2..12.  The ladder matters because each
     harmonic k is a smooth dial with k lobes: cos(k*d) peaks whenever d is a multiple of 360/k,
     so k=2 is the conjunction/opposition axis, k=3 the trine dial, k=4 the square dial, k=12 the
     30-degree (sign-boundary) dial.  A tree can split on each of these directly; it could never
     build one.  k=1 is deliberately absent: cos(1*d) = cos(|d|) with |d| in [0,180], where cos is
     strictly monotone, so it is the absolute arc re-expressed and a tree splits it identically.
     How far each body's ladder runs is set by that body's angular rate (see ARC_PLAN) — a harmonic
     that cannot wrap across a human age gap is a duplicate column, not a feature.
  B. THE ARC MODULO a dial (30/45/60/72/90/120/144/180).  The literal harmonic-dial reduction:
     the sawtooth |d| mod M, and the dial DISTANCE (distance to the nearest multiple of M), which
     is the orb an astrologer would actually read off an Mth-harmonic chart.
  C. CROSS-BODY doctrinal arcs (Venus of one against Uranus of the other, etc.), symmetrised.
  D. ROTATION FRAMES.  Each partner's chart is rotated so a chosen centre body C sits at 0:
         phi_p,i = (theta_p,i - theta_p,C) mod 360
     which is invariant to any whole-chart rotation, i.e. it is chart SHAPE rather than chart
     position.  Then the cross-partner distance in that SAME rotated frame,
         overlay_C,i = circular distance between phi_a,i and phi_b,i
     is exactly what a synastry overlay is: lay one wheel on the other, aligned on C, and read how
     far body i has slipped.  Algebraically overlay_C,i = |wrap(d_i - d_C)| — a difference of two
     differences, which is two levels beyond anything a tree can assemble.  Three centres are used:
     sun-centred, moon-centred, and node-centred.  The node-centred frame is the "ascendant-free"
     one asked for: with no birth time the ascendant and MC are always NaN, so the lunar nodes are
     the only chart AXIS available, and a node-centred frame is the closest honest substitute for
     an ascendant-centred one.

ORDER-FREENESS (this dataset puts every pair in both orders, so column order must not be learnable)
---------------------------------------------------------------------------------------------------
Swapping the two partners maps d_i -> -d_i.  Therefore:
  * |d|, cos(k*d), |sin(k*d)|, |d| mod M, dial distance, and every overlay distance are EVEN in d
    and so are invariant by construction — nothing to symmetrise.
  * the raw SIGNED arc is odd and would leak column order, so it is never emitted raw.  It is
    emitted only after canonicalisation: the sign is fixed by which partner was born FIRST, a rule
    that depends on the dates and not on which column they arrived in.  Swapping partners flips both
    d and the older/younger sign, leaving the product unchanged.  Where the birth order cannot be
    established (a year missing, or an exact tie with no day precision) the signed columns are NaN
    rather than guessed.
  * cross-BODY pairs (X != Y) have two observable contacts, (a.X, b.Y) and (a.Y, b.X); swapping the
    partners merely exchanges them, so any set statistic over the two (fmin / fmax) is order-free.
  * within-chart rotated positions phi_p,i are per-partner and so are reduced to fmax/fmin over the
    two partners before being emitted.

MISSING DATA
------------
Four date shapes occur: 'YYYY-MM-DD', 'YYYY-00-00' (year only), '0000-MM-DD' (year unknown) and
'0000-00-00' (absent).  All four are handled, and nothing is ever imputed:
  * no year at all  -> NOTHING in a chart can be placed (an ephemeris needs an epoch), so every body
    of that partner is forced to NaN even if Z happened to supply a number.
  * year but no month/day -> the day-precision bodies (sun, moon, mercury, venus, mars) are forced
    to NaN; the slow bodies, which resolve from a year alone, are kept.
  * NaN propagates through every arc, every harmonic and every aggregate.  Aggregates over a set of
    bodies divide by the number of VALID bodies and return NaN when that count is zero, so a row
    with nothing to read is NaN and never a 0 that would be misread as "perfectly aligned".
No integer is ever derived from a date and used to index a lookup table, so a NaN can never be cast
to an int and silently select the wrong row of anything.
df.start is ALWAYS the string '0000-00-00' in this dataset; it is never read.

PURITY: build() is a pure function of (df, Z, half) — no I/O, no network, no randomness, no globals
mutated, and the same number of columns is returned for 'train' and for 'test' because the column
plan below is a static constant.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Bodies.  'ascendant' and 'medium_coeli' are omitted: with no birth time they
# are always NaN, so they could only contribute empty columns.
# ---------------------------------------------------------------------------
BODIES = [
    'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus',
    'neptune', 'pluto', 'true_node', 'true_south_node', 'chiron', 'mean_lilith',
]
NB = len(BODIES)
BIDX = {b: i for i, b in enumerate(BODIES)}

# Bodies that need day precision to be placed at all (they move ~0.5-13 deg/day).
# A value for one of these from a year-only date would be a fabrication, so it is
# refused at the door.  The slow bodies below move slowly enough that a year alone
# pins them to within a few degrees, which is why Z supplies them for year-only rows.
FAST = ('sun', 'moon', 'mercury', 'venus', 'mars')

# true_south_node is a RIGID mirror of true_node (always node + 180 exactly), so its
# cross-partner arc equals the node's arc identically.  It is excluded from every
# aggregate to avoid double-counting one body as two.
MIRROR = 'true_south_node'

# ---------------------------------------------------------------------------
# THE COLUMN PLAN.  Static, hence identical width on both halves.
# ---------------------------------------------------------------------------

# THE HARMONIC LADDER, per body: (body, cos harmonics, |sin| harmonics).
#
# Every body listed gets the absolute arc.  The COS ladder deliberately starts at k=2, because
# cos(1*d) = cos(|d|) and |d| lives in [0, 180] where cos is strictly monotone — so cos1 is a
# monotone transform of the absolute arc and a tree would split it identically.  Emitting it would
# cost width and add nothing.  (Measured: rank-correlation of cos1 with |arc| is exactly 1.00 for
# all fourteen bodies.)  This also matches the doctrine as usually stated: the arc itself, then its
# 2nd through 12th harmonics.
#
# How far the ladder goes is set by GEOMETRY, not by any fit to the labels: harmonic k folds the
# arc into k lobes, so it only carries information beyond |arc| once k * (the largest arc this
# population actually shows) exceeds 180 degrees.  A body's arc grows at (360 / its period) degrees
# per year of age gap, so the slow outer planets simply never wrap across a human age gap and their
# low harmonics stay monotone in |arc|:
#   saturn   29.5 yr,  12.2 deg/yr  -> arc spans the full circle; every harmonic to k=12 is live
#   uranus   84.0 yr,   4.3 deg/yr  -> arc spans the full circle; decorrelates from k=3 upward
#   jupiter  11.9 yr,  30.3 deg/yr  -> wraps repeatedly; k=2,3 already independent of |arc|
#   node     18.6 yr,  19.3 deg/yr  -> wraps repeatedly; k=2,3 independent
#   chiron   50.7 yr,   7.1 deg/yr  -> k=2 partly independent
#   neptune 164.8 yr,   2.2 deg/yr  -> 99th pct of |arc| is 77 deg: k=2 and k=3 measured at
#   pluto   248.0 yr,   1.5 deg/yr  -> 99th pct of |arc| is 50 deg: rank-corr 0.99-1.00 with |arc|
#     ...so neptune and pluto are given the arc alone; a ladder on them would be duplicate columns.
# The day-precision bodies move degrees per DAY, so their arcs are effectively uniform on the
# circle and their low harmonics are live.
ARC_PLAN = [
    ('saturn',    [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
    ('uranus',    [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
    ('jupiter',   [2, 3]),
    ('true_node', [2, 3]),
    ('neptune',   []),
    ('pluto',     []),
    ('chiron',    [2]),
    ('sun',       [2, 3]),
    ('moon',      [2, 3]),
    ('venus',     [2, 3]),
    ('mars',      [2, 3]),
]

# The canonically signed arc is emitted only where the sign is BOTH readable and informative.
# For jupiter (11.9 yr) or the node (18.6 yr) the arc wraps several times over a typical age gap,
# so a sign there would describe the wrap rather than the birth order.  At the other extreme
# neptune (164.8 yr) and pluto (248 yr) turn so slowly that the older partner's planet is behind
# the younger's on essentially every row: measured, their signed arc is rank-identical to minus
# their own absolute arc (|rho| = 0.9999 / 0.9995), so it is a duplicate column and is not emitted.
# Saturn and uranus are the band where the direction genuinely varies.
SIGNED = ['saturn', 'uranus']

# Group B — the dials.
#
# THE DEGENERACY THAT GOVERNS THIS BLOCK.  Two of the three natural dial encodings collapse onto
# the cosine ladder above, and both collapses were measured on real data before being fixed:
#   * dial DISTANCE to the nearest multiple of M is a strictly monotone function of
#     cos((360/M) * d), so emitting both on the same body gives two rank-identical columns
#     (|rho| = 1.000 — arcdial90 vs cos4, arcdial60 vs cos6, arcdial30 vs cos12, ...).
#   * |sin(k*d)| is a strictly monotone function of cos(2k*d), because cos(2x) = 1 - 2 sin^2(x).
#     The whole rectified-sine ladder was therefore removed: for a quantity that must be EVEN in d
#     (which order-freeness requires), the cosine ladder is already a complete basis and the
#     rectified sine can only restate it.
#   * |d| mod M does NOT collapse.  It is a sawtooth: it keeps WHERE inside the fold the arc sits,
#     which the distance-to-edge throws away by folding the two halves together.  Verified
#     independent of every cosine on the same body.
# So: raw modulo goes on the bodies whose arc fills the circle, and dial distance is used ONLY as a
# cheap way to reach a HIGH harmonic on a body whose cosine ladder was deliberately kept short.
# The assertion below enforces exactly that and will fail the import if it is ever violated.
DIAL_RAW_SPEC = [
    ('saturn', [30, 45, 60, 72, 90, 120, 144]),   # 12.2 deg/yr — the arc fills the circle
    ('uranus', [30, 90]),                          # 4.3 deg/yr — fills it over the wider gaps
]
DIAL_DIST_SPEC = [
    ('jupiter',   [90, 60, 30]),    # reaches the 4th, 6th and 12th harmonic; its ladder stops at 3
    ('true_node', [90, 60, 30]),    # likewise
    ('chiron',    [120, 60]),       # reaches the 3rd and 6th; its ladder stops at 2
    ('sun',       [90]),            # reaches the 4th (the square dial) on the day-precision bodies
    ('moon',      [90]),
    ('venus',     [90]),
    ('mars',      [90]),
]

# Static self-check: a dial DISTANCE at M is rank-identical to cos((360/M) * d), so it must never
# be emitted on a body whose cosine ladder already contains that harmonic.  This runs at import and
# is the reason the collapse above cannot come back through a later edit of the plan.
_COS_OF = dict(ARC_PLAN)
for _b, _Ms in DIAL_DIST_SPEC:
    for _M in _Ms:
        _k = 360.0 / _M
        if _k == int(_k) and int(_k) in _COS_OF.get(_b, []):
            raise AssertionError(
                'dial distance %d on %s duplicates rr_arc_cos%d_%s' % (_M, _b, int(_k), _b))
for _b, _Ms in DIAL_RAW_SPEC:
    if _b not in _COS_OF:
        raise AssertionError('raw dial on %s, which has no arc plan' % _b)
del _COS_OF


# Group C — cross-body doctrinal contacts, each symmetrised over its two orderings.
#   venus x uranus — love met by disruption: the classical signature of a bond broken by choice
#   moon  x uranus — emotional life met by upheaval
#   venus x saturn — love met by duty/coldness; the classic endure-or-leave pair
#   moon  x saturn — the pair doctrine most often blames for coldness inside a marriage
#   sun   x moon   — the marriage contact proper, the two luminaries
#   venus x mars   — attraction and desire
#   mars  x saturn — friction against restraint; the anger/frustration pair
#   sun   x saturn — vitality met by duty; endurance at the cost of the self
CROSS_PAIRS = [
    ('venus', 'uranus'), ('moon', 'uranus'), ('venus', 'saturn'), ('moon', 'saturn'),
    ('sun', 'moon'), ('venus', 'mars'), ('mars', 'saturn'), ('sun', 'saturn'),
]

# Group D — the rotation frames.
CENTRES = ['sun', 'moon', 'true_node']
OVERLAY_BODIES = ['saturn', 'uranus', 'neptune', 'pluto', 'jupiter', 'chiron']
# The within-chart rotated position, reduced across the two partners (fmax and fmin).
ROT_FRAME = [('sun', 'saturn'), ('sun', 'uranus'), ('true_node', 'saturn'), ('true_node', 'uranus')]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _wrap180(x):
    """Signed angle wrapped to [-180, 180).  NaN in -> NaN out (np.mod preserves NaN)."""
    return np.mod(x + 180.0, 360.0) - 180.0


def _wrap360(x):
    """Angle wrapped to [0, 360)."""
    return np.mod(x, 360.0)


def _parse_dates(col, n):
    """Vectorised parse of a date column into (year, month, day, has_year, has_md).

    Handles all four shapes without ever inventing a component:
      'YYYY-MM-DD' -> year + month/day        'YYYY-00-00' -> year only
      '0000-MM-DD' -> month/day, NO year      '0000-00-00' -> nothing
    Anything unparseable (None, NaN, a wrong-length string) is treated as 'nothing'.
    The returned year/month/day are floats carrying NaN where unknown; they are used only for
    COMPARISON, never as an index into any table, so a NaN can never become a wrong lookup."""
    s = pd.Series(col).astype(str).str.strip()
    y = pd.to_numeric(s.str.slice(0, 4), errors='coerce').to_numpy(dtype=np.float64)
    m = pd.to_numeric(s.str.slice(5, 7), errors='coerce').to_numpy(dtype=np.float64)
    d = pd.to_numeric(s.str.slice(8, 10), errors='coerce').to_numpy(dtype=np.float64)
    if y.shape[0] != n:
        raise ValueError('date column length %d != %d' % (y.shape[0], n))
    has_year = np.isfinite(y) & (y > 0)
    has_md = np.isfinite(m) & np.isfinite(d) & (m > 0) & (d > 0)
    y = np.where(has_year, y, np.nan)
    m = np.where(has_md, m, np.nan)
    d = np.where(has_md, d, np.nan)
    return y, m, d, has_year, has_md


def _theta(Z, slot, half, n, has_year, has_md):
    """(n, 14) sidereal longitudes for one partner, columns in BODIES order.

    Bodies are resolved by NAME from Z['bodies'], so a reordered npz cannot silently shuffle them,
    and a body absent from the npz yields an all-NaN column rather than a narrower matrix.

    Two honesty guards are then applied.  They are no-ops against a well-formed Z (verified: this
    dataset's Z already NaNs every day-precision body on a year-only row) and they exist so that a
    Z which quietly defaulted an unknown date to some epoch cannot leak a fabricated longitude:
      * no year  -> the whole chart is NaN (nothing can be placed without an epoch)
      * no month/day -> the FAST bodies are NaN (they move too fast to be pinned by a year)"""
    key = 'theta_%s_%s' % (slot, half)
    T = np.asarray(Z[key], dtype=np.float64)
    if T.ndim != 2 or T.shape[0] != n:
        raise ValueError('%s has shape %r, expected (%d, k)' % (key, T.shape, n))
    zb = [str(x) for x in np.asarray(Z['bodies']).ravel().tolist()]
    where = {nm: i for i, nm in enumerate(zb)}
    out = np.full((n, NB), np.nan, dtype=np.float64)
    for k, b in enumerate(BODIES):
        j = where.get(b)
        if j is not None and j < T.shape[1]:
            out[:, k] = T[:, j]
    out[~has_year, :] = np.nan
    for b in FAST:
        out[~has_md, BIDX[b]] = np.nan
    return out


def _older_sign(ya, ma, da, hya, hmda, yb, mb, db, hyb, hmdb):
    """+1 if partner A was born first, -1 if partner B was, NaN if it cannot be established.

    This is the ONLY thing that fixes the sign of a signed arc, and it is a fact about the dates
    rather than about which column they arrived in — which is exactly what makes the signed arc
    order-free.  Ordering is established when both years are known and differ; when the years are
    equal it needs day precision on BOTH sides and a genuine difference.  A tie, or any missing
    piece, returns NaN (the signed columns then go NaN) rather than defaulting to a direction."""
    n = ya.shape[0]
    s = np.full(n, np.nan, dtype=np.float64)
    both_y = hya & hyb
    s = np.where(both_y & (ya < yb), 1.0, s)
    s = np.where(both_y & (ya > yb), -1.0, s)
    same_y = both_y & (ya == yb) & hmda & hmdb
    key_a = ma * 100.0 + da
    key_b = mb * 100.0 + db
    s = np.where(same_y & (key_a < key_b), 1.0, s)
    s = np.where(same_y & (key_a > key_b), -1.0, s)
    return s


def _nan_mean(M):
    """Row-wise mean over the finite entries; NaN when a row has none.

    Written by hand rather than with np.nanmean so that an all-NaN row returns NaN silently
    instead of emitting a RuntimeWarning, and so the divisor is provably the valid count."""
    ok = np.isfinite(M)
    cnt = ok.sum(axis=1)
    tot = np.where(ok, M, 0.0).sum(axis=1)
    return np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)


def _nan_min(M):
    """Row-wise minimum over the finite entries; NaN when a row has none."""
    ok = np.isfinite(M)
    cnt = ok.sum(axis=1)
    mn = np.where(ok, M, np.inf).min(axis=1)
    return np.where(cnt > 0, mn, np.nan)


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build(df, Z, half):
    n = len(df)
    cols = []
    names = []

    def add(name, v):
        """Append one column, checking the length so a broadcasting slip cannot pass silently."""
        a = np.asarray(v, dtype=np.float64).reshape(-1)
        if a.shape[0] != n:
            raise ValueError('feature %s has length %d, expected %d' % (name, a.shape[0], n))
        cols.append(a)
        names.append(name)

    for c in ('dob_a', 'dob_b'):
        if c not in df.columns:
            raise ValueError('df is missing required column %r' % c)

    ya, ma, da, hya, hmda = _parse_dates(df['dob_a'].to_numpy(), n)
    yb, mb, db, hyb, hmdb = _parse_dates(df['dob_b'].to_numpy(), n)
    # df.start is always '0000-00-00' here and is deliberately never read.

    A = _theta(Z, 'a', half, n, hya, hmda)
    B = _theta(Z, 'b', half, n, hyb, hmdb)

    sign = _older_sign(ya, ma, da, hya, hmda, yb, mb, db, hyb, hmdb)

    # D[:, i] — the signed cross-partner arc for body i, wrapped to [-180, 180).
    # This single matrix is the substrate of the whole module: every feature below is a function
    # of it (or of the within-chart rotations that reduce to it).
    D = _wrap180(A - B)
    ADEG = np.abs(D)                       # order-free magnitude, in [0, 180]
    DRAD = np.deg2rad(D)                   # radians once, reused by every harmonic

    def d_of(b):
        return D[:, BIDX[b]]

    def rad_of(b):
        return DRAD[:, BIDX[b]]

    # -----------------------------------------------------------------------
    # GROUP A — same-body cross-partner arcs and their Fourier ladder.
    # Doctrine: "his Saturn against her Saturn" is an ARC, not two positions.  The tree is handed
    # the arc itself, then a bank of dials over it.  cos(k*d) is even in d and therefore already
    # order-free; |sin(k*d)| supplies the quadrature component (it peaks exactly where cos is flat)
    # while staying even, so nothing here can encode which partner is in which column.
    # -----------------------------------------------------------------------
    for (body, cos_ks) in ARC_PLAN:
        add('rr_arc_abs_%s' % body, ADEG[:, BIDX[body]])
        # ^ absolute cross-partner arc between the two <body> positions, degrees in [0,180]:
        #   the plain DIFFERENCE a tree cannot form for itself.  For the slow outer planets this
        #   doubles as a smooth, unwrapped reading of how far apart in time the two were born.
        for k in cos_ks:
            add('rr_arc_cos%d_%s' % (k, body), np.cos(k * rad_of(body)))
            # ^ kth harmonic dial of the arc: peaks at every multiple of 360/k degrees
            #   (k=2 conj/opp axis, k=3 trine, k=4 square, k=6 sextile, k=12 sign boundary).
            #   Even in d, so already order-free.
    for body in SIGNED:
        add('rr_arc_signed_oldfirst_%s' % body, sign * d_of(body))
        # ^ the arc with its sign fixed by WHO WAS BORN FIRST (older minus younger).  Order-free:
        #   swapping the partners negates both factors.  NaN wherever birth order cannot be
        #   established.  Direction is real information here: the older partner's slow body sits
        #   BEHIND the younger's on the zodiac, a distinction |d| throws away.

    # -----------------------------------------------------------------------
    # GROUP B — the arc taken modulo a dial.
    # An Mth-harmonic chart is literally the zodiac folded at M degrees.  Two readings of that are
    # emitted because they answer different questions and a tree can use both:
    #   raw modulo   |d| mod M  — the sawtooth POSITION within the fold (where in the dial it sits)
    #   dial distance           — the ORB to the nearest exact multiple of M (how tight it is)
    # Both are even in d, hence order-free.
    # -----------------------------------------------------------------------
    for (body, Ms) in DIAL_RAW_SPEC:
        for Mv in Ms:
            add('rr_arcmod%d_%s' % (Mv, body), np.mod(ADEG[:, BIDX[body]], float(Mv)))
            # ^ POSITION of the <body>-<body> arc inside the M-degree fold, [0, M).  A sawtooth:
            #   unlike the dial distance it keeps which side of the fold the arc fell on.
    for (body, Ms) in DIAL_DIST_SPEC:
        for Mv in Ms:
            r = np.mod(ADEG[:, BIDX[body]], float(Mv))
            add('rr_arcdial%d_%s' % (Mv, body), np.minimum(r, float(Mv) - r))
            # ^ ORB of the <body>-<body> arc to the nearest exact multiple of M, [0, M/2] — what an
            #   astrologer reads off the Mth-harmonic chart.  Only ever on a body whose cosine
            #   ladder does not already reach harmonic 360/M (see the assertion above).

    # -----------------------------------------------------------------------
    # GROUP C — cross-BODY doctrinal contacts (X of one partner against Y of the other).
    # For X != Y there are two observable contacts, (a.X, b.Y) and (a.Y, b.X).  Swapping the
    # partners merely exchanges the two, so the tighter one (fmin) and the strongest 2nd-harmonic
    # response (fmax of cos 2d, which treats conjunction and opposition alike — doctrine's
    # "on the same axis") are order-free set statistics.  np.fmin/np.fmax are used deliberately:
    # they carry a value through when only ONE of the two contacts is computable, and return NaN
    # only when both are unknown.
    # -----------------------------------------------------------------------
    for (x, yb_) in CROSS_PAIRS:
        d1 = _wrap180(A[:, BIDX[x]] - B[:, BIDX[yb_]])
        d2 = _wrap180(A[:, BIDX[yb_]] - B[:, BIDX[x]])
        add('rr_x_absmin_%s_%s' % (x, yb_), np.fmin(np.abs(d1), np.abs(d2)))
        # ^ the TIGHTER of the two cross contacts, degrees in [0,180]
        add('rr_x_cos2max_%s_%s' % (x, yb_),
            np.fmax(np.cos(2 * np.deg2rad(d1)), np.cos(2 * np.deg2rad(d2))))
        # ^ strongest conjunction-or-opposition response across the two contacts

    # -----------------------------------------------------------------------
    # GROUP D — the rotation frames (the synastry overlay proper).
    #
    # Rotating partner p's chart so centre body C sits at 0 gives phi_p,i = (theta_p,i - theta_p,C)
    # mod 360.  That is chart SHAPE: it is unchanged if the whole chart is rotated, so it discards
    # the absolute zodiac position (which for these bodies is mostly a restatement of the birth
    # epoch) and keeps only the internal geometry.
    #
    # Laying partner B's rotated wheel on partner A's — aligned on C, which is what an astrologer
    # physically does with an overlay — and reading how far body i has slipped gives
    #     overlay_C,i = circular distance(phi_a,i, phi_b,i) = |wrap(d_i - d_C)|
    # a DIFFERENCE OF DIFFERENCES.  It is even in (d_i - d_C) and so order-free.
    #
    # Three centres.  sun-centred and moon-centred are the two luminary frames.  The third is the
    # "ascendant-free" frame the brief asks for: with no birth time the ascendant and MC are always
    # NaN, so the lunar node is the only chart AXIS that can be computed at all, and a node-centred
    # frame is the honest stand-in for an ascendant-centred one.
    # -----------------------------------------------------------------------
    for c in CENTRES:
        dc = d_of(c)
        for b in OVERLAY_BODIES:
            add('rr_ovl_%scentred_%s' % (c, b), np.abs(_wrap180(d_of(b) - dc)))
            # ^ how far <b> slips between the two charts once both are aligned on <c>, [0,180]
        # Whole-chart aggregates in the same frame.  The body set excludes the centre itself
        # (overlay 0 by construction) and the south node (a rigid 180 mirror of the north node,
        # so it would double-count one body as two).
        agg = [x for x in BODIES if x != c and x != MIRROR]
        M = np.abs(_wrap180(D[:, [BIDX[x] for x in agg]] - dc[:, None]))
        add('rr_ovl_%scentred_mean' % c, _nan_mean(M))
        # ^ mean slip across the whole chart in this frame: how well the two wheels agree overall
        add('rr_ovl_%scentred_min' % c, _nan_min(M))
        # ^ the single tightest body once aligned on <c> — the strongest overlay contact

    # Within-chart rotated POSITIONS, reduced across partners so no column order is encoded.
    # cos(phi) is 1 when body b sits exactly on the centre body in that partner's own chart and -1
    # when it is opposite; the fmax is "the more tightly one of the two holds b to c", the fmin is
    # "even the looser of the two".  fmax/fmin (not maximum/minimum) so one known partner still
    # yields a value.
    for (c, bd) in ROT_FRAME:
        pa = np.cos(np.deg2rad(_wrap360(A[:, BIDX[bd]] - A[:, BIDX[c]])))
        pb = np.cos(np.deg2rad(_wrap360(B[:, BIDX[bd]] - B[:, BIDX[c]])))
        add('rr_rot_%s0_%s_cosmax' % (c, bd), np.fmax(pa, pb))
        # ^ the more tightly ONE of the two partners holds <bd> to <c> in their own chart
        add('rr_rot_%s0_%s_cosmin' % (c, bd), np.fmin(pa, pb))
        # ^ the same for the looser of the two; the pair (max, min) is the order-free reduction
        #   of the two per-partner rotated positions

    # -----------------------------------------------------------------------
    # Coverage.  Without these the model cannot tell "no contact" from "not recorded", and every
    # NaN above would be an ambiguity.  These count RECORDED facts; they impute nothing.
    # -----------------------------------------------------------------------
    both = np.isfinite(A) & np.isfinite(B)
    add('rr_n_valid_bodies', both.sum(axis=1).astype(np.float64))
    # ^ how many of the 14 bodies are placeable for BOTH partners (0..14).  This is what separates
    #   "the doctrine says no contact here" from "nobody wrote the date down", and without it every
    #   NaN above would be that ambiguity.  It counts a RECORDED fact and imputes nothing.
    #   A companion count over the day-precision bodies alone was dropped: a chart is all-14, or 9
    #   (year only), or 0, so the fast count is a step function of this one and measured at
    #   rho = 1.000 against it.

    X = np.column_stack(cols).astype(np.float32) if cols else np.zeros((n, 0), np.float32)
    if len(names) != len(set(names)):
        raise ValueError('duplicate feature name emitted')
    return X, names
