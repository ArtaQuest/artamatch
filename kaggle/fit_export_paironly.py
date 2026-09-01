"""fit_export_paironly.py — ship the PAIR-ONLY model (operator 2026-09-01).

Reads report_paironly.json, REFITS the chosen terms on their own (so the shipped weights and the
shipped bias are one self-consistent fit rather than a slice of a wider one), then writes the same
schema the page and docs/tilldeath.py already read: terms, bias, quantiles over the whole corpus,
and 200 couples with their float64 scores for the shipped scorer to reproduce.

Every term is a two-chart angle. There is no natal, aspect or midpoint family belonging to one
person, and web/verify_docs.py now refuses the build if one appears.
"""
import json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import closed_newton as CN

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
OUT = os.path.expanduser("~/.artaquest-dev/wt/am-build/docs/tilldeath.json")
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)

rp = json.load(open(f"{D_}/report_paironly.json"))
full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm_all = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, x in enumerate(nm_all) if x != "true_south_node"]
bodies = [nm_all[i].replace("true_", "").replace("mean_", "") for i in keep]
ra, rb = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
n = len(y)

def angle(t):
    i, j, k = t["i"], t["j"], t["kind"]
    if k == "diff":  return ra[:, i] - rb[:, i]
    if k == "sum":   return ra[:, i] + rb[:, i]
    if k == "xdiff": return ra[:, i] - rb[:, j]
    if k == "xsum":  return ra[:, i] + rb[:, j]
    if k == "camp":  return (ra[:, i] + rb[:, i]) - (ra[:, j] + rb[:, j])
    raise ValueError(k)

terms = rp["terms"]
SOLO = {"natM", "natW", "aspM", "aspW", "midM", "midW"}
assert not ({t["kind"] for t in terms} & SOLO), "a single-person family reached the export"
cols = [np.cos(angle(t)) if t["trig"] == "cos" else np.sin(angle(t)) for t in terms]
F = np.column_stack(cols + [np.ones(n)]).astype(np.float32)
log(f"{len(terms)} pair-only terms · kinds {sorted({t['kind'] for t in terms})}")

Ft = torch.from_numpy(F).to(CN.DEV)
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)
wm = torch.from_numpy(w).to(CN.DEV)
G0 = CN._wgram(Ft, wm)
scale = float(np.mean(np.diag(G0)[:-1]))
reg = np.full(F.shape[1], rp["rel_lambda"] * scale); reg[-1] = 0.0
beta = np.zeros(F.shape[1]); yt = torch.from_numpy(y).to(CN.DEV)
for step in range(3):
    bt = torch.from_numpy(beta.astype(np.float32)).to(CN.DEV)
    pr = torch.sigmoid(CN._matvec(Ft, bt))
    gv = CN._wmatvec(Ft, wm * (yt - pr)) - reg * beta
    H = 0.25 * G0.copy() if step == 0 else CN._wgram(Ft, wm * pr * (1 - pr))
    H[np.diag_indices_from(H)] += reg
    beta = beta + CN._solve(H, gv, scale)
score = F.astype(np.float64) @ beta
log(f"in-sample AUC {roc_auc_score(y, score):.4f} (reference; the claim is the CV {rp['auc_3seed']:.4f})")

# THE VERIFY COUPLES MUST BE ONES THE PAGE CAN ACTUALLY COMPUTE. The corpus reaches back past 1598
# (the fit read precomputed phases, so training was never limited by the browser's tables), but the
# shipped ayanamsa spans 1598-2200 and REFUSES rather than clamps outside it. Sampling without this
# filter shipped a 1548 couple and the gate stopped the build — correctly.
SPAN = (1598, 2200)
yr = lambda c: pd.to_numeric(c.str.slice(0, 4), errors="coerce")
inspan = ((yr(full.dob_a) >= SPAN[0]) & (yr(full.dob_a) <= SPAN[1])
          & (yr(full.dob_b) >= SPAN[0]) & (yr(full.dob_b) <= SPAN[1])).to_numpy()
print(f"  {int(inspan.sum()):,} of {n:,} couples are inside the page's own {SPAN[0]}-{SPAN[1]} span")
rng = np.random.default_rng(20260901)
vsel = rng.choice(np.where(inspan)[0], 200, replace=False)
bl = rp["baselines"]
model = {
    "name": "till-death-phasor-pair-only",
    "edition": "V — Till Death Do Us Part (pair only)",
    "date": "2026-09-01",
    "zodiac": "sidereal (Lahiri), noon UT, birth dates only",
    "pair_only": True,
    "bodies": bodies,
    "servable_span": [1598, 2200],
    "formula": "score = bias + sum_t w_t * trig_t(angle_t); p = sigmoid(score)",
    "angles": {"diff": "man[i] - woman[i]", "sum": "man[i] + woman[i]",
               "xdiff": "man[i] - woman[j]", "xsum": "man[i] + woman[j]",
               "camp": "(man[i]+woman[i]) - (man[j]+woman[j])"},
    "families": rp["families"],
    "terms": [{**t, "w": float(beta[k])} for k, t in enumerate(terms)],
    "bias": float(beta[-1]),
    "cv_auc_broad": rp["auc_3seed"],
    "baseline_him_only": bl["him_only"],
    "baseline_her_only": bl["her_only"],
    "n_corpus": int(n), "n_positive": int(y.sum()),
    "quantiles": [float(q) for q in np.quantile(score, np.linspace(0, 1, 401))],
    "verify": [{"dob_a": full.dob_a.iloc[int(i)], "dob_b": full.dob_b.iloc[int(i)],
                "score": float(score[i])} for i in vsel],
}
json.dump(model, open(OUT, "w"), indent=1)
log(f"wrote {OUT} ({os.path.getsize(OUT)//1024} KB)")
log(f"CV {rp['auc_3seed']:.4f} · him-only {bl['him_only']:.4f} · her-only {bl['her_only']:.4f} "
    f"-> {rp['auc_3seed'] - max(bl['him_only'], bl['her_only']):+.4f} vs the best solo chart")
