"""
competition_pages.py — write the six pages of the artamatch-astrology competition, with the numbers READ from the
build rather than typed.

WHY THIS FILE EXISTS. publish_competition_v2.py holds the pages as constants written for the parenthood problem, and
those constants are what is live on Kaggle. Every number in them (positive rates, held-out AUCs, the 0.641 to beat)
describes a retired dataset. Retyping numbers is how they go stale, so this file takes them from the artefacts the
build actually produced — solution.csv, tradition_ranking.json, result.json — and refuses to write a page if any of
those is missing.

WHAT IT WRITES. abstract, Description, Evaluation, data-description, rules, Prizes — through the same
UpdateCompetitionPage / CreateCompetitionPage RPCs v2 used, plus the title and brief description. It never creates
or deletes a competition.

Usage:
    ~/.artamatch-venv/bin/python competition_pages.py <comp-dir> <model-dir>            # dry run: prints the pages
    AQ_DO_WRITE=1 ~/.artamatch-venv/bin/python competition_pages.py <comp-dir> <model-dir>   # writes them
"""
import csv
import json
import os
import sys
import time

import requests

SLUG = "artamatch-astrology"
B = "https://api.kaggle.com/v1/competitions.CompetitionApiService/"
CR = json.load(open(os.path.expanduser("~/.kaggle/kaggle.artafather.json")))
U, K = CR["username"], CR["key"]
if U != "artafather":
    raise SystemExit(f"the credential file names {U!r}, not artafather — refusing")

TITLE = "ArtaMatch Astrology: find the best astrology there is"
BRIEF = ("An open search for the best astrology there is. From two birth dates alone — the older partner's and "
         "the younger's, nothing else — predict whether a relationship lasted thirty years. Marriages, "
         "partnerships of any kind, business partnerships; everyone dead, so every relationship has ended. "
         "Scored across time: train on couples born 1600-1900, predict the ones born after.")


def numbers(comp, model):
    """Every figure a page cites, from the files. Missing file -> no page."""
    sol = list(csv.DictReader(open(os.path.join(comp, "solution.csv"))))
    lab = [c for c in sol[0] if c not in ("id", "Usage")][0]
    pub = [int(r[lab]) for r in sol if r["Usage"] == "Public"]
    prv = [int(r[lab]) for r in sol if r["Usage"] == "Private"]
    train = list(csv.DictReader(open(os.path.join(comp, "train.csv"))))
    tr_pos = sum(int(r[lab]) for r in train) / len(train)
    one_sided = sum(1 for r in train if "0000-00-00" in (r["dob_older"], r["dob_younger"]))
    coarse = sum(1 for r in train if r["dob_older"].endswith("-00") or r["dob_younger"].endswith("-00")) - one_sided
    rk = json.load(open(os.path.join(model, "tradition_ranking.json")))
    res = json.load(open(os.path.join(model, "result.json")))
    top = sorted(rk["traditions"], key=lambda t: -t["auc"])
    return {
        "label": lab, "n_train": len(train), "n_test": len(sol),
        "pub_n": len(pub), "prv_n": len(prv),
        "pub_pos": 100 * sum(pub) / len(pub), "prv_pos": 100 * sum(prv) / len(prv),
        "tr_pos": 100 * tr_pos, "te_pos": 100 * (sum(pub) + sum(prv)) / len(sol),
        "one_sided": one_sided, "coarse": coarse,
        "ens": rk["ensemble"], "era": rk["era_rule"], "n_heldout": rk["n_test"],
        "gap": res["baseline_auc"], "n_base": len(res.get("per_block", [])), "n_trad": len(rk["traditions"]),
        "top": top[:5], "bottom": top[-3:], "beat_era": sum(1 for t in rk["traditions"] if t["beats_era"]),
        "sample_id": sol[0]["id"],
    }


