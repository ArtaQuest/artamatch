"""fit_body_ablation.py — which of the thirteen bodies actually matter?

Kerykeion offers no further real bodies: everything else it exposes is a house or an angle, and both
need a birth TIME and PLACE this corpus does not have (charts are cast at 12:00 UT with a placeholder
location, so an Ascendant here would be a fact about the placeholder). The south node is the north
node plus 180 degrees exactly and is already refused as collinear.

So the open question is the other way round — which of the thirteen earn their place. Each body is
removed in turn, every angle that mentions it goes with it, and the whole sparse search is re-run at
the knee. The cost of losing a body is what it was worth.
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
HARM = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 27, 36)
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm_all = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep0 = [i for i, x in enumerate(nm_all) if x != "true_south_node"]
BOD = [nm_all[i].replace("true_", "").replace("mean_", "") for i in keep0]
RA0, RB0 = np.deg2rad(tha[:, okb][:, keep0]), np.deg2rad(thb[:, okb][:, keep0])
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

def run(drop=None):
    idx = [i for i, b in enumerate(BOD) if b != drop]
    RA, RB = RA0[:, idx], RB0[:, idx]
    NB = len(idx); C2 = list(itertools.combinations(range(NB), 2))
    ANG = ([RA[:, i] - RB[:, j] for i in range(NB) for j in range(NB)]
           + [RA[:, i] - RA[:, j] for i, j in C2] + [RB[:, i] - RB[:, j] for i, j in C2])
    TH = torch.from_numpy(np.column_stack([a.astype(np.float32) for a in ANG])).to(DEV)
    A_IDX = torch.tensor([a for a in range(len(ANG)) for _ in HARM], device=DEV)
    K_VAL = torch.tensor([float(k) for _ in range(len(ANG)) for k in HARM], device=DEV)
    p = len(ANG) * len(HARM)
    oof = np.zeros(n, np.float32)
    for kf in range(P.NFOLD):
        trm = fold != kf
        wm = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
        pr0 = float((y[trm] * w[trm]).sum() / w[trm].sum())
        eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
        sel = []
        for _ in range(K):
            pr = torch.sigmoid(eta); r = wm * (yt - pr); vw = wm * pr * (1 - pr)
            z = torch.empty(p, device=DEV)
            for lo in range(0, p, 1024):
                hi = min(p, lo + 1024); sl = slice(lo, hi)
                T = TH[:, A_IDX[sl]] * K_VAL[sl].unsqueeze(0)
                C, S = torch.cos(T), torch.sin(T)
                gc, gs = C.T @ r, S.T @ r
                Scc = (C * C * vw.unsqueeze(1)).sum(0); Sss = (S * S * vw.unsqueeze(1)).sum(0)
                Scs = (C * S * vw.unsqueeze(1)).sum(0)
                det = Scc * Sss - Scs * Scs; eps = 1e-9 * (Scc + Sss).abs() + 1e-12
                zz = (gs * gs * Scc - 2 * gc * gs * Scs + gc * gc * Sss) / (det + eps)
                z[sl] = torch.where((Scs * Scs) / (Scc * Sss + eps) < 0.9, zz, torch.full_like(zz, -1.0))
                del T, C, S
            if sel: z[torch.tensor(sel, dtype=torch.long, device=DEV)] = -1.0
            sel.append(int(torch.argmax(z).item()))
            cc = []
            for c in sel:
                t = TH[:, A_IDX[c]] * K_VAL[c]; cc += [torch.cos(t), torch.sin(t)]
            A = torch.stack(cc + [torch.ones(n, device=DEV)], 1)
            beta = np.zeros(A.shape[1])
            for step in range(3):
                bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
                pr2 = torch.sigmoid(A @ bt)
                g = (A.T @ (wm * (yt - pr2))).cpu().numpy().astype(np.float64)
                sw = (wm * (0.25 if step == 0 else pr2 * (1 - pr2))).sqrt().unsqueeze(1)
                H = ((A * sw).T @ (A * sw)).cpu().numpy().astype(np.float64)
                sc = float(np.mean(np.diag(H)[:-1])) or 1.0
                reg = np.full(A.shape[1], RL * sc); reg[-1] = 0.0
                H[np.diag_indices_from(H)] += reg
                beta = beta + _solve(H, g - reg * beta, sc)
            eta = A @ torch.from_numpy(beta.astype(np.float32)).to(DEV)
            del A
        oof[fold == kf] = eta.cpu().numpy()[fold == kf]
    del TH
    if DEV == "mps": torch.mps.empty_cache()
    return float(roc_auc_score(y, oof))

base = run(None)
log(f"all {len(BOD)} bodies, {K} phasors: {base:.4f}\n")
rows = []
for b in BOD:
    a = run(b)
    rows.append({"body": b, "auc_without": a, "cost": base - a})
    log(f"   without {b:<10}{a:.4f}   costs {base - a:+.4f}")
rows.sort(key=lambda r: -r["cost"])
log("\nRANKED BY WHAT THEY ARE WORTH")
for r in rows:
    log(f"   {r['body']:<10}{r['cost']:+.4f}")
dead = [r["body"] for r in rows if r["cost"] <= 0.0005]
log(f"\n   bodies worth keeping : {[r['body'] for r in rows if r['cost'] > 0.0005]}")
log(f"   bodies that pay nothing: {dead}")
json.dump({"k": K, "base": base, "bodies": rows, "keep": [r["body"] for r in rows if r["cost"] > 0.0005],
           "drop": dead}, open(f"{D_}/report_bodies.json", "w"), indent=1)
log("saved report_bodies.json")
