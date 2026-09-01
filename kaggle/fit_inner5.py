"""fit_inner.py — THE FAST BODIES ONLY, differences AND midpoints. The decisive test.

Every model in this project has ended up leaning on slow bodies: Neptune-Pluto, Uranus-Pluto,
node-Lilith. Those angles move over centuries, so a model built from them can read WHEN someone was
born, and birth era is exactly what a corpus of documented marriages is stratified by. The body
ablation made it plain — Sun, Moon, Mercury, Venus, Mars and Jupiter each cost ZERO to remove.

This turns that around and keeps only the fast bodies:

    Sun · Moon · Mercury · Venus · Mars · Jupiter · Saturn

Venus returns to the same place in 225 days, the Moon in 27, and even Saturn in 29 years — against
the 492 years of the Neptune-Pluto pair that every earlier model leaned on. No combination of these
can encode a century. If a model built only from these predicts the target, the signal is not a clock. If it
collapses to chance, the earlier AUCs were the calendar and should be reported as such.

BOTH DIFFERENCES AND MIDPOINTS, within and across the two charts:

    XY-   M[i] - W[j]   all i,j      XY+   M[i] + W[j]   all i,j
    XX-   M[i] - M[j]   i < j        XX+   M[i] + M[j]   i < j
    YY-   W[i] - W[j]   i < j        YY+   W[i] + W[j]   i < j

90 angles x 13 harmonics = 1,170 phasors, each contributing a cos and a sin.

FULL-PRECISION DATES ONLY. Fast bodies are the whole point here and a year-only birth date puts the
Moon anywhere in the zodiac, so the imputed rows would be noise wearing the model's own clothes.
"""
import itertools, json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from collections import Counter
import fit_phasor_torch as P
from closed_newton import _solve, DEV

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_max"))
KMAX = int(os.environ.get("AQ_KMAX", "24"))
RL = float(os.environ.get("AQ_RL", "0.003"))
# The FAST bodies, per the operator: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn. Saturn's
# 29-year cycle is the slowest admitted and still an order of magnitude faster than the Neptune-Pluto
# pair (492 years) that every earlier model leaned on, so no combination of these can encode a
# century. Worth knowing while reading the result: the Sun's angle over a year IS the calendar date,
# so his-Sun-minus-her-Sun is the day-of-year gap between the two births — a real cross-chart
# quantity, and one that says nothing about which century either was born in.
INNER = ("sun", "moon", "mercury", "venus", "mars")
HARM = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 27, 36)
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

full = pd.read_csv(f"{D_}/full.csv")
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm_all = [str(b) for b, o in zip(Z["bodies"], okb) if o]
sel_b = [i for i, x in enumerate(nm_all)
         if x.replace("true_", "").replace("mean_", "") in INNER]
bod = [nm_all[i] for i in sel_b]
RA, RB = np.deg2rad(tha[:, okb][:, sel_b]), np.deg2rad(thb[:, okb][:, sel_b])

# full-precision rows only
if "fullprec" in full.columns:
    m = full.fullprec.astype(int) == 1
else:
    m = ~(full.dob_a.astype(str).str.contains("-00") | full.dob_b.astype(str).str.contains("-00"))
m = m.to_numpy()
y = full.y.to_numpy().astype(np.float32)[m]
RA, RB = RA[m], RB[m]
ids = pd.read_csv(f"{D_}/_train_ids.csv", dtype=str)[m]
n = len(y)
NB = len(bod); C2 = list(itertools.combinations(range(NB), 2))
log(f"{n:,} full-precision couples of {len(m):,} · y=1 {int(y.sum()):,} ({y.mean():.2%})")
log(f"bodies: {bod}")

ANG = []
for i in range(NB):
    for j in range(NB):
        ANG.append((RA[:, i] - RB[:, j], f"his {bod[i]} - her {bod[j]}", "xdiff", i, j, "XY-"))
        ANG.append((RA[:, i] + RB[:, j], f"his {bod[i]} + her {bod[j]}", "xsum", i, j, "XY+"))
for i, j in C2:
    ANG.append((RA[:, i] - RA[:, j], f"his {bod[i]} - his {bod[j]}", "aspM", i, j, "XX-"))
    ANG.append((RA[:, i] + RA[:, j], f"his {bod[i]} + his {bod[j]}", "midM", i, j, "XX+"))
    ANG.append((RB[:, i] - RB[:, j], f"her {bod[i]} - her {bod[j]}", "aspW", i, j, "YY-"))
    ANG.append((RB[:, i] + RB[:, j], f"her {bod[i]} + her {bod[j]}", "midW", i, j, "YY+"))
