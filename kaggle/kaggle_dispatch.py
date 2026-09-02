"""kaggle_dispatch.py — run a fit_nested-style experiment as a Kaggle GPU kernel (operator 2026-09-02:
"you can also use the Kaggle GPUs"). One kernel per entry; entries run in parallel across the pool.

  python kaggle_dispatch.py datasets            # (re)create/version the code + corpus datasets
  python kaggle_dispatch.py push <slug> 'ENV=.. ENV=..' [script.py] [extra files...]
  python kaggle_dispatch.py status <slug>
  python kaggle_dispatch.py fetch <slug>        # download the trimmed output (reports + log) to ~/.artamatch-dev/kaggle/out/<slug>

Traps honoured (memory): the kaggle client authenticates at IMPORT — the account is whatever
~/.kaggle/kaggle.json says when this process starts, via ARTASWITCH; never swapped mid-run. The
kernel copies the read-only input corpus into /kaggle/working/corpus (fit_nested writes beside its
inputs), runs, then DELETES that copy — the output download drags all of /kaggle/working.
"""
import json, os, subprocess, sys, time, shutil
HOME = os.path.expanduser("~")
K = f"{HOME}/.artamatch-dev/kaggle"
USER = json.load(open(f"{HOME}/.kaggle/kaggle.json"))["username"]
CODE_DS, CORPUS_DS = f"{USER}/artamatch-comp-code", f"{USER}/artamatch-comp-corpus"
def sh(*a, **k):
    r = subprocess.run(a, capture_output=True, text=True, timeout=k.get("timeout", 600))
    return r.returncode, (r.stdout + r.stderr).strip()

def datasets():
    for path, slug, title in ((f"{K}/code", CODE_DS, "ArtaMatch competition code"), (f"{K}/corpus", CORPUS_DS, "ArtaMatch competition corpus")):
        meta = {"title": title, "id": slug, "licenses": [{"name": "CC0-1.0"}]}
        json.dump(meta, open(f"{path}/dataset-metadata.json", "w"))
        rc, out = sh("kaggle", "datasets", "status", slug)
        if rc == 0 and "not found" not in out.lower() and "403" not in out:
            rc, out = sh("kaggle", "datasets", "version", "-p", path, "-m", "update", "--dir-mode", "zip", timeout=1800)
        else:
            rc, out = sh("kaggle", "datasets", "create", "-p", path, "--dir-mode", "zip", timeout=1800)
        print(slug, "->", rc, out[-200:])

RUN_PY = '''
import os, shutil, subprocess, sys, glob, time
T0 = time.time()
src = [d for d in glob.glob("/kaggle/input/*") if "corpus" in d][0]
code = [d for d in glob.glob("/kaggle/input/*") if "code" in d][0]
os.makedirs("/kaggle/working/corpus", exist_ok=True)
for f in os.listdir(src): shutil.copy(os.path.join(src, f), "/kaggle/working/corpus/")
for f in os.listdir(code):
    if f.endswith(".py"): shutil.copy(os.path.join(code, f), "/kaggle/working/")
os.chdir("/kaggle/working")
env = dict(os.environ); env["AQ_DIR"] = "/kaggle/working/corpus"
for kv in __ENV__.split(): k, v = kv.split("=", 1); env[k] = v
print("ENV", {k: v for k, v in env.items() if k.startswith("AQ_")}, flush=True)
with open("/kaggle/working/run.log", "w") as log:
    p = subprocess.Popen([sys.executable, __SCRIPT__], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout: print(line, end="", flush=True); log.write(line)
    p.wait()
# keep only the small results: reports, ablation json, terms, oof; drop the corpus copy and code
keep = ("report_", "ablate_", "maxout_terms", "oof_nested_", "run.log")
os.makedirs("/kaggle/working/out", exist_ok=True)
for f in os.listdir("/kaggle/working/corpus"):
    if f.startswith(keep): shutil.move(os.path.join("/kaggle/working/corpus", f), "/kaggle/working/out/")
shutil.move("/kaggle/working/run.log", "/kaggle/working/out/run.log")
shutil.rmtree("/kaggle/working/corpus")
for f in os.listdir("/kaggle/working"):
    if f.endswith(".py") or f == "__pycache__": (shutil.rmtree if os.path.isdir(f) else os.remove)(f)
print("DONE in %.0fs · rc=%d" % (time.time() - T0, p.returncode), flush=True)
'''
def push(slug, envs, script="fit_nested.py", extra=()):
    d = f"{K}/kernels/{slug}"; shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    # extra files (a competitor's comp_<slug>.py and helpers) ride inside the kernel dir itself
    for x in extra: shutil.copy(x, d)
    body = RUN_PY.replace("__ENV__", json.dumps(envs)).replace("__SCRIPT__", json.dumps(script))
    if extra:
        body = body.replace('os.chdir("/kaggle/working")', 'os.chdir("/kaggle/working")\n' + "".join(
            f'shutil.copy("/kaggle/working/../input/{os.path.basename(x)}", "/kaggle/working/") if os.path.exists("/kaggle/input/{os.path.basename(x)}") else None\n' for x in extra))
    open(f"{d}/run.py", "w").write(body)
    kid = f"{USER}/artamatch-comp-{slug}".lower().replace("_", "-")
    json.dump({"id": kid, "title": f"artamatch-comp-{slug}", "code_file": "run.py", "language": "python",
               "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": False,
               "dataset_sources": [CODE_DS, CORPUS_DS], "competition_sources": [], "kernel_sources": []},
              open(f"{d}/kernel-metadata.json", "w"))
    rc, out = sh("kaggle", "kernels", "push", "-p", d, timeout=600)
    print(slug, "push ->", rc, out[-300:]); return kid
def status(slug):
    kid = f"{USER}/artamatch-comp-{slug}".lower().replace("_", "-")
    rc, out = sh("kaggle", "kernels", "status", kid); print(out); return out
def fetch(slug):
    kid = f"{USER}/artamatch-comp-{slug}".lower().replace("_", "-")
    o = f"{K}/out/{slug}"; os.makedirs(o, exist_ok=True)
    rc, out = sh("kaggle", "kernels", "output", kid, "-p", o, timeout=1200); print(out[-300:])
    lg = f"{o}/out/run.log" if os.path.exists(f"{o}/out/run.log") else f"{o}/run.log"
    if os.path.exists(lg):
        for line in open(lg):
            if "NESTED" in line or "WITHIN-ERA" in line or "VAULT" in line or "Traceback" in line: print(line.rstrip())
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "datasets": datasets()
    elif cmd == "push": push(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "fit_nested.py", sys.argv[5:])
    elif cmd == "status": status(sys.argv[2])
    elif cmd == "fetch": fetch(sys.argv[2])
