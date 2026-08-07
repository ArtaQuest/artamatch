# Does the angle between two people's planets predict how many children they had?

No. This is the study that establishes it, on every past marriage in Wikidata.

No tradition is used anywhere here. Nothing is taken from Ptolemy, nothing is graded soft or hard,
and no angle is assumed to mean anything. The features are raw angle differences, the weights are
fitted, and the only question asked is whether the fitted model predicts a real outcome on data it
has never seen.

## The model

Exactly the form specified:

```
children  ~  ( b + SUM_i w_i · f( θ_i(father) − θ_i(mother) ) )²
```

`f = sin` is the **gender-sensitive** model: sin is odd, so swapping the two people flips every
feature and changes the prediction. `f = cos` is the **genderless** one: cos is even, so swapping
changes nothing. Fitting a free phase per body is not a third model — `w·sin(Δ − p)` expands to
`(w cos p)·sin Δ − (w sin p)·cos Δ`, so amplitude-and-phase per body *is* a sin coefficient and a cos
coefficient per body, which is the row called "both harmonics".

Fitted by ordinary least squares of `√y` on the features — the variance-stabilising transform for a
count, which makes `μ = u²` an exactly linear problem — then refined by Gauss-Newton against squared
error on the count itself, so the R² below measures what it appears to.

## The data

`node research/collect.mjs ./research/data` — every past marriage on Wikidata, with both partners' birth dates
known to the day, and the number of children the two of them had **together**.

| | |
|---|---|
| spouse triples in Wikidata | 930,634 |
| male–female pairs | 461,643 |
| same-sex pairs (no father/mother to difference) | 2,668 |
| both partners have any birth date | 231,225 |
| both known to the **day** | 131,348 |
| **ended by death or divorce** | **99,495** |
| … within the ephemeris's verified window, 1800–2012 | 83,905 |
| … minus placeholder birth dates (see below) | **77,911** |
| couples with at least one recorded child | 47,673 |
| children counted | 118,885 |
| marriage duration known (start date recorded) | 41,046 |

A marriage counts as past only if its statement carries an end date or a partner has a recorded date
of death. No inference from age: a couple born in 1750 with no death date recorded is certainly dead
and certainly not still married, but Wikidata does not say so, and this dataset counts only what is
recorded. That strictness costs 23,119 couples.

### Why not the Wikidata Query Service

Because it cannot answer this completely and does not say so when it fails. WDQS has a 60-second
limit and returns whatever it managed, as a well-formed response with no error. Measured here, on the
same query minutes apart: **930,633 marriage rows one run and 878,746 the next**. Its marriage
end-date query returned **46,822 rows against a true 104,145** — missing more than half the divorces,
and looking fine. Partitioning made it worse, because the cost is the scan and not the answer: a
`STRENDS` filter that should have cut the work tenfold timed the query out instead, and a filter on
the birth year timed out on every decade.

The data therefore comes from QLever's public Wikidata endpoint, which holds a full dump, answers in
seconds and carries the whole statement model. **Every query is checked against a COUNT of its own
WHERE clause**, which is what caught the truncation above.

### Placeholder birth dates, removed

Wikidata truncates a year-precision date to 1 January and a month-precision date to the 1st. This
dataset only admits statements *flagged* day-precision, but the flag is not always honest — somebody
entering "born 1847" as a day-precision 1 January leaves no trace in the precision field. It shows up
in the distribution instead. Over all 198,985 birth dates collected, against the 0.274% a calendar day
should hold:

| | share | vs expected |
|---|---|---|
| 1 January | 0.430% | **1.57×** |
| the 1st of any month | — | **1.10×** |

A placeholder puts a person at a planetary position they were never at: noise in the features with no
matching noise in the target, which can only wash a real effect out. **All 1st-of-month births are
excluded** (`EXCLUDE=firsts`, the default), which drops 5,994 couples — a couple goes if *either*
partner is affected, because the features are differences and one bad date spoils all ten.
`EXCLUDE=jan1` drops only 1 January; `EXCLUDE=none` keeps everything, for comparison.

### Triple-checked

`node research/verify.mjs ./research/data` — three checks that can each contradict the others, and one bundle
of internal consistency. All pass. Four things they caught:

1. **The RDF value is proleptic Gregorian whatever the calendar tag says.** Shakespeare's statement
   is tagged Julian and reads 1564-05-03, which is 23 April Julian converted; Newton's reads
   1643-01-04 for 25 December 1642 Julian. The ephemeris also works in proleptic Gregorian, so the
   two agree and nothing is converted — but the Action API returns the date **as entered**, so the
   cross-API check reported three mismatches out of forty on its first run, every one of them off by
   exactly 12 or 13 days. The check converts now; the dataset was right.
2. **BCE dates lost a digit.** `slice(0, 10)` on `-0009-07-31T…` gives `-0009-07-3`. Four Roman
   couples were mangled that way until the consistency check found them.
3. **Three marriages ended before a partner was born.** Genuinely impossible source data. Dropped and
   counted, not quietly removed.
4. **The target is undercounted, badly.** Children are counted by co-parentage, which is exact per
   couple; Wikidata's own stated count (P1971) is an independent number entered by other editors. On
   the 6,434 people who married exactly once and have both, they agree only **16.4%** of the time,
   co-parentage is lower **83.1%** of the time, and it recovers **30%** of the stated children. A
   child is only counted if that child has their own item. This is measurement error in the target,
   which is why the result below rests on a permutation null and not on an R².

## The result

An **80/20 train/test split**, grouped by person so nobody straddles it — a person is assigned a side
once and both of their marriages follow. R² is against the training mean: zero means "no better than
guessing the average couple", negative means actively worse.

Two targets, because the sky should be as free to predict how long a marriage lasted as how many
children came out of it.

### Target: number of children — 77,911 couples, 62,256 train / 15,655 test

