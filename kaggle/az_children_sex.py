"""az_children_sex.py — the children-sex harvest fanned out over Azure containers (operator 2026-09-03:
"you can spread out in az servers"). WDQS throttles per IP; six containers are six IPs.
Each container gets its slice of couples as a gzip+base64 ENV variable (well under the 128 KB
argument cap), runs the same P22/P25 + P21 + P569 query loop with the standard library only, and
prints its CSV gzip+base64 between markers in its logs. The poller fetches `az container logs`,
merges every slice, writes ~/.artamatch-dev/bio/children_sex.csv and appends the 'wrote' line to
the local harvest log so the waiting chain proceeds.
Usage: python az_children_sex.py launch | poll
"""
import base64, gzip, json, os, subprocess, sys, time
import pandas as pd
RG, LOC, IMAGE, N = "artamatch-harvest-se", "swedencentral", "python:3.12-slim", 6
D_ = os.path.expanduser("~/.artamatch-dev/tilldeath_wt3"); OUT = os.path.expanduser("~/.artamatch-dev/bio/children_sex.csv")
LOG = os.path.expanduser("~/.artamatch-dev/wd_children_sex.log")
WORKER = r'''
import base64, gzip, json, os, sys, time, urllib.parse, urllib.request
pairs = [l.split(",") for l in gzip.decompress(base64.b64decode(os.environ["SLICE"])).decode().split("\n") if l]
UA = {"User-Agent": "ArtaMatch research (https://artaquest.com; children's sex; azure shard)", "Accept": "application/sparql-results+json"}
MALE, FEM = "Q6581097", "Q6581072"
def sparql(q, tries=6):
    data = urllib.parse.urlencode({"query": q}).encode()
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://query.wikidata.org/sparql", data=data, headers=UA), timeout=180) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:
            print("retry", t, str(e)[:60], flush=True); time.sleep(15 * (t + 1))
    return []
qid = lambda v: v.rsplit("/", 1)[1]
rows = {}
for lo in range(0, len(pairs), 120):
    ch = pairs[lo:lo + 120]
    vals = " ".join("(wd:%s wd:%s)" % (a, b) for a, b in ch)
    res = sparql("SELECT ?a ?b ?c ?sex ?dob WHERE { VALUES (?a ?b) { %s } { ?c wdt:P22 ?a ; wdt:P25 ?b . } UNION { ?c wdt:P22 ?b ; wdt:P25 ?a . } OPTIONAL { ?c wdt:P21 ?sex . } OPTIONAL { ?c wdt:P569 ?dob . } }" % vals)
    kids = {}
    for r in res:
        key = "|".join(sorted([qid(r["a"]["value"]), qid(r["b"]["value"])]))
        c = qid(r["c"]["value"]); sx = qid(r["sex"]["value"]) if "sex" in r else ""
        dob = r["dob"]["value"][:10] if "dob" in r else ""
        e = kids.setdefault(key, {}).setdefault(c, {"sex": "", "dob": ""})
        if sx in (MALE, FEM): e["sex"] = "M" if sx == MALE else "F"
        if dob and (not e["dob"] or dob < e["dob"]): e["dob"] = dob
    for key, d in kids.items():
        boys = sum(1 for e in d.values() if e["sex"] == "M"); girls = sum(1 for e in d.values() if e["sex"] == "F")
        unk = sum(1 for e in d.values() if not e["sex"])
        dated = sorted((e["dob"], e["sex"]) for e in d.values() if e["dob"] and e["sex"])
        rows[key] = (len(d), boys, girls, unk, dated[0][1] if dated else "")
    if (lo // 120) % 25 == 0: print("progress", lo + len(ch), len(pairs), len(rows), flush=True)
    time.sleep(0.6)
csv = "\n".join("%s,%d,%d,%d,%d,%s" % (k, *v) for k, v in rows.items())
print("BEGIN_CSV\n" + base64.b64encode(gzip.compress(csv.encode())).decode() + "\nEND_CSV", flush=True)
'''
def sh(*a, **k): return subprocess.run(a, capture_output=True, text=True, timeout=k.get("timeout", 600))
def slices():
    full = pd.read_csv(f"{D_}/full.csv", dtype=str)
    pairs = [(a, b) for a, b, n in zip(full.pid_a, full.pid_b, pd.to_numeric(full.n_children, errors="coerce").fillna(0)) if n >= 1]
    k = (len(pairs) + N - 1) // N
    return [pairs[i * k:(i + 1) * k] for i in range(N)]
