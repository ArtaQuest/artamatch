# How ArtaMatch works — the full method

Everything the page computes, how each piece was verified, and where every embedded number comes
from. The [README](README.md) is the summary; this is the reference. Nothing here is needed to *use*
the page — it exists so that any claim on the page can be checked, or contradicted, by a stranger.

Every quantity below is tagged **[measured]** (computed here, and reproducible with the commands in
§18), **[derived]** (algebra, true before anything was run) or **[paper]** (taken from the source the
model comes from). Nothing else is in the model.

---

## 1 · The positions, and how they are verified

A dependency-free ephemeris (`src/engine/ephemeris.ts`) places the Sun, Moon and eight planets on the
ecliptic for any date between 1800 and 2100, in the constellation-aligned **sidereal (Lahiri)** frame.

| Piece | Method | Source |
|---|---|---|
| Moon | 45-term truncated ELP-2000/82 series + nutation in longitude | Meeus, *Astronomical Algorithms*, ch. 47 |
| Sun … Pluto | Keplerian elements, Table 1 | JPL/Standish, *Approximate Positions of the Planets* |
| Zodiac offset (ayanamsa) | quadratic fit to Swiss Ephemeris `SIDM_LAHIRI` | `tools/fit-ayanamsa.py` |

Everything in the file is pure and deterministic — no clock, no I/O, no network — which is what makes
a reading reproducible by someone who wants to disagree with it.

**Verification** is against the Swiss Ephemeris (`pyswisseph`), the reference implementation
professional software uses. `tests/golden.json` holds 1,975 sample dates spanning 1900–2100 plus
hourly Moon positions across whole days, and it is committed, so the comparison runs in CI without
the 300 MB ephemeris files: a regression in the positions fails the build rather than shipping
quietly.

Worst-case error, in arcminutes [measured]: **Sun 0.8 · Moon 1.4 · Mars 3.1 · Jupiter 10.4 ·
Saturn 22.3**. The per-body tolerances asserted in `tests/ephemeris.test.ts` are those measured
values with a little headroom, not aspirational numbers — if a change makes any body worse, the test
fails. The ayanamsa is reproduced to better than 10⁻⁵ degrees [measured].

The ephemeris is the least uncertain thing in the model, by a wide margin: the missing birth hour
costs hundreds of times more than 1.4′ does. That is the whole reason §8 exists.

## 2 · What a date of birth can and cannot say

A date fixes a **day**, not an instant, and the place of birth is not given either, so a date is read
as a **universal-time day**. That is stated rather than smoothed over: a real local day can begin as
much as 12 hours before, or 14 hours after, the day measured here.

Three things follow, and the model handles each differently rather than pretending they are the same
problem:

- **The bodies that a day almost pins down.** Six of the seven scored bodies move so little in a day
  that the date settles their angle to a fraction of a degree. The residual is not ignored, it is
  *weighted* — §5.
- **The Moon.** It moves 11.77 to 15.37 degrees a day, so it is the only scored body a date leaves
  materially open. It appears in 13 of the 49 cells, and the averaging in §4 is mostly about it.
- **The houses and the rising sign.** They turn a full circle every day, so from a date alone they
  are not approximate, they are unknown. They are refused rather than defaulted to sunrise, which is
  the usual dodge. But the *arithmetic* does not delete the rising sign, and the honest number for
  what it is worth is in §7 — it is not zero.

For one person's own chart (`src/engine/natal.ts`), the same discipline applies one layer down: a
planet near a sign boundary at midnight is in two signs that day, so every body reports every sign
the date allows and the share of the day it spent in each — found by scanning for the change and
bisecting inside the hour that changed, never by sampling. Conventional synastry weights the rising
sign and the midheaven most heavily of all, so a date-only reading is missing the tradition's own
top-weighted factor entirely. That is a limit of the input, and it is said out loud rather than
papered over.

## 3 · The model, and where it comes from

Arash Ashrafnejad, *"The zodiac's compatibility rules are a two-phase stability test"*, **Journal of
Seasonality**, 4 July 2026, CC BY 4.0 — the author's own paper.

Two signs are modelled as two **phases of one cycle**. The doctrine's soft/hard grading is then
recovered by asking a single control-theory question — is the combined two-phase system stable? For a
pair separated by phi [paper]:

```
    tau   = lambda_1 + lambda_2 = cos( 2 phi )               the sum of the two growth rates
    delta = lambda_1 * lambda_2 = BASELINE + cos( 2 phi )    their product
```

and the verdict is two sign-checks. **delta < 0** is a saddle — one rate grows while the other decays,
a genuine **contest**. Otherwise the pair shares one rate, tau/2, and it either spirals inward
(tau < 0, it **settles**) or outward (tau > 0, it **strains**).

