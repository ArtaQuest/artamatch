"""wd_children_sex.py — the SEX (P21) and birth date (P569) of every linked child of every corpus
couple with children (operator 2026-09-03: "identify and classify whether they had boys/girls/both").

For each couple (him = P22 father, her = P25 mother, either orientation) the children with a
recorded sex are counted: boys, girls, unknown; the firstborn's sex is the sex of the earliest-born
child with a date (unknown when no child has a date). Writes ~/.artamatch-dev/bio/children_sex.csv
(pair, n_sexed, boys, girls, unknown, firstborn) keyed like children.csv (min|max of the QIDs).
"""
import csv, json, os, time, urllib.parse, urllib.request
import pandas as pd
D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_wt3")
OUT = os.path.expanduser("~/.artamatch-dev/bio/children_sex.csv")
UA = {"User-Agent": "ArtaMatch research (https://artaquest.com; children's sex)", "Accept": "application/sparql-results+json"}
MALE, FEM = "Q6581097", "Q6581072"
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
full = pd.read_csv(f"{D_}/full.csv", dtype=str)
pairs = [(a, b) for a, b, n in zip(full.pid_a, full.pid_b, pd.to_numeric(full.n_children, errors="coerce").fillna(0)) if n >= 1]
log(f"{len(pairs):,} couples with children")
def sparql(q, tries=5):
    data = urllib.parse.urlencode({"query": q}).encode()
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://query.wikidata.org/sparql", data=data, headers=UA), timeout=180) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:
            log(f"   {type(e).__name__} {str(e)[:50]} (attempt {t+1})"); time.sleep(12 * (t + 1))
    return []
qid = lambda v: v.rsplit("/", 1)[1]
rows = {}
for lo in range(0, len(pairs), 120):
    ch = pairs[lo:lo + 120]
    vals = " ".join(f"(wd:{a} wd:{b})" for a, b in ch)
    res = sparql(f"""SELECT ?a ?b ?c ?sex ?dob WHERE {{ VALUES (?a ?b) {{ {vals} }}
      {{ ?c wdt:P22 ?a ; wdt:P25 ?b . }} UNION {{ ?c wdt:P22 ?b ; wdt:P25 ?a . }}
      OPTIONAL {{ ?c wdt:P21 ?sex . }} OPTIONAL {{ ?c wdt:P569 ?dob . }} }}""")
    kids = {}
    for r in res:
        key = f"{min(qid(r['a']['value']), qid(r['b']['value']))}|{max(qid(r['a']['value']), qid(r['b']['value']))}"
        c = qid(r["c"]["value"]); sx = qid(r["sex"]["value"]) if "sex" in r else ""
        dob = r["dob"]["value"][:10] if "dob" in r else ""
        d = kids.setdefault(key, {})
        e = d.setdefault(c, {"sex": "", "dob": ""})
        if sx in (MALE, FEM): e["sex"] = "M" if sx == MALE else "F"
        if dob and (not e["dob"] or dob < e["dob"]): e["dob"] = dob
    for key, d in kids.items():
        boys = sum(1 for e in d.values() if e["sex"] == "M"); girls = sum(1 for e in d.values() if e["sex"] == "F")
        unk = sum(1 for e in d.values() if not e["sex"])
        dated = sorted((e["dob"], e["sex"]) for e in d.values() if e["dob"] and e["sex"])
        first = dated[0][1] if dated else ""
        rows[key] = (len(d), boys, girls, unk, first)
    if (lo // 120) % 40 == 0: log(f"   {min(lo+120,len(pairs)):,}/{len(pairs):,} · {len(rows):,} couples with sexed children")
    time.sleep(0.8)
with open(OUT, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["pair", "n_linked", "boys", "girls", "unknown", "firstborn"])
    for k, v in rows.items(): w.writerow([k, *v])
b = sum(1 for v in rows.values() if v[1] and not v[2]); g = sum(1 for v in rows.values() if v[2] and not v[1]); both = sum(1 for v in rows.values() if v[1] and v[2])
log(f"wrote {OUT}: {len(rows):,} couples · boys only {b:,} · girls only {g:,} · both {both:,} · firstborn known {sum(1 for v in rows.values() if v[4]):,}")
