"""fit_maxout.py — MAX OUT the fixed-term CV, then bring EVERY fast body in with real weight.

Operator orders (2026-09-01): "inluce all the fast bodies and ensure trained properly and have
maximum weight" + "max out auc". Procedure:

  A. The frontier's within-fold selection is noisy past ~7 terms; the fold-AGREED list refit as a
     FIXED structure is not. Scan every prefix of the agreed list (fixed-term 10-fold CV, same
     folds, same closed-form solver) and take the prefix that maximises AUC.
  B. Fast bodies = sun, moon, mercury, venus, mars, jupiter, saturn. For each one missing from
     that model, run the SAME 2-df score selection the main search used — restricted to phasors
     involving that body — inside every fold, take the fold-agreement winner, add it, measure the
     CV delta. Sequential (each addition conditions the next), ordered by each body's best score.
  C. On the final structure, sweep lambda over a wide grid by CV and PROVE the chosen one is
     interior (a boundary lambda is an unconverged sweep). Then prove the 3-step closed form
     reaches the gradient solution: refit the same penalised objective with Adam to convergence
     and compare train AUC and weights.
  D. Report every fast body's fitted amplitude sqrt(a^2+c^2) on the full-data refit — "maximum
     weight" means the amplitude the data itself supports at the CV-chosen lambda, not a clamp.

Writes report_maxout.json + maxout_terms.json (the exporter ships from the latter).
"""
import json, os, time, itertools
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from collections import Counter
import fit_phasor_torch as P
from closed_newton import _solve, DEV

def _solve_soft(H, g, scale):
    """as fit_final._solve_soft (NOT imported — importing fit_final runs the whole search)"""
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
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
rp = json.load(open(f"{D_}/report_final.json"))

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
log(f"{len(ANG)} angles x {len(HARM)} harmonics = {p:,} phasors · {n:,} couples")

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

def met_index(t):
    """a frequency-list entry -> its MET index"""
    for ix, m in enumerate(MET):
        if m["kind"] == t["kind"] and m["i"] == t["i"] and m["j"] == t["j"] and m["k"] == t["k"]:
            return ix
    raise KeyError(t)

def cols(ci):
    t = THETA[:, MET[ci]["a"]] * MET[ci]["k"]
    return torch.cos(t), torch.sin(t)

def design(sel):
    cc = []
    for c in sel:
        u, v = cols(c); cc += [u, v]
    return torch.stack(cc + [torch.ones(n, device=DEV)], 1)

def newton(Amat, wm_t, rl, steps=3):
    q = Amat.shape[1]; beta = np.zeros(q)
    for step in range(steps):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        pr = torch.sigmoid(Amat @ bt)
        g = (Amat.T @ (wm_t * (yt - pr))).cpu().numpy().astype(np.float64)
        sw = (wm_t * (0.25 if step == 0 else pr * (1 - pr))).sqrt().unsqueeze(1)
        H = ((Amat * sw).T @ (Amat * sw)).cpu().numpy().astype(np.float64)
        sc = float(np.mean(np.diag(H)[:-1])) or 1.0
        reg = np.full(q, rl * sc); reg[-1] = 0.0
        H[np.diag_indices_from(H)] += reg
        beta = beta + _solve_soft(H, g - reg * beta, sc)
    return beta

