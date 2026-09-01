"""build_infid.py — the INFIDELITY target, from the 10k one-by-one judged dataset.

A judge read each couple's Wikipedia description against RUBRIC2 and recorded, per couple, whether
the record shows an infidelity. That flag is the label here: y = 1 where the prose says so.

Like the happy target and unlike every Wikidata-derived one, this label is produced by READING, so it
cannot be predicted from how complete a couple's structured record is — the failure mode that made
the divorce target reach 0.86 from one chart. It is also very unbalanced (about 4%), so every fit is
class-weighted and the baselines are measured on exactly the same rows.
"""
import os
import numpy as np, pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
OUT = os.path.expanduser("~/.artamatch-dev/infid")
MISSING = "0000-00-00"
os.makedirs(OUT, exist_ok=True)

q = pd.read_csv(f"{BIO}/marriage_quality_binary.csv")
jj = pd.read_csv(f"{BIO}/judged.csv")
truthy = lambda s: s.astype(str).str.lower().isin(["true", "1", "1.0", "yes"])
flag = {}
for a, b, f in zip(jj.pid_a, jj.pid_b, truthy(jj.infidelity)):
    flag[(a, b)] = flag.get((a, b), False) or bool(f)
d = q[~q.dob_a.astype(str).str.contains("-00") & ~q.dob_b.astype(str).str.contains("-00")].copy()
d = d[d.dob_a.notna() & d.dob_b.notna()].drop_duplicates(["pid_a", "pid_b"]).reset_index(drop=True)
d["y"] = [int(flag.get((a, b), False) or flag.get((b, a), False) or r == "infidelity")
          for a, b, r in zip(d.pid_a, d.pid_b, d.reason)]
d["start"] = MISSING
print(f"  {len(d):,} judged couples with full-precision dates")
print(f"  infidelity recorded: {int(d.y.sum()):,} ({d.y.mean():.2%})")
d.assign(ended_in_divorce=d.y)[["dob_a", "dob_b", "start", "ended_in_divorce"]].to_csv(
    f"{OUT}/train.csv", index=False)
d[["pid_a", "pid_b"]].assign(y_rule=0, y_alive=0).to_csv(f"{OUT}/_train_ids.csv", index=False)
d[["pid_a", "pid_b", "dob_a", "dob_b", "y", "reason", "good", "confidence"]].to_csv(
    f"{OUT}/full.csv", index=False)
te = d.head(20).copy(); te.insert(0, "id", [f"r{i:06d}" for i in range(len(te))])
te[["id", "dob_a", "dob_b", "start"]].to_csv(f"{OUT}/test.csv", index=False)
te.assign(ended_in_divorce=0)[["id", "ended_in_divorce"]].to_csv(f"{OUT}/solution.csv", index=False)
print(f"  wrote {OUT}")
