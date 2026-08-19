"""
tradition_members.py — every OTHER astrology and numerology as a stack member for edition IV.

Operator 2026-08-19: "add all other astrology and numerologies to the stack". The astro/ bundle holds nineteen
tradition modules (Hellenistic, modern Western, Uranian, harmonics, Vedic core / aṣṭakavarga / matching, Chinese,
East Asian, Tibetan, Persian-Arabic, Babylonian-Egyptian, Mesoamerican, Polynesian, African, Aboriginal Australian,
Indigenous Americas, lunar-calendrical, numerology — plus houses and astrocartography) built on core.py, which
orders the two partners by AGE and reads no sex: genderless already, and identical for (a, b) and (b, a). So each
tradition is computed ONCE per unordered pair and broadcast to both rows.

One member per tradition: LightGBM on all of the tradition's feature blocks, forward-chained OOF over the same four
blocks as the rest of the edition-IV stack, the all-train fit scoring the test pairs. Writes AQ_OUT/tradition_members.npz
(S_train rows x traditions, S_test, names) for artamodel_iv_ensemble.py to pick up.
Usage: AQ_SRC=/tmp/aq4 AQ_PHASES=/tmp/aq4feat/phases.npz AQ_OUT=/tmp/aq4sub python tradition_members.py
"""
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
ASTRO, WEB, KAG = os.path.join(ROOT, "astro"), os.path.join(ROOT, "web"), os.path.join(ROOT, "kaggle")
for p in (ASTRO, WEB, KAG, HERE):
    sys.path.insert(0, p)
