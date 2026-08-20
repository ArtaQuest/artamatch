"""
physics_members_iv.py — "entropic gravity" and other PHYSICAL features of the three instants, as stack members.

Operator 2026-08-19: "think of creative ways of feature engineering … explore entropic gravity effects with Vi/T
where Vi is the gravitational potential of external bodies." From the ephemeris (sweshim: geocentric distance of
every body at the instant) and the birthplace:
  Φᵢ = G Mᵢ / rᵢ   for Sun, Moon, Mercury … Pluto at each birth (09:00 local mean time) and at the start (12:00 UT)
  τᵢ = Mᵢ / rᵢ³    the tidal term of each body
  T               the temperature AT THE PLACE OF BIRTH: NASA POWER's 2001–2020 monthly T2M normal of the
                  birthplace's grid cell for the birth month (annual mean when the month is unknown), kelvin — plus
                  the cell's elevation; a latitude+season climatology only where POWER has no value (flagged)
  Φᵢ/T, ΣΦ/T, Στ  the entropic-gravity quantities; plus day length and the Sun's altitude at 09:00 (insolation)
For the pair: the sum and the absolute difference of each partner quantity (even under the swap). One member = a
LightGBM on the lot, forward-chained OOF; a second member = the Φᵢ/T set alone. Writes AQ_OUT/physics_members.npz.
"""
import datetime as dt
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "web"))
from artamodel import auc   # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq4"); PH = os.environ.get("AQ_PHASES", "/tmp/aq4feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq4sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
# masses in solar masses (IAU 2015 nominal values), geocentric distances come in AU
MASS = {"sun": 1.0, "moon": 3.694e-8, "mercury": 1.660e-7, "venus": 2.448e-6, "mars": 3.227e-7, "jupiter": 9.546e-4, "saturn": 2.858e-4, "uranus": 4.366e-5, "neptune": 5.151e-5, "pluto": 6.6e-9}
BODIES = list(MASS)


_T2M = None
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def t_at_pob(lat, lon, month):
    """T AT THE PLACE OF BIRTH (operator: "don't forget to get T at the POB"): the NASA POWER 2001–2020 monthly
    T2M normal of the birthplace's 0.5° grid cell for the birth month (the annual mean when the month is unknown),
    in kelvin, with the cell's elevation; (nan, nan) when the service has no value — the caller falls back to the
    latitude climatology and flags it."""
    global _T2M
    if _T2M is None:
        path = os.environ.get("AQ_T2M", "/tmp/aq4sub/t2m_normals.json"); _T2M = json.load(open(path)) if os.path.exists(path) else {}
    if lat != lat or lon != lon:
        return float("nan"), float("nan")
    rec = _T2M.get(f"{round(lat * 2) / 2},{round(lon * 2) / 2}")
    if not rec:
        return float("nan"), float("nan")
    v = rec.get(MONTHS[month - 1]) if month else rec.get("ANN")
    if v is None or v == -999.0:
        v = rec.get("ANN")
    rh = rec.get("RH_" + (MONTHS[month - 1] if month else "ANN"), rec.get("RH_ANN"))
    if rh is None or rh == -999.0:
        rh = rec.get("RH_ANN")
    return (float(v) + 273.15 if v is not None and v != -999.0 else float("nan")), (float(rec["elev"]) if rec.get("elev") is not None else float("nan")), (float(rh) if rh is not None and rh != -999.0 else float("nan"))


def temperature_proxy(lat, doy):
    """Kelvin at the surface, a smooth climatology: 300 K at the equator falling with latitude, a seasonal swing
    that grows with latitude and flips hemisphere (peak ~ 20 July north, ~ 20 January south). A proxy, not a record."""
    lat = np.asarray(lat, float); doy = np.asarray(doy, float)
    base = 300.0 - 0.45 * np.abs(lat) - 0.003 * lat ** 2
    season = (6.0 + 0.25 * np.abs(lat)) * np.cos(2 * np.pi * (doy - 201.0) / 365.25) * np.sign(lat + 1e-9)
    return base + season


