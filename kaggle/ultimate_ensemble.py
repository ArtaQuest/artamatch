"""
ultimate_ensemble.py — the best ensemble of pure astrology/numerology features.

One member per family (pure features only — no calendar integers, no precision flags, no counts, no mortality
physics), each an XGBoost scored out-of-fold forward-chained on the later birth; a NON-NEGATIVE logistic stack
over member ranks fitted on those OOF scores (so no member can be used backwards and a useless member takes
weight zero); then every member refitted on the ENTIRE corpus with the stack weights kept.
"""
import os, sys, json
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from pure_astro import load_families

DEP = os.path.expanduser("~/.artamatch-dev/fm_dep")     # the combined corpus final_model.py wrote

def main():
    import xgboost as xgb
    dep = pd.read_csv(f"{DEP}/train.csv", dtype=str)
    y = pd.to_numeric(dep.ended_in_divorce).to_numpy().astype(int)
    Z = np.load(f"{DEP}/phases.npz", allow_pickle=True)
    X, names = load_families(dep, Z, "train")
    fam_of = np.array([n.split(":", 1)[0] for n in names])
    fams = sorted(set(fam_of))
    print(f"  {len(dep):,} pairs · {X.shape[1]:,} pure features · {len(fams)} families", flush=True)

    later = np.fmax(pd.to_numeric(dep.dob_a.str[:4], errors="coerce").replace(0, np.nan),
                    pd.to_numeric(dep.dob_b.str[:4], errors="coerce").replace(0, np.nan))
    later = np.nan_to_num(later.to_numpy(), nan=1900).astype(int)
    cuts = [np.quantile(later, q) for q in (0.40, 0.55, 0.70, 0.85, 1.0)]
    P = dict(n_estimators=300, learning_rate=0.05, max_depth=4, min_child_weight=30, subsample=0.8,
             colsample_bytree=0.7, reg_lambda=20.0, verbosity=0, n_jobs=4)

    S, kept = [], []
    for f in fams:
        cols = np.where(fam_of == f)[0]
        if len(cols) < 3 or not np.isfinite(X[:, cols]).any():
            continue
        s, _ = G.forward_oof(X[:, cols], X[:2, cols], y, later, cuts, {"tree_method": "hist"}, seed=0)
        ok = np.isfinite(s)
        if ok.sum() < 2000:
            continue
        S.append(s); kept.append(f)
        print(f"    member {f:<22} OOF AUC {G.auc(y[ok], s[ok]):.4f} on {int(ok.sum()):,} rows", flush=True)
    S = np.column_stack(S)
    scored = np.isfinite(S).all(1)
    F = G.rankfeat(S[scored])
    w, b = G.fit_nonneg(F, y[scored], np.ones(int(scored.sum())))
    z = F @ w + b
    print(f"\n  NON-NEGATIVE STACK over {len(kept)} members · OOF AUC {G.auc(y[scored], z):.4f} "
          f"on {int(scored.sum()):,} rows", flush=True)
    order = np.argsort(-w)
    print("  stack weights:")
    for i in order:
        if w[i] > 0:
            print(f"    {kept[i]:<24} {w[i]:.3f}  ({100*w[i]/max(w.sum(),1e-9):.0f}%)")
    zero = [kept[i] for i in range(len(kept)) if w[i] == 0]
    if zero:
        print(f"    (weight zero: {', '.join(zero)})")

    # deployment: refit every kept member on the ENTIRE corpus, keep the weights
    models = {}
    for f in kept:
        cols = np.where(fam_of == f)[0]
        m = xgb.XGBClassifier(random_state=0, **P)
        m.fit(X[:, cols], y)
        models[f] = (m, cols.tolist())
        m.save_model(os.path.expanduser(f"~/.artamatch-dev/ens_{f}.json"))
    json.dump({"families": kept, "weights": w.tolist(), "bias": float(b),
               "cols": {f: models[f][1] for f in kept},
               "train_scores_ref": "ens_train_scores.npz"},
              open(os.path.expanduser("~/.artamatch-dev/ultimate_ensemble.json"), "w"), indent=1)
    # rank-transform reference: deployment scores on the training corpus, for mapping new couples to ranks
    T = np.column_stack([models[f][0].predict_proba(X[:, models[f][1]])[:, 1] for f in kept])
    np.savez_compressed(os.path.expanduser("~/.artamatch-dev/ens_train_scores.npz"), T=T,
                        fams=np.array(kept, dtype=object))
    print(f"\n  deployed: every member refitted on all {len(dep):,} pairs; weights + rank reference saved")

if __name__ == "__main__":
    main()
