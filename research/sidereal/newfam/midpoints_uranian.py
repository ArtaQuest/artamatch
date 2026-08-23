"""
midpoints_uranian
=================

MIDPOINT TREES — the Hamburg School / Uranian core method, applied as a synastry
question to a couple whose relationship ENDED, to separate a NATURAL ending
(a partner died) from an ARTIFICIAL one (divorce / annulment / separation).

Doctrine in one paragraph
-------------------------
Witte's Hamburg School (and Ebertin's `Combination of Stellar Influences`, which
is the same technique in German-language dress) holds that the meaningful unit of
a chart is not the planet but the MIDPOINT: the half-sum (p+q)/2 of two bodies.
A midpoint is "occupied" when a third body sits on it, and the resulting
three-body statement is read as a sentence (`Sun/Moon = Saturn` -> "separation
from the partner, a bond under privation"). Because a half-sum is only defined up
to 180 degrees, and because Witte read charts on a rotating DIAL, the technique
never asks for a plain conjunction: it asks whether the body falls on the midpoint
axis modulo the dial. The 90-degree dial folds conjunction, opposition and square
onto one point; the 45-degree dial additionally folds in semisquare and
sesquiquadrate — the eight "hard" aspects Witte considered the only real ones.

The synastry form used here: take every pairwise midpoint of partner A's 10
classical bodies (C(10,2) = 45 midpoints, the "midpoint tree") and ask how closely
each of partner B's 10 bodies sits on each of them, on each dial. Then the same
in the other direction, and pool — the doctrine has no notion of which partner is
listed first, so every statistic here is symmetric in (a, b) by construction.

What each group of features encodes
-----------------------------------
A. TREE OCCUPANCY (global).  How densely does each partner's body-set fall on the
   other's whole 45-midpoint tree?  Emitted on four dials:
     360 = conjunction to the DIRECT (near) midpoint only — the one place where
           the mod-360 midpoint says something the mod-180 one cannot;
     180 = conjunction OR opposition (the classic "midpoint axis");
      90 = + square (the 90-degree dial);
      45 = + semisquare / sesquiquadrate (the 45-degree dial).
   Four statistics per dial: a smooth triangular-kernel mean (the spec's "orb
   membership, not a hard cutoff"), the fraction of pairs occupied within 1.5
   degrees, the raw count within 1.5 degrees, and the single tightest contact.

B. PER-RECEIVER TREES.  The same tree-occupancy question narrowed to one
   RECEIVING body (Sun, Moon, Venus, Mars, Saturn): how much of the partner's
   tree does *this* body of mine light up?  Uranian practice reads a planet's
   "tree" exactly this way.

C. THE NAMED MARRIAGE AXES.  The four axes the brief names — Venus/Mars,
   Sun/Moon, Venus/Saturn, Moon/Venus — measured against the other partner's Sun
   and Moon, on the 90 and 45 dials, as both `max` (either direction carries it)
   and `mutual` (BOTH directions carry it; NaN if either side is unknown, because
   mutuality cannot be asserted from one side). Plus six ENDING axes, which is
   where the natural-vs-artificial question actually lives in Ebertin: Mars/Saturn
   (his literal "death axis"), Saturn/Pluto, Sun/Saturn, Moon/Saturn (privation,
   bereavement, the ending imposed from outside) against Venus/Uranus (sudden
   rupture) and Venus/Neptune (deception, dissolution) — the endings a couple
   chooses.

D. NATAL SELF-TREES.  One partner's own core axis occupied by their own Saturn,
   Uranus, Neptune or Pluto — Ebertin's separation signatures read inside a single
   chart (`Venus/Mars = Saturn` is his "inhibition, separation in love"). Combined
   across the two partners with a NaN-tolerant max, so it reads "at least one
   partner carries this signature" and stays order-free.

Correctness notes
-----------------
* `df.start` is ignored entirely: it is the constant string "0000-00-00" in this
  dataset and carries no information. Nothing here is derived from it.
* All four date shapes ('YYYY-MM-DD', 'YYYY-00-00', '0000-MM-DD', '0000-00-00')
  are parsed defensively. Only ONE feature is derived from the dates at all — a
  coverage count of how many partners have a full Y+M+D date — and a date whose
  YEAR is missing ('0000-MM-DD') counts as NOT full, because no ephemeris position
  can be resolved from a month and day without a year. No date is ever cast to an
  int and used as an index.
* A dial distance is computed from a signed offset that is NaN whenever either
  operand is NaN, so an unknown body silently drops out of every count instead of
  contributing a fabricated zero. Where a statistic has NO valid input at all the
  result is NaN, never 0 — "nothing occupied" and "nothing known" are different
  facts and are kept different.
* On the 180 / 90 / 45 dials the direct (mod-360) and the mod-180 midpoint give
  IDENTICAL distances, because the two representatives differ by exactly 180 and
  every one of those dials divides 180. Both are computed, the equivalence is
  asserted in the self-test, and the mod-360 form is used only for the 360 dial,
  which is the sole place it differs.
* Pure function of (df, Z): no file reads, no network, no randomness, no globals.

Coverage confound — READ THIS BEFORE MODELLING
----------------------------------------------
The RAW COUNT features (`mpu_tree_d*_hit_count`) are requested by the brief and
are computed correctly, but they scale with how many (midpoint, body) pairs were
computable at all, and that in turn is decided by whether the two birth dates
carry day precision. Measured on the real training half:

    corr(mpu_tree_d90_hit_count, mpu_tree_valid_frac) = +0.89
    corr(mpu_tree_d45_hit_count, mpu_tree_valid_frac) = +0.94
    corr(mpu_tree_d90_hit_frac,  mpu_tree_valid_frac) = -0.005
    corr(mpu_tree_d90_kern_mean, mpu_tree_valid_frac) = -0.005

and their in-sample univariate AUC (~0.556) is indistinguishable from the AUC of
the bare coverage columns themselves (~0.555). So a model handed the counts alone
will learn "this couple has precisely recorded birth dates" — a real property of
the record, but NOT the midpoint doctrine. The DENSITY forms (`hit_frac`,
`kern_mean`) are the doctrine-pure ones: they are normalised by the number of
valid pairs and are uncorrelated with coverage.

The `max` statistics sit in between (r = +0.48 to +0.72): a maximum taken over
more valid entries is mechanically larger. `mpu_tree_valid_frac` and
`mpu_day_precision_count` are emitted deliberately so this confound can be
CONTROLLED rather than hidden — keep at least one of them in any model that also
uses the counts or the maxima.
"""

