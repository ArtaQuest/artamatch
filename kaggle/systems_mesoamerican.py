"""systems_mesoamerican.py — every date-computable MESOAMERICAN calendar cycle as a PSEUDO-BODY.

Contract (ArtaMatch pseudo-body round, 2026-09-03): SYSTEMS = [{"name", "n", "desc", "fn"}, ...],
fn(y, m, d, L) -> int state in [0, N-1].  y/m/d is the proleptic GREGORIAN birth date (the corpus
ISO dates), L a dict of that person's sidereal longitudes in degrees — unused here, every cycle
below is a pure function of the day count.  Pure Python, standard library only, deterministic; the
same code runs in the browser under Pyodide.  A state s of N is later placed at (s+1)*360/N degrees
on its own circle by the caller; a CONSTANT offset in any cycle (which day is "first") is absorbed
by the fitted phase, so only cycle LENGTHS and BOUNDARIES matter — those are exact here.

CORRELATION.  GMT 584283: Long Count 0.0.0.0.0 (13.0.0.0.0) = JDN 584283 = 11 August 3114 BCE
(proleptic Gregorian) = 4 Ahau 8 Cumku, Lord of the Night G9.  D below is days since that day.

TABLES (documented in code; 0-based state = row index):
  Tzolk'in day signs (20), Yucatec / Aztec:
     0 Imix/Cipactli   1 Ik'/Ehecatl     2 Ak'bal/Calli    3 K'an/Cuetzpalin  4 Chikchan/Coatl
     5 Kimi/Miquiztli  6 Manik'/Mazatl   7 Lamat/Tochtli   8 Muluk/Atl        9 Ok/Itzcuintli
    10 Chuwen/Ozomatli 11 Eb/Malinalli  12 Ben/Acatl      13 Ix/Ocelotl      14 Men/Cuauhtli
    15 Kib/Cozcacuauhtli 16 Kaban/Ollin 17 Etz'nab/Tecpatl 18 Kawak/Quiahuitl 19 Ajaw/Xochitl
  Colour/direction of a day sign = sign % 4:  0 east/red (Imix, Chikchan, Muluk, Ben, Kaban),
     1 north/white (Ik', Kimi, Ok, Ix, Etz'nab), 2 west/black (Ak'bal, Manik', Chuwen, Men, Kawak),
     3 south/yellow (K'an, Lamat, Eb, Kib, Ajaw).
  Haab months (19):  0 Pop 1 Wo 2 Sip 3 Sotz' 4 Sek 5 Xul 6 Yaxk'in 7 Mol 8 Ch'en 9 Yax 10 Sak
    11 Keh 12 Mak 13 K'ank'in 14 Muwan 15 Pax 16 K'ayab 17 Kumk'u 18 Wayeb (5 days).
  Lords of the Night (9): G1..G9 -> states 0..8; the creation day is G9.
  Year Bearers: the Tzolk'in day on the seating of Pop (0 Pop) of the Haab year holding the date.
    365 % 20 = 5, so the sign steps by five signs a year and only FOUR signs ever carry a year
    (Ik', Manik', Eb, Kaban under this convention; Ak'bal/Lamat/Ben/Etz'nab if 1 Pop is used —
    sign // 5 is the bearer class under either convention).  365 % 13 = 1, so the tone steps by
    one a year: the 4 x 13 = 52-year Calendar Round of years.
  819-day count: stations are the days with D = -3 (mod 819) — the one preceding the creation is
    12.19.13.3.0, 1 Ajaw 18 Sotz', 2460 days before 4 Ajaw 8 Kumk'u (Thompson).  819 = 7 x 9 x 13,
    so every station falls on tone 1 and the same Lord of the Night.  Stations rotate through the
    four directions (east, north, west, south) — station index % 4.
  Venus (Dresden Codex table): base 9.9.9.16.0, 1 Ajaw 18 K'ayab, D = 1,364,360; canonical
    synodic period 584 days split 236 (morning star) + 90 (superior conjunction) + 250 (evening
    star) + 8 (inferior conjunction); five periods = 2920 days = eight Haab years (the Venus
    round); the table holds 65 periods = 13 rounds = 104 years.  This is the CALENDRICAL Venus,
    not the planet — the true synodic period is 583.92 days, and the corpus carries the real one.
  Aztec tonalpohualli / xiuhpohualli: under the Caso correlation (fall of Tenochtitlan, 13 August
    1521 Julian = 1 Coatl) the Aztec day sign and number coincide EXACTLY with the Maya Tzolk'in
    under GMT 584283 (verified in the smoke test below: that day is 1 Chikchan).  The Aztec
    trecena and veintena are therefore the same cycles with at most a constant offset, which the
    fit absorbs, so NO separate Aztec pseudo-body is added — as the lens instructs.
  Long Count positions (k'in 20, winal 18, tun 360, k'atun 20, the 13-k'atun "may" cycle) are
    added as the calendar's own cycles.  The k'in position (D % 20) is the Tzolk'in day sign
    shifted by a constant and is NOT added.  The bak'tun (12.0.0.0.0 = 1618) takes only two
    values across 1600-2000 — a step, not a cycle — and is NOT added.
"""

