"""
arabic_parts.py — ARABIC PARTS / LOTS (Hellenistic-Arabic doctrine of derived points).

DOCTRINE
--------
A "lot" (Greek kleros, Arabic sahm, English "part") is not a body: it is a point CONSTRUCTED by
carrying an arc from one place to another.  The canonical form is

        Lot = A + B - C      (mod 360)

read as: "take the arc from C to B, and project it forward from A".  Classically A is the
Ascendant, which is why the famous lots (Fortune = Asc + Moon - Sun) need a birth TIME.

We have no birth time.  Z['ascendant'] and Z['medium_coeli'] are NaN in every row, by construction.
So the classic Lot of Fortune is simply unavailable and we do not fake it.  Instead this module
builds the TIME-INDEPENDENT lots, of which there are two honest kinds:

  (1) ASC-CANCELLING REDUCTIONS.  Several classical lots are defined FROM another lot, and when you
      substitute the definition the Ascendant cancels exactly.  Example, the Lot of Eros by day:
            Eros(day)   = Asc + Venus - Spirit
            Spirit(day) = Asc + Sun   - Moon
        =>  Eros(day)   = Asc + Venus - (Asc + Sun - Moon) = Moon + Venus - Sun
      This is not an approximation.  It is the classical lot, algebraically Asc-free.  The same
      cancellation gives Necessity, Courage, Victory and Nemesis in their sect-mirrored forms, all
      of the shape  X + Moon - Sun.  That family is the doctrinal core of this module.

  (2) SUN-FOR-ASCENDANT SUBSTITUTION.  Paulus' Lot of Marriage is Asc + Saturn - Venus (men) /
      Asc + Venus - Saturn (women).  The Ascendant does not cancel there.  The traditional
      substitute for the Ascendant when the hour is unknown is the SECT LIGHT, i.e. the Sun (the
      "ascendant of the day"), which is exactly the requested "Saturn + Venus - Sun" shape.  These
      are flagged as substitutions in their names (marriage_m / marriage_f / marriage_sym), not
      passed off as the time-accurate lot.

  (3) THE EXHAUSTIVE FAMILY.  Every A + B - C over the six lot-planets
      {sun, moon, venus, mars, jupiter, saturn} with A, B, C all distinct (A,B unordered, since
      A + B is symmetric) = C(6,2) x 4 = 60 lots.  Reported as aggregate statistics rather than 60
      raw columns, so the doctrine is represented without drowning the model.

WHAT IS ENCODED, AND WHY THAT WAY
---------------------------------
For each lot we compute it in BOTH partners' charts and encode, exactly as the doctrine reads a lot:
  * its SIGN            -> whether the two partners' matching lots fall in the same sign, and the
                           whole-sign distance between them.  Whole-sign is the Hellenistic aspect
                           doctrine proper (signs aspect signs), and it is far more robust to a
                           year-only birth date than a degree orb is.
  * its ASPECT-ORB MEMBERSHIP to the seven classical planets, in the partner's OWN chart and
                           CROSS-partner (partner1's lot against partner2's planets) — a lot is
                           held to be "activated" when a planet aspects it.
  * the ANGULAR DISTANCE between the two partners' MATCHING lots (the synastry of the lots).

ASPECTS are the five Ptolemaic ones only — 0, 60, 90, 120, 180.  30 and 150 are NOT aspects in this
tradition, they are AVERSION (the signs cannot see each other), and aversion is encoded as its own
feature rather than smuggled in as a weak aspect.

ORDER-FREENESS
--------------
Nothing here can learn column order.  Every cross-partner quantity is symmetric in (a, b):
separations and whole-sign distances are |a - b| based; activation rates are summed over both
directions; the Venus/Saturn arcs are reduced to max/min/|diff|/sum.  The sex-coded Paulus lots
(men's / women's) are computed for BOTH partners and only ever compared like-for-like, so no
feature asserts which partner is which — consistent with the genderless standing rule.

NaN POLICY
----------
NaN is a correct answer and is never filled.  Sun/Moon/Mercury/Venus/Mars resolve only from a
day-precise birth date, so every lot built on them is NaN for a year-only partner (~13% of rows) —
that is the honest result, not a defect.  No NaN is ever cast to an int or used to index a lookup
table: sign indices are produced by np.floor, which propagates NaN, and every comparison that would
collapse NaN to False is re-masked back to NaN explicitly.

DATE SHAPES
-----------
df.dob_a / df.dob_b arrive in four shapes and all four are handled: 'YYYY-MM-DD' (full),
'YYYY-00-00' (year only -> slow bodies only), '0000-MM-DD' (year UNKNOWN -> nothing resolves at
all) and '0000-00-00' (absent).  df.start is always '0000-00-00' in this dataset and is deliberately
never read.

A FIFTH shape, 'YYYY-MM-00' (month, no day), is present in the live data — 291 partner entries
(126 in dob_a, 165 in dob_b) across the 20,955 training rows —
and it matters, because Z supplies a SUN longitude for every one of them while correctly leaving the
other fast bodies NaN.  A month pins the Sun only to about +/-15 degrees, which is most of a sign, so that
position cannot support either of this module's two readings: which SIGN the lot falls in, and
whether it holds a 3-degree orb.  This module therefore treats month-only as day-unknown and
discards the assumed Sun.  That is the whole reason the precision guard exists rather than trusting
Z: the guard blanks ~6,300 cells on the real training half, every one of them descended from a Sun
that was inferred from a month rather than recorded.

The parsed precision is not merely reported — it is ENFORCED onto the charts before any lot is
built (_enforce_precision), so a fabricated position could not reach a feature even if Z supplied
one.  No feature COUNTS that precision, though: a date-precision census encodes no doctrine, and it
is a proxy for era and notability rather than for astrology.  Such a column measured d = +0.28
against the label here — far and away the strongest thing this module could emit — which is exactly
why it must not sit inside a doctrine module, where it would be mistaken for lot signal.  It
belongs in a plain feature module, once.

Imports are limited to numpy / pandas / itertools.  build() is a pure function: no file reads, no
network, no randomness, no global mutation.
"""

