"""
kerykeion_phases.py — the PHASE theta of every body at every time, through Kerykeion (sidereal, Lahiri).

Operator, 2026-08-18: "use kerykeion for getting the phase of each body at each time". Three instants per couple:
dad's birth and mom's birth at 09:00 LOCAL at each birthplace (time zone from the coordinates through
timezonefinder; Kerykeion converts to UT and casts, houses included), and the wedding at 12:00 UT (no wedding
place is in the data, so no wedding houses).

BODIES: Sun Moon Mercury Venus Mars Jupiter Saturn Uranus Neptune Pluto TrueNode(Rahu) TrueSouthNode(Ketu) Chiron
MeanLilith, and for the natal charts the Ascendant and MC. Precision-aware like everything else here: a
year-only birth (1st of January placeholder) gets only the bodies the year can place -- Jupiter and slower --
and no angles; a month-only birth adds the Sun; a year-only wedding gets the slow bodies only.

Writes AQ_OUT/phases.npz: theta_dad, theta_mom, theta_wed (rows x bodies, degrees, NaN where undefined),
bodies, y_train / ids, the plain columns for references. Kerykeion agrees with PyJHora to 0.005 degrees on the
same instant (checked); ~0.8 ms per chart, so the whole build is minutes.
"""
import datetime as dt
import multiprocessing as mp
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
SRC = os.environ.get("AQ_SRC", "/tmp/aq3")
OUT = os.environ.get("AQ_OUT", "/tmp/aq3feat")
LIMIT = int(os.environ.get("AQ_LIMIT") or 0)
BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
SLOW = {"jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "true_south_node", "chiron", "mean_lilith"}
ANGLES = {"ascendant", "medium_coeli"}
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.1f}s]", *a, flush=True)


_TF = None
_TZC = {}


def tz_name(lat, lon):
    global _TF
    if _TF is None:
        from timezonefinder import TimezoneFinder
        _TF = TimezoneFinder()
    key = (round(lat, 2), round(lon, 2))
    if key not in _TZC:
        _TZC[key] = _TF.timezone_at(lng=lon, lat=lat) or _TF.closest_timezone_at(lng=lon, lat=lat) or "UTC"
    return _TZC[key]


def prec(dob):
    if not dob or dob == "0000-00-00" or dob == "nan":
        return 0
    return 1 if dob.endswith("-00-00") else (2 if dob.endswith("-00") else 3)


def theta(dob, lat, lon, hour, natal):
    """Longitudes of BODIES at (dob, hour local at lat/lon), NaN where the date's precision cannot place them."""
    from kerykeion import AstrologicalSubject
    out = np.full(len(BODIES), np.nan)
    p = prec(dob)
    if p == 0:
        return out
    if natal and (lat is None or (isinstance(lat, float) and np.isnan(lat))):
        return out
    y, m, d = int(dob[:4]), max(1, int(dob[5:7])), max(1, int(dob[8:10]))
    try:
        if natal:
            s = AstrologicalSubject("x", y, m, d, hour, 0, lng=float(lon), lat=float(lat), tz_str=tz_name(float(lat), float(lon)),
                                    city="x", nation="XX", zodiac_type="Sidereal", sidereal_mode="LAHIRI", online=False)
        else:
            s = AstrologicalSubject("w", y, m, d, hour, 0, lng=0.0, lat=51.48, tz_str="UTC", city="Greenwich", nation="GB",
                                    zodiac_type="Sidereal", sidereal_mode="LAHIRI", online=False)
    except Exception:
        return out
    for j, b in enumerate(BODIES):
        if b in ANGLES and (not natal or p < 3):
            continue
        if p == 1 and b not in SLOW:
            continue
        if p == 2 and b not in SLOW and b != "sun":
            continue
        try:
            out[j] = float(getattr(s, b).abs_pos)
        except Exception:
            pass
    return out


def _work(args):
    i, dd, latd, lond, dm, latm, lonm, start = args
    wed = start if start[5:] != "01-01" else start[:4] + "-00-00"       # a 1 January start is a year-only record
    return i, theta(dd, latd, lond, 9, True), theta(dm, latm, lonm, 9, True), theta(wed, None, None, 12, False)


def build(df):
    jobs = [(i, r.dob_dad, r.lat_dad, r.lon_dad, r.dob_mom, r.lat_mom, r.lon_mom, r.start)
            for i, r in enumerate(df.itertuples(index=False))]
    with mp.Pool(max(1, mp.cpu_count() - 1)) as pool:
        res = pool.map(_work, jobs, chunksize=256)
    n = len(df); D = np.full((n, len(BODIES)), np.nan); M = D.copy(); W = D.copy()
    for i, a, b, c in res:
        D[i], M[i], W[i] = a, b, c
    return D, M, W


def main():
    tr = pd.read_csv(f"{SRC}/train.csv", dtype={"dob_dad": str, "dob_mom": str, "start": str})
    te = pd.read_csv(f"{SRC}/test.csv", dtype={"dob_dad": str, "dob_mom": str, "start": str})
    LABEL = [c for c in tr.columns if c not in {"id", "dob_dad", "dob_mom", "lat_dad", "lon_dad", "lat_mom", "lon_mom", "start"}][0]
    if LIMIT:
        tr, te = tr.head(LIMIT), te.head(max(200, LIMIT // 4)); log(f"AQ_LIMIT={LIMIT}: DRY RUN")
    log(f"train {len(tr):,} · test {len(te):,}")
    Dtr, Mtr, Wtr = build(tr); log("train phases")
    Dte, Mte, Wte = build(te); log("test phases")
    def plain(df):
        yd = pd.to_numeric(df.dob_dad.str[:4], errors="coerce").where(df.dob_dad != "0000-00-00")
        ym = pd.to_numeric(df.dob_mom.str[:4], errors="coerce").where(df.dob_mom != "0000-00-00")
        sy = df.start.str[:4].astype(float)
        return np.column_stack([sy - yd, sy - ym, ym - yd, sy, (df.start.str[5:] == "01-01").astype(float)])
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(f"{OUT}/phases.npz", theta_dad_train=Dtr, theta_mom_train=Mtr, theta_wed_train=Wtr,
                        theta_dad_test=Dte, theta_mom_test=Mte, theta_wed_test=Wte, bodies=np.array(BODIES, dtype=object),
                        y_train=tr[LABEL].to_numpy().astype(np.int8), id_test=te.id.to_numpy() if "id" in te else np.arange(len(te)),
                        plain_train=plain(tr), plain_test=plain(te),
                        plain_names=np.array(["age_dad_at_start", "age_mom_at_start", "age_gap", "start_year", "start_is_jan1"], dtype=object),
                        yr_train=np.column_stack([pd.to_numeric(tr.dob_dad.str[:4], errors="coerce").fillna(0),
                                                  pd.to_numeric(tr.dob_mom.str[:4], errors="coerce").fillna(0)]).astype(np.int16))
    full = np.isfinite(Dtr).all(1) & np.isfinite(Mtr).all(1)
    log(f"wrote {OUT}/phases.npz · {len(BODIES)} bodies · train rows with BOTH natal charts complete: {full.sum():,} · "
        f"wedding sky complete: {np.isfinite(Wtr[:, :10]).all(1).sum():,}")


if __name__ == "__main__":
    main()