| model | astrology alone | + era & age gap |
|---|---|---|
| **gendered (sin)**, all 10 bodies | **0.01841** | 0.09756 |
| genderless (cos), all 10 bodies | 0.00909 | 0.09653 |
| both harmonics, all 10 bodies | 0.02243 | 0.09769 |
| **gendered (sin)**, no outer planets | **0.00956** | 0.09666 |
| genderless (cos), no outer planets | 0.00017 | 0.09628 |
| both harmonics, no outer planets | 0.00966 | 0.09684 |
| **era & age gap alone, no astrology** | — | **0.09501** |

### Target: years of marriage — 38,218 couples, 30,446 train / 7,772 test

| model | astrology alone | + era & age gap |
|---|---|---|
| gendered (sin), all 10 bodies | 0.04923 | 0.16525 |
| **genderless (cos)**, all 10 bodies | **0.05775** | 0.16402 |
| both harmonics, all 10 bodies | 0.06656 | 0.16509 |
| **gendered (sin)**, no outer planets | **0.01257** | 0.16496 |
| genderless (cos), no outer planets | 0.00800 | 0.16384 |
| both harmonics, no outer planets | 0.02139 | 0.16451 |
| **era & age gap alone, no astrology** | — | **0.16410** |

**Which of sin and cos wins depends on what you ask it to predict.** Gendered wins on children
(0.0184 against 0.0091) and loses on marriage length (0.0490 against 0.0573) — then wins again on
marriage length once the outer planets come out (0.0126 against 0.0081). A property of two people
would not change its mind when the target changes. A clock read two slightly different ways would,
and does.

### The decisive test: an ordinary, non-astrological fact

Predicting the number of children on the 38,290 couples whose marriage length is known:

| | held-out R² | what it adds |
|---|---|---|
| era + age gap | 0.12787 | |
| era + age gap + **how long they were married** | 0.18296 | **+0.05509** |
| … + gendered (sin), all 10 bodies | 0.18401 | +0.00106 |
| … + genderless (cos), all 10 bodies | 0.18326 | +0.00031 |
| … + both harmonics, all 10 bodies | 0.18372 | +0.00076 |
| … + gendered (sin), no outer planets | 0.18355 | +0.00059 |
| … + genderless (cos), no outer planets | 0.18324 | +0.00028 |
| … + both harmonics, no outer planets | 0.18354 | +0.00058 |

**Knowing how long a couple stayed married is worth fifty times more than the entire sky.** All ten
planets, both harmonics, twenty fitted parameters, add at most 0.001.

### What the "signal" actually is

It is not zero, and the permutation null says so: shuffling fathers against mothers and re-running
the whole pipeline 200 times gives a null median of about −0.0001 against a real 0.0184, p = 0.005.
The effect is real. It is a clock.

Correlation of each feature with the couple's **age gap in years** (`node research/mechanism.mjs`):

| body | sin(Δ) vs age gap | cos(Δ) vs age gap | sin(Δ) vs children | sin(Δ) vs years married |
|---|---|---|---|---|
| Sun | −0.001 | −0.004 | −0.001 | 0.004 |
| Moon | 0.003 | 0.004 | −0.001 | 0.001 |
| Mercury | −0.001 | −0.004 | −0.000 | 0.005 |
| Venus | 0.003 | 0.001 | 0.004 | 0.008 |
| Mars | −0.001 | 0.010 | −0.013 | −0.006 |
| Jupiter | −0.050 | 0.090 | −0.017 | −0.038 |
| Saturn | 0.079 | **0.522** | −0.092 | −0.099 |
| Uranus | **0.857** | 0.785 | −0.041 | 0.079 |
| Neptune | **0.963** | 0.758 | −0.018 | 0.111 |
| Pluto | **0.946** | 0.612 | 0.013 | 0.158 |

Neptune's angle difference correlates with the age gap at **0.963**. It is not a compatibility
feature; it is a measurement of how many years apart two people were born, expressed in degrees. Drop
the three outer planets and the fitted astrological amplitude collapses from 1.65 to 0.13.

And the fitted weights say it outright. On **both** targets, nearly the whole astrological amplitude
sits in the two slowest bodies — the two best clocks — and collapses when they are removed:

| target | bodies | amplitude | the two largest weights |
|---|---|---|---|
| children | all 10 | 1.669 | Pluto **+1.489**, Neptune **−0.738** |
| children | no outer planets | **0.133** | Saturn −0.129, Sun −0.016 |
| years married | all 10 | 5.144 | Pluto **+4.784**, Neptune **−1.861** |
| years married | no outer planets | **0.286** | Jupiter −0.084, Saturn −0.272 |

Removing three of ten bodies removes 92% of the fitted signal on children and 94% on marriage length.
No model of two people behaves that way; a calendar does.

For scale, the same table's honest rows:

| | r |
|---|---|
| age gap vs children | −0.008 |
| age gap vs years married | 0.124 |
| **years married vs children** | **0.279** |

## The targets, as distributed

The shape is the result's context.

**Number of children** (n = 77,911), mean 1.012, sd 1.697, max 18:

| children | couples | share | cumulative |
|---|---|---|---|
| 0 | 44,336 | 56.91% | 56.9% |
| 1 | 14,899 | 19.12% | 76.0% |
| 2 | 7,868 | 10.10% | 86.1% |
| 3 | 4,584 | 5.88% | 92.0% |
| 4 | 2,676 | 3.43% | 95.4% |
| 5 | 1,360 | 1.75% | 97.2% |
| 6–9 | 1,807 | 2.32% | 99.5% |
| 10+ | 381 | 0.49% | 100.0% |

**Fifty-seven per cent have no recorded child, and that is not fifty-seven per cent childless** — it
is Wikidata having no item for the child. The verifier measures the gap: co-parentage recovers about
30% of the stated counts. This target is mostly a zero produced by missing data, and no model can
predict past that.

**Years of marriage** (n = 38,218), mean 28.6, median 28.0, sd 18.2, range 0–79.8 — a far healthier
target, spread almost evenly across its range:

| years | share | | years | share |
|---|---|---|---|---|
| 0–5 | 11.1% | | 30–40 | 16.0% |
| 5–10 | 10.6% | | 40–50 | 16.7% |
| 10–20 | 16.1% | | 50–60 | 10.7% |
| 20–30 | 15.0% | | 60+ | 3.8% |

