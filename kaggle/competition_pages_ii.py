"""
competition_pages_ii.py — the six pages of the SECOND-EDITION competition (the start date as an input), with every
number READ from the build and the model, never typed.

Reuses competition_pages.py's plumbing (numbers, call, the page-writing loop) and replaces only what changed: the
slug, the title and brief (both inside Kaggle's launch-checklist limits of 60 and 140 characters, which the API
does not enforce and the first push of the creator exceeded), and the copy -- which now has to say that the
start IS a column, why a year-only start reads 1 January, what it makes possible (age at the start), what it does
to the held-out half (the 1996 ceiling), and that the bar has moved from the era rule to the two ages.

Usage: AQ_DO_WRITE=1 python competition_pages_ii.py /tmp/aqmycomp /tmp/aqmymodel
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import competition_pages as P1                                       # noqa: E402

SLUG = os.environ.get("AQ_COMPETITION", "artamatch-marriage-year")
TITLE = "ArtaMatch Astrology II: two births and a wedding date"
BRIEF = ("Two birth dates and the date it began: did the relationship last thirty years? "
         "Train on births 1600-1900, predict the couples born after.")
assert len(TITLE) <= 60 and len(BRIEF) <= 140, (len(TITLE), len(BRIEF))
P1.SLUG, P1.TITLE, P1.BRIEF = SLUG, TITLE, BRIEF


def numbers(comp, model):
    N = P1.numbers(comp, model)
    res = json.load(open(os.path.join(model, "result.json")))
    N["ages"] = res.get("baseline_auc")                       # boosted trees on the two ages at the start
    N["age_older"] = res.get("baseline_older_age_auc")
    N["gap"] = res.get("baseline_gap_auc", res.get("baseline_auc"))
    import csv
    te = list(csv.DictReader(open(os.path.join(comp, "test.csv"))))
    tr = list(csv.DictReader(open(os.path.join(comp, "train.csv"))))
    N["sy_te"] = (min(int(r["start"][:4]) for r in te), max(int(r["start"][:4]) for r in te))
    N["sy_tr"] = (min(int(r["start"][:4]) for r in tr), max(int(r["start"][:4]) for r in tr))
    N["j1_te"] = 100 * sum(1 for r in te if r["start"][5:] == "01-01") / len(te)
    N["j1_tr"] = 100 * sum(1 for r in tr if r["start"][5:] == "01-01") / len(tr)
    return N


def pages(N):
    lab = N["label"]
    top_rows = "\n".join(f"| {t['name']} alone | {t['auc']:.4f} |" for t in N["top"])
    ages = f"{N['ages']:.4f}" if N["ages"] is not None else "—"
    age_older = f"{N['age_older']:.4f}" if N["age_older"] is not None else "—"
    ABSTRACT = f"""# Let's end this loneliness epidemic with astrology.

**The second ArtaMatch competition.** Two birth dates — the **older** partner's and the **younger**'s — and the
**date the relationship began** (the wedding date; 1 January where only the year is known). Predict whether it lasted thirty years. Any relationship two people chose
counts: a marriage, an unmarried or same-sex partnership, a business partnership. Everyone in the data is dead,
so every relationship in it has ended.

Scored **across time**: the training couples were born 1600–1900, the held-out couples after 1900. Plain AUC.

The first edition (`artamatch-astrology`) gave two dates and nothing else, and its leaderboard was decided by
the age gap. This edition adds the one thing that changes the question: with the start known, each
partner's **age at the start** is on the table, and it is a far stronger ordinary predictor than the gap. So the
bar has moved: the number to beat is not chance and not the era rule but **{ages}** — boosted trees on the two
ages at the start, published beside the Foundation's own nineteen-tradition astrology stack.

Prizes: 1,000 / 500 / 100 ArtaCoin. See the Prizes tab for what that is, stated plainly.
"""

    DESCRIPTION = f"""## Let's end this loneliness epidemic with astrology

This is an open search for the best astrology there is, conducted the only way that settles anything: by
measuring it on people who really lived, against baselines that are not allowed to know astrology.

## The question

You are given three dates. The first is the **older** partner's birth, the second the **younger**'s — the
order is computed from the dates, and nothing about anybody's sex is recorded or used. The third is when the
relationship **began** — the wedding date, for a marriage. Predict the probability that it
lasted **thirty years or longer**.

A relationship is anything two people chose: a marriage (`P26` on Wikidata), an unmarried partnership (`P451`),
a business or sporting partnership (`P1327`), or Wikidata's general "significant person" relation (`P3342`,
with every pair that also carries a family link excluded). Family relations are not here — a sibling does not
"last".

## Where the label comes from

Exactly as a Wikipedia infobox reads a marriage — *"m. 1903; div. 1919"*. If an end date is recorded, the
relationship ran from its start to that end. If not, it ran until somebody died, so the end is the earlier of
the two deaths. `{lab}` is `(end − start) ≥ 30 years`. **A relationship ended by a death is not automatically a
long one**: twelve years is a 0, forty years is a 1.

## What changed from the first edition, and how to read the third date

