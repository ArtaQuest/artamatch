"""build_systems_phys.py — the dimensions a longitude-only bank CANNOT express.

Every feature tested so far is a function of ecliptic longitude. A chart holds more, and the
tradition uses it:
  * ECLIPTIC LATITUDE and DECLINATION — "parallels" and "contra-parallels" are declination aspects,
    a standard technique, and no function of longitudes can produce them.
  * RETROGRADATION — a classic dignity/debility, a 2-state fact per body.
  * SPEED — station (near-zero motion) versus fast; encoded as a decile on its own circle so a
    phasor of the difference is a smooth function of "how much faster he is than her".
  * DISTANCE from earth — perigee/apogee, likewise a decile.
  * The remaining DIVISIONAL CHARTS (shodasavarga): D2, D3, D4, D7, D10, D16, D20, D24, D27, D30,
    D40, D45, D60 signs of every body (D9 and D12 are already in systems_all).
Latitude and declination enter as CONTINUOUS pseudo-bodies (n = 0) mapped to their own circle:
latitude spans about ±8 degrees for the planets and the Moon ±5, so it is scaled to the full circle
(lat/8.5 * 180) rather than used raw, or a phasor of the difference would only ever see a sliver of
one cycle. Declination spans ±25 and is scaled the same way. The scaling is a fixed linear map, so
nothing about the fit is data-dependent.

AQ_DIR (corpus), AQ_OUT_FILE (systems_phys.npz), AQ_NPROC. Writes theta_a_sys/theta_b_sys/names/nstates.
"""
import os, sys, time
import numpy as np, pandas as pd
import swisseph as swe
from multiprocessing import Pool

D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
OUT = os.environ.get("AQ_OUT_FILE", "systems_phys.npz")
NPROC = int(os.environ.get("AQ_NPROC", "8"))
EPHE = os.path.expanduser("~/ephe")
if os.path.isdir(EPHE): swe.set_ephe_path(EPHE)
BODIES = [("sun", swe.SUN), ("moon", swe.MOON), ("mercury", swe.MERCURY), ("venus", swe.VENUS),
          ("mars", swe.MARS), ("jupiter", swe.JUPITER), ("saturn", swe.SATURN), ("uranus", swe.URANUS),
          ("neptune", swe.NEPTUNE), ("pluto", swe.PLUTO), ("chiron", swe.CHIRON)]
DIVS = [2, 3, 4, 7, 10, 16, 20, 24, 27, 30, 40, 45, 60]
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
LAT_SCALE, DEC_SCALE = 8.5, 25.0          # fixed linear maps, never data-dependent

def one(iso):
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    jd = swe.julday(y, m, d, 12.0)
    eps = np.deg2rad(swe.calc_ut(jd, swe.ECL_NUT, swe.FLG_SWIEPH)[0][0])
    aya = swe.get_ayanamsa_ut(jd)
    out = []
    for nm, code in BODIES:
        try: xx = swe.calc_ut(jd, code, FLAGS)[0]
        except Exception: out += [np.nan] * (4 + len(DIVS)); continue
        lon, lat, dist, sp = xx[0], xx[1], xx[2], xx[3]
        sl, cl = np.sin(np.deg2rad(lon)), np.cos(np.deg2rad(lat))
        deci = np.rad2deg(np.arcsin(np.sin(np.deg2rad(lat)) * np.cos(eps) + cl * np.sin(eps) * sl))
        sid = (lon - aya) % 360.0
        out += [np.clip(lat / LAT_SCALE, -1, 1) * 180.0,          # latitude, own circle
                np.clip(deci / DEC_SCALE, -1, 1) * 180.0,         # declination, own circle
                1.0 if sp < 0 else 0.0,                            # retrograde (2 states)
                sp, dist]                                          # speed, distance (ranked later)
        out += [float(int((n * sid % 360.0) // 30.0)) for n in DIVS]   # divisional signs
    return out

def build(col):
    with Pool(NPROC) as p: return np.array(p.map(one, list(col), chunksize=256), np.float64)

if __name__ == "__main__":
    t0 = time.time()
    full = pd.read_csv(f"{D_}/full.csv", dtype=str)
    print(f"{len(full):,} couples · {len(BODIES)} bodies · {NPROC} workers", flush=True)
    A, B = build(full.true_dob_a), build(full.true_dob_b)
    print(f"  raw ephemeris done in {time.time()-t0:.0f}s", flush=True)
    names, nstates, cols_a, cols_b = [], [], [], []
    per = 5 + len(DIVS)
    for bi, (nm, _) in enumerate(BODIES):
        o = bi * per
        for k, (lbl, n) in enumerate((("lat", 0), ("dec", 0), ("retro", 2))):
            names.append(f"phys_{lbl}_{nm}"); nstates.append(n)
            cols_a.append(A[:, o + k]); cols_b.append(B[:, o + k])
        # speed and distance are not angles: rank them JOINTLY over both partners (a fixed
        # monotone map of the pooled distribution, not a fit) and place the decile on its circle
        for k, lbl in ((3, "speed"), (4, "dist")):
            both = np.concatenate([A[:, o + k], B[:, o + k]])
            q = np.nanquantile(both, np.linspace(0, 1, 11)[1:-1])
            names.append(f"phys_{lbl}dec_{nm}"); nstates.append(10)
            cols_a.append(np.searchsorted(q, A[:, o + k]).astype(float))
            cols_b.append(np.searchsorted(q, B[:, o + k]).astype(float))
        for j, n in enumerate(DIVS):
            names.append(f"div_D{n}_{nm}"); nstates.append(12)
            cols_a.append(A[:, o + 5 + j]); cols_b.append(B[:, o + 5 + j])
    TA = np.column_stack(cols_a); TB = np.column_stack(cols_b)
    for i, n in enumerate(nstates):          # discrete states -> the same angle rule as everywhere
        if n:
            TA[:, i] = (TA[:, i] + 1) * 360.0 / n
            TB[:, i] = (TB[:, i] + 1) * 360.0 / n
    bad = ~np.isfinite(TA).all(0) | ~np.isfinite(TB).all(0)
    if bad.any():
        print(f"  dropping {int(bad.sum())} systems with a non-finite value: {[names[i] for i in np.where(bad)[0]][:6]}", flush=True)
        keep = ~bad
        TA, TB = TA[:, keep], TB[:, keep]
        names = [n for n, k in zip(names, keep) if k]; nstates = [s for s, k in zip(nstates, keep) if k]
    np.savez_compressed(f"{D_}/{OUT}", theta_a_sys=TA, theta_b_sys=TB,
                        names=np.array(names), nstates=np.array(nstates))
    print(f"wrote {D_}/{OUT} · {len(names)} pseudo-bodies · {time.time()-t0:.0f}s", flush=True)
    print("  sample:", names[:6], "...", names[-3:], flush=True)
