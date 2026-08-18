"""
rank_named.py — every named feature's own 2-parameter logistic AUC, ranked.

    logit P(lasted 30 years) = b0 + b1 * feature

One feature, two parameters, per feature. The logistic is monotone in the feature and AUC is invariant under
monotone transforms, so its AUC IS the feature's rank AUC and b1's SIGN is the only thing the fit decides. The
sign is fitted on the TRAINING half and applied to the held-out half; taking max(auc, 1-auc) on the held-out set
would be choosing the direction with the answers in hand, which across 675 features is not a rounding error.

FOUR COLUMNS PER FEATURE
  train      AUC on the training half (genuine pairs) -- the ranking key, and where the sign comes from
  held out   the same feature, same sign, on the 13,250 held-out couples born after the training window
  matched    held-out AUC WITHIN 1-year age-gap bands. The age gap alone is worth 0.6047 held out, so a feature
             that merely encodes the difference of two dates scores well without saying anything astrological.
             The estimator is validated in both directions (validate_control.py): it removes the gap
             (0.6046 -> 0.4982) and preserves a planted gap-independent signal (0.5958 -> 0.5961).
  flip       whether the held-out sign disagrees with the training sign, i.e. the feature reversed direction
             out of time -- the clearest single symptom of a feature that was noise

RANKED BY THE TRAINING HALF, never by the held-out set: the maximum of 675 held-out draws sits well above 0.5
by construction, so ranking on it would surface the luckiest feature rather than the best one. The report prints
what pure multiple testing is expected to produce, so the top of the table can be read against it.

Usage: AQ_SUB=25000 python research/coherent/rank_named.py
"""
import csv
import json
import math
import os
import sys
import time

import numpy as np

