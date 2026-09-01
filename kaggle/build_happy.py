"""build_happy.py — the HAPPY corpus: 1,590 marriages an LLM judged one at a time.

Each row is a Wikipedia description a judge read against RUBRIC6 and called happy or unhappy; the
8,410 it called neither are left out, because "the record does not say" is not a third class of
marriage. y = 1 is happy.

This is the smallest and most directly-judged target in the project, and the one whose label owes
nothing to Wikidata's structured fields — so it cannot be predicted from how well documented a couple
is, which every other target in this corpus can. That is exactly why it is worth fitting: an earlier
pass found birth years score 0.5186 on it, against 0.5910 on the older quality label.
"""
import os
import numpy as np, pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
OUT = os.path.expanduser("~/.artamatch-dev/happy")
MISSING = "0000-00-00"
os.makedirs(OUT, exist_ok=True)
v = pd.read_csv(f"{BIO}/round0_all_verdicts.csv", usecols=["pid_a", "pid_b", "v", "dob_a", "dob_b"])
d = v[v.v.isin(["happy", "unhappy"])].copy()
d = d[~d.dob_a.astype(str).str.contains("-00") & ~d.dob_b.astype(str).str.contains("-00")]
d = d.drop_duplicates(["pid_a", "pid_b"]).reset_index(drop=True)
d["y"] = (d.v == "happy").astype(int)
d["start"] = MISSING
print(f"  {len(d):,} judged couples · happy {int(d.y.sum()):,} · unhappy {int((d.y == 0).sum()):,}")
d.assign(ended_in_divorce=d.y)[["dob_a", "dob_b", "start", "ended_in_divorce"]].to_csv(
    f"{OUT}/train.csv", index=False)
d[["pid_a", "pid_b"]].assign(y_rule=0, y_alive=0).to_csv(f"{OUT}/_train_ids.csv", index=False)
d.to_csv(f"{OUT}/full.csv", index=False)
te = d.head(20).copy(); te.insert(0, "id", [f"r{i:06d}" for i in range(len(te))])
te[["id", "dob_a", "dob_b", "start"]].to_csv(f"{OUT}/test.csv", index=False)
te.assign(ended_in_divorce=0)[["id", "ended_in_divorce"]].to_csv(f"{OUT}/solution.csv", index=False)
print(f"  wrote {OUT}")
