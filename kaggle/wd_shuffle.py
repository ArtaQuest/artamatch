"""
wd_shuffle.py — the interpolation ensemble (operator 2026-08-25: shuffled split, whole history on both sides).

Forward-chaining is gone because the regime changed: with every era on both sides of the split, reading the
era from the slow bodies IS the requested skill, not a leak. OOF becomes 5-fold GROUP K-fold, grouped by
marriage-graph component so a remarried chain never straddles a fold. Stack weights fit on all OOF rows.
The test half is read once, at the end. Gender swap check as before, with phases rebuilt, aligned by name.
"""
import json, os, subprocess, sys
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from pure_astro import load_families

D = os.path.expanduser(os.environ.get("AQ_D", "~/.artamatch-dev/remar_sh"))
TAG = os.environ.get("AQ_TAG", "shuf")
HP = dict(n_estimators=300, learning_rate=0.05, max_depth=4, min_child_weight=30, subsample=0.8,
          colsample_bytree=0.7, reg_lambda=20.0, verbosity=0, n_jobs=4, tree_method="hist")


def phases(df, out):
    os.makedirs(out, exist_ok=True)
    df.to_csv(f"{out}/train.csv", index=False)
    df.head(2).drop(columns=[c for c in df.columns if c == "ended_in_divorce"]).assign(
        id=["x0", "x1"]).to_csv(f"{out}/test.csv", index=False)
    subprocess.run([sys.executable, "-u", os.path.join(CODE, "kerykeion_phases.py")], capture_output=True,
                   text=True, timeout=1800, env=dict(os.environ, AQ_SRC=out, AQ_OUT=out, AQ_NO_PLACE="1"))
    return np.load(f"{out}/phases.npz", allow_pickle=True)