The first edition computed the label from the relationship's own dates and then threw them away. This one keeps
the **start**, as a full date. Read its day with care: Wikidata's `P580` qualifier is often year-precision, and
a year-only start is published as **`YYYY-01-01`** — so a 1 January in this column is usually a year-only record
and only sometimes a real New Year's Day wedding, and nothing in the value tells the two apart. About
{N['j1_tr']:.0f}% of training starts and {N['j1_te']:.0f}% of held-out starts are 1 January. The year is exact in
every row.

What it buys a model is real: each partner's **age at the start**, the **era** the relationship began in, a
**wedding chart** for the rows whose day is real, and — for the held-out half — the ceiling on how long it could
possibly have run.

## Why everyone is dead, why the split is by time, and the 1996 ceiling

A relationship that has not ended cannot be given a duration. Rather than cap the birth years and infer it, the
dataset requires a datable end — a recorded end date or a partner's death — and the held-out half requires both
partners dead. The split is **temporal**: you fit on couples born up to 1900 and are scored on couples born
after. Learn from the historical couples and predict the modern ones.

That rule now has a consequence you can compute exactly, because the start is a column. A held-out couple
is dead by 2026, so a relationship that began in year *s* cannot have lasted longer than *2026 − s*. Anything
that began **after 1996 cannot reach thirty years** — its label would be 0 by arithmetic — and such rows are
**removed from the test set** rather than left in as free points. Nearer the boundary the effect is soft but
real: the later the start, the more "both already dead" selects for early deaths, and an early death ends a
relationship. The held-out start years run {N['sy_te'][0]}–{N['sy_te'][1]}; the training half's
{N['sy_tr'][0]}–{N['sy_tr'][1]}, all from couples born by 1900, so **the training rows contain no couple for
whom this ceiling ever binds** — a model cannot learn it from them; it has to come from the definition.

## The numbers that will decide this competition

**Age at the start** is the strongest ordinary predictor here and it owes nothing to any tradition. On the
held-out couples, the older partner's age at the start alone scores **{age_older}**; boosted trees on the two
ages score **{ages}**. The age gap, which decided the first edition, scores {N['gap']:.4f} on these rows. Read
every leaderboard place against **{ages}**, not against 0.5.

## The Foundation's own entry

A stack of {N['n_base']} feature blocks across {N['n_trad']} traditions — Hellenistic, Vedic, Chinese, Maya, Uranian,
heliacal-rising and lunar-calendar systems, and Pythagorean numerology — computed from the two birth dates
through a Swiss Ephemeris. Its held-out AUC is **{N['ens']:.4f}**. Every tradition is also scored alone on the
same held-out couples.

| held out, couples born after the training window | AUC |
|---|---|
| Boosted trees on the two ages at the start (no astrology) | {ages} |
| The older partner's age at the start alone | {age_older} |
| The age gap alone (the first edition's bar) | {N['gap']:.4f} |
| The era rule (sum of the two birth years) | {N['era']:.4f} |
| The Foundation's {N['n_trad']}-tradition astrology stack | {N['ens']:.4f} |
{top_rows}

The Foundation is publishing that whichever way it reads. A leaderboard that tops out at the two ages is a
result, and it will be reported as one.
"""

    EVALUATION = f"""## Metric

**Area under the ROC curve** between your predicted probability and the observed `{lab}`.

Only the ranking matters. A submission that gets every ordering right scores 1.0 whatever its absolute
probabilities are; a submission that ranks at random scores 0.5.

## Submission format

One row per id in `test.csv`, plus a header:

```
id,{lab}
{N['sample_id']},0.63
```

`{lab}` is a probability. Any real number is accepted and only its order is used. Every id in `test.csv` must
appear exactly once. `sample_submission.csv` predicts 0.5 for every row and scores 0.5.

## The split

{N['pub_n']:,} test rows form the public leaderboard and {N['prv_n']:,} the private one, drawn at random per
couple. Both halves carry both classes: the public half is {N['pub_pos']:.2f}% positive and the private half
{N['prv_pos']:.2f}%, so an AUC is defined on each.

The train/test division is by **time and by person**: every held-out couple was born after 1900, every
training couple by 1900, and nobody in the test set appears anywhere in the training file.

## What a good score looks like

| held out | AUC |
|---|---|
| Random, or the sample submission | 0.500 |
| The era rule: the sum of the two birth years | {N['era']:.4f} |
| Two-parameter logistic on the age gap (younger − older) | {N['gap']:.4f} |
| The older partner's age at the start, alone | {age_older} |
| **Boosted trees on the two ages at the start** | **{ages}** |
| The Foundation's {N['n_trad']}-tradition astrology stack | {N['ens']:.4f} |

**Read the two ages as the bar.** They know nothing but when each partner was born and when the relationship
began, and on a split by time they are what a model must beat to have read the couple rather than the calendar.
"""

    DATA_DESCRIPTION = f"""## Files

| file | rows | what |
|---|---|---|
| `train.csv` | {N['n_train']:,} | `dob_older`, `dob_younger`, `start`, `{lab}` |
| `test.csv` | {N['n_test']:,} | `id`, `dob_older`, `dob_younger`, `start` |
| `sample_submission.csv` | {N['n_test']:,} | `id`, `{lab}` = 0.5 |

## The columns

* `dob_older` — the older partner's date of birth, `YYYY-MM-DD`.
* `dob_younger` — the younger partner's date of birth.
* `start` — the date the relationship began, `YYYY-MM-DD`; the wedding date for a marriage. Present in every
  row of both files. **`YYYY-01-01` means the year is known and the day is not** (about {N['j1_tr']:.0f}% of
  training rows, {N['j1_te']:.0f}% of test rows); a real 1 January cannot be told from it.
* `{lab}` — 1 if the relationship lasted thirty years or longer, else 0.

**The test rows are complete and day-precision.** Both dates known to the day, both partners dead, no
placeholder dates, the couple's later birth after 1900, and the start in or before 1996 (later starts
cannot reach thirty years before 2026 and are excluded).