**Why cos(2 phi) and nothing else.** An aspect has a built-in symmetry: phi and 360 − phi name the
same aspect, and the pattern repeats every 180 degrees. cos(2 phi) is the lowest wave with that
shape, so it is the only harmonic in the model [derived]. That single fact is what makes §4 an
identity rather than an approximation.

### 3.1 · The score: the stability margin

The score is the paper's verdict read as a continuous number — m = −max(Re lambda₁, Re lambda₂),
positive when every disturbance dies away. `margin()` in `src/engine/stability.ts`, and its shape is
the claim that contradicts every compatibility site there is:

| trace | margin | class |
|---|---|---|
| tau > 0 | −tau/2 < 0 | strains |
| BRANCH < tau < 0 | −tau/2 > 0 | settles |
| tau = BRANCH = 2 − √7 = −0.645751 | **PEAK = (√7 − 2)/2 = 0.322876** | the best a pair can be |
| tau < −0.75 | < 0 | contest |

Named values, all [derived] and all asserted in `tests/stability.test.ts`: a sextile scores 0.25, a
square −(√2 − 1)/2, and being in the same place or directly opposite both score −0.5. **The margin
does not rise with opposition.** It peaks in the interior and falls away below the peak, so the
maximally anti-aligned pair is not the best match — it is a contest. Measured over the census, the
most anti-aligned pairing that exists (tau = −0.8658) scores −0.118, below average [measured].

**Two zeros that mean opposite things, so a score never travels without its class.** The tempting shorthand "m = 0 at the
contest boundary" is false: m vanishes at tau = −0.75, where the *product* of the two rates is zero,
**and** at tau = 0, where their *sum* is. Those mean opposite things and the margin alone cannot tell
them apart, which is why every reading carries the class shares beside the score [derived, tested].

One numerical detail, because the page prints the ceiling: the discriminant is factored through its
two roots rather than evaluated term by term. Written out, its three terms cancel to about 10⁻¹⁶ at
the peak — a double root is where a square root is least accurate — and `sqrt` turns that into an
error near 10⁻⁸, eight digits lost at exactly the value shown as the ceiling. Factored,
`margin(BRANCH)` returns `PEAK` exactly, and a test asserts it.

### 3.2 · The one constant, and the limit of the uniqueness result

**BASELINE = 0.75** [paper]. It sets where a pair stops merely straining and becomes a contest. The
paper shows every value in (0.5, 1) puts that cut between the trine's cos 2phi = −0.5 and the square's
−1, so the square is singled out across the whole band; §14 re-measures the ordering across that band
rather than taking it on trust.

`tests/stability.test.ts` reproduces the paper's published results on the twelve whole-sign offsets:
only the two squares drive the product negative; the 144-cell census comes out **48 settles, 24
contest, 72 strains**; and every sign has the identical profile of **4 settles, 2 contests, 6
strains**. The soft aspects land in the settling class, the square is the one contested aspect, and
being in the same place is filed with the hard ones — the paper's own noted exception.

**The scope of that uniqueness, stated so the page cannot overclaim it.** "Only the square is a
contest" is a fact about twelve equally spaced signs, not about the continuous circle. Read at the
degree, which is what a real chart forces, delta < 0 wherever cos(2 phi) < −0.75 — a window **41.4
degrees wide**, so **any separation from 69.3 to 110.7 degrees is a contest** [derived].

### 3.3 · The paper's own evidence

Reported as the paper reports it, and not restated more strongly: rank correlation **0.63** against an
author-assigned harmony ranking, at n = 7; and **100%** of 40,000 tradition-faithful rankings agreeing
in direction, with a median of 0.51 [paper].

### 3.4 · What is measured, what is derived, what was chosen

| | |
|---|---|
| **[measured]** | every position (§1) · every body's concentration (§5) · the whole census (§12) · the band (§12) · every ablation (§14) · the frame's size (§10) · the season (§11) |
| **[derived]** | the weight of a body pair, \|z_i\| \|z_j\| — it is what the average over the unknown hours equals (§4) · the mean separation · BRANCH · PEAK · the width of the contest window |
| **[paper]** | the two-phase model · the verdict rule · the margin · BASELINE = 0.75 |
| **chosen** | seven bodies rather than ten — but chosen *on a measurement*, §6 · the reference window and its epoch, §12 · a flat prior over the 24 hours of the day · the sidereal Lahiri frame, §10 · reading a date as a universal-time day, §2 |

There is no orb, no kernel width, no aspect list, no valence table, no per-body importance, no
exchange rate between easy and hard, and no reader's switch. That list is the point of the rewrite.

## 4 · The collapse: why the decomposition is an identity

A birth date fixes a day, so each chart is drawn 24 times and each pair 24 × 24 = **576** times.
Define for each body its **second-harmonic resultant** over the day's hours,

```
    z_b = (1/24) * SUM over the day's 24 hours of exp( 2i * L_b(hour) )
```

