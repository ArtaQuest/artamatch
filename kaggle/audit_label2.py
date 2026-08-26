"""Label rule v2 candidates + recoverable-couple count.
Rule variants on same-partner repeat weddings: (all kept = shipped) / (all collapsed) / (collapse gap<=4,
keep gap>=5 as a true divorce signal). Recovery: missing-start couples where both partners are mono-married
are definitive negatives."""
import glob, os, re, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from build_remarriage import render, qid, ART, NAT, MISSING
SRC = os.path.expanduser("~/.artamatch-dev/marriages")

fr = [pd.read_csv(f, dtype=str) for f in sorted(glob.glob(os.path.join(SRC, "d*.csv")))]
d = pd.concat(fr, ignore_index=True)
for c in ("a", "b", "cause", "asex"):
    d[c] = d[c].map(qid)
yr = lambda s: pd.to_numeric(s.astype(str).str.extract(r"^[+-]?(\d{4})")[0], errors="coerce").replace(0, np.nan)
d["sy"] = yr(d.start); d["ady"] = yr(d.adeath)
d["dob"] = [render(v, p) for v, p in zip(d.adob, d.aprec)]
per = (d.sort_values("dob").drop_duplicates("a").set_index("a")[["dob", "ady", "asex"]])

mar = pd.concat([d[["a", "b", "sy"]].rename(columns={"a": "p", "b": "q"}),
                 d[["b", "a", "sy"]].rename(columns={"b": "p", "a": "q"})], ignore_index=True)
mar = mar[mar.p.str.startswith("Q")].drop_duplicates(["p", "q", "sy"])
mm = mar[mar.sy.notna() & (mar.q != "")]
solo = mar[mar.sy.notna() & (mar.q == "")]

def build_idx(collapse):
    """collapse: None=shipped · 'all' · 'smart' (gap<=4 collapsed to min, >=5 kept)"""
    idx = {}
    for p, gr in mm.groupby("p"):
        if collapse is None:
            v = gr.sy.values
        elif collapse == "all":
            v = gr.groupby("q").sy.min().values
        else:
            vs = []
            for _, g2 in gr.groupby("q"):
                ys = np.sort(g2.sy.values)
                kept = [ys[0]]
                for y2 in ys[1:]:
                    if y2 - kept[-1] >= 5:
                        kept.append(y2)
                vs += kept
            v = np.array(vs)
        idx[p] = v
    for p, gr in solo.groupby("p"):
        idx[p] = np.concatenate([idx.get(p, np.empty(0)), gr.sy.values])
    return idx

bdy = per.ady.reindex(d.b).to_numpy()
da_ = d.ady.to_numpy()
expl = d.cause.isin(ART | NAT).to_numpy()
truth = d.cause.isin(ART).to_numpy().astype(int)
def score(idx, nm):
    def one(p, s, other_death):
        v = idx.get(p)
        if v is None or not np.isfinite(s) or not np.isfinite(other_death):
            return False
        return bool(np.any((v > s) & (v < other_death)))
    pred = np.array([one(pa, s, db) or one(pb, s, da)
                     for pa, pb, s, da, db in zip(d.a, d.b, d.sy, da_, bdy)]).astype(int)
    p_, t_ = pred[expl], truth[expl]
    tp = int(((p_ == 1) & (t_ == 1)).sum()); fp = int(((p_ == 1) & (t_ == 0)).sum())
    fn = int(((p_ == 0) & (t_ == 1)).sum())
    print(f"  {nm:<44} precision {tp/max(1,tp+fp):.1%}  recall {tp/max(1,tp+fn):.1%}  positives {int(pred.sum()):,}")
    return pred

print("LABEL VARIANTS (validated on the 13,323 cause-carrying statements)")
score(build_idx(None), "shipped: every distinct (p,q,year) counts")
score(build_idx("all"), "collapse: one start per spouse")
score(build_idx("smart"), "smart: gap<=4 collapsed, re-wedding >=5y kept")

# recoverable negatives: missing-start couples where BOTH partners have exactly one marriage statement
nmar_any = pd.concat([d[["a", "b"]].rename(columns={"a": "p", "b": "q"}),
                      d[["b", "a"]].rename(columns={"b": "p", "a": "q"})], ignore_index=True)
nmar_any = nmar_any[nmar_any.p.str.startswith("Q")].drop_duplicates(["p", "q"])
cnt = nmar_any.groupby("p").size()
miss = d[d.sy.isna()].copy()
mono_a = miss.a.map(cnt).fillna(9) == 1
mono_b = miss.b.map(cnt).fillna(9) == 1
rec = miss[mono_a & mono_b].copy()
print(f"\nRECOVERABLE MISSING-START COUPLES (both partners mono-married => definitive negative)")
print(f"  missing-start statements: {len(miss):,} · both mono-married: {len(rec):,}")
bdob = per.dob.reindex(rec.b).to_numpy(); bsex = per.asex.reindex(rec.b).to_numpy()
rec["dob_b"] = bdob; rec["bsex"] = bsex
rec = rec[(rec.dob != MISSING) & pd.notna(rec.dob_b) & (rec.dob_b != MISSING)]
MALE, FEM = "Q6581097", "Q6581072"
rec = rec[((rec.asex == MALE) & (rec.bsex == FEM)) | ((rec.asex == FEM) & (rec.bsex == MALE))]
ya = pd.to_numeric(rec.dob.str[:4], errors="coerce").replace(0, np.nan)
yb = pd.to_numeric(rec.dob_b.str[:4], errors="coerce").replace(0, np.nan)
rec = rec[(ya < 1950) & (yb < 1950) & (np.abs(ya - yb) <= 60) & ya.between(1400, 1950) & yb.between(1400, 1950)]
rec["pair"] = [f"{min(x,y)}|{max(x,y)}" for x, y in zip(rec.a, rec.b)]
rec = rec.drop_duplicates("pair")
# exclude couples already shipped (they have a start-dated statement elsewhere)
shipped = set()
for f in ("_train_ids.csv", "_test_ids.csv"):
    t = pd.read_csv(os.path.expanduser(f"~/.artamatch-dev/remar_sh/{f}"), dtype=str)
    shipped |= {f"{min(x,y)}|{max(x,y)}" for x, y in zip(t.pid_a, t.pid_b)}
rec = rec[~rec.pair.isin(shipped)]
print(f"  after dob/gender/window/dedupe gates and minus already-shipped: {len(rec):,} NEW couples, all label 0")
