"""
pure_astro.py — ONLY astrology and numerology, and only what can score a couple who are not in any dataset.

Operator: "you must only use astrology/numerology models that predict futures."

WHAT IS REMOVED, and why each one had to go:

  MECHANISTIC MORTALITY PRIOR   a Gompertz hazard against a constant divorce rate. The single strongest term
                                in the winning pipeline and its author called it "pure physics". It is
                                actuarial science, not a doctrine.
  OCCURRENCE / LINK COUNTS      how many rows a birth date appears in, and whether a partner was born later
                                than the one in this row. Worth ~0.06 AUC on their own — more, by the author's
                                own account, than everything else combined — and they are disqualified twice
                                over: they are computed by pooling BOTH halves of the data, and they cannot
                                exist for a couple who are not already in the corpus. A model that needs you
                                to have appeared in it before cannot predict anybody's future.
  DATE PRECISION                how completely a birth date happens to be recorded. That is a fact about
                                Wikidata's editors, and for a living person asking about their own future it
                                is always "fully recorded" — a constant, carrying nothing.
  RAW BIRTH YEAR AS AN INTEGER  the bare number. The slow bodies still carry the era, and by the operator's
                                own argument that IS the astrological channel — Pluto's longitude over 248
                                years is the birth year in astrological dress. So era reaches the model, but
                                only through a planet, never through a calendar integer.

WHAT REMAINS is every family in the catalogue: sidereal longitudes of 14 bodies for both partners, their arcs
and aspects, the varga charts, Arabic lots, midpoint trees, BaZi, the fixed stars, declinations and dignities,
the world calendars, the numerologies. All pure functions of two dates, all computable for anybody alive or
unborn.
"""
import glob
import importlib.util
import os
import re
import sys

import numpy as np
import pandas as pd

D = os.environ.get("AQ_DATA", os.path.expanduser("~/.artamatch-dev/sep4"))
FEAT = os.environ.get("AQ_FEAT", os.path.expanduser("~/.artamatch-dev/sep4feat"))
NEW = os.environ.get("AQ_NEWFAM", os.path.expanduser("~/.artamatch-dev/newfam"))
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G   # noqa: E402

# a feature is disqualified if its NAME shows it is a calendar integer, a record-keeping artefact, or a count
BANNED = re.compile(r"(birth_year|later_birth|earlier_birth|start_year|precision|day_precision|year_only|"
                    r"coverage|valid_frac|hit_count|_count$|census|n_known|occurrence)", re.I)


def load_families(df, Z, half):
    """Every family module, with disqualified columns dropped by name."""
    X, names = [], []
    for fam, adapt, _ in G.FAMILIES:
        try:
            x, n = adapt(df, Z, half)
            x = np.asarray(x, np.float32)
            keep = [i for i, nm in enumerate(n) if not BANNED.search(nm)]
            if keep and np.isfinite(x[:, keep]).any():
                X.append(x[:, keep]); names += [f"{fam}:{n[i]}" for i in keep]
        except Exception:
            pass
    for p in sorted(glob.glob(os.path.join(NEW, "*.py"))):
        nm = os.path.basename(p)[:-3]
        try:
            spec = importlib.util.spec_from_file_location(f"nf_{nm}", p)
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            x, n = m.build(df, Z, half)
            x = np.asarray(x, np.float32)
            keep = [i for i, q in enumerate(n) if not BANNED.search(q)]
            if keep and np.isfinite(x[:, keep]).any():
                X.append(x[:, keep]); names += [f"{nm}:{n[i]}" for i in keep]
        except Exception:
            pass
    return (np.column_stack(X).astype(np.float32) if X else np.zeros((len(df), 0), np.float32)), names


def main():
    import xgboost as xgb
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{FEAT}/phases.npz", allow_pickle=True)

    Xtr, names = load_families(tr, Z, "train")
    Xte, _ = load_families(te, Z, "test")
    print(f"  {Xtr.shape[1]:,} purely astrological/numerological features "
          f"(every calendar integer, precision flag and count removed)", flush=True)

    byr = lambda d: np.fmax(pd.to_numeric(d.dob_a.str[:4], errors="coerce").replace(0, np.nan),
                            pd.to_numeric(d.dob_b.str[:4], errors="coerce").replace(0, np.nan))
    later = np.nan_to_num(byr(tr).to_numpy(), nan=1900).astype(int)
    P = dict(n_estimators=400, learning_rate=0.04, max_depth=5, min_child_weight=30, subsample=0.8,
             colsample_bytree=0.6, reg_lambda=20.0, verbosity=0, n_jobs=4)

    # honest measurement first: fit on train only, read test once
    s = np.mean([xgb.XGBClassifier(random_state=k, **P).fit(Xtr, ytr).predict_proba(Xte)[:, 1] for k in (0, 1, 2)], 0)
    auc = G.auc(yte, s)
    print(f"\n  TEST AUC of pure astrology + numerology, trained on the training half only: {auc:.4f}")
    print(f"  (chance is 0.5000; the disqualified pipeline reported 0.6548 with mortality and occurrence counts)")

    # then the deployment fit, on every row, as instructed
    allrows = pd.concat([tr[["dob_a", "dob_b"]], te[["dob_a", "dob_b"]]], ignore_index=True)
    allrows["start"] = "0000-00-00"
    y = np.concatenate([ytr, yte])
    Xall = np.vstack([Xtr, Xte])
    m = xgb.XGBClassifier(random_state=0, **P).fit(Xall, y)
    print(f"  deployment model refitted on all {len(y):,} pairs", flush=True)
    np.savez_compressed(os.path.expanduser("~/.artamatch-dev/pure_astro.npz"),
                        names=np.array(names, dtype=object), test_auc=auc)
    m.save_model(os.path.expanduser("~/.artamatch-dev/pure_astro.json"))
    print("  saved model + feature list")


if __name__ == "__main__":
    main()
