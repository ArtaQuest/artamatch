"""
publish_model.py — publish the fitted stack as a Kaggle model under the ArtaQuest Foundation.

WHAT IS PUBLISHED is not a pickle. It is two files that any numpy can evaluate:

    model.json   which feature block each base model reads, which of that block's columns it was trained on,
                 what kind of model it is, and the meta logistic's weights
    model.npz    the numbers — split thresholds, child indices and leaf values for each boosted ensemble,
                 coefficients for each logistic

That choice is deliberate and it is what makes the model verifiable rather than merely downloadable. A
pickled estimator is bound to the scikit-learn version that made it; these arrays are not bound to anything,
and the same two files are what runs in a browser on the project's web page. `export_model.py --selftest`
asserts the numpy evaluator reproduces scikit-learn to 1e-16 and XGBoost to 1e-7 (the float32 limit), so the
published artefact and the measured model are the same object.

WHAT IT CANNOT DO ALONE. The model consumes feature blocks, not raw dates — the astronomy that turns two
birth dates into those blocks is `core.py` plus the tradition modules plus a pure-numpy Swiss Ephemeris
stand-in, which travel with the repository and the build notebook rather than in this artefact. The usage
section says so plainly, because a model file that looks self-contained and is not wastes people's time.

Usage: AQ_MODEL_DIR=/tmp/aqfull ~/.artamatch-venv/bin/python publish_model.py [--instance-only]
"""
import json
import os
import shutil
import sys
import time

MODEL_DIR = os.environ.get("AQ_MODEL_DIR", "/tmp/aqfull")
STAGE = "/tmp/aqmodelpub"
OWNER = "artaquest-foundation"
SLUG = "artamatch-two-dates-stack"
INSTANCE = "astrology-stack"

os.environ.pop("KAGGLE_API_TOKEN", None)
CR = json.load(open(os.path.expanduser("~/.kaggle/kaggle.artafather.json")))
os.environ["KAGGLE_USERNAME"], os.environ["KAGGLE_KEY"] = CR["username"], CR["key"]
assert CR["username"] == "artafather"


def retry(fn, label, tries=6):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            s = str(e)
            if "already exist" in s.lower() or "409" in s:
                print(f"  {label}: already exists")
                return None
            if i == tries - 1:
                print(f"  {label}: gave up — {type(e).__name__} {s[:200]}")
                return None
            time.sleep(3 * (i + 1))


