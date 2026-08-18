"""
rank_sidereal.py — every sidereal family and every single feature, scored on the held-out half; a pre-registered
pool as the entry.

FAMILIES are read off the feature names: plain (ages at the start, gap, start year), vedic sub-families (D1,
vargas, panchanga, shadbala, ashtakavarga, dosha, dasa, pair) and zwds sub-families (palace, major, minor, pair,
crossings). Each family is scored ALONE with a small LightGBM (NaN-native), and each single feature with its own
two-parameter logistic (sign from the training half). Selection never touches the held-out labels: the pool's
members and weights are fixed in this file, and the held-out column is read once at the end for reporting.

The temporal folds (train births <= 1820/1850/1875) are used only for feature STABILITY, as before.

Usage: AQ_FEAT=/tmp/aq3feat/sidereal.npz AQ_SOL=/tmp/aq3comp/solution.csv python rank_sidereal.py
"""
import csv
import json
import math
import os
import re
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata

T0 = time.time()
FEAT = os.environ.get("AQ_FEAT", "/tmp/aq3feat/sidereal.npz")
SOL = os.environ.get("AQ_SOL", "/tmp/aq3comp/solution.csv")
OUT = os.environ.get("AQ_OUT", os.path.dirname(FEAT))


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def auc(y, s):
    y = np.asarray(y, np.int64); s = np.asarray(s, np.float64)
    m = np.isfinite(s)
    y, s = y[m], s[m]
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(s)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def subfamily(name):
    if name.startswith("plain_"):
        return "plain"
    src, k = name.split("::", 1)
    k2 = re.sub(r"^(dad|mom|pair)_", "", k)
    if src == "vedic":
        if k.startswith("pair_wed_") or k2.startswith("wed_"):
            return "vedic:vivaha muhurta (the wedding day)"
        if k.startswith("pair_"):
            return "vedic:pair (ashtakoota, transposition, dasa)"
        if re.match(r"D\d+_", k2):
            return "vedic:vargas D2-D60"
        if k2.startswith("sb_"):
            return "vedic:shad bala"
        if k2.startswith("sav_") or k2.startswith("bav_"):
            return "vedic:ashtakavarga"
        if k2 in ("tithi", "moon_nakshatra", "moon_pada", "yoga", "karana", "vaara", "lunar_month", "adhika_masa"):
            return "vedic:panchanga"
        if k2 in ("manglik", "kala_sarpa", "ganda_moola"):
            return "vedic:doshas"
        if "dasa" in k2 or "bhukti" in k2:
            return "vedic:vimsottari at the start"
        if k2 in ("tz_hours", "lat", "lon"):
            return "plain"
        return "vedic:D1 (lagna, grahas, houses, nakshatras)"
    if src == "zwds":
        if k.startswith("pair_"):
            return "zwds:pair (spouse x life palace, branches)"
        if k2.startswith("pal_") or k2.startswith("in_"):
            return "zwds:palaces"
        if k2.startswith("major_"):
            return "zwds:major stars"
        if k2.startswith("minor_"):
            return "zwds:minor stars"
        return "zwds:astrolabe (soul, body, class)"
    return src


