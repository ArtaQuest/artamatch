"""
ArtaMatch — the astrology-only stack, trained and benchmarked on a Kaggle GPU.

WHY THIS RUNS HERE. Two reasons, and speed is the smaller one. The laptop has 17 GB of RAM against this
machine's 29, so a run there had to build features in chunks and prove chunking equivalent; here the whole
thing fits. And the laptop went to sleep mid-run twice, which killed a three-hour job both times. The GPU
buys something different again: with boosting on the GPU it is affordable to screen EVERY block of EVERY
tradition with several model kinds instead of a chosen few, which is what "exhaustive" has to mean.

WHAT IS TRAINED. One base model per feature block, the better of a GPU-boosted tree ensemble and a
standardised logistic; a meta logistic over their out-of-fold predictions; the whole thing exported as plain
arrays the browser evaluates without scikit-learn.

THE BENCHMARK IS THE HEADLINE, not a single AUC. Each partner's birth date is degraded independently over
four levels — full, month only, year only, absent — and the model is scored in all sixteen combinations:

    BENCHMARK = the mean of the 16 cells.

Also reported: the 15-cell mean excluding `absent|absent`. That cell puts every couple on one fixed date, so
no model can separate them and it is 0.5 by construction; it is in the average because the operator asked for
a complete factorial, and reported separately so its fixed contribution is visible rather than buried.

THE INPUT CONTRACT IS TWO DATES. No birthplace, so no Ascendant, no house cusp, no astrocartography line;
every chart is cast at 08:00 UT. Two traditions are therefore all-constant and drop out on their own.

THREE THINGS THAT ARE EASY TO GET WRONG AND ARE HANDLED HERE

  1. A degraded row must be scored by the fold-model that never saw it. The fold models are all kept and each
     fold's rows are scored with its own. Scoring degraded features with a model refitted on everything would
     leak the test rows into all sixteen cells and inflate the entire benchmark.
  2. Training uses the SHIM, not pyswisseph — which is not a compromise but the stronger choice: the browser
     runs the shim, so training on it removes the last difference between the measured model and the shipped
     one. pyswisseph is not installed here anyway.
  3. Non-human partners are excluded. Wikidata has 10,641 entities with a declared partnership that are not
     P31=Q5 — George Jetson, Jane Jetson and Terry McGinnis among them, with declared spouses and recorded
     children — and 516 rows of the dataset were built from them.
"""
import gc
import json
import os
import sys
import time

import numpy as np

T0 = time.time()
# Overridable so the identical file can be dry-run on the laptop before it costs GPU hours. A dry run with
# AQ_LIMIT set is the only way to find an API mistake in this script without waiting for a Kaggle queue.
IN = os.environ.get("AQ_IN") or "/kaggle/input/artamatch-astrology-couples"
OUT = os.environ.get("AQ_OUT_DIR") or "/kaggle/working"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, IN)

# THE COST BUDGET, set from a measured dry run rather than by hope.
#
# Screening every block of every tradition with every model kind at five folds is about 4,000 boosted fits,
# and the 16-cell grid rebuilds features for every couple in every cell — which at the full 84,000
# day-precision couples is roughly 8 hours of CPU work that no GPU touches, past Kaggle's session limit.
# So the budget is spent where it changes an answer:
#
#   SCREENING decides only which blocks to keep, so it runs on a subsample with three folds and one cheap
#   boosted configuration. A block's rank does not need the final model's precision.
#   FITTING is the shipped model, so it uses every row, five folds and every model kind.
#   THE GRID is a measurement, so it runs on a subsample large enough for the number to mean something —
#   the standard error is printed next to each cell so the precision is explicit rather than implied.
FOLDS = 5
SCREEN_FOLDS = 3
SCREEN_ROWS = int(os.environ.get("AQ_SCREEN_ROWS") or 45000)
GRID_ROWS = int(os.environ.get("AQ_GRID_ROWS") or 25000)
MAX_PER_TRADITION = 3
CELL_CHUNK = int(os.environ.get("AQ_CELL_CHUNK") or 20000)
LIMIT = int(os.environ.get("AQ_LIMIT") or 0)          # dry-run only: keep the first N couples
SEED = 20260812


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


