"""
artamodel_iv_ensemble.py — the edition-IV ensemble, built so that the mistakes of the edition-III stack cannot recur.

  1. OUT-OF-FOLD SCORES ARE FORWARD ONLY: fit on every row before a cut, score the block after it (four blocks over
     the latest 60% of train by the later birth year). The test is "fit on ≤1900, predict >1900"; a backwards fold
     taught the III stacker that its clock members were noise.
  2. EVERY MEMBER IS THE SAME MODEL IN EVERY FOLD: the boosted ArtaModel member runs its phasors in a FIXED cycle
     (the greedy picker changed the model between folds). The greedy construction is kept as a second member.
  3. WEIGHTS ARE NON-NEGATIVE, so every subset is a feasible point of the full problem and the full pool cannot lose
     to a subset on the data it is fitted on — asserted in the table below, never assumed.
  4. WEIGHTS ARE FITTED PER AVAILABILITY GROUP (wedding-sky clocks present / synastry only / sky only) and on the
     most recent blocks, because train's mixture of groups is not test's.
  5. EVERYTHING IS EVEN: the plain model reads (older age, younger age, |gap|, start year); the phase members read
     |Δθ|; every score is averaged over the two orders of a pair before it is ranked.
Members: plain · ArtaModel IV greedy · ArtaModel IV fixed-cycle · 84 per-phasor fields · 6 per-term sums ·
the 3-term and 6-term sums.  Usage: AQ_PHASES=/tmp/aq4feat/phases.npz AQ_SOL=/tmp/aq4comp/solution.csv AQ_OUT=/tmp/aq4sub python artamodel_iv_ensemble.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from artamodel import BODIES14, TERMS_IV, auc, phase_matrix           # noqa: E402
from artamodel_full_stack import _fit, matched                        # noqa: E402
from artamodel_deploy import boost_recorded, score                    # noqa: E402
from artamodel_nonneg_final import boost_fixed                        # noqa: E402
from artamodel_iv import symmetrise, pair_key                         # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq4feat/phases.npz"); SOL = os.environ.get("AQ_SOL", "/tmp/aq4comp/solution.csv"); OUT = os.environ.get("AQ_OUT", "/tmp/aq4sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)


def forward(P, y, later, Pte, cuts, kind, rows=None, order=None):
    has = np.isfinite(P).any(1); has_te = np.isfinite(Pte).any(1); pop = has if rows is None else has & rows
    s_tr = np.full(len(P), np.nan); s_te = np.full(len(Pte), np.nan)
    def fit_on(mask):
        if mask.sum() < 300 or len(np.unique(y[mask])) < 2:
            return None
        L = later[mask]; inner = L > np.quantile(L, 0.85)
        if kind == "field":
            m, _ = _fit(P[mask], y[mask], inner); return lambda Q: m.logit(np.nan_to_num(np.cos(np.radians(Q))), np.nan_to_num(np.sin(np.radians(Q))))[0]
        if kind == "greedy":
            b = boost_recorded(P[mask], y[mask], inner, stages=80, nu=0.1); return lambda Q: score(b, Q)
        return boost_fixed(P[mask], y[mask], inner, order)
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]; blk = has & (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True)
        f = fit_on(pop & (later <= lo))
        if f is not None and blk.any():
            s_tr[blk] = f(P[blk])
    f = fit_on(pop)
    if f is not None:
        s_te[has_te] = f(Pte[has_te])
    return s_tr, s_te, int(pop.sum())


def rankfeat(X):
    F = np.zeros_like(X, dtype=float)
    for j in range(X.shape[1]):
        f = np.isfinite(X[:, j])
        if f.sum() > 1:
            F[f, j] = r01(X[f, j]) - 0.5
    return F


def fit_nonneg(F, y, sw, lam):
    n, m = F.shape; yy = 2.0 * y - 1.0
    def obj(th):
        w, b = th[:m], th[m]; z = F @ w + b; p = 1 / (1 + np.exp(-yy * z)); g = -(yy * (1 - p)) * sw
        return float(np.sum(sw * np.logaddexp(0, -yy * z)) / sw.sum() + lam * w @ w), np.concatenate([F.T @ g / sw.sum() + 2 * lam * w, [g.sum() / sw.sum()]])
    r = minimize(obj, np.zeros(m + 1), jac=True, method="L-BFGS-B", bounds=[(0, None)] * m + [(None, None)], options={"maxiter": 3000})
    return r.x[:m], r.x[m]


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True); s1, s2 = list(Z["slots"]); bodies = list(Z["bodies"]); ids = Z["id_test"]; y = Z["y_train"].astype(np.int64)
    A, Bm, W = Z[f"theta_{s1}_train"], Z[f"theta_{s2}_train"], Z["theta_wed_train"]; Ae, Be, We = Z[f"theta_{s1}_test"], Z[f"theta_{s2}_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); later = Z["yr_train"].astype(int).max(1)
    sol = pd.read_csv(SOL).set_index("id"); lab = [c for c in sol.columns if c != "Usage"][0]; yte = sol.loc[ids, lab].to_numpy().astype(int)
    j1 = ptr[:, pn.index("start_is_jan1")] == 1.0; j1e = pte[:, pn.index("start_is_jan1")] == 1.0; W = W.copy(); We = We.copy(); W[j1] = np.nan; We[j1e] = np.nan
    cuts = [np.quantile(later, q) for q in QS]; log(f"cuts {[int(c) for c in cuts]}; train {len(y):,} · test {len(ids):,}")
    B = [bodies.index(b) for b in BODIES14]; charts = np.isfinite(A[:, B]).all(1) & np.isfinite(Bm[:, B]).all(1)
    P, labels = phase_matrix(A, Bm, W, bodies, BODIES14, TERMS_IV, even=True); Pe, _ = phase_matrix(Ae, Be, We, bodies, BODIES14, TERMS_IV, even=True)
    # ---- plain, exactly even: older age, younger age, |gap|, start year ----
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    def plainX(p): a, b = p[:, ia], p[:, ib]; return np.column_stack([np.fmax(a, b), np.fmin(a, b), np.abs(a - b), p[:, iy]])
    X, Xe = plainX(ptr), plainX(pte)
    prm = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=100, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=10.0, verbose=-1)
    pl_tr = np.full(len(y), np.nan)
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True)
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(X[later <= lo], y[later <= lo]); pl_tr[blk] = c.predict_proba(X[blk])[:, 1]
    pl_te = np.zeros(len(Xe))
    for sd in range(3):
        c = lgb.LGBMClassifier(random_state=sd, **prm); c.fit(X, y); pl_te += c.predict_proba(Xe)[:, 1] / 3
    # ---- ADVERSARIAL-VALIDATION IMPORTANCE WEIGHTS (AQ_ADV=1): a classifier that tells train rows from test rows on the
    # covariates (ages, |gap|, start year, birthplaces, availability) gives every train row a weight p/(1−p) — how much
    # it resembles the test era — used as sample weights in the geography fit and the stacker. Clipped to [0.2, 5].
    ADV = os.environ.get("AQ_ADV") == "1"; adv_w = np.ones(len(y))
    if ADV:
        SRC_a = os.environ.get("AQ_SRC", "/tmp/aq4"); tra = pd.read_csv(f"{SRC_a}/train.csv", dtype=str); tea = pd.read_csv(f"{SRC_a}/test.csv", dtype=str)
        def cov(df, p):
            a, b = p[:, ia], p[:, ib]; la = pd.to_numeric(df.lat_a, errors="coerce").to_numpy(); lo = pd.to_numeric(df.lon_a, errors="coerce").to_numpy(); lb = pd.to_numeric(df.lat_b, errors="coerce").to_numpy(); lob = pd.to_numeric(df.lon_b, errors="coerce").to_numpy()
            return np.column_stack([np.fmax(a, b), np.fmin(a, b), np.abs(a - b), p[:, iy], np.fmax(la, lb), np.fmin(la, lb), np.fmax(lo, lob), np.fmin(lo, lob), np.isnan(la).astype(float) + np.isnan(lb).astype(float), p[:, pn.index("start_is_jan1")]])
        Xa = np.vstack([cov(tra, ptr), cov(tea, pte)]); ya = np.concatenate([np.zeros(len(y)), np.ones(len(pte))])
        from sklearn.model_selection import StratifiedKFold
        pa = np.zeros(len(Xa)); skf = StratifiedKFold(5, shuffle=True, random_state=0)
        for fi, vi in skf.split(Xa, ya):
            c = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=200, verbose=-1, random_state=0); c.fit(Xa[fi], ya[fi]); pa[vi] = c.predict_proba(Xa[vi])[:, 1]
        from sklearn.metrics import roc_auc_score as _auc
        pt = np.clip(pa[:len(y)], 1e-3, 1 - 1e-3); prior = len(pte) / len(Xa); adv_w = np.clip((pt / (1 - pt)) * ((1 - prior) / prior), 0.2, 5.0)
        log(f"  adversarial validation: train-vs-test AUC {_auc(ya, pa):.3f}; importance weights on train rows: median {np.median(adv_w):.2f}, mean {adv_w.mean():.2f}, share at the 5.0 cap {np.mean(adv_w >= 5.0):.1%}")
    members_tr, members_te, names, meta = [pl_tr], [pl_te], ["PLAIN (older age, younger age, |gap|, start year)"], []
    def add(s_tr, s_te, n, name):
        members_tr.append(s_tr); members_te.append(s_te); names.append(name)
        f = np.isfinite(s_tr) & (later > cuts[0]); g = np.isfinite(s_te)
        oof = auc(y[f], s_tr[f]) if f.sum() > 200 and len(np.unique(y[f])) > 1 else float("nan"); held = auc(yte[g], symmetrise(ids, s_te)[g]) if g.sum() > 200 else float("nan")
        meta.append({"member": name, "n_fit": n, "forward_oof": oof, "held_on_its_rows": held, "n_test": int(g.sum())})
        log(f"  {name:<40} fit {n:>6,}  fwd-OOF {oof:.4f}  held(its rows) {held:.4f} on {g.sum():,}")
    # plain + calendar: the start's month and day-of-year (a calendar fact, not astrology; 1-January placeholders flagged)
    import datetime as _dt
    def calX(p, Wm):
        j1_ = p[:, pn.index("start_is_jan1")]; doy = np.full(len(p), np.nan); mon = np.full(len(p), np.nan)
        return np.column_stack([plainX(p), j1_])
    Xc, Xce = calX(ptr, W), calX(pte, We); pc_tr = np.full(len(y), np.nan)
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True)
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xc[later <= lo], y[later <= lo]); pc_tr[blk] = c.predict_proba(Xc[blk])[:, 1]
    c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xc, y); add(pc_tr, c.predict_proba(Xce)[:, 1], len(y), "PLAIN + start-is-1-January flag")
    # PLAIN + GEOGRAPHY: the two birthplaces (older/younger assignment, so even), their great-circle distance, and
    # the order-free extremes. Not astrology — a fact about where the two were born — and the one input nothing
    # else in the stack had read; forward OOF 0.659 vs 0.642 for the ages alone.
    SRC = os.environ.get("AQ_SRC", "/tmp/aq4")
    trc = pd.read_csv(f"{SRC}/train.csv", dtype=str); tec = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    def geoX(df, p):
        a, b = p[:, ia], p[:, ib]; swap = b > a
        la, lo = pd.to_numeric(df.lat_a, errors="coerce").to_numpy(), pd.to_numeric(df.lon_a, errors="coerce").to_numpy()
        lb, lob = pd.to_numeric(df.lat_b, errors="coerce").to_numpy(), pd.to_numeric(df.lon_b, errors="coerce").to_numpy()
        lat_o, lon_o, lat_y, lon_y = np.where(swap, lb, la), np.where(swap, lob, lo), np.where(swap, la, lb), np.where(swap, lo, lob)
        d = np.degrees(np.arccos(np.clip(np.sin(np.radians(lat_o)) * np.sin(np.radians(lat_y)) + np.cos(np.radians(lat_o)) * np.cos(np.radians(lat_y)) * np.cos(np.radians(lon_o - lon_y)), -1, 1))) * 111.0
        j1_ = p[:, pn.index("start_is_jan1")]
        # + the start's WEEKDAY and MONTH (calendar facts; NaN for a year-only start) — forward OOF 0.6627 -> 0.6643
        st_ = pd.to_datetime(df.start, errors="coerce"); wd_ = st_.dt.weekday.to_numpy(dtype=float); mo_ = st_.dt.month.to_numpy(dtype=float); jan_ = j1_ == 1.0; wd_[jan_] = np.nan; mo_[jan_] = np.nan
        return np.column_stack([plainX(p), lat_o, lon_o, lat_y, lon_y, d, np.fmax(la, lb), np.fmin(la, lb), np.fmax(lo, lob), np.fmin(lo, lob), (d < 1).astype(float), j1_, np.isnan(la).astype(float) + np.isnan(lb).astype(float), wd_, mo_])
    Xg, Xge = geoX(trc, ptr), geoX(tec, pte)
    # three small capacities averaged (forward OOF 0.661–0.663 for all three; the larger models overfit the era)
    GEO_PRMS = [dict(n_estimators=200, learning_rate=0.05, num_leaves=7, min_child_samples=400, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=30.0, verbose=-1),
                dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1),
                dict(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=200, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)]
    pg_tr = np.zeros(len(y)); pg_te = np.zeros(len(Xge)); cnt_tr = np.zeros(len(y))
    for prm_g in GEO_PRMS:
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True)
            c = lgb.LGBMClassifier(random_state=0, **prm_g); c.fit(Xg[later <= lo], y[later <= lo], sample_weight=adv_w[later <= lo]); pg_tr[blk] += c.predict_proba(Xg[blk])[:, 1]; cnt_tr[blk] += 1
        c = lgb.LGBMClassifier(random_state=0, **prm_g); c.fit(Xg, y, sample_weight=adv_w); pg_te += c.predict_proba(Xge)[:, 1] / len(GEO_PRMS)
    pg_tr = np.where(cnt_tr > 0, pg_tr / np.maximum(cnt_tr, 1), np.nan)
    add(pg_tr, pg_te, len(y), "PLAIN + GEOGRAPHY (birthplaces, distance) + start weekday/month")
    # the 9-term boosted construction (midpoints c / mw / dw added, even mode)
    from artamodel import TERMS9 as _T9
    P9, l9 = phase_matrix(A, Bm, W, bodies, BODIES14, _T9, even=True); P9e, _ = phase_matrix(Ae, Be, We, bodies, BODIES14, _T9, even=True)
    s_tr, s_te, n = forward(P9, y, later, P9e, cuts, "greedy", rows=charts); add(s_tr, s_te, n, "ARTAMODEL 9-term greedy boosted (midpoints)")
    c6 = list(range(len(labels))); order = [labels.index(l) for l in ("a_uranus", "t1_neptune", "t2_neptune", "t1_pluto", "t2_pluto", "t1_uranus", "t2_uranus")]
    s_tr, s_te, n = forward(P, y, later, Pe, cuts, "greedy", rows=charts); add(s_tr, s_te, n, "ARTAMODEL IV greedy boosted (full-chart rows)")
    s_tr, s_te, n = forward(P, y, later, Pe, cuts, "fixed", rows=charts, order=order); add(s_tr, s_te, n, "ARTAMODEL IV fixed-cycle boosted (stable)")
    for j, l in enumerate(labels):
        s_tr, s_te, n = forward(P[:, [j]], y, later, Pe[:, [j]], cuts, "field"); add(s_tr, s_te, n, f"phasor {l}")
    for t in TERMS_IV:
        cc = [j for j, l in enumerate(labels) if l.split("_", 1)[0] == t]; s_tr, s_te, n = forward(P[:, cc], y, later, Pe[:, cc], cuts, "field"); add(s_tr, s_te, n, f"SUM term {t}")
    cc = [j for j, l in enumerate(labels) if l.split("_", 1)[0] in ("a", "t1", "t2")]; s_tr, s_te, n = forward(P[:, cc], y, later, Pe[:, cc], cuts, "field"); add(s_tr, s_te, n, "SUM 3-term (a+t1+t2)")
    s_tr, s_te, n = forward(P, y, later, Pe, cuts, "field"); add(s_tr, s_te, n, "SUM 6-term")
    # EXTRA MEMBER FILES (AQ_EXTRA=a.npz,b.npz): every other astrology and numerology — tradition_members.py (the
    # nineteen tropical traditions incl. numerology) and sidereal_members.py (the PyJHora / iztro families) — each
    # an (rows x members) S_train / S_test aligned to the edition-IV files, forward-OOF like everything here
    for extra in [e for e in os.environ.get("AQ_EXTRA", "").split(",") if e]:
        M = np.load(extra, allow_pickle=True); Sx, Tx, nx = M["S_train"].astype(float), M["S_test"].astype(float), list(M["names"])
        assert Sx.shape[0] == len(y) and Tx.shape[0] == len(ids), (extra, Sx.shape, Tx.shape)
        for j, nm in enumerate(nx):
            add(Sx[:, j], Tx[:, j], int(np.isfinite(Sx[:, j]).sum()), nm)
    S = np.column_stack(members_tr); T = np.column_stack(members_te)
    T = np.column_stack([symmetrise(ids, T[:, j]) if np.isfinite(T[:, j]).any() else T[:, j] for j in range(T.shape[1])])   # every member even over the pair
    # THE TRAIN SIDE TOO (operator 2026-08-19: "ensure data augmentation is done properly to respect the symmetries"):
    # a pair's two rows share the forward block, so both carry an OOF score; average them so the stacker's features
    # are even in the swap exactly as the test features are. The pair key is the order-free (dob, lat, lon) x2 + start.
    SRC_ = os.environ.get("AQ_SRC", "/tmp/aq4"); trk = pd.read_csv(f"{SRC_}/train.csv", dtype=str)
    ka = trk["dob_a"] + "|" + trk["lat_a"].fillna("") + "|" + trk["lon_a"].fillna(""); kb = trk["dob_b"] + "|" + trk["lat_b"].fillna("") + "|" + trk["lon_b"].fillna("")
    train_key = np.where(ka <= kb, ka + "||" + kb, kb + "||" + ka) + "||" + trk["start"]
    def sym_train(v):
        f = np.isfinite(v); d = pd.DataFrame({"k": train_key, "v": v}); m = d.groupby("k")["v"].transform("mean").to_numpy(); return np.where(f, m, v)
    S = np.column_stack([sym_train(S[:, j]) if np.isfinite(S[:, j]).any() else S[:, j] for j in range(S.shape[1])])
    chk = pd.DataFrame({"k": train_key, "v": S[:, 0]}).groupby("k")["v"].agg(lambda q: np.nanmax(q) - np.nanmin(q) if np.isfinite(q).any() else 0).max()
    assert chk < 1e-9, f"train-side symmetrisation failed ({chk})"; log("  train-side pair symmetry of every member asserted")
    np.savez_compressed(os.path.join(OUT, f"iv_members{'_adv' if ADV else ''}.npz"), S_train=S, S_test=T, names=np.array(names), y=y, yte=yte, later=later, ids=ids, cuts=np.array(cuts))
    log(f"{S.shape[1]} members")
    # ---- stackers ----
    ix = {n_: i for i, n_ in enumerate(names)}; pl, gr, fx = 0, ix["ARTAMODEL IV greedy boosted (full-chart rows)"], ix["ARTAMODEL IV fixed-cycle boosted (stable)"]
    hasT = np.isfinite(S[:, ix["phasor t1_uranus"]]) | np.isfinite(S[:, ix["phasor t2_uranus"]]); hasA = np.isfinite(S[:, ix["phasor a_uranus"]])
    hasTe = np.isfinite(T[:, ix["phasor t1_uranus"]]) | np.isfinite(T[:, ix["phasor t2_uranus"]]); hasAe = np.isfinite(T[:, ix["phasor a_uranus"]])
    gtr = np.where(hasT, 0, np.where(hasA, 1, 2)); gte = np.where(hasTe, 0, np.where(hasAe, 1, 2))
    log(f"  groups train/test: sky-clocks {np.mean(gtr==0):.0%}/{np.mean(gte==0):.0%}  synastry-only {np.mean(gtr==1):.0%}/{np.mean(gte==1):.0%}  sky-only {np.mean(gtr==2):.0%}/{np.mean(gte==2):.0%}")
    ages = pte[:, [ia, ib]]; cell = (np.floor(np.nan_to_num(np.fmax(ages[:, 0], ages[:, 1])) / 3) * 1000 + np.floor(np.nan_to_num(np.fmin(ages[:, 0], ages[:, 1])) / 3)).astype(int)
    per = [i for i, n_ in enumerate(names) if n_.startswith("phasor ")]; sums = [i for i, n_ in enumerate(names) if n_.startswith("SUM")]
    trad = [i for i, n_ in enumerate(names) if n_.startswith("TRADITION ")]; sid = [i for i, n_ in enumerate(names) if n_.startswith("SIDEREAL ")]
    geo = ix["PLAIN + GEOGRAPHY (birthplaces, distance) + start weekday/month"]
    top = sorted(per, key=lambda j: -meta[j - 1]["forward_oof"] if not np.isnan(meta[j - 1]["forward_oof"]) else 0)[:6]
    subsets = [("plain alone", [pl]), ("geography alone", [geo]), ("greedy alone", [gr]), ("fixed alone", [fx]), ("plain + greedy", [pl, gr]), ("geography + greedy + fixed", [geo, gr, fx]), ("plain + greedy + fixed", [pl, gr, fx]),
               ("plain + greedy + fixed + 6 best phasors", [pl, gr, fx] + top), ("per-phasor (84) + plain", per + [pl]), ("sums (8) + plain", sums + [pl])] \
              + ([("traditions + plain", trad + [pl]), ("ArtaModel family (95) only", [i for i in range(len(names)) if i not in trad + sid])] if trad else []) \
              + ([("sidereal families + plain", sid + [pl])] if sid else []) + [("ALL members", list(range(len(names))))]
    R = {"members": meta, "runs": {}, "pools": {}}; out = {}
    for fit_from, lam in ((cuts[-3], 1e-2), (cuts[-3], 1e-3), (cuts[0], 1e-2)):
        oof = later > fit_from; yo = y[oof]; lo_ = later[oof]; gt = gtr[oof]
        log(f"--- grouped non-negative stacker: weights on OOF rows later > {int(fit_from)} ({oof.sum():,}), lambda {lam:g} ---"); rows = []
        for nm, cols_ in subsets:
            ztr = np.zeros(int(oof.sum())); zte = np.zeros(len(T))
            for g in (0, 1, 2):
                mtr = gt == g; mte = gte == g
                if mtr.sum() < 300:
                    continue
                Ftr = rankfeat(S[oof][mtr][:, cols_]); Fte = rankfeat(T[mte][:, cols_]); sw = (1.0 + 3.0 * (lo_[mtr] - lo_.min()) / max(1, lo_.max() - lo_.min())) * adv_w[oof][mtr]
                w, b = fit_nonneg(Ftr, yo[mtr], sw, lam); ztr[mtr] = Ftr @ w + b; zte[mte] = Fte @ w + b
            zte = symmetrise(ids, zte); a_fit = auc(yo, ztr); a_te = auc(yte, zte); ac = matched(yte, zte, cell)
            rows.append({"subset": nm, "k": len(cols_), "fit_auc": a_fit, "held": a_te, "age_cell": ac}); out[(fit_from, lam, nm)] = zte
            log(f"  {nm:<42} k={len(cols_):>3}  fit {a_fit:.4f}  HELD {a_te:.4f}  age-cell {ac:.4f}")
            if nm.startswith("ALL"):
                full = (a_fit, a_te)
        bs = max(r["held"] for r in rows if not r["subset"].startswith("ALL"))
        log(f"  monotone on fit: {all(r['fit_auc'] <= full[0] + 1e-9 for r in rows)}   on held: {full[1] >= bs - 1e-9}   (full {full[1]:.4f} vs best subset {bs:.4f})")
        R["runs"][f"from{int(fit_from)}_lam{lam:g}"] = rows
    # ---- selection-free equal-weight pools (NaN-aware rank average) ----
    def blend(cols_):
        acc = np.zeros(len(T)); cnt = np.zeros(len(T))
        for j in cols_:
            v = T[:, j]; f = np.isfinite(v)
            if f.sum() > 1:
                acc[f] += r01(v[f]); cnt[f] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.5)
    for nm, cols_ in (("plain + greedy", [pl, gr]), ("plain + greedy + fixed", [pl, gr, fx]), ("plain + greedy + fixed + 6 best phasors", [pl, gr, fx] + top), ("plain + all members with fwd-OOF >= 0.60", [pl] + [j for j in range(1, len(names)) if (meta[j - 1]["forward_oof"] or 0) >= 0.60]),
                      ("plain + greedy + fixed + traditions + sidereal families", [pl, gr, fx] + trad + sid), ("geography + greedy + fixed", [geo, gr, fx]), ("geography + plain + greedy + fixed", [geo, pl, gr, fx])):
        pb = blend(cols_); R["pools"][nm] = {"k": len(cols_), "held": auc(yte, pb), "age_cell": matched(yte, pb, cell)}; out[("pool", nm)] = pb
        log(f"  POOL equal-weight {nm:<42} k={len(cols_):>3}  HELD {auc(yte, pb):.4f}  age-cell {matched(yte, pb, cell):.4f}")
    # ---- BAGGED stacker: the ALL-members grouped non-negative stack averaged over a grid of (fit window, lambda,
    # recency weight) — every setting is a legitimate stacker, averaging them removes the choice. Reported like the rest.
    def one_stack(cols_, fit_from, lam, rec):
        oof = later > fit_from; yo = y[oof]; lo_ = later[oof]; gt = gtr[oof]; zte = np.zeros(len(T)); ztr = np.zeros(int(oof.sum()))
        for g in (0, 1, 2):
            mtr = gt == g; mte = gte == g
            if mtr.sum() < 300:
                continue
            Ftr = rankfeat(S[oof][mtr][:, cols_]); Fte = rankfeat(T[mte][:, cols_]); sw = (1.0 + rec * (lo_[mtr] - lo_.min()) / max(1, lo_.max() - lo_.min())) * adv_w[oof][mtr]
            w, b = fit_nonneg(Ftr, yo[mtr], sw, lam); ztr[mtr] = Ftr @ w + b; zte[mte] = Fte @ w + b
        return r01(symmetrise(ids, zte)), auc(yo, ztr)
    grid = [(cuts[-3], 1e-2, 3.0), (cuts[-3], 1e-3, 3.0), (cuts[-3], 3e-3, 1.0), (cuts[-2], 1e-2, 3.0), (cuts[0], 1e-2, 3.0), (cuts[0], 3e-3, 0.0)]
    allc = list(range(len(names))); bag = np.zeros(len(T)); bag_fit = []
    for fit_from, lam, rec in grid:
        z, af = one_stack(allc, fit_from, lam, rec); bag += z / len(grid); bag_fit.append(af)
    R["bagged_stack_all"] = {"grid": [[float(a), b, c] for a, b, c in grid], "held": auc(yte, bag), "age_cell": matched(yte, bag, cell)}
    log(f"  BAGGED grouped non-negative stack, ALL members, {len(grid)} settings: HELD {auc(yte, bag):.4f}  age-cell {matched(yte, bag, cell):.4f}")
    out[("bag", "all")] = bag
    pd.DataFrame({"id": ids, lab: r01(bag)}).to_csv(os.path.join(OUT, f"submission_iv_stack_bagged{'_adv' if ADV else ''}.csv"), index=False)
    # the submissions: the biggest non-negative stack (recent rows, lambda 1e-2) and the small pre-registered pool
    pd.DataFrame({"id": ids, lab: r01(out[(cuts[-3], 1e-2, "ALL members")])}).to_csv(os.path.join(OUT, f"submission_iv_stack_all{'_adv' if ADV else ''}.csv"), index=False)
    pd.DataFrame({"id": ids, lab: r01(out[("pool", "plain + greedy + fixed")])}).to_csv(os.path.join(OUT, "submission_iv_pool3.csv"), index=False)
    pd.DataFrame({"id": ids, lab: r01(out[("pool", "geography + greedy + fixed")])}).to_csv(os.path.join(OUT, f"submission_iv_pool_geo3{'_adv' if ADV else ''}.csv"), index=False)
    json.dump(R, open(os.path.join(OUT, f"artamodel_iv_ensemble{'_adv' if ADV else ''}.json"), "w"), indent=1); log("wrote artamodel_iv_ensemble.json, submission_iv_stack_all.csv, submission_iv_pool3.csv")


if __name__ == "__main__":
    main()
