"""
ctx_nationality.py — nationality, sex and geography, so the model is nationality-aware.

NOT A TRADITION. Deliberately named ctx_ rather than trad_ so nothing here is ever reported as an
astrological result. These are the couple's recorded circumstances: where each partner held citizenship,
where they were born, and which of them is which. `run.py` picks ctx_* modules up alongside the tradition
modules, and the deep sweep can concatenate this block onto any astrology block, which is what makes a
model nationality-aware rather than nationality-blind.

WHY IT MATTERS HERE. Prominence is measured by Wikipedia sitelinks, and Wikipedia's coverage is wildly
uneven across countries and languages — a Swedish and a Brazilian family of identical standing do not
attract the same number of language editions. A model that cannot see nationality has no way to express
that, and one that can may use it either as a correction or as a signal.

WHAT IS BUILT

    citizenship        one-hot over the most common countries, for the older and younger partner
                       separately, plus counts and a "known at all" flag
    shared             whether the two share a citizenship, how many they share, and whether either is
                       unknown — the missingness is itself informative and is emitted rather than imputed
    continent          a coarser grouping, so a country seen a handful of times still contributes
    sex pair           the four combinations, and which partner is the older one
    geography          each birthplace's latitude and longitude with explicit missing flags, the
                       great-circle distance between the two birthplaces, and hemisphere flags

MISSING DATA is never quietly filled with a mean. Every field that can be absent ships an accompanying
indicator column, so a tree can split on "unknown" and a linear model can price it.

Usage: cd /Users/arash/Studio/artamatch/astro && /tmp/aqpy/bin/python ctx_nationality.py
"""

import collections
import numpy as np

TRADITION = "Context: citizenship, sex and birthplace geography (NOT astrology)"

# ISO alpha-2 to a coarse region. Only the codes that actually occur need to be right; anything unlisted
# falls into "other", which is reported rather than hidden.
# Historical states, which carry 42.4% of all citizenship mentions in this data and have no ISO code.
# Mapped by hand for the largest ones, because a dataset whose median birth year is 1900 is mostly made of
# them and "other" would be the single biggest category otherwise.
HIST = {}
for names, reg in (
    ("Ming dynasty|Tang dynasty|Song dynasty|Qing dynasty|Yuan dynasty|Han dynasty|Sui dynasty|"
     "Jin dynasty|Liao dynasty|Xin dynasty|Shu Han|Cao Wei|Eastern Wu|Empire of Japan|Joseon|Goryeo|"
     "Republic of China|Qin dynasty|Northern Song|Southern Song", "E.Asia"),
    ("Russian Empire|Soviet Union|Grand Duchy of Moscow|Tsardom of Russia|Polish-Lithuanian Commonwealth|"
     "Polish–Lithuanian Commonwealth|Czechoslovakia|Austria-Hungary|Kingdom of Hungary|Kingdom of Poland|"
     "Kingdom of Bohemia|Yugoslavia|Kingdom of Yugoslavia|Duchy of Warsaw|Kingdom of Prussia", "E.Europe"),
    ("United Kingdom of Great Britain and Ireland|Kingdom of Great Britain|Kingdom of England|"
     "Kingdom of Scotland|Kingdom of Ireland|Kingdom of France|Kingdom of Italy|Kingdom of Denmark|"
     "Kingdom of Sweden|Kingdom of Norway|Holy Roman Empire|German Empire|Weimar Republic|Nazi Germany|"
     "Kingdom of Spain|Crown of Castile|Crown of Aragon|Papal States|Republic of Venice|Ancient Rome|"
     "Roman Empire|Kingdom of Portugal|Duchy of Milan|Grand Duchy of Tuscany|Kingdom of Prussia|"
     "Dutch Republic|Kingdom of the Netherlands|Kingdom of Bavaria|Kingdom of Saxony", "W.Europe"),
    ("Ottoman Empire|Byzantine Empire|Persian Empire|Pahlavi Iran|Qajar Iran|Safavid Iran|Zand Iran|"
     "Afsharid Iran|Achaemenid Empire|Guarded Domains of Iran|Anshan Persia|Mandatory Palestine|"
     "Azerbaijan Democratic Republic|Armenian Soviet Socialist Republic", "W.Asia"),
    ("British Raj|Mughal Empire|Maratha Empire|Sikh Empire", "S.Asia"),
    ("Ancient Egypt|Ptolemaic Kingdom|Union of South Africa|Kingdom of Egypt", "Africa"),
    ("Confederate States of America|Thirteen Colonies|British America|New Spain|Viceroyalty of New Spain|"
     "Kingdom of Hawaii", "N.America"),
    ("Empire of Brazil|Gran Colombia|Viceroyalty of Peru", "S.America"),
):
    for nm in names.split("|"):
        HIST[nm.strip().lower()] = reg

