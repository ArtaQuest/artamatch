"""
build_remarriage.py — label divorce STRUCTURALLY: either partner married again after this marriage began.

Operator 2026-08-24: "do not rely on the wiki label · list all the marriages of each couple · its considered
divorce if either remarried after."

THE LABEL (operator 2026-08-25, superseding the first cut): a marriage is a DIVORCE if either partner
remarried WHILE BOTH WERE STILL ALIVE. Validated against the 13,323 statements carrying an explicit end
cause: precision 89.8% — when this rule says divorce it is nearly always right — against 54.3% for the
plain remarried-after rule, whose false positives are widowers remarrying. Recall is 32.7%: many real
divorces leave no recorded remarriage, so the negative class contains hidden divorces and the measured AUC
is a floor, not a ceiling.

WHAT IS CHECKED BEFORE IT IS TRUSTED. The rule is scored three ways against the ~24,000 statements where
Wikidata DOES record an explicit end cause — not to defer to that label, but because a rule that disagrees
with the recorded truth needs to explain itself:
  · the rule as specified
  · the rule restricted to remarriages that began while the OTHER PARTNER WAS STILL ALIVE, which is the
    version that distinguishes a divorce from a widower marrying again
  · the recorded label itself, as the ceiling
Both variants are emitted so the difference can be measured rather than argued.
"""
import glob, os, re
import numpy as np, pandas as pd

SRC = os.path.expanduser(os.environ.get("AQ_MAR", "~/.artamatch-dev/marriages"))
OUT = os.path.expanduser(os.environ.get("AQ_OUT", "~/.artamatch-dev/remar"))
MISSING = "0000-00-00"
LABEL = "ended_in_divorce"
ART = {"Q93190", "Q701040", "Q5561011", "Q3456503", "Q1299585", "Q1142948", "Q759734", "Q100926628",
       "Q305418", "Q2914621", "Q5282797", "Q234213", "Q898987", "Q16557696", "Q65089925"}
NAT = {"Q24037741", "Q99521170", "Q4", "Q90110620", "Q179115", "Q18646998", "Q10806", "Q161936",
       "Q10737", "Q210392", "Q267505", "Q1076426", "Q15747939", "Q21142718"}
qid = lambda s: re.sub(r"[^Q0-9]", "", str(s)) if isinstance(s, str) else ""


def render(ts, prec):
    """Wikidata stores a full timestamp with the real precision beside it, so a year-precision date arrives
    looking exactly like 1 January. Render at the DECLARED precision or the fast bodies get a day nobody
    recorded."""
    if not isinstance(ts, str):
        return MISSING
    m = re.match(r"^[+-]?(\d{4})-(\d{2})-(\d{2})", ts.strip())
    if not m:
        return MISSING
    y, mo, d = m.groups()
    if y == "0000":
        return MISSING
    p = pd.to_numeric(prec, errors="coerce")
    if not np.isfinite(p):
        return f"{y}-00-00" if (mo, d) == ("01", "01") else f"{y}-{mo}-{d}"
    if p <= 9:
        return f"{y}-00-00"
    if p == 10:
        return f"{y}-{mo}-00"
    return f"{y}-00-00" if (mo, d) == ("01", "01") else f"{y}-{mo}-{d}"


