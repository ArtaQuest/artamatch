"""reenc_pattern — WHOLE-CHART PATTERN AND SHAPE doctrine, for one chart and for the pair.

Everything else in the catalogue reads a chart as a bag of PAIRWISE contacts: this longitude against
that longitude, aspect by aspect.  That is not how an astrologer opens a chart.  The first thing read
is the SHAPE — where the bodies clump, how much of the wheel is empty, whether the whole figure is a
bundle, a bowl with a handle, a see-saw or a splash — and only then the individual aspects.  Marc
Edmund Jones' seven planetary patterns (bundle, bowl, bucket, locomotive, see-saw, splash, splay) are
the classical statement of that reading, and the balance doctrine (fire/earth/air/water,
cardinal/fixed/mutable, "she has no water in her chart") is its companion.  Nothing in the catalogue
encodes either.  This module does, per partner and then — the part that actually matters for a
relationship — BETWEEN the two charts: do their occupied arcs overlap or interlock, does one
partner's stellium fall into the other's empty quarter, how far apart are the two charts' centres of
gravity, and do their element/modality balances duplicate each other or complete each other.

WHY IT COULD BEAR ON THE QUESTION.  The label separates an ending by death from an ending by divorce.
Chart-shape doctrine is read as temperament: a bundle chart is specialised and self-contained, a
splash diffuse, a bucket driven by its single handle body.  Pair doctrine holds that two charts which
interlock (each filling the other's empty arc) make a durable partnership while two that merely
duplicate each other do not.  This module states those claims as numbers so they can be contradicted.

TWO BODY SETS, deliberately.

  P10 — the ten classical planets, Sun through Pluto.  This is the set every pattern threshold in the
        literature was calibrated on, so it is the only set on which the named patterns are emitted.
        It needs DAY precision on both birth dates (Sun through Mars do not resolve from a year), so
        it is NaN for the rows that have none.  That is correct: the shape of a chart is not defined
        until you know where all ten bodies are, and a shape computed from six of them is a different
        object wearing the same name.

  P8  — jupiter, saturn, uranus, neptune, pluto, chiron, true_node, mean_lilith.  The bodies Z can
        place from a YEAR alone, so this block is computable for essentially every row and cannot be
        confounded with how precisely a birth date was recorded.  It is an ECHO of the same reading,
        not the doctrine itself: no named pattern is claimed from it, only the continuous shape
        quantities (dispersion, empty arc, occupancy, balance) that are defined for any body set.

  true_south_node is excluded from BOTH sets on purpose.  It is exactly 180 degrees from true_node by
  construction, so it carries no shape information at all, while its guaranteed antipode would drag
  every resultant length toward zero and split every empty arc in two — it would corrupt the very
  statistics this module exists to measure.  ascendant and medium_coeli are excluded because with no
  birth time they are always NaN.

ORDER-FREENESS.  No per-partner quantity is ever emitted raw.  Every one is reduced by
max / min / |difference| over the two partners (all three symmetric under a swap), and every genuinely
relational quantity is symmetric by construction: an arc intersection length does not know which arc
came first, a pooled chart is the union of two sets, a "count of elements one partner lacks and the
other supplies" sums both directions, and a pattern class is emitted as the COUNT of partners holding
it (0, 1, 2) rather than as A's class and B's class.  max/min use np.maximum/np.minimum, which
PROPAGATE NaN — a per-chart property with one chart unknown is unknown, not "equal to the known one".

MISSINGNESS.  A chart's shape statistics are computed only when every body in its set is finite; the
row is NaN otherwise, and every pair feature is NaN unless both charts are complete.  Nothing is
imputed.  For index safety, longitudes are replaced by 0.0 on incomplete rows BEFORE any floor-to-sign
cast, so a NaN can never become an integer that indexes a sign/element table; those rows are then
masked back to NaN.  Coverage is reported honestly by three columns (how many of the ten planets each
partner actually has) so a model can condition on precision instead of confusing it with doctrine.

A HONEST CAVEAT, stated rather than hidden.  The P8 bodies move slowly, so for a year-only birth date
the whole P8 figure is a deterministic function of the birth YEAR; two people born in nearby years
have near-identical outer-planet figures.  The P8 pair features therefore carry a large component of
"how far apart in time were these two born".  That is a real property of the doctrine on this data,
not a defect of the encoding, and it is why the P10 block — whose fast bodies scramble within a year —
is emitted alongside it rather than replaced by it.

THE FOUR DATE SHAPES, and how they are handled.  This module never re-parses the date strings; it
reads the FINITENESS PATTERN of Z, which is the ground truth for what can actually be computed.  A
full 'YYYY-MM-DD' places all fourteen bodies, so both blocks read.  'YYYY-00-00' (year only) places
the slow bodies but not Sun through Mars, so P10 is NaN and P8 reads.  '0000-MM-DD' (year unknown)
can place at most the Sun, so BOTH blocks are NaN.  '0000-00-00' places nothing and everything is
NaN.  All four were exercised against the real npz and against a synthetic Z before this shipped.
Deriving precision from Z rather than from the strings also means there is exactly one source of
truth: a feature is emitted when and only when the bodies it is made of exist.

df is therefore read only for its LENGTH.  df.start is ALWAYS the string '0000-00-00' in this dataset.  It is never read here, and nothing in
this module uses a wedding date, an age, or anything but the two birth charts Z supplies.

Pure function of (df, Z, half): no I/O, no network, no randomness, no global state mutated.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Body sets (see the module docstring for why each is what it is).
# ---------------------------------------------------------------------------
P10 = ['sun', 'moon', 'mercury', 'venus', 'mars',
       'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']

P8 = ['jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
      'chiron', 'true_node', 'mean_lilith']

# Sign s (0 = Aries .. 11 = Pisces) has element s % 4 (fire, earth, air, water)
# and modality s % 3 (cardinal, fixed, mutable).  Both identities are exact for
# the standard zodiac ordering and are why no lookup table is needed.
ELEM_NAMES = ['fire', 'earth', 'air', 'water']
MODAL_NAMES = ['cardinal', 'fixed', 'mutable']

# Classical pattern thresholds (Marc Edmund Jones), in degrees.  Emitted only for
# P10, the set they were stated for.
T_BUNDLE = 120.0     # every planet inside one trine
T_BOWL = 180.0       # every planet inside one hemisphere
T_ISOLATE = 60.0     # a body separated from its neighbours by a sextile counts as cut off
T_BUCKET_BODY = 200.0   # the nine remaining planets of a bucket still read as a bowl
T_LOCO_LO = 90.0     # locomotive: one empty gap of roughly a square-to-quincunx
T_LOCO_HI = 150.0
STELLIUM_ARC = 30.0  # doctrine's stellium: three or more bodies inside one sign's width
COG_ORB = 15.0       # the orb allowed to an AGGREGATE direction, deliberately wide


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _theta(Z, slot, half, n, want):
    """(n, len(want)) sidereal longitudes for one partner, columns in `want` order.

    Bodies are resolved BY NAME from Z['bodies'] so a reordered npz cannot silently
    shuffle them.  A body absent from the npz yields an all-NaN column, which keeps
    the returned width constant instead of dropping features."""
    T = np.asarray(Z['theta_%s_%s' % (slot, half)], dtype=np.float64)
    if T.ndim != 2 or T.shape[0] != n:
        raise ValueError('theta_%s_%s has shape %r, expected (%d, k)'
                         % (slot, half, T.shape, n))
    have = {str(x): i for i, x in enumerate(np.asarray(Z['bodies']).ravel().tolist())}
    out = np.full((n, len(want)), np.nan, dtype=np.float64)
    for k, b in enumerate(want):
        j = have.get(b)
        if j is not None and j < T.shape[1]:
            out[:, k] = T[:, j]
    return out


def _ent(cnt):
    """Shannon entropy (nats) of a count vector, row-wise.  0 log 0 is taken as 0.
    Rows summing to 0 return 0.0 and are gated to NaN by the caller."""
    tot = cnt.sum(axis=1, keepdims=True)
    p = cnt / np.maximum(tot, 1.0)
    lp = np.where(p > 0.0, np.log(np.where(p > 0.0, p, 1.0)), 0.0)
    return -(p * lp).sum(axis=1)


def _arc_overlap(s1, l1, s2, l2):
    """Length in degrees of the intersection of two circular arcs, arc i running
    FORWARD from s_i for l_i degrees.  Written as two interval intersections (the
    second wrapped by a full turn) because an arc can meet another in two pieces.
    The result is a geometric intersection, hence symmetric in (1, 2) — which is
    what makes every feature built on it order-free."""
    b = np.mod(s2 - s1, 360.0)
    o1 = np.minimum(l1, b + l2) - np.maximum(0.0, b)
    o2 = np.minimum(l1, b + l2 - 360.0) - np.maximum(0.0, b - 360.0)
    return np.maximum(o1, 0.0) + np.maximum(o2, 0.0)


def _arc_depth(p, s, l):
    """Signed degrees from point p to the nearer edge of the arc [s, s+l]:
    POSITIVE when p is inside (distance to the nearer edge), NEGATIVE when outside
    (minus the distance to the nearer edge).  Used for "how deeply does one
    partner's stellium sit in the other partner's empty arc"."""
    f = np.mod(p - s, 360.0)
    inside = f <= l
    d_in = np.minimum(f, l - f)
    d_out = np.minimum(np.maximum(f - l, 0.0), 360.0 - f)
    return np.where(inside, d_in, -d_out)


