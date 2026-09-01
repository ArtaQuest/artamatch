"""fix_loo_base.py — repair the leave-one-out base in report_paironly.json.

The contributions were subtracted from pruning_curve[64] = 0.7333, which is the score of a model
whose terms are chosen INSIDE each fold. The leave-one-out refits hold the 64 terms FIXED, and that
model scores higher. Subtracting the wrong base by 0.0033 made every one of the 64 terms look
harmful, which is not what was measured. The ranking is a constant shift and was never wrong; the
signs were.

Recomputes the fixed-term base on the same single seed the LOO runs used, and rewrites the field.
"""
import json, os
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P
from closed_newton import newton_fold, DEV

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
rp = json.load(open(f"{D_}/report_paironly.json"))
full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, x in enumerate(nm) if x != "true_south_node"]
ra, rb = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
n = len(y)
def ang(t):
    i, j, k = t["i"], t["j"], t["kind"]
    if k == "diff":  return ra[:, i] - rb[:, i]
    if k == "sum":   return ra[:, i] + rb[:, i]
    if k == "xdiff": return ra[:, i] - rb[:, j]
    raise ValueError(k)
cols = [np.cos(ang(t)) if t["trig"] == "cos" else np.sin(ang(t)) for t in rp["terms"]]
F = np.column_stack(cols + [np.ones(n)]).astype(np.float32)
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
rl = rp["rel_lambda"]
Ft = torch.from_numpy(F).to(DEV)
oof = np.zeros(n, np.float32)
for k in range(P.NFOLD):
    r = newton_fold(Ft, y, w, fold != k, (rl,))
    oof[fold == k] = r[rl][fold == k]
base7 = float(roc_auc_score(y, oof))
del Ft
old_base = rp["pruning_curve"][str(rp["minimal_m"])]
print(f"  seed-7 fixed-term base: {base7:.4f}   (the wrong base was {old_base:.4f})")
for t in rp["loo"]:
    without = old_base - t["contribution"]
    t["auc_without"] = without
    t["contribution"] = base7 - without
rp["loo"] = sorted(rp["loo"], key=lambda t: -t["contribution"])
rp["loo_base_seed7_fixed_terms"] = base7
rp["loo_base_note"] = ("contributions are against the FIXED-term model on seed 7; the pruning curve's "
                       "value at this m selects terms inside each fold and is not the right base")
json.dump(rp, open(f"{D_}/report_paironly.json", "w"), indent=1)
pos = sum(1 for t in rp["loo"] if t["contribution"] > 0)
print(f"  corrected: {pos} of {len(rp['loo'])} terms contribute positively")
print("  top five:")
for t in rp["loo"][:5]:
    print(f"    {t['term']:<34}{t['contribution']:+.5f}")
print("  the three whose removal helps most:")
for t in rp["loo"][-3:]:
    print(f"    {t['term']:<34}{t['contribution']:+.5f}")
