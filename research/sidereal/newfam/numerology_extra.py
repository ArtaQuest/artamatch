"""numerology_extra.py — biorhythm compatibility as popularly computed, combined-date roots, Lo Shu overlay."""
import numpy as np
import pandas as pd


def _jdn(col):
    out = np.full(len(col), np.nan)
    for i, v in enumerate(col.astype(str)):
        if len(v) >= 10 and v[:4].isdigit() and v[:4] != "0000" and v[5:7] != "00" and v[8:10] != "00":
            try:
                y, mo, d = int(v[:4]), int(v[5:7]), int(v[8:10])
                a = (14 - mo) // 12; yy = y + 4800 - a; mm = mo + 12 * a - 3
                out[i] = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
            except Exception:
                pass
    return out


def _root(n):
    n = int(n)
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def build(df, Z, half):
    ja, jb = _jdn(df.dob_a), _jdn(df.dob_b)
    dd = np.abs(ja - jb)
    cols, names = [], []
    tot = np.zeros(len(dd))
    for P in (23, 28, 33):
        c = np.where(np.isfinite(dd), (1 + np.cos(2 * np.pi * dd / P)) / 2, np.nan)
        cols.append(c); names.append(f"bio_compat_{P}")
        tot = tot + np.nan_to_num(c)
    cols.append(np.where(np.isfinite(dd), tot / 3, np.nan)); names.append("bio_compat_mean")
    digits = lambda s: [sum(int(c) for c in v if c.isdigit()) if isinstance(v, str) and v[:4] != "0000" else -1
                        for v in s.astype(str)]
    da, db = digits(df.dob_a), digits(df.dob_b)
    comb = np.array([float(_root(x + y)) if x >= 0 and y >= 0 else np.nan for x, y in zip(da, db)])
    cols += [comb, np.where(np.isfinite(comb), np.isin(comb, [2, 6, 9]).astype(float), np.nan)]
    names += ["combined_root", "combined_root_harmonious"]
    def loshu(s):
        out = np.full((len(s), 9), np.nan)
        for i, v in enumerate(s.astype(str)):
            if isinstance(v, str) and v[:4] != "0000":
                row = np.zeros(9)
                for c in v:
                    if c.isdigit() and c != "0":
                        row[int(c) - 1] += 1
                out[i] = row
        return out
    La, Lb = loshu(df.dob_a), loshu(df.dob_b)
    okg = np.isfinite(La).all(1) & np.isfinite(Lb).all(1)
    shared_missing = np.where(okg, ((La == 0) & (Lb == 0)).sum(1).astype(float), np.nan)
    complement = np.where(okg, (((La > 0) & (Lb == 0)) | ((La == 0) & (Lb > 0))).sum(1).astype(float), np.nan)
    overlap = np.where(okg, ((La > 0) & (Lb > 0)).sum(1).astype(float), np.nan)
    cols += [shared_missing, complement, overlap]
    names += ["loshu_shared_missing", "loshu_complement", "loshu_overlap"]
    cols += [np.where(np.isfinite(dd), dd % 7, np.nan), np.where(np.isfinite(dd), dd % 9, np.nan)]
    names += ["daygap_mod7", "daygap_mod9"]
    return np.column_stack(cols).astype(np.float32), names
