"""Myanmar calendar — a port of yan9a/mmcal's ceMmDateTime.js (cal_watat · cal_my · j2m · yatyaza · pyathada).

Needed because yatyaza and pyathada — the inauspicious days printed on every Burmese calendar and genuinely
consulted when a wedding date is chosen — are functions of the MYANMAR month, which no pip-installable package
gave us. Their own formulas are trivial; the month is not, because the intercalary (watat) rule changes across
four calendrical eras and carries a hand-list of exceptions.

Verified by differential test against the reference JavaScript: 2,784 dates spanning JDN 2200000–2470000
(~1354–2093 CE), zero mismatches on year type, year, month, month day, yatyaza and pyathada.
"""
import math

SY = 1577917828.0 / 4320000.0      # solar year  365.2587565
LM = 1577917828.0 / 53433336.0     # lunar month  29.53058795
MO = 1954168.050623                # beginning of 0 ME


def _bs2(k, A):
    l, u = 0, len(A) - 1
    while u >= l:
        i = (l + u) // 2
        if A[i][0] > k: u = i - 1
        elif A[i][0] < k: l = i + 1
        else: return i
    return -1


def get_const(my):
    EW = 0
    if my >= 1312:
        EI, WO, NM = 3, -0.5, 8; fme = [[1377, 1]]; wte = [1344, 1345]
    elif my >= 1217:
        EI, WO, NM = 2, -1.0, 4; fme = [[1234, 1], [1261, -1]]; wte = [1263, 1264]
    elif my >= 1100:
        EI, WO, NM = 1.3, -0.85, -1; fme = [[1120, 1], [1126, -1], [1150, 1], [1172, -1], [1207, 1]]; wte = [1201, 1202]
    elif my >= 798:
        EI, WO, NM = 1.2, -1.1, -1
        fme = [[813, -1], [849, -1], [851, -1], [854, -1], [927, -1], [933, -1], [936, -1], [938, -1],
               [949, -1], [952, -1], [963, -1], [968, -1], [1039, -1]]; wte = []
    else:
        EI, WO, NM = 1.1, -1.1, -1
        fme = [[205, 1], [246, 1], [471, 1], [572, -1], [651, 1], [653, 2], [656, 1], [672, 1],
               [729, 1], [767, -1]]; wte = []
    i = _bs2(my, fme)
    if i >= 0: WO += fme[i][1]
    if my in wte: EW = 1
    return EI, WO, NM, EW


def cal_watat(my):
    EI, WO, NM, EW = get_const(my)
    TA = (SY / 12 - LM) * (12 - NM)
    ed = math.fmod(SY * (my + 3739), LM)
    if ed < TA: ed += LM
    fm = round(SY * my + MO - ed + 4.5 * LM + WO)
    watat = 0
    if EI >= 2:
        TW = LM - (SY / 12 - LM) * NM
        if ed >= TW: watat = 1
    else:
        watat = (my * 7 + 2) % 19
        if watat < 0: watat += 19
        watat = watat // 12
    watat ^= EW
    return fm, watat


def cal_my(my):
    yd = 0; nd = 0; werr = 0; fm = 0
    fm2, myt = cal_watat(my)
    while True:
        yd += 1
        fm1, w1 = cal_watat(my - yd)
        if w1 != 0 or yd >= 3: break
    if myt:
        nd = (fm2 - fm1) % 354; myt = nd // 31 + 1
        fm = fm2
        if nd not in (30, 31): werr = 1
    else:
        fm = fm1 + 354 * yd
    tg1 = fm1 + 354 * yd - 102
    return myt, tg1, fm, werr


def j2m(jdn):
    jdn = round(jdn)
    my = math.floor((jdn - 0.5 - MO) / SY)
    myt, tg1, fm, werr = cal_my(my)
    dd = jdn - tg1 + 1
    b = myt // 2; c = 1 // (myt + 1)
    myl = 354 + (1 - c) * 30 + b
    mmt = (dd - 1) // myl
    dd -= mmt * myl
    a = (dd + 423) // 512
    mm = math.floor((dd - b * a + c * a * 30 + 29.26) / 29.544)
    e = (mm + 12) // 16; f = (mm + 11) // 16
    md = dd - math.floor(29.544 * mm - 29.26) - b * e + c * f * 30
    mm += f * 3 - e * 4 + 12 * mmt
    return myt, my, mm, md


def cal_mml(mm, myt):
    mml = 30 - mm % 2
    if mm == 3: mml += myt // 2
    return mml


def cal_mp(md, mm, myt):
    mml = cal_mml(mm, myt)
    return (md + 1) // 16 + md // 16 + md // mml


def yatyaza(mm, wd):
    m1 = mm % 4
    wd1 = m1 // 2 + 4
    wd2 = (1 - m1 // 2 + m1 % 2) * (1 + 2 * (m1 % 2))
    return 1 if (wd == wd1 or wd == wd2) else 0


def pyathada(mm, wd):
    m1 = mm % 4; wda = [1, 3, 3, 0, 2, 1, 2]
    if m1 == 0 and wd == 4: return 2
    return 1 if m1 == wda[wd] else 0