### Impossible durations, removed

Wikidata's marriage records are much dirtier than its birth records, and the damage lands on this
target. Found in the collected set: a **1,535-year marriage** (start date typed as year 0180 for a
couple born in the 1640s), marriages beginning **before a partner was born** (one starts in 1848 for a
husband born in 1884), 134 running over 70 years and 13 over 80. A duration is used only if the
marriage starts after both births, both partners were at least 12, and it ran under 80 years. That
drops 72 couples.

What cannot be fixed, and is stated instead: **32.9% of marriage start dates fall on 1 January**, 120×
that day's share of the calendar, and 5.7% of death dates do too, 20.7× theirs. P580 and P570 carry no
precision filter here, unlike the births. The year is still right, so a duration measured in decades
carries about a year of noise — enough to weaken a real effect, never enough to manufacture one.

## Two or more children: a logistic regression

`node research/logistic.mjs` — the same features, the same split, but a classifier:

```
P(children ≥ 2) = σ( b + Σ wᵢ · sin( θᵢ(father) − θᵢ(mother) ) )
```

fitted by IRLS. 24.0% of couples clear the bar, so **"always say no" scores 76% and knows nothing** —
which is why AUC and McFadden's pseudo-R² are the numbers to read, not accuracy.

| model | AUC | pseudo-R² | Brier | accuracy |
|---|---|---|---|---|
| **gendered (sin)**, all 10 bodies | **0.5862** | 0.01679 | 0.1827 | 75.3% |
| genderless (cos), all 10 bodies | 0.5622 | 0.01044 | 0.1839 | 75.3% |
| both harmonics, all 10 bodies | 0.5900 | 0.02065 | 0.1820 | 75.3% |
| **gendered (sin)**, no outer planets | **0.5608** | 0.00842 | 0.1842 | 75.3% |
| genderless (cos), no outer planets | 0.5059 | −0.00007 | 0.1859 | 75.3% |
| both harmonics, no outer planets | 0.5588 | 0.00821 | 0.1843 | 75.3% |
| **era & age gap alone, no astrology** | **0.6520** | **0.05398** | **0.1750** | 75.3% |

Adding astrology on top of era and age gap moves AUC from 0.6520 to between 0.6527 and 0.6540 —
**+0.002 at best**.

Three things worth naming:

- **Every model scores 75.3% accuracy — identical to the trivial classifier.** Not one of them ever
  crosses 0.5 for anybody. At the threshold that matters, the sky never changes a single call.
- **Genderless without the outer planets is the one variant that fails its own null**: AUC 0.5059
  against a null median of 0.4998, p = 0.119. Strip the clock from the symmetric model and there is
  nothing left at all. Every other variant passes at p = 0.005 — as a clock.
- **The odds ratios say it outright.** For the sin model on all ten bodies: **Pluto 79.2** and
  Neptune 0.122, with every other body between 0.74 and 1.10. Remove the three outer planets and the
  whole table sits between 0.70 and 1.05 — nothing there moves anybody's odds by more than a third.

### The classification report — sin model, by where the bar is set

`node research/logistic.mjs` at `THRESHOLD=1`, `2`, `3`. Train 62,256, test 15,655, 80/20 split by
person. A report like this lives or dies on the threshold, so both are shown, and the F1-optimal one
is chosen **on train** and applied unchanged to test — choosing it on test would be tuning on the
answer.

#### P(children ≥ 1) — base rate 43.7% on test

The only balanced cut, and the only one where the model ever crosses 0.50 for anybody.

| class | train precision | recall | f1 | support | test precision | recall | f1 | support |
|---|---|---|---|---|---|---|---|---|
| 0 (under 1) | 0.582 | 0.875 | 0.699 | 35,521 | 0.577 | 0.880 | 0.697 | 8,815 |
| 1 (1 or more) | 0.501 | 0.166 | 0.250 | 26,735 | **0.521** | 0.168 | 0.254 | 6,840 |
| accuracy | | | 0.571 | | | | **0.569** | |

Test confusion: tp 1,147, fp 1,055, fn 5,693, tn 7,760. Precision 0.521 against a 0.437 base rate is a
**19% lift**, and accuracy 0.569 against the trivial 0.563 is a gain of **0.6 percentage points**. It
finds 17% of the couples who had a child, and is right slightly more often than a coin when it does.

At the F1-optimal threshold (0.285) it collapses the other way — predicting "yes" for 15,193 of 15,655
to reach recall 0.987, precision 0.444 which is the base rate, and accuracy 0.455, well below saying
nothing. Both ends of the threshold range are degenerate; there is no setting where this model is
useful.

With the outer planets removed the balanced cut goes too: tp 9 and fp 4 on the whole test set, class-1
recall 0.001.

#### P(children ≥ 2) — base rate 24.7%, and P(children ≥ 3) — base rate 14.6%

At 0.50 both are **constant classifiers**. Positive-class precision, recall and f1 are all 0.000 on
train and test alike, and accuracy equals the base rate to three decimals:

| | test confusion at 0.50 | accuracy | trivial |
|---|---|---|---|
| 2+ | tp 0, fp 3, fn 3,862, tn 11,790 | 0.753 | 0.753 |
| 3+ | tp 0, fp 2, fn 2,281, tn 13,372 | 0.854 | 0.854 |

With the outer planets removed, neither makes a single positive call: tp 0, fp 0.

Forced to make calls at their F1-optimal thresholds:

| cut | threshold | test precision | recall | f1 | base rate | lift | wrong per right |
|---|---|---|---|---|---|---|---|
| 2+ | 0.215 | 0.281 | 0.775 | 0.412 | 0.247 | +14% | 2.6 |
| 3+ | 0.135 | 0.176 | 0.669 | 0.279 | 0.146 | +21% | 4.7 |

The lift *rises* as the class gets rarer — proportional lift is easy on a rare class — while the
absolute precision falls and the false positives multiply. To catch two thirds of the large families
it must flag 55% of everybody.

#### The whole picture

