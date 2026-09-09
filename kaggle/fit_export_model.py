"""fit_export_model.py — ship any fitted model, whatever families and harmonics it uses.

Reads a report holding a term list of {kind, i, j, k, trig}, REFITS those exact terms on the whole
corpus by the closed-form three-step Newton (so the shipped weights and bias are one self-consistent
fit rather than a slice of a wider one), and writes docs/tilldeath.json in the schema the page and
docs/tilldeath.py already read.

  AQ_REPORT   which report to ship (default report_final.json)
  AQ_TERMS    how many of its terms, most-agreed first (default: the report's knee)

The term list comes from the frontier's FOLD AGREEMENT, not from one fold: a term chosen by 9 of 10
folds is a term the data insists on, whereas the single best fold's list is one draw. The AUC quoted
is the frontier's own out-of-fold figure at that k, which was measured with selection inside each
fold and is therefore not inflated by this choice.
"""
import json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import closed_newton as CN

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
REPORT = os.environ.get("AQ_REPORT", "report_final.json")
OUT = os.path.expanduser("~/.artaquest-dev/wt/am-build/docs/tilldeath.json")
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)

rp = json.load(open(f"{D_}/{REPORT}"))
K = int(os.environ.get("AQ_TERMS", rp.get("knee", 32)))
terms = rp["frequency"][:K]
log(f"{REPORT}: shipping {K} terms (folds agreeing: "
    f"{terms[0]['folds']} down to {terms[-1]['folds']} of 10)")

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
nm_all = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, x in enumerate(nm_all) if x != "true_south_node"]
bodies = [nm_all[i].replace("true_", "").replace("mean_", "") for i in keep]
A, B = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
n = len(y)

def angle(t):
    i, j, k = t["i"], t["j"], t["kind"]
    if k == "diff":  return A[:, i] - B[:, i]
    if k == "sum":   return A[:, i] + B[:, i]
    if k == "natM":  return A[:, i]
    if k == "natW":  return B[:, i]
    if k == "xdiff": return A[:, i] - B[:, j]
    if k == "xsum":  return A[:, i] + B[:, j]
    if k == "aspM":  return A[:, i] - A[:, j]
    if k == "aspW":  return B[:, i] - B[:, j]
    if k == "midM":  return A[:, i] + A[:, j]
    if k == "midW":  return B[:, i] + B[:, j]
    if k == "camp":  return (A[:, i] + B[:, i]) - (A[:, j] + B[:, j])
    if k == "ddm":   return (A[:, i] - B[:, i]) - (A[:, j] - B[:, j])
    if k == "ddp":   return (A[:, i] - B[:, i]) + (A[:, j] - B[:, j])
    if k == "ssp":   return (A[:, i] + B[:, i]) + (A[:, j] + B[:, j])
    if k == "dsm":   return (A[:, i] - B[:, i]) - (A[:, j] + B[:, j])
    if k == "dsp":   return (A[:, i] - B[:, i]) + (A[:, j] + B[:, j])
    raise ValueError(k)

cols = []
for t in terms:
    a = angle(t) * t.get("k", 1)
    cols.append(np.cos(a) if t["trig"] == "cos" else np.sin(a))
F = np.column_stack(cols + [np.ones(n)]).astype(np.float32)
Ft = torch.from_numpy(F).to(CN.DEV)
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)
wm = torch.from_numpy(w).to(CN.DEV)
G0 = CN._wgram(Ft, wm)
scale = float(np.mean(np.diag(G0)[:-1]))
reg = np.full(F.shape[1], rp["rl"] * scale); reg[-1] = 0.0
beta = np.zeros(F.shape[1]); yt = torch.from_numpy(y).to(CN.DEV)
for step in range(3):
    bt = torch.from_numpy(beta.astype(np.float32)).to(CN.DEV)
    pr = torch.sigmoid(CN._matvec(Ft, bt))
    gv = CN._wmatvec(Ft, wm * (yt - pr)) - reg * beta
    H = 0.25 * G0.copy() if step == 0 else CN._wgram(Ft, wm * pr * (1 - pr))
    H[np.diag_indices_from(H)] += reg
    beta = beta + CN._solve(H, gv, scale)
score = F.astype(np.float64) @ beta
log(f"in-sample {roc_auc_score(y, score):.4f} (reference) · frontier out-of-fold at k={K}: "
    f"{rp['auc_by_k'][str(K)] if str(K) in rp['auc_by_k'] else rp['knee_auc']:.4f}")

SPAN = (1598, 2200)
yr = lambda c: pd.to_numeric(c.str.slice(0, 4), errors="coerce")
inspan = ((yr(full.dob_a) >= SPAN[0]) & (yr(full.dob_a) <= SPAN[1])
          & (yr(full.dob_b) >= SPAN[0]) & (yr(full.dob_b) <= SPAN[1])).to_numpy()
rng = np.random.default_rng(20260901)
vsel = rng.choice(np.where(inspan)[0], 200, replace=False)
SOLO = {"natM", "natW", "aspM", "aspW", "midM", "midW"}
kinds = {t["kind"] for t in terms}
bl = rp["baselines"]
model = {
    "name": "till-death-" + "-".join(rp.get("families", ["model"])).lower(),
    "edition": "V — Till Death Do Us Part",
    "date": "2026-09-01",
    "zodiac": "sidereal (Lahiri), noon UT, birth dates only",
    "pair_only": not bool(kinds & SOLO),
    "families": rp.get("families"),
    "bodies": bodies,
    "servable_span": list(SPAN),
    "formula": "score = bias + sum_t w_t * trig_t(k_t * angle_t); p = sigmoid(score)",
    "terms": [{"kind": t["kind"], "i": t["i"], "j": t["j"], "k": t.get("k", 1),
               "trig": t["trig"], "label": t["label"], "folds": t["folds"],
               "w": float(beta[ix])} for ix, t in enumerate(terms)],
    "bias": float(beta[-1]),
    "cv_auc_broad": float(rp["auc_by_k"][str(K)]) if str(K) in rp["auc_by_k"] else float(rp["knee_auc"]),
    "baseline_him_only": bl["him_only"],
    "baseline_her_only": bl["her_only"],
    "n_corpus": int(n), "n_positive": int(y.sum()),
    "quantiles": [float(q) for q in np.quantile(score, np.linspace(0, 1, 401))],
    "verify": [{"dob_a": full.dob_a.iloc[int(i)], "dob_b": full.dob_b.iloc[int(i)],
                "score": float(score[i])} for i in vsel],
}
json.dump(model, open(OUT, "w"), indent=1)
log(f"wrote {OUT} ({os.path.getsize(OUT)//1024} KB) · pair_only={model['pair_only']} · kinds {sorted(kinds)}")
log(f"CV {model['cv_auc_broad']:.4f} · him {bl['him_only']:.4f} · her {bl['her_only']:.4f} -> "
    f"{model['cv_auc_broad'] - max(bl['him_only'], bl['her_only']):+.4f}")
