"""v18_fit.py — v16's winning recipe (v13 bank, corpus v3) re-declared under the DOCTRINE-ONLY
constraint: weekday/age-gap/calendar/biorhythm features removed from the bank entirely (denylist.py).
Fresh CV over the pruned bank, one test read."""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
from v12_fit import side
from denylist import clause_ok
D = os.path.expanduser("~/.artamatch-dev/remar_sh3")

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
    ex1 = set(n6 + nA + nL)
    XN, nN = V13.new_singles(tr, Z, "train", ex1); XNt, _ = V13.new_singles(te, Z, "test", ex1)
    supN = XN.sum(0) >= 40
    XN, XNt = XN[:, supN], XNt[:, supN]; nN = [n for n, s in zip(nN, supN) if s]
    Xall = np.column_stack([X6, XA, XL, XN]); Xallt = np.column_stack([X6t, XAt, XLt, XNt])
    names = n6 + nA + nL + nN
    del X6, XA, XL, XN, X6t, XAt, XLt, XNt
    keep = np.array([clause_ok(n) for n in names])
    Xall, Xallt = Xall[:, keep], Xallt[:, keep]
    names = [n for n, k in zip(names, keep) if k]
    dep = np.array([side(n) for n in names])
    both_ix = np.where(dep == "AB")[0]
    print(f"  DOCTRINE-ONLY bank {len(names):,} ({int((~keep).sum())} calendar features removed) · "
          f"both-date {len(both_ix):,}", flush=True)

    m0 = Lasso(alpha=5e-5, positive=True, max_iter=12000); m0.fit(Xall, ytr)
    pool = np.where(m0.coef_ > 0)[0]
    if len(pool) > 650:
        pool = pool[np.argsort(-m0.coef_[pool])][:650]
    top = pool[np.argsort(-m0.coef_[pool])][:220]
    D2 = {"A": {"A"}, "B": {"B"}, "AB": {"A", "B"}}
    Xt_top, Xtt_top = Xall[:, top], Xallt[:, top]
    ptr, pte, pn = [], [], []
    for i in range(len(top)):
        Pi = Xt_top[:, i:i+1] * Xt_top[:, i+1:]
        js = np.where(Pi.sum(0) >= 30)[0] + i + 1
        js = np.array([j for j in js if D2[dep[top[i]]] | D2[dep[top[j]]] == {"A", "B"}], int)
        if len(js):
            ptr.append(Xt_top[:, i:i+1] * Xt_top[:, js]); pte.append(Xtt_top[:, i:i+1] * Xtt_top[:, js])
            pn += [(int(top[i]), int(top[j])) for j in js]
    Xp, Xpt = np.column_stack(ptr), np.column_stack(pte)
    del ptr, pte

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

    def cv_relaxed(X, alphas):
        out = {}
        for alpha in alphas:
            oofR = np.full(len(ytr), np.nan); nz = []
            for k in range(5):
                m = Lasso(alpha=alpha, positive=True, max_iter=6000)
                m.fit(X[fold != k], ytr[fold != k])
                surv = np.where(m.coef_ > 0)[0]; nz.append(len(surv))
                if len(surv) >= 2:
                    w, b = G.fit_nonneg(X[fold != k][:, surv], yi[fold != k], np.ones(int((fold != k).sum())))
                    oofR[fold == k] = X[fold == k][:, surv] @ w + b
            out[alpha] = G.auc(yi, oofR)
            print(f"    alpha={alpha:<8} CV relaxed {out[alpha]:.4f} · survivors ~{int(np.mean(nz))}", flush=True)
        return out

    XtrA = np.column_stack([Xall[:, both_ix], Xp]).astype(np.float32)
    XteA = np.column_stack([Xallt[:, both_ix], Xpt]).astype(np.float32)
    fnA = [names[i] for i in both_ix] + [f"{names[a]} AND {names[b]}" for a, b in pn]
    del Xp, Xpt
    print(f"  STAGE A matrix {XtrA.shape[1]:,}", flush=True)
    rA = cv_relaxed(XtrA, (1e-4, 1.5e-4, 2e-4))
    aA, cvA = max(rA.items(), key=lambda kv: kv[1])
    mA = Lasso(alpha=aA, positive=True, max_iter=12000); mA.fit(XtrA, ytr)
    conjA = [pn[i - len(both_ix)] for i in np.where(mA.coef_ > 0)[0] if i >= len(both_ix)]
    ttr, tte, tn = [], [], []
    ext = top[:120]
    for a, b in conjA:
        base_tr = Xall[:, a] * Xall[:, b]; base_te = Xallt[:, a] * Xallt[:, b]
        C = base_tr[:, None] * Xall[:, ext]
        js = np.where((C.sum(0) >= 30) & (ext != a) & (ext != b))[0]
        if len(js):
            ttr.append(C[:, js]); tte.append(base_te[:, None] * Xallt[:, ext[js]])
            tn += [f"{names[a]} AND {names[b]} AND {names[ext[j]]}" for j in js]
    Xq = np.column_stack(ttr) if ttr else np.zeros((len(tr), 0), np.float32)
    Xqt = np.column_stack(tte) if tte else np.zeros((len(te), 0), np.float32)
    if Xq.shape[1]:
        hv = (Xq.astype(bool).T @ np.random.default_rng(3).normal(size=len(tr))).round(9)
        _, keep2 = np.unique(hv, return_index=True)
        Xq, Xqt = Xq[:, sorted(keep2)], Xqt[:, sorted(keep2)]; tn = [tn[k] for k in sorted(keep2)]
    XtrB = np.column_stack([XtrA, Xq]); XteB = np.column_stack([XteA, Xqt])
    fnB = fnA + tn
    print(f"  STAGE B matrix {XtrB.shape[1]:,} (+{len(tn):,} triples)", flush=True)
    rB = cv_relaxed(XtrB, (aA,))
    aB, cvB = list(rB.items())[0][0], list(rB.values())[0]
    if cvB > cvA:
        stage, alpha, cv, Xtr, Xte_, fn = "B", aB, cvB, XtrB, XteB, fnB
    else:
        stage, alpha, cv, Xtr, Xte_, fn = "A", aA, cvA, XtrA, XteA, fnA
    m = Lasso(alpha=alpha, positive=True, max_iter=12000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
    zt = Xte_[:, surv] @ w + b0
    weights = {fn[i]: float(v) for i, v in zip(surv, w) if v > 0}
    from denylist import rule_ok
    assert all(rule_ok(k) for k in weights), "calendar rule leaked through"
    viol = [k for k in weights
            if set().union(*(D2[side(p)] for p in k.split(" AND "))) != {"A", "B"}]
    assert not viol
    auc = G.auc(yte, zt)
    n1 = sum(1 for k in weights if " AND " not in k)
    n2 = sum(1 for k in weights if k.count(" AND ") == 1); n3 = sum(1 for k in weights if k.count(" AND ") == 2)
    print(f"\n  v18 DOCTRINE-ONLY stage {stage} alpha={alpha} · {len(weights)} rules "
          f"({n1} singles, {n2} pairs, {n3} triples) · TEST AUC (read once): {auc:.4f}   [v16 was 0.7016]")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:10]:
        print(f"    {k_[:100]:<102} +{v:.4f}")
    json.dump({"model": "ArtaMatch v18 (doctrine-only, pair-only, full-precision corpus)", "alpha": alpha,
               "stage": stage, "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4), "intercept": float(b0),
               "n_matrix": int(Xtr.shape[1]), "n_surviving": len(weights), "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v18_model.json"), "w"), indent=1)
    np.save(os.path.expanduser("~/.artamatch-dev/v18_test_z.npy"), zt)
    print("  saved v18_model.json + v18_test_z.npy")


if __name__ == "__main__":
    main()