so |z_b| in [0, 1] measures how tightly the date pins that body's phase down, and arg(z_b)/2 is its
effective longitude. Because the 576-chart grid is **by construction** the Cartesian product of A's 24
hours with B's 24 hours, the double sum factorises, exactly:

```
    (1/576) SUM over the 576 charts of cos( 2 phi_ij )  ===  Re( z_j^B * conj(z_i^A) )
                                                       ===  |z_i| |z_j| cos( 2 Delta_ij )
```

That is not an approximation of the average over the unknown birth hours. It **is** that average, to
floating point. Held against the brute-force double sum in `tests/stability.test.ts`: worst
discrepancy per cell **2.4 × 10⁻¹⁵**, and for a whole chart **2.8 × 10⁻¹⁶** [measured]. So "weight
each body pair by how firmly the dates pin its angle down, and score it at its mean angle" is not a
modelling choice at all — it is what the expectation equals. The engine this replaces needed a
Gaussian kernel, a trapezoid integration and a printed error bar (median 9.8 × 10⁻⁶) to get near the
same place; here the explanation and the number are the same arithmetic.

Summing the cells collapses one step further. With Z = SUM over bodies of z_b,

```
    tau_bar = (1/N^2) * Re( Z_B * conj(Z_A) ) = ( |Z_A| |Z_B| / N^2 ) * cos( 2 Delta_AB )
```

so a whole chart reduces to **one complex number**, and the compatibility of two people is the cosine
of the angle between their two vectors.

**Stated precisely, because the loose version is easy to falsify.** The 49-cell matrix is exactly
**rank 2** — it is the outer product Re(z_j conj z_i), so it has two singular values and
then nothing above the floating-point floor [measured]. So the grid contains no information beyond
the two charts themselves, and the score contains nothing beyond |Z| and arg(Z), two real numbers per
person. It is *not* true that the grid reduces to two numbers per person; it reduces to each person's
seven body angles, and the score reduces further. This is disclosed rather than buried, because a
score with two parameters per person cannot hide a thumb on the scale — that is the trade, taken
deliberately.

**The one precondition.** The collapse assumes nothing about constant speed, Gaussian anything, or
independence between bodies. It assumes exactly one thing: that the 576 charts are a **Cartesian
product** — the two people's unknown birth hours are separate unknowns. That is load-bearing, it is
the right assumption, and it can fail: force the two hours to be equal and the identity breaks by
**2.6 × 10⁻⁴**, which is 10¹¹ times the floating-point error [measured]. Any separable per-person
prior over the hour keeps the collapse; a joint prior over the two destroys it.

And the ablation that undercuts this section rather than flattering it is in §14.1: the 576-chart grid
barely moves the score.

## 5 · The weights

Each body pair's weight is |z_i| |z_j|, and every one of those numbers is measured rather than set.

| body | concentration \|z\| [measured] | note |
|---|---|---|
| **Moon** | **0.9912** | range 0.98806 at 15.37 °/day to 0.99299 at 11.77 °/day — the only scored body a date leaves materially open |
| Sun | 0.99995 | |
| Mercury | 0.99991 | minimum 0.99975 |
| Venus | 0.99994 | |
| Mars | 0.99998 | |
| Jupiter | 0.9999988 | |
| Saturn | 0.9999997 | |
| Uranus, Neptune, Pluto | > 0.9999999 | pinned down *more* precisely than anything else — see §6 |

A phase spread perfectly uniformly round the circle has |z| = 0 exactly, and a test asserts that. The
important consequence of this table is the honest one: with every scored |z| at 0.988 or better, there
is very little for the averaging in §4 to do, which is exactly what §14.1 measures.

Two house rules travel with these: a circular average is always `atan2` of a resultant vector and
never a scalar mean of angles, so no readout can be broken by a wrap through 360; and the weights are
positive but never normalised.

## 6 · Why seven bodies and not ten, on the measurement

Uranus, Neptune and Pluto are pinned by a birth date more precisely than anything else, so a weight
built from concentration alone counts them **heaviest of all**. That is exactly why they had to be
measured out rather than argued out. Over every one of the 97,259,044 pairs in the reference window
[measured]:

| bodies | r vs age gap | population mean | population spread |
|---|---|---|---|
| the three outers **alone** | **+0.954** | −0.0859 | 0.0957 |
| all ten | +0.222 | −0.0092 | 0.0499 |
| **the seven shipped** | **+0.021** | −0.0002 | 0.0742 |
| the personal five | +0.002 | −0.0008 | 0.1138 |

The three outer planets alone are an **age-gap meter with an astrology label**, at r = 0.95. The
direction is worth stating because it is not the obvious one: two people born a few months apart have
all three sitting on top of each other, the model reads that as being in the same place, and that is
filed with the hard aspects. So including them **penalises being the same age** — mean −0.179 at a gap
of zero, rising to −0.040 by twelve years — and it flattens the spread from 0.074 to 0.050, costing a
third of the score's power to tell anybody apart in exchange for a fact about the calendar.