import itertools

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------------------------
# Doctrine constants
# --------------------------------------------------------------------------------------------

# The five Ptolemaic aspects.  Conjunction, sextile, square, trine, opposition.
ASPECTS = (0.0, 60.0, 90.0, 120.0, 180.0)

# A lot is a computed POINT, not a body, so tradition gives it a tight orb.  3 degrees.
ORB_POINT = 3.0

# The six planets the lots are built from (the brief's set: no Mercury in the combinatorial family).
LOT_PLANETS = ("sun", "moon", "venus", "mars", "jupiter", "saturn")

# The seven classical planets, used as the targets a lot can be aspected BY.
SEVEN = ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn")

# Points fetched in addition to the seven.  The true node (Caput Draconis / Rahu) is a legitimate
# ingredient of the Arabic lots and, unlike the seven, it resolves from a YEAR ALONE.
EXTRA_POINTS = ("true_node",)

# Year-resolvable lots.  Every lot over the six lot-planets needs at least one of
# Sun/Moon/Venus/Mars, so for a year-only birth date the whole combinatorial family above is NaN —
# which would leave roughly a quarter of pairs with no lot doctrine at all.  Jupiter, Saturn and the
# true node are the classical lot ingredients that DO resolve from a year, so these three lots (the
# three ways of choosing which of the trio is the subtracted point) carry the doctrine into the
# year-only rows.  They are not a fallback estimate of the fast lots: they are different lots,
# named as such, and they are NaN in their own right when a birth year is unknown.
SLOW_LOTS = (
    ("jupsat_node", "jupiter", "saturn", "true_node"),
    ("jupnode_sat", "jupiter", "true_node", "saturn"),
    ("satnode_jup", "saturn", "true_node", "jupiter"),
)

