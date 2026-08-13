"""
trad_chinese.py — Chinese astrology: BaZi (四柱八字), Wu Xing (五行), the 24 jieqi (二十四節氣),
the 28 xiu (二十八宿), Nine Star Ki / 九星 and the Eight Mansions (八宅) kua relation.

WHAT THIS MODULE COMPUTES, AND FROM WHAT

Every feature here descends from four arithmetic objects, all derived from the instant itself — no
tables of "lucky animals", no invented encodings:

  1. THE SEXAGENARY CYCLE (干支), stem (10) x branch (12) = 60.
     YEAR pillar   index = (solar_year - 4) mod 60, 0 = 甲子.  Anchor: 1984 = 甲子 year, the head of
                   the 79th cycle. The solar year turns at LICHUN (立春), when the Sun reaches
                   tropical longitude 315 deg — NOT at Chinese New Year and not on 1 January. This
                   is the BaZi rule (三命通會; every 通書 almanac), and it is computed here from the
                   Sun's own longitude, so no lunisolar calendar table is needed.
     MONTH pillar  branch = 寅 (Tiger) for the 30 deg of solar longitude beginning at Lichun, then
                   forward: month branch = (2 + floor((lam - 315) mod 360 / 30)) mod 12. Astronomical
                   solar-term boundaries, never calendar months. The month STEM comes from the year
                   stem by the 五虎遁 rule ("five tigers escaping": 甲己年起丙寅, 乙庚起戊寅,
                   丙辛起庚寅, 丁壬起壬寅, 戊癸起甲寅), i.e. stem = (2*year_stem + 2 + m) mod 10.
     DAY pillar    index = (JDN - 11) mod 60, JDN = floor(JD + 0.5). THE EPOCH IS STATED AND
                   TESTED: JDN 11 is 甲子. Two independent published anchors fall out exactly and
                   are asserted in __main__ below — 1 Oct 1949 = 甲子日 and 1 Jan 1900 = 甲戌日.
                   The day count has run unbroken since antiquity, so it needs no calendar at all.
     HOUR pillar   *** CANNOT BE COMPUTED. *** The hour pillar needs the birth TIME, and this
                   dataset has birth DATES only (everything is evaluated at 12:00 UT). There is no
                   proxy worth having: at noon the hour branch would be 午 for every single person,
                   a constant, and the hour stem (五鼠遁: stem = (2*day_stem + hour_branch) mod 10)
                   would then be a pure bijection of the day stem — literally zero new information.
                   So the hour pillar is OMITTED rather than faked, and every Wu Xing count below is
                   over SIX characters (three pillars), not the canonical eight. Said plainly here
                   and repeated in each block that depends on it.
                   Second, smaller consequence: the Chinese day boundary is midnight (or 23:00 for
                   the 子 hour under the 早子時/夜子時 dispute) in CHINA local time; with no time and
                   no place, a birth in the last hour of a day carries the wrong day pillar. That is
                   an irreducible ~4% of rows and cannot be detected, let alone fixed.

  2. THE 24 SOLAR TERMS (節氣) at exact 15 deg steps of the Sun's TROPICAL longitude, indexed 0 =
     立春 Lichun at 315 deg. Also the continuous phase within the term, which is the honest
     representation given that a term boundary can fall either side of noon UT.

  3. THE 28 XIU (二十八宿) from the MOON's longitude, in two divisions of the same doctrine:
     equal 28ths, and the classical unequal widths (角12 亢9 氐15 房5 心5 尾18 箕11 斗26 牛8 女12
     虛10 危17 室16 壁9 奎16 婁12 胃14 昴11 畢16 觜2 參9 井33 鬼4 柳15 星7 張18 翼18 軫17 Chinese
     degrees). Both are anchored at SPICA (角宿一, the determinative star of 角), which is put at
     exactly 180 deg by the True Citra ayanamsa — so the origin precesses correctly with no star
     catalogue. Caveat: the true xiu are EQUATORIAL divisions (right ascension); measuring them
     along the ecliptic, as nearly all modern practice does, is an approximation.
     *** THE MOON IS THE WEAKEST INPUT HERE. *** Its noon longitude is off by up to ~6 deg against
     the real birth moment, and a xiu is only 12.86 deg wide, so a xiu label is roughly a coin
     flip between itself and its neighbour. Built anyway (the doctrine is lunar), reported honestly.

  4. THE NINE STARS (九星) from the solar year, on the classical continuous 年紫白 count
     star = ((1 - solar_year) mod 9) + 1, calibrated on the published annual stars 2017 = 1白,
     2018 = 9紫 ... 2024 = 3碧. This is identical to the Nine Star Ki 本命星 and to the MALE Ming
     Gua of 八宅; the FEMALE Ming Gua is (solar_year - 5) mod 9. We do not know either partner's
     sex, so both are emitted for both partners and the Eight Mansions relation is computed for all
     four sex assignments.

RELATIONS BETWEEN THE TWO PEOPLE — the part the tradition actually stakes its claim on. Every one
of these is a closed-form rule, cited where it is defined:
  三合 trine (申子辰 · 亥卯未 · 寅午戌 · 巳酉丑) — equivalently branch mod 4;
  三會 directional trio (寅卯辰 · 巳午未 · 申酉戌 · 亥子丑); 半合 half-trine;
  六合 secret friends (a+b) mod 12 == 1; 六沖 clash |a-b| == 6; 六害 harm (a+b) mod 12 == 7;
  六破 destruction (子酉 丑辰 寅亥 卯午 巳申 未戌); 三刑 punishment (寅巳申 · 丑戌未 · 子卯) and
  自刑 self-punishment (辰辰 午午 酉酉 亥亥); 天干五合 (甲己 乙庚 丙辛 丁壬 戊癸, |a-b| == 5) and
  天干相沖 (甲庚 乙辛 丙壬 丁癸, |a-b| == 6), hence the named 天合地合 and 天克地沖 pairings;
  納音 (the 30 two-pillar hidden elements of 六十甲子); 十二長生 (the day stem's stage in a branch);
  五行生剋 (Wood->Fire->Earth->Metal->Water generating, Wood->Earth->Water->Fire->Metal overcoming);
  八宅遊年 (Eight Mansions), derived from trigram line changes, not from a memorised grid:
  no line changed = 伏位, top = 生氣, bottom+middle = 天醫, all three = 延年, bottom = 禍害,
  bottom+top = 六煞, middle+top = 五鬼, middle = 絕命. Verified against the published tables for
  坎 (生氣 SE, 絕命 SW) and 乾 (生氣 W, 天醫 NE, 延年 SW, 絕命 S).
  建除十二客 the day officer, (day branch - month branch) mod 12, which is what the almanac
  actually uses to choose a wedding day — computed for the wedding instant, together with the
  classical 忌 rule that the wedding day must not clash (沖) with either partner's animal.

WEIGHTS: where a tradition tallies its relations into a single number the weights differ between
texts, so every weighted score is emitted ALONGSIDE the raw unweighted flags it was built from.
The flags are the doctrine; the weights are one reading of it.
"""

