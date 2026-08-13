"""
kaggle_sweep.py — move the whole sweep off this laptop and onto Kaggle.

WHY

The laptop cannot do this work. It has 8 cores and it shares them with sixteen coding subagents, a
running audio app and a browser; the load average reached 325 and a sweep that should take twenty
minutes was taking six hours. Kaggle gives a dedicated 4-core / 30 GB session for 12 hours, and — the
reason that matters most here — it ships XGBoost, LightGBM and CatBoost preinstalled, none of which work
on this machine (LightGBM cannot even load its OpenMP library).

WHAT GETS SHIPPED

A Kaggle dataset holds everything the sweep needs, FLAT in one directory, because Kaggle serves only the
dataset root:

    core.py evalx.py run.py trad_*.py     the substrate and all fifteen tradition modules
    ephem-cache.npz                       the precomputed ephemeris, so nothing is recomputed remotely
    with-kids.json                        the couples
    se*.se1                               Swiss Ephemeris files, for the three modules that call swe directly

core.py and run.py read every path from AQ_* environment variables, so the identical files run in both
places with no forking.

THE NOTEBOOK then runs collect -> screen -> deep -> oof -> stack with the full model zoo including the
three boosters, and writes its artefacts to /kaggle/working where they can be pulled back.

Usage:
    /tmp/aqpy/bin/python kaggle_sweep.py push      # build payload, version the dataset, push the notebook
    /tmp/aqpy/bin/python kaggle_sweep.py status    # where is it
    /tmp/aqpy/bin/python kaggle_sweep.py pull      # download the outputs into ./kaggle-out
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EPHE = os.path.expanduser("~/.sweph/ephe")
PAYLOAD = os.path.join(HERE, "kaggle-payload")
OUTDIR = os.path.join(HERE, "kaggle-out")

def _owner():
    """Whoever ArtaSwitch has this Mac authenticated as — never a hardcoded account.

    ArtaSwitch rotates ~/.kaggle/kaggle.json between several accounts to spend each one's weekly GPU hours,
    and it explicitly reverts anything that writes that file directly. Hardcoding an owner therefore breaks
    the moment the pool rotates: this session went artafather -> arash0ash -> ashranet, and a dataset owned
    by one account is 403 to the others.

    ArtaSwitch is a SEPARATE tool and this repository does not depend on it or on where it is checked out.
    Point $AQ_KAGGLE_ACCOUNTS at its account script and ask it which account to spend, rather than writing
    ~/.kaggle/kaggle.json here:
        "$AQ_KAGGLE_ACCOUNTS" pick --expect <hours>
        "$AQ_KAGGLE_ACCOUNTS" use <account>
    With the variable unset this function simply reports whoever is currently authenticated, which is all the
    rest of this file needs.
    """
    import json as _j
    import os as _o
    try:
        return _j.load(open(_o.path.expanduser("~/.kaggle/kaggle.json")))["username"]
    except Exception:
        return "artafather"


OWNER = _owner()
DATASET = f"{OWNER}/artamatch-astro"
DATA2 = f"{OWNER}/artamatch-wd-data"      # the marriages file alone, versioned independently of the code
KERNEL = f"{OWNER}/artamatch-sweep"
DATASET_TITLE = "ArtaMatch astro substrate"       # Kaggle rejects titles over 50 characters
KERNEL_TITLE = "ArtaMatch sweep"          # must slugify to the KERNEL id or Kaggle warns and renames

# The notebook. One string per cell source on purpose — a list-of-lines source is accepted by the API but
# several tools in this project mangle it, and a single string always round-trips.
CELLS = [
    ("markdown", """# ArtaMatch — the tradition sweep

Every astrological tradition that could be implemented, encoded as feature blocks, scored against a
marriage outcome, and then ensembled. Fifteen tradition modules, 211 feature blocks, 59,428 columns.

