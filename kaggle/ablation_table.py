"""ablation_table.py — one markdown table from the nested ablation JSONs (ablate_*.json).

Every row is the SAME procedure (stepwise inside every fold, K fixed, 5 outer folds) with one
thing removed; the delta is against the baseline run of that same procedure — never against the
10-fold deploy number, which is a different estimator.
"""
import glob, json, os, sys
D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt"))
runs = {}
# tags read k32_<what>_o5; the baseline is k32_o5 — the glob once matched only the baseline
for f in glob.glob(f"{D_}/ablate_k32_*o5.json"):
    j = json.load(open(f)); runs[j["tag"]] = j["nested_auc"]
base = runs.get("k32_o5")
if base is None:
    sys.exit("no baseline ablate_k32_o5.json yet")
rows = []
for tag, auc in runs.items():
    if tag == "k32_o5": continue
    what = tag.replace("k32_", "").replace("_o5", "")
    kind = ("body" if what.startswith("noBody") else "family" if what.startswith("noFam") else "harmonic" if what.startswith("noHarm") else "other")
    name = what.replace("noBody", "").replace("noFam", "").replace("noHarm", "k=")
    rows.append((kind, name, auc, base - auc))
rows.sort(key=lambda r: (r[0], -r[3]))
print(f"baseline (same procedure, 5 outer folds, K=32): **{base:.4f}**\n")
print("| removed | kind | nested AUC | cost |\n|---|---|---|---|")
for kind, name, auc, cost in rows:
    print(f"| {name} | {kind} | {auc:.4f} | {cost:+.4f} |")
