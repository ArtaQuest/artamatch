"""dataset_meta_iv.py — dataset-metadata.json for the FOURTH edition (genderless), numbers read from the CSVs.
Usage: python dataset_meta_iv.py <owner/slug> <dataset-dir> <src-dir>"""
import csv
import json
import sys

ref, d, src = sys.argv[1], sys.argv[2], sys.argv[3]
tr = list(csv.DictReader(open(f"{src}/train.csv"))); te = list(csv.DictReader(open(f"{src}/test.csv")))
both = sum(1 for r in tr if r["lat_a"] not in ("", "nan") and r["lat_b"] not in ("", "nan"))
one = sum(1 for r in tr if "0000-00-00" in (r["dob_a"], r["dob_b"]))
jan1_tr = sum(1 for r in tr if r["start"][5:] == "01-01"); jan1_te = sum(1 for r in te if r["start"][5:] == "01-01")
desc = f"""# Let's end this loneliness epidemic with astrology.

**Fourth edition — genderless.** Two people's birth dates and birthplaces and the date their relationship began.
Did it last thirty years? **No sex is read and no order is claimed**: the two partners are `a` and `b`, and
**every pair appears in both orders** — `(a, b, y)` and `(b, a, y)` are both rows, in train and in test — so a
model is symmetric by the data rather than by a column convention. **Every long-term relationship Wikidata
records** is in: marriages (same-sex marriages included, since nothing reads a sex), unmarried partnerships,
business and sporting partnerships, and Wikidata's general "significant person" relation with family pairs
excluded.

| column | meaning |
|---|---|
| `dob_a`, `dob_b` | the two partners' dates of birth, `YYYY-MM-DD` (no meaning attaches to which is which) |
| `lat_a`, `lon_a`, `lat_b`, `lon_b` | their birthplaces, decimal degrees (empty when Wikidata has none) |
| `start` | the date the relationship began — the wedding date for a marriage — `YYYY-MM-DD`, 1 January where only the year is known |
| `lasted_30_years` | 1 if the relationship lasted thirty years or longer, else 0 |

## Both orders, on purpose

{len(tr)//2:,} training pairs are {len(tr):,} rows; {len(te)//2:,} test pairs are {len(te):,} rows (`p000123a` and
`p000123b` are the same pair, the partners exchanged, always on the same public/private side). A submission
that is not even in its two partners is penalised by the metric itself: a model's two scores for a pair should be
the same score. The Foundation's own models are even by construction — every phase DIFFERENCE enters as its
absolute value, |θa − θb|, so each term is an even function of the swap — and averaged over the two orders besides.

## The birth time is a convention: 09:00 local

Nobody's birth time is in Wikidata. With the birthplace known, the Foundation casts every chart at **09:00
local time at the birthplace**, converted to UT through the historical time zone of the coordinates. That gives
each chart an ascendant and twelve houses — the sign rising at nine in the morning there, whatever the truth
was. It is the dataset's convention; you may use another.

## Sidereal

The Foundation's own model for this edition is **ArtaModel IV** — a sidereal (Lahiri) phase model over fourteen
bodies: the absolute synastry angle between the two natal charts, the wedding sky to each partner, each natal
longitude and the wedding sky itself, every difference taken as an absolute value. It is published term by term.
Nothing about the data forces that on you.

## The rows

`lasted_30_years` is `(end − start) >= 30 years`, the end being a recorded end date or, failing that, the
earlier of the two deaths. **A relationship ended by a death is not automatically a long one.**

**Train** births 1600–1900, **test** births 1901 onward with both partners dead — a temporal split. The test rows
are strict: both dates to the day, both birthplaces present, the start in or before 1996 (a later start cannot
reach thirty years before 2026 and is removed rather than left as a free point). The training rows are
inclusive: {one:,} of {len(tr):,} have one partner absent from Wikidata (`0000-00-00`, in either column), dates
may be coarse (`1809-11-00`, `1802-00-00`), and a birthplace may be empty; both places are known in {both:,}
training rows. The start reads `YYYY-01-01` where only its year is known — {100*jan1_tr/len(tr):.0f}% of
training starts, {100*jan1_te/len(te):.0f}% of test starts — and a real 1 January cannot be told from it.

## The bar

With the start known, **each partner's age at the start** is the strongest ordinary predictor in the problem
and owes nothing to any tradition. Read every score against it, not against 0.5.

Built by a public notebook that runs the SPARQL live, so anyone can re-run it and contradict it. Earlier
editions: `artamatch-astrology` (two dates), `artamatch-marriage-year` (two dates and the start),
`artamatch-sidereal` (places, man/woman marriages only).
"""
json.dump({"title": "ArtaMatch IV: genderless, any long-term pair", "id": ref,
           "licenses": [{"name": "CC0-1.0"}],
           "subtitle": "Two births, two places, the start date; every pair in both orders. Thirty years?",
           "description": desc}, open(f"{d}/dataset-metadata.json", "w"), indent=1)
print(f"  metadata written for {ref}: {len(tr):,} train / {len(te):,} test")