T0 = time.time()
REPO = os.path.expanduser("~/Studio/artamatch")
ASTRO, WEB, KAG = f"{REPO}/astro", f"{REPO}/web", f"{REPO}/kaggle"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("AQ_OUT", "/tmp/aqnamed")
os.makedirs(OUT, exist_ok=True)
TRAIN = os.environ.get("AQ_TRAIN", "/tmp/aqdur/train.csv")
TEST = os.environ.get("AQ_TEST", "/tmp/aqdur/test.csv")
SOL = os.environ.get("AQ_SOL", "/tmp/aqdurcomp/solution.csv")
SUB = int(os.environ.get("AQ_SUB") or 25000)


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def auc(y, s):
    y = np.asarray(y, np.int64)
    s = np.asarray(s, np.float64)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    o = np.argsort(s, kind="mergesort")
    ys, ss = y[o], s[o]
    r = np.empty(len(ss))
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[i:j + 1] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((r[ys == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def matched(y, s, band):
    num = den = 0.0
    for b in np.unique(band):
        m = band == b
        yy, ss = y[m], s[m]
        n1, n0 = int(yy.sum()), int((1 - yy).sum())
        if n1 and n0:
            num += auc(yy, ss) * n1 * n0
            den += n1 * n0
    return num / den if den else float("nan")


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

    import named_features as NF

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
    tr = [r for r in tr if r["_yo"] and r["_yy"]]          # genuine pairs, matching the held-out distribution
    if SUB and SUB < len(tr):
        idx = np.random.default_rng(7).choice(len(tr), size=SUB, replace=False)
        tr = [tr[i] for i in sorted(idx)]
    log(f"train {len(tr):,} genuine pairs · held out {len(te):,}")

    def load(rows):
        json.dump([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
                  open(os.environ["AQ_COUPLES"], "w"))
        E = core.load()
        if E.n != len(rows):
            raise SystemExit(f"core kept {E.n} of {len(rows)} rows")
        return E

    Ftr = NF.build(load(tr))
    log(f"training features built: {len(Ftr)}")
    Fte = NF.build(load(te))
    log(f"held-out features built: {len(Fte)}")
    assert [f[0] for f in Ftr] == [f[0] for f in Fte], "the two halves produced different feature lists"

    ytr = np.array([r["label"] for r in tr], dtype=np.int64)
    sol = pd.read_csv(SOL).set_index("id")
    lab = [c for c in sol.columns if c != "Usage"][0]
    ids = np.array([r["_id"] for r in te])
    keep = np.isin(ids, sol.index.to_numpy().astype(str))
    yte = sol.loc[ids[keep], lab].to_numpy().astype(np.int64)
    yo = np.array([r["_yo"] for r in te])[keep]
    yy = np.array([r["_yy"] for r in te])[keep]
    band = (np.abs(yy - yo) // 1) * 1
    gap_a = auc(yte, (yy - yo).astype(float))
    GAP = max(gap_a, 1 - gap_a)
    log(f"age-gap baseline (its own 2-parameter logistic): {GAP:.4f}")

    rows = []
    for (nm, ex, vtr), (_, _, vte) in zip(Ftr, Fte):
        a_tr = auc(ytr, vtr)
        sign = 1.0 if a_tr >= 0.5 else -1.0        # b1's sign, fitted on the TRAINING half only
        a_te = auc(yte, sign * vte[keep])
        a_m = matched(yte, sign * vte[keep], band)
        rows.append({"name": nm, "explanation": ex, "train": max(a_tr, 1 - a_tr), "held": a_te,
                     "matched": a_m, "flipped": bool(a_te < 0.5)})
    log(f"{len(rows)} features scored")

    rows.sort(key=lambda r: -r["train"])
    with open(os.path.join(OUT, "named_ranking.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "train", "held", "matched", "flipped", "explanation"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    def table(rs, title, n=30):
        print(f"\n  {title}\n")
        print(f"  {'#':>3}  {'feature':<62} {'train':>7} {'held':>7} {'matched':>8}  flip")
        for i, r in enumerate(rs[:n], 1):
            print(f"  {i:>3}  {r['name'][:62]:<62} {r['train']:>7.4f} {r['held']:>7.4f} "
                  f"{r['matched']:>8.4f}  {'YES' if r['flipped'] else ''}")

    se = 0.5 / math.sqrt(min(int(yte.sum()), int((1 - yte).sum())))
    exp_max = 0.5 + se * math.sqrt(2 * math.log(len(rows)))
    print(f"\n  {len(rows)} named features · held-out AUC standard error ~{se:.4f}")
    print(f"  the largest of {len(rows)} pure-null draws is expected near {exp_max:.4f} — read the top of every "
          f"table against that, not against 0.50")
    print(f"  the age gap's own 2-parameter logistic: {GAP:.4f}")

    table(rows, "ALL FEATURES, ranked by training-half AUC")
    NUMK = ("Life Path", "Personal Year", "Birthday number", "Chaldean", "pillar", "Attitude", "digit sum",
            "relationship number", "birth day", "birth month", "compatibility group")
    num = [r for r in rows if any(k in r["name"] for k in NUMK)]
    table(num, f"NUMEROLOGY only ({len(num)} features)", 20)
    ast = [r for r in rows if r not in num]
    table(ast, f"ASTROLOGY only ({len(ast)} features)", 20)
    table(sorted(rows, key=lambda r: -r["matched"]),
          "RANKED BY GAP-MATCHED AUC — the only column that can show a non-age-gap effect "
          "(NB: ordering by it is selection on the held-out set, so read it as a ceiling)", 20)

    best_m = max(rows, key=lambda r: r["matched"])
    flipped = sum(r["flipped"] for r in rows)
    print(f"\n  {flipped} of {len(rows)} features ({100*flipped/len(rows):.0f}%) REVERSED direction out of "
          f"time — the training sign disagreed with the held-out one")
    print(f"  best gap-matched feature anywhere: {best_m['matched']:.4f}  ({best_m['name'][:56]})")
    print(f"  -> {'ABOVE' if best_m['matched'] > exp_max else 'WITHIN'} the {exp_max:.4f} that searching "
          f"{len(rows)} null features would produce on its own")
    json.dump({"age_gap": GAP, "n_features": len(rows), "se": se, "expected_null_max": exp_max,
               "n_flipped": flipped, "n_train": len(tr), "n_heldout": int(keep.sum())},
              open(os.path.join(OUT, "named_ranking_meta.json"), "w"), indent=1)
    print(f"\n  wrote {OUT}/named_ranking.csv — all {len(rows)} with full explanations")


if __name__ == "__main__":
    main()