# The named, time-free lots.  (name, A, B, C)  ->  lot = A + B - C (mod 360).
#
# The first five are exact Asc-CANCELLING reductions (kind 1 above): the Ascendant divides out of
# the classical definition, so these ARE the classical lots, not stand-ins.  All share the shape
# X + Moon - Sun, which is what makes the cancellation work.
#
# The last four substitute the Sun (the sect light) for the Ascendant (kind 2 above) and say so.
NAMED_LOTS = (
    # Eros: Asc + Venus - Spirit(day), Spirit(day) = Asc + Sun - Moon.  Desire, attraction, what is
    # wanted from the union.  The lot most directly about erotic bond, hence first.
    ("eros", "moon", "venus", "sun"),
    # Necessity: Asc + Mercury - Fortune(night), Fortune(night) = Asc + Sun - Moon.  Constraint,
    # compulsion, what is forced rather than chosen — the classical counterweight to Eros.
    ("necessity", "moon", "mercury", "sun"),
    # Courage: Asc + Mars - Fortune(night).  Boldness, conflict, the capacity for open rupture.
    ("courage", "moon", "mars", "sun"),
    # Victory: Asc + Jupiter - Spirit(day).  Success, endurance, what carries through.
    ("victory", "moon", "jupiter", "sun"),
    # Nemesis: Asc + Saturn - Fortune(night).  Retribution, undoing, the hidden ending.  In the
    # tradition this is THE lot of how a thing comes apart, so it is the most on-topic lot here.
    ("nemesis", "moon", "saturn", "sun"),
    # Paulus' Lot of Marriage for men: Asc + Saturn - Venus, Sun substituted for Asc.
    ("marriage_m", "sun", "saturn", "venus"),
    # Paulus' Lot of Marriage for women: Asc + Venus - Saturn, Sun substituted for Asc.
    ("marriage_f", "sun", "venus", "saturn"),
    # The order-free marriage lot the brief asks for: Venus + Saturn - Sun.  Symmetric in the
    # Venus/Saturn pair, so unlike marriage_m/marriage_f it encodes no sex at all.
    ("marriage_sym", "venus", "saturn", "sun"),
    # Lot of Children: Asc + Jupiter - Saturn, Sun substituted for Asc.  Marriage-adjacent: the
    # tradition reads it for issue of the union.
    ("children", "sun", "jupiter", "saturn"),
)

# Extra members of the A + B - Sun family (Sun as substitute Ascendant) that the named list above
# does not already cover.  Pairs are drawn from {moon, venus, mars, jupiter, saturn}; the five
# already-named combinations (moon+venus, moon+mars, moon+jupiter, moon+saturn, venus+saturn) are
# excluded so no column is duplicated.
_SUNLOT_COVERED = {
    frozenset(("moon", "venus")),
    frozenset(("moon", "mars")),
    frozenset(("moon", "jupiter")),
    frozenset(("moon", "saturn")),
    frozenset(("venus", "saturn")),
}
SUN_LOTS = tuple(
    (a, b)
    for a, b in itertools.combinations(("moon", "venus", "mars", "jupiter", "saturn"), 2)
    if frozenset((a, b)) not in _SUNLOT_COVERED
)

# The exhaustive family: A + B - C over LOT_PLANETS, all three distinct, (A,B) unordered.
FAMILY = tuple(
    (a, b, c)
    for a, b in itertools.combinations(LOT_PLANETS, 2)
    for c in LOT_PLANETS
    if c != a and c != b
)


# --------------------------------------------------------------------------------------------
# NaN-safe primitives.  Every one of these propagates NaN rather than inventing a value, and none
# of them casts a possibly-NaN float to an int.
# --------------------------------------------------------------------------------------------


def _angsep(x, y):
    """Angular separation in [0, 180].  NaN in -> NaN out."""
    d = np.mod(np.abs(x - y), 360.0)
    return np.minimum(d, 360.0 - d)


def _orb_to_aspect(sep):
    """Degrees from `sep` to the nearest Ptolemaic aspect.  0.0 means the aspect is exact."""
    stack = np.stack([np.abs(sep - a) for a in ASPECTS], axis=-1)
    return np.min(stack, axis=-1)


def _sign_index(lon):
    """Zodiac sign as a float 0..11.  np.floor propagates NaN, so no NaN ever indexes anything."""
    return np.floor(np.mod(lon, 360.0) / 30.0)


def _sign_dist(la, lb):
    """Whole-sign distance 0..6 between two longitudes (0 = same sign, 6 = opposite signs)."""
    d = np.abs(_sign_index(la) - _sign_index(lb))
    return np.minimum(d, 12.0 - d)


def _mask_bool(cond, ref):
    """Turn a boolean array into 1.0/0.0, but restore NaN wherever `ref` is NaN.

    Needed because `nan == nan` is False, which would silently report 'not the same sign' for a
    partner whose chart does not exist.  That is exactly the fabricated value the brief forbids.
    """
    out = np.where(cond, 1.0, 0.0)
    return np.where(np.isnan(ref), np.nan, out)


