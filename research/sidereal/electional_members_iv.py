"""
electional_members_iv.py — the WEDDING-DAY astrology the traditions are most specific about, plus deep numerology
(operator 2026-08-21: "improve the robustness and diversity of its astrology and numerology features").

WHY THIS FAMILY IS DIFFERENT. Every member so far reads the couple's charts; the classical ELECTIONAL rules read
the DAY: marry on a waxing Moon, never with Venus retrograde, avoid the eclipse season, prefer the Moon's
auspicious nakṣatras, mind the planetary day and hour. They apply to every row whose wedding day is real, and they
are exactly the quantities the best-day search optimises — so if any astrology earns weight here, it earns it
where it would actually be used.

ROBUSTNESS (the honest part). Nobody's birth hour is recorded and the wedding hour is not either, so a hard
"the Moon was in Leo" is a coin flip near a boundary. Every sign/nakṣatra quantity here is therefore SOFT:
computed at 00:00 and 24:00 UT of the day and reported as the FRACTION of the day spent in the dominant division
plus a boundary-crossed flag — a membership, not a claim. Sign-level features are also averaged over FIVE
ayanāṁśas rather than pinned to one.

MEMBERS: ELECTIONAL (day only, no ages) · ELECTIONAL + couple crossings · NUMEROLOGY DEEP (no ages) ·
PLAIN + each. Forward-chained OOF like every other member file. Writes AQ_OUT/electional_members.npz.
"""
import json
import os
import sys
import time
import datetime as dt

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "web"))
from artamodel import auc, absdiff   # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq8"); PH = os.environ.get("AQ_PHASES", "/tmp/aq8feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq8sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
CHALDEAN_DAY = ["moon", "mars", "mercury", "jupiter", "venus", "saturn", "sun"]      # Mon..Sun rulers
CHALDEAN_ORDER = ["saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon"]    # the planetary-hour sequence
NAK_GOOD = {2, 4, 6, 11, 12, 13, 16, 20, 21, 25, 26}    # nakṣatras classically fit for vivāha (0-indexed)


