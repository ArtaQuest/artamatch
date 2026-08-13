"""
trad_vedic_match.py — Vedic marriage matching: Ashtakoot / Guna Milan, Kuja dosha, ten Poruthams.

WHAT THIS IS

The whole of the classical Hindu marriage-matching apparatus, computed the way the texts specify
rather than re-encoded into something that merely looks Vedic:

  * ASHTAKOOT (Guna Milan), 36 points, all eight kutas with their own published tables —
    Varna (1) · Vashya (2) · Tara/Dina (3) · Yoni (4) · Graha Maitri (5) · Gana (6) ·
    Bhakoot (7) · Nadi (8) — plus the Bhakoot dosha and Nadi dosha flags and the classical
    cancellation (dosha-bhanga / parihara) rules for each.
  * KUJA / MANGAL DOSHA for both partners with the classical cancellation conditions, including
    the "both partners have it, so it cancels" rule (dosha samya).
  * THE TEN TAMIL / SOUTH-INDIAN PORUTHAMS — Dina, Gana, Mahendra, Stree Deergha, Yoni, Rasi,
    Rasyadhipathi, Vasya, Rajju, Vedha — each as its own feature plus the count satisfied, and the
    Rajju limb category with the same-Rajju clash rule.

SOURCES FOR EACH RULE (cited again at the table that implements it)

  Ashtakoot structure and the eight kuta maxima: Narada Samhita / Muhurta Chintamani, as reproduced
  in B. V. Raman, *Muhurtha* (ch. "Marriage — Kuta agreement") and in Kalyana Varma's *Saravali*.
  Varna ranks from the Moon-sign element; Vashya five-class table; the 14-animal Yoni table with its
  seven sworn-enemy pairs; naisargika (natural) planetary friendship for Graha Maitri; Deva/Manushya/
  Rakshasa gana; the 2-12 / 5-9 / 6-8 Bhakoot dosha; Aadi/Madhya/Antya nadi.
  Poruthams: the standard Tamil *dasa porutham* list as given in Tamil panchangams and in
  B. V. Raman, *Muhurtha* (South-Indian system section) — Mahendra counts {4,7,10,13,16,19,22,25},
  Stree Deergha count > 9, Dina remainders {2,4,6,8,0}, Rajju five limbs (Pada/Uru/Udara/Kanta/Sira),
  the thirteen Vedha pairs.
  Kuja dosha: Mars in bhavas 1, 2, 4, 7, 8, 12; cancellations from the *parihara* lists in
  Manasagari / Jataka Parijata as reproduced in standard Jyotish practice.

Where a text is reproduced with variant numbers (Vashya's half-point cells, the Gana table's
asymmetry, the Tara even/odd versus {Vipat,Pratyari,Vadha} reading) BOTH readings are emitted: the
headline 36-point total uses the most widely printed version, and the alternate is a separate column,
plus a one-hot of the underlying category pair so a model can recover any table it likes.

PROXIES FORCED BY THE DATA — stated plainly, as the contract requires

  1. NO BIRTH TIME. Everything is computed at 12:00 UT. The Moon therefore carries roughly +-6 deg of
     error, which is nearly half a nakshatra (13 deg 20'). Every nakshatra-derived kuta here is
     consequently about half-reliable at the individual-couple level. That is not repaired anywhere;
     it is instead MEASURED: the block "vm: ashtakoot under the +-6deg moon smear" reports the
     EXPECTED value of every kuta under a Gaussian smear of that width together with its standard
     deviation, so a couple whose score is robust to the unknown birth time is distinguishable from
     one whose score is an accident of noon.
  2. NO LAGNA, SO NO HOUSES. Kuja dosha is classically read from the Lagna. The Lagna cannot be
     computed without a birth time and place. The substitution used here is not invented: the same
     texts prescribe examining Kuja dosha ALSO from the Moon (Chandra lagna) and from Venus, and
     this module computes it from the Moon, the Sun (Surya lagna) and Venus — three documented
     alternative reference points — and never from a fabricated Ascendant. House = whole-sign count
     from the reference, which is the Vedic bhava convention anyway.
  3. NO SEX. Varna, Gana, Dina, Mahendra, Stree Deergha, Rasi and Vasya are asymmetric in bride and
     groom. Sex is unknown, so the older partner is put in the groom role and the younger in the
     bride role, AND the reverse, and both orderings are emitted.
  4. NAVAMSA (D9) IS REAL HERE. The ninth harmonic needs only a longitude, not a birth time, so the
     navamsa Moon sign is computed exactly and used for the classical navamsa-lord cancellation of
     Bhakoot dosha.
  5. Vimshottari dasha BALANCE at birth would need a birth time; only the nakshatra LORD is used
     (which does not), for the same-dispositor cancellations.

E.Y is never read.
"""

import numpy as np

TRADITION = "Vedic marriage matching (Ashtakoot / Guna Milan 36 points, Kuja dosha, ten Poruthams)"

# ════════════════════════════════════════════════════════════════════════════════════════════════
# Zodiac arithmetic
# ════════════════════════════════════════════════════════════════════════════════════════════════
NAKW = 360.0 / 27.0           # 13 deg 20'
PADW = 360.0 / 108.0          # 3 deg 20'
NAVW = 30.0 / 9.0             # navamsa width, also 3 deg 20'


def _nak(lon):
    # exact-integer form: 27/360 = 3/40, so a boundary longitude never lands a hair below its bin
    return np.mod(np.floor(np.mod(lon, 360.0) * 3.0 / 40.0).astype(np.int64), 27)


def _p320(lon):
    """Index of the 3 deg 20' division, 0..107. Pada is this mod 4; navamsa is this mod 12."""
    return np.floor(np.mod(lon, 360.0) * 3.0 / 10.0).astype(np.int64)


def _pada(lon):
    return np.mod(_p320(lon), 4)


def _rasi(lon):
    return np.mod(np.floor(np.mod(lon, 360.0) / 30.0).astype(np.int64), 12)


def _navamsa(lon):
    """D9 sign. floor(lon / 3d20') mod 12 reproduces the classical fire->Aries, earth->Capricorn,
    air->Libra, water->Cancer starting points exactly, and needs no birth time. The pada index and
    the navamsa index are the SAME 3 deg 20' count, read mod 4 and mod 12 respectively."""
    return np.mod(_p320(lon), 12)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# The classical tables
# ════════════════════════════════════════════════════════════════════════════════════════════════

