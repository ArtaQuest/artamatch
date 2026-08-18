"""
rank_mega.py — thousands of named features, each with its own 2-parameter logistic, RANKED BY TRAINING AUC.

    logit P(lasted 30 years) = b0 + b1 * feature

One feature, two parameters, per feature. The logistic is monotone in the feature and AUC is invariant under
monotone transforms, so its AUC IS the feature's rank AUC and b1's SIGN is the only thing the fit decides. The
sign comes from the training half and is then applied out of time.

RANKED BY THE TRAINING HALF. With several thousand features and one held-out set, ranking by held-out AUC would
surface the luckiest feature rather than the best: the largest of N null draws sits sqrt(2 ln N) standard errors
above 0.5 by construction, which at N=5000 and se=0.006 is about 0.525. Training AUC is estimated on different
couples entirely, so it cannot be inflated by held-out noise. The held-out column is the CHECK.

FOUR COLUMNS
  train      AUC on the training half -- the ranking key, and the source of b1's sign
  held out   the same feature and sign on 13,250 couples born after the training window
  matched    held-out AUC WITHIN one-year age-gap bands. The gap alone is worth 0.6045, and any feature of two
             dates is a function of era and gap, so this separates a periodic claim from a re-reading of the gap
  flip       whether the held-out direction contradicts the training direction

DAY PRECISION ON BOTH DATES. `dates.concrete()` puts a year-only date at 1 January so a chart can be cast; as an
input to a LONGITUDE that is a fabrication, and it would plant a false spike at day 1 in every seasonal feature.
Only the 27,189 training couples with both dates to the day are used, which also matches the held-out half.

Usage: python research/coherent/rank_mega.py
"""
import csv
import json
import math
import os
import sys
import time

import numpy as np
from scipy.stats import rankdata

T0 = time.time()
REPO = os.path.expanduser("~/Studio/artamatch")
ASTRO, WEB, KAG = f"{REPO}/astro", f"{REPO}/web", f"{REPO}/kaggle"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("AQ_OUT", "/tmp/aqmega")
os.makedirs(OUT, exist_ok=True)
TRAIN = os.environ.get("AQ_TRAIN", "/tmp/aqdur/train.csv")
TEST = os.environ.get("AQ_TEST", "/tmp/aqdur/test.csv")
SOL = os.environ.get("AQ_SOL", "/tmp/aqdurcomp/solution.csv")
CHUNK = int(os.environ.get("AQ_CHUNK") or 1200)


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def auc_mat(X, y):
    """AUC of every column at once, ties averaged. Returns the RAW auc (not folded)."""
    n1, n0 = int(y.sum()), int((1 - y).sum())
    out = np.empty(X.shape[1])
    for s in range(0, X.shape[1], CHUNK):
        R = rankdata(X[:, s:s + CHUNK], axis=0, method="average")
        out[s:s + CHUNK] = (R[y == 1].sum(0) - n1 * (n1 + 1) / 2.0) / (n1 * n0)
    return out


def matched_mat(X, y, band):
    """Held-out AUC per column within bands, pooled over eligible pairs. Costs about one full AUC pass, because
    the bands partition the rows."""
    num = np.zeros(X.shape[1])
    den = 0.0
    for b in np.unique(band):
        m = band == b
        yy = y[m]
        n1, n0 = int(yy.sum()), int((1 - yy).sum())
        if not (n1 and n0):
            continue
        Xb = X[m]
        for s in range(0, X.shape[1], CHUNK):
            R = rankdata(Xb[:, s:s + CHUNK], axis=0, method="average")
            num[s:s + CHUNK] += ((R[yy == 1].sum(0) - n1 * (n1 + 1) / 2.0) / (n1 * n0)) * n1 * n0
        den += n1 * n0
    return num / den


