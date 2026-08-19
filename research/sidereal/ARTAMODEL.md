# ArtaModel — the study

*Named by Arash, 2026-08-18. Third-edition gendered data (dad/mom from P21; both births to the day, both
birthplaces; the wedding date; sidereal phases from Kerykeion at 09:00 local). 250 fits in
`artamodel_study.py`; every number below is held out on couples born after 1900 unless marked "inner", every
choice made on the inner temporal split, and every experiment on a FIXED population.*

## The model

```
y = | b + Σᵢ  aᵢ ·e^{i(θmᵢ − θdᵢ)}     synastry, mom − dad
             + mᵢ ·e^{i(θtᵢ − θmᵢ)}     the wedding sky transiting mom
             + dᵢ ·e^{i(θtᵢ − θdᵢ)}     the wedding sky transiting dad
             + mnᵢ·e^{i θmᵢ}            mom's own natal phase
             + dnᵢ·e^{i θdᵢ}            dad's own natal phase
             + tnᵢ·e^{i θtᵢ}            the wedding sky's own phase
             + cᵢ ·e^{i θcᵢ}            the composite (shorter-arc midpoint of the two natal longitudes)
             + tcᵢ·e^{i(θtᵢ − θcᵢ)} |²  the wedding sky transiting the composite
```

