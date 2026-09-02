"""wd_labels.py — every corpus person's name (the Wikidata English label), for name numerology.

Operator 2026-09-02: "also include numerology of names". The label is the name the world knows
the person by; it is romanised downstream (unidecode) so every person gets a value in every
script. Writes ~/.artamatch-dev/labels.csv (pid,label).
"""
import csv, json, os, time, urllib.parse, urllib.request, pandas as pd
OUT = os.path.expanduser("~/.artamatch-dev/labels.csv")
UA = {"User-Agent": "ArtaMatch research (https://artaquest.com; name numerology)", "Accept": "application/sparql-results+json"}
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
pids = set()
for D in ("tilldeath_wt3", "tilldeath_wt"):
    d = pd.read_csv(os.path.expanduser(f"~/.artamatch-dev/{D}/full.csv"), dtype=str)
    pids |= set(d.pid_a) | set(d.pid_b)
have = {}
if os.path.exists(OUT):
    have = {r["pid"]: r["label"] for r in csv.DictReader(open(OUT))}
todo = sorted(pids - set(have)); log(f"{len(pids):,} people · {len(have):,} known · {len(todo):,} to fetch")
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
with open(OUT, "a", newline="") as f:
    w = csv.writer(f)
    if not have: w.writerow(["pid", "label"])
    for lo in range(0, len(todo), 400):
        ch = todo[lo:lo+400]
        rows = sparql("SELECT ?p ?l WHERE { VALUES ?p { " + " ".join(f"wd:{x}" for x in ch) + " } ?p rdfs:label ?l . FILTER(LANG(?l) = \"en\") }")
        seen = set()
        for r in rows:
            p = r["p"]["value"].rsplit("/", 1)[1]
            if p in seen: continue
            seen.add(p); w.writerow([p, r["l"]["value"]]); n += 1
        if (lo // 400) % 50 == 0: log(f"   {min(lo+400,len(todo)):,}/{len(todo):,} · {n:,} labels"); f.flush()
        time.sleep(0.8)
log(f"wrote {OUT}: +{n:,} labels")
