"""
v8_fit.py — the interaction wave. Products of surviving doctrine statements are still doctrine statements
("his Moon in its first decan AND her Moon in Aquarius"), and they are exactly the currency trees trade in.

Singles pool: every rule surviving a permissive Lasso (alpha=1e-4) over the v7 bank, plus the last classical
singles — SADE SATI (her Saturn in the 12th/1st/2nd sign from his Moon, and the reverse), Jaimini's
ATMAKARAKA and DARAKARAKA (the self and spouse significators, by highest/lowest degree-in-sign), and the
BaZi day-master seasonal strength (stem x birth-month branch).
Products: all pairs of the top-120 singles by weight. Then Lasso(positive) + relaxed refit, CV-chosen, one
test read.
"""
import json, os, sys
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, explain_gam as EG, v6_fit as V6, v7_fit as V7
D = os.path.expanduser("~/.artamatch-dev/remar_sh")


def last_singles(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    add = lambda M, nm: (blocks.append(np.asarray(M, np.float32)), names.extend(nm))
    oh = EG.onehot
    # SADE SATI shape: the other's Saturn counted from one's Moon sign (whole-sign distance 1..12)
    for tag, C1, C2 in (("his_moon_her_saturn", A, B), ("her_moon_his_saturn", B, A)):
        h = np.where(np.isfinite(C1[:, ix["moon"]]) & np.isfinite(C2[:, ix["saturn"]]),
                     (np.floor((C2[:, ix["saturn"]] % 360) / 30) - np.floor((C1[:, ix["moon"]] % 360) / 30)) % 12 + 1,
                     np.nan)
        add(*oh(h - 1, 12, f"{tag}_house"))
        add(np.where(np.isfinite(h), np.isin(h, [12, 1, 2]).astype(np.float32), 0).reshape(-1, 1),
            [f"{tag}_sadesati"])
    # JAIMINI: Atmakaraka = the body with the HIGHEST degree-in-sign, Darakaraka = the LOWEST (of 7 charakarakas)
    KAR = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
    for tag, C in (("his", A), ("her", B)):
        deg = np.column_stack([C[:, ix[b]] % 30.0 for b in KAR])
        ok = np.isfinite(deg).all(1)
        ak = np.where(ok, np.nanargmax(np.where(np.isfinite(deg), deg, -1), 1), np.nan)
        dk = np.where(ok, np.nanargmin(np.where(np.isfinite(deg), deg, 99), 1), np.nan)
        add(*oh(ak, 7, f"{tag}_atmakaraka", KAR))
        add(*oh(dk, 7, f"{tag}_darakaraka", KAR))
        dksign = np.full(len(df), np.nan)
        for j, b in enumerate(KAR):
            m = ok & (np.nan_to_num(dk, nan=-1) == j)
            dksign[m] = np.floor((C[m, ix[b]] % 360) / 30)
        add(*oh(dksign, 12, f"{tag}_darakaraka_sign", EG.SIGNS))
    # BaZi day-master strength: day stem x solar-month branch
    import importlib.util
    _dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
    dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    mo = lambda c: pd.to_numeric(c.str[5:7], errors="coerce").replace(0, np.nan).to_numpy(float)
    dd = lambda c: pd.to_numeric(c.str[8:10], errors="coerce").replace(0, np.nan).to_numpy(float)
    for tag, j, mcol, dcol in (("his", ja, mo(df.dob_a), dd(df.dob_a)), ("her", jb, mo(df.dob_b), dd(df.dob_b))):
        stem = np.where(np.isfinite(j), (np.nan_to_num(j) + 49) % 60 % 10, np.nan)
        mb = np.where(np.isfinite(mcol) & np.isfinite(dcol), np.where(dcol >= 5, mcol, mcol - 1) % 12, np.nan)
        pr = np.where(np.isfinite(stem) & np.isfinite(mb), stem * 12 + mb, np.nan)
        add(*oh(pr, 120, f"{tag}_stem_season", [f"{EG.STEMS[s]}x{EG.BRANCH[b]}" for s in range(10) for b in range(12)]))
    return np.column_stack(blocks).astype(np.float32), names


def main():
    from sklearn.linear_model import Lasso
    tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv"); ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(float)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X6, n6 = V6.bank(tr, Z, "train"); X6t, _ = V6.bank(te, Z, "test")
    XA, nA = V7.additions(tr, Z, "train"); XAt, _ = V7.additions(te, Z, "test")
    XL, nL = last_singles(tr, Z, "train"); XLt, _ = last_singles(te, Z, "test")
    Xall = np.column_stack([X6, XA, XL]); Xallt = np.column_stack([X6t, XAt, XLt])
    names = n6 + nA + nL
    print(f"  singles bank: {Xall.shape[1]:,} ({len(nL)} final-wave)", flush=True)

    # permissive selection to form the singles pool
    m0 = Lasso(alpha=1e-4, positive=True, max_iter=8000); m0.fit(Xall, ytr)
    pool = np.where(m0.coef_ > 0)[0]
    print(f"  survivor pool at alpha=1e-4: {len(pool)}", flush=True)
    top = pool[np.argsort(-m0.coef_[pool])][:120]
    # PRODUCTS of the top singles — each an AND of two doctrine statements
    prod_cols, prod_names = [], []
    Xt_top, Xtt_top = Xall[:, top], Xallt[:, top]
    for i in range(len(top)):
        Pi = Xt_top[:, i:i+1] * Xt_top[:, i+1:]
        keep = Pi.sum(0) >= 40                       # a conjunction almost nobody satisfies cannot be learned
        if keep.any():
            prod_cols.append((i, np.where(keep)[0] + i + 1))
    Xp_tr, Xp_te = [], []
    for i, js in prod_cols:
        Xp_tr.append(Xt_top[:, i:i+1] * Xt_top[:, js])
        Xp_te.append(Xtt_top[:, i:i+1] * Xtt_top[:, js])
        prod_names += [f"{names[top[i]]} AND {names[top[j]]}" for j in js]
    Xp_tr = np.column_stack(Xp_tr) if Xp_tr else np.zeros((len(tr), 0), np.float32)
    Xp_te = np.column_stack(Xp_te) if Xp_te else np.zeros((len(te), 0), np.float32)
    Xtr = np.column_stack([Xall[:, pool], Xp_tr]).astype(np.float32)
    Xte = np.column_stack([Xallt[:, pool], Xp_te]).astype(np.float32)
    fn = [names[i] for i in pool] + prod_names
    print(f"  v8 matrix: {len(pool)} singles + {Xp_tr.shape[1]:,} products = {Xtr.shape[1]:,}", flush=True)

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
    yi = ytr.astype(int)
    results = {}
    for alpha in (1e-4, 2e-4, 3e-4, 5e-4, 8e-4):
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
    m = Lasso(alpha=alpha, positive=True, max_iter=10000); m.fit(Xtr, ytr)
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
    print(f"\n  v8 {mode} alpha={alpha} · {len(weights)} rules ({nprod} conjunctions) · "
          f"TEST AUC (read once): {auc:.4f}   [v7 0.7630 · v6 0.7635 · ensemble 0.7747]")
    for k_, v in sorted(weights.items(), key=lambda kv: -kv[1])[:14]:
        print(f"    {k_[:76]:<78} +{v:.4f}")
    json.dump({"model": f"ArtaMatch v8 ({mode}, with conjunctions)", "alpha": alpha, "mode": mode,
               "cv_auc": round(cv, 4), "test_auc": round(float(auc), 4), "intercept": float(b0),
               "n_singles_bank": int(Xall.shape[1]), "n_matrix": int(Xtr.shape[1]),
               "n_surviving": len(weights), "weights": weights},
              open(os.path.expanduser("~/.artamatch-dev/v8_model.json"), "w"), indent=1)
    print("  saved v8_model.json")


if __name__ == "__main__":
    main()
