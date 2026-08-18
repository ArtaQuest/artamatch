"""
build_sidereal.py — the third edition's feature matrices: non-astrological, Vedic (PyJHora), ZWDS (iztro).

Reads train.csv / test.csv with dob_older, dob_younger, lat_older, lon_older, lat_younger, lon_younger, start
[, lasted_30_years]; writes AQ_OUT/sidereal.npz with X_train, X_test (float32, NaN allowed), names, family per
column, y_train, ids, and the plain columns (ages at the start, gap, start year) beside them.

Vedic charts run in a process pool (about 84 ms a couple single-threaded); ZWDS goes through one Node process for
every day-precision person at once. Nothing is imputed: a feature undefined at a row's precision is NaN, which
LightGBM handles natively and a logistic ranking skips.

Usage: AQ_SRC=/tmp/aq3 AQ_OUT=/tmp/aq3feat python build_sidereal.py
"""
import json
import multiprocessing as mp
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.environ.get("AQ_SRC", "/tmp/aq3")
OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat")
LIMIT = int(os.environ.get("AQ_LIMIT") or 0)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


def _vedic_worker(args):
    import vedic_features as V
    i, do, lao, loo, dy, lay, loy, st = args
    try:
        return i, V.couple(do, lao, loo, dy, lay, loy, start=st)
    except Exception as e:
        return i, {"_error": 1.0}


def plain(df):
    """The non-astrological columns every entrant has: ages at the start, the gap, the start year, the room."""
    yo = pd.to_numeric(df.dob_older.str[:4], errors="coerce").where(df.dob_older != "0000-00-00")
    yy = pd.to_numeric(df.dob_younger.str[:4], errors="coerce").where(df.dob_younger != "0000-00-00")
    sy = df.start.str[:4].astype(float)
    return pd.DataFrame({"plain_age_older_at_start": sy - yo, "plain_age_younger_at_start": sy - yy,
                         "plain_age_gap": yy - yo, "plain_start_year": sy, "plain_room": 2026 - sy,
                         "plain_start_is_jan1": (df.start.str[5:] == "01-01").astype(float),
                         "plain_lat_older": df.lat_older, "plain_lon_older": df.lon_older,
                         "plain_lat_younger": df.lat_younger, "plain_lon_younger": df.lon_younger})


def build(df, tag):
    n = len(df)
    P = plain(df)
    # Vedic
    jobs = [(i, r.dob_older, r.lat_older, r.lon_older, r.dob_younger, r.lat_younger, r.lon_younger, r.start)
            for i, r in enumerate(df.itertuples(index=False))]
    with mp.Pool(max(1, mp.cpu_count() - 1)) as pool:
        res = pool.map(_vedic_worker, jobs, chunksize=64)
    log(f"  {tag}: vedic charts for {n:,} couples")
    keys = sorted({k for _, f in res for k in f})
    Vm = np.full((n, len(keys)), np.nan, dtype=np.float32)
    ki = {k: j for j, k in enumerate(keys)}
    for i, f in res:
        for k, v in f.items():
            Vm[i, ki[k]] = v
    # ZWDS: one node call for every day-precision person
    import ziwei_features as Z
    def dayp(s):
        return len(s) == 10 and not s.endswith("-00") and s[5:7] != "00"
    items = []
    for i, r in enumerate(df.itertuples(index=False)):
        if dayp(r.dob_older):
            items.append((f"o{i}", r.dob_older))
        if dayp(r.dob_younger):
            items.append((f"y{i}", r.dob_younger))
    A = Z.astrolabes(items)
    log(f"  {tag}: {len(A):,} astrolabes")
    zrows = [Z.couple(A.get(f"o{i}"), A.get(f"y{i}")) for i in range(n)]
    zkeys = sorted({k for f in zrows for k in f})
    Zm = np.full((n, len(zkeys)), np.nan, dtype=np.float32)
    zi = {k: j for j, k in enumerate(zkeys)}
    for i, f in enumerate(zrows):
        for k, v in f.items():
            Zm[i, zi[k]] = v
    names = list(P.columns) + [f"vedic::{k}" for k in keys] + [f"zwds::{k}" for k in zkeys]
    X = np.column_stack([P.to_numpy(dtype=np.float32), Vm, Zm])
    return names, X


def main():
    tr = pd.read_csv(f"{SRC}/train.csv", dtype={"dob_older": str, "dob_younger": str, "start": str})
    te = pd.read_csv(f"{SRC}/test.csv", dtype={"dob_older": str, "dob_younger": str, "start": str})
    LABEL = [c for c in tr.columns if c not in {"id", "dob_older", "dob_younger", "lat_older", "lon_older",
                                                 "lat_younger", "lon_younger", "start"}][0]
    if LIMIT:
        tr, te = tr.head(LIMIT), te.head(max(200, LIMIT // 4))
        log(f"AQ_LIMIT={LIMIT}: DRY RUN")
    log(f"train {len(tr):,} · test {len(te):,}")
    ntr, Xtr = build(tr, "train")
    nte, Xte = build(te, "test")
    # align columns (a family may produce a key in one half only)
    names = sorted(set(ntr) | set(nte), key=lambda k: (ntr + nte).index(k))
    def align(nm, X):
        out = np.full((X.shape[0], len(names)), np.nan, dtype=np.float32)
        idx = {k: j for j, k in enumerate(nm)}
        for j, k in enumerate(names):
            if k in idx:
                out[:, j] = X[:, idx[k]]
        return out
    Xtr, Xte = align(ntr, Xtr), align(nte, Xte)
    fam = ["plain" if n.startswith("plain_") else n.split("::")[0] for n in names]
    np.savez_compressed(f"{OUT}/sidereal.npz", X_train=Xtr, X_test=Xte, y_train=tr[LABEL].to_numpy().astype(np.int8),
                        names=np.array(names, dtype=object), family=np.array(fam, dtype=object),
                        id_test=te.id.to_numpy() if "id" in te else np.arange(len(te)),
                        yr_train=np.column_stack([pd.to_numeric(tr.dob_older.str[:4], errors="coerce").fillna(0),
                                                  pd.to_numeric(tr.dob_younger.str[:4], errors="coerce").fillna(0)]).astype(np.int16),
                        yr_test=np.column_stack([te.dob_older.str[:4].astype(int), te.dob_younger.str[:4].astype(int)]).astype(np.int16))
    log(f"wrote {OUT}/sidereal.npz: {Xtr.shape[1]:,} features · train {Xtr.shape[0]:,} · test {Xte.shape[0]:,} · "
        f"NaN share train {np.isnan(Xtr).mean()*100:.1f}%")


if __name__ == "__main__":
    main()
