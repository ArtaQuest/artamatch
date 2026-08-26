"""audit_corpus.py — extraction & label audit of the remarriage corpus.
1. The funnel, gate by gate, with counts.
2. The same-partner duplicate-year hazard: couples labeled divorced ONLY because their own marriage
   appears twice with different start years.
3. Split integrity: no marriage component may span train/test; no person either.
4. Phases alignment: recomputed charts must match phases.npz rows.
"""
import glob, os, re, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from build_remarriage import render, qid, ART, NAT, MISSING
SRC = os.path.expanduser("~/.artamatch-dev/marriages")
OUT = os.path.expanduser("~/.artamatch-dev/remar_sh")

fr = [pd.read_csv(f, dtype=str) for f in sorted(glob.glob(os.path.join(SRC, "d*.csv")))]
d = pd.concat(fr, ignore_index=True)
for c in ("a", "b", "cause", "asex"):
    d[c] = d[c].map(qid)
print(f"FUNNEL")
print(f"  raw statements                         {len(d):>9,}")
yr = lambda s: pd.to_numeric(s.astype(str).str.extract(r"^[+-]?(\d{4})")[0], errors="coerce").replace(0, np.nan)
d["sy"] = yr(d.start); d["ady"] = yr(d.adeath)
d["dob"] = [render(v, p) for v, p in zip(d.adob, d.aprec)]
print(f"  with a start year                      {int(d.sy.notna().sum()):>9,}  "
      f"({int(d.sy.isna().sum()):,} lost — no start date on the statement)")
per = (d.sort_values("dob").drop_duplicates("a").set_index("a")[["dob", "ady", "asex"]])
print(f"  distinct persons (?a side)             {len(per):>9,}")

# same-partner duplicate start years — the hazard
mar = pd.concat([d[["a", "b", "sy"]].rename(columns={"a": "p", "b": "q"}),
                 d[["b", "a", "sy"]].rename(columns={"b": "p", "a": "q"})], ignore_index=True)
mar = mar[mar.p.str.startswith("Q")].drop_duplicates(["p", "q", "sy"])
mm = mar[mar.sy.notna() & (mar.q != "")]
g = mm.groupby(["p", "q"]).sy.agg(["min", "max", "count"])
dup = g[g["count"] > 1]
gap = (dup["max"] - dup["min"])
print(f"\nSAME-PARTNER MULTIPLE START YEARS (per ordered person-spouse pair)")
print(f"  pairs with 2+ distinct start years     {len(dup):>9,}")
print(f"    year gap == 1 (almost surely the same wedding, cross-page discrepancy) {int((gap == 1).sum()):,}")
print(f"    year gap 2-4                                                          {int(gap.between(2, 4).sum()):,}")
print(f"    year gap >= 5 (plausibly a real re-wedding)                           {int((gap >= 5).sum()):,}")

# how many SHIPPED positives hinge on it: recompute y_alive with same-partner extra years collapsed to min
idx_all, idx_fix = {}, {}
for p, gr in mm.groupby("p"):
    idx_all[p] = gr.sy.values
    idx_fix[p] = gr.groupby("q").sy.min().values          # one start per distinct spouse
solo = mar[mar.sy.notna() & (mar.q == "")]
for p, gr in solo.groupby("p"):                            # spouse-unknown marriages still count
    idx_all[p] = np.concatenate([idx_all.get(p, np.empty(0)), gr.sy.values])
    idx_fix[p] = np.concatenate([idx_fix.get(p, np.empty(0)), gr.sy.values])
bdy = per.ady.reindex(d.b).to_numpy()
def y_alive(idx, pa, pb, s, da, db):
    def one(p, other_death):
        v = idx.get(p)
        if v is None or not np.isfinite(s) or not np.isfinite(other_death):
            return False
        return bool(np.any((v > s) & (v < other_death)))
    return one(pa, db) or one(pb, da)
da_ = d.ady.to_numpy()
ya_all = np.array([y_alive(idx_all, pa, pb, s, da, db)
                   for pa, pb, s, da, db in zip(d.a, d.b, d.sy, da_, bdy)])
ya_fix = np.array([y_alive(idx_fix, pa, pb, s, da, db)
                   for pa, pb, s, da, db in zip(d.a, d.b, d.sy, da_, bdy)])
flip = ya_all & ~ya_fix
print(f"  statements labeled DIVORCE under the shipped rule      {int(ya_all.sum()):>7,}")
print(f"  ...that flip to natural once duplicates collapse       {int(flip.sum()):>7,}")

# which is more truthful? validate BOTH against explicit causes
expl = d.cause.isin(ART | NAT).to_numpy()
truth = d.cause.isin(ART).to_numpy().astype(int)
for nm, pred in (("shipped rule", ya_all.astype(int)), ("duplicates collapsed", ya_fix.astype(int))):
    p_, t_ = pred[expl], truth[expl]
    tp = int(((p_ == 1) & (t_ == 1)).sum()); fp = int(((p_ == 1) & (t_ == 0)).sum())
    fn = int(((p_ == 0) & (t_ == 1)).sum())
    print(f"    {nm:<22} precision {tp / max(1, tp + fp):.1%}  recall {tp / max(1, tp + fn):.1%}"
          f"  (on {int(expl.sum()):,} cause-carrying statements)")

# split integrity on the shipped files
tri = pd.read_csv(f"{OUT}/_train_ids.csv", dtype=str); tei = pd.read_csv(f"{OUT}/_test_ids.csv", dtype=str)
ptr = set(tri.pid_a) | set(tri.pid_b); pte = set(tei.pid_a) | set(tei.pid_b)
print(f"\nSPLIT INTEGRITY")
print(f"  persons in both halves: {len(ptr & pte)}")
parent = {}
def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
allp = pd.concat([tri[["pid_a", "pid_b"]], tei[["pid_a", "pid_b"]]])
for a, b in zip(allp.pid_a, allp.pid_b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb
ctr = {find(a) for a in tri.pid_a}; cte = {find(a) for a in tei.pid_a}
print(f"  marriage components spanning both halves: {len(ctr & cte)}")

# phases alignment: recompute five random rows' charts from the dob strings
tr = pd.read_csv(f"{OUT}/train.csv", dtype=str)
Z = np.load(f"{OUT}/phases.npz", allow_pickle=True)
bodies = [str(b) for b in Z["bodies"]]
TA = np.asarray(Z["theta_a_train"], float)
sys.path.insert(0, os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs"))
import sweshim as SW, scorer as SC
SW.load(os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/ephem4.bin"),
        os.path.expanduser("~/.artaquest-dev/wt/am-pages/docs/tables.json"))
SW.set_sid_mode(SW.SIDM_LAHIRI)
SC.init(SW)
rng = np.random.default_rng(3)
full = tr[(tr.dob_a.str[:4] >= "1900") & (tr.dob_a.str[5:7] != "00") & (tr.dob_a.str[8:10] != "00")].index
worst = 0.0
for ri in rng.choice(full, 8, replace=False):
    y_, m_, dd = (int(x) for x in tr.iloc[ri].dob_a.split("-"))
    C = SC.chart(y_, m_, dd)
    for b in ("sun", "moon", "venus", "saturn"):
        tv = TA[ri, bodies.index(b)]
        if np.isfinite(tv):
            worst = max(worst, abs(((tv - C[b] + 180) % 360) - 180))
print(f"\nPHASES ALIGNMENT (8 rows x 4 bodies vs the page ephemeris)")
print(f"  worst |delta| {worst:.4f} deg — {'ALIGNED (ephemeris-compression scale)' if worst < 0.02 else 'MISALIGNED'}")
