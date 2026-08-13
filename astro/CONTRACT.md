# Tradition module contract

You are writing ONE file: `/Users/arash/Studio/artamatch/astro/trad_<slug>.py`.

Its job is to turn charts into numeric feature blocks for a marriage-outcome classifier. Nothing else.
No scoring tables, no model selection, no commentary on confounds, no baselines. Features only.

## Run everything with

```
cd /Users/arash/Studio/artamatch/astro && /tmp/aqpy/bin/python trad_<slug>.py
```

`/tmp/aqpy/bin/python` has numpy, scipy, scikit-learn, pyswisseph, astropy. Nothing else — do not pip
install. Swiss Ephemeris files are at `~/.sweph/ephe` and `core.py` already calls `set_ephe_path`.

## The interface, exactly

```python
TRADITION = "Hellenistic (Ptolemy, Vettius Valens, Dorotheus)"   # human-readable, one line

def build(E) -> dict[str, numpy.ndarray]:
    """name -> (E.n, k) float64, every value finite."""
```

Rules that are checked and will fail you:

- Every array is `(E.n, k)`, `float64`, and fully finite. No NaN, no inf, no object arrays.
- Block names are unique and prefixed with a short tradition tag, e.g. `"hel: ptolemaic orbs 6deg"`.
- **Never touch `E.Y`.** Not for feature construction, not for binning, not for scaling. Using the
  target to build a feature is the one unrecoverable error here.
- No I/O beyond reading `core`; no network; no writing files other than your own module.
- Deterministic. Same input, same output, every run. Seed anything random.
- Keep total columns across your blocks under about 6,000, and prefer several focused blocks to one
  enormous one — blocks are scored separately and then ensembled, so a well-named narrow block is worth
  more than a giant undifferentiated one.

## What `core.load()` gives you

```python
from core import load
E = load()
```

| attribute | shape | meaning |
|---|---|---|
| `E.n` | int | number of couples (2,296) |
| `E.Y` | (n,) | **the target — off limits** |
| `E.JD` | (6, n) | julian day of each instant slot |
| `E.LON` | (6, 18, n) | tropical ecliptic longitude, degrees |
| `E.LAT` | (6, 18, n) | ecliptic latitude, degrees |
| `E.DIST` | (6, 18, n) | distance, AU |
| `E.SPD` | (6, 18, n) | longitude speed, deg/day — **negative means retrograde** |
| `E.DEC` | (6, 18, n) | declination, degrees |
| `E.RA` | (6, 18, n) | right ascension, degrees |
| `E.HELIO` | (6, 18, n) | heliocentric longitude, degrees |
| `E.AYA` | (21, 6, n) | ayanamsa value per mode per instant |
| `E.gid` | (n,) | person-group id (used for splits; you do not need it) |

Instant slots — index with `E.SLOT["wedding"]` or the literal:

| 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| older's birth | younger's birth | wedding | older's secondary progression to the wedding | younger's progression | Davison (midpoint in time between births) |

Bodies, in order, index with `E.IDX["Venus"]`:

`Sun Moon Mercury Venus Mars Jupiter Saturn Uranus Neptune Pluto TrueNode MeanNode Lilith Chiron Ceres Pallas Juno Vesta`

Also available: `E.CLASSICAL` (the seven visible bodies), `E.MODERN` (ten), `E.PERIOD[name]` (sidereal
period in years), `E.AYA_NAME` (21 ayanamsa names).

Helpers on `E`:

```python
E.sidereal("Lahiri")      # (6, 18, n) sidereal longitudes for any of the 21 ayanamsas
E.wrap(d)                 # signed angular difference in (-180, 180]
E.sep(a, b)               # absolute separation in [0, 180]
E.circ(lon)               # cos/sin pair, stacked on the last axis
E.orbkern(sep, angle, w)  # Gaussian aspect kernel, 1 at exact
```

## The hard data limit — read this before designing features

Only birth **dates** are known, never times or places. Everything is computed at 12:00 UT. Therefore:

