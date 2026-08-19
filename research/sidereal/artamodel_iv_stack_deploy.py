"""
artamodel_iv_stack_deploy.py — the deployed EDITION-IV STACK: the model that leads the public board (0.64303).

    stack = grouped non-negative weights over the RANKS of three members:
      GEO   plain + geography  (older age, younger age, |gap|, start year, the two birthplaces, their distance; 3 small LightGBMs averaged)
      AM-G  ArtaModel IV, greedy boosted over split single-phasor fields (the deployed construction)
      AM-F  ArtaModel IV, the same phasors in a FIXED cycle (the stable twin)
    weights per availability group (0: the wedding sky clocks exist · 1: synastry only · 2: sky only), fitted on
    the forward-chained train OOF (rows later > the 0.70 quantile, recency-weighted, L2 1e-3) — exactly the
    configuration submitted; members REFITTED on train + test for deployment (operator: the deployed model is
    trained on all the data); every member score is averaged over the two orders of the pair.
Writes AQ_OUT/stack_iv_deployed.json (+ geo_lgbm_{0,1,2}.txt), and checks that the scorer path reproduces the
held-out AUC of the submission. Usage: AQ_OUT=/tmp/aq4sub/deploy python artamodel_iv_stack_deploy.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from artamodel import BODIES14, TERMS_IV, auc, phase_matrix                 # noqa: E402
from artamodel_deploy import boost_recorded, score, BODY_TEXT                # noqa: E402
from artamodel_ensemble import Field, cs                                     # noqa: E402
from artamodel_iv import symmetrise, TERM_TEXT_IV                            # noqa: E402
from artamodel_iv_ensemble import rankfeat, fit_nonneg                       # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq4feat/phases.npz"); SRC = os.environ.get("AQ_SRC", "/tmp/aq4"); SOL = os.environ.get("AQ_SOL", "/tmp/aq4comp/solution.csv")
MEM = os.environ.get("AQ_MEMBERS", "/tmp/aq4sub/iv_members.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq4sub/deploy")
DEPLOYED_PHASORS = ("a_uranus", "t1_neptune", "t2_neptune", "t1_pluto", "t2_pluto", "t1_uranus", "t2_uranus")
GEO_PRMS = [dict(n_estimators=200, learning_rate=0.05, num_leaves=7, min_child_samples=400, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=30.0, verbose=-1),
            dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1),
            dict(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=200, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)]
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)


def boost_recorded_fixed(P, y, inner, order, rounds=6, nu=0.1, seed=0):
    """boost_recorded with the phasor of each stage FIXED (order cycled) — every stage recorded the same way."""
    C, S = cs(P); K = C.shape[1]; fit = ~inner
    p0 = np.clip(y[fit].mean(), 1e-3, 1 - 1e-3); F0 = float(np.log(p0 / (1 - p0))); F = np.full(len(y), F0); rec = []; best, best_n, bad = -1.0, 0, 0
    for k in range(rounds * len(order)):
        j = order[k % len(order)]; p = 1 / (1 + np.exp(-F)); r = y - p; mask = np.zeros(K); mask[j] = 1.0
        f = Field(K, seed * 1000 + k, mask).fit(C[fit], S[fit], r[fit], C[inner], S[inner], r[inner]) if inner.any() else Field(K, seed * 1000 + k, mask).fit(C[fit], S[fit], r[fit], C[fit][:64], S[fit][:64], r[fit][:64])
        h = f.predict(C, S); bg, bl = 0.0, np.inf
        for gam in (0.25, 0.5, 1.0, 2.0, 4.0):
            Fx = F[fit] + nu * gam * h[fit]; loss = float(np.mean(np.logaddexp(0, -Fx * (2 * y[fit] - 1))))
            if loss < bl:
                bl, bg = loss, gam
        F = F + nu * bg * h
        rec.append({"stage": k + 1, "phasor": int(j), "step": nu * bg, "alpha": float(f.alpha), "c": float(f.c), "w_re": float(f.A1[j]), "w_im": float(-f.A2[j]), "b_re": float(f.br), "b_im": float(f.bi)})
        if inner.any():
            a = auc(y[inner], F[inner])
            if a > best + 1e-5:
                best, best_n, bad = a, k + 1, 0
            else:
                bad += 1
                if bad >= 2 * len(order):
                    break
    return {"F0": F0, "stages": rec[:best_n] if inner.any() else rec, "inner_auc": best if inner.any() else None}


def geo_features(ages_a, ages_b, la, lo, lb, lob, start_year, start_is_jan1):
    """The geography member's 16 inputs, even in the swap: older/younger assignment by age, order-free extremes."""
    swap = ages_b > ages_a
    lat_o, lon_o, lat_y, lon_y = np.where(swap, lb, la), np.where(swap, lob, lo), np.where(swap, la, lb), np.where(swap, lo, lob)
    d = np.degrees(np.arccos(np.clip(np.sin(np.radians(lat_o)) * np.sin(np.radians(lat_y)) + np.cos(np.radians(lat_o)) * np.cos(np.radians(lat_y)) * np.cos(np.radians(lon_o - lon_y)), -1, 1))) * 111.0
    return np.column_stack([np.fmax(ages_a, ages_b), np.fmin(ages_a, ages_b), np.abs(ages_a - ages_b), start_year, lat_o, lon_o, lat_y, lon_y, d, np.fmax(la, lb), np.fmin(la, lb), np.fmax(lo, lob), np.fmin(lo, lob), (d < 1).astype(float), start_is_jan1, np.isnan(la).astype(float) + np.isnan(lb).astype(float)])


