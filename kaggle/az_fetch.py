"""
az_fetch.py — fetch the remaining SPARQL slices from Azure container instances instead of this laptop.

WHY, AND IT IS MEASURED RATHER THAN ASSUMED. The same one-sided training count, three attempts each, minutes
apart on the same afternoon:

    this laptop  (residential)      200 in 24.0s   ·  HTTP 502  ·  200 in 40.4s
    Azure swedencentral             200 in 10.1s   ·  200 in 0.4s  ·  200 in 0.1s

Two to four hundred times faster with no failures, and the 0.4s/0.1s repeats say the datacenter path is served
from a cache the residential path never reaches. I had argued the opposite from the error codes -- 504 is a query
timeout and 502 an upstream error, so egress "could not matter" -- and the argument was wrong. The operator was
right to keep asking.

HOW THE ROWS COME BACK. Each container gzips its TSV and prints it base64 between markers; this reads them with
`az container logs`. No credentials travel to the container, no storage account is created, and nothing is
exposed to the internet. Container logs cap around 4 MB, and a 2 MB TSV gzips to roughly a tenth of that, so a
slice fits with a wide margin -- and the row count is verified against the endpoint's own COUNT before a slice is
accepted, so a truncated log is caught rather than cached.

WHAT IT WRITES. Exactly the cache files scrape_duration.py would have written, under the same hash-keyed names,
so the ordinary build picks them up as cache hits and every downstream assertion still runs locally.

Usage:
    ~/.artamatch-venv/bin/python az_fetch.py            # plan only: what would be fetched, in how many containers
    AQ_DO_FETCH=1 ~/.artamatch-venv/bin/python az_fetch.py
"""
import ast
import base64
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "scrape_duration.py")
CACHE = os.environ.get("AQ_SLICE_CACHE", "/tmp/aqdur/_dslices")
RG = os.environ.get("AQ_AZ_RG", "artaquest-relay")
LOC = os.environ.get("AQ_AZ_LOC", "swedencentral")
IMAGE = "python:3.12-slim"
CONTAINERS = int(os.environ.get("AQ_AZ_CONTAINERS", "6"))
SLICE = int(os.environ.get("AQ_YEAR_SLICE", "10"))


def scraper():
    """The scraper's own constants and query builders, read out of the file so this cannot drift from it."""
    tree = ast.parse(open(SRC).read())
    ns = {"os": os, "time": time}
    for n in tree.body:
        if isinstance(n, ast.Assign):
            t = n.targets[0]
            names = ([e.id for e in t.elts if isinstance(e, ast.Name)] if isinstance(t, ast.Tuple)
                     else [t.id] if isinstance(t, ast.Name) else [])
            if names and all(x in ("FLOOR", "CEIL", "CUT", "JULIAN", "PROJ", "PREFIXES", "UA", "RELS",
                                   "SLICE", "ABSENT", "MIN_YEARS", "MAX_GAP_YEARS") for x in names):
                try:
                    exec(compile(ast.Module(body=[n], type_ignores=[]), "s", "exec"), ns)
                except Exception:
                    pass
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name in ("dated", "relationship"):
            exec(compile(ast.Module(body=[n], type_ignores=[]), "s", "exec"), ns)
    return ns


S = scraper()
FLOOR, CUT, CEIL, PROJ, PREFIXES, UA, RELS = (S["FLOOR"], S["CUT"], S["CEIL"], S["PROJ"],
                                              S["PREFIXES"], S["UA"], S["RELS"])
dated, relationship = S["dated"], S["relationship"]
SELECT = f"DISTINCT {PROJ}"


def queries():
    """Every (name, lo0, hi0, body_fn) the build runs, in the build's own order and with its own bodies."""
    out = []
    for rel in RELS:
        out.append((f"test half ({rel})", CUT + 1, CEIL,
                    lambda lo, hi, rel=rel: (relationship(rel, dead=("a", "b"))
                                             + "\n  FILTER(STR(?a) < STR(?b))\n"
                                             + dated('a', lo, hi, 11) + dated('b', CUT + 1, CEIL, 11))))
        out.append((f"test half straddling {CUT} ({rel})", FLOOR, CUT,
                    lambda lo, hi, rel=rel: (relationship(rel, dead=("a", "b")) + "\n"
                                             + dated('a', lo, hi, 11) + dated('b', CUT + 1, CEIL, 11))))
        out.append((f"train both dated ({rel})", FLOOR, CUT,
                    lambda lo, hi, rel=rel: (relationship(rel, dead=()) + "\n  FILTER(STR(?a) < STR(?b))\n"
                                             + dated('a', lo, hi, 9, drop_placeholders=False)
                                             + dated('b', FLOOR, CUT, 9, drop_placeholders=False))))
        out.append((f"train one dated ({rel})", FLOOR, CUT,
                    lambda lo, hi, rel=rel: (relationship(rel, dead=()) + "\n"
                                             + dated('a', lo, hi, 9, drop_placeholders=False)
                                             + """
  OPTIONAL { ?b wdt:P21 ?bsex }
  OPTIONAL {
    ?b p:P569 ?bst . ?bst psv:P569 ?bval .
    ?bst wikibase:rank ?brank . FILTER(?brank != wikibase:DeprecatedRank)
    ?bval wikibase:timeValue ?bdob ; wikibase:timePrecision ?bprec .
  }""")))
    return out