Dropped, the population centres itself: mean −0.0002 with no centring device anywhere in the code,
which is why the file has none. The engine it replaces needed one, and its absence here is a result
rather than an omission.

Jupiter and Saturn stay. Their residual signal oscillates with their own periods instead of decaying
with the gap, so it is a cycle rather than a proxy for having been born in the same decade.

## 7 · The rising sign: 0.0430, not zero

The tempting claim is that the arithmetic deletes the rising sign and the houses for free: a phase
spread uniformly round the circle has |z| = 0, so the weight would be zero and no editor would have
to exclude anything.

**That claim is false, and the true one is better.** An ascendant does not sweep the circle uniformly
— it rises fast through some signs and slowly through others — and the residual second harmonic is

```
    |z_ASC| = tan^2( eps / 2 ) = 0.0430
```

where eps is the obliquity of the ecliptic [derived]. It is the **same value at every latitude from 0
to 60 degrees north**, and independent of the birthplace longitude. Even a perfectly uniform ascendant
would leave 2.8 × 10⁻³ on a grid of solar hours, because the sky turns 360.98 degrees in one. So the
rising sign is worth about 4% of a real body, not nothing.

What the arithmetic does instead is **flatten** it: arg(z_ASC) points the same way for everybody —
concentration 0.9987 across dates, at the solstice — so an ascendant admitted to the model would add
**the same constant to every pair alive** [measured]. It is excluded for that reason, which is a fact
about the geometry, and not for a zero that is not there. The page shows the 0.0430, because a reader
who has been told elsewhere that the rising sign matters most deserves the real number rather than a
rhetorical one. A test holds the geometry so the claim cannot drift back to "zero".

## 8 · The estimator: the mean of the 576 margins, not the margin of the mean

`Reading.tau` is the exact mean trace by §4. **It is not the score.** The score is the paper's margin
averaged over the 576 charts the two dates leave open — the expected *reading*, not the reading of the
average system.

The two agree for all but a hair of the population, because above the branch point the margin is
exactly −tau/2, a **linear** function, and there the mean of the margins is the margin of the mean. A
pair whose own 576 traces straddle the branch is a different matter: the margin has a vertical tangent
there, and the two definitions part company by as much as **0.044**, which is 59% of the population's
whole spread [measured]. So the estimator is the average of the margins **everywhere and in one code
path**, rather than a closed form that is exact about the average system instead of the average of the
systems. Over the census the closed form is provably valid on **99.850%** of pairs; the other
**146,101** pairs run the full 576-chart pass [measured].

Where the closed form *is* used — §13's scan and the census tool — it is licensed by a true bound
rather than a tolerance: no chart of a pair can have a trace below −|z_A(h)| |z_B(k)| / N², so when
that bound stays above the branch point, linearity is guaranteed and one dot product settles the day.
When the bound admits a sub-branch trace, the full pass runs. That is one code path with a proof
attached, not a fast path with a fudge factor.

Two exactness devices worth knowing about, because both were real defects first:

- **The 576 readings are sorted before they are summed**, and the mean is taken from the sorted array.
  Swapping the two people transposes the readings, which leaves them identical as a *set* but not as a
  sequence — and floating-point addition is not associative, so walking the grid the other way round
  moved the score by one unit in the last place. Sorting removes the dependence on the walk, which is
  what makes score(A,B) = score(B,A) hold **exactly** rather than to within an ulp. It is also the more
  accurate order to add in.
- **score(A,B) = score(B,A) is an identity, not an asserted invariant**, because cos(2 phi) is even in
  phi; lead(A,B) = −lead(B,A) likewise, because sin(phi) is odd. Neither needs the old engine's device
  of computing both orderings and averaging them.

The band shipped with every reading is the 5th-to-95th spread of that pair's own 576 readings, with
the minimum and maximum beside it — nine readings in ten, and no bell shape assumed.

## 9 · The contest channel, and the lead

Everything in §4 collapses. **One quantity does not**: the contest share. A saddle is a nonlinear gate
applied to each chart separately, so it carries information the score cannot.

Measured: two pairs whose traces agree to **4 × 10⁻⁷** differ in contest share by **8 percentage
points**, and the two quantities correlate only at **−0.80**. A random pair sits at about **23%**,
against a uniform baseline of 23.005% [measured]. That is why the contest share is reported in its own
right rather than folded into the score.

Two decisions inside it, both deliberate:

- **It is counted over the actual grid, not inferred from the mean**, because the gate is a threshold
  and a threshold does not commute with an average.
