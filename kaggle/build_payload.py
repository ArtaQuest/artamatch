"""
build_payload.py — assemble the Kaggle dataset that the training kernel runs on.

WHY A DATASET AND NOT A GIT CLONE. A Kaggle kernel that trains should run with the internet switched OFF, so
that what it produced is a function of its inputs and nothing else. That means everything it needs — source,
ephemeris, couples — travels as a versioned dataset.

WHAT TRAVELS, and why each piece:

    astro/core.py, astro/trad_*.py     the feature code itself. The kernel runs THESE, not a copy — the same
                                       files the browser bundles, so a number measured on Kaggle is a number
                                       the page can reproduce.
    astro/export_model.py              flattens fitted models into the arrays the browser evaluates
    web/sweshim.py, web/predictor.py   the pure-numpy swisseph and the pure-numpy model evaluator
    web/ephem4.bin, web/tables.json    the ephemeris. THE KERNEL TRAINS ON THE SHIM, deliberately: pyswisseph
                                       is not installed on Kaggle, and training on the same astronomy the
                                       browser uses removes the last gap between the measured model and the
                                       shipped one. It is the shim's accuracy that makes this safe, and that
                                       is verified against the real library before publishing.
    couples-parents.json               the dataset
    nonhuman-q5.json                   every Wikidata entity with a declared partnership that is not P31=Q5.
                                       The kernel applies it: George Jetson had a declared spouse and
                                       children, and 516 rows like that were being trained on.

WHAT DOES NOT TRAVEL. The built feature blocks (6.5 GB) — the kernel builds them, which is the whole point of
moving to a machine with 29 GB of RAM instead of 17. And no credentials of any kind.

Usage: cd kaggle && ~/.artamatch-venv/bin/python build_payload.py
"""
import glob
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAY = os.path.join(HERE, "payload")

SRC = [
    ("astro/core.py", "core.py"),
    ("astro/evalx.py", "evalx.py"),
    ("astro/export_model.py", "export_model.py"),
    ("web/sweshim.py", "sweshim.py"),
    ("web/predictor.py", "predictor.py"),
    ("web/ephem4.bin", "ephem4.bin"),
    ("web/ephem4.json", "ephem4.json"),
    ("web/tables.json", "tables.json"),
    ("research/data-dob/couples-parents.json", "couples-parents.json"),
    ("research/data-dob/nonhuman-q5.json", "nonhuman-q5.json"),
]
# Every tradition module. The kernel screens all of them and then selects, rather than being handed a
# selection made on a different population by a different machine.
SKIP_MODULES = {"electional", "muhurta", "wedding_transits"}      # need a marriage date, which does not exist


def main():
    if os.path.exists(PAY):
        shutil.rmtree(PAY)
    os.makedirs(PAY)
    total = 0
    for src, dst in SRC:
        p = os.path.join(ROOT, src)
        if not os.path.exists(p):
            raise SystemExit(f"missing {src}")
        shutil.copy2(p, os.path.join(PAY, dst))
        total += os.path.getsize(p)
    mods = []
    for p in sorted(glob.glob(os.path.join(ROOT, "astro", "trad_*.py"))):
        slug = os.path.basename(p)[5:-3]
        if slug in SKIP_MODULES:
            continue
        shutil.copy2(p, os.path.join(PAY, os.path.basename(p)))
        total += os.path.getsize(p)
        mods.append(slug)
    json.dump({"modules": mods,
               "note": "every tradition that can be computed from two birth dates; the three that need a "
                       "marriage date are excluded because there is none"},
              open(os.path.join(PAY, "modules.json"), "w"), indent=1)

    meta = {
        "title": "ArtaMatch astrology couples",
        "id": f"{os.environ.get('KAGGLE_USER', 'ashranet')}/artamatch-astrology-couples",
        "licenses": [{"name": "CC0-1.0"}],
    }
    json.dump(meta, open(os.path.join(PAY, "dataset-metadata.json"), "w"), indent=1)

    print(f"payload: {len(os.listdir(PAY))} files, {total/1e6:.1f} MB")
    for f in sorted(os.listdir(PAY), key=lambda f: -os.path.getsize(os.path.join(PAY, f)))[:8]:
        print(f"  {os.path.getsize(os.path.join(PAY, f))/1e6:>7.2f} MB  {f}")
    print(f"  {len(mods)} tradition modules: {', '.join(mods)}")


if __name__ == "__main__":
    main()
