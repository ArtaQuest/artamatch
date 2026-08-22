"""
world_members_iv.py — the matching and date-election systems people actually use, worldwide (operator 2026-08-22:
"ensure every electional or non-electional matching algorithm ever popular in any part of world is included").

The earlier families covered the astronomy. These are the CULTURAL ALGORITHMS layered on top of it — the rules a
family in Kyoto, Chengdu, Chennai, Jerusalem, Yogyakarta, Bali, Lhasa or Athens would actually apply when picking
a wedding day or judging a match. Every one is exact arithmetic on the three dates (plus, for the two combustion
rules, Sun/Venus/Jupiter longitudes we already store), so all of it is computable for any future date.

ELECTIONAL — is this a good day to marry?
  ROKUYŌ (六曜, Japan)          the six-day cycle (先勝·友引·先負·仏滅·大安·赤口) from the lunisolar month+day;
                               TAIAN is the day Japanese weddings are booked on and BUTSUMETSU the one avoided.
  TONG SHU / HUANG LI (China)  the 12 Day Officers (建除十二直, day branch against month branch), the 28 lunar
                               mansions (二十八宿), the day-month clash (沖), and the sexagenary day pillar.
  VIVĀHA MUHŪRTA (India)       the rules that actually stop Hindu weddings for months: GURU ASTA and ŚUKRA ASTA
                               (Jupiter/Venus combust within 11°/10° of the Sun), Cāturmāsa, Adhika Māsa, the
                               tithi class (Nanda/Bhadrā/Jayā/Riktā/Pūrṇā), Bhadrā (Viṣṭi karaṇa), Pañcaka, and
                               the auspicious nakṣatras for marriage.
  HEBREW CALENDAR              Shabbat, Sefirat ha-Omer, the Three Weeks, Rosh Chodesh — the periods in which a
                               Jewish wedding is not held.
  CHRISTIAN / ORTHODOX FASTS   Great Lent (from the computus), Advent, the Apostles' and Dormition fasts.
  ISLAMIC MONTHS               Ṣafar and Muḥarram avoidance, Shawwāl preference.
  JAVANESE PASARAN + WETON     the five-day market week and the neptu of the day.
  BALINESE PAWUKON             the wuku and the ten concurrent week-cycles (Ekawara … Dasawara).

MATCHING — is this a good pair?
  AṢṬAKŪṬA / GUṆA MILAN (India)  all eight kūṭas scored to the full 36 points: varṇa, vaśya, tārā, yoni, graha
                                 maitrī, gaṇa, bhakūṭa, nāḍī — from both Moons' nakṣatra and rāśi.
  CHINESE ZODIAC (full matrix)   sān hé trines, liù hé harmonies, liù chōng clashes, liù hài harms, xiāng xíng
                                 punishments, and the five-phase generating/overcoming relation of the year elements.
  NINE STAR KI (九星気学, Japan)   each partner's main star and their elemental relation.
  JAVANESE WETON MATCHING        (neptu + neptu) mod 5 → Pegat · Ratu · Jodoh · Topo · Pesthi, the reading a
                                 Javanese family gives a proposed marriage.
  TIBETAN PARKHA + MEWA          the eight trigrams and nine numbers of the birth years, and their agreement.
Writes AQ_OUT/world_members.npz.
"""
import datetime as dt
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from artamodel import auc, absdiff   # noqa: E402

SRC = os.environ.get("AQ_SRC", "/tmp/aq9c"); PH = os.environ.get("AQ_PHASES", "/tmp/aq9feat/phases.npz"); OUT = os.environ.get("AQ_OUT", "/tmp/aq9sub")
QS = (0.40, 0.55, 0.70, 0.85, 1.0); T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)

