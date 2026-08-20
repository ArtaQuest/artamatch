"""
wiki_start_harvest.py — harvest WEDDING DATES from the top-20 language Wikipedias for marriages Wikidata knows
but cannot date (operator 2026-08-20: "scrape more data across different languages of wiki. each database has its
own unique data").

WHY THIS FINDS NEW DATA. The dataset requires the marriage's START; the scraper reads it from Wikidata's P580
qualifier. Hundreds of thousands of P26 marriages carry no P580 — but the wedding YEAR often sits in a language
wiki's infobox: enwiki writes {{marriage|Alma|1903|1919}}, dewiki "⚭ 1903", ruwiki «в браке с 1903», etc. Each
wiki dates couples the others do not, so every language adds rows no other source has.

THE PIPELINE (all phases resumable, all files under AQ_DIR=/tmp/aqwiki):
  A pool.csv       SPARQL (decade-sliced, cached): P26 pairs, both partners dated, an end derivable (P582 or a
                   death), NO P580 — plus dob/prec, death, P582, birthplace coords for both partners
  B sitelinks/     wbgetentities (batched 50): each partner's article title in each TARGET language + labels
  C found.csv      per language: batch-fetch the SUBJECT's wikitext (20 titles/request, the language's own API),
                   locate the SPOUSE (local title or label) inside a marriage/spouse construct, extract the years:
                   the marriage-template family by name per wiki, else the spouse parameter's value line, else a
                   "(m. 1903)"-style parenthetical after the spouse's name. Start = the FIRST year in the match
                   (templates put it first); a full day is kept when the text carries one. Every row records the
                   language and the exact snippet, so any extraction can be audited.
  D merge          rows in the dataset's own column shape; consumed by scrape_duration.py via AQ_WIKI_STARTS so
                   every downstream rule (longest marriage, gap filter, the split, the label) applies unchanged.
Politeness: one worker per wiki, 25 req/s ceiling overall, UA with contact, exponential backoff, maxlag=5.
Usage: python wiki_start_harvest.py pool|sitelinks|harvest [--langs en,de,...]     (default: all phases in order)
"""
import csv
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import concurrent.futures as cf

DIR = os.environ.get("AQ_DIR", "/tmp/aqwiki"); os.makedirs(DIR, exist_ok=True)
UA = "ArtaMatch/5.0 (https://www.artaquest.com; arash@artaquest.org) wedding-date harvest"
LANGS = [l for l in os.environ.get("AQ_LANGS", "en,de,fr,es,it,ru,ja,pt,pl,nl,sv,zh,uk,cs,fa,ar,tr,hu,fi,da,hy").split(",") if l]   # 20 + Armenian (operator 2026-08-20)
FLOOR, CEIL = 1600, 2026
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:7.0f}s]", *a, flush=True)

# the per-wiki constructs that carry a wedding date; every pattern demands the SPOUSE nearby (checked separately)
MARRIAGE_TEMPLATES = {"en": ["marriage"], "simple": ["marriage"], "tr": ["evlilik"], "fa": ["ازدواج"], "ar": ["زواج"]}
SPOUSE_PARAMS = {"en": ["spouse", "wife", "husband", "partner"], "de": ["ehepartner", "partner"], "fr": ["conjoint", "conjointe", "époux", "épouse"],
                 "es": ["cónyuge", "pareja"], "it": ["coniuge", "consorte"], "ru": ["супруг", "супруга"], "ja": ["配偶者"], "pt": ["cônjuge"],
                 "pl": ["małżonek", "małżonka", "żona", "mąż"], "nl": ["echtgenoot", "echtgenote", "partner"], "sv": ["make", "maka", "partner"],
                 "zh": ["配偶"], "uk": ["дружина", "чоловік", "у шлюбі з"], "cs": ["choť", "manžel", "manželka", "partner"], "fa": ["همسر"],
                 "ar": ["الزوج", "الزوجة", "زوجة", "زوج"], "tr": ["evlilik", "eş"], "hu": ["házastárs"], "fi": ["puoliso"], "da": ["ægtefælle"], "hy": ["ամուսին", "կին", "ամուսնացած"]}
YEAR = r"(1[6-9]\d\d|20[0-2]\d)"


