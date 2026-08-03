# ArtaMatch

**Four old traditions read the same two dates of birth — every step shown, in plain words, with an
honest account of what a date alone cannot tell you.**

Live: https://artaquest.github.io/artamatch/ · Full methods: [METHODS.md](METHODS.md)

The four, each with its own score in its own units:

1. **The Moon score** — the traditional eight-test system, out of 36, from where the two Moons sat.
   The deepest of the four and the page's main subject: every point shows the rule that produced it
   and the exact values it read.
2. **The numbers** — the two dates' digits, reduced and compared by the classical three families.
3. **The year animals** — the twelve-year cycle, its teams, secret friends and clashes, with the
   year turning at the traditional early-February boundary (January babies belong to the previous
   animal, and the page says so).
4. **The Sun signs** — the familiar star signs compared by element, computed from the real Sun
   rather than newspaper date ranges, so boundary days come out right and are flagged.

**The ensemble.** Each system's raw score becomes a percentile against 20,000 random date pairs —
the same calibration for all four — and the headline is the plain mean of the percentiles, with a
count of how many systems place the pair above their own average. No weights of mine: an earlier
weighted blend was removed after measurement showed it moved rankings almost not at all (ρ = 0.954)
while adding unverifiable numbers.

## What makes it honest

- **Percentiles, not flattery.** The traditional "pass mark" of 18/36 is cleared by 71% of random
  pairs (median 21), so "you passed" means little; every score is shown against the distribution it
  actually comes from, and a drift test keeps those numbers current in CI.
- **Uncertainty is enumerated, not hidden.** A birth date does not fix the Moon: it moves 11.8–15.4°
  a day against 13°20′ birth stars. The page computes *every* reading the two dates allow — at most
  four Moon states per person, found by bisection — and shows each with its probability. Typical
  displacement from the unknown hour is ±6.6°, up to ±7.7° at the Moon's fastest.
- **No jargon.** The only specialist vocabulary on screen is the 12 sign names and the five major
  angle names (conjunction, opposition, trine, square, sextile). Everything else — Sanskrit star
  names, category names, glyphs — is replaced by plain-English titles. Two tests enforce this: one
  walks the rendered page, one walks every string the engine can produce.
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
  was false**. The counts now count exactly what the list shows.
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
npm test          # 74 tests — astronomy, rules, symmetry, uncertainty, jargon, drift
npx vite build
node tools/screenshot.mjs "$PWD/dist" /tmp/shots   # browser smoke: overflow, meters, console
```

CI gates every deploy on the typecheck, the full test suite, and a real-browser smoke of the built
bundle. Deployed to GitHub Pages by `.github/workflows/pages.yml`.

## What this is

There is no known mechanism by which any of this could work. These are old, internally consistent
ways of talking about people — reported faithfully, calibrated honestly, predicting nothing. Read a
result the way you would read a character sketch someone wrote about you: interesting where it
lands, harmless where it does not.

MIT licensed.
