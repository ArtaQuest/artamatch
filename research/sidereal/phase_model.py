"""
phase_model.py — the operator's sidereal phase model, fitted:

    y = | b + SUM_i  a_i e^{i(theta_m,i - theta_d,i)}  +  m_i e^{i(theta(t)_i - theta_m,i)}  +  d_i e^{i(theta(t)_i - theta_d,i)}
                   +  mn_i e^{i theta_m,i}  +  dn_i e^{i theta_d,i}  +  tn_i e^{i theta(t)_i} |^2

theta_m, theta_d are mom's and dad's SIDEREAL longitudes (Lahiri, 09:00 local at each birthplace), theta(t) the
sidereal longitudes on the wedding date (noon UT), all through KERYKEION (kerykeion_phases.py); i runs over
fourteen bodies (Sun Moon Mercury Venus Mars Jupiter Saturn Uranus Neptune Pluto TrueNode TrueSouthNode Chiron
MeanLilith), with the Ascendant and MC available for the synastry term. Three phasors per graha -- synastry, the wedding transiting mom, the wedding transiting dad --
with complex weights a, m, d and a complex bias b, all LEARNED; the squared modulus is the score. It is the
coherent-field family restricted to the phase differences the tradition actually reads.

WHAT IS FITTED AND HOW. Each phasor's weight is one complex number, held as (Re, Im) so the parameter space is
flat; the model is a complex-linear map over the 27 phasors followed by |.|^2 -- exactly the machinery of
research/coherent/coherent_fit.py (gradients checked there against finite differences), reused here. A logistic
head turns the (standardised) intensity into a probability so it can be fitted by log-loss; AUC reads the
intensity's ranking, so the head's own scale is irrelevant to the score. F fields = F independent copies of the
formula, standardised and combined linearly; F=1 is the operator's formula literally.

ROWS. The synastry term needs both natal charts (both births to the day, both places); the wedding terms need
the wedding sky. On a year-only start (published YYYY-01-01) only the slow grahas have an honest wedding
position, so two fits are reported: REAL-DAY starts only (all 27 phasors) and ALL rows (synastry on all nine,
wedding terms on Jupiter/Saturn/Rahu/Ketu only). Selection on an inner TEMPORAL split; the held-out half read
once, for the record.

Usage: AQ_PHASES=/tmp/aq3feat/phases.npz AQ_SOL=/tmp/aq3comp/solution.csv python phase_model.py
"""
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from coherent_fit import Coherent, auc                                    # noqa: E402

