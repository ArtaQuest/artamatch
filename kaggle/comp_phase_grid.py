"""comp_phase_grid.py — ONE universal ideal separation for every aspect (operator 2026-09-04:
"forget about k (harmonics). use a universal ideal separation for all aspects and find it by grid
search every 5 degrees. report the top 10 angles by AUC").

    score = bias + sum over aspect pairs of  w_ij * cos(theta_ij - phi)      one shared phi

No harmonics (k = 1 throughout) and ONE weight per aspect instead of two, so an aspect can only be
strong or weak, never re-phased: the phase is a single global number, grid-searched every 5 degrees.
Two arms per phi, both nested with the standing fold structure (groups by marriage-graph component):

  FULL      all 169 cross-chart aspects carry a weight, ridge-penalised, no selection
  SELECTED  a greedy to AQ_KMAX aspects by the 1-degree-of-freedom score test (the 2-df test does
            not apply: with the phase fixed there is one column per aspect)

A negative weight is a 180-degree phase flip, so AUC(phi) must equal AUC(phi+180) exactly. The grid
runs the whole circle anyway and that identity is asserted — it is a free check on the arithmetic.

Env: AQ_DIR, AQ_STEP (5), AQ_KMAX (32 selected arm), AQ_NOUTER (10), AQ_RL, AQ_ARMS (full,selected),
AQ_CPU. Writes AQ_DIR/report_phase_grid.json.
"""
import json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from scipy.linalg import cho_factor, cho_solve
from closed_newton import DEV as _DEV
DEV = "cpu" if os.environ.get("AQ_CPU") == "1" else _DEV

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
STEP = float(os.environ.get("AQ_STEP", "5")); KMAX = int(os.environ.get("AQ_KMAX", "32"))
NOUTER = int(os.environ.get("AQ_NOUTER", "10")); RL = float(os.environ.get("AQ_RL", "0.003"))
ARMS = os.environ.get("AQ_ARMS", "full,selected").split(",")
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32); n = len(y)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, x in enumerate(nm) if x != "true_south_node"]
bod = [nm[i].replace("true_", "").replace("mean_", "") for i in keep]
RA, RB = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NB = len(bod)
PAIRS = [(i, j) for i in range(NB) for j in range(NB)]
TH = torch.from_numpy(np.stack([RA[:, i] - RB[:, j] for i, j in PAIRS], 1).astype(np.float32)).to(DEV)
yt = torch.from_numpy(y).to(DEV)
log(f"{NB} bodies · {len(PAIRS)} cross-chart aspects · {n:,} couples · grid every {STEP:g}° · arms {ARMS}")

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
fold = np.random.default_rng(7).integers(0, 10, gid.max() + 1)[gid] % NOUTER
w_all = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)
yr = pd.to_numeric(full.dob_a.astype(str).str.slice(0, 4), errors="coerce").to_numpy(); dec = yr // 10 * 10

def solve(H, g, sc):
    for jit in (0.0, 1e-8, 1e-6, 1e-4, 1e-2, 1.0):
        try:
            Hj = H.copy()
            if jit: Hj[np.diag_indices_from(Hj)] += jit * sc
            return cho_solve(cho_factor(Hj, lower=True, check_finite=False), g, check_finite=False)
        except Exception: continue
    return np.linalg.lstsq(H, g, rcond=None)[0]

def newton(A, wm, rl, steps=12):
    q = A.shape[1]; beta = np.zeros(q)
    sw0 = (wm * 0.25).sqrt().unsqueeze(1)
    sc = float(np.mean(np.diag(((A * sw0).T @ (A * sw0)).cpu().numpy())[:-1])) or 1.0
    reg = np.full(q, rl * sc); reg[-1] = 0.0
    def loss(b):
        bb = torch.from_numpy(b.astype(np.float32)).to(DEV)
        return float((wm * torch.nn.functional.binary_cross_entropy_with_logits(A @ bb, yt, reduction="none")).sum()) + 0.5 * float((reg * b * b).sum())
    cur = loss(beta); g0 = None
    for step in range(steps):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        pr = torch.sigmoid(A @ bt)
        g = (A.T @ (wm * (yt - pr))).cpu().numpy().astype(np.float64) - reg * beta
        if not np.isfinite(g).all(): break
        gn = np.max(np.abs(g)); g0 = g0 or max(gn, 1e-12)
        if step >= 3 and gn < 1e-7 * g0: break
        sw = (wm * (0.25 if step == 0 else pr * (1 - pr))).sqrt().unsqueeze(1)
        H = ((A * sw).T @ (A * sw)).cpu().numpy().astype(np.float64)
        if not np.isfinite(H).all(): break
        H[np.diag_indices_from(H)] += reg
        d = solve(H, g, sc); t = 1.0
        while t >= 1 / 64:
            cand = beta + t * d; lc = loss(cand)
            if np.isfinite(lc) and lc <= cur + 1e-9 * abs(cur): beta, cur = cand, lc; break
            t /= 2
        else: break
    return beta

