"""fit_export_final.py — the shipped artifact of the till-death phasor model.

One JSON, everything the browser needs and everything a stranger needs to check it:

  terms          the 48 surviving sin/cos terms — family, bodies, angle recipe, full-data weight
  bias           the full-data intercept (three-step closed-form Newton, balanced BCE, the
                 ablation's rl on the broad target)
  distribution   401 quantiles of the model score over all 175,155 couples — the browser places
                 a couple as a percentile of the real corpus, never a made-up scale
  verify         200 couples (dob pairs + float64 score) — the JS engine must reproduce these
                 before anything ships; a browser scorer that silently disagrees has burnt this
                 project before
"""
import json, os, re, time
import numpy as np, pandas as pd, torch
import fit_phasor_torch as P
import closed_newton as CN
from sklearn.metrics import roc_auc_score

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

rep = json.load(open(f"{D_}/report_ablation.json"))
FAMS, RL = rep["survivor_families"], rep["rel_lambda"]
terms = rep["terms"]
log(f"families {FAMS} · rl {RL} · {len(terms)} terms")

full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(np.float32)
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
tha, thb = Z["theta_a_train"], Z["theta_b_train"]
okb = ~np.isnan(tha).any(0) & ~np.isnan(thb).any(0)
names = [str(b) for b, o in zip(Z["bodies"], okb) if o]
keep = [i for i, nm in enumerate(names) if nm != "true_south_node"]
bod = [names[i] for i in keep]                 # canonical body ids for the JS engine
short = [b.replace("true_", "").replace("mean_", "") for b in bod]
ra, rb = np.deg2rad(tha[:, okb][:, keep]), np.deg2rad(thb[:, okb][:, keep])
NB = len(bod)
n = len(y)

# resolve each term name -> (kind, i, j, trig)
def parse(tname):
    m = re.match(r"(cos|sin)\((.*)\)$", tname)
    trig, inner = m.group(1), m.group(2)
    def bi(x): return short.index(x)
    if inner.startswith("D "):
        return {"trig": trig, "kind": "diff", "i": bi(inner[2:]), "j": None}
    if inner.startswith("his mid "):
        a, b = inner[8:].split("/"); return {"trig": trig, "kind": "midM", "i": bi(a), "j": bi(b)}
    if inner.startswith("her mid "):
        a, b = inner[8:].split("/"); return {"trig": trig, "kind": "midW", "i": bi(a), "j": bi(b)}
    if inner.startswith("his ") and "-" in inner[4:]:
        a, b = inner[4:].split("-"); return {"trig": trig, "kind": "aspM", "i": bi(a), "j": bi(b)}
    if inner.startswith("her ") and "-" in inner[4:]:
        a, b = inner[4:].split("-"); return {"trig": trig, "kind": "aspW", "i": bi(a), "j": bi(b)}
    if inner.startswith("his "):
        return {"trig": trig, "kind": "natM", "i": bi(inner[4:]), "j": None}
    if inner.startswith("her "):
        return {"trig": trig, "kind": "natW", "i": bi(inner[4:]), "j": None}
    if inner.startswith("mid "):
        return {"trig": trig, "kind": "sum", "i": bi(inner[4:]), "j": None}
    raise ValueError(tname)

def angle_of(t):
    k = t["kind"]; i, j = t["i"], t["j"]
    if k == "diff": return ra[:, i] - rb[:, i]
    if k == "natM": return ra[:, i]
    if k == "natW": return rb[:, i]
    if k == "sum":  return ra[:, i] + rb[:, i]
    if k == "aspM": return ra[:, i] - ra[:, j]
    if k == "aspW": return rb[:, i] - rb[:, j]
    if k == "midM": return ra[:, i] + ra[:, j]
    if k == "midW": return rb[:, i] + rb[:, j]

parsed = [parse(t["term"]) for t in terms]
cols = [np.cos(angle_of(t)) if t["trig"] == "cos" else np.sin(angle_of(t)) for t in parsed]
F = np.column_stack(cols + [np.ones(n)]).astype(np.float32)
Ft = torch.from_numpy(F).to(CN.DEV)
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)
wm = torch.from_numpy(w).to(CN.DEV)