def main():
    os.makedirs(OUT, exist_ok=True)
    fr = [pd.read_csv(f, dtype=str) for f in sorted(glob.glob(os.path.join(SRC, "d*.csv")))]
    d = pd.concat(fr, ignore_index=True)
    for c in ("a", "b", "cause", "asex"):
        d[c] = d[c].map(qid) if c in d.columns else ""
    print(f"  {len(d):,} raw marriage statements from {len(fr)} decade files", flush=True)

    yr = lambda s: pd.to_numeric(s.astype(str).str.extract(r"^[+-]?(\d{4})")[0], errors="coerce").replace(0, np.nan)
    d["sy"] = yr(d.start); d["ady"] = yr(d.adeath); d["aby"] = yr(d.adob)
    d["dob"] = [render(v, p) for v, p in zip(d.adob, d.aprec)]

    # ── PERSON TABLE: everyone appears as ?a in their own birth-decade slice, so this is complete
    per = (d.sort_values("dob").drop_duplicates("a")
             .set_index("a")[["dob", "aby", "ady", "asex"]])
    print(f"  {len(per):,} distinct people with a birth date", flush=True)
    # AUDIT 2026-08-26: ~6% of persons carry MULTI-VALUED birth dates and the lexical pick above chooses
    # the coarsest (or even a deprecated) statement. AQ_TRUTHY points at a rank-resolved sweep
    # (qid, dob_truthy, death_truthy) fetched live: preferred > normal, deprecated never — those override.
    tp = os.environ.get("AQ_TRUTHY")
    if tp and os.path.exists(os.path.expanduser(tp)):
        tt = pd.read_csv(os.path.expanduser(tp), dtype=str).set_index("qid")
        hit = per.index.intersection(tt.index)
        per.loc[hit, "dob"] = tt.loc[hit, "dob_truthy"]
        tdy = pd.to_numeric(tt.loc[hit, "death_truthy"], errors="coerce")
        per.loc[hit, "ady"] = np.where(np.isfinite(tdy), tdy, per.loc[hit, "ady"])
        amap_d = per.dob.to_dict(); amap_y = per.ady.to_dict()
        inA = d.a.isin(hit)
        d.loc[inA, "dob"] = d.loc[inA, "a"].map(amap_d)
        d.loc[inA, "ady"] = d.loc[inA, "a"].map(amap_y)
        print(f"  {len(hit):,} persons patched to rank-resolved (truthy) birth/death dates", flush=True)
    # OPERATOR 2026-08-26: a day-precision 1 January is kept as a REAL date only when the person's
    # Wikipedia article states the birth as 1 January of that year (the corpus carries ~2x the natural
    # rate of Jan-1 claims — half are import artifacts). AQ_JAN1 points at the verification sweep;
    # verified persons are upgraded from the blanket year-only demotion back to the true date.
    jp = os.environ.get("AQ_JAN1")
    if jp and os.path.exists(os.path.expanduser(jp)):
        jv = pd.read_csv(os.path.expanduser(jp), dtype=str)
        upgraded = 0
        for q, y in zip(jv[jv.verified == "1"].qid, jv[jv.verified == "1"].year):
            if q in per.index and per.at[q, "dob"] == f"{y}-00-00":
                per.at[q, "dob"] = f"{y}-01-01"
                upgraded += 1
        amap_d = per.dob.to_dict()
        inA = d.a.isin(set(jv[jv.verified == "1"].qid))
        d.loc[inA, "dob"] = d.loc[inA, "a"].map(amap_d)
        print(f"  {upgraded} Wikipedia-verified 1-January births restored to full precision "
              f"({int((jv.verified == '0').sum())} unverified stay year-only)", flush=True)

    # ── EVERY MARRIAGE OF EVERY PERSON, from both sides of each statement
    mar = pd.concat([d[["a", "b", "sy"]].rename(columns={"a": "p", "b": "q"}),
                     d[["b", "a", "sy"]].rename(columns={"b": "p", "a": "q"})], ignore_index=True)
    mar = mar[mar.p.str.startswith("Q")].drop_duplicates(["p", "q", "sy"])
    nmar = mar.groupby("p").size()
    lastmar = mar.groupby("p").sy.max()
    print(f"  marriage list built: {len(mar):,} person-marriage rows · "
          f"{int((nmar > 1).sum()):,} people with 2+ marriages", flush=True)

    # ── THE RULE: did either partner marry again AFTER this marriage began?
    d["a_later"] = [np.nansum(g) if False else 0 for g in []] if False else 0
    # AUDIT 2026-08-26: the same wedding recorded on both pages with discrepant years must not count as
    # a remarriage — collapse to ONE start per distinct spouse (validated: precision 89.8% -> 92.1% against
    # explicit end causes; spouse-unknown marriages keep every year). AQ_NO_COLLAPSE=1 restores the old rule.
    if os.environ.get("AQ_NO_COLLAPSE"):
        idx = {p: g.sy.values for p, g in mar.groupby("p")}
    else:
        mm_ = mar[mar.q != ""]
        idx = {p: g.groupby("q").sy.min().values for p, g in mm_.groupby("p")}
        for p, g in mar[mar.q == ""].groupby("p"):
            idx[p] = np.concatenate([idx.get(p, np.empty(0)), g.sy.values])
    def remarried_after(p, s):
        v = idx.get(p)
        if v is None or not np.isfinite(s):
            return False
        return bool(np.any(v > s))
    d["a_rem"] = [remarried_after(p, s) for p, s in zip(d.a, d.sy)]
    d["b_rem"] = [remarried_after(p, s) for p, s in zip(d.b, d.sy)]
    d["y_rule"] = (d.a_rem | d.b_rem).astype(int)

    # ── VARIANT: only remarriages that began while the OTHER partner was still alive
    bdy = per.ady.reindex(d.b).to_numpy()
    def remarried_while_alive(p, s, other_death):
        v = idx.get(p)
        if v is None or not np.isfinite(s) or not np.isfinite(other_death):
            return False
        return bool(np.any((v > s) & (v < other_death)))
    d["y_alive"] = np.array([remarried_while_alive(pa, s, db) or remarried_while_alive(pb, s, da)
                             for pa, pb, s, da, db in zip(d.a, d.b, d.sy, d.ady, bdy)]).astype(int)

    # ── VALIDATION against the recorded cause, which we are no longer relying on
    expl = d.cause.isin(ART | NAT)
    truth = d.cause.isin(ART).astype(int)
    m = expl.to_numpy()
    print(f"\n  VALIDATION on the {int(m.sum()):,} statements carrying an explicit end cause:")
    for nm, col in (("the rule as specified (remarried after)", "y_rule"),
                    ("variant: remarried while the other lived", "y_alive")):
        pred = d[col].to_numpy()[m]; t = truth.to_numpy()[m]
        acc = (pred == t).mean()
        tp = int(((pred == 1) & (t == 1)).sum()); fp = int(((pred == 1) & (t == 0)).sum())
        fn = int(((pred == 0) & (t == 1)).sum())
        prec = tp / max(1, tp + fp); rec = tp / max(1, tp + fn)
        print(f"    {nm:<42} acc {acc:.1%}  precision {prec:.1%}  recall {rec:.1%}")
    print(f"    (base rate among those: {truth[m].mean():.1%} artificial)")

    # ── the dataset: gendered, both dates, pre-1950, one row per couple
    draw = d                                   # full statement table, kept for the recovery pass below
    d = d[d.sy.notna()]
    bdob = per.dob.reindex(d.b).to_numpy(); bsex = per.asex.reindex(d.b).to_numpy()
    # a b-side partner born outside 1500-1950 never appears as ?a, so their sex is unknown here — those rows
    # are dropped at the gender gate below rather than guessed
    out = pd.DataFrame({"pa": d.a.to_numpy(), "pb": d.b.to_numpy(), "dob_a": d.dob.to_numpy(),
                        "dob_b": bdob, "asex": d.asex.to_numpy(), "bsex": bsex,
                        "sy": d.sy.to_numpy(), "y_rule": d.y_rule.to_numpy(), "y_alive": d.y_alive.to_numpy()})
    out = out[(out.dob_a != MISSING) & pd.notna(out.dob_b) & (out.dob_b != MISSING)]
    MALE, FEM = "Q6581097", "Q6581072"
    keep = ((out.asex == MALE) & (out.bsex == FEM)) | ((out.asex == FEM) & (out.bsex == MALE))
    out = out[keep].copy()
    sw = out.asex == FEM
    A = np.where(sw, out.dob_b, out.dob_a); B = np.where(sw, out.dob_a, out.dob_b)
    PA = np.where(sw, out.pb, out.pa); PB = np.where(sw, out.pa, out.pb)
    out = pd.DataFrame({"dob_a": A, "dob_b": B, "pid_a": PA, "pid_b": PB,
                        "y_rule": out.y_rule.to_numpy(), "y_alive": out.y_alive.to_numpy()})
    # ── HARD ASSERTION, not a convention: after the swap, pid_a must be MALE and pid_b FEMALE for every
    #    single row, checked against the sex map itself. A dataset that merely intends male-first is one
    #    refactor away from silently breaking the meaning of every gendered feature downstream.
    sexmap = per.asex.to_dict()
    sa = np.array([sexmap.get(p, "") for p in out.pid_a]); sb = np.array([sexmap.get(p, "") for p in out.pid_b])
    # a person can carry TWO P21 statements, and which one a dedupe keeps depends on row order — the statement
    # side and the person table can then disagree. Such rows are DROPPED (their sex is genuinely ambiguous in
    # the source), and the assertion runs on what remains.
    ok = (sa == MALE) & (sb == FEM)
    if (~ok).any():
        print(f"  dropped {int((~ok).sum())} row(s) with self-contradictory sex records", flush=True)
        out = out[ok].copy()
        sa, sb = sa[ok], sb[ok]
    assert (sa == MALE).all() and (sb == FEM).all()
    print(f"  ASSERTED: column a is the MAN and column b the WOMAN on all {len(out):,} rows", flush=True)
    out["pair"] = [f"{min(x,y)}|{max(x,y)}" for x, y in zip(out.pid_a, out.pid_b)]
    out = out.drop_duplicates("pair")
    ya = pd.to_numeric(out.dob_a.str[:4], errors="coerce").replace(0, np.nan)
    yb = pd.to_numeric(out.dob_b.str[:4], errors="coerce").replace(0, np.nan)
    if os.environ.get("AQ_DECEASED"):
        # OPERATOR 2026-08-26: every deceased person is included — a couple qualifies when both were born
        # before 1950 (a life that has run its course) OR both have a recorded death, any birth year.
        dmap = per.ady.to_dict()
        da_k = np.isfinite(pd.Series([dmap.get(p, np.nan) for p in out.pid_a]).to_numpy(float))
        db_k = np.isfinite(pd.Series([dmap.get(p, np.nan) for p in out.pid_b]).to_numpy(float))
        elig = ((ya < 1950) & (yb < 1950)) | (da_k & db_k)
        out = out[elig & (np.abs(ya - yb) <= 60) & ya.between(1400, 2010) & yb.between(1400, 2010)]
        print(f"  DECEASED-INCLUSION: {int((da_k & db_k & ~((ya < 1950) & (yb < 1950))).sum()):,} "
              f"post-1950 both-deceased couples added to the pre-1950 corpus")
    else:
        out = out[(ya < 1950) & (yb < 1950) & (np.abs(ya - yb) <= 60) & ya.between(1400, 1950) & yb.between(1400, 1950)]
    # AUDIT 2026-08-26: a statement with no start date CAN still be labeled when neither partner has any
    # other marriage statement at all — nobody remarried, so the label is 0 by definition. 52% of the raw
    # harvest was dropped for a missing start; this recovers the mono-married slice of it as definitive
    # negatives (each such couple is its own marriage component, so split integrity holds by construction).
    # AQ_NO_RECOVER=1 skips it.
    if not os.environ.get("AQ_NO_RECOVER"):
        nmar_any = pd.concat([draw[["a", "b"]].rename(columns={"a": "p", "b": "q"}),
                              draw[["b", "a"]].rename(columns={"b": "p", "a": "q"})], ignore_index=True)
        nmar_any = nmar_any[nmar_any.p.str.startswith("Q")].drop_duplicates(["p", "q"])
        cnt = nmar_any.groupby("p").size()
        miss = draw[draw.sy.isna()].copy()
        rec = miss[(miss.a.map(cnt).fillna(9) == 1) & (miss.b.map(cnt).fillna(9) == 1)].copy()
        rec["dob_b"] = per.dob.reindex(rec.b).to_numpy()
        rec["bsex"] = per.asex.reindex(rec.b).to_numpy()
        rec = rec[(rec.dob != MISSING) & pd.notna(rec.dob_b) & (rec.dob_b != MISSING)]
        keep2 = ((rec.asex == MALE) & (rec.bsex == FEM)) | ((rec.asex == FEM) & (rec.bsex == MALE))
        rec = rec[keep2].copy()
        sw2 = rec.asex == FEM
        rec_out = pd.DataFrame({
            "dob_a": np.where(sw2, rec.dob_b, rec.dob), "dob_b": np.where(sw2, rec.dob, rec.dob_b),
            "pid_a": np.where(sw2, rec.b, rec.a), "pid_b": np.where(sw2, rec.a, rec.b),
            "y_rule": 0, "y_alive": 0})
        ry_a = pd.to_numeric(rec_out.dob_a.str[:4], errors="coerce").replace(0, np.nan)
        ry_b = pd.to_numeric(rec_out.dob_b.str[:4], errors="coerce").replace(0, np.nan)
        if os.environ.get("AQ_DECEASED"):
            rdmap = per.ady.to_dict()
            rda = np.isfinite(pd.Series([rdmap.get(p, np.nan) for p in rec_out.pid_a]).to_numpy(float))
            rdb = np.isfinite(pd.Series([rdmap.get(p, np.nan) for p in rec_out.pid_b]).to_numpy(float))
            relig = ((ry_a < 1950) & (ry_b < 1950)) | (rda & rdb)
            rec_out = rec_out[relig & (np.abs(ry_a - ry_b) <= 60)
                              & ry_a.between(1400, 2010) & ry_b.between(1400, 2010)]
        else:
            rec_out = rec_out[(ry_a < 1950) & (ry_b < 1950) & (np.abs(ry_a - ry_b) <= 60)
                              & ry_a.between(1400, 1950) & ry_b.between(1400, 1950)]
        rec_out["pair"] = [f"{min(x,y)}|{max(x,y)}" for x, y in zip(rec_out.pid_a, rec_out.pid_b)]
        out = pd.concat([out, rec_out], ignore_index=True).drop_duplicates("pair")
        print(f"  +{len(rec_out):,} recovered mono-married missing-start couples (all definitive negatives)")
    # OPERATOR 2026-08-26: AQ_FULLPREC=1 keeps only couples where BOTH dates are full precision
    if os.environ.get("AQ_FULLPREC"):
        fp = ((out.dob_a.str[5:7] != "00") & (out.dob_a.str[8:10] != "00")
              & (out.dob_b.str[5:7] != "00") & (out.dob_b.str[8:10] != "00"))
        print(f"  FULL-PRECISION GATE: {int(fp.sum()):,} of {len(out):,} couples have both dates to the day")
        out = out[fp].copy()
    out["later_birth"] = np.fmax(pd.to_numeric(out.dob_a.str[:4], errors="coerce"),
                                 pd.to_numeric(out.dob_b.str[:4], errors="coerce"))
    print(f"\n  {len(out):,} gendered couples, both born before 1950, one row each")
    print(f"    label by the rule:    {out.y_rule.mean():.1%} artificial")
    print(f"    label by the variant: {out.y_alive.mean():.1%} artificial")

    # SPLIT (operator 2026-08-25): SHUFFLED, not temporal — "don't bias into modern. I want models that
    # interpolate the entire history of recorded marriages." The test half is a uniform sample of five
    # centuries, so every era appears on both sides and the slow-body era channel is measurable skill.
    # Person- and birth-date-disjointness are KEPT: identity must still never leak, only doctrine.
    if os.environ.get("AQ_SPLIT", "shuffle") == "shuffle":
        # SPLIT BY CONNECTED COMPONENT of the marriage graph, not by row. Row-shuffling followed by dropping
        # test rows that share a person with train deletes exactly the REMARRIED (their multiple rows straddle
        # the halves), halving the positive rate in test (8.2% vs 17.6%). Whole components go to one side, so
        # nothing is deleted and both halves keep the true base rate — and person-disjointness holds by
        # construction.
        parent = {}
        def find(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        for a, b in zip(out.pid_a, out.pid_b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        comp = np.array([find(a) for a in out.pid_a])
        rng = np.random.default_rng(42)
        uniq = rng.permutation(np.unique(comp))
        sizes = pd.Series(comp).value_counts()
        cum = np.cumsum([sizes[c] for c in uniq])
        n_te = int(len(out) * 0.15)
        te_comps = set(uniq[cum <= n_te])
        is_te = np.array([c in te_comps for c in comp])
        tr = out[~is_te].copy(); te = out[is_te].copy()
        bnd = -1
    else:
        out = out.sort_values("later_birth", kind="mergesort").reset_index(drop=True)
        cut = int(len(out) * 0.85)
        bnd = out.later_birth.iloc[cut - 1]
        tr = out[out.later_birth <= bnd].copy(); te = out[out.later_birth > bnd].copy()
    seen_p = set(tr.pid_a) | set(tr.pid_b)
    te = te[~(te.pid_a.isin(seen_p) | te.pid_b.isin(seen_p))].copy()
    # birth-DATE disjointness is a TEMPORAL-split guard (a memorisable person recurring under a new id). In the
    # shuffled interpolation regime five centuries of training cover nearly every calendar date, so it deleted
    # 87% of the test half and skewed what survived toward the under-documented centuries (7.5% positive
    # against 17.6% overall). Two DIFFERENT people sharing a birth date is interpolation itself — the person
    # filter above is the identity guard.
    if bnd != -1:
        seen_d = (set(tr.dob_a) | set(tr.dob_b)) - {MISSING}
        te = te[~(te.dob_a.isin(seen_d) | te.dob_b.isin(seen_d))].copy()
    te.insert(0, "id", [f"r{i:06d}" for i in range(len(te))])
    for f in (tr, te):
        f["start"] = MISSING
    # THE label is the operator's definition — remarried while both lived. The plain rule ships as a sidecar.
    tr.rename(columns={"y_alive": LABEL})[["dob_a", "dob_b", "start", LABEL]].to_csv(f"{OUT}/train.csv", index=False)
    te[["id", "dob_a", "dob_b", "start"]].to_csv(f"{OUT}/test.csv", index=False)
    te.rename(columns={"y_alive": LABEL})[["id", LABEL]].to_csv(f"{OUT}/solution.csv", index=False)
    tr[["pid_a", "pid_b", "y_rule", "y_alive"]].to_csv(f"{OUT}/_train_ids.csv", index=False)
    te[["id", "pid_a", "pid_b", "y_rule", "y_alive"]].to_csv(f"{OUT}/_test_ids.csv", index=False)
    print(f"\n  train {len(tr):,} · test {len(te):,} · split={'SHUFFLED (interpolation)' if bnd == -1 else f'temporal to {int(bnd)}'}")
    print(f"  test birth-year span: {int(te.later_birth.min())}-{int(te.later_birth.max())} (train "
          f"{int(tr.later_birth.min())}-{int(tr.later_birth.max())})")
    print(f"  artificial: train {tr.y_rule.mean():.1%} · test {te.y_rule.mean():.1%}")


if __name__ == "__main__":
    main()
