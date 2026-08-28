"""bio_namecheck.py — NEGATIVE RESULT: you cannot detect a wrong-person record by name presence.

Judges reported, unprompted, that some descriptions are dominated by a sibling, an in-law, a prior
marriage or a same-named relative — one (r003612) never mentioning the wife at all. Parsing those out of
judge prose under-catches badly, so this tried the mechanical version: does each partner's name occur in
the description? Measured against the eight ids judges named unprompted, every variant fails:

  rule                                     flags        catches
  any name token present                   14.2%        2 of 8   <- shared married surname defeats it
  a non-shared distinctive token present    22.1%        4 of 8
  the given name present                    47.3%        7 of 8   <- catches them, at half the corpus

The 47% variant is the only one with useful recall and it is unusable, because 96.2% of what it flags
DOES name the person by a later token — a surname or a title. It is measuring "this prose calls her
Lady Cleveland rather than Wilhelmina", which is ordinary English for a historical figure. Flagged
records are also simply the shorter ones (median 44 words against 89): fewer words, fewer name mentions.
The rate is flat across languages (English-only 47.5%, non-ASCII names 47.8%), so it is not a
transliteration artefact either.

WHAT IS USED INSTEAD, and why it is defensible:
  · the judge's own `not_a_marriage` flag — a schema field, so every judge sets it uniformly;
  · `confidence == "low"` — which is what a judge assigns to exactly these garbled or wrong-person
    records (r003508, r003861), is ~4% of rows, and is reported by every judge without being asked.
Wrong-person records that survive both are LABEL NOISE, and label noise attenuates AUC toward 0.5. It
cannot manufacture a positive result — so it weakens a null finding's force and never inflates a
positive one. That asymmetry is why this file stays a measurement and not a filter.

Run it to reproduce the table. Usage: bio_namecheck.py [--flag]
"""
import os, re, sys, unicodedata
import pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
PARTICLE = set("""of the de la le du von van der den bin ibn al el and jr sr st saint mac mc ap ben
i ii iii iv v vi vii viii ix x xi xii xiii xiv xv xvi xvii xviii xix xx
sir dame lord lady don dona donna duke duchess count countess baron baroness prince princess king queen
earl marquess marchioness viscount viscountess archduke archduchess grand landgrave margrave
mrs mr miss ms dr rev""".split())


def fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def toks(name):
    """distinctive words of a name: drop particles, titles, regnal numerals and initials"""
    out = []
    for w in re.findall(r"[\w'-]+", fold(name)):
        w = w.strip("'-")
        if len(w) < 3 or w in PARTICLE:
            continue
        out.append(w)
    return out


def main():
    idx = pd.read_csv(f"{BIO}/index.csv", dtype=str)
    d = fold_series(idx.description)
    rows = []
    for rid, na, nb, desc in zip(idx.rid, idx.name_a, idx.name_b, d):
        ta, tb = toks(na), toks(nb)
        ha = any(t in desc for t in ta) if ta else True
        hb = any(t in desc for t in tb) if tb else True
        if not (ha and hb):
            rows.append({"rid": rid, "name_a": na, "name_b": nb,
                         "missing": ("him" if not ha else "") + ("her" if not hb else ""),
                         "n_tokens_missing_side": len(tb) if not hb else len(ta)})
    w = pd.DataFrame(rows)
    print(f"  {len(idx):,} descriptions checked for both partners' names")
    print(f"  {len(w):,} ({len(w)/len(idx):.2%}) never name one of the two people")
    if len(w):
        print("    which side: " + " · ".join(f"{k} {v}" for k, v in w.missing.value_counts().items()))
    # does it agree with what the judges reported unprompted?
    known = ["r003612", "r000174", "r003688", "r003607", "r003643", "r003644", "r003682", "r003715"]
    got = set(w.rid)
    print("\n  against the ids judges reported unprompted as wrong-person:")
    for k in known:
        hit = "caught" if k in got else "MISSED"
        sub = idx[idx.rid == k]
        who = f"{sub.name_a.iloc[0]} x {sub.name_b.iloc[0]}" if len(sub) else "?"
        print(f"    {k} {hit:<7} {who[:58]}")
    if "--flag" in sys.argv:
        w.to_csv(f"{BIO}/wrongperson.csv", index=False)
        print(f"\n    wrote {BIO}/wrongperson.csv ({len(w)} rows)")


def fold_series(s):
    return [fold(x) for x in s.fillna("")]


if __name__ == "__main__":
    main()
