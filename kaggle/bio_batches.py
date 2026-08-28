"""bio_batches.py — split the qualifying marriages into classification batches.

A batch carries ONLY what a judgement of the relationship needs: the two names, the marriage
description assembled from both Wikipedia articles, the couple's children count, whether they share a
notable work, and Wikidata's recorded end cause when there is one. Birth dates are deliberately NOT
included: the labels must not be able to encode the era, because the era is exactly what the
astrological features read. (Dates inside the prose are left alone; the rubric forbids judging by era.)

-> ~/.artamatch-dev/bio/batches/batch_XXXX.json  and  index.csv mapping row ids back to couples.
"""
import json, os, sys
import pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
PER = int(os.environ.get("AQ_PER_BATCH", "120"))
MIN_CHARS = 100

ART = {"Q93190", "Q701040", "Q5561011", "Q3456503", "Q1299585", "Q1142948", "Q759734", "Q100926628",
       "Q305418", "Q2914621", "Q5282797", "Q234213", "Q898987", "Q16557696", "Q65089925"}
NAT = {"Q24037741", "Q99521170", "Q4", "Q90110620", "Q179115", "Q18646998", "Q10806", "Q161936",
       "Q10737", "Q210392", "Q267505", "Q1076426", "Q15747939", "Q21142718"}


def main():
    m = pd.read_csv(f"{BIO}/marriages.csv", dtype=str)
    m["n"] = pd.to_numeric(m.n_chars, errors="coerce").fillna(0)
    weak = pd.to_numeric(m.get("weak_name", 0), errors="coerce").fillna(0)
    q = m[(m.n > MIN_CHARS) & m.name_a.notna() & m.name_b.notna() & (weak == 0)].copy()
    q = q.reset_index(drop=True)
    q["rid"] = [f"r{i:06d}" for i in range(len(q))]
    os.makedirs(f"{BIO}/batches", exist_ok=True)
    os.makedirs(f"{BIO}/labels", exist_ok=True)
    kids = pd.to_numeric(q.children, errors="coerce")
    nb = 0
    for b in range(0, len(q), PER):
        chunk = q.iloc[b:b + PER]
        items = []
        for _, r in chunk.iterrows():
            k = pd.to_numeric(r.children, errors="coerce")
            cause = ""
            if isinstance(r.cause, str) and r.cause in ART:
                cause = "record says it ended by divorce/annulment/separation"
            elif isinstance(r.cause, str) and r.cause in NAT:
                cause = "record says it ended by death"
            items.append({"id": r.rid, "him": r.name_a, "her": r.name_b,
                          "children_together": int(k) if pd.notna(k) else None,
                          "shares_a_notable_work": None,
                          "ended": cause, "description": r.description})
        json.dump(items, open(f"{BIO}/batches/batch_{nb:04d}.json", "w"), ensure_ascii=False, indent=1)
        nb += 1
    q[["rid", "pid_a", "pid_b", "name_a", "name_b", "dob_a", "dob_b", "fullprec", "married",
       "death_a", "death_b", "cause", "children", "n_chars"]].to_csv(f"{BIO}/index.csv", index=False)
    print(f"  {len(q):,} marriages over {MIN_CHARS} chars -> {nb} batches of {PER}")
    print(f"    full-precision both dates: {int(pd.to_numeric(q.fullprec).sum()):,}")
    print(f"    with children on record: {int((kids.fillna(0) > 0).sum()):,}")
    print(f"    median description {int(q.n.median())} chars")


if __name__ == "__main__":
    main()
