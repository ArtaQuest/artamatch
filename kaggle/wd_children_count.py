"""wd_children_count.py — P1971 (number of children) for every corpus person: the explicit count.

The label so far is "children LINKED in Wikidata" (P22/P25); an explicit P1971 = 0 is real
childlessness rather than a thin record, and P1971 >= 1 with no linked child is a child the record
knows of but has no item for. This lets the label be purified: negatives that are explicit zeros
or deep records; positives by either evidence. Writes ~/.artamatch-dev/p1971.csv (pid,n).
"""
import csv, json, os, time, urllib.parse, urllib.request, pandas as pd
OUT = os.path.expanduser("~/.artamatch-dev/p1971.csv")
UA = {"User-Agent": "ArtaMatch research (https://artaquest.com; label purification)", "Accept": "application/sparql-results+json"}
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
d = pd.read_csv(os.path.expanduser("~/.artamatch-dev/tilldeath_wt3/full.csv"), dtype=str)
pids = sorted(set(d.pid_a) | set(d.pid_b)); log(f"{len(pids):,} people")
def sparql(q, tries=5):
    data = urllib.parse.urlencode({"query": q}).encode()
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://query.wikidata.org/sparql", data=data, headers=UA), timeout=180) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:
            log(f"   {type(e).__name__} {str(e)[:50]} (attempt {t+1})"); time.sleep(12 * (t + 1))
    return []
n = 0
with open(OUT, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["pid", "n"])
    for lo in range(0, len(pids), 500):
        ch = pids[lo:lo+500]
        for r in sparql("SELECT ?p ?n WHERE { VALUES ?p { " + " ".join(f"wd:{x}" for x in ch) + " } ?p wdt:P1971 ?n }"):
            w.writerow([r["p"]["value"].rsplit("/", 1)[1], r["n"]["value"]]); n += 1
        if (lo // 500) % 40 == 0: log(f"   {min(lo+500,len(pids)):,}/{len(pids):,} · {n:,} with P1971"); f.flush()
        time.sleep(0.8)
log(f"wrote {OUT}: {n:,} people state their number of children")
