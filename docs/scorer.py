"""ArtaMatch v5 in-browser scorer. Computes the 1,293 doctrine statements BY NAME from two birth dates and
applies the frozen coefficients. Runs identically under CPython (for verification) and Pyodide (on the page).
Charts: sidereal Lahiri, 12:00 UT, matching the training pipeline."""
import numpy as np

BODIES = ["sun","moon","mercury","venus","mars","jupiter","saturn","uranus","neptune","pluto","true_node","chiron"]
MEAN = {"sun":0.9856474,"moon":13.1763966,"mercury":0.9856474,"venus":0.9856474,"mars":0.5240208,
        "jupiter":0.0830853,"saturn":0.0334442,"uranus":0.0117252,"neptune":0.0059800,"pluto":0.0039717,
        "true_node":-0.0529539,"chiron":0.0197354,"mean_lilith":0.1114041}
SIGNS = ["Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"]
STEMS = ["JiaWood","YiWood","BingFire","DingFire","WuEarth","JiEarth","GengMetal","XinMetal","RenWater","GuiWater"]
BRANCH = ["Rat","Ox","Tiger","Rabbit","Dragon","Snake","Horse","Goat","Monkey","Rooster","Dog","Pig"]
_SW = {}


def init(sw):
    """sw = a loaded sweshim module (set to Lahiri by caller)."""
    _SW["sw"] = sw
    _SW["codes"] = {"sun": sw.SUN, "moon": sw.MOON, "mercury": sw.MERCURY, "venus": sw.VENUS, "mars": sw.MARS,
                    "jupiter": sw.JUPITER, "saturn": sw.SATURN, "uranus": sw.URANUS, "neptune": sw.NEPTUNE,
                    "pluto": sw.PLUTO, "true_node": sw.TRUE_NODE, "chiron": sw.CHIRON}


def jdn(y, m, d):
    a = (14 - m) // 12; yy = y + 4800 - a; mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def chart(y, m, d):
    sw = _SW["sw"]
    jd = sw.julday(y, m, d, 12.0)
    out = {}
    try:
        aya = sw.get_ayanamsa_ut(jd)
    except Exception:
        aya = float("nan")
    for b, c in _SW["codes"].items():
        try:
            xx, _flag = sw.calc_ut(jd, c)
            out[b] = (xx[0] - aya) % 360.0
            out[f"__speed_{b}"] = xx[3]
        except Exception:
            out[b] = float("nan")
            out[f"__speed_{b}"] = float("nan")
    return out


def lifepath(y, m, d):
    t = sum(int(c) for c in f"{y:04d}{m:02d}{d:02d}")
    while t > 9:
        t = sum(int(c) for c in str(t))
    return t


