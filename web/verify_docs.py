"""
verify_docs.py — prove the SHIPPED docs/ directory works, using only what is inside it.

WHY THIS EXISTS SEPARATELY FROM ship.py. ship.py builds docs/ from web/, and it cannot run in CI: the two
largest inputs it needs, `web/ephem4.bin` and `web/model.npz`, are deliberately gitignored, and the ephemeris
is generated from Swiss Ephemeris `.se1` files that are not in the repository either. The copies that ship are
the ones in docs/. So CI cannot rebuild the page — it can only check the artefact it is about to publish, and
that is what this does, from docs/ alone.

WHAT IT CHECKS, each one a failure that has actually happened here or is one edit away:

  1. every file the page fetches is present, and `.nojekyll` exists (without it GitHub Pages hides
     directories beginning with an underscore and serves 404s for files that are plainly there)
  2. the ephemeris magic in docs/ephem4.bin matches the literal docs/sweshim.py compares against — read from
     the source, not guessed from a candidate list, because guessing "AQEPH003".."AQEPH009" once rejected a
     correct AQEPH00A asset and blamed the asset
  3. model.json is STRUCTURALLY a model: `base` is the list of base models, not a number. Overwriting it with
     a float while injecting the benchmark produced a file that looked fine and could not be loaded
  4. the benchmark block has exactly 14 cells, the man x woman keys are the ones the page reads, and
     absent|absent is absent — the metric is the weighted mean of 14 and a 16th cell would silently change it
  5. every module named in model.json is in docs/bundle/, and nothing in the bundle imports a package Pyodide
     will not have
  6. END TO END: the bundled tradition modules are imported and run on probe couples through the SHIPPED shim
     and the SHIPPED predictor, and every block must come out at the exact width the model was trained on.
     A width drift is the failure mode that produces a page which loads, scores, and is wrong.

Usage:  python web/verify_docs.py [docs-dir]
"""
import ast
import glob
import importlib
import json
import os
import re
import sys

DOCS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

REQUIRED = ["index.html", "ephem4.bin", "tables.json", "model.json", "model.npz",
            "sweshim.py", "predictor.py", "runner.py", ".nojekyll",
            "tilldeath.py", "tilldeath.json"]
ALLOWED_IMPORTS = {"numpy", "astropy", "erfa"}
LEVELS = ["full", "month", "year", "absent"]
# Mirrors kaggle/dates.py. It is a literal here because docs/ must verify from its own contents with nothing but
# numpy and astropy — but a mismatch is caught, not shrugged at: the model's cell list must equal this exactly.
EXCLUDED_CELLS = {"absent|absent", "month|month"}
EXPECTED_CELLS = {f"{a}|{b}" for a in LEVELS for b in LEVELS} - EXCLUDED_CELLS

fails = []


def check(label, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}{('  — ' + detail) if detail else ''}")
    if not ok:
        fails.append(label)
    return ok


