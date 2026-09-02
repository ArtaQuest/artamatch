"""wd_fill.py — the facts our own harvest never fetched, straight from Wikidata.

The decade harvests stored birth date, sex and death for the SUBJECT spouse of each P26 statement
only; a partner seen nowhere else has none of them, and 147,118 people fell out of the corpus for a
missing date before any other gate was reached — 149,260 couples, the largest exclusion of all,
and not a gap in Wikidata's record but in ours. This fetches P569 (with precision), P21 and P570
for every such person, 400 per POST query, keyless, and the builder fills only what is absent.

Also (H2): children rows for finished pairs that had none — the same P22/P25 count the corpus
already uses, in BOTH orientations, appended to bio/children.csv under the same unordered key.

Writes ~/.artamatch-dev/wd_facts.csv (pid,dob,prec,sex,death) and appends to bio/children.csv.
"""
import csv, json, os, time, urllib.parse, urllib.request
D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_wt")
BIO = os.path.expanduser("~/.artamatch-dev/bio")
OUT = os.path.expanduser("~/.artamatch-dev/wd_facts.csv")
UA = {"User-Agent": "ArtaMatch research (https://artaquest.com; corpus completion)",
      "Accept": "application/sparql-results+json"}
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

def sparql(q, tries=5):
    data = urllib.parse.urlencode({"query": q}).encode()
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    "https://query.wikidata.org/sparql", data=data, headers=UA), timeout=180) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:
            log(f"   {type(e).__name__} {str(e)[:60]} (attempt {t+1})"); time.sleep(12 * (t + 1))
    return []
qid = lambda v: v.rsplit("/", 1)[1]

# ── H2 first (small): children for the finished no-row pairs, either orientation
pairs = [(r["pid_a"], r["pid_b"]) for r in csv.DictReader(open(f"{D_}/_nokids_pairs.csv")) if r["finished"] == "1"]
have = set(r["pair"] for r in csv.DictReader(open(f"{BIO}/children.csv")))
pairs = [(a, b) for a, b in pairs if f"{min(a,b)}|{max(a,b)}" not in have]
log(f"H2: {len(pairs):,} finished pairs without a children row")
added = 0
with open(f"{BIO}/children.csv", "a", newline="") as f:
    w = csv.writer(f)
    for lo in range(0, len(pairs), 150):
        ch = pairs[lo:lo + 150]
        vals = " ".join(f"(wd:{a} wd:{b})" for a, b in ch)
        rows = sparql(f"""SELECT ?a ?b (COUNT(DISTINCT ?c) AS ?n) WHERE {{ VALUES (?a ?b) {{ {vals} }}
          OPTIONAL {{ {{ ?c wdt:P22 ?a ; wdt:P25 ?b . }} UNION {{ ?c wdt:P22 ?b ; wdt:P25 ?a . }} }} }} GROUP BY ?a ?b""")
        got = {(qid(r["a"]["value"]), qid(r["b"]["value"])): int(r["n"]["value"]) for r in rows}
        for a, b in ch:
            if (a, b) in got:
                w.writerow([f"{min(a,b)}|{max(a,b)}", got[(a, b)], 0]); added += 1
        time.sleep(1.0)
log(f"H2: appended {added:,} children rows ({sum(1 for _ in [])})")

# ── H1: the missing facts
pids = [r["pid"] for r in csv.DictReader(open(f"{D_}/_dob_missing.csv"))]
log(f"H1: {len(pids):,} people missing a birth date in our tables")
n_dob = n_full = 0
with open(OUT, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["pid", "dob", "prec", "sex", "death"])
    for lo in range(0, len(pids), 400):
        ch = pids[lo:lo + 400]
        vals = " ".join(f"wd:{x}" for x in ch)
        rows = sparql(f"""SELECT ?p ?dob ?prec ?sex ?death WHERE {{ VALUES ?p {{ {vals} }}
          OPTIONAL {{ ?p p:P569/psv:P569 ?v . ?v wikibase:timeValue ?dob ; wikibase:timePrecision ?prec . }}
          OPTIONAL {{ ?p wdt:P21 ?sex . }}  OPTIONAL {{ ?p wdt:P570 ?death . }} }}""")
        seen = {}
        for r in rows:
            p = qid(r["p"]["value"])
            dob = r.get("dob", {}).get("value", "")[:10] if "dob" in r else ""
            prec = r.get("prec", {}).get("value", "") if "prec" in r else ""
            # keep the most precise statement per person
            if p in seen and seen[p][1] and (not prec or int(prec) <= int(seen[p][1])): continue
            seen[p] = (dob, prec, qid(r["sex"]["value"]) if "sex" in r else "",
                       r["death"]["value"][:4] if "death" in r else "")
        for p, (dob, prec, sex, death) in seen.items():
            w.writerow([p, dob, prec, sex, death])
            if dob: n_dob += 1
            if prec == "11": n_full += 1
        if (lo // 400) % 25 == 0:
            log(f"   {min(lo+400,len(pids)):,}/{len(pids):,} · with a date {n_dob:,} · to the day {n_full:,}")
        time.sleep(1.0)
log(f"H1 done: {n_dob:,} people have a Wikidata birth date after all · {n_full:,} to the day · wrote {OUT}")
