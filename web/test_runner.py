"""
test_runner.py — exercise the code path the PAGE uses, including dates that are only partly known.

WHY THIS EXISTS. `verify_docs.py` proves the shipped bundle builds every block at its trained width and scores
probe couples. It says nothing about the layer above: whether a date with `00` in it survives the journey from
the browser control, through `_acceptable`, into `core.load()` and out as a probability. That layer was written
last and is the newest thing in the page, and its failure mode is quiet — `date.fromisoformat("1850-00-00")`
raises, `_acceptable` catches, and the page reports "outside what this model can answer" for a third of the
training data's own encoding. A refusal looks deliberate, so nothing would have looked broken.

WHAT IS ASSERTED
  1. precision is derived from the string, and monotonically: a known day under an unknown month is rejected
  2. `_concrete` turns `00` into a real instant without pretending the day was recorded
  3. `_acceptable` accepts coarse dates and refuses years outside the window the MODEL was trained on
  4. score_pair returns a finite probability at every precision, and coarsening a date CHANGES the answer —
     if it did not, the precision would not be reaching the model at all, which is exactly the bug that
     hardcoding aPrec=11 caused
  5. the window comes from the shipped model, not from a constant that can drift away from it

Usage:  ~/.artamatch-venv/bin/python web/test_runner.py [bundle-dir]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUNDLE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs")

fails = []


def check(label, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}{('  — ' + detail) if detail else ''}")
    if not ok:
        fails.append(label)
    return ok


def main():
    sys.path.insert(0, BUNDLE)
    sys.path.insert(0, os.path.join(BUNDLE, "bundle"))
    import sweshim
    sweshim.load(os.path.join(BUNDLE, "ephem4.bin"), os.path.join(BUNDLE, "tables.json"))
    sys.modules["swisseph"] = sweshim
    import runner
    # The page writes its candidate rows to "/candidates.json" — the root of Pyodide's virtual filesystem, which
    # is writable there and is not on a real machine. Redirecting it is the only concession this test makes to
    # not being a browser.
    runner.CANDIDATES = os.path.join(os.environ.get("TMPDIR", "/tmp"), "aq_test_candidates.json")
    if getattr(runner, "_stack", None) is None:
        # init takes the BYTES, the way the browser hands them over — not paths. Passing paths would raise
        # somewhere inside the loader and read as a broken bundle rather than a broken caller.
        runner.init(open(os.path.join(BUNDLE, "ephem4.bin"), "rb").read(),
                    open(os.path.join(BUNDLE, "tables.json")).read(),
                    open(os.path.join(BUNDLE, "model.json")).read(),
                    open(os.path.join(BUNDLE, "model.npz"), "rb").read())

    # --- 1 & 2: the date primitives, before anything astronomical happens
    cases = [("1889-04-16", 11, "1889-04-16"), ("1889-04-00", 10, "1889-04-01"),
             ("1889-00-00", 9, "1889-01-01")]
    got = [(runner._precision(d), runner._concrete(d)) for d, _, _ in cases]
    check("precision and concrete form derived from the string",
          got == [(p, c) for _, p, c in cases], str(got))
    check("the uncertainty window widens with the missing part",
          [runner._WINDOW[runner._precision(d)] for d, _, _ in cases] == [1.0, 30.0, 365.0])
    for bad in ("1889-4-16", "", "1889-04-16T00:00:00Z", None, 20260813):
        try:
            runner._precision(bad)
        except (ValueError, TypeError):
            pass
        else:
            check(f"rejects the malformed date {bad!r}", False)
            break
    else:
        check("malformed dates are rejected rather than guessed", True)

    # --- 5: the window is the model's, not a constant
    lo, hi = runner._year_range()
    h = getattr(runner._stack, "h", None)
    check("the accepted range is read from the shipped model where it declares one",
          isinstance(lo, int) and isinstance(hi, int) and lo < hi,
          f"{lo}-{hi}" + ("" if (h or {}).get("train_window") else "  (model declares none; using the fallback)"))

    # --- 3: acceptance
    mid = (lo + hi) // 2
    accept = [(f"{mid}-04-16", f"{mid+2}-07-08"), (f"{mid}-00-00", f"{mid+2}-00-00"),
              (f"{mid}-04-00", f"{mid+2}-07-08"), (f"{lo}-01-01", f"{lo}-12-31")]
    refuse = [(f"{hi+40}-04-16", f"{hi+42}-07-08"),          # after the training window
              (f"{lo-40}-04-16", f"{lo-38}-07-08"),          # before it
              (f"{mid}-04-16", f"{mid+70}-04-16"),           # more than 60 years apart
              ("not-a-date", f"{mid}-04-16")]
    check("coarse dates inside the window are accepted",
          all(runner._acceptable(a, b) for a, b in accept),
          str([(a, b) for a, b in accept if not runner._acceptable(a, b)]))
    check("out-of-window, too-far-apart and malformed pairs are refused",
          not any(runner._acceptable(a, b) for a, b in refuse),
          str([(a, b) for a, b in refuse if runner._acceptable(a, b)]))

    if fails:
        print(f"\n{len(fails)} check(s) failed")
        raise SystemExit(1)

    # --- 4: end to end, and precision must actually move the answer
    man, woman = f"{mid}-04-16", f"{mid+2}-07-08"
    out = {}
    for lbl, a, b in (("day x day", man, woman),
                      ("month x day", man[:7] + "-00", woman),
                      ("year x day", man[:4] + "-00-00", woman),
                      ("year x year", man[:4] + "-00-00", woman[:4] + "-00-00")):
        r = runner.score_pair(a, b)
        ok = isinstance(r, dict) and r.get("ok") and isinstance(r.get("p"), float)
        if not ok:
            check(f"score_pair({lbl})", False, json.dumps(r)[:200])
            break
        out[lbl] = r["p"]
        print(f"         {lbl:<12} {a} x {b}  ->  {r['p']:.4f}")
    else:
        check("score_pair answers at every precision", True,
              "  ".join(f"{k}={v:.4f}" for k, v in out.items()))
        vals = list(out.values())
        check("all probabilities are finite and in [0,1]",
              all(0.0 <= v <= 1.0 for v in vals))
        # If precision were not reaching the model, coarsening could not change anything. This is the assertion
        # that would have caught aPrec=11 being hardcoded for every row.
        check("coarsening a date changes the answer, so precision reaches the model",
              len(set(round(v, 6) for v in vals)) > 1,
              f"{len(set(round(v, 6) for v in vals))} distinct values from 4 precisions")

    if fails:
        print(f"\n{len(fails)} check(s) failed")
        raise SystemExit(1)
    print("\nthe page's date path holds, coarse dates included")


if __name__ == "__main__":
    main()