T0 = time.time()
PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz")
SOL = os.environ.get("AQ_SOL", "/tmp/aq3comp/solution.csv")
OUT = os.environ.get("AQ_OUT", os.path.dirname(PH))
SLOW = {"jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "true_south_node", "chiron", "mean_lilith"}
ANGLES = {"ascendant", "medium_coeli"}


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def phases(D, M, W, bodies, wed_bodies, with_angles, natal=True):
    """The phases in DEGREES per row: a_i (mom - dad) for every body (angles too, if asked), then m_i
    (wedding - mom) and d_i (wedding - dad) for the wedding bodies, then -- the extension of 2026-08-18 -- the
    NATAL terms mn_i (mom's own longitude) and dn_i (dad's own longitude). Returns (n, K) and the labels."""
    P, lab = [], []
    for j, b in enumerate(bodies):
        if b in ANGLES and not with_angles:
            continue
        P.append(M[:, j] - D[:, j]); lab.append(f"a_{b}: mom-dad")
    if natal:
        for j, b in enumerate(bodies):
            if b in ANGLES and not with_angles:
                continue
            P.append(M[:, j]); lab.append(f"mn_{b}: mom natal")
            P.append(D[:, j]); lab.append(f"dn_{b}: dad natal")
        for j, b in enumerate(bodies):
            if b not in wed_bodies:
                continue
            P.append(W[:, j]); lab.append(f"tn_{b}: wedding sky")        # the sixth term, 2026-08-18
    for j, b in enumerate(bodies):
        if b not in wed_bodies:
            continue
        P.append(W[:, j] - M[:, j]); lab.append(f"m_{b}: wedding-mom")
        P.append(W[:, j] - D[:, j]); lab.append(f"d_{b}: wedding-dad")
    return np.column_stack(P), lab


def fit_family(Ptr, ytr, Pte, inner, F, l2=1e-3, seeds=3, epochs=60):
    rad = np.pi / 180.0
    # A NaN phase means the term does not exist for that row -- the wedding day is not known, so the wedding
    # phasors are DROPPED (operator: "if wedding is not known, drop the last two terms"). Setting cos = sin = 0
    # makes the phasor's contribution exactly zero while the same weights serve every row.
    Ctr, Str = np.nan_to_num(np.cos(Ptr * rad)), np.nan_to_num(np.sin(Ptr * rad))
    Cte, Ste = np.nan_to_num(np.cos(Pte * rad)), np.nan_to_num(np.sin(Pte * rad))
    fitm = ~inner; idx = np.where(fitm)[0]
    outs, ivs = [], []
    for seed in range(seeds):
        m = Coherent(Ctr.shape[1], F, seed=seed); rng = np.random.default_rng(100 + seed)
        best, state, bad = -1.0, None, 0
        for ep in range(epochs):
            rng.shuffle(idx)
            for s0 in range(0, len(idx), 2048):
                b = idx[s0:s0 + 2048]
                if len(b) >= 32:
                    m.step(Ctr[b], Str[b], ytr[b].astype(float), 0.01, l2)
            a = auc(ytr[inner], m.logit(Ctr[inner], Str[inner])[0])
            if a > best + 1e-5:
                best, bad = a, 0
                state = (m.A1.copy(), m.A2.copy(), m.br.copy(), m.bi.copy(), m.w.copy(), m.c, m.mu.copy(), m.sd.copy())
            else:
                bad += 1
                if bad >= 10:
                    break
        m.A1, m.A2, m.br, m.bi, m.w, m.c, m.mu, m.sd = state
        outs.append(m.logit(Cte, Ste)[0]); ivs.append(best)
    return float(np.mean(ivs)), np.mean(outs, 0)


def main():
    Z = np.load(PH, allow_pickle=True)
    bodies = list(Z["bodies"]); ids = Z["id_test"]; ytr = Z["y_train"].astype(np.int64)
    Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]
    Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    later = Z["yr_train"].astype(int).max(1)
    sol = pd.read_csv(SOL).set_index("id"); lab = [c for c in sol.columns if c != "Usage"][0]
    yte = sol.loc[ids, lab].to_numpy().astype(int); pub = (sol.loc[ids, "Usage"] == "Public").to_numpy()
    j1 = ptr[:, pn.index("start_is_jan1")] == 1.0; j1e = pte[:, pn.index("start_is_jan1")] == 1.0
    PLANETS = [b for b in bodies if b not in ANGLES]
    results = {}
    log(f"phases from Kerykeion: {len(bodies)} bodies · train {len(ytr):,} · held out {len(yte):,}")
    # On a year-only start the wedding phasors are set to NaN for EVERY body (not only the fast ones): the
    # instruction is to drop the last two terms whenever the wedding is not known.
    Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    for variant, wed_bodies, angles, rm_tr, rm_te, need_wed in (
            ("ALL rows: every term present only where both of its phases are known", PLANETS, False,
             np.ones(len(ytr), bool), np.ones(len(yte), bool), False),
            ("ALL rows, the same with ASC/MC in the synastry term", PLANETS, True,
             np.ones(len(ytr), bool), np.ones(len(yte), bool), False),
            ("real-day starts only: 14 bodies x 3 phasors", PLANETS, False, ~j1, ~j1e, True),
            ("all rows: synastry terms only (no wedding terms at all)", [], False, np.ones(len(ytr), bool), np.ones(len(yte), bool), False),
            ("all rows: WITHOUT the natal terms (the previous formula)", PLANETS, False, np.ones(len(ytr), bool), np.ones(len(yte), bool), "nonatal"),
        ):
        natal = need_wed != "nonatal"; need_wed = bool(need_wed) and need_wed != "nonatal"
        Ptr, labels = phases(Dtr, Mtr, Wtr, bodies, wed_bodies, angles, natal); Pte, _ = phases(Dte, Mte, Wte, bodies, wed_bodies, angles, natal)
        n_syn = sum(1 for l in labels if l.startswith("a_")); n_nat = sum(1 for l in labels if l.startswith(("mn_", "dn_", "tn_")))
        # EVERY TERM EXISTS ONLY WHEN BOTH OF ITS PHASES DO (operator: "if dob of either is not known, drop the
        # natal term of it"; "if wedding is not known, drop the last two terms"). A phasor with a missing phase is
        # NaN here and contributes zero in the fit, so an absent partner drops the synastry term and their own
        # wedding term, a year-only birth keeps only its slow-body terms, and a row is used as long as it has at
        # least one phasor. The "real-day only" variant is the one exception: it asks for every term.
        any_tr = np.isfinite(Ptr).any(1); any_te = np.isfinite(Pte).any(1)
        ok_tr = rm_tr & any_tr & (np.isfinite(Ptr).all(1) if need_wed else True)
        ok_te = rm_te & any_te & (np.isfinite(Pte).all(1) if need_wed else True)
        if ok_tr.sum() < 500 or ok_te.sum() < 200:
            log(f"  {variant}: too few complete rows (train {int(ok_tr.sum())}, test {int(ok_te.sum())}); skipped"); continue
        Ptr_, ytr_, Pte_, yte_, pub_ = Ptr[ok_tr], ytr[ok_tr], Pte[ok_te], yte[ok_te], pub[ok_te]
        lat = later[ok_tr]; inner = lat > np.quantile(lat, 0.85)
        syn_tr = int(np.isfinite(Ptr_[:, :n_syn]).all(1).sum()); syn_te = int(np.isfinite(Pte_[:, :n_syn]).all(1).sum())
        kw_tr = int(np.isfinite(Ptr_[:, n_syn:]).all(1).sum()) if Ptr_.shape[1] > n_syn else 0
        kw_te = int(np.isfinite(Pte_[:, n_syn:]).all(1).sum()) if Pte_.shape[1] > n_syn else 0
        log(f"{variant}: {len(labels)} phasors ({n_syn} synastry, {n_nat} natal, {len(labels)-n_syn-n_nat} wedding) · "
            f"train {len(ytr_):,} (both charts {syn_tr:,}, wedding known {kw_tr:,}; inner {int(inner.sum()):,}) · "
            f"held out {len(yte_):,} (both charts {syn_te:,}, wedding known {kw_te:,})")
        for F in (1, 8, 32):
            iv, p = fit_family(Ptr_, ytr_, Pte_, inner, F)
            a = auc(yte_, p); ap = auc(yte_[pub_], p[pub_]); av = auc(yte_[~pub_], p[~pub_])
            results[f"{variant} | F={F}"] = {"inner": iv, "held": a, "public": ap, "private": av,
                                             "n_train": int(len(ytr_)), "n_test": int(len(yte_)), "phasors": len(labels)}
            log(f"    F={F:<3} inner {iv:.4f}  ->  held out {a:.4f}  (public {ap:.4f} / private {av:.4f})")
        # THE REFERENCE ON THESE ROWS: the plain columns, boosted. Dad's age alone would be too weak a bar here:
        # a slow body's wedding-transit phase (Saturn 12 deg/yr) reads each partner's age at the wedding directly.
        from sklearn.ensemble import HistGradientBoostingClassifier
        cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
        Rtr, Rte = ptr[ok_tr][:, cols], pte[ok_te][:, cols]
        pr = np.zeros(len(Rte))
        for sd in range(3):
            c = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0,
                                               early_stopping=True, validation_fraction=0.15, random_state=sd).fit(Rtr, ytr_)
            pr += c.predict_proba(Rte)[:, 1]
        ad = Rte[:, 0]; aa = auc(yte_, -ad)
        log(f"    reference on these rows — dad's age at the start alone: {max(aa, 1-aa):.4f} · "
            f"boosted trees on the two ages, the gap and the start year: {auc(yte_, pr/3):.4f}")
        results[f"{variant} | reference: ages+gap+start boosted"] = {"held": auc(yte_, pr / 3)}
    json.dump(results, open(os.path.join(OUT, "phase_model.json"), "w"), indent=1)
    log(f"wrote {OUT}/phase_model.json")


if __name__ == "__main__":
    main()
