"""
test_blocks.py — score candidate feature blocks on the real temporal split, against TWO bars.

WHY TWO BARS. On this dataset the positive rate climbs from 29% to 54% across the training span, so the birth
year alone is a strong predictor and any feature that can read the calendar inherits that strength without
reading anything astrological. A single held-out AUC therefore cannot distinguish a real effect from the era.

    BAR 1  the age gap    -- AUC of (year_younger - year_older), the one permitted non-astrology comparison. A
                             two-parameter logistic on it has exactly this AUC, since AUC is invariant under any
                             monotone transform of the score.
    BAR 2  gap-matched    -- AUC computed WITHIN one-year age-gap bands and pooled. Inside a band the gap is
                             flat, so a block that only re-reads the gap scores 0.50 here. Measured this way the
                             fitted coherent field fell from 0.5559 to 0.4932, which is how we know its whole
                             out-of-time score was the gap in disguise.

Pooling for bar 2 is over concordant PAIRS, not an average of per-band AUCs: a band with 40 rows and a band with
4,000 must not count equally, and the pair count is the natural weight (it is what AUC is a ratio of).

Usage: AQ_TRAIN=/tmp/aqdur/train.csv AQ_TEST=/tmp/aqdur/test.csv AQ_SOL=/tmp/aqdurcomp/solution.csv \
       AQ_MODS=coherent AQ_SUB=20000 python test_blocks.py
"""
import csv
import os
import sys
import time

import numpy as np

T0 = time.time()
REPO = os.path.expanduser("~/Studio/artamatch")
ASTRO, WEB, KAG = f"{REPO}/astro", f"{REPO}/web", f"{REPO}/kaggle"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("AQ_OUT") or "/tmp/aqcoh"
os.makedirs(OUT, exist_ok=True)