def _nan_mean(a, axis=1):
    """Mean ignoring NaN, without np.nanmean's all-NaN RuntimeWarning."""
    ok = np.isfinite(a)
    cnt = ok.sum(axis=axis)
    tot = np.where(ok, a, 0.0).sum(axis=axis)
    return np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)


def _nan_std(a, axis=1):
    """Population std ignoring NaN, warning-free."""
    m = _nan_mean(a, axis=axis)
    ok = np.isfinite(a)
    cnt = ok.sum(axis=axis)
    dev = np.where(ok, (a - np.expand_dims(m, axis)) ** 2, 0.0).sum(axis=axis)
    return np.where(cnt > 0, np.sqrt(dev / np.maximum(cnt, 1)), np.nan)


def _nan_min(a, axis=1):
    """Min ignoring NaN, warning-free."""
    ok = np.isfinite(a)
    cnt = ok.sum(axis=axis)
    filled = np.where(ok, a, np.inf)
    mn = filled.min(axis=axis)
    return np.where(cnt > 0, mn, np.nan)


def _nan_frac(cond, valid, axis=1):
    """Fraction of the VALID entries satisfying `cond`.  NaN when nothing is valid.

    Using a fraction rather than a raw count keeps the denominator stable when a partner's fast
    bodies are missing, so the feature means the same thing for a year-only row as for a full one.
    """
    cnt = valid.sum(axis=axis)
    hit = np.where(valid & cond, 1.0, 0.0).sum(axis=axis)
    return np.where(cnt > 0, hit / np.maximum(cnt, 1), np.nan)


# --------------------------------------------------------------------------------------------
# Date parsing.  Used ONLY to report how much precision each row had; never to synthesise a
# position.  df.start is never read — it is '0000-00-00' in every row of this dataset.
# --------------------------------------------------------------------------------------------


def _date_precision(df, col):
    """Return (has_year, has_day) boolean arrays for a date column.

    Handles all four documented shapes plus 'YYYY-MM-00' and any unparseable junk:
      'YYYY-MM-DD' -> (True,  True)      full precision
      'YYYY-00-00' -> (True,  False)     year only; slow bodies resolve, fast ones do not
      'YYYY-MM-00' -> (True,  False)     month only; deliberately NOT day-precise (see module doc:
                                         Z hands these an assumed Sun, good to only +/-15 degrees)
      '0000-MM-DD' -> (False, True)      year UNKNOWN; nothing resolves, ephemeris is meaningless
      '0000-00-00' -> (False, False)     absent
    A zero component means 'not recorded', per the dataset's convention.  pd.to_numeric with
    errors='coerce' yields NaN for junk, and NaN > 0 is False, so junk degrades to 'unknown'
    instead of raising or inventing.
    """
    n = len(df)
    if col not in df.columns:
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
    s = df[col].astype("string").fillna("").str.strip()
    parts = s.str.extract(r"^(\d+)-(\d+)-(\d+)$")
    y = pd.to_numeric(parts[0], errors="coerce").to_numpy(dtype=float)
    m = pd.to_numeric(parts[1], errors="coerce").to_numpy(dtype=float)
    d = pd.to_numeric(parts[2], errors="coerce").to_numpy(dtype=float)
    has_year = y > 0
    has_day = has_year & (m > 0) & (d > 0)
    return has_year, has_day


# --------------------------------------------------------------------------------------------
# Chart access
# --------------------------------------------------------------------------------------------


# Bodies whose position needs a DAY-precise birth date.  The rest resolve from a year alone.
FAST_BODIES = ("sun", "moon", "mercury", "venus", "mars")


def _enforce_precision(cols, has_year, has_day):
    """Blank out positions the recorded date cannot support.  Rewrites the local dict only."""
    for name, v in cols.items():
        v = v.copy()
        v[~has_year] = np.nan                    # no birth year -> no ephemeris of any kind
        if name in FAST_BODIES:
            v[~has_day] = np.nan                 # year only -> the fast bodies are unknowable
        cols[name] = v


def _theta(Z, slot, half, n):
    """Fetch the (n, 16) longitude matrix for a slot, or an all-NaN stand-in if it is absent."""
    key = "theta_%s_%s" % (slot, half)
    if key in Z:
        arr = np.asarray(Z[key], dtype=float)
        if arr.ndim == 2 and arr.shape[0] == n:
            return arr
    return np.full((n, 16), np.nan, dtype=float)


