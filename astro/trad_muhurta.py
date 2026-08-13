"""
trad_muhurta.py — Vivaha Muhurta: the classical Hindu ELECTION OF THE WEDDING DATE.

WHAT THIS MODULE IS FOR, AND HOW IT DIFFERS FROM ITS SIBLINGS
-------------------------------------------------------------
Its sibling Vedic modules read the two BIRTH charts and match them (Ashtakoota, poruthams, doshas,
vargas, Vimshottari). This module reads the WEDDING DAY ITSELF. In Jyotisha that is a separate and
much older discipline — Muhurta / Kala Vidhana — with its own literature, its own checklist and its
own vocabulary, and it asks a different question: not "do these two agree?" but "is this DAY fit for
a marriage to begin on, for these two people?"

The checklist below is the Vivaha Prakarana (marriage chapter) of the muhurta texts, taken rule by
rule and computed exactly as written wherever the data allows. Authorities, cited again at each
table that implements them:

  * Muhurta Chintamani of Ram Daivajna (1600), Vivaha Prakarana — the permitted nakshatras, the
    permitted and forbidden lunar months, the tithi and vara rules, Guru/Shukra asta.
  * Kalaprakasika (N. P. Subramania Iyer's translation) — the Panchaka arithmetic, the sevenfold
    nakshatra activity classes, the nine inauspicious nitya yogas, Vishti/Bhadra karana.
  * B. V. Raman, *Muhurtha* (ch. "Marriage") — the standard modern English digest of the same rules:
    the eleven vivaha nakshatras, the favoured tithis 2/3/5/7/10/11/13, the favoured varas Mon/Wed/
    Thu/Fri, Tara Bala, Chandra Bala, gochara (transit) fitness from the janma rasi.
  * Dharma Sindhu / Nirnaya Sindhu — Chaturmasya, Malamasa (adhika masa) and the Dhanu/Meena
    "Kharmas" solar months, in which no marriage is performed.
  * Brihat Parashara Hora Shastra — combustion (asta) limits, exaltation/debilitation degrees,
    moolatrikona ranges, and graha drishti (the 7th for all, plus 4/8 Mars, 5/9 Jupiter, 3/10 Saturn).
  * Yogini Dasha as given in Deva Keralam / Sanketa Nidhi and in the standard panchanga digests:
    Mangala 1, Pingala 2, Dhanya 3, Bhramari 4, Bhadrika 5, Ulka 6, Siddha 7, Sankata 8 = 36 years,
    started from (janma nakshatra number + 3) mod 8.

APPLYING VERSUS SEPARATING — the electional distinction, and why E.SPD carries it
--------------------------------------------------------------------------------
Muhurta is not a chart reading, it is a reading of a MOMENT IN MOTION. The texts never treat "Venus
6 degrees from the Sun" as one condition: a Venus falling INTO the Sun's rays (asta, heliacal
setting) and a Venus climbing OUT of them (udaya, heliacal rising) are opposite omens, and the
whole reason a marriage waits is that the second is coming. The same holds for an afflicting
malefic — an applying Mars is the affliction; a separating Mars is a memory of one. Every contact
in the "elec:" blocks is therefore signed by its rate of closure, computed from E.SPD:

    d|delta|/dt = sign(delta) * (speed_A - speed_B),  applying to `angle` iff that carries
    |delta| toward `angle`, i.e. approach = -sign(|delta| - angle) * d|delta|/dt  > 0.

The same speeds give the electionally decisive quantity the texts state as ghatis: HOW LONG the
present nakshatra, tithi, karana and yoga still have to run. A muhurta is only usable if its
panchanga limbs survive the ceremony.

PROXIES FORCED BY THE DATA — stated plainly, as the contract requires
--------------------------------------------------------------------
  1. NO WEDDING TIME, THEREFORE NO ELECTION IN THE STRICT SENSE. Muhurta proper elects a MOMENT: a
     lagna, a navamsa of the lagna, a planetary hour (hora), a ghati within the tithi, the Abhijit
     or Vish/Amrita ghatis, Lagna shuddhi (the 8th from the rising sign free). None of that is
     computable here, because the dataset gives the wedding DATE only and every position in this
     module is taken at 12:00 UT. Everything below is therefore a NOON PROXY for the day's fitness:
     the day-level limbs (nakshatra, tithi, vara, yoga, karana, masa, the graha condition) are what
     the tradition itself calls the "dina shuddhi" — day purity — and they are the part of the
     doctrine that survives without a time.
  2. NO LAGNA. Where a rule needs the rising sign, this module uses one of two NAMED proxies and
     says which: SURYA-LAGNA (the Sun's sidereal sign as the 1st, the contract's "solar whole-sign"
     proxy — defensible at noon, when the Sun is near the meridian, but it is a proxy and not the
     Ascendant) and CHANDRA-LAGNA (the Moon's sign as the 1st, itself a documented alternative
     reference point in the same texts). The Panchaka remainder, which needs the lagna number, is
     emitted under BOTH proxies and with the full 9-way remainder one-hot, so nothing rests on
     either choice being right. Jamitra and Bhrigu-shatka are likewise proxy-based.
  3. THE MOON IS UNCERTAIN BY ROUGHLY +-6 DEGREES at the two BIRTHS — nearly half a nakshatra. Tara
     Bala and Chandra Bala are counted FROM the janma nakshatra and janma rasi, so both inherit that
     error and are about half-reliable per couple. The wedding Moon is NOT affected in the same way:
     it too is a noon value, but the quantity that matters for the wedding is the day's nakshatra,
     and a noon Moon names the right nakshatra for most of any given day. The features are built
     anyway, because muhurta IS a lunar doctrine, but no precision should be read into the
     natal-side counts.
  4. THE EXACT TITHI AT THE CEREMONY is unknown for the same reason; the tithi here is the noon
     tithi, and the "hours remaining" features in the elec: block say how far it was from turning.
  5. VARA is taken from the Julian day at noon UT. The Hindu day runs sunrise to sunrise, so for a
     ceremony in the pre-dawn hours the traditional vara would be the previous one.
  6. THE PREVIOUS NEW MOON, needed to name the lunar month (masa) and to detect an intercalary
     Malamasa, is not in the dataset. It is estimated by back-extrapolating the Sun along the
     elongation at the mean synodic rate (12.1907 deg/day), then refined with the instantaneous
     relative speed; both estimates are emitted. The error is under a day and a half, i.e. under
     1.5 degrees of solar longitude, which only matters within that much of a sign boundary.
  7. SEX IS UNKNOWN, so every asymmetric rule (Tara Bala and Chandra Bala are computed per person,
     not per role) is emitted for OLDER and for YOUNGER separately and jointly, never as "bride"
     and "groom".
  8. SECONDARY PROGRESSION AND THE DAVISON CHART ARE NOT JYOTISHA. Slots 3, 4 and 5 are used in one
     clearly-named block as two further "charts of the couple advanced to the wedding" against which
     the same muhurta arithmetic is run. That is an adaptation to the data, not a traditional rule,
     and it is labelled as such.

NOT IMPLEMENTED, AND WHY
------------------------
  * Lagna shuddhi, the navamsa of the lagna, Lagna's Ashtakavarga bindus, the 8th-house test, the
    Udaya lagna's nakshatra — all need the rising sign.
  * The planetary hour (hora) lord, Abhijit muhurta, the Vish (poison), Amrita and Varjyam ghatis,
    Rahu Kalam, Yamaghanta, Gulika Kalam, Dur Muhurtam — all need the time of day and the local
    sunrise. A noon proxy for any of them would be a fabrication, not an approximation, because
    every one of them is defined as a FRACTION of the day between sunrise and sunset, so at noon
    each is simply "the middle one" for every couple in the dataset and would be a constant.
  * Kshaya masa (the rare lost month) — needs two consecutive solar ingresses inside one lunation,
    which the noon back-extrapolation cannot resolve safely.
  * Ashtakoota, the Tamil poruthams and Kuja dosha — these are BIRTH-chart matching, not the
    election of the day, and they already exist in trad_vedic_core.py and trad_vedic_match.py. They
    are deliberately not duplicated here. The only nakshatra-pair arithmetic in this module is
    between the WEDDING nakshatra and each natal nakshatra, which is the muhurta question.
"""

import numpy as np

TRADITION = "Vedic Vivaha Muhurta — election of the wedding date (Muhurta Chintamani, Kalaprakasika, B. V. Raman)"

YR = 365.2425
NAK = 360.0 / 27.0            # 13 deg 20'
PADA = 360.0 / 108.0          # 3 deg 20'
SYN = 29.530588853            # mean synodic month, days
SYN_RATE = 360.0 / SYN        # 12.1907 deg/day, the mean rate of elongation gain

# ── the nine grahas, in this module's own order ─────────────────────────────────────────────────
GN = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"]
SU, MO, ME, VE, MA, JU, SA, RA, KE = range(9)
SEVEN = [SU, MO, ME, VE, MA, JU, SA]
MALEFIC = [SU, MA, SA, RA, KE]
BENEFIC = [MO, ME, VE, JU]

# ── the 27 nakshatras, 0-indexed (0 = Ashwini) ──────────────────────────────────────────────────
NAK_NAME = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
            "Pushya", "Ashlesha", "Magha", "P.Phalguni", "U.Phalguni", "Hasta", "Chitra", "Swati",
            "Vishakha", "Anuradha", "Jyeshtha", "Moola", "P.Ashadha", "U.Ashadha", "Shravana",
            "Dhanishta", "Shatabhisha", "P.Bhadra", "U.Bhadra", "Revati"]