The substrate arrives as a dataset; this notebook only runs it. Nothing here is fitted to the test rows:
splits are person-disjoint (a person who appears in two marriages is never on both sides), every score is
a mean over many splits, and the stack's meta-learner sees only out-of-fold base predictions."""),

    ("code", """import os, sys, subprocess, time, json
T0 = time.time()
# WHAT HARDWARE DID WE ACTUALLY GET? A GPU kernel that silently falls back to CPU would look like a slow
# run rather than a misconfiguration, so this is printed before anything else.
try:
    print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                          "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
          or "no GPU reported by nvidia-smi")
except FileNotFoundError:
    print("nvidia-smi not present — this is a CPU session")
# pyswisseph is the one dependency Kaggle does not ship. Three tradition modules call it directly.
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyswisseph==2.10.3.2"], check=True)
import swisseph as swe
print("pyswisseph", swe.version)
for m in ("xgboost", "lightgbm", "catboost"):
    try:
        mod = __import__(m); print(m, mod.__version__)
    except Exception as e:
        print(m, "MISSING", str(e)[:60])
print(f"{os.cpu_count()} cores")"""),

    ("code", """# WHICH BENCHMARK — set by the pusher, so one notebook serves both.
COUPLES_FILE = "__COUPLES__"
EPHEM_FILE = "__EPHEM__"
print("benchmark:", COUPLES_FILE)"""),

    ("code", """# Find the payload by looking for a MARKER FILE rather than guessing the mount path. The first run
# failed on an assert here: Kaggle now nests dataset mounts, so /kaggle/input held only ['datasets']
# and the flat directory was further down. Searching for core.py is immune to the layout changing again.
SRC = None
for root, dirs, files in os.walk("/kaggle/input"):
    # Marker files: core.py AND evalx.py, both of which are always shipped. This previously looked for
    # ephem-cache.npz, which stopped being shipped when the payload was slimmed — so the finder matched
    # nothing and the run died with "payload not found" while the payload was sitting right there.
    if "core.py" in files and "evalx.py" in files:
        SRC = root
        break
assert SRC, f"payload not found under /kaggle/input; tree top = {os.listdir('/kaggle/input')}"
print("payload at", SRC)
print(len(os.listdir(SRC)), "files:", ", ".join(sorted(os.listdir(SRC))[:6]), "...")

WORK = "/kaggle/working"
os.makedirs(f"{WORK}/blocks", exist_ok=True)
os.environ["AQ_EPHE"] = SRC                      # the .se1 files sit flat beside the code
# The ephemeris cache is a BUILD ARTEFACT and always goes to the writable directory. Pointing it at the
# dataset made core.py try to write into /kaggle/input, which is read-only: "OSError [Errno 30]". The
# caches are not shipped anyway — they are regenerated here from the .se1 files in about two minutes.
os.environ["AQ_EPHEM_CACHE"] = f"{WORK}/{EPHEM_FILE or 'ephem-computed.npz'}"
COUPLES_PATH = None
for root, dirs, files in os.walk("/kaggle/input"):
    if COUPLES_FILE in files:
        cand = os.path.join(root, COUPLES_FILE)
        if COUPLES_PATH is None or os.path.getsize(cand) > os.path.getsize(COUPLES_PATH):
            COUPLES_PATH = cand          # prefer the larger file: the updated dataset is the bigger one
assert COUPLES_PATH, f"{COUPLES_FILE} not found under /kaggle/input"
print("couples:", COUPLES_PATH, os.path.getsize(COUPLES_PATH), "bytes")
os.environ["AQ_COUPLES"] = COUPLES_PATH
os.environ["AQ_BLOCKS"] = f"{WORK}/blocks"
os.environ["AQ_OUTDIR"] = WORK
os.environ["AQ_WORKERS"] = str(max(1, os.cpu_count() or 4))
# THE FOUR-INPUT CONTRACT, enforced by configuration rather than by remembering not to select a block.
# The model may see only each partner's date of birth and place of birth. The nationality module carries
# citizenship and sex, which a page cannot collect, so it is excluded from both the module list and the
# context arm; geo4 supplies place as two real coordinates instead of a country one-hot.
if COUPLES_FILE == "couples-parents.json":
    os.environ["AQ_ONLY"] = ("babylonian_egyptian,chinese,harmonics,hellenistic,lunar_calendrical,"
                             "mesoamerican,modern_western,persian_arabic,tibetan_seasia,uranian,"
                             "vedic_core,vedic_match,geo4,precision,cohort")
    os.environ["AQ_CONTEXT_KEYS"] = ("geo4::geo: EVERYTHING,precision::prec: EVERYTHING,"
                                     "cohort::coh: EVERYTHING")
    print("four-input contract enforced: no citizenship, no sex, place as coordinates")
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[v] = "1"
sys.path.insert(0, SRC)
from core import load
E = load()
print(f"{E.n:,} couples, {int(E.Y.sum()):,} per class, {len(set(E.gid.tolist())):,} person groups")"""),

    ("code", """import run, evalx
# Point every booster at the GPU when there is one. xgboost takes device="cuda"; lightgbm and catboost
# need their own flags, and catboost's GPU build ignores some CPU-only options, so each is set separately
# rather than assuming one switch covers all three.
try:
    import xgboost, subprocess
    HAS_GPU = subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0
except Exception:
    HAS_GPU = False
print("GPU available:", HAS_GPU)
if HAS_GPU:
    _orig = evalx._boosters
    def _gpu_boosters(nfeat):
        out = _orig(nfeat)
        try:
            from xgboost import XGBClassifier
            out["xgboost"] = lambda: XGBClassifier(
                n_estimators=evalx._n(600), learning_rate=0.03, max_depth=5, subsample=0.8,
                colsample_bytree=0.6, reg_lambda=2.0, min_child_weight=4, n_jobs=-1,
                tree_method="hist", device="cuda", eval_metric="logloss", random_state=0)
            out["xgboost deep"] = lambda: XGBClassifier(
                n_estimators=evalx._n(1200), learning_rate=0.015, max_depth=8, subsample=0.7,
                colsample_bytree=0.4, reg_lambda=5.0, min_child_weight=8, n_jobs=-1,
                tree_method="hist", device="cuda", eval_metric="logloss", random_state=0)
        except Exception as e:
            print("xgboost GPU setup failed:", str(e)[:80])
        try:
            from catboost import CatBoostClassifier
            out["catboost"] = lambda: CatBoostClassifier(
                iterations=evalx._n(800), learning_rate=0.03, depth=6, l2_leaf_reg=6.0,
                task_type="GPU", devices="0", verbose=0, allow_writing_files=False, random_seed=0)
        except Exception as e:
            print("catboost GPU setup failed:", str(e)[:80])
        return out
    evalx._boosters = _gpu_boosters
    # one worker only: the GPU is the bottleneck and six processes would just queue on it
    run.WORKERS = 1
from evalx import MODELS
print(f"{len(MODELS(100))} models in the zoo:")
for m in MODELS(100):
    print("   ", m)
run.collect()"""),

    ("code", """# Screen every block, then sweep the survivors across representations and the full zoo.
run.SCREEN_MODELS = ["logistic L2 (C=0.1)", "hist gradient boosting", "extra trees"]
run.SCREEN_SPLITS = 8
run.screen()"""),

    ("code", """run.KEEP_FOR_DEEP = 70
run.DEEP_SPLITS = 20
# Everything the environment has, boosters included — this is the point of running here.
run.DEEP_MODELS = [m for m in MODELS(100)]
run.reps_for = lambda ncol: (["raw"] + (["topk", "pca", "quantile"] if ncol > 8 else [])
                             + (["rff"] if ncol <= 512 else []) + (["inter"] if ncol <= 22 else []))
run.deep()"""),

    ("code", """run.KEEP_FOR_OOF = 120
run.oof()
run.stack()"""),

    ("code", """# One bundle to pull back.
import shutil, json, os
os.makedirs("/kaggle/working/bundle", exist_ok=True)
for f in ("manifest.json", "screen.json", "deep.json", "stack.json", "oof.npz"):
    p = f"/kaggle/working/{f}"
    if os.path.exists(p):
        shutil.copy(p, f"/kaggle/working/bundle/{f}")
        print(f, os.path.getsize(p), "bytes")
print(f"total {time.time()-T0:.0f}s")"""),
]


