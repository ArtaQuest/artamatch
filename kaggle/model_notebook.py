#%% [markdown]
# # The best astrology so far — and the three integers that beat it
#
# > *Let's end this loneliness epidemic with astrology.*
#
# This notebook explains the ArtaQuest Foundation's entry in
# [**ArtaMatch Astrology**](https://www.kaggle.com/competitions/artamatch-astrology) — what it computes, what it
# scores, and where it is weak. It ends with a small model you can run in two minutes and beat.
#
# The task: from a man's date of birth and a woman's, and **nothing else**, predict whether a child exists who
# names both of them as parents.
#
# | held-out, the competition's own metric | AUC |
# |---|---|
# | Random / the sample submission | 0.500 |
# | Logistic on the signed difference of the two dates | 0.512 |
# | The Foundation's 18-tradition, 54-model astrology stack | 0.624 |
# | Two birth **years** and their mean, fed to a gradient booster | **0.635** |
# | The same, plus day-of-year and lunar-phase cycles — 17 features total | **0.641** |
#
# ## Read that table again
#
# **Three integers beat the astrology stack.** Seventeen features beat it by 0.016. The stack computes about
# 57,000 columns from eighteen traditions through a Swiss Ephemeris, and it is worse on this task than the two
# birth years alone.
#
# The Foundation is publishing that because it is the result. Section 3 explains why it happens, and it is the
# thing this competition is really about: the era is doing the work, and the open question is whether *anything*
# beats it.
#
# **So the number to beat is 0.641, not 0.624.** Anyone who reports 0.63 as "beating the astrology stack" has
# beaten a worse model than three integers.

#%% [markdown]
# ## 1. The shape of the thing
#
# 18 traditions → 268 candidate feature blocks → 54 base models → one meta model.
#
# **Every feature is computed from the two dates alone**, at a fixed 08:00 UT, through a Swiss Ephemeris. There
# is no birthplace, so no ascendant, no houses and no astrocartography; there is no marriage date, so no
# electional astrology, no Vedic vivāha muhūrta and no wedding transits. Those five traditions are absent by
# necessity rather than by choice.
#
# Each tradition module turns the two charts into up to three blocks of numbers — about **57,000 columns** in
# total. A block is scored on its own with a cheap model first; the survivors are refit properly; and a logistic
# regression over the out-of-fold predictions of the 54 survivors produces the final probability.
#
# ### Why stack instead of one big model
#
# 57,000 columns on 107,738 rows is a shape that invites a single boosted model to find whatever happens to
# separate the training set. Fitting one small model per block and combining their **out-of-fold** predictions
# keeps each tradition's contribution measurable and keeps the meta model's input at 54 columns instead of
# 57,000. It also means every tradition's score can be reported honestly, including the ones that fail.
#
# ### The per-tradition scores, each tradition's best single block
#
# | tradition | AUC alone | | tradition | AUC alone |
# |---|---|---|---|---|
# | harmonics | 0.6448 | | tibetan_seasia | 0.6243 |
# | indigenous_americas | 0.6439 | | vedic_core | 0.6143 |
# | lunar_calendrical | 0.6438 | | vedic_ashtakavarga | 0.5972 |
# | african | 0.6436 | | hellenistic | 0.5772 |
# | uranian | 0.6427 | | chinese | 0.5739 |
# | babylonian_egyptian | 0.6425 | | persian_arabic | 0.5738 |
# | mesoamerican | 0.6418 | | polynesian | 0.5698 |
# | modern_western | 0.6417 | | east_asian_deep | 0.5616 |
# | aboriginal_australian | 0.6402 | | vedic_match | 0.5557 |
#
# **Read the top of that table sceptically.** The nine traditions clustered at 0.64 all encode a *long-baseline
# calendar* — heliacal risings, the Saros and Metonic cycles, the Egyptian civil year, Long Count intervals, the
# slow Uranian dials. What those have in common is that they locate a date in a long cycle, which is very nearly
# a way of saying *which era this is*. The traditions built from purely short cyclic quantities sit far lower.
#
# That is the same 0.64 the two birth years reach on their own, and the coincidence is not one. A long-baseline
# calendar quantity IS an era feature wearing astronomy. Section 3 is about what follows from that.
#
# The bottom of the table is worth as much as the top. `vedic_match` — the aṣṭakūṭa system built specifically to
# judge whether two people should marry — scores **0.5557**, below nine traditions that were never designed for
# the question. `polynesian`'s maramataka night classes score exactly **0.5000**. Those are measurements, not
# omissions.