def cvfix(sel, rl):
    """fixed-term pooled 10-fold CV AUC"""
    Amat = design(sel)
    oof = np.zeros(n, np.float32)
    for kf in range(P.NFOLD):
        wm_t = torch.from_numpy((w * (fold != kf)).astype(np.float32)).to(DEV)
        beta = newton(Amat, wm_t, rl)
        v = (Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
        oof[fold == kf] = v[fold == kf]
    del Amat
    if DEV == "mps": torch.mps.empty_cache()
    return float(roc_auc_score(y, oof))

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

RL0 = rp["rl"]
freq = rp["frequency"]
agreed = [met_index(t) for t in freq]   # ALL agreed terms — a best prefix on the scan boundary is unconverged

# ---- A. the prefix frontier of the AGREED list, as a fixed structure -------------------------
log("A. fixed-term CV of every prefix of the fold-agreed list")
prefix_auc = {}
for K in range(1, len(agreed) + 1):
    prefix_auc[K] = cvfix(agreed[:K], RL0)
    log(f"   {K:>2} phasors ({2*K+1:>2} weights)  {prefix_auc[K]:.4f}   +{freq[K-1]['folds']}/10 {freq[K-1]['fam']} {freq[K-1]['label']}")
Kstar = max(prefix_auc, key=prefix_auc.get)
assert Kstar < len(agreed), "best prefix is the whole list — the scan never turned over"
base = agreed[:Kstar]
log(f"   BEST PREFIX: {Kstar} phasors -> {prefix_auc[Kstar]:.4f}  (frontier best was {rp['best']:.4f} with within-fold selection)")

# ---- B. bring every missing fast body in ------------------------------------------------------
FAST = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
def bodies_of(sel):
    s = set()
    for c in sel:
        m = MET[c]; s.add(bod[m["i"]]); s.add(bod[m["j"]])
    return s
present = bodies_of(base)
missing = [b for b in FAST if b not in present]
log(f"B. bodies in the base model: {sorted(present)}")
log(f"   fast bodies missing: {missing}")

INV = {b: torch.tensor([bod[m["i"]] == b or bod[m["j"]] == b for m in MET], device=DEV) for b in FAST}
sel = list(base); added = []
auc_now = prefix_auc[Kstar]
while missing:
    # for each missing body, the fold-agreement winner among ITS phasors, by the same 2-df score
    cand = {}
    for b in missing:
        picks = []
        Amat = design(sel)
        for kf in range(P.NFOLD):
            wm_t = torch.from_numpy((w * (fold != kf)).astype(np.float32)).to(DEV)
            beta = newton(Amat, wm_t, RL0)
            pr = torch.sigmoid(Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV))
            z = score_all(wm_t * (yt - pr), wm_t * pr * (1 - pr), sel, INV[b])
            picks.append(int(torch.argmax(z).item()))
        del Amat
        if DEV == "mps": torch.mps.empty_cache()
        (win, agree), = Counter(picks).most_common(1)
        cand[b] = (win, agree)
    # add the body whose winner helps CV most (max out AUC subject to all-fast-in)
    scored = {b: cvfix(sel + [win], RL0) for b, (win, agree) in cand.items()}
    b = max(scored, key=scored.get)
    win, agree = cand[b]
    delta = scored[b] - auc_now
    log(f"   + {b:<8} {MET[win]['fam']} {MET[win]['label']:<38} agree {agree}/10 · CV {scored[b]:.4f} ({delta:+.4f})")
    sel.append(win); auc_now = scored[b]
    added.append({"body": b, "met": win, "label": MET[win]["label"], "fam": MET[win]["fam"],
                  "agree": agree, "cv_after": scored[b], "delta": round(delta, 4)})
    missing.remove(b)

log(f"   final structure: {len(sel)} phasors ({2*len(sel)+1} weights) · CV {auc_now:.4f} at rl={RL0}")
assert set(FAST) <= bodies_of(sel), "a fast body is still missing"

# ---- C. lambda sweep on the final structure — the chosen one must be INTERIOR -----------------
log("C. lambda sweep (fixed structure, 10-fold CV)")
GRID = [1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]
sweep = {}
for rl in GRID:
    sweep[rl] = cvfix(sel, rl)
    log(f"   rl {rl:<8g} {sweep[rl]:.4f}")
rl_star = max(sweep, key=sweep.get)
assert rl_star not in (GRID[0], GRID[-1]), f"boundary lambda {rl_star} — widen the grid"
cv_final = sweep[rl_star]
log(f"   chosen rl {rl_star} (interior) · CV {cv_final:.4f}")

