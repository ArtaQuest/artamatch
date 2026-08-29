"""v23_traditions.py — the marriage-specific doctrines still missing, all pair-only, all happy-oriented.

v21 filled the broad gaps. This adds the traditions whose whole PURPOSE is marriage, which is where a
compatibility model should have started:

  MANGAL DOSHA    Manglik status from the Moon-lagna — Mars in the 1st, 2nd, 4th, 7th, 8th or 12th. In
                  Indian practice this is the single most consulted marriage condition there is, and the
                  classical cancellation (both partners Manglik) is included with it.
  JAIMINI KARAKAS Darakaraka — the planet at the LOWEST degree in its sign — is the spouse significator
                  in Jaimini astrology. Atmakaraka (highest) is the soul. Both are computable from
                  longitude alone, no birth time needed.
  BAZI DAY PILLAR The day master is what Chinese astrology actually reads a marriage from; the bank had
                  only the YEAR pillar. Sexagenary day from the Julian day number, anchored on the
                  jia-zi day of 2000-01-07 and verified against it.
  ARABIC PARTS    The Lot of Marriage and the Lot of Eros, cast in a solar chart — the classical
                  convention for an unknown birth time, where the Sun stands in for the ascendant.
  PANCHANGA       Nitya Yoga (27) and Karana (11), the two limbs the bank was missing.
  DREAMSPELL      The Mayan oracle relations between two kin: antipode, analog and occult partner.
  PROGRESSIONS    Secondary progressed Sun and Moon — a day for a year — of each chart advanced to the
                  other's birth, then read in synastry.
  MIDPOINTS       Ebertin's marriage axis: one partner's Sun/Moon and Venus/Mars midpoints met by the
                  other's planets.
  NUMEROLOGY      Pinnacles, Challenges, karmic debt numbers and Tarot birth cards.
  CELTIC          The thirteen-tree lunar calendar.

Every statement uses BOTH dates. build(df, Z, split, exclude, min_support) -> (X, names).
"""
import numpy as np
import pandas as pd

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
STEMS = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
STEM_EL = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]
BRANCH = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster",
          "Dog", "Pig"]
KARANA = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
FIXED_KARANA = ["Kimstughna", "Shakuni", "Chatushpada", "Naga"]
JAIMINI = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]
JN = {"sun": "Sun", "moon": "Moon", "mars": "Mars", "mercury": "Mercury", "jupiter": "Jupiter",
      "venus": "Venus", "saturn": "Saturn"}
TREES = ["Birch", "Rowan", "Ash", "Alder", "Willow", "Hawthorn", "Oak", "Holly", "Hazel", "Vine",
         "Ivy", "Reed", "Elder"]
TREE_START = [(12, 24), (1, 21), (2, 18), (3, 18), (4, 15), (5, 13), (6, 10), (7, 8), (8, 5),
              (9, 2), (9, 30), (10, 28), (11, 25)]
TZ_SIGNS = ["Imix", "Ik", "Akbal", "Kan", "Chicchan", "Cimi", "Manik", "Lamat", "Muluc", "Oc",
            "Chuen", "Eb", "Ben", "Ix", "Men", "Cib", "Caban", "Etznab", "Cauac", "Ahau"]
ASPECTS = [("conj", 0, 8), ("opp", 180, 8), ("trine", 120, 7), ("square", 90, 7), ("sext", 60, 5)]
MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}


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


def _red(n, keep=()):
    while n > 9 and n not in keep:
        n = _dsum(n)
    return n


def _cats(vals, prefix, names, cols, ms):
    vals = np.asarray(vals)
    for v in pd.unique(vals):
        c = (vals == v).astype(np.float32)
        if c.sum() >= ms:
            cols.append(c); names.append(f"{prefix}={v}")


