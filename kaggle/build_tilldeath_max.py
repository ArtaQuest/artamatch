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
# AQ_TARGET picks what y means, and each target gets its own directory so switching never
# overwrites another target's charts:
#   children  y=1 the record lists children for the couple      (default)
#   p1534     y=1 an explicit P1534 cause says they ended it
TARGET = os.environ.get("AQ_TARGET", "children")
AQ_FULLPREC = os.environ.get("AQ_FULLPREC", "1") == "1"
# AQ_OUT overrides the directory — a corpus rebuilt with recovered dates lands BESIDE the current
# one, never over it: the standing corpus still backs the live model's export chain, and a rebuild
# invalidates phases.npz for whatever sits in its directory.
OUT = os.path.expanduser(os.environ.get("AQ_OUT") or
                         {"children": "~/.artamatch-dev/tilldeath_max",
                          "p1534": "~/.artamatch-dev/p1534",
                          # SUCCESS (operator 2026-09-03): the marriage LASTED and had children.
                          # A couple that split counts against, whatever their children.
                          "success": "~/.artamatch-dev/success",          # every separation signal
                          "success_strict": "~/.artamatch-dev/success_strict",   # strong signals only
                          "prosper2": "~/.artamatch-dev/prosper2"}[TARGET])     # lasted + >= 2 children
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
    jabuse = {ukey(a, b) for a, b, f in zip(jj.pid_a, jj.pid_b, jj.abuse)
              if str(f).lower() in ("true", "1", "1.0", "yes")}
    jabuse |= {ukey(a, b) for a, b, r in zip(j.pid_a, j.pid_b, j.reason) if r == "abuse"}
    # children per couple, from the count-verified harvest
    kids = {}
    _kf = f"{BIO}/children.csv"
    if os.path.exists(_kf):
        _k = pd.read_csv(_kf)
        for _pr, _n in zip(_k.pair, _k.n):
            if isinstance(_pr, str) and "|" in _pr:
                _x, _y = _pr.split("|")[:2]
                kids[ukey(_x, _y)] = int(_n)
    print(f"  children.csv: {len(kids):,} pairs · "
          f"{sum(1 for v in kids.values() if v == 0):,} with none recorded", flush=True)
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

    # ── recovered exact dates (WikiTree via P2949), applied ONLY where the year agrees with
    # Wikidata's own year — a mismatched year is a contradiction, not a recovery, and the person
    # keeps the imprecise date (and is excluded) rather than gaining a wrong precise one.
    n_wt = 0
    for WT in (os.path.expanduser("~/.artamatch-dev/wt_dates.csv"),
               os.path.expanduser("~/.artamatch-dev/wp_dates.csv")):   # WikiTree, then enwiki infoboxes
        if not os.path.exists(WT): continue
        for _, w in pd.read_csv(WT, dtype=str).iterrows():
            pid, wd = w["pid"], w["dob"]
            if not (isinstance(wd, str) and len(wd) == 10 and "-00" not in wd):
                continue
            p = person.get(pid)
            if p and "dob" in p and "-00" in p["dob"] and p["dob"][:4] == wd[:4]:
                p["dob"] = wd; n_wt += 1
        print(f"  recovered exact birth dates so far: {n_wt:,} (through {os.path.basename(WT)})", flush=True)
    # ── the facts our own harvest never fetched (wd_fill.py): filled ONLY where absent. A date
    # already held (any precision) is never replaced from here — that is WikiTree's job above, and
    # a Wikidata date is what the held one already came from.
    WF = os.path.expanduser("~/.artamatch-dev/wd_facts.csv")
    n_fill = {"dob": 0, "sex": 0, "death": 0}
    if os.path.exists(WF):
        for _, w in pd.read_csv(WF, dtype=str).fillna("").iterrows():
            p = person.setdefault(w["pid"], {})
            if w["dob"] and w["prec"] and "dob" not in p:
                p["dob"] = clean_date(w["dob"], w["prec"]); n_fill["dob"] += 1
            if w["sex"] and "sex" not in p:
                p["sex"] = w["sex"]; n_fill["sex"] += 1
            if w["death"] and "death" not in p:
                try: p["death"] = float(w["death"]); n_fill["death"] += 1
                except ValueError: pass
        print(f"  filled from {WF}: " + " · ".join(f"{k} {v:,}" for k, v in n_fill.items()), flush=True)
    prec_excluded = []; dob_missing = set(); nokids_pairs = []
    rows, dropped, skipped = [], 0, {"imputed": 0, "dob": 0, "sex": 0, "no_evidence": 0, "shady_only": 0,
                                    "no_children_row": 0, "self": 0, "died_before_born": 0,
                                    "gap60": 0}
    n_src = {"childless": 0, "P1534": 0}
    for (a, b), r in pairs.items():
        pa, pb = person.get(a, {}), person.get(b, {})
        da_, db_ = pa.get("dob", MISSING), pb.get("dob", MISSING)
        if da_ == MISSING or db_ == MISSING:
            skipped["dob"] += 1
            # who is missing a date entirely — the decade harvests fetched dates for the SUBJECT
            # spouse only, so a partner seen nowhere else has none, whether or not Wikidata has one
            for pid, dd in ((a, da_), (b, db_)):
                if dd == MISSING: dob_missing.add(pid)
            continue
        sa, sb = pa.get("sex"), pb.get("sex")
        if {sa, sb} != {MALE, FEM}:
            skipped["sex"] += 1; continue
        ya, yb = int(da_[:4]), int(db_[:4])
        dea, deb = pa.get("death", np.nan), pb.get("death", np.nan)
        # ── WHICH MARRIAGES HAVE AN OUTCOME AT ALL (operator 2026-09-01)
        # The old rule admitted any couple both born before 1950, which quietly labelled ONGOING
        # marriages as "till death": two people born in 1945, both alive, still married, counted as
        # a negative. That was 44,493 rows — 27% of every negative in the corpus, and about 90% of
        # the couples born in the 1910s to 1940s.
        #
        # A marriage has a known outcome only if:
        #   it came apart          -> the separation evidence below says so, and it is a positive
        #   somebody died          -> it ended at that death, and it is a negative
        #   both are certainly dead -> born early enough that no one could still be living
        # Anything else is a marriage still running, or one whose end nobody recorded, and it is
        # excluded rather than guessed at. Absence of a death date is NOT evidence of life for a
        # person born in 1650, so CERTAIN_DEAD carries that case on the calendar instead.
        CERTAIN_DEAD = 1905                      # born by then and you cannot be alive in 2026
        any_death = np.isfinite(dea) or np.isfinite(deb)
        certainly_dead = ya <= CERTAIN_DEAD and yb <= CERTAIN_DEAD
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
        # ── THE TARGET: DID THIS COUPLE HAVE CHILDREN? (operator 2026-09-01)
        # The divorce, infidelity and abuse classes are dropped — each was a few hundred to a few
        # thousand rows against tens of thousands, and the per-source slice showed the model read
        # them very unevenly. What is left is one balanced question with one answer per couple:
        #
        #   y = 1   children are recorded for the pair        (prospered, in the operator's framing)
        #   y = 0   none are                                   (did not)
        #
        # THE POPULATION IS STILL FINISHED MARRIAGES ONLY — a recorded death, or an explicit end
        # cause. A marriage still running has not had its children yet, and calling it childless
        # would be a statement about its age rather than about the couple.
        #
        # SAID ONCE, PLAINLY, AND IT IS THE THING TO KNOW ABOUT THIS TARGET: Wikidata lists children
        # mainly when a notable person descends from the couple. So `no children recorded` blends
        # genuine childlessness with thin documentation, and a model that predicts it is reading both.
        # That is the operator's chosen target; it is built as asked and reported with this attached.
        nkid = kids.get((a, b), kids.get((b, a)))
        if TARGET == "children":
            if nkid is None:
                skipped["no_children_row"] += 1
                nokids_pairs.append((a, b, int(art or nat or any_death)))
                continue
            if not (art or nat or any_death):
                skipped["no_evidence"] += 1; continue    # unfinished: the count is not final
            srcs = [] if nkid >= 1 else ["childless"]
        elif TARGET in ("success", "success_strict", "prosper2"):
            # THE SUCCESS TARGET (operator 2026-09-03): "flip the labels if couples split —
            # separation discounts having children; maximise the quality (test of time) and the
            # quantity (children) of the relationship."
            #   y = 1  the marriage lasted (no separation evidence) AND the record lists children
            #          (>= 1, or >= 2 for prosper2)
            #   y = 0  it split (any separation evidence — strict: P1534, an end date before either
            #          death, or remarriage while the spouse lived), or it lasted childless
            # Population unchanged: FINISHED marriages with a children row. `srcs` at this point
            # holds the separation evidence exactly as the divorce targets computed it.
            if nkid is None:
                skipped["no_children_row"] += 1
                nokids_pairs.append((a, b, int(art or nat or any_death)))
                continue
            if not (art or nat or any_death or srcs):
                skipped["no_evidence"] += 1; continue
            STRONG = {"P1534", "end-date", "remarry"}
            sep = [x for x in srcs if (x in STRONG if TARGET == "success_strict" else True)]
            need = 2 if TARGET == "prosper2" else 1
            srcs = (["split:" + "+".join(sep)] if sep else []) + (["childless" if nkid == 0 else f"few:{nkid}"] if nkid < need else [])
        else:
            # P1534 ONLY: a recorded cause saying the two of them ended it, against marriages that
            # ended in a recorded death. Rows whose only sign of trouble is weaker than P1534 are
            # excluded — calling them till-death would be the same mistake in the other direction.
            nkid = -1 if nkid is None else nkid
            AMB = {"end-date", "judge", "text", "remarry", "infid"}
            if art:
                srcs = ["P1534"]
            elif [x for x in srcs if x in AMB]:
                skipped["shady_only"] += 1; continue
            elif nat or any_death:
                srcs = []
            else:
                skipped["no_evidence"] += 1; continue

        # ── SANITY, on the dates themselves
        if a == b:
            skipped["self"] += 1; continue
        for who, dob_y, dth in ((a, ya, dea), (b, yb, deb)):
            pass
        if (np.isfinite(dea) and dea < ya) or (np.isfinite(deb) and deb < yb):
            skipped["died_before_born"] += 1; continue
        if abs(ya - yb) > 60:
            skipped["gap60"] += 1; continue
        for s in srcs: n_src[s] += 1
        him, her = (a, b) if sa == MALE else (b, a)
        dh, dw = (da_, db_) if sa == MALE else (db_, da_)
        fullprec = int(("-00" not in dh) and ("-00" not in dw))
        # FULL-PRECISION DATES ONLY (operator 2026-09-01). A year-only birth date was being imputed to
        # 1 July, which places the Moon anywhere in the zodiac and Mercury nearly so — 45% of the rows
        # were carrying fast bodies that are pure noise. Since the fast bodies are the whole point of
        # testing whether this model reads anything but the birth century, an imputed row cannot be in
        # the corpus at all.
        if AQ_FULLPREC and not fullprec:
            skipped["imputed"] += 1
            # THE RECOVERY LIST (operator 2026-09-01, "improve the data"): this couple passed every
            # gate — label, sexes, finished, sanity — and failed ONLY on date precision. A precise
            # date may exist in a genealogy the Wikidata editor never copied; WikiTree is reachable
            # in bulk through P2949. Dump the pair so the recovery harvest knows exactly who to ask
            # about, and which side needs the date.
            prec_excluded.append({"pid_a": him, "pid_b": her, "dob_a": dh, "dob_b": dw,
                                  "need_a": int("-00" in dh), "need_b": int("-00" in dw),
                                  "y": 0 if srcs else 1})
            continue
        # natural: an explicitly-recorded till-death ending — P1534 natural cause, or an end date
        # within a year of a known death. The strict target trains sep-vs-THIS.
        endnat = any(deaths and any(abs(e - d) <= 1 for d in deaths) for e in r["ends"])
        dth_h, dth_w = (dea, deb) if sa == MALE else (deb, dea)
        rows.append({"pid_a": him, "pid_b": her, "dob_a": impute(dh), "dob_b": impute(dw),
                     "true_dob_a": dh, "true_dob_b": dw, "fullprec": fullprec,
                     "death_a": dth_h, "death_b": dth_w,
                     "outcome": ("failed:" + "+".join(srcs)) if srcs else "prospered",
                     "n_children": nkid,
                     # y = 1 means it PROSPERED (operator 2026-09-01): it ended in a death, it had
                     # children, and nothing in the record says divorce, infidelity or abuse. The
                     # model therefore predicts flourishing, not failure, and the page reads that way.
                     "y": 0 if srcs else 1, "src": "+".join(srcs) or "prospered",
                     "natural": int((nat or endnat) and not srcs)})
    d = pd.DataFrame(rows)
    print(f"\n  {len(d):,} couples ({int(d.fullprec.sum()):,} full-precision · "
          f"{len(d) - int(d.fullprec.sum()):,} imputed)")
    print(f"  target '{TARGET}' · y=1: {int(d.y.sum()):,} ({d.y.mean():.2%})   "
          f"y=0: {int((d.y == 0).sum()):,} ({1 - d.y.mean():.2%})")
    print(f"  children per couple among y=1: median {int(d[d.y == 1].n_children.median())} "
          f"· max {int(d.n_children.max())}")
    print(f"  skipped: imputed date {skipped['imputed']:,} · no dob {skipped['dob']:,} · not M+F {skipped['sex']:,} · "
          f"no evidence either way {skipped['no_evidence']:,} · weaker-than-P1534 evidence only "
          f"{skipped['shady_only']:,} · no children record {skipped['no_children_row']:,} · "
          f"self-pair {skipped['self']:,} · "
          f"died before born {skipped['died_before_born']:,} · gap>60y {skipped['gap60']:,} · "
          f"contradictions {dropped}")
    oc = d.outcome.value_counts()
    print("  how each surviving marriage is known to have ended: "
          + " · ".join(f"{k} {v:,}" for k, v in oc.items()))
    dup = d.duplicated(["pid_a", "pid_b"]).sum()
    print(f"  duplicate pairs remaining: {dup}")
    assert dup == 0, "a pair appears twice"
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
    pd.DataFrame({"pid": sorted(dob_missing)}).to_csv(f"{OUT}/_dob_missing.csv", index=False)
    pd.DataFrame(nokids_pairs, columns=["pid_a", "pid_b", "finished"]).to_csv(f"{OUT}/_nokids_pairs.csv", index=False)
    print(f"  wrote _dob_missing.csv: {len(dob_missing):,} people · _nokids_pairs.csv: {len(nokids_pairs):,} pairs "
          f"({sum(f for _, _, f in nokids_pairs):,} finished)")
    if prec_excluded:
        pd.DataFrame(prec_excluded).to_csv(f"{OUT}/_prec_excluded.csv", index=False)
        print(f"  wrote _prec_excluded.csv: {len(prec_excluded):,} couples one exact date short")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
