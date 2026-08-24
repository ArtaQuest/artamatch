"""
deploy_match.py — the deployment model, trained on EVERY row, scoring one person against candidate partners.

Operator: "the inference model should be trained on the entire dataset." So train and test are concatenated
here; there is no held-out half left, and this file therefore reports NO accuracy figure. The AUC that belongs
to this model is the one measured earlier under a proper split, not anything computable from this fit.
"""
import os
import sys

import numpy as np
import pandas as pd

D = os.environ.get("AQ_DATA", os.path.expanduser("~/.artamatch-dev/sep4"))
ME = os.environ.get("AQ_ME", "1994-02-15")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
NOW = 2026.0


def mech_prior(ymin, ymax, wed_age=25.0, lam=0.017, now=NOW, dt=1.0):
    """Competing risks: divorce at a constant hazard against Gompertz mortality of either partner. This is the
    single strongest term in the winning pipeline, and no parameter in it is fitted to the data."""
    wed = ymax + wed_age
    T = np.clip(now - wed, 0.0, 120.0)
    a0, b0 = wed - ymin, wed - ymax
    k, b = 8.5e-5, 0.085
    n = len(ymin)
    pdiv = np.zeros(n); pdth = np.zeros(n); surv = np.ones(n); t = np.zeros(n)
    for _ in range(int(120 / dt)):
        act = t < T
        if not act.any():
            break
        hd = k * np.exp(b * np.clip(a0 + t, 0, 140)) + k * np.exp(b * np.clip(b0 + t, 0, 140))
        tot = hd + lam
        ev = surv * (1 - np.exp(-tot * dt))
        pdiv += np.where(act, ev * lam / np.maximum(tot, 1e-12), 0.0)
        pdth += np.where(act, ev * hd / np.maximum(tot, 1e-12), 0.0)
        surv *= np.where(act, np.exp(-tot * dt), 1.0)
        t += dt
    tot = pdiv + pdth
    return np.where(tot > 1e-12, pdiv / np.maximum(tot, 1e-12), 0.5)


def main():
    import xgboost as xgb
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    te = te.merge(sol, on="id")
    allrows = pd.concat([tr[["dob_a", "dob_b", "ended_in_divorce"]],
                         te[["dob_a", "dob_b", "ended_in_divorce"]]], ignore_index=True)
    y = pd.to_numeric(allrows.ended_in_divorce).to_numpy().astype(int)
    print(f"  trained on EVERY row: {len(allrows):,} pairs ({y.mean():.1%} artificial)", flush=True)

    yr = lambda s: pd.to_numeric(s.astype(str).str[:4], errors="coerce").replace(0, np.nan)
    def feats(a, b):
        ya, yb = yr(pd.Series(a)), yr(pd.Series(b))
        lo, hi = np.fmin(ya, yb), np.fmax(ya, yb)
        mp = mech_prior(np.nan_to_num(lo, nan=1900.0).astype(float), np.nan_to_num(hi, nan=1900.0).astype(float))
        full = lambda s: pd.Series(s).astype(str).str.match(r"^\d{4}-(?!00)\d{2}-(?!00)\d{2}$").to_numpy(float)
        return np.column_stack([hi, lo, (hi - lo).abs(), mp, full(a) * 2 + full(b)])

    X = feats(allrows.dob_a.values, allrows.dob_b.values)
    m = xgb.XGBClassifier(n_estimators=400, learning_rate=0.04, max_depth=4, min_child_weight=40,
                          subsample=0.8, colsample_bytree=0.8, reg_lambda=20.0, verbosity=0)
    m.fit(X, y)

    imp = m.get_booster().get_score(importance_type="gain")
    names = ["later_birth_year", "earlier_birth_year", "age_gap", "MECHANISTIC mortality prior", "date_precision"]
    tot = sum(imp.values()) or 1
    print("\n  what the deployed model actually weighs (gain):")
    for i, nm in enumerate(names):
        print(f"    {nm:<32}{100*imp.get(f'f{i}',0)/tot:>6.1f}%")

    print(f"\n  Scoring {ME} (male) against every candidate partner birth year:\n")
    print(f"  {'partner born':<14}{'their age now':>14}{'age gap':>9}{'P(divorce | it ends)':>23}")
    print("  " + "-" * 62)
    rows = []
    for py in range(1930, 2009, 2):
        cand = f"{py}-06-15"
        p = float(m.predict_proba(feats([ME], [cand]))[0, 1])
        rows.append((py, p))
    for py, p in rows:
        mark = ""
        if p == min(r[1] for r in rows):
            mark = "  <- the model's 'best match'"
        if py % 8 == 2 or mark:
            print(f"  {py:<14}{int(2026-py):>14}{abs(1994-py):>9}{p:>22.1%}{mark}")
    best = min(rows, key=lambda r: r[1])
    print("  " + "-" * 62)
    print(f"\n  BEST MATCH by the model: born {best[0]}, currently {int(2026-best[0])} years old, "
          f"P(divorce) = {best[1]:.1%}")
    same = [p for py, p in rows if py == 1994][0]
    print(f"  Someone your own age (1994): P(divorce) = {same:.1%}")


if __name__ == "__main__":
    main()
