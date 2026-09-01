"""fit_ultimate.py — the maximal sidereal angular space, and the fewest terms that capture it.

Operator 2026-09-01: truly max out the model with any sidereal term possible; every feature angular,
no one-hots; his and her natal placements and aspects readmitted.

EVERY FEATURE IS cos(k*theta) OR sin(k*theta) for a named angle theta and an integer harmonic k.
That single form covers the whole tradition without a single indicator column:

  k=1   the aspect itself          k=6   sextile family        k=27  nakshatra (13 deg 20')
  k=2   opposition/polarity        k=9   novile               k=36  decan (10 deg)
  k=3   trine, and the elements    k=12  THE SIGNS (30 deg)
  k=4   square, and the modes

A sign is a 30-degree bin, so its angular expression is the 12th harmonic — which is why no one-hot
is needed and none is used. Nakshatra and decan structure arrive the same way, at k=27 and k=36.

FOURTEEN NAMED ANGLE FAMILIES over 13 sidereal bodies (Lahiri, noon UT). With d_i = M[i]-W[i] and
s_i = M[i]+W[i]:

  pair, needing both charts        D d_i · S s_i · X M[i]-W[j] · XM M[i]+W[j]
                                  DD+/- d_i +/- d_j · SS+/- s_i +/- s_j · DS+/- d_i +/- s_j
  one chart                       NM M[i] · NW W[i] · AM M[i]-M[j] · AW W[i]-W[j]

1,144 base angles. Harmonics are spent where they can be afforded: the small families get k up to
36, the largest get k up to 4, giving 12,064 candidate terms.

MEMORY. 12,064 columns over 175,155 rows would be 8 GB materialised, so the base angles are stored
once (800 MB) and every cos/sin is generated in blocks on the way through the scoring pass. Only the
selected columns are ever held as a design.

SELECTION IS INSIDE EACH FOLD. Forward stepwise on the score statistic
z_j = |X_j' W (y-p)| / sqrt(X_j' W X_j), refitting by the closed-form three-step Newton each time,
using training rows only. The AUC at each k is therefore what a stranger reproduces; ranking 12,064
terms on all the data first would leak the answer into the selection.
"""
import itertools, json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P
from closed_newton import _solve, DEV

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
KMAX = int(os.environ.get("AQ_KMAX", "48"))
RL = float(os.environ.get("AQ_RL", "0.003"))
TOL = 0.0010
BLK = int(os.environ.get("AQ_BLK", "64"))     # angles per scoring block
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

d = lambda i: RA[:, i] - RB[:, i]
s = lambda i: RA[:, i] + RB[:, i]
FAM = {
 # SAME-BODY, kept as its own family ONLY for the harmonics X/XM do not carry (see HARM below), so
 # no angle-and-harmonic pair exists twice. i==j itself now lives inside X and XM.
 "D":   [(d(i), f"D {bod[i]}", "diff", i, None) for i in range(NB)],
 "S":   [(s(i), f"mid {bod[i]}", "sum", i, None) for i in range(NB)],
 "NM":  [(RA[:, i], f"his {bod[i]}", "natM", i, None) for i in range(NB)],
 "NW":  [(RB[:, i], f"her {bod[i]}", "natW", i, None) for i in range(NB)],
 "DD-": [(d(i) - d(j), f"D {bod[i]} vs D {bod[j]}", "ddm", i, j) for i, j in C2],
 "DD+": [(d(i) + d(j), f"D {bod[i]} with D {bod[j]}", "ddp", i, j) for i, j in C2],
 "SS-": [(s(i) - s(j), f"comp {bod[i]}-{bod[j]}", "camp", i, j) for i, j in C2],
 "SS+": [(s(i) + s(j), f"comp {bod[i]} with {bod[j]}", "ssp", i, j) for i, j in C2],
 "AM":  [(RA[:, i] - RA[:, j], f"his {bod[i]}-{bod[j]}", "aspM", i, j) for i, j in C2],
 "AW":  [(RB[:, i] - RB[:, j], f"her {bod[i]}-{bod[j]}", "aspW", i, j) for i, j in C2],
 # THE FULL GRID, i==j INCLUDED (operator 2026-09-01): every one of his bodies against every one of
 # hers, the same-body case among them rather than partitioned away from it.
 "X":   [(RA[:, i] - RB[:, j], f"his {bod[i]}-her {bod[j]}", "xdiff", i, j)
         for i in range(NB) for j in range(NB)],
 "XM":  [(RA[:, i] + RB[:, j], f"mid his {bod[i]}/her {bod[j]}", "xsum", i, j)
         for i in range(NB) for j in range(NB)],
 "DS-": [(d(i) - s(j), f"D {bod[i]} vs comp {bod[j]}", "dsm", i, j)
         for i in range(NB) for j in range(NB) if i != j],
 "DS+": [(d(i) + s(j), f"D {bod[i]} with comp {bod[j]}", "dsp", i, j)
         for i in range(NB) for j in range(NB) if i != j],
}
# HARMONICS, ASSIGNED SO THAT NOTHING IS DUPLICATED. X and XM cover the whole (i,j) grid at k=1..4,
# same-body included; D and S are the same-body angles and therefore carry ONLY the higher harmonics,
# which is where the sign (k=12), nakshatra (k=27) and decan (k=36) structure lives. NM/NW get the
# full ladder because a placement's sign is the most-cited fact in the tradition.
HARM = {"D": (5, 6, 7, 8, 9, 10, 12, 27, 36),
        "S": (5, 6, 7, 8, 9, 10, 12, 27, 36),
        "NM": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 27, 36),
        "NW": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 27, 36),
        **{f: (1, 2, 3, 4, 6, 12) for f in ("DD-", "DD+", "SS-", "SS+", "AM", "AW")},
        **{f: (1, 2, 3, 4) for f in ("X", "XM", "DS-", "DS+")}}
