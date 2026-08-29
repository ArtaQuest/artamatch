"""v36_worldmatch.py — the world's named MARRIAGE-MATCHING algorithms the bank did not have.

Everything already in the bank is an astrology or numerology that a matchmaker *applies* to a couple.
This module adds the systems that were built to answer the marriage question directly — the ones whose
own literature is about whether two people should marry — plus the divinatory pair-forming techniques
(a hexagram cast by the couple, a geomantic Judge) that only exist for two charts at once.

  A. JAVANESE WETON / PRIMBON JODOH   Indonesia's marriage calculation, and by headcount the most-used
     on earth. Each birthday carries a neptu — a number from the seven-day week plus a second from the
     five-day pasaran week. The couple's two neptu are added and the total read off named tables:
     Pegat, Ratu, Jodoh, Topo, Tinari, Padu, Sujanan, Pesthi.
  B. BALINESE PAWUKON                 the 210-day calendar in which ten week-cycles of different
     lengths run at once (1,2,3,4,5,6,7,8,9,10 days) across thirty named wuku. Anchored on Galungan.
  C. THE TEN PORUTHAM                 the Tamil/Sinhala marriage test, which is NOT Ashtakoota: Dina,
     Mahendra, Stree-Deergha, Vedha, Rasyadhipathi and Rajju are counts between the two birth stars.
  D. THE SIX CHINESE RELATIONS        the bank had San He, Liu He, Liu Chong and Liu Hai. This adds the
     two that were missing — Xiang Xing (the three punishments and the four self-punishments) and
     Xiang Po (destruction) — and the heavenly-stem combinations and clashes.
  E. KOREAN GUNGHAP                   the outer reading (animal sign) and the inner reading (napeum
     element of the two pillars), which is the form the verdict is actually delivered in.
  F. BURMESE MAHABOTE                 the eight houses, from birth weekday against the Burmese year.
  G. THE COUPLE'S HEXAGRAM            plum-blossom I Ching: his number makes the upper trigram, hers the
     lower, so the hexagram exists only for the pair. Its nuclear hexagram and the marriage hexagrams
     (31 Xian, 32 Heng, 37 Jiaren, 54 Guimei) are read as themselves.
  H. THE GEOMANTIC JUDGE              ilm al-raml: two figures are combined by adding their lines, which
     is what a Judge is. The Judge and the Reconciler are functions of both births and nothing else.
  I. BIORHYTHM                        the 23/28/33-day cycles, whose only published use is compatibility.
  J. HELLENISTIC DEGREE TECHNIQUES    Sabian symbols, dodekatemoria (the 2.5-degree twelfth) and
     monomoiria (the degree ruler) — three ways antiquity read a single degree, paired.
  K. KABBALAH                         the 72 Names wheel (72 x 5 degrees) and the Sefer Yetzirah letters
     for sign, planet and element.
  L. NORSE RUNIC HALF-MONTHS          the twenty-four Elder Futhark runes over the year.
  M. EGYPTIAN (NILE) ZODIAC           the twelve deities, whose date ranges are famously discontinuous.
  N. AZTEC TONALPOHUALLI              the 260-day count in its Aztec form, on the Caso correlation, with
     the thirteen Lords of the Day the Maya version does not carry.
  O. PAPASAMYA                        the Vedic balance of malefic affliction — not who is afflicted but
     whether the two are afflicted equally, which is the whole test.

Every statement uses BOTH dates. build(df, Z, split, exclude, min_support) -> (X, names).
"""
import numpy as np
import pandas as pd

SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}

# ---- A. Javanese ----------------------------------------------------------------------------
DINA = ["Senin", "Selasa", "Rebo", "Kemis", "Jemuwah", "Setu", "Ahad"]      # jdn%7 == 0 is Monday
DINA_NEPTU = np.array([4, 3, 7, 8, 6, 9, 5])                                # same order
PASARAN = ["Legi", "Pahing", "Pon", "Wage", "Kliwon"]
PASARAN_NEPTU = np.array([5, 9, 7, 4, 8])
JODOH7 = ["Pegat", "Ratu", "Jodoh", "Topo", "Tinari", "Padu", "Sujanan"]
JODOH8 = ["Pesthi", "Pegat", "Ratu", "Jodoh", "Topo", "Tinari", "Padu", "Sujanan"]
PANCASUDA = ["WasesaSegara", "TunggakSemi", "SatriaWibawa", "SumurSinaba", "SatriaWirang",
             "BumiKepetak", "LebuKatiupAngin"]

# ---- B. Balinese ----------------------------------------------------------------------------
WUKU = ["Sinta", "Landep", "Ukir", "Kulantir", "Tolu", "Gumbreg", "Wariga", "Warigadian",
        "Julungwangi", "Sungsang", "Dungulan", "Kuningan", "Langkir", "Medangsia", "Pujut",
        "Pahang", "Krulut", "Merakih", "Tambir", "Medangkungan", "Matal", "Uye", "Menail",
        "Prangbakat", "Bala", "Ugu", "Wayang", "Kelawu", "Dukut", "Watugunung"]