import itertools
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Doctrine constants
# ---------------------------------------------------------------------------

# The 10 classical bodies Witte and Ebertin build midpoint trees from.
# The node pair, Chiron and Lilith are deliberately excluded (not classical
# midpoint-tree material); Ascendant and MC are ALWAYS NaN here (no birth time).
BODIES10 = ['sun', 'moon', 'mercury', 'venus', 'mars',
            'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']

# C(10,2) = 45 pairwise midpoints — the full tree.
PAIRS = list(itertools.combinations(range(len(BODIES10)), 2))

# Dials. 360 = direct midpoint conjunction only; 180 = midpoint axis
# (conj|opp); 90 = the 90-degree dial (+square); 45 = the 45-degree dial
# (+semisquare, sesquiquadrate) — the eight hard aspects.
DIALS_GLOBAL = [360, 180, 90, 45]
DIALS_SYN = [90, 45]

# Kernel orbs, tightening as the dial folds more aspects onto one point.
# Uranian practice is tight; 1 degree on the 45 dial is already generous
# relative to its 22.5-degree half-width.
ORB = {360: 3.0, 180: 3.0, 90: 2.0, 45: 1.5}

# The brief's hard "occupied" threshold for the counts.
HIT_ORB = 1.5

# C. The four marriage axes named in the brief.
CORE_AXES = [('venus', 'mars'),     # the union / desire axis
             ('sun', 'moon'),       # Ebertin's marriage axis proper
             ('venus', 'saturn'),   # love under inhibition -> separation
             ('moon', 'venus')]     # affection, the domestic bond

# C. Axes about how a bond ENDS — the natural/artificial question itself.
END_AXES = [('mars', 'saturn'),     # Ebertin's "death axis"
            ('saturn', 'pluto'),    # hard, irreversible ending
            ('venus', 'uranus'),    # sudden rupture (a chosen ending)
            ('venus', 'neptune'),   # dissolution, deception
            ('sun', 'saturn'),      # bereavement, the partner lost
            ('moon', 'saturn')]     # privation, the bond under loss

# C. The receiving bodies: the brief asks for the other partner's Sun and Moon.
SYN_RECEIVERS = ['sun', 'moon']

# B. Bodies whose own tree-occupancy we summarise.
TREE_RECEIVERS = ['sun', 'moon', 'venus', 'mars', 'saturn']

