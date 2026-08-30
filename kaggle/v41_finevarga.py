"""v41_finevarga.py — the divisional charts, and finer cuts of the slow cycles.

The bank reads the composite chart at sign resolution: one twelfth of the circle, thirty degrees. Every
Indian tradition insists that is only the first of sixteen readings — the vargas divide each sign
again, and a planet's navamsa is held to matter more for marriage than its rasi. This adds them for the
composite and Davison charts, which is a finer cut of exactly the quantity the bank already reads:

    D3   drekkana      ten degrees      D9   navamsa       three degrees twenty
    D12  dwadasamsa    two and a half   D16  shodasamsa    one degree fifty-two
    D30  trimsamsa     one degree

and, on the same principle, the Rudhyar cycles cut into 96 and 144 parts rather than 48 and 72.

SAY WHAT THIS IS. Finer divisions of a midpoint chart are finer divisions of an era quantity: a varga
of the composite Pluto is a narrower slice of the same century. It is doctrine — the vargas are as
named as anything in the bank — and it is not evidence about a couple. interaction_filter.py scores
it accordingly and the gate removes it; it is built for the ungated maximum-AUC line of work, and the
distinction has to be carried in the reporting rather than lost.

build(df, Z, split, exclude, min_support) -> (X, names), binary.
"""
import numpy as np
import pandas as pd

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
USE = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
VARGA = [("d3", 3), ("d9", 9), ("d12", 12), ("d16", 16), ("d30", 30)]
PAIRS = [("saturn", "pluto"), ("uranus", "pluto"), ("neptune", "pluto"), ("uranus", "neptune"),
         ("saturn", "neptune"), ("saturn", "uranus"), ("jupiter", "saturn")]


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


def build(df, Z=None, split=None, exclude=frozenset(), min_support=40):
    n = len(df); ms = min_support
    if Z is None or split is None:
        return np.zeros((n, 0), np.float32), []
    A = np.asarray(Z[f"theta_a_{split}"], float)
    B = np.asarray(Z[f"theta_b_{split}"], float)
    cols, names = [], []

    for b in USE:
        a_, b_ = A[:, BI[b]], B[:, BI[b]]
        good = np.isfinite(a_) & np.isfinite(b_)
        raw = ((b_ - a_ + 180.0) % 360.0) - 180.0
        m = np.where(good, (a_ + raw / 2.0) % 360.0, np.nan)
        for tag, d in VARGA:
            # the varga sign: divide the 30-degree sign into d parts and count on round the zodiac
            deg = m % 30.0
            v = ((m // 30).astype(float) * d + np.floor(deg / (30.0 / d))) % 12
            lab = np.where(good, np.array(SIGNS, dtype=object)[np.nan_to_num(v).astype(int) % 12], "na")
            _cats(lab, f"comp{tag}_{b}", names, cols, ms)
        # and the same for the Davison, whose fast bodies genuinely differ from the composite
    for x, y in PAIRS:
        pa = (A[:, BI[x]] - A[:, BI[y]]) % 360.0
        pb = (B[:, BI[x]] - B[:, BI[y]]) % 360.0
        same = np.isfinite(pa) & np.isfinite(pb)
        for div in (96, 144):
            ka = np.floor(np.nan_to_num(pa) / (360.0 / div)).astype(int) % div
            kb = np.floor(np.nan_to_num(pb) / (360.0 / div)).astype(int) % div
            agree = same & (ka == kb)
            _flag(cols, names, agree, f"cycle{div}_{x}_{y}_same_part", ms)
            for v in (pd.unique(ka[agree]) if agree.any() else []):
                c = (agree & (ka == v)).astype(np.float32)
                if c.sum() >= ms:
                    cols.append(c); names.append(f"cycle{div}_{x}_{y}={v}")

    keep = [i for i, nm in enumerate(names) if nm not in exclude]
    X = np.column_stack([cols[i] for i in keep]).astype(np.float32) if keep else np.zeros((n, 0), np.float32)
    return X, [names[i] for i in keep]