TRIWARA = ["Pasah", "Beteng", "Kajeng"]
CATURWARA = ["Sri", "Laba", "Jaya", "Menala"]
SADWARA = ["Tungleh", "Aryang", "Urukung", "Paniron", "Was", "Maulu"]
ASTAWARA = ["Sri", "Indra", "Guru", "Yama", "Ludra", "Brahma", "Kala", "Uma"]
SANGAWARA = ["Dangu", "Jangur", "Gigis", "Nohan", "Ogan", "Erangan", "Urungan", "Tulus", "Dadi"]
DASAWARA = ["Pandita", "Pati", "Suka", "Duka", "Sri", "Manuh", "Manusa", "Raja", "Dewa", "Raksasa"]

# ---- C. nakshatra ---------------------------------------------------------------------------
NAK = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya",
       "Ashlesha", "Magha", "PurvaPhalguni", "UttaraPhalguni", "Hasta", "Chitra", "Swati",
       "Vishakha", "Anuradha", "Jyeshtha", "Mula", "PurvaAshadha", "UttaraAshadha", "Shravana",
       "Dhanishta", "Shatabhisha", "PurvaBhadrapada", "UttaraBhadrapada", "Revati"]
VEDHA = {1: 18, 2: 17, 3: 16, 4: 15, 5: 23, 6: 22, 7: 21, 8: 20, 9: 19,
         10: 27, 11: 26, 12: 25, 13: 24}                      # 1-based; Chitra's partner is Abhijit
VEDHA = {**VEDHA, **{v: k for k, v in VEDHA.items()}}
MAHENDRA_OK = {4, 7, 10, 13, 16, 19, 22, 25}
RASI_LORD = ["mars", "venus", "mercury", "moon", "sun", "mercury",
             "venus", "mars", "jupiter", "saturn", "saturn", "jupiter"]
FRIENDS = {"sun": {"moon", "mars", "jupiter"}, "moon": {"sun", "mercury"},
           "mars": {"sun", "moon", "jupiter"}, "mercury": {"sun", "venus"},
           "jupiter": {"sun", "moon", "mars"}, "venus": {"mercury", "saturn"},
           "saturn": {"mercury", "venus"}}

# ---- D/E. Chinese and Korean ----------------------------------------------------------------
BRANCH = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
ANIMAL = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster",
          "Dog", "Pig"]
STEM = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
XING3 = [{2, 5, 8}, {1, 10, 7}]                    # Yin-Si-Shen ; Chou-Xu-Wei
XING2 = {(0, 3), (3, 0)}                           # Zi-Mao, the rude punishment
XING_SELF = {4, 6, 9, 11}                          # Chen Wu You Hai punish themselves
PO = {(0, 9), (6, 3), (1, 4), (7, 10), (2, 11), (8, 5)}
PO = PO | {(b, a) for a, b in PO}
STEM_HE = {(0, 5), (1, 6), (2, 7), (3, 8), (4, 9)}
STEM_HE = STEM_HE | {(b, a) for a, b in STEM_HE}
NAYIN5 = ["Metal", "Water", "Wood", "Fire", "Earth"]
GEN = {"Wood": "Fire", "Fire": "Earth", "Earth": "Metal", "Metal": "Water", "Water": "Wood"}
CTL = {"Wood": "Earth", "Earth": "Water", "Water": "Fire", "Fire": "Metal", "Metal": "Wood"}

# ---- F. Burmese -----------------------------------------------------------------------------
MAHABOTE = ["Binga", "Ahtun", "Yaza", "Adipati", "Marana", "Thike", "Puti"]

# ---- G. I Ching -----------------------------------------------------------------------------
TRIGRAM = ["Qian", "Dui", "Li", "Zhen", "Xun", "Kan", "Gen", "Kun"]        # the Fu Xi (xiantian) order
TRI_BITS = [7, 6, 5, 4, 3, 2, 1, 0]                                        # bottom line is bit 0
KINGWEN = [
    [1, 43, 14, 34, 9, 5, 26, 11], [10, 58, 38, 54, 61, 60, 41, 19],
    [13, 49, 30, 55, 37, 63, 22, 36], [25, 17, 21, 51, 42, 3, 27, 24],
    [44, 28, 50, 32, 57, 48, 18, 46], [6, 47, 64, 40, 59, 29, 4, 7],
    [33, 31, 56, 62, 53, 39, 52, 15], [12, 45, 35, 16, 20, 8, 23, 2]]      # [upper][lower]
MARRIAGE_HEX = {31: "Xian", 32: "Heng", 37: "Jiaren", 54: "Guimei", 11: "Tai", 12: "Pi",
                63: "Jiji", 64: "Weiji", 53: "Jian", 44: "Gou"}

# ---- H. geomancy ----------------------------------------------------------------------------
GEO = {0b1111: "ViaPuella", 0b0000: "Populus", 0b1000: "LaetitiaHead", 0b0001: "TristitiaHead"}
GEO_NAME = ["Populus", "Tristitia", "Albus", "Fortuna Major", "Rubeus", "Acquisitio", "Conjunctio",
            "Cauda Draconis", "Laetitia", "Amissio", "Puella", "Carcer", "Puer", "Fortuna Minor",
            "Caput Draconis", "Via"]