# ── environment, stated rather than assumed ───────────────────────────────────────────────────────
log("environment")
import sklearn
log(f"  numpy {np.__version__}  sklearn {sklearn.__version__}")
GPU = False
try:
    import warnings as _w
    import xgboost as xgb
    log(f"  xgboost {xgb.__version__}")
    # XGBOOST DOES NOT RAISE WHEN THERE IS NO GPU. It emits a warning — "Device is changed from GPU to CPU
    # as we couldn't find any available GPU" — and trains on the CPU anyway, so a try/except around the fit
    # reports success on a machine with no GPU at all. That is what happened on the laptop dry run.
    #
    # Capturing the warning is not reliable either: it is suppressed by verbosity=0, which the first attempt
    # at this check passed, so the check reported a GPU on a machine that has none. TWO independent signals
    # are used instead — ask the driver whether a device exists, and read the warning at default verbosity —
    # and a GPU is only claimed when both agree.
    import subprocess
    have_dev = False
    try:
        r = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=30)
        have_dev = r.returncode == 0 and "GPU 0:" in r.stdout
        if have_dev:
            log(f"  nvidia-smi: {r.stdout.strip().splitlines()[0][:70]}")
    except Exception:
        pass
    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        _t = xgb.XGBClassifier(n_estimators=2, tree_method="hist", device="cuda")
        _t.fit(np.random.rand(64, 4), (np.random.rand(64) > 0.5).astype(int))
        _ = _t.predict_proba(np.random.rand(8, 4))
    fell_back = any("changed from GPU to CPU" in str(c.message)
                    or "couldn't find any available GPU" in str(c.message) for c in caught)
    GPU = have_dev and not fell_back
    if have_dev and fell_back:
        log("  a GPU exists but XGBoost fell back to CPU — treating as unavailable")
    log(f"  GPU boosting: {'available (device=cuda)' if GPU else 'NOT available — XGBoost fell back to CPU'}")
except ImportError:
    log("  xgboost missing — the run will use scikit-learn only")
    xgb = None
except Exception as e:
    log(f"  xgboost unusable ({type(e).__name__}: {str(e)[:90]})")
    xgb = None

# ── the dataset, with the non-human rows removed ──────────────────────────────────────────────────
log("dataset")
rows = json.load(open(f"{IN}/couples-parents.json"))
nh = set(json.load(open(f"{IN}/nonhuman-q5.json"))["qids"])
before = len(rows)
rows = [r for r in rows if r["a"] not in nh and r["b"] not in nh]
NONHUMAN_DROPPED = before - len(rows)      # captured HERE: AQ_LIMIT truncates `rows` below, and reading
                                           # `before - len(rows)` at the end of the run reported 133,005
log(f"  {before:,} couples -> {len(rows):,} after removing non-human partners "
    f"({NONHUMAN_DROPPED:,} dropped)")
if LIMIT:
    rows = rows[:LIMIT]
    log(f"  AQ_LIMIT={LIMIT}: DRY RUN on {len(rows):,} couples — these numbers are not results")
COUPLES = f"{OUT}/couples.json"
json.dump(rows, open(COUPLES, "w"))

os.environ.update({
    "AQ_COUPLES": COUPLES,
    "AQ_NO_PLACE": "1",            # the input contract: two dates and nothing else
    "AQ_KEEP_ALL_COLS": "1",       # block width must be a function of the code, never of the batch
    "AQ_NO_EPHEM_CACHE": "1",      # core.py validates its cache by SHAPE alone; equal-sized batches collide
    "AQ_EPHEM_CACHE": "/nonexistent.npz",
})
for k in ("AQ_SUBSAMPLE", "AQ_BALANCE", "AQ_ROW_INDEX", "AQ_ONLY_KEYS", "AQ_DUMP_ROWS"):
    os.environ.pop(k, None)