def _body_cols(theta, bodies_index, n):
    """Map body name -> its longitude column, NaN column when the body is not in Z['bodies'].

    Looking bodies up BY NAME rather than by hardcoded position means a reordered Z cannot silently
    turn Saturn into Mars, and a missing body costs a NaN column instead of an IndexError.
    """
    out = {}
    for name in SEVEN + EXTRA_POINTS:
        i = bodies_index.get(name)
        out[name] = theta[:, i].astype(float) if i is not None else np.full(n, np.nan)
    return out


def _lot(cols, a, b, c):
    """The lot A + B - C, mod 360.  NaN in any term propagates, which is the intended behaviour."""
    return np.mod(cols[a] + cols[b] - cols[c], 360.0)


def _activation(lot, planet_cols):
    """Rate at which the seven classical planets aspect this lot, within a 3-degree orb.

    Returned as a RATE over the planets that actually resolved, so a year-only partner (whose fast
    bodies are NaN) yields a comparable number rather than an artificially low count.  NaN when the
    lot itself is unknown or no planet resolved.
    """
    stack = np.stack([planet_cols[p] for p in SEVEN], axis=1)          # (n, 7)
    sep = _angsep(lot[:, None], stack)                                  # (n, 7)
    orb = _orb_to_aspect(sep)
    valid = np.isfinite(orb)
    rate = _nan_frac(orb <= ORB_POINT, valid, axis=1)
    return np.where(np.isnan(lot), np.nan, rate)


# --------------------------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------------------------


