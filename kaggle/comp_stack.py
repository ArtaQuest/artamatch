"""comp_stack.py — A PHASOR MODEL PER BODY, THEN AN ENSEMBLE OVER THEM (operator 2026-09-03:
"fit individual phasors for each body and then stack them as ensembles").

Every body — the 13 real ones and all 387 pseudo-bodies — gets its OWN small phasor model, fitted
only on the cross-chart angles that body takes part in (his b to her j for every j, and his i to
her b for every i, first harmonic). Their scores are then stacked by a ridge logistic meta-model.
Two bias/variance points differ from the single greedy: each base learner sees a 799-candidate
space instead of 160,000, and the meta averages 400 weak learners instead of choosing 32 terms.

THE STACK IS NESTED, so the number is honest:
  outer fold k        the rows the whole procedure never touches
    inner folds       base models fit on inner-train, predicting inner-val -> the meta's training
                      features for the training rows (never a base model's own fitted rows)
    base refit        on all training rows, to score fold k
    meta              ridge logistic on the 400 base columns, trained on the inner-OOF features
  pooled AUC over the outer predictions, plus the within-era AUC (decade held fixed).

Env: AQ_DIR, AQ_NOUTER (5), AQ_NINNER (3), AQ_KB (3 phasors per body), AQ_RL, AQ_META_RL,
AQ_SYSTEMS_FILE (systems_all.npz), AQ_BODIES_ONLY (real|all), AQ_CPU.
Writes AQ_DIR/report_stack.json and prints the per-body leaderboard.
"""
import json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from closed_newton import DEV as _DEV
DEV = "cpu" if os.environ.get("AQ_CPU") == "1" else _DEV
from scipy.linalg import cho_factor, cho_solve

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
NOUTER = int(os.environ.get("AQ_NOUTER", "5")); NINNER = int(os.environ.get("AQ_NINNER", "3"))
KB = int(os.environ.get("AQ_KB", "3")); RL = float(os.environ.get("AQ_RL", "0.003"))
META_RL = float(os.environ.get("AQ_META_RL", "1.0")); WHICH = os.environ.get("AQ_BODIES_ONLY", "all")
SYSF = os.environ.get("AQ_SYSTEMS_FILE", "systems_all.npz")
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
if WHICH == "all" and os.path.exists(f"{D_}/{SYSF}"):
    SZ = np.load(f"{D_}/{SYSF}", allow_pickle=True)
    bod += [str(x) for x in SZ["names"]]
    RA = np.concatenate([RA, np.deg2rad(SZ["theta_a_sys"])], 1)
    RB = np.concatenate([RB, np.deg2rad(SZ["theta_b_sys"])], 1)
NB = len(bod)
RA_t = torch.from_numpy(RA.astype(np.float32)).to(DEV); RB_t = torch.from_numpy(RB.astype(np.float32)).to(DEV)
yt = torch.from_numpy(y).to(DEV)
log(f"{NB} bodies · {n:,} couples · {NOUTER} outer x {NINNER} inner folds · {KB} phasors per body")

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
rng = np.random.default_rng(7)
fold = rng.integers(0, 10, gid.max() + 1)[gid] % NOUTER
inner_of = rng.integers(0, 97, gid.max() + 1)[gid] % NINNER      # by GROUP, so families never split
w_all = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)

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
    cur = None
    for step in range(steps):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        pr = torch.sigmoid(A @ bt)
        g = (A.T @ (wm * (yt - pr))).cpu().numpy().astype(np.float64) - reg * beta
        if not np.isfinite(g).all(): break
        if step >= 3 and np.max(np.abs(g)) < 1e-6 * max(1e-12, gn0): break
        if step == 0: gn0 = max(np.max(np.abs(g)), 1e-12)
        sw = (wm * (0.25 if step == 0 else pr * (1 - pr))).sqrt().unsqueeze(1)
        H = ((A * sw).T @ (A * sw)).cpu().numpy().astype(np.float64)
        if not np.isfinite(H).all(): break
        H[np.diag_indices_from(H)] += reg
        d = solve(H, g, sc); t = 1.0
        def loss(b):
            bb = torch.from_numpy(b.astype(np.float32)).to(DEV)
            return float((wm * torch.nn.functional.binary_cross_entropy_with_logits(A @ bb, yt, reduction="none")).sum()) + 0.5 * float((reg * b * b).sum())
        cur = loss(beta) if cur is None else cur
        while t >= 1 / 64:
            cand = beta + t * d; lc = loss(cand)
            if np.isfinite(lc) and lc <= cur + 1e-9 * abs(cur): beta, cur = cand, lc; break
            t /= 2
        else: break
    return beta

def cand_angles(b):
    """the XY angles body b takes part in: his b to her j for all j, his i to her b for all i"""
    return [(b, j) for j in range(NB)] + [(i, b) for i in range(NB) if i != b]

def design(pairs, sel):
    cols = []
    for s in sel:
        i, j = pairs[s]
        th = RA_t[:, i] - RB_t[:, j]
        cols += [torch.cos(th), torch.sin(th)]
    return torch.stack(cols + [torch.ones(n, device=DEV)], 1)

