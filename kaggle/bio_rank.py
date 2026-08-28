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
import glob, json, os, re, sys
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
    # A second pass must not re-judge what is already judged: drop the couples that already carry a
    # label, keep the existing index rows, and number the new batches after the existing ones.
    judged_pairs, keep_idx, start_batch, start_rid = set(), None, 0, 0
    if os.environ.get("AQ_APPEND") and os.path.exists(f"{BIO}/index.csv"):
        old_idx = pd.read_csv(f"{BIO}/index.csv", dtype=str)
        done_rids = set()
        for lf in glob.glob(f"{BIO}/labels/batch_*.json"):
            try:
                for o in json.load(open(lf)):
                    if isinstance(o, dict) and o.get("id"):
                        done_rids.add(o["id"])
            except Exception:
                pass
        # keep every couple that is already judged OR still being judged in an open batch — a couple
        # must never be cut twice, or two judges label the same marriage under different ids
        queued_rids = set()
        for bf in glob.glob(f"{BIO}/batches/batch_*.json"):
            try:
                for o in json.load(open(bf)):
                    if isinstance(o, dict) and o.get("id"):
                        queued_rids.add(o["id"])
            except Exception:
                pass
        keep_idx = old_idx[old_idx.rid.isin(done_rids | queued_rids)].copy()
        judged_pairs = set(zip(keep_idx.pid_a, keep_idx.pid_b))
        start_batch = len(glob.glob(f"{BIO}/batches/batch_*.json"))
        nums = [int(r[1:]) for r in keep_idx.rid if str(r).startswith("r")]
        start_rid = (max(nums) + 1) if nums else 0
        q = q[~q.set_index(["pid_a", "pid_b"]).index.isin(judged_pairs)].copy()
        print(f"  appending: {len(keep_idx):,} already judged, {len(q):,} candidates remain, "
              f"new batches start at {start_batch:04d}", flush=True)
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
    q["rid"] = [f"r{start_rid + i:06d}" for i in range(len(q))]
    os.makedirs(f"{BIO}/batches", exist_ok=True)
    os.makedirs(f"{BIO}/labels", exist_ok=True)
    if keep_idx is None:
        for f in os.listdir(f"{BIO}/batches"):
            os.remove(f"{BIO}/batches/{f}")
    nb = start_batch
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
    if keep_idx is not None:
        pd.concat([keep_idx, q], ignore_index=True).to_csv(f"{BIO}/index.csv", index=False)
    else:
        q.to_csv(f"{BIO}/index.csv", index=False)
    print(f"  top {len(q):,} by quality -> batches {start_batch:04d}..{nb - 1:04d} of {PER}")
    print(f"    two-sided accounts: {int(both.reindex(q.index, fill_value=0).sum()) if len(q) else 0:,}"
          f" · median {int(q.n.median())} chars · median quality {q.quality.median():.1f}")
    print(f"    with children on record: {int(pd.to_numeric(q.children, errors='coerce').notna().sum()):,}"
          f" · with a recorded end cause: {int(q.cause.isin(ART | NAT).sum()):,}")


if __name__ == "__main__":
    main()
