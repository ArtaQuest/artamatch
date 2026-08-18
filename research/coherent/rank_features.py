"""
rank_features.py — score and rank EVERY INDIVIDUAL FEATURE COLUMN, not blocks.

WHY SINGLE COLUMNS. The tradition ranking scores a whole tradition, and the block survey scores whole blocks of
up to 700 columns. Both can bury a single strong feature: one informative column averaged with 699 uninformative
ones reads as noise, and conversely a block can look useful because a model found structure across many weak
columns. A single-column ranking answers the question directly — is there ONE astrological or numerological
quantity, anywhere in nineteen traditions, that predicts whether a relationship lasted thirty years?

A single column needs NO FITTING. Univariate AUC is invariant under any monotone transform, so a two-parameter
logistic on one feature has exactly the AUC of the feature itself, with the sign the only choice —
`max(auc, 1-auc)`. Ties are averaged, which matters here because a great many columns are one-hot indicators.

RANKED BY THE TRAINING HALF, NEVER BY THE HELD-OUT SET. With ~57,000 columns and one held-out set, ranking by
held-out AUC would surface the luckiest column rather than the best one: the maximum of 57,000 draws with a
standard error near 0.005 sits several standard errors above the truth by construction. So the ranking is by
training-half AUC and the held-out column is a CHECK on it, printed but never used to order.

THREE NUMBERS PER COLUMN
  train      univariate AUC on the training half (genuine pairs) -- the ranking key
  held out   the same column on the 13,250 held-out couples -- the honest check
  matched    held-out AUC WITHIN 1-year age-gap bands. The age gap is worth 0.6047 held out, and a slow body's
             phase difference between partners is a near-linear read of it, so without this a column can score
             well while carrying nothing astrological. The estimator is validated in both directions in
             validate_control.py: it removes the gap (0.6046 -> 0.4982) and preserves a planted gap-independent
             signal (0.5958 -> 0.5961).

GENUINE PAIRS ONLY. 41.3% of training rows give both partners the same instant (an absent partner inherits the
other's), against 0.1% of held-out rows. Scoring a cross-chart column through them measures it on a
configuration that does not occur at test time.

THERE ARE NO COLUMN NAMES. Every tradition module returns a bare matrix, so a feature is identified as
`block :: column j`. The block name says what was computed; the index says which of its columns. That is a real
limitation of the feature layer and is stated rather than papered over.

Usage: AQ_SUB=25000 python research/coherent/rank_features.py
"""
import csv
import json
import os
import sys
import time

import numpy as np
from scipy.stats import rankdata

T0 = time.time()
REPO = os.path.expanduser("~/Studio/artamatch")
ASTRO, WEB, KAG = f"{REPO}/astro", f"{REPO}/web", f"{REPO}/kaggle"
OUT = os.environ.get("AQ_OUT", "/tmp/aqfeat")
os.makedirs(OUT, exist_ok=True)
TRAIN = os.environ.get("AQ_TRAIN", "/tmp/aqdur/train.csv")
TEST = os.environ.get("AQ_TEST", "/tmp/aqdur/test.csv")
SOL = os.environ.get("AQ_SOL", "/tmp/aqdurcomp/solution.csv")
SUB = int(os.environ.get("AQ_SUB") or 25000)
CHUNK = int(os.environ.get("AQ_CHUNK") or 1500)


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def auc_cols(X, y):
    """Univariate AUC for every column of X at once, ties averaged. Returns max(auc, 1-auc) per column."""
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return np.full(X.shape[1], np.nan)
    out = np.empty(X.shape[1])
    for s in range(0, X.shape[1], CHUNK):
        R = rankdata(X[:, s:s + CHUNK], axis=0, method="average")
        a = (R[y == 1].sum(0) - n1 * (n1 + 1) / 2.0) / (n1 * n0)
        out[s:s + CHUNK] = np.maximum(a, 1.0 - a)
    return out


def matched_cols(X, y, band):
    """Held-out AUC per column WITHIN bands, pooled over eligible pairs (not an average of per-band AUCs: a
    40-row band must not outweigh a 4,000-row one, and the pair count is what AUC is a ratio of)."""
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
            a = (R[yy == 1].sum(0) - n1 * (n1 + 1) / 2.0) / (n1 * n0)
            num[s:s + CHUNK] += a * n1 * n0
        den += n1 * n0
    return num / den if den else np.full(X.shape[1], np.nan)


