"""
dates.py — the one place that understands a birth date with `00` in it.

THE ENCODING. A published date is `YYYY-MM-DD` with `00` standing for a component Wikidata does not know:
`1850-03-17` is a day, `1850-03-00` a month, `1850-00-00` a year. The alternative — Wikidata's own padding,
which writes a year-precision birth as `1850-01-01` — makes an unknown day indistinguishable from a genuine
1 January birthday. 42.7% of rows carried such a date, so "is this a 1 January" was a readable proxy for how
well documented a person is, and documentation depth correlates with whether a child was recorded. Writing the
missingness down removes the coincidence and turns it into an input.

WHY EVERY CONSUMER NEEDS THIS AND NOT ITS OWN COPY. Three different things have to happen to such a date:
astronomy needs a real instant (`00` -> `01`), the model needs to know the precision it is looking at, and the
uncertainty window is what makes a year-precision chart honest rather than a chart of 1 January. Those three
were previously spread across the trainer, the evaluator and the grid builder, each with its own idea of what a
coarse date looked like — which is how a coarsening function and a training file can disagree without anything
failing.
"""

PRECISION_DAY, PRECISION_MONTH, PRECISION_YEAR = 11, 10, 9

# ── THE GRID, DEFINED ONCE ───────────────────────────────────────────────────────────────────────────────────
# Each partner's date is degraded independently over four levels, and two of the sixteen combinations are
# excluded from the score. This lives here because six different files need to agree on it — the scorer, the
# grid builder, the evaluator, the benchmark task, the publish gate and the page — and every time a constant
# like this has been restated in this project the copies have drifted.
LEVELS = ["full", "month", "year", "absent"]

EXCLUDED_CELLS = {
    # No input at all: both dates are the same placeholder, so nothing can be ranked and the cell would only
    # shift every competitor's average by a constant.
    "absent|absent",
    # Month precision on BOTH sides is a case that essentially does not occur. Of 107,698 couples only 859 men
    # and 1,017 women are known to the month, so the real data contains 18 such pairs — and on 18 rows an AUC
    # is noise: that group scored 0.8615 against 0.6201 for the 16,675-row day-by-day group. Simulating it
    # across every held-out couple asks the model about a situation the records almost never present.
    "month|month",
}

CELLS = [f"{a}|{b}" for a in LEVELS for b in LEVELS if f"{a}|{b}" not in EXCLUDED_CELLS]
N_CELLS = len(CELLS)          # 14

# How wide the uncertainty is, in days, for each precision. core.py takes this as `aWin`/`bWin` and it is the
# difference between "this chart is for 1 January" and "this chart is for a year we cannot place".
WINDOW = {PRECISION_DAY: 1.0, PRECISION_MONTH: 30.0, PRECISION_YEAR: 365.0}


def precision(d):
    """11 if the day is known, 10 if only the month, 9 if only the year."""
    if not isinstance(d, str) or len(d) != 10:
        raise ValueError(f"not a YYYY-MM-DD date: {d!r}")
    if d[8:10] != "00":
        return PRECISION_DAY
    if d[5:7] != "00":
        return PRECISION_MONTH
    return PRECISION_YEAR


def window(d):
    return WINDOW[precision(d)]


def concrete(d):
    """The same date with `00` replaced by `01`, so astropy and Swiss Ephemeris have an instant to work with.

    This is a representative, not a guess: the precision travels alongside it so a model can tell that the day
    was chosen rather than recorded. Anything that uses `concrete()` without also passing the precision is
    quietly claiming to know the day.
    """
    y, m, dd = d[:4], d[5:7], d[8:10]
    return f"{y}-{'01' if m == '00' else m}-{'01' if dd == '00' else dd}"


def coarsen(d, level):
    """Reduce a date to `full`, `month`, `year` — the precision grid's levels.

    IDEMPOTENT AND MONOTONE: coarsening a year-only date to `month` returns it unchanged, because precision that
    was never there cannot be added back. That property is what makes the grid honest — a `month|month` cell
    contains rows whose month was coarsened away and rows that never had one, and both look the same.
    """
    if level == "full":
        return d
    if level == "month":
        return d[:7] + "-00"
    if level == "year":
        return d[:4] + "-00-00"
    raise ValueError(f"unknown level {level!r}")


def couple_record(i, dob_man, dob_woman, label=0):
    """One row in the shape `core.load()` reads, with precision and window derived from the dates themselves.

    The trainer used to hardcode `aPrec: 11, bPrec: 11` — telling core that every day was known, including for
    the 34% of rows that only have a year. core has precision-aware features and a window field precisely for
    this, and they were being fed a constant.
    """
    return {"a": f"a{i}", "b": f"b{i}",
            "aDob": concrete(dob_man), "bDob": concrete(dob_woman),
            "aSex": "M", "bSex": "F",
            "aPrec": precision(dob_man), "bPrec": precision(dob_woman),
            "aWin": window(dob_man), "bWin": window(dob_woman),
            "label": int(label)}


def _selftest():
    assert precision("1850-03-17") == 11 and precision("1850-03-00") == 10 and precision("1850-00-00") == 9
    assert concrete("1850-00-00") == "1850-01-01"
    assert concrete("1850-03-00") == "1850-03-01"
    assert concrete("1850-03-17") == "1850-03-17"
    assert coarsen("1850-03-17", "month") == "1850-03-00"
    assert coarsen("1850-03-17", "year") == "1850-00-00"
    # Idempotent and monotone: coarsening cannot invent precision.
    assert coarsen("1850-00-00", "month") == "1850-00-00"
    assert coarsen("1850-03-00", "month") == "1850-03-00"
    assert coarsen("1850-03-00", "year") == "1850-00-00"
    assert window("1850-00-00") == 365.0
    r = couple_record(0, "1850-00-00", "1852-06-09")
    assert (r["aDob"], r["aPrec"], r["aWin"]) == ("1850-01-01", 9, 365.0)
    assert (r["bDob"], r["bPrec"], r["bWin"]) == ("1852-06-09", 11, 1.0)
    for bad in ("1850-3-17", "", "1850-03-17T00:00:00Z", None):
        try:
            precision(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted {bad!r}")
    print("  dates.py self-test passed")


if __name__ == "__main__":
    _selftest()
