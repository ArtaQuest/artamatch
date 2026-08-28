"""bio_titles.py — enwiki article title (and label) for every person in an ended marriage, via SPARQL
VALUES batches. Checkpointed: rerun resumes. -> ~/.artamatch-dev/bio/titles.csv (qid,title,label)"""
import csv, os, socket, sys, time, urllib.parse, urllib.request
import pandas as pd
socket.setdefaulttimeout(180)
OUT = os.path.expanduser("~/.artamatch-dev/bio")
UA = "ArtaMatch research (https://artaquest.com; arash@artaquest.org)"
EP = "https://query.wikidata.org/sparql"
Q = """SELECT ?a ?article ?label WHERE {{
  VALUES ?a {{ {vals} }}
  OPTIONAL {{ ?article schema:about ?a ; schema:isPartOf <https://en.wikipedia.org/> . }}
  OPTIONAL {{ ?a rdfs:label ?label . FILTER(LANG(?label) = "en") }}
}}"""
cp = pd.read_csv(f"{OUT}/couples.csv", dtype=str)
qids = sorted(set(cp.pid_a) | set(cp.pid_b))
path = f"{OUT}/titles.csv"
done = set()
if os.path.exists(path):
    done = set(pd.read_csv(path, dtype=str).qid)
todo = [q for q in qids if q not in done]
print(f"  {len(qids):,} persons · {len(done):,} checkpointed · {len(todo):,} to fetch", flush=True)
B = 600
w = open(path, "a", newline="")
wr = csv.writer(w)
if not done:
    wr.writerow(["qid", "title", "label"])
for i in range(0, len(todo), B):
    batch = todo[i:i + B]
    q = Q.format(vals=" ".join(f"wd:{x}" for x in batch))
    body = urllib.parse.urlencode({"query": q, "format": "json"}).encode()
    req = urllib.request.Request(EP, data=body, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"})
    row = None
    for k in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as f:
                row = __import__("json").load(f)["results"]["bindings"]
            break
        except Exception as e:
            if k == 4:
                print(f"    batch {i} FAILED {str(e)[:60]} — skipped, rerun resumes", flush=True)
            else:
                time.sleep(15)
    if row is None:
        continue
    got = {}
    for r in row:
        qq = r["a"]["value"].rsplit("/", 1)[-1]
        t = r.get("article", {}).get("value", "")
        if t:
            t = urllib.parse.unquote(t.rsplit("/", 1)[-1]).replace("_", " ")
        got.setdefault(qq, [t, r.get("label", {}).get("value", "")])
        if t and not got[qq][0]:
            got[qq][0] = t
    for qq in batch:
        t, l = got.get(qq, ["", ""])
        wr.writerow([qq, t, l])
    w.flush()
    if (i // B) % 20 == 0:
        print(f"    {i + len(batch):,}/{len(todo):,}", flush=True)
    time.sleep(1.0)
w.close()
tt = pd.read_csv(path, dtype=str)
print(f"  COMPLETE: {len(tt):,} rows · with an enwiki article: {int(tt.title.notna().sum()):,}")
