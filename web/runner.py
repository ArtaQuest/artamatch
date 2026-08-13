"""
runner.py — the browser's entry point. Runs the REAL pipeline on two birth dates.

WHAT HAPPENS WHEN THE PAGE SCORES A PAIR. Nothing is looked up. The two dates are written into a couples file
in the training schema, `core.py` reads that file and computes every planetary position for both charts, each
tradition module builds its own feature blocks from those positions, and the exported base models and meta
logistic turn them into one probability. That is the same `core.py` and the same `trad_*.py` files the model
was trained on, byte for byte — the only thing swapped out underneath is Swiss Ephemeris, replaced by
`sweshim.py` because Pyodide has no pyswisseph. So there is one implementation of every feature and no
opportunity for training and inference to drift apart.

NOTHING IS CACHED, by instruction and by construction:
  * `AQ_NO_EPHEM_CACHE=1`, so core.py neither reads nor writes its ephemeris cache. That cache is validated
    by SHAPE alone, and a search scores equal-sized batches one after another — exactly the case where the
    second batch would silently be scored on the first batch's sky.
  * No stored scores, no precomputed candidate grid, no memo across calls. Ask the same question twice and
    the whole computation runs twice.
  The one table that ships is the ephemeris itself, which is what Swiss Ephemeris' own data files are on the
  laptop: positions of planets, not answers about people.

THE INPUT CONTRACT IS TWO DATES. No birthplace, so no Ascendant, no house cusp, no astrocartography line, and
every chart is cast at 08:00 UT. The search therefore ranks candidate DATES; it has no city dimension.

WHAT IS REPORTED HONESTLY
  * `dropped` — core.py refuses a couple whose births are more than 60 years apart, and a candidate outside
    the shipped ephemeris span cannot be computed at all. Both are counted and returned rather than quietly
    thinned out of the result, because a search that silently drops candidates looks complete.
  * `by_tradition` — the mean base-model probability per tradition. A DESCRIPTION of where a score comes
    from, not a decomposition of it: the meta logistic is not additive over traditions, so these do not sum
    to the answer.
"""
import json
import os
import sys

import numpy as np

BUNDLE = "/bundle"
CANDIDATES = "/candidates.json"

_stack = None
_core = None
_mods = {}
_span = (None, None)


def init(asset_bytes, tables_json, model_json, model_npz_bytes):
    """Install the shim, load the model, and import the real pipeline. Call once."""
    global _stack, _core, _span
    # The environment must be set BEFORE core is imported: core.py reads AQ_COUPLES and AQ_EPHEM_CACHE into
    # module constants at import time, so a later change would be ignored. The couples path is fixed and the
    # file is rewritten for every batch.
    os.environ["AQ_COUPLES"] = CANDIDATES
    os.environ["AQ_NO_PLACE"] = "1"
    os.environ["AQ_KEEP_ALL_COLS"] = "1"
    os.environ["AQ_NO_EPHEM_CACHE"] = "1"
    os.environ["AQ_EPHEM_CACHE"] = "/nonexistent-cache.npz"
    os.environ.pop("AQ_SUBSAMPLE", None)
    os.environ.pop("AQ_BALANCE", None)
    os.environ.pop("AQ_ROW_INDEX", None)

    # ASTROPY MUST NOT REACH FOR THE NETWORK. core.py and trad_african use astropy for time conversion and
    # for precessing a star catalogue, and astropy will by default try to fetch fresh IERS Earth-orientation
    # tables when a transform asks for high accuracy. In a browser that either fails or stalls. It is turned
    # off here, and the accuracy it buys is irrelevant at this scale: IERS corrections are sub-arcsecond,
    # against a 0.0055 degree ephemeris step and a birth hour that is assumed rather than known.
    try:
        from astropy.utils import iers
        iers.conf.auto_download = False
        iers.conf.iers_degraded_accuracy = "ignore"
    except Exception:
        pass

    if BUNDLE not in sys.path:
        sys.path.insert(0, BUNDLE)
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    import sweshim
    tables = json.loads(tables_json) if isinstance(tables_json, str) else tables_json
    a = sweshim.load(None, None, blob=bytes(asset_bytes), tables=tables)
    sys.modules["swisseph"] = sweshim
    _span = (a.jd0, a.jd0 + a.ndays)

    import predictor
    _stack = predictor.load(model_json, bytes(model_npz_bytes))

    # A minimal file must exist before core is imported, because importing it is what fixes the path.
    _write([{"a": "x", "b": "y", "aDob": "1990-01-01", "bDob": "1992-01-01",
             "aSex": "M", "bSex": "F", "label": 0}])
    import core
    _core = core
    for slug in _stack.modules:
        _mods[slug] = __import__(f"trad_{slug}")
    return {"bodies": int(a.nb), "days": int(a.ndays),
            "yearFrom": int(round(2000 + (a.jd0 - 2451545.0) / 365.25)),
            "yearTo": int(round(2000 + (a.jd0 + a.ndays - 2451545.0) / 365.25)),
            "traditions": _stack.modules,
            "nbase": len(_stack.base),
            # the base list travels too, so the page can count blocks per tradition without a second fetch
            "base": [{"slug": b["slug"], "key": b["key"], "kind": b["kind"], "auc": b.get("auc")}
                     for b in _stack.h["base"]],
            "rate": _stack.h.get("rate"),
            "auc": _stack.h.get("auc"),
            "baseline": _stack.h.get("baseline"),
            "n": _stack.h.get("n"),
            "hour": _stack.h.get("hour"),
            "contract": _stack.h.get("contract"),
            "tradition_auc": _stack.h.get("tradition_auc"),
            "clean_auc": _stack.h.get("clean_auc"),
            "benchmark": _stack.h.get("benchmark")}