def instant_features(SW, codes, y, m, d, hour_ut, lat=None, lon=None):
    """Φᵢ, τᵢ for every body at the instant; day length and the Sun's altitude when a place is given."""
    jd = SW.julday(y, m, d, hour_ut); phi = []; tau = []
    for b in BODIES:
        try:
            lon_deg, lat_deg, dist = SW.calc_ut(jd, codes[b])[0][:3]
        except Exception:
            phi.append(np.nan); tau.append(np.nan); continue
        r = max(dist, 1e-6); phi.append(MASS[b] / r); tau.append(MASS[b] / r ** 3)
    extra = [np.nan, np.nan]
    if lat is not None and not (isinstance(lat, float) and math.isnan(lat)):
        try:
            sun_lon = SW.calc_ut(jd, codes["sun"])[0][0]; eps = 23.439 - 0.0000004 * (jd - 2451545.0)
            decl = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(sun_lon))))
            cosH = -math.tan(math.radians(lat)) * math.tan(math.radians(decl)); cosH = max(-1.0, min(1.0, cosH))
            daylen = 2 * math.degrees(math.acos(cosH)) / 15.0
            # the Sun's altitude at 09:00 local mean time: hour angle −45°
            alt = math.degrees(math.asin(math.sin(math.radians(lat)) * math.sin(math.radians(decl)) + math.cos(math.radians(lat)) * math.cos(math.radians(decl)) * math.cos(math.radians(-45.0))))
            extra = [daylen, alt]
        except Exception:
            pass
    return phi, tau, extra


def build(df, SW, codes, cache):
    n = len(df); F = {k: np.full((n, len(BODIES)), np.nan) for k in ("phi_a", "phi_b", "phi_s", "tau_a", "tau_b", "tau_s")}
    Ta = np.full(n, np.nan); Tb = np.full(n, np.nan); day_a = np.full((n, 2), np.nan); day_b = np.full((n, 2), np.nan)
    El_a = np.full(n, np.nan); El_b = np.full(n, np.nan); Tproxy_a = np.zeros(n); Tproxy_b = np.zeros(n)
    RH_a = np.full(n, np.nan); RH_b = np.full(n, np.nan)
    for i, r in enumerate(df.itertuples(index=False)):
        for slot, key_phi, key_tau, Tarr, darr, Elarr, Tpx, RHarr in (("a", "phi_a", "tau_a", Ta, day_a, El_a, Tproxy_a, RH_a), ("b", "phi_b", "tau_b", Tb, day_b, El_b, Tproxy_b, RH_b)):
            d = getattr(r, f"dob_{slot}"); lat = getattr(r, f"lat_{slot}"); lon = getattr(r, f"lon_{slot}")
            if not isinstance(d, str) or d == "0000-00-00" or d.endswith("-00"):
                continue
            y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10]); lat = float(lat) if lat == lat else float("nan"); lon = float(lon) if lon == lon else float("nan")
            hour_ut = 9.0 - (lon / 15.0 if lon == lon else 0.0); key = (d, round(hour_ut, 1), round(lat, 1) if lat == lat else None)
            if key not in cache:
                cache[key] = instant_features(SW, codes, y, m, dd, hour_ut, lat if lat == lat else None, lon)
            phi, tau, extra = cache[key]; F[key_phi][i] = phi; F[key_tau][i] = tau; darr[i] = extra
            if lat == lat:
                tk, el, rh = t_at_pob(lat, lon, m); Elarr[i] = el; RHarr[i] = rh
                if tk == tk:
                    Tarr[i] = tk
                else:
                    doy = dt.date(y, m, dd).timetuple().tm_yday; Tarr[i] = temperature_proxy(lat, doy); Tpx[i] = 1.0
        s = r.start
        if isinstance(s, str) and not s.endswith("-00"):
            y, m, dd = int(s[:4]), int(s[5:7]), int(s[8:10]); key = (s, 12.0, None)
            if key not in cache:
                cache[key] = instant_features(SW, codes, y, m, dd, 12.0)
            F["phi_s"][i], F["tau_s"][i] = cache[key][0], cache[key][1]
    # the features: per partner Φ/T, pair sums and |diffs| (even), start-sky Φ, τ, day lengths, altitudes
    phiT_a = F["phi_a"] / Ta[:, None]; phiT_b = F["phi_b"] / Tb[:, None]
    X = np.column_stack([F["phi_a"] + F["phi_b"], np.abs(F["phi_a"] - F["phi_b"]), F["tau_a"] + F["tau_b"], np.abs(F["tau_a"] - F["tau_b"]),
                         phiT_a + phiT_b, np.abs(phiT_a - phiT_b), np.nansum(phiT_a, 1) + np.nansum(phiT_b, 1), np.abs(np.nansum(phiT_a, 1) - np.nansum(phiT_b, 1)),
                         np.fmax(Ta, Tb), np.fmin(Ta, Tb), F["phi_s"], F["tau_s"], np.fmax(day_a[:, 0], day_b[:, 0]), np.fmin(day_a[:, 0], day_b[:, 0]), np.fmax(day_a[:, 1], day_b[:, 1]), np.fmin(day_a[:, 1], day_b[:, 1]),
                         np.fmax(El_a, El_b), np.fmin(El_a, El_b), np.abs(El_a - El_b), Tproxy_a + Tproxy_b,
                         np.fmax(RH_a, RH_b), np.fmin(RH_a, RH_b), np.abs(RH_a - RH_b)])
    names = ([f"phi_sum_{b}" for b in BODIES] + [f"phi_absdiff_{b}" for b in BODIES] + [f"tau_sum_{b}" for b in BODIES] + [f"tau_absdiff_{b}" for b in BODIES]
             + [f"phiT_sum_{b}" for b in BODIES] + [f"phiT_absdiff_{b}" for b in BODIES] + ["phiT_total_sum", "phiT_total_absdiff", "T_max", "T_min"] + [f"phi_start_{b}" for b in BODIES] + [f"tau_start_{b}" for b in BODIES]
             + ["daylen_max", "daylen_min", "sunalt_max", "sunalt_min", "elev_max", "elev_min", "elev_absdiff", "n_T_proxy", "RH_max", "RH_min", "RH_absdiff"])
    return X.astype(np.float32), names


