"""
scrape_marriages.py — EVERY marriage of everyone born before 1950, so remarriage can be read structurally.

Operator 2026-08-24: "all the couple before 1950 included · check whether remarries or not · do not rely on
the wiki label · list all the marriages of each couple · its considered divorce if either remarried after."

That inverts the bottleneck. The old label needed an end date or an explicit end cause, which only ~5% of
statements carry; this one needs only the marriage START dates, so the corpus grows by more than an order of
magnitude. It also stops depending on whether a Wikidata editor happened to record how a marriage ended.

Sliced by the BIRTH DECADE of the subject, because one decade answers in ~90s where the whole range times
out — and because a slice returns EVERY P26 statement of everyone born in it, sweeping all decades yields each
person's complete marriage list, which is exactly what the rule needs.

Also collected, for validation rather than for labelling: each person's death date and the explicit P1534 end
cause where one exists. The structural rule will be scored against those causes before it is trusted.
"""
import os, time, urllib.parse, urllib.request

OUT = os.path.expanduser(os.environ.get("AQ_MAR", "~/.artamatch-dev/marriages"))
LO, HI, STEP = int(os.environ.get("AQ_LO", "1500")), int(os.environ.get("AQ_HI", "1950")), 10
UA = "ArtaMatch research (https://artaquest.com; arash@artaquest.org)"
EP = "https://query.wikidata.org/sparql"
import socket
socket.setdefaulttimeout(180)   # a dead keep-alive socket must not hang a pass
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)

Q = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT ?a ?b ?start ?adob ?aprec ?adeath ?asex ?cause WHERE {{
  ?a p:P569/psv:P569 ?an . ?an wikibase:timeValue ?adob ; wikibase:timePrecision ?aprec .
  FILTER(YEAR(?adob) >= {lo} && YEAR(?adob) < {hi})
  ?a p:P26 ?st . ?st ps:P26 ?b .
  OPTIONAL {{ ?st pq:P580 ?start }}
  OPTIONAL {{ ?a wdt:P570 ?adeath }}
  OPTIONAL {{ ?a wdt:P21 ?asex }}
  OPTIONAL {{ ?st pq:P1534 ?cause }}
}}"""


def fetch(lo, hi, tries=4):
    u = EP + "?" + urllib.parse.urlencode({"query": Q.format(lo=lo, hi=hi)})
    req = urllib.request.Request(u, headers={"Accept": "text/csv", "User-Agent": UA})
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=600) as f:
                body = f.read().decode("utf-8", "replace")
            if body.lstrip().startswith("<"):
                raise RuntimeError("HTML, not CSV")
            return body
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if k < tries - 1:
                time.sleep(20 * (k + 1))
    raise RuntimeError(last)


QCOUNT = Q.replace("SELECT ?a ?b ?start ?adob ?aprec ?adeath ?asex ?cause", "SELECT (COUNT(*) AS ?n)")


def server_count(lo, hi, tries=3):
    import json as _json
    u = EP + "?" + urllib.parse.urlencode({"query": QCOUNT.format(lo=lo, hi=hi), "format": "json"})
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=180) as f:
                return int(_json.load(f)["results"]["bindings"][0]["n"]["value"])
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(15)


def fetch_verified(lo, hi, depth=0):
    """WDQS can TIME OUT MID-STREAM and hand back a partial CSV with HTTP 200 (verified live: the 1970s
    slice delivered 604 of 7,048 rows, and the original harvest lost tens of thousands of statements this
    way). Every slice is therefore checked against a server-side COUNT of the same pattern; a short slice
    is retried, then split in half, down to single years. Small live-edit drift (count moves between the
    two queries) is tolerated at 0.5%."""
    want = server_count(lo, hi)
    for attempt in range(3):
        body = fetch(lo, hi)
        got = max(0, body.count("\n") - 1)
        if want == 0 and got == 0:
            return body, 0
        if got >= want or (want and abs(got - want) / want <= 0.005):
            return body, got
        log(f"    slice {lo}-{hi}: TRUNCATED ({got:,} of {want:,}) — retry {attempt + 1}")
        time.sleep(20)
    if hi - lo <= 1:
        raise RuntimeError(f"year {lo} refuses to arrive whole ({got:,} of {want:,})")
    mid = (lo + hi) // 2
    log(f"    slice {lo}-{hi}: splitting at {mid}")
    b1, n1 = fetch_verified(lo, mid, depth + 1)
    time.sleep(2)
    b2, n2 = fetch_verified(mid, hi, depth + 1)
    head, rest = b2.split("\n", 1)
    return b1.rstrip("\n") + "\n" + rest, n1 + n2


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for lo in range(LO, HI, STEP):
        path = os.path.join(OUT, f"d{lo}.csv")
        if os.path.exists(path) and os.path.getsize(path) > 40:
            total += sum(1 for _ in open(path)) - 1
            continue
        try:
            body, n = fetch_verified(lo, lo + STEP)
        except Exception as e:
            # a failure must NOT leave a file: an empty CSV is indistinguishable from a genuinely empty decade,
            # and the skip-if-exists check above would then never retry it
            log(f"  {lo}s FAILED ({str(e)[:70]}) — left absent for retry")
            continue
        tmp = path + ".tmp"
        open(tmp, "w").write(body)
        os.replace(tmp, path)
        total += n
        log(f"  {lo}s: {n:,} marriage statements, count-verified  (running total {total:,})")
        time.sleep(2)
    log(f"{total:,} statements across {len(os.listdir(OUT))} decade files — every slice count-verified")


if __name__ == "__main__":
    main()
