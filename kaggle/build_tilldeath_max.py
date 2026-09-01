"""build_tilldeath_max.py — the maximum 'till death do us part' corpus (operator 2026-08-31).

Same question, every couple the wiki can support:

  PRECISION.  A year-only birth date still pins the slow bodies — Pluto crosses ~11 degrees in a
  decade — and the finalized model is dominated by outer-planet terms. So partial-precision couples
  JOIN, their chart date imputed to the middle of the known window (YYYY-07-01 for a bare year,
  YYYY-MM-15 for a bare month); the fast-body terms attenuate toward zero for them on their own,
  which is exactly what noise should do in a phasor. The true precision rides in full.csv.

  DECADES.  The original harvest stopped at subjects born 1950. marriages3 extends it to 1990,
  and those younger couples enter ONLY when both deaths are recorded — an ended marriage, proved,
  never presumed (the born-before-1950 rule stays for the old population).

Person table (dob, precision, death, sex per QID) merged from marriages2 + marriages3 + the aq9c
slice cache; statements unioned from all three; end dates come from the slice cache alone. Labels:
the same four explicit-separation sources; contradictory pairs dropped, never coin-tossed.

-> ~/.artamatch-dev/tilldeath_max/{train.csv,full.csv,_train_ids.csv,labels_report.json}
"""
import glob, json, os, re, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/Studio/artamatch/kaggle"))
from build_separation import NATURAL, ARTIFICIAL, clean_date, qid
from build_tilldeath import BOUND, ukey, yr4

BIO = os.path.expanduser("~/.artamatch-dev/bio")
SLICES = os.path.expanduser("~/.artamatch-dev/aq9c/_dslices")
SEXCSV = os.path.expanduser("~/.artamatch-dev/aq9c/_sex.csv")
OUT = os.path.expanduser("~/.artamatch-dev/tilldeath_max")
MISSING = "0000-00-00"
MALE, FEM = "Q6581097", "Q6581072"