# ── Varna (1 point). Moon-sign element -> caste rank. Brahmin 4 (water), Kshatriya 3 (fire),
#    Vaishya 2 (earth), Shudra 1 (air). Rule: 1 point iff the groom's varna is not lower than the
#    bride's (Muhurtha, Varna kuta).
VARNA = np.array([3, 2, 1, 4, 3, 2, 1, 4, 3, 2, 1, 4], dtype=np.int64)

# ── Vashya (2 points). Five classes: 0 Chatushpada (quadruped), 1 Manava/Dwipada (human),
#    2 Jalachara (water), 3 Vanachara (wild), 4 Keeta (insect). Sagittarius is Manava in its first
#    half and Chatushpada in its second; Capricorn is Chatushpada then Jalachara.
VASHYA_BASE = np.array([0, 0, 1, 2, 3, 1, 1, 4, 1, 0, 1, 2], dtype=np.int64)
#    Table as reproduced in standard Guna Milan practice; variants differ only in a couple of
#    half-point cells, and the class-pair one-hot block below lets any variant be recovered.
VASHYA_TBL = np.array([
    [2.0, 1.0, 1.0, 0.0, 1.0],
    [1.0, 2.0, 1.0, 0.5, 1.0],
    [1.0, 1.0, 2.0, 1.0, 0.5],
    [0.0, 0.5, 1.0, 2.0, 1.0],
    [1.0, 1.0, 0.5, 1.0, 2.0],
])

# ── Gana (6 points). 0 Deva, 1 Manushya, 2 Rakshasa.
GANA = np.array([0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1, 1, 0],
                dtype=np.int64)
GANA_TBL = np.array([[6.0, 5.0, 1.0],
                     [5.0, 6.0, 0.0],
                     [1.0, 0.0, 6.0]])
# the asymmetric reading (row = groom's gana, col = bride's gana) that several texts give
GANA_TBL_ASYM = np.array([[6.0, 6.0, 0.0],
                          [5.0, 6.0, 0.0],
                          [1.0, 3.0, 6.0]])
# Tamil Gana porutham grading: 1 present, 0.5 middling, 0 absent (row groom, col bride)
GANA_PORU = np.array([[1.0, 1.0, 0.0],
                      [0.5, 1.0, 0.0],
                      [0.0, 0.5, 1.0]])

# ── Yoni (4 points). 14 animals; every animal holds two nakshatras (one male, one female) except
#    the mongoose, which holds only Uttara Ashadha — 14*2 - 1 = 27, the arithmetic check on the list.
#    0 Horse 1 Elephant 2 Sheep 3 Serpent 4 Dog 5 Cat 6 Rat 7 Cow 8 Buffalo 9 Tiger 10 Deer
#    11 Monkey 12 Mongoose 13 Lion
ANIMAL = np.array([0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0,
                   13, 7, 1], dtype=np.int64)
YSEX = np.array([0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1],
                dtype=np.int64)   # 0 male, 1 female
#    The Yoni table: 4 same yoni, 3 friendly, 2 neutral, 1 unfriendly, 0 the seven sworn enemies
#    (Horse-Buffalo, Elephant-Lion, Sheep-Monkey, Serpent-Mongoose, Dog-Deer, Cat-Rat, Cow-Tiger).
YONI_TBL = np.array([
    [4, 2, 2, 3, 2, 2, 2, 2, 0, 1, 1, 3, 2, 1],   # Horse
    [2, 4, 3, 3, 3, 2, 2, 2, 3, 1, 2, 3, 2, 0],   # Elephant
    [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],   # Sheep
    [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],   # Serpent
    [2, 3, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1],   # Dog
    [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],   # Cat
    [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2],   # Rat
    [2, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],   # Cow
    [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],   # Buffalo
    [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 2, 1, 1, 1],   # Tiger
    [1, 2, 2, 2, 0, 3, 2, 3, 2, 2, 4, 2, 2, 1],   # Deer
    [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 1],   # Monkey
    [2, 2, 3, 0, 1, 2, 1, 2, 2, 1, 2, 3, 4, 2],   # Mongoose
    [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 2, 4],   # Lion
], dtype=np.float64)

# ── Nadi (8 points). Aadi/Vata 0, Madhya/Pitta 1, Antya/Kapha 2 — the zigzag of period six.
NADI = np.array([[0, 1, 2, 2, 1, 0][i % 6] for i in range(27)], dtype=np.int64)

# ── Nakshatra dispositor (Vimshottari lord), needed for the same-lord cancellations.
#    0 Ketu 1 Venus 2 Sun 3 Moon 4 Mars 5 Rahu 6 Jupiter 7 Saturn 8 Mercury
NAKLORD = np.array([i % 9 for i in range(27)], dtype=np.int64)

# ── Rajju (the five limbs), for the Tamil Rajju porutham.
#    0 Pada (feet) 1 Uru/Kati (thigh) 2 Udara/Nabhi (navel) 3 Kanta (neck) 4 Sira (head)
#    The published list is exactly the zigzag min(i mod 9, 8 - i mod 9).
RAJJU = np.array([min(i % 9, 8 - (i % 9)) for i in range(27)], dtype=np.int64)
#    ascending (aroha) or descending (avaroha) arm of the zigzag — the clash is held to be worse
#    when both partners are on the same arm
RAJJU_ARM = np.array([0 if (i % 9) <= 4 else 1 for i in range(27)], dtype=np.int64)

# ── Vedha (mutual piercing) pairs. Thirteen pairs; Chitra alone has no vedha partner.
VEDHA = np.full(27, -1, dtype=np.int64)
for _a, _b in [(0, 17), (1, 16), (2, 15), (3, 14), (4, 22), (5, 21), (6, 20), (7, 19), (8, 18),
               (9, 26), (10, 25), (11, 24), (12, 23)]:
    VEDHA[_a], VEDHA[_b] = _b, _a

# ── Sign lords, planet indices 0 Sun 1 Moon 2 Mercury 3 Mars 4 Jupiter 5 Venus 6 Saturn
SIGN_LORD = np.array([3, 5, 2, 1, 0, 2, 5, 3, 4, 6, 6, 4], dtype=np.int64)

# ── Naisargika maitri (natural friendship), Parashara's table. REL[a, b] is a's view of b:
#    1 friend, 0 neutral, -1 enemy, 2 on the diagonal. Deliberately NOT symmetric — the Moon holds
#    Mercury a friend while Mercury holds the Moon an enemy, and Jupiter holds Venus an enemy while
#    Venus holds Jupiter neutral. Graha Maitri scores the ORDERED pair, which is why.
REL = np.array([
    [2,  1,  0,  1,  1, -1, -1],   # Sun
    [1,  2,  1,  0,  0,  0,  0],   # Moon
    [1, -1,  2,  0,  0,  1,  0],   # Mercury
    [1,  1, -1,  2,  1,  0,  0],   # Mars
    [1,  1, -1,  1,  2, -1,  0],   # Jupiter
    [-1, -1,  1,  0,  0,  2,  1],  # Venus
    [-1, -1,  1, -1,  0,  1,  2],  # Saturn
], dtype=np.int64)


