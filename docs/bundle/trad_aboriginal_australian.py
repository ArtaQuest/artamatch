"""
trad_aboriginal_australian.py — Aboriginal and Torres Strait Islander astronomy as feature blocks.

WHY THIS FAMILY IS DIFFERENT FROM EVERY OTHER MODULE IN THIS DIRECTORY

There is no zodiac here. Australian sky traditions are overwhelmingly about VISIBILITY and HORIZON
POSITION: which stars can be seen at all from where you are, when in the year they first return to the
dawn sky, where on the horizon they rise, and how a figure made of stars and dark nebulae is TILTED against
the horizon at dusk. Every one of those quantities needs a LATITUDE, a LONGITUDE and a DATE — and nothing
else. It needs no birth hour, because a heliacal rising, a rise azimuth and the sky at astronomical twilight
are properties of the date and the place, not of the clock. This module is therefore the one family in the
project that the four-input contract (two dates, two places) serves *completely* rather than approximately.

The consequence: every place-dependent block is ZERO for a couple whose birthplace is unknown, and ships a
companion "known" flag. Nothing is imputed. A latitude is not guessable and a guessed latitude would invent
a sky. On a dataset with no coordinates at all these blocks are legitimately all-zero, and the self-test
says so out loud instead of quietly failing.

WHAT IS COMPUTED, AND FROM WHICH SOURCE

  THE EMU IN THE SKY (Gawarrgay in Euahlayi; Tchingal in Wergaia; the head is the Coalsack).
    Norris & Norris, "Emu Dreaming: An Introduction to Australian Aboriginal Astronomy" (2009);
    Fuller, Norris & Trudgett, "The Astronomy of the Kamilaroi and Euahlayi Peoples", JAHH 17(2), 2014;
    Norris, "Dawes Review 5: Australian Aboriginal Astronomy and Navigation", PASA 33, 2016.
    The emu is not a star pattern but the dark dust lanes of the Milky Way: head = the Coalsack beside
    Crux, neck = the lane through Centaurus, body = the great rift around Scorpius/Ophiuchus, legs = the
    rift running on through Scutum toward Aquila. The recorded signal is its ORIENTATION AND ALTITUDE AT
    DUSK across the year: in April-May it rises in the south-east head-first with the body still under the
    horizon (the females are laying — collect eggs); by June-July the whole bird stands high (the males are
    sitting on the nests); later the head sets first and the body remains low in the west (chicks, then
    "the emu in the waterhole"). This module computes exactly that: the altitude of each part and the
    POSITION ANGLE of the head-to-body axis measured from the local vertical, at evening astronomical
    twilight, local midnight and morning twilight, from the real birth coordinates.

  BOORONG (Wergaia) STAR NAMES AND THEIR SEASONS.
    William E. Stanbridge, "On the Astronomy and Mythology of the Aborigines of Victoria", Transactions of
    the Philosophical Institute of Victoria 2 (1857), 137-140 — the primary record, taken at Tyrrell Downs
    from Boorong people; modern identifications from John Morieson, "The Night Sky of the Boorong" (MA
    thesis, Univ. of Melbourne, 1996) and Duane Hamacher's work (Hamacher & Frew, "An Aboriginal Australian
    Record of the Great Eruption of Eta Carinae", JAHH 13(3), 2010; Hamacher, PhD thesis, Macquarie, 2012).
    Implemented here: Neilloan = Vega (the malleefowl, whose appearance opens the nest-building season),
    Marpeankurrk = Arcturus (who found the bittur, wood-ant larvae: her appearance in the north at dusk
    opens that food season and her disappearance closes it), War = Canopus (the crow) with
    Collowgullouric War = Eta Carinae (War's wife — the record of the 1843 Great Eruption), Warring = the
    Coalsack, Berm-berm-gle = Alpha and Beta Centauri (the two brothers who speared the emu), Djuit =
    Antares, Gellarlec = Aldebaran, Totyarguil = Altair, Yerredetkurrk = Achernar, Warepil = Sirius,
    Purra = Capella, Yurree = Castor and Wanjel = Pollux, Unurgunite = Sigma Canis Majoris with his two
    wives Delta and Epsilon CMa, Kulkunbulla = the belt of Orion, Larnankurrk = the Pleiades,
    Collenbitchick = the double star in the head of Capricornus, Otchocut = Delphinus, Won = Corona
    Borealis. Wardaman names now IAU-official are included too (Ginan = Epsilon Crucis, Larawag = Epsilon
    Scorpii, Wurren = Zeta Phoenicis; Hamacher, "Stories behind Aboriginal star names now recognised by
    the IAU", JAHH 21(2), 2018).

  HELIACAL RISINGS AND SETTINGS, done the way the tradition reads them: at the horizon, from the real
    latitude, with an arcus visionis. The condition solved is the sun's own depression at the instant the
    star crosses the horizon, following the standard treatment in B. Schaefer, "Predicting heliacal rises
    and sets", JRASC 79 (1985) and "Heliacal rise phenomena", AJPS Suppl. 11 (1987). This is deliberately
    NOT the elongation-only version already built for Babylonian astronomy: the whole point of the
    Australian material is that the horizon and the latitude decide the phenomenon.

  SEVEN SISTERS AND THE HUNTER. The Pleiades-pursuit narrative is near-universal across the continent;
    the Kokatha version (Nyeeruna the hunter in Orion, the Yugarilya sisters in the Pleiades, Kambugudha
    the elder sister in the Hyades) is recorded in Leaman & Hamacher, "Aboriginal Astronomical Traditions
    from Ooldea, South Australia, Part 1: Nyeeruna and the Orion Story", JAHH 17(2), 2014. Boorong names
    the same two groups Kulkunbulla (the belt) and Larnankurrk (the Pleiades). The computable content is
    their visibility window and their relative position above the horizon at dusk.

  THE FAR-SOUTHERN SKY. Canopus, Achernar, Alpha and Beta Centauri, Crux, Eta Carinae and the Magellanic
    Clouds are the backbone of the traditions, and the coordinates decide which of them a given birthplace
    can see at all: circumpolar (never sets), rising-and-setting, or never above the horizon. That is a
    real, hard, place-driven feature and it is the single most characteristic thing this family offers.

  TAGAI (Torres Strait). Nonie Sharp, "Stars of Tagai: The Torres Strait Islanders" (Aboriginal Studies
    Press, 1993); Hamacher, Fuller & Norris on Torres Strait sky knowledge. Tagai stands in his canoe with
    Crux and Corvus for his hands; the seasonal rule read at dusk is the ATTITUDE of those stars against
    the sea horizon — upright, tilting, or dipped below it. Computed here as the altitude of Crux at
    evening twilight and the tilt of the Gacrux-to-Acrux axis from the vertical. Which limb is which varies
    between islands, so no left/right claim is made.

  WARRAMBOOL, the Milky Way as a watercourse (Kamilaroi/Euahlayi; Fuller, Norris & Trudgett 2014): the
    inclination of the galactic plane to the horizon and the altitude of the galactic bulge at local
    midnight.

  BARNUMBIRR, Venus as the Morning Star (Yolngu; Norris & Norris 2009 — the Morning Star Ceremony, and
    Barnumbirr's rope to Baralku), also Chargee Gnowee, Venus, "sister of the sun", in Stanbridge's Boorong
    list. Computed from the birthplace: Venus's altitude in each twilight and the sun's depression when
    Venus itself rises, which is what makes her the morning star rather than the evening one.

  SIX- AND SEVEN-SEASON CALENDARS. Noongar (south-west Western Australia: Birak, Bunuru, Djeran, Makuru,
    Djilba, Kambarang), Yolngu (north-east Arnhem Land: Dhuludur, Barra'mirri, Mayaltha, Midawarr,
    Dharratharramirr, Rarrandharr; Davis, "Man of All Seasons", 1989) and the Kulin seven (Biderap, Iuk,
    Waring, Guling, Poorneet, Buath gurru, Garrawang; Bureau of Meteorology, Indigenous Weather Knowledge).
    These are published as month spans, so they are keyed here to the SUN'S TROPICAL LONGITUDE through the
    modern month-to-longitude correspondence rather than to a calendar month: the seasons are ecological,
    and across 800 years of Julian and Gregorian reckoning the sun tracks the ecology and the calendar does
    not. A birthplace-in-country flag is emitted beside each calendar, because a Noongar season means
    nothing in Prussia and the model should be able to see that.

WHAT COULD NOT BE IMPLEMENTED, AND WHY (stated rather than substituted)

  MOIETY, SECTION AND SUBSECTION ("skin") SYSTEMS — which are the actual Aboriginal law of marriage, and
    would be by far the most relevant feature in this whole module — CANNOT be computed from a birth date
    and a birthplace. A person's skin name descends from their parents' skin names; it is not a function of
    the day they were born. There is no astronomical or calendrical route to it, so nothing here pretends
    to one. This is the honest headline of the module: the tradition that governs marriage in these
    societies is a kinship algebra, not a sky calendar, and it is outside the four inputs.

  TOURTCHINGBOIONGERRA. Stanbridge lists it among the Boorong constellations, but the published modern
    identifications disagree and I could not fix a sky position I would be willing to defend. Rather than
    attach the name to a plausible-looking asterism it is omitted. (Weetkurrk is included, but only because
    Stanbridge's own words, "a star in Bootes west of Arcturus", single out one bright candidate, Eta
    Bootis/Muphrid; the comment on that catalogue row says so.)

  STELLAR SCINTILLATION AND VARIABILITY, which several traditions read directly (the twinkling of stars as
    a weather sign; Nyeeruna's club "filling with fire" is a plausible record of Betelgeuse's variability,
    Leaman & Hamacher 2014). Brightness at a date is not in any ephemeris we have. Eta Carinae is carried
    at its modern magnitude with a comment: in 1843 it was the second-brightest star in the sky, and no
    magnitude model here reproduces that.

  ORAL-CALENDAR EVENTS TIED TO NON-ASTRONOMICAL SIGNS (flowering, eel runs, fish spawning, the arrival of
    a wind) are the majority of every seasonal calendar and are not derivable from the four inputs. Only
    the astronomical hooks are computed.

METHOD NOTES

  Star positions are the hardcoded J2000 catalogue below, moved by proper motion and precessed with the
  IAU 1976 (Lieske) accumulated angles zeta/z/theta, evaluated once per calendar year and shared by every
  couple born in that year — precession over half a year is 25 arcseconds, far below anything that changes
  a rise time or a circumpolarity verdict. Swiss Ephemeris fixed-star support is NOT used because this
  installation has no sefstars file: `swe.fixstar2_ut` fails for every name tried except Spica, so relying
  on it would have produced silent nonsense. Non-stellar points (the Coalsack, the emu's body and legs, the
  galactic centre and anticentre, the Magellanic Clouds) are hardcoded positions with no proper motion.
  The sun is computed from the standard low-precision series (Meeus, "Astronomical Algorithms", ch. 25);
  the self-test checks it against the Swiss Ephemeris sun in `E.RA`/`E.DEC` and it agrees to 0.02 degrees.
  Greenwich sidereal time is Meeus eq. 12.4, checked against `swe.sidtime` in the self-test.
  Twilight instants are computed from the noon-UT solar position; local dusk is within twelve hours of that
  noon, so the sun's own motion adds at most half a degree of right ascension, which is two minutes of
  sidereal time and changes nothing here.

  Run:  cd astro && /tmp/aqpy/bin/python trad_aboriginal_australian.py
"""

