"""
artamodel_iv.py — ArtaModel, FOURTH EDITION: genderless and even.

Operator 2026-08-19: "I want a genderless model from now on. so duplicate all the train and test data. (a, b, 1)
should also mean (b, a, 1) and add any longterm relationship to the dataset (including gay marriages and business
partnerships). also for each subtractive terms add abs to ensure each term is an even function. then start over the
competition."

    y = | b + Σᵢ aᵢ·e^{i|θ1ᵢ − θ2ᵢ|} + t1ᵢ·e^{i|θtᵢ − θ1ᵢ|} + t2ᵢ·e^{i|θtᵢ − θ2ᵢ|} + n1ᵢ·e^{iθ1ᵢ} + n2ᵢ·e^{iθ2ᵢ} + tnᵢ·e^{iθtᵢ} |²

θ1, θ2 = the two partners' sidereal (Lahiri) longitudes at 09:00 local at the birthplace, in the order the row
gives them (the files carry every pair in both orders, so the model is symmetric by the data); θt = the wedding
sky at 12:00 UT; every difference is the wrapped absolute value in [0°, 180°], so each term is an even function of
the swap; the presence rule is unchanged (a term exists only when both its phases exist).

Produces, from AQ_PHASES (kerykeion_phases.py on the edition-IV files):
  submission_plain_iv.csv      LightGBM on the two ages at the start, |gap|, start year     -- the bar
  submission_artamodel_iv.csv  the 6-term boosted-over-split construction (greedy, train-only fit)
  submission_ensemble_iv.csv   equal-weight rank average of the two
  artamodel_iv.json            every number the pages need (held out, age-cell-matched, pair-symmetry check)
  artamodel_iv_deployed.json   the same construction fitted on train + test, term by term
Every submission is SYMMETRISED: the two rows of a pair (p<n>a, p<n>b) receive the mean of their two scores.
Usage: AQ_PHASES=/tmp/aq4feat/phases.npz AQ_SOL=/tmp/aq4comp/solution.csv AQ_OUT=/tmp/aq4sub python artamodel_iv.py
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "coherent"))
from artamodel import BODIES14, TERMS_IV, auc, phase_matrix                    # noqa: E402
from artamodel_deploy import boost_recorded, score, BODY_TEXT                   # noqa: E402
from artamodel_full_stack import matched                                        # noqa: E402

PH = os.environ.get("AQ_PHASES", "/tmp/aq4feat/phases.npz"); SOL = os.environ.get("AQ_SOL", "/tmp/aq4comp/solution.csv")
OUT = os.environ.get("AQ_OUT", "/tmp/aq4sub"); T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
r01 = lambda v: (rankdata(v) - 1) / max(1.0, len(v) - 1)
TERM_TEXT_IV = {"a": "|θ1 − θ2|: the absolute synastry angle between the two natal charts (even under swap)",
                "t1": "|θt − θ1|: the wedding sky to partner 1's natal longitude", "t2": "|θt − θ2|: the wedding sky to partner 2's natal longitude",
                "n1": "partner 1's own natal longitude", "n2": "partner 2's own natal longitude", "tn": "the wedding-day longitude itself"}


def pair_key(ids):
    return np.array([i[:-1] if (i[-1] in "ab" and i[:-1].lstrip("p").isdigit()) else i for i in ids])


def symmetrise(ids, s):
    """Mean of the two orders of a pair — the genderless prediction; the two rows then carry the same score."""
    k = pair_key(ids); df = pd.DataFrame({"k": k, "s": s}); m = df.groupby("k")["s"].transform("mean").to_numpy()
    return m


def explain_iv(model, labels):
    rows = {}
    for st in model["stages"]:
        lab = labels[st["phasor"]]; term, body = lab.split("_", 1)
        w = complex(st["w_re"], st["w_im"]); b = complex(st["b_re"], st["b_im"])
        r = rows.setdefault(lab, {"phasor": lab, "term": term, "body": BODY_TEXT.get(body, body), "meaning": f"{TERM_TEXT_IV[term]}, for {BODY_TEXT.get(body, body)}",
                                   "stages": 0, "contribution": 0.0, "phase_deg": None})
        r["stages"] += 1; r["contribution"] += abs(st["step"] * st["alpha"]) * abs(w) ** 2
        r["phase_deg"] = float(np.degrees(np.angle(b) - np.angle(w)) % 360.0)
    used = sorted(rows.values(), key=lambda r: -r["contribution"]); unused = [l for l in labels if l not in rows]
    return used, unused


def main():
    import lightgbm as lgb
    os.makedirs(OUT, exist_ok=True)
    Z = np.load(PH, allow_pickle=True); s1, s2 = list(Z["slots"]); bodies = list(Z["bodies"]); ids = Z["id_test"]; y = Z["y_train"].astype(np.int64)
    Atr, Btr, Wtr = Z[f"theta_{s1}_train"], Z[f"theta_{s2}_train"], Z["theta_wed_train"]; Ate, Bte, Wte = Z[f"theta_{s1}_test"], Z[f"theta_{s2}_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); later = Z["yr_train"].astype(int).max(1)
    sol = pd.read_csv(SOL).set_index("id"); lab = [c for c in sol.columns if c != "Usage"][0]; yte = sol.loc[ids, lab].to_numpy().astype(int)
    j1 = ptr[:, pn.index("start_year_only")] == 1.0; j1e = pte[:, pn.index("start_year_only")] == 1.0; Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan
    log(f"train {len(y):,} rows · test {len(ids):,} rows ({len(set(pair_key(ids))):,} pairs) · slots {s1}/{s2}")
    # ---- plain: two ages, |gap|, start year (even by construction of |gap| and by the doubled rows) ----
    ia, ib, ig, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("age_gap"), pn.index("start_year")
    X = np.column_stack([ptr[:, ia], ptr[:, ib], np.abs(ptr[:, ig]), ptr[:, iy]]); Xe = np.column_stack([pte[:, ia], pte[:, ib], np.abs(pte[:, ig]), pte[:, iy]])
    prm = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=100, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, reg_lambda=10.0, verbose=-1)
    p_plain = np.zeros(len(Xe))
    for sd in range(3):
        c = lgb.LGBMClassifier(random_state=sd, **prm); c.fit(X, y); p_plain += c.predict_proba(Xe)[:, 1] / 3
    p_plain_s = symmetrise(ids, p_plain)
    ages = pte[:, [ia, ib]]; cell = (np.floor(np.nan_to_num(np.maximum(ages[:, 0], ages[:, 1])) / 3) * 1000 + np.floor(np.nan_to_num(np.minimum(ages[:, 0], ages[:, 1])) / 3)).astype(int)
    log(f"  plain: held {auc(yte, p_plain):.4f} (symmetrised {auc(yte, p_plain_s):.4f})  age-cell-matched {matched(yte, p_plain_s, cell):.4f}")
    # ---- ArtaModel IV: even phase matrix, 6 terms x 14 bodies ----
    B = [bodies.index(b) for b in BODIES14]
    P, labels = phase_matrix(Atr, Btr, Wtr, bodies, BODIES14, TERMS_IV, even=True); Pe, _ = phase_matrix(Ate, Bte, Wte, bodies, BODIES14, TERMS_IV, even=True)
    charts = np.isfinite(Atr[:, B]).all(1) & np.isfinite(Btr[:, B]).all(1)
    lat = later[charts]; inner = lat > np.quantile(lat, 0.85)
    lb = boost_recorded(P[charts], y[charts], inner, stages=4 * len(labels), nu=0.1)
    s_lb = score(lb, Pe); s_lb_s = symmetrise(ids, s_lb)
    log(f"  ArtaModel IV (leaderboard fit, {int(charts.sum()):,} full-chart rows, {len(lb['stages'])} stages, inner {lb['inner_auc']:.4f}): "
        f"held {auc(yte, s_lb):.4f} (symmetrised {auc(yte, s_lb_s):.4f})  age-cell-matched {matched(yte, s_lb_s, cell):.4f}")
    # symmetry check: how far apart are the two orders' raw scores? (0 = perfectly even model)
    k = pair_key(ids); df = pd.DataFrame({"k": k, "s": r01(s_lb)}); spread = df.groupby("k")["s"].agg(lambda v: abs(v.max() - v.min())).mean()
    log(f"  raw pair asymmetry of the ArtaModel ranks (mean |rank_a − rank_b|): {spread:.4f}")
    p_ens = 0.5 * r01(p_plain_s) + 0.5 * r01(s_lb_s)
    log(f"  ENSEMBLE plain + ArtaModel IV (equal-weight rank average): held {auc(yte, p_ens):.4f}  age-cell-matched {matched(yte, p_ens, cell):.4f}")
    for nm, v in (("plain_iv", p_plain_s), ("artamodel_iv", s_lb_s), ("ensemble_iv", p_ens)):
        pd.DataFrame({"id": ids, lab: r01(v)}).to_csv(os.path.join(OUT, f"submission_{nm}.csv"), index=False)
    used, unused = explain_iv(lb, labels)
    # ---- deployed: train + test full-chart rows, the number of stages the leaderboard fit chose ----
    charts_te = np.isfinite(Ate[:, B]).all(1) & np.isfinite(Bte[:, B]).all(1)
    Pall = np.vstack([P[charts], Pe[charts_te]]); yall = np.concatenate([y[charts], yte[charts_te]])
    dep = boost_recorded(Pall, yall, np.zeros(len(yall), bool), stages=len(lb["stages"]), nu=0.1)
    dused, dunused = explain_iv(dep, labels)
    dep.update({"edition": "IV — genderless, even", "labels": labels, "terms": list(TERMS_IV), "bodies": BODIES14, "fitted_on": "train + test rows with both natal charts (every pair in both orders)",
                "n_rows": int(len(yall)), "leaderboard_estimate": {"inner_auc": lb["inner_auc"], "held_out_auc": float(auc(yte, s_lb_s)), "note": "the same construction fitted on train alone, symmetrised over the pair"},
                "phase_convention": {"zodiac": "sidereal, Lahiri", "engine": "Kerykeion 5.12.9 (Swiss Ephemeris)", "birth_time": "09:00 local at the birthplace", "wedding_time": "12:00 UT",
                                     "even": "every phase difference is the wrapped absolute value |Δθ| in [0°, 180°]", "order": "slot 1 / slot 2 carry no meaning; score both orders and average",
                                     "presence_rule": "a term exists only when both of its phases exist; a missing phase contributes zero"},
                "explanation": {"used": dused, "unused": dunused}})
    json.dump(dep, open(os.path.join(OUT, "artamodel_iv_deployed.json"), "w"), indent=1)
    R = {"edition": "IV", "n_train_rows": int(len(y)), "n_test_rows": int(len(ids)), "n_test_pairs": int(len(set(k))), "n_full_chart_train_rows": int(charts.sum()),
         "plain": {"held": float(auc(yte, p_plain_s)), "age_cell_matched": float(matched(yte, p_plain_s, cell))},
         "artamodel": {"held": float(auc(yte, s_lb_s)), "held_raw": float(auc(yte, s_lb)), "age_cell_matched": float(matched(yte, s_lb_s, cell)), "inner": lb["inner_auc"], "stages": len(lb["stages"]),
                       "phasors_used": [u["phasor"] for u in used], "pair_asymmetry": float(spread)},
         "ensemble": {"held": float(auc(yte, p_ens)), "age_cell_matched": float(matched(yte, p_ens, cell))},
         "terms": {t: TERM_TEXT_IV[t] for t in TERMS_IV}, "labels": labels, "leaderboard": {**lb, "labels": labels}}
    json.dump(R, open(os.path.join(OUT, "artamodel_iv.json"), "w"), indent=1)
    log(f"  deployed fit: {len(yall):,} rows · {len(dep['stages'])} stages · phasors used: {', '.join(u['phasor'] for u in dused)}")
    log(f"wrote {OUT}/submission_{{plain,artamodel,ensemble}}_iv.csv, artamodel_iv.json, artamodel_iv_deployed.json")


if __name__ == "__main__":
    main()
