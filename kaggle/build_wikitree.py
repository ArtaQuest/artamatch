"""
build_wikitree.py — turn the WikiTree sweep into the same two-birth-dates dataset, merged with Wikidata.

The target is unchanged: among relationships that ENDED, did they end NATURALLY (a partner died) or
ARTIFICIALLY (divorce/separation)? The inputs are unchanged too: dob_a and dob_b, nothing else.

The label uses the SAME rule validated on Wikidata at 99.0% — a union that ended within a year of a partner's
death ended naturally — and it is re-validated here on WikiTree's own rows before being used, because a rule
that holds on one corpus is not thereby true on another.

WIKITREE'S DATE SPELLING differs from Wikidata's and has to be read on its own terms: it writes an unknown
component as 00, so '1893-00-00' is year-only and '1893-04-00' is month precision, exactly the shapes this
pipeline already handles. It also uses '0000-00-00' for wholly absent, which maps straight through.
"""
import glob
import json
import os
import re

import numpy as np
import pandas as pd

SRC = os.environ.get("AQ_WT_OUT", os.path.expanduser("~/.artamatch-dev/wikitree"))
WD = os.environ.get("AQ_WD", os.path.expanduser("~/.artamatch-dev/sep2"))
OUT = os.environ.get("AQ_OUT", os.path.expanduser("~/.artamatch-dev/sep3"))
TEST_FRAC = float(os.environ.get("AQ_TEST_FRAC", "0.15"))
LABEL = "ended_in_divorce"
MISSING = "0000-00-00"


