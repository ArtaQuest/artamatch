"""wd_birthtime.py — who in the corpus has a TIMED birth in Wikidata (P569 precision >= 12: hour or
finer)? The one permitted source of birth times (Astro-Databank forbids crawling). A timed birth
unlocks the Moon to the degree, the Ascendant, houses and every hour-based system for that person.
Writes ~/.artamatch-dev/birthtime.csv (pid, time, prec)."""
import csv, json, os, time, urllib.parse, urllib.request, pandas as pd
OUT = os.path.expanduser("~/.artamatch-dev/birthtime.csv")
UA = {"User-Agent": "ArtaMatch research (https://artaquest.com; timed births)", "Accept": "application/sparql-results+json"}
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
    w = csv.writer(f); w.writerow(["pid", "time", "prec"])
    for lo in range(0, len(pids), 500):
        ch = pids[lo:lo+500]
        for r in sparql("SELECT ?p ?t ?prec WHERE { VALUES ?p { " + " ".join(f"wd:{x}" for x in ch) + " } ?p p:P569/psv:P569 ?v . ?v wikibase:timeValue ?t ; wikibase:timePrecision ?prec . FILTER(?prec >= 12) }"):
            w.writerow([r["p"]["value"].rsplit("/", 1)[1], r["t"]["value"], r["prec"]["value"]]); n += 1
        if (lo // 500) % 40 == 0: log(f"   {min(lo+500,len(pids)):,}/{len(pids):,} · {n:,} timed"); f.flush()
        time.sleep(0.8)
log(f"wrote {OUT}: {n:,} people with a timed birth")
