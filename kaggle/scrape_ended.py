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

OUT = os.environ.get("AQ_ENDED", os.path.expanduser("~/.artamatch-dev/ended_max"))
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

# THE MAXIMAL VIABLE QUERY, after measuring every relaxation against the label rather than guessing:
#   · an END DATE **or** an explicit END CAUSE. Requiring the date alone silently dropped 1,089 P26 statements
#     whose cause is written down but whose date is not — a divorce is a label with or without a date.
#   · AT LEAST ONE birth date, not both. This adds 14,521 P26 pairs and is only usable because the pipeline was
#     built for missing dates: a partner with no birth date renders as 0000-00-00, every feature over them is
#     NaN, and the missing-date augmentation has already trained the model on exactly that shape. The partner
#     we DO know still carries their whole chart.
#   · the birth date is OPTIONAL on each side so a one-sided pair survives the join at all.
# Relaxations measured and REJECTED: "both partners dead, so it ended in a death" scores 35.7% against the
# explicit causes, and no margin repairs it.
Q = PREFIX + """SELECT ?a ?b ?adob ?aprec ?bdob ?bprec ?end ?cause ?adeath ?bdeath WHERE {{
  ?a p:{rel} ?st . ?st ps:{rel} ?b .
  {{ ?st pq:P582 ?end }} UNION {{ ?st pq:P1534 ?cause }}
  OPTIONAL {{ ?st pq:P582 ?end }}
  OPTIONAL {{ ?st pq:P1534 ?cause }}
  OPTIONAL {{ ?a p:P569/psv:P569 ?an . ?an wikibase:timeValue ?adob ; wikibase:timePrecision ?aprec }}
  OPTIONAL {{ ?b p:P569/psv:P569 ?bn . ?bn wikibase:timeValue ?bdob ; wikibase:timePrecision ?bprec }}
  OPTIONAL {{ ?a wdt:P570 ?adeath }}
  OPTIONAL {{ ?b wdt:P570 ?bdeath }}
  FILTER( BOUND(?adob) || BOUND(?bdob) )
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
