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

Saturn's 22′ is acceptable *by construction*: connection strength scales with closeness-to-exact,
which goes to zero at the edge where a position error could flip a connection in or out.

## 2 · What a date alone can and cannot say

The Moon moves 11.8–15.4° a day; a birth star is 13°20′ wide and a sign 30°. Without a birth time
(taken as a UT day — the zone is unknown too, and saying so is part of the method):

| Quantity | Chance the noon guess is wrong |
|---|---|
| Moon sign | ~11% |
| Birth star | ~25% |
| Finer divisions | not attempted — the error swallows them |

Instead of guessing, `src/engine/uncertainty.ts` finds every (birth star, sign) state the Moon
occupies during the day — at most four; `1965-07-27` reaches the ceiling — by hourly scan plus
bisection to the second. Each state's share of the day **is** its probability under a flat prior, so
the page enumerates every possible reading exactly, with its chance. The displayed chart is taken at
the middle of the most likely state, *not* at noon: measured over 7,200 dates, noon disagrees with
the most likely birth star on 6.1% of days, which once made the page show one star and score another.

The rising point ("ascendant") moves a sign every two hours; nothing that needs it is computed, ever
— it is refused rather than defaulted.

## 3 · The Moon score (out of 36)

The traditional eight-test system, `src/engine/kuta.ts`. Each test returns its points, the exact
values it read, and the rule that produced them. The reference tables were reconstructed three times
independently, reconciled against primary sources (Saravali, BPHS, the Muhurta Chintamani lineage,
Drik Panchang), and are pinned by structural invariants in `tests/nakshatra.test.ts` — nine stars
per temperament, the period-6 constitution cycle, the animal census (13 pairs + one unpaired), the
seven canonical enemy pairs. That process caught a real transcription error worth 4 of the 36 points
(see README, "Where the tables came from").

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

## 5 · One score, not four (a removed experiment)

A version of this page also scored three other date-only traditions (date-digit numerology, the
twelve-year animal cycle, Sun-sign elements) and averaged their calibrated percentiles into an
ensemble. It worked, it was verified, and it was removed: four half-explained numbers teach less
than one fully explained one, and the page's premise is depth. The implementation and its tests are
in the git history if it is ever wanted again.

## 6 · The connections ("what runs between them")

Angles between one person's planets and the other's, `src/engine/synastry.ts`. An angle is the same
number in either zodiac — the traditions disagree about where the zodiac *starts*, which changes
signs, never angles — so this layer is not mixing systems. It is commentary, deliberately **outside
the score**: it surfaces as counts ("9 help, 4 rub") a reader can verify against the list.

Two structural rules: pairings between the three slowest planets are weighted to ~nothing (everyone
born within a few years shares them — they describe a generation, not a pair), and every weight is
defined on the unordered pair so the whole layer is symmetric.

## 7 · The words

All rendered prose lives in `src/data/corpus.json`: 78 planet-pairs × 4 configurations, 27 birth
stars, 12 Moon signs — written to a fixed voice (plain, non-fatalistic, no predictions) and audited.

**The vocabulary rule:** the only specialist terms allowed on screen are the 12 zodiac sign names
and the five major angle names (conjunction, opposition, trine, square, sextile). Everything else —
Sanskrit star and node names, the tradition's category names, symbols and glyphs — is banned and
replaced by plain titles ("The quick starter"). Two tests enforce this: one walks the **rendered
page** on every tab, one walks **every string the engine can produce** whether or not the UI
currently shows it. The second exists because a string stops being covered by the first the moment
the UI stops rendering it — which happened once.

## 8 · Privacy

Manual entries live in `localStorage` and are never transmitted; there is no server. Public entries
come read-only from profiles whose owners already publish their birthday. Share links carry only
names and dates — the receiving browser recomputes everything. Messaging deep-links into ArtaQuest's
existing end-to-end-encrypted chat rather than reimplementing one.

## 9 · Reproducing every number in this document

```bash
npm test                                   # 63 tests: ephemeris vs golden, rules, symmetry,
                                           # uncertainty, jargon guards, drift
python3 tools/golden.py                    # regenerate golden.json (needs pyswisseph + ephemeris files)
npx esbuild src/engine/score.ts  --format=esm --bundle --outfile=/tmp/score.mjs
npx esbuild src/engine/systems.ts --format=esm --bundle --outfile=/tmp/systems.mjs
node tools/calibrate.mjs /tmp/score.mjs /tmp/systems.mjs   # every calibration table
node tools/compare-elements.mjs tests/golden.json          # the Table 1 vs 2a decision
node tools/screenshot.mjs dist shots/                      # visual checks: overflow, meter height
```

And the standing caveat, which is part of the method: there is no known mechanism by which any of
this could work. These are old, internally consistent ways of talking about people — reported
faithfully, calibrated honestly, and predicting nothing.