# D. Natal disruptors read onto one's own core axes.
NATAL_DISRUPTORS = ['saturn', 'uranus', 'neptune', 'pluto']


# ---------------------------------------------------------------------------
# Small numeric helpers
# ---------------------------------------------------------------------------

def _dial_dist(off, dial):
    """Fold a signed angular offset onto `dial` and return the distance to the
    nearest dial point, in [0, dial/2]. NaN in -> NaN out (an unknown body must
    never look like an exact hit)."""
    d = np.mod(off, float(dial))
    return np.minimum(d, float(dial) - d)


def _memb(off, dial, orb):
    """Smooth TRIANGULAR orb membership: 1.0 exact, falling linearly to 0.0 at
    `orb`, and 0.0 beyond. NaN is preserved as NaN so that fmax/minimum can tell
    'unoccupied' from 'unknown'."""
    d = _dial_dist(off, dial)
    m = 1.0 - d / float(orb)
    return np.where(np.isnan(d), np.nan, np.maximum(m, 0.0))


def _mid360(p, q):
    """The DIRECT (near) midpoint on the full circle: the half-sum lying on the
    SHORTER arc between p and q. Taking a naive (p+q)/2 would pick an arbitrary
    one of the two half-sums depending on how the longitudes happen to wrap."""
    delta = np.mod(q - p + 180.0, 360.0) - 180.0   # signed separation in (-180, 180]
    return np.mod(p + 0.5 * delta, 360.0)


def _mid180(p, q):
    """The midpoint AXIS, mod 180 — direct and indirect midpoints collapse here.
    Equal to `_mid360(p, q) % 180` for every input (asserted in the self-test)."""
    return np.mod(0.5 * (p + q), 180.0)


def _tree(theta):
    """All 45 pairwise DIRECT midpoints of one partner. theta: (n, 10) ->
    (n, 45), in the fixed `PAIRS` order."""
    n = theta.shape[0]
    out = np.full((n, len(PAIRS)), np.nan, dtype=np.float32)
    for k, (i, j) in enumerate(PAIRS):
        out[:, k] = _mid360(theta[:, i], theta[:, j])
    return out


def _finalise(nvalid, ksum, hits, mx):
    """Turn accumulated sums into per-row statistics. Rows with NO valid pair at
    all become NaN across the board — a row where nothing is known must not be
    reported as a row where nothing was occupied."""
    nv = nvalid.astype(np.float64)
    den = np.where(nv > 0, nv, np.nan)
    ok = nv > 0
    return (ksum / den,                                   # kernel mean
            hits / den,                                   # occupied fraction
            np.where(ok, hits, np.nan),                   # occupied count
            np.where(ok, mx, np.nan))                     # tightest contact


def _body_cols(theta_full, bodies_index, n):
    """Pull the 10 classical bodies out of the (n, 16) theta array in BODIES10
    order. A body absent from Z['bodies'] yields an all-NaN column rather than
    an exception or a wrong column."""
    out = np.full((n, len(BODIES10)), np.nan, dtype=np.float32)
    if theta_full is None:
        return out
    rows = min(n, theta_full.shape[0])
    for k, name in enumerate(BODIES10):
        j = bodies_index.get(name)
        if j is not None and j < theta_full.shape[1]:
            out[:rows, k] = theta_full[:rows, j]
    return out


