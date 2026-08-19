"""kernel_job.py — one Kaggle kernel = one shard of the edition-IV member build. Config comes from env (baked into
the pushed kernel as the first lines): AQ_JOB in {trad, sid, sidmem}; AQ_MODULES / AQ_SHARD / AQ_TAG as needed."""
import glob, os, shutil, subprocess, sys, time
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
CODE = next(p for p in glob.glob("/kaggle/input/**/kernel_job.py", recursive=True)); CODE = os.path.dirname(CODE)
W = "/kaggle/working/code"; shutil.copytree(CODE, W, dirs_exist_ok=True); os.chdir(W)
log("code at", CODE)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "kerykeion==5.12.9", "PyJHora==4.8.7", "timezonefinder", "lightgbm"], check=False)
os.environ.update({"AQ_OUT": "/kaggle/working", "AQ_GPU": "1" if (shutil.which("nvidia-smi") and subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0) else "0", "AQ_PHASES": f"{W}/phases_iv.npz", "AQ_SRC": f"{W}/data"})
job = os.environ.get("AQ_JOB", "trad"); env = dict(os.environ)
if job == "trad":
    r = subprocess.run([sys.executable, "-u", "research/sidereal/tradition_members.py"], env=env)
elif job == "sid":
    # the sidereal builder reads dob_dad/dob_mom: point it at the dad/mom-named copies of the same files
    d = "/kaggle/working/dm"; os.makedirs(d, exist_ok=True); shutil.copy(f"{W}/data/train_dm.csv", f"{d}/train.csv"); shutil.copy(f"{W}/data/test_dm.csv", f"{d}/test.csv")
    env["AQ_SRC"] = d; r = subprocess.run([sys.executable, "-u", f"{W}/research/sidereal/build_sidereal.py"], env=env, cwd=f"{W}/research/sidereal")
else:
    raise SystemExit(f"unknown AQ_JOB {job}")
log("exit", r.returncode); print(sorted(os.listdir("/kaggle/working")))
sys.exit(r.returncode)
