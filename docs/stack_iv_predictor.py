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


def _geo_x(age1, age2, la, lo, lb, lob, start_year, jan1, wd=float("nan"), mo=float("nan")):
    nan0 = lambda v: -999.0 if (v is None or (isinstance(v, float) and math.isnan(v))) else v
    key1 = nan0(la) * 1000 + nan0(lo); key2 = nan0(lb) * 1000 + nan0(lob)
    swap = (age2 > age1) or (age2 == age1 and key2 < key1)          # symmetric tie-break: equal ages -> by (lat, lon)
    lat_o, lon_o, lat_y, lon_y = (lb, lob, la, lo) if swap else (la, lo, lb, lob)
    nan = lambda v: v is None or (isinstance(v, float) and math.isnan(v))
    if any(nan(v) for v in (lat_o, lon_o, lat_y, lon_y)):
        d = float("nan")
    else:
        d = math.degrees(math.acos(max(-1.0, min(1.0, math.sin(math.radians(lat_o)) * math.sin(math.radians(lat_y)) + math.cos(math.radians(lat_o)) * math.cos(math.radians(lat_y)) * math.cos(math.radians(lon_o - lon_y)))))) * 111.0
    f = lambda a, b, fn: float("nan") if (nan(a) or nan(b)) else fn(a, b)
    return [max(age1, age2), min(age1, age2), abs(age1 - age2), float(start_year), lat_o, lon_o, lat_y, lon_y, d, f(la, lb, max), f(la, lb, min), f(lo, lob, max), f(lo, lob, min),
            (1.0 if (not nan(d) and d < 1) else 0.0), float(jan1), float(nan(la)) + float(nan(lb)), wd, mo]


def predict(dob_1, lat_1, lon_1, dob_2, lat_2, lon_2, start):
    """Probability that the relationship lasted thirty years, with every member's part. Exactly symmetric in the pair."""
    M = _M; labels = M["members"]["AM_GREEDY"]["labels"]
    jan1 = 1.0 if start.endswith("-00-00") else 0.0                       # "year only" is spelled YYYY-00-00; a 1 January is a day
    wed = start
    t1, t2, tw = theta(dob_1, lat_1, lon_1), theta(dob_2, lat_2, lon_2), theta(wed, natal=False)
    P12, P21 = phases(t1, t2, tw, labels), phases(t2, t1, tw, labels)
    g12, acc_g = am_logit(M["members"]["AM_GREEDY"], P12); g21, _ = am_logit(M["members"]["AM_GREEDY"], P21)
    f12, acc_f = am_logit(M["members"]["AM_FIXED"], P12); f21, _ = am_logit(M["members"]["AM_FIXED"], P21)
    am_g, am_f = 0.5 * (g12 + g21), 0.5 * (f12 + f21); any_phasor = bool(np.isfinite(P12).any())
    y1, y2, ys = int(dob_1[:4]) if _prec(dob_1) else None, int(dob_2[:4]) if _prec(dob_2) else None, int(start[:4])
    age1 = float(ys - y1) if y1 else float("nan"); age2 = float(ys - y2) if y2 else float("nan")
    import datetime as _dt
    try:
        if start.endswith("-00-00"): wd_, mo_ = float("nan"), float("nan")
        elif start.endswith("-00"): wd_, mo_ = float("nan"), float(int(start[5:7]))
        else: _sd = _dt.date(ys, int(start[5:7]), int(start[8:10])); wd_, mo_ = float(_sd.weekday()), float(_sd.month)
    except Exception:
        wd_, mo_ = float("nan"), float("nan")
    x = _geo_x(age1, age2, lat_1, lon_1, lat_2, lon_2, ys, jan1, wd_, mo_)
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


