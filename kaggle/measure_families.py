"""
measure_families.py — measure every candidate family under SEVERAL honest gates, not one.

The standing order (memory: feedback_artamatch_never_give_up_on_the_search) is to exhaust the search before
reporting anything, and one of the five things to exhaust is the ADMISSION CRITERION. "Must improve every
forward-chained fold" is the strictest gate in the drawer; a real but weak effect can fail it on one unlucky
fold. Reporting only that gate would be giving up early by another name.

So every family is scored under four, side by side:

POWER FIRST, BECAUSE IT TURNED OUT TO BE THE BINDING CONSTRAINT. The single held-out test half is 2,801 rows,
and by Hanley-McNeil its standard error on an AUC of 0.576 is 0.0111. The standard error of a GAIN between two
correlated models on those same rows is 0.0035-0.0086 depending on how alike they are, so the smallest gain
detectable at three sigma is between +0.011 and +0.026. The largest gain any astrology family has produced in
this entire project is +0.009. THE TEST SET HAS BEEN TOO SMALL TO SEE THE SIZE OF EFFECT WE ARE LOOKING FOR --
a real +0.005 would have been invisible, and every null so far is partly a statement about the sample, not only
about the doctrine.

Resolving +0.005 at three sigma needs roughly 25,000 test rows, which is ~208,000 ended unions; Wikidata holds
about 97,000 statements in total. So a single holdout cannot get there, and the fix inside this data is to stop
throwing 85% of the rows away at evaluation time: POOLED FORWARD-CHAINED EVALUATION scores every row that has a
future block behind it, keeping the temporal discipline while multiplying the evaluated rows severalfold. That
is a power improvement, not a loosened control -- no row is ever scored by a model that saw it.

  ALL-FOLDS      the gain must be positive on every forward-chained fold. Strictest. What was used before.
  MEAN-FOLD      the mean fold gain must be positive. Looser, and blind to a single bad fold.
  BOOTSTRAP      resample the TEST rows 2000 times; the 5th percentile of the gain must exceed 0.
  PERMUTATION    shuffle the labels 200 times, refit, and ask how often the shuffled gain matches or beats
                 the real one. This is the only gate that prices in how much a family could win by luck
                 given its size — a 600-column family has far more chances than a 20-column one.

None of these is loosened to let something through. They are reported TOGETHER, and the two controls calibrate
all four at once: a PLANTED answer must pass every gate, pure NOISE must fail every gate. A gate the plant
fails is too tight; a gate the noise passes is too loose. Both facts are printed.
"""
import glob
import importlib.util
import json
import os
import sys
import time

import numpy as np
import pandas as pd

T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

DATA = os.environ.get("AQ_DATA", os.path.expanduser("~/.artamatch-dev/sep2"))
FEAT = os.environ.get("AQ_FEAT", os.path.expanduser("~/.artamatch-dev/sep2feat"))
NEW = os.environ.get("AQ_NEWFAM", os.path.expanduser("~/.artamatch-dev/newfam"))
CODE = os.environ.get("AQ_CODE", os.path.expanduser("~/Studio/artamatch/research/sidereal"))
OUT = os.environ.get("AQ_OUT", os.path.expanduser("~/.artamatch-dev/measure_out"))
SEEDS = [int(v) for v in os.environ.get("AQ_SEEDS", "0,1,2").split(",")]
NBOOT, NPERM = 2000, int(os.environ.get("AQ_NPERM", "200"))
sys.path.insert(0, CODE)
os.makedirs(OUT, exist_ok=True)
import giant_ensemble as G   # noqa: E402


