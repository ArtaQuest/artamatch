"""fit_nested.py — the WHOLE procedure inside every fold, so the quoted AUC cannot leak.

The prefix scan of the fold-agreed list creeps upward forever (0.6835 at 24 terms -> 0.6860 at 79)
and never turns over. That creep IS the leak: a term agreed by even one fold was chosen using data
that is out-of-fold for the other nine, so quoting the pooled fixed-term CV while scanning K is
selecting on the test set. The honest maximum is the nested estimate:

  outer 10-fold (same group folds as every other fit):
    on the 9 training folds only —
      greedy stepwise to KMAX by the 2-df score,
      K chosen by INNER 5-fold group CV over prefixes of that training-only ordering,
      every missing fast body (sun..saturn) forced in by its best training-set score,
      refit closed-form;
    predict the untouched outer fold.
  pooled outer AUC = the number the procedure would earn on couples it has never seen, with the
  selection, the K choice and the forced fast bodies all inside the loop.

Then the same procedure runs once on ALL data to produce the model that ships, quoting the nested
number. Writes report_nested.json + maxout_terms.json.
"""
import json, os, time, itertools
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from collections import Counter
import fit_phasor_torch as P
from closed_newton import _solve, DEV

def _solve_soft(H, g, scale):
    from scipy.linalg import cho_factor, cho_solve
    for jit in (0.0, 1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 1.0):
        try:
            Hj = H.copy()
            if jit:
                Hj[np.diag_indices_from(Hj)] += jit * scale
            c = cho_factor(Hj, lower=True, check_finite=False)
            return cho_solve(c, g, check_finite=False)
        except Exception:
            continue
    return np.linalg.lstsq(H, g, rcond=None)[0]

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_max"))
KMAX = int(os.environ.get("AQ_KMAX", "64"))
RL = float(os.environ.get("AQ_RL", "0.003"))
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
ANG = []
for i in range(NB):
    for j in range(NB):
        ANG.append((RA[:, i] - RB[:, j], f"his {bod[i]} - her {bod[j]}", "xdiff", i, j, "XY"))
for i, j in C2:
    ANG.append((RA[:, i] - RA[:, j], f"his {bod[i]} - his {bod[j]}", "aspM", i, j, "XX"))
for i, j in C2:
    ANG.append((RB[:, i] - RB[:, j], f"her {bod[i]} - her {bod[j]}", "aspW", i, j, "YY"))
HARM = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 27, 36)
MET = []
for a, (ang, name, kind, i, j, fam) in enumerate(ANG):
    for k in HARM:
        MET.append({"a": a, "k": k, "kind": kind, "i": i, "j": j, "fam": fam,
                    "angle_name": name,
                    "label": f"{k}*({name})" if k > 1 else name})
THETA = torch.from_numpy(np.column_stack([a[0].astype(np.float32) for a in ANG])).to(DEV)
p = len(MET)
A_IDX = torch.tensor([m["a"] for m in MET], device=DEV)
K_VAL = torch.tensor([float(m["k"]) for m in MET], device=DEV)
log(f"{len(ANG)} angles x {len(HARM)} harmonics = {p:,} phasors · {n:,} couples · KMAX {KMAX}")

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
FAST = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
INV = {b: torch.tensor([bod[m["i"]] == b or bod[m["j"]] == b for m in MET], device=DEV) for b in FAST}

def cols(ci):
    t = THETA[:, MET[ci]["a"]] * MET[ci]["k"]
    return torch.cos(t), torch.sin(t)

def design(sel):
    cc = []
    for c in sel:
        u, v = cols(c); cc += [u, v]
    return torch.stack(cc + [torch.ones(n, device=DEV)], 1)

