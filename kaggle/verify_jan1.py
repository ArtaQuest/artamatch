"""verify_jan1.py — for each day-precision Jan-1 birth claim, check the person's WIKIPEDIA article:
verified only if the English intro states the birth as '1 January <year>' / 'January 1, <year>' with the
claimed year. Unverified (no article, or the article does not say it) -> the date stays year-only.
Writes ~/.artamatch-dev/jan1_verified.csv (qid, year, title, verified)."""
import glob, json, os, re, sys, time, urllib.parse, urllib.request
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from build_remarriage import qid as _qid
UA = {"User-Agent": "ArtaMatch-audit/1.0 (research corpus verification)"}
OUT = os.path.expanduser("~/.artamatch-dev/jan1_verified.csv")

cand = list(np.load(os.path.expanduser("~/.artamatch-dev/_jan1_qids.npy")))
SRC = os.path.expanduser("~/.artamatch-dev/marriages")
fr = [pd.read_csv(f, dtype=str, usecols=["a", "adob", "aprec"]) for f in sorted(glob.glob(os.path.join(SRC, "d*.csv")))]
d = pd.concat(fr, ignore_index=True)
d["a"] = d.a.map(_qid)
p = pd.to_numeric(d.aprec, errors="coerce")
md = d.adob.astype(str).str.extract(r"^[+-]?(\d{4})-(\d{2})-(\d{2})")
j1 = d[(p >= 11) & (md[1] == "01") & (md[2] == "01")].copy()
j1["year"] = md[0]
years = j1.groupby("a").year.agg(lambda s: s.iloc[0] if s.nunique() == 1 else "")
years = {q: y for q, y in years.items() if q in set(cand) and y}
print(f"  {len(years)} candidates with one unambiguous Jan-1 year")

done = set()
if os.path.exists(OUT):
    done = set(pd.read_csv(OUT, dtype=str).qid)
todo = [q for q in years if q not in done]
print(f"  {len(todo)} to fetch ({len(done)} checkpointed)")

def api(url):
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(max(int(e.headers.get("Retry-After", "30") or 30), 30))
            elif attempt == 5:
                raise
            else:
                time.sleep(10)
        except Exception:
            if attempt == 5:
                raise
            time.sleep(10)

# 1. sitelinks
titles = {}
for i in range(0, len(todo), 50):
    batch = todo[i:i + 50]
    j = api("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=sitelinks&ids="
            + "|".join(batch))
    for q, e in j.get("entities", {}).items():
        sl = e.get("sitelinks", {})
        t = sl.get("enwiki", {}).get("title")
        if t:
            titles[q] = t
    time.sleep(1.5)
print(f"  {len(titles)} have an English Wikipedia article")

# 2. intros, 20 titles per call
by_title = {t: q for q, t in titles.items()}
tl = list(by_title)
rows = []
for i in range(0, len(tl), 20):
    batch = tl[i:i + 20]
    url = ("https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&exintro=1"
           "&explaintext=1&redirects=1&titles=" + urllib.parse.quote("|".join(batch)))
    j = api(url)
    pages = j.get("query", {}).get("pages", {})
    norm = {}
    for r_ in j.get("query", {}).get("normalized", []) + j.get("query", {}).get("redirects", []):
        norm[r_["to"]] = r_["from"]
    for pg in pages.values():
        t = pg.get("title", "")
        orig = norm.get(t, t)
        q = by_title.get(orig) or by_title.get(t)
        if not q:
            continue
        y = years[q]
        ext = pg.get("extract", "") or ""
        pat = rf"(1\s+January\s+{y}|January\s+1,?\s+{y})"
        ok = bool(re.search(pat, ext))
        rows.append((q, y, orig, int(ok)))
    time.sleep(1.5)
for q in todo:
    if q not in titles:
        rows.append((q, years[q], "", 0))
pd.DataFrame(rows, columns=["qid", "year", "title", "verified"]).to_csv(
    OUT, mode="a", header=not os.path.exists(OUT), index=False)
v = pd.read_csv(OUT, dtype=str)
print(f"  COMPLETE: {len(v)} checked · verified real Jan-1: {(v.verified == '1').sum()} · "
      f"demoted to year-only: {(v.verified == '0').sum()}")
