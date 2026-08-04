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

## 5 · The two charts, and the score between them

### 5.1 · One person's chart (`src/engine/natal.ts`)

A full natal chart has three layers: which **sign** each planet is in, which **house** it is in, and
which sign was **rising**. Only the first survives a missing birth time — houses and the rising sign
turn a full circle every 24 hours, so from a date alone they are not approximate, they are *unknown*.
This file draws the layer that survives, and the page says the other two are missing rather than
quietly defaulting them to sunrise, which is the usual dodge. This matters more than it sounds:
conventional synastry weights contacts with the rising sign and the midheaven **most heavily of
all**, so a date-only reading is missing the tradition's own top-weighted factor entirely.

Even the surviving layer has edges: a planet near a boundary at midnight is in two signs that day. So
every body reports the signs it could be in **and the share of the day it spent in each**, found
exactly — an hourly scan for a change, then bisection inside the hour that changed. The Moon does
this on about two days in five; Mercury moves at most ~2.2° in a day and Saturn ~0.13°, so theirs is
settled unless the date lands on the crossing itself.

**Five bodies get a paragraph** — Sun, Moon, Mercury, Venus, Mars. Jupiter holds a sign for about a
year and Saturn for two and a half, so a *reading* of them would describe everyone born that year;
they are drawn, they are scored, and they get a stated placement rather than a character sketch.
Uranus, Neptune and Pluto (7, 14 and 12–30 years to a sign) get their windows named and nothing else,
and are excluded from scoring entirely.

### 5.2 · The score (`src/engine/affinity.ts`)

    ease, friction  =  Σ_{i,j,a}  [v_a]±  ·  w_ij  ·  exp( −(Δ_ij − t_a)² / 2 S²_ij )
    w_ij            =  imp_i · imp_j · √( s²_ij / S²_ij )
    S²_ij           =  s²_ij + σ²_ij
    Δ_ij, σ_ij      =  circular mean and deviation of the angle over all 24×24 = 576 birth-hour pairs

The same functional form as the sky→topics forward model of the AstroAttention paper
(`analysis/adstopics/astro_forward.py`): a Gaussian kernel on a **seam-free wrapped** angular
difference, non-negative weights, summed. Four house rules are carried over verbatim — circular
readouts are always `atan2` of a resultant vector and never a scalar mean of angles; weights are
positive but **not normalised** (the recorded softmax ablation there is worse); ablations are
reported even when they undercut the model, as that paper reports its own centring worth "only
~0.003 AUC"; and **the ceiling is reported as a result**. Two deliberate departures: the paper's
phases are *fitted* per topic and here they are the tradition's five fixed angles, because there is
nothing to fit to; and its kernel is `exp(−Δ²)` with Δ in radians — an implicit width near 40°, right
for a broad seasonal phase and far too wide for an aspect — so the width here comes from the orb.

**Why the weight is not an invention.** The estimand is the average compatibility over every birth
hour the two dates leave open. For a Gaussian kernel and θ ~ N(μ, σ²),

    E[ exp( −(θ−t)²/2s² ) ]  =  √( s²/(s²+σ²) ) · exp( −(μ−t)² / (2(s²+σ²)) )

which factorises into an amplitude depending only on how well the angle is pinned down, times a
widened kernel at the mean angle. "Weight by the variance of the angle estimate, score at the mean
phase difference" is not a heuristic — it is what taking the expectation does.

**What is shown is the plain average of the 576 charts**, not the closed form. The closed form is
computed alongside as the *decomposition*, because it is what makes the number explainable, and the
gap is printed on every reading. Measured over 500 random pairs: **median 4.5 × 10⁻⁴, worst
2.4 × 10⁻³**, against a population spread of 0.057. Per-pair contributions are the exact 576-chart
averages, so the five reasons the page shows plus the stated remainder sum to the score with a
residual under 10⁻¹² — the explanation *is* the arithmetic, not an illustration of it.

### 5.3 · Constants: what is citable and what is chosen

| | value | provenance |
|---|---|---|
| orbs | Sun 15°, Moon 12°, Mercury 7°, Venus 7°, Mars 8°, Jupiter 9°, Saturn 9°; a pair is allowed the **average of the two** | [tradition] Lilly, *Christian Astrology* (1647). Sources vary 1–3°. Orbs belong to the **body**, not the angle — the older of the two systems, and the only one with a citable table |
| kernel width | s = orb/2, so a pair on the traditional edge still counts for exp(−2) ≈ 14% | [convention] the tradition supplies only "tighter is stronger" |
| angle valences | sixth +0.5, third +1, quarter −1, opposite −1 | [tradition] for the *signs* (Tetrabiblos I). [convention] for the magnitudes |
| same-place valence | the mean of the two bodies' natures | [tradition] near-total consensus that the conjunction has no valence of its own and takes it from the bodies joined |
| body natures | Jupiter +1, Venus +0.5, Sun/Moon/Mercury 0, Mars −0.5, Saturn −1 | [tradition] the classical benefic/malefic ranking — 7 numbers, not a 49-cell table |
| body importance | Sun 1, Moon 1, Venus 0.9, Mars 0.8, Mercury 0.6, Jupiter 0.5, Saturn 0.5 | [convention] the sources rank these; none numbers them |
| the percentile | 20,000 random pairs, seed 13579 | **[measured]** — the only honest number in the model |

### 5.4 · Ablations and robustness (`tools/calibrate-affinity.mjs`)

Rank correlation with the model as shipped, 1,500 random pairs:

