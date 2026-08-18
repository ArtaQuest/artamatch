"""
competition_pages_iii.py — the six pages of the THIRD-EDITION competition (birthplaces, 09:00 local, sidereal),
numbers READ from the build (the CSVs) and from research/sidereal's ranking, never typed.

Reuses competition_pages.py's plumbing (call, the page-writing loop) with its own numbers() and pages().
Usage: AQ_COMPETITION=artamatch-sidereal AQ_DO_WRITE=1 python competition_pages_iii.py /tmp/aq3comp /tmp/aq3feat
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import competition_pages as P1                                       # noqa: E402
_P1_PAGES = P1.pages                # the original, captured BEFORE it is overridden below (else recursion)

SLUG = os.environ.get("AQ_COMPETITION", "artamatch-sidereal")
TITLE = "ArtaMatch Astrology III: sidereal, place and date"
BRIEF = ("Two birth dates, two birthplaces and the date it began: did the relationship last thirty years? "
         "Sidereal charts at 09:00 local.")
assert len(TITLE) <= 60 and len(BRIEF) <= 140, (len(TITLE), len(BRIEF))
P1.SLUG, P1.TITLE, P1.BRIEF = SLUG, TITLE, BRIEF


def numbers(comp, feat):
    sol = list(csv.DictReader(open(os.path.join(comp, "solution.csv"))))
    lab = [c for c in sol[0] if c not in ("id", "Usage")][0]
    pub = [int(r[lab]) for r in sol if r["Usage"] == "Public"]; prv = [int(r[lab]) for r in sol if r["Usage"] == "Private"]
    tr = list(csv.DictReader(open(os.path.join(comp, "train.csv")))); te = list(csv.DictReader(open(os.path.join(comp, "test.csv"))))
    rk = json.load(open(os.path.join(feat, "sidereal_ranking.json")))
    fams = sorted(rk["families"], key=lambda r: -r["held"])
    plain = next((r for r in fams if r["family"] == "plain"), None)
    return {"label": lab, "n_train": len(tr), "n_test": len(sol), "pub_n": len(pub), "prv_n": len(prv),
            "pub_pos": 100 * sum(pub) / len(pub), "prv_pos": 100 * sum(prv) / len(prv),
            "one_sided": sum(1 for r in tr if "0000-00-00" in (r["dob_dad"], r["dob_mom"])),
            "both_places": sum(1 for r in tr if r["lat_dad"] not in ("", "nan") and r["lat_mom"] not in ("", "nan")),
            "jan1_tr": 100 * sum(1 for r in tr if r["start"][5:] == "01-01") / len(tr),
            "jan1_te": 100 * sum(1 for r in te if r["start"][5:] == "01-01") / len(te),
            "fams": fams, "plain": plain["held"] if plain else float("nan"),
            "members": rk["members"], "ens": rk["ensemble"], "n_features": rk["n_features"],
            "sample_id": sol[0]["id"],
            # keys competition_pages.main() prints for the first edition; not meaningful here
            "era": float("nan"), "gap": float("nan")}


def pages(N):
    lab = N["label"]
    fam_rows = "\n".join(f"| {r['family']} | {r['n_features']} | {r['held']:.4f} |" for r in N["fams"])
    mem_rows = "\n".join(f"| {k} | {v:.4f} |" for k, v in N["members"].items())
    ABSTRACT = f"""# Let's end this loneliness epidemic with astrology.

**The third ArtaMatch competition.** Two birth dates, two birthplaces, and the date the relationship began.
Predict whether it lasted thirty years. Any relationship two people chose counts; everyone in the data is dead,
so every relationship has ended. Scored **across time**: train on couples born 1600–1900, predict the ones born
after. Plain AUC.

**What is new:** the birthplace. Nobody's birth time is recorded, so the Foundation casts every chart at
**09:00 local time at the birthplace** — the first edition of this project in which a chart has an ascendant and
houses. The Foundation's own models are **sidereal only**: Jyotiṣa through PyJHora and Zǐ Wēi Dǒu Shù through
iztro, every family published scored alone. The bar is the same as last time and it is not astrology: the two
partners' **ages at the start**, which score **{N['plain']:.4f}** held out.

