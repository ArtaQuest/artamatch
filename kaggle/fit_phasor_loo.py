"""fit_phasor_loo.py — the leave-one-out contribution of EVERY term in the final model.

The ablation names the minimal model: the top-m sin/cos terms of the surviving families. This
refits the full 10-fold CV once per term with ONLY that term removed; the contribution is

    contribution(term) = AUC(all m terms) - AUC(all but this one)

on identical folds, so the difference is paired and tight. Terms are reported sorted, weight
alongside, because a heavy weight and a large contribution are not the same thing: two correlated
terms can each weigh much and contribute little alone (the pair section calls those out).

Selection caveat, stated rather than hidden: the m-term set is fixed by the full-data fit, so the
ABSOLUTE AUC here is a shade optimistic; the CONTRIBUTIONS — differences on the same folds under
the same selection — are what this report is for.
"""
import itertools, json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P
from closed_newton import newton_fold, DEV

D_ = os.path.expanduser(os.environ.get("AQ_TD_DIR", "~/.artamatch-dev/tilldeath"))
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

rep = json.load(open(f"{D_}/report_ablation.json"))
alive, best_rl = rep["survivor_families"], rep["rel_lambda"]
terms = rep["terms"]
log(f"final model: families {alive} · {len(terms)} terms · rl {best_rl:g}")

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
names = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, nm in enumerate(names) if nm != "true_south_node"]
bod = [names[i].replace("true_", "").replace("mean_", "") for i in keep]
ra, rb = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NB = len(bod)
C2 = list(itertools.combinations(range(NB), 2))
# fam_angles duplicated here ON PURPOSE: fit_phasor_ablate.py runs its whole pipeline at import
def fam_angles(f):
    if f == "D":  return [(ra[:, i] - rb[:, i], f"D {bod[i]}") for i in range(NB)]
    if f == "NM": return [(ra[:, i], f"his {bod[i]}") for i in range(NB)]
    if f == "NW": return [(rb[:, i], f"her {bod[i]}") for i in range(NB)]
    if f == "S":  return [(ra[:, i] + rb[:, i], f"mid {bod[i]}") for i in range(NB)]
    if f == "AM": return [(ra[:, i] - ra[:, j], f"his {bod[i]}-{bod[j]}") for i, j in C2]
    if f == "AW": return [(rb[:, i] - rb[:, j], f"her {bod[i]}-{bod[j]}") for i, j in C2]
    if f == "X":  return [(ra[:, i] - rb[:, j], f"X his {bod[i]}-her {bod[j]}")
                          for i in range(NB) for j in range(NB) if i != j]
    if f == "C":  return [((ra[:, i] + rb[:, i]) - (ra[:, j] + rb[:, j]), f"comp {bod[i]}-{bod[j]}")
                          for i, j in C2]
    if f == "MM": return [(ra[:, i] + ra[:, j], f"his mid {bod[i]}/{bod[j]}") for i, j in C2]
    if f == "MW": return [(rb[:, i] + rb[:, j], f"her mid {bod[i]}/{bod[j]}") for i, j in C2]
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
w = np.where(y > 0, len(y) / (2 * y.sum()), len(y) / (2 * (len(y) - y.sum()))).astype(np.float32)
n = len(y)

# rebuild the named angle bank and resolve each final term to its column
angle, aname = [], []
for f in alive:
    for a, nm in fam_angles(f):
        angle.append(a); aname.append(nm)
cols, cnames = [], []
for a, nm in zip(angle, aname):
    cols += [np.cos(a), np.sin(a)]; cnames += [f"cos({nm})", f"sin({nm})"]
lookup = {nm: i for i, nm in enumerate(cnames)}
sel = [lookup[t["term"]] for t in terms]
Fset = np.column_stack([cols[i] for i in sel] + [np.ones(n)]).astype(np.float32)
del cols
m = len(sel)

def cvauc(Fa):
    Ft = torch.from_numpy(Fa).to(DEV)
    oof = np.zeros(n, np.float32)
    for k in range(P.NFOLD):
        res = newton_fold(Ft, y, w, fold != k, (best_rl,))
        oof[fold == k] = res[best_rl][fold == k]
    del Ft
    return float(roc_auc_score(y, oof)), oof

base_auc, base_oof = cvauc(Fset)
np.save(f"{D_}/oof_final_model.npy", base_oof)
log(f"the full {m}-term model on these folds: {base_auc:.4f}\n")

out = []
for j in range(m):
    Fj = np.ascontiguousarray(np.delete(Fset, j, axis=1))
    a, _ = cvauc(Fj)
    out.append({"term": terms[j]["term"], "w": terms[j]["w"], "auc_without": a,
                "contribution": base_auc - a})
    log(f"   {j+1:>3}/{m}  {terms[j]['term']:<34} w {terms[j]['w']:+.4f}   "
        f"without: {a:.4f}   contributes {base_auc - a:+.5f}")
out.sort(key=lambda r: -r["contribution"])
log("\nRANKED BY LEAVE-ONE-OUT CONTRIBUTION")
for r_, t in enumerate(out[:40], 1):
    log(f"   {r_:>3}. {t['term']:<34} {t['contribution']:+.5f}   (w {t['w']:+.4f})")
neg = [t for t in out if t["contribution"] < -0.0002]
if neg:
    log(f"\n{len(neg)} terms whose removal IMPROVES the model (correlated shadows):")
    for t in neg[:15]:
        log(f"     {t['term']:<34} {t['contribution']:+.5f}")
json.dump({"base_auc": base_auc, "n_terms": m, "loo": out},
          open(f"{D_}/report_loo.json", "w"), indent=1)
log("saved report_loo.json")