GEO_NAME = [g.replace(" ", "") for g in GEO_NAME]

# ---- J/K. degrees ---------------------------------------------------------------------------
CHALDEAN = ["saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon"]
SY_SIGN = ["He", "Vav", "Zayin", "Chet", "Tet", "Yod", "Lamed", "Nun", "Samekh", "Ayin", "Tzadi", "Qof"]
# Sefer Yetzirah 3:4 gives three mother letters for three elements, not four: Aleph is air, Shin is
# fire, and Mem is water — "from Mem the earth was created". So earth belongs to Mem, by the text's own
# derivation. An earlier draft parked earth under Aleph, which no reading of the text supports.
SY_MOTHER = {"fire": "Shin", "water": "Mem", "air": "Aleph", "earth": "Mem"}
ELEM = ["fire", "earth", "air", "water"]

# ---- L. Norse -------------------------------------------------------------------------------
RUNE = [("Perthro", 1, 13), ("Algiz", 1, 28), ("Sowilo", 2, 12), ("Tiwaz", 2, 27),
        ("Berkano", 3, 14), ("Ehwaz", 3, 30), ("Mannaz", 4, 14), ("Laguz", 4, 29),
        ("Ingwaz", 5, 14), ("Dagaz", 5, 29), ("Othala", 6, 14), ("Fehu", 6, 29),
        ("Uruz", 7, 14), ("Thurisaz", 7, 29), ("Ansuz", 8, 13), ("Raido", 8, 29),
        ("Kenaz", 9, 13), ("Gebo", 9, 28), ("Wunjo", 10, 13), ("Hagalaz", 10, 28),
        ("Nauthiz", 11, 13), ("Isa", 11, 28), ("Jera", 12, 13), ("Eihwaz", 12, 28)]

# ---- M. Egyptian ----------------------------------------------------------------------------
NILE = [("Nile", [(1, 1, 1, 7), (6, 19, 6, 28), (9, 1, 9, 7), (11, 18, 11, 26)]),
        ("AmonRa", [(1, 8, 1, 21), (2, 1, 2, 11)]),
        ("Mut", [(1, 22, 1, 31), (9, 8, 9, 22)]),
        ("Geb", [(2, 12, 2, 29), (8, 20, 8, 31)]),
        ("Osiris", [(3, 1, 3, 10), (11, 27, 12, 18)]),
        ("Isis", [(3, 11, 3, 31), (10, 18, 10, 29), (12, 19, 12, 31)]),
        ("Thoth", [(4, 1, 4, 19), (11, 8, 11, 17)]),
        ("Horus", [(4, 20, 5, 7), (8, 12, 8, 19)]),
        ("Anubis", [(5, 8, 5, 27), (6, 29, 7, 13)]),
        ("Seth", [(5, 28, 6, 18), (9, 28, 10, 2)]),
        ("Bastet", [(7, 14, 7, 28), (9, 23, 9, 27), (10, 3, 10, 17)]),
        ("Sekhmet", [(7, 29, 8, 11), (10, 30, 11, 7)])]

# ---- N. Aztec -------------------------------------------------------------------------------
TONAL = ["Cipactli", "Ehecatl", "Calli", "Cuetzpalin", "Coatl", "Miquiztli", "Mazatl", "Tochtli",
         "Atl", "Itzcuintli", "Ozomatli", "Malinalli", "Acatl", "Ocelotl", "Cuauhtli",
         "Cozcacuauhtli", "Ollin", "Tecpatl", "Quiahuitl", "Xochitl"]
LORDS_DAY = ["Xiuhtecuhtli", "Tlaltecuhtli", "Chalchiuhtlicue", "Tonatiuh", "Tlazolteotl",
             "Mictlantecuhtli", "Centeotl", "Tlaloc", "Quetzalcoatl", "Tezcatlipoca",
             "Chalmecatecuhtli", "Tlahuizcalpantecuhtli", "Citlalicue"]


def _jdn(y, m, d):
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _cats(vals, prefix, names, cols, ms):
    vals = np.asarray(vals)
    for v in pd.unique(vals):
        c = (vals == v).astype(np.float32)
        if c.sum() >= ms:
            cols.append(c); names.append(f"{prefix}={v}")


def _flag(cols, names, arr, nm, ms):
    c = np.nan_to_num(np.asarray(arr, dtype=float)).astype(np.float32)
    if ms <= c.sum() <= len(c) - ms:
        cols.append(c); names.append(nm)


def _pasaran(jdn):
    """the five-day pasaran week. Two independent anchors agree on this offset: Indonesian
    independence, 17 August 1945, is Jemuwah Legi, and every Galungan is Buda Kliwon."""
    return jdn % 5


def _weekday(jdn):
    return jdn % 7                  # 0 = Monday


def _pawukon(jdn):
    """day 0-209 of the Balinese 210-day round; anchored on Galungan = Buda Kliwon Dungulan."""
    return (jdn - _PAW_REF + 73) % 210


_PAW_REF = _jdn(2023, 1, 4)         # Galungan, 4 January 2023