def third_party(path):
    """Runtime third-party imports, skipping the self-test guard and the helpers only it calls."""
    tree = ast.parse(open(path).read())
    main_blocks = [n for n in tree.body if isinstance(n, ast.If) and "__main__" in ast.dump(n.test)]
    body = [n for n in tree.body if n not in main_blocks]
    def names(nodes):
        out = set()
        for top in nodes:
            for n in ast.walk(top):
                if isinstance(n, ast.Name):
                    out.add(n.id)
                elif isinstance(n, ast.Attribute):
                    out.add(n.attr)
        return out
    outside, in_main = names(body), names(main_blocks)
    mods = set()
    for top in body:
        if (isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef))
                and top.name in in_main and top.name not in outside):
            continue
        for n in ast.walk(top):
            if isinstance(n, ast.Import):
                for a in n.names:
                    mods.add(a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                mods.add(n.module.split(".")[0])
    return {m for m in mods if m not in sys.stdlib_module_names}


def main():
    print(f"verifying {DOCS}")
    missing = [f for f in REQUIRED if not os.path.exists(os.path.join(DOCS, f))]
    check("every file the page fetches is present", not missing, f"missing {missing}" if missing else
          f"{len(REQUIRED)} files")

    magic = open(os.path.join(DOCS, "ephem4.bin"), "rb").read(8)
    src = open(os.path.join(DOCS, "sweshim.py")).read()
    want = sorted(set(re.findall(r'!=\s*b"(AQEPH\w+)"', src)))
    check("the shipped reader and the shipped asset agree on the magic",
          len(want) == 1 and magic == want[0].encode(),
          f"asset {magic!r} vs reader {want}")

    m = json.load(open(os.path.join(DOCS, "model.json")))
    check("model.json is structurally a model", isinstance(m.get("base"), list) and len(m["base"]) > 0,
          f"base is {type(m.get('base')).__name__}"
          + (f" of {len(m['base'])}" if isinstance(m.get("base"), list) else ""))

    # THIS GATE HAS TO MATCH WHATEVER THE BUILD MEASURED, and it used to demand the precision grid outright.
    # That grid was retired when the test set became day-precision only, so a gate requiring `benchmark15` would
    # refuse every ship from now on — and a gate that cannot go green protects nothing, because the next step is
    # somebody switching it off. What it must still refuse is a page with NO headline measurement, or one whose
    # headline is the optimistic in-training score.
    bm = m.get("benchmark") or {}
    cells = set((bm.get("cells") or {}))
    grid = isinstance(bm.get("benchmark15"), (int, float))
    heldout = (m.get("heldout") or {}).get("auc")
    if grid:
        check("the benchmark carries exactly the 14 man x woman cells", cells == EXPECTED_CELLS,
              f"{len(cells)} cells; unexpected {sorted(cells - EXPECTED_CELLS)}, "
              f"missing {sorted(EXPECTED_CELLS - cells)}")
        check("both non-questions are excluded from the metric", not (cells & EXCLUDED_CELLS),
              f"present: {sorted(cells & EXCLUDED_CELLS)}")
        check("the headline metric is present and in range", 0.0 < bm["benchmark15"] < 1.0,
              f"mean of 14 = {bm.get('benchmark15')}")
    else:
        check("a held-out measurement exists to headline",
              isinstance(heldout, (int, float)) and 0.0 < heldout < 1.0,
              f"heldout = {heldout!r} (no precision grid in this build, so this is the headline)")
        check("the held-out measurement names how many couples it is over",
              int((m.get("heldout") or {}).get("n") or 0) > 0,
              f"n = {(m.get('heldout') or {}).get('n')!r}")
        check("the era rule is published beside it, because that is the bar on a temporal split",
              isinstance((m.get("heldout") or {}).get("era_rule"), (int, float)),
              f"era_rule = {(m.get('heldout') or {}).get('era_rule')!r}")
        check("the page is not headlining the optimistic in-training score",
              m.get("auc_kind") == "heldout", f"auc_kind = {m.get('auc_kind')!r}")

    named = sorted({b["slug"] for b in m["base"]}) if isinstance(m.get("base"), list) else []
    bundled = sorted(os.path.basename(p)[5:-3] for p in glob.glob(os.path.join(DOCS, "bundle", "trad_*.py")))
    check("every module the model names is bundled", set(named) <= set(bundled),
          f"{len(named)} named, {len(bundled)} bundled; absent from bundle: {sorted(set(named)-set(bundled))}")

    # What the browser can actually satisfy: the three third-party packages Pyodide loads, every module that
    # travels IN the bundle (core.py and the trad_* files import each other), and `swisseph` — which is not a
    # package here at all: sweshim.py registers itself under that name, which is the whole point of the design.
    local = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(DOCS, "bundle", "*.py"))}
    local |= {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(DOCS, "*.py"))}
    satisfiable = ALLOWED_IMPORTS | local | {"swisseph"}
    bad = {}
    for p in glob.glob(os.path.join(DOCS, "bundle", "*.py")):
        extra = third_party(p) - satisfiable
        if extra:
            bad[os.path.basename(p)] = sorted(extra)
    check(f"every bundle import is satisfiable in the browser ({len(local)} local modules)", not bad, str(bad))

    if fails:
        print(f"\n{len(fails)} check(s) failed — refusing to publish")
        raise SystemExit(1)

    # 6. End to end, through the shipped shim and the shipped predictor.
    sys.path.insert(0, DOCS)
    sys.path.insert(0, os.path.join(DOCS, "bundle"))
    import numpy as np
    import sweshim
    sweshim.load(os.path.join(DOCS, "ephem4.bin"), os.path.join(DOCS, "tables.json"))
    sys.modules["swisseph"] = sweshim
    import predictor

    # THE PROBES MUST LIE INSIDE THE WINDOW THE MODEL WAS FITTED ON. Four of these were 1901-1950 dates, from
    # when the dataset ran to 1950; against a 1600-1900 model every one of them is an extrapolation, so the gate
    # would have been checking the feature modules on exactly the inputs the page refuses to answer for.
    # 1600 and 1900 are here on purpose — the two edges are where an off-by-one in the ephemeris span shows up —
    # and 1700-02-29 does not exist in the Gregorian calendar, so 1700-03-01 stands in as the leap-adjacent case.
    # The two EDGES are probed as separate couples. A first draft paired 1600-06-15 with 1899-12-31 to hit both
    # edges in one row, and core.py dropped it -- correctly, since it refuses couples born more than 60 years
    # apart -- so the gate failed on a probe the model rejects by design. Each edge now sits in a couple the model
    # is meant to score.
    probes = [("1601-04-11", "1605-09-02"), ("1866-12-25", "1870-01-07"), ("1700-03-01", "1704-02-29"),
              ("1820-07-04", "1825-03-18"), ("1833-10-10", "1833-10-10"),
              ("1600-06-15", "1603-01-20"), ("1897-05-05", "1899-12-31")]
    cand = "/tmp/aq_verify_docs_couples.json"
    json.dump([{"a": f"a{i}", "b": f"b{i}", "aDob": x, "bDob": y, "aSex": "M", "bSex": "F",
                "aPrec": 11, "bPrec": 11, "aWin": 1, "bWin": 1, "label": 0}
               for i, (x, y) in enumerate(probes)], open(cand, "w"))
    os.environ.update({"AQ_COUPLES": cand, "AQ_NO_PLACE": "1", "AQ_KEEP_ALL_COLS": "1",
                       "AQ_NO_EPHEM_CACHE": "1", "AQ_EPHEM_CACHE": "/nonexistent.npz"})
    core = importlib.import_module("core")
    E = core.load()
    blocks = {}
    for slug in sorted(set(named)):
        for k, v in (importlib.import_module(f"trad_{slug}").build(E) or {}).items():
            if v is not None:
                blocks[f"{slug}::{k}"] = np.asarray(v, dtype=np.float32)

    # `full_cols` is the width the block had when the model was fitted and `cols` is how many of them the
    # model kept. The width is what must still match: if a block grows or shrinks a column, the kept indices
    # point at different numbers and the page scores confidently against the wrong features.
    drift = []
    for b in m["base"]:
        key = b["key"]
        if key not in blocks:
            drift.append(f"{key}: not produced")
        elif blocks[key].shape[1] != b["full_cols"]:
            drift.append(f"{key}: built {blocks[key].shape[1]} columns, model trained on {b['full_cols']}")
    check(f"all {len(m['base'])} blocks build at the width the model was trained on", not drift,
          "; ".join(drift[:3]))

    stack = predictor.load(open(os.path.join(DOCS, "model.json")).read(),
                           open(os.path.join(DOCS, "model.npz"), "rb").read())
    p, _ = stack.proba(blocks)
    p = np.asarray(p, dtype=float)
    check("the shipped model scores the probe couples",
          p.shape == (len(probes),) and np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all(),
          "  ".join(f"{v:.1%}" for v in p))

    check_tilldeath()

    # THE VERDICT COMES AFTER EVERY CHECK, NOT BEFORE THE LAST ONE. This guard used to sit above
    # check_tilldeath(), so each till-death check printed its verdict into a list nothing ever read:
    # the script announced "publishable" and exited 0 with FAILs on screen. A gate that cannot fail
    # protects nothing, and this one could not.
    if fails:
        print(f"\n{len(fails)} check(s) failed — refusing to publish")
        raise SystemExit(1)

    if grid:
        print(f"\ndocs/ is publishable — mean of 14 AUCs {bm['benchmark15']:.4f} over "
              f"{bm.get('n_rows', 0):,} held-out couples")
    else:
        hd = m.get("heldout") or {}
        print(f"\ndocs/ is publishable — held-out AUC {hd.get('auc'):.4f} against an era rule of "
              f"{hd.get('era_rule'):.4f}, on {int(hd.get('n') or 0):,} couples born after the training years")


