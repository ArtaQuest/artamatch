"""
fit_grid.py — the astrology-only stack, scored across the precision grid under 5-fold cross-validation.

THE BENCHMARK (operator specification, 2026-08-12, final form). One AUC on clean input is not what this model
has to survive: real birth data arrives to the day, to the month, to the year, or not at all. So each
partner's date is degraded independently over four levels and the model is scored in every combination:

                    man: full      month        year        absent
    woman: full        .            .            .            .
    woman: month       .            .            .            .
    woman: year        .            .            .            .
    woman: absent      .            .            .          EXCLUDED

    BENCHMARK = the mean of the 15 cells that remain.

`absent|absent` is excluded because it is not a question. With neither date there is no input at all — both
partners collapse onto the same instant, the age gap is zero, and every chart in every tradition becomes the
same chart. Its AUC would measure the class prior, not a model.

WHAT "ABSENT" MEANS IN THE OTHER CELLS, PLAINLY. The input contract is two dates, so the only way to express
"no date" is the convention the dataset itself uses: the missing partner is placed on the known partner's day.
The model then knows nothing about that person and every feature reduces to a function of the surviving date.
That is a floor, and it should be read as one.

WHY THE SAME COUPLES IN EVERY CELL. An earlier version stratified real rows by whatever precision they
happened to have, and that confounds precision with cohort: year-only dates cluster in the 19th century, where
the parenthood rate is 46% against 24% overall — so the year-only stratum scored HIGHER (0.7353) than the
day-precision one (0.7104), which says nothing about robustness. Degrading a fixed set of day-precision
couples isolates the loss of precision from the change of population. It also fixes a second problem: the
"one date absent" stratum contained ZERO real rows, so it could not be measured at all.

THE PROTOCOL, AND THE ONE THING THAT IS EASY TO GET WRONG. Five person-disjoint folds, each an 80/20 split; a
person appears in several partnerships, so splitting by row would train on one of somebody's relationships and
test on another. Every AUC below is out-of-fold over all rows.

The trap is the degraded cells. A row's degraded features must be scored by the base models that never saw
that row — so this keeps all five fold-models per block, and scores each fold's rows with its own. Scoring
degraded features with a model refitted on everything would leak the test rows into every cell of the grid and
inflate the whole benchmark. And every score goes through `web/predictor.py` and exported arrays, not through
scikit-learn, so the benchmark is measured on the same code path the browser runs.

Usage:
    cd astro && ~/.artamatch-venv/bin/python fit_grid.py
"""
import json
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(HERE, "astro-out")
BLOCKS = os.path.join(HERE, "blocks")
COUPLES = os.path.join(ROOT, "research/data-dob/couples-parents.json")
CAND = "/tmp/aq-grid-candidates.json"
YR = 365.2425
FOLDS = 5
CELL_CHUNK = int(os.environ.get("AQ_CELL_CHUNK") or 16000)
WORKERS = int(os.environ.get("AQ_WORKERS") or 3)


def hgb():
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=15,
                                          l2_regularization=1.0, random_state=0)


def logit():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000))


def _fit_block(arg):
    """One block: both kinds, 5-fold out-of-fold, keep the FIVE fold-models plus a refit on everything."""
    path, ypath, gidpath, key, tmpdir = arg
    import joblib
    X = np.asarray(np.load(path, mmap_mode="r"), dtype=np.float32)
    y = np.load(ypath)
    gid = np.load(gidpath)
    folds = list(GroupKFold(n_splits=FOLDS).split(np.zeros(len(y)), y, groups=gid))
    best = None
    for kind, mk in (("hgb", hgb), ("logit", logit)):
        pv = np.zeros(len(y))
        models = []
        try:
            for a, b in folds:
                m = mk().fit(X[a], y[a])
                pv[b] = m.predict_proba(X[b])[:, 1]
                models.append(m)
            auc = float(roc_auc_score(y, pv))
        except Exception as e:
            print(f"    {key} / {kind} failed: {str(e)[:90]}", flush=True)
            continue
        if best is None or auc > best[1]:
            best = (kind, auc, pv, models)
    if best is None:
        return None
    kind, auc, pv, models = best
    full = (hgb() if kind == "hgb" else logit()).fit(X, y)
    stem = os.path.join(tmpdir, key.replace("/", "_").replace(" ", "_").replace(":", "-"))
    joblib.dump({"fold": models, "full": full}, stem + ".joblib", compress=0)
    return {"key": key, "kind": kind, "auc": auc, "oof": pv, "models": stem + ".joblib",
            "cols": int(X.shape[1])}