def notebook(couples="with-kids.json", ephem="ephem-cache.npz"):
    cells = [(k, v.replace("__COUPLES__", couples).replace("__EPHEM__", ephem)) for k, v in CELLS]
    return _nb(cells)


def _nb(CELLS):
    return {
        "cells": [{"cell_type": k, "metadata": {}, "source": v,
                   **({"outputs": [], "execution_count": None} if k == "code" else {})}
                  for k, v in CELLS],
        "metadata": {"kernelspec": {"language": "python", "display_name": "Python 3", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def build_payload():
    if os.path.isdir(PAYLOAD):
        shutil.rmtree(PAYLOAD)
    os.makedirs(PAYLOAD)
    # Every module the sweep can load: the traditions AND the ctx_* context modules. Globbing only
    # trad_*.py silently shipped a payload with no context blocks at all, and the run failed on a missing
    # file rather than on a missing feature — which is the good kind of failure, but only by luck.
    mods = ["core.py", "evalx.py", "run.py"]
    for pat in ("trad_*.py", "ctx_*.py"):
        mods += [os.path.basename(q) for q in sorted(glob.glob(os.path.join(HERE, pat)))]
    for f in mods:
        shutil.copy(os.path.join(HERE, f), os.path.join(PAYLOAD, f))
    # Every couples file a benchmark can name. Missing one is a hard failure on the remote, so they are
    # copied from the BENCH table rather than from a second hand-maintained list that can drift out of it.
    wanted = {c for c, _, _, _ in BENCH.values()}
    found = {}
    for sub in ("research/data-divorce", "research/data-mx", "research/data-all", "research/data-dob"):
        d = os.path.join(ROOT, sub)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f in wanted and f not in found:
                found[f] = os.path.join(d, f)
    for f in sorted(wanted):
        if f in found:
            shutil.copy(found[f], PAYLOAD)
        else:
            print(f"  WARNING: {f} is named by BENCH but was not found — that benchmark will fail")
    # The ephemeris caches are deliberately NOT shipped. ephem-par2.npz alone is ~800 MB, and the remote
    # can regenerate it from the 4 MB of .se1 files in about two minutes — uploading it would be the
    # slowest part of the whole pipeline in exchange for nothing.
    se = sorted(glob.glob(os.path.join(EPHE, "*.se1")))
    assert se, f"no Swiss Ephemeris files in {EPHE}"
    for p in se:
        shutil.copy(p, PAYLOAD)
    json.dump({"title": DATASET_TITLE, "id": DATASET, "licenses": [{"name": "CC0-1.0"}]},
              open(os.path.join(PAYLOAD, "dataset-metadata.json"), "w"), indent=1)
    tot = sum(os.path.getsize(os.path.join(PAYLOAD, f)) for f in os.listdir(PAYLOAD))
    print(f"  payload: {len(os.listdir(PAYLOAD))} files, {tot/1e6:.1f} MB, flat")
    return PAYLOAD


# ── a transport that works ───────────────────────────────────────────────────────────────────────
# The kaggle python client 2.2.4 talks to api.kaggle.com, which started returning SSL EOF and 404 mid-run
# (and is almost certainly why dataset creation failed with "slugs and hashlink are all null"). The
# documented REST surface on www.kaggle.com answers the same calls over Basic auth without complaint, so
# status and output go through curl directly. Basic auth over Bearer is what this project already found
# works for Kaggle.
API = "https://www.kaggle.com/api/v1"


def _cred():
    d = json.load(open(os.path.expanduser("~/.kaggle/kaggle.json")))
    return f"{d['username']}:{d['key']}"


def _curl(path, dest=None, tries=4):
    """GET path, body written to a FILE and the HTTP code taken from -w on stdout.

    Body-to-file and code-to-stdout, one -w only. The first version passed -w twice and then tried to
    parse the code out of a body it had also redirected, which is why every call reported HTTP 000.
    """
    tmp = dest or os.path.join(HERE, ".kg.json")
    last = ""
    for t in range(tries):
        try:
            r = subprocess.run(["curl", "-m", "300", "-sS", "-u", _cred(), "-o", tmp,
                                "-w", "%{http_code}", f"{API}{path}"],
                               capture_output=True, text=True, timeout=330)
            code = (r.stdout or "").strip()[-3:]
            if code == "200":
                if dest:
                    return True
                return json.load(open(tmp))
            last = f"HTTP {code} {(r.stderr or '')[:80]}"
        except Exception as e:
            last = str(e)[:100]
        time.sleep(5 + 10 * t)
    print(f"    {path.split('?')[0]}: {last}")
    return None


def kstatus(kernel):
    u, sl = kernel.split("/")
    return _curl(f"/kernels/status?userName={u}&kernelSlug={sl}")


def koutput(kernel):
    u, sl = kernel.split("/")
    return _curl(f"/kernels/output?userName={u}&kernelSlug={sl}")


def api():
    # Authenticate ONCE, before anything else imports the client. Kaggle binds the credential at import
    # time, so a later swap would silently act as the previous account.
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi()
    a.authenticate()
    return a


BENCH = {
    "wikidata": ("with-kids.json", "ephem-cache.npz", f"{OWNER}/artamatch-sweep", "ArtaMatch sweep"),
    "mx": ("marriages-mx.json", "ephem-mx.npz", f"{OWNER}/artamatch-sweep-mx", "ArtaMatch sweep mx"),
    # the exhaustive scrape: 39,778 day-precision unions of the 102,827 assembled, unbalanced
    "wd": ("marriages-day.json", "", f"{OWNER}/artamatch-sweep-wd", "ArtaMatch sweep wd"),
    # THE CURRENT TARGET: will two people become parents together. 134,957 declared partnerships.
    # Runs on GPU — xgboost's device="cuda" is worth roughly an order of magnitude at 135,000 rows.
    "parents": ("couples-parents.json", "ephem-par2.npz", f"{OWNER}/artamatch-parents",
                "ArtaMatch parents"),
}

# Which benchmarks request a GPU session. Only the ones whose cost is dominated by boosted trees.
GPU_BENCH = {"parents"}


def push(which="wikidata", skip_data=False):
    """Push a benchmark kernel.

    skip_data matters: creating a new DATASET VERSION cancels every kernel currently attached to that
    dataset, which is how the wikidata and mx runs both came back CANCEL_ACKNOWLEDGED after the wd push.
    So only version the payload when it has actually changed.
    """
    couples, ephem, kernel, title = BENCH[which]
    if not skip_data:
        build_payload()
    a = api()
    exists = False
    if not skip_data:
        try:
            a.dataset_status(DATASET)
            exists = True
        except Exception:
            exists = False
    if skip_data:
        print("  dataset untouched (skip_data) — a new version would cancel running kernels")
    elif exists:
        print(f"  versioning {DATASET}")
        print(a.dataset_create_version(PAYLOAD, version_notes=f"sweep payload {int(time.time())}",
                                       dir_mode="skip", quiet=True))
    else:
        print(f"  creating {DATASET}")
        print(a.dataset_create_new(PAYLOAD, public=False, quiet=True, dir_mode="skip"))

    kdir = os.path.join(HERE, f"kaggle-kernel-{which}")
    os.makedirs(kdir, exist_ok=True)
    json.dump(notebook(couples, ephem), open(os.path.join(kdir, "sweep.ipynb"), "w"), indent=1)
    sources = [DATASET] + ([DATA2] if which == "wd" else [])
    json.dump({"id": kernel, "title": title, "code_file": "sweep.ipynb",
               "language": "python", "kernel_type": "notebook", "is_private": True,
               "enable_gpu": which in GPU_BENCH, "enable_internet": True,
               "dataset_sources": sources, "competition_sources": [], "kernel_sources": []},
              open(os.path.join(kdir, "kernel-metadata.json"), "w"), indent=1)
    # The dataset must finish PROCESSING before a kernel can attach it, and "is the dataset ready" is the
    # WRONG question: after a new version is created the dataset reports ready immediately because the
    # PREVIOUS version still is, so the kernel silently attaches the old one. Two runs failed on
    # "couples-parents.json not found under /kaggle/input" while the file was plainly in the dataset.
    # Poll for the FILE instead.
    if not skip_data:
        for i in range(60):
            try:
                names = {f.name for f in a.dataset_list_files(DATASET).files}
                if couples in names:
                    print(f"  {couples} visible in the dataset after {i*10}s")
                    break
            except Exception as e:
                print(f"  dataset_list_files: {str(e)[:70]}")
            time.sleep(10)
        else:
            print(f"  WARNING: {couples} never appeared in the dataset listing; pushing anyway")
    print(f"  pushing {kernel}")
    r = a.kernels_push(kdir)
    print(r)
    bad = getattr(r, "invalidDatasetSources", None) or (r.get("invalidDatasetSources") if isinstance(r, dict) else None)
    if bad:
        print(f"  RETRYING: Kaggle rejected the data source {bad}")
        time.sleep(30)
        print(a.kernels_push(kdir))
    print(f"\n  https://www.kaggle.com/code/{kernel}")


def push_curl(which, public=True):
    """Push a kernel through the documented REST surface on www.kaggle.com.

    The python client is unusable here (api.kaggle.com returns SSL EOF and 404), and the kernels are made
    PUBLIC on purpose: kernels/output — the only way to read a run's log and artefacts — answers 403 for a
    private kernel and 200 for a public one, so a private notebook is a run whose results cannot be
    fetched back.
    """
    couples, ephem, kernel, title = BENCH[which]
    nb = notebook(couples, ephem)
    body = {
        "newTitle": title,
        "id": None,
        "slug": kernel,
        "text": json.dumps(nb),
        "language": "python",
        "kernelType": "notebook",
        "isPrivate": not public,
        "enableGpu": False,
        "enableInternet": True,
        "datasetDataSources": [DATASET],
        "competitionDataSources": [],
        "kernelDataSources": [],
        "categoryIds": [],
    }
    bf = os.path.join(HERE, ".push.json")
    json.dump(body, open(bf, "w"))
    tmp = os.path.join(HERE, ".pushresp.json")
    for t in range(4):
        r = subprocess.run(["curl", "-m", "300", "-sS", "-u", _cred(), "-o", tmp, "-w", "%{http_code}",
                            "-X", "POST", "-H", "Content-Type: application/json",
                            "--data-binary", f"@{bf}", f"{API}/kernels/push"],
                           capture_output=True, text=True)
        code = (r.stdout or "").strip()[-3:]
        if code == "200":
            j = json.load(open(tmp))
            err = j.get("error") or j.get("errorNullable") or ""
            print(f"  {kernel}: v{j.get('versionNumber')} "
                  f"{'PUBLIC' if public else 'private'}"
                  f"{'  bad sources: ' + str(j.get('invalidDatasetSources')) if j.get('invalidDatasetSources') else ''}"
                  f"{'  ERROR ' + str(err) if err else ''}")
            return j
        print(f"  {kernel}: HTTP {code} {(r.stderr or '')[:70]}")
        time.sleep(10 + 15 * t)
    return None


def status(which=None):
    ks = [BENCH[which][2]] if which else [v[2] for v in BENCH.values()]
    for k in ks:
        r = kstatus(k)
        print(f"  {k:<38} {r.get('status') if r else 'unavailable'}"
              f"{'  ' + str(r.get('failureMessage'))[:90] if r and r.get('failureMessage') else ''}")
    return


def _old_status():
    a = api()
    try:
        print(a.kernels_status(KERNEL))
    except Exception as e:
        print("kernels_status failed:", str(e)[:200])


def pull(which=None):
    a = api()
    for name, (_, _, kernel, _) in BENCH.items():
        if which and name != which:
            continue
        d = os.path.join(OUTDIR, name)
        os.makedirs(d, exist_ok=True)
        try:
            a.kernels_output(kernel, path=d, force=True, quiet=True)
            print(f"  {name}: {', '.join(sorted(os.listdir(d)))}")
        except Exception as e:
            print(f"  {name}: {str(e)[:120]}")
    return


def _old_pull():
    a = api()
    os.makedirs(OUTDIR, exist_ok=True)
    for f in sorted(os.listdir(OUTDIR)):
        print(f"  {f}  {os.path.getsize(os.path.join(OUTDIR, f)):,} bytes")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "push"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == "push":
        push(arg or "wikidata", skip_data="--keep-data" in sys.argv)
    elif cmd == "repush":
        for w in ([arg] if arg else ["mx", "wd"]):
            push_curl(w)
    elif cmd == "status":
        status(arg)
    else:
        pull(arg)
