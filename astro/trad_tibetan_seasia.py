"""
trad_tibetan_seasia.py — Tibetan nagtsi (elemental astrology of the Kalachakra tradition), Burmese
Mahabote, Thai rerk and day-colours, and the Javanese/Balinese Pawukon with its wetonan marriage
arithmetic.

Five calendrical traditions that share almost no astronomy and almost all of their method: each one
turns a BIRTH DATE into a small set of cycle positions, and then judges a marriage by comparing the
two people's positions with a closed-form rule. That is exactly what this dataset can support — dates
are all we have — so this family is unusually well served here. Nothing below needs a birth time
except where flagged, nothing needs a birth place, and nothing needs houses.

═══ EPOCHS AND ANCHORS, all stated, all asserted in __main__ ═══════════════════════════════════════

  JULIAN DAY NUMBER   jdn = floor(JD + 0.5); every instant in this dataset is 12:00 UT, so jdn is the
                      civil day. Weekday = (jdn + 1) mod 7 with 0 = Sunday. Anchor: jdn 2451545 =
                      1 January 2000 = Saturday. Asserted.

  TIBETAN 60-YEAR     The rab byung (rabjung) cycle. The FIRST rabjung began in 1027 CE, a
  CYCLE               FIRE-RABBIT year (me yos). That single anchor fixes both wheels, because the
                      Tibetan year animal/element pair is the Chinese sexagenary year: index
                      (Y - 1984) mod 60 with 0 = Wood-Mouse reproduces 1027 = Fire-Rabbit exactly,
                      and 2026 = Fire-Horse (me rta). Asserted for both years.
                      YEAR BOUNDARY — A DOCUMENTED PROXY, NOT THE PHUGPA CALENDAR. The Tibetan year
                      begins at Losar, the first day of the first Tibetan month, which falls between
                      early February and early March. The exact date needs the Phugpa (phug lugs)
                      intercalation arithmetic — 67 synodic months per 65 zodiacal months, Janson's
                      "true month" count — which is more machinery than is warranted here. The proxy
                      used is the lunisolar rule Losar shares with Chinese New Year: THE SECOND NEW
                      MOON AFTER THE DECEMBER SOLSTICE, computed from Meeus, *Astronomical
                      Algorithms*, ch. 49 (new moon, 17 periodic terms) and ch. 27 table 27.B
                      (December solstice). In roughly half of all years it lands within a day of the
                      true Losar (2021, 2024 and 2026 checked: proxy 11 Feb, 9 Feb, 17 Feb against
                      the true 12 Feb, 10 Feb, 18 Feb — the day of slack is Tibetan local time
                      against a UT-floored new moon), and in the rest it is a whole lunar month early
                      (2022, 2023, 2025), because Phugpa sometimes inserts a leap month that Chinese
                      reckoning does not. Consequence: about 4% of birth years get the neighbouring
                      animal/element. Mitigations, both emitted as features rather than hidden: the
                      1-January-boundary variant of the same wheels, and the signed distance in days
                      from the proxy Losar so a model can see which rows sit in the ambiguous month.

  MEWA (sme ba dgu)   The nine numbers of the Lo Shu magic square, which Tibetan astrology took from
                      China along with the animals and elements. The year mewa runs a DESCENDING
                      nine-count: mewa = ((1 - Y) mod 9) + 1. Anchored on the published annual
                      nine-star series that the sme ba shares with the Chinese 年紫白: 2024 = 3,
                      2025 = 2, 2026 = 1. Asserted. Tibetan practice counts backwards for a man and
                      forwards for a woman; SEX IS UNKNOWN in this dataset, so both counts are
                      emitted for both partners and all four sex assignments are formed.

  PARKHA (spar kha)   The eight trigrams, in the Tibetan clockwise order Li(S) Khon(SW) Da(W)
                      Khen(NW) Kham(N) Gin(NE) Zin(E) Zon(SE) — the Later Heaven arrangement. TWO
                      derivations, because they rest on different amounts of evidence:
                      (a) FROM THE ANIMAL'S DIRECTION, which is solid: the twelve animals sit on the
                          compass (Mouse N, Rabbit E, Horse S, Bird W, the rest filling the
                          quadrants), so each animal falls in one trigram's sector. This one is used
                          for everything that needs the trigram's identity — its element and its
                          three lines.
                      (b) FROM AN EIGHT-YEAR COUNT, whose absolute phase I could NOT verify against
                          a primary source offline. It is therefore anchored arbitrarily and only
                          its DIFFERENCES are used in the pair features — a difference of two counts
                          is invariant to the anchor, so an unknown rotation costs nothing there.
                          The per-partner one-hot of (b) is emitted too, but it is a relabelling of
                          the truth, not the truth: say so if these columns ever matter.

  BURMESE ERA         Burmese year ME = (Gregorian year of the preceding Meṣa saṅkrānti) - 638.
                      Anchor: ME 1386 began 17 April 2024. The saṅkrānti (Thingyan) is the sidereal
                      entry of the Sun into Aries, so it is computed from the sidereal solar
                      longitude rather than a fixed calendar date — which matters over four
                      centuries, since the sidereal year runs 1.4 days per century longer than the
                      Gregorian. Lahiri is used for the ingress; the Burmese Makaranta tables have
                      drifted about three days later than the true ingress, so births inside that
                      three-day window in mid-April can be assigned the neighbouring Burmese year.

  THAI              Same Meṣa saṅkrānti boundary (Songkran, 13-15 April) for the Thai animal year;
                      Lahiri puts the true ingress on 13 April 2024, which is Songkran itself.

  PAWUKON           The 210-day Javanese/Balinese week-of-weeks. Anchored on GALUNGAN, which by
                      definition falls on Buda Kliwon Dungulan — Wednesday, pancawara Kliwon, in the
                      eleventh wuku — and which fell on 28 February 2024. That makes 28 Feb 2024
                      pawukon day 74. FOUR INDEPENDENT CHECKS all fall out of that one anchor and
                      are asserted in __main__: Galungan 25 Sep 2024 (210 days later), Saraswati
                      (Saniscara Umanis Watugunung) 13 July 2024 = day 210, Pagerwesi (Buda Kliwon
                      Sinta) 17 July 2024 = day 4, and the Javanese weton of Indonesian independence,
                      17 August 1945 = Jumat Legi (Friday, pancawara Legi/Umanis). Day 1 of wuku
                      Sinta is Redite Paing; pancawara = day mod 5, which is what all four anchors
                      independently require.

═══ WHAT EACH TRADITION CONTRIBUTES ══════════════════════════════════════════════════════════════

TIBETAN (nag rtsis / the marriage reckoning). The comparison of two horoscopes in Tibetan elemental
astrology is made on five axes, each judged good, neutral or bad, and then read together — see
Philippe Cornu, *Tibetan Astrology* (Shambhala 1997), the chapter on comparing horoscopes, which
follows the *Vaidurya dkar po* tradition of Sangye Gyatso:
  srog     the LIFE-FORCE element, which is the element of the year ANIMAL (Mouse water, Ox earth,
           Tiger and Rabbit wood, Dragon earth, Snake and Horse fire, Sheep earth, Monkey and Bird
           iron, Dog earth, Pig water);
  khams    the element OF THE YEAR itself, from the sexagenary pair;
  animal   the four harmonious groups of three (Mouse-Dragon-Monkey, Ox-Snake-Bird,
           Tiger-Horse-Dog, Rabbit-Sheep-Pig — equivalently: equal residues mod 4), the six opposing
           pairs six apart (dgra), the six gshed or "destroyer" pairs where the two indices sum to 7
           mod 12, and the six srog-grogs "secret friend" pairs summing to 1 mod 12;
  mewa     the two sme ba compared: identical, complementary (summing to 10, opposite cells of the
           magic square), and the relation of their elements;
  parkha   the two trigrams compared: the relation of their elements, and which of their three lines
           differ — no line changed, top only, bottom+middle, all three, bottom only, bottom+top,
           middle+top, middle only, being the eight relations of the Chinese Eight Mansions that
           Tibetan parkha pairing shares (four favourable, four not).
Element relations are the five-element cycle in both directions: generating (mother/son) Wood → Fire
→ Earth → Iron → Water → Wood, and overcoming (enemy) Wood → Earth → Water → Fire → Iron → Wood.
The composite tally scores each axis and sums them. THE WEIGHTS ARE ONE READING; the raw flags every
weight is applied to are emitted separately, in their own blocks, so nothing rests on the weighting.

BURMESE MAHABOTE. Seven houses — Binga, Ahtun, Yaza, Adipati, Marana, Thike, Puti — built from two
integers and nothing else: the birth weekday and the year remainder, ME mod 7. The eight-day week is
real and is included (Wednesday is split, the afternoon belonging to Rahu/Yahu) together with its
weekday animals (Sunday galon/garuda, Monday tiger, Tuesday lion, Wednesday-morning tusked elephant,
Wednesday-afternoon tuskless elephant, Thursday rat, Friday guinea pig, Saturday naga) and the
Shwedagon planetary directions. TWO HONEST LIMITS. (1) THE WEDNESDAY SPLIT CANNOT BE COMPUTED: it
needs the hour of birth, and every instant here is noon. Every Wednesday is therefore taken as the
morning half, Mercury; the Rahu eighth day never occurs and its column is omitted rather than faked,
and a plain "born on a Wednesday" indicator marks the rows where the true answer is a coin flip.
(2) The rotation that maps (weekday, remainder) onto the named house could not be verified against a
primary source offline, so BOTH count directions are emitted, and the pair features are built from
the house OFFSET, which is invariant to the rotation.

THAI. The 27 rerk (ฤกษ์), the lunar mansions, taken from the sidereal Moon; and their grouping into
the nine classes that Thai practice actually judges a wedding day by — rerk = mansion mod 9, giving
Talitto (the beggar), Mahatthano (the wealthy), Joro (the thief), Phumipalo (the earth-protector),
Thesatri (the night traveller), Thewi (the queen — the marriage rerk), Petchakhat (the executioner),
Racha (the king), Samano (the ascetic). Since the rerk governs the CHOICE OF DAY, it is computed for
the wedding as well as for both births. Plus the day-colour system, which is a genuinely different
representation of the same seven-day wheel: Sunday red, Monday yellow, Tuesday pink, Wednesday
green, Thursday orange, Friday blue, Saturday purple, encoded as a hue angle.
THE MOON IS THE WEAKEST INPUT IN THIS MODULE. Its noon longitude is off by up to ~6° against the real
birth moment and a mansion is 13°20' wide, so a mansion label is close to a coin flip between itself
and its neighbour, and the nine-class label is better only because it is coarser in a different
direction. Built because the doctrine is lunar; reported as unreliable.

JAVANESE PAWUKON AND WETONAN. The concurrent cycles — ekawara 1, dwiwara 2, triwara 3, caturwara 4,
pancawara 5 (the pasaran), sadwara 6 (paringkelan), saptawara 7, astawara 8, sangawara 9, dasawara
10, and the 30 wuku — and the wetonan, pasaran × weekday, 35 positions, which is the object Javanese
marriage arithmetic is done on. The neptu (urip) numbers are the standard ones: weekday Sunday 5,
Monday 4, Tuesday 3, Wednesday 7, Thursday 8, Friday 6, Saturday 9; pasaran Legi 5, Pahing 9, Pon 7,
Wage 4, Kliwon 8. The traditional verdicts are sums and remainders of those numbers over BOTH
partners, and three of them are implemented exactly:
  mod 8   1 Pegat (separation) · 2 Ratu (queen) · 3 Jodoh (well matched) · 4 Topo (hardship first) ·
          5 Tinari (fortunate) · 6 Padu (quarrelling) · 7 Sujanan (strife) · 8 Pesthi (destined);
  mod 7   1 Wasesa Segara · 2 Tunggak Semi · 3 Satriya Wibawa · 4 Sumur Sinaba · 5 Satriya Wirang ·
          6 Bumi Kapetak · 7 Lebu Katiup Angin  (the Pasatowan Salaki Rabi count);
  mod 5   1 Sri · 2 Lungguh · 3 Dunya · 4 Lara · 5 Pati.
The mod 4, 3, 9 and 10 remainders are emitted as bare structure, WITHOUT verdict names, because the
name lists I could recall for those are not ones I would stake a citation on. Favourability numbers
attached to the named verdicts are one reading; the remainder one-hots they are derived from are
emitted beside them.

BALINESE. The same Pawukon with the cycles Java mostly drops, and their intercalation, which is
arithmetic rather than lore and closes exactly: caturwara (210 = 4·52 + 2) and astawara (210 = 8·26
+ 2) hold one name for three days at pawukon days 71-73, in wuku Dungulan; sangawara (210 = 9·23 + 3)
holds Dangu for the first four days of wuku Sinta. Both intercalations are forced by the requirement
that day 210 carry the last name and day 1 the first, and both are checked in __main__. Dasawara,
ekawara and dwiwara are not day-counts at all but functions of the urip: dasawara = (urip pancawara
+ urip saptawara) mod 10, and Luang/Menga/Pepet are that sum's parity. Then the padewasan — the
day-choosing layer that a Balinese wedding is actually scheduled by: Kajeng Kliwon, Tumpek
(Saniscara Kliwon), Buda Kliwon, Buda Cemeng (Buda Wage), Anggara Kasih (Anggara Kliwon), birth in
wuku Wayang (which calls for a bayuh oton purification), and the lunar day — penanggal waxing,
panglong waning, purnama full, tilem new — which is the one place in this module where the ephemeris
proper is used, via the Sun-Moon elongation.

WHAT COULD NOT BE IMPLEMENTED, and why, is listed at the bottom of this file.
"""