def main():
    sys.path.insert(0, KAG)
    import dates as D
    sys.path.insert(0, ASTRO)
    sys.path.insert(0, WEB)
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

    def read(path, labelled):
        out = []
        with open(path) as f:
            rd = csv.DictReader(f)
            lab = None
            if labelled:
                cand = [c for c in rd.fieldnames if c not in {"id", "dob_older", "dob_younger"}]
                assert len(cand) == 1, cand
                lab = cand[0]
            for i, r in enumerate(rd):
                rec = D.couple_record(i, r["dob_older"], r["dob_younger"], int(r[lab]) if labelled else 0)
                rec["_id"] = r.get("id")
                rec["_yo"] = int(r["dob_older"][:4]) if r["dob_older"] != "0000-00-00" else 0
                rec["_yy"] = int(r["dob_younger"][:4]) if r["dob_younger"] != "0000-00-00" else 0
                out.append(rec)
        return out

    tr, te = read(TRAIN, True), read(TEST, False)
    # genuine pairs only, matching the held-out half's distribution
    tr = [r for r in tr if r["_yo"] and r["_yy"]]
    if SUB and SUB < len(tr):
        idx = np.random.default_rng(7).choice(len(tr), size=SUB, replace=False)
        tr = [tr[i] for i in sorted(idx)]
    log(f"train {len(tr):,} genuine pairs · held out {len(te):,}")

    def load(rows):
        json.dump([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
                  open(os.environ["AQ_COUPLES"], "w"))
        E = core.load()
        if E.n != len(rows):
            raise SystemExit(f"core kept {E.n} of {len(rows)} rows — alignment would be wrong")
        return E

    E_tr = load(tr)
    log("training ephemeris built")
    E_te = load(te)
    log("held-out ephemeris built")

    ytr = np.array([r["label"] for r in tr], dtype=np.int64)
    sol = pd.read_csv(SOL).set_index("id")
    lab = [c for c in sol.columns if c != "Usage"][0]
    ids = np.array([r["_id"] for r in te])
    keep = np.isin(ids, sol.index.to_numpy().astype(str))
    yte = sol.loc[ids[keep], lab].to_numpy().astype(np.int64)
    yo = np.array([r["_yo"] for r in te])[keep]
    yy = np.array([r["_yy"] for r in te])[keep]
    gap = np.abs(yy - yo).astype(float)
    band = (gap // 1) * 1
    a0 = auc_cols(gap[:, None], yte)[0]
    log(f"age-gap baseline on the held-out rows: {a0:.4f} · {len(np.unique(band))} one-year bands")

    MODULES = [m[5:-3] for m in sorted(os.listdir(ASTRO))
               if m.startswith("trad_") and m.endswith(".py")
               and m[5:-3] not in ("electional", "muhurta", "wedding_transits")]
    rows = []
    for slug in MODULES:
        mod = __import__(f"trad_{slug}")
        Btr = mod.build(E_tr) or {}
        Bte = mod.build(E_te) or {}
        n = 0
        for k in sorted(Btr):
            if k not in Bte:
                continue
            Xtr = np.asarray(Btr[k], dtype=np.float32)
            Xte = np.asarray(Bte[k], dtype=np.float32)[keep]
            if Xtr.shape[1] != Xte.shape[1]:
                log(f"  !! {slug}::{k} width {Xtr.shape[1]} vs {Xte.shape[1]} — skipped")
                continue
            atr = auc_cols(Xtr, ytr)
            ate = auc_cols(Xte, yte)
            am = matched_cols(Xte, yte, band)
            am = np.maximum(am, 1.0 - am)
            for j in range(Xtr.shape[1]):
                if np.isfinite(atr[j]):
                    rows.append((slug, k, j, float(atr[j]), float(ate[j]), float(am[j])))
            n += Xtr.shape[1]
        del Btr, Bte
        log(f"  {slug:<24} {n:>6,} columns scored   (running total {len(rows):,})")

    log(f"{len(rows):,} columns scored in {(time.time()-T0)/60:.1f} min")
    rows.sort(key=lambda r: -r[3])                      # by TRAIN auc, never by held-out
    with open(os.path.join(OUT, "feature_ranking.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tradition", "block", "col", "train_auc", "heldout_auc", "gap_matched_auc"])
        w.writerows(rows)
    json.dump({"age_gap_heldout": float(a0), "n_columns": len(rows), "n_train": len(tr),
               "n_heldout": int(keep.sum())}, open(os.path.join(OUT, "feature_ranking_meta.json"), "w"), indent=1)

    def table(rs, title, n=25):
        print(f"\n  {title}\n")
        print(f"  {'#':>3}  {'tradition':<22} {'block':<46} {'col':>4} {'train':>7} {'held':>7} {'matched':>8}")
        for i, r in enumerate(rs[:n], 1):
            print(f"  {i:>3}  {r[0]:<22} {r[1][:46]:<46} {r[2]:>4} {r[3]:>7.4f} {r[4]:>7.4f} {r[5]:>8.4f}")

    table(rows, f"TOP SINGLE FEATURES of {len(rows):,}, ranked by TRAINING-half AUC. "
                f"Age gap held out: {a0:.4f}")
    num = [r for r in rows if r[0] == "numerology"]
    table(num, f"TOP NUMEROLOGY features ({len(num):,} columns)", 15)
    ast = [r for r in rows if r[0] != "numerology"]
    table(ast, f"TOP ASTROLOGY features ({len(ast):,} columns)", 15)

    # What the ranking is worth: the best gap-matched column, and how far it is from chance given how many
    # columns were searched. With C columns the largest of C null draws is expected several SE above 0.5.
    se = 0.5 / np.sqrt(min(int(yte.sum()), int((1 - yte).sum())))
    best_m = max(rows, key=lambda r: r[5])
    import math
    exp_max = 0.5 + se * math.sqrt(2 * math.log(max(2, len(rows))))
    print(f"\n  held-out AUC standard error ~{se:.4f}; searching {len(rows):,} columns, the largest of that many "
          f"NULL draws is expected near {exp_max:.4f}")
    print(f"  best gap-matched column anywhere: {best_m[5]:.4f}  ({best_m[0]} :: {best_m[1][:40]} col {best_m[2]})")
    print(f"  -> {'ABOVE' if best_m[5] > exp_max else 'WITHIN'} what pure multiple-testing would produce")
    print(f"\n  wrote {OUT}/feature_ranking.csv")


if __name__ == "__main__":
    main()