def pages(N):
    lab = N["label"]
    top_rows = "\n".join(f"| {t['name']} alone | {t['auc']:.4f} | {'above' if t['beats_era'] else 'below'} |"
                         for t in N["top"])
    ABSTRACT = f"""# Let's end this loneliness epidemic with astrology.

Two birth dates — the **older** partner's and the **younger**'s — and nothing else. Predict whether the
relationship lasted thirty years. Any relationship two people chose counts: a marriage, an unmarried or same-sex
partnership, a business partnership. Everyone in the data is dead, so every relationship in it has ended and none
was cut short by the records running out.

Scored **across time**: the training couples were born 1600–1900, the held-out couples after 1900. Plain AUC.

The Foundation's own nineteen-tradition astrology stack is published as a baseline, and so is the number it has
to be read against: the **era rule**, which knows only the two birth years. Whether anything beats it is the
question this competition exists to answer.

Prizes: 1,000 / 500 / 100 ArtaCoin. See the Prizes tab for what that is, stated plainly.
"""

    DESCRIPTION = f"""## Let's end this loneliness epidemic with astrology

This is an open search for the best astrology there is, conducted the only way that settles anything: by
measuring it on people who really lived, against a baseline that is not allowed to know astrology.

## The question

You are given two birth dates. The first is the **older** partner's, the second the **younger**'s — the order is
computed from the dates, and nothing about anybody's sex is recorded or used. Predict the probability that
their relationship lasted **thirty years or longer**.

A relationship is anything two people chose: a marriage (`P26` on Wikidata), an unmarried partnership (`P451`),
a business or sporting partnership (`P1327`), or Wikidata's general "significant person" relation (`P3342`,
with every pair that also carries a family link excluded). Family relations are not here — a sibling does not
"last".

## Where the label comes from

Exactly as a Wikipedia infobox reads a marriage — *"m. 1903; div. 1919"*. If an end date is recorded, the
relationship ran from its start to that end. If not, it ran until somebody died, so the end is the earlier of
the two deaths. `{lab}` is `(end − start) ≥ 30 years`. **A relationship ended by a death is not automatically a
long one**: twelve years is a 0, forty years is a 1.

The relationship's own dates are used to compute that and are then **thrown away**. They are not columns. The
start year is the most era-revealing thing about a couple, and a model given it would learn the century.

## Why everyone is dead, and why the split is by time

A relationship that has not ended cannot be given a duration. Rather than cap the birth years and infer it, the
dataset requires a datable end — a recorded end date or a partner's death — and the held-out half requires both
partners dead. So it reaches into the twentieth century and stops on its own: there are essentially no couples
born after 1975 who are both dead with dated relationships.

The split is **temporal**. You fit on couples born up to 1900 and are scored on couples born after. That is the
harder and the honest question — not "rank couples drawn from the years you learned from" but "learn from the
historical couples and predict the modern ones". An earlier version of this project split at random and scored
0.6452 inside its training era against 0.5159 out of it: a 0.13 gap that was entirely a model interpolating a
calendar it had already seen.

## The one thing that will decide this competition

**Most of what looks like signal in two birth dates is *when* the people were born.** The base rate moves across
the boundary — {N['tr_pos']:.1f}% of training relationships reach thirty years against {N['te_pos']:.1f}% of the
held-out ones — and because everyone is dead, a couple born late who are already dead died young, so "born late"
leans negative for a reason that has nothing to do with astrology.

So the number to read every score against is not 0.5. It is the **era rule**: rank couples by the sum of their
two birth years and nothing else. On the held-out couples it scores **{N['era']:.4f}**. A model above chance but
below that has read the calendar rather than the couple.

## The Foundation's own entry

A stack of {N['n_base']} feature blocks across {N['n_trad']} traditions — Hellenistic, Vedic, Chinese, Maya, Uranian,
heliacal-rising and lunar-calendar systems, and Pythagorean numerology — computed from the two dates through a
Swiss Ephemeris. Its held-out AUC is **{N['ens']:.4f}** against the era rule's {N['era']:.4f}. Every tradition is
also scored alone on the same held-out couples; {N['beat_era']} of {N['n_trad']} beat the era rule.

| held out, couples born after the training window | AUC | vs era rule |
|---|---|---|
| The era rule (two birth years) | {N['era']:.4f} | — |
| The Foundation's stack | {N['ens']:.4f} | {'above' if N['ens'] > N['era'] else 'below'} |
{top_rows}

The Foundation is publishing that whichever way it reads. A leaderboard that tops out at the era rule is a
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
| Two-parameter logistic on the age gap (younger − older) | {N['gap']:.4f} |
| **The era rule: the sum of the two birth years** | **{N['era']:.4f}** |
| The Foundation's {N['n_trad']}-tradition stack | {N['ens']:.4f} |

**Read the era rule as the bar.** It knows nothing but when the couple was born, and on a split by time it is
what a model must beat to have read the couple rather than the calendar. The Description tab explains why it
scores what it scores.
"""

    DATA_DESCRIPTION = f"""## Files

| file | rows | what |
|---|---|---|
| `train.csv` | {N['n_train']:,} | `dob_older`, `dob_younger`, `{lab}` |
| `test.csv` | {N['n_test']:,} | `id`, `dob_older`, `dob_younger` |
| `sample_submission.csv` | {N['n_test']:,} | `id`, `{lab}` = 0.5 |

## The columns

* `dob_older` — the older partner's date of birth, `YYYY-MM-DD`.
* `dob_younger` — the younger partner's date of birth.
* `{lab}` — 1 if the relationship lasted thirty years or longer, else 0.

**The test rows are complete and day-precision.** Both dates known to the day, both partners dead, no
placeholder dates, the couple's later birth after 1900.

**The training rows are deliberately not.** A date may be known only to the month (`1809-11-00`) or only to the
year (`1802-00-00`), and one partner may be absent from Wikidata entirely (`0000-00-00`, always in the second
column, since a one-sided row has no age order). `00` means unknown; `0000-00-00` means absent. Of the
{N['n_train']:,} training rows, {N['one_sided']:,} are one-sided and {N['coarse']:,} more have a coarse date.

```
dob_older,dob_younger,{lab}
1794-06-12,1801-03-27,1     <- both known to the day
1802-00-00,1809-11-00,0     <- one year only; the other year and month
1777-04-30,0000-00-00,1     <- the second partner is not in Wikidata at all
```

A relationship's duration is known just as exactly when one partner's birthday is not, so those rows carry a real
label and half an input. Drop them in one line if you want only clean rows; use them if you want the data.

## Two traps in the dates, both handled

**1 January is a placeholder** — among day-precision births 1600–1900 it occurs 2.07× as often as a median
January day, because sources that knew only the year were imported with a day. It is excluded from the test half
at day precision (and its Julian image on 11/12/13 January likewise), kept in the training half as noise, and
never excluded at year precision, where `1850-01-01` is simply how Wikidata spells 1850.

**Every date is proleptic Gregorian**, whatever calendar the source recorded — Newton's Julian-tagged birth
carries the literal `1643-01-04`. No conversion is needed.

## Provenance

Built by a public notebook that runs the SPARQL live against Wikidata, so anyone can re-run it and contradict
it: `artafather/artamatch-build-the-dataset`. The dataset itself is `artaquest-foundation/artamatch-astrology`,
CC0.
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
extra rows.

What is **not** fair is looking the answer up. The label comes from a public database, so for any given couple a
determined person can find out how long the relationship lasted. Doing that is not modelling and it produces a
leaderboard nobody learns anything from. Predict from the two dates.

## What this competition is about

Finding the best astrology there is, by measuring it. How much do two birth dates carry about how long a
relationship lasts, which method extracts the most of it, and how much of what looks like signal is the era
rather than the pairing.

A negative result is a real result here and will be reported as one: a leaderboard that tops out at the era rule
would be worth publishing, and so would one that clearly beats it.

Nothing here is advice about any real person, and no score means anything about anybody's life.
"""

    PRIZES = """## The podium

| place | prize |
|---|---|
| 1st | **1,000 ArtaCoin** |
| 2nd | **500 ArtaCoin** |
| 3rd | **100 ArtaCoin** |

Ranked on the **private** leaderboard at the deadline.

## What ArtaCoin is, stated plainly

ArtaCoin (₳) is the internal currency of artaquest.com, the ArtaQuest Foundation's platform. It is spent there —
on challenge entry fees and in the shop — and it is **not** cash, not a cryptocurrency, and not redeemable for
money. The Foundation publishes its full double-entry ledger at artaquest.com/finances, including the fact that
ArtaCoin is deliberately not fully backed, so anyone can read exactly what they are being offered before
deciding whether it is worth their afternoon.

To receive a prize you will need an account on artaquest.com for the coin to land in. If that is not something
you want, enter anyway — the leaderboard and the dataset are the substance here, and the Foundation will publish
whatever the results turn out to be either way.

## Why the amounts are small

Because the point is not the money. This competition exists to find out how much two birth dates actually carry
about how long a relationship lasts, and which method extracts the most of it. A large purse would attract
people optimising a leaderboard; a small one attracts people who find the question interesting. The
Foundation's own score is published so that beating it is unambiguous, and a negative result — a leaderboard
that tops out at the era rule — will be reported as the real result it would be.
"""
    return [("abstract", ABSTRACT), ("Description", DESCRIPTION), ("Evaluation", EVALUATION),
            ("data-description", DATA_DESCRIPTION), ("rules", RULES), ("Prizes", PRIZES)]


