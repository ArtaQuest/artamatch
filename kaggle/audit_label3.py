"""THIRD label pass: (1) an INDEPENDENT merge-based reimplementation of 'either partner remarried a
different spouse while both were alive' compared row-by-row with every shipped v3 label; (2) named
historical couples with known outcomes; (3) the overall rates, sliced."""
import glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from build_remarriage import render, qid
SRC = os.path.expanduser("~/.artamatch-dev/marriages")
D = os.path.expanduser("~/.artamatch-dev/remar_sh3")

fr = [pd.read_csv(f, dtype=str) for f in sorted(glob.glob(os.path.join(SRC, "d*.csv")))]
raw = pd.concat(fr, ignore_index=True)
for c in ("a", "b", "cause", "asex"):
    raw[c] = raw[c].map(qid)
yr = lambda s: pd.to_numeric(s.astype(str).str.extract(r"^[+-]?(\d{4})")[0], errors="coerce").replace(0, np.nan)
raw["sy"] = yr(raw.start); raw["ady"] = yr(raw.adeath)
# NOTE: corpus v3 was built from decades 1500-1949 only (the 1950+ files arrived later) — restrict alike
raw = raw[yr(raw.adob) < 1950]
per_death = raw.sort_values("dob" if "dob" in raw else "adob").drop_duplicates("a").set_index("a").ady

# independent implementation: long marriage table -> per-person collapsed (min start per spouse),
# then a MERGE of each couple against each partner's other marriages
mar = pd.concat([raw[["a", "b", "sy"]].rename(columns={"a": "p", "b": "q"}),
                 raw[["b", "a", "sy"]].rename(columns={"b": "p", "a": "q"})], ignore_index=True)
mar = mar[mar.p.str.startswith("Q") & mar.sy.notna()]
named = mar[mar.q != ""].groupby(["p", "q"], as_index=False).sy.min()
unk = mar[mar.q == ""].drop_duplicates(["p", "sy"])[["p", "q", "sy"]]
marc = pd.concat([named, unk], ignore_index=True)

ids = pd.concat([pd.read_csv(f"{D}/_train_ids.csv", dtype=str).assign(half="train"),
                 pd.read_csv(f"{D}/_test_ids.csv", dtype=str).assign(half="test")], ignore_index=True)
tr = pd.read_csv(f"{D}/train.csv", dtype=str); te = pd.read_csv(f"{D}/test.csv", dtype=str)
sol = pd.read_csv(f"{D}/solution.csv", dtype=str)
ship = np.concatenate([tr.ended_in_divorce.to_numpy(), sol.ended_in_divorce.to_numpy()]).astype(int)
assert len(ship) == len(ids)

# couple start year = min collapsed start between the two, either direction
cs = named.set_index(["p", "q"]).sy
def couple_start(a, b):
    v = []
    if (a, b) in cs.index:
        v.append(cs.loc[(a, b)])
    if (b, a) in cs.index:
        v.append(cs.loc[(b, a)])
    return min(v) if v else np.nan
starts = np.array([couple_start(a, b) for a, b in zip(ids.pid_a, ids.pid_b)])
d_a = per_death.reindex(ids.pid_a).to_numpy(float)
d_b = per_death.reindex(ids.pid_b).to_numpy(float)
by_p = {p: g for p, g in marc.groupby("p")}
def indep_label(a, b, s, da, db):
    if not np.isfinite(s):
        return 0                      # recovered mono-married couples: no other marriage exists
    for me, other, odeath in ((a, b, db), (b, a, da)):
        g = by_p.get(me)
        if g is None or not np.isfinite(odeath):
            continue
        others = g[(g.q != other) | (g.q == "")]
        if ((others.sy > s) & (others.sy < odeath)).any():
            return 1
    return 0
indep = np.array([indep_label(a, b, s, da, db)
                  for a, b, s, da, db in zip(ids.pid_a, ids.pid_b, starts, d_a, d_b)])
dis = int((indep != ship).sum())
print(f"TRIPLE-CHECK: independent reimplementation vs shipped labels on all {len(ids):,} v3 couples")
print(f"  disagreements: {dis} ({100 * dis / len(ids):.3f}%)")
if dis:
    bad = ids[indep != ship].head(8)
    for _, r in bad.iterrows():
        print(f"    {r.pid_a} x {r.pid_b} · shipped {ship[ids.index.get_loc(_)]} vs independent")

# named historical couples with known outcomes
KNOWN = [("Q517", "Q157489", 1, "Napoleon x Josephine — divorced 1810, he remarried 1810 while she lived"),
         ("Q937", "Q76346", 1, "Einstein x Mileva Maric — divorced 1919, he remarried while she lived"),
         ("Q9960", "Q231091", 1, "Reagan x Jane Wyman — divorced; remarriage while both lived"),
         ("Q47899", "Q232869", 0, "Grace Kelly x Rainier III — ended by her death 1982"),
         ("Q8007", "Q80976", 0, "Eisenhower x Mamie — ended by his death"),
         ("Q34851", "Q170510", 1, "Elizabeth Taylor x Richard Burton — divorced twice"),
         ("Q1001", "Q1002979", 0, "Gandhi x Kasturba — ended by her death 1944")]
pairset = {(min(a, b), max(a, b)): i for i, (a, b) in enumerate(zip(ids.pid_a, ids.pid_b))}
print("\nNAMED COUPLES")
for a, b, want, desc in KNOWN:
    k = (min(a, b), max(a, b))
    if k in pairset:
        got = int(ship[pairset[k]])
        print(f"  {'OK  ' if got == want else 'MISS'} shipped {got} expected {want} · {desc}")
    else:
        print(f"  (not in v3 — dates/precision gates) · {desc}")

# rates
years = pd.to_numeric(pd.concat([tr.dob_a, te.dob_a]).str[:4]).to_numpy()
print(f"\nRATES (corpus v3, {len(ship):,} full-precision couples)")
print(f"  overall divorce rate (remarried-while-both-alive): {100 * ship.mean():.2f}%")
print(f"  plain remarried-after rate (y_rule sidecar): "
      f"{100 * pd.to_numeric(pd.concat([pd.read_csv(f'{D}/_train_ids.csv', dtype=str).y_rule, pd.read_csv(f'{D}/_test_ids.csv', dtype=str).y_rule])).mean():.2f}%")
for lo, hi in ((1500, 1700), (1700, 1800), (1800, 1850), (1850, 1900), (1900, 1950)):
    m = (years >= lo) & (years < hi)
    if m.sum():
        print(f"  men born {lo}-{hi}: {100 * ship[m].mean():5.2f}%  (n={int(m.sum()):,})")