def cols(phi_rad, idx=None):
    """cos(theta - phi) for every aspect (or a subset), the whole design for one shared phase"""
    C = torch.cos(TH - phi_rad)
    return C if idx is None else C[:, torch.tensor(idx, dtype=torch.long, device=DEV)]

def within_era(sc):
    num = den = 0.0
    for d in np.unique(dec):
        r = dec == d
        if r.sum() >= 200 and 0 < y[r].sum() < r.sum(): num += roc_auc_score(y[r], sc[r]) * r.sum(); den += r.sum()
    return num / den

def run_full(phi):
    oof = np.zeros(n, np.float32)
    C = cols(np.deg2rad(phi))
    A = torch.cat([C, torch.ones(n, 1, device=DEV)], 1)
    for k in range(NOUTER):
        tr = fold != k
        wm = torch.from_numpy((w_all * tr).astype(np.float32)).to(DEV)
        beta = newton(A, wm, RL)
        v = (A @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
        oof[~tr] = v[~tr]
    del A, C
    return oof

def run_selected(phi):
    """greedy by the 1-df score test — with the phase fixed each aspect is a single column"""
    oof = np.zeros(n, np.float32)
    C = cols(np.deg2rad(phi))
    for k in range(NOUTER):
        tr = fold != k
        wm = torch.from_numpy((w_all * tr).astype(np.float32)).to(DEV)
        pr0 = float((y[tr] * w_all[tr]).sum() / w_all[tr].sum())
        eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
        sel = []
        for _ in range(KMAX):
            pr = torch.sigmoid(eta); r = wm * (yt - pr); vw = wm * pr * (1 - pr)
            g = C.T @ r; S = (C * C * vw.unsqueeze(1)).sum(0)
            z = g * g / (S + 1e-12)
            if sel: z[torch.tensor(sel, dtype=torch.long, device=DEV)] = -1.0
            sel.append(int(torch.argmax(z).item()))
            A = torch.cat([C[:, torch.tensor(sel, dtype=torch.long, device=DEV)], torch.ones(n, 1, device=DEV)], 1)
            beta = newton(A, wm, RL)
            eta = A @ torch.from_numpy(beta.astype(np.float32)).to(DEV)
            del A
        oof[~tr] = eta.cpu().numpy()[~tr]
    del C
    return oof

grid = np.arange(0.0, 360.0, STEP)
res = {}
for arm in ARMS:
    fn = run_full if arm == "full" else run_selected
    res[arm] = {}
    for phi in grid:
        oof = fn(float(phi))
        a, w = float(roc_auc_score(y, oof)), float(within_era(oof))
        res[arm][float(phi)] = {"auc": round(a, 4), "within_era": round(w, 4)}
        np.save(f"{D_}/oof_phase_{arm}_{int(phi):03d}.npy", oof) if phi % 45 == 0 else None
        log(f"  {arm:8s} phi {phi:5.0f}°  AUC {a:.4f}  within-era {w:.4f}")
    # AUC(phi) == AUC(phi+180): a negative weight IS a 180-degree flip
    bad = [(p, res[arm][p]["auc"], res[arm][(p + 180) % 360]["auc"]) for p in grid
           if abs(res[arm][float(p)]["auc"] - res[arm][float((p + 180) % 360)]["auc"]) > 0.002]
    log(f"  {arm}: phase symmetry check — {len(bad)} of {len(grid)} pairs differ by more than 0.002" + (f" e.g. {bad[:2]}" if bad else " (as expected)"))
    top = sorted(res[arm].items(), key=lambda kv: -kv[1]["auc"])[:10]
    log(f"  TOP 10 SEPARATIONS ({arm}): " + " · ".join(f"{int(p)}° {v['auc']:.4f}" for p, v in top))

json.dump({"grid_step": STEP, "nouter": NOUTER, "kmax": KMAX, "n_aspects": len(PAIRS),
           "bodies": bod, "results": res}, open(f"{D_}/report_phase_grid.json", "w"), indent=1)
log("saved report_phase_grid.json")