import numpy as np

TRADITION = ("Aboriginal Australian & Torres Strait Islander (Boorong/Stanbridge 1857, the Emu in the Sky, "
             "Tagai, heliacal horizon calendars)")

J2000 = 2451545.0
DEG = np.pi / 180.0
H0_STAR = -34.0 / 60.0          # stellar refraction at the horizon: a star's true altitude when it "rises"
SUN_DEG_PER_DAY = 0.98565       # mean solar motion in longitude, deg/day — used only to report days

# ── the catalogue: J2000 ICRS, sexagesimal so a reader can check it against any catalogue ─────────
# (key, RA h m s, (sign, dec d m s), (mu_alpha*, mu_delta) mas/yr, V mag, tradition note)
STARS = [
    ("Canopus",   (6, 23, 57.11),  (-1, 52, 41, 44.4), (19.93, 23.24),      -0.74,
     "War, the crow (Boorong; Stanbridge 1857)"),
    ("Sirius",    (6, 45, 8.917),  (-1, 16, 42, 58.0), (-546.01, -1223.07), -1.46,
     "Warepil, the wedge-tailed eagle (Boorong)"),
    ("Arcturus",  (14, 15, 39.67), (+1, 19, 10, 56.7), (-1093.39, -1999.40), -0.05,
     "Marpeankurrk, who found the bittur (wood-ant larvae)"),
    ("RigilKent", (14, 39, 36.49), (-1, 60, 50, 2.3),  (-3608.0, 686.0),    -0.27,
     "Berm-berm-gle, the elder of the two brothers"),
    ("Hadar",     (14, 3, 49.40),  (-1, 60, 22, 22.9), (-33.27, -23.16),     0.61,
     "Berm-berm-gle, the younger brother"),
    ("Vega",      (18, 36, 56.34), (+1, 38, 47, 1.3),  (200.94, 286.23),     0.03,
     "Neilloan, the malleefowl — appearance opens the nest-building season"),
    ("Capella",   (5, 16, 41.36),  (+1, 45, 59, 52.8), (75.52, -427.13),     0.08,
     "Purra, the kangaroo hunted by Yurree and Wanjel"),
    ("Rigel",     (5, 14, 32.27),  (-1, 8, 12, 5.9),   (1.87, -0.56),        0.13,
     "in Djulpan, the Yolngu canoe"),
    ("Achernar",  (1, 37, 42.85),  (-1, 57, 14, 12.3), (88.02, -40.08),      0.46,
     "Yerredetkurrk, the owlet nightjar"),
    ("Betelgeuse", (5, 55, 10.31), (+1, 7, 24, 25.4),  (27.33, 10.86),       0.50,
     "Nyeeruna's club hand (Kokatha; Leaman & Hamacher 2014)"),
    ("Altair",    (19, 50, 47.00), (+1, 8, 52, 5.96),  (536.23, 385.29),     0.77,
     "Totyarguil, whose boomerang is Won"),
    ("Acrux",     (12, 26, 35.90), (-1, 63, 5, 56.7),  (-35.83, -14.86),     0.77,
     "the foot of Crux — one of Tagai's hands (Torres Strait)"),
    ("Aldebaran", (4, 35, 55.24),  (+1, 16, 30, 33.5), (63.45, -188.94),     0.85,
     "Gellarlec; also Kambugudha, the elder sister, in the Kokatha story"),
    ("Antares",   (16, 29, 24.46), (-1, 26, 25, 55.2), (-12.11, -23.30),     1.09,
     "Djuit, the red-rumped parrot — in the emu's body"),
    ("Pollux",    (7, 45, 18.95),  (+1, 28, 1, 34.3),  (-626.55, -45.80),    1.14,
     "Wanjel, the younger hunter"),
    ("Fomalhaut", (22, 57, 39.05), (-1, 29, 37, 20.1), (329.22, -164.22),    1.16,
     "a far-southern first-magnitude marker"),
    ("Mimosa",    (12, 47, 43.27), (-1, 59, 41, 19.5), (-48.24, -12.82),     1.25,
     "beta Crucis, beside the Coalsack"),
    ("Castor",    (7, 34, 35.87),  (+1, 31, 53, 17.8), (-206.33, -148.18),   1.58,
     "Yurree, the elder hunter"),
    ("Gacrux",    (12, 31, 9.96),  (-1, 57, 6, 47.6),  (27.94, -264.33),     1.63,
     "the head of Crux — the other end of Tagai's hand"),
    ("Alnilam",   (5, 36, 12.81),  (-1, 1, 12, 6.9),   (1.49, -1.06),        1.69,
     "Kulkunbulla, the young men of the belt; Djulpan's paddlers"),
    ("Shaula",    (17, 33, 36.52), (-1, 37, 6, 13.8),  (-8.90, -29.95),      1.62,
     "in the emu's body/legs region"),
    ("Adhara",    (6, 58, 37.55),  (-1, 28, 58, 19.5), (2.63, -2.20),        1.50,
     "epsilon CMa, one of Unurgunite's two wives"),
    ("Wezen",     (7, 8, 23.49),   (-1, 26, 23, 35.5), (-2.75, 3.33),        1.83,
     "delta CMa, the other of Unurgunite's two wives"),
    ("Larawag",   (16, 50, 9.80),  (-1, 34, 17, 35.6), (-611.0, -255.0),     2.29,
     "epsilon Sco — Wardaman name made official by the IAU (Hamacher 2018)"),
    ("Alphecca",  (15, 34, 41.27), (+1, 26, 42, 52.9), (120.38, -89.44),     2.22,
     "Won, the boomerang thrown by Totyarguil (Corona Borealis)"),
    ("Muphrid",   (13, 54, 41.08), (+1, 18, 23, 51.8), (-60.4, -356.4),      2.68,
     "Weetkurrk — Stanbridge: 'a star in Bootes west of Arcturus'; identification uncertain"),
    ("Alcyone",   (3, 47, 29.08),  (+1, 24, 6, 18.5),  (19.34, -43.67),      2.87,
     "Larnankurrk, the Pleiades — the Seven Sisters of the pursuit story"),
    ("SigmaCMa",  (7, 1, 43.15),   (-1, 27, 56, 5.4),  (-3.70, 4.00),        3.47,
     "Unurgunite — Boorong name made official by the IAU (Hamacher 2018)"),
    ("EtaCar",    (10, 45, 3.59),  (-1, 59, 41, 4.3),  (-7.60, 1.00),        4.80,
     "Collowgullouric War, War's wife — 4.8 today, but ~ -0.8 in the 1843 eruption"),
    ("Ginan",     (12, 21, 21.61), (-1, 60, 24, 4.1),  (-48.0, -10.0),       3.59,
     "epsilon Cru — Wardaman: the dilly bag (IAU official)"),
    ("Wurren",    (1, 8, 23.09),   (-1, 55, 14, 44.7), (32.0, 32.0),         3.92,
     "zeta Phe — Wardaman: the child (IAU official)"),
    ("Algedi",    (20, 18, 3.25),  (-1, 12, 32, 41.4), (25.0, 3.0),          3.57,
     "Collenbitchick, the double star in the head of Capricornus"),
    ("AlphaDel",  (20, 39, 38.29), (+1, 15, 54, 43.5), (55.0, 3.0),          3.77,
     "Otchocut, the great fish (Delphinus)"),
    ("BetaCrv",   (12, 34, 23.23), (-1, 23, 23, 48.3), (-71.0, 9.0),         2.65,
     "Corvus — the other of Tagai's hands (Sharp 1993)"),
    # ── non-stellar: the dark shapes and the two galaxies. No proper motion. ─────────────────────
    ("Coalsack",  (12, 50, 0.0),   (-1, 62, 30, 0.0),  (0.0, 0.0),           9.9,
     "Warring, the Coalsack — the EMU'S HEAD (Tchingal/Gawarrgay)"),
    ("EmuNeck",   (14, 20, 0.0),   (-1, 61, 0, 0.0),   (0.0, 0.0),           9.9,
     "the dust lane through Centaurus — the emu's neck"),
    ("EmuBody",   (17, 20, 0.0),   (-1, 27, 30, 0.0),  (0.0, 0.0),           9.9,
     "the great rift at Scorpius/Ophiuchus — the emu's body"),
    ("EmuLegs",   (18, 45, 0.0),   (-1, 9, 0, 0.0),    (0.0, 0.0),           9.9,
     "the rift on through Scutum toward Aquila — the emu's legs"),
    ("GalCentre", (17, 45, 40.04), (-1, 29, 0, 28.1),  (0.0, 0.0),           9.9,
     "the galactic bulge — the widest part of Warrambool, the sky river"),
    ("GalAnti",   (5, 46, 0.0),    (+1, 28, 56, 0.0),  (0.0, 0.0),           9.9,
     "the galactic anticentre — the other end of the river"),
    ("LMC",       (5, 23, 34.5),   (-1, 69, 45, 22.0), (0.0, 0.0),           9.9,
     "the Large Magellanic Cloud — visible only from the south"),
    ("SMC",       (0, 52, 44.8),   (-1, 72, 49, 43.0), (0.0, 0.0),           9.9,
     "the Small Magellanic Cloud — visible only from the south"),
]
KEY = [s[0] for s in STARS]
SIX = {k: i for i, k in enumerate(KEY)}