def main():
    sys.path.insert(0, KAG)
    import dates as D
    sys.path[:0] = [ASTRO, WEB, HERE]
    os.environ.update({"AQ_COUPLES": os.path.join(OUT, "couples.json"), "AQ_NO_PLACE": "1",
                       "AQ_KEEP_ALL_COLS": "1", "AQ_NO_EPHEM_CACHE": "1",
                       "AQ_EPHEM_CACHE": "/nonexistent.npz"})
    for k in ("AQ_SUBSAMPLE", "AQ_BALANCE", "AQ_ROW_INDEX", "AQ_ONLY_KEYS", "AQ_DUMP_ROWS"):
        os.environ.pop(k, None)
    import sweshim
    sweshim.load(f"{WEB}/ephem4.bin", f"{WEB}/tables.json")
    sys.modules["swisseph"] = sweshim
    import core
    import pandas as pd

    import mega_features as MF

    def dayprec(c):
        return c.str.len().eq(10) & ~c.str.endswith("-00") & ~c.str.slice(5, 7).eq("00")

    tr = pd.read_csv(TRAIN, dtype={"dob_older": str, "dob_younger": str})
    te = pd.read_csv(TEST, dtype={"dob_older": str, "dob_younger": str})
    keepr = (dayprec(tr.dob_older) & dayprec(tr.dob_younger)).to_numpy()
    tr = tr[keepr].reset_index(drop=True)
    log(f"train {len(tr):,} couples with BOTH dates to the day · held out {len(te):,}")

    def recs(df, labelled):
        out = []
        lab = [c for c in df.columns if c not in {"id", "dob_older", "dob_younger"}]
        for i, r in df.iterrows():
            rec = D.couple_record(i, r.dob_older, r.dob_younger, int(r[lab[0]]) if labelled else 0)
            out.append(rec)
        return out

    def load(rows):
        json.dump(rows, open(os.environ["AQ_COUPLES"], "w"))
        E = core.load()
        if E.n != len(rows):
            raise SystemExit(f"core kept {E.n} of {len(rows)} rows")
        return E

    E_tr = load(recs(tr, True))
    log("training ephemeris built")
    E_te = load(recs(te, False))
    log("held-out ephemeris built")

    ytr = tr[[c for c in tr.columns if c not in {"id", "dob_older", "dob_younger"}][0]].to_numpy().astype(np.int64)
    sol = pd.read_csv(SOL).set_index("id")
    lab = [c for c in sol.columns if c != "Usage"][0]
    assert (te.id.to_numpy() == sol.index.to_numpy()).all(), "test.csv and solution.csv are misaligned"
    yte = sol[lab].to_numpy().astype(np.int64)
    usage = sol["Usage"].to_numpy()
    gapd = (pd.to_datetime(te.dob_younger) - pd.to_datetime(te.dob_older)).dt.days.to_numpy().astype(float)
    band = (np.abs(gapd) // 365.2425).astype(int)
    ga = auc_mat(gapd[:, None], yte)[0]
    GAP = max(ga, 1 - ga)
    log(f"age-gap baseline (its own 2-parameter logistic): {GAP:.4f}")

    rows = []

    def score(fam, Ftr, Fte):
        names = [k for k in Ftr if k in Fte]
        if not names:
            return
        Xtr = np.column_stack([Ftr[k][1] for k in names]).astype(np.float32)
        Xte = np.column_stack([Fte[k][1] for k in names]).astype(np.float32)
        keep = (Xtr.std(0) > 1e-12) & (Xte.std(0) > 1e-12) & np.isfinite(Xtr).all(0) & np.isfinite(Xte).all(0)
        if not keep.any():
            log(f"  {fam:<24} 0 usable of {len(names)}")
            return
        names = [n for n, k in zip(names, keep) if k]
        Xtr, Xte = Xtr[:, keep], Xte[:, keep]
        a_tr = auc_mat(Xtr, ytr)
        sign = np.where(a_tr >= 0.5, 1.0, -1.0).astype(np.float32)
        Xs = Xte * sign
        a_te = auc_mat(Xs, yte)
        a_m = matched_mat(Xs, yte, band)
        pub = usage == "Public"
        a_pub = auc_mat(Xs[pub], yte[pub])
        a_prv = auc_mat(Xs[~pub], yte[~pub])
        for j, n in enumerate(names):
            rows.append({"family": fam, "name": n, "explanation": Ftr[n][0],
                         "train": float(max(a_tr[j], 1 - a_tr[j])), "held": float(a_te[j]),
                         "matched": float(a_m[j]), "public": float(a_pub[j]), "private": float(a_prv[j]),
                         "flipped": bool(a_te[j] < 0.5)})
        log(f"  {fam:<24} {len(names):>5,} features   (running total {len(rows):,})")

    gens_tr = MF.families(E_tr)
    gens_te = MF.families(E_te)
    for (fam, Ftr), (_, Fte) in zip(gens_tr, gens_te):
        score(fam, Ftr, Fte)
        del Ftr, Fte

    score("calendrical + numerology",
          MF.calendrical(tr, np.asarray(E_tr.LON)[0, 0], np.asarray(E_tr.LON)[1, 0], E_tr.JD),
          MF.calendrical(te, np.asarray(E_te.LON)[0, 0], np.asarray(E_te.LON)[1, 0], E_te.JD))

    log(f"{len(rows):,} features scored in {(time.time()-T0)/60:.1f} min")
    rows.sort(key=lambda r: -r["train"])
    with open(os.path.join(OUT, "mega_ranking.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["family", "name", "train", "held", "matched", "public", "private",
                                          "flipped", "explanation"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    se = 0.5 / math.sqrt(min(int(yte.sum()), int((1 - yte).sum())))
    nullmax = 0.5 + se * math.sqrt(2 * math.log(len(rows)))
    setr = 0.5 / math.sqrt(min(int(ytr.sum()), int((1 - ytr).sum())))
    nullmax_tr = 0.5 + setr * math.sqrt(2 * math.log(len(rows)))
    print(f"\n  {len(rows):,} named features · {len(set(r['family'] for r in rows))} families")
    print(f"  age-gap baseline {GAP:.4f} · held-out se ~{se:.4f} · training se ~{setr:.4f}")
    print(f"  searching {len(rows):,} features, the largest PURE-NULL draw is expected near {nullmax_tr:.4f} on "
          f"train and {nullmax:.4f} held out")

    def table(rs, title, n=30):
        print(f"\n  {title}\n")
        print(f"  {'#':>4}  {'feature':<60} {'train':>7} {'held':>7} {'matched':>8}  flip")
        for i, r in enumerate(rs[:n], 1):
            print(f"  {i:>4}  {r['name'][:60]:<60} {r['train']:>7.4f} {r['held']:>7.4f} "
                  f"{r['matched']:>8.4f}  {'YES' if r['flipped'] else ''}")

    table(rows, "TOP FEATURES OF ALL, ranked by TRAINING AUC (held-out is the check, never the ranking key)", 40)
    NUMK = ("Life Path", "Personal Year", "Birthday number", "Chaldean", "pillar", "Attitude", "digit sum",
            "relationship number", "karmic", "challenge", "pinnacle", "compatibility group", "date digit sum")
    num = [r for r in rows if any(k in r["name"] for k in NUMK)]
    table(num, f"NUMEROLOGY, ranked by training AUC ({len(num):,} features)", 20)
    table([r for r in rows if r not in num],
          f"ASTROLOGY, ranked by training AUC ({len(rows)-len(num):,} features)", 20)

    print("\n  BY FAMILY — how each tradition's feature family behaves as a population\n")
    print(f"  {'family':<26} {'n':>6} {'best train':>11} {'its held':>9} {'median held':>12} "
          f"{'best matched':>13} {'% flipped':>10}")
    for fam in sorted(set(r["family"] for r in rows)):
        g = [r for r in rows if r["family"] == fam]
        b = max(g, key=lambda r: r["train"])
        print(f"  {fam:<26} {len(g):>6,} {b['train']:>11.4f} {b['held']:>9.4f} "
              f"{np.median([r['held'] for r in g]):>12.4f} {max(r['matched'] for r in g):>13.4f} "
              f"{100*sum(r['flipped'] for r in g)/len(g):>9.0f}%")

    flip = sum(r["flipped"] for r in rows)
    over_tr = [r for r in rows if r["train"] > nullmax_tr]
    kept = [r for r in over_tr if r["held"] > nullmax]
    print(f"\n  {flip:,} of {len(rows):,} features ({100*flip/len(rows):.0f}%) reversed direction out of time")
    print(f"  {len(over_tr):,} clear the training null threshold ({nullmax_tr:.4f}); of those, {len(kept):,} also "
          f"clear the held-out one ({nullmax:.4f})")
    print(f"  best held-out anywhere {max(r['held'] for r in rows):.4f} · best gap-matched anywhere "
          f"{max(r['matched'] for r in rows):.4f} · age gap {GAP:.4f}")
    json.dump({"n_features": len(rows), "age_gap": GAP, "se_heldout": se, "se_train": setr,
               "nullmax_train": nullmax_tr, "nullmax_heldout": nullmax, "n_flipped": flip,
               "n_train": len(tr), "n_heldout": len(te)},
              open(os.path.join(OUT, "mega_ranking_meta.json"), "w"), indent=1)
    print(f"\n  wrote {OUT}/mega_ranking.csv — all {len(rows):,} with names and explanations")


if __name__ == "__main__":
    main()
