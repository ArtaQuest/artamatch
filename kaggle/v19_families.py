"""
v19_families.py — wave 4, the finalisation wave. All both-date, all named astrology/numerology:
  - RETROGRADE PAIRS for Venus, Mercury and Mars (neither/hers/his/both) — natal retrogrades are core
    doctrine and the training flags were dead until the calc_ut indexing fix;
  - the NODE & CHIRON synastry rows the grid never had (the karmic axis): his/her node and Chiron
    against the other's ten bodies, seven aspects;
  - EXACT conjunctions (within 1 degree): graha yuddha, the planetary war;
  - GANDANTA and VARGOTTAMA pairs for the Moon, combust-Venus pairs;
  - MAYAN TZOLKIN: the 260-day sacred round (GMT correlation) — day-sign pairs and the sign distance;
  - the 28 CHINESE MANSIONS (xiu) day cycle — pair distance;
  - NINE-STAR month stars paired; numerology ATTITUDE pairs.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/research/sidereal"))
import explain_gam as EG

TEN = ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto")
_SP = {}

def _speeds(dates):
    """retrograde speed per (date, body), cached; the shipped ephemeris, Lahiri-independent."""
    if not _SP:
        import sweshim as SW
        SW.load(os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/ephem4.bin"),
                os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/tables.json"))
        SW.set_sid_mode(SW.SIDM_LAHIRI)
        _SP["sw"] = SW
        _SP["codes"] = {"mercury": SW.MERCURY, "venus": SW.VENUS, "mars": SW.MARS}
        _SP["cache"] = {}
    SW = _SP["sw"]; cache = _SP["cache"]
    out = {}
    for ds in dates:
        if ds in cache:
            out[ds] = cache[ds]; continue
        r = {}
        if len(ds) >= 10 and ds[:4].isdigit() and ds[:4] != "0000" and ds[5:7] != "00" and ds[8:10] != "00":
            try:
                jd = SW.julday(int(ds[:4]), int(ds[5:7]), int(ds[8:10]), 12.0)
                for b, c in _SP["codes"].items():
                    r[b] = SW.calc_ut(jd, c)[0][3]
            except Exception:
                r = {}
        cache[ds] = r; out[ds] = r
    return out

def families19(df, Z, half):
    bodies = [str(b) for b in Z["bodies"]]
    A = np.asarray(Z[f"theta_a_{half}"], float); B = np.asarray(Z[f"theta_b_{half}"], float)
    ix = {b: bodies.index(b) for b in bodies}
    blocks, names = [], []
    add = lambda M, nm: (blocks.append(np.asarray(M, np.float32)), names.extend(nm))
    oh = EG.onehot
    arc = lambda x, y: np.abs((x - y + 180.0) % 360.0 - 180.0)
    P4 = ["neither", "her_only", "his_only", "both"]

    # retro pairs
    sp = _speeds(list(df.dob_a.astype(str)) + list(df.dob_b.astype(str)))
    for b in ("venus", "mercury", "mars"):
        ra = np.array([1.0 if sp[d].get(b, 0) < 0 else 0.0 for d in df.dob_a.astype(str)])
        rb = np.array([1.0 if sp[d].get(b, 0) < 0 else 0.0 for d in df.dob_b.astype(str)])
        add(*oh(ra * 2 + rb, 4, f"retro_{b}_pair", P4))

    # node & chiron synastry rows (both directions), seven aspects
    ASP = ((0, 8, "conj"), (60, 4, "sext"), (90, 6, "square"), (120, 6, "trine"), (180, 8, "opp"),
           (150, 3, "quinc"), (30, 3, "semisext"))
    for x in ("true_node", "chiron"):
        for y in TEN:
            a1 = arc(A[:, ix[x]], B[:, ix[y]]); a2 = arc(A[:, ix[y]], B[:, ix[x]])
            for t, o, lab in ASP:
                add(np.where(np.isfinite(a1), (np.abs(a1 - t) <= o).astype(np.float32), 0).reshape(-1, 1),
                    [f"his_{x}_{lab}_her_{y}"])
                add(np.where(np.isfinite(a2), (np.abs(a2 - t) <= o).astype(np.float32), 0).reshape(-1, 1),
                    [f"his_{y}_{lab}_her_{x}"])

    # exact conjunctions (graha yuddha, <= 1 degree)
    for x in TEN:
        for y in TEN:
            a = arc(A[:, ix[x]], B[:, ix[y]])
            add(np.where(np.isfinite(a), (a <= 1.0).astype(np.float32), 0).reshape(-1, 1),
                [f"his_{x}_exactconj_her_{y}"])

    # gandanta (Moon within 3deg20 of a water->fire boundary) and vargottama (same sign D1 & D9) pairs
    GW = 10.0 / 3.0
    def gand(C):
        lon = C[:, ix["moon"]] % 360
        d = np.minimum(lon % 120, 120 - lon % 120)     # boundaries at 0/120/240 (Pis-Ari, Can-Leo, Sco-Sag)
        return np.where(np.isfinite(lon), (d <= GW).astype(float), np.nan)
    ga_, gb_ = gand(A), gand(B)
    add(*oh(np.where(np.isfinite(ga_) & np.isfinite(gb_), ga_ * 2 + gb_, np.nan), 4, "gandanta_moon_pair", P4))
    for b in ("moon", "venus"):
        va = np.floor((A[:, ix[b]] % 360) / 30) == np.floor((A[:, ix[b]] % 360) / GW) % 12
        vb = np.floor((B[:, ix[b]] % 360) / 30) == np.floor((B[:, ix[b]] % 360) / GW) % 12
        okv = np.isfinite(A[:, ix[b]]) & np.isfinite(B[:, ix[b]])
        add(*oh(np.where(okv, va.astype(float) * 2 + vb.astype(float), np.nan), 4, f"vargottama_{b}_pair", P4))
    ca = arc(A[:, ix["venus"]], A[:, ix["sun"]]) <= 8.5
    cb = arc(B[:, ix["venus"]], B[:, ix["sun"]]) <= 8.5
    okc = np.isfinite(A[:, ix["venus"]]) & np.isfinite(A[:, ix["sun"]]) \
        & np.isfinite(B[:, ix["venus"]]) & np.isfinite(B[:, ix["sun"]])
    add(*oh(np.where(okc, ca.astype(float) * 2 + cb.astype(float), np.nan), 4, "combust_venus_pair", P4))

    # Tzolkin (GMT correlation 584283) and the 28-mansion day cycle
    import importlib.util
    _dv = importlib.util.spec_from_file_location("dv", os.path.expanduser("~/.artamatch-dev/newfam/davison_chart.py"))
    dv = importlib.util.module_from_spec(_dv); _dv.loader.exec_module(dv)
    ja, jb = dv._jdn(df.dob_a), dv._jdn(df.dob_b)
    okj = np.isfinite(ja) & np.isfinite(jb)
    ksa = np.where(np.isfinite(ja), (np.nan_to_num(ja) - 584283) % 260 % 20, np.nan)
    ksb = np.where(np.isfinite(jb), (np.nan_to_num(jb) - 584283) % 260 % 20, np.nan)
    add(*oh(np.where(okj, ksa * 20 + ksb, np.nan), 400, "tzolkin_signpair"))
    add(*oh(np.where(okj, (ksa - ksb) % 20, np.nan), 20, "tzolkin_dist"))
    add(*oh(np.where(okj, (np.nan_to_num(ja) - np.nan_to_num(jb)) % 28, np.nan), 28, "xiu_dist"))

    # Nine-Star month star pair; numerology attitude pair
    ya = pd.to_numeric(df.dob_a.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    yb = pd.to_numeric(df.dob_b.str[:4], errors="coerce").replace(0, np.nan).to_numpy(float)
    mo_a = pd.to_numeric(df.dob_a.str[5:7], errors="coerce").replace(0, np.nan).to_numpy(float)
    dd_a = pd.to_numeric(df.dob_a.str[8:10], errors="coerce").replace(0, np.nan).to_numpy(float)
    mo_b = pd.to_numeric(df.dob_b.str[5:7], errors="coerce").replace(0, np.nan).to_numpy(float)
    dd_b = pd.to_numeric(df.dob_b.str[8:10], errors="coerce").replace(0, np.nan).to_numpy(float)
    def ninestar_year(y):
        return np.array([1 + (11 - (1 + (sum(int(c) for c in str(int(v))) - 1) % 9) - 1) % 9
                         if np.isfinite(v) else np.nan for v in y])
    def month_star(y, mo, dd):
        ys = ninestar_year(y)
        adj = np.where(np.isfinite(mo) & np.isfinite(dd),
                       np.where((mo > 2) | ((mo == 2) & (dd >= 4)), mo - 2, mo + 10), np.nan)
        first = np.where(np.isfinite(ys), np.select([ys % 3 == 1, ys % 3 == 2], [8.0, 2.0], 5.0), np.nan)
        return np.where(np.isfinite(adj) & np.isfinite(first), 1 + (first - 1 - adj) % 9, np.nan)
    msa, msb = month_star(ya, mo_a, dd_a), month_star(yb, mo_b, dd_b)
    add(*oh(np.where(np.isfinite(msa) & np.isfinite(msb), (msa - 1) * 9 + (msb - 1), np.nan), 81, "ninestar_monthpair"))
    red = lambda v: np.where(np.isfinite(v), 1 + (np.nan_to_num(v) - 1) % 9, np.nan)
    aa = red(dd_a + mo_a); ab = red(dd_b + mo_b)
    add(*oh(np.where(np.isfinite(aa) & np.isfinite(ab), (aa - 1) * 9 + (ab - 1), np.nan), 81, "attitude_pair"))
    X = np.column_stack(blocks).astype(np.float32)
    return X, names