def _maitri_table():
    """Graha Maitri (5 points): 5 same planet or mutual friends, 4 friend+neutral, 3 mutual neutral,
    1 friend+enemy, 0.5 neutral+enemy, 0 mutual enemies."""
    M = np.zeros((7, 7))
    for a in range(7):
        for b in range(7):
            if a == b:
                M[a, b] = 5.0
                continue
            ra, rb = REL[a, b], REL[b, a]
            lo, hi = min(ra, rb), max(ra, rb)
            if lo == 1 and hi == 1:
                M[a, b] = 5.0
            elif lo == 0 and hi == 1:
                M[a, b] = 4.0
            elif lo == 0 and hi == 0:
                M[a, b] = 3.0
            elif lo == -1 and hi == 1:
                M[a, b] = 1.0
            elif lo == -1 and hi == 0:
                M[a, b] = 0.5
            else:
                M[a, b] = 0.0
    return M


MAITRI = _maitri_table()

# ── Vasya rasis, for the Tamil Vasya porutham (a SIGN list, distinct from the Ashtakoot Vashya
#    class table above): the bride's rasi should be among the signs subordinate to the groom's.
_VASYA_SETS = {0: (4, 7), 1: (3, 6), 2: (5,), 3: (7, 8), 4: (6,), 5: (2, 11), 6: (5, 9), 7: (3,),
               8: (11,), 9: (0, 10), 10: (0,), 11: (9,)}
VASYA_SIGN = np.zeros((12, 12), dtype=np.float64)
for _s, _t in _VASYA_SETS.items():
    for _u in _t:
        VASYA_SIGN[_s, _u] = 1.0

# ── Bhakoot dosha distances. Dosha when the two Moon signs stand 2/12, 5/9 or 6/8 to each other,
#    i.e. when the forward count differs by 1, 4, 5, 7, 8 or 11 signs.
BHAKOOT_BAD = np.zeros(12, dtype=bool)
BHAKOOT_BAD[[1, 4, 5, 7, 8, 11]] = True

# ── Kuja dosha: Mars in bhavas 1, 2, 4, 7, 8, 12 from the reference point.
KUJA_HOUSES = (1, 2, 4, 7, 8, 12)
#    Mars in these signs is held to raise no dosha (Mesha, Karka, Simha, Vrischika, Makara, Kumbha).
KUJA_FREE_SIGNS = np.zeros(12, dtype=bool)
KUJA_FREE_SIGNS[[0, 3, 4, 7, 9, 10]] = True
#    Mars own sign / exaltation, the narrower reading.
KUJA_OWN_SIGNS = np.zeros(12, dtype=bool)
KUJA_OWN_SIGNS[[0, 7, 9]] = True
#    House-specific sign exceptions (the parihara list): {house: signs that void the dosha}
KUJA_HOUSE_EXC = {1: (0,), 2: (2, 5), 4: (0, 7), 7: (9, 3), 8: (8, 11), 12: (1, 6)}

# ════════════════════════════════════════════════════════════════════════════════════════════════
# Small mechanics
# ════════════════════════════════════════════════════════════════════════════════════════════════


def _parts(lon):
    lon = np.mod(np.asarray(lon, dtype=np.float64), 360.0)
    return {"lon": lon, "nak": _nak(lon), "pada": _pada(lon), "rasi": _rasi(lon),
            "deg": np.mod(lon, 30.0), "nav": _navamsa(lon)}


def _vclass(p):
    c = VASHYA_BASE[p["rasi"]]
    c = np.where((p["rasi"] == 8) & (p["deg"] >= 15.0), 0, c)
    c = np.where((p["rasi"] == 9) & (p["deg"] >= 15.0), 2, c)
    return c.astype(np.int64)


def _onehot(idx, k):
    out = np.zeros((len(idx), k), dtype=np.float64)
    out[np.arange(len(idx)), np.clip(idx, 0, k - 1)] = 1.0
    return out


def _pairhot(a, b, ka, kb):
    return _onehot(a.astype(np.int64) * kb + b.astype(np.int64), ka * kb)


def _harm(idx, period, hs):
    """cos/sin of a cyclic integer index at the given harmonics."""
    th = 2.0 * np.pi * np.asarray(idx, dtype=np.float64) / float(period)
    return np.column_stack([f(h * th) for h in hs for f in (np.cos, np.sin)])