# full-data closed-form fit at the ablation's rl (3-step Newton, exactly the shipped solver)
G0 = CN._wgram(Ft, wm)
scale = float(np.mean(np.diag(G0)[:-1]))
reg = np.full(F.shape[1], RL * scale); reg[-1] = 0.0
beta = np.zeros(F.shape[1])
yt = torch.from_numpy(y).to(CN.DEV)
for step in range(3):
    bt = torch.from_numpy(beta.astype(np.float32)).to(CN.DEV)
    z = CN._matvec(Ft, bt); pr = torch.sigmoid(z)
    gv = CN._wmatvec(Ft, wm * (yt - pr)) - reg * beta
    H = 0.25 * G0.copy() if step == 0 else CN._wgram(Ft, wm * pr * (1 - pr))
    H[np.diag_indices_from(H)] += reg
    beta = beta + CN._solve(H, gv, scale)
score = (F.astype(np.float64) @ beta)
auc_insample = float(roc_auc_score(y, score))
log(f"full-data fit: in-sample AUC {auc_insample:.4f} (reference only; CV is the claim: "
    f"{max(float(v) for v in rep['pruning_curve'].values()):.4f})")

# weights drift slightly from the ablation table (that one was the survivor-family design;
# this is the 48-term design) — the SHIPPED weights are these, self-consistent with the bias
qs = np.quantile(score, np.linspace(0, 1, 401))
# The verification couples must be ones the SHIPPED PAGE can actually chart: docs/ephem4.bin
# carries its ayanamsa from 1598 to 2200 and the shim REFUSES a date outside that span rather
# than clamping it. Sampling verify rows from the whole corpus would ship a self-test the page
# cannot run. The quantiles above stay over the WHOLE corpus — that is the model's reference
# population, and a percentile means "among all 175,155", including couples too old to re-chart.
yr_a = full.dob_a.str[:4].astype(int); yr_b = full.dob_b.str[:4].astype(int)
servable = np.where((yr_a >= 1600) & (yr_b >= 1600) & (yr_a <= 2195) & (yr_b <= 2195))[0]
rng = np.random.default_rng(20260901)
vsel = rng.choice(servable, 200, replace=False)
verify = [{"dob_a": full.dob_a.iloc[int(i)], "dob_b": full.dob_b.iloc[int(i)],
           "score": float(score[i])} for i in vsel]

model = {
    "name": "till-death-phasor",
    "edition": "V — Till Death Do Us Part",
    "date": "2026-09-01",
    "zodiac": "sidereal (Lahiri), noon UT, birth dates only",
    "bodies": short,
    "formula": "score = bias + sum_t w_t * trig_t(angle_t); p = sigmoid(score)",
    "angles": {"diff": "man[i] - woman[i]", "natM": "man[i]", "natW": "woman[i]",
               "sum": "man[i] + woman[i]", "aspM": "man[i] - man[j]", "aspW": "woman[i] - woman[j]",
               "midM": "man[i] + man[j]", "midW": "woman[i] + woman[j]"},
    "terms": [{**p, "w": float(beta[k]), "label": terms[k]["term"]}
              for k, p in enumerate(parsed)],
    "bias": float(beta[-1]),
    "cv_auc_broad": max(float(v) for v in rep["pruning_curve"].values()),
    "strict_five_seed": json.load(open(f"{D_}/report_model_variants.json"))["strict_mean"],
    "n_corpus": int(n), "n_positive": int(y.sum()),
    "servable_span": [1598, 2200],
    "verify_note": "sampled from couples the shipped ephemeris asset can chart (1598-2200)",
    "quantiles": [float(q) for q in qs],
    "verify": verify,
}
out = os.path.expanduser("~/Studio/artamatch/src/data/tilldeath_model.json")
json.dump(model, open(out, "w"), indent=1)
log(f"wrote {out} ({os.path.getsize(out)//1024} KB)")