# Muhurta Chintamani / Raman, *Muhurtha*, ch. "Marriage": the eleven nakshatras permitted for vivaha
# — Rohini, Mrigashira, Magha, Uttara Phalguni, Hasta, Swati, Anuradha, Moola, Uttara Ashadha,
# Uttara Bhadrapada, Revati.
VIVAHA_NAK = [3, 4, 9, 11, 12, 14, 16, 18, 20, 25, 26]
# Kalaprakasika and several regional panchangams admit a wider "madhyama" set as well; the extra
# five most often listed are Bharani, Punarvasu, Chitra, Shravana and Dhanishta.
VIVAHA_NAK_WIDE = sorted(VIVAHA_NAK + [1, 6, 13, 21, 22])
# Pushya is the famous exception: excellent for everything EXCEPT marriage (Kalaprakasika).
PUSHYA = 7

# Kalaprakasika, the sevenfold activity classes of the nakshatras. Dhruva (fixed) and Mridu
# (tender) are the two classes the texts recommend for marriage, and eight of the eleven permitted
# nakshatras fall in them.
NAK_CLASS = np.zeros(27, dtype=int)
_CLASSES = {
    0: [3, 11, 20, 25],                    # Dhruva / Sthira  — fixed
    1: [4, 13, 16, 26],                    # Mridu / Maitra   — tender
    2: [0, 7, 12],                         # Kshipra / Laghu  — swift
    3: [6, 14, 21, 22, 23],                # Chara / Chala    — movable
    4: [1, 9, 10, 19, 24],                 # Ugra / Krura     — fierce
    5: [2, 15],                            # Mishra / Sadharana — mixed
    6: [5, 8, 17, 18],                     # Tikshna / Daruna — sharp
}
for _c, _ns in _CLASSES.items():
    for _n in _ns:
        NAK_CLASS[_n] = _c
NAK_CLASS_NAME = ["Dhruva", "Mridu", "Kshipra", "Chara", "Ugra", "Mishra", "Tikshna"]

# Vimshottari lords of the nakshatras, repeating in nines (BPHS).
NAK_LORD = np.array([KE, VE, SU, MO, MA, RA, JU, SA, ME] * 3)

# The North-Indian "Panchak": the Moon in the last five nakshatras, Dhanishta to Revati.
PANCHAK_NAK = [22, 23, 24, 25, 26]

# Nakshatra gandanta — the three junctions where a water sign ends and a fire sign begins, which are
# also nakshatra junctions: Revati/Ashwini (0 deg Aries), Ashlesha/Magha (0 deg Leo),
# Jyeshtha/Moola (0 deg Sagittarius). Abhukta Mula is the last pada of Jyeshtha plus the first of
# Moola. Marriage at a gandanta Moon is among the strongest lunar prohibitions.
GANDANTA_DEG = [0.0, 120.0, 240.0]

# ── tithi, vara, yoga, karana names ─────────────────────────────────────────────────────────────
# Raman, *Muhurtha*: the tithis auspicious for marriage are the 2nd, 3rd, 5th, 7th, 10th, 11th and
# 13th of either paksha. The Rikta tithis (4, 9, 14) are forbidden for every auspicious act, and so
# are Amavasya (the 30th) and, for marriage, the 1st, 6th, 8th and 12th.
TITHI_FAV = [2, 3, 5, 7, 10, 11, 13]
TITHI_RIKTA = [4, 9, 14]
TITHI_CLASS_NAME = ["Nanda", "Bhadra", "Jaya", "Rikta", "Purna"]

VARA_NAME = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
VARA_LORD = np.array([SU, MO, MA, ME, JU, VE, SA])
VARA_FAV = [1, 3, 4, 5]                    # Monday, Wednesday, Thursday, Friday
VARA_BAD = [2, 6]                          # Tuesday (Mars), Saturday (Saturn)

# The nine inauspicious nitya yogas (Kalaprakasika): Vishkambha, Atiganda, Shula, Ganda, Vyaghata,
# Vajra, Vyatipata, Parigha, Vaidhriti. Vyatipata and Vaidhriti are the two treated as fatal.
YOGA_BAD = [0, 5, 8, 9, 12, 14, 16, 18, 26]
YOGA_FATAL = [16, 26]

# Karana: 60 half-tithis. The seven movable karanas repeat eight times over half-tithis 1..56;
# Kimstughna occupies the first, and Shakuni, Chatushpada and Naga the last three. Vishti (Bhadra)
# is the seventh movable and is forbidden for every auspicious act, marriage above all.
KARANA_NAME = ["Kimstughna", "Bava", "Balava", "Kaulava", "Taitila", "Garija", "Vanija", "Vishti",
               "Shakuni", "Chatushpada", "Naga"]
VISHTI = 7
KARANA_FIXED = [0, 8, 9, 10]

# ── the twelve lunar months (amanta), 0 = Chaitra ───────────────────────────────────────────────
MASA_NAME = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada", "Ashwin",
             "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna"]
# Muhurta Chintamani, Vivaha Prakarana: Magha, Phalguna, Vaishakha and Jyeshtha are the best months
# for marriage; Margashirsha and Kartika (after Devuthani Ekadashi) are middling; Chaitra and Pausha
# are prohibited, and the four Chaturmasya months are closed.
MASA_BEST = [10, 11, 1, 2]
MASA_OK = [8, 7]
MASA_FORBID = [0, 9, 3, 4, 5, 6]

# Dharma Sindhu: the two solar months in which no marriage is performed — the Sun in sidereal Dhanu
# (Sagittarius, "Dhanurmasa"/Kharmas) and in Meena (Pisces, "Meenamasa").
KHARMAS_SIGN = [8, 11]

# ── the eight Yoginis: name, years, lord ────────────────────────────────────────────────────────
YOGINI_NAME = ["Mangala", "Pingala", "Dhanya", "Bhramari", "Bhadrika", "Ulka", "Siddha", "Sankata"]
YOGINI_YR = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])          # 36 years in all
YOGINI_LORD = np.array([MO, SU, JU, MA, ME, SA, VE, RA])
YOGINI_CUM = np.concatenate([[0.0], np.cumsum(YOGINI_YR)])              # [0,1,3,6,10,15,21,28,36]
YOGINI_TOTAL = 36.0
# Mangala, Dhanya, Bhadrika and Siddha are the benefic Yoginis; Pingala, Bhramari, Ulka and Sankata
# are the malefic ones.
YOGINI_GOOD = [0, 2, 4, 6]

# ── Tara Bala: the ninefold count (Raman, *Muhurtha*) ───────────────────────────────────────────
TARA_NAME = ["Janma", "Sampat", "Vipat", "Kshema", "Pratyari", "Sadhaka", "Vadha", "Mitra",
             "Ati-Mitra"]
TARA_GOOD = [2, 4, 6, 8, 9]               # 1-indexed: Sampat, Kshema, Sadhaka, Mitra, Ati-Mitra
TARA_BAD = [1, 3, 5, 7]                   # Janma, Vipat, Pratyari, Vadha

# ── Chandra Bala: the wedding Moon's whole-sign house from the janma rasi ───────────────────────
CB_GOOD = [1, 3, 6, 7, 10, 11]
CB_BAD = [4, 8, 12]
CB_MID = [2, 5, 9]

# ── gochara (transit) fitness from the janma rasi, Raman, *Muhurtha* / *Hindu Predictive Astrology*
GOCHARA_GOOD = {SU: [3, 6, 10, 11], MO: [1, 3, 6, 7, 10, 11], ME: [2, 4, 6, 8, 10, 11],
                VE: [1, 2, 3, 4, 5, 8, 9, 11, 12], MA: [3, 6, 11], JU: [2, 5, 7, 9, 11],
                SA: [3, 6, 11], RA: [3, 6, 10, 11], KE: [3, 6, 10, 11]}

# ── BPHS: combustion (asta) limits in degrees of elongation; Venus and Mercury take the tighter
# limit when retrograde. The Guru/Shukra asta prohibition on marriage is the single strongest of the
# graha rules in the Vivaha Prakarana.
ASTA = {MO: (12.0, 12.0), MA: (17.0, 17.0), ME: (14.0, 12.0), JU: (11.0, 11.0),
        VE: (10.0, 8.0), SA: (15.0, 15.0)}

# ── BPHS: exaltation sign and degree; debilitation is the opposite point ────────────────────────
EXALT = {SU: (0, 10.0), MO: (1, 3.0), MA: (9, 28.0), ME: (5, 15.0), JU: (3, 5.0),
         VE: (11, 27.0), SA: (6, 20.0)}
OWN = {SU: [4], MO: [3], MA: [0, 7], ME: [2, 5], JU: [8, 11], VE: [1, 6], SA: [9, 10]}
# moolatrikona: sign, from-degree, to-degree
MOOLA = {SU: (4, 0.0, 20.0), MO: (1, 4.0, 30.0), MA: (0, 0.0, 12.0), ME: (5, 16.0, 20.0),
         JU: (8, 0.0, 10.0), VE: (6, 0.0, 15.0), SA: (10, 0.0, 20.0)}
# graha drishti (BPHS): every graha aspects the 7th; Mars also the 4th and 8th, Jupiter the 5th and
# 9th, Saturn the 3rd and 10th. Rahu is given 5, 7, 9 by the same convention as Jupiter.
DRISHTI = {SU: [7], MO: [7], ME: [7], VE: [7], MA: [4, 7, 8], JU: [5, 7, 9], SA: [3, 7, 10],
           RA: [5, 7, 9], KE: [5, 7, 9]}


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  array plumbing
# ════════════════════════════════════════════════════════════════════════════════════════════════
_N = [0]


