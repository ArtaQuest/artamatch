"""systems_east-asian.py — the CHINESE / EAST ASIAN date systems (BaZi Four Pillars, Nine-Star Ki,
Kua, the 28 day-mansions, rokuyo) as PSEUDO-BODIES for the ArtaMatch phasor fitter.

Contract (round "east-asian", 2026-09-03):
  SYSTEMS = [{"name": "east-asian_<system>", "n": N, "desc": ..., "fn": fn}, ...]
  fn(y, m, d, L) -> int state in [0, N-1].  L is a dict of the person's SIDEREAL longitudes in
  degrees ({"sun":..., "moon":..., ...}, Lahiri, 12:00 UT); the builder also passes
  L["_female"] = True/False for the gendered Kua.  Pure Python, standard library only, deterministic;
  the same code runs in the browser under Pyodide.  Any state s of N becomes the angle
  (s+1)*360/N on the system's own circle (that is done by the builder, not here).

Everything below is DATE-ONLY (plus the tropical Sun, which is the sidereal Sun the corpus already
holds plus the Lahiri ayanamsa).  Nothing here reads the label, the record depth or a name.

CONVENTIONS (a constant offset in a cycle is absorbed by the fitted phase; the LENGTH and the
BOUNDARY of each cycle are what matter, and those are exact):
  * Stems  0..9  = 甲乙丙丁戊己庚辛壬癸 (Jia Yi Bing Ding Wu Ji Geng Xin Ren Gui).
  * Branches 0..11 = 子丑寅卯辰巳午未申酉戌亥 (Zi Chou Yin Mao Chen Si Wu Wei Shen You Xu Hai =
    Rat Ox Tiger Rabbit Dragon Snake Horse Goat Monkey Rooster Dog Pig; Vietnam says Cat for Mao
    and Buffalo for Chou, Korea/Japan the same twelve — SAME cycle, same boundary).
  * Sexagenary 0..59: index i has stem i%10 and branch i%12 (甲子 = 0).
  * Elements 0..4 = wood fire earth metal water.  Polarity 0 = yang, 1 = yin.
  * The YEAR pillar changes at LI CHUN (tropical Sun = 315 deg, about 4 Feb), NOT on 1 January.
    Year cycle anchor: 1984 = 甲子 (year sexagenary 0), so year stem = (cy-4)%10, branch (cy-4)%12.
  * The MONTH pillar changes at the twelve "jie" solar terms, every 30 deg of tropical Sun from
    Li Chun: month index k = floor(((trop_sun - 315) mod 360)/30), k = 0 is the Tiger month (寅).
    Month stem by the FIVE TIGERS rule: the Tiger month of a 甲/己 year is 丙, 乙/庚 -> 戊,
    丙/辛 -> 庚, 丁/壬 -> 壬, 戊/癸 -> 甲; then one stem per month.
  * The DAY pillar: sexagenary sx = (JDN + 49) mod 60 (2000-01-01, JDN 2451545, is 戊午 = 54).
    Days are taken at the civil date, ignoring the 23:00 Zi-hour convention (birth hour unknown).
  * NAYIN (纳音): the 60-cycle is read in 30 pairs; the classic table below gives each pair's
    element.  Reported as the 5-state element (the lens) and, as extras, the 30-state pair.
  * TRINES (三合): branches {子辰申} {丑巳酉} {寅午戌} {卯未亥} = branch mod 4.
  * NINE-STAR KI: year star = 11 - digitroot(Li Chun year) (wrapping to 1..9): 1984 = 7, 2000 = 9.
    Month star: the Tiger month of a 1/4/7 year is 8, 2/5/8 -> 5, 3/6/9 -> 2, then descending.
  * KUA (八宅): digit-root s of the Li Chun year; born before 2000: male 10-s, female 5+s;
    2000 on: male 9-s, female 6+s; reduce to 1..9 (0 -> 9); a 5 becomes 2 (male) / 8 (female).
  * 28 MANSIONS OF THE DAY (二十八宿值日): a plain 28-day cycle locked to the week — 房虚昴星 fall
    on Sundays, 角 on Thursday — index = (JDN + 11) mod 28 (角 = 0), the koyomi convention; the
    4-way phase inside the weekday class is a constant the fit absorbs.  This is the DAY cycle,
    not the Moon's sidereal mansion (that would quantise the Moon the bank already carries).
  * ROKUYO (六曜): properly (lunar month + lunar day) mod 6 on the Chinese lunar calendar.
    Two versions: `rokuyo` approximates the lunar calendar from the Sun-Moon elongation (lunar
    day) and the zhongqi rule (month number, leap months folded to the prior month); `rokuyo_jdn`
    is the lens's stated stand-in, (JDN mod 6) — SAID PLAINLY: that is a 6-day cycle, not the
    calendrical rokuyo, which resets at every lunar month.
  Not implemented: the Nine-Star Ki DAY star (needs the solstice-locked yin/yang-dun switch and
  the 240-day pattern; no clean date-only rule) and the hour pillar (no birth hour).
"""
import math

