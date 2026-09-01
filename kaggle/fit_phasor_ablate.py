"""fit_phasor_ablate.py — keep only the informative terms (operator 2026-08-31).

LEVEL 1 — FAMILY ELIMINATION. Ten named k=1 families (the E4+E7+E8 union). Backward elimination:
each round refits without each remaining family; the family whose absence costs the least is
dropped if that cost is under TOL, and the loop stops when every remaining family is load-bearing.
Elimination runs on seed 7; the survivor set is confirmed on all three seeds.

    D   Mi - Wi     synastry, same body            X   Mi - Wj (i!=j)  cross-synastry grid
    NM  Mi          his natal positions            C   (Mi+Wi)-(Mj+Wj) composite aspects
    NW  Wi          her natal positions            MM  Mi + Mj         his natal midpoints
    S   Mi + Wi     couple midpoints               MW  Wi + Wj         her natal midpoints
    AM  Mi - Mj     his natal aspects              AW  Wi - Wj         her natal aspects

LEVEL 2 — PHASOR PRUNING, leakage-free. Inside the surviving basis, each fold ranks phasor pairs
by their fitted amplitude ON THAT FOLD'S TRAINING HALF, keeps the top m, refits, scores the fold's
test half. The reported curve over m never lets a test row influence its own selection. The final
model is the smallest m within TOL2 of the best, refitted on everything, printed as named phasors.
"""
import itertools, json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P
from closed_newton import newton_fold, RLAMS, DEV

D_ = os.path.expanduser(os.environ.get("AQ_TD_DIR", "~/.artamatch-dev/tilldeath"))
TOL, TOL2 = 0.0005, 0.0015
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
names = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, nm in enumerate(names) if nm != "true_south_node"]
bod = [names[i].replace("true_", "").replace("mean_", "") for i in keep]
ra, rb = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NB = len(bod)
C2 = list(itertools.combinations(range(NB), 2))
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
folds = {s: np.random.default_rng(s).integers(0, P.NFOLD, gid.max() + 1)[gid] for s in P.SEEDS}
w = np.where(y > 0, len(y) / (2 * y.sum()), len(y) / (2 * (len(y) - y.sum()))).astype(np.float32)
n = len(y)

def fam_angles(f):
    if f == "D":  return [(ra[:, i] - rb[:, i], f"D {bod[i]}") for i in range(NB)]
    if f == "NM": return [(ra[:, i], f"his {bod[i]}") for i in range(NB)]
    if f == "NW": return [(rb[:, i], f"her {bod[i]}") for i in range(NB)]
    if f == "S":  return [(ra[:, i] + rb[:, i], f"mid {bod[i]}") for i in range(NB)]
    if f == "AM": return [(ra[:, i] - ra[:, j], f"his {bod[i]}-{bod[j]}") for i, j in C2]
    if f == "AW": return [(rb[:, i] - rb[:, j], f"her {bod[i]}-{bod[j]}") for i, j in C2]
    if f == "X":  return [(ra[:, i] - rb[:, j], f"X his {bod[i]}-her {bod[j]}")
                          for i in range(NB) for j in range(NB) if i != j]
    if f == "C":  return [((ra[:, i] + rb[:, i]) - (ra[:, j] + rb[:, j]), f"comp {bod[i]}-{bod[j]}")
                          for i, j in C2]
    if f == "MM": return [(ra[:, i] + ra[:, j], f"his mid {bod[i]}/{bod[j]}") for i, j in C2]
    if f == "MW": return [(rb[:, i] + rb[:, j], f"her mid {bod[i]}/{bod[j]}") for i, j in C2]
    if f == "MP": return ([((ra[:, i] + rb[:, i]) - 2 * ra[:, j], f"cmid {bod[i]} to his {bod[j]}")
                           for i in range(NB) for j in range(NB)] +
                          [((ra[:, i] + rb[:, i]) - 2 * rb[:, j], f"cmid {bod[i]} to her {bod[j]}")
                           for i in range(NB) for j in range(NB)])
    if f == "OO": return ([((ra[:, i] + ra[:, j]) - 2 * ra[:, k], f"his mid {bod[i]}/{bod[j]} to his {bod[k]}")
                           for i, j in C2 for k in range(NB) if k not in (i, j)] +
                          [((rb[:, i] + rb[:, j]) - 2 * rb[:, k], f"her mid {bod[i]}/{bod[j]} to her {bod[k]}")
                           for i, j in C2 for k in range(NB) if k not in (i, j)])
    if f == "PP": return ([((ra[:, i] + ra[:, j]) - 2 * rb[:, k], f"his mid {bod[i]}/{bod[j]} to her {bod[k]}")
                           for i, j in C2 for k in range(NB)] +
                          [((rb[:, i] + rb[:, j]) - 2 * ra[:, k], f"her mid {bod[i]}/{bod[j]} to his {bod[k]}")
                           for i, j in C2 for k in range(NB)])
    if f == "LL": return ([(ra[:, i] + ra[:, j] - ra[:, k], f"his lot {bod[i]}+{bod[j]}-{bod[k]}")
                           for i, j in C2 for k in range(NB) if k not in (i, j)] +
                          [(rb[:, i] + rb[:, j] - rb[:, k], f"her lot {bod[i]}+{bod[j]}-{bod[k]}")
                           for i, j in C2 for k in range(NB) if k not in (i, j)])