#%% [markdown]
# ## 2. What is actually computed, tradition by tradition
#
# A representative sample rather than all 268 blocks:
#
# - **harmonics** — not a culture but the raw geometry of the two charts: contacts in ecliptic latitude,
#   parallels of declination, out-of-bounds bodies, and each planet's speed (stationary, applying, separating).
# - **lunar_calendrical** — the Saros and Inex eclipse cycles, the Metonic and Callippic calendar cycles, the
#   computus that fixes Easter, and the synodic phase of all 45 body pairs at each birth.
# - **uranian** — the Hamburg School's eight hypothetical bodies (Cupido, Hades, Zeus, Kronos, Apollon,
#   Admetos, Vulkanus, Poseidon) on the 360°, 90°, 45° and 22.5° dials, with the cross-chart distances between
#   them and the specific "planetary pictures" that school reads for marriage and children.
# - **mesoamerican** — Long Count components, the katun wheel, distance numbers, and the 365-day Haab with the
#   Calendar Round and its year bearer, all on the GMT correlation (JDN 584283).
# - **vedic_core** — the 27 nakṣatras and 108 padas as circular quantities, divisional charts D1/D2/D3/D12/D30/
#   D60, graha states with avasthā, the full panchanga and the Vimśottarī daśā.
# - **chinese** — stem-and-branch in the sixty-year cycle with the year boundary at **Lichun**, not 1 January;
#   the five-phase generating and overcoming relations; the 28 xiù measured from Spica; Nine Star Ki; Ming Gua.
# - **modern_western** — the Davison relationship chart (one chart for the midpoint *in time*) set against the
#   composite of midpoints, including where the two methods disagree.
#
# Everything is emitted as sine/cosine pairs where it is cyclic, so no quantity has an artificial seam at 0°,
# and as one-hot where the tradition names discrete classes.

#%% [markdown]
# ## 3. The one thing that will decide this competition
#
# **Most of what looks like signal in two birth dates is *when* the people were born, not who they were.**
#
# On an earlier version of this data spanning 1800–2026, recorded parenthood ran at about **58% for couples born
# in the 1800s and 2% for the 1990s** — because a couple born in 1990 may not have finished having children, and
# any child they do have has not had time to become notable enough for a public database to record. A single
# non-astrological feature block of birth cohort plus exposure reached **AUC 0.7004** on that data, which was
# *higher* than the best astrological block.
#
# This dataset restricts the parents to **1800–1950** to remove that cliff, and it works: the residual gradient
# across decades falls to **0.385** from roughly 0.56. But 0.385 is not zero. It runs 0.738 for couples born in
# the 1800s down to about 0.40 from 1900 onwards.
#
# So a feature that says "this couple is early-19th-century" still carries real predictive weight, and any
# long-cycle calendar quantity is partly such a feature. That is the most likely explanation for why nine
# unrelated traditions all land at 0.64 while the short-cycle ones sit near chance.
#
# **This is now measured, not suspected.** In section 5, on the training half, out-of-fold:
#
# | | AUC |
# |---|---|
# | era only — two birth years and their mean | **0.6488** |
# | cycles only — day-of-year and lunar phase, no years at all | 0.5971 |
# | both | 0.6567 |
# | *the 54-model astrology stack, same data, same protocol* | *0.6460* |
#
# Two integers and their mean beat eighteen traditions. And the cycles-only row is the interesting one: at
# 0.5971 it is well above chance with **no era information whatsoever**, so something genuinely cyclic is
# present. It is just much smaller than the era effect, and the astrology stack spends most of its capacity
# rediscovering the era instead.
#
# **What this means for you:** 0.64 is nearly free. The real prize is the cycles-only column — a model that
# scores well *within* a single birth decade, where the era cannot help. Nobody has published one on this data.
# The Foundation would rather publish that result than win its own competition.

