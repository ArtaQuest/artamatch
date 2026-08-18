"""dataset_meta_iii.py — dataset-metadata.json for the third edition, numbers read from the CSVs.
Usage: python dataset_meta_iii.py <owner/slug> <dataset-dir> <src-dir>"""
import csv
import json
import sys

ref, d, src = sys.argv[1], sys.argv[2], sys.argv[3]
tr = list(csv.DictReader(open(f"{src}/train.csv"))); te = list(csv.DictReader(open(f"{src}/test.csv")))
both = sum(1 for r in tr if r["lat_dad"] not in ("", "nan") and r["lat_mom"] not in ("", "nan"))
one = sum(1 for r in tr if "0000-00-00" in (r["dob_dad"], r["dob_mom"]))
jan1_tr = sum(1 for r in tr if r["start"][5:] == "01-01"); jan1_te = sum(1 for r in te if r["start"][5:] == "01-01")
desc = f"""# Let's end this loneliness epidemic with astrology.

**Third edition.** His and her birth dates and birthplaces, and the date the relationship began. Did it last thirty
years?

| column | meaning |
|---|---|
| `dob_dad` | the man's date of birth (Wikidata P21 male) |
| `dob_mom` | the woman's date of birth (P21 female) |
| `lat_dad`, `lon_dad` | his place of birth, decimal degrees (empty when Wikidata has none) |
| `lat_mom`, `lon_mom` | her place of birth |
| `start` | the date the relationship began — the wedding date for a marriage — `YYYY-MM-DD`, 1 January where only the year is known |
| `lasted_30_years` | 1 if the relationship lasted thirty years or longer, else 0 |

## The birth time is a convention: 09:00 local

Nobody's birth time is in Wikidata. The first two editions therefore cast every chart at a fixed universal
hour and could not have an ascendant. **With the birthplace known, the fixed hour can be a local one:** the
Foundation's own models cast every chart at **09:00 local time at the birthplace**, converted to UT through the
historical time zone of the coordinates (an 1850 Paris birth is on local mean time, +0:09:21; a 1950 one on
+1:00). That gives each chart an ascendant and twelve houses — the sign that rises at nine in the morning at
that place, whatever the truth was. It is the dataset's convention, stated here; you may use another.

## Sidereal

The Foundation's own models for this edition are **sidereal only** — Jyotiṣa through PyJHora (Lahiri
ayanāṁśa: rāśi and lagna, thirteen divisional charts, pañcāṅga, ṣaḍbala, sarvāṣṭakavarga, doṣas, Aṣṭakūṭa
matching, Vimśottari at the start) and Zǐ Wēi Dǒu Shù through iztro (the twelve palaces at the 巳 double-hour).
Nothing about the data forces that on you.

## The rows

**Marriages only, between a man and a woman** (operator, 2026-08-18: "only allow male x female marriages"):
Wikidata's `P26` alone, and only pairs of one man and one woman from `P21`, ordered dad first / mom second. The
earlier editions also carried unmarried, business and "significant person" pairs and every sex configuration.

`lasted_30_years` is `(end − start) >= 30 years`, the end being a recorded end date or, failing that, the
earlier of the two deaths. **A marriage ended by a death is not automatically a long one.**

**Train** births 1600–1900, **test** births 1901 onward with both partners dead — a temporal split. The test rows
are strict: both dates to the day, both birthplaces present, the start in or before 1996 (a later start cannot
reach thirty years before 2026 and is removed rather than left as a free point). The training rows are
inclusive: {one:,} of {len(tr):,} have one partner absent from Wikidata (`0000-00-00`), dates may be coarse
(`1809-11-00`, `1802-00-00`), and a birthplace may be empty; both places are known in {both:,} training rows.
The start reads `YYYY-01-01` where only its year is known — {100*jan1_tr/len(tr):.0f}% of training starts,
{100*jan1_te/len(te):.0f}% of test starts — and a real 1 January cannot be told from it.

## The bar

With the start known, **each partner's age at the start** is the strongest ordinary predictor in the problem
and owes nothing to any tradition. Read every score against it, not against 0.5. The Foundation publishes its
own sidereal families scored alone on the held-out couples so that beating them is unambiguous.

Built by a public notebook that runs the SPARQL live, so anyone can re-run it and contradict it. Earlier
editions: `artamatch-astrology` (two dates), `artamatch-marriage-year` (two dates and the start).
"""
json.dump({"title": "ArtaMatch: births, birthplaces, wedding date", "id": ref,
           "licenses": [{"name": "CC0-1.0"}],
           "subtitle": "His and her births and birthplaces, and the wedding date. Thirty years?",
           "description": desc}, open(f"{d}/dataset-metadata.json", "w"), indent=1)
print(f"  metadata written for {ref}: {len(tr):,} train / {len(te):,} test")