def T(a):
    """Anything shaped (n,), (k, n), (..., n) or already (n, k) -> (n, k) float64."""
    a = np.asarray(a, dtype=np.float64)
    n = _N[0]
    if a.ndim == 1:
        return a[:, None] if a.shape[0] == n else a[None, :]
    if a.ndim == 2 and a.shape[0] == n and a.shape[1] != n:
        return np.ascontiguousarray(a)
    return np.ascontiguousarray(a.reshape(-1, a.shape[-1]).T)


def cat(*parts):
    return np.ascontiguousarray(np.concatenate([T(p) for p in parts], axis=1), dtype=np.float64)


def oh(idx, levels):
    """One-hot of an integer index array (..., n) -> (n, m*levels)."""
    idx = np.asarray(idx, dtype=int)
    n = idx.shape[-1]
    flat = idx.reshape(-1, n)
    out = np.zeros((n, flat.shape[0] * levels))
    rows = np.arange(n)
    for i in range(flat.shape[0]):
        out[rows, i * levels + np.clip(flat[i], 0, levels - 1)] = 1.0
    return out


def circ_idx(idx, levels):
    """cos/sin of a cyclic index -> (n, 2m)."""
    a = 2.0 * np.pi * np.asarray(idx, dtype=np.float64) / levels
    return cat(np.cos(a), np.sin(a))


def isin_f(a, vals):
    return np.isin(np.asarray(a), np.asarray(vals)).astype(np.float64)


def pair_harm(a, b, levels, K=6):
    """A low-rank encoding of a categorical PAIR: outer products of the two circular harmonics.

    A 27x27 nakshatra-pair one-hot is 729 nearly-empty columns; K harmonics give 4K dense columns
    that span the same space smoothly, which is what the contract asks for.
    """
    cols = []
    for k in range(1, K + 1):
        ta = 2.0 * np.pi * k * np.asarray(a, float) / levels
        tb = 2.0 * np.pi * k * np.asarray(b, float) / levels
        ca, sa, cb, sb = np.cos(ta), np.sin(ta), np.cos(tb), np.sin(tb)
        cols += [ca * cb, ca * sb, sa * cb, sa * sb]
    return cat(*cols)


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  zodiac primitives
# ════════════════════════════════════════════════════════════════════════════════════════════════
def sign_of(lon):
    return np.clip((np.mod(lon, 360.0) / 30.0).astype(int), 0, 11)


def deg_in_sign(lon):
    return np.mod(np.mod(lon, 360.0), 30.0)


def nak_of(lon):
    return np.clip((np.mod(lon, 360.0) / NAK).astype(int), 0, 26)


def frac_in_nak(lon):
    return np.mod(np.mod(lon, 360.0), NAK) / NAK


def pada_of(lon):
    return np.clip((np.mod(np.mod(lon, 360.0), NAK) / PADA).astype(int), 0, 3)


def house_from(base_sign, other_sign):
    """Whole-sign house count 1..12 of `other_sign` reckoned from `base_sign` — the Vedic bhava."""
    return ((np.asarray(other_sign) - np.asarray(base_sign)) % 12) + 1


_SIDC = {}


def _sid(E, aya):
    if aya not in _SIDC:
        _SIDC[aya] = E.sidereal(aya)
    return _SIDC[aya]


def _grahas(tab, E):
    """(6, 18, n) body table -> (6, 9, n) in this module's graha order, with Ketu = Rahu + 180."""
    idx = [E.IDX[x] for x in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                              "TrueNode")]
    g = tab[:, idx, :]
    ke = np.mod(g[:, 7, :] + 180.0, 360.0)[:, None, :]
    return np.concatenate([g, ke], axis=1)


def _speeds(E):
    """(6, 9, n) longitude speeds; Ketu shares Rahu's speed."""
    idx = [E.IDX[x] for x in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                              "TrueNode")]
    s = E.SPD[:, idx, :]
    return np.concatenate([s, s[:, 7, :][:, None, :]], axis=1)


def approach(lonA, lonB, spdA, spdB, angle):
    """Rate of closure onto `angle`, deg/day. Positive = APPLYING, negative = SEPARATING.

    d|delta|/dt = sign(delta) * (spdA - spdB); the aspect closes when that carries |delta| toward
    `angle`. This is the electional distinction the muhurta texts turn on (asta versus udaya, an
    applying malefic versus a separating one) and it needs the speeds, not just the positions.
    """
    d = (np.asarray(lonA) - np.asarray(lonB) + 180.0) % 360.0 - 180.0
    s = np.abs(d)
    ddt = np.sign(d) * (np.asarray(spdA) - np.asarray(spdB))
    return -np.sign(s - angle) * ddt


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  the panchanga and the whole day-state of one instant
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _state(E, aya, s):
    """Every day-level quantity the Vivaha checklist reads, at instant slot `s`.

    Tithi and karana rest on the Sun-Moon elongation and are therefore ayanamsa-INDEPENDENT; the
    nakshatra, the nitya yoga, the masa and everything counted in signs move with the ayanamsa,
    which is exactly why the checklist is emitted under four of them.
    """
    sid = _sid(E, aya)
    g = _grahas(sid, E)
    sp = _speeds(E)
    lon, spd = g[s], sp[s]                                   # (9, n)
    sun, moon = lon[SU], lon[MO]
    vsun, vmoon = spd[SU], spd[MO]
    jd = E.JD[s]

    # ── the five limbs ──────────────────────────────────────────────────────────────────────────
    elong = np.mod(moon - sun, 360.0)
    tithi30 = np.clip((elong / 12.0).astype(int), 0, 29)      # 0 = Shukla Pratipada, 29 = Amavasya
    tnum = (tithi30 % 15) + 1                                 # 1..15 within the paksha
    krishna = (tithi30 >= 15)
    tclass = (tnum - 1) % 5                                   # Nanda Bhadra Jaya Rikta Purna
    vara = (np.floor(jd + 1.5).astype(int)) % 7                # 0 = Sunday
    nak = nak_of(moon)
    yoga = np.clip((np.mod(sun + moon, 360.0) / NAK).astype(int), 0, 26)
    h = np.clip((elong / 6.0).astype(int), 0, 59)              # the half-tithi
    karana = np.where(h == 0, 0, np.where(h <= 56, ((h - 1) % 7) + 1, h - 49))

    # ── how much of each limb is left to run (ghatis, in the texts; hours here) ─────────────────
    rel = np.maximum(vmoon - vsun, 1e-3)
    hrs_nak = (1.0 - frac_in_nak(moon)) * NAK / np.maximum(vmoon, 1e-3) * 24.0
    hrs_tithi = (12.0 - np.mod(elong, 12.0)) / rel * 24.0
    hrs_karana = (6.0 - np.mod(elong, 6.0)) / rel * 24.0
    hrs_yoga = (NAK - np.mod(np.mod(sun + moon, 360.0), NAK)) / np.maximum(vmoon + vsun, 1e-3) * 24.0

    # ── the lunar month, and the intercalary Malamasa (adhika masa) ─────────────────────────────
    # PROXY: the previous new moon is back-extrapolated from the elongation. Two estimates are
    # kept — the mean synodic rate and the instantaneous relative speed — because the Moon's rate
    # swings between 11.8 and 15.4 deg/day and the truth lies between them.
    d_mean = elong / SYN_RATE
    d_inst = elong / rel
    sun_nm_mean = np.mod(sun - vsun * d_mean, 360.0)
    sun_nm_inst = np.mod(sun - vsun * d_inst, 360.0)
    # The amanta month is named for the solar sign the Sun ENTERS during it: a lunation beginning
    # with the Sun in Meena is Chaitra, hence (sign at the new moon + 1) mod 12 with Chaitra = 0.
    masa = (sign_of(sun_nm_mean) + 1) % 12
    masa_alt = (sign_of(sun_nm_inst) + 1) % 12
    # A month with NO solar ingress in it is adhika (Malamasa) and closed to marriage. The Sun
    # advances vsun * SYN degrees in a lunation, so the ingress is missed exactly when the Sun sits
    # less than that far short of the next boundary.
    adv = np.clip(vsun * SYN, 27.0, 31.0)
    adhika = (deg_in_sign(sun_nm_mean) < np.maximum(30.0 - adv, 0.0)).astype(float)

    # Chaturmasya proper: Ashadha Shukla Ekadashi (tithi index 10) to Kartika Shukla Ekadashi.
    chaturmasya = (((masa == 3) & (tithi30 >= 10))
                   | np.isin(masa, [4, 5, 6])
                   | ((masa == 7) & (tithi30 < 10))).astype(float)

    # ── the solar month, Kharmas, and the sankranti ─────────────────────────────────────────────
    ssign = sign_of(sun)
    kharmas = isin_f(ssign, KHARMAS_SIGN)
    sdeg = deg_in_sign(sun)
    to_bound = np.minimum(sdeg, 30.0 - sdeg)                  # degrees ~ days from the sankranti
    sankranti = (to_bound < 1.0).astype(float)

    # ── Panchaka (Kalaprakasika): (tithi + vara + nakshatra + lagna) mod 9 ─────────────────────
    # remainder 1 Mrityu, 2 Agni, 4 Raja, 6 Chora, 8 Roga; 0, 3, 5, 7 are panchaka-rahita.
    # PROXY: there is no lagna, so the count is taken twice — once with Surya-lagna (the Sun's sign
    # as the 1st) and once with Chandra-lagna (the Moon's sign as the 1st).
    lag_su = ssign + 1
    lag_mo = sign_of(moon) + 1
    p_su = (tnum + (vara + 1) + (nak + 1) + lag_su) % 9
    p_mo = (tnum + (vara + 1) + (nak + 1) + lag_mo) % 9
    rahita = np.isin(p_su, [0, 3, 5, 7]).astype(float)
    rahita_mo = np.isin(p_mo, [0, 3, 5, 7]).astype(float)

    # ── the North-Indian Panchak, and its five kinds by weekday ────────────────────────────────
    panchak = isin_f(nak, PANCHAK_NAK)
    pk_kind = np.zeros_like(vara)                             # 0 = none
    for v, kind in ((0, 1), (1, 2), (2, 3), (5, 4), (6, 5)):  # Roga Raja Agni Mrityu Chora
        pk_kind = np.where((panchak > 0) & (vara == v), kind, pk_kind)

    # ── gandanta: the water-to-fire junctions, which are also nakshatra junctions ──────────────
    gd = np.minimum.reduce([np.abs((moon - b + 180.0) % 360.0 - 180.0) for b in GANDANTA_DEG])
    gandanta_pada = (gd < PADA).astype(float)                 # within one pada either side
    gandanta_deg = (gd < 3.3333).astype(float)
    abhukta = ((nak == 17) & (pada_of(moon) == 3)) | ((nak == 18) & (pada_of(moon) == 0))

    # ── graha condition at this instant ────────────────────────────────────────────────────────
    sgn = sign_of(lon)                                        # (9, n)
    sep_sun = np.abs((lon - sun[None, :] + 180.0) % 360.0 - 180.0)
    comb = {}
    margin = {}
    for p, (lim_d, lim_r) in ASTA.items():
        lim = np.where(spd[p] < 0, lim_r, lim_d)
        comb[p] = (sep_sun[p] < lim).astype(float)
        margin[p] = lim - sep_sun[p]                          # >0 = combust, by this much
    retro = (spd < 0).astype(float)                           # (9, n)

    return dict(lon=lon, spd=spd, sun=sun, moon=moon, vsun=vsun, vmoon=vmoon, sgn=sgn,
                elong=elong, tithi30=tithi30, tnum=tnum, krishna=krishna.astype(float),
                tclass=tclass, vara=vara, nak=nak, yoga=yoga, karana=karana, halftithi=h,
                hrs_nak=hrs_nak, hrs_tithi=hrs_tithi, hrs_karana=hrs_karana, hrs_yoga=hrs_yoga,
                masa=masa, masa_alt=masa_alt, adhika=adhika, chaturmasya=chaturmasya,
                ssign=ssign, kharmas=kharmas, to_bound=to_bound, sankranti=sankranti,
                p_su=p_su, p_mo=p_mo, rahita=rahita, rahita_mo=rahita_mo,
                panchak=panchak, pk_kind=pk_kind, gd=gd, gandanta_pada=gandanta_pada,
                gandanta_deg=gandanta_deg, abhukta=abhukta.astype(float),
                sep_sun=sep_sun, comb=comb, margin=margin, retro=retro)