def features(his, her, CA=None, CB=None):
    """(y,m,d) tuples for husband and wife -> {statement_name: 0/1}. Only names that fire are returned.
    CA/CB may inject precomputed charts (verification); normally they come from the shipped ephemeris."""
    if CA is None:
        CA = chart(*his)
    if CB is None:
        CB = chart(*her)
    ja, jb = jdn(*his), jdn(*her)
    F = {}
    sgn = lambda v: SIGNS[int(v // 30) % 12]
    for tag, C in (("his", CA), ("her", CB)):
        for b in BODIES:
            v = C[b]
            if v == v:
                F[f"{tag}_{b}_sign={sgn(v)}"] = 1.0
    dt = jb - ja
    davpos = {}
    for b in ("sun","moon","venus","mars","jupiter","saturn","uranus","neptune","pluto"):
        ta, tb = CA[b], CB[b]
        if ta == ta and tb == tb:
            raw = (tb - ta + 180.0) % 360.0 - 180.0
            k = round((MEAN[b] * dt - raw) / 360.0)
            dav = (ta + (raw + 360.0 * k) / 2.0) % 360.0
            davpos[b] = dav
            F[f"dav_{b}_sign={sgn(dav)}"] = 1.0
            F[f"dav_{b}_decan={int(dav // 10)}"] = 1.0
    for x, y_ in (("jupiter","saturn"),("saturn","uranus"),("saturn","neptune"),("saturn","pluto"),
                  ("uranus","neptune"),("uranus","pluto"),("neptune","pluto")):
        if CA[x] == CA[x] and CB[x] == CB[x] and CA[y_] == CA[y_] and CB[y_] == CB[y_]:
            ph = ((CA[x] + CB[x]) / 2 - (CA[y_] + CB[y_]) / 2) % 360.0
            F[f"cycle_{x}_{y_}_phase={sgn(ph)}"] = 1.0
            F[f"cycle36_{x}_{y_}={int(ph // 10)}"] = 1.0
    if CA["sun"] == CA["sun"] and CB["sun"] == CB["sun"]:
        F[f"sunpair={sgn(CA['sun'])}x{sgn(CB['sun'])}"] = 1.0
    if CA["moon"] == CA["moon"] and CB["moon"] == CB["moon"]:
        F[f"moonpair={sgn(CA['moon'])}x{sgn(CB['moon'])}"] = 1.0
    NAK = 360.0 / 27.0
    for tag, C in (("his", CA), ("her", CB)):
        if C["moon"] == C["moon"]:
            F[f"{tag}_nakshatra={int((C['moon'] % 360) // NAK)}"] = 1.0
        if C["moon"] == C["moon"] and C["sun"] == C["sun"]:
            el = (C["moon"] - C["sun"]) % 360.0
            F[f"{tag}_tithi={int(el // 12.0)}"] = 1.0
    arc = lambda x, y_: abs((x - y_ + 180.0) % 360.0 - 180.0)
    CONTACTS = [("sun","moon"),("moon","sun"),("venus","mars"),("mars","venus"),("sun","sun"),("moon","moon"),
                ("venus","venus"),("moon","venus"),("venus","moon"),("saturn","moon"),("moon","saturn"),
                ("saturn","venus"),("venus","saturn"),("mars","moon"),("jupiter","moon"),("jupiter","venus"),
                ("sun","saturn"),("saturn","sun"),("mars","mars"),("saturn","saturn")]
    for x, y_ in CONTACTS:
        if CA[x] == CA[x] and CB[y_] == CB[y_]:
            a = arc(CA[x], CB[y_])
            for t, o, lab in ((0, 8, "conj"), (60, 4, "sext"), (90, 6, "square"), (120, 6, "trine"), (180, 8, "opp")):
                if abs(a - t) <= o:
                    F[f"his_{x}_{lab}_her_{y_}"] = 1.0
    TENG = ("sun","moon","mercury","venus","mars","jupiter","saturn","uranus","neptune","pluto")
    for x in TENG:
        for y_ in TENG:
            if CA[x] == CA[x] and CB[y_] == CB[y_]:
                a = arc(CA[x], CB[y_])
                for t, o, lab in ((0, 8, "conj"), (60, 4, "sext"), (90, 6, "square"), (120, 6, "trine"),
                                  (180, 8, "opp"), (150, 3, "quinc"), (30, 3, "semisext")):
                    if abs(a - t) <= o:
                        F[f"his_{x}_{lab}_her_{y_}"] = 1.0
    for tag, j in (("his", ja), ("her", jb)):
        sx = (j + 49) % 60
        F[f"{tag}_daystem={STEMS[sx % 10]}"] = 1.0
        F[f"{tag}_daybranch={BRANCH[sx % 12]}"] = 1.0
    ya, yb = his[0], her[0]
    F[f"his_year_animal={BRANCH[(ya - 4) % 12]}"] = 1.0
    F[f"her_year_animal={BRANCH[(yb - 4) % 12]}"] = 1.0
    F[f"animalpair={BRANCH[(ya - 4) % 12]}x{BRANCH[(yb - 4) % 12]}"] = 1.0
    la, lb = lifepath(*his), lifepath(*her)
    F[f"his_lifepath={la}"] = 1.0
    F[f"her_lifepath={lb}"] = 1.0
    F[f"lifepath_pair={la}x{lb}"] = 1.0
    # ── v6 additions: the finer doctrine grains and the pair matrices the sparse model draws on
    for tag, C in (("his", CA), ("her", CB)):
        for b in ("sun", "moon"):
            if C[b] == C[b]:
                F[f"{tag}_{b}_decan={int((C[b] % 360) // 10)}"] = 1.0
        if C["moon"] == C["moon"]:
            F[f"{tag}_moon_pada={int((C['moon'] % 360) // (360.0 / 108.0))}"] = 1.0
    for x, y_ in (("neptune", "pluto"), ("uranus", "neptune"), ("uranus", "pluto"), ("saturn", "pluto")):
        if CA[x] == CA[x] and CB[x] == CB[x] and CA[y_] == CA[y_] and CB[y_] == CB[y_]:
            ph = ((CA[x] + CB[x]) / 2 - (CA[y_] + CB[y_]) / 2) % 360.0
            F[f"cycle24_{x}_{y_}={int(ph // 15)}"] = 1.0
    if CA["moon"] == CA["moon"] and CB["moon"] == CB["moon"]:
        ta, tb = CA["moon"], CB["moon"]
        raw = (tb - ta + 180.0) % 360.0 - 180.0
        k = round((MEAN["moon"] * dt - raw) / 360.0)
        davm = (ta + (raw + 360.0 * k) / 2.0) % 360.0
        F[f"dav_moon_nakshatra={int(davm // (360.0 / 27.0))}"] = 1.0
        NAKW = 360.0 / 27.0
        F[f"nakpair={int((ta % 360) // NAKW)}x{int((tb % 360) // NAKW)}"] = 1.0
    sxa, sxb = (ja + 49) % 60, (jb + 49) % 60
    F[f"branchpair={BRANCH[sxa % 12]}x{BRANCH[sxb % 12]}"] = 1.0
    F[f"stempair={STEMS[sxa % 10]}x{STEMS[sxb % 10]}"] = 1.0
    # ── v10 additions: the full doctrine families the conjunction model draws on. Label conventions
    #    reproduce the training one-hots exactly (e.g. birthday=14 means the 15th; attitude/vara/karana
    #    and the pair tables use the training index, not the human number).
    YONI = [0,1,2,3,3,4,5,5,6,7,7,8,9,10,8,10,11,11,12,13,12,0,1,4,9,2,6]
    VARNA = [1,2,3,0,1,2,3,0,1,2,3,0]
    VASHYA = [1,1,2,0,1,2,2,0,1,3,3,2]
    NAYIN = [3,1,0,2,3,1,4,2,3,0,4,2,1,0,4,3,1,0,2,3,1,4,2,3,0,4,2,1,0,4]
    EL5 = ["Wood","Fire","Earth","Metal","Water"]
    sign_i = lambda v: int((v % 360) // 30)
    nak_i = lambda v: int((v % 360) // NAK)
    if CA["moon"] == CA["moon"] and CB["moon"] == CB["moon"]:
        na_, nb_ = nak_i(CA["moon"]), nak_i(CB["moon"])
        F[f"yonipair={YONI[na_]}x{YONI[nb_]}"] = 1.0
        NADI = [0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2]
        GANA = [0,1,2,1,0,1,0,0,2,2,1,1,0,2,0,2,0,2,2,1,1,0,2,2,1,1,0]
        RAJJU = [0,1,2,3,4,3,2,1,0,0,1,2,3,4,3,2,1,0,0,1,2,3,4,3,2,1,0]
        NADI_L = ["Adi", "Madhya", "Antya"]; GANA_L = ["Deva", "Manushya", "Rakshasa"]
        F[f"nadipair={NADI_L[NADI[na_]]}x{NADI_L[NADI[nb_]]}"] = 1.0
        F[f"ganapair={GANA_L[GANA[na_]]}x{GANA_L[GANA[nb_]]}"] = 1.0
        F[f"rajjupair={RAJJU[na_]}x{RAJJU[nb_]}"] = 1.0
        F[f"dashalordpair={(na_ % 9) * 9 + (nb_ % 9)}"] = 1.0
        t1 = int(((na_ - nb_) % 27 + 1) % 9); t2 = int(((nb_ - na_) % 27 + 1) % 9)
        F[f"tarapair={t1 * 9 + t2}"] = 1.0
        ra_, rb_ = sign_i(CA["moon"]), sign_i(CB["moon"])
        F[f"varnapair={VARNA[ra_]}x{VARNA[rb_]}"] = 1.0
        F[f"vashyapair={VASHYA[ra_]}x{VASHYA[rb_]}"] = 1.0
    for b in ("venus", "mars"):
        if CA[b] == CA[b] and CB[b] == CB[b]:
            F[f"{b}pair={SIGNS[sign_i(CA[b])]}x{SIGNS[sign_i(CB[b])]}"] = 1.0
    ELEM = ("Fire", "Earth", "Air", "Water"); MODE = ("Cardinal", "Fixed", "Mutable")
    for b in ("sun", "moon", "venus"):
        if CA[b] == CA[b] and CB[b] == CB[b]:
            sa_, sb_ = sign_i(CA[b]), sign_i(CB[b])
            F[f"{b}_elempair={ELEM[sa_ % 4]}x{ELEM[sb_ % 4]}"] = 1.0
            F[f"{b}_modepair={MODE[sa_ % 3]}x{MODE[sb_ % 3]}"] = 1.0
            F[f"{b}_polpair={['Yang','Yin'][sa_ % 2]}x{['Yang','Yin'][sb_ % 2]}"] = 1.0
    comp = {}
    for b in ("sun","moon","venus","mars","jupiter","saturn","uranus","neptune","pluto"):
        if CA[b] == CA[b] and CB[b] == CB[b]:
            comp[b] = (CA[b] + ((CB[b] - CA[b] + 180.0) % 360.0 - 180.0) / 2.0) % 360.0
            F[f"comp_{b}_sign={SIGNS[sign_i(comp[b])]}"] = 1.0
            F[f"comp_{b}_decan={int(comp[b] // 10)}"] = 1.0
    if "sun" in comp and "moon" in comp:
        F[f"comp_tithi={int(((comp['moon'] - comp['sun']) % 360.0) // 12.0)}"] = 1.0
        F[f"comp_moon_nakshatra={int((comp['moon'] % 360) // NAK)}"] = 1.0
    if "sun" in davpos and "moon" in davpos:
        F[f"dav_tithi={int(((davpos['moon'] - davpos['sun']) % 360.0) // 12.0)}"] = 1.0
    for x, y_ in (("sun","moon"),("venus","saturn"),("venus","mars"),("moon","saturn"),("sun","saturn")):
        if x in comp and y_ in comp:
            a = arc(comp[x], comp[y_])
            for t, o, lab in ((0, 8, "conj"), (90, 6, "square"), (180, 8, "opp"), (120, 6, "trine")):
                if abs(a - t) <= o:
                    F[f"comp_{x}_{lab}_{y_}"] = 1.0
    for tag, C1, C2 in (("his", CA, CB), ("her", CB, CA)):
        if C1["sun"] == C1["sun"] and C1["moon"] == C1["moon"]:
            sm = (C1["sun"] + ((C1["moon"] - C1["sun"] + 180.0) % 360.0 - 180.0) / 2.0) % 360.0
            for b in ("sun", "moon", "venus"):
                if C2[b] == C2[b] and arc(sm, C2[b]) <= 3.0:
                    F[f"{tag}_sunmoon_mid_conj_other_{b}"] = 1.0
        for b in ("sun", "moon", "venus"):
            if C1[b] == C1[b]:
                ant = (180.0 - C1[b]) % 360.0
                for b2 in ("sun", "moon", "venus"):
                    if C2[b2] == C2[b2] and arc(ant, C2[b2]) <= 3.0:
                        F[f"{tag}_{b}_antiscia_other_{b2}"] = 1.0
    for tag, C in (("his", CA), ("her", CB)):
        for b in ("mercury", "venus", "mars", "moon"):
            if C[b] == C[b] and C["sun"] == C["sun"] and arc(C[b], C["sun"]) <= 8.5:
                F[f"{tag}_{b}_combust"] = 1.0
        for b in ("mercury", "venus", "mars", "jupiter", "saturn"):
            sp = C.get(f"__speed_{b}", float("nan"))
            if sp == sp and sp < 0:
                F[f"{tag}_{b}_retro"] = 1.0
        if C["moon"] == C["moon"] and C["sun"] == C["sun"]:
            el = (C["moon"] - C["sun"]) % 360.0
            kidx = int(el // 6.0)
            kt = 0 if kidx == 0 else (8 + (kidx - 57) if kidx >= 57 else (kidx - 1) % 7 + 1)
            F[f"{tag}_karana={kt}"] = 1.0
            F[f"{tag}_nityayoga={int(((C['moon'] + C['sun']) % 360.0) // NAK)}"] = 1.0
    wa, wb = ja % 7, jb % 7
    F[f"his_vara={wa}"] = 1.0
    F[f"her_vara={wb}"] = 1.0
    F[f"varapair={wa * 7 + wb}"] = 1.0
    for tag, (y_, m_, d_) in (("his", his), ("her", her)):
        F[f"{tag}_birthday={d_ - 1}"] = 1.0
        F[f"{tag}_attitude={(d_ + m_ - 1) % 9}"] = 1.0
        if d_ in (13, 14, 16, 19):
            F[f"{tag}_karmic_debt_day"] = 1.0
        if d_ in (11, 22):
            F[f"{tag}_master_day"] = 1.0
    gap = abs(his[0] - her[0])
    if gap <= 15:
        F[f"gap_years={gap}"] = 1.0
    if gap in (3, 6, 9):
        F["gap_369_taboo"] = 1.0
    if (his[1], his[2]) == (her[1], her[2]):
        F["same_birthday"] = 1.0
    if his[1] == her[1]:
        F["same_birth_month"] = 1.0
    def _digsum9(yy):
        return 1 + (sum(int(c) for c in str(int(yy))) - 1) % 9
    def _kua(y_, m_, d_, male):
        yy = y_ - 1 if (m_ < 2 or (m_ == 2 and d_ < 4)) else y_
        ds = _digsum9(yy)
        k = (11 - ds) if male else (4 + ds)
        k = 1 + (k - 1) % 9
        if k == 5:
            k = 2 if male else 8
        return int(k)
    ka_, kb_ = _kua(*his, True), _kua(*her, False)
    F[f"kuapair={(ka_ - 1) * 9 + (kb_ - 1)}"] = 1.0
    n9 = lambda y_: 1 + (11 - _digsum9(y_) - 1) % 9
    F[f"ninestarpair={(n9(his[0]) - 1) * 9 + (n9(her[0]) - 1)}"] = 1.0
    for tag, (y_, m_, d_), j in (("his", his, ja), ("her", her, jb)):
        mb_ = (m_ if d_ >= 5 else m_ - 1) % 12
        F[f"{tag}_monthbranch={BRANCH[mb_]}"] = 1.0
        sx_ = (j + 49) % 60
        F[f"{tag}_stem_season={STEMS[sx_ % 10]}x{BRANCH[mb_]}"] = 1.0
        F[f"{tag}_nayin={EL5[NAYIN[(sx_ // 2) % 30]]}"] = 1.0
    F[f"nayinpair={EL5[NAYIN[((ja + 49) % 60 // 2) % 30]]}x{EL5[NAYIN[((jb + 49) % 60 // 2) % 30]]}"] = 1.0
    for tag, Cm, Cs in (("his_moon_her_saturn", CA, CB), ("her_moon_his_saturn", CB, CA)):
        if Cm["moon"] == Cm["moon"] and Cs["saturn"] == Cs["saturn"]:
            h = (sign_i(Cs["saturn"]) - sign_i(Cm["moon"])) % 12 + 1
            F[f"{tag}_house={h - 1}"] = 1.0
            if h in (12, 1, 2):
                F[f"{tag}_sadesati"] = 1.0
    KAR = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
    for tag, C in (("his", CA), ("her", CB)):
        degs = [C[b] % 30.0 if C[b] == C[b] else float("nan") for b in KAR]
        if all(d_ == d_ for d_ in degs):
            ak_ = max(range(7), key=lambda i: degs[i])
            dk_ = min(range(7), key=lambda i: degs[i])
            F[f"{tag}_atmakaraka={KAR[ak_]}"] = 1.0
            F[f"{tag}_darakaraka={KAR[dk_]}"] = 1.0
            F[f"{tag}_darakaraka_sign={SIGNS[sign_i(C[KAR[dk_]])]}"] = 1.0
    return F


def score_rules(weights, intercept, his, her):
    """v10: a rule may be a conjunction — "A AND B [AND C]" fires only when every clause fires."""
    F = features(his, her)
    fired = [(name, w) for name, w in weights.items()
             if all(p in F for p in name.split(" AND "))]
    fired.sort(key=lambda t: -t[1])
    return intercept + sum(w for _, w in fired), fired


def score_v6(weights, intercept, his, her):
    """The non-negative sparse model: a couple's score is the intercept plus the risk rules they trip."""
    F = features(his, her)
    fired = sorted(((k, weights[k]) for k in F if k in weights), key=lambda t: -t[1])
    return intercept + sum(w for _, w in fired), fired


def score(coefs, intercept, his, her):
    F = features(his, her)
    z = intercept + sum(coefs.get(k, 0.0) * v for k, v in F.items())
    contrib = sorted(((k, coefs[k]) for k in F if k in coefs and abs(coefs[k]) > 1e-6), key=lambda t: t[1])
    return 1.0 / (1.0 + np.exp(-z)), contrib