| | 1+ | 2+ | 3+ |
|---|---|---|---|
| test base rate | 0.437 | 0.247 | 0.146 |
| **AUC** | **0.5826** | **0.5862** | **0.5866** |
| AUC, outer planets removed | 0.5557 | 0.5608 | 0.5627 |
| accuracy at 0.50 | 0.569 | 0.753 | 0.854 |
| the trivial classifier | 0.563 | 0.753 | 0.854 |
| positive-class f1 at 0.50 | 0.254 | **0.000** | **0.000** |

**AUC is flat at about 0.586 wherever the bar is set.** Moving it does not reveal a family-size
signal hiding at one particular count; it only changes how imbalanced the problem is, and with it
whether the model can ever cross 0.50. Take the three outer planets away and it drops to ~0.556 at
every cut.

**And none of it is overfitting.** Train against test AUC: 0.5796/0.5826 at 1+, 0.5789/0.5862 at 2+,
0.5813/0.5866 at 3+. Every gap is *negative* — the model does slightly better on couples it has never
seen. Eleven parameters on 62,256 couples have extracted everything available, and this is all of it.

One caveat that belongs with these numbers rather than under them: **the 1+ cut is the one most
damaged by the missing-child problem**. 57% of these couples have no recorded child and the verifier
shows co-parentage recovers only about 30% of Wikidata's own stated counts, so "had at least one
child" is substantially "has a well-documented family" — which tracks notability and era, not
fertility.

## A different question: divorce or death?

`TARGET=divorce node research/logistic.mjs` — did this marriage end in **divorce** rather than in a
death? This uses P1534, the qualifier where Wikidata states *why* a marriage ended, and it is the only
honest source for it: an end **date** is not evidence of divorce, because most recorded end dates mark
a death. Annulment, separation and repudiation are dropped rather than folded into either class.

5,768 couples survive with both births known to the day and an explicit cause, **45.1% of them
divorces** — the most balanced target in the study, and the one least damaged by missing data, since a
stated cause is a positive assertion rather than an absence.

| model | AUC | pseudo-R² | Brier | accuracy |
|---|---|---|---|---|
| gendered (sin), all 10 bodies | 0.6150 | 0.03429 | 0.2373 | 58.8% |
| genderless (cos), all 10 bodies | 0.6253 | 0.03242 | 0.2378 | 59.1% |
| **gendered (sin), no outer planets** | **0.4970** | **−0.00131** | 0.2493 | 53.7% |
| **genderless (cos), no outer planets** | **0.5143** | **−0.00040** | 0.2490 | 53.5% |
| **both harmonics, no outer planets** | **0.5092** | **−0.00146** | 0.2494 | 53.7% |

**This is the cleanest result in the study.** With the outer planets, AUC reaches 0.615 — the highest
any astrological model achieves anywhere here. Take the three of them away and it is **0.497: worse
than a coin**, with a negative pseudo-R², and — for the first time — **all three inner-planet variants
fail their own permutation null**:

| model | AUC | null median | p |
|---|---|---|---|
| sin, all 10 bodies | 0.6150 | 0.5031 | 0.005 |
| cos, all 10 bodies | 0.6253 | 0.4990 | 0.005 |
| **sin, no outer planets** | 0.4970 | 0.5025 | **0.612** |
| **cos, no outer planets** | 0.5143 | 0.5042 | **0.229** |
| **both, no outer planets** | 0.5092 | 0.5003 | **0.284** |

Everything the model knows about divorce is Neptune, Uranus and Pluto, and what those three know is
what year it is. The fitted odds ratios say so without ambiguity — **Neptune 157.5 and Pluto 0.004**,
two enormous collinear coefficients cancelling each other to fit a clock, with every other body
between 0.81 and 1.12. Remove them and the whole table sits between 0.82 and 1.13.

### The classification report

sin model, all 10 bodies, at the default threshold:

| class | train precision | recall | f1 | support | test precision | recall | f1 | support |
|---|---|---|---|---|---|---|---|---|
| 0 (ended by death) | 0.600 | 0.784 | 0.679 | 2,587 | 0.588 | 0.780 | 0.670 | 581 |
| 1 (divorced) | 0.571 | 0.355 | 0.438 | 2,099 | **0.588** | 0.365 | 0.451 | 501 |
| accuracy | | | 0.592 | | | | **0.588** | |

Test confusion: tp 183, fp 128, fn 318, tn 453. Precision 0.588 against a base rate of 0.463 is a
**27% lift**, the largest in the study — and every point of it comes from the three bodies that
measure the calendar. Train AUC 0.6142 against test 0.6150; the gap is negative again.

With the outer planets removed, the same model at the same threshold returns **tp 1 and fp 1 in 1,082
couples**.

## Did it last twelve years?

`TARGET=lasted node research/logistic.mjs` (`LASTED_YEARS` moves the bar). 38,216 couples with a valid
duration, **74.9% of them lasting twelve years or longer** — so the trivial classifier here says *yes*
to everybody and scores 74.9%.

| model | AUC | pseudo-R² | Brier | accuracy |
|---|---|---|---|---|
| gendered (sin), all 10 bodies | 0.5935 | 0.02922 | 0.1829 | 75.3% |
| genderless (cos), all 10 bodies | 0.6151 | 0.02411 | 0.1843 | 75.0% |
| both harmonics, all 10 bodies | 0.6060 | 0.03290 | 0.1826 | 75.1% |
| gendered (sin), no outer planets | 0.5388 | 0.00390 | 0.1899 | 74.3% |
| genderless (cos), no outer planets | 0.5204 | 0.00061 | 0.1907 | 74.3% |
| era & age gap alone, no astrology | **0.6869** | **0.10624** | **0.1653** | **77.7%** |

sin model, all 10 bodies, at the default threshold:

| class | train precision | recall | f1 | support | test precision | recall | f1 | support |
|---|---|---|---|---|---|---|---|---|
| 0 (under 12y) | 0.681 | 0.058 | 0.106 | 7,628 | 0.698 | **0.065** | 0.119 | 1,953 |
| 1 (12y or longer) | 0.760 | 0.991 | 0.860 | 22,976 | 0.754 | 0.990 | 0.856 | 5,659 |
| accuracy | | | 0.758 | | | | **0.753** | |