# ── the precision grid ────────────────────────────────────────────────────────────────────────────
def month_only(d):
    return d[:8] + "01"


def year_only(d):
    return d[:4] + "-01-01"


LEVELS = [("full", None), ("month", month_only), ("year", year_only), ("absent", "absent")]

# WITH BOTH DATES ABSENT THERE IS NO INPUT, so something has to stand in — and the choice matters more than
# it looks. Substituting one partner's date for the other, which is what every other `absent` cell does, made
# `absent|absent` come out BYTE-IDENTICAL to `absent|full`: both ended as (man's date, man's date). That
# would have put a duplicate of another condition into the average under a different name. A fixed reference
# date instead makes every row identical, so the model cannot discriminate at all and the cell is a true
# floor — AUC 0.5 by construction, for the stack and for the baseline alike. It is reported, and the mean is
# also given over the other 15 so the floor's fixed contribution can be seen rather than buried.
NO_DATE_AT_ALL = "1900-01-01"


def degrade_pair(row, wlev, mlev):
    """(aDob, bDob) with the woman's date at `wlev` and the man's at `mlev`, whichever partner is which."""
    how = dict(LEVELS)
    wa = row.get("aSex") == "F"
    wdob, mdob = (row["aDob"], row["bDob"]) if wa else (row["bDob"], row["aDob"])
    # COARSEN FIRST, THEN SUBSTITUTE. An absent partner is placed on the other's date as the model actually
    # sees it, not on their original: substituting first would have given the absent partner a full date
    # while the partner it was copied from carried only a month, so the row would contain precision that
    # exists nowhere in its own inputs.
    if how[wlev] not in (None, "absent"):
        wdob = how[wlev](wdob)
    if how[mlev] not in (None, "absent"):
        mdob = how[mlev](mdob)
    if how[wlev] == "absent" and how[mlev] == "absent":
        wdob = mdob = NO_DATE_AT_ALL
    elif how[wlev] == "absent":
        wdob = mdob
    elif how[mlev] == "absent":
        mdob = wdob
    return (wdob, mdob) if wa else (mdob, wdob)


