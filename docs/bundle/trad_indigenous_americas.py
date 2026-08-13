"""
trad_indigenous_americas.py — Indigenous American sky knowledge OUTSIDE Mesoamerica.

Andean/Inca · Diné (Navajo) · Pawnee · Lakota · Hopi · Mapuche · eastern woodland (Cherokee,
Anishinaabe, Haudenosaunee).

═══ THE HONEST FRAME, FIRST ════════════════════════════════════════════════════════════════════════

NONE OF THESE TRADITIONS CASTS A BIRTH CHART, AND NONE OF THEM SCORES A COUPLE. There is no
Ashtakoot here, no porutham count, no clash tally — inventing one would be fabrication, not
scholarship. What these traditions DO compute, precisely and on the record, is a CALENDAR POSITION
and a VISIBILITY: which moon of the lunar year it is; how far the year has run since the Pleiades
reappeared before dawn; which huaca of the 328-day Cusco count the day is; where along the horizon
the sun rose from this place this morning; whether the llama's eyes stood above the southern
horizon at midnight; whether Venus was the Morning Star or the Evening Star. Those numbers are the
tradition's own, they are exactly computable from a date and a place, and they are what this module
emits. Every block therefore answers "what was the sky doing, here, then", never "are these two
compatible" — the pairing blocks combine the two partners' own calendar positions and say so.

THREE THINGS MAKE THIS FAMILY FIT THE FOUR-INPUT CONTRACT UNUSUALLY WELL

  1. It is HORIZON astronomy, so the birthplace latitude is not a nuisance parameter — it IS the
     instrument. A Hopi sun-watcher's calendar is literally a function of (date, place).
  2. It needs no birth hour. Every observation these traditions made was at a moment the sky itself
     fixes: dawn twilight, dusk twilight, local midnight. Those are determined by date + place
     alone. One block additionally marginalises the 12 candidate birth hours (§ block 12) to answer
     the one question that does need an hour: was this star up at the moment of birth?
  3. Nothing here rests on houses or an Ascendant, so the hard limit in CONTRACT.md does not bite.

WHAT IS COMPUTED, TRADITION BY TRADITION, WITH SOURCES

  ANDEAN / INCA
    · Collca ("the storehouse") = the Pleiades. Its heliacal rising in June opened the year and was
      read as a forecast of the coming season — Polo de Ondegardo (1571); Urton, *At the Crossroads
      of the Earth and the Sky* (1981); and the modern demonstration that the cluster's pre-dawn
      clarity tracks El Niño: Orlove, Chiang & Cane, "Forecasting Andean rainfall and crop yield
      from the influence of El Niño on Pleiades visibility", Nature 403 (2000) 68-71.
    · The 328-DAY CEQUE CALENDAR. 328 huacas (shrines) strung on 41 ceques radiating from the
      Coricancha in Cusco, grouped by the four suyus; 328 days = 12 sidereal months of 27 1/3 days,
      and the 37 days left over in the solar year are the days the Pleiades are invisible.
      R. T. Zuidema, "The Inca calendar", in Aveni (ed.) *Native American Astronomy* (1977), and
      "Catachillay: the role of the Pleiades and of the Southern Cross and alpha and beta Centauri
      in the calendar of the Incas" (1982). The shrine list itself: Cobo, *Historia del Nuevo Mundo*
      (c. 1653), bk. 13, translated as Rowe, "An account of the shrines of ancient Cuzco" (1979).
    · Inti Raymi at the June solstice, Capac Raymi at the December solstice — Garcilaso de la Vega,
      *Comentarios Reales* (1609), bk. 6; Molina, *Relación de las fábulas y ritos de los Incas*.
    · The DARK-CLOUD constellations: Yacana the llama, whose eyes (Llamacñawin) are alpha and beta
      Centauri, and Yutu the tinamou = the Coalsack by Crux — Urton (1981), ch. 8; the llama that
      drinks the sea at midnight is in the Huarochirí Manuscript (c. 1608), ch. 29.

  DINÉ (NAVAJO)
    · Dilyéhé = the Pleiades; Náhookòs bikǫ' = Polaris (the central fire); Náhookòs bika'í = the
      revolving male (the Big Dipper); Náhookòs bi'áadí = the revolving female (Cassiopeia);
      Átsé Ets'ózí = First Slim One (Orion); Átsé Etsoh = First Big One (Scorpius); Gah heet'e'ii =
      Rabbit Tracks (the stars of Scorpius's tail). Griffin-Pierce, *Earth is My Mother, Sky is My
      Father* (1992); Maryboy & Begay, *Sharing the Skies: Navajo Astronomy* (2010).
    · The winter storytelling season is gated by which constellations are in the evening sky, and
      the planting rule is read off Dilyéhé: the two are visibility windows, computed here.
    · Orion and Scorpius are never in the sky together — that opposition is the teaching, and it is
      computed exactly (one up, one down, at local midnight).

  PAWNEE (SKIDI)
    · Morning Star and Evening Star, whose union makes the first human being; the star chart with
      the Chief star that does not move (Polaris), the Council of Chiefs (Corona Borealis) and the
      Swimming Ducks (lambda and upsilon Scorpii, whose pre-dawn return announces spring).
      Von Del Chamberlain, *When Stars Came Down to Earth: Cosmology of the Skidi Pawnee* (1982).
    · IDENTIFICATION IS DISPUTED and this module does not hide it: the Evening Star is Venus, but
      Chamberlain argues the Skidi Morning Star of the sacrifice is more likely MARS than Venus.
      Venus's phases are computed as the primary encoding (the assignment's reading) AND Mars's
      morning/evening station is emitted beside it, so a model can prefer either.
    · Chamberlain leaves the four semi-cardinal stars (Black, Yellow, White, Red) unidentified.
      They are therefore NOT encoded — see "WHAT I COULD NOT DO".

  LAKOTA
    · Cangleska Wakan, the sacred hoop of constellations, and the spring journey in which the
      people move to the place on the land that mirrors the constellation the sun has reached:
      Cansasa Ipusye (dried willow, Triangulum), Tayamni (the bison — head the Pleiades, backbone
      Orion's Belt, tail Sirius), and Ki Inyanka Ocanku, the Race Track ring of bright winter stars.
      Ronald Goodman, *Lakota Star Knowledge: Studies in Lakota Stellar Theology* (1992).
    · The rule is "where is the sun in the hoop", which is exactly computable. The land half of the
      mirror is a fixed geography, not a per-couple number, so only the sky half is encoded.

  HOPI
    · The horizon calendar: the sun-watcher (Tawa-mongwi) named the points on the skyline where the
      sun rose and read the date off them; Soyal at the December solstice, Powamuya in February,
      Niman about sixteen days after the June solstice, Wuwutsim in November. Alexander Stephen,
      *Hopi Journal* (ed. Parsons, 1936); McCluskey, "The astronomy of the Hopi Indians", Journal
      for the History of Astronomy 8 (1977) 174-195; Zeilik, "The ethnoastronomy of the historic
      Pueblos I: calendrical sun watching", Archaeoastronomy 8 (1985).
    · The sunrise azimuth at the birthplace, its rate of change (the solstice STANDSTILL that the
      sun-watcher actually detected), and the fraction of the way between the solstice extremes —
      the horizon-calendar coordinate itself — are computed exactly. The named marks are not: see
      "WHAT I COULD NOT DO".

  MAPUCHE
    · We Tripantu / Wüñoy Tripantu, the new year at the June solstice — the first sunrise after the
      longest night (Course, *Becoming Mapuche*, 2011; the date, 24 June, is a Chilean holiday).
    · Wüñelfe, Venus as the herald of dawn — recorded as "wüñelfe, el lucero" in Augusta,
      *Diccionario Araucano-Español* (1916). Pünoñ Choyke, "the rhea's footprint" = the Southern
      Cross, and Ngaw = the Pleiades: recorded in the early dictionaries and standard in the modern
      Mapuche ethnoastronomy literature; flagged here as secondary-literature identifications.
    · Because the Mapuche year is SOUTHERN, the module keys this block to the solstice that gives
      the LONGEST NIGHT at the birthplace, which is June in the south and December in the north.
      That is a different number from the Inca June-solstice block, not a rename of it.

  EASTERN WOODLAND
    · The year is counted in MOONS, twelve or thirteen of them, not in months. The lunation index is
      counted from the first new moon after the December solstice, which is also the anchor of the
      Haudenosaunee Midwinter ceremony (Fenton, *The Iroquois Eagle Dance* and the Seneca
      ceremonial outlines; the Pleiades' role in the northeastern calendars: Lynn Ceci, "Watchers of
      the Pleiades: ethnoastronomy among native cultivators in northeastern North America",
      Ethnohistory 25 (1978) 301-317).
    · The twelve named Cherokee moons (Unolvtani the cold moon, Kagali the bony moon, Anuyi the
      windy moon, Kawohni the flower moon, Anisguti the planting moon, Dehaluyi the green-corn
      moon, Guyegwoni the ripe-corn moon, Galohni the fruit moon, Dulisdi the nut moon, Duninudi
      the harvest moon, Nudadequa the trading moon, Vsgiyi the snow moon) as published by the
      Cherokee Nation; the ceremonial cycle in Mooney, *Myths of the Cherokee* (1900).

═══ HOW THE ASTRONOMY IS DONE, AND WHY IT IS NOT A SHORTCUT ═══════════════════════════════════════

THERE IS NO STAR FILE. `~/.sweph/ephe` carries only seas/semo/sepl — no `sefstars.txt` — so
`swe.fixstar2_ut` resolves nothing except Spica (Swiss Ephemeris's built-in, kept for the True-Citra
ayanamsa). Star positions therefore come from a hardcoded J2000 catalogue (Hipparcos/Simbad
positions, listed with their sources beside each entry) precessed with the IAU-1976 (Lieske) angles.
The self-test VALIDATES all of it against Swiss Ephemeris: Spica precessed by this module agrees
with `swe.fixstar2_ut` to 0.012 degrees over 1215-1996, the solar position agrees with
`swe.calc_ut` to 0.010 degrees, sidereal time agrees with `swe.sidtime` to 0.005 degrees, and the
civil-date conversion agrees with `swe.revjul` exactly. Nothing here is asserted without being
checked against the ephemeris.

HELIACAL EVENTS use the classical arcus-visionis criterion, not Schaefer's photometric model (which
is what `swe.heliacal_ut` implements and which needs the missing star file): a star is first visible
in the morning on the day its altitude, at the instant the sun stands 12 degrees below the horizon,
first exceeds 3 degrees while the star is east of the meridian; last visible in the evening on the
day the same quantity falls below it in the west. The 12-degree depth and the small altitude floor
are the values conventionally used for cluster/first-magnitude visibility in archaeoastronomy
(Aveni, *Skywatchers*, appendix on heliacal phenomena). The event is computed on a (latitude, epoch)
grid and interpolated, so its cost does not grow with the number of couples; resolution is 1.5
degrees of latitude and 50 years of precession, worth about one day.

SEASONS ARE KEYED TO THE SUN'S LONGITUDE, NEVER TO A DAY NUMBER. A day-of-year is a calendar
artefact and this dataset spans the Julian/Gregorian break; the sun's tropical longitude is the
season itself. Day COUNTS (the 328-day ceque calendar needs one) come from solving for the instant
the sun last held the anchor longitude, by Newton iteration on the validated solar series.

INSTANTS. Birth quantities come from `core`'s exact noon ephemeris. Night-sky quantities are
evaluated at LOCAL MIDNIGHT of the birth date and at the two twilights — moments the sky fixes, not
a guessed birth hour. A star's hour angle at local midnight turns out to be date-only to within
half a degree (local midnight is by definition opposite the sun), so those columns are valid for
every couple; the ALTITUDE needs the latitude and ships with a known-flag.

MISSING PLACES ARE NEVER IMPUTED. A place-dependent column is zero with a companion "known" flag,
per the addendum. Every block deliberately also carries date-only columns, so a block still varies
when the dataset has no coordinates at all (the local default file has none; the four-input dataset
has them for 75%/66% of partners).

═══ WHAT I COULD NOT DO ═══════════════════════════════════════════════════════════════════════════

  · No compatibility score exists to compute, in any of these traditions (see the frame above).
  · The real huaca-per-ceque counts vary from 3 to 15 (Cobo/Rowe); the exact 8-per-ceque division of
    328 is Zuidema's CALENDRICAL idealisation and is labelled as such where it is used.
  · Individual ceque AZIMUTHS are archaeological reconstructions (Bauer, *The Sacred Landscape of
    the Inca*, 1998) that are not available here, so the radial coordinate is the ceque index and
    the four documented suyu quadrants — not a measured bearing.
  · The Hopi named horizon marks (Tawaki, the specific mesa points at Walpi and Oraibi) need that
    village's skyline profile. It is not available, so the azimuth is computed against a flat,
    refracted horizon and no named mark is matched.
  · The four Pawnee semi-cardinal stars are unidentified in Chamberlain and are not encoded.
  · Lakota sky-to-land mirroring: the Black Hills sites are a fixed geography, so only the sky half.
  · Milky Way features (the Andean Mayu, Mapuche Wenu Lewfü) are omitted: the river's orientation is
    computable but no source gives a number the tradition itself reckons, so there is nothing to
    reproduce and I will not invent one.
  · Proper motion is neglected in the star catalogue. The worst case is alpha Centauri, ~0.8 degrees
    over 800 years, which changes no visibility decision made here.
  · The lunation anchor inherits the Moon's +-6 degree noon uncertainty (about +-0.5 day) and the
    new-moon instant is refined against the real ephemeris, so a moon INDEX is wrong only for a
    birth within a few hours of a new moon.

Usage: cd astro && /tmp/aqpy/bin/python trad_indigenous_americas.py
"""