def dignity(p, lon):
    """(exalted, own, moolatrikona, debilitated, proximity-to-exaltation) for graha p — BPHS."""
    s, d = sign_of(lon), deg_in_sign(lon)
    es, ed = EXALT[p]
    ex_pt = es * 30.0 + ed
    dist = np.abs((np.mod(lon, 360.0) - ex_pt + 180.0) % 360.0 - 180.0)
    exalt = (s == es).astype(float)
    debil = (s == (es + 6) % 12).astype(float)
    own = isin_f(s, OWN[p])
    ms, m0, m1 = MOOLA[p]
    mool = ((s == ms) & (d >= m0) & (d < m1)).astype(float)
    return exalt, own, mool, debil, 1.0 - dist / 180.0


def tara(frm, to):
    """The ninefold Tara count from a janma nakshatra to another (Raman, *Muhurtha*).

    count = ((to - from) mod 27) + 1; tara = ((count - 1) mod 9) + 1; paryaya = the cycle, 0..2.
    """
    count = ((np.asarray(to) - np.asarray(frm)) % 27) + 1
    t = ((count - 1) % 9) + 1
    par = (count - 1) // 9
    return count, t, par


def yogini(nak0, frac, elapsed):
    """Yogini dasha in force after `elapsed` years, from the janma nakshatra.

    The starting Yogini is (nakshatra number + 3) mod 8 — Deva Keralam / the panchanga digests. The
    BALANCE at birth needs a birth time, so it is taken as the unexpired fraction of the janma
    nakshatra, exactly the noon proxy the Vimshottari balance gets in the sibling module.
    """
    start = (np.asarray(nak0) + 3) % 8
    t0 = YOGINI_CUM[start] + np.asarray(frac) * YOGINI_YR[start]
    coord = np.mod(t0 + np.asarray(elapsed), YOGINI_TOTAL)
    md = np.clip(np.searchsorted(YOGINI_CUM, coord, side="right") - 1, 0, 7)
    inside = coord - YOGINI_CUM[md]
    mdf = inside / YOGINI_YR[md]
    # antardasha: within a mahadasha of L years the sub-periods run in the same order from the
    # mahadasha lord, each L * its own years / 36.
    ad = np.zeros_like(md)
    adf = np.zeros(len(coord))
    for m in range(8):
        sel = (md == m)
        if not sel.any():
            continue
        L = YOGINI_YR[m]
        order = [(m + j) % 8 for j in range(8)]
        sub = np.array([L * YOGINI_YR[o] / YOGINI_TOTAL for o in order])
        cum = np.concatenate([[0.0], np.cumsum(sub)])
        pos = inside[sel]
        j = np.clip(np.searchsorted(cum, pos, side="right") - 1, 0, 7)
        ad[sel] = np.array(order)[j]
        adf[sel] = (pos - cum[j]) / np.maximum(sub[j], 1e-9)
    return dict(start=start, md=md, ad=ad, mdf=mdf, adf=adf, coord=coord)


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  BLOCKS
# ════════════════════════════════════════════════════════════════════════════════════════════════
AYANAMSAS_TESTED = ["Lahiri", "Raman", "Krishnamurti", "True Citra"]
MAIN = "Lahiri"
WED = 2


def _checklist(E, aya):
    """The Vivaha day-purity checklist at the wedding, under one ayanamsa.

    Nakshatra, tithi, vara, yoga, karana, Panchaka, Panchak and gandanta — every limb emitted three
    ways: its identity (one-hot), its membership in the tradition's permitted/forbidden set, and a
    circular encoding, because the same rule scores very differently in each representation.
    """
    W = _state(E, aya, WED)
    nak, tnum, vara, yoga, kar = W["nak"], W["tnum"], W["vara"], W["yoga"], W["karana"]
    cols = [
        # ── nakshatra: identity, the permitted sets, the sevenfold class ────────────────────────
        oh(nak, 27), circ_idx(nak, 27), T(frac_in_nak(W["moon"])), oh(pada_of(W["moon"]), 4),
        T(isin_f(nak, VIVAHA_NAK)),                      # the eleven of Muhurta Chintamani
        T(isin_f(nak, VIVAHA_NAK_WIDE)),                 # the wider regional list
        T((nak == PUSHYA).astype(float)),                # Pushya: good for all but marriage
        oh(NAK_CLASS[nak], 7),
        T(isin_f(NAK_CLASS[nak], [0, 1])),               # Dhruva or Mridu — the recommended classes
        T(isin_f(NAK_CLASS[nak], [4, 6])),               # Ugra or Tikshna — the fierce and the sharp
        oh(NAK_LORD[nak], 9),
        # ── tithi: identity within the paksha, the fivefold class, the exclusions ──────────────
        oh(W["tithi30"], 30), oh(tnum - 1, 15), oh(W["tclass"], 5),
        circ_idx(W["tithi30"], 30), circ_idx(tnum - 1, 15), T(W["elong"] / 360.0),
        T(W["krishna"]), T(isin_f(tnum, TITHI_FAV)), T(isin_f(tnum, TITHI_RIKTA)),
        T((W["tithi30"] == 29).astype(float)),           # Amavasya
        T((W["tithi30"] == 14).astype(float)),           # Purnima
        T((tnum == 8).astype(float)), T((tnum == 6).astype(float)),
        T((tnum == 12).astype(float)), T((tnum == 1).astype(float)),
        T(((W["krishna"] > 0) & (tnum > 10)).astype(float)),   # the dark half after the 10th
        # ── vara ───────────────────────────────────────────────────────────────────────────────
        oh(vara, 7), circ_idx(vara, 7), oh(VARA_LORD[vara], 9),
        T(isin_f(vara, VARA_FAV)), T(isin_f(vara, VARA_BAD)), T((vara == 0).astype(float)),
        # ── nitya yoga ─────────────────────────────────────────────────────────────────────────
        oh(yoga, 27), circ_idx(yoga, 27),
        T(isin_f(yoga, YOGA_BAD)), T(isin_f(yoga, YOGA_FATAL)),
        # ── karana ─────────────────────────────────────────────────────────────────────────────
        oh(kar, 11), circ_idx(W["halftithi"], 60),
        T((kar == VISHTI).astype(float)), T(isin_f(kar, KARANA_FIXED)),
        T(((kar >= 1) & (kar <= 7)).astype(float)),
        # ── Panchaka, both lagna proxies, plus the North-Indian Panchak ────────────────────────
        oh(W["p_su"], 9), oh(W["p_mo"], 9), T(W["rahita"]), T(W["rahita_mo"]),
        T(isin_f(W["p_su"], [1])), T(isin_f(W["p_su"], [2])), T(isin_f(W["p_su"], [4])),
        T(isin_f(W["p_su"], [6])), T(isin_f(W["p_su"], [8])),
        T(W["panchak"]), oh(W["pk_kind"], 6),
        # ── gandanta ───────────────────────────────────────────────────────────────────────────
        T(W["gd"] / 60.0), T(W["gandanta_pada"]), T(W["gandanta_deg"]), T(W["abhukta"]),
        # ── the day's limb-pair interactions the texts actually name ───────────────────────────
        oh(vara * 27 + nak, 189),                        # the vara x nakshatra cell, 7 x 27
        T(isin_f(nak, VIVAHA_NAK) * isin_f(tnum, TITHI_FAV)),
        T(isin_f(nak, VIVAHA_NAK) * isin_f(vara, VARA_FAV)),
        T(isin_f(tnum, TITHI_FAV) * isin_f(vara, VARA_FAV)),
    ]
    return cat(*cols)