# ── THE MATCH FINDER ─────────────────────────────────────────────────────────────────────────────────────────────
# Operator 2026-08-19: "given someone's DOB and POB it should list the top 20 DOB+POB … search the capital of each
# country for each day from the range of DOBs of people alive." The deployed stack is evaluated on EVERY (day,
# capital) in the range — ~30,000 days × 197 capitals — by using its structure: the geography member depends on the
# candidate only through the birth YEAR and the capital (one vectorised pass over years × capitals), and the two
# ArtaModel members only through the candidate's outer-planet longitudes on the birth DAY (sampled weekly and
# interpolated — Uranus moves under 0.06°/day, so the error is below 0.02°; the capital's longitude shifts the
# 09:00 local instant by at most 12 h, under 0.006° for the bodies the model reads, and is ignored for the
# candidate's phases). The candidate takes slot 2; both orders are scored and averaged as everywhere else.
_CAPS = None


def _flatten(tree):
    feats, thr, left, right, dleft, leaf = [], [], [], [], [], []
    def rec(node):
        i = len(feats)
        if "leaf_value" in node:
            feats.append(-1); thr.append(0.0); left.append(-1); right.append(-1); dleft.append(True); leaf.append(float(node["leaf_value"])); return i
        feats.append(int(node["split_feature"])); thr.append(float(node["threshold"])); left.append(-1); right.append(-1); dleft.append(bool(node.get("default_left", True))); leaf.append(0.0)
        l = rec(node["left_child"]); r = rec(node["right_child"]); left[i] = l; right[i] = r; return i
    rec(tree)
    return np.array(feats), np.array(thr), np.array(left), np.array(right), np.array(dleft), np.array(leaf)


def lgbm_predict_proba_batch(model, X):
    """Vectorised evaluation of a LightGBM JSON dump over rows X (n, f) — identical to lgbm_predict_proba row by row."""
    X = np.asarray(X, dtype=float); n = X.shape[0]; raw = np.zeros(n)
    flat = model.get("_flat")
    if flat is None:
        flat = [_flatten(t["tree_structure"]) for t in model["tree_info"]]; model["_flat"] = flat
    for feats, thr, left, right, dleft, leaf in flat:
        node = np.zeros(n, dtype=int); active = feats[node] >= 0
        while active.any():
            idx = np.where(active)[0]; f = feats[node[idx]]; v = X[idx, f]; nanv = np.isnan(v)
            go_left = np.where(nanv, dleft[node[idx]], v <= thr[node[idx]])
            node[idx] = np.where(go_left, left[node[idx]], right[node[idx]]); active = feats[node] >= 0
        raw += leaf[node]
    return 1.0 / (1.0 + np.exp(-raw))


def _jd(y, m, d, hour_ut):
    return _SW.julday(int(y), int(m), int(d), float(hour_ut))


def _outer_lon_by_day(jd_days):
    """Sidereal (Lahiri) longitudes of Uranus, Neptune, Pluto on each JD (09:00 UT), sampled weekly and interpolated."""
    jd0, jd1 = float(jd_days[0]), float(jd_days[-1]); samp = np.arange(jd0, jd1 + 7.0, 7.0)
    out = {}
    for name, code in (("uranus", _SW.URANUS), ("neptune", _SW.NEPTUNE), ("pluto", _SW.PLUTO)):
        vals = np.array([(_SW.calc_ut(j, code)[0][0] - _SW.get_ayanamsa_ut(j)) % 360.0 for j in samp])
        unwrapped = np.degrees(np.unwrap(np.radians(vals)))
        out[name] = np.interp(jd_days, samp, unwrapped) % 360.0
    return out


