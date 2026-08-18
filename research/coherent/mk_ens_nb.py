"""Assemble the ensemble notebook by splicing mega_features.py in verbatim, so the feature code in the
notebook and the feature code in the repo cannot drift apart."""
import os
REPO = os.path.expanduser("~/Studio/artamatch")
mega = open(f"{REPO}/research/coherent/mega_features.py").read()
dates_src = open(f"{REPO}/kaggle/dates.py").read()
dates_src = dates_src.split('"""', 2)[2]
dates_src = dates_src.split("def _selftest")[0].rstrip() + "\n"
# strip the module docstring — the notebook has its own prose — and the numpy import, which the notebook does
mega = mega.split('"""', 2)[2].lstrip("\n")

HEAD = '''# %% [markdown]
# # ArtaMatch: the 4,962-feature ensemble
#
# **Two birth dates in, one probability out.** Everything else is computed here.
#
# The competition gives three columns — `dob_older`, `dob_younger`, `lasted_30_years` — and asks whether a
# relationship lasted thirty years. This notebook takes only that, plus a public **ephemeris asset** (planetary
# positions against time, plus the reader for it — an astronomical constant table, not information about any
# couple), and builds **4,962 named astrological and numerological features in this notebook**, then fits an
# ensemble on GPU.
#
# ### What is deliberately NOT an input
#
# * No precomputed feature matrix. Every column is derived from the two dates in the cells below.
# * No held-out label, anywhere. Model selection uses an **inner temporal split** — the latest 15% of training
#   births — mirroring the competition's own out-of-time split. The notebook cannot see `solution.csv` and does
#   not ask for it, so the leaderboard score it earns is a prediction rather than a description of the answer.
#
# ### The feature families
#
# | family | n | what |
# |---|---|---|
# | cross-chart synastry | 2,268 | all 18×18 ordered body pairs between the charts, harmonics 1–6 |
# | natal aspects | 1,224 | all 153 body pairs inside each chart, harmonics 1–3 |
# | single body | 424 | tropical and sidereal longitude, sign, decan, dwadasamsa, nakshatra, navamsa, speed |
# | calendrical + numerology | 270 | weekday and planetary day lord, day-of-year harmonics, sun-sign compatibility, Chinese pillars, Life Path, karmic-debt / challenge / pinnacle numbers |
# | vargas | 252 | divisional-chart signs D2–D60, and same-varga agreement across the charts |
# | harmonic charts | 216 | each body's longitude ×5, ×7, ×9 rewrapped |
# | midpoints and antiscia | 169 | Uranian midpoints and solstice mirrors, with cross-chart contacts |
# | lunar elongations | 85 | each body's distance from its own Sun, and the two charts' difference |
# | vedic pair | 54 | nakshatra and sign distance for every body, not only the Moon |
#
# ### Day precision, and why the training set shrinks
#
# A third of the training half carries only a year (`1856-00-00`). A chart cannot honestly be cast for it: placing
# it at 1 January puts the Sun near 280° for every such couple and plants a false spike at day 1 in every
# seasonal feature. So the models train on the **27,189 couples with both dates to the day**, which is also what
# the held-out half is.

# %%
import gc, json, math, os, shutil, sys, time
import numpy as np
import pandas as pd

T0 = time.time()
# FIND THE MOUNTS, DO NOT ASSUME THEIR NAMES. The first run of this notebook died with FileNotFoundError on a
# hardcoded /kaggle/input/artamatch-ephemeris, which told me a file was missing when what I needed to know was
# which inputs were actually mounted. Both datasets are public and both were listed in the kernel metadata, so
# guessing further was pointless: the notebook now identifies each input by a file it must CONTAIN, and prints
# the whole tree when it cannot.
ROOT = "/kaggle/input"
_tree = {}
for d, _, fs in os.walk(ROOT):
    for f in fs:
        _tree.setdefault(os.path.basename(d), []).append(f)
print("mounted inputs:")
for d, fs in sorted(_tree.items()):
    print(f"  {d}/  ({len(fs)} files) e.g. {sorted(fs)[:4]}")


def find_dir(marker):
    for d, _, fs in os.walk(ROOT):
        if marker in fs:
            return d
    raise SystemExit(f"no mounted input contains {marker!r}. Mounted: "
                     + json.dumps({k: sorted(v)[:6] for k, v in _tree.items()}, indent=1))


CODE = find_dir("ephem4.bin")
DATA = find_dir("train.csv")
print(f"code + ephemeris: {CODE}")
print(f"competition data: {DATA}")
WORK = "/kaggle/working/code"
os.makedirs(WORK, exist_ok=True)
for f in os.listdir(CODE):
    if f.endswith((".py", ".bin", ".json")):
        shutil.copy(os.path.join(CODE, f), os.path.join(WORK, f))
sys.path.insert(0, WORK)
os.environ.update({"AQ_NO_PLACE": "1", "AQ_KEEP_ALL_COLS": "1", "AQ_NO_EPHEM_CACHE": "1",
                   "AQ_EPHEM_CACHE": "/nonexistent.npz", "AQ_COUPLES": "/kaggle/working/couples.json"})
import sweshim
sweshim.load(os.path.join(WORK, "ephem4.bin"), os.path.join(WORK, "tables.json"))
sys.modules["swisseph"] = sweshim
info = json.load(open(os.path.join(WORK, "ephem4.json")))
print(f"ephemeris {info['yearFrom']}-{info['yearTo']}, read through the pure-numpy shim")

# GPU if there is one. The corrected recipe is LightGBM / XGBoost / a logistic, so torch is no longer imported;
# XGBoost takes device="cuda" directly. Kaggle's DEFAULT accelerator is a P100 whose compute capability (6.0)
# the preinstalled torch cannot use -- one more reason not to depend on it -- and the kernel metadata requests
# machine_shape=NvidiaTeslaT4 regardless.
DEV = "cuda" if shutil.which("nvidia-smi") else "cpu"
print(f"device for XGBoost: {DEV}")

# %%
tr_all = pd.read_csv(f"{DATA}/train.csv", dtype={"dob_older": str, "dob_younger": str})
te = pd.read_csv(f"{DATA}/test.csv", dtype={"dob_older": str, "dob_younger": str})
LABEL = [c for c in tr_all.columns if c not in {"id", "dob_older", "dob_younger"}][0]
print(f"competition train {len(tr_all):,} · test {len(te):,} · target {LABEL!r}")


def dayprec(c):
    return c.str.len().eq(10) & ~c.str.endswith("-00") & ~c.str.slice(5, 7).eq("00")


def yearknown(c):
    return c.ne("0000-00-00")


both_year = (yearknown(tr_all.dob_older) & yearknown(tr_all.dob_younger)).to_numpy()
both_day = (dayprec(tr_all.dob_older) & dayprec(tr_all.dob_younger)).to_numpy()
tr = tr_all[both_day].reset_index(drop=True)
print(f"  both dates to the day: {both_day.sum():,}  ·  both years known: {both_year.sum():,}")

# %% [markdown]
# ## The feature definitions
#
# Spliced verbatim from `research/coherent/mega_features.py`, so the notebook and the repo cannot drift. Each
# family yields `{name: (explanation, values)}` and is consumed one at a time.

# %%
'''

TAIL = open(os.path.join(REPO, 'research/coherent/nb_tail.py')).read()
open(f"{REPO}/research/coherent/ensemble_notebook.py", "w").write(HEAD + mega + TAIL.replace("__DATES_SRC__", dates_src))
print(f"  wrote ensemble_notebook.py — {len(HEAD+mega+TAIL):,} chars")
