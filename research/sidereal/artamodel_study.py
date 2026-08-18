"""
artamodel_study.py — ArtaModel studied from every angle, on FIXED populations.

Every experiment fixes the row population first and varies one thing, because a term whose presence rule admits
new rows changes the population as well as the formula -- the six-term collapse to 0.50 was ambiguous for exactly
that reason. Every choice is made on an inner TEMPORAL split of the training rows; the held-out column is read
for the record. This study reads the held-out labels many times; nothing here is submitted, and any number a
reader wants to trust should be re-run on a fresh split.

Populations (third-edition gendered data):
  FULL    both natal charts complete (day-precision births, both places) AND the wedding day known
  CHARTS  both natal charts complete; the wedding may be a year-only record (its terms drop)
  ANY     any row with at least one phasor

Usage: AQ_SRC=/tmp/aq3 AQ_PHASES=/tmp/aq3feat/phases.npz AQ_SOL=/tmp/aq3comp/solution.csv AQ_OUT=/tmp/aq3feat python artamodel_study.py
"""
import itertools
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from artamodel import ANGLES, BODIES14, GROUPS, TERMS, TERMS8, ArtaModel, auc, fit_ensemble, phase_matrix   # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq3")
PH = os.environ.get("AQ_PHASES", "/tmp/aq3feat/phases.npz")
SOL = os.environ.get("AQ_SOL", "/tmp/aq3comp/solution.csv")
OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat")
QUICK = bool(os.environ.get("AQ_QUICK"))
T0 = time.time()
R = {}                                                   # every result, keyed by experiment


def log(*a):
    print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


def matched(y, s, band):
    num = den = 0.0
    for b in np.unique(band):
        m = band == b
        n1, n0 = int(y[m].sum()), int((1 - y[m]).sum())
        if n1 and n0:
            num += auc(y[m], s[m]) * n1 * n0; den += n1 * n0
    return num / den if den else float("nan")


