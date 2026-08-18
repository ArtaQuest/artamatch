"""
publish_gpu_notebook.py — push the coherent-field GPU search to Kaggle.

PRIVATE, DELIBERATELY. The notebook reads `artafather/artamatch-longitudes`, which carries `y_test` — the
held-out labels of the artamatch-astrology competition. A public notebook over that input would print the answer
key. This is the one notebook in the project that must NOT be public; the build notebook and the model notebook
stay public because neither can see a held-out label.

NO INTERNET, and that is a claim rather than a setting: every input is the attached dataset, so the search cannot
reach anything a re-runner would not also have.

Usage: ~/.artamatch-venv/bin/python research/coherent/publish_gpu_notebook.py [--wait]
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "gpu_notebook.py")
STAGE = "/tmp/aqcohnb"

# Read the NAMED account file. ~/.kaggle/kaggle.json is rewritten on a timer by ArtaSwitch to spread GPU hours,
# and inheriting it turns a working push into a 403 that reads as a permissions problem rather than the wrong
# identity. ArtaSwitch was asked for this run and answered artafather.
_CRED = os.path.expanduser("~/.kaggle/kaggle.artafather.json")
if os.path.exists(_CRED) and not os.environ.get("KAGGLE_KEY"):
    _c = json.load(open(_CRED))
    os.environ["KAGGLE_USERNAME"], os.environ["KAGGLE_KEY"] = _c["username"], _c["key"]
os.environ.pop("KAGGLE_API_TOKEN", None)
OWNER = os.environ.get("KAGGLE_USERNAME") or "artafather"
# THE SLUG MUST BE THE ONE KAGGLE DERIVES FROM THE TITLE. Pushing "artamatch-coherent-field-gpu" with this
# title warned "your kernel title does not resolve to the specified id" and then created the kernel under the
# TITLE's slug instead — so a second push under the old id would have forked a separate notebook rather than
# versioning this one. Keep these two in agreement.
SLUG = "artamatch-coherent-phasor-field-gpu-search"


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    if OWNER != "artafather":
        raise SystemExit(f"refusing to push as {OWNER!r}: the private longitudes dataset is owned by "
                         f"artafather, so any other identity cannot attach it")

    src = open(SRC).read()
    nb = KaggleApi._convert_py_to_notebook(src)
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    open(os.path.join(STAGE, "gpu_notebook.ipynb"), "w").write(nb)
    json.dump({
        "id": f"{OWNER}/{SLUG}",
        "title": "ArtaMatch: coherent phasor field (GPU search)",
        "code_file": "gpu_notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,                 # reads held-out labels — see the module docstring
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": False,
        "dataset_sources": [f"{OWNER}/artamatch-longitudes"],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }, open(os.path.join(STAGE, "kernel-metadata.json"), "w"), indent=1)

    print(f"  {len(json.loads(nb)['cells'])} cells, {len(src):,} chars -> {OWNER}/{SLUG} (private, GPU)")
    for attempt in range(5):
        try:
            r = api.kernels_push(STAGE)
            print(f"  pushed -> {getattr(r, 'url', r)}")
            break
        except Exception as e:
            if attempt == 4:
                raise SystemExit(f"  gave up — {type(e).__name__} {str(e)[:200]}")
            time.sleep(4 * (attempt + 1))

    if "--wait" not in sys.argv:
        print("  not waiting; poll with kernels_status or pass --wait")
        return
    for i in range(240):
        try:
            st = api.kernels_status(f"{OWNER}/{SLUG}")
            s = str(getattr(st, "status", st))
            if i % 4 == 0:
                print(f"    status={s}  [{i*20//60}m]", flush=True)
            if "complete" in s.lower() or "error" in s.lower() or "cancel" in s.lower():
                print(f"  final: {s}  {getattr(st, 'failure_message', '') or ''}")
                return
        except Exception as e:
            print(f"    status: {type(e).__name__}")
        time.sleep(20)


if __name__ == "__main__":
    main()