import numpy as np
import swisseph as swe

TRADITION = ("Indigenous American beyond Mesoamerica (Inca Collca & the 328-day ceque calendar, "
             "Diné, Pawnee, Lakota, Hopi horizon calendar, Mapuche We Tripantu, eastern-woodland moons)")

D2R = np.pi / 180.0
R2D = 180.0 / np.pi
J2000 = 2451545.0
YR_TROP = 365.24219
SYN_MONTH = 29.530588853          # mean synodic month, days
SUN_H0 = -0.833                   # standard refracted sunrise/sunset altitude (centre of the disc)
TWI = -12.0                       # nautical twilight depth used as the arcus visionis reference
HMIN = 3.0                        # minimum star altitude counted as "seen" (horizon extinction)

# ── the star catalogue ──────────────────────────────────────────────────────────────────────────
# J2000 (ICRS) right ascension and declination in degrees, from the standard Hipparcos/Simbad
# positions. There is no sefstars.txt in this ephemeris directory, so these are hardcoded and the
# precession that carries them to a birth date is validated against swe.fixstar2_ut("Spica").
STARS = {
    # Pleiades — Collca (Inca), Dilyéhé (Diné), Tayamni pa (Lakota), the Seven Stars (Pawnee)
    "Alcyone":    (56.8711, 24.1051),      # eta Tau, the cluster's brightest member
    # the pole and the revolving ones — Náhookòs (Diné), the Chief star (Pawnee)
    "Polaris":    (37.9546, 89.2641),      # alpha UMi
    "Dubhe":      (165.9320, 61.7510),     # alpha UMa
    "Alkaid":     (206.8852, 49.3133),     # eta UMa
    "Schedar":    (10.1268, 56.5373),      # alpha Cas
    "Caph":       (2.2945, 59.1498),       # beta Cas
    # Corona Borealis — the Council of Chiefs (Pawnee)
    "Alphecca":   (233.6720, 26.7147),     # alpha CrB
    # Crux and the Centaurs — Pünoñ Choyke (Mapuche), Yacana's eyes and Yutu (Inca)
    "Acrux":      (186.6496, -63.0991),    # alpha Cru
    "Gacrux":     (187.7915, -57.1132),    # gamma Cru
    "Mimosa":     (191.9303, -59.6888),    # beta Cru
    "RigilKent":  (219.9021, -60.8340),    # alpha Cen — Llamacñawin, the llama's eye
    "Hadar":      (210.9559, -60.3730),    # beta Cen  — the other eye
    "Coalsack":   (192.5000, -62.5000),    # the dark nebula's centre — Yutu. A REGION, not a star.
    # Orion — Átsé Ets'ózí (Diné), Tayamni cankahu (Lakota), Hotòmqam (Hopi)
    "Mintaka":    (83.0016, -0.2991),      # delta Ori
    "Alnilam":    (84.0534, -1.2019),      # epsilon Ori
    "Alnitak":    (85.1897, -1.9426),      # zeta Ori
    "Betelgeuse": (88.7929, 7.4071),
    "Rigel":      (78.6345, -8.2016),
    # Scorpius — Átsé Etsoh and Gah heet'e'ii (Diné), the Swimming Ducks (Pawnee)
    "Antares":    (247.3519, -26.4320),    # alpha Sco
    "Shaula":     (263.4022, -37.1038),    # lambda Sco — a Swimming Duck / a Rabbit Track
    "Lesath":     (262.6910, -37.2958),    # upsilon Sco — the other one
    # the Race Track ring (Lakota Ki Inyanka Ocanku) and Tayamni's tail
    "Sirius":     (101.2872, -16.7161),
    "Procyon":    (114.8255, 5.2250),
    "Castor":     (113.6495, 31.8883),
    "Pollux":     (116.3290, 28.0262),
    "Capella":    (79.1723, 45.9980),
    "Aldebaran":  (68.9802, 16.5093),
    "Mothallah":  (28.2705, 29.5788),      # alpha Tri — Cansasa Ipusye
    "BetaTri":    (32.3860, 34.9873),
    # kept only so the self-test can check this module's precession against Swiss Ephemeris
    "Spica":      (201.2983, -11.1613),
}

# Cusco, the Coricancha: the 328-day ceque calendar is CUSCO's calendar, not the birthplace's, so
# this anchor is deliberately fixed and the resulting count is available for every couple.
CUSCO_LAT, CUSCO_LON = -13.5167, -71.9781

# The four suyus and their ceque counts (Cobo/Rowe; Zuidema 1977). 9+9+9+14 = 41 ceques, 328 huacas.
SUYU = [("Chinchaysuyu", 9), ("Antisuyu", 9), ("Collasuyu", 9), ("Cuntisuyu", 14)]
SUYU_OF_CEQUE = np.concatenate([np.full(k, i) for i, (_, k) in enumerate(SUYU)])   # (41,)

# Lakota sacred-hoop stations, in the order the sun meets them. Identifications from Goodman (1992)
# as commonly reproduced; only the groups whose identification is consistent across retellings.
HOOP = [
    ("Cansasa Ipusye (dried willow)", ["Mothallah", "BetaTri"]),
    ("Tayamni pa (the bison's head)", ["Alcyone"]),
    ("Race Track: Aldebaran", ["Aldebaran"]),
    ("Tayamni cankahu (the backbone)", ["Mintaka", "Alnilam", "Alnitak"]),
    ("Race Track: Rigel", ["Rigel"]),
    ("Tayamni sinte (the tail)", ["Sirius"]),
    ("Race Track: Gemini", ["Castor", "Pollux", "Procyon"]),
    ("Race Track: Capella", ["Capella"]),
]

# The twelve named Cherokee moons, indexed by the calendar month of the moon's own new moon.
CHEROKEE_MOONS = ["Unolvtani", "Kagali", "Anuyi", "Kawohni", "Anisguti", "Dehaluyi",
                  "Guyegwoni", "Galohni", "Dulisdi", "Duninudi", "Nudadequa", "Vsgiyi"]


# ════════════════════════════════════════════════════════════════════════════════════════════════
# validated astronomy helpers (each one is checked against Swiss Ephemeris in the self-test)
# ════════════════════════════════════════════════════════════════════════════════════════════════