Test confusion: tp 5,604, fp 1,826, fn 55, tn 127. It says yes to 7,430 of 7,612 couples — 97.6% of
them — and **finds 127 of the 1,953 short marriages, a recall of 6.5%**. Accuracy 0.753 against the
trivial 0.743 is a gain of one percentage point. The F1-optimal threshold lands at 0.535 and changes
almost nothing.

**Without the outer planets it is a constant.** Test confusion: **tp 5,659, fp 1,953, fn 0, tn 0** — it
says yes to every single couple, and the F1-optimal threshold of 0.020 produces the identical table.
Class-0 precision, recall and f1 are 0.000 throughout.

And here is the sharpest illustration in the study of why significance is not the same as use: that
constant classifier has **AUC 0.5388 with a permutation p of 0.005**. On 30,604 training couples a
tiny ranking tendency is unmistakably real and completely useless — it never separates anybody. The
odds ratios show where even that comes from: **Pluto 773.3 and Neptune 0.035**, a collinear pair
fitting the calendar, with every other body between 0.82 and 1.08.

## The midpoint (composite) form, and both together

Two further feature families, on P(children ≥ 2):

```
midpoint:  ( b + Σ wⱼ·cos( midpoint( θⱼ(father), θⱼ(mother) ) ) )²
combined:  ( b + Σ wⱼ·cos( midpointⱼ ) + Σ vⱼ·sin( θⱼ(father) − θⱼ(mother) ) )²
```

**The average of two angles is ambiguous modulo 180°**, and writing `(a+b)/2` quietly picks a branch:
add a full turn to `a` and the "average" moves half a turn, flipping the cosine's sign. Two couples
with the same true midpoint would get opposite features depending on which side of 0° their planets
happened to fall. The circular midpoint — `arg(e^{ia} + e^{ib})`, the direction of the vector sum — is
what is computed here.

The midpoint is also a **sum, not a difference**, so it does not describe a relationship at all. It is
symmetric under swapping the two people (inherently genderless, with no sin counterpart to test) and
it depends on where the planets actually *were*. That makes a strong prediction, and it holds:

| body | cos(midpoint) vs the couple's MEAN BIRTH YEAR |
|---|---|
| Pluto | **−0.896** |
| Neptune | −0.522 |
| Uranus | 0.155 |
| Saturn and inward | ≤ 0.036 |

Where the difference features measured the *gap* between two birth years, the midpoint measures the
years themselves. It is a better clock, and it duly scores better.

### Held-out AUC over 20 independent 80/20 splits

Reported as a mean because **one split is not a measurement**: re-running this study after a small
refresh of the collected data moved a held-out AUC from 0.586 to 0.572 on identical modelling. That is
split noise, and at sd ≈ 0.004 only differences above about 0.01 are real.

| model | AUC | sd |
|---|---|---|
| **era & age gap alone, no astrology** | **0.6542** | 0.0036 |
| midpoint cos + difference sin, all 10 bodies | 0.6489 | 0.0035 |
| midpoint cos, all 10 bodies | 0.6350 | 0.0039 |
| both harmonics (difference), all 10 bodies | 0.5847 | 0.0049 |
| difference sin, all 10 bodies | 0.5790 | 0.0051 |
| difference sin, no outer planets | 0.5559 | 0.0041 |
| **midpoint cos + difference sin, no outer planets** | **0.5558** | 0.0040 |
| both harmonics, no outer planets | 0.5554 | 0.0040 |
| difference cos, all 10 bodies | 0.5546 | 0.0051 |
| difference cos, no outer planets | 0.5076 | 0.0044 |
| **midpoint cos, no outer planets** | **0.5035** | 0.0036 |

Three things this settles:

- **The combined form is the best astrological model in the study, and the two families are not
  redundant.** 0.6489 against 0.6350 for the midpoint alone and 0.5790 for the difference alone — a
  real gain, many times the split noise.
- **It still loses to era and age gap.** Two non-astrological numbers, 0.6542, beat twenty fitted
  planetary weights. That is the whole result in one line.
- **Remove the three outer planets and the combined model is 0.5558 — indistinguishable from the
  difference alone at 0.5559**, and the midpoint contributes *nothing*: on its own it drops to 0.5035,
  a coin. Every point the midpoint family adds is the era clock, and nothing else.

### What the combined model does when asked to classify

At the default threshold it is still a constant: test confusion **tp 9, fp 9, fn 3,853, tn 11,740** —
eighteen positive calls in 15,611, half of them wrong, accuracy 0.753 which is the base rate. The
midpoint alone makes **zero** positive calls, and so does the combined model once the outer planets
go. Forced to its F1-optimal threshold of 0.210: test precision 0.301 against a 0.247 base rate, a 22%
lift, with tp 2,914 against fp 6,757 — 2.3 wrong calls for every right one.

It is also the first model here to overfit at all: train AUC 0.6505 against test 0.6464, a gap of
+0.004. Twenty parameters finally find something to memorise, and it is worth four thousandths.

## Every extra body, and every sidereal setting

`node research/extended.mjs`. Balanced target: did the marriage last 28.0 years or longer, 50/50 at
the median, so accuracy reads against a 50% coin.

### The bodies

Kerykeion's point list beyond the ten planets is Mean Node, True Node, Mean Lilith, Chiron, and the
four angles. All four points are added here — mean node and Lilith exactly from Meeus' lunar
arguments, the true node with its five leading periodic terms, Chiron by two-body propagation from
JPL elements (**approximate**: Chiron is a Centaur that Saturn and Uranus push around, so a Keplerian
propagation back to 1800 accumulates real error).

**The four angles are impossible here, at any setting.** An Ascendant or MC needs a birth *time* and a
birth *place*; Wikidata gives dates. This is not a configuration problem — the information does not
exist. The Moon is already the weakest of the ten for the same reason: unknown hour, ±6.6° of
irreducible uncertainty.

### The sidereal setting cannot do what was hoped, and this is provable

