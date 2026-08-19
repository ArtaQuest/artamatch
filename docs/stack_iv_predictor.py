"""
stack_iv_predictor.py — the deployed edition-IV STACK, runnable anywhere Python + numpy run, including the browser
under Pyodide (the prod page). No LightGBM, no Kerykeion: the three geography boosters are evaluated from their
JSON dumps, and the sidereal phases come from sweshim (the shipped ephemeris asset) with the Lahiri ayanāṁśa.

    import stack_iv_predictor as P
    P.init(asset_bytes, tables_text, deployed_json_text, [geo0_json_text, geo1_json_text, geo2_json_text])
    r = P.predict("1936-08-04", 37.943, 23.647, "1924-05-14", 37.727, 26.909, "1968-06-15")
    r["probability"], r["breakdown"]

Conventions (the same as the fit): births at 09:00 LOCAL MEAN TIME at the birthplace (09:00 − lon/15 h UT — the
fit used the zone clock through timezonefinder; for the outer planets the model reads the difference is under
0.01°), the start at 12:00 UT; year-only dates place only Jupiter and slower; every phase difference is |Δθ| in
[0°, 180°]; the two orders of the pair are scored and averaged, so the answer is exactly symmetric.
"""
import json
import math

import numpy as np

BODIES14 = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "true_south_node", "chiron", "mean_lilith"]
SLOW = {"jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "true_south_node", "chiron", "mean_lilith"}
_M = None; _GEO = None; _SW = None


def init(asset_bytes, tables_text, deployed_json_text, geo_json_texts, sweshim_module=None):
    """Load the ephemeris asset into sweshim, the deployed JSON, and the three geography boosters."""
    global _M, _GEO, _SW
    if sweshim_module is None:
        import sweshim as sweshim_module
    _SW = sweshim_module
    if asset_bytes is not None:
        _SW.load(None, None, blob=bytes(asset_bytes), tables=json.loads(tables_text) if isinstance(tables_text, str) else tables_text)
    _SW.set_sid_mode(_SW.SIDM_LAHIRI)
    _M = json.loads(deployed_json_text) if isinstance(deployed_json_text, str) else deployed_json_text
    _GEO = [json.loads(t) if isinstance(t, str) else t for t in geo_json_texts]
    return {"members": list(_M["members"]), "groups": _M["stacker"]["groups"], "public_board": _M["scores"]["public_board"]}


# ── LightGBM from its JSON dump ──────────────────────────────────────────────────────────────────────────────────
def _tree_value(node, x):
    while "leaf_value" not in node:
        f = node["split_feature"]; v = x[f]; thr = node["threshold"]; dt = node.get("decision_type", "<=")
        if v is None or (isinstance(v, float) and math.isnan(v)):
            go_left = node.get("default_left", True)
        elif dt == "<=":
            go_left = v <= thr
        elif dt == "==":
            go_left = str(int(v)) in str(thr).split("||")
        else:
            go_left = v < thr
        node = node["left_child"] if go_left else node["right_child"]
    return node["leaf_value"]


def lgbm_predict_proba(model, x):
    raw = sum(_tree_value(t["tree_structure"], x) for t in model["tree_info"])
    return 1.0 / (1.0 + math.exp(-raw))


# ── phases ───────────────────────────────────────────────────────────────────────────────────────────────────────
def _prec(d):
    if not d or d == "0000-00-00":
        return 0
    return 1 if d.endswith("-00-00") else (2 if d.endswith("-00") else 3)


def theta(date, lat=None, lon=None, natal=True):
    """Sidereal (Lahiri) longitudes of BODIES14 at 09:00 local mean time (natal) or 12:00 UT (start); NaN where the
    date's precision cannot place a body."""
    out = np.full(len(BODIES14), np.nan); p = _prec(date)
    if p == 0 or (natal and (lat is None or lon is None or (isinstance(lat, float) and math.isnan(lat)))):
        return out
    y, m, d = int(date[:4]), max(1, int(date[5:7])), max(1, int(date[8:10]))
    hour_ut = (9.0 - float(lon) / 15.0) if natal else 12.0
    jd = _SW.julday(y, m, d, hour_ut)
    try:
        aya = _SW.get_ayanamsa_ut(jd)
    except Exception:
        return out
    codes = {"sun": _SW.SUN, "moon": _SW.MOON, "mercury": _SW.MERCURY, "venus": _SW.VENUS, "mars": _SW.MARS, "jupiter": _SW.JUPITER, "saturn": _SW.SATURN,
             "uranus": _SW.URANUS, "neptune": _SW.NEPTUNE, "pluto": _SW.PLUTO, "true_node": _SW.TRUE_NODE, "chiron": _SW.CHIRON, "mean_lilith": _SW.MEAN_APOG}
    for j, b in enumerate(BODIES14):
        if p == 1 and b not in SLOW:
            continue
        if p == 2 and b not in SLOW and b != "sun":
            continue
        try:
            if b == "true_south_node":
                lon_t = (_SW.calc_ut(jd, _SW.TRUE_NODE)[0][0] + 180.0) % 360.0
            else:
                lon_t = _SW.calc_ut(jd, codes[b])[0][0]
            out[j] = (lon_t - aya) % 360.0
        except Exception:
            pass
    return out


def absdiff(x, y):
    return np.abs((x - y + 180.0) % 360.0 - 180.0)


def phases(t1, t2, tw, labels):
    P = np.full(len(labels), np.nan); col = {b: j for j, b in enumerate(BODIES14)}
    for k, lab in enumerate(labels):
        t, b = lab.split("_", 1); j = col[b]
        if t == "a": P[k] = absdiff(t1[j], t2[j])
        elif t == "t1": P[k] = absdiff(tw[j], t1[j])
        elif t == "t2": P[k] = absdiff(tw[j], t2[j])
        elif t == "n1": P[k] = t1[j]
        elif t == "n2": P[k] = t2[j]
        elif t == "tn": P[k] = tw[j]
    return P


def am_logit(model, P):
    rad = math.pi / 180.0; C, S = np.nan_to_num(np.cos(P * rad)), np.nan_to_num(np.sin(P * rad)); F = model["F0"]; acc = []
    for st in model["stages"]:
        j = st["phasor"]
        if not np.isfinite(P[j]):
            acc.append({"stage": st["stage"], "phasor": model["labels"][j], "contribution": 0.0, "note": "absent"}); continue
        Zr = st["w_re"] * C[j] - st["w_im"] * S[j] + st["b_re"]; Zi = st["w_re"] * S[j] + st["w_im"] * C[j] + st["b_im"]
        u = Zr * Zr + Zi * Zi; c = st["step"] * (st["alpha"] * u + st["c"]); F += c
        acc.append({"stage": st["stage"], "phasor": model["labels"][j], "phase_deg": float(P[j]), "contribution": float(c)})
    return float(F), acc


def _rank(v, grid_key):
    q = np.asarray(_M["rank_reference"]["quantiles"]); g = np.asarray(_M["rank_reference"][grid_key])
    return float(np.interp(v, g, q))


def _geo_x(age1, age2, la, lo, lb, lob, start_year, jan1):
    swap = age2 > age1
    lat_o, lon_o, lat_y, lon_y = (lb, lob, la, lo) if swap else (la, lo, lb, lob)
    nan = lambda v: v is None or (isinstance(v, float) and math.isnan(v))
    if any(nan(v) for v in (lat_o, lon_o, lat_y, lon_y)):
        d = float("nan")
    else:
        d = math.degrees(math.acos(max(-1.0, min(1.0, math.sin(math.radians(lat_o)) * math.sin(math.radians(lat_y)) + math.cos(math.radians(lat_o)) * math.cos(math.radians(lat_y)) * math.cos(math.radians(lon_o - lon_y)))))) * 111.0
    f = lambda a, b, fn: float("nan") if (nan(a) or nan(b)) else fn(a, b)
    return [max(age1, age2), min(age1, age2), abs(age1 - age2), float(start_year), lat_o, lon_o, lat_y, lon_y, d, f(la, lb, max), f(la, lb, min), f(lo, lob, max), f(lo, lob, min),
            (1.0 if (not nan(d) and d < 1) else 0.0), float(jan1), float(nan(la)) + float(nan(lb))]


def predict(dob_1, lat_1, lon_1, dob_2, lat_2, lon_2, start):
    """Probability that the relationship lasted thirty years, with every member's part. Exactly symmetric in the pair."""
    M = _M; labels = M["members"]["AM_GREEDY"]["labels"]
    jan1 = 1.0 if start[5:] == "01-01" else 0.0
    wed = start if jan1 == 0.0 else start[:4] + "-00-00"
    t1, t2, tw = theta(dob_1, lat_1, lon_1), theta(dob_2, lat_2, lon_2), theta(wed, natal=False)
    P12, P21 = phases(t1, t2, tw, labels), phases(t2, t1, tw, labels)
    g12, acc_g = am_logit(M["members"]["AM_GREEDY"], P12); g21, _ = am_logit(M["members"]["AM_GREEDY"], P21)
    f12, acc_f = am_logit(M["members"]["AM_FIXED"], P12); f21, _ = am_logit(M["members"]["AM_FIXED"], P21)
    am_g, am_f = 0.5 * (g12 + g21), 0.5 * (f12 + f21); any_phasor = bool(np.isfinite(P12).any())
    y1, y2, ys = int(dob_1[:4]) if _prec(dob_1) else None, int(dob_2[:4]) if _prec(dob_2) else None, int(start[:4])
    age1 = float(ys - y1) if y1 else float("nan"); age2 = float(ys - y2) if y2 else float("nan")
    x = _geo_x(age1, age2, lat_1, lon_1, lat_2, lon_2, ys, jan1)
    geo_p = float(np.mean([lgbm_predict_proba(mdl, x) for mdl in _GEO]))
    iu = {b: j for j, b in enumerate(BODIES14)}["uranus"]
    hasT = np.isfinite(tw[iu]) and (np.isfinite(t1[iu]) or np.isfinite(t2[iu])); hasA = np.isfinite(t1[iu]) and np.isfinite(t2[iu])
    group = "0" if hasT else ("1" if hasA else "2")
    w = M["stacker"]["weights"].get(group) or M["stacker"]["weights"]["2"]
    r_geo = _rank(geo_p, "GEO") - 0.5; r_g = (_rank(am_g, "AM_GREEDY") - 0.5) if any_phasor else 0.0; r_f = (_rank(am_f, "AM_FIXED") - 0.5) if any_phasor else 0.0
    z = w["w"][0] * r_geo + w["w"][1] * r_g + w["w"][2] * r_f + w["b"]
    return {"probability": 1.0 / (1.0 + math.exp(-z)), "logit": z, "group": group, "group_meaning": M["stacker"]["groups"][group],
            "breakdown": {"GEO": {"probability": geo_p, "rank": r_geo + 0.5, "weight": w["w"][0], "inputs": dict(zip(M["members"]["GEO"]["feature_names"], x))},
                          "AM_GREEDY": {"logit": am_g, "rank": r_g + 0.5, "weight": w["w"][1], "stages": acc_g},
                          "AM_FIXED": {"logit": am_f, "rank": r_f + 0.5, "weight": w["w"][2], "stages": acc_f}, "bias": w["b"]},
            "phases_deg": {"partner_1": {b: (None if not np.isfinite(v) else float(v)) for b, v in zip(BODIES14, t1)}, "partner_2": {b: (None if not np.isfinite(v) else float(v)) for b, v in zip(BODIES14, t2)},
                           "start": {b: (None if not np.isfinite(v) else float(v)) for b, v in zip(BODIES14, tw)}}}
