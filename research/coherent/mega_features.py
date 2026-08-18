"""
mega_features.py — thousands of NAMED single-number astrology and numerology features, across all traditions.

Every feature is one number per couple, with a name that says what it is and a sentence that says how it was
computed. Families are yielded ONE AT A TIME so the driver can score and discard them: holding five thousand
columns for both halves at once would be about 1.6 GB, and there is no reason to.

DAY PRECISION IS REQUIRED, and this is a correction to earlier runs. `dates.concrete()` maps a year-only date
like `1856-00-00` onto 1 January so that a chart can be cast at all. That is right for the trainer, which also
passes a precision flag and a century-wide window, but it is WRONG as an input to a longitude: the Sun would be
recorded at roughly 280 degrees for every such couple, planting a false spike at day 1 in every seasonal
feature and a false mode in every sign. An earlier ranking here used all rows with both years known and was
contaminated by exactly that. Only couples with BOTH dates to the day are used now — 27,189 of the training
half — which also matches the held-out half, day-precision by construction.

THE FAMILIES

  single body        each of 18 bodies in each chart: tropical and sidereal longitude as cos/sin, sign, decan,
                     dwadasamsa, nakshatra, navamsa, degree within sign, daily speed, retrogradation
  harmonic charts    each body's longitude multiplied by 5, 7 and 9 and rewrapped — the harmonic charts of
                     Addey and the Vedic vargas share this construction
  cross-chart        all 18x18 ordered body pairs between the two charts, as raw separation and as cos of
                     harmonics 1-6. This is the entire synastry grid, and its two-body case is the classical
                     aspect: |e^ia + e^ib|^2 = 2 + 2cos(a-b)
  natal aspects      all 153 body pairs inside each partner's own chart, harmonics 1-3
  midpoints          the Uranian midpoint of every classical pair, in both charts, and its cross-chart contacts
  antiscia           the solstice-mirror of each body and its cross-chart contacts
  lunar              each body's elongation from its own Sun, and the two charts' difference
  vargas             the divisional-chart sign of each classical body for D2 D3 D7 D9 D10 D12 D16 D20 D24 D27
                     D30 D60, plus same-varga-sign agreement across the two charts
  vedic pair         nakshatra distance for every body, not only the Moon
  chinese            sexagenary year stem and branch, the day pillar, and the pair relations that Chinese
                     practice reads: san-he trines, the liu-chong clash, stem elements
  calendrical        weekday and its Chaldean planetary ruler, day of the year and its harmonics, seasonal
                     separation, sun-sign compatibility in the forms people actually use
  numerology         Life Path, Birthday, Attitude, the pillars, Chaldean reduction, karmic-debt numbers,
                     challenge and pinnacle numbers, Personal Year/Month/Day, and the pair readings
"""
import numpy as np

NAMES18 = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
           "TrueNode", "MeanNode", "Lilith", "Chiron", "Ceres", "Pallas", "Juno", "Vesta"]
IDX = {n: i for i, n in enumerate(NAMES18)}
CLASSICAL = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces"]
ANIMALS = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
DAYLORD = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
STEM_EL = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]
MEANS = {
    "Sun": "identity and vitality", "Moon": "feeling and habit", "Mercury": "speech and reasoning",
    "Venus": "attraction and what is valued", "Mars": "desire and conflict",
    "Jupiter": "expansion and generosity", "Saturn": "duty and endurance, the marriage significator",
    "Uranus": "disruption", "Neptune": "idealisation", "Pluto": "compulsion",
    "TrueNode": "the true lunar node", "MeanNode": "the mean lunar node", "Lilith": "the lunar apogee",
    "Chiron": "the wound", "Ceres": "nurture", "Pallas": "strategy", "Juno": "the marriage asteroid",
    "Vesta": "devotion",
}
VARGA = {2: "hora (wealth)", 3: "drekkana (siblings)", 7: "saptamsa (children)",
         9: "navamsa (the spouse chart)", 10: "dasamsa (career)", 12: "dwadasamsa (parents)",
         16: "shodasamsa (vehicles)", 20: "vimsamsa (devotion)", 24: "siddhamsa (learning)",
         27: "bhamsa (strengths)", 30: "trimsamsa (misfortune)", 60: "shashtiamsa (the whole)"}
