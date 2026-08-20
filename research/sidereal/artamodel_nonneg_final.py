"""
artamodel_nonneg_final.py — grouped non-negative stacker with a STABLE deployed member.

The greedy boosted member changes its phasor set between forward folds (≤1823 picks only d_neptune), so its OOF
did not represent the model that scores the test. BOOST6-FIXED runs the deployed model's six phasors in a fixed
cycle (a_uranus d_pluto d_neptune d_uranus m_pluto m_saturn), same model in every fold. Weights are fitted per
availability group (dad+wedding clocks / synastry only / wedding sky only) with non-negative coefficients, on the
two most recent forward blocks (1867–1900), L2 1e-3. Subset table = the monotonicity check.
Usage: AQ_OUT=/tmp/aq3feat python artamodel_nonneg_final.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from artamodel import BODIES14, TERMS, auc, phase_matrix                  # noqa: E402
from artamodel_ensemble import Field, cs                                  # noqa: E402
from artamodel_full_stack import matched                                  # noqa: E402
from artamodel_nonneg_stack import rankfeat, fit_nonneg, DEPLOYED_PHASORS  # noqa: E402

OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat"); PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz")
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)


def boost_fixed(P, y, inner, order, rounds=6, nu=0.1, seed=0):
    C, S = cs(P); K = C.shape[1]; fit = ~inner
    p0 = np.clip(y[fit].mean(), 1e-3, 1 - 1e-3); F = np.full(len(y), float(np.log(p0 / (1 - p0)))); rec = []
    best, best_n, bad = -1.0, 0, 0
    for k in range(rounds * len(order)):
        j = order[k % len(order)]; p = 1 / (1 + np.exp(-F)); r = y - p; mask = np.zeros(K); mask[j] = 1.0
        f = Field(K, seed * 1000 + k, mask).fit(C[fit], S[fit], r[fit], C[inner], S[inner], r[inner])
        h = f.predict(C, S); bg, bl = 0.0, np.inf
        for gam in (0.25, 0.5, 1.0, 2.0, 4.0):
            Fx = F[fit] + nu * gam * h[fit]; loss = float(np.mean(np.logaddexp(0, -Fx * (2 * y[fit] - 1))))
            if loss < bl:
                bl, bg = loss, gam
        F = F + nu * bg * h; rec.append((f, nu * bg))
        a = auc(y[inner], F[inner])
        if a > best + 1e-5:
            best, best_n, bad = a, k + 1, 0
        else:
            bad += 1
            if bad >= 2 * len(order):
                break
    rec = rec[:best_n]; F0 = float(np.log(p0 / (1 - p0)))
    def predict(Q):
        Cq, Sq = cs(Q); z = np.full(len(Q), F0)
        for f, step in rec:
            z = z + step * f.predict(Cq, Sq)
        return z
    return predict


def main():
    import lightgbm as lgb
    M = np.load(os.path.join(OUT, "forward_members.npz"), allow_pickle=True)
    S, T, names, y, yte, later, ids = M["S_train"].astype(float), M["S_test"].astype(float), list(M["names"]), M["y"], M["yte"], M["later"], M["ids"]
    cuts = list(M["cuts"]); Z = np.load(PH, allow_pickle=True); ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    bodies = list(Z["bodies"]); Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]; Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    j1 = ptr[:, pn.index("start_year_only")] == 1.0; j1e = pte[:, pn.index("start_year_only")] == 1.0; Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    P, labels = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, TERMS); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, TERMS)
    order = [labels.index(l) for l in DEPLOYED_PHASORS]; B = [bodies.index(b) for b in BODIES14]
    charts = np.isfinite(Dtr[:, B]).all(1) & np.isfinite(Mtr[:, B]).all(1); has = np.isfinite(P).any(1); has_te = np.isfinite(Pe).any(1)
    # BOOST6-FIXED, forward OOF, fitted on full-chart rows (as deployed)
    s_tr = np.full(len(y), np.nan); s_te = np.full(len(Pe), np.nan)
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]; blk = has & (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); fm = charts & (later <= lo)
        L = later[fm]; pred = boost_fixed(P[fm], y[fm], L > np.quantile(L, 0.85), order); s_tr[blk] = pred(P[blk])
    L = later[charts]; pred = boost_fixed(P[charts], y[charts], L > np.quantile(L, 0.85), order); s_te[has_te] = pred(Pe[has_te])
    log(f"  BOOST6-FIXED: held {auc(yte[has_te], s_te[has_te]):.4f} on {has_te.sum():,} test rows")
    S = np.column_stack([S, s_tr]); T = np.column_stack([T, s_te]); names.append("BOOST6-FIXED (deployed phasors, fixed cycle)")
    # plain LightGBM forward
    cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]; X, Xe = ptr[:, cols], pte[:, cols]; pl_tr = np.full(len(y), np.nan)
    prm = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=100, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=10.0, verbose=-1)
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(X[later <= lo], y[later <= lo]); pl_tr[blk] = c.predict_proba(X[blk])[:, 1]
    c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(X, y); pl_te = c.predict_proba(Xe)[:, 1]
    S = np.column_stack([S, pl_tr]); T = np.column_stack([T, pl_te]); names.append("PLAIN LightGBM (two ages, gap, year)")
    ix = {n: i for i, n in enumerate(names)}; pl = ix["PLAIN LightGBM (two ages, gap, year)"]; dep = ix["BOOST6 full-chart rows (deployed construction)"]; fx = ix["BOOST6-FIXED (deployed phasors, fixed cycle)"]
    gtr = np.where(np.isfinite(S[:, ix["phasor d_uranus"]]), 0, np.where(np.isfinite(S[:, ix["phasor a_uranus"]]), 1, 2)); gte = np.where(np.isfinite(T[:, ix["phasor d_uranus"]]), 0, np.where(np.isfinite(T[:, ix["phasor a_uranus"]]), 1, 2))
    ages_te = pte[:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]; cell = (np.floor(np.nan_to_num(ages_te[:, 0]) / 3) * 1000 + np.floor(np.nan_to_num(ages_te[:, 1]) / 3)).astype(int)
    for g in (0, 1):
        f = (later > cuts[-3]) & (gtr == g); print(f"  group {g}: OOF(1867-1900) deployed {auc(y[f], S[f, dep]):.4f}  FIXED {auc(y[f], S[f, fx]):.4f}  plain {auc(y[f], S[f, pl]):.4f}   | test deployed {auc(yte[gte==g], T[gte==g, dep]):.4f}  FIXED {auc(yte[gte==g], T[gte==g, fx]):.4f}  plain {auc(yte[gte==g], T[gte==g, pl]):.4f}")
    per = [i for i, n in enumerate(names) if n.startswith("phasor ")]; sums = [i for i, n in enumerate(names) if n.startswith("SUM")]
    strong6 = [ix[n] for n in ("phasor d_neptune", "phasor d_pluto", "phasor d_uranus", "phasor a_uranus", "SUM term d over 14 bodies", "SUM 3-term over all bodies")]
    subsets = [("plain alone", [pl]), ("deployed alone", [dep]), ("FIXED alone", [fx]), ("deployed + FIXED + plain", [dep, fx, pl]), ("deployed + FIXED + plain + 6 strongest", [dep, fx, pl] + strong6),
               ("per-phasor (126) + plain", per + [pl]), ("sums (12) + plain", sums + [pl]), ("ALL 147 (everything)", list(range(len(names))))]
    R = {"runs": {}}
    for fit_from, lam in ((cuts[-3], 1e-3), (cuts[-3], 1e-2), (cuts[0], 1e-3)):
        oof = later > fit_from; yo = y[oof]; lo_ = later[oof]; gt = gtr[oof]
        log(f"--- grouped non-negative, weights fitted on OOF rows later > {int(fit_from)} ({oof.sum():,} rows), lambda {lam:g} ---")
        rows = []
        for nm, cols_ in subsets:
            ztr = np.zeros(int(oof.sum())); zte = np.zeros(len(T))
            for g in (0, 1, 2):
                mtr = gt == g; mte = gte == g
                if mtr.sum() < 300:
                    continue
                Ftr = rankfeat(S[oof][mtr][:, cols_]); Fte = rankfeat(T[mte][:, cols_]); sw = 1.0 + 3.0 * (lo_[mtr] - lo_.min()) / max(1, lo_.max() - lo_.min())
                w, b = fit_nonneg(Ftr, yo[mtr], sw, lam); ztr[mtr] = Ftr @ w + b; zte[mte] = Fte @ w + b
            a_fit = auc(yo, ztr); a_te = auc(yte, zte); ac = matched(yte, zte, cell); within = [auc(yte[gte == g_], zte[gte == g_]) for g_ in (0, 1)]
            rows.append({"subset": nm, "k": len(cols_), "fit_auc": a_fit, "held": a_te, "age_cell": ac, "held_within": within})
            log(f"  {nm:<40} k={len(cols_):>3}  fit {a_fit:.4f}  HELD {a_te:.4f}  age-cell {ac:.4f}  within d/a {within[0]:.4f}/{within[1]:.4f}")
            if nm.startswith("ALL"):
                full = (a_fit, a_te, zte)
        bs = max(r["held"] for r in rows if not r["subset"].startswith("ALL"))
        log(f"  monotone on fit: {all(r['fit_auc'] <= full[0] + 1e-9 for r in rows)}   on held: {full[1] >= bs - 1e-9}   (full {full[1]:.4f} vs best subset {bs:.4f})")
        R["runs"][f"from{int(fit_from)}_lam{lam:g}"] = rows
        if fit_from == cuts[-3] and lam == 1e-3:
            pd.DataFrame({"id": ids, "lasted_30_years": r01(full[2])}).to_csv(os.path.join(OUT, "submission_nonneg_final.csv"), index=False)
    np.savez_compressed(os.path.join(OUT, "forward_members_final.npz"), S_train=S, S_test=T, names=np.array(names), y=y, yte=yte, later=later, ids=ids, cuts=np.array(cuts))
    json.dump(R, open(os.path.join(OUT, "artamodel_nonneg_final.json"), "w"), indent=1); log("wrote artamodel_nonneg_final.json, submission_nonneg_final.csv")


if __name__ == "__main__":
    main()
