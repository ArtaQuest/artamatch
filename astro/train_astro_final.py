"""
train_astro_final.py — fit the astrology-only stack on every row and save it as one bundle.

The bundle carries everything prediction needs and nothing it can drift from:
  base       the 45 (block, model) pairs the stack is built on, each fitted on ALL rows
  colspec    per block, which columns training used, so a scoring batch cannot silently supply a
             different matrix (constant-column pruning differs between a 60,000-couple training set and a
             scoring batch where the fixed partner never varies)
  meta       the meta-logistic fitted on out-of-fold base predictions, never on in-fold ones
  auc        the cross-validated score, so whatever quotes this bundle can quote what it was worth

Usage: cd astro && ~/.artamatch-venv/bin/python train_astro_final.py
"""
import json
import os

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from core import load
import evalx
from evalx import MODELS
import run

OUT = "astro-final.joblib"
META_C = 0.03


def main():
    E = load()
    man, files = run._blocks()
    st = json.load(open(os.path.join(run.OUTDIR, "astro-stack.json")))
    base = [b for b in st["base_models"] if b["key"] in files]
    print(f"{E.n:,} rows · {len(base)} astrology base models · meta logistic C={META_C}")
    bymeta = {b["key"]: b for b in man["blocks"]}

    folds = list(GroupKFold(n_splits=5).split(np.zeros(E.n), E.Y, groups=E.gid))
    P = np.zeros((E.n, len(base)))
    fitted, colspec = [], {}
    for j, b in enumerate(base):
        X = run._get(files, b["key"])
        f = MODELS(X.shape[1])[b["model"]]
        for tr, te in folds:
            m = run.pipe("raw", X.shape[1], f)
            m.fit(X[tr], E.Y[tr])
            P[te, j] = evalx._proba(m, X[te])
        whole = run.pipe("raw", X.shape[1], f)
        whole.fit(X, E.Y)                      # the model prediction will actually use
        fitted.append(whole)
        mm = bymeta[b["key"]]
        colspec[b["key"]] = {"kept_idx": mm.get("kept_idx"), "full_cols": mm.get("full_cols"),
                             "cols": mm["cols"]}
        print(f"  [{j+1:>2}/{len(base)}] oof {roc_auc_score(E.Y, P[:, j]):.4f}  {b['key'][:56]}", flush=True)

    # the meta-learner, scored out of fold and then refitted on all the OOF columns
    pred = np.zeros(E.n)
    for tr, te in folds:
        mt = make_pipeline(StandardScaler(), LogisticRegression(C=META_C, max_iter=3000))
        mt.fit(P[tr], E.Y[tr])
        pred[te] = mt.predict_proba(P[te])[:, 1]
    auc = float(roc_auc_score(E.Y, pred))
    meta = make_pipeline(StandardScaler(), LogisticRegression(C=META_C, max_iter=3000))
    meta.fit(P, E.Y)
    print(f"\nstacked cross-validated AUC {auc:.4f}")

    joblib.dump({"kind": "astrology-only stack", "blocks": [b["key"] for b in base],
                 "models": [b["model"] for b in base], "estimators": fitted, "meta": meta,
                 "colspec": colspec, "auc": auc, "n": int(E.n), "rate": float(E.Y.mean()),
                 "label": "P(became parents together)",
                 "baselines": st.get("baselines", {})}, OUT)
    print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
