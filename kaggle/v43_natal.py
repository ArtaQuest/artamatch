"""v43_natal.py — the natal chart of each partner on its own: signs, groups, shapes, dignities.

Everything else in this project reads the two charts against each other. This reads each chart by
itself, which is how a reading actually begins — before any synastry, an astrologer says what KIND of
chart this is. Both partners get every statement, tagged his_ and her_, and the pair is left to the
rest of the bank.

  SIGNS       the sign of each body, and the finer cuts an Indian reading uses: decan, nakshatra and
              its pada, navamsa sign
  GROUPS      the element and modality each body falls in, and the COUNT of bodies in each of the four
              elements and three modalities — the chart's balance, which is what "a very Fire chart"
              means; plus the dominant element and modality, and whether any class is empty
  SHAPE       the Jones patterns: bundle, bowl, bucket, locomotive, seesaw, splash, splay. Computed
              from the largest gap between consecutive bodies round the circle, which is the standard
              construction, and a real "group" statement — it describes the whole chart at once
  STELLIUM    three or more bodies in one sign, and which sign
  DIGNITY     domicile, exaltation, detriment and fall — the classical strengths, counted
  LUNATION    the Moon's phase at birth: the eight-fold cycle every tradition reads first
  NUMEROLOGY  life path and birthday number, per person

NOTE ON WHAT THIS MEASURES. A single-side slow-planet sign is a statement about the decade someone was
born in — "his Pluto in Cancer" names a generation, not a man. These are ordinary astrology and they
are built because they were asked for, but they are the most era-loaded statements in the whole bank,
and interaction_filter.py scores them at zero by construction because they do not change when the two
births move apart. That has to be carried in the reporting.

build(df, Z, split, exclude, min_support) -> (X, names), binary.
"""
import numpy as np
import pandas as pd

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
ELEM = ["Fire", "Earth", "Air", "Water"]
MODE = ["Cardinal", "Fixed", "Mutable"]
TEN = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
EXTRA = ["true_node", "chiron", "mean_lilith"]
NAK = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya",
       "Ashlesha", "Magha", "PurvaPhalguni", "UttaraPhalguni", "Hasta", "Chitra", "Swati",
       "Vishakha", "Anuradha", "Jyeshtha", "Mula", "PurvaAshadha", "UttaraAshadha", "Shravana",
       "Dhanishta", "Shatabhisha", "PurvaBhadrapada", "UttaraBhadrapada", "Revati"]
PHASE8 = ["New", "Crescent", "FirstQtr", "Gibbous", "Full", "Disseminating", "LastQtr", "Balsamic"]
# classical rulerships: domicile / exaltation / detriment / fall, by sign index
DOMICILE = {"mars": [0, 7], "venus": [1, 6], "mercury": [2, 5], "moon": [3], "sun": [4],
            "jupiter": [8, 11], "saturn": [9, 10]}
EXALT = {"sun": 0, "moon": 1, "true_node": 2, "jupiter": 3, "mercury": 5, "saturn": 6,
         "mars": 9, "venus": 11}


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


def _shape(L):
    """Jones pattern from the ten classical bodies: n x 10 longitudes -> a label per row."""
    n = L.shape[0]
    out = np.empty(n, dtype=object)
    for r in range(n):
        v = np.sort(L[r][np.isfinite(L[r])])
        if len(v) < 8:
            out[r] = "na"; continue
        gaps = np.diff(np.concatenate([v, [v[0] + 360.0]]))
        g = np.sort(gaps)[::-1]
        span = 360.0 - g[0]
        if span <= 120:
            out[r] = "Bundle"
        elif span <= 180 and g[1] < 60:
            out[r] = "Bowl"
        elif g[1] >= 60 and span <= 240:
            out[r] = "Bucket"
        elif span <= 240:
            out[r] = "Locomotive"
        elif g[0] >= 60 and g[1] >= 60 and (g[0] + g[1]) >= 180:
            out[r] = "Seesaw"
        elif g[0] <= 60:
            out[r] = "Splash"
        else:
            out[r] = "Splay"
    return out


