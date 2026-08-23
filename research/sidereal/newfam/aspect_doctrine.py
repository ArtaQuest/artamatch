"""aspect_doctrine — the classical synastry aspect system, done the way an astrologer reads a chart.

The catalogue already carries harmonics and raw longitude differences.  What it does NOT carry is the
ASPECT DOCTRINE proper: the named angular relationships (conjunction, opposition, trine, square,
sextile, quincunx, semisextile, semisquare, sesquiquadrate, quintile, biquintile, septile, novile),
each with its own ORB (the tolerance inside which the aspect is held to operate), each orb widened
when a luminary is involved and narrowed for the minor/points, and each contact weighted by how
CLOSE it is rather than by a hard in/out flag.  An aspect at 2 degrees is not the same as one at 7,
so membership is a triangular kernel that decays linearly from 1 at exactitude to 0 at the orb edge.

Everything here is computed on the CROSS-CHART grid only (partner A's body i against partner B's
body j) — that is synastry.  Same-chart aspects are a natal matter and belong to another module.

Order-freeness.  Every global aggregate is a sum/mean/max over the FULL 14x14 ordered grid, and the
orb of a pair is max(orb_factor_i, orb_factor_j); swapping the two partners maps the grid onto its
transpose, so every one of those statistics is invariant by construction.  The named-pair columns
are symmetrised explicitly: for an unordered body pair {X, Y} the two observable contacts are
(A.X, B.Y) and (A.Y, B.X), and swapping partners merely exchanges those two, so any set statistic
over them (np.fmax / np.fmin) is order-free too.

Missingness.  Z gives NaN longitudes for the five day-precision bodies (sun, moon, mercury, venus,
mars) when a birth date has no month/day.  NaN is propagated honestly: a pair with an unknown body
contributes to nothing, sums are reported alongside the number of valid pairs, means divide by that
count, and a row with no valid pair at all returns NaN rather than a zero that would read as
"no aspects".  Nothing is imputed anywhere.  df.start is ALWAYS '0000-00-00' in this dataset and is
never read.

Pure function of (df, Z): no I/O, no randomness, no globals mutated.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Bodies.  'ascendant' and 'medium_coeli' are excluded: with no birth time they
# are always NaN, so they can only add empty columns.
# ---------------------------------------------------------------------------
BODIES = [
    'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus',
    'neptune', 'pluto', 'true_node', 'true_south_node', 'chiron', 'mean_lilith',
]
NB = len(BODIES)

# Orb multipliers by body, the traditional hierarchy: the luminaries carry the
# widest orbs (they are the loudest bodies in a reading), the planets a normal
# orb, and the computed points (nodes, Chiron, Lilith) a deliberately tight one
# because a point is not a body and doctrine gives it less room.
ORB_FACTOR = {
    'sun': 1.5, 'moon': 1.5,
    'mercury': 1.0, 'venus': 1.0, 'mars': 1.0, 'jupiter': 1.0, 'saturn': 1.0,
    'uranus': 1.0, 'neptune': 1.0, 'pluto': 1.0,
    'true_node': 0.75, 'true_south_node': 0.75, 'chiron': 0.75, 'mean_lilith': 0.75,
}

# Bodies that resolve from a year alone (always present in Z).  Used for the
# coverage-stable block: aggregates restricted to these are computable for every
# row, so they cannot be confounded with date precision.
SLOW = {'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
        'true_node', 'true_south_node', 'chiron', 'mean_lilith'}

# ---------------------------------------------------------------------------
# The aspect table: (short name, exact angle in degrees, base orb, class).
#   class 'harm' = the flowing/easy aspects   (trine, sextile)
#   class 'hard' = the aspects of friction    (opposition, square, quincunx,
#                  semisquare, sesquiquadrate)
#   class 'conj' = the conjunction, which doctrine treats as neither easy nor
#                  hard but as FUSION — its tone comes from the bodies involved,
#                  so it is kept in its own bucket instead of being miscounted.
#   class 'minor'= the creative/minor family (semisextile, quintile, biquintile,
#                  septile, novile) — real in doctrine, weak in effect, hence the
#                  much tighter orbs.
# Base orbs follow common synastry practice: majors 5-8 deg, the 30/45/135/150
# family 2-3 deg, the quintile/septile/novile family 1-1.5 deg.
# ---------------------------------------------------------------------------
ASPECTS = [
    ('conjunction',     0.0,       8.0, 'conj'),
    ('opposition',    180.0,       8.0, 'hard'),
    ('trine',         120.0,       7.0, 'harm'),
    ('square',         90.0,       7.0, 'hard'),
    ('sextile',        60.0,       5.0, 'harm'),
    ('quincunx',      150.0,       3.0, 'hard'),
    ('semisextile',    30.0,       2.0, 'minor'),
    ('semisquare',     45.0,       2.0, 'hard'),
    ('sesquiquadrate', 135.0,      2.0, 'hard'),
    ('quintile',       72.0,       1.5, 'minor'),
    ('biquintile',    144.0,       1.5, 'minor'),
    ('septile',       360.0 / 7.0, 1.0, 'minor'),   # 51.4286
    ('novile',         40.0,       1.0, 'minor'),
]

MAJORS = ['conjunction', 'opposition', 'trine', 'square', 'sextile']
EXACT_DEG = 1.0          # "exact" = within one degree of the true angle

# The pairs synastry doctrine names for marriage, each given its own columns.
#   sun_moon      — the classical marriage contact (the pair of luminaries)
#   venus_mars    — attraction/desire
#   venus_saturn  — love met by duty, coldness, endurance; the classic hard-love pair
#   moon_moon     — emotional rhythm shared or clashing
#   sun_sun       — vitality/identity, and the solar (day-of-year) relation
#   venus_venus   — matching taste and affection style
#   mars_saturn   — friction against restraint; the frustration/anger pair
#   moon_saturn   — the pair most often blamed for coldness in a marriage
NAMED_PAIRS = [
    ('sun_moon',     'sun',   'moon'),
    ('venus_mars',   'venus', 'mars'),
    ('venus_saturn', 'venus', 'saturn'),
    ('moon_moon',    'moon',  'moon'),
    ('sun_sun',      'sun',   'sun'),
    ('venus_venus',  'venus', 'venus'),
    ('mars_saturn',  'mars',  'saturn'),
    ('moon_saturn',  'moon',  'saturn'),
]
NAMED_ASPECTS = MAJORS   # each named pair gets its five major memberships


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _theta(Z, slot, half, n):
    """(n, 14) sidereal longitudes for one partner, columns in BODIES order.

    Resolved by NAME from Z['bodies'] so a reordered npz cannot silently shuffle
    the bodies.  A body absent from the npz yields an all-NaN column, which keeps
    the returned width constant instead of dropping features."""
    T = np.asarray(Z['theta_%s_%s' % (slot, half)], dtype=np.float64)
    if T.ndim != 2 or T.shape[0] != n:
        raise ValueError('theta_%s_%s has shape %r, expected (%d, k)' % (slot, half, T.shape, n))
    names = [str(x) for x in np.asarray(Z['bodies']).ravel().tolist()]
    where = {nm: i for i, nm in enumerate(names)}
    out = np.full((n, NB), np.nan, dtype=np.float64)
    for k, b in enumerate(BODIES):
        j = where.get(b)
        if j is not None and j < T.shape[1]:
            out[:, k] = T[:, j]
    return out


def _sep_grid(A, B):
    """(n, 14, 14) undirected angular separation in [0, 180].

    sep[:, i, j] is the angle between partner A's body i and partner B's body j.
    NaN in either longitude propagates to NaN, never to 0."""
    d = np.mod(A[:, :, None] - B[:, None, :], 360.0)
    return np.minimum(d, 360.0 - d)


def _tri(dist, orb):
    """Triangular orb membership: 1 at exactitude, falling linearly to 0 at the
    orb edge, 0 beyond.  np.maximum is used (not np.clip on a comparison) so that
    NaN stays NaN instead of collapsing to 'no aspect'."""
    return np.maximum(0.0, 1.0 - dist / orb)


def _date_flags(s):
    """(has_year, has_month_day) for a 'YYYY-MM-DD' string, handling all four
    shapes: full, 'YYYY-00-00' (year only), '0000-MM-DD' (year unknown!),
    '0000-00-00' (absent).  Anything unparseable is treated as absent.  These are
    booleans about what was RECORDED — nothing is inferred from them."""
    if not isinstance(s, str):
        return False, False
    p = s.strip().split('-')
    if len(p) != 3:
        return False, False
    y, m, d = p[0], p[1], p[2]
    has_y = y.isdigit() and int(y) > 0
    has_md = m.isdigit() and d.isdigit() and int(m) > 0 and int(d) > 0
    return has_y, has_md


def _safe_div(num, den):
    """num/den with den<=0 -> NaN (never a fabricated zero)."""
    den = np.asarray(den, dtype=np.float64)
    out = np.full(num.shape, np.nan, dtype=np.float64)
    ok = den > 0
    np.divide(num, np.where(ok, den, 1.0), out=out, where=ok)
    return out


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

    fac = np.array([ORB_FACTOR[b] for b in BODIES], dtype=np.float64)
    # A pair's orb is the WIDER of the two bodies' allowances — standard practice,
    # and symmetric in (i, j), which is what keeps the grid aggregates order-free.
    orb_pair = np.maximum(fac[:, None], fac[None, :]).reshape(-1)          # (196,)
    is_slow = np.array([b in SLOW for b in BODIES])
    slow_mask = np.outer(is_slow, is_slow).reshape(-1)                      # (196,)

    sep3 = _sep_grid(A, B)                                                  # (n,14,14)
    sep = sep3.reshape(n, NB * NB)
    valid = np.isfinite(sep)
    nv = valid.sum(axis=1).astype(np.float64)                               # 0..196
    nv_slow = valid[:, slow_mask].sum(axis=1).astype(np.float64)            # 0..81

    # ---------------- A. coverage / date precision (5) ----------------
    # These make the missingness legible to the model instead of hiding it inside
    # the aggregates: a synastry with 81 computable pairs is a different reading
    # from one with 196, and the model must be able to tell them apart.
    add('cov_pairs_valid', nv)                       # cross-pairs with both longitudes known
    ka = np.isfinite(A).sum(axis=1).astype(np.float64)
    kb = np.isfinite(B).sum(axis=1).astype(np.float64)
    add('cov_bodies_max', np.maximum(ka, kb))        # order-free: max/min, never (a,b)
    add('cov_bodies_min', np.minimum(ka, kb))

    da = df['dob_a'] if 'dob_a' in df.columns else pd.Series([None] * n, index=df.index)
    db = df['dob_b'] if 'dob_b' in df.columns else pd.Series([None] * n, index=df.index)
    fa = [_date_flags(s) for s in da.tolist()]
    fb = [_date_flags(s) for s in db.tolist()]
    ya = np.array([f[0] for f in fa], dtype=np.float64)
    yb = np.array([f[0] for f in fb], dtype=np.float64)
    ma = np.array([f[1] for f in fa], dtype=np.float64)
    mb = np.array([f[1] for f in fb], dtype=np.float64)
    # counts (0/1/2), not (a,b) — order-free by construction.  df.start is ignored.
    # prec_n_year is constant (2) on a half where every dob carries a year; it is kept
    # because the '0000-MM-DD' shape is legal in the contract and, when it appears, it
    # is the only column that says the YEAR is the missing part rather than the day.
    add('prec_n_year', ya + yb)                      # how many dobs carry a real year
    add('prec_n_daymonth', ma + mb)                  # how many carry a real month+day

    # ---------------- B/C/D/E: one pass over the aspect table ----------------
    grp = {'harm': np.zeros(n), 'hard': np.zeros(n), 'conj': np.zeros(n), 'minor': np.zeros(n)}
    grp_slow = {'harm': np.zeros(n), 'hard': np.zeros(n), 'conj': np.zeros(n), 'minor': np.zeros(n)}
    n_exact_any = np.zeros(n)
    n_exact_major = np.zeros(n)
    n_exact_major_slow = np.zeros(n)
    min_orb_any = np.full(n, np.inf)
    min_orb_major = np.full(n, np.inf)
    min_orb_major_slow = np.full(n, np.inf)
    per_aspect_sum = {}
    exact_by_major = {}

    for aname, angle, base, klass in ASPECTS:
        dist = np.abs(sep - angle)                                   # orb distance
        w = _tri(dist, base * orb_pair[None, :])                     # triangular membership
        s = np.nansum(w, axis=1)
        per_aspect_sum[aname] = s
        grp[klass] += s
        grp_slow[klass] += np.nansum(w[:, slow_mask], axis=1)

        ex = np.isfinite(dist) & (dist < EXACT_DEG)
        exc = ex.sum(axis=1).astype(np.float64)
        n_exact_any += exc
        dfin = np.where(np.isfinite(dist), dist, np.inf)
        min_orb_any = np.minimum(min_orb_any, dfin.min(axis=1))
        if aname in MAJORS:
            exact_by_major[aname] = exc
            n_exact_major += exc
            n_exact_major_slow += ex[:, slow_mask].sum(axis=1).astype(np.float64)
            min_orb_major = np.minimum(min_orb_major, dfin.min(axis=1))
            min_orb_major_slow = np.minimum(min_orb_major_slow, dfin[:, slow_mask].min(axis=1))

    have = nv > 0
    have_slow = nv_slow > 0

    def gate(v, ok=None):
        ok = have if ok is None else ok
        return np.where(ok, v, np.nan)

    # B. per-aspect totals over the whole 14x14 cross grid (13 x 2 = 26).
    #    _w  = summed membership: "how much of this aspect is in the synastry",
    #          the quantity a reading actually adds up.
    #    _wn = the same divided by the number of computable pairs, so rows with
    #          missing fast bodies are comparable with complete ones.
    for aname, _, _, _ in ASPECTS:
        s = per_aspect_sum[aname]
        add('asp_w_' + aname, gate(s))
        add('asp_wn_' + aname, _safe_div(s, nv))

    # C. the doctrinal groupings (10)
    add('grp_w_harm', gate(grp['harm']))     # trine + sextile: the flowing weight
    add('grp_w_hard', gate(grp['hard']))     # opposition/square/quincunx/semisquare/sesquiquadrate
    add('grp_w_conj', gate(grp['conj']))     # fusion, kept separate from easy/hard
    add('grp_w_minor', gate(grp['minor']))   # the creative/minor family
    add('grp_wn_harm', _safe_div(grp['harm'], nv))
    add('grp_wn_hard', _safe_div(grp['hard'], nv))
    add('grp_wn_conj', _safe_div(grp['conj'], nv))
    add('grp_wn_minor', _safe_div(grp['minor'], nv))
    # the single number a reader quotes: what share of the tension/ease budget is ease
    add('grp_harm_ratio', _safe_div(grp['harm'], grp['harm'] + grp['hard']))
    # and the signed balance, coverage-normalised (positive = easier than it is hard)
    add('grp_harm_minus_hard_n', _safe_div(grp['harm'] - grp['hard'], nv))

    # D. exactitude (10).  Doctrine holds that a partile (near-exact) contact is
    #    categorically stronger than a wide one, so closeness gets its own block.
    add('exact_n_any', gate(n_exact_any))                    # contacts within 1 deg, any aspect
    add('exact_n_major', gate(n_exact_major))                # ... restricted to the five majors
    add('exact_n_major_n', _safe_div(n_exact_major, nv))
    for aname in MAJORS:
        add('exact_n_' + aname, gate(exact_by_major[aname]))
    add('orb_min_any', np.where(have & np.isfinite(min_orb_any), min_orb_any, np.nan))
    add('orb_min_major', np.where(have & np.isfinite(min_orb_major), min_orb_major, np.nan))

    # E. coverage-stable block: the same reading restricted to the nine bodies that
    #    resolve from a YEAR alone.  Computable for every row, so it cannot be
    #    confounded with how precisely the two birth dates were recorded (6).
    add('slow_wn_harm', _safe_div(grp_slow['harm'], nv_slow))
    add('slow_wn_hard', _safe_div(grp_slow['hard'], nv_slow))
    add('slow_wn_conj', _safe_div(grp_slow['conj'], nv_slow))
    add('slow_harm_ratio', _safe_div(grp_slow['harm'], grp_slow['harm'] + grp_slow['hard']))
    add('slow_exact_n_major', np.where(have_slow, n_exact_major_slow, np.nan))
    add('slow_orb_min_major',
        np.where(have_slow & np.isfinite(min_orb_major_slow), min_orb_major_slow, np.nan))

    # F. the named marriage pairs (61).
    #    For an unordered body pair {X, Y} the synastry offers two contacts,
    #    (A.X, B.Y) and (A.Y, B.X).  Swapping the partners exchanges those two, so
    #    np.fmax / np.fmin over the pair is order-free; fmax is also the doctrine
    #    ("is there a Venus-Saturn contact?" is answered by the stronger direction).
    #    fmax/fmin ignore a NaN direction and return NaN only when BOTH are unknown,
    #    which reports what was observed without inventing the missing direction.
    idx = {b: i for i, b in enumerate(BODIES)}
    for pname, bx, by in NAMED_PAIRS:
        i, j = idx[bx], idx[by]
        s_ab = sep3[:, i, j]
        s_ba = sep3[:, j, i]
        orb_f = max(fac[i], fac[j])              # symmetric in (i, j)
        for aname, angle, base, klass in ASPECTS:
            if aname not in NAMED_ASPECTS:
                continue
            w_ab = _tri(np.abs(s_ab - angle), base * orb_f)
            w_ba = _tri(np.abs(s_ba - angle), base * orb_f)
            add('%s_%s' % (pname, aname), np.fmax(w_ab, w_ba))
        # total hard weight on this pair (Venus-Saturn / Moon-Saturn / Mars-Saturn
        # doctrine is specifically about the HARD contacts between them)
        h_ab = np.zeros(n)
        h_ba = np.zeros(n)
        for aname, angle, base, klass in ASPECTS:
            if klass != 'hard':
                continue
            h_ab = h_ab + _tri(np.abs(s_ab - angle), base * orb_f)   # plain +, so NaN survives
            h_ba = h_ba + _tri(np.abs(s_ba - angle), base * orb_f)
        add('%s_hardsum' % pname, np.fmax(h_ab, h_ba))
        # the separations themselves, kept because the aspect kernels throw away
        # everything outside an orb and the raw angle still carries the relation
        # (Sun-Sun, for instance, IS the two birthdays' angular distance in the year)
        add('%s_sep_max' % pname, np.fmax(s_ab, s_ba))
        if i != j:
            # for a same-body pair the two directions are identical, so sep_min
            # would duplicate sep_max — emitted only for the cross-body pairs
            add('%s_sep_min' % pname, np.fmin(s_ab, s_ba))

    X = np.stack(cols, axis=1).astype(np.float32)
    assert X.shape == (n, len(names)), (X.shape, len(names))
    assert len(set(names)) == len(names), 'duplicate feature name'
    return X, names