An ayanamsa is one offset subtracted from every longitude, so **in a difference feature it cancels
algebraically**. Verified to machine precision: moving the offset by 47.3° changes `sin(Δ)` by ~1e-16
for all ten planets. The only residue is the ayanamsa's own drift between the two birth dates — and
since every named ayanamsa differs in its *constant* and not its *rate* (≈50.29″/yr), that residue is
identical for all of them: 0.14° for a couple born ten years apart.

For midpoint features the offset does move the feature — but `cos(mid − a) = cos(a)·cos(mid) +
sin(a)·sin(mid)`, so the entire family over all offsets is spanned by `{cos(mid), sin(mid)}`. **A model
carrying both components already contains every sidereal setting at once**, and no single offset can
exceed it. Measured, on the best body set:

| | validation accuracy |
|---|---|
| worst sidereal offset | 59.38% |
| **best sidereal offset** | **62.88%** |
| carrying both midpoint components at once | **63.11%** |

The sweep spans 3.5 points and its maximum sits *below* the model that holds all settings
simultaneously. The space of sidereal settings is therefore closed, not merely unsearched.

### The search

588 configurations — 4 body sets × 5 feature forms × the **full circle in 5° steps**, which contains
Lahiri, Fagan-Bradley, Raman, Krishnamurti, De Luce, Yukteshwar, Djwhal Khul, Sassanian,
Galactic-Centre and every other named ayanamsa, plus every offset nobody has proposed.

Split three ways by person — 23,020 train, 7,584 validate, 7,612 test — because a search over enough
configurations will beat any baseline on a fixed held-out set by chance. Everything is fitted on train
and ranked on validation; the single winner is scored **once** on test.

| | validation | test |
|---|---|---|
| **era (22 decade flags) + age gap, no astrology** | **63.50%** | **63.82%** |
| winner: 10 planets + 4 extras, midpoint cos+sin + difference sin | 63.11% | 63.58% |
| the coin | | 50.00% |

**No configuration beat the baseline — not on the test set, and not even on the validation set the
search was maximising.** The winner fell 0.39 points short on validation and 0.24 points short on
test. The four extra bodies were worth +0.19 points over the ten planets alone, inside the ±0.4-point
split noise measured earlier.

The search did not fail to find the right setting. There is no right setting to find: the difference
features are provably invariant to all of them, and the midpoint features are all contained in a model
that was already losing.

## Aspects, properly: a Fourier basis in the angle

`node research/aspects.mjs`. Everything above used the **first** harmonic, and a first harmonic cannot
represent an aspect doctrine at all: `cos(Δ)` gives +0.5 at the sextile and −0.5 at the trine —
opposite signs for two aspects the tradition calls the same thing — and it cannot make 0° and 180°
behave alike. Aspects are divisions of the circle by small whole numbers, so they live in the higher
harmonics:

| | period | what it isolates |
|---|---|---|
| `cos(2Δ)` | 180° | **the square harmonic** — 0° and 180° alike, the squares their opposite |
| `cos(3Δ)` | 120° | trines |
| `cos(4Δ)` | 90° | squares as a four-fold division |
| `cos(6Δ)` | 60° | sextiles |
| `cos(12Δ)` | 30° | the whole-sign grid — every aspect the tradition names |

So the test is not to guess which aspects matter but to fit an arbitrary function of the angle, per
body: `logit = b + Σⱼ Σₙ [aⱼₙ·cos(nΔⱼ) + cⱼₙ·sin(nΔⱼ)]`. **A Fourier series to order 12 contains every
whole-sign aspect, every soft/hard grading, every orb and every weighting scheme anybody has
proposed** — with the weights fitted rather than assumed. Alongside it, the literal encoding: a
Gaussian bump on each Ptolemaic aspect (0, 30, 60, 90, 120, 150, 180) at a settable orb.

Balanced target, 28.0-year cut, 50% coin, train/validate/test split by person.

| model | astro params | fit | validation | **test** |
|---|---|---|---|---|
| **era + age gap, no astrology** | — | 63.01% | 63.50% | **63.82%** |
| Fourier order 1, 10 planets | 20 | 58.38% | 58.58% | 59.80% |
| Fourier order 2, 10 planets | 40 | 59.21% | 59.39% | 59.88% |
| Fourier order 4, 10 planets | 80 | 59.78% | 60.09% | 60.35% |
| Fourier order 12, 10 planets | 240 | 60.30% | 60.55% | **60.85%** |
| Ptolemaic bumps, orb 12°, 10 planets | 70 | 59.81% | 60.57% | 60.17% |
| Ptolemaic bumps, orb 8°, 10 planets | 70 | 59.52% | 60.28% | 60.04% |
| Ptolemaic bumps, orb 4°, 10 planets | 70 | 57.76% | 58.10% | 57.97% |
| `cos(2Δ)` alone, 10 planets | 10 | 58.73% | 59.03% | 59.83% |
| Fourier order 1, no outer planets | 14 | 55.28% | 54.56% | 55.64% |
| Fourier order 4, no outer planets | 56 | 55.33% | 54.81% | 54.95% |
| Fourier order 12, no outer planets | 168 | 55.70% | 53.69% | 54.27% |
| Ptolemaic bumps, orb 12°, no outer planets | 49 | 53.72% | 52.76% | 52.65% |
| **`cos(2Δ)` alone, no outer planets** | 7 | 51.05% | 50.90% | **49.16%** |

The squared link `μ = (b + Σ)²` was run beside the logistic one and lands within 0.4 points
everywhere — order 12 gives 60.50% against 60.85%, `cos(2Δ)` alone 59.64% against 59.83%. **The link
is not what is limiting anything.**

Four things this establishes:

- **Twelve harmonics buy one point over one harmonic.** 240 astrological parameters, 59.80% → 60.85%,
  and the best of them still loses to 22 decade flags by 3 points.
- **Without the outer planets, more aspect capacity makes it WORSE.** Validation falls monotonically
  as the basis grows: 54.56% at order 1, 54.81% at order 4, **53.69% at order 12** on 168 parameters.
  When there is no calendar to read, extra freedom to describe aspects buys overfitting and nothing
  else. That is about as direct as evidence of absence gets.
