"""sweep_batch.py — one fit_nested.py ablation per pseudo-body, in a loop, plus the control.

    AQ_SWEEP_NAMES=vedic_tithi,western_mansion AQ_DIR=... python sweep_batch.py

For every name in AQ_SWEEP_NAMES it runs fit_nested.py (same directory as this file, same AQ_DIR)
as a subprocess with

    AQ_SYSTEMS=1 AQ_SYSTEMS_FILE=systems_all.npz AQ_SYS_ONLY=<name>
    AQ_KMAX=32 AQ_NOUTER=5 AQ_NO_INNER=1 AQ_ABLATE=1 AQ_ORTHO=1 AQ_ONLY_FAM=XY AQ_ONLY_HARM=1

and once more with AQ_SYSTEMS unset (the control: the 13 planets alone, same settings). Every
other AQ_* variable is inherited (AQ_DIR, AQ_CPU, AQ_VALIDATE ...); AQ_KMAX / AQ_NOUTER may be
overridden from the environment (the local smoke uses AQ_KMAX=2 AQ_NOUTER=2). It parses the
'NESTED AUC ... X [tag]' and 'WITHIN-ERA AUC ... Y' lines from each run's output, prints

    SWEEP <name> nested=X within=Y

per run (name 'control' for the planets-only run) and a final JSON document (one line, prefixed
'SWEEP_JSON ') to stdout. Each run's full log goes to AQ_DIR/sweep_<name>.log so a failure can be
read; a run that fails or whose lines cannot be parsed reports nested=None within=None and its
error, and the loop continues. Order: control first, then the names as given.

    AQ_SWEEP_CONTROL=0    skip the control run
    AQ_SWEEP_FIT=<path>   a different fitter script (default fit_nested.py beside this file)
"""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
D_ = os.path.expanduser(os.environ.get("AQ_DIR", "~/.artamatch-dev/tilldeath_wt3"))
FIT = os.environ.get("AQ_SWEEP_FIT") or os.path.join(HERE, "fit_nested.py")
NAMES = [x.strip() for x in os.environ.get("AQ_SWEEP_NAMES", "").split(",") if x.strip()]
CONTROL = os.environ.get("AQ_SWEEP_CONTROL", "1") == "1"
BASE = {"AQ_KMAX": os.environ.get("AQ_KMAX", "32"), "AQ_NOUTER": os.environ.get("AQ_NOUTER", "5"),
        "AQ_NO_INNER": "1", "AQ_ABLATE": "1", "AQ_ORTHO": "1", "AQ_ONLY_FAM": "XY", "AQ_ONLY_HARM": "1"}
RE_NESTED = re.compile(r"NESTED AUC[^:]*:\s*([0-9.]+)\s*\[([^\]]*)\]")
RE_WITHIN = re.compile(r"WITHIN-ERA AUC[^:]*:\s*([0-9.]+)")


def run_one(name):
    env = dict(os.environ)
    env.update(BASE)
    env["AQ_DIR"] = D_
    if name == "control":
        env.pop("AQ_SYSTEMS", None); env.pop("AQ_SYSTEMS_FILE", None); env.pop("AQ_SYS_ONLY", None)
    else:
        env["AQ_SYSTEMS"], env["AQ_SYSTEMS_FILE"], env["AQ_SYS_ONLY"] = "1", "systems_all.npz", name
    t0 = time.time()
    rec = {"name": name, "nested": None, "within": None, "tag": None, "seconds": None, "error": None,
           "log": f"{D_}/sweep_{name}.log"}
    try:
        p = subprocess.run([sys.executable, FIT], env=env, cwd=HERE, capture_output=True, text=True)
        out = p.stdout + p.stderr
        with open(rec["log"], "w") as f:
            f.write(out)
        mn, mw = RE_NESTED.search(out), RE_WITHIN.search(out)
        if mn:
            rec["nested"], rec["tag"] = float(mn.group(1)), mn.group(2)
        if mw:
            rec["within"] = float(mw.group(1))
        if p.returncode != 0:
            rec["error"] = f"exit {p.returncode}: " + out.strip().splitlines()[-1][:300] if out.strip() else f"exit {p.returncode}"
        elif not (mn and mw):
            rec["error"] = "could not parse NESTED/WITHIN-ERA lines"
    except Exception as e:      # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
    rec["seconds"] = round(time.time() - t0, 1)
    print(f"SWEEP {name} nested={rec['nested']} within={rec['within']}", flush=True)
    return rec


if __name__ == "__main__":
    if not NAMES and not CONTROL:
        raise SystemExit("AQ_SWEEP_NAMES is empty")
    order = (["control"] if CONTROL else []) + NAMES
    results = [run_one(nm) for nm in order]
    ctrl = next((r for r in results if r["name"] == "control"), None)
    doc = {"dir": D_, "fit": FIT, "settings": BASE, "names": NAMES, "control": ctrl,
           "runs": [r for r in results if r["name"] != "control"]}
    if ctrl and ctrl["nested"] is not None:
        for r in doc["runs"]:
            if r["nested"] is not None:
                r["delta_nested"] = round(r["nested"] - ctrl["nested"], 5)
            if r["within"] is not None and ctrl["within"] is not None:
                r["delta_within"] = round(r["within"] - ctrl["within"], 5)
    print("SWEEP_JSON " + json.dumps(doc), flush=True)