def _write(rows):
    with open(CANDIDATES, "w") as f:
        json.dump(rows, f)


# A date whose unknown components are written `00`: `1850-03-17` is a day, `1850-03-00` a month, `1850-00-00`
# a year. This mirrors kaggle/dates.py deliberately rather than importing it — the browser bundle ships only
# what the page needs — and the two must agree, because a page that reports precision differently from the
# training data is scoring the model on a representation it never saw.
_WINDOW = {11: 1.0, 10: 30.0, 9: 365.0}


def _precision(d):
    if not isinstance(d, str) or len(d) != 10:
        raise ValueError(f"not a YYYY-MM-DD date: {d!r}")
    if d[8:10] != "00":
        return 11
    return 10 if d[5:7] != "00" else 9


def _concrete(d):
    """A real instant to compute a chart for. The precision travels beside it, so nothing claims to know the day."""
    return f"{d[:4]}-{'01' if d[5:7] == '00' else d[5:7]}-{'01' if d[8:10] == '00' else d[8:10]}"


def _row(a_id, b_id, a_dob, b_dob):
    pa, pb = _precision(a_dob), _precision(b_dob)
    return {"a": a_id, "b": b_id, "aDob": _concrete(a_dob), "bDob": _concrete(b_dob),
            "aSex": "M", "bSex": "F",
            "aPrec": pa, "bPrec": pb, "aWin": _WINDOW[pa], "bWin": _WINDOW[pb],
            "label": 0}


def _build(rows):
    """Score a batch. Returns (probabilities, per-base matrix, the ids that survived core.py's filters)."""
    if _stack is None:
        raise RuntimeError("runner.init() has not been called")
    _write(rows)
    E = _core.load()
    if E.n == 0:
        return np.zeros(0), np.zeros((0, len(_stack.base))), []
    blocks = {}
    for slug, mod in _mods.items():
        built = mod.build(E)
        for k, v in (built or {}).items():
            blocks[f"{slug}::{k}"] = v
    p, P = _stack.proba(blocks)
    ids = [str(x) for x in E.PYNG] if hasattr(E, "PYNG") else None
    return p, P, ids


def score_pair(dob_a, dob_b):
    """One couple. Returns the probability and the per-tradition description."""
    if not _acceptable(dob_a, dob_b):
        return {"ok": False,
                "why": f"outside what this model can answer: both births must fall in "
                       f"{_year_range()[0]}-{_year_range()[1]} — the years it was trained on, chosen so that "
                       f"every couple has had a full reproductive life — and be no more than "
                       f"{int(MAX_GAP_YEARS)} years apart"}
    p, P, _ = _build([_row("self", "partner", dob_a, dob_b)])
    if len(p) == 0:
        return {"ok": False, "why": "core.py refused this pair"}
    bt = _stack.by_tradition(P)
    return {"ok": True, "p": float(p[0]),
            "by_tradition": {k: float(v[0]) for k, v in bt.items()}}


