"""
run.py — the modelling side: collect every tradition's blocks, sweep representations and model families,
then build the strongest ensemble they support.

Staged, because the full cross product is far too big to run blind. Each stage caches its output so the
later ones are cheap to re-run.

    collect   import every trad_*.py, build its blocks, cache each as float32 .npy + a manifest
    screen    every block x 3 fast models x 8 splits -> a ranking, so the deep sweep is spent well
    deep      the surviving blocks x the full model zoo x 20 splits, plus REPRESENTATION variants
    oof       out-of-fold predictions for the chosen (block, model, representation) triples
    stack     greedy ensemble selection (Caruana) + meta-learners, scored under nested group CV
    report    the final table

REPRESENTATION VARIANTS, applied to every surviving block, because the same doctrine encoded differently
scores differently and that is half the experiment:

    raw          standardised only
    pca          standardised -> PCA, keeping enough components for 95% of variance
    rff          random Fourier features, an explicit approximation to an RBF kernel
    quantile     rank-transformed to uniform, which kills monotone scale artefacts
    inter        all pairwise products, for blocks small enough to afford it
    topk         univariate-screened to the k strongest columns (screening INSIDE each fold only)

Every fit is scored on person-disjoint splits from evalx, so a person in two marriages cannot straddle
train and test. Every number is a mean over splits with its spread.

Usage:
    cd /Users/arash/Studio/artamatch/astro
    /tmp/aqpy/bin/python run.py collect
    /tmp/aqpy/bin/python run.py screen
    /tmp/aqpy/bin/python run.py deep
    /tmp/aqpy/bin/python run.py oof
    /tmp/aqpy/bin/python run.py stack
"""

import glob
import importlib
import json
import os
import sys
import time
import numpy as np

from core import load
import evalx
from evalx import MODELS, splits, _clean, fit_predict

from sklearn.decomposition import PCA
from sklearn.kernel_approximation import RBFSampler
from sklearn.preprocessing import StandardScaler, QuantileTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

HERE = os.path.dirname(os.path.abspath(__file__))
# On Kaggle the working directory is read-only except /kaggle/working, so every artefact goes to OUTDIR.
OUTDIR = os.environ.get("AQ_OUTDIR") or HERE
CACHE = os.environ.get("AQ_BLOCKS") or os.path.join(HERE, "blocks")
MANIFEST = os.environ.get("AQ_OUT_MANIFEST") or os.path.join(OUTDIR, "manifest.json")
SCREEN = os.environ.get("AQ_OUT_SCREEN") or os.path.join(OUTDIR, "screen.json")
DEEP = os.environ.get("AQ_OUT_DEEP") or os.path.join(OUTDIR, "deep.json")
OOF = os.environ.get("AQ_OUT_OOF") or os.path.join(OUTDIR, "oof.npz")
STACK = os.environ.get("AQ_OUT_STACK") or os.path.join(OUTDIR, "stack.json")

SCREEN_MODELS = ["logistic L2 (C=0.1)", "hist gradient boosting"]
SCREEN_SPLITS = 5
DEEP_SPLITS = 8
KEEP_FOR_DEEP = 22          # blocks carried into the deep sweep
KEEP_FOR_OOF = 90           # (block, model, representation) triples carried into stacking



# ── parallelism ─────────────────────────────────────────────────────────────────────────────────
# One process per block with a SINGLE thread each, rather than one block at a time across all cores.
# scikit-learn's OpenMP threading scales badly at 2,296 rows: the per-tree work is too small to amortise
# the thread barriers, so eight one-thread workers beat one eight-thread worker by a wide margin here.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

WORKERS = int(os.environ.get("AQ_WORKERS") or max(1, (os.cpu_count() or 4) - 2))
_W = {}


def _winit():
    """Per-worker one-time setup: load the couples and the shared splits."""
    from core import load as _load
    _W["E"] = _load()
    _W["sp5"] = splits(_W["E"], n=SCREEN_SPLITS)
    _W["spD"] = splits(_W["E"], n=DEEP_SPLITS)