def newton_on(Amat, wm_t, rl, max_steps=25):
    """DAMPED Newton on a STATIONARY objective. Two things were proven wrong the hard way here:
    (1) recomputing the ridge scale from every step's working Hessian means every step minimises a
    DIFFERENT penalty, so "convergence" is against a moving target — the scale is now fixed once,
    from the step-0 quarter-Gram, the same objective the Adam cross-check uses; (2) a full Newton
    step on a deep design can overshoot into saturation and leave a garbage fit that paints one
    constant and scores 0.4996 on its outer fold — every step is now halved until the penalised
    loss actually falls, so the iteration is monotone by construction. Each solve is still exact."""
    q = Amat.shape[1]; beta = np.zeros(q)
    sw0 = (wm_t * 0.25).sqrt().unsqueeze(1)
    H0 = ((Amat * sw0).T @ (Amat * sw0)).cpu().numpy().astype(np.float64)
    sc = float(np.mean(np.diag(H0)[:-1])) or 1.0
    reg = np.full(q, rl * sc); reg[-1] = 0.0
    reg_t = torch.from_numpy(reg.astype(np.float32)).to(DEV)

    def ploss(b):
        bt = torch.from_numpy(b.astype(np.float32)).to(DEV)
        l = (wm_t * torch.nn.functional.binary_cross_entropy_with_logits(Amat @ bt, yt, reduction="none")).sum()
        return float(l) + 0.5 * float((reg * b * b).sum())

    cur = ploss(beta); g0 = None
    for step in range(max_steps):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        pr = torch.sigmoid(Amat @ bt)
        g = (Amat.T @ (wm_t * (yt - pr))).cpu().numpy().astype(np.float64)
        gp = g - reg * beta
        if not np.isfinite(gp).all(): break
        gn = float(np.max(np.abs(gp)))
        if g0 is None: g0 = gn or 1.0
        if step >= 3 and gn < 1e-5 * g0: break
        sw = (wm_t * (0.25 if step == 0 else pr * (1 - pr))).sqrt().unsqueeze(1)
        H = ((Amat * sw).T @ (Amat * sw)).cpu().numpy().astype(np.float64)
        if not np.isfinite(H).all(): break
        H[np.diag_indices_from(H)] += reg
        delta = _solve_soft(H, gp, sc)
        t, took = 1.0, False
        while t >= 1 / 64:
            cand = beta + t * delta
            lc = ploss(cand)
            if np.isfinite(lc) and lc <= cur + 1e-9 * abs(cur):
                beta, cur, took = cand, lc, True; break
            t /= 2
        if not took: break
    return beta

def score_all(r, vw, taken, mask=None):
    z = torch.empty(p, device=DEV)
    for lo in range(0, p, 1024):
        hi = min(p, lo + 1024); sl = slice(lo, hi)
        T = THETA[:, A_IDX[sl]] * K_VAL[sl].unsqueeze(0)
        C, S = torch.cos(T), torch.sin(T)
        gc, gs = C.T @ r, S.T @ r
        Scc = (C * C * vw.unsqueeze(1)).sum(0)
        Sss = (S * S * vw.unsqueeze(1)).sum(0)
        Scs = (C * S * vw.unsqueeze(1)).sum(0)
        det = Scc * Sss - Scs * Scs
        eps = 1e-9 * (Scc + Sss).abs() + 1e-12
        zz = (gs * gs * Scc - 2 * gc * gs * Scs + gc * gc * Sss) / (det + eps)
        rho2 = (Scs * Scs) / (Scc * Sss + eps)
        z[sl] = torch.where(rho2 < 0.9, zz, torch.full_like(zz, -1.0))
        del T, C, S
    if taken: z[torch.tensor(taken, dtype=torch.long, device=DEV)] = -1.0
    if mask is not None: z[~mask] = -1.0
    return z

def stepwise(trm_np, kmax):
    """greedy selection ORDER on the rows where trm_np is True"""
    wm_t = torch.from_numpy((w * trm_np).astype(np.float32)).to(DEV)
    pr0 = float((y[trm_np] * w[trm_np]).sum() / w[trm_np].sum())
    eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
    sel = []
    for k in range(kmax):
        pr = torch.sigmoid(eta)
        sel.append(int(torch.argmax(score_all(wm_t * (yt - pr), wm_t * pr * (1 - pr), sel)).item()))
        Amat = design(sel)
        beta = newton_on(Amat, wm_t, RL)
        eta = Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV)
        del Amat
    if DEV == "mps": torch.mps.empty_cache()
    return sel

def force_fast(sel, trm_np):
    """one phasor per missing fast body, by training-set score, refit between additions"""
    wm_t = torch.from_numpy((w * trm_np).astype(np.float32)).to(DEV)
    sel = list(sel)
    forced = []
    def present():
        s = set()
        for c in sel:
            s.add(bod[MET[c]["i"]]); s.add(bod[MET[c]["j"]])
        return s
    for b in [b for b in FAST if b not in present()]:
        Amat = design(sel)
        beta = newton_on(Amat, wm_t, RL)
        pr = torch.sigmoid(Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV))
        win = int(torch.argmax(score_all(wm_t * (yt - pr), wm_t * pr * (1 - pr), sel, INV[b])).item())
        sel.append(win); forced.append((b, win))
        del Amat
    if DEV == "mps": torch.mps.empty_cache()
    return sel, forced

