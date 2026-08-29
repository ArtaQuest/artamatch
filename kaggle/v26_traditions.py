"""v26_traditions.py — a third wave: the lagna systems, the compatibility systems, and the finer charts.

v21 filled the broad gaps; v23 added the doctrines whose purpose is marriage. This adds what is still
missing, and the first entry is the one that should embarrass us for being late:

  CHANDRA LAGNA   Vedic practice reads a chart from the MOON as ascendant when no birth time is known,
                  which is our exact situation. We already used it for Manglik and then never used it
                  again. Here every planet of his is placed in the twelve houses of HER Moon-lagna, and
                  the reverse — the standard cross-placement a Vedic astrologer actually does.
  SURYA LAGNA     the same from the Sun, the other classical time-free ascendant.
  NINE STAR KI    the Japanese nine-star system, used for compatibility specifically, from the birth
                  year and month; with the element production and control relations between two stars.
  TIBETAN         Mewa (the nine magic-square numbers) and Parkha (the eight trigrams), both from year.
  SOLAR TERMS     the twenty-four jieqi — the Chinese solar calendar the whole agricultural year is cut
                  by — taken from the Sun's tropical longitude, ayanamsa restored.
  DIVISIONALS     D3 Drekkana, D7 Saptamsa (progeny — the chart read for children) and D12 Dwadasamsa,
                  beside the D9 already present.
  NAMED YOGAS     Gaja Kesari, Chandra Mangala, Budha Aditya and Kala Sarpa — classical configurations,
                  each computable without a birth time, each paired across the two charts.
  FIXED STARS     Regulus, Spica, Aldebaran, Antares, Algol, Sirius, Fomalhaut — nearly fixed in a
                  sidereal zodiac, which is what ours is.
  MANSIONS        the twenty-eight Arabic manazil, beside the twenty-seven nakshatras.
  HARMONICS       the 4th, 6th, 8th and 12th, beside the 5th, 7th and 9th.
  SOLAR ARC       directions at a degree for a year, each chart advanced to the other's birth.
  DEGREES         the classical critical degrees, and the anaretic 29th.
  CONTRA-ANTISCIA the second classical mirror, across the equinoctial axis.
  HIJRI           the Islamic lunar calendar date.

Every statement uses BOTH dates. build(df, Z, split, exclude, min_support) -> (X, names).
"""
import numpy as np
import pandas as pd

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
PLANETS = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
NSK_EL = ["Water", "Earth", "Wood", "Wood", "Earth", "Metal", "Metal", "Earth", "Fire"]  # stars 1..9
TRIGRAM = ["Li", "Kan", "Dui", "Qian", "Kun", "Gen", "Zhen", "Xun"]
JIEQI = ["Lichun", "Yushui", "Jingzhe", "Chunfen", "Qingming", "Guyu", "Lixia", "Xiaoman", "Mangzhong",
         "Xiazhi", "Xiaoshu", "Dashu", "Liqiu", "Chushu", "Bailu", "Qiufen", "Hanlu", "Shuangjiang",
         "Lidong", "Xiaoxue", "Daxue", "Dongzhi", "Xiaohan", "Dahan"]
# sidereal longitudes (Lahiri), near-constant by construction of a sidereal zodiac
STARS = {"Regulus": 149.8, "Spica": 180.0, "Aldebaran": 39.7, "Antares": 224.1,
         "Algol": 26.2, "Sirius": 104.1, "Fomalhaut": 333.6}
ASPECTS = [("conj", 0, 8), ("opp", 180, 8), ("trine", 120, 7), ("square", 90, 7), ("sext", 60, 5)]
KENDRA = {0, 3, 6, 9}


def _jdn(y, m, d):
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _dsum(n):
    s = 0
    while n:
        s += n % 10; n //= 10
    return s


def _red1(n):
    while n > 9:
        n = _dsum(n)
    return n


