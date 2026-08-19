"""
artamodel_deploy.py — the deployable ArtaModel: 6-term, boosted over split single-sum fields (one phasor per
field), every stage recorded, serialised to JSON, and a scorer that needs only numpy.

Two fits are made:
  LEADERBOARD  fitted on the training rows that have both natal charts (9,553), applied to the 7,249 test rows;
               nothing from the answer key -- this is what goes to Kaggle.
  DEPLOYED     the same construction fitted on train + test (Arash: "the deployed model should be trained on all
               the data"), 9,553 + 7,249 rows; this is what goes to Hugging Face and to prod. It cannot be scored
               on the held-out set, because the held-out set is inside it -- the leaderboard fit is its estimate.

THE MODEL, term by term (see explain()): for each of fourteen bodies i and each of six terms,
    a_i  e^{i(θm_i − θd_i)}   mom's longitude minus dad's (synastry)
    m_i  e^{i(θt_i − θm_i)}   the wedding-day longitude minus mom's (the wedding transiting mom)
    d_i  e^{i(θt_i − θd_i)}   the wedding-day longitude minus dad's (the wedding transiting dad)
    mn_i e^{i θm_i}           mom's natal longitude
    dn_i e^{i θd_i}           dad's natal longitude
    tn_i e^{i θt_i}           the wedding-day longitude
θ sidereal (Lahiri) from Kerykeion, births at 09:00 local, the wedding at 12:00 UT. Each stage k of the boosted
model is ONE single-sum field u_k = |b_k + w_k z_j|² on ONE phasor j, chosen GREEDILY at that stage as the phasor
that best explains the current residual (so all 84 phasors of all six terms compete every time), added as
step_k · (α_k · u_k + c_k) to the logit; a term missing for a row (unknown wedding, unknown birth) contributes
zero. The score is the logit after the last stage; the probability is its sigmoid.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from artamodel import BODIES14, TERMS, phase_matrix                                          # noqa: E402
from artamodel_ensemble import Field, auc, cs                                                # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz")
OUT = os.environ.get("AQ_OUT", "/tmp/aq3sub")
os.makedirs(OUT, exist_ok=True)
TERM_TEXT = {"a": "mom's longitude minus dad's — the synastry angle between the two natal charts",
             "m": "the wedding-day longitude minus mom's natal longitude — the wedding sky transiting mom",
             "d": "the wedding-day longitude minus dad's natal longitude — the wedding sky transiting dad",
             "mn": "mom's own natal longitude", "dn": "dad's own natal longitude",
             "tn": "the wedding-day longitude itself"}
BODY_TEXT = {"sun": "Sun", "moon": "Moon", "mercury": "Mercury", "venus": "Venus", "mars": "Mars", "jupiter": "Jupiter",
             "saturn": "Saturn", "uranus": "Uranus", "neptune": "Neptune", "pluto": "Pluto", "true_node": "Rāhu (true north node)",
             "true_south_node": "Ketu (true south node)", "chiron": "Chiron", "mean_lilith": "Lilith (mean lunar apogee)"}


def pick_phasor(C, S, r, used_counts, K):
    """GREEDY stage selection: the phasor whose (cos, sin) best explain the current residual by least squares --
    the two-parameter proxy of the single-sum field -- so every term competes at every stage. A fixed cycle
    (stage k -> phasor k) with early stopping at ~37 stages had never even offered the natal and wedding-sky
    phasors, which sit last in the label order; that is not a six-term model."""
    best_j, best_r2 = 0, -1.0
    rc = r - r.mean()
    for j in range(K):
        X = np.column_stack([C[:, j], S[:, j]])
        Xc = X - X.mean(0)
        try:
            beta, *_ = np.linalg.lstsq(Xc, rc, rcond=None)
        except Exception:
            continue
        r2 = 1.0 - float(((rc - Xc @ beta) ** 2).sum()) / max(1e-12, float((rc ** 2).sum()))
        if r2 > best_r2:
            best_r2, best_j = r2, j
    return best_j


def boost_recorded(P, y, inner, stages, nu=0.1, seed=0):
    """Gradient boosting over split single-sum fields, ONE phasor per stage chosen greedily against the current
    residual, every stage recorded."""
    C, S = cs(P); K = C.shape[1]; fit = ~inner
    p0 = np.clip(y[fit].mean(), 1e-3, 1 - 1e-3); F0 = float(np.log(p0 / (1 - p0)))
    F = np.full(len(y), F0)
    rec = []; best, best_n, bad = -1.0, 0, 0
    used_counts = np.zeros(K, int)
    for k in range(stages):
        p = 1 / (1 + np.exp(-F)); r = y - p
        j = pick_phasor(C[fit], S[fit], r[fit], used_counts, K); used_counts[j] += 1
        mask = np.zeros(K); mask[j] = 1.0
        f = Field(K, seed * 1000 + k, mask).fit(C[fit], S[fit], r[fit], C[inner], S[inner], r[inner]) if inner.any() \
            else Field(K, seed * 1000 + k, mask).fit(C[fit], S[fit], r[fit], C[fit][:64], S[fit][:64], r[fit][:64])
        h = f.predict(C, S)
        best_g, best_loss = 0.0, np.inf
        for gam in (0.25, 0.5, 1.0, 2.0, 4.0):
            Fx = F[fit] + nu * gam * h[fit]
            loss = float(np.mean(np.logaddexp(0, -Fx * (2 * y[fit] - 1))))
            if loss < best_loss:
                best_loss, best_g = loss, gam
        F = F + nu * best_g * h
        rec.append({"stage": k + 1, "phasor": int(j), "step": nu * best_g, "alpha": float(f.alpha), "c": float(f.c),
                    "w_re": float(f.A1[j]), "w_im": float(-f.A2[j]), "b_re": float(f.br), "b_im": float(f.bi)})
        if inner.any():
            a = auc(y[inner], F[inner])
            if a > best + 1e-5:
                best, best_n, bad = a, k + 1, 0
            else:
                bad += 1
                if bad >= 10:
                    break
    n_keep = best_n if inner.any() else len(rec)
    return {"F0": F0, "stages": rec[:n_keep], "inner_auc": best if inner.any() else None}


def score(model, P):
    """The logit of the deployed model for phase matrix P (degrees; NaN = the term is absent). numpy only."""
    rad = np.pi / 180.0
    C, S = np.nan_to_num(np.cos(P * rad)), np.nan_to_num(np.sin(P * rad))
    F = np.full(len(P), model["F0"])
    for st in model["stages"]:
        j = st["phasor"]
        # z = e^{iφ}; w z = (wr + i wi)(C + i S) = (wr C − wi S) + i(wr S + wi C)
        Zr = st["w_re"] * C[:, j] - st["w_im"] * S[:, j] + st["b_re"]
        Zi = st["w_re"] * S[:, j] + st["w_im"] * C[:, j] + st["b_im"]
        u = Zr * Zr + Zi * Zi
        F = F + st["step"] * (st["alpha"] * u + st["c"])
    return F


def explain(model, labels):
    """Term-by-term account: every phasor's meaning, whether the deployed model uses it, and with what weight.
    The 'contribution' is Σ_stages step·|alpha|·|w|², the scale of the phasor's swing in the logit."""
    rows = {}
    for st in model["stages"]:
        lab = labels[st["phasor"]]; term, body = lab.split("_", 1)
        w = complex(st["w_re"], st["w_im"]); b = complex(st["b_re"], st["b_im"])
        r = rows.setdefault(lab, {"phasor": lab, "term": term, "body": BODY_TEXT.get(body, body),
                                   "meaning": f"{TERM_TEXT[term]}, for {BODY_TEXT.get(body, body)}",
                                   "stages": 0, "contribution": 0.0, "phase_deg": None})
        r["stages"] += 1
        r["contribution"] += abs(st["step"] * st["alpha"]) * abs(w) ** 2
        # the angle at which the field peaks: |b + w e^{iφ}|² is largest when arg(w) + φ = arg(b), i.e. φ* = arg(b) − arg(w)
        r["phase_deg"] = float(np.degrees(np.angle(b) - np.angle(w)) % 360.0)
    used = sorted(rows.values(), key=lambda r: -r["contribution"])
    unused = [lab for lab in labels if lab not in rows]
    return used, unused


