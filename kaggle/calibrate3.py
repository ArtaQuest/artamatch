"""calibrate3.py — the honest calibrator: OUT-OF-FOLD scores (5-fold, grouped by marriage component)
with the FROZEN rule list, pre-binned isotonic over them. Train-fit z overstates its own tail
(train 14.7% -> test 5.9%); OOF z does not. Output is stored as the artificial-end share; the page
displays SUCCESS = 1 - share. Usage: calibrate3.py <research.json> <deploy.json> <corpus_dir> [<extra_family_module>]"""
import importlib, json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8, v13_fit as V13
D = os.path.expanduser(sys.argv[3])

M = json.load(open(sys.argv[1])); MD = json.load(open(sys.argv[2]))
clauses = {p for k in M["weights"] for p in k.split(" AND ")}
tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
sol = pd.read_csv(f"{D}/solution.csv")
ids = pd.read_csv(f"{D}/_train_ids.csv", dtype=str)
ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
yte = sol.ended_in_divorce.to_numpy().astype(int)
Z = np.load(f"{D}/phases.npz", allow_pickle=True)

def build(df, half):
    X6, n6 = V6.bank(df, Z, half)
    XA, nA = V7.additions(df, Z, half)
    XL, nL = V8.last_singles(df, Z, half)
    XN, nN = V13.new_singles(df, Z, half, set(n6 + nA + nL))
    Xs, ns = [X6, XA, XL, XN], n6 + nA + nL + nN
    if len(sys.argv) > 4 and any(c not in set(ns) for c in clauses):
        for mname in sys.argv[4].split(","):
            mod = importlib.import_module(mname)
            fn = [f for f in dir(mod) if f.startswith("families")][0]
            XE, nE = getattr(mod, fn)(df, Z, half)
            Xs.append(XE); ns += nE
    return np.column_stack(Xs), {n: i for i, n in enumerate(ns)}

def rulemat(X, pos):
    cols = []
    for k in M["weights"]:
        parts = k.split(" AND ")
        v = X[:, pos[parts[0]]].copy()
        for p in parts[1:]:
            v *= X[:, pos[p]]
        cols.append(v)
    return np.column_stack(cols).astype(np.float32)

Xtr, pos = build(tr, "train"); Xte, _ = build(te, "test")
Rtr, Rte = rulemat(Xtr, pos), rulemat(Xte, pos)
del Xtr, Xte

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
oof = np.full(len(ytr), np.nan)
for k in range(5):
    w, b0 = G.fit_nonneg(Rtr[fold != k], ytr[fold != k], np.ones(int((fold != k).sum())))
    oof[fold == k] = Rtr[fold == k] @ w + b0
w_all, b_all = G.fit_nonneg(Rtr, ytr, np.ones(len(ytr)))
z_te = Rte @ w_all + b_all

from sklearn.isotonic import IsotonicRegression
def binned_iso(z, y, nb=40):
    qs = np.quantile(z, np.linspace(0, 1, nb + 1)); qs[0] -= 1e9; qs[-1] += 1e9
    mz, mr = [], []
    for i in range(nb):
        m = (z > qs[i]) & (z <= qs[i + 1])
        if m.sum() >= 50:
            mz.append(z[m].mean()); mr.append(y[m].mean())
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(np.array(mz), np.array(mr))
    return iso

iso = binned_iso(oof, ytr)
p_te = iso.predict(z_te)
def ece(p, y, nb=10):
    qs = np.quantile(p, np.linspace(0, 1, nb + 1)); qs[0] -= 1e-9; qs[-1] += 1e-9
    tot = 0.0; rows = []
    for i in range(nb):
        m = (p > qs[i]) & (p <= qs[i + 1])
        if m.sum():
            rows.append((float(p[m].mean()), float(y[m].mean()), int(m.sum())))
            tot += m.sum() / len(p) * abs(p[m].mean() - y[m].mean())
    return tot, rows
e, rows = ece(p_te, yte)
print(f"  OOF-calibrated · TEST ECE {e:.4f} (train-fit isotonic was ~0.018)")
for pm, ym, n_ in rows:
    print(f"    predicted {100*pm:5.1f}% -> observed {100*ym:5.1f}%  (n={n_:,})")

# deploy: OOF over the FULL corpus with the deployed weights' rule list
ids_te = pd.read_csv(f"{D}/_test_ids.csv", dtype=str)
gall = pd.concat([ids[["pid_a", "pid_b"]], ids_te[["pid_a", "pid_b"]]], ignore_index=True)
parent.clear()
for a, b in zip(gall.pid_a, gall.pid_b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb
g2 = pd.factorize(pd.Series([find(a) for a in gall.pid_a]))[0]
f2 = np.random.default_rng(7).integers(0, 5, g2.max() + 1)[g2]
Rall = np.vstack([Rtr, Rte]); y_all = np.concatenate([ytr, yte])
oof_all = np.full(len(y_all), np.nan)
for k in range(5):
    w, b0 = G.fit_nonneg(Rall[f2 != k], y_all[f2 != k], np.ones(int((f2 != k).sum())))
    oof_all[f2 == k] = Rall[f2 == k] @ w + b0
iso_d = binned_iso(oof_all, y_all)
bx = [float(v) for v in iso_d.X_thresholds_]; by = [float(v) for v in iso_d.y_thresholds_]
MD["calibration_isotonic"] = {"x": bx, "y": by,
    "note": "OOF pre-binned monotone empirical artificial-end share; page shows success = 1 - share"}
MD.pop("calibration_deciles", None)
json.dump(MD, open(sys.argv[2], "w"), indent=1)
print(f"  deployed OOF calibration: {len(bx)} breakpoints · artificial share "
      f"{100*min(by):.2f}%–{100*max(by):.1f}% -> success {100*(1-max(by)):.1f}%–{100*(1-min(by)):.2f}% · saved")
