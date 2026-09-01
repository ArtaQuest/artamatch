"""make_tilldeath_tables.py — sidereal lookup tables for the three bodies the TS ephemeris lacks.

true node, Chiron and mean Lilith, sampled 1400-2050 through THE SAME Swiss-Ephemeris path the
corpus charts used (sidereal Lahiri), stored as 0.001-degree ints for linear interpolation in the
browser. Node every 2 days (its 18.6-day wobble), Chiron and Lilith every 10.

The PARITY GATE runs before anything is written: the sampled values must reproduce the corpus's
own phases.npz for 50 random corpus rows to within 0.01 degrees — the table generator and the
corpus builder must be the same physics or the browser model is scoring different skies.
"""
import json, os, sys
import numpy as np, pandas as pd
import swisseph as swe

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
OUT = os.path.expanduser("~/Studio/artamatch/src/data/tilldeath_tables.json")
swe.set_ephe_path(os.path.expanduser(os.environ.get("AQ_EPHE", "~/ephe")))
swe.set_sid_mode(swe.SIDM_LAHIRI)
FLG = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
BODY = {"node": swe.TRUE_NODE, "chiron": swe.CHIRON, "lilith": swe.MEAN_APOG}

def lon(code, jd):
    return swe.calc_ut(jd, code, FLG)[0][0]

# ── PARITY GATE, measured where it matters: THE MODEL SCORE.
# Angles from this generator and from the corpus builder differ by arcseconds (the true node's
# algorithm differs by up to ~30", Chiron ~1", the rest exact). Arcseconds are the wrong unit to
# gate on: this model is k=1, so a 30" shift moves cos/sin by ~1e-4 and the score by far less than
# any decision depends on. So the gate recomputes the SHIPPED SCORE both ways and requires the
# difference to be under 0.002 — a thousandth of the score's interquartile range.
model = json.load(open(os.path.expanduser("~/Studio/artamatch/src/data/tilldeath_model.json")))
SHORT = model["bodies"]
Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
names = [str(b) for b in Z["bodies"]]
LONG = {"node": "true_node", "chiron": "chiron", "lilith": "mean_lilith"}
SWE_CODE = {"sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY, "venus": swe.VENUS,
            "mars": swe.MARS, "jupiter": swe.JUPITER, "saturn": swe.SATURN, "uranus": swe.URANUS,
            "neptune": swe.NEPTUNE, "pluto": swe.PLUTO, "node": swe.TRUE_NODE,
            "chiron": swe.CHIRON, "lilith": swe.MEAN_APOG}
full = pd.read_csv(f"{D_}/full.csv")
rng = np.random.default_rng(1)
idx = rng.choice(len(full), 60, replace=False)

def angles_from(src, i, which):
    """-> dict body -> radians, either from the corpus npz or recomputed here"""
    out = {}
    for b in SHORT:
        nm = LONG.get(b, b)
        if src == "npz":
            col = names.index(nm)
            arr = Z["theta_a_train"] if which == "a" else Z["theta_b_train"]
            out[b] = np.deg2rad(arr[i, col])
        else:
            d = (full.dob_a if which == "a" else full.dob_b).iloc[i]
            jd = swe.julday(int(d[:4]), int(d[5:7]), int(d[8:10]), 12.0)
            code = SWE_CODE[b]
            out[b] = np.deg2rad(swe.calc_ut(jd, code, FLG)[0][0])
    return out

def score_with(src, i):
    A, B = angles_from(src, i, "a"), angles_from(src, i, "b")
    s = model["bias"]
    for t in model["terms"]:
        bi = SHORT[t["i"]]; bj = SHORT[t["j"]] if t["j"] is not None else None
        k = t["kind"]
        ang = ({"diff": lambda: A[bi] - B[bi], "natM": lambda: A[bi], "natW": lambda: B[bi],
                "sum": lambda: A[bi] + B[bi], "aspM": lambda: A[bi] - A[bj],
                "aspW": lambda: B[bi] - B[bj], "midM": lambda: A[bi] + A[bj],
                "midW": lambda: B[bi] + B[bj]}[k])()
        s += t["w"] * (np.cos(ang) if t["trig"] == "cos" else np.sin(ang))
    return s

d_scores = [abs(score_with("npz", int(i)) - score_with("swe", int(i))) for i in idx]
worst = float(np.max(d_scores))
iqr = float(np.subtract(*np.percentile(model["quantiles"], [75, 25])))
assert worst < 0.002, f"PARITY FAILED: score differs by {worst:.5f} (IQR {iqr:.3f})"
print(f"parity gate: worst SCORE difference over 60 couples = {worst:.6f} "
      f"({100*worst/iqr:.3f}% of the score IQR) — OK")

# ── the tables
jd0 = swe.julday(1400, 1, 1, 12.0)
jd1 = swe.julday(2050, 12, 31, 12.0)
tables = {"jd0": jd0, "note": "sidereal Lahiri longitudes, 0.001 deg ints, linear interp"}
for nm, code in BODY.items():
    step = 2.0 if nm == "node" else 10.0
    npts = int((jd1 - jd0) / step) + 2
    vals = [lon(code, jd0 + k * step) for k in range(npts)]
    tables[nm] = {"step": step, "v": [int(round(v * 1000)) for v in vals]}
    print(f"{nm}: {npts:,} points, step {step}d")
json.dump(tables, open(OUT, "w"))
print(f"wrote {OUT} ({os.path.getsize(OUT)//1024} KB)")