def build(df, Z=None, split=None, exclude=frozenset(), min_support=40):
    n = len(df); ms = min_support
    if Z is None or split is None:
        return np.zeros((n, 0), np.float32), []
    cols, names = [], []
    for tag, key in (("his", "a"), ("her", "b")):
        T = np.asarray(Z[f"theta_{key}_{split}"], float)
        sign = {}
        for b in TEN + EXTRA:
            x = T[:, BI[b]] % 360.0
            good = np.isfinite(x)
            s = np.where(good, (x // 30).astype(int) % 12, -1)
            sign[b] = s
            _cats([SIGNS[i] if i >= 0 else "na" for i in s], f"{tag}_{b}_sign", names, cols, ms)
            _cats([ELEM[i % 4] if i >= 0 else "na" for i in s], f"{tag}_{b}_elem", names, cols, ms)
            _cats([MODE[i % 3] if i >= 0 else "na" for i in s], f"{tag}_{b}_mode", names, cols, ms)
            _flag(cols, names, (s >= 0) & (s % 2 == 0), f"{tag}_{b}_yang_sign", ms)
        for b in ("sun", "moon", "venus", "mars", "mercury"):
            x = T[:, BI[b]] % 360.0
            good = np.isfinite(x)
            _cats(np.where(good, (x // 10).astype(int) % 36, -1), f"{tag}_{b}_decan", names, cols, ms)
            nk = np.where(good, (x / (360.0 / 27)).astype(int) % 27, -1)
            _cats([NAK[i] if i >= 0 else "na" for i in nk], f"{tag}_{b}_nakshatra", names, cols, ms)
            _cats(np.where(good, ((x % (360.0 / 27)) / (360.0 / 108)).astype(int), -1),
                  f"{tag}_{b}_pada", names, cols, ms)
            nv = np.where(good, ((x // 30).astype(int) * 9 + ((x % 30) / (30.0 / 9)).astype(int)) % 12, -1)
            _cats([SIGNS[i] if i >= 0 else "na" for i in nv], f"{tag}_{b}_navamsa", names, cols, ms)

        # ---- GROUPS: how many bodies fall in each element and each modality ----
        S = np.column_stack([sign[b] for b in TEN])
        for i, e in enumerate(ELEM):
            c = ((S >= 0) & (S % 4 == i)).sum(1)
            _cats(np.clip(c, 0, 6), f"{tag}_count_{e}", names, cols, ms)
            _flag(cols, names, c == 0, f"{tag}_no_{e}", ms)
            _flag(cols, names, c >= 4, f"{tag}_heavy_{e}", ms)
        for i, m_ in enumerate(MODE):
            c = ((S >= 0) & (S % 3 == i)).sum(1)
            _cats(np.clip(c, 0, 7), f"{tag}_count_{m_}", names, cols, ms)
            _flag(cols, names, c == 0, f"{tag}_no_{m_}", ms)
            _flag(cols, names, c >= 5, f"{tag}_heavy_{m_}", ms)
        ecnt = np.column_stack([((S >= 0) & (S % 4 == i)).sum(1) for i in range(4)])
        mcnt = np.column_stack([((S >= 0) & (S % 3 == i)).sum(1) for i in range(3)])
        _cats([ELEM[i] for i in ecnt.argmax(1)], f"{tag}_dominant_elem", names, cols, ms)
        _cats([MODE[i] for i in mcnt.argmax(1)], f"{tag}_dominant_mode", names, cols, ms)
        _flag(cols, names, ((S >= 0) & (S % 2 == 0)).sum(1) >= 6, f"{tag}_mostly_yang", ms)

        # ---- STELLIUM: three or more of the ten in one sign ----
        occ = np.zeros((n, 12), int)
        for j in range(12):
            occ[:, j] = (S == j).sum(1)
        _flag(cols, names, occ.max(1) >= 3, f"{tag}_has_stellium", ms)
        _flag(cols, names, occ.max(1) >= 4, f"{tag}_big_stellium", ms)
        _cats([SIGNS[i] if occ[r].max() >= 3 else "none" for r, i in enumerate(occ.argmax(1))],
              f"{tag}_stellium_sign", names, cols, ms)

        # ---- SHAPE: the Jones patterns ----
        L = np.column_stack([T[:, BI[b]] % 360.0 for b in TEN])
        _cats(_shape(L), f"{tag}_chart_shape", names, cols, ms)

        # ---- DIGNITY: the classical strengths, counted ----
        dom = np.zeros(n, int); exa = np.zeros(n, int); det = np.zeros(n, int); fal = np.zeros(n, int)
        for b, hs in DOMICILE.items():
            s = sign[b]
            dom += np.isin(s, hs).astype(int)
            det += np.isin(s, [(h + 6) % 12 for h in hs]).astype(int)
        for b, e in EXALT.items():
            if b in sign:
                exa += (sign[b] == e).astype(int)
                fal += (sign[b] == (e + 6) % 12).astype(int)
        for lab, arr in (("domicile", dom), ("exalted", exa), ("detriment", det), ("fall", fal)):
            _cats(np.clip(arr, 0, 4), f"{tag}_count_{lab}", names, cols, ms)
        _flag(cols, names, (dom + exa) > (det + fal), f"{tag}_more_dignity_than_debility", ms)

        # ---- LUNATION: the Moon's phase at birth ----
        el = (T[:, BI["moon"]] - T[:, BI["sun"]]) % 360.0
        good = np.isfinite(el)
        ph = np.where(good, (el / 45.0).astype(int) % 8, -1)
        _cats([PHASE8[i] if i >= 0 else "na" for i in ph], f"{tag}_moon_phase", names, cols, ms)
        _cats(np.where(good, (el / 12.0).astype(int) % 30, -1), f"{tag}_tithi", names, cols, ms)

    # ---- NUMEROLOGY, per person ----
    for tag, c in (("his", "dob_a"), ("her", "dob_b")):
        d = df[c].astype(str)
        ok = ~d.str.contains("-00")
        def red(v):
            while v > 9 and v not in (11, 22, 33):
                v = sum(int(x) for x in str(v))
            return v
        lp = np.array([red(sum(int(ch) for ch in s.replace("-", ""))) if o else -1
                       for s, o in zip(d, ok)])
        _cats(lp, f"{tag}_lifepath", names, cols, ms)
        bd = np.array([red(int(s[8:10])) if o else -1 for s, o in zip(d, ok)])
        _cats(bd, f"{tag}_birthday_num", names, cols, ms)

    keep = [i for i, nm in enumerate(names) if nm not in exclude]
    X = np.column_stack([cols[i] for i in keep]).astype(np.float32) if keep else np.zeros((n, 0), np.float32)
    return X, [names[i] for i in keep]
