"""v38_symharm.py — the harmonic basis, made invariant to which partner is called "his".

The fourth edition of ArtaMatch is genderless by standing order: a couple is a couple whichever way
round you read it. v37's harmonics are not — cos(k(his X - her Y)) and cos(k(her X - his Y)) are two
different columns, so the model can learn a direction the doctrine does not have, and it pays twice in
variance for one fact.

Write u = A_X - B_Y and v = A_Y - B_X for an unordered pair of bodies {X, Y}. Swapping the partners
sends u -> -v and v -> -u. Two combinations survive that unchanged:

    COS SUM        cos(k u) + cos(k v)      the aspect itself, whoever is whom
    SIN DIFFERENCE sin(k u) - sin(k v)      which of the two is applying to the other

and the third, sin(k u) + sin(k v), flips sign and is therefore a statement about gender rather than
about the couple, so it is not built. On the diagonal (X == Y) u = v, the sine difference is
identically zero, and only the cosine remains — correct, because "who is ahead" of the same body in
two charts is exactly the gendered reading.

Harmonics run to K=24 rather than Addey's 12: the Moon moves thirteen degrees a day, so the fast pairs
carry real structure well above the twelfth, and a truncation is a choice that should be measured
rather than inherited.

build(df, Z, split, exclude, min_support) -> (X, names), continuous.
"""
import numpy as np

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
# true_south_node is the exact opposite of true_node, so it is a duplicate column; ascendant and
# medium_coeli need a birth TIME and this corpus has only dates, so both are excluded on purpose.
USE = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
       "true_node", "chiron", "mean_lilith"]
KMAX = 24
ASPECTS = [("conj", 0, 8), ("sext", 60, 4), ("square", 90, 6), ("trine", 120, 6), ("opp", 180, 8),
           ("quinc", 150, 3), ("semisext", 30, 3)]


def build(df, Z=None, split=None, exclude=frozenset(), min_support=40):
    n = len(df)
    if Z is None or split is None:
        return np.zeros((n, 0), np.float32), []
    A = np.asarray(Z[f"theta_a_{split}"], float)
    B = np.asarray(Z[f"theta_b_{split}"], float)
    cols, names = [], []
    for i, x in enumerate(USE):
        for y in USE[i:]:
            ax, bx = A[:, BI[x]], B[:, BI[x]]
            ay, by = A[:, BI[y]], B[:, BI[y]]
            good = np.isfinite(ax) & np.isfinite(bx) & np.isfinite(ay) & np.isfinite(by)
            u = np.radians(np.where(good, (ax - by) % 360.0, 0.0))
            v = np.radians(np.where(good, (ay - bx) % 360.0, 0.0))
            for k in range(1, KMAX + 1):
                nm = f"symh{k}cos_{x}_{y}"
                if nm not in exclude:
                    cols.append(np.where(good, np.cos(k * u) + np.cos(k * v), 0.0).astype(np.float32))
                    names.append(nm)
                if x == y:
                    continue                     # the sine difference is identically zero here
                nm = f"symh{k}sin_{x}_{y}"
                if nm not in exclude:
                    cols.append(np.where(good, np.sin(k * u) - np.sin(k * v), 0.0).astype(np.float32))
                    names.append(nm)
            gu = np.abs(((ax - by + 180.0) % 360.0) - 180.0)
            gv = np.abs(((ay - bx + 180.0) % 360.0) - 180.0)
            for lab, ang, orb in ASPECTS:
                nm = f"symgrade_{lab}_{x}_{y}"
                if nm in exclude:
                    continue
                s = (np.clip(1.0 - np.abs(gu - ang) / orb, 0.0, 1.0)
                     + np.clip(1.0 - np.abs(gv - ang) / orb, 0.0, 1.0))
                cols.append(np.where(good, s, 0.0).astype(np.float32)); names.append(nm)
    X = np.column_stack(cols).astype(np.float32) if cols else np.zeros((n, 0), np.float32)
    return X, names