import sweshim
sweshim.load(f"{IN}/ephem4.bin", f"{IN}/tables.json")
sys.modules["swisseph"] = sweshim
log("  swisseph shim installed")

import core

# ROW KEYS FIRST. The grid has to map a row of E back to the source record so it can degrade its dates, and
# core.py assigns rows by its own filters. AQ_DUMP_ROWS writes the surviving keys and stops before a single
# planetary position is computed — it exits by raising SystemExit, which is caught here rather than left to
# kill the kernel.
ROWKEYS = f"{OUT}/rowkeys.json"
os.environ["AQ_DUMP_ROWS"] = ROWKEYS
try:
    core.load()
except SystemExit:
    pass
os.environ.pop("AQ_DUMP_ROWS", None)
keys_in_order = json.load(open(ROWKEYS))["keys"]
log(f"  row keys: {len(keys_in_order):,}")

E = core.load()
y = E.Y.astype(int)
gid = E.gid
N = E.n
log(f"  {N:,} couples loaded · {int(y.sum()):,} became parents ({100*y.mean():.2f}%) · "
    f"{len(np.unique(gid)):,} person groups")

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

folds = list(GroupKFold(n_splits=FOLDS).split(np.zeros(N), y, groups=gid))
fold_of = np.zeros(N, np.int64)
for k, (_, b) in enumerate(folds):
    fold_of[b] = k
log(f"  {FOLDS} person-disjoint folds, 80/20 each: " +
    ", ".join(f"{len(b):,}" for _, b in folds))

YR = 365.2425
gap = np.where(E.SEX_O.astype(str) == "M", (E.JD[1] - E.JD[0]) / YR, -(E.JD[1] - E.JD[0]) / YR)
bp = np.zeros(N)
for a, b in folds:
    bp[b] = LogisticRegression(max_iter=2000).fit(gap[a, None], y[a]).predict_proba(gap[b, None])[:, 1]
log(f"  BASELINE signed age gap, clean input: AUC {roc_auc_score(y, bp):.4f}")


# ── the model kinds. Every one exportable to plain arrays, or it cannot be shipped ────────────────
def screen_kinds():
    """Cheap and few — this only has to RANK blocks, not produce the shipped model."""
    ks = []
    if xgb is not None:
        dev = "cuda" if GPU else "cpu"
        ks.append(("xgb", lambda: xgb.XGBClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.08, subsample=0.85,
            colsample_bytree=0.7, reg_lambda=1.0, min_child_weight=4,
            tree_method="hist", device=dev, eval_metric="logloss", random_state=0, verbosity=0)))
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier
        ks.append(("hgb", lambda: HistGradientBoostingClassifier(
            max_iter=150, learning_rate=0.08, max_leaf_nodes=15, l2_regularization=1.0, random_state=0)))
    ks.append(("logit", lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))))
    return ks


def kinds():
    ks = []
    if xgb is not None:
        dev = "cuda" if GPU else "cpu"
        ks += [
            ("xgb", lambda: xgb.XGBClassifier(
                n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.85,
                colsample_bytree=0.7, reg_lambda=1.0, min_child_weight=4,
                tree_method="hist", device=dev, eval_metric="logloss",
                random_state=0, verbosity=0)),
            ("xgb-deep", lambda: xgb.XGBClassifier(
                n_estimators=700, max_depth=8, learning_rate=0.03, subsample=0.7,
                colsample_bytree=0.5, reg_lambda=3.0, min_child_weight=8,
                tree_method="hist", device=dev, eval_metric="logloss",
                random_state=0, verbosity=0)),
        ]
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier
        ks += [("hgb", lambda: HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.06, max_leaf_nodes=15,
            l2_regularization=1.0, random_state=0))]
    ks.append(("logit", lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000))))
    return ks