Fourteen bodies (Sun … Pluto, true node = Rāhu, true south node = Ketu, Chiron, mean Lilith), Ascendant/MC
optional. Every term exists only when both of its phases exist ("if wedding is not known, drop the last two
terms"; "if dob of either is not known, drop the natal term of it") — a missing phase contributes exactly zero.
Complex weights as (Re, Im), |·|², a logistic head for the loss, Adam with L2, early-stopped on the inner
temporal split; F copies of the formula combined by the head, F = 1 being the formula literally.

**Populations.** FULL — both natal charts complete and the wedding day known: 6,258 train / 2,635 held out.
CHARTS — both charts, wedding may be year-only: 9,716 / 7,428. ANY — any row with one phasor: up to 76,081 / 7,428.
**Plain reference on the same rows** (boosted trees on the two ages at the start, the gap and the start year):
FULL 0.6371 · CHARTS 0.6083 · ANY 0.6171. Dad's age at the start alone: 0.6264 on FULL.

## 1 · Which terms (all 63 subsets of the six + the composite rungs, FULL, F = 1)

| terms | phasors | inner | held out |
|---|---|---|---|
| **m + d** (the two wedding-transit terms) — *selected by inner* | 28 | 0.6426 | **0.6304** |
| a + m + d (Arash's first formula) | 42 | 0.6416 | 0.6258 |
| a + d | 28 | 0.6280 | 0.6318 |
| d alone | 14 | 0.6235 | 0.6223 |
| a alone (synastry) | 14 | 0.5965 | 0.5755 |
| mn + dn (the natal phases) | 28 | 0.5507 | 0.5235 |
| tn (the wedding sky alone) | 14 | 0.5201 | 0.4551 |
| c (the composite alone) | 14 | 0.5069 | 0.4563 |
| c + tc | 28 | 0.6149 | 0.5828 |
| a + m + d + mn + dn | 70 | 0.6113 | 0.6098 |
| a + m + d + mn + dn + tn | 84 | 0.6021 | 0.5931 |
| a + m + d + c + tc | 70 | 0.6162 | 0.6104 |
| all eight | 112 | 0.5634 | 0.5740 |

Across the 70 configurations the inner split picks m+d; the best held-out anywhere is 0.6318, so the optimism of
selecting on the test set would have been only +0.0014 here. Every **absolute-phase** term (mn, dn, tn, c) makes
the model worse out of time; every **difference** term (a, m, d, tc) helps or is neutral.

## 2 · Which bodies (3-term a+m+d, FULL)

**One body at a time:** Uranus alone **0.6419** · the three outer 0.6302 · Neptune 0.6260 · Pluto 0.6203 · Chiron
0.6118 · Saturn 0.5913 · the nodes 0.5670 · Jupiter 0.5136 · Moon 0.5026 · Lilith 0.5003 · Mars 0.4938 · Venus
0.4796 · Mercury 0.4784 · **Sun 0.4728**. Sets: modern10 0.6202 · slow5 0.6204 · classical7 0.5889 · fast5 0.4827.

**Dropping one body from all fourteen** changes held-out by −0.0012 (Chiron) to **+0.0062** (either node) — dropping
any *fast* body improves the model, dropping any *slow* body barely moves it (they are redundant with each other).

## 3 · Invariances that prove what it reads

| convention (recomputed through Kerykeion) | 3-term held out | 6-term held out |
|---|---|---|
| Lahiri 09:00 local (baseline) | 0.6258 | 0.5931 |
| Raman · Fagan-Bradley · Krishnamurti | 0.6258 · 0.6258 · 0.6258 | 0.5931 · 0.5931 · 0.5931 |
| **tropical** | 0.6258 | 0.5941 |
| birth hour 06:00 · 12:00 · 18:00 local | 0.6258 · 0.6259 · 0.6259 | 0.5931 |
| 12:00 UT, **place ignored** | 0.6259 | 0.5933 |
| wedding at 00:00 UT | 0.6260 | 0.5934 |

The three-term model is **exactly invariant** to the ayanāṁśa and to the zodiac (a constant offset cancels in a
difference of two phases), and invariant to four decimals to the birth hour and the birthplace (a common shift of
both charts moves a slow body by nothing). It therefore cannot be reading anything sidereal, local, or angular.

## 4 · What it reads

**The two ages at the wedding, and the age gap, through the slow bodies as clocks.** Uranus moves 4.3°/yr and
completes a cycle in 84 years, so `θt − θm` for Uranus is mom's age at the wedding, unwrapped for anyone under
84; Neptune (2.2°/yr) and Pluto (1.5°/yr) the same at lower resolution; `θm − θd` for the same bodies is the age
gap. The fitted anatomy says so directly — the largest weights of the 3-term model are `d_pluto 1.27, m_pluto
1.16, a_pluto 1.11, d_uranus 0.99, a_neptune 0.90, d_neptune 0.90` — and the controls confirm it:

| 3-term, FULL | AUC |
|---|---|
| held out | 0.6269 |
| **held out within 3-year cells of (dad's age, mom's age)** | **0.4955** |
| within 2-year age-gap bands | 0.5635 |
| plain reference (two ages + gap + start year, boosted) | 0.6371 |
| reference + ArtaModel score (combiner fitted on train, out-of-fold) | 0.6361 |

Hold the two ages flat and the model is at chance. Add its score to the plain reference and nothing is gained.
The 6-, 3+composite- and 8-term variants read 0.4765, 0.5080 and 0.5058 age-cell-matched; the reference gains at
most +0.0024 from any of them (noise).

## 5 · The rest

- **Populations** (same formula): a+m+d FULL 0.6258 → CHARTS 0.6047 → ANY 0.6086; the six-term formula FULL
  0.5931 → CHARTS 0.5719 → **ANY 0.4877** — on ANY, ~50,000 rows carrying only a wedding sky (an era clock) join
  the fit and drag the shared weights toward era, which reverses across the 1900 split.
- **Angles** (ASC/MC in the synastry/natal terms): 0.6194 vs 0.6258 without — worse.
- **Harmonics** (phases × h): h=2 0.6284, h=3 0.6203, h=4 0.6069 for a+m+d — a clock survives doubling.
- **Fields × L2** (3-term): held-out 0.616–0.6365 across 28 settings; the inner split picks F=64, L2=0.01
  → 0.6163 (optimism of picking on the test set would be +0.020). Ten seeds at F=1: 0.6252 ± 0.0030.
- **Temporal folds inside the training half** rank the ladder the way the held-out set does here (a+m+d 0.63 on
  the folds vs 0.626 held out; six-term 0.58–0.63 vs 0.593) — unlike the tropical stacks of the first edition.
- **Composite (Davison-style)**: alone at chance (0.4563); with its transit, 0.5828; added to a+m+d, worse (0.6104).

## 6 · Verdict

ArtaModel is a well-behaved, fully specified, honestly fitted model — and every point of held-out AUC it earns is
the two partners' ages at the wedding and the gap between their births, measured by the outer planets as clocks.
That is why it is invariant to the zodiac, the hour and the place; why Uranus alone equals the whole thing; why
the fast bodies are pure noise; and why it vanishes when the ages are held flat. Its ceiling on this data is the
plain reference (0.6371 on FULL), which it does not reach (0.6304 at best, m+d) and does not add to.

What would move it: information that is not a function of the three dates — birth **times** (the angles would
then be real), or a wedding **place** (a real electional lagna). Both are absent from Wikidata for these couples.

## 7 · Ensembles, boosting, and split single-sum models (`artamodel_ensemble.py`)

Arash, 2026-08-18: "use ensembles and boosting techniques and split multiple single sum model". FULL population;
the plain reference on the same rows is 0.6353.

| construction | 3-term | 6-term |
|---|---|---|
| single ArtaModel F=1 | 0.6251 | 0.5820 |
| BAG, 25 bootstraps rank-averaged | 0.6339 | 0.6031 |
| BOOST, single-sum fields on residuals | 0.6318 | 0.5933–0.5969 |
| SPLIT per body (14 single sums), linear head | 0.6339 | 0.6251 |
| SPLIT per term / per phasor, linear head | 0.6291 / 0.6297 | 0.6195 / 0.6070 |
| SPLIT → LightGBM on the intensities | 0.6220–0.6293 | 0.6097–0.6269 |
| **BOOST over SPLIT, per phasor** | **0.6373** | **0.6388** |

Splitting rescues the six-term formula (each absolute-phase term in its own sum can be weighted down); boosting
over the split sums reaches the reference but does not cross it; the age-cell-matched control stays at 0.50–0.52
for every construction — better instruments for the same two quantities. Inner-selected picks: 3-term BOOST
0.6318, 6-term BOOST-over-SPLIT-per-body 0.6293 (the top held-out numbers carry about +0.007 of optimism).

## 8 · Midpoints, per-body models, sums, aspect grids — every model on every row it has (`artamodel_split_models.py`, `artamodel_full_stack.py`, `artamodel_blend.py`)

Arash, 2026-08-19: three midpoint terms (the natal composite **c** = mid(θm, θd), **mw** = mid(θm, θt), **dw** =
mid(θd, θt) → `TERMS9`); every model trained on the rows it has (the dad-natal model on almost everything, a
day-missing row on the outer planets only — the precision-aware phases do this by themselves); per-body models
|b + aᵢ e^{i(θmᵢ−θdᵢ)}|² **in addition to** the sum models; and the aspects. Marriages-only edition III:
89,465 train rows, 7,249 test rows, most dates year-only. Every member is a coherent field with a logistic head,
early-stopped on the inner temporal split of its **own** population; train scores are out-of-fold over two
temporal halves; test scores from a fit on all its rows; the stacker is LightGBM over the member scores (NaN where
a member has nothing for the couple).

**Members (144).** 126 per-phasor models (9 terms × 14 bodies, each on its own rows); 9 per-term sums over the
14 bodies — inside the square the cross terms cos(φᵢ−φⱼ) ARE the aspects between that term's phasors; the
3-/6-/9-term whole-formula sums; three explicit inter-body aspect grids (synastry θmᵢ−θdⱼ, wedding→mom θtᵢ−θmⱼ,
wedding→dad θtᵢ−θdⱼ, all i≠j, 182 phasors each); and three boosted split sums — the deployed construction on
the 9,553 full-chart rows, and the 6- and 9-term constructions on all 75,852 rows with any phasor.

| member (held out, on the rows it scores) | rows | AUC |
|---|---|---|
| phasor **d_neptune** (wedding→dad) | 16,622 | **0.6312** |
| phasor d_pluto / d_uranus / a_uranus | 16,622 / 16,622 / 11,255 | 0.6231 / 0.6177 / 0.6031 |
| SUM term d over 14 bodies | 16,622 | 0.6267 |
| SUM 3-term (a+m+d) over all bodies | 22,426 | 0.6097 |
| SUM term a / m | 11,255 / 8,787 | 0.5825 / 0.5924 |
| SUM term c / mw / dw (the three midpoints) | 11,255 / 8,787 / 16,622 | 0.4763 / 0.4545 / 0.3938 |
| SUM term mn / dn / tn (absolute phases) | 13,669 / 24,332 / 67,396 | 0.4851 / 0.5154 / 0.4713 |
| SUM 6-term / 9-term over all bodies | 75,852 | 0.4821 / 0.5345 |
| ASPECTS synastry / wedding→mom / wedding→dad grids | 11,255 / 8,787 / 16,622 | 0.5205 / 0.5044 / 0.5200 |
| BOOST6 on full-chart rows (deployed construction) | 9,553 | 0.6235 |
| BOOST6 / BOOST9 on every any-phasor row | 75,852 | 0.5665 / 0.5656 |

| stack / blend (all 7,249 test rows) | held | age-cell-matched | board |
|---|---|---|---|
| REFERENCE plain columns alone | 0.5971 | 0.5078 | 0.61055 |
| STACK 126 per-phasor only | 0.5880 | 0.5119 | |
| STACK 12 sum models only / 3 aspect grids only | 0.5521 / 0.5195 | 0.4759 / 0.5257 | |
| STACK all 144 members, no plain | 0.5812 | 0.5010 | |
| STACK all 144 + plain (regularised / loose / tight) | 0.6059 / 0.6018 / 0.6100 | 0.5112 / 0.4977 / 0.5205 | **0.61149** (selector-picked: loose) |
| RANK-BLEND top-3 members by train OOF (d_uranus, 3-term sum, a_uranus) | 0.6183 | 0.5558 | |
| deployed 6-term boosted (train-only fit) | 0.6235 | 0.5701 | 0.63 |
| 0.7·deployed + 0.3·stack | 0.6263 | 0.5592 | |

**What it says.** (1) The new midpoint terms are below chance as sums (0.39–0.48) and add nothing in the stack:
a midpoint of two slow clocks is a third clock with the information of neither. (2) The per-body models confirm the
anatomy to the body: the strongest single model on the whole dataset is **Neptune at the wedding relative to
Neptune at the groom's birth** — Neptune moves 2.2°/yr, so that phase IS the groom's age at the wedding, and
Pluto/Uranus are the next-best clocks. (3) The explicit aspect grids (182 inter-body separations each) are
0.50–0.52: the classical synastry and transit aspects carry nothing once each body's own clock is a separate
term. (4) Fitting on every available row HURTS the boosted sum (0.5665 on 75,852 rows vs 0.6235 on 9,553 full
charts): the year-only rows hand the field only the outer planets, and the stage picker then spends its stages
on the clocks that least separate within a year. (5) **The train-OOF of every clock-reading member is below
chance across temporal halves (BOOST6 0.47–0.53, held 0.62)** — a clock fitted on one era is anti-predictive on
the next, and it scores on the leaderboard only because test shares train's eras. (6) Nothing here beats the
deployed 6-term boosted split (0.631 on the board): the 144-member stack lands at 0.61149 beside the plain columns
(0.61055), and every age-cell-matched read stays at 0.50–0.57. The deployed model and its explanation stand.
