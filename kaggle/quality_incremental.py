"""quality_incremental.py — does the doctrine add ANYTHING once birth era is already known?

Filtering statements by how era-loaded they are (quality_windowfit.py) answers a related but weaker
question, and it throws away data. This is the direct test, and it is the one a referee would ask for:

  1. Fit the era model — a logistic on the two birth decades — on the training couples.
  2. Take its out-of-fold prediction and form the RESIDUAL of the label: what era cannot explain.
  3. Fit the full doctrine bank, unfiltered, against that residual.
  4. On the held-out couples compare THREE scores: era alone, doctrine alone, and era + doctrine.

If astrology carries information about marriage quality that is not era, step 4 shows era+doctrine
beating era alone by more than the test set can resolve. If it does not, the doctrine's apparent skill
was era wearing a Neptune costume — and this says so with the whole bank in play and nothing excluded,
so it cannot be dismissed as an artefact of the filter.

Everything is out-of-fold on the training side; the test set is read once, for three declared scores.

Usage: quality_incremental.py <corpus_dir>
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
ALPHAS = (1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 4e-3, 8e-3)


def decades(df):
    return np.column_stack([pd.to_numeric(df.dob_a.str[:4]) // 10,
                            pd.to_numeric(df.dob_b.str[:4]) // 10]).astype(float)


def main():
    from sklearn.linear_model import Lasso, LogisticRegression
    tr = pd.read_csv(f"{D}/train.csv", dtype=str)
    te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    yi = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
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
    Dtr, Dte = decades(tr), decades(te)

    print(f"  {os.path.basename(D)} · train {len(tr):,} · test {len(te):,} · "
          f"bank {X.shape[1]:,} pair-only doctrine statements\n")

    # 1-2. out-of-fold era prediction, and the residual it leaves behind
    era_oof = np.zeros(len(yi))
    for k in range(5):
        lo = LogisticRegression(max_iter=2000).fit(Dtr[fold != k], yi[fold != k])
        era_oof[fold == k] = lo.predict_proba(Dtr[fold == k])[:, 1]
    print(f"  era model, out-of-fold on train: AUC {G.auc(yi, era_oof):.4f}")
    resid = yi - era_oof

    # 3. the doctrine against what era leaves unexplained
    best = None
    for alpha in ALPHAS:
        oof = np.full(len(yi), np.nan); nz = []
        for k in range(5):
            m = Lasso(alpha=alpha, positive=True, max_iter=8000).fit(X[fold != k], resid[fold != k])
            surv = np.where(m.coef_ > 0)[0]; nz.append(len(surv))
            oof[fold == k] = X[fold == k][:, surv] @ m.coef_[surv] if len(surv) else 0.0
        # does adding this to era improve the OOF ranking?
        a_comb = G.auc(yi, era_oof + oof)
        a_doc = G.auc(yi, oof) if np.ptp(oof) > 0 else 0.5
        print(f"    alpha={alpha:<7} rules ~{int(np.mean(nz)):>4} · "
              f"doctrine-on-residual OOF {a_doc:.4f} · era+doctrine OOF {a_comb:.4f}")
        if best is None or a_comb > best[1]:
            best = (alpha, a_comb)
    alpha, cv = best
    print(f"\n  CV winner: alpha={alpha} (era+doctrine OOF {cv:.4f})")

    # 4. one test read: three declared scores
    lo = LogisticRegression(max_iter=2000).fit(Dtr, yi)
    era_te = lo.predict_proba(Dte)[:, 1]
    m = Lasso(alpha=alpha, positive=True, max_iter=12000).fit(X, resid)
    surv = np.where(m.coef_ > 0)[0]
    doc_te = Xt[:, surv] @ m.coef_[surv] if len(surv) else np.zeros(len(yte))
    a_era = G.auc(yte, era_te)
    a_doc = G.auc(yte, doc_te) if np.ptp(doc_te) > 0 else 0.5
    a_comb = G.auc(yte, era_te + doc_te)
    bp = f"{os.path.dirname(D)}/{os.path.basename(D)}_benchmark.json"
    se = json.load(open(bp))["auc_se"] if os.path.exists(bp) else float("nan")
    print(f"\n  TEST (read once) · {len(surv)} doctrine rules survive on the residual")
    print(f"    era alone                {a_era:.4f}")
    print(f"    doctrine alone           {a_doc:.4f}")
    print(f"    era + doctrine           {a_comb:.4f}")
    print(f"\n    what the doctrine ADDS to era: {a_comb - a_era:+.4f} = "
          f"{(a_comb - a_era) / se:+.2f} standard errors (SE {se:.4f})")
    verdict = ("the doctrine adds real information beyond era"
               if (a_comb - a_era) / se > 2 else
               "the doctrine adds nothing beyond era that this test set can resolve")
    print(f"    VERDICT: {verdict}")
    if len(surv):
        w = {names[i]: float(m.coef_[i]) for i in surv}
        for k_, v in sorted(w.items(), key=lambda kv: -kv[1])[:10]:
            print(f"      {k_[:74]:<76} +{v:.4f}")
    json.dump({"corpus": os.path.basename(D), "alpha": alpha,
               "era_auc": float(a_era), "doctrine_auc": float(a_doc), "combined_auc": float(a_comb),
               "increment": float(a_comb - a_era), "increment_se": float((a_comb - a_era) / se),
               "n_rules": int(len(surv)), "verdict": verdict},
              open(f"{os.path.dirname(D)}/{os.path.basename(D)}_incremental.json", "w"), indent=1)


if __name__ == "__main__":
    main()