_e9 = {}
_p9 = os.path.expanduser("~/.artamatch-dev/tilldeath/report_e9.json")
if os.path.exists(_p9):
    _e9 = json.load(open(_p9))
FAMS = ("D", "NM", "NW", "S", "AM", "AW", "X", "C", "MM", "MW") + tuple(_e9.get("_admitted", []))

def design(fams):
    angs, nms = [], []
    for f in fams:
        for a, nm in fam_angles(f):
            angs.append(a); nms.append(nm)
    A = np.stack(angs, 1)
    F = np.empty((n, 2 * len(angs) + 1), np.float32)
    F[:, 0:2*len(angs):2] = np.cos(A); F[:, 1:2*len(angs):2] = np.sin(A)
    F[:, -1] = 1.0
    return F, nms

def cv7(F, rlams=RLAMS, seeds=(7,)):
    Ft = torch.from_numpy(F).to(DEV)
    out = {}
    for s in seeds:
        fold = folds[s]
        oof = {rl: np.zeros(n, np.float32) for rl in rlams}
        dead = set()
        for k in range(P.NFOLD):
            res = newton_fold(Ft, y, w, fold != k, rlams)
            for rl in rlams:
                if res[rl] is None: dead.add(rl)
                else: oof[rl][fold == k] = res[rl][fold == k]
        out[s] = {rl: (roc_auc_score(y, oof[rl]) if rl not in dead else 0.0) for rl in rlams}
    del Ft
    if DEV == "mps": torch.mps.empty_cache()
    return out

# ---- LEVEL 1: backward elimination
alive = list(FAMS)
F, _ = design(alive)
cur = cv7(F)[7]; cur_auc = max(cur.values())
log(f"full union {F.shape[1]} params: {cur_auc:.4f}")
path = [{"fams": list(alive), "auc": float(cur_auc)}]
while len(alive) > 1:
    trials = []
    for f in alive:
        rest = [g for g in alive if g != f]
        Fr, _ = design(rest)
        a = max(cv7(Fr)[7].values())
        trials.append((a, f))
        log(f"   - without {f:<3} {a:.4f}  (drop cost {cur_auc - a:+.4f})")
    a_best, f_drop = max(trials)
    if a_best >= cur_auc - TOL:
        alive.remove(f_drop)
        cur_auc = a_best
        log(f"DROP {f_drop} -> {alive} @ {cur_auc:.4f}")
        path.append({"fams": list(alive), "auc": float(a_best)})
    else:
        log(f"STOP: every remaining family is load-bearing {alive}")
        break

# FORWARD RE-ENTRY: a family dropped early may earn its place back in the smaller company
for f in [f for f in FAMS if f not in alive]:
    Fr, _ = design(alive + [f])
    a = max(cv7(Fr)[7].values())
    if a > cur_auc + TOL:
        alive.append(f); cur_auc = a
        log(f"RE-ENTER {f} -> {alive} @ {a:.4f}")

F, nms = design(alive)
conf = cv7(F, seeds=P.SEEDS)
best_rl = max(conf[7], key=conf[7].get)
mean3 = float(np.mean([conf[s][best_rl] for s in P.SEEDS]))
log(f"SURVIVORS {alive}: {F.shape[1]} params · 3-seed mean {mean3:.4f} @rl {best_rl:g}")

