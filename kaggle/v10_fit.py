"""
v10_fit.py — two probes on the interaction ladder above v9:
  (a) the alpha peak: v9's relaxed CV was still rising at its grid edge (1e-4) — search 1.5e-4/2e-4/3e-4;
  (b) TRIPLES: v9's surviving conjunctions, each multiplied by the top singles (support >= 30) — a
      three-clause doctrine sentence is still a doctrine sentence.
Same matrix protocol as v9 otherwise. Test read spent only if CV beats v9's declared 0.7653.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8
D = os.path.expanduser("~/.artamatch-dev/remar_sh")
V9_CV = 0.7653

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
    names = n6 + nA + nL; pos = {n: i for i, n in enumerate(names)}
    del X6, XA, XL, X6t, XAt, XLt

    # rebuild the exact v9 matrix from its recipe
    m0 = Lasso(alpha=5e-5, positive=True, max_iter=12000); m0.fit(Xall, ytr)
    pool = np.where(m0.coef_ > 0)[0]
    if len(pool) > 650:
        pool = pool[np.argsort(-m0.coef_[pool])][:650]
    top = pool[np.argsort(-m0.coef_[pool])][:200]
    Xt_top, Xtt_top = Xall[:, top], Xallt[:, top]
    ptr, pte, pn = [], [], []
    for i in range(len(top)):
        Pi = Xt_top[:, i:i+1] * Xt_top[:, i+1:]
        js = np.where(Pi.sum(0) >= 30)[0] + i + 1
        if len(js):
            ptr.append(Xt_top[:, i:i+1] * Xt_top[:, js]); pte.append(Xtt_top[:, i:i+1] * Xtt_top[:, js])
            pn += [(top[i], top[j]) for j in js]
    Xp, Xpt = np.column_stack(ptr), np.column_stack(pte)
    # TRIPLES: v9's surviving conjunctions x top-120 singles
    M9 = json.load(open(os.path.expanduser("~/.artamatch-dev/v9_model.json")))
    conj = [tuple(pos[p] for p in k.split(" AND ")) for k in M9["weights"] if " AND " in k]
    t120 = top[:120]
    ttr, tte, tn = [], [], []
    for a, b in conj:
        base_tr = Xall[:, a] * Xall[:, b]; base_te = Xallt[:, a] * Xallt[:, b]
        C = base_tr[:, None] * Xall[:, t120]
        js = np.where((C.sum(0) >= 30) & (t120 != a) & (t120 != b))[0]
        if len(js):
            ttr.append(C[:, js]); tte.append(base_te[:, None] * Xallt[:, t120[js]])
            tn += [(a, b, t120[j]) for j in js]
    Xq = np.column_stack(ttr) if ttr else np.zeros((len(tr), 0), np.float32)
    Xqt = np.column_stack(tte) if tte else np.zeros((len(te), 0), np.float32)
    # a triple duplicating an existing pair-support pattern adds nothing; light dedup by column hash
    if Xq.shape[1]:
        hv = (Xq.astype(bool).T @ np.random.default_rng(3).normal(size=len(tr))).round(9)
        _, keep = np.unique(hv, return_index=True)
        Xq, Xqt = Xq[:, sorted(keep)], Xqt[:, sorted(keep)]; tn = [tn[k] for k in sorted(keep)]
    Xtr = np.column_stack([Xall[:, pool], Xp, Xq]).astype(np.float32)
    Xte = np.column_stack([Xallt[:, pool], Xpt, Xqt]).astype(np.float32)
    fn = ([names[i] for i in pool] + [f"{names[a]} AND {names[b]}" for a, b in pn]
          + [f"{names[a]} AND {names[b]} AND {names[c]}" for a, b, c in tn])
    del Xall, Xallt, Xp, Xpt, Xq, Xqt
    print(f"  v10 matrix: {len(pool)} singles + {len(pn):,} pairs + {len(tn):,} triples = {Xtr.shape[1]:,}", flush=True)

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
    for alpha in (1e-4, 1.5e-4, 2e-4, 3e-4):
        oofR = np.full(len(ytr), np.nan); nz = []
        for k in range(5):
            m = Lasso(alpha=alpha, positive=True, max_iter=6000)
            m.fit(Xtr[fold != k], ytr[fold != k])
            surv = np.where(m.coef_ > 0)[0]; nz.append(len(surv))
            if len(surv) >= 2:
                w, b = G.fit_nonneg(Xtr[fold != k][:, surv], yi[fold != k], np.ones(int((fold != k).sum())))
                oofR[fold == k] = Xtr[fold == k][:, surv] @ w + b
        aR = G.auc(yi, oofR); results[alpha] = aR
        print(f"    alpha={alpha:<8} CV relaxed {aR:.4f} · survivors ~{int(np.mean(nz))}", flush=True)
    alpha, cv = max(results.items(), key=lambda kv: kv[1])
    print(f"\n  CV winner: relaxed alpha={alpha} (CV {cv:.4f}) vs v9 declared CV {V9_CV}")
    if cv <= V9_CV:
        print("  CV does not beat v9 — NO test read spent; v9 remains the declared model.")
        return
    m = Lasso(alpha=alpha, positive=True, max_iter=12000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
    zt = Xte[:, surv] @ w + b0
    weights = {fn[i]: float(v) for i, v in zip(surv, w) if v > 0}
    auc = G.auc(yte, zt)
    n2 = sum(1 for k in weights if k.count(" AND ") == 1); n3 = sum(1 for k in weights if k.count(" AND ") == 2)
    print(f"\n  v10 relaxed alpha={alpha} · {len(weights)} rules ({n2} pairs, {n3} triples) · "
          f"TEST AUC (read once): {auc:.4f}   [v9 0.7724 · ensemble 0.7747]")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:12]:
        print(f"    {k_[:100]:<102} +{v:.4f}")
    json.dump({"model": "ArtaMatch v10 (relaxed, pairs+triples)", "alpha": alpha, "mode": "relaxed",
               "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4), "intercept": float(b0),
               "n_matrix": int(Xtr.shape[1]), "n_surviving": len(weights), "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v10_model.json"), "w"), indent=1)
    np.save(os.path.expanduser("~/.artamatch-dev/v10_test_z.npy"), zt)
    print("  saved v10_model.json + v10_test_z.npy")


if __name__ == "__main__":
    main()