def _date_full_mask(col, n):
    """True where a date string carries a usable YEAR *and* month *and* day.

    Handles all four shapes without ever fabricating a value:
      'YYYY-MM-DD' -> True
      'YYYY-00-00' -> False (year only)
      'YYYY-MM-00' -> False (no day)
      '0000-MM-DD' -> False (NO YEAR: a month/day pair fixes no ephemeris instant)
      '0000-00-00' -> False (absent)
    Anything malformed, missing or short also yields False. Nothing parsed here
    is ever cast to an int or used to index a table."""
    if col is None:
        return np.zeros(n, dtype=bool)
    s = pd.Series(col).astype(str)
    long_enough = s.str.len() >= 10
    y = pd.to_numeric(s.str.slice(0, 4), errors='coerce')
    m = pd.to_numeric(s.str.slice(5, 7), errors='coerce')
    d = pd.to_numeric(s.str.slice(8, 10), errors='coerce')
    # NaN compares False under numpy semantics, so malformed parts drop out.
    full = long_enough.to_numpy() & (y > 0).to_numpy() & (m > 0).to_numpy() & (d > 0).to_numpy()
    out = np.zeros(n, dtype=bool)
    out[:min(n, full.shape[0])] = full[:min(n, full.shape[0])]
    return out


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def build(df, Z, half):
    """See module docstring. Returns (X float32 (len(df), 97), names list)."""
    n = len(df)

    # --- resolve Z -------------------------------------------------------
    try:
        bodies = [str(b) for b in list(Z['bodies'])]
    except Exception:
        bodies = []
    bidx = {b: i for i, b in enumerate(bodies)}

    def _get(key):
        try:
            arr = np.asarray(Z[key], dtype=np.float64)
        except Exception:
            return None
        return arr if arr.ndim == 2 else None

    th_a = _body_cols(_get('theta_a_%s' % half), bidx, n)   # (n, 10)
    th_b = _body_cols(_get('theta_b_%s' % half), bidx, n)

    tree_a = _tree(th_a)                                    # (n, 45)
    tree_b = _tree(th_b)

    # Index of each classical body inside BODIES10, for the named axes.
    b10 = {name: k for k, name in enumerate(BODIES10)}

    names = []
    cols = []

    # =====================================================================
    # A. GLOBAL TREE OCCUPANCY — each partner's 10 bodies on the other's 45
    #    midpoints, both directions POOLED so the statistic is symmetric.
    # =====================================================================
    nvalid = np.zeros(n, dtype=np.int64)
    acc = {dial: {'ksum': np.zeros(n, dtype=np.float64),
                  'hits': np.zeros(n, dtype=np.float64),
                  'max': np.zeros(n, dtype=np.float64)}
           for dial in DIALS_GLOBAL}

    for tree, planets in ((tree_a, th_b), (tree_b, th_a)):
        # off[r, k*10 + i] = (other partner's body i) - (this partner's midpoint k)
        # explicit width: reshape(n, -1) is ambiguous when n == 0
        off = (planets[:, None, :] - tree[:, :, None]).reshape(
            n, len(PAIRS) * len(BODIES10)).astype(np.float32)
        valid = ~np.isnan(off)
        nvalid += valid.sum(axis=1)
        for dial in DIALS_GLOBAL:
            d = _dial_dist(off, dial)
            memb = 1.0 - d / ORB[dial]
            np.maximum(memb, 0.0, out=memb)
            memb[~valid] = 0.0                    # unknown contributes nothing
            a = acc[dial]
            a['ksum'] += memb.sum(axis=1, dtype=np.float64)
            np.maximum(a['max'], memb.max(axis=1), out=a['max'])
            a['hits'] += (d <= HIT_ORB).sum(axis=1)   # NaN <= x is False
            del d, memb
        del off, valid

    for dial in DIALS_GLOBAL:
        km, hf, hc, mx = _finalise(nvalid, acc[dial]['ksum'], acc[dial]['hits'], acc[dial]['max'])
        # Density of the midpoint tree lit up by the partner, on this dial.
        cols += [km, hf, hc, mx]
        names += ['mpu_tree_d%d_kern_mean' % dial,
                  'mpu_tree_d%d_hit_frac' % dial,
                  'mpu_tree_d%d_hit_count' % dial,
                  'mpu_tree_d%d_max' % dial]

    # How much of the 900 (midpoint, body) cross-pairs was computable at all —
    # a COVERAGE figure, not a doctrine figure. Kept so the model can read the
    # NaN structure instead of mistaking sparse charts for empty trees.
    total_pairs = 2.0 * len(PAIRS) * len(BODIES10)
    cols.append(nvalid.astype(np.float64) / total_pairs)
    names.append('mpu_tree_valid_frac')

    # =====================================================================
    # B. PER-RECEIVER TREES — one body of mine against the whole tree of yours,
    #    pooled over both directions.
    # =====================================================================
    for rname in TREE_RECEIVERS:
        ri = b10[rname]
        for dial in DIALS_SYN:
            ks = np.zeros(n, dtype=np.float64)
            nv = np.zeros(n, dtype=np.int64)
            mx = np.zeros(n, dtype=np.float64)
            for tree, planets in ((tree_a, th_b), (tree_b, th_a)):
                off = planets[:, ri][:, None] - tree          # (n, 45)
                valid = ~np.isnan(off)
                nv += valid.sum(axis=1)
                memb = _memb(off, dial, ORB[dial])
                memb = np.where(valid, memb, 0.0)
                ks += memb.sum(axis=1, dtype=np.float64)
                np.maximum(mx, memb.max(axis=1), out=mx)
            den = np.where(nv > 0, nv.astype(np.float64), np.nan)
            cols.append(ks / den)
            cols.append(np.where(nv > 0, mx, np.nan))
            names += ['mpu_recv_%s_d%d_kern_mean' % (rname, dial),
                      'mpu_recv_%s_d%d_max' % (rname, dial)]

    # =====================================================================
    # C. THE NAMED AXES — one partner's marriage/ending axis against the
    #    other's Sun and Moon.
    #    `max`    : np.fmax  -> ignores a NaN side, so it reads "either
    #               direction carries this contact".
    #    `mutual` : np.minimum -> PROPAGATES NaN, so mutuality is only claimed
    #               when both directions are actually known.
    # =====================================================================
    def _axis_pair_memb(pname, qname, rname, dial):
        pi, qi, ri = b10[pname], b10[qname], b10[rname]
        m_a = _mid360(th_a[:, pi], th_a[:, qi])
        m_b = _mid360(th_b[:, pi], th_b[:, qi])
        d1 = _memb(th_b[:, ri] - m_a, dial, ORB[dial])   # B's receiver on A's axis
        d2 = _memb(th_a[:, ri] - m_b, dial, ORB[dial])   # A's receiver on B's axis
        return d1, d2

    for (pn, qn) in CORE_AXES:
        for rn in SYN_RECEIVERS:
            for dial in DIALS_SYN:
                d1, d2 = _axis_pair_memb(pn, qn, rn, dial)
                cols.append(np.fmax(d1, d2))
                cols.append(np.minimum(d1, d2))
                names += ['mpu_ax_%s_%s__%s_d%d_max' % (pn, qn, rn, dial),
                          'mpu_ax_%s_%s__%s_d%d_mutual' % (pn, qn, rn, dial)]

    for (pn, qn) in END_AXES:
        for rn in SYN_RECEIVERS:
            d1, d2 = _axis_pair_memb(pn, qn, rn, 45)
            cols.append(np.fmax(d1, d2))
            names.append('mpu_endax_%s_%s__%s_d45_max' % (pn, qn, rn))

    # =====================================================================
    # D. NATAL SELF-TREES — a partner's own core axis occupied by their own
    #    Saturn/Uranus/Neptune/Pluto. Combined across partners with fmax:
    #    symmetric in (a, b), and NaN only when NEITHER partner is computable.
    #    A disruptor that is itself a member of the axis is SKIPPED: the
    #    "distance" would just be half the axis's own span, which is a
    #    degenerate identity, not a midpoint-tree contact.
    # =====================================================================
    for (pn, qn) in CORE_AXES:
        pi, qi = b10[pn], b10[qn]
        m_a = _mid360(th_a[:, pi], th_a[:, qi])
        m_b = _mid360(th_b[:, pi], th_b[:, qi])
        for xn in NATAL_DISRUPTORS:
            if xn == pn or xn == qn:
                continue
            xi = b10[xn]
            e1 = _memb(th_a[:, xi] - m_a, 45, ORB[45])
            e2 = _memb(th_b[:, xi] - m_b, 45, ORB[45])
            cols.append(np.fmax(e1, e2))
            names.append('mpu_natal_%s_%s__%s_d45_max' % (pn, qn, xn))

    # =====================================================================
    # Coverage from the DATES themselves (the only date-derived column):
    # how many of the two partners have a full Y+M+D birth date, which is what
    # decides whether the Moon/Mercury/Venus/Mars half of every tree exists.
    # Order-free (a sum over the two partners).
    # =====================================================================
    full_a = _date_full_mask(df['dob_a'] if 'dob_a' in df else None, n)
    full_b = _date_full_mask(df['dob_b'] if 'dob_b' in df else None, n)
    cols.append(full_a.astype(np.float64) + full_b.astype(np.float64))
    names.append('mpu_day_precision_count')

    X = np.column_stack(cols).astype(np.float32) if cols else np.zeros((n, 0), np.float32)
    # Guarantee the contract's row count even if Z were ragged.
    if X.shape[0] != n:
        fixed = np.full((n, X.shape[1]), np.nan, dtype=np.float32)
        r = min(n, X.shape[0])
        fixed[:r] = X[:r]
        X = fixed
    assert X.shape[1] == len(names), (X.shape, len(names))
    return X, names