def main():
    import lightgbm as lgb
    Z = np.load(FEAT, allow_pickle=True)
    X, Xe = Z["X_train"].astype(np.float32), Z["X_test"].astype(np.float32)
    y = Z["y_train"].astype(np.int64); names = list(Z["names"]); ids = Z["id_test"]
    yr = Z["yr_train"].astype(int); later = yr.max(1)
    sol = pd.read_csv(SOL).set_index("id"); lab = [c for c in sol.columns if c != "Usage"][0]
    yte = sol.loc[ids, lab].to_numpy().astype(int); pub = (sol.loc[ids, "Usage"] == "Public").to_numpy()
    fam = np.array([subfamily(n) for n in names])
    log(f"{X.shape[1]:,} features · train {len(y):,} · held out {len(yte):,} · {len(set(fam))} sub-families")

    # ── every single feature: 2-parameter logistic, sign from train, checked held out ────────────────────
    rows = []
    for j, n in enumerate(names):
        a_tr = auc(y, X[:, j])
        if math.isnan(a_tr):
            continue
        sgn = 1.0 if a_tr >= 0.5 else -1.0
        a_te = auc(yte, sgn * Xe[:, j])
        rows.append({"name": n, "family": fam[j], "train": max(a_tr, 1 - a_tr), "held": a_te,
                     "n_train": int(np.isfinite(X[:, j]).sum()), "n_held": int(np.isfinite(Xe[:, j]).sum())})
    rows.sort(key=lambda r: -r["train"])
    with open(os.path.join(OUT, "sidereal_features.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    log(f"{len(rows):,} single features scored")

    # ── every sub-family alone: LightGBM, fixed hyper-parameters, no selection ───────────────────────────
    def fit(cols, seeds=3, mono=None):
        p = np.zeros(len(Xe))
        for s in range(seeds):
            m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=100,
                                   colsample_bytree=0.7, subsample=0.8, subsample_freq=1, reg_lambda=10.0,
                                   random_state=s, verbose=-1)
            m.fit(X[:, cols], y)
            p += m.predict_proba(Xe[:, cols])[:, 1]
        return p / seeds
    fams = sorted(set(fam))
    famres = []
    preds = {}
    for F in fams:
        cols = np.where(fam == F)[0]
        p = fit(cols)
        preds[F] = p
        famres.append({"family": F, "n_features": int(len(cols)), "held": auc(yte, p),
                       "public": auc(yte[pub], p[pub]), "private": auc(yte[~pub], p[~pub])})
        log(f"  {F:<48} {len(cols):>5} features   held {auc(yte, p):.4f}")
    famres.sort(key=lambda r: -r["held"])

    # ── the entry: PRE-REGISTERED pool -- plain + all vedic + all zwds + all together, equal-weight ranks ─
    def r01(v):
        r = rankdata(v); return (r - 1) / max(1.0, len(r) - 1)
    allv = np.where(np.char.startswith(fam.astype(str), "vedic"))[0]
    allz = np.where(np.char.startswith(fam.astype(str), "zwds"))[0]
    plainc = np.where(fam == "plain")[0]
    members = {
        "plain (ages at start, gap, start year)": fit(plainc),
        "all vedic": fit(allv), "all zwds": fit(allz),
        "vedic + plain": fit(np.r_[allv, plainc]), "zwds + plain": fit(np.r_[allz, plainc]),
        "everything": fit(np.arange(X.shape[1])),
    }
    ens = np.mean([r01(v) for v in members.values()], 0)
    print(f"\n  SUB-FAMILIES ALONE (LightGBM, fixed hyper-parameters), held out on {len(yte):,} couples\n")
    print(f"  {'family':<50} {'n':>5} {'held':>7} {'public':>8} {'private':>8}")
    for r in famres:
        print(f"  {r['family']:<50} {r['n_features']:>5} {r['held']:>7.4f} {r['public']:>8.4f} {r['private']:>8.4f}")
    print(f"\n  POOL MEMBERS (pre-registered)\n")
    for k, v in members.items():
        print(f"  {k:<50} held {auc(yte, v):.4f}   public {auc(yte[pub], v[pub]):.4f}   private {auc(yte[~pub], v[~pub]):.4f}")
    print(f"\n  EQUAL-WEIGHT RANK AVERAGE of the {len(members)}: held {auc(yte, ens):.4f}   public {auc(yte[pub], ens[pub]):.4f}   private {auc(yte[~pub], ens[~pub]):.4f}")
    print(f"\n  TOP SINGLE FEATURES by training AUC (held-out is the check)\n")
    print(f"  {'feature':<62} {'train':>7} {'held':>7}  family")
    for r in rows[:25]:
        print(f"  {r['name'][:62]:<62} {r['train']:>7.4f} {r['held']:>7.4f}  {r['family']}")
    pd.DataFrame({"id": ids, lab: ens}).to_csv(os.path.join(OUT, "submission.csv"), index=False)
    json.dump({"families": famres, "members": {k: auc(yte, v) for k, v in members.items()}, "ensemble": auc(yte, ens),
               "n_features": int(X.shape[1])}, open(os.path.join(OUT, "sidereal_ranking.json"), "w"), indent=1)
    log(f"wrote {OUT}/sidereal_ranking.json, sidereal_features.csv, submission.csv")


if __name__ == "__main__":
    main()
