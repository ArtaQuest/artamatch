#%% [markdown]
# # Fitting the ArtaMatch stack where it fits
#
# This notebook trains the ArtaQuest Foundation's astrology stack on the ArtaMatch relationship-duration dataset.
# It exists because the fit does not fit on a laptop: every feature block is held at once as float32, so the
# footprint is (total columns) x rows x 4 bytes — **57,132 columns over 271 blocks is 21.3 GB at 100,000
# couples**, against 16 GB on the machine that builds the dataset. A Kaggle notebook has about 30 GB, which is
# the whole reason this file exists.
#
# It is also the honest place for it: everything here runs from public inputs, so anybody can re-run the fit and
# get the same model rather than taking a number on trust.
#
# ## Inputs, all public
#
# | input | what it carries |
# |---|---|
# | `artaquest-foundation/artamatch-astrology` | `train.csv`, `test.csv`, `sample_submission.csv` |
# | `artaquest-foundation/artamatch-ephemeris` | `core.py`, the 21 `trad_*.py` modules, `sweshim.py`, the ephemeris |
#
# The ephemeris asset spans **1598–2032** and is read through `sweshim.py`, a pure-numpy stand-in registered
# under the name `swisseph` — the same shim the browser runs, so the model in the browser and the model here are
# the same code rather than two implementations that agree by inspection.
#
# ## Why the GPU
#
# The stack is gradient-boosted trees and logistic regressions, which are CPU work. The GPU accelerator is
# requested for the RAM and the faster cores that come with the instance, not for CUDA — nothing here calls a
# GPU kernel, and saying so plainly is better than implying a speedup that is not there.

#%%
import gc
import json
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

T0 = time.time()
DATA = "/kaggle/input/artamatch-astrology"
CODE = "/kaggle/input/artamatch-ephemeris"
OUT = "/kaggle/working"
for p in (DATA, CODE):
    if not os.path.isdir(p):
        raise SystemExit(f"missing input {p} — attach both datasets to this notebook")

# The modules import each other by bare name and read `swisseph`, so they need to be importable and the shim
# needs to be registered BEFORE any of them loads.
WORK = "/kaggle/working/bundle"
os.makedirs(WORK, exist_ok=True)
for f in os.listdir(CODE):
    if f.endswith((".py", ".bin", ".json")):
        shutil.copy2(os.path.join(CODE, f), os.path.join(WORK, f))
sys.path.insert(0, WORK)

import sweshim                                        # noqa: E402
sweshim.load(os.path.join(WORK, "ephem4.bin"), os.path.join(WORK, "tables.json"))
sys.modules["swisseph"] = sweshim
info = json.load(open(os.path.join(WORK, "ephem4.json")))
print(f"  ephemeris {info['yearFrom']}-{info['yearTo']}, {info['bytes']/1e6:.1f} MB, "
      f"{len(info['bodies'])} bodies")

MODULES = sorted(f[5:-3] for f in os.listdir(WORK) if f.startswith("trad_") and f.endswith(".py"))
print(f"  {len(MODULES)} tradition modules: {', '.join(MODULES)}")

#%% [markdown]
# ## The data, and the rule that the columns are ordered by AGE
#
# `dob_older` then `dob_younger`, computed from the dates themselves. Nothing about sex is recorded or used.
# A training row may be coarse (`1802-00-00` is a year) or one-sided (`0000-00-00` means that partner is absent
# from Wikidata, always in the second column since a one-sided row has no age order). Test rows are always
# complete and day-precision.

#%%
train = pd.read_csv(f"{DATA}/train.csv", dtype=str)
test = pd.read_csv(f"{DATA}/test.csv", dtype=str)
LABEL = [c for c in train.columns if c not in ("id", "dob_older", "dob_younger")][0]
train[LABEL] = train[LABEL].astype(int)
print(f"  train {len(train):,} · test {len(test):,} · target {LABEL} "
      f"({100*train[LABEL].mean():.2f}% positive)")

ABSENT = "0000-00-00"
PREC_DAY, PREC_MONTH, PREC_YEAR, PREC_ABSENT = 11, 10, 9, 1
WINDOW = {PREC_DAY: 1.0, PREC_MONTH: 30.0, PREC_YEAR: 365.0, PREC_ABSENT: 36525.0}


def precision(d):
    if not isinstance(d, str) or len(d) != 10:
        raise ValueError(d)
    if d[:4] == "0000":
        return PREC_ABSENT
    if d[8:10] != "00":
        return PREC_DAY
    if d[5:7] != "00":
        return PREC_MONTH
    return PREC_YEAR


def concrete(d):
    return f"{d[:4]}-{'01' if d[5:7]=='00' else d[5:7]}-{'01' if d[8:10]=='00' else d[8:10]}"