def tag_of(name, body_fn, lo0, hi0):
    qh = hashlib.sha256((SELECT + "|" + body_fn(lo0, hi0)).encode()).hexdigest()[:10]
    return "".join(c if c.isalnum() else "_" for c in name) + "_" + qh


def missing():
    """Slices with no cache file yet — the work Azure should do."""
    todo = []
    for name, lo0, hi0, fn in queries():
        tag = tag_of(name, fn, lo0, hi0)
        if os.path.exists(os.path.join(CACHE, f"{tag}_{lo0}_{hi0}_whole.csv")):
            continue
        for lo in range(lo0, hi0 + 1, SLICE):
            hi = min(lo + SLICE - 1, hi0)
            path = os.path.join(CACHE, f"{tag}_{lo}_{hi}.csv")
            if os.path.exists(path) and os.path.getsize(path) >= 8:
                continue
            todo.append({"name": name, "tag": tag, "lo": lo, "hi": hi,
                         "body": fn(lo, hi), "path": path})
    return todo


WORKER = r'''
import base64, gzip, io, json, sys, time, urllib.parse, urllib.request, urllib.error
JOBS = json.loads(base64.b64decode(sys.argv[1]).decode())
PREFIXES, SELECT, UA = JOBS["prefixes"], JOBS["select"], JOBS["ua"]
EP = "https://query.wikidata.org/sparql"
def ask(q, accept, tries=5):
    last = None
    for i in range(tries):
        try:
            r = urllib.request.Request(EP + "?" + urllib.parse.urlencode({"query": q}),
                                       headers={"Accept": accept, "User-Agent": UA})
            with urllib.request.urlopen(r, timeout=300) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(5 * (i + 1))
    raise last
for j in JOBS["slices"]:
    key = j["tag"] + "|" + str(j["lo"]) + "|" + str(j["hi"])
    try:
        cq = PREFIXES + "\nSELECT (COUNT(*) AS ?n) WHERE { { SELECT " + SELECT + " WHERE { " + j["body"] + " } } }"
        d = json.loads(ask(cq, "application/sparql-results+json"))
        want = int(next(iter(d["results"]["bindings"][0].values()))["value"])
        rq = (PREFIXES + "\nSELECT " + SELECT + " WHERE { " + j["body"] + " } ORDER BY ?a ?b LIMIT 200000")
        tsv = ask(rq, "text/tab-separated-values")
        got = max(0, len(tsv.strip().splitlines()) - 1)
        blob = base64.b64encode(gzip.compress(tsv.encode())).decode()
        print("###SLICE " + key + " " + str(want) + " " + str(got) + " " + str(len(blob)))
        for i in range(0, len(blob), 3000):
            print(blob[i:i+3000])
        print("###END " + key)
    except Exception as e:
        print("###FAIL " + key + " " + type(e).__name__ + " " + str(e)[:120])
print("###DONE")
'''


