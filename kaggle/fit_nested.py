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
if os.environ.get("AQ_CPU", "0") == "1":
    DEV = "cpu"      # run on the idle cores while the GPU carries another chain; identical arithmetic

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
SUMS = os.environ.get("AQ_SUMS", "0") == "1"
DD = os.environ.get("AQ_DD", "0") == "1"                      # four-body diff families ddm/ddp/camp
HARM_EXTRA = tuple(int(x) for x in os.environ.get("AQ_HARM", "").split(",") if x)
DROP_BODY = os.environ.get("AQ_DROP_BODY", "")                 # ablation: leave one body out
DROP_FAM = os.environ.get("AQ_DROP_FAM", "")                   # ablation: leave one family out
DROP_HARM = int(os.environ.get("AQ_DROP_HARM", "0"))           # ablation: leave one harmonic out
ONLY_FAM = os.environ.get("AQ_ONLY_FAM", "")                   # lean model: keep ONE family (e.g. XY)
SYSTEMS = os.environ.get("AQ_SYSTEMS", "0") == "1"             # other systems as pseudo-bodies (build_systems.py)
VAULT = os.environ.get("AQ_VAULT", "0") == "1"                 # 10% of families sealed before anything runs; one look at the end
VALIDATE = os.environ.get("AQ_VALIDATE", "0") == "1"           # every addition must improve an inner CV, else stop
SHORTLIST = int(os.environ.get("AQ_SHORTLIST", "5"))           # candidates per step put to the inner CV
VTOL = float(os.environ.get("AQ_VTOL", "0"))                    # minimum inner-CV improvement to accept
ONLY_HARM = tuple(int(x) for x in os.environ.get("AQ_ONLY_HARM", "").split(",") if x)   # lean: keep these harmonics
NOUTER = int(os.environ.get("AQ_NOUTER", "10"))                # outer folds (ablations use 5)
NO_INNER = os.environ.get("AQ_NO_INNER", "0") == "1"           # K fixed at KMAX (ablations)
ABLATE = os.environ.get("AQ_ABLATE", "0") == "1"               # outer estimate only, no deploy pass
ORTHO = os.environ.get("AQ_ORTHO", "0") == "1"                 # exact score test: project out the selected design
GROUP = os.environ.get("AQ_GROUP", "0") == "1"                 # select ANGLES (all harmonics at once), not phasors
SWAP = os.environ.get("AQ_SWAP", "0") == "1"                   # one forward-backward swap pass after the forward run
ERA = os.environ.get("AQ_ERA", "0") == "1"                     # outer folds are contiguous birth-era blocks (diagnostic)
ERA_SPLIT = int(os.environ.get("AQ_ERA_SPLIT", "0"))            # ONE split: train grooms born < year, test >= year (extrapolation)
HALPHA = float(os.environ.get("AQ_HALPHA", "0"))               # ridge scaled by k^alpha (smoothness prior)
TAG = (f"k{KMAX}" + ("_sums" if SUMS else "") + ("_dd" if DD else "")
       + (f"_h{'-'.join(map(str,HARM_EXTRA))}" if HARM_EXTRA else "")
       + (f"_rl{os.environ['AQ_RL']}" if os.environ.get("AQ_RL") else "")
       + (f"_noBody{DROP_BODY}" if DROP_BODY else "") + (f"_noFam{DROP_FAM}" if DROP_FAM else "")
       + (f"_noHarm{DROP_HARM}" if DROP_HARM else "") + (f"_o{NOUTER}" if NOUTER != 10 else "")
       + ("_ortho" if ORTHO else "") + (f"_ha{HALPHA:g}" if HALPHA else "")
       + ("_group" if GROUP else "") + ("_swap" if SWAP else "") + ("_era" if ERA else "")
       + (f"_split{ERA_SPLIT}" if ERA_SPLIT else "")
       + (f"_only{ONLY_FAM}" if ONLY_FAM else "") + (f"_h{'-'.join(map(str,ONLY_HARM))}only" if ONLY_HARM else "")
       + ("_systems" if SYSTEMS else "") + ("_vault" if VAULT else "")
       + (f"_val{SHORTLIST}" if VALIDATE else ""))
