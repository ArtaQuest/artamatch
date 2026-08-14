"""
publish_competition_v2.py — create the ArtaMatch competition properly, and retire the rushed one.

WHY A SECOND COMPETITION RATHER THAN A FIX. The competition API has no delete: the only removal RPC is
`DeleteCompetitionPage`, which removes a tab. So the first attempt cannot be taken down, only superseded — this
script creates a clean one and then disables submissions on the old one and retitles it so nobody enters it by
mistake.

WHAT WAS WRONG WITH THE FIRST ONE. Its pages were stubs, its test set repeated every couple fourteen times over a
grid of degraded date precisions, and the metric that grid implies — the row-count-weighted mean of fourteen
per-cell AUCs — is not something Kaggle can score. There is no grouped-mean-AUC among the built-in metrics and no
API field to supply a custom one, so the leaderboard could never have worked.

WHAT THIS ONE ASKS. One row per couple, both birth dates known to the day, ranked by plain AUC. A metric Kaggle
has, a submission a person can read, and one unambiguous question: put the couples who had a child together above
the couples who did not.

THE METRIC STILL HAS TO BE SET BY HAND. `CompetitionSettings` has no metric field and neither does
`ApiCreateCompetitionRequest` — verified by listing both — so the final step is one dropdown in the UI. This
script prints exactly what to choose and stops rather than pretending it finished.

Usage: AQ_DO_CREATE=1 ~/.artamatch-venv/bin/python publish_competition_v2.py /tmp/aqcomp
"""
import json
import os
import sys
import time

import requests

DATA = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "/tmp/aqcomp"
SLUG = "artamatch-astrology"
OLD_SLUG = "artamatch-parents-together"
ORG_ID = 5418
DEADLINE = "2027-02-28T23:59:00Z"
B = "https://api.kaggle.com/v1/competitions.CompetitionApiService/"

CR = json.load(open(os.path.expanduser("~/.kaggle/kaggle.artafather.json")))
U, K = CR["username"], CR["key"]

TITLE = "ArtaMatch Astrology: find the best astrology there is"
BRIEF = ("An open search for the best astrology there is. From two birth dates alone — nothing else — predict "
         "whether a child exists who names both people as parents. Any tradition, any method, one honest number.")

MOTTO = "Let's end this loneliness epidemic with astrology."

ABSTRACT = """# Let's end this loneliness epidemic with astrology.

**This competition is a search for the best astrology there is.**

Astrology makes a checkable claim: that a birth date carries information about a life. Here it is put to the one
test that settles arguments — a held-out set, a single number, and a leaderboard anyone can climb.

From a man's date of birth and a woman's, and nothing else, predict whether a child exists who names both of
them as parents. No names, no places, no occupations, no nationality, no marriage date. Three columns in and one
bit out.

Bring any tradition or any method. Western tropical, jyotiṣa, BaZi, Zǐ Wēi Dǒu Shù, the Maya Long Count, the
Hamburg School dials, gradient boosting on the raw day numbers — the leaderboard does not care where a prediction
comes from, only how well it ranks. The Foundation has published its own attempt and the score it reached, so
there is a specific number to beat rather than a vague target.

107,738 couples to learn from, all born between 1800 and 1950 — a window chosen deliberately, for a reason worth
reading before you start."""

