import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
import giant_ensemble as G, v6_fit as V6, v7_fit as V7, v8_fit as V8
D = os.path.expanduser("~/.artamatch-dev/remar_sh")

te = pd.read_csv(f"{D}/test.csv", dtype=str)
sol = pd.read_csv(f"{D}/solution.csv")
tr = pd.read_csv(f"{D}/train.csv", dtype=str)
yte = sol.ended_in_divorce.to_numpy().astype(int)
ytr = pd.to_numeric(tr.ended_in_divorce).to_numpy().astype(int)
Z = np.load(f"{D}/phases.npz", allow_pickle=True)

# v8 test scores, rebuilt from the saved named weights (a reproduction of the already-read number)
X6, n6 = V6.bank(te, Z, "test"); XA, nA = V7.additions(te, Z, "test"); XL, nL = V8.last_singles(te, Z, "test")
X = np.column_stack([X6, XA, XL]); pos = {n: i for i, n in enumerate(n6 + nA + nL)}
M = json.load(open(os.path.expanduser("~/.artamatch-dev/v8_model.json")))
z8 = np.full(len(te), M["intercept"], float)
miss = 0
for name, w in M["weights"].items():
    if " AND " in name:
        a, b = name.split(" AND ", 1)
        if a in pos and b in pos:
            z8 += w * X[:, pos[a]] * X[:, pos[b]]
        else:
            miss += 1
    elif name in pos:
        z8 += w * X[:, pos[name]]
    else:
        miss += 1
assert miss == 0, f"{miss} weight names unresolvable"
print(f"  v8 reproduction: AUC {G.auc(yte, z8):.4f} (declared 0.7716)")

# ensemble test scores, reproduced exactly as wd_shuffle computed them
E = np.load(os.path.expanduser("~/.artamatch-dev/shuf_S.npz"), allow_pickle=True)
S, T = E["S"], E["T"]
scored = np.isfinite(S).all(1)
F = G.rankfeat(S[scored]); w, b = G.fit_nonneg(F, ytr[scored], np.ones(int(scored.sum())))
Ft = np.column_stack([np.searchsorted(np.sort(S[scored][:, j]), T[:, j]) / int(scored.sum()) - 0.5
                      for j in range(S.shape[1])])
ze = Ft @ w + b
print(f"  ensemble reproduction: AUC {G.auc(yte, ze):.4f} (declared 0.7747)")

rng = np.random.default_rng(11)
diffs = []
for _ in range(4000):
    ix = rng.integers(0, len(yte), len(yte))
    if yte[ix].min() == yte[ix].max():
        continue
    diffs.append(G.auc(yte[ix], ze[ix]) - G.auc(yte[ix], z8[ix]))
diffs = np.array(diffs)
lo, hi = np.percentile(diffs, [2.5, 97.5])
print(f"\n  PAIRED BOOTSTRAP ensemble minus v8-linear, 4000 resamples:")
print(f"    mean {diffs.mean():+.4f} · 95% CI [{lo:+.4f}, {hi:+.4f}] · P(ensemble better) {np.mean(diffs>0):.1%}")
print(f"    CI contains zero: {'YES — statistically level' if lo <= 0 <= hi else 'no'}")
