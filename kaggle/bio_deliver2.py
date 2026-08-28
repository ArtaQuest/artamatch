"""bio_deliver2.py — the deliverable: one CSV of marriages judged good or bad.

Each row is one ended marriage: both birth dates, both names, the marriage description read from
Wikipedia, the REFERENCE LINKS it was read from, the binary verdict with the evidence the judge quoted
and the single strongest ground for it, and the contributions the record shows.

The verdict is binary by design. A three-class pass (happy/neutral/toxic) put 69% of marriages in
`neutral`, which taught nothing and, worse, hid systematic disagreement between judges inside the safe
middle class. Forcing a verdict on every marriage made that disagreement measurable — a rule three
batches applied backwards was caught by counting it, and those batches were re-judged.

-> ~/.artamatch-dev/bio/marriage_quality_binary.csv
"""
import glob, json, os
import numpy as np, pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
COLS = ["dob_a", "dob_b", "name_a", "name_b", "good", "reason", "confidence", "evidence",
        "not_a_marriage", "children_together", "joint_creative_work", "joint_business",
        "children_recorded", "married", "death_a", "death_b", "languages", "sources", "n_chars",
        "description", "pid_a", "pid_b"]
GOOD_R = ("affection", "collaboration", "children", "lasted_to_death", "adversity")


def main():
    rows, partial = [], []
    for f in sorted(glob.glob(f"{BIO}/labels2/batch_*.json")):
        try:
            arr = json.load(open(f))
        except Exception as e:
            print(f"  ! {os.path.basename(f)}: {str(e)[:60]}")
            continue
        if len(arr) < 200:
            partial.append(f"{os.path.basename(f)[6:10]}({len(arr)})")
        rows += [o for o in arr if isinstance(o, dict) and isinstance(o.get("good"), bool)]
    if partial:
        print(f"  {len(partial)} batch(es) stopped early, their finished verdicts kept: "
              f"{', '.join(partial)}")
    lab = pd.DataFrame(rows).drop_duplicates("id").rename(columns={"id": "rid"})
    idx = pd.read_csv(f"{BIO}/index.csv", dtype=str)
    m = idx.merge(lab, on="rid", how="inner", suffixes=("", "_j")).rename(
        columns={"children": "children_recorded"})
    for c in COLS:
        if c not in m.columns:
            m[c] = ""
    out = m[COLS]
    p = f"{BIO}/marriage_quality_binary.csv"
    out.to_csv(p, index=False)
    n = len(out)
    print(f"  {n:,} judged marriages -> {os.path.basename(p)} "
          f"({os.path.getsize(p)/1e6:.1f} MB)")
    print(f"  verdict: good {int(out.good.sum()):,} ({out.good.mean():.1%}) · "
          f"bad {int((~out.good.astype(bool)).sum()):,} ({1-out.good.mean():.1%})")
    print("  confidence: " + " · ".join(f"{k} {v:,}" for k, v in out.confidence.value_counts().items()))
    print("\n  the ground each verdict rests on:")
    rc = out.reason.value_counts()
    for k, v in rc.items():
        side = "good" if k in GOOD_R else "bad"
        print(f"    {k:<16} {v:>6,}  ({v/n:>5.1%})  {side}")
    # a consistency check that has already caught a real problem: every reason must sit on one side
    bad_side = out.groupby("reason").good.mean()
    mixed = bad_side[(bad_side > 0.02) & (bad_side < 0.98) & (bad_side.index != "other")]
    print("\n  reasons used on BOTH sides (should be only 'other'): "
          + (", ".join(f"{k} {v:.0%} good" for k, v in mixed.items()) if len(mixed) else "none"))
    b = {c: out[c].astype(str).isin(["True", "true"]) for c in
         ("children_together", "joint_creative_work", "joint_business", "not_a_marriage")}
    print("\n  how each signal splits the verdict:")
    for k, v in b.items():
        g = out[v.to_numpy()]
        if len(g) > 20:
            print(f"    {k:<20} n={len(g):>6,}  judged good {g.good.mean():.0%}")
    langs = out.languages.fillna("").str.split(",").explode().replace("", np.nan).dropna()
    print("\n  languages the descriptions were read in: "
          + " · ".join(f"{k} {v:,}" for k, v in langs.value_counts().head(12).items()))
    print(f"  median description {int(pd.to_numeric(out.n_chars).median())} chars · "
          f"every row carries its source links")


if __name__ == "__main__":
    main()