def best_matches(dob, lat, lon, start=None, top=20, min_age=18, max_age=100, capitals=None):
    """Top (birth day, capital) candidates for the person (dob, lat, lon) with a relationship beginning on `start`
    (YYYY-MM-DD; default today), over everyone alive aged min_age..max_age at the start, in every country's capital."""
    import datetime as dt
    M = _M; labels = M["members"]["AM_GREEDY"]["labels"]; caps = capitals if capitals is not None else _CAPS
    if caps is None:
        raise RuntimeError("capitals not loaded — pass capitals=[{country, capital, lat, lon}, ...] or set stack_iv_predictor._CAPS")
    today = dt.date.today(); start = start or today.isoformat(); jan1 = 1.0 if start.endswith("-00-00") else 0.0
    sy, sm, sd = int(start[:4]), max(1, int(start[5:7])), max(1, int(start[8:10]))
    # the candidate days: everyone aged min_age..max_age at the start
    d_lo = dt.date(sy - max_age, sm, sd); d_hi = dt.date(sy - min_age, sm, sd); ndays = (d_hi - d_lo).days + 1
    days = [d_lo + dt.timedelta(days=i) for i in range(ndays)]; jds = np.array([_jd(d.year, d.month, d.day, 9.0) for d in days])
    yrs = np.array([d.year for d in days]); cand_years = np.arange(yrs.min(), yrs.max() + 1)
    # the person's and the start's phases (exact), the candidates' outer planets per day
    t1 = theta(dob, lat, lon); tw = theta(start, natal=False)
    L = _outer_lon_by_day(jds); col = {b: j for j, b in enumerate(BODIES14)}
    cand = np.full((ndays, len(BODIES14)), np.nan); cand[:, col["uranus"]] = L["uranus"]; cand[:, col["neptune"]] = L["neptune"]; cand[:, col["pluto"]] = L["pluto"]
    # ArtaModel logits per day, both orders (person = slot 1 / slot 2), vectorised over the stages' phasors
    def am_batch(model, T1, T2):
        n = T2.shape[0] if T2.ndim == 2 else T1.shape[0]; F = np.full(n, model["F0"]); rad = np.pi / 180.0
        for st in model["stages"]:
            t, b = labels[st["phasor"]].split("_", 1); j = col[b]
            a = T1[:, j] if T1.ndim == 2 else np.full(n, T1[j]); c = T2[:, j] if T2.ndim == 2 else np.full(n, T2[j])
            if t == "a": P = absdiff(a, c)
            elif t == "t1": P = absdiff(np.full(n, tw[j]), a)
            elif t == "t2": P = absdiff(np.full(n, tw[j]), c)
            elif t == "n1": P = a
            elif t == "n2": P = c
            else: P = np.full(n, tw[j])
            ok = np.isfinite(P); C, S = np.where(ok, np.cos(P * rad), 0.0), np.where(ok, np.sin(P * rad), 0.0)
            Zr = st["w_re"] * C - st["w_im"] * S + st["b_re"]; Zi = st["w_re"] * S + st["w_im"] * C + st["b_im"]
            F = F + np.where(ok, st["step"] * (st["alpha"] * (Zr * Zr + Zi * Zi) + st["c"]), 0.0)
        return F
    am_g = 0.5 * (am_batch(M["members"]["AM_GREEDY"], t1, cand) + am_batch(M["members"]["AM_GREEDY"], cand, t1))
    am_f = 0.5 * (am_batch(M["members"]["AM_FIXED"], t1, cand) + am_batch(M["members"]["AM_FIXED"], cand, t1))
    # geography per (year, capital)
    y1 = int(dob[:4]) if _prec(dob) else None; age1 = float(sy - y1) if y1 else float("nan")
    try:
        if start.endswith("-00-00"): wd_, mo_ = float("nan"), float("nan")
        elif start.endswith("-00"): wd_, mo_ = float("nan"), float(sm)
        else: _sd = dt.date(sy, sm, sd); wd_, mo_ = float(_sd.weekday()), float(_sd.month)
    except Exception:
        wd_, mo_ = float("nan"), float("nan")
    rows = []
    for yy in cand_years:
        for cp in caps:
            rows.append(_geo_x(age1, float(sy - yy), lat, lon, cp["lat"], cp["lon"], sy, jan1, wd_, mo_))
    X = np.array(rows, dtype=float); geo = np.mean([lgbm_predict_proba_batch(m, X) for m in _GEO], axis=0).reshape(len(cand_years), len(caps))
    # ranks and the stack, on the full day x capital grid
    q = np.asarray(M["rank_reference"]["quantiles"]); rk = lambda v, key: np.interp(v, np.asarray(M["rank_reference"][key]), q)
    iu = col["uranus"]; hasT = np.isfinite(tw[iu]) and np.isfinite(t1[iu]); hasA = np.isfinite(t1[iu])
    group = "0" if hasT else ("1" if hasA else "2"); w = M["stacker"]["weights"].get(group) or M["stacker"]["weights"]["2"]
    r_geo = rk(geo, "GEO") - 0.5                                   # (years, caps)
    r_g = rk(am_g, "AM_GREEDY") - 0.5; r_f = rk(am_f, "AM_FIXED") - 0.5   # (days,)
    yi = yrs - cand_years[0]
    Z = w["w"][0] * r_geo[yi, :] + (w["w"][1] * r_g + w["w"][2] * r_f)[:, None] + w["b"]     # (days, caps)
    # one entry per (year, capital): the best DAY of that year in that capital, then the top of those — so the list
    # reads as `top` distinct matches rather than twenty consecutive days in one city
    best_day = np.full((len(cand_years), len(caps)), -1, dtype=int); best_z = np.full((len(cand_years), len(caps)), -np.inf)
    for y_i in range(len(cand_years)):
        rows_y = np.where(yi == y_i)[0]
        if rows_y.size == 0:
            continue
        sub = Z[rows_y, :]; am = np.argmax(sub, axis=0); best_day[y_i, :] = rows_y[am]; best_z[y_i, :] = sub[am, np.arange(len(caps))]
    order = np.argsort(-best_z, axis=None)[:top]; out = []
    for k in order:
        y_i, ci = divmod(int(k), len(caps)); di = int(best_day[y_i, ci]); cp = caps[ci]
        out.append({"dob": days[di].isoformat(), "country": cp["country"], "capital": cp["capital"], "lat": cp["lat"], "lon": cp["lon"],
                    "probability": float(1 / (1 + np.exp(-Z[di, ci]))), "geo_probability": float(geo[y_i, ci]), "am_greedy_logit": float(am_g[di]), "am_fixed_logit": float(am_f[di])})
    return {"start": start, "group": group, "n_candidates": int(ndays * len(caps)), "n_days": int(ndays), "n_capitals": len(caps), "matches": out,
            "note": "the candidate's phases are the outer planets at 09:00 UT of the day (weekly samples interpolated); the capital enters through the geography member; a year-only start is spelled YYYY-00-00"}


