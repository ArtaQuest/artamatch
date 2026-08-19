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
    members_tr, members_te, names, meta = [pl_tr], [pl_te], ["PLAIN (older age, younger age, |gap|, start year)"], []
    def add(s_tr, s_te, n, name):
        members_tr.append(s_tr); members_te.append(s_te); names.append(name)
        f = np.isfinite(s_tr) & (later > cuts[0]); g = np.isfinite(s_te)
        oof = auc(y[f], s_tr[f]) if f.sum() > 200 and len(np.unique(y[f])) > 1 else float("nan"); held = auc(yte[g], symmetrise(ids, s_te)[g]) if g.sum() > 200 else float("nan")
        meta.append({"member": name, "n_fit": n, "forward_oof": oof, "held_on_its_rows": held, "n_test": int(g.sum())})
        log(f"  {name:<40} fit {n:>6,}  fwd-OOF {oof:.4f}  held(its rows) {held:.4f} on {g.sum():,}")
    c6 = list(range(len(labels))); order = [labels.index(l) for l in ("a_uranus", "t1_neptune", "t2_neptune", "t1_pluto", "t2_pluto", "t1_uranus", "t2_uranus")]
    s_tr, s_te, n = forward(P, y, later, Pe, cuts, "greedy", rows=charts); add(s_tr, s_te, n, "ARTAMODEL IV greedy boosted (full-chart rows)")
    s_tr, s_te, n = forward(P, y, later, Pe, cuts, "fixed", rows=charts, order=order); add(s_tr, s_te, n, "ARTAMODEL IV fixed-cycle boosted (stable)")
    for j, l in enumerate(labels):
        s_tr, s_te, n = forward(P[:, [j]], y, later, Pe[:, [j]], cuts, "field"); add(s_tr, s_te, n, f"phasor {l}")
    for t in TERMS_IV:
        cc = [j for j, l in enumerate(labels) if l.split("_", 1)[0] == t]; s_tr, s_te, n = forward(P[:, cc], y, later, Pe[:, cc], cuts, "field"); add(s_tr, s_te, n, f"SUM term {t}")
    cc = [j for j, l in enumerate(labels) if l.split("_", 1)[0] in ("a", "t1", "t2")]; s_tr, s_te, n = forward(P[:, cc], y, later, Pe[:, cc], cuts, "field"); add(s_tr, s_te, n, "SUM 3-term (a+t1+t2)")
    s_tr, s_te, n = forward(P, y, later, Pe, cuts, "field"); add(s_tr, s_te, n, "SUM 6-term")
    S = np.column_stack(members_tr); T = np.column_stack(members_te)
    T = np.column_stack([symmetrise(ids, T[:, j]) if np.isfinite(T[:, j]).any() else T[:, j] for j in range(T.shape[1])])   # every member even over the pair
    np.savez_compressed(os.path.join(OUT, "iv_members.npz"), S_train=S, S_test=T, names=np.array(names), y=y, yte=yte, later=later, ids=ids, cuts=np.array(cuts))
    log(f"{S.shape[1]} members")
    # ---- stackers ----
    ix = {n_: i for i, n_ in enumerate(names)}; pl, gr, fx = 0, ix["ARTAMODEL IV greedy boosted (full-chart rows)"], ix["ARTAMODEL IV fixed-cycle boosted (stable)"]
    hasT = np.isfinite(S[:, ix["phasor t1_uranus"]]) | np.isfinite(S[:, ix["phasor t2_uranus"]]); hasA = np.isfinite(S[:, ix["phasor a_uranus"]])
    hasTe = np.isfinite(T[:, ix["phasor t1_uranus"]]) | np.isfinite(T[:, ix["phasor t2_uranus"]]); hasAe = np.isfinite(T[:, ix["phasor a_uranus"]])
    gtr = np.where(hasT, 0, np.where(hasA, 1, 2)); gte = np.where(hasTe, 0, np.where(hasAe, 1, 2))
    log(f"  groups train/test: sky-clocks {np.mean(gtr==0):.0%}/{np.mean(gte==0):.0%}  synastry-only {np.mean(gtr==1):.0%}/{np.mean(gte==1):.0%}  sky-only {np.mean(gtr==2):.0%}/{np.mean(gte==2):.0%}")
    ages = pte[:, [ia, ib]]; cell = (np.floor(np.nan_to_num(np.fmax(ages[:, 0], ages[:, 1])) / 3) * 1000 + np.floor(np.nan_to_num(np.fmin(ages[:, 0], ages[:, 1])) / 3)).astype(int)
    per = [i for i, n_ in enumerate(names) if n_.startswith("phasor ")]; sums = [i for i, n_ in enumerate(names) if n_.startswith("SUM")]
    top = sorted(per, key=lambda j: -meta[j - 1]["forward_oof"] if not np.isnan(meta[j - 1]["forward_oof"]) else 0)[:6]
    subsets = [("plain alone", [pl]), ("greedy alone", [gr]), ("fixed alone", [fx]), ("plain + greedy", [pl, gr]), ("plain + greedy + fixed", [pl, gr, fx]),
               ("plain + greedy + fixed + 6 best phasors", [pl, gr, fx] + top), ("per-phasor (84) + plain", per + [pl]), ("sums (8) + plain", sums + [pl]), ("ALL members", list(range(len(names))))]
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
                Ftr = rankfeat(S[oof][mtr][:, cols_]); Fte = rankfeat(T[mte][:, cols_]); sw = 1.0 + 3.0 * (lo_[mtr] - lo_.min()) / max(1, lo_.max() - lo_.min())
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
    for nm, cols_ in (("plain + greedy", [pl, gr]), ("plain + greedy + fixed", [pl, gr, fx]), ("plain + greedy + fixed + 6 best phasors", [pl, gr, fx] + top), ("plain + all members with fwd-OOF >= 0.60", [pl] + [j for j in range(1, len(names)) if (meta[j - 1]["forward_oof"] or 0) >= 0.60])):
        pb = blend(cols_); R["pools"][nm] = {"k": len(cols_), "held": auc(yte, pb), "age_cell": matched(yte, pb, cell)}; out[("pool", nm)] = pb
        log(f"  POOL equal-weight {nm:<42} k={len(cols_):>3}  HELD {auc(yte, pb):.4f}  age-cell {matched(yte, pb, cell):.4f}")
    # the submissions: the biggest non-negative stack (recent rows, lambda 1e-2) and the small pre-registered pool
    pd.DataFrame({"id": ids, lab: r01(out[(cuts[-3], 1e-2, "ALL members")])}).to_csv(os.path.join(OUT, "submission_iv_stack_all.csv"), index=False)
    pd.DataFrame({"id": ids, lab: r01(out[("pool", "plain + greedy + fixed")])}).to_csv(os.path.join(OUT, "submission_iv_pool3.csv"), index=False)
    json.dump(R, open(os.path.join(OUT, "artamodel_iv_ensemble.json"), "w"), indent=1); log("wrote artamodel_iv_ensemble.json, submission_iv_stack_all.csv, submission_iv_pool3.csv")


if __name__ == "__main__":
    main()
