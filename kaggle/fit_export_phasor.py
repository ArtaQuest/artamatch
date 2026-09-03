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
# THE MAX-OUT MODEL SHIPS WHEN IT EXISTS (operator 2026-09-01: "max out auc" + every fast body in).
# Its terms come from the all-data deploy pass of fit_nested.py; the number quoted for it is the
# NESTED cross-validated AUC — selection, K choice and the forced fast bodies all inside the loop —
# because the fixed-structure CV of a structure chosen on all folds is leak-inflated (measured: the
# prefix scan of the agreement list creeps monotonically and never turns over).
mx = rn = None
TERMS_FILE = os.environ.get("AQ_TERMS", "maxout_terms_k32.json")
NESTED_FILE = TERMS_FILE.replace("maxout_terms", "report_nested")
if os.path.exists(f"{D_}/{TERMS_FILE}"):
    mx = json.load(open(f"{D_}/{TERMS_FILE}"))
    rn = json.load(open(f"{D_}/{NESTED_FILE}"))
    phas = [{**t, "folds": None} for t in mx["met"]]
    K = len(phas)
    log(f"{K} phasors from the nested deploy pass · nested AUC {rn['nested_auc']:.4f}")
else:
    phas = rp["frequency"][:K]
    log(f"{K} phasors, agreed by {phas[0]['folds']}..{phas[-1]['folds']} of 10 folds")
RL = mx["rl"] if mx else rp["rl"]

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

import re as _re
def lin_coef(label):
    """the coefficient vector of an interaction label such as
    '(his neptune - her neptune) + (his saturn - her saturn)': {"his:neptune": 1, "her:neptune": -1, ...}.
    The competition's second-order phasors carry their algebra only in the label; the scorer's
    general 'lin' kind takes exactly this dict."""
    coef = {}
    outer_sign = 1
    for piece in _re.split(r"\)\s*([+-])\s*\(", label.strip()):
        if piece in ("+", "-"): outer_sign = 1 if piece == "+" else -1; continue
        piece = piece.strip("() ")
        for m in _re.finditer(r"([+-]?)\s*(his|her)\s+([a-z_]+)", piece):
            sgn = -1 if m.group(1) == "-" else 1
            key = f"{m.group(2)}:{m.group(3)}"
            coef[key] = coef.get(key, 0) + outer_sign * sgn
    return {k: v for k, v in coef.items() if v}
def ang(t):
    i, j, k = t["i"], t["j"], t["kind"]
    if k == "xdiff": return A[:, i] - B[:, j]
    if k == "aspM":  return A[:, i] - A[:, j]
    if k == "aspW":  return B[:, i] - B[:, j]
    if k in ("int+", "int-", "lin"):
        coef = t.get("coef") or lin_coef(t["label"].split("*(", 1)[-1].rstrip(")") if t["label"].startswith(tuple("0123456789")) else t["label"])
        out = np.zeros(n)
        for key, c in coef.items():
            side, body = key.split(":", 1); out += c * (A if side == "his" else B)[:, bodies.index(body)]
        t["kind"] = "lin"; t["coef"] = coef
        return out
    raise ValueError(k)

terms, cols = [], []
for t in phas:
    a = ang(t) * t["k"]
    for trig, v in (("cos", np.cos(a)), ("sin", np.sin(a))):
        terms.append({"kind": t["kind"], "i": t["i"], "j": t["j"], "k": t["k"], "trig": trig,
                      "label": f"{trig}({t['label']})", "fam": t["fam"], "folds": t["folds"],
                      **({"coef": t["coef"]} if t["kind"] == "lin" else {})})
        cols.append(v)