def _asp(cols, names, la, lb, tag, pairs, ms, n):
    for x, y in pairs:
        ax = la[x] if isinstance(la, dict) else la[:, BI[x]]
        by = lb[y] if isinstance(lb, dict) else lb[:, BI[y]]
        d = np.abs(((ax - by + 180) % 360) - 180)
        for an, ang, orb in ASPECTS:
            c = (np.abs(d - ang) <= orb).astype(np.float32)
            c[~np.isfinite(d)] = 0.0
            if c.sum() >= ms:
                cols.append(c); names.append(f"{tag}_his_{x}_{an}_her_{y}")


def build(df, Z, split, exclude=frozenset(), min_support=40):
    n = len(df)
    ms = min_support
    A = Z[f"theta_a_{split}"]; B = Z[f"theta_b_{split}"]
    ya = pd.to_numeric(df.dob_a.str[:4]).to_numpy(int); ma = pd.to_numeric(df.dob_a.str[5:7]).to_numpy(int)
    da = pd.to_numeric(df.dob_a.str[8:10]).to_numpy(int)
    yb = pd.to_numeric(df.dob_b.str[:4]).to_numpy(int); mb = pd.to_numeric(df.dob_b.str[5:7]).to_numpy(int)
    db = pd.to_numeric(df.dob_b.str[8:10]).to_numpy(int)
    cols, names = [], []
    fin = np.isfinite(A[:, BI["moon"]]) & np.isfinite(B[:, BI["moon"]])

    # ---------- MANGAL DOSHA (Manglik), from the Moon-lagna ----------
    def manglik(P):
        mo = (P[:, BI["moon"]] // 30).astype(int) % 12
        mr = (P[:, BI["mars"]] // 30).astype(int) % 12
        house = ((mr - mo) % 12) + 1
        return np.isin(house, list(MANGLIK_HOUSES)), house
    mka, ha = manglik(A); mkb, hb = manglik(B)
    cols.append((mka & mkb & fin).astype(np.float32)); names.append("manglik_both_cancelled")
    cols.append((mka & ~mkb & fin).astype(np.float32)); names.append("manglik_he_only")
    cols.append((~mka & mkb & fin).astype(np.float32)); names.append("manglik_she_only")
    cols.append((~mka & ~mkb & fin).astype(np.float32)); names.append("manglik_neither")
    _cats([f"{i}x{j}" if f else "na" for i, j, f in zip(ha, hb, fin)], "mars_housepair", names, cols, ms)

    # ---------- JAIMINI CHARA KARAKAS ----------
    def karakas(P):
        deg = np.column_stack([P[:, BI[b]] % 30 for b in JAIMINI])
        dk = np.argmin(np.where(np.isfinite(deg), deg, 99), axis=1)     # lowest degree = spouse
        ak = np.argmax(np.where(np.isfinite(deg), deg, -1), axis=1)     # highest = soul
        return dk, ak
    dka, aka = karakas(A); dkb, akb = karakas(B)
    _cats([f"{JN[JAIMINI[i]]}x{JN[JAIMINI[j]]}" for i, j in zip(dka, dkb)], "darakarakapair", names, cols, ms)
    _cats([f"{JN[JAIMINI[i]]}x{JN[JAIMINI[j]]}" for i, j in zip(aka, akb)], "atmakarakapair", names, cols, ms)
    cols.append((dka == dkb).astype(np.float32)); names.append("darakaraka_same_planet")
    cols.append((aka == akb).astype(np.float32)); names.append("atmakaraka_same_planet")
    cols.append((dka == akb).astype(np.float32)); names.append("his_darakaraka_is_her_atmakaraka")
    cols.append((aka == dkb).astype(np.float32)); names.append("her_darakaraka_is_his_atmakaraka")
    # the sign the spouse-significator sits in, paired
    dsa = np.array([(A[i, BI[JAIMINI[dka[i]]]] // 30) % 12 if np.isfinite(A[i, BI[JAIMINI[dka[i]]]]) else -1
                    for i in range(n)]).astype(int)
    dsb = np.array([(B[i, BI[JAIMINI[dkb[i]]]] // 30) % 12 if np.isfinite(B[i, BI[JAIMINI[dkb[i]]]]) else -1
                    for i in range(n)]).astype(int)
    _cats([f"{SIGNS[i]}x{SIGNS[j]}" if i >= 0 and j >= 0 else "na" for i, j in zip(dsa, dsb)],
          "darakaraka_signpair", names, cols, ms)

    # ---------- BAZI DAY PILLAR ----------
    jda = np.array([_jdn(y, m, d) for y, m, d in zip(ya, ma, da)])
    jdb = np.array([_jdn(y, m, d) for y, m, d in zip(yb, mb, db)])
    sx_a = (jda + 49) % 60; sx_b = (jdb + 49) % 60      # anchored: 2000-01-07 is jia-zi
    dsa_s, dsb_s = sx_a % 10, sx_b % 10
    dba, dbb = sx_a % 12, sx_b % 12
    _cats([f"{STEMS[i]}x{STEMS[j]}" for i, j in zip(dsa_s, dsb_s)], "bazi_daystempair", names, cols, ms)
    _cats([f"{BRANCH[i]}x{BRANCH[j]}" for i, j in zip(dba, dbb)], "bazi_daybranchpair", names, cols, ms)
    _cats([f"{STEM_EL[i]}x{STEM_EL[j]}" for i, j in zip(dsa_s, dsb_s)], "daymaster_elempair", names, cols, ms)
    LIU_HE = {0: 1, 1: 0, 2: 11, 11: 2, 3: 10, 10: 3, 4: 9, 9: 4, 5: 8, 8: 5, 6: 7, 7: 6}
    cols.append(np.array([1.0 if LIU_HE[i] == j else 0.0 for i, j in zip(dba, dbb)], np.float32))
    names.append("bazi_day_liuhe_harmony")
    cols.append((((dba - dbb) % 12) == 6).astype(np.float32)); names.append("bazi_day_clash")
    cols.append((dsa_s == dsb_s).astype(np.float32)); names.append("bazi_same_day_master")
    order = {"Wood": 0, "Fire": 1, "Earth": 2, "Metal": 3, "Water": 4}
    oa = np.array([order[STEM_EL[i]] for i in dsa_s]); ob = np.array([order[STEM_EL[i]] for i in dsb_s])
    cols.append((((oa + 1) % 5) == ob).astype(np.float32)); names.append("daymaster_he_produces_her")
    cols.append((((ob + 1) % 5) == oa).astype(np.float32)); names.append("daymaster_she_produces_him")
    cols.append((((oa + 2) % 5) == ob).astype(np.float32)); names.append("daymaster_he_controls_her")
    cols.append((((ob + 2) % 5) == oa).astype(np.float32)); names.append("daymaster_she_controls_him")

    # ---------- ARABIC PARTS (solar chart: the Sun stands in for the ascendant) ----------
    def parts(P):
        sun, moon, ven = P[:, BI["sun"]], P[:, BI["moon"]], P[:, BI["venus"]]
        marriage = (2 * sun + 180.0 - ven) % 360.0          # Asc + Desc - Venus
        eros = (ven + moon - sun) % 360.0                    # Asc + Venus - Spirit, solar
        return {"lot_marriage": marriage, "lot_eros": eros}
    pa, pb = parts(A), parts(B)
    for k in ("lot_marriage", "lot_eros"):
        _cats([f"{SIGNS[int(x // 30) % 12]}x{SIGNS[int(y // 30) % 12]}"
               if np.isfinite(x) and np.isfinite(y) else "na" for x, y in zip(pa[k], pb[k])],
              f"{k}_signpair", names, cols, ms)
        d = np.abs(((pa[k] - pb[k] + 180) % 360) - 180)
        for an, ang, orb in ASPECTS:
            c = (np.abs(d - ang) <= orb).astype(np.float32); c[~np.isfinite(d)] = 0.0
            if c.sum() >= ms:
                cols.append(c); names.append(f"his_{k}_{an}_her_{k}")
    _asp(cols, names, pa, B, "lotmarriage", [("lot_marriage", b) for b in
         ("sun", "moon", "venus", "mars", "jupiter", "saturn")], ms, n)
    _asp(cols, names, pb, A, "herlotmarriage", [("lot_marriage", b) for b in
         ("sun", "moon", "venus", "mars", "jupiter", "saturn")], ms, n)

    # ---------- PANCHANGA: Nitya Yoga and Karana ----------
    def yoga(P):
        return np.floor((((P[:, BI["sun"]] + P[:, BI["moon"]]) % 360.0)) / (360.0 / 27.0)).astype(int) % 27
    def karana(P):
        half = np.floor((((P[:, BI["moon"]] - P[:, BI["sun"]]) % 360.0)) / 6.0).astype(int) % 60
        out = []
        for h in half:
            if h == 0:
                out.append("Kimstughna")
            elif h >= 57:
                out.append(FIXED_KARANA[h - 56])
            else:
                out.append(KARANA[(h - 1) % 7])
        return np.array(out)
    ya_, yb_ = yoga(A), yoga(B)
    _cats([f"{i}x{j}" if f else "na" for i, j, f in zip(ya_, yb_, fin)], "nityayogapair", names, cols, ms)
    cols.append(((ya_ == yb_) & fin).astype(np.float32)); names.append("nityayoga_same")
    ka_, kb_ = karana(A), karana(B)
    _cats([f"{i}x{j}" for i, j in zip(ka_, kb_)], "karanapair", names, cols, ms)
    cols.append(((ka_ == kb_) & fin).astype(np.float32)); names.append("karana_same")
    # nakshatra pada (108 divisions)
    pda = np.floor((A[:, BI["moon"]] % (360.0 / 27.0)) / (360.0 / 108.0)).astype(int) % 4
    pdb = np.floor((B[:, BI["moon"]] % (360.0 / 27.0)) / (360.0 / 108.0)).astype(int) % 4
    _cats([f"{i+1}x{j+1}" if f else "na" for i, j, f in zip(pda, pdb, fin)], "padapair", names, cols, ms)

    # ---------- DREAMSPELL ORACLE (Mayan) ----------
    kin_a = (jda + 159) % 260; kin_b = (jdb + 159) % 260
    sa_, sb_ = kin_a % 20, kin_b % 20
    cols.append((((sa_ + 10) % 20) == sb_).astype(np.float32)); names.append("dreamspell_antipode")
    cols.append(((19 - sa_) == sb_).astype(np.float32)); names.append("dreamspell_analog")
    cols.append((((kin_a + kin_b) % 260) == (261 - 2) % 260).astype(np.float32))
    names.append("dreamspell_occult")
    cols.append((sa_ == sb_).astype(np.float32)); names.append("dreamspell_same_daysign")

    # ---------- SECONDARY PROGRESSIONS (a day for a year) ----------
    gap = (jdb - jda) / 365.2422
    prog_a = {"sun": (A[:, BI["sun"]] + gap) % 360.0, "moon": (A[:, BI["moon"]] + gap * 13.1764) % 360.0}
    prog_b = {"sun": (B[:, BI["sun"]] - gap) % 360.0, "moon": (B[:, BI["moon"]] - gap * 13.1764) % 360.0}
    _asp(cols, names, prog_a, B, "prog", [("sun", "sun"), ("sun", "moon"), ("sun", "venus"),
                                          ("moon", "sun"), ("moon", "moon"), ("moon", "venus")], ms, n)
    _asp(cols, names, prog_b, A, "herprog", [("sun", "sun"), ("sun", "moon"), ("sun", "venus"),
                                             ("moon", "sun"), ("moon", "moon"), ("moon", "venus")], ms, n)

    # ---------- EBERTIN MIDPOINTS (cosmobiology's marriage axis) ----------
    def mid(P, x, y):
        a_, b_ = P[:, BI[x]], P[:, BI[y]]
        d = ((b_ - a_ + 180) % 360) - 180
        return (a_ + d / 2.0) % 360.0
    for nm, x, y in (("sunmoon", "sun", "moon"), ("venusmars", "venus", "mars"),
                     ("venusjupiter", "venus", "jupiter")):
        for src, dst, tag in ((A, B, "his"), (B, A, "her")):
            m_ = {nm: mid(src, x, y)}
            _asp(cols, names, m_, dst, f"mid{tag}", [(nm, b) for b in
                 ("sun", "moon", "venus", "mars", "jupiter", "saturn")], ms, n)

    # ---------- NUMEROLOGY: pinnacles, challenges, karmic debt, tarot ----------
    def pin(y, m, d):
        rm, rd, ry = _red(m), _red(d), _red(y)
        p1 = _red(rm + rd); p2 = _red(rd + ry); p3 = _red(p1 + p2); p4 = _red(rm + ry)
        return p1, p2, p3, p4
    def cha(y, m, d):
        rm, rd, ry = _red(m), _red(d), _red(y)
        c1 = abs(rm - rd); c2 = abs(rd - ry); c3 = abs(c1 - c2); c4 = abs(rm - ry)
        return c1, c2, c3, c4
    PA = np.array([pin(y, m, d) for y, m, d in zip(ya, ma, da)])
    PB = np.array([pin(y, m, d) for y, m, d in zip(yb, mb, db)])
    CA = np.array([cha(y, m, d) for y, m, d in zip(ya, ma, da)])
    CB = np.array([cha(y, m, d) for y, m, d in zip(yb, mb, db)])
    for i in range(4):
        _cats([f"{a}x{b}" for a, b in zip(PA[:, i], PB[:, i])], f"pinnacle{i+1}pair", names, cols, ms)
        _cats([f"{a}x{b}" for a, b in zip(CA[:, i], CB[:, i])], f"challenge{i+1}pair", names, cols, ms)
        cols.append((PA[:, i] == PB[:, i]).astype(np.float32)); names.append(f"pinnacle{i+1}_same")
        cols.append((CA[:, i] == CB[:, i]).astype(np.float32)); names.append(f"challenge{i+1}_same")
    KARMIC = {13, 14, 16, 19}
    ka2 = np.array([1.0 if (_dsum(y) + _dsum(m) + _dsum(d)) in KARMIC else 0.0
                    for y, m, d in zip(ya, ma, da)], np.float32)
    kb2 = np.array([1.0 if (_dsum(y) + _dsum(m) + _dsum(d)) in KARMIC else 0.0
                    for y, m, d in zip(yb, mb, db)], np.float32)
    cols.append(((ka2 > 0) & (kb2 > 0)).astype(np.float32)); names.append("karmicdebt_both")
    cols.append(((ka2 > 0) ^ (kb2 > 0)).astype(np.float32)); names.append("karmicdebt_one")
    cols.append(((ka2 == 0) & (kb2 == 0)).astype(np.float32)); names.append("karmicdebt_neither")
    def tarot(y, m, d):
        t = _dsum(y) + m + d
        while t > 22:
            t = _dsum(t)
        return max(t, 1)
    ta = np.array([tarot(y, m, d) for y, m, d in zip(ya, ma, da)])
    tb = np.array([tarot(y, m, d) for y, m, d in zip(yb, mb, db)])
    _cats([f"{a}x{b}" for a, b in zip(ta, tb)], "tarotbirthcardpair", names, cols, ms)
    cols.append((ta == tb).astype(np.float32)); names.append("tarotbirthcard_same")

    # ---------- CELTIC TREE CALENDAR ----------
    def tree(m, d):
        best = 0
        for i, (tm, td) in enumerate(TREE_START):
            if (m, d) >= (tm, td):
                best = i
        if (m, d) < (1, 21):
            best = 0
        return best
    tra = np.array([tree(m, d) for m, d in zip(ma, da)])
    trb = np.array([tree(m, d) for m, d in zip(mb, db)])
    _cats([f"{TREES[i]}x{TREES[j]}" for i, j in zip(tra, trb)], "celtictreepair", names, cols, ms)
    cols.append((tra == trb).astype(np.float32)); names.append("celtictree_same")

    keep = [i for i, nm in enumerate(names) if nm not in exclude]
    X = np.column_stack([cols[i] for i in keep]).astype(np.float32) if keep else np.zeros((n, 0), np.float32)
    return X, [names[i] for i in keep]