| ablation | Spearman |
|---|---|
| exchange rate ×0.5 / ×0.75 / ×1.5 / ×2.0 | 0.947 / 0.988 / 0.969 / 0.921 |
| a sixth counted as much as a third | 0.958 |
| every body weighted equally | 0.944 |
| the same-place contact fixed at +1 | 0.884 |
| **the opposite angle read as easy** | **0.718** |

**And two that undercut the model rather than flatter it**, reported because the paper this borrows
its shape from reports its own centring as worth "only ~0.003 AUC":

| ablation | result |
|---|---|
| the variance weighting — the mathematical centrepiece — switched off | **r = 0.994, Spearman 0.993** |
| the whole score reconstructed from five aspect *counts* (no kernel, no weights, no hours) | **R² = 0.733** |

The first says the weighting is nearly **inert**. That is not because it is wrong — it is what taking
the average over the unknown hours literally *is* — but because there is little for it to do: six of
the seven bodies are pinned to within a degree by the date alone, and only the Moon is genuinely
uncertain (mean confidence 0.80 against 0.96–0.98 for the rest). It stays because it is correct, not
because it earns its keep in the ordering. The second says a crude tally of how many angles fall
inside their orb already reproduces three quarters of the variance; everything else in the model is
the remaining quarter. Both belong on the record.

And the check that the model reads the whole chart rather than only the bodies it can pin down —
the weighting damps the Moon hardest, so this is the place it could quietly become a Sun-only score:

| body | mean confidence | share of the answer |
|---|---|---|
| Sun | 0.980 | 23.0% |
| **Moon** | **0.799** | **19.9%** |
| Venus | 0.964 | 14.8% |
| Mars | 0.969 | 13.8% |
| Mercury | 0.963 | 9.7% |
| Jupiter | 0.971 | 9.4% |
| Saturn | 0.971 | 9.4% |

Two bugs this reporting caught, both silent: `ease` and `friction` returned **zero** rather than a
missing value on the fast path, so the calibration reported an ease forty times too small without
complaining; and an ablation that mutated a table the code had stopped reading dutifully reported a
perfect **1.000** — an ablation which has stopped testing anything looks exactly like a component
that does not matter.

### 5.5 · The ceiling, reported as a result

Population spread of the score: **σ = 0.0566**. Median width of the 90% band one pair spans across
its own 576 charts: **0.0481**. Ratio **0.85**.

Not knowing the two birth times costs almost as much as the entire difference between one couple and
another. Two pairs whose bands overlap cannot be told apart from dates alone by *any* model; only
about two in five randomly chosen pairs can be separated at all. Every compatibility percentage
computed from dates alone and printed without a band is claiming a precision the input cannot carry.

### 5.6 · The empirical null

Voas (2007), ~10 million married couples from the 2001 England and Wales census: **no**
sign-compatibility effect, bounded below roughly one couple in a thousand; an apparent same-sign
excess turned out to be census form-filling error. There is therefore no outcome to fit to, and any
model claiming to have *learned* compatibility would be lying. Nothing here is fitted.

### 5.7 · Two scores, and why both stay

The eight-test Moon score (§3) and the fit (§5.2) read the same two dates and correlate at **0.01**.
Only one is called *the score* — the page may show many numbers but only one may carry that name —
and the older one rides along in every ranked row so a reader can watch them part company. Hiding
one to avoid the awkwardness would be the dishonest move.

## 5.4 · Removed experiments

All worked, all were verified, all were deleted. They are in the git history.

**The ensemble.** Three other date-only traditions (date-digit numerology, the twelve-year animal
cycle, Sun-sign elements), each calibrated the same way, averaged into one percentile. Removed
because four half-explained numbers teach less than one fully explained one.

**The first aspect layer.** Written readings for all 55 body pairs in four configurations, sitting
beside the score as unscored commentary. Removed because it invited "is 19 connections good?" and
could not answer it.

**The connection layer that replaced it.** Every connection between two charts with an exact
probability, computed in closed form from a difference of two uniforms and verified against a
240×240 brute-force sweep to 0.06 percentage points. It worked. It is gone anyway: §5.2 reads the
same angles, weights each by how firmly the dates pin it down, and produces a number whose parts sum
to it exactly. Keeping the older list beside it would have put two overlapping accounts of the same
thing on one page — the failure this project has already made once. `src/engine/synastry.ts` shrank
from 380 lines to 97.

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
npm test                                   # 100 tests: ephemeris vs golden, rules, symmetry,
                                           # uncertainty, the score vs longhand brute force,
                                           # the ceiling scan vs matchPair, jargon guards, drift
python3 tools/golden.py                    # regenerate golden.json (needs pyswisseph + ephemeris files)
npx esbuild src/engine/score.ts --format=esm --bundle --outfile=/tmp/score.mjs
node tools/calibrate.mjs /tmp/score.mjs                    # the percentile table + its summary
echo 'export * from "./src/engine/affinity"; export * from "./src/engine/score";' |
  npx esbuild --bundle --format=esm --loader:.ts=ts --sourcefile=e.ts --outfile=/tmp/aff.mjs
node tools/calibrate-affinity.mjs /tmp/aff.mjs             # §5.3–5.5: the percentile table,
                                                           # the ablations, the per-body shares,
                                                           # and the ceiling
node tools/compare-elements.mjs tests/golden.json          # the Table 1 vs 2a decision
node tools/contrast.mjs                                    # WCAG contrast, every ink/surface pair
node tools/screenshot.mjs dist shots/                      # 35-state visual audit, five widths
```

And the standing caveat, which is part of the method: there is no known mechanism by which any of
this could work. These are old, internally consistent ways of talking about people — reported
faithfully, calibrated honestly, and predicting nothing.
