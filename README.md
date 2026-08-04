# ArtaMatch

**Two sidereal charts, read one at a time, then laid over each other, then scored — in plain
English, with an honest account of what a date of birth alone cannot tell you.**

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

### Why there are two systems on the page and only one of them scores

An aspect layer was cut from this page once, for a good reason: a second, unscored system beside a
scored one invites "is nineteen connections *good*?" and cannot answer it. It is back because that
question now has a measured answer. Over 20,000 random pairs, **every** pair has between about ten
and twenty connections, the median is fifteen, and the count agrees with the eight-test score at
**0.03 out of 1** — which is to say not at all. Two old systems, the same two dates, no agreement.
The page says exactly that, out loud, and then shows *which* connections rather than how many.

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
