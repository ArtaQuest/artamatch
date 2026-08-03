# ArtaMatch

**A sidereal (Vedic) compatibility matcher that works from dates of birth alone — and says out loud
what a date of birth cannot tell you.**

**One score: a total out of 36**, from Ashtakoota Guna Milan — the canonical Vedic system of eight
tests, computed almost entirely from where the two Moons sat. Every one of its points shows the rule
that produced it and the exact value it read. Nothing is a black box.

Beside it, and deliberately **not** part of the score, sits the inter-chart aspect picture: what runs
between the two charts, reported as counts you can verify against the list underneath.

**No jargon.** Nothing on screen says *nakshatra*, *kuta*, *dosha*, *ayanamsa*, *orb* or *trine*.
The eight tests are called things like "Meeting of minds" and "Underlying makeup"; connections read
"her affection — pulling against — his drive". The traditional terms are kept in the code for
checking the working, and a test walks the rendered page asserting none of them reach the reader.

---

## The thing most compatibility sites get wrong

A birth **date** fixes the Sun to about a degree. It does not fix the **Moon**.

The Moon travels **11.8°–15.4° in a day**. A nakshatra is **13°20′** wide. So on most days the Moon
changes nakshatra somewhere inside the birth day — and six of the eight kutas are read off the Moon's
nakshatra and rāśi.

A matcher that quietly evaluates "the chart" at noon and prints `28/36` is stating, with total
confidence, one of two, three or four answers the input cannot distinguish between.

Take **1965-07-27**. The Moon travels 15.17° that day:

| UT hours | Nakshatra | Rāśi | Share of day |
|---|---|---|---|
| 00:00–01:22 | Ardra | Gemini | 5.7% |
| 01:22–17:12 | Punarvasu | Gemini | 66.0% |
| 17:12–22:27 | Punarvasu | Cancer | 21.9% |
| 22:27–24:00 | Pushya | Cancer | 6.4% |

Three possible birth stars. Guna Milan answers differently for each. ArtaMatch computes **all of
them**, shows the range, and marks the pair as uncertain — rather than picking one and sounding sure.

For scale: this engine's Moon is accurate to **1.4 arcminutes** against the Swiss Ephemeris, while
the unknown birth time moves it by up to **±6.6°** — roughly **290× larger**. The ephemeris is not
the source of doubt. The missing clock is.

Quantified, assuming a birth time uniform over the day:

| Quantity | Span | Chance of being wrong | Kutas at stake |
|---|---|---|---|
| Rāśi (Moon sign) | 30° | ~11% | Varna, Vashya, Graha Maitri, Bhakoot — 15 points |
| Nakshatra (birth star) | 13°20′ | ~25% | Tara, Yoni, Gana, Nadi — **21 points** |
| Pada | 3°20′ | unusable | refused, not approximated |

ArtaMatch reports all of this rather than hiding it, and refuses outright the things a date genuinely
cannot support — most importantly **Mangal dosha from the Ascendant**, since the Lagna moves a whole
sign every two hours and a date cannot even bias a guess at it. It is checked from the Moon and from
Venus, and the page says the third reading is unavailable rather than quietly defaulting to noon.

---

## Accuracy

The built-in ephemeris is dependency-free and runs entirely in the browser. It is verified against
the **Swiss Ephemeris** (`pyswisseph`, `SIDM_LAHIRI`) across 1,975 sample dates spanning 1900–2100,
plus hourly Moon positions across whole days. Measured maximum error:

| Body | Max error | | Body | Max error |
|---|---|---|---|---|
| Sun | 0.7′ | | Jupiter | 10.4′ |
| **Moon** | **1.4′** | | Saturn | 22.3′ |
| Mercury | 1.2′ | | Uranus | 3.8′ |
| Venus | 1.3′ | | Neptune | 1.8′ |
| Mars | 3.1′ | | Pluto | 1.3′ |

Lahiri ayanamsa reproduces Swiss Ephemeris to **1e-8°**.

Saturn is the loosest at 22′, and that is fine on purpose: an error near an orb boundary has almost
no effect on the score, because aspect weight is proportional to exactness, which goes to zero
exactly there.

Method: Meeus *Astronomical Algorithms* ch. 47 (45-term lunar series) for the Moon; JPL/Standish
Table 1 Keplerian elements for the planets. JPL's Table 2a with its long-period terms was tried for
the outer planets and **measured to be worse** over 1900–2100 — it is fitted across six millennia, so
it is looser inside any one century. See `tools/compare-elements.mjs`.

```bash
npm test              # runs the Swiss Ephemeris comparison + all property tests
npm run golden        # regenerate tests/golden.json (needs pyswisseph + ~/ephe)
```

---

## Where the Jyotish tables came from

The reference tables are the part of a system like this that fails silently — a transposed row is
wrong forever and nothing crashes. Every one was reconstructed independently three times, reconciled
against primary sources (Saravali, BPHS, Muhurta Chintamani lineage, Drik Panchang), and then pinned
by **structural invariants** in the tests: nine nakshatras per gana, the Vimshottari lord cycle
repeating three times, the period-6 nadi zig-zag, the yoni animals paired one male and one female
with the mongoose unpaired, and exactly seven yoni enemy pairs.

That process caught a real error. The Yoni table was first written as a short list of
enemy/friendly/unfriendly pairs with everything else defaulting to neutral — it reproduced only
**55% of the actual 14×14 table** and wrongly made elephant/sheep mortal enemies when the tradition
rates them *friendly*. Yoni is 4 of the 36 points. The full grid is now transcribed, and a test pins
the enemy set exactly so the shortcut cannot come back.