import numpy as np

TRADITION = "Tibetan, Burmese, Thai, Javanese and Balinese (nagtsi, Mahabote, rerk, Pawukon wetonan)"

# ══════════════════════════════════════════════════════════════════════════════════════════════════
# CALENDAR ARITHMETIC — pure integer, no tables, no I/O
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _jdn(jd):
    """Julian Day Number of the civil day containing the instant. Anchor: 2451545 = 2000-01-01."""
    return np.floor(np.asarray(jd, float) + 0.5).astype(np.int64)


def _greg(jdn):
    """JDN -> (year, month, day), proleptic Gregorian (Fliegel-Van Flandern, integer only)."""
    j = np.asarray(jdn, np.int64)
    a = j + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    return 100 * b + d - 4800 + m // 10, m + 3 - 12 * (m // 10), e - (153 * m + 2) // 5 + 1


def _jdn_of(y, m, d):
    """(year, month, day) -> JDN, Gregorian."""
    y = np.asarray(y, np.int64); m = np.asarray(m, np.int64); d = np.asarray(d, np.int64)
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _dow(jdn):
    """0 = Sunday .. 6 = Saturday."""
    return (np.asarray(jdn, np.int64) + 1) % 7


def _dec_solstice(year):
    """JD(TD) of the December solstice — Meeus, *Astronomical Algorithms*, table 27.B."""
    Y = (np.asarray(year, float) - 2000.0) / 1000.0
    return (2451900.05952 + 365242.74049 * Y - 0.06223 * Y ** 2
            - 0.00823 * Y ** 3 + 0.00032 * Y ** 4)


