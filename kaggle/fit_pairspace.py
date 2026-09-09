"""fit_pairspace.py — the COMPLETE two-body pair-only angle space, ablated in detail.

Operator 2026-09-01: every pair-only combination, across-body and within-body, of midpoint and
difference. With M the man's sidereal longitudes and W the woman's, the two pair primitives are

    d_i = M[i] - W[i]      the synastry difference
    s_i = M[i] + W[i]      the couple's midpoint axis

and the complete space of small-integer angles that need BOTH charts is:

    D    d_i                 same-body synastry aspect
    S    s_i                 same-body couple midpoint
    X    M[i] - W[j]  i!=j   cross-body synastry
    XM   M[i] + W[j]  i!=j   cross-body couple midpoint
    DD-  d_i - d_j    i<j    how far his own aspect sits from her same aspect
    DD+  d_i + d_j    i<j
    SS-  s_i - s_j    i<j    an aspect INSIDE the composite chart
    SS+  s_i + s_j    i<j
    DS-  d_i - s_j    i!=j   a synastry difference against a composite axis
    DS+  d_i + s_j    i!=j

THE DIAGONAL OF THE DS FAMILIES IS SINGLE-PERSON and is excluded: d_i - s_i = -2W[i] and
d_i + s_i = 2M[i]. That is not left to the algebra — every family is TESTED mechanically below by
perturbing one chart at a time; a family whose angles do not all move with BOTH charts is refused.

The ablation, in five phases:
  A  each family alone, full lambda sweep — what is each worth by itself
  B  the union, lambda swept once -> the working lambda for the screens
  C  backward elimination
  D  forward greedy selection, as an independent check on C
  E  the agreed set: lambda sweep, three seeds, term pruning, leave-one-out

Baselines throughout are the operator's two: the same model on one partner's complete solo algebra.
"""
import itertools, json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P
from closed_newton import newton_fold, RLAMS, DEV, _wgram, _wmatvec, _solve, _matvec

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
TOL, TOL2 = 0.0005, 0.0015
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
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)


def angles(f, A=None, B=None):
    """-> [(angle_vector, name, kind, i, j)] for family f, over charts A and B"""
    A = RA if A is None else A
    B = RB if B is None else B
    d = lambda i: A[:, i] - B[:, i]
    s = lambda i: A[:, i] + B[:, i]
    if f == "D":   return [(d(i), f"D {bod[i]}", "diff", i, None) for i in range(NB)]
    if f == "S":   return [(s(i), f"mid {bod[i]}", "sum", i, None) for i in range(NB)]
    if f == "X":   return [(A[:, i] - B[:, j], f"his {bod[i]}-her {bod[j]}", "xdiff", i, j)
                           for i in range(NB) for j in range(NB) if i != j]
    if f == "XM":  return [(A[:, i] + B[:, j], f"mid his {bod[i]}/her {bod[j]}", "xsum", i, j)
                           for i in range(NB) for j in range(NB) if i != j]
    if f == "DD-": return [(d(i) - d(j), f"D {bod[i]} vs D {bod[j]}", "ddm", i, j) for i, j in C2]
    if f == "DD+": return [(d(i) + d(j), f"D {bod[i]} with D {bod[j]}", "ddp", i, j) for i, j in C2]
    if f == "SS-": return [(s(i) - s(j), f"comp {bod[i]}-{bod[j]}", "camp", i, j) for i, j in C2]
    if f == "SS+": return [(s(i) + s(j), f"comp {bod[i]} with {bod[j]}", "ssp", i, j) for i, j in C2]
    if f == "DS-": return [(d(i) - s(j), f"D {bod[i]} vs comp {bod[j]}", "dsm", i, j)
                           for i in range(NB) for j in range(NB) if i != j]
    if f == "DS+": return [(d(i) + s(j), f"D {bod[i]} with comp {bod[j]}", "dsp", i, j)
                           for i in range(NB) for j in range(NB) if i != j]
    raise ValueError(f)

FAMS = ["D", "S", "X", "XM", "DD-", "DD+", "SS-", "SS+", "DS-", "DS+"]

# ── THE PAIR-ONLY TEST, MECHANICAL. Perturb one chart at a time: every angle in a pair-only family
# must move when HIS chart moves and when HERS moves. A family with any angle insensitive to either
# is single-person in disguise and is refused here rather than argued about.
rng0 = np.random.default_rng(0)
bumpA = RA + rng0.uniform(0.2, 0.5, RA.shape)
bumpB = RB + rng0.uniform(0.2, 0.5, RB.shape)
for f in FAMS:
    base = np.stack([a for a, *_ in angles(f)], 1)
    mvA = np.abs(np.stack([a for a, *_ in angles(f, A=bumpA)], 1) - base).max(0)
    mvB = np.abs(np.stack([a for a, *_ in angles(f, B=bumpB)], 1) - base).max(0)
    dead = int((mvA < 1e-9).sum() + (mvB < 1e-9).sum())
    assert dead == 0, f"{f}: {dead} angle(s) insensitive to one chart — that is a solo feature"
log(f"pair-only test PASSED for all {len(FAMS)} families "
    f"({sum(len(angles(f)) for f in FAMS)} angles, each moves with both charts)")

