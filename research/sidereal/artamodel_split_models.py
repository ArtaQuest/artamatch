"""
artamodel_split_models.py — one single-sum model per (term, body), each trained on the rows where its phasor
exists, stacked.

Arash, 2026-08-19: "ensure each model is trained with the data that is available. for example the dad's natal model
should be trained with almost all the data since missing dad natals is rare. also train per body model
|b + a_i e^{i(θm_i − θd_i)}|, and again for day-missing cases only train the outer planets."

So: for every phasor j of the nine-term model (a m d mn dn tn c mw dw × 14 bodies = 126), a field
u_j = |b_j + w_j e^{iφ_j}|² with its own logistic head, fitted on EVERY training row where φ_j exists -- the
precision-aware NaNs already say which: a year-only birth has only its slow bodies, a year-only wedding no wedding
sky, an absent partner nothing. Each model's early stopping uses the inner temporal split of ITS OWN population.
Train-side scores are OUT-OF-FOLD (two temporal halves) so the stacker never sees an in-sample score; a LightGBM
stacker then combines the 126 scores (NaN where a phasor is absent for the couple) -- with and without the plain
columns -- and everything is read on the held-out half once, beside the age-cell-matched control.

Usage: AQ_PHASES=/tmp/aq3feat/phases.npz AQ_SOL=/tmp/aq3comp/solution.csv AQ_OUT=/tmp/aq3feat python artamodel_split_models.py
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
from artamodel import BODIES14, TERMS9, TERMS, ArtaModel, auc, phase_matrix       # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz")
SOL = os.environ.get("AQ_SOL", "/tmp/aq3comp/solution.csv")
OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat")
T0 = time.time()
SLOW = {"jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "true_south_node", "chiron", "mean_lilith"}


def log(*a):
    print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


def matched(y, s, cell):
    num = den = 0.0
    for b in np.unique(cell):
        m = cell == b; n1, n0 = int(y[m].sum()), int((1 - y[m]).sum())
        if n1 and n0:
            num += auc(y[m], s[m]) * n1 * n0; den += n1 * n0
    return num / den if den else float("nan")


def one_model(p, y, later, pte, seed=0):
    """A K=1 field on this phasor's own rows: returns (train scores out-of-fold, test scores, n_rows, inner auc)."""
    ok = np.isfinite(p); n = int(ok.sum())
    s_tr = np.full(len(p), np.nan); s_te = np.full(len(pte), np.nan)
    if n < 300 or len(np.unique(y[ok])) < 2:
        return s_tr, s_te, n, float("nan")
    P = p[ok][:, None]; Y = y[ok]; L = later[ok]
    # out-of-fold on two temporal halves
    order = np.argsort(L); half = np.zeros(n, bool); half[order[n // 2:]] = True
    for h in (False, True):
        fit = half == h; oth = ~fit
        inner = np.zeros(int(fit.sum()), bool); lf = L[fit]; inner[lf > np.quantile(lf, 0.85)] = True
        am = ArtaModel(terms=("x",), bodies=["x"], F=1, seed=seed)
        C = np.nan_to_num(np.cos(np.radians(P[fit]))); S = np.nan_to_num(np.sin(np.radians(P[fit])))
        from coherent_fit import Coherent
        m = Coherent(1, 1, seed=seed); rng = np.random.default_rng(seed); idx = np.where(~inner)[0]
        best, state, bad = -1.0, None, 0
        for ep in range(120):
            rng.shuffle(idx)
            for s0 in range(0, len(idx), max(32, len(idx) // 16)):
                b = idx[s0:s0 + max(32, len(idx) // 16)]
                if len(b) >= 16: m.step(C[b], S[b], Y[fit][b].astype(float), 0.01, 1e-3)
            a = auc(Y[fit][inner], m.logit(C[inner], S[inner])[0]) if inner.sum() > 20 else 0.5
            if a > best + 1e-5: best, bad = a, 0; state = (m.A1.copy(), m.A2.copy(), m.br.copy(), m.bi.copy(), m.w.copy(), m.c, m.mu.copy(), m.sd.copy())
            else:
                bad += 1
                if bad >= 12: break
        m.A1, m.A2, m.br, m.bi, m.w, m.c, m.mu, m.sd = state
        Co = np.cos(np.radians(P[oth])); So = np.sin(np.radians(P[oth]))
        tmp = np.full(n, np.nan); tmp[oth] = m.logit(Co, So)[0]
        s_tr[np.where(ok)[0][oth]] = tmp[oth]
    # the model for the test rows: fitted on all of the phasor's rows, inner = latest 15%
    inner = L > np.quantile(L, 0.85)
    C = np.cos(np.radians(P)); S = np.sin(np.radians(P))
    m = Coherent(1, 1, seed=seed); rng = np.random.default_rng(seed); idx = np.where(~inner)[0]
    best, state, bad = -1.0, None, 0
    for ep in range(120):
        rng.shuffle(idx)
        for s0 in range(0, len(idx), max(32, len(idx) // 16)):
            b = idx[s0:s0 + max(32, len(idx) // 16)]
            if len(b) >= 16: m.step(C[b], S[b], Y[b].astype(float), 0.01, 1e-3)
        a = auc(Y[inner], m.logit(C[inner], S[inner])[0])
        if a > best + 1e-5: best, bad = a, 0; state = (m.A1.copy(), m.A2.copy(), m.br.copy(), m.bi.copy(), m.w.copy(), m.c, m.mu.copy(), m.sd.copy())
        else:
            bad += 1
            if bad >= 12: break
    m.A1, m.A2, m.br, m.bi, m.w, m.c, m.mu, m.sd = state
    oke = np.isfinite(pte)
    s_te[oke] = m.logit(np.cos(np.radians(pte[oke][:, None])), np.sin(np.radians(pte[oke][:, None])))[0]
    return s_tr, s_te, n, best


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
    log(f"{len(labels)} phasors (9 terms x 14 bodies) · train {len(y):,} · held out {len(yte):,}")
    Str = np.full((len(y), len(labels)), np.nan, np.float32); Ste = np.full((len(yte), len(labels)), np.nan, np.float32)
    info = []
    for j, labj in enumerate(labels):
        s_tr, s_te, n, iv = one_model(P[:, j], y, later, Pe[:, j])
        Str[:, j], Ste[:, j] = s_tr, s_te
        a_te = auc(yte[np.isfinite(s_te)], s_te[np.isfinite(s_te)]) if np.isfinite(s_te).sum() > 100 else float("nan")
        info.append({"phasor": labj, "n_train": n, "inner": iv, "held": a_te, "n_test": int(np.isfinite(s_te).sum())})
        if j % 14 == 0:
            log(f"  {labj:<20} rows {n:>6,}  inner {iv if np.isnan(iv) else round(iv,4)}  held {a_te if np.isnan(a_te) else round(a_te,4)}")
    log("all per-phasor models fitted")
    ages_te = pte[:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]
    cell = (np.floor(np.nan_to_num(ages_te[:, 0]) / 3) * 1000 + np.floor(np.nan_to_num(ages_te[:, 1]) / 3)).astype(int)
    cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
    R = {"per_phasor": info}

    def stack(Xtr, Xte, name):
        p = np.zeros(len(Xte))
        for sd in range(3):
            c = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=100, colsample_bytree=0.6,
                                   subsample=0.8, subsample_freq=1, reg_lambda=10.0, random_state=sd, verbose=-1)
            c.fit(Xtr, y); p += c.predict_proba(Xte)[:, 1]
        p /= 3
        R[name] = {"held": auc(yte, p), "age_cell_matched": matched(yte, p, cell)}
        log(f"  {name:<64} held {auc(yte, p):.4f}   age-cell-matched {matched(yte, p, cell):.4f}")
        return p
    six = [j for j, l in enumerate(labels) if l.split("_", 1)[0] in TERMS]
    stack(Str[:, six], Ste[:, six], "STACK of the 84 six-term per-phasor models (LightGBM, NaN-native)")
    stack(Str, Ste, "STACK of all 126 nine-term per-phasor models")
    stack(np.column_stack([Str, ptr[:, cols]]), np.column_stack([Ste, pte[:, cols]]), "STACK of 126 + the plain columns")
    stack(ptr[:, cols], pte[:, cols], "REFERENCE: plain columns alone (LightGBM)")
    # by term: which term's per-body models carry the most, on their own populations
    log("  best single per-phasor models by held-out (each on its own rows):")
    for r in sorted([r for r in info if not np.isnan(r["held"])], key=lambda r: -r["held"])[:12]:
        log(f"    {r['phasor']:<18} rows {r['n_train']:>6,}  held {r['held']:.4f}  (n_test {r['n_test']:,})")
    p_all = stack(np.column_stack([Str, ptr[:, cols]]), np.column_stack([Ste, pte[:, cols]]), "STACK 126 + plain (for the submission)")
    r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)
    pd.DataFrame({"id": ids, lab: r01(p_all)}).to_csv(os.path.join(OUT, "submission_split126.csv"), index=False)
    json.dump(R, open(os.path.join(OUT, "artamodel_split_models.json"), "w"), indent=1)
    log(f"wrote {OUT}/artamodel_split_models.json and submission_split126.csv")


if __name__ == "__main__":
    main()