Prizes: 1,000 / 500 / 100 ArtaCoin. See the Prizes tab for what that is, stated plainly.
"""
    DESCRIPTION = f"""## Let's end this loneliness epidemic with astrology

An open search for the best astrology there is, measured on people who really lived, against baselines that are
not allowed to know astrology.

## The question

Three dates and two places. `dob_dad` and `dob_mom` are his and her births — this edition orders by sex, from Wikidata's P21, and
keeps only pairs of one man and one woman; `lat_*`/`lon_*` are the birthplaces; `start` is when the relationship
began — the wedding date, for a marriage. Predict the probability that it lasted **thirty years or longer**.

A relationship is anything two people chose: a marriage (`P26`), an unmarried partnership (`P451`), a business
or sporting partnership (`P1327`), or Wikidata's "significant person" relation with every family pair excluded
(`P3342`).

## The birth time is a convention: 09:00 local

Wikidata records no birth times. The first two editions cast every chart at one universal hour and had no
ascendant. With the birthplace known the fixed hour can be a **local** one: 09:00 at the place, converted to UT
through the historical time zone of the coordinates (an 1850 Paris birth is on local mean time, +0:09:21; a 1950
one is on +1:00). Every chart then has an ascendant and twelve houses — the sign rising at nine in the morning
there, whatever the truth was. It is a convention, stated. You may use another; the data does not force it.

## Sidereal, and why the Foundation's models are only that

This edition's models are Jyotiṣa (Lahiri ayanāṁśa) and Zǐ Wēi Dǒu Shù, and nothing tropical. That is the
Foundation's choice for its own entry, not a rule: bring any tradition.

## Where the label comes from

As a Wikipedia infobox reads a marriage — *"m. 1903; div. 1919"*. A recorded end date ends it; otherwise the
earlier of the two deaths does. `{lab}` is `(end − start) ≥ 30 years`. **A relationship ended by a death is not
automatically a long one.**

## The split, the ceiling, and the placeholders

**Temporal**: fit on couples born up to 1900, score on couples born after, nobody in both. Every held-out
couple is dead by 2026, so a relationship begun after 1996 cannot reach thirty years — such rows are removed
from the test set rather than left as free points; the ceiling still bites softly before that, and the training
half (all born by 1900) never sees it. `start` reads `YYYY-01-01` where only its year is known —
{N['jan1_tr']:.0f}% of training starts, {N['jan1_te']:.0f}% of test starts — and a real 1 January cannot be told
from it. A birthplace may be empty in the training half ({N['both_places']:,} of {N['n_train']:,} rows have both);
it is never empty in the test half.

## The Foundation's own entry, and every family alone

{N['n_features']:,} sidereal features, each family scored ALONE on the {N['n_test']:,} held-out couples with a
small boosted model whose hyper-parameters were fixed in advance, and a pre-registered equal-weight pool as the
entry. Nothing here was chosen against the held-out labels.

| family, alone | features | held-out AUC |
|---|---|---|
{fam_rows}

| pool member | held-out AUC |
|---|---|
{mem_rows}
| **equal-weight rank average** | **{N['ens']:.4f}** |

The Foundation is publishing that whichever way it reads.
"""
    EVALUATION = f"""## Metric

**Area under the ROC curve** between your predicted probability and the observed `{lab}`. Only the ranking
matters.

## Submission format

```
id,{lab}
{N['sample_id']},0.63
```

One row per id in `test.csv`; any real number, only its order is used. `sample_submission.csv` predicts 0.5.

## The split

{N['pub_n']:,} test rows form the public leaderboard and {N['prv_n']:,} the private one, drawn at random per
couple; public {N['pub_pos']:.2f}% positive, private {N['prv_pos']:.2f}%.

## What a good score looks like

