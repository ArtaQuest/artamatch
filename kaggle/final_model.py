"""
final_model.py — the finalized pure-astrology model.

Design forced by the operator's three standing rules:
  1. only astrology/numerology that can predict a FUTURE (pure functions of two birth dates)
  2. the deployment fit uses the ENTIRE data
  3. WikiTree replaces Wikidata as the eventual corpus — but at 4.4% end-date coverage the sweep needs days,
     so today WikiTree serves as the INDEPENDENT test: train on Wikidata, test on WikiTree. Two different
     sources, so a shared-source artefact cannot inflate the number. When the full sweep lands, the roles flip.
"""
import os, sys
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G
from pure_astro import load_families

WD = os.path.expanduser("~/.artamatch-dev/sep4")        # maxed Wikidata: 28,839 pairs
WT = os.path.expanduser("~/.artamatch-dev/wt_corpus")   # pure WikiTree:  3,863 pairs
import subprocess

def phases_for(d, out):
    os.makedirs(out, exist_ok=True)
    env = dict(os.environ, AQ_SRC=d, AQ_OUT=out, AQ_NO_PLACE="1")
    r = subprocess.run([sys.executable, "-u", os.path.join(CODE, "kerykeion_phases.py")],
                       capture_output=True, text=True, timeout=1800, env=env)
    assert os.path.exists(os.path.join(out, "phases.npz")), r.stdout[-800:] + r.stderr[-800:]
    return np.load(os.path.join(out, "phases.npz"), allow_pickle=True)

def main():
    import xgboost as xgb
    wd_tr = pd.read_csv(f"{WD}/train.csv", dtype=str); wd_te = pd.read_csv(f"{WD}/test.csv", dtype=str)
    wd_sol = pd.read_csv(f"{WD}/solution.csv")
    wt_tr = pd.read_csv(f"{WT}/train.csv", dtype=str); wt_te = pd.read_csv(f"{WT}/test.csv", dtype=str)
    wt_sol = pd.read_csv(f"{WT}/solution.csv")
    wd_all = pd.concat([wd_tr[["dob_a","dob_b","start","ended_in_divorce"]],
                        wd_te.merge(wd_sol,on="id")[["dob_a","dob_b","start","ended_in_divorce"]]], ignore_index=True)
    wt_all = pd.concat([wt_tr[["dob_a","dob_b","start","ended_in_divorce"]],
                        wt_te.merge(wt_sol,on="id")[["dob_a","dob_b","start","ended_in_divorce"]]], ignore_index=True)
    # cross-source dedupe: any WikiTree pair whose (dob_a, dob_b) appears in Wikidata is the same couple
    seen = set(zip(wd_all.dob_a, wd_all.dob_b)) | set(zip(wd_all.dob_b, wd_all.dob_a))
    dup = np.array([(a, b) in seen for a, b in zip(wt_all.dob_a, wt_all.dob_b)])
    wt_all = wt_all[~dup].reset_index(drop=True)
    print(f"  train: Wikidata {len(wd_all):,} · independent test: WikiTree {len(wt_all):,} "
          f"({int(dup.sum()):,} shared couples removed from the test side)", flush=True)

    Zwd = phases_for(WD if os.path.exists(f"{WD}/train.csv") else WD, os.path.expanduser("~/.artamatch-dev/fm_wd"))
    # need phases for the CONCATENATED frames, so write them out
    d1 = os.path.expanduser("~/.artamatch-dev/fm_wd_all"); os.makedirs(d1, exist_ok=True)
    wd_all.to_csv(f"{d1}/train.csv", index=False)
    wd_all.head(2).drop(columns=["ended_in_divorce"]).assign(id=["x0","x1"]).to_csv(f"{d1}/test.csv", index=False)
    Z1 = phases_for(d1, d1)
    d2 = os.path.expanduser("~/.artamatch-dev/fm_wt_all"); os.makedirs(d2, exist_ok=True)
    wt_all.to_csv(f"{d2}/train.csv", index=False)
    wt_all.head(2).drop(columns=["ended_in_divorce"]).assign(id=["x0","x1"]).to_csv(f"{d2}/test.csv", index=False)
    Z2 = phases_for(d2, d2)

    Xtr, names = load_families(wd_all, Z1, "train")
    Xte, _ = load_families(wt_all, Z2, "train")
    ytr = pd.to_numeric(wd_all.ended_in_divorce).to_numpy().astype(int)
    yte = pd.to_numeric(wt_all.ended_in_divorce).to_numpy().astype(int)
    print(f"  {Xtr.shape[1]:,} pure features on both sides", flush=True)

    P = dict(n_estimators=400, learning_rate=0.04, max_depth=5, min_child_weight=30, subsample=0.8,
             colsample_bytree=0.6, reg_lambda=20.0, verbosity=0, n_jobs=4)
    s = np.mean([xgb.XGBClassifier(random_state=k, **P).fit(Xtr, ytr).predict_proba(Xte)[:, 1] for k in (0,1,2)], 0)
    auc = G.auc(yte, s)
    print(f"\n  CROSS-SOURCE TEST — trained on Wikidata, scored on WikiTree: AUC {auc:.4f}  (chance 0.5000)")

    # deployment: everything, both sources
    dep = pd.concat([wd_all, wt_all], ignore_index=True)
    d3 = os.path.expanduser("~/.artamatch-dev/fm_dep"); os.makedirs(d3, exist_ok=True)
    dep.to_csv(f"{d3}/train.csv", index=False)
    dep.head(2).drop(columns=["ended_in_divorce"]).assign(id=["x0","x1"]).to_csv(f"{d3}/test.csv", index=False)
    Z3 = phases_for(d3, d3)
    Xd, _ = load_families(dep, Z3, "train")
    yd = pd.to_numeric(dep.ended_in_divorce).to_numpy().astype(int)
    m = xgb.XGBClassifier(random_state=0, **P).fit(Xd, yd)
    m.save_model(os.path.expanduser("~/.artamatch-dev/final_model.json"))
    np.savez_compressed(os.path.expanduser("~/.artamatch-dev/final_model_meta.npz"),
                        names=np.array(names, dtype=object), cross_auc=auc, n=len(dep))
    print(f"  DEPLOYMENT model trained on the ENTIRE data: {len(dep):,} pairs, both sources. Saved.")

if __name__ == "__main__":
    main()