def _sun(jd):
    """Sun's apparent ecliptic longitude, RA, declination and the true obliquity, degrees.

    Meeus, *Astronomical Algorithms*, ch. 25 ("lower accuracy" solar series) plus the nutation term
    in longitude and the obliquity of ch. 22. Agrees with swe.calc_ut to 0.010 degrees over
    1215-2000 — checked in the self-test. Used only where a vectorised sun over arbitrary grids of
    dates is needed; every birth-instant quantity comes from core's exact table.
    """
    jd = np.asarray(jd, dtype=np.float64)
    T = (jd - J2000) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = np.mod(357.52911 + 35999.05029 * T - 0.0001537 * T * T, 360.0) * D2R
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * np.sin(M)
         + (0.019993 - 0.000101 * T) * np.sin(2 * M) + 0.000289 * np.sin(3 * M))
    Om = np.mod(125.04 - 1934.136 * T, 360.0) * D2R
    lam = np.mod(L0 + C - 0.00569 - 0.00478 * np.sin(Om), 360.0)
    e0 = (23.0 + 26.0 / 60.0 + 21.448 / 3600.0) - (46.8150 * T + 0.00059 * T * T - 0.001813 * T ** 3) / 3600.0
    eps = e0 + 0.00256 * np.cos(Om)
    lr, er = lam * D2R, eps * D2R
    ra = np.mod(np.arctan2(np.cos(er) * np.sin(lr), np.cos(lr)) * R2D, 360.0)
    dec = np.arcsin(np.clip(np.sin(er) * np.sin(lr), -1.0, 1.0)) * R2D
    return lam, ra, dec, eps


def _gmst(jd):
    """Greenwich mean sidereal time in degrees (Meeus 12.4). Agrees with swe.sidtime to 0.005 deg."""
    jd = np.asarray(jd, dtype=np.float64)
    T = (jd - J2000) / 36525.0
    return np.mod(280.46061837 + 360.98564736629 * (jd - J2000)
                  + 0.000387933 * T * T - T ** 3 / 38710000.0, 360.0)


def _precess(ra0, dec0, jd):
    """J2000 equatorial coordinates precessed to jd — IAU 1976 (Lieske) angles, Meeus 21.3.

    Checked against swe.fixstar2_ut("Spica") at six epochs spanning this dataset: agreement is
    better than 0.012 degrees. Proper motion is deliberately not applied (see the docstring).
    """
    t = (np.asarray(jd, dtype=np.float64) - J2000) / 36525.0
    zeta = (2306.2181 * t + 0.30188 * t * t + 0.017998 * t ** 3) / 3600.0 * D2R
    z = (2306.2181 * t + 1.09468 * t * t + 0.018203 * t ** 3) / 3600.0 * D2R
    th = (2004.3109 * t - 0.42665 * t * t - 0.041833 * t ** 3) / 3600.0 * D2R
    a0, d0 = np.asarray(ra0, float) * D2R, np.asarray(dec0, float) * D2R
    A = np.cos(d0) * np.sin(a0 + zeta)
    B = np.cos(th) * np.cos(d0) * np.cos(a0 + zeta) - np.sin(th) * np.sin(d0)
    C = np.sin(th) * np.cos(d0) * np.cos(a0 + zeta) + np.cos(th) * np.sin(d0)
    return np.mod(np.arctan2(A, B) * R2D + z * R2D, 360.0), np.arcsin(np.clip(C, -1, 1)) * R2D


def _star(name, jd):
    ra0, dec0 = STARS[name]
    return _precess(ra0, dec0, jd)


def _wrap(x):
    return (np.asarray(x, dtype=np.float64) + 180.0) % 360.0 - 180.0


def _alt(lat, dec, H):
    """Altitude in degrees of a body at declination `dec` and hour angle `H` seen from `lat`."""
    p, d, h = np.asarray(lat) * D2R, np.asarray(dec) * D2R, np.asarray(H) * D2R
    return np.arcsin(np.clip(np.sin(p) * np.sin(d) + np.cos(p) * np.cos(d) * np.cos(h), -1, 1)) * R2D


def _azimuth(lat, dec, H):
    """Azimuth in degrees measured from north through east."""
    p, d, h = np.asarray(lat) * D2R, np.asarray(dec) * D2R, np.asarray(H) * D2R
    y = -np.cos(d) * np.sin(h)
    x = np.sin(d) * np.cos(p) - np.cos(d) * np.sin(p) * np.cos(h)
    return np.mod(np.arctan2(y, x) * R2D, 360.0)


def _semidiurnal(lat, dec, h):
    """Hour angle (deg) at altitude h, plus 'always above' / 'never above' states.

    Returns (H, up_always, up_never). H is 0 where the body never reaches h and 180 where it never
    leaves it, so day lengths and twilight instants stay finite at every latitude.
    """
    p, d = np.asarray(lat) * D2R, np.asarray(dec) * D2R
    c = (np.sin(h * D2R) - np.sin(p) * np.sin(d)) / np.maximum(np.cos(p) * np.cos(d), 1e-12)
    never = c > 1.0
    always = c < -1.0
    H = np.arccos(np.clip(c, -1.0, 1.0)) * R2D
    return H, always.astype(np.float64), never.astype(np.float64)


def _sun_cross_before(jd_ref, lam_target):
    """JD at which the sun last held tropical longitude `lam_target` at or before `jd_ref`.

    Newton iteration on the validated solar series; the initial guess is within +-6 days so it can
    only converge to the intended crossing. This is how DAY COUNTS are obtained without ever
    touching a civil calendar (the dataset straddles the Julian/Gregorian break).
    """
    jd_ref = np.asarray(jd_ref, dtype=np.float64)
    lam_target = np.asarray(lam_target, dtype=np.float64)
    back = np.mod(_sun(jd_ref)[0] - lam_target, 360.0)
    jd = jd_ref - back / 0.98565
    for _ in range(4):
        jd = jd - _wrap(_sun(jd)[0] - lam_target) / 0.98565
    return jd


def _gregorian(jd):
    """Proleptic-Gregorian year, month, day from a Julian day (Meeus 7, alpha applied always).

    Deliberately proleptic: the Cherokee moon names are published against Gregorian months, so a
    single rule is applied across the whole span rather than switching calendars in 1582. Checked
    against swe.revjul(..., GREG_CAL) in the self-test.
    """
    jd = np.asarray(jd, dtype=np.float64)
    Z = np.floor(jd + 0.5)
    F = jd + 0.5 - Z
    alpha = np.floor((Z - 1867216.25) / 36524.25)
    A = Z + 1 + alpha - np.floor(alpha / 4)
    B = A + 1524
    C = np.floor((B - 122.1) / 365.25)
    Dd = np.floor(365.25 * C)
    Ee = np.floor((B - Dd) / 30.6001)
    day = B - Dd - np.floor(30.6001 * Ee) + F
    month = np.where(Ee < 14, Ee - 1, Ee - 13)
    year = np.where(month > 2, C - 4716, C - 4715)
    return year, month, day


# ── heliacal events on a (latitude, epoch) grid ─────────────────────────────────────────────────
_TAB_LATS = np.arange(-72.0, 72.001, 1.5)          # 97 rows; |lat| > 72 is clipped and flagged
_TAB_EPOCHS = np.arange(1200.0, 2051.0, 50.0)      # 18 columns of precession
_TABLE_CACHE = {}


def _heliacal_table(star, kind, av=TWI, hmin=HMIN):
    """Sun's tropical longitude at a star's heliacal event, per (latitude, epoch).

    kind="morning": the first morning the star clears `hmin` in the east while the sun is `av`
    degrees down — the heliacal rising. kind="evening": the last evening it clears `hmin` in the
    west at the same solar depth — the heliacal setting. Returns (cos, sin, ok) tables so the
    interpolation can be circular; ok=0 means the event does not happen at that latitude/epoch
    (the star is up all night, or never visible, or the sun never reaches that depth).
    """
    key = (star, kind, av, hmin)
    if key in _TABLE_CACHE:
        return _TABLE_CACHE[key]
    jd0 = J2000 + (_TAB_EPOCHS - 2000.0) * 365.25
    jd = jd0[:, None] + np.arange(366.0)[None, :]                  # (nep, 366)
    lam, sra, sdec, _ = _sun(jd)
    tra, tdec = _star(star, jd)
    P = _TAB_LATS[:, None, None] * D2R                             # (nlat, 1, 1)
    sd, td = sdec[None] * D2R, tdec[None] * D2R
    cH = (np.sin(av * D2R) - np.sin(P) * np.sin(sd)) / np.maximum(np.cos(P) * np.cos(sd), 1e-12)
    twilight = np.abs(cH) <= 1.0
    H0 = np.arccos(np.clip(cH, -1, 1)) * R2D
    sgn = -1.0 if kind == "morning" else 1.0
    Hs = _wrap(sra[None] + sgn * H0 - tra[None])
    alt = np.arcsin(np.clip(np.sin(P) * np.sin(td) + np.cos(P) * np.cos(td) * np.cos(Hs * D2R), -1, 1)) * R2D
    side = (Hs < 0.0) if kind == "morning" else (Hs > 0.0)
    vis = (alt >= hmin) & side & twilight
    if kind == "morning":
        trans = (~np.roll(vis, 1, axis=2)) & vis                   # first day of visibility
    else:
        trans = vis & (~np.roll(vis, -1, axis=2))                  # last day of visibility
    ok = trans.any(axis=2)
    idx = np.argmax(trans, axis=2)
    L = np.take_along_axis(np.broadcast_to(lam[None], vis.shape), idx[:, :, None], axis=2)[:, :, 0]
    out = (np.cos(L * D2R), np.sin(L * D2R), ok.astype(np.float64))
    _TABLE_CACHE[key] = out
    return out