import numpy as np

TRADITION = "Chinese (BaZi four pillars, Wu Xing, 24 jieqi, 28 xiu, Nine Star Ki)"

# ── the ten heavenly stems 天干 ──────────────────────────────────────────────────────────────────
# 甲乙 Wood · 丙丁 Fire · 戊己 Earth · 庚辛 Metal · 壬癸 Water; elements 0=Wood 1=Fire 2=Earth
# 3=Metal 4=Water throughout this module.
STEM_EL = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
STEM_YANG = np.array([1., 0., 1., 0., 1., 0., 1., 0., 1., 0.])

# ── the twelve earthly branches 地支 (子丑寅卯辰巳午未申酉戌亥) ────────────────────────────────
BRANCH_EL = np.array([4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4])

# 地支藏干 — the stems hidden in each branch, with the common 本氣/中氣/餘氣 weighting
# (main 0.6, middle 0.3, residual 0.1; 0.7/0.3 for the two-stem branches; 1.0 when alone).
HIDDEN = {
    0:  [(9, 1.0)],                           # 子 癸
    1:  [(5, .6), (9, .3), (7, .1)],          # 丑 己癸辛
    2:  [(0, .6), (2, .3), (4, .1)],          # 寅 甲丙戊
    3:  [(1, 1.0)],                           # 卯 乙
    4:  [(4, .6), (1, .3), (9, .1)],          # 辰 戊乙癸
    5:  [(2, .6), (4, .3), (6, .1)],          # 巳 丙戊庚
    6:  [(3, .7), (5, .3)],                   # 午 丁己
    7:  [(5, .6), (3, .3), (1, .1)],          # 未 己丁乙
    8:  [(6, .6), (8, .3), (4, .1)],          # 申 庚壬戊
    9:  [(7, 1.0)],                           # 酉 辛
    10: [(4, .6), (7, .3), (3, .1)],          # 戌 戊辛丁
    11: [(8, .7), (0, .3)],                   # 亥 壬甲
}
HID_EL = np.zeros((12, 5))                    # branch -> weighted element vector
for _b, _hs in HIDDEN.items():
    for _s, _w in _hs:
        HID_EL[_b, STEM_EL[_s]] += _w

# ── 納音 — the 30 hidden elements of the 60 pillars, 甲子乙丑海中金 ... 壬戌癸亥大海水 ──────────
NAYIN30 = np.array([3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4,
                    3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4])