DESCRIPTION = """## Let's end this loneliness epidemic with astrology

That is the motto, and this competition is the part of it that can actually be checked.

Astrology is usually argued about. Here it is measured. If a birth date carries anything about who a person ends
up building a life with, it should show up as a number on a held-out set — and if it does not, that is worth
knowing too, because a method that cannot beat the difference between two dates is not going to help anybody find
anyone.

Two people, two dates of birth: did they have a child together? The training file has three columns and 107,738
rows, the test file has two dates and an id, and there is nothing else to work with. Strip away names, places,
occupations and nationality and what remains is precisely the input astrology says is sufficient.

**Every tradition is welcome and none is privileged.** Compute a synastry chart or a kūṭa score, count the
sexagenary cycle, place the Long Count, run the 90° dial, or ignore astrology entirely and throw gradient
boosting at two integers. The leaderboard ranks predictions, not pedigrees. What it will settle is a narrow but
real question: how much does a birth date actually carry about this outcome, and which method extracts the most
of it.

The Foundation's own entry is an 18-tradition, 54-model stack computing about 57,000 features from the two dates
through a Swiss Ephemeris. It reaches **0.624**. That number is published so a leaderboard place means something
concrete, and so that beating it is unambiguous.

## Why every couple was born between 1800 and 1950

This is the part that makes or breaks a submission, so it is stated first.

An earlier version of this data ran from 1800 to 2026, and its dominant signal was not anything about the couple
— it was **exposure**. Recorded parenthood ran at about 58% for couples born in the 1800s and 2% for the 1990s,
because a couple born in 1990 may not have finished having children, and any child they do have has not had time
to become notable enough for a public database to record. Any smooth function of two dates scored well on that
data simply by identifying the era.

Restricting the parents to a 150-year window removes that cliff. Everyone here has had a full reproductive life,
and their children have had decades to be written about. What is left is a residual gradient of **0.385** across
decades — 0.738 for couples born in the 1800s, settling near 0.40 from 1900 onwards — against roughly 0.56 for
the unrestricted version. The residual is real and it is not zero. It is printed in the build notebook per
decade so you can read any claim against it.

## How a couple got into the data

Either Wikidata states a partnership between them — `P26` spouse or `P451` unmarried partner — or some person
names both of them as its parents.

The second kind is positive by construction, so it appears **only in the training file**. The test set is
declared partnerships alone. An early version of this dataset discovered couples *through* their children, which
made "has a child" identical to "was found via a child" — the label was the discovery route wearing a disguise.
Keeping the two universes separate is what stops that.

The label itself comes from a person naming both partners, and Wikidata records that fact two incompatible ways
that are not kept in sync: the child-side statement (`P22` father, `P25` mother) finds 67,198 pairs, the
parent-side statement (`P40` child) finds 67,378, and the union finds 93,738. Asking only the obvious way misses
26,540 couples.

## What the label does not mean

`parents_together = 0` means no child naming both partners is recorded. It does not mean they had no children.
A couple whose child was never written down counts here as a couple without one, and there is no way to tell the
two apart from inside the data. Any model here is predicting **what a public record contains**, not what
happened in anyone's life.

## Provenance

Every row comes from SPARQL queries that are printed in a public, re-runnable notebook, so the build can be
repeated and can disagree with this copy as Wikidata changes:

- the dataset: `artaquest-foundation/artamatch-astrology`
- how it was built: `artafather/artamatch-build-the-dataset`
- the Foundation's model, explained: `artafather/artamatch-the-best-astrology-so-far-explained`

## The prizes

1,000 ArtaCoin for first place, 500 for second, 100 for third, on the private leaderboard at the deadline.
ArtaCoin is the internal currency of artaquest.com — spendable there, not cash and not a cryptocurrency — and the
Foundation publishes its full ledger, so read the Prizes tab before deciding whether it is worth your afternoon.

The ArtaQuest Foundation runs this."""

EVALUATION = """## Metric

**Area under the ROC curve** between your predicted probability and the observed `parents_together`.

Only the ranking matters. A submission that gets every ordering right scores 1.0 whatever its absolute
probabilities are; a submission that ranks at random scores 0.5.

## Submission format

One row per id in `test.csv`, plus a header:

```
id,parents_together
c000001,0.63
c000002,0.11
```

`parents_together` is a probability. Any real number is accepted and only its order is used, but values outside
[0, 1] make the file harder for anyone else to read.

Every id in `test.csv` must appear exactly once. `sample_submission.csv` predicts 0.5 for every row and scores
0.5 — it is there to show the shape, not as a starting point worth beating.

## The split

30% of the test rows form the public leaderboard and 70% the private one, drawn at random per couple. Both
halves carry both classes: the public half is 45.72% positive and the private half 44.81%, so an AUC is defined
on each.

Because the split is by couple and the underlying train/test division is by **person group** — connected
components of the partnership graph — nobody in the test set appears anywhere in the training file. A model
cannot recognise a person it has already seen.

## What a good score looks like, and a warning

| held-out | AUC |
|---|---|
| Random, or the sample submission | 0.500 |
| Logistic on the signed difference of the two dates | 0.512 |
| The Foundation's 18-tradition, 54-model astrology stack | 0.624 |
| **Two birth YEARS and their mean, in a gradient booster** | **0.635** |
| **The same plus day-of-year and lunar-phase cycles — 17 features** | **0.641** |

Read that carefully, because it is the most useful thing on this page: **three integers beat the astrology
stack.** The stack computes about 57,000 features from eighteen traditions through a Swiss Ephemeris and is
worse on this task than the two birth years alone.

The Foundation is publishing that rather than hiding it, and it sets the bar honestly: **the number to beat is
0.641, not 0.624.** A submission at 0.63 has not beaten astrology — it has failed to beat two integers.

Why this happens is on the Description tab, and it is the whole point of the competition. Recorded parenthood
still varies by birth decade inside the 1800-1950 window, from 0.738 in the 1800s to about 0.40 from 1900 on, so
knowing roughly when a couple was born is most of the available signal. Any long-baseline calendar quantity —
a Saros cycle, an Egyptian civil year, a Long Count interval — is partly an era feature wearing astronomy.

**The interesting score is not the highest one.** A model that works *within* a single birth decade, where the
era cannot help, would be a genuinely new result. A 17-feature model with no year information at all reaches
about 0.597, so something cyclic is present; nobody has yet shown how much of it survives when the era is held
fixed. The full recipe is in `artafather/artamatch-the-best-astrology-so-far-explained`."""

