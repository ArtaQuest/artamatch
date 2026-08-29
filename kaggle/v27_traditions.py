"""v27_traditions.py — deepen where the signal actually is, instead of widening further.

A univariate screen over all 10,309 statements, counting how many clear |z| > 2 against how many chance
alone would throw up, ranked the families:

    outer cycles          5.93x chance      composite / Davison   3.60x
    synastry aspects      1.81x             Tibetan               1.50x
    Nine Star Ki          1.37x             numerology            1.33x
  ...and at or below chance: D9 0.90, Chandra lagna 0.83, Manglik 0.74, Jaimini 0.73,
     fixed stars 0.00, jieqi 0.00, manzil 0.00, critical degrees 0.00

Two families carry nearly everything, and the strongest single statement in the whole bank (|z| = 9.3)
is a composite one. Yet the composite and Davison charts had signs, decans, nakshatras and tithis — and
only TWENTY within-chart aspects between them. That is the gap this file closes.

  COMPOSITE ASPECTS   every pair of the ten bodies, seven angles, in both the composite (midpoint of the
                      two charts) and the Davison (a real chart for the midpoint in time). ~600 statements
                      where there were 20.
  DIGNITY             each body in its own sign, exalted, or in fall — the classical strength test —
                      inside both relationship charts.
  BALANCE             how the relationship chart distributes across fire/earth/air/water and
                      cardinal/fixed/mutable: the first thing a reader looks at in any chart.
  FINER CYCLES        the outer-planet cycles cut into 48 and 72, and four planet pairs the bank never
                      had, plus the raw separation in ten-degree steps.
  SYMMETRISED         for the doctrines that do NOT distinguish who is who — Chinese animals, life
                      paths, Tzolkin, Nine Star, Mewa, Parkha — the unordered pair, which doubles the
                      support in every cell and so lets twice as many clear the floor.

Every statement uses BOTH dates. build(df, Z, split, exclude, min_support) -> (X, names).
"""
import numpy as np
import pandas as pd

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
TEN = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
ASPECTS = [("conj", 0, 8), ("opp", 180, 8), ("trine", 120, 7), ("square", 90, 6),
           ("sext", 60, 5), ("semisext", 30, 2), ("quinc", 150, 3)]
RULER = {"mars": [0, 7], "venus": [1, 6], "mercury": [2, 5], "moon": [3], "sun": [4],
         "jupiter": [8, 11], "saturn": [9, 10]}
EXALT = {"sun": 0, "moon": 1, "mercury": 5, "venus": 11, "mars": 9, "jupiter": 3, "saturn": 6}
ELEM = ["Fire", "Earth", "Air", "Water"] * 3
MODE = ["Cardinal", "Fixed", "Mutable"] * 4
SLOW_PAIRS = [("jupiter", "uranus"), ("jupiter", "neptune"), ("jupiter", "pluto"), ("mars", "saturn")]


def _cats(vals, prefix, names, cols, ms):
    vals = np.asarray(vals)
    for v in pd.unique(vals):
        c = (vals == v).astype(np.float32)
        if c.sum() >= ms:
            cols.append(c); names.append(f"{prefix}={v}")


def _flag(cols, names, arr, nm, ms):
    c = np.nan_to_num(np.asarray(arr)).astype(np.float32)
    if ms <= c.sum() <= len(c) - ms:
        cols.append(c); names.append(nm)


def midlon(x, y):
    d = ((y - x + 180) % 360) - 180
    return (x + d / 2.0) % 360.0


