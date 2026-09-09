"""build_tilldeath.py — the 'till death do us part' corpus (operator 2026-08-31).

ONE QUESTION: did the marriage explicitly come apart, or did it hold until somebody died? Positive =
EXPLICIT separation only; every other marriage in the harvest is a negative, presumed till-death.
This inverts build_separation's population: that one kept only marriages whose ending is known
(12,446); this one keeps every full-precision couple on the wiki and lets the explicit separations
stand against all of them.

FOUR SOURCES OF AN EXPLICIT SEPARATION, strongest first, each counted and reported:
  P1534       an explicit end cause on the spouse statement (divorce, annulment, separation ...)
  end-date    an end date recorded MORE than a year from every known death — the union ended while
              both lived. Validated against explicit P1534 at 99.0% (build_separation.py); the
              remarriage rule was REJECTED there at 77.6% and is not used here either.
  judge       the 10k-corpus judge read the couple's description and tagged reason=divorce
  text        a couple-BOUND phrase in the description ("they divorced", "the marriage was
              annulled", "their separation" ...). Bound, because an unbound "divorce" is often a
              partner's OTHER marriage — measured on the judged rows: bare keyword 63.5% vs the
              judge, bound phrases ~71% on primary-reason (understated, since infidelity/abuse
              primaries usually divorced too).

A pair whose sources CONTRADICT (an explicit natural cause against an explicit artificial one)
is dropped, never resolved by a coin toss.

Population = every distinct couple, man first, with BOTH birth dates at day precision — the union
of the couples.csv harvest and the aq9c slice cache. Charts need a day; a year-precision date is a
decoration, not a measurement.

start is deliberately 0000-00-00 for every row: the model reads the two BIRTH charts only.

-> ~/.artamatch-dev/tilldeath/{train.csv,_train_ids.csv,labels_report.json}
"""
import glob, json, os, re, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from build_separation import NATURAL, ARTIFICIAL, clean_date, qid

BIO = os.path.expanduser("~/.artamatch-dev/bio")
SLICES = os.path.expanduser("~/.artamatch-dev/aq9c/_dslices")
SEXCSV = os.path.expanduser("~/.artamatch-dev/aq9c/_sex.csv")
OUT = os.path.expanduser("~/.artamatch-dev/tilldeath")
MISSING = "0000-00-00"
MALE, FEM = "Q6581097", "Q6581072"

BOUND = re.compile("|".join([
    r"\b(?:they|the couple|the pair|the marriage|the two|the union)\b[^.;]{0,60}?\b(?:divorc|separat|annull?|dissolv|split)",
    r"\btheir (?:divorce|separation|annulment|split)\b",
    r"\b(?:ended|ending|ended up|culminat\w+) in (?:divorce|separation|annulment)\b",
    r"\b(?:marriage|union) (?:was )?(?:dissolved|annulled)\b",
    r"\bdivorced? (?:him|her|each other)\b",
    r"\bfiled for divorce\b",
    r"\b(?:the )?divorce (?:was )?(?:final|finali[sz]ed|granted|became final)\b",
    r"\bwere (?:later )?divorced\b",
    r"\bgot divorced\b",
    r"\bthe couple (?:later )?(?:split|parted)\b",
    r"\b(?:they|the couple) (?:became |were |remained |grew )?estranged\b",
    r"\b(?:they|the couple) lived apart\b",
]), re.I)

ukey = lambda a, b: (a, b) if a < b else (b, a)
yr4 = lambda s: pd.to_numeric(pd.Series(s).astype(str).str.extract(r"^[+-]?(\d{4})")[0],
                              errors="coerce").to_numpy()


