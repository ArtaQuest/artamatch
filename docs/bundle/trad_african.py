"""
trad_african.py — African traditions: Ifá/Yorùbá, Akan day-souls, Ethiopian Baḥire Ḥasab, Coptic,
Dogon, the Swahili/Arab nautical almanac, and the southern-African heliacal star markers.

WHAT THIS MODULE IS, AND WHAT IT REFUSES TO PRETEND

Africa has no single astrology, and two of the systems asked for here are not chart-based at all. So
this file is written in three honesty classes, and every block name and docstring says which class it
is in:

  GENUINE — the tradition's own rule, computed exactly as its own sources state it, from a quantity the
    birth DATE really determines. The Akan day-soul (the weekday is exact), the Ethiopian/Coptic
    calendar (pure integer arithmetic on the Julian day number), the Baḥire Ḥasab computus (verified
    below to reproduce the Alexandrian computus for every Ethiopian year 1200–2029), the heliacal
    rising of the Pleiades and of Canopus (spherical astronomy), Sirius' elongation, the Sirius B
    orbital phase.
  MAPPED — a stated deterministic map from the birth date onto the tradition's categories, which the
    tradition itself does NOT derive from a birthday. Only Ifá is in this class, and it is labelled in
    the block name. **Ifá is cast**, with sixteen palm nuts (ikin) or the ọ̀pẹ̀lẹ̀ chain, by a babaláwo;
    the Odù that comes up is the outcome of that cast and of nothing else. There is no Ifá birth chart,
    no Ifá natal Odù, and no arithmetic on a date can produce one. What is below is a documented index
    map (day count modulo 16, twice) so the 16 principal Odù and the 256 compound Odù enter the model
    as categories with the tradition's real combinatorial structure. It is NOT a divination and no
    result from it should ever be described as one.
  PHASE ONLY — a cycle whose length is documented but whose anchor day this file could not source. The
    Yorùbá four-day week is in this class: the cycle is real, the epoch is not sourced here, so only
    the DIFFERENCE between two people's positions is interpretable and the docstring says so.

SOURCES, PER SYSTEM

  Ifá / Yorùbá.  William Bascom, *Ifa Divination: Communication between Gods and Men among the Yoruba*
    (Indiana UP, 1969) — the 16 principal Odù (odù méjì), their figures as four ranked positions of
    single or double marks, their seniority order, and the 256 compound figures (16 × 16) of which 16
    are méjì and 240 are the "children". Bernard Maupoil, *La géomancie à l'ancienne Côte des Esclaves*
    (1943) for the identical Fá figures in Dahomey. The seniority order used here is Bascom's:
    Ogbè, Òyèkú, Ìwòrì, Òdí, Ìrosùn, Òwónrín, Òbàrà, Òkànràn, Ògúndá, Òsá, Ìká, Òtúrúpọ̀n, Òtúrá,
    Ìrètè, Òsé, Òfún.  Two properties of that table are asserted in the self-test rather than trusted.
    First, the sixteen 4-mark figures are a bijection onto all sixteen binary patterns. Second, the
    seniority order pairs them: consecutive members are each other's REVERSAL, read bottom-to-top
    (Òbàrà 1222 / Òkànràn 2221, Ògúndá 1112 / Òsá 2111, Ìká 2212 / Òtúrúpọ̀n 2122, Òtúrá 1211 /
    Ìrètè 1121, Ìrosùn 1122 / Òwónrín 2211, Òsé 1212 / Òfún 2121), except for the four palindromic
    figures, whose reversal is themselves and which therefore pair by complement instead (Ogbè 1111 /
    Òyèkú 2222, Ìwòrì 2112 / Òdí 1221). Six reversal pairs plus two complement pairs account for all
    sixteen exactly, and an ordering that was merely plausible would not do that — which is the point
    of asserting it. (The first draft of this file asserted complementation throughout and was wrong;
    the assertion caught it.)
  Yorùbá calendar.  The traditional week is FOUR days (ọjọ́ Awo/Ifá, ọjọ́ Ògún, ọjọ́ Jàkúta,
    ọjọ́ Ọbàtálá); Ifá is consulted on ọjọ́ Awo, and sixteen days — four Yorùbá weeks — is the natural
    Ifá period. The anchor day of the four-day cycle is not sourced here; see PHASE ONLY above.
  Akan (Ghana).  The kra / ɔkra, the day-soul: a person is born with the soul of the day of the week
    and is named from it. J. B. Danquah, *The Akan Doctrine of God* (1944), ch. on the ɔkra and the
    day-names; J. G. Christaller, *Dictionary of the Asante and Fante Language* (1881) for the day and
    kra names. The seven day-souls: Sunday Kwasiada / Awusi; Monday Dwoada / Adwo; Tuesday Benada /
    Abena; Wednesday Wukuada / Aku; Thursday Yawoada / Yaw; Friday Fiada / Afi; Saturday Memeneda /
    Amen. Each has one male and one female name (Kwasi/Akosua, Kwadwo/Adwoa, Kwabena/Abenaa,
    Kwaku/Akua, Yaw/Yaa, Kofi/Afua, Kwame/Ama) — **sex is not an input to this model, so only the
    day-soul itself is emitted, never the sexed name.** The ntoro, the patrilineal spirit taken from
    the FATHER's day, cannot be computed: we do not have a parent's birth date. Said, not substituted.
  Akan calendar.  The adaduanan, a 42-day cycle (= 6 × 7, the six-day and seven-day cycles running
    together), nine of which make the Akan year of 378 days; the Adae ceremonies fall inside each
    cycle, Akwasidae always on a Sunday. Anchored here on the published Asante Akwasidae of
    21 January 2024, from which the 42-day cadence reproduces that whole year's series
    (3 Mar, 14 Apr, 26 May, 7 Jul, 18 Aug, 29 Sep, 10 Nov, 22 Dec 2024) and every one of them lands on
    a Sunday — which is the check that the anchor and the cycle length are both right. The position of
    Awukudae WITHIN the cycle is not sourced here, so it is not emitted; nor is the start of the
    378-day Akan year, so no year-position feature is emitted either.
  Ethiopian / Ge'ez.  The calendar: 13 months, twelve of 30 days plus Pagumē of 5 (6 in a leap year),
    leap when the Amete Mihret year ≡ 3 (mod 4), epoch 1 Meskerem 1 = 29 August 8 CE Julian =
    JDN 1724221 (Reingold & Dershowitz, *Calendrical Calculations*, the ethiopic-epoch). The Baḥire
    Ḥasab (ባሕረ ሐሳብ, "the sea of computation"), the Ethiopian Orthodox Tewahedo computus:
    Amete Alem = Amete Mihret + 5500; Medeb = AA mod 19; Wenber = Medeb − 1 (18 when Medeb = 0);
    Meṭqi = 19·Wenber mod 30; Abektē = 11·Wenber mod 30 (so Meṭqi + Abektē = 30); Rabiēt = ⌊AA/4⌋;
    the weekday of Meskerem 1 ("Tinte") = (AA + Rabiēt) mod 7; Beale Meṭqi is Meṭqi of Meskerem when
    Meṭqi > 14 and of Ṭiqimt otherwise; Mebaja Ḥamer, the date of Ṣome Nenewe, = Meṭqi plus the tewsak
    of the weekday Beale Meṭqi falls on (Sun 7, Mon 6, Tue 5, Wed 4, Thu 3, Fri 2, **Sat 8**), counted
    in Ṭir when Beale Meṭqi was in Meskerem and in Yekatit when it was in Ṭiqimt, carrying one month
    when the sum passes 30. The eleven movable feasts then follow by their tewsak from Nenewe: Nenewe
    0, Abiy Ṣome 14, Debre Zeit 41, Hosa'ina 62, Siqlet 67, Fasika 69, Rikbe Kahnat 93, Erget 108,
    Peraqlitos 118, Ṣome Ḥawaryat 119, Ṣome Diḥnet 121.
    Two of those numbers are asserted, not assumed. Saturday's tewsak of 8 (not 1) and the 30-day carry
    are both checked in the self-test by requiring the Baḥire Ḥasab's Nenewe to equal the independent
    Alexandrian computus (Fasika − 69, Fasika being Julian-calendar Easter by the Meeus algorithm) for
    **every Ethiopian year 1200–2029**; it does, all 830 of them. The closed form for the weekday of
    Meskerem 1 is checked against the Julian day number over the same span.
  Coptic.  Same day grid as the Ethiopian, exactly: 29 August 284 CE Julian = JDN 1825030, the era of
    the Martyrs, leap when the Coptic year ≡ 3 (mod 4), and the Coptic year = the Ethiopian year − 276
    with 276 ≡ 0 (mod 4). **So the Coptic month and day of any date are numerically identical to the
    Ethiopian month and day, and a separate "Coptic month one-hot" would be the same feature under a
    new name.** It is therefore not emitted. What is emitted instead is the layer that really is
    Coptic/Egyptian: distance kernels to the fixed feasts of the shared grid (Nayrouz Thout 1,
    the Cross Thout 17, Nativity Koiak 29, Ghiṭās/Timqat Ṭobi 11, the Annunciation Paremhat 29) and to
    Sham el-Nessim, the Egyptian spring festival kept on Easter Monday. The ancient
    Akhet / Peret / Shemu season triad maps onto civil months 1–4 / 5–8 / 9–12, which is the ancient
    scheme exactly — but the Egyptian civil year wandered against the Nile (that wandering IS the
    Sothic cycle), so the season labels are calendrical, not agricultural, and are emitted as such.
  Dogon.  Marcel Griaule & Germaine Dieterlen, *Le renard pâle* (1965), report a Dogon account of
    Sirius' companion po tolo with a period of about fifty years; Walter van Beek, "Dogon Restudied"
    (*Current Anthropology* 32, 1991, 139–167), found no such astronomy among the Dogon he worked with
    and attributes it to the fieldwork. Both are recorded; this module takes no position. The Sigui
    ceremony recurs every sixty years, the last beginning at Yougo Dogorou in 1967 (Dieterlen & Rouch);
    that is the anchor used. The real orbit is included beside the claim: Sirius B, P = 50.1284 yr,
    periastron T = 1994.5715 (Bond et al., *ApJ* 840:70, 2017).
  Swahili coast / Indian Ocean.  The nautical year is SOLAR, not lunar, and the monsoons are dated by
    the Sun's position through the 28 manāzil — Aḥmad ibn Mājid, *Kitāb al-Fawāʾid fī uṣūl ʿilm al-baḥr
    wa-l-qawāʿid* (c. 1490), the sailing directions used on the Swahili coast; G. R. Tibbetts, *Arab
    Navigation in the Indian Ocean before the Coming of the Portuguese* (1971), which tabulates the
    mawsim openings by manzil; A. H. J. Prins, *Sailing from Lamu* (1965) for the kaskazi (NE) and kusi
    (SW) msimu as Swahili sailors reckoned them. The sibling lunar module already emits the manāzil of
    the MOON; this module emits the manāzil of the SUN, which is the nautical use and a different
    quantity. Tibbetts' specific manzil-to-mawsim table is not held here, so the monsoon is emitted as
    the solar-year phase, not as a claimed opening date.
  Zulu / southern Africa.  isiLimela, the Pleiades, "the digging stars": their heliacal rising opens the
    agricultural year and the Zulu year is counted from it; among the Xhosa a man's years are counted in
    isiLimela. Naka, Canopus, is the corresponding marker in the Sotho–Tswana highveld, its first
    appearance announced by the chief. K. Snedegar, "Astronomical practices in Africa south of the
    Sahara", in *Astronomy Across Cultures* (Selin, ed., 2000). This is the strongest thing in the file,
    because a heliacal rising is not a mapping or a convention: it is a date, computable to the day from
    latitude and epoch.

HOW THE HELIACAL RISINGS ARE COMPUTED, AND WHAT IS APPROXIMATE IN IT

No star catalogue ships with the ephemeris files on hand: swe.fixstar2_ut resolves only Spica, Revati
and Pushya (the hard-coded ayanamsa reference stars) and fails on Sirius, Alcyone and Canopus, so
swe.heliacal_ut cannot be used for them either. Tested, and reported rather than worked around. The
positions used instead are the published ICRS J2000 places of η Tau (Alcyone) 03h47m29.08s +24°06′18.5″,
α CMa (Sirius) 06h45m08.92s −16°42′58.0″ and α Car (Canopus) 06h23m57.11s −52°41′44.4″, precessed to the
epoch of date with astropy (ICRS → FK5 of date). Proper motion is neglected: Sirius' 1.34″/yr is the
largest, 0.3° over the eight centuries this dataset spans, which moves a heliacal date by well under a
day. The rising itself is the classical criterion — the first morning of the year on which the Sun is
more than an arcus visionis below the horizon at the moment the star clears it (refraction −0.567°). The
arcus visionis is a parameter of the VISIBILITY MODEL, not of the tradition, which says only "when it is
first seen before dawn"; 11° is used, and the shift to 15° is emitted beside it as its own column. The
calibration this can be checked against: Sirius at Memphis' latitude comes out 4 August 2000, against the
accepted early-August modern date, and Canopus at 25°S comes out 22 May. The Pleiades at Zululand
latitudes come out in the first ten days of June, while ethnographic accounts put the DECLARED opening of
the year in late June or July — recognising a cluster low in the dawn takes longer than a first
theoretical sighting, and the gap is stated here rather than tuned away.

BIRTH TIME, BIRTHPLACE, AND THE HARD LIMITS

  * No hour. Every instant is 12:00 UT. Where the hour matters it is MARGINALISED over the twelve
    two-hour slots, never guessed: the Akan day runs dawn-to-dawn, so a birth in the hours before dawn
    carries the PREVIOUS day's kra, and the soft kra emitted here is the resulting distribution over the
    seven day-souls (three parts today, one part yesterday at Asante latitudes, where sunrise sits
    within minutes of 06:00 all year). The Sun's manzil and Ge'ez sign are emitted as the 12-hour soft
    distribution with its entropy, so a birth near a boundary declares itself instead of being rounded.
  * No houses, no Ascendant. Nothing here needs one. Not a single feature in this file is an
    Ascendant proxy, because none of these systems uses an Ascendant.
  * Birthplace. E.LAT_O/E.LAT_Y are used where a heliacal rising genuinely depends on latitude, always
    with a companion "known" flag and never imputed. When a coordinate is missing the local columns are
    zero and the flag says so. Independently of that, every heliacal marker is ALSO computed at the
    tradition's own observing latitude — Zululand 28.5°S for isiLimela, the Sotho–Tswana highveld 25°S
    for Naka, Memphis 29.85°N for Sothis, Bandiagara 14.35°N for the Dogon. That is not a stand-in for
    the person's birthplace: a calendar marker is defined by observation where the calendar is kept, so
    "how far into the Zulu year was this date" is a property of the date, and the person's own latitude
    is an extra, not the definition.
  * Sex, citizenship, nationality and marriage dates are not inputs and appear nowhere in this file.
    Where a rule needs sex (the Akan sexed day-name) the sexless part of the rule is emitted and the
    rest is declared missing.
  * E.Y is never read.

WHAT COULD NOT BE IMPLEMENTED, AND WHY (repeated in the report at the bottom)

  * A real Ifá cast, or any Ifá natal figure — Ifá is cast, not computed. Class MAPPED above.
  * The Akan ntoro (father's day) and the sexed day-name — parent's birth date and sex are not inputs.
  * The position of Awukudae inside the adaduanan, and the start of the 378-day Akan year — not sourced.
  * The Ge'ez zodiac as a one-hot — the twelve Ge'ez names (Ḥamal, Sawr, Ja'uzā, Saraṭān, Asad, Sunbulā,
    Mīzān, ʿAqrab, Qaws, Jady, Dalw, Ḥūt) label the same twelve tropical signs the Hellenistic and
    modern-western modules already emit. Re-emitting them would be the same feature under a new name, so
    what is emitted instead is the calendar-against-sky offset, which nothing else in the project has.
  * A separate Coptic month one-hot — provably identical to the Ethiopian one (see Coptic above).
  * Tibbetts' manzil-dated mawsim openings, and the exact Swahili Nairuzi anchor (26 August Julian vs
    Coptic Thout 1, three days apart) — not held; the phase is emitted circularly, where three days is a
    small rotation rather than a category change.
  * The Egyptian Cairo Calendar of lucky and unlucky days (pap. Cairo 86637) — a 365-entry table not
    held here. Not approximated.
  * swe.heliacal_ut and swe.fixstar2_ut for Sirius/Alcyone/Canopus — no star catalogue in the ephemeris
    directory; tested and replaced by an explicit criterion, as described above.
"""