def _masa_block(E):
    """Forbidden months and periods: masa, Chaturmasya, Malamasa, Kharmas, the sankranti.

    The lunar month rests on the previous new moon, which is estimated by back-extrapolation (see
    the module docstring, proxy 6); both the mean-rate and instantaneous-rate estimates are emitted
    so the model can see where they disagree, which is precisely where the month is uncertain.
    """
    cols = []
    for aya in ("Lahiri", "True Citra"):
        W = _state(E, aya, WED)
        cols += [
            oh(W["masa"], 12), circ_idx(W["masa"], 12), oh(W["masa_alt"], 12),
            T((W["masa"] == W["masa_alt"]).astype(float)),
            T(isin_f(W["masa"], MASA_BEST)), T(isin_f(W["masa"], MASA_OK)),
            T(isin_f(W["masa"], MASA_FORBID)),
            T(isin_f(W["masa"], [0])),                    # Chaitra, prohibited
            T(isin_f(W["masa"], [9])),                    # Pausha, prohibited
            T(W["chaturmasya"]), T(W["adhika"]),
            oh(W["ssign"], 12), circ_idx(W["ssign"], 12), T(W["kharmas"]),
            T(W["to_bound"] / 15.0), T(W["sankranti"]),
            T(np.mod(W["sun"], 360.0) / 360.0),
        ]
    # the tropical seasonal position too: the same day judged without any ayanamsa at all, which is
    # the control on whether the masa rules are doing anything a bare season could not do
    cols += [T(E.circ(E.LON[WED, E.IDX["Sun"]])), oh(sign_of(E.LON[WED, E.IDX["Sun"]]), 12)]
    W = _state(E, MAIN, WED)
    # Chaturmasya and the permitted months are a lunisolar band; the day of the year is the crudest
    # possible encoding of the same thing and is kept as a control on the doctrine's own version.
    doy = np.mod(E.JD[WED] - 2451545.0, YR) / YR
    cols += [circ_idx(doy * 12.0, 12), T(doy),
             T(W["chaturmasya"] * (1.0 - W["adhika"])),
             T(np.maximum(W["chaturmasya"], W["kharmas"])),
             T(np.maximum.reduce([W["chaturmasya"], W["kharmas"], W["adhika"],
                                  isin_f(W["masa"], MASA_FORBID)]))]
    return cat(*cols)


def _asta_block(E):
    """Guru/Shukra asta — Jupiter or Venus combust — with the applying/separating distinction.

    Muhurta Chintamani, Vivaha Prakarana: no marriage while Jupiter or Venus is set in the Sun's
    rays. This is the strongest of the graha prohibitions and it is inherently directional: a
    planet FALLING into the rays (applying to the Sun) and one CLIMBING out of them (udaya) are
    opposite omens, and the whole reason a family waits is that the second is coming. E.SPD gives
    that sign; the classical degree limits (Jupiter 11, Venus 10 direct / 8 retrograde) give the
    threshold.
    """
    W = _state(E, MAIN, WED)
    lon, spd = W["lon"], W["spd"]
    cols = []
    for p in (JU, VE, ME, MA, SA, MO):
        sep = W["sep_sun"][p]
        ap = approach(lon[p], W["sun"], spd[p], W["vsun"], 0.0)
        cols += [
            T(W["comb"][p]), T(W["margin"][p] / 20.0), T(sep / 180.0),
            T(E.circ(np.mod(lon[p] - W["sun"], 360.0)).reshape(E.n, 2).T),
            T(np.sign(ap)), T(np.clip(ap, -5.0, 5.0)),
            T(W["comb"][p] * (ap > 0)),                   # combust and still closing: deep asta
            T(W["comb"][p] * (ap < 0)),                   # combust but emerging: udaya approaching
            T((~(W["comb"][p] > 0) & (ap > 0) & (sep < 25.0)).astype(float)),   # about to set
            T((~(W["comb"][p] > 0) & (ap < 0) & (sep < 25.0)).astype(float)),   # just risen
            T(W["retro"][p]),
            T(np.abs(spd[p]) / (np.abs(spd[p]).max() + 1e-9)),
            T((np.abs(spd[p]) < 0.05 * np.abs(spd[p]).mean()).astype(float)),   # stationary
        ]
    ju_c, ve_c = W["comb"][JU], W["comb"][VE]
    cols += [
        T(np.maximum(ju_c, ve_c)),                        # the prohibition as the texts state it
        T(ju_c * ve_c), T(ju_c + ve_c),
        T((1.0 - ju_c) * (1.0 - ve_c)),                   # both visible: the fit condition
        # A wider band is used by some panchangas (15 degrees for either), and by others a
        # three-day guard either side of setting and rising.
        T((W["sep_sun"][JU] < 15.0).astype(float)), T((W["sep_sun"][VE] < 15.0).astype(float)),
        T((np.minimum(W["sep_sun"][JU], W["sep_sun"][VE]) < 15.0).astype(float)),
        # Simhastha Guru: Jupiter in sidereal Leo closes marriages in western India.
        T((W["sgn"][JU] == 4).astype(float)),
        T((W["sgn"][JU] == 3).astype(float)),             # Guru exalted in Cancer
        T((W["sgn"][VE] == 11).astype(float)),            # Shukra exalted in Pisces
        T(np.maximum(W["retro"][JU], W["retro"][VE])),    # vakri Guru or Shukra
        oh(W["sgn"][JU], 12), oh(W["sgn"][VE], 12),
    ]
    return cat(*cols)


def _tara_block(E, aya=MAIN):
    """Tara Bala: the ninefold count from EACH partner's janma nakshatra to the wedding nakshatra.

    Raman, *Muhurtha*: count from the janma nakshatra to the day's nakshatra; the 2nd (Sampat),
    4th (Kshema), 6th (Sadhaka), 8th (Mitra) and 9th (Ati-Mitra) taras are fit, and the 1st
    (Janma), 3rd (Vipat), 5th (Pratyari) and 7th (Vadha) are not. Both partners must clear it, so
    the joint category matters and not each alone.

    The janma nakshatra rests on a NOON Moon, uncertain by about +-6 degrees against a 13 deg 20'
    nakshatra, so these counts are right for something like half the couples. They are built anyway:
    this is what the tradition claims, and the claim is what is being tested.
    """
    sid = _sid(E, aya)
    g = _grahas(sid, E)
    nw = nak_of(g[WED, MO])
    cols = []
    ts = []
    for s in (0, 1):
        nb = nak_of(g[s, MO])
        cnt, t, par = tara(nb, nw)
        cnt_r, t_r, par_r = tara(nw, nb)                  # the reverse count: the rule is asymmetric
        ts.append(t)
        cols += [
            oh(t - 1, 9), oh(cnt - 1, 27), oh(par, 3), circ_idx(t - 1, 9), circ_idx(cnt - 1, 27),
            T(isin_f(t, TARA_GOOD)), T(isin_f(t, TARA_BAD)),
            T((t == 1).astype(float)), T((t == 3).astype(float)),
            T((t == 5).astype(float)), T((t == 7).astype(float)),
            T(((t == 1) & (par == 0)).astype(float)),      # first-cycle Janma tara, the worst reading
            oh(t_r - 1, 9), T(isin_f(t_r, TARA_GOOD)),
            oh(nb, 27),
            T((nb == nw).astype(float)),                   # the day's nakshatra IS the janma one
            T((NAK_LORD[nb] == NAK_LORD[nw]).astype(float)),
            oh(NAK_LORD[nb], 9),
        ]
    to, ty = ts
    both_good = isin_f(to, TARA_GOOD) * isin_f(ty, TARA_GOOD)
    cols += [
        oh((to - 1) * 9 + (ty - 1), 81),                   # the joint tara category
        T(both_good),
        T(np.maximum(isin_f(to, TARA_BAD), isin_f(ty, TARA_BAD))),
        T(isin_f(to, TARA_BAD) * isin_f(ty, TARA_BAD)),
        T(isin_f(to, TARA_GOOD) + isin_f(ty, TARA_GOOD)),
        T((to == ty).astype(float)), circ_idx((to - ty) % 9, 9),
        oh((to - ty) % 9, 9),
        T(nak_of(g[0, MO]) == nak_of(g[1, MO])),
    ]
    return cat(*cols)


