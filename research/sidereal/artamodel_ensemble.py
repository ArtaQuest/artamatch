"""
artamodel_ensemble.py — ArtaModel as ensembles, as boosting, and as SPLIT single-sum models.

Arash, 2026-08-18: "use ensembles and boosting techniques and split multiple single sum model".

  BAG      many ArtaModels (F=1, the literal formula), each on a bootstrap of the rows with its own seed; the
           held-out scores rank-averaged. Variance reduction for the one-field fit.
  BOOST    functional gradient boosting whose weak learner is ONE single-sum field |b + Σ_j w_j z_j|²: at each
           stage the field is fitted by least squares to the current pseudo-residuals of the logistic loss
           (r = y − p), scaled by a line-searched coefficient, shrunk by ν, and added; early-stopped on the inner
           temporal split. Each stage is a complete ArtaModel-shaped sum; the model is a sum of K such squares.
  SPLIT    the phasors partitioned into groups G_k -- per BODY (each body's own terms), per TERM TYPE (all bodies
           of one term), or per body×term (single phasors) -- and every group given its OWN single-sum field whose
           weights are masked to the group. The K intensities are combined (i) by a linear head (the coherent
           model with a block-diagonal weight matrix), and (ii) by LightGBM on the K intensities -- boosting over
           the split single-sum models -- with the plain columns optionally beside them.

Everything on the FULL population unless stated (both natal charts + the wedding day known: 6,258 train / 2,635
held out), the same protocol as the study: choices on the inner temporal split, held out read for the record,
the age-cell-matched control beside every headline.

Usage: AQ_PHASES=/tmp/aq3feat/phases.npz AQ_SOL=/tmp/aq3comp/solution.csv AQ_OUT=/tmp/aq3feat python artamodel_ensemble.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from artamodel import ANGLES, BODIES14, TERMS, ArtaModel, auc, phase_matrix       # noqa: E402
from coherent_fit import Coherent                                                    # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz")
SOL = os.environ.get("AQ_SOL", "/tmp/aq3comp/solution.csv")
OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat")
T0 = time.time()
R = {}


def log(*a):
    print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


def r01(v):
    r = rankdata(v); return (r - 1) / max(1.0, len(r) - 1)


def cs(P):
    rad = np.pi / 180.0
    return np.nan_to_num(np.cos(P * rad)), np.nan_to_num(np.sin(P * rad))


def matched(y, s, cell):
    num = den = 0.0
    for b in np.unique(cell):
        m = cell == b; n1, n0 = int(y[m].sum()), int((1 - y[m]).sum())
        if n1 and n0:
            num += auc(y[m], s[m]) * n1 * n0; den += n1 * n0
    return num / den if den else float("nan")


# ── one single-sum field fitted by LEAST SQUARES to a residual (the boosting weak learner) ─────────────────────
class Field:
    """u(x) = |b + Σ_j w_j z_j|², w and b complex, fitted so that α·u + c ≈ r by Adam on the squared error."""

    def __init__(self, K, seed, mask=None):
        g = np.random.default_rng(seed)
        sc = 1.0 / np.sqrt(K)
        self.A1 = g.normal(0, sc, K); self.A2 = g.normal(0, sc, K)
        self.br, self.bi = g.normal(0, 0.3), g.normal(0, 0.3)
        self.alpha, self.c = 0.0, 0.0
        self.mask = np.ones(K) if mask is None else mask.astype(float)
        self.A1 *= self.mask; self.A2 *= self.mask
        self.m = {k: 0.0 for k in ("A1", "A2", "br", "bi", "alpha", "c")}; self.v = dict(self.m); self.t = 0

    def u(self, C, S):
        Zr = C @ self.A1 + S @ self.A2 + self.br
        Zi = S @ self.A1 - C @ self.A2 + self.bi
        return Zr * Zr + Zi * Zi, Zr, Zi

    def fit(self, C, S, r, C_in, S_in, r_in, lr=0.02, steps=300, patience=40, l2=1e-3):
        best, state, bad = np.inf, None, 0
        for t in range(steps):
            u, Zr, Zi = self.u(C, S)
            pred = self.alpha * u + self.c
            e = pred - r                                   # d(0.5*mse)/dpred, per row / n
            n = len(r)
            g_alpha = float((e * u).mean()); g_c = float(e.mean())
            gu = e * self.alpha / n                        # dL/du
            gr, gi = 2.0 * gu * Zr, 2.0 * gu * Zi
            gA1 = (gr @ C + gi @ S) * self.mask + l2 * self.A1
            gA2 = (gr @ S - gi @ C) * self.mask + l2 * self.A2
            gbr, gbi = float(gr.sum()), float(gi.sum())
            self.t += 1
            for k, gval in (("A1", gA1), ("A2", gA2), ("br", gbr), ("bi", gbi), ("alpha", g_alpha), ("c", g_c)):
                self.m[k] = 0.9 * self.m[k] + 0.1 * gval; self.v[k] = 0.999 * self.v[k] + 0.001 * (gval * gval)
                mh = self.m[k] / (1 - 0.9 ** self.t); vh = self.v[k] / (1 - 0.999 ** self.t)
                setattr(self, k, getattr(self, k) - lr * mh / (np.sqrt(vh) + 1e-8))
            if t % 5 == 0:
                ui, _, _ = self.u(C_in, S_in)
                loss_in = float(np.mean((self.alpha * ui + self.c - r_in) ** 2))
                if loss_in < best - 1e-7:
                    best, bad = loss_in, 0
                    state = (self.A1.copy(), self.A2.copy(), self.br, self.bi, self.alpha, self.c)
                else:
                    bad += 5
                    if bad >= patience:
                        break
        if state is not None:
            self.A1, self.A2, self.br, self.bi, self.alpha, self.c = state
        return self

    def predict(self, C, S):
        u, _, _ = self.u(C, S)
        return self.alpha * u + self.c


def boost(P, y, inner, Pte, stages=60, nu=0.1, seed=0, masks=None):
    """Gradient boosting with single-sum fields. `masks` (optional list) restricts stage k's field to a group,
    cycling through the groups -- the SPLIT models boosted in turn."""
    C, S = cs(P); Cte, Ste = cs(Pte)
    fit = ~inner
    F = np.zeros(len(y)); Fte = np.zeros(len(Pte))
    p0 = np.clip(y[fit].mean(), 1e-3, 1 - 1e-3); F[:] = np.log(p0 / (1 - p0)); Fte[:] = F[0]
    best, best_stage, bad, best_Fte = -1.0, 0, 0, Fte.copy()
    for k in range(stages):
        p = 1 / (1 + np.exp(-F)); r = y - p
        mask = None if masks is None else masks[k % len(masks)]
        f = Field(C.shape[1], seed * 1000 + k, mask).fit(C[fit], S[fit], r[fit], C[inner], S[inner], r[inner])
        h = f.predict(C, S); hte = f.predict(Cte, Ste)
        # line search of the step on the logistic loss over the fit rows
        best_g, best_loss = 0.0, np.inf
        for gam in (0.25, 0.5, 1.0, 2.0, 4.0):
            Fx = F[fit] + nu * gam * h[fit]
            loss = float(np.mean(np.logaddexp(0, -Fx * (2 * y[fit] - 1))))
            if loss < best_loss:
                best_loss, best_g = loss, gam
        F = F + nu * best_g * h; Fte = Fte + nu * best_g * hte
        a = auc(y[inner], F[inner])
        if a > best + 1e-5:
            best, best_stage, bad, best_Fte = a, k + 1, 0, Fte.copy()
        else:
            bad += 1
            if bad >= 10:
                break
    return best, best_stage, best_Fte


def split_heads(P, y, inner, Pte, groups, F_seed=0):
    """SPLIT single-sum models with a LINEAR head: one field per group, weights masked to the group, K intensities
    combined by the coherent model's own head. Returns (inner auc, held-out score, K intensities train/test)."""
    C, S = cs(P); Cte, Ste = cs(Pte)
    K = C.shape[1]; G = len(groups)
    m = Coherent(K, G, seed=F_seed)
    M = np.zeros((G, K))
    for gi, cols in enumerate(groups):
        M[gi, cols] = 1.0
    m.A1 *= M; m.A2 *= M
    rng = np.random.default_rng(7 + F_seed); idx = np.where(~inner)[0]
    batch = int(min(1024, max(32, len(idx) // 16)))
    best, state, bad = -1.0, None, 0
    for ep in range(150):
        rng.shuffle(idx)
        for s0 in range(0, len(idx), batch):
            b = idx[s0:s0 + batch]
            if len(b) >= 32:
                m.step(C[b], S[b], y[b].astype(float), 0.01, 1e-3)
                m.A1 *= M; m.A2 *= M                       # keep every field inside its group
        a = auc(y[inner], m.logit(C[inner], S[inner])[0])
        if a > best + 1e-5:
            best, bad = a, 0
            state = (m.A1.copy(), m.A2.copy(), m.br.copy(), m.bi.copy(), m.w.copy(), m.c, m.mu.copy(), m.sd.copy())
        else:
            bad += 1
            if bad >= 15:
                break
    m.A1, m.A2, m.br, m.bi, m.w, m.c, m.mu, m.sd = state
    return best, m.logit(Cte, Ste)[0], m.fields(C, S)[2], m.fields(Cte, Ste)[2]


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True)
    bodies = list(Z["bodies"]); ids = Z["id_test"]; ytr = Z["y_train"].astype(np.int64)
    Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]
    Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    later = Z["yr_train"].astype(int).max(1)
    sol = pd.read_csv(SOL).set_index("id"); lab = [c for c in sol.columns if c != "Usage"][0]
    yte = sol.loc[ids, lab].to_numpy().astype(int)
    j1 = ptr[:, pn.index("start_year_only")] == 1.0; j1e = pte[:, pn.index("start_year_only")] == 1.0
    Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    B = [bodies.index(b) for b in BODIES14]
    full_tr = np.isfinite(Dtr[:, B]).all(1) & np.isfinite(Mtr[:, B]).all(1) & np.isfinite(Wtr[:, B]).all(1)
    full_te = np.isfinite(Dte[:, B]).all(1) & np.isfinite(Mte[:, B]).all(1) & np.isfinite(Wte[:, B]).all(1)
    ages_te = pte[full_te][:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]
    cell = (np.floor(ages_te[:, 0] / 3) * 1000 + np.floor(ages_te[:, 1] / 3)).astype(int)
    y = ytr[full_tr]; ye = yte[full_te]; lat = later[full_tr]; inner = lat > np.quantile(lat, 0.85)
    log(f"FULL population: train {len(y):,} (inner {int(inner.sum()):,}) · held out {len(ye):,}")
    cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
    Xp_tr, Xp_te = ptr[full_tr][:, cols], pte[full_te][:, cols]

    def report(name, s, extra=None):
        a = auc(ye, s); m_ = matched(ye, s, cell)
        R[name] = {"held": a, "age_cell_matched": m_, **(extra or {})}
        log(f"  {name:<58} held {a:.4f}   age-cell-matched {m_:.4f}" + (f"   {extra}" if extra else ""))

    for terms, tag in ((("a", "m", "d"), "3-term"), (TERMS, "6-term")):
        P, labels = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, terms); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, terms)
        P, Pe = P[full_tr], Pe[full_te]
        log(f"── {tag}: {len(labels)} phasors ──")
        # single ArtaModel, F=1 (the reference point)
        am = ArtaModel(terms=terms, bodies=BODIES14, F=1).fit(P, y, inner)
        report(f"{tag} single ArtaModel F=1", am.score(Pe), {"inner": round(am.inner_auc, 4)})
        # BAG: 25 bootstraps x seeds, rank-averaged
        rng = np.random.default_rng(0); scores = []; ivs = []
        fit_idx = np.where(~inner)[0]
        for b in range(25):
            boot = rng.choice(fit_idx, size=len(fit_idx), replace=True)
            keep = np.concatenate([boot, np.where(inner)[0]])
            inn = np.zeros(len(keep), bool); inn[len(boot):] = True
            a_ = ArtaModel(terms=terms, bodies=BODIES14, F=1, seed=b).fit(P[keep], y[keep], inn)
            scores.append(r01(a_.score(Pe))); ivs.append(a_.inner_auc)
        report(f"{tag} BAG 25 bootstraps (rank-average)", np.mean(scores, 0), {"inner_mean": round(float(np.mean(ivs)), 4)})
        # BOOST: single-sum fields on residuals
        for nu in (0.05, 0.1, 0.3):
            iv, K, s = boost(P, y, inner, Pe, stages=60, nu=nu)
            report(f"{tag} BOOST single-sum fields nu={nu}", s, {"inner": round(iv, 4), "stages": K})
        # SPLIT: groups per body / per term / per phasor
        by_body = [[k for k, l in enumerate(labels) if l.split("_", 1)[1] == b] for b in BODIES14]
        by_term = [[k for k, l in enumerate(labels) if l.split("_", 1)[0] == t] for t in terms]
        by_phasor = [[k] for k in range(len(labels))]
        for gname, groups in (("per body", by_body), ("per term", by_term), ("per phasor", by_phasor)):
            groups = [g for g in groups if g]
            iv, s, Utr, Ute = split_heads(P, y, inner, Pe, groups)
            report(f"{tag} SPLIT {gname} ({len(groups)} single sums), linear head", s, {"inner": round(iv, 4)})
            # LightGBM on the K intensities (boosting over the split models), plus with the plain columns
            def gbm(Xtr, Xte, seeds=3):
                p = np.zeros(len(Xte))
                for sd in range(seeds):
                    c = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=50, colsample_bytree=0.8,
                                           subsample=0.8, subsample_freq=1, reg_lambda=10.0, random_state=sd, verbose=-1)
                    c.fit(Xtr[~inner], y[~inner]); p += c.predict_proba(Xte)[:, 1]
                return p / seeds
            report(f"{tag} SPLIT {gname} -> LightGBM on the {len(groups)} intensities", gbm(Utr, Ute))
            report(f"{tag} SPLIT {gname} -> LightGBM on intensities + plain columns", gbm(np.column_stack([Utr, Xp_tr]), np.column_stack([Ute, Xp_te])))
            # boosting the split models in turn (each stage restricted to one group)
            masks = [np.isin(np.arange(len(labels)), g) for g in groups]
            iv, K, s = boost(P, y, inner, Pe, stages=min(120, 4 * len(groups)), nu=0.1, masks=masks)
            report(f"{tag} BOOST over SPLIT {gname} (stage k -> group k)", s, {"inner": round(iv, 4), "stages": K})
    # references on the same rows
    def gbm_plain(seeds=3):
        p = np.zeros(len(Xp_te))
        for sd in range(seeds):
            c = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=50, reg_lambda=10.0, random_state=sd, verbose=-1)
            c.fit(Xp_tr[~inner], y[~inner]); p += c.predict_proba(Xp_te)[:, 1]
        return p / seeds
    report("REFERENCE plain columns (two ages, gap, start year), LightGBM", gbm_plain())
    json.dump(R, open(os.path.join(OUT, "artamodel_ensemble.json"), "w"), indent=1)
    log(f"wrote {OUT}/artamodel_ensemble.json")


if __name__ == "__main__":
    main()