def _pack(cols):
    X = np.column_stack([np.asarray(c, dtype=np.float64).reshape(len(np.atleast_1d(c)), -1)
                         if np.asarray(c).ndim > 1 else np.asarray(c, dtype=np.float64)[:, None]
                         for c in cols])
    X = np.nan_to_num(np.ascontiguousarray(X, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    # NO VARIANCE PRUNING HERE, DELIBERATELY. This used to drop columns whose standard deviation was
    # zero in the batch being built, and that made a block's WIDTH a function of the DATA rather than
    # of the code. Two consequences, both silent: a scoring batch (one couple, or ten thousand
    # candidates sharing a fixed partner) has many constant columns, so prediction handed the model a
    # narrower and differently-ordered matrix than training did; and a full run built in row chunks
    # produced chunks of different widths that could not be concatenated. Constant columns are now
    # pruned exactly once, globally, by run.collect, which records `kept_idx` in the manifest so
    # prediction can select the same columns. Width is a function of the code alone.
    return X


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Ashtakoot / Guna Milan — the tradition's own 36-point number, computed exactly
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _ashtakoot(g, b):
    """g = the partner placed in the GROOM role, b = the BRIDE role. Returns every kuta, the 36-point
    total, the two doshas and their classical cancellations."""
    o = {}

    # 1 Varna. 1 point iff the groom's varna rank is not below the bride's.
    o["varna"] = (VARNA[g["rasi"]] >= VARNA[b["rasi"]]).astype(np.float64)

    # 2 Vashya, from the five-class table.
    cg, cb = _vclass(g), _vclass(b)
    o["vashya"] = VASHYA_TBL[cg, cb]
    o["vclass_g"], o["vclass_b"] = cg, cb

    # 3 Tara / Dina. Count inclusively from the bride's nakshatra to the groom's and back; each
    #    direction divided by nine. Even remainders (0 counted as the ninth, Parama Maitra) are
    #    auspicious and carry 1.5 points. The alternate classical reading condemns instead the
    #    3rd, 5th and 7th taras (Vipat, Pratyari, Vadha) — emitted beside it.
    cnt_bg = np.mod(g["nak"] - b["nak"], 27) + 1        # bride -> groom
    cnt_gb = np.mod(b["nak"] - g["nak"], 27) + 1        # groom -> bride
    r1, r2 = np.mod(cnt_bg, 9), np.mod(cnt_gb, 9)
    o["tara"] = 1.5 * (np.mod(r1, 2) == 0) + 1.5 * (np.mod(r2, 2) == 0)
    t1 = np.where(r1 == 0, 9, r1)
    t2 = np.where(r2 == 0, 9, r2)
    bad = np.array([3, 5, 7])
    o["tara_alt"] = 1.5 * (~np.isin(t1, bad)) + 1.5 * (~np.isin(t2, bad))
    o["cnt_bg"], o["cnt_gb"], o["tara_r1"], o["tara_r2"] = cnt_bg, cnt_gb, t1, t2

    # 4 Yoni, from the 14-animal table.
    ag, ab = ANIMAL[g["nak"]], ANIMAL[b["nak"]]
    o["yoni"] = YONI_TBL[ag, ab]
    o["yoni_enemy"] = (o["yoni"] == 0).astype(np.float64)
    #    the Tamil refinement: the male yoni should belong to the groom
    o["yoni_sex_ok"] = ((YSEX[g["nak"]] == 0) & (YSEX[b["nak"]] == 1)).astype(np.float64)

    # 5 Graha Maitri, between the lords of the two Moon signs.
    lg, lb = SIGN_LORD[g["rasi"]], SIGN_LORD[b["rasi"]]
    o["maitri"] = MAITRI[lg, lb]
    o["lord_g"], o["lord_b"] = lg, lb

    # 6 Gana.
    gg, gb_ = GANA[g["nak"]], GANA[b["nak"]]
    o["gana"] = GANA_TBL[gg, gb_]
    o["gana_asym"] = GANA_TBL_ASYM[gg, gb_]
    o["gana_g"], o["gana_b"] = gg, gb_

    # 7 Bhakoot, from the mutual sign positions.
    d = np.mod(g["rasi"] - b["rasi"], 12)
    o["bhakoot"] = np.where(BHAKOOT_BAD[d], 0.0, 7.0)
    o["bhakoot_dosha"] = BHAKOOT_BAD[d].astype(np.float64)
    o["rasi_gap"] = d
    #    cancellations (Bhakoot dosha bhanga): identical rasi lords; mutually friendly rasi lords;
    #    Graha Maitri already at its full five; a shared nakshatra dispositor; friendly navamsa lords.
    same_lord = (lg == lb)
    friend_lords = (REL[lg, lb] == 1) & (REL[lb, lg] == 1)
    full_maitri = o["maitri"] >= 5.0
    same_naklord = (NAKLORD[g["nak"]] == NAKLORD[b["nak"]])
    nlg, nlb = SIGN_LORD[g["nav"]], SIGN_LORD[b["nav"]]
    nav_friend = (nlg == nlb) | ((REL[nlg, nlb] >= 0) & (REL[nlb, nlg] >= 0))
    o["bh_c_samelord"] = same_lord.astype(np.float64)
    o["bh_c_friendlords"] = friend_lords.astype(np.float64)
    o["bh_c_fullmaitri"] = full_maitri.astype(np.float64)
    o["bh_c_naklord"] = same_naklord.astype(np.float64)
    o["bh_c_navamsa"] = nav_friend.astype(np.float64)
    bh_cancel = same_lord | friend_lords | full_maitri | same_naklord | nav_friend
    o["bh_cancel"] = (bh_cancel & BHAKOOT_BAD[d]).astype(np.float64)
    o["bhakoot_net"] = np.where(BHAKOOT_BAD[d] & bh_cancel, 7.0, o["bhakoot"])

    # 8 Nadi. Same nadi is the dosha; different nadi carries all eight points.
    same_nadi = (NADI[g["nak"]] == NADI[b["nak"]])
    o["nadi"] = np.where(same_nadi, 0.0, 8.0)
    o["nadi_dosha"] = same_nadi.astype(np.float64)
    #    cancellations: the same nakshatra but different padas; different nakshatras inside the same
    #    rasi; a shared nakshatra dispositor with different nakshatras.
    same_nak = (g["nak"] == b["nak"])
    c1 = same_nak & (g["pada"] != b["pada"])
    c2 = (g["rasi"] == b["rasi"]) & (~same_nak)
    c3 = same_naklord & (~same_nak)
    o["nd_c_pada"] = c1.astype(np.float64)
    o["nd_c_samerasi"] = c2.astype(np.float64)
    o["nd_c_naklord"] = c3.astype(np.float64)
    nd_cancel = c1 | c2 | c3
    o["nd_cancel"] = (nd_cancel & same_nadi).astype(np.float64)
    o["nadi_net"] = np.where(same_nadi & nd_cancel, 8.0, o["nadi"])

    o["total"] = (o["varna"] + o["vashya"] + o["tara"] + o["yoni"] + o["maitri"] + o["gana"]
                  + o["bhakoot"] + o["nadi"])
    o["total_alt"] = (o["varna"] + o["vashya"] + o["tara_alt"] + o["yoni"] + o["maitri"]
                      + o["gana_asym"] + o["bhakoot"] + o["nadi"])
    o["total_net"] = (o["varna"] + o["vashya"] + o["tara"] + o["yoni"] + o["maitri"] + o["gana"]
                      + o["bhakoot_net"] + o["nadi_net"])
    o["same_nak"] = same_nak.astype(np.float64)
    o["same_rasi"] = (g["rasi"] == b["rasi"]).astype(np.float64)
    o["same_pada"] = (same_nak & (g["pada"] == b["pada"])).astype(np.float64)
    return o


# ════════════════════════════════════════════════════════════════════════════════════════════════
# The ten Tamil Poruthams
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _poruthams(g, b):
    """g = groom role, b = bride role. Each porutham as its own feature, then the count satisfied."""
    o = {}
    cnt = np.mod(g["nak"] - b["nak"], 27) + 1          # count from the bride's star to the groom's
    o["count_bg"] = cnt

    # 1 Dina — remainder of the count over nine must be 2, 4, 6, 8 or 0.
    r = np.mod(cnt, 9)
    o["dina"] = np.isin(r, np.array([0, 2, 4, 6, 8])).astype(np.float64)

    # 2 Gana — the Tamil grading of the Deva/Manushya/Rakshasa pair.
    o["gana"] = GANA_PORU[GANA[g["nak"]], GANA[b["nak"]]]

    # 3 Mahendra — the count must be 4, 7, 10, 13, 16, 19, 22 or 25 (progeny and longevity).
    o["mahendra"] = np.isin(cnt, np.array([4, 7, 10, 13, 16, 19, 22, 25])).astype(np.float64)

    # 4 Stree Deergha — the count must exceed nine (the wife's longevity). The laxer reading in
    #    several panchangams is "more than seven"; both are emitted.
    o["stree"] = (cnt > 9).astype(np.float64)
    o["stree7"] = (cnt > 7).astype(np.float64)

    # 5 Yoni — the animal pair must be its own or friendly (table value 3 or 4).
    o["yoni"] = (YONI_TBL[ANIMAL[g["nak"]], ANIMAL[b["nak"]]] >= 3.0).astype(np.float64)

    # 6 Rasi — the groom's rasi counted from the bride's should fall in the 7th to the 12th; the same
    #    rasi is admitted when the stars differ.
    dr = np.mod(g["rasi"] - b["rasi"], 12) + 1
    o["rasi"] = ((dr >= 7) | ((dr == 1) & (g["nak"] != b["nak"]))).astype(np.float64)
    o["rasi_strict"] = (dr >= 7).astype(np.float64)
    o["rasi_count"] = dr

    # 7 Rasyadhipathi — the lords of the two rasis must be the same or friendly; enmity voids it.
    m = MAITRI[SIGN_LORD[g["rasi"]], SIGN_LORD[b["rasi"]]]
    o["rasyadhipathi"] = np.where(m >= 4.0, 1.0, np.where(m >= 3.0, 0.5, 0.0))

    # 8 Vasya — the bride's rasi must be among the signs subordinate to the groom's.
    o["vasya"] = VASYA_SIGN[g["rasi"], b["rasi"]]

    # 9 Rajju — the two stars must NOT share a limb. Same limb is the Rajju clash; the texts hold it
    #    worse when both also sit on the same (ascending or descending) arm of the zigzag.
    same_rajju = (RAJJU[g["nak"]] == RAJJU[b["nak"]])
    o["rajju"] = (~same_rajju).astype(np.float64)
    o["rajju_same_arm"] = (same_rajju & (RAJJU_ARM[g["nak"]] == RAJJU_ARM[b["nak"]])).astype(np.float64)
    o["rajju_limb_g"], o["rajju_limb_b"] = RAJJU[g["nak"]], RAJJU[b["nak"]]
    #    the severity ladder: feet 1 (wandering) ... head 5 (widowhood), 0 when there is no clash
    o["rajju_severity"] = np.where(same_rajju, RAJJU[g["nak"]] + 1.0, 0.0)

    # 10 Vedha — the two stars must not be a mutually piercing pair.
    o["vedha"] = (VEDHA[g["nak"]] != b["nak"]).astype(np.float64)

    o["count_satisfied"] = (o["dina"] + (o["gana"] >= 1.0) + o["mahendra"] + o["stree"] + o["yoni"]
                            + o["rasi"] + (o["rasyadhipathi"] >= 1.0) + o["vasya"] + o["rajju"]
                            + o["vedha"]).astype(np.float64)
    o["count_graded"] = (o["dina"] + o["gana"] + o["mahendra"] + o["stree"] + o["yoni"] + o["rasi"]
                         + o["rasyadhipathi"] + o["vasya"] + o["rajju"] + o["vedha"])
    return o


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Kuja / Mangal dosha
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _kuja(sid, E, slot, ref_body):
    """Kuja dosha for one partner, reckoned from `ref_body` as the first bhava.

    The Lagna is not computable from a date alone, so the reference is one of the three the texts
    themselves prescribe as alternatives: the Moon (Chandra lagna), the Sun (Surya lagna), or Venus.
    Houses are whole-sign counts from that reference, which is the Vedic bhava convention.
    """
    I = E.IDX
    mars = _rasi(sid[slot, I["Mars"]])
    ref = _rasi(sid[slot, I[ref_body]])
    jup = _rasi(sid[slot, I["Jupiter"]])
    sat = _rasi(sid[slot, I["Saturn"]])
    moon = _rasi(sid[slot, I["Moon"]])
    rahu = _rasi(sid[slot, I["TrueNode"]])
    house = np.mod(mars - ref, 12) + 1

    dosha = np.isin(house, np.array(KUJA_HOUSES))

    # ── the parihara (cancellation) list ────────────────────────────────────────────────────────
    free_sign = KUJA_FREE_SIGNS[mars]                  # Mars in Aries/Cancer/Leo/Scorpio/Cap/Aqu
    own_sign = KUJA_OWN_SIGNS[mars]                    # own or exalted, the narrow reading
    house_exc = np.zeros_like(dosha)
    for h, signs in KUJA_HOUSE_EXC.items():
        house_exc |= (house == h) & np.isin(mars, np.array(signs))
    conj_jup = (mars == jup)
    asp_jup = conj_jup | np.isin(np.mod(mars - jup, 12) + 1, np.array([5, 7, 9]))
    conj_sat = (mars == sat)
    asp_sat = conj_sat | np.isin(np.mod(mars - sat, 12) + 1, np.array([3, 7, 10]))
    conj_moon = (mars == moon)
    conj_rahu = (mars == rahu)
    cancel = free_sign | house_exc | asp_jup | conj_moon
    return {"house": house, "dosha": dosha, "free_sign": free_sign, "own_sign": own_sign,
            "house_exc": house_exc, "conj_jup": conj_jup, "asp_jup": asp_jup,
            "conj_sat": conj_sat, "asp_sat": asp_sat, "conj_moon": conj_moon,
            "conj_rahu": conj_rahu, "cancel": cancel,
            "net": dosha & (~cancel)}


# ════════════════════════════════════════════════════════════════════════════════════════════════
# build
# ════════════════════════════════════════════════════════════════════════════════════════════════
AYA_MAIN = ["Lahiri", "Raman", "Krishnamurti", "True Citra"]
AYA_SPREAD = ["Lahiri", "Raman", "Krishnamurti", "True Citra", "Fagan-Bradley", "Yukteshwar",
              "Suryasiddhanta"]
AYA_PORU = ["Lahiri", "Krishnamurti", "True Citra"]

_KUTAS8 = ("varna", "vashya", "tara", "yoni", "maitri", "gana", "bhakoot", "nadi")
_PORU10 = ("dina", "gana", "mahendra", "stree", "yoni", "rasi", "rasyadhipathi", "vasya", "rajju",
           "vedha")


def _moons(E, aya):
    sid = E.sidereal(aya)
    return sid, _parts(sid[0, E.IDX["Moon"]]), _parts(sid[1, E.IDX["Moon"]])


def _ashtakoot_block(O, Y):
    """Both role orderings of the 36-point system, with every dosha and cancellation."""
    a = _ashtakoot(O, Y)          # older in the groom role
    c = _ashtakoot(Y, O)          # younger in the groom role
    cols = []
    for k in _KUTAS8:
        cols += [a[k], c[k]]
    cols += [a["tara_alt"], a["gana_asym"], c["gana_asym"]]
    cols += [a["total"], c["total"], 0.5 * (a["total"] + c["total"]),
             a["total_alt"], c["total_alt"], a["total_net"], c["total_net"]]
    tm = 0.5 * (a["total"] + c["total"])
    for thr in (18.0, 21.0, 26.0, 32.0):
        cols.append((tm >= thr).astype(np.float64))
    cols += [a["bhakoot_dosha"], a["bh_cancel"], a["bh_c_samelord"], a["bh_c_friendlords"],
             a["bh_c_fullmaitri"], a["bh_c_naklord"], a["bh_c_navamsa"]]
    cols += [a["nadi_dosha"], a["nd_cancel"], a["nd_c_pada"], a["nd_c_samerasi"], a["nd_c_naklord"]]
    cols += [a["yoni_enemy"], a["yoni_sex_ok"], c["yoni_sex_ok"],
             a["same_nak"], a["same_rasi"], a["same_pada"]]
    cols += [a["cnt_bg"] / 27.0, a["cnt_gb"] / 27.0, a["tara_r1"] / 9.0, a["tara_r2"] / 9.0,
             a["rasi_gap"] / 12.0]
    return _pack(cols)


def _poru_block(O, Y):
    a = _poruthams(O, Y)
    c = _poruthams(Y, O)
    cols = []
    for k in _PORU10:
        cols += [a[k], c[k]]
    cols += [a["stree7"], c["stree7"], a["rasi_strict"], c["rasi_strict"]]
    cols += [a["count_satisfied"], c["count_satisfied"],
             0.5 * (a["count_satisfied"] + c["count_satisfied"]),
             np.abs(a["count_satisfied"] - c["count_satisfied"]),
             a["count_graded"], c["count_graded"]]
    for thr in (5.0, 6.0, 7.0, 8.0):
        cols.append((np.maximum(a["count_satisfied"], c["count_satisfied"]) >= thr).astype(np.float64))
    cols += [a["rajju_same_arm"], a["rajju_severity"], a["rajju_limb_g"] / 4.0,
             a["rajju_limb_b"] / 4.0, (a["rajju_limb_g"] == a["rajju_limb_b"]).astype(np.float64)]
    cols += [a["count_bg"] / 27.0, c["count_bg"] / 27.0, a["rasi_count"] / 12.0,
             c["rasi_count"] / 12.0]
    return _pack(cols)


def build(E):
    out = {}
    n = E.n
    tag = "vm"

    # ── the 36-point system under four ayanamsas, each its own block ─────────────────────────────
    moons = {}
    for aya in sorted(set(AYA_MAIN + AYA_SPREAD + AYA_PORU)):
        moons[aya] = _moons(E, aya)
    for aya in AYA_MAIN:
        _, O, Y = moons[aya]
        out[f"{tag}: ashtakoot 36pt ({aya})"] = _ashtakoot_block(O, Y)

    # ── the ten poruthams under three ayanamsas ─────────────────────────────────────────────────
    for aya in AYA_PORU:
        _, O, Y = moons[aya]
        out[f"{tag}: ten poruthams ({aya})"] = _poru_block(O, Y)

    # ── how much the doctrine's own verdict depends on which ayanamsa you hold ───────────────────
    tot, poru, kv, bh, nd, sn = [], [], {k: [] for k in _KUTAS8}, [], [], []
    ref_nak = None
    agree = np.zeros(n)
    for aya in AYA_SPREAD:
        _, O, Y = moons[aya]
        a, c = _ashtakoot(O, Y), _ashtakoot(Y, O)
        tot.append(0.5 * (a["total"] + c["total"]))
        for k in _KUTAS8:
            kv[k].append(0.5 * (a[k] + c[k]))
        bh.append(a["bhakoot_dosha"])
        nd.append(a["nadi_dosha"])
        sn.append(a["same_nak"])
        p, q = _poruthams(O, Y), _poruthams(Y, O)
        poru.append(0.5 * (p["count_satisfied"] + q["count_satisfied"]))
        if ref_nak is None:
            ref_nak = (O["nak"], Y["nak"])
        agree += ((O["nak"] == ref_nak[0]) & (Y["nak"] == ref_nak[1])).astype(np.float64)
    T = np.array(tot)
    P = np.array(poru)
    cols = [T.mean(0), T.std(0), T.min(0), T.max(0), T.max(0) - T.min(0),
            P.mean(0), P.std(0), P.min(0), P.max(0),
            np.array(bh).mean(0), np.array(nd).mean(0), np.array(sn).mean(0),
            agree / len(AYA_SPREAD)]
    for k in _KUTAS8:
        A = np.array(kv[k])
        cols += [A.mean(0), A.std(0)]
    out[f"{tag}: ashtakoot ayanamsa spread (7 modes)"] = _pack(cols)

    # ── the same doctrine as an orb kernel over the +-6deg noon-Moon error ───────────────────────
    #    A nakshatra is 13d20'; the noon Moon is uncertain by ~+-6d, so the hard bin is a coin flip.
    #    This block reports the EXPECTED kuta scores under a Gaussian smear of that width plus their
    #    spread, which is the tradition's own number carried through the actual measurement error.
    _, O0, Y0 = moons["Lahiri"]
    offs = np.linspace(-7.5, 7.5, 11)
    w = np.exp(-0.5 * (offs / 3.5) ** 2)
    w = w / w.sum()
    acc = {k: np.zeros(n) for k in _KUTAS8}
    acc2 = {k: np.zeros(n) for k in _KUTAS8}
    accT = np.zeros(n); accT2 = np.zeros(n)
    accP = np.zeros(n); accP2 = np.zeros(n)
    accB = np.zeros(n); accN = np.zeros(n); accR = np.zeros(n); accV = np.zeros(n)
    for i, do in enumerate(offs):
        Oi = _parts(O0["lon"] + do)
        for j, dy in enumerate(offs):
            ww = w[i] * w[j]
            Yj = _parts(Y0["lon"] + dy)
            a, c = _ashtakoot(Oi, Yj), _ashtakoot(Yj, Oi)
            for k in _KUTAS8:
                v = 0.5 * (a[k] + c[k])
                acc[k] += ww * v
                acc2[k] += ww * v * v
            t = 0.5 * (a["total"] + c["total"])
            accT += ww * t; accT2 += ww * t * t
            p, q = _poruthams(Oi, Yj), _poruthams(Yj, Oi)
            pc = 0.5 * (p["count_satisfied"] + q["count_satisfied"])
            accP += ww * pc; accP2 += ww * pc * pc
            accB += ww * a["bhakoot_dosha"]
            accN += ww * a["nadi_dosha"]
            accR += ww * (1.0 - p["rajju"])
            accV += ww * (1.0 - p["vedha"])
    cols = [accT, np.sqrt(np.maximum(accT2 - accT ** 2, 0.0)),
            accP, np.sqrt(np.maximum(accP2 - accP ** 2, 0.0)),
            accB, accN, accR, accV]
    for k in _KUTAS8:
        cols += [acc[k], np.sqrt(np.maximum(acc2[k] - acc[k] ** 2, 0.0))]
    out[f"{tag}: ashtakoot under the +-6deg moon smear"] = _pack(cols)

    # ── Kuja / Mangal dosha, from the three documented reference points ──────────────────────────
    sidL = moons["Lahiri"][0]
    KEYS = ("dosha", "net", "free_sign", "own_sign", "house_exc", "conj_jup", "asp_jup",
            "conj_sat", "asp_sat", "conj_moon", "conj_rahu", "cancel")
    cols = []
    for ref in ("Moon", "Sun", "Venus"):
        ko = _kuja(sidL, E, 0, ref)
        ky = _kuja(sidL, E, 1, ref)
        for k in KEYS:
            cols += [ko[k].astype(np.float64), ky[k].astype(np.float64)]
        both = ko["dosha"] & ky["dosha"]
        cols += [both.astype(np.float64),                              # dosha samya — it cancels
                 (ko["dosha"] ^ ky["dosha"]).astype(np.float64),       # one-sided, the feared case
                 (ko["dosha"] | ky["dosha"]).astype(np.float64),
                 (ko["net"] & ky["net"]).astype(np.float64),
                 (ko["net"] ^ ky["net"]).astype(np.float64),
                 ko["house"] / 12.0, ky["house"] / 12.0]
        cols.append(_onehot(np.mod(ko["house"] - 1, 12), 12))
        cols.append(_onehot(np.mod(ky["house"] - 1, 12), 12))
    #    boundary robustness: in what fraction of seven ayanamsas does the dosha survive at all
    for ref in ("Moon", "Sun", "Venus"):
        fo = np.zeros(n); fy = np.zeros(n)
        for aya in AYA_SPREAD:
            s = moons[aya][0]
            fo += _kuja(s, E, 0, ref)["dosha"].astype(np.float64)
            fy += _kuja(s, E, 1, ref)["dosha"].astype(np.float64)
        cols += [fo / len(AYA_SPREAD), fy / len(AYA_SPREAD)]
    #    Mars relative to the partner's Mars and Venus — the "kuja to kuja" reading
    mo, my = _rasi(sidL[0, E.IDX["Mars"]]), _rasi(sidL[1, E.IDX["Mars"]])
    vo, vy = _rasi(sidL[0, E.IDX["Venus"]]), _rasi(sidL[1, E.IDX["Venus"]])
    cols += [np.mod(mo - my, 12) / 12.0, (mo == my).astype(np.float64),
             (np.mod(mo - my, 12) == 6).astype(np.float64),
             np.mod(mo - vy, 12) / 12.0, np.mod(my - vo, 12) / 12.0]
    cols.append(_harm(np.mod(mo - my, 12), 12, (1, 2, 3)))
    out[f"{tag}: kuja dosha (moon/sun/venus lagna proxies)"] = _pack(cols)

    # ── the nakshatra pair in LOW-RANK form, not a 729-column one-hot ────────────────────────────
    _, O, Y = moons["Lahiri"]
    a, c = _ashtakoot(O, Y), _ashtakoot(Y, O)
    p, q = _poruthams(O, Y), _poruthams(Y, O)
    dn = np.mod(Y["nak"] - O["nak"], 27)
    dr = np.mod(Y["rasi"] - O["rasi"], 12)
    dp = np.mod(Y["pada"] - O["pada"], 4)
    cols = [_harm(dn, 27, (1, 2, 3, 4, 5, 6)),
            _harm(dr, 12, (1, 2, 3, 4, 5, 6)),
            _harm(O["nak"], 27, (1, 2, 3)), _harm(Y["nak"], 27, (1, 2, 3)),
            _harm(O["rasi"], 12, (1, 2, 3)), _harm(Y["rasi"], 12, (1, 2, 3)),
            _onehot(dp, 4),
            E.sep(O["lon"], Y["lon"]) / 180.0,
            np.cos(np.deg2rad(Y["lon"] - O["lon"])), np.sin(np.deg2rad(Y["lon"] - O["lon"])),
            np.cos(np.deg2rad(2 * (Y["lon"] - O["lon"]))),
            np.cos(np.deg2rad(3 * (Y["lon"] - O["lon"]))),
            np.cos(np.deg2rad(4 * (Y["lon"] - O["lon"]))),
            _harm(np.mod(O["lon"], NAKW) / NAKW * 27, 27, (1,)),
            _harm(np.mod(Y["lon"], NAKW) / NAKW * 27, 27, (1,)),
            a["cnt_bg"] / 27.0, a["cnt_gb"] / 27.0]
    #    the kuta vector itself is the compact pair encoding the tradition offers
    for k in _KUTAS8:
        cols += [a[k], c[k]]
    cols += [a["total"], c["total"], p["count_satisfied"], q["count_satisfied"],
             a["bhakoot_dosha"], a["nadi_dosha"], 1.0 - p["rajju"], 1.0 - p["vedha"]]
    out[f"{tag}: nakshatra pair low-rank + kuta vector"] = _pack(cols)

    # ── discrete bins: the nakshatra, rasi, pada and navamsa of each Moon ────────────────────────
    cols = [_onehot(O["nak"], 27), _onehot(Y["nak"], 27),
            _onehot(O["rasi"], 12), _onehot(Y["rasi"], 12),
            _onehot(O["pada"], 4), _onehot(Y["pada"], 4),
            _onehot(O["nav"], 12), _onehot(Y["nav"], 12)]
    out[f"{tag}: moon nakshatra/rasi/pada one-hot"] = _pack(cols)

    # ── the pair of every kuta CATEGORY, one-hot, so a model can learn any variant table ─────────
    cols = [_pairhot(GANA[O["nak"]], GANA[Y["nak"]], 3, 3),
            _pairhot(NADI[O["nak"]], NADI[Y["nak"]], 3, 3),
            _pairhot(VARNA[O["rasi"]] - 1, VARNA[Y["rasi"]] - 1, 4, 4),
            _pairhot(_vclass(O), _vclass(Y), 5, 5),
            _pairhot(RAJJU[O["nak"]], RAJJU[Y["nak"]], 5, 5),
            _onehot(dr, 12),
            _onehot(np.mod(a["tara_r1"] - 1, 9), 9), _onehot(np.mod(a["tara_r2"] - 1, 9), 9),
            _onehot(ANIMAL[O["nak"]], 14), _onehot(ANIMAL[Y["nak"]], 14),
            _onehot(a["yoni"].astype(np.int64), 5),
            _pairhot(YSEX[O["nak"]], YSEX[Y["nak"]], 2, 2),
            _pairhot(NAKLORD[O["nak"]], NAKLORD[Y["nak"]], 9, 9),
            _pairhot(SIGN_LORD[O["rasi"]], SIGN_LORD[Y["rasi"]], 7, 7),
            _pairhot(SIGN_LORD[O["nav"]], SIGN_LORD[Y["nav"]], 7, 7)]
    out[f"{tag}: kuta category pairs one-hot"] = _pack(cols)

    # ── the aggregate verdict a matchmaker actually reports ──────────────────────────────────────
    tm = 0.5 * (a["total"] + c["total"])
    pm = 0.5 * (p["count_satisfied"] + q["count_satisfied"])
    cols = [tm, tm / 36.0, _onehot(np.clip(np.floor(tm / 4.0).astype(np.int64), 0, 8), 9),
            pm, _onehot(np.clip(pm.astype(np.int64), 0, 10), 11),
            (tm >= 18.0).astype(np.float64), (pm >= 5.0).astype(np.float64),
            ((tm >= 18.0) & (pm >= 5.0)).astype(np.float64),
            a["bhakoot_dosha"] + a["nadi_dosha"],
            a["bhakoot_dosha"] * (1.0 - a["bh_cancel"]) + a["nadi_dosha"] * (1.0 - a["nd_cancel"]),
            (1.0 - p["rajju"]) + (1.0 - p["vedha"]) + a["yoni_enemy"],
            tm * (1.0 - a["bhakoot_dosha"]), tm * (1.0 - a["nadi_dosha"]),
            0.5 * (a["total_net"] + c["total_net"]), pm * tm / 36.0]
    out[f"{tag}: guna milan verdict (total, grade, doshas)"] = _pack(cols)

    for k, v in out.items():
        assert v.shape[0] == n, (k, v.shape)
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
# self-test
# ════════════════════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import time

    # doctrine sanity checks that would catch a mistyped table
    assert (np.bincount(GANA, minlength=3) == 9).all(), "each gana holds nine nakshatras"
    assert (np.bincount(NADI, minlength=3) == 9).all(), "each nadi holds nine nakshatras"
    assert (np.bincount(RAJJU, minlength=5) == [6, 6, 6, 6, 3]).all(), "rajju limb sizes"
    assert np.allclose(YONI_TBL, YONI_TBL.T), "the yoni table is symmetric"
    assert (np.diag(YONI_TBL) == 4).all(), "same yoni scores four"
    for _x, _y in [(0, 8), (1, 13), (2, 11), (3, 12), (4, 10), (5, 6), (7, 9)]:
        assert YONI_TBL[_x, _y] == 0, "the seven sworn-enemy yoni pairs score zero"
    assert np.bincount(ANIMAL, minlength=14).tolist() == [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2]
    assert (VEDHA[VEDHA >= 0] >= 0).all() and (VEDHA == -1).sum() == 1, "one star has no vedha"
    assert np.allclose(VASHYA_TBL, VASHYA_TBL.T), "vashya table symmetric as tabulated"
    # Moon holds Mercury a friend, Mercury holds the Moon an enemy -> friend+enemy = 1 point.
    # Moon/Mars is neutral+friend = 4. Sun/Saturn is mutual enmity = 0.
    assert MAITRI[1, 2] == 1.0 and MAITRI[1, 3] == 4.0 and MAITRI[0, 6] == 0.0, "graha maitri"
    assert _navamsa(np.array([0.0, 30.0, 60.0, 90.0])).tolist() == [0, 9, 6, 3], "navamsa starts"
    assert _pada(np.array([0.0, 3.34, 6.67, 10.01])).tolist() == [0, 1, 2, 3], "pada boundaries"
    assert _nak(np.array([0.0, 13.34, 26.67, 359.99])).tolist() == [0, 1, 2, 26], "nakshatra bounds"
    #   a hand-worked pair: two Moons in Ashwini 2deg. Varna 1 (equal), Vashya 2 (same class),
    #   Tara 0 (Janma tara, odd remainder, both ways), Yoni 4 (same), Maitri 5 (one lord),
    #   Gana 6 (same), Bhakoot 7 (same rasi is never 2-12/5-9/6-8), Nadi 0 (same nadi is the dosha,
    #   and the same pada leaves it uncancelled) = 25 of 36, which is what a panchangam prints.
    _w = _parts(np.array([2.0]))
    _a = _ashtakoot(_w, _w)
    assert [float(_a[k][0]) for k in _KUTAS8] == [1, 2, 0, 4, 5, 6, 7, 0], "hand-worked ashtakoot"
    assert float(_a["total"][0]) == 25.0 and float(_a["tara_alt"][0]) == 3.0
    assert float(_poruthams(_w, _w)["rajju"][0]) == 0.0, "identical stars share a rajju limb"

    from core import load
    from evalx import quick

    t0 = time.time()
    E = load()
    B = build(E)
    print(f"TRADITION  {TRADITION}")
    print(f"built {len(B)} blocks in {time.time() - t0:.1f}s over {E.n:,} couples\n")

    bad = 0
    rows = []
    for name, X in B.items():
        try:
            assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
            assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
            assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
            assert np.isfinite(X).all(), f"{name}: non-finite value"
            assert X.std(axis=0).max() > 0, f"{name}: all-constant block"
        except AssertionError as e:
            print("FAIL", e)
            bad += 1
            continue
        acc, auc = quick(E, X)
        rows.append((name, X.shape[1], acc, auc))
        print(f"  {name:<52} {X.shape[1]:>4} cols   acc {100*acc:5.2f}%   AUC {auc:.4f}")

    tot = sum(r[1] for r in rows)
    print(f"\n{len(rows)} blocks, {tot} columns total")
    if bad:
        print(f"{bad} block(s) failed")
        sys.exit(1)
    print("OK")
