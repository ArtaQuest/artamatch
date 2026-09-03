"""round2_board.py — the exhaustive pseudo-body round as one markdown board.
Merges every sweep log (Kaggle batches + the local remainder), the proxy flags, and the combined
model results when present. Deltas are against each log's OWN control (paired)."""
import glob, json, os, re
from collections import Counter
H = os.path.expanduser("~")
res = {}
for f in glob.glob(f"{H}/.artamatch-dev/kaggle/out/sweep*/out/run.log") + glob.glob(f"{H}/.artamatch-dev/kaggle/out/rest*/out/run.log") + [f"{H}/.artamatch-dev/sweep_local.log"]:
    if not os.path.exists(f): continue
    c = None; local = {}
    for line in open(f, errors="replace"):
        m = re.match(r"SWEEP (\S+) nested=([\d.]+) within=([\d.]+)", line.strip())
        if not m: continue
        n, a, w = m.group(1), float(m.group(2)), float(m.group(3))
        if n == "control": c = (a, w)
        else: local[n] = (a, w)
    c = c or (0.6911, 0.5659)
    for n, (a, w) in local.items(): res[n] = (round(a - c[0], 4), round(w - c[1], 4), a, w)
prox = {r["name"]: r for r in json.load(open(f"{H}/.artamatch-dev/round2_proxies.json"))}
man = {s["name"]: s for s in json.load(open(f"{H}/.artamatch-dev/tilldeath_wt3/systems_all_manifest.json"))["systems"]}
rows = sorted(res.items(), key=lambda kv: -kv[1][1])
print(f"# Round 2 — every pseudo-body, added alone to the lean bank (5 folds, paired control)\n")
print(f"tested {len(res)} of {len(man)} · flags: {dict(Counter(prox[n]['flag'] for n in res if n in prox))}\n")
def fmt(n, r):
    p = prox.get(n, {}); return f"| {n} | {man.get(n, {}).get('n', '?')} | {r[0]:+.4f} | {r[1]:+.4f} | {p.get('era_auc', 0):.2f} | {p.get('flag', '?')} |"
print("## Top 25 by within-era delta\n\n| pseudo-body | N | Δ pooled | Δ within-era | era AUC | flag |\n|---|---|---|---|---|---|")
for n, r in rows[:25]: print(fmt(n, r))
print("\n## Top 15 by pooled delta\n\n| pseudo-body | N | Δ pooled | Δ within-era | era AUC | flag |\n|---|---|---|---|---|---|")
for n, r in sorted(res.items(), key=lambda kv: -kv[1][0])[:15]: print(fmt(n, r))
clean = [(n, r) for n, r in rows if prox.get(n, {}).get("flag") == "clean"]
import statistics
print(f"\n## The clean {len(clean)}: Δ pooled mean {statistics.mean(r[0] for _, r in clean):+.4f} (max {max(r[0] for _, r in clean):+.4f}) · Δ within-era mean {statistics.mean(r[1] for _, r in clean):+.4f} (max {max(r[1] for _, r in clean):+.4f})")
p = f"{H}/.artamatch-dev/round2_results.json"
if os.path.exists(p):
    R = json.load(open(p))
    print("\n## Combined models (10 folds, validated, clean pseudo-bodies only)\n\n| model | nested | within-era | K |\n|---|---|---|---|")
    for k, lab in (("all_worthy", f"planets + {len(R.get('worthy', []))} worthy pseudo-bodies"), ("all_control", "planets only (control)"),
                   ("fast_model", f"Sun–Saturn + {len(R.get('within_pos', []))} within-era-positive pseudo-bodies"), ("fast_control", "Sun–Saturn alone (control)")):
        v = R.get(k)
        if v: print(f"| {lab} | {v['nested']:.4f} | {v['within']:.4f} | {v.get('K')} |")