REGION = {}
for codes, reg in (
    ("US CA MX GT CU DO HT JM PR CR PA SV HN NI BZ BS BB TT", "N.America"),
    ("BR AR CL CO PE VE UY EC BO PY GY SR", "S.America"),
    ("GB IE FR DE IT ES PT NL BE LU CH AT DK SE NO FI IS MT MC LI AD SM VA GI", "W.Europe"),
    ("PL CZ SK HU RO BG RS HR SI BA MK AL ME GR CY EE LV LT UA BY MD RU XK", "E.Europe"),
    ("TR IL LB SY JO IQ IR SA AE KW QA BH OM YE PS AM AZ GE", "W.Asia"),
    ("IN PK BD LK NP BT MV AF", "S.Asia"),
    ("CN JP KR KP TW HK MO MN VN TH MY SG ID PH KH LA MM BN TL", "E.Asia"),
    ("KZ UZ TM KG TJ", "C.Asia"),
    ("EG LY TN DZ MA SD ET KE NG ZA GH SN CI CM TZ UG ZW ZM MZ AO CD CG GA ML BF NE TD SO RW BI MW BW "
     "NA LS SZ MG MU SC GM GW GN SL LR TG BJ ER DJ CF ST CV KM", "Africa"),
    ("AU NZ PG FJ SB VU WS TO KI TV NR PW FM MH CK NU", "Oceania"),
):
    for c in codes.split():
        REGION[c] = reg


def _labels():
    """QID -> English label, cached by the collector. Used for the region map and for readable output."""
    import json
    import os
    for p in ("../research/data-dob/country-label.json",
              os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "../research/data-dob/country-label.json")):
        if os.path.exists(p):
            return json.load(open(p))
    return {}


def _region(q, LABEL):
    """A region for any citizenship entity, ISO-coded or historical."""
    iso = ISOOF_REV.get(q)
    if iso and iso in REGION:
        return REGION[iso]
    nm = str(LABEL.get(q, "")).strip().lower()
    if nm in HIST:
        return HIST[nm]
    return "other"


def _iso_rev():
    """Citizenship QID -> ISO alpha-2, so ISO-coded countries reach the REGION table."""
    import json
    import os
    for p in ("../research/data-dob/country-iso.json",
              os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "../research/data-dob/country-iso.json")):
        if os.path.exists(p):
            return {r[0]: r[1] for r in json.load(open(p)) if len(r) >= 2 and r[0]}
    return {}


ISOOF_REV = _iso_rev()