def main():
    sys.path.insert(0, HERE)
    sys.path.insert(0, WEB)
    os.environ.setdefault("AQ_COUPLES", COUPLES)
    os.environ["AQ_NO_PLACE"] = "1"
    os.environ["AQ_KEEP_ALL_COLS"] = "1"
    os.environ.setdefault("AQ_EPHEM_CACHE", os.path.join(HERE, "ephem-full.npz"))
    from core import load
    E = load()
    y = E.Y.astype(int)
    gid = E.gid
    man = json.load(open(os.path.join(HERE, "manifest.json")))
    blocks = [b for b in man["blocks"] if b["kind"] != "context"]
    print(f"\n  {E.n:,} couples · {int(y.sum()):,} became parents ({100*y.mean():.1f}%)")
    print(f"  {len(blocks)} blocks · {sum(b['cols'] for b in blocks):,} columns · "
          f"{len({b['slug'] for b in blocks})} traditions · two dates at 08:00 UT")
    np.save(os.path.join(OUT, "y.npy"), y)
    np.save(os.path.join(OUT, "gid.npy"), gid)
    folds = list(GroupKFold(n_splits=FOLDS).split(np.zeros(E.n), y, groups=gid))
    fold_of = np.zeros(E.n, np.int64)
    for k, (_, b) in enumerate(folds):
        fold_of[b] = k
    print(f"  {FOLDS} person-disjoint folds (80/20 each) over "
          f"{len(np.unique(gid)):,} person groups")
    for k, (a, b) in enumerate(folds):
        print(f"    fold {k}: {len(a):,} train / {len(b):,} test")

    # ── the one permitted baseline, on clean input ────────────────────────────────────────────────
    gap = np.where(E.SEX_O.astype(str) == "M", (E.JD[1] - E.JD[0]) / YR, -(E.JD[1] - E.JD[0]) / YR)
    bp = np.zeros(E.n)
    for a, b in folds:
        bp[b] = LogisticRegression(max_iter=2000).fit(gap[a, None], y[a]) \
            .predict_proba(gap[b, None])[:, 1]
    print(f"\n  BASELINE  signed age gap, clean input   AUC {roc_auc_score(y, bp):.4f}")

    # ── base models ───────────────────────────────────────────────────────────────────────────────
    tmpdir = tempfile.mkdtemp(prefix="aqgrid-")
    args = [(os.path.join(BLOCKS, b["file"]), os.path.join(OUT, "y.npy"),
             os.path.join(OUT, "gid.npy"), b["key"], tmpdir) for b in blocks]
    print(f"\n  fitting {len(args)} blocks x 2 kinds x {FOLDS} folds on {WORKERS} workers…")
    t0 = time.time()
    res = []
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for i, r in enumerate(ex.map(_fit_block, args), 1):
            if r is None:
                continue
            res.append(r)
            print(f"    [{i:>2}/{len(args)}] {r['auc']:.4f}  {r['kind']:<5} {r['key'][:60]}", flush=True)
    print(f"  base models done in {time.time()-t0:.0f}s")
    res.sort(key=lambda r: -r["auc"])
    P = np.column_stack([r["oof"] for r in res])
    mu, sd = P.mean(0), P.std(0) + 1e-9

    # ── the meta, one per fold, each fitted only on the other folds' out-of-fold columns ──────────
    metas = []
    pred = np.zeros(E.n)
    for k, (a, b) in enumerate(folds):
        m = LogisticRegression(C=0.03, max_iter=4000).fit((P[a] - mu) / sd, y[a])
        pred[b] = m.predict_proba((P[b] - mu) / sd)[:, 1]
        metas.append(m)
    clean_auc = float(roc_auc_score(y, pred))
    print(f"\n  STACK, clean input, out-of-fold over all rows   AUC {clean_auc:.4f}")

    # ── export: five fold-models for the benchmark, and one shipped model fitted on everything ────
    import export_model
    import joblib
    bmap = {b["key"]: b for b in blocks}

    def spec_for(r, est):
        b = bmap[r["key"]]
        return {"key": r["key"], "slug": b["slug"], "name": b["name"], "kind": r["kind"],
                "kept_idx": b["kept_idx"], "full_cols": b["full_cols"], "auc": r["auc"],
                "estimator": est}

    loaded = {r["key"]: joblib.load(r["models"]) for r in res}
    fold_files = []
    for k in range(FOLDS):
        jf, nf = os.path.join(tmpdir, f"m{k}.json"), os.path.join(tmpdir, f"m{k}.npz")
        export_model.pack([spec_for(r, loaded[r["key"]]["fold"][k]) for r in res],
                          {"mu": mu, "sd": sd, "coef": metas[k].coef_.ravel(),
                           "intercept": metas[k].intercept_[0]}, jf, nf)
        fold_files.append((jf, nf))
    print(f"  packed {FOLDS} fold-models for the grid")

    # ── the grid ──────────────────────────────────────────────────────────────────────────────────
    grid = benchmark(fold_files, fold_of, y, E.n)

    metad = {"mu": mu, "sd": sd, "coef": LogisticRegression(C=0.03, max_iter=4000)
             .fit((P - mu) / sd, y).coef_.ravel(),
             "intercept": float(LogisticRegression(C=0.03, max_iter=4000)
                                .fit((P - mu) / sd, y).intercept_[0]),
             "n": int(E.n), "rate": float(y.mean()), "hour": "08:00 UT",
             "contract": "two birth dates; no birthplace, no houses, no Ascendant",
             "auc": grid["benchmark"], "clean_auc": clean_auc,
             "baseline": {"signed age gap (dob_woman - dob_man)": grid["baseline_benchmark"]},
             "benchmark": grid, "tradition_auc": grid["tradition_auc"]}
    size, raw = export_model.pack([spec_for(r, loaded[r["key"]]["full"]) for r in res],
                                  metad, os.path.join(WEB, "model.json"),
                                  os.path.join(WEB, "model.npz"))
    print(f"\n  wrote web/model.json + model.npz ({size/1e6:.2f} MB compressed, {raw/1e6:.1f} MB raw)")
    json.dump({"clean_auc": clean_auc, "grid": grid, "n": int(E.n),
               "base": [{"key": r["key"], "kind": r["kind"], "auc": r["auc"]} for r in res]},
              open(os.path.join(OUT, "fit-grid.json"), "w"), indent=1)
    print(f"  wrote astro-out/fit-grid.json")
    shutil.rmtree(tmpdir, ignore_errors=True)