- **It is not weighted by |z|.** The 576 charts already *are* the birth-hour uncertainty; weighting by
  the concentration as well would count the same doubt twice. And the count is kept in **integers** —
  a count of grid slots is order-independent, so the share comes out bit-identical whichever person is
  put first, where a float accumulation of weighted shares was symmetric only to an ulp with a strict
  inequality riding on it.

**The lead** is the paper's l: the mean of sin(phi) across the charts where a cell **is** a saddle, and
zero when it never is. Positive means the second person is the one ahead, so they prevail in that
contest. It is defined only inside the contest window, which is where the paper defines it: averaged
over every cell instead, it names the **opposite** winner about one pair in six [measured]. A sin(phi)
from a cell that is not a saddle is not the paper's l at all.

## 10 · The frame, and what is genuinely invariant

Positions are sidereal (Lahiri). Every quantity in the model is a function of phase **differences**, so
moving the zero point of the zodiac by any **constant** changes nothing. A test asserts that exactly,
at shifts of 7.3, 0.001, −23.85, 180 and 359.9 degrees, and it is what proves no absolute longitude
has leaked into the arithmetic.

**It is tempting to go one step further and say the score is therefore the same tropical or sidereal.
That is false.** An ayanamsa is not a constant — it precesses — and the two people were born at
different times, so switching frames shifts their two charts by **different** amounts. Across this
window the Lahiri ayanamsa moves 0.377 degrees, and measured over 1,985,281 pairs the two frames
disagree by a mean of **2.4 × 10⁻⁴** and at worst **3.5 × 10⁻³** — 0.33% and 4.7% of the population
spread [measured]. Small, but not zero, and largest for the couples furthest apart in age.

The sidereal frame is therefore a real commitment here, not a relabelling, and this is its size.

## 11 · The season: the model's biggest single property

cos(2 phi) is 180-degree periodic, which is what the symmetry of an aspect demands — and it means the
model **cannot tell being in the same place from being directly opposite**. Both are tau = +1 and both
strain. Followed through to real people, that says something startling: two people born on the same
day of the year have their Sun, Mercury, Venus and Mars nearly on top of each other, so they can never
settle. Over the census, **every** same-date pairing scores below zero, without exception; so does
the MEAN of every day-of-year gap near six months, though not every pair in it — the best pairing six
months apart still reaches +0.192.

| day-of-year gap | 0 | 30 | 60 | 91 | 121 | 152 | 182 |
|---|---|---|---|---|---|---|---|
| mean score [measured] | −0.070 | −0.027 | +0.037 | +0.047 | +0.031 | −0.017 | −0.059 |

Best at about a quarter of a year apart; worst together and worst opposite. And the size of it:
**0.2577 of the score's variance is nothing but the distance between two birthdays in the calendar
year** [measured].

The engine this replaces measured **0.100** on the same test. So this is a real **regression** on that
one axis, taken knowingly in exchange for exact arithmetic, no invented constants, and a fivefold
improvement in what two dates can resolve (§12).

It is not a bug and it is not fixable without breaking the derivation: a date-only model reads the
calendar, because the Sun's longitude **is** the calendar. The old engine hid it by reading mostly the
Moon. This one states it, measures it, and shows it — a reader who tries two friends born in the same
week meets the model's worst case, and should find it already explained.

## 12 · The census, and the percentile

**There is no sample and no seed.** The old table was "20,000 random pairs, seed 13579" because
scoring a pair cost 576 × 49 exponentials. The collapse makes a pair cost one dot product, so the
reference population is computed **exhaustively**: every ordered pair of birthdays in the window, all
**97,259,044** of them. A percentile from a census cannot be a sampling artefact, and there is nothing
left to reproduce — only to recompute.

**The window** is every birthday of a person aged 18 to 44 at a stated epoch: **1981-08-05 to
2008-08-04, 9,862 days**, epoch **2026-08-04**. Two properties, both deliberate:

- *The same window for everybody.* A window relative to each person ranks each person against a
  different population, so two people's readings could not be compared and "you are in the 90th
  percentile" would mean a different thing on each screen.
- *A constant, never today.* A window that moves at midnight makes every committed number, and every
  test that guards them, silently wrong the next morning. Moving it is a deliberate release act: bump
  the epoch, re-run the calibration tool, paste the table back. A test fails if the constants and the
  window stop agreeing.

| | [measured, census] |
|---|---|
| mean | −2.454 × 10⁻⁴ |
| spread | 0.074195 |
| minimum | −0.463709 — **2000-05-18 paired with its own date** |
| maximum | 0.321482 — 1989-05-22 with 1992-04-14, short of the derived ceiling 0.322876 by 1.39 × 10⁻³ |
| settles | 49.9119% — 48,543,844 |
| strains | 50.0875% — 48,714,606 |
| contest | 0.0006% — **594** |