TRAIN = os.environ.get("AQ_TRAIN", "/tmp/aqdur/train.csv")
TEST = os.environ.get("AQ_TEST", "/tmp/aqdur/test.csv")
SOL = os.environ.get("AQ_SOL", "/tmp/aqdurcomp/solution.csv")
MODS = [m for m in os.environ.get("AQ_MODS", "coherent").split(",") if m]
SUB = int(os.environ.get("AQ_SUB") or 0)
BAND = int(os.environ.get("AQ_BAND") or 1)


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def auc(y, s):
    """Rank AUC with ties at half credit. Returns nan when one class is absent."""
    y = np.asarray(y, dtype=np.int64)
    s = np.asarray(s, dtype=np.float64)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
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
    return (r[ys == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def matched_auc(y, s, band):
    """AUC pooled over concordant/discordant pairs WITHIN bands of a nuisance quantity.

    Averaging per-band AUCs would let a 40-row band outweigh a 4,000-row one. Pooling the pair counts is what
    AUC is a ratio of, so this is the same estimator computed on a restricted pair set: only pairs of couples
    born in the same band are eligible, which is precisely what "holding the era flat" means.
    """
    num = den = 0.0
    used = 0
    for b in np.unique(band):
        m = band == b
        yy, ss = y[m], s[m]
        n1, n0 = int(yy.sum()), int((1 - yy).sum())
        if n1 == 0 or n0 == 0:
            continue
        a = auc(yy, ss)
        num += a * n1 * n0
        den += n1 * n0
        used += 1
    return (num / den if den else np.nan), used, int(den)


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
    import json

    import sweshim
    sweshim.load(os.path.join(WEB, "ephem4.bin"), os.path.join(WEB, "tables.json"))
    sys.modules["swisseph"] = sweshim
    import core
    sys.path.insert(0, HERE)
    from sklearn.ensemble import HistGradientBoostingClassifier

    def rows_from(path, labelled):
        out = []
        with open(path) as f:
            rd = csv.DictReader(f)
            lab = None
            if labelled:
                known = {"id", "dob_older", "dob_younger"}
                cand = [c for c in rd.fieldnames if c not in known]
                assert len(cand) == 1, cand
                lab = cand[0]
            for i, r in enumerate(rd):
                rec = D.couple_record(i, r["dob_older"], r["dob_younger"],
                                      int(r[lab]) if labelled else 0)
                rec["_id"] = r.get("id")
                rec["_yo"] = int(r["dob_older"][:4]) if r["dob_older"] != "0000-00-00" else 0
                rec["_yy"] = int(r["dob_younger"][:4]) if r["dob_younger"] != "0000-00-00" else 0
                out.append(rec)
        return out

    tr = rows_from(TRAIN, True)
    te = rows_from(TEST, False)
    if SUB and SUB < len(tr):
        # Seeded, and by ROW -- this harness compares blocks against each other on identical rows, so the only
        # requirement is that the draw is the same for every block, not that it match core's group rule.
        idx = np.random.default_rng(7).choice(len(tr), size=SUB, replace=False)
        tr = [tr[i] for i in sorted(idx)]
    log(f"train {len(tr):,} · test {len(te):,}")

    # the held-out labels, from the solution file
    import pandas as pd
    sol = pd.read_csv(SOL).set_index("id")
    lab = [c for c in sol.columns if c != "Usage"][0]

    def build(rows):
        json.dump([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
                  open(os.environ["AQ_COUPLES"], "w"))
        E = core.load()
        if E.n != len(rows):
            raise SystemExit(f"core kept {E.n} of {len(rows)} rows")
        B = {}
        for slug in MODS:
            for k, v in (__import__(f"trad_{slug}").build(E) or {}).items():
                B[f"{slug}::{k}"] = np.asarray(v, dtype=np.float32)
        return B

    log("building the training half's blocks")
    Btr = build(tr)
    y = np.array([r["label"] for r in tr], dtype=np.int64)
    log(f"  {len(Btr)} blocks, {sum(v.shape[1] for v in Btr.values()):,} columns")

    log("building the held-out half's blocks")
    Bte = build(te)
    ids = np.array([r["_id"] for r in te])
    keep = np.isin(ids, sol.index.to_numpy().astype(str))
    yte = sol.loc[ids[keep], lab].to_numpy().astype(np.int64)
    usage = sol.loc[ids[keep], "Usage"].to_numpy()
    yo = np.array([r["_yo"] for r in te])[keep]
    yy = np.array([r["_yy"] for r in te])[keep]
    gap = np.abs(yy - yo)
    band = (gap // BAND) * BAND
    log(f"  held-out {keep.sum():,} rows · {len(np.unique(band))} age-gap bands of {BAND}y")

    # ── the two bars ───────────────────────────────────────────────────────────────────────────────────────
    g = (yy - yo).astype(np.float64)
    a0 = auc(yte, g)
    era_auc = max(a0, 1 - a0)
    sign = 1.0 if a0 > 0.5 else -1.0
    era_m, nb, npair = matched_auc(yte, sign * g, band)
    log(f"  BAR 1 age-gap logistic          {era_auc:.4f}")
    log(f"  BAR 2 the gap inside its own bands {era_m:.4f}  <- 0.50 by construction; it verifies the control "
        f"({nb} bands of {BAND}y, {npair:,} eligible pairs)")

    rows = []
    for k in sorted(Btr):
        Xtr, Xte = Btr[k], Bte[k][keep]
        clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08, max_leaf_nodes=31,
                                             l2_regularization=1.0, early_stopping=True,
                                             validation_fraction=0.15, random_state=0)
        clf.fit(Xtr, y)
        p = clf.predict_proba(Xte)[:, 1]
        a = auc(yte, p)
        am, _, _ = matched_auc(yte, p, band)
        pub = usage == "Public"
        rows.append({"block": k, "cols": Xtr.shape[1], "auc": float(a),
                     "matched": float(am), "public": float(auc(yte[pub], p[pub])),
                     "private": float(auc(yte[~pub], p[~pub]))})
        log(f"  {k[:74]:<74} AUC {a:.4f}  era-matched {am:.4f}")

    rows.sort(key=lambda r: -r["matched"])
    print(f"\n  RANKED BY GAP-MATCHED AUC (the honest bar). Age gap {era_auc:.4f}; the gap inside its own bands {era_m:.4f}\n")
    print(f"  {'block':<72} {'cols':>5} {'AUC':>7} {'matched':>8} {'public':>7} {'private':>8}")
    for r in rows:
        print(f"  {r['block'][:72]:<72} {r['cols']:>5} {r['auc']:>7.4f} {r['matched']:>8.4f} "
              f"{r['public']:>7.4f} {r['private']:>8.4f}")
    json.dump({"age_gap": era_auc, "age_gap_matched": era_m, "band": BAND, "blocks": rows},
              open(os.path.join(OUT, "block_scores.json"), "w"), indent=1)
    print(f"\n  wrote {OUT}/block_scores.json")


if __name__ == "__main__":
    main()
