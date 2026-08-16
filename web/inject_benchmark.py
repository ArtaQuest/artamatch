"""
inject_benchmark.py — put the measured grid, and the window the model may be asked about, into web/model.json.

WHY THIS IS A SCRIPT AND NOT THREE LINES AT A PROMPT. It was three lines at a prompt, and one of them was
`m["base"] = result["baseline_auc"]` — which replaced the model's LIST OF 51 BASE MODELS with a float. The file
still looked like a model and could not be loaded. ship.py refused to bundle it, which is the only reason it did
not ship. So the keys the exporter owns are now explicitly protected, and the only thing this may add is the
measurement.

WHAT IT ADDS
    benchmark      the 15 per-cell AUCs, their mean, the same 15 cells for the signed-gap reference
    train_window   the years the model was FITTED on, so the page refuses to answer outside them

WHY THE WINDOW TRAVELS WITH THE MODEL. The page used to carry `YEAR_LO, YEAR_HI = 1800, 2026` as constants —
the span of the shipped ephemeris. That is not the same question as "what was this model trained on", and once
the training window moved to 1800-1950 the constants silently authorised extrapolation: the page's own default
inputs were 1994 and 2004, and it would have answered them with confidence. A model that declares its own
window cannot drift away from the page.

Usage: AQ_MODEL=/tmp/aqfull4 AQ_TRAIN=/tmp/aqscrape3/train.csv ~/.artamatch-venv/bin/python web/inject_benchmark.py
"""
import csv
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.environ.get("AQ_MODEL", "/tmp/aqfull4")
TRAIN = os.environ.get("AQ_TRAIN", "/tmp/aqscrape3/train.csv")

# Everything the exporter writes. This script may ADD keys and may not touch these, because they are the model.
EXPORTER_OWNS = {"base", "meta", "blocks", "contract", "rate", "hour", "traditions", "tradition_auc"}
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "kaggle"))
import dates as D          # noqa: E402  — the grid is defined once

LEVELS = D.LEVELS
EXPECTED = set(D.CELLS)


def main():
    m = json.load(open(os.path.join(MODEL, "model.json")))
    res = json.load(open(os.path.join(MODEL, "result.json")))
    # TWO MEASUREMENTS CAN LIVE HERE, and the page shows whichever the build produced. The precision GRID is the
    # robustness measurement (fourteen cells of degraded dates). The TEMPORAL RANKING is the newer and harder one:
    # every tradition alone, plus the ensemble, on held-out couples that all postdate the training half. A build
    # that produced only the ranking must not be refused for lacking the grid — that would block the more
    # important result behind the less important one.
    gp = os.path.join(MODEL, "grid_result.json")
    rp = os.path.join(MODEL, "tradition_ranking.json")
    g = json.load(open(gp)) if os.path.exists(gp) else None
    rk = json.load(open(rp)) if os.path.exists(rp) else None
    if g is None and rk is None:
        raise SystemExit("neither grid_result.json nor tradition_ranking.json exists — nothing measured to inject")

    before = {k: m[k] for k in EXPORTER_OWNS if k in m}
    if not isinstance(m.get("base"), list) or not m["base"]:
        raise SystemExit(f"model.json's `base` is a {type(m.get('base')).__name__}, not the list of base "
                        f"models — this file is not loadable and must not be shipped")

    if g is not None:
        cells = set(g["per_cell"])
        if cells != EXPECTED:
            raise SystemExit(f"the grid has {len(cells)} cells, not the {len(EXPECTED)} the metric averages; "
                             f"unexpected {sorted(cells - EXPECTED)}, missing {sorted(EXPECTED - cells)}")

    years = []
    with open(TRAIN) as f:
        for r in csv.DictReader(f):
            years.append(int(r["dob_man"][:4]))
            years.append(int(r["dob_woman"][:4]))
    lo, hi = min(years), max(years)

    if rk is not None:
        # The temporal ranking: what the page leads with when it exists.
        m["temporal"] = {
            "metric": "AUC on held-out couples that all postdate the training half; day-precision dates only",
            "ensemble": rk["ensemble"], "era_rule": rk["era_rule"], "n_test": rk["n_test"],
            "traditions": [{"slug": t["tradition"], "name": t["name"], "auc": t["auc"],
                            "public": t["public"], "private": t["private"], "n_base": t["n_base"],
                            "beats_era": t["beats_era"]} for t in rk["traditions"]],
        }
    m["benchmark"] = None if g is None else {
        "metric": g["metric"],
        "benchmark15": g["mean15"],
        "reference15": g["reference_signed_gap_mean15"],
        "lift": g["lift"],
        "n_rows": g["couples"],
        "grid": "man x woman",
        # The list, not a sentence: the page renders a blank per excluded cell and needs to know which.
        "excluded": sorted(g.get("excluded") or D.EXCLUDED_CELLS),
        "cells_scored": len(g["per_cell"]),
        "weighted": True,
        "cells": {k: {"stack": v,
                      "baseline": g["reference_per_cell"][k],
                      "lift": v - g["reference_per_cell"][k]} for k, v in g["per_cell"].items()},
    }
    # Read off the training file itself rather than restated by hand, so the page cannot claim a window the
    # model was not fitted on.
    m["train_window"] = {"from": lo, "to": hi, "n": len(years) // 2}
    m["auc"] = res["cv_auc"]
    m["n"] = res["n_train"]

    after = {k: m[k] for k in EXPORTER_OWNS if k in m}
    if after != before:
        raise SystemExit(f"this script modified keys it does not own: "
                         f"{sorted(k for k in after if after[k] != before.get(k))}")

    json.dump(m, open(os.path.join(HERE, "model.json"), "w"))
    shutil.copy2(os.path.join(MODEL, "model.npz"), os.path.join(HERE, "model.npz"))

    print(f"  web/model.json: {len(m['base'])} base models untouched")
    if g is not None:
        print(f"  grid: weighted mean of {len(g['per_cell'])} AUCs {g['mean15']:.4f}   "
              f"reference {g['reference_signed_gap_mean15']:.4f}   lift {g['lift']:+.4f}")
    if rk is not None:
        print(f"  temporal: ensemble {rk['ensemble']:.4f} vs era rule {rk['era_rule']:.4f} on {rk['n_test']:,} "
              f"held-out couples; {len(rk['traditions'])} traditions ranked, "
              f"{sum(t['beats_era'] for t in rk['traditions'])} beat the era rule")
    print(f"  train_window {lo}-{hi} over {len(years)//2:,} couples — the page will refuse anything outside it")
    print(f"  out-of-fold AUC {res['cv_auc']:.4f}   baseline {res['baseline_auc']:.4f}")


if __name__ == "__main__":
    main()
