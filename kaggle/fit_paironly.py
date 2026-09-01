"""fit_paironly.py — the PAIR-ONLY model (operator 2026-09-01): no single-person feature at all.

A feature earns its place only if it cannot be computed from one chart. That bans every natal family
the previous model leaned on — his positions, her positions, either partner's own aspects, either
partner's own midpoint axes — and leaves the five families that are irreducibly about two people:

    D    man[i] - woman[i]              same-body synastry aspect
    X    man[i] - woman[j]   (i != j)   the full cross-body synastry grid
    S    man[i] + woman[i]              the couple's midpoint axis for that body
    XM   man[i] + woman[j]   (i != j)   cross-body couple midpoints
    C    (man[i]+woman[i]) - (man[j]+woman[j])   aspects INSIDE the composite chart

Every one of these changes when either birth date moves, and none can be evaluated for one person
alone — which is the whole content of a compatibility claim.

Backward elimination, then term pruning, then leave-one-out, all on the closed-form three-step
Newton solver. The two operator-fixed baselines (him-only, her-only, complete solo algebra) are
measured on this same corpus and folds and printed beside the result, because the honest question is
not whether the pair model is good but whether two charts say something one chart does not.
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
ra, rb = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NB = len(bod); C2 = list(itertools.combinations(range(NB), 2))
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
n = len(y)
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)


def fam(f):
    """-> list of (angle, name, kind, i, j) — every one irreducibly two-person"""
    if f == "D":  return [(ra[:, i] - rb[:, i], f"D {bod[i]}", "diff", i, None) for i in range(NB)]
    if f == "S":  return [(ra[:, i] + rb[:, i], f"mid {bod[i]}", "sum", i, None) for i in range(NB)]
    if f == "X":  return [(ra[:, i] - rb[:, j], f"his {bod[i]}-her {bod[j]}", "xdiff", i, j)
                          for i in range(NB) for j in range(NB) if i != j]
    if f == "XM": return [(ra[:, i] + rb[:, j], f"mid his {bod[i]}/her {bod[j]}", "xsum", i, j)
                          for i in range(NB) for j in range(NB) if i != j]
    if f == "C":  return [((ra[:, i] + rb[:, i]) - (ra[:, j] + rb[:, j]),
                           f"comp {bod[i]}-{bod[j]}", "camp", i, j) for i, j in C2]

FAMS = ["D", "S", "X", "XM", "C"]

def design(fams):
    cols, meta = [], []
    for f in fams:
        for ang, name, kind, i, j in fam(f):
            cols += [np.cos(ang), np.sin(ang)]
            meta += [{"trig": "cos", "kind": kind, "i": i, "j": j, "label": f"cos({name})"},
                     {"trig": "sin", "kind": kind, "i": i, "j": j, "label": f"sin({name})"}]
    F = np.column_stack(cols + [np.ones(n)]).astype(np.float32)
    return F, meta

def cv(F, seeds=(7,), rlams=RLAMS, want_oof=False):
    Ft = torch.from_numpy(F).to(DEV)
    out, best_oof = {}, None
    for rl in rlams:
        aucs = []
        for s in seeds:
            fold = folds[s]
            oof = np.zeros(n, np.float32)
            ok = True
            for k in range(P.NFOLD):
                r = newton_fold(Ft, y, w, fold != k, (rl,))
                if r[rl] is None: ok = False; break
                oof[fold == k] = r[rl][fold == k]
            if not ok: aucs = []; break
            aucs.append(roc_auc_score(y, oof))
            if want_oof and s == seeds[0]: best_oof = oof.copy()
        if aucs: out[rl] = float(np.mean(aucs))
    del Ft
    if DEV == "mps": torch.mps.empty_cache()
    if not out: return None, None, None
    b = max(out, key=out.get)
    return out[b], b, out

# ── 1. backward elimination over the pair-only families
alive = list(FAMS)
F, _ = design(alive)
cur, rl, _ = cv(F)
log(f"pair-only union {F.shape[1]} params: {cur:.4f} @rl {rl:g}")
path = [{"fams": list(alive), "auc": cur}]
while len(alive) > 1:
    trials = []
    for f in alive:
        rest = [g for g in alive if g != f]
        Fr, _ = design(rest)
        a, _, _ = cv(Fr)
        trials.append((a, f))
        log(f"   without {f:<3} {a:.4f}  (cost {cur - a:+.4f})")
    a_best, f_drop = max(trials)
    if a_best >= cur - TOL:
        alive.remove(f_drop); cur = a_best
        log(f"DROP {f_drop} -> {alive} @ {cur:.4f}")
        path.append({"fams": list(alive), "auc": a_best})
    else:
        log(f"STOP: every remaining pair family is load-bearing {alive}")
        break

F, meta = design(alive)
mu, rl, curve = cv(F, seeds=P.SEEDS)
log(f"SURVIVORS {alive}: {F.shape[1]} params · 3-seed mean {mu:.4f} @rl {rl:g}")

# ── 2. term pruning, selection inside each fold
Ft = torch.from_numpy(F).to(DEV)
nterm = F.shape[1] - 1
MS = [m for m in (8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, nterm) if m <= nterm]
fold = folds[7]
curves = {m: np.zeros(n, np.float32) for m in MS}
for k in range(P.NFOLD):
    trm = fold != k
    wm = torch.from_numpy((w * trm).astype(np.float32)).to(DEV)
    G0 = _wgram(Ft, wm); scale = float(np.mean(np.diag(G0)[:-1]))
    reg = np.full(F.shape[1], rl * scale); reg[-1] = 0.0
    beta = np.zeros(F.shape[1]); yt = torch.from_numpy(y).to(DEV)
    for step in range(3):
        bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
        pr = torch.sigmoid(_matvec(Ft, bt))
        gv = _wmatvec(Ft, wm * (yt - pr)) - reg * beta
        H = 0.25 * G0.copy() if step == 0 else _wgram(Ft, wm * pr * (1 - pr))
        H[np.diag_indices_from(H)] += reg
        beta = beta + _solve(H, gv, scale)
    order = np.argsort(-np.abs(beta[:nterm]))
    for m in MS:
        sel = np.sort(np.r_[order[:m], [nterm]])
        Fm = np.ascontiguousarray(F[:, sel])
        Fmt = torch.from_numpy(Fm).to(DEV)
        r2 = newton_fold(Fmt, y, w, trm, (rl,))
        if r2[rl] is not None: curves[m][fold == k] = r2[rl][fold == k]
        del Fmt
prune = {m: float(roc_auc_score(y, curves[m])) for m in MS}
log("pruning curve: " + "  ".join(f"{m}:{prune[m]:.4f}" for m in MS))
best_m = min([m for m in MS if prune[m] >= max(prune.values()) - TOL2])
log(f"MINIMAL pair-only model: {best_m} terms ({prune[best_m]:.4f}; best {max(prune.values()):.4f})")

# ── 3. full-data fit of the minimal model, and its LOO
wm = torch.from_numpy(w).to(DEV)
G0 = _wgram(Ft, wm); scale = float(np.mean(np.diag(G0)[:-1]))
reg = np.full(F.shape[1], rl * scale); reg[-1] = 0.0
beta = np.zeros(F.shape[1]); yt = torch.from_numpy(y).to(DEV)
for step in range(3):
    bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
    pr = torch.sigmoid(_matvec(Ft, bt))
    gv = _wmatvec(Ft, wm * (yt - pr)) - reg * beta
    H = 0.25 * G0.copy() if step == 0 else _wgram(Ft, wm * pr * (1 - pr))
    H[np.diag_indices_from(H)] += reg
    beta = beta + _solve(H, gv, scale)
order = np.argsort(-np.abs(beta[:nterm]))[:best_m]
del Ft
sel = np.sort(np.r_[order, [nterm]])
Fmin = np.ascontiguousarray(F[:, sel])
mmeta = [meta[i] for i in sel[:-1]]
base_auc, rl2, _ = cv(Fmin, seeds=P.SEEDS, rlams=(rl,))
log(f"the {best_m}-term pair-only model, 3 seeds: {base_auc:.4f}")

loo = []
for j in range(best_m):
    Fj = np.ascontiguousarray(np.delete(Fmin, j, axis=1))
    a, _, _ = cv(Fj, seeds=(7,), rlams=(rl,))
    loo.append({"term": mmeta[j]["label"], "contribution": prune[best_m] - a if a else None})
loo_sorted = sorted([t for t in loo if t["contribution"] is not None],
                    key=lambda t: -t["contribution"])
log("top leave-one-out contributions:")
for t in loo_sorted[:12]:
    log(f"   {t['term']:<34}{t['contribution']:+.5f}")

bl = json.load(open(f"{D_}/report_baselines_max.json"))
log(f"\nAGAINST THE TWO PERMITTED BASELINES on this corpus and these folds:")
log(f"   him only (complete solo algebra)  {bl['him_only']:.4f}")
log(f"   her only (complete solo algebra)  {bl['her_only']:.4f}")
log(f"   PAIR-ONLY model                   {base_auc:.4f}   "
    f"({base_auc - max(bl['him_only'], bl['her_only']):+.4f} vs the best solo chart)")

json.dump({"families": alive, "elimination_path": path, "rel_lambda": rl,
           "pruning_curve": {str(k): v for k, v in prune.items()}, "minimal_m": int(best_m),
           "auc_3seed": base_auc, "loo": loo_sorted,
           "terms": [{**mmeta[i], "w": float(beta[order[i]])} for i in range(best_m)],
           "bias": float(beta[-1]), "baselines": bl},
          open(f"{D_}/report_paironly.json", "w"), indent=1)
log("saved report_paironly.json")
