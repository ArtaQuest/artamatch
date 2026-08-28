"""bio_extract.py — pull the MARRIAGE out of a Wikipedia article, in any of the 21 languages.

Traps this has to survive, all found on real couples:
  · a married surname is shared with the article's subject ("Robert Kalley" x "Sarah Poulton Kalley"),
    so a surname key matches every paragraph about the subject;
  · the last token of a label is not always a surname ("Princess Regina Kanyange of Burundi");
  · a name is written differently in every script, so the ARMENIAN article has to be searched for
    "Աննա", not "Anna" — the per-language Wikidata label is what makes that work;
  · Japanese, Chinese and Korean end sentences with their own stops and put no spaces between words.
"""
import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bio_langs import REL, HEAD, CJK

TITLES = re.compile(r"^(sir|dame|lady|lord|princess|prince|king|queen|count|countess|duke|duchess|"
                    r"baron|baroness|st|saint|dr|rev|hon|mrs|mr|ms|miss|the)\.?$", re.I)
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'À-˿Ѐ-ӿ԰-֏֐-׿؀-ۿ])")
SENT_CJK = re.compile(r"(?<=[。！？])")
QUOTES = "'''"
_cache = {}


def rel_re(lang):
    if lang not in _cache:
        _cache[lang] = re.compile(REL.get(lang, REL["en"]), re.I)
    return _cache[lang]


def head_re(lang):
    k = "h:" + lang
    if k not in _cache:
        _cache[k] = re.compile(r"^\s*(" + HEAD.get(lang, HEAD["en"]) + r")\s*$", re.I)
    return _cache[k]


def strip_wiki(t):
    t = re.sub(r"<ref[^>]*/>", " ", t)
    t = re.sub(r"<ref.*?</ref>", " ", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"\{\|.*?\|\}", " ", t, flags=re.S)
    for _ in range(6):
        t2 = re.sub(r"\{\{[^{}]*\}\}", " ", t)
        if t2 == t:
            break
        t = t2
    t = re.sub(r"\[\[(?:File|Image|Category|Fichier|Datei|Archivo|Categoria|Kategorie|Catégorie|"
               r"Файл|Категория|ファイル|分類|קטגוריה|Կատեգորիա):[^\]]*\]\]", " ", t, flags=re.I)
    t = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = t.replace(QUOTES, "").replace("''", "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"^[*#:;]+", "", t, flags=re.M)
    t = t.replace("&nbsp;", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return t


def tokens(label):
    if not isinstance(label, str) or not label.strip():
        return []
    lab = re.sub(r"\s*\(.*?\)", "", label).strip()
    lab = re.split(r"\bof\b", lab)[0].strip()
    parts = [p.strip(",.") for p in lab.split()]
    return [p for p in parts if len(p) > 2 and not TITLES.match(p) and not re.fullmatch(r"[IVXLC]+", p)]


def keyset(partner_label, subject_label, lang):
    """(full, surname|None, first|None). For CJK there are no spaces, so the whole label is the key."""
    if not isinstance(partner_label, str) or not partner_label.strip():
        return None, None, None
    if lang in CJK or not re.search(r"\s", partner_label.strip()):
        lab = re.sub(r"\s*\(.*?\)", "", partner_label).strip()
        if len(lab) < 2:
            return None, None, None
        return re.compile(re.escape(lab)), None, None
    # A REGNAL name has no surname and its given names repeat down the family: "John George III" and
    # "John George IV" share every token, so a first-name key silently pulls the brother's marriage into
    # this one's description (caught by a judge on exactly that pair). For these, ONLY the full name
    # including the numeral may match.
    plain = re.sub(r"\s*\(.*?\)", "", partner_label).strip()
    num = re.search(r"\b([IVXLC]{1,6})\b", plain)
    if num:
        stem = re.split(r"\bof\b|,", plain)[0].strip()
        if stem:
            return re.compile(re.escape(stem), re.I), None, None
    me, you = tokens(partner_label), tokens(subject_label)
    if not me:
        return None, None, None
    sur = me[-1] if len(me) >= 2 else None
    if sur and you and sur.lower() == you[-1].lower():
        sur = None
    return (re.compile(re.escape(" ".join(me)), re.I),
            re.compile(r"(?<!\w)" + re.escape(sur) + r"(?!\w)", re.I) if sur else None,
            re.compile(r"(?<!\w)" + re.escape(me[0]) + r"(?!\w)", re.I))


def sections(txt):
    blocks, cur, cur_h = [], [], ""
    for line in txt.split("\n"):
        h = re.match(r"^\s*==+\s*(.*?)\s*==+\s*$", line)
        if h:
            blocks.append((cur_h, "\n".join(cur)))
            cur_h, cur = h.group(1), []
        else:
            cur.append(line)
    blocks.append((cur_h, "\n".join(cur)))
    return blocks


def passages(wikitext, partner_label, subject_label, lang="en", cap=2600):
    """The sentences that speak about this marriage, in this language."""
    if not wikitext:
        return ""
    kf, ks, kfi = keyset(partner_label, subject_label, lang)
    if kf is None:
        return ""
    rel, head = rel_re(lang), head_re(lang)
    splitter = SENT_CJK if lang in CJK else SENT
    minlen = 8 if lang in CJK else 25
    out, seen = [], set()
    for h, body in sections(strip_wiki(wikitext)):
        if not body.strip():
            continue
        life = bool(head.match(h.strip()))
        for para in body.split("\n"):
            p = para.strip()
            if len(p) < (15 if lang in CJK else 40):
                continue
            sents = [x for x in splitter.split(p) if x and x.strip()]
            for si, sent in enumerate(sents):
                if len(sent) < minlen:
                    continue
                r = bool(rel.search(sent))
                named = bool(kf.search(sent)) or bool(ks and ks.search(sent)) or bool(kfi and kfi.search(sent))
                take = ((kf.search(sent) and r) or (ks and ks.search(sent) and r)
                        or (life and r and named) or (kf.search(sent) and life))
                if not take:
                    continue
                chunk = sent.strip()
                nxt = sents[si + 1].strip() if si + 1 < len(sents) else ""
                if nxt and rel.search(nxt) and len(nxt) > minlen:
                    chunk += " " + nxt
                if chunk not in seen:
                    seen.add(chunk)
                    out.append(chunk)
    return " ".join(out)[:cap]