def records(df, labelled):
    """The shape core.load() reads. An ABSENT partner is cast for the OTHER partner's instant and flagged with
    precision 1 and a century-wide window — a chart needs some instant, and there is no honest one for a person
    who is not in the source, so the pair features degenerate predictably rather than being guessed at."""
    out = []
    for i, r in enumerate(df.itertuples(index=False)):
        do, dy = r.dob_older, r.dob_younger
        po, py = precision(do), precision(dy)
        if po == PREC_ABSENT and py == PREC_ABSENT:
            continue
        co = concrete(dy if po == PREC_ABSENT else do)
        cy = concrete(do if py == PREC_ABSENT else dy)
        out.append({"a": f"a{i}", "b": f"b{i}", "aDob": co, "bDob": cy,
                    "aSex": "", "bSex": "", "aPrec": po, "bPrec": py,
                    "aWin": WINDOW[po], "bWin": WINDOW[py],
                    "label": int(getattr(r, LABEL)) if labelled else 0,
                    "_id": getattr(r, "id", None)})
    return out


tr_rows, te_rows = records(train, True), records(test, False)
print(f"  {len(tr_rows):,} training records, {len(te_rows):,} test records")

#%% [markdown]
# ## Two passes, because one does not fit
#
# Pass 1 builds all 271 blocks on a subsample and ranks them; pass 2 frees that and rebuilds only the survivors
# — about 57 blocks and 11,000 columns instead of 57,132 — on every row. That is the same design `core.py`
# documents, and it is what makes the full-scale fit possible at all.

#%%
CAND = "/kaggle/working/couples.json"
os.environ.update({"AQ_COUPLES": CAND, "AQ_NO_PLACE": "1", "AQ_KEEP_ALL_COLS": "1",
                   "AQ_NO_EPHEM_CACHE": "1", "AQ_EPHEM_CACHE": "/nonexistent.npz",
                   "AQ_YEAR_FLOOR": "1600", "AQ_YEAR_CEIL": "2032"})
for k in ("AQ_BALANCE", "AQ_ROW_INDEX", "AQ_ONLY_KEYS", "AQ_DUMP_ROWS"):
    os.environ.pop(k, None)
import core                                            # noqa: E402
import export_model                                    # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FOLDS = 5
MAX_PER_TRADITION = int(os.environ.get("AQ_MAX_PER_TRADITION") or 3)
SCREEN_COUPLES = int(os.environ.get("AQ_SCREEN_COUPLES") or 30000)
SCREEN_ROWS = int(os.environ.get("AQ_SCREEN_ROWS") or 15000)


def build(rows, keep=None, subsample=0):
    json.dump([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows], open(CAND, "w"))
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


sub = SCREEN_COUPLES if len(tr_rows) > SCREEN_COUPLES else 0
print(f"  pass 1: screening" + (f" on a {SCREEN_COUPLES:,}-couple subsample" if sub else " on every row"))
Es, Bs = build(tr_rows, subsample=sub)
ys = Es.Y.astype(int)
print(f"    {len(Bs)} blocks · {sum(v.shape[1] for v in Bs.values()):,} columns on {len(ys):,} rows "
      f"({sum(v.nbytes for v in Bs.values())/2**30:.1f} GB)")


def hgb():
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=15,
                                          l2_regularization=1.0, random_state=0)


def logit():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000))


def screen_model():
    return HistGradientBoostingClassifier(max_iter=120, learning_rate=0.1, max_leaf_nodes=15,
                                          l2_regularization=1.0, random_state=0)


rng = np.random.default_rng(11)
sidx = (np.sort(rng.permutation(len(ys))[:SCREEN_ROWS]) if SCREEN_ROWS < len(ys) else np.arange(len(ys)))
sy = ys[sidx]
sfolds = list(StratifiedKFold(n_splits=3, shuffle=True, random_state=7).split(np.zeros(len(sidx)), sy))
ranked = []
for key, X in Bs.items():
    ki = np.flatnonzero(X.std(0) > 1e-12)
    if ki.size == 0:
        continue
    Xs = np.ascontiguousarray(X[sidx][:, ki])
    pv = np.zeros(len(sidx))
    try:
        for a, b in sfolds:
            pv[b] = screen_model().fit(Xs[a], sy[a]).predict_proba(Xs[b])[:, 1]
        auc = float(roc_auc_score(sy, pv))
    except Exception as e:
        print(f"    {key}: {type(e).__name__} {str(e)[:60]}")
        continue
    ranked.append({"key": key, "slug": key.split("::")[0], "name": key.split("::", 1)[1],
                   "kept_idx": ki.tolist(), "full_cols": int(X.shape[1]), "screen_auc": auc})
    del Xs
ranked.sort(key=lambda s: -s["screen_auc"])
per, chosen = {}, []
for s in ranked:
    if per.get(s["slug"], 0) >= MAX_PER_TRADITION:
        continue
    per[s["slug"]] = per.get(s["slug"], 0) + 1
    chosen.append(s)
keep_keys = {s["key"] for s in chosen}
del Bs, Es, ys
gc.collect()
print(f"  pass 2: {len(chosen)} blocks across {len(per)} traditions, rebuilt on all {len(tr_rows):,} rows")
Etr, Btr = build(tr_rows, keep=keep_keys)
y = Etr.Y.astype(int)
missing = keep_keys - set(Btr)
if missing:
    raise SystemExit(f"the full-scale build lost blocks the screen chose: {sorted(missing)[:4]}")
