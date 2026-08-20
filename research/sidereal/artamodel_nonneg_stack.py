"""
artamodel_nonneg_stack.py — the monotone ensemble: NON-NEGATIVE weights over rank-transformed member scores.

Arash, 2026-08-19: "a bigger ensemble must always be better than its subset of members." With weights constrained
>= 0 and a convex objective, every subset is a feasible point of the full problem (zero the rest), so on the data
the weights are fitted on the full pool can never lose to a subset — monotone BY CONSTRUCTION. Whether that carries
to the held-out era is then a measured fact, printed per subset.

Members: the 144 forward-OOF members of artamodel_stack_forward.py (+ a stable 6-phasor coherent field on the
deployed model's phasors) + the plain LightGBM (forward OOF the same way). Feature = the member's rank among the
rows it scores (centred, so an absent member casts no vote). Objective: logistic loss, L2 on the weights, rows
weighted toward recency (the test is the next era). Subsets refitted the same way for the monotonicity table.
Usage: AQ_OUT=/tmp/aq3feat python artamodel_nonneg_stack.py
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
from artamodel import BODIES14, TERMS, auc, phase_matrix            # noqa: E402
from artamodel_full_stack import _fit, matched                      # noqa: E402
from artamodel_stack_forward import forward_member, cuts_of         # noqa: E402

OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat"); PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz")
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)
DEPLOYED_PHASORS = ("a_uranus", "d_pluto", "d_neptune", "d_uranus", "m_pluto", "m_saturn")


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
        w, b = th[:m], th[m]; z = F @ w + b
        l = np.logaddexp(0, -yy * z); p = 1 / (1 + np.exp(-yy * z))
        g = -(yy * (1 - p)) * sw
        return float(np.sum(sw * l) / sw.sum() + lam * w @ w), np.concatenate([F.T @ g / sw.sum() + 2 * lam * w, [g.sum() / sw.sum()]])
    r = minimize(obj, np.zeros(m + 1), jac=True, method="L-BFGS-B", bounds=[(0, None)] * m + [(None, None)], options={"maxiter": 3000})
    return r.x[:m], r.x[m]


def main():
    import lightgbm as lgb
    M = np.load(os.path.join(OUT, "forward_members.npz"), allow_pickle=True)
    S, T, names, y, yte, later, ids = M["S_train"].astype(float), M["S_test"].astype(float), list(M["names"]), M["y"], M["yte"], M["later"], M["ids"]
    cuts = list(M["cuts"])
    Z = np.load(PH, allow_pickle=True); ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    bodies = list(Z["bodies"]); Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]
    Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    j1 = ptr[:, pn.index("start_year_only")] == 1.0; j1e = pte[:, pn.index("start_year_only")] == 1.0
    Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    P, labels = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, TERMS); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, TERMS)
    dcols = [labels.index(l) for l in DEPLOYED_PHASORS]
    s_tr, s_te, nfit, _ = forward_member(P[:, dcols], y, later, Pe[:, dcols], cuts)
    S = np.column_stack([S, s_tr]); T = np.column_stack([T, s_te]); names.append("FIELD on the deployed model's 6 phasors")
    g = np.isfinite(s_te); log(f"  stable 6-phasor field: fit rows {nfit:,}  held {auc(yte[g], s_te[g]):.4f}")
    # plain LightGBM, forward OOF
    cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
    X, Xe = ptr[:, cols], pte[:, cols]; pl_tr = np.full(len(y), np.nan)
    prm = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=100, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=10.0, verbose=-1)
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True)
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(X[later <= lo], y[later <= lo]); pl_tr[blk] = c.predict_proba(X[blk])[:, 1]
    c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(X, y); pl_te = c.predict_proba(Xe)[:, 1]
    S = np.column_stack([S, pl_tr]); T = np.column_stack([T, pl_te]); names.append("PLAIN LightGBM (two ages, gap, year)")
    log(f"  plain LightGBM: held {auc(yte, pl_te):.4f}")
    oof = later > cuts[0]; Ftr = rankfeat(S[oof]); Fte = rankfeat(T); yo = y[oof]; lo_ = later[oof]
    ages_te = pte[:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]
    cell = (np.floor(np.nan_to_num(ages_te[:, 0]) / 3) * 1000 + np.floor(np.nan_to_num(ages_te[:, 1]) / 3)).astype(int)
    sw_rec = 1.0 + 3.0 * (lo_ - lo_.min()) / (lo_.max() - lo_.min()); sw_uni = np.ones(len(yo))
    ix = {n: i for i, n in enumerate(names)}
    dep = ix["BOOST6 full-chart rows (deployed construction)"]; fld = ix["FIELD on the deployed model's 6 phasors"]; pl = ix["PLAIN LightGBM (two ages, gap, year)"]
    per = [i for i, n in enumerate(names) if n.startswith("phasor ")]; sums = [i for i, n in enumerate(names) if n.startswith("SUM")]
    asp = [i for i, n in enumerate(names) if n.startswith("ASPECTS")]; boo = [i for i, n in enumerate(names) if n.startswith("BOOST")]
    strong6 = [ix[n] for n in ("phasor d_neptune", "phasor d_pluto", "phasor d_uranus", "phasor a_uranus", "SUM term d over 14 bodies", "SUM 3-term over all bodies")]
    subsets = [("plain alone", [pl]), ("deployed alone", [dep]), ("deployed + plain", [dep, pl]), ("deployed + stable field + plain", [dep, fld, pl]),
               ("deployed + plain + 6 strongest", [dep, pl] + strong6), ("per-phasor (126) + plain", per + [pl]), ("sums (12) + plain", sums + [pl]),
               ("aspect grids (3) + plain", asp + [pl]), ("boosted (3) + field + plain", boo + [fld, pl]), ("all 146 members, no plain", [i for i in range(len(names)) if i != pl]),
               ("ALL 147 (everything)", list(range(len(names))))]
    R = {"members": names, "runs": {}}; best_sub = None
    for lam, swn, sw in ((1e-3, "recency", sw_rec), (1e-3, "uniform", sw_uni), (1e-2, "recency", sw_rec), (1e-4, "recency", sw_rec)):
        log(f"--- lambda {lam:g}, row weights {swn} ---")
        rows = []
        for nm, cols_ in subsets:
            w, b = fit_nonneg(Ftr[:, cols_], yo, sw, lam); ztr = Ftr[:, cols_] @ w + b; zte = Fte[:, cols_] @ w + b
            a_fit = auc(yo, ztr); a_last = auc(yo[lo_ > cuts[-2]], ztr[lo_ > cuts[-2]]); a_te = auc(yte, zte); ac = matched(yte, zte, cell)
            nz = int((w > 1e-6).sum()); rows.append({"subset": nm, "k": len(cols_), "nonzero": nz, "fit_auc": a_fit, "last_block_auc": a_last, "held": a_te, "age_cell": ac})
            log(f"  {nm:<36} k={len(cols_):>3} nz={nz:>3}  fit {a_fit:.4f}  last-block {a_last:.4f}  HELD {a_te:.4f}  age-cell {ac:.4f}")
            if nm.startswith("ALL"):
                full = (a_fit, a_te, zte, w)
        mono_fit = all(r["fit_auc"] <= full[0] + 1e-9 for r in rows); mono_held = all(r["held"] <= full[1] + 1e-9 for r in rows)
        log(f"  monotone on the fit data: {mono_fit}   monotone on held-out: {mono_held}   (full {full[1]:.4f} vs best subset {max(r['held'] for r in rows if not r['subset'].startswith('ALL')):.4f})")
        top = np.argsort(-full[3])[:12]; log("  full-pool weights: " + "; ".join(f"{names[j][:30]} {full[3][j]:.3f}" for j in top if full[3][j] > 1e-6))
        R["runs"][f"lam{lam:g}_{swn}"] = {"rows": rows, "monotone_fit": mono_fit, "monotone_held": mono_held, "weights": {names[j]: float(full[3][j]) for j in range(len(names)) if full[3][j] > 1e-6}}
        if lam == 1e-3 and swn == "recency":
            pd.DataFrame({"id": ids, "lasted_30_years": r01(full[2])}).to_csv(os.path.join(OUT, "submission_nonneg_all.csv"), index=False)
    json.dump(R, open(os.path.join(OUT, "artamodel_nonneg_stack.json"), "w"), indent=1)
    log(f"wrote {OUT}/artamodel_nonneg_stack.json, submission_nonneg_all.csv (lambda 1e-3, recency)")


if __name__ == "__main__" and not os.environ.get("AQ_GROUPED"):
    main()


def grouped():
    """Non-negative stacker fitted SEPARATELY per availability pattern (rows with dad+wedding clocks / synastry
    only / wedding sky only), so the weights are not tuned to train's mixture of patterns."""
    import lightgbm as lgb
    M = np.load(os.path.join(OUT, "forward_members.npz"), allow_pickle=True)
    S, T, names, y, yte, later, ids = M["S_train"].astype(float), M["S_test"].astype(float), list(M["names"]), M["y"], M["yte"], M["later"], M["ids"]
    cuts = list(M["cuts"]); Z = np.load(PH, allow_pickle=True); ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
    X, Xe = ptr[:, cols], pte[:, cols]; pl_tr = np.full(len(y), np.nan)
    prm = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=100, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=10.0, verbose=-1)
    for k in range(1, len(cuts)):
        lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True)
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(X[later <= lo], y[later <= lo]); pl_tr[blk] = c.predict_proba(X[blk])[:, 1]
    c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(X, y); pl_te = c.predict_proba(Xe)[:, 1]
    S = np.column_stack([S, pl_tr]); T = np.column_stack([T, pl_te]); names.append("PLAIN LightGBM (two ages, gap, year)")
    ix = {n: i for i, n in enumerate(names)}; pl = ix["PLAIN LightGBM (two ages, gap, year)"]; dep = ix["BOOST6 full-chart rows (deployed construction)"]
    oof = later > cuts[0]; yo = y[oof]; lo_ = later[oof]
    has_d = lambda A: np.isfinite(A[:, ix["phasor d_uranus"]]); has_a = lambda A: np.isfinite(A[:, ix["phasor a_uranus"]])
    def groups(A):
        d, a = has_d(A), has_a(A); return np.where(d, 0, np.where(a, 1, 2))
    gtr, gte = groups(S[oof]), groups(T)
    ages_te = pte[:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]
    cell = (np.floor(np.nan_to_num(ages_te[:, 0]) / 3) * 1000 + np.floor(np.nan_to_num(ages_te[:, 1]) / 3)).astype(int)
    print(f"  groups (train OOF / test): dad+wedding clocks {np.mean(gtr==0):.0%}/{np.mean(gte==0):.0%}  synastry only {np.mean(gtr==1):.0%}/{np.mean(gte==1):.0%}  wedding sky only {np.mean(gtr==2):.0%}/{np.mean(gte==2):.0%}")
    per = [i for i, n in enumerate(names) if n.startswith("phasor ")]; sums = [i for i, n in enumerate(names) if n.startswith("SUM")]
    strong6 = [ix[n] for n in ("phasor d_neptune", "phasor d_pluto", "phasor d_uranus", "phasor a_uranus", "SUM term d over 14 bodies", "SUM 3-term over all bodies")]
    subsets = [("plain alone", [pl]), ("deployed alone", [dep]), ("deployed + plain", [dep, pl]), ("deployed + plain + 6 strongest", [dep, pl] + strong6),
               ("per-phasor (126) + plain", per + [pl]), ("sums (12) + plain", sums + [pl]), ("ALL 146 (everything)", list(range(len(names))))]
    R = json.load(open(os.path.join(OUT, "artamodel_nonneg_stack.json"))); R["grouped"] = {}
    for lam in (1e-3, 1e-2):
        print(f"--- GROUPED non-negative stacker, lambda {lam:g}, recency-weighted ---")
        rows = []
        for nm, cols_ in subsets:
            ztr = np.zeros(int(oof.sum())); zte = np.zeros(len(T))
            for gidx in (0, 1, 2):
                mtr = gtr == gidx; mte = gte == gidx
                if mtr.sum() < 300:
                    continue
                Ftr = rankfeat(S[oof][mtr][:, cols_]); Fte = rankfeat(T[mte][:, cols_])
                sw = 1.0 + 3.0 * (lo_[mtr] - lo_.min()) / (lo_.max() - lo_.min())
                w, b = fit_nonneg(Ftr, yo[mtr], sw, lam); ztr[mtr] = Ftr @ w + b; zte[mte] = Fte @ w + b
            # the three groups are joined on the logit scale: a shared intercept per group is what the per-group
            # fit gives; AUC across groups then reads the group base rates of TRAIN — say so in the read-out
            a_fit = auc(yo, ztr); a_te = auc(yte, zte); ac = matched(yte, zte, cell)
            within = [auc(yte[gte == g_], zte[gte == g_]) for g_ in (0, 1, 2) if (gte == g_).sum() > 200 and len(np.unique(yte[gte == g_])) > 1]
            rows.append({"subset": nm, "k": len(cols_), "fit_auc": a_fit, "held": a_te, "age_cell": ac, "held_within_groups": within})
            print(f"  {nm:<34} k={len(cols_):>3}  fit {a_fit:.4f}  HELD {a_te:.4f}  age-cell {ac:.4f}  held within groups {' / '.join(f'{v:.4f}' for v in within)}")
            if nm.startswith("ALL"):
                full = (a_fit, a_te, zte)
        print(f"  monotone on fit: {all(r['fit_auc'] <= full[0] + 1e-9 for r in rows)}   on held: {all(r['held'] <= full[1] + 1e-9 for r in rows)}   (full {full[1]:.4f} vs best subset {max(r['held'] for r in rows if not r['subset'].startswith('ALL')):.4f})")
        R["grouped"][f"lam{lam:g}"] = rows
        if lam == 1e-3:
            pd.DataFrame({"id": ids, "lasted_30_years": r01(full[2])}).to_csv(os.path.join(OUT, "submission_nonneg_grouped.csv"), index=False)
    json.dump(R, open(os.path.join(OUT, "artamodel_nonneg_stack.json"), "w"), indent=1)


if __name__ == "__main__" and os.environ.get("AQ_GROUPED"):
    grouped()
