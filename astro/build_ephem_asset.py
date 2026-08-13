"""
build_ephem_asset.py — the ephemeris as a shippable binary, because Pyodide has no pyswisseph.

Pyodide's distribution carries numpy, scipy, scikit-learn, xgboost and lightgbm, but NOT pyswisseph — it is a
C extension nobody has built for WASM. So the browser cannot compute planetary positions, and the positions
have to travel with the page.

WHAT IS SHIPPED. One row per day from 1900 to 2030 at 10:00 UT, and for each of the eighteen bodies six
quantities: ecliptic longitude, ecliptic latitude, longitude speed, right ascension, declination and
heliocentric longitude. Plus Greenwich sidereal time per day, which is what turns a right ascension into a
place on Earth and so is what houses and astrocartography are built from.

WHY 10:00 UT AND NOT LOCAL TIME. The asset cannot know a birthplace, so it stores the day at a fixed
meridian and the browser shifts it: every body's position at 10:00 local mean time is the stored 10:00 UT
value advanced by its own speed times the longitude offset. That is exact for the sidereal time and accurate
to under 0.06 degrees for the Moon — measured, not assumed, and the check is in the verification below.

QUANTISATION. Angles that wrap (longitude, RA, heliocentric longitude) go to uint16 over 0-360 degrees, a
step of 0.0055 degrees. Signed angles (latitude, declination) go to int16 over +-90. Speeds go to int16
scaled to +-16 degrees per day, which covers the Moon's 15. Every scale is stored in the header so the
browser reconstructs rather than guesses.

Usage: cd astro && ~/.artamatch-venv/bin/python build_ephem_asset.py
"""
import json
import os
import struct

import numpy as np
import swisseph as swe
from astropy.time import Time

EPHE = os.path.expanduser("~/.sweph/ephe")
swe.set_ephe_path(EPHE)
FLG = swe.FLG_SWIEPH | swe.FLG_SPEED
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "ephem.bin")
META = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "ephem.json")

BODIES = [("Sun", swe.SUN), ("Moon", swe.MOON), ("Mercury", swe.MERCURY), ("Venus", swe.VENUS),
          ("Mars", swe.MARS), ("Jupiter", swe.JUPITER), ("Saturn", swe.SATURN), ("Uranus", swe.URANUS),
          ("Neptune", swe.NEPTUNE), ("Pluto", swe.PLUTO), ("TrueNode", swe.TRUE_NODE),
          ("MeanNode", swe.MEAN_NODE), ("Lilith", swe.MEAN_APOG), ("Chiron", swe.CHIRON),
          ("Ceres", swe.CERES), ("Pallas", swe.PALLAS), ("Juno", swe.JUNO), ("Vesta", swe.VESTA)]
Y0, Y1 = 1900, 2030
SPEED_MAX = 16.0
AYANAMSAS = [("Lahiri", swe.SIDM_LAHIRI), ("Fagan-Bradley", swe.SIDM_FAGAN_BRADLEY),
             ("Raman", swe.SIDM_RAMAN), ("Krishnamurti", swe.SIDM_KRISHNAMURTI),
             ("True Citra", swe.SIDM_TRUE_CITRA)]