def _day_features(SW, codes, y, m, d):
    """Everything the classical rules read about ONE day, hour-marginalised where the hour matters."""
    jd0 = SW.julday(y, m, d, 0.0); jd12 = SW.julday(y, m, d, 12.0); jd24 = SW.julday(y, m, d, 24.0)
    out = {}
    lon = {}; spd = {}
    for b, c in codes.items():
        try:
            r = SW.calc_ut(jd12, c)[0]; lon[b] = r[0]; spd[b] = r[3]
        except Exception:
            lon[b] = np.nan; spd[b] = np.nan
    try:
        aya = np.mean([_aya(SW, jd12, mo) for mo in (SW.SIDM_LAHIRI, SW.SIDM_FAGAN_BRADLEY, SW.SIDM_KRISHNAMURTI, SW.SIDM_RAMAN, SW.SIDM_YUKTESHWAR)])
    except Exception:
        aya = np.nan
    # ── Moon phase / tithi: the single most-cited electional quantity ──────────────────────────────────────────
    elong = (lon.get("moon", np.nan) - lon.get("sun", np.nan)) % 360.0
    out["elong"] = elong
    out["waxing"] = float(elong < 180.0) if np.isfinite(elong) else np.nan
    out["tithi"] = np.floor(elong / 12.0) if np.isfinite(elong) else np.nan
    out["moon_illum"] = (1 - np.cos(np.radians(elong))) / 2 if np.isfinite(elong) else np.nan
    out["near_full"] = float(abs(((elong - 180 + 180) % 360) - 180) < 15) if np.isfinite(elong) else np.nan
    out["near_new"] = float(min(elong, 360 - elong) < 15) if np.isfinite(elong) else np.nan
    # ── retrogrades: "never marry with Venus retrograde" ───────────────────────────────────────────────────────
    for b in ("mercury", "venus", "mars", "jupiter", "saturn"):
        out[f"retro_{b}"] = float(spd.get(b, np.nan) < 0) if np.isfinite(spd.get(b, np.nan)) else np.nan
    out["n_retro"] = np.nansum([out[f"retro_{b}"] for b in ("mercury", "venus", "mars", "jupiter", "saturn")])
    out["venus_speed"] = spd.get("venus", np.nan); out["moon_speed"] = spd.get("moon", np.nan)
    # ── eclipse season: |Sun − node| and |Moon − node| ─────────────────────────────────────────────────────────
    node = lon.get("true_node", np.nan)
    out["sun_node"] = absdiff(lon.get("sun", np.nan), node); out["moon_node"] = absdiff(lon.get("moon", np.nan), node)
    out["eclipse_season"] = float(min(out["sun_node"], 180 - out["sun_node"]) < 18) if np.isfinite(out["sun_node"]) else np.nan
    # ── the classical marriage significators, as separations on the day ────────────────────────────────────────
    for a, b in (("moon", "venus"), ("moon", "saturn"), ("venus", "mars"), ("venus", "jupiter"), ("sun", "moon"), ("moon", "mars")):
        out[f"sep_{a}_{b}"] = absdiff(lon.get(a, np.nan), lon.get(b, np.nan))
    # ── SOFT sign / nakṣatra membership over the day (the hour is unknown) ─────────────────────────────────────
    for b in ("moon", "sun"):
        try:
            l0 = (SW.calc_ut(jd0, codes[b])[0][0] - aya) % 360.0; l24 = (SW.calc_ut(jd24, codes[b])[0][0] - aya) % 360.0
        except Exception:
            l0 = l24 = np.nan
        for name, width in (("sign", 30.0), ("nak", 360.0 / 27)):
            if not (np.isfinite(l0) and np.isfinite(l24)):
                out[f"{b}_{name}"] = np.nan; out[f"{b}_{name}_frac"] = np.nan; out[f"{b}_{name}_cross"] = np.nan; continue
            i0 = int(l0 // width); i24 = int(l24 // width)
            crossed = float(i0 != i24)
            if crossed:
                edge = (i0 + 1) * width % 360.0
                span = (edge - l0) % 360.0; total = (l24 - l0) % 360.0
                frac0 = span / total if total > 1e-9 else 0.5
                dom = i0 if frac0 >= 0.5 else i24; frac = max(frac0, 1 - frac0)
            else:
                dom = i0; frac = 1.0
            out[f"{b}_{name}"] = float(dom); out[f"{b}_{name}_frac"] = float(frac); out[f"{b}_{name}_cross"] = crossed
        out[f"{b}_deg_in_sign"] = float(l0 % 30.0) if np.isfinite(l0) else np.nan
    nk = out.get("moon_nak", np.nan)
    out["nak_auspicious"] = float(int(nk) in NAK_GOOD) if np.isfinite(nk) else np.nan
    # ── planetary day and hour (noon) ──────────────────────────────────────────────────────────────────────────
    wd = dt.date(y, m, d).weekday()
    out["day_ruler"] = float(CHALDEAN_ORDER.index(CHALDEAN_DAY[wd]))
    out["hour_ruler_noon"] = float((CHALDEAN_ORDER.index(CHALDEAN_DAY[wd]) + 6) % 7)   # ~6 planetary hours after sunrise
    out["weekday"] = float(wd)
    return out


def _aya(SW, jd, mode):
    SW.set_sid_mode(mode); return SW.get_ayanamsa_ut(jd)


def _num(dstr):
    """Deep numerology of one date: life path (master numbers kept), birthday, attitude, Chaldean, karmic debt."""
    if not isinstance(dstr, str) or dstr[:4] == "0000":
        return {k: np.nan for k in ("lp", "raw", "bd", "att", "chald", "karmic", "master", "digits")}
    digits = [int(c) for c in dstr if c.isdigit()]
    raw = sum(digits)
    def red(x, keep=True):
        while x > 9 and not (keep and x in (11, 22, 33)):
            x = sum(int(c) for c in str(x))
        return x
    y, m, d = dstr[:4], dstr[5:7], dstr[8:10]
    lp = red(raw)
    bd = red(int(d), keep=False) if d != "00" else np.nan
    att = red(int(m) + int(d), keep=False) if (m != "00" and d != "00") else np.nan
    chald = red(sum(int(c) for c in (y + m + d)), keep=False)
    return {"lp": float(lp), "raw": float(raw), "bd": float(bd) if bd == bd else np.nan, "att": float(att) if att == att else np.nan,
            "chald": float(chald), "karmic": float(raw in (13, 14, 16, 19)), "master": float(lp in (11, 22, 33)), "digits": float(len(set(digits)))}


def build(df, SW, codes, cache):
    n = len(df); rows_e = []; rows_n = []
    for r in df.itertuples(index=False):
        s = r.start
        if isinstance(s, str) and not s.endswith("-00"):
            key = s
            if key not in cache:
                try:
                    cache[key] = _day_features(SW, codes, int(s[:4]), int(s[5:7]), int(s[8:10]))
                except Exception:
                    cache[key] = None
            rows_e.append(cache[key])
        else:
            rows_e.append(None)
        na, nb, ns = _num(r.dob_a), _num(r.dob_b), _num(s)
        sy = int(s[:4]) if isinstance(s, str) and s[:4] != "0000" else np.nan
        pya = ((na["raw"] + (sy or 0)) % 9) if np.isfinite(na["raw"]) and sy == sy else np.nan     # personal year (reduced mod 9)
        pyb = ((nb["raw"] + (sy or 0)) % 9) if np.isfinite(nb["raw"]) and sy == sy else np.nan
        rel = (na["lp"] + nb["lp"]) if np.isfinite(na["lp"]) and np.isfinite(nb["lp"]) else np.nan
        grp = lambda v: (0 if v in (1, 5, 7) else (1 if v in (2, 4, 8) else 2)) if np.isfinite(v) else np.nan
        doy_a = _doy(r.dob_a); doy_b = _doy(r.dob_b); doy_s = _doy(s)
        rows_n.append([na["lp"], nb["lp"], max(na["lp"], nb["lp"]) if np.isfinite(na["lp"] + nb["lp"]) else np.nan,
                       min(na["lp"], nb["lp"]) if np.isfinite(na["lp"] + nb["lp"]) else np.nan,
                       abs(na["lp"] - nb["lp"]) if np.isfinite(na["lp"] + nb["lp"]) else np.nan,
                       float(na["lp"] == nb["lp"]) if np.isfinite(na["lp"] + nb["lp"]) else np.nan,
                       rel, (rel % 9) if rel == rel else np.nan, float(grp(na["lp"]) == grp(nb["lp"])) if np.isfinite(na["lp"] + nb["lp"]) else np.nan,
                       na["bd"], nb["bd"], na["att"], nb["att"], na["chald"], nb["chald"],
                       na["karmic"], nb["karmic"], na["master"], nb["master"], ns["lp"], ns["raw"] % 9 if np.isfinite(ns["raw"]) else np.nan,
                       pya, pyb, abs(pya - pyb) if np.isfinite(pya) and np.isfinite(pyb) else np.nan,
                       na["digits"], nb["digits"],
                       (doy_a % 7) if doy_a == doy_a else np.nan, (doy_b % 7) if doy_b == doy_b else np.nan,
                       (doy_a % 19) if doy_a == doy_a else np.nan, (doy_b % 19) if doy_b == doy_b else np.nan,
                       (doy_s % 7) if doy_s == doy_s else np.nan, (doy_s % 28) if doy_s == doy_s else np.nan,
                       abs((doy_a or 0) - (doy_b or 0)) if (doy_a == doy_a and doy_b == doy_b) else np.nan])
    keys = sorted({k for e in rows_e if e for k in e})
    E = np.full((n, len(keys)), np.nan)
    for i, e in enumerate(rows_e):
        if e:
            E[i] = [e.get(k, np.nan) for k in keys]
    return E.astype(np.float32), keys, np.array(rows_n, dtype=np.float32)


def _doy(dstr):
    try:
        return float(dt.date(int(dstr[:4]), int(dstr[5:7]), int(dstr[8:10])).timetuple().tm_yday)
    except Exception:
        return np.nan


def main():
    import lightgbm as lgb
    import sweshim as SW
    SW.load(os.path.join(ROOT, "web", "ephem4.bin"), os.path.join(ROOT, "web", "tables.json"))
    codes = {"sun": SW.SUN, "moon": SW.MOON, "mercury": SW.MERCURY, "venus": SW.VENUS, "mars": SW.MARS, "jupiter": SW.JUPITER,
             "saturn": SW.SATURN, "true_node": SW.TRUE_NODE}
    Z = np.load(PH, allow_pickle=True); y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); s1, s2 = list(Z["slots"])
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    cache = {}
    Etr, ekeys, Ntr = build(tr, SW, codes, cache); log(f"train: {Etr.shape[1]} electional + {Ntr.shape[1]} numerology features ({len(cache):,} distinct days)")
    Ete, _, Nte = build(te, SW, codes, cache); log(f"test built ({len(cache):,} days cached)")
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    plain = lambda p: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]), np.abs(p[:, ia] - p[:, ib]), p[:, iy]])
    prm = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.7, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)
    members_tr, members_te, names, meta = [], [], [], []
    def member(Xa, Xb, name):
        rows = np.isfinite(Xa).any(1); s_tr = np.full(len(y), np.nan)
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = rows & (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); fit = rows & (later <= lo)
            if fit.sum() < 500:
                continue
            c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[fit], y[fit]); s_tr[blk] = c.predict_proba(Xa[blk])[:, 1]
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[rows], y[rows])
        s_te = np.full(len(Xb), np.nan); rte = np.isfinite(Xb).any(1); s_te[rte] = c.predict_proba(Xb[rte])[:, 1]
        f = np.isfinite(s_tr) & (later > cuts[0]); o = auc(y[f], s_tr[f]) if f.sum() > 500 else float("nan")
        members_tr.append(s_tr); members_te.append(s_te); names.append(name); meta.append({"member": name, "forward_oof": o, "n_features": int(Xa.shape[1]), "n_rows": int(rows.sum())})
        log(f"  {name:<52} {Xa.shape[1]:>3} feats · {rows.sum():>7,} rows · fwd-OOF {o:.4f}")
    member(Etr, Ete, "ELECTIONAL (wedding day: phase, retro, eclipse, nakṣatra)")
    member(np.column_stack([plain(ptr), Etr]), np.column_stack([plain(pte), Ete]), "PLAIN + ELECTIONAL")
    member(Ntr, Nte, "NUMEROLOGY DEEP (life path, personal year, karmic, Chaldean)")
    member(np.column_stack([plain(ptr), Ntr]), np.column_stack([plain(pte), Nte]), "PLAIN + NUMEROLOGY DEEP")
    member(np.column_stack([plain(ptr), Etr, Ntr]), np.column_stack([plain(pte), Ete, Nte]), "PLAIN + ELECTIONAL + NUMEROLOGY")
    np.savez_compressed(os.path.join(OUT, "electional_members.npz"), S_train=np.column_stack(members_tr), S_test=np.column_stack(members_te),
                        names=np.array(names), meta=json.dumps(meta), electional_names=np.array(ekeys, dtype=object))
    log(f"wrote {OUT}/electional_members.npz with {len(names)} members")


if __name__ == "__main__":
    main()
