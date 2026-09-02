"""wt_recover.py — recover exact birth dates for precision-excluded couples via WikiTree.

_prec_excluded.csv lists couples that passed every corpus gate except date precision. For each
person still missing a day: Wikidata P2949 names their WikiTree profile (keyless, WDQS); WikiTree's
getPeople answers 1000 profiles per call (keyless) with a BirthDate and a dataStatus. A date is
accepted ONLY when WikiTree marks it certain (dataStatus '' or 'certain'), it carries a real day,
and its YEAR equals Wikidata's own year — a different year is a contradiction between two records,
not a recovery. The builder enforces the year match a second time on load.

Writes ~/.artamatch-dev/wt_dates.csv (pid,dob).
"""
import csv, json, os, time, urllib.parse, urllib.request

D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
OUT = os.path.expanduser("~/.artamatch-dev/wt_dates.csv")
UA = {"User-Agent": "ArtaMatch-research/1.0 (https://artaquest.com; date-precision recovery)"}
T0 = time.time()
log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)

need = {}   # pid -> wikidata year
with open(f"{D_}/_prec_excluded.csv") as f:
    for r in csv.DictReader(f):
        if r["need_a"] == "1": need[r["pid_a"]] = r["dob_a"][:4]
        if r["need_b"] == "1": need[r["pid_b"]] = r["dob_b"][:4]
pids = sorted(need)
log(f"{len(pids):,} people need an exact date")

# ── P2949 from WDQS, 400 QIDs per query
wt_of = {}
CH = 400
for lo in range(0, len(pids), CH):
    chunk = pids[lo:lo + CH]
    q = "SELECT ?p ?wt WHERE { VALUES ?p { " + " ".join(f"wd:{x}" for x in chunk) + " } ?p wdt:P2949 ?wt }"
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                j = json.load(r)
            for b in j["results"]["bindings"]:
                wt_of[b["p"]["value"].rsplit("/", 1)[1]] = b["wt"]["value"]
            break
        except Exception as e:
            log(f"  WDQS chunk {lo//CH}: {type(e).__name__} {str(e)[:60]} (attempt {attempt+1})")
            time.sleep(10 * (attempt + 1))
    if (lo // CH) % 20 == 0:
        log(f"  WDQS {lo+len(chunk):,}/{len(pids):,} · {len(wt_of):,} have a WikiTree id")
    time.sleep(1.0)
log(f"P2949 coverage: {len(wt_of):,}/{len(pids):,}")

# ── getPeople from WikiTree, 1000 keys per call
qid_of = {}
for q_, w in wt_of.items():
    qid_of.setdefault(w, q_)
keys = sorted(qid_of)
rec, n_uncertain, n_partial, n_yearmiss = [], 0, 0, 0
CH2 = 1000
for lo in range(0, len(keys), CH2):
    chunk = keys[lo:lo + CH2]
    data = urllib.parse.urlencode({"action": "getPeople", "keys": ",".join(chunk),
                                   "fields": "Name,BirthDate,DataStatus"}).encode()
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    "https://api.wikitree.com/api.php", data=data, headers=UA), timeout=120) as r:
                j = json.load(r)
            people = (j[0].get("people") or {}) if isinstance(j, list) else {}
            got = {}
            for _, p in people.items():
                nm, bd = p.get("Name"), p.get("BirthDate") or ""
                st = ((p.get("DataStatus") or {}).get("BirthDate") or "").lower()
                if not nm: continue
                got[nm] = (bd, st)
            for w in chunk:
                if w not in got: continue
                bd, st = got[w]
                if st not in ("", "certain"): n_uncertain += 1; continue
                if len(bd) != 10 or "-00" in bd or bd == "0000-00-00": n_partial += 1; continue
                q_ = qid_of[w]
                if bd[:4] != need[q_]: n_yearmiss += 1; continue
                rec.append((q_, bd))
            break
        except Exception as e:
            log(f"  WT chunk {lo//CH2}: {type(e).__name__} {str(e)[:60]} (attempt {attempt+1})")
            time.sleep(15 * (attempt + 1))
    log(f"  WT {min(lo+CH2,len(keys)):,}/{len(keys):,} · recovered {len(rec):,} "
        f"(uncertain {n_uncertain:,} · partial {n_partial:,} · year-mismatch {n_yearmiss:,})")
    time.sleep(2.0)

with open(OUT, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["pid", "dob"]); w.writerows(rec)
log(f"wrote {OUT}: {len(rec):,} exact dates "
    f"({len(rec)/max(1,len(pids)):.1%} of the people who needed one)")
