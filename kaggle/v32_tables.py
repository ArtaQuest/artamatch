"""v32_tables.py — a compatibility TABLE is one statement, not a hundred and forty-four.

THE PROBLEM. Every pair doctrine in this bank is a k-by-k table — his life path against hers, his animal
against hers, his yoni against hers. One-hot encoding turns a 12x12 table into 144 binary statements
averaging 55 couples each, most of which cannot clear a support floor and none of which can borrow
strength from the others. That is why numerology contributed nothing until the floor was dropped, and
why dropping the floor then admitted 445 noisy columns.

THE FIX, which is how matchmaking tables have always been read. A traditional almanac does not treat
"Rat with Dragon" as unrelated to "Rat with Monkey" — the Rat has a character of its own, so does the
Dragon, and the CELL is a correction on top of both. Model it that way: shrink each cell toward its own
row and column marginals, in proportion to how little evidence the cell has.

    cell(i,j) = [ n_ij * p_ij + k * (row_i + col_j - grand) ] / (n_ij + k)

A cell seen 500 times speaks for itself; a cell seen 3 times says almost exactly what its row and column
already said. One continuous statement per table replaces 144 binary ones, uses every couple in the
corpus, and still reads as doctrine: "the Chinese animal table puts this pairing above average".

THE LEAK THIS AVOIDS. The cell estimates read the label, so an encoder fitted once on all the training
rows and then cross-validated would be scoring rows it had already seen. fit() therefore takes only a
fold's training rows and transform() applies that encoder to the held-out ones, exactly as with
orientation.
"""
import numpy as np
import pandas as pd

SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
ANIM = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster",
        "Dog", "Pig"]
NADI = [0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2]
GANA = [0,1,2,1,0,1,0,0,2,2,1,1,0,2,0,2,0,2,2,1,1,0,2,2,1,1,0]
YONI = [0,1,2,3,3,4,5,5,6,6,7,7,8,9,8,9,10,4,11,12,12,13,1,13,10,2,0]


def _dsum(n):
    s = 0
    while n:
        s += n % 10; n //= 10
    return s


def _red(n, keep=(11, 22, 33)):
    while n > 9 and n not in keep:
        n = _dsum(n)
    return n


def _red1(n):
    while n > 9:
        n = _dsum(n)
    return n


def _jdn(y, m, d):
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def categories(df, Z=None, split=None):
    """(his_index, her_index) per couple for each named pair table."""
    ya = pd.to_numeric(df.dob_a.str[:4]).to_numpy(int); ma = pd.to_numeric(df.dob_a.str[5:7]).to_numpy(int)
    da = pd.to_numeric(df.dob_a.str[8:10]).to_numpy(int)
    yb = pd.to_numeric(df.dob_b.str[:4]).to_numpy(int); mb = pd.to_numeric(df.dob_b.str[5:7]).to_numpy(int)
    db = pd.to_numeric(df.dob_b.str[8:10]).to_numpy(int)
    ja = np.array([_jdn(y, m, d) for y, m, d in zip(ya, ma, da)])
    jb = np.array([_jdn(y, m, d) for y, m, d in zip(yb, mb, db)])
    out = {}
    lp = lambda y, m, d: _red(_red1(y) + _red1(m) + _red1(d))
    LPV = {v: i for i, v in enumerate([1,2,3,4,5,6,7,8,9,11,22,33])}
    out["life path"] = (np.array([LPV.get(lp(y,m,d),0) for y,m,d in zip(ya,ma,da)]),
                        np.array([LPV.get(lp(y,m,d),0) for y,m,d in zip(yb,mb,db)]), 12)
    out["birthday number"] = (np.array([_red1(d)-1 for d in da]), np.array([_red1(d)-1 for d in db]), 9)
    out["Chinese animal"] = ((ya - 4) % 12, (yb - 4) % 12, 12)
    out["Chinese element"] = (((ya - 4) % 10) // 2, ((yb - 4) % 10) // 2, 5)
    out["Bazi day master"] = (((ja + 49) % 60) % 10, ((jb + 49) % 60) % 10, 10)
    out["Maya day sign"] = ((ja + 159) % 260 % 20, (jb + 159) % 260 % 20, 20)
    out["Maya tone"] = ((ja + 159) % 260 % 13, (jb + 159) % 260 % 13, 13)
    if Z is not None and split is not None:
        A = Z[f"theta_a_{split}"]; B = Z[f"theta_b_{split}"]
        bod = list(Z["bodies"]); bi = {b: i for i, b in enumerate(bod)}
        for b in ("sun", "moon", "venus", "mars"):
            sa = np.nan_to_num(A[:, bi[b]] // 30, nan=0).astype(int) % 12
            sb = np.nan_to_num(B[:, bi[b]] // 30, nan=0).astype(int) % 12
            out[f"{b} sign"] = (sa, sb, 12)
        nka = np.nan_to_num(A[:, bi["moon"]] // (360/27), nan=0).astype(int) % 27
        nkb = np.nan_to_num(B[:, bi["moon"]] // (360/27), nan=0).astype(int) % 27
        out["nakshatra"] = (nka, nkb, 27)
        out["Vedic nadi"] = (np.array([NADI[i] for i in nka]), np.array([NADI[i] for i in nkb]), 3)
        out["Vedic gana"] = (np.array([GANA[i] for i in nka]), np.array([GANA[i] for i in nkb]), 3)
        out["Vedic yoni"] = (np.array([YONI[i] for i in nka]), np.array([YONI[i] for i in nkb]), 14)
    return out


class TableEncoder:
    """One shrunk compatibility table per doctrine, fitted on training rows only."""

    def __init__(self, k=25.0):
        self.k = k
        self.tab = {}
        self.grand = 0.5
        self.names = []

    def fit(self, cats, y):
        self.grand = float(y.mean())
        self.tab, self.names = {}, []
        for nm, (ia, ib, K) in cats.items():
            n_ij = np.zeros((K, K)); s_ij = np.zeros((K, K))
            np.add.at(n_ij, (ia, ib), 1.0)
            np.add.at(s_ij, (ia, ib), y)
            n_i = n_ij.sum(1, keepdims=True); s_i = s_ij.sum(1, keepdims=True)
            n_j = n_ij.sum(0, keepdims=True); s_j = s_ij.sum(0, keepdims=True)
            row = (s_i + self.k * self.grand) / (n_i + self.k)     # his side, shrunk to the grand mean
            col = (s_j + self.k * self.grand) / (n_j + self.k)     # her side
            add = row + col - self.grand                            # what the two margins alone predict
            cell = (s_ij + self.k * add) / (n_ij + self.k)          # the cell corrects the margins
            self.tab[nm] = np.clip(cell - self.grand, -0.5, 0.5)    # centred: 0 means "as expected"
            self.names.append(f"table[{nm}]")
        return self

    def transform(self, cats):
        cols = []
        for nm in self.names:
            key = nm[6:-1]
            ia, ib, _ = cats[key]
            cols.append(self.tab[key][ia, ib].astype(np.float32))
        return np.column_stack(cols) if cols else np.zeros((0, 0), np.float32)