- **The narrower the orb, the worse it does.** 4° → 57.97%, 8° → 60.04%, 12° → 60.17%. The model
  improves the *less* aspect-like the feature becomes: it wants a broad smooth trend, not a sharp
  angular coincidence. Sharpen the aspect to the orb an astrologer would actually use and accuracy
  drops three points.
- **`cos(2Δ)` on the inner planets — the aspect-stability paper's exact functional form, on real
  outcomes, with no calendar available — scores 49.16%, below a coin.**

## Full sidereal synastry: the whole cross-matrix

`node research/synastry.mjs`. Everything above used only the **diagonal** — Sun-to-Sun, Moon-to-Moon,
ten same-body differences. That is not synastry. Synastry is the whole grid: his Venus to her Mars, his
Saturn to her Moon, `Δⱼₖ = θⱼ(father) − θₖ(mother)` for all j, k. Ten bodies give **100 cross-pairs**,
and the ninety off-diagonal ones are where the tradition puts most of its weight — untested here until
now. Ridge chosen on validation from {0.3, 1, 3, 10, 30, 100}, never on test.

| model | columns | ridge | fit | validation | **test** |
|---|---|---|---|---|---|
| **baseline: era + age gap, no astrology** | 25 | 30 | 63.00% | 63.53% | **63.81%** |
| diagonal only, 10 planets (used everywhere above) | 20 | 0.3 | 58.56% | 58.89% | 59.88% |
| **FULL 10×10 synastry, first harmonic** | 200 | 0.3 | 63.13% | 62.55% | **63.58%** |
| FULL 10×10 synastry, harmonics 1+2 | 400 | 100 | 63.81% | 62.45% | 62.89% |
| FULL 10×10 synastry, `cos(2Δ)` only | 100 | 0.3 | 60.98% | 61.34% | 61.01% |
| FULL 10×10 synastry, Ptolemaic bumps orb 8° | 700 | 100 | 63.52% | 60.71% | 60.92% |
| diagonal only, classical 7 | 14 | 0.3 | 55.28% | 54.56% | 55.64% |
| FULL 7×7 synastry, classical only, first harmonic | 98 | 0.3 | 55.70% | 54.14% | 55.74% |
| FULL 7×7 synastry, classical only, harmonics 1+2 | 196 | 0.3 | 56.45% | 53.74% | 54.14% |
| FULL 7×7 synastry, classical only, bumps orb 8° | 343 | 0.3 | 55.69% | 51.19% | 51.59% |
| **FULL 7×7 synastry, classical only, `cos(2Δ)` only** | 49 | 0.3 | 52.23% | 50.69% | **49.62%** |

**This is the best astrological model in the entire study, and it is effectively a tie with the
baseline**: 63.58% against 63.81%, a 0.22-point gap inside the ±0.4-point split noise. Full synastry
reaches parity with era and age gap — using 200 columns where the baseline uses 25.

But the next two rows say what that parity is made of:

| | diagonal | full grid | the off-diagonal is worth |
|---|---|---|---|
| 10 planets | 59.88% | **63.58%** | **+3.70 points** (20 → 200 columns) |
| classical 7 only | 55.64% | 55.74% | **+0.11 points** (14 → 98 columns) |

**The off-diagonal is worth 3.7 points when the outer planets are in it and 0.1 points when they are
not.** That is decisive about what the ninety cross-pairs contribute. A cross-pair leaks the calendar
*more* than a same-body pair, not less: his Sun against her Pluto sets a day-of-year against a
birth-year, which pins the era down more finely than Pluto against Pluto can. The full grid did not
discover synastry — it built a better clock, and the clock is why it caught up with the baseline.

And the aspect-specific forms get worse as they get more traditional and more numerous:

- harmonics 1+2 on the full grid: 400 columns, **62.89%** — worse than the first harmonic's 200.
- Ptolemaic bumps at orb 8° on the full grid: 700 columns, fit 63.52% but test **60.92%** — the
  largest fit-to-test drop in the study, and the worst test score of any full-grid model.
- On the classical grid, bumps score **51.59%** and `cos(2Δ)` alone scores **49.62% — below a coin**.
  Forty-nine cells of pure sidereal synastry aspect, no calendar available, worse than guessing.

## The verdict

Neither form predicts anything. Gendered beats genderless on one target and loses on the other, which
is what a clock does and what a property of two people does not. Against the honest baseline — era,
age gap, and how long the marriage lasted — the angles between two people's planets are worth at most
0.001 of R², on 77,911 marriages, with the placeholder birth dates removed.

This agrees with the largest test ever run on the question: Voas (2007), about ten million married
couples in the 2001 England and Wales census, found no sign-compatibility effect at all.

## Reproducing it

```bash
node research/collect.mjs ./research/data          # the dataset, every query checked against a COUNT
node research/verify.mjs  ./research/data          # the three cross-checks
echo 'export * from "./src/engine/ephemeris";' | \
  npx esbuild --bundle --format=esm --loader:.ts=ts --sourcefile=e.ts --outfile=/tmp/aq-eph.mjs
EPH=/tmp/aq-eph.mjs node research/model.mjs      ./research/data/dataset.json
EPH=/tmp/aq-eph.mjs node research/mechanism.mjs  ./research/data/dataset.json
```

Everything is seeded. The window 1800–2012 is where the ephemeris is verified against the Swiss
Ephemeris; `YEAR_MIN` and `YEAR_MAX` widen it, at the cost of extrapolating the planetary positions.

---

# Part two: divorce or death

A second study, on a different target and a much cleaner one. `collect-divorce.mjs` builds the largest
balanced divorce dataset obtainable from birth dates, and everything after it asks whether the sky
predicts which way a marriage ended.

## Why Wikidata, after looking elsewhere