def ayanamsa(year):
    """Lahiri, linear enough over our span: ~23.85 deg at 2000, drifting 50.29 arcsec a year"""
    return 23.85 + (year - 2000.0) * (50.29 / 3600.0)


def _cats(vals, prefix, names, cols, ms):
    vals = np.asarray(vals)
    for v in pd.unique(vals):
        c = (vals == v).astype(np.float32)
        if c.sum() >= ms:
            cols.append(c); names.append(f"{prefix}={v}")


def _flag(cols, names, arr, nm, ms):
    c = np.asarray(arr).astype(np.float32)
    if c.sum() >= ms and c.sum() <= len(c) - ms:
        cols.append(c); names.append(nm)


def divisional(lon, n):
    """generic Dn: sign index of the nth division"""
    s = (lon // 30).astype(int) % 12
    part = ((lon % 30) / (30.0 / n)).astype(int)
    if n == 3:
        return (s + part * 4) % 12
    if n == 7:
        return np.where(s % 2 == 0, (s + part) % 12, (s + 6 + part) % 12)
    if n == 12:
        return (s + part) % 12
    return (s + part) % 12


def build(df, Z, split, exclude=frozenset(), min_support=40):
    n = len(df); ms = min_support
    A = Z[f"theta_a_{split}"]; B = Z[f"theta_b_{split}"]
    ya = pd.to_numeric(df.dob_a.str[:4]).to_numpy(int); ma = pd.to_numeric(df.dob_a.str[5:7]).to_numpy(int)
    da = pd.to_numeric(df.dob_a.str[8:10]).to_numpy(int)
    yb = pd.to_numeric(df.dob_b.str[:4]).to_numpy(int); mb = pd.to_numeric(df.dob_b.str[5:7]).to_numpy(int)
    db = pd.to_numeric(df.dob_b.str[8:10]).to_numpy(int)
    cols, names = [], []
    fin = np.isfinite(A[:, BI["moon"]]) & np.isfinite(B[:, BI["moon"]])

    # ---------- CHANDRA LAGNA and SURYA LAGNA cross-placements ----------
    for lag in ("moon", "sun"):
        tag = "chandra" if lag == "moon" else "surya"
        la = (A[:, BI[lag]] // 30).astype(int) % 12
        lb = (B[:, BI[lag]] // 30).astype(int) % 12
        for p in PLANETS:
            sa = (A[:, BI[p]] // 30).astype(int) % 12
            sb = (B[:, BI[p]] // 30).astype(int) % 12
            ok = np.isfinite(A[:, BI[p]]) & np.isfinite(B[:, BI[lag]])
            h_ab = ((sa - lb) % 12) + 1          # his planet in HER lagna houses
            h_ba = ((sb - la) % 12) + 1          # her planet in HIS lagna houses
            _cats([f"{v}" if o else "na" for v, o in zip(h_ab, ok)],
                  f"his_{p}_in_her_{tag}_house", names, cols, ms)
            _cats([f"{v}" if o else "na" for v, o in zip(h_ba, ok)],
                  f"her_{p}_in_his_{tag}_house", names, cols, ms)
            _flag(cols, names, np.isin(h_ab - 1, list(KENDRA)) & ok,
                  f"his_{p}_kendra_from_her_{tag}", ms)
            _flag(cols, names, ((h_ab == 7) & ok), f"his_{p}_in_her_7th_{tag}", ms)
            _flag(cols, names, ((h_ba == 7) & ok), f"her_{p}_in_his_7th_{tag}", ms)

    # ---------- NINE STAR KI ----------
    def nsk(y, m, d):
        yy = y if (m > 2 or (m == 2 and d >= 4)) else y - 1     # the year turns at Lichun
        s = 11 - _red1(_dsum(yy))
        if s > 9:
            s -= 9
        if s == 0:
            s = 9
        return s
    na = np.array([nsk(y, m, d) for y, m, d in zip(ya, ma, da)])
    nb = np.array([nsk(y, m, d) for y, m, d in zip(yb, mb, db)])
    _cats([f"{i}x{j}" for i, j in zip(na, nb)], "ninestarpair", names, cols, ms)
    _flag(cols, names, na == nb, "ninestar_same", ms)
    ea = np.array([NSK_EL[i - 1] for i in na]); eb = np.array([NSK_EL[i - 1] for i in nb])
    _cats([f"{i}x{j}" for i, j in zip(ea, eb)], "ninestar_elempair", names, cols, ms)
    order = {"Wood": 0, "Fire": 1, "Earth": 2, "Metal": 3, "Water": 4}
    oa = np.array([order[x] for x in ea]); ob = np.array([order[x] for x in eb])
    _flag(cols, names, ((oa + 1) % 5) == ob, "ninestar_he_produces_her", ms)
    _flag(cols, names, ((ob + 1) % 5) == oa, "ninestar_she_produces_him", ms)
    _flag(cols, names, ((oa + 2) % 5) == ob, "ninestar_he_controls_her", ms)
    _flag(cols, names, ((ob + 2) % 5) == oa, "ninestar_she_controls_him", ms)
    _flag(cols, names, oa == ob, "ninestar_same_element", ms)

    # ---------- TIBETAN MEWA and PARKHA ----------
    mwa = ((ya - 1927) % 9); mwb = ((yb - 1927) % 9)
    _cats([f"{i+1}x{j+1}" for i, j in zip(mwa, mwb)], "mewapair", names, cols, ms)
    _flag(cols, names, mwa == mwb, "mewa_same", ms)
    pka = ((ya - 1927) % 8); pkb = ((yb - 1927) % 8)
    _cats([f"{TRIGRAM[i]}x{TRIGRAM[j]}" for i, j in zip(pka, pkb)], "parkhapair", names, cols, ms)
    _flag(cols, names, pka == pkb, "parkha_same", ms)

    # ---------- 24 SOLAR TERMS (jieqi) ----------
    tra = (A[:, BI["sun"]] + ayanamsa(ya)) % 360.0
    trb = (B[:, BI["sun"]] + ayanamsa(yb)) % 360.0
    ja = np.floor(((tra - 315.0) % 360.0) / 15.0).astype(int) % 24
    jb = np.floor(((trb - 315.0) % 360.0) / 15.0).astype(int) % 24
    okj = np.isfinite(tra) & np.isfinite(trb)
    _cats([f"{JIEQI[i]}x{JIEQI[j]}" if o else "na" for i, j, o in zip(ja, jb, okj)],
          "jieqipair", names, cols, ms)
    _flag(cols, names, (ja == jb) & okj, "jieqi_same", ms)
    _flag(cols, names, (((ja - jb) % 24) == 12) & okj, "jieqi_opposite", ms)

    # ---------- DIVISIONAL CHARTS D3, D7, D12 ----------
    for dv, nm in ((3, "d3"), (7, "d7"), (12, "d12")):
        for p in ("moon", "venus", "jupiter"):
            la_ = A[:, BI[p]]; lb_ = B[:, BI[p]]
            ok = np.isfinite(la_) & np.isfinite(lb_)
            xa = divisional(np.nan_to_num(la_, nan=0.0), dv)
            xb = divisional(np.nan_to_num(lb_, nan=0.0), dv)
            _cats([f"{SIGNS[i]}x{SIGNS[j]}" if o else "na" for i, j, o in zip(xa, xb, ok)],
                  f"{nm}_{p}pair", names, cols, ms)
            _flag(cols, names, (xa == xb) & ok, f"{nm}_{p}_same_sign", ms)
            _flag(cols, names, (((xa - xb) % 12) == 6) & ok, f"{nm}_{p}_opposite", ms)

    # ---------- NAMED VEDIC YOGAS ----------
    def yogas(P):
        s = {p: (P[:, BI[p]] // 30).astype(int) % 12 for p in
             ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn")}
        gk = np.isin((s["jupiter"] - s["moon"]) % 12, list(KENDRA))
        cm = ((s["moon"] - s["mars"]) % 12 == 0) | ((s["moon"] - s["mars"]) % 12 == 6)
        ba = (s["sun"] - s["mercury"]) % 12 == 0
        rah = P[:, BI["true_node"]]
        span = np.array([((P[i, [BI[p] for p in ("sun", "moon", "mercury", "venus", "mars",
                                                 "jupiter", "saturn")]] - rah[i]) % 360).max()
                         if np.isfinite(rah[i]) else np.nan for i in range(len(P))])
        ks = np.where(np.isfinite(span), span <= 180.0, False)
        return gk, cm, ba, ks
    ga_, ca_, ba_, ka_ = yogas(A)
    gb_, cb_, bb_, kb_ = yogas(B)
    for nm, xa, xb in (("gajakesari", ga_, gb_), ("chandramangala", ca_, cb_),
                       ("budhaaditya", ba_, bb_), ("kalasarpa", ka_, kb_)):
        _flag(cols, names, xa & xb, f"{nm}_both", ms)
        _flag(cols, names, xa ^ xb, f"{nm}_one", ms)
        _flag(cols, names, ~xa & ~xb, f"{nm}_neither", ms)

    # ---------- FIXED STARS ----------
    for sn, sl in STARS.items():
        for p in ("sun", "moon", "venus", "mars"):
            ca = np.abs(((A[:, BI[p]] - sl + 180) % 360) - 180) <= 2.0
            cb = np.abs(((B[:, BI[p]] - sl + 180) % 360) - 180) <= 2.0
            _flag(cols, names, np.nan_to_num(ca) & np.nan_to_num(cb), f"star_{sn}_{p}_both", ms)
            _flag(cols, names, np.nan_to_num(ca) ^ np.nan_to_num(cb), f"star_{sn}_{p}_one", ms)

    # ---------- ARABIC LUNAR MANSIONS (28) ----------
    mza = np.floor(A[:, BI["moon"]] / (360.0 / 28.0)).astype(int) % 28
    mzb = np.floor(B[:, BI["moon"]] / (360.0 / 28.0)).astype(int) % 28
    _cats([f"{i}x{j}" if o else "na" for i, j, o in zip(mza, mzb, fin)], "manzilpair", names, cols, ms)
    _flag(cols, names, (mza == mzb) & fin, "manzil_same", ms)

    # ---------- HARMONICS 4, 6, 8, 12 ----------
    for h in (4, 6, 8, 12):
        Ah, Bh = (A * h) % 360.0, (B * h) % 360.0
        for x in ("sun", "moon", "venus", "mars", "jupiter"):
            for y_ in ("sun", "moon", "venus", "mars", "jupiter"):
                d = np.abs(((Ah[:, BI[x]] - Bh[:, BI[y_]] + 180) % 360) - 180)
                for an, ang, orb in ASPECTS[:2]:
                    c = (np.abs(d - ang) <= orb).astype(np.float32); c[~np.isfinite(d)] = 0.0
                    if ms <= c.sum() <= len(c) - ms:
                        cols.append(c); names.append(f"h{h}_his_{x}_{an}_her_{y_}")

    # ---------- SOLAR ARC DIRECTIONS (a degree for a year) ----------
    jda = np.array([_jdn(y, m, d) for y, m, d in zip(ya, ma, da)])
    jdb = np.array([_jdn(y, m, d) for y, m, d in zip(yb, mb, db)])
    gap = (jdb - jda) / 365.2422
    for src, dst, tag in ((A, B, "sa_his"), (B, A, "sa_her")):
        g = gap if tag == "sa_his" else -gap
        for x in ("sun", "venus", "mars"):
            arc = (src[:, BI[x]] + g) % 360.0
            for y_ in ("sun", "moon", "venus", "mars"):
                d = np.abs(((arc - dst[:, BI[y_]] + 180) % 360) - 180)
                for an, ang, orb in ASPECTS[:2]:
                    c = (np.abs(d - ang) <= orb).astype(np.float32); c[~np.isfinite(d)] = 0.0
                    if ms <= c.sum() <= len(c) - ms:
                        cols.append(c); names.append(f"{tag}_{x}_{an}_{y_}")

    # ---------- CRITICAL AND ANARETIC DEGREES ----------
    def critical(P, p):
        lon = P[:, BI[p]]; s = (lon // 30).astype(int) % 12; deg = lon % 30
        card = np.isin(s, [0, 3, 6, 9]) & (np.isclose(np.round(deg), 0, atol=1) |
                                           (np.abs(deg - 13) <= 1) | (np.abs(deg - 26) <= 1))
        fix = np.isin(s, [1, 4, 7, 10]) & ((np.abs(deg - 8.5) <= 1.5) | (np.abs(deg - 21.5) <= 1.5))
        mut = np.isin(s, [2, 5, 8, 11]) & ((np.abs(deg - 4) <= 1) | (np.abs(deg - 17) <= 1))
        return np.nan_to_num(card | fix | mut), np.nan_to_num(deg >= 29.0)
    for p in ("sun", "moon", "venus", "mars"):
        ca, aa = critical(A, p); cb, ab = critical(B, p)
        _flag(cols, names, ca & cb, f"critdeg_{p}_both", ms)
        _flag(cols, names, ca ^ cb, f"critdeg_{p}_one", ms)
        _flag(cols, names, aa & ab, f"anaretic_{p}_both", ms)
        _flag(cols, names, aa ^ ab, f"anaretic_{p}_one", ms)

    # ---------- CONTRA-ANTISCIA (mirror across the equinoctial axis) ----------
    ca_ = (360.0 - A) % 360.0
    for x in ("sun", "moon", "venus", "mars"):
        for y_ in ("sun", "moon", "venus", "mars"):
            d = np.abs(((ca_[:, BI[x]] - B[:, BI[y_]] + 180) % 360) - 180)
            for an, ang, orb in ASPECTS[:1]:
                c = (np.abs(d - ang) <= orb).astype(np.float32); c[~np.isfinite(d)] = 0.0
                if ms <= c.sum() <= len(c) - ms:
                    cols.append(c); names.append(f"contrantiscia_his_{x}_{an}_her_{y_}")

    # ---------- COMPOSITE AND DAVISON MOON PHASE ----------
    def midlon(x, y_):
        d = ((y_ - x + 180) % 360) - 180
        return (x + d / 2.0) % 360.0
    csun = midlon(A[:, BI["sun"]], B[:, BI["sun"]])
    cmoon = midlon(A[:, BI["moon"]], B[:, BI["moon"]])
    cph = np.floor(((cmoon - csun) % 360.0) / 45.0).astype(int) % 8
    PH = ["New", "Crescent", "FirstQtr", "Gibbous", "Full", "Disseminating", "LastQtr", "Balsamic"]
    _cats([PH[i] if o else "na" for i, o in zip(cph, fin)], "composite_moonphase", names, cols, ms)

    # ---------- HIJRI CALENDAR DATE ----------
    def hijri(jd):
        d = jd - 1948439.5
        yr = int(d // 354.36707) + 1
        rem = d - (yr - 1) * 354.36707
        mo = min(12, int(rem // 29.530589) + 1)
        return yr, mo
    ha = np.array([hijri(j)[1] for j in jda]); hb = np.array([hijri(j)[1] for j in jdb])
    _cats([f"{i}x{j}" for i, j in zip(ha, hb)], "hijrimonthpair", names, cols, ms)
    _flag(cols, names, ha == hb, "hijrimonth_same", ms)

    keep = [i for i, nm in enumerate(names) if nm not in exclude]
    X = np.column_stack([cols[i] for i in keep]).astype(np.float32) if keep else np.zeros((n, 0), np.float32)
    return X, [names[i] for i in keep]