# ----------------------------------------------------------------------------------------- helpers
def jdn(y, m, d):
    """Julian Day Number of a proleptic Gregorian date (Fliegel & Van Flandern 1968)."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045

def jdn_julian(y, m, d):
    """Julian Day Number of a JULIAN-calendar date (used only to check the Caso correlation)."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083

def ayanamsa(y):
    """Lahiri ayanamsa in degrees for year y (tropical = sidereal + ayanamsa); a few arcminutes."""
    return 23.853 + 0.013971 * (y - 2000)

GMT = 584283                 # JDN of 0.0.0.0.0 (Goodman-Martinez-Thompson, 584283 variant)
KIN0_AT_ERA = 159            # 4 Ajaw = kin 160 (1-based) of the 260: (159 % 13) + 1 = 4, 159 % 20 = 19 Ajaw
HAAB_AT_ERA = 348            # 8 Kumk'u = 17 * 20 + 8
G_AT_ERA = 8                 # Lord of the Night G9 (0-based 8)
STATION_819_OFFSET = 3       # stations at D = -3 (mod 819); 12.19.13.3.0 precedes the era by 2460 = 3*819 + 3
VENUS_BASE = 1364360         # 9.9.9.16.0 = 9*144000 + 9*7200 + 9*360 + 16*20, 1 Ajaw 18 K'ayab
VENUS_PERIOD = 584
VENUS_STATIONS = (236, 326, 576)     # cumulative: morning | superior conj | evening | inferior conj
VENUS_ROUND = 5 * VENUS_PERIOD       # 2920 = 8 * 365
DRESDEN_ROUNDS = 13                  # 65 periods = 13 rounds = 37,960 days = 104 Haab years
CALENDAR_ROUND = 18980               # lcm(260, 365) = 52 Haab years

def days(y, m, d):
    """Days since the era (Long Count 0.0.0.0.0)."""
    return jdn(y, m, d) - GMT

def kin0(D):
    """0-based Tzolk'in kin: 0 = 1 Imix ... 259 = 13 Ajaw."""
    return (D + KIN0_AT_ERA) % 260

def haab_doy(D):
    """0-based Haab day of year: 0 = 0 Pop (seating of Pop) ... 364 = 4 Wayeb."""
    return (D + HAAB_AT_ERA) % 365

def haab_year_index(D):
    """Index of the Haab year holding D, counted from the year that holds the era day."""
    return (D + HAAB_AT_ERA) // 365

def year_bearer_kin0(D):
    """Kin (0-based) of 0 Pop of the Haab year holding D."""
    return kin0(D - haab_doy(D))

