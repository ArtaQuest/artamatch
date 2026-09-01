"""fit_export_phasor.py — ship the lean phasor model, with the decomposition that qualifies it.

The model is the frontier's knee: the fewest phasors that reach the ceiling, each phasor contributing
a cos and a sin of one named angle at one harmonic, so its amplitude and phase are both free.

It also ships the numbers that say what the AUC is made of — the same search restricted to bodies
that cannot encode a century (Sun-Saturn) and to bodies that cannot encode a decade (Sun-Mars) — and
the two one-chart baselines. A page that prints a percentile without those is overclaiming, and the
verifier refuses a model file that omits them.
"""
import json, os, time
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
import closed_newton as CN

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_max"))
OUT = os.path.expanduser("~/.artaquest-dev/wt/am-build/docs/tilldeath.json")
K = int(os.environ.get("AQ_K", "5"))
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)

rp = json.load(open(f"{D_}/report_final.json"))
bl = json.load(open(f"{D_}/report_baselines_max.json"))
# READ THE NAMED FILES, AND PROVE THEY ARE DIFFERENT RUNS. fit_inner.py and fit_inner5.py both used
# to write report_inner.json, so the 5-body result silently overwrote the 7-body one and this file
# shipped 0.5193 for both. A one-off patch fixed the artefact and the next export undid it, which is
# what a fix outside the mechanism always does.
inner7 = json.load(open(f"{D_}/report_inner7.json"))
inner5 = json.load(open(f"{D_}/report_inner5.json"))
assert len(inner7["inner"]) == 7 and len(inner5["inner"]) == 5, \
    f"body counts wrong: {inner7['inner']} vs {inner5['inner']}"
assert abs(inner7["best"] - inner5["best"]) > 1e-6, \
    f"the two restricted runs report the SAME AUC ({inner7['best']}) — one overwrote the other"
phas = rp["frequency"][:K]
log(f"{K} phasors, agreed by {phas[0]['folds']}..{phas[-1]['folds']} of 10 folds")

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

def ang(t):
    i, j, k = t["i"], t["j"], t["kind"]
    if k == "xdiff": return A[:, i] - B[:, j]
    if k == "aspM":  return A[:, i] - A[:, j]
    if k == "aspW":  return B[:, i] - B[:, j]
    raise ValueError(k)

terms, cols = [], []
for t in phas:
    a = ang(t) * t["k"]
    for trig, v in (("cos", np.cos(a)), ("sin", np.sin(a))):
        terms.append({"kind": t["kind"], "i": t["i"], "j": t["j"], "k": t["k"], "trig": trig,
                      "label": f"{trig}({t['label']})", "fam": t["fam"], "folds": t["folds"]})
        cols.append(v)
F = np.column_stack(cols + [np.ones(n)]).astype(np.float32)
Ft = torch.from_numpy(F).to(CN.DEV)
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)
wm = torch.from_numpy(w).to(CN.DEV)
G0 = CN._wgram(Ft, wm); scale = float(np.mean(np.diag(G0)[:-1]))
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
log(f"in-sample {roc_auc_score(y, score):.4f} · frontier out-of-fold at k={K}: {rp['auc_by_k'][str(K)]:.4f}")

SPAN = (1598, 2200)
yr = lambda c: pd.to_numeric(c.astype(str).str.slice(0, 4), errors="coerce")
inspan = ((yr(full.dob_a) >= SPAN[0]) & (yr(full.dob_a) <= SPAN[1])
          & (yr(full.dob_b) >= SPAN[0]) & (yr(full.dob_b) <= SPAN[1])).to_numpy()
rng = np.random.default_rng(20260901)
vsel = rng.choice(np.where(inspan)[0], 200, replace=False)
SOLO = {"natM", "natW", "aspM", "aspW", "midM", "midW"}
model = {
    "name": "artamatch-children-phasor",
    "edition": "V — what the record remembers",
    "date": "2026-09-01",
    "zodiac": "sidereal (Lahiri), noon UT, birth dates only",
    "target": "children_recorded",
    "target_says": "whether the historical record lists children for a couple like this",
    "pair_only": not bool({t["kind"] for t in terms} & SOLO),
    "bodies": bodies,
    "servable_span": list(SPAN),
    "formula": "score = bias + sum over phasors of a*cos(k*angle) + c*sin(k*angle); p = sigmoid(score)",
    "angles": {"xdiff": "man[i] - woman[j]", "aspM": "man[i] - man[j]", "aspW": "woman[i] - woman[j]"},
    "n_phasors": K, "n_weights": len(terms) + 1,
    "terms": [{**t, "w": float(beta[ix])} for ix, t in enumerate(terms)],
    "bias": float(beta[-1]),
    # THE FIXED-TERM CV, not the frontier's value at this k. The frontier re-picks its terms inside
    # every fold and so scores a different (and slightly higher) thing than a model whose terms are
    # fixed in advance — which is what actually ships. Quoting the frontier's number here would
    # flatter the file by about 0.005.
    "cv_auc_broad": float(json.load(open(f"{D_}/report_lean.json"))["prefix"][str(K)]),
    "cv_auc_frontier_within_fold": float(rp["auc_by_k"][str(K)]) if str(K) in rp["auc_by_k"] else None,
    "baseline_him_only": bl["him_only"],
    "baseline_her_only": bl["her_only"],
    "baseline_age_gap": bl["age_gap"],
    # WHAT THE AUC IS MADE OF. The same search restricted to bodies that cannot encode a century,
    # then to bodies that cannot encode a decade. The page prints these next to every reading.
    "decomposition": {
        "all_13_bodies": float(rp["best"]),
        "fast_7_bodies_sun_to_saturn": float(inner7["best"]),
        "fast_5_bodies_sun_to_mars": float(inner5["best"]) if inner5 else None,
        "age_gap_2_params": bl["age_gap"],
        "note": ("Uranus, Neptune, Pluto, the node, Chiron and Lilith move over centuries, so their "
                 "positions identify when a person was born. Removing them takes the model from "
                 f"{rp['best']:.4f} to {inner7['best']:.4f}; removing Jupiter and Saturn as well "
                 f"takes it to {inner5['best'] if inner5 else float('nan'):.4f}, below the "
                 f"{bl['age_gap']:.4f} that two numbers of birth-date difference reach on their own."),
    },
    "n_corpus": int(n), "n_positive": int(y.sum()),
    "quantiles": [float(q) for q in np.quantile(score, np.linspace(0, 1, 401))],
    "verify": [{"dob_a": full.dob_a.iloc[int(i)], "dob_b": full.dob_b.iloc[int(i)],
                "score": float(score[i])} for i in vsel],
}
json.dump(model, open(OUT, "w"), indent=1)
log(f"wrote {OUT} ({os.path.getsize(OUT)//1024} KB) · {K} phasors, {len(terms)+1} weights")
for t in model["terms"]:
    log(f"    {t['w']:+.4f}  {t['fam']:<3} {t['label']}")