def main():
    os.makedirs(OUT, exist_ok=True)

    # ── 1. the base population: couples.csv, already deduped and man-first
    c = pd.read_csv(f"{BIO}/couples.csv", dtype=str)
    c = c[(c.fullprec == "1") & ~c.dob_a.str.contains("-00") & ~c.dob_b.str.contains("-00")]
    print(f"  couples.csv: {len(c):,} day-precision couples", flush=True)
    base = {}                        # ukey -> dict(pid_a, pid_b, dob_a, dob_b, da, db, causes=set())
    for r in c.itertuples(index=False):
        k = ukey(r.pid_a, r.pid_b)
        base[k] = {"pid_a": r.pid_a, "pid_b": r.pid_b, "dob_a": r.dob_a, "dob_b": r.dob_b,
                   "da": float(r.da) if r.da and r.da != "nan" else np.nan,
                   "db": float(r.db) if r.db and r.db != "nan" else np.nan,
                   "causes": set(), "ends": [], "src": set()}
        if isinstance(r.cause, str) and r.cause.startswith("Q"):
            base[k]["causes"].add(r.cause)

    # ── 2. the slice cache: end dates, more causes, more deaths, and some pairs of its own
    sx = {}
    if os.path.exists(SEXCSV):
        s = pd.read_csv(SEXCSV, dtype=str)
        col = [x for x in s.columns if x != s.columns[0]][0]
        sx = dict(zip(s[s.columns[0]].map(qid), s[col].map(qid)))
    newpairs, enddates, morecause = 0, 0, 0
    for fn in sorted(glob.glob(f"{SLICES}/*.csv")):
        d = pd.read_csv(fn, dtype=str)
        if not {"a", "b", "adob", "bdob"} <= set(d.columns):
            continue
        for col in ("end", "adeath", "bdeath", "cause", "aprec", "bprec"):
            if col not in d.columns:
                d[col] = ""
        m = (pd.to_numeric(d.aprec, errors="coerce") >= 11) & \
            (pd.to_numeric(d.bprec, errors="coerce") >= 11)
        d = d[m]
        if not len(d):
            continue
        A, B = d.a.map(qid), d.b.map(qid)
        CS = d.cause.map(qid)
        E, DA, DB = yr4(d.end), yr4(d.adeath), yr4(d.bdeath)
        dobA = [clean_date(v, p) for v, p in zip(d.adob, d.aprec)]
        dobB = [clean_date(v, p) for v, p in zip(d.bdob, d.bprec)]
        for a, b, cs, e, da, db, xa, xb in zip(A, B, CS, E, DA, DB, dobA, dobB):
            if not (a and b) or "-00" in xa or "-00" in xb:
                continue
            k = ukey(a, b)
            row = base.get(k)
            if row is None:
                # a pair the couples harvest missed: orient by sex, else skip
                if sx.get(a) == MALE and sx.get(b) == FEM:
                    row = {"pid_a": a, "pid_b": b, "dob_a": xa, "dob_b": xb}
                elif sx.get(a) == FEM and sx.get(b) == MALE:
                    row = {"pid_a": b, "pid_b": a, "dob_a": xb, "dob_b": xa}
                else:
                    continue
                row.update({"da": np.nan, "db": np.nan, "causes": set(), "ends": [], "src": set()})
                base[k] = row; newpairs += 1
            if cs.startswith("Q"):
                row["causes"].add(cs); morecause += 1
            if np.isfinite(e):
                row["ends"].append(e); enddates += 1
            for key, v in (("da", da), ("db", db)):
                if np.isfinite(v) and not np.isfinite(row[key]):
                    row[key] = v
    print(f"  slices: +{newpairs:,} new pairs · {enddates:,} end dates · "
          f"{morecause:,} cause statements", flush=True)

    # ── 3. the judge and the text, joined by pid pair (NEVER by row index)
    j = pd.read_csv(f"{BIO}/marriage_quality_binary.csv")
    jdiv = {ukey(a, b) for a, b, r in zip(j.pid_a, j.pid_b, j.reason) if r == "divorce"}
    t = pd.read_csv(f"{BIO}/marriages.csv")
    thit = {ukey(a, b) for a, b, d in zip(t.pid_a, t.pid_b, t.description.fillna(""))
            if BOUND.search(d)}
    print(f"  judge reason=divorce: {len(jdiv):,} pairs · bound text hits: {len(thit):,} pairs",
          flush=True)

    # ── 4. label every pair
    rows, dropped = [], 0
    n_src = {"P1534": 0, "end-date": 0, "judge": 0, "text": 0}
    for k, r in base.items():
        art = bool(r["causes"] & ARTIFICIAL)
        nat = bool(r["causes"] & NATURAL)
        if art and nat:
            dropped += 1; continue                       # the two items disagree: drop
        # end-vs-death, exactly build_separation's validated form: an end more than a year
        # from EVERY known death, with at least one death known
        endsep = False
        deaths = [v for v in (r["da"], r["db"]) if np.isfinite(v)]
        for e in r["ends"]:
            if deaths and all(abs(e - d) > 1 for d in deaths) and e < min(deaths):
                endsep = True
        srcs = []
        if art: srcs.append("P1534")
        if endsep and not art and not nat: srcs.append("end-date")
        if k in jdiv: srcs.append("judge")
        if k in thit: srcs.append("text")
        if nat and not art:
            srcs = [s for s in srcs if s in ("P1534",)]   # explicit natural beats inference and prose
        y = 1 if srcs else 0
        for s in srcs: n_src[s] += 1
        rows.append({"pid_a": r["pid_a"], "pid_b": r["pid_b"], "dob_a": r["dob_a"],
                     "dob_b": r["dob_b"], "y": y, "src": "+".join(srcs)})
    d = pd.DataFrame(rows)
    print(f"\n  {len(d):,} couples · {int(d.y.sum()):,} explicit separations "
          f"({d.y.mean():.2%}) · {dropped} contradictory pairs dropped")
    print("  by source (a pair can have several): " +
          " · ".join(f"{k} {v:,}" for k, v in n_src.items()), flush=True)

    d["start"] = MISSING
    d.rename(columns={"y": "ended_in_divorce"})[
        ["dob_a", "dob_b", "start", "ended_in_divorce"]].to_csv(f"{OUT}/train.csv", index=False)
    d[["pid_a", "pid_b"]].assign(y_rule=0, y_alive=0).to_csv(f"{OUT}/_train_ids.csv", index=False)
    d.to_csv(f"{OUT}/full.csv", index=False)
    te = d.head(20).copy(); te.insert(0, "id", [f"r{i:06d}" for i in range(len(te))])
    te[["id", "dob_a", "dob_b", "start"]].to_csv(f"{OUT}/test.csv", index=False)
    te.assign(ended_in_divorce=0)[["id", "ended_in_divorce"]].to_csv(f"{OUT}/solution.csv", index=False)
    json.dump({"n": len(d), "positives": int(d.y.sum()), "sources": n_src,
               "contradictions_dropped": dropped},
              open(f"{OUT}/labels_report.json", "w"), indent=1)
    print(f"  wrote {OUT}/train.csv + _train_ids.csv + full.csv")


if __name__ == "__main__":
    main()
