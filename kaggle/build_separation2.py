"""
build_separation2.py — natural (death) vs artificial (divorce) separation, from TWO BIRTH DATES and nothing else.

Operator 2026-08-22: "completely purge and drop start year ... just two dates. thats it", "expand the dataset",
"ensure its robust to 00 (missing) cases".

WHAT THE MODEL SEES: dob_a, dob_b. That is the entire input. The wedding date is gone — not masked, not
down-weighted, ABSENT from the published files — because it carries the era, and the era is what every previous
edition turned out to be reading. The end date and the death dates are used to derive the LABEL and then
discarded the same way. Whatever is left has to come from the two birth dates alone.

THE EXPANSION: the old cache was sliced by START year, so a union with no recorded start was never fetched.
This target needs no start, so the requirement is simply that the union ended — which QLever answers unsliced
in seconds. 97,447 statements across four relationship types (marriage, unmarried partnership, professional
partner, significant person) against 37,100 usable from the old cache.

THE LABEL: the explicit P1534 end cause where Wikidata records one, otherwise the end-vs-death rule, which was
validated against the explicit labels at 99.0%. Separation counts as artificial in all three forms Wikidata
spells it. Remarriage was tested as a third rule and REJECTED at 77.6% — see build_separation.py.

MISSING DATES ARE FIRST-CLASS. Wikidata stores every date as a full timestamp with the real precision beside
it, so a year-precision birth arrives looking exactly like 1 January. Rendered honestly here as YYYY-00-00, and
the counts are printed, because roughly a quarter of these births are year-only and a pipeline that silently
treats them as real days is measuring a day nobody recorded.
"""
import glob
import os
import re

import numpy as np
import pandas as pd

SRC = os.environ.get("AQ_ENDED", os.path.expanduser("~/.artamatch-dev/ended"))
OUT = os.environ.get("AQ_OUT", os.path.expanduser("~/.artamatch-dev/sep2"))
TEST_FRAC = float(os.environ.get("AQ_TEST_FRAC", "0.15"))
LABEL = "ended_in_divorce"
MISSING = "0000-00-00"

NATURAL = {"Q24037741", "Q99521170", "Q4", "Q90110620", "Q179115", "Q18646998", "Q10806", "Q161936",
           "Q10737", "Q210392", "Q267505", "Q1076426", "Q15747939", "Q21142718"}
ARTIFICIAL = {"Q93190", "Q701040", "Q5561011", "Q3456503", "Q1299585", "Q1142948", "Q759734", "Q100926628",
              "Q305418", "Q2914621", "Q5282797", "Q234213", "Q898987", "Q16557696", "Q65089925"}
MALE, FEMALE = "Q6581097", "Q6581072"

qid = lambda s: re.sub(r"[^Q0-9]", "", str(s)) if isinstance(s, str) else ""
yr = lambda s: pd.to_numeric(s.astype(str).str.extract(r"^[+-]?(\d{4})")[0], errors="coerce")


def render(ts, prec):
    """A Wikidata timestamp at its DECLARED precision: 11 = day, 10 = month, 9 or less = year."""
    if not isinstance(ts, str):
        return MISSING
    m = re.match(r"^[+-]?(\d{4})-(\d{2})-(\d{2})", ts.strip())
    if not m:
        return MISSING
    y, mo, d = m.groups()
    if y == "0000":
        return MISSING
    p = pd.to_numeric(prec, errors="coerce")
    if not np.isfinite(p):
        return f"{y}-00-00" if (mo, d) == ("01", "01") else f"{y}-{mo}-{d}"
    if p <= 9:
        return f"{y}-00-00"
    if p == 10:
        return f"{y}-{mo}-00"
    return f"{y}-00-00" if (mo, d) == ("01", "01") else f"{y}-{mo}-{d}"


