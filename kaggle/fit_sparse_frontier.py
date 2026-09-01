"""fit_sparse_frontier.py — the most AUC for the fewest terms, over the whole pair-only space.

Operator 2026-09-01: max out AUC with the minimum number of terms.

The candidate set is every sin and cos of every pair-only angle — 10 families, 962 angles, 1,924
terms, each one provably needing both birth charts (fit_pairspace.py tests that mechanically).

FORWARD STEPWISE, WITH THE SELECTION INSIDE EACH FOLD. At each step the next term is the one whose
score statistic against the current working residual is largest,

    z_j = | X_j' W (y - p) | / sqrt( X_j' W X_j )

which is the exact first-order criterion for the closed-form Newton fit, then the model is refitted
on the enlarged set. Every one of those steps happens on the fold's TRAINING rows only, so the
reported AUC at each k is what a stranger would get: the fold's held-out rows never influence which
terms the fold chose. That is the difference between a frontier and a flattering curve — ranking
1,924 terms on all the data and then cross-validating the winners would leak the answer into the
selection.

Reported: AUC at every k, the knee (fewest terms within TOL of the best), and how often each term is
chosen across the ten folds, which is the stability that decides what ships.
"""
import itertools, json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P
from closed_newton import _solve, DEV

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
KMAX = int(os.environ.get("AQ_KMAX", "64"))
TOL = 0.0010
RL = float(os.environ.get("AQ_RL", "0.001"))
CH = 24576
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm_all = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, x in enumerate(nm_all) if x != "true_south_node"]
bod = [nm_all[i].replace("true_", "").replace("mean_", "") for i in keep]
RA, RB = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NB = len(bod); C2 = list(itertools.combinations(range(NB), 2))
n = len(y)

def angles(f):
    d = lambda i: RA[:, i] - RB[:, i]
    s = lambda i: RA[:, i] + RB[:, i]
    if f == "D":   return [(d(i), f"D {bod[i]}", "diff", i, None) for i in range(NB)]
    if f == "S":   return [(s(i), f"mid {bod[i]}", "sum", i, None) for i in range(NB)]
    if f == "X":   return [(RA[:, i] - RB[:, j], f"his {bod[i]}-her {bod[j]}", "xdiff", i, j)
                           for i in range(NB) for j in range(NB) if i != j]
    if f == "XM":  return [(RA[:, i] + RB[:, j], f"mid his {bod[i]}/her {bod[j]}", "xsum", i, j)
                           for i in range(NB) for j in range(NB) if i != j]
    if f == "DD-": return [(d(i) - d(j), f"D {bod[i]} vs D {bod[j]}", "ddm", i, j) for i, j in C2]
    if f == "DD+": return [(d(i) + d(j), f"D {bod[i]} with D {bod[j]}", "ddp", i, j) for i, j in C2]
    if f == "SS-": return [(s(i) - s(j), f"comp {bod[i]}-{bod[j]}", "camp", i, j) for i, j in C2]
    if f == "SS+": return [(s(i) + s(j), f"comp {bod[i]} with {bod[j]}", "ssp", i, j) for i, j in C2]
    if f == "DS-": return [(d(i) - s(j), f"D {bod[i]} vs comp {bod[j]}", "dsm", i, j)
                           for i in range(NB) for j in range(NB) if i != j]
    if f == "DS+": return [(d(i) + s(j), f"D {bod[i]} with comp {bod[j]}", "dsp", i, j)
                           for i in range(NB) for j in range(NB) if i != j]
    # SINGLE-PERSON families, readmitted for the ultimate model (operator 2026-09-01). They are kept
    # in their own families so the frontier reports exactly how much of the chosen model is one
    # chart and how much is two, which is the question the whole exercise turns on.
    if f == "NM":  return [(RA[:, i], f"his {bod[i]}", "natM", i, None) for i in range(NB)]
    if f == "NW":  return [(RB[:, i], f"her {bod[i]}", "natW", i, None) for i in range(NB)]
    if f == "AM":  return [(RA[:, i] - RA[:, j], f"his {bod[i]}-{bod[j]}", "aspM", i, j) for i, j in C2]
    if f == "AW":  return [(RB[:, i] - RB[:, j], f"her {bod[i]}-{bod[j]}", "aspW", i, j) for i, j in C2]
