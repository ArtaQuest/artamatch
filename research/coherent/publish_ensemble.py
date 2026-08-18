"""
publish_ensemble.py — push the 4,962-feature ensemble notebook to Kaggle.

TWO INPUTS ONLY, and that is the whole point:

  artaquest-foundation/artamatch-astrology   the competition's own three columns
  artaquest-foundation/artamatch-ephemeris   core.py, sweshim.py, the tradition modules and ephem4.bin

The second is CODE plus an astronomical constant table — planetary position against time. It carries nothing
about any couple, and every entrant can attach it. No feature matrix and no held-out label is uploaded anywhere:
an earlier attempt exported both to private datasets and they have been deleted. Features are built inside the
notebook, from the two dates, in cells a reader can run.

PUBLIC, because it can be. The notebook never sees a held-out label, so publishing it gives away no answer —
only a method.

machine_shape=NvidiaTeslaT4: Kaggle's default accelerator is a P100 at compute capability 6.0 and the
preinstalled torch supports 7.0+, so `enable_gpu` alone produces a kernel where every cuda call raises.
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "ensemble_notebook.py")
STAGE = "/tmp/aqensnb"
_CRED = os.path.expanduser("~/.kaggle/kaggle.artafather.json")
if os.path.exists(_CRED) and not os.environ.get("KAGGLE_KEY"):
    _c = json.load(open(_CRED))
    os.environ["KAGGLE_USERNAME"], os.environ["KAGGLE_KEY"] = _c["username"], _c["key"]
os.environ.pop("KAGGLE_API_TOKEN", None)
OWNER = os.environ.get("KAGGLE_USERNAME") or "artafather"
# Kaggle derives the slug from the TITLE and warns if a different id is requested, then uses its own — which
# forks a second notebook on the next push. These two are kept in agreement deliberately.
TITLE = "ArtaMatch the 4962 feature ensemble"
SLUG = "artamatch-the-4962-feature-ensemble"


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    if OWNER != "artafather":
        raise SystemExit(f"refusing to push as {OWNER!r}; this notebook belongs to artafather")
    src = open(SRC).read()
    # THE GATE MUST MATCH THE MECHANISM, NOT A PHRASE. A first version rejected the notebook because the string
    # "solution.csv" appeared in the markdown explaining that the notebook cannot see it. What matters is
    # whether a forbidden path is actually READ, so the check looks for it inside a read call and ignores
    # comments and prose entirely.
    import re
    code = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith("#") and not l.lstrip().startswith("* "))
    FORBIDDEN = ("solution", "/tmp/aqdur", "/tmp/aqcoh", "/tmp/aqmat", "artamatch-longitudes",
                 "artamatch-mega-features")
    reads = re.findall(r"(?:read_csv|np\.load|open|load)\s*\(\s*[^)]*", code)
    for r in reads:
        for bad in FORBIDDEN:
            if bad in r:
                raise SystemExit(f"the notebook READS {bad!r} in `{r[:80]}` — it may use only the competition "
                                 f"dataset and the ephemeris asset")
    assert "/kaggle/input/artamatch-astrology" in code, "the notebook does not read the competition dataset"
    print(f"  gate: {len(reads)} read calls checked, none touches a forbidden path")
    nb = KaggleApi._convert_py_to_notebook(src)
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    open(os.path.join(STAGE, "ensemble_notebook.ipynb"), "w").write(nb)
    json.dump({
        "id": f"{OWNER}/{SLUG}", "title": TITLE, "code_file": "ensemble_notebook.ipynb",
        "language": "python", "kernel_type": "notebook", "is_private": False,
        "machine_shape": "NvidiaTeslaT4", "enable_gpu": True, "enable_tpu": False,
        "enable_internet": False,
        "dataset_sources": ["artaquest-foundation/artamatch-astrology",
                            "artaquest-foundation/artamatch-ephemeris"],
        "competition_sources": [], "kernel_sources": [], "model_sources": [],
    }, open(os.path.join(STAGE, "kernel-metadata.json"), "w"), indent=1)
    print(f"  {len(json.loads(nb)['cells'])} cells, {len(src):,} chars -> {OWNER}/{SLUG}")
    for attempt in range(5):
        try:
            r = api.kernels_push(STAGE)
            print(f"  pushed -> {getattr(r, 'url', r)}")
            return
        except Exception as e:
            if attempt == 4:
                raise SystemExit(f"  gave up — {type(e).__name__} {str(e)[:200]}")
            time.sleep(4 * (attempt + 1))


if __name__ == "__main__":
    main()