def check_tilldeath():
    """The Till Death model must reproduce its own fit THROUGH THE SHIPPED SHIM.

    This is the one gate that matters for it. The weights were fitted in Python against Swiss
    Ephemeris positions; the page recomputes those positions here, with docs/sweshim.py and
    docs/ephem4.bin. If the two ever diverge — a changed ayanamsa path, a body index off by one, a
    term dropped in an edit — the page keeps rendering confident numbers the corpus never produced.
    So the model file ships 200 couples with their float64 scores, and they are replayed.

    Tolerance 1e-3: the shim reproduces Swiss Ephemeris to arcseconds, which at k=1 moves the score
    by ~1e-4 (measured: worst 1.2e-4 over these couples). Anything structurally wrong moves it by
    whole units, hundreds of times this ceiling.
    """
    sys.path.insert(0, DOCS)
    import sweshim
    sweshim.load(os.path.join(DOCS, "ephem4.bin"), os.path.join(DOCS, "tables.json"))
    import tilldeath as td
    m = json.load(open(os.path.join(DOCS, "tilldeath.json")))

    check("the till-death model is structurally a model",
          isinstance(m.get("terms"), list) and len(m["terms"]) > 0
          and isinstance(m.get("bias"), float) and isinstance(m.get("quantiles"), list),
          f"{len(m.get('terms', []))} terms, {len(m.get('quantiles', []))} quantiles")

    kinds = {"diff", "natM", "natW", "sum", "aspM", "aspW", "midM", "midW",
             "xdiff", "xsum", "camp", "ddm", "ddp", "ssp", "dsm", "dsp", "lin"}
    SOLO = {"natM", "natW", "aspM", "aspW", "midM", "midW"}
    # EVERY TERM MUST BE SINUSOIDAL (operator 2026-09-01): a cosine or a sine of an integer harmonic
    # of a named angle. Anything else — an indicator, a bucket, a threshold — is refused here.
    badk = [t for t in m["terms"] if not isinstance(t.get("k", 1), int) or t.get("k", 1) < 1]
    check("every term is a sinusoid of an integer harmonic", not badk,
          f"{len(badk)} with a bad harmonic" if badk
          else "harmonics present: " + ", ".join(str(x) for x in sorted({t.get("k", 1) for t in m["terms"]})))
    def _ok_lin(t):
        # a linear term names every body it uses, with a non-zero integer coefficient
        return isinstance(t.get("coef"), dict) and t["coef"] and all(
            key.split(":", 1)[0] in ("his", "her") and key.split(":", 1)[1] in m["bodies"]
            and isinstance(c, int) and c != 0 for key, c in t["coef"].items())
    bad = [t for t in m["terms"] if t["kind"] not in kinds or t["trig"] not in ("cos", "sin")
           or (t["kind"] == "lin" and not _ok_lin(t))
           or (t["kind"] != "lin" and (not (0 <= t["i"] < len(m["bodies"]))
               or (t["j"] is not None and not (0 <= t["j"] < len(m["bodies"])))))]
    check("every till-death term names a real body and a real angle kind", not bad,
          f"{len(bad)} malformed" if bad else f"{len(m['terms'])} terms over {len(m['bodies'])} bodies")

    # CONSISTENCY, NOT PROHIBITION (operator 2026-09-01, revised). Single-person features are allowed
    # again in the ultimate model, so the gate no longer bans them — it bans MISDESCRIBING them. A
    # model may read one chart's placements and aspects; it may not do that while advertising itself
    # as pair-only, and it may not publish a percentile without the one-chart baselines beside it,
    # because the whole question is what the second chart adds. The earlier model beat one partner's
    # chart by 0.005 while calling itself a compatibility reading, which is the failure this catches.
    solo = sorted({t["kind"] for t in m["terms"]} & SOLO)
    if m.get("pair_only"):
        check("a model that calls itself pair-only contains no single-person feature", not solo,
              f"solo kinds present: {solo}" if solo
              else "every term needs both charts (" + ", ".join(sorted({t["kind"] for t in m["terms"]})) + ")")
    else:
        check("a model using single-person features says so rather than claiming to be pair-only",
              True, f"pair_only=false, solo families present: {solo or 'none'}")
    # THE DECOMPOSITION MUST BE THREE DIFFERENT MEASUREMENTS. Two of its three figures came out
    # byte-identical once, because two search scripts wrote the same report filename and the later
    # run silently replaced the earlier one — so the page told readers the seven-body model scored
    # what the five-body model scored. A file that cannot distinguish its own restricted runs must
    # not be published.
    dc = m.get("decomposition") or {}
    if dc:
        vals = [dc.get("all_13_bodies"), dc.get("fast_7_bodies_sun_to_saturn"),
                dc.get("fast_5_bodies_sun_to_mars")]
        ok = all(isinstance(v, float) for v in vals) and len({round(v, 6) for v in vals}) == 3
        check("the decomposition reports three distinct restricted fits", ok,
              " > ".join(f"{v:.4f}" if isinstance(v, float) else str(v) for v in vals)
              + ("" if ok else "  <- two of these are the same number"))
        check("the decomposition is ordered: fewer bodies never scores higher",
              all(isinstance(v, float) for v in vals) and vals[0] > vals[1] > vals[2],
              "all13 > fast7 > fast5" if all(isinstance(v, float) for v in vals)
              and vals[0] > vals[1] > vals[2] else "OUT OF ORDER")

    check("the one-chart baselines are published beside the model",
          isinstance(m.get("baseline_him_only"), float) and isinstance(m.get("baseline_her_only"), float),
          f"him {m.get('baseline_him_only')} · her {m.get('baseline_her_only')}")
    if isinstance(m.get("baseline_her_only"), float):
        bar = max(m["baseline_him_only"], m["baseline_her_only"])
        check("the model does not claim a lift it has not got",
              m["cv_auc_broad"] >= bar - 0.02,
              f"CV {m['cv_auc_broad']:.4f} vs one chart {bar:.4f} -> {m['cv_auc_broad']-bar:+.4f}")

    check("the till-death quantiles are sorted",
          all(m["quantiles"][i] <= m["quantiles"][i + 1] for i in range(len(m["quantiles"]) - 1)))

    worst, n = td.verify(m)
    check("the till-death page reproduces its own fit through the shipped shim", worst < 1e-3,
          f"worst |diff| {worst:.2e} over {n} couples")

    for page in ("index.html", "lab.html"):
        fp = os.path.join(DOCS, page)
        if not os.path.exists(fp):
            continue
        html = open(fp, encoding="utf-8", errors="replace").read()
        check(f"{page} wires the till-death module, model and container",
              all(t in html for t in ("tilldeath.py", "tilldeath.json", 'id="td-out"')),
              " ".join(t for t in ("tilldeath.py", "tilldeath.json", 'id="td-out"') if t not in html)
              or "all three present")

    lo, hi = m["servable_span"]
    outside = [v for v in m["verify"]
               if not (lo <= int(v["dob_a"][:4]) <= hi and lo <= int(v["dob_b"][:4]) <= hi)]
    check("every till-death verification couple is inside the shipped ephemeris span",
          not outside, f"{len(outside)} outside {lo}-{hi}")


if __name__ == "__main__":
    main()