RL = float(os.environ.get("AQ_RL", "0.003"))
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm_all = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, x in enumerate(nm_all) if x != "true_south_node"
        and x.replace("true_", "").replace("mean_", "") != DROP_BODY]
bod = [nm_all[i].replace("true_", "").replace("mean_", "") for i in keep]
RA, RB = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NSTATES = [0] * len(bod)          # 0 = continuous (a planet); N = a discrete system with N states
if SYSTEMS:
    # EVERY OTHER SYSTEM AS A PSEUDO-BODY (operator 2026-09-02). Its state is an angle on its own
    # circle, so the same families give every aspect — across systems too. A harmonic that is a
    # multiple of a discrete body's state count is a constant on that circle and is skipped.
    SZ = np.load(f"{D_}/systems.npz", allow_pickle=True)
    bod = bod + [str(x) for x in SZ["names"]]
    NSTATES = NSTATES + [int(x) for x in SZ["nstates"]]
    RA = np.concatenate([RA, np.deg2rad(SZ["theta_a_sys"])], 1)
    RB = np.concatenate([RB, np.deg2rad(SZ["theta_b_sys"])], 1)
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
if SUMS:
    # THE SUM HALF OF THE PAIR ALGEBRA (operator 2026-09-01, "keep experimenting"): the diff
    # families span d-space only; sums are the composite/Davison axes. xsum includes i=j (the
    # composite chart's own axis); midM/midW stay i<j because i=j is 2*his[i] — a solo natal
    # position, which the diagonal rule excludes. Sum angles at low harmonic encode absolute
    # longitude, i.e. the CALENDAR — whatever they add, the decomposition must re-measure.
    for i in range(NB):
        for j in range(NB):
            ANG.append((RA[:, i] + RB[:, j], f"his {bod[i]} + her {bod[j]}", "xsum", i, j, "XYs"))
    for i, j in C2:
        ANG.append((RA[:, i] + RA[:, j], f"his {bod[i]} + his {bod[j]}", "midM", i, j, "XXs"))
    for i, j in C2:
        ANG.append((RB[:, i] + RB[:, j], f"her {bod[i]} + her {bod[j]}", "midW", i, j, "YYs"))
if DD:
    # FOUR-BODY DIFFERENCE FAMILIES, pure d-space (no absolute longitude, so no calendar through a
    # sum): ddm = (his i - her i) - (his j - her j), ddp = the same with a plus (midpoint axis to
    # midpoint axis), camp = the composite chart's own aspect (his i + her i) - (his j + her j).
    for i, j in C2:
        ANG.append(((RA[:, i] - RB[:, i]) - (RA[:, j] - RB[:, j]),
                    f"(his {bod[i]} - her {bod[i]}) - (his {bod[j]} - her {bod[j]})", "ddm", i, j, "DDm"))
    for i, j in C2:
        ANG.append(((RA[:, i] - RB[:, i]) + (RA[:, j] - RB[:, j]),
                    f"(his {bod[i]} - her {bod[i]}) + (his {bod[j]} - her {bod[j]})", "ddp", i, j, "DDp"))
    for i, j in C2:
        ANG.append(((RA[:, i] + RB[:, i]) - (RA[:, j] + RB[:, j]),
                    f"composite {bod[i]} - composite {bod[j]}", "camp", i, j, "CAMP"))
if DROP_FAM:
    ANG = [a for a in ANG if a[5] != DROP_FAM]
if ONLY_FAM:
    ANG = [a for a in ANG if a[5] == ONLY_FAM]
HARM = tuple(h for h in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 27, 36) + HARM_EXTRA if h != DROP_HARM)
if ONLY_HARM:
    HARM = tuple(h for h in HARM if h in ONLY_HARM)