NAYIN = NAYIN30[np.arange(60) // 2]           # pillar index -> element

# ── 十二長生 — the branch each stem begins its cycle in; yang stems run forward, yin backward ────
CS_START = np.array([11, 6, 2, 9, 2, 9, 5, 0, 8, 3])   # 甲亥 乙午 丙寅 丁酉 戊寅 己酉 庚巳 辛子 壬申 癸卯

# ── 六破 — the six destructions, explicit because no simple modulus isolates them ────────────────
PO_TAB = np.zeros((12, 12), bool)
for _a, _b in [(0, 9), (1, 4), (2, 11), (3, 6), (5, 8), (7, 10)]:
    PO_TAB[_a, _b] = PO_TAB[_b, _a] = True

# ── 三刑 / 自刑 — punishments ────────────────────────────────────────────────────────────────────
XING_TAB = np.zeros((12, 12), bool)
XING_TRIADS = [(2, 5, 8), (1, 7, 10)]         # 寅巳申 無恩之刑 · 丑戌未 恃勢之刑
for _g in XING_TRIADS:
    for _a in _g:
        for _b in _g:
            if _a != _b:
                XING_TAB[_a, _b] = True
XING_TAB[0, 3] = XING_TAB[3, 0] = True        # 子卯 無禮之刑
SELF_X = np.zeros(12, bool)
SELF_X[[4, 6, 9, 11]] = True                  # 辰午酉亥 自刑

SANHE_TRIADS = [(8, 0, 4), (11, 3, 7), (2, 6, 10), (5, 9, 1)]     # 申子辰 亥卯未 寅午戌 巳酉丑
SANHUI_TRIOS = [(2, 3, 4), (5, 6, 7), (8, 9, 10), (11, 0, 1)]     # 寅卯辰 巳午未 申酉戌 亥子丑
WANG = np.zeros(12, bool)
WANG[[0, 3, 6, 9]] = True                     # 子午卯酉, the 帝旺 branch that makes a 半合

# ── 28 xiu, in order from 角 Jiao (Spica) ────────────────────────────────────────────────────────
XIU = ("角 亢 氐 房 心 尾 箕 斗 牛 女 虛 危 室 壁 奎 婁 胃 昴 畢 觜 參 井 鬼 柳 星 張 翼 軫").split()
XIU_W = np.array([12, 9, 15, 5, 5, 18, 11, 26, 8, 12, 10, 17, 16, 9, 16, 12, 14, 11,
                  16, 2, 9, 33, 4, 15, 7, 18, 18, 17], float)      # classical Chinese degrees
XIU_EDGE = np.concatenate([[0.0], np.cumsum(XIU_W / XIU_W.sum() * 360.0)])
# the 七曜 attached to the xiu repeat with period 7: 木金土日月火水 (角=木, 亢=金, 氐=土, 房=日 ...)
XIU_LUM = np.arange(28) % 7

# ── 九星 -> element and Luo Shu 洛書 seat ────────────────────────────────────────────────────────
# 1白水 2黑土 3碧木 4綠木 5黃土 6白金 7赤金 8白土 9紫火
STAR_EL = np.array([0, 4, 2, 0, 0, 2, 3, 3, 2, 1])   # index by star 1..9 (slot 0 unused)
LOSHU = {4: (0, 0), 9: (0, 1), 2: (0, 2), 3: (1, 0), 5: (1, 1),
         7: (1, 2), 8: (2, 0), 1: (2, 1), 6: (2, 2)}
LO_R = np.array([0] + [LOSHU[s][0] for s in range(1, 10)], float)
LO_C = np.array([0] + [LOSHU[s][1] for s in range(1, 10)], float)
EAST_GROUP = np.array([0, 1, 0, 1, 1, 0, 0, 0, 0, 1], float)       # 東四命 1 3 4 9 (5 is neither)

# ── 八宅 — trigram lines, bottom first; the kua number of each trigram ───────────────────────────
TRI = {1: (0, 1, 0), 2: (0, 0, 0), 3: (1, 0, 0), 4: (0, 1, 1),
       6: (1, 1, 1), 7: (1, 1, 0), 8: (0, 0, 1), 9: (1, 0, 1)}
# which lines changed -> the 遊年 relation, and its classical rank
#   +4 生氣 · +3 天醫 · +2 延年 · +1 伏位 · -1 禍害 · -2 六煞 · -3 五鬼 · -4 絕命
BAZHAI = {(0, 0, 0): (3, 1.), (0, 0, 1): (0, 4.), (1, 1, 0): (1, 3.), (1, 1, 1): (2, 2.),
          (1, 0, 0): (4, -1.), (1, 0, 1): (5, -2.), (0, 1, 1): (6, -3.), (0, 1, 0): (7, -4.)}
BZ_REL = np.zeros((10, 10), np.int64)
BZ_SCORE = np.zeros((10, 10))
for _ka, _ta in TRI.items():
    for _kb, _tb in TRI.items():
        _chg = tuple(int(x != y) for x, y in zip(_ta, _tb))
        BZ_REL[_ka, _kb], BZ_SCORE[_ka, _kb] = BAZHAI[_chg]

# ── 建除十二客 — the day officer, and the fortune the almanac attaches to it ─────────────────────
# 建 除 滿 平 定 執 破 危 成 收 開 閉; the common 通書 summary: 成 大吉, 破 大凶, the rest as below.
JIANCHU_SCORE = np.array([0., 1., -1., -1., 1., -1., -2., -1., 2., -1., 1., -1.])
JIANCHU_WED = np.array([0., 0., 0., 0., 1., 0., 0., 0., 1., 0., 1., 0.])   # 宜嫁娶: 定 成 開

SHENG = np.zeros((5, 5))                      # 生 Wood->Fire->Earth->Metal->Water->Wood
KE = np.zeros((5, 5))                         # 剋 Wood->Earth->Water->Fire->Metal->Wood
for _e in range(5):
    SHENG[_e, (_e + 1) % 5] = 1.
    KE[_e, (_e + 2) % 5] = 1.

OLD, YNG, WED = 0, 1, 2


# ── plumbing ────────────────────────────────────────────────────────────────────────────────────
def _oh(idx, k):
    """One-hot of an integer array, (n, k) float64."""
    return np.eye(k)[np.asarray(idx, np.int64)]


def _cal(jd):
    """Gregorian year, month, day and the integer Julian Day Number (Fliegel & Van Flandern).

    Pure integer arithmetic — no calendar library, no ephemeris, no I/O. JDN 2299161 = 1582-10-15,
    the first Gregorian day, which __main__ asserts.
    """
    jdn = np.floor(np.asarray(jd, np.float64) + 0.5).astype(np.int64)
    l = jdn + 68569
    nn = (4 * l) // 146097
    l = l - (146097 * nn + 3) // 4
    i = (4000 * (l + 1)) // 1461001
    l = l - (1461 * i) // 4 + 31
    j = (80 * l) // 2447
    day = l - (2447 * j) // 80
    l2 = j // 11
    return 100 * (nn - 49) + i + l2, j + 2 - 12 * l2, day, jdn


def _pillars(E, slot):
    """The three computable pillars plus the solar-term position for one instant slot.

    No hour pillar: see the module docstring. `sy` is the LICHUN year, not the calendar year.
    """
    y, m, _, jdn = _cal(E.JD[slot])
    lam = E.LON[slot, E.IDX["Sun"]]                       # tropical solar longitude
    # before Lichun (Sun < 315 deg) in January or February, the BaZi year is still the previous one
    sy = y - ((m <= 2) & (lam < 315.0)).astype(np.int64)
    off = np.mod(lam - 315.0, 360.0)                      # degrees of Sun travel since Lichun
    jq = np.floor(off / 15.0).astype(np.int64)            # 0 = 立春 ... 23 = 大寒
    mnum = np.floor(off / 30.0).astype(np.int64)          # 0 = 寅 month
    yidx = np.mod(sy - 4, 60)                             # 1984 = 甲子
    ys, yb = yidx % 10, yidx % 12
    mb = (2 + mnum) % 12
    ms = (2 * ys + 2 + mnum) % 10                         # 五虎遁
    didx = np.mod(jdn - 11, 60)                           # JDN 11 = 甲子
    return dict(sy=sy, lam=lam, off=off, jq=jq, jqph=off / 15.0 - jq, mnum=mnum,
                yidx=yidx, ys=ys, yb=yb, ms=ms, mb=mb,
                midx=(6 * ms - 5 * mb) % 60, didx=didx, ds=didx % 10, db=didx % 12)


def _bre(a, b):
    """Every classical relation between two earthly-branch arrays, as float flags."""
    tri_a, tri_b = ((a - 2) % 12) // 3, ((b - 2) % 12) // 3
    same = (a == b)
    sanhe = ((a % 4) == (b % 4)) & ~same
    r = dict(
        same=same.astype(float),
        sanhe=sanhe.astype(float),                                     # 三合
        banhe=(sanhe & (WANG[a] | WANG[b])).astype(float),             # 半合
        sanhui=((tri_a == tri_b) & ~same).astype(float),               # 三會方局
        liuhe=(((a + b) % 12) == 1).astype(float),                     # 六合
        chong=(np.abs(((a - b + 6) % 12) - 6) == 6).astype(float),     # 六沖
        hai=(((a + b) % 12) == 7).astype(float),                       # 六害
        po=PO_TAB[a, b].astype(float),                                 # 六破
        xing=(XING_TAB[a, b] | (same & SELF_X[a])).astype(float),      # 三刑 + 自刑
        selfxing=(same & SELF_X[a]).astype(float),
    )
    return r


def _bre_block(a, b, tag):
    """The relation flags plus the tradition's own tally, for one pair of branch columns."""
    r = _bre(a, b)
    keys = ["same", "sanhe", "banhe", "sanhui", "liuhe", "chong", "hai", "po", "xing", "selfxing"]
    cols = [r[k] for k in keys]
    names = [f"{tag}:{k}" for k in keys]
    # a tally in the shape the almanacs use: 合 credit, 沖刑害破 debit. Weights vary between texts,
    # so the flags above are emitted too and the model may reweight them freely.
    cols += [3 * r["sanhe"] + 3 * r["liuhe"] + 2 * r["sanhui"] + 1.5 * r["banhe"]
             - 3 * r["chong"] - 2 * r["xing"] - 2 * r["hai"] - r["po"],
             r["sanhe"] + r["liuhe"] + r["sanhui"] + r["banhe"],
             r["chong"] + r["xing"] + r["hai"] + r["po"]]
    names += [f"{tag}:tally", f"{tag}:he_count", f"{tag}:clash_count"]
    return cols, names


def _stems(a, b):
    """天干五合 (|a-b| == 5) and 天干相沖 (|a-b| == 6), the two named stem relations."""
    d = np.abs(a - b)
    return (d == 5).astype(float), (d == 6).astype(float)


def _life_stage(stem, branch):
    """十二長生 — the stage (0 長生 ... 11 養) of a stem in a branch; yin stems run backward."""
    st = CS_START[stem]
    fwd = (branch - st) % 12
    bwd = (st - branch) % 12
    return np.where(STEM_YANG[stem] > 0, fwd, bwd).astype(np.int64)


def _el_counts(P, hidden):
    """Wu Xing counts over the SIX characters of the three computable pillars (no hour pillar).

    `hidden=False` counts the visible characters (3 stems + 3 branches, the branch counted by its
    own element). `hidden=True` replaces each branch by its 藏干 weighted element vector.
    """
    n = P["ys"].shape[0]
    C = np.zeros((n, 5))
    for s in ("ys", "ms", "ds"):
        C += _oh(STEM_EL[P[s]], 5)
    for b in ("yb", "mb", "db"):
        C += HID_EL[P[b]] if hidden else _oh(BRANCH_EL[P[b]], 5)
    return C


def _rel5(ea, eb):
    """五行生剋 as one of five relations: 0 同 · 1 a生b · 2 a剋b · 3 b剋a · 4 b生a."""
    d = (eb - ea) % 5
    return np.where(d == 0, 0, np.where(d == 1, 1, np.where(d == 2, 2, np.where(d == 3, 3, 4))))


def _xiu(E, slot, unequal):
    """The Moon's xiu. Anchored on Spica at exactly 180 deg via the True Citra ayanamsa.

    The Moon's noon longitude carries ~6 deg of error against the real birth moment and a xiu is
    12.86 deg wide, so this label is about half reliable. Divisions along the ecliptic; the true
    xiu are equatorial.
    """
    lon = np.mod(E.sidereal("True Citra")[slot, E.IDX["Moon"]] - 180.0, 360.0)
    if unequal:
        i = np.clip(np.searchsorted(XIU_EDGE, lon, side="right") - 1, 0, 27)
        w = XIU_EDGE[i + 1] - XIU_EDGE[i]
        return i.astype(np.int64), (lon - XIU_EDGE[i]) / w
    q = lon / (360.0 / 28.0)
    i = np.clip(np.floor(q).astype(np.int64), 0, 27)
    return i, q - i


def _stack(cols):
    """hstack a mix of (n,) and (n, k) columns."""
    n = np.asarray(cols[0]).shape[0]
    X = np.hstack([np.asarray(c, np.float64).reshape(n, -1) for c in cols])
    return np.ascontiguousarray(X, np.float64)


# ── the blocks ──────────────────────────────────────────────────────────────────────────────────
def build(E):
    O, Yg, W = _pillars(E, OLD), _pillars(E, YNG), _pillars(E, WED)
    out = {}

    # 1 ── the raw pillars, one-hot. Pure interaction material: trees and kernels can read a
    #      stem-branch identity that no linear model can. Three pillars x (10 stems + 12 branches)
    #      for both partners and for the wedding day. No hour pillar — see the module docstring.
    cols = []
    for P in (O, Yg, W):
        for s, b in (("ys", "yb"), ("ms", "mb"), ("ds", "db")):
            cols += [_oh(P[s], 10), _oh(P[b], 12)]
    out["chi: pillars one-hot (year/month/day, no hour)"] = np.hstack(cols)

    # 2 ── the same cycles, circular. cos/sin of each pillar's position in the 60, the 10 and the
    #      12, plus the SIGNED OFFSETS between the partners' pillars — the 60-cycle distance
    #      between two day pillars is what 天合地合 and 天克地沖 are extremes of.
    cols = []
    for P in (O, Yg, W):
        for k, m in (("yidx", 60), ("midx", 60), ("didx", 60), ("ys", 10), ("yb", 12),
                     ("ms", 10), ("mb", 12), ("ds", 10), ("db", 12)):
            cols.append(E.circ(P[k] * 360.0 / m).reshape(E.n, 2))
    for k, m in (("yidx", 60), ("midx", 60), ("didx", 60), ("ys", 10), ("yb", 12), ("db", 12)):
        d = (O[k].astype(float) - Yg[k]) % m
        cols += [E.circ(d * 360.0 / m).reshape(E.n, 2), (np.minimum(d, m - d) / m)[:, None]]
    cols.append(((O["sy"] - Yg["sy"]) % 60 / 60.0)[:, None])          # sexagenary age gap
    out["chi: sexagenary cycles circular + partner offsets"] = np.hstack(cols)

    # 3 ── Wu Xing counts over the visible characters. Six characters, not eight: the hour pillar
    #      is unavailable, so these counts are systematically two characters light for everybody.
    #      Emitted as counts, proportions, and the pair's agreement/complement.
    A, B, Aw = _el_counts(O, False), _el_counts(Yg, False), _el_counts(W, False)

    def _elfeat(A, B, Wc):
        pa, pb = A / A.sum(1, keepdims=True), B / B.sum(1, keepdims=True)
        cols = [A, B, pa, pb, Wc, A + B, A - B, np.abs(A - B), np.minimum(A, B),
                (A == 0).sum(1, keepdims=True).astype(float),        # 缺 how many elements missing
                (B == 0).sum(1, keepdims=True).astype(float),
                A.max(1, keepdims=True), B.max(1, keepdims=True),
                _oh(A.argmax(1), 5), _oh(B.argmax(1), 5),
                (np.abs(pa - pb).sum(1))[:, None],
                (pa * pb).sum(1)[:, None] / (np.linalg.norm(pa, axis=1) *
                                             np.linalg.norm(pb, axis=1))[:, None]]
        return cols
    out["chi: wu xing counts, visible characters"] = _stack(_elfeat(A, B, Aw))

    # 4 ── the same doctrine over the HIDDEN stems (藏干) — the count a practitioner actually uses,
    #      weighting each branch's main/middle/residual qi 0.6/0.3/0.1.
    Ah, Bh, Wh = _el_counts(O, True), _el_counts(Yg, True), _el_counts(W, True)
    out["chi: wu xing counts, hidden stems weighted"] = _stack(_elfeat(Ah, Bh, Wh))

    # 5 ── the relations between the partners: 五行生剋 on each pillar, the bilinear generating and
    #      overcoming scores over the whole element vectors, 納音, and 十二長生 (each partner's day
    #      stem read in the other's day branch — the day pillar is the self in BaZi).
    cols, names = [], []
    for k, el in (("ds", STEM_EL), ("ys", STEM_EL), ("ms", STEM_EL),
                  ("db", BRANCH_EL), ("yb", BRANCH_EL), ("mb", BRANCH_EL)):
        cols.append(_oh(_rel5(el[O[k]], el[Yg[k]]), 5))
    for X1, X2 in ((A, B), (Ah, Bh)):
        cols += [(X1 @ SHENG * X2).sum(1)[:, None], (X2 @ SHENG * X1).sum(1)[:, None],
                 (X1 @ KE * X2).sum(1)[:, None], (X2 @ KE * X1).sum(1)[:, None],
                 (X1 * X2).sum(1)[:, None]]
    ny_o_y, ny_y_y = NAYIN[O["yidx"]], NAYIN[Yg["yidx"]]
    ny_o_d, ny_y_d = NAYIN[O["didx"]], NAYIN[Yg["didx"]]
    cols += [_oh(ny_o_y, 5), _oh(ny_y_y, 5), _oh(ny_o_d, 5), _oh(ny_y_d, 5),
             _oh(_rel5(ny_o_y, ny_y_y), 5), _oh(_rel5(ny_o_d, ny_y_d), 5)]
    cols += [_oh(_life_stage(O["ds"], Yg["db"]), 12), _oh(_life_stage(Yg["ds"], O["db"]), 12),
             _oh(_life_stage(O["ds"], O["db"]), 12), _oh(_life_stage(Yg["ds"], Yg["db"]), 12)]
    cols += [STEM_YANG[O["ds"]][:, None], STEM_YANG[Yg["ds"]][:, None],
             (STEM_YANG[O["ds"]] == STEM_YANG[Yg["ds"]]).astype(float)[:, None]]
    out["chi: partner element relations (sheng/ke, nayin, life stages)"] = np.hstack(cols)

    # 6 ── the year branches: the zodiac animal pairing everyone means by "Chinese compatibility".
    #      Flags, the tally, and the full ordered 12x12 animal pair (older x younger) — 144 sparse
    #      columns is exactly the interaction a tree can exploit and a linear model cannot.
    c, nm = _bre_block(O["yb"], Yg["yb"], "yb")
    he, ch = _stems(O["ys"], Yg["ys"])
    r = _bre(O["yb"], Yg["yb"])
    out["chi: year branch relations (zodiac animals)"] = np.hstack(
        [_stack(c), he[:, None], ch[:, None],
         (he * r["liuhe"])[:, None], (ch * r["chong"])[:, None],       # 天合地合 / 天克地沖
         _oh(O["yb"] * 12 + Yg["yb"], 144),
         _oh(O["yb"] % 4, 4), _oh(Yg["yb"] % 4, 4),
         _oh(((O["yb"] - 2) % 12) // 3, 4), _oh(((Yg["yb"] - 2) % 12) // 3, 4)])

    # 7 ── the DAY branches. In BaZi the day pillar is the self and the day branch is the spouse
    #      palace (夫妻宮), so this is the relation the tradition weights above the year animal.
    c, nm = _bre_block(O["db"], Yg["db"], "db")
    he, ch = _stems(O["ds"], Yg["ds"])
    r = _bre(O["db"], Yg["db"])
    out["chi: day branch relations (day pillar is the self)"] = np.hstack(
        [_stack(c), he[:, None], ch[:, None],
         (he * r["liuhe"])[:, None], (ch * r["chong"])[:, None],
         _oh(O["db"] * 12 + Yg["db"], 144),
         _oh(_rel5(STEM_EL[O["ds"]], STEM_EL[Yg["ds"]]), 5)])

    # 8 ── every pillar against every pillar: 3 x 3 branch pairs, all ten relations each, plus the
    #      column totals and whether the six branches between them COMPLETE a triad
    #      (三合局成 / 三會方局成 / 三刑全) — a rule that needs both charts at once.
    cols = []
    tot = {}
    for ka in ("yb", "mb", "db"):
        for kb in ("yb", "mb", "db"):
            r = _bre(O[ka], Yg[kb])
            for k, v in r.items():
                cols.append(v[:, None])
                tot[k] = tot.get(k, 0.) + v
    cols += [v[:, None] for v in tot.values()]
    allb = [O["yb"], O["mb"], O["db"], Yg["yb"], Yg["mb"], Yg["db"]]
    has = np.stack([np.any(np.stack([b == j for b in allb]), 0) for j in range(12)], 1)
    for g in SANHE_TRIADS + SANHUI_TRIOS + XING_TRIADS:
        cols.append(np.all(has[:, list(g)], 1).astype(float)[:, None])
    cols.append(has.sum(1, keepdims=True).astype(float))               # how many distinct branches
    out["chi: branch relations across all nine pillar pairs"] = np.hstack(cols)

    # 9 ── the tradition's own single numbers, alone in a narrow block. Three weightings of the
    #      same relation set, because no two almanacs weight it identically, plus the two named
    #      extremes and the day/year split.
    def _score(a, b, wsan, wliu, wch, wxi, wha, wpo):
        r = _bre(a, b)
        return (wsan * r["sanhe"] + wliu * r["liuhe"] + .5 * wsan * r["sanhui"]
                + wch * r["chong"] + wxi * r["xing"] + wha * r["hai"] + wpo * r["po"])
    ry, rd = _bre(O["yb"], Yg["yb"]), _bre(O["db"], Yg["db"])
    hey, chy = _stems(O["ys"], Yg["ys"])
    hed, chd = _stems(O["ds"], Yg["ds"])
    cols = [_score(O["yb"], Yg["yb"], 3, 3, -3, -2, -2, -1),
            _score(O["db"], Yg["db"], 3, 3, -3, -2, -2, -1),
            _score(O["yb"], Yg["yb"], 6, 6, -6, -4, -3, -2),
            _score(O["db"], Yg["db"], 6, 6, -6, -4, -3, -2),
            _score(O["yb"], Yg["yb"], 1, 1, -1, -1, -1, -1),
            _score(O["db"], Yg["db"], 1, 1, -1, -1, -1, -1)]
    cols += [ry["sanhe"] + ry["liuhe"] - ry["chong"], rd["sanhe"] + rd["liuhe"] - rd["chong"],
             hey * ry["liuhe"] + hed * rd["liuhe"],                    # 天合地合, year and day
             -(chy * ry["chong"] + chd * rd["chong"]),                 # 天克地沖
             np.abs(_rel5(STEM_EL[O["ds"]], STEM_EL[Yg["ds"]]) - 2).astype(float)]
    s = cols[0] + cols[1]
    cols += [s, np.sign(s), (s >= 3).astype(float), (s <= -3).astype(float)]
    out["chi: traditional he/chong compatibility tallies"] = _stack(cols)

    # 10 ── the 24 solar terms, from the Sun's own longitude at 15 deg steps, 0 = 立春. Plus the
    #       almanac's day officer 建除十二客 for the wedding, and the 擇日 rule that the wedding day
    #       must not clash with either partner's animal.
    cols = []
    for P in (O, Yg, W):
        cols += [_oh(P["jq"], 24), P["jqph"][:, None], (P["off"] / 360.0)[:, None],
                 E.circ(P["off"]).reshape(E.n, 2), (P["jq"] % 2).astype(float)[:, None],
                 _oh(P["mnum"], 12)]
    dj = (O["jq"].astype(float) - Yg["jq"]) % 24
    cols += [E.circ(dj * 15.0).reshape(E.n, 2), (np.minimum(dj, 24 - dj) / 12.0)[:, None],
             (O["jq"] == Yg["jq"]).astype(float)[:, None],
             (O["mnum"] == Yg["mnum"]).astype(float)[:, None]]
    for P, tag in ((O, "o"), (Yg, "y"), (W, "w")):
        off = (P["db"] - P["mb"]) % 12
        cols += [_oh(off, 12), JIANCHU_SCORE[off][:, None], JIANCHU_WED[off][:, None]]
    for P in (O, Yg):
        for k in ("yb", "db"):
            r = _bre(W["db"], P[k])
            cols += [r["chong"][:, None], r["liuhe"][:, None], r["sanhe"][:, None],
                     r["hai"][:, None], r["xing"][:, None]]
    out["chi: 24 jieqi solar terms + jianchu day officer"] = np.hstack(cols)

    # 11 ── the 28 xiu, equal 28ths from Spica. Moon-based, so ~half reliable (see docstring).
    def _xblock(unequal):
        xa, pa = _xiu(E, OLD, unequal)
        xb, pb = _xiu(E, YNG, unequal)
        xw, pw = _xiu(E, WED, unequal)
        d = (xb.astype(np.int64) - xa) % 28
        # 宿曜 三九の秘法: the nine-relation cycle repeats three times round the mansions
        rel_f = np.where(d == 0, 0, (d - 1) % 9 + 1)
        rel_b = np.where(d == 0, 0, ((28 - d) - 1) % 9 + 1)
        cols = [_oh(xa, 28), _oh(xb, 28), _oh(xw, 28),
                pa[:, None], pb[:, None], pw[:, None],
                _oh(xa // 7, 4), _oh(xb // 7, 4), _oh(xw // 7, 4),          # 四象 palaces
                _oh(XIU_LUM[xa], 7), _oh(XIU_LUM[xb], 7), _oh(XIU_LUM[xw], 7),   # 七曜
                _oh(d, 28), _oh(rel_f, 10), _oh(rel_b, 10),
                E.circ(d * 360.0 / 28.0).reshape(E.n, 2),
                (np.minimum(d, 28 - d) / 14.0)[:, None],
                (xa == xb).astype(float)[:, None],
                (xa // 7 == xb // 7).astype(float)[:, None],
                (XIU_LUM[xa] == XIU_LUM[xb]).astype(float)[:, None],
                E.circ((xa + pa) * 360.0 / 28.0).reshape(E.n, 2),
                E.circ((xb + pb) * 360.0 / 28.0).reshape(E.n, 2)]
        return np.hstack(cols)
    out["chi: 28 xiu, equal divisions from Spica"] = _xblock(False)

    # 12 ── the same 28 xiu on the CLASSICAL unequal widths (角12 ... 軫17). A different doctrine
    #       of the same object: 觜 is 2 degrees wide and 井 is 33, so many rows change mansion.
    out["chi: 28 xiu, classical unequal widths"] = _xblock(True)

    # 13 ── the nine stars 九星, on the continuous 年紫白 count from the LICHUN year, with the
    #       monthly star 月紫白 (寅月 starts at 8 for 子午卯酉 years, 5 for 辰戌丑未, 2 for 寅申巳亥,
    #       then counting down). Includes the Luo Shu seat, since the 3x3 geometry is the doctrine.
    def _star(P):
        m = ((1 - P["sy"]) % 9) + 1
        st = np.array([8, 5, 2])[P["yb"] % 3]
        mo = ((st - P["mnum"] - 1) % 9) + 1
        return m.astype(np.int64), mo.astype(np.int64)
    sa, ma = _star(O)
    sb, mb_ = _star(Yg)
    sw, mw = _star(W)
    ds = (sa - sb) % 9
    cols = [_oh(sa - 1, 9), _oh(sb - 1, 9), _oh(sw - 1, 9),
            _oh(ma - 1, 9), _oh(mb_ - 1, 9), _oh(mw - 1, 9),
            _oh((sa - 1) * 9 + (sb - 1), 81),
            _oh(STAR_EL[sa], 5), _oh(STAR_EL[sb], 5), _oh(_rel5(STAR_EL[sa], STAR_EL[sb]), 5),
            _oh(_rel5(STAR_EL[ma], STAR_EL[mb_]), 5),
            _oh(ds, 9), E.circ(ds * 40.0).reshape(E.n, 2),
            (np.minimum(ds, 9 - ds) / 4.5)[:, None],
            (sa == sb).astype(float)[:, None],
            LO_R[sa][:, None], LO_C[sa][:, None], LO_R[sb][:, None], LO_C[sb][:, None],
            np.abs(LO_R[sa] - LO_R[sb])[:, None], np.abs(LO_C[sa] - LO_C[sb])[:, None],
            np.hypot(LO_R[sa] - LO_R[sb], LO_C[sa] - LO_C[sb])[:, None],
            (LO_R[sa] == LO_R[sb]).astype(float)[:, None],
            (LO_C[sa] == LO_C[sb]).astype(float)[:, None],
            EAST_GROUP[sa][:, None], EAST_GROUP[sb][:, None],
            (EAST_GROUP[sa] == EAST_GROUP[sb]).astype(float)[:, None],
            ((sa == 5) | (sb == 5)).astype(float)[:, None]]
    out["chi: nine star ki (nian/yue zibai)"] = np.hstack(cols)

    # 14 ── 八宅 Eight Mansions. The Ming Gua differs by SEX and the sex of each partner is unknown,
    #       so both are computed for both: male gua = (2 - year) mod 9, female = (year - 5) mod 9
    #       (0 -> 9), 5 -> 坤 2 for a male and 艮 8 for a female, as the tradition prescribes. The
    #       遊年 relation is then emitted for all four sex assignments — a documented hedge, not a
    #       guess. The relation itself is derived from trigram line changes (see module docstring).
    def _gua(P):
        m = ((2 - P["sy"]) % 9)
        f = ((P["sy"] - 5) % 9)
        m = np.where(m == 0, 9, m); f = np.where(f == 0, 9, f)
        m = np.where(m == 5, 2, m); f = np.where(f == 5, 8, f)
        return m.astype(np.int64), f.astype(np.int64)
    om, of = _gua(O)
    ym, yf = _gua(Yg)
    cols = [_oh(om, 10), _oh(of, 10), _oh(ym, 10), _oh(yf, 10)]
    for a, b in ((om, yf), (of, ym), (om, ym), (of, yf)):
        rel, sc = BZ_REL[a, b], BZ_SCORE[a, b]
        cols += [_oh(rel, 8), sc[:, None], (sc > 0).astype(float)[:, None],
                 (np.abs(sc) == 4).astype(float)[:, None],
                 (EAST_GROUP[a] == EAST_GROUP[b]).astype(float)[:, None]]
    cols.append((BZ_SCORE[om, yf] + BZ_SCORE[of, ym])[:, None])
    out["chi: eight mansions (bazhai) kua relation"] = np.hstack(cols)

    return {k: np.ascontiguousarray(v, np.float64) for k, v in out.items()}


# ── self-test ───────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick

    # the calendar and the sexagenary epoch, asserted against published anchors
    y, m, d, jdn = _cal(np.array([2299161.0, 2433191.0, 2415021.0]))
    assert (y[0], m[0], d[0]) == (1582, 10, 15), "Gregorian conversion is wrong"
    assert np.mod(jdn[1] - 11, 60) == 0, "1 Oct 1949 must be a jiazi day"
    assert np.mod(jdn[2] - 11, 60) == 10, "1 Jan 1900 must be a jiaxu day"
    assert (1984 - 4) % 60 == 0, "1984 must be the jiazi year"
    assert NAYIN[(1986 - 4) % 60] == 1 and NAYIN[(1990 - 4) % 60] == 2, "nayin table is wrong"
    assert BZ_REL[1, 4] == 0 and BZ_REL[1, 2] == 7, "bazhai: Kan's shengqi is Xun, jueming Kun"
    assert BZ_REL[6, 7] == 0 and BZ_REL[6, 9] == 7, "bazhai: Qian's shengqi is Dui, jueming Li"
    assert ((1 - 2017) % 9) + 1 == 1 and ((1 - 2024) % 9) + 1 == 3, "nine star count is wrong"
    print(f"TRADITION  {TRADITION}")
    print("epoch      day pillar (JDN - 11) mod 60, JDN 11 = jiazi; 1949-10-01 = jiazi,")
    print("           1900-01-01 = jiaxu.  Year pillar (lichun year - 4) mod 60, 1984 = jiazi.")
    print("no hour pillar: birth times are unknown; every wu xing count is over 6 characters.\n")

    E = load()
    X = build(E)
    fails = 0
    print(f"{'block':<52}{'cols':>6}{'acc':>9}{'auc':>9}")
    for name, A in X.items():
        try:
            assert isinstance(A, np.ndarray), f"{name}: not an ndarray"
            assert A.dtype == np.float64, f"{name}: dtype {A.dtype}"
            assert A.ndim == 2 and A.shape[0] == E.n, f"{name}: shape {A.shape} != ({E.n}, k)"
            assert np.isfinite(A).all(), f"{name}: non-finite values"
            assert A.std(axis=0).max() > 0, f"{name}: every column is constant"
            assert name.startswith("chi: "), f"{name}: missing tradition tag"
        except AssertionError as e:
            print(f"FAIL  {e}")
            fails += 1
            continue
        acc, auc = quick(E, A)
        print(f"{name:<52}{A.shape[1]:>6}{100*acc:>8.2f}%{auc:>9.4f}")
    tot = sum(v.shape[1] for v in X.values())
    print(f"\n{len(X)} blocks, {tot} columns total")
    if fails:
        sys.exit(1)
    print("OK")
