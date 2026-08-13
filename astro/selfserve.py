"""
selfserve.py — what the model is worth using ONLY what a web form can ask a stranger.

The deployed page is self-serve: two people type in what they know about themselves. That is a strict
subset of the context the sweep had. The sweep's best model reached AUC 0.7023 using a 421-column context
block that includes CITIZENSHIP one-hots — and a visitor will not be asked for their citizenship history,
nor could they give the multi-valued historical-state version the model was trained on.

So the honest question is not "how good is the best model" but "how good is the best model on the features
the page can actually collect". Three tiers are measured:

    dates only      the two birth dates and nothing else
    + form context  what a form can reasonably ask: birth country, sex, and exact date precision
    full context    everything the sweep had, including citizenship — the 0.7023 number

Whatever the page ships, it must quote the tier it can actually feed. Quoting the full-context number on a
page that cannot supply citizenship would be a lie by omission.

Usage: cd astro && AQ_COUPLES=... /tmp/aqpy/bin/python selfserve.py
"""

import json
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from core import load
import ctx_nationality as CN
import ctx_precision as CP
from evalx import MODELS
import run

BEST_BLOCK = "mesoamerican::meso: distance numbers (LC intervals)"
BEST_MODEL = "lightgbm"
BEST_REP = "raw"


def form_context(E):
    """Only the context a stranger can supply: birth country, sex, and their dates being exact.

    Deliberately EXCLUDES citizenship (multi-valued, historical, and not something a form asks) and
    birthplace coordinates beyond the country. Missingness indicators are kept, because the model was
    trained with them and a page that supplies nothing for citizenship needs those columns to say so.
    """
    full = CN.build(E)
    prec = CP.build(E)
    keep = [
        full["ctx: birth country one-hot, both"],
        full["ctx: birth region + same region"],
        full["ctx: sex pair"],
        prec["prec: date precision + window width"],
    ]
    return np.concatenate(keep, axis=1)


def main():
    E = load()
    man, files = run._blocks()
    X0 = run._get(files, BEST_BLOCK)
    fullctx = np.concatenate(
        [np.load(files[k]).astype(np.float64) for k in run.CONTEXT_KEYS if k in files], axis=1)
    formctx = form_context(E)
    print(f"{E.n:,} couples · astrology block {X0.shape[1]} cols · "
          f"form context {formctx.shape[1]} cols · full context {fullctx.shape[1]} cols\n")

    tiers = {
        "dates only (astrology block alone)": X0,
        "+ form context (country, sex, precision)": np.concatenate([X0, formctx], axis=1),
        "+ FULL context (adds citizenship)": np.concatenate([X0, fullctx], axis=1),
        "form context alone, no astrology": formctx,
    }
    folds = list(GroupKFold(n_splits=5).split(np.zeros(E.n), E.Y, groups=E.gid))
    print(f"  {'feature tier':<44} {'cols':>6} {'AUC':>8}")
    print(f"  {'-'*44} {'-'*6} {'-'*8}")
    out = {}
    for name, X in tiers.items():
        p = np.zeros(E.n)
        f = MODELS(X.shape[1])[BEST_MODEL]
        for tr, te in folds:
            mdl = run.pipe(BEST_REP, X.shape[1], f)
            mdl.fit(X[tr], E.Y[tr])
            import evalx
            p[te] = evalx._proba(mdl, X[te])
        auc = float(roc_auc_score(E.Y, p))
        out[name] = {"cols": int(X.shape[1]), "auc": auc}
        print(f"  {name:<44} {X.shape[1]:>6} {auc:>8.4f}")
    json.dump(out, open("max-out/selfserve.json", "w"), indent=1)
    print("\n  The page must quote the '+ form context' row — that is the only tier it can feed.")


if __name__ == "__main__":
    main()
