"""
build_grid_test.py — turn the held-out couples into the precision test set the metric needs.

THE METRIC is the row-count-weighted MEAN OF THE PER-CELL AUCs. Each partner's birth date is degraded
independently over four levels — full date, month only, year only, absent — giving a 4x4 grid, and TWO of the
sixteen combinations are excluded. `dates.py` owns that list and the reasons; this file imports it rather than
restating it, because a grid definition copied into six files is a grid definition that will drift.

The test set is one row per (couple, cell), so a submission predicts every surviving cell for every couple.

WHY absent x absent IS EXCLUDED and not merely down-weighted: with neither date there is no input. Every row
in that cell carries the same placeholder, so no model can separate them and the cell would contribute a
constant near 0.5 to every competitor's average — moving the scale without ranking anyone. It is not a hard
cell; it is not a question.

WHY month x month IS EXCLUDED: it is a case the records essentially never present. Of 107,698 couples only 859
men and 1,017 women are known to the month, which leaves 18 real pairs where both are — and an AUC over 18 rows
is noise, as those 18 demonstrated by scoring 0.8615 against 0.6201 for the 16,675-row day-by-day group.
Simulating it across every held-out couple would average in a question the data cannot answer.

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
NO_DATE = "1900-00-00"   # no date at all: not even a year is claimed
LEVELS = ["full", "month", "year", "absent"]


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dates as D

# Coarsening lives in dates.py so this file and the training data cannot disagree about what a month-precision
# date looks like. `00` marks the unknown component: `1850-03-00` is a month, `1850-00-00` a year. Coarsening is
# idempotent, so a row that only ever had a year is identical to one coarsened down to a year — which is the
# property that makes the `year|year` cell measure ranking rather than documentation depth.
COARSEN = {"full": None, "month": "month", "year": "year", "absent": "absent"}
LEVELS = D.LEVELS


def degrade(dob_a, dob_b, la, lb):
    a, b = dob_a, dob_b
    if COARSEN[la] not in (None, "absent"):
        a = D.coarsen(a, COARSEN[la])
    if COARSEN[lb] not in (None, "absent"):
        b = D.coarsen(b, COARSEN[lb])
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
                    if f"{la}|{lb}" in D.EXCLUDED_CELLS:
                        continue          # not part of the metric; dates.py says which and why
                    a, b = degrade(r["dob_man"], r["dob_woman"], la, lb)
                    rid = f"{r['id']}_{la}_{lb}"
                    wt.writerow([rid, a, b])
                    ws.writerow([rid, sol_in[r["id"]], f"{la}|{lb}", usage[r["id"]]])
                    wp.writerow([rid, 0.5])
                    n += 1
    print(f"  wrote {n:,} rows ({len(rows):,} couples x {D.N_CELLS} cells)")
    for p in (test_p, sol_p, samp_p):
        print(f"    {os.path.getsize(p)/1e6:6.2f} MB  {os.path.basename(p)}")

    # A couple must never straddle the public/private split, and every cell must be present exactly once.
    seen = {}
    for r in csv.DictReader(open(sol_p)):
        cid = r["id"].rsplit("_", 2)[0]
        seen.setdefault(cid, set()).add(r["cell"])
        assert usage[cid] == r["Usage"], f"couple {cid} has mixed Usage"
    bad = [c for c, s in seen.items() if len(s) != D.N_CELLS]
    assert not bad, f"{len(bad)} couples do not have all {D.N_CELLS} cells"
    leaked = {c for s in seen.values() for c in s} & D.EXCLUDED_CELLS
    assert not leaked, f"excluded cells leaked into the test set: {sorted(leaked)}"
    pub = sum(1 for v in usage.values() if v == "Public")
    print(f"  checked: every couple has all {D.N_CELLS} cells, none straddles the split "
          f"({pub:,} public / {len(usage)-pub:,} private couples)")
    json.dump({"couples": len(rows), "cells": D.N_CELLS, "rows": n,
               "levels": LEVELS, "grid": "man x woman (dob_man, dob_woman)",
               "cell_list": list(D.CELLS),
               "metric": f"row-count-weighted mean of the {D.N_CELLS} per-cell AUCs",
               "excluded": sorted(D.EXCLUDED_CELLS)},
              open(os.path.join(OUT, "grid.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
