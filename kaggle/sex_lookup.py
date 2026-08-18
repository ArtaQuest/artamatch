"""
sex_lookup.py — P21 (sex or gender) for every person in the cached slices, WITHOUT refetching the slices.

The third edition orders the columns dad-first / mom-second, which needs each partner's sex. Adding
`OPTIONAL { ?a wdt:P21 ?asex }` to the query bodies would change every hash and refetch 440 slices (hours). The
Q-ids are already in the cache, so this asks Wikidata one thing -- P21 for a VALUES batch of ids -- by POST,
three thousand ids at a time, and appends to a resumable CSV that the scraper reads. Q6581097 male, Q6581072
female; anything else (trans, non-binary, unknown, intersex, ...) is kept as its own Q-id and treated as
"neither of the two the ordering needs" downstream, which is a statement about the ORDERING RULE, not the person.

Usage: python sex_lookup.py            # reads /tmp/aqdur/_dslices, writes /tmp/aqdur/_sex.csv, resumes
"""
import csv
import glob
import os
import sys
import time
import urllib.parse
import urllib.request

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CACHE = os.environ.get("AQ_SLICE_CACHE", "/tmp/aqdur/_dslices")
OUT = os.environ.get("AQ_SEX_CSV", "/tmp/aqdur/_sex.csv")
UA = "ArtaMatch/4.0 (https://www.artaquest.com) sex lookup for column ordering"
BATCH = int(os.environ.get("AQ_SEX_BATCH") or 3000)
EP = ["https://query.wikidata.org/sparql", "https://qlever.dev/api/wikidata"]


def qids_in_cache():
    """Every Q-id in the a/b columns of every cached slice file (all editions' hashes; the union is fine)."""
    ids = set()
    for f in glob.glob(os.path.join(CACHE, "*.csv")):
        try:
            df = pd.read_csv(f, sep=None, engine="python", usecols=lambda c: c in ("a", "b", "?a", "?b"),
                             dtype=str, on_bad_lines="skip")
        except Exception:
            continue
        for c in df.columns:
            ids.update(v.strip("<>").rsplit("/", 1)[-1] for v in df[c].dropna().astype(str) if "Q" in v)
    return sorted(i for i in ids if i.startswith("Q") and i[1:].isdigit())


def fetch(batch):
    q = ("SELECT ?p ?sex WHERE { VALUES ?p { " + " ".join(f"wd:{i}" for i in batch) + " } ?p wdt:P21 ?sex }")
    q = "PREFIX wd: <http://www.wikidata.org/entity/> PREFIX wdt: <http://www.wikidata.org/prop/direct/> " + q
    for base in EP:
        for attempt in range(4):
            try:
                data = urllib.parse.urlencode({"query": q}).encode()
                req = urllib.request.Request(base, data=data, headers={"Accept": "text/csv", "User-Agent": UA,
                                             "Content-Type": "application/x-www-form-urlencoded"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    txt = r.read().decode()
                rows = list(csv.reader(txt.splitlines()))
                if not rows or rows[0][:2] != ["p", "sex"]:
                    raise ValueError(f"unexpected header {rows[:1]}")
                return [(a.strip("<>").rsplit("/", 1)[-1], b.strip("<>").rsplit("/", 1)[-1]) for a, b in rows[1:] if a and b]
            except Exception as e:
                time.sleep(3 * (attempt + 1))
    return None


def main():
    ids = qids_in_cache()
    have = set()
    if os.path.exists(OUT):
        have = {r[0] for r in csv.reader(open(OUT)) if r}
    todo = [i for i in ids if i not in have]
    print(f"  {len(ids):,} people in the cache · {len(have):,} already looked up · {len(todo):,} to fetch "
          f"in batches of {BATCH}", flush=True)
    t0 = time.time()
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        for s in range(0, len(todo), BATCH):
            batch = todo[s:s + BATCH]
            res = fetch(batch)
            if res is None:
                print(f"    batch {s//BATCH}: FAILED on both endpoints; skipped (rerun to resume)", flush=True)
                continue
            got = {}
            for p, sex in res:
                got.setdefault(p, sex)                 # first statement wins; multi-valued P21 is rare
            for i in batch:
                w.writerow([i, got.get(i, "")])        # empty = no P21 on file
            f.flush()
            if (s // BATCH) % 10 == 0:
                print(f"    {s + len(batch):,}/{len(todo):,}  ({time.time()-t0:.0f}s)", flush=True)
    df = pd.read_csv(OUT, header=None, names=["qid", "sex"], dtype=str).fillna("")
    vc = df.sex.value_counts()
    print(f"  done: {len(df):,} people · male {vc.get('Q6581097',0):,} · female {vc.get('Q6581072',0):,} · "
          f"other/none {len(df) - vc.get('Q6581097',0) - vc.get('Q6581072',0):,}")


if __name__ == "__main__":
    main()
