"""
ship.py — assemble docs/ for GitHub Pages, and refuse to assemble a broken one.

WHAT GOES IN. The page, the three browser-side Python files, the ephemeris asset and its tables, the exported
model — and `docs/bundle/`, which is the TRAINING CODE, copied verbatim: `core.py` plus every `trad_*.py`
module the model actually reads. That copy is the whole point of the architecture. The browser does not run a
port of the feature code; it runs the file that was trained on, with only Swiss Ephemeris swapped for
`sweshim.py` underneath.

WHAT IS CHECKED BEFORE ANYTHING IS WRITTEN, because a page that half-works is worse than one that does not
load at all — the first looks like a result:

  1. every module named in model.json is present in the bundle, and every bundled module is one the model
     names (a stale extra module would be dead weight; a missing one is a crash on first score)
  2. the asset's magic matches what the shipped sweshim.py expects — the two have gone out of step twice
     during development, and the failure is a blank page with a console error nobody reads
  3. nothing in the bundle imports a package Pyodide does not have. The permitted set is numpy, astropy and
     erfa; scipy and scikit-learn are deliberately NOT shipped, because the exported model does not need
     them and they are large.
  4. every block still produces the exact width the model was trained on, checked by RUNNING the modules
     through the shipped shim — the check that catches a tradition module edited after the model was fitted,
     which is the likeliest way this repository breaks its own deployment. The same pass scores six probe
     couples end to end, so publishing cannot happen unless the whole browser path executes.

Usage: cd web && ~/.artamatch-venv/bin/python ship.py
"""
import ast
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASTRO = os.path.join(ROOT, "astro")
DOCS = os.path.join(ROOT, "docs")
# What the browser will actually have: numpy and astropy from Pyodide (astropy pulls pyerfa, which provides
# `erfa`), plus this project's own modules. scipy and scikit-learn are deliberately absent — the exported
# model is evaluated by predictor.py in pure numpy, so shipping them would add tens of megabytes for nothing.
# numpy and astropy come from Pyodide (astropy pulls pyerfa, which provides `erfa`); everything else in this
# set is a file that SHIPS, so it is importable by definition. Derived from PAGE_FILES rather than restated,
# because adding a page module and forgetting to list it here fails the build with "packages Pyodide will not
# have" — which reads as a missing dependency rather than a stale allow-list, and leaves docs/ unwritten while
# every later check happily re-tests the previous build.
ALLOWED_IMPORTS = {"numpy", "astropy", "erfa", "swisseph", "core"} | {
    f[:-3] for f in ["index.html", "sweshim.py", "predictor.py", "runner.py", "worked.py"] if f.endswith(".py")}
PAGE_FILES = ["index.html", "artamodel.html", "stack_iv_predictor.py", "stack_iv_deployed.json", "capitals.json", "geo_lgbm_0.json", "geo_lgbm_1.json", "geo_lgbm_2.json", "sweshim.py", "predictor.py", "runner.py", "worked.py",
              "ephem4.bin", "ephem4.json", "tables.json", "model.json", "model.npz"]


