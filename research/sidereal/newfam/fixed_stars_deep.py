"""fixed_stars_deep — the fixed-star and constellation doctrine, at the depth the tradition uses.

WHAT THIS ENCODES
-----------------
Classical astrology does not read only the planets: it reads the planets AGAINST the fixed stars.
A planet on Algol is not the same planet as one on Spica, and the whole delineation of a chart can
turn on a single degree.  The rules are specific and old:

  * The contact is a CONJUNCTION IN LONGITUDE, and the orb is TIGHT — one to two degrees, never the
    5-8 degrees a planetary aspect gets.  Ptolemy, Robson and Brady all insist on this: a star is a
    point, not a body with a sphere of influence.
  * The orb is scaled by the star's MAGNITUDE.  A first-magnitude star is loud enough to be read at
    two degrees; a fourth-magnitude one barely at half of that.  Brightness IS importance here.
  * Every star carries a PLANETARY NATURE — "of the nature of Mars and Jupiter" — which is how the
    tradition states what the star does.  That is the star's tone, and it is what makes a contact
    benefic or malefic independent of the planet that made it.
  * Four stars are ROYAL (the Persian Watchers of the four quarters): Aldebaran, Regulus, Antares,
    Fomalhaut.  Fifteen are BEHENIAN (Agrippa's magical stars).  A handful are NEBULAE AND CLUSTERS
    — Praesepe, the Pleiades, the Hyades, Capulus, Aculeus, Acumen, Facies, Foramen — read by the
    whole tradition as "blindness and trouble", the cloudy places where sight and judgement fail.

The catalogue below carries 80 stars: the four Royals, the fifteen Behenians, the ten nebulae and
clusters, the marriage stars, the separative stars, the stars of violent death, and the rest of the
list Robson tabulates.

THE FRAME — WHY 50.29"/yr IS *NOT* APPLIED HERE
-----------------------------------------------
Z gives SIDEREAL (Lahiri) longitudes.  Precession is what the sidereal frame REMOVES: a fixed star's
sidereal longitude is, by construction, constant.  The 50.29 arcsec/year era correction is what you
apply to get a star's TROPICAL longitude for a birth year — and applying it on top of an already
sidereal chart would double-count it, putting Aldebaran 5.6 degrees off for a 1600 birth and turning
every one-degree conjunction into noise.  So the correction IS made, once, in the right place:

  catalogue value  = the star's TROPICAL ecliptic longitude at J2000, computed from the star's
                     J2000 RA/Dec through the J2000 obliquity, then cross-checked against the
                     classical tables: 69 of 77 checked stars agree to under 0.05 deg and 74 of 77
                     to under 0.2 deg (Baten Kaitos 21.950 vs the tabulated 21 Ari 57, Zuben
                     Eschamali 229.372 vs 19 Sco 22, Aldebaran 69.789 vs 9 Gem 47).  Where the two
                     disagreed the computation won and the disagreement was traced: the tabulated
                     "Tejat" at 3 Cnc 14 is Propus (eta Geminorum), not mu, so BOTH are carried
                     here under their own names.
  sidereal (Lahiri)= tropical(J2000) - AYANAMSA_J2000  (23 deg 51' 11")
  era correction   = PROPER MOTION ONLY, the star's real motion in ecliptic longitude, which is the
                     only thing that actually moves a star in this frame.  Values are per-star
                     arcsec/yr derived from Hipparcos mu_alpha*/mu_delta.  It matters for a handful:
                     Bungula -4.82"/yr (0.53 deg over four centuries), Altair +0.70, Pollux -0.61,
                     Sirius and Procyon -0.55, Vega +0.50, Denebola -0.42.  For the rest it is under
                     0.03"/yr and is set to exactly 0 rather than pretending to a precision we lack.

Sanity check on the conversion: Spica lands at 203.841 - 23.853 = 179.988, i.e. sidereal 180 deg,
which is the Chitrapaksha definition of the Lahiri ayanamsa itself.  Regulus lands at 125.976
(6 deg Leo sidereal, in Magha) and Aldebaran at 45.936 — both the standard Vedic positions.

ORDER-FREENESS
--------------
The label is a property of the COUPLE, so no feature may know which partner was written into
column a.  Every per-partner quantity is emitted only as max/min (or as a pair minimum) over the
two partners; every pair quantity is a symmetric function of the two star profiles (min, product,
dot, |difference|, or a sum over the full ordered cross-grid, which swapping partners merely
transposes).  Nothing raw-per-slot is ever emitted.

MISSINGNESS
-----------
NaN is propagated, never filled.  Slow bodies resolve from a year alone; sun/moon/mercury/venus/mars
need month+day, so a 'YYYY-00-00' row has them NaN and every feature that touches them is NaN.  A
partner with no usable longitude at all yields NaN for that partner, and every pair feature that
needs both partners is then NaN too (np.maximum/np.minimum are used, not np.fmax/np.fmin, precisely
so a missing partner cannot be silently replaced by the present one).  df.start is ALWAYS
'0000-00-00' in this dataset and is never read.  The '0000-MM-DD' shape (day known, year unknown)
cannot produce any longitude, so the era falls back to J2000 for the star positions -- which changes
nothing, because every longitude on such a row is NaN anyway, and because the era correction is
bounded by ~0.5 deg in this frame regardless.

Pure function of (df, Z, half): no I/O, no randomness, no global state, no other module imported.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Frame constants
# ---------------------------------------------------------------------------
# Lahiri (Chitrapaksha) ayanamsa at J2000.0 = 23 deg 51' 11".  Subtracting it from a tropical
# J2000 longitude gives the sidereal longitude in the frame Z is expressed in.
AYANAMSA_J2000 = 23.0 + 51.0 / 60.0 + 11.0 / 3600.0      # 23.85306 deg

# ---------------------------------------------------------------------------
# Bodies.  'ascendant' and 'medium_coeli' are excluded: with no birth time they are always NaN and
# could only contribute empty columns.  Classical star doctrine reads a star against a PLANET or an
# ANGLE; the angles are unavailable, so the planets and the modern points carry it.
# ---------------------------------------------------------------------------
BODIES = [
    'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus',
    'neptune', 'pluto', 'true_node', 'true_south_node', 'chiron', 'mean_lilith',
]
NB = len(BODIES)

# How loudly each body carries a star.  The tradition ranks the luminaries first (a star on the Sun
# or Moon IS the delineation), then the personal planets, then the social ones; the nodes get a
# reduced share because they are points, and the moderns (Uranus/Neptune/Pluto/Chiron/Lilith) the
# least because no classical author read a star through them at all.
BODY_W = {
    'sun': 1.50, 'moon': 1.50,
    'venus': 1.20, 'mercury': 1.00, 'mars': 1.00,
    'jupiter': 0.90, 'saturn': 0.90,
    'true_node': 0.70, 'true_south_node': 0.70,
    'uranus': 0.50, 'neptune': 0.50, 'pluto': 0.50,
    'chiron': 0.40, 'mean_lilith': 0.40,
}

# Bodies that resolve from a birth YEAR alone.  Features restricted to these are computable on every
# row that has a year at all, so they cannot be confounded with date precision.
SLOW = {'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
        'true_node', 'true_south_node', 'chiron', 'mean_lilith'}

# ---------------------------------------------------------------------------
# THE CATALOGUE.  (key, tropical longitude at J2000 in degrees, proper motion in ecliptic longitude
# in arcsec/yr, visual magnitude, planetary nature).
#
# Longitudes are computed from J2000 RA/Dec through the J2000 obliquity, NOT copied from a table --
# and then checked against the classical tables, which they reproduce to a few arcminutes.  The
# magnitude drives both the orb and the weight, exactly as the doctrine's "regard only the brighter
# stars" rule intends.  The nature is Ptolemy's/Robson's planetary equivalence for the star.
# ---------------------------------------------------------------------------
CATALOG = [
    # key                  lon2000     pm    mag   nature
    ('difda',                2.584,  0.240, 2.04, ('saturn',)),
    ('algenib',              9.156,  0.000, 2.83, ('mars', 'mercury')),
    ('alpheratz',           14.309,  0.055, 2.06, ('jupiter', 'venus')),
    ('baten_kaitos',        21.950,  0.033, 3.73, ('saturn',)),
    ('mirach',              30.405,  0.124, 2.06, ('venus',)),
    ('sheratan',            33.970,  0.054, 2.64, ('mars', 'saturn')),
    ('hamal',               37.663,  0.131, 2.00, ('mars', 'saturn')),
    ('schedar',             37.784,  0.034, 2.24, ('saturn', 'venus')),
    ('almach',              44.225,  0.000, 2.10, ('venus',)),
    ('menkar',              44.320, -0.035, 2.53, ('saturn',)),
    ('zaurak',              53.868,  0.038, 2.95, ('saturn',)),
    ('capulus',             54.185,  0.000, 4.30, ('mars', 'mercury')),      # h+chi Persei cluster
    ('algol',               56.168,  0.000, 2.12, ('saturn', 'jupiter')),    # the Gorgon's head
    ('alcyone',             59.992,  0.000, 2.87, ('moon', 'mars')),         # the Pleiades
    ('prima_hyadum',        65.805,  0.110, 3.65, ('saturn', 'mercury')),    # the Hyades
    ('ain',                 68.465,  0.100, 3.53, ('saturn', 'mercury')),    # the Hyades, Bull's eye
    ('aldebaran',           69.789,  0.036, 0.85, ('mars',)),                # ROYAL - Watcher of East
    ('rigel',               76.830,  0.000, 0.12, ('jupiter', 'saturn')),
    ('bellatrix',           80.947,  0.000, 1.64, ('mars', 'mercury')),
    ('capella',             81.858,  0.044, 0.08, ('mars', 'mercury')),
    ('alnilam',             83.464,  0.000, 1.69, ('jupiter', 'saturn')),
    ('al_hecka',            84.785,  0.000, 3.00, ('mars',)),
    ('polaris',             88.568,  0.047, 1.98, ('saturn', 'venus')),
    ('betelgeuse',          88.755,  0.000, 0.50, ('mars', 'mercury')),
    ('menkalinan',          89.910, -0.061, 1.90, ('mars', 'mercury')),
    ('propus',              93.436, -0.060, 3.28, ('mercury', 'venus')),
    ('tejat',               95.302,  0.061, 2.87, ('mercury', 'venus')),
    ('alhena',              99.105,  0.000, 1.93, ('mercury', 'venus')),
    ('sirius',             104.082, -0.545, -1.46, ('jupiter', 'mars')),
    ('canopus',            104.961,  0.064, -0.72, ('saturn', 'jupiter')),
    ('castor',             110.240, -0.182, 1.58, ('mercury',)),
    ('pollux',             113.216, -0.612, 1.14, ('mars',)),
    ('procyon',            115.786, -0.545, 0.38, ('mercury', 'mars')),
    ('praesepe',           127.351, -0.031, 3.70, ('mars', 'moon')),         # M44, the Beehive
    ('asellus_australis',  128.722,  0.077, 3.94, ('mars', 'sun')),          # the southern Ass
    ('alphard',            147.279,  0.000, 1.98, ('saturn', 'venus')),
    ('regulus',            149.829, -0.235, 1.35, ('mars', 'jupiter')),      # ROYAL - Watcher North
    ('zosma',              161.317,  0.189, 2.56, ('saturn', 'venus')),
    ('denebola',           171.618, -0.419, 2.14, ('saturn', 'venus')),
    ('alkaid',             176.933, -0.149, 1.86, ('moon', 'venus')),
    ('zaniah',             184.832,  0.000, 3.89, ('mercury', 'venus')),
    ('vindemiatrix',       189.940, -0.271, 2.83, ('saturn', 'mercury')),    # "the Widow Maker"
    ('algorab',            193.452, -0.140, 2.95, ('mars', 'saturn')),
    ('seginus',            197.663, -0.243, 3.03, ('mercury', 'saturn')),
    ('foramen',            202.155,  0.000, 4.30, ('saturn', 'jupiter')),    # eta Carinae nebula
    ('spica',              203.841,  0.000, 0.98, ('venus', 'mars')),
    ('arcturus',           204.234, -0.281, -0.04, ('mars', 'jupiter')),
    ('princeps',           213.158,  0.187, 3.47, ('mercury', 'saturn')),
    ('alphecca',           222.296,  0.200, 2.23, ('venus', 'mercury')),     # the bridal crown
    ('zuben_elgenubi',     225.083, -0.081, 2.75, ('saturn', 'mars')),       # the Southern Scale
    ('zuben_eschamali',    229.372, -0.090, 2.61, ('jupiter', 'mercury')),   # the Northern Scale
    ('unukalhai',          232.075,  0.133, 2.65, ('saturn', 'mars')),
    ('agena',              233.792,  0.000, 0.61, ('venus', 'jupiter')),
    ('bungula',            239.479, -4.815, -0.27, ('venus', 'jupiter')),    # alpha Centauri
    ('yed_prior',          242.302,  0.000, 2.74, ('saturn', 'venus')),
    ('dschubba',           242.571,  0.000, 2.32, ('mars', 'saturn')),
    ('graffias',           243.190,  0.000, 2.62, ('mars', 'saturn')),
    ('han',                249.229,  0.000, 2.56, ('saturn', 'venus')),
    ('antares',            249.762,  0.000, 1.09, ('mars', 'jupiter')),      # ROYAL - Watcher West
    ('rastaban',           251.966, -0.076, 2.79, ('saturn', 'mars')),
    ('sabik',              257.970,  0.032, 2.43, ('saturn', 'venus')),
    ('ras_alhague',        262.449,  0.150, 2.08, ('saturn', 'venus')),
    ('lesath',             264.013,  0.000, 2.69, ('mercury', 'mars')),
    ('aculeus',            265.780,  0.000, 4.20, ('mars', 'moon')),         # M6, the Scorpion sting
    ('galactic_centre',    266.840,  0.000, 5.00, ('saturn', 'jupiter', 'pluto')),  # modern, not classical
    ('acumen',             268.713,  0.000, 3.30, ('mars', 'moon')),         # M7
    ('facies',             278.314,  0.000, 5.10, ('sun', 'mars')),          # M22, the Archer's face
    ('nunki',              282.385,  0.000, 2.05, ('jupiter', 'mercury')),
    ('vega',               285.316,  0.502, 0.03, ('venus', 'mercury')),
    ('altair',             301.776,  0.695, 0.77, ('mars', 'jupiter')),
    ('giedi',              303.769,  0.045, 3.57, ('venus', 'mars')),
    ('dabih',              304.047,  0.048, 3.05, ('saturn', 'venus')),
    ('sadalsuud',          323.395,  0.000, 2.90, ('saturn', 'mercury')),
    ('deneb_algedi',       323.543,  0.150, 2.85, ('saturn', 'jupiter')),
    ('sadalmelik',         333.352,  0.000, 2.95, ('saturn', 'mercury')),
    ('fomalhaut',          333.860,  0.249, 1.16, ('venus', 'mercury')),     # ROYAL - Watcher South
    ('deneb_adige',        335.329,  0.000, 1.25, ('venus', 'mercury')),
    ('achernar',           345.311,  0.066, 0.46, ('jupiter',)),
    ('markab',             353.486,  0.041, 2.48, ('mars', 'mercury')),
    ('scheat',             359.374,  0.268, 2.42, ('mars', 'mercury')),
]

# --- doctrinal groupings ---------------------------------------------------
# The four Persian Royal Stars, the Watchers of the four quarters: the tradition's most emphatic
# stars, read for both the greatest fortune and the sharpest fall.
ROYAL = frozenset(['aldebaran', 'regulus', 'antares', 'fomalhaut'])

# Agrippa's fifteen Behenian stars — the ones held to be usable, i.e. the operative canon.
BEHENIAN = frozenset([
    'algol', 'alcyone', 'aldebaran', 'capella', 'sirius', 'procyon', 'regulus', 'alkaid',
    'algorab', 'spica', 'arcturus', 'alphecca', 'antares', 'vega', 'deneb_algedi',
])

# Nebulae, clusters and cloudy places.  Every author from Ptolemy on reads these as the degrees of
# BLINDNESS — literal eye trouble, and figuratively a failure to see what is in front of one.  They
# are extended objects, so their orb is widened rather than narrowed despite their faintness.
NEBULA = frozenset([
    'capulus', 'alcyone', 'prima_hyadum', 'ain', 'praesepe', 'asellus_australis',
    'foramen', 'aculeus', 'acumen', 'facies',
])

# The marriage/union stars: the crown of Ariadne (Alphecca, the bridal garland), Mirach ("happy
# marriage, love of home"), Almach and Alpheratz (honour and love through Venus/Jupiter), Spica (the
# gift), Vega (charm), the Northern Scale (good fortune), the Twins (partnership), Giedi (sacrifice),
# Sadalsuud ("luckiest of the lucky") and Deneb Adige (the swan, Venus/Mercury).
MARRIAGE = frozenset([
    'alphecca', 'mirach', 'almach', 'alpheratz', 'spica', 'vega', 'zuben_eschamali',
    'castor', 'pollux', 'giedi', 'sadalsuud', 'deneb_adige',
])

# The separative stars: the ones whose delineation names PARTING, loss of a partner, disgrace
# through another, or forced change.  Vindemiatrix is literally "the Widow Maker"; Algol is
# beheading and severance; Ras Alhague is "misfortune through women"; Denebola is disgrace through
# others; Baten Kaitos is compulsory change and enforced emigration.
SEPARATIVE = frozenset([
    'algol', 'capulus', 'vindemiatrix', 'denebola', 'zosma', 'ras_alhague', 'scheat',
    'markab', 'zuben_elgenubi', 'rastaban', 'baten_kaitos', 'antares',
])

# The stars of violent or untimely DEATH.  This set is on the label's own axis: the outcome asked
# for is whether the relationship ended because a partner died, and this is the list the tradition
# would consult for exactly that question.
VIOLENT = frozenset([
    'algol', 'capulus', 'facies', 'aculeus', 'acumen', 'antares', 'aldebaran', 'bellatrix',
    'menkar', 'dschubba', 'graffias', 'rastaban', 'scheat', 'markab', 'alcyone', 'praesepe',
])

# Nature buckets, DERIVED from the planetary equivalences rather than hand-listed, so a star cannot
# land in the wrong one through a typo.  Both are deliberately PURE: benefic = of Jupiter and/or
# Venus with no malefic admixture, malefic = of Mars and/or Saturn with no benefic admixture.  The
# mixed stars (Antares of Mars and Jupiter, Algol of Saturn and Jupiter, Sirius of Jupiter and Mars,
# Spica of Venus and Mars) fall into NEITHER, which is exactly how the tradition reads them: great
# fortune carrying a great fall.  Mercury, the Sun and the Moon are neutral admixtures and do not
# move a star out of its class -- only a benefic mitigates a malefic and vice versa.  A loose
# "anything touching Mars or Saturn" malefic set would cover 61 of the 80 stars and be
# indistinguishable from the total star load, saying nothing.
def _is_benefic(nature):
    s = set(nature)
    return bool(s & {'jupiter', 'venus'}) and not (s & {'mars', 'saturn'})


def _is_malefic(nature):
    s = set(nature)
    return bool(s & {'mars', 'saturn'}) and not (s & {'jupiter', 'venus'})


def _star_orb(key, mag):
    """The orb a star is allowed, in degrees.

    Doctrine is emphatic that a star's orb is TIGHT (1-2 deg, never a planetary 5-8), and that it
    scales with brightness because brightness is the tradition's proxy for importance.  The Royals
    get the full 2 degrees; a nebula or cluster is an EXTENDED object several degrees wide on the
    sky, so it is floored at 1.5 rather than shrunk to its (faint) integrated magnitude."""
    if key in ROYAL:
        orb = 2.00
    elif mag <= 1.0:
        orb = 1.75
    elif mag <= 2.0:
        orb = 1.50
    elif mag <= 3.0:
        orb = 1.00
    else:
        orb = 0.75
    if key in NEBULA:
        orb = max(orb, 1.50)
    return orb


def _star_weight(key, mag):
    """How much a contact with this star counts.

    Linear in magnitude (brighter = louder), clipped so that no star vanishes and none dominates,
    then multiplied for the two canonical grades of importance: the Royal Stars carry far more
    weight than their brightness alone (Fomalhaut is only magnitude 1.16 yet is a Watcher), and the
    Behenians are the stars the tradition actually operates with."""
    w = float(np.clip(2.6 - 0.45 * mag, 0.5, 2.5))
    if key in ROYAL:
        w *= 1.50
    elif key in BEHENIAN:
        w *= 1.25
    return w


# Frozen, index-aligned arrays derived from the catalogue once, at import.
STAR_KEYS = [c[0] for c in CATALOG]
NS = len(STAR_KEYS)
STAR_LON0 = np.array([c[1] - AYANAMSA_J2000 for c in CATALOG], dtype=np.float64) % 360.0
STAR_PM = np.array([c[2] for c in CATALOG], dtype=np.float64)          # arcsec/yr in longitude
STAR_MAG = np.array([c[3] for c in CATALOG], dtype=np.float64)
STAR_ORB = np.array([_star_orb(c[0], c[3]) for c in CATALOG], dtype=np.float64)
STAR_W = np.array([_star_weight(c[0], c[3]) for c in CATALOG], dtype=np.float64)
STAR_IDX = {k: i for i, k in enumerate(STAR_KEYS)}

BENEFIC = frozenset([c[0] for c in CATALOG if _is_benefic(c[4])])
MALEFIC = frozenset([c[0] for c in CATALOG if _is_malefic(c[4])])

# The per-partner buckets emitted as max/min pairs.  Each is a weighted sum of every contact this
# partner's bodies make with the stars in the named set.
BUCKETS = [
    ('royal', ROYAL),
    ('behenian', BEHENIAN),
    ('nebula', NEBULA),
    ('marriage', MARRIAGE),
    ('separative', SEPARATIVE),
    ('violent', VIOLENT),
    ('benefic_nat', BENEFIC),
    ('malefic_nat', MALEFIC),
]

# Bodies whose star contacts get their own column: the classical carriers of a star's meaning.
CARRIERS = [
    ('sun', ['sun']),
    ('moon', ['moon']),
    ('venus', ['venus']),
    ('mars', ['mars']),
    ('saturn', ['saturn']),
    ('jupiter', ['jupiter']),
    ('node', ['true_node', 'true_south_node']),
]

# Named stars given their own columns.  HEAVY get both max and min over the couple (the min says
# "BOTH partners carry it", which is the stronger doctrinal statement); the rest get max only, so
# the column count stays honest to how much each star is actually read for.
HEAVY_STARS = ['algol', 'regulus', 'aldebaran', 'antares', 'fomalhaut', 'spica', 'alphecca', 'alcyone']
LIGHT_STARS = ['sirius', 'vega', 'arcturus', 'praesepe', 'capella', 'ras_alhague', 'scheat',
               'deneb_algedi', 'mirach', 'vindemiatrix']

# Synastry conjunction orb for the star-marked cross-chart contacts.  A planet-to-planet conjunction
# is a wide aspect (6 deg is standard practice); the TIGHT part of those features is the star mark
# the degree carries, not the conjunction itself.
CROSS_CONJ_ORB = 6.0
CHUNK = 8192       # rows per block in the (n, 14, 14) cross-grid pass, to bound peak memory


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _theta(Z, slot, half, n):
    """(n, 14) sidereal longitudes for one partner, columns in BODIES order.

    Resolved by NAME out of Z['bodies'] so a reordered npz cannot silently shuffle the bodies; a
    body missing from the npz becomes an all-NaN column, which keeps the returned width constant
    instead of dropping features on one half and not the other."""
    T = np.asarray(Z['theta_%s_%s' % (slot, half)], dtype=np.float64)
    if T.ndim != 2 or T.shape[0] != n:
        raise ValueError('theta_%s_%s has shape %r, expected (%d, k)' % (slot, half, T.shape, n))
    have = [str(x) for x in np.asarray(Z['bodies']).ravel().tolist()]
    where = {nm: i for i, nm in enumerate(have)}
    out = np.full((n, NB), np.nan, dtype=np.float64)
    for k, b in enumerate(BODIES):
        j = where.get(b)
        if j is not None and j < T.shape[1]:
            out[:, k] = T[:, j]
    return out


def _date_parts(s):
    """(year or nan, has_month_day) for the four legal shapes: 'YYYY-MM-DD', 'YYYY-00-00',
    '0000-MM-DD' (year unknown) and '0000-00-00' (absent).  Anything unparseable is absent.
    Nothing is inferred: a missing year is nan, never a default."""
    if not isinstance(s, str):
        return np.nan, False
    p = s.strip().split('-')
    if len(p) != 3:
        return np.nan, False
    y, m, d = p[0], p[1], p[2]
    yr = np.nan
    if y.isdigit() and int(y) > 0:
        yr = float(int(y))
    has_md = m.isdigit() and d.isdigit() and 0 < int(m) <= 12 and 0 < int(d) <= 31
    return yr, has_md


def _col(df, name, n):
    if name in df.columns:
        return df[name].tolist()
    return [None] * n


def _sep(lon, ref):
    """Undirected angular separation in [0, 180] between an (n, k) array and an (n,) reference.
    NaN propagates: an unknown longitude yields NaN, never 0 (which would read as 'exact')."""
    d = np.mod(lon - ref[:, None], 360.0)
    return np.minimum(d, 360.0 - d)


def _tri(dist, orb):
    """Triangular orb membership: 1 at exactitude, decaying linearly to 0 at the orb edge.
    np.maximum is used so NaN stays NaN rather than collapsing to 'no contact'."""
    return np.maximum(0.0, 1.0 - dist / orb)


def _guard(v, ok):
    """Force NaN wherever the partner had no usable longitude at all."""
    return np.where(ok, v, np.nan)


def _safe_div(num, den):
    """num/den with den <= 0 -> NaN (never a fabricated zero)."""
    num = np.asarray(num, dtype=np.float64)
    den = np.asarray(den, dtype=np.float64)
    out = np.full(num.shape, np.nan, dtype=np.float64)
    good = den > 0
    np.divide(num, np.where(good, den, 1.0), out=out, where=good)
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

    def add_pair(base, va, vb):
        """Emit a per-partner quantity order-free.  np.maximum/np.minimum PROPAGATE NaN on purpose:
        np.fmax would quietly substitute the known partner for the unknown one, which would let the
        model read a one-sided chart as if it were the couple's."""
        add(base + '_max', np.maximum(va, vb))
        add(base + '_min', np.minimum(va, vb))

    A = _theta(Z, 'a', half, n)
    B = _theta(Z, 'b', half, n)

    body_w = np.array([BODY_W[b] for b in BODIES], dtype=np.float64)
    slow_mask = np.array([b in SLOW for b in BODIES], dtype=bool)

    finA = np.isfinite(A)
    finB = np.isfinite(B)
    nvA = finA.sum(axis=1).astype(np.float64)
    nvB = finB.sum(axis=1).astype(np.float64)
    okA = nvA > 0
    okB = nvB > 0

    # --- birth years -> the era each star position is evaluated for -------------------------
    pa = [_date_parts(s) for s in _col(df, 'dob_a', n)]
    pb = [_date_parts(s) for s in _col(df, 'dob_b', n)]
    yrA = np.array([p[0] for p in pa], dtype=np.float64)
    yrB = np.array([p[0] for p in pb], dtype=np.float64)
    mdA = np.array([p[1] for p in pa], dtype=np.float64)
    mdB = np.array([p[1] for p in pb], dtype=np.float64)
    # Where the year is unknown the era falls back to J2000.  That is not a fabricated date: it is
    # simply the epoch of the catalogue, and every longitude on such a row is NaN anyway, so no
    # feature can be computed from it.  Clipped to a sane span so a corrupt year cannot move a star
    # by tens of degrees.
    eraA = np.where(np.isfinite(yrA), np.clip(yrA, 1000.0, 2200.0), 2000.0)
    eraB = np.where(np.isfinite(yrB), np.clip(yrB, 1000.0, 2200.0), 2000.0)

    # ---------------- accumulators, one set per partner ----------------
    def _acc():
        return dict(
            total=np.zeros(n), total_slow=np.zeros(n),
            wmax=np.full(n, -np.inf),
            hits=np.zeros(n), nstars=np.zeros(n), nstars_slow=np.zeros(n),
            min_any=np.full(n, np.inf), min_royal=np.full(n, np.inf),
            bucket={b: np.zeros(n) for b, _ in BUCKETS},
            carrier={c: np.zeros(n) for c, _ in CARRIERS},
            named={k: np.zeros(n) for k in set(HEAVY_STARS) | set(LIGHT_STARS)},
            mark=np.full((n, NB), -np.inf),          # strongest star weight on each body's degree
            mark_royal=np.full((n, NB), -np.inf),
            mark_mal=np.full((n, NB), -np.inf),
            mark_ben=np.full((n, NB), -np.inf),
            mark_neb=np.full((n, NB), -np.inf),
            C=np.zeros((n, NS), dtype=np.float32),   # per-star contact profile (for the pair block)
        )

    accA, accB = _acc(), _acc()
    carrier_idx = {c: [BODIES.index(b) for b in bl] for c, bl in CARRIERS}
    same_body_same_star = np.zeros(n)                # G11, accumulated inside the star loop

    # ---------------- ONE pass over the catalogue, both partners together ----------------
    for k in range(NS):
        key = STAR_KEYS[k]
        orb = STAR_ORB[k]
        w = STAR_W[k]
        in_royal = key in ROYAL
        in_bucket = {b: (key in s) for b, s in BUCKETS}
        t_pair = []
        for acc, TH, fin, era in ((accA, A, finA, eraA), (accB, B, finB, eraB)):
            # The star's sidereal longitude for THIS birth year: J2000 sidereal position plus the
            # star's own proper motion in longitude.  Precession is absent by construction — it is
            # exactly what the sidereal frame has already removed.
            lam = np.mod(STAR_LON0[k] + STAR_PM[k] * (era - 2000.0) / 3600.0, 360.0)
            d = _sep(TH, lam)                        # (n, 14), NaN where the body is unknown
            t = _tri(d, orb)                         # (n, 14) membership in [0, 1], NaN preserved
            contrib = w * body_w[None, :] * t
            t_pair.append(np.where(fin, t, 0.0))

            cz = np.where(fin, contrib, 0.0)
            acc['total'] += cz.sum(axis=1)
            acc['total_slow'] += cz[:, slow_mask].sum(axis=1)
            acc['wmax'] = np.maximum(acc['wmax'], np.where(fin, contrib, -np.inf).max(axis=1))

            hit = np.where(fin, t, 0.0) > 0.0
            acc['hits'] += hit.sum(axis=1)
            any_hit = hit.any(axis=1)
            acc['nstars'] += any_hit
            acc['nstars_slow'] += hit[:, slow_mask].any(axis=1)

            dz = np.where(fin, d, np.inf)
            dmin = dz.min(axis=1)
            acc['min_any'] = np.minimum(acc['min_any'], dmin)
            if in_royal:
                acc['min_royal'] = np.minimum(acc['min_royal'], dmin)

            for b, _ in BUCKETS:
                if in_bucket[b]:
                    acc['bucket'][b] += cz.sum(axis=1)
            for c, idx in carrier_idx.items():
                acc['carrier'][c] += (w * np.where(fin[:, idx], t[:, idx], 0.0)).sum(axis=1)
            if key in acc['named']:
                acc['named'][key] += cz.sum(axis=1)

            marked = np.where(fin, w * t, -np.inf)   # star weight on the degree, body-independent
            acc['mark'] = np.maximum(acc['mark'], marked)
            if in_royal:
                acc['mark_royal'] = np.maximum(acc['mark_royal'], marked)
            if key in MALEFIC:
                acc['mark_mal'] = np.maximum(acc['mark_mal'], marked)
            if key in BENEFIC:
                acc['mark_ben'] = np.maximum(acc['mark_ben'], marked)
            if key in NEBULA:
                acc['mark_neb'] = np.maximum(acc['mark_neb'], marked)

            acc['C'][:, k] = np.where(fin, contrib, 0.0).max(axis=1).astype(np.float32)

        # G11: the SAME body of both partners on the SAME star (both Venuses on Spica, both Moons on
        # Algol).  This is the tradition's strongest "shared fate" statement, and it is symmetric in
        # the two partners because the product is.
        same_body_same_star += (w * body_w[None, :] * t_pair[0] * t_pair[1]).sum(axis=1)

    # tidy the sentinel-initialised accumulators and mask rows with no usable chart
    for acc, ok in ((accA, okA), (accB, okB)):
        acc['wmax'] = _guard(np.where(np.isfinite(acc['wmax']), acc['wmax'], 0.0), ok)
        acc['min_any'] = _guard(np.where(np.isfinite(acc['min_any']), acc['min_any'], np.nan), ok)
        acc['min_royal'] = _guard(np.where(np.isfinite(acc['min_royal']), acc['min_royal'], np.nan), ok)
        for key in ('total', 'total_slow', 'hits', 'nstars', 'nstars_slow'):
            acc[key] = _guard(acc[key], ok)
        for b in acc['bucket']:
            acc['bucket'][b] = _guard(acc['bucket'][b], ok)
        for c in acc['carrier']:
            acc['carrier'][c] = _guard(acc['carrier'][c], ok)
        for s in acc['named']:
            acc['named'][s] = _guard(acc['named'][s], ok)
        for m in ('mark', 'mark_royal', 'mark_mal', 'mark_ben', 'mark_neb'):
            acc[m] = np.where(np.isfinite(acc[m]), acc[m], 0.0)
            acc[m] = np.where(acc[m] > 0.0, acc[m], 0.0)
        acc['C'] = np.where(ok[:, None], acc['C'], np.nan)

    # ================================================================================
    # GROUP A — coverage census (4).  NOT a doctrinal claim: these say only how much of the
    # doctrine below COULD be evaluated, so the model can tell "no star contact" apart from "no
    # birth date".  Counts over the two partners, never per-slot, so they stay order-free.
    # ================================================================================
    add('fs_cov_bodies_max', np.maximum(nvA, nvB))     # bodies with a known longitude, wider chart
    add('fs_cov_bodies_min', np.minimum(nvA, nvB))     # ... and the thinner one
    add('fs_prec_n_year', np.isfinite(yrA).astype(float) + np.isfinite(yrB).astype(float))
    add('fs_prec_n_daymonth', mdA + mdB)               # how many dobs resolve the fast bodies

    # ================================================================================
    # GROUP B — how heavily each chart is written on by the fixed stars (24).
    # "total" is the whole weighted star load; "wmax" the single loudest contact; "hits" and
    # "nstars" the extent of it.  Then the doctrinal sets: Royal, Behenian, the nebulae of
    # blindness, the marriage stars, the separative stars, the stars of violent death, and the two
    # nature buckets.  Each emitted as max/min over the couple.
    # ================================================================================
    add_pair('fs_total', accA['total'], accB['total'])
    add_pair('fs_loudest', accA['wmax'], accB['wmax'])
    add_pair('fs_n_hits', accA['hits'], accB['hits'])
    add_pair('fs_n_stars', accA['nstars'], accB['nstars'])
    for b, _ in BUCKETS:
        add_pair('fs_' + b, accA['bucket'][b], accB['bucket'][b])

    # ================================================================================
    # GROUP C — the tightest orbs (4).  Doctrine reads exactitude, not membership: a planet 6' from
    # Algol is a different statement from one 1.5 deg away.  Emitted as the couple's minimum (the
    # single tightest contact anywhere in the pair) and maximum-of-minima (how loose the LOOSER
    # partner's tightest contact is) — both symmetric under swapping the partners.
    # ================================================================================
    add('fs_orb_any_pairmin', np.minimum(accA['min_any'], accB['min_any']))
    add('fs_orb_any_pairmax', np.maximum(accA['min_any'], accB['min_any']))
    add('fs_orb_royal_pairmin', np.minimum(accA['min_royal'], accB['min_royal']))
    add('fs_orb_royal_pairmax', np.maximum(accA['min_royal'], accB['min_royal']))

    # ================================================================================
    # GROUP D — WHICH body carries the stars (14).  The tradition's reading turns entirely on this:
    # a star on the Moon is a fate in the feelings, on Mars a fate in the actions, on Saturn a fate
    # in the endings.  Weighted star contact per carrier, max/min over the couple.
    # ================================================================================
    for c, _ in CARRIERS:
        add_pair('fs_carrier_' + c, accA['carrier'][c], accB['carrier'][c])

    # ================================================================================
    # GROUP E — the named stars (26).  The eight HEAVY ones get max AND min: the min is the strong
    # claim that BOTH partners carry that star, which is what a synastry reading would remark on.
    # The ten lighter ones get max only.
    # ================================================================================
    for s in HEAVY_STARS:
        add_pair('fs_star_' + s, accA['named'][s], accB['named'][s])
    for s in LIGHT_STARS:
        add('fs_star_%s_max' % s, np.maximum(accA['named'][s], accB['named'][s]))

    # ================================================================================
    # GROUP F — the slow-body-only star load (4).  Jupiter outward plus the nodes, Chiron and
    # Lilith resolve from a birth YEAR alone, so these two are computable on every row that has a
    # year and cannot be confounded with whether the day was recorded.
    # ================================================================================
    add_pair('fs_total_slow', accA['total_slow'], accB['total_slow'])
    add_pair('fs_n_stars_slow', accA['nstars_slow'], accB['nstars_slow'])

    # ================================================================================
    # GROUP G — the PAIR block: stars the two charts hold in common (13).
    # A shared star is the classical statement that two people are written on by the same fate.
    # C_a and C_b are each partner's (n, 80) star profile — the strongest weighted contact any of
    # their bodies makes with each star — so every statistic below is a symmetric function of the
    # two profiles and cannot learn column order.
    # ================================================================================
    Ca = accA['C'].astype(np.float64)
    Cb = accB['C'].astype(np.float64)
    both = np.minimum(Ca, Cb)                          # NaN if either partner is unusable
    either = np.maximum(Ca, Cb)
    star_w = STAR_W[None, :]

    add('fs_shared_count', (both > 0).sum(axis=1).astype(float) * np.where(okA & okB, 1.0, np.nan))
    add('fs_shared_weighted', (star_w * both).sum(axis=1))
    add('fs_shared_max', both.max(axis=1))
    for tag, s in (('royal', ROYAL), ('nebula', NEBULA), ('marriage', MARRIAGE),
                   ('separative', SEPARATIVE), ('violent', VIOLENT)):
        idx = [STAR_IDX[x] for x in s]
        add('fs_shared_' + tag, (star_w[:, idx] * both[:, idx]).sum(axis=1))

    # Direction vs magnitude of the two star profiles: the cosine says "written on by the same
    # stars", the dot product says "written on strongly by the same stars", and the L1 difference
    # says the opposite — how far apart the two stellar signatures are.
    na = np.sqrt((Ca * Ca).sum(axis=1))
    nb = np.sqrt((Cb * Cb).sum(axis=1))
    dot = (Ca * Cb).sum(axis=1)
    add('fs_profile_cos', _safe_div(dot, na * nb))     # NaN when a chart touches no star at all
    add('fs_profile_dot', dot)
    add('fs_profile_absdiff', np.abs(Ca - Cb).sum(axis=1))
    add('fs_same_body_same_star', _guard(same_body_same_star, okA & okB))
    add('fs_shared_jaccard', _safe_div((both > 0).sum(axis=1).astype(float),
                                       (either > 0).sum(axis=1).astype(float)))

    # ================================================================================
    # GROUP H — star-MARKED synastry (10).  This is the "one partner's planets on the other's
    # star-marked degrees" reading: a cross-chart conjunction is not neutral, it inherits the
    # character of the degree it falls in.  mark[i] is the strongest star weight sitting on body i's
    # degree; a cross conjunction between A's body i and B's body j is weighted by the louder of the
    # two marks, which is symmetric under transposing the grid (i.e. under swapping the partners).
    # ================================================================================
    add_pair('fs_markdeg', accA['mark'].max(axis=1) * np.where(okA, 1.0, np.nan),
             accB['mark'].max(axis=1) * np.where(okB, 1.0, np.nan))

    lum = [BODIES.index('sun'), BODIES.index('moon')]
    vm = [BODIES.index('venus'), BODIES.index('mars')]
    xs = {k: np.zeros(n) for k in ('total', 'royal', 'malefic', 'benefic', 'nebula', 'lum', 'vm')}
    xmax = np.full(n, -np.inf)
    xcnt = np.zeros(n)
    for s0 in range(0, n, CHUNK):
        s1 = min(n, s0 + CHUNK)
        a = A[s0:s1]
        b = B[s0:s1]
        fa = finA[s0:s1]
        fb = finB[s0:s1]
        d = np.mod(a[:, :, None] - b[:, None, :], 360.0)
        d = np.minimum(d, 360.0 - d)
        conj = np.maximum(0.0, 1.0 - d / CROSS_CONJ_ORB)
        good = fa[:, :, None] & fb[:, None, :]
        conj = np.where(good, conj, 0.0)
        xcnt[s0:s1] = good.reshape(s1 - s0, -1).sum(axis=1)
        for tag, ma, mb in (('total', accA['mark'], accB['mark']),
                            ('royal', accA['mark_royal'], accB['mark_royal']),
                            ('malefic', accA['mark_mal'], accB['mark_mal']),
                            ('benefic', accA['mark_ben'], accB['mark_ben']),
                            ('nebula', accA['mark_neb'], accB['mark_neb'])):
            mk = np.maximum(ma[s0:s1][:, :, None], mb[s0:s1][:, None, :])
            v = conj * mk
            xs[tag][s0:s1] = v.reshape(s1 - s0, -1).sum(axis=1)
            if tag == 'total':
                xmax[s0:s1] = v.reshape(s1 - s0, -1).max(axis=1)
                # the luminary sub-grid (the marriage contact) and the Venus/Mars sub-grid
                # (attraction), each a full 2x2 over the ordered pair, hence swap-symmetric
                xs['lum'][s0:s1] = v[:, lum][:, :, lum].reshape(s1 - s0, -1).sum(axis=1)
                xs['vm'][s0:s1] = v[:, vm][:, :, vm].reshape(s1 - s0, -1).sum(axis=1)

    xok = xcnt > 0
    add('fs_xstar_total', _guard(xs['total'], xok))
    add('fs_xstar_max', _guard(np.where(np.isfinite(xmax), xmax, 0.0), xok))
    add('fs_xstar_royal', _guard(xs['royal'], xok))
    add('fs_xstar_malefic', _guard(xs['malefic'], xok))
    add('fs_xstar_benefic', _guard(xs['benefic'], xok))
    add('fs_xstar_nebula', _guard(xs['nebula'], xok))
    add('fs_xstar_luminary', _guard(xs['lum'], xok))
    add('fs_xstar_venus_mars', _guard(xs['vm'], xok))

    if n == 0:
        X = np.zeros((0, len(names)), dtype=np.float32)
    else:
        X = np.column_stack(cols).astype(np.float32)
    if X.shape[1] != len(names):
        raise AssertionError('width %d != %d names' % (X.shape[1], len(names)))
    return X, names
