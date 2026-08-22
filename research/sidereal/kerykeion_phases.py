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


NO_PLACE = os.environ.get("AQ_NO_PLACE", "") == "1"      # dates-only dataset: cast every chart at 12:00 UT, no place


def _work(args):
    i, dd, latd, lond, dm, latm, lonm, start = args
    if NO_PLACE:
        wed_ = start
        return i, theta(dd, None, None, 12, False), theta(dm, None, None, 12, False), theta(wed_, None, None, 12, False)
    wed = start                                                          # precision is in the string: YYYY-00-00 year, YYYY-MM-00 month
    return i, theta(dd, latd, lond, 9, True), theta(dm, latm, lonm, 9, True), theta(wed, None, None, 12, False)


def slots(df):
    if "lat_a" not in df.columns and "dob_a" in df.columns:
        for c in ("lat_a", "lon_a", "lat_b", "lon_b"):
            df[c] = np.nan
    if "lat_dad" not in df.columns and "dob_dad" in df.columns:
        for c in ("lat_dad", "lon_dad", "lat_mom", "lon_mom"):
            df[c] = np.nan
    """FOURTH EDITION (genderless, 2026-08-19): the files carry `dob_a/dob_b`; the earlier editions `dob_dad/dob_mom`.
    The extractor reads whichever it is given and names its outputs by the same slot names."""
    return ("a", "b") if "dob_a" in df.columns else ("dad", "mom")


def build(df):
    s1, s2 = slots(df)
    jobs = [(i, getattr(r, f"dob_{s1}"), getattr(r, f"lat_{s1}"), getattr(r, f"lon_{s1}"), getattr(r, f"dob_{s2}"),
             getattr(r, f"lat_{s2}"), getattr(r, f"lon_{s2}"), r.start)
            for i, r in enumerate(df.itertuples(index=False))]
    with mp.Pool(max(1, mp.cpu_count() - 1)) as pool:
        res = pool.map(_work, jobs, chunksize=256)
    n = len(df); D = np.full((n, len(BODIES)), np.nan); M = D.copy(); W = D.copy()
    for i, a, b, c in res:
        D[i], M[i], W[i] = a, b, c
    return D, M, W


def main():
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    s1, s2 = slots(tr)
    for df in (tr, te):
        for c in (f"lat_{s1}", f"lon_{s1}", f"lat_{s2}", f"lon_{s2}"):
            # A dates-only build publishes no coordinate of any kind, so these columns are absent rather than
            # empty. Materialise them as NaN — NO_PLACE casts every chart at 12:00 UT and never reads them,
            # but the label-detection line below still needs the names to exclude.
            df[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else np.nan
    LABEL = [c for c in tr.columns if c not in {"id", f"dob_{s1}", f"dob_{s2}", f"lat_{s1}", f"lon_{s1}", f"lat_{s2}", f"lon_{s2}", "start"}][0]
    d1, d2 = tr[f"dob_{s1}"], tr[f"dob_{s2}"]
    if LIMIT:
        tr, te = tr.head(LIMIT), te.head(max(200, LIMIT // 4)); log(f"AQ_LIMIT={LIMIT}: DRY RUN")
    log(f"train {len(tr):,} · test {len(te):,}")
    Dtr, Mtr, Wtr = build(tr); log("train phases")
    Dte, Mte, Wte = build(te); log("test phases")
    def plain(df):
        yd = pd.to_numeric(df[f"dob_{s1}"].str[:4], errors="coerce").where(df[f"dob_{s1}"] != "0000-00-00")
        ym = pd.to_numeric(df[f"dob_{s2}"].str[:4], errors="coerce").where(df[f"dob_{s2}"] != "0000-00-00")
        sy = df.start.str[:4].astype(float)
        return np.column_stack([sy - yd, sy - ym, ym - yd, sy, df.start.str.endswith("-00-00").astype(float)])
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(f"{OUT}/phases.npz", **{f"theta_{s1}_train": Dtr, f"theta_{s2}_train": Mtr, "theta_wed_train": Wtr,
                        f"theta_{s1}_test": Dte, f"theta_{s2}_test": Mte, "theta_wed_test": Wte}, bodies=np.array(BODIES, dtype=object), slots=np.array([s1, s2], dtype=object),
                        y_train=tr[LABEL].to_numpy().astype(np.int8), id_test=te.id.to_numpy() if "id" in te else np.arange(len(te)),
                        plain_train=plain(tr), plain_test=plain(te),
                        plain_names=np.array([f"age_{s1}_at_start", f"age_{s2}_at_start", "age_gap", "start_year", "start_year_only"], dtype=object),
                        yr_train=np.column_stack([pd.to_numeric(d1.str[:4], errors="coerce").fillna(0),
                                                  pd.to_numeric(d2.str[:4], errors="coerce").fillna(0)]).astype(np.int16))
    # Count completeness over the ten PLANETS only. The last two bodies are the ascendant and the medium coeli,
    # which need a birth time and a place — neither of which a dates-only build has — so they are NaN on every
    # row by design. Including them made this line report "BOTH natal charts complete: 0" on a file that in fact
    # had 26,680 complete pairs, which reads as a dead dataset.
    full = np.isfinite(Dtr[:, :10]).all(1) & np.isfinite(Mtr[:, :10]).all(1)
    log(f"wrote {OUT}/phases.npz · {len(BODIES)} bodies · train rows with BOTH natal charts complete (10 planets): "
        f"{full.sum():,} · wedding sky complete: {np.isfinite(Wtr[:, :10]).all(1).sum():,}")


if __name__ == "__main__":
    main()