# ---- closed form vs gradient, on the full data at rl* -----------------------------------------
Amat = design(sel)
w_t = torch.from_numpy(w).to(DEV)
beta_cf = newton(Amat, w_t, rl_star)
auc_cf = float(roc_auc_score(y, (Amat @ torch.from_numpy(beta_cf.astype(np.float32)).to(DEV)).cpu().numpy()))
# the same penalised objective, by Adam, to convergence
q = Amat.shape[1]
sw = (w_t * 0.25).sqrt().unsqueeze(1)
H0 = ((Amat * sw).T @ (Amat * sw)).cpu().numpy().astype(np.float64)
sc = float(np.mean(np.diag(H0)[:-1]))
bt = torch.zeros(q, device=DEV, requires_grad=True)
opt = torch.optim.Adam([bt], lr=0.05)
reg_t = torch.full((q,), rl_star * sc, device=DEV); reg_t[-1] = 0.0
for it in range(4000):
    opt.zero_grad()
    eta = Amat @ bt
    loss = (w_t * torch.nn.functional.binary_cross_entropy_with_logits(eta, yt, reduction="none")).sum() \
           + 0.5 * (reg_t * bt * bt).sum()
    loss.backward(); opt.step()
beta_gd = bt.detach().cpu().numpy().astype(np.float64)
auc_gd = float(roc_auc_score(y, (Amat @ bt.detach()).cpu().numpy()))
wdiff = float(np.max(np.abs(beta_cf - beta_gd)))
log(f"   closed form: train AUC {auc_cf:.4f} · Adam 4000 steps: {auc_gd:.4f} · max|w_cf - w_gd| {wdiff:.4f}")
assert auc_cf >= auc_gd - 1e-4, "closed form fell short of the gradient solution"

# ---- D. every fast body's fitted amplitude ----------------------------------------------------
log("D. fitted amplitudes on the full data (weight each body actually carries)")
amp_by_term = []
for t_i, c in enumerate(sel):
    a_, c_ = beta_cf[2 * t_i], beta_cf[2 * t_i + 1]
    amp_by_term.append({"label": MET[c]["label"], "fam": MET[c]["fam"], "k": MET[c]["k"],
                        "kind": MET[c]["kind"], "i": MET[c]["i"], "j": MET[c]["j"],
                        "w_cos": round(float(a_), 4), "w_sin": round(float(c_), 4),
                        "amp": round(float(np.hypot(a_, c_)), 4),
                        "bodies": sorted({bod[MET[c]["i"]], bod[MET[c]["j"]]})})
for t in sorted(amp_by_term, key=lambda t: -t["amp"]):
    log(f"   amp {t['amp']:.4f}  {t['fam']}  {t['label']}")
for b in FAST:
    amps = [t["amp"] for t in amp_by_term if b in t["bodies"]]
    assert amps and max(amps) > 0, f"{b} carries no weight"
    log(f"   {b:<8} in {len(amps)} term(s) · max amplitude {max(amps):.4f}")

json.dump({"prefix_auc": {str(k): round(v, 4) for k, v in prefix_auc.items()},
           "K_star": Kstar, "fast_added": added, "rl_sweep": {str(k): round(v, 4) for k, v in sweep.items()},
           "rl_star": rl_star, "cv_final": round(cv_final, 4),
           "closed_vs_gradient": {"auc_cf": round(auc_cf, 4), "auc_gd": round(auc_gd, 4),
                                  "max_wdiff": round(wdiff, 4)},
           "terms": amp_by_term, "bias": round(float(beta_cf[-1]), 4)},
          open(f"{D_}/report_maxout.json", "w"), indent=1)
json.dump({"met": [{"kind": MET[c]["kind"], "i": MET[c]["i"], "j": MET[c]["j"], "k": MET[c]["k"],
                    "label": MET[c]["label"], "fam": MET[c]["fam"]} for c in sel],
           "rl": rl_star, "cv": round(cv_final, 4)},
          open(f"{D_}/maxout_terms.json", "w"), indent=1)
log("saved report_maxout.json + maxout_terms.json")
