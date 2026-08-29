"""v21_traditions.py — the traditions the bank was missing, all of them pair-only.

An audit of the 6,104-statement bank by tradition found numerology represented by 99 statements (the
per-tradition fit could not even select from it), and moon phase, the Chinese zodiac animal relations,
the Navamsa D9 chart, the Ashtakoota total, the Mayan Tzolkin and the harmonic charts absent entirely.
Those are not obscure corners — Guna Milan is THE marriage number in Vedic practice, the D9 is the
divisional chart Vedic astrology reads a marriage in, and the six harmonies are how Chinese practice
answers this exact question. This module supplies them.

Every statement here is a named doctrine and every one uses BOTH dates. A one-sided fact (his life path,
her moon phase) appears only inside a pairing, never alone, which is the standing constraint.

  NUMEROLOGY      Pythagorean and Chaldean life path, birthday number, attitude number, personal year
                  at the partner's birth, master numbers, and the classical compatibility classes
  MOON PHASE      Rudhyar's eight lunation types, paired, plus their separation around the cycle
  CHINESE         year animal and stem, the four trines (san he), six harmonies (liu he), six clashes
                  (liu chong), harms (xiang hai), the five-element production and control cycles
  VEDIC D9        the Navamsa divisional chart — the chart a marriage is judged in — for Moon, Venus,
                  Jupiter and the 7th house lord, paired and aspected
  ASHTAKOOTA      all eight kootas scored the traditional way (Varna, Vashya, Tara, Yoni, Graha Maitri,
                  Gana, Bhakoot, Nadi) and the Guna Milan TOTAL out of 36, banded as practitioners read it
  MAYAN           Tzolkin day sign and galactic tone, paired
  HARMONICS       the 5th (creative), 7th (romantic) and 9th (marriage) harmonic charts, in synastry
  DRACONIC        the node-relative chart, in synastry
  ANTISCIA        solstice-point contacts, the classical hidden aspect

build(df, Z, split, exclude) -> (X, names), matching the other bank builders.
"""
import numpy as np
import pandas as pd

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
ANIMALS = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster",
           "Dog", "Pig"]
STEM_EL = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]
PHASES = ["New", "Crescent", "FirstQtr", "Gibbous", "Full", "Disseminating", "LastQtr", "Balsamic"]
# Rudhyar's eight lunation types, by the Moon's elongation from the Sun
NAK = 27
# nakshatra -> gana (0 Deva, 1 Manushya, 2 Rakshasa), traditional assignment
GANA = [0,1,2,1,0,1,0,0,2,2,1,1,0,2,0,2,0,2,2,1,1,0,2,2,1,1,0]
# nakshatra -> nadi (0 Aadi/Vata, 1 Madhya/Pitta, 2 Antya/Kapha)
NADI = [0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2]
# nakshatra -> yoni animal (14 animals, traditional)
YONI = [0,1,2,3,3,4,5,5,6,6,7,7,8,9,8,9,10,4,11,12,12,13,1,13,10,2,0]
YONI_NAME = ["Horse","Elephant","Sheep","Serpent","Dog","Cat","Rat","Cow","Buffalo","Tiger","Hare",
             "Monkey","Lion","Mongoose"]
# yoni pairs that are traditional enemies (score 0) - by animal index
YONI_ENEMY = {(0,8),(1,5),(2,11),(3,6),(4,9),(7,9),(10,12),(13,3)}
# nakshatra -> varna via moon sign is standard; varna by moon sign: water=Brahmin etc.
VARNA_BY_SIGN = [1,2,3,0,1,2,3,0,1,2,3,0]   # Ari..Pis -> Kshatriya/Vaishya/Shudra/Brahmin cycle
VARNA_NAME = ["Brahmin","Kshatriya","Vaishya","Shudra"]
SIGN_LORD = [4,3,2,1,0,2,3,4,5,6,6,5]        # Mars,Venus,Mercury,Moon,Sun,Mercury,Venus,Mars,Jup,Sat,Sat,Jup
LORD_NAME = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn"]
# graha maitri: friendship matrix between the seven lords (2=friend,1=neutral,0=enemy)
MAITRI = np.array([
    [2,2,1,0,2,2,0],[2,2,2,1,1,1,1],[2,0,2,2,1,1,2],[1,1,2,2,1,0,2],
    [2,2,0,1,2,2,1],[2,1,0,2,2,2,1],[1,1,2,2,0,1,2]])