def main():
    Z = np.load(PH, allow_pickle=True)
    bodies = list(Z["bodies"]); ids = Z["id_test"]; ytr = Z["y_train"].astype(np.int64)
    Dtr, Mtr, Wtr = Z["theta_dad_train"], Z["theta_mom_train"], Z["theta_wed_train"]
    Dte, Mte, Wte = Z["theta_dad_test"], Z["theta_mom_test"], Z["theta_wed_test"]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"])
    later = Z["yr_train"].astype(int).max(1)
    sol = pd.read_csv(SOL).set_index("id"); lab = [c for c in sol.columns if c != "Usage"][0]
    yte = sol.loc[ids, lab].to_numpy().astype(int)
    j1 = ptr[:, pn.index("start_is_jan1")] == 1.0; j1e = pte[:, pn.index("start_is_jan1")] == 1.0
    Wtr = Wtr.copy(); Wte = Wte.copy(); Wtr[j1] = np.nan; Wte[j1e] = np.nan       # a year-only wedding has no sky
    B = [bodies.index(b) for b in BODIES14]
    charts_tr = np.isfinite(Dtr[:, B]).all(1) & np.isfinite(Mtr[:, B]).all(1)
    charts_te = np.isfinite(Dte[:, B]).all(1) & np.isfinite(Mte[:, B]).all(1)
    wed_tr = np.isfinite(Wtr[:, B]).all(1); wed_te = np.isfinite(Wte[:, B]).all(1)
    POP = {"FULL": (charts_tr & wed_tr, charts_te & wed_te), "CHARTS": (charts_tr, charts_te),
           "ANY": (np.ones(len(ytr), bool), np.ones(len(yte), bool))}
    for k, (a, b) in POP.items():
        log(f"population {k:<6} train {int(a.sum()):,} · held out {int(b.sum()):,}")
    ages_tr = ptr[:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]
    ages_te = pte[:, [pn.index("age_dad_at_start"), pn.index("age_mom_at_start")]]
    gap_te = pte[:, pn.index("age_gap")]

    def run(name, terms, bods, pop="FULL", F=1, l2=1e-3, seeds=3, angles=False, D=(Dtr, Dte), M=(Mtr, Mte), W=(Wtr, Wte),
            harmonic=1.0, record=True):
        mtr, mte = POP[pop]
        P, labels = phase_matrix(D[0], M[0], W[0], bodies, bods, terms, angles)
        Pe, _ = phase_matrix(D[1], M[1], W[1], bodies, bods, terms, angles)
        if harmonic != 1.0:
            P, Pe = P * harmonic, Pe * harmonic
        ok = mtr & np.isfinite(P).any(1) if pop == "ANY" else mtr
        oke = mte & np.isfinite(Pe).any(1) if pop == "ANY" else mte
        y, ye = ytr[ok], yte[oke]; lat = later[ok]; inner = lat > np.quantile(lat, 0.85)
        iv, s = fit_ensemble(P[ok], y, inner, Pe[oke], seeds=seeds, terms=terms, bodies=bods, F=F, l2=l2, angles_in_natal=angles)
        a = auc(ye, s)
        row = {"terms": list(terms), "bodies": len(bods), "pop": pop, "F": F, "l2": l2, "n_train": int(ok.sum()),
               "n_test": int(oke.sum()), "phasors": len(labels), "inner": iv, "held": a}
        if record:
            R[name] = row
        return row, s, oke

    # ── E0. references per population: the plain columns, boosted, on the same rows ─────────────────────────
    from sklearn.ensemble import HistGradientBoostingClassifier
    for pop, (mtr, mte) in POP.items():
        cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
        Xtr, Xte = ptr[mtr][:, cols], pte[mte][:, cols]
        pr = np.zeros(len(Xte))
        for sd in range(3):
            c = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0,
                                               early_stopping=True, validation_fraction=0.15, random_state=sd).fit(Xtr, ytr[mtr])
            pr += c.predict_proba(Xte)[:, 1]
        ad = auc(yte[mte], -Xte[:, 0])
        R[f"E0 reference {pop}"] = {"pop": pop, "held": auc(yte[mte], pr / 3), "dad_age_alone": max(ad, 1 - ad),
                                    "n_test": int(mte.sum())}
        log(f"E0 {pop}: plain boosted {auc(yte[mte], pr/3):.4f} · dad's age alone {max(ad,1-ad):.4f}")

    # ── E1. every subset of the six terms, FULL population, F=1 ─────────────────────────────────────────────
    subsets = [c for r in range(1, 7) for c in itertools.combinations(TERMS, r)]
    if QUICK:
        subsets = [("a",), ("m", "d"), ("a", "m", "d"), ("mn", "dn"), ("tn",), ("a", "m", "d", "mn", "dn"), TERMS]
    for i, sub in enumerate(subsets):
        row, _, _ = run(f"E1 terms {'+'.join(sub)}", sub, BODIES14, "FULL", F=1, seeds=2)
        if i % 8 == 0 or len(sub) in (3, 6):
            log(f"E1 {'+'.join(sub):<22} inner {row['inner']:.4f} held {row['held']:.4f}")
    # the composite terms (Davison-style midpoints), added on 2026-08-18: alone, with the three, with all
    for sub in (("c",), ("c", "tc"), ("a", "c"), ("a", "m", "d", "c"), ("a", "m", "d", "c", "tc"), TERMS + ("c",), TERMS8):
        row, _, _ = run(f"E1 terms {'+'.join(sub)}", sub, BODIES14, "FULL", F=1, seeds=2)
        log(f"E1 {'+'.join(sub):<26} inner {row['inner']:.4f} held {row['held']:.4f}")
    # the same ladder at F=8 for the main rungs
    for sub in (("a",), ("a", "m", "d"), ("a", "m", "d", "mn", "dn"), TERMS, ("a", "m", "d", "c", "tc"), TERMS8):
        row, _, _ = run(f"E1 F8 terms {'+'.join(sub)}", sub, BODIES14, "FULL", F=8, seeds=2)
        log(f"E1 F=8 {'+'.join(sub):<22} inner {row['inner']:.4f} held {row['held']:.4f}")

    # ── E2. populations: the same formula on FULL / CHARTS / ANY ────────────────────────────────────────────
    for sub in (("a", "m", "d"), TERMS, ("a", "m", "d", "c", "tc"), TERMS8):
        for pop in ("FULL", "CHARTS", "ANY"):
            row, _, _ = run(f"E2 pop {pop} terms {'+'.join(sub)}", sub, BODIES14, pop, F=1, seeds=2)
            log(f"E2 {pop:<6} {'+'.join(sub):<18} n {row['n_train']:>6,}/{row['n_test']:>5,} inner {row['inner']:.4f} held {row['held']:.4f}")

    # ── E3. bodies: drop-one, only-one, groups, classical sets (FULL, both 3-term and 6-term) ────────────────
    for sub, tag in ((("a", "m", "d"), "3"), (TERMS, "6")):
        base, _, _ = run(f"E3 {tag}-term all 14 bodies", sub, BODIES14, "FULL", F=1, seeds=2)
        for b in BODIES14:
            row, _, _ = run(f"E3 {tag}-term drop {b}", sub, [x for x in BODIES14 if x != b], "FULL", F=1, seeds=2)
            R[f"E3 {tag}-term drop {b}"]["delta_vs_all"] = row["held"] - base["held"]
        for b in BODIES14:
            row, _, _ = run(f"E3 {tag}-term only {b}", sub, [b], "FULL", F=1, seeds=2)
        for g, bl in GROUPS.items():
            if g == "angles":
                continue
            row, _, _ = run(f"E3 {tag}-term only {g}", sub, bl, "FULL", F=1, seeds=2)
            row2, _, _ = run(f"E3 {tag}-term drop {g}", sub, [x for x in BODIES14 if x not in bl], "FULL", F=1, seeds=2)
        for nm, bl in (("classical7", BODIES14[:7]), ("modern10", BODIES14[:10]), ("slow5", ["jupiter", "saturn", "uranus", "neptune", "pluto"]),
                       ("fast5", ["sun", "moon", "mercury", "venus", "mars"])):
            run(f"E3 {tag}-term set {nm}", sub, bl, "FULL", F=1, seeds=2)
        log(f"E3 {tag}-term ablations done")

    # ── E4. angles in the natal/synastry terms ─────────────────────────────────────────────────────────────
    for sub in (("a",), ("a", "m", "d"), TERMS):
        run(f"E4 angles + {'+'.join(sub)}", sub, BODIES14, "FULL", F=1, seeds=2, angles=True)
    log("E4 done")

    # ── E5. harmonics: the phases multiplied by h (squares, trines, quarters) and a mixed bank ─────────────
    for h in (2.0, 3.0, 4.0):
        run(f"E5 harmonic {int(h)} terms a+m+d", ("a", "m", "d"), BODIES14, "FULL", F=1, seeds=2, harmonic=h)
        run(f"E5 harmonic {int(h)} terms all", TERMS, BODIES14, "FULL", F=1, seeds=2, harmonic=h)
    log("E5 done")

    # ── E6. fields and regularisation, seeds spread ─────────────────────────────────────────────────────────
    for F in ([1, 8] if QUICK else [1, 2, 4, 8, 16, 32, 64]):
        for l2 in ([1e-3] if QUICK else [1e-4, 1e-3, 1e-2, 1e-1]):
            run(f"E6 3-term F={F} l2={l2:g}", ("a", "m", "d"), BODIES14, "FULL", F=F, l2=l2, seeds=2)
    seeds_held = []
    for sd in range(10):
        am = ArtaModel(terms=("a", "m", "d"), bodies=BODIES14, F=1, seed=sd)
        P, _ = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, ("a", "m", "d")); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, ("a", "m", "d"))
        mtr, mte = POP["FULL"]; lat = later[mtr]; inner = lat > np.quantile(lat, 0.85)
        am.fit(P[mtr], ytr[mtr], inner); seeds_held.append(auc(yte[mte], am.score(Pe[mte])))
    R["E6 3-term F=1 seed spread"] = {"held_mean": float(np.mean(seeds_held)), "held_sd": float(np.std(seeds_held)), "seeds": seeds_held}
    log(f"E6 seeds: 3-term F=1 held out {np.mean(seeds_held):.4f} +- {np.std(seeds_held):.4f} over 10 seeds")

    # ── E7. controls: does the model carry anything beyond the ages and the gap? (FULL, 3-term and 6-term) ──
    mtr, mte = POP["FULL"]
    for sub, tag in ((("a", "m", "d"), "3-term"), (TERMS, "6-term"), (("a", "m", "d", "c", "tc"), "3+composite"), (TERMS8, "8-term")):
        row, s, oke = run(f"E7 {tag} for controls", sub, BODIES14, "FULL", F=1, seeds=3, record=False)
        y = yte[oke]; A = ages_te[oke]; g = gap_te[oke]
        cell = (np.floor(A[:, 0] / 3) * 1000 + np.floor(A[:, 1] / 3)).astype(int)
        gb = np.floor(np.abs(g) / 2).astype(int)
        # the reference and a combiner FITTED ON TRAIN: does adding the model beat the reference?
        cols = [pn.index(c) for c in ("age_dad_at_start", "age_mom_at_start", "age_gap", "start_year")]
        Xtr, Xte = ptr[mtr][:, cols], pte[mte][:, cols]
        Ptr_, _ = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, sub); Pte_, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, sub)
        lat = later[mtr]; inner = lat > np.quantile(lat, 0.85)
        # out-of-fold model score on train (2 halves by time) so the combiner is not fitted on in-sample scores
        s_tr = np.zeros(int(mtr.sum()))
        for half in (0, 1):
            fitm = np.arange(int(mtr.sum())) % 2 == half
            am = ArtaModel(terms=sub, bodies=BODIES14, F=1).fit(Ptr_[mtr][fitm], ytr[mtr][fitm], inner[fitm]); s_tr[~fitm] = am.score(Ptr_[mtr][~fitm])
        am_full = ArtaModel(terms=sub, bodies=BODIES14, F=1).fit(Ptr_[mtr], ytr[mtr], inner); s_te = am_full.score(Pte_[mte])
        pr_ref = np.zeros(len(Xte)); pr_both = np.zeros(len(Xte))
        for sd in range(3):
            c = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0, early_stopping=True, validation_fraction=0.15, random_state=sd)
            pr_ref += c.fit(Xtr, ytr[mtr]).predict_proba(Xte)[:, 1]
            c2 = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0, early_stopping=True, validation_fraction=0.15, random_state=sd)
            pr_both += c2.fit(np.column_stack([Xtr, s_tr]), ytr[mtr]).predict_proba(np.column_stack([Xte, s_te]))[:, 1]
        R[f"E7 {tag} controls"] = {"held": auc(y, s), "age_cell_matched": matched(y, s, cell), "gap_matched": matched(y, s, gb),
                                   "reference": auc(y, pr_ref / 3), "reference_plus_model": auc(y, pr_both / 3),
                                   "n_age_cells": int(len(np.unique(cell)))}
        log(f"E7 {tag}: held {auc(y,s):.4f} · age-cell-matched {matched(y,s,cell):.4f} · gap-matched {matched(y,s,gb):.4f} · "
            f"reference {auc(y,pr_ref/3):.4f} · reference+model {auc(y,pr_both/3):.4f}")

    # ── E8. anatomy: the fitted weights of the F=1 models on FULL ──────────────────────────────────────────
    for sub, tag in ((("a", "m", "d"), "3-term"), (TERMS, "6-term"), (TERMS8, "8-term")):
        P, labels = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, sub); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, sub)
        lat = later[mtr]; inner = lat > np.quantile(lat, 0.85)
        ws = []
        for sd in range(3):
            am = ArtaModel(terms=sub, bodies=BODIES14, F=1, seed=sd).fit(P[mtr], ytr[mtr], inner)
            ws.append(am.weights(labels))
        anat = {k: {"modulus_mean": float(np.mean([w[k][0] for w in ws])), "modulus_sd": float(np.std([w[k][0] for w in ws])),
                    "phase_deg": [round(w[k][1], 1) for w in ws]} for k in ws[0]}
        R[f"E8 anatomy {tag}"] = anat
        top = sorted((k for k in anat if not k.startswith("_")), key=lambda k: -anat[k]["modulus_mean"])[:12]
        log(f"E8 {tag} largest weights: " + ", ".join(f"{k} {anat[k]['modulus_mean']:.2f}" for k in top[:8]))

    # ── E9. ayanamsa and hour: recompute the FULL population's phases with Kerykeion under other conventions ─
    if not QUICK:
        try:
            from kerykeion import AstrologicalSubject
            from timezonefinder import TimezoneFinder
            from zoneinfo import ZoneInfo
            tf = TimezoneFinder(); tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
            tzc = {}
            def tzn(lat, lon):
                k = (round(float(lat), 2), round(float(lon), 2))
                if k not in tzc: tzc[k] = tf.timezone_at(lng=float(lon), lat=float(lat)) or "UTC"
                return tzc[k]
            def recompute(df, mask, zodiac, sidm, hour, wed_hour=12, ut_only=False):
                n = len(df); Dn = np.full((n, len(bodies)), np.nan); Mn = Dn.copy(); Wn = Dn.copy()
                for i in np.where(mask)[0]:
                    r = df.iloc[i]
                    for arr, dob, la, lo in ((Dn, r.dob_dad, r.lat_dad, r.lon_dad), (Mn, r.dob_mom, r.lat_mom, r.lon_mom)):
                        y_, m_, d_ = int(dob[:4]), int(dob[5:7]), int(dob[8:10])
                        kw = dict(zodiac_type=zodiac, online=False, city="x", nation="XX")
                        if zodiac == "Sidereal": kw["sidereal_mode"] = sidm
                        if ut_only:
                            s = AstrologicalSubject("x", y_, m_, d_, hour, 0, lng=0.0, lat=51.48, tz_str="UTC", **kw)
                        else:
                            s = AstrologicalSubject("x", y_, m_, d_, hour, 0, lng=float(lo), lat=float(la), tz_str=tzn(la, lo), **kw)
                        for j, b in enumerate(bodies):
                            try: arr[i, j] = float(getattr(s, b).abs_pos)
                            except Exception: pass
                    st = r.start; kw = dict(zodiac_type=zodiac, online=False, city="G", nation="GB")
                    if zodiac == "Sidereal": kw["sidereal_mode"] = sidm
                    s = AstrologicalSubject("w", int(st[:4]), int(st[5:7]), int(st[8:10]), wed_hour, 0, lng=0.0, lat=51.48, tz_str="UTC", **kw)
                    for j, b in enumerate(bodies):
                        if b in ANGLES: continue
                        try: Wn[i, j] = float(getattr(s, b).abs_pos)
                        except Exception: pass
                return Dn, Mn, Wn
            mtr, mte = POP["FULL"]
            configs = [("Lahiri 09:00 (baseline)", "Sidereal", "LAHIRI", 9, 12, False), ("Raman", "Sidereal", "RAMAN", 9, 12, False),
                       ("Fagan-Bradley", "Sidereal", "FAGAN_BRADLEY", 9, 12, False), ("Krishnamurti", "Sidereal", "KRISHNAMURTI", 9, 12, False),
                       ("TROPICAL", "Tropic", None, 9, 12, False),
                       ("hour 06:00 local", "Sidereal", "LAHIRI", 6, 12, False), ("hour 12:00 local", "Sidereal", "LAHIRI", 12, 12, False),
                       ("hour 18:00 local", "Sidereal", "LAHIRI", 18, 12, False), ("hour 12:00 UT, place ignored", "Sidereal", "LAHIRI", 12, 12, True),
                       ("wedding at 00:00 UT", "Sidereal", "LAHIRI", 9, 0, False)]
            for name, zod, sidm, hr, wh, ut in configs:
                try:
                    Dn, Mn, Wn = recompute(tr, mtr, zod, sidm, hr, wh, ut); Dne, Mne, Wne = recompute(te, mte, zod, sidm, hr, wh, ut)
                except Exception as e:
                    log(f"E9 {name}: {type(e).__name__} {str(e)[:80]}"); continue
                for sub, tag in ((("a", "m", "d"), "3-term"), (TERMS, "6-term")):
                    row, _, _ = run(f"E9 {name} {tag}", sub, BODIES14, "FULL", F=1, seeds=2, D=(Dn, Dne), M=(Mn, Mne), W=(Wn, Wne))
                    log(f"E9 {name:<28} {tag}: inner {row['inner']:.4f} held {row['held']:.4f}")
        except Exception as e:
            log(f"E9 skipped: {type(e).__name__} {str(e)[:100]}")

    # ── E10. temporal folds inside the training half vs held out, for the main variants ────────────────────
    mtr, mte = POP["FULL"]
    for sub, tag in ((("a",), "a"), (("a", "m", "d"), "a+m+d"), (("a", "m", "d", "mn", "dn"), "5-term"), (TERMS, "6-term")):
        P, _ = phase_matrix(Dtr, Mtr, Wtr, bodies, BODIES14, sub); Pe, _ = phase_matrix(Dte, Mte, Wte, bodies, BODIES14, sub)
        lat = later[mtr]; Pf, yf = P[mtr], ytr[mtr]
        folds = []
        for cut in (1820, 1850, 1875):
            f = lat <= cut; v = (lat > cut) & (lat <= {1820: 1850, 1850: 1875, 1875: 1901}[cut])
            if f.sum() < 300 or v.sum() < 100: continue
            inner_f = np.zeros(int(f.sum()), bool); inner_f[-max(50, int(f.sum()) // 8):] = True
            am = ArtaModel(terms=sub, bodies=BODIES14, F=1).fit(Pf[f], yf[f], inner_f); folds.append(auc(yf[v], am.score(Pf[v])))
        R[f"E10 folds {tag}"] = {"fold_aucs": folds, "held": R.get(f"E1 terms {'+'.join(sub)}", {}).get("held")}
        log(f"E10 {tag}: folds {' '.join(f'{a:.3f}' for a in folds)} · held out {R[f'E10 folds {tag}']['held']}")

    os.makedirs(OUT, exist_ok=True)
    json.dump(R, open(os.path.join(OUT, "artamodel_study.json"), "w"), indent=1)
    log(f"wrote {OUT}/artamodel_study.json with {len(R)} results")


if __name__ == "__main__" and not os.environ.get("AQ_SUMMARISE"):
    main()


def selected_by_inner(R):
    """The honest headline of every sweep: the configuration the INNER split picks, and only its held-out score.
    Printing the max of a held-out column is selection on the test set; this is the number to quote instead, and
    the gap between the two is the optimism a reader should subtract from any 'best held-out' in the tables."""
    out = {}
    fams = {"E1 term subsets (F=1)": lambda k: k.startswith("E1 terms "),
            "E1 F=8 rungs": lambda k: k.startswith("E1 F8 "),
            "E3 3-term body sets": lambda k: k.startswith("E3 3-term"),
            "E3 6-term body sets": lambda k: k.startswith("E3 6-term"),
            "E5 harmonics": lambda k: k.startswith("E5 "),
            "E6 fields x L2": lambda k: k.startswith("E6 3-term F="),
            "E9 conventions, 3-term": lambda k: k.startswith("E9 ") and k.endswith("3-term"),
            "E9 conventions, 6-term": lambda k: k.startswith("E9 ") and k.endswith("6-term")}
    for fam, pred in fams.items():
        rows = {k: v for k, v in R.items() if pred(k) and isinstance(v, dict) and "inner" in v}
        if not rows:
            continue
        best_inner = max(rows, key=lambda k: rows[k]["inner"])
        best_held = max(rows, key=lambda k: rows[k]["held"])
        out[fam] = {"n_configs": len(rows), "selected_by_inner": best_inner, "its_inner": rows[best_inner]["inner"],
                    "its_held": rows[best_inner]["held"], "max_held_in_family": rows[best_held]["held"],
                    "optimism_if_selected_on_held": rows[best_held]["held"] - rows[best_inner]["held"]}
    return out


if __name__ == "__main__" and os.environ.get("AQ_SUMMARISE"):
    R = json.load(open(os.path.join(OUT, "artamodel_study.json")))
    S = selected_by_inner(R)
    print(f"  {'sweep':<28} {'n':>3}  {'selected by inner':<34} {'inner':>6} {'held':>6}  {'max held':>8} {'optimism':>8}")
    for fam, v in S.items():
        print(f"  {fam:<28} {v['n_configs']:>3}  {v['selected_by_inner'][:34]:<34} {v['its_inner']:.4f} {v['its_held']:.4f}  "
              f"{v['max_held_in_family']:.4f} {v['optimism_if_selected_on_held']:+.4f}")
    json.dump(S, open(os.path.join(OUT, "artamodel_selected.json"), "w"), indent=1)
