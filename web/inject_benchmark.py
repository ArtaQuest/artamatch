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

    # An ABSENT partner is written 0000-00-00 and must not count as a birth in year zero. It did: the page
    # reported the model as fitted on 0-1900 and would have accepted a year-0 date as inside the window. Caught on
    # a fixture with one-sided rows, before the real run.
    years, n_rows = [], 0
    with open(TRAIN) as f:
        for r in csv.DictReader(f):
            n_rows += 1
            for c in ("dob_older", "dob_younger"):
                y = int(r[c][:4])
                if y > 0:
                    years.append(y)
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
        "grid": "older x younger",
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
    m["train_window"] = {"from": lo, "to": hi, "n": n_rows}
    m["n"] = res["n_train"]

    # THE HEADLINE NUMBER IS THE HELD-OUT ONE WHEN THERE IS ONE. This read `m["auc"] = res["cv_auc"]`, and the
    # page falls back to `i.auc` for its headline whenever the precision-grid data is absent — which it now
    # always is, because that grid was retired when the test set became day-precision only. So the prod page
    # would have shown the in-training selection AUC as the model's score, under a label describing a metric
    # that no longer exists.
    #
    # That number is optimistic and it is not a small effect: on 1,500 rows of COIN-FLIP labels it prints ~0.56
    # while the age-gap baseline beside it correctly prints ~0.50, because the base predictions the meta model
    # combines were produced over the same folds the meta is validated on, the hgb-vs-logit choice is made on
    # that same vector, and block screening ran on all of train. It is a selection score, not a performance
    # estimate, and a published figure must never be the flattering one.
    #
    # rank_traditions.py already measures the ensemble on the TEMPORAL held-out couples, which is the number the
    # competition is scored on. `auc_kind` travels with it so the page can say which it is showing rather than
    # leaving a reader to assume.
    if rk is not None:
        m["auc"] = rk["ensemble"]
        m["auc_kind"] = "heldout"
        m["heldout"] = {"auc": rk["ensemble"], "era_rule": rk["era_rule"], "n": rk["n_test"]}
    else:
        m["auc"] = res["cv_auc"]
        m["auc_kind"] = "in-training selection (optimistic)"

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
    print(f"  train_window {lo}-{hi} over {n_rows:,} couples — the page will refuse anything outside it")
    print(f"  headline the page will show: {m['auc']:.4f} ({m['auc_kind']})")
    print(f"  in-training selection AUC {res['cv_auc']:.4f} (optimistic, not published) · "
          f"signed-gap baseline {res['baseline_auc']:.4f}")


if __name__ == "__main__":
    main()