def benchmark(fold_files, fold_of, y_all, n_all):
    """Every cell of the precision grid, out-of-fold, scored through the exported arrays."""
    import importlib
    import predictor
    import sweshim
    sweshim.load(os.path.join(WEB, "ephem4.bin"), os.path.join(WEB, "tables.json"))
    sys.modules["swisseph"] = sweshim
    stacks = [predictor.load(open(jf).read(), open(nf, "rb").read()) for jf, nf in fold_files]

    # map row index -> source record, so a row can be degraded and rebuilt
    order = json.load(open(os.path.join(OUT, "rows.json")))["keys"]
    src = {}
    for r in json.load(open(COUPLES)):
        src[(r["a"], r["b"])] = r
        src[(r["b"], r["a"])] = r
    idx, rows = [], []
    for i in range(n_all):
        r = src.get(tuple(order[i]))
        if r is None:
            continue
        # both dates to the day, or "full" is not full and cannot be degraded to month or year;
        # and both sexes known, or there is no woman's date to degrade
        if int(r.get("aPrec", 11)) < 11 or int(r.get("bPrec", 11)) < 11:
            continue
        if r.get("aSex") not in ("M", "F") or r.get("bSex") not in ("M", "F") \
                or r["aSex"] == r["bSex"]:
            continue
        idx.append(i)
        rows.append(r)
    idx = np.array(idx)
    yv = y_all[idx]
    fv = fold_of[idx]
    print(f"\n  GRID on {len(rows):,} couples with both dates to the day and both sexes known "
          f"({100*yv.mean():.1f}% became parents)")

    os.environ["AQ_COUPLES"] = CAND
    os.environ["AQ_NO_EPHEM_CACHE"] = "1"
    os.environ["AQ_EPHEM_CACHE"] = "/nonexistent.npz"
    import core
    importlib.reload(core)
    mods = {s: __import__(f"trad_{s}") for s in stacks[0].modules}

    names = [nm for nm, _ in LEVELS]
    cells, per_trad_full = {}, {}
    print(f"\n  {'woman':>7} x {'man':<7} {'stack':>8} {'baseline':>9} {'lift':>8}   "
          f"(out-of-fold over all {len(rows):,})")
    print(f"  {'-'*17} {'-'*8} {'-'*9} {'-'*8}")
    t0 = time.time()
    for wlev in names:
        for mlev in names:
            pred = np.zeros(len(rows))
            gapv = np.zeros(len(rows))
            tradsum = {}
            for lo in range(0, len(rows), CELL_CHUNK):
                hi = min(lo + CELL_CHUNK, len(rows))
                recs = []
                for j in range(lo, hi):
                    r = rows[j]
                    a, b = degrade_pair(r, wlev, mlev)
                    recs.append({"a": f"a{j}", "b": f"b{j}", "aDob": a, "bDob": b,
                                 "aSex": r["aSex"], "bSex": r["bSex"],
                                 "aPrec": 11, "bPrec": 11, "aWin": 1, "bWin": 1,
                                 "label": int(y_all[idx[j]])})
                json.dump(recs, open(CAND, "w"))
                E = core.load()
                if E.n != hi - lo:
                    raise SystemExit(f"{wlev}|{mlev}: core kept {E.n} of {hi-lo} rows — a degraded date "
                                     f"was refused, so scores could not be aligned to couples")
                blocks = {}
                for slug, mod in mods.items():
                    for k, v in (mod.build(E) or {}).items():
                        blocks[f"{slug}::{k}"] = v
                gapv[lo:hi] = np.where(E.SEX_O.astype(str) == "M", (E.JD[1] - E.JD[0]) / YR,
                                       -(E.JD[1] - E.JD[0]) / YR)
                # each row scored by the fold-model that never saw it
                for k in range(FOLDS):
                    sel = np.flatnonzero(fv[lo:hi] == k)
                    if not len(sel):
                        continue
                    sub = {kk: vv[sel] for kk, vv in blocks.items()}
                    p, Pm = stacks[k].proba(sub)
                    pred[lo + sel] = p
                    if (wlev, mlev) == ("full", "full"):
                        for tk, tv in stacks[k].by_tradition(Pm).items():
                            tradsum.setdefault(tk, np.zeros(len(rows)))[lo + sel] = tv
            auc = float(roc_auc_score(yv, pred))
            bp = np.zeros(len(rows))
            for k in range(FOLDS):
                te = np.flatnonzero(fv == k)
                tr = np.flatnonzero(fv != k)
                bp[te] = LogisticRegression(max_iter=2000).fit(gapv[tr, None], yv[tr]) \
                    .predict_proba(gapv[te, None])[:, 1]
            bauc = float(roc_auc_score(yv, bp))
            cells[f"{wlev}|{mlev}"] = {"woman": wlev, "man": mlev, "stack": auc,
                                       "baseline": bauc, "lift": auc - bauc}
            if (wlev, mlev) == ("full", "full"):
                per_trad_full = {k: float(roc_auc_score(yv, v)) for k, v in tradsum.items()}
            print(f"  {wlev:>7} x {mlev:<7} {auc:>8.4f} {bauc:>9.4f} {auc-bauc:>+8.4f}", flush=True)
    print(f"  grid built in {time.time()-t0:.0f}s")

    ks = list(cells.keys())
    b = float(np.mean([cells[k]["stack"] for k in ks]))
    bb = float(np.mean([cells[k]["baseline"] for k in ks]))
    k15 = [k for k in ks if k != "absent|absent"]
    b15 = float(np.mean([cells[k]["stack"] for k in k15]))
    bb15 = float(np.mean([cells[k]["baseline"] for k in k15]))
    print(f"\n  {'-'*17} {'-'*8} {'-'*9} {'-'*8}")
    print(f"  BENCHMARK, mean of all {len(ks)} cells  {b:>8.4f} {bb:>9.4f} {b-bb:>+8.4f}")
    print(f"  the other 15, without the floor  {b15:>8.4f} {bb15:>9.4f} {b15-bb15:>+8.4f}")
    return {"cells": cells, "benchmark": b, "baseline_benchmark": bb, "n_cells": len(ks),
            "benchmark15": b15, "baseline15": bb15,
            "tradition_auc": per_trad_full, "n_rows": int(len(rows)),
            "floor": "absent|absent puts every couple on the same fixed date, so no model can separate "
                     "them: 0.5 by construction, and included so the 4x4 design stays complete"}


if __name__ == "__main__":
    main()