import numpy as np
import swisseph as swe
from astropy.coordinates import SkyCoord, FK5
from astropy.time import Time
import astropy.units as u

import core  # noqa: F401  (core sets the ephemeris path on import; no other use)

TRADITION = ("African traditions (Ifá/Yorùbá Odù · Akan day-souls · Ethiopian Baḥire Ḥasab · "
             "Coptic · Dogon/Sirius · Swahili nautical manāzil · isiLimela heliacal risings)")


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  small helpers
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _onehot(idx, k):
    """(n,) integer index -> (n, k) indicator."""
    idx = np.asarray(idx, dtype=np.int64)
    out = np.zeros((idx.shape[0], k))
    out[np.arange(idx.shape[0]), np.clip(idx, 0, k - 1)] = 1.0
    return out


def _circ(x, period):
    """Circular cos/sin of x within a cycle of `period` (scalar, or per-row) -> (n, 2)."""
    r = 2.0 * np.pi * np.asarray(x, float) / np.asarray(period, float)
    return np.stack([np.cos(r), np.sin(r)], axis=-1)


def _col(x):
    x = np.asarray(x, float)
    return x.reshape(x.shape[0], -1)


def _stack(*parts):
    return np.hstack([_col(p) for p in parts]).astype(np.float64)


def _finite(X):
    return np.nan_to_num(np.asarray(X, np.float64), nan=0.0, posinf=0.0, neginf=0.0)


