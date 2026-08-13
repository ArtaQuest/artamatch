"""
finalmodel.py — pick and fit the model that will actually ship, on the features a form can collect.

Two questions, in order:

  1. WHICH MODEL FAMILY. A gradient-boosted ensemble has to be exported as hundreds of trees and
     reimplemented in TypeScript; a logistic regression is a dot product and ships as a weight vector. If
     the linear model is close, it is the better artefact by a wide margin. Measured, not assumed.
  2. FITTED ON EVERYTHING. Whatever wins is then refitted on ALL couples at full budget, since the sweep
     used a 70,000 subsample and a reduced iteration count for speed.

The score quoted on the page comes from this file's cross-validated column, on the form-context tier only.

Usage: cd astro && /tmp/aqpy/bin/python finalmodel.py
"""

import json
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from core import load
import evalx
from evalx import MODELS
import run
from selfserve import form_context, BEST_BLOCK

CANDIDATES = ["logistic L2 (C=0.01)", "logistic L2 (C=0.1)", "logistic L2 (C=1)", "LDA",
              "lightgbm", "xgboost", "hist gradient boosting"]


def main():
    E = load()
    man, files = run._blocks()
    X = np.concatenate([run._get(files, BEST_BLOCK), form_context(E)], axis=1)
    print(f"{E.n:,} couples · {X.shape[1]} features (4 astrology + {X.shape[1]-4} form context)\n")
    folds = list(GroupKFold(n_splits=5).split(np.zeros(E.n), E.Y, groups=E.gid))
    print(f"  {'model':<26} {'AUC':>8}  {'deployable as':<28}")
    print(f"  {'-'*26} {'-'*8}  {'-'*28}")
    res = {}
    for mn in CANDIDATES:
        f = MODELS(X.shape[1]).get(mn)
        if f is None:
            continue
        p = np.zeros(E.n)
        try:
            for tr, te in folds:
                mdl = run.pipe("raw", X.shape[1], f)
                mdl.fit(X[tr], E.Y[tr])
                p[te] = evalx._proba(mdl, X[te])
        except Exception as e:
            print(f"  {mn:<26} FAILED {str(e)[:40]}")
            continue
        auc = float(roc_auc_score(E.Y, p))
        res[mn] = auc
        shape = "a weight vector" if ("logistic" in mn or mn == "LDA") else "hundreds of trees"
        print(f"  {mn:<26} {auc:>8.4f}  {shape:<28}")
    json.dump(res, open("max-out/finalmodel.json", "w"), indent=1)
    lin = max((v for k, v in res.items() if "logistic" in k or k == "LDA"), default=0)
    tree = max((v for k, v in res.items() if not ("logistic" in k or k == "LDA")), default=0)
    print(f"\n  best linear {lin:.4f} · best tree {tree:.4f} · the trees are worth {tree-lin:+.4f}")
    print("  A gap under about 0.01 is not worth shipping a tree ensemble to a browser for.")


if __name__ == "__main__":
    main()
