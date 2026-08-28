"""bio_rank.py — pick the 10,000 best marriages to judge, and cut them into classification batches.

"Best" is not "longest". A description earns its place by being about the RELATIONSHIP and by being
checkable:
  · both dates precise to the day        — a chart needs a day, so nothing else can be modelled
  · the partner is named, not guessed    — the weak-name guard already dropped surname-only mismatches
  · relationship density                 — how much of the prose actually speaks of the marriage
  · two-sided                            — assembled from BOTH partners' articles, so the account is
                                           corroborated rather than one article's telling
  · structured facts present             — children count and a recorded end cause give the judgement
                                           something beyond prose

-> ~/.artamatch-dev/bio/batches/batch_XXXX.json (200 each) + index.csv
"""
import json, os, re, sys
import numpy as np, pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
TOP = int(os.environ.get("AQ_TOP", "10000"))
PER = int(os.environ.get("AQ_PER_BATCH", "200"))
REL = re.compile(r"\b(marri|wed|wife|husband|spouse|divorc|separat|widow|engage|couple|honeymoon|"
                 r"elope|affair|mistress|lover|son|daughter|child|children|adopt|abus|violen|"
                 r"affection|devoted|happy|unhappy|estranged|reconcil|collaborat|co-found|together)", re.I)
ART = {"Q93190", "Q701040", "Q5561011", "Q3456503", "Q1299585", "Q1142948", "Q759734", "Q100926628",
       "Q305418", "Q2914621", "Q5282797", "Q234213", "Q898987", "Q16557696", "Q65089925"}
NAT = {"Q24037741", "Q99521170", "Q4", "Q90110620", "Q179115", "Q18646998", "Q10806", "Q161936",
       "Q10737", "Q210392", "Q267505", "Q1076426", "Q15747939", "Q21142718"}


def main():
    m = pd.read_csv(f"{BIO}/marriages.csv", dtype=str)
    m["n"] = pd.to_numeric(m.n_chars, errors="coerce").fillna(0)
    m["weak"] = pd.to_numeric(m.get("weak_name", 0), errors="coerce").fillna(0)
    m["fp"] = pd.to_numeric(m.fullprec, errors="coerce").fillna(0)
    ti = pd.read_csv(f"{BIO}/titles.csv", dtype=str).fillna("")
    has_art = set(ti.qid[ti.title != ""])
    q = m[(m.n > 100) & (m.weak == 0) & (m.fp == 1) & m.name_a.notna() & m.name_b.notna()].copy()
    print(f"  {len(m):,} described · {len(q):,} chart-ready, name-confirmed, over 100 chars", flush=True)
    rel = q.description.fillna("").map(lambda s: len(REL.findall(s)))
    dens = rel / (q.n / 200.0).clip(lower=1)                     # relationship words per 200 chars
    both = (q.pid_a.isin(has_art) & q.pid_b.isin(has_art)).astype(float)
    kids = pd.to_numeric(q.children, errors="coerce")
    cause_known = q.cause.isin(ART | NAT).astype(float)
    q["quality"] = (2.0 * both
                    + 2.0 * np.log1p(rel)
                    + 1.5 * dens.clip(upper=6)
                    + (q.n.clip(upper=1800) / 600.0)
                    + 0.5 * kids.notna().astype(float)
                    + 0.5 * cause_known)
    q = q.sort_values("quality", ascending=False).head(TOP).reset_index(drop=True)
    q["rid"] = [f"r{i:06d}" for i in range(len(q))]
    os.makedirs(f"{BIO}/batches", exist_ok=True)
    os.makedirs(f"{BIO}/labels", exist_ok=True)
    for f in os.listdir(f"{BIO}/batches"):
        os.remove(f"{BIO}/batches/{f}")
    nb = 0
    for b in range(0, len(q), PER):
        chunk = q.iloc[b:b + PER]
        items = []
        for _, r in chunk.iterrows():
            k = pd.to_numeric(r.children, errors="coerce")
            ended = ""
            if isinstance(r.cause, str) and r.cause in ART:
                ended = "the record says this marriage ended by divorce, annulment or separation"
            elif isinstance(r.cause, str) and r.cause in NAT:
                ended = "the record says this marriage ended when one of them died"
            items.append({"id": r.rid, "him": r.name_a, "her": r.name_b,
                          "children_together": int(k) if pd.notna(k) else None,
                          "ended": ended, "description": r.description})
        json.dump(items, open(f"{BIO}/batches/batch_{nb:04d}.json", "w"), ensure_ascii=False, indent=1)
        nb += 1
    q.to_csv(f"{BIO}/index.csv", index=False)
    print(f"  top {len(q):,} by quality -> {nb} batches of {PER}")
    print(f"    two-sided accounts: {int(both.reindex(q.index, fill_value=0).sum()) if len(q) else 0:,}"
          f" · median {int(q.n.median())} chars · median quality {q.quality.median():.1f}")
    print(f"    with children on record: {int(pd.to_numeric(q.children, errors='coerce').notna().sum()):,}"
          f" · with a recorded end cause: {int(q.cause.isin(ART | NAT).sum()):,}")


if __name__ == "__main__":
    main()