def _prune(X):
    """Finite-ise and shape-normalise. Column count is fixed by the code — see the note below."""
    X = _finite(X)
    # NO VARIANCE PRUNING HERE, DELIBERATELY. This used to drop columns whose standard deviation was
    # zero in the batch being built, and that made a block's WIDTH a function of the DATA rather than
    # of the code. Two consequences, both silent: a scoring batch (one couple, or ten thousand
    # candidates sharing a fixed partner) has many constant columns, so prediction handed the model a
    # narrower and differently-ordered matrix than training did; and a full run built in row chunks
    # produced chunks of different widths that could not be concatenated. Constant columns are now
    # pruned exactly once, globally, by run.collect, which records `kept_idx` in the manifest so
    # prediction can select the same columns. Width is a function of the code alone.
    return X


def _wrap180(x):
    return (np.asarray(x, float) + 180.0) % 360.0 - 180.0


# ── calendar arithmetic, all integer, all verified in the self-test ──────────────────────────────
def g2jdn(y, m, d):
    """Proleptic-Gregorian date -> Julian day number (astropy/ERFA use the proleptic Gregorian for
    ISO strings, which is the calendar core.py's julian days came from)."""
    y = np.asarray(y, np.int64); m = np.asarray(m, np.int64); d = np.asarray(d, np.int64)
    a = (14 - m) // 12; y2 = y + 4800 - a; m2 = m + 12 * a - 3
    return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045


