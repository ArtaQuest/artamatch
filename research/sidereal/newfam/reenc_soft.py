"""reenc_soft — UNCERTAINTY-MARGINALISED re-encoding of the fast bodies.

THE PROBLEM THIS MODULE EXISTS TO FIX
=====================================
About a fifth of the birth dates in this dataset are recorded to the YEAR only ('YYYY-00-00'), and
a few hundred to the MONTH ('YYYY-MM-00').  For those rows Z hands back NaN for exactly the five
bodies synastry cares most about — sun, moon, mercury, venus, mars — because a body that moves half
a degree to thirteen degrees a day cannot be placed from a year.  Every other module in this family
propagates that NaN, so the doctrines that matter most end up measured on the SMALLEST sample.

Measured on this data (train half, 20,955 rows): dob_a is day-precise on 18,201 rows, month-precise
on 126 and year-only on 2,628; dob_b is 16,719 / 165 / 4,071.  So roughly one partner-slot in six is
thrown away by every fast-body feature in the project.

A year-only date is not the absence of information about Venus.  It is a DISTRIBUTION over the
circle, and that distribution is perfectly computable: the body sweeps a known path as the date
ranges over the days of that year.  This module therefore MARGINALISES instead of discarding.  Every
column here is an expectation taken over the unknown day (and, for one shape, the unknown year):

    a point-precise date  ->  the distribution is a point mass, the expectation is the point value,
                              and the column equals what a point-wise module would have emitted
    a coarse date         ->  the distribution is a real arc of the zodiac, and the column is the
                              honest average of the doctrine over that arc
    a genuinely uniform   ->  the column is the PRIOR of that doctrine, which is the correct answer
      case                    to "what is the chance of a Moon trine, given only two years?"

so the SAME columns are defined for EVERY row and nothing is thrown away.  That is the whole point.


WHAT IS RECOVERED, MEASURED (not asserted)
==========================================
Resultant length R = |E[e^{i*lambda}]| of the marginal.  R = 1 is a point, R = 0 is no information.
Sampled over years 1400..2003 with the ephemeris below:

    body      R over an unknown DAY-OF-YEAR     R over an unknown DAY-OF-MONTH
    sun       0.018  (uniform - see below)      0.989   <- confined to one ~30 deg arc
    moon      0      (uniform, exactly)         0       (uniform, exactly)
    mercury   0.047  (uniform in practice)      0.981
    venus     0.253  <- REAL, not uniform       0.987
    mars      0.560  <- STRONG                  0.996

Two of those deserve saying out loud:

  * MARS FROM A YEAR ALONE.  Geocentric Mars advances only ~191 degrees in a calendar year, so a
    year-only date confines Mars to roughly HALF the zodiac, and to a KNOWN half.  Measured span
    over a sample of years: 131 to 238 one-degree bins occupied out of 360.  That is a large,
    locatable recovery on ~16% of partner-slots that every other module writes off as NaN.
  * VENUS FROM A YEAR ALONE.  Geocentric Venus circles once a year on average, so the naive answer
    is "uniform" - but its synodic period is 584 days, so over any single year it lingers and
    retrogrades unevenly and the marginal keeps R ~ 0.25.  Real, and free.

And two where the honest answer is "nothing", which this module says plainly rather than inventing
structure:

  * THE MOON is uniform for anything coarser than a day.  At 13.176 deg/day even a single MONTH
    sweeps 395 degrees - more than the whole circle - so the phase is uniform whatever model you
    use.  The module therefore sets the Moon's coarse marginal to EXACTLY uniform (z_k = 0 for all
    k >= 1) rather than running a mean-motion model whose accumulated error would be pure aliasing
    noise dressed up as a feature.
  * THE SUN over an unknown day of the year is uniform (measured R = 0.018): a year is one full
    solar circuit.  But over an unknown day of a KNOWN MONTH the Sun is confined to a ~30 degree
    arc (R = 0.989) - one sign wide, and located - which is the single most-used symbol in all of
    astrology recovered on the ~290 month-precision dates.

THE FIFTH DATE SHAPE, '0000-MM-DD' (year unknown, month and day known)
----------------------------------------------------------------------
The Sun's TROPICAL longitude is essentially a function of the day of the year alone, so this shape
pins the Sun to about a degree of the tropical zodiac regardless of year.  Z is SIDEREAL, however,
and sidereal = tropical - ayanamsa(year), with the ayanamsa drifting ~50.3 arcsec/yr; over an
unknown span of centuries that smears the ~1 degree arc across ~10 degrees.  Rather than invent a
prior over the era, the module anchors on the ONE era fact the row itself carries: couples are
near-contemporaries, so the partner's year is used, marginalised over +/- 25 years (51 samples).
If the partner has no year either, no era fact exists anywhere in the row and the Sun is left
uniform - ignorance is reported, not filled in.  (This shape occurs 0 times in the present data on
either half; it is implemented and tested because the contract requires all five shapes.)


THE EPHEMERIS, AND WHY IT IS SAFE TO USE ONE
============================================
A marginal over an unknown day needs the body's path over that day range, which Z cannot supply
(Z has already refused to place the body).  No ephemeris may be called - so the module carries the
standard JPL "Approximate Positions of the Planets" mean elements (Standish) for Mercury, Venus,
Earth-Moon barycentre and Mars, solves Kepler two-body, and takes the geocentric ecliptic longitude
in the fixed J2000 frame.  Pure arithmetic on numpy; no I/O, no tables loaded, no randomness.

THE FRAME IS THE RISK, so it was MEASURED, not assumed.  If the module's own longitudes sat in a
different frame from Z's, a mixed pair (one partner day-precise from Z, one marginalised from the
model) would carry a constant bias in its arc and the model would learn precision, not doctrine.
Calibration against Z on all 35,485 day-precise partner-slots of both halves:

    frame:     Z = (J2000-frame geocentric longitude) - 23.8625 deg
    calendar:  PROLEPTIC GREGORIAN on every date, including pre-1582 (the historical
               Julian-before-1582 convention was tested and is WRONG here - it puts the p99
               residual at 33 deg instead of 0.01)
    clock:     12:00 UT
    residual:  sun max 0.012 deg / rms 0.003 ; mercury max 0.022 / rms 0.007 ;
               venus max 0.046 / rms 0.006 ; mars max 0.083 / rms 0.010
    the 23.8625 offset is CONSTANT across eras (measured 23.8601 for 1400-1600, 23.8630 for
    1800-1900), exactly as it must be: sidereal = J2000-frame - ayanamsa(J2000), because the
    precession in the tropical longitude and the precession in the ayanamsa cancel.

A worst case of 0.083 degrees against arcs 30 to 190 degrees wide is nothing.  Day-precise rows are
still taken from Z itself (never from the model), so this module never contradicts its neighbours;
the model is used only where Z is silent.


HOW THE MARGINALS ARE COMPUTED AND COMBINED
===========================================
Each (partner, body) becomes a 720-bin circular histogram over the zodiac (0.5 deg bins), summing
to 1.  A point mass is deposited by LINEAR interpolation into the two neighbouring bins, so a
day-precise row is represented to about 1e-5 in its first harmonics.  A coarse row is a uniform
quadrature over its day range (365 samples spanning the true year length, 31 spanning the true
month length, 51 years for the '0000-MM-DD' shape); a uniform case is the flat 1/720 histogram.

Two facts make everything else cheap and EXACT (no Gibbs ringing, no harmonic truncation):

  1. the marginal phasor is the histogram's Fourier coefficient:
         z_k = E[e^{i k lambda}] = conj( rfft(h)[k] )
     with bin j placed at angle j*0.5 deg.  R = |z_1|, and (Re z_1, Im z_1) is the mean resultant
     VECTOR, i.e. the circular mean direction and R carried jointly.
  2. the two birth dates are independent, so the density of the inter-partner arc
     D = lambda_a - lambda_b is the circular CROSS-CORRELATION of the two histograms, whose
     spectrum is just rfft(h_a) * conj(rfft(h_b)).  Every orb window used here is EVEN in D (the
     orb is applied to +alpha and -alpha together), so its own spectrum is real and the window's
     integral against the arc density is a Parseval sum in the spectrum - the density itself never
     has to be materialised:
         P(aspect) = sum_k parseval_k * Re(rfft(h_a)[k] * conj(rfft(h_b)[k])) * rfft(W)[k]
     This is the "integrate over the unknown day rather than testing a single arc" the brief asks
     for, done exactly rather than by sampling day pairs (which would be 365 x 365 combinations per
     row), and it is what makes the module order-free to the LAST BIT rather than merely to within
     float noise - see ORDER-FREENESS.  Verified against explicit enumeration of the day pairs:
     max absolute error 0.0021 on a mixed pair, 0.0004 on a double integral over two unknown years.

     Orb windows carry FRACTIONAL edge weights (the fraction of each bin's interval inside the
     orb), not a 0/1 test on the bin centre.  A 0/1 test admits the edge bins whole and so
     integrates orb + one bin instead of orb: it put a uniform pair's conjunction probability at
     0.04583 instead of the exact prior 0.04444.  Caught by the verification harness.
     The residue of the 0.5 degree binning is a SOFT ORB EDGE: on a day/day pair the aspect
     probability is 0 or 1 except within 0.86 degrees of the orb boundary (measured over all
     18,201 x 5 day-precise same-body arcs in the train half), where it ramps between them.  That
     is a fair description of an orb anyway - an astrologer's 8 degrees is not a cliff - and it
     costs 1-2% of day/day rows a fractional value instead of a hard 0/1.

Both reduce correctly at the extremes with no special case: two point masses give p_D a spike and
the aspect probability is 0 or 1; two uniforms give p_D flat and the aspect probability is exactly
its prior (conjunction 16/360 = 0.0444, sextile 0.0556, square 0.0778, trine 0.0778, opposition
0.0444, any-major 0.3000).


ORDER-FREENESS
==============
This dataset carries every pair in BOTH orders, so a column that changed when the partners are
swapped would let the model learn column order instead of the doctrine.  Every column here is
invariant BY CONSTRUCTION, and the verification harness checks it bit-for-bit:

  * swapping partners maps D -> -D.  Every aspect window is symmetric about 0 (an orb is applied to
    +alpha and -alpha together), and |D| and cos(kD) are even, so blocks A and P are unchanged
    mathematically - and, because they are computed as Re(F_a)Re(F_b) + Im(F_a)Im(F_b) contracted
    against a real window spectrum, they are unchanged BIT FOR BIT.  This is not pedantry: the
    first version took an inverse FFT instead, which is the same number by a different sequence of
    roundings, and the harness found the swapped pair differing in the last bits of 30 columns.
  * block N is the MEAN of the two partners' marginal phasors - symmetric in the two partners, and
    not a compromise: it is what a genderless model computes when the two natal terms share one
    complex weight.
  * block S (same sign / same element) is a symmetric bilinear form in the two sign vectors.
  * block X (cross-body) has two observable contacts, (a.X vs b.Y) and (a.Y vs b.X); swapping the
    partners merely EXCHANGES them, so the mean and the max over the two are order-free while
    either one alone would not be.
  * the census column counts over an unordered set of 10 partner-body slots.


NaN POLICY, AND WHERE THIS MODULE DELIBERATELY DIFFERS FROM ITS NEIGHBOURS
==========================================================================
The hard rule is never to fabricate a value for a date nobody recorded.  A marginal expectation is
not a fabrication - it is the correct answer to the question actually asked - so a YEAR-ONLY date
gets a number here rather than a NaN, and that is the entire thesis of the module.  The line is
drawn at RECORDED vs NOT RECORDED:

  * '0000-00-00' - nothing recorded at all.  There is no distribution to integrate, because there
    is no observation.  Every column involving that partner is NaN.  (Block N averages over the
    partners that ARE present, and is NaN only when neither is.)
  * 'YYYY-00-00', 'YYYY-MM-00', '0000-MM-DD' - something WAS recorded, and the marginal over the
    rest is computed and emitted.
  * a NaN in Z for a body on a day-precise date (should not occur for these five bodies; it does
    occur for ascendant and medium_coeli, which this module never touches) falls back to the
    analytic point for the four modelled bodies, and to uniform for the Moon, which has no model.

No integer is ever derived from a date and used to index anything without a finite-value mask in
front of it: bin indices are computed only on rows that passed a np.isfinite gate, so a NaN can
never be cast to an int and silently select the wrong bin.

df.start is the string '0000-00-00' on every row of both halves and is deliberately never read.


THE ONE CENSUS COLUMN
=====================
Date precision proxies era and notability and is the strongest single thing in this data against
the label - stronger than any real doctrine - so a precision census must not be smuggled in as
doctrine.  Two consequences, both deliberate:

  * the module emits exactly ONE such column, rs_n_fast_localised, which counts how many of the ten
    (partner, body) slots have a concentrated marginal.  It is named so it can be dropped in one
    line for an ablation.
  * standalone per-body R / sign-entropy / max-sign-probability columns are NOT emitted, even
    though they are named in the brief, because for the Moon R is EXACTLY the day-precision
    indicator and for the Sun it takes three discrete values - five more copies of the census
    wearing a doctrine's name.  The information the brief asks for is still here, in the form that
    carries the doctrine with it: the circular mean and R are emitted JOINTLY as the mean resultant
    vector (block N, R*cos(mu) and R*sin(mu)), and the sign distribution is emitted as the
    doctrinal same-sign / same-element probabilities (block S) rather than as its entropy.  Every
    remaining column is a doctrine whose value on an unknown row happens to be that doctrine's
    prior, which is unavoidable for any marginalisation and is not the same thing as a census.

PURITY: build() is a pure function of (df, Z, half).  No file reads, no network, no randomness, no
global state mutated; the module-level constants are deterministic arithmetic evaluated at import.
The column plan is static, so both halves return identical width.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Bodies.  Only the five FAST bodies live here - they are the ones Z refuses to
# place on a coarse date, and therefore the only ones with anything to
# marginalise.  Jupiter and slower already resolve from a year alone and are
# handled point-wise by the other modules; re-encoding them here would only
# duplicate their columns.  ascendant / medium_coeli are always NaN (no birth
# times) and are never touched.
# ---------------------------------------------------------------------------
FAST = ('sun', 'moon', 'mercury', 'venus', 'mars')

# Bodies with an analytic model below.  The Moon is absent ON PURPOSE: a
# mean-motion Moon (13.176 deg/day) accumulates tens of degrees of error within
# weeks, and over any range coarser than a day its marginal is uniform anyway,
# so the model could only manufacture noise.  See the docstring.
MODELLED = ('sun', 'mercury', 'venus', 'mars')

# Frame constant, MEASURED against Z on 35,485 day-precise partner-slots:
#   Z_sidereal = (geocentric longitude in the fixed J2000 ecliptic frame) - AYAN
# constant across eras (see docstring); residual max 0.083 deg on mars, rms 0.010.
AYAN = 23.8625

# Circular histogram resolution.  720 bins = 0.5 deg.  Fine enough that the
# 0/1 orb windows (5-8 deg) land on bin boundaries exactly, coarse enough that a
# chunk of 2048 rows x 5 bodies x 2 partners stays small.
NBIN = 720
BINDEG = 360.0 / NBIN

# Quadrature sample counts.  Each grid spans the TRUE length of its interval
# (true year length 365 or 366, true month length 28-31), so the quadrature is
# unbiased while the arrays stay rectangular and vectorised.
YEAR_SAMPLES = 365      # unknown day of a known year
MONTH_SAMPLES = 31      # unknown day of a known month
DOY_YEARS = 51          # unknown year, month+day known: partner's year +/- 25
DOY_HALFWIDTH = 25      # couples are near-contemporaries; see docstring

# Rows processed at a time.  Bounds peak memory (the year quadrature is
# CHUNK x 365 longitudes) without changing any result: chunking is exact.
CHUNK = 2048

# Classical synastry aspects and their orbs, in degrees.  The window is applied
# to BOTH +alpha and -alpha, which is what makes every aspect column even in D
# and therefore order-free.  Priors (probability under two uniform marginals):
# conj 0.0444, sext 0.0556, squ 0.0778, tri 0.0778, opp 0.0444, any 0.3000.
ASPECTS = (
    ('conj', 0.0, 8.0),
    ('sext', 60.0, 5.0),
    ('squ', 90.0, 7.0),
    ('tri', 120.0, 7.0),
    ('opp', 180.0, 8.0),
)

# Cross-body synastry contacts.  The classical relationship pairs, each read in
# BOTH directions (his X on her Y, and his Y on her X) and then symmetrised.
CROSS_PAIRS = (
    ('sun', 'moon'),
    ('sun', 'venus'),
    ('sun', 'mars'),
    ('moon', 'venus'),
    ('moon', 'mars'),
    ('venus', 'mars'),
)

# Threshold for "this marginal is concentrated" in the single census column.
# R >= 0.5 separates a located body (a point, a month arc, or a year-confined
# Mars at R ~ 0.56) from an effectively uniform one (year-only sun/moon/mercury
# at R <= 0.05, year-only venus at R ~ 0.25).
LOCALISED_R = 0.5


# ---------------------------------------------------------------------------
# Static window matrices, built once at import from the constants above.
# _WIN[i] is the 0/1 indicator over the 720 arc bins of aspect i's orb window
# (both lobes); _WIN[-1] is the union "any classical aspect".  The five major
# windows are disjoint (60+5 < 90-7, 90+7 < 120-7, 120+7 < 180-8), so the union
# is taken with a clip rather than a sum only as belt-and-braces.
# ---------------------------------------------------------------------------
_ARCDEG = np.arange(NBIN) * BINDEG                 # bin centre, 0..359.5
_ABSARC = np.minimum(_ARCDEG, 360.0 - _ARCDEG)     # |D| in [0,180] per bin


def _circdist(x, a):
    """Shortest angular distance in degrees between angle arrays x and scalar a."""
    return np.abs(((x - a + 180.0) % 360.0) - 180.0)


# The weight of a bin is the FRACTION OF THAT BIN'S INTERVAL that lies inside the
# orb, not a 0/1 test on its centre.  A 0/1 test admits the bins at both edges
# whole and so counts orb+BINDEG of arc instead of orb: measured, that put a
# uniform pair's conjunction probability at 33/720 = 0.04583 instead of the true
# 32/720 = 0.04444, i.e. every prior was wrong by half a bin.  With the
# fractional weight the window integrates to exactly its angular width, so the
# uniform case lands on the exact prior and the day/day case is still 0 or 1.
def _window(alpha, orb):
    lobes = sorted({alpha % 360.0, (-alpha) % 360.0})   # +alpha and -alpha; one lobe at 0 and 180
    w = np.zeros(NBIN, dtype=np.float64)
    for a in lobes:
        t = _circdist(_ARCDEG, a)
        w += np.clip(orb + 0.5 * BINDEG - t, 0.0, BINDEG) / BINDEG
    return w


_WIN = np.zeros((len(ASPECTS) + 1, NBIN), dtype=np.float64)
for _i, (_nm, _a, _orb) in enumerate(ASPECTS):
    _WIN[_i] = _window(_a, _orb)
_WIN[len(ASPECTS)] = np.minimum(1.0, _WIN[:len(ASPECTS)].sum(axis=0))

ASPECT_NAMES = tuple(nm for nm, _, _ in ASPECTS) + ('any',)

# Every window above, and _ABSARC, is EVEN about the origin of the arc (an orb
# is applied to +alpha and -alpha together), so its DFT is real.  That fact is
# what makes this module exactly order-free rather than approximately so:
# integrating an even window against the arc density can then be done by
# Parseval, entirely in the spectrum,
#     sum_n p_D[n] W[n] = sum_k parseval_k * Re(F_a[k] * conj(F_b[k])) * What[k]
# and Re(F_a * conj(F_b)) = Re(F_a)Re(F_b) + Im(F_a)Im(F_b) is BIT-IDENTICAL
# when the two partners are exchanged (IEEE multiplication and addition of the
# same two operands commute exactly).  Taking the inverse FFT instead would give
# the mathematically identical answer through a different sequence of roundings,
# and the swapped pair then differed in the last bits - which the verification
# harness caught, and which is why it is done this way.
_WSPEC = np.fft.rfft(_WIN, axis=1).real            # (6, NBIN//2+1), imaginary part ~1e-13
_ABSSPEC = np.fft.rfft(_ABSARC).real               # (NBIN//2+1,)
_PARSEVAL = np.full(NBIN // 2 + 1, 2.0 / NBIN)
_PARSEVAL[0] = 1.0 / NBIN
_PARSEVAL[-1] = 1.0 / NBIN


# ---------------------------------------------------------------------------
# Calendar and analytic ephemeris.  Pure arithmetic; no tables read from disk.
# ---------------------------------------------------------------------------
def _jd_midnight(y, m, d):
    """Julian Day at 00:00 UT for a PROLEPTIC GREGORIAN civil date.

    Proleptic (i.e. the Gregorian rule extended backwards through 1582) is not a
    guess: it was calibrated against Z, and the historical Julian-before-1582
    convention leaves a 10-day / 10-degree residual on the pre-1582 dates while
    this one leaves 0.01 degrees.  See the docstring's calibration table.
    """
    y = np.asarray(y, dtype=np.float64)
    m = np.asarray(m, dtype=np.float64)
    d = np.asarray(d, dtype=np.float64)
    yy = np.where(m <= 2, y - 1.0, y)
    mm = np.where(m <= 2, m + 12.0, m)
    a = np.floor(yy / 100.0)
    b = 2.0 - a + np.floor(a / 4.0)
    return (np.floor(365.25 * (yy + 4716.0)) + np.floor(30.6001 * (mm + 1.0))
            + d + b - 1524.5)


def _is_leap(y):
    y = np.asarray(y)
    return (y % 4 == 0) & ((y % 100 != 0) | (y % 400 == 0))


_MLEN = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=np.float64)


def _month_len(y, m):
    """Length in days of civil month m of year y (arrays); m must be 1..12."""
    base = _MLEN[np.asarray(m, dtype=np.int64) - 1]
    return np.where((np.asarray(m) == 2) & _is_leap(y), 29.0, base)


# JPL "Approximate Positions of the Planets" (Standish) mean Keplerian elements
# referred to the mean ecliptic and equinox of J2000, with linear rates per
# Julian century.  Order: a, a_dot, e, e_dot, I, I_dot, L, L_dot, longperi,
# longperi_dot, longnode, longnode_dot  (au and degrees).
_ELEMENTS = {
    'mercury': (0.38709927, 0.00000037, 0.20563593, 0.00001906,
                7.00497902, -0.00594749, 252.25032350, 149472.67411175,
                77.45779628, 0.16047689, 48.33076593, -0.12534081),
    'venus': (0.72333566, 0.00000390, 0.00677672, -0.00004107,
              3.39467605, -0.00078890, 181.97909950, 58517.81538729,
              131.60246718, 0.00268329, 76.67984255, -0.27769418),
    'earth': (1.00000261, 0.00000562, 0.01671123, -0.00004392,
              -0.00001531, -0.01294668, 100.46457166, 35999.37244981,
              102.93768193, 0.32327364, 0.0, 0.0),
    'mars': (1.52371034, 0.00001847, 0.09339410, 0.00007882,
             1.84969142, -0.00813131, -4.55343205, 19140.30268499,
             -23.94362959, 0.44441088, 49.55953891, -0.29257343),
}


def _helio_xy(name, T):
    """Heliocentric x, y of a planet in the J2000 ecliptic frame, au.

    Two-body Kepler on the mean elements above.  Only x and y are needed: an
    ecliptic LONGITUDE is atan2(y, x) of the geocentric vector, and the orbital
    inclination already enters x and y through the node/inclination rotation.
    """
    a0, ad, e0, ed, i0, idot, l0, ldot, p0, pd, o0, od = _ELEMENTS[name]
    a = a0 + ad * T
    e = e0 + ed * T
    inc = np.deg2rad(i0 + idot * T)
    lon = l0 + ldot * T
    peri = p0 + pd * T
    node = np.deg2rad(o0 + od * T)
    # mean anomaly, wrapped to [-180,180) before the solve so Newton starts near
    # the root even for the extreme centuries in this data (1400..2003).
    M = np.deg2rad(((lon - peri + 180.0) % 360.0) - 180.0)
    E = M + e * np.sin(M)                     # first-order start
    for _ in range(12):                       # Newton; e <= 0.21 (mercury)
        E = E - (E - e * np.sin(E) - M) / (1.0 - e * np.cos(E))
    xv = a * (np.cos(E) - e)
    yv = a * np.sqrt(1.0 - e * e) * np.sin(E)
    w = np.deg2rad(peri) - node               # argument of perihelion
    cw, sw = np.cos(w), np.sin(w)
    cn, sn = np.cos(node), np.sin(node)
    ci = np.cos(inc)
    x = xv * (cw * cn - sw * sn * ci) - yv * (sw * cn + cw * sn * ci)
    y = xv * (cw * sn + sw * cn * ci) - yv * (sw * sn - cw * cn * ci)
    return x, y


def _geo_lons(jd, bodies):
    """Geocentric ecliptic longitudes in Z's frame, degrees, for `bodies`.

    Returns a dict body -> (len(jd),) array in [0, 360).  The Earth solve is
    done once and shared, which is why all four modelled bodies are requested
    together rather than one at a time.
    """
    T = (np.asarray(jd, dtype=np.float64) - 2451545.0) / 36525.0
    ex, ey = _helio_xy('earth', T)
    out = {}
    for b in bodies:
        if b == 'sun':
            x, y = -ex, -ey            # the Sun seen from Earth is Earth seen from the Sun, reversed
        else:
            px, py = _helio_xy(b, T)
            x, y = px - ex, py - ey
        out[b] = (np.rad2deg(np.arctan2(y, x)) - AYAN) % 360.0
    return out


# ---------------------------------------------------------------------------
# Date parsing.  Five shapes, all handled; a field that is absent is 0.
# ---------------------------------------------------------------------------
def _parse_dates(col, n):
    """'YYYY-MM-DD' strings (any of the five shapes) -> (year, month, day) int arrays.

    A missing field is 0, never a guess.  Anything unparseable is treated as
    wholly absent (0,0,0), which the NaN policy turns into NaN columns rather
    than into a fabricated date.
    """
    s = pd.Series(col).astype('string').fillna('')
    s = s.str.strip()
    ok = s.str.match(r'^\d{4}-\d{2}-\d{2}$').fillna(False).to_numpy()
    y = np.zeros(n, dtype=np.int64)
    m = np.zeros(n, dtype=np.int64)
    d = np.zeros(n, dtype=np.int64)
    if ok.any():
        v = s.to_numpy()
        sub = np.asarray(v[ok], dtype='U10')
        y[ok] = np.asarray([int(t[0:4]) for t in sub], dtype=np.int64)
        m[ok] = np.asarray([int(t[5:7]) for t in sub], dtype=np.int64)
        d[ok] = np.asarray([int(t[8:10]) for t in sub], dtype=np.int64)
    # A month outside 1..12 or a day outside 1..31 is not a date we can place;
    # demote it to "absent" for that field rather than indexing a table with it.
    bad_m = (m < 1) | (m > 12)
    m = np.where(bad_m, 0, m)
    bad_d = (d < 1) | (d > 31) | (m == 0)
    d = np.where(bad_d, 0, d)
    y = np.where(y < 1, 0, y)
    return y, m, d


# ---------------------------------------------------------------------------
# Histogram construction: one circular marginal per (partner, body).
# ---------------------------------------------------------------------------
def _deposit(h, rows, ang, w):
    """Add mass w at angles `ang` into rows `rows` of h, linearly interpolated.

    Every caller filters to finite angles first; the assertion below is the last
    line of defence against a NaN reaching the int cast that picks a bin.
    """
    if rows.size == 0:
        return
    ang = np.asarray(ang, dtype=np.float64)
    good = np.isfinite(ang)
    if not good.all():
        rows = rows[good]
        ang = ang[good]
        w = w[good] if np.ndim(w) else w
        if rows.size == 0:
            return
    x = (ang % 360.0) * (NBIN / 360.0)
    i0 = np.floor(x).astype(np.int64)
    f = x - i0
    i0 = i0 % NBIN
    i1 = (i0 + 1) % NBIN
    c = h.shape[0]
    wv = np.broadcast_to(np.asarray(w, dtype=np.float64), rows.shape)
    flat0 = rows * NBIN + i0
    flat1 = rows * NBIN + i1
    acc = np.bincount(flat0, weights=wv * (1.0 - f), minlength=c * NBIN)
    acc += np.bincount(flat1, weights=wv * f, minlength=c * NBIN)
    h += acc.reshape(c, NBIN)


def _marginals(y, m, d, theta, co_y):
    """The five circular marginals for ONE partner over a chunk of rows.

    y, m, d : (c,) int   this partner's parsed date fields (0 = field absent)
    theta   : (c, 5) float  Z's longitudes for FAST, in Z's own frame, NaN where
                            Z refused to place the body
    co_y    : (c,) int   the OTHER partner's year, used only by the '0000-MM-DD'
                         shape as the row's only available era anchor

    Returns dict body -> (c, NBIN) histogram, each row summing to 1.
    """
    c = int(y.shape[0])
    hists = {b: np.zeros((c, NBIN), dtype=np.float64) for b in FAST}
    placed = {b: np.zeros(c, dtype=bool) for b in FAST}

    day_p = (y > 0) & (m > 0) & (d > 0)            # 'YYYY-MM-DD'
    mon_p = (y > 0) & (m > 0) & (d == 0)           # 'YYYY-MM-00'
    yr_p = (y > 0) & (m == 0)                      # 'YYYY-00-00' (and 'YYYY-00-DD')
    doy_p = (y == 0) & (m > 0) & (d > 0)           # '0000-MM-DD'
    # everything else -> uniform, filled at the end

    # --- day precision: the point mass comes from Z, never from the model, so
    # this module agrees exactly with every point-wise module on these rows.
    if day_p.any():
        rows_all = np.nonzero(day_p)[0]
        for k, b in enumerate(FAST):
            th = theta[rows_all, k]
            fin = np.isfinite(th)
            r = rows_all[fin]
            _deposit(hists[b], r, th[fin], np.ones(r.shape[0]))
            placed[b][r] = True
        # Z silent on a day-precise date should not happen for these five bodies;
        # if it does, the four modelled bodies fall back to the analytic point
        # (0.08 deg of Z at worst) and the Moon stays uniform, having no model.
        need = rows_all[~np.isfinite(theta[rows_all][:, [FAST.index(b) for b in MODELLED]]).all(axis=1)]
        if need.size:
            jd = _jd_midnight(y[need], m[need], d[need]) + 0.5
            lons = _geo_lons(jd, MODELLED)
            for b in MODELLED:
                miss = need[~placed[b][need]]
                if miss.size:
                    sel = np.searchsorted(need, miss)
                    _deposit(hists[b], miss, lons[b][sel], np.ones(miss.shape[0]))
                    placed[b][miss] = True

    # --- month precision: unknown day of a known month.  31 samples spanning
    # the TRUE month length, so the quadrature is uniform over the real month.
    if mon_p.any():
        rows = np.nonzero(mon_p)[0]
        jd0 = _jd_midnight(y[rows], m[rows], 1) + 0.5
        span = _month_len(y[rows], m[rows])
        frac = np.arange(MONTH_SAMPLES, dtype=np.float64) / MONTH_SAMPLES
        jd = jd0[:, None] + span[:, None] * frac[None, :]
        lons = _geo_lons(jd.ravel(), MODELLED)
        rep = np.repeat(rows, MONTH_SAMPLES)
        wgt = np.full(rep.shape[0], 1.0 / MONTH_SAMPLES)
        for b in MODELLED:
            _deposit(hists[b], rep, lons[b], wgt)
            placed[b][rows] = True
        # the Moon sweeps 395 deg in a month: uniform, left unplaced on purpose.

    # --- year only: unknown day of a known year.  365 samples spanning the true
    # year length (366 in a leap year), so no day of the year is over-weighted.
    if yr_p.any():
        rows = np.nonzero(yr_p)[0]
        jd0 = _jd_midnight(y[rows], 1, 1) + 0.5
        span = np.where(_is_leap(y[rows]), 366.0, 365.0)
        frac = np.arange(YEAR_SAMPLES, dtype=np.float64) / YEAR_SAMPLES
        jd = jd0[:, None] + span[:, None] * frac[None, :]
        lons = _geo_lons(jd.ravel(), MODELLED)
        rep = np.repeat(rows, YEAR_SAMPLES)
        wgt = np.full(rep.shape[0], 1.0 / YEAR_SAMPLES)
        for b in MODELLED:
            _deposit(hists[b], rep, lons[b], wgt)
            placed[b][rows] = True
        # the Moon is uniform over a year by a very large margin: left unplaced.

    # --- year unknown, month and day known.  Only the Sun is recoverable: its
    # longitude is a function of the day of the year, up to the ayanamsa drift
    # over the unknown era.  The row's only era fact is the partner's year, so
    # that is what is marginalised over (+/- 25 years).  With no partner year
    # anywhere in the row, nothing anchors the era and the Sun stays uniform.
    if doy_p.any():
        rows = np.nonzero(doy_p & (co_y > 0))[0]
        if rows.size:
            offs = np.arange(-DOY_HALFWIDTH, DOY_HALFWIDTH + 1, dtype=np.int64)
            yy = co_y[rows][:, None] + offs[None, :]
            mm = np.broadcast_to(m[rows][:, None], yy.shape)
            dd = np.broadcast_to(d[rows][:, None], yy.shape)
            # a 29 Feb in a non-leap year of the window rolls to 1 Mar, which is
            # the right neighbour on the circle and shifts the Sun by 1 degree.
            jd = _jd_midnight(yy.ravel(), mm.ravel(), dd.ravel()) + 0.5
            lons = _geo_lons(jd, ('sun',))
            rep = np.repeat(rows, DOY_YEARS)
            _deposit(hists['sun'], rep, lons['sun'],
                     np.full(rep.shape[0], 1.0 / DOY_YEARS))
            placed['sun'][rows] = True

    # --- everything not placed above is UNIFORM: the honest marginal of a body
    # whose position the record cannot constrain at all.  Uniform is not a
    # fabricated position - it carries exactly zero information (z_k = 0 for all
    # k >= 1) and makes every aspect probability equal to its prior.
    flat = 1.0 / NBIN
    for b in FAST:
        rest = ~placed[b]
        if rest.any():
            hists[b][rest] = flat
    return hists


# ---------------------------------------------------------------------------
# THE COLUMN PLAN.  Static, so both halves return identical width.
# ---------------------------------------------------------------------------
def _column_names():
    names = []
    # BLOCK N - marginalised natal phasors, tied over the two partners.
    for b in FAST:
        for k in (1, 2):
            names.append('rs_nat_c%d_%s' % (k, b))
            names.append('rs_nat_s%d_%s' % (k, b))
    # BLOCK A - marginalised same-body synastry aspect probabilities.
    for b in FAST:
        for nm in ASPECT_NAMES:
            names.append('rs_asp_%s_%s' % (nm, b))
    # BLOCK P - marginalised arc phasors and expected arc.
    for b in FAST:
        names.append('rs_arc_ecos1_%s' % b)
        names.append('rs_arc_ecos2_%s' % b)
        names.append('rs_arc_eabs_%s' % b)
    # BLOCK X - marginalised cross-body contacts, symmetrised over the two.
    for x, yb in CROSS_PAIRS:
        names.append('rs_x_conj_mean_%s_%s' % (x, yb))
        names.append('rs_x_conj_max_%s_%s' % (x, yb))
        names.append('rs_x_any_mean_%s_%s' % (x, yb))
    # BLOCK S - marginalised sign agreement.
    for b in FAST:
        names.append('rs_sign_same_%s' % b)
        names.append('rs_sign_elem_%s' % b)
    # BLOCK E - the single permitted census column.
    names.append('rs_n_fast_localised')
    return names


NAMES = _column_names()
NCOL = len(NAMES)

_ASP_CONJ = ASPECT_NAMES.index('conj')
_ASP_ANY = ASPECT_NAMES.index('any')


def _cross_spec(Fa, Fb):
    """Re( rfft(h_a)[k] * conj(rfft(h_b)[k]) ), the real cross-spectrum.

    This is Re(E[exp(i*k*D)]) for the arc D = lambda_a - lambda_b, i.e. E[cos kD]
    at every harmonic at once, and it is the only place the two partners meet.
    Written as Re*Re + Im*Im rather than as a complex product so that exchanging
    the partners is bit-for-bit the same computation (see _WSPEC above).
    """
    return Fa.real * Fb.real + Fa.imag * Fb.imag


def _integrate(reC, spec):
    """Parseval: integrate even window(s) `spec` against the arc density of reC.

    reC  : (c, NBIN//2+1) real cross-spectrum from _cross_spec
    spec : (w, NBIN//2+1) real spectra of the even windows
    returns (c, w) - the probability mass of the arc inside each window.
    """
    return (reC * _PARSEVAL) @ spec.T


def _chunk_features(ya, ma, da, yb, mb, db, tha, thb):
    """All columns for one chunk of rows.  Returns (c, NCOL) float64."""
    c = int(ya.shape[0])
    out = np.empty((c, NCOL), dtype=np.float64)
    col = 0

    HA = _marginals(ya, ma, da, tha, yb)
    HB = _marginals(yb, mb, db, thb, ya)
    # rfft[k] = sum_j h_j exp(-2*pi*i*j*k/NBIN); with bin j at angle j*BINDEG
    # the marginal phasor is z_k = E[exp(i*k*lambda)] = conj(rfft[k]).
    FA = {b: np.fft.rfft(HA[b], axis=1) for b in FAST}
    FB = {b: np.fft.rfft(HB[b], axis=1) for b in FAST}

    # Presence: a wholly unrecorded date ('0000-00-00') has no distribution to
    # integrate.  Those rows are NaN'd at the end rather than given a prior.
    pres_a = (ya > 0) | (ma > 0) | (da > 0)
    pres_b = (yb > 0) | (mb > 0) | (db > 0)
    both = pres_a & pres_b

    # ---- BLOCK N -----------------------------------------------------------
    # Marginalised natal phasor, TIED over the two partners:
    #     ( E[cos k*lambda_a] + E[cos k*lambda_b] ) / 2   and the sin twin.
    # This pair IS the circular mean direction and the resultant length R
    # carried jointly (R*cos mu, R*sin mu) - the summary the brief asks for, in
    # the one form that keeps the direction attached to the concentration
    # instead of isolating precision in a column of its own.  It collapses to
    # cos/sin of the point on a day-precise date and to EXACTLY 0 on a uniform
    # marginal, which is the correct expectation and not an imputed angle.
    # Doctrine: a natal placement matters in whoever's chart it falls (a tied
    # weight, the genderless form), and for the slow-moving symbolism the mean
    # phasor of a pair is a clock on the couple's shared epoch.
    # Tied means MEAN OVER THE PARTNERS PRESENT: a partner with no date at all
    # contributes nothing rather than dragging the mean toward zero.
    wa = pres_a.astype(np.float64)
    wb = pres_b.astype(np.float64)
    wsum = wa + wb
    with np.errstate(invalid='ignore', divide='ignore'):
        for b in FAST:
            for k in (1, 2):
                za = np.conj(FA[b][:, k])
                zb = np.conj(FB[b][:, k])
                mc = (wa * za.real + wb * zb.real) / wsum
                ms = (wa * za.imag + wb * zb.imag) / wsum
                bad = wsum <= 0
                mc = np.where(bad, np.nan, mc)
                ms = np.where(bad, np.nan, ms)
                out[:, col] = mc
                col += 1
                out[:, col] = ms
                col += 1

    # ---- BLOCK A and BLOCK P ----------------------------------------------
    # The density of the inter-partner arc D = lambda_a - lambda_b is the
    # circular cross-correlation of the two marginals - one inverse FFT - which
    # is the exact integral over BOTH unknown days at once.  Aspect
    # probabilities are then dot products with the fixed orb windows, so a
    # day/day pair gives 0 or 1, a coarse/known pair gives the true fraction of
    # the unknown days that land in the orb, and a uniform pair gives exactly
    # the prior.  Every window covers +alpha and -alpha together, so every
    # column is even in D and therefore order-free.
    cross = {}
    for b in FAST:
        cross[b] = _cross_spec(FA[b], FB[b])
        probs = _integrate(cross[b], _WSPEC)   # (c, 6) - the five aspects then 'any'
        np.clip(probs, 0.0, 1.0, out=probs)
        out[:, col:col + probs.shape[1]] = probs
        col += probs.shape[1]

    for b in FAST:
        # E[cos D] and E[cos 2D]: the marginalised versions of the arc phasors a
        # point-wise module emits as cos of a single arc.  E[e^{i k D}] is the
        # conjugate of the kth cross-spectrum coefficient, so its real part is
        # read straight off - exact, not binned.  Even in D under a swap.
        out[:, col] = cross[b][:, 1]
        col += 1
        out[:, col] = cross[b][:, 2]
        col += 1
        # E[|D|]: the expected absolute arc in degrees, [0,180].  This is the
        # marginalised form of the single most basic synastry number there is -
        # "how far apart are their two Venuses" - and is 90 exactly when either
        # marginal is uniform, which is the correct expectation, not a guess.
        out[:, col] = np.clip(_integrate(cross[b], _ABSSPEC[None, :])[:, 0], 0.0, 180.0)
        col += 1

    # ---- BLOCK X -----------------------------------------------------------
    # Cross-body contacts (his Venus on her Mars, and his Mars on her Venus).
    # Two observable contacts exist; swapping the partners exchanges them, so
    # the MEAN and the MAX over the two are order-free while either alone would
    # encode column order.  This is where marginalisation pays most: a partner
    # known only to a year still has a located Mars, so its contact with the
    # other partner's day-precise Venus is a real, graded probability.
    for x, yb_ in CROSS_PAIRS:
        q1 = np.clip(_integrate(_cross_spec(FA[x], FB[yb_]), _WSPEC), 0.0, 1.0)
        q2 = np.clip(_integrate(_cross_spec(FA[yb_], FB[x]), _WSPEC), 0.0, 1.0)
        out[:, col] = 0.5 * (q1[:, _ASP_CONJ] + q2[:, _ASP_CONJ])
        col += 1
        out[:, col] = np.maximum(q1[:, _ASP_CONJ], q2[:, _ASP_CONJ])
        col += 1
        out[:, col] = 0.5 * (q1[:, _ASP_ANY] + q2[:, _ASP_ANY])
        col += 1

    # ---- BLOCK S -----------------------------------------------------------
    # Sign agreement, integrated over the uncertainty.  P(both partners' body
    # falls in the SAME sidereal sign) = sum_s pa[s]*pb[s], and the same over
    # the four elements (fire/earth/air/water = sign index mod 4), which is the
    # classical "compatible element" reading.  A point/point pair gives 0 or 1,
    # a month-precise Sun spread across a sign boundary gives the true split,
    # and a uniform pair gives exactly 1/12 and 1/4.  Symmetric bilinear forms,
    # hence order-free.  This is the sign-distribution summary the brief asks
    # for, kept in its doctrinal form rather than reduced to an entropy (an
    # entropy would have been the precision census under another name).
    for b in FAST:
        sa = HA[b].reshape(c, 12, NBIN // 12).sum(axis=2)
        sb = HB[b].reshape(c, 12, NBIN // 12).sum(axis=2)
        out[:, col] = (sa * sb).sum(axis=1)
        col += 1
        ea = sa.reshape(c, 3, 4).sum(axis=1)     # sign index mod 4 = element
        eb = sb.reshape(c, 3, 4).sum(axis=1)
        out[:, col] = (ea * eb).sum(axis=1)
        col += 1

    # ---- BLOCK E -----------------------------------------------------------
    # THE ONE PERMITTED CENSUS COLUMN.  How many of the ten (partner, body)
    # slots have a concentrated marginal, R = |z_1| >= 0.5.  Precision is the
    # strongest single signal in this data and it is era/notability, not
    # doctrine; it is given exactly one clearly named column so that it can be
    # dropped in one line for an ablation instead of being smeared across the
    # block as five copies of R wearing a doctrine's name.
    cnt = np.zeros(c, dtype=np.float64)
    for b in FAST:
        cnt += (np.abs(FA[b][:, 1]) >= LOCALISED_R).astype(np.float64) * pres_a
        cnt += (np.abs(FB[b][:, 1]) >= LOCALISED_R).astype(np.float64) * pres_b
    out[:, col] = cnt
    col += 1

    if col != NCOL:
        raise RuntimeError('emitted %d columns, plan says %d' % (col, NCOL))

    # A partner whose date is wholly unrecorded has no distribution to
    # marginalise, so every pairwise column involving it is NaN.  Block N is
    # exempt: it already averaged over the partners that are present.
    nblock = 4 * len(FAST)
    out[~both, nblock:NCOL - 1] = np.nan
    return out


def build(df, Z, half):
    """Uncertainty-marginalised re-encoding of the five fast bodies.

    Pure function.  See the module docstring for the doctrine behind every
    block, the measured calibration of the analytic ephemeris against Z, and
    the NaN policy.
    """
    n = len(df)
    for c in ('dob_a', 'dob_b'):
        if c not in df.columns:
            raise ValueError('df is missing required column %r' % c)
    if half not in ('train', 'test'):
        raise ValueError('half must be train or test, got %r' % (half,))

    ya, ma, da = _parse_dates(df['dob_a'].to_numpy(), n)
    yb, mb, db = _parse_dates(df['dob_b'].to_numpy(), n)
    # df.start is '0000-00-00' on every row of this dataset and is never read.

    bodies = [str(b) for b in np.asarray(Z['bodies']).ravel()]
    try:
        widx = [bodies.index(b) for b in FAST]
    except ValueError as exc:
        raise ValueError('Z is missing a fast body: %s' % (exc,))
    TA = np.asarray(Z['theta_a_%s' % half], dtype=np.float64)
    TB = np.asarray(Z['theta_b_%s' % half], dtype=np.float64)
    if TA.shape[0] != n or TB.shape[0] != n:
        raise ValueError('Z has %d/%d rows for half %r, df has %d'
                         % (TA.shape[0], TB.shape[0], half, n))
    TA = TA[:, widx]
    TB = TB[:, widx]

    X = np.empty((n, NCOL), dtype=np.float64)
    for lo in range(0, n, CHUNK):
        hi = min(n, lo + CHUNK)
        X[lo:hi] = _chunk_features(
            ya[lo:hi], ma[lo:hi], da[lo:hi],
            yb[lo:hi], mb[lo:hi], db[lo:hi],
            TA[lo:hi], TB[lo:hi],
        )
    return X.astype(np.float32), list(NAMES)