Graha Maitri (all 7 rows), Gana, Varna, Tara, Bhakoot and Nadi were confirmed unchanged.

## Two bugs worth recording

**The displayed birth star disagreed with the scored one, on 6.1% of dates.** The report was drawn
at noon while the "most likely" birth star was the one covering the largest share of the day. On a
day where the Moon changes birth star twice, noon can land in a two-hour sliver next to a state
covering half the day — so the page printed one birth star and scored a different one. The headline
is now taken at the middle of the most likely state, which makes the shown chart and the computed
score the same chart, and is also the better estimate under a flat prior over birth times.

**Meters rendered as full-height gradient blocks.** `.meter` was a `<span>`, and inline boxes
silently ignore `height` — so a 6px bar filled its container and overlapped everything beneath it.
Every sized element in the stylesheet now states its `display`, and the screenshot tool asserts no
meter is taller than 12px.

## Why there is only one number

An earlier version reported a 0–100 figure blended 60% from the traditional score, 30% from an "ease"
index and 10% from a "pull" index. Three measurements killed it (`tools/calibrate.mjs`, 20,000 random
pairs, deterministic seed):

| | |
|---|---|
| Ranking by the blend vs by the traditional score alone | **ρ = 0.954** |
| "Pull" index, 10th → 90th percentile | **56 → 75** |
| Median of the 0–100 blend | **59** |

The two invented components moved the ranking almost not at all while adding two unverifiable
numbers and a set of weights nobody could check. "Pull" returned roughly the same answer for
everybody, which is not a measurement. And a 0–100 scale invited reading 59 as a fail when it was
exactly average.

So the score is the tradition's own: out of 36, with a threshold in use for centuries, and no weights
from me. What was "ease" survives only as a tie-break and as **counts** — "9 connections help, 4 rub"
— which a reader can check against the list.

## Every score comes with a percentile, because the pass mark flatters

"22 out of 36, above the traditional pass mark of 18" reads as good news. It is not:

- **71%** of randomly paired dates clear 18
- the **median** pair scores **21**
- 25.5 is the 75th percentile; 28 is the 90th

A threshold that seven in ten pairs clear tells you almost nothing, and presenting it as an
achievement is flattery. So every score is shown against the distribution it actually came from, and
the bands ("Above average", "High") are set on measured percentiles rather than on the tradition's
own generous cutoffs.

## The one test you can switch off

Varna, worth 1 point of 36, ranks four temperaments in a fixed order taken from an old caste
hierarchy and scores only when the first person's sits at or above the second's. It is named plainly,
its rule says exactly what it is doing, and there is a checkbox to leave it out of both the score and
the ranking.

## Design decisions worth arguing with

**Scores are symmetric.** `score(A,B) === score(B,A)`, asserted over hundreds of random date pairs.
A ranked list is incoherent otherwise — A's list and B's list would disagree about the same pair.

Three of the eight kutas (Varna, Gana, and the halves of Tara) are genuinely asymmetric in the
tradition, which is written for a groom and a bride. ArtaMatch is not told who is who, so it computes
**both orderings**, ranks on the mean, and shows both numbers whenever they differ.

**Outer-to-outer aspects are nearly weightless.** Uranus, Neptune and Pluto take 84, 165 and 248
years to orbit. Everyone born within a few years of you shares your Uranus–Neptune angle. Counting
those as compatibility scores every pair of age-peers as soulmates and every cross-generational pair
as doomed — it measures a birth cohort, not a relationship. This is the largest systematic error
available here and naive matchers walk straight into it.

**Aspects are zodiac-independent, so the two halves of the page are not mixing systems.** The angle
between two planets is the same number whichever zodiac you measure from — the traditions disagree
about where the zodiac *starts*, which changes which sign something falls in, but it cannot change an
angle. This is worth stating because applying a Western technique to sidereal positions looks like a
category error until you notice that it isn't one.

**No chart wheel.** The connection grid is a table, because that is what the data is; it reads on a
phone and needs no legend.

**The headline is a range when the date cannot support a number.** Rather than printing one confident
figure, an uncertain pair shows every reading the two dates allow with a probability against each —
"this reading is about 49% likely", then the alternatives. The eight tests depend on the Moon only
through which birth star and sign it is in, and each day holds at most four such states whose shares
*are* their probabilities, so that table is exact rather than sampled.

---

## Privacy

- **Manual entries never leave your browser.** They live in `localStorage`. There is no ArtaMatch
  server to send them to — this is a static page.
- **Public accounts** are [ArtaQuest](https://artaquest.com) members whose birthday is already public
  on their own profile (ArtaQuest publishes its whole database by design). Read-only, no credential.
- **Messaging** deep-links into ArtaQuest's existing end-to-end encrypted member messaging rather
  than re-implementing a worse one.

---

## Development

```bash
npm install
npm run dev       # http://localhost:5173/artamatch/
npm run build
npm test
```

Deployed to GitHub Pages from `main` by `.github/workflows/pages.yml`, which gates on the typecheck
and the full Swiss Ephemeris comparison — a regression fails the build rather than shipping quietly.

---

## A note on what this is

Astrology is a shared symbolic language with no established causal mechanism. Nothing here predicts
anything about anybody. It is offered as a way of describing patterns and starting conversations —
not as a verdict on a person, and least of all on a person who did not ask to be assessed.

MIT licensed.