# ---- LEVEL 2: within-fold pruning of individual TERMS (each sin or cos column on its own,
# so an angle whose effect is symmetric keeps cos and sheds sin)
npair = (F.shape[1] - 1) // 2
nterm = 2 * npair
MS = [m for m in (8, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, nterm) if m <= nterm]
Ft = torch.from_numpy(F).to(DEV)
fold = folds[7]
curves = {m: np.zeros(n, np.float32) for m in MS}
for k in range(P.NFOLD):
    trm = fold != k
    res = newton_fold(Ft, y, w, trm, (best_rl,))
    # amplitudes come from a fold-train refit: run one more newton on train to get beta
    # (newton_fold returns scores; refit here directly for beta via small closed solve)
    # build fold beta by solving on the fold train with the same machinery:
    from closed_newton import _wgram, _wmatvec, _solve
    wm = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
    G0 = _wgram(Ft, wm)
    scale = float(np.mean(np.diag(G0)[:-1]))
    reg = np.full(F.shape[1], best_rl * scale); reg[-1] = 0.0
    beta = np.zeros(F.shape[1])
    yt = torch.from_numpy(y).to(DEV)
    for step in range(3):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        z = Ft @ bt; pr = torch.sigmoid(z)
        gv = _wmatvec(Ft, wm * (yt - pr)) - reg * beta
        H = 0.25 * G0.copy() if step == 0 else _wgram(Ft, wm * pr * (1 - pr))
        H[np.diag_indices_from(H)] += reg
        beta = beta + _solve(H, gv, scale)
    mag = np.abs(beta[:nterm])
    order = np.argsort(-mag)
    for m in MS:
        sel = np.sort(np.r_[order[:m], [nterm]])
        Fm = np.ascontiguousarray(F[:, sel])
        Fmt = torch.from_numpy(Fm).to(DEV)
        r2 = newton_fold(Fmt, y, w, trm, (best_rl,))
        curves[m][fold == k] = r2[best_rl][fold == k]
        del Fmt
log("pruning curve (seed 7):")
prune = {m: float(roc_auc_score(y, curves[m])) for m in MS}
for m in MS:
    log(f"   top {m:>4} terms: {prune[m]:.4f}")
best_m = min([m for m in MS if prune[m] >= max(prune.values()) - TOL2])
log(f"MINIMAL model: {best_m} sin/cos terms within {TOL2} of the best ({max(prune.values()):.4f})")

# final full-data fit at best_m for the named table
from closed_newton import _wgram, _wmatvec, _solve
wm = torch.from_numpy(w).to(DEV)
G0 = _wgram(Ft, wm)
scale = float(np.mean(np.diag(G0)[:-1]))
reg = np.full(F.shape[1], best_rl * scale); reg[-1] = 0.0
beta = np.zeros(F.shape[1])
yt = torch.from_numpy(y).to(DEV)
for step in range(3):
    bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
    z = Ft @ bt; pr = torch.sigmoid(z)
    gv = _wmatvec(Ft, wm * (yt - pr)) - reg * beta
    H = 0.25 * G0.copy() if step == 0 else _wgram(Ft, wm * pr * (1 - pr))
    H[np.diag_indices_from(H)] += reg
    beta = beta + _solve(H, gv, scale)
mag = np.abs(beta[:nterm])
order = np.argsort(-mag)[:best_m]
tname = lambda j: f"{'cos' if j % 2 == 0 else 'sin'}({nms[j // 2]})"
log(f"\nTHE MODEL — {best_m} named sin/cos terms (full-data fit, signed weights):")
for r, j in enumerate(order, 1):
    log(f"   {r:>3}. {tname(j):<34} w {beta[j]:+.4f}")
json.dump({"survivor_families": alive, "elimination_path": path,
           "confirmed_mean_3seeds": mean3, "rel_lambda": best_rl,
           "pruning_curve": {str(m): prune[m] for m in MS}, "minimal_m": int(best_m),
           "terms": [{"term": tname(j), "w": float(beta[j])} for j in order]},
          open(f"{D_}/report_ablation.json", "w"), indent=1)
log("saved report_ablation.json")
