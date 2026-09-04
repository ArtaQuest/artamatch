"""comp_aspect_terms.py — A TERM PER MAJOR ASPECT, EACH WITH ITS OWN WEIGHT (operator 2026-09-04).

No harmonics. The traditional aspects are named angles — conjunction 0, semisextile 30, sextile 60,
square 90, trine 120, quincunx 150, opposition 180 — and each gets its own weight. Three arms,
because "a term for each aspect" can mean three different models and the difference matters:

  GLOBAL   seven terms in the whole model: for each aspect, ONE weight applied to how much the two
           charts are in that aspect (the orb-weighted count over all 169 cross-chart pairs). This
           is the literal reading: "how much does being at a trine matter, at all".
  SMOOTH   one term per (aspect pair, aspect angle): w * cos(theta - A), the phase fixed at the
           traditional angle instead of fitted. 169 x 7 candidates, greedy selection.
  ORB      the tradition's actual claim: a bump at the aspect, symmetric in direction (120 either
           way is a trine), f = exp(-d^2 / 2 sigma^2) with d the distance to the nearer of +-A and
           sigma = orb/2. 169 x 7 candidates, greedy selection.

The ORB arm is NOT a sinusoid, so the publish gate would refuse to ship it — it is a measurement of
the tradition's own feature shape, not a deployment candidate, and it is reported as such.

Env: AQ_DIR, AQ_ARMS, AQ_ORB (8 degrees), AQ_KMAX (32), AQ_NOUTER (10), AQ_RL, AQ_CPU.
Writes AQ_DIR/report_aspect_terms.json.
"""
import json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from scipy.linalg import cho_factor, cho_solve
from closed_newton import DEV as _DEV
DEV = "cpu" if os.environ.get("AQ_CPU") == "1" else _DEV

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
ARMS = os.environ.get("AQ_ARMS", "global,smooth,orb").split(",")
ORB = float(os.environ.get("AQ_ORB", "8")); KMAX = int(os.environ.get("AQ_KMAX", "32"))
NOUTER = int(os.environ.get("AQ_NOUTER", "10")); RL = float(os.environ.get("AQ_RL", "0.003"))
ASPECTS = [("conjunction", 0.0), ("semisextile", 30.0), ("sextile", 60.0), ("square", 90.0),
           ("trine", 120.0), ("quincunx", 150.0), ("opposition", 180.0)]
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32); n = len(y)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, x in enumerate(nm) if x != "true_south_node"]
bod = [nm[i].replace("true_", "").replace("mean_", "") for i in keep]
RA, RB = tha[:, okb][:, keep], thb[:, okb][:, keep]          # degrees
NB = len(bod)
PAIRS = [(i, j) for i in range(NB) for j in range(NB)]
TH = torch.from_numpy(np.stack([(RA[:, i] - RB[:, j]) % 360.0 for i, j in PAIRS], 1).astype(np.float32)).to(DEV)
yt = torch.from_numpy(y).to(DEV)
log(f"{NB} bodies · {len(PAIRS)} pairs · {len(ASPECTS)} aspects · orb {ORB:g}° · {n:,} couples · arms {ARMS}")

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

def wrap(x): return (x + 180.0) % 360.0 - 180.0
def orb_col(A):
    """symmetric bump at +-A: the tradition's aspect with an orb"""
    d = torch.minimum(torch.abs(wrap(TH - A)), torch.abs(wrap(TH + A)))
    return torch.exp(-(d ** 2) / (2.0 * (ORB / 2.0) ** 2))
def smooth_col(A): return torch.cos(torch.deg2rad(TH - A))

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

def within_era(sc):
    num = den = 0.0
    for d in np.unique(dec):
        r = dec == d
        if r.sum() >= 200 and 0 < y[r].sum() < r.sum(): num += roc_auc_score(y[r], sc[r]) * r.sum(); den += r.sum()
    return num / den

