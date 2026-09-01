"""fit_target_variants.py — improving the TARGET, judged on one yardstick (operator 2026-08-31).

Four definitions of 'came apart', each fitted with the survivor families and the closed-form
solver, each scored two ways:

    own-CV       10-fold grouped CV on the variant's own labels — how learnable it is
    STRICT AUC   the same out-of-fold scores, evaluated ONLY on the confident core:
                 explicitly-separated rows vs explicitly-natural-end rows. One yardstick,
                 comparable across variants, immune to each variant's own label shifts.

  base       y as built (all six sources positive, everything else negative)
  weighted   same labels, sample weights by source reliability — P1534 1.0 · end-date 0.99 ·
             judge 0.95 · infid 0.90 · text 0.85 · remarry 0.78 (its measured agreement) —
             a positive keeps its BEST source's weight; negatives 1.0
  no-remarry rows whose ONLY evidence is remarriage are EXCLUDED from training (still scored)
  strict     train only explicit-sep vs explicit-natural rows (confident vs confident)

Also reported: the base model's out-of-fold ranking sliced per source — which kind of
separation the sky actually sees.
"""
import json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P
from closed_newton import newton_fold, RLAMS, DEV

D_ = os.path.expanduser(os.environ.get("AQ_TD_DIR", "~/.artamatch-dev/tilldeath_max"))
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

rep_ab = json.load(open(f"{D_}/report_ablation.json"))
FAMS = rep_ab["survivor_families"]
log(f"survivor families from the max-corpus ablation: {FAMS}")

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
src = full.src.fillna("").to_numpy()
natural = full.natural.to_numpy().astype(bool)
strict_mask = (y > 0) | natural
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
names = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, nm in enumerate(names) if nm != "true_south_node"]
bod = [names[i].replace("true_", "").replace("mean_", "") for i in keep]
ra, rb = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NB = len(bod)
import itertools
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
n = len(y)
cs = lambda a: [np.cos(a), np.sin(a)]

def fam_cols(f):
    if f == "D":  return [c for i in range(NB) for c in cs(ra[:, i] - rb[:, i])]
    if f == "NM": return [c for i in range(NB) for c in cs(ra[:, i])]
    if f == "NW": return [c for i in range(NB) for c in cs(rb[:, i])]
    if f == "S":  return [c for i in range(NB) for c in cs(ra[:, i] + rb[:, i])]
    if f == "AM": return [c for i, j in C2 for c in cs(ra[:, i] - ra[:, j])]
    if f == "AW": return [c for i, j in C2 for c in cs(rb[:, i] - rb[:, j])]
    if f == "MM": return [c for i, j in C2 for c in cs(ra[:, i] + ra[:, j])]
    if f == "MW": return [c for i, j in C2 for c in cs(rb[:, i] + rb[:, j])]
    if f == "C":  return [c for i, j in C2 for c in cs((ra[:, i] + rb[:, i]) - (ra[:, j] + rb[:, j]))]
    if f == "X":  return [c for i in range(NB) for j in range(NB) if i != j
                          for c in cs(ra[:, i] - rb[:, j])]
F = np.column_stack([c for f in FAMS for c in fam_cols(f)] + [np.ones(n)]).astype(np.float32)
Ft = torch.from_numpy(F).to(DEV)
log(f"design {F.shape}")

REL = {"P1534": 1.0, "end-date": 0.99, "judge": 0.95, "infid": 0.90, "text": 0.85, "remarry": 0.78}
def src_rel(s):
    parts = [p for p in s.split("+") if p]
    return max((REL[p] for p in parts), default=0.0)
rel = np.array([src_rel(s) for s in src], np.float32)
only_remarry = (y > 0) & (src == "remarry")

def balanced(yv, mask):
    w = np.zeros(n, np.float32)
    m = mask.astype(bool)
    pos = m & (yv > 0); neg = m & (yv == 0)
    w[pos] = m.sum() / (2 * max(pos.sum(), 1))
    w[neg] = m.sum() / (2 * max(neg.sum(), 1))
    return w

def run(label, yv, w_extra, train_mask):
    wbase = balanced(yv, train_mask) * w_extra
    per = {}
    for s_ in (7,):
        fold = folds[s_]
        oof = {rl: np.zeros(n, np.float32) for rl in RLAMS}
        dead = set()
        for k in range(P.NFOLD):
            trm = (fold != k) & train_mask
            res = newton_fold(Ft, yv, wbase * trm, np.ones(n, bool), (RLAMS))
            # NOTE: newton_fold takes trm separately; here train selection rides IN the weights
            for rl in RLAMS:
                if res[rl] is None: dead.add(rl)
                else: oof[rl][fold == k] = res[rl][fold == k]
        cur = {rl: (roc_auc_score(y[fold >= 0], oof[rl]) if rl not in dead else 0.0)
               for rl in RLAMS}
        per = (cur, oof)
    curve, oof = per
    best = max(curve, key=curve.get)
    o = oof[best]
    own = curve[best]
    sm = strict_mask
    strict = roc_auc_score(y[sm], o[sm])
    log(f">> {label:<12} rl {best:g}  own-CV {own:.4f}   STRICT {strict:.4f}")
    out = {"rel_lambda": best, "own_cv": float(own), "strict_auc": float(strict)}
    if label == "base":
        neg = o[y == 0]
        for tag in ("P1534", "end-date", "judge", "text", "infid", "remarry"):
            mm = (y == 1) & np.char.find(src.astype(str), tag) >= 0
            mm = np.array([(y[i] == 1) and (tag in src[i]) for i in range(n)])
            if mm.sum() > 50:
                aa = roc_auc_score(np.r_[np.ones(int(mm.sum())), np.zeros(len(neg))],
                                   np.r_[o[mm], neg])
                log(f"     slice {tag:<9} n={int(mm.sum()):>5,}  AUC vs all negatives {aa:.4f}")
                out[f"slice_{tag}"] = float(aa)
        np.save(f"{D_}/oof_base_target.npy", o)
    return out

rep = {}
allm = np.ones(n, bool)
rep["base"] = run("base", y, np.ones(n, np.float32), allm)
rep["weighted"] = run("weighted", y, np.where(y > 0, rel, 1.0).astype(np.float32), allm)
rep["no-remarry"] = run("no-remarry", y, np.ones(n, np.float32), ~only_remarry)
rep["strict"] = run("strict", y, np.ones(n, np.float32), strict_mask)
best_t = max(rep, key=lambda k: rep[k]["strict_auc"])
log(f"BEST TARGET by the strict yardstick: {best_t} ({rep[best_t]['strict_auc']:.4f})")
rep["_best"] = best_t
json.dump(rep, open(f"{D_}/report_targets.json", "w"), indent=1)
log("saved report_targets.json")
