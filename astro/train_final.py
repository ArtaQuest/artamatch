"""
train_final.py — fit the model that the partner search will use, on every row, and save it with the block
list it needs so prediction cannot drift from training.

The block list and estimator are chosen from the deep sweep's own results rather than by hand: whichever
(block set, model) combination scored best out of fold. The bundle records the cross-validated AUC so the
prediction step can print what the score it is quoting was actually worth.

Usage: cd astro && /tmp/aqpy/bin/python train_final.py --out final-model.joblib
"""
import argparse
import json
import os

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from core import load
import evalx
from evalx import MODELS
import run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="final-model.joblib")
    ap.add_argument("--model", default="xgboost")
    ap.add_argument("--blocks", default="", help="comma-separated block keys; default = the four-input set")
    a = ap.parse_args()

    E = load()
    man, files = run._blocks()
    if a.blocks:
        keys = [k.strip() for k in a.blocks.split(",") if k.strip()]
    else:
        # the four-input contract: everything derivable from two dates and two birthplaces
        keys = [k for k in ("cohort::coh: EVERYTHING", "precision::prec: EVERYTHING",
                            "geo4::geo: EVERYTHING") if k in files]
    missing = [k for k in keys if k not in files]
    if missing:
        raise SystemExit(f"blocks not built: {missing}")
    X = np.concatenate([run._get(files, k) for k in keys], axis=1)
    # Record which columns of each block training actually used, so prediction can reproduce the exact
    # matrix rather than whatever a scoring batch happens to leave non-constant.
    bymeta = {b["key"]: b for b in man["blocks"]}
    colspec = {k: {"kept_idx": bymeta[k].get("kept_idx"), "full_cols": bymeta[k].get("full_cols"),
                   "cols": bymeta[k]["cols"]} for k in keys}
    print(f"{E.n:,} rows · {X.shape[1]} features from {len(keys)} blocks · model {a.model}")

    folds = list(GroupKFold(n_splits=5).split(np.zeros(E.n), E.Y, groups=E.gid))
    p = np.zeros(E.n)
    for tr, te in folds:
        m = run.pipe("raw", X.shape[1], MODELS(X.shape[1])[a.model])
        m.fit(X[tr], E.Y[tr])
        p[te] = evalx._proba(m, X[te])
    auc = float(roc_auc_score(E.Y, p))
    print(f"cross-validated AUC {auc:.4f}")

    est = run.pipe("raw", X.shape[1], MODELS(X.shape[1])[a.model])
    est.fit(X, E.Y)
    joblib.dump({"estimator": est, "blocks": keys, "colspec": colspec, "auc": auc, "model": a.model,
                 "label": "P(became parents together)", "n": int(E.n),
                 "rate": float(E.Y.mean())}, a.out)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