KINDS = kinds()
SKINDS = screen_kinds()
log(f"  screening kinds {[k for k, _ in SKINDS]} · fitting kinds {[k for k, _ in KINDS]}")

# The screening subsample is drawn BY PERSON GROUP, not by row, so a person never straddles the boundary and
# the inner folds stay leak-free.
rng = np.random.default_rng(SEED)
ug = np.unique(gid)
if SCREEN_ROWS and SCREEN_ROWS < N:
    take = set(rng.permutation(ug)[:max(1, int(len(ug) * SCREEN_ROWS / N))].tolist())
    smask = np.array([g in take for g in gid])
else:
    smask = np.ones(N, bool)
sidx = np.flatnonzero(smask)
sy, sgid = y[sidx], gid[sidx]
sfolds = list(GroupKFold(n_splits=SCREEN_FOLDS).split(np.zeros(len(sidx)), sy, groups=sgid))
log(f"  screening on {len(sidx):,} of {N:,} couples ({100*sy.mean():.1f}% parents), "
    f"{SCREEN_FOLDS} folds; the selected blocks are then refitted on all {N:,}")

import export_model

MODULES = json.load(open(f"{IN}/modules.json"))["modules"]
log(f"screening {len(MODULES)} traditions")

# ── SCREEN: build one module at a time, fit every block, keep only what is small ──────────────────
# Never hold all blocks: all 254 of them at this row count is 30 GB. A module's blocks are built, fitted,
# reduced to an out-of-fold vector and a set of fold models, then freed.
screen = []
for mi, slug in enumerate(MODULES, 1):
    t = time.time()
    try:
        mod = __import__(f"trad_{slug}")
        blocks = mod.build(E) or {}
    except Exception as e:
        log(f"  [{mi:>2}/{len(MODULES)}] {slug:<22} FAILED {type(e).__name__}: {str(e)[:80]}")
        continue
    kept = 0
    for name, X in blocks.items():
        if X is None:
            continue
        X = np.asarray(X, dtype=np.float32)
        if X.ndim != 2 or X.shape[0] != N:
            continue
        keep = X.std(0) > 1e-12
        if keep.sum() == 0:
            continue
        kept_idx = np.flatnonzero(keep)
        full_cols = int(X.shape[1])
        Xs = np.ascontiguousarray(X[sidx][:, kept_idx])
        best = None
        for kind, mk in SKINDS:
            pv = np.zeros(len(sidx))
            try:
                for a, b in sfolds:
                    pv[b] = mk().fit(Xs[a], sy[a]).predict_proba(Xs[b])[:, 1]
                auc = float(roc_auc_score(sy, pv))
            except Exception as e:
                print(f"      {slug}::{name} / {kind}: {type(e).__name__} {str(e)[:70]}", flush=True)
                continue
            if best is None or auc > best:
                best = auc
        if best is None:
            continue
        # Nothing but the score and the column list is kept. The models fitted here are throwaway: their job
        # was to rank this block, and the ones that ship are refitted below on every row.
        screen.append({"key": f"{slug}::{name}", "slug": slug, "name": name,
                       "kept_idx": kept_idx.tolist(), "full_cols": full_cols, "screen_auc": best})
        kept += 1
        del Xs
    del blocks, X
    gc.collect()
    log(f"  [{mi:>2}/{len(MODULES)}] {slug:<22} {kept:>3} blocks  {time.time()-t:>6.1f}s  "
        f"best {max((s['screen_auc'] for s in screen if s['slug'] == slug), default=0):.4f}")

log(f"screened {len(screen)} blocks across {len({s['slug'] for s in screen})} traditions")
json.dump(sorted([{"key": s["key"], "slug": s["slug"], "screen_auc": s["screen_auc"],
                   "cols": len(s["kept_idx"])} for s in screen], key=lambda r: -r["screen_auc"]),
          open(f"{OUT}/screen.json", "w"), indent=1)