def third_party(path):
    """Third-party modules imported on a path the BROWSER can reach.

    Two kinds of code in these modules never run in a browser, and counting either one refuses a bundle that
    works perfectly:

      1. the `if __name__ == "__main__"` block, and
      2. module-level helper functions that only the `__main__` block ever names — the self-test reporters.
         About twenty of these modules do `from evalx import quick` inside a `_report()` that nothing but the
         self-test calls. Excluding only (1) flagged those as missing Pyodide packages, which is a false
         refusal: the import is unreachable from `build()`.

    The exclusion is deliberately narrow. A helper referenced ANYWHERE outside the self-test block — including
    indirectly, by being named in another reachable function — is still checked, so the gate keeps catching the
    thing it exists for: a browser-reachable import of a package Pyodide does not ship.
    """
    tree = ast.parse(open(path).read())
    main_blocks = [n for n in tree.body if isinstance(n, ast.If) and "__main__" in ast.dump(n.test)]
    body = [n for n in tree.body if n not in main_blocks]

    # Every name mentioned anywhere outside the self-test guard.
    named_outside = set()
    for top in body:
        for n in ast.walk(top):
            if isinstance(n, ast.Name):
                named_outside.add(n.id)
            elif isinstance(n, ast.Attribute):
                named_outside.add(n.attr)

    # Names the self-test guard itself mentions. A helper is dev-only when the SELF-TEST calls it and nothing
    # outside does. "Referenced nowhere in this file" is NOT sufficient and was a real hole: `build()` is called
    # from the browser, never from inside its own module, so treating unreferenced defs as dev-only stopped
    # checking the one function that always runs.
    named_in_main = set()
    for blk in main_blocks:
        for n in ast.walk(blk):
            if isinstance(n, ast.Name):
                named_in_main.add(n.id)
            elif isinstance(n, ast.Attribute):
                named_in_main.add(n.attr)

    def dev_only(node):
        """A module-level def that the self-test calls and nothing outside the self-test mentions."""
        return (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in named_in_main
                and node.name not in named_outside)

    mods, skipped = set(), []
    for top in body:
        if dev_only(top):
            skipped.append(top.name)
            continue
        for n in ast.walk(top):
            if isinstance(n, ast.Import):
                for a in n.names:
                    mods.add(a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                mods.add(n.module.split(".")[0])
    if skipped and os.environ.get("AQ_SHIP_VERBOSE"):
        print(f"    {os.path.basename(path)}: self-test-only helpers skipped: {sorted(skipped)}")
    return {m for m in mods if m not in sys.stdlib_module_names}


def main():
    for f in PAGE_FILES:
        if not os.path.exists(os.path.join(HERE, f)):
            raise SystemExit(f"missing web/{f} — run fit_ship.py and build_asset_v4.py first")

    header = json.load(open(os.path.join(HERE, "model.json")))
    slugs = []
    for b in header["base"]:
        if b["slug"] not in slugs:
            slugs.append(b["slug"])
    print(f"model.json: {len(header['base'])} base models across {len(slugs)} traditions")
    print(f"  AUC {header.get('auc')}   baseline {header.get('baseline')}   n {header.get('n')}")

    # 1. the bundle is exactly the modules the model names
    need = ["core.py"] + [f"trad_{s}.py" for s in slugs]
    missing = [f for f in need if not os.path.exists(os.path.join(ASTRO, f))]
    if missing:
        raise SystemExit(f"the model names modules that do not exist: {missing}")

    # 2. the asset magic the shipped reader expects
    magic = open(os.path.join(HERE, "ephem4.bin"), "rb").read(8)
    src = open(os.path.join(HERE, "sweshim.py")).read()
    # Read the literal the reader actually compares against, rather than guessing from a candidate list. The
    # guess used to be "AQEPH003".."AQEPH009" — digits only — so when the magic became AQEPH00A it could not
    # bind at all and the gate rejected a perfectly good asset while blaming the asset. A gate that cannot read
    # its signal must say so about ITSELF, not fail the thing it is measuring.
    want = re.findall(r'!=\s*b"(AQEPH\w+)"', src)
    if not want:
        raise SystemExit("cannot find the magic comparison in sweshim.py — this gate can no longer read the "
                         "reader, so fix the gate; do not assume the asset is wrong")
    if len(set(want)) > 1:
        raise SystemExit(f"sweshim.py compares against more than one magic {sorted(set(want))} — ambiguous")
    want = want[0].encode()
    if magic != want:
        raise SystemExit(f"asset magic {magic!r} but sweshim.py expects {want!r} — rebuild the asset")
    print(f"  asset magic {magic.decode()} matches the shipped reader")

    # 3. nothing imports a package Pyodide does not have
    bad = []
    for f in need + ["sweshim.py", "predictor.py", "runner.py"]:
        p = os.path.join(ASTRO if f.startswith(("core", "trad_")) else HERE, f)
        extra = third_party(p) - ALLOWED_IMPORTS
        if extra:
            bad.append(f"{f} imports {sorted(extra)}")
    if bad:
        raise SystemExit("packages Pyodide will not have:\n  " + "\n  ".join(bad))
    print(f"  {len(need) + 3} python files import only {sorted(ALLOWED_IMPORTS - {'core', 'swisseph'})}")

    # 4. EVERY BLOCK STILL PRODUCES THE WIDTH THE MODEL WAS TRAINED ON. This is the check that catches a
    # tradition module edited after the model was fitted — the most likely way this repository breaks its own
    # deployment, and one that shows up in a browser as a silent misalignment rather than an error, because a
    # narrower matrix still multiplies. The modules are run on a handful of couples through the shipped shim,
    # which also proves the whole browser path imports and executes before anything is published.
    import numpy as np
    sys.path.insert(0, HERE)
    sys.path.insert(0, ASTRO)
    probe = "/tmp/aq-ship-probe.json"
    json.dump([{"a": f"a{i}", "b": f"b{i}", "aDob": d, "bDob": e, "aSex": "M", "bSex": "F",
                "aPrec": 11, "bPrec": 11, "aWin": 1, "bWin": 1, "label": 0}
               # THE EXTREMES ARE IN THE PROBE ON PURPOSE. Several modules search outward from a birth
               # date — the new moon before it, the previous eclipse — so a birth on 1800-01-01 reaches
               # into 1799, and the first shipped asset did not carry it. That surfaced as a crash on the
               # first evaluation cell, never in training, because training uses real Swiss Ephemeris and
               # has no edge. These six pairs pin both ends of the accepted range, a same-day couple, and a
               # 1-January date, so publishing exercises every boundary the page can be handed.
               for i, (d, e) in enumerate([("1994-02-15", "2004-01-31"),
                                           ("1800-01-01", "1800-01-02"),
                                           ("1800-01-03", "1802-06-01"),
                                           ("2026-12-31", "2026-12-30"),
                                           ("1975-07-04", "1975-07-04"),
                                           ("1920-01-01", "1921-01-01")])],
              open(probe, "w"))
    os.environ.update({"AQ_COUPLES": probe, "AQ_NO_PLACE": "1", "AQ_KEEP_ALL_COLS": "1",
                       "AQ_NO_EPHEM_CACHE": "1", "AQ_EPHEM_CACHE": "/nonexistent.npz"})
    for k in ("AQ_SUBSAMPLE", "AQ_ROW_INDEX", "AQ_BALANCE", "AQ_ONLY_KEYS"):
        os.environ.pop(k, None)
    import sweshim
    sweshim.load(os.path.join(HERE, "ephem4.bin"), os.path.join(HERE, "tables.json"))
    sys.modules["swisseph"] = sweshim
    import core
    E = core.load()
    built = {}
    for slug in slugs:
        for bk, bv in (__import__(f"trad_{slug}").build(E) or {}).items():
            built[f"{slug}::{bk}"] = np.asarray(bv)
    wrong, absent = [], []
    for b in header["base"]:
        X = built.get(b["key"])
        if X is None:
            absent.append(b["key"])
        elif X.shape[1] != b["full_cols"]:
            wrong.append(f"{b['key']}: builds {X.shape[1]} columns, model trained on {b['full_cols']}")
    if absent:
        raise SystemExit(f"{len(absent)} blocks the model needs are no longer built: {absent[:3]}")
    if wrong:
        raise SystemExit("block widths no longer match the model:\n  " + "\n  ".join(wrong[:5]))
    print(f"  all {len(header['base'])} blocks build at the exact width the model was trained on, "
          f"through the shipped shim")

    import predictor
    st = predictor.load(open(os.path.join(HERE, "model.json")).read(),
                        open(os.path.join(HERE, "model.npz"), "rb").read())
    pr, _ = st.proba(built)
    if not np.all(np.isfinite(pr)) or pr.min() < 0 or pr.max() > 1:
        raise SystemExit(f"the shipped model returned values outside [0,1] or non-finite: {pr}")
    print(f"  end to end on {len(pr)} probe couples: " + ", ".join(f"{100*x:.1f}%" for x in pr))

    # ── write ─────────────────────────────────────────────────────────────────────────────────────
    if os.path.exists(DOCS):
        shutil.rmtree(DOCS)
    os.makedirs(os.path.join(DOCS, "bundle"))
    total = 0
    for f in PAGE_FILES:
        shutil.copy2(os.path.join(HERE, f), os.path.join(DOCS, f))
        total += os.path.getsize(os.path.join(DOCS, f))
    for f in need:
        shutil.copy2(os.path.join(ASTRO, f), os.path.join(DOCS, "bundle", f))
        total += os.path.getsize(os.path.join(DOCS, "bundle", f))
    json.dump({"files": need,
               "note": "core.py and the tradition modules, copied verbatim from astro/ — the browser runs "
                       "the training code, not a port of it"},
              open(os.path.join(DOCS, "bundle", "manifest.json"), "w"), indent=1)
    open(os.path.join(DOCS, ".nojekyll"), "w").close()   # or Pages hides anything starting with _

    print(f"\nwrote docs/ — {total/1e6:.2f} MB over {len(PAGE_FILES) + len(need)} files")
    for f in sorted(os.listdir(DOCS)):
        p = os.path.join(DOCS, f)
        if os.path.isfile(p):
            print(f"  {os.path.getsize(p)/1e6:>7.2f} MB  {f}")
    bsz = sum(os.path.getsize(os.path.join(DOCS, "bundle", f))
              for f in os.listdir(os.path.join(DOCS, "bundle")))
    print(f"  {bsz/1e6:>7.2f} MB  bundle/ ({len(need)} modules)")
    print(f"\n  the page also pulls Pyodide, numpy and astropy from the CDN at runtime")


if __name__ == "__main__":
    main()
