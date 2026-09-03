"""systems_calendars.py — OTHER CALENDARS as pseudo-bodies (tradition slug "calendars").

Every system here is a pure function of the Gregorian birth date (y, m, d): the date goes to a
Julian Day Number (Fliegel & Van Flandern, 1968) and from the JDN into each calendar by the
standard arithmetic algorithm, implemented here in full — no packages, no tables fetched, nothing
beyond the standard library. The same code must run under Pyodide in the browser, so every state
function has the contract

        fn(y, m, d, L) -> int in [0, N-1]

where L is the person's dict of SIDEREAL longitudes in degrees (unused by a calendar; the
ayanamsa helper is included for a system that ever needs the tropical Sun).

The corpus dates are proleptic Gregorian (1600-2000). A calendar's own numbering starts at 1
everywhere (month 1, day 1, week 1); the state is that number minus one, so the fitter's
angle rule state s of N -> (s+1)*360/N puts "1" at 360/N degrees exactly as the numerology
systems do.

Calendars and their algorithms (each documented at its function):

  Hebrew        Dershowitz & Reingold molad arithmetic (elapsed-days + the four dehiyyot).
                month 13 (Nisan=1 .. Elul=6, Tishri=7 .. Adar=12, Adar II=13), day 30,
                weekday of Rosh Hashanah 7 (only Mon/Tue/Thu/Sat ever occur — lo ADU rosh),
                plus the year length class 3 (deficient/regular/complete) and leap 2.
  Islamic       tabular (civil, Friday-epoch, 30-year cycle of 11 leap years — the 'type II'
                intercalation 2,5,7,10,13,16,18,21,24,26,29). month 12, day 30.
  Persian       Solar Hijri / Jalali by the Borkowski 33-year-cycle algorithm (the algorithm of
                jalaali.js; valid for Jalali years -61..3177, i.e. 560..3798 CE). month 12, day 31.
  Zoroastrian   Yazdegerdi: 12 x 30 named days + 5 Gatha days, no leap ever; epoch 16 June 632
                Julian = JDN 1952063. month 13 (13 = the Gathas), day-name 30 (Gatha k -> day k).
  Coptic        Alexandrian: 12 x 30 + 5/6 epagomenal, leap when year % 4 == 3; epoch 29 Aug 284
                Julian = JDN 1825030. The Ethiopian calendar has the identical month/day (only the
                year differs, by 276), so one pair serves both. month 13, day 30.
  Julian        proleptic Julian calendar: day-of-year 365 (Feb 29 shares Feb 28's state, so a
                calendar date is one state in every year), month 12, day 31.
  Gregorian     day-of-year 365 (same leap rule), quarter 4, ISO week 53, ISO weekday 7.
  French Rep.   in force 22 Sep 1792 (1 Vendemiaire I) .. 31 Dec 1805 (10 Nivose XIV); the
                new-year table is the equinox rule as actually decreed (sextile years III, VII, XI).
                Outside that span the state is the reserved 0 ("not in force"); in force the month
                is 1..13 (13 = Sansculottides) and the decade-day 1..10 — hence N = 14 and N = 11.
  Roman         nundinal letter A..H = JDN mod 8 (the eight-day market week is a pure cycle).
  JDN cycles    JDN mod 7, 8, 9, 10, 11, 12, 13, each as its own circle.

Self-test:  python systems_calendars.py   (prints the smoke count and every fixed-point check).
"""

# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------

def ayanamsa(y):
    """Lahiri ayanamsa in degrees, linear fit good to a few arcminutes: tropical = sidereal + this."""
    return 23.853 + 0.013971 * (y - 2000)


def jdn(y, m, d):
    """Julian Day Number of a proleptic Gregorian date (Fliegel & Van Flandern 1968, floor form)."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def jdn_julian(y, m, d):
    """Julian Day Number of a (proleptic) Julian-calendar date."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083


def gregorian(j):
    """JDN -> (y, m, d) proleptic Gregorian (inverse of jdn)."""
    a = j + 32044
    b = (4 * a + 3) // 146097
    c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def julian(j):
    """JDN -> (y, m, d) proleptic Julian calendar."""
    c = j + 32082
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = d - 4800 + m // 10
    return year, month, day


