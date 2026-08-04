# ArtaMatch

**Two sidereal charts, read one at a time, then laid over each other, then scored — with a
continuous, variance-weighted model, in plain English, and with an honest account of what a date of
birth alone cannot tell you.**

### → [artaquest.github.io/artamatch](https://artaquest.github.io/artamatch/)

Full method, and the provenance of every number on the page: **[METHODS.md](METHODS.md)**

The reading is one document, read top to bottom, in the order a person actually asks:

1. **The score** — what it is, and whether that is good.
2. **Each of them, on their own** — both charts drawn, and five things each one is said to suggest,
   one plain paragraph apiece.
3. **Where the two charts touch** — both people on one shared band, and the connections between
   their planets, narrated.
4. **Where the score came from** — the eight tests, drawn to scale.
5. **How sure the score is** — every reading the two dates allow, and the 576 hour combinations.

### The rule the whole page is built on

**Nothing is a bare number.** A date of birth fixes a *day*, not an instant, so every statement is
made **24 × 24 = 576 times** — once for each combination of the two unknown birth hours — and
reported with its mean, its give-or-take and how often it held. The score carries its exact
distribution; every planet carries the share of the day it spent in the sign shown; every connection
carries how many of the 576 charts actually contained it.

### The chart is a straight line, not a wheel

A wheel's *rotation* carries the houses and the rising sign, and a birth date fixes neither of them —
they turn a full circle every day. Drawing the circle anyway would put a real-looking orientation on
a chart that has none. So the circle is cut open at the start of Aries and laid flat: the same twelve
signs in the same order, an angle becomes a horizontal distance you can measure with your eye, and
both people share one axis, so "in the same place" is literally one label sitting above another.

### Three diagrams, each answering a different question

- **The sky band** — where every planet was, for one person or for both at once, with a leader line
  from each label to its exact position and the connections numbered to match the list below.
- **The anatomy bar** — 36 = 1+2+3+4+5+6+7+8, drawn to scale, each test's block filled by the
  points it earned. The score becomes visible arithmetic.
- **The hour grid** — all 576 combinations of the two birth hours, shaded by the score each gives.
  You can see the blocks where the answer changes, and whether the missing hour matters at all.

### The ceiling: what is the *most* you could score?

A score out of 36 on its own invites "is 24 good?", and a percentile answers that only in the
aggregate. So the ranking panel answers it for **this person**: it scans **every single birth date
within twelve years either side of theirs, one day at a time** — about 8,767 of them — and reports
the best score that exists anywhere in that window, the worst, the middle, and a histogram of the
lot. The scan runs in slices of a frame behind a progress bar, so the page never stops scrolling.

It also puts a stake through a superstition the rest of the page would otherwise feed. The top score
is not held by one soulmate born on one magic day: the eight tests read the Moon, the Moon comes back
to the same place every 27.3 days, and so **dozens of those days reach the identical ceiling** — for
one of the seeded people, 71 days out of 8,767, about one in 123. The panel prints that count, and it
is the most honest sentence on it.

The scan is a *second* implementation of the score (Moon-only, skipping nine bodies it does not need,
because it runs nine thousand times). Two code paths for one number is how a page ends up
contradicting itself, so a test holds the fast path against `matchPair` **to ten decimal places on
every day of four whole months**, and again on every date the scan names as best.

### The score

Every angle between one person's seven bodies and the other's, scored against the five angles the
tradition names, and summed:

```
     ease, friction  =  Σ  [v]±  ·  w_ij  ·  exp( −(Δ_ij − t_a)² / 2S²_ij )
                       i,j,a

     w_ij  =  imp_i · imp_j · √( s²_ij / S²_ij )        S²_ij = s²_ij + σ²_ij
```

where Δ and σ are the **circular mean and deviation of the angle across all 576 charts**. It is the
same functional form as the ArtaQuest sky→topics forward model in the AstroAttention paper — a
Gaussian kernel on a seam-free wrapped angular difference, non-negative weights, summed — with the
phases fixed by the tradition instead of fitted, because there is nothing to fit to.

**The weight is not bolted on; it falls out.** The thing being estimated is the average
compatibility over every birth hour the two dates leave open. For a Gaussian kernel that expectation
has a closed form, and it *factorises* into an amplitude that depends only on how well the angle is
pinned down, times the same kernel — widened — evaluated at the mean angle. "Weight by the variance,
score at the mean" is what taking the expectation *does*.