SRC = os.environ.get("AQ_SRC", "/tmp/aq4"); PH = os.environ.get("AQ_PHASES", "/tmp/aq4feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq4sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
EXCLUDE = {"electional", "muhurta", "wedding_transits"}          # need the wedding instant; core runs DOB-only here


def pairkey(df):
    a = df["dob_a"] + "|" + df["lat_a"].fillna("").astype(str) + "|" + df["lon_a"].fillna("").astype(str)
    b = df["dob_b"] + "|" + df["lat_b"].fillna("").astype(str) + "|" + df["lon_b"].fillna("").astype(str)
    return np.where(a <= b, a + "||" + b, b + "||" + a) + "||" + df["start"]


def main():
    import dates as D
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score as auc
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    ktr, kte = pairkey(tr), pairkey(te)
    utr = pd.Series(np.arange(len(tr))).groupby(ktr).first(); ute = pd.Series(np.arange(len(te))).groupby(kte).first()
    rows_tr = tr.iloc[utr.to_numpy()].reset_index(drop=True); rows_te = te.iloc[ute.to_numpy()].reset_index(drop=True)
    log(f"train {len(tr):,} rows -> {len(rows_tr):,} pairs · test {len(te):,} rows -> {len(rows_te):,} pairs")
    y_pair = rows_tr["lasted_30_years"].astype(int).to_numpy()
    yrs = lambda df: np.fmax(pd.to_numeric(df.dob_a.str[:4], errors="coerce").fillna(0), pd.to_numeric(df.dob_b.str[:4], errors="coerce").fillna(0)).astype(int).to_numpy()
    later_pair = yrs(rows_tr)
    Z = np.load(PH, allow_pickle=True); later_rows = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later_rows, q) for q in QS]
    # core's couples file: train pairs then test pairs, one record each
    recs = []
    for i, r in enumerate(pd.concat([rows_tr, rows_te], ignore_index=True).itertuples(index=False)):
        rec = D.couple_record(i, r.dob_a, r.dob_b, int(getattr(r, "lasted_30_years", 0) or 0) if i < len(rows_tr) else 0)
        recs.append({k: v for k, v in rec.items() if not k.startswith("_")})
    cand = os.path.join(OUT, "couples_iv.json"); json.dump(recs, open(cand, "w"))
    os.environ.update({"AQ_COUPLES": cand, "AQ_NO_PLACE": "1", "AQ_KEEP_ALL_COLS": "1", "AQ_NO_EPHEM_CACHE": "1", "AQ_EPHEM_CACHE": "/nonexistent.npz"})
    for k in ("AQ_SUBSAMPLE", "AQ_BALANCE", "AQ_ROW_INDEX", "AQ_ONLY_KEYS", "AQ_DUMP_ROWS"):
        os.environ.pop(k, None)
    import sweshim
    sweshim.load(os.path.join(WEB, "ephem4.bin"), os.path.join(WEB, "tables.json")); sys.modules["swisseph"] = sweshim
    import core
    E = core.load(); log(f"core kept {E.n:,} of {len(recs):,} records")
    # map E's rows back to our record index through the ids couple_record gave ("a{i}" / "b{i}")
    idx = np.array([int(str(r["pold"])[1:]) for r in E.recs]); ntr = len(rows_tr)
    is_tr = idx < ntr; pos_tr = idx[is_tr]; pos_te = idx[~is_tr] - ntr
    y_e = y_pair[pos_tr]; later_e = later_pair[pos_tr]
    MODULES = [m[5:-3] for m in sorted(os.listdir(ASTRO)) if m.startswith("trad_") and m.endswith(".py") and m[5:-3] not in EXCLUDE]
    only = [m for m in os.environ.get("AQ_MODULES", "").split(",") if m]          # a shard of the traditions (Kaggle)
    if only:
        MODULES = [m for m in MODULES if m in only]; log(f"AQ_MODULES: {MODULES}")
    prm = dict(n_estimators=300, learning_rate=0.04, num_leaves=15, min_child_samples=100, colsample_bytree=0.3, subsample=0.8, subsample_freq=1, reg_lambda=10.0, verbose=-1)
    GPU = os.environ.get("AQ_GPU") == "1"
    def learner():
        """LightGBM on the CPU, or XGBoost on CUDA when AQ_GPU=1 (the Kaggle kernels): the same depth-limited
        boosted trees, the same 300 rounds, so a member's meaning does not change with the machine."""
        if GPU:
            import xgboost as xgb
            return xgb.XGBClassifier(n_estimators=300, learning_rate=0.04, max_depth=4, min_child_weight=50, colsample_bytree=0.3, subsample=0.8, reg_lambda=10.0,
                                     tree_method="hist", device="cuda", verbosity=0)
        return lgb.LGBMClassifier(random_state=0, **prm)
    S_tr = np.full((len(tr), len(MODULES)), np.nan, np.float32); S_te = np.full((len(te), len(MODULES)), np.nan, np.float32); meta = []
    tr_pos_of_key = pd.Series(np.arange(len(rows_tr)), index=utr.index); te_pos_of_key = pd.Series(np.arange(len(rows_te)), index=ute.index)
    row_to_pair_tr = tr_pos_of_key.loc[ktr].to_numpy(); row_to_pair_te = te_pos_of_key.loc[kte].to_numpy()
    for m_i, slug in enumerate(MODULES):
        t1 = time.time()
        try:
            blocks = __import__(f"trad_{slug}").build(E) or {}
        except Exception as e:
            log(f"  {slug}: build failed ({type(e).__name__}: {str(e)[:80]}) — skipped"); continue
        mats = [np.asarray(v, dtype=np.float32) for v in blocks.values() if v is not None]
        if not mats:
            log(f"  {slug}: no blocks — skipped"); continue
        X = np.column_stack(mats); del mats, blocks; gc.collect()
        X[~np.isfinite(X)] = np.nan
        Xtr, Xte = X[is_tr], X[~is_tr]
        s_pair_tr = np.full(ntr, np.nan); s_pair_te = np.full(len(rows_te), np.nan)
        oof = np.full(len(y_e), np.nan)
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = (later_e > lo) & ((later_e <= cuts[k]) if k < len(cuts) - 1 else True); fit = later_e <= lo
            if fit.sum() < 500 or not blk.any() or len(np.unique(y_e[fit])) < 2:
                continue
            c = learner(); c.fit(Xtr[fit], y_e[fit]); oof[blk] = c.predict_proba(Xtr[blk])[:, 1]
        c = learner(); c.fit(Xtr, y_e); pte = c.predict_proba(Xte)[:, 1]
        s_pair_tr[pos_tr] = oof; s_pair_te[pos_te] = pte
        S_tr[:, m_i] = s_pair_tr[row_to_pair_tr]; S_te[:, m_i] = s_pair_te[row_to_pair_te]
        f = np.isfinite(oof); o = auc(y_e[f], oof[f]) if f.sum() > 500 else float("nan")
        meta.append({"tradition": slug, "n_features": int(X.shape[1]), "n_pairs": int(E.n), "forward_oof": o})
        log(f"  {slug:<26} {X.shape[1]:>6,} features  fwd-OOF {o:.4f}  ({time.time()-t1:.0f}s)")
        del X, Xtr, Xte; gc.collect()
    names = np.array([f"TRADITION {m}" for m in MODULES])
    keep = [i for i in range(len(MODULES)) if np.isfinite(S_te[:, i]).any()]
    tag = os.environ.get("AQ_TAG", "")
    np.savez_compressed(os.path.join(OUT, f"tradition_members{tag}.npz"), S_train=S_tr[:, keep], S_test=S_te[:, keep], names=names[keep], meta=json.dumps(meta))
    log(f"wrote {OUT}/tradition_members{tag}.npz with {len(keep)} tradition members")


if __name__ == "__main__":
    main()