# ── SELECT: up to three blocks from EVERY tradition, a per-tradition guarantee ────────────────────
per, chosen = {}, []
for s in sorted(screen, key=lambda r: -r["screen_auc"]):
    if per.get(s["slug"], 0) >= MAX_PER_TRADITION:
        continue
    per[s["slug"]] = per.get(s["slug"], 0) + 1
    chosen.append(s)
log(f"selected {len(chosen)} base models across {len(per)} traditions")
for slug in sorted(per, key=lambda t: -max(s["screen_auc"] for s in chosen if s["slug"] == t)):
    aucs = ", ".join(f"{s['screen_auc']:.4f}" for s in chosen if s["slug"] == slug)
    log(f"    {slug:<24} {aucs}")

# ── FIT: rebuild ONLY the selected blocks, on every row, with every kind and five folds ───────────
# A second pass over the modules that own a selected block. Rebuilding is cheaper than having held 30 GB of
# blocks through the screen, and it is the same code producing the same numbers either way.
log(f"fitting {len(chosen)} selected blocks at full scale")
by_mod = {}
for s in chosen:
    by_mod.setdefault(s["slug"], []).append(s)
for mi, (slug, group) in enumerate(sorted(by_mod.items()), 1):
    t = time.time()
    blocks = __import__(f"trad_{slug}").build(E) or {}
    for s in group:
        X = np.asarray(blocks[s["name"]], dtype=np.float32)
        if X.shape[1] != s["full_cols"]:
            raise SystemExit(f"{s['key']}: rebuilt {X.shape[1]} columns, screened {s['full_cols']} — a "
                             f"block's width must be a function of the code, never of the batch")
        Xk = np.ascontiguousarray(X[:, np.asarray(s["kept_idx"])])
        best = None
        for kind, mk in KINDS:
            pv = np.zeros(N)
            models = []
            try:
                for a, b in folds:
                    m = mk().fit(Xk[a], y[a])
                    pv[b] = m.predict_proba(Xk[b])[:, 1]
                    models.append(m)
                auc = float(roc_auc_score(y, pv))
            except Exception as e:
                print(f"      {s['key']} / {kind}: {type(e).__name__} {str(e)[:70]}", flush=True)
                continue
            if best is None or auc > best["auc"]:
                best = {"auc": auc, "kind": kind, "mk": mk, "oof": pv.astype(np.float32),
                        "models": models}
        if best is None:
            raise SystemExit(f"{s['key']}: no model kind could be fitted")
        # Flatten the winner and refit on all rows exactly once. A fitted estimator is large and
        # version-bound; the flat arrays are neither, so nothing past this point holds an estimator.
        flatten = (export_model.flatten_xgb if best["kind"].startswith("xgb")
                   else export_model.flatten_hgb if best["kind"].startswith("hgb")
                   else export_model.flatten_linear)
        best["flat"] = [flatten(m) for m in best["models"]]
        best["full"] = flatten(best["mk"]().fit(Xk, y))
        del best["models"], best["mk"]
        s.update(best)
        log(f"    {s['auc']:.4f}  {s['kind']:<8} {s['key'][:58]}  (screen said {s['screen_auc']:.4f})")
        del Xk, X
    del blocks
    gc.collect()
    log(f"  [{mi:>2}/{len(by_mod)}] {slug:<22} {time.time()-t:>6.1f}s")

P = np.column_stack([s["oof"] for s in chosen]).astype(np.float64)
mu, sd = P.mean(0), P.std(0) + 1e-9
metas = []
pred = np.zeros(N)
for k, (a, b) in enumerate(folds):
    m = LogisticRegression(C=0.03, max_iter=4000).fit((P[a] - mu) / sd, y[a])
    pred[b] = m.predict_proba((P[b] - mu) / sd)[:, 1]
    metas.append(m)
