"""
trad_east_asian_deep.py — the East Asian systems the BaZi module does not reach: Vietnamese TỬ VI
(紫微斗數 Purple Star), Korean SAJU / 명리학 with the ten gods (십성), Japanese SHUKUYŌ (宿曜),
ROKUYŌ (六曜), ONMYŌDŌ (陰陽道) direction taboos and SANMEIGAKU (算命学), Mongolian ZURKHAI
(зурхай), and the three Chinese almanac objects `trad_chinese.py` leaves out.

WHY THIS IS NOT trad_chinese.py AGAIN

`trad_chinese.py` is built entirely on the SOLAR year: it takes the sexagenary year from 立春
(Lichun, Sun at 315°) and never computes a lunisolar calendar at all ("no lunisolar calendar table
is needed"). Everything below needs the LUNAR MONTH and the LUNAR DAY — Tử Vi places its stars from
them, the Japanese almanac derives the mansion and the rokuyō from them, and the Mongolian year
turns on the lunar new moon rather than on Lichun. So the first thing this module does is compute
the Chinese-style lunisolar calendar, which is new here, and everything else stands on it.

THE LUNISOLAR CALENDAR, AND ITS ONE APPROXIMATION
  · 初一 is the local civil day CONTAINING the true new moon. The new moon instant is found from
    Meeus, *Astronomical Algorithms* 2nd ed., ch. 49 (the truncated new-moon series), converted
    from TT to UT with `swe.deltat`, then Newton-refined against the real Swiss Ephemeris until the
    Sun–Moon elongation is under 1e-6°, so the series is only a starting point and the answer is
    the ephemeris's.
  · MONTH NUMBER by the 無中氣置閏 rule: the month is numbered by the 中氣 (major solar term, a
    multiple of 30° of solar longitude) that falls inside it, 冬至 → month 11, 大寒 → 12, 雨水 → 1;
    a month containing no 中氣 is a leap month and keeps the number of the month before it.
    APPROXIMATION, stated plainly: the official rule also requires that only ONE leap month falls
    between two winter solstices, which needs the whole 歲 (solstice-to-solstice) span in view. The
    no-中氣 test alone can therefore disagree with the published calendar by one month number in the
    rare years with a 13-month 歲 and two 中氣-less months. A `leap` flag is emitted so a model can
    isolate exactly those rows.
  · TIME ZONE IS PART OF THE DOCTRINE. The Vietnamese calendar is computed at UTC+7 (UTC+8 before
    1968) — Hồ Ngọc Đức's published Vietnamese calendar algorithm — the Chinese at UTC+8 (Beijing),
    the modern Korean and Japanese at UTC+9. A new moon between 15:00 and 17:00 UT lands on a
    different local day in two of those zones, and then the whole month is offset by one day. All
    three are emitted with their disagreement flags: this is the real mechanism by which Tết and
    春節 occasionally fall on different days.
  · The birth DATE is taken as the civil date the record states, and the East Asian calendar is
    applied to it. For a person born outside East Asia that is the only defensible reading; it is
    not a claim that they used the calendar.

TỬ VI / 紫微斗數 — a whole system, not a flavour of BaZi
  Twelve palaces around a fixed ring of the twelve branches; the LIFE PALACE (命宮 cung Mệnh) is
  found from the lunar month and the birth hour, the twelve palaces then run BACKWARD from it
  (命·兄弟·夫妻·子女·財帛·疾厄·遷移·奴僕·官祿·田宅·福德·父母); the 五行局 (ngũ hành cục) comes
  from the 納音 element of the life palace's own stem-branch; and 紫微 is placed from the LUNAR DAY
  and that 局 by the classical 安紫微訣 — quotient and borrow: borrow = 局 − (day mod 局), quotient =
  (day + borrow)/局, start at 寅 and count `quotient` palaces, then move FORWARD `borrow` palaces if
  the borrow is even and BACKWARD if it is odd. That algorithm reproduces the published 紫微 tables
  exactly and __main__ asserts eleven of their cells.
  The other thirteen major stars follow the two classical verses:
    紫微系 「紫微天機逆行旁，隔一陽武天同當，又隔二位遇廉貞，空三復見紫微郎」
            → 天機 z−1, 太陽 z−3, 武曲 z−4, 天同 z−5, 廉貞 z−8
    天府系 「天府順行有太陰，貪狼而後巨門臨，隨來天相天梁繼，七殺空三是破軍」
            → 天府 = mirror of 紫微 in the 寅–申 axis (4 − z), 太陰 f+1, 貪狼 f+2, 巨門 f+3,
              天相 f+4, 天梁 f+5, 七殺 f+6, 破軍 f+10
  __main__ asserts the entire published 紫府在寅 chart (子破軍 丑天機 寅紫微天府 卯太陰 辰貪狼
  巳巨門 午廉貞天相 未天梁 申七殺 酉天同 戌武曲 亥太陽), all twelve palaces at once.

  THE BIRTH HOUR IS MARGINALISED, NOT GUESSED, and one consequence has to be said out loud. The
  life palace is (寅 + month − 1 − hour branch), so under a uniform prior over the twelve
  double-hours the life palace — and therefore every palace, including 夫妻 — is EXACTLY uniform
  over the twelve branches. Any feature of the form "which branch is the spouse palace" is a
  constant and is not emitted. What is NOT uniform, and is emitted, is everything measured
  RELATIVE to the palace ring: the 五行局 (it depends on the life palace's stem, hence on the year
  stem), the offset 紫微 − 命宮, and above all WHICH STARS FALL IN WHICH PALACE — because 紫微's seat
  moves with the 局 and the lunar day while the palace ring moves with the hour, so the two do not
  cancel. That is the honest information the marginalisation leaves, and it is exactly the case the
  brief describes as worth building.
  Also invariant, and worth stating: because the prior over the twelve hours is uniform, converting
  the hour from UT to the birthplace's local time is a relabelling of a uniform distribution and
  cannot change a single marginal. The missing longitude costs nothing HERE (it does cost elsewhere,
  see the Korean block).

KOREAN SAJU / 사주명리학
  The four pillars themselves are `trad_chinese.py`'s (and the hour pillar is uncomputable there and
  here), so no pillar is re-emitted. What is emitted is the Korean reading of them:
  · 십성 SIPSEONG, the ten gods, each one a closed form in the relation between a stem and the DAY
    STEM (일간): same element → 비견/겁재, day stem generates → 식신/상관, day stem overcomes →
    편재/정재, it overcomes the day stem → 편관/정관, it generates the day stem → 편인/정인, the
    first of each pair when the yin/yang polarity MATCHES. In one line:
    god = 2·((element(other) − element(day)) mod 5) + [polarity differs]. Emitted as a distribution
    over the visible characters and over the 藏干 (hidden stems) with the 本氣/中氣/餘氣 weights.
  · 격국 GYEOKGUK, the structure: the sipseong of the 월지 본기 (the month branch's principal hidden
    stem) against the day stem, with the 건록격/양인격 special cases flagged.
  · 신강/신약, body-strong or body-weak: the signed sum of supporting (비견 겁재 인성) against
    draining (식상 재성 관성) characters, with 득령 (support from the month branch) doubled, which is
    how the weighting is described in the 명리 textbooks.
  · 궁합 GUNGHAP between the two charts: 원진 (the Korean resentment pair 子未 丑午 寅酉 卯申 辰亥
    巳戌 — note it is NOT the Chinese 六害, which pairs 寅巳 not 寅酉), 귀문관살, 도화살, 괴강,
    백호대살, and the two people's day stems read as ten gods of each other, in both directions.
  · 용신 (the chosen element) is NOT computed. It is a practitioner's judgement between the 억부,
    조후 and 병약 methods, not a rule, and inventing one would be inventing a tradition.
  · 삼재 needs the year a person is being read IN, which is not an input, so it is omitted.

JAPANESE
  · SHUKUYŌ 宿曜, from the 宿曜経 (Xiuyao jing, translated by Amoghavajra 不空 in 759, carried to
    Japan by Kūkai in 806). TWENTY-SEVEN mansions — 牛 is dropped, which is what makes the pairing
    doctrine work at all, since 27 = 3 × 9. Two independent determinations, both emitted:
      the ALMANAC rule (宿曜暦), mansion = start[lunar month] + lunar day − 1 (mod 27), the
      month-start table 正月室 二月奎 三月胃 四月畢 五月参 六月鬼 七月張 八月角 九月氐 十月心
      十一月斗 十二月虚, whose twelve increments sum to exactly 27 — a self-consistency check
      __main__ asserts; and
      the ASTRONOMICAL one, the Moon's sidereal position, where Shukuyō mansion = nakshatra − 2
      because 昴 is Krittika. The two agree only sometimes and the agreement flag is a feature.
    THE PAIRING DOCTRINE (三九の秘法): counting forward from one's own 命宿, the other person's
    mansion is 命 → 栄 → 衰 → 安 → 危 → 成 → 壊 → 友 → 親, the nine repeating three times, plus the
    near/middle/far rank from which of the three nines it lands in. It is ASYMMETRIC — A may be B's
    栄 while B is A's 親 — and both directions are emitted, which is the whole point of the doctrine.
    (`trad_chinese.py` applies a nine-cycle to the 28 xiu; on 28 mansions the 3 × 9 structure does
    not close, and it reads the mansion off the Moon only. This is the 27-mansion form with the
    calendrical mansion, the rank and the valence.)
    業胎, the special karmic pair, is NOT emitted: the sources I can check do not agree on its
    distance and I will not guess one.
  · ROKUYŌ 六曜, still printed on Japanese calendars and still consulted for wedding dates:
    index = (lunar month + lunar day) mod 6 with 0 = 大安, 1 = 赤口, 2 = 先勝, 3 = 友引, 4 = 先負,
    5 = 仏滅. Verified against the fixed points 正月一日 = 先勝 … 六月一日 = 赤口.
  · SANRINBŌ 三隣亡: 亥 days in lunar months 1·4·7·10, 寅 in 2·5·8·11, 午 in 3·6·9·12.
  · ONMYŌDŌ direction taboos. 天一神 (Ten'ichijin) wanders the eight directions on the sexagenary
    DAY cycle: sixteen days in the heavens from 癸巳 to 戊申, then 5 days in each corner and 6 in
    each cardinal — 己酉 NE·5, 甲寅 E·6, 庚申 SE·5, 乙丑 S·6, 辛未 SW·5, 丙子 W·6, 壬午 NW·5,
    丁亥 N·6, and 16 + 44 = 60 closes the cycle exactly on 癸巳 again. Every one of those nine
    named day-pillars is asserted in __main__ from the arithmetic alone. 八将神: 大将軍 three years
    to a quarter (亥子丑 W, 寅卯辰 N, 巳午未 E, 申酉戌 S), 太歳 in the year's own branch, 歳破
    opposite it. 鬼門 the demon gate 丑寅 (NE) and 裏鬼門 未申 (SW).
    金神七殺 is NOT emitted: I could not verify its year-stem table against a source.
  · SANMEIGAKU 算命学 (Takao Yoshimasa, 20th c.). Its 十大主星 are a bijection of the ten gods
    (貫索=比肩 石門=劫財 鳳閣=食神 調舒=傷官 禄存=偏財 司禄=正財 車騎=偏官 牽牛=正官 龍高=偏印
    玉堂=印綬), so the LABELS carry nothing new — what is new is the 人体星図, which places them at
    five body positions from five different pillar characters (頭 month branch, 左手 year stem,
    胸 day branch, 右手 month stem — the SPOUSE position — 腹 year branch), and the 十二大従星 with
    their published energy numbers (天報3 天輔6 天貴9 天恍7 天南8 天禄11 天将12 天堂10 天胡4 天極2
    天庫5 天馳1 — a permutation of 1…12, which __main__ checks). Their sum is the ENERGY TOTAL
    (エネルギー総量), a number the tradition computes and stakes a claim on, so it is computed
    exactly. Its 位相法 is emitted at PILLAR level (律音, the two people sharing an identical
    stem-branch; 大半会; 納音 sameness), which is where it differs from the branch-level relations
    `trad_chinese.py` already has.

MONGOLIAN ZURKHAI зурхай
  Tibetan-derived, and `trad_tibetan_seasia.py` already has nagtsi's animal, element, mewa, parkha
  and marriage tally — so this block does the one thing Mongolian practice does DIFFERENTLY: the
  жаран (60-year cycle) year turns at ЦАГААН САР, the lunar new year, not at Lichun. The animal and
  element of the year are therefore computed from the LUNAR year here, and the disagreement with the
  Lichun year (which happens for every birth in the ~5 weeks between them) is emitted as its own
  flag — with the 60-cycle epoch checked: the Tibetan rabjung begins in 1027 CE, and 1027 − 4 gives
  sexagenary 丁卯 = FIRE-HARE, which is exactly what the Tibetan and Mongolian almanacs call it.
  Also the position in the lunar month under the Mongolian names (шинийн 1…30, битүүн the dark
  30th), and the animal relations recomputed on the lunar-year animals.
  NOT computed, and the reason: the Mongolian and Tibetan calendars are PHUGPA, whose mean-value
  arithmetic skips and doubles lunar dates (лхагва/chad·lhag), so a Mongolian tshes zhag is not the
  Chinese lunar day. Reproducing it needs the Phugpa epoch tables, which I do not have; the Chinese
  true-new-moon day is used and labelled as such. The мэнгэ anchor used in Mongolian almanacs is
  likewise omitted rather than guessed.

CHINESE ALMANAC ADDITIONS
  · 黃道黑道十二神, the YELLOW-and-BLACK day system, entirely absent upstream: 青龍 明堂 天刑 朱雀
    金匱 天德 白虎 玉堂 天牢 玄武 司命 勾陳 in order, the god of a day being (day branch − start)
    where the start is given by the verse 「寅申須加子，卯酉却加寅，辰戌龍位上，巳亥午上存，
    子午尋申位，丑未戌上真」— which is the closed form start = 2·(month branch − 2) mod 12, and it
    reproduces all twelve of the verse's cases (asserted). Six gods are 黃道 (auspicious:
    青龍 明堂 金匱 天德 玉堂 司命) and six 黑道.
  · 胎元, the conception pillar (month stem + 1, month branch + 3) — a classical BaZi object the
    upstream module does not compute.
  · The 28-xiu PAIR relations that upstream does not emit: the 七曜 relation as 生/剋 between the two
    luminaries' elements rather than a bare same-flag, the cross one-hots of the luminary pair
    (7×7) and the 四象 palace pair (4×4), and the 14-apart 沖.
  · The 值宿 (the day's own mansion on the continuous 28-day count) is NOT emitted. It is
    weekday-locked — the luminary in each name (房日兔, 虛日鼠, 昴日雞, 星日馬 are all 日) fixes the
    cycle modulo 7 — but that leaves four possible phases and I cannot verify which one an almanac
    uses without the almanac. Guessing one in four would be fabricating a position.

THE 天干 / 地支 / 五行 CONVENTIONS used here match `trad_chinese.py` so a reader can move between
the two modules: stems 0=甲…9=癸, branches 0=子…11=亥, elements 0=Wood 1=Fire 2=Earth 3=Metal
4=Water, day pillar = (JDN − 11) mod 60, sexagenary pillar index = (6·stem − 5·branch) mod 60.

NO WEDDING DAY IS READ, AND THAT COSTS THIS MODULE ITS MOST NATURAL FEATURE. The input contract
allows only the two birth dates and the two birthplaces; the marriage date is not an input. But
choosing a day is precisely what a 通書, a 宿曜暦 and a rokuyō calendar are FOR — 大安 for a wedding,
成 or 開 for 嫁娶, the 黃道 gods, a mansion that is not the couple's 壊宿. None of that is testable
here and none of it is emitted. Where a third chart genuinely helps, the DAVISON instant (slot 5,
the true midpoint in time between the two births) stands in: it is derived from the two dates of
birth alone, so it is admissible, and it is a real DOB-only relationship chart — but it is a
constructed moment, not a day anybody lived through, and no claim is made that an almanac would
have anything to say about it. Slots 3 and 4 (the secondary progressions) are avoided for the same
reason: they are measured to the wedding.

AN ERA RULER IS NOT A TRADITION. Anything of the form floor((year − epoch)/60) — which cycle of the
жаран a person was born in, which rabjung — is a monotone function of the birth year and scores like
one (AUC 0.64 on this data, the same as the raw year). It is admissible under the input contract and
it is emphatically NOT zurkhai, so it is not emitted: the жаран POSITION mod 60 is the tradition's
object and the cycle NUMBER is a birth-cohort proxy wearing its name. Birth-era effects belong to
`ctx_cohort.py`, where they can be seen for what they are.

WHAT NO EAST ASIAN SYSTEM CAN HAVE HERE: the HOUR PILLAR. It is marginalised where a system needs
the hour branch as a POSITION (Tử Vi's palaces, 文昌/文曲, 火星/鈴星), and simply absent where it is
needed as a CHARACTER (the hour stem-branch of the four pillars), because at 12:00 UT the hour
branch would be a constant and its stem a bijection of the day stem — no information, only noise
dressed as a pillar. Every Wu Xing or sipseong count below is therefore over six characters, not
eight, and every block that depends on that says so.
"""

