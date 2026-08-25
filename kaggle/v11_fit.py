"""
v11_fit.py — wave 5: the finest doctrine-sanctioned grids on the channels that keep winning.
Every list v8-v10 produced is topped by outer-cycle phases read at 30/15 degrees while the trees read the
continuous phase. The traditions' own finer grains: the 36 decans (10 deg), the 144 dwadasamsa (2.5 deg)
and the 360 Sabian symbols (1 deg) — "the Neptune-Pluto cycle standing on Sabian degree N" is a sentence.
Personal Sabian degrees for Sun/Moon/Venus and the Davison luminaries join them.
Then the same ladder: permissive pool -> pair products -> v10's surviving triples. Gate: CV > 0.7656.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, explain_gam as EG, v6_fit as V6, v7_fit as V7, v8_fit as V8
D = os.path.expanduser("~/.artamatch-dev/remar_sh")
V10_CV = 0.7656
CYC = (("jupiter","saturn"),("saturn","uranus"),("saturn","neptune"),("saturn","pluto"),
       ("uranus","neptune"),("uranus","pluto"),("neptune","pluto"))

def fine_singles(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    add = lambda M, nm: (blocks.append(np.asarray(M, np.float32)), names.extend(nm))
    oh = EG.onehot
    for x, y in CYC:
        ph = ((A[:, ix[x]] + B[:, ix[x]]) / 2 - (A[:, ix[y]] + B[:, ix[y]]) / 2) % 360.0
        both = (np.isfinite(A[:, ix[x]]) & np.isfinite(B[:, ix[x]])
                & np.isfinite(A[:, ix[y]]) & np.isfinite(B[:, ix[y]]))
        p = np.where(both, ph, np.nan)
        add(*oh(np.floor(p / 10), 36, f"cycle36_{x}_{y}"))
        add(*oh(np.floor(p / 2.5), 144, f"cycle144_{x}_{y}"))
        add(*oh(np.floor(p), 360, f"sabian_cycle_{x}_{y}"))
    for tag, C in (("his", A), ("her", B)):
        for b in ("sun", "moon", "venus"):
            add(*oh(np.floor(C[:, ix[b]] % 360), 360, f"{tag}_{b}_sabian"))
    # Davison Sun/Moon Sabian degree (mean-motion midpoint chart, same construction as EG)
    import importlib.util
    _dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
    dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    dt = jb - ja
    for b in ("sun", "moon"):
        ta, tb = A[:, ix[b]], B[:, ix[b]]
        raw = (tb - ta + 180.0) % 360.0 - 180.0
        k = np.round((dv.MEAN[b] * dt - raw) / 360.0)
        davb = np.where(np.isfinite(dt), (ta + (raw + 360.0 * k) / 2.0) % 360.0, np.nan)
        add(*oh(np.floor(davb), 360, f"dav_{b}_sabian"))
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
    XF, nF = fine_singles(tr, Z, "train"); XFt, _ = fine_singles(te, Z, "test")
    sup = XF.sum(0) >= 40                       # a Sabian degree almost no couple occupies cannot be learned
    XF, XFt = XF[:, sup], XFt[:, sup]; nF = [n for n, s in zip(nF, sup) if s]
    Xall = np.column_stack([X6, XA, XL, XF]); Xallt = np.column_stack([X6t, XAt, XLt, XFt])
    names = n6 + nA + nL + nF; pos = {n: i for i, n in enumerate(names)}
    del X6, XA, XL, XF, X6t, XAt, XLt, XFt
    print(f"  singles bank: {Xall.shape[1]:,} ({len(nF):,} fine-grid, support-kept)", flush=True)

    m0 = Lasso(alpha=5e-5, positive=True, max_iter=12000); m0.fit(Xall, ytr)
    pool = np.where(m0.coef_ > 0)[0]
    if len(pool) > 800:
        pool = pool[np.argsort(-m0.coef_[pool])][:800]
    print(f"  survivor pool at alpha=5e-5: {len(pool)}", flush=True)
    top = pool[np.argsort(-m0.coef_[pool])][:220]
    Xt_top, Xtt_top = Xall[:, top], Xallt[:, top]
    ptr, pte, pn = [], [], []
    for i in range(len(top)):
        Pi = Xt_top[:, i:i+1] * Xt_top[:, i+1:]
        js = np.where(Pi.sum(0) >= 30)[0] + i + 1
        if len(js):
            ptr.append(Xt_top[:, i:i+1] * Xt_top[:, js]); pte.append(Xtt_top[:, i:i+1] * Xtt_top[:, js])
            pn += [f"{names[top[i]]} AND {names[top[j]]}" for j in js]
    Xp, Xpt = np.column_stack(ptr), np.column_stack(pte)
    M10 = json.load(open(os.path.expanduser("~/.artamatch-dev/v10_model.json")))
    ttr, tte, tn = [], [], []
    for kname in M10["weights"]:
        parts = kname.split(" AND ")
        if len(parts) < 2 or not all(p in pos for p in parts):
            continue
        cols = [pos[p] for p in parts]
        base_tr = np.prod(Xall[:, cols], 1); base_te = np.prod(Xallt[:, cols], 1)
        if len(parts) == 2:                       # extend v10's surviving pairs AND triples by one clause
            ext = top[:120]
        else:
            ext = top[:60]
        C = base_tr[:, None] * Xall[:, ext]
        js = np.where((C.sum(0) >= 30) & ~np.isin(ext, cols))[0]
        if len(js):
            ttr.append(C[:, js]); tte.append(base_te[:, None] * Xallt[:, ext[js]])
            tn += [f"{kname} AND {names[ext[j]]}" for j in js]
    Xq = np.column_stack(ttr) if ttr else np.zeros((len(tr), 0), np.float32)
    Xqt = np.column_stack(tte) if tte else np.zeros((len(te), 0), np.float32)
    if Xq.shape[1]:
        hv = (Xq.astype(bool).T @ np.random.default_rng(3).normal(size=len(tr))).round(9)
        _, keep = np.unique(hv, return_index=True)
        Xq, Xqt = Xq[:, sorted(keep)], Xqt[:, sorted(keep)]; tn = [tn[k] for k in sorted(keep)]
    Xtr = np.column_stack([Xall[:, pool], Xp, Xq]).astype(np.float32)
    Xte = np.column_stack([Xallt[:, pool], Xpt, Xqt]).astype(np.float32)
    fn = [names[i] for i in pool] + pn + tn
    del Xall, Xallt, Xp, Xpt, Xq, Xqt
    print(f"  v11 matrix: {len(pool)} singles + {len(pn):,} pairs + {len(tn):,} deeper = {Xtr.shape[1]:,}", flush=True)

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
    for alpha in (7e-5, 1e-4, 1.5e-4):
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
    print(f"\n  CV winner: relaxed alpha={alpha} (CV {cv:.4f}) vs v10 declared CV {V10_CV}")
    if cv <= V10_CV:
        print("  CV does not beat v10 — NO test read spent; v10 remains the declared model.")
        return
    m = Lasso(alpha=alpha, positive=True, max_iter=12000); m.fit(Xtr, ytr)
    surv = np.where(m.coef_ > 0)[0]
    w, b0 = G.fit_nonneg(Xtr[:, surv], yi, np.ones(len(yi)))
    zt = Xte[:, surv] @ w + b0
    weights = {fn[i]: float(v) for i, v in zip(surv, w) if v > 0}
    auc = G.auc(yte, zt)
    n1 = sum(1 for k in weights if " AND " not in k)
    print(f"\n  v11 relaxed alpha={alpha} · {len(weights)} rules ({n1} singles) · "
          f"TEST AUC (read once): {auc:.4f}   [v10 0.7731 · ensemble 0.7747]")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:12]:
        print(f"    {k_[:100]:<102} +{v:.4f}")
    json.dump({"model": "ArtaMatch v11 (relaxed, fine grids + deep conjunctions)", "alpha": alpha,
               "mode": "relaxed", "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4),
               "intercept": float(b0), "n_matrix": int(Xtr.shape[1]), "n_surviving": len(weights),
               "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v11_model.json"), "w"), indent=1)
    np.save(os.path.expanduser("~/.artamatch-dev/v11_test_z.npy"), zt)
    print("  saved v11_model.json + v11_test_z.npy")


if __name__ == "__main__":
    main()