# ----------------------------------------------------------------------------------------- Tzolk'in
def tz_kin(y, m, d, L):      return kin0(days(y, m, d))                       # 260
def tz_sign(y, m, d, L):     return kin0(days(y, m, d)) % 20                  # 20
def tz_tone(y, m, d, L):     return kin0(days(y, m, d)) % 13                  # 13 (tone - 1)
def tz_trecena(y, m, d, L):  return kin0(days(y, m, d)) // 13                 # 20 (1 Imix, 1 Ix, 1 Manik', ...)
def tz_colour(y, m, d, L):   return kin0(days(y, m, d)) % 20 % 4              # 4 east/north/west/south
def tz_quarter(y, m, d, L):  return kin0(days(y, m, d)) // 65                 # 4 directional 65-day quarters
def tz_burner(y, m, d, L):   return kin0(days(y, m, d)) % 65                  # 65 Burner (Ah Toc) cycle phase

# ----------------------------------------------------------------------------------------- Haab
def hb_doy(y, m, d, L):      return haab_doy(days(y, m, d))                   # 365
def hb_month(y, m, d, L):    return haab_doy(days(y, m, d)) // 20             # 19 (Wayeb = 18)
def hb_day(y, m, d, L):      return haab_doy(days(y, m, d)) % 20              # 20 (Wayeb reaches only 4)

# ----------------------------------------------------------------------------------------- Lords of the Night
def lord_night(y, m, d, L):  return (days(y, m, d) + G_AT_ERA) % 9            # 9 G1..G9

# ----------------------------------------------------------------------------------------- Year Bearers
def yb_sign(y, m, d, L):     return (year_bearer_kin0(days(y, m, d)) % 20) // 5     # 4 bearer classes
def yb_tone(y, m, d, L):     return year_bearer_kin0(days(y, m, d)) % 13            # 13
def yb_round(y, m, d, L):    return haab_year_index(days(y, m, d)) % 52             # 52-year Calendar Round of years
def cr_day(y, m, d, L):      return days(y, m, d) % CALENDAR_ROUND                  # 18980 Calendar Round day