def _new_moon(k):
    """JD(TD) of new moon number k from 2000-01-06 — Meeus ch. 49, the 17 largest periodic terms.
    Verified against the new moon of 2024-02-09 22:59 UT to better than 0.002 day."""
    k = np.asarray(k, float)
    T = k / 1236.85
    jde = (2451550.09766 + 29.530588861 * k + 0.00015437 * T ** 2
           - 0.000000150 * T ** 3 + 0.00000000073 * T ** 4)
    Ec = 1.0 - 0.002516 * T - 0.0000074 * T ** 2
    M = np.deg2rad(2.5534 + 29.10535670 * k - 0.0000014 * T ** 2 - 0.00000011 * T ** 3)
    Mp = np.deg2rad(201.5643 + 385.81693528 * k + 0.0107582 * T ** 2
                    + 0.00001238 * T ** 3 - 0.000000058 * T ** 4)
    F = np.deg2rad(160.7108 + 390.67050284 * k - 0.0016118 * T ** 2
                   - 0.00000227 * T ** 3 + 0.000000011 * T ** 4)
    Om = np.deg2rad(124.7746 - 1.56375588 * k + 0.0020672 * T ** 2 + 0.00000215 * T ** 3)
    c = (-0.40720 * np.sin(Mp) + 0.17241 * Ec * np.sin(M) + 0.01608 * np.sin(2 * Mp)
         + 0.01039 * np.sin(2 * F) + 0.00739 * Ec * np.sin(Mp - M)
         - 0.00514 * Ec * np.sin(Mp + M) + 0.00208 * Ec * Ec * np.sin(2 * M)
         - 0.00111 * np.sin(Mp - 2 * F) - 0.00057 * np.sin(Mp + 2 * F)
         + 0.00056 * Ec * np.sin(2 * Mp + M) - 0.00042 * np.sin(3 * Mp)
         + 0.00042 * Ec * np.sin(M + 2 * F) + 0.00038 * Ec * np.sin(M - 2 * F)
         - 0.00024 * Ec * np.sin(2 * Mp - M) - 0.00017 * np.sin(Om)
         - 0.00007 * np.sin(Mp + 2 * M))
    return jde + c


def _losar_jdn(year):
    """PROXY for the Tibetan new year of `year`: the second new moon after the December solstice of
    year-1, floored to a civil day. See the epoch note in the module docstring — this is the
    lunisolar rule Losar shares with Chinese New Year, not the Phugpa intercalation."""
    ws = _dec_solstice(np.asarray(year, np.int64) - 1)
    k = np.ceil((ws - 2451550.09766) / 29.530588861)
    k = np.where(_new_moon(k) < ws, k + 1, k)          # first new moon at or after the solstice
    return np.floor(_new_moon(k + 1) + 0.5).astype(np.int64)


def _mesa_year(gyear, doy, sid_sun):
    """Gregorian year of the Meṣa saṅkrānti (sidereal Aries ingress, mid-April) that opened the
    sidereal solar year this instant falls in. The test is robust by construction: days since the
    ingress are ~ sid_sun / 0.98565, so `doy - that` lands near +104 for a date after the ingress
    and near -261 for one before it — nowhere near the zero it is compared against."""
    t = np.asarray(doy, float) - np.asarray(sid_sun, float) / 0.98565
    return np.asarray(gyear, np.int64) - (t < 0).astype(np.int64)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# TIBETAN TABLES
# ══════════════════════════════════════════════════════════════════════════════════════════════════
# elements throughout this module: 0 shing Wood, 1 me Fire, 2 sa Earth, 3 lcags Iron, 4 chu Water
# animals: 0 Mouse 1 Ox 2 Tiger 3 Rabbit 4 Dragon 5 Snake 6 Horse 7 Sheep 8 Monkey 9 Bird 10 Dog 11 Pig

# srog — the life-force element of each animal (identical to the Chinese branch element)
SROG = np.array([4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4])

# the animal's compass sector, hence its parkha: Li(S) Khon(SW) Da(W) Khen(NW) Kham(N) Gin(NE)
# Zin(E) Zon(SE) = indices 0..7.  Mouse N, Rabbit E, Horse S, Bird W; corners take two animals each.
PARKHA = ["Li", "Khon", "Da", "Khen", "Kham", "Gin", "Zin", "Zon"]
ANIMAL_PARKHA = np.array([4, 5, 5, 6, 7, 7, 0, 1, 1, 2, 3, 3])

# trigram lines as bits, bit0 = bottom line, 1 = yang.  Li 101, Khon 000, Da 110, Khen 111,
# Kham 010, Gin 001, Zin 100, Zon 011  (written bottom-middle-top).
PARKHA_BITS = np.array([5, 0, 3, 7, 2, 4, 1, 6])
# the Tibetan element of each trigram: Li fire, Khon earth, Da iron, Khen iron(sky), Kham water,
# Gin earth(mountain), Zin wood, Zon wood(wind)
PARKHA_EL = np.array([1, 2, 3, 3, 4, 2, 0, 0])

# the eight relations of a trigram pair, keyed by which lines differ (the XOR of the line bits).
# 0 none = Fu Wei · 4 top = Sheng Qi · 3 bottom+middle = Tian Yi · 7 all = Yan Nian ·
# 1 bottom = Huo Hai · 5 bottom+top = Liu Sha · 6 middle+top = Wu Gui · 2 middle = Jue Ming
XOR2REL = np.array([0, 4, 7, 2, 1, 5, 6, 3])          # index = xor, value = relation index 0..7
REL8_SCORE = np.array([1., 3., 2., 2., -1., -2., -3., -3.])   # four favourable, four not

# mewa elements — two readings, both emitted (see docstring). d = 0..8 for sme ba 1..9.
MEWA_EL_LOSHU = np.array([4, 2, 0, 0, 2, 3, 3, 2, 1])   # the Chinese nine-star elements
MEWA_EL_COLOUR = np.array([3, 4, 4, 0, 2, 3, 1, 3, 1])  # from the Tibetan colours white/black/blue/
#                                                        green/yellow/white/red/white/red

# element relation, keyed by d = (element_b - element_a) mod 5:
#   0 same (grogs, friend) · 1 a is mother of b · 2 a overcomes b (enemy) ·
#   3 b overcomes a (enemy) · 4 a is son of b
REL5_SCORE = np.array([1., 2., -2., -2., 2.])
REL5_NAME = ["friend", "mother", "enemy(a kills b)", "enemy(b kills a)", "son"]


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# BURMESE TABLES
# ══════════════════════════════════════════════════════════════════════════════════════════════════
# the eight-day week: 0 Sun 1 Mon 2 Tue 3 Wed(morning) 4 Thu 5 Fri 6 Sat, and 7 = Rahu
# (Wednesday afternoon) which CANNOT OCCUR here — no birth times.
MAHABOTE_HOUSE = ["Binga", "Ahtun", "Yaza", "Adipati", "Marana", "Thike", "Puti"]
# conventional valuation of the house names: Yaza the king, Adipati the lord, Thike the treasure,
# Marana death, Puti putrefaction; Binga and Ahtun are read in context and are left neutral.
HOUSE_SCORE = np.array([0., 1., 2., 2., -3., 2., -2.])
# Shwedagon planetary posts, degrees clockwise from North: Sun NE, Mon E, Tue SE, Wed S, Thu W,
# Fri N, Sat SW  (Rahu NW, unused)
BUR_DIR = np.array([45., 90., 135., 180., 270., 0., 225.])


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THAI TABLES
# ══════════════════════════════════════════════════════════════════════════════════════════════════
# the nine rerk classes, mansion mod 9
RERK = ["Talitto", "Mahatthano", "Joro", "Phumipalo", "Thesatri",
        "Thewi", "Petchakhat", "Racha", "Samano"]