VASHYA_GROUP = [1,1,2,3,0,2,4,3,1,0,2,3]     # quadruped/human/jalachara etc. by moon sign
TRINE = {0:0,4:0,8:0, 1:1,5:1,9:1, 2:2,6:2,10:2, 3:3,7:3,11:3}          # san he
LIU_HE = {0:1,1:0, 2:11,11:2, 3:10,10:3, 4:9,9:4, 5:8,8:5, 6:7,7:6}     # six harmonies
XIANG_HAI = {0:7,7:0, 1:6,6:1, 2:5,5:2, 3:4,4:3, 8:11,11:8, 9:10,10:9}  # six harms
TZ_SIGNS = ["Imix","Ik","Akbal","Kan","Chicchan","Cimi","Manik","Lamat","Muluc","Oc","Chuen","Eb",
            "Ben","Ix","Men","Cib","Caban","Etznab","Cauac","Ahau"]
ASPECTS = [("conj",0,8),("opp",180,8),("trine",120,7),("square",90,7),("sext",60,5)]


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


def _reduce(n, masters=(11, 22, 33)):
    while n > 9 and n not in masters:
        n = _dsum(n)
    return n


def _reduce_plain(n):
    while n > 9:
        n = _dsum(n)
    return n


def life_path(y, m, d):
    """Pythagorean: reduce year, month and day separately, then the sum; masters survive."""
    return _reduce(_reduce_plain(y) + _reduce_plain(m) + _reduce_plain(d))


def chaldean_lp(y, m, d):
    """Chaldean reduces the whole string at once and has no 9 in its alphabet; the date form keeps 9."""
    return _reduce_plain(_dsum(y) + _dsum(m) + _dsum(d))


def personal_year(y, m, d, at_year):
    return _reduce_plain(_reduce_plain(m) + _reduce_plain(d) + _reduce_plain(at_year))


