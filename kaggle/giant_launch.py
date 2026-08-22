"""
giant_launch.py — package the code and data, then run giant_ensemble.py on a Kaggle GPU kernel.

One kernel, not a fan-out: the leave-one-out ablation needs every family present at once, so sharding it would
mean each shard could only measure what it happens to hold. The whole thing is ~30 boosted fits over ~100k rows
and at most 663 features, which is comfortably inside a 12-hour GPU session.

  python giant_launch.py push     package + upload the dataset, push the kernel, print its URL
  python giant_launch.py status   how the run is doing
  python giant_launch.py collect  pull the outputs down
"""
import json
import os
import shutil
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV = os.path.expanduser("~/.artamatch-dev")
PY = os.path.expanduser("~/.artamatch-venv/bin/python")
STAGE = os.path.join(DEV, "giantkg")
SLUG = "artamatch-giant"
OUTDIR = os.path.join(DEV, "giant_out")


def account():
    """ArtaSwitch decides which account runs this — never hardcode one, the pool tracks GPU hours."""
    for p in (os.path.expanduser("~/Studio/artaquest/tools/ticket-agent/kaggle-accounts.mjs"),):
        if os.path.exists(p):
            r = subprocess.run(["node", p, "pick"], capture_output=True, text=True, timeout=120)
            a = r.stdout.strip().splitlines()[-1].strip() if r.stdout.strip() else ""
            if a:
                return a
    raise SystemExit("ArtaSwitch did not name an account — refusing to pick one myself")


def cfgdir(acct):
    d = os.path.join(DEV, f"kgcfg_{acct}")
    os.makedirs(d, exist_ok=True)
    shutil.copy(os.path.expanduser(f"~/.kaggle/kaggle.{acct}.json"), os.path.join(d, "kaggle.json"))
    os.chmod(os.path.join(d, "kaggle.json"), 0o600)
    return d


def kag(acct, code, timeout=1800):
    """Run one Kaggle API call in a SUBPROCESS. The client authenticates AT IMPORT, so a second account in the
    same process would act as the first — that has already cost a running kernel here."""
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, "KAGGLE_CONFIG_DIR": cfgdir(acct)})
    return (r.stdout + r.stderr).strip()


def stage(acct):
    """Everything the kernel needs, in one dataset: the data, the ephemeris, the shim and the family modules."""
    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(STAGE, exist_ok=True)
    src = os.path.join(DEV, "aq9c"); feat = os.path.join(DEV, "aq9feat")
    for f, dst in ((os.path.join(src, "train.csv"), "train.csv"), (os.path.join(src, "test.csv"), "test.csv"),
                   (os.path.join(feat, "phases.npz"), "phases.npz")):
        if not os.path.exists(f):
            raise SystemExit(f"missing {f} — the rebuild chain has not finished")
        shutil.copy(f, os.path.join(STAGE, dst))
    code = os.path.join(STAGE, "code"); os.makedirs(code, exist_ok=True)
    shutil.copytree(os.path.join(REPO, "research", "sidereal"), os.path.join(code, "sidereal"),
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.npz", "*.log"))
    shutil.copy(os.path.join(REPO, "kaggle", "giant_ensemble.py"), os.path.join(code, "giant_ensemble.py"))
    web = os.path.join(STAGE, "web"); os.makedirs(web, exist_ok=True)
    for f in ("sweshim.py", "ephem4.bin", "tables.json"):
        p = os.path.join(REPO, "web", f)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(web, f))
    json.dump({"title": "ArtaMatch giant ensemble", "id": f"{acct}/{SLUG}",
               "licenses": [{"name": "CC0-1.0"}]}, open(os.path.join(STAGE, "dataset-metadata.json"), "w"), indent=1)
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(STAGE) for f in fs)
    print(f"  staged {size/1e6:.1f} MB at {STAGE}")
    return STAGE