def main():
    Z = np.load(PH, allow_pickle=True)
    bodies = list(Z["bodies"]); ids = Z["id_test"]; y = Z["y_train"].astype(np.int64)
    Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]
    Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    later = Z["yr_train"].astype(int).max(1)
    j1 = ptr[:, pn.index("start_is_jan1")] == 1.0; j1e = pte[:, pn.index("start_is_jan1")] == 1.0
    Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    B = [bodies.index(b) for b in BODIES14]
    charts = np.isfinite(Dtr[:, B]).all(1) & np.isfinite(Mtr[:, B]).all(1)
    P, labels = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, TERMS); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, TERMS)
    K = len(labels)
    # LEADERBOARD fit
    lat = later[charts]; inner = lat > np.quantile(lat, 0.85)
    lb = boost_recorded(P[charts], y[charts], inner, stages=4 * K, nu=0.1)
    s_lb = score(lb, Pe)
    print(f"  leaderboard fit: {int(charts.sum()):,} rows · {len(lb['stages'])} stages kept · inner {lb['inner_auc']:.4f}")
    from scipy.stats import rankdata
    r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)
    pd.DataFrame({"id": ids, "lasted_30_years": r01(s_lb)}).to_csv(f"{OUT}/submission_artamodel6.csv", index=False)
    json.dump({**lb, "labels": labels, "fitted_on": "train rows with both natal charts", "n_rows": int(charts.sum())},
              open(f"{OUT}/artamodel_leaderboard.json", "w"), indent=1)
    # DEPLOYED fit: train + test, the number of stages the leaderboard fit chose (no inner split possible)
    sol = pd.read_csv(os.environ.get("AQ_SOL", "/tmp/aq3comp/solution.csv")).set_index("id")
    yte = sol.loc[ids, "lasted_30_years"].to_numpy().astype(int)
    Pall = np.vstack([P[charts], Pe]); yall = np.concatenate([y[charts], yte])
    dep = boost_recorded(Pall, yall, np.zeros(len(yall), bool), stages=len(lb["stages"]), nu=0.1)
    dep.update({"labels": labels, "terms": list(TERMS), "bodies": BODIES14, "fitted_on": "train + test rows with both natal charts",
                "n_rows": int(len(yall)), "leaderboard_estimate": {"inner_auc": lb["inner_auc"], "note": "the same construction fitted on train alone; its held-out AUC is what the leaderboard reports"},
                "phase_convention": {"zodiac": "sidereal, Lahiri", "engine": "Kerykeion 5.12.9 (Swiss Ephemeris)", "birth_time": "09:00 local at the birthplace",
                                     "wedding_time": "12:00 UT", "presence_rule": "a term exists only when both of its phases exist; a missing phase contributes zero"}})
    used, unused = explain(dep, labels)
    dep["explanation"] = {"used": used, "unused": unused}
    json.dump(dep, open(f"{OUT}/artamodel_deployed.json", "w"), indent=1)
    print(f"  deployed fit: {len(yall):,} rows · {len(dep['stages'])} stages · {len(used)} phasors carry weight, {len(unused)} unused")
    print(f"  top phasors by contribution:")
    for r in used[:10]:
        print(f"    {r['phasor']:<20} {r['contribution']:8.3f}  peak at φ={r['phase_deg']:6.1f}°   {r['meaning'][:70]}")


if __name__ == "__main__":
    main()
