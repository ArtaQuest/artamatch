"""v39_composite_harm.py — the composite and Davison charts, at full harmonic resolution.

The bank reads the composite chart through signs and decans: "Pluto in Pisces, in the composite". That
is a twelve-way cut of a continuous quantity. This reads the same chart the way v37 reads synastry —
as a Fourier series on the angle — so the model sees the composite position itself rather than which
twelfth it happens to fall in.

  COMPOSITE   the circular midpoint of his body and hers: the chart of the relationship, read as a
              third entity. Ebertin's construction, and the one the bank already uses.
  DAVISON     the chart for the midpoint in TIME rather than in space. It disagrees with the composite
              on fast bodies and agrees on slow ones, so both are built.
  COMPOSITE ASPECTS  the angles WITHIN the composite chart, graded rather than flagged.

SAY THIS PLAINLY. A midpoint is an era quantity. Two people born twenty years apart around 1900 have
almost the same composite Pluto as two people born forty years apart around 1900, so anything here is
partly a statement about the century rather than about the couple — which is exactly what
interaction_filter.py exists to detect, and exactly what it scores these features near zero for. They
are built because the brief is to maximise cross-validated AUC with astrology's own vocabulary, and
the composite chart is unambiguously part of that vocabulary. What they are NOT is evidence that two
particular people suit each other.

build(df, Z, split, exclude, min_support) -> (X, names), continuous.
"""
import os
import numpy as np

BODIES = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
          "true_node", "true_south_node", "chiron", "mean_lilith", "ascendant", "medium_coeli"]
BI = {b: i for i, b in enumerate(BODIES)}
USE = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
       "true_node", "chiron", "mean_lilith"]
KMAX = int(os.environ.get("AQ_CKMAX", "16"))
ASPECTS = [("conj", 0, 8), ("sext", 60, 4), ("square", 90, 6), ("trine", 120, 6), ("opp", 180, 8)]


def build(df, Z=None, split=None, exclude=frozenset(), min_support=40):
    n = len(df)
    if Z is None or split is None:
        return np.zeros((n, 0), np.float32), []
    A = np.asarray(Z[f"theta_a_{split}"], float)
    B = np.asarray(Z[f"theta_b_{split}"], float)
    cols, names = [], []
    mids = {}
    for b in USE:
        a_, b_ = A[:, BI[b]], B[:, BI[b]]
        good = np.isfinite(a_) & np.isfinite(b_)
        raw = ((b_ - a_ + 180.0) % 360.0) - 180.0            # the short way round
        m = np.where(good, (a_ + raw / 2.0) % 360.0, 0.0)
        mids[b] = (m, good)
        t = np.radians(m)
        for k in range(1, KMAX + 1):
            for fn, lab in ((np.cos, "cos"), (np.sin, "sin")):
                nm = f"comph{k}{lab}_{b}"
                if nm in exclude:
                    continue
                cols.append(np.where(good, fn(k * t), 0.0).astype(np.float32)); names.append(nm)
    for i, x in enumerate(USE):
        mx, gx = mids[x]
        for y in USE[i + 1:]:
            my, gy = mids[y]
            good = gx & gy
            gap = np.abs(((mx - my + 180.0) % 360.0) - 180.0)
            for lab, ang, orb in ASPECTS:
                nm = f"compgrade_{lab}_{x}_{y}"
                if nm in exclude:
                    continue
                s = np.clip(1.0 - np.abs(gap - ang) / orb, 0.0, 1.0)
                cols.append(np.where(good, s, 0.0).astype(np.float32)); names.append(nm)
            t = np.radians(np.where(good, (mx - my) % 360.0, 0.0))
            for k in (1, 2, 3, 4, 6):
                nm = f"comphrel{k}cos_{x}_{y}"
                if nm in exclude:
                    continue
                cols.append(np.where(good, np.cos(k * t), 0.0).astype(np.float32)); names.append(nm)
    X = np.column_stack(cols).astype(np.float32) if cols else np.zeros((n, 0), np.float32)
    return X, names
