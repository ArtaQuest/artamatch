"""build_lon.py — cache the ecliptic longitudes for both halves once, so fitting is fast and repeatable.

Only LON is kept. The coherent field needs nothing else -- no houses, no ayanamsa, no speeds -- so the cache is
(NSLOT, NB, n) float32 per half and a few megabytes, instead of rebuilding the whole ephemeris per experiment.
"""
import csv
import json
import os
import sys
import time

import numpy as np

T0 = time.time()
REPO = os.path.expanduser("~/Studio/artamatch")
sys.path.insert(0, f"{REPO}/kaggle")
import dates as D                                                            # noqa: E402

OUT = os.environ.get("AQ_OUT", "/tmp/aqcoh")
os.makedirs(OUT, exist_ok=True)
TRAIN = os.environ.get("AQ_TRAIN", "/tmp/aqdur/train.csv")
TEST = os.environ.get("AQ_TEST", "/tmp/aqdur/test.csv")
SOL = os.environ.get("AQ_SOL", "/tmp/aqdurcomp/solution.csv")
SUB = int(os.environ.get("AQ_SUB") or 0)

sys.path.insert(0, f"{REPO}/astro")
sys.path.insert(0, f"{REPO}/web")
os.environ.update({"AQ_COUPLES": os.path.join(OUT, "couples.json"), "AQ_NO_PLACE": "1",
                   "AQ_KEEP_ALL_COLS": "1", "AQ_NO_EPHEM_CACHE": "1",
                   "AQ_EPHEM_CACHE": "/nonexistent.npz"})
for k in ("AQ_SUBSAMPLE", "AQ_BALANCE", "AQ_ROW_INDEX", "AQ_ONLY_KEYS", "AQ_DUMP_ROWS"):
    os.environ.pop(k, None)
import sweshim                                                               # noqa: E402
sweshim.load(f"{REPO}/web/ephem4.bin", f"{REPO}/web/tables.json")
sys.modules["swisseph"] = sweshim
import core                                                                  # noqa: E402


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


def lon_of(rows):
    json.dump([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
              open(os.environ["AQ_COUPLES"], "w"))
    E = core.load()
    if E.n != len(rows):
        raise SystemExit(f"core kept {E.n} of {len(rows)} rows — alignment would be wrong")
    return np.asarray(E.LON, dtype=np.float32)


tr = read(TRAIN, True)
te = read(TEST, False)
if SUB and SUB < len(tr):
    idx = np.random.default_rng(7).choice(len(tr), size=SUB, replace=False)
    tr = [tr[i] for i in sorted(idx)]
print(f"[{time.time()-T0:6.1f}s] train {len(tr):,} · test {len(te):,}", flush=True)

Ltr = lon_of(tr)
print(f"[{time.time()-T0:6.1f}s] train longitudes {Ltr.shape}", flush=True)
Lte = lon_of(te)
print(f"[{time.time()-T0:6.1f}s] test longitudes {Lte.shape}", flush=True)

import pandas as pd                                                          # noqa: E402
sol = pd.read_csv(SOL).set_index("id")
lab = [c for c in sol.columns if c != "Usage"][0]
ids = np.array([r["_id"] for r in te])
keep = np.isin(ids, sol.index.to_numpy().astype(str))
np.savez_compressed(
    os.path.join(OUT, "lon.npz"),
    lon_train=Ltr, lon_test=Lte[:, :, keep],
    y_train=np.array([r["label"] for r in tr], dtype=np.int8),
    y_test=sol.loc[ids[keep], lab].to_numpy().astype(np.int8),
    usage=sol.loc[ids[keep], "Usage"].to_numpy().astype("U8"),
    yr_train=np.array([[r["_yo"] for r in tr], [r["_yy"] for r in tr]], dtype=np.int16),
    yr_test=np.array([[r["_yo"] for r in te], [r["_yy"] for r in te]], dtype=np.int16)[:, keep],
)
print(f"[{time.time()-T0:6.1f}s] wrote {OUT}/lon.npz — held out {int(keep.sum()):,} rows", flush=True)