def jdn2g(j):
    j = np.asarray(j, np.int64)
    a = j + 32044; b = (4 * a + 3) // 146097; c = a - 146097 * b // 4
    d1 = (4 * c + 3) // 1461; e = c - 1461 * d1 // 4; m = (5 * e + 2) // 153
    return (100 * b + d1 - 4800 + m // 10, m + 3 - 12 * (m // 10), e - (153 * m + 2) // 5 + 1)


def j2jdn(y, m, d):
    """JULIAN-calendar date -> Julian day number (the Alexandrian computus works in this calendar)."""
    y = np.asarray(y, np.int64); m = np.asarray(m, np.int64); d = np.asarray(d, np.int64)
    a = (14 - m) // 12; y2 = y + 4800 - a; m2 = m + 12 * a - 3
    return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - 32083


ETH_EPOCH = 1724221      # 1 Meskerem 1 Amete Mihret = 29 August 8 CE Julian
COP_EPOCH = 1825030      # 1 Thout 1 Anno Martyrum   = 29 August 284 CE Julian  (= ETH_EPOCH + 276y)


def eth_newyear(yr):
    """JDN of 1 Meskerem of Ethiopian year `yr`. Leap (Pagumē 6) when yr ≡ 3 (mod 4), so the count of
    leap years strictly before `yr` is ⌊yr/4⌋."""
    yr = np.asarray(yr, np.int64)
    return ETH_EPOCH + 365 * (yr - 1) + yr // 4


def eth_from_jdn(j):
    """JDN -> (Ethiopian year, month 1..13, day 1..30, day-of-year 0-based)."""
    j = np.asarray(j, np.int64)
    yr = (4 * (j - ETH_EPOCH) + 1463) // 1461
    doy = j - eth_newyear(yr)
    return yr, doy // 30 + 1, doy % 30 + 1, doy


def alex_easter_jdn(y):
    """Alexandrian (Julian-calendar) Easter for Gregorian-numbered year y -> JDN. Meeus, *Astronomical
    Algorithms*, ch. 8, the Julian-calendar method. Ethiopian Fasika and Coptic Easter are this day:
    verified against 2021-05-02, 2022-04-24, 2023-04-16, 2024-05-05, 2025-04-20, 2026-04-12."""
    y = np.asarray(y, np.int64)
    a, b, c = y % 4, y % 7, y % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    m = (d + e + 114) // 31
    day = (d + e + 114) % 31 + 1
    return j2jdn(y, m, day)


# the tewsak of the weekdays, indexed Monday..Sunday (JDN mod 7 == 0 is a Monday).
# Saturday is 8, not 1 — see the module docstring; asserted, not assumed.
TEWSAK_WD = np.array([6, 5, 4, 3, 2, 8, 7], np.int64)
# the eleven movable feasts, by their tewsak from Ṣome Nenewe
TEWSAK_FEAST = [("Nenewe", 0), ("Abiy Ṣome", 14), ("Debre Zeit", 41), ("Hosa'ina", 62),
                ("Siqlet", 67), ("Fasika", 69), ("Rikbe Kahnat", 93), ("Erget", 108),
                ("Peraqlitos", 118), ("Ṣome Ḥawaryat", 119), ("Ṣome Diḥnet", 121)]


def bahire_hasab(ec):
    """The Baḥire Ḥasab, computed as the Ethiopian Orthodox Tewahedo church computes it.

    Returns a dict of the tradition's OWN numbers — Amete Alem, Medeb, Wenber, Meṭqi, Abektē, Rabiēt,
    the weekday of Meskerem 1, Beale Meṭqi and its weekday, and Mebaja Ḥamer (the JDN of Ṣome Nenewe,
    from which all eleven movable feasts follow by their tewsak).
    """
    ec = np.asarray(ec, np.int64)
    AA = ec + 5500                                  # Amete Alem, the year of the world
    medeb = AA % 19                                 # position in the 19-year lunar cycle
    wenber = np.where(medeb == 0, 18, medeb - 1)
    metqi = (wenber * 19) % 30
    abekte = (wenber * 11) % 30                     # Meṭqi + Abektē = 30
    rabiet = AA // 4
    tinte = (AA + rabiet) % 7                       # weekday of 1 Meskerem, 0 = Monday
    ny = eth_newyear(ec)
    bm_month = np.where(metqi > 14, 1, 2)           # Beale Meṭqi: Meskerem when Meṭqi > 14, else Ṭiqimt
    bm_jdn = ny + (bm_month - 1) * 30 + metqi - 1
    bm_wd = bm_jdn % 7
    mh_day = metqi + TEWSAK_WD[bm_wd]
    base_month = np.where(metqi > 14, 5, 6)         # counted in Ṭir, or in Yekatit
    carry = mh_day > 30
    mh_month = base_month + carry.astype(np.int64)
    mh_dom = np.where(carry, mh_day - 30, mh_day)
    nenewe = ny + (mh_month - 1) * 30 + mh_dom - 1
    return {"AA": AA, "medeb": medeb, "wenber": wenber, "metqi": metqi, "abekte": abekte,
            "rabiet": rabiet, "tinte": tinte, "beale_metqi": bm_jdn, "beale_wd": bm_wd,
            "mebaja_month": mh_month, "mebaja_day": mh_dom, "nenewe": nenewe}


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Ifá: the 16 principal Odù, as four ranked positions of single (1) or double (2) marks
#  Bascom 1969, seniority order. Both structural properties are asserted in the self-test.
# ════════════════════════════════════════════════════════════════════════════════════════════════
ODU = [
    ("Ogbè",      (1, 1, 1, 1)),
    ("Òyèkú",     (2, 2, 2, 2)),
    ("Ìwòrì",     (2, 1, 1, 2)),
    ("Òdí",       (1, 2, 2, 1)),
    ("Ìrosùn",    (1, 1, 2, 2)),
    ("Òwónrín",   (2, 2, 1, 1)),
    ("Òbàrà",     (1, 2, 2, 2)),
    ("Òkànràn",   (2, 2, 2, 1)),
    ("Ògúndá",    (1, 1, 1, 2)),
    ("Òsá",       (2, 1, 1, 1)),
    ("Ìká",       (2, 2, 1, 2)),
    ("Òtúrúpọ̀n",  (2, 1, 2, 2)),
    ("Òtúrá",     (1, 2, 1, 1)),
    ("Ìrètè",     (1, 1, 2, 1)),
    ("Òsé",       (1, 2, 1, 2)),
    ("Òfún",      (2, 1, 2, 1)),
]
ODU_NAME = [o[0] for o in ODU]
ODU_BITS = np.array([[m - 1 for m in o[1]] for o in ODU], np.int64)     # (16, 4), 0 = single mark

# ── Akan day-souls, Sunday-first, with the qualities their own sources give them ────────────────
#    (Danquah 1944; Christaller 1881). The sexed names are listed for the record and never used.
AKAN = [
    ("Kwasiada",  "Awusi", "the universe, the leader",   "Kwasi/Akosua"),
    ("Dwoada",    "Adwo",  "peace, the calm",            "Kwadwo/Adwoa"),
    ("Benada",    "Abena", "the ocean, compassion",      "Kwabena/Abenaa"),
    ("Wukuada",   "Aku",   "Ananse the spider, fame",    "Kwaku/Akua"),
    ("Yawoada",   "Yaw",   "the earth, bravery",         "Yaw/Yaa"),
    ("Fiada",     "Afi",   "fertility, the wanderer",    "Kofi/Afua"),
    ("Memeneda",  "Amen",  "the ancient one, God",       "Kwame/Ama"),
]
AKAN_KRA = [a[1] for a in AKAN]
# the six-day cycle that crosses the seven-day one to make the 42-day adaduanan
NNANSON6 = ["Fɔ", "Nwona", "Nkyi", "Kuru", "Kwa", "Mono"]
AKWASIDAE_ANCHOR = 2460331          # JDN of 21 January 2024, a published Asante Akwasidae (a Sunday)

# ── fixed feasts of the shared Ethiopian/Coptic grid: (name, month, day) ────────────────────────
FIXED_FEASTS = [("Nayrouz / Enkutatash", 1, 1), ("Meskel / the Cross", 1, 17),
                ("Nativity (Ledet/Koiak 29)", 4, 29), ("Timqat / Ghiṭās (Ṭobi 11)", 5, 11),
                ("Annunciation (Paremhat 29)", 7, 29)]

# ── stars: published ICRS J2000 places, and the tradition's own observing latitude ──────────────
STARS = {  # name: (RA deg, Dec deg)
    "Alcyone": (56.87116, 24.10514),     # η Tau, the Pleiades — isiLimela
    "Sirius": (101.28716, -16.71612),    # α CMa — Sothis / po tolo
    "Canopus": (95.98796, -52.69566),    # α Car — Naka
}
CANON_LAT = {"Alcyone": -28.5,      # Zululand
             "Canopus": -25.0,      # the Sotho–Tswana highveld
             "Sirius": 29.85,       # Memphis
             "Sirius_dogon": 14.35}  # Bandiagara, the Dogon plateau
AV_MAIN, AV_ALT = 11.0, 15.0        # arcus visionis: a parameter of the model, not of the tradition

# ── Dogon and Sirius B ─────────────────────────────────────────────────────────────────────────
SIGUI_ANCHOR_JD = 2439492.5         # 1 January 1967, the Sigui at Yougo Dogorou
SIGUI_PERIOD = 60.0 * 365.2425      # sixty years
POTOLO_CLAIM = 50.0 * 365.2425      # Griaule & Dieterlen's "about fifty years"
SIRB_P = 50.1284 * 365.2425         # Bond et al. 2017
SIRB_T0 = 2449534.0                 # periastron 1994.5715, as a julian day (1994.5715 -> ~1994-07-27)

YR = 365.2425


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  heliacal risings — built on a (epoch, latitude) grid and interpolated per couple
# ════════════════════════════════════════════════════════════════════════════════════════════════
_EPOCHS = np.arange(1180, 2081, 20)
_GRID_LATS = np.arange(-66.0, 72.01, 2.0)


def _sun_year(y):
    """Apparent right ascension and declination of the Sun for each day of Gregorian year y."""
    j0 = int(g2jdn(y, 1, 1))
    ra = np.empty(367); dec = np.empty(367)
    for i in range(367):
        q = swe.calc_ut(float(j0 + i), swe.SUN, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)[0]
        ra[i], dec[i] = q[0], q[1]
    return j0, ra, dec


def _star_of_date(name, jd):
    """ICRS J2000 place precessed to the equinox of date -> (RA, Dec) in degrees."""
    ra, dec = STARS[name]
    c = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
    f = c.transform_to(FK5(equinox=Time(float(jd), format="jd")))
    return float(f.ra.deg), float(f.dec.deg)


def _heliacal_grid(name, lats, av):
    """Day-of-year (0-based, fractional) of the star's heliacal morning rising, on the (epoch, lat)
    grid. NaN where the star never rises at that latitude, or never clears the criterion.

    The criterion: the first morning of the year on which, at the instant the star crosses the horizon
    (refraction −0.567°), the Sun is more than `av` degrees below the horizon. The star's rising sets a
    local sidereal time, so the Sun's hour angle at that instant follows from its right ascension on
    that date without needing a clock — which is why no birth time and no longitude enter here.
    """
    lats = np.asarray(lats, float)
    out = np.full((len(_EPOCHS), len(lats)), np.nan)
    ph = np.deg2rad(lats)[None, :]
    sin_h0 = np.sin(np.deg2rad(-0.567))
    for ei, y in enumerate(_EPOCHS):
        j0, sra, sdec = _SUN_CACHE.setdefault(int(y), _sun_year(int(y)))
        ara, adec = _star_of_date(name, j0 + 182.0)
        dr = np.deg2rad(adec)
        arg = (sin_h0 - np.sin(ph) * np.sin(dr)) / (np.cos(ph) * np.cos(dr))
        rises = np.abs(arg) <= 1.0
        Hr = np.rad2deg(np.arccos(np.clip(arg, -1.0, 1.0)))          # (1, L) semi-diurnal arc
        lst = ara - Hr                                               # LST at the star's rising
        H = np.deg2rad(_wrap180(lst - sra[:, None]))                 # (D, L) the Sun's hour angle
        sd = np.deg2rad(sdec)[:, None]
        alt = np.rad2deg(np.arcsin(np.sin(ph) * np.sin(sd) + np.cos(ph) * np.cos(sd) * np.cos(H)))
        g = alt + av                                                 # > 0 means still too bright
        for L in range(len(lats)):
            if not rises[0, L]:
                continue
            gg = g[:, L]
            down = np.where((gg[:-1] > 0) & (gg[1:] <= 0))[0]
            if not len(down):
                continue
            i = down[0]
            out[ei, L] = i + gg[i] / (gg[i] - gg[i + 1])
    return out


_SUN_CACHE = {}
_GRID_CACHE = {}


def _grid(name, av, lats):
    key = (name, av, len(lats), float(lats[0]), float(lats[-1]))
    if key not in _GRID_CACHE:
        _GRID_CACHE[key] = _heliacal_grid(name, lats, av)
    return _GRID_CACHE[key]


def _rise_doy_fixed_lat(name, av, lat, years):
    """Heliacal-rising day-of-year for one fixed latitude, per birth year (linear in epoch)."""
    G = _grid(name, av, np.array([lat]))[:, 0]
    ok = np.isfinite(G)
    if not ok.any():
        return np.full(np.shape(years), np.nan)
    return np.interp(np.asarray(years, float), _EPOCHS[ok], G[ok])


def _rise_doy_var_lat(name, av, lats, years):
    """Heliacal-rising day-of-year at each couple's own latitude (bilinear over epoch × latitude)."""
    lats = np.asarray(lats, float); years = np.asarray(years, float)
    out = np.full(lats.shape, np.nan)
    good = np.isfinite(lats)
    if not good.any():
        return out
    G = _grid(name, av, _GRID_LATS)
    li = np.clip(np.searchsorted(_GRID_LATS, lats[good]) - 1, 0, len(_GRID_LATS) - 2)
    lw = (lats[good] - _GRID_LATS[li]) / (_GRID_LATS[li + 1] - _GRID_LATS[li])
    ei = np.clip(np.searchsorted(_EPOCHS, years[good]) - 1, 0, len(_EPOCHS) - 2)
    ew = (years[good] - _EPOCHS[ei]) / (_EPOCHS[ei + 1] - _EPOCHS[ei])
    v = np.zeros(li.shape)
    for de, we in ((0, 1 - ew), (1, ew)):
        for dl, wl in ((0, 1 - lw), (1, lw)):
            v = v + we * wl * G[ei + de, li + dl]
    out[good] = v
    return out


def _phase_since_rise(jdn, doy_this, doy_prev, years):
    """Fraction of the year elapsed since the last heliacal rising, and the days since it."""
    jdn = np.asarray(jdn, float)
    j_this = g2jdn(years, 1, 1).astype(float) + doy_this
    j_prev = g2jdn(years - 1, 1, 1).astype(float) + doy_prev
    last = np.where(jdn >= j_this, j_this, j_prev)
    days = jdn - last
    ok = np.isfinite(days)
    days = np.where(ok, days, 0.0)
    # a full turn is one tropical year; the residual drift of the rising itself is < 1 day/century
    return np.clip(days, 0.0, 400.0) / YR, np.where(ok, days, 0.0), ok.astype(float)


def _star_radec(name, jd):
    """Star RA/Dec per couple, interpolated over the epoch grid (linear; < 0.01° over 20 years)."""
    tab = np.array([_star_of_date(name, float(g2jdn(int(y), 7, 1))) for y in _EPOCHS])
    yrs = np.asarray(jdn2g(np.round(np.asarray(jd)).astype(np.int64))[0], float)
    return np.interp(yrs, _EPOCHS, tab[:, 0]), np.interp(yrs, _EPOCHS, tab[:, 1])


def _elongation(E, slot, name):
    """Angular separation of the Sun from the star at the birth instant — place-free, and the quantity
    that actually decides whether the star is in the dawn sky at all."""
    jd = E.JD[slot]
    sra, sdec = E.RA[slot, E.IDX["Sun"]], E.DEC[slot, E.IDX["Sun"]]
    ara, adec = _star_radec(name, jd)
    c = (np.sin(np.deg2rad(sdec)) * np.sin(np.deg2rad(adec)) +
         np.cos(np.deg2rad(sdec)) * np.cos(np.deg2rad(adec)) * np.cos(np.deg2rad(sra - ara)))
    return np.rad2deg(np.arccos(np.clip(c, -1.0, 1.0))), _wrap180(sra - ara)


# ════════════════════════════════════════════════════════════════════════════════════════════════
def build(E):
    """name -> (E.n, k) float64, finite."""
    B = {}
    n = E.n
    SO, SY, SW = E.SLOT["older"], E.SLOT["younger"], E.SLOT["wedding"]
    jd_o, jd_y, jd_w = E.JD[SO], E.JD[SY], E.JD[SW]
    JO = np.floor(jd_o + 0.5).astype(np.int64)      # the julian day NUMBER of each birth
    JY = np.floor(jd_y + 0.5).astype(np.int64)
    JW = np.floor(jd_w + 0.5).astype(np.int64)
    gyO = jdn2g(JO)[0]
    gyY = jdn2g(JY)[0]

    # ══ Ifá ═════════════════════════════════════════════════════════════════════════════════════
    # MAPPED, NOT DIVINED. Two casts per person, by the stated rule: the julian day number modulo 16
    # for the right leg, and the same count divided by 16 modulo 16 for the left. Sixteen is the base
    # of the system and sixteen days are four Yorùbá weeks; the day count is the only monotone integer
    # a bare date offers. A babaláwo's cast is not this and this is not a cast.
    o1, o2 = (JO % 16).astype(np.int64), ((JO // 16) % 16).astype(np.int64)
    y1, y2 = (JY % 16).astype(np.int64), ((JY // 16) % 16).astype(np.int64)

    B["afr: ifá odù legs, date-derived map (not a divination)"] = _prune(_stack(
        _onehot(o1, 16), _onehot(o2, 16), _onehot(y1, 16), _onehot(y2, 16),
        _circ(o1, 16), _circ(o2, 16), _circ(y1, 16), _circ(y2, 16),
        # seniority rank as a scalar: in Ifá the senior figure speaks first
        o1 / 15.0, o2 / 15.0, y1 / 15.0, y2 / 15.0))

    # the figures themselves: four ranked positions of single or double marks, so an Odù is 4 bits and
    # a compound Odù is 8. Complementarity and mark counts are what the tradition reads off the figure.
    bo = np.hstack([ODU_BITS[o1], ODU_BITS[o2]]).astype(float)      # (n, 8)
    by = np.hstack([ODU_BITS[y1], ODU_BITS[y2]]).astype(float)
    agree = (bo == by).astype(float)
    B["afr: ifá figure bits, mark counts & leg sharing"] = _prune(_stack(
        bo, by, agree, agree.sum(1), bo.sum(1), by.sum(1), np.abs(bo.sum(1) - by.sum(1)),
        (o1 == y1).astype(float), (o2 == y2).astype(float),
        ((o1 == y1) | (o2 == y2)).astype(float), ((o1 == y1) & (o2 == y2)).astype(float),
        (o1 == y2).astype(float), (o2 == y1).astype(float),          # crossed legs
        (o1 == o2).astype(float), (y1 == y2).astype(float),          # a méjì: both legs the same
        # paired figures sit next to each other in the seniority order, so (i ^ 1) is the partner —
        # the reversal of the figure, or its complement when the figure is a palindrome
        (o1 == (y1 ^ 1)).astype(float), (o2 == (y2 ^ 1)).astype(float),
        # and the bare bitwise complement, which is a different relation for 12 of the 16
        (np.abs(bo[:, :4] - (1 - by[:, :4])).sum(1) == 0).astype(float),
        (np.abs(bo[:, 4:] - (1 - by[:, 4:])).sum(1) == 0).astype(float),
        (np.abs(bo[:, :4] - by[:, 3::-1]).sum(1) == 0).astype(float),   # reversal of the right leg
        # a shared PARENT: the méjì both legs of a compound figure descend from
        (np.minimum(o1, o2) == np.minimum(y1, y2)).astype(float)))

    # the compound Odù of the union: one partner's cast as the right leg, the other's as the left.
    # 256 = 16 × 16 is the whole Ifá corpus; the méjì are the diagonal.
    comp = o1 * 16 + y1
    comp_rev = y1 * 16 + o1
    B["afr: ifá compound odù of the union (256, ordered)"] = _prune(_stack(
        _onehot(comp, 256), (comp % 17 == 0).astype(float), (comp == comp_rev).astype(float)))

    # seniority: which figure governs when two appear
    rmin, rmax = np.minimum(o1, y1), np.maximum(o1, y1)
    B["afr: ifá seniority (bascom order) & the senior odù"] = _prune(_stack(
        o1 / 15.0, y1 / 15.0, np.abs(o1 - y1) / 15.0, (o1 - y1) / 15.0,
        (o1 < y1).astype(float), (o1 == y1).astype(float),
        _onehot(rmin, 16), _onehot(rmax, 16), _onehot(np.abs(o1 - y1), 16),
        _circ(rmin, 16), _circ(rmax, 16),
        # Ogbè and Òyèkú are the two elders; the eight complement families are (rank // 2)
        (o1 <= 1).astype(float), (y1 <= 1).astype(float),
        _onehot(o1 // 2, 8), _onehot(y1 // 2, 8), (o1 // 2 == y1 // 2).astype(float)))

    # ── the Yorùbá four-day week. PHASE ONLY: the cycle is real, the anchor is not sourced here, so
    #    only the difference between two people is interpretable. The absolute one-hots are emitted
    #    anyway because to a tree they are a four-fold parity of the date, which costs nothing.
    w4o, w4y = (JO % 4).astype(np.int64), (JY % 4).astype(np.int64)
    m16o, m16y = (JO % 16).astype(np.int64), (JY % 16).astype(np.int64)
    B["afr: yorùbá four-day week & 16-day ifá month (phase only)"] = _prune(_stack(
        _onehot(w4o, 4), _onehot(w4y, 4), _onehot((w4o - w4y) % 4, 4),
        (w4o == w4y).astype(float), _circ(w4o, 4), _circ(w4y, 4),
        _onehot((m16o - m16y) % 16, 16), _circ((m16o - m16y) % 16, 16),
        ((m16o - m16y) % 16 == 0).astype(float)))

    # ══ Akan ════════════════════════════════════════════════════════════════════════════════════
    # GENUINE: the weekday is exact from the julian day number. JDN mod 7 == 0 is a Monday, so the
    # day-soul index below is Monday-first and Sunday is 6.
    wdo, wdy = (JO % 7).astype(np.int64), (JY % 7).astype(np.int64)
    kra_o = (wdo + 1) % 7           # 0 = Sunday/Awusi, to match the AKAN table order
    kra_y = (wdy + 1) % 7

    # the Akan day runs dawn-to-dawn, so a birth in the dark hours before dawn carries the PREVIOUS
    # day's kra. There is no birth hour, so this is MARGINALISED: the fraction of the day that falls
    # before sunrise is computed from latitude and the Sun's declination — at Asante latitudes
    # (6.7°N) sunrise sits within minutes of 06:00 all year, so that fraction is essentially 1/4.
    def _pre_dawn_frac(lat, dec):
        la = np.deg2rad(np.asarray(lat, float)); de = np.deg2rad(np.asarray(dec, float))
        arg = np.clip((np.sin(np.deg2rad(-0.833)) - np.sin(la) * np.sin(de)) /
                      (np.cos(la) * np.cos(de)), -1.0, 1.0)
        H0 = np.rad2deg(np.arccos(arg))             # semi-diurnal arc of the Sun, degrees
        return np.clip((12.0 - H0 / 15.0) / 24.0, 0.0, 1.0)

    decO, decY = E.DEC[SO, E.IDX["Sun"]], E.DEC[SY, E.IDX["Sun"]]
    fO_can = _pre_dawn_frac(6.7, decO)              # the tradition's own latitude, Asante
    fY_can = _pre_dawn_frac(6.7, decY)
    knO = np.isfinite(E.LAT_O).astype(float)
    knY = np.isfinite(E.LAT_Y).astype(float)
    fO_loc = np.where(knO > 0, _pre_dawn_frac(np.nan_to_num(E.LAT_O), decO), 0.0)
    fY_loc = np.where(knY > 0, _pre_dawn_frac(np.nan_to_num(E.LAT_Y), decY), 0.0)
    softO = ((1 - fO_can)[:, None] * _onehot(kra_o, 7) + fO_can[:, None] * _onehot((kra_o - 1) % 7, 7))
    softY = ((1 - fY_can)[:, None] * _onehot(kra_y, 7) + fY_can[:, None] * _onehot((kra_y - 1) % 7, 7))
    B["afr: akan kra day-soul, dawn-boundary marginalised"] = _prune(_stack(
        _onehot(kra_o, 7), _onehot(kra_y, 7), softO, softY,
        _circ(kra_o, 7), _circ(kra_y, 7),
        fO_can, fY_can, fO_loc, fY_loc, knO, knY,
        E.entropy(softO), E.entropy(softY)))

    B["afr: akan day-soul pair 7x7 (hard and soft)"] = _prune(_stack(
        _onehot(kra_o * 7 + kra_y, 49),
        (softO[:, :, None] * softY[:, None, :]).reshape(n, 49),
        _onehot((kra_o - kra_y) % 7, 7), (kra_o == kra_y).astype(float),
        _circ((kra_o - kra_y) % 7, 7)))

    # the adaduanan: 42 days = the six-day and seven-day cycles running together, position 0 =
    # Akwasidae. Nine adaduanan make the Akan year; that year's start is not sourced, so it is absent.
    ado = ((JO - AKWASIDAE_ANCHOR) % 42).astype(np.int64)
    ady = ((JY - AKWASIDAE_ANCHOR) % 42).astype(np.int64)
    B["afr: akan adaduanan 42-day cycle & akwasidae"] = _prune(_stack(
        _onehot(ado, 42), _onehot(ady, 42),
        _onehot(ado % 6, 6), _onehot(ady % 6, 6),
        _circ(ado, 42), _circ(ady, 42), ado / 41.0, ady / 41.0,
        (ado == 0).astype(float), (ady == 0).astype(float),
        (ado == ady).astype(float), _circ((ado - ady) % 42, 42),
        (ado % 6 == ady % 6).astype(float)))

    # ══ Ethiopian / Coptic ══════════════════════════════════════════════════════════════════════
    ecO, emO, edO, doyO = eth_from_jdn(JO)
    ecY, emY, edY, doyY = eth_from_jdn(JY)
    lenO = 366 - np.where(ecO % 4 == 3, 0, 1)                # 366 in a leap year (Pagumē 6), else 365
    lenY = 366 - np.where(ecY % 4 == 3, 0, 1)
    B["afr: ethiopian/coptic 13-month grid (pagumē)"] = _prune(_stack(
        _onehot(emO - 1, 13), _onehot(emY - 1, 13),
        edO / 30.0, edY / 30.0, _circ(edO - 1, 30), _circ(edY - 1, 30),
        _circ(doyO, lenO.astype(float)), _circ(doyY, lenY.astype(float)),
        doyO / 365.0, doyY / 365.0,
        (emO == 13).astype(float), (emY == 13).astype(float),          # born in Pagumē
        (ecO % 4 == 3).astype(float), (ecY % 4 == 3).astype(float),    # a leap year, Pagumē 6
        (emO == emY).astype(float), _onehot((emO - emY) % 13, 13),
        _circ(doyO - doyY, 365.0), np.abs(doyO - doyY) / 365.0,
        # the ancient season triad on the civil months, Akhet / Peret / Shemu + the epagomenal days
        _onehot(np.minimum((emO - 1) // 4, 3), 4), _onehot(np.minimum((emY - 1) // 4, 3), 4)))

    bhO, bhY = bahire_hasab(ecO), bahire_hasab(ecY)
    B["afr: ethiopian baḥire ḥasab (wenber, meṭqi, abektē, tinte)"] = _prune(_stack(
        _onehot(bhO["wenber"], 19), _onehot(bhY["wenber"], 19),
        bhO["metqi"] / 29.0, bhY["metqi"] / 29.0, bhO["abekte"] / 29.0, bhY["abekte"] / 29.0,
        _circ(bhO["metqi"], 30), _circ(bhY["metqi"], 30),
        _onehot(bhO["tinte"], 7), _onehot(bhY["tinte"], 7),
        _onehot(bhO["beale_wd"], 7), _onehot(bhY["beale_wd"], 7),
        _onehot(bhO["AA"] % 4, 4), _onehot(bhY["AA"] % 4, 4),          # the evangelist of the year
        _onehot(bhO["mebaja_month"] - 5, 3), _onehot(bhY["mebaja_month"] - 5, 3),
        bhO["mebaja_day"] / 30.0, bhY["mebaja_day"] / 30.0,
        (bhO["wenber"] == bhY["wenber"]).astype(float),
        _onehot((bhO["wenber"] - bhY["wenber"]) % 19, 19),
        _circ(bhO["wenber"] - bhY["wenber"], 19),
        (bhO["metqi"] - bhY["metqi"]) / 29.0))

    # the movable feasts by their tewsak, and the fixed ones, as signed distances and orb kernels.
    # NOTE ON SLOT 2: it is the wedding when the dataset carries one and the Davison midpoint when it
    # does not (core.py's DOB-only mode), so the slot-2 columns are named for the instant, not the rite.
    def _feasts(J, ec, nen):
        cols = []
        for _, tw in TEWSAK_FEAST:
            d = (J - (nen + tw)).astype(float)
            d = np.where(d > 200, d - 365.25, np.where(d < -200, d + 365.25, d))
            cols.append(d / 182.0)
        fas = nen + 69
        for name, mo, dy in FIXED_FEASTS:
            d = (J - (eth_newyear(ec) + (mo - 1) * 30 + dy - 1)).astype(float)
            d = np.where(d > 200, d - 365.25, np.where(d < -200, d + 365.25, d))
            cols.append(d / 182.0)
            cols.append(np.exp(-0.5 * (d / 3.0) ** 2))
            cols.append(np.exp(-0.5 * (d / 10.0) ** 2))
        dn = (J - nen).astype(float)
        cols += [np.exp(-0.5 * ((J - fas).astype(float) / 3.0) ** 2),
                 np.exp(-0.5 * ((J - fas).astype(float) / 10.0) ** 2),
                 np.exp(-0.5 * (dn / 3.0) ** 2),
                 ((dn >= 14) & (dn <= 69)).astype(float),        # inside the 55-day Abiy Ṣome
                 ((dn > 69) & (dn <= 118)).astype(float),        # the fifty days of Fasika
                 (np.abs(J - (fas + 1)) <= 0).astype(float)]     # Sham el-Nessim, Easter Monday
        return np.column_stack(cols)

    FO, FY = _feasts(JO, ecO, bhO["nenewe"]), _feasts(JY, ecY, bhY["nenewe"])
    ecW = eth_from_jdn(JW)[0]
    FW = _feasts(JW, ecW, bahire_hasab(ecW)["nenewe"])
    B["afr: ethiopian tewsak feasts & coptic fixed feasts"] = _prune(_stack(
        FO, FY, FW, np.abs(FO[:, 5] - FY[:, 5]),
        ((FO[:, -3] > 0) & (FY[:, -3] > 0)).astype(float)))

    # the Ge'ez calendar against the sky. The Ethiopian year is Julian-leap-locked, so it slides
    # against the tropical year by about a day per 128 years; the offset between the calendar month
    # and the sign the Sun actually occupies is the visible residue of that slide, and is the one
    # thing here the twelve Ge'ez sign names do not already duplicate.
    sunO, sunY = E.LON[SO, E.IDX["Sun"]], E.LON[SY, E.IDX["Sun"]]
    signO = np.floor(sunO / 30.0).astype(np.int64) % 12
    signY = np.floor(sunY / 30.0).astype(np.int64) % 12
    ny_lonO = np.array([swe.calc_ut(float(j), swe.SUN, swe.FLG_SWIEPH)[0][0]
                        for j in eth_newyear(ecO)])
    ny_lonY = np.array([swe.calc_ut(float(j), swe.SUN, swe.FLG_SWIEPH)[0][0]
                        for j in eth_newyear(ecY)])
    softsO = E.soft_bins(SO, E.IDX["Sun"], 12)
    softsY = E.soft_bins(SY, E.IDX["Sun"], 12)
    B["afr: ge'ez calendar-against-sky drift (month vs sign)"] = _prune(_stack(
        _onehot((signO - (emO - 1)) % 12, 12), _onehot((signY - (emY - 1)) % 12, 12),
        ny_lonO, ny_lonY, _circ(ny_lonO, 360.0), _circ(ny_lonY, 360.0),
        (ny_lonO - ny_lonY),
        softsO, softsY, E.entropy(softsO), E.entropy(softsY),
        ((signO - (emO - 1)) % 12 == (signY - (emY - 1)) % 12).astype(float)))

    # ══ Swahili / ibn Mājid: the SUN through the 28 manāzil ═════════════════════════════════════
    m = E.AYA_NAME.index("Fagan-Bradley")            # the manāzil are sidereal, anchored on the stars
    ayaO, ayaY = E.AYA[m, SO], E.AYA[m, SY]
    mzO = E.soft_bins(SO, E.IDX["Sun"], 28, offset=ayaO)
    mzY = E.soft_bins(SY, E.IDX["Sun"], 28, offset=ayaY)
    sidO = np.mod(sunO - ayaO, 360.0)
    sidY = np.mod(sunY - ayaY, 360.0)
    iO = (np.floor(sidO / (360.0 / 28)).astype(np.int64)) % 28
    iY = (np.floor(sidY / (360.0 / 28)).astype(np.int64)) % 28
    B["afr: swahili/ibn mājid solar manzil 28 (nautical)"] = _prune(_stack(
        mzO, mzY, E.entropy(mzO), E.entropy(mzY),
        _circ(sidO, 360.0), _circ(sidY, 360.0),
        _onehot((iO - iY) % 28, 28), (iO == iY).astype(float), _circ((iO - iY) % 28, 28),
        # the msimu: kaskazi and kusi turn about the equinoxes, so the tropical solar phase is the
        # monsoon phase. Tibbetts' manzil-dated openings are not held here — see the docstring.
        _circ(sunO, 360.0), _circ(sunY, 360.0),
        np.cos(np.deg2rad(sunO - sunY))))

    # ══ Dogon ═══════════════════════════════════════════════════════════════════════════════════
    sgO, sgY = (jd_o - SIGUI_ANCHOR_JD) / SIGUI_PERIOD, (jd_y - SIGUI_ANCHOR_JD) / SIGUI_PERIOD
    poO, poY = (jd_o - SIGUI_ANCHOR_JD) / POTOLO_CLAIM, (jd_y - SIGUI_ANCHOR_JD) / POTOLO_CLAIM
    sbO, sbY = (jd_o - SIRB_T0) / SIRB_P, (jd_y - SIRB_T0) / SIRB_P
    B["afr: dogon sigui 60y & sirius b orbital phase"] = _prune(_stack(
        _circ(sgO, 1.0), _circ(sgY, 1.0), np.mod(sgO, 1.0), np.mod(sgY, 1.0),
        _circ(poO, 1.0), _circ(poY, 1.0), np.mod(poO, 1.0), np.mod(poY, 1.0),
        _circ(sbO, 1.0), _circ(sbY, 1.0), np.mod(sbO, 1.0), np.mod(sbY, 1.0),
        _circ(sgO - sgY, 1.0), _circ(sbO - sbY, 1.0),
        np.abs(np.mod(sbO, 1.0) - np.mod(sbY, 1.0)),
        (jd_o - jd_y) / SIGUI_PERIOD))

    # ══ heliacal risings ════════════════════════════════════════════════════════════════════════
    def _rise_block(star, canon_lat, av=AV_MAIN, local=True, ndiv=12):
        cols, names = [], []
        for J, gy, lat, kn in ((JO, gyO, E.LAT_O, knO), (JY, gyY, E.LAT_Y, knY)):
            d_t = _rise_doy_fixed_lat(star, av, canon_lat, gy)
            d_p = _rise_doy_fixed_lat(star, av, canon_lat, gy - 1)
            ph, days, ok = _phase_since_rise(J, d_t, d_p, gy)
            cols += [_circ(ph, 1.0), ph, days / 365.0, ok,
                     _onehot(np.clip((ph * ndiv).astype(np.int64), 0, ndiv - 1), ndiv)]
            a_t = _rise_doy_fixed_lat(star, AV_ALT, canon_lat, gy)
            cols.append(np.nan_to_num(a_t - d_t))          # what the arcus visionis is worth, in days
            if local:
                l_t = _rise_doy_var_lat(star, av, lat, gy)
                l_p = _rise_doy_var_lat(star, av, lat, gy - 1)
                lph, ldays, lok = _phase_since_rise(J, l_t, l_p, gy)
                cols += [_circ(np.where(lok > 0, lph, 0.0), 1.0) * lok[:, None],
                         np.where(lok > 0, lph, 0.0), lok, kn,
                         np.where(lok > 0, lph, 0.0) - ph]
        return cols

    pl = _rise_block("Alcyone", CANON_LAT["Alcyone"])
    ca = _rise_block("Canopus", CANON_LAT["Canopus"])
    sepA, dlonA = _elongation(E, SO, "Alcyone")
    sepA2, dlonA2 = _elongation(E, SY, "Alcyone")
    B["afr: isilimela & naka heliacal risings, the southern year"] = _prune(_stack(
        *pl, *ca, sepA / 180.0, sepA2 / 180.0, _circ(dlonA, 360.0), _circ(dlonA2, 360.0),
        np.cos(np.deg2rad(dlonA - dlonA2))))

    si = _rise_block("Sirius", CANON_LAT["Sirius"])
    sd = _rise_block("Sirius", CANON_LAT["Sirius_dogon"], local=False, ndiv=12)
    sepS, dlonS = _elongation(E, SO, "Sirius")
    sepS2, dlonS2 = _elongation(E, SY, "Sirius")
    B["afr: sothic sirius rising & solar elongation"] = _prune(_stack(
        *si, *sd, sepS / 180.0, sepS2 / 180.0, _circ(dlonS, 360.0), _circ(dlonS2, 360.0),
        (sepS < 20).astype(float), (sepS2 < 20).astype(float),      # inside the 70-day invisibility
        np.cos(np.deg2rad(dlonS - dlonS2))))

    for k in B:
        B[k] = np.ascontiguousarray(_finite(B[k]), dtype=np.float64)
    return B


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  self-test
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _verify_scholarship():
    """Everything in this file that a source could get wrong, checked against something independent."""
    # 1. the Ifá table: a bijection onto all sixteen binary figures, paired by reversal (or, for the
    #    four palindromes, by complement) along the seniority order — see the module docstring.
    codes = [int("".join(str(b) for b in row), 2) for row in ODU_BITS]
    assert sorted(codes) == list(range(16)), "the 16 Odù figures must be all 16 binary patterns"
    npal = 0
    for i in range(0, 16, 2):
        a, b = ODU_BITS[i], ODU_BITS[i + 1]
        if (a == a[::-1]).all():
            npal += 1
            assert (a == 1 - b).all(), f"{ODU_NAME[i]}/{ODU_NAME[i+1]}: palindromes must complement"
        else:
            assert (a[::-1] == b).all(), f"{ODU_NAME[i]}/{ODU_NAME[i+1]} must be reversals"
    assert npal == 2, "exactly two of the eight pairs are palindromic (Ogbè/Òyèkú, Ìwòrì/Òdí)"
    assert sum(1 for r in ODU_BITS if (r == r[::-1]).all()) == 4, "four palindromic figures exist"
    # 2. the calendar conversions, against known dates
    assert int(g2jdn(2000, 1, 1)) == 2451545
    assert tuple(int(x) for x in jdn2g(2451545)) == (2000, 1, 1)
    assert int(j2jdn(284, 8, 29)) == COP_EPOCH and int(j2jdn(8, 8, 29)) == ETH_EPOCH
    assert int(2451545 % 7) == 5, "JDN mod 7 == 5 is a Saturday; 0 is a Monday"
    for ec, want in ((2013, (2020, 9, 11)), (2015, (2022, 9, 11)), (2016, (2023, 9, 12)),
                     (2017, (2024, 9, 11))):
        got = tuple(int(x) for x in jdn2g(eth_newyear(ec)))
        assert got == want, f"Meskerem 1 {ec} EC: got {got}, expected {want}"
    ecs = np.arange(1, 2200)
    y, m, d, _ = eth_from_jdn(eth_newyear(ecs))
    assert (y == ecs).all() and (m == 1).all() and (d == 1).all(), "eth calendar must round-trip"
    js = np.arange(ETH_EPOCH, ETH_EPOCH + 700000, 331)
    y, m, d, _ = eth_from_jdn(js)
    assert (eth_newyear(y) + (m - 1) * 30 + d - 1 == js).all(), "eth month/day must invert"
    # 3. Fasika = Julian-calendar Easter, against six published Ethiopian Easters
    for gy, want in ((2021, (2021, 5, 2)), (2022, (2022, 4, 24)), (2023, (2023, 4, 16)),
                     (2024, (2024, 5, 5)), (2025, (2025, 4, 20)), (2026, (2026, 4, 12))):
        got = tuple(int(x) for x in jdn2g(alex_easter_jdn(gy)))
        assert got == want, f"Fasika {gy}: got {got}, expected {want}"
    # 4. THE BIG ONE: the Baḥire Ḥasab's own arithmetic must reproduce the Alexandrian computus for
    #    every Ethiopian year in range. This is what validates Saturday's tewsak of 8 and the 30-day
    #    carry, neither of which is obvious and both of which are wrong in the naive reading.
    ec = np.arange(1200, 2030)
    bh = bahire_hasab(ec)
    assert (bh["nenewe"] == alex_easter_jdn(ec + 8) - 69).all(), "Baḥire Ḥasab must give Nenewe"
    assert ((bh["metqi"] + bh["abekte"] == 30) | (bh["wenber"] == 0)).all(), "Meṭqi + Abektē = 30"
    assert (bh["tinte"] == eth_newyear(ec) % 7).all(), "(AA + Rabiēt) mod 7 must be Meskerem 1's day"
    ey, em, ed, _ = eth_from_jdn(bh["nenewe"])
    assert set(np.unique(em).tolist()) <= {5, 6, 7}, "Nenewe falls in Ṭir, Yekatit or Megabit"
    # 5. the Akwasidae anchor: nine published 2024 dates, 42 days apart, every one a Sunday
    for k, want in enumerate([(2024, 1, 21), (2024, 3, 3), (2024, 4, 14), (2024, 5, 26),
                              (2024, 7, 7), (2024, 8, 18), (2024, 9, 29), (2024, 11, 10),
                              (2024, 12, 22)]):
        j = AKWASIDAE_ANCHOR + 42 * k
        assert tuple(int(x) for x in jdn2g(j)) == want and j % 7 == 6, f"Akwasidae {k}"
    # 6. the heliacal criterion, against dates that are independently known
    d = _rise_doy_fixed_lat("Sirius", AV_MAIN, 29.85, [2000.0])[0]
    got = tuple(int(x) for x in jdn2g(int(g2jdn(2000, 1, 1) + round(d))))
    assert got[1] == 8 and got[2] <= 8, f"Sirius at Memphis, 2000: got {got}, expected early August"
    d = _rise_doy_fixed_lat("Canopus", AV_MAIN, -25.0, [2000.0])[0]
    got = tuple(int(x) for x in jdn2g(int(g2jdn(2000, 1, 1) + round(d))))
    assert got[1] == 5, f"Canopus at 25S, 2000: got {got}, expected May"
    d = _rise_doy_fixed_lat("Alcyone", AV_MAIN, -28.5, [2000.0])[0]
    got = tuple(int(x) for x in jdn2g(int(g2jdn(2000, 1, 1) + round(d))))
    assert got[1] == 6, f"the Pleiades at 28.5S, 2000: got {got}, expected June"
    print("scholarship checks: ifá figures, 4 calendars, 6 Fasikas, 830 Baḥire Ḥasab years,")
    print("                    9 Akwasidae, 3 heliacal risings — all pass")


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick

    _verify_scholarship()
    E = load()
    print(f"\n{TRADITION}\ncouples {E.n:,}   birthplaces known: older "
          f"{np.isfinite(E.LAT_O).mean():.1%}, younger {np.isfinite(E.LAT_Y).mean():.1%}\n")
    B = build(E)
    bad = 0
    rows = []
    for name, X in B.items():
        try:
            assert X.shape[0] == E.n, f"{name}: rows {X.shape[0]} != {E.n}"
            assert X.ndim == 2 and X.shape[1] > 0, f"{name}: shape {X.shape}"
            assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
            assert np.isfinite(X).all(), f"{name}: non-finite values"
            assert X.std(axis=0).max() > 1e-12, f"{name}: all-constant block"
        except AssertionError as e:
            print("FAIL", e)
            bad += 1
            continue
        acc, auc = quick(E, X)
        rows.append((name, X.shape[1], acc, auc))
        print(f"  {name:<58} {X.shape[1]:>4} cols   acc {100*acc:5.2f}%   AUC {auc:.4f}")
    tot = sum(r[1] for r in rows)
    print(f"\n{len(rows)} blocks, {tot} columns total")
    if bad:
        print(f"{bad} BLOCK(S) FAILED")
        sys.exit(1)
    print("OK")
