"""
competition_pages_iv.py — the FOURTH edition's pages (genderless; every pair in both orders; any long-term
relationship), numbers read from the build and from research/sidereal/artamodel_iv.py's artamodel_iv.json.
Usage: AQ_COMPETITION=artamatch-genderless AQ_DO_WRITE=1 python competition_pages_iv.py /tmp/aq4comp /tmp/aq4sub
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import competition_pages as P1                                       # noqa: E402
_P1_PAGES = P1.pages                # captured BEFORE the override below (else recursion)

SLUG = os.environ.get("AQ_COMPETITION", "artamatch-genderless")
TITLE = "ArtaMatch Astrology IV: genderless, any relationship"
BRIEF = ("Two births, two places, the start date, every pair in both orders: did the relationship last thirty years? "
         "Genderless; any long-term pair.")
assert len(TITLE) <= 60 and len(BRIEF) <= 140, (len(TITLE), len(BRIEF))
P1.SLUG, P1.TITLE, P1.BRIEF = SLUG, TITLE, BRIEF


def numbers(comp, sub):
    sol = list(csv.DictReader(open(os.path.join(comp, "solution.csv"))))
    lab = [c for c in sol[0] if c not in ("id", "Usage")][0]
    pub = [int(r[lab]) for r in sol if r["Usage"] == "Public"]; prv = [int(r[lab]) for r in sol if r["Usage"] == "Private"]
    tr = list(csv.DictReader(open(os.path.join(comp, "train.csv")))); te = list(csv.DictReader(open(os.path.join(comp, "test.csv"))))
    R = json.load(open(os.path.join(sub, "artamodel_iv.json")))
    return {"label": lab, "n_train": len(tr), "n_test": len(sol), "pub_n": len(pub), "prv_n": len(prv),
            "pub_pos": 100 * sum(pub) / len(pub), "prv_pos": 100 * sum(prv) / len(prv),
            "one_sided": sum(1 for r in tr if "0000-00-00" in (r["dob_a"], r["dob_b"])),
            "both_places": sum(1 for r in tr if r["lat_a"] not in ("", "nan") and r["lat_b"] not in ("", "nan")),
            "jan1_tr": 100 * sum(1 for r in tr if r["start"][5:] == "01-01") / len(tr),
            "jan1_te": 100 * sum(1 for r in te if r["start"][5:] == "01-01") / len(te),
            "plain": R["plain"]["held"], "arta": R["artamodel"]["held"], "arta_cell": R["artamodel"]["age_cell_matched"],
            "plain_cell": R["plain"]["age_cell_matched"], "ens": R["ensemble"]["held"], "phasors": R["artamodel"]["phasors_used"],
            "n_full": R["n_full_chart_train_rows"], "sample_id": sol[0]["id"], "era": float("nan"), "gap": float("nan")}


def pages(N):
    lab = N["label"]
    ABSTRACT = f"""# Let's end this loneliness epidemic with astrology.

**The fourth ArtaMatch competition — genderless.** Two people's birth dates and birthplaces and the date their
relationship began. Predict whether it lasted thirty years. **No sex is read and no order is claimed**: the
partners are `a` and `b`, and **every pair is in the data in both orders**, in train and in test, so the metric
itself rewards a model that is even in its two partners. **Every long-term relationship** Wikidata records is in
— marriages of every kind, unmarried partnerships, business and sporting partnerships, "significant person" pairs
with family excluded. Everyone in the data is dead, so every relationship has ended. Scored **across time**:
train on people born 1600–1900, predict the ones born after. Plain AUC.

The Foundation's own model, **ArtaModel IV**, is a sidereal phase model in which every phase difference enters
as an absolute value — an even function of the swap by construction — and it is published term by term. The bar
is not astrology: the two partners' **ages at the start** score **{N['plain']:.4f}** held out; ArtaModel IV scores
{N['arta']:.4f}; their equal-weight average {N['ens']:.4f}.

Prizes: 1,000 / 500 / 100 ArtaCoin. See the Prizes tab for what that is, stated plainly.
"""
    DESCRIPTION = f"""## Let's end this loneliness epidemic with astrology

An open search for the best astrology there is, measured on people who really lived, against baselines that are
not allowed to know astrology.

## The question

Three dates and two places. `dob_a` and `dob_b` are the two partners' births — **which is which means nothing**;
`lat_*`/`lon_*` are the birthplaces; `start` is when the relationship began — the wedding date, for a marriage.
Predict the probability that it lasted **thirty years or longer**.

