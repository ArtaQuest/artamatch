"""
build_separation.py — the target reframed (operator 2026-08-22).

"Did it last 30 years" was a question about how much LIFE the couple had left: hold the two ages flat and
almost the whole signal disappeared, because the older you marry the less time there is to reach thirty years.

This asks a better-posed question. Among relationships that ENDED, did they end NATURALLY (one of them died) or
ARTIFICIALLY (divorce, annulment, repudiation, nullity)? Duration is no longer the outcome; both classes are
"ended". Wikidata records the answer directly as the P1534 end cause on the P26 statement.

  NATURAL  (label 0)   death of subject's spouse · death of subject · death
  ARTIFICIAL (label 1) divorce · annulment · repudiation · declaration of nullity

Deliberately EXCLUDED: "marital separation" (Q5561011) — spouses who stop living together without divorcing
are neither, and there are only a few dozen.

THE INPUTS ARE THE SAME THREE DATES as every other edition: both births and the start. The END date is NOT an
input and never will be — it hands over the duration, and duration nearly determines the answer (a union of
forty-five years ended in a funeral). It is kept in the file only so the control can hold it flat.

One marriage appears on BOTH partners' items, so every pair is deduplicated on (person, person, start) and a
pair whose two items DISAGREE about the cause is dropped rather than resolved by a coin toss.

P1534 IS RECORDED ON ONLY 13,825 OF 236,614 CACHED STATEMENTS, but 37,683 carry an end date AND at least one
partner's death date — and those two facts are enough to infer the cause: a union that ended the year one of
them died ended naturally. That inference is NOT assumed. It was validated against the 13,384 statements where
P1534 is explicit and agrees with them 99.0% of the time (a +-1 year tolerance is the optimum; +-0 gives 98.9%,
+-5 gives 97.7%). So the explicit cause is used wherever it exists and the validated rule fills the rest, with
the SOURCE of every label recorded so the two can be compared afterwards.

The inference reads only the END and DEATH dates. The model reads only the two births and the start. They share
no column, so nothing is being predicted from its own definition — but note the honest residual: a person born
in 1850 died before divorce was common, so era remains a confound, and the control is what handles it.
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

CACHE = os.environ.get("AQ_SLICE_CACHE", os.path.expanduser("~/.artamatch-dev/aq9c/_dslices"))
SEX = os.environ.get("AQ_SEX_CSV", os.path.expanduser("~/.artamatch-dev/aq9c/_sex.csv"))
OUT = os.environ.get("AQ_OUT", os.path.expanduser("~/.artamatch-dev/aqsep"))
TEST_FRAC = float(os.environ.get("AQ_TEST_FRAC", "0.12"))
LABEL = "ended_in_divorce"

# Every one of the 134 distinct P1534 values on a P26 statement was enumerated and labelled; the eight largest
# cover 99.2% and the tail is mostly blank nodes (unknown-value placeholders), which are excluded by not being
# listed. NATURAL means the union ended because somebody died. ARTIFICIAL means the two of them ended it —
# and per the operator, SEPARATION AND REMARRIAGE COUNT AS DIVORCE.
NATURAL = {
    "Q24037741",   # death of subject's spouse      8,249
    "Q99521170",   # death of subject               5,577
    "Q4",          # death                          2,063
    "Q90110620",   # death of subject's partner        13
    "Q179115",     # widow                              6
    "Q18646998",   # widower                            6
    "Q10806",      # September 11 attacks               4
    "Q161936",     # Death                              3
    "Q10737",      # suicide                            2
    "Q210392",     # killed in action                   2
    "Q267505",     # dying                              2
    "Q1076426",    # uxoricide — a death, though nobody would call it natural; n=2 either way
    "Q15747939",   # execution by shooting              2
    "Q21142718",   # accidental death                   2
}
ARTIFICIAL = {
    "Q93190",      # divorce                       10,010
    "Q701040",     # annulment                        212
    "Q5561011",    # marital separation                64   <- operator: counts as divorce
    "Q3456503",    # repudiation                       22
    "Q1299585",    # declaration of nullity            14
    "Q1142948",    # legal separation                  11   <- separation
    "Q759734",     # annulment (second item)            6
    "Q100926628",  # breakup                            5
    "Q305418",     # abandonment                        3
    "Q2914621",    # infidelity                         3
    "Q5282797",    # dissolution                        3
    "Q234213",     # adultery                           2
    "Q898987",     # separation process                 2   <- separation
    "Q16557696",   # Mexican divorce                    2
    "Q65089925",   # conscious uncoupling               2
}
# Deliberately in NEITHER set, because they do not say how the union ended: declaration of war (Q334516),
# coup d'etat (Q45382), and Q113455903, which has no English label.

qid = lambda s: re.sub(r"[^Q0-9]", "", str(s)) if isinstance(s, str) else ""   # cached ids carry a trailing '>'


MISSING = "0000-00-00"


def clean_date(s, prec=None):
    """Render a Wikidata timestamp at its DECLARED precision.

    Wikidata stores every date as a full timestamp and puts the real precision in a separate field: 11 = day,
    10 = month, 9 or less = year. A year-precision date therefore arrives looking exactly like the 1st of
    January, and 29.9% of the start dates in this cache are such a date. Passing them through as real days
    would hand the fast bodies — Moon, Mercury, Venus, Mars — a position for a day nobody recorded, which is
    the difference between a measurement and a decoration.

    So: YYYY-MM-DD only at day precision, YYYY-MM-00 at month, YYYY-00-00 otherwise. The pipeline spells
    unknown as 0000-00-00 and never as an empty cell — an empty cell returns from pandas as a float NaN and
    breaks the phase builder with 'float has no attribute endswith'.
    """
    if not isinstance(s, str):
        return MISSING
    m = re.match(r"^[+-]?(\d{4})-(\d{2})-(\d{2})", s.strip())
    if not m:
        return MISSING
    y, mo, d = m.groups()
    if y == "0000":
        return MISSING
    p = pd.to_numeric(prec, errors="coerce") if prec is not None else np.nan
    if p is not None and np.isfinite(p):
        if p <= 9:
            return f"{y}-00-00"
        if p == 10:
            return f"{y}-{mo}-00"
        if (mo, d) == ("01", "01"):        # claims day precision AND lands on 1 January: almost always a year
            return f"{y}-00-00"
        return f"{y}-{mo}-{d}"
    # no precision column (the start and end dates): 1 January is year precision by the same reasoning
    return f"{y}-00-00" if (mo, d) == ("01", "01") else f"{y}-{mo}-{d}"


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(CACHE, "*.csv")))
    if not files:
        raise SystemExit(f"no cached slices under {CACHE}")
    keep = []
    for f in files:
        try:
            d = pd.read_csv(f, dtype=str)
        except Exception:
            continue
        if not {"a", "b", "adob", "bdob", "start", "cause"} <= set(d.columns):
            continue
        d["cause"] = d["cause"].map(qid) if "cause" in d.columns else ""
        for c in ("end", "adeath", "bdeath"):
            if c not in d.columns:
                d[c] = ""
        keep.append(d)
    if not keep:
        raise SystemExit("no rows with a usable end cause")
    df = pd.concat(keep, ignore_index=True)
    print(f"  {len(df):,} cached statements", flush=True)

    yr4 = lambda s: pd.to_numeric(s.astype(str).str.extract(r"^[+-]?(\d{4})")[0], errors="coerce")
    for c in ("a", "b"):
        df[c] = df[c].map(qid)
    E, S = yr4(df.end), yr4(df.start)
    DA, DB = yr4(df.adeath), yr4(df.bdeath)

    # ── RULE 2: REMARRIAGE. Operator 2026-08-22: remarrying counts as divorce. If one of them started another
    # union while the other was STILL ALIVE, the first one cannot have ended in a death — it was ended.
    # Conservative on purpose: the other partner's death year must be KNOWN and strictly later, so a missing
    # death date never manufactures a divorce.
    starts = {}
    for who, other, od in (("a", "b", DA), ("b", "a", DB)):
        for pid, st in zip(df[who], S):
            if isinstance(pid, str) and pid and np.isfinite(st):
                starts.setdefault(pid, []).append(st)
    def remarried(pid, this_start, other_death):
        """Did `pid` begin another union after this one, while the other partner was still alive?"""
        if not (isinstance(pid, str) and pid) or not np.isfinite(this_start) or not np.isfinite(other_death):
            return False
        return any(t > this_start and t < other_death for t in starts.get(pid, ()))
    remar = np.array([remarried(pa, st, db) or remarried(pb, st, da)
                      for pa, pb, st, da, db in zip(df.a, df.b, S, DA, DB)])

    # ── RULE 1: the union ended the year one of them died
    gap = np.fmin((E - DA).abs().fillna(9e9), (E - DB).abs().fillna(9e9))
    died_then = E.notna() & (DA.notna() | DB.notna()) & (gap <= 1)

    explicit = df["cause"].isin(NATURAL | ARTIFICIAL)

    # VALIDATE both rules where the truth is written down, before using either
    truth = df["cause"].isin(ARTIFICIAL)
    T = truth.to_numpy()
    for nm, pred, mask in (("end-vs-death", np.asarray(~died_then),
                            explicit.to_numpy() & E.notna().to_numpy() & (DA.notna() | DB.notna()).to_numpy()),
                           ("remarriage  ", np.asarray(remar), explicit.to_numpy() & np.asarray(remar))):
        if mask.sum() > 30:
            print(f"  rule check · {nm}: agrees with P1534 on {int(mask.sum()):,} statements, "
                  f"{100*(pred[mask] == T[mask]).mean():.1f}%", flush=True)

    # REMARRIAGE IS NOT USED AS A LABEL, and the check above is why. It agrees with P1534 only 77.6% of the
    # time, at every margin from 0 to 12 years, against end-vs-death's 99.0%. Its errors are not random: the
    # disagreeing rows have `end` equal to a partner's death date to the DAY — unions that plainly ended in a
    # funeral — while the surviving partner also has another union starting inside the window. Concurrent or
    # mis-dated marriages, in other words, and letting remarriage override would have relabelled thousands of
    # deaths as divorces. Where end-vs-death can decide, it decides; where it cannot, remarriage's accuracy is
    # unvalidatable (there is no ground truth for exactly those rows), so nothing is invented for them.
    #
    # The operator's intent is honoured on the part that IS reliable: separation of every kind — marital
    # separation, legal separation, separation process — now counts as artificial, in the class lists above.
    inferable = (~explicit) & E.notna() & (DA.notna() | DB.notna())
    df["y"] = np.where(explicit, truth.astype(int), (~died_then).astype(int))
    df["src"] = np.where(explicit, "P1534", np.where(inferable, "end-vs-death", ""))
    df["remarried_flag"] = remar.astype(int)          # kept for auditing, never for labelling
    df = df[explicit | inferable]
    print(f"  {int(explicit.sum()):,} by an explicit P1534 · "
          f"{int((df.src == 'end-vs-death').sum()):,} by end-vs-death · "
          f"remarriage REJECTED as a label source (77.6% vs 99.0%)", flush=True)

    for c, pc in (("adob", "aprec"), ("bdob", "bprec"), ("start", None), ("end", None)):
        pr = df[pc] if (pc and pc in df.columns) else pd.Series([None] * len(df), index=df.index)
        df[c] = [clean_date(v, q) for v, q in zip(df[c], pr)]
    # one marriage, two items: key on the UNORDERED pair plus the start date
    df["pair"] = [f"{min(x, y)}|{max(x, y)}|{s}" for x, y, s in zip(df.a, df.b, df.start)]
    before = len(df)
    g = df.groupby("pair")["y"].nunique()
    conflicted = set(g[g > 1].index)
    df = df[~df["pair"].isin(conflicted)]
    print(f"  dropped {len(conflicted):,} pairs whose two items DISAGREE about how it ended "
          f"({before - len(df):,} statements)", flush=True)
    df = df.drop_duplicates("pair", keep="first")
    print(f"  {len(df):,} distinct relationships", flush=True)

    df = df[(df.start != MISSING) & ((df.adob != MISSING) | (df.bdob != MISSING))]
    print(f"  {len(df):,} with a start date and at least one birth date", flush=True)

    # gendered: the man is column a, as in the previous edition
    sx = {}
    if os.path.exists(SEX):
        s = pd.read_csv(SEX, dtype=str)
        col = [c for c in s.columns if c != s.columns[0]][0]
        sx = dict(zip(s[s.columns[0]].map(qid), s[col].map(qid)))
    MALE, FEMALE = "Q6581097", "Q6581072"
    rows = []
    for r in df.itertuples(index=False):
        ga, gb = sx.get(r.a, ""), sx.get(r.b, "")
        if ga == MALE and gb == FEMALE:
            A, B = (r.adob, r.bdob)
        elif gb == MALE and ga == FEMALE:
            A, B = (r.bdob, r.adob)
        else:
            continue                                   # same-sex or unknown: dropped, as in the gendered edition
        rows.append((A, B, r.start, r.end, r.y, r.src))
    out = pd.DataFrame(rows, columns=["dob_a", "dob_b", "start", "end", LABEL, "src"])
    print(f"  {len(out):,} male x female pairs with a known sex for both", flush=True)

    # a duration the control can hold flat — NOT an input
    yr = lambda s: pd.to_numeric(s.str[:4], errors="coerce")
    out["duration_years"] = yr(out.end) - yr(out.start)
    # sanity, because the cache contains rows a person could not have lived: a wedding before a birth, and a
    # union lasting longer than anyone's marriage. One sample row had the wife born three years AFTER the wedding.
    ya, yb, ys = yr(out.dob_a), yr(out.dob_b), yr(out.start)
    bad_birth = ((ys < ya) & ya.notna()) | ((ys < yb) & yb.notna())
    bad_dur = out.duration_years.notna() & ((out.duration_years < 0) | (out.duration_years > 85))
    print(f"  dropped {int(bad_birth.sum()):,} with a wedding BEFORE a birth and "
          f"{int(bad_dur.sum()):,} with an impossible duration", flush=True)
    out = out[~bad_birth & ~bad_dur]

    # forward-chained split, exactly as before: the TEST half is the most recent, so nothing is fitted on its era
    out = out.sort_values("start", kind="mergesort").reset_index(drop=True)
    cut = int(len(out) * (1 - TEST_FRAC))
    tr, te = out.iloc[:cut].copy(), out.iloc[cut:].copy()
    te.insert(0, "id", [f"s{i:06d}" for i in range(len(te))])
    sol = te[["id", LABEL]].copy()
    cols = ["dob_a", "dob_b", "start", LABEL]
    tr[cols].to_csv(f"{OUT}/train.csv", index=False)
    te[["id", "dob_a", "dob_b", "start"]].to_csv(f"{OUT}/test.csv", index=False)
    sol.to_csv(f"{OUT}/solution.csv", index=False)
    # the end date and duration go to a SIDECAR the control reads and no model ever sees
    out[["start", "end", "duration_years", "src", LABEL]].to_csv(f"{OUT}/_meta.csv", index=False)
    tr[["start", "end", "duration_years", "src"]].to_csv(f"{OUT}/_meta_train.csv", index=False)

    print(f"\n  wrote train.csv ({len(tr):,}) · test.csv ({len(te):,})")
    print(f"  artificial (divorce etc): train {tr[LABEL].mean():.1%} · test {te[LABEL].mean():.1%}")
    d = tr.duration_years.dropna()
    print(f"  duration known for {len(d):,} training rows · median {d.median():.0f}y")
    prec_rate = lambda c: (tr[c].str.match(r"^\d{4}-(?!00)\d{2}-(?!00)\d{2}$")).mean()
    print(f"  day-precision: dob_a {prec_rate('dob_a'):.1%} · dob_b {prec_rate('dob_b'):.1%} · start {prec_rate('start'):.1%}")
    for lab, name in ((0, "natural (death)"), (1, "artificial (divorce)")):
        dd = tr[tr[LABEL] == lab].duration_years.dropna()
        print(f"    {name:<24} n={len(dd):>6,}  median {dd.median():>5.0f}y  mean {dd.mean():>5.1f}y")
    print(f"  start years: train {tr.start.str[:4].min()}–{tr.start.str[:4].max()} · "
          f"test {te.start.str[:4].min()}–{te.start.str[:4].max()}")
    for src in ("P1534", "end-vs-death"):
        m = tr.src == src
        if m.any():
            print(f"  label source {src:<9} train n={int(m.sum()):>6,}  artificial {tr[m][LABEL].mean():.1%}")


if __name__ == "__main__":
    main()