def impute(d):
    """chart date for a partial rendering; '' for unusable"""
    if not isinstance(d, str) or d == MISSING:
        return ""
    if d.endswith("-00-00"):
        return d[:4] + "-07-01"
    if d.endswith("-00"):
        return d[:8] + "15"
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    person, stmts = {}, []
    # ── the two decade harvests: statements on the subject; person facts accumulate
    for src in ("marriages2", "marriages3"):
        files = sorted(glob.glob(os.path.expanduser(f"~/.artamatch-dev/{src}/d*.csv")))
        nrows = 0
        for fn in files:
            d = pd.read_csv(fn, dtype=str)
            nrows += len(d)
            A, B = d.a.map(qid), d.b.map(qid)
            CS = d.cause.map(qid) if "cause" in d else ""
            dob = [clean_date(v, p) for v, p in zip(d.adob, d.aprec)]
            dy = yr4(d.adeath) if "adeath" in d else np.full(len(d), np.nan)
            SY = yr4(d.start) if "start" in d else np.full(len(d), np.nan)
            sx = d.asex.map(qid) if "asex" in d else ""
            for a, b, cs, dd, dv, sxx, sy in zip(A, B, CS, dob, dy, sx, SY):
                if not (a and b):
                    continue
                p = person.setdefault(a, {})
                if dd != MISSING and ("dob" not in p or len(dd.replace("-00", "")) >
                                      len(p["dob"].replace("-00", ""))):
                    p["dob"] = dd
                if np.isfinite(dv) and "death" not in p:
                    p["death"] = float(dv)
                if sxx and "sex" not in p:
                    p["sex"] = sxx
                stmts.append((a, b, cs, np.nan, sy))
                if np.isfinite(sy):
                    person.setdefault(a, {}).setdefault("starts", []).append(float(sy))
        print(f"  {src}: {len(files)} slices · {nrows:,} statements", flush=True)
    # ── the aq9c cache: both-side facts AND end dates
    for fn in sorted(glob.glob(f"{SLICES}/*.csv")):
        d = pd.read_csv(fn, dtype=str)
        if not {"a", "b", "adob", "bdob"} <= set(d.columns):
            continue
        for c in ("end", "adeath", "bdeath", "cause", "aprec", "bprec"):
            if c not in d.columns:
                d[c] = ""
        A, B = d.a.map(qid), d.b.map(qid)
        CS = d.cause.map(qid)
        E, DA, DB = yr4(d.end), yr4(d.adeath), yr4(d.bdeath)
        dobA = [clean_date(v, p) for v, p in zip(d.adob, d.aprec)]
        dobB = [clean_date(v, p) for v, p in zip(d.bdob, d.bprec)]
        for a, b, cs, e, da, db, xa, xb in zip(A, B, CS, E, DA, DB, dobA, dobB):
            if not (a and b):
                continue
            for pid, dd, dv in ((a, xa, da), (b, xb, db)):
                p = person.setdefault(pid, {})
                if dd != MISSING and ("dob" not in p or len(dd.replace("-00", "")) >
                                      len(p["dob"].replace("-00", ""))):
                    p["dob"] = dd
                if np.isfinite(dv) and "death" not in p:
                    p["death"] = float(dv)
            stmts.append((a, b, cs, e if np.isfinite(e) else np.nan, np.nan))
    sx = pd.read_csv(SEXCSV, dtype=str) if os.path.exists(SEXCSV) else None
    if sx is not None:
        col = [x for x in sx.columns if x != sx.columns[0]][0]
        for pid, s in zip(sx[sx.columns[0]].map(qid), sx[col].map(qid)):
            person.setdefault(pid, {}).setdefault("sex", s)
    print(f"  person table {len(person):,} · statements {len(stmts):,}", flush=True)

    # ── one row per unordered pair
    pairs = {}
    for a, b, cs, e, sy in stmts:
        k = ukey(a, b)
        r = pairs.setdefault(k, {"causes": set(), "ends": [], "sy": np.nan})
        if isinstance(cs, str) and cs.startswith("Q"):
            r["causes"].add(cs)
        if np.isfinite(e):
            r["ends"].append(e)
        if np.isfinite(sy) and not (np.isfinite(r["sy"]) and r["sy"] <= sy):
            r["sy"] = sy
    print(f"  distinct pairs {len(pairs):,}", flush=True)

    j = pd.read_csv(f"{BIO}/marriage_quality_binary.csv")
    jdiv = {ukey(a, b) for a, b, r in zip(j.pid_a, j.pid_b, j.reason) if r == "divorce"}
    # operator 2026-08-31: judged infidelity COUNTS as a separation-class positive — the per-row
    # flag from judged.csv (any infidelity the judge read) plus the primary-reason rows
    jj = pd.read_csv(f"{BIO}/judged.csv")
    jinf = {ukey(a, b) for a, b, f in zip(jj.pid_a, jj.pid_b, jj.infidelity)
            if str(f).lower() in ("true", "1", "1.0", "yes")}
    jinf |= {ukey(a, b) for a, b, r in zip(j.pid_a, j.pid_b, j.reason) if r == "infidelity"}
    t = pd.read_csv(f"{BIO}/marriages.csv")
    thit = {ukey(a, b) for a, b, d in zip(t.pid_a, t.pid_b, t.description.fillna(""))
            if BOUND.search(d)}

    def remarried(pid, this_start, other_death):
        """a NEW union while the other partner lived — both years known, never inferred.
        Operator 2026-08-31: remarrying counts as divorce. Conservative exactly as
        build_separation measured it; an explicit natural cause still overrides (the
        measured 22% failure mode is concurrent unions, and those carry natural causes)."""
        if not np.isfinite(this_start) or not np.isfinite(other_death):
            return False
        return any(t > this_start and t < other_death
                   for t in person.get(pid, {}).get("starts", ()))

    rows, dropped, skipped = [], 0, {"dob": 0, "sex": 0, "pop": 0}
    n_src = {"P1534": 0, "end-date": 0, "judge": 0, "text": 0, "infid": 0, "remarry": 0}
    for (a, b), r in pairs.items():
        pa, pb = person.get(a, {}), person.get(b, {})
        da_, db_ = pa.get("dob", MISSING), pb.get("dob", MISSING)
        if da_ == MISSING or db_ == MISSING:
            skipped["dob"] += 1; continue
        sa, sb = pa.get("sex"), pb.get("sex")
        if {sa, sb} != {MALE, FEM}:
            skipped["sex"] += 1; continue
        ya, yb = int(da_[:4]), int(db_[:4])
        dea, deb = pa.get("death", np.nan), pb.get("death", np.nan)
        ended = (ya < 1950 and yb < 1950) or (np.isfinite(dea) and np.isfinite(deb))
        if not ended:
            skipped["pop"] += 1; continue
        art = bool(r["causes"] & ARTIFICIAL)
        nat = bool(r["causes"] & NATURAL)
        if art and nat:
            dropped += 1; continue
        deaths = [v for v in (dea, deb) if np.isfinite(v)]
        endsep = any(deaths and all(abs(e - d) > 1 for d in deaths) and e < min(deaths)
                     for e in r["ends"])
        srcs = []
        if art: srcs.append("P1534")
        if endsep and not art and not nat: srcs.append("end-date")
        if (a, b) in jdiv or (b, a) in jdiv: srcs.append("judge")
        if (a, b) in thit or (b, a) in thit: srcs.append("text")
        if (a, b) in jinf or (b, a) in jinf: srcs.append("infid")
        sy = r["sy"]
        if remarried(a, sy, deb) or remarried(b, sy, dea):
            srcs.append("remarry")
        if nat and not art:
            # an explicit natural end silences the PROSE sources, never the judge's infidelity flag
            srcs = [s for s in srcs if s in ("P1534", "infid")]
        for s in srcs: n_src[s] += 1
        him, her = (a, b) if sa == MALE else (b, a)
        dh, dw = (da_, db_) if sa == MALE else (db_, da_)
        fullprec = int(("-00" not in dh) and ("-00" not in dw))
        # natural: an explicitly-recorded till-death ending — P1534 natural cause, or an end date
        # within a year of a known death. The strict target trains sep-vs-THIS.
        endnat = any(deaths and any(abs(e - d) <= 1 for d in deaths) for e in r["ends"])
        rows.append({"pid_a": him, "pid_b": her, "dob_a": impute(dh), "dob_b": impute(dw),
                     "true_dob_a": dh, "true_dob_b": dw, "fullprec": fullprec,
                     "y": 1 if srcs else 0, "src": "+".join(srcs),
                     "natural": int((nat or endnat) and not srcs)})
    d = pd.DataFrame(rows)
    print(f"\n  {len(d):,} couples ({int(d.fullprec.sum()):,} full-precision · "
          f"{len(d) - int(d.fullprec.sum()):,} imputed) · "
          f"{int(d.y.sum()):,} explicit separations ({d.y.mean():.2%})")
    print(f"  skipped: no dob {skipped['dob']:,} · not M+F {skipped['sex']:,} · "
          f"not provably ended {skipped['pop']:,} · contradictions {dropped}")
    print("  sources: " + " · ".join(f"{k} {v:,}" for k, v in n_src.items()), flush=True)

    d["start"] = MISSING
    d.rename(columns={"y": "ended_in_divorce"})[
        ["dob_a", "dob_b", "start", "ended_in_divorce"]].to_csv(f"{OUT}/train.csv", index=False)
    d[["pid_a", "pid_b"]].assign(y_rule=0, y_alive=0).to_csv(f"{OUT}/_train_ids.csv", index=False)
    d.to_csv(f"{OUT}/full.csv", index=False)
    te = d.head(20).copy(); te.insert(0, "id", [f"r{i:06d}" for i in range(len(te))])
    te[["id", "dob_a", "dob_b", "start"]].to_csv(f"{OUT}/test.csv", index=False)
    te.assign(ended_in_divorce=0)[["id", "ended_in_divorce"]].to_csv(f"{OUT}/solution.csv", index=False)
    json.dump({"n": len(d), "positives": int(d.y.sum()), "sources": n_src,
               "skipped": skipped, "contradictions": dropped},
              open(f"{OUT}/labels_report.json", "w"), indent=1)
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