def create(i, sl):
    W = base64.b64encode(WORKER.encode()).decode()
    env = base64.b64encode(gzip.compress("\n".join(f"{a},{b}" for a, b in sl).encode())).decode()
    r = sh("az", "container", "create", "-g", RG, "-n", f"kidsex{i}", "--image", IMAGE, "--location", LOC,
           "--restart-policy", "Never", "--cpu", "1", "--memory", "1.5", "--os-type", "Linux",
           "--environment-variables", f"SLICE={env}", f"W={W}",
           "--command-line", "python -c \"import base64,os;exec(base64.b64decode(os.environ['W']))\"", timeout=900)
    ok = r.returncode == 0
    print(f"shard {i}: {len(sl):,} couples · create -> {'ok' if ok else (r.stderr or r.stdout).strip()[-120:]}", flush=True)
    return ok
def launch():
    for i, sl in enumerate(slices()):
        create(i, sl)
def poll():
    """a SCHEDULER, not a waiter: the region allows six cores and two belong to the relay, so at most
    four shards run at once; a finished shard is merged, deleted to free its core, and the next
    pending shard is launched into the slot."""
    S = slices(); rows = {}; done = set(); running = set(); pending = []
    for i in range(N):
        st = sh("az", "container", "show", "-g", RG, "-n", f"kidsex{i}", "--query", "instanceView.state", "-o", "tsv")
        (running if st.returncode == 0 and st.stdout.strip() else pending).add(i) if False else (running.add(i) if (st.returncode == 0 and st.stdout.strip()) else pending.append(i))
    print(f"running {sorted(running)} · pending {pending}", flush=True)
    while len(done) < N:
        time.sleep(60)
        for i in sorted(running):
            st = sh("az", "container", "show", "-g", RG, "-n", f"kidsex{i}", "--query", "instanceView.state", "-o", "tsv").stdout.strip()
            if st in ("Succeeded", "Failed", "Terminated", "Stopped"):
                logs = sh("az", "container", "logs", "-g", RG, "-n", f"kidsex{i}", timeout=600).stdout
                if "BEGIN_CSV" in logs:
                    b = logs.split("BEGIN_CSV\n", 1)[1].split("\nEND_CSV", 1)[0]
                    for line in gzip.decompress(base64.b64decode(b)).decode().split("\n"):
                        if line: p = line.split(","); rows[p[0]] = p[1:]
                    print(f"shard {i}: {st} · merged {len(rows):,} couples so far", flush=True)
                else:
                    print(f"shard {i}: {st} without a CSV — tail: {logs[-200:]!r}", flush=True); pending.append(i)
                sh("az", "container", "delete", "-g", RG, "-n", f"kidsex{i}", "--yes")
                running.discard(i); done.add(i) if "BEGIN_CSV" in logs else None
        while pending and len(running) < 4:
            i = pending.pop(0)
            if create(i, S[i]): running.add(i)
            else: pending.append(i); break
        print(f"done {sorted(done)} · running {sorted(running)} · pending {pending}", flush=True)
    with open(OUT, "w") as f:
        f.write("pair,n_linked,boys,girls,unknown,firstborn\n")
        for k, v in rows.items(): f.write(",".join([k] + v) + "\n")
    b = sum(1 for v in rows.values() if int(v[1]) and not int(v[2])); g = sum(1 for v in rows.values() if int(v[2]) and not int(v[1])); both = sum(1 for v in rows.values() if int(v[1]) and int(v[2]))
    msg = f"wrote {OUT}: {len(rows):,} couples · boys only {b:,} · girls only {g:,} · both {both:,} · firstborn known {sum(1 for v in rows.values() if v[4]):,}"
    print(msg, flush=True); open(LOG, "a").write(msg + "\n")
if __name__ == "__main__":
    launch() if sys.argv[1] == "launch" else poll()