## Genderless, and both orders

This edition reads no sex and claims no order. Every pair is two rows, the partners exchanged — `p000123a` and
`p000123b` in the test set are the same pair, always on the same public/private side. A model that gives a pair
two different scores is penalised by the metric itself rather than by a rule; the simplest fix is to score both
orders and average. The Foundation's ArtaModel IV is even by construction: every phase difference is its absolute
value, |θa − θb|, so each term is an even function of the swap.

## Every long-term relationship

Wikidata's `P26` (spouse — same-sex marriages included, since nothing reads a sex), `P451` (unmarried partner),
`P1327` (business or sport partner) and `P3342` (significant person, with every pair that also carries a family
link excluded). The third edition kept man-woman marriages only; this one keeps every pair two people chose.

## The birth time is a convention: 09:00 local

Wikidata records no birth times. With the birthplace known the fixed hour can be a **local** one: 09:00 at the
place, converted to UT through the historical time zone of the coordinates. Every chart then has an ascendant and
twelve houses — the sign rising at nine in the morning there, whatever the truth was. It is a convention, stated.

## Where the label comes from

As a Wikipedia infobox reads a marriage — *"m. 1903; div. 1919"*. A recorded end date ends it; otherwise the
earlier of the two deaths does. `{lab}` is `(end − start) ≥ 30 years`. **A relationship ended by a death is not
automatically a long one.**

## The split, the ceiling, and the placeholders

**Temporal**: fit on pairs born up to 1900, score on pairs born after, nobody in both. Every held-out pair is
dead by 2026, so a relationship begun after 1996 cannot reach thirty years — such rows are removed from the test
set rather than left as free points. `start` reads `YYYY-01-01` where only its year is known —
{N['jan1_tr']:.0f}% of training starts, {N['jan1_te']:.0f}% of test starts — and a real 1 January cannot be told
from it. A birthplace may be empty in the training half ({N['both_places']:,} of {N['n_train']:,} rows have both);
it is never empty in the test half.

## The Foundation's own entry: ArtaModel IV, term by term

    y = | b + Σᵢ aᵢ·e^{{i|θ1ᵢ − θ2ᵢ|}} + t1ᵢ·e^{{i|θtᵢ − θ1ᵢ|}} + t2ᵢ·e^{{i|θtᵢ − θ2ᵢ|}} + n1ᵢ·e^{{iθ1ᵢ}} + n2ᵢ·e^{{iθ2ᵢ}} + tnᵢ·e^{{iθtᵢ}} |²

over fourteen sidereal (Lahiri) bodies: the absolute synastry angle between the two charts, the wedding sky to
each partner, each natal longitude, the wedding sky itself; a term exists only when both its phases are known.
Fitted as a boosted sum of single-phasor fields on the {N['n_full']:,} training rows with both charts complete,
train only; the phasors it keeps: {', '.join(N['phasors'])}. Held out **{N['arta']:.4f}**; age-cell-matched
(within 3-year cells of the two ages) {N['arta_cell']:.4f} — read that second number as what is left once the
ages are held flat. The plain columns score {N['plain']:.4f} ({N['plain_cell']:.4f} matched). Code and weights
are public. The Foundation is publishing that whichever way it reads.
"""
    EVALUATION = f"""## Metric

**Area under the ROC curve** between your predicted probability and the observed `{lab}`. Only the ranking
matters.

## Submission format

```
id,{lab}
{N['sample_id']},0.63
```

One row per id in `test.csv` — both orders of every pair; any real number, only its order is used.
`sample_submission.csv` predicts 0.5.

## The split

{N['pub_n']:,} test rows form the public leaderboard and {N['prv_n']:,} the private one, drawn at random per
PAIR (both orders of a pair on the same side); public {N['pub_pos']:.2f}% positive, private {N['prv_pos']:.2f}%.

## What a good score looks like

