"""v37_harmonics.py — Addey's harmonics, as continuous features, over every cross-chart angle.

WHY THIS EXISTS. Every synastry statement in the bank is a BINARY: "his Venus is trine her Mars,
within six degrees". That throws away almost everything the angle contains. A pair four degrees from
exact and a pair five degrees and fifty-nine minutes from exact are the same flag; a pair six degrees
and one minute away is nothing at all. Doctrine does not say that — every tradition holds that an
aspect is strongest when exact and fades from there, and John Addey's *Harmonics in Astrology* (1976)
says the whole zodiac of aspects is nothing but a Fourier series on the angle between two bodies.

So: for each ordered cross-chart pair (his X, her Y) take the angle t = (his X - her Y) mod 360 and
emit cos(k t) and sin(k t) for k = 1..K. That is the harmonic decomposition of the aspect circle,
literally Addey's technique, and it is the natural continuous form of the thing the binaries
approximate:

    k=1  the conjunction/opposition axis        k=2  the opposition (the 2nd harmonic)
    k=3  the trine                              k=4  the square
    k=5  the quintile        k=6  the sextile    k=7  the septile
    k=8  the semi-square     k=9  the novile     k=12 the semi-sextile

A cosine at harmonic k peaks exactly where that aspect is exact and falls away smoothly, with no orb
to choose and no cliff at its edge. The sine term carries which SIDE of exact the angle sits on —
applying or separating, which traditional practice reads as a real distinction.

GRADED ASPECTS. The same idea stated the way an astrologer states it: strength = 1 - |gap| / orb,
zero outside the orb. Same doctrine, same orbs as the binary bank, but graded. Kept alongside the
harmonics because it is the form a reader recognises.

Everything here is a function of BOTH charts and of nothing else — there is no midpoint quantity in
this file. build(df, Z, split, exclude, min_support) -> (X, names), X continuous in [-1, 1].
"""
import numpy as np

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
import os
# The slow bodies carry the ERA in their absolute longitude — Pluto moves four thousandths of a degree
# a day, so cos(his Pluto - her Neptune) is nearly a function of the decade. AQ_HARM_BODIES=fast keeps
# only the bodies that move fast enough that the angle is about the two births rather than the century.
_FAST = ["sun", "moon", "mercury", "venus", "mars", "true_node"]
_ALL = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
        "true_node", "chiron", "mean_lilith"]
USE = _FAST if os.environ.get("AQ_HARM_BODIES") == "fast" else (
      _ALL if os.environ.get("AQ_HARM_BODIES") == "all" else _ALL[:11])
KMAX = int(os.environ.get("AQ_KMAX", "16"))
ASPECTS = [("conj", 0, 8), ("sext", 60, 4), ("square", 90, 6), ("trine", 120, 6), ("opp", 180, 8),
           ("quinc", 150, 3), ("semisext", 30, 3)]


def build(df, Z=None, split=None, exclude=frozenset(), min_support=40):
    n = len(df)
    if Z is None or split is None:
        return np.zeros((n, 0), np.float32), []
    A = np.asarray(Z[f"theta_a_{split}"], float)
    B = np.asarray(Z[f"theta_b_{split}"], float)
    cols, names = [], []

    for x in USE:
        ax = A[:, BI[x]]
        for y in USE:
            by = B[:, BI[y]]
            t = np.radians((ax - by) % 360.0)
            good = np.isfinite(t)
            t = np.where(good, t, 0.0)
            for k in range(1, KMAX + 1):
                for fn, lab in ((np.cos, "cos"), (np.sin, "sin")):
                    nm = f"h{k}{lab}_his_{x}_her_{y}"
                    if nm in exclude:
                        continue
                    v = np.where(good, fn(k * t), 0.0).astype(np.float32)
                    cols.append(v); names.append(nm)
            # the graded aspect: the binary the bank already has, but with the cliff taken off
            gap = np.abs(((ax - by + 180.0) % 360.0) - 180.0)
            for lab, ang, orb in ASPECTS:
                nm = f"grade_{lab}_his_{x}_her_{y}"
                if nm in exclude:
                    continue
                s = np.clip(1.0 - np.abs(gap - ang) / orb, 0.0, 1.0)
                cols.append(np.where(good, s, 0.0).astype(np.float32)); names.append(nm)

    X = np.column_stack(cols).astype(np.float32) if cols else np.zeros((n, 0), np.float32)
    return X, names