SLOTS = (("older", 0), ("younger", 1))


def _fold(d, p=360.0):
    d = np.mod(d, p)
    return np.minimum(d, p - d)


def families(E, dates=None):
    """Yield (family_name, {feature_name: (explanation, values)}) one family at a time."""
    LON = np.asarray(E.LON, dtype=np.float64)
    SPD = np.asarray(getattr(E, "SPD", np.zeros_like(LON)), dtype=np.float64)
    rad = np.pi / 180.0
    try:
        SID = np.asarray(E.sidereal("Lahiri"), dtype=np.float64)
    except Exception:
        SID = None

    # ── single body ───────────────────────────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for b in NAMES18:
            i = IDX[b]
            lam = np.mod(LON[s, i], 360.0)
            F[f"{b} tropical longitude, cos — {who}"] = (
                f"Cosine of {b}'s tropical ecliptic longitude in the {who} partner's chart; {b} signifies "
                f"{MEANS[b]}. Cosine and sine avoid the 359-to-1 degree wrap.", np.cos(lam * rad))
            F[f"{b} tropical longitude, sin — {who}"] = (
                f"Sine of {b}'s tropical longitude for the {who} partner.", np.sin(lam * rad))
            F[f"{b} sign 1-12 — {who}"] = (
                f"Which 30-degree tropical sign {b} occupied for the {who} partner, Aries 1 to Pisces 12.",
                np.floor(lam / 30.0) + 1)
            F[f"{b} decan 1-36 — {who}"] = (
                f"Which 10-degree decan {b} occupied for the {who} partner; the decans are the oldest "
                f"subdivision of the zodiac still read.", np.floor(lam / 10.0) + 1)
            F[f"{b} dwadasamsa 1-144 — {who}"] = (
                f"Which 2.5-degree twelfth-of-a-sign {b} occupied for the {who} partner.",
                np.floor(lam / 2.5) + 1)
            F[f"{b} nakshatra 1-27 — {who}"] = (
                f"Which of the 27 lunar mansions {b} occupied for the {who} partner.",
                np.floor(lam / (360.0 / 27.0)) + 1)
            F[f"{b} navamsa 1-108 — {who}"] = (
                f"Which of the 108 navamsa ninths {b} occupied for the {who} partner; the navamsa is the "
                f"divisional chart read for marriage.", np.floor(lam / (360.0 / 108.0)) + 1)
            F[f"{b} degree within its sign — {who}"] = (
                f"How far into its sign {b} had travelled for the {who} partner, 0-30 degrees.",
                np.mod(lam, 30.0))
            F[f"{b} daily speed — {who}"] = (
                f"{b}'s apparent motion in degrees per day at the {who} partner's birth.", SPD[s, i])
            if np.any(SPD[s, i] < 0):
                F[f"{b} retrograde — {who}"] = (
                    f"1 when {b} was apparently moving backwards at the {who} partner's birth.",
                    (SPD[s, i] < 0).astype(float))
            if SID is not None:
                sl = np.mod(SID[s, i], 360.0)
                F[f"{b} sidereal longitude (Lahiri), cos — {who}"] = (
                    f"Cosine of {b}'s SIDEREAL longitude under the Lahiri ayanamsa for the {who} partner — the "
                    f"zodiac Indian astrology uses, offset from the tropical one by the precession of the "
                    f"equinoxes.", np.cos(sl * rad))
                F[f"{b} sidereal nakshatra 1-27 (Lahiri) — {who}"] = (
                    f"{b}'s lunar mansion in the sidereal zodiac for the {who} partner, which is the form "
                    f"Jyotisa actually reads.", np.floor(sl / (360.0 / 27.0)) + 1)
    yield "single body", F

    # ── harmonic charts ───────────────────────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for b in NAMES18:
            for h in (5, 7, 9):
                lam = np.mod(LON[s, IDX[b]] * h, 360.0)
                F[f"{b} in the {h}th-harmonic chart, cos — {who}"] = (
                    f"Cosine of {b}'s longitude multiplied by {h} and rewrapped, for the {who} partner. "
                    f"Multiplying a longitude by n is how a harmonic chart is built; the {h}th harmonic is "
                    f"read for creative and fated themes.", np.cos(lam * rad))
                F[f"{b} sign in the {h}th-harmonic chart — {who}"] = (
                    f"Which sign {b} falls in once its longitude is multiplied by {h}, for the {who} partner.",
                    np.floor(lam / 30.0) + 1)
    yield "harmonic charts", F

    # ── cross-chart synastry: all 18x18 ordered pairs ─────────────────────────────────────────────────────
    F = {}
    for a in NAMES18:
        for b in NAMES18:
            d = _fold(LON[0, IDX[a]] - LON[1, IDX[b]])
            F[f"{a}(older) to {b}(younger) separation"] = (
                f"The angle between the older partner's {a} and the younger partner's {b}, folded to 0-180 "
                f"degrees: {MEANS[a]} meeting {MEANS[b]}.", d)
            for h in (1, 2, 3, 4, 5, 6):
                F[f"{a}(older) to {b}(younger), harmonic {h}"] = (
                    f"cos({h} x separation) between the older partner's {a} and the younger partner's {b}. "
                    f"Peaks when the {h}th-harmonic aspect is exact and decays smoothly with orb, which is what "
                    f"a hard orb window approximates.", np.cos(h * d * rad))
    yield "cross-chart synastry", F

    # ── natal aspects inside each chart ───────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for ii in range(len(NAMES18)):
            for jj in range(ii + 1, len(NAMES18)):
                a, b = NAMES18[ii], NAMES18[jj]
                d = _fold(LON[s, IDX[a]] - LON[s, IDX[b]])
                F[f"{a} to {b} separation — {who}'s own chart"] = (
                    f"The natal angle between {a} and {b} in the {who} partner's own chart.", d)
                for h in (1, 2, 3):
                    F[f"{a} to {b}, harmonic {h} — {who}'s own chart"] = (
                        f"cos({h} x separation) between {a} and {b} natally for the {who} partner.",
                        np.cos(h * d * rad))
    yield "natal aspects", F

    # ── midpoints and antiscia ───────────────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for ii in range(len(CLASSICAL)):
            for jj in range(ii + 1, len(CLASSICAL)):
                a, b = CLASSICAL[ii], CLASSICAL[jj]
                m = np.mod((LON[s, IDX[a]] + LON[s, IDX[b]]) / 2.0, 360.0)
                F[f"{a}/{b} midpoint, cos — {who}"] = (
                    f"Cosine of the midpoint between {a} and {b} in the {who} partner's chart. The Hamburg "
                    f"School reads midpoints as the site where two principles combine.", np.cos(m * rad))
                F[f"{a}/{b} midpoint sign — {who}"] = (
                    f"Which sign the {a}/{b} midpoint fell in for the {who} partner.", np.floor(m / 30.0) + 1)
        for b in NAMES18:
            an = np.mod(180.0 - LON[s, IDX[b]], 360.0)
            F[f"{b} antiscion, cos — {who}"] = (
                f"Cosine of {b}'s antiscion for the {who} partner — its mirror across the solstice axis, a "
                f"contact Hellenistic and Renaissance astrology treats as equivalent to a conjunction.",
                np.cos(an * rad))
    for a in CLASSICAL:
        for b in CLASSICAL:
            mo = np.mod((LON[0, IDX[a]] + LON[0, IDX[b]]) / 2.0, 360.0)
            for c in CLASSICAL:
                if c != a:
                    continue
                d = _fold(mo - LON[1, IDX[c]])
                F[f"older's {a}/{b} midpoint to younger's {c}"] = (
                    f"How close the younger partner's {c} falls to the older partner's {a}/{b} midpoint, "
                    f"0-180 degrees — a cross-chart midpoint contact.", d)
    yield "midpoints and antiscia", F

    # ── lunar elongations ────────────────────────────────────────────────────────────────────────────────
    F = {}
    for who, s in SLOTS:
        for b in NAMES18:
            if b == "Sun":
                continue
            p = np.mod(LON[s, IDX[b]] - LON[s, IDX["Sun"]], 360.0)
            F[f"{b} elongation from the Sun, cos — {who}"] = (
                f"Cosine of {b}'s angular distance from the Sun for the {who} partner. For the Moon this is the "
                f"lunation phase; for a planet it decides whether it rose before or after the Sun, which "
                f"Hellenistic astrology treats as a change of condition.", np.cos(p * rad))
            F[f"{b} is oriental of the Sun — {who}"] = (
                f"1 when {b} rose before the Sun for the {who} partner (elongation under 180 degrees).",
                (p < 180).astype(float))
    for b in NAMES18:
        if b == "Sun":
            continue
        po = np.mod(LON[0, IDX[b]] - LON[0, IDX["Sun"]], 360.0)
        py = np.mod(LON[1, IDX[b]] - LON[1, IDX["Sun"]], 360.0)
        F[f"{b} elongation difference between the partners"] = (
            f"How far apart the partners were in {b}'s cycle relative to the Sun, 0-180 degrees.",
            _fold(po - py))
    yield "lunar elongations", F

    # ── vargas ───────────────────────────────────────────────────────────────────────────────────────────
    F = {}
    for D, label in VARGA.items():
        for b in CLASSICAL:
            for who, s in SLOTS:
                base = SID if SID is not None else LON
                v = np.floor(np.mod(base[s, IDX[b]], 360.0) / (30.0 / D)) % 12
                F[f"{b} sign in D{D} {label} — {who}"] = (
                    f"{b}'s sign in the D{D} divisional chart ({label}) for the {who} partner: the sign is "
                    f"divided into {D} parts and the part index mapped back onto the twelve signs. Computed on "
                    f"the sidereal zodiac, as Jyotisa does.", v + 1)
            vo = np.floor(np.mod((SID if SID is not None else LON)[0, IDX[b]], 360.0) / (30.0 / D)) % 12
            vy = np.floor(np.mod((SID if SID is not None else LON)[1, IDX[b]], 360.0) / (30.0 / D)) % 12
            F[f"{b} shares a D{D} sign across the two charts"] = (
                f"1 when {b} occupies the same D{D} ({label}) sign in both partners' charts — the divisional "
                f"form of a same-sign contact.", (vo == vy).astype(float))
    yield "vargas", F

    # ── vedic pair distances for every body ──────────────────────────────────────────────────────────────
    F = {}
    base = SID if SID is not None else LON
    for b in NAMES18:
        no = np.floor(np.mod(base[0, IDX[b]], 360.0) / (360.0 / 27.0))
        ny = np.floor(np.mod(base[1, IDX[b]], 360.0) / (360.0 / 27.0))
        F[f"{b} nakshatra distance between the partners"] = (
            f"How many of the 27 lunar mansions separate the partners' {b}, folded to 0-13. Ashtakuta scores "
            f"several kutas from exactly this distance, though only for the Moon.", _fold(no - ny, 27))
        so = np.floor(np.mod(base[0, IDX[b]], 360.0) / 30.0)
        sy = np.floor(np.mod(base[1, IDX[b]], 360.0) / 30.0)
        F[f"{b} sign distance between the partners"] = (
            f"How many signs separate the partners' {b}, folded to 0-6.", _fold(so - sy, 12))
        F[f"{b} in the same sign for both partners"] = (
            f"1 when both partners' {b} occupy the same sign.", (so == sy).astype(float))
    yield "vedic pair", F


