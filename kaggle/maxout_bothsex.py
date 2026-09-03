"""maxout_bothsex.py — max out the nested AUC on the BOTH-SEXES target (operator 2026-09-03:
"fit whether they had both sex or not, finalize everything on that, max out its auc").

Every arm is the same nested procedure with one thing changed, each with its own paired control,
on ~/.artamatch-dev/sex_both (28,315 couples with two or more sexed children, 70.1% both).
Reported beside the confound that dominates the target: family size alone scores 0.7516.
Writes ~/.artamatch-dev/bothsex_maxout.json.
"""
import json, os, re, subprocess, time
H = os.path.expanduser("~"); D = f"{H}/.artamatch-dev/sex_both"
ARMS = [
    ("lean_validated",   {"AQ_ONLY_FAM": "XY", "AQ_ONLY_HARM": "1", "AQ_VALIDATE": "1", "AQ_SHORTLIST": "5"}),
    ("lean_plain",       {"AQ_ONLY_FAM": "XY", "AQ_ONLY_HARM": "1"}),
    ("xy_all_harmonics", {"AQ_ONLY_FAM": "XY", "AQ_VALIDATE": "1", "AQ_SHORTLIST": "5"}),
    ("full_bank",        {"AQ_VALIDATE": "1", "AQ_SHORTLIST": "5"}),
    ("full_bank_plain",  {}),
    ("k64",              {"AQ_ONLY_FAM": "XY", "AQ_ONLY_HARM": "1", "AQ_VALIDATE": "1", "AQ_SHORTLIST": "5", "AQ_KMAX": "64"}),
    ("systems_lean",     {"AQ_ONLY_FAM": "XY", "AQ_ONLY_HARM": "1", "AQ_VALIDATE": "1", "AQ_SHORTLIST": "5",
                          "AQ_SYSTEMS": "1", "AQ_SYSTEMS_FILE": "systems_all.npz"}),
    ("systems_full",     {"AQ_VALIDATE": "1", "AQ_SHORTLIST": "5", "AQ_SYSTEMS": "1", "AQ_SYSTEMS_FILE": "systems_all.npz"}),
]
def run(tag, env, script="fit_nested.py"):
    e = dict(os.environ, AQ_DIR=D, AQ_KMAX=env.get("AQ_KMAX", "32"), AQ_ORTHO="1")
    e.update(env)
    log = f"{H}/.artamatch-dev/bothsex_{tag}.log"; t0 = time.time()
    with open(log, "w") as lf:
        subprocess.run([f"{H}/.artamatch-venv/bin/python", script], env=e, stdout=lf, stderr=subprocess.STDOUT, cwd=f"{H}/Studio/artamatch/kaggle")
    txt = open(log, errors="replace").read()
    g = lambda pat: (re.search(pat, txt) or [None, None])[1]
    out = {"nested": float(g(r"NESTED AUC[^:]*: ([\d.]+)") or "nan"), "within": float(g(r"WITHIN-ERA AUC[^:]*: ([\d.]+)") or "nan"),
           "K": g(r"K by 10-fold CV[^:]*: (\d+)"), "bank": g(r"= ([\d,]+) phasors"), "minutes": round((time.time() - t0) / 60, 1)}
    print(f"  {tag:18s} nested {out['nested']:.4f} · within-era {out['within']:.4f} · K {out['K']} · bank {out['bank']} · {out['minutes']} min", flush=True)
    return out
res = {}
for tag, env in ARMS:
    res[tag] = run(tag, env)
    json.dump(res, open(f"{H}/.artamatch-dev/bothsex_maxout.json", "w"), indent=1)
best = max((v["nested"], k) for k, v in res.items() if v["nested"] == v["nested"])
print(f"BEST ARM: {best[1]} at {best[0]:.4f}", flush=True)
print("== BOTHSEX MAXOUT DONE ==", flush=True)