def _safe_div(num, den):
    """num/den with den <= 0 -> NaN (never a fabricated zero)."""
    num = np.asarray(num, dtype=np.float64)
    den = np.asarray(den, dtype=np.float64)
    out = np.full(np.broadcast(num, den).shape, np.nan, dtype=np.float64)
    ok = den > 0
    np.divide(num, np.where(ok, den, 1.0), out=out, where=ok)
    return out


def _cos_sim(A, B):
    """Row-wise cosine similarity of two count/proportion vectors; NaN if either
    row is all zero (an undefined direction is not a similarity of 0)."""
    na = np.sqrt((A * A).sum(1))
    nb = np.sqrt((B * B).sum(1))
    return _safe_div((A * B).sum(1), na * nb)


def _corr(A, B):
    """Row-wise Pearson correlation between two occupancy vectors; NaN when either
    is constant (a flat vector has no direction to agree or disagree with)."""
    a = A - A.mean(1, keepdims=True)
    b = B - B.mean(1, keepdims=True)
    return _safe_div((a * b).sum(1), np.sqrt((a * a).sum(1) * (b * b).sum(1)))


def _tri(dist, orb):
    """Triangular orb membership: 1 at exactitude, falling linearly to 0 at the orb
    edge.  np.maximum (not a comparison) so NaN stays NaN rather than collapsing
    to 'no contact'."""
    return np.maximum(0.0, 1.0 - dist / orb)


