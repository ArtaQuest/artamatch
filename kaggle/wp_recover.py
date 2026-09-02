"""wp_recover.py — exact birth dates from English Wikipedia infoboxes, for year-only people.

For the couples still one exact date short after WikiTree: the enwiki article (via the Wikidata
sitelink) often carries {{birth date|Y|M|D}} / {{birth date and age|...}} where Wikidata holds
only the year. Titles come from WDQS (400 per query); wikitext from the MediaWiki API (50 titles
per call). A date is accepted only from an explicit day-precision template whose year equals
Wikidata's — freeform prose dates are NOT parsed (too many are approximate or baptismal).

Writes ~/.artamatch-dev/wp_dates.csv (pid,dob); the builder applies it exactly like WikiTree's.
"""
import csv, json, os, re, time, urllib.parse, urllib.request
D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_wt")
OUT = os.path.expanduser("~/.artamatch-dev/wp_dates.csv")
UA = {"User-Agent": "ArtaMatch research (https://artaquest.com; date-precision recovery)"}
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

need = {}
for r in csv.DictReader(open(f"{D_}/_prec_excluded.csv")):
    if r["need_a"] == "1": need[r["pid_a"]] = r["dob_a"][:4]
    if r["need_b"] == "1": need[r["pid_b"]] = r["dob_b"][:4]
pids = sorted(need)
log(f"{len(pids):,} people need an exact date")

def sparql(q, tries=5):
    data = urllib.parse.urlencode({"query": q}).encode()
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://query.wikidata.org/sparql", data=data,
                    headers={**UA, "Accept": "application/sparql-results+json"}), timeout=180) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:
            log(f"   WDQS {type(e).__name__} {str(e)[:50]} (attempt {t+1})"); time.sleep(12 * (t + 1))
    return []

title_of = {}
for lo in range(0, len(pids), 400):
    ch = pids[lo:lo + 400]
    rows = sparql("SELECT ?p ?t WHERE { VALUES ?p { " + " ".join(f"wd:{x}" for x in ch) + " } "
                  "?a schema:about ?p ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?t . }")
    for r in rows:
        title_of[r["p"]["value"].rsplit("/", 1)[1]] = r["t"]["value"]
    if (lo // 400) % 25 == 0: log(f"   titles {min(lo+400,len(pids)):,}/{len(pids):,} · {len(title_of):,} have enwiki")
    time.sleep(1.0)
log(f"enwiki coverage: {len(title_of):,}/{len(pids):,}")

# {{birth date|1890|5|12}}, {{Birth date and age|1890|05|12|df=y}}, {{bda|...}}, {{birth-date|...}} with numeric fields
TPL = re.compile(r"\{\{\s*(?:birth[ _-]?date(?:[ _-]and[ _-]age)?|bda)\s*\|\s*(?:df=\w+\s*\|\s*|mf=\w+\s*\|\s*)?(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", re.I)
pid_of_title = {t: p for p, t in title_of.items()}
titles = sorted(pid_of_title)
rec, n_notpl, n_yearmiss = [], 0, 0
API = "https://en.wikipedia.org/w/api.php"
for lo in range(0, len(titles), 50):
    ch = titles[lo:lo + 50]
    params = urllib.parse.urlencode({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                                     "format": "json", "formatversion": "2", "titles": "|".join(ch)}).encode()
    for t in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(API, data=params, headers=UA), timeout=120) as r:
                j = json.load(r)
            break
        except Exception as e:
            log(f"   API {type(e).__name__} {str(e)[:50]} (attempt {t+1})"); time.sleep(10 * (t + 1)); j = {}
    for pg in j.get("query", {}).get("pages", []):
        title = pg.get("title"); p = pid_of_title.get(title)
        if not p: continue
        txt = ((pg.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("content", "")) or ""
        m = TPL.search(txt[:20000])   # the infobox is at the top
        if not m: n_notpl += 1; continue
        y, mo, d = m.groups()
        if y != need[p]: n_yearmiss += 1; continue
        try:
            import datetime; datetime.date(int(y), int(mo), int(d))
        except ValueError: continue
        rec.append((p, f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"))
    if (lo // 50) % 100 == 0:
        log(f"   wikitext {min(lo+50,len(titles)):,}/{len(titles):,} · recovered {len(rec):,} (no template {n_notpl:,} · year mismatch {n_yearmiss:,})")
    time.sleep(0.5)
with open(OUT, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["pid", "dob"]); w.writerows(rec)
log(f"wrote {OUT}: {len(rec):,} exact dates ({len(rec)/max(1,len(pids)):.1%} of the people who needed one)")