def main():
    import lightgbm as lgb
    import sweshim as SW
    SW.load(os.path.join(ROOT, "web", "ephem4.bin"), os.path.join(ROOT, "web", "tables.json"))
    codes = {"sun": SW.SUN, "moon": SW.MOON, "mercury": SW.MERCURY, "venus": SW.VENUS, "mars": SW.MARS, "jupiter": SW.JUPITER, "saturn": SW.SATURN, "uranus": SW.URANUS, "neptune": SW.NEPTUNE, "pluto": SW.PLUTO}
    Z = np.load(PH, allow_pickle=True); y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); s1, s2 = list(Z["slots"])
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    for df in (tr, te):
        for c in ("lat_a", "lon_a", "lat_b", "lon_b"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    cache = {}; Xtr, names = build(tr, SW, codes, cache); log(f"train physics {Xtr.shape} ({len(cache):,} instants)"); Xte, _ = build(te, SW, codes, cache); log(f"test physics {Xte.shape}")
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    plain = lambda p: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]), np.abs(p[:, ia] - p[:, ib]), p[:, iy]])
    prm = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.6, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)
    members_tr, members_te, mnames, meta = [], [], [], []
    def member(Xa, Xb, name):
        s_tr = np.full(len(y), np.nan)
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[later <= lo], y[later <= lo]); s_tr[blk] = c.predict_proba(Xa[blk])[:, 1]
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa, y); s_te = c.predict_proba(Xb)[:, 1]
        f = np.isfinite(s_tr) & (later > cuts[0]); o = auc(y[f], s_tr[f]); members_tr.append(s_tr); members_te.append(s_te); mnames.append(name); meta.append({"member": name, "forward_oof": o, "n_features": int(Xa.shape[1])})
        log(f"  {name:<46} {Xa.shape[1]:>3} features  fwd-OOF {o:.4f}")
    phiT = [i for i, n in enumerate(names) if n.startswith("phiT_")]
    member(Xtr[:, phiT], Xte[:, phiT], "PHYSICS Φ/T only (entropic gravity, no ages)")
    member(Xtr, Xte, "PHYSICS all (Φ, τ, Φ/T, T, day length, Sun altitude; no ages)")
    member(np.column_stack([plain(ptr), Xtr]), np.column_stack([plain(pte), Xte]), "PLAIN + PHYSICS")
    member(np.column_stack([plain(ptr), Xtr[:, phiT]]), np.column_stack([plain(pte), Xte[:, phiT]]), "PLAIN + Φ/T")
    np.savez_compressed(os.path.join(OUT, "physics_members.npz"), S_train=np.column_stack(members_tr), S_test=np.column_stack(members_te), names=np.array(mnames), meta=json.dumps(meta), feature_names=np.array(names))
    log(f"wrote {OUT}/physics_members.npz")


if __name__ == "__main__":
    main()