def weekday(j):
    """0 = Sunday .. 6 = Saturday."""
    return (j + 1) % 7


_CUM_COMMON = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def doy365(m, d):
    """Day of year on a fixed 365-day circle: Feb 29 shares Feb 28's state (58)."""
    x = _CUM_COMMON[m - 1] + d - 1
    if m == 2 and d == 29:
        x = 58
    return x


# ----------------------------------------------------------------------------------------------
# Hebrew calendar (Dershowitz & Reingold, "Calendrical Calculations", arithmetic of the molad)
# ----------------------------------------------------------------------------------------------
# Epoch: 1 Tishri AM 1 = Monday 7 October 3761 BCE (Julian) = R.D. -1373427 = JDN 347998.
HEBREW_EPOCH = jdn_julian(-3760, 10, 7)          # astronomical year -3760 == 3761 BCE


def hebrew_leap(hy):
    return (7 * hy + 1) % 19 < 7


def _hebrew_elapsed_days(hy):
    """Days from the epoch to the molad-derived new year of hy, before the year-length dehiyyot."""
    months_elapsed = (235 * hy - 234) // 19
    parts_elapsed = 12084 + 13753 * months_elapsed
    day = months_elapsed * 29 + parts_elapsed // 25920
    if (3 * (day + 1)) % 7 < 3:        # dehiyyah: Rosh Hashanah never on Sun, Wed, Fri (lo ADU rosh)
        day += 1
    return day


def _hebrew_delay(hy):
    """Dehiyyot GaTaRaD and BeTU'TeKaPoT, expressed through the neighbouring years' lengths."""
    ny0 = _hebrew_elapsed_days(hy - 1)
    ny1 = _hebrew_elapsed_days(hy)
    ny2 = _hebrew_elapsed_days(hy + 1)
    if ny2 - ny1 == 356:
        return 2
    if ny1 - ny0 == 382:
        return 1
    return 0


def hebrew_new_year(hy):
    """JDN of 1 Tishri of Hebrew year hy."""
    return HEBREW_EPOCH + _hebrew_elapsed_days(hy) + _hebrew_delay(hy)


def hebrew_year_length(hy):
    return hebrew_new_year(hy + 1) - hebrew_new_year(hy)


def hebrew_month_length(hy, hm):
    """hm in 1..13 (Nisan=1 .. Adar=12, Adar II=13; in a leap year 12 = Adar I, 13 = Adar II)."""
    yl = hebrew_year_length(hy)
    if hm in (2, 4, 6, 10, 13):
        return 29
    if hm == 8 and yl % 10 != 5:       # Heshvan is 30 only in a complete year
        return 29
    if hm == 9 and yl % 10 == 3:       # Kislev is 29 only in a deficient year
        return 29
    if hm == 12 and not hebrew_leap(hy):   # Adar (common year) is 29; Adar I (leap) is 30
        return 29
    return 30


