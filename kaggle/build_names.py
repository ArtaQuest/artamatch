"""build_names.py — NAME-NUMEROLOGY VARIANTS as pseudo-bodies (competition lens "names-variants").

Writes AQ_DIR/systems_names.npz (same shape as systems.npz: theta_a_sys, theta_b_sys in degrees,
names, nstates, plus has_label_a/b for REPORTING ONLY — never a feature). Read by
comp_names-variants.py under AQ_NAMES=1. Never touches systems.npz.

The name is the Wikidata English label (~/.artamatch-dev/labels.csv), romanised with unidecode so
every script gets letters. Three name PARTS x two letter SYSTEMS x five QUANTITIES = 30 bodies:
  parts     : first  = first token · surname = last token that is not a roman numeral and has
              >= 3 letters (falls back to the first token) · full = every letter of the label
              (parenthetical and the part after a comma — titles — are dropped first)
  systems   : Pythagorean (A=1..I=9, J=1..) · Chaldean (classical 1-8 table, no 9)
  quantities: expression (all letters, reduced 1-9: 9 states) · soul urge (vowels AEIOUY, 9) ·
              personality (consonants, 9) · hidden passion (the most frequent letter VALUE in the
              part; ties -> the smallest; Pythagorean 9 states, Chaldean 8) · master expression
              (reduction STOPS at 11/22/33, which stay their own states: circle of 12 =
              1..9,11,22,33 in that order)
A person WITHOUT a label (or with no Latin letters) gets a uniformly RANDOM state on every circle,
seeded by the pid — zero information, so "has a label" (a record-depth quantity) can never enter
the model through a fixed fallback state. Coverage is printed and stored for the report.
"""
import os, re, zlib, numpy as np, pandas as pd
from unidecode import unidecode
D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
LAB = os.path.expanduser(os.environ.get("AQ_LABELS", "~/.artamatch-dev/labels.csv"))
PYTH = {c: (i % 9) + 1 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
CHAL = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [1,2,3,4,5,8,3,5,1,1,2,3,4,5,7,8,1,2,3,4,6,6,6,5,1,7]))
VOWELS = set("AEIOUY")
ROMAN = re.compile(r"^[IVXLCDM]+$")
MASTER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33]          # the 12-state master circle, in this order

def red9(t):
    while t > 9: t = sum(int(c) for c in str(t))
    return t
def red_master(t):
    while t > 9 and t not in (11, 22, 33): t = sum(int(c) for c in str(t))
    return t
def letters(s): return "".join(c for c in unidecode(s or "").upper() if "A" <= c <= "Z")
def parts(label):
    base = re.sub(r"\([^)]*\)", " ", label or "").split(",")[0]
    toks = [t for t in (letters(t) for t in base.split()) if t]
    if not toks: return None
    first = toks[0]
    sur = [t for t in toks[1:] if not ROMAN.match(t) and len(t) >= 3]
    return {"first": first, "surname": sur[-1] if sur else first, "full": "".join(toks)}
def quantities(L, table, nhid):
    vals = [table[c] for c in L]
    counts = np.bincount(vals, minlength=nhid + 1)[1:]
    hidden = int(np.argmax(counts)) + 1                                         # ties -> smallest
    return {"expr": red9(sum(vals)) - 1,
            "soul": red9(sum(table[c] for c in L if c in VOWELS) or 9) - 1,
            "pers": red9(sum(table[c] for c in L if c not in VOWELS) or 9) - 1,
            "hidden": hidden - 1,
            "master": MASTER.index(red_master(sum(vals)))}
SYS = []
for part in ("first", "surname", "full"):
    for sysname, nhid in (("pyth", 9), ("chal", 8)):
        for q, N in (("expr", 9), ("soul", 9), ("pers", 9), ("hidden", nhid), ("master", 12)):
            SYS.append((f"nm_{part}_{sysname}_{q}", N))
NST = [N for _, N in SYS]

def states(label, pid):
    P = parts(label)
    if P is None:
        rng = np.random.default_rng(zlib.crc32(pid.encode()))
        return [int(rng.integers(0, N)) for _, N in SYS], False
    out = []
    for part in ("first", "surname", "full"):
        for table, nhid in ((PYTH, 9), (CHAL, 8)):
            qs = quantities(P[part], table, nhid)
            out += [qs[q] for q in ("expr", "soul", "pers", "hidden", "master")]
    return out, True

if __name__ == "__main__":
    full = pd.read_csv(f"{D_}/full.csv", dtype=str)
    labels = dict(pd.read_csv(LAB, dtype=str).fillna("").itertuples(index=False, name=None)) if os.path.exists(LAB) else {}
    def side(pcol):
        S, H = [], []
        for pid in full[pcol]:
            st, has = states(labels.get(pid, ""), pid); S.append(st); H.append(has)
        S = np.array(S, np.int64); H = np.array(H, bool)
        return (S + 1) * (360.0 / np.array(NST, np.float64)), H
    A, HA = side("pid_a"); B, HB = side("pid_b")
    print(f"  names: {len(labels):,} labels · labelled: him {HA.mean():.1%} · her {HB.mean():.1%} · both {(HA & HB).mean():.1%} of {len(full):,} couples (unlabelled = random state)")
    for k, (nm, N) in enumerate(SYS[:10]):
        cnt = np.bincount(np.rint(A[HA, k] * N / 360.0).astype(int) - 1, minlength=N)
        print(f"  {nm:<28} N={N:<2} his labelled-state histogram {cnt.tolist()}")
    np.savez_compressed(f"{D_}/systems_names.npz", theta_a_sys=A, theta_b_sys=B,
                        names=np.array([n for n, _ in SYS]), nstates=np.array(NST),
                        has_label_a=HA, has_label_b=HB)
    print(f"wrote {D_}/systems_names.npz · {len(SYS)} name pseudo-bodies x {len(full):,} couples")
