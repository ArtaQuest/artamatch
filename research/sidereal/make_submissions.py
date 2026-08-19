"""
make_submissions.py — the third edition's leaderboard entries, from the best models so far.

  1  plain            LightGBM on the two ages at the start, the gap and the start year (the honest bar)
  2  artamodel        ArtaModel 3-term, BOOSTED over SPLIT single-sum fields (the best construction of the study),
                      fitted on every training row that has both natal charts (the wedding terms present where
                      the day is known, dropped otherwise), applied to every test row the same way
  3  ensemble         equal-weight rank average of 1, 2 and the pre-registered sidereal pool

Nothing here reads solution.csv. Choices inside the fit are on the inner temporal split, as everywhere.
Usage: AQ_PHASES=/tmp/aq3feat/phases.npz AQ_FEAT=/tmp/aq3feat/sidereal.npz AQ_OUT=/tmp/aq3sub python make_submissions.py
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from artamodel import BODIES14, phase_matrix                                          # noqa: E402
from artamodel_ensemble import boost                                                   # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz")
FEAT = os.environ.get("AQ_FEAT", "/tmp/aq3feat/sidereal.npz")
OUT = os.environ.get("AQ_OUT", "/tmp/aq3sub")
os.makedirs(OUT, exist_ok=True)


def r01(v):
    r = rankdata(v); return (r - 1) / max(1.0, len(r) - 1)


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True)
    bodies = list(Z["bodies"]); ids = Z["id_test"]; y = Z["y_train"].astype(np.int64)
    Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]
    Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    later = Z["yr_train"].astype(int).max(1)
    j1 = ptr[:, pn.index("start_is_jan1")] == 1.0; j1e = pte[:, pn.index("start_is_jan1")] == 1.0
    Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    LABEL = "lasted_30_years"

    # 1 plain
    cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
    Xtr, Xte = ptr[:, cols], pte[:, cols]
    ok = np.isfinite(Xtr).all(1)
    p_plain = np.zeros(len(Xte))
    for sd in range(5):
        c = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=50, reg_lambda=10.0,
                               random_state=sd, verbose=-1).fit(Xtr[ok], y[ok])
        p_plain += c.predict_proba(Xte)[:, 1]
    p_plain /= 5
    pd.DataFrame({"id": ids, LABEL: p_plain}).to_csv(f"{OUT}/submission_plain.csv", index=False)
    print(f"  1 plain: fitted on {int(ok.sum()):,} rows")

    # 2 ArtaModel 3-term boosted over split per phasor, on CHARTS rows (both natal charts), presence rule
    B = [bodies.index(b) for b in BODIES14]
    charts = np.isfinite(Dtr[:, B]).all(1) & np.isfinite(Mtr[:, B]).all(1)
    P, labels = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, ("a", "m", "d")); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, ("a", "m", "d"))
    lat = later[charts]; inner = lat > np.quantile(lat, 0.85)
    masks = [np.isin(np.arange(len(labels)), [k]) for k in range(len(labels))]
    iv, K, s_arta = boost(P[charts], y[charts], inner, Pe, stages=min(120, 4 * len(labels)), nu=0.1, masks=masks)
    print(f"  2 ArtaModel boosted-over-split: fitted on {int(charts.sum()):,} rows · inner {iv:.4f} · {K} stages")
    pd.DataFrame({"id": ids, LABEL: r01(s_arta)}).to_csv(f"{OUT}/submission_artamodel.csv", index=False)

    # 3 ensemble with the sidereal pool
    pool = pd.read_csv(os.path.join(os.path.dirname(FEAT), "submission.csv"))
    assert (pool.id.to_numpy() == ids).all(), "pool ids differ"
    ens = np.mean([r01(p_plain), r01(s_arta), r01(pool[LABEL].to_numpy())], 0)
    pd.DataFrame({"id": ids, LABEL: ens}).to_csv(f"{OUT}/submission_ensemble.csv", index=False)
    print(f"  3 ensemble: plain + ArtaModel + sidereal pool, equal-weight ranks")
    print(f"  wrote {OUT}/submission_{{plain,artamodel,ensemble}}.csv over {len(ids):,} test rows")


if __name__ == "__main__":
    main()
