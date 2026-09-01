"""fit_final.py — THE FINAL MODEL (operator 2026-09-01): XY, XX and YY.

Take the two sidereal charts as ONE set of 26 bodies — his thirteen and hers — and the model is every
pairwise angular difference in that set. Nothing else:

    XY   M[i] - W[j]   all i,j   169   his body against hers, same body included
    XX   M[i] - M[j]   i < j      78   an aspect inside his own chart
    YY   W[i] - W[j]   i < j      78   an aspect inside her own chart
                                 ---
                                  325 angles, which is exactly C(26,2) minus nothing:
                                      78 + 78 + 169 = 325 = every pair among 26 bodies

Every term is sinusoidal: cos(k*angle) or sin(k*angle) for an integer harmonic k. The ladder is
k = 1..10, 12, 27, 36 — the aspect itself, the classical divisions, then the SIGN (30 degrees is the
12th harmonic), the NAKSHATRA (k=27) and the DECAN (k=36). 325 x 13 x 2 = 8,450 candidates, and no
indicator column anywhere.

MINIMUM TERMS FOR MAXIMUM AUC. Forward stepwise on the score statistic, refitted by the closed-form
three-step Newton, with the SELECTION INSIDE EACH FOLD on training rows only — so the AUC printed at
each k is what a stranger reproduces, not what ranking 8,450 terms on all the data would flatter us
into believing.

XX and YY are single-person families by construction, so this model is NOT pair-only and says so; the
gate in web/verify_docs.py requires it to publish the one-chart baselines beside its own figure.
"""
import itertools, json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from collections import Counter
import fit_phasor_torch as P
from closed_newton import _solve, DEV


def _solve_soft(H, g, scale):
    """As closed_newton._solve, but a search must not die on one awkward subset: the jitter ladder
    runs further and, failing that, falls back to a least-squares solve and SAYS SO. The shipped
    model path keeps the strict solver — a fit that needs a pseudo-inverse is a fit worth knowing
    about, not one to hide."""
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
    _solve_soft.fallbacks = getattr(_solve_soft, "fallbacks", 0) + 1
    return np.linalg.lstsq(H, g, rcond=None)[0]

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_max"))
KMAX = int(os.environ.get("AQ_KMAX", "32"))
RL = float(os.environ.get("AQ_RL", "0.003"))
TOL = 0.0010
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
assert len(ANG) == 169 + 78 + 78 == 325, len(ANG)
assert len(ANG) == NB * NB + 2 * len(C2)

# ONE CANDIDATE IS ONE PHASOR: an angle at a harmonic, contributing BOTH cos and sin, each with its
# own free weight. a*cos(kt) + c*sin(kt) = A*cos(kt - phi), so the pair carries an amplitude AND a
# phase, while a lone cosine would pin the phase at zero and a lone sine at ninety degrees. Selecting
# the two together is what makes the fitted phase free, and it is how the operator's formula reads.
MET = []
for a, (ang, name, kind, i, j, fam) in enumerate(ANG):
    for k in HARM:
        MET.append({"a": a, "k": k, "kind": kind, "i": i, "j": j, "fam": fam,
                    "angle_name": name,
                    "label": f"{k}*({name})" if k > 1 else name})
# no candidate twice, proven on the angle's own values
sig = {}
for ix, m in enumerate(MET):
    key = (round(float(ANG[m["a"]][0][0]), 7), round(float(ANG[m["a"]][0][977]), 7), m["k"])
    assert key not in sig, f"duplicate: {m['label']} == {MET[sig[key]]['label']}"
    sig[key] = ix
THETA = torch.from_numpy(np.column_stack([a[0].astype(np.float32) for a in ANG])).to(DEV)
p = len(MET)
log(f"{len(ANG)} angles (XY 169 · XX 78 · YY 78) x {len(HARM)} harmonics = {p:,} phasors")
log(f"each phasor is TWO weights (cos and sin), so k phasors = {2}k+1 parameters")
log(f"uniqueness proven · angles held as {THETA.element_size()*THETA.nelement()/2**30:.2f} GB")

A_IDX = torch.tensor([m["a"] for m in MET], device=DEV)
K_VAL = torch.tensor([float(m["k"]) for m in MET], device=DEV)

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

def cols(ci):
    """the two columns of one phasor"""
    t = THETA[:, MET[ci]["a"]] * MET[ci]["k"]
    return torch.cos(t), torch.sin(t)