def load_new_modules():
    """Every .py in the candidate directory that exposes build(df, Z, half). A module that raises is REPORTED
    and skipped — a family that failed to build is not a family that contributed nothing."""
    mods, bad = {}, []
    for p in sorted(glob.glob(os.path.join(NEW, "*.py"))):
        nm = os.path.basename(p)[:-3]
        try:
            spec = importlib.util.spec_from_file_location(f"newfam_{nm}", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            if not hasattr(m, "build"):
                bad.append((nm, "no build()")); continue
            mods[nm] = m.build
        except Exception as e:
            bad.append((nm, f"{type(e).__name__}: {e}"))
    return mods, bad


def main():
    import xgboost as xgb
    params, on_gpu = G.gpu_params()
    tr = pd.read_csv(os.path.join(DATA, "train.csv"), dtype=str)
    te = pd.read_csv(os.path.join(DATA, "test.csv"), dtype=str)
    sol = pd.read_csv(os.path.join(DATA, "solution.csv"))
    y = pd.to_numeric(tr["ended_in_divorce"]).to_numpy().astype(np.int64)
    yte = sol["ended_in_divorce"].to_numpy().astype(np.int64)
    Z = np.load(os.path.join(FEAT, "phases.npz"), allow_pickle=True)
    byr = lambda d: np.fmax(pd.to_numeric(d.dob_a.str[:4], errors="coerce").replace(0, np.nan),
                            pd.to_numeric(d.dob_b.str[:4], errors="coerce").replace(0, np.nan))
    assert byr(te).min() > byr(tr).max(), "test is not strictly later-born"
    later = np.nan_to_num(byr(tr).to_numpy(), nan=1900).astype(int)
    cuts = [np.quantile(later, q) for q in (0.40, 0.55, 0.70, 0.85, 1.0)]
    log(f"xgboost {xgb.__version__} · {'GPU' if on_gpu else 'CPU'} · train {len(tr):,} · test {len(te):,}")

    yr = lambda d, c: pd.to_numeric(d[c].str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    full = lambda d, c: d[c].fillna("").str.match(r"^\d{4}-(?!00)\d{2}-(?!00)\d{2}$").to_numpy(float)
    base = lambda d: np.column_stack([np.fmax(yr(d, "dob_a"), yr(d, "dob_b")), np.fmin(yr(d, "dob_a"), yr(d, "dob_b")),
                                      np.abs(yr(d, "dob_a") - yr(d, "dob_b")), full(d, "dob_a") * 2 + full(d, "dob_b")])
    B, Bte = base(tr), base(te)

    cand = {}
    for fam, adapt, _ in G.FAMILIES:                    # the existing catalogue
        try:
            X, _n = adapt(tr, Z, "train"); Xt, _ = adapt(te, Z, "test")
            X, Xt = np.asarray(X, np.float32), np.asarray(Xt, np.float32)
            if np.isfinite(X).any() and X.shape[1] == Xt.shape[1]:
                cand[fam] = (X, Xt)
        except Exception as e:
            log(f"  existing {fam}: {type(e).__name__}: {e}")
    newmods, bad = load_new_modules()
    for nm, b in newmods.items():                       # the newly written ones
        try:
            X, _n = b(tr, Z, "train"); Xt, _ = b(te, Z, "test")
            X, Xt = np.asarray(X, np.float32), np.asarray(Xt, np.float32)
            if X.shape[1] != Xt.shape[1]:
                bad.append((nm, f"width {X.shape[1]} vs {Xt.shape[1]}")); continue
            if not np.isfinite(X).any():
                bad.append((nm, "all NaN")); continue
            cand[f"NEW:{nm}"] = (X, Xt)
        except Exception as e:
            bad.append((nm, f"{type(e).__name__}: {e}"))
    rng = np.random.default_rng(7)
    cand["_NOISE_"] = (rng.normal(size=(len(tr), 60)).astype(np.float32), rng.normal(size=(len(te), 60)).astype(np.float32))
    cand["_PLANT_"] = ((y * 2.0 - 1 + rng.normal(scale=1.5, size=len(tr))).reshape(-1, 1).astype(np.float32),
                       (yte * 2.0 - 1 + rng.normal(scale=1.5, size=len(te))).reshape(-1, 1).astype(np.float32))
    log(f"{len(cand)} candidates ({len(newmods)} newly written, {len(bad)} failed to build)")
    for nm, why in bad:
        log(f"   FAILED {nm}: {why}")

    def oof_test(X, Xt, seed):
        return G.forward_oof(X, Xt, y, later, cuts, params, seed=seed)

    P = dict(n_estimators=260, learning_rate=0.05, max_depth=4, min_child_weight=40, subsample=0.8,
             colsample_bytree=0.7, reg_lambda=20.0, verbosity=0, n_jobs=4, **params)

    def fit_score(X, Xt, yy, seed):
        c = xgb.XGBClassifier(random_state=seed, **P)
        rows = np.isfinite(X).any(1)
        c.fit(X[rows], yy[rows])
        m = np.isfinite(Xt).any(1)
        s = np.full(len(Xt), np.nan); s[m] = c.predict_proba(Xt[m])[:, 1]
        return s

    base_scores = [fit_score(B, Bte, y, s) for s in SEEDS]
    base_t = G.auc(yte, np.nanmean(np.column_stack(base_scores), 1))
    log(f"baseline on test: {base_t:.4f}")

    qs = np.quantile(later, np.linspace(0, 1, 5)[1:-1])
    results = {}
    for nm, (X, Xt) in cand.items():
        XA, XAt = np.column_stack([B, X]), np.column_stack([Bte, Xt])
        s = np.nanmean(np.column_stack([fit_score(XA, XAt, y, sd) for sd in SEEDS]), 1)
        a = G.auc(yte, s); gain = a - base_t
        # BOOTSTRAP: resample the test rows, so the interval reflects how few of them there are
        bmean = np.nanmean(np.column_stack(base_scores), 1)
        idx = np.random.default_rng(11).integers(0, len(yte), size=(NBOOT, len(yte)))
        bs = np.array([G.auc(yte[i], s[i]) - G.auc(yte[i], bmean[i]) for i in idx])
        lo = float(np.percentile(bs, 5))
        # PERMUTATION: shuffle the LABELS, refit the whole thing, and see how often a family of this size wins
        # this much by luck alone. This is the only gate that prices in width — 600 columns get far more
        # chances to fit noise than 20 do, and no fold rule or bootstrap knows that.
        prng = np.random.default_rng(23)
        pg = []
        for _ in range(NPERM):
            yp = prng.permutation(y)
            sp = fit_score(XA, XAt, yp, 0); sb = fit_score(B, Bte, yp, 0)
            pg.append(G.auc(yte, sp) - G.auc(yte, sb))
        pg = np.array(pg)
        pval = float((pg >= gain).mean())
        # fold gains, forward-chained inside train — and POOLED, so the gain is also measured on every
        # training row that has a past to be fitted on, not only on the 2,801 held-out rows
        fg = []
        pool_a = np.full(len(y), np.nan); pool_b = np.full(len(y), np.nan)
        for k, q in enumerate(qs):
            f, e = later <= q, later > q
            if k + 1 < len(qs):
                e = e & (later <= qs[k + 1])          # each row scored ONCE, by the latest model before it
            if f.sum() < 500 or e.sum() < 300 or min(y[f].sum(), (1 - y[f]).sum()) < 100:
                continue
            sb = fit_score(B[f], B[e], y[f], 0); sa = fit_score(XA[f], XA[e], y[f], 0)
            fg.append(G.auc(y[e], sa) - G.auc(y[e], sb))
            pool_a[e] = sa; pool_b[e] = sb
        fg = np.array(fg) if fg else np.array([np.nan])
        pm = np.isfinite(pool_a) & np.isfinite(pool_b)
        pooled_gain = (G.auc(y[pm], pool_a[pm]) - G.auc(y[pm], pool_b[pm])) if pm.sum() > 500 else np.nan
        pooled_n = int(pm.sum())
        gates = {"all-folds": float(np.nanmin(fg)) > 0, "mean-fold": float(np.nanmean(fg)) > 0,
                 "bootstrap": lo > 0, "permutation": pval < 0.05}
        results[nm] = dict(auc=a, gain=gain, boot_lo=lo, perm_p=pval, perm_null_95=float(np.percentile(pg, 95)),
                           fold_min=float(np.nanmin(fg)), fold_mean=float(np.nanmean(fg)),
                           pooled_gain=float(pooled_gain), pooled_n=pooled_n,
                           n_features=int(X.shape[1]), gates=gates, n_gates_passed=int(sum(gates.values())))
        log(f"  {nm[:32]:<34} AUC {a:.4f} gain {gain:+.4f} | folds min {np.nanmin(fg):+.4f} mean "
            f"{np.nanmean(fg):+.4f} | boot5% {lo:+.4f} | perm p={pval:.3f} (null95 {np.percentile(pg,95):+.4f})"
            f" | POOLED {pooled_gain:+.4f} on {pooled_n:,} | {sum(gates.values())}/4 gates")
    # the controls calibrate every gate at once, and both facts are printed
    pl, no = results.get("_PLANT_"), results.get("_NOISE_")
    if pl and no:
        log("")
        log(f"CONTROL CALIBRATION  ({'PASS' if pl['n_gates_passed'] == 4 and no['n_gates_passed'] == 0 else 'CHECK'})")
        log(f"  planted answer passes {pl['n_gates_passed']}/4 gates  (must be 4 — fewer means a gate is too "
            f"tight to see a real effect)")
        log(f"  pure noise    passes {no['n_gates_passed']}/4 gates  (must be 0 — more means a gate is too "
            f"loose to stop a fake one)")
    json.dump(dict(baseline=base_t, results=results, failed=dict(bad)),
              open(os.path.join(OUT, "measure.json"), "w"), indent=1)
    log(f"wrote {OUT}/measure.json")


if __name__ == "__main__":
    main()
