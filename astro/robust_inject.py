"""
robust_inject.py — what the shipped model does when a birth date is WRONG, not merely missing.

TWO HALVES OF ONE REQUIREMENT. `fit_ship.py` measures robustness to MISSING input by stratifying the real
rows: AUC among couples where both dates are known to the day, to the month, to the year only, or where one
date is absent. That is the honest way to measure missingness, because those rows really are missing and no
simulation is involved. It cannot measure robustness to input that is WRONG, though, because a wrong date
looks exactly like a right one — so that half has to be injected, and this is where.

WHAT IS INJECTED, and why each one is a real failure mode rather than an arbitrary perturbation:

    +-1, +-7, +-30 days   a transcription slip, a timezone-shifted record, a month misread. Small, plausible,
                          and the interesting question is whether the model is SMOOTH under them or jumps.
    1 January same year   not arbitrary at all: this is Wikidata's own placeholder for a year-precision date,
                          and it is the single most common wrong date in the source. A model that scores it as
                          confidently as a real date is claiming precision it does not have.
    random day same year  the honest upper bound on year-only uncertainty.
    the two dates swapped a mislabelled couple. The astrology features are symmetric by design (older/younger
                          is assigned by date, not by role), so this one SHOULD change almost nothing — and if
                          it does change something, that is a bug in the feature code, not a robustness
                          finding. It is included as a control.

WHAT IS REPORTED. AUC after the corruption, and the SPEARMAN RANK CORRELATION against the uncorrupted scores.
The second matters more for how this model is actually used: the page ranks candidate dates, so what a user
suffers from a wrong date is a reordering, and a corruption can leave AUC almost intact while shuffling the
ranking badly.

IT ALSO CHECKS THE SHIPPED MODEL. Scoring here goes through `web/predictor.py` and the exported arrays — the
browser's path, not scikit-learn's — so agreement with `fit_ship.py`'s reported AUC on the same rows is an
end-to-end check that what was measured is what was shipped.

Usage: cd astro && ~/.artamatch-venv/bin/python robust_inject.py
"""
import json
import os
import sys
from datetime import date, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(HERE, "astro-out")
COUPLES = os.path.join(ROOT, "research/data-dob/couples-parents.json")
N = int(os.environ.get("AQ_ROBUST_N") or 6000)
CAND = "/tmp/aq-robust-candidates.json"


def _shift(s, days):
    return (date.fromisoformat(s) + timedelta(days=days)).isoformat()


def corruptions(rng):
    """name -> a function mapping (aDob, bDob) to a corrupted pair."""
    def jitter(d):
        return lambda a, b: (a, _shift(b, d))

    def jan1(a, b):
        return (a, b[:4] + "-01-01")

    def randday(a, b):
        y = int(b[:4])
        return (a, (date(y, 1, 1) + timedelta(days=int(rng.integers(0, 365)))).isoformat())

    def swap(a, b):
        return (b, a)

    return [
        ("younger date +1 day", jitter(1)),
        ("younger date -1 day", jitter(-1)),
        ("younger date +7 days", jitter(7)),
        ("younger date +30 days", jitter(30)),
        ("younger date -> 1 January (Wikidata's placeholder)", jan1),
        ("younger date -> random day that year", randday),
        ("the two dates swapped (control: should barely move)", swap),
    ]