FamiLinx (86M Geni.com profiles, Kaplanis et al. 2018) is the obvious candidate for scale and is useless
here: its individual records carry birth and death dates, locations and gender, and **nothing about
marriage events** — the 54-page empirical evaluation of the database mentions marriage once, in passing.
That generalises. Genealogy corpora record births, deaths, marriages and parentage; divorce is the one
life event they almost never capture, because it leaves no descendant. Same for WikiTree and the GEDCOM
collections. IPUMS census microdata has "divorced" as a status but only ages, and no way to pair two
ex-spouses. Administrative divorce certificates carry both parties' dates of birth and would be ideal;
they are not open.

## The dataset

| route to a label | divorce | death |
|---|---|---|
| explicitly stated cause (`P1534`) | 4,586 | 7,161 |
| **remarriage while the partner still lived** | **1,829** | — |
| end date more than a year before both deaths | 1,618 | 17,005 |
| **total labelled** | **8,033** | **24,166** |

32,199 couples from 50,615 statements; balanced to **16,066**. The inference rule was validated against
the stated causes: **92.8% recall, 99.7% specificity, 99.0% precision**. All 126 distinct `P1534` values
are enumerated and accounted for — the first version knew about ten and missed a second annulment item
(`Q759734`), dissolution, breakup, Mexican divorce, separation process and conscious uncoupling.

Two traps `verify-divorce.mjs` caught:

- **A completeness check that compared two different Wikidata snapshots.** The collector tried QLever
  first and fell back to WDQS, so a COUNT could come from one and the data from the other. One query
  returned 64,856 usable rows against a COUNT of 64,855 — one *more* than existed. Every check now pins
  both of its questions to the same server.
- **Balance broken by filtering.** The collector balances, then the placeholder filter removes rows
  unevenly (death-ended marriages are older records with more placeholders), leaving 53.5% positive while
  still labelled 50/50. Balancing now happens last, after every filter.

Placeholder dates matter more here than in part one: **17.4% of birth dates fall on 1 January**, because
any-precision births are admitted and a year-precision date renders that way. Only 1 January is dropped
(other 1st-of-month dates are kept — the excess there is 1.10x against 1.57x).

## The result

Balanced 50/50, 80/20 by person, on **explicitly stated causes only** — no inference:

| model | TRAIN | VAL | **TEST** |
|---|---|---|---|
| dates: 20-year bins + age gap | 69.43% | 65.99% | 70.10% |
| **dates: smooth polynomials in the same three dates** | 69.48% | 65.70% | **71.93%** |
| the wave score `\|z₁+z₂\|²`, 60-year window | 69.88% | 65.26% | 68.69% |
| wave score + dates | 71.86% | 67.30% | 72.78% |

**Astrology adds 0.85 points** over a properly specified model of the same three dates. And the
orthogonalisation is decisive: the dates explain 58.4% of the wave score's variance, and the remainder
alone tests at **47.67% — below chance**.

On the *inference-contaminated* set that remainder gave 60.43%, and the era-preserving null gave
p = 0.066 rather than 0.016. The apparent effect was a labelling artefact: era predicts the label partly
by predicting which labelling route fired. Clean labels, no effect.

## Two corrections worth recording

**A physics bug.** The linear-phasor models used HELIOCENTRIC periods. Mercury's 88 days is its orbit
around the Sun; seen from Earth its longitude advances once a *year*. Measured over 210 years: Mercury
1.000 y (not 0.241), Venus 0.999 y (not 0.615). Two of ten phasors were turning 4x and 1.6x too fast.
`phasor3.mjs` onward uses a day-by-day ephemeris table and is unaffected.

**A well-posedness test that should have come first.** Nobody agrees where the zodiac starts — the named
ayanamsas span about 25 degrees — so a model of two *people* cannot depend on the choice. Only
DIFFERENCE features are exactly invariant:

| feature family | shift +1 deg | +25 deg | +180 deg |
|---|---|---|---|
| differences (cos, sin, orb bumps, cos 2d) | **0 exact** | **0 exact** | **0 exact** |
| midpoints | 0.018 | 0.433 | 2.000 |
| individual placements | 0.016 | 0.393 | 2.000 |
| the phasor **as fitted** (b non-zero) | 0.006 | **0.175** | 0.513 |
| the phasor with b = 0 | 0 exact | 0 exact | 0 exact |

Every model that scored well violated one of these two symmetries. The best-posed model — orb bumps on
the Ptolemaic aspects over the classical 7x7 grid, differences only — scores 51.6% and 48.6%. The most
sensical model is the one that fails hardest, and that is the finding rather than a coincidence.

## The scripts

| file | what it does |
|---|---|
| `collect.mjs` · `verify.mjs` | part one's dataset and its three cross-checks |
| `model.mjs` · `mechanism.mjs` | children and marriage length; what the features actually track |
| `logistic.mjs` · `duration.mjs` | classification at 1+/2+/3+ children, and duration |
| `aspects.mjs` | Fourier bases to order 12 and explicit Ptolemaic orbs |
| `synastry.mjs` | the full 10x10 cross-matrix |
| `paper-model.mjs` | the two-phase stability model of Ashrafnejad (2026), reconstructed and verified |
| `longevity.mjs` · `marriagelife.mjs` | lifespan in long marriages; total life lived inside the marriage |
| `extended.mjs` | every extra Kerykeion body, and the full circle of sidereal offsets |
| `improved.mjs` · `three-dates.mjs` | orthogonalisation, era-free features, the marriage date |
| `collect-divorce.mjs` · `verify-divorce.mjs` | part two's dataset and its five checks |
| `divorce-model.mjs` | divorce or death, every feature family |
| `phasor.mjs` · `phasor2.mjs` · `phasor3.mjs` | one complex number per person, rank-R, day-by-day ephemeris |
| `interference.mjs` · `interference28.mjs` | positive interference integrated after the wedding |
| `rectified.mjs` | `max(b + Σ aⱼcos(midⱼ), 0)²` |
| `transit-wave.mjs` · `zsum.mjs` · `zsum2.mjs` | the transit-to-natal wave, and `\|z₁+z₂\|²` in closed form |
| `zsum-checks.mjs` | the three checks that decide whether any of it survives |

Every script is seeded. `research/data/` and `research/data-divorce/` are gitignored and regenerate from
the two collectors in a couple of minutes.
