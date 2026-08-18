"""
train_on_csv.py — train the astrology stack on the published three-column dataset and predict the test half.

WHY THIS EXISTS SEPARATELY. The rest of this project trains on a rich internal file with precision flags,
sitelink counts and person ids. The published competition data has none of that: two dates and a label. So
this is the model as a competitor would have to build it, on exactly the columns everyone else gets — which
makes its score comparable to theirs rather than to a privileged version of the task.

WHAT IT DOES
  1. Turns train.csv into the couples file core.py reads. THE COLUMN ORDER IS AGE — `dob_older` then
     `dob_younger`, computed from the dates themselves — and no sex is read anywhere (`aSex`/`bSex` are empty
     placeholders; no tradition module consumes them, checked). That matters for exactly one number: the
     baseline is a logistic on `dob_younger - dob_older`, the AGE GAP, which is non-negative by construction.
     Anything asymmetric in the features now means "older partner vs younger partner" for every row.
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
import subprocess
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


def label_column(fieldnames):
    """The target column, DISCOVERED from the header rather than hardcoded.

    This read `r["parents_together"]` as a literal, which was right for exactly one dataset. When the question
    changed to marriage duration the column became `lasted_30_years`, and a hardcoded name does not fail
    gracefully — it raises deep in a loop, or worse, a `.get(...)` default would have trained every row on
    label 0 and reported a perfectly plausible AUC of 0.5. The target is whatever column is neither an id nor a
    date, and there must be exactly one of them.
    """
    # `start_year` joined the inputs in the second edition (2026-08-18). It is carried on the record under a
    # private key that core.load() never sees -- the tradition modules read charts, not years -- and the label
    # is still whatever single column is left.
    known = {"id", "dob_older", "dob_younger", "start_year"}
    cand = [c for c in (fieldnames or []) if c not in known]
    if len(cand) != 1:
        raise SystemExit(f"cannot identify the label column: expected exactly one column outside {sorted(known)}, "
                         f"found {cand} in header {fieldnames}")
    return cand[0]


def rows_from(path, labelled):
    """Read the published CSV into the shape core.load() wants, precision included.

    The precision is DERIVED from the date rather than assumed. This used to pass `aPrec: 11, aWin: 1` for
    every row — telling core that every day was known, including for the third of rows that carry only a year
    as `YYYY-00-00`. core has precision-aware features and an uncertainty window for exactly this case and they
    were being handed a constant.
    """
    out = []
    with open(path) as f:
        rd = csv.DictReader(f)
        lab = label_column(rd.fieldnames) if labelled else None
        for i, r in enumerate(rd):
            rec = D.couple_record(i, r["dob_older"], r["dob_younger"], int(r[lab]) if labelled else 0)
            rec["_id"] = r.get("id")
            rec["_start_year"] = int(r["start_year"]) if r.get("start_year") else None
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

    def build(rows, keep=None, subsample=0):
        """Feature blocks for these rows. `keep` retains only those block keys; `subsample` thins by couple.

        WHY BOTH ARGUMENTS EXIST — this is a memory bound, not a nicety. Every block is held at once as
        float32, so the footprint is (total columns) x rows x 4 bytes: 57,132 columns over 271 blocks is
        10.6 GB at 50,000 couples and 21.3 GB at 100,000, on a machine with 16 GB. Building the full set at
        full scale is a certain OOM past about 80,000 rows, and the training half is larger than that.

        core.py has documented the remedy since it was written — screen on a subsample, then recompute only
        the survivors at full scale — and this file defeated it by popping AQ_SUBSAMPLE and AQ_ONLY_KEYS from
        the environment and keeping every block regardless. Now the screening pass passes `subsample` and the
        fitting pass passes `keep`, which is about 57 blocks of 271, so neither pass holds more than a few GB.

        The modules still COMPUTE all of their own blocks — filtering that would mean editing nineteen
        modules and risking a width change, which is the one thing verify_docs refuses to publish. What
        bounds memory is that unwanted blocks are never RETAINED; a module's own dict is transient.
        """
        write(rows)
        if subsample:
            os.environ["AQ_SUBSAMPLE"] = str(subsample)
        else:
            os.environ.pop("AQ_SUBSAMPLE", None)
        E = core.load()
        if not subsample and E.n != len(rows):
            raise SystemExit(f"core kept {E.n} of {len(rows)} rows — predictions could not be aligned")
        blocks = {}
        for slug in MODULES:
            for k, v in (__import__(f"trad_{slug}").build(E) or {}).items():
                key = f"{slug}::{k}"
                if v is None or (keep is not None and key not in keep):
                    continue
                blocks[key] = np.asarray(v, dtype=np.float32)
        return E, blocks

    # PASS 1 — SCREEN on a subsample of couples. Below the threshold this is the whole training half and the
    # two passes see identical data; above it, the screen ranks blocks on a seeded subsample drawn by PERSON
    # GROUP (core.py's own rule, so a couple is never split from its partner's other relationships).
    # HOW BIG THE SCREENING SUBSAMPLE CAN BE IS A PROPERTY OF THE MACHINE, not a number to hardcode. Pass 1
    # holds every block at once, so its footprint is (total columns) x rows x 4 bytes: at a fixed 30,000 couples
    # that is 6.4 GB, which is fine on the 30 GB of a Kaggle notebook and an OOM on a 16 GB laptop with a
    # browser open. The column total is not known until the blocks are built, so it is estimated from the
    # measured 57,132 and corrected by what pass 1 actually reports.
    def screen_budget():
        env = os.environ.get("AQ_SCREEN_COUPLES")
        if env:
            return int(env), "AQ_SCREEN_COUPLES"
        try:
            phys = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True,
                                      text=True).stdout or 0)
        except Exception:
            phys = 0
        if not phys:                                    # not macOS, or sysctl unavailable
            try:
                phys = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            except Exception:
                phys = 8 * 2**30
        n = int(phys * 0.30 / (57132 * 4))
        return max(4000, min(30000, n)), f"30% of {phys/2**30:.0f} GB"

    SCREEN_COUPLES, why = screen_budget()
    sub = SCREEN_COUPLES if len(tr) > SCREEN_COUPLES else 0
    if sub:
        log(f"  screening subsample capped at {SCREEN_COUPLES:,} couples ({why})")
    log(f"building features for the screening pass"
        + (f" ({SCREEN_COUPLES:,}-couple subsample of {len(tr):,})" if sub else f" (all {len(tr):,} rows)"))
    Es, Bs = build(tr, subsample=sub)
    ys = Es.Y.astype(int)
    log(f"  {len(Bs)} blocks · {sum(v.shape[1] for v in Bs.values()):,} columns on {len(ys):,} rows "
        f"({sum(v.nbytes for v in Bs.values())/2**30:.1f} GB)")

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
    sidx = (np.sort(rng.permutation(len(ys))[:SCREEN_ROWS]) if SCREEN_ROWS < len(ys)
            else np.arange(len(ys)))
    sy = ys[sidx]
    sfolds = list(StratifiedKFold(n_splits=3, shuffle=True, random_state=7)
                  .split(np.zeros(len(sidx)), sy))
    log(f"screening {len(Bs)} blocks on {len(sidx):,} rows, 3 folds, one cheap model")
    ranked = []
    for key, X in Bs.items():
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
    # PASS 2 — rebuild ONLY the surviving blocks, at full scale. The screening arrays are freed first, so the
    # two footprints never coexist. `kept_idx` was measured on the subsample: a column constant there but not
    # here is dropped (a real but tiny loss) and one constant here but not there is kept (a harmless constant),
    # and the block WIDTH is a function of the module alone, so the shape contract holds either way.
    keep_keys = {s_["key"] for s_ in chosen}
    del Bs, Es, ys
    gc.collect()
    log(f"  selected {len(chosen)} across {len(per)} traditions; rebuilding those {len(keep_keys)} blocks "
        f"on all {len(tr):,} rows")
    Etr, Btr = build(tr, keep=keep_keys)
    y = Etr.Y.astype(int)
    missing = keep_keys - set(Btr)
    if missing:
        raise SystemExit(f"the full-scale build lost blocks the screen chose: {sorted(missing)[:4]}")
    log(f"  {len(Btr)} blocks · {sum(v.shape[1] for v in Btr.values()):,} columns on {len(y):,} rows "
        f"({sum(v.nbytes for v in Btr.values())/2**30:.1f} GB)")
    for s_ in chosen:
        w = Btr[s_["key"]].shape[1]
        if w != s_["full_cols"]:
            raise SystemExit(f"{s_['key']} is {w} columns at full scale and was {s_['full_cols']} on the "
                             f"screen — a block width changed between passes, which invalidates kept_idx")

    # The baseline and the folds belong to the FULL training half, so they are computed here rather than
    # before the screen.
    YR = 365.2425
    gap = (Etr.JD[1] - Etr.JD[0]) / YR
    folds = list(StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=7).split(np.zeros(len(y)), y))
    bp = np.zeros(len(y))
    for a, b in folds:
        bp[b] = LogisticRegression(max_iter=2000).fit(gap[a, None], y[a]).predict_proba(gap[b, None])[:, 1]
    log(f"  BASELINE two-parameter logistic on the AGE GAP (younger - older): AUC {roc_auc_score(y, bp):.4f}")

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
    # THIS NUMBER IS OPTIMISTIC, AND IT IS A SELECTION SCORE RATHER THAN A PERFORMANCE ESTIMATE. The meta model
    # above is cross-validated, but three things upstream of it are not:
    #
    #   * the base predictions in P were themselves produced over THESE SAME folds, so when the meta trains on
    #     P[a] those values came from base models that had seen fold b's labels;
    #   * each base model's hgb-vs-logit choice is made by comparing AUCs computed on that same OOF vector;
    #   * base-model selection and each block's `kept_idx` column screening ran on the whole training half.
    #
    # Measured under the null — 1,500 rows with coin-flip labels — this prints well above 0.5 while the age-gap
    # baseline beside it correctly prints ~0.5. The honest number for this project is the TEMPORAL HELD-OUT AUC,
    # which finalize.sh step 4 reports against the era rule and the age gap, and which is what the
    # competition is scored on. Quote that one.
    log(f"  STACK in-training selection AUC {cv:.4f} (optimistic — see the note in the source; the honest "
        f"number is the held-out one)")
    log(f"  BASELINE age gap {roc_auc_score(y, bp):.4f}   apparent lift {cv-roc_auc_score(y, bp):+.4f}")

    specs = [{"key": s["key"], "slug": s["slug"], "name": s["name"], "kind": s["kind"],
              "kept_idx": s["kept_idx"], "full_cols": s["full_cols"], "auc": s["auc"],
              "estimator": s["estimator"]} for s in chosen]
    export_model.pack(specs, {"mu": mu, "sd": sd, "coef": meta.coef_.ravel(),
                              "intercept": meta.intercept_[0], "auc": cv,
                              "n": int(len(y)), "rate": float(y.mean()), "hour": "08:00 UT",
                              "contract": "two birth dates only, as published",
                              "baseline": {"logistic on the age gap (younger - older)": float(roc_auc_score(y, bp))}},
                      os.path.join(OUT, "model.json"), os.path.join(OUT, "model.npz"))
    log(f"  exported model.json + model.npz")
    # The per-base out-of-fold matrix and the labels, so every tradition can be scored ALONE afterwards without
    # retraining anything: rank_traditions.py fits a mini-stack over each tradition's own base predictions.
    np.save(os.path.join(OUT, "oof_base.npy"), P.astype(np.float32))
    np.save(os.path.join(OUT, "y_train.npy"), y.astype(np.int8))

    del Btr
    gc.collect()
    log("building features for the test half and predicting")
    Ete, Bte = build(te)
    import predictor
    st = predictor.load(open(os.path.join(OUT, "model.json")).read(),
                        open(os.path.join(OUT, "model.npz"), "rb").read())
    p, P_te = st.proba(Bte)
    np.save(os.path.join(OUT, "test_base.npy"), np.asarray(P_te, dtype=np.float32))   # (n_test, n_base)
    with open(os.path.join(OUT, "submission.csv"), "w", newline="") as f:
        w = csv.writer(f)
        # The submission's prediction column must be named exactly as the training target, or Kaggle scores a
        # column it cannot find. Read from the training header rather than restated here.
        with open(TRAIN) as tf:
            w.writerow(["id", label_column(csv.DictReader(tf).fieldnames)])
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