def build(df, Z, half):
    """Arabic Parts / Lots features.  See module docstring.  Pure function of (df, Z, half)."""
    n = len(df)

    bodies = [str(b) for b in np.asarray(Z["bodies"]).ravel().tolist()]
    bodies_index = {name: i for i, name in enumerate(bodies)}

    th_a = _theta(Z, "a", half, n)
    th_b = _theta(Z, "b", half, n)
    ca = _body_cols(th_a, bodies_index, n)
    cb = _body_cols(th_b, bodies_index, n)

    # Enforce the NaN policy from the DATES themselves rather than trusting Z to have done it.
    # Z is already NaN-correct today, but this module must never emit a lot built on a position
    # nobody recorded, so the guarantee is made here where the feature is produced: a partner with
    # no birth YEAR loses every body, and a partner with no DAY loses the fast bodies, whatever Z
    # happens to contain.  If Z were ever rebuilt with interpolated positions for a year-only date,
    # this is what would stop that fabrication reaching a feature.
    _enforce_precision(ca, *_date_precision(df, "dob_a"))
    _enforce_precision(cb, *_date_precision(df, "dob_b"))

    cols = []
    names = []

    def add(name, vec):
        cols.append(np.asarray(vec, dtype=float).reshape(n))
        names.append(name)

    # ----------------------------------------------------------------------------------------
    # GROUP 1 — the nine named time-free lots, each read as the doctrine reads a lot: where it
    # falls, and how the two partners' MATCHING lots stand to one another.  5 features per lot.
    # ----------------------------------------------------------------------------------------
    named_a = {}
    named_b = {}
    for nm, A, B, C in NAMED_LOTS:
        la = _lot(ca, A, B, C)
        lb = _lot(cb, A, B, C)
        named_a[nm] = la
        named_b[nm] = lb

        sep = _angsep(la, lb)
        # The raw synastry of the lot: how far apart the two partners' same-named lots sit.
        add("ap_%s_sep" % nm, sep)
        # Smooth conjunction(+1)/opposition(-1) contrast — lets a linear model use the axis without
        # needing a threshold, and is monotone through the square at 0.
        add("ap_%s_cos" % nm, np.cos(np.deg2rad(sep)))
        # Degrees to the nearest Ptolemaic aspect: 0 = the two lots are in exact aspect.  Continuous
        # rather than a hard orb flag, so the model chooses its own tightness.
        add("ap_%s_orb" % nm, _orb_to_aspect(sep))
        # Whole-sign distance 0..6 — the Hellenistic aspect doctrine proper, robust to a year-only
        # date in a way a degree orb is not.
        sd = _sign_dist(la, lb)
        add("ap_%s_signdist" % nm, sd)
        # Both partners' lot in the SAME sign: the strongest whole-sign statement there is.
        add("ap_%s_samesign" % nm, _mask_bool(sd == 0.0, sd))

    # ----------------------------------------------------------------------------------------
    # GROUP 2 — aspect-orb membership of each lot to the seven planets, own-chart and CROSS.
    # "own" = each partner's lot against that same partner's planets (is the lot activated at all).
    # "cross" = partner1's lot against partner2's planets, and symmetrically — the brief's
    # cross-partner reading, and the only place synastry between lot and body can appear.
    # Both are summed over the two directions, so neither can encode column order.
    # ----------------------------------------------------------------------------------------
    own_stack = []
    cross_stack = []
    for nm, A, B, C in NAMED_LOTS:
        la, lb = named_a[nm], named_b[nm]
        own = _nan_mean(np.stack([_activation(la, ca), _activation(lb, cb)], axis=1), axis=1)
        cross = _nan_mean(np.stack([_activation(la, cb), _activation(lb, ca)], axis=1), axis=1)
        add("ap_%s_act_own" % nm, own)
        add("ap_%s_act_cross" % nm, cross)
        own_stack.append(own)
        cross_stack.append(cross)

    # ----------------------------------------------------------------------------------------
    # GROUP 3 — the rest of the A + B - Sun family (Sun as substitute Ascendant), for the five
    # planet pairs the named lots do not already cover.  Two features each, the two that carried
    # the most doctrine above: the smooth aspect axis and the whole-sign distance.
    # ----------------------------------------------------------------------------------------
    for A, B in SUN_LOTS:
        nm = "%s%s" % (A[:3], B[:3])
        la = _lot(ca, A, B, "sun")
        lb = _lot(cb, A, B, "sun")
        sep = _angsep(la, lb)
        add("ap_sunlot_%s_cos" % nm, np.cos(np.deg2rad(sep)))
        add("ap_sunlot_%s_signdist" % nm, _sign_dist(la, lb))

    # ----------------------------------------------------------------------------------------
    # GROUP 4 — the exhaustive 60-lot family, A + B - C over the six lot-planets with all three
    # distinct.  Reported as AGGREGATES: sixty raw columns would swamp the module and most of them
    # restate one another, but the doctrine's claim is about the family as a whole — "the lots of
    # this pair fall together / fall in aversion" — which is exactly what an aggregate states.
    # ----------------------------------------------------------------------------------------
    fam_sep = np.empty((n, len(FAMILY)), dtype=float)
    fam_sd = np.empty((n, len(FAMILY)), dtype=float)
    fam_cross = np.empty((n, len(FAMILY)), dtype=float)
    for j, (A, B, C) in enumerate(FAMILY):
        la = _lot(ca, A, B, C)
        lb = _lot(cb, A, B, C)
        fam_sep[:, j] = _angsep(la, lb)
        fam_sd[:, j] = _sign_dist(la, lb)
        fam_cross[:, j] = _nan_mean(
            np.stack([_activation(la, cb), _activation(lb, ca)], axis=1), axis=1
        )

    fam_cos = np.cos(np.deg2rad(fam_sep))
    fam_orb = _orb_to_aspect(fam_sep)
    fam_valid = np.isfinite(fam_sep)
    sd_valid = np.isfinite(fam_sd)

    # Central tendency of the whole family's synastry: are these two people's lots broadly with or
    # broadly against one another.
    add("ap_fam_mean_cos", _nan_mean(fam_cos, axis=1))
    # Spread — a pair can average to nothing while being sharply split between conjunct and opposed.
    add("ap_fam_std_cos", _nan_std(fam_cos, axis=1))
    add("ap_fam_mean_sep", _nan_mean(fam_sep, axis=1))
    # The single tightest conjunction anywhere in the family: the doctrine's "one exact contact".
    add("ap_fam_min_sep", _nan_min(fam_sep, axis=1))
    # Fractions in the classical readings.  8 degrees is the customary orb for a conjunction of
    # points; 3 degrees is the tight orb used for a lot in aspect.
    add("ap_fam_frac_conj8", _nan_frac(fam_sep <= 8.0, fam_valid, axis=1))
    add("ap_fam_frac_opp8", _nan_frac(fam_sep >= 172.0, fam_valid, axis=1))
    add("ap_fam_frac_orb3", _nan_frac(fam_orb <= ORB_POINT, fam_valid, axis=1))
    add("ap_fam_frac_samesign", _nan_frac(fam_sd == 0.0, sd_valid, axis=1))
    # AVERSION — whole-sign distance 1 or 5, the signs that cannot see each other.  In this
    # tradition aversion is a positive statement about disconnection, not a missing aspect, so it
    # gets its own feature instead of being folded into "no aspect".
    add("ap_fam_frac_aversion", _nan_frac((fam_sd == 1.0) | (fam_sd == 5.0), sd_valid, axis=1))
    # Mean cross-partner activation across the whole family.
    add("ap_fam_mean_act_cross", _nan_mean(fam_cross, axis=1))

    # Sub-family means, split by which planet was SUBTRACTED.  The subtracted point is the one the
    # arc is measured FROM, so it is the term that most changes a lot's meaning — a family of lots
    # taken from Saturn reads quite differently from one taken from Venus.
    for p in LOT_PLANETS:
        idx = [j for j, (A, B, C) in enumerate(FAMILY) if C == p]
        add("ap_fam_mean_cos_from_%s" % p, _nan_mean(fam_cos[:, idx], axis=1))

    # Sub-family means, split by a planet PARTICIPATING in the added pair.
    for p in LOT_PLANETS:
        idx = [j for j, (A, B, C) in enumerate(FAMILY) if p in (A, B)]
        add("ap_fam_mean_cos_with_%s" % p, _nan_mean(fam_cos[:, idx], axis=1))

    # Roll-ups of the named lots' activation, so the model gets the named core as one signal too.
    add("ap_named_mean_act_own", _nan_mean(np.stack(own_stack, axis=1), axis=1))
    add("ap_named_mean_act_cross", _nan_mean(np.stack(cross_stack, axis=1), axis=1))

    # ----------------------------------------------------------------------------------------
    # GROUP 5 — the Venus-Saturn arc itself.  Every Lot of Marriage in Paulus is built by carrying
    # the Venus-Saturn arc, so the arc is the primitive underneath marriage_m / marriage_f /
    # marriage_sym and is worth stating directly: Venus is the significator of union, Saturn of
    # binding and of endings, and their arc is the tradition's marriage measure.  Reduced to
    # max/min/|diff|/sum so no feature knows which partner is which.
    # ----------------------------------------------------------------------------------------
    arc_a = _angsep(ca["venus"], ca["saturn"])
    arc_b = _angsep(cb["venus"], cb["saturn"])
    pair = np.stack([arc_a, arc_b], axis=1)
    add("ap_vs_arc_max", np.max(pair, axis=1))
    add("ap_vs_arc_min", np.min(pair, axis=1))
    add("ap_vs_arc_absdiff", np.abs(arc_a - arc_b))
    add("ap_vs_arc_sum", arc_a + arc_b)
    # Both partners carrying a tight Venus-Saturn conjunction: the doctrine's strongest single
    # statement that the marriage lot is concentrated rather than spread.
    tight = _mask_bool((arc_a <= 8.0) & (arc_b <= 8.0), arc_a + arc_b)
    add("ap_vs_both_tight", tight)
    # The two partners' Venus-Saturn arcs seen as an angle against each other (cyclic), which is how
    # a synastry of the marriage measure would be read.
    add("ap_vs_arc_cos_diff", np.cos(np.deg2rad(arc_a - arc_b)))

    # ----------------------------------------------------------------------------------------
    # GROUP 6 — the year-resolvable lots over Jupiter / Saturn / true node.  See SLOW_LOTS: these
    # are the only lots in the tradition's toolkit that survive a year-only birth date, so they are
    # the sole carrier of lot doctrine for the ~24% of pairs where at least one partner has no day.
    # ----------------------------------------------------------------------------------------
    for nm, A, B, C in SLOW_LOTS:
        la = _lot(ca, A, B, C)
        lb = _lot(cb, A, B, C)
        sep = _angsep(la, lb)
        add("ap_slow_%s_cos" % nm, np.cos(np.deg2rad(sep)))
        sd = _sign_dist(la, lb)
        add("ap_slow_%s_signdist" % nm, sd)

    if n == 0:
        X = np.zeros((0, len(names)), dtype=np.float32)
    else:
        X = np.column_stack(cols).astype(np.float32)
    return X, names