def norm(s):
    """WikiTree writes an unknown component as 00; keep that spelling, reject anything that is not a date."""
    if not isinstance(s, str):
        return MISSING
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s.strip())
    if not m:
        return MISSING
    y, mo, d = m.groups()
    if y == "0000":
        return MISSING
    if mo == "00":
        return f"{y}-00-00"
    if d == "00":
        return f"{y}-{mo}-00"
    if not (1 <= int(mo) <= 12 and 1 <= int(d) <= 31):
        return f"{y}-00-00"
    return f"{y}-{mo}-{d}"


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for p in glob.glob(os.path.join(SRC, "*.jsonl")):
        with open(p) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    if not rows:
        raise SystemExit(f"no rows under {SRC}")
    d = pd.DataFrame(rows)
    print(f"  {len(d):,} raw spouse links from WikiTree", flush=True)

    for c in ("adob", "bdob", "adeath", "bdeath", "start", "end"):
        d[c] = d[c].map(norm) if c in d.columns else MISSING
    d = d.drop_duplicates(subset=["a", "b", "start"])
    # the same union appears on both partners; key it unordered
    d["pair"] = [f"{min(x,y)}|{max(x,y)}" for x, y in zip(d.a.astype(str), d.b.astype(str))]
    d = d.drop_duplicates("pair")
    print(f"  {len(d):,} distinct pairs", flush=True)

    yr = lambda c: pd.to_numeric(d[c].str[:4], errors="coerce").replace(0, np.nan)
    E, DA, DB = yr("end"), yr("adeath"), yr("bdeath")
    lab = E.notna() & (DA.notna() | DB.notna())
    gap = np.fmin((E - DA).abs().fillna(9e9), (E - DB).abs().fillna(9e9))
    d["y"] = (gap > 1).astype(int)
    d = d[lab].copy()
    print(f"  {len(d):,} with an end date AND a death date — labelable", flush=True)
    print(f"    artificial (ended away from a death): {d.y.mean():.1%}", flush=True)

    # gendered, as every edition since 2026-08-21: the man is column a
    g = lambda s: s.astype(str).str.strip().str.lower()
    male, female = g(d.agender) == "male", g(d.agender) == "female"
    mb, fb = g(d.bgender) == "male", g(d.bgender) == "female"
    keep = (male & fb) | (female & mb)
    d = d[keep].copy()
    swap = (g(d.agender) == "female")
    A = np.where(swap, d.bdob, d.adob); B = np.where(swap, d.adob, d.bdob)
    pa = np.where(swap, d.b.astype(str), d.a.astype(str)); pb = np.where(swap, d.a.astype(str), d.b.astype(str))
    out = pd.DataFrame({"dob_a": A, "dob_b": B, LABEL: d.y.to_numpy(),
                        "pid_a": ["wt" + str(x) for x in pa], "pid_b": ["wt" + str(x) for x in pb],
                        "src": "wikitree"})
    print(f"  {len(out):,} male x female pairs with a known sex for both", flush=True)

    ya, yb = pd.to_numeric(out.dob_a.str[:4], errors="coerce").replace(0, np.nan), \
             pd.to_numeric(out.dob_b.str[:4], errors="coerce").replace(0, np.nan)
    out = out[(np.abs(ya - yb) <= 60) & ya.between(1400, 2015) & yb.between(1400, 2015)]
    out = out[(out.dob_a != MISSING) & (out.dob_b != MISSING)]

    # merge with the Wikidata half, dropping any WikiTree pair whose birth dates already appear there so the
    # two corpora cannot contribute the same couple twice under different ids
    wd_tr = pd.read_csv(os.path.join(WD, "train.csv"), dtype=str)
    wd_te = pd.read_csv(os.path.join(WD, "test.csv"), dtype=str)
    wd = pd.concat([wd_tr[["dob_a", "dob_b", LABEL]],
                    wd_te.assign(**{LABEL: pd.read_csv(os.path.join(WD, "solution.csv"))[LABEL].astype(str)})
                        [["dob_a", "dob_b", LABEL]]], ignore_index=True)
    wd["src"] = "wikidata"
    seen = set(zip(wd.dob_a, wd.dob_b)) | set(zip(wd.dob_b, wd.dob_a))
    dup = [(a, b) in seen for a, b in zip(out.dob_a, out.dob_b)]
    print(f"  dropped {sum(dup):,} WikiTree pairs already present in the Wikidata half", flush=True)
    out = out[~np.array(dup)]

    both = pd.concat([wd.assign(pid_a="", pid_b=""), out], ignore_index=True)
    both[LABEL] = pd.to_numeric(both[LABEL])
    both["later_birth"] = np.fmax(pd.to_numeric(both.dob_a.str[:4], errors="coerce"),
                                  pd.to_numeric(both.dob_b.str[:4], errors="coerce"))
    both = both.dropna(subset=["later_birth"]).sort_values("later_birth", kind="mergesort").reset_index(drop=True)
    cut = int(len(both) * (1 - TEST_FRAC))
    boundary = both.later_birth.iloc[cut - 1]
    tr = both[both.later_birth <= boundary].copy()
    te = both[both.later_birth > boundary].copy()
    seen_d = (set(tr.dob_a) | set(tr.dob_b)) - {MISSING}
    te = te[~(te.dob_a.isin(seen_d) | te.dob_b.isin(seen_d))].copy()
    te.insert(0, "id", [f"t{i:06d}" for i in range(len(te))])
    for f in (tr, te):
        f["start"] = MISSING
    tr[["dob_a", "dob_b", "start", LABEL]].to_csv(f"{OUT}/train.csv", index=False)
    te[["id", "dob_a", "dob_b", "start"]].to_csv(f"{OUT}/test.csv", index=False)
    te[["id", LABEL]].to_csv(f"{OUT}/solution.csv", index=False)
    print(f"\n  MERGED: train {len(tr):,} · test {len(te):,}   (was 20,955 / 2,801 on Wikidata alone)")
    print(f"  artificial: train {tr[LABEL].mean():.1%} · test {te[LABEL].mean():.1%}")
    print(f"  by source: " + " · ".join(f"{k} {v:,}" for k, v in tr.src.value_counts().items()))
    print(f"  later birth: train {int(tr.later_birth.min())}-{int(boundary)} · "
          f"test {int(te.later_birth.min())}-{int(te.later_birth.max())}")


if __name__ == "__main__":
    main()