def run():
    todo = missing()
    if not todo:
        print("  nothing to fetch — every slice is already cached")
        return
    groups = [todo[i::CONTAINERS] for i in range(CONTAINERS)]
    groups = [g for g in groups if g]
    print(f"  {len(todo)} slices missing, {len(groups)} containers, "
          f"{min(len(g) for g in groups)}-{max(len(g) for g in groups)} slices each")
    for g in groups[:1]:
        print(f"    e.g. {g[0]['name']} {g[0]['lo']}-{g[0]['hi']}")
    if os.environ.get("AQ_DO_FETCH") != "1":
        print("\n  PLAN ONLY — set AQ_DO_FETCH=1 to create the containers")
        return

    names = []
    for i, g in enumerate(groups):
        payload = base64.b64encode(json.dumps({
            "prefixes": PREFIXES, "select": SELECT, "ua": UA,
            "slices": [{"tag": s["tag"], "lo": s["lo"], "hi": s["hi"], "body": s["body"]} for s in g],
        }).encode()).decode()
        w = base64.b64encode(WORKER.encode()).decode()
        cname = f"aqfetch{i}"
        cmd = (f"/bin/sh -c \"echo {w} | base64 -d > /w.py && python /w.py {payload}\"")
        subprocess.run(["az", "container", "create", "-g", RG, "-n", cname, "--image", IMAGE,
                        "--os-type", "Linux", "--cpu", "1", "--memory", "1.5",
                        "--restart-policy", "Never", "--location", LOC,
                        "--command-line", cmd, "-o", "none"], check=False)
        names.append(cname)
        print(f"    started {cname} with {len(g)} slices")

    lookup = {s["tag"] + "|" + str(s["lo"]) + "|" + str(s["hi"]): s for s in todo}
    done, saved, failed = set(), 0, 0
    t0 = time.time()
    while len(done) < len(names) and time.time() - t0 < 3600:
        time.sleep(20)
        for cname in names:
            if cname in done:
                continue
            st = subprocess.run(["az", "container", "show", "-g", RG, "-n", cname,
                                 "--query", "instanceView.state", "-o", "tsv"],
                                capture_output=True, text=True).stdout.strip()
            logs = subprocess.run(["az", "container", "logs", "-g", RG, "-n", cname],
                                  capture_output=True, text=True).stdout
            n_new, n_fail = harvest(logs, lookup)
            saved += n_new
            failed += n_fail
            if "###DONE" in logs or st in ("Terminated", "Failed"):
                done.add(cname)
                print(f"    {cname} finished ({st}); {saved} slices written so far")
    for cname in names:
        subprocess.run(["az", "container", "delete", "-g", RG, "-n", cname, "--yes", "-o", "none"],
                       check=False)
    print(f"  wrote {saved} slices, {failed} failed; containers deleted")
    left = missing()
    print(f"  {len(left)} slices still missing — the local build will fetch those" if left
          else "  every slice is now cached")


def harvest(logs, lookup):
    """Pull complete ###SLICE...###END blocks out of a container log and write them as cache files."""
    saved = failed = 0
    lines = logs.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("###FAIL "):
            failed += 1
            print(f"      {lines[i][8:140]}")
            i += 1
            continue
        if not lines[i].startswith("###SLICE "):
            i += 1
            continue
        parts = lines[i].split()
        key, want, got = parts[1], int(parts[2]), int(parts[3])
        body, j = [], i + 1
        while j < len(lines) and not lines[j].startswith("###END "):
            body.append(lines[j].strip())
            j += 1
        if j >= len(lines):                     # the log is still being written; wait for the rest
            return saved, failed
        i = j + 1
        s = lookup.get(key)
        if s is None or os.path.exists(s["path"]):
            continue
        try:
            tsv = gzip.decompress(base64.b64decode("".join(body))).decode()
        except Exception as e:
            print(f"      {key}: log block did not decode ({type(e).__name__}) — leaving it to the local build")
            failed += 1
            continue
        df = pd.read_csv(io.StringIO(tsv), sep="\t", dtype=str, keep_default_na=False)
        for c in df.columns:
            df[c] = (df[c].str.replace(r"\^\^<[^>]*>$", "", regex=True)
                          .str.replace(r'^"(.*)"$', r"\1", regex=True))
        df.columns = [c.strip().lstrip("?") for c in df.columns]
        for c in df.columns:
            df[c] = df[c].str.strip().str.strip('"')
        expect = [v.lstrip("?") for v in SELECT.replace("DISTINCT", "").split()]
        if [c for c in expect if c not in df.columns]:
            print(f"      {key}: columns are {list(df.columns)[:4]}, not the projection — refusing")
            failed += 1
            continue
        if len(df) < want:
            print(f"      {key}: {len(df):,} rows against a count of {want:,} — truncated, refusing")
            failed += 1
            continue
        os.makedirs(CACHE, exist_ok=True)
        df.to_csv(s["path"] + ".tmp", index=False)
        os.replace(s["path"] + ".tmp", s["path"])
        print(f"      {s['name']} {s['lo']}-{s['hi']}: {len(df):,} rows (from Azure, count-verified)")
        saved += 1
    return saved, failed


if __name__ == "__main__":
    run()