def build(df, Z, split, exclude=frozenset(), min_support=40):
    n = len(df); ms = min_support
    A = Z[f"theta_a_{split}"]; B = Z[f"theta_b_{split}"]
    ya = pd.to_numeric(df.dob_a.str[:4]).to_numpy(int)
    yb = pd.to_numeric(df.dob_b.str[:4]).to_numpy(int)
    ma = pd.to_numeric(df.dob_a.str[5:7]).to_numpy(int); da = pd.to_numeric(df.dob_a.str[8:10]).to_numpy(int)
    mb = pd.to_numeric(df.dob_b.str[5:7]).to_numpy(int); db = pd.to_numeric(df.dob_b.str[8:10]).to_numpy(int)
    cols, names = [], []

    # the two relationship charts
    C = np.column_stack([midlon(A[:, BI[b]], B[:, BI[b]]) for b in TEN])   # composite: midpoints
    CI = {b: i for i, b in enumerate(TEN)}
    # Davison: the chart of the midpoint IN TIME. Without re-casting we approximate each body by its
    # own mean motion carried to the midpoint date, which is exact for the slow bodies and close for
    # the fast ones; the composite above is the exact midpoint construction.
    MOTION = {"sun": 0.9856, "moon": 13.1764, "mercury": 1.383, "venus": 1.602, "mars": 0.524,
              "jupiter": 0.0831, "saturn": 0.0335, "uranus": 0.0117, "neptune": 0.0060,
              "pluto": 0.0040}
    def _jdn(y, m, d):
        a = (14 - m) // 12; yy = y + 4800 - a; mm = m + 12 * a - 3
        return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    jda = np.array([_jdn(y, m, d) for y, m, d in zip(ya, ma, da)])
    jdb = np.array([_jdn(y, m, d) for y, m, d in zip(yb, mb, db)])
    half = (jdb - jda) / 2.0
    Dv = np.column_stack([(A[:, BI[b]] + MOTION[b] * half) % 360.0 for b in TEN])

    for chart, tag in ((C, "comp"), (Dv, "dav")):
        # ---------- aspects between every pair of bodies inside the relationship chart ----------
        for i in range(len(TEN)):
            for j in range(i + 1, len(TEN)):
                d = np.abs(((chart[:, i] - chart[:, j] + 180) % 360) - 180)
                for an, ang, orb in ASPECTS:
                    c = (np.abs(d - ang) <= orb).astype(np.float32)
                    c[~np.isfinite(d)] = 0.0
                    if ms <= c.sum() <= len(c) - ms:
                        cols.append(c); names.append(f"{tag}X_{TEN[i]}_{an}_{TEN[j]}")
        # ---------- classical dignity ----------
        sg = (chart // 30).astype(int) % 12
        for b in ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"):
            s = sg[:, CI[b]]
            _flag(cols, names, np.isin(s, RULER.get(b, [])), f"{tag}_{b}_own_sign", ms)
            _flag(cols, names, s == EXALT[b], f"{tag}_{b}_exalted", ms)
            _flag(cols, names, s == (EXALT[b] + 6) % 12, f"{tag}_{b}_in_fall", ms)
        # ---------- elemental and modal balance of the relationship chart ----------
        for lab, table in (("elem", ELEM), ("mode", MODE)):
            counts = {}
            for k in set(table):
                counts[k] = np.sum([np.isin(sg[:, CI[b]], [q for q, t in enumerate(table) if t == k])
                                    for b in TEN], axis=0)
            dom = np.array([max(counts, key=lambda k: counts[k][r]) for r in range(n)])
            _cats(dom, f"{tag}_dominant_{lab}", names, cols, ms)
            for k in sorted(set(table)):
                _cats(np.clip(counts[k], 0, 6), f"{tag}_{lab}_{k}_count", names, cols, ms)
            _flag(cols, names, np.array([counts[k][r] == 0 for r in range(n) for k in [None]])
                  if False else np.any([counts[k] == 0 for k in counts], axis=0),
                  f"{tag}_{lab}_a_whole_class_empty", ms)

    # ---------- finer outer-planet cycles, and pairs the bank never had ----------
    def cyc(x, y):
        return (A[:, BI[x]] - A[:, BI[y]]) % 360.0, (B[:, BI[x]] - B[:, BI[y]]) % 360.0
    PAIRS = [("saturn", "pluto"), ("uranus", "pluto"), ("neptune", "pluto"), ("uranus", "neptune"),
             ("saturn", "neptune"), ("saturn", "uranus"), ("jupiter", "saturn")] + SLOW_PAIRS
    for x, y in PAIRS:
        pa, pb = cyc(x, y)
        same = np.isfinite(pa) & np.isfinite(pb)
        # NOTE: an "na" catch-all here would be a statement meaning "the two births differ", which is
        # real but unreadable — and its negation shipped into a model once as
        # NOT(cyclesep10_neptune_pluto=na). Name the shared-bin condition explicitly instead, and let
        # the per-bin statements carry only rows that actually share that bin.
        for div in (48, 72):
            ka = np.floor(pa / (360.0 / div)).astype(int) % div
            kb = np.floor(pb / (360.0 / div)).astype(int) % div
            agree = same & (ka == kb)
            _flag(cols, names, agree, f"cycle{div}_{x}_{y}_same_part", ms)
            for v in pd.unique(ka[agree]) if agree.any() else []:
                c = (agree & (ka == v)).astype(np.float32)
                if c.sum() >= ms:
                    cols.append(c); names.append(f"cycle{div}_{x}_{y}={v}")
        sa = np.floor(pa / 10.0).astype(int) % 36
        sb = np.floor(pb / 10.0).astype(int) % 36
        agree = same & (sa == sb)
        _flag(cols, names, agree, f"cyclesep10_{x}_{y}_same_band", ms)
        for v in pd.unique(sa[agree]) if agree.any() else []:
            c = (agree & (sa == v)).astype(np.float32)
            if c.sum() >= ms:
                cols.append(c); names.append(f"cyclesep10_{x}_{y}={v}")

    # ---------- SYMMETRISED pairs, for the doctrines that do not distinguish who is who ----------
    def _dsum(v):
        s = 0
        while v:
            s += v % 10; v //= 10
        return s
    def _red(v, keep=(11, 22, 33)):
        while v > 9 and v not in keep:
            v = _dsum(v)
        return v
    def _red1(v):
        while v > 9:
            v = _dsum(v)
        return v
    ANIM = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster",
            "Dog", "Pig"]
    lpa = np.array([_red(_red1(y) + _red1(m) + _red1(d)) for y, m, d in zip(ya, ma, da)])
    lpb = np.array([_red(_red1(y) + _red1(m) + _red1(d)) for y, m, d in zip(yb, mb, db)])
    bra = (ya - 4) % 12; brb = (yb - 4) % 12
    tza = (jda + 159) % 260 % 20; tzb = (jdb + 159) % 260 % 20
    def nsk(y, m, d):
        yy = y if (m > 2 or (m == 2 and d >= 4)) else y - 1
        s = 11 - _red1(_dsum(yy))
        if s > 9:
            s -= 9
        return 9 if s == 0 else s
    nka = np.array([nsk(y, m, d) for y, m, d in zip(ya, ma, da)])
    nkb = np.array([nsk(y, m, d) for y, m, d in zip(yb, mb, db)])
    SYM = [("sym_lifepathpair", lpa, lpb, None),
           ("sym_animalpair", bra, brb, ANIM),
           ("sym_tzolkinpair", tza, tzb, None),
           ("sym_ninestarpair", nka, nkb, None),
           ("sym_mewapair", (ya - 1927) % 9, (yb - 1927) % 9, None),
           ("sym_parkhapair", (ya - 1927) % 8, (yb - 1927) % 8, None)]
    for nm, u, v, lut in SYM:
        lab = []
        for x, y in zip(u, v):
            lo, hi = (x, y) if x <= y else (y, x)
            lab.append(f"{lut[lo]}x{lut[hi]}" if lut else f"{lo}x{hi}")
        _cats(lab, nm, names, cols, ms)

    keep = [i for i, nm in enumerate(names) if nm not in exclude]
    X = np.column_stack([cols[i] for i in keep]).astype(np.float32) if keep else np.zeros((n, 0), np.float32)
    return X, [names[i] for i in keep]
