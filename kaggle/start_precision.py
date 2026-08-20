"""
start_precision.py — the PRECISION of every relationship's start date (P580 qualifier), for the pairs whose start
falls on the 1st of a month, WITHOUT refetching the slices.

WHY. The queries project the start as a bare time value, so Wikidata's year-precision start prints as YYYY-01-01
and a month-precision one as YYYY-MM-01 — indistinguishable from a real 1 January or a real first of the month.
Operator 2026-08-19: "ensure that YYYY-01-01 is not same as YYYY-00-00". The births already carry their precision
(`wikibase:timePrecision` is projected for them); this asks for the start's, by VALUES batches of (a, b) pairs over
every relationship property, and writes a resumable CSV the scraper reads: a, b, start (first 10 chars), precision
(9 year · 10 month · 11 day). A pair with more than one dated relationship gets one row per start.
Usage: python start_precision.py      # reads /tmp/aqdur/_dslices (the slice cache), writes /tmp/aqdur/_startprec.csv
"""
import csv
import glob
import os
import sys
import time
import urllib.parse
import urllib.request

import pandas as pd

CACHE = os.environ.get("AQ_SLICE_CACHE", "/tmp/aqdur/_dslices"); OUT = os.environ.get("AQ_START_PREC", "/tmp/aqdur/_startprec.csv")
UA = "ArtaMatch/4.0 (https://www.artaquest.com; arash@artaquest.org) start-date precision lookup"
BATCH = int(os.environ.get("AQ_PREC_BATCH") or 400); EP = "https://query.wikidata.org/sparql"
RELS = ("P26", "P451", "P1327", "P3342")


def pairs_in_cache():
    """(a, b, start10) for every cached row whose start is on the 1st of a month (the ambiguous ones)."""
    out = set()
    for f in glob.glob(os.path.join(CACHE, "*.csv")):
        try:
            df = pd.read_csv(f, dtype=str, keep_default_na=False)
        except Exception:
            continue
        cols = {c.lstrip("?"): c for c in df.columns}
        if not {"a", "b", "start"} <= set(cols):
            continue
        for a, b, st in zip(df[cols["a"]], df[cols["b"]], df[cols["start"]]):
            st10 = str(st)[:10]
            if len(st10) == 10 and st10[8:10] == "01":
                import re as _re
                qa, qb = _re.sub(r"[^Q0-9]", "", a.rsplit("/", 1)[-1]), _re.sub(r"[^Q0-9]", "", b.rsplit("/", 1)[-1])
                if qa.startswith("Q") and qb.startswith("Q") and qa[1:].isdigit() and qb[1:].isdigit():
                    out.add((qa, qb, st10))
    return sorted(out)


def ask(pairs, tries=8):
    vals = " ".join(f"(wd:{a} wd:{b})" for a, b, _ in pairs)
    q = f"""SELECT ?a ?b ?st ?prec WHERE {{ VALUES (?a ?b) {{ {vals} }}
  VALUES (?p ?ps) {{ {" ".join(f"(p:{r} ps:{r})" for r in RELS)} }}
  ?a ?p ?m . ?m ?ps ?b . ?m pqv:P580 ?v . ?v wikibase:timeValue ?st ; wikibase:timePrecision ?prec . }}"""
    body = urllib.parse.urlencode({"query": q, "format": "json"}).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(EP, data=body, headers={"User-Agent": UA, "Accept": "application/sparql-results+json", "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=180) as r:
                res = __import__("json").load(r)
            out = {}
            for row in res["results"]["bindings"]:
                a = row["a"]["value"].rsplit("/", 1)[-1]; b = row["b"]["value"].rsplit("/", 1)[-1]; st = row["st"]["value"][:10].lstrip("+"); p = int(row["prec"]["value"])
                out[(a, b, st)] = max(p, out.get((a, b, st), 0))
            return out
        except Exception as e:
            wait = min(180, 10 * 2 ** i); print(f"    {type(e).__name__}: {str(e)[:60]} — waiting {wait}s", flush=True); time.sleep(wait)
    return None


def main():
    pairs = pairs_in_cache(); print(f"  {len(pairs):,} ambiguous (a, b, start) triples in the cache", flush=True)
    done = {}
    if os.path.exists(OUT):
        for r in csv.reader(open(OUT)):
            if len(r) == 4:
                done[(r[0], r[1], r[2])] = r[3]
        print(f"  resuming: {len(done):,} already answered", flush=True)
    todo = [p for p in pairs if p not in done]; print(f"  {len(todo):,} to ask, {BATCH} per query", flush=True)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f); t0 = time.time()
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]; res = ask(chunk)
            if res is None:
                print("  giving up on this batch; rerun to resume", flush=True); continue
            n = 0
            for a, b, st in chunk:
                # the P580 value may sit on the OTHER direction of the statement (b's P26 to a); ask both keys
                p = res.get((a, b, st)) or res.get((b, a, st))
                w.writerow([a, b, st, p if p is not None else ""]); n += p is not None
            f.flush(); print(f"  {i + len(chunk):>7,}/{len(todo):,}  answered {n}/{len(chunk)}  {time.time()-t0:5.0f}s", flush=True)
            time.sleep(4.0)
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