The worst pairing that exists is a date paired with itself, and its score is exactly minus half the
largest trace two dates can reach — the two facts are the same fact. The aggregate contest class is
real and vanishing, which is precisely why §9 is reported separately.

**Each chart as one vector** [measured]: |Z| lies in [0, 7] and the census finds a minimum of 0.0252
(1981-12-15), a maximum of 6.7412 (2000-05-18) and a median of 2.9035. So |tau| reaches **0.9274** of
its theoretical 1.0, and the interior optimum tau = −0.6458 is comfortably reachable.

**The percentile table** shipped in `src/engine/stability.ts` is 41 steps spanning −0.32 to +0.32,
each entry the share of the census scoring at or below that step, and it is generated by the tool in
§18 rather than typed. A drift test recomputes a slice in CI and fails if the numbers go stale,
because a shifted distribution must never leave an old table on the page.

**The resolution limit, reported as a result** [measured]:

| | |
|---|---|
| population spread of the score | 0.074195 |
| median width of the 90% band **one pair** spans over its own 576 charts | 0.012101 |
| bands measured | 8,100 real pairs, a 90 × 90 grid of days across the window |
| ratio | **0.163** |

Not knowing the two birth times costs about 16% of the whole difference between one couple and
another. That is the ceiling on what two dates can resolve, and it is where this model gains most on
the one it replaces: there the same ratio was **0.85**, and only about two pairs in five could be told
apart at all. Aggregating over all 49 cells is what bought it — the Moon is the only body a date
leaves open and it appears in 13 of the 49. Any page printing a compatibility percentage from dates
alone without a band is claiming a precision the input does not carry. That is arithmetic, not
criticism.

## 13 · The scan: the most this person could score, and against whom

`scanWindow` scores **every one of the 9,862 days** in the reference window against one person, one
day at a time, and reports the best, the worst, the median, a histogram, and the number of days that
cannot be told apart from the best.

- Each day's whole contribution is three numbers — its mean chart vector and its largest hourly
  length — so 9,862 days is about 237 KB and nothing needs shipping or caching.
- The closed form is used **where it is provably exact and nowhere else**, licensed by the bound in
  §8. Over the census that is 99.850% of pairs; the remaining 146,101 run the full 576-chart pass
  [measured].
- It yields the fraction done so a browser can run it in slices of a frame. A panel that freezes the
  page for a second while you scroll it is broken.

**The number that matters is indistinguishability, not ties.** How many days cannot be told apart from
the best one — within one band width of it [measured]:

| person | days indistinguishable from the best | of |
|---|---|---|
| 1985-03-15 | 15 | 9,862 |
| 1999-11-02 | 11 | 9,862 |
| 1992-02-29 | 19 | 9,862 |

About **one day in 600**. Exact ties: **1**. The page this replaces printed "71 days out of 8,767" tied
at the ceiling; because the score is now continuous, exact ties are a question about rounding rather
than about people, and the honest equivalent is the table above. It puts the same stake through the
one-soulmate idea, and it is the most useful sentence on the panel.

## 14 · Robustness, and every ablation

Rank correlations below are Spearman, against the model exactly as shipped, on a 400-day grid of the
window (160,000 pairs). Reproduced by the tool in §18.

### 14.1 · Three that undercut the model rather than flatter it

Reported first, and at least as prominently as anything favourable, because the paper this borrows its
shape from reports its own centring as worth "only ~0.003 AUC".

| ablation | result [measured] | why it stays |
|---|---|---|
| **the 576-chart grid**, replaced by a single noon chart | mean difference 3.4 × 10⁻⁴ (0.45% of the spread), correlation **0.999983** — but worst case 2.4 × 10⁻², which is **33%** of the spread | it is not an approximation of the average over the unknown hours, it **is** that average (§4); and it is what produces the **band**, which is the part of the answer that needed it. Every concentration is at least 0.988, so there is little for the averaging to do |
| **the eigenvalue nonlinearity**, replaced by plain −cos(2 phi)/2 — the paper's contest class thrown away | Spearman **0.999956**. It fires on **594** pairs in 97 million | it is the paper's own verdict function, and without it the best possible match would be the most anti-aligned pair — which the paper calls a contest |
| **BASELINE**, swept across the paper's stated band | 0.9926 (0.50) · 0.9991 (0.60) · **1.0 (0.75)** · 0.99996 (0.90) · 0.99996 (1.00) | the ordering barely depends on the only number in the model that was not derived here. Reporting that is the point |

So the mathematical centrepiece is nearly **inert**, and the apparatus that computes 576 charts moves
the typical score by half a percent of its own spread, and the worst by a third of it. Both belong on
the record: saying so beats letting a
derivation imply an importance it does not have.

### 14.2 · The body set

The table in §6, which is the one ablation that changed the shipped model. Everything else here left
it alone.

### 14.3 · What robustness cannot cover