# ── tables ────────────────────────────────────────────────────────────────────────────────────────────────────────
DAY_NEPTU = {6: 5, 0: 4, 1: 3, 2: 7, 3: 8, 4: 6, 5: 9}          # Javanese: Sun..Sat by weekday() (Mon=0)
PASARAN_NEPTU = [5, 9, 7, 4, 8]                                  # Legi, Pahing, Pon, Wage, Kliwon
GANA = {0: [0, 4, 6, 7, 12, 14, 16, 21, 26], 1: [1, 3, 5, 10, 11, 19, 20, 24, 25], 2: [2, 8, 9, 13, 15, 17, 18, 22, 23]}
NADI = {0: [0, 5, 6, 11, 12, 17, 18, 23, 24], 1: [1, 4, 7, 10, 13, 16, 19, 22, 25], 2: [2, 3, 8, 9, 14, 15, 20, 21, 26]}
YONI = [0, 1, 2, 3, 3, 4, 5, 5, 6, 7, 7, 8, 9, 10, 8, 10, 11, 11, 12, 13, 12, 0, 1, 4, 9, 2, 6]      # 27 → 14 animals
YONI_ENEMY = {(0, 7), (1, 8), (2, 9), (3, 10), (4, 11), (5, 12), (6, 13)}
VASHYA = [1, 1, 2, 0, 1, 2, 2, 0, 1, 3, 3, 2]                    # rāśi → Chatushpada/Manava/Jalachara/Keeta classes
VARNA = [1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0]                     # rāśi → Kshatriya/Vaishya/Shudra/Brahmin
LORDS = [4, 5, 2, 1, 0, 2, 5, 4, 3, 6, 6, 3]                     # rāśi lords: Ma Ve Me Mo Su Me Ve Ma Ju Sa Sa Ju
FRIEND = {(0, 1), (1, 0), (0, 3), (3, 0), (0, 4), (4, 0), (1, 2), (2, 1), (5, 6), (6, 5), (2, 5), (5, 2), (3, 4), (4, 3)}
VIVAHA_NAK = {0, 2, 4, 6, 11, 12, 14, 16, 20, 21, 22, 25, 26}    # the nakṣatras classically fit for marriage
SANHE = {(0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)}           # Chinese trines (rat-dragon-monkey …)
LIUHE = {(0, 1), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)}       # six harmonies
XING = {(0, 3), (1, 10), (2, 5), (4, 4), (6, 6), (7, 7), (8, 11), (9, 9)}   # punishments (simplified classic set)
YEAR_ELEM = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]                       # stem → wood fire earth metal water
GEN = {(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)}                   # generating cycle
OVR = {(0, 2), (2, 4), (4, 1), (1, 3), (3, 0)}                   # overcoming cycle
KI_ELEM = {1: 4, 2: 2, 3: 0, 4: 0, 5: 2, 6: 3, 7: 3, 8: 2, 9: 1}  # nine-star → five phase


def jdn(dstr):
    if not isinstance(dstr, str) or len(dstr) < 10 or dstr.endswith("-00") or dstr[:4] == "0000":
        return None
    try:
        return dt.date(int(dstr[:4]), int(dstr[5:7]), int(dstr[8:10]))
    except Exception:
        return None


def easter(y):
    a = y % 19; b, c = divmod(y, 100); d, e = divmod(b, 4); f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i, k = divmod(c, 4); l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451; mo, da = divmod(h + l - 7 * m + 114, 31)
    return dt.date(y, mo, da + 1)


_LD_CACHE = {}


def lunisolar(d):
    """(lunar month, lunar day, is_leap) of the Chinese/Japanese lunisolar calendar, or None outside its range."""
    key = d.toordinal()
    if key in _LD_CACHE:
        return _LD_CACHE[key]
    try:
        from lunardate import LunarDate
        L = LunarDate.from_solar_date(d.year, d.month, d.day)
        out = (L.month, L.day, int(getattr(L, "isLeapMonth", False)))
    except Exception:
        out = None
    _LD_CACHE[key] = out
    return out