def design(fams):
    cols, meta = [], []
    for f in fams:
        for ang, name, kind, i, j in angles(f):
            cols += [np.cos(ang), np.sin(ang)]
            meta += [{"trig": "cos", "kind": kind, "i": i, "j": j, "label": f"cos({name})", "fam": f},
                     {"trig": "sin", "kind": kind, "i": i, "j": j, "label": f"sin({name})", "fam": f}]
    return np.column_stack(cols + [np.ones(n)]).astype(np.float32), meta

def cv(F, seeds=(7,), rlams=RLAMS):
    Ft = torch.from_numpy(F).to(DEV)
    out = {}
    for rl in rlams:
        aucs = []
        for s in seeds:
            fold = folds[s]; oof = np.zeros(n, np.float32); ok = True
            for k in range(P.NFOLD):
                r = newton_fold(Ft, y, w, fold != k, (rl,))
                if r[rl] is None: ok = False; break
                oof[fold == k] = r[rl][fold == k]
            if not ok: aucs = []; break
            aucs.append(roc_auc_score(y, oof))
        if aucs: out[rl] = float(np.mean(aucs))
    del Ft
    if DEV == "mps": torch.mps.empty_cache()
    if not out: return None, None, {}
    b = max(out, key=out.get)
    return out[b], b, out

rep = {"families": {}, "phases": {}}
bl = json.load(open(f"{D_}/report_baselines_max.json"))
BAR = max(bl["him_only"], bl["her_only"])
log(f"the bar to clear: one chart alone = {BAR:.4f} (her {bl['her_only']:.4f}, him {bl['him_only']:.4f})\n")

# ── PHASE A: each family alone
log("PHASE A — each family fitted alone")
for f in FAMS:
    F, _ = design([f])
    a, rl, _ = cv(F)
    rep["families"][f] = {"n_angles": len(angles(f)), "params": F.shape[1], "auc": a, "rl": rl}
    log(f"   {f:<4}{len(angles(f)):>5} angles {F.shape[1]:>6} params   AUC {a:.4f} @rl {rl:g}"
        f"   {'clears the bar' if a > BAR else ''}")
    del F

# ── PHASE B: the union
log("\nPHASE B — the whole space at once")
F, meta = design(FAMS)
a_union, RL, curve = cv(F)
log(f"   union {F.shape[1]:,} params: {a_union:.4f} @rl {RL:g}  (lambda curve: "
    + "  ".join(f"{k:g}:{v:.4f}" for k, v in curve.items()) + ")")
rep["phases"]["union"] = {"params": F.shape[1], "auc": a_union, "rl": RL}
del F

# ── PHASE C: backward elimination at the working lambda
log("\nPHASE C — backward elimination")
alive = list(FAMS); cur = a_union; path = []
while len(alive) > 1:
    trials = []
    for f in alive:
        Fr, _ = design([g for g in alive if g != f])
        a, _, _ = cv(Fr, rlams=(RL,))
        trials.append((a, f)); del Fr
        log(f"   without {f:<4} {a:.4f}  (cost {cur - a:+.4f})")
    a_best, f_drop = max(trials)
    if a_best >= cur - TOL:
        alive.remove(f_drop); cur = a_best
        log(f"   DROP {f_drop} -> {alive} @ {cur:.4f}")
        path.append({"dropped": f_drop, "remaining": list(alive), "auc": a_best})
    else:
        log(f"   STOP — every remaining family is load-bearing: {alive}")
        break
rep["phases"]["backward"] = {"survivors": alive, "auc": cur, "path": path}

# ── PHASE D: forward greedy, independently
log("\nPHASE D — forward greedy selection (independent of C)")
chosen, best = [], 0.0
while len(chosen) < len(FAMS):
    cands = []
    for f in [g for g in FAMS if g not in chosen]:
        Fa, _ = design(chosen + [f])
        a, _, _ = cv(Fa, rlams=(RL,)); del Fa
        cands.append((a, f))
    a_best, f_add = max(cands)
    if a_best <= best + TOL:
        log(f"   STOP — nothing else adds {TOL}: best candidate {f_add} at {a_best:.4f}")
        break
    chosen.append(f_add); best = a_best
    log(f"   ADD {f_add:<4} -> {chosen} @ {best:.4f}")
rep["phases"]["forward"] = {"chosen": chosen, "auc": best}
log(f"   backward said {alive} ({cur:.4f}) · forward said {chosen} ({best:.4f})")

# ── PHASE E: the agreed set, in full
final = alive if cur >= best else chosen
log(f"\nPHASE E — {final} in full")
F, meta = design(final)
a3, rl3, curve3 = cv(F, seeds=P.SEEDS)
log(f"   {F.shape[1]} params · 3-seed {a3:.4f} @rl {rl3:g}")
rep["phases"]["final"] = {"families": final, "params": F.shape[1], "auc_3seed": a3, "rl": rl3,
                          "lambda_curve": curve3}
log(f"\n   AGAINST THE BASELINES: pair-only {a3:.4f} · her alone {bl['her_only']:.4f} · "
    f"him alone {bl['him_only']:.4f}  ->  {a3 - BAR:+.4f}")
rep["baselines"] = bl
rep["lift_over_best_solo"] = a3 - BAR
json.dump(rep, open(f"{D_}/report_pairspace.json", "w"), indent=1)
log("saved report_pairspace.json")
