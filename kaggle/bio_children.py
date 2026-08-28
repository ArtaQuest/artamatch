"""bio_children.py — how many children each couple had together (Wikidata P22 father + P25 mother),
plus whether they share a notable joint work (P800 overlap). Checkpointed VALUES-pair SPARQL over POST.
-> ~/.artamatch-dev/bio/children.csv (pair,n,joint_works)"""
import csv, json, os, socket, time, urllib.parse, urllib.request
import pandas as pd
socket.setdefaulttimeout(180)
BIO = os.path.expanduser("~/.artamatch-dev/bio")
UA = "ArtaMatch research (https://artaquest.com; arash@artaquest.org)"
EP = "https://query.wikidata.org/sparql"
Q = """SELECT ?a ?b (COUNT(DISTINCT ?c) AS ?n) (COUNT(DISTINCT ?w) AS ?wk) WHERE {{
  VALUES (?a ?b) {{ {vals} }}
  OPTIONAL {{ ?c wdt:P22 ?a ; wdt:P25 ?b . }}
  OPTIONAL {{ ?a wdt:P800 ?w . ?b wdt:P800 ?w . }}
}} GROUP BY ?a ?b"""
cp = pd.read_csv(f"{BIO}/couples.csv", dtype=str)
pairs = list(dict.fromkeys(zip(cp.pid_a, cp.pid_b)))
path = f"{BIO}/children.csv"
done = set()
if os.path.exists(path):
    done = set(pd.read_csv(path, dtype=str).pair)
todo = [(a, b) for a, b in pairs if f"{min(a,b)}|{max(a,b)}" not in done]
print(f"  {len(pairs):,} couples · {len(done):,} checkpointed · {len(todo):,} to fetch", flush=True)
w = open(path, "a", newline="")
wr = csv.writer(w)
if not done:
    wr.writerow(["pair", "n", "joint_works"])
B = 300
for i in range(0, len(todo), B):
    batch = todo[i:i + B]
    vals = " ".join(f"(wd:{a} wd:{b})" for a, b in batch)
    body = urllib.parse.urlencode({"query": Q.format(vals=vals), "format": "json"}).encode()
    req = urllib.request.Request(EP, data=body, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"})
    res = None
    for k in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as f:
                res = json.load(f)["results"]["bindings"]
            break
        except Exception as e:
            if k == 4:
                print(f"    batch {i} failed {str(e)[:60]}", flush=True)
            else:
                time.sleep(12)
    if res is None:
        continue
    got = {}
    for r in res:
        a = r["a"]["value"].rsplit("/", 1)[-1]; b = r["b"]["value"].rsplit("/", 1)[-1]
        got[(a, b)] = (r["n"]["value"], r["wk"]["value"])
    for a, b in batch:
        n, wk = got.get((a, b), ("0", "0"))
        wr.writerow([f"{min(a,b)}|{max(a,b)}", n, wk])
    w.flush()
    if (i // B) % 25 == 0:
        print(f"    {i + len(batch):,}/{len(todo):,}", flush=True)
    time.sleep(0.8)
w.close()
k = pd.read_csv(path, dtype=str)
n = pd.to_numeric(k.n, errors="coerce").fillna(0)
print(f"  COMPLETE: {len(k):,} couples · with children on record: {int((n > 0).sum()):,} "
      f"· mean among those {n[n > 0].mean():.1f}")
