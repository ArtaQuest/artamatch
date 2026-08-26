"""
v15_families.py — the aggregate-doctrine wave (corpus v2). v13 atomised the traditions into their finest
cells; this wave adds the traditions' own AGGREGATES and the great pair rules still missing, every one a
function of BOTH dates:
  - the Ashtakoota GUNA MILAN itself: each kuta's score and the famous 36-point total with its verdict
    bands (reusing the validated tables in world_members_iv);
  - MANGAL (Kuja) dosha as a PAIR: Mars in 1/2/4/7/8/12 from the Moon, matched or unmatched;
  - the NAVAMSA (D9) pair tables for Moon and Venus — the marriage divisional chart;
  - Chinese branch RELATION CLASSES (six harmonies, trines, clashes, harms, punishments, breaks) for the
    year and day pillars, the five-element cycle between the day masters, the five stem combinations;
  - VEDHA obstruction pairs, MAHENDRA and STRIDIRGHA counts from her star to his;
  - house-from-Moon OVERLAYS: his Sun/Venus/Mars/Jupiter counted from her Moon sign and vice versa;
  - the 7th-HARMONIC (Addey) sign pair for Venus and Moon; the tithi-class (Nanda..Purna) pair.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
import explain_gam as EG
import world_members_iv as WM

LIUCHONG = {(i, (i + 6) % 12) for i in range(12)}
LIUHAI = {(0, 7), (1, 6), (2, 5), (3, 4), (8, 11), (9, 10)}
PO = {(0, 9), (1, 4), (2, 11), (3, 6), (5, 8), (7, 10)}
HE5 = {(0, 5), (1, 6), (2, 7), (3, 8), (4, 9)}            # stem combinations Jia-Ji … Wu-Gui
VEDHA = {(0, 17), (1, 16), (2, 15), (3, 14), (4, 22), (5, 21), (6, 20), (7, 19), (8, 18),
         (9, 26), (10, 25), (11, 24), (12, 23)}           # the classical obstruction pairs

def _rel_branch(x, y):
    """8-class Chinese branch relation, precedence clash > punish > harm > break > harmony > trine > same."""
    p = (min(x, y), max(x, y))
    if p in LIUCHONG or (y, x) in LIUCHONG or (x, y) in LIUCHONG:
        return 0
    if (x, y) in WM.XING or (y, x) in WM.XING or (x == y and (x, x) in WM.XING):
        return 1
    if p in LIUHAI:
        return 2
    if p in PO:
        return 3
    if p in WM.LIUHE or (y, x) in WM.LIUHE:
        return 4
    if any(x in t and y in t for t in WM.SANHE):
        return 5
    if x == y:
        return 6
    return 7

REL_L = ["Clash", "Punishment", "Harm", "Break", "SixHarmony", "Trine", "Same", "None"]
ELREL_L = ["Same", "HeFeedsHer", "SheFeedsHim", "HeControlsHer", "SheControlsHim", "None"]

def _rel_elem(x, y):
    if x == y:
        return 0
    if (x, y) in WM.GEN:
        return 1
    if (y, x) in WM.GEN:
        return 2
    if (x, y) in WM.OVR:
        return 3
    if (y, x) in WM.OVR:
        return 4
    return 5

def families15(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    add = lambda M, nm: (blocks.append(np.asarray(M, np.float32)), names.extend(nm))
    oh = EG.onehot
    NAK = 360.0 / 27.0
    ma, mb = A[:, ix["moon"]], B[:, ix["moon"]]
    na = np.floor((ma % 360) / NAK); nb = np.floor((mb % 360) / NAK)
    ra = np.floor((ma % 360) / 30); rb = np.floor((mb % 360) / 30)

    # ── GUNA MILAN: the tradition's own aggregate, straight from the validated scorer
    K = WM.ashtakoota(na, ra, nb, rb)
    add(*oh(K[:, 0], 2, "kuta_varna"))
    add(*oh(K[:, 1], 3, "kuta_vashya"))
    add(*oh(K[:, 2] / 3, 2, "kuta_tara", ["0", "3"]))
    add(*oh(K[:, 3] / 2, 3, "kuta_yoni", ["0", "2", "4"]))
    add(*oh(np.where(np.isfinite(K[:, 4]), (K[:, 4] == 5).astype(float), np.nan), 2, "kuta_maitri", ["1", "5"]))
    add(*oh(K[:, 5] / 3, 3, "kuta_gana", ["0", "3", "6"]))
    add(*oh(K[:, 6] / 7, 2, "kuta_bhakoot", ["0", "7"]))
    add(*oh(K[:, 7] / 8, 2, "kuta_nadi", ["0", "8"]))
    add(*oh(K[:, 8], 37, "guna_total"))
    band = np.where(np.isfinite(K[:, 8]),
                    np.digitize(np.nan_to_num(K[:, 8]), [18, 25, 33]), np.nan)
    add(*oh(band, 4, "guna_band", ["under18_rejected", "18to24_acceptable", "25to32_good", "33plus_excellent"]))

    # ── MANGAL DOSHA as a pair (Mars from the Moon, whole-sign houses 1,2,4,7,8,12)
    for ref in ("moon", "venus"):
        rfa = np.floor((A[:, ix[ref]] % 360) / 30); rfb = np.floor((B[:, ix[ref]] % 360) / 30)
        msa = np.floor((A[:, ix["mars"]] % 360) / 30); msb = np.floor((B[:, ix["mars"]] % 360) / 30)
        ha = (msa - rfa) % 12 + 1; hb = (msb - rfb) % 12 + 1
        man_a = np.isin(ha, [1, 2, 4, 7, 8, 12]); man_b = np.isin(hb, [1, 2, 4, 7, 8, 12])
        okm = np.isfinite(ha) & np.isfinite(hb)
        cls = np.where(okm, man_a.astype(int) * 2 + man_b.astype(int), np.nan)
        add(*oh(cls, 4, f"mangal_{ref}", ["neither", "her_only", "his_only", "both"]))

    # ── NAVAMSA (D9) sign pairs for Moon and Venus
    for b in ("moon", "venus"):
        d9a = np.floor((A[:, ix[b]] % 360) / (10.0 / 3.0)) % 12
        d9b = np.floor((B[:, ix[b]] % 360) / (10.0 / 3.0)) % 12
        pr = np.where(np.isfinite(d9a) & np.isfinite(d9b), d9a * 12 + d9b, np.nan)
        add(*oh(pr, 144, f"{b}_d9pair", [f"{EG.SIGNS[i]}x{EG.SIGNS[j]}" for i in range(12) for j in range(12)]))

    # ── CHINESE relations: year and day branches, day-master element cycle, stem combinations, Na Yin cycle
    import importlib.util
    _dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
    dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    ya = pd.to_numeric(df.dob_a.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    yb = pd.to_numeric(df.dob_b.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    yba = (ya - 4) % 12; ybb = (yb - 4) % 12
    rel_y = np.where(np.isfinite(yba) & np.isfinite(ybb),
                     [_rel_branch(int(x), int(y)) if np.isfinite(x) and np.isfinite(y) else 0
                      for x, y in zip(yba, ybb)], np.nan)
    add(*oh(rel_y, 8, "year_branch_rel", REL_L))
    sxa = np.where(np.isfinite(ja), (np.nan_to_num(ja) + 49) % 60, np.nan)
    sxb = np.where(np.isfinite(jb), (np.nan_to_num(jb) + 49) % 60, np.nan)
    dba = sxa % 12; dbb = sxb % 12
    rel_d = np.where(np.isfinite(dba) & np.isfinite(dbb),
                     [_rel_branch(int(x), int(y)) if np.isfinite(x) and np.isfinite(y) else 0
                      for x, y in zip(dba, dbb)], np.nan)
    add(*oh(rel_d, 8, "day_branch_rel", REL_L))
    ea = np.where(np.isfinite(sxa), np.array(WM.YEAR_ELEM)[np.nan_to_num(sxa).astype(int) % 10], np.nan)
    eb = np.where(np.isfinite(sxb), np.array(WM.YEAR_ELEM)[np.nan_to_num(sxb).astype(int) % 10], np.nan)
    rel_e = np.where(np.isfinite(ea) & np.isfinite(eb),
                     [_rel_elem(int(x), int(y)) if np.isfinite(x) and np.isfinite(y) else 5
                      for x, y in zip(ea, eb)], np.nan)
    add(*oh(rel_e, 6, "daymaster_rel", ELREL_L))
    combo = [1.0 if np.isfinite(x) and np.isfinite(y)
             and (min(int(x) % 10, int(y) % 10), max(int(x) % 10, int(y) % 10)) in HE5 else 0.0
             for x, y in zip(sxa, sxb)]
    add(np.asarray(combo, np.float32).reshape(-1, 1), ["stem_he_combo"])
    NAYIN = [3,1,0,2,3,1,4,2,3,0,4,2,1,0,4,3,1,0,2,3,1,4,2,3,0,4,2,1,0,4]
    nya = np.where(np.isfinite(sxa), np.array(NAYIN)[np.nan_to_num(sxa).astype(int) // 2 % 30], np.nan)
    nyb = np.where(np.isfinite(sxb), np.array(NAYIN)[np.nan_to_num(sxb).astype(int) // 2 % 30], np.nan)
    # Na Yin elements use the wood-fire-earth-metal-water indices already
    rel_n = np.where(np.isfinite(nya) & np.isfinite(nyb),
                     [_rel_elem(int(x), int(y)) if np.isfinite(x) and np.isfinite(y) else 5
                      for x, y in zip(nya, nyb)], np.nan)
    add(*oh(rel_n, 6, "nayin_rel", ELREL_L))

    # ── VEDHA, MAHENDRA, STRIDIRGHA from the two stars
    okn = np.isfinite(na) & np.isfinite(nb)
    ved = [1.0 if np.isfinite(x) and np.isfinite(y)
           and (min(int(x), int(y)), max(int(x), int(y))) in VEDHA else 0.0 for x, y in zip(na, nb)]
    add(np.asarray(ved, np.float32).reshape(-1, 1), ["vedha_pair"])
    cnt = np.where(okn, (na - nb) % 27 + 1, np.nan)          # from her star to his, inclusive
    add(np.where(np.isfinite(cnt), np.isin(cnt, [4, 7, 10, 13, 16, 19, 22, 25]).astype(np.float32), 0).reshape(-1, 1),
        ["mahendra"])
    add(np.where(np.isfinite(cnt), (cnt > 13).astype(np.float32), 0).reshape(-1, 1), ["stridirgha"])

    # ── HOUSE-FROM-MOON OVERLAYS: his planet counted from HER Moon sign, and hers from his
    for tag, C1, refm in (("his", A, rb), ("her", B, ra)):     # his bodies against HER Moon, and vice versa
        for b in ("sun", "venus", "mars", "jupiter"):
            s1 = np.floor((C1[:, ix[b]] % 360) / 30)
            h = np.where(np.isfinite(s1) & np.isfinite(refm), (s1 - refm) % 12, np.nan)
            add(*oh(h, 12, f"{tag}_{b}_from_other_moon"))

    # ── 7th HARMONIC pairs (Addey) for Venus and Moon; tithi-class pair
    for b in ("venus", "moon"):
        h7a = np.floor(((A[:, ix[b]] * 7) % 360) / 30); h7b = np.floor(((B[:, ix[b]] * 7) % 360) / 30)
        pr = np.where(np.isfinite(h7a) & np.isfinite(h7b), h7a * 12 + h7b, np.nan)
        add(*oh(pr, 144, f"{b}_h7pair", [f"{EG.SIGNS[i]}x{EG.SIGNS[j]}" for i in range(12) for j in range(12)]))
    ta = np.floor(((ma - A[:, ix["sun"]]) % 360) / 12) % 5
    tb = np.floor(((mb - B[:, ix["sun"]]) % 360) / 12) % 5
    TCL = ["Nanda", "Bhadra", "Jaya", "Rikta", "Purna"]
    pr = np.where(np.isfinite(ta) & np.isfinite(tb), ta * 5 + tb, np.nan)
    add(*oh(pr, 25, "tithiclass_pair", [f"{x}x{y}" for x in TCL for y in TCL]))

    X = np.column_stack(blocks).astype(np.float32)
    return X, names


if __name__ == "__main__":
    D = os.path.expanduser("~/.artamatch-dev/remar_sh2")
    tr = pd.read_csv(f"{D}/train.csv", dtype=str).head(2000)
    Z = np.load(f"{D}/phases.npz", allow_pickle=True)
    X, names = families15(tr.reset_index(drop=True), Z, "train")
    # smoke on a slice: shapes, no all-NaN, name count
    print(f"  {X.shape[1]} indicators from families15 · fired-mean {np.nanmean(X):.4f}")
    import collections
    fam = collections.Counter(n.split("=")[0] for n in names)
    for f, c in fam.most_common(12):
        print(f"    {f:<28}{c}")