The number shown is the plain average of the 576 charts. The factorisation is computed alongside it
and reported as the *decomposition*, because that is what makes the number explainable — and the gap
between the two is printed on every reading (measured: median 4.5 × 10⁻⁴, worst 2.4 × 10⁻³, against
a population spread of 0.057).

### Two numbers, not one — and the reason is the biggest fabrication in the genre

The tradition has said for two thousand years which angles are easy and which are hard. It has never
once said the **exchange rate** — how many easy angles cancel a hard one. Every published
compatibility percentage nets them anyway, and that undisclosed rate is the largest invented number
in the whole field.

So **ease and friction are shown separately and never silently subtracted.** A combined number
exists for ranking, at the only non-arbitrary rate there is (one for one), labelled as the choice it
is — and how much that choice matters is measured, not argued.

### What is measured and what is a convention

| | |
|---|---|
| **Measured** | the positions · every angle, mean and spread · the 576-chart distribution · the percentile against 20,000 random pairs · every robustness figure below |
| **Convention** | which angles are easy or hard [Ptolemy, *Tetrabiblos* I] · how wide an orb is [Lilly, *Christian Astrology*, 1647 — orbs belong to the **body**, and two bodies get the average of theirs] · which bodies are benefic or malefic [classical] · how much each body matters [the sources rank them; the numbers are ours] |

A convention that drove the answer would be a problem. Measured over 1,500 random pairs, almost
none of them does — rank correlation against the model as shipped:

| ablation | Spearman |
|---|---|
| exchange rate ×0.5 … ×2.0 | 0.921 – 0.988 |
| a sixth counted as much as a third | 0.958 |
| every body weighted equally | 0.944 |
| the same-place contact fixed at +1 | 0.884 |
| **the opposite angle read as easy** | **0.718** |

**Two more ablations, which undercut the model rather than flatter it** — reported because the paper
this borrows its shape from reports its own centring as worth "only ~0.003 AUC":

| ablation | result |
|---|---|
| the variance weighting switched off | r = 0.994 |
| the score reconstructed from five aspect *counts* | R² = 0.733 |

So the mathematical centrepiece is nearly **inert**, and a crude tally of aspects already reproduces
three quarters of the answer. The weighting stays because it is *what taking the average over the
unknown hours is*, not because it earns its keep in the ordering — six of the seven bodies are pinned
to within a degree by the date alone, so there is little for it to do. Saying so beats letting a
derivation imply an importance it does not have.

The opposite-angle row above is the one choice the model refuses to make for you, so it is **a switch
on the page**.
The classical texts call being directly opposite hard; writers on couples very often read it as two
people completing each other. Nothing else we chose moves the ordering nearly as much.

### The ceiling, reported as a result

Over 20,000 random pairs the score has a standard deviation of **0.0566**. The 90% band a single
pair spans across its own 576 charts has a median width of **0.0481** — a ratio of **0.85**.

**Not knowing the two birth times costs almost as much as the entire difference between one couple
and another.** Two pairs whose bands overlap cannot be told apart from dates alone by any model,
however good; only about two in five randomly chosen pairs can be separated at all. Any site
printing a compatibility percentage from dates alone, without a band, is claiming a precision the
input does not carry. That is not a criticism of their model — it is arithmetic.

### The empirical null

The largest test ever run — Voas (2007), ~10 million married couples from the 2001 England and Wales
census — found **no** sign-compatibility effect, bounding any effect below roughly one couple in a
thousand. So nothing here is fitted, because there is nothing to fit to. What is computed is: under
the tradition's own conventions, stated openly, where does this pair fall among random pairs? That
has a true, reproducible answer, and it is the only one on offer.

### Why there are two scores on the page and what to do about it

The older **eight-test Moon score out of 36** is still there, in its own section, still calibrated,
still carrying its own exact distribution over the 576 charts. It is not a rival headline: only one
number on the page is called *the score*.

It stays because of what it measures *about the new one*. The two read the same two dates and agree
at **0.01 out of 1** — knowing one tells you nothing about the other. That disagreement is the most
useful thing either of them says, and hiding one to avoid the awkwardness would be the dishonest
move. The ranked list is ordered by the fit; the older score rides along in every row so you can
watch them part company.

## What makes it honest

- **Percentiles, not flattery.** The traditional "pass mark" of 18/36 is cleared by 71% of random
  pairs (median 21), so "you passed" means little; every score is shown against the distribution it
  actually comes from. A drift test recomputes the distribution in CI and asserts the *embedded*
  constants and the percentile table against it, cell by cell — so a shifted distribution cannot
  leave stale numbers on the page.