clean = float(roc_auc_score(y, pred))
log(f"STACK clean input, out-of-fold: AUC {clean:.4f}")
meta_full = LogisticRegression(C=0.03, max_iter=4000).fit((P - mu) / sd, y)


def pack(which, path_json, path_npz, coef, intercept, extra=None):
    """Write a model file from ALREADY FLATTENED arrays — no estimator objects survive this far."""
    arrays, header = {}, {"base": [], "traditions": []}
    for i, s in enumerate(chosen):
        p = f"b{i}"
        flat = s["full"] if which == "full" else s["flat"][which]
        for k, v in flat.items():
            arrays[f"{p}_{k}"] = v
        arrays[f"{p}_kept"] = np.asarray(s["kept_idx"], np.int32)
        header["base"].append({"key": s["key"], "slug": s["slug"], "name": s["name"],
                               "kind": s["kind"], "cols": len(s["kept_idx"]),
                               "full_cols": s["full_cols"], "auc": s["auc"]})
    seen = []
    for b in header["base"]:
        if b["slug"] not in seen:
            seen.append(b["slug"])
    header["traditions"] = seen
    arrays["meta_mu"] = mu
    arrays["meta_sd"] = sd
    arrays["meta_coef"] = np.asarray(coef, np.float64)
    arrays["meta_int"] = np.asarray([float(intercept)], np.float64)
    header.update(extra or {})
    np.savez_compressed(path_npz, **arrays)
    json.dump(header, open(path_json, "w"), indent=1)


fold_files = []
for k in range(FOLDS):
    jf, nf = f"{OUT}/fold{k}.json", f"{OUT}/fold{k}.npz"
    pack(k, jf, nf, metas[k].coef_.ravel(), metas[k].intercept_[0])
    fold_files.append((jf, nf))
log(f"packed {FOLDS} fold-models for the grid")

# ── THE GRID ──────────────────────────────────────────────────────────────────────────────────────
import predictor

stacks = [predictor.load(open(j).read(), open(n, "rb").read()) for j, n in fold_files]
need_mods = stacks[0].modules
need_keys = {b["key"] for b in stacks[0].h["base"]}

src = {}
for r in rows:
    src[(r["a"], r["b"])] = r
    src[(r["b"], r["a"])] = r
idx, grows = [], []
for i, kk in enumerate(keys_in_order):
    r = src.get(tuple(kk))
    if r is None:
        continue
    if int(r.get("aPrec", 11)) < 11 or int(r.get("bPrec", 11)) < 11:
        continue
    if r.get("aSex") not in ("M", "F") or r.get("bSex") not in ("M", "F") or r["aSex"] == r["bSex"]:
        continue
    idx.append(i)
    grows.append(r)
idx = np.array(idx)
# A SUBSAMPLE, BY PERSON GROUP, and its precision is printed rather than assumed. Sixteen cells each rebuild
# every feature from the dates, which at the full day-precision population is about eight hours of CPU work
# no GPU touches. The Hanley-McNeil standard error below says what the resulting number is worth; raise
# AQ_GRID_ROWS to trade time for precision.
if GRID_ROWS and GRID_ROWS < len(idx):
    gg = np.unique(gid[idx])
    keepg = set(np.random.default_rng(SEED + 1)
                .permutation(gg)[:max(1, int(len(gg) * GRID_ROWS / len(idx)))].tolist())
    sel = [j for j, i in enumerate(idx) if gid[i] in keepg]
    idx = idx[sel]
    grows = [grows[j] for j in sel]
yv, fv = y[idx], fold_of[idx]


def auc_se(a, n1, n0):
    """Hanley-McNeil standard error of an AUC — what one cell of the grid is actually worth."""
    q1 = a / (2.0 - a)
    q2 = 2.0 * a * a / (1.0 + a)
    v = (a * (1 - a) + (n1 - 1) * (q1 - a * a) + (n0 - 1) * (q2 - a * a)) / (n1 * n0)
    return float(np.sqrt(max(v, 0.0)))