DATA_DESCRIPTION = """## Files

| file | rows | what |
|---|---|---|
| `train.csv` | 107,738 | three columns: two dates and the label |
| `test.csv` | 16,469 | an id and two dates |
| `sample_submission.csv` | 16,469 | the format, predicting 0.5 everywhere |

## Columns

| column | meaning |
|---|---|
| `dob_man` | the man's date of birth, `YYYY-MM-DD` |
| `dob_woman` | the woman's date of birth |
| `parents_together` | 1 if a child exists naming **both** of them as parents, else 0 |

**Column order carries the sex.** The first column is the man and the second the woman, assigned from Wikidata's
`P21` — or, for pairs found through a child, from the parental role itself, since `P22` is father and `P25` is
mother. An earlier version ordered each pair by Q-number, which made "the first column is the man" false for
45,182 of 87,762 rows and scrambled the sign of every asymmetric feature.

## Missing parts of a date are written `00`, in the training file only

`1850-03-17` is a day, `1850-03-00` a month, `1850-00-00` a year.

Wikidata pads an unknown day with `01`, which would make a year-only birth indistinguishable from a genuine
1 January birthday — and 42.7% of rows carried such a date, so "is this a 1 January" became a readable proxy for
how well documented a person is, which correlates with whether a child was recorded. Writing the missingness
down removes the coincidence.

The same reasoning is why **every 1 January is stored as a year**. Among 167,044 day-precision births, 1 January
occurs 767 times against a median day-of-year count of 456 — a 1.7x excess, where 2 January and 31 December both
sit at 1.0x and even Christmas Day reaches only 1.28x. Roughly 311 of those are records whose source knew only
the year and whose importer wrote a day anyway. About 456 genuine 1 January birthdays lose their day as a
result; that is the cost, and it is the right side to err on.

**The test set has no `00` at all.** Both dates in every test row are known to the day. That is what keeps the
metric one question rather than fourteen.

## Also enforced

Both partners human (`P31 = Q5`, which removes 10,641 non-human entities with declared partnerships — an earlier
build contained George Jetson with a declared spouse and recorded children); opposite sex; births less than 60
years apart; one row per distinct pair, keeping the finest available precision; and no Wikipedia-article filter,
which makes the data more inclusive at the cost of false negatives — real children simply not recorded, which
depresses a measured AUC rather than inflating it."""

