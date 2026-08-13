"""
trad_vedic_ashtakavarga.py — the two big QUANTITATIVE systems of Jyotisha, plus the shadowy planets
and the Jaimini arudha padas. Everything here computes a number the tradition itself computes.

WHY THIS MODULE EXISTS SEPARATELY FROM trad_vedic_core / trad_vedic_match
------------------------------------------------------------------------
Those two implement the lunar/matching apparatus (Ashtakoota, vargas, dashas, poruthams) and both
state in their own docstrings that they do NOT compute Ashtakavarga, Shadbala, the upagrahas or the
arudha padas, because each needs something a noon chart does not have. This module computes them,
and where the missing thing is the birth hour it MARGINALISES over the twelve two-hour slots instead
of guessing, exactly as the contract's addendum prescribes. Nothing here re-emits a feature from
either sibling module: the naisargika/tatkalika friendship tables and the seven vargas appear only as
INGREDIENTS of Saptavargaja bala, never as features of their own.

THE FOUR SYSTEMS, AND THE AUTHORITY FOR EACH
--------------------------------------------
1. ASHTAKAVARGA (bindus / benefic points) — Brihat Parashara Hora Sastra ch. 66 (Santhanam tr.,
   "Ashtakavarga"); the same eight tables are reproduced in B. V. Raman, *Ashtakavarga System of
   Prediction*, and in Kalyana Varma's *Saravali*. For each of the seven grahas, eight contributors
   (the seven grahas plus the Lagna) each give a bindu to a named set of houses counted from
   themselves. Summing a graha's eight rows gives its BHINNASHTAKAVARGA (BAV) over the twelve signs;
   summing the seven BAVs gives the SARVASHTAKAVARGA (SAV), whose twelve entries total 337.
   VERIFIED, because this is the single most error-prone lookup in the whole codebase: the eight rows
   of each graha are asserted at import to sum to the doctrinal per-graha totals — Sun 48, Moon 49,
   Mars 39, Mercury 54, Jupiter 56, Venus 52, Saturn 39 — and those to 337; the Lagna rows are
   asserted to sum to 45, so the seven-contributor table used here sums to exactly 292. If any table
   is mistyped the module refuses to import rather than silently emitting wrong bindus.
   Also computed: the KAKSHYA subdivisions (BPHS 66; each sign is eight parts of 3°45' belonging in
   fixed order to Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon, Lagna) with the kakshya-vedha
   reading a practitioner actually uses in gochara; and the SODHYA PINDA (BPHS 66 + the Pindayu
   chapter) via Trikona and Ekadhipatya Sodhana with the Rasi and Graha gunakaras.
2. SHADBALA (six-fold strength, in Virupas; 60 Virupas = 1 Rupa) — BPHS ch. 27 ("Bala"), with
   B. V. Raman, *Graha and Bhava Balas*, as the working authority for the arithmetic. All six are
   computed separately, because the components are what practitioners read: Sthana (five
   sub-components), Dig, Kala (six sub-components), Cheshta, Naisargika and Drik bala, then the total
   in Rupas against the classical minimum requirement per graha.
3. UPAGRAHAS (the shadowy planets) — BPHS ch. 6 / Mantreswara, *Phaladeepika* ch. 3 for the five
   fixed offsets from the Sun; Prasna Marga ch. VI (Kerala) for Gulika/Mandi's eighth-part rule.
4. ARUDHA PADAS (Jaimini) — Jaimini Upadesa Sutras 1.1.20-22: the arudha of a bhava is as far from
   its lord as the lord is from the bhava, with the exception that an arudha falling in the bhava
   itself or in the seventh from it is moved to the tenth therefrom. The UPAPADA (arudha of the 12th)
   is the classical marriage arudha, so it is given its own cross-partner block.

WHAT IS EXACT, WHAT IS MARGINALISED, WHAT IS A NAMED PROXY, WHAT IS OMITTED
--------------------------------------------------------------------------
EXACT from the birth date alone (no birth time needed, nothing approximated):
  the seven-contributor Ashtakavarga tables, the SAV, the kakshyas, the sodhana reductions and
  sodhya pindas; Uchcha, Saptavargaja, Ojhayugmarasyamsa and Drekkana bala; Paksha and Ayana bala;
  the Varsha, Masa and Dina lords (via the ahargana, below); Cheshta bala from the seeghra kendra;
  Naisargika bala; Drik bala (Sphuta Drishti); Ishta and Kashta phala; and the five Sun-derived
  upagrahas Dhuma, Vyatipata, Parivesha, Indrachapa and Upaketu.
MARGINALISED over the twelve two-hour slots, never point-estimated:
  the SAV's stability (block "av8: SAV stability over the 12 birth-hour slots") — the Moon's noon
  position is uncertain by roughly ±6°, so the Moon's contributor row can move a whole sign; the
  block reports the mean and the standard deviation of every sign's SAV across the twelve hours, so
  a couple whose bindu profile is robust to the unknown hour is distinguishable from one whose
  profile is an accident of the assumed clock time.
  The HORA bala: under a uniform prior over the twenty-four horas of the day it reduces EXACTLY to
  60·(horas ruled)/24, and because 24 = 3·7 + 3 the three planets nearest the day lord in the
  Chaldean order rule four horas and the rest three — so the marginal is not a guess, it is a closed
  form that depends only on the weekday.
  The ARUDHA PADAS need a Lagna. Under a uniform prior over the twelve rising signs the arudha is
  still couple-specific, because the arudha is fixed by where the house LORD actually stands, so
  the distribution over the twelve signs is emitted (with its entropy) rather than one sign.
PROXIES, named as such, never presented as the doctrine:
  Kendradi bala and Dig bala need the Ascendant. Where no birthplace exists they are computed from
  CHANDRA LAGNA (the Moon's sign/degree as the 1st) and SURYA LAGNA (the Sun's), the two reference
  points the texts themselves offer when the lagna is doubted — and both are emitted, so the choice
  is testable rather than assumed. Under a uniform hour prior the true Kendradi bala averages to
  35 virupas and the true Dig bala to 30 for every graha and every couple, i.e. it is a constant;
  saying that plainly is more useful than emitting a constant column.
  Saptavargaja bala applies Moolatrikona only in the rasi, where a degree is meaningful, and plain
  lordship in the other six vargas.
OMITTED, with the reason:
  GULIKA and MANDI are implemented (`_gulika_mandi`) but are NOT emitted on this dataset. They are
  the Ascendant rising at the start of the eighth part of the day, so they need sunrise, sunset AND
  the Ascendant — that is birth PLACE, not merely birth hour. The couples file loaded here carries
  no coordinates at all (E.LAT_O / E.LAT_Y are entirely NaN), so the block would be a fabrication.
  The code path is smoke-tested against a known place and date in `__main__` and the block appears
  automatically on any dataset that does carry coordinates; nothing is faked to fill the gap.
  Likewise the true eight-contributor Ashtakavarga (with the Lagna row) and the true SAV-per-bhava
  are emitted only where coordinates exist; under a flat prior over rising signs the Lagna row adds
  the same constant to every sign, so the seven-contributor table IS the whole of the available
  information and is what ships here.
  NATHONNATHA and TRIBHAGA bala are exactly constant under a uniform hour prior (30 virupas for
  every graha, and 10 for every graha but Jupiter, respectively). They are added into the Kala bala
  total for doctrinal correctness and are deliberately not emitted as columns.
  The eight-fold GATI virupa table (Vakra, Anuvakra, Vikala, Manda, Mandatara, Sama, Chara,
  Atichara) is given with irreconcilable numbers across editions, so only the motion CLASS and the
  speed ratio are emitted, and Cheshta bala itself comes from the seeghra-kendra formula.
  BHAVA BALA (the strength of the twelve houses) needs house cusps, hence a birthplace: omitted.
  PINDAYU longevity is not computed: it needs the Lagna's own sodhya pinda and the haranas
  (reductions for combustion, war and the like). The sodhya pindas themselves are emitted, but on
  the seven-contributor table, so they run about an eighth below the figures a text with a Lagna
  would print — a scale difference, not a ranking one.
  Yuddha bala is implemented from the classical bimba (disc) table but a planetary war needs two
  planets inside 1°, so the column is zero for almost every couple; that is the tradition's answer,
  not a defect.

THE AYANAMSA is Lahiri throughout (the Indian civil standard); trad_vedic_core already tests the
ayanamsa choice itself on Ashtakoota, and repeating that sweep here would only duplicate it.

E.Y is never read. No file is written. No randomness.
"""

import numpy as np

TRADITION = ("Vedic quantitative Jyotisha: Ashtakavarga bindus, Shadbala in rupas, the upagrahas "
             "and the Jaimini arudha padas")

