"""
v13_fit.py — the constrained ladder's big both-date bank extension. v12 banned one-sided rules and paid
0.0052; the recovery must come from features that read BOTH dates by construction:
  - the FULL synastry grid: his-planet x her-planet x aspect over all 10 classical+outer bodies and
    7 aspects (conj/sextile/square/trine/opposition/quincunx/semi-sextile with their orbs) — training
    had only 20 named contact pairs of the tradition's complete table;
  - the healthy 10-degree grains: decans of the 7 couple-midpoint cycles, of the Davison chart and of
    the composite chart (the 1-degree grids died in v11; the 10-degree ones survived);
  - the midpoint charts' own panchanga: Davison and composite tithi, composite Moon nakshatra.
Then the identical pair-only ladder as v12. Test read ONLY if CV beats v12's 0.7557.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, explain_gam as EG, v6_fit as V6, v7_fit as V7, v8_fit as V8
from v12_fit import side
D = os.path.expanduser("~/.artamatch-dev/remar_sh")
V12_CV = 0.7557
TEN = ["sun","moon","mercury","venus","mars","jupiter","saturn","uranus","neptune","pluto"]
ASPECTS = ((0, 8, "conj"), (60, 4, "sext"), (90, 6, "square"), (120, 6, "trine"), (180, 8, "opp"),
           (150, 3, "quinc"), (30, 3, "semisext"))
CYC = (("jupiter","saturn"),("saturn","uranus"),("saturn","neptune"),("saturn","pluto"),
       ("uranus","neptune"),("uranus","pluto"),("neptune","pluto"))

def new_singles(df, Z, half, existing):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    add = lambda M, nm: (blocks.append(np.asarray(M, np.float32)), names.extend(nm))
    oh = EG.onehot
    arc = lambda x, y: np.abs((x - y + 180.0) % 360.0 - 180.0)
    # full synastry grid, skipping cells the bank already names
    for x in TEN:
        for y in TEN:
            a = arc(A[:, ix[x]], B[:, ix[y]])
            for t, o, lab in ASPECTS:
                nm = f"his_{x}_{lab}_her_{y}"
                if nm in existing:
                    continue
                add(np.where(np.isfinite(a), (np.abs(a - t) <= o).astype(np.float32), 0).reshape(-1, 1), [nm])
    # decans of the couple-midpoint cycles
    for x, y in CYC:
        ph = ((A[:, ix[x]] + B[:, ix[x]]) / 2 - (A[:, ix[y]] + B[:, ix[y]]) / 2) % 360.0
        both = (np.isfinite(A[:, ix[x]]) & np.isfinite(B[:, ix[x]])
                & np.isfinite(A[:, ix[y]]) & np.isfinite(B[:, ix[y]]))
        add(*oh(np.where(both, np.floor(ph / 10), np.nan), 36, f"cycle36_{x}_{y}"))
    # Davison and composite decans + their panchanga
    import importlib.util
    _dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
    dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    dt = jb - ja
    davpos = {}
    for b in ("sun","moon","venus","mars","jupiter","saturn","uranus","neptune","pluto"):
        ta, tb = A[:, ix[b]], B[:, ix[b]]
        raw = (tb - ta + 180.0) % 360.0 - 180.0
        k = np.round((dv.MEAN[b] * dt - raw) / 360.0)
        davpos[b] = np.where(np.isfinite(dt), (ta + (raw + 360.0 * k) / 2.0) % 360.0, np.nan)
        add(*oh(np.floor(davpos[b] / 10), 36, f"dav_{b}_decan"))
    comppos = {}
    for b in ("sun","moon","venus","mars","jupiter","saturn","uranus","neptune","pluto"):
        ta, tb = A[:, ix[b]], B[:, ix[b]]
        comppos[b] = np.where(np.isfinite(ta) & np.isfinite(tb),
                              (ta + ((tb - ta + 180.0) % 360.0 - 180.0) / 2.0) % 360.0, np.nan)
        add(*oh(np.floor(comppos[b] / 10), 36, f"comp_{b}_decan"))
    add(*oh(np.floor(((davpos["moon"] - davpos["sun"]) % 360.0) / 12.0), 30, "dav_tithi"))
    add(*oh(np.floor(((comppos["moon"] - comppos["sun"]) % 360.0) / 12.0), 30, "comp_tithi"))
    add(*oh(np.floor((comppos["moon"] % 360) / (360.0 / 27.0)), 27, "comp_moon_nakshatra"))
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
    existing = set(n6 + nA + nL)
    XN, nN = new_singles(tr, Z, "train", existing); XNt, _ = new_singles(te, Z, "test", existing)
    sup = XN.sum(0) >= 40
    XN, XNt = XN[:, sup], XNt[:, sup]; nN = [n for n, s in zip(nN, sup) if s]
    Xall = np.column_stack([X6, XA, XL, XN]); Xallt = np.column_stack([X6t, XAt, XLt, XNt])
    names = n6 + nA + nL + nN
    del X6, XA, XL, XN, X6t, XAt, XLt, XNt
    dep = np.array([side(n) for n in names])
    both_ix = np.where(dep == "AB")[0]
    print(f"  bank {len(names):,} (+{len(nN):,} new both-date) · both-date singles {len(both_ix):,}", flush=True)

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
    rA = cv_relaxed(XtrA, (1e-4, 1.5e-4, 2e-4, 3e-4))
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
    print(f"\n  CV winner: stage {stage} alpha={alpha} (CV {cv:.4f}) vs v12 declared CV {V12_CV}")
    if cv <= V12_CV:
        print("  CV does not beat v12 — NO test read spent; v12 remains the declared pair-only model.")
        return
    m = Lasso(alpha=alpha, positive=True, max_iter=12000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
    zt = Xte_[:, surv] @ w + b0
    weights = {fn[i]: float(v) for i, v in zip(surv, w) if v > 0}
    viol = [k for k in weights
            if {s for p in k.split(" AND ") for s in ({"A"} if side(p) == "A" else {"B"} if side(p) == "B" else {"A", "B"})} != {"A", "B"}]
    assert not viol, f"one-sided rules survived: {viol[:5]}"
    auc = G.auc(yte, zt)
    n1 = sum(1 for k in weights if " AND " not in k)
    n2 = sum(1 for k in weights if k.count(" AND ") == 1); n3 = sum(1 for k in weights if k.count(" AND ") == 2)
    print(f"\n  v13 PAIR-ONLY stage {stage} relaxed alpha={alpha} · {len(weights)} rules "
          f"({n1} singles, {n2} pairs, {n3} triples) · TEST AUC (read once): {auc:.4f}"
          f"   [v12 0.7679 · unconstrained v10 0.7731 · ensemble 0.7747]")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:14]:
        print(f"    {k_[:100]:<102} +{v:.4f}")
    json.dump({"model": "ArtaMatch v13 (pair-only, full synastry grid)", "alpha": alpha, "stage": stage,
               "mode": "relaxed", "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4),
               "intercept": float(b0), "n_matrix": int(Xtr.shape[1]), "n_surviving": len(weights),
               "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v13_model.json"), "w"), indent=1)
    np.save(os.path.expanduser("~/.artamatch-dev/v13_test_z.npy"), zt)
    print("  saved v13_model.json + v13_test_z.npy")


if __name__ == "__main__":
    main()