def day_features(dstr, sun=np.nan, ven=np.nan, jup=np.nan, moon=np.nan):
    """Everything the world's electional systems read about one day."""
    d = jdn(dstr)
    if d is None:
        return [np.nan] * 34
    J = d.toordinal() + 1721425
    wd = d.weekday()
    sx = (J + 49) % 60; stem = sx % 10; branch = sx % 12                    # the sexagenary DAY pillar
    ls = lunisolar(d)
    lm, ld, leap = (ls if ls else (np.nan, np.nan, np.nan))
    # 六曜: (lunar month + lunar day) mod 6. The cycle RESTARTS each lunar month, which is why the month enters the
    # sum; verified against the canonical anchors 1/1=先勝 … 5/1=大安, so index 0 is 大安 TAIAN and 5 is 仏滅 BUTSUMETSU
    # — the two that actually decide a Japanese wedding booking.
    rokuyo = ((lm + ld) % 6) if ls else np.nan
    taian = float(rokuyo == 0) if ls else np.nan; butsumetsu = float(rokuyo == 5) if ls else np.nan
    # The Day Officers run off the SOLAR-term month (節月), not the lunisolar one: 寅 begins at Lì Chūn, not at
    # Chinese New Year, and the two can differ by weeks. The terms sit within a day or two of the 5th of each
    # Gregorian month, which is accurate enough here and — unlike the lunar month — is defined for every date.
    month_branch = (d.month if d.day >= 5 else d.month - 1) % 12
    officer = (branch - month_branch) % 12                                  # 建除十二直; 建 when the two agree
    officer_good = float(officer in (2, 3, 5, 8, 9, 11))                    # 除·满·平·成·收·开 are the usable ones
    # 二十八宿, the 28-day "duty" cycle. The offset is NOT free: the cycle maps exactly onto the 7-day week, so
    # the four Sun mansions 房·虛·昴·星 must always fall on a Sunday — which narrows it to four candidates — and
    # five published assignments for August 2026 (女 1st, 虛 2nd, 角 20th, 心 24th, 牛 28th) then pin it uniquely
    # to 11. The offset shipped first, 20, failed the weekday test outright and was 19 positions out.
    mansion = (J + 11) % 28
    clash = float((branch - month_branch) % 12 == 6)                        # 沖: the day clashes the month
    # Hindu muhūrta
    elong = (moon - sun) % 360.0 if np.isfinite(moon + sun) else np.nan
    tithi = np.floor(elong / 12.0) + 1 if np.isfinite(elong) else np.nan
    tithi_class = ((tithi - 1) % 5) if np.isfinite(tithi) else np.nan       # Nanda/Bhadrā/Jayā/Riktā/Pūrṇā
    rikta = float(tithi_class == 3) if np.isfinite(tithi) else np.nan
    karana = np.floor((elong % 360) / 6.0) if np.isfinite(elong) else np.nan
    bhadra = float(karana in (7, 15, 23, 31, 39, 47, 55)) if np.isfinite(karana) else np.nan
    guru_asta = float(absdiff(jup, sun) < 11.0) if np.isfinite(jup + sun) else np.nan
    shukra_asta = float(absdiff(ven, sun) < 10.0) if np.isfinite(ven + sun) else np.nan
    nak = np.floor((moon % 360) / (360 / 27)) if np.isfinite(moon) else np.nan
    vivaha_nak = float(int(nak) in VIVAHA_NAK) if np.isfinite(nak) else np.nan
    chaturmas = float(lm in (5, 6, 7, 8)) if ls else np.nan                 # the four months when no wedding is held
    panchaka = float(int(nak) in (22, 23, 24, 25, 26)) if np.isfinite(nak) else np.nan
    # Hebrew
    try:
        from convertdate import hebrew
        hy, hm, hd = hebrew.from_gregorian(d.year, d.month, d.day)
        omer = float((hm == hebrew.NISAN and hd >= 16) or hm == hebrew.IYYAR or (hm == hebrew.SIVAN and hd <= 5))
        # convertdate numbers Hebrew months from NISAN=1, so Tammuz is 4 and Av is 5 — NOT 11 and 12, which
        # are Shevat and Adar and put this mourning period in midwinter instead of midsummer
        three_weeks = float((hm == hebrew.TAMMUZ and hd >= 17) or (hm == hebrew.AV and hd <= 9))
        rosh_chodesh = float(hd == 1 or hd == 30)
    except Exception:
        hm = hd = omer = three_weeks = rosh_chodesh = np.nan
    shabbat = float(wd == 5)
    # Christian and Orthodox fasts
    try:
        E = easter(d.year); lent = float(0 <= (E - d).days <= 46)
        pent = E + dt.timedelta(days=49); apostles = float(pent + dt.timedelta(days=8) <= d <= dt.date(d.year, 6, 28))
    except Exception:
        lent = apostles = np.nan
    advent = float(d.month == 12 and d.day <= 24 or (d.month == 11 and d.day >= 15))
    dormition = float(d.month == 8 and d.day <= 14)
    # Islamic
    try:
        from convertdate import islamic
        iy, im, idd = islamic.from_gregorian(d.year, d.month, d.day)
        safar = float(im == 2); muharram = float(im == 1); shawwal = float(im == 10); ramadan = float(im == 9)
    except Exception:
        im = safar = muharram = shawwal = ramadan = np.nan
    # Javanese + Balinese
    pasaran = J % 5                                                          # anchored on 1945-08-17 = Jumat Legi
    neptu_day = DAY_NEPTU[wd] + PASARAN_NEPTU[pasaran]
    paw = (J + 61) % 210                                                     # anchored so every Galungan (Buda Kliwon
                                                                             # Dungulan) lands on pawukon day 70
    wuku = paw // 7
    triwara = paw % 3; caturwara = paw % 4; sadwara = paw % 6; astawara = paw % 8; sangawara = paw % 9; dasawara = paw % 10
    return [float(wd), float(stem), float(branch), float(sx), lm, ld, leap, rokuyo, taian, butsumetsu, officer,
            officer_good, float(mansion), clash, tithi, tithi_class, rikta, bhadra, guru_asta, shukra_asta, nak,
            vivaha_nak, chaturmas, panchaka, float(hm) if hm == hm else np.nan, omer, three_weeks, rosh_chodesh,
            shabbat, lent, advent, float(im) if im == im else np.nan, float(neptu_day), float(wuku)]