def arm_global():
    """seven columns: for each aspect, the orb-weighted count of pairs in it"""
    X = torch.stack([orb_col(A).sum(1) for _, A in ASPECTS], 1)
    X = (X - X.mean(0)) / X.std(0)
    A_ = torch.cat([X, torch.ones(n, 1, device=DEV)], 1)
    oof = np.zeros(n, np.float32); W = []
    for k in range(NOUTER):
        tr = fold != k
        wm = torch.from_numpy((w_all * tr).astype(np.float32)).to(DEV)
        beta = newton(A_, wm, RL); W.append(beta[:-1].tolist())
        v = (A_ @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
        oof[~tr] = v[~tr]
    wm_all = torch.from_numpy(w_all).to(DEV)
    beta = newton(A_, wm_all, RL)
    return oof, {nm_: round(float(w), 4) for (nm_, _), w in zip(ASPECTS, beta[:-1])}, np.array(W)

def arm_pairs(kind):
    """one candidate per (pair, aspect); greedy by the 1-df score test, nested"""
    build = orb_col if kind == "orb" else smooth_col
    COLS = torch.cat([build(A) for _, A in ASPECTS], 1)          # n x (7*169)
    labels = [f"{bod[i]}-{bod[j]} {an}" for an, _ in ASPECTS for (i, j) in PAIRS]
    oof = np.zeros(n, np.float32); picks = []
    for k in range(NOUTER):
        tr = fold != k
        wm = torch.from_numpy((w_all * tr).astype(np.float32)).to(DEV)
        pr0 = float((y[tr] * w_all[tr]).sum() / w_all[tr].sum())
        eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
        sel = []
        for _ in range(KMAX):
            pr = torch.sigmoid(eta); r = wm * (yt - pr); vw = wm * pr * (1 - pr)
            g = COLS.T @ r; S = (COLS * COLS * vw.unsqueeze(1)).sum(0)
            z = g * g / (S + 1e-12)
            if sel: z[torch.tensor(sel, dtype=torch.long, device=DEV)] = -1.0
            sel.append(int(torch.argmax(z).item()))
            A_ = torch.cat([COLS[:, torch.tensor(sel, dtype=torch.long, device=DEV)], torch.ones(n, 1, device=DEV)], 1)
            beta = newton(A_, wm, RL)
            eta = A_ @ torch.from_numpy(beta.astype(np.float32)).to(DEV)
            del A_
        oof[~tr] = eta.cpu().numpy()[~tr]
        picks.append([labels[s] for s in sel])
        log(f"     {kind} fold {k+1}/{NOUTER} · fold AUC {roc_auc_score(y[~tr], oof[~tr]):.4f}")
    del COLS
    from collections import Counter
    which = Counter(a.split()[-1] for p in picks for a in p)
    return oof, dict(which), picks[0][:8]

out = {}
for arm in ARMS:
    if arm == "global":
        oof, weights, W = arm_global()
        a, w = float(roc_auc_score(y, oof)), float(within_era(oof))
        stab = {nm_: round(float(np.mean(np.sign(W[:, i]))), 2) for i, (nm_, _) in enumerate(ASPECTS)}
        log(f"  GLOBAL (7 terms) AUC {a:.4f} · within-era {w:.4f}")
        log(f"     weights: {weights}")
        log(f"     sign agreement across folds (1 = same sign every fold): {stab}")
        out["global"] = {"auc": round(a, 4), "within_era": round(w, 4), "weights": weights, "sign_agreement": stab}
    else:
        oof, which, first = arm_pairs(arm)
        a, w = float(roc_auc_score(y, oof)), float(within_era(oof))
        log(f"  {arm.upper()} (169x7 candidates, K={KMAX}) AUC {a:.4f} · within-era {w:.4f}")
        log(f"     aspects chosen across folds: {which}")
        log(f"     first fold's first 8: {first}")
        out[arm] = {"auc": round(a, 4), "within_era": round(w, 4), "aspect_counts": which, "first_fold": first}
    np.save(f"{D_}/oof_aspect_{arm}.npy", oof)
    json.dump({"orb": ORB, "kmax": KMAX, "nouter": NOUTER, "aspects": [a for a, _ in ASPECTS], "arms": out},
              open(f"{D_}/report_aspect_terms.json", "w"), indent=1)
log("saved report_aspect_terms.json")