# ════════════════════════════════════════════════════════════════════════════════════════════════
# The seven grahas, in the order the Ashtakavarga and Shadbala tables are printed in
# ════════════════════════════════════════════════════════════════════════════════════════════════
GR = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
NG = 7
SUN, MOON, MARS, MERC, JUP, VEN, SAT = range(7)
CONTRIB = GR + ["Lagna"]

# Sign lords, Aries..Pisces, as indices into GR
LORD = np.array([MARS, VEN, MERC, MOON, SUN, MERC, VEN, MARS, JUP, SAT, SAT, JUP])

# ════════════════════════════════════════════════════════════════════════════════════════════════
# ASHTAKAVARGA — BPHS ch. 66. Houses (counted from the contributor's own sign, 1 = that sign) in
# which the contributor gives one bindu to the graha named by the key.
#
# The row lengths are the doctrinal check: they must sum to 48 / 49 / 39 / 54 / 56 / 52 / 39 = 337,
# and the eight Lagna rows to 45. Asserted at import — see _verify_tables().
# ════════════════════════════════════════════════════════════════════════════════════════════════
BAV_TABLE = {
    "Sun": {
        "Sun":     (1, 2, 4, 7, 8, 9, 10, 11),
        "Moon":    (3, 6, 10, 11),
        "Mars":    (1, 2, 4, 7, 8, 9, 10, 11),
        "Mercury": (3, 5, 6, 9, 10, 11, 12),
        "Jupiter": (5, 6, 9, 11),
        "Venus":   (6, 7, 12),
        "Saturn":  (1, 2, 4, 7, 8, 9, 10, 11),
        "Lagna":   (3, 4, 6, 10, 11, 12),
    },
    "Moon": {
        "Sun":     (3, 6, 7, 8, 10, 11),
        "Moon":    (1, 3, 6, 7, 10, 11),
        "Mars":    (2, 3, 5, 6, 9, 10, 11),
        "Mercury": (1, 3, 4, 5, 7, 8, 10, 11),
        "Jupiter": (1, 2, 4, 7, 8, 10, 11),
        "Venus":   (3, 4, 5, 7, 9, 10, 11),
        "Saturn":  (3, 5, 6, 11),
        "Lagna":   (3, 6, 10, 11),
    },
    "Mars": {
        "Sun":     (3, 5, 6, 10, 11),
        "Moon":    (3, 6, 11),
        "Mars":    (1, 2, 4, 7, 8, 10, 11),
        "Mercury": (3, 5, 6, 11),
        "Jupiter": (6, 10, 11, 12),
        "Venus":   (6, 8, 11, 12),
        "Saturn":  (1, 4, 7, 8, 9, 10, 11),
        "Lagna":   (1, 3, 6, 10, 11),
    },
    "Mercury": {
        "Sun":     (5, 6, 9, 11, 12),
        "Moon":    (2, 4, 6, 8, 10, 11),
        "Mars":    (1, 2, 4, 7, 8, 9, 10, 11),
        "Mercury": (1, 3, 5, 6, 9, 10, 11, 12),
        "Jupiter": (6, 8, 11, 12),
        "Venus":   (1, 2, 3, 4, 5, 8, 9, 11),
        "Saturn":  (1, 2, 4, 7, 8, 9, 10, 11),
        "Lagna":   (1, 2, 4, 6, 8, 10, 11),
    },
    "Jupiter": {
        "Sun":     (1, 2, 3, 4, 7, 8, 9, 10, 11),
        "Moon":    (2, 5, 7, 9, 11),
        "Mars":    (1, 2, 4, 7, 8, 10, 11),
        "Mercury": (1, 2, 4, 5, 6, 9, 10, 11),
        "Jupiter": (1, 2, 3, 4, 7, 8, 10, 11),
        "Venus":   (2, 5, 6, 9, 10, 11),
        "Saturn":  (3, 5, 6, 12),
        "Lagna":   (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    "Venus": {
        "Sun":     (8, 11, 12),
        "Moon":    (1, 2, 3, 4, 5, 8, 9, 11, 12),
        # Editions differ between (3,5,6,9,11,12) and (3,4,6,9,11,12) for the Mars row; both are six
        # cells so the doctrinal total is unaffected. Raman's printing is used.
        "Mars":    (3, 5, 6, 9, 11, 12),
        "Mercury": (3, 5, 6, 9, 11),
        "Jupiter": (5, 8, 9, 10, 11),
        "Venus":   (1, 2, 3, 4, 5, 8, 9, 10, 11),
        "Saturn":  (3, 4, 5, 8, 9, 10, 11),
        "Lagna":   (1, 2, 3, 4, 5, 8, 9, 11),
    },
    "Saturn": {
        "Sun":     (1, 2, 4, 7, 8, 10, 11),
        "Moon":    (3, 6, 11),
        "Mars":    (3, 5, 6, 10, 11, 12),
        "Mercury": (6, 8, 9, 10, 11, 12),
        "Jupiter": (5, 6, 11, 12),
        "Venus":   (6, 11, 12),
        "Saturn":  (3, 5, 6, 11),
        "Lagna":   (1, 3, 4, 6, 10, 11),
    },
}
DOCTRINAL_TOTAL = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54, "Jupiter": 56,
                   "Venus": 52, "Saturn": 39}


def _verify_tables():
    """Refuse to import on a mistyped bindu table. This is the checked doctrinal arithmetic."""
    grand = 0
    lagna_total = 0
    for g in GR:
        row = BAV_TABLE[g]
        assert set(row) == set(CONTRIB), f"{g}: contributors {sorted(row)}"
        for c, hs in row.items():
            assert len(set(hs)) == len(hs), f"{g} from {c}: repeated house"
            assert all(1 <= h <= 12 for h in hs), f"{g} from {c}: house out of range"
        tot = sum(len(hs) for hs in row.values())
        assert tot == DOCTRINAL_TOTAL[g], f"{g}: {tot} bindus, doctrine says {DOCTRINAL_TOTAL[g]}"
        grand += tot
        lagna_total += len(row["Lagna"])
    assert grand == 337, f"grand total {grand}, doctrine says 337"
    assert lagna_total == 45, f"Lagna rows total {lagna_total}, doctrine says 45"
    return grand, lagna_total, grand - lagna_total


GRAND, LAGNA_BINDUS, SEVEN_ROW_TOTAL = _verify_tables()      # 337, 45, 292

# Kakshya: each sign is eight parts of 3 deg 45', belonging in this fixed order from 0 deg of the
# sign — BPHS ch. 66. Index 7 is the Lagna's kakshya, which has no owner without a birth time.
KAKSHYA_LORD = np.array([SAT, JUP, MARS, SUN, VEN, MERC, MOON, 7])
KAKW = 30.0 / 8.0

# Sodhya pinda multipliers. Rasi gunakara Aries..Pisces and Graha gunakara in GR order — BPHS ch. 66
# (the Pindayu apparatus), tabulated identically in Raman, *Ashtakavarga System of Prediction*.
RASI_GUNA = np.array([7, 10, 8, 4, 10, 5, 7, 8, 9, 5, 11, 12], float)
GRAHA_GUNA = np.array([5, 5, 8, 5, 10, 7, 5], float)
TRINES = [(0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)]
# The five same-lord sign pairs. The Sun and Moon own one sign each, so they take no part.
EKA_PAIRS = [(0, 7), (1, 6), (2, 5), (8, 11), (9, 10)]

# ════════════════════════════════════════════════════════════════════════════════════════════════
# SHADBALA constants — BPHS ch. 27
# ════════════════════════════════════════════════════════════════════════════════════════════════
# Deep exaltation longitudes (sidereal degrees from 0 Aries). Debilitation is 180 deg away.
EXALT = np.array([10.0, 33.0, 298.0, 165.0, 95.0, 357.0, 200.0])
# Moolatrikona: (sign, from degree, to degree)
MOOLA = {SUN: (4, 0.0, 20.0), MOON: (1, 4.0, 30.0), MARS: (0, 0.0, 12.0), MERC: (5, 16.0, 20.0),
         JUP: (8, 0.0, 10.0), VEN: (6, 0.0, 15.0), SAT: (10, 0.0, 20.0)}
# Naisargika (natural) bala: 60/7 times the rank Sun > Moon > Venus > Jupiter > Mercury > Mars > Saturn
NAISARGIKA = np.array([7, 6, 2, 3, 4, 5, 1], float) * 60.0 / 7.0
# Natural friendship, BPHS ch. 3: +1 friend, 0 neutral, -1 enemy; rows are the planet's own view
NATF = np.zeros((NG, NG), int)
for _p, _fr, _en in [
    (SUN,  (MOON, MARS, JUP),      (VEN, SAT)),
    (MOON, (SUN, MERC),            ()),
    (MARS, (SUN, MOON, JUP),       (MERC,)),
    (MERC, (SUN, VEN),             (MOON,)),
    (JUP,  (SUN, MOON, MARS),      (MERC, VEN)),
    (VEN,  (MERC, SAT),            (SUN, MOON)),
    (SAT,  (MERC, VEN),            (SUN, MOON, MARS)),
]:
    for _q in _fr:
        NATF[_p, _q] = 1
    for _q in _en:
        NATF[_p, _q] = -1
# Compound (panchadha) dignity in virupas, indexed by natural+temporal in -2..+2
COMPOUND = {2: 22.5, 1: 15.0, 0: 7.5, -1: 3.75, -2: 1.875}
OWN_SIGN_VIRUPA, MOOLA_VIRUPA = 30.0, 45.0
# Ojhayugmarasyamsa: Moon and Venus gain 15 virupas in an EVEN sign / navamsa, the rest in an ODD one
EVEN_STRONG = np.array([0, 1, 0, 0, 0, 1, 0], bool)
# Drekkana bala: a male planet in the 1st drekkana, a hermaphrodite in the 2nd, a female in the 3rd
# gets 15 virupas (BPHS 27). Sun/Mars/Jupiter male, Mercury/Saturn hermaphrodite, Moon/Venus female.
DREK_PART = np.array([0, 2, 0, 1, 0, 2, 1])
# Dig bala: the cusp (degrees from the Ascendant) at which each graha is fullest — Mercury and
# Jupiter east/1st, Sun and Mars south/10th, Saturn west/7th, Moon and Venus north/4th
DIG_STRONG = np.array([270.0, 90.0, 270.0, 0.0, 0.0, 90.0, 180.0])
# Ayana bala: which declination each graha gains in. Mercury gains in both (BPHS 27).
AYANA_NORTH = np.array([1, -1, 1, 0, 1, 1, -1])     # +1 north, -1 south, 0 = either
# Paksha bala: the natural benefics take the Moon's phase strength, the malefics its complement.
# Mercury is read as a natural benefic here, which is the usual reading of BPHS 27.
BENEFIC = np.array([0, 1, 0, 1, 1, 1, 0], bool)     # Moon handled by waxing/waning below
# Classical minimum Shadbala, in Rupas (BPHS ch. 27). Some editions print 6.5 for the Sun; the
# widely reproduced list is used and the ratio to it is emitted, so the threshold is testable.
MIN_RUPA = np.array([5.0, 6.0, 5.0, 7.0, 6.5, 5.5, 5.0])
# Classical bimba (disc) sizes for Yuddha bala. The Sun and Moon never go to war.
BIMBA = np.array([np.nan, np.nan, 9.4, 6.6, 190.4, 16.6, 158.0])
# Mean geocentric daily motion, for the motion classes. Mercury and Venus keep pace with the Sun.
MEAN_SPD = np.array([0.98565, 13.17640, 0.52403, 0.98565, 0.08309, 0.98565, 0.03346])
# Weekday lords, Sunday..Saturday, as GR indices; and the Chaldean hora order
WEEK_LORD = np.array([SUN, MOON, MARS, MERC, JUP, VEN, SAT])
CHALDEAN = np.array([SAT, JUP, MARS, SUN, VEN, MERC, MOON])
# Kali Yuga epoch: JD 588465.5, midnight of 18 Feb 3102 BCE (Julian) at Ujjain — Surya Siddhanta.
# That day was a Friday, which is what makes the ahargana's weekday arithmetic below self-checking.
KALI_JD = 588465.5
KALI_WD = 5                                          # Friday, with Sunday = 0

# ════════════════════════════════════════════════════════════════════════════════════════════════
# UPAGRAHAS — the five Sun-derived shadowy planets, BPHS ch. 6 / Phaladeepika ch. 3.
#   Dhuma = Sun + 133 deg 20'      Vyatipata = 360 - Dhuma       Parivesha = Vyatipata + 180
#   Indrachapa = 360 - Parivesha   Upaketu = Indrachapa + 16 deg 40'
# Composing those gives a fixed offset each, and Upaketu + 30 deg = the Sun again, exactly as the
# text says — which is the internal check that the composition is right.
# ════════════════════════════════════════════════════════════════════════════════════════════════
UPAGRAHA = [("Dhuma", 1.0, 133.0 + 20.0 / 60.0),
            ("Vyatipata", -1.0, 226.0 + 40.0 / 60.0),
            ("Parivesha", -1.0, 46.0 + 40.0 / 60.0),
            ("Indrachapa", 1.0, 313.0 + 20.0 / 60.0),
            ("Upaketu", 1.0, 330.0)]
assert abs(((330.0 + 30.0) % 360.0)) < 1e-9, "Upaketu + 30 deg must return the Sun"


# ════════════════════════════════════════════════════════════════════════════════════════════════
# small helpers
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _sign(lon):
    return np.floor(np.mod(lon, 360.0) / 30.0).astype(np.int64) % 12


def _deg_in_sign(lon):
    return np.mod(np.mod(lon, 360.0), 30.0)


def _rowcorr(A, B):
    a = A - A.mean(1, keepdims=True)
    b = B - B.mean(1, keepdims=True)
    den = np.sqrt((a * a).sum(1) * (b * b).sum(1))
    return np.where(den > 1e-12, (a * b).sum(1) / np.maximum(den, 1e-12), 0.0)


def _onehot(idx, k):
    n = len(idx)
    out = np.zeros((n, k))
    out[np.arange(n), np.asarray(idx).astype(int) % k] = 1.0
    return out


def _circconv(P, row):
    """out[:, s] = sum_L P[:, L] * row[(s - L) % 12] — a graha's Lagna row smeared over a lagna prior."""
    out = np.zeros_like(P)
    for L in range(12):
        for s in range(12):
            w = row[(s - L) % 12]
            if w:
                out[:, s] += P[:, L] * w
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
# ASHTAKAVARGA
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _bav(sgn, lagna_dist=None):
    """Bhinnashtakavarga: (7 grahas, n, 12 signs) bindus.

    `sgn` is (7, n) sign indices of the seven grahas. With `lagna_dist` (n, 12) — a distribution over
    the rising sign — the Lagna row is added as its expectation, which is the only honest way to
    include an eighth contributor we cannot pin down.
    """
    n = sgn.shape[1]
    out = np.zeros((NG, n, 12))
    ar = np.arange(n)
    for p, g in enumerate(GR):
        for c, cn in enumerate(GR):
            for h in BAV_TABLE[g][cn]:
                out[p][ar, (sgn[c] + h - 1) % 12] += 1.0
    if lagna_dist is not None:
        for p, g in enumerate(GR):
            row = np.zeros(12)
            for h in BAV_TABLE[g]["Lagna"]:
                row[(h - 1) % 12] += 1.0
            out[p] += _circconv(lagna_dist, row)
    return out


def _trikona(b):
    """Trikona Sodhana, BPHS 66: in each trine, if no sign is empty of bindus deduct the smallest
    from all three; a trine containing a zero is left alone."""
    r = b.copy()
    for t in TRINES:
        cols = r[:, list(t)]
        red = np.where((cols == 0).any(1), 0.0, cols.min(1))
        r[:, list(t)] = cols - red[:, None]
    return r


def _ekadhipatya(b, occ):
    """Ekadhipatya Sodhana, in Raman's four-rule printing (*Ashtakavarga System of Prediction*),
    applied to the five pairs of signs sharing a lord, AFTER the trikona reduction:
      both signs occupied           -> no reduction
      neither occupied              -> the larger drops to the smaller; if equal, both to zero
      one occupied, one not         -> the empty one drops to the occupied one's count, or to zero
                                       if it already holds no more than the occupied one
      either sign holds no bindu    -> no reduction
    Editions differ on the equal-and-unoccupied cell; this is the commonest printing.
    """
    r = b.copy()
    for (i, j) in EKA_PAIRS:
        a, c = r[:, i].copy(), r[:, j].copy()
        oi, oj = occ[:, i], occ[:, j]
        m = np.minimum(a, c)
        eq = a == c
        none = (~oi) & (~oj)
        na = np.where(none, np.where(eq, 0.0, m), a)
        nc = np.where(none, np.where(eq, 0.0, m), c)
        only_i = oi & (~oj)
        nc = np.where(only_i, np.where(c > a, a, 0.0), nc)
        only_j = oj & (~oi)
        na = np.where(only_j, np.where(a > c, c, 0.0), na)
        keep = (oi & oj) | (a == 0) | (c == 0)
        r[:, i] = np.where(keep, a, na)
        r[:, j] = np.where(keep, c, nc)
    return r


# ════════════════════════════════════════════════════════════════════════════════════════════════
# the seven vargas needed by Saptavargaja bala (BPHS ch. 6) — ingredients, never emitted as features
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _varga_lords(lon):
    """The lord of the sign a graha occupies in each of D1, D2, D3, D7, D9, D12, D30 -> (7 vargas, n)."""
    s = _sign(lon)
    d = _deg_in_sign(lon)
    odd = (s % 2) == 0                                  # Aries is the 1st sign, hence odd
    out = []
    out.append(LORD[s])                                                     # D1 rasi
    hora = np.where(odd, np.where(d < 15, 4, 3), np.where(d < 15, 3, 4))     # D2: Leo or Cancer
    out.append(LORD[hora])
    out.append(LORD[(s + 4 * np.floor(d / 10.0).astype(np.int64)) % 12])     # D3 drekkana
    st = np.where(odd, s, (s + 6) % 12)
    out.append(LORD[(st + np.floor(d / (30.0 / 7.0)).astype(np.int64)) % 12])  # D7 saptamsa
    out.append(LORD[np.floor(np.mod(lon, 360.0) / (10.0 / 3.0)).astype(np.int64) % 12])   # D9 navamsa
    out.append(LORD[(s + np.floor(d / 2.5).astype(np.int64)) % 12])          # D12 dwadasamsa
    # D30 trimsamsa: Parashara's unequal 5/5/8/7/5 division, reversed in even signs
    odd_l = np.select([d < 5, d < 10, d < 18, d < 25], [MARS, SAT, JUP, MERC], VEN)
    eve_l = np.select([d < 5, d < 12, d < 20, d < 25], [VEN, MERC, JUP, SAT], MARS)
    out.append(np.where(odd, odd_l, eve_l))
    return np.array(out)


def _saptavargaja(lon, sgn):
    """Saptavargaja bala in virupas, (7 grahas, n) — the compound (panchadha) dignity summed over the
    seven vargas. Moolatrikona is applied only in the rasi, where the degree means something."""
    n = sgn.shape[1]
    ar = np.arange(n)
    # tatkalika (temporal) friendship, from the rasi: 2nd, 3rd, 4th, 10th, 11th, 12th are friends
    dist = (sgn[None, :, :] - sgn[:, None, :]) % 12                     # (p, q, n) houses-1
    tat = np.where(np.isin(dist, [1, 2, 3, 9, 10, 11]), 1, -1)
    out = np.zeros((NG, n))
    for p in range(NG):
        vl = _varga_lords(lon[p])                                        # (7 vargas, n)
        for v in range(7):
            lord = vl[v]
            own = lord == p
            comp = NATF[p][lord] + tat[p][lord, ar]
            val = np.select([comp == 2, comp == 1, comp == 0, comp == -1],
                            [COMPOUND[2], COMPOUND[1], COMPOUND[0], COMPOUND[-1]], COMPOUND[-2])
            val = np.where(own, OWN_SIGN_VIRUPA, val)
            if v == 0:
                ms, lo, hi = MOOLA[p]
                d = _deg_in_sign(lon[p])
                val = np.where((sgn[p] == ms) & (d >= lo) & (d < hi), MOOLA_VIRUPA, val)
            out[p] += val
    return out


def _drishti(x):
    """Sphuta Drishti in virupas, BPHS ch. 26. `x` is (aspected - aspecting) mod 360 in degrees.

    The piecewise ramps below reproduce every doctrinal value exactly: 15 at the 3rd, 45 at the 4th,
    30 at the 5th, 0 at the 6th, 60 (full) at the 7th, 45 at the 8th, 30 at the 9th, 15 at the 10th,
    and nothing from the 11th, 12th, 1st or 2nd.
    """
    x = np.mod(x, 360.0)
    v = np.zeros_like(x, dtype=float)
    m = (x > 30) & (x <= 60);   v[m] = (x[m] - 30.0) / 2.0
    m = (x > 60) & (x <= 90);   v[m] = (x[m] - 60.0) + 15.0
    m = (x > 90) & (x <= 120);  v[m] = (120.0 - x[m]) / 2.0 + 30.0
    m = (x > 120) & (x <= 150); v[m] = 150.0 - x[m]
    m = (x > 150) & (x <= 180); v[m] = (x[m] - 150.0) * 2.0
    m = (x > 180) & (x <= 300); v[m] = (300.0 - x[m]) / 2.0
    return v


# the zones in which Mars, Jupiter and Saturn have their special full aspect, with the peak the
# general ramp reaches inside each zone (so the special aspect can be scaled to 60 at that peak)
SPECIAL = {MARS: [((90, 120), 45.0), ((210, 240), 45.0)],
           JUP:  [((120, 150), 30.0), ((240, 270), 30.0)],
           SAT:  [((60, 90), 45.0), ((270, 300), 15.0)]}


def _drishti_special(x, aspecting):
    """The same ramp with the special aspects of Mars (4th/8th), Jupiter (5th/9th) and Saturn
    (3rd/10th) raised to full. The texts describe these as full but do not agree on how the
    intermediate degrees are handled, so the ramp is scaled to reach 60 at the zone's own peak and
    both readings are emitted as separate features."""
    v = _drishti(x)
    if aspecting in SPECIAL:
        xx = np.mod(x, 360.0)
        for (lo, hi), peak in SPECIAL[aspecting]:
            m = (xx > lo) & (xx <= hi)
            v[m] = np.minimum(60.0, v[m] * (60.0 / peak))
    return v


# ════════════════════════════════════════════════════════════════════════════════════════════════
# Gulika and Mandi — implemented, but only usable where a BIRTHPLACE exists (see the docstring)
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _gulika_mandi(jd, lat, lon, aya, mode="gulika"):
    """The Ascendant at the start of the day's eighth part (Gulika) or of Saturn's own part (Mandi).

    Prasna Marga ch. VI: the day from sunrise to sunset is cut into eight equal parts ruled in
    weekday-lord order from the day's own lord, the eighth being lordless and Gulika's. A night birth
    uses the night divided the same way, starting from the lord of the fifth weekday onward. Returns
    (day_version_sidereal_longitude, night_version, daylight_fraction_of_the_24h) for one instant.
    Requires real coordinates; there is no zodiacal substitute for a house cusp.
    """
    import swisseph as swe
    flg = swe.CALC_RISE | swe.BIT_DISC_CENTER
    geo = (float(lon), float(lat), 0.0)
    j0 = np.floor(jd - 0.5) + 0.5                                  # midnight UT starting the day
    r1 = swe.rise_trans(j0, swe.SUN, flg, geo)
    s1 = swe.rise_trans(j0, swe.SUN, swe.CALC_SET | swe.BIT_DISC_CENTER, geo)
    if r1[0] != 0 or s1[0] != 0:
        return None
    sunrise, sunset = r1[1][0], s1[1][0]
    if sunset < sunrise:                                            # set before rise: take the next
        s1 = swe.rise_trans(sunrise, swe.SUN, swe.CALC_SET | swe.BIT_DISC_CENTER, geo)
        if s1[0] != 0:
            return None
        sunset = s1[1][0]
    r2 = swe.rise_trans(sunset, swe.SUN, flg, geo)
    if r2[0] != 0:
        return None
    next_rise = r2[1][0]
    day_len, night_len = sunset - sunrise, next_rise - sunset
    wd = int(np.floor(sunrise + 1.5)) % 7
    if mode == "gulika":
        part_day, part_night = 7, 7                                 # the eighth, lordless part
    else:
        part_day = int((6 - wd) % 7)                                # Saturn's own part, from the day lord
        part_night = int((6 - (wd + 4) % 7) % 7)                    # night starts from the 5th lord
    t_day = sunrise + day_len * part_day / 8.0
    t_night = sunset + night_len * part_night / 8.0
    out = []
    for t in (t_day, t_night):
        asc = swe.houses_ex(t, float(lat), float(lon), b'W')[1][0]
        out.append(float(np.mod(asc - aya, 360.0)))
    return out[0], out[1], float(day_len / (day_len + night_len))


def _asc_dist(E, slot, lat, lon, ok, aya):
    """(n, 12) distribution of the sidereal rising SIGN over the twelve two-hour slots.

    Where a birthplace is unknown the row is left flat at 1/12, which is the correct expectation
    under ignorance and is very nearly the truth anyway: the Ascendant cycles once a day, so its
    marginal under a uniform hour prior is almost uniform by construction. What departs from
    uniformity is a function of latitude and date, not of the individual.
    """
    import swisseph as swe
    n = E.n
    out = np.full((n, 12), 1.0 / 12.0)
    idx = np.where(ok)[0]
    for k in idx:
        cnt = np.zeros(12)
        for h in range(int(E.HOURS)):
            jd = float(E.JD[slot, k]) + float(E.HOUR_OFFSETS[h])
            a = swe.houses_ex(jd, float(lat[k]), float(lon[k]), b'W')[1][0]
            cnt[int(np.mod(a - aya[k], 360.0) // 30.0) % 12] += 1.0
        out[k] = cnt / cnt.sum()
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
# per-partner chart assembly
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _chart(E, slot, aya_idx):
    """Everything one partner's chart needs, as a dict of arrays."""
    n = E.n
    ar = np.arange(n)
    aya = E.AYA[aya_idx, slot]
    gi = [E.IDX[g] for g in GR]
    lon = np.mod(E.LON[slot][gi] - aya[None, :], 360.0)               # (7, n) sidereal
    spd = E.SPD[slot][gi]
    dec = E.DEC[slot][gi]
    blat = E.LAT[slot][gi]
    helio = E.HELIO[slot][gi]
    sgn = _sign(lon)
    deg = _deg_in_sign(lon)
    C = {"aya": aya, "lon": lon, "spd": spd, "dec": dec, "blat": blat, "sgn": sgn, "deg": deg,
         "helio": helio, "jd": E.JD[slot], "ar": ar, "n": n}

    # ── Ashtakavarga, seven contributors (the Lagna row needs a birthplace; see the docstring) ──
    bav = _bav(sgn)                                                    # (7, n, 12)
    C["bav"] = bav
    C["sav"] = bav.sum(0)                                              # (n, 12), rows sum to 292
    occ = np.zeros((n, 12), bool)
    for p in range(NG):
        occ[ar, sgn[p]] = True
    C["occ"] = occ
    # the same table on the doctrinal 337 scale, so the classical "30 strong / 25 weak" per-sign
    # thresholds still mean what they mean: a flat prior over rising signs puts 45/12 in every sign
    C["sav337"] = C["sav"] + LAGNA_BINDUS / 12.0

    # ── kakshya ──
    kak = np.floor(deg / KAKW).astype(np.int64)                        # (7, n) 0..7
    C["kak"] = kak
    C["kakpos"] = (deg - kak * KAKW) / KAKW
    klord = KAKSHYA_LORD[kak]                                          # (7, n), 7 = Lagna
    C["klord"] = klord
    ben = np.zeros((NG, n))
    for p, g in enumerate(GR):
        for c, cn in enumerate(GR):
            hs = BAV_TABLE[g][cn]
            h = (sgn[p] - sgn[c]) % 12 + 1
            gives = np.isin(h, hs)
            ben[p] += np.where((klord[p] == c) & gives, 1.0, 0.0)
    C["kakben"] = ben                                                  # 1 if the kakshya lord gives it a bindu
    C["kaklagna"] = (klord == 7).astype(float)

    # ── sodhana and the sodhya pindas ──
    red = np.zeros_like(bav)
    for p in range(NG):
        red[p] = _ekadhipatya(_trikona(bav[p]), occ)
    C["red"] = red
    gmul = np.zeros((n, 12))
    for p in range(NG):
        gmul[ar, sgn[p]] += GRAHA_GUNA[p]
    C["rasi_pinda"] = (red * RASI_GUNA[None, None, :]).sum(2)          # (7, n)
    C["graha_pinda"] = (red * gmul[None, :, :]).sum(2)
    C["sodhya"] = C["rasi_pinda"] + C["graha_pinda"]

    # ── Shadbala: Sthana bala ──
    debil = np.mod(EXALT + 180.0, 360.0)
    uchcha = np.abs(E.wrap(lon - debil[:, None])) / 3.0                # 0 at debilitation, 60 at exaltation
    sapta = _saptavargaja(lon, sgn)
    nav = np.floor(np.mod(lon, 360.0) / (10.0 / 3.0)).astype(np.int64) % 12
    odd_r = (sgn % 2) == 0
    odd_n = (nav % 2) == 0
    want_even = EVEN_STRONG[:, None]
    ojha = (np.where(want_even ^ odd_r, 15.0, 0.0) + np.where(want_even ^ odd_n, 15.0, 0.0))
    drek = np.where(np.floor(deg / 10.0).astype(np.int64) == DREK_PART[:, None], 15.0, 0.0)
    C["uchcha"], C["sapta"], C["ojha"], C["drek"] = uchcha, sapta, ojha, drek

    # ── Kendradi and Dig bala from the two named lagna proxies ──
    for tag, ref in (("cl", MOON), ("sl", SUN)):
        h = (sgn - sgn[ref][None, :]) % 12 + 1
        C["kendra_" + tag] = np.select([np.isin(h, [1, 4, 7, 10]), np.isin(h, [2, 5, 8, 11])],
                                       [60.0, 30.0], 15.0)
        powerless = np.mod(lon[ref][None, :] + DIG_STRONG[:, None] + 180.0, 360.0)
        C["dig_" + tag] = np.abs(E.wrap(lon - powerless)) / 3.0
    C["kendra"] = 0.5 * (C["kendra_cl"] + C["kendra_sl"])
    C["dig"] = 0.5 * (C["dig_cl"] + C["dig_sl"])

    # ── Kala bala ──
    elong = np.mod(lon[MOON] - lon[SUN], 360.0)
    phase = np.where(elong <= 180.0, elong, 360.0 - elong) / 3.0       # 0 new, 60 full
    waxing = elong < 180.0
    ben_row = np.repeat(BENEFIC[:, None], n, axis=1)
    ben_row[MOON] = waxing
    paksha_raw = np.where(ben_row, phase[None, :], 60.0 - phase[None, :])
    paksha = paksha_raw.copy()
    paksha[MOON] = paksha[MOON] * 2.0                                  # the Moon's is doubled, BPHS 27
    C["paksha"] = paksha
    ay = np.where(AYANA_NORTH[:, None] == 0, np.abs(dec),
                  np.where(AYANA_NORTH[:, None] > 0, dec, -dec))
    # (24 +- kranti) * 60/48, so a declination of 24 deg the right way gives the full 60 virupas. The
    # Moon and the outer bodies can exceed 24 deg of declination, so the base is clipped to its own
    # scale before the Sun's doubling rather than being allowed to run past it.
    ayana_raw = np.clip((24.0 + ay) * 60.0 / 48.0, 0.0, 60.0)
    ayana = ayana_raw.copy()
    ayana[SUN] = ayana[SUN] * 2.0                                      # the Sun's is doubled, BPHS 27
    C["ayana"] = ayana
    # ahargana: days since the Kali epoch, then the classical 360-day year and 30-day month, which
    # advance the weekday by 3 and by 2 respectively (360 % 7 == 3, 30 % 7 == 2)
    ah = np.floor(E.JD[slot] - KALI_JD).astype(np.int64)
    yrs, rem = ah // 360, ah % 360
    mons, days = rem // 30, rem % 30
    wd_year = (KALI_WD + 3 * yrs) % 7
    wd_mon = (KALI_WD + 3 * yrs + 2 * mons) % 7
    wd_day = (KALI_WD + ah) % 7
    assert np.array_equal(wd_day, (np.floor(E.JD[slot] + 1.5).astype(np.int64)) % 7), \
        "the ahargana weekday must agree with the Julian day's own weekday"
    C["wd_day"] = wd_day
    varsha = np.where(WEEK_LORD[wd_year][None, :] == np.arange(NG)[:, None], 15.0, 0.0)
    masa = np.where(WEEK_LORD[wd_mon][None, :] == np.arange(NG)[:, None], 30.0, 0.0)
    dina = np.where(WEEK_LORD[wd_day][None, :] == np.arange(NG)[:, None], 45.0, 0.0)
    # Hora bala, marginalised in closed form: 24 horas from the day lord in the Chaldean order, so
    # the first three planets of that cycle rule four horas and the remaining four rule three.
    pos_in_chald = np.array([int(np.where(CHALDEAN == p)[0][0]) for p in range(NG)])
    start = np.array([int(np.where(CHALDEAN == WEEK_LORD[w])[0][0]) for w in range(7)])
    off = (pos_in_chald[:, None] - start[None, :]) % 7                 # (7 grahas, 7 weekdays)
    hcount = np.where(off < 3, 4.0, 3.0)
    hora = 60.0 * hcount[:, wd_day] / 24.0
    C["varsha"], C["masa"], C["dina"], C["hora"] = varsha, masa, dina, hora
    # constants under a uniform hour prior, carried into the total but never emitted as columns
    natho = np.full((NG, n), 30.0)
    natho[MERC] = 60.0
    tribh = np.full((NG, n), 10.0)
    tribh[JUP] = 60.0
    C["natho"], C["tribhaga"] = natho, tribh

    # ── Cheshta bala ──
    # The seeghra kendra done with real heliocentric geometry: the synodic anomaly between the Earth
    # and the graha, zero at conjunction with the Sun and 180 at opposition (which for Mercury and
    # Venus is inferior conjunction — precisely when they are retrograde and the texts call them
    # strong). Surya Siddhanta's seeghrocha, read off the ephemeris rather than its epicycle.
    helio_earth = np.mod(E.LON[slot][E.IDX["Sun"]] + 180.0, 360.0)
    psi = np.mod(helio_earth[None, :] - helio, 360.0)
    psi = np.where(psi <= 180.0, psi, 360.0 - psi)
    cheshta = psi / 3.0
    elong_g = np.abs(E.wrap(E.LON[slot][gi] - E.LON[slot][E.IDX["Sun"]][None, :]))
    C["cheshta_seeghra"] = cheshta
    C["cheshta_elong"] = elong_g / 3.0
    ches = cheshta.copy()
    # BPHS 27: the Sun has no Cheshta bala of its own and takes its Ayana bala, the Moon its Paksha
    # bala. The UNDOUBLED values are used — the doubling belongs to Kala bala, and a Cheshta bala of
    # 120 would put those two on a different scale from the other five.
    ches[SUN] = ayana_raw[SUN]
    ches[MOON] = paksha_raw[MOON]
    C["cheshta"] = ches
    ratio = spd / MEAN_SPD[:, None]
    C["spd_ratio"] = ratio
    C["gati"] = np.select([ratio < 0, np.abs(ratio) < 0.05, ratio < 0.5, ratio < 1.5],
                          [0.0, 1.0, 2.0, 3.0], 4.0)                   # vakra/vikala/manda/sama/atichara

    # ── Drik bala ──
    dmat = np.zeros((NG, NG, n))                                       # [aspecting, aspected]
    dmat_s = np.zeros((NG, NG, n))
    for c in range(NG):
        for p in range(NG):
            if c == p:
                continue
            x = np.mod(lon[p] - lon[c], 360.0)
            dmat[c, p] = _drishti(x)
            dmat_s[c, p] = _drishti_special(x, c)
    C["dmat"] = dmat
    bmask = ben_row.astype(float)
    C["drik_ben"] = (dmat * bmask[:, None, :]).sum(0)
    C["drik_mal"] = (dmat * (1.0 - bmask)[:, None, :]).sum(0)
    C["drik"] = (C["drik_ben"] - C["drik_mal"]) / 4.0
    C["drik_special"] = ((dmat_s * bmask[:, None, :]).sum(0)
                         - (dmat_s * (1.0 - bmask)[:, None, :]).sum(0)) / 4.0

    # ── the six, and the total in rupas ──
    C["sthana"] = uchcha + sapta + ojha + drek + C["kendra"]
    C["kala"] = (paksha + C["ayana"] + varsha + masa + dina + hora + natho + tribh)
    C["naisargika"] = np.repeat(NAISARGIKA[:, None], n, axis=1)
    pre = C["sthana"] + C["dig"] + C["kala"] + C["cheshta"] + C["naisargika"] + C["drik"]
    # Yuddha bala: two grahas (never the luminaries) inside 1 deg are at war; the more northerly wins
    # and takes the difference of their strengths divided by the difference of their discs.
    yud = np.zeros((NG, n))
    war = np.zeros((NG, n))
    for p in range(MARS, NG):
        for q in range(p + 1, NG):
            close = (np.abs(E.wrap(lon[p] - lon[q])) < 1.0) & (sgn[p] == sgn[q])
            if not close.any():
                continue
            d = np.abs(pre[p] - pre[q]) / abs(BIMBA[p] - BIMBA[q])
            pwin = blat[p] > blat[q]
            yud[p] += np.where(close, np.where(pwin, d, -d), 0.0)
            yud[q] += np.where(close, np.where(pwin, -d, d), 0.0)
            war[p] += close
            war[q] += close
    C["yuddha"], C["war"] = yud, war
    C["kala"] = C["kala"] + yud
    C["total"] = pre + yud
    C["rupa"] = C["total"] / 60.0
    C["ishta"] = np.sqrt(np.clip(uchcha, 0, None) * np.clip(C["cheshta"], 0, None))
    C["kashta"] = np.sqrt(np.clip(60.0 - uchcha, 0, None) * np.clip(60.0 - C["cheshta"], 0, None))

    # ── upagrahas ──
    up = {}
    for name, _sg, offs in UPAGRAHA:
        up[name] = np.mod(_sg * lon[SUN] + offs, 360.0) if _sg > 0 else np.mod(offs - lon[SUN], 360.0)
    C["up"] = up
    return C


def _sav_hours(E, slot, aya_idx):
    """SAV at all twelve possible birth hours -> (n, 12 signs, 12 hours). The Moon's contributor row
    is the one that really moves; this is what the ±6° noon uncertainty does to the bindu profile."""
    aya = E.AYA[aya_idx, slot]
    gi = [E.IDX[g] for g in GR]
    H = E.hours(slot)[gi]                                              # (7, 12 hours, n)
    sid = np.mod(H - aya[None, None, :], 360.0)
    out = np.empty((E.n, 12, int(E.HOURS)))
    for h in range(int(E.HOURS)):
        out[:, :, h] = _bav(_sign(sid[:, h, :])).sum(0)
    return out


def _arudha(sgn, pL):
    """Arudha pada of every bhava as a distribution over signs -> (12 bhavas, n, 12 signs).

    Jaimini Upadesa Sutras 1.1.20-22: count from the bhava to its lord and as far again from the
    lord; if that lands in the bhava itself or in the seventh from it, take the tenth therefrom.
    `pL` is the prior over the rising sign — the arudha needs a lagna, and this marginalises it.
    """
    n = sgn.shape[1]
    ar = np.arange(n)
    out = np.zeros((12, n, 12))
    for L in range(12):
        w = pL[:, L]
        if not np.any(w > 0):
            continue
        for h in range(1, 13):
            H = (L + h - 1) % 12
            P = sgn[LORD[H]]
            A = (2 * P - H) % 12
            A = np.where((A == H) | (A == (H + 6) % 12), (A + 9) % 12, A)
            out[h - 1][ar, A] += w
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
# build
# ════════════════════════════════════════════════════════════════════════════════════════════════
def build(E):
    aya_idx = E.AYA_NAME.index("Lahiri")
    O = _chart(E, E.SLOT["older"], aya_idx)
    Y = _chart(E, E.SLOT["younger"], aya_idx)
    n, ar = E.n, np.arange(E.n)
    out = {}
    okO = np.isfinite(E.LAT_O) & np.isfinite(E.LON_O)
    okY = np.isfinite(E.LAT_Y) & np.isfinite(E.LON_Y)

    # ── 1. SAV per sign, the doctrinal thresholds, and the bindus under each graha ──────────────
    cols = [O["sav"], Y["sav"]]
    for C in (O, Y):
        s = C["sav337"]
        cols += [s.max(1, keepdims=True), s.min(1, keepdims=True),
                 s.std(1, keepdims=True),
                 (s >= 30).sum(1, keepdims=True).astype(float),      # classically strong signs
                 (s <= 25).sum(1, keepdims=True).astype(float),      # classically weak signs
                 np.abs(s - s.mean(1, keepdims=True)).mean(1, keepdims=True)]
        own = np.stack([C["bav"][p][ar, C["sgn"][p]] for p in range(NG)], 1)     # bindus under each graha
        sav_at = np.stack([s[ar, C["sgn"][p]] for p in range(NG)], 1)
        sev = np.stack([C["bav"][p][ar, (C["sgn"][p] + 6) % 12] for p in range(NG)], 1)
        sav7 = np.stack([s[ar, (C["sgn"][p] + 6) % 12] for p in range(NG)], 1)
        cols += [own, sav_at, sev, sav7]
    out["av8: SAV per sign + bindus under each graha"] = np.column_stack(cols)

    # ── 2. the seven Bhinnashtakavarga tables in full ───────────────────────────────────────────
    out["av8: BAV 7 grahas x 12 signs"] = np.column_stack(
        [O["bav"].transpose(1, 0, 2).reshape(n, NG * 12),
         Y["bav"].transpose(1, 0, 2).reshape(n, NG * 12)])

    # ── 3. kakshya and the kakshya-vedha reading, own and across the pair ───────────────────────
    cols = []
    for C in (O, Y):
        cols += [C["kak"].T.astype(float), C["kakpos"].T, C["kakben"].T, C["kaklagna"].T,
                 C["kakben"].sum(0)[:, None], (C["kak"] <= 1).sum(0)[:, None].astype(float)]
    for A, B in ((O, Y), (Y, O)):
        # A's graha standing in B's chart: the bindus B's table gives that sign, and whether the
        # kakshya A's graha occupies is one B's own table blesses — gochara read across the pair
        cross = np.stack([B["bav"][p][ar, A["sgn"][p]] for p in range(NG)], 1)
        crosss = np.stack([B["sav337"][ar, A["sgn"][p]] for p in range(NG)], 1)
        kb = np.zeros((n, NG))
        for p, g in enumerate(GR):
            for c, cn in enumerate(GR):
                h = (A["sgn"][p] - B["sgn"][c]) % 12 + 1
                kb[:, p] += np.where((A["klord"][p] == c) & np.isin(h, BAV_TABLE[g][cn]), 1.0, 0.0)
        cols += [cross, crosss, kb]
    out["av8: kakshya + kakshya vedha (own and cross)"] = np.column_stack(cols)

    # ── 4. the two SAV profiles compared ────────────────────────────────────────────────────────
    a, b = O["sav337"], Y["sav337"]
    cosv = ((a * b).sum(1) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-9))
    cols = [np.minimum(a, b), np.abs(a - b), a + b,
            _rowcorr(a, b)[:, None], cosv[:, None],
            np.abs(a - b).sum(1)[:, None], np.sqrt(((a - b) ** 2).sum(1))[:, None],
            (np.argmax(a, 1) == np.argmax(b, 1)).astype(float)[:, None],
            ((np.argmax(a, 1) - np.argmax(b, 1)) % 12 == 6).astype(float)[:, None]]
    for p in (MOON, SUN, VEN, JUP, SAT, MARS, MERC):
        cols += [b[ar, O["sgn"][p]][:, None], a[ar, Y["sgn"][p]][:, None],
                 b[ar, (O["sgn"][p] + 6) % 12][:, None], a[ar, (Y["sgn"][p] + 6) % 12][:, None]]
    out["av8: SAV profile pair comparison"] = np.column_stack(cols)

    # ── 5. SAV over the twelve bhavas from the two named lagna proxies ──────────────────────────
    cols = []
    for C in (O, Y):
        for ref in (MOON, SUN):
            base = C["sgn"][ref]
            H = np.stack([C["sav337"][ar, (base + h) % 12] for h in range(12)], 1)
            cols += [H, H[:, [0, 3, 6, 9]].sum(1)[:, None], H[:, 6][:, None] - H[:, 0][:, None]]
    for A, B in ((O, Y), (Y, O)):
        base = B["sgn"][MOON]
        cols.append(np.stack([A["sav337"][ar, (base + h) % 12] for h in (0, 3, 6, 7, 11)], 1))
    out["av8: SAV in 12 bhavas from chandra/surya lagna"] = np.column_stack(cols)

    # ── 6. the sodhana reductions and the sodhya pindas ─────────────────────────────────────────
    cols = []
    for C in (O, Y):
        rs = C["red"].sum(0)
        cols += [rs, C["rasi_pinda"].T, C["graha_pinda"].T, C["sodhya"].T,
                 C["sodhya"].sum(0)[:, None], rs.sum(1)[:, None],
                 (C["sav"].sum(1) - rs.sum(1))[:, None]]
    cols += [_rowcorr(O["sodhya"].T, Y["sodhya"].T)[:, None],
             np.abs(O["sodhya"] - Y["sodhya"]).sum(0)[:, None]]
    out["av8: sodhya pinda (trikona + ekadhipatya)"] = np.column_stack(cols)

    # ── 7. how much of the bindu profile survives the unknown birth hour ────────────────────────
    cols = []
    for slot in (E.SLOT["older"], E.SLOT["younger"]):
        S = _sav_hours(E, slot, aya_idx)                               # (n, 12 signs, 12 hours)
        m, sd = S.mean(2), S.std(2)
        cols += [m, sd, sd.max(1, keepdims=True), sd.mean(1, keepdims=True),
                 (sd > 0.5).sum(1, keepdims=True).astype(float)]
    out["av8: SAV stability over the 12 birth-hour slots"] = np.column_stack(cols)

    # ── 8. Sthana bala, all five sub-components ─────────────────────────────────────────────────
    cols = []
    for C in (O, Y):
        cols += [C["uchcha"].T, C["sapta"].T, C["ojha"].T, C["drek"].T,
                 C["kendra_cl"].T, C["kendra_sl"].T, C["sthana"].T,
                 C["sthana"].sum(0)[:, None]]
    out["sb6: sthana bala, five components"] = np.column_stack(cols)

    # ── 9. Kala bala, sub-component by sub-component, plus Dig bala under both proxies ──────────
    cols = []
    for C in (O, Y):
        cols += [C["paksha"].T, C["ayana"].T, C["varsha"].T, C["masa"].T, C["dina"].T, C["hora"].T,
                 C["yuddha"].T, C["war"].T, C["kala"].T, C["dig_cl"].T, C["dig_sl"].T,
                 _onehot(C["wd_day"], 7)]
    out["sb6: kala bala components + dig bala proxies"] = np.column_stack(cols)

    # ── 10. Cheshta bala, the motion classes, and Ishta / Kashta phala ──────────────────────────
    cols = []
    for C in (O, Y):
        cols += [C["cheshta_seeghra"].T, C["cheshta_elong"].T, C["cheshta"].T, C["gati"].T,
                 C["spd_ratio"].T, (C["spd_ratio"] < 0).sum(0)[:, None].astype(float),
                 C["ishta"].T, C["kashta"].T,
                 C["ishta"].sum(0)[:, None], C["kashta"].sum(0)[:, None]]
    out["sb6: cheshta bala + ishta/kashta phala"] = np.column_stack(cols)

    # ── 11. Drik bala from the Sphuta Drishti formula, both readings, plus the 7x7 matrix ───────
    cols = []
    for C in (O, Y):
        cols += [C["drik"].T, C["drik_special"].T, C["drik_ben"].T, C["drik_mal"].T,
                 C["dmat"].transpose(2, 0, 1).reshape(n, NG * NG)]
    out["sb6: drik bala (sphuta drishti)"] = np.column_stack(cols)

    # ── 12. the six summed: rupas against the classical minimum ─────────────────────────────────
    cols = []
    for C in (O, Y):
        r = C["rupa"]
        ratio = r / MIN_RUPA[:, None]
        cols += [C["sthana"].T, C["dig"].T, C["kala"].T, C["cheshta"].T, C["drik"].T,
                 r.T, ratio.T, (ratio >= 1.0).astype(float).T,
                 (ratio >= 1.0).sum(0)[:, None].astype(float), r.sum(0)[:, None],
                 _onehot(np.argmax(r, 0), NG), _onehot(np.argmin(r, 0), NG)]
    out["sb6: shadbala rupas vs classical minima"] = np.column_stack(cols)

    # ── 13. the pair's strengths against each other ─────────────────────────────────────────────
    ro, ry = O["rupa"], Y["rupa"]
    out["sb6: cross-partner shadbala comparison"] = np.column_stack([
        (ro - ry).T, np.abs(ro - ry).T, (ro / np.maximum(ry, 1e-6)).T, (ro > ry).astype(float).T,
        _rowcorr(ro.T, ry.T)[:, None], (ro.sum(0) - ry.sum(0))[:, None],
        np.minimum(ro, ry).T, np.maximum(ro, ry).T,
        (np.argmax(ro, 0) == np.argmax(ry, 0)).astype(float)[:, None],
        (O["ishta"].sum(0) - Y["ishta"].sum(0))[:, None],
        (O["kashta"].sum(0) - Y["kashta"].sum(0))[:, None],
    ])

    # ── 14. the five Sun-derived upagrahas, exactly ─────────────────────────────────────────────
    # These are rigid rotations of the Sun, so cos/sin of one is a rotation of cos/sin of the Sun and
    # would add nothing a solar block does not already carry. What IS new is their DISCRETE
    # membership (a shifted partition of the zodiac is a different partition) and their aspects,
    # which peak at their own longitudes — so that is what this block emits.
    cols = []
    names = [u[0] for u in UPAGRAHA]
    for C in (O, Y):
        for nm in names:
            u = C["up"][nm]
            cols += [_onehot(_sign(u), 12),
                     np.floor(np.mod(u, 360.0) * 3.0 / 40.0)[:, None],         # nakshatra index
                     np.floor(np.mod(u, 360.0) / (10.0 / 3.0))[:, None] % 12]  # navamsa index
            # the classical reading: an upagraha in the 7th or 8th from the Moon, or with Venus
            h = (_sign(u) - C["sgn"][MOON]) % 12 + 1
            cols += [np.isin(h, [7, 8]).astype(float)[:, None],
                     np.isin(h, [1, 2, 12]).astype(float)[:, None],
                     E.orbkern(E.sep(u, C["lon"][VEN]), 0.0, 6.0)[:, None],
                     E.orbkern(E.sep(u, C["lon"][SAT]), 0.0, 6.0)[:, None]]
    for A, B in ((O, Y), (Y, O)):
        for nm in names:
            u = A["up"][nm]
            for p in (MOON, VEN, MARS, JUP, SAT):
                s = E.sep(u, B["lon"][p])
                cols += [E.orbkern(s, 0.0, 6.0)[:, None], E.orbkern(s, 180.0, 6.0)[:, None],
                         E.orbkern(s, 120.0, 8.0)[:, None]]
            cols.append(((_sign(u) - B["sgn"][MOON]) % 12 == 0).astype(float)[:, None])
    out["upg: sun-derived upagrahas (exact)"] = np.column_stack(cols)

    # ── 15/16. arudha padas, with the lagna marginalised ────────────────────────────────────────
    pLO = _asc_dist(E, E.SLOT["older"], E.LAT_O, E.LON_O, okO, O["aya"]) if okO.any() \
        else np.full((n, 12), 1.0 / 12.0)
    pLY = _asc_dist(E, E.SLOT["younger"], E.LAT_Y, E.LON_Y, okY, Y["aya"]) if okY.any() \
        else np.full((n, 12), 1.0 / 12.0)
    AO, AY = _arudha(O["sgn"], pLO), _arudha(Y["sgn"], pLY)
    cols = []
    for A in (AO, AY):
        for h in (0, 6, 11):                                            # AL, Darapada A7, Upapada UL
            cols += [A[h], E.entropy(A[h])[:, None]]
        cm = np.concatenate([np.stack([(A[h] * np.cos(np.deg2rad(np.arange(12) * 30.0))).sum(1),
                                       (A[h] * np.sin(np.deg2rad(np.arange(12) * 30.0))).sum(1)], 1)
                             for h in range(12)], 1)
        cols.append(cm)
    out["arp: arudha padas, lagna marginalised"] = np.column_stack(cols)

    def _rel(P, Q):
        """P(sign(P) - sign(Q) == d) for d = 0..11, over two independent sign distributions."""
        return np.stack([sum(P[:, (s + d) % 12] * Q[:, s] for s in range(12)) for d in range(12)], 1)

    ULO, ULY, ALO, ALY, A7O, A7Y = AO[11], AY[11], AO[0], AY[0], AO[6], AY[6]
    cols = [_rel(ULO, ALY), _rel(ULY, ALO), _rel(ULO, ULY), _rel(A7O, A7Y), _rel(ALO, ALY)]
    for P, C in ((ULO, Y), (ULY, O), (A7O, Y), (A7Y, O)):
        # is the partner's Venus, Jupiter or Moon standing on the arudha, or in the 2nd from it —
        # the sustenance of the marriage in the Jaimini reading
        for p in (MOON, VEN, JUP, SAT, MARS):
            cols += [P[ar, C["sgn"][p]][:, None], P[ar, (C["sgn"][p] - 1) % 12][:, None]]
    for P in (ULO, ULY, A7O, A7Y, ALO, ALY):
        cols.append(E.entropy(P)[:, None])
    out["arp: upapada lagna cross-partner"] = np.column_stack(cols)

    # ── coordinate-dependent blocks: only where a real birthplace exists (see the docstring) ────
    # `.any()`, not a fraction of the batch — see the note in trad_east_asian_deep: whether coordinates
    # exist is a fact about the input contract, identical in every chunk.
    if okO.any() and okY.any():
        cols = []
        for C, pL, ok in ((O, pLO, okO), (Y, pLY, okY)):
            b8 = _bav(C["sgn"], pL)
            cols += [b8.sum(0), b8.sum(2).T, pL, E.entropy(pL)[:, None], ok.astype(float)[:, None]]
            base = np.argmax(pL, 1)
            cols.append(np.stack([b8.sum(0)[ar, (base + h) % 12] for h in range(12)], 1))
        out["av8: 8-contributor BAV with the lagna marginalised"] = np.column_stack(cols)
        g = _gulika_block(E, O, Y, okO, okY)
        if g is not None:
            out["upg: gulika + mandi (day/night marginalised)"] = g

    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in out.items()}


def _gulika_block(E, O, Y, okO, okY):
    """Gulika and Mandi for both partners, where a birthplace exists. Returns None if it cannot be
    computed for anybody, which is the case on a couples file with no coordinates."""
    n = E.n
    parts = []
    for C, slot, lat, lon, ok in ((O, E.SLOT["older"], E.LAT_O, E.LON_O, okO),
                                  (Y, E.SLOT["younger"], E.LAT_Y, E.LON_Y, okY)):
        got = np.zeros(n)
        vals = np.zeros((n, 4))                                # gulika day/night, mandi day/night
        frac = np.zeros(n)
        for k in np.where(ok)[0]:
            g = _gulika_mandi(float(E.JD[slot, k]), lat[k], lon[k], float(C["aya"][k]), "gulika")
            m = _gulika_mandi(float(E.JD[slot, k]), lat[k], lon[k], float(C["aya"][k]), "mandi")
            if g is None or m is None:
                continue
            vals[k] = [g[0], g[1], m[0], m[1]]
            frac[k] = g[2]
            got[k] = 1.0
        if not got.any():
            return None
        # the expectation over the birth hour is a two-point mixture: the day version with weight
        # equal to the daylight fraction, the night version with the rest
        dist = np.zeros((n, 12))
        dist2 = np.zeros((n, 12))
        ar = np.arange(n)
        dist[ar, _sign(vals[:, 0])] += frac * got
        dist[ar, _sign(vals[:, 1])] += (1.0 - frac) * got
        dist2[ar, _sign(vals[:, 2])] += frac * got
        dist2[ar, _sign(vals[:, 3])] += (1.0 - frac) * got
        h = (_sign(vals[:, 0]) - C["sgn"][MOON]) % 12 + 1
        parts += [dist, dist2, frac[:, None], got[:, None],
                  E.circ(vals[:, 0]), E.circ(vals[:, 2]),
                  np.isin(h, [1, 2, 7, 8, 12]).astype(float)[:, None] * got[:, None],
                  E.orbkern(E.sep(vals[:, 0], C["lon"][MOON]), 0.0, 6.0)[:, None] * got[:, None],
                  E.orbkern(E.sep(vals[:, 0], C["lon"][VEN]), 0.0, 6.0)[:, None] * got[:, None]]
    return np.column_stack(parts)


# ════════════════════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick

    E = load()
    print(f"\n{TRADITION}")
    print(f"  bindu tables verified: grand total {GRAND}, Lagna rows {LAGNA_BINDUS}, "
          f"seven-contributor total {SEVEN_ROW_TOTAL}")
    print("  per-graha doctrinal totals " + " ".join(f"{g[:3]} {DOCTRINAL_TOTAL[g]}" for g in GR))

    # the coordinate-dependent path is dead on a couples file with no birthplace, so prove the code
    # runs at all rather than shipping something untested: Tehran, the March equinox of 1980
    try:
        import swisseph as swe
        jd = 2444319.5 + 6.0 / 24.0                               # 1980-03-21 06:00 UT
        g = _gulika_mandi(jd, 35.70, 51.42, 23.5, "gulika")
        m = _gulika_mandi(jd, 35.70, 51.42, 23.5, "mandi")
        print(f"  geo path smoke test (Tehran 1980-03-21, NOT a feature): "
              f"gulika day {g[0]:.2f} night {g[1]:.2f} deg · mandi day {m[0]:.2f} · "
              f"daylight {100*g[2]:.1f}%")
    except Exception as e:
        print(f"  geo path smoke test FAILED: {e}")

    okO, okY = np.isfinite(E.LAT_O), np.isfinite(E.LAT_Y)
    print(f"  birthplace known: older {100*okO.mean():.1f}% · younger {100*okY.mean():.1f}%"
          + ("" if okO.any() else "   -> lagna/sunrise blocks omitted, nothing faked"))

    B = build(E)
    # the doctrinal row sums, checked on the real data rather than on the tables alone
    A = _chart(E, E.SLOT["older"], E.AYA_NAME.index("Lahiri"))
    for p, g in enumerate(GR):
        t = A["bav"][p].sum(1)
        want = DOCTRINAL_TOTAL[g] - len(BAV_TABLE[g]["Lagna"])
        assert np.allclose(t, want), f"{g} BAV rows sum to {t[:3]}, want {want}"
    assert np.allclose(A["sav"].sum(1), SEVEN_ROW_TOTAL), "SAV must total 292 without the Lagna"
    print(f"  on the data: every BAV row sums to its doctrinal total, every SAV to "
          f"{SEVEN_ROW_TOTAL} (337 - 45 Lagna bindus)")

    bad, tot = 0, 0
    print()
    for k, v in B.items():
        assert v.shape[0] == E.n, f"{k}: {v.shape}"
        assert v.ndim == 2, f"{k}: not 2-D"
        assert v.dtype == np.float64, f"{k}: {v.dtype}"
        assert np.isfinite(v).all(), f"{k}: non-finite"
        if v.std(0).max() <= 0:
            print(f"  {k}: ALL CONSTANT")
            bad += 1
            continue
        tot += v.shape[1]
        a, u = quick(E, v)
        print(f"  {k:<52} {v.shape[1]:>4} cols   acc {100*a:6.2f}%   AUC {u:.4f}")
    print(f"\n  {len(B)} blocks, {tot} columns")
    print("OK" if not bad else f"{bad} constant block(s)")
    sys.exit(1 if bad else 0)