def _pmap(fn, items, workers=None):
    """Map fn over items in worker processes, yielding results as they finish."""
    from concurrent.futures import ProcessPoolExecutor, as_completed
    with ProcessPoolExecutor(max_workers=workers or WORKERS, initializer=_winit) as ex:
        futs = {ex.submit(fn, it): it for it in items}
        for f in as_completed(futs):
            yield futs[f], f.result()


# ── stage: collect ──────────────────────────────────────────────────────────────────────────────
def _only_keys():
    f = os.environ.get("AQ_ONLY_KEYS")
    if not f:
        return None
    rows = json.load(open(f))
    ks = {r["key"] if isinstance(r, dict) else r for r in rows}
    print(f"  AQ_ONLY_KEYS: saving only {len(ks)} blocks")
    return ks


_ONLY_KEYS = None


def collect():
    global _ONLY_KEYS
    _ONLY_KEYS = _only_keys()
    E = load()
    os.makedirs(CACHE, exist_ok=True)
    sys.path.insert(0, HERE)
    man = {"blocks": [], "modules": []}
    from core import MARRIAGE_MODULES
    paths = sorted(glob.glob(os.path.join(HERE, "trad_*.py"))) + sorted(glob.glob(os.path.join(HERE, "ctx_*.py")))
    # AQ_ONLY restricts the run to a permitted set of modules. Used to enforce an INPUT CONTRACT: the
    # deployed model may see only the two birth dates and the two birthplaces, so the citizenship and sex
    # blocks must be excluded by configuration rather than by hoping nobody selects them.
    only = [x.strip() for x in (os.environ.get("AQ_ONLY") or "").split(",") if x.strip()]
    if only:
        paths = [p for p in paths if os.path.basename(p)[:-3].split("_", 1)[1] in only]
        print(f"  AQ_ONLY: restricted to {len(paths)} modules — {', '.join(only)}")
    for path in paths:
        base = os.path.basename(path)[:-3]
        slug = base.split("_", 1)[1]
        kind = "context" if base.startswith("ctx_") else "tradition"
        if not getattr(E, "HAS_WEDDING", True) and slug in MARRIAGE_MODULES:
            print(f"  {slug:<22} SKIPPED — needs a marriage date, and this dataset has none")
            continue
        t0 = time.time()
        try:
            mod = importlib.import_module(base)
            blocks = mod.build(E)
        except Exception as e:
            print(f"  {slug:<22} FAILED to build: {str(e)[:100]}")
            man["modules"].append({"slug": slug, "kind": kind, "ok": False, "error": str(e)[:300]})
            continue
        trad = getattr(mod, "TRADITION", slug)
        kept = 0
        for name, X in blocks.items():
            key_full = f"{slug}::{name}"
            X = _clean(X)
            if X.ndim != 2 or X.shape[0] != E.n:
                print(f"  {slug}/{name}: bad shape {X.shape}, skipped")
                continue
            keep = X.std(0) > 1e-12
            # AQ_KEEP_ALL_COLS disables constant-column pruning. It exists for PREDICTION: a scoring batch
            # legitimately has constant columns (every candidate shares the fixed partner, every date is
            # day-precision), so pruning there would hand the model a different column set than it was
            # trained on. The training manifest records which columns it kept, and prediction selects
            # exactly those — see train_final.py and _score_batch.py.
            if os.environ.get("AQ_KEEP_ALL_COLS") == "1":
                keep = np.ones(X.shape[1], dtype=bool)
            if keep.sum() == 0:
                print(f"  {slug}/{name}: all columns constant, skipped")
                continue
            # AQ_ONLY_KEYS restricts which blocks are SAVED (all of a module's blocks are still built —
            # they come out of one build() call). All 268 blocks unpruned at 135,005 rows is 32 GB on disk;
            # the 57 the stack actually selects is 6.7 GB, and the machine has 45 GB free.
            if _ONLY_KEYS is not None and key_full not in _ONLY_KEYS:
                continue
            kept_idx = np.flatnonzero(keep).tolist()
            X = X[:, keep]
            key = f"{slug}::{name}"
            np.save(os.path.join(CACHE, key.replace("/", "_").replace(" ", "_") + ".npy"),
                    X.astype(np.float32))
            man["blocks"].append({"key": key, "slug": slug, "kind": kind, "name": name, "cols": int(X.shape[1]),
                                  "dropped_constant": int((~keep).sum()), "kept_idx": kept_idx,
                                  "full_cols": int(len(keep)),
                                  "file": key.replace("/", "_").replace(" ", "_") + ".npy"})
            kept += 1
        man["modules"].append({"slug": slug, "kind": kind, "ok": True, "tradition": trad, "blocks": kept,
                               "seconds": round(time.time() - t0, 1)})
        print(f"  {slug:<22} {kept:>3} blocks  {time.time()-t0:>6.1f}s  {trad[:50]}")
    json.dump(man, open(MANIFEST, "w"), indent=1)
    tot = sum(b["cols"] for b in man["blocks"])
    print(f"\n{len(man['blocks'])} blocks, {tot:,} columns total, from "
          f"{sum(1 for m in man['modules'] if m['ok'])} modules")