def main():
    import lightgbm as lgb
    os.makedirs(OUT, exist_ok=True)
    Z = np.load(PH, allow_pickle=True); s1, s2 = list(Z["slots"]); bodies = list(Z["bodies"]); ids = Z["id_test"]; y = Z["y_train"].astype(np.int64)
    A, Bm, W = Z[f"theta_{s1}_train"], Z[f"theta_{s2}_train"], Z["theta_wed_train"]; Ae, Be, We = Z[f"theta_{s1}_test"], Z[f"theta_{s2}_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); later = Z["yr_train"].astype(int).max(1)
    sol = pd.read_csv(SOL).set_index("id"); yte = sol.loc[ids, "lasted_30_years"].to_numpy().astype(int)
    j1 = ptr[:, pn.index("start_is_jan1")] == 1.0; j1e = pte[:, pn.index("start_is_jan1")] == 1.0; W = W.copy(); We = We.copy(); W[j1] = np.nan; We[j1e] = np.nan
    B = [bodies.index(b) for b in BODIES14]; charts = np.isfinite(A[:, B]).all(1) & np.isfinite(Bm[:, B]).all(1); charts_te = np.isfinite(Ae[:, B]).all(1) & np.isfinite(Be[:, B]).all(1)
    P, labels = phase_matrix(A, Bm, W, bodies, BODIES14, TERMS_IV, even=True); Pe, _ = phase_matrix(Ae, Be, We, bodies, BODIES14, TERMS_IV, even=True)
    order = [labels.index(l) for l in DEPLOYED_PHASORS]
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    num = lambda df, c: pd.to_numeric(df[c], errors="coerce").to_numpy()
    ia, ib, iy, ij = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year"), pn.index("start_is_jan1")
    Xg = geo_features(ptr[:, ia], ptr[:, ib], num(tr, "lat_a"), num(tr, "lon_a"), num(tr, "lat_b"), num(tr, "lon_b"), ptr[:, iy], ptr[:, ij])
    Xge = geo_features(pte[:, ia], pte[:, ib], num(te, "lat_a"), num(te, "lon_a"), num(te, "lat_b"), num(te, "lon_b"), pte[:, iy], pte[:, ij])
    # ---- the stacker weights: from the saved forward-OOF member matrix, exactly the submitted configuration ----
    M = np.load(MEM, allow_pickle=True); S, names, cuts = M["S_train"], list(M["names"]), list(M["cuts"]); ix = {n: i for i, n in enumerate(names)}
    cols = [ix["PLAIN + GEOGRAPHY (birthplaces, distance)"], ix["ARTAMODEL IV greedy boosted (full-chart rows)"], ix["ARTAMODEL IV fixed-cycle boosted (stable)"]]
    hasT = np.isfinite(S[:, ix["phasor t1_uranus"]]) | np.isfinite(S[:, ix["phasor t2_uranus"]]); hasA = np.isfinite(S[:, ix["phasor a_uranus"]]); gtr = np.where(hasT, 0, np.where(hasA, 1, 2))
    oof = later > cuts[-3]; yo = y[oof]; lo_ = later[oof]; gt = gtr[oof]; weights = {}
    for g in (0, 1, 2):
        mtr = gt == g
        if mtr.sum() < 300:
            continue
        Ftr = rankfeat(S[oof][mtr][:, cols]); sw = 1.0 + 3.0 * (lo_[mtr] - lo_.min()) / max(1, lo_.max() - lo_.min()); w, b = fit_nonneg(Ftr, yo[mtr], sw, 1e-3)
        weights[str(g)] = {"w": [float(x) for x in w], "b": float(b), "n_fit": int(mtr.sum())}
        log(f"  group {g}: weights GEO {w[0]:.3f}  AM-greedy {w[1]:.3f}  AM-fixed {w[2]:.3f}  bias {b:+.3f}  ({mtr.sum():,} OOF rows)")
    # ---- members refitted on train + test ----
    Xall = np.vstack([Xg, Xge]); yall_g = np.concatenate([y, yte]); geo_models = []
    for k, prm in enumerate(GEO_PRMS):
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xall, yall_g); c.booster_.save_model(os.path.join(OUT, f"geo_lgbm_{k}.txt")); geo_models.append(c)
    geo_te = np.mean([c.predict_proba(Xge)[:, 1] for c in geo_models], axis=0)
    Pall = np.vstack([P[charts], Pe[charts_te]]); yall = np.concatenate([y[charts], yte[charts_te]])
    lat = later[charts]; inner = lat > np.quantile(lat, 0.85)
    g_lb = boost_recorded(P[charts], y[charts], inner, stages=4 * len(labels), nu=0.1); g_dep = boost_recorded(Pall, yall, np.zeros(len(yall), bool), stages=len(g_lb["stages"]), nu=0.1)
    f_lb = boost_recorded_fixed(P[charts], y[charts], inner, order); f_dep = boost_recorded_fixed(Pall, yall, np.zeros(len(yall), bool), order, rounds=max(1, int(np.ceil(len(f_lb["stages"]) / len(order)))))
    f_dep["stages"] = f_dep["stages"][:len(f_lb["stages"])]
    log(f"  ArtaModel greedy: {len(g_dep['stages'])} stages on {len(yall):,} rows · fixed-cycle: {len(f_dep['stages'])} stages")
    am_g_te = score(g_dep, Pe); am_f_te = score(f_dep, Pe)
    # ---- rank reference grids: quantiles of each member's deployed scores over the rows it scores (the test-era population) ----
    qs = np.linspace(0, 1, 201)
    def grid(v):
        v = v[np.isfinite(v)]; return [float(x) for x in np.quantile(v, qs)]
    ref = {"GEO": grid(geo_te), "AM_GREEDY": grid(am_g_te[np.isfinite(Pe).any(1)]), "AM_FIXED": grid(am_f_te[np.isfinite(Pe).any(1)])}
    # ---- the scorer path on the test rows: does it reproduce the held-out AUC? ----
    def rank_of(v, g_):
        g_ = np.asarray(g_); return np.interp(v, g_, qs)
    hasTe = np.isfinite(Pe[:, labels.index("t1_uranus")]) | np.isfinite(Pe[:, labels.index("t2_uranus")]); hasAe = np.isfinite(Pe[:, labels.index("a_uranus")]); gte = np.where(hasTe, 0, np.where(hasAe, 1, 2))
    zte = np.zeros(len(ids))
    for g in (0, 1, 2):
        m = gte == g
        if not m.any() or str(g) not in weights:
            continue
        F = np.column_stack([rank_of(geo_te[m], ref["GEO"]) - 0.5, np.where(np.isfinite(am_g_te[m]) & (np.isfinite(Pe[m]).any(1)), rank_of(am_g_te[m], ref["AM_GREEDY"]) - 0.5, 0.0),
                             np.where(np.isfinite(am_f_te[m]) & (np.isfinite(Pe[m]).any(1)), rank_of(am_f_te[m], ref["AM_FIXED"]) - 0.5, 0.0)])
        zte[m] = F @ np.array(weights[str(g)]["w"]) + weights[str(g)]["b"]
    zsym = symmetrise(ids, zte); held = auc(yte, zsym)
    log(f"  scorer path on the test rows (members fitted on train+test): held-out AUC {held:.4f}  (the submitted stack: 0.6448 held, 0.64303 public)")
    dep = {"edition": "IV — genderless, even", "model": "grouped non-negative stack of ranks: GEO + ArtaModel IV greedy + ArtaModel IV fixed-cycle",
           "members": {"GEO": {"what": "plain + geography: older age, younger age, |gap|, start year, birthplaces (older/younger), great-circle distance, order-free extremes, same-place flag, start-is-1-January, missing-place count",
                               "files": [f"geo_lgbm_{k}.txt" for k in range(3)], "feature_names": ["age_older", "age_younger", "age_gap_abs", "start_year", "lat_older", "lon_older", "lat_younger", "lon_younger", "distance_km", "lat_max", "lat_min", "lon_max", "lon_min", "same_place", "start_is_jan1", "n_missing_places"], "fitted_on": f"train + test rows ({len(yall_g):,})"},
                       "AM_GREEDY": {**g_dep, "labels": labels, "fitted_on": f"train + test full-chart rows ({len(yall):,})"},
                       "AM_FIXED": {**f_dep, "labels": labels, "order": list(DEPLOYED_PHASORS), "fitted_on": f"train + test full-chart rows ({len(yall):,})"}},
           "rank_reference": {"quantiles": [float(q) for q in qs], **ref}, "stacker": {"groups": {"0": "wedding-sky clocks exist (t1/t2 Uranus)", "1": "synastry only (a Uranus)", "2": "wedding sky only"}, "weights": weights, "note": "logit = Σ w·(rank − 0.5) + b per group; member absent → rank term 0; weights fitted on forward-chained train OOF (later > 1867, recency-weighted, L2 1e-3); the two orders of a pair are averaged"},
           "phase_convention": {"zodiac": "sidereal, Lahiri", "engine": "Kerykeion 5.12.9", "birth_time": "09:00 local", "wedding_time": "12:00 UT", "even": "|Δθ| in [0°,180°]"},
           "scores": {"public_board": 0.64303, "held_out_submitted": 0.6448, "held_out_scorer_path": float(held)}, "terms": {t: TERM_TEXT_IV[t] for t in TERMS_IV}, "bodies": BODIES14}
    json.dump(dep, open(os.path.join(OUT, "stack_iv_deployed.json"), "w"), indent=1); log(f"wrote {OUT}/stack_iv_deployed.json + geo_lgbm_0..2.txt")


if __name__ == "__main__":
    main()
