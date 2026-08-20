"""
build_sidereal.py — the third edition's feature matrices: non-astrological, Vedic (PyJHora), ZWDS (iztro).

Reads train.csv / test.csv with dob_dad, dob_mom, lat_dad, lon_dad, lat_mom, lon_mom, start
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
    yo = pd.to_numeric(df.dob_dad.str[:4], errors="coerce").where(df.dob_dad != "0000-00-00")
    yy = pd.to_numeric(df.dob_mom.str[:4], errors="coerce").where(df.dob_mom != "0000-00-00")
    sy = df.start.str[:4].astype(float)
    return pd.DataFrame({"plain_age_dad_at_start": sy - yo, "plain_age_mom_at_start": sy - yy,
                         "plain_age_gap": yy - yo, "plain_start_year": sy, "plain_room": 2026 - sy,
                         "plain_start_year_only": df.start.str.endswith("-00-00").astype(float),
                         "plain_lat_dad": df.lat_dad, "plain_lon_dad": df.lon_dad,
                         "plain_lat_mom": df.lat_mom, "plain_lon_mom": df.lon_mom})


def build(df, tag):
    n = len(df)
    P = plain(df)
    # Vedic
    jobs = [(i, r.dob_dad, r.lat_dad, r.lon_dad, r.dob_mom, r.lat_mom, r.lon_mom, r.start)
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
        if dayp(r.dob_dad):
            items.append((f"o{i}", r.dob_dad))
        if dayp(r.dob_mom):
            items.append((f"y{i}", r.dob_mom))
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
    tr = pd.read_csv(f"{SRC}/train.csv", dtype={"dob_dad": str, "dob_mom": str, "start": str})
    te = pd.read_csv(f"{SRC}/test.csv", dtype={"dob_dad": str, "dob_mom": str, "start": str})
    LABEL = [c for c in tr.columns if c not in {"id", "dob_dad", "dob_mom", "lat_dad", "lon_dad",
                                                 "lat_mom", "lon_mom", "start"}][0]
    if LIMIT:
        tr, te = tr.head(LIMIT), te.head(max(200, LIMIT // 4))
        log(f"AQ_LIMIT={LIMIT}: DRY RUN")
    # SHARDS (Kaggle, 2026-08-19): AQ_SHARD="k/N" builds rows k, k+N, k+2N, ... of each half and writes
    # sidereal_k_of_N.npz with the row indices; build_sidereal.py --merge N reassembles them into sidereal.npz.
    shard = os.environ.get("AQ_SHARD", "")
    if shard:
        k, N = (int(x) for x in shard.split("/")); itr, ite = np.arange(k, len(tr), N), np.arange(k, len(te), N)
        tr, te = tr.iloc[itr].reset_index(drop=True), te.iloc[ite].reset_index(drop=True)
        log(f"shard {k}/{N}: train rows {len(tr):,} · test rows {len(te):,}")
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
    if shard:
        np.savez_compressed(f"{OUT}/sidereal_{k}_of_{N}.npz", X_train=Xtr, X_test=Xte, names=np.array(names, dtype=object), idx_train=itr, idx_test=ite)
        log(f"wrote {OUT}/sidereal_{k}_of_{N}.npz: {Xtr.shape[1]:,} features · train {Xtr.shape[0]:,} · test {Xte.shape[0]:,}")
        return
    np.savez_compressed(f"{OUT}/sidereal.npz", X_train=Xtr, X_test=Xte, y_train=tr[LABEL].to_numpy().astype(np.int8),
                        names=np.array(names, dtype=object), family=np.array(fam, dtype=object),
                        id_test=te.id.to_numpy() if "id" in te else np.arange(len(te)),
                        yr_train=np.column_stack([pd.to_numeric(tr.dob_dad.str[:4], errors="coerce").fillna(0),
                                                  pd.to_numeric(tr.dob_mom.str[:4], errors="coerce").fillna(0)]).astype(np.int16),
                        yr_test=np.column_stack([te.dob_dad.str[:4].astype(int), te.dob_mom.str[:4].astype(int)]).astype(np.int16))
    log(f"wrote {OUT}/sidereal.npz: {Xtr.shape[1]:,} features · train {Xtr.shape[0]:,} · test {Xte.shape[0]:,} · "
        f"NaN share train {np.isnan(Xtr).mean()*100:.1f}%")


def merge(N):
    """Reassemble sidereal.npz from N shard files in OUT (columns united by name, rows by the saved indices)."""
    tr = pd.read_csv(f"{SRC}/train.csv", dtype={"dob_dad": str, "dob_mom": str, "start": str}); te = pd.read_csv(f"{SRC}/test.csv", dtype={"dob_dad": str, "dob_mom": str, "start": str})
    LABEL = [c for c in tr.columns if c not in {"id", "dob_dad", "dob_mom", "lat_dad", "lon_dad", "lat_mom", "lon_mom", "start"}][0]
    parts = [np.load(f"{OUT}/sidereal_{k}_of_{N}.npz", allow_pickle=True) for k in range(N)]
    names = []
    for P in parts:
        for n in P["names"]:
            if n not in names:
                names.append(n)
    Xtr = np.full((len(tr), len(names)), np.nan, np.float32); Xte = np.full((len(te), len(names)), np.nan, np.float32); col = {n: j for j, n in enumerate(names)}
    for P in parts:
        js = [col[n] for n in P["names"]]; Xtr[np.ix_(P["idx_train"], js)] = P["X_train"]; Xte[np.ix_(P["idx_test"], js)] = P["X_test"]
    fam = ["plain" if n.startswith("plain_") else n.split("::")[0] for n in names]
    np.savez_compressed(f"{OUT}/sidereal.npz", X_train=Xtr, X_test=Xte, y_train=tr[LABEL].to_numpy().astype(np.int8), names=np.array(names, dtype=object), family=np.array(fam, dtype=object),
                        id_test=te.id.to_numpy() if "id" in te else np.arange(len(te)),
                        yr_train=np.column_stack([pd.to_numeric(tr.dob_dad.str[:4], errors="coerce").fillna(0), pd.to_numeric(tr.dob_mom.str[:4], errors="coerce").fillna(0)]).astype(np.int16),
                        yr_test=np.column_stack([te.dob_dad.str[:4].astype(int), te.dob_mom.str[:4].astype(int)]).astype(np.int16))
    log(f"merged {N} shards -> {OUT}/sidereal.npz: {len(names):,} features · train {len(tr):,} · test {len(te):,} · NaN share train {np.isnan(Xtr).mean()*100:.1f}%")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--merge":
        merge(int(sys.argv[2]))
    else:
        main()
