"""
v12_fit.py — the PAIR-ONLY constraint (operator order 2026-08-25): every rule must use BOTH partners'
dates, otherwise it biases a type of person instead of judging the match. Enforcement by name:
  - a feature reading one chart alone (his_*/her_* without a cross reference) may NEVER stand alone;
  - it may appear only inside a conjunction whose clauses together span both dates;
  - both-date features (pair tables, synastry contacts, Davison, composite, couple-midpoint cycles,
    gap, Sade Sati, midpoint/antiscia contacts) stand alone freely.
Ladder inside one script: both-date singles + mixed pairs -> CV -> surviving pairs extended to mixed
triples -> CV again -> the better stage is declared and reads test ONCE.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8
D = os.path.expanduser("~/.artamatch-dev/remar_sh")

def side(name):
    """'A' = his date only, 'B' = her date only, 'AB' = both."""
    if "_her_" in name or "_his_" in name or "_other_" in name:
        return "AB"
    if name.startswith("his_"):
        return "A"
    if name.startswith("her_"):
        return "B"
    return "AB"

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
    dep = np.array([side(n) for n in names])
    both_ix = np.where(dep == "AB")[0]
    print(f"  bank {len(names):,} · both-date singles {len(both_ix):,} · "
          f"one-sided {int((dep=='A').sum()):,}+{int((dep=='B').sum()):,} (conjunction-only)", flush=True)

    # pool for conjunction building may see every feature; the CONSTRAINT binds what enters the model
    m0 = Lasso(alpha=5e-5, positive=True, max_iter=12000); m0.fit(Xall, ytr)
    pool = np.where(m0.coef_ > 0)[0]
    if len(pool) > 650:
        pool = pool[np.argsort(-m0.coef_[pool])][:650]
    top = pool[np.argsort(-m0.coef_[pool])][:220]
    print(f"  pool {len(pool)} · product base {len(top)}", flush=True)
    Xt_top, Xtt_top = Xall[:, top], Xallt[:, top]
    ptr, pte, pn = [], [], []
    for i in range(len(top)):
        di = dep[top[i]]
        Pi = Xt_top[:, i:i+1] * Xt_top[:, i+1:]
        js = np.where(Pi.sum(0) >= 30)[0] + i + 1
        js = np.array([j for j in js
                       if {"A": {"A"}, "B": {"B"}, "AB": {"A", "B"}}[di]
                       | {"A": {"A"}, "B": {"B"}, "AB": {"A", "B"}}[dep[top[j]]] == {"A", "B"}], int)
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

    # STAGE A: both-date singles + mixed pairs
    XtrA = np.column_stack([Xall[:, both_ix], Xp]).astype(np.float32)
    XteA = np.column_stack([Xallt[:, both_ix], Xpt]).astype(np.float32)
    fnA = [names[i] for i in both_ix] + [f"{names[a]} AND {names[b]}" for a, b in pn]
    print(f"  STAGE A matrix {XtrA.shape[1]:,}", flush=True)
    rA = cv_relaxed(XtrA, (7e-5, 1e-4, 1.5e-4))
    aA, cvA = max(rA.items(), key=lambda kv: kv[1])
    mA = Lasso(alpha=aA, positive=True, max_iter=12000); mA.fit(XtrA, ytr)
    survA = np.where(mA.coef_ > 0)[0]
    conjA = [pn[i - len(both_ix)] for i in survA if i >= len(both_ix)]
    print(f"  stage A: alpha={aA} CV {cvA:.4f} · surviving mixed pairs {len(conjA)}", flush=True)

    # STAGE B: extend the surviving pairs by one clause (any side — pair already spans both)
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
    rB = cv_relaxed(XtrB, (7e-5, 1e-4, 1.5e-4))
    aB, cvB = max(rB.items(), key=lambda kv: kv[1])

    if cvB > cvA:
        stage, alpha, cv, Xtr, Xte_, fn = "B", aB, cvB, XtrB, XteB, fnB
    else:
        stage, alpha, cv, Xtr, Xte_, fn = "A", aA, cvA, XtrA, XteA, fnA
    m = Lasso(alpha=alpha, positive=True, max_iter=12000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
    zt = Xte_[:, surv] @ w + b0
    weights = {fn[i]: float(v) for i, v in zip(surv, w) if v > 0}
    # constraint audit before the read: no surviving rule may be one-sided
    viol = [k for k in weights
            if {s for p in k.split(" AND ") for s in ({"A"} if side(p) == "A" else {"B"} if side(p) == "B" else {"A", "B"})} != {"A", "B"}]
    assert not viol, f"one-sided rules survived: {viol[:5]}"
    auc = G.auc(yte, zt)
    n1 = sum(1 for k in weights if " AND " not in k)
    n2 = sum(1 for k in weights if k.count(" AND ") == 1); n3 = sum(1 for k in weights if k.count(" AND ") == 2)
    print(f"\n  v12 PAIR-ONLY stage {stage} relaxed alpha={alpha} · {len(weights)} rules "
          f"({n1} both-date singles, {n2} pairs, {n3} triples) · TEST AUC (read once): {auc:.4f}"
          f"   [unconstrained v10 0.7731 · ensemble 0.7747]")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:14]:
        print(f"    {k_[:100]:<102} +{v:.4f}")
    json.dump({"model": "ArtaMatch v12 (pair-only rules, relaxed)", "alpha": alpha, "stage": stage,
               "mode": "relaxed", "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4),
               "intercept": float(b0), "n_matrix": int(Xtr.shape[1]), "n_surviving": len(weights),
               "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v12_model.json"), "w"), indent=1)
    np.save(os.path.expanduser("~/.artamatch-dev/v12_test_z.npy"), zt)
    print("  saved v12_model.json + v12_test_z.npy")


if __name__ == "__main__":
    main()