def _selfcheck():
    j = _jdn(1945, 8, 17)                                       # Indonesian independence
    assert DINA[_weekday(j)] == "Jemuwah" and PASARAN[_pasaran(j)] == "Legi", "weton anchor"
    for y, m, d in ((2023, 1, 4), (2024, 2, 28), (2024, 9, 25), (2020, 2, 19)):
        jj = _jdn(y, m, d)
        assert _pawukon(jj) == 73 and PASARAN[_pasaran(jj)] == "Kliwon", f"pawukon anchor {y}"
    assert DINA[_weekday(_jdn(2000, 1, 1))] == "Setu", "weekday anchor"
    p = (_jdn(1521, 8, 13) - _AZ_REF) % 260                     # Caso: 13 Aug 1521 = 1 Coatl
    assert p == 104 and p % 13 == 0 and TONAL[p % 20] == "Coatl", "aztec anchor"


_AZ_REF = _jdn(1521, 8, 13) - 104


def _rune(m, d):
    """the runic half-month a date falls in; RUNE is in calendar order and wraps at the year end."""
    key = m * 100 + d
    idx = 23                                                    # before 13 Jan -> Eihwaz, from 28 Dec
    for i, (_, mm, dd) in enumerate(RUNE):
        if key >= mm * 100 + dd:
            idx = i
    return idx


def _nile(m, d):
    key = m * 100 + d
    for i, (_, spans) in enumerate(NILE):
        for a, b, c, e in spans:
            if a * 100 + b <= key <= c * 100 + e:
                return i
    return 0