SLUG = "east-asian"

# ---------------------------------------------------------------- helpers (stdlib only)
def jdn(y, m, d):
    """Fliegel–Van Flandern Julian Day Number of a proleptic Gregorian civil date."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045

def ayanamsa(y):
    """Lahiri ayanamsa in degrees, linear in the year (good to a few arcminutes)."""
    return 23.853 + 0.013971 * (y - 2000)

def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and abs(x) != float("inf")

def _approx_trop_sun(y, m, d):
    """Fallback tropical Sun (deg) at 12:00 UT from the date alone (low-precision solar theory,
    ~0.01 deg): only used when L carries no usable 'sun'."""
    n = jdn(y, m, d) - 2451545
    Lm = (280.460 + 0.9856474 * n) % 360.0
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    return (Lm + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360.0

def tropical_sun(y, m, d, L):
    s = L.get("sun") if isinstance(L, dict) else None
    if _num(s):
        return (float(s) + ayanamsa(y)) % 360.0
    return _approx_trop_sun(y, m, d)

def sidereal_moon(y, m, d, L):
    mo = L.get("moon") if isinstance(L, dict) else None
    if _num(mo):
        return float(mo) % 360.0
    # fallback: mean lunar longitude (tropical) minus ayanamsa; ~5 deg error, never NaN
    n = jdn(y, m, d) - 2451545
    return ((218.316 + 13.176396 * n) - ayanamsa(y)) % 360.0

def digit_root(t):
    t = abs(int(t))
    while t > 9:
        t = sum(int(c) for c in str(t))
    return t

def li_chun_year(y, m, d, L):
    """The BaZi year: the civil year, minus one for births between 1 Jan and Li Chun."""
    ts = tropical_sun(y, m, d, L)
    return y - 1 if (m <= 2 and ts < 315.0) else y

def month_index(y, m, d, L):
    """0 = Tiger month (from Li Chun), 1 = Rabbit (from Jing Zhe), ... 11 = Ox."""
    ts = tropical_sun(y, m, d, L)
    return int(((ts - 315.0) % 360.0) // 30.0) % 12

def year_sx(y, m, d, L):
    return (li_chun_year(y, m, d, L) - 4) % 60

def month_sx(y, m, d, L):
    ys = year_sx(y, m, d, L) % 10
    k = month_index(y, m, d, L)
    tiger_stem = ((ys % 5) * 2 + 2) % 10          # five-tigers rule
    stem = (tiger_stem + k) % 10
    branch = (2 + k) % 12                          # Tiger = 寅 = 2
    # the unique sexagenary index with this stem and branch (they always share parity)
    for i in range(60):
        if i % 10 == stem and i % 12 == branch:
            return i
    return (stem * 6) % 60  # unreachable

def day_sx(y, m, d, L=None):
    return (jdn(y, m, d) + 49) % 60

# NAYIN table: 30 pairs of the 60-cycle -> element index (0 wood, 1 fire, 2 earth, 3 metal, 4 water)
# 甲子乙丑海中金 丙寅丁卯炉中火 戊辰己巳大林木 庚午辛未路旁土 壬申癸酉剑锋金 甲戌乙亥山头火
# 丙子丁丑涧下水 戊寅己卯城头土 庚辰辛巳白蜡金 壬午癸未杨柳木 甲申乙酉泉中水 丙戌丁亥屋上土
# 戊子己丑霹雳火 庚寅辛卯松柏木 壬辰癸巳长流水 甲午乙未沙中金 丙申丁酉山下火 戊戌己亥平地木
# 庚子辛丑壁上土 壬寅癸卯金箔金 甲辰乙巳覆灯火 丙午丁未天河水 戊申己酉大驿土 庚戌辛亥钗钏金
# 壬子癸丑桑柘木 甲寅乙卯大溪水 丙辰丁巳沙中土 戊午己未天上火 庚申辛酉石榴木 壬戌癸亥大海水
NAYIN = [3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4, 3, 1, 0, 2, 3, 1, 4, 2, 3, 4, 4, 2, 1, 0, 4]
assert len(NAYIN) == 30

# hidden element of each branch: 子water 丑earth 寅wood 卯wood 辰earth 巳fire 午fire 未earth 申metal 酉metal 戌earth 亥water
BRANCH_ELEMENT = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]

def nine_star_year(cy):
    s = 11 - digit_root(cy)
    return s - 9 if s > 9 else s                   # 1..9

def nine_star_month(cy, k):
    ys = nine_star_year(cy)
    tiger = {1: 8, 4: 8, 7: 8, 2: 5, 5: 5, 8: 5, 3: 2, 6: 2, 9: 2}[ys]
    return ((tiger - k - 1) % 9) + 1               # 1..9, descending month by month

def kua(cy, female):
    s = digit_root(cy)
    if cy < 2000:
        k = 5 + s if female else 10 - s
    else:
        k = 6 + s if female else 9 - s
    k = digit_root(k)
    if k == 0:
        k = 9
    if k == 5:
        k = 8 if female else 2
    return k                                       # 1..9

def _female(L):
    return bool(L.get("_female", False)) if isinstance(L, dict) else False

def lunar_month_and_day(y, m, d, L):
    """Approximate Chinese lunar (month 1..12, day 1..30) from Sun-Moon elongation and the zhongqi
    rule.  Lunar day = floor(elongation/12) + 1.  Month number = the zhongqi (Sun at 330 + 30(n-1))
    first reached at or after the month's new moon; if that zhongqi is more than ~29.5 days of solar
    motion away, the month is intercalary and takes the previous month's number."""
    ts = tropical_sun(y, m, d, L)
    mo = (sidereal_moon(y, m, d, L) + ayanamsa(y)) % 360.0
    elong = (mo - ts) % 360.0
    lday = int(elong // 12.0) + 1                  # 1..30
    age_days = elong / 12.190749                    # mean synodic motion of the elongation
    sun_at_new = (ts - 0.9856474 * age_days) % 360.0
    off = (sun_at_new - 330.0) % 360.0             # degrees past the month-1 zhongqi (雨水)
    n = int(math.ceil(off / 30.0))                 # zhongqi count to the first one at/after new moon
    gap = (n * 30.0 - off) % 360.0
    leap = gap > 29.106                            # 29.53 days of mean solar motion
    month = (n % 12) + 1
    if leap:
        month = ((month - 2) % 12) + 1
    return month, lday

# ---------------------------------------------------------------- the state functions
def year_stem(y, m, d, L):      return year_sx(y, m, d, L) % 10
def year_branch(y, m, d, L):    return year_sx(y, m, d, L) % 12
def year_sexagenary(y, m, d, L): return year_sx(y, m, d, L)
def month_stem(y, m, d, L):     return month_sx(y, m, d, L) % 10
def month_branch(y, m, d, L):   return month_sx(y, m, d, L) % 12
def month_sexagenary(y, m, d, L): return month_sx(y, m, d, L)
def day_stem(y, m, d, L):       return day_sx(y, m, d) % 10
def day_branch(y, m, d, L):     return day_sx(y, m, d) % 12
def day_sexagenary(y, m, d, L): return day_sx(y, m, d)
def year_nayin(y, m, d, L):     return NAYIN[year_sx(y, m, d, L) // 2]
def month_nayin(y, m, d, L):    return NAYIN[month_sx(y, m, d, L) // 2]
def day_nayin(y, m, d, L):      return NAYIN[day_sx(y, m, d) // 2]
def year_nayin30(y, m, d, L):   return year_sx(y, m, d, L) // 2
def day_nayin30(y, m, d, L):    return day_sx(y, m, d) // 2
def year_trine(y, m, d, L):     return year_sx(y, m, d, L) % 12 % 4
def month_trine(y, m, d, L):    return month_sx(y, m, d, L) % 12 % 4
def day_trine(y, m, d, L):      return day_sx(y, m, d) % 12 % 4
def year_stem_element(y, m, d, L):  return (year_sx(y, m, d, L) % 10) // 2
def month_stem_element(y, m, d, L): return (month_sx(y, m, d, L) % 10) // 2
def day_stem_element(y, m, d, L):   return (day_sx(y, m, d) % 10) // 2
def year_polarity(y, m, d, L):  return year_sx(y, m, d, L) % 2
def month_polarity(y, m, d, L): return month_sx(y, m, d, L) % 2
def day_polarity(y, m, d, L):   return day_sx(y, m, d) % 2
def year_branch_element(y, m, d, L):  return BRANCH_ELEMENT[year_sx(y, m, d, L) % 12]
def month_branch_element(y, m, d, L): return BRANCH_ELEMENT[month_sx(y, m, d, L) % 12]
def day_branch_element(y, m, d, L):   return BRANCH_ELEMENT[day_sx(y, m, d) % 12]
def ninestar_year(y, m, d, L):  return nine_star_year(li_chun_year(y, m, d, L)) - 1
def ninestar_month(y, m, d, L): return nine_star_month(li_chun_year(y, m, d, L), month_index(y, m, d, L)) - 1
def kua_number(y, m, d, L):     return kua(li_chun_year(y, m, d, L), _female(L)) - 1
def mansion28(y, m, d, L):      return (jdn(y, m, d) + 11) % 28
def rokuyo(y, m, d, L):
    mo, dy = lunar_month_and_day(y, m, d, L)
    return (mo + dy) % 6                          # 0 大安 1 赤口 2 先勝 3 友引 4 先負 5 仏滅
def rokuyo_jdn(y, m, d, L):     return jdn(y, m, d) % 6

def _s(name, n, desc, fn):
    return {"name": f"{SLUG}_{name}", "n": n, "desc": desc, "fn": fn}

SYSTEMS = [
    _s("year_stem", 10, "BaZi year heavenly stem (Li Chun year; 甲=0, 1984=甲)", year_stem),
    _s("year_branch", 12, "BaZi year earthly branch = zodiac animal (Li Chun year; 子/Rat=0)", year_branch),
    _s("year_sexagenary", 60, "BaZi year pillar, 60-cycle (甲子=0, 1984)", year_sexagenary),
    _s("month_stem", 10, "BaZi month stem, five-tigers rule from the year stem", month_stem),
    _s("month_branch", 12, "BaZi month branch from tropical Sun (jie every 30 deg from Li Chun; 寅 Tiger=2)", month_branch),
    _s("month_sexagenary", 60, "BaZi month pillar, 60-cycle (stem x branch)", month_sexagenary),
    _s("day_stem", 10, "BaZi day stem, sx=(JDN+49) mod 60", day_stem),
    _s("day_branch", 12, "BaZi day branch, sx=(JDN+49) mod 60", day_branch),
    _s("day_sexagenary", 60, "BaZi day pillar, 60-cycle, (JDN+49) mod 60", day_sexagenary),
    _s("year_nayin", 5, "Nayin element of the year pillar (wood fire earth metal water)", year_nayin),
    _s("month_nayin", 5, "Nayin element of the month pillar", month_nayin),
    _s("day_nayin", 5, "Nayin element of the day pillar", day_nayin),
    _s("year_nayin30", 30, "Nayin pair of the year pillar (30 named sounds)", year_nayin30),
    _s("day_nayin30", 30, "Nayin pair of the day pillar (30 named sounds)", day_nayin30),
    _s("year_trine", 4, "Year animal trine / san-he group (branch mod 4)", year_trine),
    _s("month_trine", 4, "Month branch trine (branch mod 4)", month_trine),
    _s("day_trine", 4, "Day branch trine (branch mod 4)", day_trine),
    _s("year_stem_element", 5, "Element of the year stem", year_stem_element),
    _s("month_stem_element", 5, "Element of the month stem", month_stem_element),
    _s("day_stem_element", 5, "Element of the day stem", day_stem_element),
    _s("year_polarity", 2, "Yin/yang of the year pillar (0 yang)", year_polarity),
    _s("month_polarity", 2, "Yin/yang of the month pillar (0 yang)", month_polarity),
    _s("day_polarity", 2, "Yin/yang of the day pillar (0 yang)", day_polarity),
    _s("year_branch_element", 5, "Hidden element of the year branch", year_branch_element),
    _s("month_branch_element", 5, "Hidden element of the month branch", month_branch_element),
    _s("day_branch_element", 5, "Hidden element of the day branch", day_branch_element),
    _s("ninestar_year", 9, "Nine-Star Ki year star (Li Chun year; 1984=7, 2000=9)", ninestar_year),
    _s("ninestar_month", 9, "Nine-Star Ki month star (solar months from Li Chun)", ninestar_month),
    _s("kua", 9, "Eight-Mansions Kua number, gendered by L['_female'] (Li Chun year)", kua_number),
    _s("mansion28", 28, "28 lunar mansions of the DAY, (JDN+11) mod 28, week-locked (房 on Sunday)", mansion28),
    _s("rokuyo", 6, "Rokuyo (lunar month + lunar day) mod 6; lunar calendar approximated from Sun-Moon elongation at noon UT + zhongqi rule (about +-1 lunar day vs the Beijing-midnight calendar)", rokuyo),
    _s("rokuyo_jdn", 6, "Rokuyo stand-in: JDN mod 6 (a plain 6-day cycle, NOT the calendrical rokuyo)", rokuyo_jdn),
]

# ---------------------------------------------------------------- smoke test
if __name__ == "__main__":
    import random
    rng = random.Random(1234)
    dates = [(1600, 1, 1), (1600, 2, 3), (1600, 2, 5), (1625, 7, 14), (1650, 12, 31), (1675, 3, 1),
             (1700, 2, 29 - 1), (1710, 1, 15), (1725, 10, 5), (1750, 6, 21), (1775, 4, 4),
             (1800, 2, 28), (1825, 9, 9), (1850, 11, 11), (1875, 5, 5), (1900, 1, 1), (1900, 2, 4),
             (1925, 8, 18), (1950, 3, 21), (1960, 6, 30), (1975, 12, 25), (1984, 2, 4), (1984, 2, 5),
             (1999, 12, 31), (2000, 1, 1), (2000, 2, 3), (2000, 2, 5), (2000, 12, 31)]
    bodies = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
              "pluto", "node", "chiron", "lilith"]
    checks = 0
    for (y, m, d) in dates:
        for female in (False, True):
            for kind in ("synthetic", "no_sun", "approx_sun"):
                if kind == "synthetic":
                    L = {b: rng.uniform(0, 360) for b in bodies}
                elif kind == "no_sun":
                    L = {"moon": rng.uniform(0, 360)}
                else:
                    L = {b: rng.uniform(0, 360) for b in bodies}
                    L["sun"] = (_approx_trop_sun(y, m, d) - ayanamsa(y)) % 360.0
                L["_female"] = female
                for S in SYSTEMS:
                    v = S["fn"](y, m, d, L)
                    assert isinstance(v, int) and not isinstance(v, bool), (S["name"], y, m, d, v)
                    assert 0 <= v < S["n"], (S["name"], y, m, d, v)
                    checks += 1
    # anchors
    Lr = {"sun": (_approx_trop_sun(2000, 1, 1) - ayanamsa(2000)) % 360.0}
    assert day_sexagenary(2000, 1, 1, Lr) == 54            # 戊午
    assert year_sexagenary(1984, 6, 1, Lr) == 0            # 甲子
    assert year_stem(2000, 1, 1, Lr) == 5 and year_branch(2000, 1, 1, Lr) == 3   # still 己卯 before Li Chun
    L5 = {"sun": (_approx_trop_sun(2000, 2, 5) - ayanamsa(2000)) % 360.0}
    assert year_stem(2000, 2, 5, L5) == 6 and year_branch(2000, 2, 5, L5) == 4    # 庚辰 after Li Chun
    assert month_branch(2000, 2, 5, L5) == 2 and month_stem(2000, 2, 5, L5) == 4  # 戊寅 (庚 year -> 戊 tiger)
    assert nine_star_year(1984) == 7 and nine_star_year(2000) == 9 and nine_star_year(1960) == 4
    assert kua(1975, False) == 6 and kua(1975, True) == 9 and kua(2007, False) == 9
    assert NAYIN[27] == 1 and NAYIN[0] == 3
    print(f"SMOKE OK: {len(SYSTEMS)} systems x {len(dates)} dates x 2 genders x 3 L-kinds = {checks} state checks in range; anchors OK")
    for S in SYSTEMS:
        print(f"  {S['name']:36s} n={S['n']:3d}  {S['desc']}")
