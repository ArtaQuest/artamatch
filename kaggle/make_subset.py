"""make_subset.py — a corpus directory restricted to couples where BOTH spouses are deeply documented.

AQ_MIN_SITELINKS=N (default 5) keeps couples whose two people each have at least N Wikidata
sitelinks. Writes AQ_OUT with full.csv, _train_ids.csv, train.csv, test.csv and a row-filtered
phases.npz, so every standard fitter runs on it unchanged. The sitelink count is used ONLY to
choose rows — it never enters a model.
"""
import os, numpy as np, pandas as pd
SRC = os.path.expanduser(os.environ.get("AQ_SRC", "~/.artamatch-dev/tilldeath_wt2"))
OUT = os.path.expanduser(os.environ.get("AQ_OUT", "~/.artamatch-dev/tilldeath_deep"))
MIN = int(os.environ.get("AQ_MIN_SITELINKS", "5"))
sl = pd.read_csv(os.path.expanduser("~/.artamatch-dev/sitelinks.csv"), dtype={"pid": str})
sl = dict(zip(sl.pid, pd.to_numeric(sl.sitelinks, errors="coerce").fillna(0)))
full = pd.read_csv(f"{SRC}/full.csv", dtype=str)
ids = pd.read_csv(f"{SRC}/_train_ids.csv", dtype=str)
keep = np.array([(sl.get(a, 0) >= MIN) and (sl.get(b, 0) >= MIN) for a, b in zip(full.pid_a, full.pid_b)])
os.makedirs(OUT, exist_ok=True)
full[keep].to_csv(f"{OUT}/full.csv", index=False)
ids[keep].to_csv(f"{OUT}/_train_ids.csv", index=False)
for f in ("train.csv", "test.csv", "solution.csv"):
    if os.path.exists(f"{SRC}/{f}"):
        d = pd.read_csv(f"{SRC}/{f}", dtype=str)
        (d[keep] if len(d) == len(full) else d).to_csv(f"{OUT}/{f}", index=False)
Z = np.load(f"{SRC}/phases.npz", allow_pickle=True)
np.savez_compressed(f"{OUT}/phases.npz", **{k: (Z[k][keep] if (hasattr(Z[k], "shape") and Z[k].shape[:1] == (len(full),)) else Z[k]) for k in Z.files})
y = full[keep].y.astype(int)
print(f"min sitelinks {MIN}: kept {keep.sum():,} of {len(full):,} couples · y=1 {y.mean():.1%}")
