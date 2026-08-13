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
    cv = res["cv_auc"]
    base = res["baseline_auc"]
    n = res["n_train"]
    nb = res["blocks"]
    nt = res["traditions"]
    per = sorted(res["per_block"], key=lambda r: -r["auc"])

    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    for f in ("model.json", "model.npz", "result.json"):
        shutil.copy2(os.path.join(MODEL_DIR, f), os.path.join(STAGE, f))

    LEV = ["full", "month", "year", "absent"]
    if grid:
        pc = grid["per_cell"]
        head = "| man \\ woman | " + " | ".join(LEV) + " |"
        rule = "|---" * (len(LEV) + 1) + "|"
        body = "\n".join("| **" + a + "** | " + " | ".join(
            "—" if a == "absent" and b == "absent" else f"{pc[f'{a}|{b}']:.4f}" for b in LEV) + " |"
            for a in LEV)
        grid_table = (f"| **Mean of the 15 per-cell AUCs** (the headline metric) | **{grid['mean15']:.4f}** |\n"
                      f"| The same reference over the same 15 cells | {grid['reference_signed_gap_mean15']:.4f} |"
                      f"\n\n### The 15 cells, on {grid['couples']:,} held-out couples\n\n"
                      f"{head}\n{rule}\n{body}")
    else:
        grid_table = ""

    overview = f"""# ArtaMatch — an astrology-only stack over two birth dates

Fitted on [artaquest-foundation/artamatch-two-birth-dates](https://www.kaggle.com/datasets/{OWNER}/artamatch-two-birth-dates):
{n:,} declared couples, two birth dates each, and whether a child exists who names both partners.

| | AUC |
|---|---|
| **This stack**, {nb} feature blocks across {nt} traditions, out-of-fold | **{cv:.4f}** |
| Two-parameter logistic on the signed gap (woman - man) | {base:.4f} |
| Lift | **{cv-base:+.4f}** |
{grid_table}

## What it is

{nb} base models, one per feature block, each the better of histogram gradient boosting and a standardised
logistic; then a meta logistic over their out-of-fold predictions. Every feature comes from a tradition
module — aspects, harmonics, divisional charts, calendars, heliacal risings, Uranian dials — computed from
the two dates alone at 08:00 UT. No birthplace, no sex, no nationality, no cohort variable.

Strongest blocks:

{chr(10).join(f"- `{r['key']}` — {r['auc']:.4f} ({r['kind']})" for r in per[:8])}

## What to compare it against

Chance is 0.5, but 0.5 is not the bar. The reference is a two-parameter logistic on the **signed** difference
between the two dates — woman minus man, which is meaningful here only because the dataset's column order
carries sex, assigned from Wikidata's P21. That reference is in the table above and is the number this model
is measured against.

## Robustness to missing and wrong dates

The headline score is not a single AUC on clean inputs. Each partner's date is degraded independently over four
levels — the full date, the month only, the year only, absent — and the model is scored in every cell of the
resulting grid. The `absent x absent` cell is excluded: with neither date there is no input, so no model can
rank anything there. The metric is the mean of the remaining **fifteen** per-cell AUCs, which means a model
that is strong on clean dates and useless on vague ones scores worse than one that degrades gracefully.

That metric is NOT a pooled AUC over the same rows, and the difference is not small: every cell holds the same
couples with the same labels, so only one pair in fifteen that a pooled AUC ranks comes from inside a cell. A
submission ranking perfectly within every cell scores 1.000 on this metric and can score near 0.5 pooled.

## Provenance

Built by [the dataset notebook](https://www.kaggle.com/code/artafather/artamatch-build-the-dataset) from live
SPARQL against Wikidata. Companion benchmark:
`artamatch-two-birth-dates-one-shared-child`.
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
            "trainingData": [f"{OWNER}/artamatch-two-birth-dates"]}
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
    print(f"  model {cv:.4f} vs baseline {base:.4f} on {n:,} couples · {nb} blocks / {nt} traditions")
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
