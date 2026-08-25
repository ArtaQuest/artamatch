"""
v9_fit.py — descend the interaction path v8 opened. v8's relaxed CV peaked at the EDGE of its alpha grid
(0.7636 at 1e-4, still rising) and its product pool stopped at the top-120 singles. v9 widens both:
pool from a 5e-5 Lasso, products from the top-200, alpha grid extended to 3e-5.
Test is read ONLY if CV beats v8's declared 0.7636 — otherwise v8 stands and no read is spent.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8
D = os.path.expanduser("~/.artamatch-dev/remar_sh")
V8_CV = 0.7636

def main():
    from sklearn.linear_model import Lasso
    tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv"); ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(float)
    yte = sol.ended_in_divorce.to_numpy().astype(int); yi = ytr.astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X6, n6 = V6.bank(tr, Z, "train"); X6t, _ = V6.bank(te, Z, "test")
    XA, nA = V7.additions(tr, Z, "train"); XAt, _ = V7.additions(te, Z, "test")
    XL, nL = V8.last_singles(tr, Z, "train"); XLt, _ = V8.last_singles(te, Z, "test")
    Xall = np.column_stack([X6, XA, XL]); Xallt = np.column_stack([X6t, XAt, XLt])
    names = n6 + nA + nL
    del X6, XA, XL, X6t, XAt, XLt
    print(f"  singles bank: {Xall.shape[1]:,}", flush=True)

    m0 = Lasso(alpha=5e-5, positive=True, max_iter=12000); m0.fit(Xall, ytr)
    pool = np.where(m0.coef_ > 0)[0]
    if len(pool) > 650:
        pool = pool[np.argsort(-m0.coef_[pool])][:650]
    print(f"  survivor pool at alpha=5e-5: {len(pool)}", flush=True)
    top = pool[np.argsort(-m0.coef_[pool])][:200]
    Xt_top, Xtt_top = Xall[:, top], Xallt[:, top]
    prod_tr, prod_te, prod_names = [], [], []
    for i in range(len(top)):
        Pi = Xt_top[:, i:i+1] * Xt_top[:, i+1:]
        js = np.where(Pi.sum(0) >= 30)[0] + i + 1
        if len(js):
            prod_tr.append(Xt_top[:, i:i+1] * Xt_top[:, js])
            prod_te.append(Xtt_top[:, i:i+1] * Xtt_top[:, js])
            prod_names += [f"{names[top[i]]} AND {names[top[j]]}" for j in js]
    Xp = np.column_stack(prod_tr); Xpt = np.column_stack(prod_te)
    if Xp.shape[1] > 9000:                       # keep the widest-support products
        keep = np.argsort(-Xp.sum(0))[:9000]
        Xp, Xpt = Xp[:, keep], Xpt[:, keep]; prod_names = [prod_names[k] for k in keep]
    Xtr = np.column_stack([Xall[:, pool], Xp]).astype(np.float32)
    Xte = np.column_stack([Xallt[:, pool], Xpt]).astype(np.float32)
    fn = [names[i] for i in pool] + prod_names
    del Xall, Xallt, Xp, Xpt, prod_tr, prod_te
    print(f"  v9 matrix: {len(pool)} singles + {len(prod_names):,} products = {Xtr.shape[1]:,}", flush=True)

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
    results = {}
    for alpha in (3e-5, 5e-5, 1e-4):
        oofP = np.full(len(ytr), np.nan); oofR = np.full(len(ytr), np.nan); nz = []
        for k in range(5):
            m = Lasso(alpha=alpha, positive=True, max_iter=6000)
            m.fit(Xtr[fold != k], ytr[fold != k])
            oofP[fold == k] = Xtr[fold == k] @ m.coef_ + m.intercept_
            surv = np.where(m.coef_ > 0)[0]; nz.append(len(surv))
            if len(surv) >= 2:
                w, b = G.fit_nonneg(Xtr[fold != k][:, surv], yi[fold != k], np.ones(int((fold != k).sum())))
                oofR[fold == k] = Xtr[fold == k][:, surv] @ w + b
        aP, aR = G.auc(yi, oofP), G.auc(yi, oofR)
        results[(alpha, "plain")] = aP; results[(alpha, "relaxed")] = aR
        print(f"    alpha={alpha:<7} CV plain {aP:.4f} · relaxed {aR:.4f} · survivors ~{int(np.mean(nz))}", flush=True)
    (alpha, mode), cv = max(results.items(), key=lambda kv: kv[1])
    print(f"\n  CV winner: {mode} alpha={alpha} (CV {cv:.4f}) vs v8 declared CV {V8_CV}")
    if cv <= V8_CV:
        print("  CV does not beat v8 — NO test read spent; v8 remains the declared model.")
        return
    m = Lasso(alpha=alpha, positive=True, max_iter=12000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    if mode == "relaxed":
        w, b0 = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
        zt = Xte[:, surv] @ w + b0
        weights = {fn[i]: float(v) for i, v in zip(surv, w) if v > 0}
    else:
        zt = Xte @ m.coef_ + m.intercept_; b0 = float(m.intercept_)
        weights = {fn[i]: float(m.coef_[i]) for i in surv}
    auc = G.auc(yte, zt)
    nprod = sum(1 for k in weights if " AND " in k)
    print(f"\n  v9 {mode} alpha={alpha} · {len(weights)} rules ({nprod} conjunctions) · "
          f"TEST AUC (read once): {auc:.4f}   [v8 0.7716 · ensemble 0.7747]")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:14]:
        print(f"    {k_[:88]:<90} +{v:.4f}")
    json.dump({"model": f"ArtaMatch v9 ({mode}, conjunctions wide)", "alpha": alpha, "mode": mode,
               "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4), "intercept": float(b0),
               "n_matrix": int(Xtr.shape[1]), "n_surviving": len(weights), "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v9_model.json"), "w"), indent=1)
    np.save(os.path.expanduser("~/.artamatch-dev/v9_test_z.npy"), zt)
    print("  saved v9_model.json + v9_test_z.npy")


if __name__ == "__main__":
    main()
