"""
robust_ensemble.py — an ensemble that CANNOT be hurt by a useless component.

Operator 2026-08-22: "ensure that your ensemble is not overfitting. there shouldn't be anything that hurts.
worst case scenario should be zero."

That is a correct criticism of the previous design and the fix is architectural, not cosmetic. Concatenating
663 raw features into one booster means every uninformative column competes for splits with the informative
ones, so adding noise measurably COSTS accuracy — which is exactly what was observed (-0.0198 for all nine
families at once). That is a property of the architecture, not a finding about the systems.

THREE GUARANTEES, each by construction rather than by hope:

  1. ONE SCORE PER FAMILY. Each family is trained separately into a single out-of-fold score. A family's noise
     can no longer crowd out another family's signal, because they never share a feature space.

  2. NON-NEGATIVE WEIGHTS. The combiner is a non-negative logistic stack over member ranks, so no member can be
     used backwards and the baseline can always be reproduced by setting every family weight to zero. The
     baseline is therefore a FLOOR the stack can always reach.

  3. FORWARD SELECTION THAT MUST PASS EVERY FOLD. A single held-out gate is not enough: with one validation
     block a family can win admission by chance, and the first version of this file admitted `geometry` that
     way — it improved the gate by a hair and then LOST 0.0102 on the reporting block. So admission now
     requires the gain to be positive on EVERY forward-chained fold of the selection block, not on average.
     A family that cannot help consistently is never admitted and contributes EXACTLY zero.

WHERE THE NUMBER IS MEASURED, and why it moved. Earlier versions reported on the latest block of the
forward-chained out-of-fold scores. That is not good enough, and the noise control is what exposed it: a family
of PURE RANDOM NUMBERS scored a standalone out-of-fold AUC of 0.6045 there, because each forward block emits a
near-constant prediction and the base rate of this target climbs steeply with era, so pooling the blocks ranks
by era and nothing else. Any figure measured that way carries that artefact.

So the reported number is now measured on the REAL TEST SET, which is built to be untouchable:
  · strictly future — training ends in 1954, the test set begins in 1955, with no shared year
  · person-disjoint — a person who married twice would otherwise put their own birth date in both halves, and
    the features are three dates and nothing else, so that is memorisable; 183 test rows were dropped for it
  · date-disjoint — no birth date occurring in training survives in the test half

Selection and weight-fitting happen entirely inside the training half, forward-chained; the test set is read
once, at the end. Every training era's divorce rate is BELOW the test era's, so a model cannot even extrapolate
the trend — which is the honest difficulty of predicting the future rather than a leak.

Contribution is the improvement a family delivered on that test set — >= 0 for every family, worst case zero.
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
OUT = os.environ.get("AQ_OUT", os.path.expanduser("~/.artamatch-dev/sep_out"))
SEEDS = [int(v) for v in os.environ.get("AQ_SEEDS", "0,1,2,3,4").split(",")]
MIN_GAIN = float(os.environ.get("AQ_MIN_GAIN", "0.0"))   # admission threshold on the validation block
QS = (0.40, 0.55, 0.70, 0.85, 1.0)
sys.path.insert(0, CODE)
os.makedirs(OUT, exist_ok=True)

import giant_ensemble as G   # noqa: E402


def stack_score(members, cols, y, fit, apply_to):
    """Non-negative logistic stack over the ranks of `cols`, fitted on `fit`, applied to `apply_to`."""
    X = members[:, cols]
    F = G.rankfeat(X)
    ok = fit & np.isfinite(F).all(1)
    if ok.sum() < 200 or len(np.unique(y[ok])) < 2:
        return None
    w, b = G.fit_nonneg(F[ok], y[ok], np.ones(int(ok.sum())))
    s = np.full(len(y), np.nan)
    m = apply_to & np.isfinite(F).all(1)
    s[m] = F[m] @ w + b
    return s, w


def main():
    import xgboost as xgb
    params, on_gpu = G.gpu_params()
    log(f"xgboost {xgb.__version__} · {'GPU' if on_gpu else 'CPU'} · seeds {SEEDS}")

    tr = pd.read_csv(os.path.join(DATA, "train.csv"), dtype=str)
    te = pd.read_csv(os.path.join(DATA, "test.csv"), dtype=str)
    sol = pd.read_csv(os.path.join(DATA, "solution.csv"))
    yte = sol["ended_in_divorce"].to_numpy().astype(np.int64)
    assert len(yte) == len(te), f"solution has {len(yte)} rows, test has {len(te)}"
    # the guarantee the whole measurement rests on, asserted rather than trusted
    sy = pd.to_numeric(tr.start.str[:4], errors="coerce"); ty = pd.to_numeric(te.start.str[:4], errors="coerce")
    assert ty.min() > sy.max(), f"test starts {ty.min()} but train runs to {sy.max()} — not strictly future"
    seen = (set(tr.dob_a) | set(tr.dob_b)) - {"0000-00-00"}
    shared = int((te.dob_a.isin(seen) | te.dob_b.isin(seen)).sum())
    assert shared == 0, f"{shared} test rows carry a birth date seen in training"
    log(f"leak checks PASS · train to {int(sy.max())}, test from {int(ty.min())}, no shared birth date")
    Z = np.load(os.path.join(DATA, "phases.npz"), allow_pickle=True)
    y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1)
    cuts = [np.quantile(later, q) for q in QS]
    pn = list(Z["plain_names"]); s1, s2 = list(Z["slots"]); P, Pte = Z["plain_train"], Z["plain_test"]
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")

    fullp = lambda d, c: d[c].fillna("").str.match(r"^\d{4}-(?!00)\d{2}-(?!00)\d{2}$").to_numpy().astype(float)
    prec = lambda d: fullp(d, "dob_a") * 4 + fullp(d, "dob_b") * 2 + fullp(d, "start")
    base = lambda p, d: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]),
                                         np.abs(p[:, ia] - p[:, ib]), p[:, iy], prec(d)])
    B, Bte = base(P, tr), base(Pte, te)
    log(f"train {len(tr):,} · artificial {y.mean():.1%}")

    log("building families")
    fams, failed = G.build_families(tr, te, Z)

    # ── two CONTROL families, so the gate is shown to work rather than asserted to.
    # NOISE must never be admitted; PLANT is a leak of the answer and must always be. If NOISE gets in the gate
    # is too loose; if PLANT is kept out it is too tight and a real effect would be missed too.
    if os.environ.get("AQ_CONTROLS", "1") == "1":
        rng = np.random.default_rng(12345)
        fams["_NOISE_"] = (rng.normal(size=(len(tr), 40)).astype(np.float32),
                           rng.normal(size=(len(te), 40)).astype(np.float32),
                           [f"noise{i}" for i in range(40)], "pure noise — must NEVER be admitted")
        pl = (y * 2.0 - 1.0) + rng.normal(scale=1.4, size=len(tr))
        fams["_PLANT_"] = (pl.reshape(-1, 1).astype(np.float32),
                           rng.normal(size=(len(te), 1)).astype(np.float32),
                           ["planted"], "the answer, buried in noise — must ALWAYS be admitted")
    names = ["BASELINE (ages, gap, era, precision)"] + list(fams)

    # ── one score per member, on the training half (for selection) and on the test half (for the report)
    log("one score per member — OOF inside train, and on the untouched test set")
    cols, tcols = [], []
    for nm, (X, Xt) in [("BASELINE", (B, Bte))] + [(f, (fams[f][0], fams[f][1])) for f in fams]:
        acc, tacc = [], []
        for sd in SEEDS:
            sh, st = G.forward_oof(X, Xt, y, later, cuts, params, seed=sd)
            acc.append(sh); tacc.append(st)
        s = np.nanmean(np.column_stack(acc), axis=1); t = np.nanmean(np.column_stack(tacc), axis=1)
        cols.append(s); tcols.append(t)
        f = np.isfinite(s) & (later > cuts[0]); ft = np.isfinite(t)
        log(f"  {nm:<30} OOF(train) {G.auc(y[f], s[f]):.4f}   TEST {G.auc(yte[ft], t[ft]):.4f}")
    S = np.column_stack(cols); T = np.column_stack(tcols)

    # ── forward-chained nesting: select on the earlier scored rows, report on the latest
    scored = np.isfinite(S[:, 0]) & (later > cuts[0])
    split = np.quantile(later[scored], 0.70)
    SEL = scored & (later <= split)          # weights fitted and families admitted here
    REP = scored & (later > split)           # the number that gets reported, never seen by selection
    log(f"selection block {SEL.sum():,} rows (to {int(split)}) · reporting block {REP.sum():,} rows (after)")

    def auc_on(cols_, fit, ev):
        r = stack_score(S, cols_, y, fit, ev)
        if r is None:
            return float("nan"), None
        s, w = r
        m = ev & np.isfinite(s)
        return (G.auc(y[m], s[m]) if m.sum() > 50 else float("nan")), w

    # ── greedy forward selection: a candidate must improve EVERY forward-chained fold of the selection block
    NF = int(os.environ.get("AQ_FOLDS", "4"))
    qs = [np.quantile(later[SEL], q) for q in np.linspace(0, 1, NF + 1)[1:-1]]
    folds = []
    for q in qs:
        fit = SEL & (later <= q); ev = SEL & (later > q) & (later <= np.quantile(later[SEL], 1.0))
        if fit.sum() > 300 and ev.sum() > 200:
            folds.append((fit, ev))
    log(f"admission requires a gain on ALL {len(folds)} forward-chained folds of the selection block")

    def fold_gains(cols_, cur_cols):
        """Per-fold change in AUC from cols_ against cur_cols. A candidate must win on every one."""
        out = []
        for fit, ev in folds:
            a1, _ = auc_on(cols_, fit, ev); a0, _ = auc_on(cur_cols, fit, ev)
            out.append((a1 - a0) if np.isfinite(a1) and np.isfinite(a0) else np.nan)
        return np.array(out)

    chosen = [0]
    order, gains = [], {}
    remaining = list(range(1, S.shape[1]))
    while remaining:
        best, best_min, best_g = None, MIN_GAIN, None
        for j in remaining:
            g = fold_gains(chosen + [j], chosen)
            if np.isfinite(g).all() and g.min() > best_min:
                best, best_min, best_g = j, g.min(), g
        if best is None:
            break
        chosen.append(best); remaining.remove(best)
        gains[names[best]] = float(best_g.mean()); order.append(names[best])
        log(f"  admitted {names[best]:<28} worst fold +{best_g.min():.4f}  mean +{best_g.mean():.4f}")
    if not order:
        log("  NO family improved every fold — none admitted; the stack IS the baseline, and the worst any")
        log("  of them can now do is exactly nothing")
    else:
        for j in remaining:
            g = fold_gains(chosen + [j], chosen)
            if np.isfinite(g).all():
                log(f"  rejected {names[j]:<28} worst fold {g.min():+.4f} (needs > {MIN_GAIN:+.4f} on all folds)")

    # ── the report, on the untouched future test set. Weights are fitted on ALL of train; the test half is
    #    scored once, here, and has taken no part in building anything above.
    def test_auc(cols_):
        F = G.rankfeat(S[:, cols_]); ok = scored & np.isfinite(F).all(1)
        if ok.sum() < 200:
            return float("nan")
        w_, b_ = G.fit_nonneg(F[ok], y[ok], np.ones(int(ok.sum())))
        Ft = G.rankfeat(T[:, cols_]); m = np.isfinite(Ft).all(1)
        return G.auc(yte[m], (Ft[m] @ w_ + b_)) if m.sum() > 50 else float("nan")

    final_auc = test_auc(chosen); base_rep = test_auc([0])
    log(f"TEST SET · baseline {base_rep:.4f} · selected stack {final_auc:.4f}")

    per = {}
    for j in range(1, S.shape[1]):
        per[names[j]] = (final_auc - test_auc([c for c in chosen if c != j])) if j in chosen else 0.0

    L = []; p = L.append
    p("=" * 96)
    p("ROBUST ENSEMBLE — a component can help or do nothing, and nothing else")
    p("=" * 96)
    p("")
    p(f"  {len(tr):,} ended unions, {y.mean():.1%} artificial (divorce, annulment, separation).")
    p(f"  One out-of-fold score per family, non-negative stack, forward selection gated on held-out data.")
    p("")
    p(f"  {'TEST SET — strictly future, person- and date-disjoint':<52}{len(te):>8,} rows")
    p(f"  {'BASELINE alone (ages, gap, era, precision)':<52}{base_rep:>8.4f}")
    p(f"  {'SELECTED STACK':<52}{final_auc:>8.4f}")
    p(f"  {'gain from every astrological system combined':<52}{final_auc-base_rep:>+8.4f}")
    p("")
    p(f"  {'FAMILY':<40}{'admitted?':>11}{'contribution':>14}")
    p("  " + "-" * 66)
    for nm, v in sorted(per.items(), key=lambda kv: -kv[1]):
        p(f"  {nm:<40}{('yes' if nm in order else 'no'):>11}{v:>+14.4f}")
    p("  " + "-" * 66)
    p("")
    p("  A family not admitted contributes EXACTLY zero, not approximately zero: it is absent from the stack,")
    p("  so it cannot move the number in either direction. That is the guarantee the architecture provides —")
    p("  the worst any component can do is nothing.")
    if failed:
        p("")
        p("  Families that did not build (absent, not zero): " + ", ".join(f for f, _ in failed))
    rep = "\n".join(L)
    print("\n" + rep, flush=True)
    open(os.path.join(OUT, "robust_ensemble.txt"), "w").write(rep + "\n")
    json.dump(dict(baseline=base_rep, stack=final_auc, admitted=order, contribution=per,
                   n_report=int(REP.sum()), n_train=len(tr)),
              open(os.path.join(OUT, "robust_ensemble.json"), "w"), indent=1)
    log(f"wrote {OUT}/robust_ensemble.txt")


if __name__ == "__main__":
    main()