#%% [markdown]
# ## 4. Where the model is weak, stated plainly
#
# - **No birth time.** Every chart is cast for 08:00 UT. The Moon moves about 0.5° an hour, so a Moon-based
#   quantity carries up to ±6° of error, and anything needing an ascendant is simply absent.
# - **The label is a record, not a life.** It says whether Wikidata's record of the marriage spans thirty
#   years, which is a fact about what was written down. A marriage whose ending was never recorded is dated
#   from the earlier spouse's death instead, and one ended by a death is NOT counted as long automatically.
# - **Most training rows are incomplete, on purpose.** Unknown parts are written `00` — `1850-00-00` is a
#   year, `1850-03-00` a month — and `0000-00-00` means that partner is absent from the source entirely. The
#   duration of a marriage is known just as exactly when one spouse's birthday is not, so those rows carry a
#   real label and half an input. The test set has none of it: every scored row is complete and day-precision.
# - **1 January is a placeholder, and it is excluded.** Among day-precision births 1600–1900, 1 January occurs
#   **2.07×** as often as a median January day, where 2 January sits at 1.00× — a source that knew only the year
#   was imported with a day anyway. Those records are dropped at day precision, which also costs the genuine
#   1 January birthdays. They are NOT dropped at year precision, where `1850-01-01` is simply how the source
#   spells "1850".
# - **The same placeholder moves in the Julian calendar.** Every date here is proleptic Gregorian, whatever
#   calendar the source recorded — so a *Julian* 1 January is stored as 11, 12 or 13 January depending on the
#   century, and the excess is measurably there: **2.08×** the median January day at 13 January among
#   Julian-dated records. Those are excluded at the century-correct date.
# - **The stack is not reproducible from this notebook.** It needs the ephemeris asset and 18 modules, which live
#   in the project repository. What is reproducible is every number quoted here, because the model, the dataset
#   and the build notebook are all public.

#%% [markdown]
# ## 5. A model you can run and beat
#
# Everything below runs on the competition data with nothing but pandas and scikit-learn. It is deliberately
# simple — no ephemeris, no astrology — so that it is a floor rather than a ceiling.

#%%
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

BASE = "/kaggle/input/artamatch-astrology"
try:
    train = pd.read_csv(f"{BASE}/train.csv")
except FileNotFoundError:                       # running outside Kaggle
    train = pd.read_csv("train.csv")
# The target column is DISCOVERED, not spelled out, so this notebook keeps working when the question changes.
LABEL = [c for c in train.columns if c not in ("id", "dob_older", "dob_younger")][0]
ABSENT = "0000-00-00"
n_absent = int((train.dob_older.eq(ABSENT) | train.dob_younger.eq(ABSENT)).sum())
n_coarse = int((train.dob_older.str.contains("-00") | train.dob_younger.str.contains("-00")).sum()) - n_absent
print(f"{len(train):,} training couples, {train[LABEL].mean():.2%} positive  (target: {LABEL})")
print(f"  {n_absent:,} have one partner absent from the source, written {ABSENT}")
print(f"  {n_coarse:,} more have a date known only to the month or the year")
print(f"  the SCORED rows are all complete and day-precision, so you never predict from a placeholder")
train.head()


#%% [markdown]
# ### The reference every entry should beat
#
# A two-parameter logistic on the signed difference between the two dates. This is the number quoted on the
# Evaluation tab, and it is the honest floor: anything that cannot beat it has not learned anything about
# astrology, only about arithmetic.

#%%
def as_day(s):
    """Days since 1800. `00` components become 01, so month and year precision survive as coarse values, and an
    ABSENT partner (`0000-00-00`) becomes NaN rather than a date in year zero.

    That distinction is the one to get right. Year 0 is not a date, and letting it through produces a birth
    -657,000 days before 1800 that silently drags every fitted coefficient. NaN is the honest value, and it is
    also the one scikit-learn refuses loudly instead of quietly modelling.
    """
    y = s.str.slice(0, 4).astype(int)
    m = s.str.slice(5, 7).astype(int).clip(lower=1)
    d = s.str.slice(8, 10).astype(int).clip(lower=1)
    out = (pd.to_datetime(dict(year=y.clip(lower=1), month=m, day=d), errors="coerce")
           - pd.Timestamp("1800-01-01")).dt.days
    return out.where(y > 0)


dm, dw = as_day(train.dob_older), as_day(train.dob_younger)
# The signed-gap baseline needs BOTH dates, so it is fitted on the couples that have both. That is a property of
# this particular baseline and not of the dataset: a real entry can use the one-sided rows, and there are a lot
# of them. Reported rather than dropped in silence.
both = dm.notna() & dw.notna()
print(f"the signed-gap baseline uses the {int(both.sum()):,} couples with both dates "
      f"({100*both.mean():.1f}% of the file); the other {int((~both).sum()):,} have one partner absent")
y = train.loc[both, LABEL].to_numpy()
gap = ((dw - dm)[both]).to_numpy().reshape(-1, 1) / 365.2425

ref = LogisticRegression(max_iter=2000).fit(gap, y)
print(f"signed-gap logistic, in-sample AUC: {roc_auc_score(y, ref.predict_proba(gap)[:, 1]):.4f}")


#%% [markdown]
# ### A small feature set, honestly labelled
#
# Two groups, kept separate so their contributions can be read apart:
#
# - **era** — the two birth years and their mean. This is the exposure effect from section 3, in its plainest
#   form. It is included because pretending it is not there does not make it go away.
# - **cycles** — day-of-year and lunar-phase proxies as sine/cosine pairs, plus the gap. This is the nearest
#   thing here to an astrological feature.

