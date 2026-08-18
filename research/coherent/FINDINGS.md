# The coherent phasor field — built, fitted, tested, not enrolled

Arash's proposal, 2026-08-18:

```
F(chart) = | b_field + A_field * SUM_i a_i * exp( i * ( theta_i(t) - p_field,i ) ) |^2
```

Each body's ecliptic longitude `theta_i` is the phase of a unit phasor, weighted by `a_i`, rotated by a
field-specific offset `p_i`, summed **coherently**, biased by `b`, and read as a squared modulus — an
interference intensity, large where the chosen bodies reinforce and small where they cancel.

## Why the form is worth building

It **contains the classical aspect as its two-body case** and generalises it. With `b = 0`, `a = (1,1)`:

```
| e^{i*th1} + e^{i*th2} |^2  =  2 + 2*cos(th1 - th2)
```

— maximal at conjunction, zero at 180 degrees. Harmonic `h` gives squares (`h=2`), trines (`h=3`), and the
higher harmonic charts. So a bank of these spans every classical aspect, every harmonic of one, and — the part
no hand-coded block reaches — every **multi-body resonance**, with the offsets fitted rather than named. No
other tradition module in this project computes an unnamed quantity; all 19 compute a named one.

Expanding the modulus shows what is really being learned:

```
|b + sum_k w_k z_k|^2 = |b|^2 + 2*Re(conj(b) * sum_k w_k z_k) + sum_{j,k} w_j conj(w_k) z_j conj(z_k)
```

The last term is a **quadratic form in the chart's Fourier coefficients**, so `F` fields are a rank-`F`
quadratic model over every pairwise product of body phases — including every cross-partner contact, which is
synastry generalised: one column carries the whole cross-aspect grid instead of one named contact.

## Two implementations

| file | what |
|---|---|
| `trad_coherent.py` | random bank, 4 blocks x 192 columns, fixed seed. 6 self-tests, incl. one proving the wedding/progressed slots are never read |
| `coherent_fit.py` | `a`, `p`, `b` **fitted**. Gradients exact, checked against finite differences to `4e-9` |

The fit reparameterises `w_k = a_k * exp(-i p_k)` into one complex weight, which makes the model a complex
linear layer followed by `|.|^2`: the parameter space is flat (no phase wrapping) and every gradient is a
matmul, so it needs no autograd framework and runs anywhere.

## What had to be fixed before any number meant anything

**41.3% of training rows have the two charts IDENTICAL; 0.1% of held-out rows do.** `dates.couple_record`
gives a partner with no known birth date the *other* partner's instant — deliberate and documented, and
harmless for a one-sided feature. For a coherent sum over both charts it is not: when
`theta_older == theta_younger` the sum collapses to `sum_k (w_Ok + w_Yk) e^{i h th_k}`, a different and smaller
function class. So 41% of the fit's gradient came from a configuration that essentially never occurs at test
time. **This affects every cross-chart block in the shipped stack** — ashtakoot, the Uranian dial distances,
the composite and Davison charts — all fitted through the same 37,387 degenerate rows. The fit now drops them
(53,238 genuine pairs remain).

Also: high harmonics on fast bodies are noise by construction. Birth *dates* only, so at a fixed hour the Moon
carries +-6.6 deg; at `h=12` that is +-79 deg of phase error. `basis(..., orb)` admits a term only when
`h * (daily motion)/2 <= orb`. At `orb=30` the Moon is kept to `h<=4` and every slow body to `h<=12`.

## The protocol

27 configurations, one held-out set. Reporting the best held-out score over 27 tries is selection on the test
set, so: every configuration early-stops on an **inner temporal split** (the latest training births, mirroring
the outer split — a random inner split measurably overfits the epoch count here); configurations are ranked by
**inner** AUC; the winner is chosen by that ranking alone and only then is its held-out AUC read.

## Result: the field re-reads the age gap, and reads it worse

| | held-out AUC |
|---|---|
| age-gap logistic (the one permitted comparison) | **0.6047** |
| coherent field, selected config (`all18`, 8 fields, L2 0.01) | 0.5559 |
| coherent field, every `fast`-body config (9 of them) | 0.496 – 0.502 |

