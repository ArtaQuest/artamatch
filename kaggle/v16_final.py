"""v16_final.py — the declared model of the corrected, full-precision corpus (v3):
truthy-ranked dates · Wikipedia-verified Jan-1 · collapsed duplicate weddings · +recovered negatives ·
BOTH dates full precision. Two candidate banks — the v13 bank, and v13+families15 (the aggregate wave) —
each through the pair-only ladder (singles+pairs, then +triples). CV picks bank and stage; ONE test read."""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
import v15_families as F15
import v17_families as F17
from v12_fit import side
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
    XF, nF = F15.families15(tr, Z, "train"); XFt, _ = F15.families15(te, Z, "test")
    supF = XF.sum(0) >= 40
    XF, XFt = XF[:, supF], XFt[:, supF]; nF = [n for n, s in zip(nF, supF) if s]
    XW, nW = F17.families17(tr, Z, "train"); XWt, _ = F17.families17(te, Z, "test")
    supW = XW.sum(0) >= 40
    XW, XWt = XW[:, supW], XWt[:, supW]; nW = [n for n, s in zip(nW, supW) if s]
    print(f"  corpus v3: train {len(tr):,} ({yi.mean():.1%}) · test {len(te):,} ({yte.mean():.1%})", flush=True)

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
    D2 = {"A": {"A"}, "B": {"B"}, "AB": {"A", "B"}}

    def cv_relaxed(X, alphas, label):
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
            print(f"    [{label}] alpha={alpha:<8} CV relaxed {out[alpha]:.4f} · survivors ~{int(np.mean(nz))}", flush=True)
        return out

    def ladder(Xall, Xallt, names, label):
        dep = np.array([side(n) for n in names])
        both_ix = np.where(dep == "AB")[0]
        m0 = Lasso(alpha=5e-5, positive=True, max_iter=12000); m0.fit(Xall, ytr)
        pool = np.where(m0.coef_ > 0)[0]
        if len(pool) > 650:
            pool = pool[np.argsort(-m0.coef_[pool])][:650]
        top = pool[np.argsort(-m0.coef_[pool])][:220]
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
        XtrA = np.column_stack([Xall[:, both_ix], Xp]).astype(np.float32)
        XteA = np.column_stack([Xallt[:, both_ix], Xpt]).astype(np.float32)
        fnA = [names[i] for i in both_ix] + [f"{names[a]} AND {names[b]}" for a, b in pn]
        print(f"  [{label}] bank {len(names):,} · stage A matrix {XtrA.shape[1]:,}", flush=True)
        rA = cv_relaxed(XtrA, (5e-5, 7.5e-5, 1e-4, 1.5e-4), label + ":A")
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
            _, keep = np.unique(hv, return_index=True)
            Xq, Xqt = Xq[:, sorted(keep)], Xqt[:, sorted(keep)]; tn = [tn[k] for k in sorted(keep)]
        XtrB = np.column_stack([XtrA, Xq]); XteB = np.column_stack([XteA, Xqt])
        fnB = fnA + tn
        print(f"  [{label}] stage B matrix {XtrB.shape[1]:,} (+{len(tn):,} triples)", flush=True)
        rB = cv_relaxed(XtrB, (aA,), label + ":B")
        aB, cvB = list(rB.items())[0]
        if cvB > cvA:
            return ("B", aB, cvB, XtrB, XteB, fnB)
        return ("A", aA, cvA, XtrA, XteA, fnA)

    base_names = n6 + nA + nL + nN
    Xbase = np.column_stack([X6, XA, XL, XN]); Xbase_t = np.column_stack([X6t, XAt, XLt, XNt])
    cand = {}
    cand["v13bank"] = ladder(Xbase, Xbase_t, base_names, "v13bank")
    Xfull = np.column_stack([Xbase, XF]); Xfull_t = np.column_stack([Xbase_t, XFt])
    del X6, XA, XL, XN, X6t, XAt, XLt, XNt
    cand["v13+agg"] = ladder(Xfull, Xfull_t, base_names + nF, "v13+agg")
    Xw = np.column_stack([Xfull, XW]); Xw_t = np.column_stack([Xfull_t, XWt])
    del XF, XFt, XW, XWt
    cand["v13+agg+w3"] = ladder(Xw, Xw_t, base_names + nF + nW, "v13+agg+w3")
    bank, (stage, alpha, cv, Xtr, Xte_, fn) = max(cand.items(), key=lambda kv: kv[1][2])
    print(f"\n  CV winner: {bank} stage {stage} alpha={alpha} (CV {cv:.4f})")
    m = Lasso(alpha=alpha, positive=True, max_iter=12000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
    zt = Xte_[:, surv] @ w + b0
    weights = {fn[i]: float(v) for i, v in zip(surv, w) if v > 0}
    viol = [k for k in weights
            if set().union(*(D2[side(p)] for p in k.split(" AND "))) != {"A", "B"}]
    assert not viol, f"one-sided rules survived: {viol[:5]}"
    auc = G.auc(yte, zt)
    n1 = sum(1 for k in weights if " AND " not in k)
    n2 = sum(1 for k in weights if k.count(" AND ") == 1); n3 = sum(1 for k in weights if k.count(" AND ") == 2)
    print(f"\n  v16 FINAL (corpus v3, full precision) · {bank} stage {stage} alpha={alpha} · {len(weights)} rules "
          f"({n1} singles, {n2} pairs, {n3} triples) · TEST AUC (read once): {auc:.4f}")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:14]:
        print(f"    {k_[:100]:<102} +{v:.4f}")
    json.dump({"model": f"ArtaMatch v16 (corpus v3 full-precision, {bank})", "alpha": alpha, "stage": stage,
               "bank": bank, "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4), "intercept": float(b0),
               "n_matrix": int(Xtr.shape[1]), "n_surviving": len(weights), "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v16_model.json"), "w"), indent=1)
    np.save(os.path.expanduser("~/.artamatch-dev/v16_test_z.npy"), zt)
    print("  saved v16_model.json + v16_test_z.npy")


if __name__ == "__main__":
    main()
