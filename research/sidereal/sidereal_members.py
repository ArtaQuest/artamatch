"""
sidereal_members.py — the PyJHora / iztro sidereal families as stack members for edition IV (one member per
sub-family: Vedic D1, vargas, pañcāṅga, ṣaḍbala, aṣṭakavarga, doṣa, daśā, pair/Aṣṭakūṭa; Zǐ Wēi palaces, majors,
minors, pair, crossings). Features are built by build_sidereal.py on the edition-IV files with the slots named
dad/mom for the builder only (slot a = "dad", slot b = "mom"); both orders of every pair are in the rows, and the
ensemble symmetrises every member over the pair, so no order survives into a score.
LightGBM per family, forward-chained OOF over the stack's four blocks; all-train fit scores the test rows.
Usage: AQ_FEAT=/tmp/aq4sid/sidereal.npz AQ_PHASES=/tmp/aq4feat/phases.npz AQ_OUT=/tmp/aq4sub python sidereal_members.py
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from rank_sidereal import subfamily                                   # noqa: E402

FEAT = os.environ.get("AQ_FEAT", "/tmp/aq4sid/sidereal.npz"); PH = os.environ.get("AQ_PHASES", "/tmp/aq4feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq4sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


def main():
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score as auc
    F = np.load(FEAT, allow_pickle=True); Xtr, Xte, names, y = F["X_train"], F["X_test"], list(F["names"]), F["y_train"].astype(int)
    Z = np.load(PH, allow_pickle=True); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    assert len(y) == len(later) == Xtr.shape[0], (len(y), len(later), Xtr.shape)
    fam = np.array([subfamily(n) for n in names]); fams = [f for f in dict.fromkeys(fam) if f != "plain"]
    prm = dict(n_estimators=300, learning_rate=0.04, num_leaves=15, min_child_samples=100, colsample_bytree=0.5, subsample=0.8, subsample_freq=1, reg_lambda=10.0, verbose=-1)
    GPU = os.environ.get("AQ_GPU") == "1"
    def learner():
        if GPU:
            import xgboost as xgb
            return xgb.XGBClassifier(n_estimators=300, learning_rate=0.04, max_depth=4, min_child_weight=50, colsample_bytree=0.5, subsample=0.8, reg_lambda=10.0, tree_method="hist", device="cuda", verbosity=0)
        return lgb.LGBMClassifier(random_state=0, **prm)
    S_tr = np.full((len(y), len(fams)), np.nan, np.float32); S_te = np.full((Xte.shape[0], len(fams)), np.nan, np.float32); meta = []
    for i, fm in enumerate(fams):
        cols = np.where(fam == fm)[0]; A, B = Xtr[:, cols], Xte[:, cols]; rows_tr = np.isfinite(A).any(1); rows_te = np.isfinite(B).any(1)
        oof = np.full(len(y), np.nan)
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = rows_tr & (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); fit = rows_tr & (later <= lo)
            if fit.sum() < 500 or not blk.any() or len(np.unique(y[fit])) < 2:
                continue
            c = learner(); c.fit(A[fit], y[fit]); oof[blk] = c.predict_proba(A[blk])[:, 1]
        c = learner(); c.fit(A[rows_tr], y[rows_tr]); S_te[rows_te, i] = c.predict_proba(B[rows_te])[:, 1]
        S_tr[:, i] = oof; f = np.isfinite(oof); o = auc(y[f], oof[f]) if f.sum() > 500 else float("nan")
        meta.append({"family": fm, "n_features": int(len(cols)), "n_train_rows": int(rows_tr.sum()), "forward_oof": o})
        log(f"  {fm:<46} {len(cols):>5} features  rows {rows_tr.sum():>7,}  fwd-OOF {o:.4f}")
    np.savez_compressed(os.path.join(OUT, "sidereal_members.npz"), S_train=S_tr, S_test=S_te, names=np.array([f"SIDEREAL {f}" for f in fams]), meta=json.dumps(meta))
    log(f"wrote {OUT}/sidereal_members.npz with {len(fams)} family members")


if __name__ == "__main__":
    main()
