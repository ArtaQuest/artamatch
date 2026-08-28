"""bio_agree.py — how far apart are two judgements of the same marriages?

Compares two label files item by item: exact agreement, agreement on the ordinal scale
(toxic < neutral < happy), the confusion matrix, and — the number that actually matters for the
modelling target — agreement on the sharp contrast, happy vs toxic.
Usage: bio_agree.py <a.json> <b.json>
"""
import json, sys
from collections import Counter

A = {o["id"]: o for o in json.load(open(sys.argv[1]))}
B = {o["id"]: o for o in json.load(open(sys.argv[2]))}
ids = [i for i in A if i in B]
ORD = {"toxic": 0, "neutral": 1, "happy": 2}
same = [i for i in ids if A[i]["label"] == B[i]["label"]]
off1 = [i for i in ids if abs(ORD[A[i]["label"]] - ORD[B[i]["label"]]) == 1]
flip = [i for i in ids if abs(ORD[A[i]["label"]] - ORD[B[i]["label"]]) == 2]
print(f"  {len(ids)} marriages judged twice")
print(f"    exact agreement      {len(same)/len(ids):.1%}  ({len(same)})")
print(f"    one step apart       {len(off1)/len(ids):.1%}  ({len(off1)})")
print(f"    opposite (happy<->toxic) {len(flip)/len(ids):.1%}  ({len(flip)})")
sharp = [i for i in ids if A[i]["label"] != "neutral" and B[i]["label"] != "neutral"]
if sharp:
    ok = sum(1 for i in sharp if A[i]["label"] == B[i]["label"])
    print(f"    where both call it non-neutral: {ok}/{len(sharp)} = {ok/len(sharp):.0%} agree")
# Cohen's kappa
n = len(ids)
po = len(same) / n
ca, cb = Counter(A[i]["label"] for i in ids), Counter(B[i]["label"] for i in ids)
pe = sum(ca[k] * cb[k] for k in ORD) / (n * n)
print(f"    Cohen's kappa        {(po - pe) / (1 - pe):.3f}")
print("  confusion (rows = first file, cols = second):")
print("            " + "".join(f"{k:>9}" for k in ORD))
for r in ORD:
    row = [sum(1 for i in ids if A[i]["label"] == r and B[i]["label"] == c) for c in ORD]
    print(f"    {r:<8}" + "".join(f"{v:>9}" for v in row))
dis = [i for i in ids if A[i]["label"] != B[i]["label"]][:6]
if dis:
    print("  examples of disagreement:")
    for i in dis:
        print(f"    {i}: {A[i]['label']:<8} vs {B[i]['label']:<8} | {A[i].get('evidence','')[:70]}")
