"""systems_vedic.py — VEDIC / JYOTISH date-computable systems as PSEUDO-BODIES (tradition slug "vedic").

CONTRACT (round of 2026-09-03). Every entry of SYSTEMS is {"name", "n", "desc", "fn"} with
fn(y, m, d, L) -> int in [0, n-1]   (or a float in DEGREES when n == 0, a continuous circle)
where L is a dict of ONE person's SIDEREAL (Lahiri) longitudes in degrees keyed "sun", "moon",
"mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "node" (Rahu; the
corpus key "true_node" is accepted too), "chiron", "lilith" ("mean_lilith" accepted).  Pure Python,
standard library only, deterministic — the same code runs in the browser under Pyodide.

The longitudes are ALREADY sidereal, so no Vedic system here needs the ayanamsa; the helper
ayanamsa(y) is kept for parity with the other tradition modules (tropical = sidereal + ayanamsa).

Angle convention downstream: state s of N -> (s+1)*360/N on its own circle (numerology: state 0 ->
40 degrees).  A constant offset in any table (which nakshatra is "first") is absorbed by the fitted
phase; only the cycle LENGTH and the BOUNDARIES matter, and those are exact here.

WHAT IS IMPLEMENTED (63 systems)
  nakshatra (27) and pada (108) of the Moon, Sun, Venus, Mars                                8
  panchanga: tithi 30 · paksha 2 · yoga 27 · karana 60 (half-tithi) · karana name 11 · vara 7   6
  rashi (12) of each of the 13 bodies                                                        13
  Vimshottari: mahadasha lord 9 · antardasha lord 9 · pratyantardasha lord 9 · Moon's
      nakshatra phase (continuous, n=0: the fraction traversed x 360)                         4
  Ashtakoota inputs from the Moon's nakshatra / rashi: gana 3 · yoni 14 · nadi 3 · varna 4 ·
      vashya 5 · rajju 5                                                                      6
  navamsa D9 sign (12) of each body · dwadasamsa D12 sign (12) of each body                  26
NOT duplicated, on purpose (an identical or constant-offset angle adds nothing to the bank):
  * bhakoot koota = the Moon rashi, already a system.
  * tara group (nakshatra count mod 9) = nakshatra % 9 = the Vimshottari mahadasha lord EXACTLY
    (Ashwini->Ketu, Bharani->Venus, ... repeating every 9), so `vedic_dasha_lord` IS the tara
    group; `tara_group(y,m,d,L)` is exported as an alias but is not a second SYSTEMS entry.
  * Ketu = Rahu + 180: its rashi / D9 / D12 are Rahu's shifted by a constant 6 signs.
Sources of the tables: Brihat Parashara Hora Shastra (dashas, vargas), Muhurta Chintamani /
standard Ashtakoota tables as printed in every North-Indian kundali-milan almanac.
"""

# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def jdn(y, m, d):
    """Fliegel-Van Flandern: proleptic Gregorian civil date -> Julian Day Number (integer, noon)."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045

def ayanamsa(y):
    """Lahiri ayanamsa in degrees, linear in the year (good to a few arcminutes 1600-2100)."""
    return 23.853 + 0.013971 * (y - 2000)

def _lon(L, name):
    """Sidereal longitude of a body, accepting the corpus spellings; Ketu derived from Rahu."""
    if name == "node":
        v = L.get("node", L.get("true_node", L.get("rahu")))
    elif name == "lilith":
        v = L.get("lilith", L.get("mean_lilith"))
    elif name == "ketu":
        v = _lon(L, "node") + 180.0
    else:
        v = L[name]
    return float(v) % 360.0

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
          "pluto", "node", "chiron", "lilith"]
NAK = 360.0 / 27.0            # 13 deg 20'
PADA = NAK / 4.0              # 3 deg 20'

def nakshatra(lon):  return int((lon % 360.0) // NAK) % 27
def pada(lon):       return int((lon % 360.0) // PADA) % 108
def rashi(lon):      return int((lon % 360.0) // 30.0) % 12
def navamsa(lon):
    """D9: the sign occupied in the ninefold chart = floor(9 * lon / 30) mod 12.  Parashari rule
    (movable signs count from themselves, fixed from the 9th, dual from the 5th) reduces to this."""
    return int((lon % 360.0) * 9.0 // 30.0) % 12
def dwadasamsa(lon):
    """D12: twelfth of a sign, counted from the sign itself = floor(12 * lon / 30) mod 12."""
    return int((lon % 360.0) * 12.0 // 30.0) % 12

# ----------------------------------------------------------------------------------------------
# Vimshottari dasha
# ----------------------------------------------------------------------------------------------
# lord order from Ashwini, and the years each rules (sum 120)
DASHA_LORDS = ["ketu", "venus", "sun", "moon", "mars", "rahu", "jupiter", "saturn", "mercury"]
DASHA_YEARS = [7, 20, 6, 10, 7, 18, 16, 19, 17]

def moon_frac(L):
    """Fraction of the Moon's nakshatra already traversed at birth, in [0, 1)."""
    lon = _lon(L, "moon")
    return (lon % NAK) / NAK