**The training rows are deliberately not.** A date may be known only to the month (`1809-11-00`) or only to the
year (`1802-00-00`), and one partner may be absent from Wikidata entirely (`0000-00-00`, always in the second
column, since a one-sided row has no age order). `00` means unknown; `0000-00-00` means absent. Of the
{N['n_train']:,} training rows, {N['one_sided']:,} are one-sided and {N['coarse']:,} more have a coarse date.
The start is never missing.

```
dob_older,dob_younger,start,{lab}
1794-06-12,1801-03-27,1823-05-19,1     <- both known to the day; wed 19 May 1823
1802-00-00,1809-11-00,1831-01-01,0     <- one year only; the other year and month; the start known to the year
1777-04-30,0000-00-00,1799-09-02,1     <- the second partner is not in Wikidata at all
```

A relationship's duration is known just as exactly when one partner's birthday is not, so those rows carry a real
label and most of an input. Drop them in one line if you want only clean rows; use them if you want the data.

## Two traps in the dates, both handled

**1 January is a placeholder** — among day-precision births 1600–1900 it occurs 2.07× as often as a median
January day, because sources that knew only the year were imported with a day. It is excluded from the test half
at day precision (and its Julian image on 11/12/13 January likewise), kept in the training half as noise, and
never excluded at year precision, where `1850-01-01` is simply how Wikidata spells 1850.

**Every date is proleptic Gregorian**, whatever calendar the source recorded — Newton's Julian-tagged birth
carries the literal `1643-01-04`. No conversion is needed.

## Provenance

Built by a public notebook that runs the SPARQL live against Wikidata, so anyone can re-run it and contradict
it: `artafather/artamatch-build-the-dataset`. The dataset itself is `artaquest-foundation/artamatch-marriage-year`,
CC0. The first edition, two dates only, is `artaquest-foundation/artamatch-astrology`.
"""

    RULES = f"""## The short version

Predict `{lab}` for every row of `test.csv`. Best AUC on the private leaderboard wins: 1,000 ArtaCoin for
first, 500 for second, 100 for third. ArtaCoin is spendable on artaquest.com and is not cash — see the Prizes tab.

## Submissions

Up to the daily limit shown on the submission page. Pick your final submissions before the deadline; the private
leaderboard decides the outcome.

## Teams and accounts

**One account per person.** This is Kaggle's rule, not ours, and it is the one worth restating: a person entering
from several accounts invalidates their own results and everyone else's comparison. Team up openly instead.

## What you may use

Anything public. The dataset is CC0 and the build notebook is public, so re-running the SPARQL yourself is fair
game and is actively encouraged — Wikidata changes, and a build from a different day is a legitimate source of
extra rows. The ceiling that follows from "both dead by 2026" is derivable from this page and is fair game too.

What is **not** fair is looking the answer up. The label comes from a public database, so for any given couple a
determined person can find out how long the relationship lasted. Doing that is not modelling and it produces a
leaderboard nobody learns anything from. Predict from the three dates.

## What this competition is about

Finding the best astrology there is, by measuring it. How much do two birth dates and a wedding date carry about
how long a relationship lasts, which method extracts the most of it, and how much of what looks like signal is
age and era rather than the pairing.

A negative result is a real result here and will be reported as one: a leaderboard that tops out at the two
ages at the start would be worth publishing, and so would one that clearly beats it.

Nothing here is advice about any real person, and no score means anything about anybody's life.
"""
    PRIZES = P1.pages(N)[5][1].replace(
        "a leaderboard\nthat tops out at the era rule",
        "a leaderboard\nthat tops out at the two ages at the start").replace(
        "how much two birth dates actually carry",
        "how much two birth dates and a wedding date actually carry")
    return [("abstract", ABSTRACT), ("Description", DESCRIPTION), ("Evaluation", EVALUATION),
            ("data-description", DATA_DESCRIPTION), ("rules", RULES), ("Prizes", PRIZES)]


P1.numbers, P1.pages = numbers, pages

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.argv = [sys.argv[0], "/tmp/aqmycomp", "/tmp/aqmymodel"]
    P1.main()