FAMS = ["D", "S", "X", "XM", "DD-", "DD+", "SS-", "SS+", "DS-", "DS+",
        "NM", "NW", "AM", "AW"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

cols, meta = [], []
for f in FAMS:
    for ang, name, kind, i, j in angles(f):
        cols += [np.cos(ang), np.sin(ang)]
        meta += [{"trig": "cos", "kind": kind, "i": i, "j": j, "label": f"cos({name})", "fam": f},
                 {"trig": "sin", "kind": kind, "i": i, "j": j, "label": f"sin({name})", "fam": f}]
# NATAL SIGNS, as the tradition means them: a body IS or IS NOT in a sign. That is a one-hot, not a
# cosine — a sign is a 30-degree bin with hard edges, and the harmonics that would approximate it
# were measured to hurt. They enter as indicator columns and keep the same weight-on-a-named-thing
# reading as every other term.
for who, R, tag in (("his", RA, "sgM"), ("her", RB, "sgW")):
    sg = (np.degrees(R) % 360.0 // 30.0).astype(int)
    for i in range(NB):
        for k in range(12):
            c = (sg[:, i] == k).astype(np.float32)
            if c.sum() < 200:            # a sign almost nobody's body sits in cannot be learned
                continue
            cols.append(c)
            meta.append({"trig": "onehot", "kind": tag, "i": i, "j": k,
                         "label": f"{who} {bod[i]} in {SIGNS[k]}", "fam": tag})
X = np.column_stack(cols).astype(np.float32)
del cols
p = X.shape[1]
from collections import Counter as _C
_fc = _C(mm["fam"] for mm in meta)
log(f"candidate space: {p:,} terms · {X.nbytes/2**30:.2f} GB")
log("   " + " · ".join(f"{k} {v}" for k, v in _fc.items()))

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

Xt = torch.from_numpy(X).to(DEV)
yt = torch.from_numpy(y).to(DEV)
oof = np.zeros((KMAX + 1, n), np.float32)
picks = []

def fit_subset(sel, wm_t):
    """closed-form 3-step Newton on the selected columns + intercept, on the weighted rows"""
    S = Xt[:, sel]
    A = torch.cat([S, torch.ones(n, 1, device=DEV)], 1)
    q = A.shape[1]
    beta = np.zeros(q)
    G0 = None
    for step in range(3):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        pr = torch.sigmoid(A @ bt)
        g = (A.T @ (wm_t * (yt - pr))).cpu().numpy().astype(np.float64)
        sw = (wm_t * (0.25 if step == 0 else 1.0) * (1.0 if step == 0 else (pr * (1 - pr)))).sqrt().unsqueeze(1)
        H = ((A * sw).T @ (A * sw)).cpu().numpy().astype(np.float64)
        scale = float(np.mean(np.diag(H)[:-1])) or 1.0
        reg = np.full(q, RL * scale); reg[-1] = 0.0
        g = g - reg * beta
        H[np.diag_indices_from(H)] += reg
        beta = beta + _solve(H, g, scale)
    bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
    return (A @ bt), beta

for k_fold in range(P.NFOLD):
    trm = fold != k_fold
    wm_t = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
    sel, eta = [], None
    # k = 0: intercept only
    pr0 = float((y[trm] * w[trm]).sum() / (w[trm]).sum())
    eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
    oof[0][fold == k_fold] = eta.cpu().numpy()[fold == k_fold]
    for k in range(1, KMAX + 1):
        pr = torch.sigmoid(eta)
        r = wm_t * (yt - pr)                       # weighted working residual
        num = torch.zeros(p, device=DEV)
        den = torch.zeros(p, device=DEV)
        vw = wm_t * pr * (1 - pr)
        for i0 in range(0, n, CH):
            c = Xt[i0:i0 + CH]
            num += c.T @ r[i0:i0 + CH]
            den += (c * c * vw[i0:i0 + CH].unsqueeze(1)).sum(0)
        z = (num.abs() / (den.sqrt() + 1e-9))
        z[torch.tensor(sel, dtype=torch.long, device=DEV)] = -1.0 if sel else z[0] * 0 - 1.0
        j = int(torch.argmax(z).item())
        sel.append(j)
        eta, beta = fit_subset(sel, wm_t)
        oof[k][fold == k_fold] = eta.cpu().numpy()[fold == k_fold]
    picks.append(list(sel))
    log(f"   fold {k_fold+1}/{P.NFOLD} selected {KMAX} terms")

aucs = {k: float(roc_auc_score(y, oof[k])) for k in range(1, KMAX + 1)}
log("\nTHE FRONTIER — out-of-fold AUC, selection inside each fold")
for k in range(1, KMAX + 1):
    mark = ""
    if k > 1 and aucs[k] - aucs[k - 1] < 0.0002: mark = ""
    log(f"   {k:>3} terms   {aucs[k]:.4f}{mark}")
best = max(aucs.values())
knee = min(k for k in aucs if aucs[k] >= best - TOL)
log(f"\n   best {best:.4f} at k={max(aucs, key=aucs.get)}; KNEE = {knee} terms ({aucs[knee]:.4f})")

from collections import Counter
freq = Counter(j for s in picks for j in s)
stable = [j for j, c in freq.most_common() if c >= 6]
log(f"\n   {len(freq)} distinct terms ever chosen; {len(stable)} chosen by >=6 of 10 folds")
log("   the terms the folds agree on:")
for j, c in freq.most_common(20):
    log(f"     {c:>2}/10  {meta[j]['fam']:<4} {meta[j]['label']}")

PAIRF = {"D", "S", "X", "XM", "DD-", "DD+", "SS-", "SS+", "DS-", "DS+"}
log("\n   WHAT THE FRONTIER CHOSE, by kind of evidence:")
for kk in (8, 16, 32, min(64, KMAX)):
    if kk > KMAX: continue
    fl = picks[0][:kk]
    npair = sum(1 for j in fl if meta[j]["fam"] in PAIRF)
    log(f"     first {kk:>2} terms of fold 1: {npair} need both charts, {kk-npair} are one chart")
bl = json.load(open(f"{D_}/report_baselines_max.json"))
BAR = max(bl["him_only"], bl["her_only"])
log(f"\n   one chart alone = {BAR:.4f}; the frontier's best = {best:.4f} ({best - BAR:+.4f})")
json.dump({"rl": RL, "kmax": KMAX, "auc_by_k": aucs, "best": best, "knee": knee,
           "knee_auc": aucs[knee], "baselines": bl, "lift_over_best_solo": best - BAR,
           "fold_picks": picks,
           "frequency": [{"term": meta[j]["label"], "fam": meta[j]["fam"], "folds": c,
                          "idx": j} for j, c in freq.most_common(60)],
           "meta_stable": [meta[j] for j in stable]},
          open(f"{D_}/report_frontier.json", "w"), indent=1)
log("saved report_frontier.json")
