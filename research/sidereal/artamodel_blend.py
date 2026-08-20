"""
artamodel_blend.py — the boosted sum models fitted on EVERY available row, added to the 141 full-stack members, then
stacked / rank-blended, with every choice made on train out-of-fold scores (the test read is a readout, never a selector).

Members added here (each OOF over two temporal halves on train; fitted on all its rows for test):
  BOOST6 charts  -- the deployed construction: 6-term greedy boosted split fields, rows with BOTH full natal charts
  BOOST6 any     -- the same on every row with at least one 6-term phasor (the presence rule zeroes the rest)
  BOOST9 any     -- the 9-term version (c / mw / dw added) on every row with at least one phasor
Usage: AQ_OUT=/tmp/aq3feat python artamodel_blend.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from artamodel import BODIES14, TERMS, TERMS9, auc, phase_matrix   # noqa: E402
from artamodel_deploy import boost_recorded, score                 # noqa: E402
from artamodel_full_stack import matched                           # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat")
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)


def boosted_member(P, y, later, Pte, rows, stages=80):
    ok = rows; n = int(ok.sum()); s_tr = np.full(len(P), np.nan); s_te = np.full(len(Pte), np.nan)
    Pk, Y, L = P[ok], y[ok], later[ok]; order = np.argsort(L); half = np.zeros(n, bool); half[order[n // 2:]] = True
    oof_all = np.full(len(P), np.nan)
    for h in (False, True):
        fit = half == h; lf = L[fit]; inner = lf > np.quantile(lf, 0.85)
        m = boost_recorded(Pk[fit], Y[fit], inner, stages=stages, nu=0.1)
        # score EVERY train row not in this fit (inside and outside the member's population): the stacker needs a
        # score wherever the presence rule gives one
        oth = np.ones(len(P), bool); oth[np.where(ok)[0][fit]] = False
        sc = score(m, P[oth]); tmp = oof_all[oth]; tmp = np.where(np.isnan(tmp), sc, (tmp + sc) / 2); oof_all[oth] = tmp
    inner = L > np.quantile(L, 0.85); m = boost_recorded(Pk, Y, inner, stages=stages, nu=0.1)
    s_te = score(m, Pte)
    # rows outside the population that carry no phasor at all score the constant F0 -> NaN them (no information)
    has_tr = np.isfinite(P).any(1); has_te = np.isfinite(Pte).any(1)
    oof_all[~has_tr] = np.nan; s_te[~has_te] = np.nan
    return oof_all, s_te, n, m["inner_auc"], len(m["stages"])


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True); M = np.load(os.path.join(OUT, "fullstack_members.npz"), allow_pickle=True)
    Str, Ste, names, y, yte, later, ids = M["S_train"], M["S_test"], list(M["names"]), M["y"], M["yte"], M["later"], M["ids"]
    bodies = list(Z["bodies"]); Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]
    Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    j1 = ptr[:, pn.index("start_year_only")] == 1.0; j1e = pte[:, pn.index("start_year_only")] == 1.0
    Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    B = [bodies.index(b) for b in BODIES14]
    charts = np.isfinite(Dtr[:, B]).all(1) & np.isfinite(Mtr[:, B]).all(1)
    P6, l6 = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, TERMS); P6e, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, TERMS)
    P9, l9 = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, TERMS9); P9e, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, TERMS9)
    ages_te = pte[:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]
    cell = (np.floor(np.nan_to_num(ages_te[:, 0]) / 3) * 1000 + np.floor(np.nan_to_num(ages_te[:, 1]) / 3)).astype(int)
    cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
    R = {"members": [], "stacks": {}, "blends": {}}
    extra_tr, extra_te, extra_names = [], [], []
    for nm, P, Pe, rows in (("BOOST6 charts (deployed construction)", P6, P6e, charts),
                            ("BOOST6 any-phasor rows", P6, P6e, np.isfinite(P6).any(1)),
                            ("BOOST9 any-phasor rows", P9, P9e, np.isfinite(P9).any(1))):
        s_tr, s_te, n, iv, st = boosted_member(P, y, later, Pe, rows)
        fin = np.isfinite(s_te); a = auc(yte[fin], s_te[fin]); ac = matched(yte[fin], s_te[fin], cell[fin])
        ftr = np.isfinite(s_tr); oof = auc(y[ftr], s_tr[ftr])
        R["members"].append({"member": nm, "n_train": n, "stages": st, "inner": iv, "train_oof": oof, "held_on_scored_rows": a, "n_test_scored": int(fin.sum()), "age_cell_matched": ac})
        log(f"  {nm:<40} rows {n:>6,}  stages {st:>3}  inner {iv:.4f}  train-OOF {oof:.4f}  held {a:.4f} on {fin.sum():,} test rows  age-cell {ac:.4f}")
        extra_tr.append(s_tr); extra_te.append(s_te); extra_names.append(nm)
    Xtr = np.column_stack([Str] + extra_tr).astype(np.float32); Xte = np.column_stack([Ste] + extra_te).astype(np.float32)
    allnames = names + extra_names
    np.savez_compressed(os.path.join(OUT, "fullstack_members_plus.npz"), S_train=Xtr, S_test=Xte, names=np.array(allnames), y=y, yte=yte, later=later, ids=ids)

    # ---- stacks: selection by train OOF of the STACKER (temporal split of the member OOF scores) ----
    sel_fit = later <= np.quantile(later, 0.80); sel_val = ~sel_fit
    def stack(Xa, Xb, name, params):
        pv = np.zeros(int(sel_val.sum())); p = np.zeros(len(Xb))
        for sd in range(3):
            c = lgb.LGBMClassifier(random_state=sd, verbose=-1, **params)
            c.fit(Xa[sel_fit], y[sel_fit]); pv += c.predict_proba(Xa[sel_val])[:, 1]
            c = lgb.LGBMClassifier(random_state=sd, verbose=-1, **params); c.fit(Xa, y); p += c.predict_proba(Xb)[:, 1]
        sel = auc(y[sel_val], pv / 3); held = auc(yte, p / 3); ac = matched(yte, p / 3, cell)
        R["stacks"][name] = {"train_oof_selector": sel, "held": held, "age_cell_matched": ac}
        log(f"  {name:<70} selector(train OOF) {sel:.4f}   held {held:.4f}   age-cell {ac:.4f}")
        return p / 3
    P_REG = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=100, colsample_bytree=0.6, subsample=0.8, subsample_freq=1, reg_lambda=10.0)
    P_LOOSE = dict(n_estimators=800, learning_rate=0.03, num_leaves=31, min_child_samples=50, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=1.0)
    P_TIGHT = dict(n_estimators=300, learning_rate=0.02, num_leaves=7, min_child_samples=300, colsample_bytree=0.5, subsample=0.7, subsample_freq=1, reg_lambda=30.0)
    ex = slice(len(names), len(allnames))
    out = {}
    out["boosted only (3) + plain"] = stack(np.column_stack([Xtr[:, ex], ptr[:, cols]]), np.column_stack([Xte[:, ex], pte[:, cols]]), "STACK boosted members (3) + plain", P_REG)
    out["all 144 + plain (reg)"] = stack(np.column_stack([Xtr, ptr[:, cols]]), np.column_stack([Xte, pte[:, cols]]), "STACK all 144 members + plain  [regularised]", P_REG)
    out["all 144 + plain (loose)"] = stack(np.column_stack([Xtr, ptr[:, cols]]), np.column_stack([Xte, pte[:, cols]]), "STACK all 144 members + plain  [loose]", P_LOOSE)
    out["all 144 + plain (tight)"] = stack(np.column_stack([Xtr, ptr[:, cols]]), np.column_stack([Xte, pte[:, cols]]), "STACK all 144 members + plain  [tight]", P_TIGHT)
    out["all 144 no plain"] = stack(Xtr, Xte, "STACK all 144 members, no plain", P_REG)
    out["plain"] = stack(ptr[:, cols], pte[:, cols], "REFERENCE plain columns alone", P_REG)

    # ---- rank blends (no fitting): top-k members by TRAIN OOF, equal-weight rank average, NaN-aware ----
    oofs = np.array([auc(y[np.isfinite(Xtr[:, j])], Xtr[np.isfinite(Xtr[:, j]), j]) if np.isfinite(Xtr[:, j]).sum() > 500 else 0.5 for j in range(Xtr.shape[1])])
    order = np.argsort(-oofs)
    def rankblend(cols_, Xm):
        acc = np.zeros(len(Xm)); cnt = np.zeros(len(Xm))
        for j in cols_:
            v = Xm[:, j]; f = np.isfinite(v)
            if f.sum() < 2: continue
            acc[f] += r01(v[f]); cnt[f] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.5)
    log("  top members by train OOF: " + "; ".join(f"{allnames[j]} {oofs[j]:.4f}" for j in order[:8]))
    for k in (1, 3, 5, 10, 20):
        cols_ = order[:k]; sel = auc(y[sel_val], rankblend(cols_, Xtr[sel_val])); pb = rankblend(cols_, Xte)
        R["blends"][f"top{k}"] = {"members": [allnames[j] for j in cols_], "train_oof_selector": sel, "held": auc(yte, pb), "age_cell_matched": matched(yte, pb, cell)}
        log(f"  RANK-BLEND top-{k:<2} by train OOF        selector {sel:.4f}   held {auc(yte, pb):.4f}   age-cell {matched(yte, pb, cell):.4f}")
    # the deployed leaderboard submission itself (already scored 0.631 on the board) blended with the best stack
    dep = pd.read_csv("/tmp/aq3sub/submission_artamodel6.csv").set_index("id").loc[ids].iloc[:, 0].to_numpy()
    for w in (0.5, 0.7):
        pb = w * r01(dep) + (1 - w) * r01(out["all 144 + plain (reg)"])
        R["blends"][f"deployed{w}+stack"] = {"held": auc(yte, pb), "age_cell_matched": matched(yte, pb, cell)}
        log(f"  BLEND {w:.1f}·deployed-6-term + {1-w:.1f}·stack(all+plain)     held {auc(yte, pb):.4f}   age-cell {matched(yte, pb, cell):.4f}   (readout only — no selector)")
    # choose the submission by the SELECTOR among the stacks
    best = max(R["stacks"].items(), key=lambda kv: kv[1]["train_oof_selector"])
    log(f"  selector picks: {best[0]}  (train OOF {best[1]['train_oof_selector']:.4f}, held {best[1]['held']:.4f})")
    key = {"STACK boosted members (3) + plain": "boosted only (3) + plain", "STACK all 144 members + plain  [regularised]": "all 144 + plain (reg)",
           "STACK all 144 members + plain  [loose]": "all 144 + plain (loose)", "STACK all 144 members + plain  [tight]": "all 144 + plain (tight)",
           "STACK all 144 members, no plain": "all 144 no plain", "REFERENCE plain columns alone": "plain"}[best[0]]
    pd.DataFrame({"id": ids, "lasted_30_years": r01(out[key])}).to_csv(os.path.join(OUT, "submission_blend_selected.csv"), index=False)
    R["selected"] = best[0]
    json.dump(R, open(os.path.join(OUT, "artamodel_blend.json"), "w"), indent=1)
    log(f"wrote {OUT}/artamodel_blend.json, submission_blend_selected.csv")


if __name__ == "__main__":
    main()