def build(E):
    n = E.n
    out = {}

    natO, natY = E.NAT_O, E.NAT_Y
    LABEL = _labels()
    freq = collections.Counter(q for i in range(n) for q in set(natO[i] + natY[i]))
    # 90 slots rather than 60, because the entities are now states rather than modern countries and the
    # long tail of historical polities is real: Ming dynasty is the single most common citizenship here.
    TOP = [q for q, _ in freq.most_common(90)]
    tix = {q: j for j, q in enumerate(TOP)}
    regs = sorted(set(REGION.values())) + ["other"]
    rix = {r: j for j, r in enumerate(regs)}

    # ── citizenship one-hot, each partner separately ──────────────────────────────────────────────
    A = np.zeros((n, len(TOP) + 2))
    B = np.zeros((n, len(TOP) + 2))
    for i in range(n):
        for q in natO[i]:
            if q in tix:
                A[i, tix[q]] = 1.0
        for q in natY[i]:
            if q in tix:
                B[i, tix[q]] = 1.0
        A[i, -2] = len(natO[i])                      # how many citizenships
        A[i, -1] = 1.0 if natO[i] else 0.0           # known at all
        B[i, -2] = len(natY[i])
        B[i, -1] = 1.0 if natY[i] else 0.0
    out["ctx: citizenship one-hot, older"] = A
    out["ctx: citizenship one-hot, younger"] = B
    out["ctx: citizenship one-hot, both partners"] = np.concatenate([A, B], axis=1)

    # ── sharing, and the missingness itself ───────────────────────────────────────────────────────
    sh = np.zeros((n, 6))
    for i in range(n):
        so, sy = set(natO[i]), set(natY[i])
        inter = so & sy
        sh[i] = [1.0 if inter else 0.0, len(inter), len(so | sy),
                 1.0 if (so and sy) else 0.0,
                 1.0 if (not so and not sy) else 0.0,
                 1.0 if (bool(so) != bool(sy)) else 0.0]
    out["ctx: shared citizenship + missingness"] = sh

    # ── region, which keeps rare countries useful ─────────────────────────────────────────────────
    RA = np.zeros((n, len(regs)))
    RB = np.zeros((n, len(regs)))
    for i in range(n):
        for q in natO[i]:
            RA[i, rix[_region(q, LABEL)]] = 1.0
        for q in natY[i]:
            RB[i, rix[_region(q, LABEL)]] = 1.0
    same_reg = ((RA * RB).sum(axis=1) > 0).astype(float)[:, None]
    out["ctx: region one-hot + same region"] = np.concatenate([RA, RB, same_reg], axis=1)

    # ── the pair of countries as one identity, kept low-rank ──────────────────────────────────────
    # A full 60x60 country-pair one-hot is 3,600 nearly-empty columns. The outer product of the two
    # region vectors is the same idea at a size that can actually be estimated.
    out["ctx: region pair outer product"] = np.einsum("ij,ik->ijk", RA, RB).reshape(n, -1)

    # ── sex, and which partner is older ───────────────────────────────────────────────────────────
    so, sy = E.SEX_O.astype(str), E.SEX_Y.astype(str)
    sx = np.column_stack([
        ((so == "M") & (sy == "F")).astype(float),
        ((so == "F") & (sy == "M")).astype(float),
        ((so == "M") & (sy == "M")).astype(float),
        ((so == "F") & (sy == "F")).astype(float),
        ((so == "M")).astype(float),                 # the OLDER partner is male
        ((so != "M") & (so != "F")).astype(float),   # sex unknown for the older partner
        ((sy != "M") & (sy != "F")).astype(float),
    ])
    out["ctx: sex pair"] = sx

    # ── geography, with explicit missing flags and the distance between birthplaces ───────────────
    la, lo = E.LAT_O, E.LON_O
    lb, lb2 = E.LAT_Y, E.LON_Y
    okA = np.isfinite(la) & np.isfinite(lo)
    okB = np.isfinite(lb) & np.isfinite(lb2)
    both = okA & okB
    # great-circle distance in km, 0 where unknown, with the flag saying which
    R = 6371.0
    p1, p2 = np.radians(np.nan_to_num(la)), np.radians(np.nan_to_num(lb))
    dl = np.radians(np.nan_to_num(lb2) - np.nan_to_num(lo))
    hav = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    dist = 2 * R * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))
    geo = np.column_stack([
        np.nan_to_num(la), np.nan_to_num(lo), okA.astype(float),
        np.nan_to_num(lb), np.nan_to_num(lb2), okB.astype(float),
        np.where(both, dist, 0.0), both.astype(float),
        np.where(both, np.log1p(np.where(both, dist, 0.0)), 0.0),
        (np.nan_to_num(la) >= 0).astype(float), (np.nan_to_num(lb) >= 0).astype(float),
        np.where(both, np.abs(np.nan_to_num(la) - np.nan_to_num(lb)), 0.0),
    ])
    out["ctx: birthplace geography"] = geo

    # ── PLACE OF BIRTH, the primary geography ─────────────────────────────────────────────────────
    # Preferred over citizenship: one value per person, carries coordinates, and is a fact about the birth
    # moment rather than a status that changes over a life. Every nationality bug in this project came from
    # citizenship being multi-valued and 42% historical states with no ISO code.
    pco, pcy = E.PCO_O.astype(str), E.PCO_Y.astype(str)
    cfreq = collections.Counter([q for q in pco if q] + [q for q in pcy if q])
    CTOP = [q for q, _ in cfreq.most_common(80)]
    cix = {q: j for j, q in enumerate(CTOP)}
    CA = np.zeros((n, len(CTOP) + 1))
    CB = np.zeros((n, len(CTOP) + 1))
    for i in range(n):
        if pco[i] in cix:
            CA[i, cix[pco[i]]] = 1.0
        CA[i, -1] = 1.0 if pco[i] else 0.0
        if pcy[i] in cix:
            CB[i, cix[pcy[i]]] = 1.0
        CB[i, -1] = 1.0 if pcy[i] else 0.0
    samec = ((pco == pcy) & (pco != "")).astype(float)[:, None]
    bothc = ((pco != "") & (pcy != "")).astype(float)[:, None]
    out["ctx: birth country one-hot, both"] = np.concatenate([CA, CB, samec, bothc], axis=1)

    RA2 = np.zeros((n, len(regs)))
    RB2 = np.zeros((n, len(regs)))
    for i in range(n):
        if pco[i]:
            RA2[i, rix[_region(pco[i], LABEL)]] = 1.0
        if pcy[i]:
            RB2[i, rix[_region(pcy[i], LABEL)]] = 1.0
    out["ctx: birth region + same region"] = np.concatenate(
        [RA2, RB2, ((RA2 * RB2).sum(1) > 0).astype(float)[:, None]], axis=1)

    # exact birthplace identity: same town is a much stronger statement than same country
    pobo, poby = E.POB_O.astype(str), E.POB_Y.astype(str)
    same_town = ((pobo == poby) & (pobo != "")).astype(float)
    out["ctx: same birthplace + geo resolution"] = np.column_stack([
        same_town, (pobo != "").astype(float), (poby != "").astype(float),
        E.GEORES_O, E.GEORES_Y, np.minimum(E.GEORES_O, E.GEORES_Y),
    ])

    out["ctx: EVERYTHING"] = np.concatenate(
        [A, B, sh, RA, RB, same_reg, sx, geo, CA, CB, samec, bothc, RA2, RB2,
         same_town[:, None], E.GEORES_O[:, None], E.GEORES_Y[:, None]], axis=1)
    return {k: np.ascontiguousarray(v, dtype=np.float64) for k, v in out.items()}


if __name__ == "__main__":
    import sys
    from core import load
    from evalx import quick
    E = load()
    bl = build(E)
    bad = 0
    for k, v in bl.items():
        assert v.shape[0] == E.n, f"{k}: {v.shape}"
        assert v.dtype == np.float64, f"{k}: {v.dtype}"
        assert np.isfinite(v).all(), f"{k}: not finite"
        if v.std(0).max() <= 0:
            print(f"  {k}: ALL CONSTANT")
            bad += 1
        a, u = quick(E, v)
        print(f"  {k:<44} {v.shape[1]:>5} cols   acc {100*a:6.2f}%  AUC {u:.4f}")
    print("OK" if not bad else f"{bad} constant blocks")
    sys.exit(1 if bad else 0)
