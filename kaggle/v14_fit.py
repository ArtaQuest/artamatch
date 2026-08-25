"""
v14_fit.py — the closing constrained wave. Remaining both-date doctrine not yet in the bank:
  - the MINOR aspects across the full his x her grid: quintile 72, biquintile 144 (Kepler),
    semisquare 45, sesquiquadrate 135 (Ebertin), orb 2;
  - COMPOSITE-TO-NATAL contacts (Hand's composite technique): each partner's natal planet against
    the couple's composite planets, 7 aspects;
  - DAVISON-TO-NATAL contacts, likewise (the Davison chart is a real chart; its contacts to the
    natals are read in the same tradition).
Ladder and constraint identical to v13. Test read ONLY if CV beats v13's 0.7577.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, explain_gam as EG, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
import v12_fit as V12
D = os.path.expanduser("~/.artamatch-dev/remar_sh")
V13_CV = 0.7577
TEN = V13.TEN

def side14(name):
    if "_comp_" in name or "_dav_" in name:
        return "AB"
    return V12.side(name)

def newer_singles(df, Z, half, existing):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    add = lambda M, nm: (blocks.append(np.asarray(M, np.float32)), names.extend(nm))
    arc = lambda x, y: np.abs((x - y + 180.0) % 360.0 - 180.0)
    MINOR = ((72, 2, "quintile"), (144, 2, "biquintile"), (45, 2, "semisquare"), (135, 2, "sesquiquadrate"))
    for x in TEN:
        for y in TEN:
            a = arc(A[:, ix[x]], B[:, ix[y]])
            for t, o, lab in MINOR:
                nm = f"his_{x}_{lab}_her_{y}"
                if nm not in existing:
                    add(np.where(np.isfinite(a), (np.abs(a - t) <= o).astype(np.float32), 0).reshape(-1, 1), [nm])
    import importlib.util
    _dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
    dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    dt = jb - ja
    NINE = ("sun","moon","venus","mars","jupiter","saturn","uranus","neptune","pluto")
    davpos, comppos = {}, {}
    for b in NINE:
        ta, tb = A[:, ix[b]], B[:, ix[b]]
        raw = (tb - ta + 180.0) % 360.0 - 180.0
        k = np.round((dv.MEAN[b] * dt - raw) / 360.0)
        davpos[b] = np.where(np.isfinite(dt), (ta + (raw + 360.0 * k) / 2.0) % 360.0, np.nan)
        comppos[b] = np.where(np.isfinite(ta) & np.isfinite(tb),
                              (ta + ((tb - ta + 180.0) % 360.0 - 180.0) / 2.0) % 360.0, np.nan)
    MAIN = ((0, 8, "conj"), (60, 4, "sext"), (90, 6, "square"), (120, 6, "trine"), (180, 8, "opp"),
            (150, 3, "quinc"), (30, 3, "semisext"))
    for kind, POS in (("comp", comppos), ("dav", davpos)):
        for tag, C in (("his", A), ("her", B)):
            for x in TEN:
                for y in NINE:
                    a = arc(C[:, ix[x]], POS[y])
                    for t, o, lab in MAIN:
                        add(np.where(np.isfinite(a), (np.abs(a - t) <= o).astype(np.float32), 0).reshape(-1, 1),
                            [f"{tag}_{x}_{lab}_{kind}_{y}"])
    X = np.column_stack(blocks).astype(np.float32)
    return X, names

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
    ex2 = ex1 | set(nN)
    XM, nM = newer_singles(tr, Z, "train", ex2); XMt, _ = newer_singles(te, Z, "test", ex2)
    supN = XN.sum(0) >= 40; supM = XM.sum(0) >= 40
    XN, XNt = XN[:, supN], XNt[:, supN]; nN = [n for n, s in zip(nN, supN) if s]
    XM, XMt = XM[:, supM], XMt[:, supM]; nM = [n for n, s in zip(nM, supM) if s]
    Xall = np.column_stack([X6, XA, XL, XN, XM]); Xallt = np.column_stack([X6t, XAt, XLt, XNt, XMt])
    names = n6 + nA + nL + nN + nM
    del X6, XA, XL, XN, XM, X6t, XAt, XLt, XNt, XMt
    dep = np.array([side14(n) for n in names])
    both_ix = np.where(dep == "AB")[0]
    print(f"  bank {len(names):,} (+{len(nM):,} minor/derived-chart contacts) · both-date {len(both_ix):,}", flush=True)

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
    print(f"  STAGE A matrix {XtrA.shape[1]:,}", flush=True)
    rA = cv_relaxed(XtrA, (1e-4, 1.5e-4, 2e-4))
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
    print(f"\n  CV winner: stage {stage} alpha={alpha} (CV {cv:.4f}) vs v13 declared CV {V13_CV}")
    if cv <= V13_CV:
        print("  CV does not beat v13 — NO test read spent; v13 remains the declared pair-only model.")
        return
    m = Lasso(alpha=alpha, positive=True, max_iter=12000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
    zt = Xte_[:, surv] @ w + b0
    weights = {fn[i]: float(v) for i, v in zip(surv, w) if v > 0}
    D2c = {"A": {"A"}, "B": {"B"}, "AB": {"A", "B"}}
    viol = [k for k in weights
            if set().union(*(D2c[side14(p)] for p in k.split(" AND "))) != {"A", "B"}]
    assert not viol, f"one-sided rules survived: {viol[:5]}"
    auc = G.auc(yte, zt)
    n1 = sum(1 for k in weights if " AND " not in k)
    n2 = sum(1 for k in weights if k.count(" AND ") == 1); n3 = sum(1 for k in weights if k.count(" AND ") == 2)
    print(f"\n  v14 PAIR-ONLY stage {stage} relaxed alpha={alpha} · {len(weights)} rules "
          f"({n1} singles, {n2} pairs, {n3} triples) · TEST AUC (read once): {auc:.4f}"
          f"   [v13 0.7709 · unconstrained v10 0.7731 · ensemble 0.7747]")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:14]:
        print(f"    {k_[:100]:<102} +{v:.4f}")
    json.dump({"model": "ArtaMatch v14 (pair-only, minor aspects + derived-chart contacts)", "alpha": alpha,
               "stage": stage, "mode": "relaxed", "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4),
               "intercept": float(b0), "n_matrix": int(Xtr.shape[1]), "n_surviving": len(weights),
               "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v14_model.json"), "w"), indent=1)
    np.save(os.path.expanduser("~/.artamatch-dev/v14_test_z.npy"), zt)
    print("  saved v14_model.json + v14_test_z.npy")


if __name__ == "__main__":
    main()