def main():
    import xgboost as xgb
    tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
    sol = pd.read_csv(f"{D}/solution.csv")
    ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
    ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
    yte = sol.ended_in_divorce.to_numpy().astype(int)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    print(f"  SHUFFLED interpolation · train {len(tr):,} ({ytr.mean():.1%}) · test {len(te):,} ({yte.mean():.1%})", flush=True)

    # fold groups = marriage-graph components inside train
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in zip(ids.pid_a, ids.pid_b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    comp = np.array([find(a) for a in ids.pid_a])
    _, gid = np.unique(comp, return_inverse=True)
    rngf = np.random.default_rng(7)
    fold_of_group = rngf.integers(0, 5, gid.max() + 1)
    fold = fold_of_group[gid]
    print(f"  5 group-folds over {gid.max()+1:,} components", flush=True)

    Xtr, names = load_families(tr, Z, "train")
    Xte, _ = load_families(te, Z, "test")
    fam_of = np.array([n.split(":", 1)[0] for n in names])
    fams = sorted(set(fam_of))
    print(f"  {Xtr.shape[1]:,} pure features · {len(fams)} families", flush=True)

    S, T, kept = [], [], []
    for f in fams:
        cols = np.where(fam_of == f)[0]
        if len(cols) < 3 or not np.isfinite(Xtr[:, cols]).any():
            continue
        s = np.full(len(tr), np.nan)
        for k in range(5):
            fit, ev = fold != k, fold == k
            if fit.sum() < 500 or len(np.unique(ytr[fit])) < 2:
                continue
            m = xgb.XGBClassifier(random_state=0, **HP); m.fit(Xtr[fit][:, cols], ytr[fit])
            s[ev] = m.predict_proba(Xtr[ev][:, cols])[:, 1]
        m = xgb.XGBClassifier(random_state=0, **HP); m.fit(Xtr[:, cols], ytr)
        t = m.predict_proba(Xte[:, cols])[:, 1]
        ok = np.isfinite(s)
        if ok.sum() < 2000:
            continue
        S.append(s); T.append(t); kept.append(f)
        print(f"    {f:<22} OOF {G.auc(ytr[ok], s[ok]):.4f}   TEST {G.auc(yte, t):.4f}", flush=True)
    S = np.column_stack(S); T = np.column_stack(T)
    np.savez_compressed(os.path.expanduser(f"~/.artamatch-dev/{TAG}_S.npz"), S=S, T=T,
                        kept=np.array(kept, dtype=object))
    scored = np.isfinite(S).all(1)
    F = G.rankfeat(S[scored]); w, b = G.fit_nonneg(F, ytr[scored], np.ones(int(scored.sum())))
    print(f"\n  STACK over {len(kept)} members · OOF {G.auc(ytr[scored], F @ w + b):.4f} on {int(scored.sum()):,}")
    print("  weights: " + " · ".join(f"{kept[i]} {100*w[i]/max(w.sum(),1e-9):.0f}%" for i in np.argsort(-w) if w[i] > 0))
    Ft = np.column_stack([np.searchsorted(np.sort(S[scored][:, j]), T[:, j]) / int(scored.sum()) - 0.5
                          for j in range(len(kept))])
    zt = Ft @ w + b
    auc = G.auc(yte, zt)
    print(f"\n  TEST AUC (interpolation, read once): {auc:.4f}   chance 0.5000")

    sw = te.copy(); sw["dob_a"], sw["dob_b"] = te.dob_b.values, te.dob_a.values
    Zsw = phases(sw.assign(ended_in_divorce=0), os.path.expanduser(f"~/.artamatch-dev/{TAG}_swap"))
    Xsw_raw, nsw = load_families(sw, Zsw, "train")
    pos = {nm: i for i, nm in enumerate(nsw)}
    Xsw = np.full((len(te), len(names)), np.nan, np.float32)
    for j, nm in enumerate(names):
        i = pos.get(nm)
        if i is not None:
            Xsw[:, j] = Xsw_raw[:, i]
    Fsw = np.zeros((len(te), len(kept)))
    for j, f in enumerate(kept):
        cols = np.where(fam_of == f)[0]
        m = xgb.XGBClassifier(random_state=0, **HP); m.fit(Xtr[:, cols], ytr)
        sc = m.predict_proba(Xsw[:, cols])[:, 1]
        Fsw[:, j] = np.searchsorted(np.sort(S[scored][:, j]), sc) / int(scored.sum()) - 0.5
    zsw = Fsw @ w + b
    dz = np.abs(1/(1+np.exp(-zt)) - 1/(1+np.exp(-zsw)))
    print(f"\n  GENDER CHECK — swap, phases rebuilt, name-aligned:")
    print(f"    mean |dP| {np.nanmean(dz):.4f} · max {np.nanmax(dz):.4f} · rows >1pt: {(dz>0.01).mean():.0%}")
    print(f"    swapped AUC {G.auc(yte, zsw):.4f} vs correct {auc:.4f}")

    allX = np.vstack([Xtr, Xte]); ally = np.concatenate([ytr, yte])
    ref = []
    for f in kept:
        cols = np.where(fam_of == f)[0]
        m = xgb.XGBClassifier(random_state=0, **HP); m.fit(allX[:, cols], ally)
        m.save_model(os.path.expanduser(f"~/.artamatch-dev/{TAG}_{f}.json"))
        ref.append(m.predict_proba(allX[:, cols])[:, 1])
    np.savez_compressed(os.path.expanduser(f"~/.artamatch-dev/{TAG}_ref.npz"),
                        T=np.column_stack(ref), fams=np.array(kept, dtype=object), w=w, b=b)
    json.dump({"families": kept, "weights": w.tolist(), "bias": float(b), "test_auc": float(auc)},
              open(os.path.expanduser(f"~/.artamatch-dev/{TAG}.json"), "w"), indent=1)
    print(f"\n  deployed on all {len(ally):,} pairs · saved as {TAG}")


if __name__ == "__main__":
    main()
