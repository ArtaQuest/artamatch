"""
v17_families.py — wave 3 of the feature exploration, unlocked by the full-precision corpus (every couple
now has a complete fast-body chart). All both-date, all named doctrine:
  - the LUMINARY CROSS tables: his Sun x her Moon and his Moon x her Sun (the classical marriage exchange),
    his Venus x her Mars / his Mars x her Venus, and the Mercury pair;
  - whole-sign DISTANCE overlays for Sun, Moon and Venus (her Sun counted from his, etc.);
  - cross ELEMENTS of the luminaries (his Sun-element x her Moon-element and the reverse);
  - the YEAR PILLAR pair (stems, Na Yin, five-element cycle) beside the existing day pillar;
  - PERSONAL-YEAR numerology: each partner's personal year in the other's birth year;
  - BIORHYTHM phase offsets (23/28/33-day cycles of the birth-date gap — the 1970s matching tradition);
  - the TITHI DISTANCE between the two birth Moon-phases;
  - Feng-shui EAST/WEST group pair (pooled Kua);
  - DRACONIC synastry: Sun and Moon referred to each person's own lunar node, paired;
  - CONTRA-ANTISCIA contacts (the equinox mirror), completing the solstice mirror already in the bank.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
import explain_gam as EG
import world_members_iv as WM

def families17(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    add = lambda M, nm: (blocks.append(np.asarray(M, np.float32)), names.extend(nm))
    oh = EG.onehot
    S144 = [f"{EG.SIGNS[i]}x{EG.SIGNS[j]}" for i in range(12) for j in range(12)]
    sg = lambda C, b: np.floor((C[:, ix[b]] % 360) / 30)

    def pair144(xa, xb, name):
        pr = np.where(np.isfinite(xa) & np.isfinite(xb), xa * 12 + xb, np.nan)
        add(*oh(pr, 144, name, S144))

    pair144(sg(A, "sun"), sg(B, "moon"), "his_sun_her_moon_pair")
    pair144(sg(A, "moon"), sg(B, "sun"), "his_moon_her_sun_pair")
    pair144(sg(A, "venus"), sg(B, "mars"), "his_venus_her_mars_pair")
    pair144(sg(A, "mars"), sg(B, "venus"), "his_mars_her_venus_pair")
    pair144(sg(A, "mercury"), sg(B, "mercury"), "mercurypair")
    for b in ("sun", "moon", "venus"):
        d1 = np.where(np.isfinite(sg(A, b)) & np.isfinite(sg(B, b)), (sg(B, b) - sg(A, b)) % 12, np.nan)
        add(*oh(d1, 12, f"her_{b}_from_his_{b}"))
    ELEM = ("Fire", "Earth", "Air", "Water")
    E16 = [f"{a}x{b}" for a in ELEM for b in ELEM]
    ea_s, eb_m = sg(A, "sun") % 4, sg(B, "moon") % 4
    ea_m, eb_s = sg(A, "moon") % 4, sg(B, "sun") % 4
    add(*oh(np.where(np.isfinite(ea_s) & np.isfinite(eb_m), ea_s * 4 + eb_m, np.nan), 16,
            "his_sunelem_her_moonelem", E16))
    add(*oh(np.where(np.isfinite(ea_m) & np.isfinite(eb_s), ea_m * 4 + eb_s, np.nan), 16,
            "his_moonelem_her_sunelem", E16))

    ya = pd.to_numeric(df.dob_a.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    yb = pd.to_numeric(df.dob_b.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    ysa = np.where(np.isfinite(ya), (ya - 4) % 10, np.nan); ysb = np.where(np.isfinite(yb), (yb - 4) % 10, np.nan)
    add(*oh(np.where(np.isfinite(ysa) & np.isfinite(ysb), ysa * 10 + ysb, np.nan), 100, "year_stempair",
            [f"{x}x{y}" for x in EG.STEMS for y in EG.STEMS]))
    NAYIN = [3,1,0,2,3,1,4,2,3,0,4,2,1,0,4,3,1,0,2,3,1,4,2,3,0,4,2,1,0,4]
    EL5 = ["Wood", "Fire", "Earth", "Metal", "Water"]
    nya = np.where(np.isfinite(ya), np.array(NAYIN)[np.nan_to_num((ya - 4) % 60 // 2 % 30).astype(int)], np.nan)
    nyb = np.where(np.isfinite(yb), np.array(NAYIN)[np.nan_to_num((yb - 4) % 60 // 2 % 30).astype(int)], np.nan)
    add(*oh(np.where(np.isfinite(nya) & np.isfinite(nyb), nya * 5 + nyb, np.nan), 25, "year_nayinpair",
            [f"{x}x{y}" for x in EL5 for y in EL5]))
    def elem_rel(x, y):
        if not (np.isfinite(x) and np.isfinite(y)):
            return np.nan
        xi, yi = int(np.array(WM.YEAR_ELEM)[int(x)]), int(np.array(WM.YEAR_ELEM)[int(y)])
        if xi == yi:
            return 0
        if (xi, yi) in WM.GEN:
            return 1
        if (yi, xi) in WM.GEN:
            return 2
        if (xi, yi) in WM.OVR:
            return 3
        return 4
    add(*oh(np.array([elem_rel(x, y) for x, y in zip(ysa, ysb)], float), 5, "year_elem_rel",
            ["Same", "HeFeedsHer", "SheFeedsHim", "HeControlsHer", "SheControlsHim"]))

    mo_a = pd.to_numeric(df.dob_a.str[5:7], errors="coerce").replace(0, np.nan).to_numpy(float)
    dd_a = pd.to_numeric(df.dob_a.str[8:10], errors="coerce").replace(0, np.nan).to_numpy(float)
    mo_b = pd.to_numeric(df.dob_b.str[5:7], errors="coerce").replace(0, np.nan).to_numpy(float)
    dd_b = pd.to_numeric(df.dob_b.str[8:10], errors="coerce").replace(0, np.nan).to_numpy(float)
    red = lambda v: np.where(np.isfinite(v), 1 + (np.nan_to_num(v) - 1) % 9, np.nan)
    def digsum(y):
        return np.array([sum(int(c) for c in str(int(v))) if np.isfinite(v) else np.nan for v in y])
    add(*oh(red(dd_a + mo_a + digsum(yb)) - 1, 9, "his_personal_year_in_hers"))
    add(*oh(red(dd_b + mo_b + digsum(ya)) - 1, 9, "her_personal_year_in_his"))

    import importlib.util
    _dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
    dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    dj = np.where(np.isfinite(ja) & np.isfinite(jb), np.abs(jb - ja), np.nan)
    add(*oh(np.where(np.isfinite(dj), np.nan_to_num(dj) % 23, np.nan), 23, "bio_physical"))
    add(*oh(np.where(np.isfinite(dj), np.nan_to_num(dj) % 28, np.nan), 28, "bio_emotional"))
    add(*oh(np.where(np.isfinite(dj), np.nan_to_num(dj) % 33, np.nan), 33, "bio_intellectual"))

    ta = np.floor(((A[:, ix["moon"]] - A[:, ix["sun"]]) % 360) / 12)
    tb = np.floor(((B[:, ix["moon"]] - B[:, ix["sun"]]) % 360) / 12)
    add(*oh(np.where(np.isfinite(ta) & np.isfinite(tb), (ta - tb) % 30, np.nan), 30, "tithi_distance"))

    def kua(y, m, d, male):
        if not (np.isfinite(y) and np.isfinite(m) and np.isfinite(d)):
            return np.nan
        yy = y - 1 if (m < 2 or (m == 2 and d < 4)) else y
        s = 1 + (sum(int(c) for c in str(int(yy))) - 1) % 9
        k = (11 - s) if male else (4 + s)
        k = 1 + (k - 1) % 9
        if k == 5:
            k = 2 if male else 8
        return k
    ka = np.array([kua(y, m, d_, True) for y, m, d_ in zip(ya, mo_a, dd_a)], float)
    kb = np.array([kua(y, m, d_, False) for y, m, d_ in zip(yb, mo_b, dd_b)], float)
    east = lambda k: np.where(np.isfinite(k), np.isin(k, [1, 3, 4, 9]).astype(float), np.nan)
    add(*oh(np.where(np.isfinite(ka) & np.isfinite(kb), east(ka) * 2 + east(kb), np.nan), 4, "eastwest_pair",
            ["WestxWest", "WestxEast", "EastxWest", "EastxEast"]))

    # DRACONIC: longitudes referred to each person's own north node
    for b in ("sun", "moon"):
        dra = np.where(np.isfinite(A[:, ix[b]]) & np.isfinite(A[:, ix["true_node"]]),
                       (A[:, ix[b]] - A[:, ix["true_node"]]) % 360, np.nan)
        drb = np.where(np.isfinite(B[:, ix[b]]) & np.isfinite(B[:, ix["true_node"]]),
                       (B[:, ix[b]] - B[:, ix["true_node"]]) % 360, np.nan)
        pair144(np.floor(dra / 30), np.floor(drb / 30), f"draconic_{b}pair")

    arc = lambda x, y: np.abs((x - y + 180.0) % 360.0 - 180.0)
    for tag, C1, C2 in (("his", A, B), ("her", B, A)):
        for b in ("sun", "moon", "venus"):
            cant = (360.0 - C1[:, ix[b]]) % 360.0
            for b2 in ("sun", "moon", "venus"):
                a = arc(cant, C2[:, ix[b2]])
                add(np.where(np.isfinite(a), (a <= 3.0).astype(np.float32), 0).reshape(-1, 1),
                    [f"{tag}_{b}_contrantiscia_other_{b2}"])
    X = np.column_stack(blocks).astype(np.float32)
    return X, names