# favourability of each rerk FOR A MARRIAGE specifically (Thewi the queen is the marriage rerk,
# Petchakhat the executioner and Samano the ascetic are the ones a wedding is moved to avoid)
RERK_SCORE = np.array([0., 2., -2., 2., 0., 3., -3., 2., -2.])
# Thai day colours as hue angles: red, yellow, pink, green, orange, light blue, purple
THAI_HUE = np.array([0., 60., 330., 120., 30., 200., 285.])


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# JAVANESE / BALINESE TABLES
# ══════════════════════════════════════════════════════════════════════════════════════════════════
URIP_SAPTA = np.array([5, 4, 3, 7, 8, 6, 9])          # Redite..Saniscara = Sunday..Saturday
URIP_PANCA = np.array([5, 9, 7, 4, 8])                # Umanis/Legi, Paing/Pahing, Pon, Wage, Kliwon
URIP_SAD = np.array([7, 6, 5, 8, 9, 3])               # Tungleh..Maulu
JODOH8 = ["Pesthi", "Pegat", "Ratu", "Jodoh", "Topo", "Tinari", "Padu", "Sujanan"]
JODOH8_SCORE = np.array([2., -3., 3., 3., 1., 2., -2., -2.])
SALAKI7 = ["Lebu Katiup Angin", "Wasesa Segara", "Tunggak Semi", "Satriya Wibawa",
           "Sumur Sinaba", "Satriya Wirang", "Bumi Kapetak"]
SALAKI7_SCORE = np.array([-3., 2., 1., 2., 1., -2., -1.])
SRI5 = ["Pati", "Sri", "Lungguh", "Dunya", "Lara"]
SRI5_SCORE = np.array([-3., 3., 2., 2., -2.])

# Galungan 2024 = Buda Kliwon Dungulan = 28 February 2024 = pawukon day 74
_PAW_ANCHOR = int(_jdn_of(2024, 2, 28))
_PAW_DAY_AT_ANCHOR = 74


def _pawukon(jdn):
    """The Pawukon position of a civil day. Returns a dict of cycle indices, all 0-based.

    day 1..210 with day 1 = Redite Paing of wuku Sinta. Intercalations for caturwara, astawara and
    sangawara are the ones forced by closure (see the module docstring): one name held for three
    days at days 71-73 for the 4- and 8-cycles, Dangu held for the first four days for the 9-cycle.
    """
    day = (np.asarray(jdn, np.int64) - _PAW_ANCHOR + (_PAW_DAY_AT_ANCHOR - 1)) % 210 + 1
    dp = np.where(day <= 71, day, np.where(day <= 73, 71, day - 2))     # caturwara / astawara
    dq = np.where(day <= 4, 1, day - 3)                                 # sangawara
    panca = day % 5
    sapta = (day - 1) % 7
    urip = URIP_PANCA[panca] + URIP_SAPTA[sapta]
    return {
        "day": day, "wuku": (day - 1) // 7, "dayinwuku": (day - 1) % 7,
        "eka": urip % 2,                                    # Luang when the urip sum is odd
        "dwi": urip % 2,                                    # Menga / Pepet — the same parity bit
        "tri": (day - 1) % 3, "catur": (dp - 1) % 4, "panca": panca,
        "sad": (day - 1) % 6, "sapta": sapta, "asta": (dp - 1) % 8,
        "sanga": (dq - 1) % 9, "dasa": urip % 10, "urip": urip,
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# FEATURE PLUMBING
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _oh(idx, k):
    """One-hot of an integer index array."""
    idx = np.asarray(idx, np.int64) % k
    Z = np.zeros((idx.shape[0], k))
    Z[np.arange(idx.shape[0]), idx] = 1.0
    return Z


def _cyc(idx, k, harmonics=(1, 2)):
    """Circular encoding of a position on a k-cycle: cos/sin at the given harmonics."""
    idx = np.asarray(idx, float)
    out = []
    for h in harmonics:
        a = 2.0 * np.pi * h * idx / k
        out += [np.cos(a), np.sin(a)]
    return np.stack(out, axis=1)


def _col(v):
    return np.asarray(v, float).reshape(-1, 1)


def _pairoh(a, b, k):
    """One-hot of the ORDERED pair (a, b) on a k-category cycle -> k*k columns."""
    return _oh(np.asarray(a, np.int64) % k * k + np.asarray(b, np.int64) % k, k * k)


def _stack(parts):
    X = np.hstack([np.asarray(p, float).reshape(p.shape[0], -1) for p in parts])
    return np.ascontiguousarray(np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0), dtype=np.float64)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# DERIVE EVERY CALENDAR POSITION ONCE
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _derive(E):
    """Per-instant calendar positions for the three real dates (both births and the wedding).

    Slots 3-5 (the two secondary progressions and the Davison midpoint) are deliberately skipped:
    they are constructed instants, not days anybody was born on or married on, and none of these
    five traditions has anything to say about them.
    """
    sun, moon = E.IDX["Sun"], E.IDX["Moon"]
    sid_lah = E.sidereal("Lahiri")
    sid_ss = E.sidereal("Suryasiddhanta")
    out = {}
    for tag, s in (("A", 0), ("B", 1), ("W", 2)):
        jd = E.JD[s]
        jdn = _jdn(jd)
        gy, gm, gd = _greg(jdn)
        doy = jdn - _jdn_of(gy, 1, 1) + 1
        d = {"jd": jd, "jdn": jdn, "gy": gy, "gm": gm, "gd": gd, "doy": doy, "dow": _dow(jdn)}

        # ── Tibetan year, on the Losar proxy and on 1 January ───────────────────────────────────
        lj = _losar_jdn(gy)
        ty = np.where(jdn >= lj, gy, gy - 1)
        d["losar_dist"] = (jdn - lj).astype(float)        # signed days from the proxy Losar
        d["losar_amb"] = ((jdn - lj) >= 0) & ((jdn - lj) < 40)   # the month the proxy may be wrong in
        for key, yr in (("t", ty), ("j", gy)):            # "t" = Losar boundary, "j" = 1 January
            c60 = (yr - 1984) % 60
            d[key + "_year"] = yr
            d[key + "_c60"] = c60
            d[key + "_animal"] = c60 % 12
            d[key + "_elem"] = (c60 % 10) // 2
            d[key + "_yang"] = 1 - (c60 % 2)
            d[key + "_rabjung"] = (yr - 1027) % 60
        # mewa: descending nine-count (the male reading) and its ascending mirror (the female one)
        d["mewa_d"] = ((1 - ty) % 9)                      # 0-based; +1 gives sme ba 1..9
        d["mewa_a"] = ((ty - 1) % 9)
        # parkha: from the animal's compass sector, and from an eight-year count (anchor unverified)
        d["parkha"] = ANIMAL_PARKHA[d["t_animal"]]
        d["parkha_d"] = (-ty) % 8
        d["parkha_a"] = ty % 8

        # ── Burmese ──────────────────────────────────────────────────────────────────────────────
        ss = sid_lah[s, sun]
        d["me"] = _mesa_year(gy, doy, ss) - 638
        d["rem7"] = d["me"] % 7
        d["bw"] = d["dow"]                                # eight-day week folded: Rahu unobtainable
        d["is_wed"] = (d["dow"] == 3).astype(float)
        d["house_p"] = (d["bw"] + d["rem7"]) % 7
        d["house_m"] = (d["bw"] - d["rem7"]) % 7

        # ── Thai ─────────────────────────────────────────────────────────────────────────────────
        d["thai_year"] = _mesa_year(gy, doy, ss)
        d["thai_animal"] = (d["thai_year"] - 1984) % 12
        d["nak"] = np.floor(sid_lah[s, moon] / (360.0 / 27.0)).astype(np.int64) % 27
        d["nak_ss"] = np.floor(sid_ss[s, moon] / (360.0 / 27.0)).astype(np.int64) % 27
        d["rerk"] = d["nak"] % 9
        d["rerk_ss"] = d["nak_ss"] % 9
        d["nak_frac"] = np.mod(sid_lah[s, moon], 360.0 / 27.0) / (360.0 / 27.0)

        # ── Pawukon ──────────────────────────────────────────────────────────────────────────────
        d.update({("p_" + k): v for k, v in _pawukon(jdn).items()})
        d["weton"] = d["p_panca"] * 7 + d["p_sapta"]       # 35 positions
        d["neptu"] = (URIP_PANCA[d["p_panca"]] + URIP_SAPTA[d["p_sapta"]]).astype(float)

        # ── lunar day, from the ephemeris (Balinese penanggal / panglong) ─────────────────────────
        elong = np.mod(E.LON[s, moon] - E.LON[s, sun], 360.0)
        d["elong"] = elong
        d["tithi"] = np.floor(elong / 12.0).astype(np.int64) % 30
        out[tag] = d
    return out


