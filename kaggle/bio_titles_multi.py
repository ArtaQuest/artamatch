"""bio_titles_multi.py — for every person in an ended marriage: which of the 21 Wikipedias has an
article about them, and what their NAME is in each of those languages.

The name matters as much as the article: an Armenian article calls her "Աննա", not "Anna", so the only
way to find the passages about her is to carry Wikidata's Armenian label. Sitelinks and labels are
fetched in two separate passes so neither query explodes into a cross product.

-> ~/.artamatch-dev/bio/sitelinks.csv (qid,lang,title) · labels_multi.csv (qid,lang,label)
"""
import csv, json, os, socket, sys, time, urllib.parse, urllib.request
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bio_langs import LANGS
socket.setdefaulttimeout(240)
BIO = os.path.expanduser("~/.artamatch-dev/bio")
UA = "ArtaMatch research (https://artaquest.com; arash@artaquest.org)"
EP = "https://query.wikidata.org/sparql"
SITES = " ".join(f"<https://{l}.wikipedia.org/>" for l in LANGS)
LANGLIST = ", ".join(f'"{l}"' for l in LANGS)

Q_SITE = """SELECT ?a ?site ?article WHERE {{
  VALUES ?a {{ {vals} }}
  VALUES ?site {{ {sites} }}
  ?article schema:about ?a ; schema:isPartOf ?site .
}}"""
Q_LABEL = """SELECT ?a ?label WHERE {{
  VALUES ?a {{ {vals} }}
  ?a rdfs:label ?label .
  FILTER(LANG(?label) IN ({langs}))
}}"""


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
                print(f"    batch failed: {str(e)[:70]}", flush=True)
                return None
            time.sleep(15 if getattr(e, "code", 0) != 429 else 40)


def main():
    who = pd.read_csv(f"{BIO}/couples.csv", dtype=str)
    qids = sorted(set(who.pid_a) | set(who.pid_b))
    sp, lp = f"{BIO}/sitelinks.csv", f"{BIO}/labels_multi.csv"
    done_s = set(pd.read_csv(sp, dtype=str).qid) if os.path.exists(sp) else set()
    done_l = set(pd.read_csv(lp, dtype=str).qid) if os.path.exists(lp) else set()
    todo = [q for q in qids if q not in done_s or q not in done_l]
    print(f"  {len(qids):,} persons · {len(todo):,} to fetch across {len(LANGS)} languages", flush=True)
    ws = csv.writer(open(sp, "a", newline=""))
    wl = csv.writer(open(lp, "a", newline=""))
    if not done_s:
        ws.writerow(["qid", "lang", "title"])
    if not done_l:
        wl.writerow(["qid", "lang", "label"])
    B = 400
    for i in range(0, len(todo), B):
        batch = todo[i:i + B]
        vals = " ".join(f"wd:{x}" for x in batch)
        rs = ask(Q_SITE.format(vals=vals, sites=SITES))
        if rs is not None:
            for r in rs:
                q = r["a"]["value"].rsplit("/", 1)[-1]
                lang = r["site"]["value"].split("//")[1].split(".")[0]
                title = urllib.parse.unquote(r["article"]["value"].rsplit("/", 1)[-1]).replace("_", " ")
                ws.writerow([q, lang, title])
        rl = ask(Q_LABEL.format(vals=vals, langs=LANGLIST))
        if rl is not None:
            for r in rl:
                q = r["a"]["value"].rsplit("/", 1)[-1]
                wl.writerow([q, r["label"]["xml:lang"], r["label"]["value"]])
        # a person with no article anywhere still counts as done, or the resume loop never ends
        for q in batch:
            ws.writerow([q, "", ""])
            wl.writerow([q, "", ""])
        if (i // B) % 20 == 0:
            print(f"    {i + len(batch):,}/{len(todo):,}", flush=True)
        time.sleep(1.0)
    s = pd.read_csv(sp, dtype=str).fillna("")
    s = s[s.lang != ""]
    print(f"  COMPLETE · {len(s):,} articles across {s.lang.nunique()} languages")
    print("  top: " + " · ".join(f"{k} {v:,}" for k, v in s.lang.value_counts().head(12).items()))


if __name__ == "__main__":
    main()