import numpy as np
import swisseph as swe

TRADITION = ("East Asian deep: Vietnamese Tử Vi (Purple Star), Korean Saju sipseong, Japanese "
             "Shukuyō · Rokuyō · Onmyōdō · Sanmeigaku, Mongolian Zurkhai, Chinese almanac additions")

# ── stems, branches, elements — same conventions as trad_chinese.py ─────────────────────────────
STEM_EL = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4])          # 甲乙木 丙丁火 戊己土 庚辛金 壬癸水
STEM_YANG = np.array([1., 0., 1., 0., 1., 0., 1., 0., 1., 0.])
BRANCH_EL = np.array([4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4])  # 子水 丑土 寅卯木 辰土 巳午火 …
BRANCH_YANG = np.array([1., 0., 1., 0., 1., 0., 1., 0., 1., 0., 1., 0.])

# 地支藏干 with the 本氣/中氣/餘氣 weights (main 0.6, middle 0.3, residual 0.1; 0.7/0.3 for two-stem
# branches; 1.0 when a branch holds one stem alone) — 《三命通會》
HIDDEN = {
    0:  [(9, 1.0)], 1: [(5, .6), (9, .3), (7, .1)], 2: [(0, .6), (2, .3), (4, .1)],
    3:  [(1, 1.0)], 4: [(4, .6), (1, .3), (9, .1)], 5: [(2, .6), (4, .3), (6, .1)],
    6:  [(3, .7), (5, .3)], 7: [(5, .6), (3, .3), (1, .1)], 8: [(6, .6), (8, .3), (4, .1)],
    9:  [(7, 1.0)], 10: [(4, .6), (7, .3), (3, .1)], 11: [(8, .7), (0, .3)],
}
PRIN = np.array([h[0][0] for _, h in sorted(HIDDEN.items())])       # 本氣, the principal hidden stem

# 納音 — the 30 hidden elements of the 六十甲子 (甲子乙丑海中金 … 壬戌癸亥大海水)
NAYIN30 = np.array([3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4,
                    3, 1, 0, 2, 3, 1, 4, 2, 3, 0, 4, 2, 1, 0, 4])