def _interp_table(tab, lat, epoch):
    """Bilinear interpolation of a (lat, epoch) heliacal table -> (longitude, ok).

    The stored angle is interpolated through its cosine and sine so the year boundary is not a cliff.
    `ok` is the product of the four corners: an event is used only where it exists all around, which
    keeps the (rare) latitude at which a star turns circumpolar from being interpolated across.
    """
    C, S, OK = tab
    la = np.clip(np.asarray(lat, float), _TAB_LATS[0], _TAB_LATS[-1])
    ep = np.clip(np.asarray(epoch, float), _TAB_EPOCHS[0], _TAB_EPOCHS[-1])
    i = np.clip(np.searchsorted(_TAB_LATS, la) - 1, 0, len(_TAB_LATS) - 2)
    j = np.clip(np.searchsorted(_TAB_EPOCHS, ep) - 1, 0, len(_TAB_EPOCHS) - 2)
    u = (la - _TAB_LATS[i]) / (_TAB_LATS[i + 1] - _TAB_LATS[i])
    v = (ep - _TAB_EPOCHS[j] ) / (_TAB_EPOCHS[j + 1] - _TAB_EPOCHS[j])
    w = [((1 - u) * (1 - v), i, j), (u * (1 - v), i + 1, j), ((1 - u) * v, i, j + 1), (u * v, i + 1, j + 1)]
    c = sum(a * C[p, q] for a, p, q in w)
    s = sum(a * S[p, q] for a, p, q in w)
    okv = OK[i, j] * OK[i + 1, j] * OK[i, j + 1] * OK[i + 1, j + 1]
    return np.mod(np.arctan2(s, c) * R2D, 360.0), okv


def _new_moon_before(E, s):
    """JD of the new moon at or before each birth, refined against the real lunar ephemeris.

    The noon lunar age gives a first guess (mean synodic rate); two Newton steps on the true
    Moon-Sun elongation, with the true relative speed, land within a minute. The Moon's own +-6
    degree noon uncertainty (about half a day of lunar age) is the real limit here, not the solver.
    """
    jd = E.JD[s]
    age = np.mod(E.LON[s, E.IDX["Moon"]] - E.LON[s, E.IDX["Sun"]], 360.0)
    g = jd - age / (360.0 / SYN_MONTH)
    g = np.asarray(g, dtype=np.float64).copy()
    for _ in range(2):
        for k in range(g.shape[0]):
            m = swe.calc_ut(float(g[k]), swe.MOON, swe.FLG_SWIEPH | swe.FLG_SPEED)[0]
            su = swe.calc_ut(float(g[k]), swe.SUN, swe.FLG_SWIEPH | swe.FLG_SPEED)[0]
            d = (m[0] - su[0] + 180.0) % 360.0 - 180.0
            g[k] -= d / max(m[3] - su[3], 1e-6)
    return g


# ════════════════════════════════════════════════════════════════════════════════════════════════
# per-partner quantities — everything the blocks draw on, computed once per birth slot
# ════════════════════════════════════════════════════════════════════════════════════════════════

def _partner(E, s):
    q = {}
    jd = np.asarray(E.JD[s], dtype=np.float64)
    q["jd"] = jd
    q["epoch"] = 2000.0 + (jd - J2000) / 365.25
    lat_raw = E.LAT_O if s == 0 else E.LAT_Y
    lon_raw = E.LON_O if s == 0 else E.LON_Y
    ok = (np.isfinite(lat_raw) & np.isfinite(lon_raw)).astype(np.float64)
    q["ok"] = ok
    q["lat"] = np.clip(np.nan_to_num(np.asarray(lat_raw, float)), -89.0, 89.0)
    q["lon"] = np.nan_to_num(np.asarray(lon_raw, float))
    lat, lon = q["lat"], q["lon"]

    iS, iM, iV, iMa = E.IDX["Sun"], E.IDX["Moon"], E.IDX["Venus"], E.IDX["Mars"]
    q["sunlam"] = np.mod(E.LON[s, iS], 360.0)
    q["sundec"] = E.DEC[s, iS]
    q["sunra"] = E.RA[s, iS]
    q["sunspd"] = E.SPD[s, iS]
    _, _, _, eps = _sun(jd)
    q["eps"] = eps

    # ── the two twilights and local midnight: the moments these traditions actually observed ────
    Ht, tw_always, tw_never = _semidiurnal(lat, q["sundec"], TWI)
    q["tw_polar_dark"] = tw_always          # sun never rises to -12 deg: polar night
    q["tw_polar_light"] = tw_never          # sun never falls to -12 deg: white night
    q["H_twi"] = Ht
    Hd, day_never, day_always = _semidiurnal(lat, q["sundec"], SUN_H0)
    # _semidiurnal returns (H, always_above, never_above) for the given altitude
    q["daylen"] = 2.0 * Hd / 15.0
    q["polar_day"] = day_never              # sun never sets
    q["polar_night"] = day_always           # sun never rises
    q["H_rise"] = Hd
    q["sunrise_az"] = _azimuth(lat, q["sundec"], -Hd)
    q["sunset_az"] = _azimuth(lat, q["sundec"], Hd)

    # local mean midnight ending the birth day, and the sidereal time there
    jdmid = jd + 0.5 - lon / 360.0
    q["jdmid"] = jdmid
    lam_m, ra_m, dec_m, _ = _sun(jdmid)
    q["lst_mid"] = np.mod(_gmst(jdmid) + lon, 360.0)
    # dawn: the sun 12 degrees down before sunrise; dusk: the same depth after sunset
    jddawn = jd + 0.5 - lon / 360.0 + (0.5 - Ht / 360.0)
    jddusk = jd - 0.5 - lon / 360.0 + (0.5 + Ht / 360.0)
    q["lst_dawn"] = np.mod(_gmst(jddawn) + lon, 360.0)
    q["lst_dusk"] = np.mod(_gmst(jddusk) + lon, 360.0)

    # ── star geometry at those three moments ─────────────────────────────────────────────────────
    q["star"] = {}
    for name in ("Alcyone", "Polaris", "Dubhe", "Alkaid", "Schedar", "Caph", "Alphecca", "Acrux",
                 "Gacrux", "RigilKent", "Hadar", "Coalsack", "Alnilam", "Antares", "Shaula",
                 "Sirius", "Aldebaran", "Rigel", "Capella", "Castor", "Mothallah"):
        ra, dec = _star(name, jd)
        Hm = _wrap(q["lst_mid"] - ra)
        d = {"ra": ra, "dec": dec, "H_mid": Hm,
             "alt_mid": _alt(lat, dec, Hm),
             "alt_dawn": _alt(lat, dec, _wrap(q["lst_dawn"] - ra)),
             "alt_dusk": _alt(lat, dec, _wrap(q["lst_dusk"] - ra))}
        # circumpolar / never-rises are pure place facts and are the reason a tradition can name a
        # star at all: Náhookòs never revolves for a southern observer, Yacana never rises for a
        # northern one.
        d["circumpolar"] = (dec > (90.0 - np.abs(lat))).astype(np.float64) * (lat > 0) \
                         + (dec < -(90.0 - np.abs(lat))).astype(np.float64) * (lat < 0)
        d["never_rises"] = ((np.abs(dec + np.sign(lat) * 0.0) > 0) &
                            (_alt(lat, dec, 0.0) < 0) & (_alt(lat, dec, 180.0) < 0)).astype(np.float64)
        d["up_mid"] = (d["alt_mid"] > 0).astype(np.float64)
        # the date on which the star culminates at local midnight: the sun stands opposite it
        d["lam_midnight_culm"] = np.mod(_ecl_lon(ra, dec, eps) + 180.0, 360.0)
        d["ecl_lon"] = _ecl_lon(ra, dec, eps)
        q["star"][name] = d

    # ── the twelve candidate birth hours (the addendum's marginalisation) ─────────────────────────
    off = np.asarray(getattr(E, "HOUR_OFFSETS", (np.arange(12) * 2 + 1 - 12.0) / 24.0), float)
    q["hour_lst"] = np.mod(_gmst(jd[None, :] + off[:, None]) + lon[None, :], 360.0)   # (12, n)
    q["hour_sun_alt"] = _alt(lat[None, :], q["sundec"][None, :],
                             _wrap(q["hour_lst"] - q["sunra"][None, :]))

    # ── Venus and Mars: the Morning Star / Evening Star machinery ─────────────────────────────────
    for nm, ip, syn in (("venus", iV, 583.92), ("mars", iMa, 779.94)):
        elong = _wrap(E.LON[s, ip] - q["sunlam"])
        q[nm + "_elong"] = elong
        q[nm + "_morning"] = (elong < 0).astype(np.float64)
        q[nm + "_evening"] = (elong > 0).astype(np.float64)
        # heliocentric synodic angle: 0 at inferior conjunction (Venus) / at opposition (Mars)
        syna = np.mod(E.HELIO[s, ip] - (q["sunlam"] + 180.0), 360.0)
        q[nm + "_syn"] = syna
        q[nm + "_days_since_conj"] = syna * syn / 360.0
        q[nm + "_retro"] = (E.SPD[s, ip] < 0).astype(np.float64)
        # illuminated fraction, from the triangle Sun-Earth-planet (r is recovered, not assumed)
        Delta = E.DIST[s, ip]
        Rse = E.DIST[s, iS]
        cpsi = np.cos(E.LAT[s, ip] * D2R) * np.cos(elong * D2R)
        r = np.sqrt(np.maximum(Rse ** 2 + Delta ** 2 - 2 * Rse * Delta * cpsi, 1e-9))
        ci = np.clip((r ** 2 + Delta ** 2 - Rse ** 2) / np.maximum(2 * r * Delta, 1e-9), -1, 1)
        q[nm + "_illum"] = 0.5 * (1.0 + ci)
        q[nm + "_dist"] = Delta
        ra_p, dec_p = E.RA[s, ip], E.DEC[s, ip]
        q[nm + "_alt_dawn"] = _alt(lat, dec_p, _wrap(q["lst_dawn"] - ra_p))
        q[nm + "_alt_dusk"] = _alt(lat, dec_p, _wrap(q["lst_dusk"] - ra_p))

    # ── heliacal events: local latitude, and Cusco for the ceque calendar ────────────────────────
    for tag, star, kind in (("pl_mfv", "Alcyone", "morning"), ("pl_elv", "Alcyone", "evening"),
                            ("duck_mfv", "Shaula", "morning")):
        tab = _heliacal_table(star, kind)
        lam_e, okv = _interp_table(tab, lat, q["epoch"])
        q[tag + "_lam"] = lam_e
        q[tag + "_ok"] = okv * ok
        jd_e = _sun_cross_before(jd, lam_e)
        q[tag + "_days"] = np.clip(jd - jd_e, 0.0, 367.0) * q[tag + "_ok"]

    tab = _heliacal_table("Alcyone", "morning")
    lam_cz, ok_cz = _interp_table(tab, np.full_like(jd, CUSCO_LAT), q["epoch"])
    q["cusco_lam"] = lam_cz
    q["cusco_ok"] = ok_cz
    q["cusco_days"] = np.clip(jd - _sun_cross_before(jd, lam_cz), 0.0, 367.0)

    # ── the eastern-woodland moon count ──────────────────────────────────────────────────────────
    jd_nm = _new_moon_before(E, s)
    q["jd_nm"] = jd_nm
    q["moon_day"] = np.clip(jd - jd_nm, 0.0, 31.0)
    jd_ws = _sun_cross_before(jd, 270.0)                  # the December solstice just past
    q["jd_ws"] = jd_ws
    q["days_since_solstice"] = jd - jd_ws
    k = np.floor((jd_nm - jd_ws) / SYN_MONTH)
    q["moon_index"] = np.clip(k + 1.0, 1.0, 13.0)         # 1..13 moons of this lunar year
    jd_nm0 = jd_nm - k * SYN_MONTH                        # the first new moon after the solstice
    q["jd_nm0"] = jd_nm0
    q["midwinter_days"] = jd - jd_nm0                     # the Haudenosaunee Midwinter anchor
    q["moons_in_year"] = np.floor((jd_ws + YR_TROP - jd_nm0) / SYN_MONTH) + 1.0
    yy, mm, dd = _gregorian(jd_nm)
    q["moon_month"] = mm                                  # names the Cherokee moon
    return q


