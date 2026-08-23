"""phasor_pair — the COMPONENTS OF A PHASOR MODEL, not a tree's feature table.

WHAT THIS MODULE IS
-------------------
ArtaModel (research/sidereal/artamodel.py, ARTAMODEL.md) is not a tree and not a linear model on
angles; it is a complex-amplitude model

    y = | b + SUM_i  a_i e^{i|theta1_i - theta2_i|}     the synastry term  ("a"  of TERMS_IV)
                   + n_i e^{i theta_i}                  each natal phase   ("n1"/"n2" of TERMS_IV)
        |^2

fitted over sidereal (Lahiri) longitudes.  Its whole power is that a COMPLEX weight applied to a
phasor e^{i*phi} is a free choice of PHASE as well as magnitude: the model can place its response
peak at ANY arc, and can add two arcs coherently or destructively.  That is what "represents an ARC
natively" means, and it is exactly what a boosted tree cannot do — a tree only compares a column
against thresholds, so it can neither rotate a phase nor sum two phases coherently.  (The project
has already paid for that: a GBM handed two birth years scored 0.5311 while the plain DIFFERENCE of
the years scored 0.6045 — feedback_tree_baseline_cannot_represent_a_difference.)

A phasor model is, however, LINEAR in the pair (cos phi, sin phi):

    Re( conj(w) e^{i*phi} )  =  Re(w) cos(phi) + Im(w) sin(phi)

So handing a downstream linear / ridge / logistic / phasor stage the (cos, sin) PAIR of every phase
the doctrine names lets that stage recover the complex amplitude a_i exactly, by ordinary linear
fitting — and lets a |.|^2 head reconstruct the intensity.  This module therefore emits phasor
COMPONENTS ONLY.  It computes no aggregates, no counts, no orbs, no dials: every column here is a
cos or a sin of an angle, in [-1, 1], so the block is a clean complex basis that a downstream stage
can weight coherently.

CONVENTIONS TAKEN FROM artamodel.py (matched deliberately)
----------------------------------------------------------
  * absdiff — every inter-partner phase enters as the WRAPPED ABSOLUTE difference |theta_a-theta_b|
    in [0, 180] degrees (artamodel.absdiff, `even=True`, the fourth "genderless" edition).
  * even functions — operator 2026-08-19: "(a, b, 1) should also mean (b, a, 1) ... for each
    subtractive term add abs to ensure each term is an even function".  This dataset carries pairs
    in both orders, so a column that changed under a swap would let the model learn column order
    instead of the doctrine.  Every column below is EXACTLY invariant to swapping the partners —
    bitwise, by construction, not approximately (see ORDER-FREENESS).
  * TERMS_IV — the term set of the genderless edition is ("a", "t1", "t2", "n1", "n2", "tn"): the
    synastry arc, the wedding sky against each partner, each natal phase, the wedding sky's own
    phase.  In THIS dataset there is no wedding: df.start is the string '0000-00-00' on every row
    and carries no information, so t1, t2 and tn cannot exist and are not faked.  What survives of
    TERMS_IV is exactly "a" (Block A below) and "n1"/"n2" (Block B).
  * the presence rule — "a term exists only when both of its phases exist"; a missing phase is NaN
    and contributes exactly nothing (ArtaModel does nan_to_num on cos/sin, so a NaN phasor is the
    zero vector).  NaN here is therefore not a defect: it is the model's own presence rule, and it
    is never replaced by a number that would read as "0 degrees apart" or "at 0 degrees".
  * harmonics — ARTAMODEL.md section 5 fits phases scaled by h ("h=2 0.6284, h=3 0.6203, h=4
    0.6069"); harmonic h of a phasor is the h-lobed dial (h=2 the conjunction/opposition axis,
    h=3 the trine dial, h=4 the square dial), and for a SLOW body a harmonic is also a finer era
    clock.  The ladder runs h = 1..4, pruned per body by measured redundancy (see THE PLAN).

THE TWO BLOCKS
--------------
A. ARC PHASORS (the synastry term "a"), per body:
       cos(h * |theta_a - theta_b|),  sin(h * |theta_a - theta_b|)
   The arc is the age gap read on that body's clock (Uranus turns 4.3 deg/yr, so |arc_uranus| IS
   the gap in years for any gap under 84; Saturn 12.2 deg/yr; the fast bodies wrap within days, so
   their arc is the classical synastry aspect between the two charts).  cos is even in the signed
   difference already; sin is taken of the ABSOLUTE arc so that it too is even.  The pair spans the
   phase plane, so a downstream complex weight can peak at any arc — a conjunction doctrine, an
   opposition doctrine or a 137-degree doctrine are all the same fit here.

B. NATAL PHASORS, TIED (the terms "n1" and "n2" carried by ONE shared weight), per body:
       ( cos(h*theta_a) + cos(h*theta_b) ) / 2,   ( sin(h*theta_a) + sin(h*theta_b) ) / 2
   The brief asks for "cos and sin of each partner's raw longitude".  Emitting them per partner
   would break order-freeness: cos(theta_a) as its own column tells the model which column a row
   arrived in.  The MEAN of the two partners' phasors is the order-free form, and it is not a
   compromise — it is precisely what the genderless model computes when n1 and n2 share one complex
   weight, because Re(conj(w)(z_a+z_b)) = Re(conj(w)z_a) + Re(conj(w)z_b).  A tied natal term IS
   the doctrine "this natal placement matters, in whoever's chart it falls".  Dividing by 2 only
   puts the column on the same [-1, 1] scale as Block A so one ridge penalty is fair to both.
   What this natal block means physically: a slow body's longitude at birth is a CLOCK ON THE BIRTH
   YEAR (Pluto 248 yr, Neptune 165 yr, Uranus 84 yr, Chiron 50.7 yr), and the mean of the pair is
   the clock on the couple's mean birth epoch.  Era is the thing most likely to separate a marriage
   that ended in a death from one that ended in a divorce, so this block is expected to matter here
   even though ARTAMODEL.md found absolute-phase terms unhelpful on the marriage-year task (there
   the era was already handed over as the wedding date; here it is not handed over at all).

WHAT IS NOT EMITTED, AND WHY (measured, not assumed)
----------------------------------------------------
  * ascendant / medium_coeli — always NaN in Z (no birth times), so 100% empty columns.  Verified:
    nan fraction 1.000 on both slots.
  * true_south_node — a RIGID mirror: measured on this dataset's Z, theta_south - theta_node is
    exactly 180.000000 on all 20,955 training rows.  Its arc column is then IDENTICAL to the node's
    (|d| is unchanged by adding 180 to both charts), and its natal column is exactly +/- the node's
    (cos(h(t+180)) = (-1)^h cos(h t)).  Both are linearly dependent columns: for the linear/phasor
    stage this module feeds, a duplicated or negated copy adds exactly zero and only splits a
    weight.  So 13 bodies, not 14.
  * higher arc harmonics on the slowest bodies — the arc of a slow planet cannot span the circle
    over a human age gap (measured 99th percentile |arc|: Pluto 49.6 deg, Neptune 77.3 deg, Uranus
    148.0 deg), so its high harmonics are still monotone in the arc and are LINEARLY REDUNDANT.
    Measured incremental R^2 of each harmonic pair against the lower ones of the same body (train
    half, label-free): Pluto h3 1.000 / h4 1.000, Neptune h3 0.997-1.000 / h4 1.000, Uranus h4
    cos 0.997 sin 0.995.  Those pairs are dropped.  Everything kept has at least one component
    below 0.99, i.e. carries >=1% of its own variance.  Harmonics are pruned as PAIRS, never as
    single columns: a phasor stage needs both components of e^{i h phi} to own a free complex
    weight, so half a pair would hobble exactly the model this module exists to serve.
  * a "composite"/Davison midpoint phasor (ArtaModel's "c" term) — the normalised natal-sum
    direction.  Dropped because for the slow bodies, where a midpoint would mean something, the arc
    is small (Pluto |arc| <= 50 deg at the 99th pct), so the sum's amplitude 2cos(arc/2) is nearly
    constant and the unit midpoint is within a few percent of the Block-B column already emitted.
  * anything derived from df.start — it is '0000-00-00' on every row of this dataset.

ORDER-FREENESS (exact, not approximate)
---------------------------------------
Swapping the two partners must leave X bitwise identical, and does:
  * the arc is computed as  min( (theta_a-theta_b) mod 360, (theta_b-theta_a) mod 360 ).  IEEE
    subtraction gives exactly negated results for the two orders, so the swap merely exchanges the
    two arguments of a commutative min — the result is the same float, not a nearby one.  (The
    usual |wrap180(d)| is equal mathematically but can differ in the last ulp between the two
    orders; this form cannot.)
  * the natal block is (x + y)/2, and floating addition is commutative.
The self-test asserts EXACT equality of X under a swap of both the date columns and the theta
matrices, and it is an assert rather than a tolerance for that reason.

MISSING DATA — four date shapes, nothing invented
--------------------------------------------------
'YYYY-MM-DD' full; 'YYYY-00-00' year only; '0000-MM-DD' month/day but NO year; '0000-00-00' absent.
  * no year -> nothing in that chart can be placed (an ephemeris needs an epoch): every body of
    that partner is forced to NaN even if Z supplied a number.
  * year but no month/day -> the day-precision bodies (sun, moon, mercury, venus, mars) are forced
    to NaN; the slow bodies resolve from a year alone and are kept.  (Both guards are no-ops
    against this dataset's Z, which already NaNs exactly these; they exist so that a Z which had
    quietly defaulted an unknown date to some epoch could not leak a fabricated longitude.)
  * NaN then propagates: an arc needs BOTH partners, and so does the tied natal term (it is one
    term over two phases — the presence rule applied to a tied weight), so either partner missing
    leaves the column NaN rather than silently turning a two-phasor mean into a one-phasor value of
    a different magnitude.
No date component is ever cast to an int, and no lookup table is indexed by anything derived from a
date, so a NaN can never index a row of anything.  Dates are read ONLY to decide presence.

PURITY: build(df, Z, half) reads only df and Z, has no I/O, no network, no randomness, no global
state, and the column plan is a module-level constant, so 'train' and 'test' return the same width.

VERIFIED (all four date shapes in every combination on a synthetic Z, and the real 20,955 / 2,801
rows): 162 columns on both halves, identical names; a row with no year on either side comes back
ALL NaN even though the Z handed it longitudes; a year-only row keeps the eight slow bodies and
NaNs the five day-precision ones; every finite value lies in [-1, 1]; X is bitwise identical after
swapping the two partners (dates and theta matrices together) on synthetic and on real rows; the
largest absolute correlation between any two of the 162 columns is 0.986, so no column duplicates
another.  Usability, as a sanity check rather than a result: an ordinary ridge on these columns
alone (NaN -> 0, the presence rule) reaches 0.700 AUC on a random held-out half and recovers a
planted phasor — a signal built from cos|arc_uranus| makes pp_arc_cos_h1_uranus the largest fitted
weight of the 162, which is the artamodel.py self-test transposed to this basis.  On a TEMPORAL
split (fit on couples born <= 1900, scored on later ones) the arc block holds 0.539 while the natal
block falls below chance: the natal phasors are era clocks, and an era clock cannot transfer across
a split made ON era.  Both halves are emitted anyway — which one to trust is the downstream stage's
decision to make, and hiding either would be hiding the evidence for it.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Bodies.  Order fixed here; resolved from Z BY NAME so a reordered npz cannot
# silently shuffle them.  'ascendant'/'medium_coeli' (always NaN) and
# 'true_south_node' (rigid 180-degree mirror of true_node) are excluded above.
# ---------------------------------------------------------------------------
BODIES = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus',
          'neptune', 'pluto', 'true_node', 'chiron', 'mean_lilith']
NB = len(BODIES)
BIDX = {b: i for i, b in enumerate(BODIES)}

# Day-precision bodies: they move ~0.5-13 deg/day, so a year-only date cannot place them and any
# value for one of them on such a row would be a fabrication.
FAST = ('sun', 'moon', 'mercury', 'venus', 'mars')

# --- THE PLAN (static: identical width on both halves) ----------------------
# ARC ladder per body.  Full h=1..4 except where a harmonic PAIR was measured linearly redundant
# against the lower harmonics of the same body on the train half (incremental R^2 >= 0.99 on both
# components; see WHAT IS NOT EMITTED).  Rate/period given for why the arc does or does not wrap
# over a human age gap.
ARC_H = {
    'sun':         (1, 2, 3, 4),   # ~1 deg/day  — arc uniform on the circle; every dial is live
    'moon':        (1, 2, 3, 4),   # ~13 deg/day
    'mercury':     (1, 2, 3, 4),   # ~1.4 deg/day
    'venus':       (1, 2, 3, 4),   # ~1.2 deg/day
    'mars':        (1, 2, 3, 4),   # ~0.5 deg/day
    'jupiter':     (1, 2, 3, 4),   # 11.9 yr  -> 30.3 deg/yr; wraps over any gap
    'saturn':      (1, 2, 3, 4),   # 29.5 yr  -> 12.2 deg/yr; arc fills the circle
    'true_node':   (1, 2, 3, 4),   # 18.6 yr  -> 19.3 deg/yr
    'chiron':      (1, 2, 3, 4),   # 50.7 yr  ->  7.1 deg/yr; p99 |arc| 175 deg
    'mean_lilith': (1, 2, 3, 4),   #  8.85 yr -> 40.7 deg/yr
    'uranus':      (1, 2, 3),      # 84 yr    ->  4.3 deg/yr; p99 |arc| 148 deg, h4 pair R^2 .995+
    'neptune':     (1, 2),         # 165 yr   ->  2.2 deg/yr; p99 |arc|  77 deg, h3+ R^2 .997+
    'pluto':       (1, 2),         # 248 yr   ->  1.5 deg/yr; p99 |arc|  50 deg, h3+ R^2 1.000
}
# NATAL ladder per body.  Birth years here span 1400-1948, so EVERY body's natal longitude wraps
# the circle many times and every harmonic pair was measured independent (worst incremental
# R^2 = 0.60, Pluto h4).  The ladder is nevertheless run to h=4 only on the four bodies whose
# period exceeds a human lifetime — the genuine era clocks, where a higher harmonic buys real era
# resolution (Pluto 248/4 = 62 yr, Neptune 41 yr, Uranus 21 yr, Chiron 13 yr).  On the rest, a
# harmonic above 2 would only subdivide a wheel that already turns several times per generation.
NAT_H = {
    'uranus': (1, 2, 3, 4), 'neptune': (1, 2, 3, 4), 'pluto': (1, 2, 3, 4), 'chiron': (1, 2, 3, 4),
    'sun': (1, 2), 'moon': (1, 2), 'mercury': (1, 2), 'venus': (1, 2), 'mars': (1, 2),
    'jupiter': (1, 2), 'saturn': (1, 2), 'true_node': (1, 2), 'mean_lilith': (1, 2),
}
assert set(ARC_H) == set(BODIES) and set(NAT_H) == set(BODIES)

# Width, fixed at import: 2 columns per (body, harmonic) in each block.
N_COLS = 2 * sum(len(v) for v in ARC_H.values()) + 2 * sum(len(v) for v in NAT_H.values())

DEG = np.pi / 180.0


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _arc(ta, tb):
    """The wrapped ABSOLUTE inter-partner arc in [0, 180] degrees — artamodel.absdiff, written in
    the one form that is EXACTLY symmetric in (ta, tb) rather than symmetric to within an ulp.

    min(mod(ta-tb, 360), mod(tb-ta, 360)): swapping the partners exchanges the two arguments of a
    commutative min, so the returned float is identical, bit for bit.  NaN propagates (np.mod keeps
    NaN and np.minimum, unlike np.fmin, does not drop it)."""
    return np.minimum(np.mod(ta - tb, 360.0), np.mod(tb - ta, 360.0))


def _parse_dates(col, n):
    """(has_year, has_md) for one date column, over all four shapes.

    'YYYY-MM-DD' -> (True, True)   'YYYY-00-00' -> (True, False)
    '0000-MM-DD' -> (False, True)  '0000-00-00' -> (False, False)
    Anything unparseable (None, NaN, a short string) reads as absent.  Only the two booleans leave
    this function: no year/month/day number is ever used as a value or as an index."""
    s = pd.Series(col).astype(str).str.strip()
    y = pd.to_numeric(s.str.slice(0, 4), errors='coerce').to_numpy(dtype=np.float64)
    m = pd.to_numeric(s.str.slice(5, 7), errors='coerce').to_numpy(dtype=np.float64)
    d = pd.to_numeric(s.str.slice(8, 10), errors='coerce').to_numpy(dtype=np.float64)
    if y.shape[0] != n:
        raise ValueError('date column length %d != %d' % (y.shape[0], n))
    has_year = np.isfinite(y) & (y > 0)
    has_md = np.isfinite(m) & np.isfinite(d) & (m > 0) & (d > 0)
    return has_year, has_md


def _theta(Z, slot, half, n, has_year, has_md):
    """(n, 13) sidereal longitudes for one partner, columns in BODIES order, degrees, NaN unknown.

    Bodies are looked up by NAME; a body absent from Z yields an all-NaN column rather than a
    narrower matrix.  Then the two honesty guards of the docstring: no year -> the whole chart is
    NaN; no month/day -> the FAST bodies are NaN."""
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


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build(df, Z, half):
    """Phasor components for a downstream linear / phasor stage.  See the module docstring."""
    n = len(df)
    hy_a, hmd_a = _parse_dates(df['dob_a'], n)
    hy_b, hmd_b = _parse_dates(df['dob_b'], n)
    # df['start'] is deliberately not read: it is '0000-00-00' on every row of this dataset, so the
    # transit terms t1/t2/tn of TERMS_IV do not exist and are not simulated.
    TA = _theta(Z, 'a', half, n, hy_a, hmd_a)
    TB = _theta(Z, 'b', half, n, hy_b, hmd_b)

    cols, names = [], []

    def add(name, v):
        v = np.asarray(v, dtype=np.float64)
        if v.shape != (n,):
            raise ValueError('column %s has shape %r, expected (%d,)' % (name, v.shape, n))
        cols.append(v)
        names.append(name)

    for b in BODIES:
        j = BIDX[b]
        ta, tb = TA[:, j], TB[:, j]

        # --- Block A: the synastry arc phasor, e^{i h |theta_a - theta_b|} ------------------
        # Even in the swap by construction (_arc is exactly symmetric), so the pair encodes the
        # doctrine "these two bodies stand SOME arc apart" and never "whose is ahead".  NaN unless
        # both partners have this body — the presence rule for a difference term.
        arc = _arc(ta, tb)
        for h in ARC_H[b]:
            r = h * arc * DEG
            add('pp_arc_cos_h%d_%s' % (h, b), np.cos(r))
            add('pp_arc_sin_h%d_%s' % (h, b), np.sin(r))

        # --- Block B: the tied natal phasor, (e^{i h theta_a} + e^{i h theta_b}) / 2 ---------
        # One complex weight over both partners' natal phases (n1 and n2 of TERMS_IV sharing a
        # weight) — the order-free form of "cos and sin of each partner's raw longitude".  For a
        # slow body this is the clock on the couple's mean birth epoch; for the sun it is the mean
        # seasonal position (the sun-sign doctrine, on a continuous dial).  NaN unless both
        # partners have the body, so a two-phasor mean is never silently replaced by a one-phasor
        # value of different magnitude.
        for h in NAT_H[b]:
            ra, rb = h * ta * DEG, h * tb * DEG
            add('pp_nat_cos_h%d_%s' % (h, b), (np.cos(ra) + np.cos(rb)) / 2.0)
            add('pp_nat_sin_h%d_%s' % (h, b), (np.sin(ra) + np.sin(rb)) / 2.0)

    X = np.column_stack(cols).astype(np.float32) if cols else np.zeros((n, 0), dtype=np.float32)
    if X.shape[1] != N_COLS or len(names) != N_COLS:
        raise AssertionError('emitted %d columns, plan says %d' % (X.shape[1], N_COLS))
    if len(set(names)) != len(names):
        raise AssertionError('duplicate column name')
    return X, names
