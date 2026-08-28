"""bio_verify2.py — does every BINARY judgement's evidence actually come from its own description?

Two independent checks, because they catch different failures:

  1. OVERLAP (paraphrase-tolerant). The share of the evidence's content words that appear in the
     couple's own description, ignoring stopwords and the partners' own names. A judgement whose
     evidence words are mostly absent from the text is resting on something the record does not say.
     This is what caught a quote belonging to a different couple entirely.

  2. VERBATIM QUOTED FRAGMENTS (strict). Where the judge wrapped a fragment in quotation marks it is
     asserting the record says exactly that, so it must appear exactly. THREE traps, every one of which
     made an earlier version of this check report false positives:
       · a possessive or contraction apostrophe is not a quote delimiter ("Mary's" / "didn't")
       · an ellipsis inside a quote joins two fragments — each side is checked separately
       · an escaped quote in the JSON arrives as \\" and a naive capture swallows the backslash into
         the fragment, so a quote that IS present fails to match. Escapes are stripped first.

  3. RECORD-INADEQUACY REPORTS (a filter, not an error). The rubric instructs a judge to say so in the
     evidence when the description is about the wrong person or says nothing about this pair. Such
     evidence is meta-commentary — "the description never mentions her", "no divorce recorded" — and
     CANNOT overlap the description, by definition. The first version of this check scored those as
     fabrications and would have dropped legitimate work. They are exempted from check 1 and reported
     separately, because a description that is about somebody else must leave the corpus anyway — for
     being the wrong record, not for having bad evidence.

Rows failing check 1 or 2, plus wrong-person reports from check 3, are written to unverified_quotes2.csv
with --flag, which bio_corpus2.py reads and excludes. Usage: bio_verify2.py [--flag]
"""
import glob, json, os, re, sys
import pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
FLOOR = float(os.environ.get("AQ_FLOOR", "0.5"))
STOP = set("""a an the and or but if of to in on at by for with from as is was were be been being they
their them he she his her it its this that these those had have has not no than then when while who whom
which what where after before during until about into over under again further once here there all any
both each few more most other some such only own same so too very can will just should now would could""".split())
# a quote delimiter, NOT an apostrophe inside a word: straight/curly double quotes, or a single quote
# that is not flanked by word characters on both sides
META = set("""description record records prose entry article text passage says state states stated
mentions mention mentioned narrate narrates narrated narration recorded nothing never neither none
otherwise itself themselves himself herself given gives giving beyond apart aside regarding concerning
listing genealogical structured field fields flag flagged marked marks indicates indicating suggests
implies implied appears seems seemingly presumably apparently unclear ambiguous garbled confusing
entirely instead rather actually merely simply solely purely only wholly partly largely mostly
different another other same wrong correct incorrect
troubled trouble untroubled conflict conflicts affection devotion divorce divorced separation separated
infidelity abuse coercion adversity collaboration thin sparse dry bare""".split())
WRONGREC = re.compile(
    r"(never|not|n't|no)\s+(?:\w+\s+){0,3}(mention|mentions|mentioned|name|names|named|appear|appears|"
    r"refer|refers|discuss|discusses|state|states|stated)"
    r"|about (?:a )?different|different (?:wife|husband|spouse|person|man|woman|marriage)"
    r"|wrong (?:person|spouse|wife|husband)"
    r"|entirely about|barely appears|does not appear|is not about|nothing about (?:this|the) (?:pair|couple|marriage)",
    re.I)
QUOTED = re.compile(r'"([^"]{8,})"|“([^”]{8,})”|(?<!\w)\'([^\']{8,})\'(?!\w)')
ELLIPSIS = re.compile(r'\s*(?:\.\.\.|…)\s*')


def words(s):
    return [w for w in re.findall(r"[\w'-]+", str(s).lower()) if w not in STOP and len(w) > 2]