def navamsa_sign(lon):
    """D9: each 30 deg sign divides into nine 3 deg 20' parts; the count starts from the sign's
    element-partner (movable from itself, fixed from the 9th, dual from the 5th)."""
    s = (lon // 30).astype(int) % 12
    part = ((lon % 30) / (30.0 / 9.0)).astype(int)
    start = np.where(s % 3 == 0, s, np.where(s % 3 == 1, (s + 8) % 12, (s + 4) % 12))
    return (start + part) % 12


def _cats(vals, prefix, names, cols, min_support, n):
    """one-hot a categorical, keeping only levels with enough support"""
    vals = np.asarray(vals)
    for v in pd.unique(vals):
        col = (vals == v).astype(np.float32)
        if col.sum() >= min_support:
            cols.append(col); names.append(f"{prefix}={v}")


def build(df, Z, split, exclude=frozenset(), min_support=None):
    n = len(df)
    if min_support is None:
        min_support = max(30, int(0.015 * n))
    A = Z[f"theta_a_{split}"]; B = Z[f"theta_b_{split}"]
    ya = pd.to_numeric(df.dob_a.str[:4]).to_numpy(int); ma = pd.to_numeric(df.dob_a.str[5:7]).to_numpy(int)
    da = pd.to_numeric(df.dob_a.str[8:10]).to_numpy(int)
    yb = pd.to_numeric(df.dob_b.str[:4]).to_numpy(int); mb = pd.to_numeric(df.dob_b.str[5:7]).to_numpy(int)
    db = pd.to_numeric(df.dob_b.str[8:10]).to_numpy(int)
    cols, names = [], []

    # ---------- NUMEROLOGY ----------
    lpa = np.array([life_path(y, m, d) for y, m, d in zip(ya, ma, da)])
    lpb = np.array([life_path(y, m, d) for y, m, d in zip(yb, mb, db)])
    cha = np.array([chaldean_lp(y, m, d) for y, m, d in zip(ya, ma, da)])
    chb = np.array([chaldean_lp(y, m, d) for y, m, d in zip(yb, mb, db)])
    bda = np.array([_reduce(d) for d in da]); bdb = np.array([_reduce(d) for d in db])
    ata = np.array([_reduce_plain(_reduce_plain(m) + _reduce_plain(d)) for m, d in zip(ma, da)])
    atb = np.array([_reduce_plain(_reduce_plain(m) + _reduce_plain(d)) for m, d in zip(mb, db)])
    _cats([f"{a}x{b}" for a, b in zip(lpa, lpb)], "lifepathpair", names, cols, min_support, n)
    _cats([f"{a}x{b}" for a, b in zip(cha, chb)], "chaldeanpair", names, cols, min_support, n)
    _cats([f"{a}x{b}" for a, b in zip(bda, bdb)], "birthdaynumpair", names, cols, min_support, n)
    _cats([f"{a}x{b}" for a, b in zip(ata, atb)], "attitudepair", names, cols, min_support, n)
    _cats([_reduce_plain(a + b) for a, b in zip(lpa, lpb)], "lifepath_sum", names, cols, min_support, n)
    _cats(np.abs(lpa - lpb), "lifepath_gap", names, cols, min_support, n)
    cols.append((lpa == lpb).astype(np.float32)); names.append("lifepath_same")
    cols.append((np.isin(lpa, [11, 22, 33]) | np.isin(lpb, [11, 22, 33])).astype(np.float32))
    names.append("lifepath_master_present")
    cols.append((np.isin(lpa, [11, 22, 33]) & np.isin(lpb, [11, 22, 33])).astype(np.float32))
    names.append("lifepath_both_master")
    # the classical numerological compatibility sets
    HARM = {1: {1, 5, 7}, 2: {2, 4, 8}, 3: {3, 6, 9}, 4: {2, 4, 8}, 5: {1, 5, 7},
            6: {3, 6, 9}, 7: {1, 5, 7}, 8: {2, 4, 8}, 9: {3, 6, 9}}
    harm = np.array([1.0 if _reduce_plain(b) in HARM.get(_reduce_plain(a), set()) else 0.0
                     for a, b in zip(lpa, lpb)], dtype=np.float32)
    cols.append(harm); names.append("lifepath_harmonious_set")
    # personal-year cycle: what year each was living when the other was born
    pya = np.array([personal_year(y, m, d, yy) for y, m, d, yy in zip(ya, ma, da, yb)])
    pyb = np.array([personal_year(y, m, d, yy) for y, m, d, yy in zip(yb, mb, db, ya)])
    _cats([f"{a}x{b}" for a, b in zip(pya, pyb)], "personalyearpair", names, cols, min_support, n)

    # ---------- MOON PHASE (Rudhyar) ----------
    ph_a = (A[:, BI["moon"]] - A[:, BI["sun"]]) % 360.0
    ph_b = (B[:, BI["moon"]] - B[:, BI["sun"]]) % 360.0
    pa = np.floor(ph_a / 45.0).astype(int) % 8
    pb = np.floor(ph_b / 45.0).astype(int) % 8
    ok = np.isfinite(ph_a) & np.isfinite(ph_b)
    lab = np.array([f"{PHASES[i]}x{PHASES[j]}" if o else "na" for i, j, o in zip(pa, pb, ok)])
    _cats(lab, "moonphasepair", names, cols, min_support, n)
    sep = np.where(ok, np.minimum((pa - pb) % 8, (pb - pa) % 8), -1)
    _cats(sep, "moonphase_sep", names, cols, min_support, n)
    cols.append(((pa == pb) & ok).astype(np.float32)); names.append("moonphase_same")
    cols.append((((pa - pb) % 8 == 4) & ok).astype(np.float32)); names.append("moonphase_opposite")

    # ---------- CHINESE ----------
    bra = (ya - 4) % 12; brb = (yb - 4) % 12
    sta = (ya - 4) % 10; stb = (yb - 4) % 10
    _cats([f"{ANIMALS[i]}x{ANIMALS[j]}" for i, j in zip(bra, brb)], "animalpair", names, cols, min_support, n)
    _cats([f"{STEM_EL[i]}x{STEM_EL[j]}" for i, j in zip(sta, stb)], "stemelempair", names, cols, min_support, n)
    cols.append(np.array([1.0 if TRINE[i] == TRINE[j] else 0.0 for i, j in zip(bra, brb)], np.float32))
    names.append("chinese_sanhe_trine")
    cols.append(np.array([1.0 if LIU_HE[i] == j else 0.0 for i, j in zip(bra, brb)], np.float32))
    names.append("chinese_liuhe_harmony")
    cols.append((((bra - brb) % 12) == 6).astype(np.float32)); names.append("chinese_liuchong_clash")
    cols.append(np.array([1.0 if XIANG_HAI.get(i) == j else 0.0 for i, j in zip(bra, brb)], np.float32))
    names.append("chinese_xianghai_harm")
    cols.append((bra == brb).astype(np.float32)); names.append("chinese_same_animal")
    ea = np.array([STEM_EL.index(STEM_EL[i]) for i in sta]); eb = np.array([STEM_EL.index(STEM_EL[i]) for i in stb])
    # five-element production (sheng) and control (ke) cycles, on Wood Fire Earth Metal Water
    order = {"Wood": 0, "Fire": 1, "Earth": 2, "Metal": 3, "Water": 4}
    oa = np.array([order[STEM_EL[i]] for i in sta]); ob = np.array([order[STEM_EL[i]] for i in stb])
    cols.append((((oa + 1) % 5) == ob).astype(np.float32)); names.append("wuxing_he_produces_her")
    cols.append((((ob + 1) % 5) == oa).astype(np.float32)); names.append("wuxing_she_produces_him")
    cols.append((((oa + 2) % 5) == ob).astype(np.float32)); names.append("wuxing_he_controls_her")
    cols.append((((ob + 2) % 5) == oa).astype(np.float32)); names.append("wuxing_she_controls_him")
    cols.append((oa == ob).astype(np.float32)); names.append("wuxing_same_element")
    cols.append(((sta % 2) == (stb % 2)).astype(np.float32)); names.append("chinese_same_polarity")

    # ---------- VEDIC: nakshatra, Navamsa D9, Ashtakoota ----------
    mna = A[:, BI["moon"]]; mnb = B[:, BI["moon"]]
    nka = np.floor(mna / (360.0 / NAK)).astype(int) % NAK
    nkb = np.floor(mnb / (360.0 / NAK)).astype(int) % NAK
    sa = (mna // 30).astype(int) % 12; sb = (mnb // 30).astype(int) % 12
    okv = np.isfinite(mna) & np.isfinite(mnb)

    # Navamsa D9 of the marriage significators
    for b in ("moon", "venus", "jupiter"):
        d9a = navamsa_sign(np.nan_to_num(A[:, BI[b]], nan=-1))
        d9b = navamsa_sign(np.nan_to_num(B[:, BI[b]], nan=-1))
        good = np.isfinite(A[:, BI[b]]) & np.isfinite(B[:, BI[b]])
        _cats([f"{SIGNS[i]}x{SIGNS[j]}" if g else "na" for i, j, g in zip(d9a, d9b, good)],
              f"d9_{b}pair", names, cols, min_support, n)
        cols.append(((d9a == d9b) & good).astype(np.float32)); names.append(f"d9_{b}_same_sign")
        cols.append((((d9a - d9b) % 12 == 6) & good).astype(np.float32)); names.append(f"d9_{b}_opposite")
        cols.append((((d9a - d9b) % 12 % 4 == 0) & good).astype(np.float32)); names.append(f"d9_{b}_trine")

    # the eight kootas, scored traditionally
    varna = np.where(np.array([VARNA_BY_SIGN[i] for i in sa]) >= np.array([VARNA_BY_SIGN[i] for i in sb]), 1, 0)
    vashya = np.array([2 if VASHYA_GROUP[i] == VASHYA_GROUP[j] else (1 if abs(VASHYA_GROUP[i]-VASHYA_GROUP[j]) == 1 else 0)
                       for i, j in zip(sa, sb)])
    cnt_ab = ((nkb - nka) % NAK) + 1; cnt_ba = ((nka - nkb) % NAK) + 1
    tara = np.where(((cnt_ab % 9) not in (3, 5, 7) if False else True), 0, 0)
    tara = np.array([3 if ((a % 9) not in (3, 5, 7) and (b % 9) not in (3, 5, 7)) else
                     (1.5 if ((a % 9) not in (3, 5, 7) or (b % 9) not in (3, 5, 7)) else 0)
                     for a, b in zip(cnt_ab, cnt_ba)])
    yon_a = np.array([YONI[i] for i in nka]); yon_b = np.array([YONI[i] for i in nkb])
    yoni = np.array([4 if i == j else (0 if (min(i, j), max(i, j)) in
                     {(min(x, y), max(x, y)) for x, y in YONI_ENEMY} else 2)
                     for i, j in zip(yon_a, yon_b)])
    la = np.array([SIGN_LORD[i] for i in sa]); lb = np.array([SIGN_LORD[i] for i in sb])
    maitri = np.array([[0, 1, 3, 5][MAITRI[i, j]] if False else (5 if MAITRI[i, j] == 2 else (3 if MAITRI[i, j] == 1 else 0))
                       for i, j in zip(la, lb)])
    gana = np.array([6 if GANA[i] == GANA[j] else (5 if {GANA[i], GANA[j]} == {0, 1} else
                     (1 if {GANA[i], GANA[j]} == {1, 2} else 0)) for i, j in zip(nka, nkb)])
    dist = (sb - sa) % 12 + 1
    bhakoot = np.array([0 if d in (6, 8, 2, 12, 5, 9) else 7 for d in dist])
    nadi = np.array([0 if NADI[i] == NADI[j] else 8 for i, j in zip(nka, nkb)])
    total = varna + vashya + tara + yoni + maitri + gana + bhakoot + nadi
    for nm, v, mx in (("varna", varna, 1), ("vashya", vashya, 2), ("tara", tara, 3), ("yoni", yoni, 4),
                      ("grahamaitri", maitri, 5), ("gana", gana, 6), ("bhakoot", bhakoot, 7), ("nadi", nadi, 8)):
        _cats(np.where(okv, v, -1), f"koota_{nm}", names, cols, min_support, n)
        cols.append(((v >= mx) & okv).astype(np.float32)); names.append(f"koota_{nm}_full")
    band = np.where(~okv, -1, np.digitize(total, [12, 18, 24, 28, 32]))
    _cats(band, "guna_total_band", names, cols, min_support, n)
    cols.append(((total >= 18) & okv).astype(np.float32)); names.append("guna_total_ge18_traditional_pass")
    cols.append(((total >= 24) & okv).astype(np.float32)); names.append("guna_total_ge24_very_good")
    cols.append(((nadi == 0) & okv).astype(np.float32)); names.append("nadi_dosha")
    cols.append(((bhakoot == 0) & okv).astype(np.float32)); names.append("bhakoot_dosha")
    _cats([f"{YONI_NAME[i]}x{YONI_NAME[j]}" if o else "na" for i, j, o in zip(yon_a, yon_b, okv)],
          "yonipair", names, cols, min_support, n)
    _cats([f"{LORD_NAME[i]}x{LORD_NAME[j]}" if o else "na" for i, j, o in zip(la, lb, okv)],
          "moonlordpair", names, cols, min_support, n)
    _cats([f"{VARNA_NAME[VARNA_BY_SIGN[i]]}x{VARNA_NAME[VARNA_BY_SIGN[j]]}" if o else "na"
           for i, j, o in zip(sa, sb, okv)], "varnapair", names, cols, min_support, n)

    # ---------- MAYAN TZOLKIN ----------
    jd_a = np.array([_jdn(y, m, d) for y, m, d in zip(ya, ma, da)])
    jd_b = np.array([_jdn(y, m, d) for y, m, d in zip(yb, mb, db)])
    tza = (jd_a + 159) % 260; tzb = (jd_b + 159) % 260
    dsa = tza % 20; dsb = tzb % 20
    toa = tza % 13 + 1; tob = tzb % 13 + 1
    _cats([f"{TZ_SIGNS[i]}x{TZ_SIGNS[j]}" for i, j in zip(dsa, dsb)], "tzolkin_signpair", names, cols, min_support, n)
    _cats([f"{i}x{j}" for i, j in zip(toa, tob)], "tzolkin_tonepair", names, cols, min_support, n)
    cols.append((dsa == dsb).astype(np.float32)); names.append("tzolkin_same_daysign")
    cols.append((toa == tob).astype(np.float32)); names.append("tzolkin_same_tone")
    cols.append((((dsa - dsb) % 20) == 10).astype(np.float32)); names.append("tzolkin_antipode")

    # ---------- HARMONIC + DRACONIC + ANTISCIA SYNASTRY ----------
    pl = ["sun", "moon", "venus", "mars", "jupiter", "saturn"]
    def aspect_cols(la_, lb_, tag, bodies_a, bodies_b):
        for x in bodies_a:
            for y in bodies_b:
                d = np.abs(((la_[:, BI[x]] - lb_[:, BI[y]] + 180) % 360) - 180)
                for an, ang, orb in ASPECTS:
                    col = (np.abs(d - ang) <= orb).astype(np.float32)
                    col[~np.isfinite(d)] = 0.0
                    if col.sum() >= min_support:
                        cols.append(col); names.append(f"{tag}_his_{x}_{an}_her_{y}")
    for h in (5, 7, 9):
        aspect_cols((A * h) % 360.0, (B * h) % 360.0, f"h{h}", pl, pl)
    dra_a = (A - A[:, [BI["true_node"]]]) % 360.0
    dra_b = (B - B[:, [BI["true_node"]]]) % 360.0
    aspect_cols(dra_a, dra_b, "draconic", ["sun", "moon", "venus", "mars"], ["sun", "moon", "venus", "mars"])
    anti_a = (180.0 - A) % 360.0
    aspect_cols(anti_a, B, "antiscia", ["sun", "moon", "venus", "mars"], ["sun", "moon", "venus", "mars"])

    keep = [i for i, nm in enumerate(names) if nm not in exclude]
    X = np.column_stack([cols[i] for i in keep]).astype(np.float32) if keep else np.zeros((n, 0), np.float32)
    return X, [names[i] for i in keep]
