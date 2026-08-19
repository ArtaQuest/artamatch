"""
artamodel_score.py — score a couple with the deployed ArtaModel, from three dates and two places. numpy only for
the model; Kerykeion for the phases (pip install kerykeion timezonefinder).

    from artamodel_score import predict
    p = predict("1936-08-04", 37.943, 23.647, "1924-05-14", 37.727, 26.909, "1968-06-15")   # dad, mom, wedding

Returns the probability that the marriage lasted thirty years, and the term-by-term account of how the logit was
formed. See README.md / ARTAMODEL.md for what the model is and, honestly, what it reads.
"""
import json
import os
import warnings

import numpy as np

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = json.load(open(os.path.join(HERE, "artamodel_deployed.json")))
BODIES = MODEL["bodies"]; TERMS = MODEL["terms"]; LABELS = MODEL["labels"]
ANGLES = {"ascendant", "medium_coeli"}
SLOW = {"jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "true_south_node", "chiron", "mean_lilith"}
_TF = None


def _tz(lat, lon):
    global _TF
    if _TF is None:
        from timezonefinder import TimezoneFinder
        _TF = TimezoneFinder()
    return _TF.timezone_at(lng=lon, lat=lat) or "UTC"


def _prec(d):
    if not d or d == "0000-00-00":
        return 0
    return 1 if d.endswith("-00-00") else (2 if d.endswith("-00") else 3)


def theta(date, lat=None, lon=None, hour=9, natal=True):
    """Sidereal (Lahiri) longitudes of the model's bodies at 09:00 local (natal) or 12:00 UT (wedding); NaN where
    the date's precision cannot place a body (year-only -> slow bodies only)."""
    from kerykeion import AstrologicalSubject
    out = np.full(len(BODIES), np.nan); p = _prec(date)
    if p == 0 or (natal and (lat is None or lon is None)):
        return out
    y, m, d = int(date[:4]), max(1, int(date[5:7])), max(1, int(date[8:10]))
    if natal:
        s = AstrologicalSubject("x", y, m, d, hour, 0, lng=float(lon), lat=float(lat), tz_str=_tz(float(lat), float(lon)),
                                city="x", nation="XX", zodiac_type="Sidereal", sidereal_mode="LAHIRI", online=False)
    else:
        s = AstrologicalSubject("w", y, m, d, 12, 0, lng=0.0, lat=51.48, tz_str="UTC", city="G", nation="GB",
                                zodiac_type="Sidereal", sidereal_mode="LAHIRI", online=False)
    for j, b in enumerate(BODIES):
        if p == 1 and b not in SLOW:
            continue
        if p == 2 and b not in SLOW and b != "sun":
            continue
        try:
            out[j] = float(getattr(s, b).abs_pos)
        except Exception:
            pass
    return out


def phases(td, tm, tw):
    """The 84 phases in the model's label order (NaN = the term does not exist)."""
    P = np.full(len(LABELS), np.nan)
    col = {b: j for j, b in enumerate(BODIES)}
    for k, lab in enumerate(LABELS):
        t, b = lab.split("_", 1); j = col[b]
        if t == "a": P[k] = tm[j] - td[j]
        elif t == "m": P[k] = tw[j] - tm[j]
        elif t == "d": P[k] = tw[j] - td[j]
        elif t == "mn": P[k] = tm[j]
        elif t == "dn": P[k] = td[j]
        elif t == "tn": P[k] = tw[j]
    return P


def logit(P):
    """The deployed model's logit for one phase vector, with the per-stage account."""
    rad = np.pi / 180.0
    C, S = np.nan_to_num(np.cos(P * rad)), np.nan_to_num(np.sin(P * rad))
    F = MODEL["F0"]; account = []
    for st in MODEL["stages"]:
        j = st["phasor"]
        if not np.isfinite(P[j]):
            account.append({"stage": st["stage"], "phasor": LABELS[j], "contribution": 0.0, "note": "term absent for this couple"}); continue
        Zr = st["w_re"] * C[j] - st["w_im"] * S[j] + st["b_re"]; Zi = st["w_re"] * S[j] + st["w_im"] * C[j] + st["b_im"]
        u = Zr * Zr + Zi * Zi; contrib = st["step"] * (st["alpha"] * u + st["c"])
        F += contrib; account.append({"stage": st["stage"], "phasor": LABELS[j], "phase_deg": float(P[j] % 360), "contribution": float(contrib)})
    return float(F), account


def predict(dob_dad, lat_dad, lon_dad, dob_mom, lat_mom, lon_mom, start):
    wed = start if start[5:] != "01-01" else start[:4] + "-00-00"          # a 1 January start is a year-only record
    P = phases(theta(dob_dad, lat_dad, lon_dad), theta(dob_mom, lat_mom, lon_mom), theta(wed, natal=False))
    F, account = logit(P)
    return {"probability": float(1 / (1 + np.exp(-F))), "logit": F, "terms": account}


if __name__ == "__main__":
    r = predict("1936-08-04", 37.943, 23.647, "1924-05-14", 37.727, 26.909, "1968-06-15")
    print(f"  p(lasted 30 years) = {r['probability']:.3f}   logit {r['logit']:+.3f}")
    for t in r["terms"][:8]:
        print(f"    stage {t['stage']:>2}  {t['phasor']:<12} " + (f"φ={t['phase_deg']:6.1f}°  {t['contribution']:+.4f}" if "phase_deg" in t else t["note"]))
