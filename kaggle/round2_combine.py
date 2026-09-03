"""round2_combine.py — after the exhaustive pseudo-body sweep: merge every result, pick the worthy
ones, and run the two combined models on the local GPU, 10 folds with inner CV:
  (a) ALL-WORTHY: lean planet bank + every pseudo-body with pooled delta >= +0.0003 or within-era
      delta >= +0.0010 (vs its own kernel's control), validated selection; control = planets only.
  (b) FAST-BODY: planets restricted to Sun..Saturn + every pseudo-body with a positive within-era
      delta (cap 40, by within-era delta), validated; control = the fast planets alone.
Writes ~/.artamatch-dev/round2_results.json.
"""
import glob, json, os, re, subprocess, sys, time
H = os.path.expanduser("~"); D = f"{H}/.artamatch-dev/tilldeath_wt3"
res, ctrls = {}, []
for f in glob.glob(f"{H}/.artamatch-dev/kaggle/out/sweep*/out/run.log") + glob.glob(f"{H}/.artamatch-dev/kaggle/out/rest*/out/run.log") + [f"{H}/.artamatch-dev/sweep_local.log"]:
    if not os.path.exists(f): continue
    c = None; local = {}
    for line in open(f, errors="replace"):
        m = re.match(r"SWEEP (\S+) nested=([\d.]+) within=([\d.]+)", line.strip())
        if not m: continue
        n, a, w = m.group(1), float(m.group(2)), float(m.group(3))
        if n == "control": c = (a, w)
        else: local[n] = (a, w)
    if c is None: c = (0.6911, 0.5659)
    ctrls.append(c)
    for n, (a, w) in local.items(): res[n] = {"nested": a, "within": w, "d_pooled": round(a - c[0], 4), "d_within": round(w - c[1], 4)}
# ERA PROXIES OUT (round2_proxies.json): 42 pseudo-bodies predict "born after 1900" at AUC > 0.60
# — the Uranian hypotheticals at 0.9999, Eris, the Long Count may/katun, Pluto/Neptune signs. Any
# of them in a combined model is the calendar through a side door; the fast-body model above all.
prox = {r["name"]: r["flag"] for r in json.load(open(f"{H}/.artamatch-dev/round2_proxies.json"))}
res = {n: r for n, r in res.items() if prox.get(n, "clean") == "clean"}
print(f"after dropping era/depth proxies: {len(res)} clean pseudo-bodies", flush=True)
rows = sorted(res.items(), key=lambda kv: -kv[1]["d_within"])
worthy = [n for n, r in rows if r["d_pooled"] >= 0.0003 or r["d_within"] >= 0.0010]
within_pos = [n for n, r in rows if r["d_within"] > 0][:40]
print(f"merged {len(res)} pseudo-bodies · worthy {len(worthy)} · within-era positive {len([n for n,r in rows if r['d_within']>0])} (cap 40)", flush=True)
FAST = "sun,moon,mercury,venus,mars,jupiter,saturn"
def run(tagname, env):
    e = dict(os.environ, AQ_DIR=D, AQ_KMAX="32", AQ_ORTHO="1", AQ_ONLY_FAM="XY", AQ_ONLY_HARM="1", AQ_VALIDATE="1", AQ_SHORTLIST="5")
    e.update(env)
    log = f"{H}/.artamatch-dev/round2_{tagname}.log"
    t0 = time.time()
    with open(log, "w") as lf:
        subprocess.run([f"{H}/.artamatch-venv/bin/python", "fit_nested.py"], env=e, stdout=lf, stderr=subprocess.STDOUT, cwd=f"{H}/Studio/artamatch/kaggle")
    txt = open(log, errors="replace").read()
    g = lambda pat: (re.search(pat, txt) or [None, None])[1]
    out = {"nested": float(g(r"NESTED AUC[^:]*: ([\d.]+)") or "nan"), "within": float(g(r"WITHIN-ERA AUC[^:]*: ([\d.]+)") or "nan"),
           "K": g(r"K by 10-fold CV[^:]*: (\d+)"), "minutes": round((time.time() - t0) / 60, 1), "log": log}
    print(f"  {tagname}: nested {out['nested']} · within-era {out['within']} · K {out['K']} · {out['minutes']} min", flush=True); return out
results = {"worthy": worthy, "within_pos": within_pos, "sweep": res}
print("== ALL-WORTHY (planets + worthy pseudo-bodies), 10-fold validated ==", flush=True)
results["all_worthy"] = run("all_worthy", {"AQ_SYSTEMS": "1", "AQ_SYSTEMS_FILE": "systems_all.npz", "AQ_SYS_ONLY": ",".join(worthy)}) if worthy else None
print("== CONTROL (planets only), 10-fold validated ==", flush=True)
results["all_control"] = run("all_control", {})
print("== FAST-BODY MODEL (Sun..Saturn + within-era-positive pseudo-bodies), 10-fold validated ==", flush=True)
results["fast_model"] = run("fast_model", {"AQ_ONLY_BODIES": FAST, "AQ_SYSTEMS": "1", "AQ_SYSTEMS_FILE": "systems_all.npz", "AQ_SYS_ONLY": ",".join(within_pos)}) if within_pos else None
print("== FAST-BODY CONTROL (Sun..Saturn alone) ==", flush=True)
results["fast_control"] = run("fast_control", {"AQ_ONLY_BODIES": FAST})
json.dump(results, open(f"{H}/.artamatch-dev/round2_results.json", "w"), indent=1)
print("== ROUND2 COMBINE DONE ==", flush=True)