def main():
    res = json.load(open(os.path.join(MODEL_DIR, "result.json")))
    gp = os.path.join(MODEL_DIR, "grid_result.json")
    grid = json.load(open(gp)) if os.path.exists(gp) else None
    hdr = json.load(open(os.path.join(MODEL_DIR, "model.json")))
    cv = res["cv_auc"]                     # in-training selection score: optimistic, and said so below
    base = res["baseline_auc"]
    n = res["n_train"]
    # THE HELD-OUT RANKING is the number to lead with. It is measured on couples born after the training window
    # by rank_traditions.py, and it is what the competition scores; the in-training cv_auc is a selection score
    # that reads ~0.56 on coin-flip labels. Publishing cv_auc as 'the AUC' would be the flattering number.
    rp = os.path.join(MODEL_DIR, "tradition_ranking.json")
    rk = json.load(open(rp)) if os.path.exists(rp) else None
    nb = res["blocks"]
    nt = res["traditions"]
    per = sorted(res["per_block"], key=lambda r: -r["auc"])

    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    for f in ("model.json", "model.npz", "result.json"):
        shutil.copy2(os.path.join(MODEL_DIR, f), os.path.join(STAGE, f))

    # Which cells are scored is dates.py's decision, not this file's. Hardcoding "absent|absent" here meant that
    # excluding a second cell crashed the publisher with a KeyError after the page had already deployed.
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dates as _D
    LEV = _D.LEVELS
    if grid:
        pc = grid["per_cell"]
        excluded = set(grid.get("excluded") or _D.EXCLUDED_CELLS)
        head = "| man \\ woman | " + " | ".join(LEV) + " |"
        rule = "|---" * (len(LEV) + 1) + "|"
        body = "\n".join("| **" + a + "** | " + " | ".join(
            "—" if f"{a}|{b}" in excluded else f"{pc[f'{a}|{b}']:.4f}" for b in LEV) + " |"
            for a in LEV)
        nc = len(pc)
        grid_table = (f"| **Row-count-weighted mean of the {nc} per-cell AUCs** (the headline metric) "
                      f"| **{grid['mean15']:.4f}** |\n"
                      f"| The same reference over the same {nc} cells "
                      f"| {grid['reference_signed_gap_mean15']:.4f} |"
                      f"\n\n### The {nc} cells, on {grid['couples']:,} held-out couples\n\n"
                      f"{head}\n{rule}\n{body}\n\n"
                      f"Blank cells are excluded from the metric: {', '.join('`'+c+'`' for c in sorted(excluded))}. "
                      f"`absent|absent` has no input at all to rank on; `month|month` is a case the records "
                      f"essentially never present — 18 real pairs out of 107,738, where an AUC is noise.")
    else:
        grid_table = ""

    heldout_rows = ""
    if rk:
        top = sorted(rk["traditions"], key=lambda t: -t["auc"])[:6]
        heldout_rows = (
            f"| **This stack, HELD OUT** — couples born after the training window, both dead, day-precision dates "
            f"| **{rk['ensemble']:.4f}** on {rk['n_test']:,} couples |\n"
            f"| The era rule on the same held-out couples (sum of the two birth years) | {rk['era_rule']:.4f} |\n"
            + "".join(f"| {t['name']} alone, held out | {t['auc']:.4f} |\n" for t in top))
    overview = f"""# ArtaMatch — an astrology-only stack over two birth dates

Fitted on [artaquest-foundation/artamatch-astrology](https://www.kaggle.com/datasets/{OWNER}/artamatch-astrology):
{n:,} relationships — marriages, unmarried and same-sex partnerships, business partnerships, non-family
"significant person" relations — as two birth dates, **older partner first**, and whether the relationship
lasted thirty years. Training couples were born 1600-1900; the held-out couples were born after 1900 and are
all dead, so every relationship in the file has ended.

| | AUC |
|---|---|
{heldout_rows}| This stack, in-training selection score (OPTIMISTIC — reads ~0.56 on coin-flip labels; not a performance estimate) | {cv:.4f} |
| Two-parameter logistic on the age gap (younger − older) | {base:.4f} |
{grid_table}

**Read the held-out row against the era rule, not against 0.5.** On a temporal split the era rule is the bar:
a model above chance but below it has read the calendar rather than the couple.

## What it is

{nb} base models, one per feature block, each the better of histogram gradient boosting and a standardised
logistic; then a meta logistic over their out-of-fold predictions. Every feature comes from a tradition
module — aspects, harmonics, divisional charts, calendars, heliacal risings, Uranian dials, and numerology —
computed from the two dates alone at 08:00 UT. No birthplace, no sex, no nationality, no cohort variable; the
column order is age, computed from the dates.

Strongest blocks by in-training selection score (see the caveat above):

{chr(10).join(f"- `{r['key']}` — {r['auc']:.4f} ({r['kind']})" for r in per[:8])}

## What to compare it against

Two references, both reported every time. The **era rule** — the sum of the two birth years — is the one that
matters on a split by time. The **age gap** — younger minus older, non-negative because the older partner is
always the first column — is the one baseline this project permits itself, and it is in the table above.

## What the training rows look like

Test rows are complete and day-precision. Training rows may be coarse (`1802-00-00` is a year, `1809-11-00` a
month) or one-sided (`0000-00-00` in the second column means that partner is absent from Wikidata). A
relationship's duration is known just as exactly when one partner's birthday is not, so those rows carry a real
label; drop them in one line if you want only clean rows.

## Provenance

Built by [the dataset notebook](https://www.kaggle.com/code/artafather/artamatch-build-the-dataset) from live
SPARQL against Wikidata. Companion competition: `artamatch-astrology`. Companion benchmark:
`artamatch-astrology`, where a language model is asked to write an astrology model and is scored on it.
"""

    usage = """## The files

- `model.json` — structure: the block each base model reads, its column indices, its kind, and the meta weights
- `model.npz` — numbers: thresholds, child indices and leaf values per tree; coefficients per logistic
- `result.json` — the measured scores and the per-block table

## Evaluating it

These are plain arrays on purpose: no pickle, so no scikit-learn version to match. The project's
`predictor.py` is about 150 lines of numpy and reproduces scikit-learn to 1e-16 and XGBoost to 1e-7.

```python
import predictor
stack = predictor.load(open("model.json").read(), open("model.npz","rb").read())
probs, per_base = stack.proba(blocks)   # blocks: {block key -> (n, cols) array}
```

## What you also need, and this matters

The model consumes **feature blocks**, not dates. Turning two birth dates into those blocks needs `core.py`,
the tradition modules and a pure-numpy Swiss Ephemeris stand-in — they are not in this artefact. Without them
this file cannot score a couple. They ship with the project repository and are the same files the browser
version runs, which is why a score here and a score there agree.
"""

    meta = {"ownerSlug": OWNER, "modelSlug": SLUG, "instanceSlug": INSTANCE,
            "framework": "scikitLearn", "licenseName": "CC0 1.0",
            "title": "ArtaMatch two-dates astrology stack",
            "subtitle": "An astrology-only stack over two birth dates, and the baseline it has to beat",
            "isPrivate": False, "fineTunable": False,
            "modelInstanceType": "Unspecified",
            "overview": overview, "usage": usage,
            "trainingData": [f"{OWNER}/artamatch-astrology"]}
    json.dump(meta, open(os.path.join(STAGE, "model-instance-metadata.json"), "w"), indent=1)
    json.dump({"ownerSlug": OWNER, "slug": SLUG,
               "title": "ArtaMatch two-dates astrology stack",
               "subtitle": meta["subtitle"], "isPrivate": False,
               "description": overview,
               "publishTime": "", "provenanceSources": ""},
              open(os.path.join(STAGE, "model-metadata.json"), "w"), indent=1)

    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    print(f"  model in-training {cv:.4f} (optimistic) vs baseline {base:.4f} on {n:,} couples · {nb} blocks / {nt} traditions")
    if rk:
        print(f"  HELD OUT: {rk['ensemble']:.4f} vs era rule {rk['era_rule']:.4f} on {rk['n_test']:,} couples")
    if grid:
        print(f"  grid  mean of 15 AUCs {grid['mean15']:.4f} vs reference "
              f"{grid['reference_signed_gap_mean15']:.4f} on {grid['couples']:,} held-out couples")

    if "--instance-only" not in sys.argv:
        r = retry(lambda: api.model_create_new(STAGE), "model_create_new")
        print(f"  container -> {r}")
    r = retry(lambda: api.model_instance_create(STAGE, quiet=True, dir_mode="skip"), "model_instance_create")
    print(f"  instance  -> {r}")
    # "Already exists" arrives TWO ways: as an exception (caught in retry, which returns None) and as a normal
    # 200-shaped response object carrying errorCode 409. Only checking for None publishes the first version and
    # then silently stops updating the model on every run after it.
    already = r is None or str(getattr(r, "error_code", "") or
                               (r.get("errorCode") if isinstance(r, dict) else "")) == "409"
    if not already and "409" in str(r):
        already = True
    if already:
        r2 = retry(lambda: api.model_instance_version_create(
            f"{OWNER}/{SLUG}/scikitLearn/{INSTANCE}", STAGE,
            version_notes=f"out-of-fold AUC {cv:.4f} on {n:,} couples", quiet=True, dir_mode="skip"),
            "model_instance_version_create")
        print(f"  new version -> {r2}")


if __name__ == "__main__":
    main()