# THE THREE RULES A PAIR HAS TO SATISFY, kept in one place so the runner and core.py cannot disagree.
# core.load refuses a couple whose births are more than 60 years apart, and refuses any birth year outside
# 1200-2026; the shipped ephemeris covers 1800-2030 and the shim raises rather than extrapolate outside it.
# The binding range is the intersection. Getting this wrong does not produce an error message — core.load
# silently returns fewer rows than were asked for, and since it drops them from the MIDDLE of a batch, the
# surviving scores can no longer be matched to the dates that produced them.
# The range this model may be ASKED about is the range it was TRAINED on, not the range the ephemeris covers.
# The training window is 1800-1950 — deliberately, to keep the exposure effect out of the measurement — so a
# 1994 birth is extrapolation, and the honest answer to it is a refusal rather than a confident number. The
# shipped model.json carries the window it was fitted on and that is what is used; the constants here are only
# the fallback for a build that predates the field.
YEAR_LO, YEAR_HI = 1800, 1950
MAX_GAP_YEARS = 60.0


def _acceptable(dob_a, dob_b):
    """Can this model answer about these two dates at all?

    `date.fromisoformat` cannot read `1850-00-00`, so this parses the concrete form. Without that, every
    coarse date — a third of the training data's own encoding — was refused by the page as malformed.
    """
    from datetime import date
    try:
        a, b = date.fromisoformat(_concrete(dob_a)), date.fromisoformat(_concrete(dob_b))
    except (ValueError, TypeError, IndexError):
        return False
    lo, hi = _year_range()
    if not (lo <= a.year <= hi and lo <= b.year <= hi):
        return False
    return abs((b - a).days) / 365.2425 <= MAX_GAP_YEARS


def _year_range():
    """The window the shipped model was fitted on, falling back to the module constants."""
    h = getattr(_stack, "h", None) or {}
    tw = h.get("train_window") or {}
    try:
        return int(tw["from"]), int(tw["to"])
    except (KeyError, TypeError, ValueError):
        return YEAR_LO, YEAR_HI


def _dates(frm, to, step):
    from datetime import date, timedelta
    d0 = date.fromisoformat(frm)
    d1 = date.fromisoformat(to)
    n = (d1 - d0).days
    return [(d0 + timedelta(days=k)).isoformat() for k in range(0, n + 1, max(1, int(step)))]


def search_plan(self_dob, frm, to, step, batch=240):
    """The candidate list and how it will be batched — so the page can show real progress, not a guess."""
    ds = _dates(frm, to, step)
    ok = [d for d in ds if _acceptable(self_dob, d)]
    return {"candidates": len(ds), "scorable": len(ok),
            "unscorable": len(ds) - len(ok),
            "batches": (len(ds) + batch - 1) // batch, "batch": batch,
            "range": [YEAR_LO, YEAR_HI], "maxGap": MAX_GAP_YEARS}


def search_batch(self_dob, frm, to, step, bi, batch=240):
    """Score batch `bi`. Returns rows plus a count of candidates core.py would not accept.

    Batches are scored independently and nothing is retained between them: each call recomputes its own
    charts from the dates. That is slower than holding a table and it is the point.
    """
    ds = _dates(frm, to, step)
    lo, hi = bi * batch, min((bi + 1) * batch, len(ds))
    chunk = ds[lo:hi]
    if not chunk:
        return {"rows": [], "dropped": 0, "done": True}
    rows = [_row("self", f"c{lo+i}", self_dob, d) for i, d in enumerate(chunk)]
    p, P, _ = _build(rows)
    # core.py drops rows it will not model (births over 60 years apart), and it drops them from the middle
    # of the batch, so the surviving rows cannot be matched back by position. Re-derive which dates survive
    # using the same rule, and report the count rather than absorbing it.
    keep = []
    for i, d in enumerate(chunk):
        if _acceptable(self_dob, d):
            keep.append(i)
    dropped = len(chunk) - len(keep)
    out = []
    if len(p) == len(keep):
        bt = _stack.by_tradition(P)
        for j, i in enumerate(keep):
            out.append({"date": chunk[i], "p": float(p[j]),
                        "by_tradition": {k: float(v[j]) for k, v in bt.items()}})
    elif len(p):
        # The rule above did not reproduce core.py's filter exactly. Say so instead of misaligning dates
        # against scores, which would silently attribute one candidate's number to another.
        return {"rows": [], "dropped": len(chunk),
                "warning": f"batch {bi}: core.py kept {len(p)} of {len(chunk)} rows but the local filter "
                           f"predicted {len(keep)}; batch skipped rather than risk misaligning dates",
                "done": hi >= len(ds)}
    return {"rows": out, "dropped": dropped, "done": hi >= len(ds),
            "from": lo, "to": hi, "total": len(ds)}