def dasha_lord(L):
    return nakshatra(_lon(L, "moon")) % 9

def _sub_lord(start, frac):
    """Sub-period lord: periods run from `start` in DASHA_LORDS order with lengths proportional to
    DASHA_YEARS; return the index of the period containing fraction `frac` of the whole."""
    target = frac * 120.0
    acc = 0.0
    for k in range(9):
        i = (start + k) % 9
        acc += DASHA_YEARS[i]
        if target < acc:
            return i, (target - (acc - DASHA_YEARS[i])) / DASHA_YEARS[i]
    return (start + 8) % 9, 1.0 - 1e-12

def antardasha_lord(L):
    """Bhukti running at birth: elapsed fraction of the mahadasha = fraction of the nakshatra
    traversed (the dasha balance rule), bhuktis run from the maha lord in lord order."""
    ml = dasha_lord(L)
    return _sub_lord(ml, moon_frac(L))[0]

def pratyantar_lord(L):
    ml = dasha_lord(L)
    al, f2 = _sub_lord(ml, moon_frac(L))
    return _sub_lord(al, f2)[0]

# ----------------------------------------------------------------------------------------------
# panchanga
# ----------------------------------------------------------------------------------------------
def elongation(L):  return (_lon(L, "moon") - _lon(L, "sun")) % 360.0
def tithi(L):       return int(elongation(L) // 12.0) % 30
def paksha(L):      return 0 if tithi(L) < 15 else 1          # 0 shukla (waxing), 1 krishna
def yoga(L):        return int(((_lon(L, "sun") + _lon(L, "moon")) % 360.0) // NAK) % 27
def karana(L):      return int(elongation(L) // 6.0) % 60     # half-tithi index
# the eleven karana NAMES: half-tithi 0 = Kimstughna (fixed); 1..56 = the seven movable karanas
# Bava, Balava, Kaulava, Taitila, Gara, Vanija, Vishti cycling eight times; 57 Shakuni,
# 58 Chatushpada, 59 Naga (fixed).  States: 0-6 movable in that order, 7 Shakuni, 8 Chatushpada,
# 9 Naga, 10 Kimstughna.
def karana_name(L):
    h = karana(L)
    if h == 0:  return 10
    if h >= 57: return 7 + (h - 57)
    return (h - 1) % 7
def vara(y, m, d):  return (jdn(y, m, d) + 1) % 7               # 0 = Sunday (Ravivara)

# ----------------------------------------------------------------------------------------------
# Ashtakoota tables, indexed by nakshatra 0 = Ashwini ... 26 = Revati
# ----------------------------------------------------------------------------------------------
# gana: 0 deva, 1 manushya, 2 rakshasa
GANA = [0, 1, 2, 1, 0, 1, 0, 0, 2,      # Ashwini..Ashlesha
        2, 1, 1, 0, 2, 0, 2, 0, 2,      # Magha..Jyeshtha
        2, 1, 1, 0, 2, 2, 1, 1, 0]      # Mula..Revati
# yoni animals: 0 horse, 1 elephant, 2 sheep, 3 serpent, 4 dog, 5 cat, 6 rat, 7 cow, 8 buffalo,
# 9 tiger, 10 deer, 11 monkey, 12 mongoose, 13 lion
YONI = [0, 1, 2, 3, 3, 4, 5, 2, 5,      # Ashwini horse, Bharani elephant, Krittika sheep, Rohini serpent,
        6, 6, 7, 8, 9, 8, 9, 10, 10,    # Mrigashira serpent, Ardra dog, Punarvasu cat, Pushya sheep, Ashlesha cat,
        4, 11, 12, 11, 13, 0, 13, 7, 1] # Magha rat, P.Phalguni rat, U.Phalguni cow, Hasta buffalo, Chitra tiger,
                                        # Swati buffalo, Vishakha tiger, Anuradha deer, Jyeshtha deer, Mula dog,
                                        # P.Ashadha monkey, U.Ashadha mongoose, Shravana monkey, Dhanishta lion,
                                        # Shatabhisha horse, P.Bhadrapada lion, U.Bhadrapada cow, Revati elephant
# nadi: 0 adi, 1 madhya, 2 antya — the classical six-step pattern 0,1,2,2,1,0 repeated
NADI = [(0, 1, 2, 2, 1, 0)[i % 6] for i in range(27)]
# rajju (the limb): 0 pada (foot), 1 kati (waist), 2 nabhi (navel), 3 kantha (neck), 4 sira (head)
RAJJU = [0, 1, 2, 3, 4, 3, 2, 1, 0,     # Ashwini..Ashlesha  (ascending then descending)
         0, 1, 2, 3, 4, 3, 2, 1, 0,     # Magha..Jyeshtha
         0, 1, 2, 3, 4, 3, 2, 1, 0]     # Mula..Revati
# varna from the Moon rashi: 0 brahmin (water signs), 1 kshatriya (fire), 2 vaishya (earth),
# 3 shudra (air).  Aries fire, Taurus earth, Gemini air, Cancer water, ... = element by rashi % 4
VARNA_BY_ELEMENT = {0: 1, 1: 2, 2: 3, 3: 0}     # element index (fire, earth, air, water) -> varna
# vashya from the Moon LONGITUDE (two signs split at their midpoint):
# 0 chatushpada (quadruped), 1 manava (human), 2 jalachara (aquatic), 3 vanachara (wild), 4 keeta (insect)
def vashya(lon):
    r = rashi(lon); half = (lon % 30.0) >= 15.0
    if r in (0, 1):  return 0            # Aries, Taurus
    if r == 2:       return 1            # Gemini
    if r == 3:       return 2            # Cancer
    if r == 4:       return 3            # Leo
    if r in (5, 6):  return 1            # Virgo, Libra
    if r == 7:       return 4            # Scorpio
    if r == 8:       return 0 if half else 1   # Sagittarius: first half human, second quadruped
    if r == 9:       return 2 if half else 0   # Capricorn: first half quadruped, second aquatic
    if r == 10:      return 1            # Aquarius
    return 2                             # Pisces

def tara_group(y, m, d, L):
    """Alias: nakshatra count group = nakshatra % 9, identical to the Vimshottari mahadasha lord."""
    return dasha_lord(L)

# ----------------------------------------------------------------------------------------------
# SYSTEMS
# ----------------------------------------------------------------------------------------------
def _mk_body(name, f, tag):
    def fn(y, m, d, L, _n=name, _f=f):
        return _f(_lon(L, _n))
    fn.__name__ = f"vedic_{tag}_{name}"
    return fn

SYSTEMS = []
for b in ("moon", "sun", "venus", "mars"):
    SYSTEMS.append({"name": f"vedic_nakshatra_{b}", "n": 27,
                    "desc": f"nakshatra (27 lunar mansions of 13d20') of the sidereal {b}, 0 = Ashwini",
                    "fn": _mk_body(b, nakshatra, "nakshatra")})
for b in ("moon", "sun", "venus", "mars"):
    SYSTEMS.append({"name": f"vedic_pada_{b}", "n": 108,
                    "desc": f"nakshatra pada (quarter, 3d20') of the sidereal {b}, 0 = Ashwini 1",
                    "fn": _mk_body(b, pada, "pada")})
SYSTEMS += [
    {"name": "vedic_tithi", "n": 30, "desc": "tithi: floor((moon - sun) / 12 deg), 0 = shukla pratipada, 14 = purnima, 29 = amavasya",
     "fn": lambda y, m, d, L: tithi(L)},
    {"name": "vedic_paksha", "n": 2, "desc": "paksha: 0 shukla (waxing, tithi 1-15), 1 krishna (waning)",
     "fn": lambda y, m, d, L: paksha(L)},
    {"name": "vedic_yoga", "n": 27, "desc": "nitya yoga: floor((sun + moon) / 13d20'), 0 = Vishkambha",
     "fn": lambda y, m, d, L: yoga(L)},
    {"name": "vedic_karana", "n": 60, "desc": "karana as the half-tithi index floor((moon - sun) / 6 deg), 0 = Kimstughna",
     "fn": lambda y, m, d, L: karana(L)},
    {"name": "vedic_karana_name", "n": 11, "desc": "the eleven karana names: 0-6 Bava..Vishti (movable), 7 Shakuni, 8 Chatushpada, 9 Naga, 10 Kimstughna (fixed)",
     "fn": lambda y, m, d, L: karana_name(L)},
    {"name": "vedic_vara", "n": 7, "desc": "vara (weekday, Gregorian civil date at noon UT), 0 = Ravivara (Sunday)",
     "fn": lambda y, m, d, L: vara(y, m, d)},
]
for b in BODIES:
    SYSTEMS.append({"name": f"vedic_rashi_{b}", "n": 12,
                    "desc": f"sidereal rashi (sign) of {b}, 0 = Mesha (Aries)",
                    "fn": _mk_body(b, rashi, "rashi")})
SYSTEMS += [
    {"name": "vedic_dasha_lord", "n": 9, "desc": "Vimshottari mahadasha lord at birth = Moon nakshatra % 9: 0 Ketu, 1 Venus, 2 Sun, 3 Moon, 4 Mars, 5 Rahu, 6 Jupiter, 7 Saturn, 8 Mercury (also the tara/nakshatra-count group)",
     "fn": lambda y, m, d, L: dasha_lord(L)},
    {"name": "vedic_antardasha_lord", "n": 9, "desc": "Vimshottari antardasha (bhukti) lord running at birth, from the fraction of the Moon nakshatra traversed; same 9-lord coding",
     "fn": lambda y, m, d, L: antardasha_lord(L)},
    {"name": "vedic_pratyantar_lord", "n": 9, "desc": "Vimshottari pratyantardasha lord running at birth (third level); same 9-lord coding",
     "fn": lambda y, m, d, L: pratyantar_lord(L)},
    {"name": "vedic_moon_nak_phase", "n": 0, "desc": "continuous: the fraction of the Moon's nakshatra traversed at birth x 360 (the dasha-balance phase; = the 27th harmonic of the Moon)",
     "fn": lambda y, m, d, L: (moon_frac(L) * 360.0) % 360.0},
    {"name": "vedic_gana", "n": 3, "desc": "gana of the Moon nakshatra: 0 deva, 1 manushya, 2 rakshasa",
     "fn": lambda y, m, d, L: GANA[nakshatra(_lon(L, "moon"))]},
    {"name": "vedic_yoni", "n": 14, "desc": "yoni animal of the Moon nakshatra: 0 horse, 1 elephant, 2 sheep, 3 serpent, 4 dog, 5 cat, 6 rat, 7 cow, 8 buffalo, 9 tiger, 10 deer, 11 monkey, 12 mongoose, 13 lion",
     "fn": lambda y, m, d, L: YONI[nakshatra(_lon(L, "moon"))]},
    {"name": "vedic_nadi", "n": 3, "desc": "nadi of the Moon nakshatra: 0 adi, 1 madhya, 2 antya",
     "fn": lambda y, m, d, L: NADI[nakshatra(_lon(L, "moon"))]},
    {"name": "vedic_varna", "n": 4, "desc": "varna of the Moon rashi: 0 brahmin (water), 1 kshatriya (fire), 2 vaishya (earth), 3 shudra (air)",
     "fn": lambda y, m, d, L: VARNA_BY_ELEMENT[rashi(_lon(L, "moon")) % 4]},
    {"name": "vedic_vashya", "n": 5, "desc": "vashya of the Moon (rashi with half-sign splits in Sagittarius and Capricorn): 0 chatushpada, 1 manava, 2 jalachara, 3 vanachara, 4 keeta",
     "fn": lambda y, m, d, L: vashya(_lon(L, "moon"))},
    {"name": "vedic_rajju", "n": 5, "desc": "rajju of the Moon nakshatra: 0 pada (foot), 1 kati, 2 nabhi, 3 kantha, 4 sira (head)",
     "fn": lambda y, m, d, L: RAJJU[nakshatra(_lon(L, "moon"))]},
]
for b in BODIES:
    SYSTEMS.append({"name": f"vedic_d9_{b}", "n": 12,
                    "desc": f"navamsa (D9) sign of {b}: floor(9 * lon / 30) mod 12, 0 = Mesha",
                    "fn": _mk_body(b, navamsa, "d9")})
for b in BODIES:
    SYSTEMS.append({"name": f"vedic_d12_{b}", "n": 12,
                    "desc": f"dwadasamsa (D12) sign of {b}: floor(12 * lon / 30) mod 12, 0 = Mesha",
                    "fn": _mk_body(b, dwadasamsa, "d12")})

assert len({s["name"] for s in SYSTEMS}) == len(SYSTEMS), "duplicate system name"

def angle(sysrec, y, m, d, L):
    """The pseudo-body angle in degrees for one system record."""
    v = sysrec["fn"](y, m, d, L)
    if sysrec["n"] == 0:
        return float(v) % 360.0
    return (int(v) + 1) * 360.0 / sysrec["n"]

# ----------------------------------------------------------------------------------------------
# smoke test + optional corpus builder
# ----------------------------------------------------------------------------------------------
def smoke(verbose=False):
    """Run every system on 24 dates 1600-2000 with synthetic longitudes, assert ranges and
    boundaries.  Returns the number of (date, system) evaluations."""
    import math
    dates = [(1600, 1, 1), (1600, 2, 29), (1617, 7, 4), (1650, 12, 31), (1666, 9, 2), (1700, 3, 1),
             (1725, 11, 15), (1752, 9, 14), (1776, 7, 4), (1800, 1, 1), (1815, 6, 18), (1848, 2, 22),
             (1869, 10, 2), (1888, 5, 5), (1900, 2, 28), (1900, 3, 1), (1914, 8, 4), (1929, 10, 29),
             (1945, 8, 15), (1969, 7, 20), (1984, 2, 29), (1999, 12, 31), (2000, 1, 1), (2000, 12, 31)]
    keys = BODIES + ["true_node", "mean_lilith"]
    count = 0
    for di, (y, m, d) in enumerate(dates):
        # synthetic longitudes: deterministic, spread over the circle, including exact boundaries
        L = {}
        for bi, b in enumerate(keys):
            L[b] = ((y * 7.31 + m * 41.7 + d * 13.9 + bi * 97.3 + di * di * 3.7) % 360.0)
        if di % 3 == 0:    # exact boundaries: a nakshatra edge, a sign edge, 0, 359.999...
            L["moon"] = [0.0, NAK, 30.0, 359.999999][di // 3 % 4]
            L["sun"] = 180.0 if di % 6 else 0.0
        for s in SYSTEMS:
            v = s["fn"](y, m, d, L)
            if s["n"] == 0:
                assert isinstance(v, float) and 0.0 <= v < 360.0 and not math.isnan(v), (s["name"], v)
            else:
                assert isinstance(v, int) and 0 <= v < s["n"], (s["name"], v, s["n"])
            a = angle(s, y, m, d, L)
            assert 0.0 <= a <= 360.0, (s["name"], a)
            count += 1
        assert 0 <= vara(y, m, d) < 7
    # known anchors
    assert vara(2000, 1, 1, ) == 6, "2000-01-01 was a Saturday"
    assert vara(1969, 7, 20) == 0, "1969-07-20 was a Sunday"
    assert jdn(2000, 1, 1) == 2451545
    assert jdn(1600, 1, 1) == 2305448
    # table sanity
    assert len(GANA) == len(YONI) == len(NADI) == len(RAJJU) == 27
    assert sorted(set(GANA)) == [0, 1, 2] and GANA.count(0) == GANA.count(1) == GANA.count(2) == 9
    assert sorted(set(YONI)) == list(range(14))
    assert NADI.count(0) == NADI.count(1) == NADI.count(2) == 9
    assert RAJJU.count(4) == 3 and all(RAJJU.count(k) == 6 for k in range(4))
    # dasha logic anchors: Moon at 0 deg (Ashwini start) -> Ketu/Ketu; Moon at 13d20' -> Venus/Venus
    L0 = {b: 0.0 for b in keys}
    assert dasha_lord(L0) == 0 and antardasha_lord(L0) == 0 and pratyantar_lord(L0) == 0
    L1 = dict(L0); L1["moon"] = NAK
    assert dasha_lord(L1) == 1 and antardasha_lord(L1) == 1
    L2 = dict(L0); L2["moon"] = NAK * 0.999999          # end of Ashwini: last bhukti = Mercury
    assert dasha_lord(L2) == 0 and antardasha_lord(L2) == 8
    # karana anchors
    Lk = dict(L0); Lk["moon"] = 3.0;   assert karana_name(Lk) == 10       # Kimstughna
    Lk["moon"] = 6.5;                  assert karana_name(Lk) == 0        # Bava
    Lk["moon"] = 357.0;                assert karana_name(Lk) == 9        # Naga (h = 59)
    Lk["moon"] = 342.5;                assert karana_name(Lk) == 7        # Shakuni (h = 57)
    # vashya half-sign anchors
    assert vashya(240.0 + 5) == 1 and vashya(240.0 + 20) == 0 and vashya(270.0 + 5) == 0 and vashya(270.0 + 20) == 2
    # navamsa / dwadasamsa anchors
    assert navamsa(0.0) == 0 and navamsa(3.34) == 1 and navamsa(30.0) == 9 and navamsa(359.99) == 11
    assert dwadasamsa(0.0) == 0 and dwadasamsa(2.6) == 1 and dwadasamsa(30.0) == 0 and dwadasamsa(31.0) == 0 and dwadasamsa(33.0) == 1
    # Ketu = Rahu + 180 and the corpus spellings resolve
    assert rashi(_lon({"true_node": 10.0}, "ketu")) == 6 and _lon({"mean_lilith": 370.0}, "lilith") == 10.0
    if verbose:
        print(f"smoke: {len(dates)} dates x {len(SYSTEMS)} systems = {count} evaluations, all in range")
    return count

if __name__ == "__main__":
    import os, sys
    n = smoke(verbose=True)
    if "--build" in sys.argv:
        # AQ_DIR/systems_vedic.npz in the fitter's format (theta_a_sys, theta_b_sys, names, nstates)
        import numpy as np, pandas as pd
        D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
        full = pd.read_csv(f"{D_}/full.csv", dtype=str)
        Z = np.load(f"{D_}/phases.npz", allow_pickle=True)
        bodies = [str(b) for b in Z["bodies"]]
        def side(col, theta):
            out = np.empty((len(full), len(SYSTEMS)), np.float64)
            for r, (iso, row) in enumerate(zip(full[col], theta)):
                y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
                L = {b: float(v) for b, v in zip(bodies, row) if b not in ("ascendant", "medium_coeli")}
                for k, s in enumerate(SYSTEMS):
                    out[r, k] = angle(s, y, m, d, L)
            return out
        A = side("true_dob_a", Z["theta_a_train"]); B = side("true_dob_b", Z["theta_b_train"])
        out = f"{D_}/systems_vedic.npz"
        np.savez_compressed(out, theta_a_sys=A, theta_b_sys=B,
                            names=np.array([s["name"] for s in SYSTEMS]),
                            nstates=np.array([s["n"] for s in SYSTEMS]))
        print(f"wrote {out} · {len(SYSTEMS)} systems x {len(full):,} couples")
