"""comp_label-p1971_baselines.py — copy of fit_baselines_max.py that also prints the WITHIN-ERA AUC of each
baseline (same decade rule as fit_nested.py) and writes comp_label-p1971_baselines.json. Original docstring:

fit_baselines_max.py — the operator's two baselines, on the corpus the SHIPPED model was fitted on.

him-only and her-only were measured on the 90k corpus and never on the 175,155-row one, so the
shipped 0.7430 has been standing without the bar it is supposed to clear. Same folds, same closed-form
solver, same balanced BCE. Also reported, as a sanity number rather than a permitted baseline: the
signed difference in birth dates, which is the whole of what a cynic would say the model is reading.
"""
import itertools, json, os
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
import fit_phasor_torch as P
from closed_newton import newton_fold, RLAMS, DEV

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_max"))
full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
names = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, nm in enumerate(names) if nm != "true_south_node"]
ra, rb = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NB = len(keep); C2 = list(itertools.combinations(range(NB), 2))
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
n = len(y)
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)
cs = lambda a: [np.cos(a), np.sin(a)]
_yr = pd.to_numeric(full.dob_a.astype(str).str.slice(0, 4), errors="coerce").to_numpy(); WITHIN = {}

def cv(cols, label):
    F = np.column_stack(cols + [np.ones(n)]).astype(np.float32)
    Ft = torch.from_numpy(F).to(DEV); Ft2 = Ft
    best = None
    for rl in RLAMS:
        oof = np.zeros(n, np.float32)
        dead = False
        for k in range(P.NFOLD):
            r = newton_fold(Ft, y, w, fold != k, (rl,))
            if r[rl] is None: dead = True; break
            oof[fold == k] = r[rl][fold == k]
        if dead: continue
        a = roc_auc_score(y, oof)
        if best is None or a > best[0]: best = (a, rl)
    del Ft
    # WITHIN-ERA AUC of the best-lambda OOF, the same decade rule as fit_nested.py (>=200 rows, both classes)
    oof = np.zeros(n, np.float32)
    for k in range(P.NFOLD):
        r = newton_fold(Ft2, y, w, fold != k, (best[1],))
        oof[fold == k] = r[best[1]][fold == k]
    dec = _yr // 10 * 10; num = den = 0.0
    for d in np.unique(dec[np.isfinite(dec)]):
        rr = dec == d
        if rr.sum() >= 200 and 0 < y[rr].sum() < rr.sum():
            num += roc_auc_score(y[rr], oof[rr]) * rr.sum(); den += rr.sum()
    we = num / den if den else float("nan")
    WITHIN[label] = we
    print(f"  {label:<34}{F.shape[1]:>5} params   AUC {best[0]:.4f}  @rl {best[1]:g}   WITHIN-ERA {we:.4f}", flush=True)
    return best[0]

print(f"corpus {n:,} · positives {int(y.sum()):,}\n")
# the SHIPPED families, and each solo chart on its own — the mandated baselines
him = [c for i in range(NB) for c in cs(ra[:, i])] + \
      [c for i, j in C2 for c in cs(ra[:, i] - ra[:, j])] + \
      [c for i, j in C2 for c in cs(ra[:, i] + ra[:, j])]
her = [c for i in range(NB) for c in cs(rb[:, i])] + \
      [c for i, j in C2 for c in cs(rb[:, i] - rb[:, j])] + \
      [c for i, j in C2 for c in cs(rb[:, i] + rb[:, j])]
shipped = [c for i in range(NB) for c in cs(ra[:, i] - rb[:, i])] + \
          [c for i in range(NB) for c in cs(ra[:, i])] + \
          [c for i in range(NB) for c in cs(rb[:, i])] + \
          [c for i, j in C2 for c in cs(rb[:, i] - rb[:, j])] + \
          [c for i, j in C2 for c in cs(rb[:, i] + rb[:, j])]
a_him = cv(him, "him only (complete solo algebra)")
a_her = cv(her, "her only (complete solo algebra)")
a_pair = cv(shipped, "the shipped families (D+NM+NW+AW+MW)")

# the cynic's number: signed birth-date difference, 2 parameters
# the happy corpus has no true_dob_* columns (its dates are all full precision); fall back to dob_*
_ca = "true_dob_a" if "true_dob_a" in full.columns else "dob_a"
_cb = "true_dob_b" if "true_dob_b" in full.columns else "dob_b"
ya = pd.to_datetime(full[_ca].astype(str).str.replace("-00", "-01", regex=False), errors="coerce")
yb = pd.to_datetime(full[_cb].astype(str).str.replace("-00", "-01", regex=False), errors="coerce")
gap = ((ya - yb).dt.days / 365.25).fillna(0).to_numpy().reshape(-1, 1)
oof = np.zeros(n)
for k in range(P.NFOLD):
    m = fold != k
    oof[~m] = LogisticRegression(max_iter=1000, class_weight="balanced").fit(
        np.c_[gap[m], gap[m] ** 2], y[m]).predict_proba(np.c_[gap[~m], gap[~m] ** 2])[:, 1]
a_gap = roc_auc_score(y, oof)
print(f"  {'signed birth-date gap (2 params)':<34}{3:>5} params   AUC {a_gap:.4f}   [sanity, not a baseline]")

print(f"\n  pair over the best solo chart: {a_pair - max(a_him, a_her):+.4f}")
print(f"  pair over the age-gap number : {a_pair - a_gap:+.4f}")
json.dump({"him_only": a_him, "her_only": a_her, "shipped_families": a_pair, "age_gap": a_gap,
           "lift_over_best_solo": a_pair - max(a_him, a_her), "within_era": WITHIN},
          open(f"{D_}/comp_label-p1971_baselines.json", "w"), indent=1)
print(f"\nsaved comp_label-p1971_baselines.json")