N1, N0 = int(yv.sum()), int((1 - yv).sum())
log(f"GRID on {len(grows):,} couples with both dates to the day and both sexes known "
    f"({100*yv.mean():.1f}% parents; {N1:,} positive, {N0:,} negative)")
log(f"  a cell's standard error at AUC 0.70 is about {auc_se(0.70, N1, N0):.4f}")


def month_only(d):
    return d[:8] + "01"


def year_only(d):
    return d[:4] + "-01-01"


LEVELS = [("full", None), ("month", month_only), ("year", year_only), ("absent", "absent")]
NO_DATE = "1900-01-01"


def degrade_pair(row, wlev, mlev):
    how = dict(LEVELS)
    wa = row.get("aSex") == "F"
    w, m = (row["aDob"], row["bDob"]) if wa else (row["bDob"], row["aDob"])
    if how[wlev] not in (None, "absent"):
        w = how[wlev](w)
    if how[mlev] not in (None, "absent"):
        m = how[mlev](m)
    if how[wlev] == "absent" and how[mlev] == "absent":
        w = m = NO_DATE
    elif how[wlev] == "absent":
        w = m
    elif how[mlev] == "absent":
        m = w
    return (w, m) if wa else (m, w)


CELLS_PATH = f"{OUT}/cells.json"
cells = json.load(open(CELLS_PATH)) if os.path.exists(CELLS_PATH) else {}
names = [n for n, _ in LEVELS]
per_trad = {}
log(f"{'woman':>7} x {'man':<7} {'stack':>8} {'se':>7} {'baseline':>9} {'lift':>8}")
for wlev in names:
    for mlev in names:
        cell = f"{wlev}|{mlev}"
        if cell in cells:
            log(f"  {wlev:>7} x {mlev:<7} {cells[cell]['stack']:>8.4f} (cached from an earlier session)")
            continue
        t = time.time()
        pv = np.zeros(len(grows))
        gv = np.zeros(len(grows))
        trad_acc = {}
        for lo in range(0, len(grows), CELL_CHUNK):
            hi = min(lo + CELL_CHUNK, len(grows))
            recs = []
            for j in range(lo, hi):
                r = grows[j]
                a, b = degrade_pair(r, wlev, mlev)
                recs.append({"a": f"a{j}", "b": f"b{j}", "aDob": a, "bDob": b,
                             "aSex": r["aSex"], "bSex": r["bSex"], "aPrec": 11, "bPrec": 11,
                             "aWin": 1, "bWin": 1, "label": int(yv[j])})
            json.dump(recs, open(COUPLES, "w"))
            Ec = core.load()
            if Ec.n != hi - lo:
                raise SystemExit(f"{cell}: core kept {Ec.n} of {hi-lo} rows — scores cannot be aligned")
            blk = {}
            for slug in need_mods:
                for nm2, v in (__import__(f"trad_{slug}").build(Ec) or {}).items():
                    kk2 = f"{slug}::{nm2}"
                    if kk2 in need_keys:
                        blk[kk2] = v
            gv[lo:hi] = np.where(Ec.SEX_O.astype(str) == "M", (Ec.JD[1] - Ec.JD[0]) / YR,
                                 -(Ec.JD[1] - Ec.JD[0]) / YR)
            for k in range(FOLDS):
                sel = np.flatnonzero(fv[lo:hi] == k)
                if not len(sel):
                    continue
                p2, Pm = stacks[k].proba({kk2: vv[sel] for kk2, vv in blk.items()})
                pv[lo + sel] = p2
                if cell == "full|full":
                    for tk, tv in stacks[k].by_tradition(Pm).items():
                        trad_acc.setdefault(tk, np.zeros(len(grows)))[lo + sel] = tv
            del blk
            gc.collect()
        auc = float(roc_auc_score(yv, pv))
        bpv = np.zeros(len(grows))
        for k in range(FOLDS):
            te, tr = np.flatnonzero(fv == k), np.flatnonzero(fv != k)
            bpv[te] = LogisticRegression(max_iter=2000).fit(gv[tr, None], yv[tr]) \
                .predict_proba(gv[te, None])[:, 1]
        bauc = float(roc_auc_score(yv, bpv))
        cells[cell] = {"woman": wlev, "man": mlev, "stack": auc, "baseline": bauc, "lift": auc - bauc,
                       "se": auc_se(auc, N1, N0)}
        if cell == "full|full":
            per_trad = {k: float(roc_auc_score(yv, v)) for k, v in trad_acc.items()}
            json.dump(per_trad, open(f"{OUT}/tradition_auc.json", "w"), indent=1)
        json.dump(cells, open(CELLS_PATH, "w"), indent=1)
        log(f"  {wlev:>7} x {mlev:<7} {auc:>8.4f} {cells[cell]['se']:>7.4f} {bauc:>9.4f} "
            f"{auc-bauc:>+8.4f}   {time.time()-t:.0f}s")