RULES = """## The short version

Predict `parents_together` for every row of `test.csv`. Best AUC on the private leaderboard wins: 1,000 ArtaCoin
for first, 500 for second, 100 for third. ArtaCoin is spendable on artaquest.com and is not cash — see the
Prizes tab.

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
determined person can find out whether a child is recorded. Doing that is not modelling and it produces a
leaderboard nobody learns anything from. Predict from the two dates.

## What this competition is about

Finding the best astrology there is, by measuring it. How much do two birth dates carry about a shared child,
which method extracts the most of it, and how much of what looks like signal is the era rather than the pairing.

A negative result is a real result here and will be reported as one: a leaderboard that tops out near the
date-difference reference would be worth publishing, and so would one that clearly beats the Foundation's 0.624.

Nothing here is advice about any real person, and no score means anything about anybody's life."""

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
about a shared child, and which method extracts the most of it. A large purse would attract people optimising a
leaderboard; a small one attracts people who find the question interesting. The Foundation's own score is
published so that beating it is unambiguous, and a negative result — a leaderboard that tops out near the
date-difference reference — will be reported as the real result it would be."""

PAGES = [("abstract", ABSTRACT), ("Description", DESCRIPTION), ("Evaluation", EVALUATION),
         ("data-description", DATA_DESCRIPTION), ("rules", RULES), ("Prizes", PRIZES)]


def call(ep, payload, label="", tries=5):
    for i in range(tries):
        try:
            r = requests.post(B + ep, json=payload, auth=(U, K), timeout=300)
            try:
                body = r.json()
            except Exception:
                body = r.text[:200]
            if r.status_code >= 400 and i < tries - 1 and r.status_code >= 500:
                time.sleep(3 * (i + 1))
                continue
            return r.status_code, body
        except Exception as e:
            if i == tries - 1:
                return None, f"{type(e).__name__} {e}"
            time.sleep(3 * (i + 1))
    return None, "gave up"


def upload(path, kind, comp):
    """Blob upload: ask for a token, PUT the bytes, then hand the token to the creating RPC."""
    from kaggle.api.kaggle_api_extended import KaggleApi
    os.environ["KAGGLE_USERNAME"], os.environ["KAGGLE_KEY"] = U, K
    api = KaggleApi()
    api.authenticate()
    tok = api.competition_data_upload(comp, path) if hasattr(api, "competition_data_upload") else None
    return tok


def main():
    do = os.environ.get("AQ_DO_CREATE") == "1"
    for f in ("train.csv", "test.csv", "sample_submission.csv", "solution.csv"):
        p = os.path.join(DATA, f)
        if not os.path.exists(p):
            raise SystemExit(f"missing {p} — run build_dayday_test.py first")
        print(f"  {os.path.getsize(p)/1e6:6.2f} MB  {f}")
    meta = json.load(open(os.path.join(DATA, "testset.json")))
    print(f"  test set: {meta['rows']:,} rows, {meta['positives']:,} positive, metric {meta['metric']}")

    if not do:
        print("\n  DRY RUN — set AQ_DO_CREATE=1 to create the competition and write its pages")
        for name, body in PAGES:
            print(f"    would write page {name:<18} {len(body):>6,} chars")
        return

    # `privacy: "PUBLIC"` makes this 400 with an EMPTY body — the string is not the enum the server wants and the
    # response names no field. Omitting privacy, numPrizes and reward creates it; the prize wording lives on the
    # Prizes page, which is where an entrant reads it anyway.
    st, b = call("CreateCompetition", {
        "slug": SLUG, "title": TITLE, "briefDescription": BRIEF, "organizationId": ORG_ID})
    already = isinstance(b, dict) and "already taken" in json.dumps(b)
    print(f"\n  CreateCompetition -> {st}  "
          f"{'already exists, continuing' if already else (json.dumps(b)[:150] if isinstance(b, dict) else b)}")

    st, _ = call("UpdateCompetitionSettings", {
        "competitionName": SLUG, "updateMask": "deadline,title,briefDescription",
        "settings": {"competitionName": SLUG, "deadline": DEADLINE, "title": TITLE,
                     "briefDescription": BRIEF}})
    print(f"  deadline + title  -> {st}")

    # The page NAME is a top-level field with an update mask; putting it only inside `page` answers
    # 404 "has no page named ''", which reads as a missing page rather than a malformed request. A fresh
    # competition already carries default pages, so Create answers 409 for those and only new tabs need it.
    for name, body in PAGES:
        st, b = call("UpdateCompetitionPage", {
            "competitionName": SLUG, "pageName": name, "updateMask": "content,isPublished",
            "page": {"name": name, "content": body, "isPublished": True}})
        if st and st >= 400:
            st2, b2 = call("CreateCompetitionPage", {
                "competitionName": SLUG,
                "page": {"name": name, "content": body, "isPublished": True}})
            st = f"{st} then create {st2}"
            b = b2
        print(f"  page {name:<18} {len(body):>6,} chars -> {st}")

    print("\n  RETIRING THE OLD COMPETITION (there is no delete RPC, only supersede)")
    st, _ = call("UpdateCompetitionSettings", {
        "competitionName": OLD_SLUG, "updateMask": "title,briefDescription,disableSubmissions",
        "settings": {"competitionName": OLD_SLUG,
                     "title": "[SUPERSEDED] ArtaMatch two birth dates one shared child",
                     "briefDescription": f"Superseded by {SLUG}, which asks one question with one row per "
                                         f"couple and a metric Kaggle can score. Do not enter this one.",
                     "disableSubmissions": True}})
    print(f"  old competition retitled + submissions disabled -> {st}")

    print("\n  WHAT IS LEFT, AND IT CANNOT BE DONE FROM HERE")
    print("    Set the metric to AUC in the UI: CompetitionSettings has no metric field and neither does")
    print("    CreateCompetition, so the solution upload 500s until a metric exists. Choose")
    print("    'Area Under Receiver Operating Characteristic Curve', then re-run upload_competition_data.py.")


if __name__ == "__main__":
    main()