def _elrel(a, b):
    """d = (element_b - element_a) mod 5 — the Tibetan mother/son/friend/enemy relation index."""
    return (np.asarray(b, np.int64) - np.asarray(a, np.int64)) % 5


def _animal_flags(a, b):
    """The named Tibetan animal relations. Returns (dict of float arrays, distance 0..6)."""
    a = np.asarray(a, np.int64); b = np.asarray(b, np.int64)
    diff = (b - a) % 12
    dist = np.minimum(diff, 12 - diff)                 # 0..6, symmetric
    s = (a + b) % 12
    return {
        "same": (a == b).astype(float),
        "mthun_group": ((a % 4) == (b % 4)).astype(float),           # the four harmonious triads
        "mthun_not_same": (((a % 4) == (b % 4)) & (a != b)).astype(float),
        "dgra_opposite": (dist == 6).astype(float),                  # the six opposing pairs
        "srog_grogs": (s == 1).astype(float),                        # secret friends, sum 1 mod 12
        "gshed": (s == 7).astype(float),                             # destroyer pairs, sum 7 mod 12
    }, dist


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# THE BLOCKS
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def build(E):
    D = _derive(E)
    A, B, W = D["A"], D["B"], D["W"]
    out = {}

    # ── 1 ── Tibetan sexagenary year of each partner ─────────────────────────────────────────────
    parts = []
    for p in (A, B):
        parts += [_oh(p["t_animal"], 12), _oh(p["t_elem"], 5), _col(p["t_yang"]),
                  _cyc(p["t_rabjung"], 60, (1, 2, 3)), _cyc(p["t_animal"], 12, (1, 2, 3, 4)),
                  _cyc(p["t_elem"], 5, (1, 2)),
                  _oh(p["j_animal"], 12), _oh(p["j_elem"], 5),          # 1-January boundary variant
                  _col(p["losar_dist"] / 365.0), _col(p["losar_amb"].astype(float))]
    parts += [_oh(W["t_animal"], 12), _oh(W["t_elem"], 5)]               # the wedding year itself
    out["tsa: rabjung year animal x element"] = _stack(parts)

    # ── 2 ── Tibetan animal relations, the pair being the object ──────────────────────────────────
    fl, dist = _animal_flags(A["t_animal"], B["t_animal"])
    flj, distj = _animal_flags(A["j_animal"], B["j_animal"])
    diff = (B["t_animal"] - A["t_animal"]) % 12
    parts = [_pairoh(A["t_animal"], B["t_animal"], 12),                  # 144 ordered-pair columns
             _oh(diff, 12), _oh(dist, 7), _cyc(diff, 12, (1, 2, 3, 4, 6)),
             np.stack([fl[k] for k in sorted(fl)], axis=1),
             np.stack([flj[k] for k in sorted(flj)], axis=1),
             _col(dist), _col(dist == 0)]
    # the wedding-day animal against each partner's year animal — the Tibetan bag ma'i nyi ma rule
    # that a wedding day must not clash with either partner's animal (day count: JDN-11 mod 60 = 0
    # is a Wood-Mouse day, the shared East Asian day cycle)
    wd_an = (W["jdn"] - 11) % 12
    for p in (A, B):
        f2, d2 = _animal_flags(p["t_animal"], wd_an)
        parts += [np.stack([f2[k] for k in sorted(f2)], axis=1), _oh(d2, 7)]
    parts += [_oh(wd_an, 12)]
    out["tsa: animal relations (mthun/dgra/gshed)"] = _stack(parts)

    # ── 3 ── Tibetan element relations: srog and khams ────────────────────────────────────────────
    sa, sb = SROG[A["t_animal"]], SROG[B["t_animal"]]
    ea, eb = A["t_elem"], B["t_elem"]
    parts = [_oh(_elrel(sa, sb), 5), _oh(_elrel(sb, sa), 5),             # both orderings
             _oh(_elrel(ea, eb), 5), _oh(_elrel(eb, ea), 5),
             _pairoh(sa, sb, 5), _pairoh(ea, eb, 5),                     # 25 + 25
             _oh(sa, 5), _oh(sb, 5), _oh(ea, 5), _oh(eb, 5),
             _col(REL5_SCORE[_elrel(sa, sb)]), _col(REL5_SCORE[_elrel(ea, eb)]),
             _col(sa == sb), _col(ea == eb),
             _oh(_elrel(sa, eb), 5), _oh(_elrel(ea, sb), 5),             # crossed: srog vs khams
             _oh(_elrel(sa, SROG[W["t_animal"]]), 5),
             _oh(_elrel(sb, SROG[W["t_animal"]]), 5)]
    out["tsa: element relations (srog + khams)"] = _stack(parts)

    # ── 4 ── Tibetan mewa arithmetic ──────────────────────────────────────────────────────────────
    parts = []
    for ma, mb in ((A["mewa_d"], B["mewa_d"]), (A["mewa_d"], B["mewa_a"]),
                   (A["mewa_a"], B["mewa_d"]), (A["mewa_a"], B["mewa_a"])):
        tot = (ma + 1) + (mb + 1)                                        # sme ba are 1..9
        parts += [_oh(tot % 9, 9), _oh((mb - ma) % 9, 9),
                  _col(tot / 18.0), _col(ma == mb), _col(tot == 10),
                  _oh(_elrel(MEWA_EL_LOSHU[ma], MEWA_EL_LOSHU[mb]), 5),
                  _oh(_elrel(MEWA_EL_COLOUR[ma], MEWA_EL_COLOUR[mb]), 5),
                  _col(REL5_SCORE[_elrel(MEWA_EL_LOSHU[ma], MEWA_EL_LOSHU[mb])])]
    parts += [_oh(A["mewa_d"], 9), _oh(B["mewa_d"], 9), _oh(A["mewa_a"], 9), _oh(B["mewa_a"], 9),
              _pairoh(A["mewa_d"], B["mewa_d"], 9),                      # 81
              _cyc(A["mewa_d"], 9, (1, 2)), _cyc(B["mewa_d"], 9, (1, 2)),
              _oh(W["mewa_d"], 9)]
    out["tsa: mewa (sme ba dgu) arithmetic"] = _stack(parts)

    # ── 5 ── Tibetan parkha pairing ───────────────────────────────────────────────────────────────
    pa, pb = A["parkha"], B["parkha"]
    xor = PARKHA_BITS[pa] ^ PARKHA_BITS[pb]
    rel8 = XOR2REL[xor]
    parts = [_oh(pa, 8), _oh(pb, 8), _pairoh(pa, pb, 8),                 # 64
             _oh(rel8, 8), _col(REL8_SCORE[rel8]),
             _oh(_elrel(PARKHA_EL[pa], PARKHA_EL[pb]), 5),
             _oh(_elrel(PARKHA_EL[pb], PARKHA_EL[pa]), 5),
             _col(REL5_SCORE[_elrel(PARKHA_EL[pa], PARKHA_EL[pb])]),
             _col(pa == pb), _cyc((pb - pa) % 8, 8, (1, 2, 4)),
             # the eight-year count, differences only (its absolute phase is unverified)
             _oh((A["parkha_d"] - B["parkha_d"]) % 8, 8),
             _oh((A["parkha_a"] - B["parkha_a"]) % 8, 8),
             _oh((A["parkha_d"] - B["parkha_a"]) % 8, 8),
             _oh((A["parkha_a"] - B["parkha_d"]) % 8, 8),
             _oh(A["parkha_d"], 8), _oh(B["parkha_d"], 8),
             _oh(ANIMAL_PARKHA[W["t_animal"]], 8)]
    out["tsa: parkha (spar kha) pairing"] = _stack(parts)

    # ── 6 ── the Tibetan marriage reckoning itself — the tradition's own number ────────────────────
    s_srog = REL5_SCORE[_elrel(sa, sb)]
    s_khams = REL5_SCORE[_elrel(ea, eb)]
    s_animal = (2.0 * fl["mthun_not_same"] + 2.0 * fl["srog_grogs"] + 1.0 * fl["same"]
                - 2.0 * fl["dgra_opposite"] - 3.0 * fl["gshed"])
    s_parkha = REL8_SCORE[rel8] + REL5_SCORE[_elrel(PARKHA_EL[pa], PARKHA_EL[pb])]
    axes, totals = [], []
    for ma, mb in ((A["mewa_d"], B["mewa_d"]), (A["mewa_d"], B["mewa_a"]),
                   (A["mewa_a"], B["mewa_d"]), (A["mewa_a"], B["mewa_a"])):
        s_mewa = (2.0 * (ma == mb) + 1.0 * (((ma + 1) + (mb + 1)) == 10)
                  + REL5_SCORE[_elrel(MEWA_EL_LOSHU[ma], MEWA_EL_LOSHU[mb])])
        ax = np.stack([s_srog, s_khams, s_animal, s_mewa, s_parkha], axis=1)
        tot = ax.sum(axis=1)
        axes.append(ax); totals.append(tot)
    ax0 = axes[0]
    T = np.stack(totals, axis=1)
    out["tsa: marriage reckoning tally"] = _stack([
        ax0, T, _col(T.mean(axis=1)), _col(T.min(axis=1)), _col(T.max(axis=1)),
        _col((ax0 > 0).sum(axis=1)), _col((ax0 < 0).sum(axis=1)),
        _col(np.abs(ax0).sum(axis=1)), _col(T[:, 0] / 12.0),
        _oh(np.clip(np.round(T[:, 0]) + 10, 0, 21).astype(np.int64), 22),   # binned tally
        _col(T[:, 0] >= 4), _col(T[:, 0] <= -4), _col(T[:, 0] == 0),
    ])

    # ── 7 ── Burmese Mahabote: the two inputs and the natal house ─────────────────────────────────
    # The WEEKDAY ANIMAL needs no columns of its own: garuda/tiger/lion/tusked-elephant/rat/
    # guinea-pig/naga is a bijection with the weekday, and the only animal that would break it —
    # the tuskless elephant of Rahu, Wednesday afternoon — cannot occur without a birth time. The
    # weekday one-hot below IS the weekday-animal one-hot.
    parts = []
    for p in (A, B):
        parts += [_oh(p["dow"], 7), _oh(p["rem7"], 7), _oh(p["house_p"], 7), _oh(p["house_m"], 7),
                  _cyc(p["dow"], 7, (1, 2, 3)), _cyc(p["rem7"], 7, (1, 2, 3)),
                  _cyc(BUR_DIR[p["dow"]], 360.0, (1, 2)),                # the Shwedagon post
                  _col(p["is_wed"]), _col(HOUSE_SCORE[p["house_p"]]), _col(HOUSE_SCORE[p["house_m"]]),
                  _col((p["me"] % 100) / 100.0)]
    parts += [_oh(W["dow"], 7), _oh(W["rem7"], 7), _col(W["is_wed"])]
    out["bur: mahabote weekday + year remainder"] = _stack(parts)

    # ── 8 ── Burmese Mahabote: the house pairing ──────────────────────────────────────────────────
    offp = (A["house_p"] - B["house_p"]) % 7
    offm = (A["house_m"] - B["house_m"]) % 7
    parts = [_oh(offp, 7), _oh(offm, 7),                                  # anchor-free offsets
             _oh((A["dow"] - B["dow"]) % 7, 7), _oh((A["rem7"] - B["rem7"]) % 7, 7),
             _pairoh(A["dow"], B["dow"], 7),                              # 49
             _pairoh(A["house_p"], B["house_p"], 7),                      # 49
             _cyc(offp, 7, (1, 2, 3)),
             _col(offp == 0), _col(A["dow"] == B["dow"]), _col(A["rem7"] == B["rem7"]),
             # each partner's day-planet read in the other's house frame, both directions
             _oh((B["house_p"] + (A["dow"] - B["dow"])) % 7, 7),
             _oh((A["house_p"] + (B["dow"] - A["dow"])) % 7, 7),
             _col(HOUSE_SCORE[(B["house_p"] + (A["dow"] - B["dow"])) % 7]),
             _col(HOUSE_SCORE[(A["house_p"] + (B["dow"] - A["dow"])) % 7]),
             _col(HOUSE_SCORE[A["house_p"]] + HOUSE_SCORE[B["house_p"]]),
             # the wedding weekday in each partner's frame
             _oh((A["house_p"] - W["dow"]) % 7, 7), _oh((B["house_p"] - W["dow"]) % 7, 7)]
    out["bur: mahabote house pairing"] = _stack(parts)

    # ── 9 ── Thai rerk: the 27 mansions and the nine classes ──────────────────────────────────────
    parts = []
    for p in (A, B, W):
        parts += [_oh(p["nak"], 27), _oh(p["rerk"], 9), _oh(p["rerk_ss"], 9),
                  _cyc(p["nak"] + p["nak_frac"], 27, (1, 2, 3)), _col(p["nak_frac"]),
                  _col(RERK_SCORE[p["rerk"]])]
    parts += [_pairoh(A["rerk"], B["rerk"], 9),                           # 81
              _oh((B["nak"] - A["nak"]) % 27, 27), _oh((B["rerk"] - A["rerk"]) % 9, 9),
              _col(A["rerk"] == B["rerk"]), _col(A["nak"] == B["nak"]),
              _col(RERK_SCORE[A["rerk"]] + RERK_SCORE[B["rerk"]]),
              _col(RERK_SCORE[W["rerk"]] * 2.0),                          # the wedding-day rerk
              _oh((W["rerk"] - A["rerk"]) % 9, 9), _oh((W["rerk"] - B["rerk"]) % 9, 9)]
    out["thai: rerk mansions + nine classes"] = _stack(parts)

    # ── 10 ── Thai day colours, planets and animal years ──────────────────────────────────────────
    parts = []
    for p in (A, B, W):
        parts += [_oh(p["dow"], 7), _cyc(THAI_HUE[p["dow"]], 360.0, (1, 2)),
                  _oh(p["thai_animal"], 12), _cyc(p["thai_animal"], 12, (1, 2, 3))]
    parts += [_pairoh(A["dow"], B["dow"], 7),                             # 49
              _pairoh(A["thai_animal"], B["thai_animal"], 12),            # 144
              _col(A["dow"] == B["dow"]), _col(A["thai_animal"] == B["thai_animal"]),
              _col(np.cos(np.deg2rad(THAI_HUE[A["dow"]] - THAI_HUE[B["dow"]]))),
              _oh((A["thai_animal"] - B["thai_animal"]) % 12, 12),
              _col(A["thai_animal"] % 4 == B["thai_animal"] % 4)]
    out["thai: day colours + animal year"] = _stack(parts)

    # ── 11 ── Javanese/Balinese Pawukon, all concurrent cycles, per partner ───────────────────────
    cyc = [("eka", 2), ("tri", 3), ("catur", 4), ("panca", 5), ("sad", 6), ("sapta", 7),
           ("asta", 8), ("sanga", 9), ("dasa", 10)]
    parts = []
    for p in (A, B):
        for k, m in cyc:
            parts.append(_oh(p["p_" + k], m))
        parts += [_oh(p["p_wuku"], 30), _cyc(p["p_day"], 210, (1, 2, 3, 5, 6, 7)),
                  _cyc(p["p_wuku"], 30, (1, 2, 3)), _col(p["p_urip"] / 20.0),
                  _col(URIP_SAD[p["p_sad"]] / 10.0)]
    out["jav: pawukon concurrent cycles"] = _stack(parts)

    # ── 12 ── the wetonan, 35 positions, and the neptu ────────────────────────────────────────────
    parts = []
    for p in (A, B):
        parts += [_oh(p["weton"], 35), _cyc(p["weton"], 35, (1, 2, 5, 7)), _col(p["neptu"] / 20.0),
                  _oh(p["p_panca"], 5), _oh(p["p_sapta"], 7)]
    parts += [_oh((A["weton"] - B["weton"]) % 35, 35),
              _pairoh(A["p_panca"], B["p_panca"], 5),                     # 25
              _col(A["weton"] == B["weton"]), _col(A["p_panca"] == B["p_panca"]),
              _col((A["neptu"] + B["neptu"]) / 40.0), _col(np.abs(A["neptu"] - B["neptu"]) / 20.0),
              _col(A["neptu"] * B["neptu"] / 400.0),
              _cyc(A["neptu"] + B["neptu"], 8, (1, 2)), _cyc(A["neptu"] + B["neptu"], 7, (1, 2)),
              _cyc(A["neptu"] + B["neptu"], 5, (1, 2))]
    out["jav: wetonan 35 + neptu"] = _stack(parts)

    # ── 13 ── the Javanese marriage verdicts — the tradition's own numbers ────────────────────────
    tot = (A["neptu"] + B["neptu"]).astype(np.int64)
    tp = (URIP_PANCA[A["p_panca"]] + URIP_PANCA[B["p_panca"]]).astype(np.int64)
    ts = (URIP_SAPTA[A["p_sapta"]] + URIP_SAPTA[B["p_sapta"]]).astype(np.int64)
    parts = [_oh(tot % 8, 8), _oh(tot % 7, 7), _oh(tot % 5, 5),
             _oh(tot % 4, 4), _oh(tot % 3, 3), _oh(tot % 9, 9), _oh(tot % 10, 10),
             _col(JODOH8_SCORE[tot % 8]), _col(SALAKI7_SCORE[tot % 7]), _col(SRI5_SCORE[tot % 5]),
             _col(JODOH8_SCORE[tot % 8] + SALAKI7_SCORE[tot % 7] + SRI5_SCORE[tot % 5]),
             _col(tot / 40.0), _col(tp / 20.0), _col(ts / 20.0),
             _oh(tp % 8, 8), _oh(tp % 7, 7), _oh(tp % 5, 5),
             _oh(ts % 8, 8), _oh(ts % 7, 7), _oh(ts % 5, 5),
             _col(JODOH8_SCORE[tp % 8]), _col(SALAKI7_SCORE[ts % 7]),
             # the same arithmetic with the wedding day joined in (a Javanese wedding day is chosen
             # from the couple's neptu, so the three-way total is the object of the choice)
             _oh((tot + W["neptu"].astype(np.int64)) % 8, 8),
             _oh((tot + W["neptu"].astype(np.int64)) % 7, 7),
             _oh((tot + W["neptu"].astype(np.int64)) % 5, 5),
             _col(W["neptu"] / 20.0),
             _col(JODOH8_SCORE[(tot + W["neptu"].astype(np.int64)) % 8])]
    out["jav: neptu marriage verdicts"] = _stack(parts)

    # ── 14 ── Balinese padewasan of the wedding day + the lunar day ───────────────────────────────
    parts = []
    for k, m in cyc:
        parts.append(_oh(W["p_" + k], m))
    kajeng_kliwon = ((W["p_tri"] == 2) & (W["p_panca"] == 4)).astype(float)
    tumpek = ((W["p_sapta"] == 6) & (W["p_panca"] == 4)).astype(float)
    buda_kliwon = ((W["p_sapta"] == 3) & (W["p_panca"] == 4)).astype(float)
    buda_cemeng = ((W["p_sapta"] == 3) & (W["p_panca"] == 3)).astype(float)
    anggara_kasih = ((W["p_sapta"] == 2) & (W["p_panca"] == 4)).astype(float)
    parts += [_oh(W["p_wuku"], 30), _cyc(W["p_day"], 210, (1, 2, 3, 5)),
              np.stack([kajeng_kliwon, tumpek, buda_kliwon, buda_cemeng, anggara_kasih], axis=1),
              _col(W["p_wuku"] == 26),                                    # wuku Wayang
              _col(A["p_wuku"] == 26), _col(B["p_wuku"] == 26),
              _oh(W["weton"], 35), _oh(W["tithi"], 30),
              _cyc(W["elong"], 360.0, (1, 2, 3)),
              _col(E.orbkern(np.abs(E.wrap(W["elong"])), 0.0, 15.0)),      # tilem, the new moon
              _col(E.orbkern(np.abs(E.wrap(W["elong"])), 180.0, 15.0)),    # purnama, the full moon
              _col(np.abs(E.wrap(W["elong"])) / 180.0),
              _oh((W["weton"] - A["weton"]) % 35, 35),
              _oh((W["weton"] - B["weton"]) % 35, 35),
              _oh((W["p_wuku"] - A["p_wuku"]) % 30, 30),
              _col(W["p_urip"] / 20.0)]
    for p in (A, B):
        parts += [_oh(p["tithi"], 30), _cyc(p["elong"], 360.0, (1, 2))]
    out["bal: padewasan + lunar day"] = _stack(parts)

    return out


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# COULD NOT BE IMPLEMENTED — stated rather than faked
# ══════════════════════════════════════════════════════════════════════════════════════════════════
# · The PHUGPA Tibetan calendar proper (Janson's true-month arithmetic, 67 synodic months per 65
#   zodiacal months, the zla shol leap month and the zhag chad omitted day). Losar is therefore a
#   documented lunisolar proxy, right about half the time and one month early otherwise.
# · The Tibetan five personal forces beyond srog — bla (soul), lus (body), dbang thang (power) and
#   klung rta (wind horse). They come from a memorised table per animal that I could not reconstruct
#   with confidence, so only srog (which is the animal's own element, and independently attested) is
#   used. Guessing the other four would have produced four plausible-looking fabrications.
# · The BURMESE WEDNESDAY SPLIT (Rahu, the eighth day) — needs the hour of birth. Every Wednesday is
#   taken as the morning half; a "born on a Wednesday" flag marks the affected rows.
# · The Mahabote house ROTATION: which of (weekday + remainder) and (weekday - remainder) names the
#   house could not be checked against a primary source offline, so both are emitted and the pairing
#   features are built on the rotation-invariant offset.
# · The Thai LUNISOLAR month and the Thai 8/15-day lunar weeks (wan phra) — these need the Thai
#   Chulasakarat calendar's own intercalation tables, not just an astronomical new moon.
# · The Balinese SASIH (lunar month) name and the ngunaratri day-doubling: the sasih number needs the
#   Balinese year's leap-month (mala sasih) scheme. The lunar DAY (penanggal/panglong) is computed
#   astronomically from the Sun-Moon elongation instead, which is what it approximates anyway.
# · Anything houses-based in any of these traditions: no birth times, no birth places.


