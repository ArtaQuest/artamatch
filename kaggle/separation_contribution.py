"""
separation_contribution.py — what each system adds to predicting NATURAL vs ARTIFICIAL separation.

The target (operator 2026-08-22): among unions that ended, did one of them die, or did they divorce?

WHY THIS DOES NOT USE THE CELL-MATCHED CONTROL. On the 89k-row duration dataset, holding the confounders flat
inside cells worked because there were ~100,000 comparable pairs left afterwards. Here there are 11,116 rows,
and the tightest cell that keeps every reference at 0.5000 leaves 1,983 pairs — a 3-sigma bar of 0.034, when
the effects in question are around 0.01. A control that cannot resolve the thing it is testing is not a
control. Measured, not assumed: see the sweep in the commit message.

SO THE CONFOUNDERS GO IN THE BASELINE INSTEAD. The baseline model is given every one of them outright — both
ages, the age gap, the wedding year, and the exact pattern of which of the three dates are fully recorded —
and each family is scored by what it ADDS on top. That is a nested-model comparison, it uses every row rather
than only within-cell pairs, and on this sample size it resolves an order of magnitude finer.

AND IT IS RUN SEVERAL TIMES. A single run of this kind produced a confident ranking of the world's traditions
on the previous target, and rerunning it with one nuisance changed dissolved that ranking entirely — the
run-to-run spread was five times the best effect. So every figure here is the mean over several seeds with the
spread printed beside it, and nothing is called a contribution unless it clears its own spread.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

DATA = os.environ.get("AQ_DATA", os.path.expanduser("~/.artamatch-dev/seppkg"))
CODE = os.environ.get("AQ_CODE", os.path.expanduser("~/Studio/artamatch/research/sidereal"))
WEB = os.environ.get("AQ_WEB", os.path.expanduser("~/Studio/artamatch/web"))
OUT = os.environ.get("AQ_OUT", os.path.expanduser("~/.artamatch-dev/sep_out"))
SEEDS = [int(v) for v in os.environ.get("AQ_SEEDS", "0,1,2,3,4").split(",")]
QS = (0.40, 0.55, 0.70, 0.85, 1.0)
sys.path.insert(0, CODE)
os.makedirs(OUT, exist_ok=True)

import giant_ensemble as G   # noqa: E402  — reuse its adapters, auc and family list


def main():
    import xgboost as xgb
    params, on_gpu = G.gpu_params()
    log(f"xgboost {xgb.__version__} · {'GPU' if on_gpu else 'CPU'} · seeds {SEEDS}")

    tr = pd.read_csv(os.path.join(DATA, "train.csv"), dtype=str)
    te = pd.read_csv(os.path.join(DATA, "test.csv"), dtype=str)
    Z = np.load(os.path.join(DATA, "phases.npz"), allow_pickle=True)
    y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1)
    cuts = [np.quantile(later, q) for q in QS]
    pn = list(Z["plain_names"]); s1, s2 = list(Z["slots"]); P, Pte = Z["plain_train"], Z["plain_test"]
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    log(f"train {len(tr):,} · artificial {y.mean():.1%}")

    # THE BASELINE CARRIES EVERY CONFOUNDER
    fullp = lambda d, c: d[c].fillna("").str.match(r"^\d{4}-(?!00)\d{2}-(?!00)\d{2}$").to_numpy().astype(float)
    prec = lambda d: fullp(d, "dob_a") * 4 + fullp(d, "dob_b") * 2 + fullp(d, "start")
    base = lambda p, d: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]),
                                         np.abs(p[:, ia] - p[:, ib]), p[:, iy], prec(d)])
    B, Bte = base(P, tr), base(Pte, te)
    BN = ["age_older", "age_younger", "age_gap", "start_year", "date_precision"]

    log("building families")
    fams, failed = G.build_families(tr, te, Z)

    def oof(X, Xte, seed):
        s, _ = G.forward_oof(X, Xte, y, later, cuts, params, seed=seed)
        return s

    def score(X, Xte, label):
        """Mean held-out AUC over the seeds, and the spread across them."""
        vals = []
        for sd in SEEDS:
            s = oof(X, Xte, sd)
            f = np.isfinite(s) & (later > cuts[0])
            vals.append(G.auc(y[f], s[f]))
        v = np.array(vals)
        log(f"  {label:<46} {v.mean():.4f}  spread {v.max()-v.min():.4f}")
        return float(v.mean()), float(v.max() - v.min()), vals

    log("baseline — every confounder, and nothing else")
    b_m, b_sp, b_all = score(B, Bte, "CONFOUNDERS ONLY (ages, gap, era, precision)")
    # each confounder alone, so the baseline can be read rather than taken on faith
    singles = []
    for nm, col, colte in (("the wedding year alone", P[:, [iy]], Pte[:, [iy]]),
                           ("both ages alone", P[:, [ia, ib]], Pte[:, [ia, ib]]),
                           ("date precision alone", prec(tr).reshape(-1, 1), prec(te).reshape(-1, 1))):
        m_, sp_, _ = score(col, colte, nm)
        singles.append((nm, (m_, sp_)))

    log("each family, on top of the full baseline")
    rows = {}
    for fam in fams:
        Xa = np.column_stack([B, fams[fam][0]]); Xb = np.column_stack([Bte, fams[fam][1]])
        m, sp, allv = score(Xa, Xb, f"baseline + {fam}")
        rows[fam] = dict(mean=m, spread=sp, gain=m - b_m, n_features=int(fams[fam][0].shape[1]),
                         desc=fams[fam][3], seeds=allv)
    # everything at once
    allX = np.column_stack([B] + [fams[f][0] for f in fams])
    allXte = np.column_stack([Bte] + [fams[f][1] for f in fams])
    g_m, g_sp, _ = score(allX, allXte, f"baseline + ALL {allX.shape[1]-len(BN)} astrological features")

    L = []
    p = L.append
    p("=" * 96)
    p("NATURAL (death) vs ARTIFICIAL (divorce) — what each system adds over the confounders")
    p("=" * 96)
    p("")
    p(f"  {len(tr):,} ended unions, {y.mean():.1%} artificial. Held-out AUC, forward-chained, "
      f"mean of {len(SEEDS)} seeds.")
    p("")
    p(f"  {'BASELINE':<52}{'AUC':>9}{'spread':>9}")
    p("  " + "-" * 70)
    for nm, v in singles:
        p(f"  {nm:<52}{v[0]:>9.4f}{v[1]:>9.4f}")
    p(f"  {'CONFOUNDERS ONLY (ages, gap, era, precision)':<52}{b_m:>9.4f}{b_sp:>9.4f}")
    p("")
    p(f"  {'FAMILY (added on top of the baseline)':<40}{'feats':>7}{'AUC':>9}{'GAIN':>9}{'spread':>9}   {'verdict':<22}")
    p("  " + "-" * 94)
    for fam, r in sorted(rows.items(), key=lambda kv: -kv[1]["gain"]):
        real = abs(r["gain"]) > max(r["spread"], b_sp)
        verdict = "clears its own spread" if (real and r["gain"] > 0) else (
            "HURTS" if r["gain"] < -max(r["spread"], b_sp) else "inside the noise")
        p(f"  {fam:<40}{r['n_features']:>7}{r['mean']:>9.4f}{r['gain']:>+9.4f}{r['spread']:>9.4f}   {verdict:<22}")
    p("  " + "-" * 94)
    p(f"  {'ALL FAMILIES AT ONCE':<40}{allX.shape[1]-len(BN):>7}{g_m:>9.4f}{g_m-b_m:>+9.4f}{g_sp:>9.4f}")
    p("")
    p("A gain is only called real if it exceeds the seed-to-seed spread of its own run and of the baseline.")
    p("The spread is not a standard error — it is what the same model does on the same data when only the")
    p("random seed changes, and it is the floor below which nothing here can be distinguished.")
    if failed:
        p("")
        p("Families that did not build (absent, not zero): " + ", ".join(f for f, _ in failed))
    rep = "\n".join(L)
    print("\n" + rep, flush=True)
    open(os.path.join(OUT, "separation_contribution.txt"), "w").write(rep + "\n")
    json.dump(dict(baseline=dict(mean=b_m, spread=b_sp), families=rows,
                   all_families=dict(mean=g_m, spread=g_sp), n_train=len(tr), positive_rate=float(y.mean())),
              open(os.path.join(OUT, "separation_contribution.json"), "w"), indent=1)
    log(f"wrote {OUT}/separation_contribution.txt")


if __name__ == "__main__":
    main()
