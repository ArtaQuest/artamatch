"""Pre-binned isotonic: bin train z into equal-count bins (>=~1,100 each), take each bin's empirical
rate, run isotonic (PAVA) over the bin means. Kills the sparse-tail leaves that plain isotonic overfits
(15.6%-predicted -> 5.9%-observed on test). Method validated on v16; applied to the deployed model.
Usage: calibrate2.py <research_model.json> <deploy.json>"""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
D = os.path.expanduser("~/.artamatch-dev/remar_sh3")

tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
sol = pd.read_csv(f"{D}/solution.csv")
ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
yte = sol.ended_in_divorce.to_numpy().astype(int)
Z = np.load(f"{D}/phases.npz", allow_pickle=True)
M = json.load(open(sys.argv[1])); MD = json.load(open(sys.argv[2]))

def build(df, half):
    X6, n6 = V6.bank(df, Z, half)
    XA, nA = V7.additions(df, Z, half)
    XL, nL = V8.last_singles(df, Z, half)
    XN, nN = V13.new_singles(df, Z, half, set(n6 + nA + nL))
    return np.column_stack([X6, XA, XL, XN]), {n: i for i, n in enumerate(n6 + nA + nL + nN)}

def rulescore(X, pos, weights, b0):
    z = np.full(X.shape[0], b0)
    for k, w in weights.items():
        parts = k.split(" AND ")
        v = X[:, pos[parts[0]]].copy()
        for p in parts[1:]:
            v *= X[:, pos[p]]
        z += w * v
    return z

Xtr, pos = build(tr, "train"); Xte, _ = build(te, "test")
z_tr = rulescore(Xtr, pos, M["weights"], M["intercept"])
z_te = rulescore(Xte, pos, M["weights"], M["intercept"])

from sklearn.isotonic import IsotonicRegression
def binned_iso(z, y, nb=40):
    qs = np.quantile(z, np.linspace(0, 1, nb + 1))
    qs[0] -= 1e9; qs[-1] += 1e9
    mz, mr = [], []
    for i in range(nb):
        m = (z > qs[i]) & (z <= qs[i + 1])
        if m.sum() >= 50:
            mz.append(z[m].mean()); mr.append(y[m].mean())
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(np.array(mz), np.array(mr))
    return iso

def ece(p, y, nb=10):
    qs = np.quantile(p, np.linspace(0, 1, nb + 1)); qs[0] -= 1e-9; qs[-1] += 1e-9
    tot = 0.0; rows = []
    for i in range(nb):
        m = (p > qs[i]) & (p <= qs[i + 1])
        if m.sum():
            rows.append((float(p[m].mean()), float(y[m].mean()), int(m.sum())))
            tot += m.sum() / len(p) * abs(p[m].mean() - y[m].mean())
    return tot, rows

iso = binned_iso(z_tr, ytr)
p_te = iso.predict(z_te)
e, rows = ece(p_te, yte)
print(f"  TEST ECE (pre-binned isotonic): {e:.4f}  [plain isotonic was 0.0180 · deciles 0.0161]")
print(f"  distinct calibrated values on test: {len(np.unique(p_te.round(5)))}")
for pm, ym, n_ in rows:
    print(f"    {100*pm:5.1f}% -> {100*ym:5.1f}%  ({n_:,})")

# deploy: fit on ALL data with the DEPLOYED weights
Xall = np.vstack([Xtr, Xte]); y_all = np.concatenate([ytr, yte])
z_all = rulescore(Xall, pos, MD["weights"], MD["intercept"])
iso_d = binned_iso(z_all, y_all)
bx = [float(v) for v in iso_d.X_thresholds_]; by = [float(v) for v in iso_d.y_thresholds_]
MD["calibration_isotonic"] = {"x": bx, "y": by,
    "note": "pre-binned monotone empirical share, fit on all couples; linear between points, clipped outside"}
json.dump(MD, open(sys.argv[2], "w"), indent=1)
print(f"  deployed calibration: {len(bx)} breakpoints · {100*min(by):.2f}%–{100*max(by):.1f}% · saved")