MET = []
for a, (ang, name, kind, i, j, fam) in enumerate(ANG):
    for k in HARM:
        if any(NSTATES[x] and k % NSTATES[x] == 0 for x in (i, j)):
            continue        # constant on a discrete circle
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
fold = np.random.default_rng(7).integers(0, P.NFOLD, gid.max() + 1)[gid] % NOUTER
if ERA:
    # ERA-BLOCKED FOLDS (diagnostic, never a way to raise AUC): each outer fold is a contiguous block
    # of birth years, assigned by the component's mean husband-birth-year so no family straddles a
    # block. A model that is mostly a calendar cannot carry a birth decade it never saw, so the gap
    # between this estimate and the random-fold one IS the calendar share, measured a third way.
    yr_row = pd.to_numeric(full.dob_a.astype(str).str.slice(0, 4), errors="coerce").to_numpy()
    comp_year = pd.Series(yr_row).groupby(gid).transform("mean").to_numpy()
    order_c = np.argsort(comp_year, kind="stable")
    fold = np.empty(n, int); fold[order_c] = (np.arange(n) * NOUTER) // n
    log("ERA folds: " + " · ".join(f"{int(np.nanmin(yr_row[fold==k]))}-{int(np.nanmax(yr_row[fold==k]))}" for k in range(NOUTER)))
if ERA_SPLIT:
    # EXTRAPOLATION, one direction only: the model never sees a groom born on or after the cutoff
    # and is scored only on those. This is the live page's situation for a modern couple.
    yr_row = pd.to_numeric(full.dob_a.astype(str).str.slice(0, 4), errors="coerce").to_numpy()
    fold = (yr_row >= ERA_SPLIT).astype(int)
    log(f"ERA SPLIT at {ERA_SPLIT}: train {(fold==0).sum():,} · test {(fold==1).sum():,}")
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)
vault = np.zeros(n, bool)
if VAULT:
    # THE VAULT (operator 2026-09-02, "ensure the model is not prone to overfitting"): one family in
    # ten is sealed away by a fixed seed before the search, the fold assignment, the inner CV or the
    # lambda sweep see anything. Every fit gives sealed rows weight zero; every outer test set
    # excludes them. The deploy model built on the other 90% is scored on the vault exactly once.
    vault = (np.random.default_rng(2026).integers(0, 10, gid.max() + 1)[gid] == 0)
    w = w * (~vault)
    fold = np.where(vault, -1, fold)
    log(f"VAULT: {vault.sum():,} couples sealed · {(~vault).sum():,} available")
