"""quality_windowfit.py — is there any doctrine signal LEFT once birth era is taken away?

The unrestricted fit selects outer-planet phase markers under every fold seed: Neptune-Pluto phase,
Pluto sign, the long saturn-pluto cycles. Two birth decades and two parameters score as well or better.
Those rules also cannot do the product's job: ArtaMatch ranks HER candidate dates within +/-12 years of a
fixed date, and a Neptune-Pluto phase is constant across such a window, so the ranking it produces is
flat. A model that reads only era is both unproven and unshippable.

This asks the sharper question. Every statement in the bank is scored for how strongly it encodes birth
era — the absolute difference in mean birth year between the couples it fires on and the couples it does
not, in years. Statements above a ceiling are removed, and the same regularised fit runs on what remains.

  AQ_ETA_MAX   share of a statement's variance birth decade may explain  (default 0.05)
  AQ_OUT       where to write the model

What survives is doctrine that distinguishes couples born in the SAME period — which is the only kind
that can rank dates inside a 12-year window, and the only kind the era control cannot explain.

Usage: quality_windowfit.py <corpus_dir> <out_model.json>
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
from v12_fit import side
from denylist import clause_ok

D = os.path.expanduser(sys.argv[1])
OUT = os.path.expanduser(sys.argv[2])
ETA_MAX = float(os.environ.get("AQ_ETA_MAX", "0.05"))
ALPHAS = (2e-4, 5e-4, 1e-3, 2e-3, 4e-3, 8e-3)


def main():
    from sklearn.linear_model import Lasso, LogisticRegression
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(float)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    yi = ytr.astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)

    X6, n6 = V6.bank(tr, Z, "train"); X6t, _ = V6.bank(te, Z, "test")
    XA, nA = V7.additions(tr, Z, "train"); XAt, _ = V7.additions(te, Z, "test")
    XL, nL = V8.last_singles(tr, Z, "train"); XLt, _ = V8.last_singles(te, Z, "test")
    ex1 = set(n6 + nA + nL)
    XN, nN = V13.new_singles(tr, Z, "train", ex1); XNt, _ = V13.new_singles(te, Z, "test", ex1)
    X = np.column_stack([X6, XA, XL, XN]); Xt = np.column_stack([X6t, XAt, XLt, XNt])
    names = n6 + nA + nL + nN
    del X6, XA, XL, XN, X6t, XAt, XLt, XNt

    floor = max(40, int(0.02 * len(tr)))
    keep = np.array([clause_ok(n) for n in names]) & (X.sum(0) >= floor) \
        & np.array([side(n) == "AB" for n in names])
    X, Xt = X[:, keep], Xt[:, keep]
    names = [n for n, k in zip(names, keep) if k]

    yr = pd.to_numeric(tr.dob_a.str[:4]).to_numpy(float)
    yr_b = pd.to_numeric(tr.dob_b.str[:4]).to_numpy(float)
    mid = (yr + yr_b) / 2.0
    # How era-loaded is each statement? A difference of MEAN birth year is the obvious measure and it is
    # NOT sufficient: a cyclical statement can fire heavily in the 1850s and again in the 1950s, matching
    # the overall mean exactly while being entirely determined by era. That blind spot let
    # cycle24_neptune_pluto=21 through with a mean gap of 1 year.
    # The measure used instead is eta^2 — the share of the statement's variance explained by the couple's
    # birth DECADE, which is 1.0 for a fully era-determined statement and 0 for one independent of era.
    # It is on a natural scale, it is blind to nothing cyclical, and the bank's own distribution sets a
    # sane cut: median 0.009, ninetieth percentile 0.24, and the Neptune-Pluto phase markers at 0.79-0.83.
    dec = (mid // 10).astype(int)
    decs = [d for d in np.unique(dec) if (dec == d).sum() >= 30]
    era_gap = np.zeros(X.shape[1]); eta2 = np.zeros(X.shape[1])
    for j in range(X.shape[1]):
        f = (X[:, j] > 0).astype(float); p = f.mean()
        if p <= 0 or p >= 1:
            era_gap[j], eta2[j] = 1e9, 1.0
            continue
        era_gap[j] = abs(mid[f > 0].mean() - mid[f == 0].mean())
        eta2[j] = sum((dec == d).sum() * (f[dec == d].mean() - p) ** 2 for d in decs) / (len(f) * p * (1 - p))
    era_ok = eta2 <= ETA_MAX
    print(f"  {os.path.basename(D)}: bank {X.shape[1]:,} pair-only doctrine statements")
    print(f"  era loading (eta^2 on birth decade): median {np.median(eta2):.3f} · "
          f"90th pct {np.percentile(eta2, 90):.3f} · max {eta2.max():.3f}")
    print(f"  keeping the {int(era_ok.sum()):,} statements with eta^2 <= {ETA_MAX} "
          f"({era_ok.mean():.0%} of the bank)")
    caught = (era_gap <= 3) & ~era_ok
    if caught.any():
        cj = np.argsort(-np.where(caught, eta2, -1))[:4]
        print("  era-determined DESPITE a flat mean birth year (what a mean-gap filter misses): "
              + " · ".join(f"{names[j]} (gap {era_gap[j]:.0f}y, eta2 {eta2[j]:.2f})" for j in cj))
    X, Xt = X[:, era_ok], Xt[:, era_ok]
    names = [n for n, k in zip(names, era_ok) if k]
    if X.shape[1] < 10:
        print("  too few statements survive to fit"); return

    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    gid = pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]
    fold = np.random.default_rng(7).integers(0, 5, gid.max() + 1)[gid]

    best = None
    for alpha in ALPHAS:
        oof = np.full(len(ytr), np.nan); nz = []
        for k in range(5):
            m = Lasso(alpha=alpha, positive=True, max_iter=8000).fit(X[fold != k], ytr[fold != k])
            surv = np.where(m.coef_ > 0)[0]; nz.append(len(surv))
            if len(surv) >= 2:
                w, b = G.fit_nonneg(X[fold != k][:, surv], yi[fold != k],
                                    np.ones(int((fold != k).sum())))
                oof[fold == k] = X[fold == k][:, surv] @ w + b
            else:
                oof[fold == k] = 0.0
        a_cv = G.auc(yi, oof)
        print(f"    alpha={alpha:<7} CV {a_cv:.4f} · rules ~{int(np.mean(nz))}", flush=True)
        if best is None or a_cv > best[1]:
            best = (alpha, a_cv)
    alpha, cv = best
    print(f"\n  CV winner: alpha={alpha} (CV {cv:.4f})")
    m = Lasso(alpha=alpha, positive=True, max_iter=12000).fit(X, ytr)
    surv = np.where(m.coef_ > 0)[0]
    if len(surv) < 2:
        print("  fewer than two rules survive — nothing to declare"); return
    w, b0 = G.fit_nonneg(X[:, surv], yi, np.ones(len(yi)))
    auc = G.auc(yte, Xt[:, surv] @ w + b0)
    weights = {names[i]: float(v) for i, v in zip(surv, w) if v > 0}

    dec_tr = np.column_stack([pd.to_numeric(tr.dob_a.str[:4]) // 10, pd.to_numeric(tr.dob_b.str[:4]) // 10]).astype(float)
    dec_te = np.column_stack([pd.to_numeric(te.dob_a.str[:4]) // 10, pd.to_numeric(te.dob_b.str[:4]) // 10]).astype(float)
    era = G.auc(yte, LogisticRegression(max_iter=2000).fit(dec_tr, yi).predict_proba(dec_te)[:, 1])
    bm = {}
    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    if os.path.exists(bp):
        bm = json.load(open(bp))
    se = bm.get("auc_se", float("nan"))
    print(f"\n  {len(weights)} era-free doctrine rules · TEST AUC (read once): {auc:.4f}")
    print(f"    chance 0.5000 · age gap {bm.get('age_gap_auc', float('nan')):.4f} · "
          f"birth-decade control {era:.4f} · SE {se:.4f}")
    print(f"    above chance by {auc - 0.5:+.4f} = {(auc - 0.5) / se:+.2f} SE")
    print(f"    vs the era control  {auc - era:+.4f} = {(auc - era) / se:+.2f} SE")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:14]:
        print(f"    {k_[:78]:<80} +{v:.4f}")
    json.dump({"model": f"ArtaMatch quality, era-free doctrine (birth-decade eta^2 <= {ETA_MAX})",
               "alpha": alpha, "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4),
               "era_control_auc": round(float(era), 4), "era_eta2_max": ETA_MAX,
               "intercept": float(b0), "n_bank": int(X.shape[1]), "n_surviving": len(weights),
               "benchmark": bm, "weights": weights}, open(OUT, "w"), indent=1)
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