def calendrical(df, sun_o, sun_y, JD):
    """Families that need the CALENDAR date, not only a longitude: weekday, day of the year, sun-sign pairs,
    the Chinese sexagenary pillars, and numerology. Requires day precision on both dates."""
    # DATES AS numpy datetime64[D], NOT pandas datetimes. pandas 2.x parses to NANOSECONDS, whose range starts at
    # 1677-09-21, and the training half starts in 1600: the Kaggle kernel died on OutOfBoundsDatetime at the
    # first 17th-century couple. It worked locally only because pandas 3 infers a microsecond resolution. numpy's
    # datetime64[D] spans +-2.5e16 days on every version, and every calendar quantity below is integer
    # arithmetic on it: 1970-01-01 was a Thursday, so (days_since_epoch + 4) % 7 is the weekday with Sunday 0.
    do = np.array(df.dob_older.to_numpy().astype(str), dtype="datetime64[D]")
    dy = np.array(df.dob_younger.to_numpy().astype(str), dtype="datetime64[D]")

    def _cal(d):
        Y = d.astype("datetime64[Y]")
        M = d.astype("datetime64[M]")
        return {"year": Y.astype(np.int64) + 1970,
                "month": M.astype(np.int64) % 12 + 1,
                "day": (d - M).astype(np.int64) + 1,
                "doy": (d - Y).astype(np.int64) + 1,
                "wd": (d.astype(np.int64) + 4) % 7}
    co, cy = _cal(do), _cal(dy)
    doy = {"older": co["doy"], "younger": cy["doy"]}
    wd = {"older": co["wd"], "younger": cy["wd"]}
    yr = {"older": co["year"], "younger": cy["year"]}
    mo = {"older": co["month"], "younger": cy["month"]}
    dm = {"older": co["day"], "younger": cy["day"]}
    gap_days = (dy - do).astype(np.int64).astype(float)

    F = {}
    for who in ("older", "younger"):
        F[f"day of the year — {who}"] = (
            f"The {who} partner's birth day counted from 1 January, 1-366: the season of birth, very nearly "
            f"orthogonal to the birth year.", doy[who].astype(float))
        for h in (1, 2, 3, 4):
            F[f"day of the year, cos harmonic {h} — {who}"] = (
                f"cos({h} x 2pi x day-of-year / 365.25) for the {who} partner: the {h}-per-year component of "
                f"the seasonal cycle, free of the 31-December wrap.",
                np.cos(h * 2 * np.pi * doy[who] / 365.25))
            F[f"day of the year, sin harmonic {h} — {who}"] = (
                f"The sine companion of the {h}-per-year seasonal component for the {who} partner.",
                np.sin(h * 2 * np.pi * doy[who] / 365.25))
        F[f"weekday of birth (0 Sunday) — {who}"] = (
            f"Which day of the week the {who} partner was born. The seven-day week is the oldest astrological "
            f"cycle still in use and is near-orthogonal to both era and age gap.", wd[who].astype(float))
        for k, lord in enumerate(DAYLORD):
            F[f"born on a {lord} day — {who}"] = (
                f"1 when the {who} partner was born on the weekday ruled by {lord} in the Chaldean order "
                f"({['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'][k]}).",
                (wd[who] == k).astype(float))
        F[f"day of the month — {who}"] = (
            f"The raw day of the month of the {who} partner's birth, 1-31.", dm[who].astype(float))
        F[f"month of birth — {who}"] = (
            f"The raw calendar month of the {who} partner's birth, 1-12.", mo[who].astype(float))

    dd = _fold(doy["older"].astype(float) - doy["younger"].astype(float), 365.25)
    F["seasonal separation of the two births (days)"] = (
        "How far apart in the YEAR the two partners were born, ignoring which year — the Sun-to-Sun synastry "
        "contact and the sub-year remainder of the age gap at once.", dd)
    for h in (1, 2, 3, 4):
        F[f"seasonal separation, cos harmonic {h}"] = (
            f"cos({h} x the seasonal separation): h=1 peaks when the birthdays coincide, h=2 when they coincide "
            f"or fall six months apart.", np.cos(h * 2 * np.pi * dd / 365.25))
    F["born within 15 days of the same point in the year"] = (
        "1 when the partners' birthdays fall within a fortnight of each other in the calendar.",
        (dd < 15).astype(float))
    F["same weekday of birth"] = (
        "1 when both partners were born on the same weekday, i.e. their age gap is a whole number of weeks.",
        (wd["older"] == wd["younger"]).astype(float))
    F["same calendar month of birth"] = (
        "1 when both partners were born in the same month of the year.",
        (mo["older"] == mo["younger"]).astype(float))
    whole = np.round(gap_days / 365.2425)
    F["age gap in whole years"] = (
        "The partners' age difference rounded to whole years — the term that carries the mortality effect, "
        "listed so the periodic features can be read against it.", whole)
    F["sub-year remainder of the age gap"] = (
        "What is left of the age gap after removing whole years, folded to 0-182 days. Seasonal, and unable to "
        "carry a mortality effect.", _fold(gap_days - whole * 365.2425, 365.2425))
    for p, nm in ((7.0, "week"), (12.0, "twelve-year animal cycle"), (19.0, "Metonic 19-year cycle"),
                  (29.53059, "synodic month"), (60.0, "sexagenary 60-year cycle")):
        unit_years = nm in ("twelve-year animal cycle", "Metonic 19-year cycle", "sexagenary 60-year cycle")
        v = gap_days / (365.2425 if unit_years else 1.0)
        F[f"age gap modulo the {nm}"] = (
            f"The age gap taken modulo the {nm} and folded, isolating that cycle's own claim from the smooth "
            f"age-gap trend. No smooth model of the gap can contain it.", _fold(v, p))

    # ── sun-sign compatibility, in the forms people actually use ─────────────────────────────────────────
    so = np.floor(np.mod(sun_o, 360.0) / 30.0)
    sy = np.floor(np.mod(sun_y, 360.0) / 30.0)
    ds = _fold(so - sy, 12)
    F["Sun-sign distance between the partners (0-6)"] = (
        "How many of the twelve signs separate the two Suns, folded. Every sun-sign compatibility rule in "
        "circulation is a function of this one number.", ds)
    F["both Suns in the SAME sign"] = ("1 when both partners share a Sun sign.", (ds == 0).astype(float))
    F["Suns in the same ELEMENT (the classic trine 'compatible' rule)"] = (
        "1 when the two Sun signs share an element — 0, 4 or 8 signs apart. The single most repeated "
        "compatibility rule in popular astrology.", (np.mod(so - sy, 4) == 0).astype(float))
    F["Suns in the same MODALITY (cardinal/fixed/mutable)"] = (
        "1 when the Sun signs share a modality, 0/3/6/9 signs apart — held to produce friction.",
        (np.mod(so - sy, 3) == 0).astype(float))
    for k, nm in ((6, "OPPOSITE signs"), (3, "SQUARE"), (2, "SEXTILE"), (1, "adjacent signs")):
        F[f"Suns in {nm}"] = (
            f"1 when the two Suns are {k} signs apart, folded.", (ds == k).astype(float))
    F["popular 'compatible' verdict (same element or sextile)"] = (
        "1 when the pair satisfies the composite rule a magazine column applies: same element, or two signs "
        "apart.", ((np.mod(so - sy, 4) == 0) | (ds == 2)).astype(float))
    for si, nm in enumerate(SIGNS):
        F[f"older partner's Sun in {nm}"] = (
            f"1 when the older partner's Sun was in {nm}.", (so == si).astype(float))
        F[f"younger partner's Sun in {nm}"] = (
            f"1 when the younger partner's Sun was in {nm}.", (sy == si).astype(float))

    # ── Chinese sexagenary pillars ───────────────────────────────────────────────────────────────────────
    for who in ("older", "younger"):
        F[f"Chinese year branch (animal) 1-12 — {who}"] = (
            f"The {who} partner's birth-year animal, Rat 1 to Pig 12, from the year modulo twelve.",
            (np.mod(yr[who] - 4, 12) + 1).astype(float))
        F[f"Chinese year stem 1-10 — {who}"] = (
            f"The {who} partner's birth-year heavenly stem, from the year modulo ten.",
            (np.mod(yr[who] - 4, 10) + 1).astype(float))
        F[f"Chinese year stem element 1-5 — {who}"] = (
            f"The five-phase element of the {who} partner's year stem: Wood, Fire, Earth, Metal, Water.",
            (np.mod(yr[who] - 4, 10) // 2 + 1).astype(float))
    jd = np.floor(np.asarray(JD[0], dtype=np.float64) + 0.5)
    jdy = np.floor(np.asarray(JD[1], dtype=np.float64) + 0.5)
    for who, j in (("older", jd), ("younger", jdy)):
        F[f"sexagenary DAY index 1-60 — {who}"] = (
            f"The {who} partner's day pillar: the continuous 60-day sexagenary count, which advances one step "
            f"per calendar day and is independent of the year cycle.", np.mod(j, 60) + 1)
        F[f"sexagenary day branch 1-12 — {who}"] = (
            f"The animal branch of the {who} partner's day pillar.", np.mod(j, 12) + 1)
    ao, ay = np.mod(yr["older"] - 4, 12), np.mod(yr["younger"] - 4, 12)
    dan = _fold(ao.astype(float) - ay, 12)
    F["Chinese animal distance between the partners (0-6)"] = (
        "How many animal years separate the partners. Being the age gap modulo twelve, no smooth model of the "
        "gap contains it.", dan)
    F["same Chinese animal"] = ("1 when both partners share an animal sign.", (dan == 0).astype(float))
    F["san-he trine group match (4 or 8 animals apart)"] = (
        "1 when the animals share a san-he trine, the groups Chinese practice holds most compatible.",
        (np.mod(ao - ay, 4) == 0).astype(float))
    F["liu-chong clash (exactly 6 animals apart)"] = (
        "1 when the animals are directly opposed on the twelve-year wheel — the specific and widely believed "
        "claim that a six-year age gap is unlucky.", (dan == 6).astype(float))
    F["same stem element across the partners"] = (
        "1 when both birth years carry the same five-phase element.",
        (np.mod(yr["older"] - 4, 10) // 2 == np.mod(yr["younger"] - 4, 10) // 2).astype(float))
    F["stem-element distance on the five-phase wheel"] = (
        "Folded distance between the partners' stem elements, where adjacency is generation and two is "
        "conquest.", _fold(np.mod(yr["older"] - 4, 10) // 2 - np.mod(yr["younger"] - 4, 10) // 2, 5))

    # ── numerology ───────────────────────────────────────────────────────────────────────────────────────
    import trad_numerology as NU
    N = {"older": NU.numbers(yr["older"], mo["older"], dm["older"]),
         "younger": NU.numbers(yr["younger"], mo["younger"], dm["younger"])}
    LAB = {"lp": ("Life Path", "the digit sum of the whole birth date reduced to one figure, keeping the master "
                               "numbers 11, 22 and 33 — the most-read number in the practice"),
           "bday": ("Birthday number", "the day of the month reduced to one figure"),
           "att": ("Attitude number", "month plus day reduced — how the person is said to present"),
           "y": ("Year pillar", "the birth year's digits reduced on their own"),
           "m": ("Month pillar", "the birth month reduced"),
           "d": ("Day pillar", "the birth day reduced, no master numbers"),
           "chal": ("Chaldean number", "the date reduced under the Chaldean rule, which holds 9 sacred")}
    KARMIC = (13, 14, 16, 19)
    for who in ("older", "younger"):
        for k, (nm, ex) in LAB.items():
            F[f"{nm} — {who}"] = (f"The {who} partner's {nm}: {ex}.", N[who][k].astype(float))
            for val in range(1, 10):
                F[f"{nm} is {val} — {who}"] = (
                    f"1 when the {who} partner's {nm} reduces to {val}.",
                    (N[who][k] == val).astype(float))
        F[f"Life Path is a master number — {who}"] = (
            f"1 when the {who} partner's Life Path is 11, 22 or 33, a class numerology treats as distinct and "
            f"more demanding rather than merely larger.", np.isin(N[who]["lp"], NU.MASTER).astype(float))
        raw = NU._digit_sum(yr[who]) + NU._digit_sum(mo[who]) + NU._digit_sum(dm[who])
        for kd in KARMIC:
            F[f"karmic debt number {kd} — {who}"] = (
                f"1 when the {who} partner's unreduced date sum is {kd}, one of the four numbers numerology "
                f"designates a karmic debt.", (raw == kd).astype(float))
        F[f"unreduced date digit sum — {who}"] = (
            f"The {who} partner's whole birth date digit-summed once, before reduction.", raw.astype(float))
        F[f"digit sum of the birth year — {who}"] = (
            f"The {who} partner's birth year digit-summed, e.g. 1899 -> 27. Deliberately almost decorrelated "
            f"from the year itself: 1899 and 1900 give 27 and 10.", NU._digit_sum(yr[who]).astype(float))
        ch = np.abs(NU._reduce(mo[who], False) - NU._reduce(dm[who], False))
        F[f"first challenge number — {who}"] = (
            f"The {who} partner's first challenge number: the absolute difference of the reduced month and "
            f"reduced day, read as the obstacle carried through early life.", ch.astype(float))
        F[f"first pinnacle number — {who}"] = (
            f"The {who} partner's first pinnacle: reduced month plus reduced day, read as the theme of the "
            f"first life cycle.", NU._reduce(mo[who] + dm[who], False).astype(float))
    lpo, lpy = N["older"]["lp"], N["younger"]["lp"]
    F["sum of the two Life Paths"] = ("The partners' Life Paths added.", (lpo + lpy).astype(float))
    F["relationship number (Life Paths summed and reduced)"] = (
        "The two Life Paths added and reduced — the number a numerologist assigns to the couple itself.",
        NU._reduce(lpo + lpy, keep_master=False).astype(float))
    F["absolute difference of the two Life Paths"] = (
        "How far apart the partners' Life Paths are.", np.abs(lpo - lpy).astype(float))
    F["identical Life Paths"] = ("1 when both partners share a Life Path.", (lpo == lpy).astype(float))
    F["same numerological compatibility group"] = (
        "1 when both Life Paths fall in the same taught grouping — 1-5-7 mind, 2-4-8 business, 3-6-9 creative.",
        np.array([1.0 if NU._GROUP.get(int(a), -1) == NU._GROUP.get(int(b), -2) else 0.0
                  for a, b in zip(lpo, lpy)]))
    F["identical Birthday numbers"] = (
        "1 when both partners reduce the same day-of-month number.",
        (N["older"]["bday"] == N["younger"]["bday"]).astype(float))
    F["identical Chaldean numbers"] = (
        "1 when both partners share a Chaldean reduction.",
        (N["older"]["chal"] == N["younger"]["chal"]).astype(float))
    F["older partner's Personal Year in the younger's birth year"] = (
        "The numerologist's question 'what personal year were you in when they were born': the older partner's "
        "month and day added to the younger's birth year, reduced.",
        NU.personal_year(mo["older"], dm["older"], yr["younger"]).astype(float))
    F["younger partner's Personal Year in the older's birth year"] = (
        "The same quantity with the partners exchanged.",
        NU.personal_year(mo["younger"], dm["younger"], yr["older"]).astype(float))
    mid = (yr["older"] + yr["younger"]) // 2
    F["both in the same Personal Year at their date midpoint"] = (
        "1 when both partners share a Personal Year computed at the midpoint year between their births.",
        (NU.personal_year(mo["older"], dm["older"], mid)
         == NU.personal_year(mo["younger"], dm["younger"], mid)).astype(float))
    return F
