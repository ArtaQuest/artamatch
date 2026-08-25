"""All-data deploy refit for a pair-only rule model (v13/v14): the RULE LIST is frozen from the
research fit (structure chosen on train only); the WEIGHTS are refit on the entire corpus, per the
operator order that the inference model trains on all data. Calibration deciles computed on all data.
Usage: deploy_pair.py <model.json> <out.json>"""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
try:
    import v14_fit as V14
except Exception:
    V14 = None
D = os.path.expanduser("~/.artamatch-dev/remar_sh")

M = json.load(open(sys.argv[1]))
clauses = sorted({p for k in M["weights"] for p in k.split(" AND ")})

tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
sol = pd.read_csv(f"{D}/solution.csv")
y = np.concatenate([pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int),
                    sol.ended_in_divorce.to_numpy().astype(int)])
Z = np.load(f"{D}/phases.npz", allow_pickle=True)

def build(df, half):
    X6, n6 = V6.bank(df, Z, half)
    XA, nA = V7.additions(df, Z, half)
    XL, nL = V8.last_singles(df, Z, half)
    ex1 = set(n6 + nA + nL)
    XN, nN = V13.new_singles(df, Z, half, ex1)
    Xs, ns = [X6, XA, XL, XN], n6 + nA + nL + nN
    if V14 is not None and any(c not in set(ns) for c in clauses):
        XM, nM = V14.newer_singles(df, Z, half, ex1 | set(nN))
        Xs.append(XM); ns += nM
    return np.column_stack(Xs), ns

Xtr, names = build(tr, "train"); Xte, _ = build(te, "test")
X = np.vstack([Xtr, Xte]); pos = {n: i for i, n in enumerate(names)}
del Xtr, Xte
missing = [c for c in clauses if c not in pos]
assert not missing, f"missing clauses: {missing[:5]}"

cols = []
for k in M["weights"]:
    parts = k.split(" AND ")
    v = X[:, pos[parts[0]]].copy()
    for p in parts[1:]:
        v *= X[:, pos[p]]
    cols.append(v)
R = np.column_stack(cols).astype(np.float32)
del X
print(f"  {R.shape[0]:,} couples x {R.shape[1]} frozen rules · refitting on all data", flush=True)
w, b0 = G.fit_nonneg(R, y, np.ones(len(y)))
z = R @ w + b0
auc_all = G.auc(y, z)
qs = np.quantile(z, np.linspace(0, 1, 11))
qs[0] -= 1e6; qs[-1] += 1e6                       # finite outer edges; the page falls back to the last band
dec = []
for i in range(10):
    m_ = (z >= qs[i]) & (z < qs[i + 1])
    dec.append({"lo": float(qs[i]), "hi": float(qs[i + 1]),
                "share": float(y[m_].mean()), "n": int(m_.sum())})
weights = {k: float(v) for k, v in zip(M["weights"], w)}
kept = {k: v for k, v in weights.items() if v > 1e-9}
print(f"  in-sample AUC (all data, description only): {auc_all:.4f} · rules with weight after refit: {len(kept)}")
json.dump({"model": M["model"] + " · deployed weights refit on all 56,621 couples",
           "test_auc_research": M["test_auc"], "cv_auc": M["cv_auc"], "alpha": M["alpha"],
           "trained_on": int(len(y)), "base_rate": float(y.mean()),
           "intercept": float(b0), "weights": kept, "calibration_deciles": dec},
          open(sys.argv[2], "w"), indent=1)
print(f"  saved {sys.argv[2]}")