def _chandra_block(E, aya=MAIN):
    """Chandra Bala and gochara: the wedding sky counted from each partner's janma rasi.

    Chandra Bala (Raman, *Muhurtha*): the Moon of the muhurta in the 1st, 3rd, 6th, 7th, 10th or
    11th from the janma rasi is fit; the 4th, 8th and 12th are unfit — the 8th (Ashtama Chandra)
    being a prohibition in its own right. Gochara extends the same reckoning to every graha with
    its own list of favourable houses. Both are whole-sign counts, which is the Vedic bhava
    convention and needs no birth time; the janma rasi itself, however, is a noon Moon sign and so
    is wrong for perhaps a sixth of the couples.
    """
    sid = _sid(E, aya)
    g = _grahas(sid, E)
    cols = []
    cbs = []
    for s in (0, 1):
        base_mo = sign_of(g[s, MO])
        base_su = sign_of(g[s, SU])
        cb = house_from(base_mo, sign_of(g[WED, MO]))
        cbs.append(cb)
        cols += [
            oh(cb - 1, 12), circ_idx(cb - 1, 12),
            T(isin_f(cb, CB_GOOD)), T(isin_f(cb, CB_BAD)), T(isin_f(cb, CB_MID)),
            T((cb == 8).astype(float)),                    # Ashtama Chandra
            T((cb == 4).astype(float)), T((cb == 12).astype(float)),
            oh(house_from(base_su, sign_of(g[WED, MO])) - 1, 12),
            oh(house_from(base_mo, sign_of(g[WED, SU])) - 1, 12),
            T(E.circ(E.wrap(g[WED, MO] - g[s, MO])).reshape(E.n, 2).T),
            T(np.abs(E.wrap(g[WED, MO] - g[s, MO])) / 180.0),
        ]
        # gochara: every graha's whole-sign house from the janma rasi, with its own fit list
        good = np.zeros(E.n)
        for p in range(9):
            hp = house_from(base_mo, sign_of(g[WED, p]))
            gp = isin_f(hp, GOCHARA_GOOD[p])
            good += gp
            cols += [oh(hp - 1, 12), T(gp)]
        cols += [T(good / 9.0), T((good >= 5).astype(float)), T((good <= 2).astype(float))]
    co, cy = cbs
    cols += [
        oh((co - 1) * 12 + (cy - 1), 144),
        T(isin_f(co, CB_GOOD) * isin_f(cy, CB_GOOD)),
        T(np.maximum(isin_f(co, CB_BAD), isin_f(cy, CB_BAD))),
        T(isin_f(co, CB_GOOD) + isin_f(cy, CB_GOOD)),
        T((co == cy).astype(float)), oh((co - cy) % 12, 12),
    ]
    return cat(*cols)


def _graha_block(E, aya=MAIN):
    """Graha bala at the wedding: dignity, combustion, affliction of the Moon and Venus, Sun-Moon.

    The Vivaha Prakarana asks three things of the sky itself, independently of the couple: that the
    karaka grahas of marriage (Jupiter for the union, Venus for the wife, the Moon for the mind) be
    strong and unafflicted; that Mars and Saturn not fall on the Moon or on Venus by conjunction or
    drishti (BPHS: the 7th for all, plus 4/8 for Mars, 3/10 for Saturn); and that the Sun-Moon
    relation not be an Amavasya. Whole-sign drishti and degree kernels at three orbs are both
    emitted, since the orb is itself a doctrinal parameter.
    """
    W = _state(E, aya, WED)
    lon, spd, sgn = W["lon"], W["spd"], W["sgn"]
    cols = []
    for p in SEVEN:
        ex, ow, mo_, de, prox = dignity(p, lon[p])
        cols += [T(ex), T(ow), T(mo_), T(de), T(prox), oh(sgn[p], 12), T(W["retro"][p]),
                 T(deg_in_sign(lon[p]) / 30.0)]
        if p in W["comb"]:
            cols += [T(W["comb"][p])]
    # affliction of the Moon and of Venus by Mars, Saturn, Rahu and the Sun
    for tgt in (MO, VE, JU):
        for aff in (MA, SA, RA, SU):
            h = house_from(sgn[aff], sgn[tgt])             # the target's house from the afflicter
            dr = isin_f(h, DRISHTI[aff])
            sep = np.abs(E.wrap(lon[tgt] - lon[aff]))
            ap = approach(lon[tgt], lon[aff], spd[tgt], spd[aff], 0.0)
            cols += [
                T(dr), T((h == 1).astype(float)),          # same sign: conjunction
                oh(h - 1, 12), T(sep / 180.0),
                T(E.orbkern(sep, 0.0, 4.0)), T(E.orbkern(sep, 0.0, 8.0)),
                T(E.orbkern(sep, 0.0, 13.0)),
                T(E.orbkern(sep, 180.0, 8.0)), T(E.orbkern(sep, 90.0, 8.0)),
                T(np.sign(ap)), T(dr * (ap > 0)),           # an APPLYING afflicter is the affliction
            ]
    # kartari: malefics on both sides of the Moon by sign — a papa-kartari yoga on the muhurta Moon
    mo_s = sgn[MO]
    before = np.zeros(E.n)
    after = np.zeros(E.n)
    for p in MALEFIC:
        before += (sgn[p] == (mo_s - 1) % 12)
        after += (sgn[p] == (mo_s + 1) % 12)
    cols += [T(before), T(after), T(((before > 0) & (after > 0)).astype(float))]
    # the Sun-Moon relation, and the Moon's paksha bala
    cols += [
        T(W["elong"] / 360.0), T(E.circ(W["elong"]).reshape(E.n, 2).T),
        T(np.minimum(W["elong"], 360.0 - W["elong"]) / 180.0),
        T((W["elong"] < 12.0).astype(float)), T((W["elong"] > 348.0).astype(float)),
        T(W["comb"][MO]),
        oh(house_from(sgn[SU], sgn[MO]) - 1, 12),
        T(W["vmoon"] / 15.0), T((W["vmoon"] > 13.1764).astype(float)),   # a swift Moon
        T(W["hrs_nak"] / 24.0), T(W["hrs_tithi"] / 24.0),
        T(W["hrs_karana"] / 12.0), T(W["hrs_yoga"] / 24.0),
        # Bhrigu-shatka and Jamitra, on the two named lagna PROXIES (see docstring, proxy 2)
        T((house_from(sgn[MO], sgn[VE]) == 6).astype(float)),
        T((house_from(sgn[SU], sgn[VE]) == 6).astype(float)),
        T((house_from(sgn[SU], sgn[MO]) == 7).astype(float)),
        # benefic and malefic counts in the wedding sky's own kendras from the Moon
        T(sum(isin_f(house_from(mo_s, sgn[p]), [1, 4, 7, 10]) for p in BENEFIC)),
        T(sum(isin_f(house_from(mo_s, sgn[p]), [1, 4, 7, 10]) for p in MALEFIC)),
        T(sum(isin_f(house_from(mo_s, sgn[p]), [6, 8, 12]) for p in MALEFIC)),
    ]
    return cat(*cols)


def _yogini_block(E, aya=MAIN):
    """Yogini dasha at the wedding, plus the bare eightfold count — an alternative to Vimshottari.

    The 36-year Yogini cycle (Mangala 1, Pingala 2, Dhanya 3, Bhramari 4, Bhadrika 5, Ulka 6,
    Siddha 7, Sankata 8) starts from (janma nakshatra number + 3) mod 8. The BALANCE at birth needs
    a birth time; the unexpired fraction of the janma nakshatra is used instead, and the mahadasha
    in force at the wedding can therefore be off by one near a boundary. The bare eightfold count
    (the starting Yogini alone, and the count from janma to the wedding nakshatra) is emitted too,
    because it needs no balance at all and so carries none of that error.
    """
    sid = _sid(E, aya)
    g = _grahas(sid, E)
    nw = nak_of(g[WED, MO])
    cols = []
    Ys = []
    for s in (0, 1):
        nb = nak_of(g[s, MO])
        frac = frac_in_nak(g[s, MO])
        elapsed = (E.JD[WED] - E.JD[s]) / YR
        Yg = yogini(nb, frac, elapsed)
        Ys.append(Yg)
        cols += [
            oh(Yg["md"], 8), oh(Yg["ad"], 8), oh(Yg["start"], 8),
            oh(YOGINI_LORD[Yg["md"]], 9), oh(YOGINI_LORD[Yg["ad"]], 9),
            circ_idx(Yg["md"], 8), circ_idx(Yg["coord"], 36),
            T(Yg["mdf"]), T(Yg["adf"]), T(Yg["coord"] / 36.0),
            T(isin_f(Yg["md"], YOGINI_GOOD)), T(isin_f(Yg["ad"], YOGINI_GOOD)),
            T((Yg["md"] == Yg["ad"]).astype(float)),
            T(YOGINI_YR[Yg["md"]] / 8.0), T(elapsed / 60.0),
            # the bare eightfold count, no balance involved
            oh((nb + 3) % 8, 8), oh(((nw - nb) % 27) % 8, 8),
            circ_idx(((nw - nb) % 27) % 8, 8),
        ]
    A, B = Ys
    cols += [
        oh(A["md"] * 8 + B["md"], 64),
        T((A["md"] == B["md"]).astype(float)),
        T(isin_f(A["md"], YOGINI_GOOD) * isin_f(B["md"], YOGINI_GOOD)),
        T(isin_f(A["md"], YOGINI_GOOD) + isin_f(B["md"], YOGINI_GOOD)),
        oh((A["md"] - B["md"]) % 8, 8),
        T((YOGINI_LORD[A["md"]] == YOGINI_LORD[B["md"]]).astype(float)),
        # does the wedding nakshatra's own Yogini agree with either partner's running one?
        oh((nw + 3) % 8, 8),
        T((((nw + 3) % 8) == A["md"]).astype(float)),
        T((((nw + 3) % 8) == B["md"]).astype(float)),
    ]
    return cat(*cols)