- **Every prediction carries a confidence interval.** Not just the report — the hero, the ranking
  rows and the totals all show the range the unknown birth hours allow, so a list of point estimates
  can never hide that two people are statistically indistinguishable. The headline is the *expected*
  score (the mean across every birth time), beside a 90% interval and the single most likely reading.
- **The interval is computed exactly, not sampled.** A birth date does not fix the Moon: it moves
  11.8–15.4° a day against 13°20′ birth stars. But the eight tests read the Moon only through which
  birth star, sign and mid-sign half it is in — so each day partitions into at most four states whose
  shares *are* their probabilities, and enumerating the ≤16 combinations gives the true distribution.
  Verified against brute force: it agrees with a 240×240 hour sweep (57,600 pairs) to within 0.15
  percentage points, and a 24×24 sample is measurably *worse* — off by up to 1.3 points, because
  24 samples miss where the boundaries actually fall.
- **No jargon.** The only specialist vocabulary on screen is the 12 sign names. Everything else —
  Sanskrit star names, category names, glyphs — is replaced by plain-English titles ("The quick
  starter"). Two tests enforce it: one walks the rendered page, one walks every string the engine
  can produce.
- **Symmetric by construction.** score(A,B) = score(B,A), asserted over hundreds of random pairs, so
  everyone's ranked list agrees about any shared pair.
- **The one test with an inherited caste hierarchy can be switched off** — and the score is then
  compared against a separately calibrated distribution, not the 36-point one.
- **Astronomy verified twice.** The built-in positions are checked against the Swiss Ephemeris on
  1,975 committed dates in CI, and held on a second unseen 1,699-date sample during review. Moon
  worst case: 1.4 arcminutes — hundreds of times smaller than the missing-clock uncertainty.

## What triple-checking found (kept on the record)

Adversarial review (34 agents, every finding re-verified by execution) confirmed 26 issues, all now
fixed and regression-tested. The ones worth remembering:

- The "every reading the dates allow" table **missed a reading** whenever the Moon crossed the
  mid-sign split at 15° of Sagittarius or Capricorn — the one rule that reads a degree within a
  sign. The state enumeration now includes those boundaries, verified by brute force.
- Merged probability rows were **labelled with the wrong reading**: distinct birth-star combinations
  with equal scores were glued under the first one's labels with their combined chance.
- The helps/rubs counts filtered on an invisible threshold, so **"you can count them in the list"
  was false**. Fixed at the time; the layer has since been removed entirely.
- A stray `.toUpperCase()` made the **switch-off toggle silently ignore the exclusion** in the
  score. Caught by a test written the same hour.
- The visible copy said "six of the eight tests read the Moon"; it is all eight.

Earlier finds, same spirit: a yoni table reconstructed from a shortcut reproduced only 55% of the
real grid (fixed against sources, pinned by tests); the displayed birth star disagreed with the
scored one on 6.1% of dates — the star alone on ~3%, star-or-sign on ~6% — because the display used
noon while the score used the likeliest state; inline `<span>` meters rendered as full-height blocks
because inline boxes ignore height. Details and the full method: [METHODS.md](METHODS.md).

## Privacy

Manual entries live in this browser's localStorage and are never transmitted — there is no server.
Public entries come read-only from ArtaQuest profiles whose owners already publish their birthday.
"Copy a link to this reading" carries only the two names and dates; the receiving browser recomputes
everything. Messaging deep-links into ArtaQuest's existing end-to-end-encrypted chat.

## Development

```bash
npm install
npm run dev       # http://localhost:5173/artamatch/
npm test          # 68 tests — astronomy, rules, symmetry, uncertainty, jargon, drift
npx vite build
node tools/contrast.mjs                           # WCAG contrast for every ink/surface pair
node tools/screenshot.mjs "$PWD/dist" /tmp/shots   # 35-state visual audit at five widths
```

CI gates every deploy on the typecheck, the full test suite, a computed **contrast** check (every
ink ≥ 4.5:1 on the surface it is used against — the brand permits two hues, so the only lever is
lightness), and a real-browser audit of the built bundle: 5 viewports × 5 states, asserting no
overflow, no console errors, intact instruments, un-squeezed rows and usable tap targets. Deployed to GitHub Pages by `.github/workflows/pages.yml`.

## What this is

There is no known mechanism by which any of this could work. These are old, internally consistent
ways of talking about people — reported faithfully, calibrated honestly, predicting nothing. Read a
result the way you would read a character sketch someone wrote about you: interesting where it
lands, harmless where it does not.

MIT licensed.
