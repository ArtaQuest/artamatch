"""v42_conjunctions.py — configurations: two named conditions that hold at once.

Every statement in the bank is read alone, and no astrologer reads a chart that way. A reading is a
CONFIGURATION — Saturn on her Moon *and* the composite Sun in the seventh — and the whole claim of the
craft is that the combination says something neither half says. A linear model over single statements
cannot express that; an explicit AND column can, and stays exactly as explainable, because the card
reads "both of these hold".

THE POOL IS CHOSEN WITHOUT THE LABEL. Pairing every statement with every other would be 130 million
columns, so a pool has to be picked — and picking it by how well each statement predicts would put
selection outside the cross-validation folds and make the score a fiction. The pool here is chosen by
SUPPORT alone: the statements that fire in between 8% and 60% of couples, ranked by how close they are
to firing half the time, which is where an AND has the most room to say something new. Support does not
involve the label, so this can be done once, outside the folds, without leaking.

build(df, Z, split, exclude, min_support) -> (X, names) with names of the form "A AND B" — the format
v24_fit already splits on when it applies the interaction gate.
"""
import os
import numpy as np

POOL = int(os.environ.get("AQ_CONJ_POOL", "160"))
LO, HI = 0.08, 0.60


def build_from(X, names, min_support=40, exclude=frozenset()):
    """X, names: an already-built binary bank. Returns the AND columns only."""
    n = len(X)
    rate = X.mean(0)
    ok = np.where((rate >= LO) & (rate <= HI))[0]
    if len(ok) == 0:
        return np.zeros((n, 0), np.float32), []
    ok = ok[np.argsort(np.abs(rate[ok] - 0.5))][:POOL]        # closest to half, label never consulted
    cols, out = [], []
    for i in range(len(ok)):
        xi = X[:, ok[i]]
        for j in range(i + 1, len(ok)):
            nm = f"{names[ok[i]]} AND {names[ok[j]]}"
            if nm in exclude:
                continue
            c = (xi * X[:, ok[j]]).astype(np.float32)
            s = c.sum()
            if min_support <= s <= n - min_support:
                cols.append(c); out.append(nm)
    X2 = np.column_stack(cols).astype(np.float32) if cols else np.zeros((n, 0), np.float32)
    return X2, out
