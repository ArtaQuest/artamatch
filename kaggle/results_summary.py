"""results_summary.py — every nested run in a corpus directory, one line each, sorted by AUC.

Reads report_nested_*.json (full runs: nested AUC + deploy K + lambda) and ablate_*.json (outer
estimate only). Tags are the run's full configuration, so nothing here can be confused with
anything else. Run with AQ_DIR pointing at the corpus directory.
"""
import glob, json, os
D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt"))
rows = []
for f in glob.glob(f"{D_}/report_nested_*.json"):
    j = json.load(open(f)); tag = os.path.basename(f)[len("report_nested_"):-5]
    rows.append((j["nested_auc"], tag, f"K={j['deploy']['K']} rl={j['deploy']['rl']} fixed-ref={j['deploy']['fixed_cv_reference']}"))
for f in glob.glob(f"{D_}/ablate_*.json"):
    j = json.load(open(f))
    rows.append((j["nested_auc"], j["tag"], f"outer-only · {len(j['per_fold'])} folds"))
rows.sort(reverse=True)
print(f"{os.path.basename(D_)}: {len(rows)} runs\n")
print("| nested AUC | configuration | notes |\n|---|---|---|")
for auc, tag, note in rows:
    print(f"| {auc:.4f} | `{tag}` | {note} |")