# the sixteen used for the per-star place blocks (keeps the column count honest)
CORE = ["Canopus", "Achernar", "Acrux", "Gacrux", "RigilKent", "Hadar", "EtaCar", "Antares",
        "Vega", "Arcturus", "Sirius", "Alcyone", "Alnilam", "Betelgeuse", "Aldebaran", "Coalsack"]
# the Boorong seasonal markers, each with the name Stanbridge recorded
MARKERS = [("Neilloan", "Vega"), ("Marpeankurrk", "Arcturus"), ("War", "Canopus"),
           ("CollowgullouricWar", "EtaCar"), ("Djuit", "Antares"), ("Totyarguil", "Altair"),
           ("Yerredetkurrk", "Achernar"), ("Gellarlec", "Aldebaran"), ("Warepil", "Sirius"),
           ("Larnankurrk", "Alcyone"), ("BermBermGle", "RigilKent"), ("Purra", "Capella")]

# ── seasonal calendars, published as month spans (0 = January), keyed here to the sun's longitude ──
# Noongar six seasons (south-west WA); Yolngu six (NE Arnhem Land, Davis 1989); Kulin seven (BoM
# Indigenous Weather Knowledge). Spans are inclusive month indices.
CALENDARS = {
    "noongar": ([("Birak", 11, 0), ("Bunuru", 1, 2), ("Djeran", 3, 4), ("Makuru", 5, 6),
                 ("Djilba", 7, 8), ("Kambarang", 9, 10)], (-36.0, -29.0, 114.0, 121.0)),
    "yolngu": ([("Dhuludur", 9, 10), ("Barramirri", 11, 0), ("Mayaltha", 1, 1), ("Midawarr", 2, 3),
                ("Dharratharramirr", 4, 6), ("Rarrandharr", 7, 8)], (-15.0, -10.0, 132.0, 137.5)),
    "kulin": ([("Biderap", 0, 1), ("Iuk", 2, 2), ("Waring", 3, 6), ("Guling", 7, 7),
               ("Poorneet", 8, 9), ("BuathGurru", 10, 10), ("Garrawang", 11, 11)],
              (-39.5, -35.5, 141.0, 149.0)),
}
# the sun's tropical longitude at the first of each month, modern epoch (0 deg = March equinox)
MONTH_LON = np.array([280.0, 310.6, 338.5, 9.1, 38.7, 69.3, 98.9, 129.5, 160.0, 189.6, 220.2, 249.8])
AUSTRALIA = (-44.0, -9.0, 112.0, 154.0)          # lat lo, lat hi, lon lo, lon hi


# ── small utilities ─────────────────────────────────────────────────────────────────────────────
def _fin(X, n):
    """(n, k) float64, finite, contiguous. Columns are never dropped: a place-gated block may be all
    zero on a dataset that carries no birthplace, and a zero-column array is not a valid block."""
    X = np.asarray(X, dtype=np.float64)
    if X.ndim == 1:
        X = X[:, None]
    assert X.shape[0] == n, (X.shape, n)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return np.ascontiguousarray(X)


def _sig(x, w):
    """Logistic squash with the argument clipped, so no overflow warning and no inf."""
    return 1.0 / (1.0 + np.exp(-np.clip(np.asarray(x, dtype=np.float64) / w, -30.0, 30.0)))


def _wrap360(x):
    return np.mod(np.asarray(x, dtype=np.float64), 360.0)


def _wrap180(x):
    return (np.asarray(x, dtype=np.float64) + 180.0) % 360.0 - 180.0


def _cs(deg):
    """cos/sin pair of an angle in degrees, as two arrays."""
    r = np.deg2rad(deg)
    return np.cos(r), np.sin(r)


# ── astronomy ───────────────────────────────────────────────────────────────────────────────────
def _obliquity(jd):
    """IAU 1976 mean obliquity of the ecliptic, degrees (Meeus 22.2)."""
    T = (np.asarray(jd, dtype=np.float64) - J2000) / 36525.0
    return 23.439291111 - 0.0130041667 * T - 1.6388889e-7 * T ** 2 + 5.0361111e-7 * T ** 3


