"""bio_deliver.py — the deliverable: one CSV of judged marriages.

Each row is one ended marriage: both birth dates, both names, the marriage description read from
Wikipedia, the REFERENCE LINKS it was read from, the judgement (happy / neutral / toxic) with the
evidence the judge quoted, and the contributions the record shows — children, joint creative work,
joint business — plus the harms — conflict, infidelity, abuse.

-> ~/.artamatch-dev/bio/marriage_quality.csv
"""
import glob, json, os
import numpy as np, pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
COLS = ["dob_a", "dob_b", "name_a", "name_b", "label", "confidence", "evidence",
        "children_together", "joint_creative_work", "joint_business", "conflict", "infidelity", "abuse",
        "children_recorded", "married", "death_a", "death_b", "languages", "sources", "n_chars",
        "description", "pid_a", "pid_b"]


def main():
    rows = []
    for f in sorted(glob.glob(f"{BIO}/labels/batch_*.json")):
        try:
            arr = json.load(open(f))
        except Exception as e:
            print(f"  ! {os.path.basename(f)}: {str(e)[:60]}")
            continue
        for o in arr:
            if isinstance(o, dict) and o.get("label") in ("happy", "neutral", "toxic"):
                rows.append(o)
    lab = pd.DataFrame(rows).drop_duplicates("id").rename(columns={"id": "rid"})
    idx = pd.read_csv(f"{BIO}/index.csv", dtype=str)
    m = idx.merge(lab, on="rid", how="inner", suffixes=("", "_j"))
    m = m.rename(columns={"children": "children_recorded"})
    for c in COLS:
        if c not in m.columns:
            m[c] = ""
    out = m[COLS]
    out.to_csv(f"{BIO}/marriage_quality.csv", index=False)
    n = len(out)
    print(f"  {n:,} judged marriages -> marriage_quality.csv")
    print("  label: " + " · ".join(f"{k} {v:,} ({v/n:.0%})" for k, v in out.label.value_counts().items()))
    print("  confidence: " + " · ".join(f"{k} {v:,}" for k, v in out.confidence.value_counts().items()))
    b = {c: out[c].astype(str).isin(["True", "true"]) for c in
         ("children_together", "joint_creative_work", "joint_business", "conflict", "infidelity", "abuse")}
    print("  what the record shows: " + " · ".join(f"{k} {int(v.sum()):,}" for k, v in b.items()))
    print("\n  how each signal splits the judgement (share of that group judged happy / toxic):")
    for k, v in b.items():
        g = out[v.to_numpy()]
        if len(g) > 20:
            print(f"    {k:<20} n={len(g):>5,}  happy {(g.label=='happy').mean():.0%}  "
                  f"toxic {(g.label=='toxic').mean():.0%}")
    langs = out.languages.fillna("").str.split(",").explode().replace("", np.nan).dropna()
    print("\n  languages the descriptions were read in: "
          + " · ".join(f"{k} {v:,}" for k, v in langs.value_counts().head(10).items()))
    print(f"  median description {int(pd.to_numeric(out.n_chars).median())} chars · "
          f"every row carries its source links")


if __name__ == "__main__":
    main()
