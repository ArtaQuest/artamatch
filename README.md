# ArtaMatch

**One score, fully explained: the oldest date-only matching tradition, out of 36 — every step shown
in plain words, with an honest account of what a date alone cannot tell you.**

### → [artaquest.github.io/artamatch](https://artaquest.github.io/artamatch/)

Full method, and the provenance of every number on the page: **[METHODS.md](METHODS.md)**

The page computes the traditional eight-test Moon score (sidereal, Lahiri) and then explains it
three ways at once:

- **The anatomy bar** — 36 = 1+2+3+4+5+6+7+8, drawn to scale, each test's block filled by the
  points it earned. The score becomes visible arithmetic: the two heaviest tests carry as much as
  the other six together, and you can see it.
- **The landscape strip** — every possible score, sized by how often 20,000 random pairs land on
  it, with this pair marked. "Higher than 69 in 100" stops being a claim and becomes a place.
- **The sky ruler** — the full 360° band, its 27 birth-star stretches and 12 signs, with both
  Moons marked and the band each swept during its birth day. The one picture of what the eight
  tests actually read, uncertainty included.
- **The hour grid** — all 576 combinations of the two birth hours, shaded by the score each gives.
  You can see the blocks where the answer changes, and see at a glance whether the missing hour
  matters at all.

The whole reading is **one scrolling document** with six numbered sections — what the score is, how
it is built, how sure it is, what it read, the eight tests one by one, and who these two people are.
Nothing is behind a tab, because the evidence for a number should not live on a different screen
from the number.

Two experiments were built, verified and then deleted to get here: an *ensemble* of four traditions,
and an *aspect layer* of 55 planet-pair readings. Both worked; both made the page about more than
one thing. They are in the git history, and in [METHODS.md](METHODS.md) §5.

## What makes it honest

- **Percentiles, not flattery.** The traditional "pass mark" of 18/36 is cleared by 71% of random
  pairs (median 21), so "you passed" means little; every score is shown against the distribution it
  actually comes from, and a drift test keeps those numbers current in CI.
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
npm test          # 64 tests — astronomy, rules, symmetry, uncertainty, jargon, drift
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