def _geofig(y, m, d):
    """the date-cast geomantic figure: four lines, each single or double by the parity of one field."""
    return ((d & 1) << 3) | ((m & 1) << 2) | (((y // 10) % 10 & 1) << 1) | (y % 10 & 1)


def _popcount(a):
    return sum(((a >> k) & 1) for k in range(4))


def build(df, Z=None, split=None, exclude=frozenset(), min_support=40):
    _selfcheck()
    n = len(df); ms = min_support
    ya = pd.to_numeric(df.dob_a.str[:4]).to_numpy(int); ma = pd.to_numeric(df.dob_a.str[5:7]).to_numpy(int)
    da = pd.to_numeric(df.dob_a.str[8:10]).to_numpy(int)
    yb = pd.to_numeric(df.dob_b.str[:4]).to_numpy(int); mb = pd.to_numeric(df.dob_b.str[5:7]).to_numpy(int)
    db = pd.to_numeric(df.dob_b.str[8:10]).to_numpy(int)
    ja = np.array([_jdn(y, m, d) for y, m, d in zip(ya, ma, da)])
    jb = np.array([_jdn(y, m, d) for y, m, d in zip(yb, mb, db)])
    cols, names = [], []
    P = lambda a, b: [f"{i}x{j}" for i, j in zip(a, b)]

    # ============ A. JAVANESE WETON — the Primbon marriage calculation ============
    wa, wb = _weekday(ja), _weekday(jb)
    pa, pb = _pasaran(ja), _pasaran(jb)
    na = DINA_NEPTU[wa] + PASARAN_NEPTU[pa]
    nb = DINA_NEPTU[wb] + PASARAN_NEPTU[pb]
    tot = na + nb
    _cats([JODOH7[(t - 1) % 7] for t in tot], "weton_jodoh7", names, cols, ms)
    _cats([JODOH8[t % 8] for t in tot], "weton_jodoh8", names, cols, ms)
    _cats([PANCASUDA[(t - 1) % 7] for t in tot], "weton_pancasuda", names, cols, ms)
    _cats(tot, "weton_neptu_total", names, cols, ms)
    _cats(np.abs(na - nb), "weton_neptu_gap", names, cols, ms)
    _flag(cols, names, na == nb, "weton_equal_neptu", ms)
    _flag(cols, names, (tot % 5) == 0, "weton_total_divides_by_pancawara", ms)
    _cats(P([PASARAN[i] for i in pa], [PASARAN[j] for j in pb]), "weton_pasaranpair", names, cols, ms)
    _flag(cols, names, pa == pb, "weton_same_pasaran", ms)
    _flag(cols, names, (wa == wb) & (pa == pb), "weton_same_weton", ms)     # the same day of the 35
    _cats((ja - jb) % 35, "weton_cycle35_offset", names, cols, ms)
    # the two outcomes Primbon calls unmarriageable, kept as their own statements
    _flag(cols, names, np.array([JODOH7[(t - 1) % 7] == "Pegat" for t in tot]), "weton_pegat", ms)
    _flag(cols, names, np.array([JODOH7[(t - 1) % 7] in ("Jodoh", "Tinari", "Ratu") for t in tot]),
          "weton_auspicious_three", ms)

    # ============ B. BALINESE PAWUKON — ten week-cycles at once ============
    ka, kb = _pawukon(ja), _pawukon(jb)
    _cats(P([WUKU[i // 7] for i in ka], [WUKU[j // 7] for j in kb]), "pawukon_wukupair", names, cols, ms)
    _flag(cols, names, (ka // 7) == (kb // 7), "pawukon_same_wuku", ms)
    _flag(cols, names, ka == kb, "pawukon_same_day", ms)
    _cats(np.minimum((ka - kb) % 210, (kb - ka) % 210) // 21, "pawukon_distance_tenth", names, cols, ms)
    for nm, tab in (("triwara", TRIWARA), ("caturwara", CATURWARA), ("sadwara", SADWARA),
                    ("astawara", ASTAWARA), ("sangawara", SANGAWARA), ("dasawara", DASAWARA)):
        L = len(tab)
        # the shorter waras do not divide 210 evenly; Balinese practice repeats the opening name
        ia = np.array([tab[min(i, 210 - 1) % L] for i in ka])
        ib = np.array([tab[min(j, 210 - 1) % L] for j in kb])
        _cats(P(ia, ib), f"pawukon_{nm}pair", names, cols, ms)
        _flag(cols, names, ia == ib, f"pawukon_same_{nm}", ms)
    dwa = np.array(["Menga" if i % 2 == 0 else "Pepet" for i in ka])
    dwb = np.array(["Menga" if j % 2 == 0 else "Pepet" for j in kb])
    _cats(P(dwa, dwb), "pawukon_dwiwarapair", names, cols, ms)
    _flag(cols, names, dwa == dwb, "pawukon_same_dwiwara", ms)
    # Kajeng Kliwon, the day Bali treats as most charged: triwara Kajeng meeting pancawara Kliwon
    kk_a = ((ka % 3) == 2) & (pa == 4); kk_b = ((kb % 3) == 2) & (pb == 4)
    _flag(cols, names, kk_a | kk_b, "pawukon_kajeng_kliwon_either", ms)
    _flag(cols, names, kk_a & kk_b, "pawukon_kajeng_kliwon_both", ms)

    # ============ C. THE TEN PORUTHAM (Tamil/Sinhala) ============
    if Z is not None and split is not None:
        A = Z[f"theta_a_{split}"]; B = Z[f"theta_b_{split}"]
        mo_a = A[:, BI["moon"]] % 360.0; mo_b = B[:, BI["moon"]] % 360.0
        nk_a = (mo_a / (360.0 / 27)).astype(int) + 1            # 1-based nakshatra
        nk_b = (mo_b / (360.0 / 27)).astype(int) + 1
        ra_ = (mo_a / 30).astype(int); rb_ = (mo_b / 30).astype(int)   # Moon sign (rasi)
        # DINA — count from her star to his, mod 9; the school's fortunate residues
        dina = ((nk_a - nk_b) % 27) + 1
        _cats(dina % 9, "porutham_dina_residue", names, cols, ms)
        _flag(cols, names, np.isin(dina % 9, [2, 4, 6, 8, 0]), "porutham_dina_ok", ms)
        # MAHENDRA — the count that promises children
        _flag(cols, names, np.isin(dina, list(MAHENDRA_OK)), "porutham_mahendra_ok", ms)
        # STREE-DEERGHA — the count that promises the wife's long life
        _flag(cols, names, dina > 13, "porutham_streedeergha_ok", ms)
        _cats(np.minimum(dina, 27), "porutham_star_count", names, cols, ms)
        # VEDHA — the piercing pair, which cancels every other agreement
        ved = np.array([VEDHA.get(int(x), -1) == int(y) for x, y in zip(nk_a, nk_b)])
        _flag(cols, names, ved, "porutham_vedha_pierced", ms)
        _flag(cols, names, ~ved, "porutham_vedha_clear", ms)
        # RASYADHIPATHI — friendship between the two Moon-sign lords
        la_ = np.array([RASI_LORD[i] for i in ra_]); lb_ = np.array([RASI_LORD[j] for j in rb_])
        _flag(cols, names, la_ == lb_, "porutham_same_rasi_lord", ms)
        _flag(cols, names, np.array([b in FRIENDS.get(a, set()) or a in FRIENDS.get(b, set())
                                     for a, b in zip(la_, lb_)]), "porutham_rasi_lords_friendly", ms)
        _cats(P(la_, lb_), "porutham_rasilordpair", names, cols, ms)
        # RAJJU in its five-limb form, and the rule that the same limb is the one real refusal
        RAJJU = ["Pada", "Kati", "Nabhi", "Kantha", "Siro"]
        rj_a = np.array([RAJJU[min(int(x) - 1, 26) % 9 % 5] for x in nk_a])
        rj_b = np.array([RAJJU[min(int(y) - 1, 26) % 9 % 5] for y in nk_b])
        _flag(cols, names, rj_a == rj_b, "porutham_same_rajju", ms)
        _cats(P(rj_a, rj_b), "porutham_rajjupair", names, cols, ms)
        # O. PAPASAMYA — malefic affliction counted for each, and compared
        MAL = ["mars", "saturn", "sun"]
        def _papa(T):
            asc = T[:, BI["moon"]] % 360.0
            c = np.zeros(len(T), int)
            for b in MAL:
                h = (((T[:, BI[b]] - asc) % 360.0) / 30).astype(int) + 1
                c += np.isin(h, [1, 2, 4, 7, 8, 12]).astype(int)
            return c
        ca_, cb_ = _papa(A), _papa(B)
        _flag(cols, names, ca_ == cb_, "papasamya_equal", ms)
        _cats(np.abs(ca_ - cb_), "papasamya_gap", names, cols, ms)
        _cats(P(ca_, cb_), "papasamya_pair", names, cols, ms)
        _flag(cols, names, (ca_ == 0) & (cb_ == 0), "papasamya_both_clear", ms)
        _flag(cols, names, (ca_ >= 3) & (cb_ >= 3), "papasamya_both_heavy", ms)

        # ============ J. HELLENISTIC DEGREE TECHNIQUES ============
        for body in ("sun", "moon", "venus"):
            xa = A[:, BI[body]] % 360.0; xb = B[:, BI[body]] % 360.0
            sab_a = np.floor(xa).astype(int); sab_b = np.floor(xb).astype(int)
            _flag(cols, names, sab_a == sab_b, f"sabian_same_symbol_{body}", ms)
            _flag(cols, names, (sab_a % 30) == (sab_b % 30), f"sabian_same_degree_in_sign_{body}", ms)
            _flag(cols, names, ((sab_a % 30) + (sab_b % 30)) == 29, f"sabian_degrees_complete_{body}", ms)
            # dodekatemorion: the sign a 2.5-degree twelfth of a sign points to
            dd_a = ((sab_a // 30) * 12 + ((xa % 30) / 2.5).astype(int)) % 12
            dd_b = ((sab_b // 30) * 12 + ((xb % 30) / 2.5).astype(int)) % 12
            _flag(cols, names, dd_a == dd_b, f"dodekatemoria_same_{body}", ms)
            _cats(P([SIGNS[i] for i in dd_a], [SIGNS[j] for j in dd_b]),
                  f"dodekatemoria_{body}pair", names, cols, ms)
            _flag(cols, names, dd_a == (sab_b // 30), f"dodekatemoria_his_{body}_lands_on_her_sign", ms)
            # monomoiria: the Chaldean ruler of the single degree
            mn_a = np.array([CHALDEAN[i % 7] for i in sab_a])
            mn_b = np.array([CHALDEAN[j % 7] for j in sab_b])
            _flag(cols, names, mn_a == mn_b, f"monomoiria_same_ruler_{body}", ms)
            _cats(P(mn_a, mn_b), f"monomoiria_{body}pair", names, cols, ms)
            # ============ K. KABBALAH — the 72 Names wheel, five degrees each ============
            k7_a = (xa / 5).astype(int); k7_b = (xb / 5).astype(int)
            _flag(cols, names, k7_a == k7_b, f"kab72_same_name_{body}", ms)
            _flag(cols, names, ((k7_a - k7_b) % 72 == 36), f"kab72_opposite_name_{body}", ms)
            _cats(np.minimum((k7_a - k7_b) % 72, (k7_b - k7_a) % 72) // 6,
                  f"kab72_arc_{body}", names, cols, ms)
        # Sefer Yetzirah letters: the simple letter of the sign, the mother letter of the element
        for body in ("sun", "moon"):
            sa_ = ((A[:, BI[body]] % 360.0) / 30).astype(int)
            sb_ = ((B[:, BI[body]] % 360.0) / 30).astype(int)
            _cats(P([SY_SIGN[i] for i in sa_], [SY_SIGN[j] for j in sb_]),
                  f"seferyetzirah_letterpair_{body}", names, cols, ms)
            mo_a2 = np.array([SY_MOTHER[ELEM[i % 4]] for i in sa_])
            mo_b2 = np.array([SY_MOTHER[ELEM[j % 4]] for j in sb_])
            _flag(cols, names, mo_a2 == mo_b2, f"seferyetzirah_same_mother_{body}", ms)
            _cats(P(mo_a2, mo_b2), f"seferyetzirah_motherpair_{body}", names, cols, ms)

    # ============ D. THE SIX CHINESE RELATIONS, COMPLETED ============
    yba = (ya - 4) % 12; ybb = (yb - 4) % 12                    # year branch
    dba = (ja + 49) % 12; dbb = (jb + 49) % 12                  # day branch, the bank's anchor
    dsa = (ja + 49) % 10; dsb = (jb + 49) % 10                  # day stem
    for tag, xa_, xb_ in (("year", yba, ybb), ("day", dba, dbb)):
        xing = np.array([any({int(i), int(j)} <= s and i != j for s in XING3) or
                         (int(i), int(j)) in XING2 for i, j in zip(xa_, xb_)])
        _flag(cols, names, xing, f"xiangxing_punishment_{tag}", ms)
        _flag(cols, names, ~xing, f"xiangxing_clear_{tag}", ms)
        _flag(cols, names, (xa_ == xb_) & np.isin(xa_, list(XING_SELF)),
              f"xiangxing_self_punishment_{tag}", ms)
        po = np.array([(int(i), int(j)) in PO for i, j in zip(xa_, xb_)])
        _flag(cols, names, po, f"xiangpo_destruction_{tag}", ms)
        _flag(cols, names, ~po, f"xiangpo_clear_{tag}", ms)
        # the three that the bank had, re-stated here so a Korean reading can quote them
        _flag(cols, names, ((xa_ - xb_) % 12 == 6), f"liuchong_clash_{tag}", ms)
        _flag(cols, names, ((xa_ - xb_) % 4 == 0) & (xa_ != xb_), f"sanhe_trine_{tag}", ms)
        _flag(cols, names, ((xa_ + xb_) % 12 == 1), f"liuhe_sixharmony_{tag}", ms)
    he = np.array([(int(i), int(j)) in STEM_HE for i, j in zip(dsa, dsb)])
    _flag(cols, names, he, "stem_he_combination", ms)
    _flag(cols, names, ((dsa - dsb) % 10 == 6), "stem_clash", ms)
    _cats(P([STEM[i] for i in dsa], [STEM[j] for j in dsb]), "stempair_day", names, cols, ms)
    # nayin element of the year pillar, and its generating/controlling relation
    nya = np.array([NAYIN5[((ya[i] - 4) % 60) // 12] for i in range(n)])
    nyb = np.array([NAYIN5[((yb[i] - 4) % 60) // 12] for i in range(n)])
    _flag(cols, names, np.array([GEN[a] == b or GEN[b] == a for a, b in zip(nya, nyb)]),
          "nayin_year_generating", ms)
    _flag(cols, names, np.array([CTL[a] == b or CTL[b] == a for a, b in zip(nya, nyb)]),
          "nayin_year_controlling", ms)
    _flag(cols, names, nya == nyb, "nayin_year_same", ms)

    # ============ E. KOREAN GUNGHAP — the outer and the inner reading ============
    outer_good = ((yba - ybb) % 4 == 0) | ((yba + ybb) % 12 == 1)
    outer_bad = ((yba - ybb) % 12 == 6) | np.array([(int(i), int(j)) in PO for i, j in zip(yba, ybb)])
    inner_good = np.array([GEN[a] == b or GEN[b] == a or a == b for a, b in zip(nya, nyb)])
    inner_bad = np.array([CTL[a] == b or CTL[b] == a for a, b in zip(nya, nyb)])
    _flag(cols, names, outer_good, "gunghap_outer_auspicious", ms)
    _flag(cols, names, outer_bad, "gunghap_outer_inauspicious", ms)
    _flag(cols, names, inner_good, "gunghap_inner_auspicious", ms)
    _flag(cols, names, inner_bad, "gunghap_inner_inauspicious", ms)
    _flag(cols, names, outer_good & inner_good, "gunghap_both_auspicious", ms)
    _flag(cols, names, outer_bad | inner_bad, "gunghap_either_inauspicious", ms)
    _cats([f"{'G' if g else ('B' if b_ else 'N')}x{'G' if g2 else ('B' if b2 else 'N')}"
           for g, b_, g2, b2 in zip(outer_good, outer_bad, inner_good, inner_bad)],
          "gunghap_verdict", names, cols, ms)

    # ============ F. BURMESE MAHABOTE ============
    hb_a = ((ya - 638) % 7 - (wa + 1)) % 7
    hb_b = ((yb - 638) % 7 - (wb + 1)) % 7
    _cats(P([MAHABOTE[i] for i in hb_a], [MAHABOTE[j] for j in hb_b]), "mahabote_pair", names, cols, ms)
    _flag(cols, names, hb_a == hb_b, "mahabote_same_house", ms)
    _flag(cols, names, ((hb_a - hb_b) % 7 == 4) | ((hb_b - hb_a) % 7 == 4), "mahabote_marana_apart", ms)
    _flag(cols, names, (hb_a == 4) | (hb_b == 4), "mahabote_marana_either", ms)
    _flag(cols, names, (hb_a == 2) & (hb_b == 2), "mahabote_both_yaza", ms)

    # ============ G. THE COUPLE'S HEXAGRAM (plum blossom) ============
    sum_a = (yba + 1) + ma + da
    sum_b = (ybb + 1) + mb + db
    up = sum_a % 8; lo = sum_b % 8
    hexn = np.array([KINGWEN[int(u)][int(l)] for u, l in zip(up, lo)])
    _cats(hexn, "iching_couple_hexagram", names, cols, ms)
    _cats(P([TRIGRAM[i] for i in up], [TRIGRAM[j] for j in lo]), "iching_trigrampair", names, cols, ms)
    _flag(cols, names, up == lo, "iching_doubled_trigram", ms)
    for h, nm in MARRIAGE_HEX.items():
        _flag(cols, names, hexn == h, f"iching_couple_is_{nm}", ms)
    _cats((sum_a + sum_b) % 6 + 1, "iching_changing_line", names, cols, ms)
    bits = np.array([(TRI_BITS[int(u)] << 3) | TRI_BITS[int(l)] for u, l in zip(up, lo)])
    nucl_u = np.array([TRI_BITS.index(((b >> 1) & 7)) for b in bits])
    nucl_l = np.array([TRI_BITS.index(((b >> 2) & 7)) for b in bits])
    _cats([KINGWEN[int(u)][int(l)] for u, l in zip(nucl_u, nucl_l)],
          "iching_nuclear_hexagram", names, cols, ms)
    _cats(np.array([bin(int(b)).count("1") for b in bits]), "iching_yang_lines", names, cols, ms)

    # ============ H. THE GEOMANTIC JUDGE ============
    ga = np.array([_geofig(y, m, d) for y, m, d in zip(ya, ma, da)])
    gb = np.array([_geofig(y, m, d) for y, m, d in zip(yb, mb, db)])
    judge = ga ^ gb                                            # adding two figures IS the exclusive or
    recon = judge ^ ga
    _cats([GEO_NAME[i] for i in judge], "geomancy_judge", names, cols, ms)
    _cats([GEO_NAME[i] for i in recon], "geomancy_reconciler", names, cols, ms)
    _cats(P([GEO_NAME[i] for i in ga], [GEO_NAME[j] for j in gb]), "geomancy_witnesspair",
          names, cols, ms)
    _flag(cols, names, ga == gb, "geomancy_same_figure", ms)
    _flag(cols, names, judge == 0, "geomancy_judge_is_populus", ms)          # the void judgement
    _cats(np.array([_popcount(int(j)) for j in judge]), "geomancy_judge_points", names, cols, ms)
    _flag(cols, names, np.array([_popcount(int(j)) % 2 == 0 for j in judge]), "geomancy_judge_even", ms)

    # ============ I. BIORHYTHM ============
    dd = np.abs(ja - jb)
    for nm, per in (("physical", 23), ("emotional", 28), ("intellectual", 33)):
        ph = (dd % per) / per                                   # 0 = in step, .5 = opposed
        _flag(cols, names, np.minimum(ph, 1 - ph) < 0.08, f"biorhythm_{nm}_in_phase", ms)
        _flag(cols, names, np.abs(ph - 0.5) < 0.08, f"biorhythm_{nm}_opposed", ms)
        _cats((ph * 8).astype(int), f"biorhythm_{nm}_octant", names, cols, ms)
    allthree = np.ones(n, bool)
    for per in (23, 28, 33):
        ph = (dd % per) / per
        allthree &= np.minimum(ph, 1 - ph) < 0.15
    _flag(cols, names, allthree, "biorhythm_all_three_in_phase", ms)

    # ============ L. NORSE RUNIC HALF-MONTHS ============
    ru_a = np.array([_rune(m, d) for m, d in zip(ma, da)])
    ru_b = np.array([_rune(m, d) for m, d in zip(mb, db)])
    _cats(P([RUNE[i][0] for i in ru_a], [RUNE[j][0] for j in ru_b]), "runepair", names, cols, ms)
    _flag(cols, names, ru_a == ru_b, "rune_same_halfmonth", ms)
    _flag(cols, names, ((ru_a - ru_b) % 24 == 12), "rune_opposite_wheel", ms)
    _cats((ru_a // 8) * 3 + (ru_b // 8), "rune_aettpair", names, cols, ms)   # the three aetts
    _flag(cols, names, (ru_a // 8) == (ru_b // 8), "rune_same_aett", ms)

    # ============ M. EGYPTIAN (NILE) ZODIAC ============
    eg_a = np.array([_nile(m, d) for m, d in zip(ma, da)])
    eg_b = np.array([_nile(m, d) for m, d in zip(mb, db)])
    _cats(P([NILE[i][0] for i in eg_a], [NILE[j][0] for j in eg_b]), "nilepair", names, cols, ms)
    _flag(cols, names, eg_a == eg_b, "nile_same_deity", ms)
    _flag(cols, names, np.array([{int(i), int(j)} == {9, 7} for i, j in zip(eg_a, eg_b)]),
          "nile_seth_against_horus", ms)                        # the quarrel the myth is named for
    _flag(cols, names, np.array([{int(i), int(j)} == {4, 5} for i, j in zip(eg_a, eg_b)]),
          "nile_osiris_with_isis", ms)                          # and the marriage it is named for

    # ============ N. AZTEC TONALPOHUALLI ============
    ta_ = (ja - _AZ_REF) % 260; tb_ = (jb - _AZ_REF) % 260
    _cats(P([TONAL[i % 20] for i in ta_], [TONAL[j % 20] for j in tb_]), "aztec_signpair",
          names, cols, ms)
    _flag(cols, names, (ta_ % 20) == (tb_ % 20), "aztec_same_sign", ms)
    _flag(cols, names, (ta_ % 13) == (tb_ % 13), "aztec_same_number", ms)
    _flag(cols, names, ta_ == tb_, "aztec_same_day", ms)
    _cats(P([LORDS_DAY[i % 13] for i in ta_], [LORDS_DAY[j % 13] for j in tb_]),
          "aztec_lordofdaypair", names, cols, ms)
    _flag(cols, names, ((ta_ % 13) + (tb_ % 13)) == 12, "aztec_numbers_complete_thirteen", ms)
    _cats(np.minimum((ta_ - tb_) % 260, (tb_ - ta_) % 260) // 20, "aztec_distance_trecena",
          names, cols, ms)
    _flag(cols, names, (ta_ // 13) == (tb_ // 13), "aztec_same_trecena", ms)

    keep = [i for i, nm in enumerate(names) if nm not in exclude]
    X = np.column_stack([cols[i] for i in keep]).astype(np.float32) if keep else np.zeros((n, 0), np.float32)
    return X, [names[i] for i in keep]
