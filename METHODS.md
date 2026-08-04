# How ArtaMatch works — the full method

Everything the page computes, how each piece was verified, and where every embedded number comes
from. The [README](README.md) is the summary; this is the reference. Nothing here is needed to *use*
the page — it exists so that any claim on the page can be checked by a stranger.

---

## 1 · The positions

A dependency-free ephemeris (`src/engine/ephemeris.ts`) places the Sun, Moon and eight planets on
the ecliptic for any date between 1800 and 2100, in the constellation-aligned (sidereal, Lahiri)
frame the Moon-score tradition uses.

| Piece | Method | Source |
|---|---|---|
| Moon | 45-term truncated ELP-2000/82 series + nutation | Meeus, *Astronomical Algorithms*, ch. 47 |
| Planets | Keplerian elements, Table 1 | JPL/Standish, *Approximate Positions of the Planets* |
| Zodiac offset | Quadratic fit to Swiss Ephemeris SIDM_LAHIRI | `tools/fit-ayanamsa.py` |

**Verification** is against the Swiss Ephemeris (`pyswisseph`), the reference implementation used by
professional software — twice, with independent samples:

- `tests/golden.json`: 1,975 dates, every 37 days, 1900–2100, plus hourly Moon positions across
  whole days. Runs in CI on every push (`tests/ephemeris.test.ts`).
- A second, unseen sample (step 43, offset start, different Moon days, including 2050) was run
  during review and passed every tolerance.

Measured worst-case error, in arcminutes: Sun 0.8, **Moon 1.4**, Mercury 1.2, Venus 1.4, Mars 3.1,
Jupiter 10.4, Saturn 22.3, Uranus 3.8, Neptune 1.9, Pluto 1.3. The zodiac offset reproduces Swiss
Ephemeris to 1e-8°. JPL's longer-range Table 2a was tried for the outer planets and **measured
worse** over 1900–2100 (`tools/compare-elements.mjs`) — it is fitted across six millennia and is
looser inside any one century.

Only the Moon's accuracy bears on the score — the eight tests read nothing else. Mars and Venus are
computed because they feed one of the three warnings. At 1.4′ the Moon is some 280× finer than the
±6.6° the missing birth time costs, which is the whole reason the uncertainty model matters more
than the ephemeris does.

## 2 · What a date alone can and cannot say

The Moon moves 11.8–15.4° a day; a birth star is 13°20′ wide and a sign 30°. Without a birth time
(taken as a UT day — the zone is unknown too, and saying so is part of the method):

| Quantity | Chance the noon guess is wrong |
|---|---|
| Moon sign | ~11% |
| Birth star | ~25% |
| Finer divisions | not attempted — the error swallows them |

Instead of guessing, `src/engine/uncertainty.ts` finds every (birth star, sign, mid-sign half) state
the Moon occupies during the day — at most four; `1965-07-27` reaches the ceiling — by hourly scan
plus bisection to the second. Each state's share of the day **is** its probability under a flat
prior, so the page enumerates every possible reading exactly, with its chance.

**This is exact, and it was checked against brute force.** The eight tests read the Moon *only*
through those three quantities, so the ≤16 state combinations are the whole distribution. Compared
against sweeping the actual hour grid, the exact method agrees with a 240×240 sweep (57,600 hour
pairs) to within **0.15 percentage points** — while a 24×24 sweep is off by up to **1.3 points**,
because 24 samples per day straddle the boundaries rather than finding them. The page therefore
computes the interval exactly and *draws* the 24×24 hour grid as the explanation, rather than
sampling the grid to get the number.

Every prediction carries the result: the **expected** score (the probability-weighted mean, and the
right thing to rank on), the **narrowest 90% interval**, the **full support**, and the single **most
likely** reading with its probability. There is one code path — a `detailed` flag once let ranking
skip the distribution, which meant the ranking and the report could quietly disagree. The displayed chart is taken at
the middle of the most likely state, *not* at noon: measured over 7,200 dates, noon disagrees with
the most likely reading on about 6% of days (the birth star alone on roughly 3%, the star-or-sign on
roughly 6%), which once made the page show one birth star and score another.

The rising point ("ascendant") moves a sign every two hours; nothing that needs it is computed, ever
— it is refused rather than defaulted.

## 3 · The Moon score (out of 36)

