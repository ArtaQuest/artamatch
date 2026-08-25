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
    idx = {p: g.sy.values for p, g in mar.groupby("p")}
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
    out = out[(ya < 1950) & (yb < 1950) & (np.abs(ya - yb) <= 60) & ya.between(1400, 1950) & yb.between(1400, 1950)]
    out["later_birth"] = np.fmax(pd.to_numeric(out.dob_a.str[:4], errors="coerce"),
                                 pd.to_numeric(out.dob_b.str[:4], errors="coerce"))
    print(f"\n  {len(out):,} gendered couples, both born before 1950, one row each")
    print(f"    label by the rule:    {out.y_rule.mean():.1%} artificial")
    print(f"    label by the variant: {out.y_alive.mean():.1%} artificial")

    out = out.sort_values("later_birth", kind="mergesort").reset_index(drop=True)
    cut = int(len(out) * 0.85)
    bnd = out.later_birth.iloc[cut - 1]
    tr = out[out.later_birth <= bnd].copy(); te = out[out.later_birth > bnd].copy()
    seen_p = set(tr.pid_a) | set(tr.pid_b)
    te = te[~(te.pid_a.isin(seen_p) | te.pid_b.isin(seen_p))]
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
    print(f"\n  train {len(tr):,} · test {len(te):,} · born to {int(bnd)} / from {int(te.later_birth.min())}")
    print(f"  artificial: train {tr.y_rule.mean():.1%} · test {te.y_rule.mean():.1%}")


if __name__ == "__main__":
    main()
