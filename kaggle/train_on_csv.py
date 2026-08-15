"""
train_on_csv.py — train the astrology stack on the published three-column dataset and predict the test half.

WHY THIS EXISTS SEPARATELY. The rest of this project trains on a rich internal file with precision flags,
sitelink counts and person ids. The published competition data has none of that: two dates and a label. So
this is the model as a competitor would have to build it, on exactly the columns everyone else gets — which
makes its score comparable to theirs rather than to a privileged version of the task.

WHAT IT DOES
  1. Turns train.csv into the couples file core.py reads. SEX IS CARRIED BY THE COLUMN ORDER — `dob_man`
     then `dob_woman`, assigned from Wikidata's P21 — so `aSex`/`bSex` are facts here rather than the
     placeholders they used to be. That matters for exactly one number: the baseline is a logistic on
     `dob_woman - dob_man`, which is the SIGNED age gap and not the unsigned ordering it had to be while the
     pair was sorted by Q-number. Anything asymmetric in the features means the same for every row now,
     where before its sign was arbitrary.
  2. Builds every tradition's feature blocks through the shim — the same astronomy the browser runs.
  3. Fits one model per block (boosted trees or a standardised logistic, whichever scores better
     out-of-fold), then a meta logistic over their out-of-fold predictions, over person-disjoint folds.
     There are no person ids in the published data, so folds are grouped by the pair itself: with one row per
     unordered couple and the training half already person-disjoint from the test half, the leak this
     guards against at full scale cannot occur within the file.
  4. Predicts test.csv and writes submission.csv, plus the exported arrays so the same model can be
     published as a Kaggle model and evaluated in the browser.

Usage:
    AQ_TRAIN=/tmp/aqscrape/train.csv AQ_TEST=/tmp/aqscrape/test.csv AQ_OUT=/tmp/aqmodel \\
        ~/.artamatch-venv/bin/python train_on_csv.py
"""
import csv
import gc
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dates as D          # noqa: E402  — the one place that understands a date with 00 in it
ROOT = os.path.dirname(HERE)
ASTRO = os.path.join(ROOT, "astro")
WEB = os.path.join(ROOT, "web")
TRAIN = os.environ.get("AQ_TRAIN", "/tmp/aqscrape/train.csv")
TEST = os.environ.get("AQ_TEST", "/tmp/aqscrape/test.csv")
OUT = os.environ.get("AQ_OUT", "/tmp/aqmodel")
LIMIT = int(os.environ.get("AQ_LIMIT") or 0)
FOLDS = 5
# How many blocks each tradition may contribute. The per-tradition cap is a guarantee, not a budget: it stops a
# strong tradition crowding out every other one. Raising it gives the meta model more to combine — 18 traditions
# at 6 is up to 108 base models instead of 54 — at the cost of a longer refit. The meta model stays a LOGISTIC
# whatever this is set to, because predictor.py evaluates a linear meta and a boosted one could not ship.
MAX_PER_TRADITION = int(os.environ.get("AQ_PER_TRADITION") or 3)
T0 = time.time()
os.makedirs(OUT, exist_ok=True)
CAND = os.path.join(OUT, "couples.json")


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def rows_from(path, labelled):
    """Read the published CSV into the shape core.load() wants, precision included.

    The precision is DERIVED from the date rather than assumed. This used to pass `aPrec: 11, aWin: 1` for
    every row — telling core that every day was known, including for the third of rows that carry only a year
    as `YYYY-00-00`. core has precision-aware features and an uncertainty window for exactly this case and they
    were being handed a constant.
    """
    out = []
    with open(path) as f:
        for i, r in enumerate(csv.DictReader(f)):
            rec = D.couple_record(i, r["dob_man"], r["dob_woman"],
                                  int(r["parents_together"]) if labelled else 0)
            rec["_id"] = r.get("id")
            out.append(rec)
    return out


def write(rows):
    json.dump([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows], open(CAND, "w"))