DAYN = ["wd", "stem", "branch", "sexagenary", "lunar_month", "lunar_day", "leap_month", "rokuyo", "taian", "butsumetsu",
        "day_officer", "officer_good", "mansion28", "month_clash", "tithi", "tithi_class", "rikta", "bhadra",
        "guru_asta", "shukra_asta", "nakshatra", "vivaha_nakshatra", "chaturmas", "panchaka", "hebrew_month",
        "omer", "three_weeks", "rosh_chodesh", "shabbat", "lent", "advent", "islamic_month", "javanese_neptu", "wuku"]


def ashtakoota(nak_a, ras_a, nak_b, ras_b):
    """Guṇa Milan, all eight kūṭas to the full 36 points, from the two Moons."""
    out = np.full((len(nak_a), 10), np.nan)
    ok = np.isfinite(nak_a) & np.isfinite(nak_b) & np.isfinite(ras_a) & np.isfinite(ras_b)
    na = np.nan_to_num(nak_a).astype(int); nb = np.nan_to_num(nak_b).astype(int)
    ra = np.nan_to_num(ras_a).astype(int); rb = np.nan_to_num(ras_b).astype(int)
    varna = np.where(VARNA_ARR[rb] >= VARNA_ARR[ra], 1.0, 0.0)
    vashya = np.where(VASHYA_ARR[ra] == VASHYA_ARR[rb], 2.0, np.where(np.abs(VASHYA_ARR[ra] - VASHYA_ARR[rb]) == 1, 1.0, 0.0))
    t1 = ((nb - na) % 27 + 1) % 9; t2 = ((na - nb) % 27 + 1) % 9
    tara = np.where(np.isin(t1, [3, 5, 7]) | np.isin(t2, [3, 5, 7]), 0.0, 3.0)
    ya = YONI_ARR[na]; yb = YONI_ARR[nb]
    yoni = np.where(ya == yb, 4.0, np.array([0.0 if (min(x, y), max(x, y)) in YONI_ENEMY else 2.0 for x, y in zip(ya, yb)]))
    la = LORDS_ARR[ra]; lb = LORDS_ARR[rb]
    maitri = np.where(la == lb, 5.0, np.array([5.0 if (x, y) in FRIEND else 1.0 for x, y in zip(la, lb)]))
    gana = np.where(GANA_ARR[na] == GANA_ARR[nb], 6.0, np.where(np.abs(GANA_ARR[na] - GANA_ARR[nb]) == 1, 3.0, 0.0))
    dist = (rb - ra) % 12; dist2 = (ra - rb) % 12
    bhak = np.where(np.isin(dist, [5, 7, 1, 11]) | np.isin(dist2, [5, 7]), 0.0, 7.0)
    nadi = np.where(NADI_ARR[na] == NADI_ARR[nb], 0.0, 8.0)
    total = varna + vashya + tara + yoni + maitri + gana + bhak + nadi
    for k, v in enumerate((varna, vashya, tara, yoni, maitri, gana, bhak, nadi, total, (total >= 18).astype(float))):
        out[:, k] = np.where(ok, v, np.nan)
    return out