PAIRF = {"D", "S", "X", "XM", "DD-", "DD+", "SS-", "SS+", "DS-", "DS+"}

TH, MET = [], []          # base angles, and the (angle, k, trig) candidate list
for f, items in FAM.items():
    for ang, name, kind, i, j in items:
        TH.append(ang.astype(np.float32))
        for k in HARM[f]:
            for tg in ("cos", "sin"):
                MET.append({"a": len(TH) - 1, "k": k, "trig": tg, "fam": f, "kind": kind,
                            "i": i, "j": j, "label": f"{tg}({k}*{name})" if k > 1 else f"{tg}({name})"})
# NO CANDIDATE MAY APPEAR TWICE. Merging i==j into X and XM makes D and S subsets of them at shared
# harmonics, which would put exactly collinear columns in the design; the harmonic split above avoids
# it, and this proves the split rather than trusting it. Keyed on the angle's VALUES, so two
# differently-named families that happen to compute the same angle are caught too.
_sig = {}
for _ix, _m in enumerate(MET):
    _k = (round(float(TH[_m["a"]][0]), 6), round(float(TH[_m["a"]][7]), 6),
          round(float(TH[_m["a"]][1234]), 6), _m["k"], _m["trig"])
    if _k in _sig:
        raise AssertionError(f"duplicate candidate: {_m['label']} ({_m['fam']}) == "
                             f"{MET[_sig[_k]]['label']} ({MET[_sig[_k]]['fam']})")
    _sig[_k] = _ix
log(f"uniqueness proven: {len(MET):,} candidates, no two the same angle at the same harmonic")
THETA = torch.from_numpy(np.column_stack(TH)).to(DEV)
NA, p = THETA.shape[1], len(MET)
del TH
log(f"{NA:,} base angles · {p:,} candidate terms · angles held as {THETA.element_size()*THETA.nelement()/2**30:.2f} GB")
from collections import Counter
log("   " + " · ".join(f"{k}:{v}" for k, v in Counter(m["fam"] for m in MET).items()))

# candidate index -> (angle col, harmonic, is_sin) as tensors, for block scoring
A_IDX = torch.tensor([m["a"] for m in MET], device=DEV)
K_VAL = torch.tensor([float(m["k"]) for m in MET], device=DEV)
IS_SIN = torch.tensor([1.0 if m["trig"] == "sin" else 0.0 for m in MET], device=DEV)

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

def col(ci):
    """materialise one candidate column exactly"""
    m = MET[ci]
    t = THETA[:, m["a"]] * m["k"]
    return torch.sin(t) if m["trig"] == "sin" else torch.cos(t)

