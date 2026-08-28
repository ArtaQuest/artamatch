"""bio_assemble.py — one marriage description per couple, read from up to 21 Wikipedias.

For each ended marriage the description is built from BOTH partners' articles, English first and then
the other languages, each language searched with that language's own name for the partner and its own
relationship vocabulary. Every row carries the REFERENCE LINKS the text was read from, so any judgement
can be checked against the source.

-> ~/.artamatch-dev/bio/marriages.csv
"""
import glob, gzip, json, os, re
import numpy as np, pandas as pd
from bio_extract import passages, tokens
from bio_langs import LANGS

BIO = os.path.expanduser("~/.artamatch-dev/bio")
ORDER = {l: i for i, l in enumerate(LANGS)}


def load_pages():
    """(lang, title) -> wikitext, from every shard downloaded so far"""
    wt = {}
    for f in sorted(glob.glob(f"{BIO}/pages/*.jsonl.gz")):
        with gzip.open(f, "rt") as fh:
            for line in fh:
                if not line.strip():
                    continue
                o = json.loads(line)
                lang = o.get("lang", "en")
                wt[(lang, o["title"])] = o["wikitext"]
                if o.get("resolved"):
                    wt.setdefault((lang, o["resolved"]), o["wikitext"])
    return wt


def main():
    cp = pd.read_csv(f"{BIO}/couples.csv", dtype=str)
    # articles: multilingual sitelinks if present, else the English-only sweep
    if os.path.exists(f"{BIO}/sitelinks.csv"):
        sl = pd.read_csv(f"{BIO}/sitelinks.csv", dtype=str).fillna("")
        sl = sl[(sl.lang != "") & (sl.title != "")]
    else:
        sl = pd.DataFrame(columns=["qid", "lang", "title"])
    if os.path.exists(f"{BIO}/titles.csv"):
        en = pd.read_csv(f"{BIO}/titles.csv", dtype=str).fillna("")
        en = en[en.title != ""][["qid", "title"]].assign(lang="en")
        sl = pd.concat([sl, en[["qid", "lang", "title"]]], ignore_index=True).drop_duplicates(["qid", "lang"])
    arts = {}
    for q, lang, t in zip(sl.qid, sl.lang, sl.title):
        arts.setdefault(q, {})[lang] = t
    # names per language, with the English label as the fallback everywhere
    lab = {}
    if os.path.exists(f"{BIO}/labels_multi.csv"):
        lm = pd.read_csv(f"{BIO}/labels_multi.csv", dtype=str).fillna("")
        lm = lm[(lm.lang != "") & (lm.label != "")]
        for q, lang, l in zip(lm.qid, lm.lang, lm.label):
            lab.setdefault(q, {})[lang] = l
    if os.path.exists(f"{BIO}/titles.csv"):
        t0 = pd.read_csv(f"{BIO}/titles.csv", dtype=str).fillna("")
        for q, l in zip(t0.qid, t0.label):
            if l:
                lab.setdefault(q, {}).setdefault("en", l)
    wt = load_pages()
    print(f"  {len(wt):,} articles loaded · {len(cp):,} couples · {len(arts):,} people with an article",
          flush=True)
    kids = {}
    if os.path.exists(f"{BIO}/children.csv"):
        k = pd.read_csv(f"{BIO}/children.csv", dtype=str)
        kids = dict(zip(k.pair, pd.to_numeric(k.n, errors="coerce").fillna(0).astype(int)))

    def name(q, lang):
        d = lab.get(q, {})
        return d.get(lang) or d.get("en") or ""

    rows = []
    for r in cp.itertuples():
        aa, ab = arts.get(r.pid_a, {}), arts.get(r.pid_b, {})
        langs = sorted(set(aa) | set(ab), key=lambda l: ORDER.get(l, 99))
        chunks, srcs = [], []
        for lang in langs:
            for who, other, amap in ((r.pid_a, r.pid_b, aa), (r.pid_b, r.pid_a, ab)):
                t = amap.get(lang)
                if not t:
                    continue
                txt = wt.get((lang, t))
                if not txt:
                    continue
                got = passages(txt, name(other, lang), name(who, lang), lang)
                if got:
                    chunks.append(got)
                    srcs.append(f"https://{lang}.wikipedia.org/wiki/" + t.replace(" ", "_"))
            if sum(len(c) for c in chunks) > 3000:
                break
        desc = re.sub(r"\s+", " ", " ".join(chunks)).strip()
        if not desc:
            continue
        parts, seen_s = [], set()
        for sent in re.split(r"(?<=[.!?。！？])\s*", desc):
            k = sent.strip().lower()
            if k and k not in seen_s:
                seen_s.add(k)
                parts.append(sent.strip())
        desc = " ".join(parts)[:5000]
        la, lb = name(r.pid_a, "en"), name(r.pid_b, "en")

        def named(q):
            tk = tokens(name(q, "en"))
            if not tk:
                return False
            low = desc.lower()
            return (" ".join(tk).lower() in low) or (tk[0].lower() in low)
        # a surname-only hit can pull the wrong relative; one partner named explicitly is anchor enough,
        # and a non-Latin description is exempt because the name there is in another script entirely
        latin = bool(re.search(r"[A-Za-z]", desc))
        weak = int(latin and not (named(r.pid_a) or named(r.pid_b)))
        pair = f"{min(r.pid_a, r.pid_b)}|{max(r.pid_a, r.pid_b)}"
        rows.append({"pid_a": r.pid_a, "pid_b": r.pid_b, "name_a": la, "name_b": lb, "weak_name": weak,
                     "dob_a": r.dob_a, "dob_b": r.dob_b, "fullprec": r.fullprec, "married": r.sy,
                     "death_a": r.da, "death_b": r.db, "cause": r.cause,
                     "children": kids.get(pair, ""), "languages": ",".join(sorted(
                         {s.split("//")[1].split(".")[0] for s in srcs}, key=lambda l: ORDER.get(l, 99))),
                     "sources": " ".join(srcs[:6]), "n_chars": len(desc), "description": desc})
    out = pd.DataFrame(rows)
    out.to_csv(f"{BIO}/marriages.csv", index=False)
    over = out[(out.n_chars > 100) & (out.weak_name == 0)]
    print(f"  {len(out):,} couples with any description · {len(over):,} over 100 chars and name-confirmed "
          f"({int(out.weak_name.sum()):,} dropped as weak name matches)")
    print(f"    both dates full precision: {int(pd.to_numeric(over.fullprec).sum()):,}"
          f" · median {int(over.n_chars.median()) if len(over) else 0} chars")
    if len(over):
        langs = over.languages.str.split(",").explode().value_counts()
        print("    languages read: " + " · ".join(f"{k} {v:,}" for k, v in langs.head(12).items()))


if __name__ == "__main__":
    main()
