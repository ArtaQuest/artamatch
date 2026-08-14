"""
build_dayday_test.py — the competition test set, simplified to one row per couple.

WHY THIS REPLACES THE 14-CELL GRID. The grid asked the same 25,405 couples fourteen times over, once per
combination of degraded date precision, and scored the row-count-weighted mean of the fourteen AUCs. It measured
something real — how gracefully a model degrades when a date is vague — but it cost 355,502 rows to say it, every
couple's label appeared fourteen times, and the metric it produced is not one Kaggle can score: there is no
grouped-mean-AUC among the built-in metrics and no API field to supply one.

One row per couple, both dates known to the day, scored by plain AUC. That is a metric Kaggle has, a submission
a person can eyeball, and a target with a single obvious meaning: rank the couples who had a child together
above the couples who did not.

WHAT IS DROPPED AND WHAT THAT COSTS. Couples where either date is known only to the month or the year leave the
test set entirely — about a third of the held-out half. The measurement therefore says nothing about robustness
to missing dates, which the grid did say something about. That is a deliberate trade: the robustness question is
still answered by the project's own page, which keeps the full grid, while the competition asks the single
question a leaderboard can rank people on.

THE SPLIT IS UNCHANGED. These couples are the held-out side of a person-group split — connected components of
the partnership graph — so nobody in this file appears in train.csv, and they are declared partnerships only,
never pairs discovered through a child.

Usage: ~/.artamatch-venv/bin/python build_dayday_test.py /tmp/aqscrape3 /tmp/aqcomp
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dates as D          # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/aqscrape3"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/aqcomp"
PUBLIC_FRACTION = 0.30


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(SRC, "test.csv"))))
    sol_in = {r["id"]: r["parents_together"]
              for r in csv.DictReader(open(os.path.join(SRC, "solution.csv")))}
    print(f"  {len(rows):,} held-out couples in the source")

    keep, dropped = [], {"man": 0, "woman": 0, "both": 0}
    for r in rows:
        pm, pw = D.precision(r["dob_man"]), D.precision(r["dob_woman"])
        if pm == D.PRECISION_DAY and pw == D.PRECISION_DAY:
            keep.append(r)
        else:
            k = ("both" if pm != D.PRECISION_DAY and pw != D.PRECISION_DAY
                 else "man" if pm != D.PRECISION_DAY else "woman")
            dropped[k] += 1
    print(f"  {len(keep):,} have BOTH dates to the day  ({100*len(keep)/len(rows):.1f}%)")
    print(f"  dropped: {dropped['man']:,} where his date is coarser, {dropped['woman']:,} where hers is, "
          f"{dropped['both']:,} where both are")

    # Every surviving row must genuinely be day precision, and no `00` may reach the published file: the whole
    # point of this test set is that one question is being asked, on inputs of one kind.
    for r in keep:
        assert "-00" not in r["dob_man"] and "-00" not in r["dob_woman"], r
        assert D.precision(r["dob_man"]) == 11 and D.precision(r["dob_woman"]) == 11, r

    rng = np.random.default_rng(20260814)
    ids = [r["id"] for r in keep]
    usage = {i: ("Public" if u < PUBLIC_FRACTION else "Private")
             for i, u in zip(ids, rng.random(len(ids)))}

    test_p = os.path.join(OUT, "test.csv")
    sol_p = os.path.join(OUT, "solution.csv")
    samp_p = os.path.join(OUT, "sample_submission.csv")
    with open(test_p, "w", newline="") as ft, open(sol_p, "w", newline="") as fs, \
            open(samp_p, "w", newline="") as fp:
        wt, ws, wp = csv.writer(ft), csv.writer(fs), csv.writer(fp)
        wt.writerow(["id", "dob_man", "dob_woman"])
        ws.writerow(["id", "parents_together", "Usage"])
        wp.writerow(["id", "parents_together"])
        for r in keep:
            wt.writerow([r["id"], r["dob_man"], r["dob_woman"]])
            ws.writerow([r["id"], sol_in[r["id"]], usage[r["id"]]])
            wp.writerow([r["id"], 0.5])

    pos = sum(int(sol_in[r["id"]]) for r in keep)
    pub = sum(1 for v in usage.values() if v == "Public")
    print(f"  wrote {len(keep):,} rows · {pos:,} positive ({100*pos/len(keep):.2f}%) · "
          f"{pub:,} public / {len(keep)-pub:,} private")
    # A leaderboard needs both classes on BOTH sides of the split, or the AUC is undefined for one of them.
    for side in ("Public", "Private"):
        sub = [int(sol_in[i]) for i in ids if usage[i] == side]
        assert 0 < sum(sub) < len(sub), f"the {side} half has only one class and cannot be scored"
        print(f"    {side:<8} {len(sub):>7,} rows, {100*sum(sub)/len(sub):.2f}% positive")

    for p in (test_p, sol_p, samp_p):
        print(f"    {os.path.getsize(p)/1e6:5.2f} MB  {os.path.basename(p)}")
    json.dump({"rows": len(keep), "positives": pos, "metric": "AUC",
               "precision": "both dates known to the day",
               "public_fraction": PUBLIC_FRACTION,
               "dropped_for_coarse_dates": dropped},
              open(os.path.join(OUT, "testset.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