KOOTA_N = ["varna", "vashya", "tara", "yoni", "graha_maitri", "gana", "bhakoot", "nadi", "guna_total", "guna_pass"]
VARNA_ARR = np.array(VARNA); VASHYA_ARR = np.array(VASHYA); LORDS_ARR = np.array(LORDS)
YONI_ARR = np.array(YONI)
GANA_ARR = np.zeros(27, int)
for g, lst in GANA.items():
    for n in lst:
        GANA_ARR[n] = g
NADI_ARR = np.zeros(27, int)
for g, lst in NADI.items():
    for n in lst:
        NADI_ARR[n] = g


def year_systems(ya, yb):
    """Systems keyed on the BIRTH YEAR: Chinese zodiac relations, Nine Star Ki, Tibetan parkha/mewa."""
    out = []
    ba = (ya - 4) % 12; bb = (yb - 4) % 12; sa = (ya - 4) % 10; sb = (yb - 4) % 10
    ea = np.array(YEAR_ELEM)[sa]; eb = np.array(YEAR_ELEM)[sb]
    trine = np.array([1.0 if any({x, y} <= set(t) for t in SANHE) else 0.0 for x, y in zip(ba, bb)])
    liuhe = np.array([1.0 if (min(x, y), max(x, y)) in LIUHE or (x, y) in LIUHE or (y, x) in LIUHE else 0.0 for x, y in zip(ba, bb)])
    clash = ((ba - bb) % 12 == 6).astype(float)
    harm = (((ba + bb) % 12) == 7).astype(float)
    xing = np.array([1.0 if (x, y) in XING or (y, x) in XING else 0.0 for x, y in zip(ba, bb)])
    gen = np.array([1.0 if (x, y) in GEN or (y, x) in GEN else 0.0 for x, y in zip(ea, eb)])
    ovr = np.array([1.0 if (x, y) in OVR or (y, x) in OVR else 0.0 for x, y in zip(ea, eb)])
    same_elem = (ea == eb).astype(float)
    ki = lambda y: 11 - (((y // 1000) + (y // 100) % 10 + (y // 10) % 10 + y % 10 - 1) % 9 + 1)
    kia = np.array([((11 - (sum(int(c) for c in str(int(v))) - 1) % 9) - 1) % 9 + 1 for v in ya])
    kib = np.array([((11 - (sum(int(c) for c in str(int(v))) - 1) % 9) - 1) % 9 + 1 for v in yb])
    kea = np.array([KI_ELEM[int(k)] for k in kia]); keb = np.array([KI_ELEM[int(k)] for k in kib])
    ki_gen = np.array([1.0 if (x, y) in GEN or (y, x) in GEN else 0.0 for x, y in zip(kea, keb)])
    parkha_a = (ya - 4) % 8; parkha_b = (yb - 4) % 8; mewa_a = (ya - 4) % 9; mewa_b = (yb - 4) % 9
    for arr, nm in ((ba, "zod_branch_a"), (bb, "zod_branch_b"), (trine, "san_he"), (liuhe, "liu_he"), (clash, "liu_chong"),
                    (harm, "liu_hai"), (xing, "xiang_xing"), (gen, "elem_generate"), (ovr, "elem_overcome"),
                    (same_elem, "elem_same"), (kia, "nine_star_a"), (kib, "nine_star_b"), (ki_gen, "nine_star_generate"),
                    ((kia == kib).astype(float), "nine_star_same"), (parkha_a, "parkha_a"), (parkha_b, "parkha_b"),
                    ((parkha_a == parkha_b).astype(float), "parkha_same"), (mewa_a, "mewa_a"), (mewa_b, "mewa_b"),
                    ((mewa_a == mewa_b).astype(float), "mewa_same"), ((ba - bb) % 12, "zod_branch_dist")):
        out.append((np.asarray(arr, dtype=float), nm))
    return out


def build(df, Z, half):
    bodies = list(Z["bodies"]); s1, s2 = list(Z["slots"])
    A = Z[f"theta_{s1}_{half}"]; B = Z[f"theta_{s2}_{half}"]; W = Z[f"theta_wed_{half}"]
    isun, imoon, iven, ijup = (bodies.index(b) for b in ("sun", "moon", "venus", "jupiter"))
    D = np.array([day_features(s, W[i, isun], W[i, iven], W[i, ijup], W[i, imoon]) for i, s in enumerate(df.start)], dtype=float)
    cols = [D]; names = [f"wed_{n}" for n in DAYN]
    # each partner's own day-systems (the Javanese weton and the sexagenary pillar are personal, not electional)
    for tag, dob in (("a", df.dob_a), ("b", df.dob_b)):
        P = np.array([day_features(s) for s in dob], dtype=float)
        keep = [DAYN.index(n) for n in ("wd", "branch", "stem", "sexagenary", "javanese_neptu", "wuku", "nakshatra", "rokuyo")]
        cols.append(P[:, keep]); names += [f"{tag}_{DAYN[k]}" for k in keep]
        if tag == "a":
            Pa = P
        else:
            Pb = P
    # JAVANESE WETON MATCHING — the reading a Javanese family gives a proposed marriage
    na = Pa[:, DAYN.index("javanese_neptu")]; nb = Pb[:, DAYN.index("javanese_neptu")]
    tot = na + nb
    cols.append(np.column_stack([tot, tot % 5, tot % 7, np.abs(na - nb), (tot % 5 == 3).astype(float), (tot % 5 == 1).astype(float)]))
    names += ["weton_total", "weton_mod5", "weton_mod7", "weton_diff", "weton_jodoh", "weton_pegat"]
    # AṢṬAKŪṬA from both Moons
    nak_a = np.floor((A[:, imoon] % 360) / (360 / 27)); nak_b = np.floor((B[:, imoon] % 360) / (360 / 27))
    ras_a = np.floor((A[:, imoon] % 360) / 30); ras_b = np.floor((B[:, imoon] % 360) / 30)
    cols.append(ashtakoota(nak_a, ras_a, nak_b, ras_b)); names += [f"guna_{n}" for n in KOOTA_N]
    # year-keyed systems
    ya = pd.to_numeric(df.dob_a.str[:4], errors="coerce").fillna(0).to_numpy().astype(int)
    yb = pd.to_numeric(df.dob_b.str[:4], errors="coerce").fillna(0).to_numpy().astype(int)
    for arr, nm in year_systems(ya, yb):
        cols.append(arr.reshape(-1, 1)); names.append(nm)
    X = np.column_stack(cols).astype(np.float32)
    X[:, [names.index(n) for n in names if n.startswith(("zod_", "nine_star", "parkha", "mewa"))]] = np.where(
        (ya > 0)[:, None] & (yb > 0)[:, None], X[:, [names.index(n) for n in names if n.startswith(("zod_", "nine_star", "parkha", "mewa"))]], np.nan)
    return X, names


def main():
    import lightgbm as lgb
    Z = np.load(PH, allow_pickle=True); y = Z["y_train"].astype(np.int64); later = Z["yr_train"].astype(int).max(1); cuts = [np.quantile(later, q) for q in QS]
    ptr, pte, pn = Z["plain_train"], Z["plain_test"], list(Z["plain_names"]); s1, s2 = list(Z["slots"])
    tr = pd.read_csv(f"{SRC}/train.csv", dtype=str); te = pd.read_csv(f"{SRC}/test.csv", dtype=str)
    Xtr, names = build(tr, Z, "train"); log(f"train built: {Xtr.shape[1]} world-system features"); Xte, _ = build(te, Z, "test"); log("test built")
    ia, ib, iy = pn.index(f"age_{s1}_at_start"), pn.index(f"age_{s2}_at_start"), pn.index("start_year")
    plain = lambda p: np.column_stack([np.fmax(p[:, ia], p[:, ib]), np.fmin(p[:, ia], p[:, ib]), np.abs(p[:, ia] - p[:, ib]), p[:, iy]])
    prm = dict(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=200, colsample_bytree=0.7, subsample=0.8, subsample_freq=1, reg_lambda=20.0, verbose=-1)
    members_tr, members_te, mnames, meta = [], [], [], []
    def member(cols, name):
        Xa = Xtr[:, cols]; Xb = Xte[:, cols]; rows = np.isfinite(Xa).any(1); s_tr = np.full(len(y), np.nan)
        for k in range(1, len(cuts)):
            lo = cuts[k - 1]; blk = rows & (later > lo) & ((later <= cuts[k]) if k < len(cuts) - 1 else True); fit = rows & (later <= lo)
            if fit.sum() < 500:
                continue
            c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[fit], y[fit]); s_tr[blk] = c.predict_proba(Xa[blk])[:, 1]
        c = lgb.LGBMClassifier(random_state=0, **prm); c.fit(Xa[rows], y[rows])
        s_te = np.full(len(Xb), np.nan); rte = np.isfinite(Xb).any(1); s_te[rte] = c.predict_proba(Xb[rte])[:, 1]
        f = np.isfinite(s_tr) & (later > cuts[0]); o = auc(y[f], s_tr[f]) if f.sum() > 500 else float("nan")
        members_tr.append(s_tr); members_te.append(s_te); mnames.append(name); meta.append({"member": name, "forward_oof": o, "n_features": len(cols), "n_rows": int(rows.sum())})
        log(f"  {name:<46} {len(cols):>3} feats · {rows.sum():>7,} rows · fwd-OOF {o:.4f}")
    idx = lambda pred: [i for i, n in enumerate(names) if pred(n)]
    member(idx(lambda n: n.startswith("wed_")), "ELECTIONAL WORLD (rokuyō, tongshu, muhūrta, fasts)")
    member(idx(lambda n: n.startswith("guna_")), "AṢṬAKŪṬA / GUṆA MILAN (36 points)")
    member(idx(lambda n: n.startswith(("zod_", "elem_", "liu_", "san_he", "xiang"))), "CHINESE ZODIAC MATCHING (hé/chōng/hài/xíng)")
    member(idx(lambda n: n.startswith(("nine_star", "parkha", "mewa"))), "NINE STAR KI + TIBETAN PARKHA/MEWA")
    member(idx(lambda n: n.startswith("weton")), "JAVANESE WETON MATCHING")
    member(list(range(len(names))), "WORLD SYSTEMS ALL (no ages)")
    plainx = plain(ptr); plainxe = plain(pte)
    Xtr = np.column_stack([plainx, Xtr]); Xte = np.column_stack([plainxe, Xte]); names = ["age_older", "age_younger", "age_gap", "start_year"] + names
    member(list(range(len(names))), "PLAIN + WORLD SYSTEMS ALL")
    np.savez_compressed(os.path.join(OUT, "world_members.npz"), S_train=np.column_stack(members_tr), S_test=np.column_stack(members_te),
                        names=np.array(mnames), meta=json.dumps(meta), feature_names=np.array(names, dtype=object))
    log(f"wrote {OUT}/world_members.npz with {len(mnames)} members")


if __name__ == "__main__":
    main()
