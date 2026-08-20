"""
artamodel_full_stack.py — the full ArtaModel stack: per-body single models PLUS the sum models PLUS the aspect grids,
every member fitted on the rows it has, out-of-fold, stacked.

Arash, 2026-08-19: "the per body models are in addition to the sum models. so aspects would be there too."

MEMBERS (each a coherent field |b + Σ w z|² with a logistic head, early-stopped on the inner temporal split of its
OWN population, train scores out-of-fold over two temporal halves, test scores from a fit on all its rows):
  per-phasor   126 single-phasor models (9 terms x 14 bodies)                       -- artamodel_split_models.py
  per-term     9 sums over the 14 bodies of one term, e.g. |b + Σ_i a_i e^{i(θm_i − θd_i)}|²: the cross-body
               interference terms cos(φ_i − φ_j) inside the square are the aspects between the phasors
  formula      the 3-term (a+m+d), 6-term and 9-term sums over all bodies
  aspect grids the classical inter-body aspects written out explicitly: SYN θm_i − θd_j for all i ≠ j (182
               phasors), WM θt_i − θm_j, WD θt_i − θd_j -- the whole synastry and transit grids as sums
The stacker is LightGBM over all member scores (NaN where a member has nothing for the couple) with and without
the plain columns; held out read once beside the age-cell-matched control.

Usage: AQ_PHASES=/tmp/aq3feat/phases.npz AQ_SOL=/tmp/aq3comp/solution.csv AQ_OUT=/tmp/aq3feat python artamodel_full_stack.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from artamodel import BODIES14, TERMS9, TERMS, auc, phase_matrix             # noqa: E402
from coherent_fit import Coherent                                             # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz")
SOL = os.environ.get("AQ_SOL", "/tmp/aq3comp/solution.csv")
OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat")
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


def matched(y, s, cell):
    num = den = 0.0
    for b in np.unique(cell):
        m = cell == b; n1, n0 = int(y[m].sum()), int((1 - y[m]).sum())
        if n1 and n0:
            num += auc(y[m], s[m]) * n1 * n0; den += n1 * n0
    return num / den if den else float("nan")


def _fit(P, Y, inner, seed=0):
    C = np.nan_to_num(np.cos(np.radians(P))); S = np.nan_to_num(np.sin(np.radians(P)))
    m = Coherent(C.shape[1], 1, seed=seed); rng = np.random.default_rng(seed); idx = np.where(~inner)[0]
    bs = int(min(1024, max(32, len(idx) // 16))); best, state, bad = -1.0, None, 0
    for ep in range(120):
        rng.shuffle(idx)
        for s0 in range(0, len(idx), bs):
            b = idx[s0:s0 + bs]
            if len(b) >= 16:
                m.step(C[b], S[b], Y[b].astype(float), 0.01, 1e-3)
        a = auc(Y[inner], m.logit(C[inner], S[inner])[0]) if inner.sum() > 20 else 0.5
        if a > best + 1e-5:
            best, bad = a, 0; state = (m.A1.copy(), m.A2.copy(), m.br.copy(), m.bi.copy(), m.w.copy(), m.c, m.mu.copy(), m.sd.copy())
        else:
            bad += 1
            if bad >= 12:
                break
    m.A1, m.A2, m.br, m.bi, m.w, m.c, m.mu, m.sd = state
    return m, best


def member(P, y, later, Pte, name, min_rows=300):
    """One stack member on the rows where ANY of its phasors exists: OOF train scores (two temporal halves) and
    test scores (fit on all its rows). Missing phasors inside a row contribute zero (the presence rule)."""
    ok = np.isfinite(P).any(1); oke = np.isfinite(Pte).any(1); n = int(ok.sum())
    s_tr = np.full(len(P), np.nan); s_te = np.full(len(Pte), np.nan)
    if n < min_rows or len(np.unique(y[ok])) < 2:
        return s_tr, s_te, n, float("nan")
    Pk, Y, L = P[ok], y[ok], later[ok]; order = np.argsort(L); half = np.zeros(n, bool); half[order[n // 2:]] = True
    for h in (False, True):
        fit = half == h; oth = ~fit; lf = L[fit]; inner = lf > np.quantile(lf, 0.85)
        m, _ = _fit(Pk[fit], Y[fit], inner)
        Co = np.nan_to_num(np.cos(np.radians(Pk[oth]))); So = np.nan_to_num(np.sin(np.radians(Pk[oth])))
        tmp = np.full(n, np.nan); tmp[oth] = m.logit(Co, So)[0]; s_tr[np.where(ok)[0][oth]] = tmp[oth]
    inner = L > np.quantile(L, 0.85); m, best = _fit(Pk, Y, inner)
    s_te[oke] = m.logit(np.nan_to_num(np.cos(np.radians(Pte[oke]))), np.nan_to_num(np.sin(np.radians(Pte[oke]))))[0]
    return s_tr, s_te, n, best


def grid(A, B, bodies_idx):
    """Inter-body phase differences A_i − B_j for all i != j -> (n, 182) and labels."""
    cols, lab = [], []
    for i in bodies_idx:
        for j in bodies_idx:
            if i == j: continue
            cols.append(A[:, i] - B[:, j]); lab.append(f"{BODIES14[bodies_idx.index(i)]}-{BODIES14[bodies_idx.index(j)]}")
    return np.column_stack(cols), lab


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True)
    bodies = list(Z["bodies"]); ids = Z["id_test"]; y = Z["y_train"].astype(np.int64)
    Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]
    Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    later = Z["yr_train"].astype(int).max(1)
    sol = pd.read_csv(SOL).set_index("id"); lab = [c for c in sol.columns if c != "Usage"][0]
    yte = sol.loc[ids, lab].to_numpy().astype(int)
    j1 = ptr[:, pn.index("start_year_only")] == 1.0; j1e = pte[:, pn.index("start_year_only")] == 1.0
    Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    P, labels = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, TERMS9); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, TERMS9)
    B = [bodies.index(b) for b in BODIES14]
    members_tr, members_te, names, meta = [], [], [], []

    def add(Ptr_, Pte_, name):
        s_tr, s_te, n, iv = member(Ptr_, y, later, Pte_, name)
        members_tr.append(s_tr); members_te.append(s_te); names.append(name)
        a = auc(yte[np.isfinite(s_te)], s_te[np.isfinite(s_te)]) if np.isfinite(s_te).sum() > 100 else float("nan")
        meta.append({"member": name, "phasors": int(Ptr_.shape[1]), "n_train": n, "inner": iv, "held_on_its_rows": a, "n_test": int(np.isfinite(s_te).sum())})
        log(f"  {name:<46} phasors {Ptr_.shape[1]:>4}  rows {n:>6,}  inner {iv if np.isnan(iv) else round(iv,4)}  held(on its rows) {a if np.isnan(a) else round(a,4)}")

    # per-phasor (126)
    for j, l in enumerate(labels):
        add(P[:, [j]], Pe[:, [j]], f"phasor {l}")
    # per-term sums (9)
    for t in TERMS9:
        cols = [j for j, l in enumerate(labels) if l.split("_", 1)[0] == t]
        add(P[:, cols], Pe[:, cols], f"SUM term {t} over 14 bodies")
    # formula sums
    for sub, nm in ((("a", "m", "d"), "3-term"), (TERMS, "6-term"), (TERMS9, "9-term")):
        cols = [j for j, l in enumerate(labels) if l.split("_", 1)[0] in sub]
        add(P[:, cols], Pe[:, cols], f"SUM {nm} over all bodies")
    # aspect grids
    G, gl = grid(Mtr, Dtr, B); Ge, _ = grid(Mte, Dte, B); add(G, Ge, "ASPECTS synastry grid θm_i − θd_j (i≠j)")
    G, gl = grid(Wtr, Mtr, B); Ge, _ = grid(Wte, Mte, B); add(G, Ge, "ASPECTS wedding→mom grid θt_i − θm_j")
    G, gl = grid(Wtr, Dtr, B); Ge, _ = grid(Wte, Dte, B); add(G, Ge, "ASPECTS wedding→dad grid θt_i − θd_j")
    Str = np.column_stack(members_tr).astype(np.float32); Ste = np.column_stack(members_te).astype(np.float32)
    log(f"{Str.shape[1]} members")
    np.savez_compressed(os.path.join(OUT, "fullstack_members.npz"), S_train=Str, S_test=Ste, names=np.array(names), y=y, yte=yte, later=later, ids=ids)
    ages_te = pte[:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]
    cell = (np.floor(np.nan_to_num(ages_te[:, 0]) / 3) * 1000 + np.floor(np.nan_to_num(ages_te[:, 1]) / 3)).astype(int)
    cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
    R = {"members": meta}
    def stack(Xtr, Xte, name):
        p = np.zeros(len(Xte))
        for sd in range(3):
            c = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=100, colsample_bytree=0.6,
                                   subsample=0.8, subsample_freq=1, reg_lambda=10.0, random_state=sd, verbose=-1)
            c.fit(Xtr, y); p += c.predict_proba(Xte)[:, 1]
        p /= 3; R[name] = {"held": auc(yte, p), "age_cell_matched": matched(yte, p, cell)}
        log(f"  {name:<58} held {auc(yte, p):.4f}   age-cell-matched {matched(yte, p, cell):.4f}")
        return p
    per = [i for i, n in enumerate(names) if n.startswith("phasor ")]; sums = [i for i, n in enumerate(names) if n.startswith("SUM")]
    asp = [i for i, n in enumerate(names) if n.startswith("ASPECTS")]
    stack(Str[:, per], Ste[:, per], "STACK per-phasor only (126)")
    stack(Str[:, sums], Ste[:, sums], "STACK sum models only (12)")
    stack(Str[:, asp], Ste[:, asp], "STACK aspect grids only (3)")
    stack(Str, Ste, "STACK all members (per-phasor + sums + aspects)")
    p_all = stack(np.column_stack([Str, ptr[:, cols]]), np.column_stack([Ste, pte[:, cols]]), "STACK all members + plain columns")
    stack(ptr[:, cols], pte[:, cols], "REFERENCE plain columns alone")
    r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)
    pd.DataFrame({"id": ids, lab: r01(p_all)}).to_csv(os.path.join(OUT, "submission_fullstack.csv"), index=False)
    json.dump(R, open(os.path.join(OUT, "artamodel_full_stack.json"), "w"), indent=1)
    log(f"wrote {OUT}/artamodel_full_stack.json and submission_fullstack.csv")


if __name__ == "__main__":
    main()