def main():
    sys.path.insert(0, ASTRO)
    sys.path.insert(0, WEB)
    os.environ.update({"AQ_COUPLES": CAND, "AQ_NO_PLACE": "1", "AQ_KEEP_ALL_COLS": "1",
                       "AQ_NO_EPHEM_CACHE": "1", "AQ_EPHEM_CACHE": "/nonexistent.npz"})
    for k in ("AQ_SUBSAMPLE", "AQ_BALANCE", "AQ_ROW_INDEX", "AQ_ONLY_KEYS", "AQ_DUMP_ROWS"):
        os.environ.pop(k, None)

    import sweshim
    sweshim.load(os.path.join(WEB, "ephem4.bin"), os.path.join(WEB, "tables.json"))
    sys.modules["swisseph"] = sweshim
    import core
    import export_model
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    tr = rows_from(TRAIN, True)
    te = rows_from(TEST, False)
    if LIMIT:
        tr, te = tr[:LIMIT], te[:max(200, LIMIT // 4)]
        log(f"AQ_LIMIT={LIMIT}: DRY RUN — these numbers are not results")
    log(f"train {len(tr):,} · test {len(te):,}")

    MODULES = [m[5:-3] for m in sorted(os.listdir(ASTRO))
               if m.startswith("trad_") and m.endswith(".py")
               and m[5:-3] not in ("electional", "muhurta", "wedding_transits")]

    def build(rows):
        write(rows)
        E = core.load()
        if E.n != len(rows):
            raise SystemExit(f"core kept {E.n} of {len(rows)} rows — predictions could not be aligned")
        blocks = {}
        for slug in MODULES:
            for k, v in (__import__(f"trad_{slug}").build(E) or {}).items():
                if v is not None:
                    blocks[f"{slug}::{k}"] = np.asarray(v, dtype=np.float32)
        return E, blocks

    log("building features for the training half")
    Etr, Btr = build(tr)
    y = Etr.Y.astype(int)
    log(f"  {len(Btr)} blocks · {sum(v.shape[1] for v in Btr.values()):,} columns")

    YR = 365.2425
    gap = (Etr.JD[1] - Etr.JD[0]) / YR
    folds = list(StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=7).split(np.zeros(len(y)), y))
    bp = np.zeros(len(y))
    for a, b in folds:
        bp[b] = LogisticRegression(max_iter=2000).fit(gap[a, None], y[a]).predict_proba(gap[b, None])[:, 1]
    log(f"  BASELINE two-parameter logistic on the SIGNED gap (woman - man): AUC {roc_auc_score(y, bp):.4f}")

    def hgb():
        return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=15,
                                              l2_regularization=1.0, random_state=0)

    def logit():
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000))

    def screen_model():
        return HistGradientBoostingClassifier(max_iter=120, learning_rate=0.1, max_leaf_nodes=15,
                                              l2_regularization=1.0, random_state=0)

    # TWO STAGES, because fitting every block on every row is the expensive thing and it only has to RANK.
    # A dry run fitted all 237 blocks with both model kinds over five folds and took 26 minutes on 1,200
    # rows; the same shape on 70,475 would run for most of a day. Screening therefore runs on a subsample
    # with three folds and one cheap configuration, and only the blocks that survive are refitted on
    # everything with five folds and both kinds.
    SCREEN_ROWS = int(os.environ.get("AQ_SCREEN_ROWS") or 15000)
    rng = np.random.default_rng(11)
    sidx = (np.sort(rng.permutation(len(y))[:SCREEN_ROWS]) if SCREEN_ROWS < len(y)
            else np.arange(len(y)))
    sy = y[sidx]
    sfolds = list(StratifiedKFold(n_splits=3, shuffle=True, random_state=7)
                  .split(np.zeros(len(sidx)), sy))
    log(f"screening {len(Btr)} blocks on {len(sidx):,} rows, 3 folds, one cheap model")
    ranked = []
    for key, X in Btr.items():
        keep = X.std(0) > 1e-12
        if keep.sum() == 0:
            continue
        ki = np.flatnonzero(keep)
        Xs = np.ascontiguousarray(X[sidx][:, ki])
        pv = np.zeros(len(sidx))
        try:
            for a, b in sfolds:
                pv[b] = screen_model().fit(Xs[a], sy[a]).predict_proba(Xs[b])[:, 1]
            auc = float(roc_auc_score(sy, pv))
        except Exception as e:
            log(f"    {key}: {type(e).__name__} {str(e)[:60]}")
            continue
        ranked.append({"key": key, "slug": key.split("::")[0], "name": key.split("::", 1)[1],
                       "kept_idx": ki.tolist(), "full_cols": int(X.shape[1]), "screen_auc": auc})
        del Xs
    ranked.sort(key=lambda s: -s["screen_auc"])
    log(f"  screened {len(ranked)}; best {ranked[0]['screen_auc']:.4f} ({ranked[0]['key'][:50]})")

    per, chosen = {}, []
    for s in ranked:
        if per.get(s["slug"], 0) >= MAX_PER_TRADITION:
            continue
        per[s["slug"]] = per.get(s["slug"], 0) + 1
        chosen.append(s)
    log(f"  selected {len(chosen)} across {len(per)} traditions; refitting on all {len(y):,} rows")

    scored = []
    for s in chosen:
        X = Btr[s["key"]]
        Xk = np.ascontiguousarray(X[:, np.asarray(s["kept_idx"])])
        best = None
        for kind, mk in (("hgb", hgb), ("logit", logit)):
            pv = np.zeros(len(y))
            try:
                for a, b in folds:
                    pv[b] = mk().fit(Xk[a], y[a]).predict_proba(Xk[b])[:, 1]
                auc = float(roc_auc_score(y, pv))
            except Exception as e:
                log(f"    {s['key']} / {kind}: {type(e).__name__} {str(e)[:60]}")
                continue
            if best is None or auc > best["auc"]:
                best = {"auc": auc, "kind": kind, "mk": mk, "oof": pv}
        if best is None:
            continue
        s.update({"auc": best["auc"], "kind": best["kind"], "oof": best["oof"],
                  "estimator": best["mk"]().fit(Xk, y)})
        scored.append(s)
        log(f"    {s['auc']:.4f}  {s['kind']:<5} {s['key'][:56]}  (screen {s['screen_auc']:.4f})")
        del Xk
    chosen = scored

    P = np.column_stack([s["oof"] for s in chosen])
    mu, sd = P.mean(0), P.std(0) + 1e-9
    pred = np.zeros(len(y))
    for a, b in folds:
        m = LogisticRegression(C=0.03, max_iter=4000).fit((P[a] - mu) / sd, y[a])
        pred[b] = m.predict_proba((P[b] - mu) / sd)[:, 1]
    cv = float(roc_auc_score(y, pred))
    meta = LogisticRegression(C=0.03, max_iter=4000).fit((P - mu) / sd, y)
    log(f"  STACK out-of-fold AUC {cv:.4f}   baseline {roc_auc_score(y, bp):.4f}   "
        f"lift {cv-roc_auc_score(y, bp):+.4f}")

    specs = [{"key": s["key"], "slug": s["slug"], "name": s["name"], "kind": s["kind"],
              "kept_idx": s["kept_idx"], "full_cols": s["full_cols"], "auc": s["auc"],
              "estimator": s["estimator"]} for s in chosen]
    export_model.pack(specs, {"mu": mu, "sd": sd, "coef": meta.coef_.ravel(),
                              "intercept": meta.intercept_[0], "auc": cv,
                              "n": int(len(y)), "rate": float(y.mean()), "hour": "08:00 UT",
                              "contract": "two birth dates only, as published",
                              "baseline": {"logistic on the signed gap (woman - man)": float(roc_auc_score(y, bp))}},
                      os.path.join(OUT, "model.json"), os.path.join(OUT, "model.npz"))
    log(f"  exported model.json + model.npz")

    del Btr
    gc.collect()
    log("building features for the test half and predicting")
    Ete, Bte = build(te)
    import predictor
    st = predictor.load(open(os.path.join(OUT, "model.json")).read(),
                        open(os.path.join(OUT, "model.npz"), "rb").read())
    p, _ = st.proba(Bte)
    with open(os.path.join(OUT, "submission.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "parents_together"])
        for r, prob in zip(te, p):
            w.writerow([r["_id"], f"{prob:.6f}"])
    log(f"  wrote submission.csv ({len(p):,} rows, mean {p.mean():.4f})")
    json.dump({"cv_auc": cv, "baseline_auc": float(roc_auc_score(y, bp)),
               "blocks": len(chosen), "traditions": len(per), "n_train": int(len(y)),
               "per_block": [{"key": s["key"], "kind": s["kind"], "auc": s["auc"]} for s in chosen]},
              open(os.path.join(OUT, "result.json"), "w"), indent=1)
    log(f"done in {(time.time()-T0)/60:.1f} min")


if __name__ == "__main__":
    main()