The traditional eight-test system, `src/engine/kuta.ts`. Each test returns its points, the exact
values it read, and the rule that produced them. The reference tables were reconstructed three times
independently, reconciled against primary sources (Saravali, BPHS, the Muhurta Chintamani lineage,
Drik Panchang), and are pinned by structural invariants in `tests/nakshatra.test.ts` — nine stars
per temperament, the period-6 constitution cycle, the animal census (13 pairs + one unpaired), the
seven canonical enemy pairs. That process caught a real transcription error worth 4 of the 36 points
(see README, "What triple-checking found").

Three of the eight tests are asymmetric in the tradition (written for a groom and a bride). Both
orderings are always computed and the mean used, because a ranked list must be symmetric —
`score(A,B) = score(B,A)` is asserted over hundreds of random pairs.

The first test ranks four temperaments in an order inherited from a caste hierarchy. It is named
plainly, worth 1 point, and can be switched off — in which case the score is compared against a
**separately calibrated** 35-point distribution, not the 36-point one.

## 4 · Calibration — what a score is worth

Every raw score is placed against the distribution of 20,000 random date pairs
(`tools/calibrate.mjs`, fixed seed, reproducible to the digit). This is the page's central honesty
device: the traditional "pass mark" of 18 is cleared by **71%** of random pairs, and the median pair
scores **21**, so "you passed" would be flattery. Percentile bands ("Above average", "High") are set
on the measured distribution. A drift test (in `tests/score.test.ts`) recomputes a 2,000-pair sample
in CI and fails if the embedded numbers go stale.

## 5 · The two charts, and the connections between them

### 5.1 · One person's chart (`src/engine/natal.ts`)

A full natal chart has three layers: which **sign** each planet is in, which **house** it is in, and
which sign was **rising**. Only the first survives a missing birth time — houses and the rising sign
turn a full circle every 24 hours, so from a date alone they are not approximate, they are *unknown*.
This file draws the layer that survives, and the page says the other two are missing rather than
quietly defaulting them to sunrise, which is the usual dodge.

Even the surviving layer has edges: a planet near a boundary at midnight is in two signs that day. So
every body reports the signs it could be in **and the share of the day it spent in each**, found
exactly — an hourly scan for a change, then bisection inside the hour that changed. The Moon does
this on about two days in five; Mercury moves at most ~2.2° in a day and Saturn ~0.13°, so theirs is
settled unless the date lands on the crossing itself.

**Five bodies get a paragraph** — Sun, Moon, Mercury, Venus, Mars. Jupiter holds a sign for about a
year and Saturn for two and a half, so a *reading* of them would describe everyone born that year;
they are drawn, they make connections, and they get a stated placement rather than a character
sketch. Uranus, Neptune and Pluto (7, 14 and 12–30 years to a sign) get their windows named and
nothing else.

### 5.2 · Where two charts touch (`src/engine/synastry.ts`)

Seven bodies (Sun … Saturn) make connections; the three slowest do not, because "your Pluto is
opposite my Sun" is true of everyone born in a twenty-year window — a fact about a generation, not
about two people.

**How close counts as close** is a *convention*, and is labelled as one on the page: 8° when the Sun
or the Moon is involved, 6° otherwise, for all five angles. No measurement could settle it.

**The method is 576 charts.** `synastryGrid` draws both charts once for every combination of the two
unknown birth hours and reports every quantity as a mean, a standard deviation and a 5th-to-95th
band: the angle between each pair of bodies, how far that angle sits from the exact one, and how
many connections the two charts have at all.

**Verified three ways.** A closed form is kept in the same file and renders nothing — it exists to
check the grid. Under a flat prior over birth times each longitude is nearly uniform over its day's
arc, so the angle between two of them is a **difference of two uniforms**, a trapezoid with an exact
area. `tests/synastry.test.ts` holds all three against each other:

| | worst disagreement |
|---|---|
| closed form vs 240×240 brute force (57,600 hour pairs) | **0.06 pp** |
| 24×24 grid vs closed form | **1.9 pp**, on a connection sitting exactly on the edge of its orb |

The closed form's own residual came down 30× (1.73 pp → 0.06 pp) when each body's day was cut into
twelve pieces instead of treated as one straight arc: Mercury near a turn decelerates to a standstill
and back, so it lingers at one end of its arc and races the other.

**Ordering.** Connections are ranked by **strength** — the average, over all 576 charts, of how close
the angle is as a fraction of the orb, counting a chart where it misses as nothing. Ranking by
*probability* was tried and thrown away: probability is a fact about how slowly the planets move, so
the six slowest pairs won every time and the Moon — the most personal body there is, and the one the
entire score is built from — could never appear at all. A test asserts the Moon now reaches the
narrated list on more than 30% of pairs, and that no single planet fills more than two of the six.

