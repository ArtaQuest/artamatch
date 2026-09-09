"""fit_feature_ablation.py — what each FEATURE in the shipped model is worth.

The frontier says how many phasors are needed; it does not say what any one of them contributes once
the others are present. This holds the term set fixed at the knee, drops each phasor in turn, and
re-runs the whole ten-fold fit without it. Also drops each FAMILY (XY, XX, YY) the same way.

The term set is the one the folds AGREED on — a phasor nine of ten folds chose independently — not
the single best fold's list, which is one draw.

Contributions are measured against the fixed-term model's own CV, not against the frontier's value at
that k. Those are different models: the frontier re-picks its terms inside every fold, so subtracting
from it made every term in an earlier run of this look harmful, which was an arithmetic error rather
than a finding.
"""
import itertools, json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from collections import Counter
import fit_phasor_torch as P
from closed_newton import _solve, DEV

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_max"))
K = int(os.environ.get("AQ_K", "8"))
RL = float(os.environ.get("AQ_RL", "0.003"))
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

rp = json.load(open(f"{D_}/report_final.json"))
terms = rp["frequency"][:K]
log(f"{K} phasors, agreed by {terms[0]['folds']}..{terms[-1]['folds']} of 10 folds")

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm_all = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, x in enumerate(nm_all) if x != "true_south_node"]
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
    raise ValueError(k)

COLS = []
for t in terms:
    a = ang(t) * t["k"]
    COLS.append((np.cos(a).astype(np.float32), np.sin(a).astype(np.float32)))

def cv(use):
    cc = []
    for ix in use:
        c, s = COLS[ix]; cc += [c, s]
    F = np.column_stack(cc + [np.ones(n)]).astype(np.float32)
    Ft = torch.from_numpy(F).to(DEV)
    oof = np.zeros(n, np.float32)
    for kf in range(P.NFOLD):
        trm = fold != kf
        wm = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
        beta = np.zeros(F.shape[1])
        for step in range(3):
            bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
            pr = torch.sigmoid(Ft @ bt)
            g = (Ft.T @ (wm * (yt - pr))).cpu().numpy().astype(np.float64)
            sw = (wm * (0.25 if step == 0 else pr * (1 - pr))).sqrt().unsqueeze(1)
            H = ((Ft * sw).T @ (Ft * sw)).cpu().numpy().astype(np.float64)
            sc = float(np.mean(np.diag(H)[:-1])) or 1.0
            reg = np.full(F.shape[1], RL * sc); reg[-1] = 0.0
            H[np.diag_indices_from(H)] += reg
            beta = beta + _solve(H, g - reg * beta, sc)
        p_ = (Ft @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
        oof[fold == kf] = p_[fold == kf]
    del Ft
    if DEV == "mps": torch.mps.empty_cache()
    return float(roc_auc_score(y, oof))

base = cv(list(range(K)))
log(f"the fixed {K}-phasor model: {base:.4f}\n")
rows = []
for ix, t in enumerate(terms):
    a = cv([q for q in range(K) if q != ix])
    rows.append({"fam": t["fam"], "label": t["label"], "k": t["k"], "folds": t["folds"],
                 "auc_without": a, "contribution": base - a})
    log(f"   without {t['fam']:<3} {t['label']:<32}{a:.4f}   contributes {base - a:+.5f}")
log("\nRANKED")
for r in sorted(rows, key=lambda r: -r["contribution"]):
    log(f"   {r['contribution']:+.5f}  {r['fam']:<3} {r['label']}")
fam_rows = []
for f in ("XY", "XX", "YY"):
    use = [ix for ix, t in enumerate(terms) if t["fam"] != f]
    if not use or len(use) == K: continue
    a = cv(use)
    fam_rows.append({"family": f, "n_dropped": K - len(use), "auc_without": a,
                     "contribution": base - a})
    log(f"\n   without the whole {f} family ({K - len(use)} phasors): {a:.4f}   "
        f"costs {base - a:+.5f}")
json.dump({"k": K, "base": base, "features": rows, "families": fam_rows},
          open(f"{D_}/report_features.json", "w"), indent=1)
log("\nsaved report_features.json")