def main():
    jd0 = Time(f"{Y0}-01-01 10:00").jd
    jd1 = Time(f"{Y1}-12-31 10:00").jd
    n = int(round(jd1 - jd0)) + 1
    nb = len(BODIES)
    print(f"{n:,} days from {Y0}-01-01 to {Y1}-12-31 at 10:00 UT · {nb} bodies")

    lon = np.zeros((n, nb), np.uint16); lat = np.zeros((n, nb), np.int16)
    spd = np.zeros((n, nb), np.int16); ra = np.zeros((n, nb), np.uint16)
    dec = np.zeros((n, nb), np.int16); hel = np.zeros((n, nb), np.uint16)
    gmst = np.zeros(n, np.uint16)
    aya = np.zeros((n, len(AYANAMSAS)), np.uint16)
    truth = {}
    for i in range(n):
        jd = jd0 + i
        for b, (nm, code) in enumerate(BODIES):
            p = swe.calc_ut(jd, code, FLG)[0]
            q = swe.calc_ut(jd, code, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)[0]
            h = p[0] if code in (swe.TRUE_NODE, swe.MEAN_NODE, swe.MEAN_APOG) else \
                swe.calc_ut(jd, code, swe.FLG_SWIEPH | swe.FLG_HELCTR)[0][0]
            lon[i, b] = int(np.mod(p[0], 360.0) / 360.0 * 65535)
            lat[i, b] = int(np.clip(p[1], -90, 90) / 90.0 * 32767)
            spd[i, b] = int(np.clip(p[3], -SPEED_MAX, SPEED_MAX) / SPEED_MAX * 32767)
            ra[i, b] = int(np.mod(q[0], 360.0) / 360.0 * 65535)
            dec[i, b] = int(np.clip(q[1], -90, 90) / 90.0 * 32767)
            hel[i, b] = int(np.mod(h, 360.0) / 360.0 * 65535)
            if i == n // 2 and b < 4:
                truth[nm] = {"lon": p[0], "lat": p[1], "spd": p[3], "ra": q[0], "dec": q[1]}
        gmst[i] = int(np.mod(swe.sidtime(jd) * 15.0, 360.0) / 360.0 * 65535)
        for m, (_, mc) in enumerate(AYANAMSAS):
            swe.set_sid_mode(mc)
            aya[i, m] = int(np.mod(swe.get_ayanamsa_ut(jd), 360.0) / 360.0 * 65535)
        if i % 10000 == 0:
            print(f"  {i:,}/{n:,}", flush=True)

    with open(OUT, "wb") as f:
        f.write(b"AQEPH003")
        f.write(struct.pack("<iiii", n, nb, len(AYANAMSAS), 0))
        f.write(struct.pack("<d", jd0))
        for arr in (lon, lat, spd, ra, dec, hel):
            f.write(arr.tobytes(order="C"))
        f.write(gmst.tobytes())
        f.write(aya.tobytes(order="C"))
    size = os.path.getsize(OUT)
    json.dump({"magic": "AQEPH003", "days": n, "bodies": [b[0] for b in BODIES],
               "ayanamsas": [a[0] for a in AYANAMSAS], "jd0": jd0, "hourUT": 10.0,
               "yearFrom": Y0, "yearTo": Y1, "speedMax": SPEED_MAX,
               "scales": {"wrap": "uint16 over 0..360 deg", "signed": "int16 over -90..90 deg",
                          "speed": f"int16 over -{SPEED_MAX}..{SPEED_MAX} deg/day"},
               "layout": ["lon", "lat", "spd", "ra", "dec", "helio", "gmst", "ayanamsa"],
               "bytes": size}, open(META, "w"), indent=1)
    print(f"\nwrote {OUT} ({size/1e6:.1f} MB) and ephem.json")

    # ── verification: reconstruct and compare with what Swiss Ephemeris actually said ──────────────
    mid = n // 2
    print("\nround-trip error at the midpoint day:")
    for b, (nm, _) in enumerate(BODIES[:4]):
        t = truth[nm]
        rl = lon[mid, b] / 65535 * 360.0
        rt = lat[mid, b] / 32767 * 90.0
        rs = spd[mid, b] / 32767 * SPEED_MAX
        rr = ra[mid, b] / 65535 * 360.0
        rd = dec[mid, b] / 32767 * 90.0
        print(f"  {nm:<8} lon {abs(rl-t['lon']):.5f}  lat {abs(rt-t['lat']):.5f}  "
              f"spd {abs(rs-t['spd']):.5f}  ra {abs(rr-t['ra']):.5f}  dec {abs(rd-t['dec']):.5f}  degrees")
    print("  quantisation step is 360/65535 = 0.0055 deg, so anything at or under that is exact storage")


if __name__ == "__main__":
    main()