### 5.3 · Why the connections are not scored

Measured over the same 20,000 random pairs (`tools/calibrate-synastry.mjs`, seed 13579):

| | |
|---|---|
| connections per pair | median **15**, 5th–95th **10.5 – 20.2** |
| correlation with the eight-test score | **0.030** |

So the *count* measures nothing — everybody has about fifteen — and the two traditions, handed the
same two dates, do not agree with each other. The page prints both facts before the first connection
and then shows **which** connections rather than how many. That is what lets a second system sit
beside a scored one without becoming a rival scoreboard.

(A sanity check that falls out of the same run: the three angles reachable from either side —
60°, 90°, 120° — occur ~3.8 times per pair, and the two that are not — 0° and 180° — occur ~1.9,
almost exactly half, which is what the geometry demands.)

## 5.4 · Removed experiments

All worked, all were verified, all were deleted. They are in the git history.

**The ensemble.** Three other date-only traditions (date-digit numerology, the twelve-year animal
cycle, Sun-sign elements), each calibrated the same way, averaged into one percentile. Removed
because four half-explained numbers teach less than one fully explained one.

**The first aspect layer.** Written readings for all 55 body pairs in four configurations, sitting
beside the score as unscored commentary. Removed because it invited "is 19 connections good?" and
could not answer it. The layer above is its replacement, and the difference is §5.3: the question now
has a measured answer, and every sentence carries the spread of the 576 charts behind it.

**The sky ruler.** A linear 360° band with both Moons and their daily arcs. Cut because the *score*
depends only on the relationship between the two Moons, never on where they sit absolutely, so it
drew data no test reads. The chart in §5.1 is a different object with a different job: it shows every
planet, for the reading rather than for the score, and both people at once.

## 6 · The words

All rendered prose lives in `src/data/corpus.json` (31 KB: 27 birth stars, 12 Moon signs, and 60
chart readings — five bodies × twelve signs) and in `src/engine/interpret.ts` (what each test means
at full, partial and no marks) — written to a fixed voice: plain, non-fatalistic, no predictions.

**Connection sentences are assembled, not stored.** Each is built from a body phrase ("how Ada
feels"), a joining phrase ("sits in the same place as") and a meaning — so all 7 × 7 × 5 = 245
possible sentences are correct by construction, with no table to fall out of step. What an angle
*means* is printed the first time it appears in a reading and not again: six paragraphs ending in the
same stock sentence read as a form letter, and the reader stops seeing the part that is about them.

**The vocabulary rule:** the only specialist terms allowed on screen are the 12 zodiac sign names.
Everything else — Sanskrit star names, the tradition's category names, symbols and glyphs — is
replaced by plain titles ("The quick starter"). Two tests enforce it: one walks the **rendered
page**, one walks **every string the engine can produce** whether or not the UI currently shows it.
The second exists because a string stops being covered by the first the moment the UI stops
rendering it — which happened once, and shipped stale wording for a week.

## 7 · Privacy

Manual entries live in `localStorage` and are never transmitted; there is no server. Public entries
come read-only from profiles whose owners already publish their birthday. Share links carry only
names and dates — the receiving browser recomputes everything. Messaging deep-links into ArtaQuest's
existing end-to-end-encrypted chat rather than reimplementing one.

## 8 · Reproducing every number in this document

```bash
npm test                                   # 83 tests: ephemeris vs golden, rules, symmetry,
                                           # uncertainty, synastry vs brute force, jargon, drift
python3 tools/golden.py                    # regenerate golden.json (needs pyswisseph + ephemeris files)
npx esbuild src/engine/score.ts --format=esm --bundle --outfile=/tmp/score.mjs
node tools/calibrate.mjs /tmp/score.mjs                    # the percentile table + its summary
echo 'export * from "./src/engine/score"; export * from "./src/engine/synastry";
      export * from "./src/engine/uncertainty";' |
  npx esbuild --bundle --format=esm --loader:.ts=ts --sourcefile=e.ts --outfile=/tmp/syn.mjs
node tools/calibrate-synastry.mjs /tmp/syn.mjs             # §5.3: what a count of connections is worth
node tools/compare-elements.mjs tests/golden.json          # the Table 1 vs 2a decision
node tools/contrast.mjs                                    # WCAG contrast, every ink/surface pair
node tools/screenshot.mjs dist shots/                      # 35-state visual audit, five widths
```

And the standing caveat, which is part of the method: there is no known mechanism by which any of
this could work. These are old, internally consistent ways of talking about people — reported
faithfully, calibrated honestly, and predicting nothing.