def _sun(jd):
    """Apparent solar longitude, right ascension and declination, degrees (Meeus ch. 25, low precision).

    Good to about 0.01 degrees over this dataset's eight centuries; the self-test checks it against the
    Swiss Ephemeris sun already in E.RA/E.DEC.
    """
    jd = np.asarray(jd, dtype=np.float64)
    T = (jd - J2000) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = np.deg2rad(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    C = ((1.914602 - 0.004817 * T - 1.4e-5 * T * T) * np.sin(M)
         + (0.019993 - 0.000101 * T) * np.sin(2 * M) + 0.000289 * np.sin(3 * M))
    om = np.deg2rad(125.04 - 1934.136 * T)
    lam = L0 + C - 0.00569 - 0.00478 * np.sin(om)
    eps = np.deg2rad(_obliquity(jd) + 0.00256 * np.cos(om))
    lr = np.deg2rad(lam)
    ra = _wrap360(np.rad2deg(np.arctan2(np.cos(eps) * np.sin(lr), np.cos(lr))))
    dec = np.rad2deg(np.arcsin(np.sin(eps) * np.sin(lr)))
    return _wrap360(lam), ra, dec, np.rad2deg(eps)


def _lam_of_ra(ra, eps):
    """The sun's ecliptic longitude that corresponds to a given solar right ascension (both degrees).

    tan(alpha) = cos(eps) tan(lambda) inverted, quadrant-safe. Used to turn a required heliacal-rising
    right ascension into the solar longitude at which it happens, which is the phase this module reports.
    """
    r, e = np.deg2rad(ra), np.deg2rad(eps)
    return _wrap360(np.rad2deg(np.arctan2(np.sin(r), np.cos(r) * np.cos(e))))


def _dec_of_lam(lam, eps):
    return np.rad2deg(np.arcsin(np.sin(np.deg2rad(eps)) * np.sin(np.deg2rad(lam))))


def _gmst(jd):
    """Greenwich mean sidereal time, degrees (Meeus 12.4). Checked against swe.sidtime in the self-test."""
    jd = np.asarray(jd, dtype=np.float64)
    d = jd - J2000
    T = d / 36525.0
    return _wrap360(280.46061837 + 360.98564736629 * d + 0.000387933 * T * T - T ** 3 / 38710000.0)


def _catalogue():
    ra, dec, pmr, pmd, mag = [], [], [], [], []
    for _k, (h, m, s), (sg, dd, dm, ds), (pa, pd), v, _n in STARS:
        ra.append(15.0 * (h + m / 60.0 + s / 3600.0))
        dec.append(sg * (dd + dm / 60.0 + ds / 3600.0))
        pmr.append(pa / 3.6e6)                      # mas/yr -> deg/yr, already includes cos(dec)
        pmd.append(pd / 3.6e6)
        mag.append(v)
    return (np.array(ra), np.array(dec), np.array(pmr), np.array(pmd), np.array(mag))


_RA0, _DEC0, _PMR, _PMD, _MAG = _catalogue()


def _precess(jd):
    """Catalogue -> apparent equatorial coordinates of date. Returns (ra, dec), each (nobj, len(jd)).

    Linear proper motion from J2000, then the IAU 1976 / Lieske accumulated precession angles applied as
    the standard equatorial rotation.
    """
    jd = np.atleast_1d(np.asarray(jd, dtype=np.float64))
    dt = (jd - J2000) / 365.25
    d0 = np.deg2rad(_DEC0)[:, None] + np.deg2rad(_PMD)[:, None] * dt[None, :]
    a0 = (np.deg2rad(_RA0)[:, None]
          + np.deg2rad(_PMR)[:, None] * dt[None, :] / np.cos(np.deg2rad(_DEC0))[:, None])
    T = (jd - J2000) / 36525.0
    asec = DEG / 3600.0
    zeta = (2306.2181 * T + 0.30188 * T ** 2 + 0.017998 * T ** 3) * asec
    z = (2306.2181 * T + 1.09468 * T ** 2 + 0.018203 * T ** 3) * asec
    th = (2004.3109 * T - 0.42665 * T ** 2 - 0.041833 * T ** 3) * asec
    ap = a0 + zeta[None, :]
    A = np.cos(d0) * np.sin(ap)
    B = np.cos(th)[None, :] * np.cos(d0) * np.cos(ap) - np.sin(th)[None, :] * np.sin(d0)
    C = np.sin(th)[None, :] * np.cos(d0) * np.cos(ap) + np.cos(th)[None, :] * np.sin(d0)
    ra = _wrap360(np.rad2deg(np.arctan2(A, B)) + np.rad2deg(z)[None, :])
    dec = np.rad2deg(np.arcsin(np.clip(C, -1.0, 1.0)))
    return ra, dec


def _stars_at(jd):
    """Star positions for every couple, precession evaluated once per calendar year and shared.

    Half a year of precession is 25 arcseconds; nothing in this module resolves that.
    """
    jd = np.asarray(jd, dtype=np.float64)
    yr = np.floor((jd - J2000) / 365.25)
    uy, inv = np.unique(yr, return_inverse=True)
    ra_u, dec_u = _precess(J2000 + (uy + 0.5) * 365.25)
    return ra_u[:, inv], dec_u[:, inv]


def _ha_at_alt(phi, dec, h):
    """Hour angle (0..180 deg) at which declination `dec` reaches altitude `h` from latitude `phi`.

    Returns (H, c) where c is the raw cosine: c < -1 means the body never descends to h (circumpolar
    above it), c > 1 means it never climbs to h. H is the clipped solution.
    """
    sp, cp = np.sin(np.deg2rad(phi)), np.cos(np.deg2rad(phi))
    sd, cd = np.sin(np.deg2rad(dec)), np.cos(np.deg2rad(dec))
    c = (np.sin(np.deg2rad(h)) - sp * sd) / np.maximum(cp * cd, 1e-9)
    return np.rad2deg(np.arccos(np.clip(c, -1.0, 1.0))), c


def _altaz(phi, dec, H):
    """Altitude and azimuth (from north, eastward) in degrees, for hour angle H in degrees."""
    p, d, h = np.deg2rad(phi), np.deg2rad(dec), np.deg2rad(H)
    sa = np.sin(p) * np.sin(d) + np.cos(p) * np.cos(d) * np.cos(h)
    alt = np.rad2deg(np.arcsin(np.clip(sa, -1.0, 1.0)))
    y = -np.cos(d) * np.sin(h)
    x = np.sin(d) * np.cos(p) - np.cos(d) * np.sin(p) * np.cos(h)
    return alt, _wrap360(np.rad2deg(np.arctan2(y, x)))


def _bearing(alt1, az1, alt2, az2):
    """Position angle of point 2 seen from point 1, measured from the LOCAL VERTICAL, degrees.

    0 means point 2 lies straight above point 1 (the figure standing up), +-180 straight below, +-90 exactly
    horizontal. This is the great-circle initial bearing in the alt-azimuth frame with the zenith as pole —
    the number the emu's posture actually is.
    """
    b1, b2 = np.deg2rad(alt1), np.deg2rad(alt2)
    dl = np.deg2rad(np.asarray(az2, dtype=np.float64) - np.asarray(az1, dtype=np.float64))
    y = np.sin(dl) * np.cos(b2)
    x = np.cos(b1) * np.sin(b2) - np.sin(b1) * np.cos(b2) * np.cos(dl)
    return np.rad2deg(np.arctan2(y, x))


def _helphase(phi, sra, sdec, lam, eps, star_ra, star_dec, av, evening, at_set):
    """Solve for the solar longitude at which a star has its heliacal event, and report the phase since.

    The four classical horizon events all reduce to one equation: the star is exactly at the horizon while
    the sun sits `av` degrees below it (the arcus visionis). With H0 the star's semi-diurnal arc,

        LST(event) = star_ra -+ H0                      (- for the rise, + for the set)
        cos(H_sun) = (sin(-av) - sin(phi) sin(dec_sun)) / (cos(phi) cos(dec_sun))
        ra_sun     = LST(event) -+ H_sun                (- for evening/west, + for morning/east)

    and dec_sun is itself a function of ra_sun, so it is solved by fixed-point iteration (six passes;
    the self-test reports the residual). Returns
        (phase, ok) with phase = the solar longitude travelled since the event, in degrees, 0..360.
    `evening=True` puts the sun west of the meridian (an evening event), False east (a morning event).
    `at_set=True` uses the star's setting, False its rising.
    Sources for the arcus visionis formulation: Schaefer 1985, 1987.
    """
    H0, cH0 = _ha_at_alt(phi, star_dec, H0_STAR)
    rises = (cH0 > -1.0) & (cH0 < 1.0)               # neither circumpolar nor permanently below
    lst = star_ra + (H0 if at_set else -H0)
    lam_req = np.array(lam, dtype=np.float64, copy=True)
    ok = np.ones_like(lam_req, dtype=bool)
    for _ in range(6):
        ds = _dec_of_lam(lam_req, eps)
        Hs, cs = _ha_at_alt(phi, ds, -av)
        ok = (cs >= -1.0) & (cs <= 1.0)
        ra_req = lst - Hs if evening else lst + Hs
        lam_req = _lam_of_ra(_wrap360(ra_req), eps)
    return _wrap360(lam - lam_req), (ok & rises)


def _arcus(mag):
    """Arcus visionis by magnitude: the sun's depression at which a star of that brightness is first seen
    again. Ptolemy's Phaseis works with about 10 degrees for first-magnitude stars and more for fainter
    ones; Schaefer's modern reduction (1985, 1987) gives roughly 7-13 degrees over this range. Stepped,
    because a continuous fit would pretend to a precision the ancient rule never had."""
    m = np.asarray(mag, dtype=np.float64)
    return np.where(m <= 0.0, 8.0, np.where(m <= 1.5, 10.0, np.where(m <= 2.5, 12.0, 14.0)))


# ── per-partner geometry, computed once and shared by every block ────────────────────────────────
def _geom(E, slot):
    """Everything place-and-date about one partner's birth: the sky as seen from there, that night."""
    n = E.n
    lat = E.LAT_O if slot == 0 else E.LAT_Y
    lon = E.LON_O if slot == 0 else E.LON_Y
    known = (np.isfinite(lat) & np.isfinite(lon))
    phi = np.clip(np.nan_to_num(lat), -89.5, 89.5)
    lam_e = np.nan_to_num(lon)
    jd = E.JD[slot]
    # The sun comes from the Swiss Ephemeris table core already computed, not from the analytic series:
    # apparent longitude, right ascension and declination are all there and are exact. The analytic series
    # in _sun() is kept only for the dataset-free geometry self-test, and for the obliquity relation the
    # heliacal solver iterates on.
    isun = E.IDX["Sun"]
    slam = _wrap360(E.LON[slot, isun])
    sra_ra = _wrap360(E.RA[slot, isun])
    sdec_d = np.asarray(E.DEC[slot, isun], dtype=np.float64)
    eps = _obliquity(jd)
    ra, dec = _stars_at(jd)

    # local sidereal time at the three instants the traditions actually read the sky at
    H18, c18 = _ha_at_alt(phi, sdec_d, -18.0)                # astronomical twilight
    dark = (c18 > -1.0) & (c18 < 1.0)                        # a real twilight exists on that date/place
    lst = {"dusk": _wrap360(sra_ra + H18),
           "midnight": _wrap360(sra_ra + 180.0),             # always defined: the middle of the night
           "dawn": _wrap360(sra_ra - H18)}
    g = {"n": n, "slot": slot, "known": known.astype(np.float64), "kmask": known,
         "phi": phi, "lam_e": lam_e, "jd": jd, "sun_lam": slam, "sun_ra": sra_ra, "sun_dec": sdec_d,
         "eps": eps, "ra": ra, "dec": dec, "lst": lst, "dark": dark.astype(np.float64), "H18": H18}

    # rise / set geometry for every catalogue object
    H0, cH0 = _ha_at_alt(phi[None, :], dec, H0_STAR)
    g["H0"] = H0
    g["circum"] = (cH0 <= -1.0)                              # never sets
    g["never"] = (cH0 >= 1.0)                                # never rises
    g["rises"] = ~(g["circum"] | g["never"])
    g["culm"] = 90.0 - np.abs(phi[None, :] - dec)            # altitude at upper culmination
    g["upfrac"] = np.where(g["circum"], 1.0, np.where(g["never"], 0.0, H0 / 180.0))
    # rise azimuth: where on the horizon it comes up. The set azimuth is its mirror, 360 - A.
    ca = ((np.sin(np.deg2rad(H0_STAR)) - np.sin(np.deg2rad(phi))[None, :] * np.sin(np.deg2rad(dec)))
          / np.maximum(np.cos(np.deg2rad(phi))[None, :] * np.cos(np.deg2rad(H0_STAR)), 1e-9))
    g["azrise"] = np.rad2deg(np.arccos(np.clip(ca, -1.0, 1.0)))
    return g


def _at(g, key, when):
    """Altitude and azimuth of one catalogue object at one of the three night instants."""
    i = SIX[key]
    H = _wrap180(g["lst"][when] - g["ra"][i])
    return _altaz(g["phi"], g["dec"][i], H) + (H,)


def _stack(cols, n):
    """Column-stack a mixed list of (n,) vectors and (n, k) / (k, n) blocks into one (n, K) matrix."""
    out = []
    for c in cols:
        a = np.asarray(c, dtype=np.float64)
        if a.ndim == 1:
            a = a[:, None]
        elif a.shape[0] != n:
            assert a.shape[1] == n, (a.shape, n)
            a = a.T
        out.append(a)
    return _fin(np.column_stack(out), n)


# ── the blocks ──────────────────────────────────────────────────────────────────────────────────
def _b_visibility(E, G):
    """Which of the named stars each birthplace can see at all, and whether the two shared a sky.

    The one feature that is most characteristic of this whole family: from Hobart, Canopus never sets; from
    Sydney, Achernar never sets but Canopus does; from Berlin, neither ever rises. Declination of date is
    emitted too, un-gated, because precession alone moves these verdicts over eight centuries and that part
    of the feature is knowable without a birthplace.
    """
    n, cols = E.n, []
    for g in G:
        k = g["known"]
        cols += [g["circum"].astype(float).T * k[:, None], g["never"].astype(float).T * k[:, None]]
        cols += [(g["circum"].sum(0) * g["known"]), (g["never"].sum(0) * g["known"]),
                 (g["rises"].sum(0) * g["known"]), k]
        # how much of the far-southern sky this latitude reaches: the declination of the pole that is
        # permanently up, and of the cap that never rises
        cols += [np.sign(g["phi"]) * (90.0 - np.abs(g["phi"])) * k, np.abs(g["phi"]) * k]
    # shared sky: seen-by-one-only, per object, and the overlap of the two visible sets
    both = G[0]["known"] * G[1]["known"]
    vis0 = (~G[0]["never"]).astype(float)
    vis1 = (~G[1]["never"]).astype(float)
    cols += [np.abs(vis0 - vis1).T * both[:, None],
             (vis0 * vis1).sum(0) * both, np.abs(vis0 - vis1).sum(0) * both,
             (vis0 * vis1).sum(0) / np.maximum(np.maximum(vis0, vis1).sum(0), 1.0) * both, both]
    cols += [G[0]["dec"].T, G[1]["dec"].T]          # un-gated: precession of date
    return _stack(cols, n)


def _b_culmination(E, G):
    """How high each named star climbs, and for what fraction of the day it is above the horizon.

    Culmination altitude is 90 - |phi - dec| and the day fraction is the semi-diurnal arc over 180; both
    are pure place-and-date, and both are what a horizon-based tradition is actually looking at.
    """
    n, cols = E.n, []
    idx = [SIX[k] for k in CORE]
    for g in G:
        k = g["known"]
        cols += [np.clip(g["culm"][idx], -90.0, 90.0).T * k[:, None], g["upfrac"][idx].T * k[:, None]]
    both = G[0]["known"] * G[1]["known"]
    cols += [np.abs(G[0]["culm"][idx] - G[1]["culm"][idx]).T * both[:, None],
             np.abs(G[0]["upfrac"][idx] - G[1]["upfrac"][idx]).T * both[:, None], both]
    return _stack(cols, n)


def _b_horizon(E, G):
    """Rise azimuths — the horizon calendar.

    Australian sky knowledge is largely a horizon practice: a star returns not merely at a time of year but
    at a PLACE on the skyline, and that azimuth is fixed by declination and latitude. Emitted as cos/sin so
    a linear model can use it, plus the offset from due east, which is the quantity a horizon marker
    encodes.
    """
    n, cols = E.n, []
    idx = [SIX[k] for k in CORE]
    for g in G:
        k = g["known"]
        a = g["azrise"][idx]
        c, s = _cs(a)
        cols += [c.T * k[:, None], s.T * k[:, None], (np.abs(a - 90.0)).T * k[:, None]]
    both = G[0]["known"] * G[1]["known"]
    cols += [np.abs(_wrap180(G[0]["azrise"][idx] - G[1]["azrise"][idx])).T * both[:, None], both]
    return _stack(cols, n)


EMU = ["Coalsack", "EmuNeck", "EmuBody", "EmuLegs"]


def _b_emu_axis(E, G):
    """THE EMU IN THE SKY: the altitude of each part and the tilt of the axis, at dusk, midnight and dawn.

    The dark shape between Crux and Scorpius is read by its posture, not its position in a zodiac: the
    position angle of the head-to-body axis measured from the local vertical is the signal (Norris & Norris
    2009; Fuller, Norris & Trudgett 2014). cos of that angle is +1 when the bird stands straight up and 0
    when it lies flat along the horizon, which is exactly the running/sitting distinction the tradition
    draws. Computed at evening astronomical twilight, at local midnight (always defined, even inside the
    polar circles) and at morning twilight.
    """
    n, cols = E.n, []
    for g in G:
        k = g["known"]
        for when in ("dusk", "midnight", "dawn"):
            P = {p: _at(g, p, when) for p in EMU}
            alts = [P[p][0] for p in EMU]
            for a in alts:
                cols.append(a * k)
            for a, b in (("Coalsack", "EmuBody"), ("Coalsack", "EmuNeck"), ("EmuBody", "EmuLegs")):
                th = _bearing(P[a][0], P[a][1], P[b][0], P[b][1])
                c, s = _cs(th)
                cols += [c * k, np.abs(s) * k]
            up = sum((a > 0).astype(float) for a in alts)
            cols += [up * k, ((P["Coalsack"][0] > 0) & (P["EmuBody"][0] > 0)).astype(float) * k,
                     np.sin(np.deg2rad(P["Coalsack"][2])) * k]      # west (+) or east (-) of the meridian
        cols += [k, g["dark"] * k]
    both = G[0]["known"] * G[1]["known"]
    h0 = _at(G[0], "Coalsack", "dusk")[0]
    h1 = _at(G[1], "Coalsack", "dusk")[0]
    cols += [np.abs(h0 - h1) * both, both]
    return _stack(cols, n)


def _b_emu_posture(E, G):
    """The emu's posture as the tradition's own verdict: a five-way reading of the dusk sky.

    Head up but body still below the horizon is the April-May sky, when the record says the females are
    laying and the eggs are collected. Head and body both up with the head still east of the meridian is
    the mid-year sky, the bird "sitting on the nest". Head west of the meridian is the later sky, and head
    already set with the body still up is the last of it — the emu going down into the waterhole. The five
    classes are disjoint and exhaustive, and a soft version is emitted beside the hard one because a
    boundary at altitude zero is a cliff the ephemeris cannot really place.
    """
    n = E.n
    hard, soft = [], []
    for g in G:
        k = g["known"]
        ha, _haz, hH = _at(g, "Coalsack", "dusk")
        ba, _baz, _bH = _at(g, "EmuBody", "dusk")
        hu, bu = ha > 0.0, ba > 0.0
        west = np.sin(np.deg2rad(hH)) > 0.0
        cls = np.stack([(~hu) & (~bu), hu & (~bu), hu & bu & (~west), hu & bu & west, (~hu) & bu])
        hard.append(cls.astype(float).T * k[:, None])
        sh, sb = _sig(ha, 4.0), _sig(ba, 4.0)
        sw = _sig(np.sin(np.deg2rad(hH)) * 30.0, 6.0)
        soft.append(np.stack([(1 - sh) * (1 - sb), sh * (1 - sb), sh * sb * (1 - sw),
                              sh * sb * sw, (1 - sh) * sb]).T * k[:, None])
    both = G[0]["known"] * G[1]["known"]
    c0, c1 = hard[0], hard[1]
    pair = (c0[:, :, None] * c1[:, None, :]).reshape(n, 25) * both[:, None]
    same = (c0 * c1).sum(1) * both
    return _stack([hard[0], hard[1], soft[0], soft[1], pair, same, both], n)


def _b_emu_phase(E, G):
    """The emu's season without a birthplace: the sun's angle from the emu, which every couple has.

    Whether the emu is in the evening sky at all is mostly a solar-longitude question — the head is opposite
    the sun in June and lost in the glare in December — and that part needs no coordinates. This block is
    therefore dense for every couple in the dataset, which none of the other place blocks can be, and it
    also carries the pair's agreement: were the two born into the same emu season.
    """
    n, cols = E.n, []
    ph = []
    for g in G:
        for p in ("Coalsack", "EmuBody"):
            d = _wrap360(g["sun_ra"] - g["ra"][SIX[p]])
            ph.append(d)
            c, s = _cs(d)
            cols += [c, s, np.abs(_wrap180(d - 180.0))]        # 0 when the part culminates at midnight
        cols += [np.cos(np.deg2rad(g["sun_lam"])), np.sin(np.deg2rad(g["sun_lam"]))]
    d = _wrap180(ph[0] - ph[2])
    c, s = _cs(d)
    cols += [c, s, np.abs(d)]
    return _stack(cols, n)


def _b_heliacal_alt(E, G):
    """How deep in twilight each Boorong marker rose and set on the birth date, at the birth latitude.

    The sun's altitude at the exact moment the star crosses the horizon IS the heliacal-visibility
    variable: near -10 degrees the star is making its first or last appearance, deeper than that it is
    fully in the night sky, shallower and it is lost in the twilight. Three orb widths are emitted because
    the arcus visionis is itself a parameter and no tradition fixes it to a degree.
    """
    n, cols = E.n, []
    for g in G:
        k = g["known"]
        for _name, key in MARKERS:
            i = SIX[key]
            H0, cH0 = _ha_at_alt(g["phi"], g["dec"][i], H0_STAR)
            rises = ((cH0 > -1.0) & (cH0 < 1.0)).astype(float)
            for at_set in (False, True):
                lst = g["ra"][i] + (H0 if at_set else -H0)
                Hs = _wrap180(lst - g["sun_ra"])
                alt, _az = _altaz(g["phi"], g["sun_dec"], Hs)
                cols += [alt * k * rises,
                         np.exp(-0.5 * ((alt + 10.0) / 3.0) ** 2) * k * rises,
                         np.exp(-0.5 * ((alt + 10.0) / 6.0) ** 2) * k * rises,
                         np.sin(np.deg2rad(Hs)) * k * rises]     # morning (east) or evening (west) event
            cols.append(rises * k)
        cols.append(k)
    return _stack(cols, n)


def _b_heliacal_phase(E, G):
    """Days since the heliacal rising, and days since the heliacal setting, of each Boorong marker.

    This is the tradition's own clock. Neilloan's return says build nests; Marpeankurrk's return says the
    bittur are ready and her departure says they are gone. The phase is reported in the sun's own
    longitude, exactly where the arcus-visionis equation is solved, and converted to days only for
    readability. A star that is circumpolar or never rises from that latitude has no such event, and its
    columns are zero behind an explicit flag rather than being filled with a nearest-looking number.
    """
    n, cols = E.n, []
    for g in G:
        k = g["known"]
        for _name, key in MARKERS:
            i = SIX[key]
            av = float(_arcus(_MAG[i]))
            phr, okr = _helphase(g["phi"], g["sun_ra"], g["sun_dec"], g["sun_lam"], g["eps"],
                                 g["ra"][i], g["dec"][i], av, evening=False, at_set=False)
            phs, oks = _helphase(g["phi"], g["sun_ra"], g["sun_dec"], g["sun_lam"], g["eps"],
                                 g["ra"][i], g["dec"][i], av, evening=True, at_set=True)
            fr, fs = okr.astype(float) * k, oks.astype(float) * k
            cr, sr = _cs(phr)
            cs_, ss = _cs(phs)
            # phr and phs are the solar longitude travelled since each event, so the arc from the setting
            # to the following rising is their difference, and the star is inside the sun's glare exactly
            # while less of that arc has passed than the whole of it.
            gap = _wrap360(phs - phr)
            inglare = (phs < gap)
            cols += [cr * fr, sr * fr, (phr / SUN_DEG_PER_DAY) * fr,
                     cs_ * fs, ss * fs, (phs / SUN_DEG_PER_DAY) * fs,
                     np.minimum(phr, 360.0 - phr) * fr, fr, fs,
                     inglare.astype(float) * fr * fs]
        cols.append(k)
    return _stack(cols, n)


def _b_boorong_verdict(E, G):
    """Which marker rules the season, and Stanbridge's own recorded statements as tests.

    Stanbridge writes the calendar as verdicts, not as coordinates: Neilloan is seen and the malleefowl are
    building; Marpeankurrk stands in the north in the evening and the bittur are gathered; she sets and they
    are finished. Each recorded statement is computed as the geometry it describes — the star above the
    horizon at dusk, in the northern half of the sky, with its heliacal return recent — and the tally of how
    many of the statements hold at once is emitted as the season's own number.
    """
    n = E.n
    OUT = []
    near = []
    for g in G:
        k = g["known"]
        ph, up_n, up_dusk = [], [], []
        for _name, key in MARKERS:
            i = SIX[key]
            av = float(_arcus(_MAG[i]))
            p, ok = _helphase(g["phi"], g["sun_ra"], g["sun_dec"], g["sun_lam"], g["eps"],
                              g["ra"][i], g["dec"][i], av, evening=False, at_set=False)
            # recency of the heliacal return, as a weight that decays over a season
            ph.append(np.where(ok, np.exp(-np.minimum(p, 360.0 - p) / 30.0), 0.0))
            alt, az, _H = _at(g, key, "dusk")
            up_dusk.append((alt > 0).astype(float))
            up_n.append(((alt > 0) & (np.cos(np.deg2rad(az)) > 0)).astype(float))   # northern half
        P = np.stack(ph).T * k[:, None]                     # (n, markers)
        near.append(P)
        arg = np.argmax(P, axis=1)
        one = np.zeros((n, len(MARKERS)))
        one[np.arange(n), arg] = 1.0
        one *= (P.max(1) > 0)[:, None] * k[:, None]
        UD = np.stack(up_dusk).T * k[:, None]
        UN = np.stack(up_n).T * k[:, None]
        # the recorded statements, in Stanbridge's order of use
        v_neilloan = UD[:, 0] * P[:, 0]                       # Vega returns: nests are being built
        v_bittur_on = UN[:, 1]                                # Arcturus in the north at dusk: bittur
        v_bittur_off = (1.0 - UD[:, 1]) * k                   # Arcturus gone from the evening sky
        v_war = P[:, 2]                                       # Canopus returns
        v_wife = P[:, 3] * UD[:, 3]                           # Eta Carinae beside him
        v_djuit = UD[:, 4]                                    # Antares in the evening sky
        tally = v_neilloan + v_bittur_on + v_bittur_off + v_war + v_wife + v_djuit
        OUT += [one, P, UD, UN,
                np.column_stack([v_neilloan, v_bittur_on, v_bittur_off, v_war, v_wife, v_djuit, tally]), k]
    both = G[0]["known"] * G[1]["known"]
    agree = (near[0] * near[1]).sum(1) * both
    OUT += [agree, both]
    return _stack(OUT, n)


def _b_sisters(E, G):
    """The Seven Sisters and the hunter, as geometry above the horizon at dusk.

    Every version of the story is a chase, and what a sky-watcher sees of a chase is which figure is higher
    and which way the axis between them leans. The Pleiades (Larnankurrk / the Yugarilya), the belt of Orion
    (Kulkunbulla / Nyeeruna's waist), Betelgeuse (his club hand) and Aldebaran/Hyades (Kambugudha, the
    elder sister who stands between them) are computed at evening twilight, along with the tilt of the
    hunter-to-sisters axis from the vertical: whether he is below them, beside them, or above.
    """
    n, cols = E.n, []
    for g in G:
        k = g["known"]
        P = {p: _at(g, p, "dusk") for p in ("Alcyone", "Alnilam", "Betelgeuse", "Aldebaran")}
        for p in P:
            cols.append(P[p][0] * k)
        th = _bearing(P["Alnilam"][0], P["Alnilam"][1], P["Alcyone"][0], P["Alcyone"][1])
        c, s = _cs(th)
        cols += [c * k, np.abs(s) * k]
        th2 = _bearing(P["Aldebaran"][0], P["Aldebaran"][1], P["Alcyone"][0], P["Alcyone"][1])
        c2, s2 = _cs(th2)
        cols += [c2 * k, np.abs(s2) * k,
                 (P["Alcyone"][0] - P["Alnilam"][0]) * k,          # who is higher: the chase direction
                 (P["Aldebaran"][0] - P["Alcyone"][0]) * k,
                 ((P["Alcyone"][0] > 0) & (P["Alnilam"][0] > 0)).astype(float) * k,
                 np.abs(_wrap180(P["Alcyone"][1] - P["Alnilam"][1])) * k,
                 np.sin(np.deg2rad(P["Alcyone"][2])) * k, k]
    both = G[0]["known"] * G[1]["known"]
    cols += [np.abs(_at(G[0], "Alcyone", "dusk")[0] - _at(G[1], "Alcyone", "dusk")[0]) * both, both]
    return _stack(cols, n)


def _b_windows(E, G):
    """The visibility windows of the Pleiades and of Orion: in the sky, or lost in the sun's glare.

    The Pleiades vanish for about six weeks each year and their return is a cold-season marker across much
    of the continent; Orion's is a wet-season marker in the north. The window is bounded by the star
    group's own heliacal setting and rising at that latitude, so the "absent from the sky" flag below is
    computed, not assumed, and it is zero wherever the latitude makes the group circumpolar.
    """
    n, cols = E.n, []
    for g in G:
        k = g["known"]
        for key in ("Alcyone", "Alnilam", "Betelgeuse", "Coalsack", "Canopus"):
            i = SIX[key]
            av = float(_arcus(_MAG[i]))
            pr, okr = _helphase(g["phi"], g["sun_ra"], g["sun_dec"], g["sun_lam"], g["eps"],
                                g["ra"][i], g["dec"][i], av, evening=False, at_set=False)
            pset, okset = _helphase(g["phi"], g["sun_ra"], g["sun_dec"], g["sun_lam"], g["eps"],
                                    g["ra"][i], g["dec"][i], av, evening=True, at_set=True)
            f = (okr & okset).astype(float) * k
            # the invisible arc runs from the heliacal setting to the following heliacal rising
            gap = _wrap360(pset - pr)
            hidden = (pset < gap) & okset & okr
            cols += [(pr / SUN_DEG_PER_DAY) * f, hidden.astype(float) * k,
                     np.maximum(gap - pset, 0.0) / SUN_DEG_PER_DAY * hidden,
                     (gap / SUN_DEG_PER_DAY) * f,
                     np.exp(-0.5 * (np.minimum(pr, 360.0 - pr) / 15.0) ** 2) * f]
        cols.append(k)
    return _stack(cols, n)


def _b_tagai(E, G):
    """Tagai: the attitude of Crux (and Corvus) against the sea horizon at dusk.

    The Torres Strait rule is read as a posture, not a date — the hand upright, tilting, or dipped under
    the water (Sharp 1993). Computed as the altitude of Acrux and Gacrux at evening twilight and the tilt
    of the Gacrux-to-Acrux axis from the vertical, plus an in-country flag for the Torres Strait latitudes,
    because the rule is a local horizon rule and the model should be able to see where it applies.
    """
    n, cols = E.n, []
    for g in G:
        k = g["known"]
        A = _at(g, "Acrux", "dusk")
        Gx = _at(g, "Gacrux", "dusk")
        Cv = _at(g, "BetaCrv", "dusk")
        th = _bearing(Gx[0], Gx[1], A[0], A[1])
        c, s = _cs(th)
        dip = _sig(-A[0], 3.0)                        # the hand going into the sea
        cols += [A[0] * k, Gx[0] * k, Cv[0] * k, c * k, np.abs(s) * k, dip * k,
                 ((A[0] > 0) & (Gx[0] > 0)).astype(float) * k,
                 np.sin(np.deg2rad(A[2])) * k, np.cos(np.deg2rad(A[1])) * k,
                 ((g["phi"] > -11.5) & (g["phi"] < -9.0) &
                  (g["lam_e"] > 141.0) & (g["lam_e"] < 145.0)).astype(float) * k, k]
    return _stack(cols, n)


def _b_warrambool(E, G):
    """Warrambool, the Milky Way as a watercourse: its inclination to the horizon and where the bulge sits.

    Kamilaroi and Euahlayi read the galaxy as a river with the emu in it (Fuller, Norris & Trudgett 2014).
    The computable content is the tilt of the galactic plane against the local horizon — the axis from the
    bulge to the anticentre — and the altitude of the bulge itself, at dusk and at local midnight.
    """
    n, cols = E.n, []
    for g in G:
        k = g["known"]
        for when in ("dusk", "midnight"):
            C = _at(g, "GalCentre", when)
            A = _at(g, "GalAnti", when)
            th = _bearing(C[0], C[1], A[0], A[1])
            c, s = _cs(th)
            cols += [C[0] * k, A[0] * k, c * k, np.abs(s) * k,
                     ((C[0] > 0) | (A[0] > 0)).astype(float) * k,
                     np.maximum(C[0], A[0]) * k]
        cols.append(k)
    both = G[0]["known"] * G[1]["known"]
    cols += [np.abs(_at(G[0], "GalCentre", "midnight")[0]
                    - _at(G[1], "GalCentre", "midnight")[0]) * both, both]
    return _stack(cols, n)


def _b_barnumbirr(E, G):
    """Barnumbirr / Chargee Gnowee: Venus as the morning star, from the birthplace.

    Yolngu ceremony is built on Venus's return to the dawn horizon (Norris & Norris 2009), and Stanbridge
    records Venus as Chargee Gnowee, sister of the sun. What decides morning from evening is the sign of
    the elongation, and what decides visibility is Venus's altitude in the twilight and the sun's own
    depression when Venus itself rises. All three are computed here; the elongation alone would be the
    place-free version and is deliberately not the whole of this block.
    """
    n, cols = E.n, []
    iv = E.IDX["Venus"]
    for g in G:
        k = g["known"]
        s = g["slot"]
        vra, vdec = E.RA[s, iv], E.DEC[s, iv]
        elong = _wrap180(E.LON[s, iv] - E.LON[s, E.IDX["Sun"]])
        H0, cH0 = _ha_at_alt(g["phi"], vdec, H0_STAR)
        rises = ((cH0 > -1.0) & (cH0 < 1.0)).astype(float)
        Hs = _wrap180((vra - H0) - g["sun_ra"])
        alt_at_rise, _az = _altaz(g["phi"], g["sun_dec"], Hs)
        for when in ("dusk", "dawn"):
            H = _wrap180(g["lst"][when] - vra)
            alt, _az2 = _altaz(g["phi"], vdec, H)
            cols += [alt * k, (alt > 0).astype(float) * k]
        # elongation is Venus's longitude minus the sun's: negative means Venus rises first and is the
        # MORNING star (Barnumbirr), positive means she follows the sun down and is the evening star.
        cols += [alt_at_rise * k * rises,
                 np.exp(-0.5 * ((alt_at_rise + 6.0) / 3.0) ** 2) * k * rises,
                 np.abs(elong), (elong < 0).astype(float),
                 np.cos(np.deg2rad(elong)), np.sin(np.deg2rad(elong)), rises * k, k]
    return _stack(cols, n)


def _b_parans(E, G):
    """Which named star was on the horizon at the birth — marginalised over the twelve two-hour slots.

    A star rising, culminating or setting at the moment of birth is the one thing in this family that does
    need a clock, so it is computed at all twelve slot centres and reported as a DISTRIBUTION with its
    entropy, never as a pick. Note what is and is not uniform here: the Ascendant marginal is nearly flat
    by construction, but the fraction of the twelve hours in which a given star is near the horizon is not,
    because the angle at which that star's diurnal circle crosses the horizon depends on its declination and
    on the latitude — a star rising steeply passes through the band in minutes, one rising obliquely lingers.
    """
    n, cols = E.n, []
    off = np.asarray(getattr(E, "HOUR_OFFSETS", (np.arange(12) * 2 + 1 - 12.0) / 24.0), dtype=np.float64)
    idx = [SIX[k] for k in CORE]
    for g in G:
        k = g["known"]
        gm = _gmst(g["jd"][None, :] + off[:, None]) + g["lam_e"][None, :]      # (12, n) local sidereal
        rise_frac = []
        for i in idx:
            H = _wrap180(gm - g["ra"][i][None, :])
            alt, _az = _altaz(g["phi"][None, :], g["dec"][i][None, :], H)
            up = (alt > 0.0)
            near = (alt > -1.0) & (alt < 5.0)
            r = (near & (H < 0)).mean(0)
            s = (near & (H >= 0)).mean(0)
            c = (np.abs(H) < 15.0).mean(0)
            rise_frac.append(r)
            cols += [up.mean(0) * k, r * k, s * k, c * k]
        P = np.stack(rise_frac).T * k[:, None]
        tot = P.sum(1, keepdims=True)
        Q = np.where(tot > 0, P / np.maximum(tot, 1e-12), 1.0 / len(idx))
        cols += [E.entropy(Q) * k, tot.ravel() * k, k]
    return _stack(cols, n)


def _season_soft(lam, spans):
    """One-hot and soft membership of the sun's longitude in a calendar's month-derived season spans."""
    lo = np.array([MONTH_LON[a] for _nm, a, _b in spans])
    hi = np.array([MONTH_LON[(b + 1) % 12] for _nm, _a, b in spans])
    width = _wrap360(hi - lo)
    d = _wrap360(lam[None, :] - lo[:, None])
    inside = (d < width[:, None])
    centre = _wrap360(lo + width / 2.0)
    dist = np.abs(_wrap180(lam[None, :] - centre[:, None]))
    soft = np.exp(-0.5 * (dist / 30.0) ** 2)
    return inside.astype(float).T, (soft / np.maximum(soft.sum(0), 1e-12)).T


def _b_calendars(E, G):
    """The six- and seven-season calendars, keyed to the sun rather than to a calendar month.

    Noongar, Yolngu and Kulin all divide the year into six or seven ecological seasons, published as month
    spans. They are keyed here to the sun's tropical longitude through the modern month-to-longitude
    correspondence, because the seasons track the ecology and a Julian or Gregorian month across eight
    centuries does not. Each calendar carries an in-country flag from the birthplace: these are local
    calendars and their content is not transportable, and a model that can see "this birth was not in
    Noongar country" is being told the truth rather than being handed a season that means nothing there.
    The rest of every such calendar — flowering, eel runs, winds — is not derivable from four inputs.
    """
    n, cols = E.n, []
    for g in G:
        k = g["known"]
        for name, (spans, box) in CALENDARS.items():
            one, soft = _season_soft(g["sun_lam"], spans)
            ing = ((g["phi"] > box[0]) & (g["phi"] < box[1]) &
                   (g["lam_e"] > box[2]) & (g["lam_e"] < box[3])).astype(float) * k
            cols += [one, soft, ing[:, None], one * ing[:, None]]
        inaus = ((g["phi"] > AUSTRALIA[0]) & (g["phi"] < AUSTRALIA[1]) &
                 (g["lam_e"] > AUSTRALIA[2]) & (g["lam_e"] < AUSTRALIA[3])).astype(float) * k
        south = (g["phi"] < 0).astype(float) * k
        c, s = _cs(g["sun_lam"])
        cols += [inaus, south, c, s, k]
    both = G[0]["known"] * G[1]["known"]
    cols += [np.abs(_wrap180(G[0]["sun_lam"] - G[1]["sun_lam"])), both]
    return _stack(cols, n)


def _b_pair_sky(E, G):
    """Did the two of them grow up under the same sky?

    A pairing feature built out of the visibility classes rather than out of a zodiac: the difference in
    how high the emu's head climbs, in how long Canopus stays up, in which of the far-southern markers are
    permanently in the sky, and the plain fact of whether the two birthplaces are in the same hemisphere.
    In a tradition where the sky is the country's own, that is the closest computable analogue of a
    compatibility test — and it is emitted as its own block, because it is a claim about the pair, not
    about either person.
    """
    n = E.n
    a, b = G[0], G[1]
    both = a["known"] * b["known"]
    idx = [SIX[k] for k in CORE]
    cols = [np.abs(a["phi"] - b["phi"]) * both,
            np.abs(_wrap180(a["lam_e"] - b["lam_e"])) * both,
            ((a["phi"] >= 0) == (b["phi"] >= 0)).astype(float) * both,
            (a["circum"][idx].astype(float) * b["circum"][idx].astype(float)).sum(0) * both,
            np.abs(a["circum"][idx].astype(float) - b["circum"][idx].astype(float)).sum(0) * both,
            np.abs(a["culm"][idx] - b["culm"][idx]).max(0) * both,
            np.abs(a["upfrac"][idx] - b["upfrac"][idx]).sum(0) * both]
    for key in ("Coalsack", "Canopus", "Achernar", "Alcyone", "EtaCar"):
        i = SIX[key]
        cols += [np.abs(a["culm"][i] - b["culm"][i]) * both,
                 np.abs(a["upfrac"][i] - b["upfrac"][i]) * both,
                 np.abs(a["azrise"][i] - b["azrise"][i]) * both,
                 np.abs(_at(a, key, "dusk")[0] - _at(b, key, "dusk")[0]) * both,
                 (a["never"][i] == b["never"][i]).astype(float) * both]
    cols += [both, a["known"], b["known"], a["known"] + b["known"]]
    return _stack(cols, n)


# ── the module contract ─────────────────────────────────────────────────────────────────────────
def build(E):
    """name -> (E.n, k) float64, every value finite."""
    G = (_geom(E, 0), _geom(E, 1))
    out = {
        "abo: named-star visibility classes at each birthplace": _b_visibility(E, G),
        "abo: culmination altitude & hours above the horizon": _b_culmination(E, G),
        "abo: rise azimuths — the horizon calendar": _b_horizon(E, G),
        "abo: the emu in the sky — axis tilt at dusk/midnight/dawn": _b_emu_axis(E, G),
        "abo: emu posture verdict (breeding-season reading)": _b_emu_posture(E, G),
        "abo: emu solar phase, place-free": _b_emu_phase(E, G),
        "abo: heliacal windows — sun's depth at marker rise/set": _b_heliacal_alt(E, G),
        "abo: days since heliacal rising/setting, circular": _b_heliacal_phase(E, G),
        "abo: Boorong season marker + Stanbridge's verdicts": _b_boorong_verdict(E, G),
        "abo: Seven Sisters and the hunter at dusk": _b_sisters(E, G),
        "abo: Pleiades & Orion visibility windows": _b_windows(E, G),
        "abo: Tagai — Crux against the sea horizon": _b_tagai(E, G),
        "abo: Warrambool — Milky Way tilt & the bulge": _b_warrambool(E, G),
        "abo: Barnumbirr — Venus as the morning star": _b_barnumbirr(E, G),
        "abo: star on the horizon at birth, 12-hour marginal": _b_parans(E, G),
        "abo: six- and seven-season calendars in country": _b_calendars(E, G),
        "abo: shared sky between the two birthplaces": _b_pair_sky(E, G),
    }
    return out


# ── self-test ───────────────────────────────────────────────────────────────────────────────────
def _astronomy_selftest():
    """Facts about the sky that must come out right, checked against known values.

    This is the part of the module that does not depend on the dataset carrying a birthplace: if the
    geometry is wrong these fail, whatever the couples file happens to hold.
    """
    jd = 2451545.0 + 8000.0                     # 2022-01-15ish, a modern epoch
    ra, dec = _precess(np.array([jd]))
    ok = True

    def chk(name, got, want, tol):
        nonlocal ok
        good = abs(got - want) <= tol
        ok &= good
        print(f"    {'ok ' if good else 'FAIL'} {name:<52} {got:9.3f}  (expect {want} +-{tol})")

    chk("Canopus declination of date", float(dec[SIX['Canopus'], 0]), -52.7, 0.3)
    chk("Achernar declination of date", float(dec[SIX['Achernar'], 0]), -57.2, 0.3)
    chk("Coalsack declination of date", float(dec[SIX['Coalsack'], 0]), -62.5, 0.4)
    # Canopus is circumpolar from Hobart, not from Sydney; Achernar is circumpolar from Sydney
    for lat, star, want in ((-42.9, "Canopus", 1), (-33.87, "Canopus", 0), (-33.87, "Achernar", 1),
                            (51.5, "Canopus", 0), (51.5, "Achernar", 0)):
        _H, c = _ha_at_alt(np.array([lat]), dec[SIX[star], :1], H0_STAR)
        got = 1 if c[0] <= -1.0 else 0
        chk(f"{star} circumpolar from lat {lat}", got, want, 0)
    _H, c = _ha_at_alt(np.array([51.5]), dec[SIX["Canopus"], :1], H0_STAR)
    chk("Canopus never rises from lat 51.5 (c>1)", float(c[0]), 1.35, 0.35)
    # Crux at dusk from Sydney in early May: about 50 degrees up in the south-east, body still below
    lam, sra, sdec, eps = _sun(np.array([2459700.5]))       # 2022-05-01
    H18, _c = _ha_at_alt(np.array([-33.87]), sdec, -18.0)
    lst = _wrap360(sra + H18)
    ra2, dec2 = _precess(np.array([2459700.5]))
    alt, az = _altaz(np.array([-33.87]), dec2[SIX["Coalsack"], :1], _wrap180(lst - ra2[SIX["Coalsack"], :1]))
    chk("emu head altitude, Sydney dusk 1 May", float(alt[0]), 47.0, 8.0)
    chk("emu head azimuth, Sydney dusk 1 May", float(az[0]), 148.0, 15.0)
    balt, _baz = _altaz(np.array([-33.87]), dec2[SIX["EmuBody"], :1],
                        _wrap180(lst - ra2[SIX["EmuBody"], :1]))
    chk("emu body still below horizon then", float(balt[0] < 0), 1.0, 0.0)
    # the same night two months later: the whole bird is up
    lam, sra, sdec, eps = _sun(np.array([2459760.5]))       # 2022-06-30
    H18, _c = _ha_at_alt(np.array([-33.87]), sdec, -18.0)
    lst = _wrap360(sra + H18)
    balt, _baz = _altaz(np.array([-33.87]), dec2[SIX["EmuBody"], :1],
                        _wrap180(lst - ra2[SIX["EmuBody"], :1]))
    chk("emu body up at dusk on 30 June", float(balt[0] > 0), 1.0, 0.0)
    # the tilt convention: a point straight overhead of another must give bearing 0
    chk("bearing of a point straight above", float(_bearing(np.array([10.0]), np.array([90.0]),
                                                            np.array([40.0]), np.array([90.0]))[0]),
        0.0, 0.001)
    chk("bearing of a point at the same altitude", abs(float(_bearing(np.array([10.0]), np.array([90.0]),
                                                                     np.array([10.0]), np.array([150.0]))[0])),
        90.0, 6.0)
    # heliacal rising of Sirius from Cairo, about 1 August in the modern era (the classical Egyptian check)
    phi = np.array([30.0])
    lam, sra, sdec, eps = _sun(np.array([2459792.5]))       # 2022-08-01
    r2, d2 = _precess(np.array([2459792.5]))
    ph, okh = _helphase(phi, sra, sdec, lam, eps, r2[SIX["Sirius"], :1], d2[SIX["Sirius"], :1],
                        8.0, evening=False, at_set=False)
    days = float(np.minimum(ph, 360.0 - ph)[0]) / SUN_DEG_PER_DAY
    chk("Sirius heliacal rise within days of 1 Aug (Cairo)", days, 0.0, 14.0)
    return ok


def _report(E, bl, place_known):
    from evalx import quick
    bad, flat = 0, []
    print(f"  {'block':<56} {'cols':>5}   {'acc':>7}  {'AUC':>6}")
    rows = []
    for k, v in bl.items():
        assert v.ndim == 2 and v.shape[0] == E.n, (k, v.shape)
        assert v.dtype == np.float64, (k, v.dtype)
        assert np.isfinite(v).all(), k
        const = v.std(0).max() <= 0.0
        if const:
            flat.append(k)
            if place_known:
                bad += 1
        a, u = quick(E, v)
        rows.append((k, v.shape[1], a, u))
        tag = "   (place-gated: all zero)" if const else ""
        print(f"  {k:<56} {v.shape[1]:>5}   {100*a:6.2f}%  {u:.4f}{tag}")
    print(f"  total columns {sum(r[1] for r in rows):,}")
    return bad, flat, rows


if __name__ == "__main__":
    import sys
    import numpy as np
    import swisseph as swe
    from core import load

    print(f"\n{TRADITION}\n")
    print("  sky geometry self-test (independent of the dataset):")
    geo_ok = _astronomy_selftest()

    E = load()
    kn = int((np.isfinite(E.LAT_O) & np.isfinite(E.LON_O)).sum())
    kn2 = int((np.isfinite(E.LAT_Y) & np.isfinite(E.LON_Y)).sum())
    print(f"\n  couples {E.n:,} · birthplace known: older {100*kn/E.n:.1f}% · younger {100*kn2/E.n:.1f}%")

    # the arithmetic this module leans on, checked against Swiss Ephemeris on the real dates
    isun = E.IDX["Sun"]
    eps = _obliquity(E.JD[0])
    dinv = np.abs(_wrap180(_lam_of_ra(E.RA[0, isun], eps) - E.LON[0, isun])).max()
    j = E.JD[0][:400]
    dst = np.abs(_wrap180(_gmst(j) - np.array([swe.sidtime(float(x)) * 15.0 for x in j]))).max()
    _lam, sra, sdec, _e = _sun(E.JD[0])
    dra = np.abs(_wrap180(sra - E.RA[0, isun])).max()
    print(f"  ephemeris RA -> ecliptic longitude round trip: {dinv:.5f} deg  (the heliacal solver's map)")
    print(f"  analytic GMST vs swe.sidtime:                  {dst:.5f} deg")
    print(f"  analytic sun (self-test only) vs ephemeris RA:  {dra:.4f} deg over {E.n:,} dates back to "
          f"{int((E.JD[0].min()-J2000)/365.25+2000)}")
    assert dinv < 0.02, "the RA/longitude map disagrees with the ephemeris sun"
    assert dst < 0.05, "sidereal time disagrees with the ephemeris"

    bl = build(E)
    bad, flat, rows = _report(E, bl, place_known=(kn > 0 or kn2 > 0))
    if not (kn or kn2):
        print("\n  NOTE: this couples file carries NO birthplace, so every place-dependent block is zero by\n"
              "        construction — a latitude is never imputed here, because a guessed latitude invents a\n"
              "        sky. The blocks above marked place-gated will populate on a dataset with coordinates;\n"
              "        the sky geometry itself is verified by the independent self-test at the top.")
    ok = geo_ok and bad == 0
    print("\nOK" if ok else f"\nFAILED (constant blocks with coordinates present: {bad}; geometry ok={geo_ok})")
    sys.exit(0 if ok else 1)