# ----------------------------------------------------------------------------------------- 819-day count
def st819_station(y, m, d, L): return ((days(y, m, d) + STATION_819_OFFSET) // 819) % 4   # 4 directions
def st819_phase(y, m, d, L):   return (days(y, m, d) + STATION_819_OFFSET) % 819          # 819 days since station

# ----------------------------------------------------------------------------------------- Venus (Dresden)
def _vphase(D):              return (D - VENUS_BASE) % VENUS_PERIOD
def venus_phase(y, m, d, L): return _vphase(days(y, m, d))                                  # 584
def venus_station(y, m, d, L):                                                              # 4
    p = _vphase(days(y, m, d))
    return 0 if p < VENUS_STATIONS[0] else 1 if p < VENUS_STATIONS[1] else 2 if p < VENUS_STATIONS[2] else 3
def venus_round_year(y, m, d, L): return ((days(y, m, d) - VENUS_BASE) % VENUS_ROUND) // 365     # 8 Haab years in the round
def venus_round_cycle(y, m, d, L): return ((days(y, m, d) - VENUS_BASE) % VENUS_ROUND) // VENUS_PERIOD  # 5 periods in the round
def venus_dresden_row(y, m, d, L): return ((days(y, m, d) - VENUS_BASE) // VENUS_ROUND) % DRESDEN_ROUNDS  # 13 rounds in the table

# ----------------------------------------------------------------------------------------- Long Count
def lc_winal(y, m, d, L):    return (days(y, m, d) % 360) // 20       # 18 winals in a tun
def lc_tun_day(y, m, d, L):  return days(y, m, d) % 360               # 360 days in a tun
def lc_tun(y, m, d, L):      return (days(y, m, d) // 360) % 20       # 20 tuns in a k'atun
def lc_katun(y, m, d, L):    return (days(y, m, d) // 7200) % 20      # 20 k'atuns in a bak'tun
def lc_may(y, m, d, L):      return (days(y, m, d) // 7200) % 13      # 13-k'atun "may" cycle (7200 % 13 = 11, all 13 tones)

SYSTEMS = [
    {"name": "mesoamerican_tz_kin",        "n": 260,   "desc": "Tzolk'in kin, 0 = 1 Imix ... 259 = 13 Ajaw (GMT 584283)", "fn": tz_kin},
    {"name": "mesoamerican_tz_sign",       "n": 20,    "desc": "Tzolk'in day sign, Imix..Ajaw", "fn": tz_sign},
    {"name": "mesoamerican_tz_tone",       "n": 13,    "desc": "Tzolk'in tone 1..13 (Aztec day number; 13 Lords of the Day)", "fn": tz_tone},
    {"name": "mesoamerican_tz_trecena",    "n": 20,    "desc": "Trecena, kin // 13: the 13-day period named by its first day (1 Imix, 1 Ix, ...)", "fn": tz_trecena},
    {"name": "mesoamerican_tz_colour",     "n": 4,     "desc": "Colour/direction of the day sign: east red, north white, west black, south yellow", "fn": tz_colour},
    {"name": "mesoamerican_tz_quarter",    "n": 4,     "desc": "Directional 65-day quarter of the 260 (1 Imix, 1 Kimi, 1 Chuwen, 1 Kib)", "fn": tz_quarter},
    {"name": "mesoamerican_tz_burner",     "n": 65,    "desc": "Burner (Ah Toc) 65-day cycle phase, kin % 65", "fn": tz_burner},
    {"name": "mesoamerican_haab_doy",      "n": 365,   "desc": "Haab day of year, 0 = seating of Pop ... 364 = 4 Wayeb", "fn": hb_doy},
    {"name": "mesoamerican_haab_month",    "n": 19,    "desc": "Haab month Pop..Kumk'u, Wayeb = 18", "fn": hb_month},
    {"name": "mesoamerican_haab_day",      "n": 20,    "desc": "Haab day in month 0..19 (Wayeb only 0..4)", "fn": hb_day},
    {"name": "mesoamerican_lord_night",    "n": 9,     "desc": "Lord of the Night G1..G9 (era day = G9)", "fn": lord_night},
    {"name": "mesoamerican_yb_sign",       "n": 4,     "desc": "Year Bearer sign class: Ik'/Manik'/Eb/Kaban (sign // 5), 4-year cycle", "fn": yb_sign},
    {"name": "mesoamerican_yb_tone",       "n": 13,    "desc": "Year Bearer tone, 13-year cycle", "fn": yb_tone},
    {"name": "mesoamerican_yb_round",      "n": 52,    "desc": "Year of the 52-year Calendar Round (bearer sign x tone)", "fn": yb_round},
    {"name": "mesoamerican_cr_day",        "n": 18980, "desc": "Calendar Round day, D % 18980 (0 = 4 Ajaw 8 Kumk'u)", "fn": cr_day},
    {"name": "mesoamerican_819_station",   "n": 4,     "desc": "819-day count station direction (east, north, west, south)", "fn": st819_station},
    {"name": "mesoamerican_819_phase",     "n": 819,   "desc": "Days since the 819-day count station (stations at D = -3 mod 819)", "fn": st819_phase},
    {"name": "mesoamerican_venus_phase",   "n": 584,   "desc": "Dresden Venus 584-day phase from 9.9.9.16.0 1 Ajaw 18 K'ayab", "fn": venus_phase},
    {"name": "mesoamerican_venus_station", "n": 4,     "desc": "Dresden Venus station: morning 236 | superior 90 | evening 250 | inferior 8", "fn": venus_station},
    {"name": "mesoamerican_venus_round8",  "n": 8,     "desc": "Haab year within the 2920-day Venus round (5 periods = 8 years)", "fn": venus_round_year},
    {"name": "mesoamerican_venus_round5",  "n": 5,     "desc": "Venus period within the 2920-day round (5 periods)", "fn": venus_round_cycle},
    {"name": "mesoamerican_venus_dresden13", "n": 13,  "desc": "Round within the Dresden table (13 rounds = 65 periods = 104 years)", "fn": venus_dresden_row},
    {"name": "mesoamerican_lc_winal",      "n": 18,    "desc": "Long Count winal within the tun", "fn": lc_winal},
    {"name": "mesoamerican_lc_tun_day",    "n": 360,   "desc": "Long Count day within the tun, D % 360", "fn": lc_tun_day},
    {"name": "mesoamerican_lc_tun",        "n": 20,    "desc": "Long Count tun within the k'atun", "fn": lc_tun},
    {"name": "mesoamerican_lc_katun",      "n": 20,    "desc": "Long Count k'atun within the bak'tun", "fn": lc_katun},
    {"name": "mesoamerican_lc_may",        "n": 13,    "desc": "13-k'atun may cycle (k'atun ending tone), ~256 years", "fn": lc_may},
]
NST = {s["name"]: s["n"] for s in SYSTEMS}

def states(y, m, d, L):
    """Every state at once: {name: state}."""
    return {s["name"]: s["fn"](y, m, d, L) for s in SYSTEMS}

def angles(y, m, d, L):
    """Every state as its pseudo-body angle, (s+1)*360/N degrees, in SYSTEMS order."""
    return [(s["fn"](y, m, d, L) + 1) * 360.0 / s["n"] for s in SYSTEMS]

# ----------------------------------------------------------------------------------------- self-test
def _selftest():
    # Anchors (all proleptic Gregorian unless stated).
    assert jdn(2000, 1, 1) == 2451545
    assert jdn(-3113, 8, 11) == GMT, jdn(-3113, 8, 11)                # 11 Aug 3114 BCE = astronomical year -3113
    L = {}
    era = (-3113, 8, 11)
    assert tz_tone(*era, L) == 3 and tz_sign(*era, L) == 19, "era day is 4 Ajaw"
    assert hb_month(*era, L) == 17 and hb_day(*era, L) == 8, "era day is 8 Kumk'u"
    assert lord_night(*era, L) == 8, "era day is G9"
    assert st819_phase(*era, L) == 3, "12.19.13.3.0 is 3 days short of 3 x 819 before the era"
    # 12.19.13.3.0 = 1 Ajaw 18 Sotz' (Thompson's 819-day station before the era): D = -2460
    D = -2460; k = kin0(D); h = haab_doy(D)
    assert k % 13 == 0 and k % 20 == 19 and h // 20 == 3 and h % 20 == 18, (k, h)
    # Dresden Venus base 9.9.9.16.0 = 1 Ajaw 18 K'ayab
    k = kin0(VENUS_BASE); h = haab_doy(VENUS_BASE)
    assert k % 13 == 0 and k % 20 == 19 and h // 20 == 16 and h % 20 == 18, (k, h)
    # 21 Dec 2012 = 13.0.0.0.0 = 4 Ajaw 3 K'ank'in
    end = (2012, 12, 21)
    assert days(2012, 12, 21) == 13 * 144000
    assert tz_tone(*end, L) == 3 and tz_sign(*end, L) == 19 and hb_month(*end, L) == 13 and hb_day(*end, L) == 3
    # Caso: fall of Tenochtitlan, 13 Aug 1521 JULIAN = 1 Coatl (Aztec) — must be 1 Chikchan (Maya) under GMT.
    Dc = jdn_julian(1521, 8, 13) - GMT
    assert kin0(Dc) % 13 == 0 and kin0(Dc) % 20 == 4, ("Caso/GMT disagree", kin0(Dc))
    # Pakal's birth: 9.8.9.13.0, 8 Ajaw 13 Pop = 21 March 603 Julian = 24 March 603 proleptic Gregorian
    # (the often-quoted 23 March is the 584285 variant of the correlation, two days later)
    Dp = 9 * 144000 + 8 * 7200 + 9 * 360 + 13 * 20
    assert kin0(Dp) % 13 == 7 and kin0(Dp) % 20 == 19 and haab_doy(Dp) == 13, (kin0(Dp), haab_doy(Dp))
    assert jdn_julian(603, 3, 21) - GMT == Dp and jdn(603, 3, 24) - GMT == Dp and _ymd(Dp + GMT) == (603, 3, 24)
    # Smoke: 24+ dates spanning 1600-2000 with a synthetic L; every state in range, every fn int.
    import random
    rng = random.Random(7)
    dates = [(1600, 1, 1), (1618, 9, 18), (1650, 6, 15), (1700, 2, 28), (1750, 12, 31), (1800, 7, 4),
             (1850, 3, 3), (1900, 1, 1), (1900, 2, 28), (1900, 3, 1), (1950, 10, 10), (2000, 12, 31),
             (1666, 6, 6), (1789, 7, 14), (1815, 6, 18), (1865, 4, 14), (1914, 8, 4), (1945, 8, 15),
             (1969, 7, 20), (1999, 12, 31), (1604, 2, 29), (1896, 2, 29), (1700, 3, 1), (1999, 1, 1)]
    dates += [(rng.randint(1600, 2000), rng.randint(1, 12), rng.randint(1, 28)) for _ in range(76)]
    Ls = {"sun": 123.4, "moon": 45.6, "mercury": 1.0, "venus": 359.9, "mars": 200.0, "jupiter": 0.0,
          "saturn": 180.0, "uranus": 90.0, "neptune": 270.0, "pluto": 33.3, "node": 66.6, "chiron": 99.9, "lilith": 12.0}
    seen = {s["name"]: set() for s in SYSTEMS}
    for (y, m, d) in dates:
        for s in SYSTEMS:
            v = s["fn"](y, m, d, Ls)
            assert type(v) is int, (s["name"], v)
            assert 0 <= v < s["n"], (s["name"], (y, m, d), v)
            seen[s["name"]].add(v)
        a = angles(y, m, d, Ls)
        assert all(0.0 < x <= 360.0 for x in a)
    # Range exhaustiveness on a long window: every small-N system must visit every state.
    for s in SYSTEMS:
        if s["n"] <= 365:
            vis = set(s["fn"](1900, 1, 1, Ls) for _ in [0])
            base = jdn(1900, 1, 1)
            span = 366 * 60 if s["n"] <= 52 else 366 * 3
            vis = {s["fn"](*_ymd(base + i), Ls) for i in range(0, span, 1 if s["n"] <= 365 else 1)}
            if s["name"] in ("mesoamerican_yb_sign", "mesoamerican_yb_tone", "mesoamerican_yb_round",
                             "mesoamerican_819_station", "mesoamerican_venus_round8", "mesoamerican_venus_round5",
                             "mesoamerican_lc_tun", "mesoamerican_lc_katun", "mesoamerican_lc_may", "mesoamerican_venus_dresden13"):
                continue  # slow cycles, checked by construction (modulo arithmetic on D)
            assert len(vis) == s["n"], (s["name"], len(vis), s["n"])
    return len(dates)

def _ymd(j):
    """Inverse Fliegel-Van Flandern: JDN -> proleptic Gregorian (y, m, d)."""
    l = j + 68569
    n = 4 * l // 146097
    l = l - (146097 * n + 3) // 4
    i = 4000 * (l + 1) // 1461001
    l = l - 1461 * i // 4 + 31
    jj = 80 * l // 2447
    d = l - 2447 * jj // 80
    l = jj // 11
    m = jj + 2 - 12 * l
    y = 100 * (n - 49) + i + l
    return y, m, d

if __name__ == "__main__":
    import sys
    n = _selftest()
    print(f"systems_mesoamerican: {len(SYSTEMS)} systems, self-test OK on {n} dates 1600-2000 + 6 historical anchors")
    for s in SYSTEMS:
        print(f"  {s['name']:34s} n={s['n']:<6d} {s['desc']}")
    if "--build" in sys.argv:
        # Optional: write AQ_DIR/systems_mesoamerican.npz in the fit_nested.py layout.
        import os, numpy as np, pandas as pd
        D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
        full = pd.read_csv(f"{D_}/full.csv", dtype=str)
        def side(col):
            out = []
            for iso in full[col]:
                y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
                out.append(angles(y, m, d, {}))
            return np.array(out, np.float64)
        A, B = side("true_dob_a"), side("true_dob_b")
        np.savez_compressed(f"{D_}/systems_mesoamerican.npz", theta_a_sys=A, theta_b_sys=B,
                            names=np.array([s["name"] for s in SYSTEMS]), nstates=np.array([s["n"] for s in SYSTEMS]))
        print(f"wrote {D_}/systems_mesoamerican.npz · {len(SYSTEMS)} systems x {len(full):,} couples")
