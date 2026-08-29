"""v29_traditions.py — wave four, aimed at the families the screen said actually carry signal.

The univariate screen ranked outer cycles at 5.93x chance and composite/Davison at 3.60x, with synastry
1.81x, Tibetan 1.50x, Nine Star 1.37x and numerology 1.33x. So this file goes deeper into those and
leaves the flat families alone.

  ASPECT PATTERNS   the gestalts a chart reader names before anything else — grand trine, T-square,
                    grand cross, stellium, yod — found in the composite and Davison charts. These are
                    the classical way of saying "this chart has a SHAPE", and the bank had none of them.
  COMPOSITE D9      the navamsa of the relationship chart itself: the ninth-part reading applied to the
                    composite, which is how a Vedic astrologer would look at a union rather than a person.
  CYCLE PHASES      Rudhyar's eight-phase doctrine applied to the outer-planet PAIRS, not just the Moon:
                    a Saturn-Pluto cycle has a new, crescent, full and balsamic phase like any other, and
                    "both born in the waning square of Saturn-Pluto" is the statement a mundane
                    astrologer actually makes.
  MUTUAL RECEPTION  his planet in the sign the other's planet rules, and back again — the classical
                    courtesy between two charts, and one of the oldest synastry judgements there is.
  TIBETAN FOUR      srog, lus, dbang-thang and klung-rta — life-force, body, power and luck. These are
                    the four quantities Tibetan practice actually compares when matching a couple; the
                    bank had only the Mewa and Parkha they are built from.
  NINE STAR MONTH   the monthly star beside the yearly one, and the two-number profile.
  NUMEROLOGY        Chaldean compound numbers, universal year/month/day at each birth, the bridge
                    numbers between two life paths, and digit-shape features (repeats, palindromes,
                    runs) that the tradition reads directly off the written date.

Every statement uses BOTH dates. build(df, Z, split, exclude, min_support) -> (X, names).
"""
import numpy as np
import pandas as pd

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
TEN = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
SEVEN = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
RULES = {0: "mars", 1: "venus", 2: "mercury", 3: "moon", 4: "sun", 5: "mercury",
         6: "venus", 7: "mars", 8: "jupiter", 9: "saturn", 10: "saturn", 11: "jupiter"}
PHASE8 = ["New", "Crescent", "FirstQtr", "Gibbous", "Full", "Disseminating", "LastQtr", "Balsamic"]
CYCLE_PAIRS = [("jupiter", "saturn"), ("saturn", "uranus"), ("saturn", "neptune"), ("saturn", "pluto"),
               ("uranus", "neptune"), ("uranus", "pluto"), ("neptune", "pluto")]
# Tibetan: the four qualities derive from the year's animal and element
ANIM = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster",
        "Dog", "Pig"]
ANIM_EL = ["Water", "Earth", "Wood", "Wood", "Earth", "Fire", "Fire", "Earth", "Metal", "Metal",
           "Earth", "Water"]          # the element each animal carries (srog, the life-force)
EL5 = ["Wood", "Fire", "Earth", "Metal", "Water"]


def _dsum(n):
    s = 0
    while n:
        s += n % 10; n //= 10
    return s


def _red1(n):
    while n > 9:
        n = _dsum(n)
    return n


def _cats(vals, prefix, names, cols, ms):
    vals = np.asarray(vals)
    for v in pd.unique(vals):
        c = (vals == v).astype(np.float32)
        if c.sum() >= ms:
            cols.append(c); names.append(f"{prefix}={v}")


def _flag(cols, names, arr, nm, ms):
    c = np.nan_to_num(np.asarray(arr, dtype=float)).astype(np.float32)
    if ms <= c.sum() <= len(c) - ms:
        cols.append(c); names.append(nm)


def midlon(x, y):
    d = ((y - x + 180) % 360) - 180
    return (x + d / 2.0) % 360.0


