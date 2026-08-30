"""bio_batches3.py — build RUBRIC3 judging batches, gated so we do not spend a judgement on a
marriage whose record cannot produce a label.

WHY A GATE. Under RUBRIC3 a row is only used if |warmth - trouble| >= 2, so a bare genealogical
entry is judged and then thrown away. On the previous corpus only 32% of judgements produced a
usable label. Requiring a description of at least 250 characters carrying at least two relationship
cue words raises that to 0.599 labels per judgement — 88% more label for the same work.

WHY THE GATE IS SAFE. It selects on record richness, which is the confound this whole rebuild
exists to remove, so it was measured rather than assumed. On the 10,000 already judged:

    gate                       judged   labels   labels/judgement   era AUC after balancing
    judge everything           10,000    3,189              0.319                    0.5023
    >=2 cue words               4,083    2,296              0.562                    0.4933
    >=250 chars AND >=2 cues    3,682    2,207              0.599                    0.4952

and its recall of labellable rows is flat across the centuries — 74.4% / 71.7% / 70.6% / 72.8% for
births in 1700-1800 / 1800-50 / 1850-1900 / 1900-50. It costs about 30% of the labellable rows and
costs nothing in era balance, which is the trade worth making when the candidate pool is far larger
than the number we can judge.

BIRTH DATES ARE NOT IN THE BATCH, exactly as in bio_batches.py: the labels must not be able to
encode the era, because the era is what the astrological features read. Dates are used here only to
report the era spread of the pool, and are dropped before anything is written.

Writes -> ~/.artamatch-dev/bio/batches3/batch_XXXX.json  +  pool3.csv (the gate's decisions, for audit)
Runs nothing and judges nothing.
"""
import json, os, re, sys
import numpy as np
import pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
PER = int(os.environ.get("AQ_PER_BATCH", "60"))
MIN_CHARS = int(os.environ.get("AQ_MIN_CHARS", "250"))
MIN_CUES = int(os.environ.get("AQ_MIN_CUES", "2"))
LIMIT = int(os.environ.get("AQ_LIMIT", "0"))          # 0 = the whole gated pool; set small for a pilot

# Relationship cue words. Multilingual on purpose — a fifth of the corpus is not in English, and an
# English-only list would gate out whole languages, which would be a selection far worse than length.
CUES = (r"love|loved|devot|affection|happ|adore|beloved|inseparable|grief|mourn|widow|"
        r"divorc|affair|mistress|adulter|separat|estrang|abus|violen|unhapp|quarrel|"
        r"litigat|scandal|desert|abandon|bigam|collaborat|co-wrote|co-found|partnership|"
        r"together|jointly|his wife|her husband|the couple|marriage was|remarri|"
        r"liebe|ehe|scheidung|amour|épous|amore|matrimon|esposa|marido|"
        r"брак|развод|любов|結婚|離婚|婚姻|زواج|طلاق")

ART = {"Q93190", "Q701040", "Q5561011", "Q3456503", "Q1299585", "Q1142948", "Q759734", "Q100926628",
       "Q305418", "Q2914621", "Q5282797", "Q234213", "Q898987", "Q16557696", "Q65089925"}
NAT = {"Q24037741", "Q99521170", "Q4", "Q90110620", "Q179115", "Q18646998", "Q10806", "Q161936",
       "Q10737", "Q210392", "Q267505", "Q1076426", "Q15747939", "Q21142718"}


def main():
    m = pd.read_csv(f"{BIO}/marriages.csv", dtype=str)
    m["desc"] = m.description.fillna("").astype(str)
    m["nc"] = m.desc.str.len()
    m["ncue"] = m.desc.str.lower().str.count(CUES)
    weak = pd.to_numeric(m.get("weak_name", 0), errors="coerce").fillna(0)
    ya = pd.to_numeric(m.dob_a.astype(str).str[:4], errors="coerce")
    yb = pd.to_numeric(m.dob_b.astype(str).str[:4], errors="coerce")
    m["mid"] = (ya + yb) / 2

    elig = (weak == 0) & m.name_a.notna() & m.name_b.notna() & m.mid.notna()
    gate = elig & (m.nc >= MIN_CHARS) & (m.ncue >= MIN_CUES)
    q = m[gate].copy().reset_index(drop=True)
    q["rid"] = [f"s{i:06d}" for i in range(len(q))]     # s-prefixed so it can never collide with r*

    # Order by decade round-robin, so that ANY prefix of the batch list is already era-spread. A pilot
    # or an interrupted run therefore yields a balanced sample rather than whichever century sorted
    # first, and no batch is all-Victorian.
    q["dec"] = (q.mid // 10 * 10).astype(int)
    q["k"] = q.groupby("dec").cumcount()
    q = q.sort_values(["k", "dec"]).reset_index(drop=True)
    if LIMIT:
        q = q.iloc[:LIMIT]

    os.makedirs(f"{BIO}/batches3", exist_ok=True)
    os.makedirs(f"{BIO}/labels3", exist_ok=True)
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
                          "ended": cause, "description": r.desc})
        json.dump(items, open(f"{BIO}/batches3/batch_{nb:04d}.json", "w"),
                  ensure_ascii=False, indent=1)
        nb += 1

    q[["rid", "pid_a", "pid_b", "dob_a", "dob_b", "mid", "nc", "ncue"]].to_csv(
        f"{BIO}/pool3.csv", index=False)
    print(f"  {int(elig.sum()):,} eligible · {int(gate.sum()):,} pass the gate "
          f"({gate.sum()/max(elig.sum(),1):.0%})")
    print(f"  {len(q):,} queued -> {nb} batches of {PER} in {BIO}/batches3/")
    print(f"  expected labels at 0.599 per judgement: ~{int(len(q)*0.599):,}")
    d = q.dec.value_counts().sort_index()
    print(f"  birth decades {d.index.min()}-{d.index.max()}, "
          f"largest {d.max():,} smallest {d.min():,}")


if __name__ == "__main__":
    main()