ks = list(cells.keys())
bench = float(np.mean([cells[k]["stack"] for k in ks]))
bbase = float(np.mean([cells[k]["baseline"] for k in ks]))
k15 = [k for k in ks if k != "absent|absent"]
b15 = float(np.mean([cells[k]["stack"] for k in k15]))
bb15 = float(np.mean([cells[k]["baseline"] for k in k15]))
log(f"BENCHMARK mean of all {len(ks)} cells  {bench:.4f}   baseline {bbase:.4f}   lift {bench-bbase:+.4f}")
log(f"          the other 15, no floor      {b15:.4f}   baseline {bb15:.4f}   lift {b15-bb15:+.4f}")

grid = {"cells": cells, "benchmark": bench, "baseline_benchmark": bbase, "n_cells": len(ks),
        "benchmark15": b15, "baseline15": bb15, "tradition_auc": per_trad, "n_rows": len(grows),
        "cell_se": auc_se(bench, N1, N0), "positives": N1, "negatives": N0,
        "floor": "absent|absent puts every couple on one fixed date, so the features are identical for every "
                 "row and nothing about a couple can separate it from another. It is not exactly 0.5 "
                 "though, and the reason is the protocol rather than the model: each row is scored by the "
                 "fold-model that never saw it, those five models differ slightly, and fold membership is "
                 "not perfectly independent of the label. So this cell measures fold-model disagreement, "
                 "and it should be read as 0.5 give or take one standard error. It is included because the "
                 "operator asked for a complete 4x4 factorial."}
pack("full", f"{OUT}/model.json", f"{OUT}/model.npz",
     meta_full.coef_.ravel(), meta_full.intercept_[0],
     extra={"auc": bench, "clean_auc": clean, "n": int(N), "rate": float(y.mean()),
            "hour": "08:00 UT", "gpu": GPU,
            "contract": "two birth dates; no birthplace, no houses, no Ascendant",
            "baseline": {"signed age gap (dob_woman - dob_man)": bbase},
            "benchmark": grid, "tradition_auc": per_trad,
            "nonhuman_dropped": NONHUMAN_DROPPED})
json.dump({"benchmark": grid, "clean_auc": clean, "n": int(N), "gpu": GPU,
           "screened": len(screen), "selected": len(chosen),
           "base": [{"key": s["key"], "kind": s["kind"], "auc": s["auc"]} for s in chosen]},
          open(f"{OUT}/result.json", "w"), indent=1)
for k in range(FOLDS):
    for ext in ("json", "npz"):
        try:
            os.remove(f"{OUT}/fold{k}.{ext}")
        except OSError:
            pass
for f in (COUPLES, ROWKEYS):
    try:
        os.remove(f)
    except OSError:
        pass
log(f"wrote model.json, model.npz, screen.json, result.json — done in {(time.time()-T0)/60:.1f} min")
