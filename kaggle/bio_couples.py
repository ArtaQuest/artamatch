"""bio_couples.py — every ENDED marriage with both birth dates, from the count-verified harvest.
Output ~/.artamatch-dev/bio/couples.csv: pid_a/dob_a (the man), pid_b/dob_b (the woman), start year,
both death years, the structural remarriage label for reference, and each date's precision.
'Ended' = both born before 1950, or both have a recorded death."""
import glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from build_remarriage import render, qid, MISSING
SRC = os.path.expanduser(os.environ.get("AQ_MAR", "~/.artamatch-dev/marriages2"))
OUT = os.path.expanduser("~/.artamatch-dev/bio")
MALE, FEM = "Q6581097", "Q6581072"

os.makedirs(OUT, exist_ok=True)
files = sorted(glob.glob(os.path.join(SRC, "d*.csv")))
d = pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)
for c in ("a", "b", "cause", "asex"):
    d[c] = d[c].map(qid)
print(f"  {len(d):,} statements from {len(files)} verified decade files", flush=True)
yr = lambda s: pd.to_numeric(s.astype(str).str.extract(r"^[+-]?(\d{4})")[0], errors="coerce").replace(0, np.nan)
d["sy"] = yr(d.start); d["ady"] = yr(d.adeath)
d["dob"] = [render(v, p) for v, p in zip(d.adob, d.aprec)]
d["prec"] = pd.to_numeric(d.aprec, errors="coerce")

per = d.sort_values("dob").drop_duplicates("a").set_index("a")[["dob", "ady", "asex", "prec"]]
print(f"  {len(per):,} distinct persons", flush=True)

# one row per couple, male first, both dobs present
b = d.b
out = pd.DataFrame({"pa": d.a.to_numpy(), "pb": b.to_numpy(), "dob_a": d.dob.to_numpy(),
                    "dob_b": per.dob.reindex(b).to_numpy(), "asex": d.asex.to_numpy(),
                    "bsex": per.asex.reindex(b).to_numpy(), "prec_a": d.prec.to_numpy(),
                    "prec_b": per.prec.reindex(b).to_numpy(), "sy": d.sy.to_numpy(),
                    "da": d.ady.to_numpy(), "db": per.ady.reindex(b).to_numpy(),
                    "cause": d.cause.to_numpy()})
out = out[(out.dob_a != MISSING) & pd.notna(out.dob_b) & (out.dob_b != MISSING)]
keep = ((out.asex == MALE) & (out.bsex == FEM)) | ((out.asex == FEM) & (out.bsex == MALE))
out = out[keep].copy()
sw = out.asex == FEM
for x, y in (("pa", "pb"), ("dob_a", "dob_b"), ("prec_a", "prec_b"), ("da", "db")):
    xa, xb = out[x].to_numpy().copy(), out[y].to_numpy().copy()
    out[x] = np.where(sw, xb, xa); out[y] = np.where(sw, xa, xb)
out["pair"] = [f"{min(x,y)}|{max(x,y)}" for x, y in zip(out.pa, out.pb)]
out = out.sort_values("sy").drop_duplicates("pair")
ya = pd.to_numeric(out.dob_a.str[:4], errors="coerce").replace(0, np.nan)
yb = pd.to_numeric(out.dob_b.str[:4], errors="coerce").replace(0, np.nan)
ended = ((ya < 1950) & (yb < 1950)) | (np.isfinite(out.da.to_numpy(float)) & np.isfinite(out.db.to_numpy(float)))
out = out[ended & (np.abs(ya - yb) <= 60) & ya.between(1400, 2010) & yb.between(1400, 2010)].copy()
out["fullprec"] = ((out.prec_a >= 11) & (out.prec_b >= 11)).astype(int)
out.rename(columns={"pa": "pid_a", "pb": "pid_b"})[
    ["pid_a", "pid_b", "dob_a", "dob_b", "fullprec", "sy", "da", "db", "cause"]].to_csv(
    f"{OUT}/couples.csv", index=False)
print(f"  {len(out):,} ended marriages with both birth dates ({int(out.fullprec.sum()):,} full precision)")
print(f"  distinct persons in them: {len(set(out.pa) | set(out.pb)):,}")