F = np.column_stack(cols + [np.ones(n)]).astype(np.float32)
Ft = torch.from_numpy(F).to(CN.DEV)
w = np.where(y > 0, n / (2 * y.sum()), n / (2 * (n - y.sum()))).astype(np.float32)
wm = torch.from_numpy(w).to(CN.DEV)
G0 = CN._wgram(Ft, wm); scale = float(np.mean(np.diag(G0)[:-1]))
reg = np.full(F.shape[1], RL * scale); reg[-1] = 0.0
beta = np.zeros(F.shape[1]); yt = torch.from_numpy(y).to(CN.DEV)
# NEWTON TO CONVERGENCE, each step an exact solve. Three fixed steps were proven not enough at 35
# phasors (train AUC 0.6413 vs the gradient solution's 0.6859 on the same objective); the number of
# steps is decided by the gradient collapsing, and an unconverged fit refuses to export.
# ... and each step is DAMPED: halved until the penalised loss actually falls. A full step on a
# deep design overshot into saturation during the nested runs and left a constant-painting fit.
def _ploss(b):
    bt = torch.from_numpy(b.astype(np.float32)).to(CN.DEV)
    l = (wm * torch.nn.functional.binary_cross_entropy_with_logits(CN._matvec(Ft, bt), yt, reduction="none")).sum()
    return float(l) + 0.5 * float((reg * b * b).sum())
cur = _ploss(beta); g0 = gn = None
for step in range(25):
    bt = torch.from_numpy(beta.astype(np.float32)).to(CN.DEV)
    pr = torch.sigmoid(CN._matvec(Ft, bt))
    gv = CN._wmatvec(Ft, wm * (yt - pr)) - reg * beta
    gn = float(np.max(np.abs(gv)))
    if g0 is None: g0 = gn or 1.0
    if step >= 3 and gn < 1e-5 * g0: break
    H = 0.25 * G0.copy() if step == 0 else CN._wgram(Ft, wm * pr * (1 - pr))
    H[np.diag_indices_from(H)] += reg
    delta = CN._solve(H, gv, scale)
    t, took = 1.0, False
    while t >= 1 / 64:
        cand = beta + t * delta
        lc = _ploss(cand)
        if np.isfinite(lc) and lc <= cur + 1e-9 * abs(cur):
            beta, cur, took = cand, lc, True; break
        t /= 2
    if not took: break
assert gn < 1e-3 * g0, f"export refit did not converge: |g| {gn:.3g} vs start {g0:.3g}"
score = F.astype(np.float64) @ beta
log(f"in-sample {roc_auc_score(y, score):.4f} (converged in {step+1} Newton steps)")

# THE TARGET IS NAMED BY THE CORPUS DIRECTORY (operator 2026-09-03, the success target), never by
# copy: the artifact carries what the number means, and the page reads it from there.
_T = os.path.basename(D_.rstrip("/"))
TARGET_META = {
    "success": {"name": "artamatch-success-phasor", "target": "lasted_with_children",
                "says": "whether a marriage like this lasted — no separation in the record — and had children",
                "question": "did a marriage like this last — no separation in the record — and have children",
                "positive": "toward lasting with children"},
    "success_strict": {"name": "artamatch-success-strict-phasor", "target": "lasted_with_children_strict",
                "says": "whether a marriage like this lasted — no explicit end, no end date before a death, no remarriage — and had children",
                "question": "did a marriage like this last — no explicit end, no end date before a death, no remarriage — and have children",
                "positive": "toward lasting with children"},
    "prosper2": {"name": "artamatch-prosper2-phasor", "target": "lasted_with_two_or_more_children",
                "says": "whether a marriage like this lasted and had two or more children",
                "question": "did a marriage like this last and have two or more children",
                "positive": "toward lasting with children"},
}.get(_T, {"name": "artamatch-children-phasor", "target": "children_recorded",
           "says": "whether the historical record lists children for a couple like this",
           "question": "did the historical record list children for a couple like this",
           "positive": "toward children in the record"})