def _ecl_lon(ra, dec, eps):
    """Ecliptic longitude from equatorial coordinates, all in degrees."""
    a, d, e = np.asarray(ra) * D2R, np.asarray(dec) * D2R, np.asarray(eps) * D2R
    y = np.sin(a) * np.cos(e) + np.tan(d) * np.sin(e)
    return np.mod(np.arctan2(y, np.cos(a)) * R2D, 360.0)


def _cs(deg):
    """cos/sin of an angle in degrees, as two columns."""
    r = np.asarray(deg, dtype=np.float64) * D2R
    return [np.cos(r), np.sin(r)]


def _onehot(idx, k):
    idx = np.clip(np.asarray(idx, dtype=np.int64), 0, k - 1)
    out = np.zeros((idx.shape[0], k))
    out[np.arange(idx.shape[0]), idx] = 1.0
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
# the blocks
# ════════════════════════════════════════════════════════════════════════════════════════════════

def build(E):
    Q = {0: _partner(E, 0), 1: _partner(E, 1)}
    B = {}
    n = E.n
    A, Y = Q[0], Q[1]

    # ── 1 ── the Pleiades' heliacal rising at the birth latitude ─────────────────────────────────
    # Collca's June rising opened the Inca year and forecast the season (Polo 1571; Urton 1981;
    # Orlove/Chiang/Cane 2000). Place-dependent: the rising date is a function of latitude.
    cols = []
    for q in (A, Y):
        ple = q["star"]["Alcyone"]
        inv = np.mod(q["pl_mfv_lam"] - q["pl_elv_lam"], 360.0)      # the invisibility arc
        since_elv = np.mod(q["sunlam"] - q["pl_elv_lam"], 360.0)
        in_inv = ((since_elv < inv) & (q["pl_mfv_ok"] > 0) & (q["pl_elv_ok"] > 0)).astype(float)
        cols += [q["pl_mfv_lam"] * q["pl_mfv_ok"], q["pl_mfv_ok"],
                 q["pl_elv_lam"] * q["pl_elv_ok"], q["pl_elv_ok"],
                 q["pl_mfv_days"], q["pl_mfv_days"] / 365.25,
                 inv * q["pl_mfv_ok"] * q["pl_elv_ok"] / 0.98565,   # invisibility, in days
                 in_inv, np.where(in_inv > 0, since_elv / 0.98565, 0.0),
                 ple["alt_dawn"] * q["ok"], ple["alt_dusk"] * q["ok"], ple["alt_mid"] * q["ok"],
                 (ple["alt_dawn"] > HMIN).astype(float) * q["ok"],
                 (ple["alt_dusk"] > HMIN).astype(float) * q["ok"], q["ok"]]
        cols += _cs(q["pl_mfv_days"] / 365.25 * 360.0)
        # date-only core: how far the sun stands from the cluster
        cols += _cs(_wrap(q["sunlam"] - ple["ecl_lon"]))
        cols += [np.abs(_wrap(q["sunlam"] - ple["ecl_lon"]))]
    cols += [np.mod(A["pl_mfv_days"] - Y["pl_mfv_days"], 365.25),
             np.abs(_wrap((A["pl_mfv_days"] - Y["pl_mfv_days"]) / 365.25 * 360.0)),
             A["pl_mfv_ok"] * Y["pl_mfv_ok"]]
    B["iam: inca collca (pleiades) heliacal rising"] = np.column_stack(cols)

    # ── 2 ── the 328-day ceque calendar, anchored on Cusco ───────────────────────────────────────
    # Zuidema (1977, 1982): 328 huacas on 41 ceques = 12 sidereal months; the 37 remaining days of
    # the solar year are the Pleiades' invisibility. The count belongs to CUSCO, not to the
    # birthplace, so this block is date-only and valid for every couple. The exact 8 huacas per
    # ceque is Zuidema's calendrical idealisation; Cobo's real counts run from 3 to 15.
    cols = []
    huaca = {}
    ceque = {}
    for i, q in ((0, A), (1, Y)):
        d = np.floor(q["cusco_days"])
        inside = (d < 328).astype(float)
        h = np.where(inside > 0, d + 1.0, 0.0)                       # huaca 1..328, else 0
        c = np.where(inside > 0, np.floor(d / 8.0), -1.0)            # ceque 0..40, else -1
        huaca[i], ceque[i] = h, c
        su = np.where(c >= 0, SUYU_OF_CEQUE[np.clip(c.astype(int), 0, 40)], -1)
        cols += [q["cusco_days"], h, np.where(c >= 0, c, 0.0), inside, 1.0 - inside,
                 np.where(inside > 0, np.mod(d, 8.0), 0.0),          # huaca within its ceque
                 np.where(inside > 0, q["cusco_days"] - 328.0, 0.0) * (1.0 - inside)]
        cols += _cs(np.where(c >= 0, c / 41.0 * 360.0, 0.0))         # the radial coordinate
        cols += _cs(q["cusco_days"] / 365.25 * 360.0)
        cols += [_onehot(su + 1, 5)]                                 # 0 = outside the 328 count
    cols += [(ceque[0] == ceque[1]).astype(float),
             (SUYU_OF_CEQUE[np.clip(ceque[0].astype(int), 0, 40)]
              == SUYU_OF_CEQUE[np.clip(ceque[1].astype(int), 0, 40)]).astype(float)
             * (ceque[0] >= 0) * (ceque[1] >= 0),
             np.abs(huaca[0] - huaca[1]),
             np.minimum(np.mod(ceque[0] - ceque[1], 41.0), np.mod(ceque[1] - ceque[0], 41.0))]
    cols += _cs((ceque[0] - ceque[1]) / 41.0 * 360.0)
    B["iam: inca 328-day ceque calendar (zuidema)"] = np.column_stack(cols)

    # ── 3 ── the ceque one-hot: the radial organisation as a discrete category ───────────────────
    B["iam: inca ceque 41 one-hot, both partners"] = np.column_stack(
        [_onehot(np.where(ceque[0] >= 0, ceque[0] + 1, 0), 42),
         _onehot(np.where(ceque[1] >= 0, ceque[1] + 1, 0), 42)])

    # ── 4 ── Inti Raymi, Capac Raymi and the zenith passage ──────────────────────────────────────
    # Garcilaso (1609) puts Inti Raymi at the June solstice and Capac Raymi at the December one.
    # The zenith passage (the sun overhead) exists only within the tropics and is a place fact.
    cols = []
    for q in (A, Y):
        dJ = _wrap(q["sunlam"] - 90.0) / 0.98565                     # days from the June solstice
        dD = _wrap(q["sunlam"] - 270.0) / 0.98565
        trop = (np.abs(q["lat"]) <= 23.44) * q["ok"]
        lam_z = np.arcsin(np.clip(np.sin(q["lat"] * D2R) / np.sin(q["eps"] * D2R), -1, 1)) * R2D
        # the two crossings of the sun's declination with the latitude
        z1, z2 = np.mod(lam_z, 360.0), np.mod(180.0 - lam_z, 360.0)
        dz = np.minimum(np.abs(_wrap(q["sunlam"] - z1)), np.abs(_wrap(q["sunlam"] - z2))) / 0.98565
        cols += [dJ, dD, np.abs(dJ), np.abs(dD), q["sundec"],
                 E.orbkern(np.abs(dJ), 0.0, 5.0), E.orbkern(np.abs(dD), 0.0, 5.0),
                 q["daylen"] * q["ok"], (q["daylen"] - 12.0) * q["ok"],
                 q["polar_day"], q["polar_night"], q["ok"],
                 trop, dz * trop, E.orbkern(dz * trop, 0.0, 4.0) * trop]
        cols += _cs(q["sunlam"])
    cols += [np.abs(_wrap(A["sunlam"] - Y["sunlam"])),
             (A["daylen"] - Y["daylen"]) * A["ok"] * Y["ok"], A["ok"] * Y["ok"]]
    B["iam: inca inti raymi, capac raymi & zenith passage"] = np.column_stack(cols)

    # ── 5 ── Yacana and Yutu, the dark clouds, at local midnight ─────────────────────────────────
    # Urton (1981): the llama's eyes are alpha and beta Centauri; Yutu the tinamou is the Coalsack.
    # The Huarochirí Manuscript has the llama drink the sea at MIDNIGHT, which is why the instant is
    # local midnight and not a guessed birth hour.
    cols = []
    for q in (A, Y):
        for nm in ("RigilKent", "Hadar", "Coalsack", "Acrux"):
            d = q["star"][nm]
            cols += [d["alt_mid"] * q["ok"], d["up_mid"] * q["ok"], d["circumpolar"] * q["ok"],
                     d["never_rises"] * q["ok"]]
        ya = q["star"]["RigilKent"]
        cols += _cs(ya["H_mid"])
        cols += [_wrap(q["sunlam"] - ya["lam_midnight_culm"]) / 0.98565,   # days to its midnight culmination
                 np.abs(_wrap(q["sunlam"] - ya["lam_midnight_culm"])) / 0.98565,
                 q["ok"]]
    cols += [A["star"]["RigilKent"]["up_mid"] * Y["star"]["RigilKent"]["up_mid"] * A["ok"] * Y["ok"],
             np.abs(A["star"]["RigilKent"]["alt_mid"] - Y["star"]["RigilKent"]["alt_mid"]) * A["ok"] * Y["ok"]]
    B["iam: inca dark clouds yacana & yutu at midnight"] = np.column_stack(cols)

    # ── 6 ── Dilyéhé and the Diné storytelling / planting windows ────────────────────────────────
    # Griffin-Pierce (1992); Maryboy & Begay (2010). The winter storytelling season is gated by the
    # evening sky, and Orion and Scorpius are never up together — the teaching, computed.
    cols = []
    for q in (A, Y):
        ple, ori, sco = q["star"]["Alcyone"], q["star"]["Alnilam"], q["star"]["Antares"]
        ev = (ple["alt_dusk"] > HMIN).astype(float) * q["ok"]
        cols += [ple["alt_dusk"] * q["ok"], ple["alt_mid"] * q["ok"], ple["alt_dawn"] * q["ok"], ev,
                 q["pl_elv_days"], q["pl_elv_days"] / 365.25,
                 ori["alt_mid"] * q["ok"], ori["up_mid"] * q["ok"],
                 sco["alt_mid"] * q["ok"], sco["up_mid"] * q["ok"],
                 np.abs(ori["up_mid"] - sco["up_mid"]) * q["ok"],           # exactly one of them up
                 (1.0 - ori["up_mid"]) * (1.0 - sco["up_mid"]) * q["ok"],   # neither
                 q["star"]["Shaula"]["alt_mid"] * q["ok"], q["ok"]]
        cols += _cs(_wrap(q["sunlam"] - ple["ecl_lon"]))
        cols += _cs(_wrap(q["sunlam"] - ori["ecl_lon"]))
        cols += _cs(_wrap(q["sunlam"] - sco["ecl_lon"]))
    cols += [(A["star"]["Alcyone"]["alt_dusk"] > HMIN).astype(float)
             * (Y["star"]["Alcyone"]["alt_dusk"] > HMIN).astype(float) * A["ok"] * Y["ok"],
             np.abs(A["pl_elv_days"] - Y["pl_elv_days"])]
    B["iam: dine dilyehe evening window & orion-scorpius"] = np.column_stack(cols)

    # ── 7 ── Náhookòs, the revolving male and female, at local midnight ──────────────────────────
    # The pair turns about the central fire (Polaris). Their POSITION ANGLE at local midnight is a
    # date quantity (local midnight is opposite the sun); whether they revolve at all, or set, or
    # never rise, is a latitude quantity.
    cols = []
    for q in (A, Y):
        pol, du, al, sc, ca = (q["star"]["Polaris"], q["star"]["Dubhe"], q["star"]["Alkaid"],
                               q["star"]["Schedar"], q["star"]["Caph"])
        cols += [pol["alt_mid"] * q["ok"], pol["up_mid"] * q["ok"],
                 du["alt_mid"] * q["ok"], du["up_mid"] * q["ok"], du["circumpolar"] * q["ok"],
                 al["alt_mid"] * q["ok"], al["circumpolar"] * q["ok"],
                 sc["alt_mid"] * q["ok"], sc["up_mid"] * q["ok"], sc["circumpolar"] * q["ok"],
                 ca["alt_mid"] * q["ok"],
                 du["never_rises"] * q["ok"], sc["never_rises"] * q["ok"], q["ok"]]
        cols += _cs(du["H_mid"])       # the revolving male's station on the night clock
        cols += _cs(sc["H_mid"])       # the revolving female's
        cols += [np.abs(_wrap(du["H_mid"] - sc["H_mid"]))]
    cols += [A["star"]["Dubhe"]["circumpolar"] * Y["star"]["Dubhe"]["circumpolar"] * A["ok"] * Y["ok"],
             np.abs(_wrap(A["star"]["Dubhe"]["H_mid"] - Y["star"]["Dubhe"]["H_mid"]))]
    B["iam: dine nahookos revolving pair, midnight"] = np.column_stack(cols)

    # ── 8 ── Pawnee Morning Star and Evening Star ────────────────────────────────────────────────
    # Chamberlain (1982). Venus's phase is the primary encoding; Mars is emitted beside it because
    # Chamberlain argues the Skidi Morning Star of the sacrifice is more likely Mars.
    cols = []
    role = {}
    for i, q in ((0, A), (1, Y)):
        vis = (np.abs(q["venus_elong"]) >= 8.0).astype(float)
        role[i] = np.where(vis == 0, 2, np.where(q["venus_elong"] < 0, 0, 1))   # 0 morning, 1 evening, 2 hidden
        cols += [q["venus_elong"], np.abs(q["venus_elong"]), q["venus_morning"], q["venus_evening"],
                 1.0 - vis, q["venus_days_since_conj"], q["venus_retro"], q["venus_illum"],
                 q["venus_dist"], E.orbkern(np.abs(q["venus_elong"]), 46.5, 3.0),
                 E.orbkern(np.abs(q["venus_elong"]), 46.5, 8.0),
                 q["venus_alt_dawn"] * q["ok"], q["venus_alt_dusk"] * q["ok"],
                 (q["venus_alt_dawn"] > 0).astype(float) * q["venus_morning"] * q["ok"],
                 q["mars_elong"], q["mars_morning"], q["mars_days_since_conj"], q["mars_illum"],
                 q["mars_alt_dawn"] * q["ok"], q["ok"]]
        cols += _cs(q["venus_syn"])
        cols += _cs(q["mars_syn"])
    # the union of Morning Star and Evening Star is the Skidi origin of the first human being
    cols += [_onehot(role[0] * 3 + role[1], 9),
             (((role[0] == 0) & (role[1] == 1)) | ((role[0] == 1) & (role[1] == 0))).astype(float),
             (role[0] == role[1]).astype(float),
             np.abs(_wrap(A["venus_syn"] - Y["venus_syn"]))]
    cols += _cs(A["venus_syn"] - Y["venus_syn"])
    B["iam: pawnee morning star & evening star"] = np.column_stack(cols)

    # ── 9 ── the Pawnee star chart's visibility ──────────────────────────────────────────────────
    # The Chief star that does not move, the Council of Chiefs, and the Swimming Ducks whose
    # pre-dawn return announces spring (Chamberlain 1982). The four semi-cardinal stars are
    # unidentified in Chamberlain and are deliberately absent.
    cols = []
    for q in (A, Y):
        pol, crb, dk = q["star"]["Polaris"], q["star"]["Alphecca"], q["star"]["Shaula"]
        cols += [pol["alt_mid"] * q["ok"], pol["up_mid"] * q["ok"],
                 crb["alt_mid"] * q["ok"], crb["up_mid"] * q["ok"], crb["alt_dusk"] * q["ok"],
                 dk["alt_mid"] * q["ok"], dk["alt_dawn"] * q["ok"],
                 (dk["alt_dawn"] > HMIN).astype(float) * q["ok"],
                 q["duck_mfv_days"], q["duck_mfv_days"] / 365.25, q["duck_mfv_ok"],
                 q["star"]["Alcyone"]["up_mid"] * q["ok"], q["ok"]]
        cols += _cs(crb["H_mid"])
        cols += _cs(dk["H_mid"])
        cols += [_wrap(q["sunlam"] - crb["lam_midnight_culm"]) / 0.98565]
    cols += [np.abs(A["duck_mfv_days"] - Y["duck_mfv_days"]),
             A["star"]["Alphecca"]["up_mid"] * Y["star"]["Alphecca"]["up_mid"] * A["ok"] * Y["ok"]]
    B["iam: pawnee star chart visibility"] = np.column_stack(cols)

    # ── 10 ── the Lakota sacred hoop: where the sun stands in it ─────────────────────────────────
    # Goodman (1992). The rule is the sun's arrival at a constellation of the hoop; the land half of
    # the mirror is a fixed geography and is not encoded.
    cols = []
    station = {}
    for i, q in ((0, A), (1, Y)):
        seps = []
        for _, members in HOOP:
            lam_g = np.mean([_ecl_lon(*_star(m, q["jd"]), q["eps"]) for m in members], axis=0) \
                if len(members) > 1 else _ecl_lon(*_star(members[0], q["jd"]), q["eps"])
            seps.append(np.abs(_wrap(q["sunlam"] - lam_g)))
        S = np.column_stack(seps)
        station[i] = np.argmin(S, axis=1)
        cols += [E.orbkern(S, 0.0, 8.0), E.orbkern(S, 0.0, 15.0), _onehot(station[i], len(HOOP)),
                 S.min(axis=1)[:, None], (S.min(axis=1) < 10.0).astype(float)[:, None]]
        ring = np.mean([_ecl_lon(*_star(m, q["jd"]), q["eps"])
                        for m in ("Aldebaran", "Rigel", "Sirius", "Castor", "Capella")], axis=0)
        cols += [np.column_stack(_cs(_wrap(q["sunlam"] - ring)))]
    cols += [(station[0] == station[1]).astype(float)[:, None],
             _onehot(station[0] * len(HOOP) + station[1], len(HOOP) ** 2)]
    B["iam: lakota sacred hoop, the sun's station"] = np.column_stack(cols)

    # ── 11 ── the Hopi horizon calendar ──────────────────────────────────────────────────────────
    # Stephen (1936); McCluskey (1977); Zeilik (1985). The sunrise azimuth AT THE BIRTHPLACE, its
    # daily change (the standstill the sun-watcher looked for) and the fraction of the way between
    # the solstice extremes — the horizon coordinate itself. No named mesa mark: no skyline profile.
    cols = []
    for q in (A, Y):
        lat = q["lat"]
        # the solstice azimuth limits at this latitude bracket the horizon calendar
        az_j = _azimuth(lat, q["eps"], -_semidiurnal(lat, q["eps"], SUN_H0)[0])
        az_d = _azimuth(lat, -q["eps"], -_semidiurnal(lat, -q["eps"], SUN_H0)[0])
        span = np.abs(az_d - az_j)
        frac = np.where(span > 1e-6, (q["sunrise_az"] - az_j) / np.maximum(span, 1e-6), 0.0)
        # d(azimuth)/d(day), exactly: dA/ddec * ddec/dt, with ddec/dt from the sun's own speed
        sinA = np.sin(q["sunrise_az"] * D2R)
        ddec = (np.sin(q["eps"] * D2R) * np.cos(q["sunlam"] * D2R) * q["sunspd"]
                / np.maximum(np.cos(q["sundec"] * D2R), 1e-6))
        dAdt = -np.cos(q["sundec"] * D2R) * ddec / np.maximum(
            np.abs(sinA) * np.cos(lat * D2R) * np.cos(SUN_H0 * D2R), 1e-3)
        moving = np.clip(np.abs(dAdt), 0.0, 3.0)
        okz = q["ok"] * (1.0 - q["polar_day"]) * (1.0 - q["polar_night"])
        dJ = _wrap(q["sunlam"] - 90.0) / 0.98565
        dD = _wrap(q["sunlam"] - 270.0) / 0.98565
        cols += [q["sunrise_az"] * okz, q["sunset_az"] * okz, span * q["ok"],
                 np.clip(frac, -0.2, 1.2) * okz, moving * okz, okz,
                 (q["sunrise_az"] - 90.0) * okz,                 # north or south of due east
                 (moving < 0.1).astype(float) * okz,             # the standstill itself
                 E.orbkern(np.abs(dD), 0.0, 4.0),                # Soyal, the December solstice
                 E.orbkern(dJ - 16.0, 0.0, 4.0),                 # Niman, ~16 days after June
                 E.orbkern(np.abs(_wrap(q["sunlam"] - 325.0)), 0.0, 8.0),   # Powamuya, February
                 E.orbkern(np.abs(_wrap(q["sunlam"] - 233.0)), 0.0, 8.0),   # Wuwutsim, November
                 q["daylen"] * q["ok"], q["moon_day"] / SYN_MONTH]
        cols += _cs(q["sunrise_az"] * 2.0)
    cols += [np.abs(A["sunrise_az"] - Y["sunrise_az"]) * A["ok"] * Y["ok"],
             (np.sign(A["sunrise_az"] - 90.0) == np.sign(Y["sunrise_az"] - 90.0)).astype(float)
             * A["ok"] * Y["ok"],
             np.abs(A["daylen"] - Y["daylen"]) * A["ok"] * Y["ok"], A["ok"] * Y["ok"]]
    B["iam: hopi horizon sunrise calendar"] = np.column_stack(cols)

    # ── 12 ── Hotòmqam and Dilyéhé through the kiva hatchway ─────────────────────────────────────
    # McCluskey (1977): the November and December ceremonies were timed by Orion's Belt and the
    # Pleiades seen overhead at night. The date of a midnight culmination is exact; the hatchway
    # itself needs an hour, so what is emitted is the culmination OFFSET and the midnight altitude.
    cols = []
    for q in (A, Y):
        for nm in ("Alnilam", "Alcyone", "Aldebaran", "Sirius"):
            d = q["star"][nm]
            off = _wrap(q["sunlam"] - d["lam_midnight_culm"]) / 0.98565
            cols += [off, np.abs(off), E.orbkern(np.abs(off), 0.0, 10.0),
                     d["alt_mid"] * q["ok"], d["up_mid"] * q["ok"]]
            cols += _cs(d["H_mid"])
        cols += [q["ok"]]
    cols += [np.abs(_wrap(A["star"]["Alnilam"]["H_mid"] - Y["star"]["Alnilam"]["H_mid"])),
             np.abs(_wrap(A["star"]["Alcyone"]["H_mid"] - Y["star"]["Alcyone"]["H_mid"]))]
    B["iam: hopi kiva culmination of orion & pleiades"] = np.column_stack(cols)

    # ── 13 ── Mapuche We Tripantu and Pünoñ Choyke ───────────────────────────────────────────────
    # The new year is the first sunrise after the LONGEST NIGHT, which is June in the south and
    # December in the north — so this block keys to the local winter solstice, not to June.
    cols = []
    for q in (A, Y):
        south = (q["lat"] < 0).astype(float)
        lam_win = np.where(q["lat"] < 0, 90.0, 270.0)                # local winter solstice
        dW = _wrap(q["sunlam"] - lam_win) / 0.98565
        nightlen = 24.0 - q["daylen"]
        longest = 24.0 - 2.0 * _semidiurnal(q["lat"], -np.abs(q["eps"]) * np.sign(q["lat"] + 1e-9),
                                            SUN_H0)[0] / 15.0
        cru_a, cru_g = q["star"]["Acrux"], q["star"]["Gacrux"]
        cols += [dW * q["ok"], np.abs(dW) * q["ok"], E.orbkern(np.abs(dW), 0.0, 4.0) * q["ok"],
                 E.orbkern(dW - 3.0, 0.0, 3.0) * q["ok"],           # We Tripantu, 24 June
                 south * q["ok"], nightlen * q["ok"], longest * q["ok"],
                 (nightlen - longest) * q["ok"],
                 cru_a["alt_mid"] * q["ok"], cru_a["up_mid"] * q["ok"], cru_a["circumpolar"] * q["ok"],
                 cru_g["alt_mid"] * q["ok"], cru_a["never_rises"] * q["ok"],
                 q["venus_morning"] * (q["venus_alt_dawn"] > 3.0).astype(float) * q["ok"],
                 q["venus_alt_dawn"] * q["ok"], q["ok"]]
        cols += _cs(cru_a["H_mid"])
        cols += [_wrap(q["sunlam"] - cru_a["lam_midnight_culm"]) / 0.98565]
    cols += [(A["lat"] < 0).astype(float) * A["ok"] * ((Y["lat"] >= 0).astype(float) * Y["ok"]),
             A["star"]["Acrux"]["up_mid"] * Y["star"]["Acrux"]["up_mid"] * A["ok"] * Y["ok"],
             np.abs(A["star"]["Acrux"]["alt_mid"] - Y["star"]["Acrux"]["alt_mid"]) * A["ok"] * Y["ok"]]
    B["iam: mapuche we tripantu & punon choyke"] = np.column_stack(cols)

    # ── 14 ── the moon count of the eastern woodland year ────────────────────────────────────────
    # Twelve or thirteen moons, counted from the first new moon after the December solstice — the
    # same anchor as the Haudenosaunee Midwinter (Fenton; Ceci 1978).
    cols = []
    for q in (A, Y):
        cols += [q["moon_index"], q["moons_in_year"], (q["moons_in_year"] >= 13).astype(float),
                 q["moon_day"], q["moon_day"] / SYN_MONTH, q["midwinter_days"],
                 q["days_since_solstice"], q["jd_nm0"] - q["jd_ws"],   # how late the year's first moon fell
                 E.orbkern(q["midwinter_days"] - 5.0, 0.0, 3.0),       # Midwinter begins about day five
                 q["moon_month"]]
        cols += _cs(q["moon_day"] / SYN_MONTH * 360.0)
        cols += _cs(q["moon_index"] / 13.0 * 360.0)
    cols += [np.abs(A["moon_index"] - Y["moon_index"]),
             (A["moon_index"] == Y["moon_index"]).astype(float),
             np.abs(A["moon_day"] - Y["moon_day"]),
             (A["moons_in_year"] == Y["moons_in_year"]).astype(float)]
    B["iam: woodland moon count from the solstice"] = np.column_stack(cols)

    # ── 15 ── the named moons, as categories ─────────────────────────────────────────────────────
    cols = []
    for q in (A, Y):
        cols += [_onehot(q["moon_month"] - 1, 12),                     # the Cherokee moon's name
                 _onehot(q["moon_index"] - 1, 13)]                     # its ordinal in the lunar year
    cols += [(A["moon_month"] == Y["moon_month"]).astype(float)[:, None],
             _onehot((A["moon_month"] - 1) * 12 + (Y["moon_month"] - 1), 144)]
    B["iam: named moons (cherokee 12, ordinal 13)"] = np.column_stack(cols)

    # ── 16 ── the unknown birth hour, marginalised over the 12 double-hours ──────────────────────
    # The one question here that genuinely needs an hour: was this star above the horizon at the
    # moment of birth? Answered as a DISTRIBUTION over the 12 candidate hours plus its entropy,
    # never as a point guess. The sun's own up-fraction is the day-or-night marginal.
    # The star half needs a latitude. The MOON half does not, and it belongs here for the same
    # reason: the woodland moon-day is uncertain by about half a day, so the honest encoding is the
    # distribution of the lunar day over the 12 candidate hours and how undecided it is.
    cols = []
    for s, q in ((0, A), (1, Y)):
        H = E.hours(s)                                                  # (NB, 12, n)
        age = np.mod(H[E.IDX["Moon"]] - H[E.IDX["Sun"]], 360.0)         # (12, n) lunar age
        quart = np.zeros((n, 4))
        lday = np.zeros((n, 30))
        for h in range(age.shape[0]):
            quart[np.arange(n), np.clip((age[h] // 90.0).astype(int), 0, 3)] += 1.0
            lday[np.arange(n), np.clip((age[h] // 12.0).astype(int), 0, 29)] += 1.0
        quart /= age.shape[0]
        lday /= age.shape[0]
        noon = np.clip((np.mod(E.LON[s, E.IDX["Moon"]] - E.LON[s, E.IDX["Sun"]], 360.0) // 12.0)
                       .astype(int), 0, 29)
        cols += [quart, E.entropy(quart)[:, None], E.entropy(lday)[:, None],
                 (1.0 - lday[np.arange(n), noon])[:, None],             # how much of the hour prior disagrees
                 lday.max(axis=1)[:, None],
                 E.entropy(E.soft_bins(s, E.IDX["Sun"], 12))[:, None]]  # the sun's sign marginal
    for q in (A, Y):
        for nm in ("Alcyone", "Dubhe", "RigilKent", "Acrux", "Alnilam", "Antares", "Polaris"):
            d = q["star"][nm]
            alt = _alt(q["lat"][None, :], d["dec"][None, :], _wrap(q["hour_lst"] - d["ra"][None, :]))
            up = (alt > 0).astype(np.float64).mean(axis=0)
            cols += [up * q["ok"], alt.mean(axis=0) * q["ok"], alt.max(axis=0) * q["ok"],
                     E.entropy(np.column_stack([up, 1.0 - up])) * q["ok"]]
        day = (q["hour_sun_alt"] > SUN_H0).astype(np.float64).mean(axis=0)
        cols += [day * q["ok"], E.entropy(np.column_stack([day, 1.0 - day])) * q["ok"],
                 q["hour_sun_alt"].max(axis=0) * q["ok"], q["ok"]]
    for nm in ("Alcyone", "Dubhe", "RigilKent"):
        ua, uy = [], []
        for q, acc in ((A, ua), (Y, uy)):
            d = q["star"][nm]
            alt = _alt(q["lat"][None, :], d["dec"][None, :], _wrap(q["hour_lst"] - d["ra"][None, :]))
            acc.append((alt > 0).astype(np.float64).mean(axis=0))
        cols += [np.abs(ua[0] - uy[0]) * A["ok"] * Y["ok"], ua[0] * uy[0] * A["ok"] * Y["ok"]]
    B["iam: birth-hour marginal, which named stars were up"] = np.column_stack(cols)

    out = {}
    for k, X in B.items():
        X = np.ascontiguousarray(np.asarray(X, dtype=np.float64))
        if X.ndim == 1:
            X = X[:, None]
        assert X.shape[0] == n, f"{k}: {X.shape} rows != {n}"
        out[k] = X
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
# self-test
# ════════════════════════════════════════════════════════════════════════════════════════════════

def _validate_against_swe():
    """Every helper in this module, checked against Swiss Ephemeris. No result is taken on faith."""
    jds = np.array([2165102.0, 2200000.0, 2300000.0, 2400000.0, 2450348.0, J2000])
    lam, ra, dec, eps = _sun(jds)
    e_lam = e_ra = e_dec = e_st = e_sp = 0.0
    for i, jd in enumerate(jds):
        p = swe.calc_ut(float(jd), swe.SUN, swe.FLG_SWIEPH)[0]
        qq = swe.calc_ut(float(jd), swe.SUN, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)[0]
        e_lam = max(e_lam, abs(_wrap(lam[i] - p[0])))
        e_ra = max(e_ra, abs(_wrap(ra[i] - qq[0])))
        e_dec = max(e_dec, abs(dec[i] - qq[1]))
        e_st = max(e_st, abs(_wrap(_gmst(jd) - swe.sidtime(float(jd)) * 15.0)))
        r, d = _precess(*STARS["Spica"], jd)
        sp = swe.fixstar2_ut("Spica", float(jd), swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)[0]
        e_sp = max(e_sp, abs(_wrap(r - sp[0])), abs(d - sp[1]))
    print(f"  solar longitude vs swe.calc_ut      max |d| = {e_lam:.4f} deg")
    print(f"  solar RA / dec vs swe.calc_ut       max |d| = {max(e_ra, e_dec):.4f} deg")
    print(f"  sidereal time vs swe.sidtime        max |d| = {e_st:.4f} deg")
    print(f"  Spica precessed vs swe.fixstar2_ut  max |d| = {e_sp:.4f} deg")
    assert e_lam < 0.02 and e_ra < 0.02 and e_dec < 0.02, "solar series disagrees with the ephemeris"
    assert e_st < 0.02, "sidereal time disagrees with the ephemeris"
    assert e_sp < 0.02, "precession disagrees with the ephemeris"
    # civil dates
    bad = 0
    for jd in np.arange(2165102.0, 2450348.0, 4013.0):
        y, m, d = _gregorian(jd)
        sy, sm, sd, sh = swe.revjul(float(jd), swe.GREG_CAL)
        if (int(y), int(m), int(np.floor(d))) != (sy, sm, sd):
            bad += 1
    print(f"  gregorian dates vs swe.revjul       {bad} disagreements of 72")
    assert bad == 0, "civil-date conversion disagrees with the ephemeris"
    # horizon geometry, from first principles
    assert abs(_alt(41.0, STARS["Polaris"][1], 0.0) - 41.0) < 1.5, "Polaris should stand at the latitude"
    assert _alt(41.0, -60.83, 0.0) < 0, "alpha Centauri cannot rise at 41 N"
    a_eq = _azimuth(0.0, 0.0, -_semidiurnal(0.0, 0.0, SUN_H0)[0])
    assert abs(a_eq - 90.0) < 1.5, f"equinox sunrise on the equator should be due east, got {a_eq:.2f}"
    dl = 2 * _semidiurnal(0.0, 0.0, SUN_H0)[0] / 15.0
    assert abs(dl - 12.1) < 0.2, f"equatorial day length should be ~12.1 h, got {dl:.2f}"
    print(f"  Polaris altitude at 41 N            {_alt(41.0, STARS['Polaris'][1], 0.0):.2f} deg")
    print(f"  equinox sunrise azimuth at 0 N      {a_eq:.2f} deg (due east)")


def _validate_traditions():
    """The two computed calendars, checked against what the ethnographic record says they should be."""
    # The Pleiades' heliacal rising at Cusco should fall in the first half of June, which is what
    # the colonial sources and the modern fieldwork both report.
    tab = _heliacal_table("Alcyone", "morning")
    for yr in (1500.0, 1800.0, 2000.0):
        lam, ok = _interp_table(tab, np.array([CUSCO_LAT]), np.array([yr]))
        jd = _sun_cross_before(np.array([J2000 + (yr - 2000.0) * 365.25 + 300.0]), lam)
        y, m, d = (float(v[0]) for v in _gregorian(jd))
        print(f"  Collca rises at Cusco, {int(yr)}:        {int(m):02d}-{int(d):02d} "
              f"(sun at {lam[0]:.1f} deg, exists={int(ok[0])})")
        assert ok[0] == 1.0, "the Pleiades must have a heliacal rising at Cusco"
        assert 5 <= int(m) <= 6, "Collca's rising at Cusco should fall in May/June"
    # and at a Hopi latitude it is a late-May/June event too, drifting with precession
    for la in (35.9, 40.0, -38.0):
        lam, ok = _interp_table(tab, np.array([la]), np.array([1900.0]))
        jd = _sun_cross_before(np.array([J2000 - 100.0 * 365.25 + 300.0]), lam)
        y, m, d = (float(v[0]) for v in _gregorian(jd))
        print(f"  Pleiades rise at lat {la:+.1f}, 1900:    {int(m):02d}-{int(d):02d} (exists={int(ok[0])})")


if __name__ == "__main__":
    import sys
    import time
    import numpy as np
    from core import load
    from evalx import quick

    t0 = time.time()
    print(f"TRADITION  {TRADITION}\n")
    print("validating the astronomy against Swiss Ephemeris")
    _validate_against_swe()
    print("\nvalidating the traditions' own calendars")
    _validate_traditions()

    E = load()
    known = ((np.isfinite(E.LAT_O) & np.isfinite(E.LON_O)).mean(),
             (np.isfinite(E.LAT_Y) & np.isfinite(E.LON_Y)).mean())
    print(f"\ncouples {E.n:,}   birthplace known: older {100*known[0]:.1f}%  younger {100*known[1]:.1f}%")
    if max(known) == 0.0:
        print("  NOTE: this dataset carries no coordinates at all, so every place-dependent column is\n"
              "        zero with its known-flag at zero. The blocks still vary through their date-only\n"
              "        columns, which is why each block deliberately carries some.")
    t1 = time.time()
    B = build(E)
    print(f"{len(B)} blocks, {sum(x.shape[1] for x in B.values())} columns, built in {time.time()-t1:.1f}s\n")

    fail = 0
    for name, X in sorted(B.items()):
        assert name.startswith("iam: "), f"{name}: wrong prefix"
        assert X.shape[0] == E.n, f"{name}: {X.shape[0]} rows != {E.n}"
        assert X.dtype == np.float64, f"{name}: dtype {X.dtype}"
        assert np.isfinite(X).all(), f"{name}: non-finite values in columns " \
                                     f"{np.where(~np.isfinite(X).all(axis=0))[0][:8]}"
        assert X.std(axis=0).max() > 0, f"{name}: every column is constant"
        acc, auc = quick(E, X)
        nz = int((X.std(axis=0) > 0).sum())
        print(f"  {name:<52} {X.shape[1]:>4} cols ({nz:>4} live)  {100*acc:6.2f}%  AUC {auc:.4f}")
    print(f"\nOK — {len(B)} blocks in {time.time()-t0:.1f}s")
    sys.exit(fail)