def pick_k(order, trm_np, seed, nfold=5):
    """inner group-CV over prefixes of a fixed ordering, on training rows only"""
    ifold = np.random.default_rng(seed).integers(0, nfold, gid.max() + 1)[gid]
    Amat = design(order)
    q = Amat.shape[1]
    oof = np.zeros((len(order), n), np.float32)
    for kf in range(nfold):
        tr = trm_np & (ifold != kf)
        wm_t = torch.from_numpy((w * tr).astype(np.float32)).to(DEV)
        for K in range(1, len(order) + 1):
            sl = list(range(2 * K)) + [q - 1]
            beta = newton_on(Amat[:, sl], wm_t, RL)
            v = (Amat[:, sl] @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
            hold = trm_np & (ifold == kf)
            oof[K - 1][hold] = v[hold]
    del Amat
    if DEV == "mps": torch.mps.empty_cache()
    inner = trm_np.copy()
    aucs = [float(roc_auc_score(y[inner], oof[K - 1][inner])) for K in range(1, len(order) + 1)]
    return int(np.argmax(aucs)) + 1, aucs

# ---- the nested estimate ----------------------------------------------------------------------
oof_outer = np.zeros(n, np.float32)
per_fold = []
for kf in range(P.NFOLD):
    trm = fold != kf
    order = stepwise(trm, KMAX)
    Kin, inner_aucs = pick_k(order, trm, seed=1000 + kf)
    sel, forced = force_fast(order[:Kin], trm)
    wm_t = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
    Amat = design(sel)
    beta = newton_on(Amat, wm_t, RL)
    v = (Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
    oof_outer[~trm] = v[~trm]
    del Amat
    if DEV == "mps": torch.mps.empty_cache()
    fauc = float(roc_auc_score(y[~trm], v[~trm]))
    per_fold.append({"K_inner": Kin, "n_forced": len(forced), "fold_auc": round(fauc, 4),
                     "forced": [b for b, _ in forced]})
    log(f"   outer {kf+1}/10 · K_inner {Kin} (+{len(forced)} forced: {','.join(b for b,_ in forced) or 'none'}) · fold AUC {fauc:.4f}")

auc_nested = float(roc_auc_score(y, oof_outer))
log(f"NESTED AUC (selection + K + forced fast bodies ALL inside the loop): {auc_nested:.4f}")
np.save(f"{D_}/oof_nested.npy", oof_outer)

# ---- the deployed model: the same procedure, once, on all data --------------------------------
log("deploy pass on ALL data")
allr = np.ones(n, bool)
order = stepwise(allr, KMAX)
Kin, inner_aucs = pick_k(order, allr, seed=77, nfold=10)
log(f"   K by 10-fold CV over the all-data ordering: {Kin}  (curve max {max(inner_aucs):.4f})")
sel, forced = force_fast(order[:Kin], allr)
log(f"   forced in: {[(b, MET[c]['label']) for b, c in forced] or 'none'}")

# lambda sweep for the final refit — interior or refuse
Amat = design(sel)
q = Amat.shape[1]
GRID = [1e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]
sw = {}
for rl in GRID:
    oo = np.zeros(n, np.float32)
    for kf in range(P.NFOLD):
        wm_t = torch.from_numpy((w * (fold != kf)).astype(np.float32)).to(DEV)
        beta = newton_on(Amat, wm_t, rl)
        v = (Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
        oo[fold == kf] = v[fold == kf]
    sw[rl] = float(roc_auc_score(y, oo))
# THE CURVE IS FLAT AT THE LOW END (measured: 1e-5..3e-3 within 1e-4 of each other), so an argmax
# lands on the low boundary by rounding luck and says nothing. On a flat curve the defensible pick
# is the LARGEST lambda whose CV is within tolerance of the best — the most-regularised model the
# data cannot tell from the winner. Only the TOP boundary would mean the sweep truly never turned
# over, and that is still refused.
best = max(sw.values())
rl_star = max(rl for rl in GRID if sw[rl] >= best - 2e-4)
assert rl_star != GRID[-1], f"boundary lambda {rl_star} — the sweep never turned over"
log(f"   lambda: {rl_star} (interior) · fixed-structure CV {sw[rl_star]:.4f} [reference only — the honest number is the nested {auc_nested:.4f}]")

w_t = torch.from_numpy(w).to(DEV)
beta_cf = newton_on(Amat, w_t, rl_star)
auc_cf = float(roc_auc_score(y, (Amat @ torch.from_numpy(beta_cf.astype(np.float32)).to(DEV)).cpu().numpy()))
# closed form vs gradient on the same penalised objective
sw0 = (w_t * 0.25).sqrt().unsqueeze(1)
sc = float(np.mean(np.diag(((Amat * sw0).T @ (Amat * sw0)).cpu().numpy())[:-1]))
bt = torch.zeros(q, device=DEV, requires_grad=True)
opt = torch.optim.Adam([bt], lr=0.05)
reg_t = torch.full((q,), rl_star * sc, device=DEV); reg_t[-1] = 0.0
for it in range(4000):
    opt.zero_grad()
    loss = (w_t * torch.nn.functional.binary_cross_entropy_with_logits(Amat @ bt, yt, reduction="none")).sum() \
           + 0.5 * (reg_t * bt * bt).sum()
    loss.backward(); opt.step()
auc_gd = float(roc_auc_score(y, (Amat @ bt.detach()).cpu().numpy()))
wdiff = float(np.max(np.abs(beta_cf - bt.detach().cpu().numpy().astype(np.float64))))
log(f"   closed form train AUC {auc_cf:.4f} vs Adam-4000 {auc_gd:.4f} · max weight diff {wdiff:.4f}")
assert auc_cf >= auc_gd - 1e-4, "closed form fell short of the gradient solution"

terms = []
for t_i, c in enumerate(sel):
    a_, c_ = beta_cf[2 * t_i], beta_cf[2 * t_i + 1]
    terms.append({"label": MET[c]["label"], "fam": MET[c]["fam"], "k": MET[c]["k"],
                  "kind": MET[c]["kind"], "i": MET[c]["i"], "j": MET[c]["j"],
                  "w_cos": round(float(a_), 4), "w_sin": round(float(c_), 4),
                  "amp": round(float(np.hypot(a_, c_)), 4),
                  "bodies": sorted({bod[MET[c]["i"]], bod[MET[c]["j"]]})})
for t in sorted(terms, key=lambda t: -t["amp"]):
    log(f"   amp {t['amp']:.4f}  {t['fam']}  {t['label']}")
for b in FAST:
    amps = [t["amp"] for t in terms if b in t["bodies"]]
    assert amps and max(amps) > 0, f"{b} missing or weightless"
    log(f"   {b:<8} in {len(amps)} term(s) · max amplitude {max(amps):.4f}")

json.dump({"nested_auc": round(auc_nested, 4), "per_fold": per_fold,
           "deploy": {"K": Kin, "n_forced": len(forced), "rl": rl_star,
                      "fixed_cv_reference": round(sw[rl_star], 4),
                      "closed_vs_gradient": {"auc_cf": round(auc_cf, 4), "auc_gd": round(auc_gd, 4),
                                             "max_wdiff": round(wdiff, 4)}},
           "rl_sweep": {str(k): round(v, 4) for k, v in sw.items()},
           "terms": terms, "bias": round(float(beta_cf[-1]), 4)},
          open(f"{D_}/report_nested_k{KMAX}.json", "w"), indent=1)
json.dump({"met": [{"kind": MET[c]["kind"], "i": MET[c]["i"], "j": MET[c]["j"], "k": MET[c]["k"],
                    "label": MET[c]["label"], "fam": MET[c]["fam"]} for c in sel],
           "rl": rl_star, "cv": round(auc_nested, 4)},
          open(f"{D_}/maxout_terms_k{KMAX}.json", "w"), indent=1)
# KMAX-STAMPED FILENAMES. The K=64 run silently overwrote the K=32 artifacts under the shared
# names, so the exporter would have shipped the WORSE model (nested 0.6783 vs 0.6794) — the same
# two-runs-one-filename failure that once put a wrong number on the live page. The name now carries
# the run's identity, and the exporter names the file it ships from.
log(f"saved report_nested_k{KMAX}.json + maxout_terms_k{KMAX}.json")