def http(url, data=None, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                return None
            time.sleep(min(120, 4 * 2 ** i))


# ── phase A: the pool ────────────────────────────────────────────────────────────────────────────────────────────
def sparql(q, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request("https://query.wikidata.org/sparql", data=urllib.parse.urlencode({"query": q, "format": "json"}).encode(),
                                         headers={"User-Agent": UA, "Accept": "application/sparql-results+json", "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:
            log(f"    sparql {type(e).__name__} {str(e)[:60]} — wait {min(300, 15 * 2 ** i)}s"); time.sleep(min(300, 15 * 2 ** i))
    return None


def pool():
    out = os.path.join(DIR, "pool.csv"); done_slices = set()
    if os.path.exists(out):
        for r in csv.reader(open(out)):
            if r and r[0] == "#slice":
                done_slices.add(r[1])
    f = open(out, "a", newline=""); w = csv.writer(f)
    if os.path.getsize(out) == 0:
        w.writerow(["a", "b", "adob", "aprec", "bdob", "bprec", "adeath", "bdeath", "end", "alat", "alon", "blat", "blon"])
    V = lambda r, k: r.get(k, {}).get("value", "")
    for lo in range(FLOOR, 2010, 10):
        tag = f"{lo}"
        if tag in done_slices:
            continue
        q = f"""SELECT ?a ?b ?adob ?aprec ?bdob ?bprec ?adeath ?bdeath ?end ?apob ?bpob WHERE {{
  ?a p:P26 ?m . ?m ps:P26 ?b . FILTER(STR(?a) < STR(?b))
  ?a p:P569/psv:P569 ?av . ?av wikibase:timeValue ?adob ; wikibase:timePrecision ?aprec . FILTER(YEAR(?adob) >= {lo} && YEAR(?adob) < {lo + 10})
  ?b p:P569/psv:P569 ?bv . ?bv wikibase:timeValue ?bdob ; wikibase:timePrecision ?bprec .
  FILTER NOT EXISTS {{ ?m pq:P580 ?st }}
  OPTIONAL {{ ?m pq:P582 ?end }} OPTIONAL {{ ?a wdt:P570 ?adeath }} OPTIONAL {{ ?b wdt:P570 ?bdeath }}
  OPTIONAL {{ ?a wdt:P19/wdt:P625 ?apob }} OPTIONAL {{ ?b wdt:P19/wdt:P625 ?bpob }}
  FILTER(BOUND(?end) || BOUND(?adeath) || BOUND(?bdeath)) }}"""
        rows = sparql(q)
        if rows is None:
            log(f"  pool {lo}s: FAILED, will resume"); continue
        n = 0
        for r in rows:
            pt = lambda s: re.match(r"Point\((\S+) (\S+)\)", s or "")
            pa, pb = pt(V(r, "apob")), pt(V(r, "bpob"))
            w.writerow([V(r, "a").rsplit("/", 1)[-1], V(r, "b").rsplit("/", 1)[-1], V(r, "adob")[:10], V(r, "aprec"), V(r, "bdob")[:10], V(r, "bprec"),
                        V(r, "adeath")[:10], V(r, "bdeath")[:10], V(r, "end")[:10],
                        pa.group(2) if pa else "", pa.group(1) if pa else "", pb.group(2) if pb else "", pb.group(1) if pb else ""]); n += 1
        w.writerow(["#slice", tag]); f.flush(); log(f"  pool {lo}s: {n:,} pairs"); time.sleep(3)
    f.close(); log(f"pool done -> {out}")


# ── phase B: sitelinks ───────────────────────────────────────────────────────────────────────────────────────────
def sitelinks():
    pool_rows = [r for r in csv.DictReader(open(os.path.join(DIR, "pool.csv"))) if r["a"] != "#slice"]
    qids = sorted({r["a"] for r in pool_rows} | {r["b"] for r in pool_rows})
    out = os.path.join(DIR, "sitelinks.jsonl"); have = set()
    if os.path.exists(out):
        for line in open(out):
            try: have.add(json.loads(line)["qid"])
            except Exception: pass
    todo = [q for q in qids if q not in have]; log(f"sitelinks: {len(qids):,} people, {len(todo):,} to fetch")
    props = "sitelinks|labels"; wikis = [l + "wiki" for l in LANGS]
    with open(out, "a") as f:
        for i in range(0, len(todo), 50):
            chunk = todo[i:i + 50]
            j = http("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(chunk), "props": props, "format": "json", "maxlag": 5}))
            if not j or "entities" not in j:
                log(f"  sitelinks batch {i}: failed, will resume"); time.sleep(20); continue
            for qid, e in j["entities"].items():
                sl = {k[:-4]: v["title"] for k, v in (e.get("sitelinks") or {}).items() if k in wikis}
                lb = {k: v["value"] for k, v in (e.get("labels") or {}).items() if k in LANGS}
                f.write(json.dumps({"qid": qid, "sl": sl, "lb": lb}, ensure_ascii=False) + "\n")
            if i % 2000 == 0:
                f.flush(); log(f"  sitelinks {i:,}/{len(todo):,}")
            time.sleep(0.35)
    log("sitelinks done")


# ── phase C: the wikitext harvest ────────────────────────────────────────────────────────────────────────────────
def _find_dates(lang, text, spouse_names):
    """(start_iso, prec, snippet) for the marriage to this spouse in this wikitext, or None. prec 11 day / 9 year."""
    esc = [re.escape(n) for n in spouse_names if n and len(n) > 2]
    if not esc:
        return None
    name_re = "(?:" + "|".join(esc) + ")"
    # 1. the marriage-template family: {{marriage|[[Spouse]]|1903|1919}} and language twins
    for tpl in MARRIAGE_TEMPLATES.get(lang, []) + MARRIAGE_TEMPLATES.get("en", []):
        for m in re.finditer(r"\{\{\s*" + re.escape(tpl) + r"\s*\|([^{}]*)\}\}", text, re.I):
            body = m.group(1)
            if not re.search(name_re, body, re.I):
                continue
            iso = re.search(YEAR + r"-(\d\d)-(\d\d)", body)
            if iso:
                return iso.group(0), 11, body[:160]
            MONTHS_EN = {m: i + 1 for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"))}
            d1 = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+" + YEAR, body) or re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s*" + YEAR, body)
            if d1:
                g = d1.groups(); mon = MONTHS_EN.get((g[1] if g[0].isdigit() else g[0]).lower()); day = int(g[0] if g[0].isdigit() else g[1]); yr4 = g[2]
                if mon:
                    return f"{yr4}-{mon:02d}-{day:02d}", 11, body[:160]
            yr = re.search(YEAR, body)
            if yr:
                return yr.group(0) + "-00-00", 9, body[:160]
    # 2. the spouse parameter's value line: |spouse = [[Name]] (m. 1903; div 1919) / ⚭ 1903 / с 1903
    for par in SPOUSE_PARAMS.get(lang, []) + SPOUSE_PARAMS.get("en", []):
        for m in re.finditer(r"\|\s*" + re.escape(par) + r"\s*=([^\n]*?" + name_re + r"[^\n]*)", text, re.I):
            line = m.group(1)
            yr = re.search(YEAR, line)
            if yr:
                return yr.group(0) + "-00-00", 9, line[:160]
    # 3. a parenthetical right after the spouse's name, REQUIRING a marriage marker — "(1848–1919)" is a lifespan
    MARK = {"en": r"m\.|marr", "de": r"⚭|verh", "fr": r"mari|ép", "es": r"matr|casad", "it": r"spos", "ru": r"брак|с\s", "uk": r"шлюб|з\s", "pl": r"ślub|od\s", "pt": r"casad", "nl": r"getr", "sv": r"gift", "da": r"gift", "fi": r"avio", "cs": r"sňat|od\s", "hu": r"házas", "tr": r"evl", "fa": r"ازدواج", "ar": r"تزوج|زواج", "ja": r"結婚", "zh": r"结婚|結婚", "hy": r"ամուսն"}
    mark = MARK.get(lang, r"⚭|m\.")
    m = re.search(name_re + r"[^\n(]{0,40}\((?:[^)]{0,40}?(?:" + mark + r")[^)]{0,40}?)" + YEAR + r"[^)]*\)", text, re.I)
    if m:
        yr = re.search(YEAR, m.group(0))
        return yr.group(0) + "-00-00", 9, m.group(0)[:160]
    # 4. PROSE (the wikis that keep marriage in running text — dewiki rejects person infoboxes altogether):
    #    "heiratete [am 9. März] 1902 [[Alma]]" / "épousa [[Alma]] en 1902" / "женился на [[Альме]] в 1902" —
    #    a marriage VERB, the spouse and a year within one clause, either order; the plausibility gate downstream
    #    still rejects any year that cannot be a wedding
    VERB = {"de": r"heiratete|ehelichte|verm[äa]hlte|schloss.{0,20}Ehe", "fr": r"épous[ae]|se mari[ae]|mariage avec", "es": r"se cas[óo]|contrajo matrimonio",
            "it": r"spos[òo]", "pt": r"casou(?:-se)?", "ru": r"женился|вышла замуж|вступил[аи]? в брак|обвенчал", "uk": r"одружився|вийшла заміж",
            "pl": r"poślubił|ożenił|wyszła za", "nl": r"trouwde|huwde", "sv": r"gifte sig", "da": r"giftede sig", "fi": r"avioitui|meni naimisiin",
            "cs": r"oženil se|vdala se|vzal si", "hu": r"feleségül vette|házasságot kötött", "tr": r"evlendi", "ja": r"結婚", "zh": r"结婚|結婚",
            "fa": r"ازدواج کرد", "ar": r"تزوج", "hy": r"ամուսնացավ|ամուսնացել", "en": r"married"}
    verb = VERB.get(lang)
    if verb:
        win = r"[^\n;]{0,90}"          # periods allowed: German ordinal dates ("9. März 1902") sit inside the clause
        for pat in (r"(?:" + verb + r")" + win + name_re + win + YEAR, r"(?:" + verb + r")" + win + YEAR + win + name_re,
                    name_re + win + r"(?:" + verb + r")" + win + YEAR, YEAR + win + r"(?:" + verb + r")" + win + name_re):
            m = re.search(pat, text, re.I)
            if m:
                yr = re.search(YEAR, m.group(0))
                return yr.group(0) + "-00-00", 9, m.group(0)[:160]
    return None


def harvest(langs=None):
    pool_rows = [r for r in csv.DictReader(open(os.path.join(DIR, "pool.csv"))) if r["a"] != "#slice"]
    SL = {}
    for line in open(os.path.join(DIR, "sitelinks.jsonl")):
        try: j = json.loads(line); SL[j["qid"]] = j
        except Exception: pass
    out = os.path.join(DIR, "found.csv"); have = set()
    if os.path.exists(out):
        for r in csv.reader(open(out)):
            if len(r) >= 5:
                have.add((r[0], r[1], r[4]))
    f = open(out, "a", newline=""); w = csv.writer(f)
    def one_lang(lang):
        api = f"https://{lang}.wikipedia.org/w/api.php"
        jobs = []
        for r in pool_rows:
            for subj, sp in ((r["a"], r["b"]), (r["b"], r["a"])):
                t = SL.get(subj, {}).get("sl", {}).get(lang)
                if not t or (r["a"], r["b"], lang) in have:
                    continue
                names = [SL.get(sp, {}).get("sl", {}).get(lang, ""), SL.get(sp, {}).get("lb", {}).get(lang, ""), SL.get(sp, {}).get("lb", {}).get("en", "")]
                jobs.append((r, subj, t, [n for n in names if n]))
        log(f"  {lang}: {len(jobs):,} article reads queued")
        got = 0
        for i in range(0, len(jobs), 20):
            chunk = jobs[i:i + 20]; titles = "|".join(dict.fromkeys(j[2] for j in chunk))
            resp = http(api + "?" + urllib.parse.urlencode({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "titles": titles, "format": "json", "redirects": 1, "maxlag": 5}))
            if not resp:
                time.sleep(15); continue
            pages = {p.get("title", ""): (p.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("*", "") for p in (resp.get("query", {}).get("pages", {}) or {}).values()}
            norm = {n.get("from"): n.get("to") for n in resp.get("query", {}).get("normalized", [])}
            for r, subj, title, names in chunk:
                text = pages.get(norm.get(title, title), "")
                if not text:
                    continue
                hit = _find_dates(lang, text, names)
                if hit:
                    st, prec, snip = hit; sy = int(st[:4])
                    by = [int(r[k][:4]) for k in ("adob", "bdob") if r[k][:4].isdigit()]
                    ey = [int(r[k][:4]) for k in ("end", "adeath", "bdeath") if r[k][:4].isdigit()]
                    # a wedding before either 14th birthday, or after the marriage's own end, is a misread — dropped
                    if by and sy < max(by) + 14:
                        continue
                    if ey and sy > min(ey):
                        continue
                    w.writerow([r["a"], r["b"], st, prec, lang, subj, snip.replace("\n", " ")]); got += 1
            if i % 400 == 0 and i:
                f.flush(); log(f"  {lang}: {i:,}/{len(jobs):,} read · {got:,} dates found")
            time.sleep(0.6)
        log(f"  {lang}: DONE — {got:,} wedding dates found")
        return got
    langs = langs or LANGS
    with cf.ThreadPoolExecutor(min(6, len(langs))) as ex:
        totals = list(ex.map(one_lang, langs))
    f.close(); log(f"harvest done: {sum(totals):,} dates across {len(langs)} languages -> {out}")


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase in ("pool", "all"): pool()
    if phase in ("sitelinks", "all"): sitelinks()
    if phase in ("harvest", "all"): harvest()