#%%
def features(df):
    dm, dw = as_day(df.dob_older), as_day(df.dob_younger)
    ym = df.dob_older.str.slice(0, 4).astype(int)
    yw = df.dob_younger.str.slice(0, 4).astype(int)
    out = {"era_man": ym, "era_woman": yw, "era_mean": (ym + yw) / 2}
    out["gap_years"] = (dw - dm) / 365.2425
    out["gap_abs"] = out["gap_years"].abs()
    for nm, d in (("man", dm), ("woman", dw)):
        for period, label in ((365.2425, "yr"), (29.530588, "syn")):
            ang = 2 * np.pi * (d % period) / period
            out[f"{nm}_{label}_sin"] = np.sin(ang)
            out[f"{nm}_{label}_cos"] = np.cos(ang)
    # The difference of two phases is what a synastry claim is actually about.
    for period, label in ((365.2425, "yr"), (29.530588, "syn")):
        ang = 2 * np.pi * ((dw - dm) % period) / period
        out[f"diff_{label}_sin"] = np.sin(ang)
        out[f"diff_{label}_cos"] = np.cos(ang)
    return pd.DataFrame(out)


X = features(train)
ERA = [c for c in X.columns if c.startswith("era")]
CYC = [c for c in X.columns if c not in ERA]
print(f"{X.shape[1]} features: {len(ERA)} era, {len(CYC)} cyclic")


#%% [markdown]
# ### Cross-validated, and split three ways so the era is visible
#
# The point of scoring the era-only and cycles-only models separately is to see how much of the total is which.

#%%
def cv(cols, label, n_splits=5):
    oof = np.zeros(len(X))
    for tr, va in StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=7).split(X, y):
        mdl = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08,
                                             max_leaf_nodes=31, random_state=7)
        mdl.fit(X.iloc[tr][cols], y[tr])
        oof[va] = mdl.predict_proba(X.iloc[va][cols])[:, 1]
    auc = roc_auc_score(y, oof)
    print(f"  {label:<26} {auc:.4f}")
    return auc, oof


print("out-of-fold AUC on the training half:")
auc_era, _ = cv(ERA, "era only (2 years + mean)")
auc_cyc, _ = cv(CYC, "cycles only (no years)")
auc_all, oof_all = cv(list(X.columns), "both together")


#%% [markdown]
# Read those three against each other, not against 0.5. Era-only lands within about 0.008 of both-together,
# which says plainly that this model is mostly dating the cohort — and that it still beats an eighteen-tradition
# ephemeris stack while doing it.
#
# The cycles-only number is the one to build on: whatever it is above 0.5 is signal that does not come from
# knowing which decade the couple was born in.

#%%
final = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08,
                                       max_leaf_nodes=31, random_state=7).fit(X, y)
try:
    test = pd.read_csv(f"{BASE}/test.csv")
except FileNotFoundError:
    test = pd.read_csv("test.csv")
pred = final.predict_proba(features(test)[X.columns])[:, 1]
sub = pd.DataFrame({"id": test.id, LABEL: pred})
sub.to_csv("submission.csv", index=False)
print(f"wrote submission.csv — {len(sub):,} rows, mean {pred.mean():.4f}")
sub.head()


#%% [markdown]
# ## 6. Where to go from here
#
# Three directions that seem genuinely open:
#
# 1. **Find something that works inside one decade.** Fit and score within a single birth decade, where the era
#    cannot help. The cycles-only model above reaches about 0.597 with no year information at all, so there is
#    something there — the open question is how much of it survives when the era is held fixed rather than merely
#    withheld. Anything solid here is a real finding and nobody has published one on this data.
# 2. **Take a tradition the stack scored badly and do it properly.** `vedic_match` at 0.5557 is the aṣṭakūṭa
#    system for judging marriages, computed here under a ±6° smear on the Moon because there is no birth time.
#    A better treatment of that uncertainty — marginalising over the unknown hour instead of taking noon — might
#    be worth more than any new tradition.
# 3. **Attack the label noise.** A couple whose child went unrecorded is a false negative, and false negatives
#    are not uniformly distributed: they concentrate among the less-documented. Modelling that explicitly is a
#    different kind of idea from adding features.
#
# The dataset is CC0, the build is public, and the Foundation's own score is published so that beating it is
# unambiguous. If the answer turns out to be that two birth dates carry almost nothing beyond the era, that is
# the result and it will be published as such.
#
# — [ArtaQuest Foundation](https://artaquest.com) · [the live model](https://artaquest.github.io/artamatch/)
