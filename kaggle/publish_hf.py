"""
publish_hf.py — push the ArtaMatch stack to a Hugging Face model repo.

WHERE THE TOKEN COMES FROM, and why this file never stores one. In order: `HF_TOKEN` in the environment, then
`~/.artamatch-hf-token` (gitignored, expected 0600). Nothing is written to the repo, nothing is echoed, and the
token is never passed on a command line where `ps` could read it. The AQ Vault holds HF_TOKEN under PROD's
wp-config salts, so it cannot be decrypted from a local Studio install — that is why this reads a file rather
than calling `AQ\\Secrets::get`.

WHAT IS UPLOADED. The model itself (`model.json` + `model.npz`), the artefacts that let somebody reproduce the
reported score (`result.json`, `tradition_ranking.json`), and a README that leads with the HELD-OUT AUC against
the era rule. NOT the out-of-fold matrices: they are a training-time intermediate, they are large, and publishing
them invites someone to quote the optimistic in-training number as performance.

The weights are small — a few MB — because the stack is boosted trees and logistic coefficients, not a network.

Usage:
    ~/.artamatch-venv/bin/python publish_hf.py <model-dir>            # dry run: prints what it would push
    AQ_DO_PUSH=1 ~/.artamatch-venv/bin/python publish_hf.py <model-dir>
"""
import json
import os
import shutil
import sys

REPO = os.environ.get("AQ_HF_REPO", "ArtaQuest/artamatch-astrology")
STAGE = "/tmp/aqhfpush"


def token():
    t = os.environ.get("HF_TOKEN")
    if t:
        return t.strip(), "the environment"
    p = os.path.expanduser("~/.artamatch-hf-token")
    if os.path.exists(p):
        mode = oct(os.stat(p).st_mode & 0o777)
        if mode != "0o600":
            print(f"  WARNING {p} is {mode}, not 0600 — a token readable by other users is a leaked token")
        return open(p).read().strip(), p
    return None, None