def navamsa(lon):
    s = (lon // 30).astype(int) % 12
    part = ((lon % 30) / (30.0 / 9.0)).astype(int)
    start = np.where(s % 3 == 0, s, np.where(s % 3 == 1, (s + 8) % 12, (s + 4) % 12))
    return (start + part) % 12


def build(df, Z, split, exclude=frozenset(), min_support=40):
    n = len(df); ms = min_support
    A = Z[f"theta_a_{split}"]; B = Z[f"theta_b_{split}"]
    ya = pd.to_numeric(df.dob_a.str[:4]).to_numpy(int); ma = pd.to_numeric(df.dob_a.str[5:7]).to_numpy(int)
    da = pd.to_numeric(df.dob_a.str[8:10]).to_numpy(int)
    yb = pd.to_numeric(df.dob_b.str[:4]).to_numpy(int); mb = pd.to_numeric(df.dob_b.str[5:7]).to_numpy(int)
    db = pd.to_numeric(df.dob_b.str[8:10]).to_numpy(int)
    cols, names = [], []

    C = np.column_stack([midlon(A[:, BI[b]], B[:, BI[b]]) for b in TEN])
    CI = {b: i for i, b in enumerate(TEN)}
    MOTION = {"sun": 0.9856, "moon": 13.1764, "mercury": 1.383, "venus": 1.602, "mars": 0.524,
              "jupiter": 0.0831, "saturn": 0.0335, "uranus": 0.0117, "neptune": 0.0060, "pluto": 0.0040}
    def _jdn(y, m, d):
        a = (14 - m) // 12; yy = y + 4800 - a; mm = m + 12 * a - 3
        return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    jda = np.array([_jdn(y, m, d) for y, m, d in zip(ya, ma, da)])
    jdb = np.array([_jdn(y, m, d) for y, m, d in zip(yb, mb, db)])
    Dv = np.column_stack([(A[:, BI[b]] + MOTION[b] * (jdb - jda) / 2.0) % 360.0 for b in TEN])

    # ---------- ASPECT PATTERNS in the two relationship charts ----------
    for chart, tag in ((C, "comp"), (Dv, "dav")):
        P = chart.shape[1]
        sep = np.abs(((chart[:, :, None] - chart[:, None, :] + 180) % 360) - 180)
        tri = (np.abs(sep - 120) <= 7); sq = (np.abs(sep - 90) <= 6)
        opp = (np.abs(sep - 180) <= 8); conj = (sep <= 8); quinc = (np.abs(sep - 150) <= 3)
        sx = (np.abs(sep - 60) <= 5)
        iu = np.triu_indices(P, 1)
        # grand trine: three bodies mutually trine
        gt = np.zeros(n, bool); tsq = np.zeros(n, bool); gc = np.zeros(n, bool); yod = np.zeros(n, bool)
        for i in range(P):
            for j in range(i + 1, P):
                for k in range(j + 1, P):
                    gt |= tri[:, i, j] & tri[:, j, k] & tri[:, i, k]
                    tsq |= opp[:, i, j] & sq[:, i, k] & sq[:, j, k]
                    yod |= sx[:, i, j] & quinc[:, i, k] & quinc[:, j, k]
        for i in range(P):
            for j in range(i + 1, P):
                for k in range(P):
                    for l in range(k + 1, P):
                        if len({i, j, k, l}) == 4:
                            gc |= opp[:, i, j] & opp[:, k, l] & sq[:, i, k] & sq[:, j, l]
                            if gc.all():
                                break
        _flag(cols, names, gt, f"{tag}_grand_trine", ms)
        _flag(cols, names, tsq, f"{tag}_t_square", ms)
        _flag(cols, names, gc, f"{tag}_grand_cross", ms)
        _flag(cols, names, yod, f"{tag}_yod", ms)
        # stellium: three or more of the ten in one sign
        sg = (chart // 30).astype(int) % 12
        big = np.zeros(n, int)
        for s in range(12):
            big = np.maximum(big, (sg == s).sum(1))
        _flag(cols, names, big >= 3, f"{tag}_stellium3", ms)
        _flag(cols, names, big >= 4, f"{tag}_stellium4", ms)
        _cats(np.clip(big, 0, 6), f"{tag}_largest_sign_cluster", names, cols, ms)
        # how many aspects the chart carries at all — a loose or a tight chart
        cnt = (conj | opp | tri | sq | sx)[:, iu[0], iu[1]].sum(1)
        _cats(np.clip(cnt // 3, 0, 8), f"{tag}_aspect_density", names, cols, ms)
        # ---------- composite navamsa ----------
        for b in ("moon", "venus", "jupiter", "sun"):
            d9 = navamsa(chart[:, CI[b]])
            _cats([SIGNS[i] for i in d9], f"{tag}_d9_{b}_sign", names, cols, ms)

    # ---------- RUDHYAR PHASES OF THE OUTER-PLANET CYCLES ----------
    for x, y in CYCLE_PAIRS:
        pa = (A[:, BI[x]] - A[:, BI[y]]) % 360.0
        pb = (B[:, BI[x]] - B[:, BI[y]]) % 360.0
        fa = np.floor(pa / 45.0).astype(int) % 8
        fb = np.floor(pb / 45.0).astype(int) % 8
        ok = np.isfinite(pa) & np.isfinite(pb)
        _cats([f"{PHASE8[i]}x{PHASE8[j]}" if o else "na" for i, j, o in zip(fa, fb, ok)],
              f"cyclephase_{x}_{y}", names, cols, ms)
        _flag(cols, names, (fa == fb) & ok, f"cyclephase_{x}_{y}_same", ms)
        _flag(cols, names, (((fa - fb) % 8) == 4) & ok, f"cyclephase_{x}_{y}_opposed", ms)

    # ---------- MUTUAL RECEPTION ----------
    for p in SEVEN:
        for q in SEVEN:
            if p == q:
                continue
            sa = (A[:, BI[p]] // 30).astype(int) % 12
            sb = (B[:, BI[q]] // 30).astype(int) % 12
            ok = np.isfinite(A[:, BI[p]]) & np.isfinite(B[:, BI[q]])
            rec = np.array([RULES[i] == q and RULES[j] == p for i, j in zip(sa, sb)])
            _flag(cols, names, rec & ok, f"reception_his_{p}_her_{q}", ms)
    # the weaker one-way courtesy: his planet sits in the sign her planet rules
    for p in SEVEN:
        sa = (A[:, BI[p]] // 30).astype(int) % 12
        host = np.array([RULES[i] for i in sa])
        for q in SEVEN:
            _flag(cols, names, (host == q) & np.isfinite(A[:, BI[p]]),
                  f"his_{p}_guest_of_{q}", ms)

    # ---------- TIBETAN: srog, lus, dbang-thang, klung-rta ----------
    bra = (ya - 4) % 12; brb = (yb - 4) % 12
    srog_a = np.array([ANIM_EL[i] for i in bra]); srog_b = np.array([ANIM_EL[i] for i in brb])
    o5 = {e: i for i, e in enumerate(EL5)}
    sa_ = np.array([o5[e] for e in srog_a]); sb_ = np.array([o5[e] for e in srog_b])
    _cats([f"{a}x{b}" for a, b in zip(srog_a, srog_b)], "tib_srogpair", names, cols, ms)
    _flag(cols, names, sa_ == sb_, "tib_srog_same", ms)
    _flag(cols, names, ((sa_ + 1) % 5) == sb_, "tib_srog_he_feeds_her", ms)
    _flag(cols, names, ((sb_ + 1) % 5) == sa_, "tib_srog_she_feeds_him", ms)
    _flag(cols, names, ((sa_ + 2) % 5) == sb_, "tib_srog_he_harms_her", ms)
    _flag(cols, names, ((sb_ + 2) % 5) == sa_, "tib_srog_she_harms_him", ms)
    # lus (body), dbang-thang (power) and klung-rta (luck) step round the same wheel at other offsets
    for nm, off in (("lus", 1), ("dbangthang", 2), ("klungrta", 3)):
        la_ = (sa_ + off) % 5; lb_ = (sb_ + off) % 5
        _flag(cols, names, la_ == lb_, f"tib_{nm}_same", ms)
        _flag(cols, names, ((la_ + 2) % 5) == lb_, f"tib_{nm}_he_harms_her", ms)
        _cats([f"{EL5[i]}x{EL5[j]}" for i, j in zip(la_, lb_)], f"tib_{nm}pair", names, cols, ms)

    # ---------- NINE STAR KI: the monthly star ----------
    def nsk_year(y, m, d):
        yy = y if (m > 2 or (m == 2 and d >= 4)) else y - 1
        s = 11 - _red1(_dsum(yy))
        if s > 9:
            s -= 9
        return 9 if s == 0 else s
    def nsk_month(y, m, d):
        yy = y if (m > 2 or (m == 2 and d >= 4)) else y - 1
        mm = m - 2 if (m > 2 or (m == 2 and d >= 4)) else m + 10
        grp = nsk_year(y, m, d) % 3
        startv = {1: 8, 2: 2, 0: 5}[grp]
        v = (startv - (mm - 1)) % 9
        return 9 if v == 0 else v
    mya = np.array([nsk_month(y, m, d) for y, m, d in zip(ya, ma, da)])
    myb = np.array([nsk_month(y, m, d) for y, m, d in zip(yb, mb, db)])
    _cats([f"{i}x{j}" for i, j in zip(mya, myb)], "ninestar_monthpair", names, cols, ms)
    _flag(cols, names, mya == myb, "ninestar_month_same", ms)
    yra = np.array([nsk_year(y, m, d) for y, m, d in zip(ya, ma, da)])
    yrb = np.array([nsk_year(y, m, d) for y, m, d in zip(yb, mb, db)])
    _flag(cols, names, (yra == myb) | (yrb == mya), "ninestar_year_meets_month", ms)

    # ---------- NUMEROLOGY: compound, universal, bridge, and the shape of the digits ----------
    lpa = np.array([_red1(_red1(y) + _red1(m) + _red1(d)) for y, m, d in zip(ya, ma, da)])
    lpb = np.array([_red1(_red1(y) + _red1(m) + _red1(d)) for y, m, d in zip(yb, mb, db)])
    _cats(np.abs(lpa - lpb), "bridge_lifepath", names, cols, ms)
    bd_a = np.array([_red1(d) for d in da]); bd_b = np.array([_red1(d) for d in db])
    _cats(np.abs(bd_a - bd_b), "bridge_birthday", names, cols, ms)
    ua = np.array([_red1(_dsum(y)) for y in ya]); ub = np.array([_red1(_dsum(y)) for y in yb])
    _cats([f"{i}x{j}" for i, j in zip(ua, ub)], "universalyearpair", names, cols, ms)
    uda = np.array([_red1(_dsum(y) + m + d) for y, m, d in zip(ya, ma, da)])
    udb = np.array([_red1(_dsum(y) + m + d) for y, m, d in zip(yb, mb, db)])
    _cats([f"{i}x{j}" for i, j in zip(uda, udb)], "universaldaypair", names, cols, ms)
    comp_a = np.array([(_dsum(y) + m + d) for y, m, d in zip(ya, ma, da)])
    comp_b = np.array([(_dsum(y) + m + d) for y, m, d in zip(yb, mb, db)])
    _cats(np.clip(comp_a, 0, 52), "chaldean_compound_his", names, cols, ms)
    _cats(np.clip(comp_b, 0, 52), "chaldean_compound_her", names, cols, ms)
    _flag(cols, names, comp_a == comp_b, "chaldean_compound_same", ms)
    def shape(y, m, d):
        s = f"{y:04d}{m:02d}{d:02d}"
        rep = max(s.count(c) for c in set(s))
        pal = int(s == s[::-1])
        run = 1; best = 1
        for i in range(1, len(s)):
            run = run + 1 if int(s[i]) == int(s[i - 1]) + 1 else 1
            best = max(best, run)
        return rep, pal, best
    SA = np.array([shape(y, m, d) for y, m, d in zip(ya, ma, da)])
    SB = np.array([shape(y, m, d) for y, m, d in zip(yb, mb, db)])
    _cats([f"{a}x{b}" for a, b in zip(SA[:, 0], SB[:, 0])], "digit_repeatpair", names, cols, ms)
    _flag(cols, names, (SA[:, 1] > 0) | (SB[:, 1] > 0), "digit_palindrome_either", ms)
    _cats([f"{a}x{b}" for a, b in zip(np.clip(SA[:, 2], 0, 4), np.clip(SB[:, 2], 0, 4))],
          "digit_runpair", names, cols, ms)

    keep = [i for i, nm in enumerate(names) if nm not in exclude]
    X = np.column_stack([cols[i] for i in keep]).astype(np.float32) if keep else np.zeros((n, 0), np.float32)
    return X, [names[i] for i in keep]