if __name__ == "__main__":
    import sys
    import numpy as np
    from core import load
    from evalx import quick

    fail = []

    # ── epoch and anchor assertions ───────────────────────────────────────────────────────────────
    assert int(_jdn_of(2000, 1, 1)) == 2451545, "JDN epoch"
    _g1 = lambda t: tuple(int(np.asarray(x).ravel()[0]) for x in t)
    assert _g1(_greg(np.array([2451545]))) == (2000, 1, 1), "JDN -> Gregorian"
    assert int(_dow(np.array([2451545]))[0]) == 6, "2000-01-01 must be a Saturday"

    # Tibetan sexagenary anchors: 1027 = Fire-Rabbit (head of the first rabjung), 2026 = Fire-Horse
    for yr, want in ((1027, (1, 3)), (2026, (1, 6)), (1984, (0, 0))):
        c = (yr - 1984) % 60
        assert ((c % 10) // 2, c % 12) == want, f"sexagenary year {yr}"
    # mewa: the published nine-star series 2024 = 3, 2025 = 2, 2026 = 1
    for yr, want in ((2024, 3), (2025, 2), (2026, 1)):
        assert ((1 - yr) % 9) + 1 == want, f"mewa {yr}"
    # Losar proxy: within a day of the true Losar in the years where Phugpa and Chinese agree
    for yr, want in ((2024, (2024, 2, 9)), (2026, (2026, 2, 17))):
        got = _g1(_greg(_losar_jdn(np.array([yr]))))
        assert got == want, f"losar proxy {yr}: {got}"

    # the sexagenary DAY count, used for the wedding-day animal: JDN 11 mod 60 is a Wood-Mouse day.
    # Two independent published anchors: 1 Oct 1949 = jiazi, 1 Jan 1900 = jiaxu (index 10).
    for ymd, want in (((1949, 10, 1), 0), ((1900, 1, 1), 10)):
        _j = int(np.asarray(_jdn_of(*(np.array([v]) for v in ymd))).ravel()[0])
        assert (_j - 11) % 60 == want, f"sexagenary day epoch at {ymd}"

    # Meeus checks: the new moon of 2024-02-09 22:59 UT, the December solstice of 2023 03:27 UT
    k = round((2460350.4576 - 2451550.09766) / 29.530588861)
    assert abs(float(_new_moon(np.array([k]))[0]) - 2460350.4576) < 0.01, "new moon term"
    assert abs(float(_dec_solstice(np.array([2023]))[0]) - 2460300.6438) < 0.01, "solstice term"

    # Pawukon: four independent published dates from the one Galungan anchor
    def paw1(y, m, d):
        return {k: int(np.asarray(v).ravel()[0]) for k, v in _pawukon(_jdn_of(np.array([y]),
                np.array([m]), np.array([d]))).items()}
    g = paw1(2024, 2, 28)      # Galungan: Buda Kliwon Dungulan
    assert (g["day"], g["wuku"], g["sapta"], g["panca"]) == (74, 10, 3, 4), f"Galungan {g}"
    g2 = paw1(2024, 9, 25)     # Galungan again, 210 days later
    assert g2["day"] == 74, "Galungan + 210"
    s = paw1(2024, 7, 13)      # Saraswati: Saniscara Umanis Watugunung, the last day
    assert (s["day"], s["wuku"], s["sapta"], s["panca"]) == (210, 29, 6, 0), f"Saraswati {s}"
    pg = paw1(2024, 7, 17)     # Pagerwesi: Buda Kliwon Sinta, day 4
    assert (pg["day"], pg["wuku"], pg["sapta"], pg["panca"]) == (4, 0, 3, 4), f"Pagerwesi {pg}"
    ind = paw1(1945, 8, 17)    # Indonesian independence: Jumat Legi
    assert (ind["sapta"], ind["panca"]) == (5, 0), f"Jumat Legi {ind}"
    # the intercalated cycles must close: day 210 carries the last name, day 1 the first
    assert paw1(2024, 7, 13)["catur"] == 3 and paw1(2024, 7, 13)["asta"] == 7, "4/8-cycle closure"
    assert paw1(2024, 7, 13)["sanga"] == 8, "9-cycle closure (Dadi on day 210)"
    assert paw1(2024, 7, 14)["sanga"] == 0, "9-cycle restart (Dangu on day 1)"
    # every intercalated cycle must be surjective over one pawukon
    _all = [paw1(*_g1(_greg(np.array([int(_jdn_of(2024, 2, 28)) + i])))) for i in range(210)]
    for key, m in (("catur", 4), ("asta", 8), ("sanga", 9), ("dasa", 10)):
        assert len({r[key] for r in _all}) == m, f"{key} not surjective over the pawukon"
    print("epochs + anchors OK  (JDN · rabjung 1027 · mewa 2024-26 · Losar 2024/2026 · Meeus "
          "new moon + solstice · Galungan/Saraswati/Pagerwesi/Jumat-Legi · pawukon closure)")

    E = load()
    blocks = build(E)

    # the weekday must agree between the two independent routes that compute it
    D = _derive(E)
    for tag in ("A", "B", "W"):
        assert (D[tag]["dow"] == D[tag]["p_sapta"]).all(), f"pawukon saptawara vs weekday ({tag})"
    assert not np.shares_memory(np.asarray(E.Y), np.asarray(list(blocks.values())[0]))

    print(f"\n{TRADITION}\n{len(blocks)} blocks, {E.n} couples\n")
    tot = 0
    for name, X in blocks.items():
        try:
            assert isinstance(X, np.ndarray), "not an ndarray"
            assert X.dtype == np.float64, f"dtype {X.dtype}"
            assert X.ndim == 2 and X.shape[0] == E.n, f"shape {X.shape}"
            assert np.isfinite(X).all(), "non-finite value"
            assert X.std(axis=0).max() > 0, "block is entirely constant"
            a, u = quick(E, X)
            tot += X.shape[1]
            print(f"  {name:<44} {X.shape[1]:>5} cols   acc {100*a:5.2f}%   AUC {u:.4f}")
        except AssertionError as e:
            fail.append(f"{name}: {e}")
            print(f"  {name:<44} FAILED  {e}")
    print(f"\n  {'total':<44} {tot:>5} cols")
    if fail:
        print("\nFAILURES:")
        for f in fail:
            print("  " + f)
        sys.exit(1)
    print("\nOK")