def base_fit(b, rows):
    """greedy ortho 2-df score test to KB phasors, on `rows` only"""
    pairs = cand_angles(b)
    wm = torch.from_numpy((w_all * rows).astype(np.float32)).to(DEV)
    pr0 = float((y[rows] * w_all[rows]).sum() / w_all[rows].sum())
    eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
    sel = []
    I = torch.tensor([p[0] for p in pairs], device=DEV); J = torch.tensor([p[1] for p in pairs], device=DEV)
    for _ in range(KB):
        pr = torch.sigmoid(eta); r = wm * (yt - pr); vw = wm * pr * (1 - pr)
        TH = RA_t[:, I] - RB_t[:, J]
        C, S = torch.cos(TH), torch.sin(TH)
        if sel:                                            # exact score test: project out the model
            X = design(pairs, sel); XW = X * vw.unsqueeze(1)
            G = (X.T @ XW).cpu().numpy().astype(np.float64); G[np.diag_indices_from(G)] += 1e-6 * float(np.mean(np.diag(G)))
            Gi = torch.from_numpy(np.linalg.inv(G).astype(np.float32)).to(DEV)
            C = C - X @ (Gi @ (XW.T @ C)); S = S - X @ (Gi @ (XW.T @ S))
        gc, gs = C.T @ r, S.T @ r
        Scc = (C * C * vw.unsqueeze(1)).sum(0); Sss = (S * S * vw.unsqueeze(1)).sum(0); Scs = (C * S * vw.unsqueeze(1)).sum(0)
        det = Scc * Sss - Scs * Scs; eps = 1e-9 * (Scc + Sss).abs() + 1e-12
        z = (gs * gs * Scc - 2 * gc * gs * Scs + gc * gc * Sss) / (det + eps)
        z = torch.where((Scs * Scs) / (Scc * Sss + eps) < 0.9, z, torch.full_like(z, -1.0))
        if sel: z[torch.tensor(sel, dtype=torch.long, device=DEV)] = -1.0
        sel.append(int(torch.argmax(z).item()))
        A = design(pairs, sel); beta = newton(A, wm, RL)
        eta = A @ torch.from_numpy(beta.astype(np.float32)).to(DEV)
        del A, TH, C, S
    A = design(pairs, sel); beta = newton(A, wm, RL)
    score = (A @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
    del A
    return score, [pairs[s] for s in sel]

oof = np.zeros(n, np.float32); base_auc = np.zeros((NOUTER, NB))
for k in range(NOUTER):
    tr = fold != k
    F_tr = np.zeros((n, NB), np.float32)          # inner-OOF features on training rows
    F_te = np.zeros((n, NB), np.float32)          # refit-on-train features on fold k
    for b in range(NB):
        for iv in range(NINNER):
            rows = tr & (inner_of != iv)
            s, _ = base_fit(b, rows)
            hold = tr & (inner_of == iv); F_tr[hold, b] = s[hold]
        s, _ = base_fit(b, tr)
        F_te[~tr, b] = s[~tr]
        base_auc[k, b] = roc_auc_score(y[~tr], s[~tr])
        if b % 50 == 0: log(f"   fold {k+1}/{NOUTER} · body {b+1}/{NB} ({bod[b]}) base AUC {base_auc[k, b]:.4f}")
    Xtr = torch.from_numpy(np.column_stack([F_tr, np.ones(n, np.float32)])).to(DEV)
    wm = torch.from_numpy((w_all * tr).astype(np.float32)).to(DEV)
    beta = newton(Xtr, wm, META_RL)
    Xte = torch.from_numpy(np.column_stack([F_te, np.ones(n, np.float32)])).to(DEV)
    v = (Xte @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
    oof[~tr] = v[~tr]
    log(f"   fold {k+1}/{NOUTER} · STACK fold AUC {roc_auc_score(y[~tr], v[~tr]):.4f}")
    del Xtr, Xte

auc = float(roc_auc_score(y, oof))
yr = pd.to_numeric(full.dob_a.astype(str).str.slice(0, 4), errors="coerce").to_numpy(); dec = yr // 10 * 10
num = den = 0.0
for d in np.unique(dec):
    r = dec == d
    if r.sum() >= 200 and 0 < y[r].sum() < r.sum(): num += roc_auc_score(y[r], oof[r]) * r.sum(); den += r.sum()
log(f"STACK NESTED AUC: {auc:.4f} · WITHIN-ERA {num/den:.4f}   ({NB} per-body models stacked)")
order = np.argsort(-base_auc.mean(0))
log("top base learners: " + " · ".join(f"{bod[i]} {base_auc.mean(0)[i]:.4f}" for i in order[:12]))
np.save(f"{D_}/oof_stack_{NB}b_k{KB}_o{NOUTER}.npy", oof)
json.dump({"nested_auc": round(auc, 4), "within_era_auc": round(num / den, 4), "n_bodies": NB,
           "kb": KB, "nouter": NOUTER, "ninner": NINNER, "meta_rl": META_RL,
           "base_auc_mean": {bod[i]: round(float(base_auc.mean(0)[i]), 4) for i in order}},
          open(f"{D_}/report_stack_{NB}b_k{KB}_o{NOUTER}.json", "w"), indent=1)
log(f"saved report_stack_{NB}b_k{KB}_o{NOUTER}.json")