def score_all(r, vw, taken):
    """z_j for every candidate, generated in blocks — nothing is materialised whole"""
    z = torch.empty(p, device=DEV)
    for lo in range(0, p, BLK * 26):
        hi = min(p, lo + BLK * 26)
        idx = slice(lo, hi)
        T = THETA[:, A_IDX[idx]] * K_VAL[idx].unsqueeze(0)
        Cm = torch.where(IS_SIN[idx].unsqueeze(0).bool(), torch.sin(T), torch.cos(T))
        num = Cm.T @ r
        den = (Cm * Cm * vw.unsqueeze(1)).sum(0)
        z[idx] = num.abs() / (den.sqrt() + 1e-9)
        del T, Cm
    if taken:
        z[torch.tensor(taken, dtype=torch.long, device=DEV)] = -1.0
    return z

def fit_subset(sel, wm_t):
    A = torch.stack([col(c) for c in sel] + [torch.ones(n, device=DEV)], 1)
    q = A.shape[1]
    beta = np.zeros(q)
    for step in range(3):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        pr = torch.sigmoid(A @ bt)
        g = (A.T @ (wm_t * (yt - pr))).cpu().numpy().astype(np.float64)
        vv = wm_t * (0.25 if step == 0 else pr * (1 - pr))
        sw = vv.sqrt().unsqueeze(1)
        H = ((A * sw).T @ (A * sw)).cpu().numpy().astype(np.float64)
        sc = float(np.mean(np.diag(H)[:-1])) or 1.0
        reg = np.full(q, RL * sc); reg[-1] = 0.0
        H[np.diag_indices_from(H)] += reg
        beta = beta + _solve(H, g - reg * beta, sc)
    bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
    out = A @ bt
    del A
    return out, beta

oof = np.zeros((KMAX + 1, n), np.float32)
picks = []
for kf in range(P.NFOLD):
    trm = fold != kf
    wm_t = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
    pr0 = float((y[trm] * w[trm]).sum() / w[trm].sum())
    eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
    oof[0][fold == kf] = eta.cpu().numpy()[fold == kf]
    sel = []
    for k in range(1, KMAX + 1):
        pr = torch.sigmoid(eta)
        z = score_all(wm_t * (yt - pr), wm_t * pr * (1 - pr), sel)
        sel.append(int(torch.argmax(z).item()))
        eta, beta = fit_subset(sel, wm_t)
        oof[k][fold == kf] = eta.cpu().numpy()[fold == kf]
    picks.append(sel)
    npair = sum(1 for j in sel if MET[j]["fam"] in PAIRF)
    log(f"   fold {kf+1}/{P.NFOLD}: {KMAX} terms · {npair} pair / {KMAX-npair} one-chart")

aucs = {k: float(roc_auc_score(y, oof[k])) for k in range(1, KMAX + 1)}
log("\nTHE FRONTIER — out-of-fold AUC, selection inside each fold")
for k in range(1, KMAX + 1):
    log(f"   {k:>3} terms   {aucs[k]:.4f}")
best_k = max(aucs, key=aucs.get); best = aucs[best_k]
knee = min(k for k in aucs if aucs[k] >= best - TOL)
bl = json.load(open(f"{D_}/report_baselines_max.json"))
BAR = max(bl["him_only"], bl["her_only"])
log(f"\n   best {best:.4f} at {best_k} terms · KNEE {knee} terms ({aucs[knee]:.4f})")
log(f"   one chart alone {BAR:.4f}  ->  {best - BAR:+.4f}")
freq = Counter(j for sp in picks for j in sp)
log("\n   the terms the folds agree on:")
for j, c in freq.most_common(22):
    log(f"     {c:>2}/10  {MET[j]['fam']:<4} {MET[j]['label']}")
json.dump({"rl": RL, "kmax": KMAX, "auc_by_k": aucs, "best": best, "best_k": best_k,
           "knee": knee, "knee_auc": aucs[knee], "baselines": bl,
           "lift_over_best_solo": best - BAR, "n_candidates": p, "n_angles": NA,
           "harmonics": {k: list(v) for k, v in HARM.items()},
           "frequency": [{"folds": c, "fam": MET[j]["fam"], "label": MET[j]["label"],
                          **{kk: MET[j][kk] for kk in ("k", "trig", "kind", "i", "j")}}
                         for j, c in freq.most_common(80)],
           "fold_picks": [[{"fam": MET[j]["fam"], "label": MET[j]["label"]} for j in sp]
                          for sp in picks]},
          open(f"{D_}/report_ultimate.json", "w"), indent=1)
log("saved report_ultimate.json")