for s in chosen:
    w = Btr[s["key"]].shape[1]
    if w != s["full_cols"]:
        raise SystemExit(f"{s['key']} is {w} columns at full scale, {s['full_cols']} on the screen — a width "
                         f"changed between passes, which invalidates kept_idx")
print(f"    {len(Btr)} blocks · {sum(v.shape[1] for v in Btr.values()):,} columns "
      f"({sum(v.nbytes for v in Btr.values())/2**30:.1f} GB)")

#%% [markdown]
# ## The baseline, then the stack
#
# The one baseline this project permits itself is a two-parameter logistic on the **age gap** — younger minus
# older, non-negative because the older partner is always the first column. It is reported every time.

#%%
YR = 365.2425
gap = (Etr.JD[1] - Etr.JD[0]) / YR
folds = list(StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=7).split(np.zeros(len(y)), y))
bp = np.zeros(len(y))
for a, b in folds:
    bp[b] = LogisticRegression(max_iter=2000).fit(gap[a, None], y[a]).predict_proba(gap[b, None])[:, 1]
base_auc = float(roc_auc_score(y, bp))
print(f"  BASELINE age gap (younger - older): AUC {base_auc:.4f}")

scored = []
for s in chosen:
    Xk = np.ascontiguousarray(Btr[s["key"]][:, np.asarray(s["kept_idx"])])
    best = None
    for kind, mk in (("hgb", hgb), ("logit", logit)):
        pv = np.zeros(len(y))
        try:
            for a, b in folds:
                pv[b] = mk().fit(Xk[a], y[a]).predict_proba(Xk[b])[:, 1]
            auc = float(roc_auc_score(y, pv))
        except Exception as e:
            print(f"    {s['key']} / {kind}: {type(e).__name__} {str(e)[:60]}")
            continue
        if best is None or auc > best["auc"]:
            best = {"auc": auc, "kind": kind, "mk": mk, "oof": pv}
    if best is None:
        continue
    s.update({"auc": best["auc"], "kind": best["kind"], "oof": best["oof"],
              "estimator": best["mk"]().fit(Xk, y)})
    scored.append(s)
    print(f"    {s['auc']:.4f}  {s['kind']:<5} {s['key'][:58]}")
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
# THIS NUMBER IS A SELECTION SCORE AND IT IS OPTIMISTIC. The base predictions it combines were produced over the
# same folds the meta is validated on, the hgb-vs-logit choice was made on that same vector, and the screen ran
# on all of the training half. On coin-flip labels it reads about 0.56. The honest number is the held-out AUC,
# which the competition scores; do not quote this one as performance.
print(f"\n  STACK in-training selection AUC {cv:.4f} (OPTIMISTIC — the honest number is the held-out one)")
print(f"  BASELINE age gap {base_auc:.4f}")

#%% [markdown]
# ## Predict the held-out couples, and write everything the rest of the pipeline needs

#%%
specs = [{"key": s["key"], "slug": s["slug"], "name": s["name"], "kind": s["kind"],
          "kept_idx": s["kept_idx"], "full_cols": s["full_cols"], "auc": s["auc"],
          "estimator": s["estimator"]} for s in chosen]
hdr, npz = export_model.pack(specs, {"mu": mu, "sd": sd, "coef": meta.coef_.ravel(),
                                     "intercept": meta.intercept_[0], "auc": cv},
                             {"rate": float(y.mean()), "hour": 8.0, "n": int(len(y)),
                              "baseline": {"logistic on the age gap (younger - older)": base_auc}})
open(f"{OUT}/model.json", "w").write(hdr)
open(f"{OUT}/model.npz", "wb").write(npz)
np.save(f"{OUT}/oof_base.npy", P.astype(np.float32))
np.save(f"{OUT}/y_train.npy", y.astype(np.int8))
del Btr
gc.collect()

Ete, Bte = build(te_rows, keep={s["key"] for s in chosen})
import predictor                                       # noqa: E402
st = predictor.load(open(f"{OUT}/model.json").read(), open(f"{OUT}/model.npz", "rb").read())
p_te, P_te = st.proba(Bte)
np.save(f"{OUT}/test_base.npy", np.asarray(P_te, dtype=np.float32))
sub_df = pd.DataFrame({"id": [r["_id"] for r in te_rows], LABEL: p_te})
sub_df.to_csv(f"{OUT}/submission.csv", index=False)
json.dump({"cv_auc": cv, "baseline_auc": base_auc, "n_train": int(len(y)),
           "blocks": len(chosen), "traditions": len(per),
           "per_block": [{"key": s["key"], "auc": s["auc"], "kind": s["kind"]} for s in chosen]},
          open(f"{OUT}/result.json", "w"), indent=1)
shutil.rmtree(WORK, ignore_errors=True)
os.remove(CAND)
print(f"  wrote model.json · model.npz · oof_base.npy · y_train.npy · test_base.npy · submission.csv "
      f"· result.json")
print(f"  submission: {len(sub_df):,} rows, mean {p_te.mean():.4f}")
print(f"\n  total {(time.time()-T0)/60:.1f} min")