SPAN = (1598, 2200)
_LAB = os.path.expanduser("~/.artamatch-dev/labels.csv")
_labels = dict(pd.read_csv(_LAB, dtype=str).fillna("").itertuples(index=False, name=None)) if os.path.exists(_LAB) else {}
dec_of = (pd.to_numeric(full.dob_a.astype(str).str.slice(0, 4), errors="coerce").fillna(0) // 10 * 10).astype(int).to_numpy()
yr = lambda c: pd.to_numeric(c.astype(str).str.slice(0, 4), errors="coerce")
inspan = ((yr(full.dob_a) >= SPAN[0]) & (yr(full.dob_a) <= SPAN[1])
          & (yr(full.dob_b) >= SPAN[0]) & (yr(full.dob_b) <= SPAN[1])).to_numpy()
rng = np.random.default_rng(20260901)
vsel = rng.choice(np.where(inspan)[0], 200, replace=False)
SOLO = {"natM", "natW", "aspM", "aspW", "midM", "midW"}
model = {
    "name": TARGET_META["name"],
    "edition": "V — what the record remembers",
    "date": "2026-09-01",
    "zodiac": "sidereal (Lahiri), noon UT, birth dates only",
    "target": TARGET_META["target"],
    "target_says": TARGET_META["says"],
    "target_positive": TARGET_META["positive"],
    "target_question": TARGET_META["question"],
    "pair_only": not bool({t["kind"] for t in terms} & SOLO),
    "bodies": bodies,
    "servable_span": list(SPAN),
    "formula": "score = bias + sum over phasors of a*cos(k*angle) + c*sin(k*angle); p = sigmoid(score)",
    "angles": {"xdiff": "man[i] - woman[j]", "aspM": "man[i] - man[j]", "aspW": "woman[i] - woman[j]"},
    "n_phasors": K, "n_weights": len(terms) + 1,
    # the candidate bank (from the terms file when the run recorded it, else from AQ_BANK_* for a
    # run made before the field existed — always explicit, never inferred from a filename)
    "bank": (mx.get("bank") if mx and mx.get("bank") else
             {"families": os.environ["AQ_BANK_FAMS"].split(","), "harmonics": [int(x) for x in os.environ["AQ_BANK_HARMS"].split(",")],
              "n_candidates": int(os.environ["AQ_BANK_N"]), "systems": False, "ortho": True}) if mx else None,
    "terms": [{**t, "w": float(beta[ix])} for ix, t in enumerate(terms)],
    "bias": float(beta[-1]),
    # THE FIXED-TERM CV, not the frontier's value at this k. The frontier re-picks its terms inside
    # every fold and so scores a different (and slightly higher) thing than a model whose terms are
    # fixed in advance — which is what actually ships. Quoting the frontier's number here would
    # flatter the file by about 0.005.
    "cv_auc_broad": float(rn["nested_auc"]) if rn else
                    float(json.load(open(f"{D_}/report_lean.json"))["prefix"][str(K)]),
    "cv_note": ("nested 10-fold: stepwise selection, the choice of how many phasors, and the "
                "forced-in fast bodies were all re-run inside every training fold, so this number "
                "never saw its own test couples") if rn else "fixed-term 10-fold CV",
    "cv_auc_fixed_structure_reference": float(rn["deploy"]["fixed_cv_reference"]) if rn else None,
    "closed_vs_gradient": rn["deploy"]["closed_vs_gradient"] if rn else None,
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
    # ERA-CONDITIONED QUANTILES (operator 2026-09-02, "keep improving"): most of the score is the
    # birth calendar, so a couple born in the 1990s is capped near the middle of the ALL-couples
    # distribution by Neptune's position alone. Ranking them among couples whose husband was born
    # in the same decade removes that cap and answers the fairer question. 101 quantiles per
    # decade with at least 200 couples; the page shows both numbers and says which is which.
    "quantiles_by_decade": {str(dec): [float(q) for q in np.quantile(score[dec_of == dec], np.linspace(0, 1, 101))]
                            for dec in sorted(set(dec_of)) if (dec_of == dec).sum() >= 200},
    # the replay couples carry their names too, so a model with name pseudo-bodies can be gated
    # by the same shim replay (the labels file is the corpus builder's; absent -> "")
    "verify": [{"dob_a": full.dob_a.iloc[int(i)], "dob_b": full.dob_b.iloc[int(i)],
                "name_a": _labels.get(full.pid_a.iloc[int(i)], ""), "name_b": _labels.get(full.pid_b.iloc[int(i)], ""),
                "score": float(score[i])} for i in vsel],
}
json.dump(model, open(OUT, "w"), indent=1)
log(f"wrote {OUT} ({os.path.getsize(OUT)//1024} KB) · {K} phasors, {len(terms)+1} weights")
for t in model["terms"]:
    log(f"    {t['w']:+.4f}  {t['fam']:<3} {t['label']}")