# ── the rule set, as the tradition states it: each entry is 1 when the day PASSES ───────────────
def _rules(E, aya=MAIN):
    """Every Vivaha condition as a pass flag, with the weight the texts' emphasis implies.

    Weight 3 = a prohibition the texts treat as closing the day outright (Guru/Shukra asta,
    Chaturmasya, Malamasa, a Rikta tithi, Amavasya, Vishti karana, a forbidden nakshatra, a
    gandanta Moon). Weight 2 = a strong condition. Weight 1 = a preference.
    """
    W = _state(E, aya, WED)
    sid = _sid(E, aya)
    g = _grahas(sid, E)
    nak, tnum, vara, sgn = W["nak"], W["tnum"], W["vara"], W["sgn"]
    nw = nak
    R, WT, GR = {}, {}, {}

    def add(name, ok, w, grp):
        R[name] = np.asarray(ok, dtype=np.float64)
        WT[name] = float(w)
        GR[name] = grp

    # ── the five limbs of the day (dina shuddhi) ────────────────────────────────────────────────
    add("nakshatra permitted", isin_f(nak, VIVAHA_NAK), 3, "panchanga")
    add("nakshatra not Pushya", 1.0 - (nak == PUSHYA), 1, "panchanga")
    add("nakshatra class Dhruva/Mridu", isin_f(NAK_CLASS[nak], [0, 1]), 1, "panchanga")
    add("tithi favoured", isin_f(tnum, TITHI_FAV), 2, "panchanga")
    add("tithi not Rikta", 1.0 - isin_f(tnum, TITHI_RIKTA), 3, "panchanga")
    add("not Amavasya", 1.0 - (W["tithi30"] == 29), 3, "panchanga")
    add("tithi not Ashtami", 1.0 - (tnum == 8), 1, "panchanga")
    add("tithi not Chaturdashi", 1.0 - (tnum == 14), 2, "panchanga")
    add("paksha fit", 1.0 - ((W["krishna"] > 0) & (tnum > 10)), 1, "panchanga")
    add("vara favoured", isin_f(vara, VARA_FAV), 2, "panchanga")
    add("vara not Tue/Sat", 1.0 - isin_f(vara, VARA_BAD), 3, "panchanga")
    add("yoga not inauspicious", 1.0 - isin_f(W["yoga"], YOGA_BAD), 2, "panchanga")
    add("yoga not Vyatipata/Vaidhriti", 1.0 - isin_f(W["yoga"], YOGA_FATAL), 3, "panchanga")
    add("karana not Vishti", 1.0 - (W["karana"] == VISHTI), 3, "panchanga")
    add("karana movable", ((W["karana"] >= 1) & (W["karana"] <= 7)).astype(float), 1, "panchanga")
    add("Panchaka rahita (Surya-lagna proxy)", W["rahita"], 2, "panchanga")
    add("not North Panchak", 1.0 - W["panchak"], 1, "panchanga")
    add("Moon not gandanta", 1.0 - W["gandanta_deg"], 3, "panchanga")
    add("not Abhukta Mula", 1.0 - W["abhukta"], 2, "panchanga")
    # ── kala: the month and the solar year ─────────────────────────────────────────────────────
    add("masa permitted", isin_f(W["masa"], MASA_BEST + MASA_OK), 2, "kala")
    add("masa best four", isin_f(W["masa"], MASA_BEST), 1, "kala")
    add("not Chaturmasya", 1.0 - W["chaturmasya"], 3, "kala")
    add("not Malamasa (adhika)", 1.0 - W["adhika"], 3, "kala")
    add("not Kharmas (Dhanu/Meena)", 1.0 - W["kharmas"], 2, "kala")
    add("not a sankranti day", 1.0 - W["sankranti"], 1, "kala")
    # ── the grahas of the day ──────────────────────────────────────────────────────────────────
    add("Guru not asta", 1.0 - W["comb"][JU], 3, "graha")
    add("Shukra not asta", 1.0 - W["comb"][VE], 3, "graha")
    add("Guru not vakri", 1.0 - W["retro"][JU], 1, "graha")
    add("Shukra not vakri", 1.0 - W["retro"][VE], 1, "graha")
    add("not Simhastha Guru", 1.0 - (sgn[JU] == 4), 1, "graha")
    add("Guru not debilitated", 1.0 - (sgn[JU] == 9), 2, "graha")
    add("Shukra not debilitated", 1.0 - (sgn[VE] == 5), 2, "graha")
    add("no Bhrigu-shatka (Chandra-lagna proxy)", 1.0 - (house_from(sgn[MO], sgn[VE]) == 6), 2,
        "graha")
    add("no Jamitra (Surya-lagna proxy)", 1.0 - (house_from(sgn[SU], sgn[MO]) == 7), 1, "graha")
    # Mars/Saturn on the Moon or on Venus, by conjunction or by drishti
    aff_mo = np.zeros(E.n)
    aff_ve = np.zeros(E.n)
    for aff in (MA, SA):
        aff_mo = np.maximum(aff_mo, isin_f(house_from(sgn[aff], sgn[MO]), DRISHTI[aff]))
        aff_ve = np.maximum(aff_ve, isin_f(house_from(sgn[aff], sgn[VE]), DRISHTI[aff]))
    add("Moon free of Mars/Saturn", 1.0 - aff_mo, 2, "graha")
    add("Venus free of Mars/Saturn", 1.0 - aff_ve, 2, "graha")
    add("Moon not combust", 1.0 - W["comb"][MO], 2, "graha")
    # ── the couple's own conditions: Tara Bala, Chandra Bala, gochara ──────────────────────────
    for lab, s in (("older", 0), ("younger", 1)):
        nb = nak_of(g[s, MO])
        _, t, _ = tara(nb, nw)
        cb = house_from(sign_of(g[s, MO]), sgn[MO])
        add(f"Tara Bala fit ({lab})", isin_f(t, TARA_GOOD), 3, "couple")
        add(f"not Vadha/Pratyari tara ({lab})", 1.0 - isin_f(t, [5, 7]), 2, "couple")
        add(f"Chandra Bala fit ({lab})", isin_f(cb, CB_GOOD), 3, "couple")
        add(f"not Ashtama Chandra ({lab})", 1.0 - (cb == 8), 2, "couple")
        add(f"Guru gochara fit ({lab})",
            isin_f(house_from(sign_of(g[s, MO]), sgn[JU]), GOCHARA_GOOD[JU]), 2, "couple")
        add(f"Shani gochara fit ({lab})",
            isin_f(house_from(sign_of(g[s, MO]), sgn[SA]), GOCHARA_GOOD[SA]), 1, "couple")
    return R, WT, GR


def _tally_block(E):
    """The tradition's own verdict: the whole checklist as pass flags, tallies and thresholds.

    This is the block that states what Vivaha Muhurta actually claims — that a day carrying more of
    these conditions is a better day to marry on. Every rule is emitted individually (so a model can
    find which ones carry anything), then as an unweighted count, a weighted count, four thematic
    sub-counts, and the dosha side of each. The classical practice is not to score at all but to
    REFUSE on any weight-3 failure, so that refusal is emitted too, as the "shuddha" flag.
    """
    cols = []
    for aya in ("Lahiri", "True Citra"):
        R, WT, GR = _rules(E, aya)
        names = list(R)
        M = np.stack([R[k] for k in names], axis=0)            # (rules, n)
        w = np.array([WT[k] for k in names])
        tot = M.sum(axis=0)
        wtot = (M * w[:, None]).sum(axis=0)
        hard = np.array([WT[k] >= 3 for k in names])
        soft = np.array([WT[k] == 2 for k in names])
        shuddha = M[hard].min(axis=0)                           # no weight-3 failure at all
        nhard = (1.0 - M[hard]).sum(axis=0)
        nsoft = (1.0 - M[soft]).sum(axis=0)
        cols += [T(M), T(tot), T(tot / len(names)), T(wtot), T(wtot / w.sum()),
                 T(shuddha), T(nhard), T(nsoft),
                 T((nhard == 0).astype(float)), T((nhard <= 1).astype(float)),
                 T((nhard <= 2).astype(float)),
                 T((tot >= len(names) * 0.6).astype(float)),
                 T((tot >= len(names) * 0.75).astype(float)),
                 T((tot >= len(names) * 0.9).astype(float))]
        for gname in ("panchanga", "kala", "graha", "couple"):
            ks = [k for k in names if GR[k] == gname]
            sub = np.stack([R[k] for k in ks], axis=0)
            wg = np.array([WT[k] for k in ks])
            cols += [T(sub.sum(axis=0)), T(sub.sum(axis=0) / len(ks)), T(sub.min(axis=0)),
                     T((sub * wg[:, None]).sum(axis=0) / wg.sum())]
    return cat(*cols)