Two properties are **not** robust and are not presented as such: the **season** (§11, 0.2577 of the
variance) and the **frame** (§10, worst 4.7% of the spread). The first is a consequence of the
harmonic and cannot be removed without abandoning the derivation; the second is a real commitment to
the sidereal zodiac. Both are measured and printed rather than defended.

## 15 · The empirical null

Voas (2007), roughly **10 million married couples** from the 2001 England and Wales census: **no**
sign-compatibility effect, bounded below about one couple in a thousand.

So there is no outcome to fit to, and any model claiming to have *learned* compatibility would be
lying. **Nothing here is fitted.** What is computed is a different and answerable question: under the
tradition's own rules, stated openly, where does this pair fall among every pairing in the reference window?

## 16 · What was removed

All of it worked, all of it was verified, all of it is in the git history. It went because the
standing instruction is that everything must be logical or stripped away, and each of these contained
numbers nobody could source.

- **The eight-test Vedic Moon score out of 36** (`kuta.ts`, `nakshatra.ts`, `score.ts`,
  `interpret.ts`, `corpus.json`) — lookup tables reconstructed from Sanskrit sources, one of the eight
  ranking four temperaments in an order inherited from a caste hierarchy. Not derivable.
- **The continuous affinity fit** (`affinity.ts`) — a Gaussian kernel on five traditional aspect
  angles, with its widths taken from a 1647 orb table and halved by a convention of ours.
- **The valence table** (sixth +0.5, third +1, quarter −1, opposite −1): the tradition names which
  angles are easy, and the magnitudes were ours.
- **Benefic/malefic natures** and **per-body importance** — labelled at the time as "the sources rank
  these; none numbers them", which was honest and is not a defence.
- **The ease/friction split** and the exchange rate between them; and **the reader's switch** that read
  the opposite angle as easy, which was the single choice that moved the ordering most.
- **The random-angle null subtraction** and the exact trapezoid expectation it needed. A centring
  device is only needed by a score that is off-centre by construction; this one centres itself (§6).
- **Both 20,000-random-pair calibration tables and their seed** — replaced by the census (§12).
- **The "effective aspect angle"**, 0.5 · acos(tau_bar). It was appealing, because the aggregate lies
  on the same one-parameter family as a single aspect. It went because it is a monotone
  reparameterisation of the trace and so carries nothing new, and because its reachable range over
  real charts is only about 11 to 75 degrees: it can never report 90, so a reader shown "your
  effective aspect is 70 degrees" would reasonably conclude they were near a square when they were at
  the far end of the whole scale. One number that cannot say what it appears to say is worse than no
  number.

## 17 · Privacy

Manual entries live in `localStorage` and are never transmitted; there is no server. Public entries
come read-only from profiles whose owners already publish their birthday. Share links carry only names
and dates — the receiving browser recomputes everything. Messaging deep-links into ArtaQuest's
existing end-to-end-encrypted chat rather than reimplementing one.

## 18 · Reproducing every number in this document

```bash
npm test                                   # §1 ephemeris vs the committed Swiss Ephemeris golden
                                           # data; §4 the collapse against brute force; §3 the
                                           # paper's published census and algebra; §7 the rising
                                           # sign's 0.0430; §8 the exact symmetries; the ceiling

python3 tools/golden.py                    # §1 regenerate golden.json (needs pyswisseph + the
                                           # ephemeris files)
node tools/compare-elements.mjs tests/golden.json   # §1 the Table 1 vs Table 2a decision

# §5, §6, §9-§14: the census, the percentile table, every ablation, the band, the scan
echo 'export * from "./src/engine/stability"; export * from "./src/engine/ephemeris";' | \
  npx esbuild --bundle --format=esm --loader:.ts=ts --sourcefile=e.ts --outfile=/tmp/aq.mjs
node tools/calibrate-stability.mjs /tmp/aq.mjs

node tools/contrast.mjs                    # WCAG contrast, every ink/surface pair
node tools/screenshot.mjs dist shots/      # real-browser audit of the built bundle, five widths
```

The calibration tool is bundled through stdin because `--outdir` writes `.js`, which node in `/tmp`
reads as CommonJS. It prints the percentile table in the exact form it is pasted back into
`src/engine/stability.ts`, so the shipped constants and the census can never quietly disagree.

And the standing caveat, which is part of the method: there is no known mechanism by which any of this
could work. These are old, internally consistent ways of talking about people — reported faithfully,
calibrated honestly, and predicting nothing.

## Edition V — Till Death Do Us Part (2026-09-01)

A second reading on the page, from a different corpus and a different model family to everything
above. It answers the opposite question: not *does this last* but *did it come apart*.

### The corpus

**175,155 marriages** between people with recorded birth dates, harvested from Wikidata
(`P26` spouse statements, every birth decade 1500–1990) and Wikipedia prose. A marriage counts as
having come apart — **9,682 of them, 5.53%** — when
the record says so explicitly, by any of six routes:

