"""
scrape_ended.py — every union that ENDED, in one pass, with the date precisions.

The old slice cache was built for the duration question and is sliced by START year, so a union with no start
was never fetched. This target does not need one: the operator's inputs are the two BIRTH DATES and nothing
else. So the requirement is simply "the union ended", and QLever answers that unsliced in seconds where the
Wikidata endpoint 504s on a single decade.

Fetches, per relationship type, both partners' birth dates AND their declared precision (a year-precision date
arrives looking exactly like 1 January, so the precision is the only way to tell), both death dates, the end
date, and the P1534 end cause where it exists.
"""
import os
import time
import urllib.parse
import urllib.request

OUT = os.environ.get("AQ_ENDED", os.path.expanduser("~/.artamatch-dev/ended"))
EP = "https://qlever.dev/api/wikidata"
UA = "ArtaMatch/1.0 (https://artaquest.com; arash@artaquest.org)"
RELS = {"P26": "marriage", "P451": "unmarried partnership", "P1327": "professional partner",
        "P3342": "significant person"}
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)

PREFIX = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX wikibase: <http://wikiba.se/ontology#>
"""

Q = PREFIX + """SELECT ?a ?b ?adob ?aprec ?bdob ?bprec ?end ?cause ?adeath ?bdeath WHERE {{
  ?a p:{rel} ?st . ?st ps:{rel} ?b . ?st pq:P582 ?end .
  ?a p:P569/psv:P569 ?an . ?an wikibase:timeValue ?adob ; wikibase:timePrecision ?aprec .
  ?b p:P569/psv:P569 ?bn . ?bn wikibase:timeValue ?bdob ; wikibase:timePrecision ?bprec .
  OPTIONAL {{ ?st pq:P1534 ?cause }}
  OPTIONAL {{ ?a wdt:P570 ?adeath }}
  OPTIONAL {{ ?b wdt:P570 ?bdeath }}
}}"""


def fetch(query, timeout=900):
    url = EP + "?" + urllib.parse.urlencode({"query": query})
    req = urllib.request.Request(url, headers={"Accept": "text/csv", "User-Agent": UA})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
            if body.lstrip().startswith(("<", "{")):
                raise RuntimeError(body[:200])
            return body
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            log(f"    retry {attempt+1}: {last[:120]}")
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(last)


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for rel, name in RELS.items():
        path = os.path.join(OUT, f"{rel}.csv")
        if os.path.exists(path) and os.path.getsize(path) > 200:
            n = sum(1 for _ in open(path)) - 1
            log(f"  {rel:<6} {name:<24} {n:>8,} rows (cached)")
            total += n
            continue
        body = fetch(Q.format(rel=rel))
        tmp = path + ".tmp"
        open(tmp, "w").write(body)
        os.replace(tmp, path)          # atomic, so a half-written file is never mistaken for a complete one
        n = max(0, body.count("\n") - 1)
        total += n
        log(f"  {rel:<6} {name:<24} {n:>8,} rows")
    log(f"{total:,} ended-union statements in {OUT}")


if __name__ == "__main__":
    main()