def call(ep, payload, tries=5):
    for i in range(tries):
        try:
            r = requests.post(B + ep, json=payload, auth=(U, K), timeout=300)
            try:
                body = r.json()
            except Exception:
                body = r.text[:200]
            if r.status_code >= 500 and i < tries - 1:
                time.sleep(3 * (i + 1))
                continue
            return r.status_code, body
        except Exception as e:
            if i == tries - 1:
                return None, f"{type(e).__name__} {e}"
            time.sleep(3 * (i + 1))
    return None, "gave up"


def main():
    comp = sys.argv[1] if len(sys.argv) > 1 else "/tmp/aqdurcomp"
    model = sys.argv[2] if len(sys.argv) > 2 else "/tmp/aqdurmodel"
    N = numbers(comp, model)
    P = pages(N)
    print(f"  numbers from the build: train {N['n_train']:,} · test {N['n_test']:,} · held-out ensemble "
          f"{N['ens']:.4f} vs era {N['era']:.4f} · gap {N['gap']:.4f} · public {N['pub_pos']:.2f}% / private "
          f"{N['prv_pos']:.2f}% positive")
    for name, body in P:
        assert "parent" not in body.lower() and "child" not in body.lower(), f"{name} still says parent/child"
        assert "man" not in body.replace("human", "").replace("Roman", "").split() and "woman" not in body, \
            f"{name} still names a man or woman"
    if os.environ.get("AQ_DO_WRITE") != "1":
        print("\n  DRY RUN — set AQ_DO_WRITE=1 to write the pages")
        for name, body in P:
            print(f"    would write {name:<18} {len(body):>6,} chars")
        return
    st, _ = call("UpdateCompetitionSettings", {
        "competitionName": SLUG, "updateMask": "title,briefDescription",
        "settings": {"competitionName": SLUG, "title": TITLE, "briefDescription": BRIEF}})
    print(f"  title + brief -> {st}")
    for name, body in P:
        st, b = call("UpdateCompetitionPage", {
            "competitionName": SLUG, "pageName": name, "updateMask": "content,isPublished",
            "page": {"name": name, "content": body, "isPublished": True}})
        if st and st >= 400:
            st2, b = call("CreateCompetitionPage", {
                "competitionName": SLUG, "page": {"name": name, "content": body, "isPublished": True}})
            st = f"{st} then create {st2}"
        print(f"  page {name:<18} {len(body):>6,} chars -> {st}")


if __name__ == "__main__":
    main()