| evidence | pairs |
|---|---|
| remarriage while the other partner was still living | 5,377 |
| an explicit `P1534` end cause (divorce, annulment, separation) | 2,739 |
| a couple-bound phrase in the prose ("they divorced", "their separation") | 2,196 |
| an end date more than a year from either death | 2,069 |
| a per-couple judgement of the article text | 1,813 |
| recorded infidelity | 573 |

Everything else is a negative: presumed till-death. Couples enter only when the marriage is
*provably over* — both born before 1950, or both deaths recorded — so a marriage still running is
never counted as one that held. 22 pairs whose records contradict each other were dropped rather
than resolved by a coin toss. Partial birth dates are kept, imputed to the middle of the known
window (78,830 of them); the slow bodies that dominate the model are barely moved
by a few months, and the fast terms simply attenuate.

### The model

```
score = bias + Σ w · cos(angle)  +  w · sin(angle)          p = sigmoid(score)
```

**64 terms** over 13 sidereal bodies (Lahiri, noon UT), in three families — and every one of them
needs **both** birth charts. No placement, aspect or midpoint belonging to a single person is
admissible, because such a feature is not evidence about a couple:

- `diff  man[i] − woman[i]` — the same-body synastry aspect
- `sum   man[i] + woman[i]` — the couple's midpoint axis for that body
- `xdiff man[i] − woman[j]` — the cross-body synastry grid

Each term is one cosine or one sine of one named angle, at the fundamental harmonic only. The score
is `bias + Σ wₜ·trigₜ(angleₜ)`, through a sigmoid. Fitted by the closed-form solver: three explicit
Newton steps on balanced BCE, the first of which is the weighted least-squares solution.

**Ten-fold grouped cross-validated AUC 0.7366**, folds cut by connected component of the marriage
graph so a person never appears on both sides of a split, averaged over three fold seeds.

### The number that matters, and it is not the AUC

The operator's two baselines are the same model fitted on **one** partner's chart alone, given the
complete solo algebra — placements, own aspects, own midpoint axes — on this corpus and these folds:

| model | AUC |
|---|---|
| **the pair-only model (64 terms)** | **0.7366** |
| her chart alone (339 params) | 0.7362 |
| his chart alone (339 params) | 0.7309 |
| signed birth-date gap (2 params, sanity only) | 0.5422 |

Reading **both** charts together buys **+0.0004** over reading one of them. That is not a small
effect; on 9,682 positives it is indistinguishable from nothing. The corpus can tell a 1650 marriage
from a 1950 one and it can rank a person, but two charts read as a pair say no more than one chart
read alone. This is the finding, and the page prints it beside every reading rather than showing the
percentile on its own.

An earlier edition of this model reached 0.7430 — by including his placements, her natal aspects and
her midpoint axes. It beat one partner's chart by 0.005 while claiming to read a pair, which is why
single-person families are now banned outright and `web/verify_docs.py` refuses to publish a model
containing one.

### What was tried and rejected

Under the pair-only rule, backward elimination dropped **cross-body couple midpoints**
(`man[i] + woman[j]`, removing them *helped* by 0.0018) and **composite-internal aspects**
(`(man[i]+woman[i]) − (man[j]+woman[j])`, no cost). Of the survivors, the cross-body grid carries
most of the signal: removing it costs 0.0200, against 0.0017 for the same-body differences and
0.0004 for the couple midpoints.

Rejected earlier, each measured rather than assumed: every harmonic above the fundamental (the
classical aspect ladder — trine as the 3rd, square as the 4th — adds nothing on this target); the
complete quadratic mixing of the basis (5,565 parameters, worse); and all four three-body families,
Ebertin's midpoint contacts and the Hellenistic lots among them. Out of reach with date-only data,
and recorded rather than silently skipped: houses, angles, declinations and planetary speeds.

### Honest limits

- **Term pruning chose 64 by looking at the curve**, so 0.7366 carries a little selection optimism;
  the family-level figure before pruning was 0.7316.
- **Which separations it sees.** Sliced by evidence, out of fold: P1534 0.781 · end-date 0.713 ·
  judge 0.808 · text 0.757 · infidelity 0.666 · remarriage 0.747. It reads a documented divorce far
  better than a documented infidelity.
- **A harder target.** Trained and scored on the confident core only — explicit separation against
  explicit till-death — five-seed AUC was **0.7165** for the earlier model family. Both numbers are
  real; the stricter one is what to quote against a sceptic.
- **The corpus is wider than the page.** 168,541 of the 175,155 couples fall inside the shipped
  1598–2200 ayanamsa span; the fit used precomputed positions, so the remainder trained the model
  but cannot be reproduced in the browser.
- **What it cannot do.** It reads two birth dates. It knows nothing of the people.
