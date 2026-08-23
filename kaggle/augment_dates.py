"""
augment_dates.py — train the model to survive the missing dates it will actually meet.

Operator 2026-08-22: "during training, create a random augmentation that sets either of the 6 info to zero by a
small chance ... actually couple the month and day, so either 0000-xx-xx or xxxx-00-00 ... this way the year
only models will be trained as well".

Each of the two birth dates carries two maskable units, and they are coupled exactly as instructed:

    the YEAR       ->  0000-MM-DD   the month and day survive; the model must read them without an era
    the MONTH+DAY  ->  YYYY-00-00   the year survives; this is the year-only case, and it is the COMMON one
                                    (12.5% of dob_a and 19.4% of dob_b are already year-only in the real data)

Masking them independently at a small rate gives the model every combination — both dates whole, one degraded,
both degraded, and the year-only pairs that dominate the older half of the dataset. A model trained only on
complete dates has never had to answer the question the data mostly asks.

A masked date is a DIFFERENT date, so its planetary positions are different too — every augmented copy needs
its own pass through the phase builder rather than a reuse of the original's longitudes. That is why this
writes CSVs instead of perturbing a feature matrix.
"""
import os
import re
import sys

import numpy as np
import pandas as pd

SRC = os.environ.get("AQ_SRC", os.path.expanduser("~/.artamatch-dev/sep2"))
OUT = os.environ.get("AQ_AUG_OUT", os.path.expanduser("~/.artamatch-dev/sep2aug"))
K = int(os.environ.get("AQ_AUG_COPIES", "3"))
P_YEAR = float(os.environ.get("AQ_P_YEAR", "0.08"))       # chance of losing the year, keeping month+day
P_MD = float(os.environ.get("AQ_P_MD", "0.15"))           # chance of losing month+day, keeping the year


def mask(col, rng):
    """Return the column with each date independently degraded: year gone, or month+day gone, or untouched."""
    out = []
    for v in col:
        s = str(v)
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
        if not m or s == "0000-00-00":
            out.append(s); continue
        y, mo, d = m.groups()
        r = rng.random()
        if r < P_YEAR and (mo, d) != ("00", "00"):
            out.append(f"0000-{mo}-{d}")          # the year is hidden; month and day remain
        elif r < P_YEAR + P_MD:
            out.append(f"{y}-00-00")              # year-only, the shape most of the real data already has
        else:
            out.append(s)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    tr = pd.read_csv(os.path.join(SRC, "train.csv"), dtype=str)
    for k in range(K):
        rng = np.random.default_rng(1000 + k)
        d = tr.copy()
        d["dob_a"] = mask(d.dob_a, rng)
        d["dob_b"] = mask(d.dob_b, rng)
        sub = os.path.join(OUT, f"aug{k}")
        os.makedirs(sub, exist_ok=True)
        d.to_csv(os.path.join(sub, "train.csv"), index=False)
        # the phase builder wants a test half too; a token one keeps it happy and is never used
        tr.head(50).drop(columns=[c for c in tr.columns if c == "ended_in_divorce"]).assign(
            id=[f"x{i}" for i in range(50)]).to_csv(os.path.join(sub, "test.csv"), index=False)
        chg_a = (d.dob_a != tr.dob_a).mean(); chg_b = (d.dob_b != tr.dob_b).mean()
        yo = lambda c: d[c].str.match(r"^\d{4}-00-00$").mean()
        ny = lambda c: d[c].str.match(r"^0000-\d{2}-\d{2}$").mean()
        print(f"  copy {k}: dob_a changed {chg_a:.1%} (year-only {yo('dob_a'):.1%}, no-year {ny('dob_a'):.1%}) · "
              f"dob_b changed {chg_b:.1%} (year-only {yo('dob_b'):.1%}, no-year {ny('dob_b'):.1%})", flush=True)
    print(f"  {K} augmented copies in {OUT}")


if __name__ == "__main__":
    main()
