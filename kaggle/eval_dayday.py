"""
eval_dayday.py — score a model on the competition's own metric, fast.

WHY THIS EXISTS ALONGSIDE eval_grid.py. The grid builds features for 355,670 rows and takes about 18 minutes.
The competition asks one question on 16,469 couples, so scoring a candidate model against it needs a twentieth of
that work. When the objective is a single AUC, an 18-minute evaluation loop is the thing stopping you from trying
more than a couple of ideas.

Usage: AQ_MODEL=/tmp/aqfull7 AQ_COMP=/tmp/aqcomp ~/.artamatch-venv/bin/python eval_dayday.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ASTRO = os.path.join(os.path.dirname(HERE), "astro")
# predictor.py lives in web/ — it is the numpy evaluator the browser runs, and reusing it here is the point:
# a score measured with the shipped evaluator cannot disagree with the score the page shows.
WEB = os.path.join(os.path.dirname(HERE), "web")
sys.path.insert(0, HERE)
sys.path.insert(0, ASTRO)
sys.path.insert(0, WEB)
import dates as D          # noqa: E402
import competition_metric as cm          # noqa: E402

MODEL = os.environ.get("AQ_MODEL", "/tmp/aqfull6")
COMP = os.environ.get("AQ_COMP", "/tmp/aqcomp")
CAND = "/tmp/aq_dayday_couples.json"
CHUNK = int(os.environ.get("AQ_CHUNK") or 8000)


def main():
    te = pd.read_csv(os.path.join(COMP, "test.csv"))
    sol = pd.read_csv(os.path.join(COMP, "solution.csv"))
    print(f"  {len(te):,} day-precision couples")

    os.environ.update({"AQ_COUPLES": CAND, "AQ_NO_PLACE": "1", "AQ_KEEP_ALL_COLS": "1",
                       "AQ_NO_EPHEM_CACHE": "1", "AQ_EPHEM_CACHE": "/nonexistent.npz"})
    import core
    import predictor
    stack = predictor.load(open(os.path.join(MODEL, "model.json")).read(),
                           open(os.path.join(MODEL, "model.npz"), "rb").read())
    mods = {}
    for b in stack.h["base"]:
        mods.setdefault(b["slug"], __import__(f"trad_{b['slug']}"))
    print(f"  {len(stack.h['base'])} base models across {len(mods)} traditions")

    preds = np.zeros(len(te))
    for start in range(0, len(te), CHUNK):
        part = te.iloc[start:start + CHUNK]
        json.dump([D.couple_record(i, r.dob_man, r.dob_woman)
                   for i, r in enumerate(part.itertuples())], open(CAND, "w"))
        E = core.load()
        if E.n != len(part):
            raise SystemExit(f"core kept {E.n} of {len(part)} — predictions could not be aligned")
        blocks = {}
        for slug, mod in mods.items():
            for k, v in (mod.build(E) or {}).items():
                if v is not None:
                    blocks[f"{slug}::{k}"] = np.asarray(v, dtype=np.float32)
        p, _ = stack.proba(blocks)
        preds[start:start + len(part)] = p
        print(f"    {start+len(part):,}/{len(te):,}", flush=True)

    d = pd.DataFrame({"id": te.id, "p": preds}).merge(sol, on="id", validate="one_to_one")
    overall = cm._auc(d.parents_together.to_numpy(), d.p.to_numpy())
    out = {"auc": float(overall), "n": int(len(d)), "metric": "AUC on day-precision couples"}
    for side in ("Public", "Private"):
        s = d[d.Usage == side]
        a = float(cm._auc(s.parents_together.to_numpy(), s.p.to_numpy()))
        out[side.lower()] = a
        print(f"    {side:<8} {a:.4f}  ({len(s):,} rows)")
    print(f"\n  DAY x DAY AUC : {overall:.4f}")
    pd.DataFrame({"id": te.id, "parents_together": preds}).to_csv(
        os.path.join(MODEL, "submission_dayday.csv"), index=False)
    json.dump(out, open(os.path.join(MODEL, "dayday_result.json"), "w"), indent=1)
    print(f"  wrote submission_dayday.csv and dayday_result.json")


if __name__ == "__main__":
    main()
