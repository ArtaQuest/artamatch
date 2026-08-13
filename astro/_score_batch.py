"""
_score_batch.py — score one batch of candidate partners. Called by predict_partner.py as a subprocess.

Run in its own process on purpose: core.load() caches the couples and the ephemeris at module scope, so a
long sweep over city batches in one process would either reuse a stale cache or need core to be reloadable.
A fresh process per batch is the simplest thing that is definitely correct.

Prints one line of JSON: [{date, city, country, pop, score}, ...]
"""
import json
import os
import sys

import joblib
import numpy as np

from core import load
import run


def main():
    model_path, cand_path = sys.argv[1], sys.argv[2]
    bundle = joblib.load(model_path)
    rows = json.load(open(cand_path))
    E = load()
    # core.load can drop rows (implausible spacing, out-of-range dates), so candidates are matched back by
    # the person id it preserves rather than by position — an off-by-one here would silently mis-attribute
    # every score in the batch.
    keys = [r["pyng"] if r["pyng"] != "SELF" else r["pold"] for r in E.recs]
    meta = {r["b"]: r for r in rows}

    # Build with NO constant-column pruning, then select exactly the columns training kept. Without this a
    # scoring batch silently gets a narrower matrix — every candidate shares the fixed partner, so plenty of
    # columns are constant here that were not constant across 135,000 real couples.
    os.environ["AQ_KEEP_ALL_COLS"] = "1"
    run.collect()
    man, files = run._blocks()
    colspec = bundle.get("colspec") or {}
    mats = []
    for k in bundle["blocks"]:
        if k not in files:
            sys.exit(f"block {k} missing from this batch's manifest")
        M = run._get(files, k)
        spec = colspec.get(k)
        if spec and spec.get("kept_idx") is not None:
            if M.shape[1] != spec["full_cols"]:
                sys.exit(f"block {k}: batch has {M.shape[1]} raw columns, training saw {spec['full_cols']}")
            M = M[:, spec["kept_idx"]]
        if spec and M.shape[1] != spec["cols"]:
            sys.exit(f"block {k}: {M.shape[1]} columns after selection, training used {spec['cols']}")
        mats.append(M)
    X = np.concatenate(mats, axis=1)
    p = bundle["estimator"].predict_proba(X)[:, 1]

    out = []
    for i, key in enumerate(keys):
        m = meta.get(key)
        if m is None:
            continue
        out.append({"date": m["_date"], "city": m["_city"], "country": m["_country"],
                    "pop": m["_pop"], "score": float(p[i])})
    print(json.dumps(out))


if __name__ == "__main__":
    main()