| held out | AUC |
|---|---|
| Random, or the sample submission | 0.500 |
| **The plain columns: the two ages at the start, their gap, the start year (no astrology)** | **{N['plain']:.4f}** |
| ArtaModel IV (the Foundation's even sidereal phase model) | {N['arta']:.4f} |
| Equal-weight rank average of the two | {N['ens']:.4f} |

**Read the plain columns as the bar.** They know nothing but when each partner was born and when the
relationship began.
"""
    DATA = f"""## Files

| file | rows | what |
|---|---|---|
| `train.csv` | {N['n_train']:,} | `dob_a`, `dob_b`, `lat_a`, `lon_a`, `lat_b`, `lon_b`, `start`, `{lab}` — every pair in both orders |
| `test.csv` | {N['n_test']:,} | `id` + the seven inputs — every pair in both orders (`p<n>a`, `p<n>b`) |
| `sample_submission.csv` | {N['n_test']:,} | `id`, `{lab}` = 0.5 |

## The columns

* `dob_a`, `dob_b` — dates of birth, `YYYY-MM-DD`; which partner is `a` carries no meaning. In the training half
  a date may be known only to the month (`1809-11-00`) or the year (`1802-00-00`), and one partner may be absent
  entirely (`0000-00-00`, in either column). {N['one_sided']:,} training rows are one-sided.
* `lat_a`, `lon_a`, `lat_b`, `lon_b` — birthplaces in decimal degrees, from Wikidata's place-of-birth item;
  empty in the training half when unknown, always present in the test half.
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
`artaquest-foundation/artamatch-genderless`, CC0. Earlier editions: `artamatch-astrology` (two dates),
`artamatch-marriage-year` (two dates and the start), `artamatch-sidereal` (places; man-woman marriages only).
"""
    base = {**N, "n_trad": 0, "top": [], "beat_era": 0, "gap": 0, "era": 0, "n_base": 0, "ens": N["ens"], "coarse": 0, "tr_pos": 0, "te_pos": 0, "n_heldout": N["n_test"]}
    RULES = _P1_PAGES(base)[4][1].replace("Predict from the two dates.", "Predict from the dates and the places.").replace(
        "How much do two birth dates carry about how long a\nrelationship lasts",
        "How much do two birth dates, two birthplaces and a start date carry about how long a\nrelationship lasts").replace(
        "a leaderboard that tops out at the era rule\nwould be worth publishing", "a leaderboard that tops out at the plain columns\nwould be worth publishing")
    PRIZES = _P1_PAGES(base)[5][1].replace("a leaderboard\nthat tops out at the era rule", "a leaderboard\nthat tops out at the plain columns").replace(
        "how much two birth dates actually carry", "how much two birth dates, two birthplaces and a start date actually carry")
    return [("abstract", ABSTRACT), ("Description", DESCRIPTION), ("Evaluation", EVALUATION), ("data-description", DATA), ("rules", RULES), ("Prizes", PRIZES)]


P1.numbers, P1.pages = numbers, pages


def main():
    comp = sys.argv[1] if len(sys.argv) > 1 else "/tmp/aq4comp"; sub = sys.argv[2] if len(sys.argv) > 2 else "/tmp/aq4sub"
    N = numbers(comp, sub); P = pages(N)
    print(f"  numbers from the build: train {N['n_train']:,} · test {N['n_test']:,} · plain {N['plain']:.4f} · ArtaModel IV {N['arta']:.4f} · ensemble {N['ens']:.4f}")
    for name, body in P:
        assert "parent" not in body.lower() and "child" not in body.lower(), f"{name} still says parent/child"
        import re
        for w in ("dad", "mom", "man", "woman", "his", "her", "him", "wife", "husband"):
            # the one permitted mention is the description of the THIRD edition ("man-woman marriages only")
            assert not re.search(rf"\b{w}\b", body.lower().replace("man-woman", "")) or name in ("rules", "Prizes"), f"{name} still says {w!r}"
    if os.environ.get("AQ_DO_WRITE") != "1":
        print("\n  DRY RUN — set AQ_DO_WRITE=1 to write the pages")
        for name, body in P:
            print(f"    would write {name:<18} {len(body):>6,} chars")
        return
    st, _ = P1.call("UpdateCompetitionSettings", {"competitionName": SLUG, "updateMask": "title,briefDescription",
                                                    "settings": {"competitionName": SLUG, "title": TITLE, "briefDescription": BRIEF}})
    print(f"  title + brief -> {st}")
    for name, body in P:
        st, b = P1.call("UpdateCompetitionPage", {"competitionName": SLUG, "pageName": name, "updateMask": "content,isPublished",
                                                    "page": {"name": name, "content": body, "isPublished": True}})
        if st and st >= 400:
            st2, b = P1.call("CreateCompetitionPage", {"competitionName": SLUG, "page": {"name": name, "content": body, "isPublished": True}})
            st = f"{st} then create {st2}"
        print(f"  page {name:<18} {len(body):>6,} chars -> {st}")


if __name__ == "__main__":
    main()
