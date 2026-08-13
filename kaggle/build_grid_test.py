"""
build_grid_test.py — turn the held-out couples into the 15-cell precision test set the metric needs.

THE METRIC (operator, 2026-08-13) is the MEAN OF 15 AUCs. Each partner's birth date is degraded independently
over four levels — full date, month only, year only, absent — giving a 4x4 grid, and the cell where BOTH are
absent is excluded from the score. So the test set is one row per (couple, cell) and a submission predicts all
fifteen.

    17,280 held-out couples x 15 cells = 259,200 rows

WHY absent x absent IS EXCLUDED and not merely down-weighted: with neither date there is no input. Every row
in that cell would carry the same fixed placeholder, so no model could separate them and the cell would
contribute a constant near 0.5 to every competitor's average — moving the scale without ranking anyone. It is
not a hard cell; it is not a question.

THE GRID'S AXES ARE THE MAN AND THE WOMAN, and the column order is what carries that. The dataset's columns are
`dob_man` then `dob_woman`, assigned from Wikidata's P21 rather than inherited from the pair's Q-number
ordering — an earlier build ordered them by QID, which made "first column is the man" false for about half the
rows and would have transposed half of this grid.

WHY POOLED AUC IS NOT THIS METRIC, and why the cell column exists. A single AUC over all 259,200 rows is not
the mean of fifteen per-cell AUCs: pooling compares rows across cells, so an easy cell's high scores outrank a
hard cell's low ones and the number drifts towards a between-cell comparison. The `cell` column is in the
solution file so the score can be computed per cell and then averaged, which is what was asked for.

WHAT 'absent' MEANS for the one partner who has it. There is no way to express a missing date in a table of two
dates, so the substitute is the other partner's date AS THE MODEL SEES IT — the coarsening is applied first and
the substitution second. Doing it the other way round would hand the absent partner a full date copied from a
partner whose own record had already been reduced to a month, putting precision in the row that exists nowhere
in its inputs.

Usage: ~/.artamatch-venv/bin/python build_grid_test.py /tmp/aqscrape2 /tmp/aqgrid
"""
import csv
import json
import os
import sys

import numpy as np

SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/aqscrape"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/aqgrid"
NO_DATE = "1900-01-01"
LEVELS = ["full", "month", "year", "absent"]


def month_only(d):
    return d[:8] + "01"


def year_only(d):
    return d[:4] + "-01-01"


COARSEN = {"full": None, "month": month_only, "year": year_only, "absent": "absent"}


def degrade(dob_a, dob_b, la, lb):
    a, b = dob_a, dob_b
    if COARSEN[la] not in (None, "absent"):
        a = COARSEN[la](a)
    if COARSEN[lb] not in (None, "absent"):
        b = COARSEN[lb](b)
    if COARSEN[la] == "absent" and COARSEN[lb] == "absent":
        a = b = NO_DATE
    elif COARSEN[la] == "absent":
        a = b
    elif COARSEN[lb] == "absent":
        b = a
    return a, b


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(SRC, "test.csv"))))
    need = {"id", "dob_man", "dob_woman"}
    if not need <= set(rows[0]):
        raise SystemExit(f"test.csv has {sorted(rows[0])} — this grid needs {sorted(need)}, because the axes "
                         f"are the man and the woman and the column order is what says which is which")
    sol_in = {r["id"]: r["parents_together"] for r in csv.DictReader(open(os.path.join(SRC, "solution.csv")))}
    print(f"  {len(rows):,} held-out couples")

    test_p = os.path.join(OUT, "test.csv")
    sol_p = os.path.join(OUT, "solution.csv")
    samp_p = os.path.join(OUT, "sample_submission.csv")
    rng = np.random.default_rng(20260813)
    n = 0
    with open(test_p, "w", newline="") as ft, open(sol_p, "w", newline="") as fs, \
            open(samp_p, "w", newline="") as fp:
        wt, ws, wp = csv.writer(ft), csv.writer(fs), csv.writer(fp)
        wt.writerow(["id", "dob_man", "dob_woman"])
        ws.writerow(["id", "parents_together", "cell", "Usage"])
        wp.writerow(["id", "parents_together"])
        # Public/Private is assigned per COUPLE, not per row, so a couple never appears on both halves of the
        # leaderboard — otherwise its 16 cells would be split and the private score would leak from the public.
        usage = {r["id"]: ("Public" if rng.random() < 0.30 else "Private") for r in rows}
        for r in rows:
            for la in LEVELS:
                for lb in LEVELS:
                    if la == "absent" and lb == "absent":
                        continue                      # no input at all: excluded from the metric
                    a, b = degrade(r["dob_man"], r["dob_woman"], la, lb)
                    rid = f"{r['id']}_{la}_{lb}"
                    wt.writerow([rid, a, b])
                    ws.writerow([rid, sol_in[r["id"]], f"{la}|{lb}", usage[r["id"]]])
                    wp.writerow([rid, 0.5])
                    n += 1
    print(f"  wrote {n:,} rows ({len(rows):,} couples x 15 cells)")
    for p in (test_p, sol_p, samp_p):
        print(f"    {os.path.getsize(p)/1e6:6.2f} MB  {os.path.basename(p)}")

    # A couple must never straddle the public/private split, and every cell must be present exactly once.
    seen = {}
    for r in csv.DictReader(open(sol_p)):
        cid = r["id"].rsplit("_", 2)[0]
        seen.setdefault(cid, set()).add(r["cell"])
        assert usage[cid] == r["Usage"], f"couple {cid} has mixed Usage"
    bad = [c for c, s in seen.items() if len(s) != 15]
    assert not bad, f"{len(bad)} couples do not have all 15 cells"
    assert not any("absent|absent" in s for s in seen.values()), "absent|absent leaked into the test set"
    pub = sum(1 for v in usage.values() if v == "Public")
    print(f"  checked: every couple has all 15 cells, none straddles the split "
          f"({pub:,} public / {len(usage)-pub:,} private couples)")
    json.dump({"couples": len(rows), "cells": 15, "rows": n,
               "levels": LEVELS, "grid": "man x woman (dob_man, dob_woman)",
               "metric": "mean of the 15 per-cell AUCs; absent x absent excluded",
               "excluded": "absent|absent — with neither date there is no input, so the cell cannot rank "
                           "anyone and would only shift every competitor's average by a constant"},
              open(os.path.join(OUT, "grid.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