yt = torch.from_numpy(y).to(DEV)
FAST = [b for b in ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"] if b != DROP_BODY]
INV = {b: torch.tensor([bod[m["i"]] == b or bod[m["j"]] == b for m in MET], device=DEV) for b in FAST}

def cols(ci):
    t = THETA[:, MET[ci]["a"]] * MET[ci]["k"]
    return torch.cos(t), torch.sin(t)

def design(sel):
    cc = []
    for c in sel:
        u, v = cols(c); cc += [u, v]
    return torch.stack(cc + [torch.ones(n, device=DEV)], 1)

def reg_vec(q, rl, sc, ksel):
    reg = np.full(q, rl * sc); reg[-1] = 0.0
    if HALPHA and ksel is not None:
        # SMOOTHNESS PRIOR: a high harmonic is a sharp, narrow-orb shape, and it is penalised more —
        # reg_k = rl * k^alpha, normalised so the mean penalty over the model's columns is unchanged.
        kk = np.array([float(k) for k in ksel for _ in (0, 1)] + [1.0]) ** HALPHA
        kk[:-1] *= (q - 1) / kk[:-1].sum()
        reg[:-1] *= kk[:-1]
    return reg

def newton_on(Amat, wm_t, rl, max_steps=40, ksel=None):
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
    reg = reg_vec(q, rl, sc, ksel)
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
        # 1e-5 relative was measured NOT ENOUGH on the 93,598-couple corpus: Newton stopped there
        # and Adam ground 3e-4 of AUC closer along a flat direction (weights 0.24 apart). Quadratic
        # convergence makes the extra decades of gradient collapse nearly free.
        if step >= 3 and gn < 1e-7 * g0: break
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

def score_all(r, vw, taken, mask=None, X=None):
    """X: the current design (selected columns + intercept). With AQ_ORTHO=1 each candidate column
    is projected onto the W-orthogonal complement of X before scoring, which turns the marginal
    2-df statistic into the EXACT score test for adding it to THIS model — a candidate that merely
    restates what the model already holds scores near zero instead of near its raw strength."""
    z = torch.empty(p, device=DEV)
    if ORTHO and X is not None:
        XW = X * vw.unsqueeze(1)
        G = (X.T @ XW).cpu().numpy().astype(np.float64)
        G[np.diag_indices_from(G)] += 1e-6 * float(np.mean(np.diag(G)))
        Ginv = torch.from_numpy(np.linalg.inv(G).astype(np.float32)).to(DEV)
    for lo in range(0, p, 1024):
        hi = min(p, lo + 1024); sl = slice(lo, hi)
        T = THETA[:, A_IDX[sl]] * K_VAL[sl].unsqueeze(0)
        C, S = torch.cos(T), torch.sin(T)
        if ORTHO and X is not None:
            C = C - X @ (Ginv @ (XW.T @ C)); S = S - X @ (Ginv @ (XW.T @ S))
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

GSIZE = len(HARM)
INV_ANG = {b: torch.tensor([bod[a[3]] == b or bod[a[4]] == b for a in ANG], device=DEV) for b in FAST}
def score_group(r, vw, taken_angles, mask=None, X=None):
    """the 2*GSIZE-degree-of-freedom score statistic for adding a WHOLE ANGLE — every harmonic's
    cosine and sine at once. z = g' S^-1 g with S ridge-stabilised; batched over angles."""
    nA = len(ANG); z = torch.full((nA,), -1.0, device=DEV)
    kv = torch.tensor([float(k) for k in HARM], device=DEV)
    if ORTHO and X is not None:
        XW = X * vw.unsqueeze(1)
        G = (X.T @ XW).cpu().numpy().astype(np.float64); G[np.diag_indices_from(G)] += 1e-6 * float(np.mean(np.diag(G)))
        Ginv = torch.from_numpy(np.linalg.inv(G).astype(np.float32)).to(DEV)
    for lo in range(0, nA, 8):
        hi = min(nA, lo + 8)
        T = THETA[:, lo:hi].unsqueeze(2) * kv                       # n x A x GSIZE
        Xc = torch.cat([torch.cos(T), torch.sin(T)], 2)              # n x A x 2G
        if ORTHO and X is not None:
            flat = Xc.reshape(n, -1)
            flat = flat - X @ (Ginv @ (XW.T @ flat)); Xc = flat.reshape(n, hi - lo, -1)
        g = torch.einsum("nai,n->ai", Xc, r).cpu().numpy().astype(np.float64)
        S = torch.einsum("nai,naj->aij", Xc, Xc * vw.unsqueeze(1).unsqueeze(2)).cpu().numpy().astype(np.float64)
        for a in range(hi - lo):
            Sa = S[a]; Sa[np.diag_indices_from(Sa)] += 1e-4 * float(np.trace(Sa)) / Sa.shape[0]
            try: z[lo + a] = float(g[a] @ np.linalg.solve(Sa, g[a]))
            except np.linalg.LinAlgError: z[lo + a] = -1.0
        del T, Xc
    if taken_angles: z[torch.tensor(taken_angles, dtype=torch.long, device=DEV)] = -1.0
    if mask is not None: z[~mask] = -1.0
    return z
def angle_phasors(a): return list(range(a * GSIZE, (a + 1) * GSIZE))

def inner_auc(sel, trm_np, ifold, nfold=5):
    """inner cross-validated AUC of a FIXED structure on the training rows only"""
    if not sel:
        return 0.5
    Amat = design(sel); oof = np.zeros(n, np.float32)
    for kf in range(nfold):
        tr = trm_np & (ifold != kf)
        wm_t = torch.from_numpy((w * tr).astype(np.float32)).to(DEV)
        beta = newton_on(Amat, wm_t, RL, ksel=[MET[c]["k"] for c in sel])
        v = (Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
        hold = trm_np & (ifold == kf); oof[hold] = v[hold]
    del Amat
    return float(roc_auc_score(y[trm_np], oof[trm_np]))

def stepwise(trm_np, kmax, seed=0):
    """greedy selection ORDER on the rows where trm_np is True.

    With AQ_VALIDATE=1 the greedy becomes VALIDATED (operator 2026-09-02: "if adding more reduces
    AUC there is overfitting; the worst case should be the same score"): the score test only
    SHORTLISTS candidates; each is then judged by an inner five-fold CV inside the training rows,
    the best one enters only if it improves that CV, and selection stops when none does. A
    candidate that merely won the in-sample lottery cannot get in, so a wider bank of duds costs
    nothing and a wider bank with signal still helps — the superset can no longer score lower
    except by CV noise."""
    ifold = np.random.default_rng(seed + 7).integers(0, 5, gid.max() + 1)[gid] if VALIDATE else None
    cur_auc = 0.5
    wm_t = torch.from_numpy((w * trm_np).astype(np.float32)).to(DEV)
    pr0 = float((y[trm_np] * w[trm_np]).sum() / w[trm_np].sum())
    eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
    sel = []; angles = []
    for k in range(kmax):
        pr = torch.sigmoid(eta)
        Xcur = design(sel) if (ORTHO and sel) else None
        if GROUP:
            a = int(torch.argmax(score_group(wm_t * (yt - pr), wm_t * pr * (1 - pr), angles, X=Xcur)).item())
            angles.append(a); sel += angle_phasors(a)
        elif VALIDATE:
            z = score_all(wm_t * (yt - pr), wm_t * pr * (1 - pr), sel, X=Xcur)
            short = [int(c) for c in torch.topk(z, SHORTLIST).indices.tolist()]
            cand = [(inner_auc(sel + [c], trm_np, ifold), c) for c in short]
            best_auc, best = max(cand)
            if best_auc <= cur_auc + VTOL:
                del Xcur; break              # nothing on the shortlist survives validation: stop
            sel.append(best); cur_auc = best_auc
        else:
            sel.append(int(torch.argmax(score_all(wm_t * (yt - pr), wm_t * pr * (1 - pr), sel, X=Xcur)).item()))
        del Xcur
        Amat = design(sel)
        beta = newton_on(Amat, wm_t, RL, ksel=[MET[c]["k"] for c in sel])
        eta = Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV)
        del Amat
    if SWAP and not GROUP:
        # ONE FORWARD-BACKWARD PASS: for each chosen phasor, refit without it and ask the exact
        # score test what it would pick in its place; swap if a different phasor scores higher
        # than the one being held. Greedy forward selection cannot revisit an early pick that a
        # later pick made redundant; this can.
        swapped = 0
        for pos in range(len(sel)):
            rest = sel[:pos] + sel[pos + 1:]
            Ar = design(rest)
            br = newton_on(Ar, wm_t, RL, ksel=[MET[c]["k"] for c in rest])
            pr = torch.sigmoid(Ar @ torch.from_numpy(br.astype(np.float32)).to(DEV))
            z = score_all(wm_t * (yt - pr), wm_t * pr * (1 - pr), rest, X=(Ar if ORTHO else None))
            best = int(torch.argmax(z).item())
            if best != sel[pos] and float(z[best]) > float(z[sel[pos]]) * 1.02:
                sel[pos] = best; swapped += 1
            del Ar
        log(f"      swap pass: {swapped} of {len(sel)} replaced")
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
        beta = newton_on(Amat, wm_t, RL, ksel=[MET[c]["k"] for c in sel])
        pr = torch.sigmoid(Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV))
        if GROUP:
            a = int(torch.argmax(score_group(wm_t * (yt - pr), wm_t * pr * (1 - pr),
                                             [c // GSIZE for c in sel[::GSIZE]], INV_ANG[b],
                                             X=(Amat if ORTHO else None))).item())
            sel += angle_phasors(a); forced.append((b, a * GSIZE))
        else:
            win = int(torch.argmax(score_all(wm_t * (yt - pr), wm_t * pr * (1 - pr), sel, INV[b],
                                             X=(Amat if ORTHO else None))).item())
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
        for K in range(GSIZE if GROUP else 1, len(order) + 1, GSIZE if GROUP else 1):
            sl = list(range(2 * K)) + [q - 1]
            beta = newton_on(Amat[:, sl], wm_t, RL, ksel=[MET[c]["k"] for c in order[:K]])
            v = (Amat[:, sl] @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
            hold = trm_np & (ifold == kf)
            oof[K - 1][hold] = v[hold]
    del Amat
    if DEV == "mps": torch.mps.empty_cache()
    inner = trm_np.copy()
    Ks = list(range(GSIZE if GROUP else 1, len(order) + 1, GSIZE if GROUP else 1))
    aucs = [float(roc_auc_score(y[inner], oof[K - 1][inner])) for K in Ks]
    return Ks[int(np.argmax(aucs))], aucs

# ---- the nested estimate ----------------------------------------------------------------------
oof_outer = np.zeros(n, np.float32)
per_fold = []
tested = np.zeros(n, bool)
for kf in ([1] if ERA_SPLIT else range(NOUTER)):
    trm = fold != kf
    tested |= ~trm
    order = stepwise(trm, KMAX, seed=1000 + kf)
    Kin, inner_aucs = (KMAX, []) if NO_INNER else pick_k(order, trm, seed=1000 + kf)
    sel, forced = force_fast(order[:Kin], trm)
    wm_t = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
    Amat = design(sel)
    beta = newton_on(Amat, wm_t, RL, ksel=[MET[c]["k"] for c in sel])
    v = (Amat @ torch.from_numpy(beta.astype(np.float32)).to(DEV)).cpu().numpy()
    oof_outer[~trm] = v[~trm]
    del Amat
    if DEV == "mps": torch.mps.empty_cache()
    fauc = float(roc_auc_score(y[~trm], v[~trm]))
    per_fold.append({"K_inner": Kin, "n_forced": len(forced), "fold_auc": round(fauc, 4),
                     "forced": [b for b, _ in forced]})
    log(f"   outer {kf+1}/{NOUTER} · K_inner {Kin} (+{len(forced)} forced: {','.join(b for b,_ in forced) or 'none'}) · fold AUC {fauc:.4f}")

auc_nested = float(roc_auc_score(y[tested & ~vault], oof_outer[tested & ~vault]))
# WITHIN-ERA AUC (operator 2026-09-02, "figure out the bottleneck"): the AUC inside each husband
# birth decade, weighted by couples. The calendar cannot help here — decade is held fixed — so
# this is what a feature earns beyond the era. It is the metric "more astrology" has to move.
_yr = pd.to_numeric(full.dob_a.astype(str).str.slice(0, 4), errors="coerce").to_numpy()
_dec = (_yr // 10 * 10); _m = tested & ~vault
_num = _den = 0.0
for _d in np.unique(_dec[_m]):
    _r = _m & (_dec == _d)
    if _r.sum() >= 200 and 0 < y[_r].sum() < _r.sum():
        _num += roc_auc_score(y[_r], oof_outer[_r]) * _r.sum(); _den += _r.sum()
auc_within_era = _num / _den if _den else float("nan")
log(f"WITHIN-ERA AUC (decade held fixed, couple-weighted): {auc_within_era:.4f}   [pooled nested {auc_nested:.4f}]")
log(f"NESTED AUC (selection + K + forced fast bodies ALL inside the loop): {auc_nested:.4f}  [{TAG}]")
np.save(f"{D_}/oof_nested_{TAG}.npy", oof_outer)
if ABLATE:
    json.dump({"tag": TAG, "nested_auc": round(auc_nested, 4), "within_era_auc": round(auc_within_era, 4), "per_fold": per_fold,
               "n_angles": len(ANG), "n_phasors": p, "harmonics": list(HARM), "bodies": bod},
              open(f"{D_}/ablate_{TAG}.json", "w"), indent=1)
    log(f"saved ablate_{TAG}.json"); raise SystemExit(0)

# ---- the deployed model: the same procedure, once, on all data --------------------------------
log("deploy pass on ALL data")
allr = ~vault
order = stepwise(allr, KMAX, seed=77)
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
        beta = newton_on(Amat, wm_t, rl, ksel=[MET[c]["k"] for c in sel])
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
beta_cf = newton_on(Amat, w_t, rl_star, ksel=[MET[c]["k"] for c in sel])
sc_all = (Amat @ torch.from_numpy(beta_cf.astype(np.float32)).to(DEV)).cpu().numpy()
auc_cf = float(roc_auc_score(y[allr], sc_all[allr]))
if VAULT:
    auc_vault = float(roc_auc_score(y[vault], sc_all[vault]))
    log(f"VAULT AUC (the sealed 10%, scored once by the model built on the other 90%): {auc_vault:.4f}  vs nested {auc_nested:.4f}")
# closed form vs gradient on the same penalised objective
sw0 = (w_t * 0.25).sqrt().unsqueeze(1)
sc = float(np.mean(np.diag(((Amat * sw0).T @ (Amat * sw0)).cpu().numpy())[:-1]))
bt = torch.zeros(q, device=DEV, requires_grad=True)
opt = torch.optim.Adam([bt], lr=0.05)
reg_t = torch.from_numpy(reg_vec(q, rl_star, sc, [MET[c]["k"] for c in sel]).astype(np.float32)).to(DEV)
for it in range(4000):
    opt.zero_grad()
    loss = (w_t * torch.nn.functional.binary_cross_entropy_with_logits(Amat @ bt, yt, reduction="none")).sum() \
           + 0.5 * (reg_t * bt * bt).sum()
    loss.backward(); opt.step()
auc_gd = float(roc_auc_score(y[allr], (Amat @ bt.detach()).cpu().numpy()[allr]))
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

json.dump({"nested_auc": round(auc_nested, 4), "within_era_auc": round(auc_within_era, 4), "per_fold": per_fold,
           "deploy": {"K": Kin, "n_forced": len(forced), "rl": rl_star,
                      "fixed_cv_reference": round(sw[rl_star], 4),
                      "closed_vs_gradient": {"auc_cf": round(auc_cf, 4), "auc_gd": round(auc_gd, 4),
                                             "max_wdiff": round(wdiff, 4)}},
           "rl_sweep": {str(k): round(v, 4) for k, v in sw.items()},
           "terms": terms, "bias": round(float(beta_cf[-1]), 4)},
          open(f"{D_}/report_nested_{TAG}.json", "w"), indent=1)
json.dump({"met": [{"kind": MET[c]["kind"], "i": MET[c]["i"], "j": MET[c]["j"], "k": MET[c]["k"],
                    "label": MET[c]["label"], "fam": MET[c]["fam"]} for c in sel],
           "rl": rl_star, "cv": round(auc_nested, 4),
           # THE BANK the model was chosen from — the page describes it from here, never from copy
           "bank": {"families": sorted({a[5] for a in ANG}), "harmonics": list(HARM),
                    "n_candidates": p, "systems": SYSTEMS, "ortho": ORTHO}},
          open(f"{D_}/maxout_terms_{TAG}.json", "w"), indent=1)
# KMAX-STAMPED FILENAMES. The K=64 run silently overwrote the K=32 artifacts under the shared
# names, so the exporter would have shipped the WORSE model (nested 0.6783 vs 0.6794) — the same
# two-runs-one-filename failure that once put a wrong number on the live page. The name now carries
# the run's identity, and the exporter names the file it ships from.
log(f"saved report_nested_{TAG}.json + maxout_terms_{TAG}.json")