- **No Ascendant, no Midheaven, no houses.** Any tradition resting on them cannot be computed. You may
  use a documented zodiacal proxy (e.g. treat the Sun's sign as the first place, "solar whole-sign"),
  but the docstring must say plainly that it is a proxy and why.
- **The Moon is uncertain by roughly ±6°.** Sign-level lunar features are ~half reliable; nakshatra
  (13°20′) or lunar-mansion features are worse. Still build them — several traditions are entirely
  lunar — but note the limitation in the docstring.
- Anything needing a birth *time of day* (Chinese hour pillar, exact tithi at birth, Vedic birth-time
  dasha balance) can only be approximated at noon. Say so where you do it.

## Representation guidance — this is where the value is

The same tradition can be encoded many ways and they score very differently. Build several:

- **Circular**: `cos`/`sin` of a longitude or of a difference. Smooth, linear-model friendly.
- **Aspect kernels**: `E.orbkern(sep, angle, width)` at the tradition's own angles and orbs. Try 2–3
  orb widths — orb choice is itself a tradition-specific parameter.
- **Discrete bins**: one-hot of sign / nakshatra / branch / day-sign. Interaction-heavy; trees and
  kernels see these, linear models mostly cannot.
- **Pair interactions**: for a pairing tradition, the *pair* of categories matters, not each alone.
  A 27×27 nakshatra pair one-hot is 729 mostly-empty columns; better is a small set of derived scores
  (the tradition's own compatibility table) plus a low-rank encoding of the pair.
- **Tradition's own scores**: if the tradition computes a number (Ashtakoot's 36 points, a porutham
  count, an element-clash tally), compute exactly that number the way the tradition does. These are the
  most valuable features in the whole exercise — they are what the tradition actually claims.
- **Both directions**: many pairing rules are asymmetric (bride vs groom). We do not know sex, so use
  older/younger, and where a rule is asymmetric emit both orderings.

## Self-test, required

End your file with a `__main__` block that:

1. loads `core`, calls `build(E)`,
2. asserts every block's shape, dtype, finiteness, and that no block is all-constant,
3. prints one line per block: name, columns, and a fast score from
   `from evalx import quick; quick(E, X)` — this returns `(accuracy, auc)`,
4. exits non-zero on any assertion failure.

Run it. Iterate until it passes and every block prints. A module that does not run is worth nothing.
Report at the end: the block names, their column counts, and their quick scores.

---

## Addendum — the input contract, and what it now permits

The deployed model may see **only four things**, any of which may be missing:

    partner A: date of birth, place of birth (latitude, longitude)
    partner B: date of birth, place of birth (latitude, longitude)

Anything **derived** from those four is permitted. Citizenship, sex, marriage dates and nationality are NOT
inputs — do not build features from them.

### Two things this unlocks that earlier modules could not do

**PLACE IS NOW AVAILABLE AS REAL COORDINATES.** `E.LAT_O`, `E.LON_O`, `E.LAT_Y`, `E.LON_Y` carry each
partner's birthplace latitude and longitude (NaN when unknown — always emit a companion "known" flag rather
than imputing). Coordinates are present for the older partner in 75.1% of couples, the younger in 66.3%,
and both in 53.3%. This makes computable, for the first time in this project: the Ascendant, Midheaven and
house cusps; the Vertex and East Point; local sidereal time; parans (a star rising, culminating or setting
at the moment of birth); Local Space and Astro*Carto*Graphy directions; and topocentric rather than
geocentric positions.

**THE UNKNOWN BIRTH HOUR IS MARGINALISED, NOT GUESSED.** There is no birth time, so anything needing one is
computed at all **12 two-hour slots** and averaged — which is the Chinese double-hour, and also the correct
expectation under a uniform prior. `core.py` provides this:

```python
E.hours(slot)                  # (NB, 12, n) longitudes at all 12 slot centres
E.soft_bins(slot, body, nbins) # fraction of the 12 hours placing a body in each bin — a DISTRIBUTION
E.entropy(p)                   # how undecided that distribution is, in bits
```

Emit the **distribution and its entropy**, not a point estimate: "8 of 12 hours put the Moon in Hasta and
4 in Chitra" is strictly more information than picking one, and it is honest about what is unknown.

Be aware of the limit this imposes, and state it where it bites: under a uniform hour prior the Ascendant is
very nearly uniform over the zodiac by construction, because it cycles once per day. So an Ascendant
*marginal* carries little on its own — but Ascendant-dependent quantities that are NOT uniform (which house
a planet falls in, whether a star was rising, the Vertex relative to a planet) still carry information, and
those are worth building. Say which case you are in.

### Reliability weighting is already handled

`ctx_precision.py` computes, per body per partner, the exact attenuation `sin(x)/x` with `x = ω·W/2` for a
date known only to a month or a year, or not at all. You do not need to duplicate that — build your features
from the dates you are given and let that module express how much each is worth. For reference, at
year precision the Sun and Moon are destroyed (attenuation ~0.00) while Jupiter outward survive intact
(0.99–1.00).
