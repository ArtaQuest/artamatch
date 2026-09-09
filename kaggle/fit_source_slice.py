"""fit_source_slice.py — does the model see every KIND of separation, or only one?

Half the positive class now comes from the remarriage rule, whose own agreement with an explicit
P1534 cause was measured at 77.6% in build_separation.py — which is why that file refused to use it
as a label source at all. It is in this corpus on the operator's instruction, so the honest thing is
to report whether the model predicts remarriage-only positives as well as documented divorces.

For each evidence source, the model's out-of-fold score is ranked over THAT source's positives
against ALL negatives. A source the model reads poorly is a source contributing noise; a source it
reads far better than the rest is the one the headline AUC is really about.
"""
import json, os
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
oof = np.load(f"{D_}/oof_final.npy")
full = pd.read_csv(f"{D_}/full.csv")
y = full.y.to_numpy().astype(int)
src = full.src.fillna("").to_numpy()
neg = oof[y == 0]
print(f"  {len(full):,} couples · {int(y.sum()):,} positives · {len(neg):,} negatives\n")
print(f"  {'evidence':<12}{'n':>8}{'AUC vs all negatives':>24}")
rows = {}
for tag in ("P1534", "end-date", "judge", "text", "infid", "remarry"):
    m = np.array([tag in s for s in src]) & (y == 1)
    if m.sum() < 50: continue
    a = roc_auc_score(np.r_[np.ones(int(m.sum())), np.zeros(len(neg))], np.r_[oof[m], neg])
    rows[tag] = {"n": int(m.sum()), "auc": float(a)}
    print(f"  {tag:<12}{int(m.sum()):>8,}{a:>24.4f}")
only_re = (y == 1) & (src == "remarry")
if only_re.sum() > 50:
    a = roc_auc_score(np.r_[np.ones(int(only_re.sum())), np.zeros(len(neg))], np.r_[oof[only_re], neg])
    rows["remarry_only"] = {"n": int(only_re.sum()), "auc": float(a)}
    print(f"\n  {'remarry ONLY':<12}{int(only_re.sum()):>8,}{a:>24.4f}   (no other evidence at all)")
doc = (y == 1) & np.array([("P1534" in s or "end-date" in s or "judge" in s) for s in src])
a = roc_auc_score(np.r_[np.ones(int(doc.sum())), np.zeros(len(neg))], np.r_[oof[doc], neg])
rows["documented"] = {"n": int(doc.sum()), "auc": float(a)}
print(f"  {'documented':<12}{int(doc.sum()):>8,}{a:>24.4f}   (P1534, end-date or the judge)")
json.dump(rows, open(f"{D_}/report_source_slice.json", "w"), indent=1)
print(f"\n  saved report_source_slice.json")