| held out | AUC |
|---|---|
| Random, or the sample submission | 0.500 |
| **The plain columns: ages at the start, the gap, the start year (no astrology)** | **{N['plain']:.4f}** |
| The Foundation's sidereal pool | {N['ens']:.4f} |

**Read the plain columns as the bar.** They know nothing but when each partner was born and when the
relationship began.
"""
    DATA = f"""## Files

| file | rows | what |
|---|---|---|
| `train.csv` | {N['n_train']:,} | `dob_dad`, `dob_mom`, `lat_dad`, `lon_dad`, `lat_mom`, `lon_mom`, `start`, `{lab}` |
| `test.csv` | {N['n_test']:,} | `id` + the seven inputs |
| `sample_submission.csv` | {N['n_test']:,} | `id`, `{lab}` = 0.5 |

## The columns

* `dob_dad`, `dob_mom` — dates of birth, `YYYY-MM-DD`; in the training half a date may be known only to
  the month (`1809-11-00`) or the year (`1802-00-00`), and one partner may be absent entirely (`0000-00-00`, in
  either column). {N['one_sided']:,} training rows are one-sided.
* `lat_dad`, `lon_dad`, `lat_mom`, `lon_mom` — birthplaces in decimal degrees, from Wikidata's
  place-of-birth item; empty in the training half when unknown, always present in the test half.
* `start` — the date the relationship began; `YYYY-01-01` when only the year is known.
* `{lab}` — 1 if the relationship lasted thirty years or longer, else 0.

**The test rows are strict**: both dates to the day, both places present, both partners dead, later birth after
1900, start in or before 1996.

## Casting a chart at 09:00 local

Take the birthplace's time zone (for example `timezonefinder` → `zoneinfo`; the tables carry the local-mean-time
era), form 09:00 local on the birth date, convert to UT, cast. The Foundation's code for this is public.

## Two traps in the dates, both handled

**1 January is a placeholder** among births (excluded from the test half at day precision, kept in training as
noise) and among starts (published as such — see above). **Every date is proleptic Gregorian.**

## Provenance

Built by a public notebook that runs the SPARQL live against Wikidata. The dataset is
`artaquest-foundation/artamatch-sidereal`, CC0. Earlier editions: `artamatch-astrology` (two dates),
`artamatch-marriage-year` (two dates and the start).
"""
    RULES = _P1_PAGES({**N, "n_trad": 0, "top": [], "beat_era": 0, "gap": 0, "era": 0, "n_base": 0, "ens": N["ens"],
                      "coarse": 0, "tr_pos": 0, "te_pos": 0, "n_heldout": N["n_test"]})[4][1]
    RULES = RULES.replace("Predict from the two dates.", "Predict from the dates and the places.").replace(
        "How much do two birth dates carry about how long a\nrelationship lasts",
        "How much do two birth dates, two birthplaces and a start date carry about how long a\nrelationship lasts").replace(
        "a leaderboard that tops out at the era rule\nwould be worth publishing",
        "a leaderboard that tops out at the plain columns\nwould be worth publishing")
    PRIZES = _P1_PAGES({**N, "n_trad": 0, "top": [], "beat_era": 0, "gap": 0, "era": 0, "n_base": 0, "ens": N["ens"],
                       "coarse": 0, "tr_pos": 0, "te_pos": 0, "n_heldout": N["n_test"]})[5][1].replace(
        "a leaderboard\nthat tops out at the era rule", "a leaderboard\nthat tops out at the plain columns").replace(
        "how much two birth dates actually carry", "how much two birth dates, two birthplaces and a start date actually carry")
    return [("abstract", ABSTRACT), ("Description", DESCRIPTION), ("Evaluation", EVALUATION),
            ("data-description", DATA), ("rules", RULES), ("Prizes", PRIZES)]


P1.numbers, P1.pages = numbers, pages
if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.argv = [sys.argv[0], "/tmp/aq3comp", "/tmp/aq3feat"]
    P1.main()