def _blocks():
    man = json.load(open(MANIFEST))
    return man, {b["key"]: os.path.join(CACHE, b["file"]) for b in man["blocks"]}


def _get(files, key):
    return np.load(files[key]).astype(np.float64)


# ── representations ─────────────────────────────────────────────────────────────────────────────
def represent(kind, ncol, seed=0):
    """A representation is a prefix pipeline; the model is appended after it."""
    if kind == "raw":
        return [StandardScaler()]
    if kind == "pca":
        # Randomised solver with a fixed component budget. The full solver with a 0.95 variance target
        # was the single biggest cost in this sweep: it recomputes an exact SVD of a 2,296 x 1,296 matrix,
        # and it was being refitted once per model rather than once per fold.
        return [StandardScaler(), PCA(n_components=min(96, max(2, ncol // 2)),
                                      svd_solver="randomized", random_state=seed)]
    if kind == "rff":
        return [StandardScaler(), RBFSampler(gamma=1.0 / max(ncol, 1), n_components=min(512, 8 * ncol),
                                             random_state=seed)]
    if kind == "quantile":
        return [QuantileTransformer(output_distribution="uniform", n_quantiles=256,
                                    subsample=100000, random_state=seed)]
    if kind == "inter":
        from sklearn.preprocessing import PolynomialFeatures
        return [StandardScaler(), PolynomialFeatures(2, interaction_only=True, include_bias=False)]
    if kind == "topk":
        return [StandardScaler(), SelectKBest(f_classif, k=min(48, ncol))]
    raise ValueError(kind)


def reps_for(ncol):
    """Representations worth trying at this width.

    Trimmed to three for the deep sweep: the raw standardised block, a univariate-screened top-k (which
    won the best result in the first partial sweep), and a PCA projection. Quantile, random Fourier
    features and pairwise interactions never won a block in the partial sweep and cost as much as the
    three that did.
    """
    r = ["raw"]
    if ncol > 8:
        r += ["topk", "pca"]
    if ncol <= 22:
        r += ["inter"]
    return r


def pipe(rep, ncol, model_factory, seed=0):
    return make_pipeline(*represent(rep, ncol, seed), model_factory())


# ── stage: screen ───────────────────────────────────────────────────────────────────────────────

def _screen_one(arg):
    key, path = arg
    E, sp = _W["E"], _W["sp5"]
    X = np.load(path).astype(np.float64)
    best = None
    for mn in SCREEN_MODELS:
        f = MODELS(X.shape[1]).get(mn)
        if f is None:
            continue
        A, U = [], []
        try:
            for tr, te in sp:
                p = fit_predict(f, X, E.Y, tr, te)
                A.append(((p > 0.5).astype(float) == E.Y[te]).mean())
                U.append(roc_auc_score(E.Y[te], p))
        except Exception as e:
            return {"error": f"{mn}: {str(e)[:70]}"}
        r = {"model": mn, "acc": float(np.mean(A)), "auc": float(np.mean(U)), "acc_sd": float(np.std(A))}
        if best is None or r["auc"] > best["auc"]:
            best = r
    return best or {"error": "no model succeeded"}

def screen():
    """Screen every block, resumably and in parallel.

    Each result is keyed by the block name AND a hash of its cached array, so a re-run after a module is
    edited rescores only the blocks whose data actually changed. Without that, one fix to one tradition
    would cost the whole sweep again.
    """
    import hashlib
    man, files = _blocks()
    done = {}
    if os.path.exists(SCREEN):
        for r in json.load(open(SCREEN)):
            if "hash" in r:
                done[(r["key"], r["hash"])] = r
    rows, todo = [], []
    for b in man["blocks"]:
        h = hashlib.md5(open(files[b["key"]], "rb").read()).hexdigest()[:16]
        if (b["key"], h) in done:
            rows.append(done[(b["key"], h)])
        else:
            todo.append({**b, "hash": h})
    print(f"  {len(rows)} cached, {len(todo)} to score, {WORKERS} workers")
    n = 0
    for item, res in _pmap(_screen_one, [(t["key"], files[t["key"]]) for t in todo]):
        n += 1
        t = next(x for x in todo if x["key"] == item[0])
        if "error" in res:
            print(f"  [{n:>3}/{len(todo)}] {t['key'][:52]:<52} FAILED {res['error']}", flush=True)
            continue
        rows.append({**t, **res})
        print(f"  [{n:>3}/{len(todo)}] {t['key'][:52]:<52} {t['cols']:>5} cols "
              f"{100*res['acc']:>6.2f}%  AUC {res['auc']:.4f}  ({res['model'][:20]})", flush=True)
        if n % 5 == 0:
            json.dump(sorted(rows, key=lambda r: -r["auc"]), open(SCREEN, "w"), indent=1)
    rows.sort(key=lambda r: -r["auc"])
    json.dump(rows, open(SCREEN, "w"), indent=1)
    print(f"\ntop 20 blocks by AUC:")
    for r in rows[:20]:
        print(f"  {r['auc']:.4f}  {100*r['acc']:>6.2f}%  {r['cols']:>5} cols  {r['key']}")



# Everything appended to an astrology block to make the model context-aware: nationality and birthplace,
# plus date precision and the per-body reliability that goes with it. The precision block scores ~0.518 on
# its own — as it should, precision does not predict prominence — but it is what lets a tree learn "for
# THIS couple the Sun is unknown and Jupiter is exact", which is the honest way to use a year-precision row.
# Under the four-input contract the context arm is coordinates + date precision + cohort. Citizenship and
# sex are NOT inputs the page can collect, so "nationality" is deliberately absent here.
CONTEXT_KEYS = [x.strip() for x in (os.environ.get("AQ_CONTEXT_KEYS") or
                "geo4::geo: EVERYTHING,precision::prec: EVERYTHING,cohort::coh: EVERYTHING").split(",")]


def _deep_one(arg):
    """All models for ONE (block, representation), sharing the fitted representation per fold.

    Fitting the representation inside every model's pipeline meant a 1,296-column block paid for its PCA
    eleven times per fold. Here the representation is fitted once per fold and every model sees the same
    transformed matrices, which is both faster and a fairer comparison between the models.
    """
    key, path, rep, models, ctxpath = arg
    E, sp = _W["E"], _W["spD"]
    X = np.load(path).astype(np.float64)
    if ctxpath:
        # CONTEXT-AWARE: birthplace and nationality (Wikipedia coverage is very uneven by country, so a
        # model blind to it cannot express that) plus date precision and per-body reliability (so a
        # year-precision row can be used for Jupiter outward and discounted for the Sun and Moon).
        X = np.concatenate([X] + [np.load(c).astype(np.float64) for c in ctxpath], axis=1)
    ncol = X.shape[1]
    out = []
    per_model = {m: ([], []) for m in models}
    try:
        for tr, te in sp:
            from sklearn.pipeline import make_pipeline as _mp
            pre = _mp(*represent(rep, ncol))
            Ztr = pre.fit_transform(X[tr], E.Y[tr])
            Zte = pre.transform(X[te])
            for mn in models:
                try:
                    mdl = MODELS(Ztr.shape[1])[mn]()
                    mdl.fit(Ztr, E.Y[tr])
                    p = evalx._proba(mdl, Zte)
                except Exception:
                    continue
                per_model[mn][0].append(((p > 0.5).astype(float) == E.Y[te]).mean())
                per_model[mn][1].append(roc_auc_score(E.Y[te], p))
    except Exception as e:
        return [{"error": f"{rep}: {str(e)[:70]}"}]
    for mn, (A, U) in per_model.items():
        if len(A) != len(sp):
            continue
        out.append({"key": key, "rep": rep, "model": mn, "cols": ncol, "ctx": bool(ctxpath),
                    "acc": float(np.mean(A)), "acc_sd": float(np.std(A)),
                    "auc": float(np.mean(U)), "auc_sd": float(np.std(U))})
    return out


# Models whose cost grows fast enough in the number of columns that they are not worth running on the
# widest blocks: the RBF SVM is quadratic in rows and the MLP's first layer is linear in columns, and
# neither has ever won a wide block in this sweep. They still run on everything narrower.
SLOW_ON_WIDE = ("SVM rbf", "MLP (128,64)", "PCA + SVM rbf")

# The deep sweep runs a chosen subset rather than the whole zoo. The screen already showed which families
# matter on this data: a regularised linear model, a boosted tree, a bagged tree, and one kernel method.
# Running fourteen models over six representations was a cost the machine could not pay while sixteen
# subagents were also running.
DEEP_MODELS = ["logistic L2 (C=0.1)", "logistic L2 (C=1)", "hist gradient boosting",
               "extra trees", "random forest", "LDA"]
WIDE = 320

# ── stage: deep ─────────────────────────────────────────────────────────────────────────────────
def deep():
    """The surviving blocks x every representation x every model, in parallel and resumably."""
    man, files = _blocks()
    scr = json.load(open(SCREEN))
    keep = [r["key"] for r in scr[:KEEP_FOR_DEEP]]
    prev = {}
    if os.path.exists(DEEP):
        for o in json.load(open(DEEP)):
            prev[(o["key"], o["rep"], o["model"], bool(o.get("ctx")))] = o
    ctxpaths = [files[k] for k in CONTEXT_KEYS if k in files]
    ctx = ctxpaths or None
    print(f"  context blocks: {len(ctxpaths)} found "
          f"({'every astrology block is also scored WITH them' if ctxpaths else 'none — skipping the +ctx arm'})")
    jobs = []
    for key in keep:
        ncol = next(b["cols"] for b in man["blocks"] if b["key"] == key)
        for rep in reps_for(ncol):
            models = [m for m in MODELS(ncol) if m in DEEP_MODELS
                      if not (m.startswith("PCA") and rep in ("rff", "pca", "inter", "topk"))
                      and not (ncol > WIDE and m in SLOW_ON_WIDE)
                      and (key, rep, m, False) not in prev]
            if models:
                jobs.append((key, files[key], rep, models, None))
                if ctx and key not in CONTEXT_KEYS:
                    jobs.append((key, files[key], rep, models, ctx))
    out = list(prev.values())
    nfit = sum(len(j[3]) for j in jobs)
    print(f"  {len(keep)} blocks, {len(prev)} cached, {len(jobs)} (block,representation) jobs "
          f"= {nfit:,} fits, {WORKERS} workers")
    n = 0
    for _, res in _pmap(_deep_one, jobs):
        n += 1
        out.extend([r for r in res if "error" not in r])
        if n % 5 == 0:
            out.sort(key=lambda o: -o["auc"])
            json.dump(out, open(DEEP, "w"), indent=1)
            print(f"  [{n:>4}/{len(jobs)}] best so far {out[0]['auc']:.4f} "
                  f"{100*out[0]['acc']:.2f}%  {out[0]['rep']}/{out[0]['model'][:18]}/"
                  f"{out[0]['key'][:38]}", flush=True)
    out.sort(key=lambda o: -o["auc"])
    json.dump(out, open(DEEP, "w"), indent=1)
    print(f"\n{len(out):,} (block, representation, model) results")
    print("top 30 by AUC:")
    for o in out[:30]:
        print(f"  {o['auc']:.4f} +-{o['auc_sd']:.4f}  {100*o['acc']:>6.2f}%  "
              f"{'+ctx ' if o.get('ctx') else '     '}{o['rep']:<9} {o['model'][:22]:<22} {o['key']}")


# ── stage: oof ──────────────────────────────────────────────────────────────────────────────────
def _diverse(res, cap):
    """Pick a strong but DIVERSE candidate set: at most 3 per block and 12 per module."""
    per_block, per_slug, chosen = {}, {}, []
    for o in res:
        slug = o["key"].split("::")[0]
        bkey = (o["key"], bool(o.get("ctx")))
        if per_block.get(bkey, 0) >= 3 or per_slug.get(slug, 0) >= 12:
            continue
        per_block[bkey] = per_block.get(bkey, 0) + 1
        per_slug[slug] = per_slug.get(slug, 0) + 1
        chosen.append(o)
        if len(chosen) >= cap:
            break
    return chosen


def oof():
    """Out-of-fold base predictions for stacking, honouring each candidate's CONTEXT flag.

    This previously loaded the block alone and ignored `ctx`, so a candidate selected because it scored
    0.70 WITH the context block was then evaluated at 0.62 without it — the stack was being built from
    deliberately weakened versions of its own chosen models. The flag now travels with the candidate.
    """
    E = load()
    man, files = _blocks()
    res = json.load(open(DEEP))
    res.sort(key=lambda o: -o["auc"])
    cand = _diverse(res, KEEP_FOR_OOF)
    ctxpaths = [files[k] for k in CONTEXT_KEYS if k in files]
    gkf = GroupKFold(n_splits=5)
    folds = list(gkf.split(np.zeros(E.n), E.Y, groups=E.gid))
    P = np.zeros((E.n, len(cand)))
    for j, o in enumerate(cand):
        X = _get(files, o["key"])
        if o.get("ctx") and ctxpaths:
            X = np.concatenate([X] + [np.load(c).astype(np.float64) for c in ctxpaths], axis=1)
        f = MODELS(X.shape[1])[o["model"]]
        for tr, te in folds:
            mdl = pipe(o["rep"], X.shape[1], f)
            mdl.fit(X[tr], E.Y[tr])
            P[te, j] = evalx._proba(mdl, X[te])
        a = ((P[:, j] > 0.5).astype(float) == E.Y).mean()
        print(f"  [{j+1:>3}/{len(cand)}] oof {100*a:>6.2f}%  AUC {roc_auc_score(E.Y, P[:, j]):.4f}  "
              f"{'+ctx' if o.get('ctx') else '    '} {o['rep']:<9} {o['model'][:18]:<18} {o['key'][:38]}",
              flush=True)
    np.savez_compressed(OOF, P=P, meta=np.array(json.dumps(cand)))
    print(f"\nOOF matrix {P.shape} written")


# ── stage: stack ────────────────────────────────────────────────────────────────────────────────
def _caruana(P, y, idx_hill, rounds=60):
    """Greedy ensemble selection with replacement (Caruana et al. 2004).

    Members are added one at a time, each time whichever addition most improves AUC on a HILL-CLIMBING
    set held aside from the meta-learner's own training rows. Climbing on the same rows the members were
    chosen from would select for overfit, which is the whole failure mode this method exists to avoid.
    Selection with replacement is what lets a strong member accumulate a larger weight.
    """
    m = P.shape[1]
    w = np.zeros(m)
    S = np.zeros(len(idx_hill))          # running SUM of selected members on the hill-climbing rows
    k = 0
    for _ in range(rounds):
        best, bj = -np.inf, -1
        for j in range(m):
            s = roc_auc_score(y[idx_hill], (S + P[idx_hill, j]) / (k + 1))
            if s > best:
                best, bj = s, j
        S = S + P[idx_hill, bj]
        k += 1
        w[bj] += 1
    return w / w.sum()


def stack():
    E = load()
    z = np.load(OOF, allow_pickle=False)
    P, cand = z["P"], json.loads(str(z["meta"]))
    y = E.Y
    print(f"  {P.shape[1]} base models over {P.shape[0]:,} couples\n")

    # nested group CV: the meta-learner is fitted on OOF predictions of the outer-train rows only
    gkf = GroupKFold(n_splits=5)
    folds = list(gkf.split(np.zeros(E.n), y, groups=E.gid))
    metas = {
        "mean of all": None,
        "greedy ensemble (Caruana)": "caruana",
        "meta logistic (C=0.03)": lambda: LogisticRegression(C=0.03, max_iter=2000),
        "meta logistic (C=0.3)": lambda: LogisticRegression(C=0.3, max_iter=2000),
        "meta logistic (C=3)": lambda: LogisticRegression(C=3.0, max_iter=2000),
        "rank mean of top 12": "rank12",
    }
    res = {}
    for name, spec in metas.items():
        pred = np.zeros(E.n)
        for tr, te in folds:
            if spec is None:
                pred[te] = P[te].mean(1)
            elif spec == "caruana":
                # hold one group-aware inner fold aside purely to hill-climb on
                inner = list(GroupKFold(n_splits=3).split(np.zeros(len(tr)), y[tr], groups=E.gid[tr]))
                _, hill = inner[0]
                w = _caruana(P[tr], y[tr], hill)
                pred[te] = P[te] @ w
            elif spec == "rank12":
                order = np.argsort([-roc_auc_score(y[tr], P[tr, j]) for j in range(P.shape[1])])[:12]
                R = np.apply_along_axis(lambda c: np.argsort(np.argsort(c)) / len(c), 0, P[:, order])
                pred[te] = R[te].mean(1)
            else:
                mdl = make_pipeline(StandardScaler(), spec())
                mdl.fit(P[tr], y[tr])
                pred[te] = mdl.predict_proba(P[te])[:, 1]
        acc = float(((pred > 0.5).astype(float) == y).mean())
        auc = float(roc_auc_score(y, pred))
        res[name] = {"acc": acc, "auc": auc}
        print(f"  {name:<30} acc {100*acc:>6.2f}%   AUC {auc:.4f}")

    single = max(range(P.shape[1]), key=lambda j: roc_auc_score(y, P[:, j]))
    res["best single base model"] = {
        "acc": float(((P[:, single] > 0.5).astype(float) == y).mean()),
        "auc": float(roc_auc_score(y, P[:, single])),
        "what": f"{cand[single]['rep']} / {cand[single]['model']} / {cand[single]['key']}"}
    print(f"\n  best single base model: {100*res['best single base model']['acc']:.2f}% "
          f"AUC {res['best single base model']['auc']:.4f}")
    print(f"    {res['best single base model']['what']}")
    json.dump({"results": res, "candidates": cand}, open(STACK, "w"), indent=1)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "collect"
    t0 = time.time()
    {"collect": collect, "screen": screen, "deep": deep, "oof": oof, "stack": stack}[stage]()
    print(f"\n[{stage}] {time.time()-t0:.1f}s")