def main():
    os.makedirs(OUT, exist_ok=True)
    frames = []
    for f in sorted(glob.glob(os.path.join(SRC, "P*.csv"))):
        d = pd.read_csv(f, dtype=str)
        d["rel"] = os.path.basename(f).split(".")[0]
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    print(f"  {len(df):,} ended-union statements across {df.rel.nunique()} relationship types", flush=True)

    for c in ("a", "b", "cause"):
        df[c] = df[c].map(qid) if c in df.columns else ""
    df["dob_a"] = [render(v, p) for v, p in zip(df.adob, df.aprec)]
    df["dob_b"] = [render(v, p) for v, p in zip(df.bdob, df.bprec)]

    # ── the label, and then every date that produced it is thrown away
    E, DA, DB = yr(df.end), yr(df.adeath), yr(df.bdeath)
    gap = np.fmin((E - DA).abs().fillna(9e9), (E - DB).abs().fillna(9e9))
    explicit = df["cause"].isin(NATURAL | ARTIFICIAL)
    truth = df["cause"].isin(ARTIFICIAL)
    inferable = (~explicit) & E.notna() & (DA.notna() | DB.notna())
    m = (explicit & E.notna() & (DA.notna() | DB.notna())).to_numpy()
    if m.sum() > 100:
        print(f"  end-vs-death rule agrees with the explicit P1534 on {int(m.sum()):,} statements: "
              f"{100*((gap.to_numpy()[m] > 1) == truth.to_numpy()[m]).mean():.1f}%", flush=True)
    df["y"] = np.where(explicit, truth.astype(int), (gap > 1).astype(int))
    df["src"] = np.where(explicit, "P1534", "end-vs-death")
    df = df[explicit | inferable].copy()
    print(f"  {int(explicit.sum()):,} labelled explicitly · {int((~explicit & inferable).sum()):,} by end-vs-death",
          flush=True)

    # one union appears on both partners' items; a pair whose two items disagree is dropped, not coin-tossed
    df["pair"] = [f"{min(x, y)}|{max(x, y)}" for x, y in zip(df.a, df.b)]
    g = df.groupby("pair")["y"].nunique()
    conflicted = set(g[g > 1].index)
    df = df[~df["pair"].isin(conflicted)].drop_duplicates("pair", keep="first")
    print(f"  {len(df):,} distinct pairs ({len(conflicted):,} dropped for disagreeing with themselves)", flush=True)

    df = df[(df.dob_a != MISSING) & (df.dob_b != MISSING)]
    print(f"  {len(df):,} with both birth dates", flush=True)

    sx = {}
    sp = os.path.join(SRC, "_sex.csv")
    if os.path.exists(sp):
        s = pd.read_csv(sp, dtype=str)
        sx = dict(zip(s["p"], s["sex"]))
    rows = []
    for r in df.itertuples(index=False):
        ga, gb = sx.get(r.a, ""), sx.get(r.b, "")
        if ga == MALE and gb == FEMALE:
            rows.append((r.dob_a, r.dob_b, r.y, r.a, r.b, r.rel, r.src))
        elif gb == MALE and ga == FEMALE:
            rows.append((r.dob_b, r.dob_a, r.y, r.b, r.a, r.rel, r.src))
    out = pd.DataFrame(rows, columns=["dob_a", "dob_b", LABEL, "pid_a", "pid_b", "rel", "src"])
    print(f"  {len(out):,} male x female pairs with a known sex for both", flush=True)

    ya, yb = yr(out.dob_a), yr(out.dob_b)
    out = out[(np.abs(ya - yb) <= 60) & (ya.between(1400, 2015)) & (yb.between(1400, 2015))]
    out["later_birth"] = np.fmax(ya, yb)

    # ── the split. The only inputs are the two births, so THAT is the axis: the test half is the most recently
    #    BORN couples, people the training half has never seen at any age.
    out = out.sort_values("later_birth", kind="mergesort").reset_index(drop=True)
    cut = int(len(out) * (1 - TEST_FRAC))
    boundary = out.later_birth.iloc[cut - 1]
    tr = out[out.later_birth <= boundary].copy()
    te = out[out.later_birth > boundary].copy()            # strictly later, no shared birth YEAR
    print(f"  temporal cut on the later birth: train to {int(boundary)}, test strictly after", flush=True)

    seen_p = set(tr.pid_a) | set(tr.pid_b)
    sh = te.pid_a.isin(seen_p) | te.pid_b.isin(seen_p)
    te = te[~sh]
    seen_d = (set(tr.dob_a) | set(tr.dob_b)) - {MISSING}
    sd = te.dob_a.isin(seen_d) | te.dob_b.isin(seen_d)
    te = te[~sd].copy()
    print(f"  dropped {int(sh.sum()):,} test rows sharing a PERSON and {int(sd.sum()):,} sharing a birth DATE",
          flush=True)

    te.insert(0, "id", [f"s{i:06d}" for i in range(len(te))])
    tr[["dob_a", "dob_b", LABEL]].to_csv(f"{OUT}/train.csv", index=False)
    te[["id", "dob_a", "dob_b"]].to_csv(f"{OUT}/test.csv", index=False)
    te[["id", LABEL]].to_csv(f"{OUT}/solution.csv", index=False)
    tr[["pid_a", "pid_b", "rel", "src", "later_birth"]].to_csv(f"{OUT}/_train_meta.csv", index=False)

    print(f"\n  wrote train.csv ({len(tr):,}) · test.csv ({len(te):,})  — columns: dob_a, dob_b, {LABEL}")
    print(f"  artificial: train {tr[LABEL].mean():.1%} · test {te[LABEL].mean():.1%}")
    day = lambda d, c: d[c].str.match(r"^\d{4}-(?!00)\d{2}-(?!00)\d{2}$").mean()
    yon = lambda d, c: d[c].str.match(r"^\d{4}-00-00$").mean()
    for nm, d in (("train", tr), ("test", te)):
        print(f"  {nm}: dob_a day-precision {day(d,'dob_a'):.1%} year-only {yon(d,'dob_a'):.1%} · "
              f"dob_b day-precision {day(d,'dob_b'):.1%} year-only {yon(d,'dob_b'):.1%}")
    print(f"  later birth: train {int(tr.later_birth.min())}-{int(tr.later_birth.max())} · "
          f"test {int(te.later_birth.min())}-{int(te.later_birth.max())}")
    print("  by relationship type: " + " · ".join(f"{k} {v:,}" for k, v in tr.rel.value_counts().items()))


if __name__ == "__main__":
    main()