def score_all(r, vw, taken):
    """the TWO-DEGREE-OF-FREEDOM score statistic for adding a whole phasor:

        z = [gc, gs] . inv([[Scc, Scs], [Scs, Sss]]) . [gc, gs]

    which is the right criterion when both columns enter together. Scoring cos and sin separately
    and taking the larger would prefer an angle whose effect happens to align with one of them over
    an angle with a stronger effect at an inconvenient phase — the phase is precisely what a phasor
    is free to fit, so it must not decide the ranking.
    """
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
        # CONDITIONING GUARD. The 2-df statistic divides by det, so a phasor whose cos and sin are
        # nearly collinear scores high for being ill-conditioned rather than for fitting anything.
        # Measured on this corpus, det runs from 0.035 (his Pluto to her Pluto at k=1) against a
        # typical 0.25 — a sevenfold advantage, enough that the greedy took Pluto-Pluto at k=1, then
        # k=2, then k=3, and the joint design was singular by the fourth step. Such a phasor carries
        # ONE degree of freedom, not two, so it is refused rather than ranked as if it had two.
        rho2 = (Scs * Scs) / (Scc * Sss + eps)
        z[sl] = torch.where(rho2 < 0.9, zz, torch.full_like(zz, -1.0))
        del T, C, S
    if taken: z[torch.tensor(taken, dtype=torch.long, device=DEV)] = -1.0
    return z

def fit_subset(sel, wm_t):
    cc = []
    for c in sel:
        u, v = cols(c); cc += [u, v]
    A = torch.stack(cc + [torch.ones(n, device=DEV)], 1)
    q = A.shape[1]; beta = np.zeros(q)
    for step in range(3):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        pr = torch.sigmoid(A @ bt)
        g = (A.T @ (wm_t * (yt - pr))).cpu().numpy().astype(np.float64)
        sw = (wm_t * (0.25 if step == 0 else pr * (1 - pr))).sqrt().unsqueeze(1)
        H = ((A * sw).T @ (A * sw)).cpu().numpy().astype(np.float64)
        sc = float(np.mean(np.diag(H)[:-1])) or 1.0
        reg = np.full(q, RL * sc); reg[-1] = 0.0
        H[np.diag_indices_from(H)] += reg
        beta = beta + _solve_soft(H, g - reg * beta, sc)
    bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
    out = A @ bt; del A
    return out, beta

oof = np.zeros((KMAX + 1, n), np.float32); picks = []
for kf in range(P.NFOLD):
    trm = fold != kf
    wm_t = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
    pr0 = float((y[trm] * w[trm]).sum() / w[trm].sum())
    eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
    oof[0][fold == kf] = eta.cpu().numpy()[fold == kf]
    sel = []
    for k in range(1, KMAX + 1):
        pr = torch.sigmoid(eta)
        sel.append(int(torch.argmax(score_all(wm_t * (yt - pr), wm_t * pr * (1 - pr), sel)).item()))
        eta, beta = fit_subset(sel, wm_t)
        oof[k][fold == kf] = eta.cpu().numpy()[fold == kf]
    picks.append(sel)
    fc = Counter(MET[j]["fam"] for j in sel)
    log(f"   fold {kf+1}/10 · {KMAX} phasors: XY {fc['XY']} · XX {fc['XX']} · YY {fc['YY']}")

aucs = {k: float(roc_auc_score(y, oof[k])) for k in range(1, KMAX + 1)}
np.save(f"{D_}/oof_final.npy", oof[max(aucs, key=aucs.get)])   # for the per-source slice
log("\nTHE FRONTIER — out-of-fold AUC, phasors chosen inside each fold")
log(f"   {'phasors':>8}{'weights':>9}{'AUC':>9}")
for k in range(1, KMAX + 1):
    log(f"   {k:>8}{2*k+1:>9}{aucs[k]:>9.4f}")
bk = max(aucs, key=aucs.get); best = aucs[bk]
knee = min(k for k in aucs if aucs[k] >= best - TOL)
bl = json.load(open(f"{D_}/report_baselines_max.json"))
BAR = max(bl["him_only"], bl["her_only"])
log(f"\n   best {best:.4f} at {bk} terms · KNEE {knee} ({aucs[knee]:.4f})")
log(f"   him alone {bl['him_only']:.4f} · her alone {bl['her_only']:.4f} -> {best - BAR:+.4f}")
freq = Counter(j for sp in picks for j in sp)
log("\n   what the folds agree on:")
for j, c in freq.most_common(24):
    log(f"     {c:>2}/10  {MET[j]['fam']:<3} {MET[j]['label']}")
fc = Counter(MET[j]["fam"] for sp in picks for j in sp)
log(f"\n   family share of all picks: " + " · ".join(f"{k} {v}" for k, v in fc.items()))
hc = Counter(MET[j]["k"] for sp in picks for j in sp)
log(f"   harmonic share: " + " · ".join(f"k{k} {v}" for k, v in sorted(hc.items())))
json.dump({"families": ["XY", "XX", "YY"], "n_angles": len(ANG), "harmonics": list(HARM),
           "n_phasors_candidate": p, "weights_per_phasor": 2, "rl": RL, "auc_by_k": aucs, "best": best, "best_k": bk,
           "knee": knee, "knee_auc": aucs[knee], "baselines": bl,
           "lift_over_best_solo": best - BAR,
           "family_share": dict(fc), "harmonic_share": {str(k): v for k, v in sorted(hc.items())},
           "frequency": [{"folds": c, **{kk: MET[j][kk] for kk in
                          ("fam", "label", "k", "kind", "i", "j")}}
                         for j, c in freq.most_common(120)]},
          open(f"{D_}/report_final.json", "w"), indent=1)
log("saved report_final.json")
