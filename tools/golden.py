#!/usr/bin/env python3
"""Generate Swiss Ephemeris golden data for verifying ArtaMatch's built-in ephemeris.

Requires pyswisseph and the .se1 ephemeris files. Point AM_EPHE at the directory
holding them (default ~/ephe). Output: tests/golden.json — committed, so the
verification runs in CI without the 300 MB ephemeris.
"""
import json, os, sys
import swisseph as swe

EPHE = os.environ.get("AM_EPHE", os.path.expanduser("~/ephe"))
swe.set_ephe_path(EPHE)
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

BODIES = [("Sun", swe.SUN), ("Moon", swe.MOON), ("Mercury", swe.MERCURY),
          ("Venus", swe.VENUS), ("Mars", swe.MARS), ("Jupiter", swe.JUPITER),
          ("Saturn", swe.SATURN), ("Uranus", swe.URANUS), ("Neptune", swe.NEPTUNE),
          ("Pluto", swe.PLUTO)]
FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

def jd_noon(y, m, d):
    return swe.julday(y, m, d, 12.0)

rows = []
# Dense sample: every 37 days from 1900 to 2100 (prime step -> no aliasing with any period)
jd0 = jd_noon(1900, 1, 1)
jd1 = jd_noon(2100, 1, 1)
jd = jd0
while jd <= jd1:
    y, m, d, h = swe.revjul(jd)
    entry = {"jd": round(jd, 6), "date": f"{y:04d}-{m:02d}-{d:02d}",
             "ayanamsa": round(swe.get_ayanamsa_ut(jd), 8), "b": {}}
    for name, pl in BODIES:
        (lon, lat, dist, slon, slat, sdist), _ = swe.calc_ut(jd, pl, FLAGS)
        entry["b"][name] = [round(lon, 6), round(slon, 6)]  # sidereal longitude, daily motion
    rows.append(entry)
    jd += 37

# Moon fine-grain: hourly across 4 whole days, to exercise the intra-day uncertainty model
moon_days = []
for (y, m, d) in [(1969, 7, 20), (1994, 2, 15), (2026, 8, 3), (2001, 9, 11)]:
    hours = []
    for hh in range(0, 25):
        j = swe.julday(y, m, d, float(hh))
        (lon, *_), _ = swe.calc_ut(j, swe.MOON, FLAGS)
        hours.append(round(lon, 6))
    moon_days.append({"date": f"{y:04d}-{m:02d}-{d:02d}", "hourly": hours})

out = {"source": "Swiss Ephemeris (pyswisseph %s), SIDM_LAHIRI, geocentric apparent"
       % swe.version, "count": len(rows), "rows": rows, "moon_days": moon_days}
dest = os.path.join(os.path.dirname(__file__), "..", "tests", "golden.json")
os.makedirs(os.path.dirname(dest), exist_ok=True)
with open(dest, "w") as f:
    json.dump(out, f, separators=(",", ":"))
print("wrote", os.path.abspath(dest), len(rows), "rows")