# ---------------------------------------------------------------------------
# the per-chart reading
# ---------------------------------------------------------------------------
def _chart(L):
    """All shape statistics of ONE chart.  L is (n, k) longitudes in degrees, NaN
    where the body could not be placed.

    A chart counts as readable only when EVERY body in the set is finite: the shape
    of a figure is not defined while part of the figure is missing.  Unreadable rows
    have their longitudes replaced by 0.0 first — so that the floor-to-sign cast can
    never turn a NaN into a bogus integer index — and every scalar returned for them
    is NaN.  Raw arrays (suffix _raw) are returned ungated for the pair block, which
    applies its own ok_a & ok_b mask."""
    n, k = L.shape
    ok = np.isfinite(L).all(axis=1)
    Lf = np.where(ok[:, None], np.mod(L, 360.0), 0.0)
    nm = np.where(ok, 0.0, np.nan)          # add to a scalar to NaN the unreadable rows
    st = {'ok': ok, 'k': k, 'nm': nm}

    # --- circular dispersion -------------------------------------------------
    # The resultant length R of the unit vectors: 1 when every body sits on one
    # degree (a perfect bundle), 0 when they balance out around the wheel.  This is
    # the continuous form of "how concentrated is this chart".
    rad = np.radians(Lf)
    C = np.cos(rad).mean(1)
    S = np.sin(rad).mean(1)
    st['R'] = np.hypot(C, S) + nm
    # The chart's CENTRE OF GRAVITY: the mean direction of the same vectors.  This
    # is the single longitude an astrologer would point at to say "this chart sits
    # here".  Kept raw (a direction cannot be max/min'd) and used only in the pair
    # block, where the two centres' separation IS order-free.
    st['cog_raw'] = np.mod(np.degrees(np.arctan2(S, C)), 360.0)

    # --- the empty arcs, which are what shape doctrine is actually about --------
    Sd = np.sort(Lf, axis=1)
    G = np.empty((n, k), dtype=np.float64)
    G[:, :k - 1] = Sd[:, 1:] - Sd[:, :-1]
    G[:, k - 1] = Sd[:, 0] + 360.0 - Sd[:, k - 1]     # the wrap-around gap
    gmax = G.max(1)
    gi = G.argmax(1)
    gap_start = np.take_along_axis(Sd, gi[:, None], 1)[:, 0]
    st['G_raw'] = G
    st['gmax'] = gmax + nm                            # the largest EMPTY arc
    st['gap_start_raw'] = gap_start
    st['span_raw'] = 360.0 - gmax                     # the OCCUPIED arc's length
    st['occ_start_raw'] = np.mod(gap_start + gmax, 360.0)
    Gs = np.sort(G, axis=1)
    st['g2'] = Gs[:, -2] + nm                         # second largest gap: what
    # separates a locomotive (one gap) from a see-saw (two)
    st['g2_raw'] = Gs[:, -2]
    st['gap_ratio'] = _safe_div(Gs[:, -2], gmax) + nm  # in [0,1]; near 1 = two equal voids
    st['nge60'] = (G >= T_ISOLATE).sum(1).astype(np.float64) + nm

    # mean pairwise angular separation — a dispersion measure that, unlike R, does
    # not collapse for a symmetric figure (a perfect opposition has R = 0 but a
    # mean separation of 180)
    D = np.mod(Lf[:, None, :] - Lf[:, :, None], 360.0)      # D[:,i,j] = forward i->j
    sep = np.minimum(D, 360.0 - D)
    st['mean_sep'] = _safe_div(sep.sum(axis=(1, 2)), float(k * (k - 1))) + nm

    # --- sign / element / modality occupancy -----------------------------------
    sgn = np.clip((Lf // 30.0).astype(np.int64), 0, 11)     # Lf is finite by construction
    scnt = np.zeros((n, 12), dtype=np.float64)
    for s in range(12):
        scnt[:, s] = (sgn == s).sum(1)
    ecnt = np.zeros((n, 4), dtype=np.float64)
    mcnt = np.zeros((n, 3), dtype=np.float64)
    for s in range(12):
        ecnt[:, s % 4] += scnt[:, s]
        mcnt[:, s % 3] += scnt[:, s]
    st['scnt_raw'] = scnt
    st['ecnt_raw'] = ecnt
    st['mcnt_raw'] = mcnt
    st['nsign'] = (scnt > 0).sum(1).astype(np.float64) + nm
    st['sign_ent'] = _ent(scnt) + nm
    st['elem_ent'] = _ent(ecnt) + nm
    st['modal_ent'] = _ent(mcnt) + nm
    st['elem_max'] = ecnt.max(1) / float(k) + nm          # dominant element's share
    st['modal_max'] = mcnt.max(1) / float(k) + nm
    st['elem_empty'] = (ecnt == 0).sum(1).astype(np.float64) + nm   # "no water in her chart"
    st['modal_empty'] = (mcnt == 0).sum(1).astype(np.float64) + nm
    st['sign_max'] = scnt.max(1) + nm                     # strict single-sign stellium size
    # share of the figure in the first half of the zodiac (Aries-Virgo).  The only
    # hemisphere reading available without a birth time: the house hemispheres need
    # an ascendant, which is always NaN here, so they are not attempted.
    st['north'] = (Lf < 180.0).mean(1) + nm

    # --- stellium: the densest 30-degree window --------------------------------
    # Doctrine's stellium is three or more bodies within one sign's width.  A widest
    # window can always be anchored ON a body, so counting bodies within 30 degrees
    # FORWARD of each body and taking the maximum finds it exactly.
    within = D <= STELLIUM_ARC
    cntw = within.sum(2)
    best = cntw.argmax(1)
    st['stel'] = cntw.max(1).astype(np.float64) + nm
    Dbest = np.take_along_axis(D, best[:, None, None], 1)[:, 0, :]
    m = Dbest <= STELLIUM_ARC
    # centre of the winning window = anchor + mean offset of its members
    off = _safe_div(np.where(m, Dbest, 0.0).sum(1), m.sum(1))
    anchor = np.take_along_axis(Lf, best[:, None], 1)[:, 0]
    st['stel_ctr_raw'] = np.mod(anchor + np.nan_to_num(off), 360.0)

    return st


def _patterns(st):
    """The seven classical planetary patterns as mutually exclusive indicators.

    Evaluated in Jones' own precedence — the tighter figures claim a chart first —
    so exactly one indicator is 1 on a readable row and all are NaN on a row whose
    chart could not be read.

      bundle      all ten planets inside 120 degrees: a specialised, self-contained figure
      bowl        all ten inside 180: a chart with a whole empty hemisphere
      bucket      a bowl-like body of nine plus ONE body cut off on both sides — the
                  'handle', which doctrine says the whole life is driven through
      seesaw      two groups facing each other across two empty arcs: a life of
                  weighing one thing against another
      locomotive  one empty arc of about a trine and no other: self-driving, applied
      splash      no empty arc as wide as a sextile: interests scattered everywhere
      splay       none of the above — irregular clumps, the individualist figure
    """
    n, k = st['G_raw'].shape
    ok = st['ok']
    G = st['G_raw']
    gmax = st['G_raw'].max(1)
    span = 360.0 - gmax
    nge = (G >= T_ISOLATE).sum(1)

    # a body is 'isolated' when BOTH the gap before it and the gap after it (in
    # sorted order) are at least a sextile — the handle test
    iso = (G[:, np.arange(k) - 1] >= T_ISOLATE) & (G >= T_ISOLATE)
    n_iso = iso.sum(1)

    # if exactly one body is isolated, remove it: its two adjacent gaps merge, and
    # the remaining nine read as a bowl only if their own span is still bowl-like
    rest_gmax = np.zeros(n, dtype=np.float64)
    for t in range(k):
        merged = G[:, t - 1] + G[:, t]
        other = G.copy()
        other[:, t - 1] = -1.0
        other[:, t] = -1.0
        cand = np.maximum(merged, other.max(1))
        sel = iso[:, t] & (n_iso == 1)
        rest_gmax = np.where(sel, cand, rest_gmax)
    rest_span = 360.0 - rest_gmax

    bundle = span <= T_BUNDLE
    bowl = (~bundle) & (span <= T_BOWL)
    bucket = (~bundle) & (~bowl) & (n_iso == 1) & (rest_span <= T_BUCKET_BODY)
    seesaw = (~bundle) & (~bowl) & (~bucket) & (nge == 2) & (n_iso == 0)
    loco = (~bundle) & (~bowl) & (~bucket) & (~seesaw) & (nge == 1) \
        & (gmax >= T_LOCO_LO) & (gmax <= T_LOCO_HI)
    splash = (~bundle) & (~bowl) & (~bucket) & (~seesaw) & (~loco) & (gmax < T_ISOLATE)
    splay = ~(bundle | bowl | bucket | seesaw | loco | splash)

    out = {}
    for nm_, v in [('bundle', bundle), ('bowl', bowl), ('bucket', bucket),
                   ('seesaw', seesaw), ('loco', loco), ('splash', splash),
                   ('splay', splay)]:
        out[nm_] = np.where(ok, v.astype(np.float64), np.nan)
    out['n_iso'] = np.where(ok, n_iso.astype(np.float64), np.nan)
    return out


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build(df, Z, half):
    n = len(df)
    cols = []
    names = []

    def add(name, v):
        a = np.asarray(v, dtype=np.float64).reshape(n)
        cols.append(a)
        names.append(name)

    def red(tag, spec, a, b):
        """The order-free reduction of a per-partner scalar.  max/min say 'the more
        and the less extreme partner' without saying which is which; |difference|
        says how unlike they are.  np.maximum/np.minimum PROPAGATE NaN, so a pair
        with one unreadable chart stays unknown instead of borrowing the other's
        value.  `spec` selects which reductions this quantity earns: the central
        doctrine gets all three, a second-order quantity only what it adds."""
        if 'M' in spec:
            add(tag + '_max', np.maximum(a, b))
        if 'm' in spec:
            add(tag + '_min', np.minimum(a, b))
        if 'D' in spec:
            add(tag + '_absdiff', np.abs(a - b))

    A10 = _theta(Z, 'a', half, n, P10)
    B10 = _theta(Z, 'b', half, n, P10)
    A8 = _theta(Z, 'a', half, n, P8)
    B8 = _theta(Z, 'b', half, n, P8)

    sa10, sb10 = _chart(A10), _chart(B10)
    sa8, sb8 = _chart(A8), _chart(B8)

    # =========================================================================
    # 0. COVERAGE (3).  Facts about what was RECORDED, not about the charts: how
    #    many of the ten classical planets each partner could be placed with.
    #    Emitted so a model can separate 'this doctrine says nothing here' from
    #    'this birth date was never written down precisely'.  Order-free by
    #    min/max.  Never used to impute anything.
    # =========================================================================
    na10 = np.isfinite(A10).sum(1).astype(np.float64)
    nb10 = np.isfinite(B10).sum(1).astype(np.float64)
    add('cov_p10_min', np.minimum(na10, nb10))
    add('cov_p10_max', np.maximum(na10, nb10))
    add('cov_p10_both_complete', ((na10 == 10) & (nb10 == 10)).astype(np.float64))

    # =========================================================================
    # 1-2. THE PER-CHART SHAPE READING, reduced order-free.
    #      P10 gets the full trio on twelve quantities; P8 echoes the nine of them
    #      that do not need the fast bodies to mean anything, with max and
    #      |difference| only (its min is largely redundant once max and the spread
    #      are known, and the block exists for coverage, not for a second opinion).
    # =========================================================================
    #   key, reductions, what the quantity IS and which doctrine it encodes
    P10_CORE = [
        ('R',          'MmD', 'resultant length: 1 = every body on one degree (a bundle), '
                              '0 = the figure balances out round the wheel'),
        ('gmax',       'MmD', 'the largest EMPTY arc — the quantity every classical pattern '
                              'threshold is cut on'),
        ('g2',         'MmD', 'the second largest empty arc — ONE void is a locomotive, TWO are '
                              'a see-saw; the pair (gmax, g2) is what separates them'),
        ('nge60',      'MmD', 'how many empty arcs reach a sextile: the count of real voids'),
        ('nsign',      'MmD', 'how many of the twelve signs are occupied at all'),
        ('sign_ent',   'MmD', 'entropy of sign occupancy: a few signs shouting vs twelve murmuring'),
        ('elem_ent',   'MmD', 'entropy of the fire/earth/air/water balance'),
        ('modal_ent',  'MmD', 'entropy of the cardinal/fixed/mutable balance'),
        ('elem_max',   'MmD', "the dominant element's share of the figure"),
        ('elem_empty', 'MmD', 'elements entirely missing — the classic "no water in her chart"'),
        ('stel',       'MmD', 'stellium size: the most bodies inside any one 30-degree window'),
        ('sign_max',   'MD',  'the most bodies inside a single SIGN — the strict stellium; its min '
                              'is dropped because the 30-degree-window stellium above already '
                              'carries the weak end of the same reading'),
        # second-order P10 quantities: real doctrine, but each is close to a
        # monotone re-expression of one above, so only what it ADDS is emitted
        ('modal_max',  'MD',  "the dominant modality's share"),
        ('modal_empty', 'D',  'modalities entirely missing (rare with ten bodies, hence diff only)'),
        ('north',      'D',   'share of the figure in Aries-Virgo — the only hemisphere reading '
                              'available with no birth time (the house hemispheres need an '
                              'ascendant, which is always NaN here)'),
        ('mean_sep',   'D',   'mean pairwise separation: a dispersion measure that, unlike R, does '
                              'not collapse on a symmetric figure'),
    ]
    # The coverage-stable echo.  Only the quantities that still mean something for a
    # set of eight slow bodies, and only max + |difference| — this block exists so
    # every row has a shape reading, not to give a second opinion on the P10 one.
    P8_CORE = [
        ('R', 'MD'), ('gmax', 'MD'), ('g2', 'D'), ('nge60', 'MD'), ('nsign', 'MD'),
        ('elem_ent', 'MD'), ('elem_max', 'D'), ('elem_empty', 'MD'), ('stel', 'MD'),
    ]

    for key, spec, _doc in P10_CORE:
        red('p10_' + key, spec, sa10[key], sb10[key])                  # 40
    for key, spec in P8_CORE:
        red('p8_' + key, spec, sa8[key], sb8[key])                     # 16

    # =========================================================================
    # 3. THE NAMED PATTERNS (8), P10 only.
    #    Emitted as the COUNT of partners holding each class (0, 1 or 2) — which is
    #    symmetric under a swap by construction — plus whether the two charts are
    #    the SAME figure, which is the doctrinal question ("two bowls facing each
    #    other" is a different marriage from "a bowl and a splash").
    # =========================================================================
    pa, pb = _patterns(sa10), _patterns(sb10)
    for key in ['bundle', 'bowl', 'bucket', 'seesaw', 'loco', 'splash', 'splay']:
        add('pat_n_' + key, pa[key] + pb[key])
    both = sa10['ok'] & sb10['ok']
    same = np.zeros(n, dtype=np.float64)
    for key in ['bundle', 'bowl', 'bucket', 'seesaw', 'loco', 'splash', 'splay']:
        same = same + np.nan_to_num(pa[key]) * np.nan_to_num(pb[key])
    add('pat_same_class', np.where(both, same, np.nan))

    # =========================================================================
    # 4. OCCUPIED-ARC GEOMETRY (10).  The pair question shape doctrine actually
    #    asks: do the two figures sit on top of each other, or does each occupy
    #    what the other leaves empty?  The occupied arc of a chart is the complement
    #    of its largest empty arc; the intersection of two arcs is a geometric
    #    quantity and therefore already order-free.
    # =========================================================================
    def arc_block(sa, sb, tag, full):
        both_ = sa['ok'] & sb['ok']
        g = lambda v: np.where(both_, v, np.nan)
        sA, lA = sa['occ_start_raw'], sa['span_raw']
        sB, lB = sb['occ_start_raw'], sb['span_raw']
        ov = _arc_overlap(sA, lA, sB, lB)
        union = lA + lB - ov
        add(tag + '_arc_jaccard', g(_safe_div(ov, union)))
        # how much of each partner's EMPTY arc the other partner's bodies fill.
        # 1.0 = the other chart lands squarely in the void this chart leaves — the
        # doctrinal 'interlock'.  Reduced max/min so neither direction is named.
        # each chart's EMPTY arc runs forward from gap_start for (360 - span) degrees
        fillA = _safe_div(_arc_overlap(sa['gap_start_raw'], 360.0 - lA, sB, lB), 360.0 - lA)
        fillB = _safe_div(_arc_overlap(sb['gap_start_raw'], 360.0 - lB, sA, lA), 360.0 - lB)
        add(tag + '_gapfill_max', g(np.maximum(fillA, fillB)))
        add(tag + '_gapfill_min', g(np.minimum(fillA, fillB)))
        # the product is the single 'do they interlock BOTH ways' number, and a
        # product of two order-free-as-a-set quantities is itself symmetric
        add(tag + '_interlock', g(fillA * fillB))
        if full:
            add(tag + '_arc_overlap_deg', g(ov))
            # (the union is not emitted: it is lA + lB - overlap, and both spans are
            #  already carried by p10_gmax_max / p10_gmax_min)
            # distance between the two occupied arcs' starting points: are the two
            # figures rotated onto each other or a third of a turn apart
            d = np.mod(sA - sB, 360.0)
            add(tag + '_arc_start_dist', g(np.minimum(d, 360.0 - d)))

    arc_block(sa10, sb10, 'p10', True)      # 7
    arc_block(sa8, sb8, 'p8', False)        # 4

    # =========================================================================
    # 5. STELLIUM AGAINST THE OTHER CHART'S VOID (6).  The specific claim: one
    #    partner's concentration of bodies falling into the arc the other partner
    #    leaves entirely empty is the classical 'she supplies what he has none of'.
    #    Emitted as a count over both directions (symmetric) and as max/min of the
    #    signed depth (also symmetric as a set statistic).
    # =========================================================================
    def stel_block(sa, sb, tag):
        both_ = sa['ok'] & sb['ok']
        g = lambda v: np.where(both_, v, np.nan)
        dA = _arc_depth(sa['stel_ctr_raw'], sb['gap_start_raw'], sb['gmax'])  # A's stellium in B's void
        dB = _arc_depth(sb['stel_ctr_raw'], sa['gap_start_raw'], sa['gmax'])
        add(tag + '_stel_in_void_n', g((dA > 0).astype(np.float64) + (dB > 0).astype(np.float64)))
        add(tag + '_stel_void_depth_max', g(np.maximum(dA, dB)))
        add(tag + '_stel_void_depth_min', g(np.minimum(dA, dB)))

    stel_block(sa10, sb10, 'p10')           # 3
    stel_block(sa8, sb8, 'p8')              # 3

    # =========================================================================
    # 6. CENTRES OF GRAVITY (9).  Each chart has one mean direction; the angle
    #    between the two is the single most compact statement of 'how far apart do
    #    these two figures sit on the wheel'.  A separation is symmetric, so this is
    #    order-free.  Its aspect memberships get a deliberately WIDE orb (15 deg)
    #    because an aggregate direction is not a body and does not deserve a body's
    #    precision.
    # =========================================================================
    def cog_block(sa, sb, tag, full):
        both_ = sa['ok'] & sb['ok']
        d = np.mod(sa['cog_raw'] - sb['cog_raw'], 360.0)
        dist = np.where(both_, np.minimum(d, 360.0 - d), np.nan)
        add(tag + '_cog_dist', dist)
        add(tag + '_cog_cos', np.cos(np.radians(dist)))
        if full:
            # only the aspects doctrine reads on an AGGREGATE direction: fused,
            # flowing, or facing.  The sextile and square are body-to-body claims
            # and are not asserted of a centre of gravity.
            for ang in [0.0, 120.0, 180.0]:
                add('%s_cog_asp%d' % (tag, int(ang)), _tri(np.abs(dist - ang), COG_ORB))

    cog_block(sa10, sb10, 'p10', True)      # 7
    cog_block(sa8, sb8, 'p8', False)        # 2

    # =========================================================================
    # 7. ELEMENT AND MODALITY BALANCE — DIFFERENCE and COMPLEMENTARITY (13).
    #    Balance doctrine read as a pair: do the two charts duplicate one another's
    #    emphasis, or does each supply what the other lacks?  Every statistic is
    #    stated symmetrically — an L1 distance, a cosine, and counts that sum both
    #    directions of 'one has none of this and the other has plenty'.
    # =========================================================================
    def bal_block(sa, sb, tag, cnt_key, label, full):
        both_ = sa['ok'] & sb['ok']
        g = lambda v: np.where(both_, v, np.nan)
        cA, cB = sa[cnt_key], sb[cnt_key]
        pA = cA / float(sa['k'])
        pB = cB / float(sb['k'])
        add('%s_%s_l1' % (tag, label), g(np.abs(pA - pB).sum(1)))
        # one partner has NONE of an element and the other has at least two bodies
        # in it: the doctrinal 'she brings him the water he has none of'.  Both
        # directions summed, so the count cannot know which partner is which.
        fill = ((cA == 0) & (cB >= 2)).sum(1) + ((cB == 0) & (cA >= 2)).sum(1)
        add('%s_%s_complement' % (tag, label), g(fill.astype(np.float64)))
        # neither of them has any: a lack the couple shares and nobody can cover
        add('%s_%s_double_lack' % (tag, label),
            g(((cA == 0) & (cB == 0)).sum(1).astype(np.float64)))
        if full:
            add('%s_%s_cos' % (tag, label), g(_cos_sim(pA, pB)))
            # both heavily weighted to the SAME element: doubled, not balanced
            add('%s_%s_double_heavy' % (tag, label),
                g(((pA >= 0.4) & (pB >= 0.4)).sum(1).astype(np.float64)))
            # the couple read as ONE figure: pooled balance, inherently symmetric
            pool = cA + cB
            add('%s_%s_pool_ent' % (tag, label), g(_ent(pool)))
            add('%s_%s_pool_empty' % (tag, label),
                g((pool == 0).sum(1).astype(np.float64)))

    bal_block(sa10, sb10, 'p10', 'ecnt_raw', 'elem', True)     # 7
    bal_block(sa10, sb10, 'p10', 'mcnt_raw', 'modal', False)   # 3
    bal_block(sa8, sb8, 'p8', 'ecnt_raw', 'elem', False)       # 3

    # =========================================================================
    # 8. SIGN OCCUPANCY AS SETS (5).  Coarser than the arc geometry and closer to
    #    how a chart is actually spoken about ('we share a Scorpio emphasis; the
    #    whole air trine is empty between us').  Set statistics are symmetric.
    # =========================================================================
    def sign_block(sa, sb, tag, full):
        both_ = sa['ok'] & sb['ok']
        g = lambda v: np.where(both_, v, np.nan)
        oA = sa['scnt_raw'] > 0
        oB = sb['scnt_raw'] > 0
        inter = (oA & oB).sum(1).astype(np.float64)
        union = (oA | oB).sum(1).astype(np.float64)
        add(tag + '_sign_jaccard', g(_safe_div(inter, union)))
        if full:
            add(tag + '_sign_both', g(inter))
            # signs empty in BOTH charts — the couple's shared blind quarter
            add(tag + '_sign_neither', g(12.0 - union))
            add(tag + '_sign_corr', g(_corr(sa['scnt_raw'], sb['scnt_raw'])))
            add(tag + '_sign_pool_ent', g(_ent(sa['scnt_raw'] + sb['scnt_raw'])))

    sign_block(sa10, sb10, 'p10', True)     # 5
    sign_block(sa8, sb8, 'p8', False)       # 1

    # =========================================================================
    # 9. THE POOLED CHART (7).  Put all twenty bodies on one wheel and read THAT
    #    figure — the composite the couple makes together.  A union is symmetric by
    #    construction, so nothing here needs reducing.
    # =========================================================================
    def pool_block(Xa, Xb, tag, full):
        sp = _chart(np.concatenate([Xa, Xb], axis=1))
        add(tag + '_pool_R', sp['R'])
        add(tag + '_pool_gmax', sp['gmax'])
        if full:
            add(tag + '_pool_nsign', sp['nsign'])
            add(tag + '_pool_stel', sp['stel'])
            add(tag + '_pool_sign_ent', sp['sign_ent'])
            add(tag + '_pool_elem_empty', sp['elem_empty'])
            add(tag + '_pool_nge60', sp['nge60'])

    pool_block(A10, B10, 'p10', True)       # 7
    pool_block(A8, B8, 'p8', False)         # 2

    X = np.stack(cols, axis=1).astype(np.float32)
    assert X.shape == (n, len(names)), (X.shape, len(names))
    assert len(set(names)) == len(names), 'duplicate feature name'
    return X, names
