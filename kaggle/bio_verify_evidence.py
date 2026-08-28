"""bio_verify_evidence.py — does every judgement's evidence actually come from its own description?

One judge, auditing its own work, found a quote attributed to a couple that belonged to a different
entry entirely. That is the failure mode worth checking across all of them: an evidence string that
cannot be traced back to the description is a judgement resting on something invented.

The rubric allows close paraphrase, so this measures OVERLAP rather than demanding a verbatim substring:
the share of the evidence's content words (ignoring stopwords, and ignoring the two partners' own names,
which the judge may add for clarity) that appear in the description. Rows below the floor are reported,
and with --flag they are written to unsupported.csv for exclusion.
"""
import glob, json, os, re, sys
import pandas as pd

BIO = os.path.expanduser("~/.artamatch-dev/bio")
FLOOR = float(os.environ.get("AQ_FLOOR", "0.5"))
STOP = set("""a an the and or but if of to in on at by for with from as is was were be been being they
their them he she his her it its this that these those had have has not no than then when while who whom
which what where after before during until about into over under again further once here there all any
both each few more most other some such only own same so too very can will just should now""".split())


def words(s):
    return [w for w in re.findall(r"[\w'-]+", str(s).lower()) if w not in STOP and len(w) > 2]


def main():
    idx = pd.read_csv(f"{BIO}/index.csv", dtype=str).set_index("rid")
    rows = []
    for f in sorted(glob.glob(f"{BIO}/labels/batch_*.json")):
        try:
            arr = json.load(open(f))
        except Exception:
            continue
        for o in arr:
            rid = o.get("id")
            if rid not in idx.index:
                continue
            desc = str(idx.at[rid, "description"]).lower()
            names = set(words(idx.at[rid, "name_a"])) | set(words(idx.at[rid, "name_b"]))
            ev = [w for w in words(o.get("evidence", "")) if w not in names]
            if not ev:
                rows.append((rid, o.get("label"), 0.0, os.path.basename(f)))
                continue
            hit = sum(1 for w in ev if w in desc)
            rows.append((rid, o.get("label"), hit / len(ev), os.path.basename(f)))
    d = pd.DataFrame(rows, columns=["rid", "label", "support", "batch"])
    bad = d[d.support < FLOOR]
    print(f"  {len(d):,} judgements checked against their own description")
    print(f"    median evidence support {d.support.median():.0%} · "
          f"below {FLOOR:.0%}: {len(bad):,} ({len(bad)/max(1,len(d)):.2%})")
    if len(bad):
        print("    worst offenders by batch: " + " · ".join(
            f"{k} {v}" for k, v in bad.batch.value_counts().head(5).items()))
        print("    by label: " + " · ".join(f"{k} {v}" for k, v in bad.label.value_counts().items()))
    if "--flag" in sys.argv:
        bad.to_csv(f"{BIO}/unsupported.csv", index=False)
        print(f"    wrote {BIO}/unsupported.csv for exclusion")


if __name__ == "__main__":
    main()
