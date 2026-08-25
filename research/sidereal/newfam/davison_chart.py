"""
davison_chart.py — the DAVISON RELATIONSHIP CHART: the classical "chart of the couple", cast for the moment
midway between the two births. The single most-used relationship chart in modern Western practice and absent
from this catalogue until now, because it needs planetary positions at a THIRD date. With both endpoint
longitudes known it needs no ephemeris: each body's arc between the two births is unwrapped by its mean
geocentric motion (the revolution count is unambiguous — every body's wobble around mean motion is far less
than 180 degrees over any admissible gap) and the Davison longitude is the endpoint mean along that arc.
Both dates must be day-precise; anything less leaves the pair's Davison NaN rather than invented.
"""
import numpy as np
import pandas as pd

MEAN = {"sun": 0.9856474, "moon": 13.1763966, "mercury": 0.9856474, "venus": 0.9856474, "mars": 0.5240208,
        "jupiter": 0.0830853, "saturn": 0.0334442, "uranus": 0.0117252, "neptune": 0.0059800,
        "pluto": 0.0039717, "true_node": -0.0529539, "true_south_node": -0.0529539,
        "chiron": 0.0197354, "mean_lilith": 0.1114041}


def _jdn(col):
    """Integer JDN from the date string. NOT pandas datetimes: Timestamp cannot hold years before 1677, and
    most of this corpus is older — and year 0000 (the unknown marker) must read as NaN, not as a date."""
    out = np.full(len(col), np.nan)
    for i, v in enumerate(col.astype(str)):
        m = None
        if len(v) >= 10 and v[:4].isdigit() and v[:4] != "0000" and v[5:7].isdigit() and v[8:10].isdigit():
            y, mo, d = int(v[:4]), int(v[5:7]), int(v[8:10])
            if 1 <= mo <= 12 and 1 <= d <= 31:
                a = (14 - mo) // 12; yy = y + 4800 - a; mm = mo + 12 * a - 3
                out[i] = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    return out


def build(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ja, jb = _jdn(df.dob_a), _jdn(df.dob_b)
    dt = jb - ja                                                     # signed days, husband -> wife
    ix = {b: bodies.index(b) for b in MEAN}
    D = {}
    for b, n in MEAN.items():
        ta, tb = A[:, ix[b]], B[:, ix[b]]
        raw = (tb - ta + 180.0) % 360.0 - 180.0                      # signed short arc
        k = np.round((n * dt - raw) / 360.0)                         # whole revolutions between the births
        D[b] = (ta + (raw + 360.0 * k) / 2.0) % 360.0                # midpoint ALONG the true arc
        D[b] = np.where(np.isfinite(dt), D[b], np.nan)
    cols, names = [], []
    for b in MEAN:
        r = np.radians(D[b])
        cols += [np.sin(r), np.cos(r)]; names += [f"dav_sin_{b}", f"dav_cos_{b}"]
    # the Davison chart's own internal aspects — the couple's OWN tithi, and the classical marriage pairs
    def arc(x, y):
        return np.abs((x - y + 180.0) % 360.0 - 180.0)
    pairs = [("sun", "moon"), ("venus", "mars"), ("venus", "saturn"), ("sun", "venus"), ("moon", "saturn"),
             ("moon", "venus"), ("sun", "saturn"), ("jupiter", "venus")]
    for x, y in pairs:
        a = arc(D[x], D[y])
        cols += [a] + [np.clip(1 - np.abs(a - t) / o, 0, 1) for t, o in ((0, 8), (90, 6), (120, 6), (180, 8))]
        names += [f"davint_{x}_{y}_arc"] + [f"davint_{x}_{y}_{t}" for t in (0, 90, 120, 180)]
    dav_tithi = np.floor(((D["moon"] - D["sun"]) % 360.0) / 12.0) + 1
    cols += [dav_tithi]; names += ["dav_tithi"]
    # Davison-to-natal: where the couple's chart touches each person's own
    for tag, C in (("h", A), ("w", B)):
        for db in ("sun", "moon", "venus"):
            for nb in ("sun", "moon", "venus", "saturn"):
                a = arc(D[db], C[:, ix[nb]])
                cols += [np.clip(1 - a / 6.0, 0, 1)]
                names += [f"dav{db}_conj_{tag}{nb}"]
    # Arabic lots ON the Davison — the relationship's own Lot of Marriage family (time-free forms)
    for nm, x, y, z in (("marriage", "venus", "saturn", "sun"), ("eros", "venus", "sun", "moon"),
                        ("union", "jupiter", "venus", "sun")):
        lot = (D[x] + D[y] - D[z]) % 360.0
        r = np.radians(lot)
        cols += [np.sin(r), np.cos(r)]; names += [f"davlot_{nm}_sin", f"davlot_{nm}_cos"]
    return np.column_stack(cols).astype(np.float32), names