KERNEL = '''import glob, os, shutil, subprocess, sys, time
T0=time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
subprocess.run([sys.executable,"-m","pip","install","-q","lunardate","convertdate","xgboost"],check=False)
IN=next(p for p in glob.glob("/kaggle/input/**/giant_ensemble.py",recursive=True))
CODE=os.path.dirname(IN); ROOT=os.path.dirname(CODE)
W="/kaggle/working/code"; shutil.copytree(CODE,W,dirs_exist_ok=True)
for d in glob.glob(os.path.join(ROOT,"..","web")) + glob.glob("/kaggle/input/**/web",recursive=True):
    if os.path.isdir(d): shutil.copytree(d,"/kaggle/working/web",dirs_exist_ok=True); break
os.environ.update({"AQ_DATA":"/kaggle/input","AQ_CODE":f"{W}/sidereal","AQ_WEB":"/kaggle/working/web","AQ_OUT":"/kaggle/working"})
log("nvidia-smi:", subprocess.run(["nvidia-smi","--query-gpu=name","--format=csv,noheader"],capture_output=True,text=True).stdout.strip() or "none")
r=subprocess.run([sys.executable,"-u",f"{W}/giant_ensemble.py"],env=dict(os.environ))
log("exit",r.returncode)
shutil.rmtree(W,ignore_errors=True); shutil.rmtree("/kaggle/working/web",ignore_errors=True)
print(sorted(os.listdir("/kaggle/working")))
'''


def push():
    acct = account(); print(f"ArtaSwitch picked: {acct}")
    d = stage(acct)
    print("uploading the dataset (this is the slow part)")
    out = kag(acct, f'''
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi(); api.authenticate()
try:
    api.dataset_create_version({json.dumps(d)}, "giant ensemble inputs", dir_mode="zip")
    print("VERSIONED")
except Exception as e:
    if "not found" in str(e).lower() or "404" in str(e):
        api.dataset_create_new({json.dumps(d)}, dir_mode="zip"); print("CREATED")
    else: raise
''', timeout=3600)
    print(" ", out.splitlines()[-1] if out else "?")
    kd = os.path.join(DEV, "giantkernel"); shutil.rmtree(kd, ignore_errors=True); os.makedirs(kd)
    open(os.path.join(kd, "kernel.py"), "w").write(KERNEL)
    json.dump({"id": f"{acct}/artamatch-giant-ensemble", "title": "artamatch-giant-ensemble",
               "code_file": "kernel.py", "language": "python", "kernel_type": "script", "is_private": True,
               "enable_gpu": True, "enable_internet": True,
               "dataset_sources": [f"{acct}/{SLUG}"], "competition_sources": [], "kernel_sources": [],
               "model_sources": []}, open(os.path.join(kd, "kernel-metadata.json"), "w"), indent=1)
    print("pushing the kernel")
    out = kag(acct, f'''
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi(); api.authenticate()
r=api.kernels_push({json.dumps(kd)})
print("URL:", getattr(r,"url",None), "| ERROR:", getattr(r,"error",None))
''')
    print(" ", out.splitlines()[-1] if out else "?")
    # kernels_push can return an EMPTY url and quietly keep the previous version — say so rather than assume
    if "URL: None" in out or "URL: |" in out:
        print("  !! the push returned no URL — the kernel may NOT have been updated; check the web UI")
    json.dump({"account": acct, "slug": "artamatch-giant-ensemble"}, open(os.path.join(DEV, "giant_run.json"), "w"))
    print(f"  https://www.kaggle.com/code/{acct}/artamatch-giant-ensemble")


def status():
    r = json.load(open(os.path.join(DEV, "giant_run.json")))
    out = kag(r["account"], f'''
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi(); api.authenticate()
s=api.kernels_status("{r['account']}/{r['slug']}")
print(getattr(s,"status",s), "|", getattr(s,"failureMessage",""))
''')
    print(out.splitlines()[-1] if out else "?")


def collect():
    r = json.load(open(os.path.join(DEV, "giant_run.json")))
    os.makedirs(OUTDIR, exist_ok=True)
    out = kag(r["account"], f'''
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi(); api.authenticate()
api.kernels_output("{r['account']}/{r['slug']}", {json.dumps(OUTDIR)})
print("OK")
''', timeout=3600)
    print(out.splitlines()[-1] if out else "?")
    rep = os.path.join(OUTDIR, "contribution_report.txt")
    if os.path.exists(rep):
        print(open(rep).read())


if __name__ == "__main__":
    {"push": push, "status": status, "collect": collect}[sys.argv[1] if len(sys.argv) > 1 else "status"]()
