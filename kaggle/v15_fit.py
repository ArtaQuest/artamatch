"""v15_fit.py — corpus v2, bank = v13's + families15 (guna milan aggregates, mangal pair, D9 pairs,
Chinese relation classes, vedha/mahendra/stridirgha, Moon overlays, H7 pairs, tithi-class pair).
Same pair-only ladder. Test read ONLY if CV beats the v2 baseline's declared CV (read from v13v2_model.json)."""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
import v15_families as F15
from v12_fit import side
D = os.path.expanduser("~/.artamatch-dev/remar_sh2")
BASE = json.load(open(os.path.expanduser("~/.artamatch-dev/v13v2_model.json")))
GATE = BASE["cv_auc"]

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
    sup = XN.sum(0) >= 40
    XN, XNt = XN[:, sup], XNt[:, sup]; nN = [n for n, s in zip(nN, sup) if s]
    XF, nF = F15.families15(tr, Z, "train"); XFt, _ = F15.families15(te, Z, "test")
    supF = XF.sum(0) >= 40
    XF, XFt = XF[:, supF], XFt[:, supF]; nF = [n for n, s in zip(nF, supF) if s]
    Xall = np.column_stack([X6, XA, XL, XN, XF]); Xallt = np.column_stack([X6t, XAt, XLt, XNt, XFt])
    names = n6 + nA + nL + nN + nF
    del X6, XA, XL, XN, XF, X6t, XAt, XLt, XNt, XFt
    dep = np.array([side(n) for n in names])
    both_ix = np.where(dep == "AB")[0]
    print(f"  bank {len(names):,} (+{len(nF)} aggregate-wave) · both-date {len(both_ix):,} · gate CV {GATE}", flush=True)

    m0 = Lasso(alpha=5e-5, positive=True, max_iter=12000); m0.fit(Xall, ytr)
    pool = np.where(m0.coef_ > 0)[0]
    if len(pool) > 650:
        pool = pool[np.argsort(-m0.coef_[pool])][:650]
    top = pool[np.argsort(-m0.coef_[pool])][:220]
    print(f"  pool {len(pool)} · product base {len(top)}", flush=True)
    Xt_top, Xtt_top = Xall[:, top], Xallt[:, top]
    D2 = {"A": {"A"}, "B": {"B"}, "AB": {"A", "B"}}
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
    print(f"  mixed pairs {len(pn):,}", flush=True)

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
    rA = cv_relaxed(XtrA, (5e-5, 7.5e-5, 1e-4, 1.5e-4))
    aA, cvA = max(rA.items(), key=lambda kv: kv[1])
    mA = Lasso(alpha=aA, positive=True, max_iter=12000); mA.fit(XtrA, ytr)
    survA = np.where(mA.coef_ > 0)[0]
    conjA = [pn[i - len(both_ix)] for i in survA if i >= len(both_ix)]
    print(f"  stage A: alpha={aA} CV {cvA:.4f} · surviving mixed pairs {len(conjA)}", flush=True)

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
    del Xq, Xqt, ttr, tte
    print(f"  STAGE B matrix {XtrB.shape[1]:,} (+{len(tn):,} triples)", flush=True)
    rB = cv_relaxed(XtrB, (aA,))
    aB, cvB = max(rB.items(), key=lambda kv: kv[1])

    if cvB > cvA:
        stage, alpha, cv, Xtr, Xte_, fn = "B", aB, cvB, XtrB, XteB, fnB
    else:
        stage, alpha, cv, Xtr, Xte_, fn = "A", aA, cvA, XtrA, XteA, fnA
    print(f"\n  CV winner: stage {stage} alpha={alpha} (CV {cv:.4f}) vs v2-baseline CV {GATE}")
    if cv <= GATE:
        print("  CV does not beat the v2 baseline — NO test read spent; the baseline stands.")
        return
    m = Lasso(alpha=alpha, positive=True, max_iter=12000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
    zt = Xte_[:, surv] @ w + b0
    weights = {fn[i]: float(v) for i, v in zip(surv, w) if v > 0}
    D2c = {"A": {"A"}, "B": {"B"}, "AB": {"A", "B"}}
    viol = [k for k in weights
            if set().union(*(D2c[side(p)] for p in k.split(" AND "))) != {"A", "B"}]
    assert not viol, f"one-sided rules survived: {viol[:5]}"
    auc = G.auc(yte, zt)
    n1 = sum(1 for k in weights if " AND " not in k)
    n2 = sum(1 for k in weights if k.count(" AND ") == 1); n3 = sum(1 for k in weights if k.count(" AND ") == 2)
    newfam = sum(1 for k in weights if any(
        p.startswith(("kuta_", "guna_", "mangal_", "moon_d9", "venus_d9", "year_branch_rel", "day_branch_rel",
                      "daymaster_rel", "nayin_rel", "stem_he", "vedha", "mahendra", "stridirgha",
                      "his_sun_from", "his_venus_from", "his_mars_from", "his_jupiter_from",
                      "her_sun_from", "her_venus_from", "her_mars_from", "her_jupiter_from",
                      "venus_h7", "moon_h7", "tithiclass"))
        for p in k.split(" AND ")))
    print(f"\n  v15 CORPUS-V2 stage {stage} alpha={alpha} · {len(weights)} rules "
          f"({n1} singles, {n2} pairs, {n3} triples · {newfam} touch the aggregate wave) · "
          f"TEST AUC (read once): {auc:.4f}   [v2 baseline {BASE['test_auc']}]")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:14]:
        print(f"    {k_[:100]:<102} +{v:.4f}")
    json.dump({"model": "ArtaMatch v15 (corpus v2, aggregate doctrine wave)", "alpha": alpha, "stage": stage,
               "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4), "intercept": float(b0),
               "n_matrix": int(Xtr.shape[1]), "n_surviving": len(weights), "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v15_model.json"), "w"), indent=1)
    np.save(os.path.expanduser("~/.artamatch-dev/v15_test_z.npy"), zt)
    print("  saved v15_model.json + v15_test_z.npy")


if __name__ == "__main__":
    main()
