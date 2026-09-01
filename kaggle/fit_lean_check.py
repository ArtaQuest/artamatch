"""fit_lean_check.py — is the shipped model still too big?

The body ablation says Chiron and Mars cost nothing, yet two of the five shipped phasors mention
them. If they are truly dispensable, a model of just the Neptune/Pluto phasors should score the same,
and shipping five would be three numbers of decoration. Fit every prefix of the agreed list, and the
Neptune/Pluto subset on its own.
"""
import json, os
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P
from closed_newton import _solve, DEV

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
rp = json.load(open(f"{D_}/report_final.json"))
full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, x in enumerate(nm) if x != "true_south_node"]
bod = [nm[i].replace("true_", "").replace("mean_", "") for i in keep]
A, B = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
n = len(y)
ids = pd.read_csv(f"{D_}/_train_ids.csv", dtype=str)
parent = {}
def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
for a, b in zip(ids.pid_a, ids.pid_b):
    pa, pb = find(a), find(b)
    if pa != pb: parent[pa] = pb
gid = pd.factorize(pd.Series([find(a) for a in ids.pid_a]))[0]
fold = np.random.default_rng(7).integers(0, P.NFOLD, gid.max() + 1)[gid]
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)
yt = torch.from_numpy(y).to(DEV)

def ang(t):
    i, j, k = t["i"], t["j"], t["kind"]
    if k == "xdiff": return A[:, i] - B[:, j]
    if k == "aspM":  return A[:, i] - A[:, j]
    if k == "aspW":  return B[:, i] - B[:, j]
def cv(ph):
    cols = []
    for t in ph:
        a = ang(t) * t["k"]; cols += [np.cos(a), np.sin(a)]
    F = np.column_stack(cols + [np.ones(n)]).astype(np.float32)
    Ft = torch.from_numpy(F).to(DEV)
    oof = np.zeros(n, np.float32)
    for kf in range(P.NFOLD):
        wm = torch.from_numpy((w * (fold != kf)).astype(np.float32)).to(DEV)
        beta = np.zeros(F.shape[1])
        for step in range(3):
            bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
            pr = torch.sigmoid(Ft @ bt)
            g = (Ft.T @ (wm * (yt - pr))).cpu().numpy().astype(np.float64)
            sw = (wm * (0.25 if step == 0 else pr * (1 - pr))).sqrt().unsqueeze(1)
            H = ((Ft * sw).T @ (Ft * sw)).cpu().numpy().astype(np.float64)
            sc = float(np.mean(np.diag(H)[:-1])) or 1.0
            reg = np.full(F.shape[1], rp["rl"] * sc); reg[-1] = 0.0
            H[np.diag_indices_from(H)] += reg
            beta = beta + _solve(H, g - reg * beta, sc)
        v = (Ft @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
        oof[fold == kf] = v[fold == kf]
    del Ft
    if DEV == "mps": torch.mps.empty_cache()
    return float(roc_auc_score(y, oof))

ph = rp["frequency"][:8]
print("  prefix of the fold-agreed list:")
for k in range(1, 9):
    print(f"    {k} phasors ({2*k+1:>2} weights)   {cv(ph[:k]):.4f}    +{ph[k-1]['fam']} {ph[k-1]['label']}")
NP = {"neptune", "pluto"}
sub = [t for t in ph[:5] if {bod[t["i"]], bod[t["j"]] if t["j"] is not None else bod[t["i"]]} <= NP]
print(f"\n  the Neptune/Pluto phasors alone ({len(sub)} of the first 5):")
for t in sub: print(f"    {t['fam']} {t['label']}")
print(f"    -> {cv(sub):.4f}")
json.dump({"prefix": {str(k): cv(ph[:k]) for k in range(1, 9)},
           "neptune_pluto_only": cv(sub), "n_np": len(sub)},
          open(f"{D_}/report_lean.json", "w"), indent=1)
