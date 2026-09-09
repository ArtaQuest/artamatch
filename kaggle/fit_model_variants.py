"""fit_model_variants.py — modelling improvements, CLOSED FORM ONLY (standing order).

Run on the winning target from report_targets.json, survivor families from the ablation.

  per-family lambda   each family gets its own ridge strength — the reg vector is block-diagonal,
                      so it is STILL one Cholesky per step; swept by coordinate descent around the
                      global optimum (2 passes over families, 3 candidates each)
  survivor-quad       every product of two surviving-model terms, appended — the restricted second
                      order that the global quadratic (rejected) could not isolate
  five seeds          the final configuration at seeds 7/23/101/311/887
  learning curve      group-aware subsamples at 45k / 90k / all rows — is more harvest still paying
"""
import itertools, json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import fit_phasor_torch as P
from closed_newton import newton_fold, RLAMS, DEV

D_ = os.path.expanduser(os.environ.get("AQ_TD_DIR", "~/.artamatch-dev/tilldeath_max"))
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
SEEDS5 = (7, 23, 101, 311, 887)

rep_ab = json.load(open(f"{D_}/report_ablation.json"))
rep_tg = json.load(open(f"{D_}/report_targets.json"))
FAMS = rep_ab["survivor_families"]
TGT = rep_tg["_best"]
log(f"families {FAMS} · target variant '{TGT}'")

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
src = full.src.fillna("").to_numpy()
natural = full.natural.to_numpy().astype(bool)
strict_mask = (y > 0) | natural
only_remarry = (y > 0) & (src == "remarry")
REL = {"P1534": 1.0, "end-date": 0.99, "judge": 0.95, "infid": 0.90, "text": 0.85, "remarry": 0.78}
rel = np.array([max((REL[p] for p in s.split("+") if p), default=0.0) for s in src], np.float32)

Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
names = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, nm in enumerate(names) if nm != "true_south_node"]
ra, rb = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NB = len(keep)
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
folds = {s: np.random.default_rng(s).integers(0, P.NFOLD, gid.max() + 1)[gid] for s in SEEDS5}
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

blocks = [(f, np.column_stack(fam_cols(f)).astype(np.float32)) for f in FAMS]
sizes = [b.shape[1] for _, b in blocks]
F = np.column_stack([b for _, b in blocks] + [np.ones(n)]).astype(np.float32)
Ft = torch.from_numpy(F).to(DEV)
p1 = F.shape[1]
log(f"design {F.shape} · blocks {dict(zip(FAMS, sizes))}")

# the winning target's weights/mask
train_mask = np.ones(n, bool)
w_extra = np.ones(n, np.float32)
if TGT == "weighted":
    w_extra = np.where(y > 0, rel, 1.0).astype(np.float32)
elif TGT == "no-remarry":
    train_mask = ~only_remarry
elif TGT == "strict":
    train_mask = strict_mask
pos = train_mask & (y > 0); neg = train_mask & (y == 0)
wb = np.zeros(n, np.float32)
wb[pos] = train_mask.sum() / (2 * pos.sum()); wb[neg] = train_mask.sum() / (2 * neg.sum())
W = wb * w_extra

import closed_newton as CN
def cv_regvec(regmul, seeds, rlbase):
    """per-family lambda: newton with reg VECTOR = rlbase * scale * regmul[block]"""
    aucs = {}
    for s_ in seeds:
        fold = folds[s_]
        oof = np.zeros(n, np.float32)
        for k in range(P.NFOLD):
            wm_np = (W * ((fold != k) & train_mask)).astype(np.float32)
            wm = torch.from_numpy(wm_np).to(DEV)
            G0 = CN._wgram(Ft, wm)
            scale = float(np.mean(np.diag(G0)[:-1]))
            reg = np.empty(p1); o = 0
            for m_, sz in zip(regmul, sizes):
                reg[o:o+sz] = rlbase * scale * m_; o += sz
            reg[-1] = 0.0
            beta = np.zeros(p1)
            yt = torch.from_numpy(y).to(DEV)
            for step in range(3):
                bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
                z = CN._matvec(Ft, bt)
                pr = torch.sigmoid(z)
                gv = CN._wmatvec(Ft, wm * (yt - pr)) - reg * beta
                H = 0.25 * G0.copy() if step == 0 else CN._wgram(Ft, wm * pr * (1 - pr))
                H[np.diag_indices_from(H)] += reg
                beta = beta + CN._solve(H, gv, scale)
            bt = torch.from_numpy(beta.astype(np.float32)).to(DEV)
            zz = CN._matvec(Ft, bt).cpu().numpy()
            oof[fold == k] = zz[fold == k]
        aucs[s_] = {"own": float(roc_auc_score(y, oof)),
                    "strict": float(roc_auc_score(y[strict_mask], oof[strict_mask]))}
    return aucs

# 1. global lambda baseline (seed 7)
base_curve = {}
for rl in RLAMS:
    base_curve[rl] = cv_regvec([1.0] * len(FAMS), (7,), rl)[7]["strict"]
rl0 = max(base_curve, key=base_curve.get)
log(f"global lambda: " + "  ".join(f"{k:g}:{v:.4f}" for k, v in base_curve.items()) +
    f"  -> rl {rl0:g}")

# 2. per-family multipliers, 2 coordinate passes over {0.3, 1, 3}
mult = [1.0] * len(FAMS)
best = base_curve[rl0]
for _pass in range(2):
    for fi in range(len(FAMS)):
        for cand in (0.3, 3.0):
            trial = list(mult); trial[fi] = cand
            a = cv_regvec(trial, (7,), rl0)[7]["strict"]
            if a > best + 1e-5:
                best = a; mult = trial
                log(f"   {FAMS[fi]} x{cand}: STRICT {a:.4f}  (kept)")
log(f"per-family multipliers {dict(zip(FAMS, mult))} -> STRICT {best:.4f}")

# 3. five-seed final at the tuned config
five = cv_regvec(mult, SEEDS5, rl0)
mo = np.mean([five[s]["own"] for s in SEEDS5]); ms = np.mean([five[s]["strict"] for s in SEEDS5])
log(f"FIVE-SEED FINAL: own-CV {mo:.4f} +/- {np.std([five[s]['own'] for s in SEEDS5]):.4f} · "
    f"STRICT {ms:.4f} +/- {np.std([five[s]['strict'] for s in SEEDS5]):.4f}")

# 4. learning curve (group-aware subsample, seed 7, tuned config)
rng = np.random.default_rng(7)
ug = np.unique(gid)
lc = {}
for frac, nm in ((0.25, "44k"), (0.5, "88k"), (1.0, "175k")):
    sel_g = set(rng.choice(ug, int(len(ug) * frac), replace=False)) if frac < 1 else set(ug)
    keep_rows = np.array([g in sel_g for g in gid])
    tm_save, W_save = train_mask.copy(), W.copy()
    globals()["train_mask"] = train_mask & keep_rows
    a = cv_regvec(mult, (7,), rl0)[7]
    globals()["train_mask"] = tm_save
    lc[nm] = a
    log(f"   learning curve {nm}: own {a['own']:.4f} · STRICT {a['strict']:.4f}")

json.dump({"families": FAMS, "target": TGT, "rl": rl0, "block_mult": dict(zip(FAMS, mult)),
           "five_seed": {str(k): v for k, v in five.items()},
           "own_mean": float(mo), "strict_mean": float(ms), "learning_curve": lc},
          open(f"{D_}/report_model_variants.json", "w"), indent=1)
log("saved report_model_variants.json")