def norm(s):
    """collapse whitespace, drop JSON escapes, unify quote/dash glyphs — a real match must not be
    lost to typography or to a stray backslash the escape survived as"""
    s = str(s).replace("\\\"", "\"").replace("\\'", "'").replace("\\\\", "")
    s = s.lower().replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    return re.sub(r"\s+", " ", s).strip()


def main():
    idx = pd.read_csv(f"{BIO}/index.csv", dtype=str).set_index("rid")
    rows = []
    for f in sorted(glob.glob(f"{BIO}/labels2/batch_*.json")):
        try:
            arr = json.load(open(f))
        except Exception:
            continue
        if len(arr) < 40:
            continue
        for o in arr:
            rid = o.get("id")
            if rid not in idx.index or not isinstance(o.get("good"), bool):
                continue
            desc_raw = str(idx.at[rid, "description"])
            desc, dl = norm(desc_raw), desc_raw.lower()
            names = set(words(idx.at[rid, "name_a"])) | set(words(idx.at[rid, "name_b"]))
            ev_raw = o.get("evidence", "")
            # a judge's meta-commentary about the record is not a claim about its contents
            ev = [w for w in words(ev_raw) if w not in names and w not in META]
            support = (sum(1 for w in ev if w in dl) / len(ev)) if ev else 1.0
            wrong_rec = bool(WRONGREC.search(str(ev_raw)))
            nq = bad_q = 0
            for m in QUOTED.finditer(norm(ev_raw)):
                frag = next(g for g in m.groups() if g)
                for part in ELLIPSIS.split(frag):
                    part = norm(part).strip(" ,.;:")
                    if len(part) < 8:
                        continue
                    nq += 1
                    if part not in desc:
                        bad_q += 1
            rows.append((rid, int(o["good"]), o.get("reason", ""), round(support, 3),
                         nq, bad_q, int(wrong_rec), os.path.basename(f)))
    d = pd.DataFrame(rows, columns=["rid", "good", "reason", "support", "n_quoted", "n_bad_quoted",
                                    "wrong_record", "batch"])
    if not len(d):
        print("  nothing to check yet")
        return
    print(f"  {len(d):,} binary judgements checked against their own description")
    print(f"  1. OVERLAP  median support {d.support.median():.0%}")
    low = d[d.support < FLOOR]
    print(f"     below {FLOOR:.0%}: {len(low):,} ({len(low)/len(d):.2%})"
          + (f" · by verdict: good {int(low.good.sum())} / bad {int((1-low.good).sum())}" if len(low) else ""))
    print(f"  2. VERBATIM {int(d.n_quoted.sum()):,} explicitly quoted fragments in "
          f"{int((d.n_quoted > 0).sum()):,} judgements")
    vq = d[d.n_bad_quoted > 0]
    print(f"     not found verbatim: {len(vq):,} judgements "
          f"({len(vq)/max(1,(d.n_quoted>0).sum()):.2%} of those that quote)")
    print(f"  3. RECORD-INADEQUACY the judge reports the description is about the wrong person or is "
          f"silent on this pair: {int(d.wrong_record.sum()):,} ({d.wrong_record.mean():.2%})")
    bad = d[(d.support < FLOOR) | (d.n_bad_quoted > 0) | (d.wrong_record == 1)]
    print(f"  UNION to exclude: {len(bad):,} ({len(bad)/len(d):.2%})")
    if len(bad):
        print("     by batch: " + " · ".join(f"{k[6:10]} {v}" for k, v in bad.batch.value_counts().head(6).items()))
        print("     by reason: " + " · ".join(f"{k} {v}" for k, v in bad.reason.value_counts().head(6).items()))
    if "--flag" in sys.argv:
        bad.to_csv(f"{BIO}/unverified_quotes2.csv", index=False)
        print(f"     wrote {BIO}/unverified_quotes2.csv ({len(bad)} rows) for exclusion")


if __name__ == "__main__":
    main()