def readme(model):
    res = json.load(open(os.path.join(model, "result.json")))
    rp = os.path.join(model, "tradition_ranking.json")
    rk = json.load(open(rp)) if os.path.exists(rp) else None
    hdr = json.load(open(os.path.join(model, "model.json")))
    heldout = ""
    if rk:
        top = sorted(rk["traditions"], key=lambda t: -t["auc"])[:6]
        heldout = (
            f"| **This stack, HELD OUT** | **{rk['ensemble']:.4f}** on {rk['n_test']:,} couples |\n"
            f"| The era rule on the same couples (sum of the two birth years) | {rk['era_rule']:.4f} |\n"
            + "".join(f"| {t['name']} alone | {t['auc']:.4f} |\n" for t in top))
    return f"""---
license: cc0-1.0
tags:
- astrology
- tabular-classification
- wikidata
library_name: sklearn
---

# ArtaMatch — an astrology-only stack over two birth dates

Predicts whether a **relationship lasted thirty years**, from two birth dates and nothing else. Marriages,
unmarried and same-sex partnerships, business partnerships, non-family "significant person" relations. The first
date is the **older** partner's; no sex is recorded or used anywhere.

| held out — couples born after the training window, all dead | AUC |
|---|---|
{heldout}| Two-parameter logistic on the age gap (younger − older) | {res['baseline_auc']:.4f} |
| This stack, in-training selection score — **optimistic, not a performance estimate** | {res['cv_auc']:.4f} |

**Read the held-out row against the era rule, not against 0.5.** The split is by time — fit on couples born
1600–1900, scored on couples born after — so a model above chance but below the era rule has read the calendar
rather than the couple. The in-training figure is a selection score: the base predictions it combines were made
over the same folds it is validated on, and it reads about 0.56 on coin-flip labels.

## What it is

{res['blocks']} base models across {res['traditions']} traditions — Hellenistic, Vedic, Chinese, Maya, Uranian,
heliacal-rising and lunar-calendar systems, plus Pythagorean and Chaldean numerology — each the better of
histogram gradient boosting and a standardised logistic, combined by a meta logistic over their out-of-fold
predictions. Every feature is computed from the two dates alone at 08:00 UT. No birthplace, no sex, no
nationality, no cohort variable.

## Running it

The weights alone are not enough: the features come from an ephemeris and 21 tradition modules, published
together as
[`artaquest-foundation/artamatch-ephemeris`](https://www.kaggle.com/datasets/artaquest-foundation/artamatch-ephemeris).

```python
import sys, sweshim, predictor
sweshim.load("ephem4.bin", "tables.json")
sys.modules["swisseph"] = sweshim          # before any tradition module imports it
stack = predictor.load(open("model.json").read(), open("model.npz", "rb").read())
```

`sweshim.py` is a pure-numpy stand-in for pyswisseph, so the model in a browser and the model here are the same
code rather than two implementations that agree by inspection.

## Files

| file | what |
|---|---|
| `model.json` | the block specs, the meta coefficients, and the contract the features must satisfy |
| `model.npz` | the numbers: thresholds, child indices and leaf values per tree; coefficients per logistic |
| `result.json` | the in-training figures and every block's score |
| `tradition_ranking.json` | every tradition scored ALONE on the held-out couples, against the era rule |

## What this is not

Not advice about any real person, and no score means anything about anybody's life. The label is a fact about
what Wikidata records, not about what happened: a relationship whose ending was never written down is dated from
the earlier partner's death, and one ended by a death is **not** counted as long automatically.

Dataset: [`artaquest-foundation/artamatch-astrology`](https://www.kaggle.com/datasets/artaquest-foundation/artamatch-astrology).
Competition: [artamatch-astrology](https://www.kaggle.com/competitions/artamatch-astrology).
Page: <https://artaquest.github.io/artamatch/>
"""


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "/tmp/aqdurmodel"
    need = ["model.json", "model.npz", "result.json"]
    for f in need:
        if not os.path.exists(os.path.join(model, f)):
            raise SystemExit(f"missing {model}/{f} — train first")
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    files = need + [f for f in ("tradition_ranking.json",) if os.path.exists(os.path.join(model, f))]
    for f in files:
        shutil.copy2(os.path.join(model, f), os.path.join(STAGE, f))
    open(os.path.join(STAGE, "README.md"), "w").write(readme(model))
    total = sum(os.path.getsize(os.path.join(STAGE, f)) for f in os.listdir(STAGE))
    print(f"  staged {len(os.listdir(STAGE))} files, {total/1e6:.2f} MB, for {REPO}")
    for f in sorted(os.listdir(STAGE)):
        print(f"    {os.path.getsize(os.path.join(STAGE, f))/1024:8.1f} KB  {f}")

    tok, src = token()
    if not tok:
        print("\n  NO TOKEN. Set HF_TOKEN in the environment or write it to ~/.artamatch-hf-token (chmod 600).")
        print("  The AQ Vault's HF_TOKEN is encrypted with PROD's salts and cannot be read from a local Studio.")
        return
    print(f"  token from {src}")
    if os.environ.get("AQ_DO_PUSH") != "1":
        print("\n  DRY RUN — set AQ_DO_PUSH=1 to create the repo and upload")
        return

    from huggingface_hub import HfApi
    api = HfApi(token=tok)
    who = api.whoami()
    print(f"  authenticated as {who.get('name')} ({who.get('type')})")
    api.create_repo(REPO, repo_type="model", exist_ok=True, private=False)
    api.upload_folder(repo_id=REPO, folder_path=STAGE, repo_type="model",
                      commit_message="ArtaMatch: relationship-duration stack, held-out score against the era rule")
    print(f"  pushed -> https://huggingface.co/{REPO}")


if __name__ == "__main__":
    main()