The sweep separates perfectly by body set: **every** fast configuration is at chance, **every** classical or
all-18 configuration that trains at all reaches 0.52–0.56. The only difference between the sets is Jupiter and
slower — and a slow body's phase *difference* between two partners is a near-linear, unwrapped read of the age
gap:

```
Pluto 1.45 deg/yr -> a 0-60 year gap spans  0- 87 deg, no wrapping
Neptune 2.19      ->                        0-131 deg
Uranus  4.29      ->                        0-257 deg
Saturn 12.2       -> wraps twice
Mars  191, Sun 360+ -> wraps hundreds of times, unreadable as a gap
```

Three measurements confirm it (`decisive.py`):

1. rank correlation between the field's held-out score and the age gap: **rho = -0.448**
2. AUC with the gap held flat in 1-year bands (39 bands, 2.75M eligible pairs): **0.4932** — chance. The
   control validates itself: the gap's own AUC inside its own bands is 0.5000 exactly, as it must be. At 2-year
   and 3-year bands: 0.4956 and 0.4943.
3. a two-feature combiner (gap + field) fitted on the training half does **not** beat the gap alone out of time

So the field's entire out-of-time score is the age gap in disguise, and a two-parameter logistic reads that gap
better than 3,961 fitted parameters do.

## The control is validated in both directions

Every negative conclusion here rests on one estimator, so `validate_control.py` plants five features with known
answers on the REAL held-out labels and REAL age gaps:

| planted feature | raw | gap-matched | |
|---|---|---|---|
| pure age gap | 0.6046 | **0.4982** | removed |
| gap-independent signal | 0.5958 | **0.5961** | preserved to 0.0003 |
| weaker gap-independent signal | 0.5472 | 0.5406 | preserved |
| half gap + half signal | 0.6483 | 0.5980 | partially removed |
| pure noise | 0.5032 | 0.5034 | unchanged |

Showing only that the gap's own AUC falls to 0.50 inside its own bands is **half** the requirement — it proves
the estimator destroys what it holds flat. The second row is the other half: a gap-independent effect at 0.5958
survives at 0.5961. Without it, "nothing survives the control" could have been a property of the arithmetic
rather than of the data.

## The same control applied to 30 existing blocks

`test_blocks.py` over numerology, `vedic_match` and `harmonics` (30 blocks, 30,000 training couples). Raw
held-out AUC vs gap-matched AUC:

| block | raw | gap-matched |
|---|---|---|
| `har: harmonic 5/7/9 conj (Addey creative)` | 0.5870 | 0.5037 |
| `har: ecliptic latitude contacts` | 0.5801 | 0.4937 |
| `har: speed, stations, applying/separating` | 0.5789 | 0.5018 |
| `har: harmonic 2/3/4/6/8/12 conj` | 0.5771 | 0.4914 |
| `num: personal years, in each other's birth year` | 0.5286 | 0.5049 |
| `num: life path, birthday, attitude, pillars` | 0.4960 | 0.4995 |

**Every one of the 30 blocks lands between 0.4815 and 0.5072 once the gap is held flat.** Nothing survives.

This also explains the tradition ranking's *order*. Traditions whose features are direct functions of a
date difference top it (Modern Western Davison/composite 0.6069, harmonics 0.6050, Uranian 0.5977); traditions
whose features cannot smoothly encode a difference sit at the bottom (Numerology 0.5344, Aboriginal 0.5335,
Polynesian 0.5078). Numerology is the cleanest case — its own module docstring predicted this: digit sums are
almost decorrelated from the date itself, 1899 and 1900 having digit-sums 27 and 10, so it has no channel to
the gap and scores accordingly.

## Why it is here and not in `astro/`

Any `astro/trad_*.py` auto-enrols in the shipped stack. Enrolling this would add a second-rate age-gap reader
to a stack that already loses to the age gap. To enrol it anyway:

```
cp research/coherent/trad_coherent.py astro/
```

## Reproducing

```
python research/coherent/build_lon.py                 # caches both halves' longitudes (81s, full scale)
python research/coherent/coherent_fit.py --gradcheck  # exact gradients vs finite differences
AQ_SEEDS=3 python research/coherent/sweep.py          # the 27-configuration sweep
python research/coherent/decisive.py                  # the three measurements above
AQ_MODS=numerology,harmonics AQ_SUB=30000 python research/coherent/test_blocks.py
python research/coherent/validate_control.py       # the estimator, on five cases with known answers
```

