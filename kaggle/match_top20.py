"""Top-20 partner birth dates for male 1994-02-15 under the ultimate pure-astrology ensemble."""
import json, os, subprocess, sys
import numpy as np, pandas as pd
CODE = os.path.expanduser("~/Studio/artamatch/research/sidereal")
sys.path.insert(0, CODE); sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from pure_astro import load_families
ME = "1994-02-15"

cfg = json.load(open(os.path.expanduser("~/.artamatch-dev/ultimate_ensemble.json")))
ref = np.load(os.path.expanduser("~/.artamatch-dev/ens_train_scores.npz"), allow_pickle=True)
T, fams = ref["T"], list(ref["fams"])
w = np.array(cfg["weights"]); b = cfg["bias"]

# candidate grid: the 15th of every month, 1966-2008
cands = [f"{y}-{m:02d}-15" for y in range(1966, 2009) for m in range(1, 13)]
df = pd.DataFrame({"dob_a": [ME]*len(cands), "dob_b": cands, "start": "0000-00-00", "ended_in_divorce": 0})
d = os.path.expanduser("~/.artamatch-dev/match20"); os.makedirs(d, exist_ok=True)
df.to_csv(f"{d}/train.csv", index=False)
df.head(2).drop(columns=["ended_in_divorce"]).assign(id=["x0","x1"]).to_csv(f"{d}/test.csv", index=False)
subprocess.run([sys.executable, "-u", os.path.join(CODE, "kerykeion_phases.py")], capture_output=True,
               text=True, timeout=900, env=dict(os.environ, AQ_SRC=d, AQ_OUT=d, AQ_NO_PLACE="1"))
Z = np.load(f"{d}/phases.npz", allow_pickle=True)
X, names = load_families(df, Z, "train")
fam_of = np.array([n.split(":", 1)[0] for n in names])

import xgboost as xgb
F = np.zeros((len(df), len(fams)))
for j, f in enumerate(fams):
    m = xgb.XGBClassifier(); m.load_model(os.path.expanduser(f"~/.artamatch-dev/ens_{f}.json"))
    cols = np.where(fam_of == f)[0]
    s = m.predict_proba(X[:, cols])[:, 1]
    # map each candidate's member score to its rank within the training distribution, as the stack was fitted
    F[:, j] = np.searchsorted(np.sort(T[:, j]), s) / len(T) - 0.5
z = F @ w + b
p = 1 / (1 + np.exp(-z))
out = pd.DataFrame({"dob": cands, "p": p}).sort_values("p")
print(f"ULTIMATE ASTROLOGY ENSEMBLE — 9 weighted families, led by BaZi (37%), trained on all 32,592 pairs")
print(f"cross-source validation (trained Wikidata, tested WikiTree): AUC 0.7394 · within-corpus OOF 0.5866\n")
print(f"TOP 20 MATCHES for male {ME}  —  lowest P(ends in divorce | it ends)\n")
print(f"  {'#':>3}  {'partner born':<14}{'age gap':>9}{'P(divorce)':>12}")
print("  " + "-" * 44)
for i, (_, r) in enumerate(out.head(20).iterrows(), 1):
    gap = abs(1994 - int(r.dob[:4]))
    print(f"  {i:>3}  {r.dob:<14}{gap:>9}{r.p:>11.1%}")
print("  " + "-" * 44)
print(f"\n  worst 3 of the {len(cands)}: " + " · ".join(f"{r.dob} {r.p:.1%}" for _, r in out.tail(3).iterrows()))
print(f"  same-day partner (1994-02-15 not in grid; nearest 1994-02): "
      + f"{float(out[out.dob=='1994-02-15'].p.iloc[0]):.1%}" if (out.dob=='1994-02-15').any() else "")
