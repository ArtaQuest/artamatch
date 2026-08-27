"""Every decade file vs a server-side COUNT of the same pattern — a silently truncated download
(HTTP 200, partial CSV) is invisible any other way. Mismatched decades are re-fetched by scrape_marriages."""
import os, time, urllib.parse, urllib.request, json
UA = "ArtaMatch research (https://artaquest.com; arash@artaquest.org)"
EP = "https://query.wikidata.org/sparql"
Q = """SELECT (COUNT(*) AS ?n) WHERE {{
  ?a p:P569/psv:P569 ?an . ?an <http://wikiba.se/ontology#timeValue> ?adob ;
     <http://wikiba.se/ontology#timePrecision> ?aprec .
  FILTER(YEAR(?adob) >= {lo} && YEAR(?adob) < {hi})
  ?a p:P26 ?st . ?st ps:P26 ?b .
}}"""
MAR = os.path.expanduser("~/.artamatch-dev/marriages")
bad = []
for lo in range(1500, 2010, 10):
    path = os.path.join(MAR, f"d{lo}.csv")
    have = sum(1 for _ in open(path)) - 1 if os.path.exists(path) else -1
    u = EP + "?" + urllib.parse.urlencode({"query": Q.format(lo=lo, hi=lo + 10), "format": "json"})
    n = None
    for t in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=120) as f:
                n = int(json.load(f)["results"]["bindings"][0]["n"]["value"])
            break
        except Exception:
            time.sleep(15)
    # the data query returns one row per (P26 stmt x P569 stmt) cross product; COUNT here is per P26 x P569 too
    flag = "" if n is not None and have == n else "  <-- MISMATCH"
    if flag:
        bad.append(lo)
    print(f"  d{lo}: file {have:>7,} · server {('?' if n is None else format(n, ',')):>7}{flag}", flush=True)
    time.sleep(1.5)
print("MISMATCHED:", bad if bad else "none — harvest complete")
open(os.path.expanduser("~/.artamatch-dev/_harvest_bad.json"), "w").write(json.dumps(bad))