MET = [{"a": a, "k": k, "kind": kd, "i": i, "j": j, "fam": f,
        "label": (f"{k}*({nm})" if k > 1 else nm)}
       for a, (_, nm, kd, i, j, f) in enumerate(ANG) for k in HARM]
THETA = torch.from_numpy(np.column_stack([a[0].astype(np.float32) for a in ANG])).to(DEV)
p = len(MET)
log(f"{len(ANG)} angles x {len(HARM)} harmonics = {p:,} phasors "
    f"({dict(Counter(a[5] for a in ANG))})")
A_IDX = torch.tensor([m_["a"] for m_ in MET], device=DEV)
K_VAL = torch.tensor([float(m_["k"]) for m_ in MET], device=DEV)

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

def fit(sel, wm):
    cc = []
    for c in sel:
        t = THETA[:, MET[c]["a"]] * MET[c]["k"]; cc += [torch.cos(t), torch.sin(t)]
    A = torch.stack(cc + [torch.ones(n, device=DEV)], 1)
    beta = np.zeros(A.shape[1])
    for step in range(3):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        pr = torch.sigmoid(A @ bt)
        g = (A.T @ (wm * (yt - pr))).cpu().numpy().astype(np.float64)
        sw = (wm * (0.25 if step == 0 else pr * (1 - pr))).sqrt().unsqueeze(1)
        H = ((A * sw).T @ (A * sw)).cpu().numpy().astype(np.float64)
        sc = float(np.mean(np.diag(H)[:-1])) or 1.0
        reg = np.full(A.shape[1], RL * sc); reg[-1] = 0.0
        H[np.diag_indices_from(H)] += reg
        beta = beta + _solve(H, g - reg * beta, sc)
    out = A @ torch.from_numpy(beta.astype(np.float32)).to(DEV)
    del A
    return out

oof = np.zeros((KMAX + 1, n), np.float32); picks = []
for kf in range(P.NFOLD):
    trm = fold != kf
    wm = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
    pr0 = float((y[trm] * w[trm]).sum() / w[trm].sum())
    eta = torch.full((n,), float(np.log(pr0 / (1 - pr0))), device=DEV)
    oof[0][fold == kf] = eta.cpu().numpy()[fold == kf]
    sel = []
    for k in range(1, KMAX + 1):
        pr = torch.sigmoid(eta); r = wm * (yt - pr); vw = wm * pr * (1 - pr)
        z = torch.empty(p, device=DEV)
        for lo in range(0, p, 1024):
            hi = min(p, lo + 1024); sl = slice(lo, hi)
            T = THETA[:, A_IDX[sl]] * K_VAL[sl].unsqueeze(0)
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
        eta = fit(sel, wm)
        oof[k][fold == kf] = eta.cpu().numpy()[fold == kf]
    picks.append(sel)
    log(f"   fold {kf+1}/10 · {dict(Counter(MET[j]['fam'] for j in sel))}")

aucs = {k: float(roc_auc_score(y, oof[k])) for k in range(1, KMAX + 1)}
log("\nTHE FRONTIER — inner planets only, full-precision dates")
for k in range(1, KMAX + 1):
    log(f"   {k:>3} phasors ({2*k+1:>3} weights)   {aucs[k]:.4f}")
bk = max(aucs, key=aucs.get)
log(f"\n   best {aucs[bk]:.4f} at {bk} phasors")
freq = Counter(j for sp in picks for j in sp)
log("   most agreed:")
for j, c in freq.most_common(12):
    log(f"     {c:>2}/10  {MET[j]['fam']:<4} {MET[j]['label']}")
log(f"   family share: {dict(Counter(MET[j]['fam'] for sp in picks for j in sp))}")
log(f"   harmonic share: {dict(sorted(Counter(MET[j]['k'] for sp in picks for j in sp).items()))}")
json.dump({"inner": list(INNER), "n": n, "auc_by_k": aucs, "best": aucs[bk], "best_k": bk,
           "family_share": {k: v for k, v in Counter(MET[j]["fam"] for sp in picks for j in sp).items()},
           "frequency": [{"folds": c, **{q: MET[j][q] for q in ("fam", "label", "k", "kind", "i", "j")}}
                         for j, c in freq.most_common(40)]},
          open(f"{D_}/report_inner.json", "w"), indent=1)
log("saved report_inner.json")
