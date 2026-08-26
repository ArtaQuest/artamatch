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
    # ── v16 additions: the aggregate-doctrine wave (guna milan, mangal, D9, Chinese relations, overlays,
    #    harmonics) and wave 3 (luminary crosses, year pillar, personal years, biorhythms, draconic).
    #    Label conventions reproduce the training one-hots exactly.
    VASHYA_T = [1,1,2,0,1,2,2,0,1,3,3,2]
    VARNA_T = [1,2,3,0,1,2,3,0,1,2,3,0]
    LORDS_T = [4,5,2,1,0,2,5,4,3,6,6,3]
    FRIEND_T = {(0,1),(1,0),(0,3),(3,0),(0,4),(4,0),(1,2),(2,1),(5,6),(6,5),(2,5),(5,2),(3,4),(4,3)}
    GANA_T = [0,1,2,1,0,1,0,0,2,2,1,1,0,2,0,2,0,2,2,1,1,0,2,2,1,1,0]
    NADI_T = [0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2]
    YONI_T = [0,1,2,3,3,4,5,5,6,7,7,8,9,10,8,10,11,11,12,13,12,0,1,4,9,2,6]
    YONI_EN = {(0,7),(1,8),(2,9),(3,10),(4,11),(5,12),(6,13)}
    if CA["moon"] == CA["moon"] and CB["moon"] == CB["moon"]:
        na_g, nb_g = nak_i(CA["moon"]), nak_i(CB["moon"])
        ra_g, rb_g = sign_i(CA["moon"]), sign_i(CB["moon"])
        varna = 1.0 if VARNA_T[rb_g] >= VARNA_T[ra_g] else 0.0
        vd = abs(VASHYA_T[ra_g] - VASHYA_T[rb_g])
        vashya = 2.0 if vd == 0 else (1.0 if vd == 1 else 0.0)
        t1 = ((nb_g - na_g) % 27 + 1) % 9; t2 = ((na_g - nb_g) % 27 + 1) % 9
        tara = 0.0 if (t1 in (3, 5, 7) or t2 in (3, 5, 7)) else 3.0
        ya_, yb_ = YONI_T[na_g], YONI_T[nb_g]
        yoni = 4.0 if ya_ == yb_ else (0.0 if (min(ya_, yb_), max(ya_, yb_)) in YONI_EN else 2.0)
        la_, lb_ = LORDS_T[ra_g], LORDS_T[rb_g]
        maitri = 5.0 if (la_ == lb_ or (la_, lb_) in FRIEND_T) else 1.0
        gd = abs(GANA_T[na_g] - GANA_T[nb_g])
        gana = 6.0 if gd == 0 else (3.0 if gd == 1 else 0.0)
        dist = (rb_g - ra_g) % 12; dist2 = (ra_g - rb_g) % 12
        bhak = 0.0 if (dist in (5, 7, 1, 11) or dist2 in (5, 7)) else 7.0
        nadi = 0.0 if NADI_T[na_g] == NADI_T[nb_g] else 8.0
        total = varna + vashya + tara + yoni + maitri + gana + bhak + nadi
        F[f"kuta_varna={int(varna)}"] = 1.0
        F[f"kuta_vashya={int(vashya)}"] = 1.0
        F[f"kuta_tara={int(tara)}"] = 1.0
        F[f"kuta_yoni={int(yoni)}"] = 1.0
        F[f"kuta_maitri={int(maitri)}"] = 1.0
        F[f"kuta_gana={int(gana)}"] = 1.0
        F[f"kuta_bhakoot={int(bhak)}"] = 1.0
        F[f"kuta_nadi={int(nadi)}"] = 1.0
        F[f"guna_total={int(total)}"] = 1.0
        band = 0 if total < 18 else (1 if total < 25 else (2 if total < 33 else 3))
        F[f"guna_band={['under18_rejected','18to24_acceptable','25to32_good','33plus_excellent'][band]}"] = 1.0
        F[f"her_moon_from_his_moon={int((rb_g - ra_g) % 12)}"] = 1.0
    for ref in ("moon", "venus"):
        if CA[ref] == CA[ref] and CB[ref] == CB[ref] and CA["mars"] == CA["mars"] and CB["mars"] == CB["mars"]:
            ha_ = (sign_i(CA["mars"]) - sign_i(CA[ref])) % 12 + 1
            hb_ = (sign_i(CB["mars"]) - sign_i(CB[ref])) % 12 + 1
            cls = (1 if ha_ in (1, 2, 4, 7, 8, 12) else 0) * 2 + (1 if hb_ in (1, 2, 4, 7, 8, 12) else 0)
            F[f"mangal_{ref}={['neither','her_only','his_only','both'][cls]}"] = 1.0
    for b in ("moon", "venus"):
        if CA[b] == CA[b] and CB[b] == CB[b]:
            d9a = int((CA[b] % 360) // (10.0 / 3.0)) % 12; d9b = int((CB[b] % 360) // (10.0 / 3.0)) % 12
            F[f"{b}_d9pair={SIGNS[d9a]}x{SIGNS[d9b]}"] = 1.0
            h7a = int(((CA[b] * 7) % 360) // 30); h7b = int(((CB[b] * 7) % 360) // 30)
            F[f"{b}_h7pair={SIGNS[h7a]}x{SIGNS[h7b]}"] = 1.0
    SANHE = [{0, 4, 8}, {1, 5, 9}, {2, 6, 10}, {3, 7, 11}]
    LIUHE = {(0, 1), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)}
    XING = {(0, 3), (1, 10), (2, 5), (4, 4), (6, 6), (7, 7), (8, 11), (9, 9)}
    LIUHAI = {(0, 7), (1, 6), (2, 5), (3, 4), (8, 11), (9, 10)}
    PO = {(0, 9), (1, 4), (2, 11), (3, 6), (5, 8), (7, 10)}
    REL_L = ["Clash", "Punishment", "Harm", "Break", "SixHarmony", "Trine", "Same", "None"]
    def _relbr(x, y_):
        if (x - y_) % 12 == 6:
            return 0
        if (x, y_) in XING or (y_, x) in XING or (x == y_ and (x, x) in XING):
            return 1
        if (min(x, y_), max(x, y_)) in LIUHAI:
            return 2
        if (min(x, y_), max(x, y_)) in PO:
            return 3
        if (x, y_) in LIUHE or (y_, x) in LIUHE:
            return 4
        if any(x in t and y_ in t for t in SANHE):
            return 5
        if x == y_:
            return 6
        return 7
    GEN5 = {(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)}
    OVR5 = {(0, 2), (2, 4), (4, 1), (1, 3), (3, 0)}
    STEM_EL = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
    def _relel(x, y_):
        if x == y_:
            return 0
        if (x, y_) in GEN5:
            return 1
        if (y_, x) in GEN5:
            return 2
        if (x, y_) in OVR5:
            return 3
        if (y_, x) in OVR5:
            return 4
        return 5
    yba_, ybb_ = (his[0] - 4) % 12, (her[0] - 4) % 12
    F[f"year_branch_rel={REL_L[_relbr(yba_, ybb_)]}"] = 1.0
    F[f"day_branch_rel={REL_L[_relbr(sxa % 12, sxb % 12)]}"] = 1.0
    ELREL6 = ["Same", "HeFeedsHer", "SheFeedsHim", "HeControlsHer", "SheControlsHim", "None"]
    F[f"daymaster_rel={ELREL6[_relel(STEM_EL[sxa % 10], STEM_EL[sxb % 10])]}"] = 1.0
    if (min(sxa % 10, sxb % 10), max(sxa % 10, sxb % 10)) in {(0, 5), (1, 6), (2, 7), (3, 8), (4, 9)}:
        F["stem_he_combo"] = 1.0
    nyi_a = NAYIN[(sxa // 2) % 30]; nyi_b = NAYIN[(sxb // 2) % 30]
    F[f"nayin_rel={ELREL6[_relel(nyi_a, nyi_b)]}"] = 1.0
    if CA["moon"] == CA["moon"] and CB["moon"] == CB["moon"]:
        na_g, nb_g = nak_i(CA["moon"]), nak_i(CB["moon"])
        VEDHA_T = {(0,17),(1,16),(2,15),(3,14),(4,22),(5,21),(6,20),(7,19),(8,18),(9,26),(10,25),(11,24),(12,23)}
        if (min(na_g, nb_g), max(na_g, nb_g)) in VEDHA_T:
            F["vedha_pair"] = 1.0
        cnt = (na_g - nb_g) % 27 + 1
        if cnt in (4, 7, 10, 13, 16, 19, 22, 25):
            F["mahendra"] = 1.0
        if cnt > 13:
            F["stridirgha"] = 1.0
    for tag, C1, Cm in (("his", CA, CB), ("her", CB, CA)):
        if Cm["moon"] == Cm["moon"]:
            refm = sign_i(Cm["moon"])
            for b in ("sun", "venus", "mars", "jupiter"):
                if C1[b] == C1[b]:
                    F[f"{tag}_{b}_from_other_moon={int((sign_i(C1[b]) - refm) % 12)}"] = 1.0
    if CA["moon"] == CA["moon"] and CA["sun"] == CA["sun"] and CB["moon"] == CB["moon"] and CB["sun"] == CB["sun"]:
        TCL = ["Nanda", "Bhadra", "Jaya", "Rikta", "Purna"]
        ta_ = int(((CA["moon"] - CA["sun"]) % 360) // 12) % 5
        tb_ = int(((CB["moon"] - CB["sun"]) % 360) // 12) % 5
        F[f"tithiclass_pair={TCL[ta_]}x{TCL[tb_]}"] = 1.0
        F[f"tithi_distance={int((((CA['moon'] - CA['sun']) % 360) // 12 - ((CB['moon'] - CB['sun']) % 360) // 12) % 30)}"] = 1.0
    # wave 3
    if CA["sun"] == CA["sun"] and CB["moon"] == CB["moon"]:
        F[f"his_sun_her_moon_pair={SIGNS[sign_i(CA['sun'])]}x{SIGNS[sign_i(CB['moon'])]}"] = 1.0
        ELEM4 = ("Fire", "Earth", "Air", "Water")
        F[f"his_sunelem_her_moonelem={ELEM4[sign_i(CA['sun']) % 4]}x{ELEM4[sign_i(CB['moon']) % 4]}"] = 1.0
    if CA["moon"] == CA["moon"] and CB["sun"] == CB["sun"]:
        F[f"his_moon_her_sun_pair={SIGNS[sign_i(CA['moon'])]}x{SIGNS[sign_i(CB['sun'])]}"] = 1.0
        ELEM4 = ("Fire", "Earth", "Air", "Water")
        F[f"his_moonelem_her_sunelem={ELEM4[sign_i(CA['moon']) % 4]}x{ELEM4[sign_i(CB['sun']) % 4]}"] = 1.0
    if CA["venus"] == CA["venus"] and CB["mars"] == CB["mars"]:
        F[f"his_venus_her_mars_pair={SIGNS[sign_i(CA['venus'])]}x{SIGNS[sign_i(CB['mars'])]}"] = 1.0
    if CA["mars"] == CA["mars"] and CB["venus"] == CB["venus"]:
        F[f"his_mars_her_venus_pair={SIGNS[sign_i(CA['mars'])]}x{SIGNS[sign_i(CB['venus'])]}"] = 1.0
    if CA["mercury"] == CA["mercury"] and CB["mercury"] == CB["mercury"]:
        F[f"mercurypair={SIGNS[sign_i(CA['mercury'])]}x{SIGNS[sign_i(CB['mercury'])]}"] = 1.0
    for b in ("sun", "venus"):
        if CA[b] == CA[b] and CB[b] == CB[b]:
            F[f"her_{b}_from_his_{b}={int((sign_i(CB[b]) - sign_i(CA[b])) % 12)}"] = 1.0
    ysa_, ysb_ = (his[0] - 4) % 10, (her[0] - 4) % 10
    F[f"year_stempair={STEMS[ysa_]}x{STEMS[ysb_]}"] = 1.0
    EL5v = ["Wood", "Fire", "Earth", "Metal", "Water"]
    yna_ = NAYIN[((his[0] - 4) % 60) // 2 % 30]; ynb_ = NAYIN[((her[0] - 4) % 60) // 2 % 30]
    F[f"year_nayinpair={EL5v[yna_]}x{EL5v[ynb_]}"] = 1.0
    ELREL5 = ["Same", "HeFeedsHer", "SheFeedsHim", "HeControlsHer", "SheControlsHim"]
    r5 = _relel(STEM_EL[ysa_], STEM_EL[ysb_])
    if r5 < 5:
        F[f"year_elem_rel={ELREL5[r5]}"] = 1.0
    F[f"his_personal_year_in_hers={(his[2] + his[1] + sum(int(c) for c in str(her[0])) - 1) % 9}"] = 1.0
    F[f"her_personal_year_in_his={(her[2] + her[1] + sum(int(c) for c in str(his[0])) - 1) % 9}"] = 1.0
    dj_ = abs(jb - ja)
    F[f"bio_physical={dj_ % 23}"] = 1.0
    F[f"bio_emotional={dj_ % 28}"] = 1.0
    F[f"bio_intellectual={dj_ % 33}"] = 1.0
    _east = lambda k: 1 if k in (1, 3, 4, 9) else 0
    F[f"eastwest_pair={['WestxWest','WestxEast','EastxWest','EastxEast'][_east(ka_) * 2 + _east(kb_)]}"] = 1.0
    for b in ("sun", "moon"):
        if (CA[b] == CA[b] and CA["true_node"] == CA["true_node"]
                and CB[b] == CB[b] and CB["true_node"] == CB["true_node"]):
            dra = (CA[b] - CA["true_node"]) % 360; drb = (CB[b] - CB["true_node"]) % 360
            F[f"draconic_{b}pair={SIGNS[int(dra // 30)]}x{SIGNS[int(drb // 30)]}"] = 1.0
    for tag, C1, C2 in (("his", CA, CB), ("her", CB, CA)):
        for b in ("sun", "moon", "venus"):
            if C1[b] == C1[b]:
                cant = (360.0 - C1[b]) % 360.0
                for b2 in ("sun", "moon", "venus"):
                    if C2[b2] == C2[b2] and arc(cant, C2[b2]) <= 3.0:
                        F[f"{tag}_{b}_contrantiscia_other_{b2}"] = 1.0
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