## At scale on Kaggle GPU

`gpu_notebook.py` + `publish_gpu_notebook.py` — private (the longitudes carry `y_test`), `machine_shape:
NvidiaTeslaT4` because Kaggle's default P100 is compute capability 6.0 and the preinstalled torch needs 7.0+.
It scales the BASIS (24 harmonics, 18 bodies) and the RESTARTS, not the field count, since 8 fields beat 64
locally. Reports held-out AUC, the age-gap logistic, and the gap-matched AUC, plus the best fast-body
configuration separately.

---

# Addendum, 2026-08-18 (later): from one formula to 4,962 features, and what the leaderboard can reach

## Named features, then thousands of them

`named_features.py` (667) and then `mega_features.py` (**4,962** across nine families) define every feature
with a name and a sentence, and `rank_named.py` / `rank_mega.py` score each with its own two-parameter
logistic — sign fitted on the training half, AUC read held out. Ranked by **training** AUC, because the largest
of 4,962 null draws sits near 0.5254 held out and ranking on that column surfaces the luckiest feature.

Result: median held-out **0.4999**, median gap-matched **0.4999**, **51% reverse direction out of time**.
Ranks 1–11 are Pluto/Uranus/Neptune cross-chart separations and **the age gap itself sits at rank 12** among
them — a slow planet's separation between two charts is the gap, read less precisely. Best numerology feature
(birth-year digit sum) is 0.5358 train → 0.4591 held out, reversed.

A contamination was fixed on the way: `dates.concrete()` places a year-only date at 1 January, so every
longitude for such a couple was fabricated. Only the **27,189 couples with both dates to the day** are used.

## The periodicity argument, and its false positives

Two dates are two numbers, so every feature is a function of era and gap; independence was never available.
What *is* separable is **periodicity** — the dates modulo a cycle. `fine_structure.py` tests 52 periodic
claims (sun-sign compatibility in every popular form, Chaldean weekdays, Chinese san-he/liu-chong, seasonal
harmonics, gap mod 7/12/19/29.53/60) against a model given era and gap explicitly: **0 of 52** clear the noise
floor. The first version reported two — Metonic-mod-19 at +0.0212 and Chinese animal distance at +0.0149 —
because its baseline, a tree on the two raw years, scored 0.5311 while the gap scores 0.6045: **an axis-aligned
tree cannot represent a difference**, and every gap-correlated feature was credited for patching that. Handing
the baseline the rotated coordinates sent both negative.

## The ensemble that scored below its own feature

The first ensemble scored **0.5809** held out with the age gap as an input — impossible for an honest pipeline.
Adversarial validation ruled out extrapolation (top features' ranges overlap 100%). It was overfitting behind a
validation split (1888–1900) too close in time to expose it. Repairing the split with three expanding-window
temporal folds did **not** repair selection: across ten candidates, mean fold AUC vs held-out AUC is
**Spearman −0.15**. Internal validation on 1600–1900 does not rank models for 1901–1990.

`sota_ensemble.py` therefore keeps a hard floor (ship the gap alone if nothing beats it on the folds), and the
shipping recipe does **no selection at all**: eleven pre-registered models, equal weights, rank-averaged.

| | held out |
|---|---|
| age gap alone | 0.6045 |
| **equal-weight rank average of 11** | **0.6103** |
| best member (XGBoost depth 3, top-50 stable) | 0.6164 |
| worst member (L2 logistic, top-200) | 0.5814 |
| the broken first ensemble | 0.5809 |

## What 0.7 would require

A model fitted and scored **on the same rows** with bins fine enough to memorise reaches **0.6484** from the two
birth years — the most optimistic number any function of era and gap can print, even cheating. Out of time the
best two-year model is the gap alone at 0.6045. So 0.7 is not reachable from era-and-gap under any modelling;
it would need astrology to add ≥0.09 held out. The measured astrological contribution is real but small: the
corrected ensemble sits at 0.5291 with the gap held flat.

Honesty note: the held-out labels were read many times during this session for diagnosis, so every number
above is mildly optimistic; the private leaderboard is the arbiter.