def main():
    sys.path.insert(0, WEB)
    sys.path.insert(0, HERE)
    if not os.path.exists(os.path.join(WEB, "model.npz")):
        raise SystemExit("no web/model.npz — run fit_ship.py first")

    os.environ["AQ_COUPLES"] = CAND
    os.environ["AQ_NO_PLACE"] = "1"
    os.environ["AQ_KEEP_ALL_COLS"] = "1"
    os.environ["AQ_NO_EPHEM_CACHE"] = "1"
    os.environ["AQ_EPHEM_CACHE"] = "/nonexistent.npz"
    os.environ.pop("AQ_SUBSAMPLE", None)
    os.environ.pop("AQ_ROW_INDEX", None)

    import sweshim
    sweshim.load(os.path.join(WEB, "ephem4.bin"), os.path.join(WEB, "tables.json"))
    sys.modules["swisseph"] = sweshim
    import predictor
    stack = predictor.load(open(os.path.join(WEB, "model.json")).read(),
                           open(os.path.join(WEB, "model.npz"), "rb").read())

    raw = json.load(open(COUPLES))
    day = [r for r in raw
           if int(r.get("aPrec", 11)) >= 11 and int(r.get("bPrec", 11)) >= 11
           and isinstance(r.get("aDob"), str) and isinstance(r.get("bDob"), str)
           and len(r["aDob"]) == 10 and len(r["bDob"]) == 10
           and 1800 <= int(r["aDob"][:4]) <= 2026 and 1800 <= int(r["bDob"][:4]) <= 2026]
    rng = np.random.default_rng(11)
    pick = rng.permutation(len(day))[:N]
    rows = [day[i] for i in pick]
    print(f"  {len(rows):,} couples with both dates to the day, sampled from {len(day):,}")

    _write(rows, lambda a, b: (a, b))
    import core
    mods = {s: __import__(f"trad_{s}") for s in stack.modules}
    print(f"  {len(mods)} tradition modules · {len(stack.base)} base models")

    y0, p0 = _score(core, mods, stack)
    from sklearn.metrics import roc_auc_score
    from scipy.stats import spearmanr
    auc0 = float(roc_auc_score(y0, p0))
    print(f"\n  UNCORRUPTED  n={len(y0):,}  rate {100*np.mean(y0):.1f}%  AUC {auc0:.4f}"
          f"   (scored through the SHIPPED arrays, not scikit-learn)")

    print(f"\n  {'corruption':<52} {'AUC':>7} {'delta':>8} {'rank corr':>10}")
    print(f"  {'-'*52} {'-'*7} {'-'*8} {'-'*10}")
    out = {}
    for nm, fn in corruptions(rng):
        _write(rows, fn)
        y, p = _score(core, mods, stack)
        if len(p) != len(p0):
            print(f"  {nm:<52}   {len(p)} of {len(p0)} rows survived — skipped")
            continue
        a = float(roc_auc_score(y, p))
        rho = float(spearmanr(p0, p).statistic)
        out[nm] = {"auc": a, "delta": a - auc0, "spearman": rho}
        print(f"  {nm:<52} {a:>7.4f} {a-auc0:>+8.4f} {rho:>10.4f}")

    json.dump({"n": int(len(y0)), "auc_clean": auc0, "injected": out},
              open(os.path.join(OUT, "robust-inject.json"), "w"), indent=1)
    # fold it into the shipped header so the page can show it without a second fetch
    hp = os.path.join(WEB, "model.json")
    h = json.load(open(hp))
    h["robustness_injected"] = out
    h["robustness_injected_n"] = int(len(y0))
    json.dump(h, open(hp, "w"), indent=1)
    print(f"\n  wrote astro-out/robust-inject.json and folded it into web/model.json")


def _write(rows, fn):
    outr = []
    for i, r in enumerate(rows):
        a, b = fn(r["aDob"], r["bDob"])
        lab = r.get("label", r.get("hasKids", 0))
        outr.append({"a": f"a{i}", "b": f"b{i}", "aDob": a, "bDob": b,
                     "aSex": r.get("aSex", "M"), "bSex": r.get("bSex", "F"),
                     "aPrec": 11, "bPrec": 11, "aWin": 1, "bWin": 1, "label": int(lab)})
    json.dump(outr, open(CAND, "w"))


def _score(core, mods, stack):
    E = core.load()
    blocks = {}
    for slug, mod in mods.items():
        for k, v in (mod.build(E) or {}).items():
            blocks[f"{slug}::{k}"] = v
    p, _ = stack.proba(blocks)
    return E.Y.astype(int), p


if __name__ == "__main__":
    main()