def _elec_block(E, aya=MAIN):
    """The electional signature of the moment: applying versus separating, and the limbs' expiry.

    Muhurta reads a moment IN MOTION, so every contact here is signed by its rate of closure from
    E.SPD (positive = applying). The Moon's contacts to the benefics and malefics of the day, the
    wedding Moon's contacts to each partner's natal Moon, Sun and Venus, and the four panchanga
    limbs' remaining hours are all in one block because they are one idea: how long the elected
    condition lasts and which way it is moving.

    The hours-remaining figures are measured FROM NOON, not from the ceremony, whose hour is
    unknown; they are therefore a proxy for "did this limb have room to run on that day".
    """
    W = _state(E, aya, WED)
    lon, spd = W["lon"], W["spd"]
    cols = [
        T(W["hrs_nak"] / 24.0), T(W["hrs_tithi"] / 24.0), T(W["hrs_karana"] / 12.0),
        T(W["hrs_yoga"] / 24.0),
        T((W["hrs_nak"] < 6.0).astype(float)), T((W["hrs_tithi"] < 6.0).astype(float)),
        T((W["hrs_karana"] < 3.0).astype(float)),
        T(np.minimum.reduce([W["hrs_nak"], W["hrs_tithi"], W["hrs_karana"], W["hrs_yoga"]]) / 24.0),
        T(frac_in_nak(W["moon"])), T(np.mod(W["elong"], 12.0) / 12.0),
        # the Moon just entering a nakshatra versus about to leave it — the same day, two omens
        T((frac_in_nak(W["moon"]) < 0.25).astype(float)),
        T((frac_in_nak(W["moon"]) > 0.75).astype(float)),
        T(W["vmoon"] / 15.0), T(W["vsun"]),
        T(W["vmoon"] - W["vsun"]),
    ]
    # the wedding Moon applying to / separating from every other graha of the day
    for p in (SU, ME, VE, MA, JU, SA, RA):
        sep = np.abs(E.wrap(lon[MO] - lon[p]))
        for ang in (0.0, 60.0, 90.0, 120.0, 180.0):
            ap = approach(lon[MO], lon[p], spd[MO], spd[p], ang)
            k = E.orbkern(sep, ang, 6.0)
            cols += [T(k), T(np.sign(ap) * k), T((ap > 0).astype(float) * k)]
        cols += [T(sep / 180.0), T(np.sign(approach(lon[MO], lon[p], spd[MO], spd[p], 0.0)))]
    # a benefic-minus-malefic balance, counted only over APPLYING contacts within 6 degrees
    ben = np.zeros(E.n)
    mal = np.zeros(E.n)
    for p in (ME, VE, JU):
        sep = np.abs(E.wrap(lon[MO] - lon[p]))
        ben += ((sep < 6.0) & (approach(lon[MO], lon[p], spd[MO], spd[p], 0.0) > 0)).astype(float)
    for p in (SU, MA, SA, RA, KE):
        sep = np.abs(E.wrap(lon[MO] - lon[p]))
        mal += ((sep < 6.0) & (approach(lon[MO], lon[p], spd[MO], spd[p], 0.0) > 0)).astype(float)
    cols += [T(ben), T(mal), T(ben - mal), T((mal > 0).astype(float))]
    # the wedding sky applying to each partner's natal points — transit contact, signed
    sid = _sid(E, aya)
    g = _grahas(sid, E)
    sp = _speeds(E)
    for s in (0, 1):
        for wp, nt in ((MO, MO), (MO, SU), (MO, VE), (JU, MO), (JU, VE), (SA, MO), (MA, VE),
                       (VE, VE), (SU, MO)):
            sep = np.abs(E.wrap(g[WED, wp] - g[s, nt]))
            # a natal point does not move, so the transiting body's own speed carries the sign
            ap = approach(g[WED, wp], g[s, nt], sp[WED, wp], 0.0, 0.0)
            cols += [T(E.orbkern(sep, 0.0, 6.0)), T(E.orbkern(sep, 180.0, 6.0)),
                     T(E.orbkern(sep, 120.0, 6.0)), T(sep / 180.0), T(np.sign(ap)),
                     T(np.sign(ap) * E.orbkern(sep, 0.0, 6.0))]
    return cat(*cols)


def _pair_block(E, aya=MAIN):
    """The (wedding limb, natal limb) PAIRS, low-rank — the muhurta's own asymmetric arithmetic.

    Tara Bala already reduces the nakshatra pair to nine categories; this block keeps the pair
    itself, encoded as products of circular harmonics rather than as a 27x27 one-hot, and does the
    same for the wedding sign against each natal Moon sign and for the two partners' taras jointly.
    """
    sid = _sid(E, aya)
    g = _grahas(sid, E)
    nw = nak_of(g[WED, MO])
    sw = sign_of(g[WED, MO])
    cols = []
    ts = []
    for s in (0, 1):
        nb = nak_of(g[s, MO])
        sb = sign_of(g[s, MO])
        _, t, _ = tara(nb, nw)
        ts.append(t)
        cols += [pair_harm(nw, nb, 27, K=6), pair_harm(sw, sb, 12, K=4),
                 pair_harm(nw, nak_of(g[s, SU]), 27, K=3),
                 circ_idx((nw - nb) % 27, 27), oh((nw - nb) % 27, 27)]
    cols += [pair_harm(ts[0] - 1, ts[1] - 1, 9, K=4),
             pair_harm(nak_of(g[0, MO]), nak_of(g[1, MO]), 27, K=4),
             pair_harm(nw, (nak_of(g[0, MO]) + nak_of(g[1, MO])) % 27, 27, K=3)]
    return cat(*cols)


def _prog_block(E, aya=MAIN):
    """The same muhurta arithmetic against slots 3, 4 and 5 — an ADAPTATION, not a Vedic rule.

    Secondary progression and the Davison chart belong to modern Western practice, not to Jyotisha;
    no muhurta text knows them. They are used here because the dataset provides them and because
    they are two further legitimate "charts of the couple at the wedding": the progressed chart is
    each partner's own advanced sky, and the Davison chart is the couple's single shared one. The
    Tara and Chandra Bala counts are re-run from those Moons instead of the natal Moons, and the
    Davison instant is put through the whole panchanga. This is labelled an adaptation and should
    not be read as doctrine.
    """
    sid = _sid(E, aya)
    g = _grahas(sid, E)
    nw = nak_of(g[WED, MO])
    cols = []
    for s in (3, 4):
        nb = nak_of(g[s, MO])
        _, t, par = tara(nb, nw)
        cb = house_from(sign_of(g[s, MO]), sign_of(g[WED, MO]))
        cols += [
            oh(nb, 27), oh(t - 1, 9), T(isin_f(t, TARA_GOOD)), T(isin_f(t, TARA_BAD)),
            oh(cb - 1, 12), T(isin_f(cb, CB_GOOD)), T(isin_f(cb, CB_BAD)),
            circ_idx(nb, 27), T(frac_in_nak(g[s, MO])),
            # the progressed Sun-Moon elongation: a "progressed tithi"
            T(np.mod(g[s, MO] - g[s, SU], 360.0) / 360.0),
            oh(np.clip((np.mod(g[s, MO] - g[s, SU], 360.0) / 12.0).astype(int), 0, 29), 30),
            T(E.circ(E.wrap(g[s, MO] - g[WED, MO])).reshape(E.n, 2).T),
            T(np.abs(E.wrap(g[s, VE] - g[WED, VE])) / 180.0),
        ]
    D = _state(E, aya, 5)
    cols += [
        oh(D["nak"], 27), oh(D["tithi30"], 30), oh(D["vara"], 7), oh(D["yoga"], 27),
        oh(D["karana"], 11), circ_idx(D["nak"], 27), circ_idx(D["tithi30"], 30),
        T(isin_f(D["nak"], VIVAHA_NAK)), T(isin_f(D["tnum"], TITHI_FAV)),
        T(isin_f(D["tnum"], TITHI_RIKTA)), T((D["karana"] == VISHTI).astype(float)),
        T(isin_f(D["vara"], VARA_FAV)), T(isin_f(D["yoga"], YOGA_BAD)),
        oh(D["masa"], 12), T(D["chaturmasya"]), T(D["kharmas"]),
        T(D["comb"][JU]), T(D["comb"][VE]),
    ]
    # Tara and Chandra Bala of the wedding reckoned from the DAVISON Moon — the couple's own
    # composite janma point, in place of two separate ones
    nd = D["nak"]
    _, td, _ = tara(nd, nw)
    cbd = house_from(sign_of(D["moon"]), sign_of(g[WED, MO]))
    cols += [oh(td - 1, 9), T(isin_f(td, TARA_GOOD)), oh(cbd - 1, 12), T(isin_f(cbd, CB_GOOD)),
             oh((nw - nd) % 27, 27), circ_idx((nw - nd) % 27, 27),
             T(np.abs(E.wrap(g[WED, MO] - D["moon"])) / 180.0),
             T(np.abs(E.wrap(g[WED, JU] - D["lon"][JU])) / 180.0)]
    return cat(*cols)


# ════════════════════════════════════════════════════════════════════════════════════════════════
def build(E):
    _N[0] = E.n
    _SIDC.clear()
    out = {}
    for aya in AYANAMSAS_TESTED:
        out[f"muh: vivaha day-purity checklist [{aya}]"] = _checklist(E, aya)
    out["muh: masa, chaturmasya & malamasa"] = _masa_block(E)
    out["muh: guru-shukra asta (asta vs udaya)"] = _asta_block(E)
    out["muh: tara bala from both janma nakshatras"] = _tara_block(E)
    out["muh: chandra bala & gochara from janma rasi"] = _chandra_block(E)
    out["muh: graha bala & affliction at the wedding"] = _graha_block(E)
    out["muh: yogini dasha + eightfold count"] = _yogini_block(E)
    out["muh: the vivaha rule tally (own verdict)"] = _tally_block(E)
    out["elec: applying vs separating + limb expiry"] = _elec_block(E)
    out["wt: wedding-natal limb pairs, low-rank"] = _pair_block(E)
    out["wt: progressed & davison muhurta (adaptation)"] = _prog_block(E)
    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    import time
    from core import load
    from evalx import quick

    t0 = time.time()
    E = load()
    B = build(E)
    print(f"{TRADITION}\n{len(B)} blocks, built in {time.time()-t0:.1f}s\n")
    total = 0
    bad = 0
    for name, X in B.items():
        try:
            assert isinstance(X, np.ndarray), f"{name}: not an ndarray"
            assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
            assert X.ndim == 2 and X.shape[0] == E.n, f"{name}: shape {X.shape} != ({E.n}, k)"
            assert np.isfinite(X).all(), f"{name}: non-finite values"
            assert X.std(axis=0).max() > 0, f"{name}: all-constant"
        except AssertionError as e:
            print(f"FAIL {e}")
            bad += 1
            continue
        total += X.shape[1]
        a, u = quick(E, X)
        print(f"  {name:<48} {X.shape[1]:>5} cols   acc {100*a:5.2f}%   AUC {u:.4f}")
    print(f"\ntotal columns {total}")
    if bad:
        print(f"{bad} block(s) failed")
        sys.exit(1)
    print("OK")