NAYIN = NAYIN30[np.arange(60) // 2]
# 五行局 of Tử Vi: 水二局 木三局 金四局 土五局 火六局 — indexed by element 0W 1F 2E 3M 4Wa
CUC = np.array([3, 6, 5, 4, 2])

# 十二長生 — the branch in which each stem begins its cycle; yang stems run forward, yin backward
CS_START = np.array([11, 6, 2, 9, 2, 9, 5, 0, 8, 3])
# 十二大従星 of 算命学 keyed by that stage (0 長生 … 11 養) and their published energy numbers
JU_NAME = ["天貴", "天恍", "天南", "天禄", "天将", "天堂", "天胡", "天極", "天庫", "天馳",
           "天報", "天輔"]
JU_ENERGY = np.array([9., 7., 8., 11., 12., 10., 4., 2., 5., 1., 3., 6.])

# ── Tử Vi: the fourteen major stars, then the four we can also place ────────────────────────────
STARS = ["紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門",
         "天相", "天梁", "七殺", "破軍", "文昌", "文曲", "左輔", "右弼"]
NMAJ = 14
# 生年四化 by year stem — 化祿 化權 化科 化忌, as indices into STARS. 中州派 table; the 庚 化科 is
# disputed between 太陰, 天同 and 天府 between schools and 太陰 is taken here, said out loud.
SIHUA = np.array([
    [5, 13, 3, 2],    # 甲 廉貞祿 破軍權 武曲科 太陽忌
    [1, 11, 0, 7],    # 乙 天機 天梁 紫微 太陰
    [4, 1, 14, 5],    # 丙 天同 天機 文昌 廉貞
    [7, 4, 1, 9],     # 丁 太陰 天同 天機 巨門
    [8, 7, 17, 1],    # 戊 貪狼 太陰 右弼 天機
    [3, 8, 11, 15],   # 己 武曲 貪狼 天梁 文曲
    [2, 3, 7, 4],     # 庚 太陽 武曲 太陰(disputed) 天同
    [9, 2, 15, 14],   # 辛 巨門 太陽 文曲 文昌
    [11, 0, 16, 3],   # 壬 天梁 紫微 左輔 武曲
    [13, 9, 7, 8],    # 癸 破軍 巨門 太陰 貪狼
])
PALACE = ["命", "兄弟", "夫妻", "子女", "財帛", "疾厄", "遷移", "奴僕", "官祿", "田宅", "福德", "父母"]
# 祿存 by year stem 甲寅 乙卯 丙巳 丁午 戊巳 己午 庚申 辛酉 壬亥 癸子
LUCUN = np.array([2, 3, 5, 6, 5, 6, 8, 9, 11, 0])
# 天魁/天鉞 「甲戊庚牛羊，乙己鼠猴鄉，丙丁豬雞位，壬癸兔蛇藏，辛逢虎馬」
TKUI = np.array([1, 0, 11, 11, 1, 0, 1, 6, 3, 3])
TYUE = np.array([7, 8, 9, 9, 7, 8, 7, 2, 5, 5])
# 火星/鈴星 starts by year-branch trine 「寅午戌人丑卯方，申子辰人寅戌揚，巳酉丑人卯戌位，亥卯未人酉戌房」
HUO_START = {0: 2, 1: 3, 2: 1, 3: 9}      # key = year branch mod 4 (0 申子辰, 1 巳酉丑, 2 寅午戌, 3 亥卯未)
LING_START = {0: 10, 1: 10, 2: 3, 3: 10}

# ── Korean 십성 names, in the order the closed form produces ────────────────────────────────────
SIPSEONG = ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"]
# 원진 (Korean resentment pair) — an explicit table, because no single modulus isolates it: it is
# the CLASH partner shifted one place, +1 for the yang branches and −1 for the yin.
WONJIN = np.zeros((12, 12), bool)
for _a, _b in [(0, 7), (1, 6), (2, 9), (3, 8), (4, 11), (5, 10)]:
    WONJIN[_a, _b] = WONJIN[_b, _a] = True
# 귀문관살 鬼門關殺 — 子酉 丑午 寅未 卯申 辰亥 巳戌
GWIMUN = np.zeros((12, 12), bool)
for _a, _b in [(0, 9), (1, 6), (2, 7), (3, 8), (4, 11), (5, 10)]:
    GWIMUN[_a, _b] = GWIMUN[_b, _a] = True
# 괴강 魁罡 day pillars 庚辰 庚戌 壬辰 壬戌 (some texts add 戊戌 — flagged separately)
GOEGANG = [(6, 4), (6, 10), (8, 4), (8, 10)]
# 백호대살 白虎大殺 pillars 甲辰 乙未 丙戌 丁丑 戊辰 壬戌 癸丑
BAEKHO = [(0, 4), (1, 7), (2, 10), (3, 1), (4, 4), (8, 10), (9, 1)]

# ── Japanese Shukuyō: the 27 mansions from 昴 (= Krittika), and the almanac's month-start table ──
SHUKU = ("昴 畢 觜 参 井 鬼 柳 星 張 翼 軫 角 亢 氐 房 心 尾 箕 斗 女 虚 危 室 壁 奎 婁 胃").split()
SHUKU_START = np.array([22, 24, 26, 1, 3, 5, 8, 11, 13, 15, 18, 20])   # lunar month 1…12 → mansion
SHUKU_REL = ["命", "栄", "衰", "安", "危", "成", "壊", "友", "親"]
# a valence for the nine, summarising how the texts describe them; the nine flags are emitted too,
# so the weighting is one reading and the doctrine is the flags
SHUKU_VAL = np.array([0., 2., -1., 1., -2., 2., -3., 1., 2.])
ROKUYO = ["大安", "赤口", "先勝", "友引", "先負", "仏滅"]
ROKUYO_WED = np.array([1., 0., 0., 1., 0., -1.])     # 大安 best, 友引 welcome, 仏滅 avoided

# ── Onmyōdō: 天一神's 44-day circuit of the eight directions plus 16 days in the heavens ─────────
# (start sexagenary day index, days, direction 0=N 1=NE 2=E 3=SE 4=S 5=SW 6=W 7=NW, 8=in heaven)
TENICHI = [(45, 5, 1), (50, 6, 2), (56, 5, 3), (1, 6, 4), (7, 5, 5), (12, 6, 6),
           (18, 5, 7), (23, 6, 0), (29, 16, 8)]
TENICHI_DIR = np.zeros(60, np.int64)
for _s, _len, _d in TENICHI:
    for _i in range(_len):
        TENICHI_DIR[(_s + _i) % 60] = _d
# 大将軍 stands three years in a quarter: 亥子丑 W, 寅卯辰 N, 巳午未 E, 申酉戌 S
DAISHOGUN = np.array([6, 6, 0, 0, 0, 2, 2, 2, 4, 4, 4, 6])
# the branch of each of the eight compass points, for turning a branch into a direction
BR_DIR = np.array([0, 1, 1, 2, 3, 3, 4, 5, 5, 6, 7, 7])     # 子N 丑寅NE 卯E 辰巳SE 午S 未申SW 酉W 戌亥NW

# ── the 28 xiu: 七曜 luminary (木金土日月火水 from 角) and the four 四象 palaces ─────────────────
XIU = ("角 亢 氐 房 心 尾 箕 斗 牛 女 虛 危 室 壁 奎 婁 胃 昴 畢 觜 參 井 鬼 柳 星 張 翼 軫").split()
XIU_LUM = np.arange(28) % 7
LUM_EL = np.array([0, 3, 2, 1, 4, 1, 4])   # 木金土日月火水 → Wood Metal Earth Fire(Sun) Water(Moon) Fire Water

# ── 黃道黑道十二神 ───────────────────────────────────────────────────────────────────────────────
HUANGHEI = ["青龍", "明堂", "天刑", "朱雀", "金匱", "天德", "白虎", "玉堂", "天牢", "玄武",
            "司命", "勾陳"]
HUANG = np.array([1., 1., 0., 0., 1., 1., 0., 1., 0., 0., 1., 0.])    # 1 = 黃道 auspicious

# Slot 5 is the DAVISON midpoint — the true midpoint in time between the two births, and the only
# third chart derivable from the two dates of birth alone. Slot 2 (the wedding) is deliberately
# never touched: the marriage date is not an input. See the docstring.
OLD, YNG, DAV = 0, 1, 5
SYNODIC = 29.530588861
NM_EPOCH = 2451550.09766          # Meeus AA ch.49: lunation k = 0 is the new moon of 2000 Jan 6


# ── plumbing ────────────────────────────────────────────────────────────────────────────────────
def _oh(idx, k):
    """One-hot of an integer array, (n, k) float64."""
    return np.eye(k)[np.clip(np.asarray(idx, np.int64), 0, k - 1)]


def _stack(cols):
    n = np.asarray(cols[0]).shape[0]
    return np.ascontiguousarray(np.hstack([np.asarray(c, np.float64).reshape(n, -1) for c in cols]),
                                np.float64)


def _cal(jd):
    """Gregorian year, month, day and integer Julian Day Number (Fliegel & Van Flandern)."""
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


def _pillar_index(stem, branch):
    """The sexagenary index of a (stem, branch) pair: (6·stem − 5·branch) mod 60."""
    return np.mod(6 * np.asarray(stem, np.int64) - 5 * np.asarray(branch, np.int64), 60)


def _life_stage(stem, branch):
    """十二長生 — 0 長生 … 11 養; yin stems run backward through the branches."""
    st = CS_START[stem]
    return np.where(STEM_YANG[stem] > 0, (branch - st) % 12, (st - branch) % 12).astype(np.int64)


# ── the true new moon: Meeus AA ch.49 as a seed, the Swiss Ephemeris as the answer ──────────────
_NM = {}


def _nm_series(k):
    """Meeus, *Astronomical Algorithms* 2nd ed., ch. 49 — the truncated NEW MOON series, in TT."""
    k = np.asarray(k, np.float64)
    T = k / 1236.85
    jde = (NM_EPOCH + SYNODIC * k + 0.00015437 * T ** 2
           - 0.000000150 * T ** 3 + 0.00000000073 * T ** 4)
    Ec = 1 - 0.002516 * T - 0.0000074 * T ** 2
    M = np.deg2rad(2.5534 + 29.10535670 * k - 0.0000014 * T ** 2 - 0.00000011 * T ** 3)
    Mp = np.deg2rad(201.5643 + 385.81693528 * k + 0.0107582 * T ** 2
                    + 0.00001238 * T ** 3 - 0.000000058 * T ** 4)
    F = np.deg2rad(160.7108 + 390.67050284 * k - 0.0016118 * T ** 2
                   - 0.00000227 * T ** 3 + 0.000000011 * T ** 4)
    Om = np.deg2rad(124.7746 - 1.56375588 * k + 0.0020672 * T ** 2 + 0.00000215 * T ** 3)
    s = np.sin
    jde = jde + (-0.40720 * s(Mp) + 0.17241 * Ec * s(M) + 0.01608 * s(2 * Mp) + 0.01039 * s(2 * F)
                 + 0.00739 * Ec * s(Mp - M) - 0.00514 * Ec * s(Mp + M) + 0.00208 * Ec ** 2 * s(2 * M)
                 - 0.00111 * s(Mp - 2 * F) - 0.00057 * s(Mp + 2 * F) + 0.00056 * Ec * s(2 * Mp + M)
                 - 0.00042 * s(3 * Mp) + 0.00042 * Ec * s(M + 2 * F) + 0.00038 * Ec * s(M - 2 * F)
                 - 0.00024 * Ec * s(2 * Mp - M) - 0.00017 * s(Om) - 0.00007 * s(Mp + 2 * M))
    return jde


def _elong(jd):
    """(Moon − Sun) longitude in (−180, 180], and the rate of change in deg/day, from the ephemeris."""
    fl = swe.FLG_SWIEPH | swe.FLG_SPEED
    mo = swe.calc_ut(float(jd), swe.MOON, fl)[0]
    su = swe.calc_ut(float(jd), swe.SUN, fl)[0]
    return (mo[0] - su[0] + 180.0) % 360.0 - 180.0, mo[3] - su[3], su[0]


def _nm_lookup(karr):
    """True new moon (UT julian day) and the Sun's longitude there, for lunation numbers `karr`."""
    ks = np.unique(np.asarray(karr, np.int64))
    need = [int(k) for k in ks if int(k) not in _NM]
    if need:
        seed = _nm_series(np.array(need, np.float64))
        for kk, t0 in zip(need, seed):
            t = float(t0) - swe.deltat(float(t0))          # TT → UT
            for _ in range(6):
                f, rate, _s = _elong(t)
                t -= f / rate
            f, _r, sl = _elong(t)
            assert abs(f) < 1e-5, f"new moon {kk} did not converge ({f:.2e} deg)"
            _NM[kk] = (t, sl)
    ka = np.asarray(karr, np.int64)
    t = np.array([_NM[int(k)][0] for k in ka])
    sl = np.array([_NM[int(k)][1] for k in ka])
    return t, sl


def _lunar(E, slot):
    """The Chinese-style lunisolar calendar for one instant slot.

    Returns the lunar month number and the leap flag, the lunar DAY in each of the three calendar
    zones (UTC+7 Vietnamese, +8 Chinese, +9 Korean/Japanese), and the lunar YEAR's stem and branch.
    See the module docstring for the 無中氣置閏 rule and the one case where it can disagree with the
    published calendar.
    """
    jd = np.asarray(E.JD[slot], np.float64)
    kc = np.rint((jd - NM_EPOCH) / SYNODIC).astype(np.int64)
    cand = np.stack([_nm_lookup(kc + d)[0] for d in (-2, -1, 0, 1)])        # (4, n)
    ok = cand <= jd[None, :]
    assert ok[0].all(), "two lunations before the instant must precede it"
    pick = 3 - np.argmax(ok[::-1], axis=0)                                  # last True
    k0 = kc - 2 + pick
    t0, sl0 = _nm_lookup(k0)
    t1, sl1 = _nm_lookup(k0 + 1)
    # 無中氣置閏: is a multiple of 30 deg of solar longitude crossed inside this lunar month?
    a = np.mod(sl0 - 270.0, 360.0)                    # degrees of Sun since 冬至 at the new moon
    d = np.mod(sl1 - sl0, 360.0)                      # solar travel over the month, ~29 deg
    kk = np.floor(a / 30.0).astype(np.int64)
    has = (30.0 * (kk + 1)) < (a + d)
    month = np.mod(10 + kk + has.astype(np.int64), 12) + 1
    leap = (~has).astype(np.float64)
    gy, gm, _gd, jdn = _cal(jd)
    day = {tz: (jdn - np.floor(t0 + 0.5 + tz / 24.0).astype(np.int64) + 1) for tz in (7, 8, 9)}
    for tz in day:
        day[tz] = np.clip(day[tz], 1, 30)
    # the lunar YEAR turns at 正月初一, so months 11 and 12 falling in January or February belong to
    # the previous lunar year
    ly = gy - ((month >= 11) & (gm <= 2)).astype(np.int64)
    return dict(month=month, leap=leap, day=day, ly=ly, t0=t0, t1=t1,
                lys=np.mod(ly - 4, 10), lyb=np.mod(ly - 4, 12), jdn=jdn, gm=gm)


def _pillars(E, slot, lonshift=None):
    """Year / month / day pillars on the SOLAR-term boundaries, as BaZi and Saju both take them.

    `lonshift` (degrees of birthplace longitude, or None) moves the Sun to LOCAL noon rather than
    12:00 UT before the solar term is read — the Korean 진태양시 correction; see that block.
    No hour pillar: the module docstring says why.
    """
    y, m, _d, jdn = _cal(E.JD[slot])
    lam = np.asarray(E.LON[slot, E.IDX["Sun"]], np.float64)
    if lonshift is not None:
        lam = lam + np.asarray(E.SPD[slot, E.IDX["Sun"]], np.float64) * (-lonshift / 360.0)
    lam = np.mod(lam, 360.0)
    sy = y - ((m <= 2) & (lam < 315.0)).astype(np.int64)          # the 立春 year
    off = np.mod(lam - 315.0, 360.0)
    jq = np.floor(off / 15.0).astype(np.int64)
    mnum = np.floor(off / 30.0).astype(np.int64)
    yidx = np.mod(sy - 4, 60)
    ys, yb = yidx % 10, yidx % 12
    mb = (2 + mnum) % 12
    ms = (2 * ys + 2 + mnum) % 10                                 # 五虎遁
    didx = np.mod(jdn - 11, 60)                                   # JDN 11 = 甲子
    return dict(sy=sy, jq=jq, mnum=mnum, yidx=yidx, ys=ys, yb=yb, ms=ms, mb=mb,
                midx=_pillar_index(ms, mb), didx=didx, ds=didx % 10, db=didx % 12, jdn=jdn)


# ── Tử Vi ───────────────────────────────────────────────────────────────────────────────────────
def _ziwei(day, cuc):
    """安紫微訣 — 紫微's branch from the lunar day and the 五行局. Verified against the published
    tables for all five 局 in __main__."""
    day = np.asarray(day, np.int64)
    cuc = np.asarray(cuc, np.int64)
    r = day % cuc
    borrow = np.where(r == 0, 0, cuc - r)
    q = (day + borrow) // cuc
    z = np.mod(2 + q - 1, 12)
    return np.mod(np.where(borrow % 2 == 0, z + borrow, z - borrow), 12)


def _tuvi(lm, ld, ys, yb):
    """Every Tử Vi placement, for all TWELVE possible birth hours at once → (12, n) arrays."""
    hb = np.arange(12, dtype=np.int64)[:, None]
    lm = np.asarray(lm, np.int64)[None, :]
    ld = np.asarray(ld, np.int64)[None, :]
    ysb = np.asarray(ys, np.int64)[None, :]
    ybb = np.asarray(yb, np.int64)[None, :]
    life = np.mod(2 + (lm - 1) - hb, 12)                # 命宮: 寅 for 正月, forward to the birth
    body = np.mod(2 + (lm - 1) + hb, 12)                # 身宮                month, back to the hour
    lstem = np.mod(2 * ysb + 2 + np.mod(life - 2, 12), 10)              # 五虎遁 on the life palace
    el = NAYIN[_pillar_index(lstem, life)]
    cuc = CUC[el]
    z = _ziwei(np.broadcast_to(ld, cuc.shape), cuc)
    f = np.mod(4 - z, 12)                               # 天府, the 寅–申 mirror of 紫微
    S = np.empty((12, len(STARS)) + z.shape[1:], np.int64)
    for i, o in enumerate((0, -1, -3, -4, -5, -8)):                     # 紫微系
        S[:, i] = np.mod(z + o, 12)
    for i, o in enumerate((0, 1, 2, 3, 4, 5, 6, 10), start=6):          # 天府系
        S[:, i] = np.mod(f + o, 12)
    S[:, 14] = np.mod(10 - hb, 12)                      # 文昌 from 戌, backward to the hour
    S[:, 15] = np.mod(4 + hb, 12)                       # 文曲 from 辰, forward
    S[:, 16] = np.mod(4 + (lm - 1), 12) + np.zeros_like(z)              # 左輔 from 辰 by month
    S[:, 17] = np.mod(10 - (lm - 1), 12) + np.zeros_like(z)             # 右弼 from 戌 by month
    hs = np.zeros_like(ybb)
    ls = np.zeros_like(ybb)
    for g in range(4):
        hs = np.where(ybb % 4 == g, HUO_START[g], hs)
        ls = np.where(ybb % 4 == g, LING_START[g], ls)
    return dict(life=life, body=body, cuc=cuc, el=el, z=z, f=f, S=S,
                huo=np.mod(hs + hb, 12) + np.zeros_like(z),
                ling=np.mod(ls + hb, 12) + np.zeros_like(z))


def _palace_branch(life, j):
    """The branch of palace `j` — the twelve palaces run BACKWARD from 命宮."""
    return np.mod(life - j, 12)


def _in_palace(S, pb):
    """Probability, over the twelve equally-likely birth hours, that each star sits in palace `pb`.

    S is (12, nstar, n) star branches, pb is (12, n) the palace's branch → (n, nstar).
    """
    return (S == pb[:, None, :]).mean(axis=0).T


# ── Korean 십성 ─────────────────────────────────────────────────────────────────────────────────
def _sipseong(day_stem, other_stem):
    """The ten gods in one closed form: 2·((element(other) − element(day)) mod 5) + [polarity differs].

    0 비견 1 겁재 2 식신 3 상관 4 편재 5 정재 6 편관 7 정관 8 편인 9 정인.
    """
    d = np.asarray(day_stem, np.int64)
    o = np.asarray(other_stem, np.int64)
    rel = (STEM_EL[o] - STEM_EL[d]) % 5
    diff = (STEM_YANG[o] != STEM_YANG[d]).astype(np.int64)
    return 2 * rel + diff


def _sipseong_hist(P, hidden):
    """The sipseong distribution over a chart's characters, against its own day stem.

    `hidden=False` counts the four visible characters other than the day stem — year stem, month
    stem and the year/month/day branches taken by their principal hidden stem. `hidden=True` uses
    the full 藏干 with the 本氣/中氣/餘氣 weights. SIX characters, not eight: no hour pillar.
    """
    n = P["ds"].shape[0]
    H = np.zeros((n, 10))
    for s in ("ys", "ms"):
        H += _oh(_sipseong(P["ds"], P[s]), 10)
    for b in ("yb", "mb", "db"):
        if hidden:
            for st, w in HIDDEN.items():
                m = (P[b] == st)
                if not m.any():
                    continue
                for hs, hw in w:
                    g = _sipseong(P["ds"][m], np.full(m.sum(), hs))
                    np.add.at(H, (np.where(m)[0], g), hw)
        else:
            H += _oh(_sipseong(P["ds"], PRIN[P[b]]), 10)
    return H


def _trine(b):
    """The 三會 directional trio index of a branch: 0 寅卯辰, 1 巳午未, 2 申酉戌, 3 亥子丑."""
    return ((np.asarray(b, np.int64) - 2) % 12) // 3


def build(E):
    out = {}
    n = E.n
    P = {s: _pillars(E, s) for s in (OLD, YNG, DAV)}
    L = {s: _lunar(E, s) for s in (OLD, YNG, DAV)}
    O, Y, D = P[OLD], P[YNG], P[DAV]
    LO, LY, LD = L[OLD], L[YNG], L[DAV]

    # ══ 1 ── the lunisolar calendar itself ══════════════════════════════════════════════════════
    # New here: trad_chinese.py never leaves the solar year. The three calendar zones are the
    # Vietnamese (UTC+7, Hồ Ngọc Đức), the Chinese (UTC+8) and the modern Korean/Japanese (UTC+9);
    # their disagreements are the mechanism by which Tết and 春節 fall on different days.
    cols = []
    for T in (LO, LY, LD):
        cols += [_oh(T["month"] - 1, 12), T["leap"][:, None],
                 E.circ((T["month"] - 1) * 30.0).reshape(n, 2)]
        for tz in (7, 8, 9):
            cols += [_oh(T["day"][tz] - 1, 30), E.circ((T["day"][tz] - 1) * 12.0).reshape(n, 2),
                     (T["day"][tz] / 30.0)[:, None]]
        cols += [(T["day"][7] != T["day"][8]).astype(float)[:, None],
                 (T["day"][8] != T["day"][9]).astype(float)[:, None],
                 (T["day"][7] == 15).astype(float)[:, None],       # full moon day 望
                 (T["day"][7] == 1).astype(float)[:, None],
                 (T["day"][7] >= 29).astype(float)[:, None]]      # 晦 / битүүн, the dark end
    for a, b, tag in ((LO, LY, "oy"),):
        dm = (a["month"].astype(float) - b["month"]) % 12
        dd = (a["day"][8].astype(float) - b["day"][8]) % 30
        cols += [_oh(dm.astype(np.int64), 12), E.circ(dm * 30.0).reshape(n, 2),
                 (np.minimum(dm, 12 - dm) / 6.0)[:, None],
                 _oh(dd.astype(np.int64), 30), E.circ(dd * 12.0).reshape(n, 2),
                 (np.minimum(dd, 30 - dd) / 15.0)[:, None],
                 (a["month"] == b["month"]).astype(float)[:, None],
                 (a["day"][8] == b["day"][8]).astype(float)[:, None],
                 (a["leap"] + b["leap"])[:, None]]
    out["ead: sino-viet lunar month, day and leap (3 zones)"] = _stack(cols)

    # ══ 2 ── Tử Vi frame: 五行局 and 紫微 measured against the palace ring ══════════════════════
    # The palace ring itself is uniform under a uniform hour prior (docstring), so nothing absolute
    # about it is emitted. The 局 and the OFFSETS are not uniform and they are what is emitted.
    V = {}
    for s, T in ((OLD, LO), (YNG, LY)):
        V[s] = _tuvi(T["month"], T["day"][7], T["lys"], T["lyb"])
    cols = []
    for s in (OLD, YNG):
        v = V[s]
        cuc_d = np.stack([(v["cuc"] == c).mean(axis=0) for c in (2, 3, 4, 5, 6)], axis=1)
        el_d = np.stack([(v["el"] == e).mean(axis=0) for e in range(5)], axis=1)
        dz = np.stack([(np.mod(v["z"] - v["life"], 12) == j).mean(axis=0) for j in range(12)], axis=1)
        dzs = np.stack([(np.mod(v["z"] - _palace_branch(v["life"], 2), 12) == j).mean(axis=0)
                        for j in range(12)], axis=1)
        df = np.stack([(np.mod(v["f"] - v["life"], 12) == j).mean(axis=0) for j in range(12)], axis=1)
        zb = np.stack([(v["z"] == j).mean(axis=0) for j in range(12)], axis=1)
        cols += [cuc_d, el_d, dz, dzs, df, zb,
                 E.entropy(cuc_d)[:, None], E.entropy(dz)[:, None], E.entropy(zb)[:, None],
                 (v["cuc"] * 1.0).mean(axis=0)[:, None],
                 (np.mod(v["z"] - v["body"], 12) == 0).mean(axis=0)[:, None],
                 ((v["z"] == 2) | (v["z"] == 8)).mean(axis=0)[:, None]]   # 紫府同宮 in 寅 or 申
    # the two charts' 局 and 紫微 seats against each other
    cq = np.stack([[(V[OLD]["cuc"] == a).mean(axis=0) * (V[YNG]["cuc"] == b).mean(axis=0)
                    for b in (2, 3, 4, 5, 6)] for a in (2, 3, 4, 5, 6)]).reshape(25, n).T
    dzz = np.stack([(np.mod(V[OLD]["z"][:, None, :] - V[YNG]["z"][None, :, :], 12) == j).mean(axis=(0, 1))
                    for j in range(12)], axis=1)
    cols += [cq, dzz, E.entropy(dzz)[:, None]]
    out["ead: tuvi ngu hanh cuc + ziwei frame (hour-marginalised)"] = _stack(cols)

    # ══ 3 ── Tử Vi: which of the fourteen major stars occupy which palace ═══════════════════════
    # 夫妻 (cung Thê, the spouse palace) is the tradition's own claim about marriage; 子女 is its
    # claim about children; 命 and 福德 are the two it reads for the person themselves. Every number
    # is a probability over the twelve possible birth hours.
    cols = []
    for s in (OLD, YNG):
        v = V[s]
        for j in (0, 2, 3, 10):
            pb = _palace_branch(v["life"], j)
            pr = _in_palace(v["S"][:, :NMAJ], pb)
            cnt = (v["S"][:, :NMAJ] == pb[:, None, :]).sum(axis=1)
            cols += [pr, (cnt == 0).mean(axis=0)[:, None], cnt.mean(axis=0)[:, None],
                     E.entropy(pr / np.maximum(pr.sum(axis=1, keepdims=True), 1e-9))[:, None]]
        # 借星安宮: when 夫妻 is empty the school borrows from the opposite palace 官祿
        sp = _palace_branch(v["life"], 2)
        op = _palace_branch(v["life"], 8)
        emp = (v["S"][:, :NMAJ] == sp[:, None, :]).sum(axis=1) == 0
        cols += [emp.mean(axis=0)[:, None],
                 (emp[:, None, :] & (v["S"][:, :NMAJ] == op[:, None, :])).mean(axis=0).T]
    out["ead: tuvi palace star distributions (menh, the, tu tuc, phuc duc)"] = _stack(cols)

    # ══ 4 ── Tử Vi minor stars and 生年四化 ════════════════════════════════════════════════════
    # 紅鸞 and 天喜 are the romance pair, 孤辰 and 寡宿 the loneliness pair, and all four come from
    # the year branch alone — no hour, so these are EXACT, not marginalised. The 四化 are exact in
    # identity (year stem) and marginalised in position.
    cols = []
    for s, T in ((OLD, LO), (YNG, LY)):
        v = V[s]
        yb, ys = T["lyb"], T["lys"]
        t = _trine(yb)
        hongluan = np.mod(3 - yb, 12)
        thienhi = np.mod(9 - yb, 12)
        gochen = np.mod(5 + 3 * t, 12)
        quasuc = np.mod(1 + 3 * t, 12)
        thienma = np.array([2, 11, 8, 5])[yb % 4]
        lucun = LUCUN[ys]
        kinhduong = np.mod(lucun + 1, 12)
        daila = np.mod(lucun - 1, 12)
        thienhinh = np.mod(9 + (T["month"] - 1), 12)
        thienyeu = np.mod(1 + (T["month"] - 1), 12)
        cols += [_oh(hongluan, 12), _oh(thienhi, 12), _oh(gochen, 12), _oh(quasuc, 12),
                 _oh(thienma, 12), _oh(lucun, 12), _oh(kinhduong, 12), _oh(daila, 12),
                 _oh(TKUI[ys], 12), _oh(TYUE[ys], 12), _oh(thienhinh, 12), _oh(thienyeu, 12)]
        # each of those exact stars against the (uniform) palace ring is uniform, so what is emitted
        # is the marginal probability that it lands in the SPOUSE palace — which is 1/12 only if the
        # star is independent of the hour, and these are, so instead the informative form is the
        # offset from 紫微, whose seat is hour-dependent
        for nm_, br in (("hongluan", hongluan), ("thienhi", thienhi), ("gochen", gochen),
                        ("lucun", lucun), ("thienyeu", thienyeu)):
            d = np.stack([(np.mod(v["z"] - br[None, :], 12) == j).mean(axis=0) for j in range(12)],
                         axis=1)
            cols.append(d)
        # 四化: is the transformed star in the spouse palace, the life palace, the child palace?
        sh = SIHUA[ys]                                                  # (n, 4)
        for j in (0, 2, 3):
            pb = _palace_branch(v["life"], j)
            for c in range(4):
                sb = v["S"][:, sh[:, c], np.arange(n)]                  # (12, n)
                cols.append((sb == pb).mean(axis=0)[:, None])
        cols += [_oh(sh[:, 3], len(STARS)), _oh(sh[:, 0], len(STARS))]   # which star carries 忌 / 祿
        # 火星/鈴星, both hour-dependent, against the spouse palace
        sp = _palace_branch(v["life"], 2)
        cols += [(v["huo"] == sp).mean(axis=0)[:, None], (v["ling"] == sp).mean(axis=0)[:, None],
                 (kinhduong[None, :] == sp).mean(axis=0)[:, None]]
    out["ead: tuvi minor stars + sinh nien tu hoa"] = _stack(cols)

    # ══ 5 ── Tử Vi couple overlay ═════════════════════════════════════════════════════════════
    # Only comparisons that survive marginalisation are here: star-to-star between the two charts
    # where both stars are hour-independent (exact), and star-set similarity between the two spouse
    # palaces (each computed inside its own chart, so the palace ring does not cancel).
    cols = []
    ta, tb = _trine(LO["lyb"]), _trine(LY["lyb"])
    hla, hlb = np.mod(3 - LO["lyb"], 12), np.mod(3 - LY["lyb"], 12)
    hxa, hxb = np.mod(9 - LO["lyb"], 12), np.mod(9 - LY["lyb"], 12)
    gca, gcb = np.mod(5 + 3 * ta, 12), np.mod(5 + 3 * tb, 12)
    qsa, qsb = np.mod(1 + 3 * ta, 12), np.mod(1 + 3 * tb, 12)
    lca, lcb = LUCUN[LO["lys"]], LUCUN[LY["lys"]]
    for nm_, a, b in (("hongluan", hla, hlb), ("thienhi", hxa, hxb), ("gochen", gca, gcb),
                      ("quasuc", qsa, qsb), ("lucun", lca, lcb)):
        d = np.mod(a - b, 12)
        cols += [_oh(d, 12), (a == b).astype(float)[:, None],
                 E.circ(d * 30.0).reshape(n, 2)]
    cols += [(hla == hxb).astype(float)[:, None], (hxa == hlb).astype(float)[:, None],
             (gca == qsb).astype(float)[:, None], (qsa == gcb).astype(float)[:, None],
             (lca == LUCUN[LY["lys"]]).astype(float)[:, None]]
    # the two spouse palaces' major-star profiles: agreement, overlap, and the pair of dominant stars
    pa = _in_palace(V[OLD]["S"][:, :NMAJ], _palace_branch(V[OLD]["life"], 2))
    pb = _in_palace(V[YNG]["S"][:, :NMAJ], _palace_branch(V[YNG]["life"], 2))
    la = _in_palace(V[OLD]["S"][:, :NMAJ], V[OLD]["life"])
    lb = _in_palace(V[YNG]["S"][:, :NMAJ], V[YNG]["life"])
    cols += [(pa * pb).sum(axis=1)[:, None], np.abs(pa - pb).sum(axis=1)[:, None],
             (pa * lb).sum(axis=1)[:, None], (la * pb).sum(axis=1)[:, None],
             (la * lb).sum(axis=1)[:, None], pa * pb, np.minimum(pa, pb)]
    # 四化 忌 star shared between the two charts
    ja, jb = SIHUA[LO["lys"], 3], SIHUA[LY["lys"], 3]
    cols += [(ja == jb).astype(float)[:, None],
             (SIHUA[LO["lys"], 0] == SIHUA[LY["lys"], 0]).astype(float)[:, None],
             _oh(ja, len(STARS)) * _oh(jb, len(STARS))]
    out["ead: tuvi couple overlay (hong loan, thien hi, spouse-palace sets)"] = _stack(cols)

    # ══ 6 ── Korean 십성: the ten gods across the pillars ═══════════════════════════════════════
    cols = []
    for s in (OLD, YNG, DAV):
        Q = P[s]
        hv = _sipseong_hist(Q, False)
        hh = _sipseong_hist(Q, True)
        cols += [hv, hh, hh / np.maximum(hh.sum(axis=1, keepdims=True), 1e-9),
                 E.entropy(hh / np.maximum(hh.sum(axis=1, keepdims=True), 1e-9))[:, None],
                 # the five 육친 groups: 비겁 식상 재성 관성 인성
                 np.stack([hh[:, 0] + hh[:, 1], hh[:, 2] + hh[:, 3], hh[:, 4] + hh[:, 5],
                           hh[:, 6] + hh[:, 7], hh[:, 8] + hh[:, 9]], axis=1),
                 (hh == 0).sum(axis=1)[:, None]]           # how many of the ten are missing 무 (無)
    # each partner's day stem read as a ten god of the other's — the 일간 대 일간 core of 궁합,
    # asymmetric, so both directions
    goy = _sipseong(O["ds"], Y["ds"])
    gyo = _sipseong(Y["ds"], O["ds"])
    cols += [_oh(goy, 10), _oh(gyo, 10), (goy == gyo).astype(float)[:, None],
             _oh(_sipseong(O["ds"], PRIN[Y["db"]]), 10), _oh(_sipseong(Y["ds"], PRIN[O["db"]]), 10),
             _oh(_sipseong(O["ds"], Y["ms"]), 10), _oh(_sipseong(Y["ds"], O["ms"]), 10)]
    out["ead: saju sipseong across the pillars"] = _stack(cols)

    # ══ 7 ── Korean 격국 and 신강/신약 ═════════════════════════════════════════════════════════
    cols = []
    for s in (OLD, YNG):
        Q = P[s]
        gg = _sipseong(Q["ds"], PRIN[Q["mb"]])                          # 월지 본기 → the structure
        cols += [_oh(gg, 10),
                 (gg == 0).astype(float)[:, None],                      # 건록격 (비견 in the month)
                 (gg == 1).astype(float)[:, None]]                      # 양인격 (겁재)
        hh = _sipseong_hist(Q, True)
        supp = hh[:, 0] + hh[:, 1] + hh[:, 8] + hh[:, 9]                 # 비겁 + 인성
        drain = hh[:, 2] + hh[:, 3] + hh[:, 4] + hh[:, 5] + hh[:, 6] + hh[:, 7]
        # 득령: the month branch supports the day stem — the textbooks weight it double
        mg = _sipseong(Q["ds"], PRIN[Q["mb"]])
        deok = np.isin(mg, [0, 1, 8, 9]).astype(float)
        cols += [supp[:, None], drain[:, None], (supp - drain)[:, None],
                 (supp + 2 * deok - drain)[:, None], deok[:, None],
                 (supp / np.maximum(supp + drain, 1e-9))[:, None],
                 # the five-element census of the whole chart, and which element is missing
                 np.stack([(STEM_EL[Q["ys"]] == e).astype(float) + (STEM_EL[Q["ms"]] == e)
                           + (BRANCH_EL[Q["yb"]] == e) + (BRANCH_EL[Q["mb"]] == e)
                           + (BRANCH_EL[Q["db"]] == e) + (STEM_EL[Q["ds"]] == e)
                           for e in range(5)], axis=1),
                 _oh(STEM_EL[Q["ds"]], 5), STEM_YANG[Q["ds"]][:, None],
                 _oh(_life_stage(Q["ds"], Q["db"]), 12),                # 일주 십이운성
                 _oh(_life_stage(Q["ds"], Q["mb"]), 12)]
    # the pair: strength difference and element complementarity
    def _cen(Q):
        return np.stack([(STEM_EL[Q["ys"]] == e).astype(float) + (STEM_EL[Q["ms"]] == e)
                         + (BRANCH_EL[Q["yb"]] == e) + (BRANCH_EL[Q["mb"]] == e)
                         + (BRANCH_EL[Q["db"]] == e) + (STEM_EL[Q["ds"]] == e) for e in range(5)],
                        axis=1)
    ca, cb = _cen(O), _cen(Y)
    cols += [ca + cb, np.abs(ca - cb), (ca * cb).sum(axis=1)[:, None],
             ((ca == 0) & (cb > 0)).sum(axis=1)[:, None],        # partner supplies what is missing
             ((cb == 0) & (ca > 0)).sum(axis=1)[:, None],
             ((ca == 0) & (cb == 0)).sum(axis=1)[:, None]]
    out["ead: saju gyeokguk + sin-gang strength"] = _stack(cols)

    # ══ 8 ── Korean 궁합: 원진, 귀문관살 and the marriage 신살 ═════════════════════════════════
    cols = []
    for ka, kb, tag in (("yb", "yb", "year"), ("db", "db", "day"), ("mb", "mb", "month"),
                        ("yb", "db", "cross1"), ("db", "yb", "cross2")):
        a, b = O[ka], Y[kb]
        cols += [WONJIN[a, b].astype(float)[:, None], GWIMUN[a, b].astype(float)[:, None],
                 (a == b).astype(float)[:, None],
                 (np.abs(((a - b + 6) % 12) - 6) == 6).astype(float)[:, None],   # 충
                 ((a % 4) == (b % 4)).astype(float)[:, None] - (a == b).astype(float)[:, None]]
    # 원진 anywhere between the two charts is what practitioners actually tally
    wtot = np.zeros(n)
    gtot = np.zeros(n)
    for ka in ("yb", "mb", "db"):
        for kb in ("yb", "mb", "db"):
            wtot += WONJIN[O[ka], Y[kb]]
            gtot += GWIMUN[O[ka], Y[kb]]
    cols += [wtot[:, None], gtot[:, None], (wtot > 0).astype(float)[:, None]]
    for s in (OLD, YNG):
        Q = P[s]
        # 도화살 the peach blossom (the 子午卯酉 seat of the year trine) and 홍염살 by day stem
        doh = np.array([9, 6, 3, 0])[Q["yb"] % 4]
        hong = np.array([6, 6, 2, 7, 4, 4, 10, 9, 0, 8])[Q["ds"]]
        gk = np.zeros(n)
        for st, br in GOEGANG:
            gk += ((Q["ds"] == st) & (Q["db"] == br)).astype(float)
        bh = np.zeros(n)
        for st, br in BAEKHO:
            for kk in (("ys", "yb"), ("ms", "mb"), ("ds", "db")):
                bh += ((Q[kk[0]] == st) & (Q[kk[1]] == br)).astype(float)
        yangin = (Q["db"] == np.array([3, 4, 6, 7, 6, 7, 9, 10, 0, 1])[Q["ds"]]).astype(float)
        cols += [_oh(doh, 12), _oh(hong, 12), gk[:, None], bh[:, None], yangin[:, None],
                 np.isin(Q["db"], doh).astype(float)[:, None],
                 (Q["yb"] == doh).astype(float)[:, None]]
    # both partners' 도화 on the same branch, and the day-pillar 납음 relation
    doa = np.array([9, 6, 3, 0])[O["yb"] % 4]
    dob_ = np.array([9, 6, 3, 0])[Y["yb"] % 4]
    na, nb = NAYIN[O["didx"]], NAYIN[Y["didx"]]
    cols += [(doa == dob_).astype(float)[:, None],
             _oh(na * 5 + nb, 25), (na == nb).astype(float)[:, None],
             ((nb - na) % 5 == 1).astype(float)[:, None],       # A's day element generates B's
             ((nb - na) % 5 == 2).astype(float)[:, None]]       # A's overcomes B's
    out["ead: saju gunghap — wonjin, gwimun, sinsal"] = _stack(cols)

    # ══ 9 ── Korean 진태양시: the solar term read at LOCAL noon, from the birthplace longitude ══
    # This is the one place the missing longitude really costs something. Korean practice corrects
    # the clock to true solar time (Seoul is 127 deg E on a 135 deg E zone, −32 minutes), and the
    # month pillar turns on the solar-term instant, so a birth within half a day of a boundary can
    # change pillar. Emitted only when the dataset carries coordinates; otherwise the whole block
    # would be constant and it is dropped with a note rather than faked.
    known = np.isfinite(E.LON_O) & np.isfinite(E.LON_Y)
    # `.any()`, not `.mean() > 0.01`: whether birthplaces exist is a property of the input CONTRACT, the
    # same for every row and every chunk, where a fraction of the batch is not.
    if np.isfinite(E.LON_O).any():
        cols = []
        for s, lo in ((OLD, E.LON_O), (YNG, E.LON_Y)):
            g = np.where(np.isfinite(lo), lo, 0.0)
            Ql = _pillars(E, s, lonshift=g)
            Q = P[s]
            k = np.isfinite(lo).astype(float)
            cols += [k[:, None],
                     ((Ql["mb"] != Q["mb"]) * k).astype(float)[:, None],
                     ((Ql["jq"] != Q["jq"]) * k).astype(float)[:, None],
                     ((Ql["sy"] != Q["sy"]) * k).astype(float)[:, None],
                     (np.mod(g, 360.0) / 360.0 * k)[:, None],
                     E.circ(np.where(np.isfinite(lo), lo, 0.0)).reshape(n, 2) * k[:, None],
                     (np.where(np.isfinite(lo), lo, 0.0) / 15.0 * k)[:, None]]   # zone offset, hours
        cols += [known.astype(float)[:, None],
                 (np.abs(np.where(np.isfinite(E.LON_O), E.LON_O, 0.0)
                         - np.where(np.isfinite(E.LON_Y), E.LON_Y, 0.0)) / 180.0
                  * known)[:, None]]
        out["ead: saju true-solar-term boundary from birthplace"] = _stack(cols)

    # ══ 10 ── Japanese Shukuyō: the 27 mansions, almanac rule and the Moon ═════════════════════
    SK = {}
    for s, T in ((OLD, LO), (YNG, LY), (DAV, LD)):
        alm = np.mod(SHUKU_START[T["month"] - 1] + T["day"][9] - 1, 27)
        sid = E.sidereal("Lahiri")[s, E.IDX["Moon"]]
        nak = np.floor(np.mod(sid, 360.0) / (360.0 / 27.0)).astype(np.int64)
        ast = np.mod(nak - 2, 27)                       # 昴 = Krittika
        frac = np.mod(sid, 360.0) / (360.0 / 27.0) - nak
        SK[s] = (alm, ast, frac)
    cols = []
    for s in (OLD, YNG, DAV):
        alm, ast, frac = SK[s]
        cols += [_oh(alm, 27), _oh(ast, 27), frac[:, None],
                 E.circ(alm * (360.0 / 27.0)).reshape(n, 2),
                 E.circ((ast + frac) * (360.0 / 27.0)).reshape(n, 2),
                 (alm == ast).astype(float)[:, None],
                 (np.minimum(np.mod(alm - ast, 27), np.mod(ast - alm, 27)) / 13.0)[:, None],
                 _oh(alm % 9, 9), _oh(alm // 9, 3), _oh(ast % 9, 9), _oh(ast // 9, 3)]
    out["ead: shukuyo 27 mansions — almanac rule vs the moon"] = _stack(cols)

    # ══ 11 ── Shukuyō pairing: the nine relations, both directions ═════════════════════════════
    # 三九の秘法. 命 栄 衰 安 危 成 壊 友 親, the nine repeating three times round the 27, plus the
    # near/middle/far rank. Asymmetric by construction — A can be B's 栄 while B is A's 親.
    cols = []
    for tag, (aa, bb) in (("almanac", (SK[OLD][0], SK[YNG][0])),
                          ("moon", (SK[OLD][1], SK[YNG][1]))):
        d_ab = np.mod(bb - aa, 27)
        d_ba = np.mod(aa - bb, 27)
        for d in (d_ab, d_ba):
            rel = d % 9
            rank = d // 9
            cols += [_oh(rel, 9), _oh(rank, 3), _oh(rel * 3 + rank, 27),
                     SHUKU_VAL[rel][:, None], (rel == 0).astype(float)[:, None],
                     (rel == 6).astype(float)[:, None],           # 壊宿, the doctrine's worst
                     np.isin(rel, [1, 5, 7, 8]).astype(float)[:, None],
                     E.circ(d * (360.0 / 27.0)).reshape(n, 2),
                     (np.minimum(d, 27 - d) / 13.5)[:, None]]
        rel_ab, rel_ba = d_ab % 9, d_ba % 9
        cols += [(SHUKU_VAL[rel_ab] + SHUKU_VAL[rel_ba])[:, None],
                 (SHUKU_VAL[rel_ab] * SHUKU_VAL[rel_ba])[:, None],
                 np.abs(SHUKU_VAL[rel_ab] - SHUKU_VAL[rel_ba])[:, None],
                 (rel_ab == rel_ba).astype(float)[:, None],
                 _oh(rel_ab * 9 + rel_ba, 81)]
        # each partner against the DAVISON chart's mansion. The classical use of this comparison is
        # choosing a DAY, which needs a wedding date and is therefore unavailable (see docstring).
        wm = SK[DAV][0] if tag == "almanac" else SK[DAV][1]
        for own in (aa, bb):
            dw = np.mod(wm - own, 27)
            cols += [_oh(dw % 9, 9), SHUKU_VAL[dw % 9][:, None]]
    out["ead: shukuyo pairing — nine relations, both directions"] = _stack(cols)

    # ══ 12 ── Japanese day quality: 六曜, 七曜, 三隣亡 ═════════════════════════════════════════
    cols = []
    for s, T in ((OLD, LO), (YNG, LY), (DAV, LD)):
        rk = np.mod(T["month"] + T["day"][9], 6)
        wd = np.mod(T["jdn"] + 1, 7)                                # 0 = Sunday, the 七曜
        srb = np.array([11, 2, 6])[(T["month"] - 1) % 3]            # 三隣亡's forbidden day branch
        cols += [_oh(rk, 6), ROKUYO_WED[rk][:, None], (rk == 0).astype(float)[:, None],
                 (rk == 5).astype(float)[:, None],
                 _oh(wd, 7), E.circ(wd * (360.0 / 7.0)).reshape(n, 2),
                 (P[s]["db"] == srb).astype(float)[:, None],
                 E.circ(rk * 60.0).reshape(n, 2)]
    ra = np.mod(LO["month"] + LO["day"][9], 6)
    rb = np.mod(LY["month"] + LY["day"][9], 6)
    rw = np.mod(LD["month"] + LD["day"][9], 6)
    wa, wb = np.mod(LO["jdn"] + 1, 7), np.mod(LY["jdn"] + 1, 7)
    cols += [_oh(np.mod(ra - rb, 6), 6), (ra == rb).astype(float)[:, None],
             _oh(ra * 6 + rb, 36), _oh(np.mod(wa - wb, 7), 7), (wa == wb).astype(float)[:, None],
             _oh(wa * 7 + wb, 49), (ROKUYO_WED[ra] + ROKUYO_WED[rb])[:, None],
             ROKUYO_WED[rw][:, None], (rw == 0).astype(float)[:, None]]
    out["ead: japanese day quality — rokuyo, nichiyo, sanrinbo"] = _stack(cols)

    # ══ 13 ── Onmyōdō directions: 天一神, 八将神, 鬼門 ════════════════════════════════════════
    cols = []
    for s in (OLD, YNG, DAV):
        Q = P[s]
        td = TENICHI_DIR[Q["didx"]]
        cols += [_oh(td, 9), (td == 8).astype(float)[:, None],           # in the heavens = no taboo
                 _oh(DAISHOGUN[Q["yb"]], 8), _oh(BR_DIR[Q["yb"]], 8),    # 大将軍, 太歳
                 _oh(BR_DIR[np.mod(Q["yb"] + 6, 12)], 8),                # 歳破
                 np.isin(Q["yb"], [1, 2]).astype(float)[:, None],        # 鬼門 丑寅
                 np.isin(Q["yb"], [7, 8]).astype(float)[:, None],        # 裏鬼門 未申
                 np.isin(Q["db"], [1, 2]).astype(float)[:, None],
                 np.isin(Q["db"], [7, 8]).astype(float)[:, None],
                 (td == DAISHOGUN[Q["yb"]]).astype(float)[:, None],      # two taboos on one quarter
                 (td == BR_DIR[Q["yb"]]).astype(float)[:, None],
                 (td == 1).astype(float)[:, None],                       # 天一神 on the demon gate
                 E.circ(np.where(td == 8, 0.0, td * 45.0)).reshape(n, 2)]
    tdo, tdy, tdw = (TENICHI_DIR[P[s]["didx"]] for s in (OLD, YNG, DAV))
    cols += [(tdo == tdy).astype(float)[:, None], _oh(np.mod(tdo - tdy, 9), 9),
             (DAISHOGUN[O["yb"]] == DAISHOGUN[Y["yb"]]).astype(float)[:, None],
             (BR_DIR[O["yb"]] == BR_DIR[np.mod(Y["yb"] + 6, 12)]).astype(float)[:, None],
             _oh(DAISHOGUN[O["yb"]] * 8 + DAISHOGUN[Y["yb"]], 64),
             (tdw == 8).astype(float)[:, None], _oh(tdw, 9),
             ((tdw == tdo) | (tdw == tdy)).astype(float)[:, None]]
    out["ead: onmyodo directions — ten'ichijin, hasshojin, kimon"] = _stack(cols)

    # ══ 14 ── 算命学: the 人体星図, the 従星 energies and the 位相法 ════════════════════════════
    cols = []
    ENE = {}
    for s in (OLD, YNG):
        Q = P[s]
        # the five 十大主星 positions: 頭 month branch, 左手 year stem, 胸 day branch,
        # 右手 month stem (the SPOUSE position), 腹 year branch
        pos = {"head": _sipseong(Q["ds"], PRIN[Q["mb"]]),
               "lhand": _sipseong(Q["ds"], Q["ys"]),
               "chest": _sipseong(Q["ds"], PRIN[Q["db"]]),
               "rhand": _sipseong(Q["ds"], Q["ms"]),
               "belly": _sipseong(Q["ds"], PRIN[Q["yb"]])}
        for k, v in pos.items():
            cols.append(_oh(v, 10))
        # the three 十二大従星 and the ENERGY TOTAL the tradition computes
        st = [_life_stage(Q["ds"], Q[b]) for b in ("yb", "mb", "db")]
        ene = sum(JU_ENERGY[x] for x in st)
        ENE[s] = ene
        cols += [np.stack([JU_ENERGY[x] for x in st], axis=1), ene[:, None], (ene / 36.0)[:, None]]
        for x in st:
            cols.append(_oh(x, 12))
        cols += [(ene >= 30).astype(float)[:, None], (ene <= 12).astype(float)[:, None],
                 np.stack([(x == 4).astype(float) for x in st], axis=1).sum(axis=1)[:, None]]  # 天将星
        # how many of the ten stars the chart actually shows, and whether the spouse position
        # repeats another position — 算命学 reads a repeated star as a doubled trait
        allp = np.stack(list(pos.values()), axis=1)
        cols += [np.stack([(allp == g).sum(axis=1) for g in range(10)], axis=1),
                 (allp[:, 3:4] == allp).sum(axis=1)[:, None],
                 np.stack([(allp == g).any(axis=1) for g in range(10)], axis=1).sum(axis=1)[:, None]]
    cols += [(ENE[OLD] - ENE[YNG])[:, None], np.abs(ENE[OLD] - ENE[YNG])[:, None],
             (ENE[OLD] + ENE[YNG])[:, None]]
    # 位相法 at PILLAR level, which is where it differs from the branch relations upstream:
    # 律音 = an identical stem-branch shared by the two charts; 納音 sameness; the 60-cycle distance
    for ka in ("yidx", "midx", "didx"):
        for kb in ("yidx", "midx", "didx"):
            same = (O[ka] == Y[kb]).astype(float)
            cols += [same[:, None], (NAYIN[O[ka]] == NAYIN[Y[kb]]).astype(float)[:, None]]
    d60 = np.mod(O["didx"].astype(float) - Y["didx"], 60)
    cols += [E.circ(d60 * 6.0).reshape(n, 2), (np.minimum(d60, 60 - d60) / 30.0)[:, None],
             _oh(_sipseong(O["ds"], Y["ds"]) , 10) + _oh(_sipseong(Y["ds"], O["ds"]), 10)]
    out["ead: sanmeigaku jintai seizu + energy total + isoho"] = _stack(cols)

    # ══ 15 ── Mongolian Zurkhai: the жаран turned at Цагаан сар, not at Lichun ═════════════════
    cols = []
    for s, T in ((OLD, LO), (YNG, LY)):
        Q = P[s]
        an = T["lyb"]                                   # animal of the LUNAR year
        el = STEM_EL[T["lys"]]                          # Модон Гал Шороо Төмөр Ус
        rab = np.mod(T["ly"] - 1027, 60)                # position in the жаран, 1027 = fire-hare
        # NOT the cycle NUMBER: floor((year-1027)/60) is the birth year in disguise (see docstring)
        cols += [_oh(an, 12), _oh(el, 5), _oh(an * 5 + el, 60), _oh(rab, 60),
                 E.circ(rab * 6.0).reshape(n, 2),
                 (an != Q["yb"]).astype(float)[:, None],      # lunar year vs Lichun year disagree
                 (el != STEM_EL[Q["ys"]]).astype(float)[:, None],
                 _oh(T["day"][8] - 1, 30), (T["day"][8] >= 29).astype(float)[:, None],
                 (T["day"][8] == 15).astype(float)[:, None],
                 (T["day"][8] <= 3).astype(float)[:, None],   # шинийн, the bright start
                 _oh(_trine(an), 4), STEM_YANG[T["lys"]][:, None]]   # арга / билиг, yang / yin
    a, b = LO["lyb"], LY["lyb"]
    ea, eb = STEM_EL[LO["lys"]], STEM_EL[LY["lys"]]
    d12 = np.mod(a.astype(float) - b, 12)
    cols += [_oh(d12.astype(np.int64), 12), E.circ(d12 * 30.0).reshape(n, 2),
             (a == b).astype(float)[:, None],
             ((a % 4) == (b % 4)).astype(float)[:, None],                 # same triad, "мөрөөдөл"
             (np.abs(((a - b + 6) % 12) - 6) == 6).astype(float)[:, None],  # 6 apart, хөнөөл
             (ea == eb).astype(float)[:, None], _oh(ea * 5 + eb, 25),
             ((eb - ea) % 5 == 1).astype(float)[:, None], ((eb - ea) % 5 == 2).astype(float)[:, None],
             (STEM_YANG[LO["lys"]] == STEM_YANG[LY["lys"]]).astype(float)[:, None],
             ((LO["lyb"] != O["yb"]) | (LY["lyb"] != Y["yb"])).astype(float)[:, None],
             np.abs(np.mod(LO["ly"] - LY["ly"], 60) - 30)[:, None] / 30.0]
    out["ead: mongolian zurkhai jaran + tsagaan sar year boundary"] = _stack(cols)

    # ══ 16 ── Chinese almanac additions: 黃道黑道十二神, 胎元, the 28-xiu pair table ════════════
    cols = []
    for s in (OLD, YNG, DAV):
        Q = P[s]
        god = np.mod(Q["db"] - 2 * (Q["mb"] - 2), 12)     # the verse, in closed form
        te_s = np.mod(Q["ms"] + 1, 10)                    # 胎元, the conception pillar
        te_b = np.mod(Q["mb"] + 3, 12)
        cols += [_oh(god, 12), HUANG[god][:, None], E.circ(god * 30.0).reshape(n, 2),
                 _oh(te_s, 10), _oh(te_b, 12), _oh(NAYIN[_pillar_index(te_s, te_b)], 5),
                 (te_b == Q["db"]).astype(float)[:, None],
                 (np.abs(((te_b - Q["db"] + 6) % 12) - 6) == 6).astype(float)[:, None]]
    ga, gb, gw = (np.mod(P[s]["db"] - 2 * (P[s]["mb"] - 2), 12) for s in (OLD, YNG, DAV))
    cols += [(HUANG[ga] + HUANG[gb])[:, None], HUANG[gw][:, None],
             (ga == gb).astype(float)[:, None], _oh(np.mod(ga - gb, 12), 12),
             _oh(ga * 12 + gb, 144), (HUANG[ga] * HUANG[gb])[:, None],
             ((HUANG[gw] > 0) & (HUANG[ga] > 0) & (HUANG[gb] > 0)).astype(float)[:, None]]
    # the 28 xiu, equal divisions anchored on Spica at 180 deg (True Citra), PAIR relations only —
    # the identities are already upstream. The Moon is +-6 deg at noon and a xiu is 12.86 deg, so a
    # mansion label is about half reliable; these relations inherit that.
    xa, xb = (np.clip(np.floor(np.mod(E.sidereal("True Citra")[s, E.IDX["Moon"]] - 180.0, 360.0)
                               / (360.0 / 28.0)).astype(np.int64), 0, 27) for s in (OLD, YNG))
    la_, lb_ = XIU_LUM[xa], XIU_LUM[xb]
    ea_, eb_ = LUM_EL[la_], LUM_EL[lb_]
    dx = np.mod(xa - xb, 28)
    cols += [_oh(la_ * 7 + lb_, 49), _oh((xa // 7) * 4 + (xb // 7), 16),
             (ea_ == eb_).astype(float)[:, None],
             ((eb_ - ea_) % 5 == 1).astype(float)[:, None],       # A's luminary generates B's
             ((eb_ - ea_) % 5 == 2).astype(float)[:, None],       # A's overcomes B's
             ((ea_ - eb_) % 5 == 2).astype(float)[:, None],
             (dx == 14).astype(float)[:, None], (dx % 7 == 0).astype(float)[:, None],
             np.minimum(np.abs(dx - 14), 14)[:, None] / 14.0,
             _oh(np.mod(la_ - lb_, 7), 7)]
    out["ead: chinese almanac additions — 12 day gods, taiyuan, xiu pairs"] = _stack(cols)

    return out


# ── self-test ───────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import time
    from core import load
    from evalx import quick

    t0 = time.time()

    # ── doctrine checks that do not need the dataset ────────────────────────────────────────────
    # 安紫微訣 against the published 紫微 tables, one cell per 局 plus the whole 木三局 and 土五局 runs
    anchors = [(2, 1, 1), (2, 2, 2), (2, 3, 2), (3, 1, 4), (3, 2, 1), (3, 3, 2), (3, 4, 5),
               (3, 5, 2), (3, 6, 3), (4, 1, 11), (5, 1, 6), (5, 2, 11), (5, 3, 4), (5, 4, 1),
               (5, 5, 2), (6, 1, 9)]
    for cuc, day, want in anchors:
        got = int(_ziwei(np.array([day]), np.array([cuc]))[0])
        assert got == want, f"ziwei cuc={cuc} day={day}: got {got}, want {want}"
    # the whole published 紫府在寅 chart, all twelve palaces at once
    z = np.array([2])
    f = np.mod(4 - z, 12)
    place = {}
    for i, o in zip(range(6), (0, -1, -3, -4, -5, -8)):
        place.setdefault(int(np.mod(z + o, 12)[0]), []).append(STARS[i])
    for i, o in zip(range(6, 14), (0, 1, 2, 3, 4, 5, 6, 10)):
        place.setdefault(int(np.mod(f + o, 12)[0]), []).append(STARS[i])
    want = {0: ["破軍"], 1: ["天機"], 2: ["紫微", "天府"], 3: ["太陰"], 4: ["貪狼"], 5: ["巨門"],
            6: ["廉貞", "天相"], 7: ["天梁"], 8: ["七殺"], 9: ["天同"], 10: ["武曲"], 11: ["太陽"]}
    for br in range(12):
        assert sorted(place.get(br, [])) == sorted(want[br]), f"branch {br}: {place.get(br)}"
    # 五虎遁 on the life palace must give a pillar whose stem and branch agree in parity
    for ys in range(10):
        for br in range(12):
            st = (2 * ys + 2 + ((br - 2) % 12)) % 10
            assert st % 2 == br % 2, "五虎遁 produced an impossible stem-branch pair"
    # the ten gods: the classical readings of 甲 seeing 丙 庚 戊 壬 辛
    for other, want_g in ((2, "식신"), (6, "편관"), (4, "편재"), (8, "편인"), (7, "정관"),
                          (9, "정인"), (0, "비견"), (1, "겁재"), (3, "상관"), (5, "정재")):
        g = SIPSEONG[int(_sipseong(np.array([0]), np.array([other]))[0])]
        assert g == want_g, f"甲 sees stem {other}: got {g}, want {want_g}"
    # Shukuyō: the twelve month-start increments must close the ring of 27 exactly
    inc = [(SHUKU_START[(i + 1) % 12] - SHUKU_START[i]) % 27 for i in range(12)]
    assert sum(inc) == 27 and set(inc) <= {2, 3}, f"shukuyo month starts do not close: {inc}"
    assert SHUKU[22] == "室" and SHUKU[0] == "昴", "shukuyo mansion order"
    # Rokuyō fixed points: 正月一日 先勝 … 六月一日 赤口
    for m, w in ((1, "先勝"), (2, "友引"), (3, "先負"), (4, "仏滅"), (5, "大安"), (6, "赤口")):
        assert ROKUYO[(m + 1) % 6] == w, f"rokuyo month {m}: {ROKUYO[(m+1) % 6]} != {w}"
    # 天一神: every one of the nine named starting day-pillars must fall where the circuit says
    SN = "甲乙丙丁戊己庚辛壬癸"
    BN = "子丑寅卯辰巳午未申酉戌亥"
    named = {45: "己酉", 50: "甲寅", 56: "庚申", 1: "乙丑", 7: "辛未", 12: "丙子", 18: "壬午",
             23: "丁亥", 29: "癸巳"}
    for idx, nm in named.items():
        assert SN[idx % 10] + BN[idx % 12] == nm, f"sexagenary {idx} is not {nm}"
    assert sum(l for _s, l, _d in TENICHI) == 60, "ten'ichijin circuit must be 60 days"
    assert (TENICHI_DIR == 8).sum() == 16, "sixteen days in the heavens"
    for d in range(8):
        assert (TENICHI_DIR == d).sum() in (5, 6), "corners 5 days, cardinals 6"
    # 黃道黑道: the closed form must reproduce all twelve cases of the verse
    verse = {2: 0, 8: 0, 3: 2, 9: 2, 4: 4, 10: 4, 5: 6, 11: 6, 0: 8, 6: 8, 1: 10, 7: 10}
    for mb, start in verse.items():
        assert (2 * (mb - 2)) % 12 == start, f"month branch {mb}: start {start} not reproduced"
    assert HUANG.sum() == 6, "six yellow-path gods and six black"
    # 算命学 energies are a permutation of 1..12
    assert sorted(JU_ENERGY.tolist()) == list(range(1, 13)), "juusei energies"
    assert len(JU_NAME) == 12 and len(STARS) == 18 and SIHUA.shape == (10, 4)
    # the Tibetan/Mongolian rabjung epoch: 1027 CE must be FIRE-HARE on Chinese arithmetic
    assert STEM_EL[(1027 - 4) % 10] == 1 and (1027 - 4) % 12 == 3, "rabjung 1027 is not fire-hare"
    print("doctrine checks passed (ziwei tables, 紫府在寅 chart, ten gods, shukuyo ring, rokuyo, "
          "ten'ichijin, 黃黑道 verse, sanmeigaku energies, rabjung epoch)")

    E = load()
    X = build(E)

    # the calendar itself, checked against the ephemeris rather than against a table
    assert {OLD, YNG, DAV} == {0, 1, 5}, "the wedding slot and its progressions are not inputs"
    Lo = _lunar(E, OLD)
    ph = np.mod(E.LON[OLD, E.IDX["Moon"]] - E.LON[OLD, E.IDX["Sun"]], 360.0)
    age = E.JD[OLD] - Lo["t0"]
    assert (age >= 0).all() and (age < 30.6).all(), "moon age out of range"
    # the elongation implied by the new-moon time must match the ephemeris elongation
    pred = np.mod(age * 12.19, 360.0)
    bad = np.abs((pred - ph + 180) % 360 - 180) > 25
    assert bad.mean() < 0.02, f"new moon disagrees with the ephemeris phase on {bad.mean():.1%} of rows"
    assert Lo["month"].min() >= 1 and Lo["month"].max() <= 12
    for tz in (7, 8, 9):
        assert Lo["day"][tz].min() >= 1 and Lo["day"][tz].max() <= 30
    print(f"lunar calendar: months {Lo['month'].min()}-{Lo['month'].max()}, "
          f"days {Lo['day'][7].min()}-{Lo['day'][7].max()}, "
          f"leap {100*Lo['leap'].mean():.1f}% of rows, "
          f"VN/CN day differs on {100*(Lo['day'][7] != Lo['day'][8]).mean():.1f}%, "
          f"CN/JP on {100*(Lo['day'][8] != Lo['day'][9]).mean():.1f}%")

    total = 0
    for name, A in X.items():
        assert isinstance(A, np.ndarray), f"{name} is not an ndarray"
        assert A.dtype == np.float64, f"{name} dtype {A.dtype}"
        assert A.ndim == 2 and A.shape[0] == E.n, f"{name} shape {A.shape} != ({E.n}, k)"
        assert np.isfinite(A).all(), f"{name} has non-finite values"
        assert A.std(axis=0).max() > 0, f"{name} is entirely constant"
        assert name.startswith("ead: "), f"{name} is not prefixed"
        total += A.shape[1]
    print(f"\n{len(X)} blocks, {total} columns, built in {time.time()-t0:.1f}s\n")

    for name, A in X.items():
        acc, auc = quick(E, A)
        print(f"  {name:<62} {A.shape[1]:>4} cols   acc {100*acc:.2f}%   AUC {auc:.4f}")
    print("\nOK")
    sys.exit(0)