# ── THE BEST START DAY (electional) ──────────────────────────────────────────────────────────────────────────────
def best_start_days(dob_1, lat_1, lon_1, dob_2, lat_2, lon_2, from_date=None, years=5, top=20):
    """For a given pair, the `top` start days in [from_date, from_date + years) by the deployed stack: the start
    day enters through the two ages, the weekday and month (geography member) and the start-day outer planets
    (the ArtaModel t1/t2 terms); both orders of the pair are averaged. Candidate start-day skies are sampled
    weekly and interpolated (< 0.02°)."""
    import datetime as dt
    M = _M; labels = M["members"]["AM_GREEDY"]["labels"]; col = {b: j for j, b in enumerate(BODIES14)}
    today = dt.date.today(); d0 = dt.date.fromisoformat(from_date) if from_date else today
    ndays = int(round(365.2425 * years)); days = [d0 + dt.timedelta(days=i) for i in range(ndays)]          # every day, 1 January included: "year only" is spelled YYYY-00-00
    jds = np.array([_jd(d.year, d.month, d.day, 12.0) for d in days])
    t1, t2 = theta(dob_1, lat_1, lon_1), theta(dob_2, lat_2, lon_2)
    L = _outer_lon_by_day(jds); TW = np.full((ndays, len(BODIES14)), np.nan); TW[:, col["uranus"]] = L["uranus"]; TW[:, col["neptune"]] = L["neptune"]; TW[:, col["pluto"]] = L["pluto"]
    def am_batch(model, A_, B_):
        F = np.full(ndays, model["F0"]); rad = np.pi / 180.0
        for st in model["stages"]:
            t, b = labels[st["phasor"]].split("_", 1); j = col[b]
            if t == "a": P = np.full(ndays, absdiff(A_[j], B_[j]))
            elif t == "t1": P = absdiff(TW[:, j], np.full(ndays, A_[j]))
            elif t == "t2": P = absdiff(TW[:, j], np.full(ndays, B_[j]))
            elif t == "n1": P = np.full(ndays, A_[j])
            elif t == "n2": P = np.full(ndays, B_[j])
            else: P = TW[:, j]
            ok = np.isfinite(P); C, S = np.where(ok, np.cos(P * rad), 0.0), np.where(ok, np.sin(P * rad), 0.0)
            Zr = st["w_re"] * C - st["w_im"] * S + st["b_re"]; Zi = st["w_re"] * S + st["w_im"] * C + st["b_im"]
            F = F + np.where(ok, st["step"] * (st["alpha"] * (Zr * Zr + Zi * Zi) + st["c"]), 0.0)
        return F
    am_g = 0.5 * (am_batch(M["members"]["AM_GREEDY"], t1, t2) + am_batch(M["members"]["AM_GREEDY"], t2, t1))
    am_f = 0.5 * (am_batch(M["members"]["AM_FIXED"], t1, t2) + am_batch(M["members"]["AM_FIXED"], t2, t1))
    y1 = int(dob_1[:4]) if _prec(dob_1) else None; y2 = int(dob_2[:4]) if _prec(dob_2) else None
    rows = []
    for d in days:
        a1 = float(d.year - y1) if y1 else float("nan"); a2 = float(d.year - y2) if y2 else float("nan")
        rows.append(_geo_x(a1, a2, lat_1, lon_1, lat_2, lon_2, d.year, 0.0, float(d.weekday()), float(d.month)))
    geo = np.mean([lgbm_predict_proba_batch(m, np.array(rows, dtype=float)) for m in _GEO], axis=0)
    q = np.asarray(M["rank_reference"]["quantiles"]); rk = lambda v, key: np.interp(v, np.asarray(M["rank_reference"][key]), q)
    iu = col["uranus"]; hasA = np.isfinite(t1[iu]) and np.isfinite(t2[iu]); hasT = (np.isfinite(t1[iu]) or np.isfinite(t2[iu]))
    group = "0" if hasT else ("1" if hasA else "2"); w = M["stacker"]["weights"].get(group) or M["stacker"]["weights"]["2"]
    Z = w["w"][0] * (rk(geo, "GEO") - 0.5) + w["w"][1] * (rk(am_g, "AM_GREEDY") - 0.5) + w["w"][2] * (rk(am_f, "AM_FIXED") - 0.5) + w["b"]
    row = lambda i: {"start": days[i].isoformat(), "weekday": days[i].strftime("%A"), "probability": float(1 / (1 + np.exp(-Z[i]))), "geo_probability": float(geo[i]), "am_greedy_logit": float(am_g[i]), "am_fixed_logit": float(am_f[i])}
    # TWENTY OPTIONS, not twenty copies of one week: the best day of each calendar month, ranked, `top` of them —
    # consecutive Tuesdays of one month are one option, not twenty (operator 2026-08-19)
    best_in_month = {}
    for i, d in enumerate(days):
        k = d.strftime("%Y-%m")
        if k not in best_in_month or Z[i] > Z[best_in_month[k]]:
            best_in_month[k] = i
    options = [dict(row(i), month=k) for k, i in sorted(best_in_month.items(), key=lambda kv: -Z[kv[1]])][:top]
    raw = [row(i) for i in np.argsort(-Z)[:top]]
    return {"from": d0.isoformat(), "years": years, "n_days": ndays, "group": group, "best_days": options, "raw_top_days": raw, "note": "every calendar day scored; a year-only start is spelled YYYY-00-00",
            "best_day_per_month": [dict(row(i), month=k) for k, i in sorted(best_in_month.items())]}
