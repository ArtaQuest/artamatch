"""bio_human.py — which of these "people" are actually people?

The harvest asked Wikidata for anything with a birth date and a spouse. It never asked whether the
subject was HUMAN, so fictional characters carrying P569 and P26 came along — a judge found Indiana
Jones married to Marion Ravenwood in the middle of the batch. This fetches P31 (instance of) for every
person in a judged-or-judgeable couple and records whether Q5 (human) is among its values.

-> ~/.artamatch-dev/bio/humans.csv (qid,is_human)
"""
import csv, json, os, socket, time, urllib.parse, urllib.request
import pandas as pd
socket.setdefaulttimeout(240)
BIO = os.path.expanduser("~/.artamatch-dev/bio")
UA = "ArtaMatch research (https://artaquest.com; arash@artaquest.org)"
EP = "https://query.wikidata.org/sparql"
OUT = f"{BIO}/humans.csv"
Q = """SELECT ?a (COUNT(?h) AS ?n) WHERE {{
  VALUES ?a {{ {vals} }}
  OPTIONAL {{ ?a wdt:P31 ?h . FILTER(?h = wd:Q5) }}
}} GROUP BY ?a"""


def ask(q, tries=5):
    body = urllib.parse.urlencode({"query": q, "format": "json"}).encode()
    req = urllib.request.Request(EP, data=body, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=240) as f:
                return json.load(f)["results"]["bindings"]
        except Exception as e:
            if k == tries - 1:
                print(f"    batch failed: {str(e)[:60]}", flush=True)
                return None
            time.sleep(20 if getattr(e, "code", 0) == 429 else 10)


def main():
    m = pd.read_csv(f"{BIO}/marriages.csv", dtype=str)
    m["n"] = pd.to_numeric(m.n_chars, errors="coerce").fillna(0)
    cand = m[(m.n > 100) & (pd.to_numeric(m.fullprec, errors="coerce").fillna(0) == 1)]
    qids = sorted(set(cand.pid_a) | set(cand.pid_b))
    done = set(pd.read_csv(OUT, dtype=str).qid) if os.path.exists(OUT) else set()
    todo = [q for q in qids if q not in done]
    print(f"  {len(qids):,} people in judgeable couples · {len(todo):,} to check", flush=True)
    w = csv.writer(open(OUT, "a", newline=""))
    if not done:
        w.writerow(["qid", "is_human"])
    B = 500
    for i in range(0, len(todo), B):
        batch = todo[i:i + B]
        rs = ask(Q.format(vals=" ".join(f"wd:{x}" for x in batch)))
        if rs is None:
            continue
        got = {r["a"]["value"].rsplit("/", 1)[-1]: int(r["n"]["value"]) > 0 for r in rs}
        for q in batch:
            w.writerow([q, int(got.get(q, False))])
        if (i // B) % 10 == 0:
            print(f"    {i + len(batch):,}/{len(todo):,}", flush=True)
        time.sleep(0.8)
    h = pd.read_csv(OUT, dtype=str)
    nonhuman = h[h.is_human == "0"]
    print(f"  COMPLETE · {len(h):,} checked · NOT human: {len(nonhuman):,} ({len(nonhuman)/max(1,len(h)):.2%})")


if __name__ == "__main__":
    main()