def hebrew(j):
    """JDN -> (hy, hm, hd)."""
    approx = (j - HEBREW_EPOCH) * 98496 // 35975351 + 1        # 35975351/98496 days per year
    hy = approx - 1
    while hebrew_new_year(hy + 1) <= j:
        hy += 1
    days = j - hebrew_new_year(hy)                           # day index from 1 Tishri
    order = [7, 8, 9, 10, 11, 12, 13, 1, 2, 3, 4, 5, 6] if hebrew_leap(hy) \
        else [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
    for hm in order:
        ml = hebrew_month_length(hy, hm)
        if days < ml:
            return hy, hm, days + 1
        days -= ml
    raise AssertionError("hebrew: day index past the year")


def hebrew_to_jdn(hy, hm, hd):
    order = [7, 8, 9, 10, 11, 12, 13, 1, 2, 3, 4, 5, 6] if hebrew_leap(hy) \
        else [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
    j = hebrew_new_year(hy)
    for x in order:
        if x == hm:
            return j + hd - 1
        j += hebrew_month_length(hy, x)
    raise ValueError("hebrew month %d absent from year %d" % (hm, hy))


# ----------------------------------------------------------------------------------------------
# Islamic tabular (civil) calendar — the Fliegel-style closed formulae
# ----------------------------------------------------------------------------------------------
ISLAMIC_EPOCH = 1948440                # 1 Muharram 1 AH = Friday 16 July 622 Julian (civil epoch)


def islamic(j):
    """JDN -> (iy, im, id), tabular Hijri with the 30-year cycle (leap years 2,5,7,10,13,16,18,21,24,26,29)."""
    l = j - ISLAMIC_EPOCH + 10632
    n = (l - 1) // 10631
    l = l - 10631 * n + 354
    jj = ((10985 - l) // 5316) * ((50 * l) // 17719) + (l // 5670) * ((43 * l) // 15238)
    l = l - ((30 - jj) // 15) * ((17719 * jj) // 50) - (jj // 16) * ((15238 * jj) // 43) + 29
    im = (24 * l) // 709
    idd = l - (709 * im) // 24
    iy = 30 * n + jj - 30
    return iy, im, idd


def islamic_to_jdn(iy, im, idd):
    return (11 * iy + 3) // 30 + 354 * iy + 30 * im - (im - 1) // 2 + idd + ISLAMIC_EPOCH - 385


# ----------------------------------------------------------------------------------------------
# Persian Solar Hijri / Jalali — Borkowski's 33-year-cycle algorithm (the one in jalaali.js)
# ----------------------------------------------------------------------------------------------
_JAL_BREAKS = (-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192,
               2262, 2324, 2394, 2456, 3178)


def _jal_cal(jy):
    """-> (leap, gy, march): is jy leap; the Gregorian year and the March day of 1 Farvardin jy."""
    bl = len(_JAL_BREAKS)
    gy = jy + 621
    leap_j = -14
    jp = _JAL_BREAKS[0]
    if jy < jp or jy >= _JAL_BREAKS[bl - 1]:
        raise ValueError("Jalali year out of range: %d" % jy)
    jump = 0
    for i in range(1, bl):
        jm = _JAL_BREAKS[i]
        jump = jm - jp
        if jy < jm:
            break
        leap_j = leap_j + (jump // 33) * 8 + ((jump % 33) // 4)
        jp = jm
    n = jy - jp
    leap_j = leap_j + (n // 33) * 8 + (((n % 33) + 3) // 4)
    if (jump % 33) == 4 and jump - n == 4:
        leap_j += 1
    leap_g = gy // 4 - (((gy // 100) + 1) * 3) // 4 - 150
    march = 20 + leap_j - leap_g
    if jump - n < 6:
        n = n - jump + ((jump + 4) // 33) * 33
    leap = ((n + 1) % 33 - 1) % 4
    if leap == -1:
        leap = 4
    return leap, gy, march


def jalali(j):
    """JDN -> (jy, jm, jd)."""
    gy = gregorian(j)[0]
    jy = gy - 621
    leap, _, march = _jal_cal(jy)
    jdn1f = jdn(gy, 3, march)
    k = j - jdn1f
    if k >= 0:
        if k <= 185:
            return jy, 1 + k // 31, k % 31 + 1
        k -= 186
    else:
        jy -= 1
        k += 179
        if leap == 1:
            k += 1
    return jy, 7 + k // 30, k % 30 + 1


def jalali_to_jdn(jy, jm, jd):
    _, gy, march = _jal_cal(jy)
    return jdn(gy, 3, march) + (jm - 1) * 31 - (jm // 7) * (jm - 7) + jd - 1


# ----------------------------------------------------------------------------------------------
# Zoroastrian Yazdegerdi — 365 days always; 12 x 30 named days then the 5 Gatha days
# ----------------------------------------------------------------------------------------------
YAZDEGERDI_EPOCH = jdn_julian(632, 6, 16)        # 1 Farvardin 1 Y.Z. = JDN 1952063
ZOROASTRIAN_DAY_NAMES = ("Hormazd", "Bahman", "Ardibehesht", "Shahrevar", "Aspandarmad", "Khordad",
                         "Amardad", "Dae-pa-Adar", "Adar", "Avan", "Khorshed", "Mohor", "Tir", "Gosh",
                         "Dae-pa-Meher", "Meher", "Srosh", "Rashne", "Fravardin", "Behram", "Ram",
                         "Govad", "Dae-pa-Din", "Din", "Ashishvangh", "Ashtad", "Asman", "Zamyad",
                         "Mahrespand", "Aneran")
ZOROASTRIAN_MONTHS = ("Fravardin", "Ardibehesht", "Khordad", "Tir", "Amardad", "Shahrevar", "Meher",
                      "Avan", "Adar", "Dae", "Bahman", "Aspandarmad", "Gathas")


def yazdegerdi(j):
    """JDN -> (yz_year, month 1..13, day 1..30 [1..5 in the Gathas])."""
    days = j - YAZDEGERDI_EPOCH
    yr = days // 365 + 1
    doy = days % 365
    return yr, doy // 30 + 1, doy % 30 + 1


# ----------------------------------------------------------------------------------------------
# Coptic (and, month/day-identical, Ethiopian)
# ----------------------------------------------------------------------------------------------
COPTIC_EPOCH = jdn_julian(284, 8, 29)             # 1 Thout AM 1 = JDN 1825030
ETHIOPIC_EPOCH = jdn_julian(8, 8, 29)             # 1 Meskerem 1 = JDN 1724221 (same structure)


def _alexandrian_to_jdn(epoch, y, m, d):
    return epoch - 1 + 365 * (y - 1) + y // 4 + 30 * (m - 1) + d


def _alexandrian(epoch, j):
    y = (4 * (j - epoch) + 1463) // 1461
    m = (j - _alexandrian_to_jdn(epoch, y, 1, 1)) // 30 + 1
    d = j + 1 - _alexandrian_to_jdn(epoch, y, m, 1)
    return y, m, d


def coptic(j):
    return _alexandrian(COPTIC_EPOCH, j)


def ethiopic(j):
    return _alexandrian(ETHIOPIC_EPOCH, j)


# ----------------------------------------------------------------------------------------------
# ISO week
# ----------------------------------------------------------------------------------------------
def _greg_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def greg_doy(y, m, d):
    return _CUM_COMMON[m - 1] + d + (1 if (m > 2 and _greg_leap(y)) else 0)


def iso_weekday(j):
    """1 = Monday .. 7 = Sunday."""
    return (weekday(j) + 6) % 7 + 1


def _iso_weeks_in_year(y):
    p = lambda yy: (yy + yy // 4 - yy // 100 + yy // 400) % 7
    return 53 if (p(y) == 4 or p(y - 1) == 3) else 52


def iso_week(y, m, d):
    """-> (iso_year, week 1..53)."""
    j = jdn(y, m, d)
    w = (greg_doy(y, m, d) - iso_weekday(j) + 10) // 7
    if w < 1:
        return y - 1, _iso_weeks_in_year(y - 1)
    if w > _iso_weeks_in_year(y):
        return y + 1, 1
    return y, w


# ----------------------------------------------------------------------------------------------
# French Republican — the calendar as decreed (equinox rule), 1 Vendemiaire I .. 10 Nivose XIV
# ----------------------------------------------------------------------------------------------
# 1 Vendemiaire of each year, Gregorian.  Sextile (366-day) years: III, VII, XI — exactly the
# years whose successor starts a day later than 365 days on.
_FRC_NEW_YEARS = (
    (1792, 9, 22), (1793, 9, 22), (1794, 9, 22), (1795, 9, 23), (1796, 9, 22), (1797, 9, 22),
    (1798, 9, 22), (1799, 9, 23), (1800, 9, 23), (1801, 9, 23), (1802, 9, 23), (1803, 9, 24),
    (1804, 9, 23), (1805, 9, 23))
FRC_NEW_YEAR_JDN = tuple(jdn(*x) for x in _FRC_NEW_YEARS)
FRC_START = FRC_NEW_YEAR_JDN[0]
FRC_END = jdn(1805, 12, 31)                       # 10 Nivose XIV; abolished from 1 Jan 1806
FRC_MONTHS = ("Vendemiaire", "Brumaire", "Frimaire", "Nivose", "Pluviose", "Ventose", "Germinal",
              "Floreal", "Prairial", "Messidor", "Thermidor", "Fructidor", "Sansculottides")


def french_republican(j):
    """JDN -> (year 1..14, month 1..13, day 1..30) or None when the calendar was not in force."""
    if j < FRC_START or j > FRC_END:
        return None
    yr = 0
    for i, ny in enumerate(FRC_NEW_YEAR_JDN):
        if j >= ny:
            yr = i + 1
    days = j - FRC_NEW_YEAR_JDN[yr - 1]
    return yr, days // 30 + 1, days % 30 + 1


# ----------------------------------------------------------------------------------------------
# the systems
# ----------------------------------------------------------------------------------------------
def _heb_month(y, m, d, L):
    return hebrew(jdn(y, m, d))[1] - 1


def _heb_day(y, m, d, L):
    return hebrew(jdn(y, m, d))[2] - 1


def _heb_rh_weekday(y, m, d, L):
    hy = hebrew(jdn(y, m, d))[0]
    return weekday(hebrew_new_year(hy))


def _heb_year_length(y, m, d, L):
    """0 deficient (353/383), 1 regular (354/384), 2 complete (355/385)."""
    hy = hebrew(jdn(y, m, d))[0]
    return {3: 0, 4: 1, 5: 2}[hebrew_year_length(hy) % 10]


def _heb_leap(y, m, d, L):
    return 1 if hebrew_leap(hebrew(jdn(y, m, d))[0]) else 0


def _isl_month(y, m, d, L):
    return islamic(jdn(y, m, d))[1] - 1


def _isl_day(y, m, d, L):
    return islamic(jdn(y, m, d))[2] - 1


def _jal_month(y, m, d, L):
    return jalali(jdn(y, m, d))[1] - 1


def _jal_day(y, m, d, L):
    return jalali(jdn(y, m, d))[2] - 1


def _yz_month(y, m, d, L):
    return yazdegerdi(jdn(y, m, d))[1] - 1


def _yz_day(y, m, d, L):
    return yazdegerdi(jdn(y, m, d))[2] - 1


def _cop_month(y, m, d, L):
    return coptic(jdn(y, m, d))[1] - 1


def _cop_day(y, m, d, L):
    return coptic(jdn(y, m, d))[2] - 1


def _jul_doy(y, m, d, L):
    _, jm, jd = julian(jdn(y, m, d))
    return doy365(jm, jd)


def _jul_month(y, m, d, L):
    return julian(jdn(y, m, d))[1] - 1


def _jul_day(y, m, d, L):
    return julian(jdn(y, m, d))[2] - 1


def _greg_doy(y, m, d, L):
    return doy365(m, d)


def _greg_quarter(y, m, d, L):
    return (m - 1) // 3


def _iso_week(y, m, d, L):
    return iso_week(y, m, d)[1] - 1


def _iso_weekday(y, m, d, L):
    return iso_weekday(jdn(y, m, d)) - 1


def _frc_month(y, m, d, L):
    r = french_republican(jdn(y, m, d))
    return 0 if r is None else r[1]


def _frc_decade_day(y, m, d, L):
    r = french_republican(jdn(y, m, d))
    return 0 if r is None else (r[2] - 1) % 10 + 1


def _nundinal(y, m, d, L):
    return jdn(y, m, d) % 8


def _mod(n):
    def fn(y, m, d, L):
        return jdn(y, m, d) % n
    fn.__name__ = "_jdn_mod%d" % n
    return fn


SYSTEMS = [
    {"name": "calendars_hebrew_month", "n": 13, "fn": _heb_month,
     "desc": "Hebrew month, Nisan=1 .. Elul=6, Tishri=7 .. Adar=12, Adar II=13 (D&R molad arithmetic)"},
    {"name": "calendars_hebrew_day", "n": 30, "fn": _heb_day,
     "desc": "Hebrew day of month 1..30"},
    {"name": "calendars_hebrew_rosh_hashanah_weekday", "n": 7, "fn": _heb_rh_weekday,
     "desc": "weekday of 1 Tishri of the Hebrew year of birth, 0=Sun..6=Sat (only Mon/Tue/Thu/Sat occur)"},
    {"name": "calendars_hebrew_year_length", "n": 3, "fn": _heb_year_length,
     "desc": "Hebrew year length class: deficient / regular / complete"},
    {"name": "calendars_hebrew_leap", "n": 2, "fn": _heb_leap,
     "desc": "Hebrew year is embolismic (has Adar II)"},
    {"name": "calendars_islamic_month", "n": 12, "fn": _isl_month,
     "desc": "tabular Hijri month, Muharram=1 .. Dhu al-Hijjah=12 (civil epoch JDN 1948440)"},
    {"name": "calendars_islamic_day", "n": 30, "fn": _isl_day,
     "desc": "tabular Hijri day of month 1..30"},
    {"name": "calendars_jalali_month", "n": 12, "fn": _jal_month,
     "desc": "Solar Hijri month, Farvardin=1 .. Esfand=12 (Borkowski 33-year cycles)"},
    {"name": "calendars_jalali_day", "n": 31, "fn": _jal_day,
     "desc": "Solar Hijri day of month 1..31"},
    {"name": "calendars_yazdegerdi_month", "n": 13, "fn": _yz_month,
     "desc": "Zoroastrian Yazdegerdi month, Fravardin=1 .. Aspandarmad=12, 13 = the five Gatha days"},
    {"name": "calendars_yazdegerdi_day_name", "n": 30, "fn": _yz_day,
     "desc": "Zoroastrian day-name Hormazd=1 .. Aneran=30 (Gatha day k -> k)"},
    {"name": "calendars_coptic_month", "n": 13, "fn": _cop_month,
     "desc": "Coptic/Ethiopian month, Thout=1 .. Mesori=12, 13 = the epagomenal days (Nesi/Pagume)"},
    {"name": "calendars_coptic_day", "n": 30, "fn": _cop_day,
     "desc": "Coptic/Ethiopian day of month 1..30 (1..6 in the epagomenal month)"},
    {"name": "calendars_julian_doy", "n": 365, "fn": _jul_doy,
     "desc": "day of year in the proleptic Julian calendar, 365-circle (Feb 29 shares Feb 28)"},
    {"name": "calendars_julian_month", "n": 12, "fn": _jul_month,
     "desc": "month in the proleptic Julian calendar"},
    {"name": "calendars_julian_day", "n": 31, "fn": _jul_day,
     "desc": "day of month in the proleptic Julian calendar"},
    {"name": "calendars_gregorian_doy", "n": 365, "fn": _greg_doy,
     "desc": "Gregorian day of year, 365-circle (Feb 29 shares Feb 28)"},
    {"name": "calendars_gregorian_quarter", "n": 4, "fn": _greg_quarter,
     "desc": "Gregorian quarter Q1..Q4"},
    {"name": "calendars_iso_week", "n": 53, "fn": _iso_week,
     "desc": "ISO 8601 week number 1..53"},
    {"name": "calendars_iso_weekday", "n": 7, "fn": _iso_weekday,
     "desc": "ISO weekday Monday=1 .. Sunday=7"},
    {"name": "calendars_french_republican_month", "n": 14, "fn": _frc_month,
     "desc": "French Republican month 1..13 (13 = Sansculottides) while in force 1792-09-22..1805-12-31; reserved 0 = not in force"},
    {"name": "calendars_french_republican_decade_day", "n": 11, "fn": _frc_decade_day,
     "desc": "French Republican day of the decade Primidi=1 .. Decadi=10 while in force; reserved 0 = not in force"},
    {"name": "calendars_roman_nundinal", "n": 8, "fn": _nundinal,
     "desc": "Roman nundinal letter A..H = JDN mod 8 (identical column to calendars_jdn_mod8)"},
]
for _n in (7, 8, 9, 10, 11, 12, 13):
    SYSTEMS.append({"name": "calendars_jdn_mod%d" % _n, "n": _n, "fn": _mod(_n),
                    "desc": "Julian Day Number mod %d, a pure %d-day cycle" % (_n, _n)})


# ----------------------------------------------------------------------------------------------
# self-test
# ----------------------------------------------------------------------------------------------
def _selftest():
    L = {"sun": 123.4, "moon": 210.0, "mercury": 100.0, "venus": 140.0, "mars": 300.0, "jupiter": 12.0,
         "saturn": 250.0, "uranus": 33.0, "neptune": 190.0, "pluto": 260.0, "node": 80.0, "chiron": 5.0,
         "lilith": 175.0}
    # fixed points, each a known conversion
    assert jdn(2000, 1, 1) == 2451545
    assert gregorian(2451545) == (2000, 1, 1)
    assert jdn_julian(632, 6, 16) == 1952063 == YAZDEGERDI_EPOCH
    assert COPTIC_EPOCH == 1825030 and ETHIOPIC_EPOCH == 1724221 and HEBREW_EPOCH == 347998
    assert julian(jdn(1900, 3, 14)) == (1900, 3, 1)               # 13-day lag after Julian 29 Feb 1900
    assert julian(jdn(1700, 3, 12)) == (1700, 3, 1)               # 11 days after Julian 29 Feb 1700
    assert julian(jdn(1600, 1, 11)) == (1600, 1, 1)
    # Hebrew
    assert hebrew(jdn(2024, 10, 3)) == (5785, 7, 1)
    assert hebrew(jdn(2023, 9, 16)) == (5784, 7, 1)
    assert hebrew(jdn(2024, 4, 23)) == (5784, 1, 15)               # Pesach
    assert hebrew(jdn(2023, 12, 8)) == (5784, 9, 25)               # Chanukah
    assert hebrew(jdn(2024, 3, 24)) == (5784, 13, 14)              # Purim in Adar II
    assert hebrew(jdn(2025, 3, 14)) == (5785, 12, 14)              # Purim in plain Adar
    assert hebrew(jdn(1600, 1, 1)) == (5360, 10, 14)
    for hy in range(5300, 5900):
        assert weekday(hebrew_new_year(hy)) in (1, 2, 4, 6), hy
        yl = hebrew_year_length(hy)
        assert yl in ((383, 384, 385) if hebrew_leap(hy) else (353, 354, 355)), (hy, yl)
        order = [7, 8, 9, 10, 11, 12, 13, 1, 2, 3, 4, 5, 6] if hebrew_leap(hy) else [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
        assert sum(hebrew_month_length(hy, x) for x in order) == yl
    # Islamic
    assert islamic(ISLAMIC_EPOCH) == (1, 1, 1) and islamic_to_jdn(1, 1, 1) == ISLAMIC_EPOCH
    assert islamic(jdn(2024, 3, 11)) == (1445, 9, 1)               # 1 Ramadan 1445 (tabular)
    assert islamic(jdn(2024, 7, 8)) == (1446, 1, 1)               # tabular (Umm al-Qura had 7 July)
    # Jalali
    assert jalali(jdn(2024, 3, 20)) == (1403, 1, 1)
    assert jalali(jdn(2021, 3, 21)) == (1400, 1, 1)
    assert jalali(jdn(2000, 3, 20)) == (1379, 1, 1)
    assert jalali(jdn(2000, 3, 19)) == (1378, 12, 29)              # 1378 common; 1379 leap:
    assert jalali(jdn(2001, 3, 20)) == (1379, 12, 30)
    assert jalali(jdn(1979, 2, 11)) == (1357, 11, 22)              # 22 Bahman 1357
    # Coptic / Ethiopic
    assert coptic(jdn(2024, 9, 11)) == (1741, 1, 1)
    assert coptic(jdn(2023, 9, 12)) == (1740, 1, 1)
    assert coptic(jdn(2023, 9, 11)) == (1739, 13, 6)               # 6th epagomenal day of a leap year
    assert ethiopic(jdn(2024, 9, 11)) == (2017, 1, 1)
    assert ethiopic(jdn(2024, 9, 11))[1:] == coptic(jdn(2024, 9, 11))[1:]
    # Yazdegerdi
    assert yazdegerdi(YAZDEGERDI_EPOCH) == (1, 1, 1)
    assert yazdegerdi(YAZDEGERDI_EPOCH + 364) == (1, 13, 5)
    # ISO week
    assert iso_week(2024, 12, 30) == (2025, 1)
    assert iso_week(2021, 1, 3) == (2020, 53)
    assert iso_week(2020, 12, 31) == (2020, 53)
    assert iso_week(2019, 12, 30) == (2020, 1)
    assert iso_week(2000, 1, 1) == (1999, 52)
    assert iso_weekday(jdn(2024, 1, 1)) == 1                       # a Monday
    # French Republican
    assert french_republican(jdn(1792, 9, 22)) == (1, 1, 1)
    assert french_republican(jdn(1794, 7, 27)) == (2, 11, 9)       # 9 Thermidor II
    assert french_republican(jdn(1799, 11, 9)) == (8, 2, 18)       # 18 Brumaire VIII
    assert french_republican(jdn(1795, 9, 22)) == (3, 13, 6)       # 6th complementary day of sextile III
    assert french_republican(jdn(1805, 12, 31)) == (14, 4, 10)     # 10 Nivose XIV, the last day
    assert french_republican(jdn(1806, 1, 1)) is None and french_republican(jdn(1792, 9, 21)) is None
    # round trips over the whole 1600-2000 span
    j0, j1 = jdn(1600, 1, 1), jdn(2000, 12, 31)
    names = [s["name"] for s in SYSTEMS]
    assert len(names) == len(set(names))
    for s in SYSTEMS:
        assert s["n"] >= 2 and s["name"].startswith("calendars_")
    smoke = 0
    for j in range(j0, j1 + 1):
        y, m, d = gregorian(j)
        assert jdn(y, m, d) == j
        assert jdn_julian(*julian(j)) == j
        hy, hm, hd = hebrew(j)
        assert hebrew_to_jdn(hy, hm, hd) == j
        assert islamic_to_jdn(*islamic(j)) == j
        assert jalali_to_jdn(*jalali(j)) == j
        cy, cm, cd = coptic(j)
        assert _alexandrian_to_jdn(COPTIC_EPOCH, cy, cm, cd) == j
        if j % 97 == 0 or j == j0 or j == j1:              # ~1,500 dates through every system
            for s in SYSTEMS:
                v = s["fn"](y, m, d, L)
                assert isinstance(v, int) and 0 <= v < s["n"], (s["name"], y, m, d, v)
            smoke += 1
    # the 20 named dates the lens asks for
    named = [(1600, 1, 1), (1610, 2, 29), (1625, 7, 14), (1650, 12, 31), (1666, 9, 2), (1700, 3, 1),
             (1720, 6, 30), (1750, 11, 5), (1776, 7, 4), (1789, 7, 14), (1792, 9, 22), (1794, 7, 27),
             (1800, 2, 28), (1805, 12, 31), (1815, 6, 18), (1848, 2, 24), (1869, 11, 17), (1900, 2, 28),
             (1917, 11, 7), (1945, 5, 8), (1969, 7, 20), (1979, 2, 11), (2000, 12, 31)]
    for (y, m, d) in named:
        for s in SYSTEMS:
            v = s["fn"](y, m, d, L)
            assert isinstance(v, int) and 0 <= v < s["n"], (s["name"], y, m, d, v)
        smoke += 1
    # every state of every system is actually reached somewhere in the span (no dead state)
    seen = {s["name"]: set() for s in SYSTEMS}
    for j in range(j0, j1 + 1, 1):
        y, m, d = gregorian(j)
        for s in SYSTEMS:
            if len(seen[s["name"]]) < s["n"]:
                seen[s["name"]].add(s["fn"](y, m, d, L))
    dead = {k: sorted(set(range(dict((s["name"], s["n"]) for s in SYSTEMS)[k])) - v) for k, v in seen.items()}
    dead = {k: v for k, v in dead.items() if v}
    return smoke, dead


if __name__ == "__main__":
    import time
    t = time.time()
    smoke, dead = _selftest()
    print("systems: %d" % len(SYSTEMS))
    print("smoke dates through every system: %d (all in range)" % smoke)
    print("round-trip days 1600-01-01..2000-12-31: %d" % (jdn(2000, 12, 31) - jdn(1600, 1, 1) + 1))
    print("states never reached in 1600-2000: %s" % (dead if dead else "none except the documented ones"))
    print("%.1fs" % (time.time() - t))
