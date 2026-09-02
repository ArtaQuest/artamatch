"""wd_sitelinks.py — how thoroughly each person in the corpus is documented (Wikidata sitelink count).

For the documentation-depth purification experiment: "no children recorded" blends genuine
childlessness with thin documentation. Restricting to couples whose BOTH spouses are deeply
documented (many sitelinks) makes absence more informative; the number to watch is whether the
pair lift over one chart grows on that subset. Sitelink count is a covariate for SUBSETTING
only — it never enters the model (angular features only).

Writes ~/.artamatch-dev/sitelinks.csv (pid,sitelinks).
"""
import csv, json, os, time, urllib.parse, urllib.request
import pandas as pd
D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_wt")
OUT = os.path.expanduser("~/.artamatch-dev/sitelinks.csv")
UA = {"User-Agent": "ArtaMatch research (https://artaquest.com; documentation depth)",
      "Accept": "application/sparql-results+json"}
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
d = pd.read_csv(f"{D_}/full.csv", dtype=str)
pids = sorted(set(d.pid_a) | set(d.pid_b))
log(f"{len(pids):,} people in the corpus")
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
    w = csv.writer(f); w.writerow(["pid", "sitelinks"])
    for lo in range(0, len(pids), 500):
        ch = pids[lo:lo + 500]
        rows = sparql("SELECT ?p ?s WHERE { VALUES ?p { " + " ".join(f"wd:{x}" for x in ch) + " } ?p wikibase:sitelinks ?s }")
        for r in rows:
            w.writerow([r["p"]["value"].rsplit("/", 1)[1], r["s"]["value"]]); n += 1
        if (lo // 500) % 40 == 0: log(f"   {min(lo+500,len(pids)):,}/{len(pids):,}")
        time.sleep(0.8)
log(f"wrote {OUT}: {n:,} people")
