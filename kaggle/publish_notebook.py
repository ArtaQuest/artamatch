"""
publish_notebook.py — push the dataset-build notebook to Kaggle, public and re-runnable.

WHY THE NOTEBOOK IS THE POINT. The dataset is three columns of dates and a bit; anyone can download it and
nobody can check it. What makes it checkable is that every row came from SPARQL queries printed in the notebook
against a public endpoint, so a stranger can re-run the build and get a DIFFERENT answer as Wikidata changes —
and that disagreement is the evidence. A dataset published without its build is an assertion.

THE NOTEBOOK NEEDS INTERNET, which is not the default for a Kaggle kernel and fails in a way that looks like a
code bug: the SPARQL fetch raises a connection error inside a cell rather than saying "internet is off".

OWNERSHIP. Notebooks would not accept the organisation as an owner, so this pushes under the personal account
and the dataset it builds stays under the Foundation. The notebook's own output is not the published dataset —
that is uploaded from the operator machine — so the two cannot silently disagree about which build is live.

Usage: KAGGLE_USERNAME=... KAGGLE_KEY=... ~/.artamatch-venv/bin/python publish_notebook.py [--wait]
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "scrape_notebook.py")
STAGE = "/tmp/aqnbpush"
# READ THE ACCOUNT FILE, DO NOT INHERIT THE AMBIENT ONE. ~/.kaggle/kaggle.json is rewritten on a timer by
# ArtaSwitch to spread GPU hours across several accounts, and this script inherited whatever it found there: a
# push that had just worked came back 403 because the file had rotated to a different account mid-session, and a
# 403 on SaveKernel reads as a permissions problem rather than as the wrong identity. The other publishers in
# this directory already read the named file; this one was the exception.
_CRED = os.path.expanduser("~/.kaggle/kaggle.artafather.json")
if os.path.exists(_CRED) and not os.environ.get("KAGGLE_KEY"):
    _c = json.load(open(_CRED))
    os.environ["KAGGLE_USERNAME"], os.environ["KAGGLE_KEY"] = _c["username"], _c["key"]
OWNER = os.environ.get("KAGGLE_USERNAME") or "artafather"
SLUG = "artamatch-build-the-dataset"
TITLE = "ArtaMatch: build the dataset"

os.environ.pop("KAGGLE_API_TOKEN", None)


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    # The notebook lives under a specific account and a version pushed by another one is a 403, not a merge.
    if OWNER != "artafather":
        raise SystemExit(f"refusing to push as {OWNER!r}: this notebook is owned by artafather, and pushing as "
                         f"anyone else answers 403 SaveKernel — set KAGGLE_USERNAME/KAGGLE_KEY explicitly")

    src = open(SRC).read()
    nb = KaggleApi._convert_py_to_notebook(src)      # py:percent cells -> .ipynb JSON

    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    open(os.path.join(STAGE, "scrape_notebook.ipynb"), "w").write(nb)
    json.dump({
        "id": f"{OWNER}/{SLUG}",
        "title": TITLE,
        "code_file": "scrape_notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        # The build is nothing but live SPARQL. Without this the first fetch raises a connection error inside a
        # cell, which reads as a bug in the notebook rather than as a switch that was left off.
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }, open(os.path.join(STAGE, "kernel-metadata.json"), "w"), indent=1)

    cells = json.loads(nb)["cells"]
    print(f"  {len(cells)} cells, {len(src):,} chars of source -> {OWNER}/{SLUG}")

    for attempt in range(5):
        try:
            r = api.kernels_push(STAGE)
            print(f"  pushed -> {getattr(r, 'url', r)}")
            break
        except Exception as e:
            if attempt == 4:
                print(f"  gave up — {type(e).__name__} {str(e)[:200]}")
                return
            time.sleep(4 * (attempt + 1))

    if "--wait" not in sys.argv:
        print("  not waiting for the run; pass --wait to poll it")
        return
    for i in range(120):
        try:
            st = api.kernels_status(f"{OWNER}/{SLUG}")
            status = str(getattr(st, "status", st))
            if i % 4 == 0:
                print(f"    status={status}")
            if "complete" in status.lower() or "error" in status.lower():
                print(f"  final: {status}  {getattr(st, 'failure_message', '') or ''}")
                return
        except Exception as e:
            print(f"    status check: {type(e).__name__}")
        time.sleep(15)


if __name__ == "__main__":
    main()
