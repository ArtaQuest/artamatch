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
    aya = sw.get_ayanamsa_ut(jd)
    out = {}
    for b, c in _SW["codes"].items():
        try:
            out[b] = (sw.calc_ut(jd, c)[0][0] - aya) % 360.0
        except Exception:
            out[b] = float("nan")
    return out


def lifepath(y, m, d):
    t = sum(int(c) for c in f"{y:04d}{m:02d}{d:02d}")
    while t > 9:
        t = sum(int(c) for c in str(t))
    return t


def features(his, her):
    """(y,m,d) tuples for husband and wife -> {statement_name: 0/1}. Only names that fire are returned."""
    CA, CB = chart(*his), chart(*her)
    ja, jb = jdn(*his), jdn(*her)
    F = {}
    sgn = lambda v: SIGNS[int(v // 30) % 12]
    for tag, C in (("his", CA), ("her", CB)):
        for b in BODIES:
            v = C[b]
            if v == v:
                F[f"{tag}_{b}_sign={sgn(v)}"] = 1.0
    dt = jb - ja
    for b in ("sun","moon","venus","mars","jupiter","saturn","uranus","neptune","pluto"):
        ta, tb = CA[b], CB[b]
        if ta == ta and tb == tb:
            raw = (tb - ta + 180.0) % 360.0 - 180.0
            k = round((MEAN[b] * dt - raw) / 360.0)
            dav = (ta + (raw + 360.0 * k) / 2.0) % 360.0
            F[f"dav_{b}_sign={sgn(dav)}"] = 1.0
    for x, y_ in (("jupiter","saturn"),("saturn","uranus"),("saturn","neptune"),("saturn","pluto"),
                  ("uranus","neptune"),("uranus","pluto"),("neptune","pluto")):
        if CA[x] == CA[x] and CB[x] == CB[x] and CA[y_] == CA[y_] and CB[y_] == CB[y_]:
            ph = ((CA[x] + CB[x]) / 2 - (CA[y_] + CB[y_]) / 2) % 360.0
            F[f"cycle_{x}_{y_}_phase={sgn(ph)}"] = 1.0
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
    return F


def score(coefs, intercept, his, her):
    F = features(his, her)
    z = intercept + sum(coefs.get(k, 0.0) * v for k, v in F.items())
    contrib = sorted(((k, coefs[k]) for k in F if k in coefs and abs(coefs[k]) > 1e-6), key=lambda t: t[1])
    return 1.0 / (1.0 + np.exp(-z)), contrib
